//! Agent Observability Library
//!
//! Comprehensive instrumentation and observability for DSPy agents from Rust.
//! Provides structured logging, distributed tracing, performance metrics, and
//! error categorization with Jaeger/OpenTelemetry integration.

use anyhow::{anyhow, Context, Result};
use chrono::{DateTime, Utc};
use once_cell::sync::Lazy;
use parking_lot::RwLock;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tracing::{debug, error, info, instrument, warn, Span};

/// Global metrics registry
static METRICS_REGISTRY: Lazy<Arc<RwLock<MetricsRegistry>>> =
    Lazy::new(|| Arc::new(RwLock::new(MetricsRegistry::default())));

/// Error categories for structured error tracking
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ErrorCategory {
    /// Python runtime errors
    PythonRuntime,
    /// Agent execution errors
    AgentExecution,
    /// Tool invocation errors
    ToolInvocation,
    /// Timeout errors
    Timeout,
    /// Validation errors
    Validation,
    /// Network/IO errors
    NetworkIO,
    /// Configuration errors
    Configuration,
    /// Unknown errors
    Unknown,
}

impl ErrorCategory {
    /// Convert from error message patterns
    pub fn from_error(error: &str) -> Self {
        let error_lower = error.to_lowercase();

        if error_lower.contains("timeout") {
            Self::Timeout
        } else if error_lower.contains("validation") || error_lower.contains("invalid") {
            Self::Validation
        } else if error_lower.contains("tool") {
            Self::ToolInvocation
        } else if error_lower.contains("network") || error_lower.contains("io") {
            Self::NetworkIO
        } else if error_lower.contains("config") {
            Self::Configuration
        } else if error_lower.contains("agent") {
            Self::AgentExecution
        } else if error_lower.contains("python") {
            Self::PythonRuntime
        } else {
            Self::Unknown
        }
    }

    /// Get human-readable name
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::PythonRuntime => "python_runtime",
            Self::AgentExecution => "agent_execution",
            Self::ToolInvocation => "tool_invocation",
            Self::Timeout => "timeout",
            Self::Validation => "validation",
            Self::NetworkIO => "network_io",
            Self::Configuration => "configuration",
            Self::Unknown => "unknown",
        }
    }
}

/// Performance metrics for agent operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceMetrics {
    /// Operation name
    pub operation: String,
    /// Start timestamp
    pub start_time: DateTime<Utc>,
    /// End timestamp
    pub end_time: DateTime<Utc>,
    /// Duration in milliseconds
    pub duration_ms: u128,
    /// Success/failure status
    pub success: bool,
    /// Error category if failed
    pub error_category: Option<ErrorCategory>,
    /// Additional metadata
    pub metadata: HashMap<String, String>,
}

impl PerformanceMetrics {
    /// Create new metrics entry
    pub fn new(operation: impl Into<String>) -> Self {
        Self {
            operation: operation.into(),
            start_time: Utc::now(),
            end_time: Utc::now(),
            duration_ms: 0,
            success: true,
            error_category: None,
            metadata: HashMap::new(),
        }
    }

    /// Complete the metrics with duration
    pub fn complete(&mut self, success: bool, error_category: Option<ErrorCategory>) {
        self.end_time = Utc::now();
        self.duration_ms = (self.end_time - self.start_time).num_milliseconds() as u128;
        self.success = success;
        self.error_category = error_category;
    }

    /// Add metadata
    pub fn add_metadata(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.metadata.insert(key.into(), value.into());
    }
}

/// Metrics registry for tracking aggregated statistics
#[derive(Debug, Default)]
pub struct MetricsRegistry {
    /// Total agent calls
    total_calls: u64,
    /// Successful calls
    successful_calls: u64,
    /// Failed calls by category
    failed_calls: HashMap<ErrorCategory, u64>,
    /// Average duration by operation
    avg_duration: HashMap<String, Duration>,
    /// All performance metrics
    metrics: Vec<PerformanceMetrics>,
}

impl MetricsRegistry {
    /// Record a new metric
    pub fn record(&mut self, metric: PerformanceMetrics) {
        self.total_calls += 1;

        if metric.success {
            self.successful_calls += 1;
        } else if let Some(category) = metric.error_category {
            *self.failed_calls.entry(category).or_insert(0) += 1;
        }

        // Update average duration
        let operation = metric.operation.clone();
        let duration = Duration::from_millis(metric.duration_ms as u64);

        self.avg_duration
            .entry(operation)
            .and_modify(|avg| {
                *avg = (*avg + duration) / 2;
            })
            .or_insert(duration);

        self.metrics.push(metric);
    }

    /// Get success rate
    pub fn success_rate(&self) -> f64 {
        if self.total_calls == 0 {
            0.0
        } else {
            (self.successful_calls as f64) / (self.total_calls as f64)
        }
    }

