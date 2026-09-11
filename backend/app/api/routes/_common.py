"""Shared route helpers."""

from __future__ import annotations

from typing import Sequence

from fastapi import UploadFile

from ...deps import ops
from ...schemas.operations import OperationSummary
from ...services.validation_service import SUFFIX_RULES
from ...storage.op_store import OpRecord


def summary(rec: OpRecord) -> OperationSummary:
    return OperationSummary(
        id=rec.id, kind=rec.kind, media=rec.media, method=rec.method,
        status=rec.status, progress=rec.progress, message=rec.message,
        created_at=rec.created_at, updated_at=rec.updated_at,
    )


async def accept_uploads(rec: OpRecord, files: Sequence[UploadFile],
                         rule: str) -> list[str]:
    allowed = SUFFIX_RULES[rule] or None
    for upload in files:
        await ops.save_upload(rec, upload, allowed)
    return list(rec.input_names)