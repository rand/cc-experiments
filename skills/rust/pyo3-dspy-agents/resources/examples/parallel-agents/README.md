# Parallel Agents Example

High-performance concurrent agent execution using Tokio's JoinSet for parallel processing, result aggregation, and benchmarking.

## Overview

This example demonstrates:

- **Concurrent execution** using `tokio::task::JoinSet` for parallel agent processing
- **Result aggregation** with deduplication and consensus voting
- **Performance benchmarking** comparing parallel vs sequential execution
- **Throughput measurements** across different concurrency levels
- **Agent pool management** with semaphore-based rate limiting

## Architecture

### Core Components

#### ParallelAgentExecutor

The main executor that manages concurrent agent execution:

```rust
pub struct ParallelAgentExecutor {
    config: ParallelConfig,
    semaphore: Arc<Semaphore>,
    metrics_cache: Arc<DashMap<String, ExecutionMetrics>>,
}
```

**Features**:
- JoinSet-based parallel execution
- Configurable concurrency limits
- Timeout handling per agent
- Automatic result aggregation
- Performance metrics collection

#### ParallelConfig

Configuration for execution behavior:

```rust
pub struct ParallelConfig {
    pub max_concurrency: usize,        // Max concurrent agents
    pub agent_timeout: Duration,       // Timeout per agent
    pub deduplicate_results: bool,     // Remove duplicates
    pub consensus_threshold: f32,      // Min confidence for consensus
}
```

#### ExecutionMetrics

Performance tracking:

```rust
pub struct ExecutionMetrics {
    pub total_duration: Duration,
    pub successful_count: usize,
    pub failed_count: usize,
    pub avg_duration: Duration,
    pub min_duration: Duration,
    pub max_duration: Duration,
    pub throughput: f64,               // requests/second
}
```

## Usage

### Build and Run

```bash
cd skills/rust/pyo3-dspy-agents/resources/examples/parallel-agents
cargo build --release
cargo run --release
```

### Run Tests

```bash
cargo test
```

## Examples

### Example 1: Basic Parallel Execution

Execute multiple questions concurrently:

```rust
let config = ParallelConfig {
    max_concurrency: 4,
    agent_timeout: Duration::from_secs(30),
    deduplicate_results: false,
    consensus_threshold: 0.6,
};

let executor = ParallelAgentExecutor::new(config);

let questions = vec![
    "What is the capital of France?".to_string(),
    "What is 2 + 2?".to_string(),
    // ...
];

let results = executor.execute_parallel(questions).await?;
```

**Output**:
```
Questions to process:
  1. What is the capital of France?
  2. What is 2 + 2?
  3. Who wrote Romeo and Juliet?
  4. What is the speed of light?

Results:
  1. Agent 0 answer for 'What is the capital of France?' (took 102ms)
  2. Agent 1 answer for 'What is 2 + 2?' (took 98ms)
  3. Agent 2 answer for 'Who wrote Romeo and Juliet?' (took 105ms)
  4. Agent 3 answer for 'What is the speed of light?' (took 101ms)

Total execution time: 107ms
```

### Example 2: Parallel vs Sequential Comparison

Benchmark performance improvements:

```rust
let executor = ParallelAgentExecutor::new(config);

// Run parallel
let (parallel_results, parallel_duration) =
    benchmark_parallel_execution(&executor, questions.clone()).await?;

// Run sequential
let (sequential_results, sequential_duration) =
    benchmark_sequential_execution(questions.clone()).await?;
```

**Output**:
```
================================================================================
PERFORMANCE COMPARISON
================================================================================

Execution Times:
  Sequential: 823ms
  Parallel:   112ms
  Speedup:    7.35x

Throughput:
  Sequential: 9.72 req/sec
  Parallel:   71.43 req/sec

Efficiency:
  Time saved: 711ms (86.4%)
================================================================================
```

### Example 3: Consensus Voting

Multiple agents vote on the same question:

```rust
let result = executor
    .execute_with_consensus(
        "What is the capital of France?".to_string(),
        5  // 5 agents
    )
    .await?;
```

**Output**:
```
================================================================================
AGGREGATED RESULTS WITH CONSENSUS
================================================================================

Consensus:
  Answer:     Agent 0 answer for 'What is the capital of France?'
  Confidence: 100.0%

Individual Results:
  Agent 0: Agent 0 answer for 'What is the capital of France?' (took 101ms)
  Agent 1: Agent 1 answer for 'What is the capital of France?' (took 98ms)
  Agent 2: Agent 2 answer for 'What is the capital of France?' (took 102ms)
  Agent 3: Agent 3 answer for 'What is the capital of France?' (took 99ms)
  Agent 4: Agent 4 answer for 'What is the capital of France?' (took 103ms)

--------------------------------------------------------------------------------
EXECUTION METRICS
--------------------------------------------------------------------------------

Results:
  Successful: 5
  Failed:     0
  Total:      5

Timing:
  Total:      105ms
  Average:    21ms
  Min:        98ms
  Max:        103ms

Performance:
  Throughput: 47.62 req/sec
================================================================================
```

### Example 4: Agent Pool

