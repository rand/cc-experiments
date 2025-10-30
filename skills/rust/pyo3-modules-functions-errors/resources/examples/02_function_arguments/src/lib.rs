//! Example 02: Function Arguments and Signatures
//!
//! This example demonstrates:
//! - Optional arguments with Option<T>
//! - Default values using #[pyo3(signature = (...))]
//! - Keyword-only arguments
//! - Variable arguments (*args)
//! - Keyword arguments (**kwargs)
//! - Multiple signature patterns

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};

/// Simple function with optional argument.
///
/// Args:
///     name: Required name
///     age: Optional age (defaults to None)
///
/// Returns:
///     A formatted string with name and optionally age
#[pyfunction]
fn greet_person(name: &str, age: Option<u32>) -> String {
    match age {
        Some(a) => format!("{} is {} years old", name, a),
        None => format!("Hello, {}", name),
    }
}

/// Function with default values using signature attribute.
///
/// Args:
///     base: The base value (required)
///     exponent: The exponent (default: 2)
///     modulo: Optional modulo operation (default: None)
///
/// Returns:
///     base^exponent % modulo (if modulo provided)
#[pyfunction]
#[pyo3(signature = (base, exponent=2, modulo=None))]
fn power(base: i64, exponent: u32, modulo: Option<i64>) -> i64 {
    let result = base.pow(exponent);
    match modulo {
        Some(m) => result % m,
        None => result,
    }
}

/// Function with keyword-only arguments.
///
/// Args:
///     text: The text to process (required)
///     uppercase: Convert to uppercase (keyword-only, default: False)
///     trim: Trim whitespace (keyword-only, default: True)
///     repeat: Number of repetitions (keyword-only, default: 1)
///
/// Returns:
///     Processed text
#[pyfunction]
#[pyo3(signature = (text, *, uppercase=false, trim=true, repeat=1))]
fn process_text(text: &str, uppercase: bool, trim: bool, repeat: usize) -> String {
    let mut result = text.to_string();

    if trim {
        result = result.trim().to_string();
    }

    if uppercase {
        result = result.to_uppercase();
    }

    result.repeat(repeat)
}

/// Function accepting variable positional arguments (*args).
///
/// Args:
///     *numbers: Variable number of integers
///
/// Returns:
///     Sum of all numbers
#[pyfunction]
fn sum_numbers(numbers: &PyTuple) -> PyResult<i64> {
    let mut total: i64 = 0;
    for num in numbers.iter() {
        total += num.extract::<i64>()?;
    }
    Ok(total)
}

/// Function accepting variable keyword arguments (**kwargs).
///
/// Args:
///     **kwargs: Variable keyword arguments
///
/// Returns:
///     Dict with keys converted to uppercase
#[pyfunction]
fn uppercase_keys(kwargs: Option<&PyDict>) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let result = PyDict::new(py);

        if let Some(kw) = kwargs {
            for (key, value) in kw.iter() {
                let key_str: String = key.extract()?;
                result.set_item(key_str.to_uppercase(), value)?;
            }
        }

        Ok(result.into())
    })
}

/// Function with both *args and **kwargs.
///
/// Args:
///     prefix: Required prefix string
///     *items: Variable positional arguments
///     separator: Keyword-only separator (default: ", ")
///     **options: Variable keyword arguments
///
/// Returns:
///     Dict with formatted string and options
#[pyfunction]
#[pyo3(signature = (prefix, *items, separator=", ", **options))]
fn combine_args(
    prefix: &str,
    items: &PyTuple,
    separator: &str,
    options: Option<&PyDict>,
) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let result = PyDict::new(py);

        // Format items
        let mut formatted_items = Vec::new();
        for item in items.iter() {
            formatted_items.push(item.to_string());
        }
        let items_str = formatted_items.join(separator);
        let text = format!("{}: {}", prefix, items_str);
        result.set_item("text", text)?;

        // Add options
        if let Some(opts) = options {
            result.set_item("options", opts)?;
        }

        Ok(result.into())
    })
}

/// Function demonstrating all argument types together.
///
/// Args:
///     required: Required positional argument
///     optional: Optional positional argument (default: None)
///     with_default: Argument with default value (default: 42)
///     keyword_only: Keyword-only argument (default: "default")
///
/// Returns:
///     Dict containing all provided arguments
#[pyfunction]
#[pyo3(signature = (required, optional=None, with_default=42, *, keyword_only="default"))]
fn complex_signature(
    required: i64,
    optional: Option<String>,
    with_default: i64,
    keyword_only: &str,
) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let result = PyDict::new(py);
        result.set_item("required", required)?;
        result.set_item("optional", optional)?;
        result.set_item("with_default", with_default)?;
        result.set_item("keyword_only", keyword_only)?;
        Ok(result.into())
    })
}

/// Function that formats configuration from various argument types.
///
/// Args:
///     name: Configuration name (required)
///     values: List of values (default: empty)
///     enabled: Whether configuration is enabled (default: True)
///     tags: Additional tags (keyword-only, default: empty)
///
/// Returns:
///     Formatted configuration string
#[pyfunction]
#[pyo3(signature = (name, values=None, enabled=true, *, tags=None))]
fn make_config(
    name: &str,
    values: Option<Vec<String>>,
    enabled: bool,
    tags: Option<Vec<String>>,
) -> String {
    let mut config = format!("Config: {}\n", name);
    config.push_str(&format!("Enabled: {}\n", enabled));

    if let Some(vals) = values {
        config.push_str(&format!("Values: {}\n", vals.join(", ")));
    }

    if let Some(tag_list) = tags {
        config.push_str(&format!("Tags: {}\n", tag_list.join(", ")));
    }

    config
}

#[pymodule]
fn function_arguments(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(greet_person, m)?)?;
    m.add_function(wrap_pyfunction!(power, m)?)?;
    m.add_function(wrap_pyfunction!(process_text, m)?)?;
    m.add_function(wrap_pyfunction!(sum_numbers, m)?)?;
    m.add_function(wrap_pyfunction!(uppercase_keys, m)?)?;
    m.add_function(wrap_pyfunction!(combine_args, m)?)?;
    m.add_function(wrap_pyfunction!(complex_signature, m)?)?;
    m.add_function(wrap_pyfunction!(make_config, m)?)?;

    Ok(())
}
