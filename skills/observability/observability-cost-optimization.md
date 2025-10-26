---
name: observability-cost-optimization
description: Optimizing observability costs through sampling, cardinality management, and retention strategies
---

# Observability Cost Optimization

**Scope**: Cardinality management, sampling strategies, log reduction, metrics aggregation, retention policies, OTel Collector cost reduction

**Lines**: 420

**Last Updated**: 2025-10-26

---

## When to Use This Skill

Use this skill when:
- Observability costs are growing faster than infrastructure costs
- Experiencing cardinality explosion in metrics or traces
- Need to reduce log ingestion volume without losing critical data
- Implementing sampling strategies for high-traffic systems
- Optimizing retention policies for traces, metrics, and logs
- Configuring OTel Collector processors for cost reduction
- Balancing observability coverage with budget constraints

**Don't use** for:
- Initial observability setup (implement first, optimize later)
- Low-traffic systems (<1000 req/sec)
- Systems where observability budget is unconstrained

**Context (2024-2025)**:
- **50%+ of teams** cite cost as biggest observability challenge (CNCF survey)
- **Average 30-40% cost reduction** achievable with proper sampling
- **Cardinality is #1 cost driver** for metrics-based systems
- **Logs account for 60-70%** of total observability costs

---

## Core Concepts

### Cost Drivers

**1. Cardinality** (Metrics/Traces)
- Number of unique time series (metric + unique label combinations)
- Example: `http_requests_total{method="GET", endpoint="/api/users", status="200"}`
- **Impact**: 10x cardinality = 10x storage + 10x query cost

**2. Ingestion Volume** (Logs/Traces)
- Number of events per second
- **Impact**: 1M logs/day vs 1B logs/day = 1000x cost difference

**3. Retention Period**
- How long data is stored
- **Impact**: 30d vs 90d retention = 3x storage cost

**4. Query Complexity**
- Aggregations, joins, scans
- **Impact**: High-cardinality queries can timeout or spike costs

### Cost Optimization Strategy

```
1. Identify: What's costing the most? (cardinality, volume, retention)
2. Reduce: Apply sampling, filtering, aggregation
3. Retain: Short retention for raw data, long retention for aggregates
4. Monitor: Track cost metrics (bytes ingested, cardinality growth)
```

---

## Patterns

### Pattern 1: Cardinality Management (Metrics)

```python
from prometheus_client import Counter, Histogram

# ❌ HIGH CARDINALITY: user_id has 1M+ unique values
requests_bad = Counter(
    'http_requests_total',
    'HTTP requests',
    ['method', 'endpoint', 'status', 'user_id']  # 10 × 50 × 5 × 1M = 2.5M time series!
)

# ✅ LOW CARDINALITY: bounded label values
requests_good = Counter(
    'http_requests_total',
    'HTTP requests',
    ['method', 'endpoint', 'status']  # 10 × 50 × 5 = 2,500 time series
)

# ✅ ALTERNATIVE: Use histograms to reduce cardinality
request_duration = Histogram(
    'http_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint'],  # No status code (use buckets instead)
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
)

# Usage
def handle_request(method, endpoint, user_id):
    # Track request count (low cardinality)
    requests_good.labels(method=method, endpoint=endpoint, status="200").inc()

    # Track user_id in logs/traces (not metrics)
    logger.info("Request processed", extra={"user_id": user_id})

    # Track duration in histogram (bounded cardinality)
    with request_duration.labels(method=method, endpoint=endpoint).time():
        process_request()
```

**Cardinality Reduction Techniques**:
1. **Remove high-cardinality labels**: user_id, email, trace_id, session_id
2. **Group labels**: Instead of 1000 endpoints, group into 10 categories
3. **Use histograms**: Instead of per-bucket metrics, use histogram buckets
4. **Relabel in Prometheus**: Drop or aggregate labels at scrape time

### Pattern 2: Prometheus Relabeling

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'api-servers'
    static_configs:
      - targets: ['api-1:8080', 'api-2:8080']

    metric_relabel_configs:
      # Drop high-cardinality labels
      - source_labels: [user_id]
        action: labeldrop

      # Group endpoints into categories
      - source_labels: [endpoint]
        regex: '/api/users/.*'
        replacement: '/api/users/:id'
        target_label: endpoint

      # Drop low-value metrics entirely
      - source_labels: [__name__]
        regex: 'go_gc_.*'
        action: drop

      # Limit label values
      - source_labels: [status_code]
        regex: '2..'
        replacement: '2xx'
        target_label: status_code
