# DSPy Performance Benchmarking Example

Complete benchmarking suite for measuring DSPy call performance from Rust using PyO3.

## Purpose

This example demonstrates how to:
- Measure single DSPy call latency
- Benchmark batch processing throughput
- Quantify GIL acquisition overhead
- Compare Predict vs ChainOfThought performance
- Track memory usage patterns
- Generate statistical performance reports

## Prerequisites

```bash
# Install Python dependencies
pip install dspy-ai openai

# Set your OpenAI API key
export OPENAI_API_KEY="your-key-here"
```

## Building and Running

```bash
# Build the benchmark suite
cargo build --release

# Run benchmarks (uses real API calls - costs apply!)
cargo run --release

# Run with custom iterations
ITERATIONS=50 cargo run --release
```

## What It Measures

### 1. Single Call Latency
Measures end-to-end latency for individual DSPy calls including:
- GIL acquisition time
- Python function call overhead
- LLM API latency
- Response parsing time

### 2. Batch Processing Throughput
Measures performance when processing multiple queries:
- Sequential vs parallel processing
- Queries per second
- Aggregate throughput
- Batching efficiency

### 3. GIL Overhead
Quantifies Python GIL acquisition cost:
- Time spent waiting for GIL
- GIL hold duration
- Impact on concurrent operations
- Overhead percentage of total time

### 4. Module Comparison
Compares different DSPy modules:
- `dspy.Predict` (simple completion)
- `dspy.ChainOfThought` (reasoning steps)
- Latency differences
- Quality vs speed tradeoffs

### 5. Memory Usage
Tracks memory consumption:
- Baseline memory
- Per-call memory delta
- Peak memory usage
- Memory leak detection

## Statistical Metrics

The benchmark reports:
- **Min**: Fastest observed time
- **Max**: Slowest observed time
- **Mean**: Average time across all runs
- **Median (P50)**: 50th percentile
- **P95**: 95th percentile (95% of calls faster)
- **P99**: 99th percentile (99% of calls faster)
- **Throughput**: Queries per second

## Sample Output

```
=== DSPy Performance Benchmark Suite ===
Iterations: 20
Model: gpt-3.5-turbo

--- Single Call Latency (Predict) ---
Min:     245.32 ms
Max:     892.17 ms
Mean:    412.58 ms
Median:  398.45 ms
P95:     724.91 ms
P99:     856.33 ms

--- Batch Processing (10 queries) ---
Sequential: 4,127.89 ms (2.42 qps)
Parallel:   1,234.56 ms (8.10 qps)
Speedup:    3.34x

--- GIL Overhead Analysis ---
Total time:      412.58 ms
GIL acquire:      12.34 ms (2.99%)
Python execute:  398.21 ms (96.52%)
Result convert:    2.03 ms (0.49%)

--- Module Comparison ---
Predict:        412.58 ms (baseline)
ChainOfThought: 687.42 ms (1.67x slower)

--- Memory Usage ---
Baseline:   45.2 MB
Peak:       52.8 MB
Delta:       7.6 MB
Per-call:  380.0 KB
```

## Performance Tips

### 1. Minimize GIL Contention
```rust
// BAD: Holding GIL during computation
Python::with_gil(|py| {
    let result = expensive_computation();
    call_dspy(py, result)
});

// GOOD: Release GIL during computation
let result = expensive_computation();
Python::with_gil(|py| call_dspy(py, result));
```

### 2. Batch When Possible
Process multiple queries in batches to amortize overhead:
```rust
// Instead of 100 individual calls
for query in queries {
    call_dspy(query)?;
}

// Batch them
call_dspy_batch(&queries)?;
```

### 3. Reuse Python Objects
```rust
// Cache module instances
Python::with_gil(|py| {
    let predictor = create_predictor(py)?;
    for query in queries {
        predictor.call1((query,))?;
    }
    Ok(())
});
```

