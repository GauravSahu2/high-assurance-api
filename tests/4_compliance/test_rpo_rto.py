"""
Compliance Test: Business Continuity — RPO/RTO Verification
═══════════════════════════════════════════════════════════════
Frameworks: SOC 2 A1.2, PCI DSS 12.10, ISO 22301

Validates:
  • Disaster recovery infrastructure exists (k8s self-healing)
  • Health endpoint enables automated failover detection
  • Application can reinitialize state after crash (init_db)
  • Chaos engineering experiments are defined
  • Rollback tests exist
  • Backup integrity tests exist
"""
import os
import time

import pytest
from main import app as flask_app, redis_client, init_db
from database import SessionLocal
from models import Account




class TestRecoveryPointObjective:
    """SOC 2 A1.2: RPO — Maximum acceptable data loss."""

    def test_database_uses_transactions(self):
        """RPO=0: All writes must be transactional (no partial writes)."""
        import inspect
        from main import transfer
        source = inspect.getsource(transfer)
        assert "db.commit()" in source, "Transfers must use explicit commits"
        assert "db.rollback()" in source, "Transfers must handle rollback"

    def test_outbox_pattern_ensures_no_lost_events(self):
        """RPO=0: Events are written in the same transaction as data changes."""
        import inspect
        from main import transfer
        source = inspect.getsource(transfer)
        # OutboxEvent is added BEFORE commit — same transaction
        commit_pos = source.find("db.commit()")
        outbox_pos = source.find("OutboxEvent")
        assert outbox_pos < commit_pos, \
            "OutboxEvent must be added before commit (same transaction boundary)"

    def test_idempotency_prevents_duplicate_processing(self, client):
        """RPO: Replayed requests must not cause duplicate data changes."""
        token = client.post("/login", json={"username": "admin", "password": "password123"}).get_json()["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Idempotency-Key": "rpo-001"}

        res1 = client.post("/transfer", json={"amount": 10.0, "to_user": "user_2"}, headers=headers)
        res2 = client.post("/transfer", json={"amount": 10.0, "to_user": "user_2"}, headers=headers)

        assert res1.status_code == 200
        assert res2.status_code == 409, "Duplicate must be rejected (idempotency)"


class TestRecoveryTimeObjective:
    """SOC 2 A1.2: RTO — Maximum acceptable downtime."""

    def test_health_endpoint_responds_fast(self, client):
        """RTO: Health check must respond in <500ms for load balancer probes."""
        start = time.time()
        res = client.get("/health")
        elapsed = time.time() - start
        assert res.status_code == 200
        assert elapsed < 0.5, f"Health endpoint took {elapsed:.3f}s (max 500ms for LB probes)"

    def test_app_can_reinitialize_after_crash(self):
        """RTO: Application must be able to self-heal on restart."""
        # init_db should be idempotent — calling it twice should not crash
        init_db()
        init_db()  # Second call must not raise

        db = SessionLocal()
        try:
            accounts = db.query(Account).all()
            assert len(accounts) >= 2, "init_db must restore seed data"
        finally:
            db.close()

    def test_kubernetes_liveness_probe_configured(self):
        """RTO: K8s must automatically restart unhealthy pods."""
        deployment_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "k8s", "deployment.yaml"
        )
        assert os.path.exists(deployment_path), "K8s deployment manifest must exist"
        with open(deployment_path) as f:
            content = f.read()
        assert "livenessProbe" in content, \
            "K8s deployment must have a livenessProbe for auto-restart"
        assert "/health" in content, \
            "Liveness probe must check the /health endpoint"

    def test_multiple_replicas_configured(self):
        """RTO: Must have >1 replica for zero-downtime recovery."""
        deployment_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "k8s", "deployment.yaml"
        )
        with open(deployment_path) as f:
            content = f.read()
        assert "replicas:" in content, "Deployment must specify replicas"
        # Extract replica count
        import re
        match = re.search(r'replicas:\s*(\d+)', content)
        assert match, "Could not parse replica count"
        replicas = int(match.group(1))
        assert replicas >= 2, \
            f"RTO VIOLATION: Only {replicas} replica(s) configured. Need >= 2 for HA."

    def test_chaos_experiments_defined(self):
        """SRE: Chaos engineering validates RTO under failure conditions."""
        chaos_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "k8s", "chaos_network_delay.yaml"
        )
        assert os.path.exists(chaos_path), \
            "Chaos Mesh experiments must be defined for resilience testing"
        with open(chaos_path) as f:
            content = f.read()
        assert "NetworkChaos" in content, "Must have network chaos experiments"
        assert "PodChaos" in content, "Must have pod-kill experiments"

    def test_rollback_test_exists(self):
        """SOC 2 A1.2: Rollback procedures must be tested."""
        rollback_path = os.path.join(
            os.path.dirname(__file__), "..", "19_deployment_rollbacks",
            "test_automated_rollback.py"
        )
        assert os.path.exists(rollback_path), \
            "Automated rollback test must exist"

    def test_backup_integrity_test_exists(self):
        """SOC 2 A1.2: Backup restoration must be verified."""
        backup_path = os.path.join(
            os.path.dirname(__file__), "..", "20_disaster_recovery",
            "test_backup_integrity.py"
        )
        assert os.path.exists(backup_path), \
            "Backup integrity test must exist"
