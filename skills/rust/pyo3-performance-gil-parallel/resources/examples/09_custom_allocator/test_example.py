"""Test suite for custom allocator patterns."""
import custom_allocator

def test_all():
    # Buffer pool
    pool = custom_allocator.BufferPool(size=1024, capacity=10)
    batches = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    results = pool.process_batch(batches)
    assert results == [[1.0, 4.0, 9.0], [16.0, 25.0, 36.0]]

    # Sliding window
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = custom_allocator.sliding_window_sum(data, window=3)
    assert result == [6.0, 9.0, 12.0]

    # Preallocated transform
    data = [4.0, 9.0, 16.0, 25.0]
    result = custom_allocator.parallel_transform_preallocated(data)
    assert result == [2.0, 3.0, 4.0, 5.0]

    # Arena batch processing
    batches = [[1.0, 2.0], [3.0, 4.0]]
    result = custom_allocator.batch_process_arena(batches)
    assert sorted(result) == [1.0, 4.0, 9.0, 16.0]

    # Object pool
    pool = custom_allocator.ObjectPool(object_size=100)
    items = [1.0, 2.0, 3.0]
    results = pool.process_with_pooling(items)
    assert len(results) == 3

    print("All custom allocator tests passed!")

if __name__ == "__main__":
    test_all()
