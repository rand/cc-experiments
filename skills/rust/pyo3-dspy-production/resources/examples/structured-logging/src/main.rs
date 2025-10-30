//! Structured logging demonstration for DSPy production integration.
//!
//! This example demonstrates:
//! - Multi-layer logging setup (console + JSON file)
//! - Request ID generation and propagation
//! - Trace context through async operations
//! - Error logging with full context preservation
//! - Performance metrics collection and reporting

use anyhow::{anyhow, Context, Result};
use chrono::Utc;
use std::time::Instant;
use structured_logging::{
    DSpyEvent, InstrumentedDSpyService, LogFormat, LoggingConfig, MetricsAggregator,
    PerformanceMetric, RequestContext,
};
use tracing::{debug, error, info, instrument, warn};

// ============================================================================
// Demonstration Scenarios
// ============================================================================

/// Demonstrate basic request correlation
#[instrument]
async fn demo_request_correlation() -> Result<()> {
    info!("=== Request Correlation Demo ===");

    // Create root request context
    let root_context = RequestContext::new()
        .with_user_id("user_123".to_string())
        .with_metadata("source".to_string(), "api".to_string());

    info!(
        request_id = %root_context.request_id,
        user_id = ?root_context.user_id,
        "Root request created"
    );

    // Create child contexts to show correlation
    let child1 = root_context.child();
    info!(
        request_id = %child1.request_id,
        parent_id = ?child1.parent_id,
        "Child request 1 created"
    );

    let child2 = root_context.child();
    info!(
        request_id = %child2.request_id,
        parent_id = ?child2.parent_id,
        "Child request 2 created"
    );

    // Simulate nested operations
    process_with_context(&child1, "Operation 1").await?;
    process_with_context(&child2, "Operation 2").await?;

    info!("Request correlation demo completed");
    Ok(())
}

/// Helper function to process with context
#[instrument(skip(context), fields(request_id = %context.request_id))]
async fn process_with_context(context: &RequestContext, operation: &str) -> Result<()> {
    info!(operation = %operation, "Processing operation");

    // Simulate some work
    tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;

    debug!(operation = %operation, "Operation completed");
    Ok(())
}

/// Demonstrate DSPy event logging
#[instrument]
async fn demo_dspy_events() -> Result<()> {
    info!("=== DSPy Event Logging Demo ===");

    let context = RequestContext::new().with_metadata("demo".to_string(), "dspy_events".to_string());

    // Log different types of DSPy events
    let prediction_event = DSpyEvent::Prediction {
        model: "gpt-4".to_string(),
        prompt_tokens: 150,
        completion_tokens: 75,
        latency_ms: 1250,
    };
    prediction_event.log(&context);

    let optimization_event = DSpyEvent::Optimization {
        optimizer: "MIPROv2".to_string(),
        iteration: 5,
        score: 0.87,
        improvement: 0.12,
    };
    optimization_event.log(&context);

    let pipeline_event = DSpyEvent::Pipeline {
        pipeline: "qa_pipeline".to_string(),
        stage: "retrieval".to_string(),
        status: "completed".to_string(),
    };
    pipeline_event.log(&context);

    let cache_event = DSpyEvent::Cache {
        operation: "get".to_string(),
        hit: true,
        key: "prompt:abc123".to_string(),
    };
    cache_event.log(&context);

    info!("DSPy event logging demo completed");
    Ok(())
}

/// Demonstrate error handling with context preservation
#[instrument]
async fn demo_error_handling() -> Result<()> {
    info!("=== Error Handling Demo ===");

    let context = RequestContext::new()
        .with_user_id("user_456".to_string())
        .with_metadata("operation".to_string(), "error_demo".to_string());

    // Successful operation
    match execute_operation(&context, true).await {
        Ok(result) => {
            info!(
                request_id = %context.request_id,
                result = %result,
                "Operation succeeded"
            );
        }
        Err(e) => {
            error!(
                request_id = %context.request_id,
                error = %e,
                "Operation failed (unexpected)"
            );
        }
    }

    // Failed operation with context
    match execute_operation(&context, false).await {
        Ok(result) => {
            info!(
                request_id = %context.request_id,
                result = %result,
                "Operation succeeded (unexpected)"
            );
        }
        Err(e) => {
            error!(
                request_id = %context.request_id,
                error = %e,
                error_chain = ?e.chain().collect::<Vec<_>>(),
                "Operation failed with full error context"
            );
        }
    }

    // Nested error context
    if let Err(e) = nested_operation_with_error(&context).await {
        error!(
            request_id = %context.request_id,
            error = %e,
            "Nested operation failed"
        );
        for (idx, cause) in e.chain().enumerate() {
            error!(
                request_id = %context.request_id,
                level = idx,
                cause = %cause,
                "Error chain"
            );
        }
    }

    info!("Error handling demo completed");
    Ok(())
}

