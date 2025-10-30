//! Production-ready PyO3 package
//!
//! Demonstrates a complete production release workflow including
//! versioning, documentation, changelog, and PyPI publishing.

use pyo3::prelude::*;

/// Calculate the nth triangular number.
///
/// A triangular number counts objects arranged in an equilateral triangle.
/// The nth triangular number is the sum of the n natural numbers from 1 to n.
///
/// Args:
///     n: Position in sequence (must be non-negative)
///
/// Returns:
///     The nth triangular number
///
/// Raises:
///     ValueError: If n is negative
///
/// Example:
///     >>> from production_release import triangular
///     >>> triangular(5)
///     15
///     >>> triangular(10)
///     55
#[pyfunction]
fn triangular(n: i64) -> PyResult<i64> {
    if n < 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "n must be non-negative"
        ));
    }
    Ok((n * (n + 1)) / 2)
}

/// Calculate factorial using iterative algorithm.
///
/// Args:
///     n: Non-negative integer
///
/// Returns:
///     n factorial (n!)
///
/// Raises:
///     ValueError: If n is negative
///     OverflowError: If result exceeds i64 range
///
/// Example:
///     >>> from production_release import factorial
///     >>> factorial(5)
///     120
#[pyfunction]
fn factorial(n: i64) -> PyResult<i64> {
    if n < 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "factorial is not defined for negative numbers"
        ));
    }

    let mut result = 1i64;
    for i in 2..=n {
        result = result.checked_mul(i).ok_or_else(|| {
            pyo3::exceptions::PyOverflowError::new_err(
                "factorial result too large"
            )
        })?;
    }
    Ok(result)
}

/// Check if a number is a perfect square.
///
/// Args:
///     n: Integer to check
///
/// Returns:
///     True if n is a perfect square, False otherwise
///
/// Example:
///     >>> from production_release import is_perfect_square
///     >>> is_perfect_square(16)
///     True
///     >>> is_perfect_square(15)
///     False
#[pyfunction]
fn is_perfect_square(n: i64) -> bool {
    if n < 0 {
        return false;
    }
    let sqrt = (n as f64).sqrt() as i64;
    sqrt * sqrt == n
}

/// Get package version information.
///
/// Returns:
///     Dictionary with version components and metadata
///
/// Example:
///     >>> from production_release import version_info
///     >>> info = version_info()
///     >>> info['version']
///     '1.0.0'
#[pyfunction]
fn version_info(py: Python) -> PyResult<PyObject> {
    let dict = pyo3::types::PyDict::new(py);

    dict.set_item("version", env!("CARGO_PKG_VERSION"))?;
    dict.set_item("name", env!("CARGO_PKG_NAME"))?;

    let version = env!("CARGO_PKG_VERSION");
    let parts: Vec<&str> = version.split('.').collect();

    dict.set_item("major", parts.first().and_then(|s| s.parse::<u32>().ok()).unwrap_or(0))?;
    dict.set_item("minor", parts.get(1).and_then(|s| s.parse::<u32>().ok()).unwrap_or(0))?;
    dict.set_item("patch", parts.get(2).and_then(|s| s.parse::<u32>().ok()).unwrap_or(0))?;

    Ok(dict.into())
}

/// A production-ready PyO3 package.
///
/// This module provides mathematical utilities with comprehensive
/// documentation, error handling, and testing.
#[pymodule]
fn production_release(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(triangular, m)?)?;
    m.add_function(wrap_pyfunction!(factorial, m)?)?;
    m.add_function(wrap_pyfunction!(is_perfect_square, m)?)?;
    m.add_function(wrap_pyfunction!(version_info, m)?)?;

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_triangular() {
        assert_eq!(triangular(0).unwrap(), 0);
        assert_eq!(triangular(1).unwrap(), 1);
        assert_eq!(triangular(5).unwrap(), 15);
        assert_eq!(triangular(10).unwrap(), 55);
        assert!(triangular(-1).is_err());
    }

    #[test]
    fn test_factorial() {
        assert_eq!(factorial(0).unwrap(), 1);
        assert_eq!(factorial(5).unwrap(), 120);
        assert_eq!(factorial(10).unwrap(), 3628800);
        assert!(factorial(-1).is_err());
    }

    #[test]
    fn test_is_perfect_square() {
        assert!(is_perfect_square(0));
        assert!(is_perfect_square(1));
        assert!(is_perfect_square(16));
        assert!(!is_perfect_square(15));
        assert!(!is_perfect_square(-1));
    }
}
