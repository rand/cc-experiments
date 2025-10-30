//! Example 09: Complete Error Hierarchy with Context
//!
//! This example demonstrates:
//! - Multi-level error hierarchies
//! - Error context and chaining
//! - Converting Rust errors to Python exceptions
//! - Best practices for error design

use pyo3::prelude::*;
use pyo3::exceptions::PyException;
use pyo3::create_exception;

// Base exceptions
create_exception!(error_hierarchy, AppError, PyException, "Base application error");

// Database errors
create_exception!(error_hierarchy, DatabaseError, AppError, "Base database error");
create_exception!(error_hierarchy, ConnectionError, DatabaseError, "Database connection failed");
create_exception!(error_hierarchy, QueryError, DatabaseError, "Query execution failed");
create_exception!(error_hierarchy, TransactionError, DatabaseError, "Transaction failed");

// Network errors
create_exception!(error_hierarchy, NetworkError, AppError, "Base network error");
create_exception!(error_hierarchy, TimeoutError, NetworkError, "Operation timed out");
create_exception!(error_hierarchy, HttpError, NetworkError, "HTTP request failed");

// Validation errors
create_exception!(error_hierarchy, ValidationError, AppError, "Base validation error");
create_exception!(error_hierarchy, SchemaError, ValidationError, "Schema validation failed");
create_exception!(error_hierarchy, ConstraintError, ValidationError, "Constraint violation");

/// Error with context chain.
#[pyclass(extends=PyException)]
struct ContextError {
    #[pyo3(get)]
    message: String,
    #[pyo3(get)]
    context: Vec<String>,
    #[pyo3(get)]
    error_code: String,
}

#[pymethods]
impl ContextError {
    #[new]
    fn new(message: String, context: Vec<String>, error_code: String) -> (Self, PyException) {
        (
            ContextError { message: message.clone(), context, error_code },
            PyException::new_err(message),
        )
    }
    
    fn __str__(&self) -> String {
        let ctx = if self.context.is_empty() {
            String::new()
        } else {
            format!("\nContext:\n  {}", self.context.join("\n  "))
        };
        format!("[{}] {}{}", self.error_code, self.message, ctx)
    }
    
    fn add_context(&mut self, context: String) {
        self.context.push(context);
    }
}

/// Simulates database connection with errors.
#[pyfunction]
fn connect_database(host: &str, port: u16) -> PyResult<String> {
    if host.is_empty() {
        return Err(ConnectionError::new_err("Host cannot be empty"));
    }
    
    if port == 0 {
        return Err(ConnectionError::new_err(format!(
            "Invalid port: {}. Must be non-zero", port
        )));
    }
    
    if port == 9999 {
        return Err(ConnectionError::new_err(format!(
            "Connection refused: {}:{}", host, port
        )));
    }
    
    Ok(format!("Connected to {}:{}", host, port))
}

/// Simulates query execution.
#[pyfunction]
fn execute_query(query: &str) -> PyResult<Vec<String>> {
    if query.trim().is_empty() {
        return Err(QueryError::new_err("Query cannot be empty"));
    }
    
    if query.contains("DROP") {
        return Err(QueryError::new_err("Dangerous query detected"));
    }
    
    if query.len() > 1000 {
        return Err(QueryError::new_err("Query too long"));
    }
    
    Ok(vec!["result1".to_string(), "result2".to_string()])
}

/// Simulates HTTP request.
#[pyfunction]
fn http_request(url: &str, timeout: u64) -> PyResult<String> {
    if !url.starts_with("http://") && !url.starts_with("https://") {
        return Err(HttpError::new_err("Invalid URL scheme"));
    }
    
    if timeout == 0 {
        return Err(TimeoutError::new_err("Timeout must be positive"));
    }
    
    if url.contains("slow") {
        return Err(TimeoutError::new_err(format!(
            "Request to {} timed out after {}s", url, timeout
        )));
    }
    
    Ok(format!("Response from {}", url))
}

/// Validates data with schema.
#[pyfunction]
fn validate_schema(data: Vec<(String, String)>) -> PyResult<()> {
    if data.is_empty() {
        return Err(SchemaError::new_err("Data cannot be empty"));
    }
    
    for (key, value) in &data {
        if key.is_empty() {
            return Err(SchemaError::new_err("Keys cannot be empty"));
        }
        
        if value.is_empty() {
            return Err(ConstraintError::new_err(format!(
                "Value for key '{}' cannot be empty", key
            )));
        }
    }
    
    Ok(())
}

/// Complex operation with error context.
#[pyfunction]
fn complex_operation(input: i64) -> PyResult<i64> {
    if input < 0 {
        let context = vec![
            format!("Input value: {}", input),
            "Must be non-negative".to_string(),
            "Called from complex_operation".to_string(),
        ];
        
        return Err(PyErr::from_type(
            Python::with_gil(|py| ContextError::type_object(py)),
            ("Validation failed".to_string(), context, "ERR_NEGATIVE".to_string()),
        ));
    }
    
    if input > 1000 {
        let context = vec![
            format!("Input value: {}", input),
            "Must be <= 1000".to_string(),
        ];
        
        return Err(PyErr::from_type(
            Python::with_gil(|py| ContextError::type_object(py)),
            ("Range error".to_string(), context, "ERR_RANGE".to_string()),
        ));
    }
    
    Ok(input * 2)
}

#[pymodule]
fn error_hierarchy(py: Python, m: &PyModule) -> PyResult<()> {
    // Register exception hierarchy
    m.add("AppError", py.get_type::<AppError>())?;
    
    m.add("DatabaseError", py.get_type::<DatabaseError>())?;
    m.add("ConnectionError", py.get_type::<ConnectionError>())?;
    m.add("QueryError", py.get_type::<QueryError>())?;
    m.add("TransactionError", py.get_type::<TransactionError>())?;
    
    m.add("NetworkError", py.get_type::<NetworkError>())?;
    m.add("TimeoutError", py.get_type::<TimeoutError>())?;
    m.add("HttpError", py.get_type::<HttpError>())?;
    
    m.add("ValidationError", py.get_type::<ValidationError>())?;
    m.add("SchemaError", py.get_type::<SchemaError>())?;
    m.add("ConstraintError", py.get_type::<ConstraintError>())?;
    
    m.add_class::<ContextError>()?;
    
    // Register functions
    m.add_function(wrap_pyfunction!(connect_database, m)?)?;
    m.add_function(wrap_pyfunction!(execute_query, m)?)?;
    m.add_function(wrap_pyfunction!(http_request, m)?)?;
    m.add_function(wrap_pyfunction!(validate_schema, m)?)?;
    m.add_function(wrap_pyfunction!(complex_operation, m)?)?;
    
    Ok(())
}
