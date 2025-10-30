//! Concurrent batch processing for DSPy predictions
//!
//! This module provides high-performance concurrent execution of multiple DSPy
//! predictions with rate limiting, result aggregation, and comprehensive metrics.
//!
//! # Features
//!
//! - Concurrent execution using Tokio JoinSet
//! - Semaphore-based rate limiting
//! - Performance benchmarking and metrics
//! - Result deduplication with DashMap
//! - Sequential vs parallel comparison
//!
//! # Examples
//!
//! ```no_run
//! use concurrent_batch::{BatchPredictor, BatchConfig};
//! use anyhow::Result;
//!
//! #[tokio::main]
//! async fn main() -> Result<()> {
//!     let config = BatchConfig::new(10, "question -> answer");
//!     let predictor = BatchPredictor::new(config)?;
//!
//!     let questions = vec![
//!         "What is Rust?".to_string(),
//!         "What is async programming?".to_string(),
//!     ];
//!
//!     let results = predictor.predict_batch(questions).await?;
//!     println!("Results: {:?}", results);
//!
//!     Ok(())
//! }
//! ```

use anyhow::{Context, Result};
use dashmap::DashMap;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Semaphore;
use tokio::task::JoinSet;

/// Configuration for batch processing
#[derive(Debug, Clone)]
pub struct BatchConfig {
    /// Maximum number of concurrent predictions
    pub max_concurrent: usize,
    /// DSPy signature (e.g., "question -> answer")
    pub signature: String,
    /// Enable result caching/deduplication
    pub enable_cache: bool,
    /// Timeout per prediction (seconds)
    pub timeout_secs: u64,
}

impl BatchConfig {
    /// Create new configuration
    pub fn new(max_concurrent: usize, signature: impl Into<String>) -> Self {
        Self {
            max_concurrent,
            signature: signature.into(),
            enable_cache: true,
            timeout_secs: 30,
        }
    }

    /// Builder: Set cache enabled
    pub fn with_cache(mut self, enabled: bool) -> Self {
        self.enable_cache = enabled;
        self
    }

    /// Builder: Set timeout
    pub fn with_timeout(mut self, secs: u64) -> Self {
        self.timeout_secs = secs;
        self
    }
}

/// Metrics for batch execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BatchMetrics {
    /// Total questions processed
    pub total_questions: usize,
    /// Successful predictions
    pub successful: usize,
    /// Failed predictions
    pub failed: usize,
    /// Total duration
    pub duration: Duration,
    /// Per-question latencies (ms)
    pub latencies: Vec<u64>,
    /// Cache hits (if enabled)
    pub cache_hits: usize,
    /// Rate limit wait count
    pub rate_limit_waits: usize,
    /// Peak concurrent tasks
    pub peak_concurrent: usize,
}

impl BatchMetrics {
    /// Create new metrics
    fn new() -> Self {
        Self {
            total_questions: 0,
            successful: 0,
            failed: 0,
            duration: Duration::from_secs(0),
            latencies: Vec::new(),
            cache_hits: 0,
            rate_limit_waits: 0,
            peak_concurrent: 0,
        }
    }

    /// Calculate throughput (questions/sec)
    pub fn throughput(&self) -> f64 {
        self.total_questions as f64 / self.duration.as_secs_f64()
    }

    /// Calculate success rate
    pub fn success_rate(&self) -> f64 {
        if self.total_questions == 0 {
            0.0
        } else {
            self.successful as f64 / self.total_questions as f64
        }
    }

    /// Get latency percentile (ms)
    pub fn latency_percentile(&self, percentile: f64) -> Option<u64> {
        if self.latencies.is_empty() {
            return None;
        }

        let mut sorted = self.latencies.clone();
        sorted.sort_unstable();

        let index = ((percentile / 100.0) * sorted.len() as f64) as usize;
        Some(sorted[index.min(sorted.len() - 1)])
    }

