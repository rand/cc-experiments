# Example 05: Complex Types

Demonstrates Option, Result, nested structures, and complex data transformations.

## Building
```bash
maturin develop
```

## Key Features
- Option<T> for nullable values
- Result-like OperationResult pattern
- Nested structures (User with Address)
- Collections of optional values
- Data aggregation and transformation

## Usage
```python
import complex_types as ct

# Safe operations
result = ct.safe_divide(10, 2)
if result.success:
    print(result.value)

# Optional values
email = ct.parse_int("42")  # Returns Some or None

# Nested structures
addr = ct.Address("123 Main", "NYC", "10001", "USA")
user = ct.User(1, "Alice", "alice@test.com", 30, addr)
```

## Next Steps
- **06_class_inheritance**: Inheritance patterns
- **07_property_methods**: Custom properties
