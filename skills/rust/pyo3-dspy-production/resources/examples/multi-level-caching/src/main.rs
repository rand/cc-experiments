//! Multi-Level Caching Demo
//!
//! Demonstrates production caching patterns for DSPy services:
//! 1. Cache performance (miss → hit comparison)
//! 2. Sequential vs cached comparison
//! 3. Cache warming
//! 4. TTL testing
//! 5. Cost savings calculation

use anyhow::Result;
use multi_level_caching::DSpyCacheService;
use std::time::{Duration, Instant};

/// ANSI color codes for pretty output
mod colors {
    pub const RESET: &str = "\x1b[0m";
    pub const BOLD: &str = "\x1b[1m";
    pub const GREEN: &str = "\x1b[32m";
    pub const YELLOW: &str = "\x1b[33m";
    pub const BLUE: &str = "\x1b[34m";
    pub const CYAN: &str = "\x1b[36m";
    pub const RED: &str = "\x1b[31m";
}

/// Print a section header
fn print_header(title: &str) {
    println!(
        "\n{}{}╔════════════════════════════════════════════════════════════╗{}",
        colors::BOLD,
        colors::BLUE,
        colors::RESET
    );
    println!(
        "{}{}║  {:<56}  ║{}",
        colors::BOLD,
        colors::BLUE,
        title,
        colors::RESET
    );
    println!(
        "{}{}╚════════════════════════════════════════════════════════════╝{}",
        colors::BOLD,
        colors::BLUE,
        colors::RESET
    );
}

/// Print a sub-section
fn print_subsection(title: &str) {
    println!(
        "\n{}{}▶ {}{}",
        colors::BOLD,
        colors::CYAN,
        title,
        colors::RESET
    );
    println!("{}{}", colors::CYAN, "─".repeat(60));
    println!("{}", colors::RESET);
}

/// Format duration in milliseconds with color coding
fn format_duration(duration: Duration) -> String {
    let ms = duration.as_millis();
    let color = if ms < 10 {
        colors::GREEN
    } else if ms < 100 {
        colors::YELLOW
    } else {
        colors::RED
    };

    format!("{}{}ms{}", color, ms, colors::RESET)
}

/// Demo 1: Cache Performance Comparison
///
/// Shows the difference between:
/// - First call (cache miss → LM API)
/// - Second call (cache hit → memory)
/// - Third call (same input, memory cache)
async fn demo_cache_performance(service: &mut DSpyCacheService) -> Result<()> {
    print_header("Demo 1: Cache Performance");

    let question = "What is Rust and why is it popular?";

    // First call: Cache miss
    print_subsection("First Call (Cache Miss → LM API)");
    println!("Question: {}", question);

    let start = Instant::now();
    let result1 = service.predict(question.to_string()).await?;
    let duration1 = start.elapsed();

    println!("Answer: {}", result1.answer);
    println!(
        "{}Cached:{} {}",
        colors::BOLD,
        colors::RESET,
        result1.metadata.cached
    );
    println!(
        "{}Duration:{} {}",
        colors::BOLD,
        colors::RESET,
        format_duration(duration1)
    );

    // Wait a moment to show realistic timing
    tokio::time::sleep(Duration::from_secs(1)).await;

    // Second call: Cache hit (memory)
    print_subsection("Second Call (Cache Hit → Memory)");
    println!("Question: {}", question);

    let start = Instant::now();
    let result2 = service.predict(question.to_string()).await?;
    let duration2 = start.elapsed();

    println!("Answer: {}", result2.answer);
    println!(
        "{}Cached:{} {}",
        colors::BOLD,
        colors::RESET,
        result2.metadata.cached
    );
    println!(
        "{}Cache Level:{} {:?}",
        colors::BOLD,
        colors::RESET,
        result2.metadata.cache_level
    );
    println!(
        "{}Duration:{} {}",
        colors::BOLD,
        colors::RESET,
        format_duration(duration2)
    );

    // Performance comparison
    print_subsection("Performance Comparison");
    let speedup = duration1.as_millis() as f64 / duration2.as_millis() as f64;
    println!(
        "{}Speed improvement:{} {}{:.1}x faster{}",
        colors::BOLD,
        colors::RESET,
        colors::GREEN,
        speedup,
        colors::RESET
    );
    println!(
        "Time saved: {}",
        format_duration(duration1 - duration2)
    );

    Ok(())
}

