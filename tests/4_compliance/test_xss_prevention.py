"""
Compliance Test: XSS Prevention & Input Sanitization
═══════════════════════════════════════════════════════════
Frameworks: OWASP A03, CWE-79, PCI DSS 6.5.7

Validates:
  • JSON responses don't reflect unsanitized user input
  • Script tags in input are never executed/reflected
  • CSP header blocks inline script execution
  • Error messages don't include raw user input
"""
import json

import pytest
from main import app as flask_app, redis_client




class TestXSSPrevention:
    """OWASP A03: Injection — Cross-Site Scripting."""

    def test_script_tag_in_username_not_reflected(self, client):
        """CWE-79: Script tags in input must not appear in output."""
        xss_payload = "<script>alert('xss')</script>"
        res = client.post("/login", json={"username": xss_payload, "password": "test"})
        body = res.get_data(as_text=True)
        assert "<script>" not in body, \
            "XSS VULNERABILITY: Script tag reflected in response"

    def test_html_entities_in_error_messages(self, client):
        """CWE-79: Error messages must not contain raw HTML."""
        payloads = [
            "<img src=x onerror=alert(1)>",
            "'; DROP TABLE users;--",
            "<svg/onload=alert(1)>",
            "javascript:alert(1)",
        ]
        for payload in payloads:
            res = client.post("/login", json={"username": payload, "password": "x"})
            body = res.get_data(as_text=True)
            assert "<img" not in body, f"HTML reflected: {payload}"
            assert "<svg" not in body, f"SVG reflected: {payload}"
            assert "onerror" not in body, f"Event handler reflected: {payload}"

    def test_transfer_to_user_xss(self, client):
        """CWE-79: XSS via to_user field must not reflect."""
        token = client.post("/login", json={"username": "admin", "password": "password123"}).get_json()["token"]
        xss = "<script>steal(document.cookie)</script>"
        res = client.post("/transfer",
                          json={"amount": 1.0, "to_user": xss},
                          headers={"Authorization": f"Bearer {token}"})
        body = res.get_data(as_text=True)
        assert "<script>" not in body, "XSS via to_user field reflected in response"

    def test_csp_prevents_inline_scripts(self, client):
        """OWASP A03: CSP must block inline script execution."""
        res = client.get("/health")
        csp = res.headers.get("Content-Security-Policy", "")
        # default-src 'self' implicitly blocks inline scripts
        assert "default-src" in csp, "CSP must define default-src"
        assert "unsafe-inline" not in csp, \
            "CSP must NOT allow unsafe-inline (enables XSS)"
        assert "unsafe-eval" not in csp, \
            "CSP must NOT allow unsafe-eval (enables code injection)"

    def test_json_content_type_prevents_browser_xss(self, client):
        """CWE-79: API responses must use application/json, not text/html."""
        endpoints = ["/health", "/"]
        for ep in endpoints:
            res = client.get(ep)
            ct = res.headers.get("Content-Type", "")
            assert "application/json" in ct, \
                f"Endpoint {ep} returns Content-Type '{ct}' — must be application/json"

    def test_idempotency_key_xss(self, client):
        """CWE-79: XSS via headers must not reflect."""
        token = client.post("/login", json={"username": "admin", "password": "password123"}).get_json()["token"]
        res = client.post("/transfer",
                          json={"amount": 1.0, "to_user": "user_2"},
                          headers={
                              "Authorization": f"Bearer {token}",
                              "X-Idempotency-Key": "<script>alert(1)</script>"
                          })
        body = res.get_data(as_text=True)
        assert "<script>" not in body, "XSS via X-Idempotency-Key reflected"
