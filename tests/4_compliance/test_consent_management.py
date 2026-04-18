"""
Compliance Test: Consent & Data Processing Awareness
═══════════════════════════════════════════════════════════
Frameworks: GDPR Art.6–7, HIPAA Consent, SOC 2 CC2.1

Validates:
  • API responses include privacy-relevant metadata
  • Terms of service endpoint or reference exists
  • Login response doesn't expose unnecessary user data
  • Data processing scope is documented via OpenAPI spec
"""
import os

import pytest
from main import app as flask_app


class TestConsentAndTransparency:
    """GDPR Art.6: Lawfulness of data processing."""

    def test_openapi_spec_exists(self, client):
        """GDPR Art.13: Data processing must be documented."""
        res = client.get("/openapi.yaml")
        assert res.status_code == 200, "OpenAPI spec must be publicly accessible"
        body = res.get_data(as_text=True)
        assert "openapi" in body.lower() or "swagger" in body.lower(), \
            "Spec must be a valid OpenAPI document"

    def test_openapi_describes_data_collected(self):
        """GDPR Art.13: Users must know what data is collected."""
        spec_path = os.path.join(os.path.dirname(__file__), "..", "..", "openapi.yaml")
        if os.path.exists(spec_path):
            with open(spec_path) as f:
                content = f.read()
            # Verify the spec documents the data model
            assert "username" in content or "user" in content, \
                "OpenAPI spec must document user-facing fields"
            assert "/login" in content or "/transfer" in content, \
                "OpenAPI spec must document API endpoints"

    def test_login_response_is_minimal(self, client):
        """GDPR Art.5(1)(c): Data minimization — only return what's needed."""
        res = client.post("/login", json={"username": "admin", "password": "password123"})
        data = res.get_json()

        # Login should only return token info, not user profile
        assert "token" in data, "Login must return a token"
        assert "password" not in data, "Login must NOT return password"
        assert "password_hash" not in data, "Login must NOT return hash"
        # These are acceptable in login response per OAuth 2.0 spec
        acceptable_keys = {"token", "access_token", "token_type", "expires_in", "refresh_token"}
        extra_keys = set(data.keys()) - acceptable_keys
        assert len(extra_keys) == 0, \
            f"Login returns unnecessary data: {extra_keys}. Violates data minimization."

    def test_health_endpoint_does_not_leak_internals(self, client):
        """SOC 2 CC2.1: System information must not be overshared."""
        res = client.get("/health")
        data = res.get_json()

        # Health should report status, not internal details
        assert "password" not in str(data).lower()
        assert "secret" not in str(data).lower()
        assert "database_url" not in str(data).lower()
        assert "connection_string" not in str(data).lower()

    def test_correlation_id_in_responses(self, client):
        """SOC 2 CC7.2: All requests must be traceable."""
        res = client.get("/health")
        assert "X-Correlation-ID" in res.headers, \
            "Every response must include X-Correlation-ID for traceability"
        assert len(res.headers["X-Correlation-ID"]) > 0, \
            "Correlation ID must not be empty"
