use pyo3::prelude::*;
use numpy::{PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2, ToPyArray};
use ndarray::{Array1, Array2, s};

/// Transpose a 2D array using ndarray
///
/// Args:
///     array: Input 2D NumPy array
///
/// Returns:
///     Transposed 2D NumPy array
#[pyfunction]
fn transpose<'py>(
    py: Python<'py>,
    array: PyReadonlyArray2<f64>
) -> PyResult<&'py PyArray2<f64>> {
    let arr = array.as_array();
    let transposed = arr.t().to_owned();
    Ok(transposed.to_pyarray(py))
}

/// Matrix multiplication using ndarray
///
/// Args:
///     a: First 2D array (m x n)
///     b: Second 2D array (n x p)
///
/// Returns:
///     Result of matrix multiplication (m x p)
#[pyfunction]
fn matmul<'py>(
    py: Python<'py>,
    a: PyReadonlyArray2<f64>,
    b: PyReadonlyArray2<f64>
) -> PyResult<&'py PyArray2<f64>> {
    let arr_a = a.as_array();
    let arr_b = b.as_array();

    if arr_a.shape()[1] != arr_b.shape()[0] {
        return Err(pyo3::exceptions::PyValueError::new_err(
            format!("Incompatible shapes: {:?} and {:?}", arr_a.shape(), arr_b.shape())
        ));
    }

    let result = arr_a.dot(&arr_b);
    Ok(result.to_pyarray(py))
}

/// Compute row-wise sum of a 2D array
///
/// Args:
///     array: Input 2D NumPy array
///
/// Returns:
///     1D array of row sums
#[pyfunction]
fn sum_rows<'py>(
    py: Python<'py>,
    array: PyReadonlyArray2<f64>
) -> PyResult<&'py PyArray1<f64>> {
    let arr = array.as_array();
    let sums = arr.sum_axis(ndarray::Axis(1));
    Ok(sums.to_pyarray(py))
}

/// Compute column-wise sum of a 2D array
///
/// Args:
///     array: Input 2D NumPy array
///
/// Returns:
///     1D array of column sums
#[pyfunction]
fn sum_cols<'py>(
    py: Python<'py>,
    array: PyReadonlyArray2<f64>
) -> PyResult<&'py PyArray1<f64>> {
    let arr = array.as_array();
    let sums = arr.sum_axis(ndarray::Axis(0));
    Ok(sums.to_pyarray(py))
}

/// Normalize each row to have zero mean and unit variance
///
/// Args:
///     array: Input 2D NumPy array
///
/// Returns:
///     Normalized 2D array
#[pyfunction]
fn normalize_rows<'py>(
    py: Python<'py>,
    array: PyReadonlyArray2<f64>
) -> PyResult<&'py PyArray2<f64>> {
    let arr = array.as_array();
    let mut normalized = arr.to_owned();

    for mut row in normalized.axis_iter_mut(ndarray::Axis(0)) {
        let mean = row.mean().unwrap_or(0.0);
        let std = row.std(0.0);

        if std > 1e-10 {
            row.mapv_inplace(|x| (x - mean) / std);
        } else {
            row.fill(0.0);
        }
    }

    Ok(normalized.to_pyarray(py))
}

/// Element-wise operations using ndarray
///
/// Args:
///     array: Input NumPy array
///
/// Returns:
///     Array with operation applied (array * 2 + 1)
#[pyfunction]
fn element_wise_op<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>
) -> PyResult<&'py PyArray1<f64>> {
    let arr = array.as_array();
    let result = &arr * 2.0 + 1.0;
    Ok(result.to_pyarray(py))
}

/// Extract diagonal from a 2D array
///
/// Args:
///     array: Input 2D NumPy array
///
/// Returns:
///     1D array containing diagonal elements
#[pyfunction]
fn get_diagonal<'py>(
    py: Python<'py>,
    array: PyReadonlyArray2<f64>
) -> PyResult<&'py PyArray1<f64>> {
    let arr = array.as_array();
    let diag = arr.diag().to_owned();
    Ok(diag.to_pyarray(py))
}

