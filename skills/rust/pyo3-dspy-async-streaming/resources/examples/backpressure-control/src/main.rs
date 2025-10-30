//! Backpressure control demonstration
//!
//! This binary demonstrates various backpressure handling scenarios including:
//! - Simple blocking backpressure
//! - Slow consumer with drop strategy
//! - Fast producer with adaptive rate control
//! - Visual metrics display

use anyhow::Result;
use backpressure_control::{
    AdaptiveRateController, BackpressureController, BackpressureMetrics, BackpressureStrategy,
    RateControlAlgorithm,
};
use std::time::Duration;
use tokio::time;
use tracing::{info, Level};
use tracing_subscriber;

/// Display metrics in a visual format
fn display_metrics(metrics: &BackpressureMetrics, capacity: usize, max_rate: f64) {
    println!("\n=== Backpressure Metrics ===");

    // Queue depth bar
    let queue_pct = (metrics.current_depth as f64 / capacity as f64 * 100.0) as usize;
    let queue_bar = format!(
        "[{}{}]",
        "█".repeat(queue_pct / 5),
        "░".repeat(20 - queue_pct / 5)
    );
    println!(
        "Queue Depth: {} {}/{}",
        queue_bar, metrics.current_depth, capacity
    );

    // Rate limit bar (if adaptive)
    if metrics.current_rate_limit > 0.0 {
        let rate_pct = (metrics.current_rate_limit / max_rate * 100.0) as usize;
        let rate_bar = format!(
            "[{}{}]",
            "█".repeat(rate_pct / 5),
            "░".repeat(20 - rate_pct / 5)
        );
        println!(
            "Rate Limit:  {} {:.1}/{:.0} items/sec",
            rate_bar, metrics.current_rate_limit, max_rate
        );
    }

    // Dropped items bar
    let max_dropped = metrics.produced_count.max(1);
    let dropped_pct = (metrics.dropped_count as f64 / max_dropped as f64 * 100.0) as usize;
    let dropped_bar = format!(
        "[{}{}]",
        "█".repeat((dropped_pct / 5).min(20)),
        "░".repeat(20 - (dropped_pct / 5).min(20))
    );
    println!(
        "Dropped:     {} {} items ({:.1}%)",
        dropped_bar, metrics.dropped_count, dropped_pct
    );

    // Throughput bar
    let throughput_pct = ((metrics.throughput_rate / max_rate * 100.0) as usize).min(100);
    let throughput_bar = format!(
        "[{}{}]",
        "█".repeat(throughput_pct / 5),
        "░".repeat(20 - throughput_pct / 5)
    );
    println!(
        "Throughput:  {} {:.1} items/sec",
        throughput_bar, metrics.throughput_rate
    );

    // Statistics
    println!("\n=== Statistics ===");
    println!("Produced:           {} items", metrics.produced_count);
    println!("Consumed:           {} items", metrics.consumed_count);
    println!("Peak Queue Depth:   {} items", metrics.peak_depth);
    println!("Avg Queue Depth:    {:.1} items", metrics.avg_queue_depth);
    println!("Backpressure Events: {}", metrics.backpressure_events);
    println!("===================\n");
}

/// Scenario 1: Simple backpressure with blocking
async fn scenario_blocking() -> Result<()> {
    info!("=== Scenario 1: Blocking Backpressure ===");
    info!("Fast producer (100 items/sec) vs Slow consumer (10 items/sec)");
    info!("Strategy: Block producer when buffer is full\n");

    let controller = BackpressureController::new(20, BackpressureStrategy::Block);
    let capacity = controller.capacity();

    // Spawn producer task
    let producer_controller = BackpressureController::new(20, BackpressureStrategy::Block);
    let producer = tokio::spawn(async move {
        for i in 0..50 {
            producer_controller.send(i).await.ok();
            time::sleep(Duration::from_millis(10)).await; // 100 items/sec
        }
    });

    // Consumer task (slow)
    let consumer = tokio::spawn(async move {
        let mut count = 0;
        while count < 50 {
            if let Some(_item) = controller.recv().await {
                count += 1;
                time::sleep(Duration::from_millis(100)).await; // 10 items/sec

                if count % 10 == 0 {
                    let metrics = controller.metrics().await;
                    display_metrics(&metrics, capacity, 100.0);
                }
            }
        }
    });

    producer.await?;
    consumer.await?;

    info!("Scenario 1 complete\n");
    Ok(())
}

