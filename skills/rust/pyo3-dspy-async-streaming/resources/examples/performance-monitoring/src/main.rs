//! Performance Monitoring Demo Application
//!
//! Demonstrates comprehensive async performance monitoring with:
//! - Prometheus metrics endpoint
//! - Live performance dashboard
//! - Sync vs async comparison
//! - Load testing capabilities

use anyhow::Result;
use axum::{
    extract::State,
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use performance_monitoring::{PerformanceMonitor, PerformanceReport};
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tokio::time::sleep;
use tracing::{info, instrument};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

/// Application state shared across handlers
#[derive(Clone)]
struct AppState {
    monitor: PerformanceMonitor,
}

/// Dashboard data for visualization
#[derive(Debug, Serialize, Deserialize)]
struct DashboardData {
    performance_report: PerformanceReport,
    metrics_url: String,
    grafana_url: String,
}

/// Comparison report structure
#[derive(Debug, Serialize, Deserialize)]
struct ComparisonReport {
    sync_results: BenchmarkResults,
    async_results: BenchmarkResults,
    improvement: ImprovementMetrics,
}

/// Benchmark results
#[derive(Debug, Serialize, Deserialize)]
struct BenchmarkResults {
    total_requests: u64,
    duration_seconds: f64,
    throughput_rps: f64,
    latency_p50_ms: f64,
    latency_p95_ms: f64,
    latency_p99_ms: f64,
    success_rate: f64,
}

/// Improvement metrics
#[derive(Debug, Serialize, Deserialize)]
struct ImprovementMetrics {
    throughput_multiplier: f64,
    latency_p99_reduction: f64,
    efficiency_gain: f64,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info,performance_monitoring=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    info!("Starting performance monitoring demo");

    // Parse command line arguments
    let args: Vec<String> = std::env::args().collect();
    if args.len() > 1 {
        match args[1].as_str() {
            "--compare" => {
                run_comparison().await?;
                return Ok(());
            }
            "--load-test" => {
                let duration = args
                    .get(3)
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(60);
                let concurrency = args
                    .get(5)
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(100);
                run_load_test(duration, concurrency).await?;
                return Ok(());
            }
            "--help" => {
                print_help();
                return Ok(());
            }
            _ => {
                eprintln!("Unknown argument: {}", args[1]);
                print_help();
                return Ok(());
            }
        }
    }

    // Create performance monitor
    let monitor = PerformanceMonitor::new("performance_demo");

    // Create app state
    let state = AppState {
        monitor: monitor.clone(),
    };

    // Build router
    let app = Router::new()
        .route("/", get(root_handler))
        .route("/metrics", get(metrics_handler))
        .route("/dashboard", get(dashboard_handler))
        .route("/health", get(health_handler))
        .route("/predict", get(predict_handler))
        .route("/load", get(load_handler))
        .with_state(state);

    // Start background monitoring task
    let monitor_clone = monitor.clone();
    tokio::spawn(async move {
        background_monitoring(monitor_clone).await;
    });

    // Start server
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
    info!("Server listening on http://0.0.0.0:3000");
    info!("Metrics available at http://0.0.0.0:3000/metrics");
    info!("Dashboard available at http://0.0.0.0:3000/dashboard");

    axum::serve(listener, app).await?;

    Ok(())
}

/// Root handler with API information
async fn root_handler() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "service": "Performance Monitoring Demo",
        "endpoints": {
            "metrics": "/metrics",
            "dashboard": "/dashboard",
            "health": "/health",
            "predict": "/predict",
            "load": "/load?count=100"
        },
        "grafana": "http://localhost:3001",
        "prometheus": "http://localhost:9090"
    }))
}

/// Prometheus metrics endpoint
#[instrument(skip(state))]
async fn metrics_handler(State(state): State<AppState>) -> Response {
    let metrics = state.monitor.export_prometheus();
    (
        StatusCode::OK,
        [("Content-Type", "text/plain; version=0.0.4")],
        metrics,
    )
        .into_response()
}

/// Dashboard data endpoint (JSON)
#[instrument(skip(state))]
async fn dashboard_handler(State(state): State<AppState>) -> Json<DashboardData> {
    let report = state.monitor.report();

    Json(DashboardData {
        performance_report: report,
        metrics_url: "http://localhost:3000/metrics".to_string(),
        grafana_url: "http://localhost:3001".to_string(),
    })
}

/// Health check endpoint
async fn health_handler() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "healthy",
        "timestamp": chrono::Utc::now(),
    }))
}

/// Simulated prediction endpoint
#[instrument(skip(state))]
async fn predict_handler(State(state): State<AppState>) -> Json<serde_json::Value> {
    let result = state
        .monitor
        .track_async("prediction", async {
            // Simulate async work with variable latency
            let latency = 10 + (rand::random::<u64>() % 20);
            sleep(Duration::from_millis(latency)).await;

            // Simulate occasional failures (5%)
            if rand::random::<u8>() < 13 {
                anyhow::bail!("Random failure");
            }

            Ok::<_, anyhow::Error>(serde_json::json!({
                "prediction": "positive",
                "confidence": 0.95,
                "latency_ms": latency,
            }))
        })
        .await;

    match result {
        Ok(data) => Json(data),
        Err(e) => Json(serde_json::json!({
            "error": e.to_string(),
        })),
    }
}

