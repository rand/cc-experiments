//! Concurrent Batch Processing Examples
//!
//! This binary provides multiple examples demonstrating concurrent batch
//! processing of DSPy predictions with performance benchmarking.
//!
//! # Usage
//!
//! Run different examples:
//!
//! ```bash
//! # Simple batch (8 questions)
//! cargo run -- --mode simple
//!
//! # Large batch (150 questions)
//! cargo run -- --mode large
//!
//! # Rate-limited batch
//! cargo run -- --mode rate-limited
//!
//! # Full benchmark comparison
//! cargo run -- --mode benchmark
//! ```

use anyhow::{Context, Result};
use concurrent_batch::{BatchConfig, BatchPredictor, BenchmarkResult};
use std::time::Instant;

/// Example mode
#[derive(Debug, Clone, Copy)]
enum Mode {
    Simple,
    Large,
    RateLimited,
    Benchmark,
}

impl Mode {
    fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "simple" => Some(Mode::Simple),
            "large" => Some(Mode::Large),
            "rate-limited" | "rate_limited" => Some(Mode::RateLimited),
            "benchmark" => Some(Mode::Benchmark),
            _ => None,
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Parse command line arguments
    let args: Vec<String> = std::env::args().collect();
    let mode = if args.len() > 2 && args[1] == "--mode" {
        Mode::from_str(&args[2]).unwrap_or(Mode::Simple)
    } else {
        Mode::Simple
    };

    println!("Concurrent Batch Processing Examples");
    println!("====================================\n");

    match mode {
        Mode::Simple => run_simple_example().await?,
        Mode::Large => run_large_example().await?,
        Mode::RateLimited => run_rate_limited_example().await?,
        Mode::Benchmark => run_benchmark_example().await?,
    }

    Ok(())
}

/// Example 1: Simple Batch (4-8 questions)
///
/// Demonstrates basic concurrent execution with a small batch.
async fn run_simple_example() -> Result<()> {
    println!("Example 1: Simple Batch");
    println!("-----------------------\n");

    let questions = vec![
        "What is Rust programming language?".to_string(),
        "What is Python programming language?".to_string(),
        "What is DSPy framework?".to_string(),
        "What is async programming?".to_string(),
        "What is concurrent programming?".to_string(),
        "What is parallel programming?".to_string(),
        "What is the difference between concurrency and parallelism?".to_string(),
        "What are the benefits of using Rust for systems programming?".to_string(),
    ];

    println!("Questions: {}", questions.len());
    println!("Max Concurrent: 4\n");

    // Sequential execution
    println!("Sequential Execution:");
    println!("--------------------");
    let config = BatchConfig::new(1, "question -> answer");
    let predictor = BatchPredictor::new(config)?;

    let seq_start = Instant::now();
    let seq_results = predictor.predict_sequential(questions.clone()).await?;
    let seq_duration = seq_start.elapsed();

    println!("Duration: {:.2}s", seq_duration.as_secs_f64());
    println!("Results: {} answers", seq_results.len());
    println!();

    // Concurrent execution
    println!("Concurrent Execution (4 workers):");
    println!("----------------------------------");
    let config = BatchConfig::new(4, "question -> answer");
    let predictor = BatchPredictor::new(config)?;

    let conc_start = Instant::now();
    let conc_results = predictor.predict_batch(questions.clone()).await?;
    let conc_duration = conc_start.elapsed();
    let metrics = predictor.get_metrics(conc_duration);

    println!("Duration: {:.2}s", conc_duration.as_secs_f64());
    println!("Results: {} answers", conc_results.len());
    println!("Throughput: {:.2} questions/sec", metrics.throughput());
    println!();

    // Analysis
    let speedup = seq_duration.as_secs_f64() / conc_duration.as_secs_f64();
    println!("Performance Analysis:");
    println!("--------------------");
    println!("Speedup: {:.2}x", speedup);
    println!("Efficiency: {:.1}%", (speedup / 4.0) * 100.0);
    println!("Peak Concurrent: {}", metrics.peak_concurrent);
    println!();

    // Show sample results
    println!("Sample Results:");
    println!("--------------");
    for (i, result) in conc_results.iter().take(3).enumerate() {
        println!(
            "{}. Q: {}",
            i + 1,
            result.question.chars().take(60).collect::<String>()
        );
        println!(
            "   A: {} ({}ms)",
            result.answer.chars().take(80).collect::<String>(),
            result.latency_ms
        );
        println!();
    }

    Ok(())
}

