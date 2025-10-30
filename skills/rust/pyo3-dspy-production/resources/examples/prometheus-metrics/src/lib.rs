//! Prometheus metrics instrumentation for DSPy services
//!
//! This library provides comprehensive metrics collection for DSPy-based services:
//! - Counter metrics for predictions, cache hits, errors
//! - Gauge metrics for active predictions, cache size
//! - Histogram metrics for latency and duration
//! - Middleware for automatic HTTP request tracking
//!
//! # Example
//!
//! ```no_run
//! use prometheus_metrics::{DSpyMetrics, MetricsMiddleware};
//! use axum::{Router, routing::post, middleware};
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     let metrics = DSpyMetrics::new("my_service")?;
//!
//!     let app = Router::new()
//!         .route("/predict", post(predict_handler))
//!         .layer(middleware::from_fn_with_state(
//!             metrics.clone(),
//!             MetricsMiddleware::track_request
//!         ));
//!
//!     let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
//!     axum::serve(listener, app).await?;
//!     Ok(())
//! }
//! ```

use anyhow::{Context, Result};
use axum::{
    extract::State,
    http::{Request, StatusCode},
    middleware::Next,
    response::{IntoResponse, Response},
};
use lazy_static::lazy_static;
use prometheus::{
    CounterVec, Encoder, GaugeVec, Histogram, HistogramOpts, HistogramVec, Opts,
    Registry, TextEncoder,
};
use std::sync::Arc;
use std::time::Instant;

// ============================================================================
// Global Registry
// ============================================================================

lazy_static! {
    /// Global Prometheus registry for all metrics
    pub static ref REGISTRY: Registry = Registry::new();
}

// ============================================================================
// Metric Collections
// ============================================================================

/// Counter metrics for DSPy service
struct Counters {
    /// Total number of predictions made
    predictions: CounterVec,
    /// Total number of cache hits
    cache_hits: CounterVec,
    /// Total number of cache misses
    cache_misses: CounterVec,
    /// Total number of errors
    errors: CounterVec,
}

impl Counters {
    fn new(service: &str) -> Result<Self> {
        let predictions = CounterVec::new(
            Opts::new("dspy_predictions_total", "Total number of predictions made")
                .const_label("service", service),
            &["prediction_type", "status"],
        )
        .context("Failed to create predictions counter")?;

        let cache_hits = CounterVec::new(
            Opts::new("dspy_cache_hits_total", "Total number of cache hits")
                .const_label("service", service),
            &["cache_type"],
        )
        .context("Failed to create cache_hits counter")?;

        let cache_misses = CounterVec::new(
            Opts::new("dspy_cache_misses_total", "Total number of cache misses")
                .const_label("service", service),
            &["cache_type"],
        )
        .context("Failed to create cache_misses counter")?;

        let errors = CounterVec::new(
            Opts::new("dspy_errors_total", "Total number of errors")
                .const_label("service", service),
            &["error_type"],
        )
        .context("Failed to create errors counter")?;

        REGISTRY.register(Box::new(predictions.clone()))?;
        REGISTRY.register(Box::new(cache_hits.clone()))?;
        REGISTRY.register(Box::new(cache_misses.clone()))?;
        REGISTRY.register(Box::new(errors.clone()))?;

        Ok(Self {
            predictions,
            cache_hits,
            cache_misses,
            errors,
        })
    }
}

/// Gauge metrics for DSPy service
struct Gauges {
    /// Number of currently active predictions
    active_predictions: GaugeVec,
    /// Current cache size in bytes
    cache_size: GaugeVec,
}

impl Gauges {
    fn new(service: &str) -> Result<Self> {
        let active_predictions = GaugeVec::new(
            Opts::new(
                "dspy_active_predictions",
                "Number of currently active predictions",
            )
            .const_label("service", service),
            &[],
        )
        .context("Failed to create active_predictions gauge")?;

        let cache_size = GaugeVec::new(
            Opts::new("dspy_cache_size_bytes", "Current cache size in bytes")
                .const_label("service", service),
            &["cache_type"],
        )
        .context("Failed to create cache_size gauge")?;

        REGISTRY.register(Box::new(active_predictions.clone()))?;
        REGISTRY.register(Box::new(cache_size.clone()))?;

        Ok(Self {
            active_predictions,
            cache_size,
        })
    }
}