/// Load test endpoint
#[instrument(skip(state))]
async fn load_handler(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<std::collections::HashMap<String, String>>,
) -> Json<serde_json::Value> {
    let count: usize = params
        .get("count")
        .and_then(|s| s.parse().ok())
        .unwrap_or(100);

    info!("Starting load test with {} requests", count);

    let start = std::time::Instant::now();
    let mut tasks = Vec::new();

    for _ in 0..count {
        let monitor = state.monitor.clone();
        tasks.push(tokio::spawn(async move {
            monitor
                .track_async("load_test", async {
                    sleep(Duration::from_millis(5 + (rand::random::<u64>() % 10))).await;
                    Ok::<_, anyhow::Error>(())
                })
                .await
        }));
    }

    // Wait for all tasks
    let results = futures::future::join_all(tasks).await;
    let success_count = results.iter().filter(|r| r.is_ok()).count();

    let duration = start.elapsed();

    Json(serde_json::json!({
        "total_requests": count,
        "successful": success_count,
        "duration_seconds": duration.as_secs_f64(),
        "throughput_rps": count as f64 / duration.as_secs_f64(),
    }))
}

/// Background monitoring task
async fn background_monitoring(monitor: PerformanceMonitor) {
    let mut interval = tokio::time::interval(Duration::from_secs(10));

    loop {
        interval.tick().await;

        // Generate some background load
        for _ in 0..5 {
            let monitor = monitor.clone();
            tokio::spawn(async move {
                let _ = monitor
                    .track_async("background_task", async {
                        sleep(Duration::from_millis(5)).await;
                        Ok::<_, anyhow::Error>(())
                    })
                    .await;
            });
        }
    }
}

/// Run sync vs async comparison
async fn run_comparison() -> Result<()> {
    println!("\nPerformance Comparison: Sync vs Async");
    println!("======================================\n");

    let request_count = 1000;

    // Run sync benchmark
    println!("Running synchronous benchmark...");
    let sync_results = run_sync_benchmark(request_count).await?;

    // Run async benchmark
    println!("Running asynchronous benchmark...");
    let async_results = run_async_benchmark(request_count).await?;

    // Calculate improvements
    let improvement = ImprovementMetrics {
        throughput_multiplier: async_results.throughput_rps / sync_results.throughput_rps,
        latency_p99_reduction: ((sync_results.latency_p99_ms - async_results.latency_p99_ms)
            / sync_results.latency_p99_ms)
            * 100.0,
        efficiency_gain: ((async_results.throughput_rps - sync_results.throughput_rps)
            / sync_results.throughput_rps)
            * 100.0,
    };

    // Print results
    print_comparison_report(&ComparisonReport {
        sync_results,
        async_results,
        improvement,
    });

    Ok(())
}

/// Run synchronous benchmark
async fn run_sync_benchmark(count: usize) -> Result<BenchmarkResults> {
    let monitor = PerformanceMonitor::new("sync_benchmark");
    let start = std::time::Instant::now();

    for _ in 0..count {
        // Simulate synchronous blocking work
        std::thread::sleep(Duration::from_millis(10));
        monitor.record_latency("sync_task", Duration::from_millis(10));
        monitor.record_throughput("sync_task");
    }

    let duration = start.elapsed();
    let stats = monitor.get_stats("sync_task").unwrap();

    Ok(BenchmarkResults {
        total_requests: count as u64,
        duration_seconds: duration.as_secs_f64(),
        throughput_rps: count as f64 / duration.as_secs_f64(),
        latency_p50_ms: stats.latency_ms.p50_ms,
        latency_p95_ms: stats.latency_ms.p95_ms,
        latency_p99_ms: stats.latency_ms.p99_ms,
        success_rate: 100.0,
    })
}

/// Run asynchronous benchmark
async fn run_async_benchmark(count: usize) -> Result<BenchmarkResults> {
    let monitor = PerformanceMonitor::new("async_benchmark");
    let start = std::time::Instant::now();

    let mut tasks = Vec::new();
    for _ in 0..count {
        let monitor = monitor.clone();
        tasks.push(tokio::spawn(async move {
            monitor
                .track_async("async_task", async {
                    sleep(Duration::from_millis(10)).await;
                    Ok::<_, anyhow::Error>(())
                })
                .await
        }));
    }

    // Wait for all tasks
    futures::future::join_all(tasks).await;

    let duration = start.elapsed();
    let stats = monitor.get_stats("async_task").unwrap();

    Ok(BenchmarkResults {
        total_requests: count as u64,
        duration_seconds: duration.as_secs_f64(),
        throughput_rps: count as f64 / duration.as_secs_f64(),
        latency_p50_ms: stats.latency_ms.p50_ms,
        latency_p95_ms: stats.latency_ms.p95_ms,
        latency_p99_ms: stats.latency_ms.p99_ms,
        success_rate: stats.task_stats.success_rate,
    })
}

