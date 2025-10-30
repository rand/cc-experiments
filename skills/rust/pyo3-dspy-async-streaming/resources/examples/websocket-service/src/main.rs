//! WebSocket Service Main Server
//!
//! Production-ready Axum server with WebSocket support for real-time AI streaming.

use anyhow::{Context, Result};
use axum::{
    extract::{ws::WebSocketUpgrade, State},
    http::{header, Method, StatusCode},
    response::{Html, IntoResponse, Json, Response},
    routing::get,
    Router,
};
use serde::Serialize;
use std::{
    net::SocketAddr,
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::signal;
use tower::ServiceBuilder;
use tower_http::{
    cors::{Any, CorsLayer},
    services::ServeDir,
    trace::TraceLayer,
};
use tracing::{info, warn};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};
use websocket_service::{ConnectionManager, WebSocketHandler};

/// Application state shared across handlers
#[derive(Clone)]
struct AppState {
    manager: ConnectionManager,
    start_time: Arc<Instant>,
}

/// Health check response
#[derive(Serialize)]
struct HealthResponse {
    status: String,
    connections: usize,
    uptime_seconds: u64,
    version: String,
}

/// Error response
#[derive(Serialize)]
struct ErrorResponse {
    error: String,
    code: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "websocket_service=debug,tower_http=debug,axum=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    info!("Starting WebSocket service...");

    // Initialize Python interpreter
    pyo3::prepare_freethreaded_python();
    info!("Python interpreter initialized");

    // Create application state
    let state = AppState {
        manager: ConnectionManager::new(),
        start_time: Arc::new(Instant::now()),
    };

    // Build router
    let app = create_router(state);

    // Get bind address from environment
    let host = std::env::var("HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
    let port = std::env::var("PORT").unwrap_or_else(|_| "8080".to_string());
    let addr: SocketAddr = format!("{}:{}", host, port)
        .parse()
        .context("Invalid HOST or PORT")?;

    info!("Listening on http://{}", addr);
    info!("WebSocket endpoint: ws://{}/ws", addr);
    info!("Health check: http://{}/health", addr);

    // Create TCP listener
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .context("Failed to bind to address")?;

    // Start server with graceful shutdown
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .context("Server error")?;

    info!("Server stopped");
    Ok(())
}

/// Create application router with all routes and middleware
fn create_router(state: AppState) -> Router {
    // CORS configuration
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods([Method::GET, Method::POST])
        .allow_headers([header::CONTENT_TYPE, header::AUTHORIZATION]);

    // Static file serving
    let static_files = ServeDir::new("static");

    // Build router
    Router::new()
        // WebSocket endpoint
        .route("/ws", get(websocket_handler))
        // Health check endpoint
        .route("/health", get(health_handler))
        // Metrics endpoint (optional)
        .route("/metrics", get(metrics_handler))
        // Root - serve static HTML client
        .route("/", get(root_handler))
        // Static files
        .nest_service("/static", static_files)
        // 404 handler
        .fallback(not_found_handler)
        // Application state
        .with_state(state)
        // Middleware
        .layer(
            ServiceBuilder::new()
                .layer(TraceLayer::new_for_http())
                .layer(cors),
        )
}

/// WebSocket upgrade handler
async fn websocket_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
) -> impl IntoResponse {
    info!("WebSocket upgrade request received");
    ws.on_upgrade(move |socket| {
        let handler = WebSocketHandler::new(state.manager);
        handler.handle(socket)
    })
}

/// Health check handler
async fn health_handler(State(state): State<AppState>) -> impl IntoResponse {
    let connections = state.manager.connection_count().await;
    let uptime = state.start_time.elapsed();

    let response = HealthResponse {
        status: "healthy".to_string(),
        connections,
        uptime_seconds: uptime.as_secs(),
        version: env!("CARGO_PKG_VERSION").to_string(),
    };

    Json(response)
}

/// Metrics handler for monitoring
async fn metrics_handler(State(state): State<AppState>) -> impl IntoResponse {
    let connections = state.manager.connection_count().await;
    let sessions = state.manager.session_count().await;
    let uptime = state.start_time.elapsed();

    // Prometheus-style metrics
    let metrics = format!(
        "# HELP websocket_connections_total Total active WebSocket connections\n\
         # TYPE websocket_connections_total gauge\n\
         websocket_connections_total {}\n\
         \n\
         # HELP websocket_sessions_total Total active sessions\n\
         # TYPE websocket_sessions_total gauge\n\
         websocket_sessions_total {}\n\
         \n\
         # HELP websocket_uptime_seconds Server uptime in seconds\n\
         # TYPE websocket_uptime_seconds counter\n\
         websocket_uptime_seconds {}\n",
        connections,
        sessions,
        uptime.as_secs()
    );

    (
        StatusCode::OK,
        [(header::CONTENT_TYPE, "text/plain; version=0.0.4")],
        metrics,
    )
}

/// Root handler - serves static HTML client
async fn root_handler() -> impl IntoResponse {
    // Serve inline HTML if static file not found
    let html = include_str!("../static/index.html");
    Html(html)
}

/// 404 handler
async fn not_found_handler() -> impl IntoResponse {
    let error = ErrorResponse {
        error: "Not found".to_string(),
        code: "not_found".to_string(),
    };
    (StatusCode::NOT_FOUND, Json(error))
}

/// Graceful shutdown signal handler
async fn shutdown_signal() {
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
            info!("Received Ctrl+C, shutting down gracefully...");
        },
        _ = terminate => {
            info!("Received terminate signal, shutting down gracefully...");
        },
    }

    // Give connections time to close gracefully
    tokio::time::sleep(Duration::from_secs(2)).await;
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{Request, StatusCode},
    };
    use tower::ServiceExt;

    #[tokio::test]
    async fn test_health_endpoint() {
        let state = AppState {
            manager: ConnectionManager::new(),
            start_time: Arc::new(Instant::now()),
        };

        let app = create_router(state);

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
    async fn test_metrics_endpoint() {
        let state = AppState {
            manager: ConnectionManager::new(),
            start_time: Arc::new(Instant::now()),
        };

        let app = create_router(state);

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

        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .unwrap();
        let body_str = String::from_utf8(body.to_vec()).unwrap();

        assert!(body_str.contains("websocket_connections_total"));
        assert!(body_str.contains("websocket_sessions_total"));
    }

    #[tokio::test]
    async fn test_not_found() {
        let state = AppState {
            manager: ConnectionManager::new(),
            start_time: Arc::new(Instant::now()),
        };

        let app = create_router(state);

        let response = app
            .oneshot(
                Request::builder()
                    .uri("/nonexistent")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_cors_headers() {
        let state = AppState {
            manager: ConnectionManager::new(),
            start_time: Arc::new(Instant::now()),
        };

        let app = create_router(state);

        let response = app
            .oneshot(
                Request::builder()
                    .uri("/health")
                    .header("Origin", "http://example.com")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
        assert!(response.headers().contains_key("access-control-allow-origin"));
    }
}
