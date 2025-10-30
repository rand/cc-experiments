# Prometheus Metrics for DSPy Services

Comprehensive Prometheus metrics instrumentation for DSPy-based production services.

## Features

- **Counter Metrics**: Track prediction counts, cache hits, errors
- **Gauge Metrics**: Monitor active predictions, cache size
- **Histogram Metrics**: Measure prediction duration, API latency
- **Custom Labels**: Service name, prediction type, error type
- **HTTP Endpoint**: `/metrics` in OpenMetrics format
- **Middleware**: Automatic request/response tracking
- **Grafana Integration**: Pre-configured dashboards

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│   Axum HTTP Server          │
│   - /predict endpoint       │
│   - /metrics endpoint       │
│   - Metrics Middleware      │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   DSpyMetrics               │
│   - Prometheus Registry     │
│   - Counter: predictions    │
│   - Counter: cache_hits     │
│   - Counter: errors         │
│   - Gauge: active           │
│   - Gauge: cache_size       │
│   - Histogram: duration     │
│   - Histogram: latency      │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   DSPy Python Service       │
│   - Prediction logic        │
│   - Cache management        │
└─────────────────────────────┘
```

## Metrics Exposed

### Counters

**`dspy_predictions_total`**
- Description: Total number of predictions made
- Labels: `service`, `prediction_type`, `status`
- Example: `dspy_predictions_total{service="qa",prediction_type="cot",status="success"} 1523`

**`dspy_cache_hits_total`**
- Description: Total number of cache hits
- Labels: `service`, `cache_type`
- Example: `dspy_cache_hits_total{service="qa",cache_type="redis"} 892`

**`dspy_errors_total`**
- Description: Total number of errors
- Labels: `service`, `error_type`
- Example: `dspy_errors_total{service="qa",error_type="timeout"} 12`

### Gauges

**`dspy_active_predictions`**
- Description: Number of currently active predictions
- Labels: `service`
- Example: `dspy_active_predictions{service="qa"} 5`

**`dspy_cache_size_bytes`**
- Description: Current cache size in bytes
- Labels: `service`, `cache_type`
- Example: `dspy_cache_size_bytes{service="qa",cache_type="redis"} 1048576`

### Histograms

**`dspy_prediction_duration_seconds`**
- Description: Prediction duration in seconds
- Labels: `service`, `prediction_type`
- Buckets: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
- Example:
  ```
  dspy_prediction_duration_seconds_bucket{service="qa",prediction_type="cot",le="0.1"} 450
  dspy_prediction_duration_seconds_sum{service="qa",prediction_type="cot"} 125.5
  dspy_prediction_duration_seconds_count{service="qa",prediction_type="cot"} 1523
  ```

**`dspy_api_latency_seconds`**
- Description: API request latency in seconds
- Labels: `service`, `endpoint`, `method`, `status_code`
- Buckets: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0
- Example:
  ```
  dspy_api_latency_seconds_bucket{service="qa",endpoint="/predict",method="POST",status_code="200",le="0.1"} 892
  ```

## Usage

### Run Standalone Service

```bash
cargo run --release
```

Server starts on `http://localhost:3000`:
- `POST /predict` - Make predictions
- `GET /metrics` - Prometheus metrics
- `GET /health` - Health check

### Run with Prometheus & Grafana

```bash
docker-compose up -d
```

Services:
- Application: `http://localhost:3000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001` (admin/admin)

### Instrumenting Your Service

```rust
use prometheus_metrics::{DSpyMetrics, MetricsMiddleware};
use axum::{Router, routing::post, middleware};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize metrics
    let metrics = DSpyMetrics::new("my_service")?;

    // Create router with metrics middleware
    let app = Router::new()
        .route("/predict", post(predict_handler))
        .layer(middleware::from_fn_with_state(
            metrics.clone(),
            MetricsMiddleware::track_request
        ));

    // Serve app
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
    axum::serve(listener, app).await?;

    Ok(())
}

async fn predict_handler(
    State(metrics): State<DSpyMetrics>,
) -> Result<Json<Response>, StatusCode> {
    // Record active prediction
    let _guard = metrics.record_active_prediction();

    // Time prediction
    let timer = metrics.start_prediction_timer("cot");

    // Make prediction
    let result = make_prediction().await;

    // Record result
    match result {
        Ok(response) => {
            timer.observe_duration();
            metrics.record_prediction("cot", "success");
            Ok(Json(response))
        }
        Err(e) => {
            metrics.record_error("prediction_failed");
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}
```

### Recording Metrics Manually

```rust
// Record prediction
metrics.record_prediction("cot", "success");
metrics.record_prediction("react", "failure");

// Record cache hit
metrics.record_cache_hit("redis");
metrics.record_cache_miss("redis");

// Record error
metrics.record_error("timeout");
metrics.record_error("rate_limit");

// Update cache size
metrics.update_cache_size("redis", 2048576);

// Time operations
let timer = metrics.start_prediction_timer("cot");
// ... do work ...
timer.observe_duration();

// Track active work (RAII guard)
{
    let _guard = metrics.record_active_prediction();
    // ... prediction active ...
} // guard dropped, count decremented
```

