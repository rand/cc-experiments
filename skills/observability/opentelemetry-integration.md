---
name: observability-opentelemetry-integration
description: Integrating OpenTelemetry for unified observability (traces, metrics, logs)
---

# OpenTelemetry Integration

**Scope**: OTel Collector, auto-instrumentation, manual instrumentation, traces/metrics/logs correlation, backend integrations

**Lines**: 460

**Last Updated**: 2025-10-26

---

## When to Use This Skill

Use this skill when:
- Adopting OpenTelemetry for unified observability (traces, metrics, logs)
- Migrating from proprietary instrumentation (Datadog, New Relic, AppDynamics)
- Implementing distributed tracing across microservices
- Correlating traces, metrics, and logs with exemplars
- Setting up OTel Collector pipelines and processors
- Auto-instrumenting applications (Python, Java, Go, Node.js)
- Integrating with observability backends (Grafana, Jaeger, Datadog)
- Standardizing telemetry across polyglot environments

**Don't use** for:
- Simple metrics-only instrumentation (use Prometheus directly)
- Single-process applications without distributed components
- Legacy systems that can't run OTel agents

**Context (2024-2025)**:
- **89% of organizations** investing in OpenTelemetry (CNCF survey)
- **75% still use Prometheus** alongside OTel (complementary, not replacement)
- **100% YoY increase** in OTel search volume (2024-2025)
- **45% YoY growth** in OTel adoption across enterprises

---

## Core Concepts

### OpenTelemetry Architecture

```
Application Code
  ↓
OTel SDK (auto or manual instrumentation)
  ↓
OTel Collector (optional but recommended)
  ↓ (pipelines: receivers → processors → exporters)
Backend (Jaeger, Grafana Tempo, Datadog, etc.)
```

**Key Components**:
1. **SDK**: Libraries for instrumenting code (auto or manual)
2. **Collector**: Pipeline for receiving, processing, exporting telemetry
3. **Backend**: Storage and visualization (Jaeger, Tempo, Prometheus, Loki)

### Signals: Traces, Metrics, Logs

**Traces**: Request flows across services
- Spans: Individual operations with start/end times
- Context propagation: W3C Trace Context headers
- Use: "Why is this request slow?"

**Metrics**: Aggregated measurements over time
- Counters, gauges, histograms (like Prometheus)
- Exemplars: Link metrics to traces
- Use: "How many errors occurred?"

**Logs**: Discrete events with context
- Structured logs with trace/span IDs
- Correlation with traces and metrics
- Use: "What happened in this request?"

### OpenTelemetry vs Prometheus

| Feature | OpenTelemetry | Prometheus |
|---------|--------------|------------|
| **Purpose** | Unified telemetry (traces/metrics/logs) | Metrics-only |
| **Adoption** | 89% investment (2024) | 75% active usage (2024) |
| **Model** | Push (via Collector) | Pull (scrape) |
| **Traces** | Native support | None |
| **Logs** | Native support | None (use Loki) |
| **Metrics** | Compatible with Prometheus | Native |
| **Exemplars** | Yes (link metrics → traces) | Yes (since v2.26) |
| **Use Case** | Modern cloud-native observability | Metrics-focused monitoring |

**Key Insight**: OTel complements Prometheus (not replaces). Use OTel for traces/logs, export to Prometheus for metrics.

---

## Patterns

### Pattern 1: OTel Collector Configuration

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  # Prometheus scraper (if needed)
  prometheus:
    config:
      scrape_configs:
        - job_name: 'otel-collector'
          scrape_interval: 15s
          static_configs:
            - targets: ['localhost:8888']

processors:
  # Batch telemetry for efficiency
  batch:
    timeout: 10s
    send_batch_size: 1024

  # Sample traces (90% reduction)
  probabilistic_sampler:
    sampling_percentage: 10

  # Add resource attributes
  resource:
    attributes:
      - key: environment
        value: production
        action: insert
      - key: service.version
        value: ${SERVICE_VERSION}
        action: insert

  # Remove PII from logs
  attributes:
    actions:
      - key: email
        action: delete
      - key: ssn
        action: delete

