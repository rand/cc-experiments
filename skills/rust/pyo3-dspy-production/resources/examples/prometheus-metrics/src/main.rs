//! Prometheus metrics demo server for DSPy services
//!
//! Demonstrates comprehensive metrics instrumentation with:
//! - HTTP endpoints with automatic tracking
//! - Simulated DSPy prediction workload
//! - Real-time metrics visualization
//! - /metrics endpoint for Prometheus scraping

use anyhow::{Context, Result};
use axum::{
    extract::State,
    http::StatusCode,
    middleware,
    response::{IntoResponse, Json},
    routing::{get, post},
    Router,
};
use prometheus_metrics::{metrics_handler, DSpyMetrics, MetricsMiddleware};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::Duration;
use tokio::time::sleep;
use tracing::{info, warn};

// ============================================================================
// Request/Response Types
// ============================================================================

#[derive(Debug, Deserialize)]
struct PredictRequest {
    /// Input text for prediction
    input: String,
    /// Type of prediction: "cot" (chain-of-thought), "react", "few_shot"
    #[serde(default = "default_prediction_type")]
    prediction_type: String,
    /// Whether to use cache
    #[serde(default = "default_use_cache")]
    use_cache: bool,
}

fn default_prediction_type() -> String {
    "cot".to_string()
}

fn default_use_cache() -> bool {
    true
}

#[derive(Debug, Serialize)]
struct PredictResponse {
    /// Prediction output
    output: String,
    /// Whether result came from cache
    from_cache: bool,
    /// Duration in seconds
    duration_seconds: f64,
    /// Confidence score
    confidence: f64,
}

#[derive(Debug, Serialize)]
struct HealthResponse {
    status: String,
    service: String,
    active_predictions: f64,
    cache_size_mb: f64,
}

// ============================================================================
// Simulated DSPy Service
// ============================================================================

/// Simulated DSPy service with caching
struct DSpyService {
    metrics: DSpyMetrics,
    cache_hit_rate: f64,
}

impl DSpyService {
    fn new(metrics: DSpyMetrics) -> Self {
        Self {
            metrics,
            cache_hit_rate: 0.6, // 60% cache hit rate
        }
    }

    /// Simulate a prediction with realistic timing and caching
    async fn predict(&self, request: PredictRequest) -> Result<PredictResponse> {
        // Track active prediction
        let _active_guard = self.metrics.record_active_prediction();

        // Start timing
        let timer = self.metrics.start_prediction_timer(&request.prediction_type);

        // Simulate cache lookup
        let from_cache = request.use_cache && rand::random::<f64>() < self.cache_hit_rate;

        if from_cache {
            self.metrics.record_cache_hit("memory");

            // Cache hit - fast response
            sleep(Duration::from_millis(5)).await;

            let duration = timer.elapsed().as_secs_f64();
            timer.observe_duration();

            self.metrics
                .record_prediction(&request.prediction_type, "success");

            return Ok(PredictResponse {
                output: format!("Cached prediction for: {}", request.input),
                from_cache: true,
                duration_seconds: duration,
                confidence: 0.95,
            });
        }

        self.metrics.record_cache_miss("memory");

        // Cache miss - simulate actual prediction
        let result = self.simulate_prediction(&request).await;

        let duration = timer.elapsed().as_secs_f64();
        timer.observe_duration();

        match result {
            Ok(output) => {
                self.metrics
                    .record_prediction(&request.prediction_type, "success");

                // Update cache size (simulate adding to cache)
                let current_size = self.metrics.get_cache_size("memory") as u64;
                let new_size = current_size + (output.len() as u64 * 2);
                self.metrics.update_cache_size("memory", new_size);

                Ok(PredictResponse {
                    output,
                    from_cache: false,
                    duration_seconds: duration,
                    confidence: 0.88,
                })
            }
            Err(e) => {
                self.metrics
                    .record_prediction(&request.prediction_type, "failure");
                self.metrics.record_error("prediction_failed");
                Err(e)
            }
        }
    }

