---
name: observability-metrics-instrumentation
description: Instrumenting applications for observability
---



# Metrics Instrumentation

**Scope**: Prometheus, StatsD, custom metrics, cardinality, histograms, counters, gauges

**Lines**: 394

**Last Updated**: 2025-10-18

---

## When to Use This Skill

Use this skill when:
- Instrumenting applications for observability
- Setting up Prometheus or StatsD metrics collection
- Designing custom metrics for business/technical KPIs
- Building dashboards requiring time-series data
- Implementing SLIs (Service Level Indicators) for SLOs
- Monitoring system performance (latency, throughput, errors)
- Detecting anomalies and performance degradation
- Capacity planning based on resource utilization

**Don't use** for:
- Detailed request tracing (use distributed tracing instead)
- Log aggregation (use structured logging instead)
- One-off debugging (logs are better)

---

## Core Concepts

### Metric Types

**1. Counter** - Monotonically increasing value
- Examples: Total requests, total errors, bytes sent
- Operations: Increment only (resets to 0 on restart)
- Query patterns: `rate()`, `increase()` in PromQL

**2. Gauge** - Value that can go up or down
- Examples: Active connections, memory usage, queue size
- Operations: Set, increment, decrement
- Query patterns: Direct value, `avg()`, `max()`

**3. Histogram** - Distribution of values in buckets
- Examples: Request latency, response size
- Operations: Observe value, auto-buckets
- Provides: `_bucket`, `_sum`, `_count` metrics
- Query patterns: `histogram_quantile()` for percentiles

**4. Summary** - Similar to histogram, client-side quantiles
- Examples: Request duration quantiles (p50, p95, p99)
- Operations: Observe value, calculate quantiles
- Provides: Quantiles, `_sum`, `_count`
- **Caution**: Cannot aggregate across instances

### Cardinality

**Definition**: Number of unique time series (metric + unique label combinations)

**Example**:
```
# 1 metric × 3 status codes × 10 endpoints = 30 time series
http_requests_total{status="200", endpoint="/api/users"}
http_requests_total{status="404", endpoint="/api/users"}
http_requests_total{status="500", endpoint="/api/users"}
...
```

**Cardinality Explosion**:
```
# DANGER: 1 metric × 1M user_ids = 1M time series!
requests_total{user_id="user_123"}
```

**Best Practices**:
- Keep label cardinality < 100 unique values
- Avoid high-cardinality labels (user_id, trace_id, email)
- Use histograms to reduce cardinality (bucket ranges instead of individual values)

### Prometheus vs StatsD

| Feature | Prometheus | StatsD |
|---------|-----------|--------|
| **Model** | Pull (scrape) | Push |
| **Storage** | Time-series DB | None (forwards to backend) |
| **Querying** | PromQL | Depends on backend |
| **Aggregation** | Server-side | Client or server |
| **Use Case** | Modern cloud-native | Legacy systems, high-throughput |

---

## Patterns

### Pattern 1: Prometheus Metrics (Python)

```python
from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client import start_http_server
import time
from functools import wraps

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

active_requests = Gauge(
    'http_active_requests',
    'Number of active HTTP requests'
)

database_connection_pool = Gauge(
    'database_connection_pool_size',
    'Database connection pool size',
    ['state']  # active, idle
)

# Decorator for automatic instrumentation
def track_request(endpoint: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            method = "GET"  # Extract from request context

            active_requests.inc()

            with http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).time():
                try:
                    result = func(*args, **kwargs)
                    status = "200"
                    return result
                except Exception as e:
                    status = "500"
                    raise
                finally:
                    http_requests_total.labels(
                        method=method,
                        endpoint=endpoint,
                        status=status
                    ).inc()
                    active_requests.dec()

        return wrapper
    return decorator

# Usage
@track_request("/api/users")
def get_users():
    time.sleep(0.1)  # Simulate work
    return {"users": []}

# Update gauges periodically
def update_connection_pool_metrics(pool):
    database_connection_pool.labels(state="active").set(pool.active_count())
    database_connection_pool.labels(state="idle").set(pool.idle_count())

# Expose metrics endpoint
if __name__ == "__main__":
    start_http_server(8000)  # Metrics at http://localhost:8000/metrics

    while True:
        get_users()
        time.sleep(1)
```

### Pattern 2: Prometheus Metrics (Go)

