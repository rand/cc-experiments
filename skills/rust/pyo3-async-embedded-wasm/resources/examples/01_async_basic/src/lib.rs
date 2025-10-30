use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use std::time::Duration;

/// Basic async function that sleeps for a given number of seconds
#[pyfunction]
fn async_sleep(py: Python, seconds: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        tokio::time::sleep(Duration::from_secs(seconds)).await;
        Ok(Python::with_gil(|py| "Sleep completed".into_py(py)))
    })
}

/// Async function that performs a simple computation
#[pyfunction]
fn async_compute(py: Python, n: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        // Simulate async computation
        tokio::time::sleep(Duration::from_millis(100)).await;
        let result = (1..=n).sum::<u64>();
        Ok(Python::with_gil(|py| result.into_py(py)))
    })
}

/// Async function that returns a greeting
#[pyfunction]
fn async_greet(py: Python, name: String) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        tokio::time::sleep(Duration::from_millis(50)).await;
        let greeting = format!("Hello, {}!", name);
        Ok(Python::with_gil(|py| greeting.into_py(py)))
    })
}

/// Async function demonstrating error handling
#[pyfunction]
fn async_divide(py: Python, a: f64, b: f64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        tokio::time::sleep(Duration::from_millis(10)).await;

        if b == 0.0 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Cannot divide by zero"
            ));
        }

        let result = a / b;
        Ok(Python::with_gil(|py| result.into_py(py)))
    })
}

/// Module initialization
#[pymodule]
fn async_basic(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(async_sleep, m)?)?;
    m.add_function(wrap_pyfunction!(async_compute, m)?)?;
    m.add_function(wrap_pyfunction!(async_greet, m)?)?;
    m.add_function(wrap_pyfunction!(async_divide, m)?)?;
    Ok(())
}
