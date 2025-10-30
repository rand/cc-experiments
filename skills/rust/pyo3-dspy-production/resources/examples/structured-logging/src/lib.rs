//! Production-grade structured logging infrastructure for DSPy integration.
//!
//! This module provides comprehensive tracing and logging capabilities including:
//! - Request ID propagation and correlation
//! - Multi-format output (JSON, pretty console)
//! - Custom DSPy-specific event tracking
//! - Performance measurement and aggregation
//! - Error context preservation

use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{debug, error, info, instrument, trace, warn, Level};
use tracing_subscriber::{
    fmt::format::FmtSpan, layer::SubscriberExt, util::SubscriberInitExt, EnvFilter, Layer,
};
use uuid::Uuid;

// ============================================================================
// Configuration
// ============================================================================

/// Logging output format
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LogFormat {
    /// Human-readable pretty format
    Pretty,
    /// Machine-parseable JSON format
    Json,
    /// Compact format for high-throughput scenarios
    Compact,
}

/// Logging configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoggingConfig {
    /// Minimum log level
    pub level: String,
    /// Output format
    pub format: LogFormat,
    /// Enable console output
    pub console_enabled: bool,
    /// Enable file output
    pub file_enabled: bool,
    /// File output path (if file_enabled)
    pub file_path: Option<String>,
    /// Enable request ID propagation
    pub request_id_enabled: bool,
    /// Enable performance metrics
    pub performance_metrics_enabled: bool,
    /// Enable DSPy-specific instrumentation
    pub dspy_instrumentation_enabled: bool,
}

impl Default for LoggingConfig {
    fn default() -> Self {
        Self {
            level: "info".to_string(),
            format: LogFormat::Pretty,
            console_enabled: true,
            file_enabled: false,
            file_path: None,
            request_id_enabled: true,
            performance_metrics_enabled: true,
            dspy_instrumentation_enabled: true,
        }
    }
}

// ============================================================================
// Request Context and Correlation
// ============================================================================

/// Request context for correlation and tracing
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestContext {
    /// Unique request identifier
    pub request_id: Uuid,
    /// Optional parent request ID for nested operations
    pub parent_id: Option<Uuid>,
    /// Request timestamp
    pub timestamp: DateTime<Utc>,
    /// Optional user/client identifier
    pub user_id: Option<String>,
    /// Custom metadata
    pub metadata: HashMap<String, String>,
}

impl RequestContext {
    /// Create a new root request context
    pub fn new() -> Self {
        Self {
            request_id: Uuid::new_v4(),
            parent_id: None,
            timestamp: Utc::now(),
            user_id: None,
            metadata: HashMap::new(),
        }
    }

    /// Create a child context from this context
    pub fn child(&self) -> Self {
        Self {
            request_id: Uuid::new_v4(),
            parent_id: Some(self.request_id),
            timestamp: Utc::now(),
            user_id: self.user_id.clone(),
            metadata: self.metadata.clone(),
        }
    }

    /// Add metadata to context
    pub fn with_metadata(mut self, key: String, value: String) -> Self {
        self.metadata.insert(key, value);
        self
    }

    /// Set user ID
    pub fn with_user_id(mut self, user_id: String) -> Self {
        self.user_id = Some(user_id);
        self
    }
}

impl Default for RequestContext {
    fn default() -> Self {
        Self::new()
    }
}

impl fmt::Display for RequestContext {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "req_id={}", self.request_id)?;
        if let Some(parent) = self.parent_id {
            write!(f, " parent_id={}", parent)?;
        }
        if let Some(user) = &self.user_id {
            write!(f, " user_id={}", user)?;
        }
        Ok(())
    }
}

// ============================================================================
// DSPy Event Tracking
// ============================================================================

/// DSPy-specific event types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum DSpyEvent {
    /// Model prediction event
    Prediction {
        model: String,
        prompt_tokens: usize,
        completion_tokens: usize,
        latency_ms: u64,
    },
    /// Optimization step
    Optimization {
        optimizer: String,
        iteration: usize,
        score: f64,
        improvement: f64,
    },
    /// Pipeline execution
    Pipeline {
        pipeline: String,
        stage: String,
        status: String,
    },
    /// Cache operation
    Cache {
        operation: String,
        hit: bool,
        key: String,
    },
}

