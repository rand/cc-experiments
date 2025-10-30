//! Performance Monitoring Library
//!
//! Comprehensive async performance monitoring with Prometheus integration.
//! Tracks latency, throughput, and task metrics for PyO3 async applications.

use anyhow::Result;
use chrono::{DateTime, Utc};
use hdrhistogram::Histogram;
use prometheus::{
    Counter, CounterVec, Gauge, GaugeVec, Histogram as PrometheusHistogram,
    HistogramOpts, HistogramVec, Opts, Registry,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex, RwLock};
use std::time::{Duration, Instant};
use tracing::{debug, info, instrument, warn};

/// Performance monitor for tracking async operations
#[derive(Clone)]
pub struct PerformanceMonitor {
    inner: Arc<MonitorInner>,
}

struct MonitorInner {
    name: String,
    registry: Registry,
    metrics: AsyncMetrics,
    latency_trackers: RwLock<HashMap<String, LatencyTracker>>,
    throughput_trackers: RwLock<HashMap<String, ThroughputTracker>>,
    task_trackers: RwLock<HashMap<String, TaskTracker>>,
    start_time: Instant,
}

/// Metrics collection for async operations
pub struct AsyncMetrics {
    /// Task duration histogram (Prometheus)
    task_duration: HistogramVec,
    /// Request counters by status
    requests_total: CounterVec,
    /// Current request rate gauge
    requests_per_second: GaugeVec,
    /// Active tasks gauge
    tasks_active: GaugeVec,
    /// Completed tasks counter
    tasks_completed: CounterVec,
    /// Failed tasks counter
    tasks_failed: CounterVec,
    /// Task queue depth
    queue_depth: GaugeVec,
}

/// High-precision latency tracking using HdrHistogram
pub struct LatencyTracker {
    histogram: Mutex<Histogram<u64>>,
    count: AtomicU64,
    total_duration: AtomicU64,
    min_duration: AtomicU64,
    max_duration: AtomicU64,
}

/// Throughput measurement with time windows
pub struct ThroughputTracker {
    window_size: Duration,
    events: RwLock<Vec<Instant>>,
    total_count: AtomicU64,
}

/// Task execution tracking
pub struct TaskTracker {
    active: AtomicU64,
    completed: AtomicU64,
    failed: AtomicU64,
    total_duration: AtomicU64,
    start_times: RwLock<HashMap<u64, Instant>>,
    next_id: AtomicU64,
}

/// Performance statistics snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceStats {
    pub task_name: String,
    pub latency_ms: LatencyStats,
    pub throughput: ThroughputStats,
    pub task_stats: TaskStats,
    pub timestamp: DateTime<Utc>,
}

/// Latency statistics with percentiles
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LatencyStats {
    pub count: u64,
    pub mean_ms: f64,
    pub min_ms: f64,
    pub max_ms: f64,
    pub p50_ms: f64,
    pub p95_ms: f64,
    pub p99_ms: f64,
    pub p99_9_ms: f64,
    pub stddev_ms: f64,
}

/// Throughput statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThroughputStats {
    pub current_rps: f64,
    pub total_requests: u64,
    pub window_size_seconds: u64,
}

/// Task execution statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskStats {
    pub active: u64,
    pub completed: u64,
    pub failed: u64,
    pub success_rate: f64,
    pub avg_duration_ms: f64,
}

/// Performance report combining all metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceReport {
    pub service_name: String,
    pub uptime_seconds: u64,
    pub tasks: HashMap<String, PerformanceStats>,
    pub timestamp: DateTime<Utc>,
}

impl PerformanceMonitor {
    /// Create a new performance monitor
    pub fn new(name: impl Into<String>) -> Self {
        let name = name.into();
        let registry = Registry::new();
        let metrics = AsyncMetrics::new(&registry).expect("Failed to create metrics");

        Self {
            inner: Arc::new(MonitorInner {
                name,
                registry,
                metrics,
                latency_trackers: RwLock::new(HashMap::new()),
                throughput_trackers: RwLock::new(HashMap::new()),
                task_trackers: RwLock::new(HashMap::new()),
                start_time: Instant::now(),
            }),
        }
    }

    /// Get the Prometheus registry for metrics export
    pub fn registry(&self) -> &Registry {
        &self.inner.registry
    }