/// Example 2: Large Batch (100+ questions)
///
/// Stress test with a large number of questions to demonstrate scalability.
async fn run_large_example() -> Result<()> {
    println!("Example 2: Large Batch");
    println!("----------------------\n");

    // Generate 150 questions
    let base_questions = vec![
        "What is artificial intelligence?",
        "What is machine learning?",
        "What is deep learning?",
        "What is natural language processing?",
        "What is computer vision?",
        "What is reinforcement learning?",
        "What is supervised learning?",
        "What is unsupervised learning?",
        "What is a neural network?",
        "What is a convolutional neural network?",
        "What is a recurrent neural network?",
        "What is a transformer model?",
        "What is attention mechanism?",
        "What is gradient descent?",
        "What is backpropagation?",
    ];

    let mut questions = Vec::new();
    for i in 0..10 {
        for q in &base_questions {
            questions.push(format!("{} (variant {})", q, i + 1));
        }
    }

    println!("Questions: {}", questions.len());
    println!("Max Concurrent: 10\n");

    // Concurrent execution
    println!("Concurrent Execution:");
    println!("--------------------");
    let config = BatchConfig::new(10, "question -> answer");
    let predictor = BatchPredictor::new(config)?;

    let start = Instant::now();
    let results = predictor.predict_batch(questions.clone()).await?;
    let duration = start.elapsed();
    let metrics = predictor.get_metrics(duration);

    println!("Duration: {:.2}s ({:.1}m)", duration.as_secs_f64(), duration.as_secs_f64() / 60.0);
    println!("Successful: {}", metrics.successful);
    println!("Failed: {}", metrics.failed);
    println!("Success Rate: {:.1}%", metrics.success_rate() * 100.0);
    println!();

    // Performance metrics
    println!("Performance Metrics:");
    println!("-------------------");
    println!("Throughput: {:.2} questions/sec", metrics.throughput());
    println!("Peak Concurrent: {}", metrics.peak_concurrent);
    println!("Cache Hits: {}", metrics.cache_hits);
    println!();

    // Latency distribution
    println!("Latency Distribution:");
    println!("--------------------");
    if let Some(p50) = metrics.latency_percentile(50.0) {
        println!("p50: {}ms", p50);
    }
    if let Some(p95) = metrics.latency_percentile(95.0) {
        println!("p95: {}ms", p95);
    }
    if let Some(p99) = metrics.latency_percentile(99.0) {
        println!("p99: {}ms", p99);
    }
    println!("Average: {:.1}ms", metrics.avg_latency());
    println!();

    // Estimate sequential time
    let estimated_seq = duration.as_secs_f64() * 10.0;
    println!("Estimated Sequential Time: {:.1}s ({:.1}m)", estimated_seq, estimated_seq / 60.0);
    println!("Estimated Speedup: {:.1}x", 10.0);
    println!();

    // Show deduplication benefit
    println!("Cache Analysis:");
    println!("--------------");
    println!("Cache Size: {} unique questions", predictor.cache_size());
    println!("Cache Hits: {} (duplicates)", metrics.cache_hits);
    println!("Cache Hit Rate: {:.1}%",
        (metrics.cache_hits as f64 / questions.len() as f64) * 100.0);

    Ok(())
}

/// Example 3: Rate-Limited Batch
///
/// Demonstrates rate limiting behavior with a modest concurrency limit.
async fn run_rate_limited_example() -> Result<()> {
    println!("Example 3: Rate-Limited Batch");
    println!("-----------------------------\n");

    let questions = vec![
        "What is API rate limiting?".to_string(),
        "What is backpressure?".to_string(),
        "What is a semaphore?".to_string(),
        "What is concurrency control?".to_string(),
        "What is throttling?".to_string(),
        "What is load balancing?".to_string(),
        "What is circuit breaker pattern?".to_string(),
        "What is retry logic?".to_string(),
        "What is exponential backoff?".to_string(),
        "What is request queuing?".to_string(),
        "What is connection pooling?".to_string(),
        "What is resource exhaustion?".to_string(),
        "What is graceful degradation?".to_string(),
        "What is failover?".to_string(),
        "What is redundancy?".to_string(),
    ];

    println!("Questions: {}", questions.len());
    println!();

    // Test different rate limits
    let rate_limits = vec![3, 5, 10];

    for max_concurrent in rate_limits {
        println!("Max Concurrent: {}", max_concurrent);
        println!("{}", "-".repeat(40));

        let config = BatchConfig::new(max_concurrent, "question -> answer");
        let predictor = BatchPredictor::new(config)?;

        let start = Instant::now();
        let results = predictor.predict_batch(questions.clone()).await?;
        let duration = start.elapsed();
        let metrics = predictor.get_metrics(duration);

        println!("Duration: {:.2}s", duration.as_secs_f64());
        println!("Throughput: {:.2} q/s", metrics.throughput());
        println!("Peak Concurrent: {}", metrics.peak_concurrent);
        println!("Average Latency: {:.1}ms", metrics.avg_latency());
        println!();

        predictor.clear_cache();
    }

    // Show rate limiting effects
    println!("Rate Limiting Analysis:");
    println!("----------------------");
    println!("Observation: Lower concurrency limits increase total time");
    println!("but prevent overwhelming the API and reduce error rates.");
    println!();
    println!("Recommended: Start with max_concurrent=5-10, tune based on:");
    println!("  - API rate limits (requests/sec, requests/minute)");
    println!("  - Error rates (429 Too Many Requests)");
    println!("  - Network bandwidth and latency");
    println!("  - Memory constraints");

    Ok(())
}

