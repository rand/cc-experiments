//! Tool-Using Agent Library
//!
//! This library provides a production-ready tool registry and execution system
//! for DSPy ReAct agents, with comprehensive error handling, retry logic,
//! circuit breaker patterns, and validation.
//!
//! # Architecture
//!
//! - `ToolRegistry`: Central registry for all tools with validation
//! - `ToolExecutor`: Handles tool execution with retry and error recovery
//! - `CircuitBreaker`: Prevents cascading failures from unhealthy tools
//! - `ToolMetrics`: Tracks tool performance and health
//!
//! # Example
//!
//! ```rust,no_run
//! use tool_using_agent::{ToolRegistry, ToolExecutor, RetryConfig};
//! use anyhow::Result;
//!
//! #[tokio::main]
//! async fn main() -> Result<()> {
//!     let mut registry = ToolRegistry::new();
//!
//!     // Register tools
//!     registry.register("calculator", |input| {
//!         Ok(format!("Result: {}", input))
//!     })?;
//!
//!     // Execute with retry
//!     let executor = ToolExecutor::new(registry);
//!     let result = executor.execute_with_retry(
//!         "calculator",
//!         "2 + 2",
//!         &RetryConfig::default()
//!     ).await?;
//!
//!     println!("Result: {}", result);
//!     Ok(())
//! }
//! ```

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use thiserror::Error;

/// Custom error types for tool operations
#[derive(Error, Debug)]
pub enum ToolError {
    #[error("Tool not found: {0}")]
    NotFound(String),

    #[error("Tool validation failed: {0}")]
    ValidationFailed(String),

    #[error("Tool execution failed: {0}")]
    ExecutionFailed(String),

    #[error("Circuit breaker is open for tool: {0}")]
    CircuitBreakerOpen(String),

    #[error("Tool timeout after {0:?}")]
    Timeout(Duration),

    #[error("Invalid tool configuration: {0}")]
    InvalidConfiguration(String),
}

/// Type alias for tool functions
pub type ToolFn = Box<dyn Fn(&str) -> Result<String> + Send + Sync>;

/// Tool metadata and configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolMetadata {
    pub name: String,
    pub description: String,
    pub version: String,
    pub timeout_ms: u64,
    pub retry_enabled: bool,
    pub max_retries: usize,
    pub tags: Vec<String>,
}

impl Default for ToolMetadata {
    fn default() -> Self {
        Self {
            name: String::new(),
            description: String::new(),
            version: "1.0.0".to_string(),
            timeout_ms: 30000,
            retry_enabled: true,
            max_retries: 3,
            tags: Vec::new(),
        }
    }
}

/// Tool performance metrics
#[derive(Debug)]
pub struct ToolMetrics {
    pub total_calls: AtomicU64,
    pub successful_calls: AtomicU64,
    pub failed_calls: AtomicU64,
    pub total_duration_ms: AtomicU64,
    pub last_success: Mutex<Option<Instant>>,
    pub last_failure: Mutex<Option<Instant>>,
}

impl ToolMetrics {
    pub fn new() -> Self {
        Self {
            total_calls: AtomicU64::new(0),
            successful_calls: AtomicU64::new(0),
            failed_calls: AtomicU64::new(0),
            total_duration_ms: AtomicU64::new(0),
            last_success: Mutex::new(None),
            last_failure: Mutex::new(None),
        }
    }

    pub fn record_success(&self, duration: Duration) {
        self.total_calls.fetch_add(1, Ordering::Relaxed);
        self.successful_calls.fetch_add(1, Ordering::Relaxed);
        self.total_duration_ms
            .fetch_add(duration.as_millis() as u64, Ordering::Relaxed);
        *self.last_success.lock().unwrap() = Some(Instant::now());
    }