```go
package metrics

import (
    "net/http"
    "time"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
    httpRequestsTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "http_requests_total",
            Help: "Total HTTP requests",
        },
        []string{"method", "endpoint", "status"},
    )

    httpRequestDuration = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "http_request_duration_seconds",
            Help:    "HTTP request latency",
            Buckets: prometheus.DefBuckets, // Default: 0.005 to 10s
        },
        []string{"method", "endpoint"},
    )

    activeRequests = promauto.NewGauge(
        prometheus.GaugeOpts{
            Name: "http_active_requests",
            Help: "Number of active HTTP requests",
        },
    )
)

// Middleware for automatic instrumentation
func MetricsMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()

        activeRequests.Inc()
        defer activeRequests.Dec()

        // Wrap ResponseWriter to capture status
        ww := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}

        next.ServeHTTP(ww, r)

        duration := time.Since(start).Seconds()

        httpRequestsTotal.WithLabelValues(
            r.Method,
            r.URL.Path,
            http.StatusText(ww.statusCode),
        ).Inc()

        httpRequestDuration.WithLabelValues(
            r.Method,
            r.URL.Path,
        ).Observe(duration)
    })
}

type responseWriter struct {
    http.ResponseWriter
    statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
    rw.statusCode = code
    rw.ResponseWriter.WriteHeader(code)
}

// Expose metrics endpoint
func StartMetricsServer(port string) {
    http.Handle("/metrics", promhttp.Handler())
    go http.ListenAndServe(":"+port, nil)
}
```

### Pattern 3: Custom Business Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Business metrics
orders_total = Counter(
    'orders_total',
    'Total orders placed',
    ['product_category', 'payment_method']
)

order_value_dollars = Histogram(
    'order_value_dollars',
    'Order value in dollars',
    buckets=[10, 25, 50, 100, 250, 500, 1000, 5000]
)

revenue_total_dollars = Counter(
    'revenue_total_dollars',
    'Total revenue in dollars',
    ['product_category']
)

cart_abandonment_total = Counter(
    'cart_abandonment_total',
    'Total cart abandonments',
    ['abandonment_stage']  # product_view, cart, checkout
)

active_subscriptions = Gauge(
    'active_subscriptions',
    'Number of active subscriptions',
    ['plan_tier']  # free, pro, enterprise
)

# Usage in business logic
def place_order(order):
    orders_total.labels(
        product_category=order.category,
        payment_method=order.payment_method
    ).inc()

    order_value_dollars.observe(order.total_amount)

    revenue_total_dollars.labels(
        product_category=order.category
    ).inc(order.total_amount)

def track_cart_abandonment(stage: str):
    cart_abandonment_total.labels(abandonment_stage=stage).inc()

def update_subscription_metrics(db):
    for tier in ['free', 'pro', 'enterprise']:
        count = db.query(Subscription).filter_by(
            tier=tier,
            status='active'
        ).count()
        active_subscriptions.labels(plan_tier=tier).set(count)
```

### Pattern 4: StatsD Metrics (Python)

```python
from statsd import StatsClient
from functools import wraps
import time

statsd = StatsClient(host='localhost', port=8125, prefix='myapp')

