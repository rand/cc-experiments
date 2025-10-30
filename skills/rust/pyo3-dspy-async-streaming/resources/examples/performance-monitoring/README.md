# Performance Monitoring Example

A comprehensive async performance monitoring system with Prometheus integration for tracking latency, throughput, and system metrics in PyO3 async applications.

## Features

- **Latency Tracking**: HdrHistogram-based latency recording with percentiles (p50, p95, p99, p99.9)
- **Throughput Measurement**: Real-time requests/second calculation
- **Task Instrumentation**: Automatic tracking of async task execution
- **Prometheus Integration**: Standard metrics export for Grafana dashboards
- **Live Monitoring**: Real-time performance dashboard
- **Comparative Analysis**: Sync vs async performance comparison

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Performance Monitor                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │ Latency Tracker │  │ Throughput Meter │  │ Task Track │ │
│  │                 │  │                  │  │            │ │
│  │ HdrHistogram    │  │ Rate Calculator  │  │ Active     │ │
│  │ Percentiles     │  │ Windows          │  │ Completed  │ │
│  │ p50/p95/p99     │  │ Req/sec          │  │ Failed     │ │
│  └─────────────────┘  └──────────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ Prometheus Registry │
                   │                     │
                   │ - Histograms        │
                   │ - Counters          │
                   │ - Gauges            │
                   └─────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   /metrics       │
                    │   Endpoint       │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Prometheus      │
                    │  + Grafana       │
                    └──────────────────┘
```

## Usage

### Basic Monitoring

```rust
use performance_monitoring::{PerformanceMonitor, MonitoredTask};
use std::time::Duration;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let monitor = PerformanceMonitor::new("my_app");

    // Monitor an async operation
    let result = monitor.track_async("prediction", async {
        // Your async work here
        tokio::time::sleep(Duration::from_millis(10)).await;
        Ok::<_, anyhow::Error>("result")
    }).await?;

    // Get performance report
    let report = monitor.report();
    println!("{}", report);

    Ok(())
}
```

### Running the Example

```bash
# Build the example
cargo build --release

# Run with Prometheus and Grafana
docker-compose up -d

# Start the monitoring server
cargo run --release

# Access endpoints
curl http://localhost:3000/metrics        # Prometheus metrics
curl http://localhost:3000/dashboard      # JSON dashboard data

# Access Grafana
open http://localhost:3001                # Default: admin/admin
```

## Metrics Exposed

### Latency Metrics

```
# HELP task_duration_seconds Task execution duration
# TYPE task_duration_seconds histogram
task_duration_seconds_bucket{task="prediction",le="0.005"} 10
task_duration_seconds_bucket{task="prediction",le="0.01"} 45
task_duration_seconds_bucket{task="prediction",le="0.025"} 90
task_duration_seconds_bucket{task="prediction",le="0.05"} 98
task_duration_seconds_bucket{task="prediction",le="0.1"} 100
task_duration_seconds_sum{task="prediction"} 1.234
task_duration_seconds_count{task="prediction"} 100
```

### Throughput Metrics

```
# HELP requests_total Total number of requests
# TYPE requests_total counter
requests_total{task="prediction",status="success"} 950
requests_total{task="prediction",status="error"} 50

# HELP requests_per_second Current request rate
# TYPE requests_per_second gauge
requests_per_second{task="prediction"} 125.5
```

### Task Metrics

```
# HELP tasks_active Currently active tasks
# TYPE tasks_active gauge
tasks_active{task="prediction"} 8

# HELP tasks_completed_total Completed tasks
# TYPE tasks_completed_total counter
tasks_completed_total{task="prediction"} 1000
```

## Prometheus Configuration

The included `prometheus.yml` configures:
- Scrape interval: 5 seconds
- Target: `localhost:3000/metrics`
- Retention: 15 days

## Grafana Dashboards

### Pre-configured Panels

1. **Latency Percentiles**: Line graph showing p50, p95, p99, p99.9
2. **Throughput**: Current requests/second
3. **Active Tasks**: Gauge of concurrent operations
4. **Error Rate**: Success vs failure ratio
5. **Task Distribution**: Histogram of execution times

### Import Dashboard

```bash
# Dashboard JSON available at
curl http://localhost:3000/grafana-dashboard > dashboard.json