/// Reshape a 1D array into a 2D array
///
/// Args:
///     array: Input 1D NumPy array
///     rows: Number of rows
///     cols: Number of columns
///
/// Returns:
///     Reshaped 2D array
#[pyfunction]
fn reshape<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>,
    rows: usize,
    cols: usize
) -> PyResult<&'py PyArray2<f64>> {
    let arr = array.as_array();

    if arr.len() != rows * cols {
        return Err(pyo3::exceptions::PyValueError::new_err(
            format!("Cannot reshape array of size {} into {}x{}", arr.len(), rows, cols)
        ));
    }

    let reshaped = arr.to_owned().into_shape((rows, cols))
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Reshape error: {}", e)))?;

    Ok(reshaped.to_pyarray(py))
}

/// Slice a 2D array
///
/// Args:
///     array: Input 2D NumPy array
///     row_start: Starting row index
///     row_end: Ending row index (exclusive)
///     col_start: Starting column index
///     col_end: Ending column index (exclusive)
///
/// Returns:
///     Sliced 2D array
#[pyfunction]
fn slice_array<'py>(
    py: Python<'py>,
    array: PyReadonlyArray2<f64>,
    row_start: usize,
    row_end: usize,
    col_start: usize,
    col_end: usize
) -> PyResult<&'py PyArray2<f64>> {
    let arr = array.as_array();

    let sliced = arr.slice(s![row_start..row_end, col_start..col_end]).to_owned();
    Ok(sliced.to_pyarray(py))
}

/// Compute outer product of two 1D arrays
///
/// Args:
///     a: First 1D array
///     b: Second 1D array
///
/// Returns:
///     2D array representing outer product
#[pyfunction]
fn outer_product<'py>(
    py: Python<'py>,
    a: PyReadonlyArray1<f64>,
    b: PyReadonlyArray1<f64>
) -> PyResult<&'py PyArray2<f64>> {
    let arr_a = a.as_array();
    let arr_b = b.as_array();

    let m = arr_a.len();
    let n = arr_b.len();

    let mut result = Array2::<f64>::zeros((m, n));

    for i in 0..m {
        for j in 0..n {
            result[[i, j]] = arr_a[i] * arr_b[j];
        }
    }

    Ok(result.to_pyarray(py))
}

/// Create identity matrix
///
/// Args:
///     size: Size of the square identity matrix
///
/// Returns:
///     Identity matrix as 2D array
#[pyfunction]
fn identity<'py>(py: Python<'py>, size: usize) -> PyResult<&'py PyArray2<f64>> {
    let identity = Array2::<f64>::eye(size);
    Ok(identity.to_pyarray(py))
}

/// Stack arrays vertically (row-wise)
///
/// Args:
///     a: First 2D array
///     b: Second 2D array
///
/// Returns:
///     Vertically stacked array
#[pyfunction]
fn vstack<'py>(
    py: Python<'py>,
    a: PyReadonlyArray2<f64>,
    b: PyReadonlyArray2<f64>
) -> PyResult<&'py PyArray2<f64>> {
    let arr_a = a.as_array();
    let arr_b = b.as_array();

    if arr_a.shape()[1] != arr_b.shape()[1] {
        return Err(pyo3::exceptions::PyValueError::new_err(
            format!("Column dimensions must match: {} vs {}", arr_a.shape()[1], arr_b.shape()[1])
        ));
    }

    let result = ndarray::concatenate(ndarray::Axis(0), &[arr_a.view(), arr_b.view()])
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Stack error: {}", e)))?;

    Ok(result.to_pyarray(py))
}

/// Module initialization
#[pymodule]
fn ndarray_ops(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(transpose, m)?)?;
    m.add_function(wrap_pyfunction!(matmul, m)?)?;
    m.add_function(wrap_pyfunction!(sum_rows, m)?)?;
    m.add_function(wrap_pyfunction!(sum_cols, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_rows, m)?)?;
    m.add_function(wrap_pyfunction!(element_wise_op, m)?)?;
    m.add_function(wrap_pyfunction!(get_diagonal, m)?)?;
    m.add_function(wrap_pyfunction!(reshape, m)?)?;
    m.add_function(wrap_pyfunction!(slice_array, m)?)?;
    m.add_function(wrap_pyfunction!(outer_product, m)?)?;
    m.add_function(wrap_pyfunction!(identity, m)?)?;
    m.add_function(wrap_pyfunction!(vstack, m)?)?;
    Ok(())
}