    /// Simulate actual prediction with realistic delays and failure rates
    async fn simulate_prediction(&self, request: &PredictRequest) -> Result<String> {
        // Simulate different prediction types with different latencies
        let delay_ms = match request.prediction_type.as_str() {
            "cot" => 100 + (rand::random::<u64>() % 100),      // 100-200ms
            "react" => 200 + (rand::random::<u64>() % 200),    // 200-400ms
            "few_shot" => 50 + (rand::random::<u64>() % 50),   // 50-100ms
            _ => {
                self.metrics.record_error("invalid_prediction_type");
                return Err(anyhow::anyhow!("Invalid prediction type"));
            }
        };

        sleep(Duration::from_millis(delay_ms)).await;

        // Simulate occasional failures (5% failure rate)
        if rand::random::<f64>() < 0.05 {
            let error_type = if rand::random::<bool>() {
                "timeout"
            } else {
                "rate_limit"
            };
            self.metrics.record_error(error_type);
            return Err(anyhow::anyhow!("Prediction failed: {}", error_type));
        }

        // Successful prediction
        Ok(format!(
            "Prediction result for '{}' using {}",
            request.input, request.prediction_type
        ))
    }
}

// ============================================================================
// HTTP Handlers
// ============================================================================

/// Metrics endpoint for Prometheus
async fn metrics_endpoint(State(service): State<Arc<DSpyService>>) -> impl IntoResponse {
    match service.metrics.gather() {
        Ok(body) => (StatusCode::OK, body),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            format!("Failed to gather metrics: {}", e),
        ),
    }
}

/// Health check endpoint
async fn health_handler(State(service): State<Arc<DSpyService>>) -> impl IntoResponse {
    let metrics = &service.metrics;

    let response = HealthResponse {
        status: "healthy".to_string(),
        service: metrics.service_name().to_string(),
        active_predictions: metrics.get_active_predictions(),
        cache_size_mb: metrics.get_cache_size("memory") / 1_048_576.0,
    };

    Json(response)
}

