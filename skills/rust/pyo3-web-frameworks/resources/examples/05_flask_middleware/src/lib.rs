//! Flask middleware with PyO3

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::Instant;

#[pyclass]
struct RequestLogger {
    logs: Arc<RwLock<Vec<String>>>,
}

#[pymethods]
impl RequestLogger {
    #[new]
    fn new() -> Self {
        RequestLogger {
            logs: Arc::new(RwLock::new(Vec::new())),
        }
    }

    fn log_request(&self, method: String, path: String, status: u16, duration: f64) -> PyResult<()> {
        let mut logs = self.logs.write().unwrap();
        logs.push(format!("{} {} {} {:.3}s", method, path, status, duration));
        Ok(())
    }

    fn get_logs(&self) -> PyResult<Vec<String>> {
        Ok(self.logs.read().unwrap().clone())
    }

    fn clear_logs(&self) -> PyResult<()> {
        self.logs.write().unwrap().clear();
        Ok(())
    }
}

#[pyclass]
struct RequestTracker {
    active: Arc<RwLock<HashMap<u64, Instant>>>,
}

#[pymethods]
impl RequestTracker {
    #[new]
    fn new() -> Self {
        RequestTracker {
            active: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn start_request(&self, request_id: u64) -> PyResult<()> {
        self.active.write().unwrap().insert(request_id, Instant::now());
        Ok(())
    }

    fn end_request(&self, request_id: u64) -> PyResult<f64> {
        let mut active = self.active.write().unwrap();
        if let Some(start) = active.remove(&request_id) {
            Ok(start.elapsed().as_secs_f64())
        } else {
            Ok(0.0)
        }
    }

    fn active_requests(&self) -> PyResult<usize> {
        Ok(self.active.read().unwrap().len())
    }
}

#[pyfunction]
fn sanitize_headers(headers: Vec<(String, String)>) -> PyResult<Vec<(String, String)>> {
    let sensitive = vec!["authorization", "cookie", "x-api-key"];
    Ok(headers.into_iter()
        .map(|(k, v)| {
            if sensitive.contains(&k.to_lowercase().as_str()) {
                (k, "[REDACTED]".to_string())
            } else {
                (k, v)
            }
        })
        .collect())
}

#[pymodule]
fn flask_middleware(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RequestLogger>()?;
    m.add_class::<RequestTracker>()?;
    m.add_function(wrap_pyfunction!(sanitize_headers, m)?)?;
    Ok(())
}
