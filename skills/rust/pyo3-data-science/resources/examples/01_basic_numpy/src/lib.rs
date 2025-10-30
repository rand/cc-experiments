use pyo3::prelude::*;
use numpy::{PyArray1, PyReadonlyArray1, PyReadonlyArray2};

/// Sum all elements in a 1D NumPy array
///
/// Args:
///     array: Input NumPy array of floats
///
/// Returns:
///     Sum of all elements as f64
#[pyfunction]
fn sum_array(array: PyReadonlyArray1<f64>) -> PyResult<f64> {
    Ok(array.as_slice()?.iter().sum())
}

/// Calculate the mean of a 1D NumPy array
///
/// Args:
///     array: Input NumPy array of floats
///
/// Returns:
///     Mean value or error if array is empty
#[pyfunction]
fn mean_array(array: PyReadonlyArray1<f64>) -> PyResult<f64> {
    let slice = array.as_slice()?;
    if slice.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("Cannot compute mean of empty array"));
    }
    let sum: f64 = slice.iter().sum();
    Ok(sum / slice.len() as f64)
}

/// Find the minimum value in a 1D NumPy array
///
/// Args:
///     array: Input NumPy array of floats
///
/// Returns:
///     Minimum value or error if array is empty
#[pyfunction]
fn min_array(array: PyReadonlyArray1<f64>) -> PyResult<f64> {
    let slice = array.as_slice()?;
    slice.iter()
        .copied()
        .min_by(|a, b| a.partial_cmp(b).unwrap())
        .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("Cannot find min of empty array"))
}

/// Find the maximum value in a 1D NumPy array
///
/// Args:
///     array: Input NumPy array of floats
///
/// Returns:
///     Maximum value or error if array is empty
#[pyfunction]
fn max_array(array: PyReadonlyArray1<f64>) -> PyResult<f64> {
    let slice = array.as_slice()?;
    slice.iter()
        .copied()
        .max_by(|a, b| a.partial_cmp(b).unwrap())
        .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("Cannot find max of empty array"))
}

/// Multiply all elements by a scalar value
///
/// Args:
///     array: Input NumPy array of floats
///     scalar: Value to multiply by
///
/// Returns:
///     New NumPy array with multiplied values
#[pyfunction]
fn multiply_scalar<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>,
    scalar: f64
) -> PyResult<&'py PyArray1<f64>> {
    let slice = array.as_slice()?;
    let result: Vec<f64> = slice.iter().map(|&x| x * scalar).collect();
    Ok(PyArray1::from_vec(py, result))
}

/// Add two NumPy arrays element-wise
///
/// Args:
///     a: First NumPy array
///     b: Second NumPy array
///
/// Returns:
///     New NumPy array with element-wise sum
#[pyfunction]
fn add_arrays<'py>(
    py: Python<'py>,
    a: PyReadonlyArray1<f64>,
    b: PyReadonlyArray1<f64>
) -> PyResult<&'py PyArray1<f64>> {
    let slice_a = a.as_slice()?;
    let slice_b = b.as_slice()?;

    if slice_a.len() != slice_b.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            format!("Array shapes don't match: {} vs {}", slice_a.len(), slice_b.len())
        ));
    }

    let result: Vec<f64> = slice_a.iter()
        .zip(slice_b.iter())
        .map(|(&x, &y)| x + y)
        .collect();

    Ok(PyArray1::from_vec(py, result))
}

/// Calculate dot product of two 1D arrays
///
/// Args:
///     a: First NumPy array
///     b: Second NumPy array
///
/// Returns:
///     Dot product as f64
#[pyfunction]
fn dot_product(a: PyReadonlyArray1<f64>, b: PyReadonlyArray1<f64>) -> PyResult<f64> {
    let slice_a = a.as_slice()?;
    let slice_b = b.as_slice()?;

    if slice_a.len() != slice_b.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            format!("Array shapes don't match: {} vs {}", slice_a.len(), slice_b.len())
        ));
    }

    let dot: f64 = slice_a.iter()
        .zip(slice_b.iter())
        .map(|(&x, &y)| x * y)
        .sum();

    Ok(dot)
}

/// Create a range array from start to end (exclusive)
///
/// Args:
///     start: Start value
///     end: End value (exclusive)
///     step: Step size
///
/// Returns:
///     New NumPy array with range values
#[pyfunction]
fn create_range<'py>(
    py: Python<'py>,
    start: i32,
    end: i32,
    step: i32
) -> PyResult<&'py PyArray1<i32>> {
    if step == 0 {
        return Err(pyo3::exceptions::PyValueError::new_err("Step cannot be zero"));
    }

    let data: Vec<i32> = if step > 0 {
        (start..end).step_by(step as usize).collect()
    } else {
        let mut v: Vec<i32> = Vec::new();
        let mut current = start;
        while current > end {
            v.push(current);
            current += step;
        }
        v
    };

    Ok(PyArray1::from_vec(py, data))
}

/// Create an array of zeros
///
/// Args:
///     size: Number of elements
///
/// Returns:
///     New NumPy array filled with zeros
#[pyfunction]
fn create_zeros<'py>(py: Python<'py>, size: usize) -> PyResult<&'py PyArray1<f64>> {
    let data = vec![0.0; size];
    Ok(PyArray1::from_vec(py, data))
}

/// Create an array of ones
///
/// Args:
///     size: Number of elements
///
/// Returns:
///     New NumPy array filled with ones
#[pyfunction]
fn create_ones<'py>(py: Python<'py>, size: usize) -> PyResult<&'py PyArray1<f64>> {
    let data = vec![1.0; size];
    Ok(PyArray1::from_vec(py, data))
}

/// Validate that array values are within a given range
///
/// Args:
///     array: Input NumPy array
///     min_val: Minimum allowed value
///     max_val: Maximum allowed value
///
/// Returns:
///     True if all values are within range, False otherwise
#[pyfunction]
fn validate_range(array: PyReadonlyArray1<f64>, min_val: f64, max_val: f64) -> PyResult<bool> {
    let slice = array.as_slice()?;
    Ok(slice.iter().all(|&x| x >= min_val && x <= max_val))
}

/// Sum elements in a 2D array
///
/// Args:
///     array: Input 2D NumPy array
///
/// Returns:
///     Sum of all elements
#[pyfunction]
fn sum_2d(array: PyReadonlyArray2<f64>) -> PyResult<f64> {
    Ok(array.as_slice()?.iter().sum())
}

/// Module initialization
#[pymodule]
fn basic_numpy(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_array, m)?)?;
    m.add_function(wrap_pyfunction!(mean_array, m)?)?;
    m.add_function(wrap_pyfunction!(min_array, m)?)?;
    m.add_function(wrap_pyfunction!(max_array, m)?)?;
    m.add_function(wrap_pyfunction!(multiply_scalar, m)?)?;
    m.add_function(wrap_pyfunction!(add_arrays, m)?)?;
    m.add_function(wrap_pyfunction!(dot_product, m)?)?;
    m.add_function(wrap_pyfunction!(create_range, m)?)?;
    m.add_function(wrap_pyfunction!(create_zeros, m)?)?;
    m.add_function(wrap_pyfunction!(create_ones, m)?)?;
    m.add_function(wrap_pyfunction!(validate_range, m)?)?;
    m.add_function(wrap_pyfunction!(sum_2d, m)?)?;
    Ok(())
}
