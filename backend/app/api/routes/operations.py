"""Operation management + result download endpoints."""

from __future__ import annotations

import zipfile
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from ...deps import ops
from ...schemas.common import OperationStatus
from ...schemas.operations import (
    OperationDetail,
    OperationListResponse,
    OperationSummary,
    ResultFile,
)
from ...security.errors import ApiError
from ...security.files import safe_join
from ...storage.op_store import OpRecord

router = APIRouter(tags=["operations"])


def _require(op_id: str) -> OpRecord:
    rec = ops.store.get(op_id)
    if rec is None:
        raise ApiError(code="OPERATION_NOT_FOUND", message="Unknown operation.",
                       status_code=404)
    return rec


def _summary(rec: OpRecord) -> OperationSummary:
    return OperationSummary(
        id=rec.id, kind=rec.kind, media=rec.media, method=rec.method,
        status=rec.status, progress=rec.progress, message=rec.message,
        created_at=rec.created_at, updated_at=rec.updated_at,
    )


@router.get("/api/operations", response_model=OperationListResponse)
def list_operations(limit: int = Query(default=50, ge=1, le=200)) -> OperationListResponse:
    records = ops.store.list(limit)
    return OperationListResponse(operations=[_summary(r) for r in records])


@router.get("/api/operations/{op_id}", response_model=OperationDetail)
def get_operation(op_id: str) -> OperationDetail:
    rec = _require(op_id)
    return OperationDetail(
        **_summary(rec).model_dump(),
        input_names=list(rec.input_names),
        result_files=list(rec.result_files),
        started_at=rec.started_at,
        finished_at=rec.finished_at,
        duration_ms=rec.duration_ms,
        error=rec.error,
    )


@router.post("/api/operations/{op_id}/cancel", response_model=OperationSummary)
def cancel_operation(op_id: str) -> OperationSummary:
    rec = _require(op_id)
    ops.cancel(rec)
    return _summary(rec)


@router.get("/api/operations/{op_id}/files", response_model=list[ResultFile])
def operation_files(op_id: str) -> list[ResultFile]:
    rec = _require(op_id)
    if rec.status is not OperationStatus.COMPLETED:
        raise ApiError(code="OPERATION_BUSY",
                       message="Results are not ready yet.", status_code=409)
    return list(rec.result_files)


@router.get("/api/operations/{op_id}/download-all")
def download_all(op_id: str) -> FileResponse:
    rec = _require(op_id)
    if rec.status is not OperationStatus.COMPLETED or not rec.result_files:
        raise ApiError(code="OPERATION_BUSY",
                       message="Results are not ready yet.", status_code=409)
    zip_path = safe_join(rec.dir, f"{rec.id}.zip")
    if not zip_path.exists():
        out_dir = rec.dir / "out"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in rec.result_files:
                zf.write(out_dir / item.name, arcname=item.name)
    return FileResponse(
        zip_path, media_type="application/zip",
        filename=f"{rec.id}.zip",
        content_disposition_type="attachment",
    )


@router.get("/api/operations/{op_id}/download")
def download_file(op_id: str, name: str = Query(...)) -> FileResponse:
    rec = _require(op_id)
    if rec.status is not OperationStatus.COMPLETED:
        raise ApiError(code="OPERATION_BUSY",
                       message="Results are not ready yet.", status_code=409)
    out_dir = rec.dir / "out"
    path = safe_join(out_dir, name)
    if not path.is_file():
        raise ApiError(code="FILE_NOT_FOUND", message="Result file not found.",
                       details={"name": name}, status_code=404)
    return FileResponse(
        path, media_type="application/octet-stream",
        filename=name, content_disposition_type="attachment",
    )