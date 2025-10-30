//! Parallel Agent Execution System
//!
//! This module provides high-performance concurrent agent execution capabilities
//! using Tokio's JoinSet for parallel processing, result aggregation, and performance
//! benchmarking.

use anyhow::Result;
use dashmap::DashMap;
use futures::stream::{self, StreamExt};
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{RwLock, Semaphore};
use tokio::task::JoinSet;
use tracing::{debug, info, warn};

/// Configuration for parallel agent execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParallelConfig {
    /// Maximum number of concurrent agents
    pub max_concurrency: usize,
    /// Timeout for individual agent execution
    pub agent_timeout: Duration,
    /// Whether to deduplicate results
    pub deduplicate_results: bool,
    /// Minimum confidence for consensus voting
    pub consensus_threshold: f32,
}

impl Default for ParallelConfig {
    fn default() -> Self {
        Self {
            max_concurrency: 4,
            agent_timeout: Duration::from_secs(30),
            deduplicate_results: true,
            consensus_threshold: 0.6,
        }
    }
}

/// Performance metrics for agent execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionMetrics {
    /// Total execution time
    pub total_duration: Duration,
    /// Number of successful executions
    pub successful_count: usize,
    /// Number of failed executions
    pub failed_count: usize,
    /// Average execution time per agent
    pub avg_duration: Duration,
    /// Minimum execution time
    pub min_duration: Duration,
    /// Maximum execution time
    pub max_duration: Duration,
    /// Throughput (requests per second)
    pub throughput: f64,
}

impl ExecutionMetrics {
    pub fn new() -> Self {
        Self {
            total_duration: Duration::ZERO,
            successful_count: 0,
            failed_count: 0,
            avg_duration: Duration::ZERO,
            min_duration: Duration::MAX,
            max_duration: Duration::ZERO,
            throughput: 0.0,
        }
    }

    pub fn update(&mut self, duration: Duration, success: bool) {
        if success {
            self.successful_count += 1;
        } else {
            self.failed_count += 1;
        }

        if duration < self.min_duration {
            self.min_duration = duration;
        }
        if duration > self.max_duration {
            self.max_duration = duration;
        }
    }

    pub fn finalize(&mut self, total_duration: Duration) {
        self.total_duration = total_duration;
        let total_count = self.successful_count + self.failed_count;

        if total_count > 0 {
            self.avg_duration = total_duration / total_count as u32;
            self.throughput = total_count as f64 / total_duration.as_secs_f64();
        }
    }
}

impl Default for ExecutionMetrics {
    fn default() -> Self {
        Self::new()
    }
}

/// Result from a single agent execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentResult {
    /// The agent's answer
    pub answer: String,
    /// Execution duration
    pub duration: Duration,
    /// Whether execution succeeded
    pub success: bool,
    /// Error message if failed
    pub error: Option<String>,
}

/// Aggregated results from multiple agents
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregatedResult {
    /// All individual results
    pub results: Vec<AgentResult>,
    /// Consensus answer (if available)
    pub consensus: Option<String>,
    /// Confidence in consensus (0.0 to 1.0)
    pub confidence: f32,
    /// Performance metrics
    pub metrics: ExecutionMetrics,
}

/// Parallel agent executor using Tokio JoinSet
pub struct ParallelAgentExecutor {
    config: ParallelConfig,
    semaphore: Arc<Semaphore>,
    metrics_cache: Arc<DashMap<String, ExecutionMetrics>>,
}

impl ParallelAgentExecutor {
    /// Create a new parallel agent executor
    pub fn new(config: ParallelConfig) -> Self {
        let semaphore = Arc::new(Semaphore::new(config.max_concurrency));

        info!(
            "Initialized ParallelAgentExecutor with max_concurrency={}",
            config.max_concurrency
        );

        Self {
            config,
            semaphore,
            metrics_cache: Arc::new(DashMap::new()),
        }
    }

