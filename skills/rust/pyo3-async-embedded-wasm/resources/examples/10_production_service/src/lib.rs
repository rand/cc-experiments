use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{Mutex, Semaphore};

/// Production-grade async service with connection pooling, rate limiting, and monitoring
#[pyclass]
struct AsyncService {
    max_concurrent: Arc<Semaphore>,
    stats: Arc<Mutex<ServiceStats>>,
}

#[derive(Default)]
struct ServiceStats {
    requests: u64,
    successes: u64,
    failures: u64,
}

#[pymethods]
impl AsyncService {
    #[new]
    fn new(max_concurrent: usize) -> Self {
        Self {
            max_concurrent: Arc::new(Semaphore::new(max_concurrent)),
            stats: Arc::new(Mutex::new(ServiceStats::default())),
        }
    }

    fn process_request(&self, py: Python, data: Vec<i64>) -> PyResult<&PyAny> {
        let semaphore = self.max_concurrent.clone();
        let stats = self.stats.clone();

        future_into_py(py, async move {
            // Acquire permit (rate limiting)
            let _permit = semaphore.acquire().await.unwrap();

            // Update stats
            {
                let mut s = stats.lock().await;
                s.requests += 1;
            }

            // Simulate processing
            tokio::time::sleep(Duration::from_millis(100)).await;

            // Process data
            let result: Result<Vec<i64>, String> = if data.iter().any(|&x| x < 0) {
                Err("Negative values not allowed".to_string())
            } else {
                Ok(data.iter().map(|x| x * 2).collect())
            };

            // Update stats
            {
                let mut s = stats.lock().await;
                match &result {
                    Ok(_) => s.successes += 1,
                    Err(_) => s.failures += 1,
                }
            }

            // Return result
            Python::with_gil(|py| match result {
                Ok(data) => Ok(data.into_py(py)),
                Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(e)),
            })
        })
    }

    fn get_stats(&self, py: Python) -> PyResult<&PyAny> {
        let stats = self.stats.clone();

        future_into_py(py, async move {
            let s = stats.lock().await;
            Python::with_gil(|py| {
                let dict = pyo3::types::PyDict::new(py);
                dict.set_item("requests", s.requests)?;
                dict.set_item("successes", s.successes)?;
                dict.set_item("failures", s.failures)?;
                dict.set_item("success_rate", {
                    if s.requests > 0 {
                        (s.successes as f64 / s.requests as f64) * 100.0
                    } else {
                        0.0
                    }
                })?;
                Ok(dict.into())
            })
        })
    }

    fn health_check(&self, py: Python) -> PyResult<&PyAny> {
        let stats = self.stats.clone();

        future_into_py(py, async move {
            let s = stats.lock().await;
            let success_rate = if s.requests > 0 {
                (s.successes as f64 / s.requests as f64) * 100.0
            } else {
                100.0
            };

            Python::with_gil(|py| {
                let dict = pyo3::types::PyDict::new(py);
                dict.set_item("healthy", success_rate >= 95.0)?;
                dict.set_item("success_rate", success_rate)?;
                dict.set_item("total_requests", s.requests)?;
                Ok(dict.into())
            })
        })
    }

    fn reset_stats(&self, py: Python) -> PyResult<&PyAny> {
        let stats = self.stats.clone();

        future_into_py(py, async move {
            let mut s = stats.lock().await;
            *s = ServiceStats::default();
            Ok(Python::with_gil(|py| "Stats reset".into_py(py)))
        })
    }
}

#[pymodule]
fn production_service(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<AsyncService>()?;
    Ok(())
}