/// Histogram metrics for DSPy service
struct Histograms {
    /// Prediction duration in seconds
    prediction_duration: HistogramVec,
    /// API request latency in seconds
    api_latency: HistogramVec,
}

impl Histograms {
    fn new(service: &str) -> Result<Self> {
        // Buckets for prediction duration (5ms to 10s)
        let prediction_buckets = vec![0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0];

        let prediction_duration = HistogramVec::new(
            HistogramOpts::new(
                "dspy_prediction_duration_seconds",
                "Prediction duration in seconds",
            )
            .const_label("service", service)
            .buckets(prediction_buckets),
            &["prediction_type"],
        )
        .context("Failed to create prediction_duration histogram")?;

        // Buckets for API latency (1ms to 1s)
        let latency_buckets = vec![0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0];

        let api_latency = HistogramVec::new(
            HistogramOpts::new(
                "dspy_api_latency_seconds",
                "API request latency in seconds",
            )
            .const_label("service", service)
            .buckets(latency_buckets),
            &["endpoint", "method", "status_code"],
        )
        .context("Failed to create api_latency histogram")?;

        REGISTRY.register(Box::new(prediction_duration.clone()))?;
        REGISTRY.register(Box::new(api_latency.clone()))?;

        Ok(Self {
            prediction_duration,
            api_latency,
        })
    }
}

// ============================================================================
// DSpyMetrics
// ============================================================================

/// Main metrics collection for DSPy services
///
/// Provides methods to record predictions, cache hits, errors, and track
/// active operations with automatic cleanup.
#[derive(Clone)]
pub struct DSpyMetrics {
    service_name: String,
    counters: Arc<Counters>,
    gauges: Arc<Gauges>,
    histograms: Arc<Histograms>,
}

impl DSpyMetrics {
    /// Create a new metrics collection for a service
    ///
    /// # Arguments
    ///
    /// * `service_name` - Name of the service (e.g., "qa", "summarization")
    ///
    /// # Example
    ///
    /// ```no_run
    /// use prometheus_metrics::DSpyMetrics;
    ///
    /// let metrics = DSpyMetrics::new("my_service").unwrap();
    /// ```
    pub fn new(service_name: &str) -> Result<Self> {
        let counters = Arc::new(Counters::new(service_name)?);
        let gauges = Arc::new(Gauges::new(service_name)?);
        let histograms = Arc::new(Histograms::new(service_name)?);

        Ok(Self {
            service_name: service_name.to_string(),
            counters,
            gauges,
            histograms,
        })
    }

    // ------------------------------------------------------------------------
    // Counter Operations
    // ------------------------------------------------------------------------

    /// Record a prediction
    ///
    /// # Arguments
    ///
    /// * `prediction_type` - Type of prediction (e.g., "cot", "react")
    /// * `status` - Status of prediction ("success", "failure")
    ///
    /// # Example
    ///
    /// ```no_run
    /// # use prometheus_metrics::DSpyMetrics;
    /// # let metrics = DSpyMetrics::new("test").unwrap();
    /// metrics.record_prediction("cot", "success");
    /// metrics.record_prediction("react", "failure");
    /// ```
    pub fn record_prediction(&self, prediction_type: &str, status: &str) {
        self.counters
            .predictions
            .with_label_values(&[prediction_type, status])
            .inc();
    }

    /// Record a cache hit
    ///
    /// # Arguments
    ///
    /// * `cache_type` - Type of cache (e.g., "redis", "memory")
    ///
    /// # Example
    ///
    /// ```no_run
    /// # use prometheus_metrics::DSpyMetrics;
    /// # let metrics = DSpyMetrics::new("test").unwrap();
    /// metrics.record_cache_hit("redis");
    /// ```
    pub fn record_cache_hit(&self, cache_type: &str) {
        self.counters
            .cache_hits
            .with_label_values(&[cache_type])
            .inc();
    }

