# Example 04: Mixed Layout

Mixed Rust/Python project structure demonstrating how to combine fast Rust extensions with pure Python code in a single package.

## What This Demonstrates

- Mixed Rust/Python project layout
- Pure Python wrapper around Rust core
- Python-source directory configuration
- Module naming conventions (`_core` for internal)
- Combining Rust performance with Python flexibility

## Project Structure

```
04_mixed_layout/
├── src/
│   └── lib.rs              # Rust core (_core module)
├── python/
│   └── mixed_layout/
│       └── __init__.py     # Python wrapper and utilities
├── Cargo.toml              # Rust configuration
├── pyproject.toml          # Python configuration with python-source
└── README.md               # This file
```

## Key Concepts

### Mixed Layout Architecture

```
┌─────────────────────────────────────┐
│   Python Package (mixed_layout)     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ Pure Python  │  │ Rust Core   │ │
│  │ __init__.py  │→ │ _core.so    │ │
│  │              │  │ (compiled)  │ │
│  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────┘
```

### Naming Conventions

- **Public API**: `mixed_layout` - What users import
- **Rust Core**: `_core` - Internal extension module (private by convention)
- **Python Wrapper**: Provides Pythonic API, validation, and pure Python utilities

### Directory Layout

```
python/mixed_layout/        # Python package root
├── __init__.py            # Main API, imports from _core
├── utils.py               # Pure Python utilities (optional)
└── _core.pyi              # Type stubs for Rust (optional)
```

## Building

### Development Build
```bash
maturin develop
```

This installs both:
1. Compiled Rust extension (`_core.so`)
2. Python source files from `python/`

### Production Build
```bash
maturin build --release
```

Wheel contains:
- `mixed_layout/_core.so` - Compiled Rust extension
- `mixed_layout/__init__.py` - Python wrapper

## Configuration

### pyproject.toml

```toml
[tool.maturin]
python-source = "python"           # Where Python files live
module-name = "mixed_layout._core" # Extension module name
```

### Cargo.toml

```toml
[lib]
name = "_core"              # Must match module-name suffix
crate-type = ["cdylib"]
```

## Testing

### Rust Tests
```bash
cargo test
```

### Python Usage
```python
import mixed_layout

# Use the public API (Rust-backed)
print(mixed_layout.fibonacci(10))  # 55
print(mixed_layout.gcd(48, 18))    # 6

# Use pure Python utilities
print(mixed_layout.lcm(12, 18))    # 36
seq = mixed_layout.fibonacci_sequence(7)
print(seq)  # [0, 1, 1, 2, 3, 5, 8]

# Use pure Python class
utils = mixed_layout.MathUtils()
print(utils.is_even(42))           # True
print(utils.factorize(60))         # [(2, 2), (3, 1), (5, 1)]

# Access version
print(mixed_layout.__version__)    # 0.1.0
```

### Import Structure

```python
# Users import from top-level package
from mixed_layout import fibonacci, gcd

# _core is an implementation detail (but accessible)
from mixed_layout._core import fibonacci as _rust_fib

# Both work, but public API is preferred
assert fibonacci(10) == _rust_fib(10)
```

## When to Use Mixed Layout

### Use Mixed Layout When:
- You need both Rust performance and Python flexibility
- You want to provide Pythonic wrappers around Rust code
- You have pure Python utilities alongside Rust extensions
- You want to add validation or type checking in Python

### Use Pure Rust When:
- Everything can be done in Rust
- No need for Python-side logic
- Simpler project structure

## Best Practices

### 1. Internal Module Naming
Use `_core` or `_lib` prefix to indicate internal module:
```python
from ._core import rust_function  # Internal
```

### 2. Public API Design
Expose clean Python API:
```python
# __init__.py
from ._core import rust_function as _rust_impl

def public_function(x):
    """Pythonic wrapper with validation."""
    if x < 0:
        raise ValueError("x must be non-negative")
    return _rust_impl(x)
```

### 3. Error Handling
Convert Rust errors to Python exceptions:
```rust
// Rust
Err(PyValueError::new_err("Invalid input"))
```
```python
# Python - catches and re-raises with context
try:
    result = _core.function(x)
except ValueError as e:
    raise ValueError(f"Processing failed: {e}") from e
```

### 4. Type Stubs (Optional)
Create `_core.pyi` for type hints:
```python
# python/mixed_layout/_core.pyi
def fibonacci(n: int) -> int: ...
def gcd(a: int, b: int) -> int: ...
```

## Verification

After building, verify structure:

```bash
# Check wheel contents
unzip -l target/wheels/mixed_layout-*.whl

# Should contain:
# mixed_layout/__init__.py
# mixed_layout/_core.*.so
```

## Common Patterns

### Pattern 1: Validation Wrapper
```python
def safe_function(x: int) -> int:
    """Add Python validation around Rust function."""
    if not isinstance(x, int):
        raise TypeError("x must be an integer")
    return _core.unsafe_function(x)
```

### Pattern 2: Default Arguments
```python
def function_with_defaults(x: int, y: int = 10) -> int:
    """Rust doesn't support default args, handle in Python."""
    return _core.function(x, y)
```

### Pattern 3: Async Wrapper
```python
async def async_function(x: int) -> int:
    """Wrap synchronous Rust in async Python."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _core.sync_function, x)
```

## Next Steps

See `05_dependencies` for:
- Managing Rust dependencies (Cargo.toml)
- Managing Python dependencies (pyproject.toml)
- Optional dependencies
- Dependency version constraints
