//! Comprehensive examples of timeout and cancellation patterns
//!
//! This binary demonstrates various timeout and cancellation patterns for
//! async operations, particularly useful when integrating with PyO3 and DSPy.

use anyhow::{Context, Result};
use std::time::{Duration, Instant};
use timeout_cancellation::*;
use tokio_util::sync::CancellationToken;
use tracing::{error, info, warn};
use tracing_subscriber::{fmt, prelude::*, EnvFilter};

/// Simulated slow operation (like a DSPy prediction)
async fn slow_operation(name: &str, duration: Duration) -> Result<String> {
    info!("Starting slow operation: {}", name);
    tokio::time::sleep(duration).await;
    info!("Completed slow operation: {}", name);
    Ok(format!("Result from {}", name))
}

/// Simulated operation that might fail (unused but kept for reference)
#[allow(dead_code)]
async fn fallible_operation(name: &str, should_fail: bool) -> Result<String> {
    tokio::time::sleep(Duration::from_millis(100)).await;

    if should_fail {
        anyhow::bail!("Operation {} failed", name);
    }

    Ok(format!("Success from {}", name))
}

/// Example 1: Simple timeout
async fn example_simple_timeout() -> Result<()> {
    info!("\n=== Example 1: Simple Timeout ===");

    let config = TimeoutConfig::new()
        .with_request_timeout(Duration::from_secs(2));

    // This should succeed
    info!("Running fast operation (should succeed)...");
    match config
        .execute_with_timeout(slow_operation("fast", Duration::from_millis(500)))
        .await
    {
        Ok(result) => info!("✓ Fast operation succeeded: {}", result),
        Err(e) => error!("✗ Fast operation failed: {}", e),
    }

    // This should timeout
    info!("Running slow operation (should timeout)...");
    match config
        .execute_with_timeout(slow_operation("slow", Duration::from_secs(5)))
        .await
    {
        Ok(result) => error!("✗ Slow operation unexpectedly succeeded: {}", result),
        Err(TimeoutError::Elapsed(d)) => info!("✓ Slow operation timed out after {:?} as expected", d),
        Err(e) => error!("✗ Unexpected error: {}", e),
    }

    Ok(())
}

/// Example 2: Cancellation with CancellationToken
async fn example_cancellation_token() -> Result<()> {
    info!("\n=== Example 2: Cancellation with Token ===");

    let token = CancellationToken::new();
    let token_clone = token.clone();

    // Spawn a task that will be cancelled
    let handle = tokio::spawn(async move {
        tokio::select! {
            _result = slow_operation("cancellable", Duration::from_secs(10)) => {
                match _result {
                    Ok(r) => info!("Operation completed: {}", r),
                    Err(e) => error!("Operation failed: {}", e),
                }
            }
            _ = token_clone.cancelled() => {
                info!("✓ Operation was cancelled gracefully");
            }
        }
    });

    // Cancel after 1 second
    tokio::time::sleep(Duration::from_secs(1)).await;
    info!("Sending cancellation signal...");
    token.cancel();

    // Wait for task to finish
    handle.await.context("Task panicked")?;

    Ok(())
}

/// Example 3: Using CancellablePrediction wrapper
async fn example_cancellable_prediction() -> Result<()> {
    info!("\n=== Example 3: CancellablePrediction Wrapper ===");

    let prediction = CancellablePrediction::<String>::new("prediction-1");

    // Spawn task to cancel after delay
    let pred_clone = CancellablePrediction::<String>::new("prediction-1");

    tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(500)).await;
        info!("Cancelling prediction...");
        pred_clone.cancel().await;
    });

    // Execute prediction
    info!("Executing cancellable prediction...");
    match prediction
        .execute(|| slow_operation("long-prediction", Duration::from_secs(5)))
        .await
    {
        Ok(result) => error!("✗ Prediction unexpectedly completed: {}", result),
        Err(TimeoutError::Cancelled) => info!("✓ Prediction was cancelled as expected"),
        Err(e) => error!("✗ Unexpected error: {}", e),
    }

    info!("Prediction status: {:?}", prediction.status().await);

    Ok(())
}

