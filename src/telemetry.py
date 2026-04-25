"""
OpenTelemetry instrumentation — distributed tracing configuration.

Provides:
    - TracerProvider with service metadata
    - Console exporter for local development
    - Optional OTLP exporter for production collectors
    - A shared tracer instance (hsa_tracer) for manual span creation
"""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from config import DEPLOY_ENV


def init_telemetry() -> trace.Tracer:
    """Initialize OpenTelemetry and return the application tracer."""
    resource = Resource.create(
        {
            "service.name": "high-assurance-api",
            "service.version": "2.0.0",
            "deployment.environment": DEPLOY_ENV,
        }
    )
    provider = TracerProvider(resource=resource)

    # Console exporter for local visibility
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # Optional OTLP collector for production
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint and not os.environ.get("TEST_MODE"):  # pragma: no cover
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)))
        except Exception:
            pass  # Graceful degradation if collector is unreachable

    trace.set_tracer_provider(provider)
    return trace.get_tracer("hsa.tracer", "2.0.0")


from prometheus_client import REGISTRY as _PROM_REGISTRY
from prometheus_client import Counter, Histogram


def _get_or_create_counter(name: str, desc: str, labels: list[str]) -> Counter:
    """Get existing counter or create new one — avoids duplicate registration."""
    existing = _PROM_REGISTRY._names_to_collectors.get(name)
    if existing:
        return existing
    return Counter(name, desc, labels)


def _get_or_create_histogram(name: str, desc: str, labels: list[str]) -> Histogram:
    """Get existing histogram or create new one — avoids duplicate registration."""
    existing = _PROM_REGISTRY._names_to_collectors.get(name)
    if existing:
        return existing
    return Histogram(name, desc, labels)


flask_http_request_total = _get_or_create_counter(
    "flask_http_request_total",
    "Total HTTP requests by method/endpoint/status",
    ["method", "endpoint", "status"],
)
http_request_duration_seconds = _get_or_create_histogram(
    "http_request_duration_seconds", "Request latency in seconds by endpoint", ["endpoint"]
)