#[instrument(skip(context), fields(request_id = %context.request_id))]
async fn execute_operation(context: &RequestContext, succeed: bool) -> Result<String> {
    info!(succeed = succeed, "Executing operation");

    if succeed {
        Ok("Operation completed successfully".to_string())
    } else {
        Err(anyhow!("Operation failed: simulated error")).context("Failed to execute operation")
    }
}

#[instrument(skip(context), fields(request_id = %context.request_id))]
async fn nested_operation_with_error(context: &RequestContext) -> Result<()> {
    level_1(context)
        .await
        .context("Failed at top level")?;
    Ok(())
}

#[instrument(skip(context), fields(request_id = %context.request_id))]
async fn level_1(context: &RequestContext) -> Result<()> {
    level_2(context)
        .await
        .context("Failed at level 1")?;
    Ok(())
}

#[instrument(skip(context), fields(request_id = %context.request_id))]
async fn level_2(context: &RequestContext) -> Result<()> {
    level_3(context)
        .await
        .context("Failed at level 2")?;
    Ok(())
}

#[instrument(skip(_context), fields(request_id = %_context.request_id))]
async fn level_3(_context: &RequestContext) -> Result<()> {
    Err(anyhow!("Deep nested error at level 3"))
}

/// Demonstrate performance metrics collection
#[instrument]
async fn demo_performance_metrics() -> Result<()> {
    info!("=== Performance Metrics Demo ===");

    let metrics = MetricsAggregator::new();
    let context = RequestContext::new().with_metadata("demo".to_string(), "performance".to_string());

    // Record various operations
    for i in 0..10 {
        let start = Instant::now();

        // Simulate work with varying duration
        let duration_ms = 50 + (i * 10);
        tokio::time::sleep(tokio::time::Duration::from_millis(duration_ms)).await;

        let elapsed = start.elapsed().as_millis() as u64;
        let success = i % 3 != 0; // Simulate some failures

        metrics
            .record(PerformanceMetric {
                operation: format!("operation_{}", i),
                duration_ms: elapsed,
                success,
                timestamp: Utc::now(),
                context: context.child(),
            })
            .await;
    }

    // Get and display summary
    let summary = metrics.summarize().await;
    info!(
        total = summary.total_operations,
        successful = summary.successful_operations,
        mean_ms = summary.mean_duration_ms,
        p50_ms = summary.p50_duration_ms,
        p95_ms = summary.p95_duration_ms,
        p99_ms = summary.p99_duration_ms,
        max_ms = summary.max_duration_ms,
        "Performance metrics summary"
    );

    println!("\n{}", summary);

    info!("Performance metrics demo completed");
    Ok(())
}

/// Demonstrate instrumented DSPy service
#[instrument]
async fn demo_instrumented_service() -> Result<()> {
    info!("=== Instrumented Service Demo ===");

    let config = LoggingConfig {
        level: "debug".to_string(),
        format: LogFormat::Pretty,
        console_enabled: true,
        file_enabled: false,
        file_path: None,
        request_id_enabled: true,
        performance_metrics_enabled: true,
        dspy_instrumentation_enabled: true,
    };

    let service = InstrumentedDSpyService::new(config);
    let context = RequestContext::new()
        .with_user_id("user_789".to_string())
        .with_metadata("demo".to_string(), "instrumented_service".to_string());

    // Execute predictions
    info!("Executing predictions...");
    for i in 0..3 {
        let model = if i % 2 == 0 { "gpt-4" } else { "gpt-3.5-turbo" };
        let prompt = format!("What is the capital of country {}?", i);

        match service.predict(context.child(), model.to_string(), prompt).await {
            Ok(response) => {
                info!(
                    model = %model,
                    response_len = response.len(),
                    "Prediction succeeded"
                );
            }
            Err(e) => {
                error!(
                    model = %model,
                    error = %e,
                    "Prediction failed"
                );
            }
        }
    }

    // Execute optimization
    info!("Executing optimization...");
    match service
        .optimize(context.child(), "MIPROv2".to_string(), 5)
        .await
    {
        Ok(score) => {
            info!(score = score, "Optimization completed");
        }
        Err(e) => {
            error!(error = %e, "Optimization failed");
        }
    }

    // Execute pipeline
    info!("Executing pipeline...");
    let stages = vec![
        "retrieval".to_string(),
        "ranking".to_string(),
        "generation".to_string(),
    ];

    match service
        .execute_pipeline(context.child(), "qa_pipeline".to_string(), stages)
        .await
    {
        Ok(_) => {
            info!("Pipeline completed");
        }
        Err(e) => {
            error!(error = %e, "Pipeline failed");
        }
    }

    // Get metrics summary
    let summary = service.metrics_summary().await;
    info!("Service metrics summary");
    println!("\n{}", summary);

    info!("Instrumented service demo completed");
    Ok(())
}

