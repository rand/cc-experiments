"""
OpenTelemetry Manual Span Creation Examples

Comprehensive examples of manual span creation patterns including:
- Basic span lifecycle
- Nested spans and parent-child relationships
- Span attributes, events, and status
- Error handling and exception recording
- Async context propagation
- Span links for cross-trace references

Usage:
    python otel_manual_spans.py
"""

import asyncio
import time
import traceback
from typing import List, Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Link, SpanContext, SpanKind, Status, StatusCode, TraceFlags


def init_tracer():
    """Initialize OpenTelemetry with console exporter."""
    resource = Resource.create({
        "service.name": "manual-spans-example",
        "service.version": "1.0.0"
    })

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)


tracer = init_tracer()


# Example 1: Basic span creation
def example_basic_spans():
    """Basic span creation and lifecycle."""
    print("\n=== Example 1: Basic Spans ===\n")

    # Method 1: Context manager (recommended)
    with tracer.start_as_current_span("operation_1") as span:
        span.set_attribute("method", "context_manager")
        span.set_attribute("count", 42)
        time.sleep(0.01)
        # Span automatically ends when context exits

    # Method 2: Manual start/end
    span = tracer.start_span("operation_2")
    span.set_attribute("method", "manual")
    try:
        time.sleep(0.01)
        span.set_status(Status(StatusCode.OK))
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
    finally:
        span.end()  # Must explicitly end span

    print("Basic spans completed\n")


# Example 2: Nested spans (parent-child)
def example_nested_spans():
    """Create nested spans with parent-child relationships."""
    print("\n=== Example 2: Nested Spans ===\n")

    with tracer.start_as_current_span("parent_operation") as parent:
        parent.set_attribute("level", "parent")
        parent.add_event("parent_started")

        time.sleep(0.01)

        # Child span automatically inherits parent context
        with tracer.start_as_current_span("child_operation_1") as child1:
            child1.set_attribute("level", "child")
            child1.set_attribute("child_number", 1)
            time.sleep(0.02)
            child1.add_event("child_1_completed")

        # Another child span
        with tracer.start_as_current_span("child_operation_2") as child2:
            child2.set_attribute("level", "child")
            child2.set_attribute("child_number", 2)

            # Grandchild span
            with tracer.start_as_current_span("grandchild_operation") as grandchild:
                grandchild.set_attribute("level", "grandchild")
                time.sleep(0.01)

            time.sleep(0.01)

        parent.add_event("all_children_completed")

    print("Nested spans completed\n")


# Example 3: Span kinds
def example_span_kinds():
    """Demonstrate different span kinds."""
    print("\n=== Example 3: Span Kinds ===\n")

    # SERVER: Inbound request handler
    with tracer.start_as_current_span(
        "handle_request",
        kind=SpanKind.SERVER
    ) as server_span:
        server_span.set_attribute("http.method", "GET")
        server_span.set_attribute("http.target", "/api/users")

        # CLIENT: Outbound request
        with tracer.start_as_current_span(
            "call_database",
            kind=SpanKind.CLIENT
        ) as client_span:
            client_span.set_attribute("db.system", "postgresql")
            client_span.set_attribute("db.statement", "SELECT * FROM users")
            time.sleep(0.02)

        # INTERNAL: Internal operation
        with tracer.start_as_current_span(
            "process_data",
            kind=SpanKind.INTERNAL
        ) as internal_span:
            internal_span.set_attribute("records.processed", 100)
            time.sleep(0.01)

    # PRODUCER: Async message send
    with tracer.start_as_current_span(
        "publish_event",
        kind=SpanKind.PRODUCER
    ) as producer_span:
        producer_span.set_attribute("messaging.system", "kafka")
        producer_span.set_attribute("messaging.destination", "user.events")
        producer_span.set_attribute("messaging.operation", "send")
        time.sleep(0.01)

    # CONSUMER: Async message receive
    with tracer.start_as_current_span(
        "consume_event",
        kind=SpanKind.CONSUMER
    ) as consumer_span:
        consumer_span.set_attribute("messaging.system", "kafka")
        consumer_span.set_attribute("messaging.destination", "user.events")
        consumer_span.set_attribute("messaging.operation", "receive")
        time.sleep(0.01)

    print("Span kinds completed\n")