/// Example 4: Deadline-based execution
async fn example_deadline_execution() -> Result<()> {
    info!("\n=== Example 4: Deadline-Based Execution ===");

    let deadline = Instant::now() + Duration::from_secs(3);
    let executor = DeadlineExecutor::new(deadline);

    info!("Deadline set for {:?} from now", Duration::from_secs(3));

    // Execute several operations
    for i in 1..=5 {
        let op_name = format!("operation-{}", i);

        match executor
            .execute(
                op_name.clone(),
                slow_operation(&op_name, Duration::from_millis(800)),
            )
            .await
        {
            Ok(_result) => {
                info!(
                    "✓ {} completed with {:?} remaining",
                    op_name,
                    executor.remaining().unwrap_or_default()
                );
            }
            Err(TimeoutError::DeadlineExceeded { .. }) => {
                info!("✓ {} hit deadline (expected)", op_name);
                break;
            }
            Err(e) => {
                error!("✗ {} failed: {}", op_name, e);
                break;
            }
        }
    }

    Ok(())
}

/// Example 5: Multiple timeout layers (per-request + global)
async fn example_multiple_timeouts() -> Result<()> {
    info!("\n=== Example 5: Multiple Timeout Layers ===");

    let global_timeout = Duration::from_secs(5);
    let request_timeout = Duration::from_secs(1);

    info!(
        "Global timeout: {:?}, Per-request timeout: {:?}",
        global_timeout, request_timeout
    );

    let result = tokio::time::timeout(global_timeout, async {
        let config = TimeoutConfig::new().with_request_timeout(request_timeout);

        let mut successful = 0;
        let mut timed_out = 0;

        for i in 1..=10 {
            let op_duration = if i % 3 == 0 {
                Duration::from_secs(2) // Will timeout
            } else {
                Duration::from_millis(500) // Will succeed
            };

            match config
                .execute_with_timeout(slow_operation(&format!("req-{}", i), op_duration))
                .await
            {
                Ok(_) => {
                    successful += 1;
                    info!("✓ Request {} succeeded", i);
                }
                Err(TimeoutError::Elapsed(_)) => {
                    timed_out += 1;
                    warn!("⚠ Request {} timed out", i);
                }
                Err(e) => {
                    error!("✗ Request {} failed: {}", i, e);
                }
            }
        }

        info!(
            "Summary: {} successful, {} timed out",
            successful, timed_out
        );

        Ok::<_, anyhow::Error>(())
    })
    .await;

    match result {
        Ok(Ok(())) => info!("✓ All operations completed within global timeout"),
        Ok(Err(e)) => error!("✗ Operations failed: {}", e),
        Err(_) => info!("⚠ Global timeout exceeded"),
    }

    Ok(())
}

/// Example 6: Retry on timeout
async fn example_retry_on_timeout() -> Result<()> {
    info!("\n=== Example 6: Retry on Timeout ===");

    let config = TimeoutConfig::new()
        .with_request_timeout(Duration::from_millis(500))
        .with_max_retries(3)
        .with_backoff(BackoffStrategy::Exponential {
            initial: Duration::from_millis(100),
            max: Duration::from_secs(2),
        });

    // Operation that gets faster each time (simulating eventual success)
    let attempt_count = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));

    info!("Attempting operation with retries...");
    let result = config
        .execute_with_retry(|| {
            let count = attempt_count.clone();
            async move {
                let attempt = count.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                let duration = Duration::from_millis(800 - (attempt as u64 * 200));

                info!("Attempt {} with {:?} duration", attempt + 1, duration);

                slow_operation(&format!("retry-attempt-{}", attempt + 1), duration).await
            }
        })
        .await;

    match result {
        Ok(value) => info!("✓ Operation succeeded after retries: {}", value),
        Err(e) => error!("✗ Operation failed after all retries: {}", e),
    }

    Ok(())
}

