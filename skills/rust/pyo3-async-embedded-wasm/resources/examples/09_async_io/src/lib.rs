use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use std::path::PathBuf;
use tokio::fs;
use tokio::io::{AsyncReadExt, AsyncWriteExt};

/// Async file reading
#[pyfunction]
fn async_read_file(py: Python, path: String) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let contents = fs::read_to_string(path)
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        Ok(Python::with_gil(|py| contents.into_py(py)))
    })
}

/// Async file writing
#[pyfunction]
fn async_write_file(py: Python, path: String, contents: String) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        fs::write(&path, &contents)
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        Ok(Python::with_gil(|py| {
            format!("Wrote {} bytes to {}", contents.len(), path).into_py(py)
        }))
    })
}

/// Async HTTP request
#[pyfunction]
fn async_http_get(py: Python, url: String) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let response = reqwest::get(&url)
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        let status = response.status().as_u16();
        let body = response
            .text()
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("status", status)?;
            dict.set_item("body", body)?;
            Ok(dict.into())
        })
    })
}

/// Batch file operations
#[pyfunction]
fn async_read_many(py: Python, paths: Vec<String>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let futures = paths.into_iter().map(|path| async move {
            match fs::read_to_string(&path).await {
                Ok(contents) => (path, Ok(contents)),
                Err(e) => (path, Err(e.to_string())),
            }
        });

        let results = futures::future::join_all(futures).await;

        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);
            for (path, result) in results {
                match result {
                    Ok(contents) => dict.set_item(path, contents)?,
                    Err(e) => dict.set_item(path, format!("Error: {}", e))?,
                }
            }
            Ok(dict.into())
        })
    })
}

/// Directory listing
#[pyfunction]
fn async_list_dir(py: Python, path: String) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let mut entries = vec![];
        let mut dir = fs::read_dir(path)
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        while let Some(entry) = dir
            .next_entry()
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?
        {
            if let Some(name) = entry.file_name().to_str() {
                entries.push(name.to_string());
            }
        }

        Ok(Python::with_gil(|py| entries.into_py(py)))
    })
}

#[pymodule]
fn async_io(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(async_read_file, m)?)?;
    m.add_function(wrap_pyfunction!(async_write_file, m)?)?;
    m.add_function(wrap_pyfunction!(async_http_get, m)?)?;
    m.add_function(wrap_pyfunction!(async_read_many, m)?)?;
    m.add_function(wrap_pyfunction!(async_list_dir, m)?)?;
    Ok(())
}
