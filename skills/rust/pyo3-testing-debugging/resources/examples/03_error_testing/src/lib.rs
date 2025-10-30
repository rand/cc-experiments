use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyTypeError};
use pyo3::create_exception;

// Custom exception types
create_exception!(error_testing, ValidationError, pyo3::exceptions::PyException);
create_exception!(error_testing, RangeError, pyo3::exceptions::PyException);

/// Divide two numbers
#[pyfunction]
fn divide(a: f64, b: f64) -> PyResult<f64> {
    if b == 0.0 {
        Err(PyValueError::new_err("Division by zero"))
    } else if a.is_nan() || b.is_nan() {
        Err(PyValueError::new_err("Cannot divide NaN values"))
    } else if a.is_infinite() || b.is_infinite() {
        Err(PyValueError::new_err("Cannot divide infinite values"))
    } else {
        Ok(a / b)
    }
}

/// Validate age
#[pyfunction]
fn validate_age(age: i32) -> PyResult<()> {
    if age < 0 {
        Err(ValidationError::new_err("Age cannot be negative"))
    } else if age > 150 {
        Err(ValidationError::new_err("Age exceeds maximum reasonable value"))
    } else {
        Ok(())
    }
}

/// Validate email format
#[pyfunction]
fn validate_email(email: String) -> PyResult<()> {
    if email.is_empty() {
        return Err(ValidationError::new_err("Email cannot be empty"));
    }
    if !email.contains('@') {
        return Err(ValidationError::new_err("Email must contain @ symbol"));
    }
    if !email.contains('.') {
        return Err(ValidationError::new_err("Email must contain a domain"));
    }
    Ok(())
}

/// Validate value is in range
#[pyfunction]
fn validate_range(value: f64, min: f64, max: f64) -> PyResult<()> {
    if min > max {
        return Err(PyValueError::new_err("Min cannot be greater than max"));
    }
    if value < min {
        return Err(RangeError::new_err(format!("Value {} is below minimum {}", value, min)));
    }
    if value > max {
        return Err(RangeError::new_err(format!("Value {} exceeds maximum {}", value, max)));
    }
    Ok(())
}

/// Parse and validate positive integer
#[pyfunction]
fn parse_positive_int(s: String) -> PyResult<u32> {
    let num: i32 = s.parse()
        .map_err(|_| PyValueError::new_err(format!("Invalid integer: '{}'", s)))?;

    if num < 0 {
        return Err(PyValueError::new_err("Number must be positive"));
    }

    Ok(num as u32)
}

/// Process data with validation
#[pyfunction]
fn process_validated_data(data: Vec<f64>, min_val: f64, max_val: f64) -> PyResult<Vec<f64>> {
    // Validate input
    if data.is_empty() {
        return Err(PyValueError::new_err("Data cannot be empty"));
    }

    // Validate range
    if min_val > max_val {
        return Err(PyValueError::new_err("min_val cannot exceed max_val"));
    }

    // Validate all values in range
    for (i, &val) in data.iter().enumerate() {
        if val < min_val || val > max_val {
            return Err(RangeError::new_err(
                format!("Value at index {} ({}) is outside range [{}, {}]", i, val, min_val, max_val)
            ));
        }
    }

    // Process data (square each value)
    Ok(data.iter().map(|&x| x * x).collect())
}

/// Chained operations with error propagation
#[pyfunction]
fn process_user_age(age_str: String) -> PyResult<String> {
    // Parse the age
    let age = parse_positive_int(age_str)?;

    // Validate the age
    validate_age(age as i32)?;

    // Return category
    let category = if age < 18 {
        "minor"
    } else if age < 65 {
        "adult"
    } else {
        "senior"
    };

    Ok(category.to_string())
}

#[pymodule]
fn error_testing(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(divide, m)?)?;
    m.add_function(wrap_pyfunction!(validate_age, m)?)?;
    m.add_function(wrap_pyfunction!(validate_email, m)?)?;
    m.add_function(wrap_pyfunction!(validate_range, m)?)?;
    m.add_function(wrap_pyfunction!(parse_positive_int, m)?)?;
    m.add_function(wrap_pyfunction!(process_validated_data, m)?)?;
    m.add_function(wrap_pyfunction!(process_user_age, m)?)?;

    // Add custom exceptions
    m.add("ValidationError", m.py().get_type_bound::<ValidationError>())?;
    m.add("RangeError", m.py().get_type_bound::<RangeError>())?;

    Ok(())
}

// ============================================================================
// RUST TESTS
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_divide_normal() {
        assert_eq!(divide(10.0, 2.0).unwrap(), 5.0);
    }

    #[test]
    fn test_divide_by_zero() {
        assert!(divide(10.0, 0.0).is_err());
    }

    #[test]
    fn test_validate_age_valid() {
        assert!(validate_age(25).is_ok());
    }

    #[test]
    fn test_validate_age_negative() {
        assert!(validate_age(-1).is_err());
    }

    #[test]
    fn test_parse_positive_valid() {
        assert_eq!(parse_positive_int("42".to_string()).unwrap(), 42);
    }

    #[test]
    fn test_parse_positive_invalid() {
        assert!(parse_positive_int("abc".to_string()).is_err());
    }
}
