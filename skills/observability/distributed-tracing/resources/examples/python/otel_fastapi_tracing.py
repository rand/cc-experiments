"""
OpenTelemetry FastAPI Distributed Tracing Example

Complete example showing auto-instrumentation and manual spans in FastAPI
with trace context propagation to downstream services.

Requirements:
    pip install fastapi uvicorn opentelemetry-api opentelemetry-sdk \
        opentelemetry-instrumentation-fastapi \
        opentelemetry-instrumentation-requests \
        opentelemetry-exporter-otlp

Usage:
    python otel_fastapi_tracing.py

    # With custom OTLP endpoint
    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 python otel_fastapi_tracing.py
"""

import os
import time
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode

# Configuration
SERVICE_NAME = os.getenv("SERVICE_NAME", "user-api")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
DOWNSTREAM_SERVICE = os.getenv("DOWNSTREAM_SERVICE", "http://localhost:8001")

# Initialize OpenTelemetry
def init_tracer():
    """Initialize OpenTelemetry tracer with OTLP exporter."""
    # Create resource with service identity
    resource = Resource.create({
        "service.name": SERVICE_NAME,
        "service.version": "1.0.0",
        "deployment.environment": "development"
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter (send to collector/backend)
    otlp_exporter = OTLPSpanExporter(
        endpoint=OTLP_ENDPOINT,
        insecure=True  # Use for development only
    )
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Also add console exporter for debugging
    console_exporter = ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)


# Initialize tracer
tracer = init_tracer()

# Create FastAPI app
app = FastAPI(title="User API", version="1.0.0")

# Instrument FastAPI (auto-creates spans for all endpoints)
FastAPIInstrumentor.instrument_app(app)

# Instrument requests library (auto-propagates context)
RequestsInstrumentor().instrument()


# In-memory user database (mock)
USERS_DB = {
    "123": {"id": "123", "name": "Alice", "email": "alice@example.com"},
    "456": {"id": "456", "name": "Bob", "email": "bob@example.com"},
}


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": SERVICE_NAME, "status": "healthy"}


@app.get("/users/{user_id}")
async def get_user(user_id: str):
    """
    Get user by ID.

    Demonstrates:
    - Auto-instrumentation (span created by FastAPIInstrumentor)
    - Manual span creation
    - Span attributes
    - Error handling with span status
    """
    # Get current span (created by FastAPIInstrumentor)
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", user_id)

    # Create manual span for database lookup
    with tracer.start_as_current_span("db.get_user") as span:
        span.set_attribute("db.system", "in-memory")
        span.set_attribute("db.operation", "SELECT")
        span.set_attribute("db.table", "users")
        span.set_attribute("user.id", user_id)

        # Simulate database query time
        time.sleep(0.05)

        user = USERS_DB.get(user_id)

        if not user:
            span.add_event("cache.miss", {"key": f"user:{user_id}"})
            span.set_status(Status(StatusCode.ERROR, "User not found"))
            raise HTTPException(status_code=404, detail="User not found")

        span.add_event("cache.hit", {"key": f"user:{user_id}"})
        span.set_attribute("user.found", True)

    # Create span for external service call
    with tracer.start_as_current_span("fetch_user_preferences") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.url", f"{DOWNSTREAM_SERVICE}/preferences/{user_id}")

        try:
            # Context automatically propagated by RequestsInstrumentor
            response = requests.get(
                f"{DOWNSTREAM_SERVICE}/preferences/{user_id}",
                timeout=2
            )
            response.raise_for_status()

            preferences = response.json()
            user["preferences"] = preferences

            span.set_attribute("http.status_code", response.status_code)
            span.set_status(Status(StatusCode.OK))

        except requests.exceptions.RequestException as e:
            # Record exception in span
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))

            # Use default preferences on error
            user["preferences"] = {"theme": "light", "language": "en"}

    return user


