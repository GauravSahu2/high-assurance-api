# 🛡️ High-Assurance Quality Architecture (20-Tier)

[![CI/CD](https://img.shields.io/badge/CI%2FCD-20%20Tiers%20Passing-success?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/GauravSahu2/high-assurance-api/actions) [![k6](https://img.shields.io/badge/Load%20Test-k6-7D64FF?style=for-the-badge&logo=k6&logoColor=white)](#) [![Playwright](https://img.shields.io/badge/E2E-Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](#) [![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](#) [![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](#)

A property-tested DevSecOps and quality engineering platform designed for strict regulatory environments (Fintech, Healthcare). This platform implements a 20-tier defense-in-depth testing strategy validating everything from live browser UI authentication down to DB ACID rollbacks, cloud infrastructure drift detection, and AI prompt-injection protections — all producing cryptographically signed, timestamped FDA-grade audit bundles.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
   - [Phase 1 — Core Logic & Security](#phase-1--core-logic--security)
   - [Phase 2 — Integration & Performance](#phase-2--integration--performance)
   - [Phase 3 — Operational Safeguards (Insider Threat)](#phase-3--operational-safeguards-insider-threat)
3. [20-Tier Matrix](#20-tier-matrix)
4. [Project Structure](#project-structure)
5. [Execution & Orchestration](#execution--orchestration)
   - [Prerequisites](#prerequisites)
   - [Installation & Environment Setup](#installation--environment-setup)
   - [Local Execution (Master Runner)](#local-execution-master-runner)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Best Practices & Operational Notes](#best-practices--operational-notes)
8. [Contact & License](#contact--license)

---

## Executive Summary

This repository encapsulates a formalized, auditable approach to software correctness, security, and operational resilience. The 20-tier approach combines property-based testing, automated regression, runtime synthetic monitoring, and cryptographic operational controls to meet strict regulatory and enterprise reliability needs.

Every tier is executed by a single orchestrator (`run_all_20_layers.sh`) and produces a timestamped, SHA-256 signed audit evidence bundle suitable for regulatory review.

---

## Architecture Overview

The architecture is divided into **three critical phases** to guarantee functional correctness and operational resilience.

### Phase 1 — Core Logic & Security

- **Functional / BVA** — Boundary-validated testing of input limits and edge cases using Boundary Value Analysis.
- **Security / BOLA** — Verifies that bounded resources cannot be accessed by unauthorized principals across all exposed endpoints. Tests hit the live running API.
- **Resilience / Idempotency** — Verifies safe retries and duplicate suppression. The `/transfer` endpoint enforces `X-Idempotency-Key` uniqueness within the replay window.
- **Compliance** — Compliant with 21 CFR Part 11.10(d) and 11.10(e) access controls and audit trails, alongside regex-based PII and secret scanning of runtime logs.
- **Frontend E2E** — Playwright (Chromium) tests for live browser UI authentication boundary enforcement, including both invalid and valid login flows via DOM assertion.
- **Database State** — ACID transaction rollback verified under injected failure conditions (e.g., malformed SQL column names).
- **Edge Infrastructure** — Multi-cloud WAF boundary verification across AWS (WAFv2), Azure (Front Door), and GCP (Cloud Armor) with graceful simulation fallbacks.
- **AI / MCP Boundaries** — Defends against prompt injection and tool-call hijacking in AI agents using an allowlist-based tool execution policy.

### Phase 2 — Integration & Performance

- **Synthetic Monitoring** — Live API heartbeat check confirming the `/health` endpoint is reachable and returning 200.
- **Integration Seams** — JSON Schema contract enforcement (consumer-driven contract testing) and CORS/cache-control header validation at the edge.
- **Distributed Tracing** — Verifies the live API `@after_request` middleware propagates `X-Correlation-ID` response headers, validated via real HTTP request assertions.
- **Auth Rate Limiting** — Hits the live `/login` endpoint to verify IP-based lockout returns HTTP 429 after 5 consecutive failed attempts.
- **Dependency Secrets** — Regex-based scanning for hardcoded AWS Access Key IDs and RSA/SSH private keys across `src/` and `tests/`.
- **Algorithmic Complexity** — Enforces O(N) time and space constraints via bounded benchmark regression using `tracemalloc` and `perf_counter`.
- **Concurrency** — Mutex-protected double-spend prevention test using `threading.Lock` with concurrent executor simulation.

### Phase 3 — Operational Safeguards (Insider Threat)

- **DB Destructive Guards** — Fresh snapshot enforcement before `DROP`/`TRUNCATE`/mass `DELETE` operations via a secure DB proxy pattern.
- **Two-Person Rule** — Senior/Lead approver enforcement for deployments touching critical paths (`infra/terraform`, `src/auth`, `src/database_migrations`).
- **Infrastructure Drift** — Live moto-backed AWS EC2 security group creation and port scan to detect unauthorized firewall rule changes.
- **Deployment Rollbacks** — Blue/Green canary rollback simulation triggered by 5xx error rate spikes, verifying 100% traffic reversion to stable.
- **Disaster Recovery** — Automated backup recency and size integrity checks to verify RTO/RPO targets are met.

---

## 20-Tier Matrix

| Tier | Category | Test File | Method |
|:---:|---|---|---|
| 1 | Functional / BVA | `tests/1_functional/test_bva.py` | Pytest parametrize (6 boundary cases) |
| 2 | Security / BOLA | `tests/2_security_bola/test_bola.py` | Live HTTP to `/api/resource` |
| 2 | Timing Attack Resistance | `tests/2_security/test_timing.py` | `time.perf_counter` variance assertion |
| 3 | Resilience / Idempotency | `tests/3_resilience/test_idempotency.py` | Duplicate UUID replay test |
| 4 | PII Zero-Leak Scan | `tests/4_compliance/zero_leak_check.sh` | Regex grep on `logs/api.log` |
| 5 | Frontend E2E | `tests/5_frontend_e2e/test_token_expiry.spec.js` | Playwright Chromium browser test |
| 6 | Database ACID State | `tests/6_database_state/test_transaction_rollback.py` | SQLite in-memory rollback |
| 7 | Edge Infrastructure | `tests/7_edge_and_infrastructure/edge_security_checks.sh` | Multi-cloud CLI verification |
| 8 | AI / MCP Boundaries | `tests/8_ai_mcp_boundaries/test_mcp_security.py` | Allowlist tool-call enforcement |
| 9 | Synthetic Monitoring | `tests/9_synthetic_monitoring/heartbeat_monitor.py` | Live HTTP heartbeat |
| 10 | Integration Contracts | `tests/10_integration_contracts/` (4 files) | JSON Schema, CORS, Pool, IAM |
| 10 | Network Seams / CORS | `tests/10_integration_seams/test_network_seams.py` | Live HTTP OPTIONS request |
| 11 | Observability / Tracing | `tests/11_observability_tracing/test_correlation_id.py` | Live HTTP header assertion |
| 12 | Auth Rate Limiting | `tests/12_auth_rate_limiting/test_brute_force_lockout.py` | Live HTTP brute-force to 429 |
| 13 | Dependency Secrets | `tests/13_dependency_secrets/scan_hardcoded_secrets.sh` | Regex entropy scan |
| 14 | Algorithmic Complexity | `tests/14_algorithmic_complexity/` (2 files) | O(N) time & space regression |
| 14 | k6 Load Testing | `tests/14_performance_complexity/k6_stress_profile.js` | k6 (p95 < 200ms threshold) |
| 15 | Concurrency / Race Conditions | `tests/15_concurrency_race_conditions/test_race_conditions.py` | `threading.Lock` double-spend |
| 16 | DB Operational Safeguards | `tests/16_db_operational_safeguards/test_db_destructive_guards.py` | Snapshot-gated destruction |
| 17 | Two-Person Rule | `tests/17_two_person_rule/test_two_person_rule.py` | Approver role enforcement |
| 18 | Infrastructure Drift | `tests/18_infra_drift_prevention/test_infra_drift.py` | moto EC2 security group scan |
| 19 | Deployment Rollbacks | `tests/19_deployment_rollbacks/test_automated_rollback.py` | Blue/Green canary simulation |
| 20 | Disaster Recovery | `tests/20_disaster_recovery/test_backup_integrity.py` | Backup recency & size check |

---

## Project Structure

```text
.
├── .github/workflows/          # GitHub Actions CI/CD (single-job, all 20 tiers)
├── src/
│   └── main.py                 # Flask API (login, transfer, BOLA resource, health)
├── tests/
│   ├── conftest.py             # Shared pytest fixtures (api_base_url, auth_header)
│   ├── 1_functional/
│   ├── 2_security/ & 2_security_bola/
│   ├── 3_resilience/
│   ├── 4_compliance/
│   ├── 5_frontend_e2e/         # Playwright spec
│   ├── 6_database_state/
│   ├── 7_edge_and_infrastructure/
│   ├── 8_ai_mcp_boundaries/
│   ├── 9_synthetic_monitoring/
│   ├── 10_integration_contracts/ & 10_integration_seams/
│   ├── 11_observability_tracing/
│   ├── 12_auth_rate_limiting/
│   ├── 13_dependency_secrets/
│   ├── 14_algorithmic_complexity/ & 14_performance_complexity/
│   ├── 15_concurrency_race_conditions/
│   ├── 16_db_operational_safeguards/
│   ├── 17_two_person_rule/
│   ├── 18_infra_drift_prevention/
│   ├── 19_deployment_rollbacks/
│   └── 20_disaster_recovery/
├── docs/
│   ├── OPERATIONS_SRE.md       # SLOs, error budgets, JSON log schema
│   ├── SECURITY_POLICIES.md    # Data classification, trust boundaries, secret rotation
│   └── WARNING_SUPPRESSION.md  # ADR for pytest.ini botocore suppression
├── audit_reports/              # Generated bundles (gitignored, uploaded to CI artifacts)
├── logs/                       # Runtime API logs (gitignored)
├── run_all_20_layers.sh        # Local master orchestrator
├── generate_audit_bundle.sh    # SHA-256 recursive manifest + zip
├── playwright.config.js        # Playwright config (baseURL, Chromium, trace-on-retry)
├── pytest.ini                  # Warning filters
├── requirements.in             # Direct Python dependencies (pip-compile source)
├── requirements.txt            # Pinned lockfile (generated, do not edit manually)
├── docker-compose.yml          # Docker alternative for local API boot
├── .env.example                # Environment variable template
└── .gitignore                  # Excludes bundles, logs, venv, playwright artifacts
```

---

## Execution & Orchestration

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.12+ | API + test runner |
| pip-tools | latest | Deterministic dependency compilation |
| Node.js | 18+ | Playwright browser runner |
| k6 | latest | Load & stress testing (Tier 14) |
| awscli-local | latest | LocalStack mock for AWS tests |

### Installation & Environment Setup

```bash
# 1. Clone the repository
git clone https://github.com/GauravSahu2/high-assurance-api.git
cd high-assurance-api

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Compile the pinned lockfile from direct dependencies and install
pip install pip-tools awscli-local
pip-compile requirements.in -o requirements.txt
pip install -r requirements.txt

# 4. Install Playwright and its Chromium browser binary
npm install @playwright/test
npx playwright install chromium

# 5. Configure environment variables
cp .env.example .env
# Edit .env and set ADMIN_PASSWORD and APP_AUTH_TOKEN
```

#### Docker Alternative

To boot only the API in an isolated container (useful for integration testing):

```bash
# Requires a populated .env file (not .env.example)
docker-compose up
```

### Local Execution (Master Runner)

Run the complete 20-tier suite with a single command:

```bash
chmod +x run_all_20_layers.sh
./run_all_20_layers.sh
```

The orchestrator will:

1. Boot the Flask API and wait for it to bind on port 8000
2. Run all 27 pytest tests across Tiers 1–20 (excluding Playwright and shell-based tiers)
3. **Reset API state** — restarts the process to clear IP-based brute-force lockouts before E2E
4. Run Playwright E2E (Tier 5) against the live Flask UI in a real Chromium browser
5. Execute PII scan, multi-cloud edge audit, synthetic heartbeat, and secrets scan
6. Run k6 load test against `/health` and `/transfer` with `p(95) < 200ms` threshold
7. Package all evidence (logs, XML results, Playwright traces, ADR docs) into a timestamped, SHA-256 signed FDA audit bundle

**Environment variable override for k6:**

The k6 script reads `APP_AUTH_TOKEN` from the environment automatically via the runner:

```bash
APP_AUTH_TOKEN=my_token ./run_all_20_layers.sh
```

---

## CI/CD Pipeline

Every push and pull request to `main` triggers the full 20-tier suite via GitHub Actions (`.github/workflows/high-assurance-pipeline.yml`).

The pipeline:

- Installs k6 via the official Grafana APT repository
- Compiles and installs Python dependencies from `requirements.in`
- Installs Playwright and Chromium
- Executes `run_all_20_layers.sh` with secrets injected from GitHub Secrets (`ADMIN_PASSWORD`, `APP_AUTH_TOKEN`)
- Uploads the complete `audit_reports/` directory as a CI artifact retained for **30 days** under the name `Compliance-Artifacts`

> If GitHub Secrets are not configured, the pipeline falls back to safe development defaults, allowing the suite to run in fork or demo contexts without secret configuration.

---

## Best Practices & Operational Notes

- Use **immutable artifacts** for release binaries and container images.
- Enforce **least privilege** for all test harnesses that mock IAM — use `@mock_aws` with `unittest.mock.patch` rather than live cloud calls.
- Maintain a **dedicated test-only keyset** for secrets scanning and rotate automatically. Never commit `.env` — only `.env.example`.
- Enforce the **two-person rule** for any schema or infrastructure change that can cause an irreversible data action.
- Store all artifacts and test results in an auditable, append-only store to comply with **21 CFR Part 11**.
- All application logs are emitted in **structured JSON** (including `trace_id` from `X-Correlation-ID`) to satisfy the schema defined in `docs/OPERATIONS_SRE.md`.
- Audit bundles are **excluded from git** (`.gitignore`) and captured exclusively as CI artifacts to prevent repository bloat.

---

## Contact & License

🔒 © 2026 Gaurav Sahu — High-Assurance Quality Engineering

This repository is maintained strictly for portfolio demonstration and personal practice purposes.

**Proprietary Work:** This is not an open-source project. All rights are reserved. No part of this repository may be redistributed, modified, or used for commercial purposes without explicit permission.

**No Contributions:** This project is not open for external contributions. Pull requests and issues from external contributors will not be reviewed or merged.

**Purpose:** This code serves as a technical showcase of high-assurance engineering principles, DevSecOps orchestration, and regulatory compliance automation.

**Contact:** [linkedin.com/in/gauravsahu22](https://www.linkedin.com/in/gauravsahu22) | Gauravsahu2203@gmail.com
