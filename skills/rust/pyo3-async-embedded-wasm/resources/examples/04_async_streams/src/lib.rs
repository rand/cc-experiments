use futures::stream::{self, StreamExt};
use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use std::time::Duration;
use tokio::sync::mpsc;
use tokio_stream::wrappers::ReceiverStream;

/// Simple stream that generates a range of numbers
#[pyfunction]
fn async_range(py: Python, start: i64, end: i64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let stream = stream::iter(start..end);

        let results: Vec<_> = stream.collect().await;

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}

/// Stream with transformation (map)
#[pyfunction]
fn async_map(py: Python, data: Vec<i64>, multiplier: i64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let stream = stream::iter(data);

        let results: Vec<_> = stream.map(|x| x * multiplier).collect().await;

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}

/// Stream with filtering
#[pyfunction]
fn async_filter(py: Python, data: Vec<i64>, min_value: i64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let stream = stream::iter(data);

        let results: Vec<_> = stream.filter(|x| {
            let x = *x;
            async move { x >= min_value }
        })
        .collect()
        .await;

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}

/// Stream with delays (simulating slow data source)
#[pyfunction]
fn async_delayed_stream(py: Python, count: usize, delay_ms: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let (tx, rx) = mpsc::channel(10);

        // Producer with delays
        tokio::spawn(async move {
            for i in 0..count {
                if tx.send(i as i64).await.is_err() {
                    break;
                }
                tokio::time::sleep(Duration::from_millis(delay_ms)).await;
            }
        });

        // Consumer
        let stream = ReceiverStream::new(rx);
        let results: Vec<_> = stream.collect().await;

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}

/// Stream with backpressure handling
#[pyfunction]
fn async_backpressure(
    py: Python,
    data: Vec<i64>,
    buffer_size: usize,
    process_delay_ms: u64,
) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let (tx, mut rx) = mpsc::channel(buffer_size);

        // Fast producer
        let producer = tokio::spawn(async move {
            for item in data {
                // This will block when buffer is full (backpressure)
                if tx.send(item).await.is_err() {
                    break;
                }
            }
        });

        // Slow consumer
        let consumer = tokio::spawn(async move {
            let mut results = Vec::new();
            while let Some(item) = rx.recv().await {
                // Simulate slow processing
                tokio::time::sleep(Duration::from_millis(process_delay_ms)).await;
                results.push(item * 2);
            }
            results
        });

        producer.await.unwrap();
        let results = consumer.await.unwrap();

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}

/// Stream chunking - process data in batches
#[pyfunction]
fn async_chunks(py: Python, data: Vec<i64>, chunk_size: usize) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let stream = stream::iter(data);

        let chunks: Vec<Vec<i64>> = stream
            .chunks(chunk_size)
            .collect()
            .await;

        Ok(Python::with_gil(|py| chunks.into_py(py)))
    })
}

/// Stream folding - accumulate values
#[pyfunction]
fn async_fold(py: Python, data: Vec<i64>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let stream = stream::iter(data);

        // Calculate sum using fold
        let sum = stream.fold(0i64, |acc, x| async move { acc + x }).await;

        Ok(Python::with_gil(|py| sum.into_py(py)))
    })
}

/// Stream merging - combine multiple streams
#[pyfunction]
fn async_merge_streams(py: Python, stream1: Vec<i64>, stream2: Vec<i64>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        use futures::stream::select;

        let s1 = stream::iter(stream1);
        let s2 = stream::iter(stream2);

        let merged = select(s1, s2);
        let results: Vec<_> = merged.collect().await;

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}

/// Stream with error handling
#[pyfunction]
fn async_stream_errors(py: Python, data: Vec<i64>, fail_on: i64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let stream = stream::iter(data);

        let results = stream
            .then(|x| async move {
                if x == fail_on {
                    Err(format!("Failed on value: {}", x))
                } else {
                    Ok(x * 2)
                }
            })
            .collect::<Vec<_>>()
            .await;

        // Convert Results to Python
        Python::with_gil(|py| {
            let py_results = results
                .into_iter()
                .map(|r| match r {
                    Ok(val) => Ok(val.into_py(py)),
                    Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e)),
                })
                .collect::<Result<Vec<_>, _>>()?;

            Ok(py_results.into_py(py))
        })
    })
}

/// Stream rate limiting
#[pyfunction]
fn async_rate_limited(py: Python, count: usize, rate_per_sec: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let delay_ms = 1000 / rate_per_sec;
        let stream = stream::iter(0..count);

        let results: Vec<_> = stream
            .then(|x| async move {
                tokio::time::sleep(Duration::from_millis(delay_ms)).await;
                x
            })
            .collect()
            .await;

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}

#[pymodule]
fn async_streams(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(async_range, m)?)?;
    m.add_function(wrap_pyfunction!(async_map, m)?)?;
    m.add_function(wrap_pyfunction!(async_filter, m)?)?;
    m.add_function(wrap_pyfunction!(async_delayed_stream, m)?)?;
    m.add_function(wrap_pyfunction!(async_backpressure, m)?)?;
    m.add_function(wrap_pyfunction!(async_chunks, m)?)?;
    m.add_function(wrap_pyfunction!(async_fold, m)?)?;
    m.add_function(wrap_pyfunction!(async_merge_streams, m)?)?;
    m.add_function(wrap_pyfunction!(async_stream_errors, m)?)?;
    m.add_function(wrap_pyfunction!(async_rate_limited, m)?)?;
    Ok(())
}
