# HSA-API Emergency Runbook

## Scenario: Database Schema Mismatch
**Symptoms:** API or Worker crashing with `UndefinedTable` errors.
**Fix:** 1. `docker compose run --rm api alembic upgrade head`
2. `docker compose restart`

## Scenario: Global Lockout (Redis failure)
**Symptoms:** All requests returning 429 even for valid users.
**Fix:**
1. `docker compose exec redis redis-cli FLUSHALL`

## Scenario: Outbox Worker Stalled
**Symptoms:** DB is growing, but events aren't being dispatched.
**Check:** `docker compose logs -f worker`
**Fix:** Restart the singleton: `docker compose restart worker`
