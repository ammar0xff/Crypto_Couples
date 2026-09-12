"""FastAPI application factory.

API-only backend. The cryptographic core stays in crypto_couples.py /
crypto_media.py and is reached exclusively through the service layer.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from . import deps
from .api.routes import audio, files, health, history, images, operations, system, video
from .api.websocket import router as ws_router
from .config.settings import settings
from .security.errors import ApiError
from .services.ffmpeg_service import inject_path
from .workers.janitor import janitor_loop

logger = logging.getLogger("crypto_couples")

_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
_INDEX = _DIST / "index.html"


def _content_security_policy() -> str:
    """API responses carry a strict CSP.

    The PWA document's own CSP is served by its static host and covers
    connect-src *to* this API, so this only needs to constrain API responses.
    """
    if settings.app_env == "development":
        connect = "'self' ws://localhost:* ws://127.0.0.1:*"
    else:
        connect = "'self'"
    return (
        "default-src 'none'; "
        f"connect-src {connect}; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = _content_security_policy()
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    deps.ops.settings.temp_directory.mkdir(parents=True, exist_ok=True)
    deps.ops.cleanup_all()  # stale temp dirs from previous runs
    janitor = asyncio.create_task(
        janitor_loop(
            cleanup=deps.ops.cleanup_expired,
            interval_seconds=max(1, settings.op_ttl_seconds // 2),
            ttl_seconds=settings.op_ttl_seconds,
        )
    )
    yield
    janitor.cancel()
    deps.executor.shutdown()


def create_app() -> FastAPI:
    inject_path()

    app = FastAPI(
        title="Crypto Couples",
        description="Visual cryptography and secret sharing (API adapter).",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    allowed = list(settings.frontend_origins)
    if settings.app_env == "development":
        allowed = list(dict.fromkeys([*allowed, "http://localhost:5173",
                                     "http://127.0.0.1:5173"]))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    for router in (health.router, system.router, operations.router,
                   history.router, images.router, audio.router,
                   files.router, video.router, ws_router):
        app.include_router(router)

    @app.get("/", include_in_schema=False)
    def root() -> Response | dict:
        if _INDEX.is_file():
            return FileResponse(_INDEX)
        return {"app": "Crypto Couples", "api": "/api", "docs": "/api/docs"}

    @app.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(exc.envelope(), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = {
            str(e["loc"]): e.get("msg", "") for e in exc.errors()
        }
        return JSONResponse(
            {"error": {"code": "INVALID_PARAMETER",
                       "message": "One or more parameters are invalid.",
                       "details": details}},
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        return JSONResponse(
            {"error": {"code": code, "message": str(exc.detail), "details": {}}},
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("unhandled error")
        return JSONResponse(
            {"error": {"code": "INTERNAL",
                       "message": "Something went wrong on the server.",
                       "details": {}}},
            status_code=500,
        )

    return app


app = create_app()