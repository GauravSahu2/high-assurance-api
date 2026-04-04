import pytest
import redis
import os
from unittest.mock import patch
from main import app as flask_app

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c

def test_global_redis_error_handler(client):
    with patch("main.redis_client.get", side_effect=redis.RedisError("mock outage")):
        res = client.post("/login", json={"username": "admin", "password": "bad"})
        assert res.status_code == 503
        assert res.get_json()["error"] == "service temporarily degraded"

def test_reset_state_production_guard(client):
    with patch.dict(os.environ, {}, clear=True):
        res = client.post("/test/reset")
    assert res.status_code == 404

def test_404_handler_is_covered(client):
    res = client.get("/this_route_does_not_exist_at_all")
    assert res.status_code == 404

def test_health_returns_503_when_redis_down(client):
    with patch("main.redis_client.ping", side_effect=redis.RedisError("down")):
        res = client.get("/health")
    assert res.status_code == 503
    assert res.get_json()["infrastructure"] == "unreachable"

def test_health_returns_503_when_db_down(client):
    with patch("main.get_db", side_effect=Exception("Simulated DB Crash")):
        res = client.get("/health")
    assert res.status_code == 503
    assert res.get_json()["infrastructure"] == "unreachable"