/// Scenario 2: Drop strategy with slow consumer
async fn scenario_drop_oldest() -> Result<()> {
    info!("=== Scenario 2: Drop Oldest Strategy ===");
    info!("Fast producer (100 items/sec) vs Slow consumer (10 items/sec)");
    info!("Strategy: Drop oldest items when buffer is full\n");

    let controller = BackpressureController::new(20, BackpressureStrategy::DropOldest);
    let capacity = controller.capacity();

    // Spawn producer task
    let producer_controller = BackpressureController::new(20, BackpressureStrategy::DropOldest);
    let producer = tokio::spawn(async move {
        for i in 0..100 {
            producer_controller.send(i).await.ok();
            time::sleep(Duration::from_millis(10)).await; // 100 items/sec
        }
    });

    // Consumer task (slow)
    let consumer = tokio::spawn(async move {
        let mut count = 0;
        time::sleep(Duration::from_secs(1)).await; // Initial delay

        while count < 50 {
            if let Some(_item) = controller.recv().await {
                count += 1;
                time::sleep(Duration::from_millis(100)).await; // 10 items/sec

                if count % 10 == 0 {
                    let metrics = controller.metrics().await;
                    display_metrics(&metrics, capacity, 100.0);
                }
            }
        }

        // Final metrics
        let metrics = controller.metrics().await;
        display_metrics(&metrics, capacity, 100.0);
    });

    producer.await?;
    consumer.await?;

    info!("Scenario 2 complete\n");
    Ok(())
}

/// Scenario 3: Adaptive rate control
async fn scenario_adaptive() -> Result<()> {
    info!("=== Scenario 3: Adaptive Rate Control (AIMD) ===");
    info!("Variable producer with adaptive rate limiting");
    info!("Strategy: Dynamically adjust production rate based on backpressure\n");

    let controller = BackpressureController::with_rate_control(
        50,
        RateControlAlgorithm::AIMD,
        50.0,  // Initial rate: 50 items/sec
        200.0, // Max rate: 200 items/sec
    );
    let capacity = controller.capacity();

    // Spawn producer task
    let producer_controller = BackpressureController::with_rate_control(
        50,
        RateControlAlgorithm::AIMD,
        50.0,
        200.0,
    );

    let producer = tokio::spawn(async move {
        for i in 0..200 {
            producer_controller.send(i).await.ok();

            // Variable delay based on item number to simulate bursts
            let delay_ms = if i % 50 < 25 {
                5 // Fast burst: 200 items/sec
            } else {
                20 // Slower: 50 items/sec
            };
            time::sleep(Duration::from_millis(delay_ms)).await;
        }
    });

    // Consumer task (variable speed)
    let consumer = tokio::spawn(async move {
        let mut count = 0;
        while count < 200 {
            if let Some(_item) = controller.recv().await {
                count += 1;

                // Variable consumption rate
                let delay_ms = if count % 100 < 50 {
                    15 // Faster: ~66 items/sec
                } else {
                    30 // Slower: ~33 items/sec
                };
                time::sleep(Duration::from_millis(delay_ms)).await;

                if count % 25 == 0 {
                    let metrics = controller.metrics().await;
                    display_metrics(&metrics, capacity, 200.0);
                }
            }
        }

        // Final metrics
        let metrics = controller.metrics().await;
        display_metrics(&metrics, capacity, 200.0);
    });

    producer.await?;
    consumer.await?;

    info!("Scenario 3 complete\n");
    Ok(())
}

/// Scenario 4: Burst handling with token bucket
async fn scenario_token_bucket() -> Result<()> {
    info!("=== Scenario 4: Token Bucket Rate Limiting ===");
    info!("Bursty producer with token bucket rate control");
    info!("Strategy: Allow bursts up to bucket capacity, then rate limit\n");

    let controller = BackpressureController::with_rate_control(
        100,
        RateControlAlgorithm::TokenBucket,
        50.0,  // Refill rate: 50 items/sec
        100.0, // Bucket capacity: 100 items
    );
    let capacity = controller.capacity();

    // Spawn producer task (bursty)
    let producer_controller = BackpressureController::with_rate_control(
        100,
        RateControlAlgorithm::TokenBucket,
        50.0,
        100.0,
    );

    let producer = tokio::spawn(async move {
        for burst in 0..5 {
            info!("Burst {} starting...", burst + 1);

            // Send burst of 30 items quickly
            for i in 0..30 {
                producer_controller.send(burst * 30 + i).await.ok();
                time::sleep(Duration::from_millis(2)).await; // 500 items/sec burst
            }

            info!("Burst {} complete, waiting...", burst + 1);
            time::sleep(Duration::from_secs(1)).await; // Wait between bursts
        }
    });

    // Consumer task (steady)
    let consumer = tokio::spawn(async move {
        let mut count = 0;
        while count < 150 {
            if let Some(_item) = controller.recv().await {
                count += 1;
                time::sleep(Duration::from_millis(20)).await; // 50 items/sec steady

                if count % 20 == 0 {
                    let metrics = controller.metrics().await;
                    display_metrics(&metrics, capacity, 100.0);
                }
            }
        }

        // Final metrics
        let metrics = controller.metrics().await;
        display_metrics(&metrics, capacity, 100.0);
    });

    producer.await?;
    consumer.await?;

    info!("Scenario 4 complete\n");
    Ok(())
}