exporters:
  # Jaeger for traces
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true

  # Prometheus for metrics
  prometheus:
    endpoint: 0.0.0.0:8889
    namespace: otel

  # Loki for logs
  loki:
    endpoint: http://loki:3100/loki/api/v1/push
    labels:
      resource:
        service.name: "service_name"
        environment: "env"

  # Datadog (if using commercial backend)
  datadog:
    api:
      site: datadoghq.com
      key: ${DD_API_KEY}

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, probabilistic_sampler, resource]
      exporters: [otlp/jaeger, datadog]

    metrics:
      receivers: [otlp, prometheus]
      processors: [batch, resource]
      exporters: [prometheus, datadog]

    logs:
      receivers: [otlp]
      processors: [batch, attributes, resource]
      exporters: [loki, datadog]

  telemetry:
    logs:
      level: info
    metrics:
      address: 0.0.0.0:8888
```

### Pattern 2: Auto-Instrumentation (Python)

```python
# Auto-instrumentation with opentelemetry-instrument CLI
# Install:
# pip install opentelemetry-distro opentelemetry-exporter-otlp

# Run with auto-instrumentation:
# opentelemetry-instrument \
#   --traces_exporter otlp \
#   --metrics_exporter otlp \
#   --service_name my-service \
#   --exporter_otlp_endpoint http://otel-collector:4318 \
#   python app.py

from flask import Flask
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/api/users/<user_id>')
def get_user(user_id):
    # Auto-instrumented by OTel
    logging.info(f"Fetching user {user_id}")

    # Database query (auto-traced)
    user = db.query(User).filter_by(id=user_id).first()

    # HTTP call (auto-traced)
    response = requests.get(f'http://auth-service/validate/{user_id}')

    return {"user": user.to_dict()}

if __name__ == '__main__':
    app.run()
```

**Auto-instrumentation supports**:
- **Python**: Flask, Django, FastAPI, SQLAlchemy, requests, httpx
- **Java**: Spring Boot, JDBC, Hibernate, OkHttp, gRPC
- **Node.js**: Express, Fastify, HTTP, MongoDB, MySQL
- **Go**: net/http, database/sql, gRPC (requires manual setup)

### Pattern 3: Manual Instrumentation (Python)

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource

# Setup tracer
resource = Resource.create({
    "service.name": "order-service",
    "service.version": "1.0.0",
    "deployment.environment": "production"
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

span_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317")
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(span_exporter)
)

# Setup metrics
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://otel-collector:4317")
)
metrics.set_meter_provider(MeterProvider(
    resource=resource,
    metric_readers=[metric_reader]
))
meter = metrics.get_meter(__name__)

# Create metrics
order_counter = meter.create_counter(
    "orders.placed",
    description="Number of orders placed",
    unit="1"
)

order_value_histogram = meter.create_histogram(
    "orders.value",
    description="Order value in USD",
    unit="USD"
)

# Manual instrumentation
def place_order(order_data: dict):
    with tracer.start_as_current_span("place_order") as span:
        # Add attributes to span
        span.set_attribute("order.id", order_data["id"])
        span.set_attribute("order.total", order_data["total"])
        span.set_attribute("customer.id", order_data["customer_id"])

        try:
            # Validate order
            with tracer.start_as_current_span("validate_order"):
                validate(order_data)

            # Save to database
            with tracer.start_as_current_span("save_to_database") as db_span:
                db_span.set_attribute("db.system", "postgresql")
                db_span.set_attribute("db.operation", "INSERT")
                order_id = db.save_order(order_data)

            # Update metrics
            order_counter.add(1, {"status": "success"})
            order_value_histogram.record(order_data["total"])

            # Add event to span
            span.add_event("Order placed successfully", {
                "order.id": order_id
            })

            return order_id

        except Exception as e:
            # Record exception in span
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))

            order_counter.add(1, {"status": "error"})
            raise
```

