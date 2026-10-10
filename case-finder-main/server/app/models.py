from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    generating_baseline = "generating_baseline"
    summarizing = "summarizing"
    embedding = "embedding"
    retrieving = "retrieving"
    filtering = "filtering"
    generating_enriched = "generating_enriched"
    completed = "completed"
    failed = "failed"
    deletion_requested = "deletion_requested"


class QuestionMode(str, Enum):
    baseline = "baseline"
    enriched = "enriched"
    both = "both"


class UploadResponse(BaseModel):
    process_id: str
    status: JobStatus


class ErrorDetail(BaseModel):
    code: str
    message: str


class ProgressResponse(BaseModel):
    process_id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    created_at: str
    updated_at: str
    error: ErrorDetail | None = None


class Question(BaseModel):
    question: str = Field(min_length=1)
    understanding: str = Field(min_length=1)
    importance: str = Field(min_length=1)


class QuestionsResponse(BaseModel):
    process_id: str
    mode: QuestionMode
    baseline: list[Question] | None = None
    enriched: list[Question] | None = None


class InputFile(BaseModel):
    original_name: str
    stored_name: str


class InputResponse(BaseModel):
    process_id: str
    text: str
    files: list[InputFile]


class WhoAmIResponse(BaseModel):
    username: str


class PendingResponse(BaseModel):
    process_id: str
    status: JobStatus
    progress: int


class DeleteResponse(BaseModel):
    process_id: str
    status: str