@app.post("/users")
async def create_user(name: str, email: str):
    """
    Create a new user.

    Demonstrates:
    - Multiple manual spans
    - Span events for state transitions
    - Attribute namespacing
    """
    with tracer.start_as_current_span("validate_user_input") as span:
        span.set_attribute("user.name", name)
        span.set_attribute("user.email", email)

        # Validation logic
        if not name or len(name) < 2:
            span.add_event("validation.failed", {"field": "name", "reason": "too_short"})
            span.set_status(Status(StatusCode.ERROR, "Invalid name"))
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters")

        if "@" not in email:
            span.add_event("validation.failed", {"field": "email", "reason": "invalid_format"})
            span.set_status(Status(StatusCode.ERROR, "Invalid email"))
            raise HTTPException(status_code=400, detail="Invalid email format")

        span.add_event("validation.passed")

    # Generate user ID
    user_id = str(len(USERS_DB) + 1)

    with tracer.start_as_current_span("db.insert_user") as span:
        span.set_attribute("db.system", "in-memory")
        span.set_attribute("db.operation", "INSERT")
        span.set_attribute("db.table", "users")
        span.set_attribute("user.id", user_id)

        # Simulate database insert
        time.sleep(0.03)

        user = {"id": user_id, "name": name, "email": email}
        USERS_DB[user_id] = user

        span.add_event("user.created", {"user.id": user_id})

    # Notify downstream service
    with tracer.start_as_current_span("notify_user_created") as span:
        span.set_attribute("event.type", "user.created")
        span.set_attribute("user.id", user_id)

        try:
            requests.post(
                f"{DOWNSTREAM_SERVICE}/events",
                json={"type": "user.created", "user_id": user_id},
                timeout=1
            )
            span.set_status(Status(StatusCode.OK))
        except requests.exceptions.RequestException as e:
            # Non-critical failure, log but don't fail request
            span.record_exception(e)
            span.add_event("notification.failed", {"reason": str(e)})

    return user


@app.get("/users/{user_id}/orders")
async def get_user_orders(user_id: str):
    """
    Get user's orders with complex nested operations.

    Demonstrates:
    - Nested spans (parent-child relationships)
    - Parallel operations (would be async in real app)
    - Span links for batch operations
    """
    # Verify user exists
    with tracer.start_as_current_span("verify_user") as span:
        span.set_attribute("user.id", user_id)

        if user_id not in USERS_DB:
            span.set_status(Status(StatusCode.ERROR, "User not found"))
            raise HTTPException(status_code=404, detail="User not found")

    # Fetch orders
    with tracer.start_as_current_span("db.get_orders") as parent_span:
        parent_span.set_attribute("user.id", user_id)
        parent_span.set_attribute("db.system", "in-memory")

        # Simulate querying multiple tables
        orders = []

        with tracer.start_as_current_span("db.query_order_table") as span:
            span.set_attribute("db.table", "orders")
            time.sleep(0.02)
            orders.append({"id": "order-1", "user_id": user_id, "total": 99.99})

        with tracer.start_as_current_span("db.query_order_items") as span:
            span.set_attribute("db.table", "order_items")
            span.set_attribute("order.count", len(orders))
            time.sleep(0.03)

        parent_span.set_attribute("orders.count", len(orders))

    return {"user_id": user_id, "orders": orders}


@app.get("/users/{user_id}/analytics")
async def get_user_analytics(user_id: str, include_predictions: bool = False):
    """
    Get user analytics with conditional tracing.

    Demonstrates:
    - Conditional span creation
    - High-cardinality attribute management
    - Performance-sensitive operations
    """
    with tracer.start_as_current_span("fetch_user_analytics") as span:
        span.set_attribute("user.id", user_id)
        span.set_attribute("analytics.include_predictions", include_predictions)

        # Fetch basic analytics (always traced)
        analytics = {
            "user_id": user_id,
            "login_count": 42,
            "last_login": "2025-01-15T10:30:00Z"
        }

        # Conditionally add expensive operation
        if include_predictions:
            with tracer.start_as_current_span("ml.predict_churn") as ml_span:
                ml_span.set_attribute("ml.model", "churn_predictor")
                ml_span.set_attribute("ml.version", "2.1.0")

                # Simulate ML inference
                time.sleep(0.1)

                prediction = {"churn_probability": 0.15, "confidence": 0.92}
                analytics["predictions"] = prediction

                ml_span.set_attribute("prediction.churn_probability", prediction["churn_probability"])
                ml_span.add_event("prediction.completed")

        span.set_attribute("analytics.fields_returned", len(analytics))

    return analytics


if __name__ == "__main__":
    import uvicorn

    print(f"Starting {SERVICE_NAME}")
    print(f"Traces will be sent to: {OTLP_ENDPOINT}")
    print(f"Downstream service: {DOWNSTREAM_SERVICE}")
    print()
    print("Endpoints:")
    print("  GET  /")
    print("  GET  /users/{user_id}")
    print("  POST /users?name=NAME&email=EMAIL")
    print("  GET  /users/{user_id}/orders")
    print("  GET  /users/{user_id}/analytics?include_predictions=true")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
