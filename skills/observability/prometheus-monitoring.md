---
name: observability-prometheus-monitoring
description: Production-ready Prometheus monitoring and alerting
---



# Prometheus Monitoring

**Scope**: Prometheus, PromQL, recording rules, alerting rules, exporters, service discovery, federation

**Lines**: 650

**Last Updated**: 2025-10-27

---

## When to Use This Skill

Use this skill when:
- Setting up Prometheus for infrastructure or application monitoring
- Writing PromQL queries for metrics analysis
- Configuring recording rules for query optimization
- Creating alerting rules for proactive monitoring
- Implementing custom exporters for application metrics
- Configuring service discovery for dynamic environments
- Setting up Prometheus federation for multi-cluster monitoring
- Optimizing Prometheus performance and storage
- Debugging high cardinality issues
- Integrating Prometheus with Grafana or Alertmanager

**Don't use** for:
- Log aggregation (use Loki or ELK instead)
- Distributed tracing (use Jaeger or Tempo instead)
- APM with transaction profiling (use dedicated APM tools)

---

## Core Concepts

### Prometheus Architecture

**Pull-Based Model**: Prometheus scrapes metrics from targets
- Targets expose metrics at HTTP endpoints (typically `/metrics`)
- Prometheus pulls metrics at configured intervals (default: 15s)
- Targets discovered via static config or service discovery
- Pushgateway available for batch jobs that can't be scraped

**Components**:
- **Prometheus Server**: Time-series database + query engine
- **Exporters**: Expose metrics from third-party systems
- **Alertmanager**: Handle alerts (deduplication, grouping, routing)
- **Pushgateway**: Receive metrics from short-lived jobs
- **Client Libraries**: Instrument applications

### Data Model

**Metrics**: Named time series with key-value labels
```
http_requests_total{method="GET", endpoint="/api/users", status="200"} 1234
|                  |                                                    |
metric name        labels (dimensions)                               value
```

**Metric Types**:
1. **Counter**: Monotonically increasing (requests, errors, bytes)
2. **Gauge**: Can go up/down (temperature, memory, active connections)
3. **Histogram**: Distribution in buckets (latency, request size)
4. **Summary**: Similar to histogram, client-side quantiles

### PromQL Basics

**Selectors**:
```promql
# Instant vector (one value per series at query time)
http_requests_total

# Filter by labels
http_requests_total{status="200", method="GET"}

# Regex matching
http_requests_total{status=~"2.."}

# Negative matching
http_requests_total{status!="200"}

# Range vector (values over time window)
http_requests_total[5m]
```

**Functions**:
```promql
# Rate: per-second average rate over time window
rate(http_requests_total[5m])

# Increase: total increase over time window
increase(http_requests_total[1h])

# Sum: aggregate across labels
sum(http_requests_total)

# Sum by label (keeps label)
sum by (status) (http_requests_total)

# Histogram quantile (percentile from histogram)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

---

## Patterns

### Pattern 1: Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'production'
    region: 'us-east-1'

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - localhost:9093

# Load rules
rule_files:
  - "rules/*.yml"
  - "alerts/*.yml"

# Scrape configurations
scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node exporter (system metrics)
  - job_name: 'node'
    static_configs:
      - targets:
          - 'node1:9100'
          - 'node2:9100'
    relabel_configs:
      - source_labels: [__address__]
        regex: '([^:]+):\d+'
        target_label: instance
        replacement: '${1}'

  # Kubernetes service discovery
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__

  # Consul service discovery
  - job_name: 'consul-services'
    consul_sd_configs:
      - server: 'localhost:8500'
    relabel_configs:
      - source_labels: [__meta_consul_service]
        target_label: job

  # File-based service discovery
  - job_name: 'file-sd'
    file_sd_configs:
      - files:
          - 'targets/*.json'
          - 'targets/*.yml'
        refresh_interval: 30s
```

### Pattern 2: Recording Rules

