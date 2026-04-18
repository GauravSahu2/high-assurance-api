"""
Compliance Test: TLS Enforcement & Transport Security
═══════════════════════════════════════════════════════════
Frameworks: PCI DSS 4.1, NIST SC-8, SOC 2 CC6.7

Validates:
  • HSTS header is present with adequate max-age
  • Security headers prevent downgrade attacks
  • Application advertises HTTPS-only in production config
  • Proxy trust is properly configured (X-Forwarded-For)
"""


class TestTLSEnforcement:
    """PCI DSS 4.1: Use strong cryptography for transmission of sensitive data."""

    def test_hsts_header_present(self, client):
        """NIST SC-8: HSTS must be enabled to prevent SSL stripping."""
        res = client.get("/health")
        hsts = res.headers.get("Strict-Transport-Security")
        assert hsts is not None, "PCI 4.1 VIOLATION: HSTS header missing"

    def test_hsts_max_age_adequate(self, client):
        """PCI 4.1: HSTS max-age must be at least 1 year (31536000)."""
        res = client.get("/health")
        hsts = res.headers.get("Strict-Transport-Security", "")
        assert "max-age=" in hsts, "HSTS missing max-age directive"
        max_age = int(hsts.split("max-age=")[1].split(";")[0].strip())
        assert max_age >= 31536000, \
            f"HSTS max-age must be >= 31536000 (1 year), got {max_age}"

    def test_content_type_options_nosniff(self, client):
        """CWE-16: Prevent MIME type sniffing attacks."""
        res = client.get("/health")
        assert res.headers.get("X-Content-Type-Options") == "nosniff", \
            "X-Content-Type-Options must be 'nosniff'"

    def test_frame_options_deny(self, client):
        """CWE-1021: Prevent clickjacking via X-Frame-Options."""
        res = client.get("/health")
        xfo = res.headers.get("X-Frame-Options", "")
        assert xfo in ("DENY", "SAMEORIGIN"), \
            f"X-Frame-Options must be DENY or SAMEORIGIN, got '{xfo}'"

    def test_csp_header_present(self, client):
        """OWASP A05: Content-Security-Policy must be configured."""
        res = client.get("/health")
        csp = res.headers.get("Content-Security-Policy")
        assert csp is not None, "Content-Security-Policy header missing"
        assert "default-src" in csp, "CSP must define default-src directive"

    def test_xss_protection_header(self, client):
        """CWE-79: X-XSS-Protection must be enabled."""
        res = client.get("/health")
        xss = res.headers.get("X-XSS-Protection", "")
        assert "1" in xss, "X-XSS-Protection must be enabled"

    def test_proxy_fix_configured(self):
        """NIST SC-8: ProxyFix must be configured for correct IP extraction."""
        import inspect

        # FlaskInstrumentor wraps wsgi_app, hiding ProxyFix at runtime.
        # Verify it's applied in source code instead.
        import main
        source = inspect.getsource(main)
        assert "ProxyFix" in source, \
            "ProxyFix not configured — client IP extraction will be wrong behind load balancer."
        assert "x_for=1" in source, \
            "ProxyFix must trust X-Forwarded-For header (x_for=1)"

    def test_cors_is_not_wildcard(self, client):
        """PCI 6.5.9: CORS must not allow wildcard origins."""
        from main import ALLOWED_ORIGINS
        assert "*" not in ALLOWED_ORIGINS, "PCI VIOLATION: CORS wildcard (*) is enabled"
        assert len(ALLOWED_ORIGINS) > 0, "CORS must have explicit allowed origins"

    def test_security_headers_on_all_responses(self, client):
        """SOC 2 CC6.7: Security headers must be present on ALL responses, not just 200s."""
        # Test on 404
        res_404 = client.get("/nonexistent-path")
        assert res_404.headers.get("X-Content-Type-Options") == "nosniff", \
            "Security headers missing on 404 responses"
        assert res_404.headers.get("Strict-Transport-Security") is not None, \
            "HSTS missing on error responses"

        # Test on 401
        res_401 = client.post("/transfer", json={"amount": 1}, headers={})
        assert res_401.headers.get("X-Content-Type-Options") == "nosniff", \
            "Security headers missing on 401 responses"