    /// Track an async operation with automatic instrumentation
    #[instrument(skip(self, future))]
    pub async fn track_async<F, T, E>(
        &self,
        task_name: impl Into<String> + std::fmt::Debug,
        future: F,
    ) -> Result<T, E>
    where
        F: std::future::Future<Output = Result<T, E>>,
        E: std::fmt::Display,
    {
        let task_name = task_name.into();
        let start = Instant::now();

        // Start task tracking
        let task_id = self.start_task(&task_name);

        // Execute the future
        let result = future.await;
        let duration = start.elapsed();

        // Record metrics
        match &result {
            Ok(_) => {
                self.record_success(&task_name, duration);
                self.end_task(&task_name, task_id, true);
            }
            Err(e) => {
                warn!("Task {} failed: {}", task_name, e);
                self.record_failure(&task_name, duration);
                self.end_task(&task_name, task_id, false);
            }
        }

        result
    }

    /// Start tracking a task (returns task ID)
    pub fn start_task(&self, task_name: &str) -> u64 {
        self.ensure_trackers(task_name);

        let trackers = self.inner.task_trackers.read().unwrap();
        if let Some(tracker) = trackers.get(task_name) {
            let task_id = tracker.start_task();

            // Update Prometheus gauge
            self.inner
                .metrics
                .tasks_active
                .with_label_values(&[task_name])
                .set(tracker.active.load(Ordering::Relaxed) as f64);

            task_id
        } else {
            0
        }
    }

    /// End tracking a task
    pub fn end_task(&self, task_name: &str, task_id: u64, success: bool) {
        let trackers = self.inner.task_trackers.read().unwrap();
        if let Some(tracker) = trackers.get(task_name) {
            if let Some(duration) = tracker.end_task(task_id, success) {
                // Update Prometheus metrics
                self.inner
                    .metrics
                    .tasks_active
                    .with_label_values(&[task_name])
                    .set(tracker.active.load(Ordering::Relaxed) as f64);

                if success {
                    self.inner
                        .metrics
                        .tasks_completed
                        .with_label_values(&[task_name, "success"])
                        .inc();
                } else {
                    self.inner
                        .metrics
                        .tasks_failed
                        .with_label_values(&[task_name, "error"])
                        .inc();
                }

                // Record duration
                self.inner
                    .metrics
                    .task_duration
                    .with_label_values(&[task_name])
                    .observe(duration.as_secs_f64());
            }
        }
    }

    /// Record successful operation
    fn record_success(&self, task_name: &str, duration: Duration) {
        self.record_latency(task_name, duration);
        self.record_throughput(task_name);

        self.inner
            .metrics
            .requests_total
            .with_label_values(&[task_name, "success"])
            .inc();
    }

    /// Record failed operation
    fn record_failure(&self, task_name: &str, duration: Duration) {
        self.record_latency(task_name, duration);

        self.inner
            .metrics
            .requests_total
            .with_label_values(&[task_name, "error"])
            .inc();
    }

    /// Record latency measurement
    pub fn record_latency(&self, task_name: &str, duration: Duration) {
        self.ensure_trackers(task_name);

        let trackers = self.inner.latency_trackers.read().unwrap();
        if let Some(tracker) = trackers.get(task_name) {
            tracker.record(duration);
        }
    }

    /// Record throughput event
    pub fn record_throughput(&self, task_name: &str) {
        self.ensure_trackers(task_name);

        let trackers = self.inner.throughput_trackers.read().unwrap();
        if let Some(tracker) = trackers.get(task_name) {
            tracker.record_event();

            // Update Prometheus gauge
            let rps = tracker.current_rate();
            self.inner
                .metrics
                .requests_per_second
                .with_label_values(&[task_name])
                .set(rps);
        }
    }

    /// Ensure trackers exist for a task
    fn ensure_trackers(&self, task_name: &str) {
        // Check if trackers exist (read lock)
        {
            let latency = self.inner.latency_trackers.read().unwrap();
            if latency.contains_key(task_name) {
                return;
            }
        }

        // Create trackers (write lock)
        {
            let mut latency = self.inner.latency_trackers.write().unwrap();
            latency
                .entry(task_name.to_string())
                .or_insert_with(|| LatencyTracker::new(2));
        }

        {
            let mut throughput = self.inner.throughput_trackers.write().unwrap();
            throughput
                .entry(task_name.to_string())
                .or_insert_with(|| ThroughputTracker::new(Duration::from_secs(60)));
        }

        {
            let mut tasks = self.inner.task_trackers.write().unwrap();
            tasks
                .entry(task_name.to_string())
                .or_insert_with(TaskTracker::new);
        }
    }

