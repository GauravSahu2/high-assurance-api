import pytest
import redis
from unittest.mock import patch, MagicMock

def test_global_redis_error_handler(client):
    import fakeredis
    with patch.object(fakeredis.FakeStrictRedis, "get", side_effect=redis.RedisError("mock outage")):
        res = client.post("/login", json={"username": "admin", "password": "bad"})
    assert res.status_code == 503

def test_health_returns_503_when_redis_down(client):
    import fakeredis
    with patch.object(fakeredis.FakeStrictRedis, "ping", side_effect=redis.RedisError("down")):
        res = client.get("/health")
    assert res.status_code == 503

def test_health_returns_503_when_db_down(client):
    import sqlalchemy.orm
    with patch.object(sqlalchemy.orm.Session, "query", side_effect=Exception("Simulated")):
        res = client.get("/health")
    assert res.status_code == 503

def test_reset_state_production_guard(client):
    with patch.dict("os.environ", {}, clear=True):
        res = client.post("/test/reset")
    assert res.status_code == 404

def test_404_handler_is_covered(client):
    res = client.get("/this_route_does_not_exist_at_all")
    assert res.status_code == 404
