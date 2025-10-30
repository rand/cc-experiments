"""
Basic functionality tests for python_tests module
"""
import pytest
from python_tests import compute_stats, filter_above, normalize


class TestComputeStats:
    """Tests for compute_stats function"""

    def test_statistics_basic(self, sample_data):
        """Test basic statistics computation."""
        result = compute_stats(sample_data)

        assert result["count"] == 5
        assert result["sum"] == 15.0
        assert result["mean"] == 3.0
        assert result["min"] == 1.0
        assert result["max"] == 5.0

    def test_statistics_empty(self, empty_data):
        """Test empty input handling."""
        result = compute_stats(empty_data)

        assert result["count"] == 0
        assert result["sum"] == 0.0
        assert result["mean"] == 0.0
        assert "min" not in result
        assert "max" not in result

    def test_statistics_single(self, single_value):
        """Test single value."""
        result = compute_stats(single_value)

        assert result["count"] == 1
        assert result["sum"] == 42.0
        assert result["mean"] == 42.0
        assert result["min"] == 42.0
        assert result["max"] == 42.0

    def test_statistics_negative(self, negative_data):
        """Test with negative numbers."""
        result = compute_stats(negative_data)

        assert result["count"] == 7
        assert result["sum"] == 0.0
        assert result["mean"] == 0.0
        assert result["min"] == -5.0
        assert result["max"] == 5.0

    def test_type_error(self):
        """Test type error handling."""
        with pytest.raises(TypeError):
            compute_stats("not a list")

        with pytest.raises(TypeError):
            compute_stats([1, 2, "three"])


class TestFilterAbove:
    """Tests for filter_above function"""

    def test_filter_basic(self, sample_data):
        """Test basic filtering."""
        result = filter_above(sample_data, 3.0)
        assert result == [4.0, 5.0]

    def test_filter_none_match(self, sample_data):
        """Test when no values match."""
        result = filter_above(sample_data, 10.0)
        assert result == []

    def test_filter_all_match(self, sample_data):
        """Test when all values match."""
        result = filter_above(sample_data, 0.0)
        assert result == sample_data

    def test_filter_empty(self, empty_data):
        """Test filtering empty list."""
        result = filter_above(empty_data, 5.0)
        assert result == []


class TestNormalize:
    """Tests for normalize function"""

    def test_normalize_basic(self):
        """Test basic normalization."""
        data = [0.0, 5.0, 10.0]
        result = normalize(data)

        assert len(result) == 3
        assert result[0] == 0.0
        assert result[1] == 0.5
        assert result[2] == 1.0

    def test_normalize_all_same(self):
        """Test normalization when all values are the same."""
        data = [5.0, 5.0, 5.0]
        result = normalize(data)

        assert len(result) == 3
        assert all(x == 0.5 for x in result)

    def test_normalize_empty(self, empty_data):
        """Test normalizing empty list."""
        result = normalize(empty_data)
        assert result == []

    def test_normalize_range(self, sample_data):
        """Test that normalized values are in [0, 1]."""
        result = normalize(sample_data)

        assert all(0.0 <= x <= 1.0 for x in result)
        assert min(result) == 0.0
        assert max(result) == 1.0
