"""File (byte) split/reveal endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile, status

from ...deps import ops
from ...schemas.crypto import FileRevealOptions, FileSplitOptions
from ...schemas.operations import OperationSummary
from ...services.file_service import file_crypto
from ...services.validation_service import validation
from ._common import accept_uploads, summary

router = APIRouter(tags=["files"])


@router.post("/api/files/split", response_model=OperationSummary,
             status_code=status.HTTP_202_ACCEPTED)
async def split_file(
    files: list[UploadFile] = File(...),
    options: str = Form(default="{}"),
) -> OperationSummary:
    opts = validation.parse_options(options, FileSplitOptions)
    validation.check_count("files", len(files), 1, 1)
    rec = ops.create(kind="split", media="file", method=opts.method,
                     meta={"shares": opts.shares,
                           "threshold": opts.threshold,
                           "seed": opts.seed})
    await accept_uploads(rec, files, "files_split")
    ops.start(rec, lambda: file_crypto.split(rec, opts))
    return summary(rec)


@router.post("/api/files/reveal", response_model=OperationSummary,
             status_code=status.HTTP_202_ACCEPTED)
async def reveal_file(
    files: list[UploadFile] = File(...),
    options: str = Form(default="{}"),
) -> OperationSummary:
    opts = validation.parse_options(options, FileRevealOptions)
    validation.check_uploads("files_reveal", [f.filename for f in files])
    validation.check_count("files", len(files), 2, 16)
    rec = ops.create(kind="reveal", media="file", method=opts.method,
                     meta={"shares": len(files)})
    await accept_uploads(rec, files, "files_reveal")
    ops.start(rec, lambda: file_crypto.reveal(rec, opts))
    return summary(rec)