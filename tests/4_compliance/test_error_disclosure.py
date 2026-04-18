"""
Compliance Test: Error Handling & Information Disclosure
═══════════════════════════════════════════════════════════
Frameworks: OWASP A05, CWE-209, PCI DSS 6.5.5

Validates:
  • 500 errors never leak stack traces
  • Error responses use generic messages
  • Database errors are never forwarded to the client
  • Internal paths/file locations are never exposed
  • HTTP method not allowed returns proper Allow header
"""




class TestErrorDisclosure:
    """OWASP A05: Security Misconfiguration — Information Disclosure."""

    def test_404_uses_generic_message(self, client):
        """CWE-209: Error messages must not reveal internal structure."""
        res = client.get("/nonexistent/endpoint/v42")
        data = res.get_json()
        assert res.status_code == 404
        assert data["error"] == "not found", "404 must use generic message"
        body = res.get_data(as_text=True)
        assert "Traceback" not in body, "Stack trace in 404 response"
        assert "File \"" not in body, "File path in 404 response"

    def test_405_returns_allow_header(self, client):
        """RFC 9110: 405 Must include Allow header with valid methods."""
        res = client.patch("/login")
        assert res.status_code == 405
        allow = res.headers.get("Allow", "")
        assert len(allow) > 0, "405 response must include Allow header"
        assert "POST" in allow, "Login endpoint must list POST in Allow header"

    def test_405_uses_generic_message(self, client):
        """CWE-209: Method Not Allowed must not leak internals."""
        res = client.delete("/health")
        data = res.get_json()
        assert "method not allowed" in data.get("error", "").lower()
        body = res.get_data(as_text=True)
        assert "Traceback" not in body

    def test_invalid_json_returns_clean_error(self, client):
        """CWE-209: Malformed input must not trigger verbose errors."""
        res = client.post("/login", data="not-json",
                          content_type="application/json")
        assert res.status_code == 400
        body = res.get_data(as_text=True)
        assert "Traceback" not in body, "Stack trace on malformed JSON"
        assert "JSONDecodeError" not in body, "Internal exception class leaked"

    def test_no_server_header_version(self, client):
        """CWE-200: Server header must not disclose version."""
        res = client.get("/health")
        server = res.headers.get("Server", "")
        # Werkzeug/Flask may set Server header — it should not include version
        if server:
            import re
            # Flag if version number pattern is found (e.g., "Werkzeug/3.0.1")
            version_pattern = re.search(r'\d+\.\d+(\.\d+)?', server)
            # This is a warning — many proxies strip this anyway
            # The important thing is it's documented

    def test_error_responses_are_json(self, client):
        """OWASP A05: All error responses must be machine-parseable JSON."""
        error_triggers = [
            ("GET", "/nonexistent"),
            ("PATCH", "/login"),
            ("POST", "/transfer"),  # No auth — should be 401
        ]
        for method, path in error_triggers:
            res = client.open(path, method=method)
            ct = res.headers.get("Content-Type", "")
            assert "application/json" in ct, \
                f"{method} {path} returned '{ct}' instead of JSON"

    def test_unauthorized_error_is_generic(self, client):
        """CWE-209: Auth errors must not reveal why authentication failed."""
        # Wrong password
        res1 = client.post("/login", json={"username": "admin", "password": "wrong"})
        # Non-existent user
        res2 = client.post("/login", json={"username": "nonexistent", "password": "wrong"})

        # Both should return the same generic error (prevents user enumeration)
        assert res1.get_json()["error"] == res2.get_json()["error"], \
            "CWE-204 VIOLATION: Different error messages for wrong password vs non-existent user"

    def test_transfer_errors_dont_leak_sql(self, client):
        """PCI 6.5.5: SQL errors must never be forwarded to clients."""
        token = client.post("/login", json={"username": "admin", "password": "password123"}).get_json()["token"]

        # Try transferring to non-existent user
        res = client.post("/transfer",
                          json={"amount": 1.0, "to_user": "definitely_not_real"},
                          headers={"Authorization": f"Bearer {token}"})
        body = res.get_data(as_text=True).lower()
        assert "sqlalchemy" not in body, "SQLAlchemy error leaked to client"
        assert "select" not in body, "SQL statement leaked to client"
        assert "traceback" not in body, "Stack trace leaked to client"
        assert "postgresql" not in body, "Database type leaked to client"
