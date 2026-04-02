import pytest
from main import app as flask_app
from main import redis_client


@pytest.fixture(autouse=True)
def reset_state():
    redis_client.flushdb()
    yield
    redis_client.flushdb()


def test_ip_based_brute_force_lockout():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        for _ in range(5):
            res = c.post("/login", json={"username": "user_1", "password": "wrongpass"})
            assert res.status_code == 401
        res = c.post("/login", json={"username": "user_1", "password": "wrongpass"})
        assert res.status_code == 429