    /// Get average latency (ms)
    pub fn avg_latency(&self) -> f64 {
        if self.latencies.is_empty() {
            0.0
        } else {
            self.latencies.iter().sum::<u64>() as f64 / self.latencies.len() as f64
        }
    }
}

/// Result of a single prediction
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictionResult {
    pub question: String,
    pub answer: String,
    pub latency_ms: u64,
    pub from_cache: bool,
}

/// Internal metrics tracking (atomic for concurrent updates)
struct MetricsTracker {
    total: AtomicUsize,
    successful: AtomicUsize,
    failed: AtomicUsize,
    cache_hits: AtomicUsize,
    rate_limit_waits: AtomicUsize,
    peak_concurrent: AtomicUsize,
    current_concurrent: AtomicUsize,
}

impl MetricsTracker {
    fn new() -> Self {
        Self {
            total: AtomicUsize::new(0),
            successful: AtomicUsize::new(0),
            failed: AtomicUsize::new(0),
            cache_hits: AtomicUsize::new(0),
            rate_limit_waits: AtomicUsize::new(0),
            peak_concurrent: AtomicUsize::new(0),
            current_concurrent: AtomicUsize::new(0),
        }
    }

    fn increment_concurrent(&self) -> usize {
        let current = self.current_concurrent.fetch_add(1, Ordering::SeqCst) + 1;
        let peak = self.peak_concurrent.load(Ordering::SeqCst);
        if current > peak {
            self.peak_concurrent.store(current, peak.max(current));
        }
        current
    }

    fn decrement_concurrent(&self) {
        self.current_concurrent.fetch_sub(1, Ordering::SeqCst);
    }
}

/// Batch predictor with concurrent execution
pub struct BatchPredictor {
    semaphore: Arc<Semaphore>,
    predictor: Arc<Py<PyAny>>,
    config: BatchConfig,
    cache: Arc<DashMap<String, String>>,
    metrics_tracker: Arc<MetricsTracker>,
}

impl BatchPredictor {
    /// Create new batch predictor
    pub fn new(config: BatchConfig) -> Result<Self> {
        // Initialize DSPy predictor with GIL
        let predictor = Python::with_gil(|py| {
            let dspy = py.import("dspy").context("Failed to import dspy")?;
            let pred = dspy
                .getattr("Predict")
                .context("Failed to get Predict class")?
                .call1((&config.signature,))
                .context("Failed to create predictor")?;
            Ok::<_, anyhow::Error>(Py::from(pred))
        })?;

        Ok(Self {
            semaphore: Arc::new(Semaphore::new(config.max_concurrent)),
            predictor: Arc::new(predictor),
            config,
            cache: Arc::new(DashMap::new()),
            metrics_tracker: Arc::new(MetricsTracker::new()),
        })
    }

    /// Execute batch predictions concurrently
    pub async fn predict_batch(&self, questions: Vec<String>) -> Result<Vec<PredictionResult>> {
        let start = Instant::now();
        let mut set = JoinSet::new();
        let mut latencies = Vec::new();

        for question in questions.iter() {
            // Check cache first
            if self.config.enable_cache {
                if let Some(cached) = self.cache.get(question) {
                    self.metrics_tracker.cache_hits.fetch_add(1, Ordering::SeqCst);
                    let result = PredictionResult {
                        question: question.clone(),
                        answer: cached.clone(),
                        latency_ms: 0,
                        from_cache: true,
                    };
                    set.spawn(async move { Ok(result) });
                    continue;
                }
            }

            // Spawn concurrent task
            let question_clone = question.clone();
            let semaphore = Arc::clone(&self.semaphore);
            let predictor = Arc::clone(&self.predictor);
            let cache = Arc::clone(&self.cache);
            let tracker = Arc::clone(&self.metrics_tracker);
            let enable_cache = self.config.enable_cache;
            let timeout = Duration::from_secs(self.config.timeout_secs);

            set.spawn(async move {
                Self::predict_single(
                    question_clone,
                    semaphore,
                    predictor,
                    cache,
                    tracker,
                    enable_cache,
                    timeout,
                )
                .await
            });
        }

        // Collect results
        let mut results = Vec::new();
        while let Some(result) = set.join_next().await {
            match result {
                Ok(Ok(pred_result)) => {
                    latencies.push(pred_result.latency_ms);
                    results.push(pred_result);
                    self.metrics_tracker.successful.fetch_add(1, Ordering::SeqCst);
                }
                Ok(Err(e)) => {
                    eprintln!("Prediction failed: {}", e);
                    self.metrics_tracker.failed.fetch_add(1, Ordering::SeqCst);
                }
                Err(e) => {
                    eprintln!("Task join failed: {}", e);
                    self.metrics_tracker.failed.fetch_add(1, Ordering::SeqCst);
                }
            }
        }

        let duration = start.elapsed();
        self.metrics_tracker
            .total
            .store(questions.len(), Ordering::SeqCst);

        Ok(results)
    }