impl DSpyEvent {
    /// Log the event at appropriate level
    #[instrument(skip(self))]
    pub fn log(&self, context: &RequestContext) {
        match self {
            DSpyEvent::Prediction {
                model,
                prompt_tokens,
                completion_tokens,
                latency_ms,
            } => {
                info!(
                    request_id = %context.request_id,
                    model = %model,
                    prompt_tokens = prompt_tokens,
                    completion_tokens = completion_tokens,
                    latency_ms = latency_ms,
                    total_tokens = prompt_tokens + completion_tokens,
                    "DSPy prediction completed"
                );
            }
            DSpyEvent::Optimization {
                optimizer,
                iteration,
                score,
                improvement,
            } => {
                info!(
                    request_id = %context.request_id,
                    optimizer = %optimizer,
                    iteration = iteration,
                    score = score,
                    improvement = improvement,
                    "DSPy optimization step"
                );
            }
            DSpyEvent::Pipeline {
                pipeline,
                stage,
                status,
            } => {
                debug!(
                    request_id = %context.request_id,
                    pipeline = %pipeline,
                    stage = %stage,
                    status = %status,
                    "DSPy pipeline stage"
                );
            }
            DSpyEvent::Cache { operation, hit, key } => {
                trace!(
                    request_id = %context.request_id,
                    operation = %operation,
                    hit = hit,
                    key = %key,
                    "DSPy cache operation"
                );
            }
        }
    }
}

// ============================================================================
// Performance Metrics
// ============================================================================

/// Performance measurement for operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceMetric {
    pub operation: String,
    pub duration_ms: u64,
    pub success: bool,
    pub timestamp: DateTime<Utc>,
    pub context: RequestContext,
}

impl PerformanceMetric {
    /// Log the metric
    #[instrument(skip(self))]
    pub fn log(&self) {
        let level = if self.success { Level::INFO } else { Level::WARN };

        match level {
            Level::INFO => info!(
                request_id = %self.context.request_id,
                operation = %self.operation,
                duration_ms = self.duration_ms,
                success = self.success,
                "Performance metric"
            ),
            _ => warn!(
                request_id = %self.context.request_id,
                operation = %self.operation,
                duration_ms = self.duration_ms,
                success = self.success,
                "Performance metric (failure)"
            ),
        }
    }
}

/// Metrics aggregator for collecting and reporting performance data
#[derive(Debug, Clone)]
pub struct MetricsAggregator {
    metrics: Arc<RwLock<Vec<PerformanceMetric>>>,
}

impl MetricsAggregator {
    /// Create a new metrics aggregator
    pub fn new() -> Self {
        Self {
            metrics: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Record a metric
    #[instrument(skip(self))]
    pub async fn record(&self, metric: PerformanceMetric) {
        metric.log();
        let mut metrics = self.metrics.write().await;
        metrics.push(metric);
    }

    /// Get summary statistics
    #[instrument(skip(self))]
    pub async fn summarize(&self) -> MetricsSummary {
        let metrics = self.metrics.read().await;

        if metrics.is_empty() {
            return MetricsSummary::default();
        }

        let total = metrics.len();
        let successful = metrics.iter().filter(|m| m.success).count();
        let durations: Vec<u64> = metrics.iter().map(|m| m.duration_ms).collect();

        let sum: u64 = durations.iter().sum();
        let mean = sum as f64 / durations.len() as f64;

        let mut sorted = durations.clone();
        sorted.sort_unstable();
        let p50 = sorted[sorted.len() / 2];
        let p95 = sorted[(sorted.len() as f64 * 0.95) as usize];
        let p99 = sorted[(sorted.len() as f64 * 0.99) as usize];
        let max = *sorted.last().unwrap();

        MetricsSummary {
            total_operations: total,
            successful_operations: successful,
            mean_duration_ms: mean,
            p50_duration_ms: p50,
            p95_duration_ms: p95,
            p99_duration_ms: p99,
            max_duration_ms: max,
        }
    }

    /// Clear all collected metrics
    pub async fn clear(&self) {
        let mut metrics = self.metrics.write().await;
        metrics.clear();
    }
}

impl Default for MetricsAggregator {
    fn default() -> Self {
        Self::new()
    }
}

/// Summary of aggregated metrics
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MetricsSummary {
    pub total_operations: usize,
    pub successful_operations: usize,
    pub mean_duration_ms: f64,
    pub p50_duration_ms: u64,
    pub p95_duration_ms: u64,
    pub p99_duration_ms: u64,
    pub max_duration_ms: u64,
}

impl fmt::Display for MetricsSummary {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        writeln!(f, "Metrics Summary:")?;
        writeln!(f, "  Total Operations: {}", self.total_operations)?;
        writeln!(f, "  Successful: {}", self.successful_operations)?;
        writeln!(f, "  Mean Duration: {:.2}ms", self.mean_duration_ms)?;
        writeln!(f, "  P50: {}ms", self.p50_duration_ms)?;
        writeln!(f, "  P95: {}ms", self.p95_duration_ms)?;
        writeln!(f, "  P99: {}ms", self.p99_duration_ms)?;
        writeln!(f, "  Max: {}ms", self.max_duration_ms)?;
        Ok(())
    }
}

// ============================================================================
// Instrumented DSPy Service
// ============================================================================

/// Instrumented wrapper for DSPy operations
pub struct InstrumentedDSpyService {
    config: LoggingConfig,
    metrics: MetricsAggregator,
}

impl InstrumentedDSpyService {
    /// Create a new instrumented service
    pub fn new(config: LoggingConfig) -> Self {
        Self {
            config,
            metrics: MetricsAggregator::new(),
        }
    }

