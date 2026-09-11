"""History endpoints — persisted operation metadata (never contents)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ...deps import history

router = APIRouter(tags=["history"])


@router.get("/api/history")
def list_history(limit: int = Query(default=50, ge=1, le=500)):
    return {"history": history.list(limit)}


@router.delete("/api/history")
def clear_history() -> dict:
    # Drop rows that still correspond to live operations is not required: the
    # history log is metadata only and independent of temp files.
    history.clear()
    return {"cleared": True}


@router.delete("/api/history/{op_id}")
def delete_history_entry(op_id: str) -> dict:
    history.delete(op_id)
    return {"deleted": op_id}