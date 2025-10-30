//! CI/CD pipeline example
//!
//! Simple package to demonstrate automated building, testing,
//! and publishing using GitHub Actions.

use pyo3::prelude::*;

/// Multiply two numbers.
///
/// Args:
///     a: First number
///     b: Second number
///
/// Returns:
///     Product of a and b
#[pyfunction]
fn multiply(a: i64, b: i64) -> i64 {
    a * b
}

/// Divide two numbers.
///
/// Args:
///     a: Numerator
///     b: Denominator
///
/// Returns:
///     Quotient
///
/// Raises:
///     ZeroDivisionError: If b is zero
#[pyfunction]
fn divide(a: f64, b: f64) -> PyResult<f64> {
    if b == 0.0 {
        return Err(pyo3::exceptions::PyZeroDivisionError::new_err(
            "Cannot divide by zero"
        ));
    }
    Ok(a / b)
}

/// Power function.
///
/// Args:
///     base: Base number
///     exp: Exponent
///
/// Returns:
///     base raised to the power of exp
#[pyfunction]
fn power(base: f64, exp: f64) -> f64 {
    base.powf(exp)
}

/// Get build and version information.
///
/// Returns:
///     Dictionary with version and build metadata
#[pyfunction]
fn build_info(py: Python) -> PyResult<PyObject> {
    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("version", env!("CARGO_PKG_VERSION"))?;
    dict.set_item("name", env!("CARGO_PKG_NAME"))?;
    dict.set_item("target", env!("TARGET"))?;

    // Add Git info if available (set by CI)
    if let Ok(git_sha) = std::env::var("GIT_SHA") {
        dict.set_item("git_sha", git_sha)?;
    }

    if let Ok(build_date) = std::env::var("BUILD_DATE") {
        dict.set_item("build_date", build_date)?;
    }

    Ok(dict.into())
}

/// Package demonstrating CI/CD pipeline integration.
#[pymodule]
fn ci_cd_example(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(multiply, m)?)?;
    m.add_function(wrap_pyfunction!(divide, m)?)?;
    m.add_function(wrap_pyfunction!(power, m)?)?;
    m.add_function(wrap_pyfunction!(build_info, m)?)?;

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_multiply() {
        assert_eq!(multiply(6, 7), 42);
        assert_eq!(multiply(-1, 5), -5);
    }

    #[test]
    fn test_divide() {
        assert_eq!(divide(10.0, 2.0).unwrap(), 5.0);
        assert!(divide(10.0, 0.0).is_err());
    }

    #[test]
    fn test_power() {
        assert_eq!(power(2.0, 3.0), 8.0);
        assert_eq!(power(10.0, 2.0), 100.0);
    }
}
