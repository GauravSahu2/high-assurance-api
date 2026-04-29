import pytest
from main import app as flask_app
from auth import generate_jwt, USERS

@pytest.fixture
def admin_token():
    return generate_jwt("admin", "admin")

@pytest.fixture
def user_token():
    return generate_jwt("user_1", "user")

def test_admin_lookup_user_success(admin_token):
    with flask_app.test_client() as c:
        resp = c.get("/api/users/user_1", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user_id"] == "user_1"
        assert data["role"] == "user"

def test_admin_lookup_user_unauthorized(user_token):
    with flask_app.test_client() as c:
        # user_1 should be able to access their own data
        resp = c.get("/api/users/user_1", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        
        # but user_1 should NOT be able to access user_2's data
        resp2 = c.get("/api/users/user_2", headers={"Authorization": f"Bearer {user_token}"})
        assert resp2.status_code == 403

def test_admin_get_balance_success(admin_token):
    with flask_app.test_client() as c:
        resp = c.get("/api/accounts/user_1/balance", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "balance" in data

def test_admin_delete_data_success(admin_token):
    with flask_app.test_client() as c:
        resp = c.delete("/api/users/user_2/data", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "data_erased"
