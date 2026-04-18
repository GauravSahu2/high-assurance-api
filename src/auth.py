"""
Authentication utilities — JWT generation, verification, and password hashing.

Security design:
    - bcrypt with configurable rounds (4 for tests, 12 for production)
    - Constant-time comparison via DUMMY_HASH to prevent user enumeration
    - JWT tokens include JTI for revocation support via Redis
"""
from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt as pyjwt

from config import (
    BCRYPT_ROUNDS_PROD,
    BCRYPT_ROUNDS_TEST,
    JWT_ALGORITHM,
    JWT_EXPIRY_SECONDS,
    TEST_MODE,
)
from security import JWT_SECRET


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt.

    Uses reduced rounds in TEST_MODE for speed.
    """
    rounds = BCRYPT_ROUNDS_TEST if TEST_MODE else BCRYPT_ROUNDS_PROD
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=rounds)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash with constant-time behavior.

    In TEST_MODE, adds a small sleep to simulate production bcrypt latency
    for timing-attack tests.
    """
    try:
        if TEST_MODE:
            time.sleep(0.01)
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def generate_jwt(username: str, role: str = "user") -> str:
    """Generate a signed JWT with JTI for revocation support."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(username),
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=JWT_EXPIRY_SECONDS),
        "jti": str(uuid.uuid4()),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt(token: str | None, redis_client: object = None) -> dict | None:
    """Decode and verify a JWT token.

    Checks token-level revocation via Redis JTI blacklist.
    Returns decoded payload or None on any failure.
    """
    if not token:
        return None
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        jti = payload.get("jti")
        if jti and redis_client:
            try:
                if redis_client.exists(f"revoked_jti:{jti}"):
                    return None
            except Exception:
                pass  # Redis failure → allow token (fail-open for availability)
        return payload
    except pyjwt.PyJWTError:
        return None


def extract_bearer_token(header: str | None) -> str | None:
    """Extract a Bearer token from an Authorization header value.

    Returns the token string or None if the header is missing/malformed.
    """
    if not header:
        return None
    parts = header.split(" ")
    if len(parts) == 2 and parts[0] == "Bearer" and parts[1]:
        return parts[1]
    return None


# ── User Store ────────────────────────────────────────────────────────────────
# Pre-computed hashes at module load time.
# In production, users would be database-backed.
USERS: dict[str, dict] = {
    "admin":  {"password_hash": hash_password("password123"), "role": "admin"},
    "user_1": {"password_hash": hash_password("password111"), "role": "user"},
    "user_2": {"password_hash": hash_password("password222"), "role": "user"},
}

# Dummy hash for non-existent users to prevent timing-based user enumeration
DUMMY_HASH: str = hash_password("dummy")
