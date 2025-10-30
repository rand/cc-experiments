"""
Integration tests combining multiple functions
"""
import pytest
from production_suite import compute_statistics, process_with_validation, parallel_process


@pytest.mark.integration
class TestWorkflows:
    """Integration tests for complete workflows"""

    def test_stats_then_process(self):
        """Test computing stats then processing data."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]

        stats = compute_statistics(data)
        mean = stats["mean"]

        min_val = mean - stats["std_dev"]
        max_val = mean + stats["std_dev"]

        filtered = [x for x in data if min_val <= x <= max_val]
        result = process_with_validation(filtered, min_val, max_val)

        assert len(result) > 0
        assert all(r >= min_val * min_val for r in result)

    def test_parallel_then_stats(self):
        """Test parallel processing followed by statistics."""
        batches = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]

        batch_sums = parallel_process(batches)
        stats = compute_statistics(batch_sums)

        assert stats["count"] == 3
        assert stats["sum"] == sum(batch_sums)

    def test_error_recovery(self):
        """Test error handling and recovery."""
        try:
            process_with_validation([1.0, 100.0], 0.0, 10.0)
        except ValueError:
            valid_data = [1.0, 5.0, 9.0]
            result = process_with_validation(valid_data, 0.0, 10.0)
            assert result == [1.0, 25.0, 81.0]


@pytest.mark.integration
@pytest.mark.slow
class TestLargeScale:
    """Large-scale integration tests"""

    def test_large_dataset(self):
        """Test with large dataset."""
        data = list(range(100000))
        data_float = [float(x) for x in data]

        stats = compute_statistics(data_float)
        assert stats["count"] == 100000

    def test_many_batches(self):
        """Test with many parallel batches."""
        batches = [[float(x) for x in range(100)] for _ in range(1000)]
        results = parallel_process(batches)
        assert len(results) == 1000
