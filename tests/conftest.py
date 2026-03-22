import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest

os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("JWT_SECRET", "super-secure-dev-secret-key-12345")

from main import app as flask_app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def auth_header(token_factory):
    token = token_factory("admin", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_state_between_tests():
    """Resets module-level state before and after every test.
    Uses runtime import so mutmut trampoline and normal pytest
    both reset the same live dict objects."""
    import main as _main

    _main.failed_login_attempts.clear()
    _main.processed_transactions.clear()
    _main.accounts["user_1"] = 1000.0
    _main.accounts["user_2"] = 500.0
    yield
    _main.failed_login_attempts.clear()
    _main.processed_transactions.clear()
    _main.accounts["user_1"] = 1000.0
    _main.accounts["user_2"] = 500.0
