//! Feature flags and conditional compilation
//!
//! Demonstrates using Cargo features to conditionally include functionality,
//! reducing binary size and dependencies for minimal builds.

use pyo3::prelude::*;

/// Basic arithmetic operations (always available).
///
/// Args:
///     a: First number
///     b: Second number
///
/// Returns:
///     Sum of a and b
#[pyfunction]
fn add(a: i64, b: i64) -> i64 {
    a + b
}

// JSON feature - only compiled if "json" feature is enabled
#[cfg(feature = "json")]
use serde::{Deserialize, Serialize};

#[cfg(feature = "json")]
#[derive(Serialize, Deserialize)]
#[pyclass]
pub struct JsonData {
    #[pyo3(get, set)]
    pub value: String,
    #[pyo3(get, set)]
    pub count: i64,
}

#[cfg(feature = "json")]
#[pymethods]
impl JsonData {
    #[new]
    fn new(value: String, count: i64) -> Self {
        JsonData { value, count }
    }
}

#[cfg(feature = "json")]
#[pyfunction]
fn to_json_string(data: &JsonData) -> PyResult<String> {
    serde_json::to_string(data).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Serialization error: {}", e))
    })
}

#[cfg(feature = "json")]
#[pyfunction]
fn from_json_string(s: &str) -> PyResult<JsonData> {
    serde_json::from_str(s).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Deserialization error: {}", e))
    })
}

// Advanced math - only with "advanced_math" feature
#[cfg(feature = "advanced_math")]
#[pyfunction]
fn fast_factorial(n: u64) -> PyResult<f64> {
    use statrs::function::factorial;
    Ok(factorial::factorial(n))
}

#[cfg(feature = "advanced_math")]
#[pyfunction]
fn gamma(x: f64) -> f64 {
    use statrs::function::gamma;
    gamma::gamma(x)
}

// Parallel processing - only with "parallel" feature
#[cfg(feature = "parallel")]
#[pyfunction]
fn parallel_sum(values: Vec<i64>) -> i64 {
    use rayon::prelude::*;
    values.par_iter().sum()
}

#[cfg(feature = "parallel")]
#[pyfunction]
fn parallel_map_double(values: Vec<i64>) -> Vec<i64> {
    use rayon::prelude::*;
    values.par_iter().map(|x| x * 2).collect()
}

/// Get information about enabled features.
///
/// Returns:
///     Dictionary showing which features are enabled
#[pyfunction]
fn feature_info(py: Python) -> PyResult<PyObject> {
    let dict = pyo3::types::PyDict::new(py);

    // Always enabled
    dict.set_item("core", true)?;

    // Conditional features
    dict.set_item("json", cfg!(feature = "json"))?;
    dict.set_item("advanced_math", cfg!(feature = "advanced_math"))?;
    dict.set_item("parallel", cfg!(feature = "parallel"))?;

    Ok(dict.into())
}

/// Check if a specific feature is enabled.
///
/// Args:
///     feature_name: Name of the feature to check
///
/// Returns:
///     True if feature is enabled, False otherwise
#[pyfunction]
fn has_feature(feature_name: &str) -> bool {
    match feature_name {
        "json" => cfg!(feature = "json"),
        "advanced_math" => cfg!(feature = "advanced_math"),
        "parallel" => cfg!(feature = "parallel"),
        _ => false,
    }
}

/// Package demonstrating feature flags and conditional compilation.
#[pymodule]
fn feature_flags(_py: Python, m: &PyModule) -> PyResult<()> {
    // Core functions - always available
    m.add_function(wrap_pyfunction!(add, m)?)?;
    m.add_function(wrap_pyfunction!(feature_info, m)?)?;
    m.add_function(wrap_pyfunction!(has_feature, m)?)?;

    // JSON feature
    #[cfg(feature = "json")]
    {
        m.add_class::<JsonData>()?;
        m.add_function(wrap_pyfunction!(to_json_string, m)?)?;
        m.add_function(wrap_pyfunction!(from_json_string, m)?)?;
    }

    // Advanced math feature
    #[cfg(feature = "advanced_math")]
    {
        m.add_function(wrap_pyfunction!(fast_factorial, m)?)?;
        m.add_function(wrap_pyfunction!(gamma, m)?)?;
    }

    // Parallel feature
    #[cfg(feature = "parallel")]
    {
        m.add_function(wrap_pyfunction!(parallel_sum, m)?)?;
        m.add_function(wrap_pyfunction!(parallel_map_double, m)?)?;
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add() {
        assert_eq!(add(2, 3), 5);
    }

    #[cfg(feature = "json")]
    #[test]
    fn test_json() {
        let data = JsonData::new("test".to_string(), 42);
        let json = to_json_string(&data).unwrap();
        assert!(json.contains("test"));
    }

    #[cfg(feature = "parallel")]
    #[test]
    fn test_parallel() {
        let result = parallel_sum(vec![1, 2, 3, 4, 5]);
        assert_eq!(result, 15);
    }
}
