//! Parallel Agents Example
//!
//! Demonstrates concurrent agent execution with performance benchmarking,
//! comparing parallel vs sequential execution, and result aggregation.

use anyhow::Result;
use parallel_agents::{
    AgentPool, AggregatedResult, ExecutionMetrics, ParallelAgentExecutor, ParallelConfig,
};
use std::time::{Duration, Instant};
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

/// Example questions for agent testing
const EXAMPLE_QUESTIONS: &[&str] = &[
    "What is the capital of France?",
    "What is 2 + 2?",
    "Who wrote Romeo and Juliet?",
    "What is the speed of light?",
    "What is the largest planet in our solar system?",
    "What year did World War II end?",
    "What is the chemical symbol for gold?",
    "How many continents are there?",
];

/// Run parallel execution benchmark
async fn benchmark_parallel_execution(
    executor: &ParallelAgentExecutor,
    questions: Vec<String>,
) -> Result<(Vec<parallel_agents::AgentResult>, Duration)> {
    info!("Running parallel execution benchmark...");

    let start = Instant::now();
    let results = executor.execute_parallel(questions).await?;
    let duration = start.elapsed();

    info!(
        "Parallel execution completed in {:?} ({} results)",
        duration,
        results.len()
    );

    Ok((results, duration))
}

/// Run sequential execution benchmark
async fn benchmark_sequential_execution(
    questions: Vec<String>,
) -> Result<(Vec<String>, Duration)> {
    info!("Running sequential execution benchmark...");

    let start = Instant::now();
    let mut results = Vec::new();

    for (idx, question) in questions.iter().enumerate() {
        let answer = execute_single_sequential(question, idx).await?;
        results.push(answer);
    }

    let duration = start.elapsed();

    info!(
        "Sequential execution completed in {:?} ({} results)",
        duration,
        results.len()
    );

    Ok((results, duration))
}

/// Execute a single agent sequentially
async fn execute_single_sequential(question: &str, idx: usize) -> Result<String> {
    // Simulate agent execution
    tokio::time::sleep(Duration::from_millis(100)).await;
    Ok(format!("Sequential answer {} for: {}", idx, question))
}

/// Display performance comparison
fn display_performance_comparison(
    parallel_duration: Duration,
    sequential_duration: Duration,
    num_questions: usize,
) {
    println!("\n{}", "=".repeat(80));
    println!("PERFORMANCE COMPARISON");
    println!("{}", "=".repeat(80));

    let speedup = sequential_duration.as_secs_f64() / parallel_duration.as_secs_f64();

    println!("\nExecution Times:");
    println!("  Sequential: {:?}", sequential_duration);
    println!("  Parallel:   {:?}", parallel_duration);
    println!("  Speedup:    {:.2}x", speedup);

    println!("\nThroughput:");
    println!(
        "  Sequential: {:.2} req/sec",
        num_questions as f64 / sequential_duration.as_secs_f64()
    );
    println!(
        "  Parallel:   {:.2} req/sec",
        num_questions as f64 / parallel_duration.as_secs_f64()
    );

    println!("\nEfficiency:");
    println!(
        "  Time saved: {:?} ({:.1}%)",
        sequential_duration - parallel_duration,
        (1.0 - parallel_duration.as_secs_f64() / sequential_duration.as_secs_f64()) * 100.0
    );

    println!("{}\n", "=".repeat(80));
}

/// Display execution metrics
fn display_metrics(metrics: &ExecutionMetrics) {
    println!("\n{}", "-".repeat(80));
    println!("EXECUTION METRICS");
    println!("{}", "-".repeat(80));

    println!("\nResults:");
    println!("  Successful: {}", metrics.successful_count);
    println!("  Failed:     {}", metrics.failed_count);
    println!(
        "  Total:      {}",
        metrics.successful_count + metrics.failed_count
    );

    println!("\nTiming:");
    println!("  Total:      {:?}", metrics.total_duration);
    println!("  Average:    {:?}", metrics.avg_duration);
    println!("  Min:        {:?}", metrics.min_duration);
    println!("  Max:        {:?}", metrics.max_duration);

    println!("\nPerformance:");
    println!("  Throughput: {:.2} req/sec", metrics.throughput);

    println!("{}\n", "-".repeat(80));
}

