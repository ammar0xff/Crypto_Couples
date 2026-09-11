"""Video split/reveal endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile, status

from ...deps import ops
from ...schemas.crypto import VideoRevealOptions, VideoSplitOptions
from ...schemas.operations import OperationSummary
from ...services.validation_service import validation
from ...services.video_service import video_crypto
from ._common import accept_uploads, summary

router = APIRouter(tags=["video"])


@router.post("/api/video/split", response_model=OperationSummary,
             status_code=status.HTTP_202_ACCEPTED)
async def split_video(
    files: list[UploadFile] = File(...),
    options: str = Form(default="{}"),
) -> OperationSummary:
    opts = validation.parse_options(options, VideoSplitOptions)
    validation.check_uploads("video_split", [f.filename for f in files])
    validation.check_count("video", len(files), 1, 1)
    rec = ops.create(kind="split", media="video", method=opts.method,
                     meta={"shares": opts.shares, "fps": opts.fps,
                           "audio_method": opts.audio_method,
                           "seed": opts.seed})
    await accept_uploads(rec, files, "video_split")
    ops.start(rec, lambda: video_crypto.split(rec, opts))
    return summary(rec)


@router.post("/api/video/reveal", response_model=OperationSummary,
             status_code=status.HTTP_202_ACCEPTED)
async def reveal_video(
    files: list[UploadFile] = File(...),
    options: str = Form(default="{}"),
) -> OperationSummary:
    opts = validation.parse_options(options, VideoRevealOptions)
    validation.check_uploads("video_reveal", [f.filename for f in files])
    validation.check_count("video", len(files), 2, 8)
    rec = ops.create(kind="reveal", media="video", method=opts.method,
                     meta={"shares": len(files)})
    await accept_uploads(rec, files, "video_reveal")
    ops.start(rec, lambda: video_crypto.reveal(rec, opts))
    return summary(rec)