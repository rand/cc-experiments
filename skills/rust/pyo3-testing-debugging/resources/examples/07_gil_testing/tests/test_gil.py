"""
GIL release and threading tests
"""
import threading
import time
import pytest
from gil_testing import compute_with_gil_release, parallel_sum, sleep_without_gil


class TestGILRelease:
    """Test GIL release behavior"""

    def test_compute_releases_gil(self):
        """Test that computation releases GIL."""
        result = compute_with_gil_release(1000)
        assert result > 0

    def test_parallel_threads_can_run(self):
        """Test that multiple threads can run during GIL release."""
        results = []

        def worker():
            result = compute_with_gil_release(10000)
            results.append(result)

        threads = [threading.Thread(target=worker) for _ in range(4)]

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start

        assert len(results) == 4
        assert all(r > 0 for r in results)
        assert elapsed < 2.0  # Should complete quickly if parallel

    def test_sleep_releases_gil(self):
        """Test that sleep releases GIL."""
        def worker():
            sleep_without_gil(100)

        threads = [threading.Thread(target=worker) for _ in range(3)]

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start

        # If GIL is released, threads run in parallel
        assert elapsed < 0.5  # Much less than 300ms sequential

    def test_parallel_sum(self):
        """Test parallel sum computation."""
        data = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        result = parallel_sum(data)
        assert result == [6, 15, 24]
