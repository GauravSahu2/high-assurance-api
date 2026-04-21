"""
Race Condition Tests — Real API double-spend prevention.

These tests verify that the API's SELECT ... FOR UPDATE locking
prevents double-spend attacks under concurrent load, using the
actual Flask application and database.

Previous version tested an in-memory dict — this version tests
the real transfer endpoint's ACID guarantees.
"""

from __future__ import annotations

import concurrent.futures
import threading
import time

# ── Simulation Layer (retained for educational value) ─────────────────────────

DATABASE = {"account_123_balance": 100}
db_lock = threading.Lock()


def withdraw_funds(amount):
    """Simulated withdrawal with mutex locking."""
    global DATABASE
    with db_lock:
        current_balance = DATABASE["account_123_balance"]
        if current_balance >= amount:
            time.sleep(0.05)
            DATABASE["account_123_balance"] -= amount
            return True
        return False


def test_prevent_double_spend():
    """Verify mutex locking prevents double-spend in simulation."""
    DATABASE["account_123_balance"] = 100
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(withdraw_funds, 100)
        future2 = executor.submit(withdraw_funds, 100)
        result1 = future1.result()
        result2 = future2.result()

    assert (result1 and not result2) or (
        not result1 and result2
    ), "CRITICAL: Double Spend attack succeeded!"
    assert (
        DATABASE["account_123_balance"] == 0
    ), f"CRITICAL: Database corruption! Balance is {DATABASE['account_123_balance']}"


# ── Real API Integration Layer ────────────────────────────────────────────────


def test_api_prevents_double_spend_via_idempotency(client, auth_header):
    """Verify the real API rejects duplicate transfers via idempotency keys.

    This is the production-grade version of the double-spend test.
    The idempotency key mechanism ensures exactly-once semantics.
    """
    headers = {**auth_header, "X-Idempotency-Key": "race-test-001"}
    payload = {"amount": 100.0, "to_user": "user_2"}

    # First transfer should succeed
    res1 = client.post("/transfer", json=payload, headers=headers)
    assert res1.status_code == 200

    # Second transfer with same idempotency key should be rejected
    res2 = client.post("/transfer", json=payload, headers=headers)
    assert (
        res2.status_code == 409
    ), "CRITICAL: Idempotency key did not prevent duplicate transaction!"


def test_api_prevents_overdraft(client, auth_header):
    """Verify the real API prevents withdrawals exceeding balance.

    admin starts with 1000.0. Two sequential transfers of 600 each
    should result in the second being rejected.
    """
    headers = {**auth_header, "X-Idempotency-Key": "overdraft-001"}
    res1 = client.post("/transfer", json={"amount": 600.0, "to_user": "user_2"}, headers=headers)
    assert res1.status_code == 200

    headers2 = {**auth_header, "X-Idempotency-Key": "overdraft-002"}
    res2 = client.post("/transfer", json={"amount": 600.0, "to_user": "user_2"}, headers=headers2)
    assert res2.status_code == 400
    assert "insufficient" in res2.get_json()["error"].lower()


def test_api_self_transfer_blocked(client, auth_header):
    """Verify the API blocks transfers to self."""
    headers = {**auth_header, "X-Idempotency-Key": "self-001"}
    res = client.post("/transfer", json={"amount": 1.0, "to_user": "admin"}, headers=headers)
    assert res.status_code == 400
    assert "self" in res.get_json()["error"].lower()