/// Example 7: Graceful cancellation with cleanup
async fn example_graceful_cancellation() -> Result<()> {
    info!("\n=== Example 7: Graceful Cancellation with Cleanup ===");

    let handler = GracefulCancellationHandler::new();

    // Simulate resource that needs cleanup
    let resource_active = std::sync::Arc::new(tokio::sync::Mutex::new(true));

    // Register cleanup handler
    let resource_clone = resource_active.clone();
    handler
        .register_cleanup(async move {
            info!("Running cleanup handler...");
            *resource_clone.lock().await = false;
            tokio::time::sleep(Duration::from_millis(100)).await;
            info!("✓ Cleanup complete");
        })
        .await;

    // Spawn multiple operations
    for i in 1..=3 {
        let token = handler.create_child(format!("worker-{}", i)).await;
        let op_name = format!("worker-{}", i);

        tokio::spawn(async move {
            tokio::select! {
                result = slow_operation(&op_name, Duration::from_secs(10)) => {
                    match result {
                        Ok(r) => info!("{} completed: {}", op_name, r),
                        Err(e) => error!("{} failed: {}", op_name, e),
                    }
                }
                _ = token.cancelled() => {
                    info!("✓ {} received cancellation signal", op_name);
                }
            }
        });
    }

    // Let operations run for a bit
    tokio::time::sleep(Duration::from_secs(1)).await;

    info!(
        "Active operations before cancellation: {}",
        handler.active_count().await
    );

    // Gracefully cancel all
    info!("Initiating graceful cancellation...");
    handler.cancel_gracefully().await;

    // Check resource was cleaned up
    assert!(!*resource_active.lock().await);
    info!("✓ All resources cleaned up successfully");

    Ok(())
}

/// Example 8: Combining patterns (deadline + cancellation + timeout)
async fn example_combined_patterns() -> Result<()> {
    info!("\n=== Example 8: Combined Patterns ===");

    // Setup: deadline, cancellation, and per-request timeout
    let executor = DeadlineExecutor::from_duration(Duration::from_secs(10));
    let handler = GracefulCancellationHandler::new();
    let config = TimeoutConfig::new().with_request_timeout(Duration::from_secs(2));

    info!("Running with combined timeout patterns:");
    info!("  - Global deadline: {:?}", Duration::from_secs(10));
    info!("  - Per-request timeout: {:?}", Duration::from_secs(2));
    info!("  - Graceful cancellation enabled");

    let mut batch_results = Vec::new();

    for i in 1..=5 {
        // Check for external cancellation
        if handler.is_cancelled() {
            info!("⚠ External cancellation detected");
            break;
        }

        let op_name = format!("batch-op-{}", i);
        let token = handler.create_child(&op_name).await;

        // Execute with deadline
        let result = executor
            .execute(&op_name, async {
                // Execute with per-request timeout and cancellation
                tokio::select! {
                    result = config.execute_with_timeout(
                        slow_operation(&op_name, Duration::from_millis(800))
                    ) => {
                        result.map_err(|e| anyhow::anyhow!("{}", e))
                    }
                    _ = token.cancelled() => {
                        info!("⚠ {} cancelled by external signal", op_name);
                        Err(anyhow::anyhow!("Cancelled"))
                    }
                }
            })
            .await;

        match result {
            Ok(value) => {
                info!(
                    "✓ {} completed (deadline remaining: {:?})",
                    op_name,
                    executor.remaining().unwrap_or_default()
                );
                batch_results.push(value);
            }
            Err(TimeoutError::DeadlineExceeded { .. }) => {
                info!("⚠ {} exceeded deadline", op_name);
                break;
            }
            Err(e) => {
                error!("✗ {} failed: {}", op_name, e);
            }
        }
    }

    info!(
        "Batch processing complete: {}/{} operations succeeded",
        batch_results.len(),
        5
    );

    // Cleanup
    handler.cancel_gracefully().await;

    Ok(())
}