    /// Record a cache miss
    ///
    /// # Arguments
    ///
    /// * `cache_type` - Type of cache (e.g., "redis", "memory")
    ///
    /// # Example
    ///
    /// ```no_run
    /// # use prometheus_metrics::DSpyMetrics;
    /// # let metrics = DSpyMetrics::new("test").unwrap();
    /// metrics.record_cache_miss("redis");
    /// ```
    pub fn record_cache_miss(&self, cache_type: &str) {
        self.counters
            .cache_misses
            .with_label_values(&[cache_type])
            .inc();
    }

    /// Record an error
    ///
    /// # Arguments
    ///
    /// * `error_type` - Type of error (e.g., "timeout", "rate_limit")
    ///
    /// # Example
    ///
    /// ```no_run
    /// # use prometheus_metrics::DSpyMetrics;
    /// # let metrics = DSpyMetrics::new("test").unwrap();
    /// metrics.record_error("timeout");
    /// metrics.record_error("rate_limit");
    /// ```
    pub fn record_error(&self, error_type: &str) {
        self.counters.errors.with_label_values(&[error_type]).inc();
    }

    // ------------------------------------------------------------------------
    // Gauge Operations
    // ------------------------------------------------------------------------

    /// Record an active prediction (returns RAII guard)
    ///
    /// The prediction count is automatically decremented when the guard is dropped.
    ///
    /// # Example
    ///
    /// ```no_run
    /// # use prometheus_metrics::DSpyMetrics;
    /// # let metrics = DSpyMetrics::new("test").unwrap();
    /// {
    ///     let _guard = metrics.record_active_prediction();
    ///     // Prediction is active...
    /// } // Guard dropped, count decremented
    /// ```
    pub fn record_active_prediction(&self) -> ActivePredictionGuard {
        self.gauges
            .active_predictions
            .with_label_values(&[])
            .inc();

        ActivePredictionGuard {
            gauge: self.gauges.active_predictions.clone(),
        }
    }

    /// Get current number of active predictions
    pub fn get_active_predictions(&self) -> f64 {
        self.gauges.active_predictions.with_label_values(&[]).get()
    }

    /// Update cache size
    ///
    /// # Arguments
    ///
    /// * `cache_type` - Type of cache (e.g., "redis", "memory")
    /// * `size_bytes` - Current size in bytes
    ///
    /// # Example
    ///
    /// ```no_run
    /// # use prometheus_metrics::DSpyMetrics;
    /// # let metrics = DSpyMetrics::new("test").unwrap();
    /// metrics.update_cache_size("redis", 1048576); // 1 MB
    /// ```
    pub fn update_cache_size(&self, cache_type: &str, size_bytes: u64) {
        self.gauges
            .cache_size
            .with_label_values(&[cache_type])
            .set(size_bytes as f64);
    }

    /// Get current cache size
    pub fn get_cache_size(&self, cache_type: &str) -> f64 {
        self.gauges.cache_size.with_label_values(&[cache_type]).get()
    }

    // ------------------------------------------------------------------------
    // Histogram Operations
    // ------------------------------------------------------------------------

    /// Start timing a prediction (returns observing guard)
    ///
    /// # Arguments
    ///
    /// * `prediction_type` - Type of prediction (e.g., "cot", "react")
    ///
    /// # Example
    ///
    /// ```no_run
    /// # use prometheus_metrics::DSpyMetrics;
    /// # let metrics = DSpyMetrics::new("test").unwrap();
    /// let timer = metrics.start_prediction_timer("cot");
    /// // ... make prediction ...
    /// timer.observe_duration();
    /// ```
    pub fn start_prediction_timer(&self, prediction_type: &str) -> PredictionTimer {
        PredictionTimer {
            histogram: self
                .histograms
                .prediction_duration
                .with_label_values(&[prediction_type]),
            start: Instant::now(),
        }
    }

    /// Record prediction duration manually
    ///
    /// # Arguments
    ///
    /// * `prediction_type` - Type of prediction
    /// * `duration_secs` - Duration in seconds
    pub fn record_prediction_duration(&self, prediction_type: &str, duration_secs: f64) {
        self.histograms
            .prediction_duration
            .with_label_values(&[prediction_type])
            .observe(duration_secs);
    }

