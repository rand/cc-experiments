"""
Test suite for atomic operations and lock-free programming.
"""
import atomic_operations


def test_atomic_counter():
    """Test atomic counter operations."""
    counter = atomic_operations.AtomicCounter(0)

    assert counter.get() == 0

    counter.increment()
    assert counter.get() == 1

    counter.add(10)
    assert counter.get() == 11

    counter.set(100)
    assert counter.get() == 100

    print(f"AtomicCounter: Basic operations OK")


def test_atomic_counter_cas():
    """Test compare-and-swap operation."""
    counter = atomic_operations.AtomicCounter(10)

    # Successful CAS
    result = counter.compare_and_swap(10, 20)
    assert result == Ok(10) or isinstance(result, tuple)  # Returns Ok or (old, success)
    assert counter.get() == 20

    # Failed CAS
    result = counter.compare_and_swap(10, 30)
    assert counter.get() == 20  # Unchanged

    print(f"AtomicCounter: Compare-and-swap OK")


def test_atomic_counter_parallel():
    """Test atomic counter with parallel increments."""
    counter = atomic_operations.AtomicCounter(0)

    threads = 4
    increments = 10000

    final_value = counter.parallel_increment(threads, increments)

    expected = threads * increments
    assert final_value == expected

    print(f"\nAtomicCounter: Parallel increment")
    print(f"  Threads: {threads}")
    print(f"  Increments per thread: {increments}")
    print(f"  Final value: {final_value}")
    print(f"  Expected: {expected}")
    print(f"  No race conditions: {final_value == expected}")


def test_atomic_flag():
    """Test atomic boolean flag."""
    flag = atomic_operations.AtomicFlag(False)

    assert flag.get() == False

    flag.set(True)
    assert flag.get() == True

    old = flag.swap(False)
    assert old == True
    assert flag.get() == False

    print(f"\nAtomicFlag: Basic operations OK")


def test_atomic_stats():
    """Test lock-free statistics collector."""
    stats = atomic_operations.AtomicStats()

    values = [10, 20, 30, 40, 50]
    for v in values:
        stats.record(v)

    assert stats.count() == 5
    assert stats.sum() == 150
    assert stats.mean() == 30.0
    assert stats.min() == 10
    assert stats.max() == 50

    print(f"\nAtomicStats: {stats.summary()}")


def test_atomic_stats_parallel():
    """Test lock-free stats with parallel recording."""
    stats = atomic_operations.AtomicStats()

    values = list(range(1, 10001))
    stats.parallel_record(values)

    assert stats.count() == 10000
    assert stats.sum() == sum(values)
    assert stats.min() == 1
    assert stats.max() == 10000

    print(f"\nAtomicStats (parallel): {stats.summary()}")


def test_progress_tracking():
    """Test lock-free progress tracking."""
    total = 100000
    thread_count = 4

    counter = atomic_operations.parallel_with_progress(total, thread_count)

    assert counter.get() == total

    print(f"\nProgress tracking: {counter.get()}/{total} completed")


def test_atomic_vs_mutex_benchmark():
    """Benchmark atomic vs mutex performance."""
    increments = 50000
    thread_count = 4

    atomic_time, mutex_time = atomic_operations.benchmark_atomic_vs_mutex(
        increments, thread_count
    )

    speedup = mutex_time / atomic_time

    print(f"\nAtomic vs Mutex Benchmark:")
    print(f"  Increments: {increments} per thread")
    print(f"  Threads: {thread_count}")
    print(f"  Atomic: {atomic_time:.6f}s")
    print(f"  Mutex:  {mutex_time:.6f}s")
    print(f"  Speedup: {speedup:.2f}x")

    # Atomics should be faster in high contention scenarios
    assert atomic_time < mutex_time * 1.5  # Allow some variance


def test_concurrent_stats():
    """Test statistical correctness under high concurrency."""
    import random

    stats = atomic_operations.AtomicStats()

    # Generate test data
    values = [random.randint(1, 1000) for _ in range(50000)]

    # Record in parallel
    stats.parallel_record(values)

    # Verify correctness
    assert stats.count() == len(values)
    assert stats.sum() == sum(values)
    assert abs(stats.mean() - sum(values) / len(values)) < 0.1
    assert stats.min() == min(values)
    assert stats.max() == max(values)

    print(f"\nConcurrent stats (50k values): All invariants maintained")


def test_high_contention():
    """Test atomic operations under high contention."""
    counter = atomic_operations.AtomicCounter(0)

    threads = 16
    increments = 5000

    final_value = counter.parallel_increment(threads, increments)

    expected = threads * increments
    assert final_value == expected

    print(f"\nHigh contention test ({threads} threads, {increments} ops each):")
    print(f"  No race conditions: {final_value == expected}")


if __name__ == "__main__":
    print("=" * 60)
    print("Atomic Operations Tests")
    print("=" * 60)

    test_atomic_counter()
    test_atomic_counter_cas()
    test_atomic_counter_parallel()
    test_atomic_flag()
    test_atomic_stats()
    test_atomic_stats_parallel()
    test_progress_tracking()
    test_atomic_vs_mutex_benchmark()
    test_concurrent_stats()
    test_high_contention()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
