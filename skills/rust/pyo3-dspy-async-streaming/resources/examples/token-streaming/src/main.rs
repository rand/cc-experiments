//! Token Streaming Examples
//!
//! Demonstrates various patterns for streaming LLM responses from DSPy:
//! - Simple token-by-token streaming
//! - Multiple concurrent streams
//! - Stream aggregation from multiple sources
//! - Error recovery with automatic retries
//! - Progress indicators during streaming

use anyhow::{Context, Result};
use futures::StreamExt;
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::io::Write;
use std::time::{Duration, Instant};
use token_streaming::{
    aggregate_streams, collect_stream, init_dspy_streaming, ConcurrentStreamProcessor,
    DSpyStream, SafeDSpyStream, StreamConfig, StreamEvent,
};
use tracing::{info, warn};

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter("token_streaming=info")
        .init();

    // Initialize Python interpreter
    pyo3::prepare_freethreaded_python();

    // Initialize DSPy with streaming configuration
    info!("Initializing DSPy with streaming support");
    init_streaming_config()?;

    // Run examples
    println!("\n=== Token Streaming Examples ===\n");

    run_simple_streaming().await?;
    println!("\n{}\n", "=".repeat(60));

    run_safe_streaming().await?;
    println!("\n{}\n", "=".repeat(60));

    run_concurrent_streaming().await?;
    println!("\n{}\n", "=".repeat(60));

    run_stream_aggregation().await?;
    println!("\n{}\n", "=".repeat(60));

    run_error_recovery().await?;
    println!("\n{}\n", "=".repeat(60));

    run_progress_indicators().await?;

    println!("\n=== All Examples Complete ===\n");

    Ok(())
}

/// Example 1: Simple unbounded streaming
async fn run_simple_streaming() -> Result<()> {
    println!("Example 1: Simple Unbounded Streaming");
    println!("{}", "-".repeat(60));

    let question = "Explain async programming in Rust in one sentence.".to_string();
    println!("Question: {}\n", question);

    let start = Instant::now();

    print!("Answer: ");
    std::io::stdout().flush()?;

    let stream = DSpyStream::new(question)?;
    let mut stream = stream.into_stream();

    let mut token_count = 0;
    while let Some(token) = stream.next().await {
        print!("{}", token);
        std::io::stdout().flush()?;
        token_count += 1;
    }

    let duration = start.elapsed();
    println!("\n");
    println!("Duration: {:.3}s", duration.as_secs_f64());
    println!("Tokens: {}", token_count);

    Ok(())
}

/// Example 2: Safe streaming with lifecycle events
async fn run_safe_streaming() -> Result<()> {
    println!("Example 2: Safe Streaming with Events");
    println!("{}", "-".repeat(60));

    let question = "What makes Rust memory-safe?".to_string();
    println!("Question: {}\n", question);

    let start = Instant::now();

    print!("Answer: ");
    std::io::stdout().flush()?;

    let stream = SafeDSpyStream::new(question, 100)?;
    let mut stream = stream.into_stream();

    let mut token_count = 0;
    let mut had_error = false;

    while let Some(event) = stream.next().await {
        match event {
            StreamEvent::Token(token) => {
                print!("{}", token);
                std::io::stdout().flush()?;
                token_count += 1;
            }
            StreamEvent::Done => {
                println!("\n\n[Stream completed successfully]");
            }
            StreamEvent::Error(e) => {
                eprintln!("\n\n[Stream error: {}]", e);
                had_error = true;
            }
        }
    }

    let duration = start.elapsed();
    println!("Duration: {:.3}s", duration.as_secs_f64());
    println!("Tokens: {}", token_count);
    println!("Status: {}", if had_error { "ERROR" } else { "SUCCESS" });

    Ok(())
}

/// Example 3: Multiple concurrent streams
async fn run_concurrent_streaming() -> Result<()> {
    println!("Example 3: Concurrent Streaming");
    println!("{}", "-".repeat(60));

    let questions = vec![
        "What is Rust?".to_string(),
        "What is Python?".to_string(),
        "What is DSPy?".to_string(),
    ];

    println!("Processing {} questions concurrently...\n", questions.len());

    let start = Instant::now();

    // Process all questions concurrently
    let handles: Vec<_> = questions
        .into_iter()
        .enumerate()
        .map(|(idx, question)| {
            tokio::spawn(async move {
                let stream_start = Instant::now();
                let stream = SafeDSpyStream::new(question.clone(), 100)?;
                let result = collect_stream(stream).await?;
                let duration = stream_start.elapsed();

                Ok::<_, anyhow::Error>((idx, question, result, duration))
            })
        })
        .collect();

    // Collect results
    let mut results = Vec::new();
    for handle in handles {
        match handle.await? {
            Ok(result) => results.push(result),
            Err(e) => warn!("Stream failed: {}", e),
        }
    }

    let total_duration = start.elapsed();

    // Display results
    for (idx, question, answer, duration) in results {
        println!("Q{}: {}", idx + 1, question);
        println!("A{}: {}", idx + 1, answer.chars().take(100).collect::<String>());
        if answer.len() > 100 {
            println!("   ... ({} more chars)", answer.len() - 100);
        }
        println!("Duration: {:.3}s\n", duration.as_secs_f64());
    }

    println!("Total duration: {:.3}s (concurrent)", total_duration.as_secs_f64());

    Ok(())
}