/// Prediction endpoint
async fn predict_handler(
    State(service): State<Arc<DSpyService>>,
    Json(request): Json<PredictRequest>,
) -> Result<Json<PredictResponse>, StatusCode> {
    info!("Prediction request: {:?}", request);

    match service.predict(request).await {
        Ok(response) => Ok(Json(response)),
        Err(e) => {
            warn!("Prediction failed: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// ============================================================================
// Background Workload Generator
// ============================================================================

/// Generate continuous background workload for demonstration
async fn generate_workload(service: Arc<DSpyService>) {
    info!("Starting background workload generator");

    let prediction_types = vec!["cot", "react", "few_shot"];

    loop {
        // Random delay between requests (10-500ms)
        let delay_ms = 10 + (rand::random::<u64>() % 490);
        sleep(Duration::from_millis(delay_ms)).await;

        // Random prediction type
        let prediction_type = prediction_types[rand::random::<usize>() % prediction_types.len()];

        let request = PredictRequest {
            input: format!("Background request {}", rand::random::<u32>()),
            prediction_type: prediction_type.to_string(),
            use_cache: rand::random::<bool>(),
        };

        match service.predict(request).await {
            Ok(response) => {
                info!(
                    "Background prediction: {} (cache: {}, duration: {:.3}s)",
                    prediction_type, response.from_cache, response.duration_seconds
                );
            }
            Err(e) => {
                warn!("Background prediction failed: {}", e);
            }
        }
    }
}

// ============================================================================
// Metrics Visualization
// ============================================================================

/// Print metrics summary to terminal
async fn print_metrics_summary(metrics: &DSpyMetrics) {
    loop {
        sleep(Duration::from_secs(10)).await;

        println!("\n{}", "=".repeat(80));
        println!("METRICS SUMMARY - {}", metrics.service_name());
        println!("{}", "=".repeat(80));

        let output = match metrics.gather() {
            Ok(o) => o,
            Err(e) => {
                warn!("Failed to gather metrics: {}", e);
                continue;
            }
        };

        // Parse and display key metrics
        for line in output.lines() {
            if line.starts_with('#') || line.is_empty() {
                continue;
            }

            // Display counters
            if line.contains("dspy_predictions_total")
                || line.contains("dspy_cache_hits_total")
                || line.contains("dspy_errors_total")
            {
                println!("  {}", line);
            }

            // Display gauges
            if line.contains("dspy_active_predictions")
                || line.contains("dspy_cache_size_bytes")
            {
                println!("  {}", line);
            }

            // Display histogram summaries
            if line.contains("_count") || line.contains("_sum") {
                if line.contains("dspy_prediction_duration_seconds")
                    || line.contains("dspy_api_latency_seconds")
                {
                    println!("  {}", line);
                }
            }
        }

        println!("{}", "=".repeat(80));
    }
}

// ============================================================================
// Main
// ============================================================================

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    info!("Starting Prometheus Metrics Demo");

    // Initialize metrics
    let metrics = DSpyMetrics::new("dspy_demo").context("Failed to create metrics")?;
    info!("Metrics initialized for service: {}", metrics.service_name());

    // Create service
    let service = Arc::new(DSpyService::new(metrics.clone()));

    // Build router
    let app = Router::new()
        .route("/health", get(health_handler))
        .route("/predict", post(predict_handler))
        .route("/metrics", get(metrics_endpoint))
        .layer(middleware::from_fn_with_state(
            metrics.clone(),
            MetricsMiddleware::track_request,
        ))
        .with_state(service.clone());

    // Start background workload
    let workload_service = service.clone();
    tokio::spawn(async move {
        generate_workload(workload_service).await;
    });

    // Start metrics visualization
    let metrics_clone = metrics.clone();
    tokio::spawn(async move {
        print_metrics_summary(&metrics_clone).await;
    });

    // Start server
    let addr = "0.0.0.0:3000";
    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .context("Failed to bind to address")?;

    info!("Server listening on http://{}", addr);
    info!("Endpoints:");
    info!("  - POST http://{}/predict - Make predictions", addr);
    info!("  - GET  http://{}/health - Health check", addr);
    info!("  - GET  http://{}/metrics - Prometheus metrics", addr);
    info!("");
    info!("Example request:");
    info!(
        r#"  curl -X POST http://{}/predict -H "Content-Type: application/json" -d '{{"input": "test", "prediction_type": "cot"}}'"#,
        addr
    );
    info!("");
    info!("View metrics:");
    info!("  curl http://{}/metrics", addr);

    axum::serve(listener, app)
        .await
        .context("Server error")?;

    Ok(())
}

// ============================================================================
// Usage Examples
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_service_prediction() {
        let metrics = DSpyMetrics::new("test").unwrap();
        let service = DSpyService::new(metrics);

        let request = PredictRequest {
            input: "test input".to_string(),
            prediction_type: "cot".to_string(),
            use_cache: false,
        };

        let result = service.predict(request).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_cache_behavior() {
        let metrics = DSpyMetrics::new("test_cache").unwrap();
        let service = DSpyService::new(metrics);

        // Make multiple requests to test caching
        let mut cache_hits = 0;
        let mut cache_misses = 0;

        for _ in 0..10 {
            let request = PredictRequest {
                input: "cached input".to_string(),
                prediction_type: "cot".to_string(),
                use_cache: true,
            };

            if let Ok(response) = service.predict(request).await {
                if response.from_cache {
                    cache_hits += 1;
                } else {
                    cache_misses += 1;
                }
            }
        }

        // Should have some cache hits
        assert!(cache_hits > 0);
        assert!(cache_misses > 0);
    }

    #[tokio::test]
    async fn test_different_prediction_types() {
        let metrics = DSpyMetrics::new("test_types").unwrap();
        let service = DSpyService::new(metrics);

        let types = vec!["cot", "react", "few_shot"];

        for pred_type in types {
            let request = PredictRequest {
                input: "test".to_string(),
                prediction_type: pred_type.to_string(),
                use_cache: false,
            };

            let result = service.predict(request).await;
            assert!(result.is_ok());
        }
    }
}
