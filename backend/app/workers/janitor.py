"""TTL janitor: expires terminal operations and deletes their temp files.

Temporary files must not linger indefinitely; every operation directory is
removed once it is terminal and older than ``op_ttl_seconds``."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def janitor_loop(*, cleanup: object, interval_seconds: int, ttl_seconds: int) -> None:
    interval = min(interval_seconds, ttl_seconds)
    while True:
        await asyncio.sleep(max(1, interval))
        try:
            await asyncio.to_thread(cleanup)
        except Exception:  # pragma: no cover - janitor must never die
            logger.warning("janitor sweep failed", exc_info=True)