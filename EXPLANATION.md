# High-Assurance API — Executive Technical Overview

<p align="center">
  <strong>A compliance-grade financial API platform with 20-tier defense-in-depth testing</strong><br>
  <em>Built for regulated industries: Fintech · Healthcare · Defense · Banking</em>
</p>

---

## For CTOs, VPs of Engineering & Technical Recruiters

This document explains what this project is, why it exists, and how it demonstrates
senior-level software engineering across security, compliance, and operational excellence.

---

## What Is This?

The **High-Assurance API** is a production-grade financial transfer service that implements:

- **JWT-authenticated fund transfers** with ACID guarantees
- **20-tier automated quality validation** from unit tests to disaster recovery
- **Real-time DAST security scanning** (OWASP ZAP) on every commit
- **100% code coverage** and **Mutation Testing** enforced as a CI gate
- **FDA 21 CFR Part 11, SOC 2, PCI DSS, and GDPR compliance testing**

It is simultaneously:
1. **A working API** you can deploy to production today
2. **A testing and compliance framework** that validates itself

---

## The 20-Tier Testing Architecture

This is the project's defining innovation. Every code change passes through **20 automated validation layers** before it can be merged:

| Tier | Category | What It Validates |
|:----:|----------|-------------------|
| 1 | **Functional BVA** | Boundary value analysis on all inputs |
| 2 | **Security** | Timing attacks, SSRF, XSS, BOLA, injection |
| 3 | **Property-Based** | Hypothesis fuzzing with 100+ generated test cases |
| 4 | **Compliance** | SOC 2, PCI DSS, FDA 21 CFR audit trail tests |
| 5 | **Contract** | OpenAPI schema conformance via Schemathesis |
| 6 | **SSRF Protection** | Egress client blocks all private/metadata IPs |
| 7 | **CSV Injection** | Pandera schema + injection prefix sanitization |
| 8 | **AI/MCP Boundaries** | Authorization containment (BOLA) verification |
| 9 | **Outbox Pattern** | Transactional event publishing reliability |
| 10 | **Integration Contracts** | CORS, caching, network seam tests |
| 11 | **Observability** | Correlation ID propagation, structured logging |
| 12 | **Rate Limiting** | Brute-force lockout at IP and user level |
| 13 | **Infrastructure Drift** | AWS config validation via moto mocks |
| 14 | **Performance** | Benchmark regressions gated at p95 latency |
| 15 | **Concurrency** | Double-spend prevention via ordered locking |
| 16 | **Chaos Engineering** | Health degradation under CHAOS_MODE |
| 17 | **Two-Person Rule** | CODEOWNERS enforcement validation |
| 18 | **OWASP ZAP DAST** | 117 security rules scanned against live API |
| 19 | **Deployment Rollback** | Automated rollback on health check failure |
| 20 | **Disaster Recovery** | Redis/DB failure isolation and recovery |
| 21 | **Secrets Management** | AWS Secrets Manager integration (moto) |
| 22 | **Policy-as-Code** | OPA/Rego policy enforcement |
| 23 | **Infrastructure** | Checkov 100% security scan completion (11 fixed, 2 suppressed) |
| 24 | **Secrets Scanning** | Gitleaks + Trivy CVE scanning |
| 25 | **Mutation Testing** | Mutmut configuration for core logic validation |

### How to Run It (Locally)

```bash
# Inner Loop (Logic + Security + Performance) — ~2 minutes
source venv/bin/activate
hsa -i

# Full 20-Tier Gauntlet (adds DAST, ZAP, static scanning) — ~3 minutes
hsa -a
```

**No cloud required.** Every tier runs on a developer laptop.

---

## As a SaaS Product

### Market Positioning

**"Compliance-as-Code for Financial APIs"**

The High-Assurance API platform can be positioned as an **internal developer platform (IDP)** or a **SaaS compliance validation service** for:

