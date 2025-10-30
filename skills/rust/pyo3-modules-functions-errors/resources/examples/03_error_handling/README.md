# Example 03: Error Handling and Exceptions

This example demonstrates comprehensive error handling in PyO3, showing how to create and raise Python exceptions from Rust code.

## What You'll Learn

- Returning `PyResult<T>` for fallible operations
- Using standard Python exception types
- Creating descriptive error messages with context
- Chaining operations with the `?` operator
- Type checking and validation
- Error propagation patterns

## Building and Running

```bash
maturin develop
pytest test_example.py -v
```

## Key Concepts

### 1. PyResult<T> Return Type

Functions that can fail should return `PyResult<T>`:

```rust
#[pyfunction]
fn divide(a: f64, b: f64) -> PyResult<f64> {
    if b == 0.0 {
        Err(PyZeroDivisionError::new_err("Cannot divide by zero"))
    } else {
        Ok(a / b)
    }
}
```

```python
divide(10.0, 2.0)  # Returns 5.0
divide(10.0, 0.0)  # Raises ZeroDivisionError
```

### 2. Standard Python Exceptions

PyO3 provides Rust types for all standard Python exceptions:

```rust
use pyo3::exceptions::{
    PyValueError,           // Invalid value
    PyTypeError,            // Wrong type
    PyZeroDivisionError,    // Division by zero
    PyIndexError,           // Index out of bounds
    PyKeyError,             // Key not found
    PyRuntimeError,         // Runtime condition
    PyIOError,              // I/O operation failed
    PyOSError,              // OS error
    // ... and more
};
```

### 3. Creating Error Messages

Use `new_err()` to create exceptions with messages:

```rust
// Simple message
Err(PyValueError::new_err("Age cannot be negative"))

// Formatted message with context
Err(PyValueError::new_err(format!(
    "String too short: expected at least {} characters, got {}",
    min_length, actual_length
)))
```

### 4. Error Propagation with ?

Use the `?` operator to propagate errors:

```rust
#[pyfunction]
fn parse_and_divide(a: &str, b: &str) -> PyResult<f64> {
    // Parse first number, propagate error if it fails
    let num_a = a.parse::<f64>()
        .map_err(|_| PyValueError::new_err(format!("Cannot parse '{}'", a)))?;

    // Parse second number
    let num_b = b.parse::<f64>()
        .map_err(|_| PyValueError::new_err(format!("Cannot parse '{}'", b)))?;

    // Check for zero
    if num_b == 0.0 {
        return Err(PyZeroDivisionError::new_err("Cannot divide by zero"));
    }

    Ok(num_a / num_b)
}
```

### 5. Converting Rust Errors

Convert Rust errors to Python exceptions using `map_err`:

```rust
// Convert parse error
s.parse::<i64>()
    .map_err(|e| PyValueError::new_err(format!("Invalid integer: {}", e)))

// Or use a closure for more complex logic
items.get(index)
    .ok_or_else(|| PyIndexError::new_err(format!(
        "Index {} out of bounds for list of length {}",
        index, items.len()
    )))
```

### 6. Type Validation

Check types at runtime when needed:

```rust
#[pyfunction]
fn process_value(py: Python, value: &PyAny) -> PyResult<f64> {
    // Try as float
    if let Ok(f) = value.extract::<f64>() {
        return Ok(f);
    }

    // Try as string
    if let Ok(s) = value.extract::<String>() {
        return s.parse::<f64>()
            .map_err(|_| PyTypeError::new_err(format!("Cannot convert '{}'", s)));
    }

    // Not supported
    Err(PyTypeError::new_err(format!(
        "Expected float or string, got {}",
        value.get_type().name()?
    )))
}
```

## Exception Types Guide

### ValueError
Use for invalid values that have the right type but wrong content:
```rust
if age < 0 {
    return Err(PyValueError::new_err("Age cannot be negative"));
}
```

### TypeError
Use for wrong types or type mismatches:
```rust
Err(PyTypeError::new_err("Expected string, got int"))
```

### ZeroDivisionError
Use for division by zero:
```rust
if denominator == 0 {
    return Err(PyZeroDivisionError::new_err("Cannot divide by zero"));
}
```

### IndexError
Use for out-of-bounds access:
```rust
if index >= items.len() {
    return Err(PyIndexError::new_err("Index out of bounds"));
}
```

### KeyError
Use for missing dictionary keys:
```rust
data.get(key)
    .ok_or_else(|| PyKeyError::new_err(format!("Key '{}' not found", key)))
```

### RuntimeError
Use for runtime conditions that don't fit other categories:
```rust
Err(PyRuntimeError::new_err("Unexpected runtime condition"))
```

## Error Message Best Practices

### 1. Be Specific
```rust
// Bad
Err(PyValueError::new_err("Invalid input"))

// Good
Err(PyValueError::new_err(format!(
    "String too short: expected at least {} characters, got {}",
    min_length, actual_length
)))
```

### 2. Include Context
```rust
// Bad
Err(PyIndexError::new_err("Index out of bounds"))

// Good
Err(PyIndexError::new_err(format!(
    "Index {} out of bounds for list of length {}",
    index, items.len()
)))
```

### 3. Show the Problematic Value
```rust
Err(PyValueError::new_err(format!(
    "Cannot parse '{}' as integer", value
)))
```

## Common Patterns

### Pattern 1: Validation Chain

```rust
#[pyfunction]
fn validate_string(value: &str, min: usize, max: usize) -> PyResult<String> {
    if min > max {
        return Err(PyValueError::new_err("Invalid range"));
    }

    let trimmed = value.trim();

    if trimmed.len() < min {
        return Err(PyValueError::new_err("String too short"));
    }

    if trimmed.len() > max {
        return Err(PyValueError::new_err("String too long"));
    }

    Ok(trimmed.to_string())
}
```

### Pattern 2: Optional Result

```rust
#[pyfunction]
fn safe_get(key: &str, data: HashMap<String, String>) -> PyResult<String> {
    data.get(key)
        .cloned()
        .ok_or_else(|| PyKeyError::new_err(format!("Key '{}' not found", key)))
}
```

### Pattern 3: Multi-Step Operation

```rust
#[pyfunction]
fn complex_operation(input: &str) -> PyResult<i64> {
    let parsed = input.parse::<i64>()
        .map_err(|e| PyValueError::new_err(format!("Parse error: {}", e)))?;

    let validated = validate(parsed)?;
    let processed = process(validated)?;

    Ok(processed)
}
```

## Performance Considerations

1. **Error creation cost**: Creating exceptions is relatively cheap
2. **Error messages**: Format strings only when error actually occurs
3. **Early returns**: Return errors as soon as detected
4. **No exception overhead**: In Rust, Result<T, E> has zero overhead

## Testing Errors in Python

```python
import pytest

def test_error_raised():
    with pytest.raises(ValueError) as exc_info:
        module.failing_function()

    # Check error message
    assert "expected message" in str(exc_info.value)
```

## Next Steps

- **Example 04**: Submodules and module organization
- **Example 05**: Custom exception types
- **Example 09**: Complete error hierarchy with context

## References

- [PyO3 Error Handling](https://pyo3.rs/latest/function.html#error-handling)
- [Python Built-in Exceptions](https://docs.python.org/3/library/exceptions.html)
- [Rust Error Handling](https://doc.rust-lang.org/book/ch09-00-error-handling.html)
