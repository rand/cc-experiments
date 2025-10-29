#!/usr/bin/env python3
"""
Complete OpenTelemetry distributed tracing setup.

Demonstrates:
- Automatic instrumentation for common frameworks
- Manual instrumentation for custom operations
- Jaeger exporter configuration
- Sampling strategies
- Context propagation
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace.sampling import (
    ParentBasedTraceIdRatioBased,
    TraceIdRatioBased,
    ALWAYS_ON,
    ALWAYS_OFF,
)

# Auto-instrumentation imports
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from flask import Flask
import requests


def initialize_tracing(
    service_name: str,
    service_version: str = "1.0.0",
    otlp_endpoint: str = "localhost:4317",
    sampling_rate: float = 0.1,
    environment: str = "production",
) -> trace.Tracer:
    """
    Initialize OpenTelemetry tracing with best practices.

    Args:
        service_name: Name of the service
        service_version: Version of the service
        otlp_endpoint: OTLP collector endpoint
        sampling_rate: Fraction of traces to sample (0.0-1.0)
        environment: Deployment environment

    Returns:
        Configured tracer instance
    """

    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": environment,
        "host.name": "production-host-1",
    })

    # Configure sampling strategy
    # Parent-based: If parent span is sampled, sample this one too
    # Otherwise, sample based on trace ID ratio
    sampler = ParentBasedTraceIdRatioBased(
        root=TraceIdRatioBased(sampling_rate),
    )

    # Create tracer provider
    provider = TracerProvider(
        resource=resource,
        sampler=sampler,
    )

    # Configure OTLP exporter for Jaeger/Zipkin
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=False,  # Use TLS in production
    )

    # Use batch processor for better performance
    span_processor = BatchSpanProcessor(
        otlp_exporter,
        max_queue_size=2048,
        max_export_batch_size=512,
        export_timeout_millis=30000,
    )
    provider.add_span_processor(span_processor)

    # Optional: Console exporter for debugging
    # console_processor = BatchSpanProcessor(ConsoleSpanExporter())
    # provider.add_span_processor(console_processor)

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Auto-instrument common frameworks
    FlaskInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    RedisInstrumentor().instrument()

    return trace.get_tracer(__name__)


def create_app(tracer: trace.Tracer) -> Flask:
    """Create Flask app with tracing."""
    app = Flask(__name__)

    @app.route("/users/<int:user_id>")
    def get_user(user_id):
        """Get user by ID with distributed tracing."""
        # Automatically traced by Flask instrumentation

        # Manual span for custom operation
        with tracer.start_as_current_span("validate_user_id") as span:
            span.set_attribute("user.id", user_id)

            if user_id <= 0:
                span.set_attribute("validation.result", "invalid")
                return {"error": "Invalid user ID"}, 400

            span.set_attribute("validation.result", "valid")

        # Database query (automatically traced)
        user_data = fetch_user_from_db(user_id, tracer)

        # External API call (automatically traced by requests instrumentation)
        with tracer.start_as_current_span("fetch_user_preferences") as span:
            span.set_attribute("user.id", user_id)

            try:
                response = requests.get(
                    f"https://preferences-api/users/{user_id}",
                    timeout=2.0
                )
                response.raise_for_status()
                preferences = response.json()

                span.set_attribute("http.status_code", response.status_code)

            except requests.RequestException as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                preferences = {"theme": "default"}

        return {
            "user": user_data,
            "preferences": preferences,
        }

    return app


def fetch_user_from_db(user_id: int, tracer: trace.Tracer) -> dict:
    """Fetch user from database with manual instrumentation."""

    with tracer.start_as_current_span("database.query.users") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.name", "users_db")
        span.set_attribute("db.statement", "SELECT * FROM users WHERE id = %s")
        span.set_attribute("db.user", "app_user")

        # Simulate database query
        import time
        time.sleep(0.05)  # 50ms query

        span.set_attribute("db.rows_affected", 1)

        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
        }


if __name__ == "__main__":
    # Initialize tracing
    tracer = initialize_tracing(
        service_name="user-api",
        service_version="1.0.0",
        otlp_endpoint="localhost:4317",
        sampling_rate=0.1,  # Sample 10% of traces
        environment="production",
    )

    # Create and run Flask app
    app = create_app(tracer)
    app.run(host="0.0.0.0", port=5000)