/// Example 9: Timeout recovery strategies
async fn example_timeout_recovery() -> Result<()> {
    info!("\n=== Example 9: Timeout Recovery Strategies ===");

    let config = TimeoutConfig::new().with_request_timeout(Duration::from_millis(500));

    // Strategy 1: Fallback value
    info!("Strategy 1: Fallback value");
    let result = match config
        .execute_with_timeout(slow_operation("slow-1", Duration::from_secs(2)))
        .await
    {
        Ok(value) => value,
        Err(TimeoutError::Elapsed(_)) => {
            info!("  ⚠ Timeout, using fallback value");
            "Fallback result".to_string()
        }
        Err(e) => return Err(e.into()),
    };
    info!("  Result: {}", result);

    // Strategy 2: Shorter timeout, then longer
    info!("\nStrategy 2: Progressive timeout (quick first, then slower)");
    let quick_config = TimeoutConfig::new().with_request_timeout(Duration::from_millis(200));
    let slow_config = TimeoutConfig::new().with_request_timeout(Duration::from_secs(2));

    let result = match quick_config
        .execute_with_timeout(slow_operation("strategy-2", Duration::from_millis(500)))
        .await
    {
        Ok(value) => {
            info!("  ✓ Succeeded with quick timeout");
            value
        }
        Err(TimeoutError::Elapsed(_)) => {
            info!("  ⚠ Quick timeout exceeded, trying with longer timeout");
            slow_config
                .execute_with_timeout(slow_operation("strategy-2-retry", Duration::from_millis(500)))
                .await?
        }
        Err(e) => return Err(e.into()),
    };
    info!("  Result: {}", result);

    // Strategy 3: Cache result and return stale on timeout
    info!("\nStrategy 3: Return cached/stale result on timeout");
    let cached_value = Some("Cached result from 5 minutes ago".to_string());

    let result = match config
        .execute_with_timeout(slow_operation("slow-2", Duration::from_secs(2)))
        .await
    {
        Ok(value) => {
            info!("  ✓ Fresh result obtained");
            value
        }
        Err(TimeoutError::Elapsed(_)) => {
            if let Some(cached) = cached_value {
                info!("  ⚠ Timeout, returning cached result");
                cached
            } else {
                info!("  ✗ No cached result available");
                return Err(anyhow::anyhow!("Timeout with no fallback"));
            }
        }
        Err(e) => return Err(e.into()),
    };
    info!("  Result: {}", result);

    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(fmt::layer())
        .with(EnvFilter::from_default_env().add_directive(tracing::Level::INFO.into()))
        .init();

    info!("=== Timeout and Cancellation Patterns Demo ===\n");

    // Run all examples sequentially
    if let Err(e) = example_simple_timeout().await {
        error!("Simple Timeout example failed: {}", e);
    }
    tokio::time::sleep(Duration::from_millis(500)).await;

    if let Err(e) = example_cancellation_token().await {
        error!("Cancellation Token example failed: {}", e);
    }
    tokio::time::sleep(Duration::from_millis(500)).await;

    if let Err(e) = example_cancellable_prediction().await {
        error!("Cancellable Prediction example failed: {}", e);
    }
    tokio::time::sleep(Duration::from_millis(500)).await;

    if let Err(e) = example_deadline_execution().await {
        error!("Deadline Execution example failed: {}", e);
    }
    tokio::time::sleep(Duration::from_millis(500)).await;

    if let Err(e) = example_multiple_timeouts().await {
        error!("Multiple Timeouts example failed: {}", e);
    }
    tokio::time::sleep(Duration::from_millis(500)).await;

    if let Err(e) = example_retry_on_timeout().await {
        error!("Retry on Timeout example failed: {}", e);
    }
    tokio::time::sleep(Duration::from_millis(500)).await;

    if let Err(e) = example_graceful_cancellation().await {
        error!("Graceful Cancellation example failed: {}", e);
    }
    tokio::time::sleep(Duration::from_millis(500)).await;

    if let Err(e) = example_combined_patterns().await {
        error!("Combined Patterns example failed: {}", e);
    }
    tokio::time::sleep(Duration::from_millis(500)).await;

    if let Err(e) = example_timeout_recovery().await {
        error!("Timeout Recovery example failed: {}", e);
    }
    tokio::time::sleep(Duration::from_millis(500)).await;

    info!("\n=== All Examples Complete ===");

    Ok(())
}
