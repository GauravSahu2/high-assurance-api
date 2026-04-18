# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-04-18
### Added
- **Blueprint Architecture**: Decomposed monolithic `main.py` into 5 functional routing modules.
- **Observability**: Programmatic SLOs, Grafana dashboard, and Prometheus metric singletons.
- **GDPR Compliance**: Added right-to-erasure endpoint (`DELETE /api/users/<id>/data`).
- **Operational Excellence**: Added liveness/readiness/startup probes to Kubernetes deployment.
- **CI/CD Quality Gates**: Added `ruff` linting and `mypy` strict type checking definitions.
- **Two-Person Rule**: Automated `CODEOWNERS` validation.

### Changed
- **JWT Security**: Enforced HS384 minimum secure key length (48 bytes).
- **Data Integrity**: Monetary balances now strictly use `Numeric(12,2)` instead of floating point.
- **Test Suite**: Tripled test count from 80s to 283 with full integration coverage.
- **Docker Compose**: Hardened with variable substitution and absent hardcoded credentials.

### Fixed
- Fixed API endpoint status code logic (/transfer HTTP 201 -> 200).
- Suppressed harmless OpenTelemetry batch processor teardown errors in pytest.
- Fixed `run_all_20_layers.sh` to spawn Gunicorn with `--workers 2`.
