//! Custom type validation and conversion
//!
//! This example demonstrates:
//! - Newtype pattern for validation
//! - Custom FromPyObject implementations
//! - Input sanitization
//! - Range validation
//! - Format validation (email, URL, etc.)

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyString;

/// Email address with validation
#[pyclass]
#[derive(Clone)]
struct Email {
    #[pyo3(get)]
    address: String,
}

#[pymethods]
impl Email {
    #[new]
    fn new(address: String) -> PyResult<Self> {
        if !Self::is_valid_email(&address) {
            return Err(PyValueError::new_err(format!(
                "Invalid email address: {}",
                address
            )));
        }
        Ok(Email { address })
    }

    fn __repr__(&self) -> String {
        format!("Email('{}')", self.address)
    }

    fn __str__(&self) -> String {
        self.address.clone()
    }
}

impl Email {
    fn is_valid_email(email: &str) -> bool {
        email.contains('@') && email.len() >= 3 && !email.starts_with('@') && !email.ends_with('@')
    }
}

/// Positive integer (always > 0)
#[pyclass]
#[derive(Clone, Copy)]
struct PositiveInt {
    #[pyo3(get)]
    value: i64,
}

#[pymethods]
impl PositiveInt {
    #[new]
    fn new(value: i64) -> PyResult<Self> {
        if value <= 0 {
            return Err(PyValueError::new_err(format!(
                "Value must be positive, got {}",
                value
            )));
        }
        Ok(PositiveInt { value })
    }

    fn __repr__(&self) -> String {
        format!("PositiveInt({})", self.value)
    }

    fn __int__(&self) -> i64 {
        self.value
    }
}

/// Bounded integer (within a range)
#[pyclass]
#[derive(Clone)]
struct BoundedInt {
    #[pyo3(get)]
    value: i64,
    #[pyo3(get)]
    min: i64,
    #[pyo3(get)]
    max: i64,
}

#[pymethods]
impl BoundedInt {
    #[new]
    fn new(value: i64, min: i64, max: i64) -> PyResult<Self> {
        if min > max {
            return Err(PyValueError::new_err(format!(
                "min ({}) must be <= max ({})",
                min, max
            )));
        }
        if value < min || value > max {
            return Err(PyValueError::new_err(format!(
                "Value {} is outside range [{}, {}]",
                value, min, max
            )));
        }
        Ok(BoundedInt { value, min, max })
    }

    fn set_value(&mut self, new_value: i64) -> PyResult<()> {
        if new_value < self.min || new_value > self.max {
            return Err(PyValueError::new_err(format!(
                "Value {} is outside range [{}, {}]",
                new_value, self.min, self.max
            )));
        }
        self.value = new_value;
        Ok(())
    }

    fn __repr__(&self) -> String {
        format!(
            "BoundedInt(value={}, min={}, max={})",
            self.value, self.min, self.max
        )
    }
}

/// Percentage (0.0 to 100.0)
#[pyclass]
#[derive(Clone, Copy)]
struct Percentage {
    #[pyo3(get)]
    value: f64,
}

#[pymethods]
impl Percentage {
    #[new]
    fn new(value: f64) -> PyResult<Self> {
        if !(0.0..=100.0).contains(&value) {
            return Err(PyValueError::new_err(format!(
                "Percentage must be between 0 and 100, got {}",
                value
            )));
        }
        Ok(Percentage { value })
    }

    fn as_decimal(&self) -> f64 {
        self.value / 100.0
    }

    fn __repr__(&self) -> String {
        format!("Percentage({}%)", self.value)
    }
}

/// Non-empty string
#[pyclass]
#[derive(Clone)]
struct NonEmptyString {
    #[pyo3(get)]
    value: String,
}

#[pymethods]
impl NonEmptyString {
    #[new]
    fn new(value: String) -> PyResult<Self> {
        let trimmed = value.trim().to_string();
        if trimmed.is_empty() {
            return Err(PyValueError::new_err("String cannot be empty"));
        }
        Ok(NonEmptyString { value: trimmed })
    }

    fn __repr__(&self) -> String {
        format!("NonEmptyString('{}')", self.value)
    }

    fn __str__(&self) -> String {
        self.value.clone()
    }

    fn __len__(&self) -> usize {
        self.value.len()
    }
}

/// Phone number with basic validation
#[pyclass]
#[derive(Clone)]
struct PhoneNumber {
    #[pyo3(get)]
    number: String,
}

