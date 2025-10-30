//! Class inheritance patterns using PyO3
//!
//! Note: PyO3 doesn't support traditional inheritance but we can demonstrate:
//! - Composition over inheritance
//! - Trait-based polymorphism
//! - Interface-like patterns
//! - Type hierarchies using enums

use pyo3::prelude::*;

/// Base interface for shapes
trait Shape {
    fn area(&self) -> f64;
    fn perimeter(&self) -> f64;
}

/// Circle implementation
#[pyclass]
struct Circle {
    #[pyo3(get, set)]
    radius: f64,
}

#[pymethods]
impl Circle {
    #[new]
    fn new(radius: f64) -> PyResult<Self> {
        if radius <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err("Radius must be positive"));
        }
        Ok(Circle { radius })
    }

    fn area(&self) -> f64 {
        std::f64::consts::PI * self.radius * self.radius
    }

    fn perimeter(&self) -> f64 {
        2.0 * std::f64::consts::PI * self.radius
    }

    fn diameter(&self) -> f64 {
        2.0 * self.radius
    }
}

/// Rectangle implementation
#[pyclass]
struct RectangleShape {
    #[pyo3(get, set)]
    width: f64,
    #[pyo3(get, set)]
    height: f64,
}

#[pymethods]
impl RectangleShape {
    #[new]
    fn new(width: f64, height: f64) -> PyResult<Self> {
        if width <= 0.0 || height <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err("Dimensions must be positive"));
        }
        Ok(RectangleShape { width, height })
    }

    fn area(&self) -> f64 {
        self.width * self.height
    }

    fn perimeter(&self) -> f64 {
        2.0 * (self.width + self.height)
    }

    fn diagonal(&self) -> f64 {
        (self.width.powi(2) + self.height.powi(2)).sqrt()
    }
}

/// Composition pattern - Employee composed with Person data
#[pyclass]
struct Employee {
    #[pyo3(get)]
    name: String,
    #[pyo3(get, set)]
    age: u32,
    #[pyo3(get)]
    employee_id: String,
    #[pyo3(get, set)]
    department: String,
    #[pyo3(get, set)]
    salary: f64,
}

#[pymethods]
impl Employee {
    #[new]
    fn new(name: String, age: u32, employee_id: String, department: String, salary: f64) -> Self {
        Employee {
            name,
            age,
            employee_id,
            department,
            salary,
        }
    }

    fn give_raise(&mut self, percentage: f64) {
        self.salary *= 1.0 + (percentage / 100.0);
    }

    fn change_department(&mut self, new_dept: String) {
        self.department = new_dept;
    }
}

/// Manager extends Employee concept through composition
#[pyclass]
struct Manager {
    employee: Employee,
    #[pyo3(get, set)]
    team_size: u32,
    #[pyo3(get, set)]
    budget: f64,
}

#[pymethods]
impl Manager {
    #[new]
    fn new(employee: Employee, team_size: u32, budget: f64) -> Self {
        Manager {
            employee,
            team_size,
            budget,
        }
    }

    fn get_name(&self) -> String {
        self.employee.name.clone()
    }

    fn get_salary(&self) -> f64 {
        self.employee.salary
    }

    fn give_raise(&mut self, percentage: f64) {
        self.employee.give_raise(percentage);
    }

    fn allocate_budget(&mut self, amount: f64) -> PyResult<()> {
        if amount > self.budget {
            return Err(pyo3::exceptions::PyValueError::new_err("Insufficient budget"));
        }
        self.budget -= amount;
        Ok(())
    }
}

/// Vehicle hierarchy using enums
#[pyclass]
#[derive(Clone)]
struct Vehicle {
    #[pyo3(get)]
    make: String,
    #[pyo3(get)]
    model: String,
    #[pyo3(get)]
    year: u32,
    #[pyo3(get)]
    vehicle_type: String,
}

#[pymethods]
impl Vehicle {
    #[staticmethod]
    fn car(make: String, model: String, year: u32, doors: u32) -> Self {
        Vehicle {
            make,
            model,
            year,
            vehicle_type: format!("Car({} doors)", doors),
        }
    }

    #[staticmethod]
    fn truck(make: String, model: String, year: u32, bed_length: f64) -> Self {
        Vehicle {
            make,
            model,
            year,
            vehicle_type: format!("Truck({} ft bed)", bed_length),
        }
    }

    #[staticmethod]
    fn motorcycle(make: String, model: String, year: u32, engine_cc: u32) -> Self {
        Vehicle {
            make,
            model,
            year,
            vehicle_type: format!("Motorcycle({} cc)", engine_cc),
        }
    }

    fn description(&self) -> String {
        format!("{} {} {} ({})", self.year, self.make, self.model, self.vehicle_type)
    }
}

/// Abstract interface pattern using function dispatch
#[pyfunction]
fn calculate_shape_area(shape_type: &str, param1: f64, param2: Option<f64>) -> PyResult<f64> {
    match shape_type {
        "circle" => Ok(std::f64::consts::PI * param1 * param1),
        "rectangle" => {
            let height = param2.ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err("Rectangle requires two parameters")
            })?;
            Ok(param1 * height)
        }
        "square" => Ok(param1 * param1),
        _ => Err(pyo3::exceptions::PyValueError::new_err("Unknown shape type")),
    }
}

#[pymodule]
fn class_inheritance(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Circle>()?;
    m.add_class::<RectangleShape>()?;
    m.add_class::<Employee>()?;
    m.add_class::<Manager>()?;
    m.add_class::<Vehicle>()?;
    m.add_function(wrap_pyfunction!(calculate_shape_area, m)?)?;
    Ok(())
}
