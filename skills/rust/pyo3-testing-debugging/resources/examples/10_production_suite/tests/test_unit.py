"""
Unit tests for production_suite
"""
import pytest
from production_suite import compute_statistics, process_with_validation, parallel_process


@pytest.mark.unit
class TestComputeStatistics:
    """Unit tests for statistics computation"""

    def test_basic_statistics(self):
        """Test basic statistics computation."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        stats = compute_statistics(data)

        assert stats["count"] == 5
        assert stats["sum"] == 15.0
        assert stats["mean"] == 3.0
        assert "variance" in stats
        assert "std_dev" in stats

    def test_empty_data_error(self):
        """Test that empty data raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            compute_statistics([])

    def test_nan_handling(self):
        """Test that NaN values are rejected."""
        with pytest.raises(ValueError, match="NaN"):
            compute_statistics([1.0, float('nan'), 3.0])

    @pytest.mark.parametrize("data,expected_sum", [
        ([1.0, 2.0, 3.0], 6.0),
        ([0.0], 0.0),
        ([-1.0, 1.0], 0.0),
    ])
    def test_sum_calculation(self, data, expected_sum):
        """Test sum calculation with various inputs."""
        stats = compute_statistics(data)
        assert stats["sum"] == expected_sum


@pytest.mark.unit
class TestProcessWithValidation:
    """Unit tests for validated processing"""

    def test_valid_processing(self):
        """Test processing with valid data."""
        data = [1.0, 2.0, 3.0]
        result = process_with_validation(data, 0.0, 10.0)
        assert result == [1.0, 4.0, 9.0]

    def test_out_of_range_error(self):
        """Test that out-of-range values raise error."""
        with pytest.raises(ValueError, match="outside range"):
            process_with_validation([1.0, 15.0], 0.0, 10.0)

    def test_invalid_range_error(self):
        """Test that invalid range raises error."""
        with pytest.raises(ValueError, match="Min cannot exceed max"):
            process_with_validation([5.0], 10.0, 5.0)


@pytest.mark.unit
class TestParallelProcess:
    """Unit tests for parallel processing"""

    def test_parallel_sum(self):
        """Test parallel batch processing."""
        batches = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        results = parallel_process(batches)
        assert results == [3.0, 7.0, 11.0]

    def test_empty_batches_error(self):
        """Test that empty batches raise error."""
        with pytest.raises(ValueError, match="No batches"):
            parallel_process([])
