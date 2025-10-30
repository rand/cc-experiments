"""Test multi-dimensional array operations with ndarray."""

import numpy as np
import pytest
import ndarray_ops


def test_transpose():
    """Test matrix transpose."""
    arr = np.array([[1.0, 2.0, 3.0],
                    [4.0, 5.0, 6.0]])

    result = ndarray_ops.transpose(arr)
    expected = arr.T

    np.testing.assert_array_almost_equal(result, expected)


def test_matmul():
    """Test matrix multiplication."""
    a = np.array([[1.0, 2.0],
                  [3.0, 4.0]])
    b = np.array([[5.0, 6.0],
                  [7.0, 8.0]])

    result = ndarray_ops.matmul(a, b)
    expected = np.matmul(a, b)

    np.testing.assert_array_almost_equal(result, expected)

    # Test incompatible shapes
    c = np.array([[1.0, 2.0, 3.0],
                  [4.0, 5.0, 6.0]])

    with pytest.raises(ValueError, match="Incompatible shapes"):
        ndarray_ops.matmul(a, c)


def test_sum_rows_cols():
    """Test row-wise and column-wise sums."""
    arr = np.array([[1.0, 2.0, 3.0],
                    [4.0, 5.0, 6.0]])

    row_sums = ndarray_ops.sum_rows(arr)
    expected_rows = np.array([6.0, 15.0])
    np.testing.assert_array_almost_equal(row_sums, expected_rows)

    col_sums = ndarray_ops.sum_cols(arr)
    expected_cols = np.array([5.0, 7.0, 9.0])
    np.testing.assert_array_almost_equal(col_sums, expected_cols)


def test_normalize_rows():
    """Test row normalization."""
    arr = np.array([[1.0, 2.0, 3.0, 4.0],
                    [5.0, 6.0, 7.0, 8.0]])

    result = ndarray_ops.normalize_rows(arr)

    # Check each row has mean close to 0 and std close to 1
    for i in range(result.shape[0]):
        row_mean = np.mean(result[i])
        row_std = np.std(result[i])
        assert abs(row_mean) < 1e-10
        assert abs(row_std - 1.0) < 1e-10


def test_element_wise_op():
    """Test element-wise operations."""
    arr = np.array([1.0, 2.0, 3.0, 4.0])

    result = ndarray_ops.element_wise_op(arr)
    expected = arr * 2.0 + 1.0

    np.testing.assert_array_almost_equal(result, expected)


def test_get_diagonal():
    """Test diagonal extraction."""
    arr = np.array([[1.0, 2.0, 3.0],
                    [4.0, 5.0, 6.0],
                    [7.0, 8.0, 9.0]])

    result = ndarray_ops.get_diagonal(arr)
    expected = np.array([1.0, 5.0, 9.0])

    np.testing.assert_array_almost_equal(result, expected)


def test_reshape():
    """Test array reshaping."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    result = ndarray_ops.reshape(arr, 2, 3)
    expected = arr.reshape(2, 3)

    np.testing.assert_array_almost_equal(result, expected)

    # Test invalid reshape
    with pytest.raises(ValueError, match="Cannot reshape"):
        ndarray_ops.reshape(arr, 2, 2)


def test_slice_array():
    """Test array slicing."""
    arr = np.array([[1.0, 2.0, 3.0, 4.0],
                    [5.0, 6.0, 7.0, 8.0],
                    [9.0, 10.0, 11.0, 12.0]])

    result = ndarray_ops.slice_array(arr, 0, 2, 1, 3)
    expected = arr[0:2, 1:3]

    np.testing.assert_array_almost_equal(result, expected)


def test_outer_product():
    """Test outer product."""
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([4.0, 5.0])

    result = ndarray_ops.outer_product(a, b)
    expected = np.outer(a, b)

    np.testing.assert_array_almost_equal(result, expected)


def test_identity():
    """Test identity matrix creation."""
    result = ndarray_ops.identity(3)
    expected = np.eye(3)

    np.testing.assert_array_almost_equal(result, expected)


def test_vstack():
    """Test vertical stacking."""
    a = np.array([[1.0, 2.0, 3.0],
                  [4.0, 5.0, 6.0]])
    b = np.array([[7.0, 8.0, 9.0]])

    result = ndarray_ops.vstack(a, b)
    expected = np.vstack([a, b])

    np.testing.assert_array_almost_equal(result, expected)

    # Test incompatible shapes
    c = np.array([[1.0, 2.0]])
    with pytest.raises(ValueError, match="Column dimensions must match"):
        ndarray_ops.vstack(a, c)


def test_complex_pipeline():
    """Test a complex operation pipeline."""
    # Create a matrix
    arr = np.array([[1.0, 2.0],
                    [3.0, 4.0]])

    # Transpose
    transposed = ndarray_ops.transpose(arr)

    # Multiply with original
    product = ndarray_ops.matmul(arr, transposed)

    # Get diagonal
    diag = ndarray_ops.get_diagonal(product)

    # Verify the result makes sense
    assert len(diag) == 2
    assert all(diag > 0)


def test_broadcasting_behavior():
    """Test operations with different array sizes."""
    # Test matmul with different dimensions
    a = np.array([[1.0, 2.0, 3.0],
                  [4.0, 5.0, 6.0]])  # 2x3
    b = np.array([[7.0, 8.0],
                  [9.0, 10.0],
                  [11.0, 12.0]])  # 3x2

    result = ndarray_ops.matmul(a, b)  # Should be 2x2
    assert result.shape == (2, 2)

    expected = np.matmul(a, b)
    np.testing.assert_array_almost_equal(result, expected)


if __name__ == "__main__":
    test_transpose()
    test_matmul()
    test_sum_rows_cols()
    test_normalize_rows()
    test_element_wise_op()
    test_get_diagonal()
    test_reshape()
    test_slice_array()
    test_outer_product()
    test_identity()
    test_vstack()
    test_complex_pipeline()
    test_broadcasting_behavior()
    print("All tests passed!")
