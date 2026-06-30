"""Concurrency utilities and custom ThreadPoolExecutor with queue monitoring."""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)


class LoggingThreadPoolExecutor(ThreadPoolExecutor):
    """A ThreadPoolExecutor that logs queue sizes when tasks are enqueued and when they finish."""

    def __init__(self, max_workers: int | None = None, thread_name_prefix: str = "", pool_name: str = ""):
        """Initialize the executor with optional pool name for logging identification."""
        super().__init__(max_workers=max_workers, thread_name_prefix=thread_name_prefix)
        self.pool_name = pool_name or thread_name_prefix or "ThreadPool"

    def get_queue_size(self) -> int:
        """Return the number of work items currently waiting in the internal work queue, or -1 if unavailable."""
        try:
            return self._work_queue.qsize()
        except BaseException:
            return -1

    def submit(self, fn, /, *args, **kwargs) -> Any:
        """Submit a task to the pool and log queue metrics on enqueue and completion."""
        future = super().submit(fn, *args, **kwargs)
        qsize = self.get_queue_size()
        logger.info(f"[{self.pool_name}] Task enqueued (queued items: {qsize})")

        def on_done(_):
            remaining = self.get_queue_size()
            logger.info(f"[{self.pool_name}] Task finished (queued items: {remaining})")

        future.add_done_callback(on_done)
        return future
