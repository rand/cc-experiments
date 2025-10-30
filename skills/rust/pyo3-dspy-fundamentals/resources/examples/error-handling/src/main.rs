//! Production Error Handling for DSPy with PyO3
//!
//! This example demonstrates robust error handling patterns for production DSPy usage:
//! - Custom error types with thiserror
//! - Retry logic with exponential backoff
//! - Timeout handling
//! - Python exception conversion
//! - Graceful degradation
//! - Error context preservation

mod errors;

use errors::{ConfigError, DSpyError, DSpyResult, ErrorContext, PredictionError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};
use std::time::Duration;
use tracing::{error, info, warn};

/// Configuration for DSPy operations
#[derive(Debug, Clone)]
struct DSpyConfig {
    model: String,
    max_retries: u32,
    timeout_ms: u64,
    backoff_base_ms: u64,
}

impl DSpyConfig {
    fn from_env() -> DSpyResult<Self> {
        let model = std::env::var("DSPY_MODEL").unwrap_or_else(|_| "gpt-3.5-turbo".to_string());

        // Validate model name
        if !Self::is_valid_model(&model) {
            return Err(ConfigError::InvalidModel { model }.into());
        }

        Ok(Self {
            model,
            max_retries: 3,
            timeout_ms: 30_000,
            backoff_base_ms: 1_000,
        })
    }

    fn is_valid_model(model: &str) -> bool {
        matches!(
            model,
            "gpt-3.5-turbo" | "gpt-4" | "gpt-4-turbo" | "claude-3-sonnet" | "claude-3-opus"
        )
    }
}

/// DSPy client with error handling
struct DSpyClient {
    config: DSpyConfig,
}

impl DSpyClient {
    fn new(config: DSpyConfig) -> Self {
        Self { config }
    }

    /// Initialize DSPy with error handling
    fn initialize(&self) -> DSpyResult<Py<PyAny>> {
        Python::with_gil(|py| {
            // Import DSPy with detailed error handling
            let dspy = PyModule::import_bound(py, "dspy").map_err(|e| {
                DSpyError::ImportError(format!(
                    "Failed to import dspy. Is it installed? Error: {}",
                    e
                ))
            })?;

            // Configure language model
            let lm_class = dspy.getattr("OpenAI").map_err(|e| {
                DSpyError::ImportError(format!("DSPy.OpenAI not found: {}", e))
            })?;

            let kwargs = PyDict::new_bound(py);
            kwargs.set_item("model", &self.config.model)?;
            kwargs.set_item("max_tokens", 1000)?;

            let lm = lm_class.call((), Some(&kwargs))?;

            // Configure DSPy settings
            dspy.call_method1("settings.configure", (&lm,))?;

            info!("DSPy initialized with model: {}", self.config.model);
            Ok(lm.unbind())
        })
    }

    /// Make a prediction with retry and timeout handling
    async fn predict_with_retry(&self, input: &str) -> DSpyResult<String> {
        if input.trim().is_empty() {
            return Err(PredictionError::EmptyInput.into());
        }

        let mut last_error = None;
        let ctx = ErrorContext::new("predict");

        for attempt in 1..=self.config.max_retries {
            let ctx = ctx.clone().with_attempt(attempt);

            match self.predict_with_timeout(input, ctx.clone()).await {
                Ok(result) => {
                    info!(
                        "Prediction succeeded on attempt {}/{}",
                        attempt, self.config.max_retries
                    );
                    return Ok(result);
                }
                Err(e) => {
                    warn!("Attempt {}/{} failed: {} [{}]", attempt, self.config.max_retries, e, ctx);

                    // Check if error is retryable
                    if !self.is_retryable(&e) {
                        error!("Non-retryable error encountered: {}", e);
                        return Err(e);
                    }

                    last_error = Some(e);

                    // Don't sleep after the last attempt
                    if attempt < self.config.max_retries {
                        let backoff = self.calculate_backoff(attempt);
                        info!("Backing off for {:?} before retry", backoff);
                        tokio::time::sleep(backoff).await;
                    }
                }
            }
        }

        Err(DSpyError::RetryExhausted {
            attempts: self.config.max_retries,
            last_error: last_error
                .map(|e| e.to_string())
                .unwrap_or_else(|| "Unknown error".to_string()),
        })
    }

    /// Make a prediction with timeout
    async fn predict_with_timeout(&self, input: &str, ctx: ErrorContext) -> DSpyResult<String> {
        let timeout = Duration::from_millis(self.config.timeout_ms);

        tokio::time::timeout(timeout, self.predict_internal(input))
            .await
            .map_err(|_| DSpyError::Timeout {
                operation: ctx.operation.clone(),
                timeout_ms: self.config.timeout_ms,
            })?
    }

