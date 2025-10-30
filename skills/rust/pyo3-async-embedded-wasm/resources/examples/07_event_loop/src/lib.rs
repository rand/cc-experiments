use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{broadcast, mpsc};

/// Custom event loop with pub/sub pattern
#[pyclass]
struct EventLoop {
    tx: Arc<broadcast::Sender<String>>,
}

#[pymethods]
impl EventLoop {
    #[new]
    fn new() -> Self {
        let (tx, _rx) = broadcast::channel(100);
        Self { tx: Arc::new(tx) }
    }

    fn emit(&self, event: String) -> PyResult<()> {
        self.tx.send(event).ok();
        Ok(())
    }

    fn subscribe(&self, py: Python) -> PyResult<&PyAny> {
        let mut rx = self.tx.subscribe();

        future_into_py(py, async move {
            let mut events = vec![];
            while let Ok(event) = rx.recv().await {
                events.push(event.clone());
                if events.len() >= 5 {
                    break;
                }
            }
            Ok(Python::with_gil(|py| events.into_py(py)))
        })
    }
}

/// Task scheduler
#[pyfunction]
fn schedule_task(py: Python, delay_ms: u64, task_id: String) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        tokio::time::sleep(Duration::from_millis(delay_ms)).await;
        Ok(Python::with_gil(|py| {
            format!("Task {} executed after {}ms", task_id, delay_ms).into_py(py)
        }))
    })
}

#[pymodule]
fn event_loop(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<EventLoop>()?;
    m.add_function(wrap_pyfunction!(schedule_task, m)?)?;
    Ok(())
}
