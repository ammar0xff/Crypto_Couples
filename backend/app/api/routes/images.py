"""Image split/reveal endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile, status

from ...deps import ops
from ...schemas.crypto import ImageRevealOptions, ImageSplitOptions
from ...schemas.operations import OperationSummary
from ...services.image_service import image_crypto
from ...services.validation_service import validation
from ._common import accept_uploads, summary

router = APIRouter(tags=["images"])


@router.post("/api/images/split", response_model=OperationSummary,
             status_code=status.HTTP_202_ACCEPTED)
async def split_image(
    files: list[UploadFile] = File(...),
    options: str = Form(default="{}"),
) -> OperationSummary:
    opts = validation.parse_options(options, ImageSplitOptions)
    validation.check_uploads("image", [f.filename for f in files])
    validation.check_count("image", len(files), 1, 1)
    rec = ops.create(kind="split", media="image", method=opts.method,
                     meta={"shares": opts.shares, "threshold": opts.threshold,
                           "seed": opts.seed})
    await accept_uploads(rec, files, "image")
    ops.start(rec, lambda: image_crypto.split(rec, opts))
    return summary(rec)


@router.post("/api/images/reveal", response_model=OperationSummary,
             status_code=status.HTTP_202_ACCEPTED)
async def reveal_image(
    files: list[UploadFile] = File(...),
    options: str = Form(default="{}"),
) -> OperationSummary:
    opts = validation.parse_options(options, ImageRevealOptions)
    validation.check_uploads("image", [f.filename for f in files])
    validation.check_count("image", len(files), 2, 8)
    rec = ops.create(kind="reveal", media="image", method=opts.method,
                     meta={"shares": len(files)})
    await accept_uploads(rec, files, "image")
    ops.start(rec, lambda: image_crypto.reveal(rec, opts))
    return summary(rec)