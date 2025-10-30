"""
Test suite for parallel basic operations using Rayon.
Demonstrates Rayon's parallel iterators and operations.
"""
import time
import parallel_basic


def test_parallel_sum():
    """Test parallel sum operation."""
    numbers = list(range(1, 1000001))

    parallel_result = parallel_basic.parallel_sum(numbers)
    sequential_result = parallel_basic.sequential_sum(numbers)

    assert parallel_result == sequential_result == sum(numbers)
    print(f"Sum of {len(numbers)} numbers: {parallel_result}")


def test_parallel_square():
    """Test parallel map operation."""
    numbers = [1.0, 2.0, 3.0, 4.0, 5.0]

    result = parallel_basic.parallel_square(numbers)
    expected = [x * x for x in numbers]

    assert result == expected
    print(f"Squared {numbers[:3]}... = {result[:3]}...")


def test_parallel_filter():
    """Test parallel filter operation."""
    numbers = list(range(100))

    result = parallel_basic.parallel_filter_even(numbers)
    expected = [x for x in numbers if x % 2 == 0]

    assert result == expected
    print(f"Filtered {len(numbers)} numbers to {len(result)} even numbers")


def test_parallel_max():
    """Test parallel reduce operation."""
    numbers = [3.14, 2.71, 1.41, 9.81, 6.28]

    result = parallel_basic.parallel_max(numbers)

    assert result == max(numbers)
    print(f"Maximum of {numbers}: {result}")


def test_parallel_sort():
    """Test parallel sort operation."""
    numbers = [5.0, 2.0, 8.0, 1.0, 9.0, 3.0]

    result = parallel_basic.parallel_sort(numbers)
    expected = sorted(numbers)

    assert result == expected
    print(f"Sorted {len(numbers)} numbers: {result}")


def test_parallel_mandelbrot():
    """Test complex parallel computation."""
    width, height = 800, 600
    max_iter = 100

    start = time.time()
    result = parallel_basic.parallel_mandelbrot(
        width, height,
        -2.5, 1.0,  # x_min, x_max
        -1.0, 1.0,  # y_min, y_max
        max_iter
    )
    elapsed = time.time() - start

    assert len(result) == height
    assert all(len(row) == width for row in result)
    assert all(0 <= pixel <= max_iter for row in result for pixel in row)

    print(f"\nMandelbrot set ({width}x{height}, {max_iter} iterations):")
    print(f"  Computed in: {elapsed:.4f}s")
    print(f"  Pixels/sec:  {width * height / elapsed:.0f}")


def test_parallel_sum_chunked():
    """Test parallel sum with custom chunk sizes."""
    numbers = list(range(1, 10001))

    # Test different chunk sizes
    for chunk_size in [100, 500, 1000]:
        result = parallel_basic.parallel_sum_chunked(numbers, chunk_size)
        assert result == sum(numbers)

    print(f"Chunked sum of {len(numbers)} numbers with various chunk sizes: OK")


def test_parallel_word_count():
    """Test parallel string processing."""
    documents = [
        "The quick brown fox jumps over the lazy dog",
        "Hello world this is a test document",
        "Parallel processing with Rayon is efficient",
        "Python and Rust work great together",
    ]

    result = parallel_basic.parallel_word_count(documents)
    expected = [len(doc.split()) for doc in documents]

    assert result == expected
    print(f"\nWord count for {len(documents)} documents:")
    for i, (doc, count) in enumerate(zip(documents, result)):
        print(f"  Doc {i}: {count} words")


def test_parallel_matrix_multiply():
    """Test nested parallelism with matrix multiplication."""
    # Small matrices for testing
    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[5.0, 6.0], [7.0, 8.0]]

    result = parallel_basic.parallel_matrix_multiply(a, b)

    # Expected: [[19, 22], [43, 50]]
    assert len(result) == 2
    assert len(result[0]) == 2
    assert result[0][0] == 19.0
    assert result[0][1] == 22.0
    assert result[1][0] == 43.0
    assert result[1][1] == 50.0

    print(f"\nMatrix multiplication:")
    print(f"  A: {a}")
    print(f"  B: {b}")
    print(f"  Result: {result}")


def benchmark_parallel_vs_sequential():
    """Benchmark parallel vs sequential execution."""
    numbers = [float(x) for x in range(1, 10000001)]

    print(f"\nBenchmark: Sum of {len(numbers)} numbers")

    # Sequential
    start = time.time()
    seq_result = parallel_basic.sequential_sum(numbers)
    seq_time = time.time() - start

    # Parallel
    start = time.time()
    par_result = parallel_basic.parallel_sum(numbers)
    par_time = time.time() - start

    assert seq_result == par_result

    print(f"  Sequential: {seq_time:.4f}s")
    print(f"  Parallel:   {par_time:.4f}s")
    print(f"  Speedup:    {seq_time / par_time:.2f}x")


if __name__ == "__main__":
    print("=" * 60)
    print("Parallel Basic Operations Tests")
    print("=" * 60)

    test_parallel_sum()
    test_parallel_square()
    test_parallel_filter()
    test_parallel_max()
    test_parallel_sort()
    test_parallel_mandelbrot()
    test_parallel_sum_chunked()
    test_parallel_word_count()
    test_parallel_matrix_multiply()
    benchmark_parallel_vs_sequential()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
