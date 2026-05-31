"""
SOL Telemetry System — OpenTelemetry Wrapper
===========================================
Defines the telemetry interfaces, tracer, metrics provider, and direct-to-dashboard exporters.
If the opentelemetry library is not installed, it transparently falls back to mock tracers/meters.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("sol.telemetry")

# Global variables
_TRACER = None
_METER = None
_IS_INITIALIZED = False
_DASHBOARD_ENDPOINT = os.getenv("SOL_TELEMETRY_ENDPOINT", "http://localhost:8000/api/telemetry")
_TELEMETRY_ENABLED = os.getenv("SOL_TELEMETRY_ENABLED", "true").lower() == "true"

try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, MetricExporter, MetricExportResult
    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False

# ---- Fallback Mock Implementations ----

class DummySpan:
    def __init__(self, name="dummy"):
        self.name = name
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    def set_attribute(self, key, value):
        return self
    def set_attributes(self, attributes):
        return self
    def record_exception(self, exception):
        return self
    def set_status(self, status, description=""):
        return self

class DummyTracer:
    def start_as_current_span(self, name, *args, **kwargs):
        return DummySpan(name)

class DummyCounter:
    def add(self, amount, attributes=None):
        pass

class DummyGauge:
    def set(self, value, attributes=None):
        pass

class DummyUpDownCounter:
    def add(self, amount, attributes=None):
        pass

class DummyMeter:
    def create_counter(self, name, unit="", description=""):
        return DummyCounter()
    def create_gauge(self, name, unit="", description=""):
        return DummyGauge()
    def create_up_down_counter(self, name, unit="", description=""):
        return DummyUpDownCounter()

# ---- Exporters (Only defined if OpenTelemetry is present) ----

if HAS_OPENTELEMETRY:
    class DirectHttpSpanExporter(SpanExporter):
        def __init__(self, endpoint: str = _DASHBOARD_ENDPOINT):
            self.endpoint = endpoint

        def export(self, spans) -> int:
            if not _TELEMETRY_ENABLED:
                return 0
            payload = []
            for span in spans:
                parent_id = format(span.parent.span_id, '016x') if span.parent else None
                span_data = {
                    "name": span.name,
                    "context": {
                        "trace_id": format(span.context.trace_id, '032x'),
                        "span_id": format(span.context.span_id, '016x'),
                    },
                    "parent_id": parent_id,
                    "start_time": span.start_time / 1e9 if span.start_time else None,
                    "end_time": span.end_time / 1e9 if span.end_time else None,
                    "attributes": dict(span.attributes) if span.attributes else {},
                    "status": {
                        "status_code": span.status.status_code.name if span.status.status_code else "UNSET",
                        "description": span.status.description or ""
                    }
                }
                payload.append(span_data)
            
            if not payload:
                return 0
            
            try:
                req = urllib.request.Request(
                    self.endpoint,
                    data=json.dumps({"spans": payload}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    pass
            except Exception:
                # Dashboard might not be running, drop telemetry silently
                pass
            return 0

        def shutdown(self) -> None:
            pass


    class DirectHttpMetricExporter(MetricExporter):
        def __init__(self, endpoint: str = _DASHBOARD_ENDPOINT):
            super().__init__()
            self.endpoint = endpoint

        def export(self, metrics_data, timeout_millis=1000, **kwargs) -> MetricExportResult:
            if not _TELEMETRY_ENABLED:
                return MetricExportResult.SUCCESS
            payload = []
            for resource_metric in metrics_data.resource_metrics:
                for scope_metric in resource_metric.scope_metrics:
                    for metric in scope_metric.metrics:
                        metric_data = {
                            "name": metric.name,
                            "description": metric.description or "",
                            "unit": metric.unit or "",
                            "data_points": []
                        }
                        # Handle different types of data points
                        try:
                            for point in metric.data.data_points:
                                point_data = {
                                    "attributes": dict(point.attributes) if point.attributes else {},
                                    "start_time_unix_nano": point.start_time_unix_nano,
                                    "time_unix_nano": point.time_unix_nano,
                                    "value": point.value
                                }
                                metric_data["data_points"].append(point_data)
                        except Exception:
                            pass
                        payload.append(metric_data)

            if not payload:
                return MetricExportResult.SUCCESS

            try:
                req = urllib.request.Request(
                    self.endpoint,
                    data=json.dumps({"metrics": payload}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    pass
            except Exception:
                pass
            return MetricExportResult.SUCCESS

        def shutdown(self, timeout_millis=3000, **kwargs) -> None:
            pass

        def force_flush(self, timeout_millis=10000, **kwargs) -> bool:
            return True

# ---- API Implementation ----

def init_telemetry(service_name: str = "sol-system"):
    """
    Initializes the OpenTelemetry providers and processors.
    Can be safely called multiple times.
    """
    global _TRACER, _METER, _IS_INITIALIZED
    
    if _IS_INITIALIZED:
        return

    if not _TELEMETRY_ENABLED:
        logger.info("SOL Telemetry is disabled via env variable.")
        _TRACER = DummyTracer()
        _METER = DummyMeter()
        _IS_INITIALIZED = True
        return

    if not HAS_OPENTELEMETRY:
        logger.warning("opentelemetry libraries not found. Falling back to mock telemetry.")
        _TRACER = DummyTracer()
        _METER = DummyMeter()
        _IS_INITIALIZED = True
        return

    try:
        # Set up TracerProvider
        trace_provider = TracerProvider()
        
        # Exporter directed to local dashboard
        direct_span_exporter = DirectHttpSpanExporter()
        span_processor = SimpleSpanProcessor(direct_span_exporter)
        trace_provider.add_span_processor(span_processor)
        
        # Add OTLP exporter if config allows
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                otlp_exporter = OTLPSpanExporter()
                from opentelemetry.sdk.trace.export import BatchSpanProcessor
                trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            except ImportError:
                pass

        trace.set_tracer_provider(trace_provider)
        _TRACER = trace.get_tracer(service_name)

        # Set up MeterProvider
        direct_metric_exporter = DirectHttpMetricExporter()
        # Export metrics every 1 second for real-time responsiveness in dashboard
        metric_reader = PeriodicExportingMetricReader(direct_metric_exporter, export_interval_millis=1000)
        
        meter_provider = MeterProvider(metric_readers=[metric_reader])
        
        # Add OTLP metric exporter if config allows
        otlp_metric_endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_metric_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
                otlp_m_exporter = OTLPMetricExporter()
                meter_provider.add_metric_reader(PeriodicExportingMetricReader(otlp_m_exporter))
            except ImportError:
                pass

        metrics.set_meter_provider(meter_provider)
        _METER = metrics.get_meter(service_name)

        _IS_INITIALIZED = True
        logger.info(f"SOL OpenTelemetry initialized successfully for service: {service_name}")
    except Exception as e:
        logger.error(f"Error initializing OpenTelemetry: {e}. Falling back to mock.")
        _TRACER = DummyTracer()
        _METER = DummyMeter()
        _IS_INITIALIZED = True


def get_tracer(service_name: str = "sol-system") -> DummyTracer | trace.Tracer:
    """Returns the initialized tracer instance."""
    global _TRACER
    if _TRACER is None:
        init_telemetry(service_name)
    return _TRACER


def get_meter(service_name: str = "sol-system") -> DummyMeter | metrics.Meter:
    """Returns the initialized meter instance."""
    global _METER
    if _METER is None:
        init_telemetry(service_name)
    return _METER


@contextmanager
def trace_span(name: str, attributes: dict | None = None, service_name: str = "sol-system"):
    """
    Convenient context manager for starting a span.
    
    Example::
    
        with trace_span("my-span", {"attr": "value"}):
            do_something()
    """
    tracer = get_tracer(service_name)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, v)
        yield span
