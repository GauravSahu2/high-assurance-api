"""
Authentication routes — login and logout with brute-force protection.

Security controls:
    - IP-based lockout after 5 failed attempts (Redis TTL: 1 hour)
    - User-based lockout after 5 failed attempts (Redis TTL: 1 hour)
    - Constant-time password verification (DUMMY_HASH for unknown users)
    - JWT JTI revocation on logout via Redis blacklist
"""

from __future__ import annotations

import time

import redis as redis_lib
from flask import Blueprint, jsonify, request

from auth import (
    DUMMY_HASH,
    USERS,
    extract_bearer_token,
    generate_jwt,
    verify_jwt,
    verify_password,
)
from config import LOCKOUT_TTL_SECONDS, MAX_LOGIN_ATTEMPTS
from logger import logger

from routes.route_utils import _check_lockout, _revoke_jti, _update_lockout

auth_bp = Blueprint("auth", __name__)


def _get_redis():
    """Lazy import to avoid circular dependency."""
    import main

    return main.redis_client


def _get_tracer():
    """Lazy import to avoid circular dependency."""
    import main

    return main.hsa_tracer


ERR_SERVICE_DEGRADED = "service temporarily degraded"
MSG_LOGGED_OUT = "logged out"


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and issue a JWT token."""
    redis_client = _get_redis()
    hsa_tracer = _get_tracer()

    ip = request.remote_addr or "unknown"
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    username = body.get("username", "")
    password = body.get("password", "")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "invalid payload types"}), 400

    # Lockout check
    is_locked, resp, status = _check_lockout(redis_client, ip, username, MAX_LOGIN_ATTEMPTS, ERR_SERVICE_DEGRADED)
    if is_locked:
        return resp, status

    with hsa_tracer.start_as_current_span("login.authenticate", attributes={"login.ip": ip, "login.user": username}):
        # Verify credentials (constant-time for non-existent users)
        user = USERS.get(username)
        hashed = user["password_hash"] if user else DUMMY_HASH
        is_valid = verify_password(password, hashed)
        if not (user and is_valid):
            err_resp = _update_lockout(redis_client, ip, username, LOCKOUT_TTL_SECONDS, ERR_SERVICE_DEGRADED)
            if err_resp:
                return err_resp
            logger.warning("authentication_failed", user_id=username, ip_address=ip)
            return jsonify({"error": "invalid credentials"}), 401

    # Successful login — clear lockout counters
    try:
        redis_client.delete(f"lockout:ip:{ip}")
        redis_client.delete(f"lockout:user:{username}")
    except Exception:
        return jsonify({"error": ERR_SERVICE_DEGRADED}), 503

    token = generate_jwt(username, USERS[username]["role"])
    return jsonify(
        {
            "token": token,
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 900,
        }
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Revoke the current JWT by blacklisting its JTI in Redis."""
    redis_client = _get_redis()

    raw = extract_bearer_token(request.headers.get("Authorization"))
    if not raw:
        return jsonify({"status": MSG_LOGGED_OUT}), 200

    claims = verify_jwt(raw, redis_client)
    if claims:
        _revoke_jti(redis_client, claims)

    return jsonify({"status": MSG_LOGGED_OUT}), 200