### 4. Profile Before Optimizing
Use this benchmark to identify bottlenecks:
- If GIL overhead > 10%: Reduce GIL hold time
- If memory growing: Check for Python object leaks
- If P99 >> P50: Investigate tail latency (caching, retries)

### 5. Consider Async Patterns
For high-throughput scenarios:
```rust
// Parallel DSPy calls (releases GIL between calls)
let handles: Vec<_> = queries
    .into_iter()
    .map(|q| tokio::spawn(async move { call_dspy(q) }))
    .collect();
```

## Interpreting Results

### Latency Percentiles
- **P50 (Median)**: Typical case performance
- **P95**: Acceptable worst-case (SLA target)
- **P99**: Tail latency (cache misses, retries)

If P99 > 2x P50, investigate:
- Network instability
- API rate limiting
- Cold start effects
- Resource contention

### GIL Overhead
- **< 5%**: Excellent, Python is not bottleneck
- **5-15%**: Acceptable for most applications
- **> 15%**: Consider refactoring to reduce GIL time

### Memory Growth
If memory increases linearly:
- Python objects not being released
- Check for reference cycles
- Use `py.check_signals()` to allow GC

### Module Performance
ChainOfThought typically 1.5-3x slower than Predict:
- Generates reasoning trace
- Multiple LLM calls internally
- Higher quality but slower

Choose based on use case:
- Predict: High-throughput, latency-sensitive
- ChainOfThought: Quality-critical, explanation needed

## Benchmarking Best Practices

### 1. Warm Up
First few calls may be slower (module loading, caching):
```rust
// Run warm-up iterations (not measured)
for _ in 0..3 {
    call_dspy("warm up query")?;
}
```

### 2. Statistical Significance
Run enough iterations for stable statistics:
- Min 20 iterations for basic metrics
- 100+ for reliable percentiles
- 1000+ for tail latency analysis

### 3. Controlled Environment
- Close other applications
- Disable CPU frequency scaling
- Use consistent network conditions
- Pin to specific CPU cores (for microbenchmarks)

### 4. Cost Awareness
Benchmarking uses real API calls:
- 20 iterations ≈ $0.01-0.05
- 100 iterations ≈ $0.05-0.25
- Use cheaper models for profiling (gpt-3.5-turbo)

## Limitations

1. **Network Variability**: LLM API latency varies by:
   - Time of day
   - Geographic location
   - API load
   - Model availability

2. **Cold Starts**: First calls may be slower due to:
   - Python module loading
   - Model initialization
   - Connection establishment

3. **Rate Limits**: High iteration counts may hit:
   - API rate limits (requests/min)
   - Token rate limits
   - Account quotas

4. **Non-Deterministic**: Results vary across runs due to:
   - Network conditions
   - API backend routing
   - System load

## Extending This Example

### Add Custom Metrics
```rust
struct BenchmarkMetrics {
    latencies: Vec<Duration>,
    token_counts: Vec<usize>,
    error_rates: Vec<f64>,
}
```

### Profile Specific Modules
```rust
benchmark_module("dspy.ReAct", iterations);
benchmark_module("dspy.ProgramOfThought", iterations);
```

### Export Results
```rust
// Save to JSON for analysis
serde_json::to_writer_pretty(
    File::create("benchmark_results.json")?,
    &metrics
)?;
```

### Compare Model Performance
```rust
benchmark_with_model("gpt-3.5-turbo", iterations);
benchmark_with_model("gpt-4", iterations);
```

## Related Examples

- `basic-dspy-call/`: Simple DSPy integration
- `signature-types/`: Type-safe DSPy signatures
- `error-handling/`: Robust error handling patterns
- `async-patterns/`: Asynchronous DSPy calls

## References

- [PyO3 Performance Guide](https://pyo3.rs/main/performance.html)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [GIL Management Best Practices](https://pyo3.rs/main/parallelism.html)