### Pattern 4: Traces + Metrics Correlation (Exemplars)

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.metrics import MeterProvider

# Enable exemplars for histograms
meter_provider = MeterProvider(
    views=[
        View(
            instrument_name="http.server.duration",
            aggregation=ExplicitBucketHistogramAggregation(
                boundaries=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
                record_min_max=True
            )
        )
    ]
)

metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

duration_histogram = meter.create_histogram(
    "http.server.duration",
    description="HTTP request duration",
    unit="s"
)

# Record metric with trace context (automatic exemplar)
def handle_request(request):
    start = time.time()

    # Trace is automatically linked to metric
    with tracer.start_as_current_span("handle_request") as span:
        try:
            response = process(request)
            return response
        finally:
            duration = time.time() - start
            # Exemplar links this metric point to the trace
            duration_histogram.record(duration, {
                "http.method": request.method,
                "http.status_code": response.status_code
            })
```

**Exemplar workflow**:
1. High latency metric detected: p95 = 2.5s
2. Click on metric point in Grafana
3. View exemplar trace IDs linked to that metric
4. Jump to trace view to see exact slow request

### Pattern 5: Log + Trace Correlation

```python
import logging
from opentelemetry import trace

# Configure structured logging with trace context
class TraceContextFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        if span:
            ctx = span.get_span_context()
            record.trace_id = format(ctx.trace_id, '032x')
            record.span_id = format(ctx.span_id, '016x')
        else:
            record.trace_id = '0' * 32
            record.span_id = '0' * 16
        return True

logging.basicConfig(
    format='%(asctime)s %(levelname)s [trace_id=%(trace_id)s span_id=%(span_id)s] %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)
logger.addFilter(TraceContextFilter())

# Use logger within traced functions
def process_payment(payment_data):
    with tracer.start_as_current_span("process_payment") as span:
        logger.info("Processing payment", extra={
            "payment.amount": payment_data["amount"],
            "payment.method": payment_data["method"]
        })

        try:
            result = charge(payment_data)
            logger.info("Payment successful", extra={"payment.id": result.id})
            return result
        except Exception as e:
            logger.error("Payment failed", extra={"error": str(e)})
            raise

# Log output includes trace/span IDs:
# 2025-10-26 10:30:15 INFO [trace_id=4bf92f3577b34da6a3ce929d0e0e4736 span_id=00f067aa0ba902b7] Processing payment
```

### Pattern 6: Sampling Strategies

```yaml
# Tail-based sampling (smart sampling after trace completes)
processors:
  tail_sampling:
    policies:
      # Always sample errors
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]

      # Sample slow requests (>1s)
      - name: slow-requests
        type: latency
        latency:
          threshold_ms: 1000

      # Sample 10% of all other requests
      - name: probabilistic
        type: probabilistic
        probabilistic:
          sampling_percentage: 10

      # Always sample specific endpoints
      - name: critical-endpoints
        type: string_attribute
        string_attribute:
          key: http.target
          values: [/api/checkout, /api/payment]

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [tail_sampling, batch]
      exporters: [otlp/jaeger]
```

### Pattern 7: Resource Attributes

```python
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

# Standard semantic conventions
resource = Resource.create({
    # Service attributes
    SERVICE_NAME: "order-service",
    SERVICE_VERSION: "1.2.3",
    "service.namespace": "ecommerce",
    "service.instance.id": "order-service-abc123",

    # Deployment attributes
    "deployment.environment": "production",
    "deployment.region": "us-east-1",

    # Cloud provider attributes
    "cloud.provider": "aws",
    "cloud.platform": "aws_eks",
    "cloud.region": "us-east-1",
    "cloud.availability_zone": "us-east-1a",

    # Kubernetes attributes (if applicable)
    "k8s.cluster.name": "prod-cluster",
    "k8s.namespace.name": "ecommerce",
    "k8s.pod.name": "order-service-7d8f5c9b4-xk2pl",
    "k8s.container.name": "order-service",
})

