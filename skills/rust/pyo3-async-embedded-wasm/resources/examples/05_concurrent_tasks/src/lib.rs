use futures::future::{join_all, select_all, try_join_all};
use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use std::time::Duration;
use tokio::task;

/// Execute tasks concurrently and collect all results
#[pyfunction]
fn parallel_execute(py: Python, task_count: usize, delay_ms: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let tasks: Vec<_> = (0..task_count)
            .map(|i| {
                task::spawn(async move {
                    tokio::time::sleep(Duration::from_millis(delay_ms)).await;
                    format!("Task {} completed", i)
                })
            })
            .collect();

        let results = join_all(tasks)
            .await
            .into_iter()
            .map(|r| r.unwrap())
            .collect::<Vec<_>>();

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}

/// Race multiple tasks and return the first to complete
#[pyfunction]
fn race_tasks(py: Python, delays_ms: Vec<u64>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let tasks: Vec<_> = delays_ms
            .into_iter()
            .enumerate()
            .map(|(i, delay)| {
                task::spawn(async move {
                    tokio::time::sleep(Duration::from_millis(delay)).await;
                    (i, delay)
                })
            })
            .collect();

        let (result, _index, _remaining) = select_all(tasks).await;
        let (winner_idx, winner_delay) = result.unwrap();

        Ok(Python::with_gil(|py| {
            format!("Task {} won ({}ms)", winner_idx, winner_delay).into_py(py)
        }))
    })
}

/// Execute tasks with error handling (try_join_all)
#[pyfunction]
fn parallel_with_errors(py: Python, values: Vec<i64>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let tasks = values.into_iter().map(|val| async move {
            tokio::time::sleep(Duration::from_millis(10)).await;
            if val < 0 {
                Err(format!("Negative value: {}", val))
            } else {
                Ok(val * 2)
            }
        });

        match try_join_all(tasks).await {
            Ok(results) => Ok(Python::with_gil(|py| results.into_py(py))),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(e)),
        }
    })
}

/// Work-stealing pattern with dynamic task generation
#[pyfunction]
fn work_stealing(py: Python, work_items: Vec<i64>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        use tokio::sync::mpsc;

        let (tx, mut rx) = mpsc::channel::<i64>(100);
        let (result_tx, mut result_rx) = mpsc::channel::<i64>(100);

        // Send initial work items
        for item in work_items.clone() {
            tx.send(item).await.unwrap();
        }
        drop(tx);

        // Spawn workers
        let worker_count = 4;
        let mut workers = vec![];

        for worker_id in 0..worker_count {
            let mut rx = rx.clone();
            let result_tx = result_tx.clone();

            let worker = task::spawn(async move {
                let mut processed = 0;
                while let Some(item) = rx.recv().await {
                    tokio::time::sleep(Duration::from_millis(10)).await;
                    let result = item * 2;
                    result_tx.send(result).await.unwrap();
                    processed += 1;
                }
                (worker_id, processed)
            });
            workers.push(worker);
        }

        drop(result_tx);

        // Collect results
        let mut results = vec![];
        while let Some(result) = result_rx.recv().await {
            results.push(result);
        }

        // Wait for workers
        let worker_stats = join_all(workers)
            .await
            .into_iter()
            .map(|r| r.unwrap())
            .collect::<Vec<_>>();

        Ok(Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("results", results)?;
            dict.set_item("worker_stats", worker_stats)?;
            Ok(dict.into())
        }))
    })
}

/// Semaphore-based concurrency limiting
#[pyfunction]
fn limited_concurrency(py: Python, task_count: usize, max_concurrent: usize) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        use tokio::sync::Semaphore;
        use std::sync::Arc;

        let semaphore = Arc::new(Semaphore::new(max_concurrent));
        let mut handles = vec![];

        for i in 0..task_count {
            let permit = semaphore.clone();
            let handle = task::spawn(async move {
                let _permit = permit.acquire().await.unwrap();
                tokio::time::sleep(Duration::from_millis(100)).await;
                format!("Task {} done", i)
            });
            handles.push(handle);
        }

        let results = join_all(handles)
            .await
            .into_iter()
            .map(|r| r.unwrap())
            .collect::<Vec<_>>();

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}

#[pymodule]
fn concurrent_tasks(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parallel_execute, m)?)?;
    m.add_function(wrap_pyfunction!(race_tasks, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_with_errors, m)?)?;
    m.add_function(wrap_pyfunction!(work_stealing, m)?)?;
    m.add_function(wrap_pyfunction!(limited_concurrency, m)?)?;
    Ok(())
}