```yaml
# rules/recording-rules.yml
groups:
  - name: api_performance
    interval: 30s
    rules:
      # Precompute request rate per endpoint
      - record: api:http_requests:rate5m
        expr: |
          sum by (job, endpoint, method) (
            rate(http_requests_total[5m])
          )

      # Precompute error rate percentage
      - record: api:http_errors:rate5m
        expr: |
          sum by (job, endpoint) (
            rate(http_requests_total{status=~"5.."}[5m])
          ) / sum by (job, endpoint) (
            rate(http_requests_total[5m])
          ) * 100

      # Precompute latency percentiles
      - record: api:http_latency:p95
        expr: |
          histogram_quantile(0.95,
            sum by (job, endpoint, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )

      - record: api:http_latency:p99
        expr: |
          histogram_quantile(0.99,
            sum by (job, endpoint, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )

  - name: resource_utilization
    interval: 30s
    rules:
      # CPU utilization percentage
      - record: node:cpu:utilization
        expr: |
          100 - (avg by (instance) (
            rate(node_cpu_seconds_total{mode="idle"}[5m])
          ) * 100)

      # Memory utilization percentage
      - record: node:memory:utilization
        expr: |
          100 * (1 - (
            node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
          ))

      # Disk utilization percentage
      - record: node:disk:utilization
        expr: |
          100 - (
            node_filesystem_avail_bytes / node_filesystem_size_bytes * 100
          )
```

### Pattern 3: Alerting Rules

```yaml
# alerts/alerting-rules.yml
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
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "{{ $labels.instance }} has been down for more than 1 minute"

      # High error rate
      - alert: HighErrorRate
        expr: |
          sum by (job, endpoint) (
            rate(http_requests_total{status=~"5.."}[5m])
          ) / sum by (job, endpoint) (
            rate(http_requests_total[5m])
          ) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.job }}/{{ $labels.endpoint }}"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            sum by (job, endpoint, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          ) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High p95 latency on {{ $labels.job }}/{{ $labels.endpoint }}"
          description: "p95 latency is {{ $value }}s"

  - name: resource_alerts
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
          description: "CPU usage is {{ $value }}%"

      # High memory usage
      - alert: HighMemory
        expr: |
          100 * (1 - (
            node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
          )) > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory on {{ $labels.instance }}"
          description: "Memory usage is {{ $value }}%"

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
          description: "Disk {{ $labels.device }} is {{ $value }}% full"
```

### Pattern 4: Custom Exporter (Python)

```python
#!/usr/bin/env python3
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import time
import random

# Define metrics
app_status = Gauge('app_status', 'Application status', ['app_name'])
requests_total = Counter('requests_total', 'Total requests', ['endpoint', 'status'])
request_duration = Histogram(
    'request_duration_seconds',
    'Request duration',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0]
)
queue_size = Gauge('queue_size', 'Current queue size', ['queue_name'])
active_connections = Gauge('active_connections', 'Active connections')

def collect_metrics():
    """Collect application metrics."""
    # Update status metrics
    app_status.labels(app_name='api-server').set(1)  # 1 = healthy

    # Simulate request metrics
    endpoints = ['/api/users', '/api/orders', '/api/products']
    statuses = ['200', '404', '500']

    for endpoint in endpoints:
        status = random.choice(statuses)
        requests_total.labels(endpoint=endpoint, status=status).inc()

        duration = random.uniform(0.01, 1.0)
        request_duration.labels(endpoint=endpoint).observe(duration)

    # Update gauge metrics
    queue_size.labels(queue_name='tasks').set(random.randint(0, 100))
    active_connections.set(random.randint(10, 500))

if __name__ == '__main__':
    # Start HTTP server for metrics endpoint
    start_http_server(8080)
    print("Exporter running on :8080/metrics")

    # Collect metrics periodically
    while True:
        collect_metrics()
        time.sleep(5)
```

### Pattern 5: Custom Exporter (Go)

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
)

var (
    appStatus = promauto.NewGaugeVec(
        prometheus.GaugeOpts{
            Name: "app_status",
            Help: "Application status",
        },
        []string{"app_name"},
    )

    requestsTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "requests_total",
            Help: "Total requests",
        },
        []string{"endpoint", "status"},
    )

    requestDuration = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "request_duration_seconds",
            Help:    "Request duration",
            Buckets: []float64{0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0},
        },
        []string{"endpoint"},
    )

    queueSize = promauto.NewGaugeVec(
        prometheus.GaugeOpts{
            Name: "queue_size",
            Help: "Current queue size",
        },
        []string{"queue_name"},
    )

    activeConnections = promauto.NewGauge(
        prometheus.GaugeOpts{
            Name: "active_connections",
            Help: "Active connections",
        },
    )
)