/// Scenario 5: Multiple strategies comparison
async fn scenario_comparison() -> Result<()> {
    info!("=== Scenario 5: Strategy Comparison ===");
    info!("Running same workload with different strategies\n");

    let strategies = vec![
        ("Block", BackpressureStrategy::Block),
        ("Drop Oldest", BackpressureStrategy::DropOldest),
        ("Drop Newest", BackpressureStrategy::DropNewest),
        ("Adaptive", BackpressureStrategy::Adaptive),
    ];

    for (name, strategy) in strategies {
        info!("Testing strategy: {}", name);

        let controller = BackpressureController::new(30, strategy);
        let capacity = controller.capacity();

        // Producer
        let producer_controller = BackpressureController::new(30, strategy);
        let producer = tokio::spawn(async move {
            for i in 0..100 {
                producer_controller.send(i).await.ok();
                time::sleep(Duration::from_millis(8)).await; // ~125 items/sec
            }
        });

        // Consumer
        let consumer = tokio::spawn(async move {
            let mut count = 0;
            while count < 80 {
                if let Some(_item) = controller.recv().await {
                    count += 1;
                    time::sleep(Duration::from_millis(15)).await; // ~66 items/sec
                }
            }

            let metrics = controller.metrics().await;
            println!("\n{} Results:", name);
            display_metrics(&metrics, capacity, 125.0);
        });

        producer.await?;
        consumer.await?;

        time::sleep(Duration::from_millis(500)).await; // Brief pause between tests
    }

    info!("Scenario 5 complete\n");
    Ok(())
}

/// Demonstrate rate controller independently
async fn demo_rate_controller() -> Result<()> {
    info!("=== Rate Controller Demo ===");
    info!("Demonstrating AIMD rate adaptation\n");

    let controller = AdaptiveRateController::new(RateControlAlgorithm::AIMD, 50.0, 200.0);

    info!("Initial rate: {:.1} items/sec", controller.current_rate().await);

    // Simulate successful sends (no backpressure)
    for i in 1..=5 {
        controller.increase_rate().await;
        info!(
            "After {} successful intervals: {:.1} items/sec",
            i,
            controller.current_rate().await
        );
        time::sleep(Duration::from_millis(100)).await;
    }

    // Simulate backpressure event
    info!("\nBackpressure event!");
    controller.decrease_rate().await;
    info!(
        "After backpressure: {:.1} items/sec",
        controller.current_rate().await
    );

    // Recovery
    for i in 1..=3 {
        controller.increase_rate().await;
        info!(
            "Recovery step {}: {:.1} items/sec",
            i,
            controller.current_rate().await
        );
        time::sleep(Duration::from_millis(100)).await;
    }

    info!("\nRate Controller Demo complete\n");
    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_max_level(Level::INFO)
        .with_target(false)
        .init();

    println!("\n╔══════════════════════════════════════════════════════════╗");
    println!("║     Backpressure Control Demonstration                  ║");
    println!("║     Rust Async Streaming Patterns                       ║");
    println!("╚══════════════════════════════════════════════════════════╝\n");

    // Run rate controller demo
    demo_rate_controller().await?;

    // Run scenarios with delays between them
    time::sleep(Duration::from_secs(1)).await;
    scenario_blocking().await?;

    time::sleep(Duration::from_secs(1)).await;
    scenario_drop_oldest().await?;

    time::sleep(Duration::from_secs(1)).await;
    scenario_adaptive().await?;

    time::sleep(Duration::from_secs(1)).await;
    scenario_token_bucket().await?;

    time::sleep(Duration::from_secs(1)).await;
    scenario_comparison().await?;

    println!("\n╔══════════════════════════════════════════════════════════╗");
    println!("║     All Scenarios Complete                              ║");
    println!("╚══════════════════════════════════════════════════════════╝\n");

    info!("Key Takeaways:");
    info!("1. Blocking: Ensures no data loss but can slow producer");
    info!("2. Drop strategies: Maintain throughput but lose data");
    info!("3. Adaptive: Balances throughput and data loss");
    info!("4. Token bucket: Allows bursts while maintaining average rate");
    info!("5. Choose strategy based on your specific requirements!");

    Ok(())
}
