//! HTTP API Server for Production DSpy Service
//!
//! Provides REST endpoints for predictions, health checks, and metrics.

use axum::{
    extract::{Extension, Json, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post},
    Router,
};
use complete_production_service::{
    HealthStatus, PredictionRequest, PredictionResponse, ProductionDSpyService, ServiceConfig,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Duration;
use tower::ServiceBuilder;
use tower_http::{
    compression::CompressionLayer,
    cors::CorsLayer,
    timeout::TimeoutLayer,
    trace::{DefaultMakeSpan, DefaultOnResponse, TraceLayer},
};
use tracing::{error, info, warn, Level};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};
use uuid::Uuid;

// =============================================================================
// Configuration
// =============================================================================

#[derive(Debug, Deserialize)]
struct ServerConfig {
    #[serde(default = "default_host")]
    host: String,

    #[serde(default = "default_port")]
    port: u16,

    #[serde(default = "default_timeout")]
    request_timeout_secs: u64,

    #[serde(default = "default_log_level")]
    log_level: String,

    #[serde(default = "default_log_format")]
    log_format: String,
}

fn default_host() -> String {
    "0.0.0.0".to_string()
}

fn default_port() -> u16 {
    8080
}

fn default_timeout() -> u64 {
    30
}

fn default_log_level() -> String {
    "info".to_string()
}

fn default_log_format() -> String {
    "json".to_string()
}

// =============================================================================
// Error Handling
// =============================================================================

#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
    error_type: String,
    request_id: Option<String>,
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, error_type) = match &self.0 {
            e if e.to_string().contains("Circuit breaker") => {
                (StatusCode::SERVICE_UNAVAILABLE, "circuit_breaker_open")
            }
            e if e.to_string().contains("not configured") => {
                (StatusCode::BAD_REQUEST, "invalid_model")
            }
            e if e.to_string().contains("timeout") => {
                (StatusCode::REQUEST_TIMEOUT, "timeout")
            }
            _ => (StatusCode::INTERNAL_SERVER_ERROR, "internal_error"),
        };

        let body = Json(ErrorResponse {
            error: self.0.to_string(),
            error_type: error_type.to_string(),
            request_id: None,
        });

        (status, body).into_response()
    }
}

struct AppError(anyhow::Error);

impl<E> From<E> for AppError
where
    E: Into<anyhow::Error>,
{
    fn from(err: E) -> Self {
        Self(err.into())
    }
}

// =============================================================================
// Application State
// =============================================================================

#[derive(Clone)]
struct AppState {
    service: Arc<ProductionDSpyService>,
}

// =============================================================================
// API Endpoints
// =============================================================================

/// POST /v1/predict - Make a prediction
async fn predict_handler(
    State(state): State<AppState>,
    Json(mut request): Json<PredictionRequest>,
) -> Result<Json<PredictionResponse>, AppError> {
    // Generate request ID if not provided
    if request.request_id.is_empty() {
        request.request_id = Uuid::new_v4().to_string();
    }

    info!(
        request_id = %request.request_id,
        model = %request.model,
        "Received prediction request"
    );

    let response = state.service.predict(request).await?;

    Ok(Json(response))
}

/// GET /health - Health check endpoint
async fn health_handler(State(state): State<AppState>) -> Json<HealthStatus> {
    let status = state.service.health().await;
    Json(status)
}

/// GET /ready - Readiness check endpoint
async fn ready_handler(State(state): State<AppState>) -> StatusCode {
    if state.service.ready().await {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    }
}

/// GET /metrics - Prometheus metrics endpoint
async fn metrics_handler(State(state): State<AppState>) -> Result<String, AppError> {
    let metrics = state.service.metrics()?;
    Ok(metrics)
}

/// GET /costs - Cost metrics endpoint
async fn costs_handler(State(state): State<AppState>) -> Json<HashMap<String, serde_json::Value>> {
    let metrics = state.service.cost_metrics();
    let json_metrics: HashMap<String, serde_json::Value> = metrics
        .into_iter()
        .map(|(k, v)| (k, serde_json::to_value(v).unwrap()))
        .collect();
    Json(json_metrics)
}

