# Example 01: Basic Types

This example demonstrates fundamental type conversions between Python and Rust using PyO3.

## What You'll Learn

- Converting Python integers to Rust (i32, i64, u32, u64)
- Working with floating-point numbers (f32, f64)
- String conversions (String, &str)
- Boolean operations
- Optional values (None/Option<T>)
- Error handling for type validation
- Overflow detection

## Building

```bash
# Install maturin if needed
pip install maturin

# Build and install the module
maturin develop

# Or build a wheel
maturin build --release
```

## Running Tests

```bash
# Install pytest
pip install pytest

# Run tests
pytest test_example.py -v
```

## Usage Examples

```python
import basic_types

# Integer operations
print(basic_types.double_integer(21))  # 42

# Float operations
print(basic_types.square_float(4.0))  # 16.0

# String operations
print(basic_types.greet("World"))  # "Hello, World!"

# Boolean operations
print(basic_types.negate_bool(True))  # False

# Optional values
print(basic_types.optional_double(5))     # 10
print(basic_types.optional_double(None))  # None

# Multiple parameters
info = basic_types.format_info("Alice", 30, 95.5, True)
print(info)  # "Name: Alice, Age: 30, Score: 95.50, Active: true"

# Validation with error handling
try:
    basic_types.validate_positive(-5)
except ValueError as e:
    print(f"Error: {e}")
```

## Key Concepts

### Type Conversions

PyO3 automatically converts between Python and Rust types:

- `int` ↔ `i32`, `i64`, `u32`, `u64`, `isize`, `usize`
- `float` ↔ `f32`, `f64`
- `str` ↔ `String`, `&str`
- `bool` ↔ `bool`
- `None` ↔ `Option<T>`

### Error Handling

Rust functions return `PyResult<T>` which maps to Python exceptions:

```rust
fn validate_positive(x: i64) -> PyResult<i64> {
    if x <= 0 {
        return Err(PyValueError::new_err("Value must be positive"));
    }
    Ok(x)
}
```

### Overflow Detection

The example demonstrates safe integer operations:

```rust
x.checked_add(1)
    .ok_or_else(|| PyOverflowError::new_err("Overflow detected"))
```

## Performance Notes

- String conversions involve copying data between Python and Rust
- Small integers and floats are passed by value (efficient)
- For large data, consider zero-copy approaches (see advanced examples)

## Next Steps

- **02_collections**: Working with lists, dicts, tuples, and sets
- **03_simple_class**: Creating Python classes in Rust
- **04_type_validation**: Custom type validators and converters