    /// Execute multiple agents in parallel using JoinSet
    pub async fn execute_parallel(
        &self,
        questions: Vec<String>,
    ) -> Result<Vec<AgentResult>> {
        let start = Instant::now();
        let mut join_set = JoinSet::new();

        info!("Starting parallel execution of {} questions", questions.len());

        for (idx, question) in questions.into_iter().enumerate() {
            let semaphore = Arc::clone(&self.semaphore);
            let timeout = self.config.agent_timeout;

            join_set.spawn(async move {
                // Acquire permit for rate limiting
                let _permit = semaphore.acquire().await.ok()?;

                let agent_start = Instant::now();

                // Execute agent
                let result = tokio::time::timeout(
                    timeout,
                    Self::execute_single_agent(question.clone(), idx),
                )
                .await;

                let duration = agent_start.elapsed();

                match result {
                    Ok(Ok(answer)) => Some(AgentResult {
                        answer,
                        duration,
                        success: true,
                        error: None,
                    }),
                    Ok(Err(e)) => Some(AgentResult {
                        answer: String::new(),
                        duration,
                        success: false,
                        error: Some(e.to_string()),
                    }),
                    Err(_) => Some(AgentResult {
                        answer: String::new(),
                        duration,
                        success: false,
                        error: Some("Timeout".to_string()),
                    }),
                }
            });
        }

        // Collect results
        let mut results = Vec::new();
        while let Some(result) = join_set.join_next().await {
            match result {
                Ok(Some(agent_result)) => results.push(agent_result),
                Ok(None) => warn!("Agent execution returned None"),
                Err(e) => warn!("Join error: {}", e),
            }
        }

        let total_duration = start.elapsed();
        info!(
            "Parallel execution completed in {:?}, {} results",
            total_duration,
            results.len()
        );

        Ok(results)
    }

    /// Execute agents with result aggregation and voting
    pub async fn execute_with_consensus(
        &self,
        question: String,
        num_agents: usize,
    ) -> Result<AggregatedResult> {
        let start = Instant::now();

        // Create multiple copies of the same question
        let questions: Vec<String> = (0..num_agents)
            .map(|_| question.clone())
            .collect();

        let results = self.execute_parallel(questions).await?;

        // Calculate metrics
        let mut metrics = ExecutionMetrics::new();
        for result in &results {
            metrics.update(result.duration, result.success);
        }
        metrics.finalize(start.elapsed());

        // Find consensus
        let (consensus, confidence) = self.calculate_consensus(&results);

        Ok(AggregatedResult {
            results,
            consensus,
            confidence,
            metrics,
        })
    }

    /// Execute batch of questions with parallel processing
    pub async fn execute_batch(
        &self,
        questions: Vec<String>,
    ) -> Result<Vec<AgentResult>> {
        self.execute_parallel(questions).await
    }

    /// Execute agents using futures stream for more control
    pub async fn execute_with_stream(
        &self,
        questions: Vec<String>,
        buffer_size: usize,
    ) -> Result<Vec<AgentResult>> {
        let start = Instant::now();
        let semaphore = Arc::clone(&self.semaphore);
        let timeout = self.config.agent_timeout;

        let results = stream::iter(questions.into_iter().enumerate())
            .map(|(idx, question)| {
                let semaphore = Arc::clone(&semaphore);
                async move {
                    let _permit = semaphore.acquire().await.ok()?;
                    let agent_start = Instant::now();

                    let result = tokio::time::timeout(
                        timeout,
                        Self::execute_single_agent(question, idx),
                    )
                    .await;

                    let duration = agent_start.elapsed();

                    match result {
                        Ok(Ok(answer)) => Some(AgentResult {
                            answer,
                            duration,
                            success: true,
                            error: None,
                        }),
                        Ok(Err(e)) => Some(AgentResult {
                            answer: String::new(),
                            duration,
                            success: false,
                            error: Some(e.to_string()),
                        }),
                        Err(_) => Some(AgentResult {
                            answer: String::new(),
                            duration,
                            success: false,
                            error: Some("Timeout".to_string()),
                        }),
                    }
                }
            })
            .buffer_unordered(buffer_size)
            .collect::<Vec<_>>()
            .await;

        let valid_results: Vec<AgentResult> = results.into_iter().flatten().collect();

        info!(
            "Stream execution completed in {:?}, {} results",
            start.elapsed(),
            valid_results.len()
        );

        Ok(valid_results)
    }

    /// Calculate consensus from results
    fn calculate_consensus(&self, results: &[AgentResult]) -> (Option<String>, f32) {
        let mut answer_counts: HashMap<String, usize> = HashMap::new();
        let mut total_valid = 0;

        for result in results {
            if result.success && !result.answer.is_empty() {
                *answer_counts.entry(result.answer.clone()).or_insert(0) += 1;
                total_valid += 1;
            }
        }

        if total_valid == 0 {
            return (None, 0.0);
        }

        // Find most common answer
        let (answer, count) = answer_counts
            .iter()
            .max_by_key(|(_, count)| *count)
            .map(|(a, c)| (a.clone(), *c))
            .unwrap_or((String::new(), 0));

        let confidence = count as f32 / total_valid as f32;

        if confidence >= self.config.consensus_threshold {
            (Some(answer), confidence)
        } else {
            (None, confidence)
        }
    }

