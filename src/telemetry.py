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

from config import DEPLOY_ENV
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


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