# Use resource in tracer/meter providers
tracer_provider = TracerProvider(resource=resource)
```

---

## Backend Integrations

### Grafana Stack (Open Source)

```yaml
# docker-compose.yml
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    volumes:
      - ./otel-config.yaml:/etc/otel-collector-config.yaml
    command: ["--config=/etc/otel-collector-config.yaml"]
    ports:
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP

  # Traces
  tempo:
    image: grafana/tempo:latest
    ports:
      - "3200:3200"

  # Metrics
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  # Logs
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"

  # Visualization
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
```

### Datadog Integration

```yaml
# otel-collector-config.yaml
exporters:
  datadog:
    api:
      site: datadoghq.com
      key: ${DD_API_KEY}

    host_metadata:
      enabled: true
      hostname: ${HOSTNAME}
      tags:
        - env:production
        - team:platform

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [datadog]

    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [datadog]
```

### Jaeger Integration

```yaml
exporters:
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/jaeger]
```

---

## Quick Reference

### Installation

```bash
# Python
pip install opentelemetry-distro opentelemetry-exporter-otlp

# Auto-instrumentation
pip install opentelemetry-instrumentation-flask  # or django, fastapi, etc.

# Node.js
npm install @opentelemetry/sdk-node @opentelemetry/auto-instrumentations-node

# Go (manual only)
go get go.opentelemetry.io/otel
go get go.opentelemetry.io/otel/sdk
go get go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc

# Java
# Download opentelemetry-javaagent.jar
java -javaagent:opentelemetry-javaagent.jar \
     -Dotel.service.name=my-service \
     -Dotel.exporter.otlp.endpoint=http://otel-collector:4317 \
     -jar myapp.jar
```

### OTel Collector Deployment

```bash
# Docker
docker run -v $(pwd)/config.yaml:/etc/otel-collector-config.yaml \
  -p 4317:4317 -p 4318:4318 \
  otel/opentelemetry-collector-contrib:latest \
  --config=/etc/otel-collector-config.yaml

# Kubernetes
kubectl apply -f https://github.com/open-telemetry/opentelemetry-operator/releases/latest/download/opentelemetry-operator.yaml
```

### Key Environment Variables

```bash
# Exporter endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318

# Service name
export OTEL_SERVICE_NAME=my-service

# Resource attributes
export OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production,service.version=1.0.0

# Traces, metrics, logs exporters
export OTEL_TRACES_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
```

---

## Anti-Patterns

### ❌ Not Using OTel Collector

```
# WRONG: Direct export to backend
App → Jaeger (vendor lock-in, no processing)

# CORRECT: Export through Collector
App → OTel Collector → Jaeger (portable, scalable)
```

### ❌ Over-Sampling in Production

```yaml
# WRONG: 100% sampling (expensive, high cardinality)
processors:
  probabilistic_sampler:
    sampling_percentage: 100

# CORRECT: Tail-based sampling (smart sampling)
processors:
  tail_sampling:
    policies:
      - name: errors
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: probabilistic
        type: probabilistic
        probabilistic: {sampling_percentage: 10}
```

### ❌ Missing Resource Attributes

```python
# WRONG: No context about service
resource = Resource.create({})

# CORRECT: Rich service metadata
resource = Resource.create({
    "service.name": "order-service",
    "service.version": "1.0.0",
    "deployment.environment": "production"
})
```

### ❌ Not Correlating Signals

```python
# WRONG: Logs without trace context
logger.info("Processing order")

# CORRECT: Logs with trace/span IDs
logger.info("Processing order", extra={
    "trace_id": trace.get_current_span().get_span_context().trace_id
})
```

---

## Related Skills

- **distributed-tracing.md** - Deep dive into distributed tracing concepts
- **metrics-instrumentation.md** - Prometheus and metrics best practices
- **structured-logging.md** - Log formatting and correlation
- **observability-cost-optimization.md** - Reduce OTel costs with sampling/filtering

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
