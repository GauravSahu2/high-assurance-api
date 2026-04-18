"""
Admin routes — user/account lookups and test state management.

Security:
    - All endpoints require JWT authentication
    - BOLA (Broken Object-Level Authorization) protection:
      users can only access their own data unless they have admin role
"""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

from auth import USERS, extract_bearer_token, verify_jwt
from database import SessionLocal, get_db
from models import Account, IdempotencyKey, OutboxEvent
from routes.transfer_routes import purge_expired_idempotency_keys

admin_bp = Blueprint("admin", __name__)


def _get_redis():
    import main
    return main.redis_client


@admin_bp.route("/api/users/<user_id>")
def get_user(user_id: str):
    """Get user profile with BOLA protection.

    Authorization rules:
        - Admin role: can access any user
        - Regular user: can only access their own profile
    """
    redis_client = _get_redis()
    claims = verify_jwt(
        extract_bearer_token(request.headers.get("Authorization")),
        redis_client,
    )
    if not claims:
        return jsonify({"error": "unauthorized"}), 401
    if claims.get("role") != "admin" and claims.get("sub") != user_id:
        return jsonify({"error": "forbidden"}), 403
    if user_id not in USERS:
        return jsonify({"error": "user not found"}), 404
    return jsonify({"user_id": user_id, "role": USERS[user_id]["role"]})


@admin_bp.route("/api/accounts/<user_id>/balance")
def get_balance(user_id: str):
    """Get account balance with BOLA protection.

    Authorization rules:
        - Admin role: can access any balance
        - Regular user: can only access their own balance
    """
    redis_client = _get_redis()
    claims = verify_jwt(
        extract_bearer_token(request.headers.get("Authorization")),
        redis_client,
    )
    if not claims:
        return jsonify({"error": "unauthorized"}), 401
    if claims.get("role") != "admin" and claims.get("sub") != user_id:
        return jsonify({"error": "forbidden"}), 403

    db = next(get_db())
    acc = db.query(Account).filter_by(user_id=user_id).first()
    if not acc:
        return jsonify({"error": "account not found"}), 404
    return jsonify({"user_id": user_id, "balance": float(acc.balance)})


@admin_bp.route("/api/users/<user_id>/data", methods=["DELETE"])
def delete_user_data(user_id: str):
    """GDPR Right to Erasure endpoint.

    Authorization rules:
        - Admin role: can delete any user's data
        - Regular user: can only delete their own data
    """
    redis_client = _get_redis()
    claims = verify_jwt(
        extract_bearer_token(request.headers.get("Authorization")),
        redis_client,
    )
    if not claims:
        return jsonify({"error": "unauthorized"}), 401
    if claims.get("role") != "admin" and claims.get("sub") != user_id:
        return jsonify({"error": "forbidden"}), 403

    db = next(get_db())
    acc = db.query(Account).filter_by(user_id=user_id).first()
    if acc:
        db.delete(acc)
        db.commit()
        return jsonify({"status": "data_erased"}), 200
    return jsonify({"error": "user data not found"}), 404


@admin_bp.route("/test/reset", methods=["POST"])
def reset_state():
    """Reset all application state — only available in TEST_MODE.

    Used by the test harness to ensure test isolation.
    """
    if not os.environ.get("TEST_MODE"):
        return jsonify({"error": "not found"}), 404

    redis_client = _get_redis()

    try:
        redis_client.flushdb()
    except Exception:
        pass

    db = next(get_db())
    purge_expired_idempotency_keys(db)
    db.query(OutboxEvent).delete()
    db.query(IdempotencyKey).delete()
    db.query(Account).delete()
    db.commit()

    import main
    main.init_db()
    return jsonify({"status": "test_state_reset"})
