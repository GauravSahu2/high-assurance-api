"""
Health and infrastructure routes — liveness, readiness, and observability.

Endpoints:
    - / : API root (liveness)
    - /health : Deep health check (Redis + DB probe)
    - /metrics : Prometheus metrics endpoint
    - /openapi.yaml : OpenAPI specification
"""

from __future__ import annotations

import os
import random
import time

from flask import Blueprint, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from database import get_db
from models import Account

health_bp = Blueprint("health", __name__)


def _get_redis():
    import main

    return main.redis_client


@health_bp.route("/")
def home():
    """API liveness probe — returns immediately."""
    return jsonify({"message": "API running"})


@health_bp.route("/openapi.yaml")
def openapi_yaml():
    """Serve the OpenAPI specification file."""
    try:
        spec_path = os.path.join(os.path.dirname(__file__), "..", "..", "openapi.yaml")
        with open(spec_path) as f:
            return f.read(), 200, {"Content-Type": "text/yaml"}
    except FileNotFoundError:
        return jsonify({"error": "spec not found"}), 404


@health_bp.route("/health", methods=["GET", "OPTIONS"])
def health():
    """Deep health check — probes Redis and database connectivity.

    Returns 503 with rollback_flag if any infrastructure component
    is unreachable, enabling automated deployment rollbacks.
    """
    if request.method == "OPTIONS":
        return jsonify({}), 200

    redis_client = _get_redis()

    # Chaos engineering support
    if os.environ.get("CHAOS_MODE", "").lower() == "true" and random.random() < 0.5:
        return jsonify({"status": "chaos"}), 503

    # Redis probe
    try:
        redis_client.ping()
    except Exception:
        return (
            jsonify(
                {
                    "status": "degraded",
                    "infrastructure": "unreachable",
                    "rollback_flag": True,
                }
            ),
            503,
        )

    # Database probe
    try:
        db = next(get_db())
        db.query(Account).first()
    except Exception:
        return (
            jsonify(
                {
                    "status": "degraded",
                    "infrastructure": "unreachable",
                    "rollback_flag": True,
                }
            ),
            503,
        )

    return jsonify({"status": "ok", "timestamp": time.time()})


@health_bp.route("/metrics")
def metrics_endpoint():
    """Prometheus metrics scrape endpoint."""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}
