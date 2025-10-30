//! Basic type conversions between Python and Rust
//!
//! This example demonstrates fundamental type conversions:
//! - Integers (i32, i64, u32, u64, isize, usize)
//! - Floats (f32, f64)
//! - Strings (String, &str)
//! - Booleans (bool)
//! - None/Option<T>

use pyo3::prelude::*;

/// Convert Python int to Rust and back
#[pyfunction]
fn double_integer(x: i64) -> PyResult<i64> {
    Ok(x * 2)
}

/// Work with unsigned integers
#[pyfunction]
fn increment_unsigned(x: u64) -> PyResult<u64> {
    x.checked_add(1)
        .ok_or_else(|| pyo3::exceptions::PyOverflowError::new_err("Overflow detected"))
}

/// Convert Python float to Rust and back
#[pyfunction]
fn square_float(x: f64) -> PyResult<f64> {
    Ok(x * x)
}

/// Work with Python strings
#[pyfunction]
fn greet(name: &str) -> PyResult<String> {
    Ok(format!("Hello, {}!", name))
}

/// Return a string slice (converted to Python str)
#[pyfunction]
fn get_language() -> PyResult<&'static str> {
    Ok("Rust")
}

/// Work with booleans
#[pyfunction]
fn negate_bool(value: bool) -> PyResult<bool> {
    Ok(!value)
}

/// Demonstrate Option<T> conversion (None in Python)
#[pyfunction]
fn optional_double(x: Option<i64>) -> PyResult<Option<i64>> {
    Ok(x.map(|n| n * 2))
}

/// Return None explicitly
#[pyfunction]
fn always_none() -> PyResult<Option<i64>> {
    Ok(None)
}

/// Work with multiple argument types
#[pyfunction]
fn format_info(name: &str, age: u32, score: f64, active: bool) -> PyResult<String> {
    Ok(format!(
        "Name: {}, Age: {}, Score: {:.2}, Active: {}",
        name, age, score, active
    ))
}

/// Demonstrate type validation
#[pyfunction]
fn validate_positive(x: i64) -> PyResult<i64> {
    if x <= 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Value must be positive",
        ));
    }
    Ok(x)
}

/// Work with various integer sizes
#[pyfunction]
fn sum_different_sizes(a: i32, b: i64, c: u32) -> PyResult<i64> {
    let result = i64::from(a) + b + i64::from(c);
    Ok(result)
}

/// Demonstrate f32 vs f64
#[pyfunction]
fn precision_comparison(x: f64) -> PyResult<(f32, f64)> {
    Ok((x as f32, x))
}

/// Convert Python bytes to string (UTF-8)
#[pyfunction]
fn bytes_to_string(data: &[u8]) -> PyResult<String> {
    String::from_utf8(data.to_vec())
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid UTF-8: {}", e)))
}

/// Work with boolean logic
#[pyfunction]
fn logical_and(a: bool, b: bool) -> PyResult<bool> {
    Ok(a && b)
}

/// Demonstrate comprehensive type handling
#[pyfunction]
fn complex_calculation(
    base: i64,
    multiplier: f64,
    offset: Option<i64>,
    enabled: bool,
) -> PyResult<Option<f64>> {
    if !enabled {
        return Ok(None);
    }

    let base_value = base as f64 * multiplier;
    let final_value = match offset {
        Some(o) => base_value + o as f64,
        None => base_value,
    };

    Ok(Some(final_value))
}

/// Python module initialization
#[pymodule]
fn basic_types(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(double_integer, m)?)?;
    m.add_function(wrap_pyfunction!(increment_unsigned, m)?)?;
    m.add_function(wrap_pyfunction!(square_float, m)?)?;
    m.add_function(wrap_pyfunction!(greet, m)?)?;
    m.add_function(wrap_pyfunction!(get_language, m)?)?;
    m.add_function(wrap_pyfunction!(negate_bool, m)?)?;
    m.add_function(wrap_pyfunction!(optional_double, m)?)?;
    m.add_function(wrap_pyfunction!(always_none, m)?)?;
    m.add_function(wrap_pyfunction!(format_info, m)?)?;
    m.add_function(wrap_pyfunction!(validate_positive, m)?)?;
    m.add_function(wrap_pyfunction!(sum_different_sizes, m)?)?;
    m.add_function(wrap_pyfunction!(precision_comparison, m)?)?;
    m.add_function(wrap_pyfunction!(bytes_to_string, m)?)?;
    m.add_function(wrap_pyfunction!(logical_and, m)?)?;
    m.add_function(wrap_pyfunction!(complex_calculation, m)?)?;
    Ok(())
}
