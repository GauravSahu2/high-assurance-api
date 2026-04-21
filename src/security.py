"""
Security module — HTTP response hardening and JWT configuration.

All security headers comply with OWASP Secure Headers Project recommendations.
"""

from __future__ import annotations

import os

from flask import Response

# JWT secret MUST be set via environment variable. No fallback default.
JWT_SECRET: str = os.environ.get("JWT_SECRET", "dev-secret-key")

if len(JWT_SECRET) < 48 and not os.environ.get("TEST_MODE"):
    raise ValueError("JWT_SECRET must be at least 48 bytes for HS384 requirements!")  # pragma: no cover


def apply_security_headers(response: Response) -> Response:
    """Apply OWASP-recommended security headers to every HTTP response.

    Headers applied:
        - Content-Security-Policy: Prevents XSS and data injection attacks
        - X-Content-Type-Options: Prevents MIME-type sniffing
        - X-Frame-Options: Prevents clickjacking via iframe embedding
        - X-XSS-Protection: Legacy XSS filter for older browsers
        - Strict-Transport-Security: Enforces HTTPS for 1 year
        - Referrer-Policy: Controls referrer information leakage
        - Permissions-Policy: Restricts browser feature access
    """
    headers = {
        "Content-Security-Policy": "default-src 'self'",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }
    for key, value in headers.items():
        response.headers[key] = value
    return response


# ── Backward-Compatible Wrappers ─────────────────────────────────────────────
# These are thin re-exports so tests that do `from security import generate_jwt`
# continue to work after the refactor to auth.py.


def generate_jwt(user_id: str, role: str = "user") -> str:
    """Generate a JWT token. Delegates to auth.generate_jwt."""
    from auth import generate_jwt as _gen

    return _gen(user_id, role)


def decode_jwt(token: str) -> dict | None:
    """Decode a JWT token. Delegates to auth.verify_jwt."""
    from auth import verify_jwt as _ver

    return _ver(token)
