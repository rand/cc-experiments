# Example 04: Async Streams

This example demonstrates async stream processing with PyO3, including transformations, backpressure, chunking, and rate limiting.

## Concepts Covered

- Creating async streams from iterators
- Stream transformations (map, filter, fold)
- Backpressure handling with bounded channels
- Stream chunking for batch processing
- Merging multiple streams
- Error handling in streams
- Rate limiting

## Code Structure

- `src/lib.rs`: Async stream operations
  - `async_range`: Basic stream generation
  - `async_map`: Transform stream elements
  - `async_filter`: Filter stream elements
  - `async_delayed_stream`: Streams with delays
  - `async_backpressure`: Demonstrate backpressure
  - `async_chunks`: Batch processing
  - `async_fold`: Accumulation
  - `async_merge_streams`: Combine streams
  - `async_stream_errors`: Error handling
  - `async_rate_limited`: Rate limiting

## Building

```bash
maturin develop
```

## Running

```bash
pytest test_example.py
python test_example.py
```

## Key Patterns

### Basic Stream

```rust
use futures::stream::{self, StreamExt};

#[pyfunction]
fn async_range(py: Python, start: i64, end: i64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let stream = stream::iter(start..end);
        let results: Vec<_> = stream.collect().await;
        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}
```

### Stream Transformation

```rust
#[pyfunction]
fn async_map(py: Python, data: Vec<i64>, multiplier: i64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let stream = stream::iter(data);
        let results: Vec<_> = stream
            .map(|x| x * multiplier)
            .collect()
            .await;
        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}
```

### Backpressure with Channels

```rust
use tokio::sync::mpsc;

#[pyfunction]
fn async_backpressure(
    py: Python,
    data: Vec<i64>,
    buffer_size: usize,
) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let (tx, mut rx) = mpsc::channel(buffer_size);

        // Fast producer
        let producer = tokio::spawn(async move {
            for item in data {
                // Blocks when buffer is full (backpressure)
                tx.send(item).await.unwrap();
            }
        });

        // Slow consumer
        let consumer = tokio::spawn(async move {
            let mut results = Vec::new();
            while let Some(item) = rx.recv().await {
                tokio::time::sleep(Duration::from_millis(10)).await;
                results.push(item);
            }
            results
        });

        producer.await.unwrap();
        consumer.await.unwrap()
    })
}
```

Key points:
- Bounded channel enforces backpressure
- Producer blocks when buffer is full
- Consumer processes at its own pace
- Prevents memory overflow from fast producers

### Stream Chunking

```rust
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
```

Use cases:
- Batch processing
- Database bulk inserts
- Network request batching
- Memory management for large datasets

### Stream Folding

```rust
#[pyfunction]
fn async_fold(py: Python, data: Vec<i64>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let stream = stream::iter(data);
        let sum = stream
            .fold(0i64, |acc, x| async move { acc + x })
            .await;
        Ok(Python::with_gil(|py| sum.into_py(py)))
    })
}
```

### Merging Streams

```rust
use futures::stream::select;

#[pyfunction]
fn async_merge_streams(
    py: Python,
    stream1: Vec<i64>,
    stream2: Vec<i64>,
) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let s1 = stream::iter(stream1);
        let s2 = stream::iter(stream2);
        let merged = select(s1, s2);
        let results: Vec<_> = merged.collect().await;
        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}
```

### Error Handling

```rust
#[pyfunction]
fn async_stream_errors(
    py: Python,
    data: Vec<i64>,
    fail_on: i64,
) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let stream = stream::iter(data);

        let results = stream
            .then(|x| async move {
                if x == fail_on {
                    Err(format!("Failed on: {}", x))
                } else {
                    Ok(x * 2)
                }
            })
            .collect::<Vec<_>>()
            .await;

        // Convert to Python
        Python::with_gil(|py| {
            let py_results = results
                .into_iter()
                .map(|r| match r {
                    Ok(val) => Ok(val.into_py(py)),
                    Err(e) => Err(PyErr::new::<PyRuntimeError, _>(e)),
                })
                .collect::<Result<Vec<_>, _>>()?;
            Ok(py_results.into_py(py))
        })
    })
}
```

### Rate Limiting

```rust
#[pyfunction]
fn async_rate_limited(
    py: Python,
    count: usize,
    rate_per_sec: u64,
) -> PyResult<&PyAny> {
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
```

## Python Usage

```python
import asyncio
import async_streams

async def main():
    # Basic range
    result = await async_streams.async_range(0, 10)

    # Map transformation
    result = await async_streams.async_map([1, 2, 3], 2)

    # Filter
    result = await async_streams.async_filter([1, 2, 3, 4, 5], 3)

    # Backpressure handling
    data = list(range(100))
    result = await async_streams.async_backpressure(data, 10, 5)

    # Chunking
    result = await async_streams.async_chunks(list(range(10)), 3)

    # Rate limiting
    result = await async_streams.async_rate_limited(10, 5)

asyncio.run(main())
```

## Performance Considerations

- **Backpressure**: Use bounded channels to prevent memory issues
- **Chunking**: Reduces overhead for batch operations
- **Rate Limiting**: Prevents overwhelming downstream systems
- **Error Handling**: Don't let errors stop the entire stream

## Use Cases

### Data Processing Pipeline

```python
# Process large dataset in chunks
async def process_large_file():
    data = load_large_dataset()
    chunks = await async_streams.async_chunks(data, 1000)
    for chunk in chunks:
        await process_chunk(chunk)
```

### API Rate Limiting

```python
# Respect API rate limits
async def fetch_many_urls():
    urls = get_url_list()
    results = await async_streams.async_rate_limited(
        len(urls),
        rate_per_sec=10
    )
```

## Learning Objectives

After completing this example, you should understand:

1. How to create and transform async streams
2. How to handle backpressure with bounded channels
3. How to chunk streams for batch processing
4. How to merge multiple streams
5. How to handle errors in stream processing
6. How to implement rate limiting

## Next Steps

- **Example 05**: Learn about concurrent task management
- **Example 06**: Build a complete plugin system
