# Example 04: Property-Based Testing

Property-based testing with proptest (Rust) and hypothesis (Python) to automatically discover edge cases.

## What You'll Learn

- Property-based testing with proptest
- Using hypothesis for Python property tests
- Defining properties and invariants
- Generating test data automatically
- Shrinking failing test cases

## Project Structure

```
04_property_testing/
├── src/
│   └── lib.rs          # Functions with property tests
├── tests/
│   └── test_properties.py  # Hypothesis property tests
├── Cargo.toml
├── pyproject.toml
└── README.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install maturin hypothesis pytest
maturin develop
```

## Running Tests

```bash
# Run Rust property tests
cargo test

# Run Python property tests
pytest tests/ -v

# Run with more examples
HYPOTHESIS_MAX_EXAMPLES=10000 pytest tests/ -v
```

## Key Concepts

### 1. Proptest in Rust

```rust
proptest! {
    #[test]
    fn test_commutative(a in 0.0..1000.0, b in 0.0..1000.0) {
        assert_eq!(add(a, b), add(b, a));
    }
}
```

### 2. Hypothesis in Python

```python
@given(st.lists(st.floats(allow_nan=False)))
def test_sum_matches_python(data):
    assert abs(fast_sum(data) - sum(data)) < 1e-6
```

## Expected Output

```
Rust tests:
test proptest_reverse_is_involution ... ok
test proptest_sort_is_idempotent ... ok
test proptest_sum_commutative ... ok

Python tests:
tests/test_properties.py::test_sum_matches_builtin PASSED
tests/test_properties.py::test_reverse_is_involution PASSED
tests/test_properties.py::test_sort_preserves_length PASSED
```

## Next Steps

- Move to example 05 for performance benchmarking
- Learn about stateful property testing
- Explore custom generators