/// Display aggregated results with consensus
fn display_aggregated_results(result: &AggregatedResult) {
    println!("\n{}", "=".repeat(80));
    println!("AGGREGATED RESULTS WITH CONSENSUS");
    println!("{}", "=".repeat(80));

    println!("\nConsensus:");
    match &result.consensus {
        Some(answer) => {
            println!("  Answer:     {}", answer);
            println!("  Confidence: {:.1}%", result.confidence * 100.0);
        }
        None => {
            println!("  No consensus reached");
            println!("  Best confidence: {:.1}%", result.confidence * 100.0);
        }
    }

    println!("\nIndividual Results:");
    for (idx, agent_result) in result.results.iter().enumerate() {
        if agent_result.success {
            println!(
                "  Agent {}: {} (took {:?})",
                idx, agent_result.answer, agent_result.duration
            );
        } else {
            println!(
                "  Agent {}: FAILED - {}",
                idx,
                agent_result.error.as_ref().unwrap_or(&"Unknown error".to_string())
            );
        }
    }

    display_metrics(&result.metrics);

    println!("{}\n", "=".repeat(80));
}

/// Example 1: Basic parallel execution
async fn example_basic_parallel() -> Result<()> {
    println!("\n\n### EXAMPLE 1: Basic Parallel Execution ###\n");

    let config = ParallelConfig {
        max_concurrency: 4,
        agent_timeout: Duration::from_secs(30),
        deduplicate_results: false,
        consensus_threshold: 0.6,
    };

    let executor = ParallelAgentExecutor::new(config);

    let questions: Vec<String> = EXAMPLE_QUESTIONS[..4]
        .iter()
        .map(|s| s.to_string())
        .collect();

    println!("Questions to process:");
    for (idx, q) in questions.iter().enumerate() {
        println!("  {}. {}", idx + 1, q);
    }

    let (results, duration) = benchmark_parallel_execution(&executor, questions).await?;

    println!("\nResults:");
    for (idx, result) in results.iter().enumerate() {
        if result.success {
            println!(
                "  {}. {} (took {:?})",
                idx + 1,
                result.answer,
                result.duration
            );
        } else {
            println!(
                "  {}. FAILED: {}",
                idx + 1,
                result.error.as_ref().unwrap_or(&"Unknown".to_string())
            );
        }
    }

    println!("\nTotal execution time: {:?}", duration);

    Ok(())
}

/// Example 2: Parallel vs Sequential comparison
async fn example_parallel_vs_sequential() -> Result<()> {
    println!("\n\n### EXAMPLE 2: Parallel vs Sequential Comparison ###\n");

    let config = ParallelConfig {
        max_concurrency: 8,
        ..Default::default()
    };

    let executor = ParallelAgentExecutor::new(config);

    let questions: Vec<String> = EXAMPLE_QUESTIONS.iter().map(|s| s.to_string()).collect();

    println!("Processing {} questions...\n", questions.len());

    // Run parallel
    let (parallel_results, parallel_duration) =
        benchmark_parallel_execution(&executor, questions.clone()).await?;

    // Run sequential
    let (sequential_results, sequential_duration) =
        benchmark_sequential_execution(questions.clone()).await?;

    display_performance_comparison(parallel_duration, sequential_duration, questions.len());

    println!("Sample Results Comparison:");
    println!("\nParallel Results (first 3):");
    for (idx, result) in parallel_results.iter().take(3).enumerate() {
        println!("  {}. {}", idx + 1, result.answer);
    }

    println!("\nSequential Results (first 3):");
    for (idx, result) in sequential_results.iter().take(3).enumerate() {
        println!("  {}. {}", idx + 1, result);
    }

    Ok(())
}