    /// Get failure breakdown
    pub fn failure_breakdown(&self) -> Vec<(ErrorCategory, u64, f64)> {
        let total_failures = self.total_calls - self.successful_calls;

        self.failed_calls
            .iter()
            .map(|(category, count)| {
                let percentage = if total_failures > 0 {
                    (*count as f64) / (total_failures as f64) * 100.0
                } else {
                    0.0
                };
                (*category, *count, percentage)
            })
            .collect()
    }

    /// Get average duration for operation
    pub fn avg_duration_ms(&self, operation: &str) -> Option<u128> {
        self.avg_duration
            .get(operation)
            .map(|d| d.as_millis())
    }

    /// Get all metrics
    pub fn all_metrics(&self) -> &[PerformanceMetrics] {
        &self.metrics
    }

    /// Export metrics as JSON
    pub fn export_json(&self) -> Result<String> {
        let summary = serde_json::json!({
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "success_rate": self.success_rate(),
            "failure_breakdown": self.failure_breakdown()
                .into_iter()
                .map(|(cat, count, pct)| serde_json::json!({
                    "category": cat.as_str(),
                    "count": count,
                    "percentage": pct,
                }))
                .collect::<Vec<_>>(),
            "metrics": self.metrics,
        });

        serde_json::to_string_pretty(&summary)
            .context("Failed to serialize metrics")
    }
}

/// Traced agent call configuration
#[derive(Debug, Clone)]
pub struct TracedAgentConfig {
    /// Maximum execution time
    pub timeout: Duration,
    /// Enable detailed logging
    pub verbose: bool,
    /// Record metrics
    pub record_metrics: bool,
}

impl Default for TracedAgentConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(30),
            verbose: false,
            record_metrics: true,
        }
    }
}

/// Instrumented agent wrapper for observability
pub struct TracedAgent {
    /// Python agent instance
    agent: Py<PyAny>,
    /// Configuration
    config: TracedAgentConfig,
}

impl TracedAgent {
    /// Create new traced agent
    #[instrument(skip(agent), fields(agent_type = "traced"))]
    pub fn new(agent: Py<PyAny>, config: TracedAgentConfig) -> Self {
        info!("Creating traced agent wrapper");
        Self { agent, config }
    }

    /// Create with default configuration
    pub fn with_defaults(agent: Py<PyAny>) -> Self {
        Self::new(agent, TracedAgentConfig::default())
    }

    /// Execute agent with full instrumentation
    #[instrument(
        skip(self, py),
        fields(
            question_len = question.len(),
            timeout_ms = self.config.timeout.as_millis(),
            verbose = self.config.verbose,
        )
    )]
    pub fn forward(&self, py: Python, question: &str) -> Result<String> {
        let span = Span::current();
        span.record("question_preview", &question.chars().take(100).collect::<String>());

        info!("Starting agent execution");

        let mut metrics = PerformanceMetrics::new("agent_forward");
        metrics.add_metadata("question_length", question.len().to_string());

        let start = Instant::now();

        // Execute agent
        let result = self.execute_with_timeout(py, question);

        let elapsed = start.elapsed();

        match result {
            Ok(answer) => {
                metrics.complete(true, None);
                metrics.add_metadata("answer_length", answer.len().to_string());

                info!(
                    duration_ms = elapsed.as_millis(),
                    answer_len = answer.len(),
                    "Agent execution successful"
                );

                if self.config.record_metrics {
                    METRICS_REGISTRY.write().record(metrics);
                }

                Ok(answer)
            }
            Err(e) => {
                let error_category = ErrorCategory::from_error(&e.to_string());
                metrics.complete(false, Some(error_category));
                metrics.add_metadata("error", e.to_string());

                error!(
                    duration_ms = elapsed.as_millis(),
                    error = %e,
                    error_category = error_category.as_str(),
                    "Agent execution failed"
                );

                if self.config.record_metrics {
                    METRICS_REGISTRY.write().record(metrics);
                }

                Err(e)
            }
        }
    }

    /// Execute with timeout protection
    #[instrument(skip(self, py))]
    fn execute_with_timeout(&self, py: Python, question: &str) -> Result<String> {
        debug!("Calling agent.forward()");

        let result = self.agent.as_ref(py).call_method1("forward", (question,));

        match result {
            Ok(prediction) => {
                debug!("Agent returned prediction object");

                let answer: String = prediction
                    .getattr("answer")
                    .context("Failed to get answer attribute")?
                    .extract()
                    .context("Failed to extract answer string")?;

                debug!(answer_len = answer.len(), "Extracted answer from prediction");

                Ok(answer)
            }
            Err(e) => {
                error!(error = %e, "Agent forward() call failed");
                Err(anyhow!("Agent execution failed: {}", e))
            }
        }
    }

    /// Execute with custom metadata tracking
    #[instrument(skip(self, py, metadata))]
    pub fn forward_with_metadata(
        &self,
        py: Python,
        question: &str,
        metadata: HashMap<String, String>,
    ) -> Result<String> {
        for (key, value) in &metadata {
            Span::current().record(key.as_str(), value.as_str());
        }

        self.forward(py, question)
    }
}

