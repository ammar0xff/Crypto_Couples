"""FFmpeg availability probe.

Never silently install FFmpeg. Report presence/absence; the video feature
degrades gracefully when it is missing (see the FEATURE spec)."""

from __future__ import annotations

import shutil
import subprocess

from fastapi import APIRouter

from ...config.settings import settings
from ...schemas.common import FfmpegStatus

router = APIRouter(tags=["system"])


def _resolve_ffmpeg() -> str | None:
    if settings.ffmpeg_path:
        return settings.ffmpeg_path
    return shutil.which("ffmpeg")


def ffmpeg_available() -> bool:
    return _resolve_ffmpeg() is not None


@router.get("/api/system/ffmpeg", response_model=FfmpegStatus)
def ffmpeg_status() -> FfmpegStatus:
    path = _resolve_ffmpeg()
    version: str | None = None
    if path:
        try:
            out = subprocess.run(
                [path, "-version"], capture_output=True, text=True, timeout=5
            )
            if out.returncode == 0:
                version = out.stdout.splitlines()[0] if out.stdout else None
        except Exception:
            path = None
    return FfmpegStatus(available=path is not None, path=path, version=version)