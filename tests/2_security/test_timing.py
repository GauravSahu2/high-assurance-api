import time

import pytest
from main import app as flask_app
from main import failed_login_attempts


@pytest.fixture(autouse=True)
def reset_state():
    failed_login_attempts.clear()
    yield
    failed_login_attempts.clear()


def test_login_timing_leak_protection():
    """Existing and ghost usernames must take similar time (constant-time check)."""
    flask_app.config["TESTING"] = True
    existing_times, ghost_times = [], []
    batch = 2
    cycles = 10

    with flask_app.test_client() as c:
        for _ in range(cycles):
            failed_login_attempts.clear()
            for _ in range(batch):
                t0 = time.perf_counter()
                c.post("/login", json={"username": "user_1", "password": "wrongpass"})
                existing_times.append(time.perf_counter() - t0)

            failed_login_attempts.clear()
            for _ in range(batch):
                t0 = time.perf_counter()
                c.post("/login", json={"username": "ghost_user_xyz", "password": "wrongpass"})
                ghost_times.append(time.perf_counter() - t0)

    avg_existing = sum(existing_times) / len(existing_times)
    avg_ghost = sum(ghost_times) / len(ghost_times)
    ratio = max(avg_existing, avg_ghost) / max(min(avg_existing, avg_ghost), 1e-9)
    assert ratio < 3.0, f"Timing leak detected: existing={avg_existing:.4f}s ghost={avg_ghost:.4f}s ratio={ratio:.2f}"
