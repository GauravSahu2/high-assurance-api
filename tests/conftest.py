import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from hypothesis import HealthCheck, settings

os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("JWT_SECRET", "super-secure-dev-secret-key-123456789012345678901234")

# ── Suppress OTel teardown noise ──────────────────────────────────────────────
# The ConsoleSpanExporter writes to stdout which is closed during pytest
# teardown, causing a harmless but noisy ValueError. Shut it down cleanly.
import atexit

from opentelemetry import trace as _otel_trace

import main as _main
from main import app as flask_app


def _shutdown_otel():
    provider = _otel_trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        try:
            provider.shutdown()
        except Exception:
            pass

atexit.register(_shutdown_otel)

# Register profiles for your two chosen loops
settings.register_profile("thorough", max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
settings.load_profile("thorough")

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c

@pytest.fixture
def token_factory():
    def make(username="user_1", role="user"):
        payload = {
            "sub": username,
            "role": role,
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, _main.JWT_SECRET, algorithm="HS256")
    return make

@pytest.fixture
def auth_header(token_factory):
    return {"Authorization": f"Bearer {token_factory('admin', 'admin')}"}

@pytest.fixture(autouse=True)
def reset_state_between_tests():
    import gc
    gc.collect()
    try: _main.redis_client.flushdb()
    except Exception: pass
    db = next(_main.get_db())
    db.query(_main.OutboxEvent).delete()
    db.query(_main.IdempotencyKey).delete()
    db.query(_main.Account).delete()
    db.commit()
    try: _main.init_db()
    except Exception: db.rollback()
    yield
    try: _main.redis_client.flushdb()
    except Exception: pass
    db = next(_main.get_db())
    db.query(_main.OutboxEvent).delete()
    db.query(_main.IdempotencyKey).delete()
    db.query(_main.Account).delete()
    db.commit()
    try: _main.init_db()
    except Exception: db.rollback()

# ── xdist per-worker database isolation ───────────────────────────────────────
def pytest_configure(config):
    """Give each xdist worker its own SQLite file to prevent race conditions."""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
    if worker_id != "master":
        os.environ["TEST_DB_PATH"] = f"./test_{worker_id}.db"
    else:
        os.environ["TEST_DB_PATH"] = "./test.db"