    /// Deduplicate results based on answer similarity
    pub fn deduplicate_results(&self, results: Vec<AgentResult>) -> Vec<AgentResult> {
        if !self.config.deduplicate_results {
            return results;
        }

        let mut seen = HashMap::new();
        let mut deduplicated = Vec::new();

        for result in results {
            let key = result.answer.to_lowercase().trim().to_string();

            if !seen.contains_key(&key) {
                seen.insert(key, true);
                deduplicated.push(result);
            }
        }

        debug!(
            "Deduplicated {} results to {}",
            seen.len() + deduplicated.len(),
            deduplicated.len()
        );

        deduplicated
    }

    /// Execute a single agent (mock implementation)
    async fn execute_single_agent(question: String, agent_id: usize) -> Result<String> {
        debug!("Agent {} processing: {}", agent_id, question);

        // Simulate PyO3 call to DSPy agent
        Python::with_gil(|py| {
            let result = Self::call_dspy_agent(py, &question, agent_id)?;
            Ok(result)
        })
    }

    /// Call DSPy agent via PyO3 (mock implementation for example)
    fn call_dspy_agent(py: Python, question: &str, agent_id: usize) -> Result<String> {
        // In a real implementation, this would call actual DSPy ReAct agent
        // For this example, we'll return a mock response

        let sys = py.import_bound("sys")?;
        let version: String = sys.getattr("version")?.extract()?;

        Ok(format!(
            "Agent {} answer for '{}' (Python: {})",
            agent_id,
            question,
            version.split_whitespace().next().unwrap_or("unknown")
        ))
    }

    /// Get cached metrics for a question
    pub fn get_metrics(&self, question: &str) -> Option<ExecutionMetrics> {
        self.metrics_cache.get(question).map(|m| m.clone())
    }

    /// Store metrics for a question
    pub fn store_metrics(&self, question: String, metrics: ExecutionMetrics) {
        self.metrics_cache.insert(question, metrics);
    }
}

impl Default for ParallelAgentExecutor {
    fn default() -> Self {
        Self::new(ParallelConfig::default())
    }
}

/// Agent pool for managing multiple agent instances
pub struct AgentPool {
    size: usize,
    #[allow(dead_code)]
    semaphore: Arc<Semaphore>,
    executor: Arc<RwLock<ParallelAgentExecutor>>,
}

impl AgentPool {
    pub fn new(size: usize, config: ParallelConfig) -> Self {
        let executor = ParallelAgentExecutor::new(config);

        Self {
            size,
            semaphore: Arc::new(Semaphore::new(size)),
            executor: Arc::new(RwLock::new(executor)),
        }
    }

    pub async fn execute_batch(&self, questions: Vec<String>) -> Result<Vec<AgentResult>> {
        let executor = self.executor.read().await;
        executor.execute_batch(questions).await
    }

    pub fn pool_size(&self) -> usize {
        self.size
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_parallel_execution() {
        let config = ParallelConfig::default();
        let executor = ParallelAgentExecutor::new(config);

        let questions = vec![
            "What is 2+2?".to_string(),
            "What is the capital of France?".to_string(),
        ];

        let results = executor.execute_parallel(questions).await.unwrap();
        assert_eq!(results.len(), 2);
    }

    #[tokio::test]
    async fn test_consensus() {
        let config = ParallelConfig {
            consensus_threshold: 0.5,
            ..Default::default()
        };
        let executor = ParallelAgentExecutor::new(config);

        let result = executor
            .execute_with_consensus("What is 2+2?".to_string(), 3)
            .await
            .unwrap();

        assert_eq!(result.results.len(), 3);
    }

    #[test]
    fn test_metrics_update() {
        let mut metrics = ExecutionMetrics::new();

        metrics.update(Duration::from_millis(100), true);
        metrics.update(Duration::from_millis(200), true);
        metrics.finalize(Duration::from_millis(300));

        assert_eq!(metrics.successful_count, 2);
        assert_eq!(metrics.min_duration, Duration::from_millis(100));
        assert_eq!(metrics.max_duration, Duration::from_millis(200));
    }
}
