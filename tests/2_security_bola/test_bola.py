import requests
import pytest

def test_bola_unauthorized_access_is_blocked(api_base_url):
    """Verifies that a user cannot access resources without a valid token."""
    url = f"{api_base_url}/api/resource"
    headers = {"Authorization": "Bearer hacker_token"}
    response = requests.get(url, headers=headers)
    assert response.status_code == 403

def test_bola_authorized_access_is_permitted(api_base_url, auth_header):
    """Verifies legitimate access works using the centralized fixture."""
    url = f"{api_base_url}/api/resource"
    response = requests.get(url, headers=auth_header)
    assert response.status_code == 200
