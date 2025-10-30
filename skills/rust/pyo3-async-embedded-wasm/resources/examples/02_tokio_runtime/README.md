# Example 02: Tokio Runtime Integration

This example demonstrates advanced Tokio runtime patterns with PyO3, including task spawning, shared state, timeouts, and channels.

## Concepts Covered

- Multi-threaded Tokio runtime configuration
- Spawning background tasks
- Concurrent task execution with `join_all`
- Shared state with `Arc<Mutex>`
- Timeout handling
- Channel-based communication between tasks

## Code Structure

- `src/lib.rs`: Advanced Tokio patterns
  - `spawn_background_task`: Independent background tasks
  - `concurrent_tasks`: Parallel task execution
  - `shared_counter_demo`: Thread-safe shared state
  - `with_timeout`: Timeout enforcement
  - `channel_demo`: Producer-consumer pattern

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

### Global Runtime Initialization

```rust
use tokio::runtime::Runtime;
use once_cell::sync::OnceCell;

static RUNTIME: OnceCell<Runtime> = OnceCell::new();

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
```

Key points:
- Initialize runtime once using `OnceCell`
- Configure multi-threaded runtime for parallel execution
- Enable all Tokio features (timers, I/O, etc.)

### Spawning Background Tasks

```rust
#[pyfunction]
fn spawn_background_task(py: Python, count: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let handle = task::spawn(async move {
            for i in 0..count {
                tokio::time::sleep(Duration::from_millis(100)).await;
                println!("Background iteration: {}", i);
            }
        });
        Ok(Python::with_gil(|py| "Spawned".into_py(py)))
    })
}
```

### Shared State

```rust
let counter = Arc::new(Mutex::new(0u64));
let mut handles = vec![];

for _ in 0..increments {
    let counter_clone = Arc::clone(&counter);
    let handle = task::spawn(async move {
        let mut count = counter_clone.lock().await;
        *count += 1;
    });
    handles.push(handle);
}

for handle in handles {
    handle.await.unwrap();
}

let final_count = *counter.lock().await;
```

Key points:
- Use `Arc<Mutex<T>>` for thread-safe shared state
- Clone Arc for each task
- Await mutex lock (non-blocking)
- Wait for all tasks to complete

### Timeout Pattern

```rust
match tokio::time::timeout(Duration::from_millis(timeout_ms), operation).await {
    Ok(result) => Ok(result),
    Err(_) => Err(PyErr::new::<PyTimeoutError, _>("Timed out")),
}
```

### Channel Communication

```rust
let (tx, mut rx) = tokio::sync::mpsc::channel::<String>(32);

// Producer
let producer = task::spawn(async move {
    for i in 0..count {
        tx.send(format!("Message {}", i)).await.ok();
    }
});

// Consumer
let consumer = task::spawn(async move {
    let mut messages = Vec::new();
    while let Some(msg) = rx.recv().await {
        messages.push(msg);
    }
    messages
});

producer.await.unwrap();
let messages = consumer.await.unwrap();
```

## Python Usage

```python
import asyncio
import tokio_runtime

async def main():
    # Spawn background task
    await tokio_runtime.spawn_background_task(10, 100)

    # Run tasks concurrently
    urls = ["url1", "url2", "url3"]
    results = await tokio_runtime.concurrent_tasks(urls)

    # Shared counter
    count = await tokio_runtime.shared_counter_demo(100)

    # With timeout
    try:
        result = await tokio_runtime.with_timeout(100, 50)
    except TimeoutError:
        print("Operation timed out")

    # Channel demo
    messages = await tokio_runtime.channel_demo(10)

asyncio.run(main())
```

## Performance Considerations

- Multi-threaded runtime enables true parallelism
- Shared state requires synchronization (mutex overhead)
- Channels are bounded to prevent memory issues
- Timeouts prevent hanging operations

## Learning Objectives

After completing this example, you should understand:

1. How to configure and manage a Tokio runtime
2. How to spawn background tasks that run independently
3. How to share state safely between async tasks
4. How to implement timeouts and cancellation
5. How to use channels for task communication

## Next Steps

- **Example 03**: Learn about embedding Python in Rust applications
- **Example 04**: Explore async streams and backpressure
