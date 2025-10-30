# Example 02: FastAPI Async

This example demonstrates async request handlers in FastAPI using PyO3 with Tokio runtime.

## What You'll Learn

- Integrating async Rust functions with FastAPI
- Using pyo3-asyncio for async Python/Rust interop
- Tokio runtime for async operations
- Concurrent request processing
- Async error handling and timeouts
- Shared state with async locks
- Concurrency limits and retry logic

## Building

```bash
# Install dependencies
pip install maturin fastapi uvicorn pytest pytest-asyncio httpx

# Build and install
maturin develop

# Or build release
maturin build --release
```

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest test_example.py -v
```

## Usage Example

Create an async FastAPI application:

```python
# app.py
from fastapi import FastAPI, HTTPException
import fastapi_async

app = FastAPI(title="Async Rust API")

@app.get("/fetch/{id}")
async def fetch_data(id: int, delay_ms: int = 100):
    """Fetch data asynchronously from Rust."""
    result = await fastapi_async.fetch_data_async(id, delay_ms)
    return {"id": id, "data": result}

@app.post("/process/batch")
async def process_batch(items: list[str]):
    """Process batch of items concurrently."""
    results = await fastapi_async.process_batch_async(items)
    return {"results": results, "count": len(results)}

@app.post("/compute/{n}")
async def compute(n: int):
    """Compute sum with progress tracking."""
    result = await fastapi_async.compute_with_progress(n)
    return {"n": n, "sum": result}

@app.get("/api/{endpoint}")
async def api_call(endpoint: str, timeout_ms: int = 1000):
    """Make API call with timeout."""
    try:
        result = await fastapi_async.api_call_with_timeout(endpoint, timeout_ms)
        return {"endpoint": endpoint, "response": result}
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))

@app.post("/aggregate")
async def aggregate(sources: list[str]):
    """Aggregate data from multiple sources."""
    result = await fastapi_async.aggregate_async(sources)
    return {"aggregated": result}

# Global counter with async operations
counter = fastapi_async.AsyncCounter()

@app.post("/counter/increment")
async def increment_counter():
    """Increment counter asynchronously."""
    count = await counter.increment_async()
    return {"count": count}

@app.get("/counter")
async def get_counter():
    """Get current counter value."""
    count = await counter.get_count_async()
    return {"count": count}

@app.post("/counter/reset")
async def reset_counter():
    """Reset counter to zero."""
    await counter.reset_async()
    return {"message": "Counter reset"}
```

Run the application:

```bash
uvicorn app:app --reload
```

Test the endpoints:

```bash
# Fetch data
curl "http://localhost:8000/fetch/42?delay_ms=100"

# Process batch
curl -X POST "http://localhost:8000/process/batch" \
  -H "Content-Type: application/json" \
  -d '["hello", "world", "test"]'

# Increment counter
curl -X POST "http://localhost:8000/counter/increment"
```

## Key Concepts

### Async Function Integration

Use `pyo3-asyncio` to bridge Rust async and Python async:

```rust
use pyo3_asyncio::tokio::future_into_py;

#[pyfunction]
fn fetch_data_async(py: Python, id: u64, delay_ms: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        sleep(Duration::from_millis(delay_ms)).await;
        let result = format!("Data for ID {}", id);
        Python::with_gil(|py| Ok(result.into_py(py)))
    })
}
```

### Concurrent Processing

Process multiple items concurrently with Tokio:

```rust
let mut handles = vec![];
for item in items {
    let handle = tokio::spawn(async move {
        // Process item
        item.to_uppercase()
    });
    handles.push(handle);
}
```

### Shared State

Use `Arc<Mutex<T>>` for thread-safe shared state:

```rust
#[pyclass]
struct AsyncCounter {
    count: Arc<Mutex<u64>>,
}

fn increment_async(&self, py: Python) -> PyResult<&PyAny> {
    let count = self.count.clone();
    future_into_py(py, async move {
        let mut c = count.lock().await;
        *c += 1;
        // ...
    })
}
```

### Timeout Handling

Use `tokio::time::timeout` for operation timeouts:

```rust
let timeout_result = tokio::time::timeout(
    Duration::from_millis(timeout_ms),
    async {
        // Operation that might take too long
    }
).await;
```

### Concurrency Limits

Use semaphores to limit concurrent operations:

```rust
let semaphore = Arc::new(Semaphore::new(max_concurrent));
let permit = semaphore.clone().acquire_owned().await?;
// Do work with permit
drop(permit); // Release permit
```

## Performance Benefits

Async Rust with Tokio provides:

- **Non-blocking I/O**: Handle thousands of concurrent requests
- **Efficient resource usage**: Lower memory and CPU overhead
- **Backpressure control**: Limit concurrency to prevent overload
- **Timeout management**: Prevent hung requests

## Best Practices

1. **Use `future_into_py`**: Always wrap async Rust functions
2. **Acquire GIL carefully**: Use `Python::with_gil()` inside async blocks
3. **Clone Arc wisely**: Clone Arc references before moving into async blocks
4. **Limit concurrency**: Use semaphores to control concurrent operations
5. **Handle timeouts**: Always set reasonable timeouts for I/O operations
6. **Test async code**: Use pytest-asyncio for comprehensive async tests

## Common Patterns

### Retry with Backoff

```python
@app.get("/retry/{url}")
async def fetch_with_retry(url: str, max_retries: int = 3):
    result = await fastapi_async.fetch_with_retry(url, max_retries)
    return {"url": url, "result": result}
```

### Batch Processing

```python
@app.post("/batch")
async def process_large_batch(items: list[float], max_concurrent: int = 10):
    results = await fastapi_async.process_with_concurrency(items, max_concurrent)
    return {"processed": len(results), "results": results}
```

## Next Steps

- **03_pydantic_integration**: Validate async requests with Pydantic
- **07_websocket_basic**: Handle WebSocket connections asynchronously
- **09_caching_layer**: Add async caching layer
- **10_production_api**: Build complete async production API
