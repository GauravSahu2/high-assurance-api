"""
AWS Secrets Manager integration tests.
Uses moto to mock the AWS Secrets Manager API — no real AWS calls.
Verifies _load_secret() reads from Secrets Manager when available
and falls back gracefully when not.
"""

import os

import boto3
from moto import mock_aws

SECRET_REGION = "us-east-1"


def _seed_secrets(client: object) -> None:
    """Seed Secrets Manager with the two secrets the app reads at startup."""
    client.create_secret(
        Name="high-assurance-api/jwt-secret",
        SecretString="test-jwt-secret-from-secrets-manager",
    )
    client.create_secret(
        Name="high-assurance-api/admin-password",
        SecretString="test-admin-password-from-secrets-manager",
    )


@mock_aws
def test_load_secret_returns_value_when_secret_exists():
    """_load_secret() must return the Secrets Manager value when found."""
    os.environ["AWS_DEFAULT_REGION"] = SECRET_REGION
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

    client = boto3.client("secretsmanager", region_name=SECRET_REGION)
    _seed_secrets(client)

    from main import _load_secret  # noqa: E402

    result = _load_secret("high-assurance-api/jwt-secret", fallback="fallback")
    assert result == "test-jwt-secret-from-secrets-manager"
    assert result != "fallback"


@mock_aws
def test_load_secret_falls_back_when_secret_missing():
    """_load_secret() must return the fallback for a nonexistent secret."""
    os.environ["AWS_DEFAULT_REGION"] = SECRET_REGION
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

    from main import _load_secret  # noqa: E402

    result = _load_secret("high-assurance-api/does-not-exist", fallback="my-fallback")
    assert result == "my-fallback"


@mock_aws
def test_load_secret_admin_password():
    """Admin password secret must be independently retrievable."""
    os.environ["AWS_DEFAULT_REGION"] = SECRET_REGION
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

    client = boto3.client("secretsmanager", region_name=SECRET_REGION)
    _seed_secrets(client)

    from main import _load_secret  # noqa: E402

    result = _load_secret("high-assurance-api/admin-password", fallback="password123")
    assert result == "test-admin-password-from-secrets-manager"
    assert result != "password123"


@mock_aws
def test_jwt_and_admin_secrets_are_separate():
    """JWT and admin password must be stored as two distinct secrets."""
    os.environ["AWS_DEFAULT_REGION"] = SECRET_REGION
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

    client = boto3.client("secretsmanager", region_name=SECRET_REGION)
    _seed_secrets(client)

    secrets = client.list_secrets()["SecretList"]
    names = {s["Name"] for s in secrets}
    assert "high-assurance-api/jwt-secret" in names
    assert "high-assurance-api/admin-password" in names
    assert len(names) == 2


def test_load_secret_is_callable():
    """_load_secret must be importable and callable from main."""
    from main import _load_secret  # noqa: E402

    assert callable(_load_secret)


def test_jwt_secret_is_string():
    """JWT_SECRET loaded at module import time must be a non-empty string."""
    from main import JWT_SECRET  # noqa: E402

    assert isinstance(JWT_SECRET, str)
    assert len(JWT_SECRET) > 0
