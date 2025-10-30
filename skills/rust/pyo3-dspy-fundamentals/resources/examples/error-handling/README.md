# Production Error Handling for DSPy with PyO3

This example demonstrates robust, production-grade error handling patterns for using DSPy from Rust via PyO3.

## Overview

Error handling is critical for production systems. This example shows:

1. **Custom Error Types** - Structured errors with `thiserror`
2. **Retry Logic** - Exponential backoff with jitter
3. **Timeout Handling** - Async timeout patterns
4. **Python Exception Conversion** - Bi-directional error mapping
5. **Graceful Degradation** - Fallback strategies when primary operations fail
6. **Error Context** - Preserve operation details for debugging

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        DSpyClient                            │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  predict_with_retry (public API)                   │    │
│  │    ├─ Input validation                             │    │
│  │    ├─ Retry loop (1..max_retries)                  │    │
│  │    └─ Error classification (retryable?)            │    │
│  └────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  predict_with_timeout                              │    │
│  │    ├─ tokio::time::timeout wrapper                 │    │
│  │    └─ Timeout error if exceeded                    │    │
│  └────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  predict_internal (async Python call)              │    │
│  │    ├─ spawn_blocking for GIL safety                │    │
│  │    ├─ Python::with_gil                             │    │
│  │    ├─ DSPy prediction                              │    │
│  │    └─ Result extraction & validation               │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                  Python Exceptions
                          │
                          ▼
              ┌───────────────────────┐
              │  DSpyError (Rust)     │
              │  ├─ ImportError       │
              │  ├─ ConfigError       │
              │  ├─ PredictionError   │
              │  ├─ Timeout           │
              │  └─ RetryExhausted    │
              └───────────────────────┘
