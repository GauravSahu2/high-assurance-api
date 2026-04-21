"""
SLO/SLI Tests — Verify Service Level Objective definitions and error budgets.

These tests validate that:
    1. SLO definitions are mathematically correct
    2. Error budget calculator produces accurate results
    3. The API performance meets SLO thresholds
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from slo import (
    ALL_SLOS,
    AVAILABILITY_SLO,
    ERROR_RATE_THRESHOLD,
    LATENCY_SLO,
    LATENCY_THRESHOLD_MS,
    check_error_budget_remaining,
)


def test_availability_slo_is_defined():
    """SLO must define 99.9% availability target."""
    assert AVAILABILITY_SLO.target == 99.9
    assert AVAILABILITY_SLO.window_days == 30
    assert "5xx" in AVAILABILITY_SLO.sli_query.lower() or "5.." in AVAILABILITY_SLO.sli_query


def test_latency_slo_is_defined():
    """SLO must define p95 latency target for /transfer."""
    assert LATENCY_SLO.target == 95.0
    assert "/transfer" in LATENCY_SLO.sli_query


def test_error_budget_calculation_healthy():
    """Error budget should be 100% when there are no failures."""
    result = check_error_budget_remaining(10000, 0)
    assert result["status"] == "healthy"
    assert result["budget_remaining_pct"] == 100.0
    assert result["error_rate"] == 0.0


def test_error_budget_calculation_warning():
    """Error budget should warn when > 80% consumed."""
    # 99.9% target → 0.1% allowed → 10 failures per 10000 = budget fully consumed
    # 9 failures per 10000 = 90% consumed → warning
    result = check_error_budget_remaining(10000, 9)
    assert result["status"] == "warning"


def test_error_budget_calculation_breached():
    """Error budget should be breached when error rate exceeds SLO."""
    result = check_error_budget_remaining(10000, 100)
    assert result["status"] == "breached"
    assert result["budget_remaining_pct"] == 0


def test_error_budget_no_data():
    """Error budget should handle zero-request case gracefully."""
    result = check_error_budget_remaining(0, 0)
    assert result["status"] == "no_data"


def test_error_budget_minutes_per_month():
    """Verify downtime budget in minutes (99.9% target → 43.2 min/month)."""
    minutes = AVAILABILITY_SLO.error_budget_minutes_per_month
    assert abs(minutes - 43.2) < 0.1, f"Expected ~43.2 min/month, got {minutes}"


def test_all_slos_have_promql():
    """Every SLO must have a valid PromQL query for monitoring."""
    for slo in ALL_SLOS:
        assert slo.sli_query, f"SLO '{slo.name}' has no PromQL query"
        assert "rate(" in slo.sli_query or "histogram_quantile(" in slo.sli_query


def test_slo_thresholds_are_sane():
    """Verify threshold constants are reasonable."""
    assert LATENCY_THRESHOLD_MS == 500.0
    assert ERROR_RATE_THRESHOLD == 0.01


def test_api_health_endpoint_meets_latency_slo(client):
    """Verify the /health endpoint responds within latency SLO."""
    import time

    start = time.perf_counter()
    res = client.get("/health")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert res.status_code == 200
    assert (
        elapsed_ms < LATENCY_THRESHOLD_MS
    ), f"Health endpoint took {elapsed_ms:.1f}ms — exceeds {LATENCY_THRESHOLD_MS}ms SLO"