```

### Pattern 3: Tail-Based Sampling (Traces)

```yaml
# otel-collector-config.yaml
processors:
  tail_sampling:
    # Wait 10s for trace to complete before sampling decision
    decision_wait: 10s

    # Limit in-memory traces
    num_traces: 100000

    policies:
      # ALWAYS sample errors (0% sampling = keep all)
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]

      # ALWAYS sample slow requests (>1s)
      - name: slow-requests
        type: latency
        latency:
          threshold_ms: 1000

      # Sample 100% of critical endpoints
      - name: critical-endpoints
        type: string_attribute
        string_attribute:
          key: http.target
          values: [/api/checkout, /api/payment]
          enabled_regex_matching: true
          invert_match: false

      # Sample 5% of all other requests
      - name: probabilistic
        type: probabilistic
        probabilistic:
          sampling_percentage: 5

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [tail_sampling, batch]
      exporters: [otlp/jaeger]
```

**Tail-Based Sampling Benefits**:
- **Smart sampling**: Keep errors and slow requests, sample rest
- **Cost reduction**: 95% reduction in trace volume → 95% cost savings
- **No data loss**: Critical traces always retained

### Pattern 4: Probabilistic Sampling (Head-Based)

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatioBased

# Sample 10% of traces (decided at trace creation)
sampler = ParentBasedTraceIdRatioBased(0.1)

tracer_provider = TracerProvider(sampler=sampler)
```

**Head-Based vs Tail-Based**:

| Feature | Head-Based | Tail-Based |
|---------|-----------|------------|
| **Decision Point** | Trace start | Trace end |
| **Context** | No visibility into trace outcome | Full trace visibility |
| **Latency** | Low | Adds 10s buffer |
| **Cost** | Lower (drops early) | Higher (buffers traces) |
| **Use Case** | High-volume, uniform traffic | Error/latency-aware sampling |

### Pattern 5: Log Sampling and Filtering

```python
import logging
import random

class SamplingFilter(logging.Filter):
    """Sample 10% of INFO logs, keep all WARNING+."""

    def filter(self, record):
        if record.levelno >= logging.WARNING:
            return True  # Keep all warnings/errors
        return random.random() < 0.1  # Sample 10% of info logs

logger = logging.getLogger(__name__)
logger.addFilter(SamplingFilter())
```

**OTel Collector Log Filtering**:

```yaml
processors:
  filter:
    logs:
      include:
        # Keep errors
        match_type: regexp
        record_attributes:
          - key: level
            value: ERROR|FATAL

      exclude:
        # Drop noisy debug logs
        match_type: regexp
        record_attributes:
          - key: message
            value: '.*health check.*'

  # Rate limiting (max 1000 logs/sec)
  groupbytrace:
    wait_duration: 1s
    num_traces: 1000

service:
  pipelines:
    logs:
      receivers: [otlp]
      processors: [filter, groupbytrace, batch]
      exporters: [loki]
```

### Pattern 6: Adaptive Sampling

```python
from opentelemetry.sdk.trace.sampling import Sampler, Decision, SamplingResult
import time

class AdaptiveSampler(Sampler):
    """Dynamically adjust sampling based on request rate."""

    def __init__(self, target_rps=100):
        self.target_rps = target_rps
        self.request_count = 0
        self.last_reset = time.time()
        self.current_rate = 1.0

    def should_sample(self, *args, **kwargs):
        now = time.time()

        # Reset counter every second
        if now - self.last_reset > 1.0:
            current_rps = self.request_count
            self.request_count = 0
            self.last_reset = now

            # Adjust sampling rate
            if current_rps > 0:
                self.current_rate = min(1.0, self.target_rps / current_rps)

        self.request_count += 1

        # Sample based on current rate
        if random.random() < self.current_rate:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)
        return SamplingResult(Decision.DROP)

    def get_description(self):
        return f"AdaptiveSampler(target_rps={self.target_rps})"
```

### Pattern 7: Metrics Aggregation and Recording Rules

```yaml
# prometheus-rules.yml
groups:
  - name: aggregation
    interval: 1m
    rules:
      # Pre-aggregate high-cardinality metrics
      - record: http_requests:rate5m
        expr: |
          sum by (method, status) (
            rate(http_requests_total[5m])
          )

      # Drop detailed labels, keep aggregates
      - record: http_errors:rate5m
        expr: |
          sum by (service) (
            rate(http_requests_total{status=~"5.."}[5m])
          )

      # Compute p95 latency (cheaper to query pre-computed)
      - record: http_request_duration:p95
        expr: |
          histogram_quantile(0.95,
            sum by (le, service) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )
```

**Retention Strategy**:
```
Raw metrics: 7d retention
Aggregated metrics (5m): 30d retention
Aggregated metrics (1h): 90d retention
```

### Pattern 8: Attribute Processor (OTel Collector)

```yaml
processors:
  # Remove high-cardinality attributes
  attributes:
    actions:
      # Delete PII
      - key: email
        action: delete
      - key: user_id
        action: delete

      # Hash high-cardinality IDs
      - key: session_id
        action: hash

      # Limit attribute value length
      - key: error_message
        action: extract
        pattern: '^(.{100}).*'
        extracted_attributes: {short_message: '\1'}

  # Group spans by endpoint pattern
  spanmetrics:
    metrics_exporter: prometheus
    latency_histogram_buckets: [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
    dimensions:
      - name: http.method
      - name: http.status_code

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [attributes, spanmetrics, batch]
      exporters: [otlp/jaeger]
```

