# Backpressure Control Example

A comprehensive demonstration of backpressure handling patterns for async streaming in Rust, with focus on bounded channels, adaptive rate control, and producer-consumer coordination.

## Overview

This example showcases:

- **Bounded Channel Management**: Using capacity-limited channels to prevent unbounded memory growth
- **Adaptive Rate Control**: Dynamic adjustment of production rates based on consumer capacity
- **Buffer Strategies**: Multiple approaches to handling buffer overflow scenarios
- **Metrics & Monitoring**: Real-time tracking of queue depth, throughput, and backpressure events
- **Producer-Consumer Patterns**: Various scenarios demonstrating proper backpressure handling

## Key Concepts

### What is Backpressure?

Backpressure occurs when a producer generates data faster than a consumer can process it. Without proper handling, this leads to:

- Unbounded memory growth
- System instability
- Out-of-memory errors
- Poor latency characteristics

### Backpressure Strategies

1. **Drop Strategy**: Drop oldest/newest items when buffer is full
2. **Block Strategy**: Block producer until consumer catches up
3. **Adaptive Rate**: Adjust production rate dynamically
4. **Buffering**: Strategic buffering with capacity limits

## Architecture

### Components

```
Producer → [Backpressure Controller] → Bounded Channel → Consumer
              ↓
         Metrics Tracker
              ↓
      Adaptive Rate Control
```

### BackpressureController

Central coordinator that manages:
- Channel capacity limits
- Buffer overflow policies
- Rate adaptation algorithms
- Metrics collection

### BoundedDSpyStream

Stream wrapper that enforces capacity limits and tracks metrics:
- Current queue depth
- Peak queue depth
- Dropped items count
- Throughput statistics

### AdaptiveRateController

Implements algorithms for dynamic rate adjustment:
- **AIMD (Additive Increase, Multiplicative Decrease)**: TCP-like congestion control
- **Token Bucket**: Rate limiting with burst capacity
- **Sliding Window**: Time-based rate averaging

## Usage

### Basic Example

```bash
cargo run
```

This runs all demo scenarios:
1. Simple backpressure with blocking
2. Slow consumer with drop strategy
3. Fast producer with adaptive rate control
4. Multiple strategies comparison

### Custom Scenarios

```rust
use backpressure_control::{
    BackpressureController,
    BackpressureStrategy,
    AdaptiveRateController,
};

// Create controller with 100-item capacity
let controller = BackpressureController::new(100, BackpressureStrategy::Adaptive);

// Create bounded stream
let stream = controller.create_stream();

// Monitor metrics
let metrics = controller.metrics();
println!("Queue depth: {}", metrics.current_depth);
println!("Dropped: {}", metrics.dropped_count);
```

## Backpressure Strategies

### 1. Drop Oldest (FIFO)

Drops the oldest items when buffer is full. Best for:
- Real-time data where recent values matter most
- Sensor readings, live metrics
- Non-critical updates

```rust
BackpressureStrategy::DropOldest
```

### 2. Drop Newest (LIFO)

Drops incoming items when buffer is full. Best for:
- Processing queues where order matters
- Historical data processing
- Batch operations

```rust
BackpressureStrategy::DropNewest
```

### 3. Block Producer

Blocks producer until consumer catches up. Best for:
- Lossless scenarios
- Critical data that cannot be dropped
- Coordinated producer-consumer systems

```rust
BackpressureStrategy::Block
```

### 4. Adaptive Rate Control

Dynamically adjusts production rate. Best for:
- Long-running streams
- Variable consumer capacity
- Optimal throughput with minimal drops

```rust
BackpressureStrategy::Adaptive
```

## Rate Control Algorithms

### AIMD (Additive Increase, Multiplicative Decrease)

```rust
// Increase rate gradually
rate += additive_increase;

// Decrease rate sharply on backpressure
rate *= multiplicative_decrease;
```

**Parameters**:
- Additive increase: +1 item/sec per interval
- Multiplicative decrease: 0.5x on backpressure event

### Token Bucket

```rust
// Add tokens at fixed rate
tokens += refill_rate * elapsed_time;
tokens = min(tokens, capacity);

// Consume token per item
if tokens >= 1.0 {
    produce_item();
    tokens -= 1.0;
}
```