    /// Get statistics for a specific task
    pub fn get_stats(&self, task_name: &str) -> Option<PerformanceStats> {
        let latency_trackers = self.inner.latency_trackers.read().unwrap();
        let throughput_trackers = self.inner.throughput_trackers.read().unwrap();
        let task_trackers = self.inner.task_trackers.read().unwrap();

        let latency_stats = latency_trackers.get(task_name)?.get_stats();
        let throughput_stats = throughput_trackers.get(task_name)?.get_stats();
        let task_stats = task_trackers.get(task_name)?.get_stats();

        Some(PerformanceStats {
            task_name: task_name.to_string(),
            latency_ms: latency_stats,
            throughput: throughput_stats,
            task_stats,
            timestamp: Utc::now(),
        })
    }

    /// Generate comprehensive performance report
    pub fn report(&self) -> PerformanceReport {
        let latency_trackers = self.inner.latency_trackers.read().unwrap();
        let tasks: HashMap<String, PerformanceStats> = latency_trackers
            .keys()
            .filter_map(|name| self.get_stats(name))
            .map(|stats| (stats.task_name.clone(), stats))
            .collect();

        PerformanceReport {
            service_name: self.inner.name.clone(),
            uptime_seconds: self.inner.start_time.elapsed().as_secs(),
            tasks,
            timestamp: Utc::now(),
        }
    }

    /// Export metrics in Prometheus format
    pub fn export_prometheus(&self) -> String {
        use prometheus::Encoder;
        let encoder = prometheus::TextEncoder::new();
        let metric_families = self.inner.registry.gather();
        encoder.encode_to_string(&metric_families).unwrap()
    }

    /// Reset all metrics (useful for testing)
    pub fn reset(&self) {
        let mut latency = self.inner.latency_trackers.write().unwrap();
        let mut throughput = self.inner.throughput_trackers.write().unwrap();
        let mut tasks = self.inner.task_trackers.write().unwrap();

        latency.clear();
        throughput.clear();
        tasks.clear();
    }
}

impl AsyncMetrics {
    fn new(registry: &Registry) -> Result<Self> {
        let task_duration = HistogramVec::new(
            HistogramOpts::new("task_duration_seconds", "Task execution duration")
                .buckets(vec![
                    0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
                ]),
            &["task"],
        )?;

        let requests_total = CounterVec::new(
            Opts::new("requests_total", "Total number of requests"),
            &["task", "status"],
        )?;

        let requests_per_second = GaugeVec::new(
            Opts::new("requests_per_second", "Current request rate"),
            &["task"],
        )?;

        let tasks_active = GaugeVec::new(
            Opts::new("tasks_active", "Currently active tasks"),
            &["task"],
        )?;

        let tasks_completed = CounterVec::new(
            Opts::new("tasks_completed_total", "Completed tasks"),
            &["task", "status"],
        )?;

        let tasks_failed = CounterVec::new(
            Opts::new("tasks_failed_total", "Failed tasks"),
            &["task", "status"],
        )?;

        let queue_depth = GaugeVec::new(
            Opts::new("queue_depth", "Task queue depth"),
            &["task"],
        )?;

        registry.register(Box::new(task_duration.clone()))?;
        registry.register(Box::new(requests_total.clone()))?;
        registry.register(Box::new(requests_per_second.clone()))?;
        registry.register(Box::new(tasks_active.clone()))?;
        registry.register(Box::new(tasks_completed.clone()))?;
        registry.register(Box::new(tasks_failed.clone()))?;
        registry.register(Box::new(queue_depth.clone()))?;

        Ok(Self {
            task_duration,
            requests_total,
            requests_per_second,
            tasks_active,
            tasks_completed,
            tasks_failed,
            queue_depth,
        })
    }
}

impl LatencyTracker {
    fn new(precision: u8) -> Self {
        Self {
            histogram: Mutex::new(
                Histogram::new_with_bounds(1, 60_000_000_000, precision)
                    .expect("Failed to create histogram"),
            ),
            count: AtomicU64::new(0),
            total_duration: AtomicU64::new(0),
            min_duration: AtomicU64::new(u64::MAX),
            max_duration: AtomicU64::new(0),
        }
    }

