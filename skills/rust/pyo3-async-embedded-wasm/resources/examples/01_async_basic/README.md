# Example 01: Basic Async Functions

This example demonstrates the fundamentals of creating async Python functions using PyO3 and pyo3-asyncio.

## Concepts Covered

- Converting Rust futures to Python coroutines with `future_into_py`
- Basic async/await patterns
- GIL management in async contexts
- Error handling in async functions
- Testing async Python extensions

## Code Structure

- `src/lib.rs`: Four basic async functions demonstrating different patterns
  - `async_sleep`: Simple async delay
  - `async_compute`: Async computation
  - `async_greet`: Async string formatting
  - `async_divide`: Error handling in async context

## Building

```bash
# Install maturin if you haven't already
pip install maturin

# Build and install in development mode
maturin develop

# Or build a wheel
maturin build --release
```

## Running

```bash
# Run the test suite
pytest test_example.py

# Run the standalone example
python test_example.py
```

## Key Patterns

### Basic Async Function

```rust
#[pyfunction]
fn async_sleep(py: Python, seconds: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        tokio::time::sleep(Duration::from_secs(seconds)).await;
        Ok(Python::with_gil(|py| "Sleep completed".into_py(py)))
    })
}
```

Key points:
- Use `future_into_py` to convert Rust futures to Python coroutines
- Use `async move` to capture variables
- Acquire GIL with `Python::with_gil()` before returning Python objects
- Return type is `PyResult<&PyAny>` (Python awaitable)

### Error Handling

```rust
#[pyfunction]
fn async_divide(py: Python, a: f64, b: f64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        if b == 0.0 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Cannot divide by zero"
            ));
        }
        let result = a / b;
        Ok(Python::with_gil(|py| result.into_py(py)))
    })
}
```

### Python Usage

```python
import asyncio
import async_basic

async def main():
    # Call async functions
    result = await async_basic.async_compute(100)
    print(f"Sum: {result}")

    # Concurrent execution
    results = await asyncio.gather(
        async_basic.async_greet("Alice"),
        async_basic.async_greet("Bob"),
    )

asyncio.run(main())
```

## Learning Objectives

After completing this example, you should understand:

1. How to create basic async Python functions in Rust
2. How to use `future_into_py` to bridge Rust and Python async
3. How to manage the GIL in async contexts
4. How to handle errors in async functions
5. How to test async PyO3 extensions

## Next Steps

- **Example 02**: Learn about Tokio runtime integration
- **Example 03**: Explore embedding Python in Rust applications