/// Example 4: Stream aggregation
async fn run_stream_aggregation() -> Result<()> {
    println!("Example 4: Stream Aggregation");
    println!("{}", "-".repeat(60));

    let questions = vec![
        "Name one benefit of Rust.".to_string(),
        "Name one benefit of async.".to_string(),
        "Name one benefit of DSPy.".to_string(),
    ];

    println!("Aggregating {} streams...\n", questions.len());

    let start = Instant::now();

    // Create all streams
    let streams: Vec<_> = questions
        .iter()
        .map(|q| SafeDSpyStream::new(q.clone(), 100))
        .collect::<Result<_, _>>()?;

    // Aggregate into single stream
    let mut merged = aggregate_streams(streams);

    let mut responses: Vec<String> = vec![String::new(); questions.len()];
    let mut completed = vec![false; questions.len()];

    // Process merged stream
    while let Some((idx, event)) = merged.next().await {
        match event {
            StreamEvent::Token(token) => {
                print!("[Stream {}] {}", idx + 1, token);
                std::io::stdout().flush()?;
                responses[idx].push_str(&token);
            }
            StreamEvent::Done => {
                println!("\n[Stream {}] Complete\n", idx + 1);
                completed[idx] = true;
            }
            StreamEvent::Error(e) => {
                eprintln!("\n[Stream {}] Error: {}\n", idx + 1, e);
                completed[idx] = true;
            }
        }
    }

    let duration = start.elapsed();

    // Summary
    println!("Aggregation complete:");
    println!("- Total responses: {}", responses.len());
    println!("- Successful: {}", completed.iter().filter(|&&c| c).count());
    println!("- Duration: {:.3}s", duration.as_secs_f64());

    Ok(())
}

/// Example 5: Error recovery with retries
async fn run_error_recovery() -> Result<()> {
    println!("Example 5: Error Recovery with Retries");
    println!("{}", "-".repeat(60));

    let question = "What is error handling in async Rust?".to_string();
    println!("Question: {}\n", question);

    let start = Instant::now();

    print!("Answer (with retry): ");
    std::io::stdout().flush()?;

    // Create stream with retry configuration
    let stream = SafeDSpyStream::with_retry(
        question,
        100,                        // buffer size
        3,                          // max retries
        Duration::from_secs(2),     // base delay
    )?;

    let mut stream = stream.into_stream();
    let mut token_count = 0;
    let mut had_error = false;

    while let Some(event) = stream.next().await {
        match event {
            StreamEvent::Token(token) => {
                print!("{}", token);
                std::io::stdout().flush()?;
                token_count += 1;
            }
            StreamEvent::Done => {
                println!("\n\n[Stream completed]");
            }
            StreamEvent::Error(e) => {
                eprintln!("\n\n[Stream failed after retries: {}]", e);
                had_error = true;
            }
        }
    }

    let duration = start.elapsed();
    println!("Duration: {:.3}s", duration.as_secs_f64());
    println!("Tokens: {}", token_count);
    println!("Retry enabled: Yes (max 3 attempts)");
    println!("Status: {}", if had_error { "FAILED" } else { "SUCCESS" });

    Ok(())
}

