//! Properties, getters, and setters with custom logic
//!
//! Demonstrates:
//! - Custom getters with #[getter]
//! - Custom setters with #[setter]
//! - Computed properties
//! - Validated setters
//! - Read-only properties

use pyo3::prelude::*;

/// Temperature class with Celsius/Fahrenheit conversion
#[pyclass]
struct Temperature {
    celsius: f64,
}

#[pymethods]
impl Temperature {
    #[new]
    fn new(celsius: f64) -> Self {
        Temperature { celsius }
    }

    #[getter]
    fn celsius(&self) -> f64 {
        self.celsius
    }

    #[setter]
    fn set_celsius(&mut self, value: f64) {
        self.celsius = value;
    }

    #[getter]
    fn fahrenheit(&self) -> f64 {
        self.celsius * 9.0 / 5.0 + 32.0
    }

    #[setter]
    fn set_fahrenheit(&mut self, value: f64) {
        self.celsius = (value - 32.0) * 5.0 / 9.0;
    }

    #[getter]
    fn kelvin(&self) -> f64 {
        self.celsius + 273.15
    }
}

/// BankAccount with balance validation
#[pyclass]
struct ValidatedAccount {
    balance: f64,
    min_balance: f64,
}

#[pymethods]
impl ValidatedAccount {
    #[new]
    fn new(initial_balance: f64, min_balance: f64) -> PyResult<Self> {
        if initial_balance < min_balance {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Initial balance below minimum"
            ));
        }
        Ok(ValidatedAccount { balance: initial_balance, min_balance })
    }

    #[getter]
    fn balance(&self) -> f64 {
        self.balance
    }

    #[setter]
    fn set_balance(&mut self, value: f64) -> PyResult<()> {
        if value < self.min_balance {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Balance cannot go below minimum"
            ));
        }
        self.balance = value;
        Ok(())
    }

    #[getter]
    fn available_balance(&self) -> f64 {
        self.balance - self.min_balance
    }
}

/// Person with computed full name
#[pyclass]
struct PersonWithName {
    #[pyo3(get, set)]
    first_name: String,
    #[pyo3(get, set)]
    last_name: String,
}

#[pymethods]
impl PersonWithName {
    #[new]
    fn new(first_name: String, last_name: String) -> Self {
        PersonWithName { first_name, last_name }
    }

    #[getter]
    fn full_name(&self) -> String {
        format!("{} {}", self.first_name, self.last_name)
    }

    #[getter]
    fn initials(&self) -> String {
        format!(
            "{}{}",
            self.first_name.chars().next().unwrap_or(' '),
            self.last_name.chars().next().unwrap_or(' ')
        )
    }
}

/// Rectangle with computed properties
#[pyclass]
struct SmartRectangle {
    width: f64,
    height: f64,
}

#[pymethods]
impl SmartRectangle {
    #[new]
    fn new(width: f64, height: f64) -> Self {
        SmartRectangle { width, height }
    }

    #[getter]
    fn width(&self) -> f64 {
        self.width
    }

    #[setter]
    fn set_width(&mut self, value: f64) -> PyResult<()> {
        if value <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err("Width must be positive"));
        }
        self.width = value;
        Ok(())
    }

    #[getter]
    fn height(&self) -> f64 {
        self.height
    }

    #[setter]
    fn set_height(&mut self, value: f64) -> PyResult<()> {
        if value <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err("Height must be positive"));
        }
        self.height = value;
        Ok(())
    }

    #[getter]
    fn area(&self) -> f64 {
        self.width * self.height
    }

    #[getter]
    fn perimeter(&self) -> f64 {
        2.0 * (self.width + self.height)
    }

    #[getter]
    fn is_square(&self) -> bool {
        (self.width - self.height).abs() < 1e-10
    }
}

#[pymodule]
fn property_methods(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Temperature>()?;
    m.add_class::<ValidatedAccount>()?;
    m.add_class::<PersonWithName>()?;
    m.add_class::<SmartRectangle>()?;
    Ok(())
}
