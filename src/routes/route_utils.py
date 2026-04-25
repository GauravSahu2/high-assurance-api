"""
Utility functions for routes to reduce complexity in handler files.
"""
from __future__ import annotations
import time
from decimal import Decimal, InvalidOperation
from flask import jsonify

def _check_lockout(redis_client, ip, username, max_attempts, err_msg):
    """Checks IP and User lockout status."""
    lockout_ip_key = f"lockout:ip:{ip}"
    lockout_user_key = f"lockout:user:{username}"
    try:
        ip_attempts = int(redis_client.get(lockout_ip_key) or 0)
        user_attempts = int(redis_client.get(lockout_user_key) or 0)
        if ip_attempts >= max_attempts or user_attempts >= max_attempts:
            return True, jsonify({"error": "too many failed attempts"}), 429
    except Exception:
        return True, jsonify({"error": err_msg}), 503
    return False, None, None


def _update_lockout(redis_client, ip, username, ttl, err_msg):
    """Increments lockout counters for IP and User."""
    lockout_ip_key = f"lockout:ip:{ip}"
    lockout_user_key = f"lockout:user:{username}"
    try:
        redis_client.incr(lockout_ip_key)
        redis_client.expire(lockout_ip_key, ttl)
        redis_client.incr(lockout_user_key)
        redis_client.expire(lockout_user_key, ttl)
    except Exception:
        return jsonify({"error": err_msg}), 503
    return None


def _revoke_jti(redis_client, claims):
    """Blacklists the JTI in Redis."""
    jti = claims.get("jti")
    exp = claims.get("exp")
    if not (jti and exp):
        return
    try:
        ttl = int(exp - time.time())
        if ttl > 0:
            redis_client.setex(f"revoked_jti:{jti}", ttl, "revoked")
    except Exception:
        pass


def _validate_transfer_request(body, claims, t_min, t_max):
    """Validates the transfer request body and parameters."""
    try:
        amt = Decimal(str(body.get("amount")))
        if amt < Decimal(t_min) or amt > Decimal(t_max):
            return None, "amount out of range or invalid"
        amount = float(amt)
    except (InvalidOperation, ValueError, TypeError):
        return None, "amount out of range or invalid"

    to_user = body.get("to_user")
    if not isinstance(to_user, str) or not to_user:
        return None, "missing or invalid destination account"

    username = claims["sub"]
    if username == to_user:
        return None, "cannot transfer to self"

    return (username, to_user, amount), None
