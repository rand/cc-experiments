# Prometheus Monitoring Reference

**Comprehensive guide to Prometheus monitoring, PromQL, exporters, and production best practices**

**Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: 3,200+

---

## Table of Contents

1. [Prometheus Architecture](#prometheus-architecture)
2. [Data Model](#data-model)
3. [PromQL Language Reference](#promql-language-reference)
4. [Recording Rules](#recording-rules)
5. [Alerting Rules](#alerting-rules)
6. [Service Discovery](#service-discovery)
7. [Exporters](#exporters)
8. [Storage and Retention](#storage-and-retention)
9. [Federation](#federation)
10. [Remote Storage](#remote-storage)
11. [Cardinality Management](#cardinality-management)
12. [Performance Optimization](#performance-optimization)
13. [High Availability](#high-availability)
14. [Integration with Grafana](#integration-with-grafana)
15. [Integration with Alertmanager](#integration-with-alertmanager)
16. [Production Best Practices](#production-best-practices)
17. [Troubleshooting](#troubleshooting)
18. [References](#references)

---

## Prometheus Architecture

### Core Components

**Prometheus Server**
- Time-series database (TSDB)
- PromQL query engine
- HTTP API for querying
- Web UI for exploration
- Pull-based metric collection (scraping)
- Rule evaluation engine
- Local storage with configurable retention

**Pushgateway**
- Intermediary for short-lived jobs
- Batch jobs push metrics to Pushgateway
- Prometheus scrapes Pushgateway
- Use cases: cron jobs, batch processes, ephemeral tasks
- **Warning**: Not for application-level metrics (anti-pattern)

**Alertmanager**
- Receives alerts from Prometheus
- Deduplication of alerts
- Grouping related alerts
- Silencing alerts
- Routing to notification channels (email, Slack, PagerDuty)
- Alert inhibition (suppress related alerts)

**Exporters**
- Expose metrics from third-party systems
- Convert metrics to Prometheus format
- Official exporters: node_exporter, mysqld_exporter, blackbox_exporter
- Community exporters: 100+ available
- Custom exporters for application metrics

**Client Libraries**
- Instrument applications to expose metrics
- Official libraries: Go, Java, Python, Ruby
- Community libraries: Node.js, Rust, C++, PHP
- Expose metrics at `/metrics` endpoint

### Pull vs Push Model

**Pull Model (Prometheus Default)**
- Prometheus scrapes targets at regular intervals
- Advantages:
  - Centralized service discovery
  - Automatic detection of down targets
  - Simpler configuration for monitored services
  - No need for targets to know Prometheus location
- Disadvantages:
  - Requires targets to be reachable from Prometheus
  - Not suitable for short-lived jobs
  - Firewall complexity in some networks

**Push Model (via Pushgateway)**
- Jobs push metrics to Pushgateway
- Prometheus scrapes Pushgateway
- Advantages:
  - Works for short-lived jobs (batch, cron)
  - Works behind firewalls
- Disadvantages:
  - Metrics can become stale
  - No automatic target detection
  - Single point of failure
  - **Anti-pattern** for long-lived services

### Prometheus Storage

**TSDB (Time Series Database)**
- Optimized for time-series data
- Append-only storage with compression
- Chunk-based storage (2-hour blocks)
- Automatic compaction and retention
- On-disk storage with write-ahead log (WAL)

**Storage Layout**
```
/data
├── wal/                    # Write-ahead log
├── 01ABCDEFGHIJKLMNOP/     # 2-hour block
│   ├── chunks/             # Compressed time-series chunks
│   ├── index               # Inverted index for labels
│   ├── meta.json           # Block metadata
│   └── tombstones          # Deleted series markers
├── 01ABCDEFGHIJKLMNPQ/     # Another 2-hour block
└── ...
```

**Retention Policies**
- `--storage.tsdb.retention.time`: Time-based retention (default: 15d)
- `--storage.tsdb.retention.size`: Size-based retention (e.g., 50GB)
- Blocks older than retention automatically deleted
- Compaction merges small blocks into larger blocks

---

## Data Model

### Metrics and Labels

**Metric Format**
```
<metric_name>{<label_name>=<label_value>, ...} <value> <timestamp>
```

**Example**
```
http_requests_total{method="GET", endpoint="/api/users", status="200"} 1234 1699999999000
```

**Components**:
- **Metric name**: Identifies the time series (e.g., `http_requests_total`)
- **Labels**: Key-value pairs for dimensions (e.g., `method="GET"`)
- **Value**: Floating-point number
- **Timestamp**: Unix timestamp in milliseconds (optional, added by Prometheus)

### Metric Naming Conventions

**Pattern**: `<namespace>_<subsystem>_<name>_<unit>`

**Good Names**
```
http_requests_total                    # Counter of HTTP requests
http_request_duration_seconds          # Histogram of request duration
node_memory_MemAvailable_bytes         # Gauge of available memory
process_cpu_seconds_total              # Counter of CPU time
database_queries_total                 # Counter of database queries
api_response_size_bytes                # Histogram of response size
queue_messages_pending                 # Gauge of pending messages
```

**Bad Names**
```
RequestCount                           # Use snake_case, not CamelCase
http_latency                           # Missing unit (seconds)
TotalErrors                            # Use snake_case
errors                                 # Too generic, add context
```

**Units**
- Use base units (seconds, bytes, ratios)
- **Seconds**: Not milliseconds (convert at instrumentation)
- **Bytes**: Not kilobytes or megabytes
- **Ratios**: 0.0 to 1.0 (not percentages)

### Label Best Practices

**Low-Cardinality Labels** (bounded set of values)
```
# Good: Status codes (limited to ~10 values)
http_requests_total{status="200"}
http_requests_total{status="404"}
http_requests_total{status="500"}

# Good: HTTP methods (limited to ~7 values)
http_requests_total{method="GET"}
http_requests_total{method="POST"}
```

**High-Cardinality Labels** (unbounded set of values - AVOID)
```
# BAD: User ID (millions of unique values)
http_requests_total{user_id="user_12345"}

# BAD: Trace ID (unique per request)
http_requests_total{trace_id="abc123"}

# BAD: Full URL with parameters
http_requests_total{url="/api/users/12345/orders/67890"}
```

**Cardinality Impact**
```
# 1 metric × 5 methods × 10 endpoints × 5 statuses = 250 time series
http_requests_total{method="...", endpoint="...", status="..."}

# 1 metric × 1M user IDs = 1M time series (EXPLOSION!)
http_requests_total{user_id="..."}
```

**Label Guidelines**
- Keep cardinality < 100 per label dimension
- Avoid user IDs, trace IDs, email addresses, UUIDs
- Use templated paths: `/api/users/:id` not `/api/users/12345`
- Use label values that can be aggregated
- Consistent label names across metrics

### Metric Types

#### Counter

**Definition**: Monotonically increasing value (resets to 0 on restart)

**Use Cases**:
- Total requests
- Total errors
- Bytes sent/received
- Tasks completed

**Operations**:
- Only increases (or resets to 0)
- Use `rate()` or `increase()` to get per-second rate

**Example**
```python
from prometheus_client import Counter

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_requests_total.labels(method='GET', endpoint='/api/users', status='200').inc()
http_requests_total.labels(method='POST', endpoint='/api/orders', status='201').inc(5)
```

**PromQL Queries**
```promql
# Requests per second over last 5 minutes
rate(http_requests_total[5m])

# Total increase over last hour
increase(http_requests_total[1h])

# Current counter value (usually not useful)
http_requests_total
```

#### Gauge

**Definition**: Value that can increase or decrease

**Use Cases**:
- Temperature
- Memory usage
- Active connections
- Queue size
- CPU utilization

**Operations**:
- Set to specific value
- Increment or decrement
- Can go up or down

**Example**
```python
from prometheus_client import Gauge

active_connections = Gauge('http_active_connections', 'Active HTTP connections')
memory_usage_bytes = Gauge('process_memory_bytes', 'Process memory usage')
queue_size = Gauge('queue_size', 'Queue size', ['queue_name'])

# Set value
active_connections.set(42)
memory_usage_bytes.set(1024 * 1024 * 100)  # 100 MB

# Increment/decrement
active_connections.inc()
active_connections.dec()
active_connections.inc(5)

# With labels
queue_size.labels(queue_name='tasks').set(123)
```

**PromQL Queries**
```promql
# Current value
http_active_connections

# Average over time
avg_over_time(http_active_connections[5m])

# Maximum over time
max_over_time(http_active_connections[5m])

# Rate of change (for gauges)
delta(process_memory_bytes[5m])
```

#### Histogram

**Definition**: Distribution of values in configurable buckets

**Use Cases**:
- Request latency
- Response size
- Request size
- Processing time

**Buckets**: Cumulative (le = "less than or equal")

**Metrics Exposed**:
- `<name>_bucket{le="<upper_bound>"}`: Cumulative count per bucket
- `<name>_sum`: Sum of all observed values
- `<name>_count`: Total count of observations

**Example**
```python
from prometheus_client import Histogram

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Observe a value
http_request_duration_seconds.labels(method='GET', endpoint='/api/users').observe(0.234)

# Time a block of code
with http_request_duration_seconds.labels(method='POST', endpoint='/api/orders').time():
    process_order()
```

**Metrics Output**
```
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.001"} 0
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.005"} 0
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.01"} 0
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.05"} 2
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.1"} 5
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.5"} 10
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="1.0"} 12
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="2.5"} 12
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="5.0"} 12
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="10.0"} 12
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="+Inf"} 12
http_request_duration_seconds_sum{method="GET",endpoint="/api/users"} 3.45
http_request_duration_seconds_count{method="GET",endpoint="/api/users"} 12
```

**PromQL Queries**
```promql
# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 99th percentile by endpoint
histogram_quantile(0.99,
  sum by (endpoint, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)

# Average latency
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Request rate
rate(http_request_duration_seconds_count[5m])
```

**Bucket Selection**
```python
# Latency (seconds)
buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]

# Request size (bytes)
buckets=[100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000]

# Duration (milliseconds converted to seconds)
buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]

# Exponential buckets (Python)
from prometheus_client import Histogram
buckets = Histogram.linear(0.001, 0.001, 10)  # 0.001 to 0.01 in 10 steps
buckets = Histogram.exponential(0.001, 2, 10)  # Exponential: 0.001, 0.002, 0.004, ...
```

#### Summary

**Definition**: Similar to histogram, calculates quantiles client-side

**Use Cases**:
- Same as histogram, but when server-side aggregation not needed
- Legacy systems (histograms preferred)

**Metrics Exposed**:
- `<name>{quantile="<φ>"}`: Pre-calculated quantiles (e.g., 0.5, 0.9, 0.99)
- `<name>_sum`: Sum of all observed values
- `<name>_count`: Total count of observations

**Example**
```python
from prometheus_client import Summary

request_latency = Summary(
    'request_latency_seconds',
    'Request latency',
    ['endpoint']
)

request_latency.labels(endpoint='/api/users').observe(0.123)

# With specific quantiles
request_latency = Summary(
    'request_latency_seconds',
    'Request latency',
    ['endpoint'],
    quantiles=[0.5, 0.9, 0.95, 0.99]
)
```

**Metrics Output**
```
request_latency_seconds{endpoint="/api/users",quantile="0.5"} 0.15
request_latency_seconds{endpoint="/api/users",quantile="0.9"} 0.35
request_latency_seconds{endpoint="/api/users",quantile="0.95"} 0.42
request_latency_seconds{endpoint="/api/users",quantile="0.99"} 0.58
request_latency_seconds_sum{endpoint="/api/users"} 12.34
request_latency_seconds_count{endpoint="/api/users"} 100
```

**Histogram vs Summary**

| Feature | Histogram | Summary |
|---------|-----------|---------|
| **Quantile calculation** | Server-side (PromQL) | Client-side |
| **Aggregation across instances** | Yes | No |
| **Accuracy** | Approximation (bucket granularity) | Exact (within sample) |
| **Resource usage** | Low CPU, more storage | More CPU, less storage |
| **Bucket configuration** | Required | Not required |
| **Use case** | Preferred for most cases | Legacy or specific needs |

**Recommendation**: Use **Histogram** unless you have specific reasons to use Summary.

---

## PromQL Language Reference

### Selectors

**Instant Vector Selector** (single value per series at query time)
```promql
# All time series with metric name
http_requests_total

# Filter by label value (equality)
http_requests_total{status="200"}

# Multiple label filters (AND)
http_requests_total{status="200", method="GET"}

# Regex matching
http_requests_total{status=~"2.."}      # 2xx status codes
http_requests_total{endpoint=~"/api/.*"}  # Endpoints starting with /api/

# Negative matching
http_requests_total{status!="200"}       # Not 200
http_requests_total{status!~"2.."}       # Not 2xx

# Alternative values (OR)
http_requests_total{status=~"200|404"}   # 200 or 404
```

**Range Vector Selector** (multiple values over time window)
```promql
# Last 5 minutes of data
http_requests_total[5m]

# Time units: s (seconds), m (minutes), h (hours), d (days), w (weeks), y (years)
http_requests_total[30s]
http_requests_total[1h]
http_requests_total[7d]

# Range vectors used in functions (rate, increase, etc.)
rate(http_requests_total[5m])
```

**Offset Modifier** (shift time window)
```promql
# Value 1 hour ago
http_requests_total offset 1h

# Rate from 1 hour ago
rate(http_requests_total[5m] offset 1h)

# Compare current vs 1 day ago
http_requests_total - http_requests_total offset 1d
```

**@ Modifier** (query at specific timestamp)
```promql
# Value at specific Unix timestamp
http_requests_total @ 1609459200

# Rate at specific time
rate(http_requests_total[5m] @ 1609459200)
```

### Operators

**Arithmetic Operators**
```promql
# Addition
metric1 + metric2
http_requests_total + 10

# Subtraction
metric1 - metric2
100 - cpu_idle_percent

# Multiplication
metric1 * metric2
memory_bytes * 1024  # Convert KB to bytes

# Division
metric1 / metric2
errors_total / requests_total  # Error rate

# Modulo
metric1 % metric2

# Exponentiation
metric1 ^ metric2
```

**Comparison Operators** (return 0 or 1, or filter)
```promql
# Equal
metric1 == metric2

# Not equal
metric1 != metric2

# Greater than
metric1 > metric2
cpu_usage > 80  # CPUs with > 80% usage

# Greater than or equal
metric1 >= metric2

# Less than
metric1 < metric2

# Less than or equal
metric1 <= metric2

# Use bool modifier to return 0/1 instead of filtering
cpu_usage > bool 80  # Returns 1 if true, 0 if false
```

**Logical Operators** (on boolean results)
```promql
# AND: Both sides must match
(cpu_usage > 80) and (memory_usage > 90)

# OR: Either side matches
(cpu_usage > 80) or (memory_usage > 90)

# Unless: Left side unless right side matches
all_instances unless down_instances
```

**Vector Matching**
```promql
# One-to-one matching (default: all labels must match)
metric1 + metric2

# Ignoring specific labels
metric1 + ignoring(instance) metric2

# Matching on specific labels only
metric1 + on(job) metric2

# Many-to-one matching (group_left)
metric1 * on(job) group_left metric2

# One-to-many matching (group_right)
metric1 * on(job) group_right metric2
```

### Aggregation Functions

**Basic Aggregation**
```promql
# Sum
sum(http_requests_total)
sum by (status) (http_requests_total)        # Group by status
sum without (instance) (http_requests_total) # Remove instance label

# Average
avg(http_request_duration_seconds)
avg by (endpoint) (http_request_duration_seconds)

# Minimum
min(http_request_duration_seconds)
min by (endpoint) (http_request_duration_seconds)

# Maximum
max(http_request_duration_seconds)
max by (endpoint) (http_request_duration_seconds)

# Count
count(http_requests_total)
count by (status) (http_requests_total)

# Standard deviation
stddev(http_request_duration_seconds)

# Variance
stdvar(http_request_duration_seconds)
```

**Top/Bottom K**
```promql
# Top 5 endpoints by request rate
topk(5, sum by (endpoint) (rate(http_requests_total[5m])))

# Bottom 3 instances by memory
bottomk(3, node_memory_MemAvailable_bytes)

# Top 10 errors by status code
topk(10, sum by (status) (rate(http_requests_total{status=~"5.."}[5m])))
```

**Count Values**
```promql
# Count occurrences of each unique value
count_values("status", http_response_status)

# Count instances by CPU count
count_values("cpu_count", node_cpu_count)
```

**Quantile**
```promql
# 95th percentile across all instances
quantile(0.95, http_request_duration_seconds)

# 99th percentile by endpoint
quantile by (endpoint) (0.99, http_request_duration_seconds)
```

### Functions

**Rate and Increase**
```promql
# Per-second rate over time window
rate(http_requests_total[5m])

# Instant rate (only last 2 points, more sensitive to scrape failures)
irate(http_requests_total[5m])

# Total increase over time window
increase(http_requests_total[1h])

# Use rate() for alerts and graphs (more stable)
# Use irate() for volatile, fast-moving counters (rare)
```

**Delta and Deriv**
```promql
# Difference between first and last value (for gauges)
delta(cpu_temperature_celsius[5m])

# Instant delta (last 2 points)
idelta(cpu_temperature_celsius[5m])

# Per-second derivative (linear regression)
deriv(cpu_temperature_celsius[5m])
```

**Prediction**
```promql
# Predict value in 1 hour using linear regression over last 1 hour
predict_linear(disk_usage_bytes[1h], 3600)

# Predict disk full time
predict_linear(disk_usage_bytes[1h], 3600 * 24 * 7)  # 1 week ahead
```

**Time Functions**
```promql
# Current Unix timestamp
time()

# Day of week (0 = Sunday, 6 = Saturday)
day_of_week()

# Day of month (1-31)
day_of_month()

# Hour of day (0-23)
hour()

# Minute (0-59)
minute()
```

**Aggregation Over Time**
```promql
# Average over time range
avg_over_time(cpu_usage[1h])

# Maximum over time range
max_over_time(cpu_usage[1h])

# Minimum over time range
min_over_time(cpu_usage[1h])

# Sum over time range (rare, usually use increase())
sum_over_time(metric[1h])

# Count over time range
count_over_time(metric[1h])

# Standard deviation over time
stddev_over_time(metric[1h])

# Quantile over time
quantile_over_time(0.95, metric[1h])
```

**Histogram Quantile**
```promql
# Calculate quantile from histogram buckets
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# By label
histogram_quantile(0.95,
  sum by (endpoint, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)

# Multiple quantiles
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))  # p50
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))  # p95
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))  # p99
```

**Sorting**
```promql
# Sort ascending
sort(http_requests_total)

# Sort descending
sort_desc(http_requests_total)
```

**Label Manipulation**
```promql
# Replace label value
label_replace(
  metric,
  "new_label",       # Destination label
  "$1",              # Replacement (from regex capture group)
  "source_label",    # Source label
  "(.*)"             # Regex pattern
)

# Example: Extract instance name from address
label_replace(
  up,
  "instance_name",
  "$1",
  "instance",
  "([^:]+):.*"       # Capture before ':'
)

# Join label values
label_join(
  metric,
  "new_label",       # Destination label
  "-",               # Separator
  "label1", "label2" # Source labels
)
```

**Absent**
```promql
# Returns 1 if no time series match (for alerting on missing metrics)
absent(up{job="api-server"})

# Alert if metric not present
absent(http_requests_total{job="api-server"})
```

**Changes and Resets**
```promql
# Number of times value changed
changes(metric[1h])

# Number of times counter reset (restarted)
resets(counter_metric[1h])
```

**Clamp**
```promql
# Clamp values to min/max
clamp_min(cpu_usage, 0)     # Minimum 0
clamp_max(cpu_usage, 100)   # Maximum 100
clamp(cpu_usage, 0, 100)    # Between 0 and 100
```

**Round**
```promql
# Round to nearest integer
round(metric)

# Round to nearest 10
round(metric, 10)

# Round to nearest 0.1
round(metric, 0.1)

# Floor (round down)
floor(metric)

# Ceil (round up)
ceil(metric)
```

**Mathematical**
```promql
# Absolute value
abs(metric)

# Square root
sqrt(metric)

# Natural logarithm
ln(metric)

# Base-2 logarithm
log2(metric)

# Base-10 logarithm
log10(metric)

# Exponential
exp(metric)
```

### Common Query Patterns

**Request Rate (Requests Per Second)**
```promql
# Total RPS
sum(rate(http_requests_total[5m]))

# RPS by endpoint
sum by (endpoint) (rate(http_requests_total[5m]))

# RPS by status code
sum by (status) (rate(http_requests_total[5m]))
```

**Error Rate**
```promql
# Error rate (percentage)
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
* 100

# Error rate by endpoint
sum by (endpoint) (rate(http_requests_total{status=~"5.."}[5m]))
/
sum by (endpoint) (rate(http_requests_total[5m]))
* 100
```

**Latency Percentiles**
```promql
# p50 (median)
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))

# p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# p99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# p99.9
histogram_quantile(0.999, rate(http_request_duration_seconds_bucket[5m]))

# By endpoint
histogram_quantile(0.95,
  sum by (endpoint, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)
```

**Apdex Score** (Application Performance Index)
```promql
# Apdex = (satisfied + tolerating/2) / total
# Satisfied: < 0.5s, Tolerating: 0.5s - 2s, Frustrated: > 2s
(
  sum(rate(http_request_duration_seconds_bucket{le="0.5"}[5m]))
  +
  sum(rate(http_request_duration_seconds_bucket{le="2"}[5m]))
  / 2
)
/
sum(rate(http_request_duration_seconds_count[5m]))
```

**CPU Utilization**
```promql
# Overall CPU utilization (%)
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Per-core CPU utilization
100 - (avg by (instance, cpu) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# CPU by mode
sum by (mode) (rate(node_cpu_seconds_total[5m])) * 100
```

**Memory Utilization**
```promql
# Memory utilization (%)
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))

# Memory used (bytes)
node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes

# Swap usage (%)
100 * (1 - (node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes))
```

**Disk Utilization**
```promql
# Disk utilization (%)
100 - (node_filesystem_avail_bytes / node_filesystem_size_bytes * 100)

# Exclude tmpfs and other ephemeral filesystems
100 - (
  node_filesystem_avail_bytes{fstype!~"tmpfs|fuse.*"}
  / node_filesystem_size_bytes * 100
)

# Disk I/O rate
rate(node_disk_read_bytes_total[5m])
rate(node_disk_written_bytes_total[5m])
```

**Network Traffic**
```promql
# Receive rate (bytes/sec)
rate(node_network_receive_bytes_total[5m])

# Transmit rate (bytes/sec)
rate(node_network_transmit_bytes_total[5m])

# Total bandwidth (receive + transmit)
rate(node_network_receive_bytes_total[5m]) + rate(node_network_transmit_bytes_total[5m])

# Network errors
rate(node_network_receive_errs_total[5m])
rate(node_network_transmit_errs_total[5m])
```

**Saturation**
```promql
# Load average (should be < number of CPUs)
node_load1

# Saturation ratio (load / CPU count)
node_load1 / count by (instance) (node_cpu_seconds_total{mode="idle"})
```

---

## Recording Rules

### Purpose

**Recording Rules**: Precompute frequently used or expensive queries

**Benefits**:
- **Performance**: Faster dashboard loading (precomputed results)
- **Consistency**: Same calculation used everywhere
- **Complexity reduction**: Hide complex queries behind simple metric names
- **Resource efficiency**: Compute once, use many times

**Use Cases**:
- Complex aggregations used in multiple dashboards
- Expensive histogram quantile calculations
- Time-series used in multiple alerts
- Aggregating metrics for long-term retention

### Configuration

**File Structure**
```yaml
# rules/recording-rules.yml
groups:
  - name: group_name
    interval: 30s  # Evaluation interval (default: global.evaluation_interval)
    rules:
      - record: metric_name
        expr: promql_expression
        labels:
          label_name: label_value
```

**Prometheus Configuration**
```yaml
# prometheus.yml
rule_files:
  - "rules/*.yml"
```

### Naming Convention

**Pattern**: `level:metric:operations`

**Levels**:
- `instance`: Per-instance metrics (no aggregation)
- `job`: Aggregated by job
- `cluster`: Aggregated across cluster
- `service`: Aggregated by service

**Examples**:
```
job:http_requests:rate5m              # Request rate by job
job:http_errors:rate5m                # Error rate by job
cluster:http_latency:p95              # p95 latency across cluster
instance:node_cpu:utilization         # CPU utilization per instance
service:api_errors:ratio              # Error ratio by service
```

### Examples

**Basic Recording Rules**
```yaml
groups:
  - name: api_performance
    interval: 30s
    rules:
      # Request rate per job
      - record: job:http_requests:rate5m
        expr: |
          sum by (job) (
            rate(http_requests_total[5m])
          )

      # Request rate per endpoint
      - record: job:http_requests:rate5m:by_endpoint
        expr: |
          sum by (job, endpoint) (
            rate(http_requests_total[5m])
          )

      # Error rate (percentage)
      - record: job:http_errors:rate5m
        expr: |
          sum by (job) (
            rate(http_requests_total{status=~"5.."}[5m])
          ) / sum by (job) (
            rate(http_requests_total[5m])
          ) * 100

      # Error rate by endpoint
      - record: job:http_errors:rate5m:by_endpoint
        expr: |
          sum by (job, endpoint) (
            rate(http_requests_total{status=~"5.."}[5m])
          ) / sum by (job, endpoint) (
            rate(http_requests_total[5m])
          ) * 100
```

**Latency Recording Rules**
```yaml
groups:
  - name: latency_percentiles
    interval: 30s
    rules:
      # p50 latency
      - record: job:http_latency:p50
        expr: |
          histogram_quantile(0.50,
            sum by (job, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )

      # p95 latency
      - record: job:http_latency:p95
        expr: |
          histogram_quantile(0.95,
            sum by (job, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )

      # p99 latency
      - record: job:http_latency:p99
        expr: |
          histogram_quantile(0.99,
            sum by (job, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )

      # p99 latency by endpoint
      - record: job:http_latency:p99:by_endpoint
        expr: |
          histogram_quantile(0.99,
            sum by (job, endpoint, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )

      # Average latency
      - record: job:http_latency:avg
        expr: |
          rate(http_request_duration_seconds_sum[5m])
          / rate(http_request_duration_seconds_count[5m])
```

**Resource Utilization Rules**
```yaml
groups:
  - name: resource_metrics
    interval: 30s
    rules:
      # CPU utilization (%)
      - record: instance:node_cpu:utilization
        expr: |
          100 - (avg by (instance) (
            rate(node_cpu_seconds_total{mode="idle"}[5m])
          ) * 100)

      # Memory utilization (%)
      - record: instance:node_memory:utilization
        expr: |
          100 * (1 - (
            node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
          ))

      # Disk utilization (%)
      - record: instance:node_disk:utilization
        expr: |
          100 - (
            node_filesystem_avail_bytes{fstype!~"tmpfs|fuse.*"}
            / node_filesystem_size_bytes * 100
          )

      # Disk I/O rate (bytes/sec)
      - record: instance:node_disk_io:rate
        expr: |
          sum by (instance, device) (
            rate(node_disk_read_bytes_total[5m])
            + rate(node_disk_written_bytes_total[5m])
          )

      # Network traffic (bytes/sec)
      - record: instance:node_network:rate
        expr: |
          sum by (instance, device) (
            rate(node_network_receive_bytes_total[5m])
            + rate(node_network_transmit_bytes_total[5m])
          )
```

**Multi-Level Aggregation**
```yaml
groups:
  - name: hierarchical_aggregation
    interval: 30s
    rules:
      # Level 1: Instance-level
      - record: instance:http_requests:rate5m
        expr: |
          sum by (instance) (
            rate(http_requests_total[5m])
          )

      # Level 2: Job-level (uses Level 1)
      - record: job:http_requests:rate5m
        expr: |
          sum by (job) (
            instance:http_requests:rate5m
          )

      # Level 3: Cluster-level (uses Level 2)
      - record: cluster:http_requests:rate5m
        expr: |
          sum(job:http_requests:rate5m)
```

**SLI (Service Level Indicator) Rules**
```yaml
groups:
  - name: sli_metrics
    interval: 30s
    rules:
      # Availability (% of successful requests)
      - record: sli:availability:ratio
        expr: |
          sum(rate(http_requests_total{status!~"5.."}[5m]))
          / sum(rate(http_requests_total[5m]))

      # Latency SLI (% of requests < 500ms)
      - record: sli:latency:ratio
        expr: |
          sum(rate(http_request_duration_seconds_bucket{le="0.5"}[5m]))
          / sum(rate(http_request_duration_seconds_count[5m]))

      # Quality SLI (% of requests without errors)
      - record: sli:quality:ratio
        expr: |
          sum(rate(http_requests_total{status=~"2..|3.."}[5m]))
          / sum(rate(http_requests_total[5m]))
```

### Best Practices

**DO**:
- Use recording rules for frequently queried metrics
- Precompute expensive histogram quantiles
- Use hierarchical aggregation (instance → job → cluster)
- Follow naming convention: `level:metric:operations`
- Keep expressions readable with multi-line format
- Use consistent intervals (30s or 1m)

**DON'T**:
- Record every metric (only frequently used ones)
- Create recording rules for rarely used queries
- Use recording rules as a substitute for optimizing queries
- Create circular dependencies between rules
- Use high-cardinality labels in aggregations

---

## Alerting Rules

### Purpose

**Alerting Rules**: Define conditions that trigger alerts

**Alert Lifecycle**:
1. **Inactive**: Condition not met
2. **Pending**: Condition met, but not for `for` duration
3. **Firing**: Condition met for `for` duration, alert sent to Alertmanager
4. **Resolved**: Condition no longer met

### Configuration

**File Structure**
```yaml
# alerts/alerting-rules.yml
groups:
  - name: group_name
    interval: 15s  # Evaluation interval
    rules:
      - alert: AlertName
        expr: promql_expression > threshold
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Brief description"
          description: "Detailed description with {{ $labels.instance }}"
          dashboard: "https://grafana.example.com/d/xyz"
```

**Prometheus Configuration**
```yaml
# prometheus.yml
rule_files:
  - "alerts/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - localhost:9093
```

### Severity Levels

**Standard Severity Levels**:
- **critical**: Immediate attention required (pager)
- **warning**: Should be addressed soon (ticket)
- **info**: Informational (log only)

**Example**
```yaml
labels:
  severity: critical  # Page on-call engineer
  severity: warning   # Create ticket
  severity: info      # Log for analysis
```

### Examples

**Service Health Alerts**
```yaml
groups:
  - name: service_health
    interval: 15s
    rules:
      # Service down
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "Instance {{ $labels.instance }} has been down for more than 1 minute"
          runbook: "https://wiki.example.com/runbooks/service-down"

      # Instance flapping (restarting frequently)
      - alert: InstanceFlapping
        expr: changes(up[10m]) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Instance {{ $labels.instance }} is flapping"
          description: "Instance has restarted {{ $value }} times in the last 10 minutes"

      # High restart rate
      - alert: HighRestartRate
        expr: rate(process_start_time_seconds[15m]) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High restart rate on {{ $labels.job }}"
          description: "Service is restarting {{ $value | humanize }} times per second"
```

**Error Rate Alerts**
```yaml
groups:
  - name: error_rates
    interval: 15s
    rules:
      # High error rate (> 5%)
      - alert: HighErrorRate
        expr: |
          sum by (job) (
            rate(http_requests_total{status=~"5.."}[5m])
          ) / sum by (job) (
            rate(http_requests_total[5m])
          ) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.job }}"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

      # Critical error rate (> 10%)
      - alert: CriticalErrorRate
        expr: |
          sum by (job) (
            rate(http_requests_total{status=~"5.."}[5m])
          ) / sum by (job) (
            rate(http_requests_total[5m])
          ) > 0.10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critical error rate on {{ $labels.job }}"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 10%)"

      # Error rate by endpoint
      - alert: HighEndpointErrorRate
        expr: |
          sum by (job, endpoint) (
            rate(http_requests_total{status=~"5.."}[5m])
          ) / sum by (job, endpoint) (
            rate(http_requests_total[5m])
          ) > 0.05
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.endpoint }}"
          description: "Error rate is {{ $value | humanizePercentage }} for {{ $labels.job }}/{{ $labels.endpoint }}"
```

**Latency Alerts**
```yaml
groups:
  - name: latency
    interval: 15s
    rules:
      # High p95 latency
      - alert: HighP95Latency
        expr: |
          histogram_quantile(0.95,
            sum by (job, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          ) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High p95 latency on {{ $labels.job }}"
          description: "p95 latency is {{ $value }}s (threshold: 1s)"

      # Critical p99 latency
      - alert: CriticalP99Latency
        expr: |
          histogram_quantile(0.99,
            sum by (job, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          ) > 5.0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critical p99 latency on {{ $labels.job }}"
          description: "p99 latency is {{ $value }}s (threshold: 5s)"

      # Latency degradation (50% increase)
      - alert: LatencyDegradation
        expr: |
          (
            histogram_quantile(0.95,
              sum by (job, le) (
                rate(http_request_duration_seconds_bucket[5m])
              )
            )
            /
            histogram_quantile(0.95,
              sum by (job, le) (
                rate(http_request_duration_seconds_bucket[5m] offset 1h)
              )
            )
          ) > 1.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Latency degradation on {{ $labels.job }}"
          description: "p95 latency increased by {{ $value | humanizePercentage }} compared to 1 hour ago"
```

**Resource Alerts**
```yaml
groups:
  - name: resources
    interval: 15s
    rules:
      # High CPU usage
      - alert: HighCPU
        expr: |
          100 - (avg by (instance) (
            rate(node_cpu_seconds_total{mode="idle"}[5m])
          ) * 100) > 80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High CPU on {{ $labels.instance }}"
          description: "CPU usage is {{ $value | humanize }}%"

      # Critical CPU usage
      - alert: CriticalCPU
        expr: |
          100 - (avg by (instance) (
            rate(node_cpu_seconds_total{mode="idle"}[5m])
          ) * 100) > 95
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Critical CPU on {{ $labels.instance }}"
          description: "CPU usage is {{ $value | humanize }}%"

      # High memory usage
      - alert: HighMemory
        expr: |
          100 * (1 - (
            node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
          )) > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory on {{ $labels.instance }}"
          description: "Memory usage is {{ $value | humanize }}%"

      # Critical memory usage
      - alert: CriticalMemory
        expr: |
          100 * (1 - (
            node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
          )) > 95
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critical memory on {{ $labels.instance }}"
          description: "Memory usage is {{ $value | humanize }}%"

      # Disk space low
      - alert: DiskSpaceLow
        expr: |
          100 - (
            node_filesystem_avail_bytes{fstype!~"tmpfs|fuse.*"}
            / node_filesystem_size_bytes * 100
          ) > 80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space on {{ $labels.instance }}"
          description: "Disk {{ $labels.mountpoint }} is {{ $value | humanize }}% full"

      # Disk space critical
      - alert: DiskSpaceCritical
        expr: |
          100 - (
            node_filesystem_avail_bytes{fstype!~"tmpfs|fuse.*"}
            / node_filesystem_size_bytes * 100
          ) > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Critical disk space on {{ $labels.instance }}"
          description: "Disk {{ $labels.mountpoint }} is {{ $value | humanize }}% full"

      # Disk will fill in 4 hours
      - alert: DiskWillFillSoon
        expr: |
          predict_linear(
            node_filesystem_avail_bytes{fstype!~"tmpfs|fuse.*"}[1h],
            4 * 3600
          ) < 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Disk will fill soon on {{ $labels.instance }}"
          description: "Disk {{ $labels.mountpoint }} will fill in approximately 4 hours"
```

**Saturation Alerts**
```yaml
groups:
  - name: saturation
    interval: 15s
    rules:
      # High load average
      - alert: HighLoadAverage
        expr: |
          node_load15
          / count by (instance) (node_cpu_seconds_total{mode="idle"})
          > 1.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High load average on {{ $labels.instance }}"
          description: "Load average is {{ $value | humanize }}x CPU count"

      # Network interface saturated
      - alert: NetworkSaturated
        expr: |
          rate(node_network_receive_bytes_total[5m]) > 100 * 1024 * 1024  # 100 MB/s
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Network saturated on {{ $labels.instance }}"
          description: "Interface {{ $labels.device }} receiving {{ $value | humanize }}B/s"

      # Too many open files
      - alert: TooManyOpenFiles
        expr: |
          process_open_fds / process_max_fds > 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Too many open files on {{ $labels.instance }}"
          description: "{{ $value | humanizePercentage }} of file descriptors in use"
```

**Absence Alerts** (missing metrics)
```yaml
groups:
  - name: absence
    interval: 1m
    rules:
      # Metrics not being scraped
      - alert: MetricsMissing
        expr: |
          absent(up{job="api-server"})
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Metrics missing for api-server"
          description: "No metrics received from api-server for 5 minutes"

      # Specific metric missing
      - alert: HTTPMetricsMissing
        expr: |
          absent(http_requests_total{job="api-server"})
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "HTTP metrics missing"
          description: "No HTTP request metrics from api-server for 10 minutes"
```

### Template Functions

**Humanize Functions**
```yaml
annotations:
  # Humanize number
  summary: "{{ $value | humanize }}"
  # Output: "1234567.89" → "1.234568M"

  # Humanize percentage
  summary: "{{ $value | humanizePercentage }}"
  # Output: "0.123" → "12.3%"

  # Humanize duration
  summary: "{{ $value | humanizeDuration }}"
  # Output: "3661" → "1h 1m 1s"

  # Humanize timestamp
  summary: "{{ $value | humanizeTimestamp }}"
  # Output: "1609459200" → "2021-01-01 00:00:00"
```

**Label Access**
```yaml
annotations:
  # Access label values
  summary: "High CPU on {{ $labels.instance }}"
  description: "Job: {{ $labels.job }}, Instance: {{ $labels.instance }}"

  # All labels as key-value pairs
  summary: "Alert on {{ $labels }}"
```

**Value Formatting**
```yaml
annotations:
  # Current value
  summary: "Value is {{ $value }}"

  # Formatted value
  summary: "Value is {{ printf \"%.2f\" $value }}"
  # Output: "Value is 12.34"

  # Conditional formatting
  summary: |
    {{ if gt $value 0.5 }}High{{ else }}Low{{ end }} usage
```

### Best Practices

**Alert Design**:
- Use `for` clause to avoid flapping alerts (e.g., `for: 5m`)
- Set appropriate severity levels (critical, warning, info)
- Include actionable information in annotations
- Add runbook URLs for complex alerts
- Use templating to include context ({{ $labels.instance }})

**Thresholds**:
- Base thresholds on SLOs/SLAs
- Different thresholds for warning vs critical
- Consider using recording rules for complex conditions
- Test alerts with realistic data

**Notification Fatigue**:
- Avoid too many low-priority alerts
- Group related alerts
- Use appropriate `for` durations
- Tune thresholds based on feedback

**DO**:
- Alert on symptoms (user-facing issues)
- Include enough context to diagnose
- Use recording rules for complex expressions
- Test alerts before deploying
- Document alerts in runbooks

**DON'T**:
- Alert on every minor issue
- Use `for: 0s` (instant alerts flap)
- Create alerts without clear action
- Ignore alert fatigue
- Forget to test alerts

---

## Service Discovery

### Why Service Discovery

**Static Configuration Limitations**:
- Manual updates when targets change
- Doesn't scale for dynamic environments
- Error-prone maintenance
- No auto-discovery of new services

**Service Discovery Benefits**:
- Automatic target discovery
- Adapts to infrastructure changes
- Scales with environment
- Reduced manual configuration

### Kubernetes Service Discovery

**Pod Discovery**
```yaml
scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      # Only scrape pods with annotation prometheus.io/scrape=true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true

      # Use custom metrics path from annotation
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)

      # Use custom port from annotation
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__

      # Add namespace label
      - source_labels: [__meta_kubernetes_namespace]
        target_label: kubernetes_namespace

      # Add pod name label
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: kubernetes_pod_name

      # Add container name label
      - source_labels: [__meta_kubernetes_pod_container_name]
        target_label: kubernetes_container_name
```

**Pod Annotations**
```yaml
# Kubernetes pod spec
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
spec:
  containers:
    - name: app
      image: my-app:latest
      ports:
        - containerPort: 8080
```

**Service Discovery**
```yaml
scrape_configs:
  - job_name: 'kubernetes-services'
    kubernetes_sd_configs:
      - role: service
    relabel_configs:
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_service_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      - source_labels: [__meta_kubernetes_namespace]
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_service_name]
        target_label: kubernetes_service_name
```

**Endpoints Discovery**
```yaml
scrape_configs:
  - job_name: 'kubernetes-endpoints'
    kubernetes_sd_configs:
      - role: endpoints
    relabel_configs:
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scheme]
        action: replace
        target_label: __scheme__
        regex: (https?)
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_service_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
```

### Consul Service Discovery

```yaml
scrape_configs:
  - job_name: 'consul-services'
    consul_sd_configs:
      - server: 'localhost:8500'
        datacenter: 'dc1'
        tags: ['production', 'monitoring']
        services: []  # Empty = discover all services
    relabel_configs:
      # Use service name as job label
      - source_labels: [__meta_consul_service]
        target_label: job

      # Add service tags as labels
      - source_labels: [__meta_consul_tags]
        target_label: consul_tags

      # Add datacenter label
      - source_labels: [__meta_consul_dc]
        target_label: datacenter

      # Filter by tag
      - source_labels: [__meta_consul_tags]
        regex: '.*,monitoring,.*'
        action: keep
```

**Consul Service Registration**
```json
{
  "service": {
    "name": "api-server",
    "tags": ["production", "monitoring"],
    "port": 8080,
    "check": {
      "http": "http://localhost:8080/health",
      "interval": "10s"
    }
  }
}
```

### EC2 Service Discovery

```yaml
scrape_configs:
  - job_name: 'ec2-instances'
    ec2_sd_configs:
      - region: us-east-1
        access_key: YOUR_ACCESS_KEY
        secret_key: YOUR_SECRET_KEY
        port: 9100
        filters:
          - name: tag:Environment
            values: [production]
          - name: instance-state-name
            values: [running]
    relabel_configs:
      # Use instance ID as instance label
      - source_labels: [__meta_ec2_instance_id]
        target_label: instance_id

      # Add availability zone
      - source_labels: [__meta_ec2_availability_zone]
        target_label: availability_zone

      # Add instance type
      - source_labels: [__meta_ec2_instance_type]
        target_label: instance_type

      # Use private IP
      - source_labels: [__meta_ec2_private_ip]
        target_label: __address__
        replacement: ${1}:9100

      # Add Name tag as instance label
      - source_labels: [__meta_ec2_tag_Name]
        target_label: instance
```

### File-Based Service Discovery

**Configuration**
```yaml
scrape_configs:
  - job_name: 'file-sd'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/*.json'
          - '/etc/prometheus/targets/*.yml'
        refresh_interval: 30s
```

**JSON Format**
```json
[
  {
    "targets": ["host1:9100", "host2:9100"],
    "labels": {
      "job": "node",
      "env": "production",
      "datacenter": "us-east-1"
    }
  },
  {
    "targets": ["api1:8080", "api2:8080", "api3:8080"],
    "labels": {
      "job": "api-server",
      "env": "production",
      "version": "v1.2.3"
    }
  }
]
```

**YAML Format**
```yaml
- targets:
    - host1:9100
    - host2:9100
  labels:
    job: node
    env: production
    datacenter: us-east-1

- targets:
    - api1:8080
    - api2:8080
  labels:
    job: api-server
    env: production
    version: v1.2.3
```

### DNS Service Discovery

```yaml
scrape_configs:
  - job_name: 'dns-sd'
    dns_sd_configs:
      - names:
          - 'node.example.com'
          - 'api.example.com'
        type: 'A'
        port: 9100
        refresh_interval: 30s
    relabel_configs:
      - source_labels: [__meta_dns_name]
        target_label: __address__
        replacement: ${1}:9100
```

### Relabeling

**Common Relabel Actions**

**keep**: Keep only matching targets
```yaml
- source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
  action: keep
  regex: true
```

**drop**: Drop matching targets
```yaml
- source_labels: [__meta_kubernetes_namespace]
  action: drop
  regex: kube-system
```

**replace**: Replace label value
```yaml
- source_labels: [__meta_kubernetes_pod_name]
  target_label: pod_name
  replacement: $1
```

**labelmap**: Map label names
```yaml
- action: labelmap
  regex: __meta_kubernetes_pod_label_(.+)
```

**labeldrop**: Drop labels matching regex
```yaml
- action: labeldrop
  regex: __meta_kubernetes_pod_label_.*
```

**labelkeep**: Keep only labels matching regex
```yaml
- action: labelkeep
  regex: (instance|job|kubernetes_.*)
```

---

## Exporters

### Node Exporter

**Purpose**: System and hardware metrics (CPU, memory, disk, network)

**Installation**
```bash
# Download and run
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.7.0.linux-amd64.tar.gz
cd node_exporter-1.7.0.linux-amd64
./node_exporter

# Metrics at http://localhost:9100/metrics
```

**Systemd Service**
```ini
[Unit]
Description=Node Exporter
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
```

**Key Metrics**
```
# CPU
node_cpu_seconds_total{mode="idle"}
node_cpu_seconds_total{mode="system"}
node_cpu_seconds_total{mode="user"}

# Memory
node_memory_MemTotal_bytes
node_memory_MemAvailable_bytes
node_memory_SwapFree_bytes

# Disk
node_filesystem_avail_bytes
node_filesystem_size_bytes
node_disk_read_bytes_total
node_disk_written_bytes_total

# Network
node_network_receive_bytes_total
node_network_transmit_bytes_total
node_network_receive_errs_total

# Load
node_load1
node_load5
node_load15
```

### Blackbox Exporter

**Purpose**: Probing endpoints (HTTP, TCP, ICMP, DNS)

**Configuration**
```yaml
# blackbox.yml
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      valid_status_codes: [200]
      method: GET
      fail_if_ssl: false
      fail_if_not_ssl: false

  http_post_2xx:
    prober: http
    timeout: 5s
    http:
      method: POST
      headers:
        Content-Type: application/json
      body: '{"key": "value"}'
      valid_status_codes: [200, 201]

  tcp_connect:
    prober: tcp
    timeout: 5s

  icmp:
    prober: icmp
    timeout: 5s
    icmp:
      preferred_ip_protocol: ip4

  dns:
    prober: dns
    timeout: 5s
    dns:
      query_name: example.com
      query_type: A
```

**Prometheus Configuration**
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
        replacement: localhost:9115  # Blackbox exporter address
```

**Key Metrics**
```
# Probe success (0 or 1)
probe_success

# HTTP-specific
probe_http_status_code
probe_http_duration_seconds
probe_http_ssl_earliest_cert_expiry

# DNS-specific
probe_dns_lookup_time_seconds

# ICMP-specific
probe_icmp_duration_seconds
```

### MySQL Exporter

**Installation**
```bash
docker run -d \
  -p 9104:9104 \
  -e DATA_SOURCE_NAME="user:password@(localhost:3306)/" \
  prom/mysqld-exporter
```

**Key Metrics**
```
# Connections
mysql_global_status_threads_connected
mysql_global_status_max_used_connections
mysql_global_status_aborted_connects

# Queries
mysql_global_status_queries
mysql_global_status_slow_queries
mysql_global_status_com_select
mysql_global_status_com_insert
mysql_global_status_com_update
mysql_global_status_com_delete

# InnoDB
mysql_global_status_innodb_buffer_pool_read_requests
mysql_global_status_innodb_buffer_pool_reads
mysql_global_status_innodb_row_lock_waits
```

### Postgres Exporter

**Installation**
```bash
docker run -d \
  -p 9187:9187 \
  -e DATA_SOURCE_NAME="postgresql://postgres:password@localhost:5432/postgres?sslmode=disable" \
  prometheuscommunity/postgres-exporter
```

**Key Metrics**
```
# Connections
pg_stat_database_numbackends

# Transactions
pg_stat_database_xact_commit
pg_stat_database_xact_rollback

# Locks
pg_locks_count

# Replication
pg_stat_replication_replay_lag
```

### Redis Exporter

**Installation**
```bash
docker run -d \
  -p 9121:9121 \
  oliver006/redis_exporter \
  --redis.addr=redis://localhost:6379
```

**Key Metrics**
```
# Connections
redis_connected_clients

# Memory
redis_memory_used_bytes
redis_memory_max_bytes

# Commands
redis_commands_processed_total
redis_commands_duration_seconds_total

# Keys
redis_db_keys
redis_db_keys_expiring

# Replication
redis_connected_slaves
redis_replication_lag_bytes
```

### Custom Exporter (Python)

```python
#!/usr/bin/env python3
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import time
import random
import psutil

# Define metrics
cpu_usage = Gauge('custom_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('custom_memory_usage_bytes', 'Memory usage in bytes')
disk_usage = Gauge('custom_disk_usage_percent', 'Disk usage percentage', ['mount_point'])
requests_total = Counter('custom_requests_total', 'Total requests', ['endpoint', 'status'])
request_duration = Histogram(
    'custom_request_duration_seconds',
    'Request duration',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0]
)

def collect_system_metrics():
    """Collect system metrics using psutil."""
    # CPU
    cpu_usage.set(psutil.cpu_percent(interval=1))

    # Memory
    mem = psutil.virtual_memory()
    memory_usage.set(mem.used)

    # Disk
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_usage.labels(mount_point=partition.mountpoint).set(usage.percent)
        except PermissionError:
            pass

def simulate_application_metrics():
    """Simulate application metrics."""
    endpoints = ['/api/users', '/api/orders', '/api/products']
    statuses = ['200', '404', '500']

    endpoint = random.choice(endpoints)
    status = random.choice(statuses)

    # Increment request counter
    requests_total.labels(endpoint=endpoint, status=status).inc()

    # Observe request duration
    duration = random.uniform(0.01, 1.0)
    request_duration.labels(endpoint=endpoint).observe(duration)

if __name__ == '__main__':
    # Start HTTP server
    start_http_server(8080)
    print("Custom exporter running on :8080/metrics")

    # Collect metrics periodically
    while True:
        collect_system_metrics()
        simulate_application_metrics()
        time.sleep(5)
```

### Custom Exporter (Go)

```go
package main

import (
    "log"
    "math/rand"
    "net/http"
    "time"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
    "github.com/prometheus/client_golang/prometheus/promhttp"
    "github.com/shirou/gopsutil/v3/cpu"
    "github.com/shirou/gopsutil/v3/mem"
)

var (
    cpuUsage = promauto.NewGauge(prometheus.GaugeOpts{
        Name: "custom_cpu_usage_percent",
        Help: "CPU usage percentage",
    })

    memoryUsage = promauto.NewGauge(prometheus.GaugeOpts{
        Name: "custom_memory_usage_bytes",
        Help: "Memory usage in bytes",
    })

    requestsTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "custom_requests_total",
            Help: "Total requests",
        },
        []string{"endpoint", "status"},
    )

    requestDuration = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "custom_request_duration_seconds",
            Help:    "Request duration",
            Buckets: []float64{0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0},
        },
        []string{"endpoint"},
    )
)

func collectSystemMetrics() {
    // CPU
    cpuPercent, _ := cpu.Percent(time.Second, false)
    if len(cpuPercent) > 0 {
        cpuUsage.Set(cpuPercent[0])
    }

    // Memory
    vmem, _ := mem.VirtualMemory()
    memoryUsage.Set(float64(vmem.Used))
}

func simulateApplicationMetrics() {
    endpoints := []string{"/api/users", "/api/orders", "/api/products"}
    statuses := []string{"200", "404", "500"}

    endpoint := endpoints[rand.Intn(len(endpoints))]
    status := statuses[rand.Intn(len(statuses))]

    // Increment counter
    requestsTotal.WithLabelValues(endpoint, status).Inc()

    // Observe duration
    duration := rand.Float64()
    requestDuration.WithLabelValues(endpoint).Observe(duration)
}

func main() {
    // Start metrics collector
    go func() {
        for {
            collectSystemMetrics()
            simulateApplicationMetrics()
            time.Sleep(5 * time.Second)
        }
    }()

    // Expose metrics endpoint
    http.Handle("/metrics", promhttp.Handler())
    log.Println("Custom exporter running on :8080/metrics")
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

---

## Storage and Retention

### Local Storage

**TSDB Storage**
- Append-only time-series database
- 2-hour blocks with compression
- Automatic compaction (merges small blocks)
- Write-ahead log (WAL) for durability

**Configuration**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  external_labels:
    cluster: 'production'

# Storage retention
storage:
  tsdb:
    path: /var/lib/prometheus
    retention.time: 15d         # Keep 15 days (default)
    retention.size: 50GB        # Max 50 GB
    wal-compression: true       # Compress WAL (recommended)
```

**Command-Line Flags**
```bash
prometheus \
  --storage.tsdb.path=/var/lib/prometheus \
  --storage.tsdb.retention.time=30d \
  --storage.tsdb.retention.size=100GB \
  --storage.tsdb.wal-compression
```

**Storage Size Estimation**
```
Storage Size = Scrape Frequency × Retention Time × Series Count × Sample Size

Example:
  Scrape: 15s (4 samples/minute)
  Retention: 15 days
  Series: 100,000
  Sample Size: ~2 bytes (compressed)

  Size = (4 samples/min) × (60 min/hr) × (24 hr/day) × (15 days) × (100,000 series) × (2 bytes)
       = 1,036,800,000,000 bytes
       ≈ 1 TB
```

**Reducing Storage**:
- Reduce retention time
- Reduce scrape frequency (15s → 30s)
- Reduce cardinality (fewer label combinations)
- Use recording rules to aggregate
- Use remote storage for long-term retention

### Remote Write

**Purpose**: Send metrics to remote storage for long-term retention

**Configuration**
```yaml
# prometheus.yml
remote_write:
  - url: "https://remote-storage.example.com/api/v1/write"
    basic_auth:
      username: prometheus
      password: secret
    write_relabel_configs:
      # Only send specific metrics
      - source_labels: [__name__]
        regex: 'api:.*'  # Only recording rules
        action: keep
    queue_config:
      capacity: 10000
      max_shards: 50
      min_shards: 1
      max_samples_per_send: 1000
      batch_send_deadline: 5s
      min_backoff: 30ms
      max_backoff: 100ms
```

**Popular Remote Storage Options**:
- **Thanos**: Long-term storage on object storage (S3, GCS)
- **Cortex**: Multi-tenant Prometheus as a Service
- **VictoriaMetrics**: High-performance TSDB
- **Grafana Mimir**: Horizontally scalable TSDB
- **InfluxDB**: Time-series database with Prometheus remote write

### Remote Read

**Purpose**: Query metrics from remote storage

**Configuration**
```yaml
# prometheus.yml
remote_read:
  - url: "https://remote-storage.example.com/api/v1/read"
    basic_auth:
      username: prometheus
      password: secret
    read_recent: true  # Read recent data locally, old data remotely
```

---

## Federation

### Purpose

**Federation**: Hierarchical Prometheus setup where parent Prometheus scrapes aggregated metrics from child instances

**Use Cases**:
- **Hierarchical Monitoring**: Regional Prometheus → Global Prometheus
- **Cross-Cluster**: Aggregate metrics from multiple clusters
- **Long-Term Storage**: Federate aggregated metrics to central instance
- **Multi-Tenancy**: Separate Prometheus per tenant, federate to central

### Configuration

**Child Prometheus** (Regional)
```yaml
# prometheus-us-east.yml
global:
  scrape_interval: 15s
  external_labels:
    cluster: 'us-east-1'
    region: 'us-east'

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['node1:9100', 'node2:9100']

  - job_name: 'api-server'
    static_configs:
      - targets: ['api1:8080', 'api2:8080']
```

**Parent Prometheus** (Global)
```yaml
# prometheus-global.yml
global:
  scrape_interval: 30s  # Less frequent scraping
  external_labels:
    environment: 'production'

scrape_configs:
  # Federate from us-east Prometheus
  - job_name: 'federate-us-east'
    scrape_interval: 30s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="api-server"}'               # All api-server metrics
        - '{__name__=~"api:.*"}'              # All recording rules starting with api:
        - '{__name__=~".*:rate5m"}'           # All rate5m recording rules
    static_configs:
      - targets:
          - 'prometheus-us-east:9090'
    relabel_configs:
      - source_labels: [__address__]
        target_label: prometheus_instance

  # Federate from eu-west Prometheus
  - job_name: 'federate-eu-west'
    scrape_interval: 30s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="api-server"}'
        - '{__name__=~"api:.*"}'
    static_configs:
      - targets:
          - 'prometheus-eu-west:9090'
    relabel_configs:
      - source_labels: [__address__]
        target_label: prometheus_instance
```

**Honor Labels**:
- `honor_labels: true`: Preserve labels from federated instance
- `honor_labels: false`: Parent Prometheus labels take precedence

**Match Expressions**:
```yaml
params:
  'match[]':
    # Match specific job
    - '{job="api-server"}'

    # Match all recording rules
    - '{__name__=~".*:.*"}'

    # Match specific metric patterns
    - '{__name__=~"http_.*"}'
    - '{__name__=~"node_.*"}'

    # Match all metrics from specific instance
    - '{instance="host1:9100"}'

    # Combine multiple selectors
    - '{job="api-server",status=~"5.."}'
```

### Best Practices

**DO**:
- Federate aggregated metrics (recording rules), not raw metrics
- Use longer scrape intervals for federation (30s-1m)
- Set `honor_labels: true` to preserve source labels
- Use specific match expressions (avoid `{__name__=~".*"}`)
- Add `prometheus_instance` label to identify source

**DON'T**:
- Federate all metrics (creates massive overhead)
- Scrape federations too frequently (causes load)
- Create circular federation (Prometheus A → B → A)
- Federate high-cardinality metrics without aggregation

---

## Cardinality Management

### Understanding Cardinality

**Cardinality**: Number of unique time series (metric name + unique label combinations)

**Example**:
```
Metric: http_requests_total
Labels: method (4 values), endpoint (20 values), status (5 values)
Cardinality: 1 × 4 × 20 × 5 = 400 time series
```

**High Cardinality Example**:
```
Metric: http_requests_total
Labels: method, endpoint, status, user_id (1M values)
Cardinality: 1 × 4 × 20 × 5 × 1,000,000 = 400,000,000 time series!
```

### Measuring Cardinality

**Total Time Series**
```promql
# Total active time series
sum(scrape_samples_scraped)

# Time series per job
sum by (job) (scrape_samples_scraped)
```

**Top Metrics by Cardinality**
```promql
# Top 10 metrics by cardinality
topk(10, count by (__name__) ({__name__=~".+"}))

# Cardinality by metric and job
count by (__name__, job) ({__name__=~".+"}))
```

**Label Cardinality**
```promql
# Unique values per label
count_values("value", label_name)

# Unique instances
count(count by (instance) ({__name__=~".+"}))
```

### Reducing Cardinality

**1. Remove High-Cardinality Labels**
```python
# BAD: User ID has millions of values
http_requests_total = Counter(
    'http_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status', 'user_id']  # REMOVE user_id!
)

# GOOD: Only low-cardinality labels
http_requests_total = Counter(
    'http_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)
```

**2. Template URL Paths**
```python
# BAD: Full URL with parameters
http_requests_total.labels(endpoint="/api/users/12345/orders/67890").inc()

# GOOD: Template the path
http_requests_total.labels(endpoint="/api/users/:id/orders/:order_id").inc()
```

**3. Drop Labels via Relabeling**
```yaml
scrape_configs:
  - job_name: 'api-server'
    static_configs:
      - targets: ['localhost:8080']
    relabel_configs:
      # Drop high-cardinality labels
      - action: labeldrop
        regex: 'user_id|trace_id|request_id'
```

**4. Use Recording Rules for Aggregation**
```yaml
# Aggregate away high-cardinality labels
- record: job:http_requests:rate5m
  expr: |
    sum by (job, endpoint, status) (
      rate(http_requests_total[5m])
    )
```

**5. Increase Scrape Interval**
```yaml
# Scrape less frequently for high-cardinality targets
scrape_configs:
  - job_name: 'high-cardinality-job'
    scrape_interval: 1m  # Instead of 15s
```

**6. Use Histograms Instead of Labels**
```python
# BAD: Response size as label (unbounded values)
http_response_size = Counter(
    'http_response_size_total',
    'Response sizes',
    ['size']  # Millions of unique sizes!
)

# GOOD: Use histogram with buckets
http_response_size = Histogram(
    'http_response_size_bytes',
    'Response size distribution',
    buckets=[100, 1000, 10000, 100000, 1000000]
)
```

### Cardinality Limits

**Prometheus Configuration**
```yaml
# prometheus.yml
global:
  # Limit samples per scrape (prevents cardinality explosion)
  sample_limit: 10000  # Default: unlimited

scrape_configs:
  - job_name: 'api-server'
    sample_limit: 5000  # Per-target limit
    label_limit: 50     # Max labels per metric
    label_name_length_limit: 100   # Max label name length
    label_value_length_limit: 200  # Max label value length
```

---

## Performance Optimization

### Query Optimization

**1. Use Recording Rules**
```promql
# SLOW: Complex query repeated everywhere
histogram_quantile(0.95,
  sum by (job, endpoint, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)

# FAST: Precomputed recording rule
job:http_latency:p95:by_endpoint
```

**2. Limit Time Range**
```promql
# SLOW: Query 30 days of data
rate(http_requests_total[30d])

# FAST: Query 5 minutes
rate(http_requests_total[5m])
```

**3. Filter Early**
```promql
# SLOW: Aggregate then filter
sum(rate(http_requests_total[5m])) by (endpoint) > 100

# FAST: Filter then aggregate
sum(rate(http_requests_total{status="200"}[5m])) by (endpoint)
```

**4. Avoid Regex When Possible**
```promql
# SLOWER: Regex matching
http_requests_total{status=~"2.."}

# FASTER: Exact matching (if possible)
http_requests_total{status="200"}
```

**5. Use `rate()` Instead of `increase()`**
```promql
# SLOWER: increase() then divide
increase(http_requests_total[5m]) / 300

# FASTER: rate() (built-in per-second calculation)
rate(http_requests_total[5m])
```

### Scrape Optimization

**1. Reduce Scrape Frequency**
```yaml
global:
  scrape_interval: 30s  # Instead of 15s (reduces load by 50%)
```

**2. Use Longer Evaluation Intervals**
```yaml
global:
  evaluation_interval: 30s  # For recording and alerting rules
```

**3. Limit Scrape Targets**
```yaml
scrape_configs:
  - job_name: 'node'
    sample_limit: 10000  # Drop targets exceeding limit
```

**4. Use HTTP Compression**
```yaml
scrape_configs:
  - job_name: 'api-server'
    metric_relabel_configs:
      - action: labeldrop
        regex: 'unnecessary_label'
```

### Storage Optimization

**1. Enable WAL Compression**
```bash
prometheus \
  --storage.tsdb.wal-compression
```

**2. Tune Retention**
```bash
prometheus \
  --storage.tsdb.retention.time=15d \  # Shorter retention
  --storage.tsdb.retention.size=50GB   # Size-based limit
```

**3. Use Remote Write for Aggregates**
```yaml
remote_write:
  - url: "https://long-term-storage.example.com/write"
    write_relabel_configs:
      # Only send aggregated metrics
      - source_labels: [__name__]
        regex: '.*:.*'  # Recording rules
        action: keep
```

**4. Reduce Cardinality**
- Drop high-cardinality labels
- Use recording rules for aggregation
- Template URL paths
- Limit label values

### Resource Sizing

**Memory Estimation**
```
Memory = Series Count × 2 KB

Example:
  100,000 series × 2 KB = 200 MB
  1,000,000 series × 2 KB = 2 GB
  10,000,000 series × 2 KB = 20 GB
```

**Recommended Resources**:
- **Small**: 100K series → 2 GB RAM, 2 CPUs
- **Medium**: 1M series → 8 GB RAM, 4 CPUs
- **Large**: 10M series → 32 GB RAM, 8 CPUs

**Monitoring Prometheus Itself**
```promql
# Memory usage
process_resident_memory_bytes

# Time series count
prometheus_tsdb_symbol_table_size_bytes

# Ingestion rate
rate(prometheus_tsdb_head_samples_appended_total[5m])

# Query duration
prometheus_engine_query_duration_seconds

# Scrape duration
scrape_duration_seconds
```

---

## High Availability

### Strategies

**1. Simple HA: Redundant Prometheus Instances**
- Run 2+ identical Prometheus instances
- Each scrapes the same targets independently
- Load balancer distributes queries
- Alertmanager deduplicates alerts

**Pros**: Simple, no coordination needed
**Cons**: Duplicate storage, no horizontal scaling

**2. Prometheus Federation**
- Regional Prometheus instances
- Global Prometheus federates aggregates
- Hierarchical structure

**Pros**: Scales to many targets, regional isolation
**Cons**: Added complexity, potential data loss if regional instance down

**3. Thanos / Cortex / Mimir**
- Purpose-built HA solutions
- Object storage for long-term retention
- Global query view
- Horizontal scaling

**Pros**: Full HA, long-term storage, global view
**Cons**: Complex setup, additional components

### Simple HA Setup

**Prometheus Instance 1**
```yaml
# prometheus-1.yml
global:
  external_labels:
    replica: 'prometheus-1'

scrape_configs:
  - job_name: 'api-server'
    static_configs:
      - targets: ['api1:8080', 'api2:8080']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

**Prometheus Instance 2**
```yaml
# prometheus-2.yml
global:
  external_labels:
    replica: 'prometheus-2'

# Same scrape configs as prometheus-1
scrape_configs:
  - job_name: 'api-server'
    static_configs:
      - targets: ['api1:8080', 'api2:8080']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

**Alertmanager Configuration** (deduplication)
```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'team-notifications'

# Deduplication based on labels
inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
```

**Query Load Balancer**
```nginx
upstream prometheus {
    server prometheus-1:9090;
    server prometheus-2:9090;
}

server {
    listen 9090;
    location / {
        proxy_pass http://prometheus;
    }
}
```

---

## Integration with Grafana

### Data Source Configuration

**Add Prometheus Data Source**
1. Grafana → Configuration → Data Sources → Add data source
2. Select "Prometheus"
3. URL: `http://prometheus:9090`
4. Access: Server (default) or Browser
5. Save & Test

**Advanced Settings**
```yaml
# HTTP Method: POST (for complex queries)
# Timeout: 60s
# Custom Query Parameters: step=15s
```

### Dashboard Creation

**Query Examples**
```promql
# Request rate
sum(rate(http_requests_total[5m])) by (endpoint)

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m]))
/ sum(rate(http_requests_total[5m]))

# Latency percentiles
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# CPU usage
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))
```

**Panel Types**:
- **Graph**: Time-series data
- **Stat**: Single value with sparkline
- **Gauge**: Percentage or threshold
- **Table**: Tabular data
- **Heatmap**: Histogram over time
- **Alert List**: Active alerts

**Variables**
```
# Job variable
Name: job
Query: label_values(up, job)

# Instance variable
Name: instance
Query: label_values(up{job="$job"}, instance)

# Endpoint variable
Name: endpoint
Query: label_values(http_requests_total, endpoint)
```

**Templated Query**
```promql
rate(http_requests_total{job="$job", instance="$instance", endpoint="$endpoint"}[5m])
```

---

## Integration with Alertmanager

### Alertmanager Configuration

**Basic Configuration**
```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alertmanager@example.com'
  smtp_auth_username: 'alerts'
  smtp_auth_password: 'password'

# Route tree
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s        # Wait before sending first alert
  group_interval: 10s    # Wait before sending batch
  repeat_interval: 12h   # Resend interval for firing alerts

  receiver: 'default'

  routes:
    # Critical alerts to PagerDuty
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true

    # Warnings to Slack
    - match:
        severity: warning
      receiver: 'slack'

    # Database alerts to DBA team
    - match:
        team: dba
      receiver: 'dba-team'

receivers:
  - name: 'default'
    email_configs:
      - to: 'team@example.com'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'your-pagerduty-key'
        description: '{{ .GroupLabels.alertname }}'

  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
        title: 'Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'dba-team'
    email_configs:
      - to: 'dba-team@example.com'

# Inhibition rules (suppress alerts)
inhibit_rules:
  # Suppress warnings if critical firing
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']

  # Suppress instance alerts if whole cluster down
  - source_match:
      alertname: 'ClusterDown'
    target_match_re:
      alertname: '.*'
    equal: ['cluster']
```

### Notification Templates

**Custom Templates**
```yaml
# templates/slack.tmpl
{{ define "slack.title" }}
[{{ .Status | toUpper }}{{ if eq .Status "firing" }}:{{ .Alerts.Firing | len }}{{ end }}]
{{ .GroupLabels.alertname }}
{{ end }}

{{ define "slack.text" }}
{{ range .Alerts }}
*Alert:* {{ .Labels.alertname }}
*Severity:* {{ .Labels.severity }}
*Description:* {{ .Annotations.description }}
*Instance:* {{ .Labels.instance }}
{{ end }}
{{ end }}
```

**Use Template**
```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
        title: '{{ template "slack.title" . }}'
        text: '{{ template "slack.text" . }}'

templates:
  - '/etc/alertmanager/templates/*.tmpl'
```

---

## Production Best Practices

### Metric Naming
- Use `snake_case` for metric names
- Include units in name (`_seconds`, `_bytes`, `_total`)
- Use consistent prefixes (namespace)
- Suffix counters with `_total`

### Label Best Practices
- Keep cardinality low (< 100 unique values per label)
- Avoid user IDs, trace IDs, UUIDs
- Use consistent label names across metrics
- Template URL paths (`/api/users/:id`)

### Recording Rules
- Precompute expensive queries
- Use hierarchical aggregation (instance → job → cluster)
- Follow naming convention: `level:metric:operations`
- Evaluate at 30s or 1m intervals

### Alerting Rules
- Alert on symptoms, not causes
- Use `for` clause to avoid flapping (5m-10m)
- Include severity labels (critical, warning)
- Add actionable annotations
- Test alerts before deploying

### Storage
- Enable WAL compression
- Set appropriate retention (15d-30d)
- Use remote write for long-term storage
- Monitor storage usage

### Performance
- Limit cardinality
- Use recording rules for expensive queries
- Tune scrape intervals (15s-30s)
- Enable query logging for slow queries

### High Availability
- Run multiple Prometheus instances
- Use Alertmanager for deduplication
- Consider Thanos/Cortex for scale
- Monitor Prometheus itself

---

## Troubleshooting

### High Cardinality

**Symptoms**:
- High memory usage
- Slow queries
- Storage filling up quickly

**Diagnosis**:
```promql
# Top metrics by cardinality
topk(10, count by (__name__) ({__name__=~".+"}))

# Cardinality by job
sum by (job) (scrape_samples_scraped)

# Label cardinality
count_values("value", label_name)
```

**Solutions**:
- Remove high-cardinality labels
- Template URL paths
- Drop unnecessary labels via relabeling
- Use histograms instead of labels
- Increase scrape interval

### Slow Queries

**Symptoms**:
- Query timeouts
- High CPU usage
- Dashboards loading slowly

**Diagnosis**:
```promql
# Query duration
topk(10, prometheus_engine_query_duration_seconds{quantile="0.99"})

# Slow queries (enable with --query.log-file)
# Check query log file
```

**Solutions**:
- Use recording rules
- Reduce time range
- Filter early in query
- Avoid regex when possible
- Limit query concurrency

### Scrape Failures

**Symptoms**:
- `up == 0`
- Missing metrics
- Gaps in data

**Diagnosis**:
```promql
# Check target status
up

# Scrape duration
scrape_duration_seconds

# Scrape errors
up == 0
```

**Solutions**:
- Check network connectivity
- Verify target is exposing metrics
- Check Prometheus logs
- Increase scrape timeout
- Verify relabeling config

### Memory Issues

**Symptoms**:
- OOMKilled
- High memory usage
- Swapping

**Diagnosis**:
```promql
# Process memory
process_resident_memory_bytes

# Time series count
prometheus_tsdb_symbol_table_size_bytes
```

**Solutions**:
- Reduce cardinality
- Reduce retention time
- Increase memory allocation
- Use remote write
- Reduce scrape targets

### Missing Metrics

**Symptoms**:
- Expected metrics not present
- Query returns no data

**Diagnosis**:
```promql
# Check if metric exists
{__name__=~"expected_metric.*"}

# Check target status
up{job="expected-job"}
```

**Solutions**:
- Verify target is scraped
- Check relabeling config (labels might be dropped)
- Verify metric name spelling
- Check sample limit
- Review metric_relabel_configs

---

## References

### Official Documentation
- Prometheus Docs: https://prometheus.io/docs/
- PromQL: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Alerting: https://prometheus.io/docs/alerting/latest/
- Exporters: https://prometheus.io/docs/instrumenting/exporters/

### Specifications
- OpenMetrics: https://openmetrics.io/
- Prometheus Text Format: https://prometheus.io/docs/instrumenting/exposition_formats/

### Tools
- PromLens: https://promlens.com/ (PromQL query builder)
- Promtool: https://prometheus.io/docs/prometheus/latest/command-line/promtool/
- Thanos: https://thanos.io/
- Cortex: https://cortexmetrics.io/
- VictoriaMetrics: https://victoriametrics.com/

### Books
- "Prometheus: Up & Running" by Brian Brazil
- "Monitoring with Prometheus" by James Turnbull

---

**End of Prometheus Monitoring Reference**