# Import in Grafana UI
Configuration → Data Sources → Add Prometheus (http://prometheus:9090)
Dashboards → Import → Upload dashboard.json
```

## Performance Comparison

The example includes sync vs async comparison:

```bash
cargo run --release -- --compare

# Output:
Performance Comparison Report
============================

Sync Implementation:
  Total requests: 1000
  Duration: 15.234s
  Throughput: 65.6 req/s
  Latency p50: 14.2ms
  Latency p95: 18.5ms
  Latency p99: 22.1ms

Async Implementation:
  Total requests: 1000
  Duration: 2.145s
  Throughput: 466.2 req/s
  Latency p50: 10.1ms
  Latency p95: 12.3ms
  Latency p99: 15.8ms

Improvement:
  Throughput: 7.1x faster
  Latency p99: 28.5% lower
```

## Instrumentation Best Practices

### 1. Automatic Instrumentation

```rust
use tracing::instrument;

#[instrument(skip(monitor))]
async fn process_request(
    monitor: &PerformanceMonitor,
    data: &str,
) -> anyhow::Result<String> {
    monitor.track_async("process", async {
        // Work happens here
        Ok(data.to_uppercase())
    }).await
}
```

### 2. Manual Tracking

```rust
let start = std::time::Instant::now();
let result = perform_work().await?;
monitor.record_latency("work", start.elapsed());
monitor.increment_counter("work_completed");
```

### 3. Custom Metrics

```rust
// Add custom gauge
monitor.set_gauge("queue_depth", queue.len() as f64);

// Add custom histogram
monitor.record_histogram("batch_size", batch.len() as f64);
```

## Configuration

Environment variables:

```bash
RUST_LOG=info                          # Logging level
METRICS_PORT=3000                      # Metrics server port
PROMETHEUS_URL=http://localhost:9090   # Prometheus URL
LATENCY_PRECISION=2                    # HdrHistogram precision
WINDOW_SIZE=60                         # Throughput window (seconds)
```

## Testing

```bash
# Run unit tests
cargo test

# Run benchmarks
cargo bench

# Load test with monitoring
cargo run --release -- --load-test --duration 60 --concurrency 100
```

## Troubleshooting

### High Latency

1. Check active tasks: `curl http://localhost:3000/dashboard | jq .active_tasks`
2. Review error rate: Look for failed requests
3. Check system resources: CPU, memory, network

### Missing Metrics

1. Verify Prometheus is scraping: http://localhost:9090/targets
2. Check metrics endpoint: http://localhost:3000/metrics
3. Review logs: `docker-compose logs prometheus`

### Memory Usage

HdrHistogram memory usage scales with precision:
- Precision 1: ~4KB per histogram
- Precision 2: ~8KB per histogram (default)
- Precision 3: ~16KB per histogram

Adjust `LATENCY_PRECISION` based on needs.

## Integration Example

```rust
use pyo3::prelude::*;
use performance_monitoring::PerformanceMonitor;

#[pyclass]
struct MonitoredModel {
    monitor: PerformanceMonitor,
}

#[pymethods]
impl MonitoredModel {
    #[new]
    fn new() -> Self {
        Self {
            monitor: PerformanceMonitor::new("dspy_model"),
        }
    }

    fn predict(&self, input: String) -> PyResult<String> {
        let monitor = self.monitor.clone();
        Python::with_gil(|py| {
            py.allow_threads(|| {
                tokio::runtime::Runtime::new()
                    .unwrap()
                    .block_on(async {
                        monitor.track_async("predict", async {
                            // Async prediction logic
                            Ok::<_, anyhow::Error>(format!("Prediction: {}", input))
                        }).await
                    })
            })
        }).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    fn get_metrics(&self) -> PyResult<String> {
        Ok(self.monitor.report())
    }
}
```

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)
- [HdrHistogram](http://hdrhistogram.org/)
- [Tokio Tracing](https://tokio.rs/tokio/topics/tracing)

## License

MIT
