//! Dependency management example
//!
//! Demonstrates managing both Rust and Python dependencies,
//! including optional dependencies and version constraints.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json;

/// A simple data structure for demonstration.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct DataPoint {
    #[pyo3(get, set)]
    pub x: f64,
    #[pyo3(get, set)]
    pub y: f64,
    #[pyo3(get, set)]
    pub label: String,
}

#[pymethods]
impl DataPoint {
    /// Create a new DataPoint.
    ///
    /// Args:
    ///     x: X coordinate
    ///     y: Y coordinate
    ///     label: Point label
    ///
    /// Example:
    ///     >>> from dependencies_example import DataPoint
    ///     >>> point = DataPoint(1.0, 2.0, "A")
    #[new]
    fn new(x: f64, y: f64, label: String) -> Self {
        DataPoint { x, y, label }
    }

    /// Calculate distance from origin.
    ///
    /// Returns:
    ///     Euclidean distance from (0, 0)
    fn distance(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!("DataPoint({}, {}, '{}')", self.x, self.y, self.label)
    }
}

/// Serialize a DataPoint to JSON string.
///
/// Args:
///     point: DataPoint to serialize
///
/// Returns:
///     JSON string representation
///
/// Example:
///     >>> from dependencies_example import DataPoint, to_json
///     >>> point = DataPoint(1.0, 2.0, "A")
///     >>> to_json(point)
///     '{"x":1.0,"y":2.0,"label":"A"}'
#[pyfunction]
fn to_json(point: &DataPoint) -> PyResult<String> {
    serde_json::to_string(point).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Serialization failed: {}", e))
    })
}

/// Deserialize a DataPoint from JSON string.
///
/// Args:
///     json_str: JSON string to deserialize
///
/// Returns:
///     DataPoint instance
///
/// Raises:
///     ValueError: If JSON is invalid
///
/// Example:
///     >>> from dependencies_example import DataPoint, from_json
///     >>> point = from_json('{"x":1.0,"y":2.0,"label":"A"}')
///     >>> point.x
///     1.0
#[pyfunction]
fn from_json(json_str: &str) -> PyResult<DataPoint> {
    serde_json::from_str(json_str).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Deserialization failed: {}", e))
    })
}

/// Calculate statistics for a list of numbers using statrs.
///
/// Args:
///     values: List of numbers
///
/// Returns:
///     Dictionary with mean, median, std_dev
///
/// Example:
///     >>> from dependencies_example import statistics
///     >>> stats = statistics([1.0, 2.0, 3.0, 4.0, 5.0])
///     >>> stats['mean']
///     3.0
#[pyfunction]
fn statistics(values: Vec<f64>) -> PyResult<PyObject> {
    use statrs::statistics::{Data, OrderStatistics, Statistics};

    if values.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Cannot compute statistics for empty list",
        ));
    }

    let data = Data::new(values);

    Python::with_gil(|py| {
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("mean", data.mean().unwrap_or(0.0))?;
        dict.set_item("median", data.median())?;
        dict.set_item("std_dev", data.std_dev().unwrap_or(0.0))?;
        dict.set_item("min", data.min())?;
        dict.set_item("max", data.max())?;
        Ok(dict.into())
    })
}

/// Get dependency information.
///
/// Returns:
///     Dictionary with Rust dependency versions
#[pyfunction]
fn dependency_info(py: Python) -> PyResult<PyObject> {
    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("pyo3", env!("CARGO_PKG_VERSION_PRE").to_string())?;
    dict.set_item("serde", "installed")?;
    dict.set_item("serde_json", "installed")?;
    dict.set_item("statrs", "installed")?;
    Ok(dict.into())
}

/// Package demonstrating Rust and Python dependency management.
#[pymodule]
fn dependencies_example(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<DataPoint>()?;
    m.add_function(wrap_pyfunction!(to_json, m)?)?;
    m.add_function(wrap_pyfunction!(from_json, m)?)?;
    m.add_function(wrap_pyfunction!(statistics, m)?)?;
    m.add_function(wrap_pyfunction!(dependency_info, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_data_point() {
        let point = DataPoint::new(3.0, 4.0, "Test".to_string());
        assert_eq!(point.distance(), 5.0);
    }

    #[test]
    fn test_serialization() {
        let point = DataPoint::new(1.0, 2.0, "A".to_string());
        let json = to_json(&point).unwrap();
        assert!(json.contains("\"x\":1.0"));

        let deserialized = from_json(&json).unwrap();
        assert_eq!(deserialized.x, 1.0);
        assert_eq!(deserialized.label, "A");
    }

    #[test]
    fn test_statistics() {
        let values = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let result = statistics(values);
        assert!(result.is_ok());
    }
}
