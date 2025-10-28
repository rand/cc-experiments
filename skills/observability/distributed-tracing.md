---
name: observability-distributed-tracing
description: Debugging latency issues in microservices
---



# Distributed Tracing

**Scope**: OpenTelemetry, spans, trace context, sampling, Jaeger, Zipkin, trace propagation

**Lines**: 381

**Last Updated**: 2025-10-18

---

## When to Use This Skill

Use this skill when:
- Debugging latency issues in microservices
- Understanding request flows across multiple services
- Identifying bottlenecks in distributed systems
- Tracking dependencies between services
- Measuring end-to-end latency percentiles
- Debugging intermittent errors in complex workflows
- Implementing service mesh observability
- Analyzing cascading failures

**Don't use** for:
- Simple monolithic applications (logs + metrics sufficient)
- Non-request-based workloads (batch jobs, cron tasks)
- Systems with <3 services (overhead not justified)

---

## Core Concepts

### Trace, Span, Context

**Trace**: Complete journey of a request through the system
- Unique Trace ID (e.g., `a1b2c3d4e5f6g7h8`)
- Contains multiple spans
- Represents end-to-end flow

**Span**: Single operation within a trace
- Unique Span ID
- Parent Span ID (for hierarchy)
- Start time, end time, duration
- Operation name (e.g., `GET /api/users`)
- Attributes (metadata: `http.method`, `db.statement`)
- Events (logs within span)
- Status (OK, ERROR)

**Context**: Propagated metadata
- Trace ID, Span ID, Parent Span ID
- Sampling decision
- Baggage (custom key-value pairs)

### Trace Hierarchy

```
Trace: User purchases product
├─ Span 1: API Gateway (100ms)
│  ├─ Span 2: Auth Service (20ms)
│  │  └─ Span 3: Database query (5ms)
│  ├─ Span 4: Product Service (50ms)
│  │  ├─ Span 5: Database query (10ms)
│  │  └─ Span 6: Cache lookup (5ms)
│  └─ Span 7: Payment Service (30ms)
│     └─ Span 8: External API call (25ms)
```

### Sampling

**Why**: Reduce data volume and cost (storing 100% traces is expensive)

**Strategies**:
1. **Head-based sampling** (decision at trace start):
   - Probabilistic: 1% of traces
   - Rate limiting: Max 100 traces/second
   - Always sample errors

2. **Tail-based sampling** (decision after trace complete):
   - Sample slow requests (>1s)
   - Sample errors
   - Sample rare endpoints

### OpenTelemetry (OTel)

**Why OpenTelemetry**: Vendor-neutral, unified API for traces, metrics, logs

**Components**:
- **SDK**: Instrumentation in your code
- **API**: Interface for creating spans
- **Exporter**: Send data to backend (Jaeger, Zipkin, Tempo)
- **Collector**: Centralized agent for receiving/processing/exporting

---

## Patterns

### Pattern 1: OpenTelemetry Setup (Python)

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from fastapi import FastAPI

# Initialize tracer provider
provider = TracerProvider()
trace.set_tracer_provider(provider)

# Configure exporter (send to OTel Collector or Jaeger)
otlp_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",  # gRPC endpoint
    insecure=True
)

# Add span processor
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# Get tracer
tracer = trace.get_tracer(__name__)

# Auto-instrument FastAPI
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

# Auto-instrument HTTP requests
RequestsInstrumentor().instrument()

# Auto-instrument SQLAlchemy
SQLAlchemyInstrumentor().instrument()

# Manual span creation
@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    # Parent span created automatically by FastAPI instrumentation

    # Create child span for business logic
    with tracer.start_as_current_span("get_user_logic") as span:
        span.set_attribute("user_id", user_id)
        span.set_attribute("service", "user-service")

        try:
            # Database call (auto-instrumented)
            user = await db.get_user(user_id)

            # Add event
            span.add_event("user_fetched", {"user_id": user_id})

            # Create nested span for external API
            with tracer.start_as_current_span("fetch_user_preferences"):
                prefs = await external_api.get_preferences(user_id)

            span.set_status(trace.Status(trace.StatusCode.OK))
            return {"user": user, "preferences": prefs}

        except Exception as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
