import pytest
from main import app as flask_app
from main import failed_login_attempts


@pytest.fixture(autouse=True)
def reset_state():
    failed_login_attempts.clear()
    yield
    failed_login_attempts.clear()


def test_ip_based_brute_force_lockout():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        # 5 failed attempts
        for _ in range(5):
            res = c.post("/login", json={"username": "user_1", "password": "wrongpass"})
            assert res.status_code == 401
        # 6th attempt must be locked out
        res = c.post("/login", json={"username": "user_1", "password": "wrongpass"})
        assert res.status_code == 429
