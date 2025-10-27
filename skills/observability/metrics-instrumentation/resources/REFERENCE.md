# Prometheus Metrics Reference

Comprehensive reference for Prometheus metrics, metric types, instrumentation patterns, PromQL, recording rules, alerting, exporters, and production deployment strategies.

## Table of Contents

1. [Fundamentals](#fundamentals)
2. [Metric Types](#metric-types)
3. [Metric Naming and Labels](#metric-naming-and-labels)
4. [Cardinality Management](#cardinality-management)
5. [PromQL Query Language](#promql-query-language)
6. [Recording Rules](#recording-rules)
7. [Alerting Rules](#alerting-rules)
8. [Instrumentation Patterns](#instrumentation-patterns)
9. [Exporters](#exporters)
10. [Service Discovery](#service-discovery)
11. [Storage and Retention](#storage-and-retention)
12. [Federation and Remote Write](#federation-and-remote-write)
13. [Grafana Integration](#grafana-integration)
14. [Performance Optimization](#performance-optimization)
15. [Production Best Practices](#production-best-practices)
16. [Common Anti-Patterns](#common-anti-patterns)
17. [Troubleshooting Guide](#troubleshooting-guide)

---

## Fundamentals

### What is Prometheus?

Prometheus is an open-source monitoring and alerting toolkit designed for reliability and scalability. It features:

- **Pull-based model**: Prometheus scrapes metrics from targets
- **Time-series database**: Stores metrics with timestamps
- **PromQL**: Powerful query language for analysis
- **Multi-dimensional data**: Labels for flexible querying
- **No distributed storage**: Single server simplicity
- **Service discovery**: Dynamic target discovery
- **Built-in alerting**: AlertManager integration

### Architecture

```
┌─────────────┐
│  Exporters  │ (expose metrics at /metrics)
└──────┬──────┘
       │ HTTP GET (scrape)
       ↓
┌─────────────────┐
│   Prometheus    │
│   Server        │
│  - TSDB         │
│  - Rules Engine │
│  - PromQL       │
└────┬────────┬───┘
     │        │
     │        └──→ AlertManager (alerts)
     ↓
  Grafana (visualization)
```

### Data Model

Prometheus stores all data as time series identified by:
- **Metric name**: The measurement (e.g., `http_requests_total`)
- **Labels**: Key-value pairs for dimensions
- **Timestamp**: When the sample was recorded
- **Value**: 64-bit float

**Example**:
```
http_requests_total{method="GET", endpoint="/api/users", status="200"} 1234 @ 1609459200
                   │                                                    │    │
                   └─ Labels                                            │    └─ Timestamp
                                                                        └─ Value
```

### Time Series

A time series is a unique combination of metric name and label set:

```
# These are 3 different time series:
http_requests_total{method="GET", endpoint="/api/users"}
http_requests_total{method="POST", endpoint="/api/users"}
http_requests_total{method="GET", endpoint="/api/orders"}
```

**Cardinality** = Number of unique time series

---

## Metric Types

Prometheus defines four core metric types. Understanding when to use each is critical for correct instrumentation.

### Counter

A counter is a cumulative metric that only increases (or resets to zero on restart).

**Characteristics**:
- Monotonically increasing
- Resets to 0 on process restart
- Cannot decrease

**Use Cases**:
- Total requests processed
- Total errors encountered
- Total bytes sent/received
- Total events published
- Total database queries

**Naming Convention**: Use `_total` suffix

**Example**:
```python
from prometheus_client import Counter

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Increment
http_requests_total.labels(
    method='GET',
    endpoint='/api/users',
    status='200'
).inc()

# Increment by amount
bytes_sent_total.labels(protocol='http').inc(1024)
```

**PromQL Usage**:
```promql
# Rate (requests per second over 5 minutes)
rate(http_requests_total[5m])

# Total increase in last hour
increase(http_requests_total[1h])

# Extrapolate to predict total over 24h
predict_linear(http_requests_total[1h], 24*3600)
```

**How It Works**:
- Application tracks cumulative count
- Prometheus scrapes current value periodically
- `rate()` calculates per-second average between samples
- Handles counter resets automatically

**Graph Behavior**:
```
Value
  │     ╱────────────────  (raw counter, always increasing)
  │   ╱
  │ ╱
  └─────────────────> Time

Rate
  │ ─────────────────────  (rate() shows steady state)
  │
  └─────────────────> Time
```

### Gauge

A gauge represents a value that can arbitrarily go up and down.

**Characteristics**:
- Can increase or decrease
- Represents current state
- Value is meaningful directly (no need for rate())

**Use Cases**:
- Current memory usage
- Active connections
- Queue size
- Temperature
- In-progress requests
- Available disk space
- Number of goroutines/threads

**Example**:
```python
from prometheus_client import Gauge

memory_usage_bytes = Gauge(
    'memory_usage_bytes',
    'Current memory usage in bytes'
)

# Set to specific value
memory_usage_bytes.set(1024 * 1024 * 512)  # 512 MB

# Increment/decrement
active_connections = Gauge('active_connections', 'Active connections')
active_connections.inc()    # +1
active_connections.dec()    # -1
active_connections.inc(5)   # +5

# Track in-progress with decorator
in_progress = Gauge('requests_in_progress', 'Requests in progress')

@in_progress.track_inprogress()
def process_request():
    # Gauge incremented on entry, decremented on exit
    pass

# Set to current time
last_success = Gauge('last_success_timestamp', 'Last successful run')
last_success.set_to_current_time()
```

**PromQL Usage**:
```promql
# Current value
memory_usage_bytes

# Average over time
avg_over_time(memory_usage_bytes[5m])

# Maximum in last hour
max_over_time(memory_usage_bytes[1h])

# Percentage of limit
(memory_usage_bytes / memory_limit_bytes) * 100
```

**When to Use Gauge vs Counter**:
```python
# WRONG: Using Gauge for monotonic value
errors_total = Gauge('errors_total', 'Total errors')
errors_total.inc()  # Resets on restart, can't use rate()

# CORRECT: Use Counter
errors_total = Counter('errors_total', 'Total errors')
errors_total.inc()  # Survives restarts via rate()
```

### Histogram

A histogram samples observations (usually request durations or response sizes) and counts them in configurable buckets. It provides:
- `_bucket{le="<upper bound>"}`: Cumulative counters for buckets
- `_sum`: Total sum of observed values
- `_count`: Total count of observations

**Characteristics**:
- Pre-defined buckets at instrumentation time
- Cumulative buckets (le = "less than or equal")
- Calculates percentiles server-side
- Aggregates across instances

**Use Cases**:
- Request latency
- Response sizes
- Processing times
- Query durations
- Batch sizes

**Example**:
```python
from prometheus_client import Histogram

# Default buckets: .005, .01, .025, .05, .075, .1, .25, .5, .75, 1, 2.5, 5, 7.5, 10, +Inf
request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Custom buckets for SLO (10ms, 50ms, 100ms, 500ms, 1s, 5s)
api_latency = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# Observe value
start = time.time()
# ... do work ...
duration = time.time() - start
request_duration_seconds.labels(method='GET', endpoint='/api/users').observe(duration)

# Context manager
with request_duration_seconds.labels(method='POST', endpoint='/api/orders').time():
    # ... do work ...
    pass
```

**Exposed Metrics**:
```
# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.01"} 50
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.05"} 145
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.1"} 180
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.5"} 195
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="1.0"} 198
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="+Inf"} 200
http_request_duration_seconds_sum{method="GET",endpoint="/api/users"} 12.5
http_request_duration_seconds_count{method="GET",endpoint="/api/users"} 200
```

**PromQL Usage**:
```promql
# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 99th percentile by endpoint
histogram_quantile(0.99,
  sum by (endpoint, le) (rate(http_request_duration_seconds_bucket[5m]))
)

# Average latency
rate(http_request_duration_seconds_sum[5m])
/
rate(http_request_duration_seconds_count[5m])

# Request rate
rate(http_request_duration_seconds_count[5m])

# Percentage of requests < 100ms (SLI)
sum(rate(http_request_duration_seconds_bucket{le="0.1"}[5m]))
/
sum(rate(http_request_duration_seconds_count[5m]))
* 100
```

**Bucket Selection**:
```python
# Latency (seconds) - exponential distribution
buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]

# Size (bytes) - powers of 10
buckets=[100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000]

# Duration (milliseconds) - linear for SLOs
buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000]

# Business metric (order value in dollars)
buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000]
```

### Summary

A summary is similar to a histogram but calculates quantiles on the client side. It provides:
- `{quantile="<φ>"}`: Pre-calculated quantiles (e.g., 0.5, 0.9, 0.99)
- `_sum`: Total sum of observed values
- `_count`: Total count of observations

**Characteristics**:
- Client-side quantile calculation
- Cannot aggregate across instances
- Configurable quantiles
- More accurate for single instance

**Use Cases**:
- Single-instance applications
- When exact quantiles needed
- Legacy systems (prefer histograms for new code)

**Example**:
```python
from prometheus_client import Summary

request_latency = Summary(
    'request_latency_seconds',
    'Request latency',
    ['endpoint']
)

# Observe
request_latency.labels(endpoint='/api/users').observe(0.25)

# Context manager
with request_latency.labels(endpoint='/api/orders').time():
    pass
```

**Exposed Metrics**:
```
request_latency_seconds{endpoint="/api/users",quantile="0.5"} 0.12
request_latency_seconds{endpoint="/api/users",quantile="0.9"} 0.35
request_latency_seconds{endpoint="/api/users",quantile="0.99"} 0.89
request_latency_seconds_sum{endpoint="/api/users"} 125.3
request_latency_seconds_count{endpoint="/api/users"} 1000
```

**Histogram vs Summary**:

| Feature | Histogram | Summary |
|---------|-----------|---------|
| Quantile calculation | Server-side | Client-side |
| Aggregation | Yes (across instances) | No |
| Accuracy | Approximate | Exact (for single instance) |
| Bucket definition | At instrumentation | At instrumentation |
| Query flexibility | High (any quantile) | Low (pre-defined only) |
| Resource usage | Lower | Higher (sliding window) |
| **Recommendation** | **Prefer for new code** | Legacy only |

**When to Use Each**:
```python
# Use Histogram (recommended)
# - Distributed systems
# - Need to aggregate across instances
# - Want flexible quantile queries
# - SLO/SLI monitoring
latency_histogram = Histogram(
    'request_duration_seconds',
    'Request duration',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# Use Summary (rare)
# - Single instance application
# - Need exact quantiles
# - Cannot predict bucket ranges
latency_summary = Summary('request_duration_seconds', 'Request duration')
```

---

## Metric Naming and Labels

Proper naming and labeling is critical for maintainability and query performance.

### Naming Conventions

**Pattern**: `<namespace>_<subsystem>_<name>_<unit>`

**Rules**:
1. Use `snake_case` (lowercase with underscores)
2. Include unit suffix for measurements
3. Use `_total` suffix for counters
4. Use descriptive names
5. Be consistent across codebase

**Valid Units**:
- Time: `_seconds`, `_milliseconds`
- Size: `_bytes`, `_megabytes`
- Percentage: `_ratio` (0-1), `_percent` (0-100)
- Count: `_total` (counter)

**Good Examples**:
```
http_requests_total
http_request_duration_seconds
database_queries_total
database_query_duration_seconds
memory_usage_bytes
cpu_usage_ratio
network_transmit_bytes_total
queue_messages_waiting
process_cpu_seconds_total
disk_io_operations_total
cache_hit_ratio
```

**Bad Examples**:
```
RequestCount              # Use snake_case
http_latency              # Missing unit
TotalErrors               # Use snake_case
request_time              # Which unit?
requests                  # Counter should have _total
db_connections_active     # Unclear if gauge or counter
```

### Labels

Labels add dimensions to metrics. They should be:
- **Low cardinality**: < 100 unique values ideally
- **Bounded**: Finite set of possible values
- **Meaningful**: Used for filtering/aggregating

**Good Label Examples**:
```python
http_requests_total{
    method="GET",           # ~7 values (GET, POST, PUT, DELETE, etc.)
    endpoint="/api/users",  # ~20-100 values (all endpoints)
    status="200",           # ~10 values (200, 201, 400, 404, 500, etc.)
    region="us-east-1"      # ~5-10 values (AWS regions)
}
```

**Label Naming**:
- Use `snake_case`
- Be consistent across metrics
- Common labels: `method`, `status`, `endpoint`, `service`, `env`, `region`, `cluster`

**Label Best Practices**:

```python
# GOOD: Bounded cardinality
requests_total = Counter(
    'requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']  # ~7 * 50 * 10 = 3,500 series
)

# BAD: Unbounded cardinality
requests_total = Counter(
    'requests_total',
    'Total requests',
    ['user_id', 'session_id']  # Millions of series!
)

# GOOD: Normalize paths
# /api/users/123 → /api/users/:id
endpoint = normalize_path(request.path)
requests_total.labels(endpoint=endpoint).inc()

# GOOD: Limit status codes to classes
status_class = f"{status // 100}xx"  # 200 → "2xx"
requests_total.labels(status=status_class).inc()
```

### Label Cardinality

**Cardinality Formula**: `unique_values(label1) × unique_values(label2) × ... × unique_values(labelN)`

**Example**:
```python
# 4 methods × 50 endpoints × 5 statuses × 3 regions = 3,000 time series
api_requests{method, endpoint, status, region}
```

**Cardinality Limits**:
- **Low**: < 100 series per metric (safe)
- **Medium**: 100-10,000 series (monitor)
- **High**: 10,000-100,000 series (optimize)
- **Critical**: > 100,000 series (fix immediately)

**Reducing Cardinality**:

```python
# Problem: Too many endpoints
# /api/users/123, /api/users/456, ... → thousands of series

# Solution 1: Normalize paths
def normalize_path(path):
    return re.sub(r'/\d+', '/:id', path)
# /api/users/123 → /api/users/:id

# Solution 2: Group by prefix
def get_endpoint_group(path):
    parts = path.split('/')
    return f"/{parts[1]}" if len(parts) > 1 else "/"
# /api/users/123 → /api

# Solution 3: Use histogram for high-cardinality dimension
# Instead of: latency{user_id="123"}
# Use: latency_by_user_type{user_type="premium"}
```

---

## Cardinality Management

Cardinality explosion is the #1 performance killer in Prometheus. Proper management is essential.

### Understanding Cardinality

Each unique combination of metric name and labels creates a new time series:

```
# 1 time series
http_requests_total{method="GET"}

# 2 time series
http_requests_total{method="GET"}
http_requests_total{method="POST"}

# 6 time series (2 methods × 3 statuses)
http_requests_total{method="GET", status="200"}
http_requests_total{method="GET", status="404"}
http_requests_total{method="GET", status="500"}
http_requests_total{method="POST", status="200"}
http_requests_total{method="POST", status="404"}
http_requests_total{method="POST", status="500"}
```

### Cardinality Explosion Scenarios

**Scenario 1: User/Request IDs**
```python
# WRONG: 1 million users = 1 million time series
requests_total{user_id="user_12345"}

# Impact: Memory = 1M series × 3KB = 3GB
```

**Scenario 2: Timestamps**
```python
# WRONG: Timestamp in label
cache_access{timestamp="2025-10-27T10:15:30Z"}

# Impact: New series every second
```

**Scenario 3: Unbounded Paths**
```python
# WRONG: /api/users/123, /api/users/456, ...
requests_total{endpoint="/api/users/123"}

# Impact: Series = number of users
```

**Scenario 4: IP Addresses**
```python
# WRONG: Millions of client IPs
requests_total{client_ip="192.168.1.100"}
```

### Detecting High Cardinality

**PromQL Queries**:

```promql
# Total active time series
prometheus_tsdb_head_series

# Series per metric
count by (__name__) ({__name__=~".+"})

# Series per label (expensive!)
count by (endpoint) (http_requests_total)

# Top metrics by series count
topk(10, count by (__name__) ({__name__=~".+"}))

# Cardinality growth rate
rate(prometheus_tsdb_head_series[5m]) * 86400  # Series added per day
```

**Prometheus UI** (`/metrics`):
```
prometheus_tsdb_head_series 1234567
prometheus_tsdb_symbol_table_size_bytes 12345678
```

**Cardinality Exporter**: Use `prometheus-cardinality-exporter` for analysis

### Solutions

**1. Remove High-Cardinality Labels**

```python
# WRONG
requests_total = Counter('requests_total', '', ['user_id', 'trace_id'])

# RIGHT: Use logs/traces for IDs
requests_total = Counter('requests_total', '', ['endpoint', 'status'])
logger.info('request', extra={'user_id': user_id, 'trace_id': trace_id})
```

**2. Normalize Paths**

```python
def normalize_path(path: str) -> str:
    """Normalize URL paths to reduce cardinality."""
    # /api/users/123 → /api/users/:id
    path = re.sub(r'/\d+', '/:id', path)

    # /api/users/abc-def-ghi → /api/users/:uuid
    path = re.sub(
        r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        '/:uuid',
        path
    )

    # /api/files/report.pdf → /api/files/:filename
    path = re.sub(r'\.(pdf|csv|xlsx|json)$', '.:ext', path)

    return path

requests_total.labels(endpoint=normalize_path(request.path)).inc()
```

**3. Group by Prefix**

```python
def get_api_prefix(path: str) -> str:
    """Extract API prefix: /api/v1/users → /api/v1"""
    parts = path.strip('/').split('/')
    return '/' + '/'.join(parts[:2]) if len(parts) >= 2 else '/'

requests_total.labels(api_prefix=get_api_prefix(path)).inc()
```

**4. Use Status Classes**

```python
# Instead of: 200, 201, 204, 301, 302, 400, 401, 403, 404, 500, 502, 503
# Use: 2xx, 3xx, 4xx, 5xx

status_class = f"{status_code // 100}xx"
requests_total.labels(status=status_class).inc()
```

**5. Sampling**

```python
import random

# Only record metric for 1% of requests
if random.random() < 0.01:
    expensive_metric.labels(user_tier=user.tier).inc()
```

**6. Aggregation**

```python
# Instead of per-user metrics
# Aggregate by user tier/segment

# WRONG: user_id has millions of values
active_users{user_id="123"}

# RIGHT: user_tier has 5 values
active_users{user_tier="premium"}
active_users{user_tier="free"}
```

**7. Relabeling**

Prometheus configuration to drop high-cardinality labels:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'my-app'
    metric_relabel_configs:
      # Drop user_id label
      - source_labels: [__name__]
        regex: 'requests_total'
        action: labeldrop
        regex: 'user_id'

      # Keep only specific endpoints
      - source_labels: [endpoint]
        regex: '/api/(users|orders|products)'
        action: keep
```

### Cardinality Budget

Establish limits per service:

```
Single metric: < 10,000 series
Per service: < 100,000 series
Entire system: < 1,000,000 series
```

**Monitoring**:
```yaml
# Alert on high cardinality
- alert: HighCardinality
  expr: prometheus_tsdb_head_series > 1000000
  for: 10m
  annotations:
    summary: "Prometheus has {{ $value }} series (> 1M)"
```

---

## PromQL Query Language

PromQL (Prometheus Query Language) is a functional query language for selecting and aggregating time series data.

### Basic Queries

**Instant Vector**: Set of time series with single sample per series

```promql
# All series for metric
http_requests_total

# Filter by label (exact match)
http_requests_total{method="GET"}

# Filter by label (regex)
http_requests_total{method=~"GET|POST"}

# Negative filter
http_requests_total{status!="200"}

# Negative regex
http_requests_total{status!~"2.."}

# Multiple labels
http_requests_total{method="GET", status="200"}
```

**Range Vector**: Set of time series with range of samples

```promql
# Last 5 minutes of samples
http_requests_total[5m]

# Last hour
http_requests_total[1h]

# Last day
http_requests_total[1d]
```

### Time Durations

```
ms - milliseconds
s  - seconds
m  - minutes
h  - hours
d  - days
w  - weeks
y  - years
```

### Operators

**Arithmetic**:
```promql
# Addition
node_memory_MemTotal_bytes + 1024

# Subtraction
node_memory_MemTotal_bytes - node_memory_MemFree_bytes

# Multiplication
rate(http_requests_total[5m]) * 60  # Convert to per-minute

# Division (percentage)
(node_memory_MemFree_bytes / node_memory_MemTotal_bytes) * 100

# Modulo
http_requests_total % 1000

# Power
http_requests_total ^ 2
```

**Comparison** (returns 1 or 0):
```promql
# Greater than
http_requests_total > 1000

# Less than
memory_usage_bytes < 1024*1024*1024  # < 1GB

# Greater or equal
cpu_usage_ratio >= 0.8

# Less or equal
error_rate <= 0.01

# Equal
http_requests_total{status="200"} == 100

# Not equal
http_requests_total != 0
```

**Logical**:
```promql
# AND
http_requests_total > 1000 and http_errors_total > 10

# OR
http_requests_total > 1000 or http_errors_total > 10

# UNLESS (subtract)
http_requests_total unless http_requests_total{status="200"}
```

### Functions

**Rate Functions** (for counters):

```promql
# rate(): Per-second average increase
rate(http_requests_total[5m])

# irate(): Instant rate (last 2 samples)
irate(http_requests_total[5m])

# increase(): Total increase over time range
increase(http_requests_total[1h])
```

**Aggregation Over Time**:

```promql
# Average over time window
avg_over_time(cpu_usage_ratio[5m])

# Maximum in time window
max_over_time(memory_usage_bytes[1h])

# Minimum
min_over_time(latency_seconds[5m])

# Sum
sum_over_time(errors_total[1h])

# Count (number of samples)
count_over_time(up[5m])

# Quantile over time
quantile_over_time(0.95, latency_seconds[5m])

# Standard deviation
stddev_over_time(latency_seconds[5m])
```

**Aggregation Operators**:

```promql
# Sum across all series
sum(http_requests_total)

# Sum by label (group by)
sum by (endpoint) (http_requests_total)

# Sum without label (remove dimension)
sum without (instance) (http_requests_total)

# Average
avg(memory_usage_bytes)
avg by (service) (memory_usage_bytes)

# Minimum
min(cpu_usage_ratio)

# Maximum
max(memory_usage_bytes)

# Count
count(up == 1)  # Number of healthy instances

# Standard deviation
stddev(latency_seconds)

# Quantile (percentile)
quantile(0.95, latency_seconds)

# Top K
topk(5, http_requests_total)

# Bottom K
bottomk(3, memory_usage_bytes)

# Count values
count_values("status", http_requests_total)
```

**Histogram Functions**:

```promql
# Quantile from histogram (percentile)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Quantile by endpoint
histogram_quantile(0.99,
  sum by (endpoint, le) (rate(http_request_duration_seconds_bucket[5m]))
)

# Average from histogram
rate(http_request_duration_seconds_sum[5m])
/
rate(http_request_duration_seconds_count[5m])
```

**Prediction Functions**:

```promql
# Predict value in 1 hour based on last 4 hours
predict_linear(disk_usage_bytes[4h], 3600)

# Derivative (rate of change)
deriv(disk_usage_bytes[5m])

# Delta (difference between first and last)
delta(cpu_seconds_total[1h])

# idelta (difference between last two samples)
idelta(cpu_seconds_total[5m])
```

**Math Functions**:

```promql
# Absolute value
abs(delta(temperature[5m]))

# Ceiling/floor/round
ceil(memory_usage_bytes / 1024)
floor(memory_usage_bytes / 1024)
round(memory_usage_bytes / 1024)

# Clamp (limit to range)
clamp(cpu_usage_ratio, 0, 1)
clamp_min(latency_seconds, 0)
clamp_max(error_rate, 1)

# Logarithm
ln(http_requests_total)
log2(http_requests_total)
log10(http_requests_total)

# Exponential
exp(value)

# Square root
sqrt(value)
```

**Time Functions**:

```promql
# Current timestamp
time()

# Day of week (0=Sunday)
day_of_week()

# Day of month
day_of_month()

# Hour of day
hour()

# Minute
minute()

# Month
month()

# Year
year()
```

**Label Functions**:

```promql
# Replace label value
label_replace(
  http_requests_total,
  "endpoint_normalized",  # New label
  "/api/:id",             # Replacement
  "endpoint",             # Source label
  "/api/.*"               # Regex
)

# Join labels
label_join(
  http_requests_total,
  "service_method",  # New label
  ".",               # Separator
  "service",         # Source labels...
  "method"
)
```

**Sorting**:

```promql
# Sort ascending
sort(http_requests_total)

# Sort descending
sort_desc(http_requests_total)
```

### Complex Queries

**Error Rate**:
```promql
# Percentage of 5xx errors
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
* 100
```

**SLI: Request Success Rate**:
```promql
# Percentage of successful requests (200-399)
sum(rate(http_requests_total{status=~"[23].."}[5m]))
/
sum(rate(http_requests_total[5m]))
* 100
```

**SLI: Latency**:
```promql
# 95% of requests complete within 200ms
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) < 0.2
```

**Saturation: Memory Usage**:
```promql
# Memory usage as percentage
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)
/
node_memory_MemTotal_bytes
* 100
```

**Availability**:
```promql
# Percentage uptime over 24h
avg_over_time(up[24h]) * 100
```

**Traffic: QPS**:
```promql
# Requests per second
sum(rate(http_requests_total[5m]))
```

**Multi-Service SLI**:
```promql
# Overall success rate across all services
sum by (service) (rate(http_requests_total{status=~"[23].."}[5m]))
/
sum by (service) (rate(http_requests_total[5m]))
```

### Subqueries

Execute a query over a time range:

```promql
# Maximum 5-minute rate in the last hour
max_over_time(rate(http_requests_total[5m])[1h:])

# 95th percentile of 5-minute rates over 24 hours
quantile_over_time(0.95, rate(http_requests_total[5m])[24h:])
```

### Offset

Query past data:

```promql
# Current rate
rate(http_requests_total[5m])

# Rate 1 hour ago
rate(http_requests_total[5m] offset 1h)

# Compare current to 1 day ago
rate(http_requests_total[5m])
/
rate(http_requests_total[5m] offset 1d)
```

---

## Recording Rules

Recording rules pre-compute expensive queries and store results as new time series. This improves query performance and reduces load.

### When to Use Recording Rules

Use recording rules for:
- Expensive aggregations queried frequently
- Dashboard queries taking > 1 second
- Alerting rules (to speed up evaluation)
- Complex SLI calculations
- Downsampling high-resolution metrics

### Syntax

```yaml
groups:
  - name: example_rules
    interval: 30s  # Evaluation interval (default: global.evaluation_interval)
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(http_requests_total[5m]))
        labels:
          team: backend
```

### Naming Convention

**Pattern**: `level:metric:operations`

- **level**: Aggregation level (job, instance, service)
- **metric**: Base metric name
- **operations**: Operations applied (rate5m, sum, avg)

**Examples**:
```
job:http_requests:rate5m
instance:cpu_usage:avg
service:error_rate:ratio
cluster:memory_usage:sum
```

### Examples

**1. Request Rate by Service**:
```yaml
groups:
  - name: request_rates
    interval: 30s
    rules:
      # Total request rate per service
      - record: service:http_requests:rate5m
        expr: sum by (service) (rate(http_requests_total[5m]))

      # Request rate per endpoint per service
      - record: service:http_requests_by_endpoint:rate5m
        expr: sum by (service, endpoint) (rate(http_requests_total[5m]))
```

**2. Error Rates**:
```yaml
groups:
  - name: error_rates
    rules:
      # Error rate by service (percentage)
      - record: service:http_errors:rate5m
        expr: |
          sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum by (service) (rate(http_requests_total[5m]))
          * 100

      # Success rate (SLI)
      - record: service:http_success:ratio
        expr: |
          sum by (service) (rate(http_requests_total{status=~"[23].."}[5m]))
          /
          sum by (service) (rate(http_requests_total[5m]))
```

**3. Latency Percentiles**:
```yaml
groups:
  - name: latency_percentiles
    rules:
      # 50th percentile
      - record: service:http_latency:p50
        expr: |
          histogram_quantile(0.5,
            sum by (service, le) (rate(http_request_duration_seconds_bucket[5m]))
          )

      # 95th percentile
      - record: service:http_latency:p95
        expr: |
          histogram_quantile(0.95,
            sum by (service, le) (rate(http_request_duration_seconds_bucket[5m]))
          )

      # 99th percentile
      - record: service:http_latency:p99
        expr: |
          histogram_quantile(0.99,
            sum by (service, le) (rate(http_request_duration_seconds_bucket[5m]))
          )
```

**4. Resource Utilization**:
```yaml
groups:
  - name: resource_utilization
    rules:
      # CPU usage by instance
      - record: instance:cpu_usage:ratio
        expr: |
          1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))

      # Memory usage percentage
      - record: instance:memory_usage:ratio
        expr: |
          (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)
          /
          node_memory_MemTotal_bytes

      # Disk usage percentage
      - record: instance:disk_usage:ratio
        expr: |
          (node_filesystem_size_bytes - node_filesystem_avail_bytes)
          /
          node_filesystem_size_bytes
```

**5. SLI/SLO Calculations**:
```yaml
groups:
  - name: sli_slo
    interval: 1m
    rules:
      # Availability SLI (target: 99.9%)
      - record: service:availability:sli
        expr: avg_over_time(up[5m])

      # Latency SLI (target: 95% < 200ms)
      - record: service:latency:sli
        expr: |
          histogram_quantile(0.95,
            sum by (service, le) (rate(http_request_duration_seconds_bucket[5m]))
          ) < 0.2

      # Error budget (30 days)
      - record: service:error_budget:ratio
        expr: |
          1 - (
            (1 - 0.999)  # Target: 99.9%
            -
            (1 - avg_over_time(service:availability:sli[30d]))
          ) / (1 - 0.999)
```

**6. Aggregation Across Labels**:
```yaml
groups:
  - name: aggregations
    rules:
      # Total traffic across all endpoints
      - record: service:http_requests_total:rate5m
        expr: sum by (service) (service:http_requests_by_endpoint:rate5m)

      # Average latency (from histogram)
      - record: service:http_latency:avg
        expr: |
          sum by (service) (rate(http_request_duration_seconds_sum[5m]))
          /
          sum by (service) (rate(http_request_duration_seconds_count[5m]))
```

### Configuration

**prometheus.yml**:
```yaml
global:
  evaluation_interval: 15s  # Default for all rules

rule_files:
  - /etc/prometheus/rules/*.yml
  - /etc/prometheus/alerts/*.yml
```

**rules/request_metrics.yml**:
```yaml
groups:
  - name: request_metrics
    interval: 30s
    rules:
      - record: service:http_requests:rate5m
        expr: sum by (service) (rate(http_requests_total[5m]))
```

### Testing Recording Rules

```bash
# Validate rules syntax
promtool check rules rules/request_metrics.yml

# Test rule query
promtool query instant http://localhost:9090 \
  'sum by (service) (rate(http_requests_total[5m]))'
```

### Best Practices

1. **Name consistently**: Use `level:metric:operations` pattern
2. **Document purpose**: Add comments explaining why rule exists
3. **Avoid recursion**: Don't create recording rules that depend on other recording rules (except for simple aggregations)
4. **Set appropriate intervals**: Match to query frequency (30s-1m typical)
5. **Monitor rule evaluation time**: Use `prometheus_rule_evaluation_duration_seconds`
6. **Keep rules simple**: Complex logic belongs in applications, not recording rules
7. **Version control**: Store rules in Git
8. **Test before deploying**: Use `promtool` to validate

---

## Alerting Rules

Alerting rules define conditions that trigger alerts, which are sent to AlertManager for routing and notification.

### Syntax

```yaml
groups:
  - name: example_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum by (service) (rate(http_requests_total[5m]))
          > 0.05
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High error rate on {{ $labels.service }}"
          description: "{{ $labels.service }} has {{ $value | humanizePercentage }} error rate"
```

**Fields**:
- `alert`: Alert name (PascalCase)
- `expr`: PromQL expression (triggers when true)
- `for`: Duration before firing (prevents flapping)
- `labels`: Additional labels for routing
- `annotations`: Human-readable descriptions

### Common Alert Patterns

**1. High Error Rate**:
```yaml
- alert: HighErrorRate
  expr: |
    sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
    /
    sum by (service) (rate(http_requests_total[5m]))
    > 0.05  # 5% error rate
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High error rate on {{ $labels.service }}"
    description: "Error rate is {{ $value | humanizePercentage }}"
```

**2. High Latency**:
```yaml
- alert: HighLatency
  expr: |
    histogram_quantile(0.95,
      sum by (service, le) (rate(http_request_duration_seconds_bucket[5m]))
    ) > 1.0  # p95 > 1 second
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High latency on {{ $labels.service }}"
    description: "p95 latency is {{ $value }}s"
```

**3. Service Down**:
```yaml
- alert: ServiceDown
  expr: up == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Service {{ $labels.job }} is down"
    description: "Instance {{ $labels.instance }} has been down for > 1 minute"
```

**4. High CPU Usage**:
```yaml
- alert: HighCPU
  expr: instance:cpu_usage:ratio > 0.8
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High CPU on {{ $labels.instance }}"
    description: "CPU usage is {{ $value | humanizePercentage }}"
```

**5. High Memory Usage**:
```yaml
- alert: HighMemory
  expr: instance:memory_usage:ratio > 0.9
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High memory on {{ $labels.instance }}"
    description: "Memory usage is {{ $value | humanizePercentage }}"
```

**6. Disk Space Low**:
```yaml
- alert: DiskSpaceLow
  expr: |
    (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Low disk space on {{ $labels.instance }}"
    description: "Only {{ $value | humanizePercentage }} remaining on {{ $labels.mountpoint }}"
```

**7. SLO Violation**:
```yaml
- alert: SLOViolation
  expr: service:availability:sli < 0.999  # 99.9% target
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "SLO violation on {{ $labels.service }}"
    description: "Availability is {{ $value | humanizePercentage }} (target: 99.9%)"
```

**8. Error Budget Exhaustion**:
```yaml
- alert: ErrorBudgetExhausted
  expr: service:error_budget:ratio <= 0
  for: 15m
  labels:
    severity: critical
  annotations:
    summary: "Error budget exhausted for {{ $labels.service }}"
    description: "Stop deploying! Error budget ratio: {{ $value }}"
```

### Annotation Templates

**Template Variables**:
- `{{ $labels.labelname }}`: Label value
- `{{ $value }}`: Alert expression value
- `{{ $externalLabels }}`: External labels from Prometheus config

**Template Functions**:
```yaml
annotations:
  # Humanize numbers
  description: "{{ $value | humanize }}"           # 1234567 → "1.234567M"
  description: "{{ $value | humanize1024 }}"       # 1234567 → "1.177856Mi"
  description: "{{ $value | humanizePercentage }}" # 0.1234 → "12.34%"
  description: "{{ $value | humanizeDuration }}"   # 12345 → "3h25m45s"
  description: "{{ $value | humanizeTimestamp }}"  # 1609459200 → "2021-01-01 00:00:00"
```

### Severity Levels

```yaml
labels:
  severity: critical  # Page on-call engineer
  severity: warning   # Notify team channel
  severity: info      # Log for reference
```

### Multi-Window Alerts

Detect sustained issues vs temporary spikes:

```yaml
- alert: SustainedHighLatency
  expr: |
    histogram_quantile(0.95,
      sum by (service, le) (rate(http_request_duration_seconds_bucket[5m]))
    ) > 1.0
    and
    histogram_quantile(0.95,
      sum by (service, le) (rate(http_request_duration_seconds_bucket[30m]))
    ) > 1.0
  for: 5m
  annotations:
    description: "Latency high for both 5m and 30m windows"
```

### Alert Dependencies

```yaml
# Alert only if service is up
- alert: HighLatency
  expr: |
    (histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0)
    and
    (up == 1)
  for: 5m
```

### Testing Alerts

```bash
# Validate alert rules
promtool check rules alerts/http_alerts.yml

# Test alert expression
promtool query instant http://localhost:9090 \
  'sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05'

# Unit test alerts (since Prometheus 2.25)
promtool test rules alerts/test.yml
```

**alerts/test.yml**:
```yaml
rule_files:
  - http_alerts.yml

evaluation_interval: 1m

tests:
  - interval: 1m
    input_series:
      - series: 'http_requests_total{status="500"}'
        values: '0+10x10'  # 0, 10, 20, ..., 100
      - series: 'http_requests_total{status="200"}'
        values: '0+100x10'

    alert_rule_test:
      - eval_time: 5m
        alertname: HighErrorRate
        exp_alerts:
          - exp_labels:
              severity: warning
            exp_annotations:
              summary: "High error rate on service"
```

---

## Instrumentation Patterns

### Python (prometheus_client)

**Installation**:
```bash
pip install prometheus-client
```

**Basic Instrumentation**:
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Define metrics
requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests in progress'
)

# Instrument
@in_progress.track_inprogress()
def handle_request(method, endpoint):
    with request_duration.labels(method=method, endpoint=endpoint).time():
        # Process request
        time.sleep(0.1)
        status = "200"

    requests_total.labels(method=method, endpoint=endpoint, status=status).inc()

# Start metrics server
start_http_server(8000)

while True:
    handle_request("GET", "/api/users")
    time.sleep(1)
```

**Flask Integration**:
```python
from flask import Flask, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

requests_total = Counter(
    'flask_requests_total',
    'Total Flask requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'flask_request_duration_seconds',
    'Flask request duration',
    ['method', 'endpoint']
)

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - request.start_time

    request_duration.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown'
    ).observe(duration)

    requests_total.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown',
        status=response.status_code
    ).inc()

    return response

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/api/users')
def get_users():
    return {"users": []}
```

### Go (client_golang)

**Installation**:
```bash
go get github.com/prometheus/client_golang/prometheus
go get github.com/prometheus/client_golang/prometheus/promhttp
```

**Basic Instrumentation**:
```go
package main

import (
    "net/http"
    "time"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
    requestsTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "http_requests_total",
            Help: "Total HTTP requests",
        },
        []string{"method", "endpoint", "status"},
    )

    requestDuration = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "http_request_duration_seconds",
            Help:    "HTTP request duration",
            Buckets: []float64{0.01, 0.05, 0.1, 0.5, 1.0, 5.0},
        },
        []string{"method", "endpoint"},
    )

    inProgress = promauto.NewGauge(
        prometheus.GaugeOpts{
            Name: "http_requests_in_progress",
            Help: "HTTP requests in progress",
        },
    )
)

// Middleware
func metricsMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()

        inProgress.Inc()
        defer inProgress.Dec()

        // Wrap writer to capture status
        ww := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}

        next.ServeHTTP(ww, r)

        duration := time.Since(start).Seconds()

        requestsTotal.WithLabelValues(
            r.Method,
            r.URL.Path,
            http.StatusText(ww.statusCode),
        ).Inc()

        requestDuration.WithLabelValues(
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

func main() {
    mux := http.NewServeMux()

    mux.HandleFunc("/api/users", func(w http.ResponseWriter, r *http.Request) {
        w.Write([]byte(`{"users": []}`))
    })

    mux.Handle("/metrics", promhttp.Handler())

    http.ListenAndServe(":8080", metricsMiddleware(mux))
}
```

### Node.js (prom-client)

**Installation**:
```bash
npm install prom-client
```

**Express Integration**:
```javascript
const express = require('express');
const client = require('prom-client');

const app = express();

// Create metrics
const requestsTotal = new client.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'endpoint', 'status']
});

const requestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request duration',
  labelNames: ['method', 'endpoint'],
  buckets: [0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
});

const inProgress = new client.Gauge({
  name: 'http_requests_in_progress',
  help: 'HTTP requests in progress'
});

// Middleware
app.use((req, res, next) => {
  const start = Date.now();

  inProgress.inc();

  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;

    requestDuration.labels(req.method, req.route?.path || req.path).observe(duration);
    requestsTotal.labels(req.method, req.route?.path || req.path, res.statusCode).inc();

    inProgress.dec();
  });

  next();
});

// Metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', client.register.contentType);
  res.end(await client.register.metrics());
});

// API endpoints
app.get('/api/users', (req, res) => {
  res.json({ users: [] });
});

app.listen(8080);
```

### Rust (prometheus crate)

**Cargo.toml**:
```toml
[dependencies]
prometheus = "0.13"
```

**Example**:
```rust
use prometheus::{Counter, Histogram, Gauge, Encoder, TextEncoder};
use std::time::Instant;

lazy_static! {
    static ref REQUESTS_TOTAL: Counter = Counter::new(
        "http_requests_total",
        "Total HTTP requests"
    ).unwrap();

    static ref REQUEST_DURATION: Histogram = Histogram::with_opts(
        histogram_opts!(
            "http_request_duration_seconds",
            "HTTP request duration",
            vec![0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
        )
    ).unwrap();

    static ref IN_PROGRESS: Gauge = Gauge::new(
        "http_requests_in_progress",
        "HTTP requests in progress"
    ).unwrap();
}

fn handle_request() {
    let _timer = REQUEST_DURATION.start_timer();
    IN_PROGRESS.inc();

    // Process request
    std::thread::sleep(std::time::Duration::from_millis(100));

    REQUESTS_TOTAL.inc();
    IN_PROGRESS.dec();
}

fn metrics_handler() -> String {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = vec![];
    encoder.encode(&metric_families, &mut buffer).unwrap();
    String::from_utf8(buffer).unwrap()
}
```

---

## Exporters

Exporters expose metrics from third-party systems in Prometheus format.

### Official Exporters

**node_exporter** - Hardware and OS metrics:
```bash
# Install
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
tar xvf node_exporter-1.6.1.linux-amd64.tar.gz
cd node_exporter-1.6.1.linux-amd64
./node_exporter

# Metrics at http://localhost:9100/metrics
```

**Metrics exposed**:
- CPU: `node_cpu_seconds_total`
- Memory: `node_memory_MemTotal_bytes`, `node_memory_MemAvailable_bytes`
- Disk: `node_disk_io_time_seconds_total`, `node_filesystem_size_bytes`
- Network: `node_network_receive_bytes_total`, `node_network_transmit_bytes_total`

**blackbox_exporter** - Black-box probing (HTTP, TCP, ICMP):
```bash
# Install
wget https://github.com/prometheus/blackbox_exporter/releases/download/v0.24.0/blackbox_exporter-0.24.0.linux-amd64.tar.gz
tar xvf blackbox_exporter-0.24.0.linux-amd64.tar.gz
cd blackbox_exporter-0.24.0.linux-amd64
./blackbox_exporter --config.file=blackbox.yml
```

**blackbox.yml**:
```yaml
modules:
  http_2xx:
    prober: http
    http:
      preferred_ip_protocol: ip4
      valid_status_codes: [200]

  tcp_connect:
    prober: tcp

  icmp:
    prober: icmp
```

**Prometheus config**:
```yaml
scrape_configs:
  - job_name: 'blackbox'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - https://example.com
        - https://api.example.com
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: localhost:9115
```

### Database Exporters

**postgres_exporter**:
```bash
docker run -e DATA_SOURCE_NAME="postgresql://user:pass@localhost:5432/db?sslmode=disable" \
  quay.io/prometheuscommunity/postgres-exporter
```

**redis_exporter**:
```bash
docker run -e REDIS_ADDR=redis://localhost:6379 \
  oliver006/redis_exporter
```

**mysql_exporter**:
```bash
docker run -e DATA_SOURCE_NAME="user:password@(localhost:3306)/" \
  prom/mysqld-exporter
```

### Custom Exporters

**Python Example**:
```python
from prometheus_client import start_http_server, Gauge
import time
import psutil

# Define metrics
cpu_usage = Gauge('system_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('system_memory_usage_bytes', 'Memory usage in bytes')
disk_usage = Gauge('system_disk_usage_percent', 'Disk usage percentage')

def collect_metrics():
    """Collect system metrics."""
    while True:
        cpu_usage.set(psutil.cpu_percent())
        memory_usage.set(psutil.virtual_memory().used)
        disk_usage.set(psutil.disk_usage('/').percent)
        time.sleep(15)

if __name__ == '__main__':
    start_http_server(9100)
    collect_metrics()
```

**Go Example**:
```go
package main

import (
    "net/http"
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
    "github.com/shirou/gopsutil/v3/cpu"
    "github.com/shirou/gopsutil/v3/mem"
)

var (
    cpuUsage = prometheus.NewGauge(prometheus.GaugeOpts{
        Name: "system_cpu_usage_percent",
        Help: "CPU usage percentage",
    })

    memUsage = prometheus.NewGauge(prometheus.GaugeOpts{
        Name: "system_memory_usage_bytes",
        Help: "Memory usage in bytes",
    })
)

func init() {
    prometheus.MustRegister(cpuUsage)
    prometheus.MustRegister(memUsage)
}

func collectMetrics() {
    for {
        cpuPercent, _ := cpu.Percent(0, false)
        cpuUsage.Set(cpuPercent[0])

        memInfo, _ := mem.VirtualMemory()
        memUsage.Set(float64(memInfo.Used))

        time.Sleep(15 * time.Second)
    }
}

func main() {
    go collectMetrics()
    http.Handle("/metrics", promhttp.Handler())
    http.ListenAndServe(":9100", nil)
}
```

---

## Service Discovery

Prometheus supports dynamic service discovery for cloud environments.

### Static Configuration

```yaml
scrape_configs:
  - job_name: 'my-app'
    static_configs:
      - targets:
        - 'localhost:8080'
        - 'app1.example.com:8080'
        - 'app2.example.com:8080'
        labels:
          env: production
```

### File-Based Discovery

**prometheus.yml**:
```yaml
scrape_configs:
  - job_name: 'file-sd'
    file_sd_configs:
      - files:
        - /etc/prometheus/targets/*.json
        refresh_interval: 30s
```

**/etc/prometheus/targets/app.json**:
```json
[
  {
    "targets": ["app1:8080", "app2:8080"],
    "labels": {
      "env": "production",
      "service": "api"
    }
  }
]
```

### Kubernetes Discovery

```yaml
scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      # Only scrape pods with annotation
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true

      # Use custom port from annotation
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: (.+)
        replacement: $1

      # Set job name from label
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: job
```

**Pod annotations**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
  labels:
    app: my-service
```

### Consul Discovery

```yaml
scrape_configs:
  - job_name: 'consul'
    consul_sd_configs:
      - server: 'localhost:8500'
        services: ['api', 'web']
```

### EC2 Discovery

```yaml
scrape_configs:
  - job_name: 'ec2'
    ec2_sd_configs:
      - region: us-east-1
        port: 9100
        filters:
          - name: tag:Environment
            values: [production]
```

---

## Storage and Retention

### Local Storage

Prometheus uses a local time-series database (TSDB).

**Configuration**:
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

storage:
  tsdb:
    path: /prometheus/data
    retention.time: 15d
    retention.size: 50GB
```

**CLI Flags**:
```bash
prometheus \
  --storage.tsdb.path=/prometheus/data \
  --storage.tsdb.retention.time=30d \
  --storage.tsdb.retention.size=100GB
```

**Disk Usage**:
- ~1-2 bytes per sample on disk (compressed)
- Formula: `samples/sec × retention_seconds × bytes_per_sample`
- Example: 1M series × 15s scrape = 66K samples/sec
  - 30 days: 66K × 2592000 × 2 bytes = ~343 GB

### Compaction

Prometheus automatically compacts data blocks:
- 2-hour blocks initially
- Compacted into longer blocks over time
- Reduces disk usage and improves query performance

### Remote Write

Send metrics to long-term storage:

```yaml
remote_write:
  - url: https://prometheus.example.com/api/v1/write
    queue_config:
      capacity: 10000
      max_shards: 50
      min_shards: 1
      max_samples_per_send: 5000
      batch_send_deadline: 5s
    write_relabel_configs:
      # Only send important metrics
      - source_labels: [__name__]
        regex: '(http_requests_total|http_request_duration_seconds.*)'
        action: keep
```

**Compatible Backends**:
- Thanos
- Cortex
- M3DB
- VictoriaMetrics
- Google Cloud Monitoring
- AWS Managed Prometheus
- Grafana Cloud

### Remote Read

Query from long-term storage:

```yaml
remote_read:
  - url: https://prometheus.example.com/api/v1/read
    read_recent: true
```

---

## Federation and Remote Write

### Federation

Prometheus can scrape metrics from other Prometheus servers.

**Use Cases**:
- Hierarchical monitoring (region → global)
- Cross-cluster metrics
- Backup and disaster recovery

**Configuration**:
```yaml
# Global Prometheus
scrape_configs:
  - job_name: 'federate'
    scrape_interval: 60s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="api"}'
        - '{__name__=~"job:.*"}'
    static_configs:
      - targets:
        - 'prometheus-us-east:9090'
        - 'prometheus-us-west:9090'
```

---

## Grafana Integration

### Adding Prometheus Data Source

**UI**: Configuration → Data Sources → Add data source → Prometheus

**Provisioning** (`/etc/grafana/provisioning/datasources/prometheus.yml`):
```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

### Dashboard Examples

**Request Rate Panel**:
```promql
sum(rate(http_requests_total[5m])) by (service)
```

**Error Rate Panel**:
```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
/
sum(rate(http_requests_total[5m])) by (service)
* 100
```

**Latency Heatmap**:
```promql
sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
```

### Variables

**Query Variable** (list of services):
```promql
label_values(http_requests_total, service)
```

**Use in panel**:
```promql
sum(rate(http_requests_total{service="$service"}[5m]))
```

---

## Performance Optimization

### Query Performance

1. **Use recording rules** for expensive aggregations
2. **Limit time range** in dashboards (default: last 1h)
3. **Reduce cardinality** (fewer time series)
4. **Use `rate()` over `increase()`** for better performance
5. **Avoid regex** when possible (`endpoint=~".*"` → `endpoint!=""`)

### Scrape Performance

1. **Increase scrape interval** (15s → 30s) for less critical metrics
2. **Use metric relabeling** to drop unused metrics
3. **Implement metric filtering** in exporters
4. **Use separate Prometheus instances** for different workloads

### Memory Optimization

1. **Reduce retention** (30d → 15d)
2. **Lower cardinality** (drop high-cardinality labels)
3. **Increase `--storage.tsdb.min-block-duration`** and `--storage.tsdb.max-block-duration`

---

## Production Best Practices

1. **High Availability**: Run multiple Prometheus servers (same config)
2. **Long-term Storage**: Use remote write (Thanos, Cortex, M3)
3. **Backup**: Regular snapshots of TSDB
4. **Monitoring**: Monitor Prometheus itself
5. **Alerting**: Use AlertManager with proper routing
6. **Resource Limits**: Set memory/CPU limits in Kubernetes
7. **Security**: Enable TLS, authentication
8. **Version Control**: Store configs in Git
9. **Testing**: Use `promtool` for validation

---

## Common Anti-Patterns

### 1. High-Cardinality Labels

**Wrong**:
```python
requests_total{user_id="123"}
```

**Right**:
```python
requests_total{user_tier="premium"}
```

### 2. Missing Units

**Wrong**:
```python
request_duration = Histogram('request_duration', ...)
```

**Right**:
```python
request_duration = Histogram('request_duration_seconds', ...)
```

### 3. Gauge for Counter

**Wrong**:
```python
errors = Gauge('errors', ...)
errors.inc()
```

**Right**:
```python
errors = Counter('errors_total', ...)
errors.inc()
```

### 4. Summary Instead of Histogram

**Wrong**:
```python
latency = Summary('latency', ...)
```

**Right**:
```python
latency = Histogram('latency_seconds', ..., buckets=[...])
```

---

## Troubleshooting Guide

### No Data in Prometheus

1. Check target status: `http://prometheus:9090/targets`
2. Verify metrics endpoint: `curl http://app:8080/metrics`
3. Check network connectivity
4. Validate scrape config syntax: `promtool check config prometheus.yml`

### High Memory Usage

1. Check cardinality: `count by (__name__) ({__name__=~".+"})`
2. Reduce retention: `--storage.tsdb.retention.time=15d`
3. Drop unused metrics with relabeling

### Slow Queries

1. Use recording rules
2. Reduce time range
3. Check cardinality
4. Simplify PromQL expression

### Missing Metrics

1. Check relabel configs (may be dropping metrics)
2. Verify metric name spelling
3. Check scrape interval (may not be scraped yet)
4. Validate label filters

---

**Last Updated**: 2025-10-27
