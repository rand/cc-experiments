//! Async FastAPI request handlers with PyO3 and Tokio
//!
//! This example demonstrates:
//! - Async function integration with pyo3-asyncio
//! - Using Tokio runtime for async operations
//! - Non-blocking I/O operations
//! - Concurrent request processing
//! - Async error handling

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use pyo3_asyncio::tokio::future_into_py;
use tokio::time::{sleep, Duration};
use std::sync::Arc;
use tokio::sync::Mutex;

/// Simulate async data fetching with delay
#[pyfunction]
fn fetch_data_async(py: Python, id: u64, delay_ms: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        sleep(Duration::from_millis(delay_ms)).await;

        let result = format!("Data for ID {}", id);

        Python::with_gil(|py| Ok(result.into_py(py)))
    })
}

/// Process multiple items concurrently
#[pyfunction]
fn process_batch_async(py: Python, items: Vec<String>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let mut handles = vec![];

        for item in items {
            let handle = tokio::spawn(async move {
                sleep(Duration::from_millis(10)).await;
                item.to_uppercase()
            });
            handles.push(handle);
        }

        let mut results = vec![];
        for handle in handles {
            let result = handle.await
                .map_err(|e| format!("Task failed: {}", e))?;
            results.push(result);
        }

        Python::with_gil(|py| Ok(results.into_py(py)))
    })
}

/// Async computation with progress tracking
#[pyfunction]
fn compute_with_progress(py: Python, n: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let mut sum = 0u64;

        for i in 0..n {
            if i % 100 == 0 {
                sleep(Duration::from_millis(1)).await;
            }
            sum += i;
        }

        Python::with_gil(|py| Ok(sum.into_py(py)))
    })
}

/// Simulate async API call with timeout
#[pyfunction]
fn api_call_with_timeout(py: Python, endpoint: String, timeout_ms: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let timeout_result = tokio::time::timeout(
            Duration::from_millis(timeout_ms),
            async {
                sleep(Duration::from_millis(timeout_ms / 2)).await;
                format!("Response from {}", endpoint)
            }
        ).await;

        match timeout_result {
            Ok(result) => Python::with_gil(|py| Ok(result.into_py(py))),
            Err(_) => Err(PyRuntimeError::new_err("Request timeout")),
        }
    })
}

/// Async data aggregation from multiple sources
#[pyfunction]
fn aggregate_async(py: Python, sources: Vec<String>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let mut results = vec![];

        for source in sources {
            sleep(Duration::from_millis(20)).await;
            results.push(format!("Data from {}", source));
        }

        let aggregated = results.join(", ");

        Python::with_gil(|py| Ok(aggregated.into_py(py)))
    })
}

/// Async counter with shared state
#[pyclass]
struct AsyncCounter {
    count: Arc<Mutex<u64>>,
}

#[pymethods]
impl AsyncCounter {
    #[new]
    fn new() -> Self {
        AsyncCounter {
            count: Arc::new(Mutex::new(0)),
        }
    }

    fn increment_async<'a>(&self, py: Python<'a>) -> PyResult<&'a PyAny> {
        let count = self.count.clone();
        future_into_py(py, async move {
            let mut c = count.lock().await;
            *c += 1;
            let value = *c;
            drop(c);

            Python::with_gil(|py| Ok(value.into_py(py)))
        })
    }

    fn get_count_async<'a>(&self, py: Python<'a>) -> PyResult<&'a PyAny> {
        let count = self.count.clone();
        future_into_py(py, async move {
            let c = count.lock().await;
            let value = *c;

            Python::with_gil(|py| Ok(value.into_py(py)))
        })
    }

    fn reset_async<'a>(&self, py: Python<'a>) -> PyResult<&'a PyAny> {
        let count = self.count.clone();
        future_into_py(py, async move {
            let mut c = count.lock().await;
            *c = 0;

            Python::with_gil(|py| Ok(py.None()))
        })
    }
}

/// Async batch processor with concurrency limit
#[pyfunction]
fn process_with_concurrency(py: Python, items: Vec<f64>, max_concurrent: usize) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        use tokio::sync::Semaphore;

        let semaphore = Arc::new(Semaphore::new(max_concurrent));
        let mut handles = vec![];

        for item in items {
            let permit = semaphore.clone().acquire_owned().await
                .map_err(|e| format!("Semaphore error: {}", e))?;

            let handle = tokio::spawn(async move {
                sleep(Duration::from_millis(50)).await;
                let result = item * item;
                drop(permit);
                result
            });

            handles.push(handle);
        }

        let mut results = vec![];
        for handle in handles {
            let result = handle.await
                .map_err(|e| format!("Task failed: {}", e))?;
            results.push(result);
        }

        Python::with_gil(|py| Ok(results.into_py(py)))
    })
}

/// Async retry logic
#[pyfunction]
fn fetch_with_retry(py: Python, url: String, max_retries: u32) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let mut retries = 0;

        loop {
            sleep(Duration::from_millis(100)).await;

            // Simulate 50% success rate
            if retries % 2 == 1 {
                return Python::with_gil(|py| {
                    Ok(format!("Success from {} after {} retries", url, retries).into_py(py))
                });
            }

            retries += 1;
            if retries >= max_retries {
                return Err(PyRuntimeError::new_err(
                    format!("Failed after {} retries", max_retries)
                ));
            }
        }
    })
}

/// Python module initialization
#[pymodule]
fn fastapi_async(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fetch_data_async, m)?)?;
    m.add_function(wrap_pyfunction!(process_batch_async, m)?)?;
    m.add_function(wrap_pyfunction!(compute_with_progress, m)?)?;
    m.add_function(wrap_pyfunction!(api_call_with_timeout, m)?)?;
    m.add_function(wrap_pyfunction!(aggregate_async, m)?)?;
    m.add_function(wrap_pyfunction!(process_with_concurrency, m)?)?;
    m.add_function(wrap_pyfunction!(fetch_with_retry, m)?)?;
    m.add_class::<AsyncCounter>()?;
    Ok(())
}
