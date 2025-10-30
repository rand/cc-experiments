//! Example 06: Function Overloading Patterns
//!
//! PyO3 doesn't support true function overloading, but this example shows:
//! - Multiple functions with different names
//! - Using PyAny for flexible argument types
//! - Builder pattern for complex configurations
//! - Function variants with increasing complexity

use pyo3::prelude::*;
use pyo3::types::PyAny;

/// Simple addition of two integers.
#[pyfunction]
fn add_ints(a: i64, b: i64) -> i64 {
    a + b
}

/// Addition of two floats.
#[pyfunction]
fn add_floats(a: f64, b: f64) -> f64 {
    a + b
}

/// Generic addition using PyAny.
#[pyfunction]
fn add_any(a: &PyAny, b: &PyAny) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        // Try as integers
        if let (Ok(a_int), Ok(b_int)) = (a.extract::<i64>(), b.extract::<i64>()) {
            return Ok((a_int + b_int).into_py(py));
        }
        
        // Try as floats
        if let (Ok(a_float), Ok(b_float)) = (a.extract::<f64>(), b.extract::<f64>()) {
            return Ok((a_float + b_float).into_py(py));
        }
        
        // Try as strings (concatenation)
        if let (Ok(a_str), Ok(b_str)) = (a.extract::<String>(), b.extract::<String>()) {
            return Ok((a_str + &b_str).into_py(py));
        }
        
        Err(pyo3::exceptions::PyTypeError::new_err(
            "Arguments must be numbers or strings"
        ))
    })
}

/// Format data with basic options.
#[pyfunction]
#[pyo3(signature = (data, uppercase=false))]
fn format_basic(data: &str, uppercase: bool) -> String {
    if uppercase {
        data.to_uppercase()
    } else {
        data.to_string()
    }
}

/// Format data with more options.
#[pyfunction]
#[pyo3(signature = (data, uppercase=false, trim=true, prefix=None))]
fn format_advanced(
    data: &str,
    uppercase: bool,
    trim: bool,
    prefix: Option<String>,
) -> String {
    let mut result = data.to_string();
    
    if trim {
        result = result.trim().to_string();
    }
    
    if uppercase {
        result = result.to_uppercase();
    }
    
    if let Some(p) = prefix {
        result = format!("{}{}", p, result);
    }
    
    result
}

/// Format data with all options.
#[pyfunction]
#[pyo3(signature = (data, uppercase=false, trim=true, prefix=None, suffix=None, repeat=1))]
fn format_full(
    data: &str,
    uppercase: bool,
    trim: bool,
    prefix: Option<String>,
    suffix: Option<String>,
    repeat: usize,
) -> String {
    let mut result = data.to_string();
    
    if trim {
        result = result.trim().to_string();
    }
    
    if uppercase {
        result = result.to_uppercase();
    }
    
    if let Some(p) = prefix {
        result = format!("{}{}", p, result);
    }
    
    if let Some(s) = suffix {
        result = format!("{}{}", result, s);
    }
    
    result.repeat(repeat)
}

/// Configuration builder pattern class.
#[pyclass]
struct Config {
    host: String,
    port: u16,
    timeout: u64,
    retries: u32,
}

#[pymethods]
impl Config {
    #[new]
    #[pyo3(signature = (host="localhost".to_string(), port=8080, timeout=30, retries=3))]
    fn new(host: String, port: u16, timeout: u64, retries: u32) -> Self {
        Config { host, port, timeout, retries }
    }
    
    fn with_host(&mut self, host: String) -> PyResult<()> {
        self.host = host;
        Ok(())
    }
    
    fn with_port(&mut self, port: u16) -> PyResult<()> {
        self.port = port;
        Ok(())
    }
    
    fn with_timeout(&mut self, timeout: u64) -> PyResult<()> {
        self.timeout = timeout;
        Ok(())
    }
    
    fn __repr__(&self) -> String {
        format!(
            "Config(host='{}', port={}, timeout={}s, retries={})",
            self.host, self.port, self.timeout, self.retries
        )
    }
}

#[pymodule]
fn function_overloading(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(add_ints, m)?)?;
    m.add_function(wrap_pyfunction!(add_floats, m)?)?;
    m.add_function(wrap_pyfunction!(add_any, m)?)?;
    m.add_function(wrap_pyfunction!(format_basic, m)?)?;
    m.add_function(wrap_pyfunction!(format_advanced, m)?)?;
    m.add_function(wrap_pyfunction!(format_full, m)?)?;
    m.add_class::<Config>()?;
    Ok(())
}
