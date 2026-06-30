import logging
import time

from podscribe.concurrency import LoggingThreadPoolExecutor


def test_logging_thread_pool_executor_queue_logging(caplog):
    caplog.set_level(logging.INFO)
    executor = LoggingThreadPoolExecutor(max_workers=1, pool_name="TestPool")

    def slow_task():
        time.sleep(0.05)

    f1 = executor.submit(slow_task)
    f2 = executor.submit(slow_task)

    f1.result()
    f2.result()
    executor.shutdown(wait=True)

    log_messages = [r.message for r in caplog.records if "TestPool" in r.message]
    assert any("Task enqueued" in m for m in log_messages)
    assert any("Task finished" in m for m in log_messages)


def test_get_queue_size_handles_exceptions():
    executor = LoggingThreadPoolExecutor(max_workers=1)

    # Test when _work_queue is missing
    del executor._work_queue
    assert executor.get_queue_size() == -1

    # Test when qsize() raises an exception
    class BrokenQueue:
        def qsize(self):
            raise NotImplementedError("Queue implementation changed")

    executor._work_queue = BrokenQueue()
    assert executor.get_queue_size() == -1
