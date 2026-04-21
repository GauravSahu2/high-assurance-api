import pytest

from main import ALLOWED_ORIGINS
from main import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_cors_allowed_origin_gets_header(client):
    # FIXED: Extract the first string from the ALLOWED_ORIGINS array
    real_origin = ALLOWED_ORIGINS[0]
    res = client.options("/health", headers={"Origin": real_origin})
    assert "Access-Control-Allow-Origin" in res.headers
    assert res.headers["Access-Control-Allow-Origin"] == real_origin


def test_cors_rejects_malicious_origin(client):
    res = client.options("/health", headers={"Origin": "https://evil-hacker.com"})
    assert "Access-Control-Allow-Origin" not in res.headers
