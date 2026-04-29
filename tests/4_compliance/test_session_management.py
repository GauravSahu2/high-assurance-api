"""
Compliance Test: Session Management & Token Lifecycle
═══════════════════════════════════════════════════════════
Frameworks: OWASP A07, PCI DSS 8.1.8, NIST AC-12

Validates:
  • JWT tokens expire after configured timeout
  • Tokens can be revoked via logout
  • Revoked tokens cannot be reused
  • Token includes required claims (sub, exp, iat, jti)
  • Expired tokens are rejected
"""

import main


class TestTokenLifecycle:
    """OWASP A07: Identification and Authentication Failures."""

    def test_token_has_expiration(self, client):
        """PCI 8.1.8: Sessions must have a defined timeout."""
        res = client.post("/login", json={"username": "admin", "password": "password123"})
        token = res.get_json()["token"]
        payload = main.verify_jwt(token)
        assert "exp" in payload, "Token must have expiration claim"
        assert payload["exp"] > payload["iat"], "Expiration must be after issuance"

    def test_token_expiration_is_900_seconds(self, client):
        """SOC 2: Session timeout must be defined and enforced."""
        res = client.post("/login", json={"username": "admin", "password": "password123"})
        token = res.get_json()["token"]
        payload = main.verify_jwt(token)
        ttl = payload["exp"] - payload["iat"]
        assert ttl == 900, f"Token TTL must be 900s (15 min), got {ttl}s"

    def test_token_has_unique_jti(self, client):
        """NIST AC-12: Each session must have a unique identifier."""
        tokens = []
        for _ in range(3):
            main.redis_client.flushdb()
            res = client.post("/login", json={"username": "admin", "password": "password123"})
            tokens.append(res.get_json()["token"])

        jtis = set()
        for t in tokens:
            payload = main.verify_jwt(t)
            assert "jti" in payload, "Token must have JTI claim"
            jtis.add(payload["jti"])

        assert len(jtis) == 3, "Each token must have a unique JTI"

    def test_token_has_subject_claim(self, client):
        """OWASP A07: Token must identify the authenticated user."""
        res = client.post("/login", json={"username": "user_1", "password": "password111"})
        token = res.get_json()["token"]
        payload = main.verify_jwt(token)
        assert payload["sub"] == "user_1", "Subject claim must match authenticated user"

    def test_token_has_role_claim(self, client):
        """SOC 2 CC6.3: Token must include authorization context."""
        res = client.post("/login", json={"username": "admin", "password": "password123"})
        token = res.get_json()["token"]
        payload = main.verify_jwt(token)
        assert payload["role"] == "admin", "Role claim must reflect user's role"


class TestTokenRevocation:
    """OWASP A07: Logout must invalidate the session."""

    def test_logout_revokes_token(self, client):
        """PCI 8.1.8: Logout must terminate the session."""
        res = client.post("/login", json={"username": "admin", "password": "password123"})
        token = res.get_json()["token"]

        # Verify token is valid before logout
        claims = main.verify_jwt(token)
        assert claims is not None, "Token should be valid before logout"

        # Perform logout
        client.post("/logout", headers={"Authorization": f"Bearer {token}"})

        # Verify token is now revoked
        claims_after = main.verify_jwt(token)
        assert claims_after is None, "PCI 8.1.8 VIOLATION: Token still valid after logout"

    def test_revoked_token_rejected_on_transfer(self, client):
        """OWASP A07: Revoked tokens must not authorize transactions."""
        res = client.post("/login", json={"username": "admin", "password": "password123"})
        token = res.get_json()["token"]

        client.post("/logout", headers={"Authorization": f"Bearer {token}"})

        res = client.post(
            "/transfer",
            json={"amount": 1.0, "to_user": "user_2"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 401, "Revoked token must not authorize transfers"

    def test_expired_token_rejected(self):
        """NIST AC-12: Expired tokens must be rejected."""
        import datetime
        import uuid

        import pyseto

        from auth import _get_paseto_keys

        now = datetime.datetime.now(datetime.UTC)
        payload = {
            "sub": "admin",
            "role": "admin",
            "iat": int((now - datetime.timedelta(seconds=1000)).timestamp()),
            "exp": int((now - datetime.timedelta(seconds=10)).timestamp()),
            "jti": str(uuid.uuid4()),
        }
        priv, _ = _get_paseto_keys()
        expired_token = pyseto.encode(priv, payload).decode()

        result = main.verify_jwt(expired_token)
        assert result is None, "Expired token must be rejected"
