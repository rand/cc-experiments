//! Production Agent Service - HTTP API Server
//!
//! Enterprise-ready HTTP API for DSPy agent orchestration using Axum.

use anyhow::Result;
use axum::{
    extract::{Json, State},
    http::{HeaderValue, Method, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post},
    Router,
};
use production_agent_service::{
    AgentConfig, AgentError, HealthStatus, ProductionAgentSystem, QueryRequest, QueryResponse,
};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Duration;
use tower::ServiceBuilder;
use tower_http::{
    cors::CorsLayer,
    timeout::TimeoutLayer,
    trace::{DefaultMakeSpan, DefaultOnResponse, TraceLayer},
};
use tracing::{info, Level};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

// ============================================================================
// Application State
// ============================================================================

#[derive(Clone)]
struct AppState {
    agent_system: Arc<ProductionAgentSystem>,
}

impl AppState {
    async fn new(config: AgentConfig) -> Result<Self> {
        let agent_system = ProductionAgentSystem::new(config).await?;

        Ok(Self {
            agent_system: Arc::new(agent_system),
        })
    }
}

// ============================================================================
// Error Response
// ============================================================================

#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
    message: String,
    request_id: Option<String>,
}

impl IntoResponse for AgentError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            AgentError::PythonError(_) => (StatusCode::INTERNAL_SERVER_ERROR, self.to_string()),
            AgentError::PoolExhausted => (StatusCode::SERVICE_UNAVAILABLE, self.to_string()),
            AgentError::CircuitBreakerOpen(_) => (StatusCode::SERVICE_UNAVAILABLE, self.to_string()),
            AgentError::ExecutionFailed(_) => (StatusCode::INTERNAL_SERVER_ERROR, self.to_string()),
            AgentError::MemoryError(_) => (StatusCode::INTERNAL_SERVER_ERROR, self.to_string()),
            AgentError::ConfigError(_) => (StatusCode::BAD_REQUEST, self.to_string()),
            AgentError::Timeout(_) => (StatusCode::GATEWAY_TIMEOUT, self.to_string()),
        };

        let error_type = match &self {
            AgentError::PythonError(_) => "python_error",
            AgentError::PoolExhausted => "pool_exhausted",
            AgentError::CircuitBreakerOpen(_) => "circuit_breaker_open",
            AgentError::ExecutionFailed(_) => "execution_failed",
            AgentError::MemoryError(_) => "memory_error",
            AgentError::ConfigError(_) => "config_error",
            AgentError::Timeout(_) => "timeout",
        };

        let error_response = ErrorResponse {
            error: error_type.to_string(),
            message,
            request_id: Some(uuid::Uuid::new_v4().to_string()),
        };

        (status, Json(error_response)).into_response()
    }
}

// ============================================================================
// HTTP Handlers
// ============================================================================

/// POST /api/v1/query - Execute agent query
async fn query_handler(
    State(state): State<AppState>,
    Json(request): Json<QueryRequest>,
) -> Result<Json<QueryResponse>, AgentError> {
    info!("Received query from user: {}", request.user_id);

    // Validate request
    if request.user_id.is_empty() {
        return Err(AgentError::ConfigError("user_id cannot be empty".to_string()));
    }

    if request.question.is_empty() {
        return Err(AgentError::ConfigError("question cannot be empty".to_string()));
    }

    // Execute query
    let response = state.agent_system.execute_query(request).await
        .map_err(|e| match e.downcast::<AgentError>() {
            Ok(agent_err) => agent_err,
            Err(other_err) => AgentError::ExecutionFailed(other_err.to_string()),
        })?;

    info!(
        "Query completed successfully in {}ms",
        response.latency_ms
    );

    Ok(Json(response))
}

/// GET /api/v1/metrics - Prometheus metrics endpoint
async fn metrics_handler(State(state): State<AppState>) -> impl IntoResponse {
    let metrics = state.agent_system.get_metrics();

    (
        StatusCode::OK,
        [(
            axum::http::header::CONTENT_TYPE,
            HeaderValue::from_static("text/plain; version=0.0.4"),
        )],
        metrics,
    )
}

