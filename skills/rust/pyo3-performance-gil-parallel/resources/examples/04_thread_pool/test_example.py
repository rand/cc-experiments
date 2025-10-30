"""
Test suite for custom thread pool implementation.
"""
import thread_pool


def test_thread_pool_basic():
    """Test basic thread pool functionality."""
    pool = thread_pool.ThreadPool(size=4)

    assert pool.size() == 4

    tasks = [float(x) for x in range(10)]
    results = pool.execute_batch(tasks)

    expected = [x * x for x in tasks]
    assert sorted(results) == sorted(expected)

    pool.shutdown()
    print(f"ThreadPool (size=4) processed {len(tasks)} tasks successfully")


def test_thread_pool_large_batch():
    """Test thread pool with large batch."""
    pool = thread_pool.ThreadPool(size=8)

    tasks = [float(x) for x in range(10000)]
    results = pool.execute_batch(tasks)

    assert len(results) == len(tasks)
    expected = [x * x for x in tasks]
    assert sorted(results) == sorted(expected)

    print(f"\nThreadPool processed {len(tasks)} tasks")
    print(f"  Pool size: {pool.size()}")
    print(f"  Results match: {sorted(results) == sorted(expected)}")

    pool.shutdown()


def test_task_queue():
    """Test task queue with parallel processing."""
    tasks = [float(x) for x in range(100)]
    queue = thread_pool.TaskQueue(tasks)

    assert queue.remaining() == 100

    results = queue.process_parallel(thread_count=4)

    assert queue.remaining() == 0
    assert len(results) == 100

    expected = [x * x for x in tasks]
    assert sorted(results) == sorted(expected)

    print(f"\nTaskQueue processed {len(tasks)} tasks with 4 threads")


def test_work_stealing():
    """Test work-stealing implementation."""
    tasks = [float(x) for x in range(1000)]

    results = thread_pool.process_work_stealing(tasks, thread_count=4)

    expected = [x * x for x in tasks]
    assert sorted(results) == sorted(expected)

    print(f"\nWork-stealing processed {len(tasks)} tasks with 4 threads")


def test_adaptive_parallel():
    """Test adaptive thread pool sizing."""
    test_sizes = [100, 5000, 200000]

    print("\nAdaptive parallel processing:")
    for size in test_sizes:
        tasks = [float(x) for x in range(size)]
        results = thread_pool.adaptive_parallel(tasks)

        expected = [x * x for x in tasks]
        assert sorted(results) == sorted(expected)

        print(f"  Size {size:>6}: processed successfully")


def test_empty_tasks():
    """Test handling of empty task list."""
    results = thread_pool.process_work_stealing([], thread_count=4)
    assert results == []

    results = thread_pool.adaptive_parallel([])
    assert results == []

    print("\nEmpty task handling: OK")


def test_single_thread():
    """Test thread pool with single thread."""
    pool = thread_pool.ThreadPool(size=1)

    tasks = [float(x) for x in range(10)]
    results = pool.execute_batch(tasks)

    expected = [x * x for x in tasks]
    assert sorted(results) == sorted(expected)

    pool.shutdown()
    print("\nSingle-threaded pool: OK")


def test_thread_pool_context():
    """Test thread pool lifecycle management."""
    pool = thread_pool.ThreadPool(size=4)
    tasks = [float(x) for x in range(100)]

    # First batch
    results1 = pool.execute_batch(tasks)
    assert len(results1) == 100

    # Second batch
    results2 = pool.execute_batch(tasks)
    assert len(results2) == 100

    pool.shutdown()
    print("\nThread pool reuse: OK")


def benchmark_thread_pool_sizes():
    """Benchmark different thread pool sizes."""
    import time

    tasks = [float(x) for x in range(50000)]

    print("\nThread pool size comparison:")
    for size in [1, 2, 4, 8]:
        pool = thread_pool.ThreadPool(size=size)

        start = time.time()
        results = pool.execute_batch(tasks)
        elapsed = time.time() - start

        pool.shutdown()

        print(f"  Size {size}: {elapsed:.4f}s ({len(results)} tasks)")


if __name__ == "__main__":
    print("=" * 60)
    print("Thread Pool Tests")
    print("=" * 60)

    test_thread_pool_basic()
    test_thread_pool_large_batch()
    test_task_queue()
    test_work_stealing()
    test_adaptive_parallel()
    test_empty_tasks()
    test_single_thread()
    test_thread_pool_context()
    benchmark_thread_pool_sizes()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
