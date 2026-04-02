# Operational Runbook: High-Assurance API

## 1. Environment Variables Reference

| Variable | Description | Default | Production Target |
|----------|-------------|---------|-------------------|
| `REDIS_URL` | Connection string for the Redis state backend. | `redis://localhost:6379/0` | Elasticache / Redis cluster URI |
| `JWT_SECRET` | Secret key used for signing JWTs. | (AWS Secret fallback) | Ensure AWS IAM access is granted |
| `OTEL_EXPORTER_OTLP_ENDPOINT`| OpenTelemetry collector endpoint for distributed tracing. | `http://localhost:4318/v1/traces` | Local sidecar proxy proxying to Datadog/NewRelic |
| `TEST_MODE` | dynamically lowers `bcrypt` work-factor to 4 for fast testing. | `false` | MUST BE UNSET IN PROD |
| `CHAOS_MODE` | Injects synthetic 503 errors into `/health`. | `false` | MUST BE UNSET IN PROD |

## 2. Deployment Guide
1. Verify CI/CD pipeline passes (Coverage: 100%, ZAP: Clean, Fuzzer: Clean).
2. Install strict dependencies: `pip install -r requirements.txt`.
3. Boot horizontally scalable WSGI server: `gunicorn --threads 4 --workers 3 -b 0.0.0.0:5000 main:app`
4. Confirm health: `curl -I http://localhost:5000/health` (Must return 200 OK).

## 3. Incident Response & Architectural Tradeoffs
* **Login Fail-Open Decision:** If Redis becomes unavailable, the API prioritizes availability. It continues serving `/login` requests, but IP-based brute-force rate limiting is suspended.
* **Monitoring Priority:** Set P1 alerts on `flask_http_request_total` where `status=429` spikes, or where `status=503` spikes from the Redis global error handler.

## 4. Automated Rollback Procedure
If the `/health` endpoint begins returning `503 Service Degraded` (or if `CHAOS_MODE` is accidentally active):
1. The Load Balancer (AWS ALB / Nginx) will automatically mark the node as `Unhealthy` within 3 intervals.
2. Traffic will automatically drain to previous deployment target groups.
3. **Manual Override:** Re-run pipeline on the previous Git SHA tag. The stateless architecture guarantees safe immediate reversion.
