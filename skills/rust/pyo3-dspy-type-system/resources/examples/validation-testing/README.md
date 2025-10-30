# Type Validation and Testing Example

This example demonstrates comprehensive type validation and testing strategies for PyO3-DSpy type conversions. It serves as a reference for ensuring type safety across the Rust-Python boundary.

## Overview

This project showcases:
- **Round-trip testing**: Verify that Rust → Python → Rust conversions preserve data
- **Edge case handling**: Test empty collections, None/null values, Unicode, special floats
- **Type validation**: Use `type_validator.py` to ensure Python types match expectations
- **Property-based testing concepts**: Ideas for generative testing
- **Integration testing**: Comprehensive test coverage for all type combinations

## Project Structure

```
validation-testing/
├── Cargo.toml                    # Project dependencies
├── README.md                     # This file
├── src/
│   ├── main.rs                  # Validation examples and demonstrations
│   └── types.rs                 # Type definitions for testing
└── tests/
    └── integration_test.rs      # Round-trip integration tests
```

## Building and Running

```bash
# Build the project
cargo build

# Run validation examples
cargo run

# Run all tests
cargo test

# Run tests with output
cargo test -- --nocapture

# Run specific test
cargo test test_primitive_roundtrip -- --nocapture
```

## Type Coverage

### Primitive Types
- Integers: `i32`, `i64`, `u32`, `u64`
- Floats: `f32`, `f64` (including NaN, infinity)
- Booleans: `bool`
- Strings: `String` (including Unicode)

### Collection Types
- Vectors: `Vec<T>`
- HashMaps: `HashMap<K, V>`
- Tuples: `(T1, T2, ...)`
- Nested collections: `Vec<Vec<T>>`, `HashMap<K, Vec<V>>`

### Optional Types
- `Option<T>` for all base types
- Nested options: `Option<Vec<T>>`
- HashMap with optional values: `HashMap<K, Option<V>>`

### Complex Types
- Structs with mixed fields
- Enums with variants
- Nested structures

## Edge Cases Tested

### Empty Collections
```rust
let empty_vec: Vec<i32> = vec![];
let empty_map: HashMap<String, i32> = HashMap::new();
```

### None/Null Values
```rust
let none_value: Option<i32> = None;
let some_none: Vec<Option<i32>> = vec![Some(1), None, Some(3)];
```

### Unicode Strings
```rust
let unicode = "Hello 世界 🌍".to_string();
let emoji = "🦀 Rust + 🐍 Python = ❤️".to_string();
```

### Special Float Values
```rust
let nan = f64::NAN;
let infinity = f64::INFINITY;
let neg_infinity = f64::NEG_INFINITY;
```

### Large Values
```rust
let large_int = i64::MAX;
let small_int = i64::MIN;
```

## Validation Workflow

### 1. Type Validator Script

The `type_validator.py` script validates Python types:

```python
def validate_type(value, expected_type):
    """Validate that a Python value matches the expected type."""
    # Validates primitives, collections, optionals
    # Returns detailed error messages on mismatch
```

### 2. Round-trip Testing

Each test follows this pattern:

```rust
#[test]
fn test_type_roundtrip() {
    // 1. Create Rust value
    let original = MyType::new();

    // 2. Convert to Python
    let py_value = to_python(&original);

    // 3. Validate Python type
    validate_python_type(&py_value);

    // 4. Convert back to Rust
    let roundtrip: MyType = from_python(&py_value);

    // 5. Assert equality
    assert_eq!(original, roundtrip);
}
```

### 3. Integration Testing

Integration tests verify:
- All type conversions work correctly
- Edge cases are handled properly
- Error messages are clear
- Performance is acceptable

## Test Organization

### Unit Tests (in src/)
```rust
#[cfg(test)]
mod tests {
    // Quick validation tests
    // Type-specific edge cases
}
```

### Integration Tests (in tests/)
```rust
// Full round-trip tests
// Cross-module validation
// End-to-end scenarios
```

## Property-Based Testing Concepts

While this example uses explicit test cases, here are property-based testing ideas:

