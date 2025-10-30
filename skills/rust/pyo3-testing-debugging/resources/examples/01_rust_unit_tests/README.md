# Example 01: Rust Unit Tests for PyO3

Basic Rust unit testing for PyO3 functions, demonstrating how to test both pure Rust logic and PyO3-wrapped functions.

## What You'll Learn

- Writing basic Rust unit tests
- Testing PyO3 functions with `Python::with_gil`
- Testing error conditions
- Running tests with cargo

## Project Structure

```
01_rust_unit_tests/
├── src/
│   └── lib.rs          # PyO3 module with tests
├── Cargo.toml          # Rust dependencies
├── pyproject.toml      # Python package metadata
└── README.md           # This file
```

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install maturin
pip install maturin

# Build and install
maturin develop
```

## Running Tests

```bash
# Run all Rust tests
cargo test

# Run with output visible
cargo test -- --nocapture

# Run specific test
cargo test test_sum_basic

# Run tests in verbose mode
cargo test -- --test-threads=1 --nocapture
```

## Key Concepts

### 1. Testing Pure Rust Functions

Pure Rust functions (no PyO3 types) can be tested without GIL:

```rust
pub fn calculate_sum(data: &[f64]) -> f64 {
    data.iter().sum()
}

#[test]
fn test_calculate_sum() {
    assert_eq!(calculate_sum(&[1.0, 2.0, 3.0]), 6.0);
}
```

### 2. Testing PyO3 Functions

PyO3 functions require GIL acquisition:

```rust
#[test]
fn test_with_gil() {
    Python::with_gil(|py| {
        let list = PyList::new(py, &[1, 2, 3]);
        // Test operations
    });
}
```

### 3. Testing Error Conditions

Always test error paths:

```rust
#[test]
fn test_division_by_zero() {
    Python::with_gil(|py| {
        let result = divide(py, 10.0, 0.0);
        assert!(result.is_err());
    });
}
```

## Expected Output

```
running 6 tests
test tests::test_calculate_sum ... ok
test tests::test_divide_basic ... ok
test tests::test_divide_by_zero ... ok
test tests::test_empty_sum ... ok
test tests::test_process_list ... ok
test tests::test_process_list_invalid ... ok

test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

## Next Steps

- Move to example 02 for Python-side testing with pytest
- Learn about fixtures and parameterized tests
- Explore integration testing strategies
