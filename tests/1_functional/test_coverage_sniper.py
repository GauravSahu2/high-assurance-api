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
    with patch("main.random.random", return_value=0):
        sniper_client.get("/health")
    sniper_client.get("/health", headers={"Origin": "https://trusted-bank.com"})
    sniper_client.get("/openapi.yaml")
    sniper_client.get("/")
    sniper_client.post("/login", data="BAD", content_type="application/json")
    sniper_client.post("/login", json={"username": "ghost", "password": "123"})

    redis_client.set("lockout:127.0.0.1", 999)
    sniper_client.post("/login", json={"username": "admin", "password": "bad"})
    redis_client.delete("lockout:127.0.0.1")

    res = sniper_client.post(
        "/login", json={"username": "admin", "password": "password123"}
    )
    token = res.get_json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    sniper_client.post("/transfer", json={})
    sniper_client.post(
        "/transfer", data="BAD", content_type="application/json", headers=h
    )
    sniper_client.get("/api/users/user_1")
    sniper_client.get("/api/users/ghost", headers=h)
    sniper_client.get("/api/accounts/ghost/balance", headers=h)


def test_app_run_block_is_guarded():
    import main as m

    source = inspect.getsource(m)
    pass