    /// Execute a prediction with full instrumentation
    #[instrument(skip(self, context, prompt), fields(request_id = %context.request_id))]
    pub async fn predict(
        &self,
        context: RequestContext,
        model: String,
        prompt: String,
    ) -> Result<String> {
        let start = std::time::Instant::now();

        info!(
            model = %model,
            prompt_len = prompt.len(),
            "Starting prediction"
        );

        // Simulate prediction work
        let result = self.execute_prediction(&model, &prompt).await;

        let duration = start.elapsed();
        let duration_ms = duration.as_millis() as u64;

        match &result {
            Ok(response) => {
                let event = DSpyEvent::Prediction {
                    model: model.clone(),
                    prompt_tokens: prompt.len() / 4, // Rough approximation
                    completion_tokens: response.len() / 4,
                    latency_ms: duration_ms,
                };
                event.log(&context);

                if self.config.performance_metrics_enabled {
                    self.metrics
                        .record(PerformanceMetric {
                            operation: format!("predict:{}", model),
                            duration_ms,
                            success: true,
                            timestamp: Utc::now(),
                            context: context.clone(),
                        })
                        .await;
                }

                info!(
                    duration_ms = duration_ms,
                    response_len = response.len(),
                    "Prediction completed successfully"
                );
            }
            Err(e) => {
                error!(
                    error = %e,
                    duration_ms = duration_ms,
                    "Prediction failed"
                );

                if self.config.performance_metrics_enabled {
                    self.metrics
                        .record(PerformanceMetric {
                            operation: format!("predict:{}", model),
                            duration_ms,
                            success: false,
                            timestamp: Utc::now(),
                            context: context.clone(),
                        })
                        .await;
                }
            }
        }

        result
    }

    /// Execute optimization with instrumentation
    #[instrument(skip(self, context), fields(request_id = %context.request_id))]
    pub async fn optimize(
        &self,
        context: RequestContext,
        optimizer: String,
        iterations: usize,
    ) -> Result<f64> {
        let start = std::time::Instant::now();

        info!(
            optimizer = %optimizer,
            iterations = iterations,
            "Starting optimization"
        );

        let mut best_score = 0.0;
        let mut previous_score = 0.0;

        for i in 0..iterations {
            let iteration_start = std::time::Instant::now();

            // Simulate optimization step
            let score = self.execute_optimization_step(i).await?;
            let improvement = score - previous_score;

            let event = DSpyEvent::Optimization {
                optimizer: optimizer.clone(),
                iteration: i,
                score,
                improvement,
            };
            event.log(&context);

            debug!(
                iteration = i,
                score = score,
                improvement = improvement,
                duration_ms = iteration_start.elapsed().as_millis() as u64,
                "Optimization step completed"
            );

            best_score = score.max(best_score);
            previous_score = score;
        }

        let duration = start.elapsed();

        info!(
            duration_ms = duration.as_millis() as u64,
            best_score = best_score,
            iterations = iterations,
            "Optimization completed"
        );

        if self.config.performance_metrics_enabled {
            self.metrics
                .record(PerformanceMetric {
                    operation: format!("optimize:{}", optimizer),
                    duration_ms: duration.as_millis() as u64,
                    success: true,
                    timestamp: Utc::now(),
                    context,
                })
                .await;
        }

        Ok(best_score)
    }

