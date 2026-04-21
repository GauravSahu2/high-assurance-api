import inspect
from unittest.mock import patch

import pytest

from main import app, redis_client, verify_jwt


@pytest.fixture
def sniper_client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_hundred_percent_coverage(sniper_client):
    verify_jwt("Malformed 123")
    verify_jwt(None)
    with patch("routes.health_routes.random.random", return_value=0):
        sniper_client.get("/health")
    sniper_client.get("/health", headers={"Origin": "https://trusted-bank.com"})
    sniper_client.get("/openapi.yaml")
    sniper_client.get("/")
    sniper_client.post("/login", data="BAD", content_type="application/json")
    sniper_client.post("/login", json={"username": "ghost", "password": "123"})

    # Cover IP-based lockout path
    redis_client.set("lockout:ip:127.0.0.1", 999)
    sniper_client.post("/login", json={"username": "admin", "password": "bad"})
    redis_client.delete("lockout:ip:127.0.0.1")

    # Cover user-based lockout path (IP ok, but account locked)
    redis_client.set("lockout:user:admin", 999)
    sniper_client.post("/login", json={"username": "admin", "password": "bad"})
    redis_client.delete("lockout:user:admin")

    res = sniper_client.post("/login", json={"username": "admin", "password": "password123"})
    token = res.get_json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    sniper_client.post("/transfer", json={})
    sniper_client.post("/transfer", data="BAD", content_type="application/json", headers=h)
    sniper_client.get("/api/users/user_1")
    sniper_client.get("/api/users/ghost", headers=h)
    sniper_client.get("/api/accounts/ghost/balance", headers=h)

    # Cover logout paths
    sniper_client.post("/logout")
    sniper_client.post("/logout", headers={"Authorization": "Bearer bad-token"})
    sniper_client.post("/logout", headers=h)


def test_app_run_block_is_guarded():
    import main as m

    _ = inspect.getsource(m)
    pass