/// Example 6: Progress indicators
async fn run_progress_indicators() -> Result<()> {
    println!("Example 6: Progress Indicators");
    println!("{}", "-".repeat(60));

    let questions = vec![
        "Explain ownership in Rust.".to_string(),
        "Explain borrowing in Rust.".to_string(),
        "Explain lifetimes in Rust.".to_string(),
    ];

    println!("Processing {} questions with progress bars...\n", questions.len());

    let multi_progress = MultiProgress::new();
    let main_pb = multi_progress.add(ProgressBar::new(questions.len() as u64));

    main_pb.set_style(
        ProgressStyle::default_bar()
            .template("[{elapsed_precise}] {bar:40.cyan/blue} {pos}/{len} {msg}")
            .unwrap()
            .progress_chars("=>-"),
    );

    main_pb.set_message("Processing questions");

    let start = Instant::now();

    // Process each question with individual progress bar
    let mut handles = Vec::new();

    for (idx, question) in questions.into_iter().enumerate() {
        let pb = multi_progress.add(ProgressBar::new_spinner());
        pb.set_style(
            ProgressStyle::default_spinner()
                .template("[{elapsed_precise}] {spinner:.green} Q{}: {msg}")
                .unwrap(),
        );
        pb.set_message(format!("{}", question.chars().take(40).collect::<String>()));

        let handle = tokio::spawn(async move {
            let stream = SafeDSpyStream::new(question, 100)?;
            let mut stream = stream.into_stream();

            let mut response = String::new();
            let mut token_count = 0;

            while let Some(event) = stream.next().await {
                match event {
                    StreamEvent::Token(token) => {
                        response.push_str(&token);
                        token_count += 1;

                        if token_count % 5 == 0 {
                            pb.set_message(format!(
                                "{} tokens",
                                token_count
                            ));
                        }
                    }
                    StreamEvent::Done => {
                        pb.finish_with_message(format!("Complete ({} tokens)", token_count));
                        break;
                    }
                    StreamEvent::Error(e) => {
                        pb.finish_with_message(format!("Error: {}", e));
                        return Err(anyhow::anyhow!("Stream error: {}", e));
                    }
                }
            }

            Ok::<_, anyhow::Error>((idx, response))
        });

        handles.push(handle);
    }

    // Wait for completion
    let mut completed = 0;
    for handle in handles {
        match handle.await? {
            Ok((idx, response)) => {
                info!("Question {} completed: {} chars", idx + 1, response.len());
                completed += 1;
                main_pb.inc(1);
            }
            Err(e) => {
                warn!("Question failed: {}", e);
                main_pb.inc(1);
            }
        }
    }

    let duration = start.elapsed();

    main_pb.finish_with_message("All questions processed");

    println!("\nSummary:");
    println!("- Completed: {}/{}", completed, questions.len());
    println!("- Duration: {:.3}s", duration.as_secs_f64());

    Ok(())
}

/// Initialize streaming configuration for DSPy
fn init_streaming_config() -> Result<()> {
    // Try to detect LLM provider from environment
    let provider = std::env::var("LM_PROVIDER").unwrap_or_else(|_| "openai".to_string());
    let model = std::env::var("LM_MODEL").unwrap_or_else(|_| {
        match provider.as_str() {
            "openai" => "gpt-3.5-turbo",
            "anthropic" => "claude-2",
            _ => "gpt-3.5-turbo",
        }
        .to_string()
    });

    info!("Configuring DSPy: provider={}, model={}", provider, model);

    init_dspy_streaming(&model, &provider).context("Failed to initialize DSPy streaming")?;

    Ok(())
}

/// Batch processing example using ConcurrentStreamProcessor
#[allow(dead_code)]
async fn example_batch_processing() -> Result<()> {
    let questions = vec![
        "What is Rust?".to_string(),
        "What is Python?".to_string(),
        "What is DSPy?".to_string(),
        "What is async?".to_string(),
        "What is streaming?".to_string(),
    ];

    let config = StreamConfig {
        buffer_size: 100,
        max_retries: 2,
        retry_delay: Duration::from_secs(1),
        timeout: Some(Duration::from_secs(30)),
    };

    let processor = ConcurrentStreamProcessor::new(3, config); // Max 3 concurrent

    println!("Processing {} questions with rate limiting...", questions.len());

    let start = Instant::now();
    let results = processor.process_batch(questions.clone()).await;
    let duration = start.elapsed();

    // Display results
    for (idx, (question, result)) in questions.iter().zip(results.iter()).enumerate() {
        println!("\nQ{}: {}", idx + 1, question);

        match result {
            Ok(answer) => {
                let preview = if answer.len() > 100 {
                    format!("{}...", &answer[..100])
                } else {
                    answer.clone()
                };
                println!("A{}: {}", idx + 1, preview);
            }
            Err(e) => {
                println!("A{}: [ERROR: {}]", idx + 1, e);
            }
        }
    }

    println!("\n\nBatch processing complete:");
    println!("- Total questions: {}", questions.len());
    println!("- Successful: {}", results.iter().filter(|r| r.is_ok()).count());
    println!("- Failed: {}", results.iter().filter(|r| r.is_err()).count());
    println!("- Duration: {:.3}s", duration.as_secs_f64());
    println!("- Average: {:.3}s per question", duration.as_secs_f64() / questions.len() as f64);

    Ok(())
}
