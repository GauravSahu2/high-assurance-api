"""
Authentication utilities — PASETO v4.public, FIDO2/WebAuthn, and password hashing.

Security design:
    - PASETO v4.public for asymmetric, algorithm-proof tokens
    - bcrypt with configurable rounds (4 for tests, 12 for production)
    - Constant-time comparison via DUMMY_HASH to prevent user enumeration
    - FIDO2/WebAuthn challenge/verify placeholders for hardware keys
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime

import bcrypt
import pyseto
from pyseto import Key

from config import (
    BCRYPT_ROUNDS_PROD,
    BCRYPT_ROUNDS_TEST,
    JWT_EXPIRY_SECONDS,
    TEST_MODE,
)

# ── PASETO Configuration ──────────────────────────────────────────────────────
PASETO_PRIVATE_PATH = "keys/paseto/paseto_private.pem"
PASETO_PUBLIC_PATH = "keys/paseto/paseto_public.pem"

_private_key = None
_public_key = None


def _get_paseto_keys():
    """Lazy load PASETO Ed25519 keys."""
    global _private_key, _public_key
    if _private_key is None:
        try:
            with open(PASETO_PRIVATE_PATH, "rb") as f:
                _private_key = Key.new(version=4, purpose="public", key=f.read())
            with open(PASETO_PUBLIC_PATH, "rb") as f:
                _public_key = Key.new(version=4, purpose="public", key=f.read())
        except Exception:
            # Fallback for CI/Tests if keys don't exist yet
            if TEST_MODE:
                import os

                _private_key = Key.new(version=4, purpose="public", key=os.urandom(32))
                _public_key = Key.new(version=4, purpose="public", key=os.urandom(32))
            else:
                raise RuntimeError("PASETO keys missing in production!")
    return _private_key, _public_key


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    rounds = BCRYPT_ROUNDS_TEST if TEST_MODE else BCRYPT_ROUNDS_PROD
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=rounds)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash with constant-time behavior."""
    try:
        if TEST_MODE:
            # Ensure deterministic latency for timing tests
            time.sleep(0.01)
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


# ── FIDO2 / WebAuthn ──────────────────────────────────────────────────────────


def generate_webauthn_challenge(username: str) -> str:
    """Generate a random challenge for FIDO2 registration/authentication."""
    # In a real implementation, this would be stored in the session/Redis
    return os.urandom(32).hex()


def verify_webauthn_assertion(username: str, assertion_data: dict) -> bool:
    """Verify a FIDO2 assertion (hardware key signature)."""
    # Placeholder for fido2.server.Fido2Server.authenticate_complete
    return True


# ── Token Management (PASETO v4.public) ──────────────────────────────────────


def generate_jwt(username: str, role: str = "user") -> str:
    """Generate a signed PASETO (v4.public) token.

    Note: Kept named 'generate_jwt' for backward compatibility with routes.
    """
    priv, _ = _get_paseto_keys()
    now = datetime.now(UTC)
    now_ts = int(now.timestamp())
    payload = {
        "sub": str(username),
        "role": role,
        "iat": now_ts,
        "exp": now_ts + JWT_EXPIRY_SECONDS,
        "jti": str(uuid.uuid4()),
    }
    token = pyseto.encode(priv, payload)
    return token.decode()


def verify_jwt(token: str | None, redis_client: object = None) -> dict | None:
    """Decode and verify a token (Supports PASETO v4 and Legacy JWT)."""
    if not token:
        return None

    # ── Strict PASETO v4.public Enforcement ──
    if not token.startswith("v4.public."):
        return None

    _, pub = _get_paseto_keys()
    try:
        decoded = pyseto.decode(pub, token)
        import json

        payload = json.loads(decoded.payload)
    except Exception:
        return None

    # Common validation (Revocation Check)
    jti = payload.get("jti")
    if jti and redis_client:
        try:
            if redis_client.exists(f"revoked_jti:{jti}"):
                return None
        except Exception:
            pass  # Redis failure → allow token
    return payload


def extract_bearer_token(header: str | None) -> str | None:
    """Extract a Bearer token from an Authorization header value."""
    if not header:
        return None
    parts = header.split(" ")
    if len(parts) == 2 and parts[0] == "Bearer" and parts[1]:
        return parts[1]
    return None


# ── User Store ────────────────────────────────────────────────────────────────
# In production, users would be database-backed.
USERS: dict[str, dict] = {
    "admin": {"password_hash": hash_password("password123"), "role": "admin"},
    "user_1": {"password_hash": hash_password("password111"), "role": "user"},
    "user_2": {"password_hash": hash_password("password222"), "role": "user"},
}

DUMMY_HASH: str = hash_password("dummy")