---

## Cost Optimization Checklist

### Metrics
```
[ ] Identify high-cardinality metrics (>10k time series)
[ ] Remove user_id, email, trace_id from labels
[ ] Group endpoints into categories (e.g., /api/users/:id)
[ ] Use histograms instead of per-value metrics
[ ] Set up Prometheus relabeling rules
[ ] Create recording rules for expensive queries
[ ] Reduce scrape interval for low-priority metrics (30s → 1m)
[ ] Set retention: 7d raw, 30d aggregated
```

### Traces
```
[ ] Implement tail-based sampling (sample 5-10% of normal traffic)
[ ] ALWAYS sample errors and slow requests
[ ] ALWAYS sample critical endpoints
[ ] Use adaptive sampling for high-traffic services
[ ] Remove PII from span attributes
[ ] Set trace retention: 7d for sampled traces
[ ] Enable span metrics for aggregate view
```

### Logs
```
[ ] Sample INFO logs (10-20%), keep WARNING/ERROR (100%)
[ ] Filter out health checks, heartbeats
[ ] Limit log message length (max 1KB)
[ ] Use structured logging (cheaper to query)
[ ] Set retention: 3d raw, 30d errors only
[ ] Rate limit noisy services (max 1k logs/sec)
```

### General
```
[ ] Monitor cost metrics (bytes ingested, cardinality growth)
[ ] Set up alerts for cost spikes
[ ] Review and prune unused metrics/logs
[ ] Use OTel Collector for preprocessing (cheaper than backend)
[ ] Negotiate volume discounts with observability vendor
[ ] Consider open-source alternatives (Grafana stack)
```

---

## Quick Reference

### Cardinality Limits (Best Practices)

```
Metric label cardinality: <100 unique values per label
Total time series per metric: <10,000
Total time series per service: <100,000
Prometheus instance limit: <1M active time series
```

### Sampling Rates by Traffic Volume

```
< 100 req/sec: 100% sampling
100-1k req/sec: 50% sampling
1k-10k req/sec: 10% sampling
10k+ req/sec: 1-5% sampling (with tail-based for errors)
```

### Retention Guidelines

```
Traces:
  - Raw: 7 days
  - Aggregated (span metrics): 30 days

Metrics:
  - Raw (15s): 7 days
  - 5m aggregates: 30 days
  - 1h aggregates: 90 days

Logs:
  - INFO: 3 days
  - WARNING: 14 days
  - ERROR: 30 days
```

### Cost Estimation Formula

```
Monthly Cost = (Ingestion Volume × Ingestion Rate) + (Storage Volume × Retention Days × Storage Rate)

Example:
Ingestion: 1TB/day × $0.50/GB = $500/day
Storage: 30TB × $0.02/GB/month = $600/month
Total: ~$15,600/month

After optimization (90% reduction):
Ingestion: 100GB/day × $0.50/GB = $50/day
Storage: 3TB × $0.02/GB/month = $60/month
Total: ~$1,560/month (90% savings)
```

---

## Anti-Patterns

### ❌ High-Cardinality Labels

```python
# WRONG: Unbounded label values
requests = Counter('requests', 'Requests', ['user_id', 'email'])

# CORRECT: Bounded labels
requests = Counter('requests', 'Requests', ['method', 'status'])
```

### ❌ No Sampling Strategy

```yaml
# WRONG: 100% sampling for high-traffic service
processors:
  probabilistic_sampler:
    sampling_percentage: 100  # 10k req/sec = 10k traces/sec!

# CORRECT: Tail-based sampling
processors:
  tail_sampling:
    policies:
      - name: errors
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: sample
        type: probabilistic
        probabilistic: {sampling_percentage: 5}
```

### ❌ Same Retention for All Data

```
# WRONG: 90d retention for all logs (expensive)
retention_days: 90

# CORRECT: Tiered retention
retention:
  info_logs: 3d
  error_logs: 30d
  raw_metrics: 7d
  aggregated_metrics: 90d
```

### ❌ Not Monitoring Cost Metrics

```python
# WRONG: No visibility into observability costs

# CORRECT: Track cost metrics
from prometheus_client import Counter, Gauge

logs_ingested_bytes = Counter('logs_ingested_bytes_total', 'Logs ingested')
metrics_cardinality = Gauge('metrics_active_series', 'Active time series')
traces_sampled = Counter('traces_sampled_total', 'Traces sampled', ['sampled'])
```

---

## Related Skills

- **opentelemetry-integration.md** - OTel Collector processors for cost reduction
- **metrics-instrumentation.md** - Cardinality management best practices
- **distributed-tracing.md** - Sampling strategies for traces
- **structured-logging.md** - Efficient log formatting

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
