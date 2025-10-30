"""
Test suite for performance timing utilities.
Demonstrates various benchmarking and profiling techniques.
"""
import time
import performance_timing


def test_timer_basic():
    """Test basic timer functionality."""
    timer = performance_timing.Timer("test_operation")

    # Simulate work
    time.sleep(0.1)

    elapsed = timer.elapsed()
    assert 0.09 < elapsed < 0.15  # Allow some variance

    result = timer.stop(iterations=10)
    assert result.name == "test_operation"
    assert result.iterations == 10
    assert result.per_iteration() > 0
    assert result.ops_per_second() > 0

    print(f"\nBasic Timer: {result}")


def test_timer_context_manager():
    """Test timer as context manager."""
    with performance_timing.Timer("context_test") as timer:
        time.sleep(0.05)
        elapsed = timer.elapsed()

    assert 0.04 < elapsed < 0.1
    print(f"Context Manager Timer: {elapsed:.4f}s")


def test_benchmark_function():
    """Test benchmarking a Python function."""

    def sample_function():
        return sum(range(1000))

    result = performance_timing.benchmark(
        "sample_function",
        sample_function,
        iterations=100
    )

    assert result.name == "sample_function"
    assert result.iterations == 100
    assert result.duration_secs > 0

    print(f"\nBenchmark: {result}")
    print(f"  Per iteration: {result.per_iteration():.6f}s")
    print(f"  Ops/sec: {result.ops_per_second():.2f}")


def test_compare_seq_vs_parallel():
    """Test sequential vs parallel comparison."""
    data = [float(x) for x in range(100000)]
    iterations = 10

    seq_result, par_result = performance_timing.compare_seq_vs_parallel(
        data, iterations
    )

    print(f"\nSequential vs Parallel (n={len(data)}, iterations={iterations}):")
    print(f"  Sequential: {seq_result.duration_secs:.4f}s")
    print(f"  Parallel:   {par_result.duration_secs:.4f}s")
    print(f"  Speedup:    {seq_result.duration_secs / par_result.duration_secs:.2f}x")

    assert seq_result.iterations == par_result.iterations == iterations


def test_profiler():
    """Test profiler for multiple measurements."""
    profiler = performance_timing.Profiler()

    # Simulate multiple operations
    operations = [
        ("operation_a", 0.1),
        ("operation_b", 0.2),
        ("operation_c", 0.05),
    ]

    for name, duration in operations:
        time.sleep(duration)
        profiler.measure(name, duration)

    results = profiler.results()
    assert len(results) == 3

    summary = profiler.summary()
    print(f"\nProfiler Summary:")
    print(summary)

    assert "operation_a" in summary
    assert "operation_b" in summary
    assert "operation_c" in summary


def test_benchmark_with_warmup():
    """Test benchmark with warmup iterations."""

    def sample_function():
        return sum(range(1000))

    result = performance_timing.benchmark_with_warmup(
        "warmup_test",
        sample_function,
        warmup=10,
        iterations=50
    )

    assert result.iterations == 50
    print(f"\nBenchmark with Warmup: {result}")


def test_statistical_benchmark():
    """Test statistical benchmark with multiple runs."""

    def sample_function():
        return sum(range(5000))

    mean, median, min_time, max_time = performance_timing.benchmark_statistical(
        "statistical_test",
        sample_function,
        runs=20,
        iterations_per_run=10
    )

    print(f"\nStatistical Benchmark (20 runs, 10 iterations each):")
    print(f"  Mean:   {mean:.6f}s")
    print(f"  Median: {median:.6f}s")
    print(f"  Min:    {min_time:.6f}s")
    print(f"  Max:    {max_time:.6f}s")
    print(f"  Range:  {(max_time - min_time) / mean * 100:.1f}% of mean")

    assert min_time <= median <= max_time
    assert min_time <= mean <= max_time


def test_memory_throughput():
    """Test memory throughput measurement."""
    size = 10_000_000  # 10M elements
    iterations = 10

    throughput = performance_timing.measure_memory_throughput(size, iterations)

    print(f"\nMemory Throughput (size={size}, iterations={iterations}):")
    print(f"  Throughput: {throughput:.2f} GB/s")

    # Typical memory bandwidth: 10-100 GB/s depending on hardware
    assert throughput > 1.0  # At least 1 GB/s


def test_real_world_scenario():
    """Test a real-world performance comparison scenario."""

    def compute_primes_python(n):
        """Python prime computation for comparison."""
        primes = []
        for num in range(2, n + 1):
            is_prime = True
            for p in primes:
                if p * p > num:
                    break
                if num % p == 0:
                    is_prime = False
                    break
            if is_prime:
                primes.append(num)
        return len(primes)

    n = 5000

    # Benchmark Python version
    python_result = performance_timing.benchmark(
        "Python primes",
        lambda: compute_primes_python(n),
        iterations=5
    )

    print(f"\nReal-world Comparison (computing primes up to {n}):")
    print(f"  Python: {python_result.duration_secs:.4f}s")
    print(f"  Per iteration: {python_result.per_iteration():.6f}s")


def test_timer_result_repr():
    """Test TimerResult string representation."""
    result = performance_timing.Timer("test").stop(iterations=100)
    repr_str = repr(result)

    assert "TimerResult" in repr_str
    assert "test" in repr_str
    assert "iterations=100" in repr_str

    print(f"\nTimerResult repr: {repr_str}")


if __name__ == "__main__":
    print("=" * 60)
    print("Performance Timing Tests")
    print("=" * 60)

    test_timer_basic()
    test_timer_context_manager()
    test_benchmark_function()
    test_compare_seq_vs_parallel()
    test_profiler()
    test_benchmark_with_warmup()
    test_statistical_benchmark()
    test_memory_throughput()
    test_real_world_scenario()
    test_timer_result_repr()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
