import threading
from concurrent.futures import ThreadPoolExecutor


class MockDatabasePool:
    def __init__(self, max_connections):
        self._max = max_connections
        self._sem = threading.Semaphore(max_connections)
        self._lock = threading.Lock()
        self.active_connections = 0

    def get_connection(self):
        acquired = self._sem.acquire(blocking=False)
        if not acquired:
            raise Exception("Pool exhausted")
        with self._lock:
            self.active_connections += 1
        return True

    def release_connection(self):
        with self._lock:
            self.active_connections -= 1
        self._sem.release()


def test_db_pool_concurrency_and_exhaustion():
    """
    Proves pool exhaustion by design:
    1. Saturate pool completely (hold all connections open)
    2. Fire overflow workers — they MUST fail because pool is full
    3. Release all held connections
    4. Verify zero active connections (no memory leak)
    """
    POOL_SIZE = 10
    OVERFLOW = 5
    pool = MockDatabasePool(max_connections=POOL_SIZE)

    # Phase 1: Saturate — hold all POOL_SIZE connections open simultaneously
    held = []
    for _ in range(POOL_SIZE):
        pool.get_connection()
        held.append(True)

    assert pool.active_connections == POOL_SIZE

    # Phase 2: Overflow — these MUST fail because pool is full
    successes = 0
    failures = 0
    result_lock = threading.Lock()

    def overflow_worker():
        nonlocal successes, failures
        try:
            pool.get_connection()
            with result_lock:
                successes += 1
            pool.release_connection()
        except Exception:
            with result_lock:
                failures += 1

    with ThreadPoolExecutor(max_workers=OVERFLOW) as executor:
        futures = [executor.submit(overflow_worker) for _ in range(OVERFLOW)]
        for f in futures:
            f.result()

    assert successes == 0, f"Expected 0 successes while pool saturated, got {successes}"
    assert failures == OVERFLOW, f"Expected {OVERFLOW} failures, got {failures}"

    # Phase 3: Release all held connections
    for _ in held:
        pool.release_connection()

    assert pool.active_connections == 0  # Memory leak check: Pool must cleanly release all