# Example 4: Span attributes and events
def example_attributes_and_events():
    """Demonstrate span attributes and events."""
    print("\n=== Example 4: Attributes and Events ===\n")

    with tracer.start_as_current_span("process_order") as span:
        # Set various attribute types
        span.set_attribute("order.id", "order-12345")
        span.set_attribute("order.total", 199.99)
        span.set_attribute("order.items_count", 3)
        span.set_attribute("order.express_shipping", True)

        # Add events with timestamps
        span.add_event("order.validated")
        time.sleep(0.01)

        span.add_event("payment.processing", {
            "payment.method": "credit_card",
            "payment.amount": 199.99
        })
        time.sleep(0.02)

        span.add_event("payment.completed", {
            "payment.transaction_id": "txn-67890",
            "payment.status": "success"
        })
        time.sleep(0.01)

        span.add_event("order.fulfilled")

        # Final attributes
        span.set_attribute("order.status", "completed")
        span.set_attribute("order.processing_time_ms", 40)

    print("Attributes and events completed\n")


# Example 5: Error handling
def example_error_handling():
    """Demonstrate error handling and exception recording."""
    print("\n=== Example 5: Error Handling ===\n")

    # Successful operation
    with tracer.start_as_current_span("successful_operation") as span:
        span.set_attribute("operation", "success")
        time.sleep(0.01)
        span.set_status(Status(StatusCode.OK))

    # Operation with error
    with tracer.start_as_current_span("failed_operation") as span:
        span.set_attribute("operation", "failure")

        try:
            # Simulate error
            raise ValueError("Invalid input data")
        except ValueError as e:
            # Record exception details
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, "Validation failed"))
            span.add_event("error.handled", {
                "error.type": type(e).__name__,
                "error.message": str(e)
            })

    # Operation with retry logic
    with tracer.start_as_current_span("operation_with_retry") as span:
        max_retries = 3
        span.set_attribute("retry.max_attempts", max_retries)

        for attempt in range(1, max_retries + 1):
            span.add_event("retry.attempt", {
                "retry.attempt_number": attempt
            })

            try:
                # Simulate occasional failure
                if attempt < 3:
                    raise ConnectionError("Service unavailable")

                span.add_event("retry.success", {
                    "retry.attempt_number": attempt
                })
                span.set_status(Status(StatusCode.OK))
                break

            except ConnectionError as e:
                if attempt == max_retries:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, "Max retries exceeded"))
                else:
                    span.add_event("retry.failed", {
                        "retry.attempt_number": attempt,
                        "error.message": str(e)
                    })
                    time.sleep(0.01 * attempt)  # Backoff

    print("Error handling completed\n")


# Example 6: Span links
def example_span_links():
    """Demonstrate span links for cross-trace references."""
    print("\n=== Example 6: Span Links ===\n")

    # Create first trace (batch job initiator)
    with tracer.start_as_current_span("batch_job_initiator") as initiator_span:
        initiator_span.set_attribute("batch.id", "batch-123")
        initiator_span.set_attribute("batch.size", 100)

        # Capture span context for linking
        initiator_context = initiator_span.get_span_context()

        time.sleep(0.01)

    # Create link to reference the initiator
    link = Link(
        context=initiator_context,
        attributes={
            "link.type": "batch_parent",
            "link.description": "Parent batch job"
        }
    )

    # Create child trace with link to parent
    with tracer.start_as_current_span(
        "batch_job_item",
        links=[link]
    ) as item_span:
        item_span.set_attribute("batch.id", "batch-123")
        item_span.set_attribute("item.index", 42)
        time.sleep(0.02)

    # Another use case: linking retry to original request
    with tracer.start_as_current_span("original_request") as original_span:
        original_span.set_attribute("request.id", "req-456")
        original_context = original_span.get_span_context()
        time.sleep(0.01)

    retry_link = Link(
        context=original_context,
        attributes={
            "link.type": "retry",
            "retry.count": 1
        }
    )

    with tracer.start_as_current_span(
        "retry_request",
        links=[retry_link]
    ) as retry_span:
        retry_span.set_attribute("request.id", "req-456")
        retry_span.set_attribute("is_retry", True)
        time.sleep(0.01)

    print("Span links completed\n")