    /// Execute pipeline with stage tracking
    #[instrument(skip(self, context, stages), fields(request_id = %context.request_id))]
    pub async fn execute_pipeline(
        &self,
        context: RequestContext,
        pipeline: String,
        stages: Vec<String>,
    ) -> Result<()> {
        info!(
            pipeline = %pipeline,
            stage_count = stages.len(),
            "Starting pipeline execution"
        );

        for (idx, stage) in stages.iter().enumerate() {
            let stage_start = std::time::Instant::now();

            let event = DSpyEvent::Pipeline {
                pipeline: pipeline.clone(),
                stage: stage.clone(),
                status: "started".to_string(),
            };
            event.log(&context);

            // Execute stage
            self.execute_stage(stage).await?;

            let duration = stage_start.elapsed();

            let event = DSpyEvent::Pipeline {
                pipeline: pipeline.clone(),
                stage: stage.clone(),
                status: "completed".to_string(),
            };
            event.log(&context);

            debug!(
                stage = %stage,
                stage_index = idx,
                duration_ms = duration.as_millis() as u64,
                "Pipeline stage completed"
            );
        }

        info!(
            pipeline = %pipeline,
            "Pipeline execution completed"
        );

        Ok(())
    }

    /// Get metrics summary
    pub async fn metrics_summary(&self) -> MetricsSummary {
        self.metrics.summarize().await
    }

    // Private helper methods

    async fn execute_prediction(&self, model: &str, prompt: &str) -> Result<String> {
        // Simulate work
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
        Ok(format!("Response from {} to prompt: {}", model, prompt))
    }

    async fn execute_optimization_step(&self, iteration: usize) -> Result<f64> {
        // Simulate work
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
        Ok(0.5 + (iteration as f64 * 0.1))
    }

    async fn execute_stage(&self, stage: &str) -> Result<()> {
        // Simulate work
        tokio::time::sleep(tokio::time::Duration::from_millis(30)).await;
        debug!(stage = %stage, "Stage execution simulated");
        Ok(())
    }
}

// ============================================================================
// Logging Initialization
// ============================================================================

/// Initialize logging with the provided configuration
pub fn init_logging(config: &LoggingConfig) -> Result<()> {
    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(&config.level));

    let subscriber = tracing_subscriber::registry().with(env_filter);

    // Console layer
    if config.console_enabled {
        let console_layer = match config.format {
            LogFormat::Pretty => tracing_subscriber::fmt::layer()
                .pretty()
                .with_span_events(FmtSpan::CLOSE)
                .with_target(true)
                .with_line_number(true)
                .boxed(),
            LogFormat::Json => tracing_subscriber::fmt::layer()
                .json()
                .with_span_events(FmtSpan::CLOSE)
                .boxed(),
            LogFormat::Compact => tracing_subscriber::fmt::layer()
                .compact()
                .with_span_events(FmtSpan::CLOSE)
                .boxed(),
        };

        subscriber.with(console_layer).init();
    } else {
        subscriber.init();
    }

    info!("Logging initialized with config: {:?}", config);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_request_context_creation() {
        let ctx = RequestContext::new();
        assert!(ctx.parent_id.is_none());
        assert!(ctx.user_id.is_none());
    }

    #[test]
    fn test_request_context_child() {
        let parent = RequestContext::new();
        let child = parent.child();
        assert_eq!(child.parent_id, Some(parent.request_id));
    }

    #[tokio::test]
    async fn test_metrics_aggregator() {
        let aggregator = MetricsAggregator::new();
        let ctx = RequestContext::new();

        aggregator
            .record(PerformanceMetric {
                operation: "test".to_string(),
                duration_ms: 100,
                success: true,
                timestamp: Utc::now(),
                context: ctx,
            })
            .await;

        let summary = aggregator.summarize().await;
        assert_eq!(summary.total_operations, 1);
        assert_eq!(summary.successful_operations, 1);
    }
}
