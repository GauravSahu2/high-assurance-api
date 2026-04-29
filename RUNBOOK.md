# 🛡️ Operational Runbook: High-Assurance API

This runbook provides the necessary procedures for deploying, monitoring, and responding to incidents within the High-Assurance API ecosystem.

---

## 1. Environment Variables Reference

| Variable | Description | Default | Production Target |
| :--- | :--- | :--- | :--- |
| `REDIS_URL` | Connection string for the Redis state backend. | `redis://localhost:6379/0` | Elasticache / Redis cluster URI |
| `PASETO_PRIVATE_KEY` | Ed25519 Private Key used for signing PASETO v4 tokens. | (AWS Secret fallback) | Ed25519 (Stored in KMS/Vault) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector endpoint for distributed tracing. | `http://localhost:4318/v1/traces` | Datadog/NewRelic OTLP Ingest |
| `TEST_MODE` | Dynamically lowers `bcrypt` work-factor to 4 for fast testing. | `false` | **MUST BE UNSET IN PROD** |
| `CHAOS_MODE` | Injects synthetic 503 errors into `/health` for resilience testing. | `false` | **MUST BE UNSET IN PROD** |
| `VAULT_ADDR` | Address for HashiCorp Vault key rotation. | `http://127.0.0.1:8200` | Enterprise Vault Cluster |

---

## 2. Deployment Guide

To ensure high-assurance stability, every deployment must follow this strict sequence:

1. **Gauntlet Verification**: Execute the full 32-tier gauntlet locally or in CI:

   ```bash
   ./hsa -a
   ```

   *Must pass 100.0% coverage, Zero ZAP Alerts, and Complexity Gate (Threshold 15).*

2. **Dependency Hardening**: Install strict, audited dependencies:

   ```bash
   pip install -r requirements.txt --require-hashes
   ```

3. **Production Boot**: Initialize the horizontally scalable WSGI server:

   ```bash
   gunicorn --threads 4 --workers 3 -b 0.0.0.0:5000 main:app
   ```

4. **Health Verification**: Confirm the node is ready for traffic:

   ```bash
   curl -I http://localhost:5000/health
   ```

   *(HTTP 200 OK with ISO-8601 timestamp is the required success signal).*

---

## 3. Incident Response & Architectural Tradeoffs

* **PASETO Auth Resilience**: If Redis (used for revocation) becomes unavailable, the API prioritizes **Availability** over strict revocation checks. It continues to verify PASETO signatures (v4.public) using the local public key, ensuring tokens are authentic even if their "revocation status" cannot be checked.
* **Complexity Monitoring**: If the `complexity-report.json` indicates an average cyclomatic complexity > 15, the deployment is blocked. If this occurs in production, audit the most recent "Hot Path" refactors for layer violations.
* **Telemetry Reliability**: We use a `SafeConsoleSpanExporter` and `atexit` handlers to ensure traces are flushed. If logs show `ValueError: I/O operation on closed file`, verify that the OTEL provider is not being shut down prematurely by the container runtime.
* **Monitoring Priority**: Set **P1 alerts** on:
  * `flask_http_request_total` where `status=429` spikes (Brute-force attack detected).
  * `status=503` spikes from the Redis/Vault global error handlers.
  * `p95_latency` exceeding 150ms on the `/transfer` endpoint.

---

## 4. Automated Rollback Procedure

The system is designed for **Self-Healing** and **Zero-Downtime Rollbacks**:

If the `/health` endpoint begins returning `503 Service Degraded` (or if `CHAOS_MODE` is accidentally active):

1. **LB Isolation**: The Load Balancer (AWS ALB / Nginx) will automatically mark the node as `Unhealthy` within 3 intervals (15 seconds).
2. **Traffic Drainage**: Traffic will automatically drain to previous deployment target groups (Blue/Green model).
3. **Audit Trail Preservation**: All transactional outbox events are preserved in the DB. Rolling back the API logic will not lose pending events; the background worker will resume processing from the previous state.
4. **Manual Override**: Re-run the pipeline on the previous Git SHA tag. The stateless architecture guarantees safe immediate reversion.

---

## 5. SRE Maintenance Tasks

* **Key Rotation**: PASETO Ed25519 keys should be rotated every 90 days via the `vault` rotation hook.
* **SBOM Audit**: Weekly review of `sbom.json` against the CISA Known Exploited Vulnerabilities (KEV) catalog.
* **Complexity Pruning**: Quarterly refactor of any functions approaching the **15/15 Complexity Threshold**.

---

Created by the High-Assurance Engineering Team
