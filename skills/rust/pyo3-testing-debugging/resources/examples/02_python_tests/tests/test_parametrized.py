"""
Parameterized tests for python_tests module
"""
import pytest
from python_tests import compute_stats, filter_above, normalize


@pytest.mark.parametrize("input_data,expected_sum,expected_count", [
    ([1.0, 2.0, 3.0], 6.0, 3),
    ([0.0], 0.0, 1),
    ([], 0.0, 0),
    ([1.5, 2.5], 4.0, 2),
    ([-1.0, 1.0], 0.0, 2),
    ([100.0, 200.0, 300.0], 600.0, 3),
])
def test_sum_cases(input_data, expected_sum, expected_count):
    """Test multiple sum computation cases."""
    result = compute_stats(input_data)
    assert result["sum"] == expected_sum
    assert result["count"] == expected_count


@pytest.mark.parametrize("data,threshold,expected", [
    ([1.0, 2.0, 3.0, 4.0, 5.0], 3.0, [4.0, 5.0]),
    ([1.0, 2.0, 3.0, 4.0, 5.0], 0.0, [1.0, 2.0, 3.0, 4.0, 5.0]),
    ([1.0, 2.0, 3.0, 4.0, 5.0], 10.0, []),
    ([], 5.0, []),
    ([5.0], 3.0, [5.0]),
    ([5.0], 5.0, []),
])
def test_filter_cases(data, threshold, expected):
    """Test multiple filtering cases."""
    result = filter_above(data, threshold)
    assert result == expected


@pytest.mark.parametrize("data", [
    [1.0, 2.0, 3.0, 4.0, 5.0],
    [0.0, 100.0],
    [-10.0, -5.0, 0.0, 5.0, 10.0],
    [1.5, 2.7, 3.2, 4.8],
])
def test_normalize_range(data):
    """Test that normalization always produces values in [0, 1]."""
    result = normalize(data)

    assert len(result) == len(data)
    assert all(0.0 <= x <= 1.0 for x in result)

    if len(data) > 1:
        # Check that min and max are at boundaries
        assert min(result) == 0.0 or all(x == data[0] for x in data)
        assert max(result) == 1.0 or all(x == data[0] for x in data)


@pytest.mark.parametrize("data,expected_mean", [
    ([1.0, 2.0, 3.0], 2.0),
    ([10.0, 20.0], 15.0),
    ([5.0], 5.0),
    ([-5.0, 5.0], 0.0),
    ([0.0, 0.0, 0.0], 0.0),
])
def test_mean_calculation(data, expected_mean):
    """Test mean calculation for various inputs."""
    result = compute_stats(data)
    assert abs(result["mean"] - expected_mean) < 1e-10


@pytest.mark.parametrize("data,expected_min,expected_max", [
    ([1.0, 2.0, 3.0, 4.0, 5.0], 1.0, 5.0),
    ([5.0, 4.0, 3.0, 2.0, 1.0], 1.0, 5.0),  # Reverse order
    ([-10.0, -5.0, 0.0, 5.0, 10.0], -10.0, 10.0),
    ([42.0], 42.0, 42.0),  # Single value
])
def test_edge_cases(data, expected_min, expected_max):
    """Test min/max computation edge cases."""
    result = compute_stats(data)
    assert result["min"] == expected_min
    assert result["max"] == expected_max


class TestIntegration:
    """Integration tests combining multiple functions"""

    @pytest.mark.parametrize("data", [
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [10.0, 20.0, 30.0, 40.0, 50.0],
        [-5.0, -3.0, -1.0, 1.0, 3.0, 5.0],
    ])
    def test_filter_then_normalize(self, data):
        """Test filtering followed by normalization."""
        # Filter data
        threshold = sum(data) / len(data)  # Use mean as threshold
        filtered = filter_above(data, threshold)

        # Normalize filtered data
        if filtered:
            normalized = normalize(filtered)
            assert len(normalized) == len(filtered)
            assert all(0.0 <= x <= 1.0 for x in normalized)

    @pytest.mark.parametrize("data", [
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [100.0, 200.0, 300.0],
    ])
    def test_stats_then_filter(self, data):
        """Test computing stats then filtering based on mean."""
        stats = compute_stats(data)
        filtered = filter_above(data, stats["mean"])

        # Verify filtered data is above mean
        assert all(x > stats["mean"] for x in filtered)