```

### Pattern 2: OpenTelemetry Setup (Go)

```go
package main

import (
    "context"
    "log"
    "time"

    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.4.0"
    "go.opentelemetry.io/otel/trace"
)

func initTracer() (*sdktrace.TracerProvider, error) {
    // Create OTLP exporter
    exporter, err := otlptracegrpc.New(
        context.Background(),
        otlptracegrpc.WithEndpoint("localhost:4317"),
        otlptracegrpc.WithInsecure(),
    )
    if err != nil {
        return nil, err
    }

    // Create resource (service metadata)
    res, err := resource.New(
        context.Background(),
        resource.WithAttributes(
            semconv.ServiceNameKey.String("api-service"),
            semconv.ServiceVersionKey.String("1.0.0"),
            semconv.DeploymentEnvironmentKey.String("production"),
        ),
    )
    if err != nil {
        return nil, err
    }

    // Create tracer provider
    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(res),
        sdktrace.WithSampler(sdktrace.AlwaysSample()),
    )

    otel.SetTracerProvider(tp)

    return tp, nil
}

func main() {
    tp, err := initTracer()
    if err != nil {
        log.Fatal(err)
    }
    defer func() {
        if err := tp.Shutdown(context.Background()); err != nil {
            log.Fatal(err)
        }
    }()

    // Get tracer
    tracer := otel.Tracer("api-service")

    // Create root span
    ctx, span := tracer.Start(context.Background(), "handle_request")
    defer span.End()

    span.SetAttributes(
        attribute.String("http.method", "GET"),
        attribute.String("http.route", "/api/users/:id"),
    )

    // Create child span
    processUser(ctx, tracer, "user_123")

    span.SetStatus(trace.StatusCode(200), "OK")
}

func processUser(ctx context.Context, tracer trace.Tracer, userID string) {
    ctx, span := tracer.Start(ctx, "process_user")
    defer span.End()

    span.SetAttributes(attribute.String("user_id", userID))

    // Simulate work
    time.Sleep(50 * time.Millisecond)

    // Nested span
    fetchFromDB(ctx, tracer, userID)
}

func fetchFromDB(ctx context.Context, tracer trace.Tracer, userID string) {
    ctx, span := tracer.Start(ctx, "database_query")
    defer span.End()

    span.SetAttributes(
        attribute.String("db.system", "postgresql"),
        attribute.String("db.statement", "SELECT * FROM users WHERE id = ?"),
    )

    // Simulate query
    time.Sleep(10 * time.Millisecond)
}
```

### Pattern 3: Trace Context Propagation (HTTP)

```python
from opentelemetry import trace
from opentelemetry.propagate import inject, extract
import requests

tracer = trace.get_tracer(__name__)

# Service A: Outgoing request
def call_service_b():
    with tracer.start_as_current_span("call_service_b") as span:
        headers = {}

        # Inject trace context into HTTP headers
        inject(headers)

        # Headers now contain:
        # traceparent: 00-<trace_id>-<span_id>-01
        # tracestate: ...

        response = requests.get(
            "http://service-b/api/data",
            headers=headers
        )

        return response.json()

# Service B: Incoming request
from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/api/data")
async def get_data(request: Request):
    # Extract trace context from incoming headers
    ctx = extract(request.headers)

    # Continue trace from Service A
    with tracer.start_as_current_span("get_data", context=ctx) as span:
        span.set_attribute("service", "service-b")

        data = await fetch_data()
        return {"data": data}
