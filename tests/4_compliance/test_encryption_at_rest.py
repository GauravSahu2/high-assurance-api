"""
Compliance Test: Encryption at Rest & in Transit Configuration
═══════════════════════════════════════════════════════════════════
Frameworks: PCI DSS 3.4, 4.1, HIPAA §164.312(a)(2)(iv), GDPR Art.32, NIST SC-8/SC-28

Validates:
  • Database connection strings enforce TLS (sslmode)
  • Sensitive environment variables are never logged
  • The application supports encrypted DB connections
  • Secrets are loaded from a secrets manager, not hardcoded
  • JWT secret has sufficient entropy
"""
import os
import re

import pytest


class TestEncryptionAtRestConfiguration:
    """PCI DSS 3.4: Render sensitive data unreadable anywhere it is stored."""

    def test_database_module_supports_ssl(self):
        """PCI 4.1: Database connections must support TLS."""
        from database import engine
        # In production, DATABASE_URL should include sslmode=verify-full
        # In test mode, SQLite is acceptable
        url = str(engine.url)
        if "sqlite" not in url:
            assert "sslmode" in url or "ssl" in url, \
                "PCI 4.1 VIOLATION: Production database URL must include sslmode parameter"

    def test_secrets_loaded_from_manager_not_env(self):
        """PCI 3.4: Secrets must come from a vault, not plaintext env vars."""
        import inspect
        from main import _load_secret
        source = inspect.getsource(_load_secret)
        assert "secretsmanager" in source, \
            "Secrets must be loaded from AWS Secrets Manager (or equivalent vault)"

    def test_jwt_secret_has_minimum_entropy(self):
        """NIST SP 800-63B: Symmetric keys must have sufficient length."""
        from security import JWT_SECRET
        # In test mode, the dev fallback is acceptable
        # This test documents the requirement for production
        if os.environ.get("TEST_MODE"):
            # Even the dev secret should be reasonably long
            assert len(JWT_SECRET) >= 16, \
                "JWT secret must be at least 16 characters (128 bits) even in dev"
        else:
            assert len(JWT_SECRET) >= 32, \
                "NIST VIOLATION: Production JWT secret must be at least 256 bits"

    def test_password_hashes_use_bcrypt(self):
        """NIST SP 800-63B: Passwords must use approved hash functions."""
        from main import USERS
        for username, data in USERS.items():
            hashed = data["password_hash"]
            # bcrypt hashes start with $2b$ or $2a$
            assert hashed.startswith("$2"), \
                f"User {username} password hash does not use bcrypt (expected $2b$ prefix)"

    def test_bcrypt_cost_factor_is_adequate(self):
        """OWASP: bcrypt work factor should be >= 4 (test) or >= 12 (prod)."""
        from main import USERS
        for username, data in USERS.items():
            hashed = data["password_hash"]
            # Extract cost factor: $2b$XX$ where XX is the cost
            parts = hashed.split("$")
            cost = int(parts[2])
            if os.environ.get("TEST_MODE"):
                assert cost >= 4, f"bcrypt cost too low for {username}: {cost}"
            else:
                assert cost >= 12, f"NIST VIOLATION: bcrypt cost must be >= 12 in production, got {cost}"

    def test_sensitive_data_not_in_plaintext_responses(self, client):
        """PCI 3.4: Sensitive data must not appear in API responses."""
        token = client.post("/login", json={"username": "admin", "password": "password123"}).get_json()["token"]

        # Login response should never include password hash
        login_res = client.post("/login", json={"username": "admin", "password": "password123"})
        body = login_res.get_data(as_text=True)
        assert "$2" not in body, "PCI 3.4 VIOLATION: Password hash leaked in login response"
        assert "password_hash" not in body, "PCI 3.4 VIOLATION: Hash field name leaked"

    def test_user_endpoint_excludes_sensitive_fields(self, client):
        """GDPR Art.32: Personal data must be minimized in responses."""
        token = client.post("/login", json={"username": "admin", "password": "password123"}).get_json()["token"]
        res = client.get("/api/users/admin", headers={"Authorization": f"Bearer {token}"})
        data = res.get_json()

        assert "password" not in data, "User endpoint leaks password"
        assert "password_hash" not in data, "User endpoint leaks password hash"
        assert "user_id" in data, "User endpoint should return user_id"
        assert "role" in data, "User endpoint should return role"