## Querying Metrics

### PromQL Examples

**Prediction rate per second:**
```promql
rate(dspy_predictions_total[5m])
```

**Error rate percentage:**
```promql
rate(dspy_errors_total[5m]) / rate(dspy_predictions_total[5m]) * 100
```

**95th percentile latency:**
```promql
histogram_quantile(0.95, rate(dspy_prediction_duration_seconds_bucket[5m]))
```

**Cache hit rate:**
```promql
rate(dspy_cache_hits_total[5m]) /
  (rate(dspy_cache_hits_total[5m]) + rate(dspy_cache_misses_total[5m]))
```

**Active predictions by service:**
```promql
sum by (service) (dspy_active_predictions)
```

## Grafana Dashboards

### Importing Dashboards

1. Open Grafana at `http://localhost:3001`
2. Login with `admin` / `admin`
3. Click **Dashboards** → **Import**
4. Upload `grafana/dashboards/dspy-overview.json`

### Key Panels

**Performance Overview:**
- Request rate (req/sec)
- Error rate (%)
- P50, P95, P99 latency
- Active predictions

**Cache Metrics:**
- Hit rate (%)
- Cache size (MB)
- Eviction rate

**Error Analysis:**
- Errors by type
- Error rate trend
- Failed predictions

## Alerting Rules

Example `prometheus/alerts.yml`:

```yaml
groups:
  - name: dspy_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          rate(dspy_errors_total[5m]) / rate(dspy_predictions_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, rate(dspy_prediction_duration_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High prediction latency"
          description: "P95 latency is {{ $value }}s"

      - alert: LowCacheHitRate
        expr: |
          rate(dspy_cache_hits_total[5m]) /
          (rate(dspy_cache_hits_total[5m]) + rate(dspy_cache_misses_total[5m])) < 0.5
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "Low cache hit rate"
          description: "Hit rate is {{ $value | humanizePercentage }}"
```

## Best Practices

### Metric Naming

✅ **Good:**
- `dspy_predictions_total` (clear, includes unit)
- `dspy_cache_size_bytes` (includes base unit)
- `dspy_prediction_duration_seconds` (includes base unit)

❌ **Bad:**
- `predictions` (too generic)
- `cache_size_mb` (use base units)
- `latency_ms` (use base units)

### Label Cardinality

✅ **Good:**
- Limited set: `prediction_type` (cot, react, few_shot)
- Bounded: `error_type` (timeout, rate_limit, invalid_input)
- Static: `service` (qa, summarization, classification)

❌ **Bad:**
- Unbounded: `user_id` (millions of values)
- High cardinality: `request_id` (unique per request)
- Dynamic: `timestamp` (infinite values)

### Histogram Buckets

Choose buckets that cover your expected range:

```rust
// For fast operations (< 1s)
vec![0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]

// For slow operations (1s - 10s)
vec![0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0]

// For very slow operations (> 10s)
vec![1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
```

### Recording Patterns

**Use RAII guards for paired operations:**
```rust
let _guard = metrics.record_active_prediction();
// Count automatically decremented when guard drops
```

**Time with observing guards:**
```rust
let timer = metrics.start_prediction_timer("cot");
let result = predict().await;
timer.observe_duration();
```

**Record outcomes explicitly:**
```rust
match result {
    Ok(_) => metrics.record_prediction("cot", "success"),
    Err(_) => {
        metrics.record_prediction("cot", "failure");
        metrics.record_error("prediction_failed");
    }
}
```

## Performance Impact

Metrics collection overhead:
- Counter increment: ~20ns
- Gauge update: ~25ns
- Histogram observation: ~150ns
- Label lookup: ~50ns

For a service handling 1000 req/sec:
- Overhead: ~0.2ms/sec = 0.02%
- Negligible impact on performance

## Troubleshooting

### Missing Metrics

**Symptom:** Metrics not appearing in Prometheus

**Solutions:**
1. Check `/metrics` endpoint directly: `curl http://localhost:3000/metrics`
2. Verify Prometheus scrape config: `prometheus.yml`
3. Check Prometheus targets: `http://localhost:9090/targets`

### High Cardinality

**Symptom:** Prometheus memory usage growing

**Solutions:**
1. Review label values: Limit to < 10 values per label
2. Remove unbounded labels (user_id, request_id)
3. Aggregate in application code before exporting

### Stale Metrics

**Symptom:** Old metric values persist

**Solutions:**
1. Use gauges for current state (automatically updated)
2. Set expiration on time-series data
3. Restart Prometheus to clear old data

## References

- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Prometheus Rust Client](https://docs.rs/prometheus/latest/prometheus/)
- [OpenMetrics Specification](https://openmetrics.io/)
- [Grafana Documentation](https://grafana.com/docs/)

## License

MIT
