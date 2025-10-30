use pyo3::prelude::*;
use pyo3::types::PyList;
use pyo3::exceptions::PyValueError;

/// Pure Rust function that calculates sum
/// This can be tested without PyO3 complexity
pub fn calculate_sum(data: &[f64]) -> f64 {
    data.iter().sum()
}

/// PyO3 function that calculates sum from Python list
#[pyfunction]
fn sum_list(list: Vec<f64>) -> f64 {
    calculate_sum(&list)
}

/// PyO3 function that divides two numbers
#[pyfunction]
fn divide(a: f64, b: f64) -> PyResult<f64> {
    if b == 0.0 {
        Err(PyValueError::new_err("Cannot divide by zero"))
    } else {
        Ok(a / b)
    }
}

/// Process a PyList and extract integers
#[pyfunction]
fn process_list(py: Python, items: &Bound<'_, PyList>) -> PyResult<Vec<i32>> {
    items.iter()
        .map(|item| item.extract::<i32>())
        .collect()
}

/// Python module definition
#[pymodule]
fn rust_unit_tests(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_list, m)?)?;
    m.add_function(wrap_pyfunction!(divide, m)?)?;
    m.add_function(wrap_pyfunction!(process_list, m)?)?;
    Ok(())
}

// ============================================================================
// TESTS
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::Python;

    // ------------------------------------------------------------------------
    // Pure Rust Tests (No GIL required)
    // ------------------------------------------------------------------------

    #[test]
    fn test_calculate_sum() {
        let data = vec![1.0, 2.0, 3.0];
        assert_eq!(calculate_sum(&data), 6.0);
    }

    #[test]
    fn test_empty_sum() {
        assert_eq!(calculate_sum(&[]), 0.0);
    }

    #[test]
    fn test_large_sum() {
        let data: Vec<f64> = (1..=100).map(|x| x as f64).collect();
        assert_eq!(calculate_sum(&data), 5050.0);
    }

    // ------------------------------------------------------------------------
    // PyO3 Tests (GIL required)
    // ------------------------------------------------------------------------

    #[test]
    fn test_divide_basic() {
        Python::with_gil(|_py| {
            let result = divide(10.0, 2.0).unwrap();
            assert_eq!(result, 5.0);
        });
    }

    #[test]
    fn test_divide_by_zero() {
        Python::with_gil(|_py| {
            let result = divide(10.0, 0.0);
            assert!(result.is_err());

            // Check error message
            if let Err(e) = result {
                let err_msg = format!("{}", e);
                assert!(err_msg.contains("Cannot divide by zero"));
            }
        });
    }

    #[test]
    fn test_divide_negative() {
        Python::with_gil(|_py| {
            let result = divide(-10.0, 2.0).unwrap();
            assert_eq!(result, -5.0);
        });
    }

    #[test]
    fn test_process_list() {
        Python::with_gil(|py| {
            let list = PyList::new_bound(py, &[1, 2, 3]);
            let result = process_list(py, &list).unwrap();
            assert_eq!(result, vec![1, 2, 3]);
        });
    }

    #[test]
    fn test_process_list_invalid() {
        Python::with_gil(|py| {
            // Create list with strings (invalid for i32)
            let list = PyList::new_bound(py, &["a", "b"]);
            let result = process_list(py, &list);
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_process_empty_list() {
        Python::with_gil(|py| {
            let list = PyList::empty_bound(py);
            let result = process_list(py, &list).unwrap();
            assert_eq!(result, Vec::<i32>::new());
        });
    }

    // ------------------------------------------------------------------------
    // Edge Case Tests
    // ------------------------------------------------------------------------

    #[test]
    fn test_sum_single_element() {
        assert_eq!(calculate_sum(&[42.0]), 42.0);
    }

    #[test]
    fn test_divide_by_one() {
        Python::with_gil(|_py| {
            let result = divide(42.0, 1.0).unwrap();
            assert_eq!(result, 42.0);
        });
    }

    #[test]
    fn test_divide_zero_by_nonzero() {
        Python::with_gil(|_py| {
            let result = divide(0.0, 5.0).unwrap();
            assert_eq!(result, 0.0);
        });
    }
}
