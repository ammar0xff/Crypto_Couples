"""Audio split/reveal endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile, status

from ...deps import ops
from ...schemas.crypto import AudioRevealOptions, AudioSplitOptions
from ...schemas.operations import OperationSummary
from ...services.audio_service import audio_crypto
from ...services.validation_service import validation
from ._common import accept_uploads, summary

router = APIRouter(tags=["audio"])


@router.post("/api/audio/split", response_model=OperationSummary,
             status_code=status.HTTP_202_ACCEPTED)
async def split_audio(
    files: list[UploadFile] = File(...),
    options: str = Form(default="{}"),
) -> OperationSummary:
    opts = validation.parse_options(options, AudioSplitOptions)
    validation.check_uploads("audio", [f.filename for f in files])
    validation.check_count("audio", len(files), 1, 1)
    rec = ops.create(kind="split", media="audio", method=opts.method,
                     meta={"shares": opts.shares,
                           "threshold": opts.threshold,
                           "seed": opts.seed})
    await accept_uploads(rec, files, "audio")
    ops.start(rec, lambda: audio_crypto.split(rec, opts))
    return summary(rec)


@router.post("/api/audio/reveal", response_model=OperationSummary,
             status_code=status.HTTP_202_ACCEPTED)
async def reveal_audio(
    files: list[UploadFile] = File(...),
    options: str = Form(default="{}"),
) -> OperationSummary:
    opts = validation.parse_options(options, AudioRevealOptions)
    validation.check_uploads("audio", [f.filename for f in files])
    validation.check_count("audio", len(files), 2, 16)
    rec = ops.create(kind="reveal", media="audio", method=opts.method,
                     meta={"shares": len(files)})
    await accept_uploads(rec, files, "audio")
    ops.start(rec, lambda: audio_crypto.reveal(rec, opts))
    return summary(rec)