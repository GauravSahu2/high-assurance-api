"""
Two-Person Rule Tests — Deployment authorization enforcement.

These tests verify that critical infrastructure changes require
multi-party approval, preventing single points of compromise.

Previous version tested a local function — this version also
validates the real CODEOWNERS file and deployment authorization.
"""

from __future__ import annotations

import os

# ── Simulation Layer (retained for educational value) ─────────────────────────


def verify_deployment_authorization(modified_files, approvers):
    """Check that critical file changes have Senior/Lead sign-off."""
    critical_paths = ["infra/terraform", "src/auth", "src/database_migrations"]
    touches_critical_code = any(any(path in file for path in critical_paths) for file in modified_files)
    if touches_critical_code:
        senior_approvers = [user for user, role in approvers.items() if role in ["Senior", "Lead", "Staff"]]
        if len(senior_approvers) == 0:
            return (
                False,
                "Deployment Blocked: Critical infrastructure requires Senior authorization.",
            )
    return True, "Deployment Authorized."


def test_deployment_authorization():
    """Verify the two-person rule in simulation."""
    modified_files = ["src/database_migrations/v2_drop_columns.sql"]
    approvers = {"dev_intern": "Junior"}

    is_authorized, msg = verify_deployment_authorization(modified_files, approvers)
    assert not is_authorized, "CRITICAL FAIL: Pipeline allowed junior to deploy critical code unreviewed!"

    approvers["senior_gaurav"] = "Senior"
    is_authorized, msg = verify_deployment_authorization(modified_files, approvers)
    assert is_authorized, "CRITICAL FAIL: Pipeline blocked a properly authorized deployment."


# ── Real CODEOWNERS Validation ────────────────────────────────────────────────


def test_codeowners_file_exists():
    """Verify CODEOWNERS file exists for GitHub branch protection."""
    codeowners_path = os.path.join(os.path.dirname(__file__), "..", "..", ".github", "CODEOWNERS")
    assert os.path.exists(
        codeowners_path
    ), "CRITICAL: .github/CODEOWNERS file missing — branch protection not enforced!"


def test_codeowners_protects_critical_paths():
    """Verify that CODEOWNERS covers security-critical directories."""
    codeowners_path = os.path.join(os.path.dirname(__file__), "..", "..", ".github", "CODEOWNERS")
    with open(codeowners_path) as f:
        content = f.read()

    critical_patterns = ["src/", "openapi.yaml", ".github/", "tests/2_security/"]
    for pattern in critical_patterns:
        assert pattern in content, f"CRITICAL: CODEOWNERS does not protect '{pattern}' — unauthorized changes possible!"


def test_codeowners_has_named_reviewer():
    """Verify CODEOWNERS assigns a specific reviewer, not a wildcard."""
    codeowners_path = os.path.join(os.path.dirname(__file__), "..", "..", ".github", "CODEOWNERS")
    with open(codeowners_path) as f:
        content = f.read()

    assert "@" in content, "CRITICAL: CODEOWNERS has no named reviewers — two-person rule not enforced!"
    # Ensure it's not just a comment with @
    lines = [l for l in content.strip().split("\n") if l.strip() and not l.strip().startswith("#")]
    reviewer_lines = [l for l in lines if "@" in l]
    assert len(reviewer_lines) >= 3, "CRITICAL: CODEOWNERS must protect at least 3 critical paths with named reviewers!"
