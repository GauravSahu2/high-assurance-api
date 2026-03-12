# High-Assurance Quality Engineering Architecture (20-Tier)

An enterprise-grade, mathematically verified DevSecOps and Quality Engineering platform designed for strict regulatory compliance (FDA 21 CFR Part 11, Fintech, and Healthcare).

## 🏗️ Architecture Overview

This project goes beyond standard unit testing. It implements a **20-Tier Defense-in-Depth** testing strategy, validating everything from UI token expiry down to database ACID rollbacks, infrastructure drift, and AI prompt injection.

### The 20 Tiers of Assurance:

**Phase 1: Core Logic & Security**
1. **Functional / BVA:** Extreme boundary testing.
2. **Security / BOLA:** Broken Object Level Authorization prevention.
3. **Resilience / Idempotency:** Network glitch double-charge prevention.
4. **Compliance:** FDA-grade Zero-Leak PII & Secret scanning.
5. **Frontend E2E:** JWT Expiry & UI graceful degradation (Playwright).
6. **Database State:** ACID Transaction Rollback verification.
7. **Edge Infrastructure:** TLS Expiry math & WAF DDoS resistance.
8. **AI / MCP Boundaries:** Prompt Injection & Tool boundary enforcement.

**Phase 2: Integration & Performance**
9. **Synthetic Monitoring:** 24/7 API heartbeat tracking.
10. **Integration Seams:** Native JSON Schema contracts & AWS IAM Least-Privilege mocking.
11. **Distributed Tracing:** X-Correlation-ID microservice tracking.
12. **Auth Rate Limiting:** Brute-force account lockouts.
13. **Dependency Secrets:** Git-hook level AWS & RSA key detection.
14. **Algorithmic Complexity:** O(N) Time & Space complexity (ReDoS prevention).
15. **Concurrency:** Mutex Row-Level Locking to prevent Double-Spend race conditions.

**Phase 3: Operational Safeguards (Insider Threat)**
16. **DB Destructive Guards:** Requires fresh snapshots for `DROP`/`DELETE` queries.
17. **Two-Person Rule:** Cryptographic Senior-level sign-off for critical infrastructure changes.
18. **Infrastructure Drift:** Code-to-Cloud firewall state verification.
19. **Deployment Rollbacks:** Automated Blue/Green canary rollbacks on 500 errors.
20. **Disaster Recovery:** Automated backup integrity and file-size verification.

## 🚀 Execution & Orchestration

### Local Execution (The Master Runner)
To execute all 20 layers locally within a secure, isolated virtual environment:
```bash
# 1. Activate the environment
source venv/bin/activate

# 2. Run the master orchestrator
./run_all_20_layers.sh
