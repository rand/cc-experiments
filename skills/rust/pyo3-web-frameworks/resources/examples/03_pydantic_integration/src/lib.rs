//! Pydantic model validation in Rust
//!
//! This example demonstrates:
//! - Extracting data from Pydantic models
//! - Validating model fields in Rust
//! - Creating validation results
//! - Complex validation logic
//! - Error reporting with Pydantic

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};
use pyo3::exceptions::PyValueError;

/// Validation result returned to Python
#[pyclass]
#[derive(Clone)]
pub struct ValidationResult {
    #[pyo3(get, set)]
    pub valid: bool,
    #[pyo3(get, set)]
    pub errors: Vec<String>,
    #[pyo3(get, set)]
    pub warnings: Vec<String>,
}

#[pymethods]
impl ValidationResult {
    #[new]
    fn new(valid: bool, errors: Vec<String>, warnings: Vec<String>) -> Self {
        ValidationResult { valid, errors, warnings }
    }

    fn __repr__(&self) -> String {
        format!(
            "ValidationResult(valid={}, errors={}, warnings={})",
            self.valid,
            self.errors.len(),
            self.warnings.len()
        )
    }

    fn has_errors(&self) -> bool {
        !self.errors.is_empty()
    }

    fn has_warnings(&self) -> bool {
        !self.warnings.is_empty()
    }
}

/// Validate email field from Pydantic model
#[pyfunction]
fn validate_email(email: String) -> PyResult<ValidationResult> {
    let mut errors = Vec::new();
    let mut warnings = Vec::new();

    let trimmed = email.trim();

    if trimmed.is_empty() {
        errors.push("Email cannot be empty".to_string());
    } else if !trimmed.contains('@') {
        errors.push("Email must contain @".to_string());
    } else if !trimmed.contains('.') {
        errors.push("Email must contain domain extension".to_string());
    }

    let parts: Vec<&str> = trimmed.split('@').collect();
    if parts.len() == 2 {
        if parts[0].len() < 2 {
            errors.push("Email local part too short".to_string());
        }
        if parts[1].len() < 3 {
            errors.push("Email domain too short".to_string());
        }
    }

    if trimmed.len() > 254 {
        errors.push("Email exceeds maximum length (254)".to_string());
    }

    if trimmed != trimmed.to_lowercase() {
        warnings.push("Email should be lowercase".to_string());
    }

    Ok(ValidationResult::new(errors.is_empty(), errors, warnings))
}

/// Validate user model
#[pyfunction]
fn validate_user_model(py: Python, model: &PyAny) -> PyResult<ValidationResult> {
    let mut errors = Vec::new();
    let mut warnings = Vec::new();

    // Convert model to dict
    let dict = model.call_method0("dict")?;

    // Validate username
    if let Ok(username) = dict.get_item("username") {
        let username_str: String = username.extract()?;
        if username_str.len() < 3 {
            errors.push("Username must be at least 3 characters".to_string());
        }
        if username_str.len() > 20 {
            errors.push("Username must be at most 20 characters".to_string());
        }
        if !username_str.chars().all(|c| c.is_alphanumeric() || c == '_') {
            errors.push("Username can only contain alphanumeric characters and underscore".to_string());
        }
    } else {
        errors.push("Username is required".to_string());
    }

    // Validate email
    if let Ok(email) = dict.get_item("email") {
        let email_str: String = email.extract()?;
        let email_result = validate_email(email_str)?;
        errors.extend(email_result.errors);
        warnings.extend(email_result.warnings);
    } else {
        errors.push("Email is required".to_string());
    }

    // Validate age
    if let Ok(age) = dict.get_item("age") {
        let age_val: i32 = age.extract()?;
        if age_val < 0 {
            errors.push("Age cannot be negative".to_string());
        }
        if age_val > 150 {
            errors.push("Age seems unrealistic".to_string());
        }
        if age_val < 18 {
            warnings.push("User is under 18".to_string());
        }
    }

    Ok(ValidationResult::new(errors.is_empty(), errors, warnings))
}

