# Timeout and Cancellation Patterns for PyO3 + DSPy

This example demonstrates robust timeout and cancellation patterns for async Python calls from Rust, specifically designed for DSPy workflows that may be slow or unpredictable.

## Key Patterns

### 1. Simple Timeouts
Use `tokio::time::timeout` to wrap async operations with hard deadlines:
```rust
let result = timeout(Duration::from_secs(5), async_operation()).await;
```

### 2. Cooperative Cancellation
Use `tokio_util::sync::CancellationToken` for graceful cancellation that allows cleanup:
```rust
let token = CancellationToken::new();
let result = run_with_cancellation(token.clone(), operation).await;
token.cancel(); // Gracefully cancel
```

### 3. Deadline-Based Execution
Track absolute deadlines across multiple operations:
```rust
let deadline = Instant::now() + Duration::from_secs(30);
executor.execute_with_deadline(deadline, operation).await;
```

### 4. Timeout Recovery
Implement fallback strategies when operations timeout:
```rust
match timeout(duration, operation).await {
    Ok(result) => result,
    Err(_) => fallback_strategy().await,
}
```

## Architecture

### Core Components

1. **TimeoutConfig**: Configuration for timeout behavior
   - Per-request timeouts
   - Global/session timeouts
   - Retry policies

2. **CancellablePrediction**: Wrapper for DSPy predictions with cancellation support
   - Cancellation token propagation
   - Cleanup on cancel
   - Status tracking

3. **DeadlineExecutor**: Executor that enforces absolute deadlines
   - Deadline tracking
   - Automatic cancellation on deadline exceeded
   - Time budget allocation

4. **GracefulCancellationHandler**: Manages graceful shutdown
   - Pending operation tracking
   - Coordinated cancellation
   - Resource cleanup

## Usage Examples

### Simple Timeout
```rust
use timeout_cancellation::*;
use std::time::Duration;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let config = TimeoutConfig::new()
        .with_request_timeout(Duration::from_secs(5));

    let result = config.execute_with_timeout(async {
        // Your DSPy prediction here
        predict_with_dspy().await
    }).await?;

    Ok(())
}
```

### Cancellation with Token
```rust
use tokio_util::sync::CancellationToken;

let token = CancellationToken::new();
let token_clone = token.clone();

tokio::spawn(async move {
    tokio::time::sleep(Duration::from_secs(10)).await;
    token_clone.cancel();
});

let result = run_cancellable(token, operation).await;
```

### Deadline-Based Execution
```rust
use std::time::Instant;

let deadline = Instant::now() + Duration::from_secs(30);
let executor = DeadlineExecutor::new(deadline);

// Execute multiple operations within deadline
executor.execute(operation1).await?;
executor.execute(operation2).await?;
```

### Multiple Timeout Layers
```rust
// Global timeout for entire session
let global_timeout = Duration::from_secs(60);

timeout(global_timeout, async {
    // Per-request timeout
    for i in 0..10 {
        let request_timeout = Duration::from_secs(5);
        timeout(request_timeout, single_prediction(i)).await?;
    }
    Ok::<_, Error>(())
}).await??;
```

### Retry on Timeout
```rust
async fn retry_on_timeout<F, Fut, T>(
    mut f: F,
    timeout_duration: Duration,
    max_retries: usize,
) -> Result<T, TimeoutError>
where
    F: FnMut() -> Fut,
    Fut: Future<Output = T>,
{
    for attempt in 0..max_retries {
        match timeout(timeout_duration, f()).await {
            Ok(result) => return Ok(result),
            Err(_) if attempt < max_retries - 1 => continue,
            Err(e) => return Err(e.into()),
        }
    }
    unreachable!()
}
```

## Best Practices

### 1. Choose the Right Pattern
- **Simple timeout**: When you just need a hard cutoff
- **Cancellation token**: When you need coordinated cancellation across multiple tasks
- **Deadline**: When managing time budgets across operations
- **Graceful handler**: When cleanup is critical (resources, connections)

### 2. Avoid Abrupt Cancellation
Don't use `task::abort()` unless absolutely necessary. Instead:
- Use `CancellationToken` for cooperative cancellation
- Allow tasks to clean up before exiting
- Propagate cancellation signals through your call chain

### 3. Handle Python State
When cancelling Python operations:
- Release GIL before cancelling
- Clean up Python objects properly
- Don't leave Python in inconsistent state

### 4. Set Appropriate Timeouts
```rust
// Too short - will timeout on valid slow operations
let bad_timeout = Duration::from_millis(100);

// Reasonable - allows for LLM latency
let good_timeout = Duration::from_secs(30);

// Per operation type
let quick_lookup = Duration::from_secs(5);
let llm_inference = Duration::from_secs(30);
let batch_processing = Duration::from_secs(120);
```

### 5. Combine Patterns
```rust
// Global deadline + per-request timeout + cancellation
let deadline = Instant::now() + Duration::from_secs(300);
let executor = DeadlineExecutor::new(deadline);
let cancel_token = CancellationToken::new();

loop {
    if cancel_token.is_cancelled() {
        break;
    }

    let request_timeout = Duration::from_secs(30);
    match executor.execute_with_timeout(request_timeout, operation()).await {
        Ok(result) => process(result),
        Err(TimeoutError::Elapsed) => retry_or_skip(),
        Err(TimeoutError::Deadline) => break,
    }
}
```

## Common Pitfalls

### 1. Not Releasing GIL
```rust
// BAD - holds GIL during timeout
Python::with_gil(|py| {
    timeout(duration, python_call(py)).await // GIL held entire time!
});

// GOOD - release GIL during wait
let result = timeout(duration, async {
    Python::with_gil(|py| python_call(py))
}).await;
```

### 2. Ignoring Timeout Errors
```rust
// BAD - silently ignores why timeout occurred
let _ = timeout(duration, operation()).await;

// GOOD - handle timeout appropriately
match timeout(duration, operation()).await {
    Ok(result) => process(result),
    Err(_) => {
        log::warn!("Operation timed out after {:?}", duration);
        fallback_strategy()
    }
}
```

### 3. Not Propagating Cancellation
```rust
// BAD - child task doesn't know about cancellation
tokio::spawn(async {
    long_operation().await
});

// GOOD - propagate cancellation token
let token = CancellationToken::new();
tokio::spawn({
    let token = token.clone();
    async move {
        tokio::select! {
            result = long_operation() => result,
            _ = token.cancelled() => {
                cleanup().await;
                Err(CancellationError)
            }
        }
    }
});
```

## Running the Examples

```bash
# Build the example
cargo build --release

# Run all examples
cargo run --release

# Run with debug logging
RUST_LOG=debug cargo run --release
```

## Integration with DSPy

This example shows patterns for:
- Timing out slow LLM calls
- Cancelling in-flight predictions
- Managing batch prediction deadlines
- Recovering from timeout failures
- Gracefully shutting down DSPy sessions

These patterns ensure your Rust application remains responsive even when DSPy operations are slow or hang.
