"""
Performance benchmarks using pytest-benchmark
"""
import math
import pytest
from benchmarking import fast_sum, fast_factorial, fast_fibonacci, process_batch


@pytest.fixture
def small_data():
    return list(range(1000))


@pytest.fixture
def large_data():
    return list(range(100000))


def python_sum(data):
    """Pure Python sum for comparison."""
    return sum(data)


def python_factorial(n):
    """Pure Python factorial for comparison."""
    return math.factorial(n)


def python_fibonacci(n):
    """Pure Python fibonacci for comparison."""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


class TestSumBenchmarks:
    """Benchmark sum operations"""

    def test_benchmark_sum_small(self, benchmark, small_data):
        """Benchmark sum with small dataset."""
        result = benchmark(fast_sum, small_data)
        assert result == sum(small_data)

    def test_benchmark_sum_large(self, benchmark, large_data):
        """Benchmark sum with large dataset."""
        result = benchmark(fast_sum, large_data)
        assert result == sum(large_data)

    def test_benchmark_vs_python(self, benchmark, small_data):
        """Compare Rust vs Python sum performance."""
        result = benchmark(fast_sum, small_data)
        assert result == python_sum(small_data)


class TestFactorialBenchmarks:
    """Benchmark factorial operations"""

    def test_benchmark_factorial(self, benchmark):
        """Benchmark factorial calculation."""
        result = benchmark(fast_factorial, 20)
        assert result == python_factorial(20)

    @pytest.mark.parametrize("n", [10, 15, 20])
    def test_benchmark_factorial_sizes(self, benchmark, n):
        """Benchmark factorial with different sizes."""
        result = benchmark(fast_factorial, n)
        assert result == python_factorial(n)


class TestFibonacciBenchmarks:
    """Benchmark fibonacci operations"""

    def test_benchmark_fibonacci(self, benchmark):
        """Benchmark fibonacci calculation."""
        result = benchmark(fast_fibonacci, 30)
        assert result > 0

    @pytest.mark.parametrize("n", [10, 20, 30, 40])
    def test_benchmark_fibonacci_sizes(self, benchmark, n):
        """Benchmark fibonacci with different sizes."""
        result = benchmark(fast_fibonacci, n)
        assert result == python_fibonacci(n)


class TestBatchBenchmarks:
    """Benchmark batch operations"""

    def test_benchmark_batch_processing(self, benchmark):
        """Benchmark batch processing."""
        data = [[float(x) for x in range(100)] for _ in range(100)]
        result = benchmark(process_batch, data)
        assert len(result) == 100


class TestComparisons:
    """Direct performance comparisons"""

    def test_compare_sum_performance(self, benchmark, small_data):
        """Compare Rust and Python sum performance side-by-side."""
        # This test demonstrates the speedup
        rust_result = fast_sum(small_data)
        python_result = python_sum(small_data)
        assert rust_result == python_result

        # Benchmark the Rust version
        benchmark(fast_sum, small_data)
