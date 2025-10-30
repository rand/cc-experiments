//! Complex type conversions with Option, Result, and nested structures
//!
//! This example demonstrates:
//! - Option<T> (None handling)
//! - Result<T, E> (error handling)
//! - Nested structures
//! - Enums
//! - Complex data transformations

use pyo3::exceptions::{PyKeyError, PyValueError};
use pyo3::prelude::*;
use std::collections::HashMap;

/// Result type for operations
#[pyclass]
#[derive(Clone)]
struct OperationResult {
    #[pyo3(get)]
    success: bool,
    #[pyo3(get)]
    value: Option<i64>,
    #[pyo3(get)]
    error: Option<String>,
}

#[pymethods]
impl OperationResult {
    #[new]
    fn new(success: bool, value: Option<i64>, error: Option<String>) -> Self {
        OperationResult {
            success,
            value,
            error,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "OperationResult(success={}, value={:?}, error={:?})",
            self.success, self.value, self.error
        )
    }
}

/// Safe division that returns Result
#[pyfunction]
fn safe_divide(a: i64, b: i64) -> PyResult<OperationResult> {
    if b == 0 {
        Ok(OperationResult {
            success: false,
            value: None,
            error: Some("Division by zero".to_string()),
        })
    } else {
        Ok(OperationResult {
            success: true,
            value: Some(a / b),
            error: None,
        })
    }
}

/// Parse integer with Option return
#[pyfunction]
fn parse_int(s: String) -> Option<i64> {
    s.parse::<i64>().ok()
}

/// Nested structure - Address
#[pyclass]
#[derive(Clone)]
struct Address {
    #[pyo3(get, set)]
    street: String,
    #[pyo3(get, set)]
    city: String,
    #[pyo3(get, set)]
    zip_code: String,
    #[pyo3(get, set)]
    country: String,
}

#[pymethods]
impl Address {
    #[new]
    fn new(street: String, city: String, zip_code: String, country: String) -> Self {
        Address {
            street,
            city,
            zip_code,
            country,
        }
    }

    fn __repr__(&self) -> String {
        format!("{}, {}, {} {}", self.street, self.city, self.zip_code, self.country)
    }
}

/// Complex nested structure - User with optional fields
#[pyclass]
#[derive(Clone)]
struct User {
    #[pyo3(get, set)]
    id: u64,
    #[pyo3(get, set)]
    name: String,
    #[pyo3(get, set)]
    email: Option<String>,
    #[pyo3(get, set)]
    age: Option<u32>,
    address: Option<Address>,
}

#[pymethods]
impl User {
    #[new]
    fn new(
        id: u64,
        name: String,
        email: Option<String>,
        age: Option<u32>,
        address: Option<Address>,
    ) -> Self {
        User {
            id,
            name,
            email,
            age,
            address,
        }
    }

    fn get_address(&self) -> Option<Address> {
        self.address.clone()
    }

    fn set_address(&mut self, address: Option<Address>) {
        self.address = address;
    }

    fn has_email(&self) -> bool {
        self.email.is_some()
    }

    fn has_address(&self) -> bool {
        self.address.is_some()
    }

    fn __repr__(&self) -> String {
        format!("User(id={}, name='{}', email={:?})", self.id, self.name, self.email)
    }
}

/// Enum representing different message types
#[pyclass]
#[derive(Clone)]
enum MessageType {
    Info,
    Warning,
    Error,
}

/// Message with type and content
#[pyclass]
#[derive(Clone)]
struct Message {
    #[pyo3(get)]
    msg_type: String,
    #[pyo3(get)]
    content: String,
    #[pyo3(get)]
    timestamp: Option<i64>,
}

#[pymethods]
impl Message {
    #[new]
    fn new(msg_type: String, content: String, timestamp: Option<i64>) -> Self {
        Message {
            msg_type,
            content,
            timestamp,
        }
    }

    #[staticmethod]
    fn info(content: String) -> Self {
        Message {
            msg_type: "INFO".to_string(),
            content,
            timestamp: None,
        }
    }

    #[staticmethod]
    fn warning(content: String) -> Self {
        Message {
            msg_type: "WARNING".to_string(),
            content,
            timestamp: None,
        }
    }

    #[staticmethod]
    fn error(content: String) -> Self {
        Message {
            msg_type: "ERROR".to_string(),
            content,
            timestamp: None,
        }
    }
}

/// Complex data structure with nested collections
#[pyclass]
struct DataStore {
    data: HashMap<String, Vec<Option<i64>>>,
}

#[pymethods]
impl DataStore {
    #[new]
    fn new() -> Self {
        DataStore {
            data: HashMap::new(),
        }
    }

    fn add_value(&mut self, key: String, value: Option<i64>) {
        self.data.entry(key).or_insert_with(Vec::new).push(value);
    }

    fn get_values(&self, key: String) -> Option<Vec<Option<i64>>> {
        self.data.get(&key).cloned()
    }

    fn get_sum(&self, key: String) -> Option<i64> {
        self.data.get(&key).map(|values| {
            values.iter().filter_map(|&v| v).sum()
        })
    }

    fn keys(&self) -> Vec<String> {
        self.data.keys().cloned().collect()
    }
}

/// Function working with complex nested types
#[pyfunction]
fn process_users(users: Vec<User>) -> HashMap<String, Vec<String>> {
    let mut result: HashMap<String, Vec<String>> = HashMap::new();

    for user in users {
        let city = user
            .address
            .as_ref()
            .map(|a| a.city.clone())
            .unwrap_or_else(|| "Unknown".to_string());

        result
            .entry(city)
            .or_insert_with(Vec::new)
            .push(user.name.clone());
    }

    result
}

/// Function demonstrating Option chaining
#[pyfunction]
fn get_user_city(user: User) -> Option<String> {
    user.address.map(|addr| addr.city)
}

/// Transform nested data
#[pyfunction]
fn extract_emails(users: Vec<User>) -> Vec<String> {
    users.into_iter().filter_map(|u| u.email).collect()
}

/// Merge two DataStores
#[pyfunction]
fn merge_stores(store1: DataStore, store2: DataStore) -> DataStore {
    let mut merged = DataStore::new();

    for (key, values) in store1.data.into_iter().chain(store2.data.into_iter()) {
        for value in values {
            merged.add_value(key.clone(), value);
        }
    }

    merged
}

#[pymodule]
fn complex_types(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<OperationResult>()?;
    m.add_class::<Address>()?;
    m.add_class::<User>()?;
    m.add_class::<Message>()?;
    m.add_class::<DataStore>()?;
    m.add_function(wrap_pyfunction!(safe_divide, m)?)?;
    m.add_function(wrap_pyfunction!(parse_int, m)?)?;
    m.add_function(wrap_pyfunction!(process_users, m)?)?;
    m.add_function(wrap_pyfunction!(get_user_city, m)?)?;
    m.add_function(wrap_pyfunction!(extract_emails, m)?)?;
    m.add_function(wrap_pyfunction!(merge_stores, m)?)?;
    Ok(())
}