    fn record(&self, duration: Duration) {
        let micros = duration.as_micros() as u64;

        // Update histogram (requires exclusive access)
        if let Ok(mut hist) = self.histogram.lock() {
            let _ = hist.record(micros);
        }

        // Update atomic counters
        self.count.fetch_add(1, Ordering::Relaxed);
        self.total_duration
            .fetch_add(micros, Ordering::Relaxed);

        // Update min
        let mut current_min = self.min_duration.load(Ordering::Relaxed);
        while micros < current_min {
            match self.min_duration.compare_exchange_weak(
                current_min,
                micros,
                Ordering::Relaxed,
                Ordering::Relaxed,
            ) {
                Ok(_) => break,
                Err(actual) => current_min = actual,
            }
        }

        // Update max
        let mut current_max = self.max_duration.load(Ordering::Relaxed);
        while micros > current_max {
            match self.max_duration.compare_exchange_weak(
                current_max,
                micros,
                Ordering::Relaxed,
                Ordering::Relaxed,
            ) {
                Ok(_) => break,
                Err(actual) => current_max = actual,
            }
        }
    }

    fn get_stats(&self) -> LatencyStats {
        let count = self.count.load(Ordering::Relaxed);
        let total = self.total_duration.load(Ordering::Relaxed);
        let min = self.min_duration.load(Ordering::Relaxed);
        let max = self.max_duration.load(Ordering::Relaxed);

        let mean_micros = if count > 0 {
            total as f64 / count as f64
        } else {
            0.0
        };

        let (p50, p95, p99, p99_9, stddev) = if let Ok(hist) = self.histogram.lock() {
            (
                hist.value_at_percentile(50.0),
                hist.value_at_percentile(95.0),
                hist.value_at_percentile(99.0),
                hist.value_at_percentile(99.9),
                hist.stdev(),
            )
        } else {
            (0, 0, 0, 0, 0.0)
        };

        LatencyStats {
            count,
            mean_ms: mean_micros / 1000.0,
            min_ms: if min == u64::MAX { 0.0 } else { min as f64 / 1000.0 },
            max_ms: max as f64 / 1000.0,
            p50_ms: p50 as f64 / 1000.0,
            p95_ms: p95 as f64 / 1000.0,
            p99_ms: p99 as f64 / 1000.0,
            p99_9_ms: p99_9 as f64 / 1000.0,
            stddev_ms: stddev / 1000.0,
        }
    }
}

impl ThroughputTracker {
    fn new(window_size: Duration) -> Self {
        Self {
            window_size,
            events: RwLock::new(Vec::new()),
            total_count: AtomicU64::new(0),
        }
    }

    fn record_event(&self) {
        let now = Instant::now();
        let mut events = self.events.write().unwrap();

        // Remove events outside the window
        let cutoff = now - self.window_size;
        events.retain(|&time| time > cutoff);

        // Add new event
        events.push(now);
        self.total_count.fetch_add(1, Ordering::Relaxed);
    }

    fn current_rate(&self) -> f64 {
        let now = Instant::now();
        let events = self.events.read().unwrap();

        let cutoff = now - self.window_size;
        let recent_count = events.iter().filter(|&&time| time > cutoff).count();

        recent_count as f64 / self.window_size.as_secs_f64()
    }

    fn get_stats(&self) -> ThroughputStats {
        ThroughputStats {
            current_rps: self.current_rate(),
            total_requests: self.total_count.load(Ordering::Relaxed),
            window_size_seconds: self.window_size.as_secs(),
        }
    }
}

impl TaskTracker {
    fn new() -> Self {
        Self {
            active: AtomicU64::new(0),
            completed: AtomicU64::new(0),
            failed: AtomicU64::new(0),
            total_duration: AtomicU64::new(0),
            start_times: RwLock::new(HashMap::new()),
            next_id: AtomicU64::new(1),
        }
    }

    fn start_task(&self) -> u64 {
        let task_id = self.next_id.fetch_add(1, Ordering::Relaxed);
        self.active.fetch_add(1, Ordering::Relaxed);

        let mut start_times = self.start_times.write().unwrap();
        start_times.insert(task_id, Instant::now());

        task_id
    }

    fn end_task(&self, task_id: u64, success: bool) -> Option<Duration> {
        self.active.fetch_sub(1, Ordering::Relaxed);

        if success {
            self.completed.fetch_add(1, Ordering::Relaxed);
        } else {
            self.failed.fetch_add(1, Ordering::Relaxed);
        }

        let mut start_times = self.start_times.write().unwrap();
        let start = start_times.remove(&task_id)?;
        let duration = start.elapsed();

        self.total_duration
            .fetch_add(duration.as_micros() as u64, Ordering::Relaxed);

        Some(duration)
    }

