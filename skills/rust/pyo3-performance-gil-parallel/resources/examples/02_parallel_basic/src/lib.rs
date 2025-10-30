use pyo3::prelude::*;
use rayon::prelude::*;

/// Simple parallel sum using Rayon
#[pyfunction]
fn parallel_sum(py: Python, numbers: Vec<f64>) -> PyResult<f64> {
    let result = py.allow_threads(|| {
        numbers.par_iter().sum()
    });
    Ok(result)
}

/// Sequential sum for comparison
#[pyfunction]
fn sequential_sum(numbers: Vec<f64>) -> PyResult<f64> {
    Ok(numbers.iter().sum())
}

/// Parallel map operation - square all numbers
#[pyfunction]
fn parallel_square(py: Python, numbers: Vec<f64>) -> PyResult<Vec<f64>> {
    let result = py.allow_threads(|| {
        numbers.par_iter().map(|x| x * x).collect()
    });
    Ok(result)
}

/// Parallel filter operation - keep only even numbers
#[pyfunction]
fn parallel_filter_even(py: Python, numbers: Vec<i64>) -> PyResult<Vec<i64>> {
    let result = py.allow_threads(|| {
        numbers.par_iter()
            .filter(|x| *x % 2 == 0)
            .copied()
            .collect()
    });
    Ok(result)
}

/// Parallel reduce operation - find maximum
#[pyfunction]
fn parallel_max(py: Python, numbers: Vec<f64>) -> PyResult<Option<f64>> {
    let result = py.allow_threads(|| {
        numbers.par_iter()
            .copied()
            .max_by(|a, b| a.partial_cmp(b).unwrap())
    });
    Ok(result)
}

/// Parallel sort using Rayon
#[pyfunction]
fn parallel_sort(py: Python, mut numbers: Vec<f64>) -> PyResult<Vec<f64>> {
    py.allow_threads(|| {
        numbers.par_sort_by(|a, b| a.partial_cmp(b).unwrap());
    });
    Ok(numbers)
}

/// Complex computation: parallel mandelbrot set calculation
fn mandelbrot_point(c_re: f64, c_im: f64, max_iter: u32) -> u32 {
    let mut z_re = 0.0;
    let mut z_im = 0.0;
    let mut n = 0;

    while n < max_iter {
        if z_re * z_re + z_im * z_im > 4.0 {
            break;
        }
        let new_re = z_re * z_re - z_im * z_im + c_re;
        let new_im = 2.0 * z_re * z_im + c_im;
        z_re = new_re;
        z_im = new_im;
        n += 1;
    }

    n
}

#[pyfunction]
fn parallel_mandelbrot(
    py: Python,
    width: usize,
    height: usize,
    x_min: f64,
    x_max: f64,
    y_min: f64,
    y_max: f64,
    max_iter: u32,
) -> PyResult<Vec<Vec<u32>>> {
    let result = py.allow_threads(|| {
        (0..height)
            .into_par_iter()
            .map(|y| {
                let c_im = y_min + (y as f64 / height as f64) * (y_max - y_min);
                (0..width)
                    .map(|x| {
                        let c_re = x_min + (x as f64 / width as f64) * (x_max - x_min);
                        mandelbrot_point(c_re, c_im, max_iter)
                    })
                    .collect()
            })
            .collect()
    });
    Ok(result)
}

/// Parallel chunk processing with custom chunk size
#[pyfunction]
fn parallel_sum_chunked(py: Python, numbers: Vec<f64>, chunk_size: usize) -> PyResult<f64> {
    let result = py.allow_threads(|| {
        numbers
            .par_chunks(chunk_size)
            .map(|chunk| chunk.iter().sum::<f64>())
            .sum()
    });
    Ok(result)
}

/// Parallel string processing - count words in multiple documents
#[pyfunction]
fn parallel_word_count(py: Python, documents: Vec<String>) -> PyResult<Vec<usize>> {
    let result = py.allow_threads(|| {
        documents
            .par_iter()
            .map(|doc| doc.split_whitespace().count())
            .collect()
    });
    Ok(result)
}

/// Nested parallelism - matrix multiplication
#[pyfunction]
fn parallel_matrix_multiply(
    py: Python,
    a: Vec<Vec<f64>>,
    b: Vec<Vec<f64>>,
) -> PyResult<Vec<Vec<f64>>> {
    if a.is_empty() || b.is_empty() || a[0].len() != b.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid matrix dimensions",
        ));
    }

    let result = py.allow_threads(|| {
        let n = a.len();
        let m = b[0].len();
        let p = b.len();

        (0..n)
            .into_par_iter()
            .map(|i| {
                (0..m)
                    .map(|j| (0..p).map(|k| a[i][k] * b[k][j]).sum())
                    .collect()
            })
            .collect()
    });

    Ok(result)
}

#[pymodule]
fn parallel_basic(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parallel_sum, m)?)?;
    m.add_function(wrap_pyfunction!(sequential_sum, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_square, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_filter_even, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_max, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_sort, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_mandelbrot, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_sum_chunked, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_word_count, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_matrix_multiply, m)?)?;
    Ok(())
}