/// GET /config - Service configuration endpoint (for debugging)
async fn config_handler(State(state): State<AppState>) -> Json<serde_json::Value> {
    let config = state.service.config();

    // Return sanitized config (remove sensitive data)
    let sanitized = serde_json::json!({
        "service_name": config.service_name,
        "service_version": config.service_version,
        "memory_cache_size": config.memory_cache_size,
        "memory_cache_ttl_secs": config.memory_cache_ttl_secs,
        "redis_cache_ttl_secs": config.redis_cache_ttl_secs,
        "ab_testing_enabled": config.ab_testing_enabled,
        "default_variant": config.default_variant,
        "models": config.models.keys().collect::<Vec<_>>(),
    });

    Json(sanitized)
}

/// GET / - Root endpoint with service info
async fn root_handler() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "service": "complete-production-service",
        "version": env!("CARGO_PKG_VERSION"),
        "endpoints": {
            "predict": "POST /v1/predict",
            "health": "GET /health",
            "ready": "GET /ready",
            "metrics": "GET /metrics",
            "costs": "GET /costs",
            "config": "GET /config",
        }
    }))
}

// =============================================================================
// Server Setup
// =============================================================================

fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/", get(root_handler))
        .route("/v1/predict", post(predict_handler))
        .route("/health", get(health_handler))
        .route("/ready", get(ready_handler))
        .route("/metrics", get(metrics_handler))
        .route("/costs", get(costs_handler))
        .route("/config", get(config_handler))
        .with_state(state)
}

fn setup_middleware(router: Router, timeout_secs: u64) -> Router {
    router.layer(
        ServiceBuilder::new()
            .layer(
                TraceLayer::new_for_http()
                    .make_span_with(DefaultMakeSpan::new().level(Level::INFO))
                    .on_response(DefaultOnResponse::new().level(Level::INFO)),
            )
            .layer(CompressionLayer::new())
            .layer(CorsLayer::permissive())
            .layer(TimeoutLayer::new(Duration::from_secs(timeout_secs))),
    )
}

// =============================================================================
// Configuration Loading
// =============================================================================

fn load_config() -> anyhow::Result<(ServiceConfig, ServerConfig)> {
    // Load service configuration from environment
    let service_config = envy::from_env::<ServiceConfig>()
        .or_else(|_| {
            warn!("Failed to load config from environment, using defaults");
            create_default_service_config()
        })?;

    // Load server configuration
    let server_config = envy::from_env::<ServerConfig>().unwrap_or_else(|_| ServerConfig {
        host: default_host(),
        port: default_port(),
        request_timeout_secs: default_timeout(),
        log_level: default_log_level(),
        log_format: default_log_format(),
    });

    Ok((service_config, server_config))
}

fn create_default_service_config() -> anyhow::Result<ServiceConfig> {
    let mut models = HashMap::new();

    // Default models
    models.insert(
        "gpt-3.5-turbo".to_string(),
        complete_production_service::ModelConfig {
            name: "gpt-3.5-turbo".to_string(),
            cost_per_1k_input_tokens: 0.0015,
            cost_per_1k_output_tokens: 0.002,
            max_retries: 3,
            request_timeout_secs: 30,
        },
    );

    models.insert(
        "gpt-4".to_string(),
        complete_production_service::ModelConfig {
            name: "gpt-4".to_string(),
            cost_per_1k_input_tokens: 0.03,
            cost_per_1k_output_tokens: 0.06,
            max_retries: 3,
            request_timeout_secs: 60,
        },
    );

    Ok(ServiceConfig {
        service_name: "complete-production-service".to_string(),
        service_version: env!("CARGO_PKG_VERSION").to_string(),
        redis_url: std::env::var("REDIS_URL")
            .unwrap_or_else(|_| "redis://localhost:6379".to_string()),
        memory_cache_size: 10_000,
        memory_cache_ttl_secs: 300,
        redis_cache_ttl_secs: 3600,
        circuit_breaker_failure_threshold: 5,
        circuit_breaker_success_threshold: 2,
        circuit_breaker_timeout_secs: 60,
        models,
        ab_testing_enabled: false,
        default_variant: "baseline".to_string(),
    })
}

