"""Runtime configuration from environment variables.

Never hardcode production URLs. Every backend setting has a safe default
appropriate for local development and can be overridden through the
environment (see .env.example / docs).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_env: str = os.environ.get("APP_ENV", "development").strip() or "development"
    host: str = os.environ.get("HOST", "127.0.0.1").strip() or "127.0.0.1"
    port: int = _env_int("PORT", 8000)

    # CORS is explicit. Production must set FRONTEND_ORIGIN; no wildcard.
    frontend_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip()
            for o in os.environ.get("FRONTEND_ORIGIN", "").split(",")
            if o.strip()
        )
        or ("http://localhost:5173", "http://127.0.0.1:5173")
    )

    max_upload_size: int = _env_int("MAX_UPLOAD_SIZE", 512 * 1024 * 1024)
    temp_directory: Path = Path(
        os.environ.get("TEMP_DIRECTORY", "backend/data/ops")
    ).resolve()
    history_path: Path = Path("backend/data/history.db").resolve()
    ffmpeg_path: str | None = (
        os.environ.get("FFMPEG_PATH", "").strip() or None
    )
    op_ttl_seconds: int = _env_int("OP_TTL_SECONDS", 3600)


settings = Settings()