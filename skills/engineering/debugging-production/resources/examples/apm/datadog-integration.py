#!/usr/bin/env python3
"""
Datadog APM integration with custom metrics and tracing.

Demonstrates:
- Datadog tracer configuration
- Custom metrics emission
- Distributed tracing
- Service checks
"""

from ddtrace import tracer, patch_all
from datadog import initialize, statsd
import time
import random


# Initialize Datadog
initialize(
    statsd_host="localhost",
    statsd_port=8125,
)

# Auto-patch supported libraries
patch_all()


@tracer.wrap(service="user-service", resource="get_user")
def get_user(user_id: int):
    """Get user with Datadog tracing."""

    # Add custom tags to span
    span = tracer.current_span()
    if span:
        span.set_tag("user.id", user_id)
        span.set_tag("environment", "production")

    # Emit custom metric
    statsd.increment("users.get.requests", tags=["user_id:{}".format(user_id)])

    # Simulate processing time
    processing_time = random.uniform(0.01, 0.1)
    time.sleep(processing_time)

    # Track processing time
    statsd.histogram("users.get.duration", processing_time * 1000, tags=["user_id:{}".format(user_id)])

    # Simulate occasional errors
    if random.random() < 0.05:
        statsd.increment("users.get.errors", tags=["error:not_found"])
        raise ValueError(f"User {user_id} not found")

    statsd.increment("users.get.success")

    return {"id": user_id, "name": f"User {user_id}"}


@tracer.wrap(service="user-service", resource="process_batch")
def process_batch(batch_size: int):
    """Process batch of users."""

    with tracer.trace("validate_batch", service="user-service") as span:
        span.set_tag("batch.size", batch_size)
        time.sleep(0.01)

    results = []
    for i in range(batch_size):
        with tracer.trace("process_user", service="user-service") as span:
            span.set_tag("user.index", i)

            try:
                user = get_user(i)
                results.append(user)
            except ValueError as e:
                span.set_error(e)
                statsd.increment("batch.user_errors")

    # Emit batch metrics
    statsd.gauge("batch.size", batch_size)
    statsd.gauge("batch.success_count", len(results))

    return results


def emit_system_metrics():
    """Emit system health metrics."""
    import psutil

    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    statsd.gauge("system.cpu.percent", cpu_percent)

    # Memory usage
    memory = psutil.virtual_memory()
    statsd.gauge("system.memory.percent", memory.percent)
    statsd.gauge("system.memory.used_mb", memory.used / 1024 / 1024)

    # Disk usage
    disk = psutil.disk_usage("/")
    statsd.gauge("system.disk.percent", disk.percent)


def service_check():
    """Perform service check."""
    try:
        # Check database connectivity
        database_ok = True  # Simulate check
        if database_ok:
            statsd.service_check(
                "database.connectivity",
                statsd.OK,
                message="Database is reachable",
                tags=["environment:production"],
            )
        else:
            statsd.service_check(
                "database.connectivity",
                statsd.CRITICAL,
                message="Database is unreachable",
                tags=["environment:production"],
            )
    except Exception as e:
        statsd.service_check(
            "service.health",
            statsd.CRITICAL,
            message=str(e),
            tags=["environment:production"],
        )


if __name__ == "__main__":
    print("Running Datadog integration demo...")

    # Process some requests
    for i in range(10):
        try:
            user = get_user(i)
            print(f"Got user: {user}")
        except ValueError as e:
            print(f"Error: {e}")

        time.sleep(0.5)

    # Process batch
    print("\nProcessing batch...")
    results = process_batch(5)
    print(f"Batch results: {len(results)} successful")

    # Emit system metrics
    print("\nEmitting system metrics...")
    emit_system_metrics()

    # Perform service check
    print("\nPerforming service check...")
    service_check()

    print("\nDemo complete. Check Datadog dashboard for metrics and traces.")
