//! Simple Python classes implemented in Rust
//!
//! This example demonstrates:
//! - Creating Python classes with #[pyclass]
//! - Instance methods with #[pymethods]
//! - Constructors (__new__)
//! - String representation (__repr__, __str__)
//! - Mutable vs immutable methods

use pyo3::prelude::*;

/// A simple counter class
#[pyclass]
struct Counter {
    #[pyo3(get, set)]
    value: i64,
}

#[pymethods]
impl Counter {
    /// Create a new counter
    #[new]
    fn new(initial: Option<i64>) -> Self {
        Counter {
            value: initial.unwrap_or(0),
        }
    }

    /// Increment the counter
    fn increment(&mut self) {
        self.value += 1;
    }

    /// Decrement the counter
    fn decrement(&mut self) {
        self.value -= 1;
    }

    /// Add a value to the counter
    fn add(&mut self, amount: i64) {
        self.value += amount;
    }

    /// Reset the counter to zero
    fn reset(&mut self) {
        self.value = 0;
    }

    /// Get the current value (immutable method)
    fn get_value(&self) -> i64 {
        self.value
    }

    /// String representation
    fn __repr__(&self) -> String {
        format!("Counter(value={})", self.value)
    }

    fn __str__(&self) -> String {
        format!("Counter: {}", self.value)
    }
}

/// A point in 2D space
#[pyclass]
struct Point {
    #[pyo3(get, set)]
    x: f64,
    #[pyo3(get, set)]
    y: f64,
}

#[pymethods]
impl Point {
    #[new]
    fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }

    /// Calculate distance from origin
    fn distance_from_origin(&self) -> f64 {
        (self.x.powi(2) + self.y.powi(2)).sqrt()
    }

    /// Calculate distance from another point
    fn distance_from(&self, other: &Point) -> f64 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        (dx.powi(2) + dy.powi(2)).sqrt()
    }

    /// Move the point by offset
    fn move_by(&mut self, dx: f64, dy: f64) {
        self.x += dx;
        self.y += dy;
    }

    /// Create a new point at origin
    #[staticmethod]
    fn origin() -> Self {
        Point { x: 0.0, y: 0.0 }
    }

    fn __repr__(&self) -> String {
        format!("Point(x={}, y={})", self.x, self.y)
    }
}

/// A person with name and age
#[pyclass]
struct Person {
    #[pyo3(get)]
    name: String,
    #[pyo3(get, set)]
    age: u32,
}

#[pymethods]
impl Person {
    #[new]
    fn new(name: String, age: u32) -> PyResult<Self> {
        if name.is_empty() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Name cannot be empty",
            ));
        }
        Ok(Person { name, age })
    }

    /// Get a greeting
    fn greet(&self) -> String {
        format!("Hello, I'm {} and I'm {} years old.", self.name, self.age)
    }

    /// Check if person is an adult
    fn is_adult(&self) -> bool {
        self.age >= 18
    }

    /// Have a birthday
    fn birthday(&mut self) {
        self.age += 1;
    }

    fn __repr__(&self) -> String {
        format!("Person(name='{}', age={})", self.name, self.age)
    }
}

/// A bank account
#[pyclass]
struct BankAccount {
    #[pyo3(get)]
    account_number: String,
    balance: f64,
}

#[pymethods]
impl BankAccount {
    #[new]
    fn new(account_number: String, initial_balance: Option<f64>) -> PyResult<Self> {
        let balance = initial_balance.unwrap_or(0.0);
        if balance < 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Initial balance cannot be negative",
            ));
        }
        Ok(BankAccount {
            account_number,
            balance,
        })
    }

    /// Get the current balance
    fn get_balance(&self) -> f64 {
        self.balance
    }

    /// Deposit money
    fn deposit(&mut self, amount: f64) -> PyResult<()> {
        if amount <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Deposit amount must be positive",
            ));
        }
        self.balance += amount;
        Ok(())
    }

    /// Withdraw money
    fn withdraw(&mut self, amount: f64) -> PyResult<()> {
        if amount <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Withdrawal amount must be positive",
            ));
        }
        if amount > self.balance {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Insufficient funds",
            ));
        }
        self.balance -= amount;
        Ok(())
    }

    /// Transfer money to another account
    fn transfer(&mut self, other: &mut BankAccount, amount: f64) -> PyResult<()> {
        self.withdraw(amount)?;
        other.deposit(amount)?;
        Ok(())
    }

    fn __repr__(&self) -> String {
        format!(
            "BankAccount(account_number='{}', balance={:.2})",
            self.account_number, self.balance
        )
    }
}

/// A simple rectangle
#[pyclass]
struct Rectangle {
    #[pyo3(get, set)]
    width: f64,
    #[pyo3(get, set)]
    height: f64,
}

#[pymethods]
impl Rectangle {
    #[new]
    fn new(width: f64, height: f64) -> PyResult<Self> {
        if width <= 0.0 || height <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Width and height must be positive",
            ));
        }
        Ok(Rectangle { width, height })
    }

    /// Calculate area
    fn area(&self) -> f64 {
        self.width * self.height
    }

    /// Calculate perimeter
    fn perimeter(&self) -> f64 {
        2.0 * (self.width + self.height)
    }

    /// Check if it's a square
    fn is_square(&self) -> bool {
        (self.width - self.height).abs() < 1e-10
    }

    /// Scale the rectangle
    fn scale(&mut self, factor: f64) -> PyResult<()> {
        if factor <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Scale factor must be positive",
            ));
        }
        self.width *= factor;
        self.height *= factor;
        Ok(())
    }

    /// Create a square
    #[staticmethod]
    fn square(side: f64) -> PyResult<Self> {
        Rectangle::new(side, side)
    }

    fn __repr__(&self) -> String {
        format!("Rectangle(width={}, height={})", self.width, self.height)
    }
}

/// Python module initialization
#[pymodule]
fn simple_class(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Counter>()?;
    m.add_class::<Point>()?;
    m.add_class::<Person>()?;
    m.add_class::<BankAccount>()?;
    m.add_class::<Rectangle>()?;
    Ok(())
}