// =============================================================================
// Main
// =============================================================================

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Load configuration
    let (service_config, server_config) = load_config()?;

    // Setup logging
    let log_level = server_config
        .log_level
        .parse::<tracing::Level>()
        .unwrap_or(Level::INFO);

    if server_config.log_format == "json" {
        tracing_subscriber::registry()
            .with(
                tracing_subscriber::EnvFilter::try_from_default_env()
                    .unwrap_or_else(|_| format!("complete_production_service={}", log_level).into()),
            )
            .with(tracing_subscriber::fmt::layer().json())
            .init();
    } else {
        tracing_subscriber::registry()
            .with(
                tracing_subscriber::EnvFilter::try_from_default_env()
                    .unwrap_or_else(|_| format!("complete_production_service={}", log_level).into()),
            )
            .with(tracing_subscriber::fmt::layer())
            .init();
    }

    info!(
        service_name = %service_config.service_name,
        service_version = %service_config.service_version,
        "Starting production service"
    );

    // Create service
    let service = ProductionDSpyService::new(service_config).await?;
    info!("Production service initialized");

    // Create application state
    let state = AppState {
        service: Arc::new(service),
    };

    // Build router with middleware
    let app = build_router(state.clone());
    let app = setup_middleware(app, server_config.request_timeout_secs);

    // Bind to address
    let addr = SocketAddr::from((
        server_config
            .host
            .parse::<std::net::IpAddr>()
            .unwrap_or_else(|_| std::net::IpAddr::V4(std::net::Ipv4Addr::new(0, 0, 0, 0))),
        server_config.port,
    ));

    info!(
        host = %server_config.host,
        port = server_config.port,
        "Starting HTTP server"
    );

    // Create listener
    let listener = tokio::net::TcpListener::bind(addr).await?;

    info!("Server listening on http://{}", addr);

    // Setup graceful shutdown
    let shutdown_signal = async {
        tokio::signal::ctrl_c()
            .await
            .expect("Failed to install CTRL+C signal handler");
        info!("Received shutdown signal");
    };

    // Start server
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal)
        .await?;

    info!("Server shutdown complete");

    Ok(())
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use tower::ServiceExt;

    async fn create_test_app() -> Router {
        let service_config = create_default_service_config().unwrap();
        let service = ProductionDSpyService::new(service_config).await.unwrap();
        let state = AppState {
            service: Arc::new(service),
        };
        build_router(state)
    }

    #[tokio::test]
    async fn test_root_endpoint() {
        let app = create_test_app().await;

        let response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_health_endpoint() {
        let app = create_test_app().await;

        let response = app
            .oneshot(
                Request::builder()
                    .uri("/health")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_ready_endpoint() {
        let app = create_test_app().await;

        let response = app
            .oneshot(
                Request::builder()
                    .uri("/ready")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert!(response.status().is_success() || response.status() == StatusCode::SERVICE_UNAVAILABLE);
    }

    #[tokio::test]
    async fn test_metrics_endpoint() {
        let app = create_test_app().await;

        let response = app
            .oneshot(
                Request::builder()
                    .uri("/metrics")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_predict_endpoint() {
        let app = create_test_app().await;

        let request_body = serde_json::json!({
            "request_id": "test-123",
            "model": "gpt-3.5-turbo",
            "input": "test input",
            "parameters": {},
            "use_cache": true
        });

        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/v1/predict")
                    .header("content-type", "application/json")
                    .body(Body::from(serde_json::to_string(&request_body).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }
}
