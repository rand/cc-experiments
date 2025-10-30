# Example 04: Type Validation

Custom type validators and converters using the newtype pattern.

## What You'll Learn

- Newtype pattern for compile-time validation
- Input sanitization and normalization
- Range validation
- Format validation (email, URL, phone, etc.)
- Custom error messages
- Type-safe APIs

## Building

```bash
maturin develop
```

## Usage

```python
import type_validation as tv

# Email validation
email = tv.Email("user@example.com")

# Positive integers
count = tv.PositiveInt(10)

# Bounded values
age = tv.BoundedInt(25, 0, 150)

# Percentages
score = tv.Percentage(95.5)

# Non-empty strings
name = tv.NonEmptyString("Alice")

# Type-safe functions
tv.send_email(email, name)
tv.calculate_grade(score)
```

## Key Concepts

### Newtype Pattern
Wrap primitive types to add validation:

```rust
#[pyclass]
struct Email {
    address: String,
}
```

### Validation in Constructor
Enforce invariants at creation:

```rust
#[new]
fn new(value: i64) -> PyResult<Self> {
    if value <= 0 {
        return Err(PyValueError::new_err("Must be positive"));
    }
    Ok(PositiveInt { value })
}
```

### Type-Safe APIs
Functions accept only validated types:

```rust
fn send_email(email: Email, message: NonEmptyString) -> PyResult<String>
```

## Next Steps

- **05_complex_types**: Option, Result, nested structures
- **06_class_inheritance**: Inheritance patterns
