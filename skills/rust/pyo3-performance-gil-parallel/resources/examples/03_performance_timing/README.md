# Example 03: Performance Timing and Benchmarking

This example provides utilities for accurate performance measurement and benchmarking of PyO3 functions, including comparison between sequential and parallel implementations.

## Concepts Covered

- **High-Resolution Timing**: Using Rust's `Instant` for accurate measurements
- **Benchmark Utilities**: Reusable benchmarking functions
- **Statistical Analysis**: Multiple runs with mean/median/min/max
- **Memory Throughput**: Measuring data processing bandwidth
- **Profiling**: Tracking multiple operations with breakdowns

## Key Components

### Timer Class
```python
timer = performance_timing.Timer("operation_name")
# ... do work ...
result = timer.stop(iterations=100)
print(f"Duration: {result.duration_secs}s")
print(f"Per iteration: {result.per_iteration()}s")
print(f"Ops/sec: {result.ops_per_second()}")
```

### Benchmark Function
```python
result = performance_timing.benchmark(
    "function_name",
    lambda: expensive_function(),
    iterations=100
)
```

### Sequential vs Parallel Comparison
```python
seq_result, par_result = performance_timing.compare_seq_vs_parallel(
    data, iterations=10
)
speedup = seq_result.duration_secs / par_result.duration_secs
```

### Profiler
```python
profiler = performance_timing.Profiler()
profiler.measure("step_1", duration1)
profiler.measure("step_2", duration2)
print(profiler.summary())  # Shows breakdown with percentages
```

### Statistical Benchmark
```python
mean, median, min_time, max_time = performance_timing.benchmark_statistical(
    "function_name",
    lambda: function(),
    runs=20,
    iterations_per_run=10
)
```

### Memory Throughput
```python
throughput_gbps = performance_timing.measure_memory_throughput(
    size=10_000_000,
    iterations=10
)
```

## Building and Testing

```bash
# Install and build
pip install maturin
maturin develop --release

# Run tests
python test_example.py
```

## Usage Patterns

### Basic Timing
```python
timer = performance_timing.Timer("my_operation")
result = my_expensive_function()
timer_result = timer.stop(iterations=1)
print(f"Took {timer_result.duration_secs:.4f}s")
```

### Context Manager
```python
with performance_timing.Timer("my_operation") as timer:
    result = my_expensive_function()
    print(f"Elapsed: {timer.elapsed():.4f}s")
```

### Warmup and Multiple Runs
```python
result = performance_timing.benchmark_with_warmup(
    "my_function",
    lambda: my_function(),
    warmup=5,      # Warmup iterations to stabilize caches
    iterations=20  # Actual benchmark iterations
)
```

### Profiling a Pipeline
```python
profiler = performance_timing.Profiler()

timer = performance_timing.Timer("load")
data = load_data()
profiler.measure("load", timer.elapsed())

timer = performance_timing.Timer("process")
result = process_data(data)
profiler.measure("process", timer.elapsed())

timer = performance_timing.Timer("save")
save_result(result)
profiler.measure("save", timer.elapsed())

print(profiler.summary())
# Shows breakdown like:
#   load: 0.500s (25.0%)
#   process: 1.200s (60.0%)
#   save: 0.300s (15.0%)
```

## Performance Tips

### Accurate Measurements
- Use warmup iterations to stabilize CPU caches
- Run multiple iterations to reduce timing noise
- Use statistical benchmarks for variable workloads
- Disable CPU frequency scaling for consistent results

### What to Measure
- **Wall-clock time**: Total elapsed time (what users experience)
- **Operations/second**: Throughput metric
- **Memory throughput**: GB/s for data-intensive operations
- **Per-iteration time**: Latency metric

### Interpreting Results
- **Speedup**: `sequential_time / parallel_time`
- **Efficiency**: `speedup / num_cores` (ideally close to 1.0)
- **Overhead**: Difference between sequential and parallel for small datasets
- **Scalability**: How speedup changes with dataset size

## Common Benchmarking Scenarios

### Compare Python vs Rust
```python
python_result = benchmark("Python", python_impl, iterations=10)
rust_result = benchmark("Rust", rust_impl, iterations=10)
speedup = python_result.duration_secs / rust_result.duration_secs
```

### Find Optimal Chunk Size
```python
for chunk_size in [100, 500, 1000, 5000]:
    result = benchmark(
        f"chunk_{chunk_size}",
        lambda: process_chunked(data, chunk_size),
        iterations=10
    )
    print(f"Chunk {chunk_size}: {result.ops_per_second():.2f} ops/sec")
```

### Measure Scaling
```python
for size in [1_000, 10_000, 100_000, 1_000_000]:
    data = generate_data(size)
    result = benchmark(f"size_{size}", lambda: process(data), iterations=5)
    print(f"Size {size}: {result.per_iteration():.6f}s")
```

## Learning Points

1. **Accurate Timing**: Rust's `Instant` provides nanosecond precision
2. **Warmup Matters**: First few iterations may be slower due to cold caches
3. **Statistical Variation**: Multiple runs reveal performance variance
4. **Memory Bandwidth**: Often the bottleneck for simple operations
5. **Context Matters**: Benchmark in conditions similar to production use

## Next Steps

- Example 04: Custom thread pools with work stealing
- Example 05: Lock-free atomic operations
