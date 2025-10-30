//! Example 05: Custom Exception Types
//!
//! This example demonstrates:
//! - Creating custom Python exception classes in Rust
//! - Exception inheritance hierarchies
//! - Adding attributes to exceptions
//! - Using custom exceptions in functions

use pyo3::prelude::*;
use pyo3::exceptions::PyException;
use pyo3::create_exception;

// Define custom exception types using create_exception! macro

// Base exception for validation errors
create_exception!(custom_exceptions, ValidationError, PyException, "Base class for validation errors");

// Specific validation exceptions inheriting from ValidationError
create_exception!(custom_exceptions, RangeError, ValidationError, "Value is out of valid range");
create_exception!(custom_exceptions, FormatError, ValidationError, "Invalid format");
create_exception!(custom_exceptions, LengthError, ValidationError, "Invalid length");

// Base exception for processing errors
create_exception!(custom_exceptions, ProcessingError, PyException, "Base class for processing errors");

// Specific processing exceptions
create_exception!(custom_exceptions, ParseError, ProcessingError, "Failed to parse input");
create_exception!(custom_exceptions, TransformError, ProcessingError, "Failed to transform data");
create_exception!(custom_exceptions, ComputationError, ProcessingError, "Computation failed");

/// Custom exception class with attributes.
#[pyclass(extends=PyException)]
struct DetailedError {
    #[pyo3(get)]
    code: i32,
    #[pyo3(get)]
    context: String,
}

#[pymethods]
impl DetailedError {
    #[new]
    fn new(message: String, code: i32, context: String) -> (Self, PyException) {
        (
            DetailedError { code, context },
            PyException::new_err(message),
        )
    }

    fn __str__(&self) -> String {
        format!("[Error {}] {}", self.code, self.context)
    }

    fn __repr__(&self) -> String {
        format!("DetailedError(code={}, context='{}')", self.code, self.context)
    }
}

/// Validates a number is within range.
///
/// Args:
///     value: The number to validate
///     min_val: Minimum valid value
///     max_val: Maximum valid value
///
/// Returns:
///     The validated value
///
/// Raises:
///     RangeError: If value is outside [min_val, max_val]
#[pyfunction]
fn validate_range(value: i32, min_val: i32, max_val: i32) -> PyResult<i32> {
    if value < min_val || value > max_val {
        Err(RangeError::new_err(format!(
            "Value {} is outside valid range [{}, {}]",
            value, min_val, max_val
        )))
    } else {
        Ok(value)
    }
}

/// Validates email format.
///
/// Args:
///     email: The email address to validate
///
/// Returns:
///     The validated email
///
/// Raises:
///     FormatError: If email format is invalid
#[pyfunction]
fn validate_email(email: &str) -> PyResult<String> {
    if !email.contains('@') || !email.contains('.') {
        return Err(FormatError::new_err(format!(
            "Invalid email format: '{}'", email
        )));
    }

    let parts: Vec<&str> = email.split('@').collect();
    if parts.len() != 2 || parts[0].is_empty() || parts[1].is_empty() {
        return Err(FormatError::new_err(format!(
            "Invalid email structure: '{}'", email
        )));
    }

    Ok(email.to_string())
}

/// Validates string length.
///
/// Args:
///     text: The string to validate
///     min_length: Minimum length (inclusive)
///     max_length: Maximum length (inclusive)
///
/// Returns:
///     The validated string
///
/// Raises:
///     LengthError: If length is outside bounds
#[pyfunction]
fn validate_length(text: &str, min_length: usize, max_length: usize) -> PyResult<String> {
    let length = text.len();

    if length < min_length {
        return Err(LengthError::new_err(format!(
            "String too short: {} characters (minimum {})",
            length, min_length
        )));
    }

    if length > max_length {
        return Err(LengthError::new_err(format!(
            "String too long: {} characters (maximum {})",
            length, max_length
        )));
    }

    Ok(text.to_string())
}

