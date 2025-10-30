use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use std::sync::Arc;
use std::time::Duration;
use tokio::runtime::Runtime;
use tokio::sync::Mutex;
use tokio::task;

/// Global Tokio runtime (initialized once)
static RUNTIME: once_cell::sync::OnceCell<Runtime> = once_cell::sync::OnceCell::new();

/// Get or initialize the global Tokio runtime
fn get_runtime() -> &'static Runtime {
    RUNTIME.get_or_init(|| {
        tokio::runtime::Builder::new_multi_thread()
            .worker_threads(4)
            .thread_name("pyo3-tokio")
            .enable_all()
            .build()
            .expect("Failed to create Tokio runtime")
    })
}

/// Spawn a background task that runs independently
#[pyfunction]
fn spawn_background_task(py: Python, count: u64, delay_ms: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let handle = task::spawn(async move {
            for i in 0..count {
                tokio::time::sleep(Duration::from_millis(delay_ms)).await;
                println!("Background task iteration: {}/{}", i + 1, count);
            }
            "Background task completed".to_string()
        });

        // Don't wait for completion - just return handle info
        Ok(Python::with_gil(|py| {
            format!("Spawned background task with {} iterations", count).into_py(py)
        }))
    })
}

/// Execute multiple tasks concurrently
#[pyfunction]
fn concurrent_tasks(py: Python, urls: Vec<String>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let tasks: Vec<_> = urls
            .into_iter()
            .enumerate()
            .map(|(i, url)| {
                task::spawn(async move {
                    // Simulate async HTTP request
                    tokio::time::sleep(Duration::from_millis(100 + (i as u64 * 50))).await;
                    format!("Fetched: {}", url)
                })
            })
            .collect();

        let results: Vec<_> = futures::future::join_all(tasks)
            .await
            .into_iter()
            .map(|r| r.unwrap_or_else(|e| format!("Error: {}", e)))
            .collect();

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}

/// Shared state example with Arc<Mutex>
#[pyfunction]
fn shared_counter_demo(py: Python, increments: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let counter = Arc::new(Mutex::new(0u64));
        let mut handles = vec![];

        // Spawn multiple tasks that increment the counter
        for _ in 0..increments {
            let counter_clone = Arc::clone(&counter);
            let handle = task::spawn(async move {
                tokio::time::sleep(Duration::from_millis(10)).await;
                let mut count = counter_clone.lock().await;
                *count += 1;
            });
            handles.push(handle);
        }

        // Wait for all tasks to complete
        for handle in handles {
            handle.await.unwrap();
        }

        let final_count = *counter.lock().await;
        Ok(Python::with_gil(|py| final_count.into_py(py)))
    })
}

/// Timeout example using tokio::time::timeout
#[pyfunction]
fn with_timeout(py: Python, operation_ms: u64, timeout_ms: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let operation = async {
            tokio::time::sleep(Duration::from_millis(operation_ms)).await;
            "Operation completed"
        };

        match tokio::time::timeout(Duration::from_millis(timeout_ms), operation).await {
            Ok(result) => Ok(Python::with_gil(|py| result.into_py(py))),
            Err(_) => Err(PyErr::new::<pyo3::exceptions::PyTimeoutError, _>(
                format!(
                    "Operation timed out after {}ms (operation would take {}ms)",
                    timeout_ms, operation_ms
                ),
            )),
        }
    })
}

/// Channel-based communication example
#[pyfunction]
fn channel_demo(py: Python, message_count: usize) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let (tx, mut rx) = tokio::sync::mpsc::channel::<String>(32);

        // Producer task
        let producer = task::spawn(async move {
            for i in 0..message_count {
                let msg = format!("Message {}", i);
                if tx.send(msg).await.is_err() {
                    break;
                }
                tokio::time::sleep(Duration::from_millis(10)).await;
            }
        });

        // Consumer task
        let consumer = task::spawn(async move {
            let mut messages = Vec::new();
            while let Some(msg) = rx.recv().await {
                messages.push(msg);
            }
            messages
        });

        // Wait for both tasks
        producer.await.unwrap();
        let messages = consumer.await.unwrap();

        Ok(Python::with_gil(|py| messages.into_py(py)))
    })
}

/// Module initialization
#[pymodule]
fn tokio_runtime(_py: Python, m: &PyModule) -> PyResult<()> {
    // Initialize runtime on module import
    let _ = get_runtime();

    m.add_function(wrap_pyfunction!(spawn_background_task, m)?)?;
    m.add_function(wrap_pyfunction!(concurrent_tasks, m)?)?;
    m.add_function(wrap_pyfunction!(shared_counter_demo, m)?)?;
    m.add_function(wrap_pyfunction!(with_timeout, m)?)?;
    m.add_function(wrap_pyfunction!(channel_demo, m)?)?;
    Ok(())
}