| Vertical | Pain Point Solved | Value Delivered |
|----------|------------------|-----------------|
| **Fintech** | PCI DSS compliance is manual and audit-heavy | Automated compliance validation on every commit |
| **Healthcare** | FDA 21 CFR Part 11 requires paper audit trails | Digital, immutable, timestamped audit events via OutboxEvent |
| **Banking** | Double-spend and race conditions cause losses | Deterministic lock ordering + idempotency keys |
| **Insurance** | SOC 2 audits require months of evidence gathering | `hsa -a` generates an audit bundle in 3 minutes |
| **Defense/Gov** | Zero-trust API security is mandated | SSRF protection, JWT revocation, BOLA enforcement |

### Revenue Model (Hypothetical)

```
├── Free Tier:       hsa CLI (open source, community)
├── Pro ($49/mo):    CI/CD pipeline integration + dashboard
├── Enterprise:      Custom compliance frameworks + dedicated support
└── Audit-as-a-Service: On-demand compliance certification bundles
```

### Competitive Differentiation

| Feature | High-Assurance API | Typical API Framework |
|---------|:-:|:-:|
| 20-tier automated testing | ✅ | ❌ |
| 100% code coverage + Mutmut | ✅ | ~70-80% |
| OWASP ZAP in local dev loop | ✅ | CI-only |
| FDA 21 CFR audit trails | ✅ | ❌ |
| SSRF-safe egress client | ✅ | Manual |
| Timing attack resistance | ✅ | ❌ |
| Policy-as-Code (OPA/Rego) | ✅ | ❌ |
| Programmatic SLO Error Budgets | ✅ | ❌ |

### Technical Architecture (SaaS Deployment)

```
┌──────────────────────────────────────────────────────────┐
│                    Load Balancer (ALB)                     │
├──────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ API Pod 1│  │ API Pod 2│  │ API Pod N│  ← Gunicorn    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │              │              │                     │
│  ┌────▼──────────────▼──────────────▼─────┐              │
│  │         PostgreSQL (RDS Multi-AZ)       │              │
│  │    Accounts │ IdempotencyKeys │ Outbox   │              │
│  └─────────────────────────────────────────┘              │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Redis (Rate │  │ Loki (Logs)  │  │ Grafana      │    │
│  │ Limiting)   │  │ + Promtail   │  │ (Dashboards) │    │
│  └─────────────┘  └──────────────┘  └──────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────┐              │
│  │  Outbox Worker (Background Processor)    │              │
│  │  Polls OutboxEvent → SQS/Kafka/Email     │              │
│  └─────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────┘
```

---

## As a Portfolio Project

### What This Demonstrates to a Recruiter

| Skill Category | Evidence |
|---------------|----------|
| **System Design** | Blueprint architecture, transactional outbox, idempotency |
| **Security Engineering** | SSRF protection, timing attack resistance, JWT revocation, BOLA, CSV injection defense |
| **Testing Mastery** | 288 tests, 20 tiers, property-based fuzzing, DAST, mutation testing, 100% coverage |
| **DevSecOps** | 9 GitHub Actions pipelines, Gitleaks, Trivy, ZAP, OPA |
| **Infra Security** | 100/100 Checkov score, rootless containers, read-only FS, NetPol |
| **Compliance** | FDA, SOC 2, PCI DSS, GDPR mapped to specific test assertions |
| **Observability** | OpenTelemetry + Prometheus SLOs + Grafana dashboards + structured logging |
| **Code Quality** | Type hints, docstrings, Flask Factory Pattern, clean architecture |
| **Operational Excellence** | K8s liveness/readiness probes, chaos engineering, automated rollbacks |

### Key Technical Decisions (Interview-Ready)

**1. Why Numeric(12,2) instead of Float for money?**
> IEEE 754 floating-point cannot represent 0.1 exactly. In financial systems,
> this causes penny-rounding errors that compound over millions of transactions.
> `Numeric(precision=12, scale=2)` stores exact decimal values.

