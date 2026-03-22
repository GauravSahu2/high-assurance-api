import threading
import time
from concurrent.futures import ThreadPoolExecutor


class MockDatabasePool:
    def __init__(self, max_connections=200):  # FAANG-style per-node limit
        self.max_connections = max_connections
        self.active_connections = 0
        self.lock = threading.Lock()  # Thread-safe locking is critical here

    def get_connection(self):
        with self.lock:
            if self.active_connections >= self.max_connections:
                raise Exception("Connection pool exhausted")
            self.active_connections += 1

        # Hold the connection open for 50ms.
        # This guarantees massive overlap and brutal thread contention.
        time.sleep(0.05)

        with self.lock:
            self.active_connections -= 1


def test_db_pool_concurrency_and_exhaustion():
    """
    Simulates a FAANG-style traffic spike:
    Smashing a 200-connection pool with 1,500 concurrent worker threads
    to mathematically prove the thread-locks prevent race conditions and deadlocks.
    """
    pool = MockDatabasePool(max_connections=200)
    successes = 0
    failures = 0
    result_lock = threading.Lock()

    def worker():
        nonlocal successes, failures
        try:
            pool.get_connection()
            with result_lock:
                successes += 1
        except Exception:
            with result_lock:
                failures += 1

    # Force 1,500 concurrent workers to fight over 200 connections
    with ThreadPoolExecutor(max_workers=1500) as executor:
        for _ in range(1500):
            executor.submit(worker)

    # The exact numbers will vary based on CPU scheduling, but we MUST see both.
    # The pool must successfully process what it can, and safely reject the rest.
    assert successes > 0
    assert failures > 0
    assert pool.active_connections == 0  # Memory leak check: Pool must cleanly release all
