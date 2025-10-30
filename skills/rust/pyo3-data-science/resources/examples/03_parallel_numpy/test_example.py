"""Test parallel NumPy processing with Rayon."""

import numpy as np
import pytest
import parallel_numpy
import time


def test_parallel_square():
    """Test parallel square computation."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = parallel_numpy.parallel_square(arr)
    expected = arr ** 2
    np.testing.assert_array_almost_equal(result, expected)


def test_parallel_transform():
    """Test parallel transformation."""
    arr = np.array([1.0, 2.0, 3.0, 4.0])
    result = parallel_numpy.parallel_transform(arr)

    # Verify computation
    for i, x in enumerate(arr):
        expected = np.sqrt(np.abs(x**3 + x**2 + x))
        assert abs(result[i] - expected) < 1e-10


def test_parallel_sum():
    """Test parallel sum with chunks."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])

    result = parallel_numpy.parallel_sum(arr, chunk_size=2)
    expected = np.sum(arr)

    assert abs(result - expected) < 1e-10


def test_parallel_stats():
    """Test parallel statistics computation."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    sum_val, mean_val, min_val, max_val = parallel_numpy.parallel_stats(arr)

    assert abs(sum_val - np.sum(arr)) < 1e-10
    assert abs(mean_val - np.mean(arr)) < 1e-10
    assert abs(min_val - np.min(arr)) < 1e-10
    assert abs(max_val - np.max(arr)) < 1e-10

    # Empty array should raise error
    empty = np.array([])
    with pytest.raises(ValueError, match="Array is empty"):
        parallel_numpy.parallel_stats(empty)


def test_parallel_filter():
    """Test parallel filtering."""
    arr = np.array([1.0, 5.0, 2.0, 8.0, 3.0, 9.0])

    result = parallel_numpy.parallel_filter(arr, threshold=4.0)
    expected = arr[arr > 4.0]

    np.testing.assert_array_almost_equal(sorted(result), sorted(expected))


def test_parallel_normalize():
    """Test parallel normalization."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    result = parallel_numpy.parallel_normalize(arr)

    # Check mean is close to 0 and std is close to 1
    assert abs(np.mean(result)) < 1e-10
    assert abs(np.std(result) - 1.0) < 1e-10

    # Empty array should raise error
    empty = np.array([])
    with pytest.raises(ValueError, match="Array is empty"):
        parallel_numpy.parallel_normalize(empty)


def test_parallel_multiply():
    """Test parallel element-wise multiplication."""
    a = np.array([1.0, 2.0, 3.0, 4.0])
    b = np.array([5.0, 6.0, 7.0, 8.0])

    result = parallel_numpy.parallel_multiply(a, b)
    expected = a * b

    np.testing.assert_array_almost_equal(result, expected)

    # Mismatched lengths should raise error
    c = np.array([1.0, 2.0])
    with pytest.raises(ValueError, match="Array lengths don't match"):
        parallel_numpy.parallel_multiply(a, c)


def test_parallel_window_sum():
    """Test parallel window sum."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    result = parallel_numpy.parallel_window_sum(arr, window_size=3)
    expected = np.array([6.0, 9.0, 12.0])  # [1+2+3, 2+3+4, 3+4+5]

    np.testing.assert_array_almost_equal(result, expected)

    # Window larger than array should raise error
    with pytest.raises(ValueError, match="Window size larger than array"):
        parallel_numpy.parallel_window_sum(arr, window_size=10)


def test_parallel_cumsum():
    """Test parallel cumulative sum."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    result = parallel_numpy.parallel_cumsum(arr)
    expected = np.cumsum(arr)

    np.testing.assert_array_almost_equal(result, expected)


def test_large_array_performance():
    """Test performance with large arrays."""
    large_arr = np.random.rand(100000)

    # These should complete quickly thanks to parallelization
    start = time.time()
    result = parallel_numpy.parallel_square(large_arr)
    elapsed = time.time() - start

    assert len(result) == len(large_arr)
    print(f"Parallel square on 100k elements: {elapsed:.4f}s")

    # Verify correctness on sample
    np.testing.assert_array_almost_equal(result[:10], large_arr[:10] ** 2)


def test_parallel_vs_sequential():
    """Compare parallel and sequential performance."""
    # Create moderately sized array
    arr = np.random.rand(50000)

    # Parallel version
    start = time.time()
    parallel_result = parallel_numpy.parallel_transform(arr)
    parallel_time = time.time() - start

    # Sequential Python version
    start = time.time()
    sequential_result = np.sqrt(np.abs(arr**3 + arr**2 + arr))
    sequential_time = time.time() - start

    print(f"Parallel: {parallel_time:.4f}s, Sequential: {sequential_time:.4f}s")

    # Results should match
    np.testing.assert_array_almost_equal(parallel_result, sequential_result)


def test_edge_cases():
    """Test edge cases."""
    # Single element
    single = np.array([5.0])
    result = parallel_numpy.parallel_square(single)
    assert result[0] == 25.0

    # Two elements
    pair = np.array([2.0, 3.0])
    result = parallel_numpy.parallel_multiply(pair, pair)
    expected = np.array([4.0, 9.0])
    np.testing.assert_array_almost_equal(result, expected)


if __name__ == "__main__":
    test_parallel_square()
    test_parallel_transform()
    test_parallel_sum()
    test_parallel_stats()
    test_parallel_filter()
    test_parallel_normalize()
    test_parallel_multiply()
    test_parallel_window_sum()
    test_parallel_cumsum()
    test_large_array_performance()
    test_parallel_vs_sequential()
    test_edge_cases()
    print("All tests passed!")