/// Print comparison report
fn print_comparison_report(report: &ComparisonReport) {
    println!("\nSynchronous Implementation:");
    println!("  Total requests: {}", report.sync_results.total_requests);
    println!("  Duration: {:.3}s", report.sync_results.duration_seconds);
    println!("  Throughput: {:.1} req/s", report.sync_results.throughput_rps);
    println!("  Latency p50: {:.2}ms", report.sync_results.latency_p50_ms);
    println!("  Latency p95: {:.2}ms", report.sync_results.latency_p95_ms);
    println!("  Latency p99: {:.2}ms", report.sync_results.latency_p99_ms);
    println!("  Success rate: {:.1}%", report.sync_results.success_rate);

    println!("\nAsynchronous Implementation:");
    println!("  Total requests: {}", report.async_results.total_requests);
    println!("  Duration: {:.3}s", report.async_results.duration_seconds);
    println!("  Throughput: {:.1} req/s", report.async_results.throughput_rps);
    println!("  Latency p50: {:.2}ms", report.async_results.latency_p50_ms);
    println!("  Latency p95: {:.2}ms", report.async_results.latency_p95_ms);
    println!("  Latency p99: {:.2}ms", report.async_results.latency_p99_ms);
    println!("  Success rate: {:.1}%", report.async_results.success_rate);

    println!("\nImprovement:");
    println!(
        "  Throughput: {:.1}x faster",
        report.improvement.throughput_multiplier
    );
    println!(
        "  Latency p99: {:.1}% lower",
        report.improvement.latency_p99_reduction
    );
    println!(
        "  Efficiency gain: {:.1}%",
        report.improvement.efficiency_gain
    );
}

/// Run load test
async fn run_load_test(duration_seconds: u64, concurrency: usize) -> Result<()> {
    println!("\nLoad Test Configuration:");
    println!("  Duration: {}s", duration_seconds);
    println!("  Concurrency: {}", concurrency);
    println!();

    let monitor = PerformanceMonitor::new("load_test");
    let start = std::time::Instant::now();
    let end_time = start + Duration::from_secs(duration_seconds);

    let mut handles = Vec::new();

    for _ in 0..concurrency {
        let monitor = monitor.clone();
        let handle = tokio::spawn(async move {
            let mut request_count = 0;
            while std::time::Instant::now() < end_time {
                let _ = monitor
                    .track_async("load_request", async {
                        sleep(Duration::from_millis(10 + (rand::random::<u64>() % 20))).await;
                        Ok::<_, anyhow::Error>(())
                    })
                    .await;
                request_count += 1;
            }
            request_count
        });
        handles.push(handle);
    }

    // Wait for all workers
    let results = futures::future::join_all(handles).await;
    let total_requests: usize = results.iter().filter_map(|r| r.as_ref().ok()).sum();

    let actual_duration = start.elapsed();

    // Print results
    println!("\nLoad Test Results:");
    println!("  Total requests: {}", total_requests);
    println!("  Duration: {:.2}s", actual_duration.as_secs_f64());
    println!(
        "  Throughput: {:.1} req/s",
        total_requests as f64 / actual_duration.as_secs_f64()
    );

    if let Some(stats) = monitor.get_stats("load_request") {
        println!("\n  Latency:");
        println!("    p50: {:.2}ms", stats.latency_ms.p50_ms);
        println!("    p95: {:.2}ms", stats.latency_ms.p95_ms);
        println!("    p99: {:.2}ms", stats.latency_ms.p99_ms);
        println!("    p99.9: {:.2}ms", stats.latency_ms.p99_9_ms);

        println!("\n  Tasks:");
        println!("    Completed: {}", stats.task_stats.completed);
        println!("    Failed: {}", stats.task_stats.failed);
        println!("    Success rate: {:.1}%", stats.task_stats.success_rate);
    }

    Ok(())
}

/// Print help message
fn print_help() {
    println!("Performance Monitoring Demo");
    println!();
    println!("Usage:");
    println!("  cargo run                              Start monitoring server");
    println!("  cargo run -- --compare                 Run sync vs async comparison");
    println!("  cargo run -- --load-test --duration 60 --concurrency 100");
    println!("                                         Run load test");
    println!();
    println!("Endpoints:");
    println!("  http://localhost:3000/                 API information");
    println!("  http://localhost:3000/metrics          Prometheus metrics");
    println!("  http://localhost:3000/dashboard        Dashboard data (JSON)");
    println!("  http://localhost:3000/predict          Simulated prediction");
    println!("  http://localhost:3000/load?count=100   Load test");
    println!();
    println!("Monitoring:");
    println!("  http://localhost:9090                  Prometheus UI");
    println!("  http://localhost:3001                  Grafana UI");
}
