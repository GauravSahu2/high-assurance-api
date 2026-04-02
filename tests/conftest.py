import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest

os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("JWT_SECRET", "super-secure-dev-secret-key-12345")

from main import app as flask_app  # noqa: E402


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def token_factory():
    secret = os.environ.get("JWT_SECRET", "super-secure-dev-secret-key-12345")

    def make(username="user_1", role="user"):
        payload = {
            "sub": username,
            "role": role,
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    return make


@pytest.fixture
def auth_header(token_factory):
    token = token_factory("admin", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_state_between_tests():
    """Resets Redis state before and after every test."""
    import main as _main

    _main.redis_client.flushdb()
    _main.init_db()
    yield
    _main.redis_client.flushdb()
    _main.init_db()