```

### Pattern 4: Custom Span Attributes

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

@app.post("/api/orders")
async def create_order(order: Order):
    with tracer.start_as_current_span("create_order") as span:
        # Standard semantic conventions
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.route", "/api/orders")
        span.set_attribute("http.status_code", 201)

        # Custom business attributes
        span.set_attribute("order.id", order.id)
        span.set_attribute("order.total", order.total)
        span.set_attribute("order.items_count", len(order.items))
        span.set_attribute("customer.id", order.customer_id)
        span.set_attribute("payment.method", order.payment_method)

        # Add events (logs within span)
        span.add_event("order_validated", {
            "validation_duration_ms": 10
        })

        try:
            result = await process_order(order)

            span.add_event("payment_processed", {
                "transaction_id": result.transaction_id
            })

            span.set_status(Status(StatusCode.OK))
            return result

        except PaymentError as e:
            span.set_status(Status(StatusCode.ERROR, "Payment failed"))
            span.record_exception(e)

            # Add error attributes
            span.set_attribute("error", True)
            span.set_attribute("error.type", "PaymentError")
            span.set_attribute("error.message", str(e))

            raise
```

### Pattern 5: Sampling Configuration

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import (
    TraceIdRatioBased,
    ParentBased,
    ALWAYS_ON,
    ALWAYS_OFF
)

# 1. Probabilistic sampling (1% of traces)
sampler = TraceIdRatioBased(0.01)

# 2. Parent-based sampling (respect parent's decision)
sampler = ParentBased(root=TraceIdRatioBased(0.1))

# 3. Always sample (development)
sampler = ALWAYS_ON

# 4. Never sample (disabled)
sampler = ALWAYS_OFF

# 5. Custom sampling (sample errors and slow requests)
class CustomSampler:
    def should_sample(self, context, trace_id, name, attributes):
        # Always sample if error
        if attributes.get("http.status_code", 0) >= 500:
            return ALWAYS_ON.should_sample(context, trace_id, name, attributes)

        # Always sample if slow
        if attributes.get("duration_ms", 0) > 1000:
            return ALWAYS_ON.should_sample(context, trace_id, name, attributes)

        # Otherwise 1% sampling
        return TraceIdRatioBased(0.01).should_sample(
            context, trace_id, name, attributes
        )

provider = TracerProvider(sampler=CustomSampler())
```

### Pattern 6: Database Tracing

```python
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy import create_engine

# Auto-instrument SQLAlchemy
engine = create_engine("postgresql://localhost/mydb")
SQLAlchemyInstrumentor().instrument(engine=engine)

# Manual span for complex queries
with tracer.start_as_current_span("complex_query") as span:
    span.set_attribute("db.system", "postgresql")
    span.set_attribute("db.name", "mydb")
    span.set_attribute("db.operation", "SELECT")
    span.set_attribute("db.statement", "SELECT * FROM users WHERE status = ?")

    results = session.execute(query)

    span.set_attribute("db.rows_returned", len(results))
```

---

## Quick Reference

### OpenTelemetry Libraries

```bash
# Python
pip install opentelemetry-api opentelemetry-sdk
pip install opentelemetry-exporter-otlp
pip install opentelemetry-instrumentation-fastapi
pip install opentelemetry-instrumentation-requests
pip install opentelemetry-instrumentation-sqlalchemy

# Go
go get go.opentelemetry.io/otel
go get go.opentelemetry.io/otel/sdk
go get go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc

# Node.js
npm install @opentelemetry/api @opentelemetry/sdk-node
npm install @opentelemetry/exporter-trace-otlp-grpc
npm install @opentelemetry/auto-instrumentations-node
```

### Trace Backend Options

| Backend | Description | Use Case |
|---------|-------------|----------|
| **Jaeger** | CNCF project, full-featured | Self-hosted, open source |
| **Zipkin** | Twitter origin, simple | Lightweight, easy setup |
| **Tempo** | Grafana Labs, S3-compatible | Cost-effective, high volume |
| **Datadog APM** | Commercial SaaS | Enterprise, full stack |
| **New Relic** | Commercial SaaS | Enterprise, full stack |

### Span Semantic Conventions

```python
# HTTP
span.set_attribute("http.method", "GET")
span.set_attribute("http.url", "https://api.example.com/users")
span.set_attribute("http.status_code", 200)
span.set_attribute("http.route", "/users/:id")