**2. Why ordered lock acquisition in transfers?**
> `sorted([sender, receiver])` ensures both workers always lock accounts in
> the same order. Without this, Worker A locking (Alice, Bob) while Worker B
> locks (Bob, Alice) creates a deadlock.

**3. Why a DUMMY_HASH for non-existent users?**
> Without it, login attempts for non-existent users return instantly (no bcrypt
> computation), while real users take ~100ms. An attacker can enumerate valid
> usernames by measuring response times. The DUMMY_HASH forces constant-time
> behavior regardless of whether the user exists.

**4. Why the Transactional Outbox instead of publishing events directly?**
> If the API writes to the database AND publishes to Kafka in the same request,
> a crash between the two operations means either: (a) the transfer happened but
> no event was published, or (b) the event was published but the transfer rolled
> back. The Outbox writes both to the same database transaction — the worker
> reads from the Outbox table and publishes asynchronously, achieving exactly-once
> delivery without distributed transactions.

**5. Why SSRF protection in an internal API?**
> If an attacker can make the API issue HTTP requests (via file URLs, webhook
> configs, etc.), they can reach internal services, cloud metadata endpoints
> (169.254.169.254), and exfiltrate IAM credentials. The egress client blocks
> all private networks and cloud metadata endpoints by default.

---

## Project Structure

```
high-assurance-api/
├── src/                         # Application source code
│   ├── main.py                  # App factory + Blueprint registration
│   ├── auth.py                  # JWT generation, password hashing
│   ├── config.py                # Centralized configuration
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models.py                # Account, IdempotencyKey, OutboxEvent
│   ├── security.py              # HTTP security headers
│   ├── telemetry.py             # OpenTelemetry instrumentation
│   ├── csv_validator.py         # Pandera CSV validation + injection sanitization
│   ├── egress_client.py         # SSRF-safe HTTP client
│   ├── worker.py                # Transactional Outbox processor
│   ├── logger.py                # Structured JSON logging (structlog)
│   └── routes/                  # Flask Blueprints
│       ├── __init__.py          # Blueprint registration
│       ├── auth_routes.py       # /login, /logout
│       ├── transfer_routes.py   # /transfer
│       ├── health_routes.py     # /, /health, /metrics
│       ├── upload_routes.py     # /upload-dataset
│       └── admin_routes.py      # /api/users, /api/accounts (GDPR erasure)
├── tests/                       # 288 tests across 20+ tiers
│   ├── 1_functional/            # BVA, coverage, unit tests
│   ├── 2_security/              # Timing attacks, BOLA
│   ├── 4_compliance/            # SOC 2, PCI DSS, FDA
│   ├── 8_ai_mcp_boundaries/     # Authorization containment
│   ├── 10_integration_*/        # Contract + CORS tests
│   ├── 15_concurrency_*/        # Race condition tests
│   ├── 22_policy_as_code/       # OPA/Rego policies
│   └── ...                      # 14 more test directories
├── policies/                    # OPA Rego policy files
├── .github/                     # CI/CD (9 pipelines)
├── openapi.yaml                 # OpenAPI 3.0 specification
├── docker-compose.yml           # Full stack (API + DB + Redis + Grafana)
├── Dockerfile                   # Production container (non-root, slim)
└── hsa                          # CLI tool for running validation tiers
```

---

## Quick Start (30 seconds)

```bash
git clone https://github.com/GauravSahu2/high-assurance-api.git
cd high-assurance-api
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run the full 288-test, 20-tier validation:
hsa -i

# Deploy locally:
docker compose up -d
curl http://localhost:5000/health
```

---

## Contact

**Gaurav Sahu** — Full-Stack Security & DevSecOps Engineer

- GitHub: [@GauravSahu2](https://github.com/GauravSahu2)
- Focus: High-assurance systems, compliance automation, API security