    pub fn record_failure(&self, duration: Duration) {
        self.total_calls.fetch_add(1, Ordering::Relaxed);
        self.failed_calls.fetch_add(1, Ordering::Relaxed);
        self.total_duration_ms
            .fetch_add(duration.as_millis() as u64, Ordering::Relaxed);
        *self.last_failure.lock().unwrap() = Some(Instant::now());
    }

    pub fn average_duration_ms(&self) -> f64 {
        let total = self.total_calls.load(Ordering::Relaxed);
        if total == 0 {
            return 0.0;
        }
        let duration = self.total_duration_ms.load(Ordering::Relaxed);
        duration as f64 / total as f64
    }

    pub fn success_rate(&self) -> f64 {
        let total = self.total_calls.load(Ordering::Relaxed);
        if total == 0 {
            return 1.0;
        }
        let successful = self.successful_calls.load(Ordering::Relaxed);
        successful as f64 / total as f64
    }
}

impl Default for ToolMetrics {
    fn default() -> Self {
        Self::new()
    }
}

/// Tool entry in the registry
struct ToolEntry {
    function: ToolFn,
    metadata: ToolMetadata,
    metrics: Arc<ToolMetrics>,
    circuit_breaker: Arc<CircuitBreaker>,
}

/// Central tool registry with validation and management
pub struct ToolRegistry {
    tools: HashMap<String, ToolEntry>,
}

impl ToolRegistry {
    /// Create a new empty tool registry
    pub fn new() -> Self {
        Self {
            tools: HashMap::new(),
        }
    }

    /// Register a new tool with default metadata
    pub fn register<F>(&mut self, name: &str, tool: F) -> Result<()>
    where
        F: Fn(&str) -> Result<String> + Send + Sync + 'static,
    {
        let metadata = ToolMetadata {
            name: name.to_string(),
            ..Default::default()
        };
        self.register_with_metadata(name, tool, metadata)
    }

    /// Register a tool with custom metadata
    pub fn register_with_metadata<F>(
        &mut self,
        name: &str,
        tool: F,
        metadata: ToolMetadata,
    ) -> Result<()>
    where
        F: Fn(&str) -> Result<String> + Send + Sync + 'static,
    {
        // Validate tool name
        if name.is_empty() {
            return Err(ToolError::ValidationFailed("Tool name cannot be empty".to_string()).into());
        }

        if self.tools.contains_key(name) {
            return Err(ToolError::ValidationFailed(format!(
                "Tool '{}' is already registered",
                name
            ))
            .into());
        }

        // Create tool entry
        let entry = ToolEntry {
            function: Box::new(tool),
            metadata,
            metrics: Arc::new(ToolMetrics::new()),
            circuit_breaker: Arc::new(CircuitBreaker::new(5, Duration::from_secs(30))),
        };

        self.tools.insert(name.to_string(), entry);
        Ok(())
    }

    /// Execute a tool by name
    pub fn execute(&self, name: &str, input: &str) -> Result<String> {
        let entry = self
            .tools
            .get(name)
            .ok_or_else(|| ToolError::NotFound(name.to_string()))?;

        let start = Instant::now();

        // Check circuit breaker
        let result = entry.circuit_breaker.call(|| (entry.function)(input));

        let duration = start.elapsed();

        match result {
            Ok(output) => {
                entry.metrics.record_success(duration);
                Ok(output)
            }
            Err(e) => {
                entry.metrics.record_failure(duration);
                Err(e)
            }
        }
    }

    /// List all registered tool names
    pub fn list_tools(&self) -> Vec<String> {
        self.tools.keys().cloned().collect()
    }

    /// Get tool metadata
    pub fn get_metadata(&self, name: &str) -> Option<&ToolMetadata> {
        self.tools.get(name).map(|entry| &entry.metadata)
    }

    /// Get tool metrics
    pub fn get_metrics(&self, name: &str) -> Option<Arc<ToolMetrics>> {
        self.tools.get(name).map(|entry| entry.metrics.clone())
    }

