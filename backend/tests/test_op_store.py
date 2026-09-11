"""Operation store lifecycle + pub/sub fan-out."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from app.schemas.common import OperationStatus
from app.storage.op_store import OpRecord, OperationStore


def _rec(store: OperationStore) -> OpRecord:
    return store.create(op_id="t1", kind="split", media="image",
                        method="stack", directory=Path("/tmp/ops/t1"))


def test_create_get_list():
    store = OperationStore()
    rec = _rec(store)
    assert store.get("t1") is rec
    assert store.list()[0].id == "t1"


def test_apply_fanout():
    store = OperationStore()
    rec = _rec(store)
    events: list[dict] = []

    async def main():
        queue: asyncio.Queue = asyncio.Queue()
        listener = asyncio.create_task(queue.get())
        store.subscribe(rec, queue, asyncio.get_running_loop())
        store.apply(rec, status=OperationStatus.PROCESSING,
                    progress=42, message="splitting")
        store.apply(rec, status=OperationStatus.COMPLETED, progress=100)
        events.append(await listener)

    asyncio.run(main())
    assert events == [{"type": "progress", "progress": 42,
                       "message": "splitting", "error": None}]


def test_terminal_sets_finished_and_duration():
    store = OperationStore()
    rec = _rec(store)
    store.apply(rec, status=OperationStatus.PROCESSING)
    store.apply(rec, status=OperationStatus.COMPLETED, progress=100)
    assert rec.finished_at is not None
    assert rec.duration_ms is not None
    assert rec.is_terminal


def test_prune_marks_expired():
    store = OperationStore()
    rec = _rec(store)
    store.apply(rec, status=OperationStatus.COMPLETED)
    removed = store.prune(0)
    assert removed == [rec]
    assert rec.status is OperationStatus.EXPIRED
    assert store.get("t1") is None


def test_snapshot_terminal_types():
    store = OperationStore()
    rec = _rec(store)
    store.apply(rec, status=OperationStatus.COMPLETED)
    assert rec.snapshot()["type"] == "completed"
    rec2 = _rec2(store)
    store.apply(rec2, status=OperationStatus.FAILED)
    assert rec2.snapshot()["type"] == "error"


def _rec2(store: OperationStore) -> OpRecord:
    rec = store.create(op_id="t2", kind="split", media="audio",
                       method="xor", directory=Path("/tmp/ops/t2"))
    return rec