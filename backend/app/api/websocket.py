"""Per-operation WebSocket progress feed with a pollable snapshot fallback.

The client may subscribe immediately after creating an operation; the server
sends the current snapshot first, then pushes progress/completed/error events.
If WebSockets are unavailable the frontend falls back to
``GET /api/operations/{op_id}``."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..deps import ops

logger = logging.getLogger(__name__)
router = APIRouter()

_EVENTS = ("completed", "error", "cancelled")


@router.websocket("/api/operations/{op_id}/ws")
async def operation_ws(ws: WebSocket, op_id: str) -> None:
    await ws.accept()
    rec = ops.store.get(op_id)
    if rec is None:
        await ws.send_json({
            "type": "error",
            "error": {"code": "OPERATION_NOT_FOUND",
                      "message": "Unknown operation.", "details": {}},
        })
        await ws.close(code=4404)
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    ops.store.subscribe(rec, queue, loop)
    try:
        await ws.send_json(rec.snapshot())
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                await ws.send_json({
                    "type": "progress", "progress": rec.progress,
                    "message": rec.message,
                })
                continue
            await ws.send_json(event)
            if event.get("type") in _EVENTS:
                break
    except WebSocketDisconnect:
        pass
    except Exception:  # pragma: no cover
        logger.warning("ws error for %s", op_id, exc_info=True)
    finally:
        ops.store.unsubscribe(rec, queue)
        try:
            await ws.close()
        except Exception:
            pass