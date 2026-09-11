"""SQLite-backed operation history.

Stores **metadata only** — never payload bytes, never secret content. Rows are
written when an operation reaches a terminal state so partial/failed attempts
leave a trace without bloating the file.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from ..storage.op_store import OpRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS operations (
    id TEXT PRIMARY KEY,
    kind TEXT, media TEXT, method TEXT,
    file_name TEXT,
    shares INTEGER, threshold INTEGER, seed INTEGER,
    status TEXT, message TEXT,
    created_at TEXT, started_at TEXT, finished_at TEXT,
    duration_ms INTEGER, result_count INTEGER
)
"""


class HistoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        with self._lock:
            self._conn.execute(_SCHEMA)
            self._conn.commit()

    def record_terminal(self, rec: OpRecord) -> None:
        if not rec.is_terminal:
            return
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        rows = (
            rec.id,
            rec.kind,
            rec.media,
            rec.method,
            ",".join(rec.input_names) if rec.input_names else None,
            rec.meta.get("shares"),
            rec.meta.get("threshold"),
            rec.meta.get("seed"),
            rec.status.value,
            rec.message,
            rec.created_at.strftime(fmt),
            rec.started_at.strftime(fmt) if rec.started_at else None,
            rec.finished_at.strftime(fmt) if rec.finished_at else None,
            rec.duration_ms,
            len(rec.result_files),
        )
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO operations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                rows,
            )
            self._conn.commit()

    def list(self, limit: int = 50) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id,kind,media,method,file_name,status,created_at,duration_ms,"
                "result_count FROM operations ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def delete(self, op_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM operations WHERE id = ?", (op_id,))
            self._conn.commit()

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM operations")
            self._conn.commit()