# Database
span.set_attribute("db.system", "postgresql")
span.set_attribute("db.name", "mydb")
span.set_attribute("db.statement", "SELECT * FROM users")
span.set_attribute("db.operation", "SELECT")

# RPC
span.set_attribute("rpc.system", "grpc")
span.set_attribute("rpc.service", "UserService")
span.set_attribute("rpc.method", "GetUser")

# Messaging
span.set_attribute("messaging.system", "rabbitmq")
span.set_attribute("messaging.destination", "orders_queue")
span.set_attribute("messaging.operation", "publish")
```

### Trace Context Headers

```
# W3C Trace Context (standard)
traceparent: 00-<trace_id>-<span_id>-<flags>
tracestate: vendor1=value1,vendor2=value2

# Example
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

---

## Anti-Patterns

### ❌ Creating Too Many Spans

```python
# WRONG: Span for every function call
with tracer.start_as_current_span("add_numbers"):  # Too granular!
    result = a + b

# CORRECT: Span for meaningful operations
with tracer.start_as_current_span("calculate_order_total"):
    total = sum(item.price for item in order.items)
    total += calculate_tax(total)
    total += calculate_shipping(order)
```

### ❌ Missing Trace Context Propagation

```python
# WRONG: No trace context in HTTP call
requests.get("http://service-b/api/data")  # Breaks trace!

# CORRECT: Inject trace context
headers = {}
inject(headers)
requests.get("http://service-b/api/data", headers=headers)
```

### ❌ Forgetting to Close Spans

```python
# WRONG: Span never closed
span = tracer.start_span("operation")
do_work()
# span.end() missing!

# CORRECT: Use context manager
with tracer.start_as_current_span("operation"):
    do_work()
```

### ❌ High-Cardinality Attributes

```python
# WRONG: User ID in span name (high cardinality)
span = tracer.start_as_current_span(f"get_user_{user_id}")

# CORRECT: User ID as attribute
span = tracer.start_as_current_span("get_user")
span.set_attribute("user_id", user_id)
```

### ❌ Sampling Before Instrumentation

```python
# WRONG: Sample before seeing attributes
sampler = TraceIdRatioBased(0.01)  # Can't see if request is slow/error

# CORRECT: Use tail-based sampling or custom sampler
class TailBasedSampler:
    def should_sample(self, context, trace_id, name, attributes):
        if attributes.get("http.status_code", 0) >= 500:
            return ALWAYS_ON
        return TraceIdRatioBased(0.01).should_sample(...)
```

### ❌ Blocking Operations in Spans

```python
# WRONG: Synchronous sleep in async span
with tracer.start_as_current_span("wait"):
    time.sleep(10)  # Blocks event loop!

# CORRECT: Async sleep
with tracer.start_as_current_span("wait"):
    await asyncio.sleep(10)
```

---

## Level 3: Resources

**Location**: `skills/observability/distributed-tracing/resources/`

### Comprehensive Reference

**`REFERENCE.md`** (800+ lines): Deep-dive reference covering:
- Distributed tracing fundamentals (traces, spans, context propagation)
- OpenTelemetry specification and architecture (API, SDK, Collector, OTLP)
- Trace context propagation formats (W3C Trace Context, B3, Jaeger, X-Ray)
- Sampling strategies (head-based, tail-based, adaptive sampling)
- Tracing backends comparison (Jaeger, Zipkin, Tempo, Honeycomb, Datadog)
- Instrumentation patterns (auto-instrumentation vs manual spans)
- Performance overhead analysis and optimization techniques
- Correlation with logs and metrics (exemplars, unified queries)
- Production patterns (service mesh integration, multi-tenant tracing, error tracking)
- Common anti-patterns and troubleshooting guide

