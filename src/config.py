"""
Application configuration — centralized constants and environment loading.

All secrets are loaded from environment variables. No hardcoded fallbacks
for production-sensitive values.
"""
from __future__ import annotations

import os

# ── Environment ───────────────────────────────────────────────────────────────
TEST_MODE: bool = bool(os.environ.get("TEST_MODE"))
DEPLOY_ENV: str = os.environ.get("DEPLOY_ENV", "development")

# ── Security ──────────────────────────────────────────────────────────────────
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRY_SECONDS: int = 900  # 15 minutes

# ── CORS ──────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS: list[str] = [
    "http://localhost:3000",
    "https://trusted-bank.com",
]

# ── Rate Limiting ─────────────────────────────────────────────────────────────
MAX_LOGIN_ATTEMPTS: int = 5
LOCKOUT_TTL_SECONDS: int = 3600  # 1 hour

# ── Transfer Limits ───────────────────────────────────────────────────────────
TRANSFER_MIN: str = "0.000001"
TRANSFER_MAX: str = "1000.0"

# ── Upload Limits ─────────────────────────────────────────────────────────────
MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

# ── Bcrypt ────────────────────────────────────────────────────────────────────
BCRYPT_ROUNDS_TEST: int = 4
BCRYPT_ROUNDS_PROD: int = 12
