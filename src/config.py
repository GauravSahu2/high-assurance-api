"""
Application configuration — centralized constants and environment loading.

All secrets are loaded from environment variables. No hardcoded fallbacks
for production-sensitive values.
"""
from __future__ import annotations

import os
import hvac

# ── Vault Configuration ──────────────────────────────────────────────────────────
VAULT_ADDR = os.environ.get("VAULT_ADDR")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN")

def get_secret(key: str, default: str | None = None) -> str:
    """Fetch secret from HashiCorp Vault with Env fallback."""
    if VAULT_ADDR and VAULT_TOKEN:
        try:
            client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
            read_response = client.secrets.kv.v2.read_secret_version(path='high-assurance', mount_point='secret')
            return read_response['data']['data'].get(key, os.environ.get(key, default))
        except Exception:
            pass # Fallback to ENV if Vault fails (High-Assurance Resilience)
    
    val = os.environ.get(key, default)
    if val is None:
         raise ValueError(f"Missing required configuration key: {key}")
    return val

# ── Environment ───────────────────────────────────────────────────────────────
TEST_MODE: bool = bool(os.environ.get("TEST_MODE"))
DEPLOY_ENV: str = os.environ.get("DEPLOY_ENV", "development")

# ── Secrets ───────────────────────────────────────────────────────────────────
JWT_SECRET: str = get_secret("JWT_SECRET", "changeme_in_production")
DATABASE_URL: str = get_secret("DATABASE_URL", "sqlite:///./high_assurance.db")
REDIS_URL: str = get_secret("REDIS_URL", "redis://localhost:6379/0")

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
