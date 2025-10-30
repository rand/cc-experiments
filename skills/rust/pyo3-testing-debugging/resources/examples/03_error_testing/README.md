# Example 03: Testing Error Handling and Exceptions

Comprehensive error handling and exception testing patterns for PyO3 extensions.

## What You'll Learn

- Testing Rust error handling with PyResult
- Converting Rust errors to Python exceptions
- Testing exception types and messages
- Custom exception classes
- Error propagation testing

## Project Structure

```
03_error_testing/
├── src/
│   └── lib.rs          # Error handling implementation
├── tests/
│   ├── test_errors.py  # Python exception tests
│   └── test_validation.py  # Input validation tests
├── Cargo.toml
├── pyproject.toml
└── README.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install maturin pytest
maturin develop
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with exception details
pytest tests/ -v --tb=short

# Run specific error tests
pytest tests/test_errors.py -v
```

## Key Concepts

### 1. PyResult Error Handling

```rust
#[pyfunction]
fn divide(a: f64, b: f64) -> PyResult<f64> {
    if b == 0.0 {
        Err(PyValueError::new_err("Division by zero"))
    } else {
        Ok(a / b)
    }
}
```

### 2. Testing Exceptions in Python

```python
def test_division_by_zero():
    with pytest.raises(ValueError, match="Division by zero"):
        divide(10.0, 0.0)
```

### 3. Custom Exception Classes

```rust
use pyo3::create_exception;

create_exception!(module, ValidationError, PyException);

#[pyfunction]
fn validate_age(age: i32) -> PyResult<()> {
    if age < 0 {
        Err(ValidationError::new_err("Age cannot be negative"))
    } else {
        Ok(())
    }
}
```

## Expected Output

```
tests/test_errors.py::test_division_by_zero PASSED           [ 11%]
tests/test_errors.py::test_negative_age PASSED               [ 22%]
tests/test_errors.py::test_invalid_email PASSED              [ 33%]
tests/test_errors.py::test_range_error PASSED                [ 44%]
tests/test_validation.py::test_validate_positive PASSED      [ 55%]
tests/test_validation.py::test_validate_range PASSED         [ 66%]
tests/test_validation.py::test_validate_email PASSED         [ 77%]
tests/test_validation.py::test_error_propagation PASSED      [ 88%]
tests/test_validation.py::test_multiple_errors PASSED        [100%]

========== 9 passed in 0.31s ==========
```

## Next Steps

- Move to example 04 for property-based testing
- Learn about testing error recovery
- Explore error context and backtraces
