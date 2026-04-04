import os
from unittest.mock import patch
import pytest
from main import app as flask_app, generate_jwt, get_db, Account

@pytest.fixture()
def anon_client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c

def test_transfer_unknown_token_returns_401(anon_client):
    res = anon_client.post("/transfer", json={"amount": 10, "to_user": "user_2"}, headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401

def test_chaos_monkey_returns_503(anon_client):
    with patch.dict(os.environ, {"CHAOS_MODE": "true"}):
        with patch("random.random", return_value=0.0):
            res = anon_client.get("/health")
    assert res.status_code == 503

def test_cors_allowed_origin_gets_header(anon_client):
    res = anon_client.options("/health", headers={"Origin": "http://localhost:3000"})
    assert "Access-Control-Allow-Origin" in res.headers

def test_login_malformed_json_returns_400(anon_client):
    res = anon_client.post("/login", data="not-json", content_type="application/json")
    assert res.status_code == 400

def test_transfer_non_dict_body_returns_400(anon_client):
    token = generate_jwt("user_1")
    res = anon_client.post("/transfer", data="not-json", content_type="application/json", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400

def test_balance_bad_token_returns_401(anon_client):
    res = anon_client.get("/api/accounts/user_1/balance", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401

def test_balance_unknown_account_returns_404(anon_client):
    token = generate_jwt("admin", "admin")
    res = anon_client.get("/api/accounts/nonexistent/balance", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404

def test_expired_jwt_returns_401(anon_client):
    from datetime import UTC, datetime, timedelta
    import jwt
    from main import JWT_SECRET
    expired_token = jwt.encode({"sub": "user_1", "role": "user", "exp": datetime.now(UTC) - timedelta(hours=1), "iat": datetime.now(UTC) - timedelta(hours=2)}, JWT_SECRET, algorithm="HS256")
    res = anon_client.post("/transfer", json={"amount": 10, "to_user": "user_2"}, headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401

def test_transfer_insufficient_funds_returns_400(anon_client):
    db = next(get_db())
    db.query(Account).filter_by(user_id="user_1").update({"balance": 0.0})
    db.commit()
    token = generate_jwt("user_1")
    res = anon_client.post("/transfer", json={"amount": 0.01, "to_user": "user_2"}, headers={"Authorization": f"Bearer {token}", "X-Idempotency-Key": "test-insuf-key-001"})
    assert res.status_code == 400

def test_reset_without_test_mode_returns_404(anon_client):
    with patch.dict(os.environ, {}, clear=True):
        res = anon_client.post("/test/reset")
    assert res.status_code == 404

def test_login_json_array_returns_400(anon_client):
    res = anon_client.post("/login", json=[{"username": "user_1", "password": "password111"}])
    assert res.status_code == 400

def test_transfer_json_array_returns_400(anon_client):
    token = generate_jwt("user_1")
    res = anon_client.post("/transfer", json=[{"amount": 10, "to_user": "user_2"}], headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400

def test_reset_endpoint_success(anon_client):
    response = anon_client.post("/test/reset")
    assert response.status_code == 200

def test_metrics_endpoint_returns_prometheus_data(anon_client):
    response = anon_client.get("/metrics")
    assert response.status_code == 200

def test_login_non_string_username_returns_400(anon_client):
    res = anon_client.post("/login", json={"username": 123, "password": 456})
    assert res.status_code == 400


def test_transfer_missing_to_user(anon_client):
    token = generate_jwt("user_1")
    res = anon_client.post("/transfer", json={"amount": 10.0}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400

def test_transfer_to_self(anon_client):
    token = generate_jwt("user_1")
    res = anon_client.post("/transfer", json={"amount": 10.0, "to_user": "user_1"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400

def test_transfer_to_nonexistent_user(anon_client):
    from main import generate_jwt
    token = generate_jwt("user_1")
    res = anon_client.post("/transfer", json={"amount": 10.0, "to_user": "ghost_recipient_999"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_logout_revokes_token(anon_client):
    from main import generate_jwt
    token = generate_jwt("user_1")
    # Verify token works initially
    res1 = anon_client.get("/api/users/user_1", headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 200
    # Logout
    res_logout = anon_client.post("/logout", headers={"Authorization": f"Bearer {token}"})
    assert res_logout.status_code == 200
    # Verify token is now blocked
    res2 = anon_client.get("/api/users/user_1", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 401

def test_logout_no_token(anon_client):
    res = anon_client.post("/logout")
    assert res.status_code == 200

def test_logout_bad_token(anon_client):
    res = anon_client.post("/logout", headers={"Authorization": "Bearer bad-token"})
    assert res.status_code == 200
