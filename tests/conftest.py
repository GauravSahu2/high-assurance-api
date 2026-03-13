import pytest
import os

@pytest.fixture
def api_base_url():
    return "http://127.0.0.1:8000"

@pytest.fixture
def auth_header():
    # Centralized token logic
    token = os.getenv("APP_AUTH_TOKEN", "valid_admin_token")
    return {"Authorization": f"Bearer {token}"}
