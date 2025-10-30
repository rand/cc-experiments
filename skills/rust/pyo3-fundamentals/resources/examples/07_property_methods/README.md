# Example 07: Property Methods

Demonstrates custom properties with getters and setters using PyO3.

## What You'll Learn

- Custom getters with `#[getter]`
- Custom setters with `#[setter]`
- Computed properties (read-only)
- Validated setters
- Property conversions (Celsius/Fahrenheit)

## Building

```bash
maturin develop
```

## Usage

```python
import property_methods as pm

# Temperature with automatic conversion
temp = pm.Temperature(0.0)
print(temp.celsius)     # 0.0
print(temp.fahrenheit)  # 32.0
temp.fahrenheit = 212.0
print(temp.celsius)     # 100.0

# Validated account
acc = pm.ValidatedAccount(1000.0, 100.0)
print(acc.available_balance)  # 900.0

# Computed properties
person = pm.PersonWithName("John", "Doe")
print(person.full_name)  # "John Doe"
print(person.initials)   # "JD"
```

## Key Concepts

### Custom Getters
```rust
#[getter]
fn fahrenheit(&self) -> f64 {
    self.celsius * 9.0 / 5.0 + 32.0
}
```

### Custom Setters with Validation
```rust
#[setter]
fn set_balance(&mut self, value: f64) -> PyResult<()> {
    if value < self.min_balance {
        return Err(PyValueError::new_err("Below minimum"));
    }
    self.balance = value;
    Ok(())
}
```

### Computed Properties
Read-only properties calculated on demand:
```rust
#[getter]
fn area(&self) -> f64 {
    self.width * self.height
}
```

## Next Steps
- **08_custom_converters**: Advanced FromPyObject implementations
- **09_generic_types**: Generic-like behavior
