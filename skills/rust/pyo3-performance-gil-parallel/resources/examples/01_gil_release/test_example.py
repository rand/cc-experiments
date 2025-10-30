"""
Test suite for GIL release example.
Demonstrates the performance impact of releasing the GIL.
"""
import time
import threading
import gil_release


def test_basic_computation():
    """Test basic prime computation functions."""
    n = 1000

    # Both should return the same result
    blocking_result = gil_release.compute_primes_blocking(n)
    releasing_result = gil_release.compute_primes_releasing(n)

    assert blocking_result == releasing_result
    print(f"Found {blocking_result} primes up to {n}")


def test_gil_release_performance():
    """Benchmark GIL release impact on single-threaded performance."""
    n = 5000
    iterations = 5

    blocking_time, releasing_time = gil_release.benchmark_gil_release(n, iterations)

    print(f"\nGIL Release Performance (n={n}, iterations={iterations}):")
    print(f"  Blocking:  {blocking_time:.4f}s")
    print(f"  Releasing: {releasing_time:.4f}s")
    print(f"  Overhead:  {(releasing_time - blocking_time) / blocking_time * 100:.2f}%")


def test_concurrent_execution():
    """Demonstrate that GIL release allows true concurrent execution."""
    n = 5000

    # Test with blocking version - threads will serialize
    start = time.time()
    threads = []
    for _ in range(4):
        t = threading.Thread(target=gil_release.compute_primes_blocking, args=(n,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    blocking_concurrent_time = time.time() - start

    # Test with releasing version - threads can run in parallel
    start = time.time()
    threads = []
    for _ in range(4):
        t = threading.Thread(target=gil_release.compute_primes_releasing, args=(n,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    releasing_concurrent_time = time.time() - start

    print(f"\nConcurrent Execution (4 threads, n={n}):")
    print(f"  Blocking:  {blocking_concurrent_time:.4f}s (threads serialize)")
    print(f"  Releasing: {releasing_concurrent_time:.4f}s (threads parallel)")
    print(f"  Speedup:   {blocking_concurrent_time / releasing_concurrent_time:.2f}x")

    # Releasing should be significantly faster
    assert releasing_concurrent_time < blocking_concurrent_time * 0.8


def test_parallel_compute():
    """Test parallel computation across multiple threads."""
    n = 10000
    thread_count = 4

    results = gil_release.parallel_compute(n, thread_count)

    print(f"\nParallel Compute (n={n}, threads={thread_count}):")
    for i, count in enumerate(results):
        print(f"  Thread {i}: {count} primes")
    print(f"  Total: {sum(results)} primes")

    assert len(results) == thread_count
    assert all(count > 0 for count in results)


def test_sleep_releasing():
    """Test that sleep releases the GIL properly."""
    sleep_time = 0.1
    thread_count = 4

    # Should take approximately sleep_time, not sleep_time * thread_count
    start = time.time()
    threads = []
    for _ in range(thread_count):
        t = threading.Thread(target=gil_release.sleep_releasing, args=(sleep_time,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start

    print(f"\nSleep Releasing ({thread_count} threads, {sleep_time}s each):")
    print(f"  Elapsed: {elapsed:.4f}s")
    print(f"  Expected: ~{sleep_time:.4f}s (parallel)")

    # Should complete in roughly sleep_time (allowing for overhead)
    assert elapsed < sleep_time * 1.5


if __name__ == "__main__":
    print("=" * 60)
    print("GIL Release Example Tests")
    print("=" * 60)

    test_basic_computation()
    test_gil_release_performance()
    test_concurrent_execution()
    test_parallel_compute()
    test_sleep_releasing()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
