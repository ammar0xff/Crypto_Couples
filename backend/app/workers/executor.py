"""Background operation runner.

Long-running crypto work is executed off the event loop on a bounded thread
pool so API requests never block on processing."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor


class OpExecutor:
    def __init__(self, max_workers: int = 2) -> None:
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="crypto-op"
        )

    def submit(self, fn) -> Future:
        return self._pool.submit(fn)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=False)