    /// Internal prediction logic (synchronous Python call in async context)
    async fn predict_internal(&self, input: &str) -> DSpyResult<String> {
        // Run blocking Python code in a separate thread pool
        let input = input.to_string();

        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                let dspy = PyModule::import_bound(py, "dspy")?;

                // Create a simple predict module
                let predict_class = dspy.getattr("Predict")?;
                let predictor = predict_class.call1(("question -> answer",))?;

                // Make prediction
                let result = predictor.call_method1("forward", (input,))?;

                // Extract answer with error handling
                let answer = result
                    .getattr("answer")
                    .map_err(|e| PredictionError::ParseError {
                        details: format!("Failed to extract answer: {}", e),
                    })?
                    .extract::<String>()
                    .map_err(|e| PredictionError::ParseError {
                        details: format!("Failed to convert answer to string: {}", e),
                    })?;

                if answer.trim().is_empty() {
                    return Err(PredictionError::EmptyResponse.into());
                }

                Ok(answer)
            })
        })
        .await
        .map_err(|e| DSpyError::Python(format!("Task join error: {}", e)))?
    }

    /// Calculate exponential backoff with jitter
    fn calculate_backoff(&self, attempt: u32) -> Duration {
        let base = self.config.backoff_base_ms;
        let exponential = base * 2_u64.pow(attempt - 1);
        let jitter = (rand::random::<f64>() * 0.3 + 0.85) as u64; // 85-115% jitter
        Duration::from_millis(exponential * jitter / 100)
    }

    /// Determine if an error is retryable
    fn is_retryable(&self, error: &DSpyError) -> bool {
        match error {
            DSpyError::Prediction(PredictionError::RateLimit { .. }) => true,
            DSpyError::Timeout { .. } => true,
            DSpyError::Model(_) => true,
            DSpyError::Python(_) => true,
            DSpyError::Prediction(PredictionError::EmptyInput) => false,
            DSpyError::Prediction(PredictionError::InvalidFormat { .. }) => false,
            DSpyError::Config(_) => false,
            _ => false,
        }
    }
}

/// Demonstrate graceful degradation with fallback strategies
async fn predict_with_fallback(client: &DSpyClient, input: &str) -> String {
    match client.predict_with_retry(input).await {
        Ok(result) => result,
        Err(e) => {
            error!("Primary prediction failed: {}", e);

            // Try fallback strategy
            warn!("Attempting fallback: simple response");

            match try_simple_fallback(input).await {
                Ok(result) => {
                    warn!("Fallback succeeded");
                    result
                }
                Err(fallback_err) => {
                    error!("Fallback also failed: {}", fallback_err);
                    format!("Error: Unable to process request. {}", e)
                }
            }
        }
    }
}

/// Simple fallback that doesn't use DSPy
async fn try_simple_fallback(input: &str) -> DSpyResult<String> {
    // In production, this might call a simpler model or return a cached response
    info!("Using simple fallback for input: {}", input);

    if input.contains("weather") {
        Ok("I don't have access to real-time weather data.".to_string())
    } else if input.contains("time") {
        Ok(format!(
            "Current time is approximately: {:?}",
            std::time::SystemTime::now()
        ))
    } else {
        Ok("I'm currently experiencing technical difficulties. Please try again later.".to_string())
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter("info")
        .with_target(false)
        .init();

    info!("Starting DSPy Error Handling Example");

    // Load configuration with error handling
    let config = match DSpyConfig::from_env() {
        Ok(cfg) => {
            info!("Configuration loaded: {:?}", cfg);
            cfg
        }
        Err(e) => {
            error!("Configuration error: {}", e);
            return Err(e.into());
        }
    };

    let client = DSpyClient::new(config);

    // Example 1: Successful prediction
    info!("\n=== Example 1: Successful Prediction ===");
    match client.predict_with_retry("What is the capital of France?").await {
        Ok(answer) => info!("Answer: {}", answer),
        Err(e) => error!("Failed: {}", e),
    }

    // Example 2: Empty input error (non-retryable)
    info!("\n=== Example 2: Empty Input Error ===");
    match client.predict_with_retry("").await {
        Ok(answer) => info!("Answer: {}", answer),
        Err(e) => warn!("Expected error: {}", e),
    }

    // Example 3: Graceful degradation
    info!("\n=== Example 3: Graceful Degradation ===");
    let answer = predict_with_fallback(&client, "What's the weather today?").await;
    info!("Answer (with fallback): {}", answer);

    // Example 4: Demonstrate error context
    info!("\n=== Example 4: Error Context Preservation ===");
    let ctx = ErrorContext::new("demo_operation").with_attempt(2);
    info!("Context: {}", ctx);

    // Example 5: Configuration errors
    info!("\n=== Example 5: Configuration Validation ===");
    std::env::set_var("DSPY_MODEL", "invalid-model");
    match DSpyConfig::from_env() {
        Ok(_) => info!("Config loaded"),
        Err(e) => warn!("Expected config error: {}", e),
    }

    info!("\n=== All examples completed ===");
    Ok(())
}

// Mock rand for backoff jitter (in production, use the rand crate)
mod rand {
    pub fn random<T>() -> f64 {
        0.95 // Fixed value for deterministic testing
    }
}