#[pymethods]
impl PhoneNumber {
    #[new]
    fn new(number: String) -> PyResult<Self> {
        let cleaned = number
            .chars()
            .filter(|c| c.is_ascii_digit() || *c == '+')
            .collect::<String>();

        if cleaned.len() < 10 {
            return Err(PyValueError::new_err(
                "Phone number must have at least 10 digits",
            ));
        }

        Ok(PhoneNumber { number: cleaned })
    }

    fn __repr__(&self) -> String {
        format!("PhoneNumber('{}')", self.number)
    }
}

/// Username with validation rules
#[pyclass]
#[derive(Clone)]
struct Username {
    #[pyo3(get)]
    name: String,
}

#[pymethods]
impl Username {
    #[new]
    fn new(name: String) -> PyResult<Self> {
        if name.len() < 3 {
            return Err(PyValueError::new_err("Username must be at least 3 characters"));
        }
        if name.len() > 20 {
            return Err(PyValueError::new_err("Username must be at most 20 characters"));
        }
        if !name.chars().all(|c| c.is_alphanumeric() || c == '_') {
            return Err(PyValueError::new_err(
                "Username can only contain letters, numbers, and underscores",
            ));
        }
        Ok(Username { name })
    }

    fn __repr__(&self) -> String {
        format!("Username('{}')", self.name)
    }
}

/// Function using validated types
#[pyfunction]
fn send_email(email: Email, message: NonEmptyString) -> PyResult<String> {
    Ok(format!(
        "Sent message '{}' to {}",
        message.value, email.address
    ))
}

/// Function using bounded types
#[pyfunction]
fn calculate_grade(score: Percentage) -> PyResult<String> {
    let grade = if score.value >= 90.0 {
        "A"
    } else if score.value >= 80.0 {
        "B"
    } else if score.value >= 70.0 {
        "C"
    } else if score.value >= 60.0 {
        "D"
    } else {
        "F"
    };
    Ok(format!("Score: {}% = Grade {}", score.value, grade))
}

/// Custom validator function
#[pyfunction]
fn validate_and_format_phone(number: String) -> PyResult<String> {
    let phone = PhoneNumber::new(number)?;
    Ok(phone.number)
}

/// Age validator
#[pyfunction]
fn create_age(value: i64) -> PyResult<BoundedInt> {
    BoundedInt::new(value, 0, 150)
}

/// URL validation (simple)
#[pyclass]
#[derive(Clone)]
struct Url {
    #[pyo3(get)]
    url: String,
}

#[pymethods]
impl Url {
    #[new]
    fn new(url: String) -> PyResult<Self> {
        if !url.starts_with("http://") && !url.starts_with("https://") {
            return Err(PyValueError::new_err("URL must start with http:// or https://"));
        }
        if url.len() < 10 {
            return Err(PyValueError::new_err("URL is too short"));
        }
        Ok(Url { url })
    }

    fn __repr__(&self) -> String {
        format!("Url('{}')", self.url)
    }
}

/// Hex color code
#[pyclass]
#[derive(Clone)]
struct HexColor {
    #[pyo3(get)]
    code: String,
}

#[pymethods]
impl HexColor {
    #[new]
    fn new(code: String) -> PyResult<Self> {
        if !code.starts_with('#') {
            return Err(PyValueError::new_err("Color code must start with #"));
        }
        let hex_part = &code[1..];
        if hex_part.len() != 6 && hex_part.len() != 3 {
            return Err(PyValueError::new_err("Color code must be #RGB or #RRGGBB"));
        }
        if !hex_part.chars().all(|c| c.is_ascii_hexdigit()) {
            return Err(PyValueError::new_err("Invalid hex characters"));
        }
        Ok(HexColor {
            code: code.to_uppercase(),
        })
    }

    fn __repr__(&self) -> String {
        format!("HexColor('{}')", self.code)
    }
}

#[pymodule]
fn type_validation(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Email>()?;
    m.add_class::<PositiveInt>()?;
    m.add_class::<BoundedInt>()?;
    m.add_class::<Percentage>()?;
    m.add_class::<NonEmptyString>()?;
    m.add_class::<PhoneNumber>()?;
    m.add_class::<Username>()?;
    m.add_class::<Url>()?;
    m.add_class::<HexColor>()?;
    m.add_function(wrap_pyfunction!(send_email, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_grade, m)?)?;
    m.add_function(wrap_pyfunction!(validate_and_format_phone, m)?)?;
    m.add_function(wrap_pyfunction!(create_age, m)?)?;
    Ok(())
}
