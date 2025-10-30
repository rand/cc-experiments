//! Custom error types for DSPy operations
//!
//! This module demonstrates production-grade error handling patterns
//! for Python/Rust interop with DSPy, including error conversion,
//! context preservation, and structured error types.

use pyo3::exceptions::{PyException, PyRuntimeError, PyTypeError, PyValueError};
use pyo3::types::PyTypeMethods;
use pyo3::{PyErr, Python};
use std::fmt;
use thiserror::Error;

/// Main error type for DSPy operations
///
/// This enum covers all possible error scenarios when working with DSPy
/// from Rust, providing structured error information and context.
#[derive(Error, Debug)]
pub enum DSpyError {
    #[error("Python initialization failed: {0}")]
    PythonInit(String),

    #[error("Failed to import DSPy module: {0}")]
    ImportError(String),

    #[error("Configuration error: {0}")]
    Config(#[from] ConfigError),

    #[error("Prediction failed: {0}")]
    Prediction(#[from] PredictionError),

    #[error("Model error: {0}")]
    Model(String),

    #[error("Timeout after {timeout_ms}ms: {operation}")]
    Timeout {
        operation: String,
        timeout_ms: u64,
    },

    #[error("Retry limit exceeded after {attempts} attempts: {last_error}")]
    RetryExhausted {
        attempts: u32,
        last_error: String,
    },

    #[error("Python exception: {0}")]
    Python(String),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

/// Configuration-related errors
#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("Missing required configuration: {field}")]
    MissingField { field: String },

    #[error("Invalid configuration value for {field}: {value}")]
    InvalidValue { field: String, value: String },

    #[error("API key not found in environment: {var_name}")]
    MissingApiKey { var_name: String },

    #[error("Invalid model name: {model}")]
    InvalidModel { model: String },
}

/// Prediction-related errors
#[derive(Error, Debug)]
pub enum PredictionError {
    #[error("Empty input provided")]
    EmptyInput,

    #[error("Invalid input format: {details}")]
    InvalidFormat { details: String },

    #[error("Model returned empty response")]
    EmptyResponse,

    #[error("Failed to parse response: {details}")]
    ParseError { details: String },

    #[error("Rate limit exceeded, retry after {retry_after_ms}ms")]
    RateLimit { retry_after_ms: u64 },

    #[error("Model quota exceeded")]
    QuotaExceeded,
}

/// Convert PyErr to DSpyError with context preservation
impl From<PyErr> for DSpyError {
    fn from(err: PyErr) -> Self {
        Python::with_gil(|py| {
            // Extract exception type and value
            let exception_type = err.get_type_bound(py)
                .qualname()
                .map(|s| s.to_string())
                .unwrap_or_else(|_| "Unknown".to_string());
            let exception_value = err.value_bound(py).to_string();

            // Map specific Python exceptions to structured errors
            if exception_type.contains("ImportError") || exception_type.contains("ModuleNotFoundError") {
                DSpyError::ImportError(format!("{}: {}", exception_type, exception_value))
            } else if exception_type.contains("ValueError") {
                DSpyError::Prediction(PredictionError::InvalidFormat {
                    details: exception_value,
                })
            } else if exception_type.contains("RuntimeError") {
                DSpyError::Model(exception_value)
            } else {
                DSpyError::Python(format!("{}: {}", exception_type, exception_value))
            }
        })
    }
}

/// Convert DSpyError back to PyErr for Python interop
impl From<DSpyError> for PyErr {
    fn from(err: DSpyError) -> Self {
        match err {
            DSpyError::ImportError(msg) => PyErr::new::<PyException, _>(msg),
            DSpyError::Config(ConfigError::MissingField { field }) => {
                PyValueError::new_err(format!("Missing field: {}", field))
            }
            DSpyError::Config(ConfigError::InvalidValue { field, value }) => {
                PyValueError::new_err(format!("Invalid value for {}: {}", field, value))
            }
            DSpyError::Prediction(PredictionError::EmptyInput) => {
                PyValueError::new_err("Empty input")
            }
            DSpyError::Prediction(PredictionError::InvalidFormat { details }) => {
                PyTypeError::new_err(details)
            }
            DSpyError::Timeout { operation, timeout_ms } => {
                PyRuntimeError::new_err(format!("Timeout after {}ms: {}", timeout_ms, operation))
            }
            _ => PyRuntimeError::new_err(err.to_string()),
        }
    }
}

/// Result type alias for DSPy operations
pub type DSpyResult<T> = Result<T, DSpyError>;

/// Error context for tracking operation details
#[derive(Debug, Clone)]
pub struct ErrorContext {
    pub operation: String,
    pub attempt: u32,
    pub timestamp: std::time::SystemTime,
}

impl ErrorContext {
    pub fn new(operation: impl Into<String>) -> Self {
        Self {
            operation: operation.into(),
            attempt: 1,
            timestamp: std::time::SystemTime::now(),
        }
    }

    pub fn with_attempt(mut self, attempt: u32) -> Self {
        self.attempt = attempt;
        self
    }
}

impl fmt::Display for ErrorContext {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "operation='{}' attempt={} timestamp={:?}",
            self.operation, self.attempt, self.timestamp
        )
    }
}
