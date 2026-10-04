"""Authenticated HTTP entry point for the separate passport factory queue."""
from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import secrets
from typing import Annotated

from app.config import Settings
from app.job_store import JobNotFoundError, JobStore
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()
app = FastAPI(title="Passport factory", version="1.0.0")


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def get_store() -> JobStore:
    return JobStore(Path(os.getenv("FACTORY_STORAGE_PATH", "/app/factory-storage")))


def authenticate(credentials: Annotated[HTTPBasicCredentials, Depends(security)],
                 settings: Annotated[Settings, Depends(get_settings)]) -> str:
    authenticated = False
    for username, password in settings.api_users.items():
        authenticated |= (secrets.compare_digest(credentials.username.encode(), username.encode())
                          & secrets.compare_digest(credentials.password.encode(), password.encode()))
    if not authenticated:
        raise HTTPException(401, "Invalid authentication credentials", headers={"WWW-Authenticate": "Basic"})
    return credentials.username


@app.post("/start_process", status_code=202)
async def start_process(
    _: Annotated[str, Depends(authenticate)],
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[JobStore, Depends(get_store)],
    files: Annotated[list[UploadFile], File()] = [],
    text: Annotated[str, Form()] = "",
):
    if text.strip() or not files:
        raise HTTPException(422, "Upload non-empty UTF-8 .md documents; pasted text is not supported")
    if len(files) > settings.max_files:
        raise HTTPException(422, "Too many files")
    parsed_files = []
    total = 0
    for upload in files:
        filename = Path(upload.filename or "").name
        if Path(filename).suffix.lower() != ".md":
            raise HTTPException(422, "Only .md files are supported")
        content = await upload.read(settings.max_file_size_bytes + 1)
        total += len(content)
        if len(content) > settings.max_file_size_bytes or total > settings.max_total_upload_bytes:
            raise HTTPException(413, "Upload size limit exceeded")
        try:
            parsed = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(422, "Documents must be UTF-8") from exc
        if not parsed.strip() or "\x00" in parsed:
            raise HTTPException(422, "Documents must contain non-empty Markdown text")
        parsed_files.append((filename, content, parsed))
    process_id = store.create_job(text="", files=parsed_files,
                                  combined_text="\n\n".join(item[2] for item in parsed_files),
                                  question_count=1, language="Russian")
    return {"process_id": process_id, "status": "queued"}


@app.get("/get_progress/{process_id}")
def get_progress(process_id: str, _: Annotated[str, Depends(authenticate)],
                 store: Annotated[JobStore, Depends(get_store)]):
    try:
        return store.read_status(process_id)
    except JobNotFoundError as exc:
        raise HTTPException(404, "Process not found") from exc


@app.get("/get_result/{process_id}")
def get_result(process_id: str, _: Annotated[str, Depends(authenticate)],
               store: Annotated[JobStore, Depends(get_store)]):
    try:
        state = store.read_status(process_id)
        if state["status"] not in {"completed", "failed"}:
            raise HTTPException(409, "Analysis is not finished")
        try:
            return store.read_json(process_id, "web_result.json")
        except JobNotFoundError as exc:
            raise HTTPException(409, "No usable analysis is available") from exc
    except JobNotFoundError as exc:
        raise HTTPException(404, "Process not found") from exc
