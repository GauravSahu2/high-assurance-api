import os
from unittest.mock import patch

import pytest
import redis
from main import app as flask_app
from main import generate_jwt


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_global_redis_error_handler(client):
    """Force a Redis outage to bubble up to the global 503 handler."""
    with patch("main.redis_client.get", side_effect=redis.RedisError("mock outage")):
        token = generate_jwt("admin")
        res = client.get(
            "/api/accounts/admin/balance", headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 503
        assert res.get_json()["error"] == "service temporarily degraded"


def test_reset_state_production_guard(client):
    """Ensure the /test/reset endpoint guards itself when not in TEST_MODE."""
    with patch.dict(os.environ, {}, clear=True):
        res = client.post("/test/reset")
        assert res.status_code == 404


def test_404_handler_is_covered(client):
    """Hits a non-existent route to trigger the global 404 handler."""
    res = client.get("/this_route_does_not_exist_at_all")
    assert res.status_code == 404
    assert "not found" in res.get_json()["error"]


def test_health_returns_503_when_redis_down(client):
    """Covers the redis.RedisError branch in /health."""
    import redis as redis_lib

    with patch("main.redis_client.ping", side_effect=redis_lib.RedisError("down")):
        res = client.get("/health")
    assert res.status_code == 503
    assert res.get_json()["redis"] == "unreachable"
