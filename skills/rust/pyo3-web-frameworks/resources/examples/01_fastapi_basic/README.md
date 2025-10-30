# Example 01: FastAPI Basic

This example demonstrates basic integration of PyO3 with FastAPI for high-performance API endpoints.

## What You'll Learn

- Creating Rust functions for CPU-intensive operations
- Exposing Rust functions to FastAPI endpoints
- Type conversions between Python and Rust
- Error handling in web context
- Performance benefits of Rust for compute-heavy endpoints
- Testing FastAPI endpoints with Rust backend

## Building

```bash
# Install maturin and dependencies
pip install maturin fastapi uvicorn httpx pytest

# Build and install the module
maturin develop

# Or build a wheel
maturin build --release
```

## Running Tests

```bash
# Install test dependencies
pip install pytest fastapi httpx

# Run tests
pytest test_example.py -v
```

## Usage Example

Create a FastAPI application using the Rust functions:

```python
# app.py
from fastapi import FastAPI, HTTPException
import fastapi_basic

app = FastAPI(title="Rust-Powered API")

@app.post("/compute/magnitude")
async def compute_magnitude(data: list[float]):
    """Compute vector magnitude using Rust."""
    try:
        result = fastapi_basic.compute_magnitude(data)
        return {"magnitude": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/compute/stats")
async def compute_stats(data: list[float]):
    """Compute statistics using Rust."""
    try:
        mean, std_dev, min_val, max_val = fastapi_basic.compute_stats(data)
        return {
            "mean": mean,
            "std_dev": std_dev,
            "min": min_val,
            "max": max_val
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/process/batch")
async def process_batch(numbers: list[float], threshold: float):
    """Process batch of numbers with filtering."""
    filtered, sum_val, count = fastapi_basic.process_batch(numbers, threshold)
    return {
        "filtered": filtered,
        "sum": sum_val,
        "count": count
    }

@app.get("/validate/user/{user_id}")
async def validate_user(user_id: str):
    """Validate user ID format."""
    is_valid = fastapi_basic.validate_user_id(user_id)
    return {"user_id": user_id, "valid": is_valid}

@app.get("/prime/{n}")
async def check_prime(n: int):
    """Check if number is prime."""
    result = fastapi_basic.is_prime(n)
    return {"number": n, "is_prime": result}
```

Run the application:

```bash
uvicorn app:app --reload
```

Test the endpoints:

```bash
# Compute magnitude
curl -X POST "http://localhost:8000/compute/magnitude" \
  -H "Content-Type: application/json" \
  -d '{"data": [3.0, 4.0]}'

# Compute statistics
curl -X POST "http://localhost:8000/compute/stats" \
  -H "Content-Type: application/json" \
  -d '{"data": [1.0, 2.0, 3.0, 4.0, 5.0]}'

# Check prime
curl "http://localhost:8000/prime/17"
```

## Key Concepts

### CPU-Intensive Operations

Functions like `compute_magnitude`, `compute_stats`, and `is_prime` benefit from Rust's performance:

```rust
#[pyfunction]
fn compute_stats(data: Vec<f64>) -> PyResult<(f64, f64, f64, f64)> {
    // Fast computation in Rust
    let sum: f64 = data.iter().sum();
    let mean = sum / data.len() as f64;
    // ... more calculations
    Ok((mean, std_dev, min, max))
}
```

### Error Handling

Rust errors are converted to Python exceptions automatically:

```rust
if data.is_empty() {
    return Err(PyValueError::new_err("Data cannot be empty"));
}
```

### Type Safety

PyO3 provides type-safe conversions between Python and Rust:

```python
# Python: list[float] -> Rust: Vec<f64>
result = fastapi_basic.compute_magnitude([3.0, 4.0])
```

## Performance Benefits

For compute-intensive operations, Rust provides significant speedup:

- **Vector operations**: 10-100x faster than pure Python
- **Statistical computations**: 20-50x faster
- **String processing**: 5-20x faster
- **Prime checking**: 50-100x faster for large numbers

## Best Practices

1. **Offload compute-heavy work**: Use Rust for CPU-intensive operations
2. **Keep interfaces simple**: Use basic types (Vec, String, f64) for easier integration
3. **Validate early**: Check inputs in Rust before processing
4. **Return rich data**: Use tuples or structs for complex results
5. **Handle errors properly**: Convert Rust errors to appropriate HTTP status codes

## Next Steps

- **02_fastapi_async**: Learn async request handlers with Tokio
- **03_pydantic_integration**: Integrate with Pydantic models
- **08_jwt_auth**: Add authentication to your API
- **10_production_api**: Build a complete production-ready API