def track_timing(metric_name: str):
    """Decorator to track execution time."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration_ms = (time.time() - start) * 1000
                statsd.timing(metric_name, duration_ms)
        return wrapper
    return decorator

# Usage
@track_timing('api.users.get')
def get_user(user_id: str):
    # Increment counter
    statsd.incr('api.users.requests')

    try:
        user = db.get_user(user_id)
        statsd.incr('api.users.success')
        return user
    except Exception as e:
        statsd.incr('api.users.errors')
        raise

# Gauge (snapshot value)
def update_queue_size():
    queue_size = redis.llen('task_queue')
    statsd.gauge('queue.size', queue_size)

# Set (count unique values)
def track_unique_users(user_id: str):
    statsd.set('users.active', user_id)
```

### Pattern 5: Histogram Percentiles (PromQL)

```promql
# 95th percentile latency
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket[5m])
)

# 99th percentile by endpoint
histogram_quantile(0.99,
  sum by (endpoint, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)

# Request rate (requests per second)
rate(http_requests_total[5m])

# Error rate (percentage)
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
* 100

# Average request duration
rate(http_request_duration_seconds_sum[5m])
/
rate(http_request_duration_seconds_count[5m])
```

### Pattern 6: Multi-Dimensional Metrics

```python
from prometheus_client import Counter

# Good: Bounded labels
api_requests = Counter(
    'api_requests_total',
    'API requests',
    ['method', 'endpoint', 'status', 'region']
)

# Method: 4 values (GET, POST, PUT, DELETE)
# Endpoint: ~20 values
# Status: 5 values (2xx, 3xx, 4xx, 5xx)
# Region: 3 values (us-east, us-west, eu-west)
# Total cardinality: 4 × 20 × 5 × 3 = 1,200 time series

api_requests.labels(
    method="GET",
    endpoint="/api/users",
    status="200",
    region="us-east"
).inc()

# Query: Filter by dimension
# sum by (endpoint) (rate(api_requests_total[5m]))
```

---

## Quick Reference

### Prometheus Client Libraries

```bash
# Python
pip install prometheus-client

# Go
go get github.com/prometheus/client_golang/prometheus

# Rust
cargo add prometheus

# Node.js
npm install prom-client
```

### StatsD Client Libraries

```bash
# Python
pip install statsd

# Node.js
npm install node-statsd

# Go
go get github.com/cactus/go-statsd-client/statsd
```

### Metric Naming Conventions

```
# Pattern: <namespace>_<subsystem>_<name>_<unit>

# Good examples
http_requests_total
http_request_duration_seconds
database_connections_active
queue_messages_processed_total
memory_usage_bytes

# Bad examples
RequestCount          # Use snake_case
http_latency          # Missing unit
TotalErrors           # Use snake_case, add context
```

### PromQL Quick Reference

```promql
# Rate (per-second average over time window)
rate(metric[5m])

# Increase (total increase over time window)
increase(metric[1h])

# Sum (aggregate across labels)
sum(metric) by (label)

# Average
avg(metric) by (label)

# Max/Min
max(metric) by (label)
min(metric) by (label)

# Histogram quantile (percentile)
histogram_quantile(0.95, rate(metric_bucket[5m]))

# Arithmetic
metric1 / metric2 * 100  # Percentage
```

### Histogram Bucket Guidelines

```python
# Latency (seconds)
buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]

# Request size (bytes)
buckets=[100, 1000, 10_000, 100_000, 1_000_000, 10_000_000]

# Duration (milliseconds)
buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000]

# Custom business metric (dollars)
buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000]
```

---

## Anti-Patterns

### ❌ High-Cardinality Labels

```python
# WRONG: User ID has millions of unique values
requests_total = Counter(
    'requests_total',
    'Total requests',
    ['user_id']  # 1M users = 1M time series!
)

# CORRECT: Use low-cardinality labels
requests_total = Counter(
    'requests_total',
    'Total requests',
    ['endpoint', 'status']  # ~100 time series
)
# Track user_id in logs or traces, not metrics
```

### ❌ Missing Units in Metric Names

```python
# WRONG: Ambiguous units
request_duration = Histogram('request_duration', 'Request duration')

# CORRECT: Explicit units
request_duration_seconds = Histogram(
    'request_duration_seconds',
    'Request duration in seconds'
)
```

### ❌ Using Gauge for Counters

```python
# WRONG: Gauge for monotonic value
requests_processed = Gauge('requests_processed', 'Requests processed')
requests_processed.inc()  # Resets on restart!

# CORRECT: Counter for monotonic value
requests_processed = Counter('requests_processed_total', 'Requests processed')
requests_processed.inc()  # Use rate() to get per-second rate
```

### ❌ Summary Instead of Histogram

```python
# WRONG: Summary (cannot aggregate across instances)
latency_summary = Summary(
    'latency_summary',
    'Request latency summary'
)

# CORRECT: Histogram (aggregates across instances)
latency_histogram = Histogram(
    'latency_seconds',
    'Request latency histogram',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)
```

### ❌ Too Many Labels

```python
# WRONG: 6 labels = cardinality explosion
metric = Counter(
    'api_requests',
    'API requests',
    ['method', 'endpoint', 'status', 'region', 'customer', 'version']
)

# CORRECT: 3-4 essential labels
metric = Counter(
    'api_requests',
    'API requests',
    ['method', 'endpoint', 'status']
)
```

### ❌ Inconsistent Label Names

```python
# WRONG: Inconsistent naming
metric1 = Counter('requests', 'Requests', ['http_method'])
metric2 = Counter('errors', 'Errors', ['method'])

# CORRECT: Consistent naming
metric1 = Counter('requests_total', 'Requests', ['method'])
metric2 = Counter('errors_total', 'Errors', ['method'])
```

---

## Level 3: Resources

This skill has **Level 3 Resources** available with comprehensive reference material, production-ready scripts, and runnable examples.

### Resource Structure

```
metrics-instrumentation/resources/
├── REFERENCE.md                    # Comprehensive reference (1,985 lines)
│   ├── Metric types deep-dive (Counter, Gauge, Histogram, Summary)
│   ├── Metric naming and label best practices
│   ├── Cardinality management strategies
│   ├── PromQL query language reference
│   ├── Recording rules and alerting rules
│   ├── Instrumentation patterns (Python, Go, Node.js, Rust)
│   ├── Exporters (node_exporter, blackbox, custom)
│   ├── Service discovery configurations
│   ├── Storage, retention, and federation
│   ├── Grafana integration
│   ├── Performance optimization techniques
│   ├── Production best practices
│   └── Troubleshooting guide
│
├── scripts/                        # Production-ready analysis tools
│   ├── analyze_metrics.py          # Cardinality analyzer
│   ├── validate_promql.py          # PromQL query validator
│   └── test_exporter.sh            # Exporter testing tool
│
└── examples/                       # Runnable examples
    ├── python/
    │   ├── flask_metrics.py        # Instrumented Flask app
    │   ├── requirements.txt
    │   └── Dockerfile
    ├── go/
    │   ├── http_metrics.go         # Instrumented Go HTTP server
    │   └── go.mod
    ├── typescript/
    │   ├── express_metrics.ts      # Instrumented Express app
    │   ├── package.json
    │   └── tsconfig.json
    ├── prometheus/
    │   ├── prometheus.yml          # Comprehensive config
    │   ├── rules.yml               # Recording rules
    │   └── alerts.yml              # Alerting rules
    ├── grafana/
    │   └── dashboards/
    │       └── http-metrics.json   # Sample dashboard
    └── docker/
        ├── docker-compose.yml      # Full stack (Prometheus + Grafana)
        └── README.md
```

### Key Resources

**REFERENCE.md** (1,985 lines): Comprehensive guide covering:
- Prometheus architecture and data model
- All metric types with detailed examples
- Metric naming conventions and label best practices
- Cardinality explosion detection and prevention
- Complete PromQL reference with 50+ query examples
- Recording rules for performance optimization
- Alerting rules with severity levels
- Instrumentation patterns for 4 languages
- Official and custom exporters
- Service discovery for Kubernetes, Consul, EC2
- Storage configuration and remote write
- Grafana dashboard design
- Performance tuning and troubleshooting

**analyze_metrics.py**: Production-ready cardinality analyzer
- Connects to Prometheus or analyzes metrics files
- Detects high-cardinality labels
- Identifies naming convention violations
- Provides optimization recommendations
- Outputs human-readable or JSON format
- Example: `analyze_metrics.py --url http://localhost:9090 --json`

**validate_promql.py**: PromQL query validator
- Validates syntax and best practices
- Checks for common anti-patterns
- Tests queries against live Prometheus
- Measures execution time and result size
- Example: `validate_promql.py --query 'rate(http_requests_total[5m])' --url http://localhost:9090`

**test_exporter.sh**: Exporter testing tool
- Tests metrics endpoints for correctness
- Validates Prometheus text format
- Checks HELP and TYPE annotations
- Detects naming convention issues
- Identifies potential cardinality problems
- Example: `test_exporter.sh --url http://localhost:8080/metrics`

**Runnable Examples**:
- Flask, Go, and Express applications with full instrumentation
- Complete Prometheus configuration with service discovery
- Recording rules and alerting rules
- Grafana dashboard JSON
- Docker Compose stack for quick deployment

### Usage

```bash
# Access comprehensive reference
cat metrics-instrumentation/resources/REFERENCE.md

# Analyze metrics from Prometheus
./scripts/analyze_metrics.py --url http://localhost:9090

# Validate PromQL queries
./scripts/validate_promql.py --query 'sum(rate(http_requests_total[5m]))'

# Test metrics endpoint
./scripts/test_exporter.sh --url http://localhost:8080/metrics

# Run example Flask app
cd examples/python
pip install -r requirements.txt
python flask_metrics.py
# Metrics at http://localhost:8080/metrics

# Run full stack with Docker
cd examples/docker
docker-compose up -d
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

### When to Use Level 3 Resources

Use these resources when:
- Designing metrics architecture for new services
- Debugging cardinality or performance issues
- Learning PromQL query patterns
- Setting up recording rules and alerts
- Instrumenting applications in Python, Go, or Node.js
- Configuring Prometheus for production
- Building Grafana dashboards
- Training team members on metrics best practices

---

## Related Skills

- **structured-logging.md** - Complementary log-based observability
- **distributed-tracing.md** - Deep request flow analysis
- **dashboard-design.md** - Visualizing metrics in Grafana
- **alerting-strategy.md** - Alert rules based on metrics

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
**Level 3 Resources**: Available
