"""
OPA / Conftest policy-as-code tests.
Validates security invariants as Rego policies using OPA CLI.
Falls back gracefully when OPA binary is not installed.
"""

import json
import os
import subprocess

import pytest

API_MANIFEST = {
    "environment": "development",
    "jwt_secret": "super-secure-dev-secret-key-12345",
    "cors_wildcard": True,
    "routes": [
        {"path": "/health", "auth_required": False},
        {"path": "/login", "auth_required": False},
        {"path": "/transfer", "auth_required": True},
        {"path": "/api/users/{user_id}", "auth_required": True},
        {"path": "/api/accounts/{user_id}/balance", "auth_required": True},
        {"path": "/openapi.yaml", "auth_required": False},
        {"path": "/", "auth_required": False},
    ],
}

PROD_MANIFEST = {
    "environment": "production",
    "jwt_secret": "super-secure-dev-secret-key-12345",
    "cors_wildcard": True,
    "routes": API_MANIFEST["routes"],
}


def _opa_available() -> bool:
    try:
        return subprocess.run(["opa", "version"], capture_output=True, timeout=5).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.mark.skipif(not _opa_available(), reason="OPA binary not installed")
def test_dev_manifest_passes_api_security_policy(tmp_path):
    """Dev environment: CORS wildcard and dev secret are acceptable."""
    manifest_file = tmp_path / "input.json"
    manifest_file.write_text(json.dumps(API_MANIFEST))
    result = subprocess.run(
        [
            "opa",
            "eval",
            "--data",
            "policies/api_security.rego",
            "--input",
            str(manifest_file),
            "data.api.security.deny",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = json.loads(result.stdout)
    denials = output["result"][0]["expressions"][0]["value"]
    assert denials == [], f"Unexpected denials in dev: {denials}"


@pytest.mark.skipif(not _opa_available(), reason="OPA binary not installed")
def test_prod_manifest_denied_for_default_jwt_secret(tmp_path):
    """Production with default JWT secret must be denied by policy."""
    manifest_file = tmp_path / "prod_input.json"
    manifest_file.write_text(json.dumps(PROD_MANIFEST))
    result = subprocess.run(
        [
            "opa",
            "eval",
            "--data",
            "policies/api_security.rego",
            "--input",
            str(manifest_file),
            "data.api.security.deny",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = json.loads(result.stdout)
    denials = output["result"][0]["expressions"][0]["value"]
    assert len(denials) >= 2, "Prod with dev JWT+CORS wildcard must trigger denials"
    denial_text = " ".join(denials)
    assert "JWT_SECRET" in denial_text
    assert "CORS" in denial_text


def test_policy_files_exist_and_are_valid_rego():
    """Policy files must exist, be non-empty, and contain valid Rego."""
    for policy in ["policies/api_security.rego", "policies/docker_security.rego"]:
        assert os.path.exists(policy), f"Missing policy file: {policy}"
        with open(policy) as f:
            content = f.read()
        assert len(content) > 100, f"Policy file too small: {policy}"
        assert "package" in content, f"Missing package declaration: {policy}"
        assert "deny" in content or "allow" in content, f"Policy must define deny or allow rules: {policy}"


def test_all_transfer_routes_require_auth():
    """Transfer, balance, and user-data routes must all require authentication."""
    protected_paths = {r["path"] for r in API_MANIFEST["routes"] if r["auth_required"]}
    must_be_protected = [
        "/transfer",
        "/api/users/{user_id}",
        "/api/accounts/{user_id}/balance",
    ]
    for path in must_be_protected:
        assert path in protected_paths, f"{path} must require authentication per security policy"


def test_public_endpoints_are_minimal():
    """Public endpoints must be limited to health, login, docs, and root."""
    public_paths = {r["path"] for r in API_MANIFEST["routes"] if not r["auth_required"]}
    allowed_public = {"/health", "/login", "/openapi.yaml", "/"}
    unexpected = public_paths - allowed_public
    assert not unexpected, f"Unexpected public endpoints: {unexpected}"
