# Example 01: Basic Package

Minimal maturin package setup demonstrating the absolute basics of creating a distributable Python package from Rust code.

## What This Demonstrates

- Minimal `Cargo.toml` configuration for PyO3
- Minimal `pyproject.toml` for maturin
- Basic `#[pyfunction]` and `#[pymodule]` attributes
- Simple function exports to Python

## Project Structure

```
01_basic_package/
├── src/
│   └── lib.rs          # Rust source with PyO3 bindings
├── Cargo.toml          # Rust package configuration
├── pyproject.toml      # Python package metadata
└── README.md           # This file
```

## Key Concepts

### Cargo.toml
- `crate-type = ["cdylib"]` - Required for Python extension modules
- `pyo3` with `extension-module` feature

### pyproject.toml
- `build-system` - Specifies maturin as build backend
- `requires-python` - Minimum Python version

### lib.rs
- `#[pyfunction]` - Exports Rust function to Python
- `#[pymodule]` - Defines the Python module
- Python-style docstrings for documentation

## Building

### Development Build
```bash
# Install maturin if not already installed
pip install maturin

# Build and install in development mode
maturin develop
```

### Production Wheel
```bash
# Build wheel for distribution
maturin build --release

# Wheel will be in target/wheels/
ls target/wheels/
```

## Testing

### Rust Tests
```bash
cargo test
```

### Python Usage
```python
import basic_package

# Test the functions
result = basic_package.add(2, 3)
print(f"2 + 3 = {result}")  # Output: 2 + 3 = 5

greeting = basic_package.greet("World")
print(greeting)  # Output: Hello, World!
```

## Expected Output

```
$ maturin develop
📦 Built wheel to target/wheels/basic_package-0.1.0-cp311-cp311-macosx_14_0_arm64.whl
📦 Installed basic_package-0.1.0

$ python3
>>> import basic_package
>>> basic_package.add(2, 3)
5
>>> basic_package.greet("Rust")
'Hello, Rust!'
```

## Next Steps

See `02_metadata_config` for:
- Complete package metadata
- License and author information
- Description and keywords
- Classifier tags
