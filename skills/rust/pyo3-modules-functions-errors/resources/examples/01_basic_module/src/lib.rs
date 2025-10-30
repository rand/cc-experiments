//! Example 01: Basic Module with Simple Functions
//!
//! This example demonstrates:
//! - Creating a PyO3 module with #[pymodule]
//! - Exporting simple functions with #[pyfunction]
//! - Basic type conversion (integers, strings, booleans)
//! - Module-level docstrings

use pyo3::prelude::*;

/// Adds two numbers together.
///
/// Args:
///     a: First number
///     b: Second number
///
/// Returns:
///     The sum of a and b
#[pyfunction]
fn add(a: i64, b: i64) -> i64 {
    a + b
}

/// Multiplies two numbers.
///
/// Args:
///     a: First number
///     b: Second number
///
/// Returns:
///     The product of a and b
#[pyfunction]
fn multiply(a: i64, b: i64) -> i64 {
    a * b
}

/// Greets a person by name.
///
/// Args:
///     name: The name to greet
///
/// Returns:
///     A greeting message
#[pyfunction]
fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

/// Checks if a number is even.
///
/// Args:
///     n: The number to check
///
/// Returns:
///     True if the number is even, False otherwise
#[pyfunction]
fn is_even(n: i64) -> bool {
    n % 2 == 0
}

/// Repeats a string n times.
///
/// Args:
///     text: The string to repeat
///     count: Number of repetitions
///
/// Returns:
///     The repeated string
#[pyfunction]
fn repeat_string(text: &str, count: usize) -> String {
    text.repeat(count)
}

/// A basic PyO3 module demonstrating simple functions.
///
/// This module provides basic arithmetic, string manipulation,
/// and utility functions implemented in Rust for improved performance.
#[pymodule]
fn basic_module(_py: Python, m: &PyModule) -> PyResult<()> {
    // Add functions to the module
    m.add_function(wrap_pyfunction!(add, m)?)?;
    m.add_function(wrap_pyfunction!(multiply, m)?)?;
    m.add_function(wrap_pyfunction!(greet, m)?)?;
    m.add_function(wrap_pyfunction!(is_even, m)?)?;
    m.add_function(wrap_pyfunction!(repeat_string, m)?)?;

    // Add module metadata
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__author__", "PyO3 Examples")?;

    Ok(())
}