```

## Error Types

### DSpyError (Main Error Type)

```rust
pub enum DSpyError {
    PythonInit(String),           // Python initialization failed
    ImportError(String),          // DSPy module not found
    Config(ConfigError),          // Configuration issues
    Prediction(PredictionError),  // Prediction failures
    Model(String),                // Model-specific errors
    Timeout { operation, ms },    // Operation timeout
    RetryExhausted { attempts },  // All retries failed
    Python(String),               // Generic Python exception
    Serialization(serde_json::Error),
    Io(std::io::Error),
}
```

### ConfigError

```rust
pub enum ConfigError {
    MissingField { field },       // Required config missing
    InvalidValue { field, value }, // Invalid config value
    MissingApiKey { var_name },   // API key not found
    InvalidModel { model },       // Unsupported model
}
```

### PredictionError

```rust
pub enum PredictionError {
    EmptyInput,                   // No input provided
    InvalidFormat { details },    // Input format wrong
    EmptyResponse,                // Model returned nothing
    ParseError { details },       // Can't parse response
    RateLimit { retry_after_ms }, // Rate limited
    QuotaExceeded,               // Quota exceeded
}
```

## Error Conversion

### Python → Rust

```rust
impl From<PyErr> for DSpyError {
    fn from(err: PyErr) -> Self {
        Python::with_gil(|py| {
            let exception_type = err.get_type(py).name().unwrap_or("Unknown");
            let exception_value = err.value(py).to_string();

            // Map specific exceptions
            if exception_type.contains("ImportError") {
                DSpyError::ImportError(...)
            } else if exception_type.contains("ValueError") {
                DSpyError::Prediction(PredictionError::InvalidFormat { ... })
            } else {
                DSpyError::Python(...)
            }
        })
    }
}
```

### Rust → Python

```rust
impl From<DSpyError> for PyErr {
    fn from(err: DSpyError) -> Self {
        match err {
            DSpyError::Config(ConfigError::MissingField { field }) => {
                PyValueError::new_err(format!("Missing field: {}", field))
            }
            DSpyError::Timeout { operation, timeout_ms } => {
                PyRuntimeError::new_err(...)
            }
            _ => PyRuntimeError::new_err(err.to_string()),
        }
    }
}
```

## Retry Strategy

### Exponential Backoff with Jitter

```rust
fn calculate_backoff(&self, attempt: u32) -> Duration {
    let base = self.config.backoff_base_ms;
    let exponential = base * 2_u64.pow(attempt - 1);
    let jitter = (rand::random::<f64>() * 0.3 + 0.85) as u64; // 85-115%
    Duration::from_millis(exponential * jitter / 100)
}
```

**Backoff progression (base=1000ms):**
- Attempt 1: Immediate
- Attempt 2: ~1000ms (850-1150ms with jitter)
- Attempt 3: ~2000ms (1700-2300ms)
- Attempt 4: ~4000ms (3400-4600ms)

### Retryable vs Non-Retryable Errors

```rust
fn is_retryable(&self, error: &DSpyError) -> bool {
    match error {
        // Retryable
        DSpyError::Prediction(PredictionError::RateLimit { .. }) => true,
        DSpyError::Timeout { .. } => true,
        DSpyError::Model(_) => true,

        // Non-retryable
        DSpyError::Prediction(PredictionError::EmptyInput) => false,
        DSpyError::Config(_) => false,
        _ => false,
    }
}
```

## Timeout Handling

### Async Timeout Wrapper

```rust
async fn predict_with_timeout(&self, input: &str, ctx: ErrorContext) -> DSpyResult<String> {
    let timeout = Duration::from_millis(self.config.timeout_ms);

    tokio::time::timeout(timeout, self.predict_internal(input))
        .await
        .map_err(|_| DSpyError::Timeout {
            operation: ctx.operation.clone(),
            timeout_ms: self.config.timeout_ms,
        })?
}
```

### GIL-Safe Async Execution

```rust
async fn predict_internal(&self, input: &str) -> DSpyResult<String> {
    // Run blocking Python code in separate thread pool
    tokio::task::spawn_blocking(move || {
        Python::with_gil(|py| {
            // Python operations here
        })
    })
    .await
    .map_err(|e| DSpyError::Python(format!("Task join error: {}", e)))?
}
```

## Graceful Degradation

### Fallback Strategy

```rust
async fn predict_with_fallback(client: &DSpyClient, input: &str) -> String {
    match client.predict_with_retry(input).await {
        Ok(result) => result,
        Err(e) => {
            error!("Primary prediction failed: {}", e);

            // Try fallback
            match try_simple_fallback(input).await {
                Ok(result) => result,
                Err(fallback_err) => {
                    format!("Error: Unable to process request. {}", e)
                }
            }
        }
    }
}
```

### Fallback Implementation

```rust
async fn try_simple_fallback(input: &str) -> DSpyResult<String> {
    // Simple pattern matching or cached responses
    if input.contains("weather") {
        Ok("I don't have access to real-time weather data.".to_string())
    } else {
        Ok("Technical difficulties. Please try again.".to_string())
    }
}
```

## Error Context Preservation

### ErrorContext Structure

```rust
#[derive(Debug, Clone)]
pub struct ErrorContext {
    pub operation: String,
    pub attempt: u32,
    pub timestamp: SystemTime,
}

impl ErrorContext {
    pub fn new(operation: impl Into<String>) -> Self {
        Self {
            operation: operation.into(),
            attempt: 1,
            timestamp: SystemTime::now(),
        }
    }

    pub fn with_attempt(mut self, attempt: u32) -> Self {
        self.attempt = attempt;
        self
    }
}
```

### Usage in Logging

```rust
let ctx = ErrorContext::new("predict").with_attempt(attempt);
warn!("Attempt {}/{} failed: {} [{}]", attempt, max_retries, e, ctx);
```

## Building and Running

### Prerequisites

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Python and DSPy
pip install dspy-ai openai
```

### Build

```bash
cd error-handling
cargo build
```

### Run Examples

```bash
# Set up environment
export OPENAI_API_KEY="your-key-here"
export DSPY_MODEL="gpt-3.5-turbo"

# Run all examples
cargo run

# With debug logging
RUST_LOG=debug cargo run
```

