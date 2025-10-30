"""
Property-based tests using hypothesis
"""
from hypothesis import given, strategies as st, assume
from property_testing import (
    sum_numbers,
    reverse_list,
    sort_list,
    is_sorted,
    scale,
)


class TestSumProperties:
    """Property tests for sum function"""

    @given(st.lists(st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6)))
    def test_sum_matches_builtin(self, data):
        """Property: Rust sum should match Python sum."""
        result = sum_numbers(data)
        expected = sum(data)
        assert abs(result - expected) < 1e-6

    @given(st.floats(allow_nan=False, allow_infinity=False), st.floats(allow_nan=False, allow_infinity=False))
    def test_sum_commutative(self, a, b):
        """Property: Sum is commutative."""
        assume(abs(a) < 1e6 and abs(b) < 1e6)
        result1 = sum_numbers([a, b])
        result2 = sum_numbers([b, a])
        assert abs(result1 - result2) < 1e-10

    @given(st.lists(st.floats(allow_nan=False, allow_infinity=False, min_value=0, max_value=1e6)))
    def test_sum_positive_for_positive_data(self, data):
        """Property: Sum of positive numbers is non-negative."""
        result = sum_numbers(data)
        assert result >= 0


class TestReverseProperties:
    """Property tests for reverse function"""

    @given(st.lists(st.integers()))
    def test_reverse_is_involution(self, data):
        """Property: Reversing twice returns original."""
        reversed_once = reverse_list(data)
        reversed_twice = reverse_list(reversed_once)
        assert reversed_twice == data

    @given(st.lists(st.integers()))
    def test_reverse_preserves_length(self, data):
        """Property: Reverse preserves length."""
        result = reverse_list(data)
        assert len(result) == len(data)

    @given(st.lists(st.integers()))
    def test_reverse_preserves_elements(self, data):
        """Property: Reverse preserves all elements."""
        result = reverse_list(data)
        assert sorted(result) == sorted(data)


class TestSortProperties:
    """Property tests for sort function"""

    @given(st.lists(st.integers()))
    def test_sort_is_sorted(self, data):
        """Property: Sorted result is actually sorted."""
        result = sort_list(data)
        assert is_sorted(result)

    @given(st.lists(st.integers()))
    def test_sort_is_idempotent(self, data):
        """Property: Sorting twice gives same result as sorting once."""
        sorted_once = sort_list(data)
        sorted_twice = sort_list(sorted_once)
        assert sorted_once == sorted_twice

    @given(st.lists(st.integers()))
    def test_sort_preserves_length(self, data):
        """Property: Sort preserves length."""
        result = sort_list(data)
        assert len(result) == len(data)

    @given(st.lists(st.integers()))
    def test_sort_preserves_elements(self, data):
        """Property: Sort preserves all elements."""
        result = sort_list(data)
        assert sorted(data) == result


class TestScaleProperties:
    """Property tests for scale function"""

    @given(st.lists(st.floats(allow_nan=False, allow_infinity=False, min_value=-100, max_value=100)),
           st.floats(allow_nan=False, allow_infinity=False, min_value=-10, max_value=10))
    def test_scale_distributive(self, data, factor):
        """Property: scale(data, f) has sum equal to sum(data) * f."""
        scaled = scale(data, factor)
        sum_then_scale = sum(data) * factor
        scale_then_sum = sum(scaled)
        assert abs(sum_then_scale - scale_then_sum) < 1e-6

    @given(st.lists(st.floats(allow_nan=False, allow_infinity=False, min_value=-100, max_value=100)))
    def test_scale_identity(self, data):
        """Property: Scaling by 1 is identity."""
        result = scale(data, 1.0)
        for i, val in enumerate(data):
            assert abs(result[i] - val) < 1e-10

    @given(st.lists(st.floats(allow_nan=False, allow_infinity=False, min_value=-100, max_value=100)))
    def test_scale_zero(self, data):
        """Property: Scaling by 0 gives all zeros."""
        result = scale(data, 0.0)
        assert all(abs(x) < 1e-10 for x in result)

    @given(st.lists(st.floats(allow_nan=False, allow_infinity=False, min_value=-100, max_value=100)),
           st.floats(allow_nan=False, allow_infinity=False, min_value=-10, max_value=10))
    def test_scale_preserves_length(self, data, factor):
        """Property: Scale preserves length."""
        result = scale(data, factor)
        assert len(result) == len(data)
