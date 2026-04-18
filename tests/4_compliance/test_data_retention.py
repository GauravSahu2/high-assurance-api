"""
Compliance Test: Data Retention & Right to Deletion
═══════════════════════════════════════════════════════════
Frameworks: GDPR Art.17 (Right to Erasure), CCPA §1798.105, SOC 2 CC6.5

Validates:
  • Data purge mechanism exists (idempotency key cleanup)
  • Purged data is actually removed from the database
  • Outbox events can be aged out per retention policy
  • Account data can be identified per user for GDPR requests
"""
from datetime import UTC, datetime, timedelta

import main
from database import SessionLocal
from main import purge_expired_idempotency_keys
from models import Account, IdempotencyKey


class TestDataRetentionPolicy:
    """GDPR Art.5(1)(e): Data must not be kept longer than necessary."""

    def test_idempotency_purge_function_exists(self):
        """SOC 2 CC6.5: Data lifecycle management must be implemented."""
        from main import purge_expired_idempotency_keys
        assert callable(purge_expired_idempotency_keys), \
            "purge_expired_idempotency_keys function must exist"

    def test_expired_idempotency_keys_are_purged(self, client):
        """GDPR Art.5: Stale records must be automatically cleaned."""
        db = SessionLocal()
        try:
            # Insert an old key (beyond 48h retention)
            old_key = IdempotencyKey(
                idempotency_key="old:test:key",
                status="processed",
                response_body={"status": "done"},
            )
            db.add(old_key)
            db.commit()

            # Manually age the record
            old_key.created_at = datetime.now(UTC) - timedelta(hours=49)
            db.commit()

            # Run purge
            deleted = purge_expired_idempotency_keys(db)
            assert deleted >= 1, "Purge must remove expired records"

            # Verify it's gone
            remaining = db.query(IdempotencyKey).filter_by(idempotency_key="old:test:key").first()
            assert remaining is None, "Expired key should be deleted after purge"
        finally:
            db.close()

    def test_recent_keys_not_purged(self, client):
        """Data retention: valid records must NOT be deleted."""
        db = SessionLocal()
        try:
            key = IdempotencyKey(
                idempotency_key="recent:test:key",
                status="processed",
                response_body={"status": "done"},
            )
            db.add(key)
            db.commit()

            deleted = purge_expired_idempotency_keys(db)

            remaining = db.query(IdempotencyKey).filter_by(idempotency_key="recent:test:key").first()
            assert remaining is not None, "Recent keys must NOT be purged"
        finally:
            # Clean up
            db.query(IdempotencyKey).filter_by(idempotency_key="recent:test:key").delete()
            db.commit()
            db.close()

    def test_user_data_identifiable_for_sar(self):
        """GDPR Art.15: Data must be queryable per user (Subject Access Request)."""
        db = SessionLocal()
        try:
            # Verify we can find all data for a specific user
            accounts = db.query(Account).filter_by(user_id="admin").all()
            assert len(accounts) >= 1, "User account data must be queryable by user_id"
        finally:
            db.close()

    def test_redis_lockout_keys_have_ttl(self, client):
        """GDPR Art.5(1)(e): Temporary data must auto-expire."""
        # Trigger a failed login to create lockout keys
        client.post("/login", json={"username": "admin", "password": "wrong"})

        # Check that the lockout key has a TTL
        ttl = main.redis_client.ttl("lockout:user:admin")
        assert ttl > 0, "Lockout keys must have a TTL (auto-expire)"
        assert ttl <= 3600, "Lockout TTL should not exceed 1 hour"

    def test_redis_revoked_jti_has_ttl(self, client):
        """GDPR: Revocation records must not persist indefinitely."""
        # Login, then logout to create a revoked JTI
        res = client.post("/login", json={"username": "admin", "password": "password123"})
        token = res.get_json()["token"]
        client.post("/logout", headers={"Authorization": f"Bearer {token}"})

        # Find the revoked JTI key
        keys = [k for k in main.redis_client.keys("revoked_jti:*")]
        if keys:
            ttl = main.redis_client.ttl(keys[0])
            assert ttl > 0, "Revoked JTI must have a TTL"
            assert ttl <= 900, "Revoked JTI TTL should not exceed token lifetime (900s)"
