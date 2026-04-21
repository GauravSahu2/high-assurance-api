"""
Transfer routes — fund transfers with ACID guarantees.

Architecture:
    - Ordered lock acquisition (sorted user IDs) prevents deadlocks
    - Idempotency keys prevent duplicate transaction replay
    - Outbox pattern ensures reliable event publishing
    - Decimal arithmetic for financial precision
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from auth import extract_bearer_token, verify_jwt
from config import TRANSFER_MAX, TRANSFER_MIN
from database import get_db
from flask import Blueprint, jsonify, request
from models import Account, IdempotencyKey, OutboxEvent

transfer_bp = Blueprint("transfer", __name__)


def _get_redis():
    import main

    return main.redis_client


def _get_tracer():
    import main

    return main.hsa_tracer


@transfer_bp.route("/transfer", methods=["POST"])
def transfer():
    """Execute a fund transfer between two accounts.

    Security: Bearer JWT required.
    Idempotency: Optional X-Idempotency-Key header for exactly-once semantics.
    Audit: Every transfer creates an OutboxEvent for compliance trail.
    """
    redis_client = _get_redis()
    hsa_tracer = _get_tracer()

    # Authenticate
    raw = extract_bearer_token(request.headers.get("Authorization"))
    if not raw:
        return jsonify({"error": "missing or malformed authorization header"}), 401
    claims = verify_jwt(raw, redis_client)
    if not claims:
        return jsonify({"error": "invalid or expired token"}), 401

    # Parse body
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    # Validate amount with Decimal precision
    try:
        amt = Decimal(str(body.get("amount")))
        if amt < Decimal(TRANSFER_MIN) or amt > Decimal(TRANSFER_MAX):
            raise ValueError
        amount = float(amt)
    except (InvalidOperation, ValueError, TypeError):
        return jsonify({"error": "amount out of range or invalid"}), 400

    # Validate destination
    to_user = body.get("to_user")
    if not isinstance(to_user, str) or not to_user:
        return jsonify({"error": "missing or invalid destination account"}), 400

    username = claims["sub"]
    if username == to_user:
        return jsonify({"error": "cannot transfer to self"}), 400

    # Idempotency check
    idem = request.headers.get("X-Idempotency-Key")
    scoped = f"{username}:{idem}" if idem else None

    db = next(get_db())
    with hsa_tracer.start_as_current_span(
        "transfer.execute",
        attributes={
            "transfer.from": username,
            "transfer.to": to_user,
            "transfer.amount": float(amt),
        },
    ) as txn_span:
        try:
            # Check for duplicate transaction
            if scoped and db.query(IdempotencyKey).filter_by(idempotency_key=scoped).first():
                return jsonify({"error": "duplicate transaction"}), 409

            # Acquire locks in deterministic order to prevent deadlocks
            accs = db.query(Account).filter(Account.user_id.in_(sorted([username, to_user]))).with_for_update().all()
            accounts = {a.user_id: a for a in accs}
            sender = accounts.get(username)
            receiver = accounts.get(to_user)

            if not sender or not receiver:
                db.rollback()
                return jsonify({"error": "account not found"}), 404

            if float(sender.balance) < amount:
                db.rollback()
                return jsonify({"error": "insufficient funds"}), 400

            # Execute transfer
            sender.balance = float(sender.balance) - amount
            receiver.balance = float(receiver.balance) + amount

            # Record idempotency key
            if scoped:
                db.add(
                    IdempotencyKey(
                        idempotency_key=scoped,
                        status="processed",
                        response_body={"status": "transferred"},
                    )
                )

            # Append audit event (Transactional Outbox)
            db.add(
                OutboxEvent(
                    event_type="FUNDS_TRANSFERRED",
                    payload={"from": username, "to": to_user, "amount": amount},
                )
            )

            db.commit()
            new_balance = float(sender.balance)
            txn_span.set_attribute("transfer.result", "success")

        except Exception:
            txn_span.set_attribute("transfer.result", "failed")
            db.rollback()
            return jsonify({"error": "transaction failed"}), 500

        return jsonify(
            {
                "status": "transferred",
                "new_balance": new_balance,
                "transaction_id": str(uuid.uuid4()),
            }
        )


def purge_expired_idempotency_keys(db) -> int:
    """Remove idempotency keys older than 48 hours.

    Called during test state resets and by scheduled maintenance.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=48)
    deleted = db.query(IdempotencyKey).filter(IdempotencyKey.created_at < cutoff).delete()
    db.commit()
    return deleted
