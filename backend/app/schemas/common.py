"""Shared Pydantic models: status enums, error envelope, system probes."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class OperationStatus(str, Enum):
    QUEUED = "queued"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict = {}


class ErrorEnvelope(BaseModel):
    error: ErrorPayload


class HealthResponse(BaseModel):
    status: str
    engine: str
    version: str
    timestamp: datetime


class FfmpegStatus(BaseModel):
    available: bool
    path: str | None = None
    version: str | None = None