/// GET /api/v1/health - Health check endpoint
async fn health_handler(State(state): State<AppState>) -> Json<HealthStatus> {
    let health = state.agent_system.health_check();

    info!("Health check: status={}", health.status);

    Json(health)
}

/// GET /api/v1/ready - Readiness probe
async fn readiness_handler(State(state): State<AppState>) -> impl IntoResponse {
    let pool_size = state.agent_system.pool_size().await;

    if pool_size > 0 {
        (StatusCode::OK, "ready")
    } else {
        (StatusCode::SERVICE_UNAVAILABLE, "not ready")
    }
}

/// GET /api/v1/live - Liveness probe
async fn liveness_handler() -> impl IntoResponse {
    (StatusCode::OK, "alive")
}

/// GET /api/v1/info - Service information
async fn info_handler() -> Json<ServiceInfo> {
    Json(ServiceInfo {
        name: env!("CARGO_PKG_NAME").to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        description: env!("CARGO_PKG_DESCRIPTION").to_string(),
        endpoints: vec![
            EndpointInfo {
                path: "/api/v1/query".to_string(),
                method: "POST".to_string(),
                description: "Execute agent query".to_string(),
            },
            EndpointInfo {
                path: "/api/v1/metrics".to_string(),
                method: "GET".to_string(),
                description: "Prometheus metrics".to_string(),
            },
            EndpointInfo {
                path: "/api/v1/health".to_string(),
                method: "GET".to_string(),
                description: "Health check".to_string(),
            },
            EndpointInfo {
                path: "/api/v1/ready".to_string(),
                method: "GET".to_string(),
                description: "Readiness probe".to_string(),
            },
            EndpointInfo {
                path: "/api/v1/live".to_string(),
                method: "GET".to_string(),
                description: "Liveness probe".to_string(),
            },
        ],
    })
}

/// POST /api/v1/circuit-breaker/reset - Reset circuit breaker
async fn circuit_breaker_reset_handler(
    State(state): State<AppState>,
) -> impl IntoResponse {
    state.agent_system.reset_circuit_breaker();
    info!("Circuit breaker manually reset");

    (StatusCode::OK, Json(serde_json::json!({
        "status": "reset",
        "message": "Circuit breaker has been reset to closed state"
    })))
}

// ============================================================================
// Response Types
// ============================================================================

#[derive(Debug, Serialize, Deserialize)]
struct ServiceInfo {
    name: String,
    version: String,
    description: String,
    endpoints: Vec<EndpointInfo>,
}

#[derive(Debug, Serialize, Deserialize)]
struct EndpointInfo {
    path: String,
    method: String,
    description: String,
}

// ============================================================================
// Server Configuration
// ============================================================================

#[derive(Debug, Clone)]
struct ServerConfig {
    host: String,
    port: u16,
    request_timeout_secs: u64,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            host: std::env::var("SERVER_HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            port: std::env::var("SERVER_PORT")
                .ok()
                .and_then(|p| p.parse().ok())
                .unwrap_or(3000),
            request_timeout_secs: std::env::var("REQUEST_TIMEOUT_SECS")
                .ok()
                .and_then(|t| t.parse().ok())
                .unwrap_or(30),
        }
    }
}

// ============================================================================
// Application Setup
// ============================================================================

fn create_app(state: AppState) -> Router {
    // API routes
    let api_routes = Router::new()
        .route("/query", post(query_handler))
        .route("/metrics", get(metrics_handler))
        .route("/health", get(health_handler))
        .route("/ready", get(readiness_handler))
        .route("/live", get(liveness_handler))
        .route("/info", get(info_handler))
        .route("/circuit-breaker/reset", post(circuit_breaker_reset_handler));

    // Root router
    Router::new()
        .nest("/api/v1", api_routes)
        .with_state(state)
}

fn create_middleware_stack(timeout_secs: u64) -> ServiceBuilder<
    tower::layer::util::Stack<
        TraceLayer<tower_http::classify::SharedClassifier<tower_http::classify::ServerErrorsAsFailures>>,
        tower::layer::util::Stack<TimeoutLayer, tower::layer::util::Stack<CorsLayer, tower::layer::util::Identity>>
    >