/// Demonstrate concurrent operations with correlation
#[instrument]
async fn demo_concurrent_operations() -> Result<()> {
    info!("=== Concurrent Operations Demo ===");

    let root_context = RequestContext::new()
        .with_user_id("user_concurrent".to_string())
        .with_metadata("demo".to_string(), "concurrent".to_string());

    // Spawn multiple concurrent operations
    let mut handles = vec![];

    for i in 0..5 {
        let context = root_context.child();
        let handle = tokio::spawn(async move {
            concurrent_worker(context, i).await
        });
        handles.push(handle);
    }

    // Wait for all operations
    for (idx, handle) in handles.into_iter().enumerate() {
        match handle.await {
            Ok(Ok(_)) => {
                debug!(worker = idx, "Worker completed successfully");
            }
            Ok(Err(e)) => {
                warn!(worker = idx, error = %e, "Worker failed");
            }
            Err(e) => {
                error!(worker = idx, error = %e, "Worker panicked");
            }
        }
    }

    info!("Concurrent operations demo completed");
    Ok(())
}

#[instrument(skip(context), fields(request_id = %context.request_id))]
async fn concurrent_worker(context: RequestContext, worker_id: usize) -> Result<()> {
    info!(worker_id = worker_id, "Worker started");

    // Simulate varying work
    let duration = 50 + (worker_id * 20);
    tokio::time::sleep(tokio::time::Duration::from_millis(duration as u64)).await;

    // Simulate occasional failures
    if worker_id % 3 == 0 {
        warn!(worker_id = worker_id, "Worker encountered non-fatal issue");
    }

    info!(
        worker_id = worker_id,
        duration_ms = duration,
        "Worker completed"
    );
    Ok(())
}

/// Demonstrate log levels and filtering
#[instrument]
async fn demo_log_levels() -> Result<()> {
    info!("=== Log Levels Demo ===");

    let context = RequestContext::new();

    tracing::trace!(request_id = %context.request_id, "This is a TRACE message");
    tracing::debug!(request_id = %context.request_id, "This is a DEBUG message");
    tracing::info!(request_id = %context.request_id, "This is an INFO message");
    tracing::warn!(request_id = %context.request_id, "This is a WARN message");
    tracing::error!(request_id = %context.request_id, "This is an ERROR message");

    // Structured fields at different levels
    debug!(
        request_id = %context.request_id,
        field1 = "value1",
        field2 = 42,
        field3 = true,
        "Debug with structured fields"
    );

    info!(
        request_id = %context.request_id,
        user = "john_doe",
        action = "login",
        duration_ms = 125,
        "User action logged"
    );

    warn!(
        request_id = %context.request_id,
        threshold = 1000,
        actual = 1250,
        "Threshold exceeded"
    );

    info!("Log levels demo completed");
    Ok(())
}

// ============================================================================
// Main Entry Point
// ============================================================================

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging with pretty console output
    let config = LoggingConfig {
        level: "debug".to_string(),
        format: LogFormat::Pretty,
        console_enabled: true,
        file_enabled: false,
        file_path: None,
        request_id_enabled: true,
        performance_metrics_enabled: true,
        dspy_instrumentation_enabled: true,
    };

    structured_logging::init_logging(&config)?;

    info!("Starting structured logging demonstrations");
    info!(
        config = ?config,
        "Logging configuration"
    );

    // Run all demonstrations
    println!("\n{}", "=".repeat(80));
    demo_request_correlation().await?;

    println!("\n{}", "=".repeat(80));
    demo_dspy_events().await?;

    println!("\n{}", "=".repeat(80));
    demo_error_handling().await?;

    println!("\n{}", "=".repeat(80));
    demo_performance_metrics().await?;

    println!("\n{}", "=".repeat(80));
    demo_instrumented_service().await?;

    println!("\n{}", "=".repeat(80));
    demo_concurrent_operations().await?;

    println!("\n{}", "=".repeat(80));
    demo_log_levels().await?;

    println!("\n{}", "=".repeat(80));
    info!("All demonstrations completed successfully");

    Ok(())
}
