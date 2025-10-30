//! Basic WebSocket handler with PyO3

use pyo3::prelude::*;
use std::sync::Arc;
use tokio::sync::Mutex;

#[pyclass]
struct WebSocketHandler {
    messages: Arc<Mutex<Vec<Vec<u8>>>>,
}

#[pymethods]
impl WebSocketHandler {
    #[new]
    fn new() -> Self {
        WebSocketHandler {
            messages: Arc::new(Mutex::new(Vec::new())),
        }
    }

    fn add_message(&self, py: Python, data: Vec<u8>) -> PyResult<()> {
        let messages = self.messages.clone();
        py.allow_threads(|| {
            tokio::runtime::Runtime::new().unwrap().block_on(async {
                messages.lock().await.push(data);
            });
        });
        Ok(())
    }

    fn get_messages(&self, py: Python) -> PyResult<Vec<Vec<u8>>> {
        let messages = self.messages.clone();
        py.allow_threads(|| {
            tokio::runtime::Runtime::new().unwrap().block_on(async {
                Ok(messages.lock().await.clone())
            })
        })
    }

    fn clear_messages(&self, py: Python) -> PyResult<()> {
        let messages = self.messages.clone();
        py.allow_threads(|| {
            tokio::runtime::Runtime::new().unwrap().block_on(async {
                messages.lock().await.clear();
            });
        });
        Ok(())
    }
}

#[pyfunction]
fn process_ws_message(data: Vec<u8>) -> PyResult<Vec<u8>> {
    // Simple echo with transformation
    Ok(data.iter().map(|b| b.wrapping_add(1)).collect())
}

#[pymodule]
fn websocket_basic(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<WebSocketHandler>()?;
    m.add_function(wrap_pyfunction!(process_ws_message, m)?)?;
    Ok(())
}