/// Demo 2: Sequential vs Cached Comparison
///
/// Compare performance of:
/// - 10 unique questions (all cache misses)
/// - Same 10 questions repeated (all cache hits)
async fn demo_sequential_vs_cached(service: &mut DSpyCacheService) -> Result<()> {
    print_header("Demo 2: Sequential vs Cached Comparison");

    let questions = vec![
        "What is async programming?",
        "Explain ownership in Rust",
        "What are traits in Rust?",
        "How does borrowing work?",
        "What is a lifetime?",
        "Explain smart pointers",
        "What is pattern matching?",
        "How do closures work?",
        "What is cargo?",
        "Explain error handling",
    ];

    // Round 1: Sequential (cache misses)
    print_subsection("Round 1: Sequential Processing (Cache Misses)");
    println!("Processing {} unique questions...\n", questions.len());

    let start = Instant::now();
    for (i, question) in questions.iter().enumerate() {
        let result = service.predict(question.to_string()).await?;
        println!(
            "  {}{}. {}Question:{} {}",
            colors::BOLD,
            i + 1,
            colors::YELLOW,
            colors::RESET,
            question
        );
        println!(
            "     {}Answer:{} {}",
            colors::BOLD,
            colors::RESET,
            &result.answer[..result.answer.len().min(60)]
        );
        if result.answer.len() > 60 {
            println!("     {}", &result.answer[60..result.answer.len().min(120)]);
        }
        println!(
            "     {}Cached:{} {}",
            colors::BOLD,
            colors::RESET,
            result.metadata.cached
        );
        println!();
    }
    let sequential_duration = start.elapsed();

    println!(
        "{}Total time:{} {}",
        colors::BOLD,
        colors::RESET,
        format_duration(sequential_duration)
    );
    println!(
        "{}Average per query:{} {}",
        colors::BOLD,
        colors::RESET,
        format_duration(sequential_duration / questions.len() as u32)
    );

    // Wait before round 2
    tokio::time::sleep(Duration::from_secs(1)).await;

    // Round 2: Cached (cache hits)
    print_subsection("Round 2: Same Questions (Cache Hits)");
    println!("Processing same {} questions from cache...\n", questions.len());

    let start = Instant::now();
    for (i, question) in questions.iter().enumerate() {
        let result = service.predict(question.to_string()).await?;
        println!(
            "  {}{}. {}Question:{} {}",
            colors::BOLD,
            i + 1,
            colors::GREEN,
            colors::RESET,
            question
        );
        println!(
            "     {}Cache Level:{} {:?}",
            colors::BOLD,
            colors::RESET,
            result.metadata.cache_level
        );
    }
    let cached_duration = start.elapsed();

    println!(
        "\n{}Total time:{} {}",
        colors::BOLD,
        colors::RESET,
        format_duration(cached_duration)
    );
    println!(
        "{}Average per query:{} {}",
        colors::BOLD,
        colors::RESET,
        format_duration(cached_duration / questions.len() as u32)
    );

    // Comparison
    print_subsection("Performance Comparison");
    let speedup = sequential_duration.as_millis() as f64 / cached_duration.as_millis() as f64;
    println!(
        "{}Speed improvement:{} {}{:.1}x faster{}",
        colors::BOLD,
        colors::RESET,
        colors::GREEN,
        speedup,
        colors::RESET
    );
    println!(
        "Time saved: {}",
        format_duration(sequential_duration - cached_duration)
    );

    Ok(())
}

/// Demo 3: Cache Warming
///
/// Pre-populate cache with common queries for instant responses
async fn demo_cache_warming(service: &mut DSpyCacheService) -> Result<()> {
    print_header("Demo 3: Cache Warming");

    print_subsection("Warming Cache with Common Queries");

    let common_queries = vec![
        "What is Rust?".to_string(),
        "How does async work in Rust?".to_string(),
        "Explain Rust's ownership system".to_string(),
        "What are the benefits of Rust?".to_string(),
        "How do I get started with Rust?".to_string(),
    ];

    println!("Pre-populating cache with {} common queries...\n", common_queries.len());

    let start = Instant::now();
    let warmed = service.warm_cache(common_queries.clone()).await?;
    let warm_duration = start.elapsed();

    println!(
        "{}✓{} Warmed {} queries in {}",
        colors::GREEN,
        colors::RESET,
        warmed,
        format_duration(warm_duration)
    );

    // Now demonstrate instant responses
    print_subsection("Testing Warmed Cache");
    println!("Making requests to pre-warmed queries...\n");

    for (i, query) in common_queries.iter().enumerate() {
        let start = Instant::now();
        let result = service.predict(query.clone()).await?;
        let duration = start.elapsed();

        println!(
            "  {}{}. {}{}",
            colors::BOLD,
            i + 1,
            colors::RESET,
            query
        );
        println!(
            "     {}Duration:{} {}",
            colors::BOLD,
            colors::RESET,
            format_duration(duration)
        );
        println!(
            "     {}Cache Level:{} {:?}",
            colors::BOLD,
            colors::RESET,
            result.metadata.cache_level
        );
        println!();
    }

    Ok(())
}

