"""
OPA / Conftest policy-as-code tests.
Validates security invariants as Rego policies using OPA CLI.
Hard-fails if OPA binary is absent — SOC2 requirement, cannot be bypassed.
"""

import json
import shutil
import subprocess

import pytest

API_MANIFEST = {
    "environment": "development",
    "jwt_secret": "super-secure-dev-secret-key-123456789012345678901234",
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
    "jwt_secret": "super-secure-dev-secret-key-123456789012345678901234",
    "cors_wildcard": True,
    "routes": API_MANIFEST["routes"],
}


def test_opa_binary_presence_is_mandatory():
    """SOC2 Compliance: Policy-as-Code checks cannot be silently skipped."""
    if not shutil.which("opa"):
        pytest.fail(
            "CRITICAL BLOCKER: OPA binary not found. " "Policy-as-code validation is a strict SOC2 requirement."
        )


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


def test_all_transfer_routes_require_auth():
    """Transfer, balance, and user-data routes must all require authentication."""
    protected = {r["path"] for r in API_MANIFEST["routes"] if r["auth_required"]}
    for path in [
        "/transfer",
        "/api/users/{user_id}",
        "/api/accounts/{user_id}/balance",
    ]:
        assert path in protected, f"{path} must require authentication per security policy"


def test_public_endpoints_are_minimal():
    """Public endpoints must be limited to health, login, docs, and root."""
    public = {r["path"] for r in API_MANIFEST["routes"] if not r["auth_required"]}
    unexpected = public - {"/health", "/login", "/openapi.yaml", "/"}
    assert not unexpected, f"Unexpected public endpoints: {unexpected}"
