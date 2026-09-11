"""Thread-safe in-memory operation store with per-op WebSocket fan-out.

Worker threads report progress through ``apply``/``broadcast``; each operation
keeps a list of (asyncio.Queue, event_loop) subscribers and events are pushed
with ``loop.call_soon_threadsafe`` so the WS handler can also be used when the
worker is not the event-loop thread.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..schemas.common import OperationStatus
from ..schemas.operations import ErrorPayload, ResultFile

TERMINAL = {
    OperationStatus.COMPLETED,
    OperationStatus.FAILED,
    OperationStatus.CANCELLED,
    OperationStatus.EXPIRED,
}

_TASK_TYPES = {
    "completed": "completed",
    "failed": "error",
    "error": "error",
    "cancelled": "cancelled",
}.get


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class OpRecord:
    id: str
    kind: str  # split | reveal
    media: str  # image | audio | video | file
    method: str | None
    dir: Path
    meta: dict = field(default_factory=dict)
    status: OperationStatus = OperationStatus.QUEUED
    progress: int = 0
    message: str = "queued"
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    input_names: list[str] = field(default_factory=list)
    result_files: list[ResultFile] = field(default_factory=list)
    error: ErrorPayload | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    _subscribers: list = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL

    def snapshot(self) -> dict:
        return {
            "type": "progress" if not self.is_terminal else _TASK_TYPES(
                self.status.value, "progress"
            ),
            "progress": self.progress,
            "message": self.message,
            "error": self.error.model_dump() if self.error else None,
        }


class OperationStore:
    def __init__(self) -> None:
        self._ops: dict[str, OpRecord] = {}
        self._lock = threading.RLock()

    def create(self, *, op_id: str, kind: str, media: str, method: str | None,
               directory: Path) -> OpRecord:
        rec = OpRecord(id=op_id, kind=kind, media=media, method=method, dir=directory)
        with self._lock:
            self._ops[op_id] = rec
        return rec

    def get(self, op_id: str) -> OpRecord | None:
        with self._lock:
            return self._ops.get(op_id)

    def list(self, limit: int = 50) -> list[OpRecord]:
        with self._lock:
            ordered = sorted(
                self._ops.values(), key=lambda r: r.created_at, reverse=True
            )
            return ordered[:limit]

    def apply(self, rec: OpRecord, *, status: OperationStatus | None = None,
              progress: int | None = None, message: str | None = None,
              error: ErrorPayload | None = None, **extra) -> dict:
        with self._lock:
            if status is not None:
                rec.status = status
                if status is OperationStatus.PROCESSING and rec.started_at is None:
                    rec.started_at = utcnow()
                if status in TERMINAL and rec.finished_at is None:
                    rec.finished_at = utcnow()
                    rec.duration_ms = int(
                        (rec.finished_at - rec.created_at).total_seconds() * 1000
                    )
            if progress is not None:
                rec.progress = progress
            if message is not None:
                rec.message = message
            if error is not None:
                rec.error = error
            for key, value in extra.items():
                setattr(rec, key, value)
            rec.updated_at = utcnow()
            event = rec.snapshot()
            subs = list(rec._subscribers)
        for queue, loop in subs:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, dict(event))
            except RuntimeError:
                pass
        return event

    def subscribe(self, rec: OpRecord, queue, loop) -> None:
        with self._lock:
            rec._subscribers.append((queue, loop))

    def unsubscribe(self, rec: OpRecord, queue) -> None:
        with self._lock:
            rec._subscribers = [
                (q, l) for (q, l) in rec._subscribers if q is not queue
            ]

    def prune(self, ttl_seconds: int) -> list[OpRecord]:
        cutoff = utcnow().timestamp() - ttl_seconds
        removed: list[OpRecord] = []
        with self._lock:
            for rec in list(self._ops.values()):
                ref = rec.finished_at or rec.updated_at
                if rec.is_terminal and ref.timestamp() < cutoff:
                    rec.status = OperationStatus.EXPIRED
                    removed.append(rec)
                    del self._ops[rec.id]
        return removed