## Example Output

```
INFO Starting DSPy Error Handling Example
INFO Configuration loaded: DSpyConfig { model: "gpt-3.5-turbo", max_retries: 3, timeout_ms: 30000, backoff_base_ms: 1000 }

=== Example 1: Successful Prediction ===
INFO DSPy initialized with model: gpt-3.5-turbo
INFO Prediction succeeded on attempt 1/3
INFO Answer: Paris

=== Example 2: Empty Input Error ===
WARN Expected error: Empty input provided

=== Example 3: Graceful Degradation ===
ERROR Primary prediction failed: Timeout after 30000ms: predict
WARN Attempting fallback: simple response
INFO Using simple fallback for input: What's the weather today?
WARN Fallback succeeded
INFO Answer (with fallback): I don't have access to real-time weather data.

=== Example 4: Error Context Preservation ===
INFO Context: operation='demo_operation' attempt=2 timestamp=SystemTime { ... }

=== Example 5: Configuration Validation ===
WARN Expected config error: Invalid model name: invalid-model

=== All examples completed ===
```

## Production Patterns

### 1. Input Validation

```rust
if input.trim().is_empty() {
    return Err(PredictionError::EmptyInput.into());
}
```

### 2. Retry Loop with Logging

```rust
for attempt in 1..=max_retries {
    match operation().await {
        Ok(result) => return Ok(result),
        Err(e) => {
            warn!("Attempt {}/{} failed: {}", attempt, max_retries, e);

            if !is_retryable(&e) {
                return Err(e);
            }

            if attempt < max_retries {
                tokio::time::sleep(calculate_backoff(attempt)).await;
            }
        }
    }
}
```

### 3. Timeout Configuration

```rust
let timeout = Duration::from_millis(config.timeout_ms);
tokio::time::timeout(timeout, operation).await?
```

### 4. Error Propagation with ?

```rust
let dspy = PyModule::import(py, "dspy")?;
let lm = lm_class.call((), Some(kwargs))?;
dspy.call_method1("settings.configure", (lm,))?;
```

### 5. Structured Logging

```rust
use tracing::{error, warn, info};

error!("Critical failure: {}", err);
warn!("Retryable error: {}", err);
info!("Operation succeeded");
```

## Testing Error Scenarios

### Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_input_error() {
        let err = PredictionError::EmptyInput;
        assert_eq!(err.to_string(), "Empty input provided");
    }

    #[test]
    fn test_backoff_calculation() {
        let config = DSpyConfig::from_env().unwrap();
        let client = DSpyClient::new(config);

        let backoff1 = client.calculate_backoff(1);
        let backoff2 = client.calculate_backoff(2);

        assert!(backoff2 > backoff1);
    }

    #[tokio::test]
    async fn test_timeout() {
        // Test timeout behavior
    }
}
```

### Integration Tests

```bash
# Create tests/integration_test.rs for full workflow testing
cargo test --test integration_test
```

## Key Takeaways

1. **Structured Errors**: Use `thiserror` for clean, composable error types
2. **Error Conversion**: Map Python exceptions to Rust errors bidirectionally
3. **Retry Logic**: Implement exponential backoff with jitter for transient failures
4. **Timeouts**: Always set timeouts for external operations
5. **Context**: Preserve error context for debugging
6. **Fallbacks**: Implement graceful degradation when primary operations fail
7. **Logging**: Use structured logging (tracing) for observability
8. **GIL Safety**: Use `spawn_blocking` for Python calls in async contexts

## Further Reading

- [thiserror documentation](https://docs.rs/thiserror)
- [anyhow documentation](https://docs.rs/anyhow)
- [PyO3 error handling](https://pyo3.rs/latest/function/error-handling.html)
- [Tokio timeout patterns](https://tokio.rs/tokio/topics/time)
- [Retry patterns in Rust](https://github.com/dtolnay/retry)

## License

MIT