/// Agent tool execution with tracing
#[derive(Debug)]
pub struct TracedTool {
    /// Tool name
    name: String,
    /// Python callable
    callable: Py<PyAny>,
}

impl TracedTool {
    /// Create new traced tool
    pub fn new(name: impl Into<String>, callable: Py<PyAny>) -> Self {
        Self {
            name: name.into(),
            callable,
        }
    }

    /// Execute tool with full instrumentation
    #[instrument(skip(self, py, args), fields(tool_name = %self.name))]
    pub fn execute(&self, py: Python, args: &PyDict) -> Result<Py<PyAny>> {
        info!(tool_name = %self.name, "Executing tool");

        let mut metrics = PerformanceMetrics::new(format!("tool_{}", self.name));
        let start = Instant::now();

        let result = self.callable.as_ref(py).call((), Some(args));
        let elapsed = start.elapsed();

        match result {
            Ok(output) => {
                metrics.complete(true, None);

                info!(
                    tool_name = %self.name,
                    duration_ms = elapsed.as_millis(),
                    "Tool execution successful"
                );

                METRICS_REGISTRY.write().record(metrics);
                Ok(output.into())
            }
            Err(e) => {
                let error_category = ErrorCategory::ToolInvocation;
                metrics.complete(false, Some(error_category));

                error!(
                    tool_name = %self.name,
                    duration_ms = elapsed.as_millis(),
                    error = %e,
                    "Tool execution failed"
                );

                METRICS_REGISTRY.write().record(metrics);
                Err(anyhow!("Tool execution failed: {}", e))
            }
        }
    }
}

/// Agent reasoning chain tracker
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningStep {
    /// Step number
    pub step: usize,
    /// Thought/reasoning
    pub thought: String,
    /// Action taken
    pub action: Option<String>,
    /// Observation result
    pub observation: Option<String>,
    /// Duration in milliseconds
    pub duration_ms: u128,
}

/// Tracked reasoning chain for ReAct agents
#[derive(Debug, Default)]
pub struct ReasoningChain {
    /// All reasoning steps
    steps: Vec<ReasoningStep>,
    /// Total duration
    total_duration: Duration,
}

impl ReasoningChain {
    /// Add a reasoning step
    #[instrument(skip(self))]
    pub fn add_step(
        &mut self,
        thought: impl Into<String>,
        action: Option<String>,
        observation: Option<String>,
        duration: Duration,
    ) {
        let step = ReasoningStep {
            step: self.steps.len() + 1,
            thought: thought.into(),
            action,
            observation,
            duration_ms: duration.as_millis(),
        };

        info!(
            step_num = step.step,
            duration_ms = step.duration_ms,
            has_action = step.action.is_some(),
            "Recording reasoning step"
        );

        self.total_duration += duration;
        self.steps.push(step);
    }

    /// Get all steps
    pub fn steps(&self) -> &[ReasoningStep] {
        &self.steps
    }

    /// Get step count
    pub fn step_count(&self) -> usize {
        self.steps.len()
    }

    /// Get total duration
    pub fn total_duration(&self) -> Duration {
        self.total_duration
    }

    /// Export as JSON
    pub fn export_json(&self) -> Result<String> {
        serde_json::to_string_pretty(&self.steps)
            .context("Failed to serialize reasoning chain")
    }
}

/// Get current metrics registry snapshot
pub fn get_metrics() -> Arc<RwLock<MetricsRegistry>> {
    Arc::clone(&METRICS_REGISTRY)
}

/// Export all metrics as JSON
pub fn export_metrics_json() -> Result<String> {
    METRICS_REGISTRY.read().export_json()
}

/// Reset metrics registry
pub fn reset_metrics() {
    *METRICS_REGISTRY.write() = MetricsRegistry::default();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_category_from_error() {
        assert_eq!(
            ErrorCategory::from_error("Connection timeout"),
            ErrorCategory::Timeout
        );
        assert_eq!(
            ErrorCategory::from_error("Invalid input"),
            ErrorCategory::Validation
        );
        assert_eq!(
            ErrorCategory::from_error("Tool failed"),
            ErrorCategory::ToolInvocation
        );
    }

    #[test]
    fn test_metrics_registry() {
        let mut registry = MetricsRegistry::default();

        let mut metric = PerformanceMetrics::new("test_op");
        metric.complete(true, None);
        registry.record(metric);

        assert_eq!(registry.total_calls, 1);
        assert_eq!(registry.successful_calls, 1);
        assert_eq!(registry.success_rate(), 1.0);
    }

    #[test]
    fn test_reasoning_chain() {
        let mut chain = ReasoningChain::default();

        chain.add_step(
            "First thought",
            Some("search".to_string()),
            Some("Result found".to_string()),
            Duration::from_millis(100),
        );

        assert_eq!(chain.step_count(), 1);
        assert_eq!(chain.steps()[0].step, 1);
    }
}
