"""Shared singletons: store, history, executor, operation service."""

from __future__ import annotations

from .config.settings import settings
from .services.operation_service import OperationService
from .storage.history import HistoryStore
from .storage.op_store import OperationStore
from .workers.executor import OpExecutor

store = OperationStore()
history = HistoryStore(settings.history_path)
executor = OpExecutor()
ops = OperationService(store, history, executor, settings)