# Example 7: Async operations
async def example_async_operations():
    """Demonstrate async context propagation."""
    print("\n=== Example 7: Async Operations ===\n")

    async def async_operation(name: str, duration: float):
        """Simulated async operation."""
        with tracer.start_as_current_span(f"async_{name}") as span:
            span.set_attribute("operation.name", name)
            span.set_attribute("operation.duration", duration)
            await asyncio.sleep(duration)
            return f"Result from {name}"

    # Parent span with async children
    with tracer.start_as_current_span("async_parent") as parent_span:
        parent_span.add_event("starting_async_operations")

        # Sequential async operations
        result1 = await async_operation("operation_1", 0.01)
        parent_span.add_event("operation_1_completed", {"result": result1})

        result2 = await async_operation("operation_2", 0.02)
        parent_span.add_event("operation_2_completed", {"result": result2})

        parent_span.add_event("all_operations_completed")

    # Parallel async operations
    with tracer.start_as_current_span("async_parallel") as parent_span:
        parent_span.add_event("starting_parallel_operations")

        # Run multiple operations concurrently
        results = await asyncio.gather(
            async_operation("parallel_1", 0.01),
            async_operation("parallel_2", 0.01),
            async_operation("parallel_3", 0.01),
        )

        parent_span.set_attribute("operations.completed", len(results))
        parent_span.add_event("parallel_operations_completed")

    print("Async operations completed\n")


# Example 8: Batch processing with spans
def example_batch_processing():
    """Demonstrate batch processing pattern."""
    print("\n=== Example 8: Batch Processing ===\n")

    items = ["item-1", "item-2", "item-3", "item-4", "item-5"]

    with tracer.start_as_current_span("process_batch") as batch_span:
        batch_span.set_attribute("batch.size", len(items))
        batch_span.add_event("batch.started")

        successful = 0
        failed = 0

        for idx, item in enumerate(items):
            # Create span for each item (but don't pollute traces)
            # In production, consider sampling or not creating individual spans
            with tracer.start_as_current_span(f"process_item") as item_span:
                item_span.set_attribute("item.id", item)
                item_span.set_attribute("item.index", idx)

                try:
                    # Simulate processing
                    time.sleep(0.005)

                    # Simulate occasional failure
                    if idx == 2:
                        raise ValueError(f"Processing failed for {item}")

                    successful += 1
                    item_span.set_status(Status(StatusCode.OK))

                except Exception as e:
                    failed += 1
                    item_span.record_exception(e)
                    item_span.set_status(Status(StatusCode.ERROR))

        # Record batch results
        batch_span.set_attribute("batch.successful", successful)
        batch_span.set_attribute("batch.failed", failed)
        batch_span.add_event("batch.completed", {
            "successful": successful,
            "failed": failed
        })

        if failed > 0:
            batch_span.set_status(Status(StatusCode.ERROR, f"{failed} items failed"))
        else:
            batch_span.set_status(Status(StatusCode.OK))

    print("Batch processing completed\n")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("OpenTelemetry Manual Span Creation Examples")
    print("=" * 60)

    # Run synchronous examples
    example_basic_spans()
    example_nested_spans()
    example_span_kinds()
    example_attributes_and_events()
    example_error_handling()
    example_span_links()
    example_batch_processing()

    # Run async examples
    asyncio.run(example_async_operations())

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60 + "\n")

    # Give time for spans to be exported
    time.sleep(2)


if __name__ == "__main__":
    main()
