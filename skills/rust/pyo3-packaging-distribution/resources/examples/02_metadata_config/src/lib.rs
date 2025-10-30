//! Complete package metadata configuration example
//!
//! Demonstrates how to properly configure package metadata for PyPI distribution,
//! including authors, licenses, descriptions, and classifiers.

use pyo3::prelude::*;

/// Calculate the factorial of a number.
///
/// Args:
///     n: Non-negative integer
///
/// Returns:
///     Factorial of n
///
/// Raises:
///     ValueError: If n is negative
///
/// Example:
///     >>> import metadata_config
///     >>> metadata_config.factorial(5)
///     120
#[pyfunction]
fn factorial(n: i64) -> PyResult<i64> {
    if n < 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Factorial is not defined for negative numbers"
        ));
    }

    let mut result = 1i64;
    for i in 2..=n {
        result = result.checked_mul(i).ok_or_else(|| {
            pyo3::exceptions::PyOverflowError::new_err("Factorial overflow")
        })?;
    }
    Ok(result)
}

/// Check if a number is prime.
///
/// Args:
///     n: Integer to check
///
/// Returns:
///     True if n is prime, False otherwise
///
/// Example:
///     >>> import metadata_config
///     >>> metadata_config.is_prime(17)
///     True
///     >>> metadata_config.is_prime(4)
///     False
#[pyfunction]
fn is_prime(n: i64) -> bool {
    if n < 2 {
        return false;
    }
    if n == 2 {
        return true;
    }
    if n % 2 == 0 {
        return false;
    }

    let limit = (n as f64).sqrt() as i64;
    for i in (3..=limit).step_by(2) {
        if n % i == 0 {
            return false;
        }
    }
    true
}

/// Get package metadata information.
///
/// Returns:
///     Dictionary containing package name, version, and author
///
/// Example:
///     >>> import metadata_config
///     >>> info = metadata_config.package_info()
///     >>> info['name']
///     'metadata_config'
#[pyfunction]
fn package_info(py: Python) -> PyResult<PyObject> {
    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("name", env!("CARGO_PKG_NAME"))?;
    dict.set_item("version", env!("CARGO_PKG_VERSION"))?;
    dict.set_item("authors", env!("CARGO_PKG_AUTHORS"))?;
    dict.set_item("description", env!("CARGO_PKG_DESCRIPTION"))?;
    Ok(dict.into())
}

/// A Python package with complete metadata configuration.
///
/// This package demonstrates best practices for package metadata,
/// including proper classifiers, dependencies, and documentation.
#[pymodule]
fn metadata_config(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(factorial, m)?)?;
    m.add_function(wrap_pyfunction!(is_prime, m)?)?;
    m.add_function(wrap_pyfunction!(package_info, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_factorial() {
        assert_eq!(factorial(0).unwrap(), 1);
        assert_eq!(factorial(5).unwrap(), 120);
        assert_eq!(factorial(10).unwrap(), 3628800);
        assert!(factorial(-1).is_err());
    }

    #[test]
    fn test_is_prime() {
        assert!(!is_prime(0));
        assert!(!is_prime(1));
        assert!(is_prime(2));
        assert!(is_prime(17));
        assert!(!is_prime(4));
        assert!(is_prime(97));
    }
}