/// Example 3: Consensus voting with multiple agents
async fn example_consensus_voting() -> Result<()> {
    println!("\n\n### EXAMPLE 3: Consensus Voting ###\n");

    let config = ParallelConfig {
        max_concurrency: 5,
        consensus_threshold: 0.6,
        ..Default::default()
    };

    let executor = ParallelAgentExecutor::new(config);

    let question = "What is the capital of France?".to_string();
    let num_agents = 5;

    println!("Question: {}", question);
    println!("Number of agents: {}\n", num_agents);

    let result = executor
        .execute_with_consensus(question, num_agents)
        .await?;

    display_aggregated_results(&result);

    Ok(())
}

/// Example 4: Agent pool usage
async fn example_agent_pool() -> Result<()> {
    println!("\n\n### EXAMPLE 4: Agent Pool ###\n");

    let config = ParallelConfig {
        max_concurrency: 6,
        ..Default::default()
    };

    let pool = AgentPool::new(6, config);

    let questions: Vec<String> = EXAMPLE_QUESTIONS.iter().map(|s| s.to_string()).collect();

    println!("Agent pool size: {}", pool.pool_size());
    println!("Processing {} questions...\n", questions.len());

    let start = Instant::now();
    let results = pool.execute_batch(questions).await?;
    let duration = start.elapsed();

    println!("Results:");
    for (idx, result) in results.iter().enumerate() {
        if result.success {
            println!("  {}. {} (took {:?})", idx + 1, result.answer, result.duration);
        } else {
            println!(
                "  {}. FAILED: {}",
                idx + 1,
                result.error.as_ref().unwrap_or(&"Unknown".to_string())
            );
        }
    }

    println!("\nTotal execution time: {:?}", duration);
    println!(
        "Average time per question: {:?}",
        duration / results.len() as u32
    );

    Ok(())
}

/// Example 5: Throughput benchmark
async fn example_throughput_benchmark() -> Result<()> {
    println!("\n\n### EXAMPLE 5: Throughput Benchmark ###\n");

    let configs = vec![
        ("Low Concurrency (2)", 2),
        ("Medium Concurrency (4)", 4),
        ("High Concurrency (8)", 8),
        ("Very High Concurrency (16)", 16),
    ];

    let questions: Vec<String> = EXAMPLE_QUESTIONS
        .iter()
        .cycle()
        .take(32)
        .map(|s| s.to_string())
        .collect();

    println!("Testing {} questions with different concurrency levels\n", questions.len());

    println!("{:<30} {:>15} {:>15}", "Configuration", "Duration", "Throughput");
    println!("{}", "-".repeat(65));

    for (name, concurrency) in configs {
        let config = ParallelConfig {
            max_concurrency: concurrency,
            ..Default::default()
        };

        let executor = ParallelAgentExecutor::new(config);
        let start = Instant::now();
        let results = executor.execute_parallel(questions.clone()).await?;
        let duration = start.elapsed();

        let throughput = results.len() as f64 / duration.as_secs_f64();

        println!(
            "{:<30} {:>15.2?} {:>12.2} req/s",
            name, duration, throughput
        );
    }

    println!("{}\n", "-".repeat(65));

    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();

    tracing::subscriber::set_global_default(subscriber).expect("Failed to set subscriber");

    println!("\n");
    println!("{}", "=".repeat(80));
    println!("PARALLEL AGENTS EXECUTION EXAMPLES");
    println!("{}", "=".repeat(80));

    // Run all examples
    example_basic_parallel().await?;
    example_parallel_vs_sequential().await?;
    example_consensus_voting().await?;
    example_agent_pool().await?;
    example_throughput_benchmark().await?;

    println!("\n");
    println!("{}", "=".repeat(80));
    println!("ALL EXAMPLES COMPLETED");
    println!("{}", "=".repeat(80));
    println!("\n");

    Ok(())
}