func collectMetrics() {
    endpoints := []string{"/api/users", "/api/orders", "/api/products"}
    statuses := []string{"200", "404", "500"}

    for {
        // Update status
        appStatus.WithLabelValues("api-server").Set(1)

        // Simulate requests
        for _, endpoint := range endpoints {
            status := statuses[rand.Intn(len(statuses))]
            requestsTotal.WithLabelValues(endpoint, status).Inc()

            duration := rand.Float64()
            requestDuration.WithLabelValues(endpoint).Observe(duration)
        }

        // Update gauges
        queueSize.WithLabelValues("tasks").Set(float64(rand.Intn(100)))
        activeConnections.Set(float64(rand.Intn(490) + 10))

        time.Sleep(5 * time.Second)
    }
}

func main() {
    // Start metrics collector
    go collectMetrics()

    // Expose metrics endpoint
    http.Handle("/metrics", promhttp.Handler())
    log.Println("Exporter running on :8080/metrics")
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

### Pattern 6: Federation

```yaml
# prometheus.yml (central Prometheus)
scrape_configs:
  # Federate from regional Prometheus instances
  - job_name: 'federate-us-east'
    scrape_interval: 30s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="api-server"}'
        - '{__name__=~"api:.*"}'  # Aggregated metrics
    static_configs:
      - targets:
          - 'prometheus-us-east:9090'

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
```

---

## Quick Reference

### PromQL Operators

```promql
# Arithmetic
metric1 + metric2
metric1 - metric2
metric1 * metric2
metric1 / metric2
metric1 % metric2
metric1 ^ metric2

# Comparison (returns 0 or 1)
metric1 == metric2
metric1 != metric2
metric1 > metric2
metric1 < metric2
metric1 >= metric2
metric1 <= metric2

# Logical (on boolean results)
metric1 and metric2
metric1 or metric2
metric1 unless metric2
```

### Aggregation Functions

```promql
sum(metric) by (label)           # Sum
avg(metric) by (label)           # Average
min(metric) by (label)           # Minimum
max(metric) by (label)           # Maximum
count(metric) by (label)         # Count
stddev(metric) by (label)        # Standard deviation
stdvar(metric) by (label)        # Variance
topk(5, metric)                  # Top 5 values
bottomk(5, metric)               # Bottom 5 values
count_values("label", metric)    # Count unique values
```

### Time Functions

```promql
rate(metric[5m])                 # Per-second rate
irate(metric[5m])                # Instant rate
increase(metric[1h])             # Total increase
delta(metric[1h])                # Difference (for gauges)
idelta(metric[5m])               # Instant delta
deriv(metric[5m])                # Per-second derivative
predict_linear(metric[1h], 3600) # Predict 1h ahead
```

### Label Manipulation

```promql
# Keep only specific labels
label_replace(metric, "new", "$1", "old", "(.*)")

# Join metrics
metric1 * on(label) metric2

# Group left/right
metric1 * on(label) group_left(extra) metric2
```

---

## Anti-Patterns

### High Cardinality Labels

```yaml
# WRONG: User ID creates millions of time series
http_requests{user_id="user_12345"}

# CORRECT: Use low-cardinality labels
http_requests{endpoint="/api/users", status="200"}
```

### Unbounded Label Values

```yaml
# WRONG: URL path with parameters
http_requests{path="/api/users/12345/orders/67890"}

# CORRECT: Template the path
http_requests{endpoint="/api/users/:id/orders/:order_id"}
```

### Missing Recording Rules

```promql
# WRONG: Complex query repeated in every dashboard
histogram_quantile(0.95,
  sum by (job, endpoint, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)

# CORRECT: Create recording rule
- record: api:http_latency:p95
  expr: histogram_quantile(0.95, ...)
```

### Inefficient Queries

```promql
# WRONG: Aggregation after filtering
sum(rate(metric[5m])) by (label1, label2) > 0

# CORRECT: Filter before aggregation
sum(rate(metric[5m])) by (label1, label2) > 0
```

---

## Level 3: Resources

This skill has **Level 3 Resources** available with comprehensive reference material, production-ready scripts, and runnable examples.

### Resource Structure

```
prometheus-monitoring/resources/
├── REFERENCE.md                    # Comprehensive reference (3,200 lines)
│   ├── Prometheus architecture and components
│   ├── Complete PromQL reference with examples
│   ├── Recording rules patterns and best practices
│   ├── Alerting rules with severity levels
│   ├── Service discovery configurations
│   ├── Federation and high availability
│   ├── Storage configuration and retention
│   ├── Cardinality management
│   ├── Performance optimization
│   └── Production troubleshooting
│
├── scripts/                        # Production-ready tools
│   ├── analyze_metrics.py          # Metrics and config analyzer
│   ├── validate_promql.py          # PromQL query validator
│   └── test_exporter.sh            # Exporter testing tool
│
└── examples/                       # Runnable examples
    ├── config/
    │   └── prometheus.yml          # Complete Prometheus config
    ├── rules/
    │   ├── recording-rules.yml     # Recording rules examples
    │   └── alert-rules.yml         # Alerting rules examples
    ├── exporters/
    │   ├── custom-exporter.py      # Python custom exporter
    │   └── custom-exporter.go      # Go custom exporter
    ├── queries/
    │   └── promql-examples.txt     # Common PromQL patterns
    ├── docker/
    │   └── docker-compose.yml      # Full monitoring stack
    └── python/
        └── metrics-client.py       # Application instrumentation
```

### Key Resources

**REFERENCE.md** (3,200 lines): Comprehensive guide covering:
- Prometheus architecture and data model
- Complete PromQL reference with 100+ query examples
- Recording rules for performance optimization
- Alerting rules with best practices
- All service discovery mechanisms (Kubernetes, Consul, EC2, file)
- Federation for multi-cluster setups
- Remote write and remote read configurations
- Storage optimization and retention policies
- Cardinality management techniques
- Performance tuning and troubleshooting
- Integration with Grafana and Alertmanager
- Production deployment patterns

**analyze_metrics.py**: Production-ready analyzer
- Parses prometheus.yml configuration
- Analyzes metric cardinality from Prometheus API
- Detects high-cardinality labels
- Identifies anti-patterns (naming, labeling)
- Validates recording and alerting rules
- Provides optimization recommendations
- Example: `analyze_metrics.py --config prometheus.yml --json`

**validate_promql.py**: PromQL validator
- Validates PromQL syntax
- Tests queries against Prometheus API
- Checks for common anti-patterns
- Measures query performance
- Suggests optimizations
- Example: `validate_promql.py --query 'rate(http_requests_total[5m])' --json`

**test_exporter.sh**: Exporter testing tool
- Tests metrics endpoints
- Validates Prometheus text format
- Checks metric naming conventions
- Identifies cardinality issues
- Validates HELP and TYPE annotations
- Example: `test_exporter.sh --endpoint http://localhost:9090/metrics --json`

**Runnable Examples**:
- Complete Prometheus configuration with all features
- Recording rules and alerting rules
- Custom exporters in Python and Go
- 50+ PromQL query examples
- Docker Compose stack (Prometheus + Grafana + Alertmanager + Node Exporter)
- Application instrumentation example

### Usage

```bash
# Access comprehensive reference
cat prometheus-monitoring/resources/REFERENCE.md

# Analyze Prometheus configuration and metrics
./scripts/analyze_metrics.py --config prometheus.yml --metrics-endpoint http://localhost:9090

# Validate PromQL queries
./scripts/validate_promql.py --query 'sum(rate(http_requests_total[5m]))' --json

# Test custom exporter
./scripts/test_exporter.sh --endpoint http://localhost:8080/metrics

# Run full monitoring stack
cd examples/docker
docker-compose up -d
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
# Alertmanager: http://localhost:9093

# Run custom exporter
cd examples/exporters
python3 custom-exporter.py
# Metrics at http://localhost:8080/metrics
```

### When to Use Level 3 Resources

Use these resources when:
- Setting up Prometheus for production environments
- Writing complex PromQL queries
- Optimizing Prometheus performance
- Debugging high cardinality issues
- Creating recording and alerting rules
- Implementing custom exporters
- Configuring service discovery
- Setting up federation or remote storage
- Training team on Prometheus best practices
- Troubleshooting Prometheus issues

---

## Related Skills

- **metrics-instrumentation.md** - Instrumenting applications with Prometheus
- **distributed-tracing.md** - Complementary distributed tracing
- **alerting-strategy.md** - Advanced alerting patterns
- **dashboard-design.md** - Visualizing Prometheus data in Grafana

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
**Level 3 Resources**: Available
