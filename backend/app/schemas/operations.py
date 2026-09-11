"""Operation models: summaries, details and progress events."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .common import ErrorPayload, OperationStatus


class ResultFile(BaseModel):
    name: str
    size: int


class OperationSummary(BaseModel):
    id: str
    kind: str  # split | reveal
    media: str  # image | audio | video | file
    method: str | None = None
    status: OperationStatus
    progress: int
    message: str
    created_at: datetime
    updated_at: datetime


class OperationDetail(OperationSummary):
    input_names: list[str] = []
    result_files: list[ResultFile] = []
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    error: ErrorPayload | None = None


class OperationListResponse(BaseModel):
    operations: list[OperationSummary]


class ProgressEvent(BaseModel):
    type: str  # progress | completed | error
    progress: int = 0
    message: str = ""
    error: ErrorPayload | None = None