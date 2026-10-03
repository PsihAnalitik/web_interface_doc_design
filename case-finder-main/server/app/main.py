from __future__ import annotations

import json
import logging
import re
import secrets
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import Settings
from .document_parser import DocumentParseError, parse_document
from .job_store import JobNotFoundError, JobStore
from .logging_config import configure_logging
from .models import (
    DeleteResponse,
    JobStatus,
    PendingResponse,
    ProgressResponse,
    QuestionMode,
    QuestionsResponse,
    UploadResponse,
)

configure_logging()
logger = logging.getLogger(__name__)
security = HTTPBasic()


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def get_store(settings: Annotated[Settings, Depends(get_settings)]) -> JobStore:
    return JobStore(settings.storage_path)


def authenticate(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    authenticated = False
    for username, password in settings.api_users.items():
        username_matches = secrets.compare_digest(credentials.username, username)
        password_matches = secrets.compare_digest(credentials.password, password)
        authenticated |= username_matches and password_matches
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


app = FastAPI(
    title="Case Finder API",
    description="Generate baseline and similar-case-enriched clarification questions.",
    version="1.0.0",
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        raise
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
        },
    )
    return response


@app.post(
    "/start_process",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_process(
    _: Annotated[str, Depends(authenticate)],
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[JobStore, Depends(get_store)],
    text: Annotated[str, Form()] = "",
    question_count: Annotated[int, Form(ge=1)] = 7,
    language: Annotated[str, Form(min_length=1, max_length=50)] = "English",
    files: Annotated[list[UploadFile], File()] = [],
) -> UploadResponse:
    if question_count > settings.max_question_count:
        raise HTTPException(
            status_code=422,
            detail=f"question_count must not exceed {settings.max_question_count}",
        )
    language = language.strip()
    if not language or not re.fullmatch(r"[^\x00-\x1f\x7f]{1,50}", language):
        raise HTTPException(
            status_code=422, detail="language contains invalid characters"
        )
    if len(files) > settings.max_files:
        raise HTTPException(
            status_code=422, detail=f"At most {settings.max_files} files are allowed"
        )

    parsed_files: list[tuple[str, bytes, str]] = []
    total_size = 0
    for upload in files:
        filename = Path(upload.filename or "").name
        if not filename:
            raise HTTPException(
                status_code=422, detail="Every file must have a filename"
            )
        content = await upload.read(settings.max_file_size_bytes + 1)
        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File {filename} exceeds the per-file size limit",
            )
        total_size += len(content)
        if total_size > settings.max_total_upload_bytes:
            raise HTTPException(
                status_code=413, detail="Total upload size limit exceeded"
            )
        try:
            parsed = parse_document(filename, content)
        except DocumentParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        parsed_files.append((filename, content, parsed))

    sections = []
    if text.strip():
        sections.append(f"<text_input>\n{text.strip()}\n</text_input>")
    for filename, _, parsed in parsed_files:
        if parsed.strip():
            sections.append(
                f"<file name={json.dumps(filename)}>\n{parsed.strip()}\n</file>"
            )
    if not sections:
        raise HTTPException(
            status_code=422,
            detail="The request must contain non-empty text or a file with extractable text",
        )

    process_id = store.create_job(
        text=text,
        files=parsed_files,
        combined_text="\n\n".join(sections),
        question_count=question_count,
        language=language,
    )
    return UploadResponse(process_id=process_id, status=JobStatus.queued)


@app.get("/get_progress/{process_id}", response_model=ProgressResponse)
def get_progress(
    process_id: str,
    _: Annotated[str, Depends(authenticate)],
    store: Annotated[JobStore, Depends(get_store)],
) -> ProgressResponse:
    try:
        return ProgressResponse.model_validate(store.read_status(process_id))
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Process not found") from exc


@app.get(
    "/get_questions/{process_id}",
    response_model=QuestionsResponse,
    responses={202: {"model": PendingResponse}},
)
def get_questions(
    process_id: str,
    _: Annotated[str, Depends(authenticate)],
    store: Annotated[JobStore, Depends(get_store)],
    mode: QuestionMode = QuestionMode.both,
):
    try:
        job_status = store.read_status(process_id)
        if job_status["status"] == "failed":
            raise HTTPException(status_code=409, detail=job_status.get("error"))
        if job_status["status"] != "completed":
            pending = PendingResponse(
                process_id=process_id,
                status=job_status["status"],
                progress=job_status["progress"],
            )
            return JSONResponse(
                status_code=202, content=pending.model_dump(mode="json")
            )
        baseline = (
            store.read_json(process_id, "baseline_questions.json")
            if mode in {QuestionMode.baseline, QuestionMode.both}
            else None
        )
        enriched = (
            store.read_json(process_id, "enriched_questions.json")
            if mode in {QuestionMode.enriched, QuestionMode.both}
            else None
        )
        return QuestionsResponse(
            process_id=process_id, mode=mode, baseline=baseline, enriched=enriched
        )
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Process not found") from exc


@app.delete("/delete_job/{process_id}", response_model=DeleteResponse)
def delete_job(
    process_id: str,
    _: Annotated[str, Depends(authenticate)],
    store: Annotated[JobStore, Depends(get_store)],
) -> DeleteResponse:
    try:
        result = store.delete(process_id)
        return DeleteResponse(process_id=process_id, status=result)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Process not found") from exc
