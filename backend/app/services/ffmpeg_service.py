"""FFmpeg availability + PATH injection so the core bridge honors FFMPEG_PATH.

The crypto core invokes ``ffmpeg`` / ``ffprobe`` by bare name. When
``Settings.ffmpeg_path`` is configured we prepend its directory to PATH so the
core bridge resolves it without modifying the core.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from ..config.settings import settings
from ..security.errors import ApiError

logger = logging.getLogger("crypto_couples.ffmpeg")


def inject_path() -> None:
    if settings.ffmpeg_path:
        binary = Path(settings.ffmpeg_path)
        if binary.exists():
            prefix = str(binary.parent) if binary.name in (
                "ffmpeg", "ffmpeg.exe") else str(binary)
            current = os.environ.get("PATH", "")
            if prefix and prefix not in current.split(os.pathsep):
                os.environ["PATH"] = prefix + os.pathsep + current
        else:
            logger.warning("FFMPEG_PATH points at a missing file: %s",
                           settings.ffmpeg_path)


def available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def require() -> None:
    if not available():
        raise ApiError(
            code="FFMPEG_MISSING",
            message="FFmpeg is required for video processing and is not "
                    "available on this server.",
        )