//! Generic type implementations with PyO3
//!
//! Demonstrates:
//! - Generic-like behavior through enums
//! - Type-erased containers
//! - Polymorphic operations
//! - Container types (Stack, Queue, etc.)

use pyo3::prelude::*;
use pyo3::types::PyAny;

/// Generic-like Stack using PyAny
#[pyclass]
struct Stack {
    items: Vec<Py<PyAny>>,
}

#[pymethods]
impl Stack {
    #[new]
    fn new() -> Self {
        Stack { items: Vec::new() }
    }

    fn push(&mut self, py: Python, item: Py<PyAny>) {
        self.items.push(item);
    }

    fn pop(&mut self, py: Python) -> Option<Py<PyAny>> {
        self.items.pop()
    }

    fn peek(&self, py: Python) -> Option<Py<PyAny>> {
        self.items.last().map(|item| item.clone_ref(py))
    }

    fn is_empty(&self) -> bool {
        self.items.is_empty()
    }

    fn size(&self) -> usize {
        self.items.len()
    }

    fn clear(&mut self) {
        self.items.clear();
    }
}

/// Type-specific stacks for common types
#[pyclass]
struct IntStack {
    items: Vec<i64>,
}

#[pymethods]
impl IntStack {
    #[new]
    fn new() -> Self {
        IntStack { items: Vec::new() }
    }

    fn push(&mut self, item: i64) {
        self.items.push(item);
    }

    fn pop(&mut self) -> Option<i64> {
        self.items.pop()
    }

    fn peek(&self) -> Option<i64> {
        self.items.last().copied()
    }

    fn sum(&self) -> i64 {
        self.items.iter().sum()
    }
}

/// Generic-like Queue
#[pyclass]
struct Queue {
    items: Vec<Py<PyAny>>,
}

#[pymethods]
impl Queue {
    #[new]
    fn new() -> Self {
        Queue { items: Vec::new() }
    }

    fn enqueue(&mut self, py: Python, item: Py<PyAny>) {
        self.items.push(item);
    }

    fn dequeue(&mut self, py: Python) -> Option<Py<PyAny>> {
        if self.items.is_empty() {
            None
        } else {
            Some(self.items.remove(0))
        }
    }

    fn is_empty(&self) -> bool {
        self.items.is_empty()
    }

    fn size(&self) -> usize {
        self.items.len()
    }
}

/// Container that holds different types with type tracking
#[pyclass]
struct TypedContainer {
    strings: Vec<String>,
    integers: Vec<i64>,
    floats: Vec<f64>,
}

#[pymethods]
impl TypedContainer {
    #[new]
    fn new() -> Self {
        TypedContainer {
            strings: Vec::new(),
            integers: Vec::new(),
            floats: Vec::new(),
        }
    }

    fn add_string(&mut self, value: String) {
        self.strings.push(value);
    }

    fn add_int(&mut self, value: i64) {
        self.integers.push(value);
    }

    fn add_float(&mut self, value: f64) {
        self.floats.push(value);
    }

    fn get_strings(&self) -> Vec<String> {
        self.strings.clone()
    }

    fn get_ints(&self) -> Vec<i64> {
        self.integers.clone()
    }

    fn get_floats(&self) -> Vec<f64> {
        self.floats.clone()
    }

    fn total_items(&self) -> usize {
        self.strings.len() + self.integers.len() + self.floats.len()
    }
}

/// Pair holding two values of potentially different types
#[pyclass]
struct Pair {
    first: Py<PyAny>,
    second: Py<PyAny>,
}

#[pymethods]
impl Pair {
    #[new]
    fn new(first: Py<PyAny>, second: Py<PyAny>) -> Self {
        Pair { first, second }
    }

    fn get_first(&self, py: Python) -> Py<PyAny> {
        self.first.clone_ref(py)
    }

    fn get_second(&self, py: Python) -> Py<PyAny> {
        self.second.clone_ref(py)
    }

    fn swap(&mut self) {
        std::mem::swap(&mut self.first, &mut self.second);
    }
}

#[pymodule]
fn generic_types(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Stack>()?;
    m.add_class::<IntStack>()?;
    m.add_class::<Queue>()?;
    m.add_class::<TypedContainer>()?;
    m.add_class::<Pair>()?;
    Ok(())
}
