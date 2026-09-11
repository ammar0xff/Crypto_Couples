"""Operation orchestration: create ops, store uploads, run workers, record
history, expire temp directories."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import UploadFile

from ..config.settings import Settings
from ..schemas.common import OperationStatus
from ..schemas.operations import ErrorPayload, ResultFile
from ..security.errors import ApiError
from ..security.files import new_token, safe_join, sanitize_filename
from ..storage.history import HistoryStore
from ..storage.op_store import OpRecord, OperationStore, TERMINAL
from ..workers.executor import OpExecutor


def _natural_key(name: str):
    import re

    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


class OperationService:
    def __init__(self, store: OperationStore, history: HistoryStore,
                 executor: OpExecutor, settings: Settings) -> None:
        self.store = store
        self.history = history
        self.executor = executor
        self.settings = settings
        self.settings.temp_directory.mkdir(parents=True, exist_ok=True)

    # -- lifecycle -----------------------------------------------------------
    def create(self, *, kind: str, media: str, method: str | None = None,
               meta: dict | None = None) -> OpRecord:
        op_id = new_token("op")
        directory = self.settings.temp_directory / op_id
        (directory / "input").mkdir(parents=True, exist_ok=True)
        (directory / "out").mkdir(parents=True)
        rec = self.store.create(
            op_id=op_id, kind=kind, media=media, method=method, directory=directory
        )
        rec.meta = meta or {}
        return rec

    async def save_upload(self, rec: OpRecord, upload: UploadFile,
                          expected_suffixes: tuple[str, ...] | None = None) -> str:
        name = sanitize_filename(upload.filename)
        suffix = Path(name).suffix.lower()
        if expected_suffixes and suffix not in expected_suffixes:
            allowed = ", ".join(expected_suffixes) if expected_suffixes else "any"
            raise ApiError(
                code="INVALID_FILE_TYPE",
                message=f"Unsupported file type '{suffix or '(none)'}'. Expected: {allowed}.",
                details={"file": name},
            )
        path = safe_join(rec.dir / "input", name)
        self.store.apply(rec, status=OperationStatus.UPLOADING,
                         progress=0, message=f"Uploading {name}")
        total = 0
        with open(path, "wb") as out:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > self.settings.max_upload_size:
                    out.close()
                    path.unlink(missing_ok=True)
                    raise ApiError(
                        code="UPLOAD_TOO_LARGE",
                        message="The uploaded file exceeds the size limit.",
                        details={"limit_bytes": self.settings.max_upload_size},
                        status_code=413,
                    )
                out.write(chunk)
        rec.input_names.append(name)
        return name

    def start(self, rec: OpRecord, run) -> None:
        self.store.apply(rec, status=OperationStatus.PROCESSING,
                         progress=0, message="Starting crypto engine")
        future = self.executor.submit(run)
        future.add_done_callback(lambda fut: self._on_done(rec, fut))

    def _on_done(self, rec: OpRecord, future) -> None:
        if rec.status is OperationStatus.CANCELLED:
            return
        try:
            future.result()
        except ApiError as error:
            if error.code != "CANCELLED":
                self.fail(rec, error)
        except Exception as error:  # never leak raw traces to clients
            self.fail(rec, ApiError(
                code="INTERNAL",
                message="The crypto engine failed unexpectedly.",
                details={"hint": type(error).__name__},
                status_code=500,
            ))

    def report(self, rec: OpRecord, progress: int, message: str) -> None:
        self.store.apply(rec, status=OperationStatus.PROCESSING,
                         progress=progress, message=message)

    def finish(self, rec: OpRecord) -> None:
        out_dir = rec.dir / "out"
        files = sorted(
            (p.name for p in out_dir.iterdir() if p.is_file()),
            key=_natural_key,
        )
        rec.result_files = [
            ResultFile(name=name, size=(out_dir / name).stat().st_size)
            for name in files
        ]
        self.store.apply(rec, status=OperationStatus.COMPLETED,
                         progress=100, message="Completed")
        self._record_history(rec)

    def fail(self, rec: OpRecord, error: ApiError) -> None:
        if rec.is_terminal:
            return
        self.store.apply(
            rec,
            status=OperationStatus.FAILED,
            progress=rec.progress,
            message=error.message,
            error=ErrorPayload(code=error.code, message=error.message,
                               details=error.details),
        )
        self._record_history(rec)

    def cancel(self, rec: OpRecord) -> None:
        if rec.is_terminal:
            return
        rec.cancel_event.set()
        self.store.apply(rec, status=OperationStatus.CANCELLED,
                         message="Cancelled")
        self._record_history(rec)

    def _record_history(self, rec: OpRecord) -> None:
        self.history.record_terminal(rec)

    # -- cleanup ---------------------------------------------------------------
    def cleanup_expired(self) -> None:
        for rec in self.store.prune(self.settings.op_ttl_seconds):
            shutil.rmtree(rec.dir, ignore_errors=True)

    def cleanup_all(self) -> None:
        """Remove every temp directory (used at startup and in tests)."""
        for child in self.settings.temp_directory.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)