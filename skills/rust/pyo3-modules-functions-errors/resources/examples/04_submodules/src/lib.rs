//! Example 04: Submodules and Module Organization
//!
//! This example demonstrates:
//! - Creating nested module structures
//! - Organizing functions into submodules
//! - Re-exporting items at different levels
//! - Module documentation and metadata
//! - Best practices for large projects

use pyo3::prelude::*;

// Math operations submodule
pub mod math {
    use pyo3::prelude::*;

    /// Adds two numbers.
    #[pyfunction]
    pub fn add(a: i64, b: i64) -> i64 {
        a + b
    }

    /// Subtracts b from a.
    #[pyfunction]
    pub fn subtract(a: i64, b: i64) -> i64 {
        a - b
    }

    /// Multiplies two numbers.
    #[pyfunction]
    pub fn multiply(a: i64, b: i64) -> i64 {
        a * b
    }

    /// Divides a by b.
    #[pyfunction]
    pub fn divide(a: f64, b: f64) -> PyResult<f64> {
        if b == 0.0 {
            Err(pyo3::exceptions::PyZeroDivisionError::new_err(
                "Cannot divide by zero"
            ))
        } else {
            Ok(a / b)
        }
    }

    /// Creates the math submodule.
    pub fn register_module(py: Python, parent_module: &PyModule) -> PyResult<()> {
        let math_module = PyModule::new(py, "math")?;
        math_module.add_function(wrap_pyfunction!(add, math_module)?)?;
        math_module.add_function(wrap_pyfunction!(subtract, math_module)?)?;
        math_module.add_function(wrap_pyfunction!(multiply, math_module)?)?;
        math_module.add_function(wrap_pyfunction!(divide, math_module)?)?;

        parent_module.add_submodule(math_module)?;
        Ok(())
    }
}

// String operations submodule
pub mod strings {
    use pyo3::prelude::*;

    /// Converts a string to uppercase.
    #[pyfunction]
    pub fn to_upper(s: &str) -> String {
        s.to_uppercase()
    }

    /// Converts a string to lowercase.
    #[pyfunction]
    pub fn to_lower(s: &str) -> String {
        s.to_lowercase()
    }

    /// Reverses a string.
    #[pyfunction]
    pub fn reverse(s: &str) -> String {
        s.chars().rev().collect()
    }

    /// Counts characters in a string.
    #[pyfunction]
    pub fn char_count(s: &str) -> usize {
        s.chars().count()
    }

    /// Checks if string is a palindrome.
    #[pyfunction]
    pub fn is_palindrome(s: &str) -> bool {
        let normalized: String = s.chars()
            .filter(|c| c.is_alphanumeric())
            .map(|c| c.to_lowercase().next().unwrap())
            .collect();
        normalized == normalized.chars().rev().collect::<String>()
    }

    /// Creates the strings submodule.
    pub fn register_module(py: Python, parent_module: &PyModule) -> PyResult<()> {
        let strings_module = PyModule::new(py, "strings")?;
        strings_module.add_function(wrap_pyfunction!(to_upper, strings_module)?)?;
        strings_module.add_function(wrap_pyfunction!(to_lower, strings_module)?)?;
        strings_module.add_function(wrap_pyfunction!(reverse, strings_module)?)?;
        strings_module.add_function(wrap_pyfunction!(char_count, strings_module)?)?;
        strings_module.add_function(wrap_pyfunction!(is_palindrome, strings_module)?)?;

        parent_module.add_submodule(strings_module)?;
        Ok(())
    }
}

// Collections operations submodule
pub mod collections {
    use pyo3::prelude::*;

    /// Sums all numbers in a list.
    #[pyfunction]
    pub fn sum_list(numbers: Vec<i64>) -> i64 {
        numbers.iter().sum()
    }

    /// Finds the maximum value in a list.
    #[pyfunction]
    pub fn max_value(numbers: Vec<i64>) -> PyResult<i64> {
        numbers.iter()
            .max()
            .copied()
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err(
                "Cannot find max of empty list"
            ))
    }

    /// Finds the minimum value in a list.
    #[pyfunction]
    pub fn min_value(numbers: Vec<i64>) -> PyResult<i64> {
        numbers.iter()
            .min()
            .copied()
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err(
                "Cannot find min of empty list"
            ))
    }

    /// Removes duplicates from a list while preserving order.
    #[pyfunction]
    pub fn unique(items: Vec<i64>) -> Vec<i64> {
        let mut seen = std::collections::HashSet::new();
        items.into_iter()
            .filter(|item| seen.insert(*item))
            .collect()
    }

    /// Computes the average of numbers in a list.
    #[pyfunction]
    pub fn average(numbers: Vec<f64>) -> PyResult<f64> {
        if numbers.is_empty() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Cannot compute average of empty list"
            ));
        }
        Ok(numbers.iter().sum::<f64>() / numbers.len() as f64)
    }

    /// Creates the collections submodule.
    pub fn register_module(py: Python, parent_module: &PyModule) -> PyResult<()> {
        let collections_module = PyModule::new(py, "collections")?;
        collections_module.add_function(wrap_pyfunction!(sum_list, collections_module)?)?;
        collections_module.add_function(wrap_pyfunction!(max_value, collections_module)?)?;
        collections_module.add_function(wrap_pyfunction!(min_value, collections_module)?)?;
        collections_module.add_function(wrap_pyfunction!(unique, collections_module)?)?;
        collections_module.add_function(wrap_pyfunction!(average, collections_module)?)?;

        parent_module.add_submodule(collections_module)?;
        Ok(())
    }
}

// Utility functions at the root level
/// Gets the version of the module.
#[pyfunction]
fn get_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// Lists all available submodules.
#[pyfunction]
fn list_submodules() -> Vec<&'static str> {
    vec!["math", "strings", "collections"]
}

/// Main module with submodules.
///
/// This module demonstrates organizing functionality into submodules:
/// - math: Mathematical operations
/// - strings: String manipulation
/// - collections: Collection operations
#[pymodule]
fn submodules(py: Python, m: &PyModule) -> PyResult<()> {
    // Register submodules
    math::register_module(py, m)?;
    strings::register_module(py, m)?;
    collections::register_module(py, m)?;

    // Add root-level functions
    m.add_function(wrap_pyfunction!(get_version, m)?)?;
    m.add_function(wrap_pyfunction!(list_submodules, m)?)?;

    // Add module metadata
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__doc__", "A module demonstrating submodule organization")?;

    Ok(())
}