**Parameters**:
- Bucket capacity: Max burst size
- Refill rate: Sustained rate limit

### Sliding Window

```rust
// Track items in time window
window.push(now, item_count);
window.remove_older_than(now - window_duration);

// Calculate rate
current_rate = window.total_items() / window_duration;
```

## Metrics

The controller tracks comprehensive metrics:

```rust
pub struct BackpressureMetrics {
    pub current_depth: usize,       // Current items in queue
    pub peak_depth: usize,          // Max queue depth observed
    pub dropped_count: u64,         // Total dropped items
    pub produced_count: u64,        // Total produced items
    pub consumed_count: u64,        // Total consumed items
    pub throughput_rate: f64,       // Items/second
    pub backpressure_events: u64,   // Times backpressure triggered
    pub current_rate_limit: f64,    // Current production rate limit
}
```

## Scenarios Demonstrated

### Scenario 1: Simple Backpressure

- Fast producer (100 items/sec)
- Slow consumer (10 items/sec)
- Block strategy
- Demonstrates producer blocking behavior

### Scenario 2: Drop Strategy

- Fast producer (100 items/sec)
- Slow consumer (10 items/sec)
- Drop oldest strategy
- Shows graceful degradation

### Scenario 3: Adaptive Rate

- Variable producer (50-200 items/sec)
- Variable consumer (30-150 items/sec)
- AIMD rate control
- Demonstrates rate adaptation

### Scenario 4: Burst Handling

- Bursty producer (0-500 items/sec)
- Steady consumer (50 items/sec)
- Token bucket algorithm
- Shows burst accommodation

## Visualization

The demo includes real-time visualization of:

```
Queue Depth: [████████████░░░░░░░░] 60/100
Rate Limit:  [████████░░░░░░░░░░░░] 80/200 items/sec
Dropped:     [██░░░░░░░░░░░░░░░░░░] 123 items
Throughput:  [███████████████░░░░░] 75 items/sec
```

## Performance Considerations

### Channel Capacity Selection

- **Too small**: Frequent backpressure, reduced throughput
- **Too large**: High memory usage, increased latency
- **Rule of thumb**: 2-5x expected burst size

### Rate Control Tuning

- **Aggressive**: Fast adaptation, potential oscillation
- **Conservative**: Stable but slower to adapt
- **Balanced**: Start conservative, tune based on metrics

### Buffer Strategies

- **Critical path**: Use Block strategy
- **Best effort**: Use Drop strategy
- **Adaptive workloads**: Use Adaptive strategy

## Integration with DSPy/Python

This example demonstrates patterns applicable to PyO3/DSPy streaming:

```rust
// Rust side: Create bounded stream with backpressure
let controller = BackpressureController::new(1000, BackpressureStrategy::Adaptive);

// Python side: Consume with automatic backpressure
#[pyfunction]
fn create_stream(capacity: usize) -> PyResult<BoundedDSpyStream> {
    Ok(BoundedDSpyStream::new(capacity))
}
```

## Testing Strategies

### Unit Tests

- Test each backpressure strategy
- Verify metrics accuracy
- Validate rate control algorithms

### Integration Tests

- End-to-end producer-consumer scenarios
- Concurrent stream handling
- Resource cleanup

### Stress Tests

- High-rate producers
- Variable consumer speeds
- Extended runtime scenarios

## Common Pitfalls

1. **Unbounded Channels**: Always use bounded channels for backpressure control
2. **No Metrics**: Track metrics to understand system behavior
3. **Fixed Rates**: Use adaptive control for variable workloads
4. **Ignoring Backpressure**: Handle channel full errors explicitly
5. **Synchronous Blocking**: Use async select! for non-blocking operations

## Further Reading

- [Tokio Channels](https://docs.rs/tokio/latest/tokio/sync/mpsc/index.html)
- [Backpressure Patterns](https://medium.com/@jayphelps/backpressure-explained-the-flow-of-data-through-software-2350b3e77ce7)
- [AIMD Algorithm](https://en.wikipedia.org/wiki/Additive_increase/multiplicative_decrease)
- [Token Bucket](https://en.wikipedia.org/wiki/Token_bucket)

## License

This example is part of the PyO3-DSPy async streaming skill resources.
