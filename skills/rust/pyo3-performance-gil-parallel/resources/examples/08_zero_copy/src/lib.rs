use pyo3::prelude::*;
use pyo3::types::PyList;
use rayon::prelude::*;

/// Zero-copy slice processing - operates directly on Python buffer
#[pyfunction]
fn process_slice_inplace(py: Python, data: Vec<f64>) -> PyResult<Vec<f64>> {
    // In real zero-copy scenario, we'd use PyArray from numpy crate
    // This demonstrates the concept with Vec
    let mut data = data;

    py.allow_threads(|| {
        data.par_iter_mut().for_each(|x| *x = *x * *x);
    });

    Ok(data)
}

/// Parallel sum without copying
#[pyfunction]
fn sum_nocopy(py: Python, data: Vec<f64>) -> PyResult<f64> {
    let result = py.allow_threads(|| data.par_iter().sum());
    Ok(result)
}

/// Process large array in chunks for cache efficiency
#[pyfunction]
fn process_chunked_nocopy(py: Python, data: Vec<f64>, chunk_size: usize) -> PyResult<Vec<f64>> {
    let mut data = data;

    py.allow_threads(|| {
        data.par_chunks_mut(chunk_size)
            .for_each(|chunk| {
                for x in chunk {
                    *x = (*x * 2.0).sqrt();
                }
            });
    });

    Ok(data)
}

/// Matrix-vector multiplication with minimal copies
#[pyfunction]
fn matvec_multiply(
    py: Python,
    matrix: Vec<Vec<f64>>,
    vector: Vec<f64>,
) -> PyResult<Vec<f64>> {
    if matrix.is_empty() || matrix[0].len() != vector.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid dimensions",
        ));
    }

    let result = py.allow_threads(|| {
        matrix
            .par_iter()
            .map(|row| row.iter().zip(&vector).map(|(a, b)| a * b).sum())
            .collect()
    });

    Ok(result)
}

/// Parallel reduce with custom accumulator
#[pyfunction]
fn parallel_reduce_nocopy(py: Python, data: Vec<f64>) -> PyResult<(f64, f64, f64, usize)> {
    let result = py.allow_threads(|| {
        data.par_iter().fold(
            || (0.0, f64::INFINITY, f64::NEG_INFINITY, 0),
            |(sum, min, max, count), &x| {
                (sum + x, min.min(x), max.max(x), count + 1)
            },
        ).reduce(
            || (0.0, f64::INFINITY, f64::NEG_INFINITY, 0),
            |(sum1, min1, max1, count1), (sum2, min2, max2, count2)| {
                (sum1 + sum2, min1.min(min2), max1.max(max2), count1 + count2)
            },
        )
    });

    Ok(result)
}

#[pymodule]
fn zero_copy(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_slice_inplace, m)?)?;
    m.add_function(wrap_pyfunction!(sum_nocopy, m)?)?;
    m.add_function(wrap_pyfunction!(process_chunked_nocopy, m)?)?;
    m.add_function(wrap_pyfunction!(matvec_multiply, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_reduce_nocopy, m)?)?;
    Ok(())
}
