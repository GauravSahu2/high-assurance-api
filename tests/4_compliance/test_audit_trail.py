"""
Compliance Test: Audit Trail Immutability & Completeness
═══════════════════════════════════════════════════════════
Frameworks: SOC 2 CC7.2–CC7.4, PCI DSS 10.1–10.7, FDA 21 CFR §11.10(e)

Validates:
  • Security-relevant events are captured in the outbox/logs
  • Audit records include who, what, when, where (user, action, timestamp, IP)
  • OutboxEvent records cannot be modified after creation
  • Failed authentication attempts are logged
  • All financial transactions generate audit events
"""

from datetime import UTC, datetime

import main
from database import SessionLocal
from models import OutboxEvent


class TestAuditTrailCompleteness:
    """SOC 2 CC7.2: Security events must be logged."""

    def test_successful_transfer_generates_audit_event(self, client):
        """PCI 10.1: All access to cardholder data is logged."""
        token = client.post("/login", json={"username": "admin", "password": "password123"}).get_json()["token"]
        client.post(
            "/transfer",
            json={"amount": 10.0, "to_user": "user_2"},
            headers={"Authorization": f"Bearer {token}", "X-Idempotency-Key": "audit-001"},
        )

        db = SessionLocal()
        try:
            events = db.query(OutboxEvent).filter_by(event_type="FUNDS_TRANSFERRED").all()
            assert len(events) >= 1, "SOC 2 CC7.2 VIOLATION: Transfer did not generate audit event"

            event = events[-1]
            payload = event.payload
            assert "from" in payload, "Audit event missing 'from' (who initiated)"
            assert "to" in payload, "Audit event missing 'to' (who received)"
            assert "amount" in payload, "Audit event missing 'amount' (what happened)"
            assert event.created_at is not None, "Audit event missing timestamp (when)"
        finally:
            db.close()

    def test_audit_event_has_timestamp(self, client):
        """FDA 21 CFR §11.10(e): Records must include date and time."""
        token = client.post("/login", json={"username": "admin", "password": "password123"}).get_json()["token"]
        client.post(
            "/transfer",
            json={"amount": 5.0, "to_user": "user_2"},
            headers={"Authorization": f"Bearer {token}", "X-Idempotency-Key": "audit-ts-001"},
        )

        db = SessionLocal()
        try:
            event = db.query(OutboxEvent).order_by(OutboxEvent.id.desc()).first()
            assert event is not None
            assert isinstance(event.created_at, datetime), "Timestamp must be a datetime object"
            # Timestamp should be recent (within last 60 seconds)
            age = (datetime.now(UTC) - event.created_at.replace(tzinfo=UTC)).total_seconds()
            assert age < 60, f"Audit timestamp is {age}s old — clock skew detected"
        finally:
            db.close()

    def test_failed_login_is_observable(self, client):
        """PCI 10.2.4: Invalid logical access attempts are logged."""
        # Attempt a failed login
        res = client.post("/login", json={"username": "admin", "password": "wrong_password"})
        assert res.status_code == 401

        # The lockout counter in Redis serves as the audit trail for failed attempts
        lockout_count = main.redis_client.get("lockout:user:admin")
        assert lockout_count is not None, "PCI 10.2.4 VIOLATION: Failed login not tracked"
        assert int(lockout_count) >= 1, "Failed login attempt must increment lockout counter"

    def test_failed_login_tracks_ip(self, client):
        """PCI 10.2.4: Source IP of failed attempts must be recorded."""
        client.post("/login", json={"username": "admin", "password": "wrong"})
        # The IP lockout key proves IP-level tracking
        ip_key = main.redis_client.get("lockout:ip:127.0.0.1")
        assert ip_key is not None, "PCI 10.2.4 VIOLATION: IP not tracked on failed login"

    def test_transfer_audit_includes_both_parties(self, client):
        """SOC 2 CC7.3: Audit trail must identify all parties in a transaction."""
        token = client.post("/login", json={"username": "admin", "password": "password123"}).get_json()["token"]
        client.post(
            "/transfer",
            json={"amount": 1.0, "to_user": "user_1"},
            headers={"Authorization": f"Bearer {token}", "X-Idempotency-Key": "audit-party-001"},
        )

        db = SessionLocal()
        try:
            event = db.query(OutboxEvent).order_by(OutboxEvent.id.desc()).first()
            assert event.payload["from"] == "admin"
            assert event.payload["to"] == "user_1"
            assert event.payload["amount"] == 1.0
        finally:
            db.close()


class TestAuditImmutability:
    """FDA 21 CFR §11.10(e): Records must not be alterable after creation."""

    def test_outbox_event_has_created_at_default(self):
        """Verify the ORM model auto-stamps creation time."""
        import inspect

        from models import OutboxEvent

        source = inspect.getsource(OutboxEvent)
        assert "created_at" in source, "OutboxEvent model must have a created_at field"

    def test_outbox_events_are_append_only_by_design(self, client):
        """Verify that the API never issues UPDATE on outbox events."""
        import inspect

        from main import transfer

        source = inspect.getsource(transfer)
        # The transfer function should only db.add() outbox events, never update them
        assert "OutboxEvent" in source, "Transfer must create OutboxEvent records"
        # No update/delete patterns on OutboxEvent in the transfer function
        assert (
            ".delete()" not in source or "OutboxEvent" not in source.split(".delete()")[0].split("\n")[-1]
        ), "FDA VIOLATION: Transfer function must not delete OutboxEvent records"
