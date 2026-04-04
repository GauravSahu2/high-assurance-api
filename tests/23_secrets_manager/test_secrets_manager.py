import pytest
import boto3
import os
from unittest.mock import patch
from moto import mock_aws
import main

SECRET_REGION = "us-east-1"

def _seed_secrets(client):
    client.create_secret(Name="high-assurance-api/jwt-secret", SecretString="test-jwt-secret-from-secrets-manager")
    client.create_secret(Name="high-assurance-api/admin-password", SecretString="test-admin-password-from-secrets-manager")

@mock_aws
def test_load_secret_returns_value_when_secret_exists():
    with patch.dict(os.environ, {"TEST_MODE": "", "AWS_DEFAULT_REGION": SECRET_REGION, "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}):
        client = boto3.client("secretsmanager", region_name=SECRET_REGION)
        _seed_secrets(client)
        
        result = main._load_secret("high-assurance-api/jwt-secret", fallback="fallback")
        assert result == "test-jwt-secret-from-secrets-manager"

@mock_aws
def test_load_secret_admin_password():
    with patch.dict(os.environ, {"TEST_MODE": "", "AWS_DEFAULT_REGION": SECRET_REGION, "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}):
        client = boto3.client("secretsmanager", region_name=SECRET_REGION)
        _seed_secrets(client)
        
        result = main._load_secret("high-assurance-api/admin-password", fallback="password123")
        assert result == "test-admin-password-from-secrets-manager"