> {
    ServiceBuilder::new()
        // CORS
        .layer(
            CorsLayer::new()
                .allow_origin("*".parse::<HeaderValue>().unwrap())
                .allow_methods([Method::GET, Method::POST])
                .allow_headers([axum::http::header::CONTENT_TYPE]),
        )
        // Timeout
        .layer(TimeoutLayer::new(Duration::from_secs(timeout_secs)))
        // Tracing
        .layer(
            TraceLayer::new_for_http()
                .make_span_with(DefaultMakeSpan::new().level(Level::INFO))
                .on_response(DefaultOnResponse::new().level(Level::INFO)),
        )
}

// ============================================================================
// Main Entry Point
// ============================================================================

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    init_tracing()?;

    info!("Starting Production Agent Service v{}", env!("CARGO_PKG_VERSION"));

    // Load configuration
    let server_config = ServerConfig::default();
    let agent_config = load_agent_config();

    info!("Server configuration: {:?}", server_config);
    info!("Agent configuration: {:?}", agent_config);

    // Initialize application state
    info!("Initializing agent system...");
    let state = AppState::new(agent_config).await?;
    info!("Agent system initialized successfully");

    // Create application with middleware
    let app = create_app(state.clone())
        .layer(create_middleware_stack(server_config.request_timeout_secs));

    // Bind server
    let addr = SocketAddr::from((
        server_config.host.parse::<std::net::IpAddr>()?,
        server_config.port,
    ));

    info!("Server listening on http://{}", addr);
    info!("API endpoints:");
    info!("  POST http://{}/api/v1/query", addr);
    info!("  GET  http://{}/api/v1/metrics", addr);
    info!("  GET  http://{}/api/v1/health", addr);
    info!("  GET  http://{}/api/v1/ready", addr);
    info!("  GET  http://{}/api/v1/live", addr);
    info!("  GET  http://{}/api/v1/info", addr);

    // Setup graceful shutdown
    let shutdown_signal = shutdown_signal();

    // Start server
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal)
        .await?;

    // Save memories on shutdown
    info!("Shutting down gracefully...");
    state.agent_system.save_all_memories("./agent_memories").await?;
    info!("Agent memories saved");

    info!("Server shutdown complete");

    Ok(())
}

// ============================================================================
// Utility Functions
// ============================================================================

fn init_tracing() -> Result<()> {
    let log_format = std::env::var("LOG_FORMAT").unwrap_or_else(|_| "pretty".to_string());

    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info,production_agent_service=debug"));

    if log_format == "json" {
        tracing_subscriber::registry()
            .with(env_filter)
            .with(tracing_subscriber::fmt::layer().json())
            .init();
    } else {
        tracing_subscriber::registry()
            .with(env_filter)
            .with(tracing_subscriber::fmt::layer().pretty())
            .init();
    }

    Ok(())
}

fn load_agent_config() -> AgentConfig {
    AgentConfig {
        pool_size: std::env::var("AGENT_POOL_SIZE")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(4),
        max_retries: std::env::var("AGENT_MAX_RETRIES")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(3),
        request_timeout: Duration::from_secs(
            std::env::var("AGENT_REQUEST_TIMEOUT_SECS")
                .ok()
                .and_then(|s| s.parse().ok())
                .unwrap_or(30),
        ),
        circuit_breaker_threshold: std::env::var("CIRCUIT_BREAKER_THRESHOLD")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(5),
        circuit_breaker_timeout: Duration::from_secs(
            std::env::var("CIRCUIT_BREAKER_TIMEOUT_SECS")
                .ok()
                .and_then(|s| s.parse().ok())
                .unwrap_or(30),
        ),
        memory_context_turns: std::env::var("MEMORY_CONTEXT_TURNS")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(3),
    }
}

async fn shutdown_signal() {
    use tokio::signal;

    let ctrl_c = async {
        signal::ctrl_c()
            .await
            .expect("Failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("Failed to install signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {
            info!("Received Ctrl+C signal");
        },
        _ = terminate => {
            info!("Received terminate signal");
        },
    }
}