    fn get_stats(&self) -> TaskStats {
        let active = self.active.load(Ordering::Relaxed);
        let completed = self.completed.load(Ordering::Relaxed);
        let failed = self.failed.load(Ordering::Relaxed);
        let total_duration = self.total_duration.load(Ordering::Relaxed);

        let total = completed + failed;
        let success_rate = if total > 0 {
            completed as f64 / total as f64 * 100.0
        } else {
            0.0
        };

        let avg_duration_ms = if total > 0 {
            (total_duration as f64 / total as f64) / 1000.0
        } else {
            0.0
        };

        TaskStats {
            active,
            completed,
            failed,
            success_rate,
            avg_duration_ms,
        }
    }
}

impl std::fmt::Display for PerformanceReport {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        writeln!(f, "Performance Report: {}", self.service_name)?;
        writeln!(f, "Uptime: {}s", self.uptime_seconds)?;
        writeln!(f, "Timestamp: {}", self.timestamp)?;
        writeln!(f)?;

        for (name, stats) in &self.tasks {
            writeln!(f, "Task: {}", name)?;
            writeln!(f, "  Latency:")?;
            writeln!(f, "    Count: {}", stats.latency_ms.count)?;
            writeln!(f, "    Mean: {:.2}ms", stats.latency_ms.mean_ms)?;
            writeln!(f, "    Min: {:.2}ms", stats.latency_ms.min_ms)?;
            writeln!(f, "    Max: {:.2}ms", stats.latency_ms.max_ms)?;
            writeln!(f, "    p50: {:.2}ms", stats.latency_ms.p50_ms)?;
            writeln!(f, "    p95: {:.2}ms", stats.latency_ms.p95_ms)?;
            writeln!(f, "    p99: {:.2}ms", stats.latency_ms.p99_ms)?;
            writeln!(f, "    p99.9: {:.2}ms", stats.latency_ms.p99_9_ms)?;
            writeln!(f, "  Throughput:")?;
            writeln!(f, "    Current: {:.2} req/s", stats.throughput.current_rps)?;
            writeln!(f, "    Total: {}", stats.throughput.total_requests)?;
            writeln!(f, "  Tasks:")?;
            writeln!(f, "    Active: {}", stats.task_stats.active)?;
            writeln!(f, "    Completed: {}", stats.task_stats.completed)?;
            writeln!(f, "    Failed: {}", stats.task_stats.failed)?;
            writeln!(f, "    Success Rate: {:.2}%", stats.task_stats.success_rate)?;
            writeln!(f)?;
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::time::sleep;

    #[tokio::test]
    async fn test_basic_tracking() {
        let monitor = PerformanceMonitor::new("test");

        let result = monitor
            .track_async("test_task", async {
                sleep(Duration::from_millis(10)).await;
                Ok::<_, anyhow::Error>(42)
            })
            .await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 42);

        let stats = monitor.get_stats("test_task").unwrap();
        assert_eq!(stats.latency_ms.count, 1);
        assert!(stats.latency_ms.mean_ms >= 10.0);
    }

    #[tokio::test]
    async fn test_multiple_operations() {
        let monitor = PerformanceMonitor::new("test");

        for _ in 0..10 {
            monitor
                .track_async("multi_task", async {
                    sleep(Duration::from_millis(5)).await;
                    Ok::<_, anyhow::Error>(())
                })
                .await
                .unwrap();
        }

        let stats = monitor.get_stats("multi_task").unwrap();
        assert_eq!(stats.latency_ms.count, 10);
        assert!(stats.latency_ms.mean_ms >= 5.0);
        assert_eq!(stats.task_stats.completed, 10);
    }

    #[test]
    fn test_latency_percentiles() {
        let tracker = LatencyTracker::new(2);

        // Record various latencies (need more samples for accurate percentiles)
        for _ in 0..100 {
            for ms in [1, 5, 10, 15, 20, 50, 100, 200].iter() {
                tracker.record(Duration::from_millis(*ms));
            }
        }

        let stats = tracker.get_stats();
        assert_eq!(stats.count, 800);
        assert!(stats.p50_ms <= stats.p95_ms);
        assert!(stats.p95_ms <= stats.p99_ms);
        assert!(stats.min_ms <= stats.max_ms);
    }

    #[test]
    fn test_throughput_tracking() {
        let tracker = ThroughputTracker::new(Duration::from_secs(60));

        for _ in 0..100 {
            tracker.record_event();
        }

        let stats = tracker.get_stats();
        assert_eq!(stats.total_requests, 100);
        assert!(stats.current_rps > 0.0);
    }
}
