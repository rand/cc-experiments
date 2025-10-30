use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

/// Data structure for JSON processing results
#[pyclass]
#[derive(Clone, Serialize, Deserialize)]
pub struct JsonStats {
    #[pyo3(get)]
    pub keys: usize,
    #[pyo3(get)]
    pub total_size: usize,
    #[pyo3(get)]
    pub nested_objects: usize,
    #[pyo3(get)]
    pub arrays: usize,
}

#[pymethods]
impl JsonStats {
    fn __repr__(&self) -> String {
        format!(
            "JsonStats(keys={}, size={}, objects={}, arrays={})",
            self.keys, self.total_size, self.nested_objects, self.arrays
        )
    }
}

/// Validate JSON file and return statistics
///
/// # Arguments
/// * `filepath` - Path to JSON file
///
/// # Returns
/// JsonStats object with analysis results
#[pyfunction]
fn validate_json(filepath: String) -> PyResult<JsonStats> {
    let content = fs::read_to_string(&filepath).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to read {}: {}", filepath, e))
    })?;

    let value: serde_json::Value = serde_json::from_str(&content).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid JSON: {}", e))
    })?;

    let stats = analyze_json(&value);

    Ok(JsonStats {
        keys: stats.0,
        total_size: content.len(),
        nested_objects: stats.1,
        arrays: stats.2,
    })
}

/// Recursively analyze JSON structure
fn analyze_json(value: &serde_json::Value) -> (usize, usize, usize) {
    match value {
        serde_json::Value::Object(map) => {
            let mut keys = map.len();
            let mut objects = 1;
            let mut arrays = 0;

            for (_, v) in map.iter() {
                let (k, o, a) = analyze_json(v);
                keys += k;
                objects += o;
                arrays += a;
            }

            (keys, objects - 1, arrays)
        }
        serde_json::Value::Array(arr) => {
            let mut keys = 0;
            let mut objects = 0;
            let mut arrays = 1;

            for v in arr.iter() {
                let (k, o, a) = analyze_json(v);
                keys += k;
                objects += o;
                arrays += a;
            }

            (keys, objects, arrays)
        }
        _ => (0, 0, 0),
    }
}

/// Format JSON with specified indentation
///
/// # Arguments
/// * `input_file` - Input JSON file path
/// * `output_file` - Output JSON file path (if None, returns formatted string)
/// * `indent` - Indentation level (spaces)
///
/// # Returns
/// Formatted JSON string if output_file is None, otherwise empty string
#[pyfunction]
fn format_json(
    input_file: String,
    output_file: Option<String>,
    indent: usize,
) -> PyResult<String> {
    let content = fs::read_to_string(&input_file).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to read {}: {}", input_file, e))
    })?;

    let value: serde_json::Value = serde_json::from_str(&content).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid JSON: {}", e))
    })?;

    let formatted = if indent == 0 {
        serde_json::to_string(&value).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to format: {}", e))
        })?
    } else {
        serde_json::to_string_pretty(&value).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to format: {}", e))
        })?
    };

    if let Some(output) = output_file {
        fs::write(&output, &formatted).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to write {}: {}", output, e))
        })?;
        Ok(String::new())
    } else {
        Ok(formatted)
    }
}

/// Merge multiple JSON files
///
/// # Arguments
/// * `input_files` - List of JSON file paths to merge
/// * `output_file` - Output file path
///
/// # Returns
/// Number of files successfully merged
#[pyfunction]
fn merge_json(input_files: Vec<String>, output_file: String) -> PyResult<usize> {
    let mut merged = serde_json::Map::new();
    let mut count = 0;

    for filepath in input_files {
        let content = match fs::read_to_string(&filepath) {
            Ok(c) => c,
            Err(_) => continue,
        };

        let value: serde_json::Value = match serde_json::from_str(&content) {
            Ok(v) => v,
            Err(_) => continue,
        };

        if let serde_json::Value::Object(map) = value {
            for (key, val) in map {
                merged.insert(key, val);
            }
            count += 1;
        }
    }

    let output = serde_json::Value::Object(merged);
    let formatted = serde_json::to_string_pretty(&output).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to format: {}", e))
    })?;

    fs::write(&output_file, formatted).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to write {}: {}", output_file, e))
    })?;

    Ok(count)
}

/// Extract value from JSON file using path notation
///
/// # Arguments
/// * `filepath` - JSON file path
/// * `path` - Dot-separated path (e.g., "user.name")
///
/// # Returns
/// String representation of the value
#[pyfunction]
fn extract_json_value(filepath: String, path: String) -> PyResult<String> {
    let content = fs::read_to_string(&filepath).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to read {}: {}", filepath, e))
    })?;

    let mut value: serde_json::Value = serde_json::from_str(&content).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid JSON: {}", e))
    })?;

    for key in path.split('.') {
        value = value.get(key).cloned().ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!("Key not found: {}", key))
        })?;
    }

    Ok(value.to_string())
}

#[pymodule]
fn typer_app(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<JsonStats>()?;
    m.add_function(wrap_pyfunction!(validate_json, m)?)?;
    m.add_function(wrap_pyfunction!(format_json, m)?)?;
    m.add_function(wrap_pyfunction!(merge_json, m)?)?;
    m.add_function(wrap_pyfunction!(extract_json_value, m)?)?;
    Ok(())
}