    /// Execute predictions sequentially (for comparison)
    pub async fn predict_sequential(&self, questions: Vec<String>) -> Result<Vec<PredictionResult>> {
        let start = Instant::now();
        let mut results = Vec::new();

        for question in questions {
            let question_clone = question.clone();
            let predictor = Arc::clone(&self.predictor);

            let pred_start = Instant::now();
            let answer = tokio::task::spawn_blocking(move || {
                Python::with_gil(|py| {
                    let result = predictor
                        .as_ref(py)
                        .call_method1("__call__", (question_clone,))
                        .context("Prediction call failed")?;
                    let answer: String = result
                        .getattr("answer")
                        .context("No answer attribute")?
                        .extract()
                        .context("Failed to extract answer")?;
                    Ok::<_, anyhow::Error>(answer)
                })
            })
            .await
            .context("Task join failed")??;

            let latency_ms = pred_start.elapsed().as_millis() as u64;

            results.push(PredictionResult {
                question,
                answer,
                latency_ms,
                from_cache: false,
            });
        }

        Ok(results)
    }

    /// Get current metrics snapshot
    pub fn get_metrics(&self, duration: Duration) -> BatchMetrics {
        let mut metrics = BatchMetrics::new();
        metrics.total_questions = self.metrics_tracker.total.load(Ordering::SeqCst);
        metrics.successful = self.metrics_tracker.successful.load(Ordering::SeqCst);
        metrics.failed = self.metrics_tracker.failed.load(Ordering::SeqCst);
        metrics.cache_hits = self.metrics_tracker.cache_hits.load(Ordering::SeqCst);
        metrics.rate_limit_waits = self.metrics_tracker.rate_limit_waits.load(Ordering::SeqCst);
        metrics.peak_concurrent = self.metrics_tracker.peak_concurrent.load(Ordering::SeqCst);
        metrics.duration = duration;
        metrics
    }

    /// Clear cache
    pub fn clear_cache(&self) {
        self.cache.clear();
    }

    /// Get cache size
    pub fn cache_size(&self) -> usize {
        self.cache.len()
    }

    /// Internal: Execute single prediction
    async fn predict_single(
        question: String,
        semaphore: Arc<Semaphore>,
        predictor: Arc<Py<PyAny>>,
        cache: Arc<DashMap<String, String>>,
        tracker: Arc<MetricsTracker>,
        enable_cache: bool,
        timeout: Duration,
    ) -> Result<PredictionResult> {
        // Acquire semaphore permit (rate limiting)
        let _permit = semaphore.acquire().await.context("Semaphore closed")?;
        tracker.increment_concurrent();

        let question_clone = question.clone();
        let pred_start = Instant::now();

        // Execute prediction with timeout
        let answer = tokio::time::timeout(timeout, tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                let result = predictor
                    .as_ref(py)
                    .call_method1("__call__", (question_clone,))
                    .context("Prediction call failed")?;
                let answer: String = result
                    .getattr("answer")
                    .context("No answer attribute")?
                    .extract()
                    .context("Failed to extract answer")?;
                Ok::<_, anyhow::Error>(answer)
            })
        }))
        .await
        .context("Prediction timeout")??;

        let latency_ms = pred_start.elapsed().as_millis() as u64;
        tracker.decrement_concurrent();

        // Store in cache
        if enable_cache {
            cache.insert(question.clone(), answer.clone());
        }

        Ok(PredictionResult {
            question,
            answer: answer?,
            latency_ms,
            from_cache: false,
        })
    }
}

