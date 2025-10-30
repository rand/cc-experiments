# Example 05: Custom Exception Types

This example demonstrates creating custom Python exception classes in Rust.

## What You'll Learn

- Creating custom exceptions with `create_exception!` macro
- Building exception hierarchies
- Adding attributes to exception classes
- Using custom exceptions in functions

## Building and Running

```bash
maturin develop
pytest test_example.py -v
```

## Key Concepts

### 1. Creating Custom Exceptions

```rust
use pyo3::create_exception;

create_exception!(module_name, ExceptionName, BaseException, "Docstring");
```

### 2. Exception Hierarchies

```rust
// Base exception
create_exception!(mymod, ValidationError, PyException);

// Derived exceptions
create_exception!(mymod, RangeError, ValidationError);
create_exception!(mymod, FormatError, ValidationError);
```

### 3. Exception with Attributes

```rust
#[pyclass(extends=PyException)]
struct DetailedError {
    #[pyo3(get)]
    code: i32,
    #[pyo3(get)]
    context: String,
}
```

## Usage in Python

```python
import custom_exceptions as ce

# Catch specific exception
try:
    ce.validate_range(100, 0, 10)
except ce.RangeError as e:
    print(f"Range error: {e}")

# Catch base exception
try:
    ce.validate_email("invalid")
except ce.ValidationError as e:
    print(f"Validation error: {e}")

# Access exception attributes
try:
    ce.raise_detailed_error("Error", 500, "Context")
except ce.DetailedError as e:
    print(f"Code: {e.code}, Context: {e.context}")
```

## Next Steps

- **Example 06**: Function overloading patterns
- **Example 09**: Complete error hierarchy with context