### Executable Scripts

**`scripts/analyze_traces.py`**
- Parse and analyze trace data from JSON files (OTLP, Jaeger, Zipkin formats)
- Identify slow spans exceeding configurable threshold
- Detect error spans and analyze failure patterns
- Calculate critical path and total duration
- Service breakdown and span statistics
- Supports filtering by service, trace ID
- Output as human-readable report or JSON for automation

**`scripts/visualize_trace.py`**
- Generate HTML Gantt chart visualizations of traces
- Create SVG flame graphs for performance analysis
- Interactive visualizations with zoom, pan, and tooltips
- Show span hierarchy and timing relationships
- Color-coded by span status (OK, ERROR, UNSET)
- Support for multiple trace formats

**`scripts/test_propagation.sh`**
- Test trace context propagation across HTTP services
- Validate W3C Trace Context, B3, Jaeger, and X-Ray header formats
- Multi-hop propagation testing (service A → B → C)
- Verify trace ID preservation across boundaries
- JSON output for CI/CD integration
- Configurable propagation format and target URLs

### Working Examples

**`examples/python/otel_fastapi_tracing.py`**
- Complete FastAPI service with OpenTelemetry instrumentation
- Auto-instrumentation for HTTP, database, and external calls
- Manual span creation for business logic
- Error handling and exception recording
- Span attributes, events, and status management
- OTLP exporter configuration

**`examples/python/otel_manual_spans.py`**
- Comprehensive manual span creation patterns
- Nested spans and parent-child relationships
- Different span kinds (CLIENT, SERVER, PRODUCER, CONSUMER, INTERNAL)
- Async context propagation with asyncio
- Span links for cross-trace references
- Batch processing patterns
- Error handling and retry logic

**`examples/typescript/otel_express_tracing.ts`**
- Express.js service with OpenTelemetry auto-instrumentation
- Manual span creation for complex operations
- Trace context propagation to downstream services
- Multi-step operations (order fulfillment workflow)
- Event tracking within spans
- Error handling middleware with tracing

**`examples/go/otel_http_tracing.go`**
- Go HTTP server with OpenTelemetry instrumentation
- otelhttp middleware for automatic span creation
- Manual span creation for business logic
- OTLP gRPC exporter configuration
- Span attributes using semantic conventions
- Producer spans for message publishing

**`examples/docker/jaeger-compose.yml`**
- Complete Docker Compose setup for distributed tracing
- Jaeger all-in-one (collector + query + UI)
- OpenTelemetry Collector with advanced processing
- Example microservices with tracing enabled
- Network configuration for inter-service communication

**`examples/docker/otel-collector-config.yaml`**
- Production-ready OpenTelemetry Collector configuration
- OTLP and Jaeger receivers
- Tail sampling processor for smart sampling
- Memory limiter and batch processing
- Resource detection and attribute processing
- Multiple exporters (Jaeger, OTLP, logging, Prometheus)
- Health check and diagnostics extensions

### Usage Examples

```bash
# Analyze traces for slow operations
./scripts/analyze_traces.py --file traces.json --slow-threshold 500

# Generate interactive trace visualization
./scripts/visualize_trace.py --file traces.json --interactive --output trace.html

# Test trace propagation
./scripts/test_propagation.sh --url http://localhost:8000 --format w3c

# Run example services
python examples/python/otel_fastapi_tracing.py
ts-node examples/typescript/otel_express_tracing.ts
go run examples/go/otel_http_tracing.go

# Start tracing infrastructure
docker-compose -f examples/docker/jaeger-compose.yml up -d
# Access Jaeger UI: http://localhost:16686
```

---

## Related Skills

- **structured-logging.md** - Correlate logs with trace IDs
- **metrics-instrumentation.md** - Complementary metrics (RED method)
- **dashboard-design.md** - Visualize traces in Grafana
- **alerting-strategy.md** - Alert on trace error rates and latency

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
