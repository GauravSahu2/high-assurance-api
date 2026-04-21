"""
Service Level Objectives (SLOs) — Programmatic SLI/SLO Definitions.

These SLOs define the reliability contracts for the High-Assurance API.
They are enforced in CI via performance benchmark tests (Tier 14) and
monitored in production via Prometheus + Grafana alerting.

Reference: Google SRE Book, Chapter 4 — Service Level Objectives
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SLO:
    """A Service Level Objective definition."""

    name: str
    description: str
    target: float  # Target percentage (e.g., 99.9)
    window_days: int  # Rolling window (e.g., 30)
    sli_query: str  # Prometheus PromQL for the SLI
    error_budget: float  # Derived: 100 - target

    @property
    def error_budget_minutes_per_month(self) -> float:
        """Calculate how many minutes of downtime are allowed per 30-day window."""
        return (100 - self.target) / 100 * self.window_days * 24 * 60


# ── Production SLOs ───────────────────────────────────────────────────────────

AVAILABILITY_SLO = SLO(
    name="API Availability",
    description="Percentage of non-5xx responses across all endpoints",
    target=99.9,
    window_days=30,
    sli_query=(
        '1 - (sum(rate(flask_http_request_total{status=~"5.."}[5m])) ' "/ sum(rate(flask_http_request_total[5m])))"
    ),
    error_budget=0.1,
)

LATENCY_SLO = SLO(
    name="Transfer Latency (p95)",
    description="95th percentile latency for /transfer endpoint",
    target=95.0,
    window_days=30,
    sli_query=("histogram_quantile(0.95, " 'rate(http_request_duration_seconds_bucket{endpoint="/transfer"}[5m]))'),
    error_budget=5.0,
)

LATENCY_THRESHOLD_MS: float = 500.0  # p95 must be under 500ms

ERROR_RATE_THRESHOLD: float = 0.01  # Max 1% error rate before alerting

# ── All SLOs (used by tests and monitoring) ───────────────────────────────────
ALL_SLOS: list[SLO] = [AVAILABILITY_SLO, LATENCY_SLO]


def check_error_budget_remaining(
    total_requests: int,
    failed_requests: int,
    slo: SLO = AVAILABILITY_SLO,
) -> dict:
    """Check how much error budget remains for a given SLO.

    Returns a dict with budget status for dashboards/alerting.
    """
    if total_requests == 0:
        return {"status": "no_data", "budget_remaining_pct": 100.0}

    error_rate = failed_requests / total_requests
    budget_consumed_pct = (error_rate / (1 - slo.target / 100)) * 100
    budget_remaining_pct = max(0, 100 - budget_consumed_pct)

    return {
        "slo_name": slo.name,
        "slo_target": slo.target,
        "error_rate": round(error_rate * 100, 4),
        "budget_consumed_pct": round(budget_consumed_pct, 2),
        "budget_remaining_pct": round(budget_remaining_pct, 2),
        "status": ("healthy" if budget_remaining_pct > 20 else "warning" if budget_remaining_pct > 0 else "breached"),
    }
