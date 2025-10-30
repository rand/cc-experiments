use pyo3::prelude::*;
use rayon::prelude::*;

/// Advanced map operation with error handling
#[pyfunction]
fn parallel_map_with_error(
    py: Python,
    numbers: Vec<f64>,
    divisor: f64,
) -> PyResult<Vec<f64>> {
    if divisor == 0.0 {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Division by zero",
        ));
    }

    let result = py.allow_threads(|| numbers.par_iter().map(|x| x / divisor).collect());

    Ok(result)
}

/// Parallel flat map
#[pyfunction]
fn parallel_flat_map(py: Python, ranges: Vec<(i64, i64)>) -> PyResult<Vec<i64>> {
    let result = py.allow_threads(|| {
        ranges
            .par_iter()
            .flat_map(|(start, end)| (*start..*end).into_par_iter())
            .collect()
    });

    Ok(result)
}

/// Parallel filter and map chain
#[pyfunction]
fn parallel_filter_map(py: Python, numbers: Vec<i64>) -> PyResult<Vec<i64>> {
    let result = py.allow_threads(|| {
        numbers
            .par_iter()
            .filter(|x| **x % 2 == 0)
            .map(|x| x * x)
            .collect()
    });

    Ok(result)
}

/// Parallel fold (reduce) with custom combiner
#[pyfunction]
fn parallel_fold(py: Python, numbers: Vec<f64>) -> PyResult<(f64, f64, f64)> {
    let result = py.allow_threads(|| {
        numbers
            .par_iter()
            .fold(
                || (0.0, f64::MAX, f64::MIN),
                |(sum, min, max), &x| (sum + x, min.min(x), max.max(x)),
            )
            .reduce(
                || (0.0, f64::MAX, f64::MIN),
                |(sum1, min1, max1), (sum2, min2, max2)| {
                    (sum1 + sum2, min1.min(min2), max1.max(max2))
                },
            )
    });

    Ok(result)
}

/// Parallel partition - split into two groups
#[pyfunction]
fn parallel_partition(py: Python, numbers: Vec<i64>, threshold: i64) -> PyResult<(Vec<i64>, Vec<i64>)> {
    let result = py.allow_threads(|| {
        numbers
            .par_iter()
            .partition(|x| **x < threshold)
    });

    Ok(result)
}

/// Parallel group by
#[pyfunction]
fn parallel_group_by_modulo(py: Python, numbers: Vec<i64>, modulo: i64) -> PyResult<Vec<Vec<i64>>> {
    let result = py.allow_threads(|| {
        let mut groups: Vec<Vec<i64>> = (0..modulo).map(|_| Vec::new()).collect();

        numbers
            .par_iter()
            .fold(
                || (0..modulo).map(|_| Vec::new()).collect::<Vec<Vec<i64>>>(),
                |mut acc, &x| {
                    acc[(x % modulo) as usize].push(x);
                    acc
                },
            )
            .reduce(
                || (0..modulo).map(|_| Vec::new()).collect::<Vec<Vec<i64>>>(),
                |mut acc1, acc2| {
                    for (i, group) in acc2.into_iter().enumerate() {
                        acc1[i].extend(group);
                    }
                    acc1
                },
            )
    });

    Ok(result)
}

/// Parallel find - returns first match
#[pyfunction]
fn parallel_find(py: Python, numbers: Vec<i64>, target: i64) -> PyResult<Option<usize>> {
    let result = py.allow_threads(|| {
        numbers
            .par_iter()
            .position_any(|x| *x == target)
    });

    Ok(result)
}

/// Parallel any/all predicates
#[pyfunction]
fn parallel_predicates(py: Python, numbers: Vec<i64>) -> PyResult<(bool, bool)> {
    let (any_negative, all_positive) = py.allow_threads(|| {
        let any_neg = numbers.par_iter().any(|x| *x < 0);
        let all_pos = numbers.par_iter().all(|x| *x > 0);
        (any_neg, all_pos)
    });

    Ok((any_negative, all_positive))
}

/// Parallel zip and process
#[pyfunction]
fn parallel_zip_add(py: Python, a: Vec<f64>, b: Vec<f64>) -> PyResult<Vec<f64>> {
    if a.len() != b.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Vectors must have same length",
        ));
    }

    let result = py.allow_threads(|| {
        a.par_iter()
            .zip(b.par_iter())
            .map(|(x, y)| x + y)
            .collect()
    });

    Ok(result)
}

/// Parallel window operations - moving average
#[pyfunction]
fn parallel_moving_average(py: Python, numbers: Vec<f64>, window: usize) -> PyResult<Vec<f64>> {
    if window == 0 || window > numbers.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid window size",
        ));
    }

    let result = py.allow_threads(|| {
        (0..numbers.len() - window + 1)
            .into_par_iter()
            .map(|i| {
                let sum: f64 = numbers[i..i + window].iter().sum();
                sum / window as f64
            })
            .collect()
    });

    Ok(result)
}

/// Parallel collect into different container
#[pyfunction]
fn parallel_collect_string(py: Python, numbers: Vec<i64>) -> PyResult<Vec<String>> {
    let result = py.allow_threads(|| {
        numbers
            .par_iter()
            .map(|x| x.to_string())
            .collect()
    });

    Ok(result)
}

/// Nested parallel iteration - matrix transpose
#[pyfunction]
fn parallel_matrix_transpose(py: Python, matrix: Vec<Vec<f64>>) -> PyResult<Vec<Vec<f64>>> {
    if matrix.is_empty() || matrix[0].is_empty() {
        return Ok(Vec::new());
    }

    let rows = matrix.len();
    let cols = matrix[0].len();

    let result = py.allow_threads(|| {
        (0..cols)
            .into_par_iter()
            .map(|j| (0..rows).map(|i| matrix[i][j]).collect())
            .collect()
    });

    Ok(result)
}

/// Custom parallel chain
#[pyfunction]
fn parallel_chain(py: Python, a: Vec<i64>, b: Vec<i64>) -> PyResult<Vec<i64>> {
    let result = py.allow_threads(|| {
        a.par_iter()
            .chain(b.par_iter())
            .copied()
            .collect()
    });

    Ok(result)
}

/// Parallel inspect for debugging
#[pyfunction]
fn parallel_process_with_log(py: Python, numbers: Vec<f64>) -> PyResult<Vec<f64>> {
    use std::sync::Mutex;
    let log = Mutex::new(Vec::new());

    let result = py.allow_threads(|| {
        numbers
            .par_iter()
            .inspect(|x| {
                if **x > 100.0 {
                    log.lock().unwrap().push(**x);
                }
            })
            .map(|x| x * 2.0)
            .collect()
    });

    Ok(result)
}

#[pymodule]
fn parallel_iterators(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parallel_map_with_error, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_flat_map, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_filter_map, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_fold, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_partition, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_group_by_modulo, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_find, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_predicates, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_zip_add, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_moving_average, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_collect_string, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_matrix_transpose, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_chain, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_process_with_log, m)?)?;
    Ok(())
}