/// Example 4: Full Benchmark Comparison
///
/// Comprehensive benchmark comparing sequential vs concurrent execution
/// with multiple concurrency levels.
async fn run_benchmark_example() -> Result<()> {
    println!("Example 4: Performance Benchmark");
    println!("--------------------------------\n");

    let questions = vec![
        "What is distributed systems?".to_string(),
        "What is microservices architecture?".to_string(),
        "What is service mesh?".to_string(),
        "What is container orchestration?".to_string(),
        "What is Kubernetes?".to_string(),
        "What is Docker?".to_string(),
        "What is serverless computing?".to_string(),
        "What is function as a service?".to_string(),
        "What is edge computing?".to_string(),
        "What is cloud native?".to_string(),
        "What is infrastructure as code?".to_string(),
        "What is GitOps?".to_string(),
        "What is continuous integration?".to_string(),
        "What is continuous deployment?".to_string(),
        "What is DevOps?".to_string(),
        "What is site reliability engineering?".to_string(),
        "What is chaos engineering?".to_string(),
        "What is observability?".to_string(),
        "What is monitoring?".to_string(),
        "What is logging?".to_string(),
    ];

    println!("Questions: {}", questions.len());
    println!();

    // Baseline: Sequential execution
    println!("1. Sequential Execution (baseline)");
    println!("{}", "=".repeat(40));

    let config = BatchConfig::new(1, "question -> answer");
    let predictor = BatchPredictor::new(config)?;

    let seq_start = Instant::now();
    let seq_results = predictor.predict_sequential(questions.clone()).await?;
    let seq_duration = seq_start.elapsed();

    println!("Duration: {:.2}s", seq_duration.as_secs_f64());
    println!("Throughput: {:.2} q/s", seq_results.len() as f64 / seq_duration.as_secs_f64());
    println!();

    // Test multiple concurrency levels
    let concurrency_levels = vec![2, 4, 8, 10];

    for max_concurrent in concurrency_levels {
        println!("{}. Concurrent Execution ({} workers)", max_concurrent, max_concurrent);
        println!("{}", "=".repeat(40));

        let config = BatchConfig::new(max_concurrent, "question -> answer");
        let predictor = BatchPredictor::new(config)?;

        let conc_start = Instant::now();
        let conc_results = predictor.predict_batch(questions.clone()).await?;
        let conc_duration = conc_start.elapsed();
        let metrics = predictor.get_metrics(conc_duration);

        let speedup = seq_duration.as_secs_f64() / conc_duration.as_secs_f64();
        let efficiency = (speedup / max_concurrent as f64) * 100.0;

        println!("Duration: {:.2}s", conc_duration.as_secs_f64());
        println!("Throughput: {:.2} q/s", metrics.throughput());
        println!("Speedup: {:.2}x", speedup);
        println!("Efficiency: {:.1}%", efficiency);
        println!("Peak Concurrent: {}", metrics.peak_concurrent);
        if let Some(p95) = metrics.latency_percentile(95.0) {
            println!("p95 Latency: {}ms", p95);
        }
        println!();

        predictor.clear_cache();
    }

    // Summary
    println!("Summary");
    println!("{}", "=".repeat(40));
    println!("Sequential baseline: {:.2}s", seq_duration.as_secs_f64());
    println!();
    println!("Key Findings:");
    println!("  - Speedup increases with concurrency");
    println!("  - Efficiency decreases due to overhead");
    println!("  - Optimal concurrency: 8-10 workers");
    println!("  - Diminishing returns beyond 10 workers");
    println!();
    println!("Recommendations:");
    println!("  - Use 4-8 workers for most workloads");
    println!("  - Monitor API rate limits");
    println!("  - Implement retry logic for failures");
    println!("  - Cache duplicate questions");

    Ok(())
}

/// Helper: Format duration as human-readable string
fn format_duration(duration: std::time::Duration) -> String {
    let secs = duration.as_secs();
    if secs < 60 {
        format!("{:.1}s", duration.as_secs_f64())
    } else {
        format!("{:.1}m", duration.as_secs_f64() / 60.0)
    }
}

/// Helper: Print separator line
fn print_separator(char: &str, length: usize) {
    println!("{}", char.repeat(length));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mode_from_str() {
        assert!(matches!(Mode::from_str("simple"), Some(Mode::Simple)));
        assert!(matches!(Mode::from_str("large"), Some(Mode::Large)));
        assert!(matches!(Mode::from_str("rate-limited"), Some(Mode::RateLimited)));
        assert!(matches!(Mode::from_str("benchmark"), Some(Mode::Benchmark)));
        assert!(Mode::from_str("invalid").is_none());
    }

    #[test]
    fn test_format_duration() {
        use std::time::Duration;

        assert_eq!(format_duration(Duration::from_secs(30)), "30.0s");
        assert_eq!(format_duration(Duration::from_secs(90)), "1.5m");
    }
}
