//! Example 10: Production-Ready API
//!
//! This example demonstrates a complete, production-ready PyO3 module combining:
//! - Module organization with submodules
//! - Comprehensive error handling
//! - Function overloading patterns
//! - Constants and configuration
//! - Full documentation
//! - Type safety

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use pyo3::types::{PyDict, PyList};
use pyo3::create_exception;
use std::collections::HashMap;

// Version and constants
const VERSION: &str = env!("CARGO_PKG_VERSION");
const MAX_BATCH_SIZE: usize = 1000;

// Custom exceptions
create_exception!(production_api, ApiError, pyo3::exceptions::PyException, "Base API error");
create_exception!(production_api, ConfigurationError, ApiError, "Configuration error");
create_exception!(production_api, ProcessingError, ApiError, "Processing error");

// Configuration class
#[pyclass]
#[derive(Clone)]
struct Config {
    #[pyo3(get, set)]
    debug: bool,
    #[pyo3(get, set)]
    max_retries: u32,
    #[pyo3(get, set)]
    timeout: u64,
    settings: HashMap<String, String>,
}

#[pymethods]
impl Config {
    #[new]
    #[pyo3(signature = (debug=false, max_retries=3, timeout=30))]
    fn new(debug: bool, max_retries: u32, timeout: u64) -> Self {
        Config {
            debug,
            max_retries,
            timeout,
            settings: HashMap::new(),
        }
    }
    
    fn set_setting(&mut self, key: String, value: String) {
        self.settings.insert(key, value);
    }
    
    fn get_setting(&self, key: &str) -> Option<String> {
        self.settings.get(key).cloned()
    }
    
    fn validate(&self) -> PyResult<()> {
        if self.max_retries > 10 {
            return Err(ConfigurationError::new_err(
                "max_retries cannot exceed 10"
            ));
        }
        if self.timeout == 0 {
            return Err(ConfigurationError::new_err(
                "timeout must be positive"
            ));
        }
        Ok(())
    }
    
    fn __repr__(&self) -> String {
        format!(
            "Config(debug={}, max_retries={}, timeout={}s)",
            self.debug, self.max_retries, self.timeout
        )
    }
}

// Data processing result
#[pyclass]
struct ProcessResult {
    #[pyo3(get)]
    success_count: usize,
    #[pyo3(get)]
    error_count: usize,
    #[pyo3(get)]
    total: usize,
    errors: Vec<String>,
}

#[pymethods]
impl ProcessResult {
    fn get_errors(&self) -> Vec<String> {
        self.errors.clone()
    }
    
    fn success_rate(&self) -> f64 {
        if self.total == 0 {
            0.0
        } else {
            self.success_count as f64 / self.total as f64
        }
    }
    
    fn __repr__(&self) -> String {
        format!(
            "ProcessResult(success={}/{}, errors={})",
            self.success_count, self.total, self.error_count
        )
    }
}

// Core processing module
pub mod processing {
    use super::*;
    
    /// Processes a batch of items with validation.
    #[pyfunction]
    pub fn process_batch(items: Vec<String>, config: &Config) -> PyResult<ProcessResult> {
        if items.len() > MAX_BATCH_SIZE {
            return Err(ProcessingError::new_err(format!(
                "Batch size {} exceeds maximum {}", items.len(), MAX_BATCH_SIZE
            )));
        }
        
        let mut success_count = 0;
        let mut errors = Vec::new();
        
        for (idx, item) in items.iter().enumerate() {
            if validate_item(item).is_ok() {
                success_count += 1;
            } else {
                errors.push(format!("Item {} failed validation", idx));
            }
        }
        
        Ok(ProcessResult {
            success_count,
            error_count: errors.len(),
            total: items.len(),
            errors,
        })
    }
    
    fn validate_item(item: &str) -> PyResult<()> {
        if item.is_empty() {
            return Err(PyValueError::new_err("Item cannot be empty"));
        }
        if item.len() > 100 {
            return Err(PyValueError::new_err("Item too long"));
        }
        Ok(())
    }
    
