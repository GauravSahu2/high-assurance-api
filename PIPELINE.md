# 🌏 High-Assurance CI/CD Architecture

This document visualizes the 32-tier validation gauntlet and the Master Pipeline logic.

## Pipeline Flow

```mermaid
graph TD
    subgraph "Phase 1: Lint & Static"
        L1[Ruff API]
        L2[Black API]
        L3[Node Lint Dashboard]
    end

    subgraph "Phase 2: The 32-Tier Gauntlet"
        V1[Tiers 1-12: Core Logic]
        V2[Tiers 13-24: Integration]
        V3[Tiers 25-32: Compliance]
    end

    subgraph "Phase 3: Security & Quality"
        S1[SonarCloud]
        S2[Checkov IaC]
        S3[Mutation Testing]
    end

    subgraph "Phase 4: Distribution"
        D1[Multi-arch Docker]
        D2[SBOM Generation]
        D3[Cosign Signing]
    end

    Start --> L1 & L2 & L3
    L1 & L2 & L3 --> V1 --> V2 --> V3
    V3 --> S1 & S2 & S3
    S1 & S2 & S3 --> D1
    D1 --> D2 --> D3
    D3 --> Deploy[🚀 Zero-Downtime Deploy]
```

## Validation Tiers Breakdown

| Layer | Hierarchy | Focus |
|---|---|---|
| **Core** | Tiers 1-12 | Boundary Value Analysis, Security Timing, Idempotency, Schema Conformance |
| **Integration** | Tiers 13-24 | Transactional Outbox, Correlation Tracing, Rate Limiting, Complexity Matrix |
| **Compliance** | Tiers 25-32 | Disaster Recovery, SLSA Provenance, FDA Bundle Signing, DAST |

## Dependabot Stabilization
The pipeline is designed to be **Bot-Safe**:
- Non-critical scans (SonarCloud, ZAP) are bypassed for `dependabot[bot]` to prevent red PRs due to missing secrets.
- `JWT_SECRET` and `APP_AUTH_TOKEN` have secure defaults for testing environments.
- Dependency CVE scans are integrated via `Trivy` and `pip-audit`.
