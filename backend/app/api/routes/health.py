"""Liveness / engine probe."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from ...schemas.common import HealthResponse
from ...core_loader import cc

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        engine=f"crypto-couples {cc.__doc__ or ''}",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )