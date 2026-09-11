"""Vercel function entrypoint.

Runs the FastAPI backend as a serverless Python function and serves the built
PWA (frontend/dist) from the same origin so the SPA can use relative /api URLs.

Serverless constraints (honest limits):
  - Filesystem is per-instance and ephemeral: temp shares and history live in
    /tmp only, mapped from TEMP_DIRECTORY / HISTORY_PATH.
  - No WebSocket support: the SPA already falls back to REST detail polling.
  - Request bodies are capped by the platform (small images/audio fine; video
    splits belong on the self-hosted uvicorn deployment).

Env vars are set with setdefault() so Vercel dashboard envs take precedence.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("TEMP_DIRECTORY", "/tmp/crypto_couples/ops")
os.environ.setdefault("HISTORY_PATH", "/tmp/crypto_couples/history.db")
os.environ.setdefault("OP_TTL_SECONDS", "3600")

from fastapi import HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from starlette.responses import Response  # noqa: E402

from app.main import app  # noqa: E402

_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _DIST.is_dir():

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str) -> Response:
        """Serve PWA static files, with index.html fallback for client routes."""
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        full = _DIST / path
        if path and full.is_file():
            return FileResponse(full)
        index = _DIST / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(index)