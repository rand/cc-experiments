"""Test suite for zero-copy operations."""
import zero_copy

def test_all():
    # In-place processing
    data = [1.0, 2.0, 3.0, 4.0]
    result = zero_copy.process_slice_inplace(data)
    assert result == [1.0, 4.0, 9.0, 16.0]

    # No-copy sum
    assert zero_copy.sum_nocopy([1.0, 2.0, 3.0, 4.0, 5.0]) == 15.0

    # Chunked processing
    data = [4.0, 16.0, 64.0, 256.0]
    result = zero_copy.process_chunked_nocopy(data, chunk_size=2)
    # Each element: (x * 2.0).sqrt()
    expected = [(x * 2.0) ** 0.5 for x in data]
    assert all(abs(a - b) < 0.01 for a, b in zip(result, expected))

    # Matrix-vector multiply
    matrix = [[1.0, 2.0], [3.0, 4.0]]
    vector = [1.0, 2.0]
    result = zero_copy.matvec_multiply(matrix, vector)
    assert result == [5.0, 11.0]

    # Parallel reduce
    sum_val, min_val, max_val, count = zero_copy.parallel_reduce_nocopy([1.0, 2.0, 3.0, 4.0, 5.0])
    assert sum_val == 15.0 and min_val == 1.0 and max_val == 5.0 and count == 5

    print("All zero-copy tests passed!")

if __name__ == "__main__":
    test_all()
