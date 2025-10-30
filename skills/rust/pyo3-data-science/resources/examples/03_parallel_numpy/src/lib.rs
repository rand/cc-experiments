use pyo3::prelude::*;
use numpy::{PyArray1, PyReadonlyArray1, ToPyArray};
use ndarray::Array1;
use rayon::prelude::*;

/// Compute squares of array elements in parallel
///
/// Args:
///     array: Input NumPy array
///
/// Returns:
///     Array with squared values
#[pyfunction]
fn parallel_square<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>
) -> PyResult<&'py PyArray1<f64>> {
    let slice = array.as_slice()?;

    // Release GIL for parallel processing
    let result: Vec<f64> = py.allow_threads(|| {
        slice.par_iter()
            .map(|&x| x * x)
            .collect()
    });

    Ok(PyArray1::from_vec(py, result))
}

/// Apply a complex mathematical function in parallel
///
/// Args:
///     array: Input NumPy array
///
/// Returns:
///     Transformed array
#[pyfunction]
fn parallel_transform<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>
) -> PyResult<&'py PyArray1<f64>> {
    let slice = array.as_slice()?;

    let result: Vec<f64> = py.allow_threads(|| {
        slice.par_iter()
            .map(|&x| {
                // Simulate expensive computation
                (x.powi(3) + x.powi(2) + x).sqrt().abs()
            })
            .collect()
    });

    Ok(PyArray1::from_vec(py, result))
}

/// Sum array elements in parallel using chunks
///
/// Args:
///     array: Input NumPy array
///     chunk_size: Size of chunks for parallel processing
///
/// Returns:
///     Sum of all elements
#[pyfunction]
fn parallel_sum(
    py: Python,
    array: PyReadonlyArray1<f64>,
    chunk_size: usize
) -> PyResult<f64> {
    let slice = array.as_slice()?;

    let result = py.allow_threads(|| {
        slice.par_chunks(chunk_size)
            .map(|chunk| chunk.iter().sum::<f64>())
            .sum()
    });

    Ok(result)
}

/// Compute running statistics in parallel
///
/// Args:
///     array: Input NumPy array
///
/// Returns:
///     Tuple of (sum, mean, min, max)
#[pyfunction]
fn parallel_stats(
    py: Python,
    array: PyReadonlyArray1<f64>
) -> PyResult<(f64, f64, f64, f64)> {
    let slice = array.as_slice()?;

    if slice.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("Array is empty"));
    }

    let (sum, min, max) = py.allow_threads(|| {
        slice.par_iter()
            .fold(
                || (0.0f64, f64::INFINITY, f64::NEG_INFINITY),
                |(sum, min, max), &x| (sum + x, min.min(x), max.max(x))
            )
            .reduce(
                || (0.0f64, f64::INFINITY, f64::NEG_INFINITY),
                |(sum1, min1, max1), (sum2, min2, max2)| {
                    (sum1 + sum2, min1.min(min2), max1.max(max2))
                }
            )
    });

    let mean = sum / slice.len() as f64;
    Ok((sum, mean, min, max))
}

/// Filter array values in parallel
///
/// Args:
///     array: Input NumPy array
///     threshold: Minimum value to keep
///
/// Returns:
///     Filtered array
#[pyfunction]
fn parallel_filter<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>,
    threshold: f64
) -> PyResult<&'py PyArray1<f64>> {
    let slice = array.as_slice()?;

    let result: Vec<f64> = py.allow_threads(|| {
        slice.par_iter()
            .filter(|&&x| x > threshold)
            .copied()
            .collect()
    });

    Ok(PyArray1::from_vec(py, result))
}

/// Normalize array using parallel computation
///
/// Args:
///     array: Input NumPy array
///
/// Returns:
///     Normalized array (zero mean, unit variance)
#[pyfunction]
fn parallel_normalize<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>
) -> PyResult<&'py PyArray1<f64>> {
    let slice = array.as_slice()?;

    if slice.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("Array is empty"));
    }

    // Compute mean and std in parallel
    let (sum, sum_sq) = py.allow_threads(|| {
        slice.par_iter()
            .fold(
                || (0.0f64, 0.0f64),
                |(sum, sum_sq), &x| (sum + x, sum_sq + x * x)
            )
            .reduce(
                || (0.0f64, 0.0f64),
                |(sum1, sum_sq1), (sum2, sum_sq2)| (sum1 + sum2, sum_sq1 + sum_sq2)
            )
    });

    let n = slice.len() as f64;
    let mean = sum / n;
    let variance = (sum_sq / n) - (mean * mean);
    let std = variance.sqrt();

    if std < 1e-10 {
        return Ok(PyArray1::from_vec(py, vec![0.0; slice.len()]));
    }

    // Normalize in parallel
    let result: Vec<f64> = py.allow_threads(|| {
        slice.par_iter()
            .map(|&x| (x - mean) / std)
            .collect()
    });

    Ok(PyArray1::from_vec(py, result))
}

/// Compute element-wise product of two arrays in parallel
///
/// Args:
///     a: First NumPy array
///     b: Second NumPy array
///
/// Returns:
///     Element-wise product
#[pyfunction]
fn parallel_multiply<'py>(
    py: Python<'py>,
    a: PyReadonlyArray1<f64>,
    b: PyReadonlyArray1<f64>
) -> PyResult<&'py PyArray1<f64>> {
    let slice_a = a.as_slice()?;
    let slice_b = b.as_slice()?;

    if slice_a.len() != slice_b.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            format!("Array lengths don't match: {} vs {}", slice_a.len(), slice_b.len())
        ));
    }

    let result: Vec<f64> = py.allow_threads(|| {
        slice_a.par_iter()
            .zip(slice_b.par_iter())
            .map(|(&x, &y)| x * y)
            .collect()
    });

    Ok(PyArray1::from_vec(py, result))
}

/// Apply parallel windowed operation
///
/// Args:
///     array: Input NumPy array
///     window_size: Size of the sliding window
///
/// Returns:
///     Array of window sums
#[pyfunction]
fn parallel_window_sum<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>,
    window_size: usize
) -> PyResult<&'py PyArray1<f64>> {
    let slice = array.as_slice()?;

    if window_size > slice.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Window size larger than array"
        ));
    }

    let result: Vec<f64> = py.allow_threads(|| {
        (0..=(slice.len() - window_size))
            .into_par_iter()
            .map(|i| slice[i..i + window_size].iter().sum())
            .collect()
    });

    Ok(PyArray1::from_vec(py, result))
}

/// Compute cumulative sum using parallel prefix scan
///
/// Args:
///     array: Input NumPy array
///
/// Returns:
///     Cumulative sum array
#[pyfunction]
fn parallel_cumsum<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>
) -> PyResult<&'py PyArray1<f64>> {
    let arr = array.as_array();

    let result: Array1<f64> = py.allow_threads(|| {
        let mut cumsum = arr.to_owned();
        let mut current_sum = 0.0;

        for val in cumsum.iter_mut() {
            current_sum += *val;
            *val = current_sum;
        }

        cumsum
    });

    Ok(result.to_pyarray(py))
}

/// Module initialization
#[pymodule]
fn parallel_numpy(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parallel_square, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_transform, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_sum, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_stats, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_filter, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_normalize, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_multiply, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_window_sum, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_cumsum, m)?)?;
    Ok(())
}
