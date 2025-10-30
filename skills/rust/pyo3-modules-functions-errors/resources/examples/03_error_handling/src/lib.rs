//! Example 03: Error Handling and Exceptions
//!
//! This example demonstrates:
//! - Returning PyResult<T> for fallible operations
//! - Creating Python exceptions from Rust errors
//! - Mapping standard exception types
//! - Custom error messages and context
//! - Using anyhow for error handling

use pyo3::prelude::*;
use pyo3::exceptions::{
    PyValueError, PyTypeError, PyZeroDivisionError,
    PyIndexError, PyKeyError, PyRuntimeError
};

/// Divides two numbers, handling division by zero.
///
/// Args:
///     a: Numerator
///     b: Denominator
///
/// Returns:
///     The quotient a / b
///
/// Raises:
///     ZeroDivisionError: If b is zero
#[pyfunction]
fn divide(a: f64, b: f64) -> PyResult<f64> {
    if b == 0.0 {
        Err(PyZeroDivisionError::new_err("Cannot divide by zero"))
    } else {
        Ok(a / b)
    }
}

/// Computes square root, validating input.
///
/// Args:
///     x: The number to compute square root of
///
/// Returns:
///     The square root of x
///
/// Raises:
///     ValueError: If x is negative
#[pyfunction]
fn sqrt(x: f64) -> PyResult<f64> {
    if x < 0.0 {
        Err(PyValueError::new_err(format!(
            "Cannot compute square root of negative number: {}",
            x
        )))
    } else {
        Ok(x.sqrt())
    }
}

/// Parses a string to integer.
///
/// Args:
///     s: String to parse
///
/// Returns:
///     Parsed integer
///
/// Raises:
///     ValueError: If string cannot be parsed as integer
#[pyfunction]
fn parse_int(s: &str) -> PyResult<i64> {
    s.parse::<i64>()
        .map_err(|e| PyValueError::new_err(format!("Invalid integer '{}': {}", s, e)))
}

/// Gets element at index from a list.
///
/// Args:
///     items: List of strings
///     index: Index to retrieve
///
/// Returns:
///     Element at the given index
///
/// Raises:
///     IndexError: If index is out of bounds
#[pyfunction]
fn get_at_index(items: Vec<String>, index: usize) -> PyResult<String> {
    items.get(index)
        .cloned()
        .ok_or_else(|| PyIndexError::new_err(format!(
            "Index {} out of bounds for list of length {}",
            index, items.len()
        )))
}

/// Validates age value.
///
/// Args:
///     age: Age value to validate
///
/// Returns:
///     The validated age
///
/// Raises:
///     ValueError: If age is negative or unreasonably large
///     TypeError: If age is not an integer (handled by PyO3)
#[pyfunction]
fn validate_age(age: i32) -> PyResult<i32> {
    if age < 0 {
        return Err(PyValueError::new_err("Age cannot be negative"));
    }
    if age > 150 {
        return Err(PyValueError::new_err("Age seems unreasonably large"));
    }
    Ok(age)
}

/// Demonstrates multiple validation steps with context.
///
/// Args:
///     value: String value to process
///     min_length: Minimum length requirement
///     max_length: Maximum length requirement
///
/// Returns:
///     Validated and trimmed value
///
/// Raises:
///     ValueError: If validation fails with detailed context
#[pyfunction]
fn validate_string(value: &str, min_length: usize, max_length: usize) -> PyResult<String> {
    // Validation: min < max
    if min_length > max_length {
        return Err(PyValueError::new_err(format!(
            "Invalid range: min_length ({}) > max_length ({})",
            min_length, max_length
        )));
    }

    let trimmed = value.trim();

    // Validation: minimum length
    if trimmed.len() < min_length {
        return Err(PyValueError::new_err(format!(
            "String too short: expected at least {} characters, got {}",
            min_length, trimmed.len()
        )));
    }

    // Validation: maximum length
    if trimmed.len() > max_length {
        return Err(PyValueError::new_err(format!(
            "String too long: expected at most {} characters, got {}",
            max_length, trimmed.len()
        )));
    }

    Ok(trimmed.to_string())
}

/// Simulates a runtime error condition.
///
/// Args:
///     should_fail: Whether to trigger an error
///
/// Returns:
///     Success message
///
/// Raises:
///     RuntimeError: If should_fail is True
#[pyfunction]
fn risky_operation(should_fail: bool) -> PyResult<String> {
    if should_fail {
        Err(PyRuntimeError::new_err(
            "Operation failed due to runtime condition"
        ))
    } else {
        Ok("Operation succeeded".to_string())
    }
}

/// Demonstrates chaining operations that can fail.
///
/// Args:
///     a: First number (string)
///     b: Second number (string)
///
/// Returns:
///     Result of parsing and dividing a/b
///
/// Raises:
///     ValueError: If parsing fails
///     ZeroDivisionError: If b is zero
#[pyfunction]
fn parse_and_divide(a: &str, b: &str) -> PyResult<f64> {
    let num_a = a.parse::<f64>()
        .map_err(|_| PyValueError::new_err(format!("Cannot parse '{}' as number", a)))?;

    let num_b = b.parse::<f64>()
        .map_err(|_| PyValueError::new_err(format!("Cannot parse '{}' as number", b)))?;

    if num_b == 0.0 {
        return Err(PyZeroDivisionError::new_err("Cannot divide by zero"));
    }

    Ok(num_a / num_b)
}

/// Safe get from a dictionary-like structure.
///
/// Args:
///     key: Key to look up
///     data: Dictionary of data
///
/// Returns:
///     Value associated with key
///
/// Raises:
///     KeyError: If key is not found
#[pyfunction]
fn safe_get(key: &str, data: std::collections::HashMap<String, String>) -> PyResult<String> {
    data.get(key)
        .cloned()
        .ok_or_else(|| PyKeyError::new_err(format!("Key '{}' not found", key)))
}

/// Type-checks and processes input.
///
/// Args:
///     value: Either a number or a string representation
///
/// Returns:
///     Processed value as float
///
/// Raises:
///     TypeError: If value cannot be converted
#[pyfunction]
fn process_value(py: Python, value: &PyAny) -> PyResult<f64> {
    // Try as float first
    if let Ok(f) = value.extract::<f64>() {
        return Ok(f);
    }

    // Try as string that can be parsed
    if let Ok(s) = value.extract::<String>() {
        return s.parse::<f64>()
            .map_err(|_| PyTypeError::new_err(format!(
                "Cannot convert '{}' to float", s
            )));
    }

    // Not a supported type
    Err(PyTypeError::new_err(format!(
        "Expected float or string, got {}",
        value.get_type().name()?
    )))
}

#[pymodule]
fn error_handling(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(divide, m)?)?;
    m.add_function(wrap_pyfunction!(sqrt, m)?)?;
    m.add_function(wrap_pyfunction!(parse_int, m)?)?;
    m.add_function(wrap_pyfunction!(get_at_index, m)?)?;
    m.add_function(wrap_pyfunction!(validate_age, m)?)?;
    m.add_function(wrap_pyfunction!(validate_string, m)?)?;
    m.add_function(wrap_pyfunction!(risky_operation, m)?)?;
    m.add_function(wrap_pyfunction!(parse_and_divide, m)?)?;
    m.add_function(wrap_pyfunction!(safe_get, m)?)?;
    m.add_function(wrap_pyfunction!(process_value, m)?)?;

    Ok(())
}
