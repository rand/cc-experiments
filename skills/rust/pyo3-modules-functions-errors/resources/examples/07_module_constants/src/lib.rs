//! Example 07: Module Constants and Enums

use pyo3::prelude::*;

// Constants
const VERSION: &str = "1.0.0";
const MAX_CONNECTIONS: usize = 100;
const DEFAULT_TIMEOUT: f64 = 30.0;

/// Simple enum exported as Python class.
#[pyclass]
#[derive(Clone)]
enum Status {
    Pending,
    Running,
    Success,
    Failed,
}

#[pymethods]
impl Status {
    fn __str__(&self) -> &str {
        match self {
            Status::Pending => "Pending",
            Status::Running => "Running",
            Status::Success => "Success",
            Status::Failed => "Failed",
        }
    }
}

/// Enum with associated values.
#[pyclass]
#[derive(Clone)]
enum LogLevel {
    Debug,
    Info,
    Warning,
    Error,
}

#[pymethods]
impl LogLevel {
    fn to_int(&self) -> u8 {
        match self {
            LogLevel::Debug => 10,
            LogLevel::Info => 20,
            LogLevel::Warning => 30,
            LogLevel::Error => 40,
        }
    }
    
    #[staticmethod]
    fn from_string(s: &str) -> PyResult<LogLevel> {
        match s.to_lowercase().as_str() {
            "debug" => Ok(LogLevel::Debug),
            "info" => Ok(LogLevel::Info),
            "warning" | "warn" => Ok(LogLevel::Warning),
            "error" => Ok(LogLevel::Error),
            _ => Err(pyo3::exceptions::PyValueError::new_err(
                format!("Invalid log level: {}", s)
            )),
        }
    }
}

#[pyfunction]
fn get_version() -> &'static str {
    VERSION
}

#[pyfunction]
fn get_max_connections() -> usize {
    MAX_CONNECTIONS
}

#[pymodule]
fn module_constants(_py: Python, m: &PyModule) -> PyResult<()> {
    // Add constants
    m.add("VERSION", VERSION)?;
    m.add("MAX_CONNECTIONS", MAX_CONNECTIONS)?;
    m.add("DEFAULT_TIMEOUT", DEFAULT_TIMEOUT)?;
    m.add("PI", std::f64::consts::PI)?;
    m.add("E", std::f64::consts::E)?;
    
    // Add enums
    m.add_class::<Status>()?;
    m.add_class::<LogLevel>()?;
    
    // Add functions
    m.add_function(wrap_pyfunction!(get_version, m)?)?;
    m.add_function(wrap_pyfunction!(get_max_connections, m)?)?;
    
    Ok(())
}