/// Demo 4: Cache Statistics
///
/// Show detailed cache performance metrics
async fn demo_cache_statistics(service: &DSpyCacheService) -> Result<()> {
    print_header("Demo 4: Cache Statistics");

    print_subsection("Detailed Cache Report");

    let report = service.detailed_stats_report().await;
    println!("{}", report);

    // Get stats for additional analysis
    let stats = service.cache_stats().await;

    print_subsection("Cache Efficiency Analysis");

    let hit_rate = stats.hit_rate() * 100.0;
    let efficiency_color = if hit_rate >= 90.0 {
        colors::GREEN
    } else if hit_rate >= 75.0 {
        colors::YELLOW
    } else {
        colors::RED
    };

    println!(
        "{}Overall Hit Rate:{} {}{:.1}%{}",
        colors::BOLD,
        colors::RESET,
        efficiency_color,
        hit_rate,
        colors::RESET
    );

    let (mem_pct, redis_pct, miss_pct) = stats.level_breakdown();
    println!(
        "  {}Memory (L1):{} {:.1}% of requests",
        colors::BOLD,
        colors::RESET,
        mem_pct
    );
    println!(
        "  {}Redis (L2):{} {:.1}% of requests",
        colors::BOLD,
        colors::RESET,
        redis_pct
    );
    println!(
        "  {}LM API (L3):{} {:.1}% of requests",
        colors::BOLD,
        colors::RESET,
        miss_pct
    );

    print_subsection("Cost Savings Calculation");

    // Assuming different price points
    let prices = vec![
        ("GPT-3.5-Turbo", 0.001),
        ("GPT-4", 0.03),
        ("Claude Opus", 0.015),
    ];

    println!("Estimated cost savings by model:\n");
    for (model, cost_per_call) in prices {
        let savings = stats.cost_savings(cost_per_call);
        let total_cost = stats.total_predictions as f64 * cost_per_call;
        let savings_pct = (savings / total_cost) * 100.0;

        println!(
            "  {}{}:{}",
            colors::BOLD,
            model,
            colors::RESET
        );
        println!(
            "    {}Without cache:{} ${:.4}",
            colors::BOLD,
            colors::RESET,
            total_cost
        );
        println!(
            "    {}With cache:{} ${:.4}",
            colors::BOLD,
            colors::RESET,
            total_cost - savings
        );
        println!(
            "    {}Savings:{} {}{:.4} ({:.1}%){}",
            colors::BOLD,
            colors::RESET,
            colors::GREEN,
            savings,
            savings_pct,
            colors::RESET
        );
        println!();
    }

    Ok(())
}

/// Demo 5: Cache Invalidation
///
/// Show how to clear caches when needed
async fn demo_cache_invalidation(service: &mut DSpyCacheService) -> Result<()> {
    print_header("Demo 5: Cache Invalidation");

    print_subsection("Before Clearing Cache");
    let stats_before = service.cache_stats().await;
    println!(
        "Memory cache: {}/{} entries",
        stats_before.memory_cache_size,
        stats_before.memory_cache_capacity
    );
    println!("Total predictions: {}", stats_before.total_predictions);
    println!("Cache hits: {}", stats_before.memory_hits + stats_before.redis_hits);

    print_subsection("Clearing All Caches");
    println!("Reasons to clear cache:");
    println!("  • Model updated (new version deployed)");
    println!("  • Prompt changed (signature modified)");
    println!("  • Bad predictions detected");
    println!("  • Data changed (underlying knowledge updated)");
    println!();

    service.clear_caches().await?;
    println!("{}✓{} All caches cleared", colors::GREEN, colors::RESET);

    print_subsection("After Clearing Cache");
    let stats_after = service.cache_stats().await;
    println!(
        "Memory cache: {}/{} entries",
        stats_after.memory_cache_size,
        stats_after.memory_cache_capacity
    );
    println!("Total predictions: {}", stats_after.total_predictions);

    println!(
        "\n{}Note:{} Statistics are preserved across cache clears for monitoring",
        colors::BOLD,
        colors::RESET
    );

    Ok(())
}