    /// Remove a tool from the registry
    pub fn unregister(&mut self, name: &str) -> Result<()> {
        self.tools
            .remove(name)
            .ok_or_else(|| ToolError::NotFound(name.to_string()))?;
        Ok(())
    }

    /// Get all tools with their metrics
    pub fn get_all_metrics(&self) -> HashMap<String, Arc<ToolMetrics>> {
        self.tools
            .iter()
            .map(|(name, entry)| (name.clone(), entry.metrics.clone()))
            .collect()
    }

    /// Validate all registered tools
    pub fn validate_all(&self) -> Result<()> {
        for (name, entry) in &self.tools {
            if entry.metadata.name.is_empty() {
                return Err(ToolError::ValidationFailed(format!(
                    "Tool '{}' has empty name in metadata",
                    name
                ))
                .into());
            }
        }
        Ok(())
    }
}

impl Default for ToolRegistry {
    fn default() -> Self {
        Self::new()
    }
}

/// Retry configuration for tool execution
#[derive(Debug, Clone)]
pub struct RetryConfig {
    pub max_retries: usize,
    pub initial_delay: Duration,
    pub max_delay: Duration,
    pub backoff_multiplier: f32,
    pub retry_on_timeout: bool,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_retries: 3,
            initial_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(5),
            backoff_multiplier: 2.0,
            retry_on_timeout: true,
        }
    }
}

/// Circuit breaker for fault tolerance
pub struct CircuitBreaker {
    failure_threshold: usize,
    success_threshold: usize,
    timeout: Duration,
    failure_count: AtomicUsize,
    success_count: AtomicUsize,
    last_failure_time: Mutex<Option<Instant>>,
    state: Mutex<CircuitState>,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

impl CircuitBreaker {
    pub fn new(failure_threshold: usize, timeout: Duration) -> Self {
        Self {
            failure_threshold,
            success_threshold: 2,
            timeout,
            failure_count: AtomicUsize::new(0),
            success_count: AtomicUsize::new(0),
            last_failure_time: Mutex::new(None),
            state: Mutex::new(CircuitState::Closed),
        }
    }

    pub fn call<F, T>(&self, f: F) -> Result<T>
    where
        F: FnOnce() -> Result<T>,
    {
        let mut state = self.state.lock().unwrap();

        match *state {
            CircuitState::Open => {
                let last_failure = self.last_failure_time.lock().unwrap();
                if let Some(time) = *last_failure {
                    if time.elapsed() > self.timeout {
                        *state = CircuitState::HalfOpen;
                        drop(state);
                        drop(last_failure);
                        return self.call_half_open(f);
                    }
                }
                Err(anyhow::anyhow!("Circuit breaker is open"))
            }
            CircuitState::HalfOpen => {
                drop(state);
                self.call_half_open(f)
            }
            CircuitState::Closed => {
                drop(state);
                self.call_closed(f)
            }
        }
    }

    fn call_closed<F, T>(&self, f: F) -> Result<T>
    where
        F: FnOnce() -> Result<T>,
    {
        match f() {
            Ok(result) => {
                self.failure_count.store(0, Ordering::Relaxed);
                Ok(result)
            }
            Err(e) => {
                let failures = self.failure_count.fetch_add(1, Ordering::Relaxed) + 1;

                if failures >= self.failure_threshold {
                    let mut state = self.state.lock().unwrap();
                    *state = CircuitState::Open;

                    let mut last_failure = self.last_failure_time.lock().unwrap();
                    *last_failure = Some(Instant::now());
                }

                Err(e)
            }
        }
    }