    /// Start timing an API request
    ///
    /// # Arguments
    ///
    /// * `endpoint` - API endpoint (e.g., "/predict")
    /// * `method` - HTTP method (e.g., "POST")
    /// * `status_code` - HTTP status code (e.g., "200")
    pub fn start_api_timer(&self, endpoint: &str, method: &str, status_code: &str) -> ApiTimer {
        ApiTimer {
            histogram: self
                .histograms
                .api_latency
                .with_label_values(&[endpoint, method, status_code]),
            start: Instant::now(),
        }
    }

    /// Record API latency manually
    pub fn record_api_latency(
        &self,
        endpoint: &str,
        method: &str,
        status_code: &str,
        duration_secs: f64,
    ) {
        self.histograms
            .api_latency
            .with_label_values(&[endpoint, method, status_code])
            .observe(duration_secs);
    }

    // ------------------------------------------------------------------------
    // Export
    // ------------------------------------------------------------------------

    /// Gather and encode metrics in OpenMetrics format
    ///
    /// # Returns
    ///
    /// String containing metrics in Prometheus exposition format
    ///
    /// # Example
    ///
    /// ```no_run
    /// # use prometheus_metrics::DSpyMetrics;
    /// # let metrics = DSpyMetrics::new("test").unwrap();
    /// let metrics_text = metrics.gather().unwrap();
    /// println!("{}", metrics_text);
    /// ```
    pub fn gather(&self) -> Result<String> {
        let encoder = TextEncoder::new();
        let metric_families = REGISTRY.gather();
        let mut buffer = Vec::new();
        encoder
            .encode(&metric_families, &mut buffer)
            .context("Failed to encode metrics")?;
        String::from_utf8(buffer).context("Failed to convert metrics to UTF-8")
    }

    /// Get service name
    pub fn service_name(&self) -> &str {
        &self.service_name
    }
}

// ============================================================================
// RAII Guards
// ============================================================================

/// Guard that automatically decrements active prediction count when dropped
pub struct ActivePredictionGuard {
    gauge: GaugeVec,
}

impl Drop for ActivePredictionGuard {
    fn drop(&mut self) {
        self.gauge.with_label_values(&[]).dec();
    }
}

/// Timer for measuring prediction duration
pub struct PredictionTimer {
    histogram: Histogram,
    start: Instant,
}

impl PredictionTimer {
    /// Observe the elapsed duration since timer creation
    pub fn observe_duration(self) {
        let duration = self.start.elapsed();
        self.histogram.observe(duration.as_secs_f64());
    }

    /// Get elapsed duration without observing
    pub fn elapsed(&self) -> std::time::Duration {
        self.start.elapsed()
    }
}

/// Timer for measuring API latency
pub struct ApiTimer {
    histogram: Histogram,
    start: Instant,
}

impl ApiTimer {
    /// Observe the elapsed duration since timer creation
    pub fn observe_duration(self) {
        let duration = self.start.elapsed();
        self.histogram.observe(duration.as_secs_f64());
    }

    /// Get elapsed duration without observing
    pub fn elapsed(&self) -> std::time::Duration {
        self.start.elapsed()
    }
}

// ============================================================================
// Middleware
// ============================================================================

/// Middleware for automatic HTTP request metrics tracking
///
/// Tracks:
/// - Request latency by endpoint, method, status code
/// - Request counts
/// - Error rates
pub struct MetricsMiddleware;

impl MetricsMiddleware {
    /// Axum middleware function to track HTTP requests
    ///
    /// # Example
    ///
    /// ```no_run
    /// use prometheus_metrics::{DSpyMetrics, MetricsMiddleware};
    /// use axum::{Router, routing::get, middleware};
    ///
    /// # #[tokio::main]
    /// # async fn main() -> anyhow::Result<()> {
    /// let metrics = DSpyMetrics::new("my_service")?;
    ///
    /// let app = Router::new()
    ///     .route("/predict", get(|| async { "OK" }))
    ///     .layer(middleware::from_fn_with_state(
    ///         metrics.clone(),
    ///         MetricsMiddleware::track_request
    ///     ));
    /// # Ok(())
    /// # }
    /// ```
    pub async fn track_request(
        State(metrics): State<DSpyMetrics>,
        req: Request<axum::body::Body>,
        next: Next,
    ) -> Response {
        let start = Instant::now();
        let method = req.method().to_string();
        let path = req.uri().path().to_string();

        // Process request
        let response = next.run(req).await;

        // Record metrics
        let status_code = response.status().as_u16().to_string();
        let duration = start.elapsed().as_secs_f64();

        metrics.record_api_latency(&path, &method, &status_code, duration);

        response
    }
}