/// Validate password strength
#[pyfunction]
fn validate_password(password: String) -> PyResult<ValidationResult> {
    let mut errors = Vec::new();
    let mut warnings = Vec::new();

    if password.len() < 8 {
        errors.push("Password must be at least 8 characters".to_string());
    }

    if password.len() > 128 {
        errors.push("Password exceeds maximum length (128)".to_string());
    }

    let has_uppercase = password.chars().any(|c| c.is_uppercase());
    let has_lowercase = password.chars().any(|c| c.is_lowercase());
    let has_digit = password.chars().any(|c| c.is_numeric());
    let has_special = password.chars().any(|c| !c.is_alphanumeric());

    if !has_uppercase {
        errors.push("Password must contain at least one uppercase letter".to_string());
    }
    if !has_lowercase {
        errors.push("Password must contain at least one lowercase letter".to_string());
    }
    if !has_digit {
        errors.push("Password must contain at least one digit".to_string());
    }
    if !has_special {
        warnings.push("Password should contain at least one special character".to_string());
    }

    if password.len() < 12 {
        warnings.push("Consider using a longer password (12+ characters)".to_string());
    }

    Ok(ValidationResult::new(errors.is_empty(), errors, warnings))
}

/// Validate API request payload
#[pyfunction]
fn validate_request(py: Python, model: &PyAny) -> PyResult<ValidationResult> {
    let mut errors = Vec::new();
    let mut warnings = Vec::new();

    let dict = model.call_method0("dict")?;

    // Validate required fields
    let required_fields = vec!["action", "resource", "user_id"];
    for field in required_fields {
        if dict.get_item(field).is_err() {
            errors.push(format!("Missing required field: {}", field));
        }
    }

    // Validate action
    if let Ok(action) = dict.get_item("action") {
        let action_str: String = action.extract()?;
        let valid_actions = vec!["create", "read", "update", "delete"];
        if !valid_actions.contains(&action_str.as_str()) {
            errors.push(format!("Invalid action: {}. Must be one of: create, read, update, delete", action_str));
        }
    }

    // Validate resource
    if let Ok(resource) = dict.get_item("resource") {
        let resource_str: String = resource.extract()?;
        if resource_str.is_empty() {
            errors.push("Resource cannot be empty".to_string());
        }
    }

    // Validate user_id
    if let Ok(user_id) = dict.get_item("user_id") {
        let id: i64 = user_id.extract()?;
        if id <= 0 {
            errors.push("User ID must be positive".to_string());
        }
    }

    Ok(ValidationResult::new(errors.is_empty(), errors, warnings))
}

/// Sanitize user input
#[pyfunction]
fn sanitize_input(input: String) -> PyResult<String> {
    // Remove dangerous characters
    let sanitized: String = input
        .chars()
        .filter(|c| c.is_alphanumeric() || c.is_whitespace() || "-_.".contains(*c))
        .collect();

    Ok(sanitized.trim().to_string())
}

/// Normalize phone number
#[pyfunction]
fn normalize_phone(phone: String) -> PyResult<String> {
    // Extract only digits
    let digits: String = phone.chars().filter(|c| c.is_numeric()).collect();

    if digits.len() < 10 {
        return Err(PyValueError::new_err("Phone number too short"));
    }

    if digits.len() > 15 {
        return Err(PyValueError::new_err("Phone number too long"));
    }

    // Format as +X-XXX-XXX-XXXX
    if digits.len() == 10 {
        Ok(format!("+1-{}-{}-{}",
            &digits[0..3],
            &digits[3..6],
            &digits[6..10]
        ))
    } else {
        Ok(format!("+{}", digits))
    }
}

/// Python module initialization
#[pymodule]
fn pydantic_integration(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ValidationResult>()?;
    m.add_function(wrap_pyfunction!(validate_email, m)?)?;
    m.add_function(wrap_pyfunction!(validate_user_model, m)?)?;
    m.add_function(wrap_pyfunction!(validate_password, m)?)?;
    m.add_function(wrap_pyfunction!(validate_request, m)?)?;
    m.add_function(wrap_pyfunction!(sanitize_input, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_phone, m)?)?;
    Ok(())
}