/// Benchmark result comparing sequential vs concurrent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkResult {
    pub sequential_duration: Duration,
    pub concurrent_duration: Duration,
    pub speedup: f64,
    pub sequential_throughput: f64,
    pub concurrent_throughput: f64,
    pub efficiency: f64,
}

impl BenchmarkResult {
    /// Calculate efficiency (speedup / max_concurrent)
    pub fn calculate_efficiency(speedup: f64, max_concurrent: usize) -> f64 {
        speedup / max_concurrent as f64
    }
}

/// Run benchmark comparing sequential vs concurrent execution
pub async fn benchmark(
    questions: Vec<String>,
    max_concurrent: usize,
    signature: &str,
) -> Result<BenchmarkResult> {
    let config = BatchConfig::new(max_concurrent, signature);
    let predictor = BatchPredictor::new(config)?;

    // Sequential execution
    println!("Running sequential execution...");
    let seq_start = Instant::now();
    let seq_results = predictor.predict_sequential(questions.clone()).await?;
    let seq_duration = seq_start.elapsed();
    let seq_throughput = seq_results.len() as f64 / seq_duration.as_secs_f64();

    // Concurrent execution
    println!("Running concurrent execution...");
    predictor.clear_cache(); // Clear cache for fair comparison
    let conc_start = Instant::now();
    let conc_results = predictor.predict_batch(questions.clone()).await?;
    let conc_duration = conc_start.elapsed();
    let conc_throughput = conc_results.len() as f64 / conc_duration.as_secs_f64();

    let speedup = seq_duration.as_secs_f64() / conc_duration.as_secs_f64();
    let efficiency = BenchmarkResult::calculate_efficiency(speedup, max_concurrent);

    Ok(BenchmarkResult {
        sequential_duration: seq_duration,
        concurrent_duration: conc_duration,
        speedup,
        sequential_throughput: seq_throughput,
        concurrent_throughput: conc_throughput,
        efficiency,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_batch_config() {
        let config = BatchConfig::new(10, "question -> answer")
            .with_cache(false)
            .with_timeout(60);

        assert_eq!(config.max_concurrent, 10);
        assert_eq!(config.signature, "question -> answer");
        assert!(!config.enable_cache);
        assert_eq!(config.timeout_secs, 60);
    }

    #[test]
    fn test_batch_metrics() {
        let mut metrics = BatchMetrics::new();
        metrics.total_questions = 100;
        metrics.successful = 95;
        metrics.failed = 5;
        metrics.duration = Duration::from_secs(10);

        assert_eq!(metrics.throughput(), 10.0);
        assert_eq!(metrics.success_rate(), 0.95);
    }

    #[test]
    fn test_latency_percentile() {
        let mut metrics = BatchMetrics::new();
        metrics.latencies = vec![100, 200, 300, 400, 500];

        assert_eq!(metrics.latency_percentile(50.0), Some(300));
        assert_eq!(metrics.latency_percentile(95.0), Some(500));
        assert_eq!(metrics.avg_latency(), 300.0);
    }

    #[test]
    fn test_benchmark_result() {
        let efficiency = BenchmarkResult::calculate_efficiency(8.0, 10);
        assert_eq!(efficiency, 0.8);
    }
}
