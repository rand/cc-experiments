# Example 01: Basic Module with Simple Functions

This example demonstrates the fundamentals of creating a PyO3 module with simple functions.

## What You'll Learn

- How to create a PyO3 module using `#[pymodule]`
- How to export functions using `#[pyfunction]`
- Basic type conversion between Rust and Python
- Adding module metadata (version, author)
- Writing function docstrings that appear in Python

## Code Structure

```
01_basic_module/
├── src/
│   └── lib.rs          # Main module implementation
├── Cargo.toml          # Rust dependencies
├── pyproject.toml      # Python packaging configuration
├── test_example.py     # Python tests
└── README.md           # This file
```

## Building and Running

### Prerequisites

```bash
# Install maturin if you haven't already
pip install maturin
```

### Build and Install

```bash
# Development build (faster, with debug symbols)
maturin develop

# Release build (optimized)
maturin develop --release
```

### Run Tests

```bash
pytest test_example.py -v
```

### Interactive Testing

```python
import basic_module

# Arithmetic functions
print(basic_module.add(5, 3))        # 8
print(basic_module.multiply(4, 7))   # 28

# String manipulation
print(basic_module.greet("World"))   # Hello, World!
print(basic_module.repeat_string("ab", 3))  # ababab

# Boolean operations
print(basic_module.is_even(42))      # True
print(basic_module.is_even(17))      # False

# Module metadata
print(basic_module.__version__)      # 0.1.0
print(basic_module.__author__)       # PyO3 Examples

# Function documentation
help(basic_module.add)
```

## Key Concepts

### 1. Module Declaration

```rust
#[pymodule]
fn basic_module(_py: Python, m: &PyModule) -> PyResult<()> {
    // Add functions and metadata
    Ok(())
}
```

The `#[pymodule]` attribute marks a function as a Python module entry point. The module name comes from the function name (or can be overridden in Cargo.toml).

### 2. Function Export

```rust
#[pyfunction]
fn add(a: i64, b: i64) -> i64 {
    a + b
}

m.add_function(wrap_pyfunction!(add, m)?)?;
```

Functions marked with `#[pyfunction]` can be exported to Python. They must be registered using `add_function` and `wrap_pyfunction!`.

### 3. Type Conversion

PyO3 automatically converts between Rust and Python types:
- `i64` ↔ `int`
- `&str`/`String` ↔ `str`
- `bool` ↔ `bool`
- `usize` ↔ `int`

### 4. Documentation

Rust doc comments (`///`) become Python docstrings automatically, making your Rust code self-documenting in Python.

## Performance Notes

These simple functions demonstrate the FFI overhead. For such trivial operations, pure Python might actually be faster due to call overhead. PyO3 shines when:
- Function does significant computation
- Working with large data structures
- Need type safety guarantees
- Integrating existing Rust libraries

## Next Steps

- **Example 02**: Learn about function arguments (optional, keyword, *args, **kwargs)
- **Example 03**: Explore error handling and exception creation
- **Example 04**: Build multi-module structures with submodules

## Common Issues

### Module Not Found
```bash
# Make sure you've built the module
maturin develop
```

### Type Errors
```python
# Python ints are arbitrary precision, but Rust i64 is limited
basic_module.add(2**63, 1)  # OverflowError
```

### Import Name Mismatch
The module name in Python matches the function name in `#[pymodule]`, not the package name in Cargo.toml.
