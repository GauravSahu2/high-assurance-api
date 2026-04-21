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

auth_bp = Blueprint("auth", __name__)


def _get_redis():
    """Lazy import to avoid circular dependency."""
    import main

    return main.redis_client


def _get_tracer():
    """Lazy import to avoid circular dependency."""
    import main

    return main.hsa_tracer


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and issue a JWT token."""
    redis_client = _get_redis()
    hsa_tracer = _get_tracer()

    ip = request.remote_addr or "unknown"
    lockout_ip_key = f"lockout:ip:{ip}"

    # Check IP-level lockout
    try:
        if int(redis_client.get(lockout_ip_key) or 0) >= MAX_LOGIN_ATTEMPTS:
            return jsonify({"error": "too many failed attempts"}), 429
    except redis_lib.RedisError:
        return jsonify({"error": "service temporarily degraded"}), 503

    with hsa_tracer.start_as_current_span("login.authenticate", attributes={"login.ip": ip}) as span:
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            span.set_attribute("login.result", "bad_request")
            return jsonify({"error": "request body must be a JSON object"}), 400

        username = body.get("username", "")
        password = body.get("password", "")
        span.set_attribute("login.user", username)

        if not isinstance(username, str) or not isinstance(password, str):
            span.set_attribute("login.result", "invalid_types")
            return jsonify({"error": "invalid payload types"}), 400

    # Check user-level lockout
    lockout_user_key = f"lockout:user:{username}"
    try:
        if int(redis_client.get(lockout_user_key) or 0) >= MAX_LOGIN_ATTEMPTS:
            return jsonify({"error": "too many failed attempts"}), 429
    except redis_lib.RedisError:
        return jsonify({"error": "service temporarily degraded"}), 503

    # Verify credentials (constant-time for non-existent users)
    user = USERS.get(username)
    hashed = user["password_hash"] if user else DUMMY_HASH
    is_valid = verify_password(password, hashed)

    if not user or not is_valid:
        try:
            redis_client.incr(lockout_ip_key)
            redis_client.expire(lockout_ip_key, LOCKOUT_TTL_SECONDS)
            redis_client.incr(lockout_user_key)
            redis_client.expire(lockout_user_key, LOCKOUT_TTL_SECONDS)
        except redis_lib.RedisError:
            return jsonify({"error": "service temporarily degraded"}), 503
        logger.warning("authentication_failed", user_id=username, ip_address=ip)
        return jsonify({"error": "invalid credentials"}), 401

    # Successful login — clear lockout counters
    try:
        redis_client.delete(lockout_ip_key)
        redis_client.delete(lockout_user_key)
    except redis_lib.RedisError:
        return jsonify({"error": "service temporarily degraded"}), 503

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
        return jsonify({"status": "logged out"}), 200

    claims = verify_jwt(raw, redis_client)
    if not claims:
        return jsonify({"status": "logged out"}), 200

    jti = claims.get("jti")
    exp = claims.get("exp")
    if jti and exp:
        try:
            ttl = int(exp - time.time())
            if ttl > 0:
                redis_client.setex(f"revoked_jti:{jti}", ttl, "revoked")
        except redis_lib.RedisError:
            pass

    return jsonify({"status": "logged out"}), 200
