from __future__ import annotations
import pytest

def test_gdpr_erasure_endpoint_admin(client, token_factory):
    """Admin can delete any user."""
    admin_token = token_factory("admin", "admin")
    res = client.delete(
        "/api/users/user_2/data",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert res.get_json()["status"] == "data_erased"


def test_gdpr_erasure_endpoint_self(client, token_factory):
    """User can delete their own data."""
    user_token = token_factory("user_1", "user")
    res = client.delete(
        "/api/users/user_1/data",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res.status_code == 200


def test_gdpr_erasure_endpoint_forbidden(client, token_factory):
    """User cannot delete others data."""
    user_token = token_factory("user_1", "user")
    res = client.delete(
        "/api/users/user_2/data",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res.status_code == 403


def test_gdpr_erasure_endpoint_not_found(client, token_factory):
    """Deleting non-existent user data."""
    admin_token = token_factory("admin", "admin")
    res = client.delete(
        "/api/users/non_existent/data",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 404


def test_gdpr_erasure_unauthorized(client):
    """Unauthenticated request must be rejected."""
    res = client.delete("/api/users/user_1/data")
    assert res.status_code == 401