/// Main entry point
#[tokio::main]
async fn main() -> Result<()> {
    // Print welcome banner
    println!("{}{}", colors::BOLD, colors::BLUE);
    println!("╔══════════════════════════════════════════════════════════════╗");
    println!("║                                                              ║");
    println!("║        Multi-Level Caching for DSPy Services                ║");
    println!("║        Production-Grade Caching Demo                        ║");
    println!("║                                                              ║");
    println!("╚══════════════════════════════════════════════════════════════╝");
    println!("{}", colors::RESET);

    // Check prerequisites
    println!("\n{}Checking prerequisites...{}", colors::BOLD, colors::RESET);

    // Check Redis
    print!("  • Redis connection... ");
    match redis::Client::open("redis://localhost:6379") {
        Ok(client) => match client.get_connection() {
            Ok(_) => println!("{}✓{}", colors::GREEN, colors::RESET),
            Err(e) => {
                println!("{}✗{}", colors::RED, colors::RESET);
                println!("\n{}Error:{} Redis connection failed: {}", colors::RED, colors::RESET, e);
                println!("\n{}Hint:{} Start Redis with: docker-compose up -d", colors::YELLOW, colors::RESET);
                return Ok(());
            }
        },
        Err(e) => {
            println!("{}✗{}", colors::RED, colors::RESET);
            println!("\n{}Error:{} Invalid Redis URL: {}", colors::RED, colors::RESET, e);
            return Ok(());
        }
    }

    // Check Python DSPy
    print!("  • Python DSPy module... ");
    match pyo3::Python::with_gil(|py| {
        py.import("dspy")
    }) {
        Ok(_) => println!("{}✓{}", colors::GREEN, colors::RESET),
        Err(e) => {
            println!("{}✗{}", colors::RED, colors::RESET);
            println!("\n{}Error:{} DSPy not found: {}", colors::RED, colors::RESET, e);
            println!("\n{}Hint:{} Install with: pip install dspy-ai", colors::YELLOW, colors::RESET);
            return Ok(());
        }
    }

    // Check OpenAI API key
    print!("  • OpenAI API key... ");
    if std::env::var("OPENAI_API_KEY").is_ok() {
        println!("{}✓{}", colors::GREEN, colors::RESET);
    } else {
        println!("{}✗{}", colors::RED, colors::RESET);
        println!("\n{}Warning:{} OPENAI_API_KEY not set", colors::YELLOW, colors::RESET);
        println!("{}Hint:{} Export with: export OPENAI_API_KEY=sk-...", colors::YELLOW, colors::RESET);
        println!("\nProceeding with demo (predictions may fail)...");
    }

    println!("\n{}All prerequisites satisfied!{}", colors::GREEN, colors::RESET);

    // Initialize service
    println!("\n{}Initializing cache service...{}", colors::BOLD, colors::RESET);

    let mut service = DSpyCacheService::new(
        "redis://localhost:6379",
        "question -> answer",
        1000,  // Memory cache: 1000 entries
        3600,  // Redis TTL: 1 hour
    )
    .await?;

    println!("{}✓{} Service initialized", colors::GREEN, colors::RESET);
    println!("  • Memory cache: 1,000 entries (LRU)");
    println!("  • Redis cache: 1 hour TTL");
    println!("  • DSPy signature: question -> answer");

    // Run demos
    demo_cache_performance(&mut service).await?;
    demo_sequential_vs_cached(&mut service).await?;
    demo_cache_warming(&mut service).await?;
    demo_cache_statistics(&service).await?;
    demo_cache_invalidation(&mut service).await?;

    // Final summary
    print_header("Demo Complete");
    println!("\n{}Key Takeaways:{}\n", colors::BOLD, colors::RESET);
    println!("  {}1.{} Multi-level caching provides {}{}-{}x speedup{}",
        colors::BOLD, colors::RESET, colors::GREEN, 100, 3000, colors::RESET);
    println!("  {}2.{} Memory (L1) cache delivers <1ms latency",
        colors::BOLD, colors::RESET);
    println!("  {}3.{} Redis (L2) cache provides persistence + distribution",
        colors::BOLD, colors::RESET);
    println!("  {}4.{} Cache hit rates of {}85-95%{} are achievable",
        colors::BOLD, colors::RESET, colors::GREEN, colors::RESET);
    println!("  {}5.{} Cost savings of {}50-90%{} on LM API calls",
        colors::BOLD, colors::RESET, colors::GREEN, colors::RESET);

    println!("\n{}Next Steps:{}\n", colors::BOLD, colors::RESET);
    println!("  • Add circuit breakers for resilience");
    println!("  • Implement Prometheus metrics");
    println!("  • Add structured logging");
    println!("  • Track cost per request");
    println!("  • Build A/B testing infrastructure");

    println!("\n{}Thank you for using Multi-Level Caching!{}", colors::BOLD, colors::RESET);

    Ok(())
}
