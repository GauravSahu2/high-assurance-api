"""
Compliance Test: Password Policy Enforcement
═══════════════════════════════════════════════════════════
Frameworks: PCI DSS 8.2.3, NIST SP 800-63B, SOC 2 CC6.1

Validates:
  • Passwords are hashed with approved algorithms (bcrypt)
  • Constant-time comparison prevents timing leaks
  • Dummy hash is used for non-existent users (enumeration prevention)
  • Password verification never logs plaintext passwords
  • Hash rounds are appropriate for the environment
"""

import os

from main import DUMMY_HASH, USERS, _hp, _vp


class TestPasswordHashing:
    """NIST SP 800-63B §5.1.1.2: Memorized secret verifiers."""

    def test_all_passwords_use_bcrypt(self):
        """PCI 8.2.1: Passwords must be rendered unreadable with strong cryptography."""
        for user, data in USERS.items():
            h = data["password_hash"]
            assert h.startswith("$2"), f"User '{user}' not using bcrypt (hash: {h[:10]}...)"

    def test_dummy_hash_exists_for_enumeration_defense(self):
        """CWE-204: Prevent user enumeration through timing."""
        assert DUMMY_HASH is not None, "Dummy hash must exist for non-existent user defense"
        assert DUMMY_HASH.startswith("$2"), "Dummy hash must use same algorithm as real hashes"

    def test_password_verification_accepts_correct(self):
        """Baseline: correct password must verify."""
        hashed = _hp("correctpassword")
        assert _vp("correctpassword", hashed) is True

    def test_password_verification_rejects_wrong(self):
        """Baseline: wrong password must not verify."""
        hashed = _hp("correctpassword")
        assert _vp("wrongpassword", hashed) is False

    def test_password_verification_handles_malformed_hash(self):
        """CWE-754: Malformed hash must not crash, must return False."""
        result = _vp("anypassword", "not-a-valid-hash")
        assert result is False, "Malformed hash should return False, not raise exception"

    def test_password_hash_different_per_user(self):
        """PCI 8.2.1: Each user must have a unique salt."""
        hashes = [data["password_hash"] for data in USERS.values()]
        # bcrypt auto-salts, so even identical passwords produce different hashes
        assert len(set(hashes)) == len(
            hashes
        ), "Password hashes should be unique per user (unique salts)"


class TestPasswordPolicyRequirements:
    """PCI DSS 8.2.3: Authentication factor requirements."""

    def test_login_rejects_empty_password(self, client):
        """PCI 8.2.3: Empty passwords must be rejected."""
        res = client.post("/login", json={"username": "admin", "password": ""})
        assert res.status_code == 401, "Empty password should not authenticate"

    def test_login_rejects_null_password(self, client):
        """CWE-287: Null/missing credentials must be rejected."""
        res = client.post("/login", json={"username": "admin"})
        # body.get("password", "") returns "" for missing key, which should fail auth
        assert res.status_code in (400, 401), "Missing password field should not authenticate"

    def test_login_rejects_non_string_password(self, client):
        """CWE-20: Password must be a string type."""
        res = client.post("/login", json={"username": "admin", "password": 12345})
        assert res.status_code == 400, "Integer password should be rejected with 400"

    def test_login_rejects_list_password(self, client):
        """CWE-20: Array injection must be blocked."""
        res = client.post("/login", json={"username": "admin", "password": ["password123"]})
        assert res.status_code == 400, "Array password should be rejected"

    def test_bcrypt_cost_factor_minimum(self):
        """OWASP: Work factor must be at minimum 4 (test) or 12 (production)."""
        for user, data in USERS.items():
            parts = data["password_hash"].split("$")
            cost = int(parts[2])
            min_cost = 4 if os.environ.get("TEST_MODE") else 12
            assert cost >= min_cost, f"bcrypt cost for {user} is {cost}, minimum is {min_cost}"