### Symmetry Property
```rust
// For all values v: from_python(to_python(v)) == v
fn prop_roundtrip<T>(value: T) -> bool {
    let py_value = to_python(&value);
    let roundtrip = from_python(&py_value);
    value == roundtrip
}
```

### Type Preservation Property
```rust
// For all values v: type_of(to_python(v)) == expected_python_type
fn prop_type_preserved<T>(value: T) -> bool {
    let py_value = to_python(&value);
    validate_type(&py_value, T::python_type())
}
```

### Error Handling Property
```rust
// For all invalid values: from_python(v) returns Err
fn prop_invalid_rejected(invalid: PyValue) -> bool {
    from_python::<ValidType>(&invalid).is_err()
}
```

## Common Testing Patterns

### Pattern 1: Parameterized Tests
```rust
#[test]
fn test_integers() {
    for value in [0, 1, -1, i32::MAX, i32::MIN] {
        assert_roundtrip(value);
    }
}
```

### Pattern 2: Table-Driven Tests
```rust
let test_cases = vec![
    ("empty", vec![]),
    ("single", vec![1]),
    ("multiple", vec![1, 2, 3]),
];

for (name, input) in test_cases {
    assert_roundtrip(input);
}
```

### Pattern 3: Error Case Testing
```rust
#[test]
#[should_panic(expected = "type mismatch")]
fn test_invalid_conversion() {
    let py_value = create_invalid_python_value();
    let _: ValidType = from_python(&py_value);
}
```

## Validation Checklist

Before releasing type conversion code:

- [ ] All primitive types tested
- [ ] All collection types tested
- [ ] Optional types tested (Some and None)
- [ ] Empty collections tested
- [ ] Unicode strings tested
- [ ] Special float values tested (NaN, infinity)
- [ ] Large/extreme values tested
- [ ] Nested structures tested
- [ ] Error cases tested
- [ ] Round-trip tests pass
- [ ] Type validation passes
- [ ] Integration tests pass
- [ ] Performance is acceptable

## Performance Considerations

### Benchmarking Round-trips
```rust
#[bench]
fn bench_roundtrip(b: &mut Bencher) {
    let value = create_test_value();
    b.iter(|| {
        let py_value = to_python(&value);
        let _: TestType = from_python(&py_value);
    });
}
```

### Memory Profiling
- Check for memory leaks in conversions
- Verify Python reference counting
- Monitor GIL contention in parallel tests

## Best Practices

1. **Test both directions**: Rust→Python and Python→Rust
2. **Test edge cases first**: They reveal bugs quickly
3. **Use descriptive test names**: `test_empty_hashmap_roundtrip`
4. **Validate Python types**: Don't assume conversions are correct
5. **Test error paths**: Invalid conversions should fail gracefully
6. **Document failures**: When tests fail, understand why
7. **Automate validation**: Use CI to run tests on every change

## Extending the Tests

To add a new type:

1. Define the type in `src/types.rs`
2. Implement conversion traits
3. Add unit tests in the type module
4. Add integration tests in `tests/integration_test.rs`
5. Add edge cases to the examples
6. Run `cargo test` to verify

## Troubleshooting

### Test Failures

**Symptom**: `assertion failed: left == right`
- Check for floating-point precision issues
- Verify HashMap ordering doesn't matter
- Look for unimplemented Debug/PartialEq

**Symptom**: `type validation failed`
- Check Python type expectations
- Verify Option<T> handling
- Look for missing type conversions

**Symptom**: `conversion error`
- Check for overflow in numeric conversions
- Verify string encoding (UTF-8)
- Look for unsupported types

### Common Pitfalls

1. **Float equality**: Use approximate comparison for f32/f64
2. **HashMap ordering**: Don't assume iteration order
3. **Python GIL**: Required for all Python operations
4. **Reference counting**: Ensure Python objects are properly managed
5. **Unicode normalization**: Strings may normalize differently

## References

- [PyO3 Documentation](https://pyo3.rs/)
- [Rust Testing](https://doc.rust-lang.org/book/ch11-00-testing.html)
- [Property-Based Testing](https://hypothesis.readthedocs.io/)
- [Type System Documentation](../../README.md)

## License

This example is part of the PyO3-DSpy type system documentation.
