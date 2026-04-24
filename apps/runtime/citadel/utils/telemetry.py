"""
OpenTelemetry telemetry utility â€” gracefully degrades if OTel is not installed.

When OTel packages are available:
  - Full W3C Trace Context propagation
  - OTLP export to collector
  - Console exporter for dev

When OTel packages are NOT installed:
  - No-op tracer (zero overhead, no errors)
  - All instrumentation calls silently succeed
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False
    logger.debug("OpenTelemetry not installed â€” telemetry disabled (no-op)")


class _NoOpSpan:
    """Minimal no-op span for when OTel is unavailable."""
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def set_attribute(self, key, value): pass
    def set_status(self, status): pass
    def record_exception(self, exc): pass
    def end(self): pass


class _NoOpTracer:
    """Minimal no-op tracer for when OTel is unavailable."""
    def start_as_current_span(self, name, **kwargs):
        return _NoOpSpan()


def setup_telemetry(service_name: str = "Citadel-runtime") -> None:
    """Initialize OpenTelemetry with W3C Trace Context."""
    if not _OTEL_AVAILABLE:
        logger.info("OpenTelemetry not available â€” skipping telemetry setup")
        return

    # Set up Resource
    resource = Resource.create(attributes={
        SERVICE_NAME: service_name,
        "environment": os.getenv("CITADEL_ENV", "development")
    })

    # Initialize TracerProvider
    provider = TracerProvider(resource=resource)

    # Add Console Exporter for dev
    if os.getenv("CITADEL_LOG_LEVEL") == "DEBUG":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # Add OTLP Exporter if endpoint is provided
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OTLP exporter configured for {otlp_endpoint}")
        except ImportError:
            logger.warning("opentelemetry-exporter-otlp not installed â€” OTLP export disabled")

    # Set global TracerProvider
    trace.set_tracer_provider(provider)

    # Enable W3C Trace Context propagation
    set_global_textmap(TraceContextTextMapPropagator())

    logger.info(f"OpenTelemetry initialized for {service_name}")


def get_tracer(name: str = "Citadel"):
    """Get a tracer instance. Returns no-op tracer if OTel is unavailable."""
    if _OTEL_AVAILABLE:
        return trace.get_tracer(name)
    return _NoOpTracer()