    fn call_half_open<F, T>(&self, f: F) -> Result<T>
    where
        F: FnOnce() -> Result<T>,
    {
        match f() {
            Ok(result) => {
                let successes = self.success_count.fetch_add(1, Ordering::Relaxed) + 1;

                if successes >= self.success_threshold {
                    let mut state = self.state.lock().unwrap();
                    *state = CircuitState::Closed;
                    self.success_count.store(0, Ordering::Relaxed);
                    self.failure_count.store(0, Ordering::Relaxed);
                }

                Ok(result)
            }
            Err(e) => {
                let mut state = self.state.lock().unwrap();
                *state = CircuitState::Open;

                let mut last_failure = self.last_failure_time.lock().unwrap();
                *last_failure = Some(Instant::now());

                self.success_count.store(0, Ordering::Relaxed);

                Err(e)
            }
        }
    }

    pub fn is_open(&self) -> bool {
        *self.state.lock().unwrap() == CircuitState::Open
    }

    pub fn reset(&self) {
        let mut state = self.state.lock().unwrap();
        *state = CircuitState::Closed;
        self.failure_count.store(0, Ordering::Relaxed);
        self.success_count.store(0, Ordering::Relaxed);
        *self.last_failure_time.lock().unwrap() = None;
    }
}

/// Tool executor with retry logic
pub struct ToolExecutor {
    registry: Arc<Mutex<ToolRegistry>>,
}

impl ToolExecutor {
    pub fn new(registry: ToolRegistry) -> Self {
        Self {
            registry: Arc::new(Mutex::new(registry)),
        }
    }

    pub async fn execute_with_retry(
        &self,
        tool_name: &str,
        input: &str,
        config: &RetryConfig,
    ) -> Result<String> {
        let mut attempts = 0;
        let mut delay = config.initial_delay;

        loop {
            attempts += 1;

            let result = {
                let registry = self.registry.lock().unwrap();
                registry.execute(tool_name, input)
            };

            match result {
                Ok(output) => return Ok(output),
                Err(e) => {
                    if attempts >= config.max_retries {
                        return Err(anyhow::anyhow!(
                            "Tool '{}' failed after {} attempts: {}",
                            tool_name,
                            attempts,
                            e
                        ));
                    }

                    eprintln!(
                        "Tool '{}' failed (attempt {}/{}): {}. Retrying in {:?}...",
                        tool_name, attempts, config.max_retries, e, delay
                    );

                    tokio::time::sleep(delay).await;

                    delay = std::cmp::min(
                        Duration::from_secs_f32(delay.as_secs_f32() * config.backoff_multiplier),
                        config.max_delay,
                    );
                }
            }
        }
    }

    pub fn get_registry(&self) -> Arc<Mutex<ToolRegistry>> {
        self.registry.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_registry_basic() {
        let mut registry = ToolRegistry::new();

        registry
            .register("test", |input| Ok(format!("Result: {}", input)))
            .unwrap();

        let result = registry.execute("test", "hello").unwrap();
        assert_eq!(result, "Result: hello");
    }

    #[test]
    fn test_registry_not_found() {
        let registry = ToolRegistry::new();
        let result = registry.execute("nonexistent", "input");
        assert!(result.is_err());
    }

    #[test]
    fn test_metrics_tracking() {
        let mut registry = ToolRegistry::new();

        registry
            .register("test", |_| Ok("success".to_string()))
            .unwrap();

        registry.execute("test", "input").unwrap();

        let metrics = registry.get_metrics("test").unwrap();
        assert_eq!(metrics.total_calls.load(Ordering::Relaxed), 1);
        assert_eq!(metrics.successful_calls.load(Ordering::Relaxed), 1);
    }

    #[test]
    fn test_circuit_breaker() {
        let breaker = CircuitBreaker::new(3, Duration::from_secs(1));

        // Should succeed initially
        let result = breaker.call(|| Ok::<_, anyhow::Error>(42));
        assert!(result.is_ok());

        // Trigger failures
        for _ in 0..3 {
            let _ = breaker.call(|| Err::<i32, _>(anyhow::anyhow!("fail")));
        }

        // Circuit should be open now
        assert!(breaker.is_open());
    }
}
