# Distributed Tracing Reference

Comprehensive reference for distributed tracing concepts, OpenTelemetry implementation, sampling strategies, and production patterns.

## Table of Contents

1. [Fundamentals](#fundamentals)
2. [OpenTelemetry Specification](#opentelemetry-specification)
3. [Trace Context Propagation](#trace-context-propagation)
4. [Sampling Strategies](#sampling-strategies)
5. [Tracing Backends](#tracing-backends)
6. [Instrumentation Patterns](#instrumentation-patterns)
7. [Performance and Overhead](#performance-and-overhead)
8. [Correlation with Logs and Metrics](#correlation-with-logs-and-metrics)
9. [Production Patterns](#production-patterns)
10. [Common Anti-Patterns](#common-anti-patterns)
11. [Troubleshooting Guide](#troubleshooting-guide)

---

## Fundamentals

### What is Distributed Tracing?

Distributed tracing tracks requests as they flow through distributed systems, capturing timing data and metadata about each operation. It answers:

- **Where is time spent?** Identify slow services/operations
- **What caused this error?** See full request context
- **How do services interact?** Visualize dependencies
- **What's the critical path?** Optimize bottlenecks

### Core Concepts

#### Trace

A trace represents the complete journey of a request through a system. It consists of one or more spans organized in a tree or directed acyclic graph (DAG).

**Trace Properties**:
- **Trace ID**: Unique identifier (128-bit hex string)
- **Root Span**: Entry point of the request
- **Span Count**: Total number of operations
- **Duration**: End-to-end latency
- **Status**: Success, error, or unset

**Example Trace**:
```
Trace ID: 4bf92f3577b34da6a3ce929d0e0e4736
├─ Span: HTTP GET /api/users/123 (200ms)
   ├─ Span: Auth.verify (10ms)
   ├─ Span: Database.query (150ms)
   │  ├─ Span: Connection.acquire (5ms)
   │  └─ Span: Query.execute (140ms)
   └─ Span: Cache.set (20ms)
```

#### Span

A span represents a single operation within a trace. It's the building block of distributed tracing.

**Span Properties**:
- **Span ID**: Unique identifier within trace (64-bit hex)
- **Parent Span ID**: Links to parent operation
- **Name**: Operation identifier (e.g., "GET /api/users")
- **Start Time**: When operation began (nanosecond precision)
- **End Time**: When operation completed
- **Duration**: End time - start time
- **Status**: ok, error, unset
- **Attributes**: Key-value metadata
- **Events**: Timestamped log entries within span
- **Links**: References to other spans (different traces)

**Span Structure**:
```json
{
  "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
  "spanId": "00f067aa0ba902b7",
  "parentSpanId": "0000000000000000",
  "name": "GET /api/users/123",
  "kind": "SERVER",
  "startTimeUnixNano": "1609459200000000000",
  "endTimeUnixNano": "1609459200200000000",
  "attributes": {
    "http.method": "GET",
    "http.url": "/api/users/123",
    "http.status_code": 200,
    "service.name": "user-api"
  },
  "status": {
    "code": "OK"
  },
  "events": [
    {
      "timeUnixNano": "1609459200050000000",
      "name": "cache.miss",
      "attributes": {
        "key": "user:123"
      }
    }
  ]
}
```

#### Span Kinds

OpenTelemetry defines five span kinds that describe the role of a span:

**1. CLIENT**
- Outbound synchronous request (e.g., HTTP client, gRPC client)
- Waits for response
- Examples: HTTP GET, database query, RPC call

**2. SERVER**
- Inbound synchronous request handler
- Typically child of remote CLIENT span
- Examples: HTTP endpoint, gRPC server method

**3. PRODUCER**
- Outbound asynchronous message (doesn't wait for response)
- Examples: Kafka producer, SQS send, AMQP publish

**4. CONSUMER**
- Inbound asynchronous message handler
- Child of remote PRODUCER span
- Examples: Kafka consumer, SQS receive, AMQP subscribe

**5. INTERNAL**
- Internal operation (doesn't cross process boundary)
- Examples: function call, algorithm step, internal logic

**Span Kind Relationships**:
```
Service A                Service B
┌─────────────┐         ┌─────────────┐
│ CLIENT span │────────>│ SERVER span │
│  (outbound) │         │  (inbound)  │
└─────────────┘         └─────────────┘

Service A                Queue                Service B
┌──────────────┐       ┌─────┐       ┌──────────────┐
│ PRODUCER span│──────>│     │──────>│ CONSUMER span│
│  (async send)│       └─────┘       │ (async recv) │
└──────────────┘                     └──────────────┘
```

#### Context Propagation

Context propagation passes trace context across service boundaries, maintaining trace continuity.

**Propagation Mechanisms**:
- **HTTP Headers**: W3C Trace Context, B3, Jaeger headers
- **Message Headers**: Kafka, AMQP, SQS metadata
- **gRPC Metadata**: Binary or text propagation
- **In-Process**: Thread-local or async context

**Critical Context**:
- Trace ID (must propagate)
- Span ID (becomes parent span ID)
- Trace Flags (sampling decision)
- Trace State (vendor-specific data)

---

## OpenTelemetry Specification

### Architecture

OpenTelemetry (OTel) is the CNCF standard for observability instrumentation.

**Components**:
1. **API**: Defines interfaces for instrumentation
2. **SDK**: Implements API with exporters and processors
3. **Instrumentation**: Auto-instrumentation and manual spans
4. **Collector**: Receives, processes, and exports telemetry
5. **Protocol (OTLP)**: Wire format for telemetry data

**Data Flow**:
```
Application
  └─> OTel API (create spans)
       └─> OTel SDK (process spans)
            └─> Exporter (OTLP, Jaeger, Zipkin)
                 └─> OTel Collector (optional)
                      └─> Backend (Jaeger, Tempo, etc.)
```

### Tracer Provider

The `TracerProvider` is the entry point for tracing. It creates `Tracer` instances.

**Configuration**:
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter
)
from opentelemetry.sdk.resources import Resource

# Create resource (service identity)
resource = Resource.create({
    "service.name": "user-service",
    "service.version": "1.2.3",
    "deployment.environment": "production"
})

# Create provider
provider = TracerProvider(resource=resource)

# Add span processor + exporter
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)

# Set global provider
trace.set_tracer_provider(provider)

# Get tracer
tracer = trace.get_tracer(
    "user-service",
    "1.2.3"
)
```

### Span Lifecycle

**Creating Spans**:
```python
# Method 1: Context manager (auto-closes)
with tracer.start_as_current_span("operation") as span:
    span.set_attribute("key", "value")
    # operation logic
    # span automatically ends

# Method 2: Manual (explicit close)
span = tracer.start_span("operation")
span.set_attribute("key", "value")
try:
    # operation logic
    span.set_status(trace.Status(trace.StatusCode.OK))
finally:
    span.end()

# Method 3: Nested spans
with tracer.start_as_current_span("parent") as parent:
    parent.set_attribute("parent.attr", "value")

    with tracer.start_as_current_span("child") as child:
        child.set_attribute("child.attr", "value")
        # child is automatically linked to parent
```

### Span Attributes

Attributes are key-value pairs that provide context about the operation.

**Semantic Conventions** (standardized attributes):
```python
from opentelemetry.semconv.trace import SpanAttributes

# HTTP attributes
span.set_attribute(SpanAttributes.HTTP_METHOD, "GET")
span.set_attribute(SpanAttributes.HTTP_URL, "/api/users/123")
span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, 200)
span.set_attribute(SpanAttributes.HTTP_TARGET, "/api/users/123")
span.set_attribute(SpanAttributes.HTTP_HOST, "api.example.com")

# Database attributes
span.set_attribute(SpanAttributes.DB_SYSTEM, "postgresql")
span.set_attribute(SpanAttributes.DB_NAME, "users")
span.set_attribute(SpanAttributes.DB_STATEMENT, "SELECT * FROM users WHERE id=$1")
span.set_attribute(SpanAttributes.DB_OPERATION, "SELECT")

# RPC attributes
span.set_attribute(SpanAttributes.RPC_SYSTEM, "grpc")
span.set_attribute(SpanAttributes.RPC_SERVICE, "UserService")
span.set_attribute(SpanAttributes.RPC_METHOD, "GetUser")

# Messaging attributes
span.set_attribute(SpanAttributes.MESSAGING_SYSTEM, "kafka")
span.set_attribute(SpanAttributes.MESSAGING_DESTINATION, "user.events")
span.set_attribute(SpanAttributes.MESSAGING_OPERATION, "send")
```

**Custom Attributes**:
```python
# Business context
span.set_attribute("user.id", "123")
span.set_attribute("tenant.id", "acme-corp")
span.set_attribute("feature.flag.enabled", True)

# Performance metrics
span.set_attribute("cache.hit", False)
span.set_attribute("query.rows_returned", 42)
span.set_attribute("batch.size", 1000)
```

**Attribute Best Practices**:
- Use semantic conventions when available
- Keep cardinality low (avoid high-cardinality IDs in keys)
- Use namespaces (e.g., "db.", "http.", "custom.")
- Prefer primitive types (string, int, float, bool)
- Avoid PII in attributes

### Span Events

Events are timestamped log entries within a span.

**Creating Events**:
```python
# Simple event
span.add_event("cache.miss")

# Event with attributes
span.add_event("exception", {
    "exception.type": "ValueError",
    "exception.message": "Invalid user ID",
    "exception.stacktrace": traceback.format_exc()
})

# Event with timestamp
span.add_event(
    "retry.attempt",
    attributes={"retry.count": 3},
    timestamp=time.time_ns()
)
```

**Common Event Patterns**:
```python
# Exception recording
from opentelemetry.trace import Status, StatusCode

try:
    # operation
except Exception as e:
    span.record_exception(e)
    span.set_status(Status(StatusCode.ERROR, str(e)))
    raise

# Checkpoint events
span.add_event("validation.started")
# ... validation logic ...
span.add_event("validation.completed", {"errors": 0})

# State transitions
span.add_event("order.state.changed", {
    "from": "pending",
    "to": "processing"
})
```

### Span Links

Links connect spans across different traces (not parent-child relationships).

**Use Cases**:
- Batch processing (link child traces to batch parent)
- Fan-out operations (link results to trigger)
- Retries (link retry traces to original)
- Async workflows (link continuation to initiator)

**Creating Links**:
```python
from opentelemetry.trace import Link, SpanContext

# Link to another trace
other_span_context = SpanContext(
    trace_id=int("4bf92f3577b34da6a3ce929d0e0e4736", 16),
    span_id=int("00f067aa0ba902b7", 16),
    is_remote=True,
    trace_flags=TraceFlags(0x01)
)

link = Link(
    context=other_span_context,
    attributes={"link.type": "retry", "retry.count": 1}
)

# Create span with link
with tracer.start_as_current_span("operation", links=[link]) as span:
    # operation logic
    pass
```

### Exporters

Exporters send span data to backends.

**Console Exporter** (debugging):
```python
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

exporter = ConsoleSpanExporter()
processor = BatchSpanProcessor(exporter)
provider.add_span_processor(processor)
```

**OTLP Exporter** (standard protocol):
```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",
    headers={"api-key": "secret"},
    timeout=10
)
processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,
    max_export_batch_size=512,
    export_timeout_millis=30000
)
provider.add_span_processor(processor)
```

**Jaeger Exporter**:
```python
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
processor = BatchSpanProcessor(exporter)
provider.add_span_processor(processor)
```

**Zipkin Exporter**:
```python
from opentelemetry.exporter.zipkin.json import ZipkinExporter

exporter = ZipkinExporter(
    endpoint="http://localhost:9411/api/v2/spans"
)
processor = BatchSpanProcessor(exporter)
provider.add_span_processor(processor)
```

---

## Trace Context Propagation

### W3C Trace Context

W3C Trace Context is the standard for context propagation via HTTP headers.

**Headers**:
- `traceparent`: Required, contains trace-id, parent-id, trace-flags
- `tracestate`: Optional, vendor-specific data

**traceparent Format**:
```
version-format - trace-id - parent-id - trace-flags
00             - 4bf92f3577b34da6a3ce929d0e0e4736 - 00f067aa0ba902b7 - 01

version: 00 (current version)
trace-id: 32 hex characters (128-bit)
parent-id: 16 hex characters (64-bit, span-id)
trace-flags: 2 hex characters (8-bit, bit 0 = sampled)
```

**Example**:
```http
GET /api/users/123 HTTP/1.1
Host: api.example.com
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
tracestate: vendor1=value1,vendor2=value2
```

**Python Implementation**:
```python
from opentelemetry.propagate import inject, extract
from opentelemetry import trace

# Inject context into headers (outgoing request)
headers = {}
inject(headers)
# headers = {
#     "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
# }

# Extract context from headers (incoming request)
ctx = extract(headers)
with tracer.start_as_current_span("operation", context=ctx) as span:
    # span is child of extracted context
    pass
```

### B3 Propagation

B3 is Zipkin's propagation format, widely used in pre-W3C systems.

**Single Header** (B3):
```http
b3: 4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-1
    ^trace-id                       ^parent-id         ^sampled
```

**Multi Header** (B3 Multiple):
```http
X-B3-TraceId: 4bf92f3577b34da6a3ce929d0e0e4736
X-B3-SpanId: 00f067aa0ba902b7
X-B3-ParentSpanId: 0000000000000000
X-B3-Sampled: 1
```

**Python Configuration**:
```python
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry import propagate

# Set B3 multi-header propagator
propagate.set_global_textmap(B3MultiFormat())

# Or single header
from opentelemetry.propagators.b3 import B3SingleFormat
propagate.set_global_textmap(B3SingleFormat())
```

### Jaeger Propagation

Jaeger uses Uber-trace-id header.

**Format**:
```http
uber-trace-id: 4bf92f3577b34da6a3ce929d0e0e4736:00f067aa0ba902b7:0000000000000000:1
               ^trace-id                       ^span-id         ^parent    ^flags
```

### AWS X-Ray Propagation

AWS X-Ray uses custom trace header format.

**Format**:
```http
X-Amzn-Trace-Id: Root=1-67891233-abcdef012345678912345678;Parent=463ac35c9f6413ad;Sampled=1
```

### gRPC Metadata Propagation

gRPC uses metadata for context propagation.

**Python gRPC**:
```python
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient

# Auto-instrumentation handles propagation
GrpcInstrumentorClient().instrument()

# Manual propagation
from opentelemetry.propagate import inject

metadata = []
inject(metadata)  # Injects as tuple list

# Call with metadata
response = stub.GetUser(request, metadata=metadata)
```

### Message Queue Propagation

**Kafka Headers**:
```python
from kafka import KafkaProducer
from opentelemetry.propagate import inject

producer = KafkaProducer()
headers = []
inject(headers)  # [(b'traceparent', b'00-...')]

producer.send(
    'topic',
    value=message,
    headers=headers
)
```

**SQS Message Attributes**:
```python
import boto3
from opentelemetry.propagate import inject

sqs = boto3.client('sqs')
attributes = {}
inject(attributes)

sqs.send_message(
    QueueUrl='queue-url',
    MessageBody='message',
    MessageAttributes={
        k: {'StringValue': v, 'DataType': 'String'}
        for k, v in attributes.items()
    }
)
```

---

## Sampling Strategies

Sampling reduces trace volume by selecting a subset of traces to record.

### Why Sample?

**Challenges at Scale**:
- High traffic systems generate millions of traces/second
- Full instrumentation overhead (CPU, memory, network)
- Backend storage and query costs
- Network bandwidth limitations

**Sampling Goals**:
- Reduce overhead while maintaining visibility
- Capture representative sample of traffic
- Always capture errors and slow requests
- Balance cost vs. insight

### Sampling Decision Points

**1. Head-Based Sampling** (at trace start):
- Decision made when trace begins
- Consistent across entire trace
- Fast, low overhead
- May miss interesting traces

**2. Tail-Based Sampling** (after trace completes):
- Decision made after seeing full trace
- Can sample based on outcome (errors, latency)
- Higher overhead (buffer all spans)
- Better signal capture

### Head-Based Sampling

#### Always On Sampler

Sample every trace (100%).

```python
from opentelemetry.sdk.trace.sampling import AlwaysOnSampler

provider = TracerProvider(sampler=AlwaysOnSampler())
```

**Use Case**: Development, low-traffic systems

#### Always Off Sampler

Sample no traces (0%).

```python
from opentelemetry.sdk.trace.sampling import AlwaysOffSampler

provider = TracerProvider(sampler=AlwaysOffSampler())
```

**Use Case**: Disable tracing temporarily

#### Trace ID Ratio Sampler

Sample a fixed percentage of traces based on trace ID.

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
provider = TracerProvider(sampler=TraceIdRatioBased(0.1))
```

**Characteristics**:
- Deterministic (same trace ID always sampled or not)
- Consistent across services
- Uniform distribution

**Use Case**: Production baseline sampling

#### Parent-Based Sampler

Respect parent span's sampling decision.

```python
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

# If parent sampled, sample this span
# If no parent, use ratio-based sampler
provider = TracerProvider(
    sampler=ParentBased(
        root=TraceIdRatioBased(0.1)
    )
)
```

**Use Case**: Maintain trace continuity across services

#### Custom Sampler

Implement custom sampling logic.

```python
from opentelemetry.sdk.trace.sampling import (
    Sampler,
    SamplingResult,
    Decision
)
from opentelemetry.trace import SpanKind

class ErrorAndSlowSampler(Sampler):
    def __init__(self, base_rate=0.01, slow_threshold_ms=1000):
        self.base_rate = base_rate
        self.slow_threshold_ms = slow_threshold_ms

    def should_sample(
        self,
        parent_context,
        trace_id,
        name,
        kind,
        attributes,
        links
    ):
        # Always sample if parent sampled
        parent_span = trace.get_current_span(parent_context)
        if parent_span.get_span_context().trace_flags.sampled:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        # Sample errors
        if attributes and attributes.get("error"):
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        # Sample slow requests (if we have duration hint)
        duration_ms = attributes.get("duration_ms", 0)
        if duration_ms > self.slow_threshold_ms:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        # Otherwise, base rate
        if trace_id % 100 < self.base_rate * 100:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        return SamplingResult(Decision.DROP)

    def get_description(self):
        return f"ErrorAndSlowSampler({self.base_rate})"

provider = TracerProvider(sampler=ErrorAndSlowSampler())
```

### Tail-Based Sampling

Tail-based sampling requires collecting all spans before deciding.

**Implementation Options**:
1. **OTel Collector**: Use tail sampling processor
2. **Backend**: Sample in storage layer (e.g., Tempo)
3. **Custom**: Build buffering service

**OTel Collector Configuration**:
```yaml
processors:
  tail_sampling:
    decision_wait: 10s  # Wait time for all spans
    num_traces: 100000  # Buffer size
    policies:
      # Always sample errors
      - name: error-policy
        type: status_code
        status_code:
          status_codes:
            - ERROR

      # Sample slow traces (>1s)
      - name: slow-policy
        type: latency
        latency:
          threshold_ms: 1000

      # Sample 1% of normal traces
      - name: baseline-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 1

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

exporters:
  otlp:
    endpoint: jaeger:4317

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [tail_sampling]
      exporters: [otlp]
```

**Tail Sampling Policies**:
- **Status Code**: Sample by span status (OK, ERROR)
- **Latency**: Sample slow traces
- **Attribute**: Sample based on attribute values
- **Rate Limiting**: Max traces per second
- **Probabilistic**: Base rate for normal traces

### Adaptive Sampling

Dynamically adjust sampling rate based on traffic and errors.

**Strategies**:
1. **Target Rate**: Maintain target traces/second
2. **Error Boost**: Increase rate during error spikes
3. **Latency Boost**: Increase rate during slowdowns
4. **Time-Based**: Higher rate during business hours

**Example (Conceptual)**:
```python
class AdaptiveSampler(Sampler):
    def __init__(self, target_tps=100):
        self.target_tps = target_tps
        self.window_start = time.time()
        self.traces_sampled = 0
        self.lock = threading.Lock()

    def should_sample(self, parent_context, trace_id, name, kind, attributes, links):
        with self.lock:
            now = time.time()
            elapsed = now - self.window_start

            # Reset window every second
            if elapsed >= 1.0:
                self.traces_sampled = 0
                self.window_start = now
                elapsed = 0

            # Calculate current rate
            current_tps = self.traces_sampled / max(elapsed, 0.001)

            # Sample if under target
            if current_tps < self.target_tps:
                self.traces_sampled += 1
                return SamplingResult(Decision.RECORD_AND_SAMPLE)

            return SamplingResult(Decision.DROP)
```

### Sampling Best Practices

**Start Conservative**:
- Begin with 1-10% sampling
- Monitor coverage and costs
- Increase gradually if needed

**Layer Sampling**:
```
Base Rate:    1%   (all traffic)
Slow Traces:  100% (>1s latency)
Errors:       100% (status=error)
Important:    100% (specific endpoints)
```

**Per-Service Sampling**:
- High-traffic services: lower rate (0.1-1%)
- Low-traffic services: higher rate (10-100%)
- Critical services: always sample errors

**Monitor Sampling**:
- Track sampling ratio
- Ensure errors captured
- Verify representative sample

---

## Tracing Backends

### Jaeger

Open-source tracing backend by Uber (now CNCF).

**Architecture**:
```
Application
  └─> Jaeger Agent (sidecar)
       └─> Jaeger Collector
            └─> Storage (Cassandra, Elasticsearch, Memory)
                 └─> Jaeger Query (UI)
```

**Deployment (Docker)**:
```bash
docker run -d --name jaeger \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -p 5775:5775/udp \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 5778:5778 \
  -p 16686:16686 \
  -p 14268:14268 \
  -p 14250:14250 \
  -p 9411:9411 \
  jaegertracing/all-in-one:latest
```

**UI Access**: http://localhost:16686

**Features**:
- Service dependency graph
- Trace search by tags
- Latency percentiles
- Span detail view
- System architecture visualization

### Zipkin

Original distributed tracing system from Twitter.

**Architecture**:
```
Application
  └─> Zipkin Collector (HTTP/Kafka)
       └─> Storage (MySQL, Cassandra, Elasticsearch)
            └─> Zipkin UI
```

**Deployment**:
```bash
docker run -d -p 9411:9411 openzipkin/zipkin
```

**UI Access**: http://localhost:9411

**Features**:
- Trace search
- Dependency diagram
- Latency distribution
- Simpler than Jaeger

### Grafana Tempo

Open-source distributed tracing backend by Grafana Labs.

**Architecture**:
```
Application
  └─> Tempo Distributor
       └─> Tempo Ingester
            └─> Object Storage (S3, GCS, Azure Blob)
                 └─> Tempo Querier
                      └─> Grafana
```

**Key Features**:
- **Cost-Effective**: Object storage backend
- **High Scale**: Designed for massive trace volume
- **Grafana Integration**: Native integration
- **TraceQL**: Powerful query language
- **No Indexes**: Traces stored by ID only

**Deployment (Docker Compose)**:
```yaml
version: "3"
services:
  tempo:
    image: grafana/tempo:latest
    command: [ "-config.file=/etc/tempo.yaml" ]
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml
      - ./tempo-data:/tmp/tempo
    ports:
      - "3200:3200"   # tempo
      - "4317:4317"   # otlp grpc
      - "4318:4318"   # otlp http

  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./grafana-datasources.yaml:/etc/grafana/provisioning/datasources/datasources.yaml
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
    ports:
      - "3000:3000"
```

**tempo.yaml**:
```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
        http:

storage:
  trace:
    backend: local
    local:
      path: /tmp/tempo/blocks

querier:
  frontend_worker:
    frontend_address: tempo:9095
```

### Honeycomb

Commercial observability platform with advanced tracing.

**Features**:
- **BubbleUp**: Automatic anomaly detection
- **High-Cardinality**: Query any attribute
- **Derived Columns**: Computed fields
- **Triggers**: Alerts on trace patterns
- **Collaboration**: Share queries and boards

**Python Setup**:
```python
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

exporter = OTLPSpanExporter(
    endpoint="https://api.honeycomb.io",
    headers={
        "x-honeycomb-team": "YOUR_API_KEY",
        "x-honeycomb-dataset": "your-service"
    }
)
```

**Query Examples**:
```
# Find slow database queries
WHERE db.statement EXISTS
CALCULATE P99(duration_ms)
GROUP BY db.statement
ORDER BY P99(duration_ms) DESC

# Traces with errors
WHERE status_code = ERROR
CALCULATE COUNT
GROUP BY error.message
```

### Lightstep (ServiceNow Cloud Observability)

Enterprise observability platform.

**Features**:
- **Change Intelligence**: Correlate deployments with performance
- **Service Diagram**: Live dependency graph
- **Trace Analysis**: Root cause identification
- - **Incident Response**: Integrated alerting

### New Relic

Full-stack observability with distributed tracing.

**Features**:
- **Trace Observer**: Tail-based sampling in cloud
- **Infinite Tracing**: 100% trace ingestion
- **Cross-Application Tracing**: Correlate traces and APM

### Datadog APM

Application Performance Monitoring with tracing.

**Features**:
- **Trace Search & Analytics**: High-cardinality queries
- **Service Map**: Auto-discovered dependencies
- **Trace-to-Log**: Correlated logging
- **Continuous Profiler**: Code-level performance

### AWS X-Ray

AWS-native distributed tracing service.

**Features**:
- **AWS Integration**: Lambda, ECS, API Gateway
- **Service Map**: Visual dependency graph
- **Trace Search**: Query by annotations
- **Insights**: Automated issue detection

---

## Instrumentation Patterns

### Auto-Instrumentation

Automatic instrumentation without code changes.

**Python Auto-Instrumentation**:
```bash
# Install
pip install opentelemetry-distro
pip install opentelemetry-exporter-otlp

# Bootstrap (installs instrumentations)
opentelemetry-bootstrap -a install

# Run with auto-instrumentation
opentelemetry-instrument \
  --traces_exporter console \
  --service_name my-service \
  python app.py
```

**Supported Libraries**:
- **HTTP**: requests, httpx, urllib, aiohttp
- **Web Frameworks**: Flask, FastAPI, Django, Starlette
- **Databases**: psycopg2, pymongo, redis, sqlalchemy
- **Messaging**: kafka-python, pika (RabMQ)
- **gRPC**: grpc

**Configuration via Environment**:
```bash
export OTEL_SERVICE_NAME=my-service
export OTEL_TRACES_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_EXPORTER_OTLP_INSECURE=true
export OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true

python app.py
```

### Manual Instrumentation

Explicit span creation for custom logic.

**FastAPI Example**:
```python
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

tracer = trace.get_tracer(__name__)

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    # Auto span from FastAPIInstrumentor

    with tracer.start_as_current_span("fetch_user_from_db") as span:
        span.set_attribute("user.id", user_id)
        user = await db.get_user(user_id)
        span.set_attribute("user.found", user is not None)

    if not user:
        with tracer.start_as_current_span("cache_miss_metric"):
            metrics.increment("user.cache.miss")

    return user
```

### Middleware Pattern

Instrument at middleware layer for cross-cutting concerns.

**Custom Middleware**:
```python
from fastapi import Request
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

@app.middleware("http")
async def tracing_middleware(request: Request, call_next):
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span(
        f"{request.method} {request.url.path}",
        kind=trace.SpanKind.SERVER
    ) as span:
        # Add request attributes
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.target", request.url.path)

        # Add custom context
        if "user-id" in request.headers:
            span.set_attribute("user.id", request.headers["user-id"])

        try:
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)

            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR))

            return response
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
```

### Database Instrumentation

**SQLAlchemy**:
```python
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy import create_engine

engine = create_engine("postgresql://user:pass@localhost/db")
SQLAlchemyInstrumentor().instrument(engine=engine)

# All queries automatically traced
```

**MongoDB**:
```python
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from pymongo import MongoClient

PymongoInstrumentor().instrument()

client = MongoClient("mongodb://localhost:27017")
# All operations automatically traced
```

### Async Context Propagation

**asyncio**:
```python
import asyncio
from opentelemetry import trace, context

tracer = trace.get_tracer(__name__)

async def parent_operation():
    with tracer.start_as_current_span("parent") as parent_span:
        parent_span.set_attribute("operation", "parent")

        # Context automatically propagates to child coroutines
        await child_operation()

async def child_operation():
    # Automatically inherits parent context
    with tracer.start_as_current_span("child") as child_span:
        child_span.set_attribute("operation", "child")
        await asyncio.sleep(0.1)

asyncio.run(parent_operation())
```

**Concurrent Tasks**:
```python
async def process_items(items):
    with tracer.start_as_current_span("process_batch") as batch_span:
        batch_span.set_attribute("batch.size", len(items))

        # Capture current context
        ctx = context.get_current()

        # Create tasks with context
        tasks = [
            context.run(ctx, process_item, item)
            for item in items
        ]

        results = await asyncio.gather(*tasks)
        return results

async def process_item(item):
    # Inherits batch_span as parent
    with tracer.start_as_current_span("process_item") as span:
        span.set_attribute("item.id", item.id)
        # process item
```

---

## Performance and Overhead

### Overhead Sources

**1. Span Creation** (~1-5 microseconds):
- Allocate span structure
- Generate span ID
- Capture start time

**2. Attribute Setting** (~0.5 microseconds per attribute):
- String formatting
- Memory allocation

**3. Context Propagation** (~2-10 microseconds):
- Serialize/deserialize context
- Header manipulation

**4. Span Export** (~10-100 microseconds batched):
- Serialization (JSON/protobuf)
- Network I/O
- Batching overhead

**Total Overhead**: Typically 1-5% CPU at 1% sampling

### Optimization Strategies

**1. Sampling**:
```python
# Reduce sampling rate for high-traffic endpoints
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# 1% sampling
provider = TracerProvider(sampler=TraceIdRatioBased(0.01))
```

**2. Batch Export**:
```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Optimize batch parameters
processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,        # Buffer size
    schedule_delay_millis=5000, # Export every 5s
    max_export_batch_size=512,  # Spans per batch
    export_timeout_millis=30000 # Export timeout
)
```

**3. Attribute Cardinality**:
```python
# BAD: High cardinality
span.set_attribute("user.id", user_id)  # Millions of unique values

# GOOD: Low cardinality
span.set_attribute("user.tier", user.tier)  # "free", "pro", "enterprise"
```

**4. Selective Instrumentation**:
```python
# Skip tracing for health checks
@app.get("/health")
async def health_check():
    # No manual spans for simple endpoints
    return {"status": "ok"}

# Trace complex operations
@app.post("/orders")
async def create_order(order: Order):
    with tracer.start_as_current_span("create_order"):
        # Complex business logic
        pass
```

**5. Async Export**:
```python
# Use async exporter to avoid blocking
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# gRPC is async by default
exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
```

### Profiling Overhead

**Measure Baseline**:
```python
import time
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# Without tracing
start = time.perf_counter()
for _ in range(100000):
    # operation
    pass
baseline = time.perf_counter() - start

# With tracing
start = time.perf_counter()
for _ in range(100000):
    with tracer.start_as_current_span("operation"):
        # operation
        pass
traced = time.perf_counter() - start

overhead_pct = ((traced - baseline) / baseline) * 100
print(f"Overhead: {overhead_pct:.2f}%")
```

### Production Tuning

**Memory**:
- Limit max_queue_size to prevent memory growth
- Monitor span processor queue depth
- Use bounded queues in high-throughput services

**CPU**:
- Reduce sampling for hot paths
- Batch exports to reduce syscalls
- Use efficient serialization (protobuf vs JSON)

**Network**:
- Use OTLP gRPC (more efficient than HTTP)
- Deploy local collector to reduce latency
- Enable gzip compression

**Latency**:
- Export asynchronously (never block request path)
- Use local agent/collector (sub-millisecond export)
- Set reasonable export timeouts

---

## Correlation with Logs and Metrics

### Trace-Log Correlation

Link logs to traces for unified debugging.

**Python Logging Integration**:
```python
import logging
from opentelemetry import trace
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Auto-inject trace context into logs
LoggingInstrumentor().instrument(set_logging_format=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] %(message)s'
)

logger = logging.getLogger(__name__)

with tracer.start_as_current_span("operation") as span:
    logger.info("Processing request")  # Includes trace_id and span_id
```

**Structured Logging**:
```python
import structlog
from opentelemetry import trace

def add_trace_context(logger, method_name, event_dict):
    span = trace.get_current_span()
    if span:
        ctx = span.get_span_context()
        event_dict['trace_id'] = format(ctx.trace_id, '032x')
        event_dict['span_id'] = format(ctx.span_id, '016x')
    return event_dict

structlog.configure(
    processors=[
        add_trace_context,
        structlog.processors.JSONRenderer()
    ]
)

log = structlog.get_logger()

with tracer.start_as_current_span("operation"):
    log.info("event", user_id=123)
    # {"event": "event", "user_id": 123, "trace_id": "...", "span_id": "..."}
```

### Trace-Metric Correlation

Connect metrics to traces for context.

**Exemplars** (Prometheus):
```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# Create meter
meter_provider = MeterProvider(
    metric_readers=[PeriodicExportingMetricReader(exporter)]
)
metrics.set_meter_provider(meter_provider)

meter = metrics.get_meter(__name__)

# Create histogram with exemplars
request_duration = meter.create_histogram(
    "http.server.request.duration",
    unit="ms",
    description="HTTP request duration"
)

# Record with trace context as exemplar
with tracer.start_as_current_span("request") as span:
    start = time.perf_counter()
    # handle request
    duration_ms = (time.perf_counter() - start) * 1000

    # Exemplar links metric to trace
    request_duration.record(
        duration_ms,
        attributes={
            "http.method": "GET",
            "http.status_code": 200
        }
    )
```

**Metric Attributes from Spans**:
```python
# Record metrics using span attributes
with tracer.start_as_current_span("db.query") as span:
    span.set_attribute("db.system", "postgresql")
    span.set_attribute("db.operation", "SELECT")

    start = time.perf_counter()
    result = execute_query()
    duration = time.perf_counter() - start

    # Use same attributes for consistency
    db_duration.record(
        duration * 1000,
        attributes={
            "db.system": span.get_attribute("db.system"),
            "db.operation": span.get_attribute("db.operation")
        }
    )
```

### Unified Query

**Grafana**:
- Use Tempo data source in Grafana
- Link metrics panels to traces (exemplars)
- Create trace-to-metrics queries

```promql
# Metric query with exemplar
histogram_quantile(0.99,
  rate(http_server_request_duration_bucket[5m])
)

# Click exemplar to jump to trace in Tempo
```

**Honeycomb**:
- Automatic trace-metric linking
- Derived columns for custom metrics
- BubbleUp shows metric outliers with traces

---

## Production Patterns

### Service Mesh Integration

**Istio/Envoy**:
- Auto-injects trace headers
- Creates parent span at ingress
- Propagates context via sidecar

**Configuration**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: istio
data:
  mesh: |
    defaultConfig:
      tracing:
        zipkin:
          address: zipkin.istio-system:9411
        sampling: 1.0  # 100% sampling
```

**Application Integration**:
```python
# Extract context from Envoy headers
from opentelemetry.propagate import extract

@app.middleware("http")
async def extract_trace_context(request, call_next):
    ctx = extract(request.headers)

    # Start span as child of Envoy span
    with tracer.start_as_current_span("app.request", context=ctx):
        response = await call_next(request)
        return response
```

### Multi-Tenant Tracing

**Tenant Isolation**:
```python
with tracer.start_as_current_span("request") as span:
    tenant_id = request.headers.get("x-tenant-id")
    span.set_attribute("tenant.id", tenant_id)
    span.set_attribute("tenant.tier", get_tier(tenant_id))

    # All child spans inherit tenant context
    process_request(tenant_id)
```

**Backend Filtering**:
```
# Query traces for specific tenant
tenant.id = "acme-corp"

# Per-tenant sampling
IF tenant.tier = "enterprise" THEN sample_rate = 1.0
ELSE sample_rate = 0.01
```

### Error Tracking

**Span Status**:
```python
try:
    result = risky_operation()
    span.set_status(Status(StatusCode.OK))
except ValidationError as e:
    # Client error (user's fault)
    span.set_status(Status(StatusCode.ERROR, "Validation failed"))
    span.set_attribute("error.type", "validation")
    span.record_exception(e)
except DatabaseError as e:
    # Server error (our fault)
    span.set_status(Status(StatusCode.ERROR, "Database unavailable"))
    span.set_attribute("error.type", "database")
    span.record_exception(e)
```

**Error Span Events**:
```python
span.add_event("retry.attempt", {
    "retry.count": attempt,
    "retry.delay_ms": delay * 1000
})

span.add_event("circuit_breaker.opened", {
    "failure_count": failures,
    "threshold": threshold
})
```

### Security and Compliance

**PII Filtering**:
```python
def sanitize_attributes(attributes):
    """Remove PII from span attributes"""
    sensitive_keys = ["password", "ssn", "credit_card", "email"]
    return {
        k: "[REDACTED]" if k in sensitive_keys else v
        for k, v in attributes.items()
    }

# Custom span processor
class PIIFilter(SpanProcessor):
    def on_start(self, span, parent_context):
        pass

    def on_end(self, span):
        # Redact sensitive attributes
        if span.attributes:
            span.attributes = sanitize_attributes(span.attributes)
```

**Data Retention**:
- Set TTL in backend (e.g., Tempo: 7-30 days)
- Use sampling to reduce stored data
- Comply with data residency requirements

---

## Common Anti-Patterns

### 1. Over-Instrumentation

**Problem**: Creating too many spans, overwhelming backend.

**Bad**:
```python
with tracer.start_as_current_span("process_items"):
    for item in items:
        with tracer.start_as_current_span(f"process_item_{item.id}"):
            # Creates millions of spans
            pass
```

**Good**:
```python
with tracer.start_as_current_span("process_items") as span:
    span.set_attribute("batch.size", len(items))
    for item in items:
        # No span for each item
        process_item(item)
    span.set_attribute("items.processed", len(items))
```

### 2. High-Cardinality Attributes

**Problem**: Attributes with millions of unique values.

**Bad**:
```python
span.set_attribute("user.id", user_id)  # Millions of users
span.set_attribute("request.timestamp", timestamp)  # Infinite values
```

**Good**:
```python
span.set_attribute("user.tier", user.tier)  # "free", "pro", "enterprise"
span.set_attribute("request.hour", timestamp.hour)  # 0-23
```

### 3. Missing Context Propagation

**Problem**: Traces break at service boundaries.

**Bad**:
```python
import requests

# No trace context propagated
response = requests.get("http://service-b/api")
```

**Good**:
```python
from opentelemetry.propagate import inject

headers = {}
inject(headers)  # Add traceparent header
response = requests.get("http://service-b/api", headers=headers)
```

### 4. Forgetting to End Spans

**Problem**: Manual spans left open, causing memory leaks.

**Bad**:
```python
span = tracer.start_span("operation")
span.set_attribute("key", "value")
# Forgot to call span.end()!
```

**Good**:
```python
# Use context manager (auto-closes)
with tracer.start_as_current_span("operation") as span:
    span.set_attribute("key", "value")
    # Automatically ends

# Or explicit try/finally
span = tracer.start_span("operation")
try:
    span.set_attribute("key", "value")
finally:
    span.end()
```

### 5. Blocking on Export

**Problem**: Exporting spans synchronously in request path.

**Bad**:
```python
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# Blocks request until export completes!
processor = SimpleSpanProcessor(exporter)
```

**Good**:
```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Exports asynchronously in background
processor = BatchSpanProcessor(exporter)
```

### 6. No Sampling Strategy

**Problem**: 100% sampling in production, overwhelming system.

**Bad**:
```python
# Default: sample everything
provider = TracerProvider()
```

**Good**:
```python
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

# Sample 1% of traces
provider = TracerProvider(
    sampler=ParentBased(root=TraceIdRatioBased(0.01))
)
```

### 7. Incomplete Error Handling

**Problem**: Errors not recorded in spans.

**Bad**:
```python
with tracer.start_as_current_span("operation"):
    try:
        risky_operation()
    except Exception:
        pass  # Silently swallowed, not recorded
```

**Good**:
```python
with tracer.start_as_current_span("operation") as span:
    try:
        risky_operation()
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise
```

---

## Troubleshooting Guide

### No Traces Appearing

**Check 1: Exporter Configuration**:
```python
# Add console exporter to verify spans created
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
```

**Check 2: Sampling**:
```python
# Verify sampler (should see in logs)
print(provider.sampler)

# Temporarily set to AlwaysOn
from opentelemetry.sdk.trace.sampling import AlwaysOnSampler
provider = TracerProvider(sampler=AlwaysOnSampler())
```

**Check 3: Backend Connectivity**:
```bash
# Test OTLP endpoint
curl -v http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans":[]}'

# Check firewall/network
telnet localhost 4317
```

### Broken Traces (Missing Spans)

**Check 1: Context Propagation**:
```python
# Verify headers injected
from opentelemetry.propagate import inject

headers = {}
inject(headers)
print(headers)  # Should contain 'traceparent'
```

**Check 2: Async Context**:
```python
# Use context.attach for async tasks
from opentelemetry import context

ctx = context.get_current()
asyncio.create_task(context.run(ctx, async_operation))
```

**Check 3: Service Instrumentation**:
```python
# Ensure all services use same propagator
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry import propagate

propagate.set_global_textmap(B3MultiFormat())
```

### High Overhead

**Check 1: Sampling Rate**:
```python
# Reduce sampling
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
provider = TracerProvider(sampler=TraceIdRatioBased(0.01))
```

**Check 2: Span Count**:
```python
# Add span counting metric
span_count = meter.create_counter("trace.spans.created")

class CountingProcessor(SpanProcessor):
    def on_end(self, span):
        span_count.add(1)
        # Alert if > threshold
```

**Check 3: Export Frequency**:
```python
# Reduce export frequency
processor = BatchSpanProcessor(
    exporter,
    schedule_delay_millis=10000  # Export every 10s instead of 5s
)
```

### Incomplete Trace Data

**Check 1: Span Processors**:
```python
# Verify processor registered
print(provider._active_span_processor)
```

**Check 2: Export Errors**:
```python
# Log export failures
import logging
logging.basicConfig(level=logging.DEBUG)

# Check exporter logs
# Look for "Failed to export" messages
```

**Check 3: Queue Overflow**:
```python
# Increase queue size
processor = BatchSpanProcessor(
    exporter,
    max_queue_size=4096  # Default 2048
)
```

---

## Summary

Distributed tracing provides end-to-end visibility into request flows across microservices:

**Key Concepts**:
- **Traces**: Complete request journeys
- **Spans**: Individual operations
- **Context**: Trace/span IDs propagated across boundaries

**OpenTelemetry**:
- Industry-standard API and SDK
- Vendor-agnostic instrumentation
- Auto and manual instrumentation

**Sampling**:
- Head-based: Fast, low overhead
- Tail-based: Better signal, higher cost
- Adaptive: Dynamic based on traffic

**Backends**:
- Jaeger: Full-featured, self-hosted
- Tempo: Cost-effective, object storage
- Honeycomb: High-cardinality queries
- Zipkin: Simple, mature

**Production**:
- Sample appropriately (1-10%)
- Batch exports asynchronously
- Correlate with logs and metrics
- Monitor overhead
- Filter PII

**Avoid**:
- Over-instrumentation
- High-cardinality attributes
- Missing context propagation
- Blocking exports
- No sampling strategy

For implementation examples, see the `examples/` directory. For scripts to analyze traces, see `scripts/`.
