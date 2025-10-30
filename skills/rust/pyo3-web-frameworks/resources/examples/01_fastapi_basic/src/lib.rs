//! Basic FastAPI endpoint integration with PyO3
//!
//! This example demonstrates:
//! - Creating simple computation functions in Rust
//! - Exposing them to FastAPI endpoints
//! - Type conversions between Python and Rust
//! - Error handling in web context
//! - Basic HTTP request processing

use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

/// Compute the square root sum of squares for a list of numbers
///
/// This is a CPU-intensive operation that benefits from Rust's performance
#[pyfunction]
fn compute_magnitude(data: Vec<f64>) -> PyResult<f64> {
    if data.is_empty() {
        return Err(PyValueError::new_err("Data cannot be empty"));
    }

    let sum_of_squares: f64 = data.iter().map(|x| x * x).sum();
    Ok(sum_of_squares.sqrt())
}

/// Process a batch of numbers: filter, transform, and aggregate
#[pyfunction]
fn process_batch(numbers: Vec<f64>, threshold: f64) -> PyResult<(Vec<f64>, f64, usize)> {
    let filtered: Vec<f64> = numbers
        .into_iter()
        .filter(|&x| x > threshold)
        .map(|x| x * 2.0)
        .collect();

    let sum: f64 = filtered.iter().sum();
    let count = filtered.len();

    Ok((filtered, sum, count))
}

/// Validate and normalize email addresses
#[pyfunction]
fn normalize_email(email: String) -> PyResult<String> {
    let trimmed = email.trim().to_lowercase();

    if !trimmed.contains('@') {
        return Err(PyValueError::new_err("Invalid email: missing @"));
    }

    if trimmed.len() < 3 {
        return Err(PyValueError::new_err("Invalid email: too short"));
    }

    Ok(trimmed)
}

/// Compute statistics for a dataset
#[pyfunction]
fn compute_stats(data: Vec<f64>) -> PyResult<(f64, f64, f64, f64)> {
    if data.is_empty() {
        return Err(PyValueError::new_err("Cannot compute stats on empty data"));
    }

    let sum: f64 = data.iter().sum();
    let mean = sum / data.len() as f64;

    let min = data.iter().cloned().fold(f64::INFINITY, f64::min);
    let max = data.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

    let variance = data.iter()
        .map(|x| (x - mean).powi(2))
        .sum::<f64>() / data.len() as f64;
    let std_dev = variance.sqrt();

    Ok((mean, std_dev, min, max))
}

/// Fast string processing: count words, chars, lines
#[pyfunction]
fn analyze_text(text: String) -> PyResult<(usize, usize, usize)> {
    let char_count = text.chars().count();
    let word_count = text.split_whitespace().count();
    let line_count = text.lines().count();

    Ok((char_count, word_count, line_count))
}

/// Hash a string using a simple algorithm
#[pyfunction]
fn hash_string(input: String) -> PyResult<u64> {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let mut hasher = DefaultHasher::new();
    input.hash(&mut hasher);
    Ok(hasher.finish())
}

/// Validate a user ID format
#[pyfunction]
fn validate_user_id(user_id: String) -> PyResult<bool> {
    // User ID must be alphanumeric and between 3-20 chars
    let valid_length = user_id.len() >= 3 && user_id.len() <= 20;
    let valid_chars = user_id.chars().all(|c| c.is_alphanumeric());

    Ok(valid_length && valid_chars)
}

/// Convert temperature from Celsius to Fahrenheit
#[pyfunction]
fn celsius_to_fahrenheit(celsius: f64) -> PyResult<f64> {
    Ok(celsius * 9.0 / 5.0 + 32.0)
}

/// Compute factorial (with overflow checking)
#[pyfunction]
fn factorial(n: u64) -> PyResult<u64> {
    if n > 20 {
        return Err(PyValueError::new_err("Input too large (max 20)"));
    }

    let mut result = 1u64;
    for i in 1..=n {
        result = result.checked_mul(i)
            .ok_or_else(|| PyValueError::new_err("Overflow in factorial"))?;
    }

    Ok(result)
}

/// Check if a number is prime
#[pyfunction]
fn is_prime(n: u64) -> PyResult<bool> {
    if n < 2 {
        return Ok(false);
    }
    if n == 2 {
        return Ok(true);
    }
    if n % 2 == 0 {
        return Ok(false);
    }

    let sqrt_n = (n as f64).sqrt() as u64;
    for i in (3..=sqrt_n).step_by(2) {
        if n % i == 0 {
            return Ok(false);
        }
    }

    Ok(true)
}

/// Python module initialization
#[pymodule]
fn fastapi_basic(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_magnitude, m)?)?;
    m.add_function(wrap_pyfunction!(process_batch, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_email, m)?)?;
    m.add_function(wrap_pyfunction!(compute_stats, m)?)?;
    m.add_function(wrap_pyfunction!(analyze_text, m)?)?;
    m.add_function(wrap_pyfunction!(hash_string, m)?)?;
    m.add_function(wrap_pyfunction!(validate_user_id, m)?)?;
    m.add_function(wrap_pyfunction!(celsius_to_fahrenheit, m)?)?;
    m.add_function(wrap_pyfunction!(factorial, m)?)?;
    m.add_function(wrap_pyfunction!(is_prime, m)?)?;
    Ok(())
}
