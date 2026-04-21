import io
from unittest.mock import patch

import redis

import main


def test_vp_exception():
    assert main._vp("pass", "invalid_hash") == False


def test_verify_jwt_redis_exception(token_factory):
    token = token_factory()
    with patch.object(main.redis_client, "exists", side_effect=redis.RedisError("mock")):
        assert main.verify_jwt(token) is not None


def test_login_lup_redis_error(client):
    def mock_get(name, *args):
        if "lockout:user:" in name:
            raise redis.RedisError("mock")
        return 0

    with patch.object(main.redis_client, "get", side_effect=mock_get):
        res = client.post("/login", json={"username": "admin", "password": "bad"})
    assert res.status_code == 503


def test_login_lup_too_many_attempts(client):
    def mock_get(name, *args):
        if "lockout:user:" in name:
            return 5
        return 0

    with patch.object(main.redis_client, "get", side_effect=mock_get):
        res = client.post("/login", json={"username": "admin", "password": "bad"})
    assert res.status_code == 429

    def mock_get2(name, *args):
        if "lockout:user:" in name:
            raise redis.RedisError("mock")
        return 0

    with patch.object(main.redis_client, "get", side_effect=mock_get2):
        res = client.post("/login", json={"username": "admin", "password": "bad"})
    assert res.status_code == 503


def test_login_incr_redis_error(client):
    with patch.object(main.redis_client, "incr", side_effect=redis.RedisError("mock")):
        res = client.post("/login", json={"username": "admin", "password": "bad"})
    assert res.status_code == 503


def test_login_delete_redis_error(client):
    with patch.object(main.redis_client, "delete", side_effect=redis.RedisError("mock")):
        res = client.post("/login", json={"username": "admin", "password": "password123"})
    assert res.status_code == 503


def test_logout_setex_redis_error(client, auth_header):
    with patch.object(main.redis_client, "setex", side_effect=redis.RedisError("mock")):
        res = client.post("/logout", headers=auth_header)
    assert res.status_code == 200


def test_upload_dataset_exception(client, auth_header):
    with patch("csv_validator.validate_and_sanitize_csv", side_effect=Exception("mock")):
        data = {"file": (io.BytesIO(b"a,b\n1,2"), "test.csv")}
        res = client.post("/upload-dataset", headers=auth_header, data=data, content_type="multipart/form-data")
    assert res.status_code == 202


def test_reset_redis_error(client):
    with patch.object(main.redis_client, "flushdb", side_effect=Exception("mock")):
        res = client.post("/test/reset")
    assert res.status_code == 200


def test_method_not_allowed_no_valid(client):
    res = client.patch("/health")
    assert res.status_code == 405

    class FakeException:
        valid_methods = None

    with client.application.test_request_context("/health"):
        res = main.method_not_allowed(FakeException())
        assert res.status_code == 405