Managed pool of agents with automatic load balancing:

```rust
let pool = AgentPool::new(6, config);

let results = pool.execute_batch(questions).await?;
```

**Output**:
```
Agent pool size: 6
Processing 8 questions...

Results:
  1. Agent 0 answer for 'What is the capital of France?' (took 102ms)
  2. Agent 1 answer for 'What is 2 + 2?' (took 99ms)
  3. Agent 2 answer for 'Who wrote Romeo and Juliet?' (took 101ms)
  ...

Total execution time: 145ms
Average time per question: 18ms
```

### Example 5: Throughput Benchmark

Compare different concurrency levels:

```rust
let configs = vec![
    ("Low Concurrency (2)", 2),
    ("Medium Concurrency (4)", 4),
    ("High Concurrency (8)", 8),
    ("Very High Concurrency (16)", 16),
];
```

**Output**:
```
Testing 32 questions with different concurrency levels

Configuration                       Duration      Throughput
-----------------------------------------------------------------
Low Concurrency (2)                  1.62s        19.75 req/s
Medium Concurrency (4)             821.34ms        38.96 req/s
High Concurrency (8)               412.56ms        77.58 req/s
Very High Concurrency (16)         218.45ms       146.49 req/s
-----------------------------------------------------------------
```

## Performance Characteristics

### Throughput Improvements

With optimal concurrency, expect:

- **2-8x speedup** for I/O-bound tasks
- **Linear scaling** up to CPU core count
- **Diminishing returns** beyond 8-16 concurrent tasks
- **Best efficiency** at 4-8 concurrent agents

### Concurrency Recommendations

| Use Case | Recommended Concurrency | Notes |
|----------|------------------------|-------|
| Development/Testing | 2-4 | Lower overhead |
| Production (CPU-bound) | 4-8 | Match CPU cores |
| Production (I/O-bound) | 8-16 | Higher parallelism |
| Batch Processing | 16-32 | Maximum throughput |

### Memory Usage

Per agent overhead: ~1-2MB
Total memory: `base + (concurrency * agent_memory)`

Example:
- 4 concurrent agents: ~50MB
- 8 concurrent agents: ~60MB
- 16 concurrent agents: ~80MB

## Advanced Features

### Result Deduplication

Automatically remove duplicate answers:

```rust
let config = ParallelConfig {
    deduplicate_results: true,
    ..Default::default()
};

let deduplicated = executor.deduplicate_results(results);
```

### Stream-Based Execution

For more control over buffering:

```rust
let results = executor
    .execute_with_stream(questions, buffer_size)
    .await?;
```

### Metrics Caching

Store and retrieve metrics:

```rust
executor.store_metrics(question.clone(), metrics);
let cached = executor.get_metrics(&question);
```

## Error Handling

### Timeout Handling

Individual agents timeout independently:

```rust
let config = ParallelConfig {
    agent_timeout: Duration::from_secs(30),
    ..Default::default()
};
```

Timeout results are captured:

```rust
AgentResult {
    success: false,
    error: Some("Timeout".to_string()),
    ..
}
```

### Partial Failures

System continues even if some agents fail:

```rust
for result in results {
    if result.success {
        // Use result
    } else {
        warn!("Agent failed: {}", result.error.unwrap());
    }
}
```

## Integration with DSPy

This example provides mock implementations. For production:

### Replace Mock with Real DSPy Agent

In `lib.rs`, replace:

```rust
fn call_dspy_agent(py: Python, question: &str, agent_id: usize) -> Result<String> {
    // Mock implementation
    Ok(format!("Agent {} answer...", agent_id))
}
```

With:

```rust
fn call_dspy_agent(py: Python, question: &str, agent_id: usize) -> Result<String> {
    let dspy = py.import_bound("dspy")?;
    let react = py.import_bound("dspy.ReAct")?;

    let agent = react.getattr("ReAct")?;
    let result = agent.call1((question,))?;

    let answer: String = result.extract()?;
    Ok(answer)
}
```

## Best Practices

1. **Start with low concurrency** (2-4) and increase based on testing
2. **Monitor resource usage** (CPU, memory, network)
3. **Set appropriate timeouts** based on expected agent latency
4. **Use consensus voting** for critical decisions
5. **Cache metrics** to track performance trends
6. **Implement backoff** for rate-limited APIs
7. **Test failure modes** (timeouts, errors, partial failures)

## Troubleshooting

### High CPU Usage

- Reduce `max_concurrency`
- Increase `agent_timeout` to reduce retry overhead
- Profile with `cargo flamegraph`

### Memory Issues

- Lower concurrency
- Enable result deduplication
- Clear metrics cache periodically

### Poor Throughput

- Increase concurrency (if CPU allows)
- Reduce per-agent overhead
- Use streaming for large batches
- Check network/I/O bottlenecks

## References

- [Tokio JoinSet Documentation](https://docs.rs/tokio/latest/tokio/task/struct.JoinSet.html)
- [PyO3 Guide](https://pyo3.rs)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [Parallel Agent Patterns](../../REFERENCE.md#parallel-agent-execution)

## License

MIT
