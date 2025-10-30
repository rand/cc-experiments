use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;

#[derive(Serialize, Deserialize)]
struct Config {
    #[serde(flatten)]
    values: HashMap<String, serde_json::Value>,
}

/// Load configuration from TOML file
#[pyfunction]
fn load_toml(filepath: String) -> PyResult<PyObject> {
    let content = fs::read_to_string(&filepath).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to read {}: {}", filepath, e))
    })?;

    let config: Config = toml::from_str(&content).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid TOML: {}", e))
    })?;

    Python::with_gil(|py| {
        let dict = PyDict::new(py);
        for (key, value) in config.values {
            dict.set_item(key, serde_json::to_string(&value).unwrap())?;
        }
        Ok(dict.into())
    })
}

/// Save configuration to TOML file
#[pyfunction]
fn save_toml(filepath: String, config: &PyDict) -> PyResult<()> {
    let mut values = HashMap::new();

    for (key, value) in config.iter() {
        let key_str: String = key.extract()?;
        let value_str: String = value.to_string();
        let json_value: serde_json::Value = serde_json::from_str(&value_str)
            .unwrap_or(serde_json::Value::String(value_str));
        values.insert(key_str, json_value);
    }

    let config = Config { values };
    let content = toml::to_string_pretty(&config).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to serialize: {}", e))
    })?;

    fs::write(&filepath, content).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to write {}: {}", filepath, e))
    })?;

    Ok(())
}

/// Load configuration from YAML file
#[pyfunction]
fn load_yaml(filepath: String) -> PyResult<PyObject> {
    let content = fs::read_to_string(&filepath).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to read {}: {}", filepath, e))
    })?;

    let config: Config = serde_yaml::from_str(&content).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid YAML: {}", e))
    })?;

    Python::with_gil(|py| {
        let dict = PyDict::new(py);
        for (key, value) in config.values {
            dict.set_item(key, serde_json::to_string(&value).unwrap())?;
        }
        Ok(dict.into())
    })
}

/// Save configuration to YAML file
#[pyfunction]
fn save_yaml(filepath: String, config: &PyDict) -> PyResult<()> {
    let mut values = HashMap::new();

    for (key, value) in config.iter() {
        let key_str: String = key.extract()?;
        let value_str: String = value.to_string();
        let json_value: serde_json::Value = serde_json::from_str(&value_str)
            .unwrap_or(serde_json::Value::String(value_str));
        values.insert(key_str, json_value);
    }

    let config = Config { values };
    let content = serde_yaml::to_string(&config).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to serialize: {}", e))
    })?;

    fs::write(&filepath, content).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to write {}: {}", filepath, e))
    })?;

    Ok(())
}

/// Merge multiple configuration files
#[pyfunction]
fn merge_configs(files: Vec<String>, output: String, format: String) -> PyResult<usize> {
    let mut merged = HashMap::new();

    for filepath in &files {
        let content = match fs::read_to_string(filepath) {
            Ok(c) => c,
            Err(_) => continue,
        };

        let config: Config = match format.as_str() {
            "toml" => toml::from_str(&content).ok(),
            "yaml" => serde_yaml::from_str(&content).ok(),
            _ => None,
        }
        .ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to parse {}", filepath))
        })?;

        for (key, value) in config.values {
            merged.insert(key, value);
        }
    }

    let config = Config { values: merged };
    let content = match format.as_str() {
        "toml" => toml::to_string_pretty(&config),
        "yaml" => serde_yaml::to_string(&config),
        _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Unknown format")),
    }
    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{}", e)))?;

    fs::write(&output, content).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to write {}: {}", output, e))
    })?;

    Ok(files.len())
}

#[pymodule]
fn config_management(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(load_toml, m)?)?;
    m.add_function(wrap_pyfunction!(save_toml, m)?)?;
    m.add_function(wrap_pyfunction!(load_yaml, m)?)?;
    m.add_function(wrap_pyfunction!(save_yaml, m)?)?;
    m.add_function(wrap_pyfunction!(merge_configs, m)?)?;
    Ok(())
}