// ============================================================================
// Helper Functions
// ============================================================================

/// Create a metrics endpoint handler for Axum
///
/// # Example
///
/// ```no_run
/// use prometheus_metrics::{DSpyMetrics, metrics_handler};
/// use axum::{Router, routing::get};
///
/// # #[tokio::main]
/// # async fn main() -> anyhow::Result<()> {
/// let metrics = DSpyMetrics::new("my_service")?;
///
/// let app = Router::new()
///     .route("/metrics", get(metrics_handler))
///     .with_state(metrics);
/// # Ok(())
/// # }
/// ```
pub async fn metrics_handler(State(metrics): State<DSpyMetrics>) -> impl IntoResponse {
    match metrics.gather() {
        Ok(body) => (StatusCode::OK, body),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            format!("Failed to gather metrics: {}", e),
        ),
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metrics_creation() {
        let metrics = DSpyMetrics::new("test_service").unwrap();
        assert_eq!(metrics.service_name(), "test_service");
    }

    #[test]
    fn test_counter_operations() {
        let metrics = DSpyMetrics::new("test_counters").unwrap();

        metrics.record_prediction("cot", "success");
        metrics.record_prediction("cot", "success");
        metrics.record_prediction("react", "failure");

        metrics.record_cache_hit("redis");
        metrics.record_cache_miss("redis");

        metrics.record_error("timeout");

        // Verify metrics were recorded
        let output = metrics.gather().unwrap();
        assert!(output.contains("dspy_predictions_total"));
        assert!(output.contains("dspy_cache_hits_total"));
        assert!(output.contains("dspy_errors_total"));
    }

    #[test]
    fn test_gauge_operations() {
        let metrics = DSpyMetrics::new("test_gauges").unwrap();

        {
            let _guard1 = metrics.record_active_prediction();
            assert_eq!(metrics.get_active_predictions(), 1.0);

            {
                let _guard2 = metrics.record_active_prediction();
                assert_eq!(metrics.get_active_predictions(), 2.0);
            }

            assert_eq!(metrics.get_active_predictions(), 1.0);
        }

        assert_eq!(metrics.get_active_predictions(), 0.0);

        metrics.update_cache_size("redis", 1024);
        assert_eq!(metrics.get_cache_size("redis"), 1024.0);
    }

    #[test]
    fn test_histogram_operations() {
        let metrics = DSpyMetrics::new("test_histograms").unwrap();

        let timer = metrics.start_prediction_timer("cot");
        std::thread::sleep(std::time::Duration::from_millis(10));
        timer.observe_duration();

        metrics.record_api_latency("/predict", "POST", "200", 0.05);

        let output = metrics.gather().unwrap();
        assert!(output.contains("dspy_prediction_duration_seconds"));
        assert!(output.contains("dspy_api_latency_seconds"));
    }

    #[test]
    fn test_metrics_output_format() {
        let metrics = DSpyMetrics::new("test_format").unwrap();

        metrics.record_prediction("cot", "success");
        metrics.update_cache_size("redis", 2048);
        metrics.record_prediction_duration("cot", 0.123);

        let output = metrics.gather().unwrap();

        // Check for proper metric naming
        assert!(output.contains("dspy_predictions_total"));
        assert!(output.contains("dspy_cache_size_bytes"));
        assert!(output.contains("dspy_prediction_duration_seconds"));

        // Check for labels
        assert!(output.contains(r#"service="test_format""#));
        assert!(output.contains(r#"prediction_type="cot""#));
        assert!(output.contains(r#"cache_type="redis""#));
    }
}