/// Parses a structured format: "key:value".
///
/// Args:
///     text: Text to parse
///
/// Returns:
///     Tuple of (key, value)
///
/// Raises:
///     ParseError: If format is invalid
#[pyfunction]
fn parse_key_value(text: &str) -> PyResult<(String, String)> {
    let parts: Vec<&str> = text.split(':').collect();

    if parts.len() != 2 {
        return Err(ParseError::new_err(format!(
            "Expected 'key:value' format, got '{}'", text
        )));
    }

    let key = parts[0].trim();
    let value = parts[1].trim();

    if key.is_empty() || value.is_empty() {
        return Err(ParseError::new_err(
            "Both key and value must be non-empty"
        ));
    }

    Ok((key.to_string(), value.to_string()))
}

/// Transforms text to title case.
///
/// Args:
///     text: Text to transform
///
/// Returns:
///     Transformed text
///
/// Raises:
///     TransformError: If transformation fails
#[pyfunction]
fn transform_title_case(text: &str) -> PyResult<String> {
    if text.is_empty() {
        return Err(TransformError::new_err(
            "Cannot transform empty string"
        ));
    }

    let result: String = text
        .split_whitespace()
        .map(|word| {
            let mut chars = word.chars();
            match chars.next() {
                Some(first) => {
                    first.to_uppercase().collect::<String>()
                        + &chars.as_str().to_lowercase()
                }
                None => String::new(),
            }
        })
        .collect::<Vec<String>>()
        .join(" ");

    Ok(result)
}

/// Computes factorial with overflow checking.
///
/// Args:
///     n: Number to compute factorial of
///
/// Returns:
///     Factorial of n
///
/// Raises:
///     ComputationError: If computation fails or overflows
#[pyfunction]
fn safe_factorial(n: u32) -> PyResult<u64> {
    if n > 20 {
        return Err(ComputationError::new_err(format!(
            "Factorial({}) would overflow u64", n
        )));
    }

    let mut result: u64 = 1;
    for i in 2..=n {
        result = result.checked_mul(i as u64)
            .ok_or_else(|| ComputationError::new_err("Overflow during factorial computation"))?;
    }

    Ok(result)
}

/// Creates a detailed error with additional context.
///
/// Args:
///     message: Error message
///     code: Error code
///     context: Additional context
///
/// Raises:
///     DetailedError: Always raises with provided details
#[pyfunction]
fn raise_detailed_error(message: String, code: i32, context: String) -> PyResult<()> {
    Err(PyErr::from_type(
        Python::with_gil(|py| DetailedError::type_object(py)),
        (message, code, context),
    ))
}

#[pymodule]
fn custom_exceptions(py: Python, m: &PyModule) -> PyResult<()> {
    // Register custom exception types
    m.add("ValidationError", py.get_type::<ValidationError>())?;
    m.add("RangeError", py.get_type::<RangeError>())?;
    m.add("FormatError", py.get_type::<FormatError>())?;
    m.add("LengthError", py.get_type::<LengthError>())?;

    m.add("ProcessingError", py.get_type::<ProcessingError>())?;
    m.add("ParseError", py.get_type::<ParseError>())?;
    m.add("TransformError", py.get_type::<TransformError>())?;
    m.add("ComputationError", py.get_type::<ComputationError>())?;

    m.add_class::<DetailedError>()?;

    // Register functions
    m.add_function(wrap_pyfunction!(validate_range, m)?)?;
    m.add_function(wrap_pyfunction!(validate_email, m)?)?;
    m.add_function(wrap_pyfunction!(validate_length, m)?)?;
    m.add_function(wrap_pyfunction!(parse_key_value, m)?)?;
    m.add_function(wrap_pyfunction!(transform_title_case, m)?)?;
    m.add_function(wrap_pyfunction!(safe_factorial, m)?)?;
    m.add_function(wrap_pyfunction!(raise_detailed_error, m)?)?;

    Ok(())
}
