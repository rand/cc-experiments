"""Test basic NumPy array operations."""

import numpy as np
import pytest
import basic_numpy


def test_sum_array():
    """Test sum_array function."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = basic_numpy.sum_array(arr)
    assert result == 15.0

    # Empty array
    empty = np.array([])
    assert basic_numpy.sum_array(empty) == 0.0


def test_mean_array():
    """Test mean_array function."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = basic_numpy.mean_array(arr)
    assert result == 3.0

    # Empty array should raise error
    empty = np.array([])
    with pytest.raises(ValueError, match="Cannot compute mean of empty array"):
        basic_numpy.mean_array(empty)


def test_min_max_array():
    """Test min_array and max_array functions."""
    arr = np.array([3.5, 1.2, 5.8, 2.1, 4.9])

    min_val = basic_numpy.min_array(arr)
    assert min_val == 1.2

    max_val = basic_numpy.max_array(arr)
    assert max_val == 5.8

    # Empty arrays should raise errors
    empty = np.array([])
    with pytest.raises(ValueError):
        basic_numpy.min_array(empty)
    with pytest.raises(ValueError):
        basic_numpy.max_array(empty)


def test_multiply_scalar():
    """Test multiply_scalar function."""
    arr = np.array([1.0, 2.0, 3.0, 4.0])
    result = basic_numpy.multiply_scalar(arr, 2.5)

    expected = np.array([2.5, 5.0, 7.5, 10.0])
    np.testing.assert_array_almost_equal(result, expected)


def test_add_arrays():
    """Test add_arrays function."""
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([4.0, 5.0, 6.0])

    result = basic_numpy.add_arrays(a, b)
    expected = np.array([5.0, 7.0, 9.0])
    np.testing.assert_array_almost_equal(result, expected)

    # Mismatched shapes should raise error
    c = np.array([1.0, 2.0])
    with pytest.raises(ValueError, match="Array shapes don't match"):
        basic_numpy.add_arrays(a, c)


def test_dot_product():
    """Test dot_product function."""
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([4.0, 5.0, 6.0])

    result = basic_numpy.dot_product(a, b)
    expected = 1.0*4.0 + 2.0*5.0 + 3.0*6.0  # 32.0
    assert result == expected

    # Verify against NumPy's dot
    np_result = np.dot(a, b)
    assert abs(result - np_result) < 1e-10

    # Mismatched shapes should raise error
    c = np.array([1.0, 2.0])
    with pytest.raises(ValueError, match="Array shapes don't match"):
        basic_numpy.dot_product(a, c)


def test_create_range():
    """Test create_range function."""
    # Forward range
    result = basic_numpy.create_range(0, 5, 1)
    expected = np.array([0, 1, 2, 3, 4])
    np.testing.assert_array_equal(result, expected)

    # Range with step
    result = basic_numpy.create_range(0, 10, 2)
    expected = np.array([0, 2, 4, 6, 8])
    np.testing.assert_array_equal(result, expected)

    # Backward range
    result = basic_numpy.create_range(5, 0, -1)
    expected = np.array([5, 4, 3, 2, 1])
    np.testing.assert_array_equal(result, expected)

    # Zero step should raise error
    with pytest.raises(ValueError, match="Step cannot be zero"):
        basic_numpy.create_range(0, 5, 0)


def test_create_zeros_ones():
    """Test create_zeros and create_ones functions."""
    # Zeros
    zeros = basic_numpy.create_zeros(5)
    expected_zeros = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
    np.testing.assert_array_equal(zeros, expected_zeros)

    # Ones
    ones = basic_numpy.create_ones(5)
    expected_ones = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
    np.testing.assert_array_equal(ones, expected_ones)


def test_validate_range():
    """Test validate_range function."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    # All values within range
    assert basic_numpy.validate_range(arr, 0.0, 10.0) is True

    # Some values outside range
    assert basic_numpy.validate_range(arr, 2.5, 10.0) is False
    assert basic_numpy.validate_range(arr, 0.0, 3.5) is False

    # Exact boundaries
    assert basic_numpy.validate_range(arr, 1.0, 5.0) is True


def test_sum_2d():
    """Test sum_2d function."""
    arr_2d = np.array([[1.0, 2.0, 3.0],
                       [4.0, 5.0, 6.0]])

    result = basic_numpy.sum_2d(arr_2d)
    expected = 21.0  # 1+2+3+4+5+6
    assert result == expected


def test_type_validation():
    """Test that functions handle type mismatches appropriately."""
    # Integer array should work with float functions
    int_arr = np.array([1, 2, 3, 4, 5], dtype=np.int32)

    # This should work due to NumPy's type coercion
    # or raise appropriate errors
    try:
        result = basic_numpy.sum_array(int_arr)
        # If it works, verify the result
        assert result == 15.0
    except TypeError:
        # Type error is also acceptable
        pass


def test_large_array_performance():
    """Test with larger arrays to ensure basic performance."""
    large_arr = np.random.rand(10000)

    # These should complete quickly
    sum_val = basic_numpy.sum_array(large_arr)
    assert sum_val > 0

    mean_val = basic_numpy.mean_array(large_arr)
    assert 0 < mean_val < 1


if __name__ == "__main__":
    test_sum_array()
    test_mean_array()
    test_min_max_array()
    test_multiply_scalar()
    test_add_arrays()
    test_dot_product()
    test_create_range()
    test_create_zeros_ones()
    test_validate_range()
    test_sum_2d()
    test_type_validation()
    test_large_array_performance()
    print("All tests passed!")
