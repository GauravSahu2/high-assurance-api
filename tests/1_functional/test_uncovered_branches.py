import os
from unittest.mock import patch

import pytest
from main import app as flask_app
from main import generate_jwt


@pytest.fixture()
def anon_client():
    """Minimal client with no conftest setup — for auth/chaos tests."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# Line 142 — /transfer with invalid JWT -> 401 (auth check first)
def test_transfer_unknown_token_returns_401(anon_client):
    res = anon_client.post(
        "/transfer",
        json={"from_account": "A1", "to_account": "B2", "amount": 10},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert res.status_code == 401


# Lines 72-73 — chaos monkey: patch CHAOS_MODE env AND random.random
def test_chaos_monkey_returns_503(anon_client):
    with patch.dict(os.environ, {"CHAOS_MODE": "true"}):
        with patch("random.random", return_value=0.0):
            res = anon_client.get("/health")
    assert res.status_code == 503


# Line 86 — CORS allows a whitelisted origin to get the header echoed back
def test_cors_allowed_origin_gets_header(anon_client):
    res = anon_client.options("/health", headers={"Origin": "http://localhost:3000"})
    assert "Access-Control-Allow-Origin" in res.headers


# Line 120 — /login with malformed JSON body -> 400
def test_login_malformed_json_returns_400(anon_client):
    res = anon_client.post("/login", data="not-json", content_type="application/json")
    assert res.status_code == 400


# Line 146 — /transfer with valid JWT but non-dict body -> 400
def test_transfer_non_dict_body_returns_400(anon_client):
    token = generate_jwt("user_1")
    res = anon_client.post(
        "/transfer", data="not-json", content_type="application/json", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 400


# Line 179 — /api/accounts/.../balance with bad token -> 401
def test_balance_bad_token_returns_401(anon_client):
    res = anon_client.get("/api/accounts/user_1/balance", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


# Lines 183, 190 — /api/accounts/.../balance for unknown account -> 404
def test_balance_unknown_account_returns_404(anon_client):
    token = generate_jwt("admin")
    res = anon_client.get("/api/accounts/nonexistent/balance", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


# Line 61 — verify_jwt returns None on expired token
def test_expired_jwt_returns_401(anon_client):
    from datetime import UTC, datetime, timedelta

    import jwt
    from main import JWT_SECRET

    expired_token = jwt.encode(
        {
            "sub": "user_1",
            "role": "user",
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC) - timedelta(hours=2),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    res = anon_client.post("/transfer", json={"amount": 10}, headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401


# Line 161 — /transfer: insufficient funds -> 400
def test_transfer_insufficient_funds_returns_400(anon_client):
    import main as _main
    from main import generate_jwt

    _main.accounts["user_1"] = 0.0
    token = generate_jwt("user_1")
    res = anon_client.post(
        "/transfer",
        json={"amount": 0.01},
        headers={"Authorization": f"Bearer {token}", "X-Idempotency-Key": "test-insuf-key-001"},
    )
    _main.accounts["user_1"] = 1000.0  # restore
    assert res.status_code == 400


# Line 190 — /test/reset returns 404 when TEST_MODE is not set
def test_reset_without_test_mode_returns_404(anon_client):
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {}, clear=True):
        res = anon_client.post("/test/reset")
    assert res.status_code == 404


# Line 120 — /login with valid JSON but non-dict (array) -> 400
def test_login_json_array_returns_400(anon_client):
    res = anon_client.post("/login", json=[{"username": "user_1", "password": "password111"}])
    assert res.status_code == 400


# Line 146 — /transfer with valid JWT but non-dict JSON body -> 400
def test_transfer_json_array_returns_400(anon_client):
    from main import generate_jwt

    token = generate_jwt("user_1")
    res = anon_client.post("/transfer", json=[{"amount": 10}], headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_reset_endpoint_success(client):
    """Lines 194-198: reset_state() success path — called with TEST_MODE=true."""
    response = client.post("/test/reset")
    assert response.status_code == 200
    assert response.get_json()["status"] == "test_state_reset"


def test_reset_endpoint_blocked_outside_test_mode():
    """Line 192: reset_state() 404 path — TEST_MODE not set."""
    import os

    from main import app

    os.environ.pop("TEST_MODE", None)
    with app.test_client() as c:
        response = c.post("/test/reset")
    os.environ["TEST_MODE"] = "true"  # restore for subsequent tests
    assert response.status_code == 404


def test_metrics_endpoint_returns_prometheus_data(client):
    """Prometheus /metrics endpoint must return valid text/plain metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert (
        b"flask_http_request_total" in response.data
        or b"# HELP" in response.data
        or response.content_type.startswith("text/plain")
    )
