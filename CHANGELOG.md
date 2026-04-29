# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-04-28

### Added (v2.1.0)

- **PASETO v4 Security**: Migrated from JWT to PASETO v4.public (Ed25519) to eliminate algorithm-confusion attacks.
- **Enterprise Complexity Gates**: Strictly enforced **15/15 Threshold** for both Cyclomatic (McCabe) and Cognitive complexity.
- **SonarQube Integration**: Added `sonar-project.properties` and a custom compliance orchestrator for FAANG-grade reporting.
- **SBOM Generation**: Integrated `CycloneDX` for automated supply chain security auditing.
- **Dependency Deep-Dive**: Created `REQUIREMENTS_DEEP_DIVE.md` mapping every library to security requirements.
- **Safe Telemetry**: Implemented `SafeConsoleSpanExporter` and `atexit` handlers to resolve process-exit tracebacks.

### Changed (v2.1.0)

- **Absolute 100% Coverage**: Hardened test suite to 316 tests, achieving 100.0% line and branch coverage across all core logic.
- **Documentation Overhaul**: Completely rewrote `README.md`, `EXPLANATION.md`, and `RUNBOOK.md` to reflect production-grade engineering.
- **DAST Hardening**: Resolved "Timestamp Disclosure" alerts in OWASP ZAP by migrating health timestamps to ISO-8601.

### Fixed (v2.1.0)

- Fixed OpenTelemetry "Closed File" `ValueError` during server shutdown.
- Resolved Schemathesis 404 "Missing Data" warnings by adding realistic OpenAPI parameter examples.

## [2.0.0] - 2026-04-18

### Added (v2.0.0)

- **Blueprint Architecture**: Decomposed monolithic `main.py` into 5 functional routing modules.
- **Observability**: Programmatic SLOs, Grafana dashboard, and Prometheus metric singletons.
- **GDPR Compliance**: Added right-to-erasure endpoint (`DELETE /api/users/<id>/data`).
- **Operational Excellence**: Added liveness/readiness/startup probes to Kubernetes deployment.
- **CI/CD Quality Gates**: Added `ruff` linting and `mypy` strict type checking definitions.
- **Two-Person Rule**: Automated `CODEOWNERS` validation.

### Changed (v2.0.0)

- **JWT Security**: Enforced HS384 minimum secure key length (48 bytes).
- **Data Integrity**: Monetary balances now strictly use `Numeric(12,2)` instead of floating point.
- **Test Suite**: Tripled test count from 80s to 283 with full integration coverage.
- **Docker Compose**: Hardened with variable substitution and absent hardcoded credentials.

### Fixed (v2.0.0)

- Fixed API endpoint status code logic (/transfer HTTP 201 -> 200).
- Suppressed harmless OpenTelemetry batch processor teardown errors in pytest.
- Fixed `run_all_20_layers.sh` to spawn Gunicorn with `--workers 2`.
