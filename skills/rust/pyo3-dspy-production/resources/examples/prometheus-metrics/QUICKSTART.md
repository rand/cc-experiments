# Quick Start Guide

Get up and running with Prometheus metrics in under 5 minutes.

## Prerequisites

- Rust 1.70+ (`rustup`)
- Docker & Docker Compose (for full stack)

## Option 1: Standalone Demo (Fastest)

```bash
# Run the demo server
cargo run --release

# In another terminal, make some predictions
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"input": "test query", "prediction_type": "cot"}'

# View metrics
curl http://localhost:3000/metrics

# View health
curl http://localhost:3000/health
```

The server will automatically generate background traffic and print metrics every 10 seconds.

## Option 2: Full Stack (Recommended)

```bash
# Start Prometheus + Grafana + Demo
docker-compose up -d

# Wait 10 seconds for services to start
sleep 10

# Open Grafana
open http://localhost:3001

# Login: admin / admin

# View metrics in Prometheus
open http://localhost:9090

# Make a test prediction
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"input": "test", "prediction_type": "react"}'
```

## What You'll See

### Terminal Output

Every 10 seconds you'll see metrics like:

```
================================================================================
METRICS SUMMARY - dspy_demo
================================================================================
  dspy_predictions_total{prediction_type="cot",status="success"} 45
  dspy_predictions_total{prediction_type="react",status="success"} 38
  dspy_cache_hits_total{cache_type="memory"} 52
  dspy_errors_total{error_type="timeout"} 2
  dspy_active_predictions{service="dspy_demo"} 3
  dspy_cache_size_bytes{cache_type="memory"} 12544
  dspy_prediction_duration_seconds_count{prediction_type="cot"} 45
  dspy_prediction_duration_seconds_sum{prediction_type="cot"} 6.75
================================================================================
```

### /metrics Endpoint

```
# HELP dspy_predictions_total Total number of predictions made
# TYPE dspy_predictions_total counter
dspy_predictions_total{prediction_type="cot",service="dspy_demo",status="success"} 152

# HELP dspy_prediction_duration_seconds Prediction duration in seconds
# TYPE dspy_prediction_duration_seconds histogram
dspy_prediction_duration_seconds_bucket{prediction_type="cot",service="dspy_demo",le="0.1"} 89
dspy_prediction_duration_seconds_bucket{prediction_type="cot",service="dspy_demo",le="0.25"} 152
dspy_prediction_duration_seconds_sum{prediction_type="cot",service="dspy_demo"} 18.4
dspy_prediction_duration_seconds_count{prediction_type="cot",service="dspy_demo"} 152
```

### Grafana Dashboard

1. Open http://localhost:3001
2. Login: `admin` / `admin`
3. Navigate to **Dashboards** → **DSPy Service Overview**
4. See real-time graphs of:
   - Request rate
   - Error rate
   - P95 latency
   - Cache hit rate
   - Active predictions

### Prometheus Queries

1. Open http://localhost:9090
2. Try these PromQL queries:

**Request rate:**
```promql
rate(dspy_predictions_total[5m])
```

**Error percentage:**
```promql
rate(dspy_errors_total[5m]) / rate(dspy_predictions_total[5m]) * 100
```

**P95 latency:**
```promql
histogram_quantile(0.95, rate(dspy_prediction_duration_seconds_bucket[5m]))
```

**Cache hit rate:**
```promql
rate(dspy_cache_hits_total[5m]) /
  (rate(dspy_cache_hits_total[5m]) + rate(dspy_cache_misses_total[5m])) * 100
```

## Testing Different Scenarios

### High Error Rate

```bash
# Make many requests quickly to trigger errors
for i in {1..50}; do
  curl -X POST http://localhost:3000/predict \
    -H "Content-Type: application/json" \
    -d '{"input": "test '$i'", "prediction_type": "cot"}' &
done
wait
```

Watch the error rate spike in Grafana!

### Different Prediction Types

```bash
# Chain-of-thought (slower)
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"input": "complex query", "prediction_type": "cot"}'

# ReAct (medium)
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"input": "reasoning query", "prediction_type": "react"}'

# Few-shot (faster)
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"input": "simple query", "prediction_type": "few_shot"}'
```

Compare latencies in the histogram!

### Cache Behavior

```bash
# Disable cache (slower)
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"input": "test", "use_cache": false}'

# Enable cache (faster on repeat)
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"input": "test", "use_cache": true}'
```

Watch the cache metrics grow!

## Cleanup

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (deletes all data)
docker-compose down -v
```

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Check [alerts.yml](alerts.yml) for alerting rules
3. Explore the [src/lib.rs](src/lib.rs) for implementation details
4. Integrate metrics into your own DSPy service

## Troubleshooting

**Port already in use:**
```bash
# Check what's using port 3000
lsof -i :3000

# Change port in docker-compose.yml if needed
```

**Metrics not showing in Prometheus:**
```bash
# Check Prometheus targets
open http://localhost:9090/targets

# Should see "dspy-demo" with state "UP"
```

**Grafana dashboard empty:**
```bash
# Wait 1-2 minutes for data to accumulate
# Adjust time range in Grafana (top right)
```

## Questions?

See the main [README.md](README.md) for:
- Architecture details
- Metric descriptions
- Best practices
- Integration guide
- Advanced configurations
