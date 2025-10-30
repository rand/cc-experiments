//! Minimal PyO3 package demonstrating basic maturin setup
//!
//! This example shows the absolute minimum configuration needed
//! to create a distributable Python package from Rust code.

use pyo3::prelude::*;

/// Add two numbers together.
///
/// Args:
///     a: First number
///     b: Second number
///
/// Returns:
///     Sum of a and b
///
/// Example:
///     >>> import basic_package
///     >>> basic_package.add(2, 3)
///     5
#[pyfunction]
fn add(a: i64, b: i64) -> i64 {
    a + b
}

/// Greet someone by name.
///
/// Args:
///     name: Name to greet
///
/// Returns:
///     Greeting message
///
/// Example:
///     >>> import basic_package
///     >>> basic_package.greet("World")
///     'Hello, World!'
#[pyfunction]
fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

/// A minimal PyO3 package demonstrating basic packaging.
#[pymodule]
fn basic_package(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(add, m)?)?;
    m.add_function(wrap_pyfunction!(greet, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add() {
        assert_eq!(add(2, 3), 5);
        assert_eq!(add(-1, 1), 0);
    }

    #[test]
    fn test_greet() {
        assert_eq!(greet("World"), "Hello, World!");
        assert_eq!(greet("Rust"), "Hello, Rust!");
    }
}