    /// Transforms items using various operations.
    #[pyfunction]
    #[pyo3(signature = (items, operation="uppercase"))]
    pub fn transform(items: Vec<String>, operation: &str) -> PyResult<Vec<String>> {
        match operation {
            "uppercase" => Ok(items.iter().map(|s| s.to_uppercase()).collect()),
            "lowercase" => Ok(items.iter().map(|s| s.to_lowercase()).collect()),
            "reverse" => Ok(items.iter().map(|s| s.chars().rev().collect()).collect()),
            "trim" => Ok(items.iter().map(|s| s.trim().to_string()).collect()),
            _ => Err(PyValueError::new_err(format!(
                "Unknown operation: {}", operation
            ))),
        }
    }
    
    /// Filters items by length.
    #[pyfunction]
    pub fn filter_by_length(items: Vec<String>, min_len: usize, max_len: usize) -> PyResult<Vec<String>> {
        if min_len > max_len {
            return Err(PyValueError::new_err("min_len cannot exceed max_len"));
        }
        
        Ok(items.into_iter()
            .filter(|s| s.len() >= min_len && s.len() <= max_len)
            .collect())
    }
}

// Statistics module
pub mod stats {
    use super::*;
    
    /// Computes statistics for a list of numbers.
    #[pyfunction]
    pub fn compute_stats(numbers: Vec<f64>) -> PyResult<PyObject> {
        if numbers.is_empty() {
            return Err(PyValueError::new_err("Cannot compute stats of empty list"));
        }
        
        let sum: f64 = numbers.iter().sum();
        let mean = sum / numbers.len() as f64;
        
        let mut sorted = numbers.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        
        let median = if sorted.len() % 2 == 0 {
            (sorted[sorted.len() / 2 - 1] + sorted[sorted.len() / 2]) / 2.0
        } else {
            sorted[sorted.len() / 2]
        };
        
        let min = sorted[0];
        let max = sorted[sorted.len() - 1];
        
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("mean", mean)?;
            dict.set_item("median", median)?;
            dict.set_item("min", min)?;
            dict.set_item("max", max)?;
            dict.set_item("count", numbers.len())?;
            Ok(dict.into())
        })
    }
}

// Utility functions at root level
#[pyfunction]
fn get_version() -> &'static str {
    VERSION
}

#[pyfunction]
fn get_max_batch_size() -> usize {
    MAX_BATCH_SIZE
}

#[pyfunction]
fn create_default_config() -> Config {
    Config::new(false, 3, 30)
}

#[pymodule]
fn production_api(py: Python, m: &PyModule) -> PyResult<()> {
    // Add version and constants
    m.add("__version__", VERSION)?;
    m.add("VERSION", VERSION)?;
    m.add("MAX_BATCH_SIZE", MAX_BATCH_SIZE)?;
    
    // Register exceptions
    m.add("ApiError", py.get_type::<ApiError>())?;
    m.add("ConfigurationError", py.get_type::<ConfigurationError>())?;
    m.add("ProcessingError", py.get_type::<ProcessingError>())?;
    
    // Register classes
    m.add_class::<Config>()?;
    m.add_class::<ProcessResult>()?;
    
    // Register root functions
    m.add_function(wrap_pyfunction!(get_version, m)?)?;
    m.add_function(wrap_pyfunction!(get_max_batch_size, m)?)?;
    m.add_function(wrap_pyfunction!(create_default_config, m)?)?;
    
    // Create and register submodules
    let processing_mod = PyModule::new(py, "processing")?;
    processing_mod.add_function(wrap_pyfunction!(processing::process_batch, processing_mod)?)?;
    processing_mod.add_function(wrap_pyfunction!(processing::transform, processing_mod)?)?;
    processing_mod.add_function(wrap_pyfunction!(processing::filter_by_length, processing_mod)?)?;
    m.add_submodule(processing_mod)?;
    
    let stats_mod = PyModule::new(py, "stats")?;
    stats_mod.add_function(wrap_pyfunction!(stats::compute_stats, stats_mod)?)?;
    m.add_submodule(stats_mod)?;
    
    Ok(())
}
