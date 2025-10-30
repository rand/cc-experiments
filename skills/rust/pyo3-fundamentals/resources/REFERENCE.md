# PyO3 Fundamentals Reference

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**PyO3 Version**: 0.20+
**Python Version**: 3.8+
**Rust Version**: 1.70+

## Table of Contents

1. [Introduction](#introduction)
2. [Environment Setup](#environment-setup)
3. [Project Structure](#project-structure)
4. [Type Conversion](#type-conversion)
5. [Error Handling](#error-handling)
6. [FFI Safety](#ffi-safety)
7. [Cross-Language Debugging](#cross-language-debugging)
8. [Memory Profiling](#memory-profiling)
9. [Production Deployment](#production-deployment)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Introduction

### What is PyO3?

PyO3 is a Rust crate that provides:
- Rust bindings for Python's C API
- Tools for creating native Python modules in Rust
- Safe abstractions over Python's object model
- Integration with Rust's ownership system

### Why Use PyO3?

**Performance Benefits**:
- **10-100x speedups** for CPU-bound operations
- Zero-cost abstractions (no Python interpreter overhead in hot loops)
- SIMD optimizations via Rust
- Parallel execution without GIL constraints (in Rust code)

**Safety Benefits**:
- Memory safety enforced by Rust compiler
- No segfaults from buffer overflows
- Thread safety checked at compile time
- Elimination of use-after-free bugs

**Developer Experience**:
- Modern tooling (cargo, rust-analyzer)
- Excellent error messages
- Type-safe FFI boundaries
- Seamless Python integration

### When to Use PyO3 vs Alternatives

| Use Case | Best Choice | Rationale |
|----------|-------------|-----------|
| CPU-bound numeric computation | **PyO3** | Parallel execution, SIMD, zero overhead |
| I/O-bound operations | Python asyncio | FFI overhead negates benefits |
| Existing Rust library | **PyO3** | Direct integration without C wrapper |
| Prototyping | Pure Python | Faster development iteration |
| Legacy C extension | **PyO3** | Memory safety, maintainability |
| Simple glue code | ctypes/cffi | Lower barrier to entry |
| Maximum performance | **PyO3** | Rust optimization potential |

---

## Environment Setup

### Prerequisites

**System Requirements**:
- Linux (x86_64, aarch64), macOS (x86_64, arm64), or Windows (x86_64)
- 4GB+ RAM for compilation
- 2GB+ disk space

**Software Requirements**:
```bash
# Rust (via rustup)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup default stable
rustc --version  # Should be 1.70+

# Python
python3 --version  # Should be 3.8+
python3 -m pip install --upgrade pip

# maturin (PyO3 build tool)
pip install maturin

# Development tools (optional but recommended)
cargo install cargo-watch    # Auto-rebuild on changes
cargo install flamegraph     # Performance profiling
pip install pytest pytest-benchmark  # Testing
```

### IDE Setup

#### VS Code Configuration

**.vscode/settings.json**:
```json
{
  "rust-analyzer.cargo.features": ["extension-module"],
  "rust-analyzer.checkOnSave.command": "clippy",
  "rust-analyzer.checkOnSave.extraArgs": ["--target-dir=target/rust-analyzer"],
  "python.analysis.extraPaths": ["${workspaceFolder}/target/wheels"],
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "files.watcherExclude": {
    "**/target/**": true
  }
}
```

**.vscode/launch.json** (debugging):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Python with Rust Extension",
      "type": "lldb",
      "request": "launch",
      "program": "${env:HOME}/.pyenv/versions/3.11.0/bin/python",
      "args": ["${file}"],
      "cwd": "${workspaceFolder}",
      "sourceLanguages": ["rust", "python"],
      "env": {
        "RUST_BACKTRACE": "1",
        "RUST_LOG": "debug"
      }
    }
  ]
}
```

#### PyCharm/IntelliJ Configuration

1. Install **Rust plugin**
2. Configure Python SDK (Settings → Project → Python Interpreter)
3. Add Rust project (File → New → Module from Existing Sources → Cargo.toml)
4. Set run configuration:
   ```
   Script path: test_module.py
   Environment variables: RUST_BACKTRACE=1
   Working directory: project root
   ```

### Verification

**verify_setup.sh**:
```bash
#!/bin/bash
set -e

echo "=== PyO3 Environment Verification ==="

# Check Rust
echo -n "Rust version: "
rustc --version || { echo "ERROR: Rust not found"; exit 1; }

# Check Python
echo -n "Python version: "
python3 --version || { echo "ERROR: Python not found"; exit 1; }

# Check maturin
echo -n "maturin version: "
maturin --version || { echo "ERROR: maturin not found"; exit 1; }

# Test compilation
echo "Testing PyO3 compilation..."
mkdir -p /tmp/pyo3_test
cd /tmp/pyo3_test
maturin init --bindings pyo3 --name test_module
maturin develop --release
python3 -c "import test_module; print('✓ Compilation successful')"

echo "=== All checks passed! ==="
```

Run:
```bash
bash verify_setup.sh
```

---

## Project Structure

### Creating a New Project

```bash
# Create project
mkdir my_rust_extension && cd my_rust_extension
maturin init --bindings pyo3

# This creates:
# my_rust_extension/
# ├── Cargo.toml          # Rust dependencies
# ├── pyproject.toml      # Python packaging
# ├── src/
# │   └── lib.rs          # Rust implementation
# └── .gitignore
```

### Directory Layout

**Recommended structure for production**:
```
my_rust_extension/
├── Cargo.toml              # Rust configuration
├── pyproject.toml          # Python packaging
├── README.md
├── LICENSE
├── .gitignore
├── src/
│   ├── lib.rs              # Python module entry point
│   ├── types.rs            # Type conversions
│   ├── errors.rs           # Error handling
│   └── ops/                # Implementation modules
│       ├── mod.rs
│       ├── math.rs
│       └── string.rs
├── tests/
│   ├── test_basic.py       # Python integration tests
│   └── test_errors.py
├── benches/
│   └── benchmark.py        # Performance benchmarks
└── examples/
    ├── basic_usage.py
    └── advanced.py
```

### Cargo.toml Configuration

**Minimal configuration**:
```toml
[package]
name = "my_rust_extension"
version = "0.1.0"
edition = "2021"

[lib]
name = "my_rust_extension"
crate-type = ["cdylib"]  # Required for Python extension

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
```

**Production configuration**:
```toml
[package]
name = "my_rust_extension"
version = "0.1.0"
edition = "2021"
authors = ["Your Name <you@example.com>"]
description = "High-performance Python extension in Rust"
license = "MIT OR Apache-2.0"
repository = "https://github.com/user/my_rust_extension"
readme = "README.md"
keywords = ["python", "pyo3", "performance"]
categories = ["api-bindings"]

[lib]
name = "my_rust_extension"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
anyhow = "1.0"       # Error handling
thiserror = "1.0"    # Custom error types
rayon = "1.8"        # Parallel iterators
serde = { version = "1.0", features = ["derive"] }  # Serialization
serde_json = "1.0"   # JSON support

[dev-dependencies]
pyo3 = { version = "0.20", features = ["auto-initialize"] }  # For Rust tests
criterion = "0.5"    # Benchmarking

[profile.release]
lto = true           # Link-time optimization
codegen-units = 1    # Better optimization, slower compile
strip = true         # Remove debug symbols
opt-level = 3        # Maximum optimization

[profile.dev]
opt-level = 0        # Fast compilation
debug = true         # Include debug info

[profile.release-with-debug]
inherits = "release"
debug = true         # Release optimization + debug symbols
strip = false
```

**Feature flags** (optional):
```toml
[features]
default = []
parallel = ["rayon"]           # Enable parallel processing
json = ["serde_json"]          # Enable JSON support
dev = ["pyo3/auto-initialize"] # For Rust unit tests
```

### pyproject.toml Configuration

**Minimal**:
```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[project]
name = "my_rust_extension"
requires-python = ">=3.8"
```

**Production**:
```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[project]
name = "my_rust_extension"
version = "0.1.0"
description = "High-performance Python extension in Rust"
readme = "README.md"
requires-python = ">=3.8"
license = { text = "MIT OR Apache-2.0" }
authors = [
    { name = "Your Name", email = "you@example.com" }
]
keywords = ["rust", "performance", "extension"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Rust",
]
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-benchmark>=4.0",
    "mypy>=1.0",
    "black>=23.0",
]

[project.urls]
Homepage = "https://github.com/user/my_rust_extension"
Repository = "https://github.com/user/my_rust_extension"
"Bug Tracker" = "https://github.com/user/my_rust_extension/issues"

[tool.maturin]
python-source = "python"  # Optional: Pure Python code alongside Rust
module-name = "my_rust_extension._core"  # Internal module name
features = ["parallel"]  # Enable Cargo features

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"

[tool.mypy]
python_version = "3.8"
strict = true
warn_return_any = true
warn_unused_configs = true
```

### Building and Installing

```bash
# Development mode (fast iteration)
maturin develop              # Debug build, installs locally
maturin develop --release    # Release build

# Build wheel
maturin build --release      # Outputs to target/wheels/

# Install wheel
pip install target/wheels/my_rust_extension-*.whl

# Auto-rebuild on changes
cargo watch -x "maturin develop"
```

---

## Type Conversion

### Overview

PyO3 provides automatic conversion between Rust and Python types through traits:
- **`FromPyObject`**: Python → Rust conversion
- **`IntoPy<PyObject>`**: Rust → Python conversion
- **`ToPyObject`**: Rust → Python conversion (borrowed)

### Primitive Types

| Rust Type | Python Type | Notes |
|-----------|-------------|-------|
| `i32`, `i64` | `int` | Checked conversion (overflow detection) |
| `u32`, `u64` | `int` | Checked conversion |
| `f32`, `f64` | `float` | Direct mapping |
| `bool` | `bool` | Direct mapping |
| `String`, `&str` | `str` | UTF-8 validation |
| `Vec<u8>`, `&[u8]` | `bytes` | Direct mapping |
| `()` | `None` | Unit type → None |

**Example**:
```rust
use pyo3::prelude::*;

#[pyfunction]
fn process_number(x: i64) -> i64 {
    x * 2
}

#[pyfunction]
fn process_string(s: String) -> String {
    s.to_uppercase()
}

#[pyfunction]
fn process_float(f: f64) -> f64 {
    f * 3.14
}

#[pyfunction]
fn return_nothing() {
    // Returns None to Python
}
```

Python usage:
```python
import my_module

print(my_module.process_number(42))      # 84
print(my_module.process_string("hello")) # "HELLO"
print(my_module.process_float(2.0))      # 6.28
print(my_module.return_nothing())        # None
```

### Option<T>

`Option<T>` maps to Python's `Optional[T]`:
- `Some(value)` → `value`
- `None` → `None`

```rust
#[pyfunction]
fn maybe_double(x: Option<i32>) -> Option<i32> {
    x.map(|n| n * 2)
}
```

Python:
```python
print(my_module.maybe_double(5))    # 10
print(my_module.maybe_double(None)) # None
```

**With default values**:
```rust
#[pyfunction]
fn greet(name: Option<String>) -> String {
    let name = name.unwrap_or_else(|| "World".to_string());
    format!("Hello, {}!", name)
}
```

Python:
```python
print(my_module.greet("Alice"))  # "Hello, Alice!"
print(my_module.greet(None))     # "Hello, World!"
```

### Collections

#### Vec<T> ↔ list

```rust
#[pyfunction]
fn sum_list(numbers: Vec<i64>) -> i64 {
    numbers.iter().sum()
}

#[pyfunction]
fn double_list(numbers: Vec<i64>) -> Vec<i64> {
    numbers.into_iter().map(|n| n * 2).collect()
}
```

Python:
```python
print(my_module.sum_list([1, 2, 3, 4]))      # 10
print(my_module.double_list([1, 2, 3]))      # [2, 4, 6]
```

#### HashMap<K, V> ↔ dict

```rust
use std::collections::HashMap;

#[pyfunction]
fn count_chars(s: String) -> HashMap<char, usize> {
    let mut counts = HashMap::new();
    for c in s.chars() {
        *counts.entry(c).or_insert(0) += 1;
    }
    counts
}

#[pyfunction]
fn merge_dicts(
    a: HashMap<String, i64>,
    b: HashMap<String, i64>,
) -> HashMap<String, i64> {
    let mut result = a;
    for (k, v) in b {
        *result.entry(k).or_insert(0) += v;
    }
    result
}
```

Python:
```python
print(my_module.count_chars("hello"))
# {'h': 1, 'e': 1, 'l': 2, 'o': 1}

print(my_module.merge_dicts(
    {"a": 1, "b": 2},
    {"b": 3, "c": 4}
))
# {'a': 1, 'b': 5, 'c': 4}
```

#### HashSet<T> ↔ set

```rust
use std::collections::HashSet;

#[pyfunction]
fn unique_chars(s: String) -> HashSet<char> {
    s.chars().collect()
}

#[pyfunction]
fn set_intersection(
    a: HashSet<i64>,
    b: HashSet<i64>,
) -> HashSet<i64> {
    a.intersection(&b).copied().collect()
}
```

Python:
```python
print(my_module.unique_chars("hello"))
# {'h', 'e', 'l', 'o'}

print(my_module.set_intersection({1, 2, 3}, {2, 3, 4}))
# {2, 3}
```

### Tuples

Rust tuples map directly to Python tuples:

```rust
#[pyfunction]
fn swap_pair(pair: (i64, String)) -> (String, i64) {
    (pair.1, pair.0)
}

#[pyfunction]
fn split_name(full_name: String) -> (String, String) {
    let parts: Vec<&str> = full_name.splitn(2, ' ').collect();
    (
        parts.get(0).unwrap_or(&"").to_string(),
        parts.get(1).unwrap_or(&"").to_string(),
    )
}
```

Python:
```python
print(my_module.swap_pair((42, "hello")))  # ('hello', 42)
print(my_module.split_name("John Doe"))    # ('John', 'Doe')
```

### Result<T, E> and Error Handling

`Result<T, E>` integrates with Python exceptions:
- `Ok(value)` → returns `value`
- `Err(e)` → raises Python exception

```rust
use pyo3::exceptions::PyValueError;

#[pyfunction]
fn divide(a: f64, b: f64) -> PyResult<f64> {
    if b == 0.0 {
        Err(PyValueError::new_err("Division by zero"))
    } else {
        Ok(a / b)
    }
}

#[pyfunction]
fn parse_int(s: String) -> PyResult<i64> {
    s.parse::<i64>()
        .map_err(|e| PyValueError::new_err(format!("Invalid integer: {}", e)))
}
```

Python:
```python
print(my_module.divide(10.0, 2.0))  # 5.0

try:
    my_module.divide(10.0, 0.0)
except ValueError as e:
    print(f"Error: {e}")  # Error: Division by zero

try:
    my_module.parse_int("not a number")
except ValueError as e:
    print(f"Error: {e}")  # Error: Invalid integer: ...
```

### Custom Types

#### Rust Struct → Python dict

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[derive(Clone)]
struct User {
    id: u64,
    name: String,
    email: String,
}

impl IntoPy<PyObject> for User {
    fn into_py(self, py: Python) -> PyObject {
        let dict = PyDict::new(py);
        dict.set_item("id", self.id).unwrap();
        dict.set_item("name", self.name).unwrap();
        dict.set_item("email", self.email).unwrap();
        dict.into()
    }
}

#[pyfunction]
fn get_user(id: u64) -> User {
    User {
        id,
        name: format!("User {}", id),
        email: format!("user{}@example.com", id),
    }
}
```

Python:
```python
user = my_module.get_user(123)
print(user)  # {'id': 123, 'name': 'User 123', 'email': 'user123@example.com'}
```

#### Python dict → Rust Struct

```rust
use pyo3::types::PyDict;

#[derive(Debug)]
struct Config {
    host: String,
    port: u16,
    debug: bool,
}

impl<'source> FromPyObject<'source> for Config {
    fn extract(ob: &'source PyAny) -> PyResult<Self> {
        let dict = ob.downcast::<PyDict>()?;
        Ok(Config {
            host: dict.get_item("host")?
                .ok_or_else(|| PyValueError::new_err("Missing 'host'"))?
                .extract()?,
            port: dict.get_item("port")?
                .ok_or_else(|| PyValueError::new_err("Missing 'port'"))?
                .extract()?,
            debug: dict.get_item("debug")
                .unwrap_or(None)
                .map(|v| v.extract())
                .transpose()?
                .unwrap_or(false),
        })
    }
}

#[pyfunction]
fn start_server(config: Config) -> String {
    format!("Starting server at {}:{} (debug={})",
            config.host, config.port, config.debug)
}
```

Python:
```python
config = {"host": "localhost", "port": 8080, "debug": True}
print(my_module.start_server(config))
# Starting server at localhost:8080 (debug=true)
```

### Bytes and Buffers

```rust
#[pyfunction]
fn hash_bytes(data: &[u8]) -> u64 {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let mut hasher = DefaultHasher::new();
    data.hash(&mut hasher);
    hasher.finish()
}

#[pyfunction]
fn compress_data(data: Vec<u8>) -> Vec<u8> {
    // Placeholder: use actual compression library
    data.into_iter().filter(|&b| b != 0).collect()
}
```

Python:
```python
data = b"hello world"
print(my_module.hash_bytes(data))

compressed = my_module.compress_data(b"\x00\x01\x00\x02")
print(compressed)  # b'\x01\x02'
```

### Type Conversion Best Practices

1. **Use appropriate types**:
   ```rust
   // Good: Specific types
   fn process(value: i64) -> PyResult<String>

   // Bad: Too generic
   fn process(value: PyObject) -> PyObject
   ```

2. **Validate input early**:
   ```rust
   #[pyfunction]
   fn set_age(age: i32) -> PyResult<()> {
       if age < 0 || age > 150 {
           return Err(PyValueError::new_err("Invalid age"));
       }
       Ok(())
   }
   ```

3. **Provide clear error messages**:
   ```rust
   // Good
   Err(PyValueError::new_err(format!(
       "Expected positive integer, got {}",
       value
   )))

   // Bad
   Err(PyValueError::new_err("Invalid input"))
   ```

4. **Use borrowing where possible**:
   ```rust
   // Good: Borrows string
   fn count_chars(s: &str) -> usize {
       s.chars().count()
   }

   // Suboptimal: Takes ownership
   fn count_chars(s: String) -> usize {
       s.chars().count()
   }
   ```

5. **Handle None explicitly**:
   ```rust
   #[pyfunction]
   fn process_optional(value: Option<i64>) -> String {
       match value {
           Some(v) => format!("Got: {}", v),
           None => "No value provided".to_string(),
       }
   }
   ```

---

## Error Handling

### Python Exception Types

PyO3 provides Python exception types in `pyo3::exceptions`:

| Rust Type | Python Exception |
|-----------|------------------|
| `PyException` | `Exception` (base) |
| `PyValueError` | `ValueError` |
| `PyTypeError` | `TypeError` |
| `PyKeyError` | `KeyError` |
| `PyIndexError` | `IndexError` |
| `PyRuntimeError` | `RuntimeError` |
| `PyOSError` | `OSError` |
| `PyIOError` | `IOError` |
| `PyFileNotFoundError` | `FileNotFoundError` |
| `PyPermissionError` | `PermissionError` |

### Basic Error Handling

```rust
use pyo3::exceptions::{PyValueError, PyTypeError};

#[pyfunction]
fn validate_age(age: i32) -> PyResult<String> {
    if age < 0 {
        Err(PyValueError::new_err("Age cannot be negative"))
    } else if age > 150 {
        Err(PyValueError::new_err("Age is unrealistically high"))
    } else {
        Ok(format!("Valid age: {}", age))
    }
}
```

### Custom Exceptions

```rust
use pyo3::create_exception;

// Define custom exception
create_exception!(my_module, InvalidConfigError, pyo3::exceptions::PyException);

#[pyfunction]
fn load_config(path: String) -> PyResult<String> {
    if !std::path::Path::new(&path).exists() {
        return Err(InvalidConfigError::new_err(
            format!("Config file not found: {}", path)
        ));
    }
    Ok("Config loaded".to_string())
}

#[pymodule]
fn my_module(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(load_config, m)?)?;
    m.add("InvalidConfigError", py.get_type::<InvalidConfigError>())?;
    Ok(())
}
```

Python usage:
```python
try:
    my_module.load_config("nonexistent.toml")
except my_module.InvalidConfigError as e:
    print(f"Config error: {e}")
```

### Integration with anyhow

**anyhow** provides ergonomic error handling in Rust:

```rust
use anyhow::{Context, Result as AnyhowResult};
use pyo3::exceptions::PyRuntimeError;

fn read_file(path: &str) -> AnyhowResult<String> {
    std::fs::read_to_string(path)
        .context(format!("Failed to read file: {}", path))
}

#[pyfunction]
fn process_file(path: String) -> PyResult<usize> {
    let content = read_file(&path)
        .map_err(|e| PyRuntimeError::new_err(format!("{:#}", e)))?;
    Ok(content.lines().count())
}
```

**Converting anyhow::Error to PyErr**:
```rust
impl From<anyhow::Error> for PyErr {
    fn from(err: anyhow::Error) -> PyErr {
        PyRuntimeError::new_err(format!("{:#}", err))
    }
}

#[pyfunction]
fn process_file_v2(path: String) -> PyResult<usize> {
    let content = read_file(&path)?;  // Automatic conversion
    Ok(content.lines().count())
}
```

### Integration with thiserror

**thiserror** provides custom error types with automatic trait implementations:

```rust
use thiserror::Error;

#[derive(Error, Debug)]
enum DataError {
    #[error("Invalid format: {0}")]
    InvalidFormat(String),

    #[error("Value out of range: {value}, expected {min}-{max}")]
    OutOfRange { value: i64, min: i64, max: i64 },

    #[error("IO error")]
    Io(#[from] std::io::Error),

    #[error("Parse error")]
    Parse(#[from] std::num::ParseIntError),
}

impl From<DataError> for PyErr {
    fn from(err: DataError) -> PyErr {
        match err {
            DataError::InvalidFormat(_) | DataError::OutOfRange { .. } => {
                PyValueError::new_err(err.to_string())
            }
            DataError::Io(_) => PyOSError::new_err(err.to_string()),
            DataError::Parse(_) => PyValueError::new_err(err.to_string()),
        }
    }
}

#[pyfunction]
fn parse_data(s: String) -> PyResult<i64> {
    let value: i64 = s.parse()
        .map_err(DataError::from)?;

    if value < 0 || value > 100 {
        return Err(DataError::OutOfRange {
            value,
            min: 0,
            max: 100,
        }.into());
    }

    Ok(value)
}
```

### Error Context and Stack Traces

```rust
use anyhow::{Context, Result};

fn process_data(data: &[u8]) -> Result<String> {
    let text = std::str::from_utf8(data)
        .context("Data is not valid UTF-8")?;

    let parsed = text.parse::<i64>()
        .context("Failed to parse as integer")?;

    if parsed < 0 {
        anyhow::bail!("Value must be non-negative, got {}", parsed);
    }

    Ok(format!("Processed: {}", parsed))
}

#[pyfunction]
fn handle_data(data: Vec<u8>) -> PyResult<String> {
    process_data(&data)
        .map_err(|e| {
            // Include full error chain
            let chain: Vec<String> = e.chain()
                .map(|e| e.to_string())
                .collect();
            PyRuntimeError::new_err(chain.join("\n  Caused by: "))
        })
}
```

Python usage:
```python
try:
    my_module.handle_data(b"\xff\xfe")
except RuntimeError as e:
    print(f"Error: {e}")
    # Error: Data is not valid UTF-8
    #   Caused by: invalid utf-8 sequence of 1 bytes from index 0
```

### Error Handling Best Practices

1. **Use specific exception types**:
   ```rust
   // Good
   if key_not_found {
       return Err(PyKeyError::new_err(key));
   }

   // Bad
   if key_not_found {
       return Err(PyException::new_err("Key not found"));
   }
   ```

2. **Provide actionable error messages**:
   ```rust
   // Good
   Err(PyValueError::new_err(format!(
       "Port {} is out of range (1-65535)",
       port
   )))

   // Bad
   Err(PyValueError::new_err("Invalid port"))
   ```

3. **Include context**:
   ```rust
   read_file(path)
       .context(format!("Failed to read config from {}", path))
   ```

4. **Don't panic in library code**:
   ```rust
   // Good
   fn divide(a: f64, b: f64) -> PyResult<f64> {
       if b == 0.0 {
           return Err(PyValueError::new_err("Division by zero"));
       }
       Ok(a / b)
   }

   // Bad
   fn divide(a: f64, b: f64) -> f64 {
       if b == 0.0 {
           panic!("Division by zero");  // Crashes Python!
       }
       a / b
   }
   ```

5. **Use Result for fallible operations**:
   ```rust
   // Good
   #[pyfunction]
   fn parse_config(s: String) -> PyResult<Config> { ... }

   // Bad (hides errors)
   #[pyfunction]
   fn parse_config(s: String) -> Option<Config> { ... }
   ```

---

## FFI Safety

### The Global Interpreter Lock (GIL)

The GIL is Python's mechanism for ensuring thread safety. Key principles:

1. **One Python thread executes at a time** (within a single interpreter)
2. **C extensions must acquire the GIL** before calling Python APIs
3. **Releasing the GIL** allows true parallelism in native code

#### GIL Management in PyO3

```rust
use pyo3::Python;

#[pyfunction]
fn cpu_bound_task(py: Python, data: Vec<i64>) -> i64 {
    // We have the GIL here (automatically acquired)

    // Release GIL for CPU-intensive work
    py.allow_threads(|| {
        // No GIL here - cannot call Python APIs
        // Can run in parallel with Python code
        data.iter().map(|&x| x * x).sum()
    })
    // GIL automatically reacquired
}
```

**When to release the GIL**:
- CPU-intensive computations (> 10ms)
- I/O operations (file, network)
- Calling external libraries

**When to keep the GIL**:
- Calling Python APIs
- Working with Python objects
- Short operations (< 1ms)

### Memory Safety Rules

#### 1. Ownership and Lifetimes

```rust
// SAFE: Borrows Python string, doesn't outlive call
#[pyfunction]
fn process_string(s: &str) -> String {
    s.to_uppercase()
}

// UNSAFE: Trying to store reference beyond function scope
// static CACHED: Option<&str> = None;  // Won't compile!

// SAFE: Take ownership instead
#[pyfunction]
fn cache_string(s: String) {
    use std::sync::Mutex;
    static CACHED: Mutex<Option<String>> = Mutex::new(None);
    *CACHED.lock().unwrap() = Some(s);
}
```

#### 2. Thread Safety

```rust
use pyo3::Python;
use std::sync::Arc;
use std::thread;

#[pyfunction]
fn parallel_sum(py: Python, data: Vec<i64>) -> i64 {
    let data = Arc::new(data);

    py.allow_threads(|| {
        let handles: Vec<_> = (0..4).map(|i| {
            let data = Arc::clone(&data);
            thread::spawn(move || {
                let chunk_size = data.len() / 4;
                let start = i * chunk_size;
                let end = if i == 3 { data.len() } else { (i + 1) * chunk_size };
                data[start..end].iter().sum::<i64>()
            })
        }).collect();

        handles.into_iter().map(|h| h.join().unwrap()).sum()
    })
}
```

#### 3. Preventing Use-After-Free

```rust
use pyo3::types::PyList;

// SAFE: Borrows list for duration of function
#[pyfunction]
fn sum_list_safe(list: &PyList) -> PyResult<i64> {
    let mut sum = 0i64;
    for item in list.iter() {
        sum += item.extract::<i64>()?;
    }
    Ok(sum)
}

// UNSAFE: Storing reference to Python object
// struct Cache {
//     list: &'static PyList,  // Lifetime issue!
// }

// SAFE: Use Py<T> for owned references
use pyo3::Py;

struct Cache {
    list: Py<PyList>,  // Reference-counted Python object
}

#[pyfunction]
fn create_cache(py: Python, list: &PyList) -> Cache {
    Cache {
        list: list.into(),  // Increment refcount
    }
}
```

#### 4. Handling Python Objects in Rust

```rust
use pyo3::{Py, PyAny, Python};

// Store Python object in Rust struct
struct Worker {
    callback: Py<PyAny>,  // Python callable
}

impl Worker {
    fn new(callback: Py<PyAny>) -> Self {
        Worker { callback }
    }

    fn execute(&self, py: Python, arg: i64) -> PyResult<i64> {
        // Call Python function from Rust
        self.callback.call1(py, (arg,))?.extract(py)
    }
}

#[pyfunction]
fn create_worker(callback: Py<PyAny>) -> Worker {
    Worker::new(callback)
}

#[pyfunction]
fn run_worker(py: Python, worker: &Worker, value: i64) -> PyResult<i64> {
    worker.execute(py, value)
}
```

Python usage:
```python
def my_callback(x):
    return x * 2

worker = my_module.create_worker(my_callback)
result = my_module.run_worker(worker, 21)
print(result)  # 42
```

### Memory Leaks Prevention

#### Reference Counting

Python uses reference counting for memory management. PyO3 handles this automatically in most cases:

```rust
// PyO3 automatically manages refcounts
#[pyfunction]
fn create_list(py: Python) -> PyResult<Py<PyList>> {
    let list = PyList::empty(py);
    // Refcount is automatically managed
    Ok(list.into())
}  // No manual cleanup needed
```

**Manual refcount management** (rarely needed):
```rust
use pyo3::ffi;

unsafe fn manual_refcount_example(py: Python) {
    let obj = py.None().as_ptr();

    // Increment refcount
    ffi::Py_INCREF(obj);

    // ... use object ...

    // Decrement refcount
    ffi::Py_DECREF(obj);
}
```

#### Circular References

```rust
// POTENTIAL LEAK: Circular reference
struct Node {
    value: i64,
    next: Option<Py<Node>>,  // Circular reference possible
}

// SOLUTION: Use weak references
use pyo3::PyCell;
use std::sync::{Arc, Weak};

struct SafeNode {
    value: i64,
    next: Option<Arc<SafeNode>>,
    parent: Option<Weak<SafeNode>>,  // Weak reference to parent
}
```

### Data Races and Synchronization

```rust
use std::sync::{Arc, Mutex};

// SAFE: Proper synchronization
struct Counter {
    value: Arc<Mutex<i64>>,
}

#[pymethods]
impl Counter {
    #[new]
    fn new() -> Self {
        Counter {
            value: Arc::new(Mutex::new(0)),
        }
    }

    fn increment(&self) {
        let mut value = self.value.lock().unwrap();
        *value += 1;
    }

    fn get(&self) -> i64 {
        *self.value.lock().unwrap()
    }
}
```

### Panic Safety

**Panics in Rust cross FFI boundary as Python exceptions:**

```rust
#[pyfunction]
fn may_panic(value: i64) -> i64 {
    if value < 0 {
        panic!("Negative value!");  // Becomes Python SystemError
    }
    value * 2
}
```

Python:
```python
try:
    my_module.may_panic(-5)
except SystemError as e:
    print(f"Rust panic: {e}")
```

**Catching panics**:
```rust
use std::panic::catch_unwind;
use std::panic::AssertUnwindSafe;

#[pyfunction]
fn safe_operation(value: i64) -> PyResult<i64> {
    let result = catch_unwind(AssertUnwindSafe(|| {
        // Code that might panic
        if value < 0 {
            panic!("Oops!");
        }
        value * 2
    }));

    match result {
        Ok(v) => Ok(v),
        Err(_) => Err(PyRuntimeError::new_err("Operation panicked")),
    }
}
```

### FFI Safety Checklist

- [ ] **GIL management**: Release GIL for CPU/IO-bound work
- [ ] **Lifetimes**: Don't store references to Python objects without `Py<T>`
- [ ] **Thread safety**: Use `Arc`, `Mutex` for shared mutable state
- [ ] **Refcounts**: Let PyO3 manage (avoid manual inc/decref)
- [ ] **Panics**: Catch panics that shouldn't cross FFI boundary
- [ ] **Send + Sync**: Mark types appropriately for threading
- [ ] **Memory leaks**: Avoid circular references
- [ ] **Null pointers**: Never pass null PyObject pointers
- [ ] **Type confusion**: Use proper extraction and validation

---

## Cross-Language Debugging

### Overview

Debugging PyO3 code requires tools that understand both Python and Rust:
- **lldb**: LLVM debugger (recommended for macOS, Linux)
- **gdb/rust-gdb**: GNU debugger with Rust support
- **VS Code**: IDE integration with both languages

### Setup

#### Install Debugging Tools

```bash
# Linux
sudo apt install lldb python3-lldb  # Ubuntu/Debian
sudo dnf install lldb python3-lldb  # Fedora

# macOS (included with Xcode)
xcode-select --install

# rust-gdb (optional)
rustup component add rust-src
```

#### Configure Project for Debugging

**Cargo.toml**:
```toml
[profile.dev]
debug = true
opt-level = 0

[profile.release-with-debug]
inherits = "release"
debug = true
strip = false
```

Build with debug symbols:
```bash
# Development build (debug symbols included)
maturin develop

# Release build with debug symbols
maturin develop --profile release-with-debug
```

### lldb Basics

#### Starting lldb

```bash
# Debug Python script using Rust extension
lldb -- python test_script.py

# Attach to running Python process
lldb -p $(pgrep python)
```

#### Essential Commands

```lldb
# Run program
(lldb) run
(lldb) r

# Set breakpoints
(lldb) breakpoint set --name my_rust_function
(lldb) br s -n my_rust_function
(lldb) b src/lib.rs:42

# List breakpoints
(lldb) breakpoint list
(lldb) br list

# Continue execution
(lldb) continue
(lldb) c

# Step commands
(lldb) step      # Step into
(lldb) next      # Step over
(lldb) finish    # Step out

# Examine variables
(lldb) frame variable
(lldb) fr v
(lldb) p variable_name
(lldb) po python_object  # Print Python object

# Stack trace
(lldb) thread backtrace
(lldb) bt

# Thread management
(lldb) thread list
(lldb) thread select 2
```

### Debugging Workflow

#### Example: Debug Rust Function Called from Python

**test_debug.py**:
```python
import my_module

def main():
    print("Starting...")
    result = my_module.process_data([1, 2, 3, 4, 5])
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
```

**src/lib.rs**:
```rust
#[pyfunction]
fn process_data(data: Vec<i64>) -> i64 {
    let sum: i64 = data.iter().sum();  // Set breakpoint here
    sum * 2
}
```

**Debug session**:
```bash
$ lldb -- python test_debug.py
(lldb) breakpoint set --name process_data
Breakpoint 1: where = my_module.so`process_data + 20

(lldb) run
Process 12345 launched
Starting...
Process 12345 stopped
* thread #1, name = 'python', stop reason = breakpoint 1.1
    frame #0: my_module.so`process_data

(lldb) frame variable
(Vec<i64>) data = size=5 {
  [0] = 1
  [1] = 2
  [2] = 3
  [3] = 4
  [4] = 5
}

(lldb) next
(lldb) frame variable sum
(i64) sum = 15

(lldb) continue
Result: 30
```

#### Mixed Python/Rust Stack Traces

```lldb
(lldb) thread backtrace
* thread #1
  * frame #0: my_module.so`process_data at lib.rs:42
    frame #1: my_module.so`pyo3::impl_::pyfunction::PyFunctionDef::call_safe
    frame #2: libpython3.11.so`_PyObject_MakeTpCall
    frame #3: libpython3.11.so`_PyEval_EvalFrameDefault
    frame #4: libpython3.11.so`_PyFunction_Vectorcall
    frame #5: 0x00007ffff7a0d321 Python`main + 123 at test_debug.py:5
```

### Debugging Common Issues

#### 1. Segmentation Fault

```bash
$ lldb -- python test_crash.py
(lldb) run
Process 12345 stopped
* thread #1, stop reason = EXC_BAD_ACCESS (code=1, address=0x0)

(lldb) bt
* frame #0: my_module.so`process_data + 142
  frame #1: my_module.so`pyo3::impl_::pyfunction::PyFunctionDef::call_safe

(lldb) frame variable
(lldb) register read
```

**Common causes**:
- Null pointer dereference
- Use-after-free
- Buffer overflow
- Invalid type cast

#### 2. Python Exception from Rust

```python
# test_exception.py
try:
    my_module.may_fail("invalid")
except ValueError as e:
    import traceback
    traceback.print_exc()
```

```bash
$ lldb -- python test_exception.py
(lldb) breakpoint set --name PyErr_SetString
(lldb) run

# When breakpoint hits:
(lldb) bt
* frame #0: libpython3.11.so`PyErr_SetString
  frame #1: my_module.so`pyo3::err::PyErr::new_err
  frame #2: my_module.so`may_fail at lib.rs:67
```

#### 3. Memory Leak Detection

```bash
# Use valgrind (Linux)
valgrind --leak-check=full python test_script.py

# Use heaptrack
heaptrack python test_script.py
heaptrack_gui heaptrack.test_script.py.12345.gz
```

### VS Code Integration

**.vscode/launch.json**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Python + Rust",
      "type": "lldb",
      "request": "launch",
      "program": "${env:HOME}/.pyenv/versions/3.11.0/bin/python",
      "args": ["${file}"],
      "cwd": "${workspaceFolder}",
      "env": {
        "RUST_BACKTRACE": "1",
        "RUST_LOG": "debug"
      },
      "sourceLanguages": ["rust", "python"],
      "preLaunchTask": "maturin-develop"
    }
  ]
}
```

**.vscode/tasks.json**:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "maturin-develop",
      "type": "shell",
      "command": "maturin develop",
      "problemMatcher": [],
      "group": {
        "kind": "build",
        "isDefault": true
      }
    }
  ]
}
```

**Usage**:
1. Set breakpoints in Rust or Python code
2. Press F5 to start debugging
3. Step through code with F10 (next), F11 (step into)
4. Inspect variables in Debug sidebar

### Advanced Debugging Techniques

#### Conditional Breakpoints

```lldb
# Break only when value > 100
(lldb) breakpoint set --name process_data --condition 'data.len > 100'

# Break and run commands
(lldb) breakpoint command add 1
Enter your debugger command(s). Type 'DONE' to end.
> frame variable
> continue
> DONE
```

#### Watchpoints

```lldb
# Break when variable changes
(lldb) watchpoint set variable my_var
(lldb) watchpoint list
```

#### Core Dump Analysis

```bash
# Generate core dump
ulimit -c unlimited
python test_crash.py  # Crashes, generates core

# Analyze core dump
lldb python --core core.12345
(lldb) bt
(lldb) frame variable
```

### Debugging Best Practices

1. **Build with debug symbols**: Use dev profile or release-with-debug
2. **Add logging**: Use `log`, `env_logger` crates
3. **Use assertions**: `assert!`, `debug_assert!` for invariants
4. **Test incrementally**: Isolate problematic code
5. **Check Python tracebacks**: Often point to Rust call site
6. **Use Rust's type system**: Many bugs caught at compile time
7. **Enable backtrace**: `RUST_BACKTRACE=1` environment variable

---

## Memory Profiling

### Why Profile Memory?

- **Detect leaks**: Memory not freed after use
- **Optimize usage**: Reduce allocations, improve cache locality
- **Understand patterns**: Where memory is allocated/freed
- **Debug issues**: Unexpected memory growth

### Tools

| Tool | Platform | Use Case |
|------|----------|----------|
| valgrind/massif | Linux | Heap profiling, leak detection |
| heaptrack | Linux | Allocation tracking, GUI visualization |
| Instruments | macOS | Comprehensive profiling suite |
| py-spy | All | Python-level profiling |
| cargo-flamegraph | All | CPU profiling (shows allocations) |

### valgrind and massif

#### Install

```bash
# Ubuntu/Debian
sudo apt install valgrind

# Fedora
sudo dnf install valgrind

# macOS (limited support)
brew install valgrind
```

#### Basic Usage

**Memory leak detection**:
```bash
valgrind --leak-check=full --show-leak-kinds=all \
  python test_script.py
```

**Output**:
```
==12345== HEAP SUMMARY:
==12345==     in use at exit: 1,024 bytes in 16 blocks
==12345==   total heap usage: 1,234 allocs, 1,218 frees, 4,567,890 bytes allocated
==12345==
==12345== LEAK SUMMARY:
==12345==    definitely lost: 512 bytes in 8 blocks
==12345==    indirectly lost: 256 bytes in 4 blocks
==12345==      possibly lost: 256 bytes in 4 blocks
```

**Heap profiling with massif**:
```bash
valgrind --tool=massif --massif-out-file=massif.out \
  python test_script.py

# Visualize results
ms_print massif.out
```

**massif output**:
```
    MB
30.23^                                                    #
     |                                                   @#
     |                                          @@@@@ ::@#
     |                                         :@@@@@:::@#
20.15+                              :::::  ::::@@@@@:::@#
     |                         @ @::::::::::::::@@@@@:::@#
     |                    @@ ::@::@ :::::::::::::@@@@@:::@#
     |               @@@::@@:::@::@::::::::::::::@@@@@:::@#
10.07+          @::::@@@::@@:::@::@::::::::::::::@@@@@:::@#
     |     @@@@::::::@@@::@@:::@::@::::::::::::::@@@@@:::@#
     |  @@::@@@@::::::@@@::@@:::@::@::::::::::::::@@@@@:::@#
     | :@@::@@@@::::::@@@::@@:::@::@::::::::::::::@@@@@:::@#
 0.00+-------------------------------------------------------------------->s
     0                                                                  100
```

### heaptrack

#### Install and Use

```bash
# Install
sudo apt install heaptrack heaptrack-gui

# Run profiling
heaptrack python test_script.py

# Analyze results
heaptrack_gui heaptrack.test_script.py.12345.gz
```

**heaptrack shows**:
- Total allocations over time
- Peak memory usage
- Allocation hotspots (flamegraph)
- Temporary allocations
- Leak candidates

### macOS Instruments

```bash
# Launch Instruments
instruments -t Allocations python test_script.py

# Or use Xcode GUI
open -a Instruments
```

**Instruments features**:
- Real-time memory graphs
- Allocation call stacks
- Object lifecycle tracking
- Memory leak detection

### Python-Level Profiling (tracemalloc)

**profile_memory.py**:
```python
import tracemalloc
import my_module

def profile_function():
    # Start tracing
    tracemalloc.start()

    # Run function
    result = my_module.process_large_data([i for i in range(10**6)])

    # Get statistics
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory: {current / 10**6:.2f} MB")
    print(f"Peak memory: {peak / 10**6:.2f} MB")

    # Top allocations
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')

    print("\nTop 10 allocations:")
    for stat in top_stats[:10]:
        print(stat)

    tracemalloc.stop()

if __name__ == "__main__":
    profile_function()
```

### Rust-Level Profiling

#### jemalloc Allocator

**Cargo.toml**:
```toml
[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
jemallocator = "0.5"

[profile.release]
debug = true  # Keep symbols for profiling
```

**src/lib.rs**:
```rust
#[global_allocator]
static GLOBAL: jemallocator::Jemalloc = jemallocator::Jemalloc;

#[pyfunction]
fn allocate_test() -> Vec<u8> {
    vec![0u8; 10_000_000]  // 10 MB allocation
}
```

#### Allocation Tracking

**Custom allocator with tracking**:
```rust
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicUsize, Ordering};

struct TrackingAllocator;

static ALLOCATED: AtomicUsize = AtomicUsize::new(0);
static DEALLOCATED: AtomicUsize = AtomicUsize::new(0);

unsafe impl GlobalAlloc for TrackingAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let ret = System.alloc(layout);
        if !ret.is_null() {
            ALLOCATED.fetch_add(layout.size(), Ordering::SeqCst);
        }
        ret
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        System.dealloc(ptr, layout);
        DEALLOCATED.fetch_add(layout.size(), Ordering::SeqCst);
    }
}

#[global_allocator]
static GLOBAL: TrackingAllocator = TrackingAllocator;

#[pyfunction]
fn get_memory_stats() -> (usize, usize, usize) {
    let allocated = ALLOCATED.load(Ordering::SeqCst);
    let deallocated = DEALLOCATED.load(Ordering::SeqCst);
    let current = allocated - deallocated;
    (allocated, deallocated, current)
}
```

Python:
```python
import my_module

# Do work
my_module.process_data([1, 2, 3])

# Check stats
allocated, deallocated, current = my_module.get_memory_stats()
print(f"Allocated: {allocated / 1024 / 1024:.2f} MB")
print(f"Deallocated: {deallocated / 1024 / 1024:.2f} MB")
print(f"Current: {current / 1024 / 1024:.2f} MB")
```

### Performance Profiling with flamegraph

```bash
# Install
cargo install flamegraph

# Profile (requires root on Linux)
sudo flamegraph python test_script.py

# Opens flamegraph.svg showing hot paths
```

**Interpreting flamegraph**:
- Width = time spent (wider = more expensive)
- Vertical stacks = call hierarchy
- Color = modules (consistent across runs)

### Memory Optimization Strategies

#### 1. Reduce Allocations

```rust
// BEFORE: Allocates new vector
#[pyfunction]
fn process_items(items: Vec<i64>) -> Vec<i64> {
    items.into_iter().map(|x| x * 2).collect()
}

// AFTER: Reuse buffer
#[pyfunction]
fn process_items_inplace(mut items: Vec<i64>) -> Vec<i64> {
    for item in &mut items {
        *item *= 2;
    }
    items
}
```

#### 2. Use References

```rust
// BEFORE: Copies string
#[pyfunction]
fn count_chars(s: String) -> usize {
    s.chars().count()
}

// AFTER: Borrows string
#[pyfunction]
fn count_chars(s: &str) -> usize {
    s.chars().count()
}
```

#### 3. Avoid Intermediate Collections

```rust
// BEFORE: Multiple allocations
#[pyfunction]
fn process(items: Vec<i64>) -> i64 {
    let doubled: Vec<_> = items.iter().map(|x| x * 2).collect();
    let filtered: Vec<_> = doubled.into_iter().filter(|x| x > &10).collect();
    filtered.into_iter().sum()
}

// AFTER: Iterator chain (lazy evaluation)
#[pyfunction]
fn process(items: Vec<i64>) -> i64 {
    items.iter()
        .map(|x| x * 2)
        .filter(|x| x > &10)
        .sum()
}
```

#### 4. Pre-allocate Capacity

```rust
// BEFORE: Grows as needed (multiple allocations)
#[pyfunction]
fn generate_sequence(n: usize) -> Vec<i64> {
    let mut result = Vec::new();
    for i in 0..n {
        result.push(i as i64);
    }
    result
}

// AFTER: Pre-allocate (single allocation)
#[pyfunction]
fn generate_sequence(n: usize) -> Vec<i64> {
    let mut result = Vec::with_capacity(n);
    for i in 0..n {
        result.push(i as i64);
    }
    result
}
```

#### 5. Use Small String Optimization

```rust
use smartstring::alias::String;  // Stack-allocated for small strings

#[pyfunction]
fn make_label(id: i64) -> String {
    format!("item_{}", id).into()  // No heap allocation if < 23 bytes
}
```

### Profiling Checklist

- [ ] Identify baseline memory usage
- [ ] Profile realistic workloads
- [ ] Check for leaks (valgrind, heaptrack)
- [ ] Find allocation hotspots (flamegraph)
- [ ] Measure before/after optimization
- [ ] Test with various data sizes
- [ ] Profile both Python and Rust sides
- [ ] Check memory usage over time (long-running)

---

## Production Deployment

### Building Release Wheels

```bash
# Build for current platform
maturin build --release

# Build with specific Python versions
maturin build --release --interpreter python3.8 python3.9 python3.10 python3.11 python3.12

# Output in target/wheels/
ls target/wheels/
# my_rust_extension-0.1.0-cp311-cp311-linux_x86_64.whl
```

### Cross-Platform Builds

#### Linux (manylinux)

Use Docker for reproducible builds:

```bash
# Pull manylinux image
docker pull quay.io/pypa/manylinux2014_x86_64

# Build wheels for all Python versions
docker run --rm -v $(pwd):/io \
  quay.io/pypa/manylinux2014_x86_64 \
  bash -c "cd /io && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    source $HOME/.cargo/env && \
    pip3 install maturin && \
    maturin build --release --manylinux 2014"
```

**Automated script** (.github/workflows/build.yml):
```yaml
name: Build Wheels

on: [push, pull_request]

jobs:
  linux:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target: [x86_64, aarch64]
    steps:
      - uses: actions/checkout@v3
      - uses: PyO3/maturin-action@v1
        with:
          target: ${{ matrix.target }}
          manylinux: auto
          args: --release --out dist
      - name: Upload wheels
        uses: actions/upload-artifact@v3
        with:
          name: wheels
          path: dist
```

#### macOS

```bash
# Build universal2 wheel (x86_64 + arm64)
rustup target add x86_64-apple-darwin aarch64-apple-darwin
maturin build --release --universal2

# Or build for specific architecture
maturin build --release --target x86_64-apple-darwin
maturin build --release --target aarch64-apple-darwin
```

#### Windows

```bash
# Build on Windows
maturin build --release

# Cross-compile from Linux (requires cross-compilation setup)
rustup target add x86_64-pc-windows-gnu
maturin build --release --target x86_64-pc-windows-gnu
```

### Publishing to PyPI

```bash
# Install twine
pip install twine

# Build all wheels
maturin build --release

# Upload to TestPyPI (test first!)
twine upload --repository testpypi target/wheels/*

# Verify installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ my-rust-extension

# Upload to PyPI
twine upload target/wheels/*
```

**Automated publishing** (.github/workflows/publish.yml):
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  build-and-publish:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v3
      - uses: PyO3/maturin-action@v1
        with:
          manylinux: auto
          command: build
          args: --release --out dist
      - name: Publish to PyPI
        env:
          MATURIN_PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
        run: maturin upload --skip-existing dist/*
```

### Versioning and Compatibility

#### Semantic Versioning

Follow semver for Rust (Cargo.toml) and Python (pyproject.toml):

```toml
# Cargo.toml
[package]
version = "1.2.3"  # MAJOR.MINOR.PATCH

# pyproject.toml
[project]
version = "1.2.3"
```

- **MAJOR**: Breaking API changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

#### Python Version Support

Specify supported Python versions:

```toml
# pyproject.toml
[project]
requires-python = ">=3.8"
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
```

**Runtime version detection**:
```rust
use pyo3::Python;

#[pyfunction]
fn check_python_version(py: Python) -> (u8, u8) {
    let version = py.version_info();
    (version.major, version.minor)
}
```

### Performance Tuning

#### Compiler Optimizations

```toml
[profile.release]
opt-level = 3           # Maximum optimization
lto = "fat"             # Link-time optimization (slower build, faster runtime)
codegen-units = 1       # Single codegen unit (better optimization)
panic = "abort"         # Smaller binary, faster panics
strip = true            # Remove debug symbols
```

**Target-specific optimizations**:
```toml
[target.x86_64-unknown-linux-gnu]
rustflags = ["-C", "target-cpu=native"]  # Use CPU-specific instructions
```

#### Runtime Configuration

```bash
# Environment variables
export RUST_LOG=info              # Logging level
export RAYON_NUM_THREADS=8        # Parallel threads
export MALLOC_CONF=prof:true      # jemalloc profiling
```

### Deployment Checklist

- [ ] Build release wheels for all platforms (Linux, macOS, Windows)
- [ ] Test wheels on clean environments
- [ ] Verify Python version compatibility (3.8+)
- [ ] Run full test suite
- [ ] Check binary size (strip symbols if too large)
- [ ] Benchmark performance (compare with pure Python)
- [ ] Update CHANGELOG.md
- [ ] Tag release in git
- [ ] Upload to TestPyPI first
- [ ] Test installation from TestPyPI
- [ ] Upload to PyPI
- [ ] Create GitHub release with wheels attached
- [ ] Update documentation

---

## Best Practices

### API Design

#### 1. Use Idiomatic Python

```rust
// GOOD: Pythonic API
#[pyfunction]
#[pyo3(signature = (items, *, reverse=false))]
fn sort_items(items: Vec<i64>, reverse: bool) -> Vec<i64> {
    let mut sorted = items;
    sorted.sort();
    if reverse {
        sorted.reverse();
    }
    sorted
}

// Python usage:
// sort_items([3, 1, 2])
// sort_items([3, 1, 2], reverse=True)
```

#### 2. Accept Flexible Types

```rust
use pyo3::types::PyAny;

#[pyfunction]
fn process_number(value: &PyAny) -> PyResult<i64> {
    // Try extracting as different numeric types
    if let Ok(i) = value.extract::<i64>() {
        return Ok(i);
    }
    if let Ok(f) = value.extract::<f64>() {
        return Ok(f as i64);
    }
    if let Ok(s) = value.extract::<String>() {
        return s.parse::<i64>()
            .map_err(|e| PyValueError::new_err(format!("Invalid number: {}", e)));
    }
    Err(PyTypeError::new_err("Expected number or string"))
}
```

#### 3. Provide Good Error Messages

```rust
// GOOD
if port < 1 || port > 65535 {
    return Err(PyValueError::new_err(format!(
        "Port {} out of range (valid: 1-65535)",
        port
    )));
}

// BAD
if port < 1 || port > 65535 {
    return Err(PyValueError::new_err("Invalid port"));
}
```

#### 4. Document Your API

```rust
/// Calculate the nth Fibonacci number.
///
/// Args:
///     n: The position in the Fibonacci sequence (must be non-negative)
///
/// Returns:
///     The nth Fibonacci number
///
/// Raises:
///     ValueError: If n is negative
///
/// Examples:
///     >>> fib(0)
///     0
///     >>> fib(10)
///     55
#[pyfunction]
fn fib(n: i64) -> PyResult<i64> {
    if n < 0 {
        return Err(PyValueError::new_err("n must be non-negative"));
    }

    match n {
        0 => Ok(0),
        1 => Ok(1),
        _ => {
            let mut a = 0i64;
            let mut b = 1i64;
            for _ in 2..=n {
                let c = a + b;
                a = b;
                b = c;
            }
            Ok(b)
        }
    }
}
```

### Performance

#### 1. Profile Before Optimizing

```python
import my_module
import time

def benchmark(func, *args, iterations=1000):
    start = time.perf_counter()
    for _ in range(iterations):
        func(*args)
    end = time.perf_counter()
    return (end - start) / iterations

# Baseline (pure Python)
def pure_python_sum(items):
    return sum(x * x for x in items)

# Rust implementation
data = list(range(10000))

python_time = benchmark(pure_python_sum, data)
rust_time = benchmark(my_module.sum_squares, data)

print(f"Python: {python_time*1000:.2f} ms")
print(f"Rust: {rust_time*1000:.2f} ms")
print(f"Speedup: {python_time/rust_time:.1f}x")
```

#### 2. Release the GIL for CPU-Bound Work

```rust
#[pyfunction]
fn cpu_intensive(py: Python, n: usize) -> u64 {
    py.allow_threads(|| {
        // Expensive computation without GIL
        (0..n as u64).map(|x| x * x).sum()
    })
}
```

#### 3. Minimize Python ↔ Rust Transitions

```rust
// GOOD: Single call with batch
#[pyfunction]
fn process_batch(items: Vec<i64>) -> Vec<i64> {
    items.into_iter().map(|x| x * x).collect()
}

// BAD: Multiple calls
#[pyfunction]
fn process_single(item: i64) -> i64 {
    item * item
}

// Python:
// Good: result = my_module.process_batch(items)
// Bad: result = [my_module.process_single(x) for x in items]  # FFI overhead!
```

#### 4. Use Parallel Iterators

```rust
use rayon::prelude::*;

#[pyfunction]
fn parallel_process(py: Python, items: Vec<i64>) -> Vec<i64> {
    py.allow_threads(|| {
        items.par_iter()
            .map(|&x| expensive_computation(x))
            .collect()
    })
}

fn expensive_computation(x: i64) -> i64 {
    (0..1000).fold(x, |acc, _| acc * 2)
}
```

### Testing

#### 1. Test from Python

```python
# tests/test_my_module.py
import pytest
import my_module

def test_basic():
    assert my_module.add(2, 3) == 5

def test_error_handling():
    with pytest.raises(ValueError, match="Division by zero"):
        my_module.divide(10, 0)

def test_types():
    assert isinstance(my_module.get_dict(), dict)
    assert my_module.get_list() == [1, 2, 3]

@pytest.mark.benchmark
def test_performance(benchmark):
    result = benchmark(my_module.sum_squares, list(range(10000)))
    assert result > 0
```

#### 2. Test from Rust

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::prelude::*;

    #[test]
    fn test_add() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let result = add(py, 2, 3);
            assert_eq!(result, 5);
        });
    }

    #[test]
    fn test_error() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let result = divide(py, 10.0, 0.0);
            assert!(result.is_err());
        });
    }
}
```

### Security

#### 1. Validate Input

```rust
#[pyfunction]
fn read_file(path: String) -> PyResult<String> {
    // Prevent path traversal
    if path.contains("..") || path.contains("~") {
        return Err(PyValueError::new_err("Invalid path"));
    }

    // Whitelist allowed directories
    let allowed_dirs = ["/tmp/uploads", "/var/data"];
    let path_obj = std::path::Path::new(&path);
    let canonical = path_obj.canonicalize()
        .map_err(|e| PyIOError::new_err(format!("Invalid path: {}", e)))?;

    let allowed = allowed_dirs.iter().any(|dir| {
        canonical.starts_with(dir)
    });

    if !allowed {
        return Err(PyPermissionError::new_err("Access denied"));
    }

    std::fs::read_to_string(&path)
        .map_err(|e| PyIOError::new_err(e.to_string()))
}
```

#### 2. Limit Resource Usage

```rust
const MAX_INPUT_SIZE: usize = 10_000_000;  // 10 MB

#[pyfunction]
fn process_data(data: Vec<u8>) -> PyResult<Vec<u8>> {
    if data.len() > MAX_INPUT_SIZE {
        return Err(PyValueError::new_err(
            format!("Input too large: {} bytes (max: {})",
                    data.len(), MAX_INPUT_SIZE)
        ));
    }

    // Process data...
    Ok(data)
}
```

#### 3. Handle Untrusted Input Safely

```rust
#[pyfunction]
fn parse_json_safe(json_str: String) -> PyResult<serde_json::Value> {
    // Limit string size
    if json_str.len() > 1_000_000 {
        return Err(PyValueError::new_err("JSON too large"));
    }

    // Parse with error handling
    serde_json::from_str(&json_str)
        .map_err(|e| PyValueError::new_err(format!("Invalid JSON: {}", e)))
}
```

---

## Troubleshooting

### Common Errors

#### 1. "ImportError: dynamic module does not define module export function"

**Cause**: Missing `#[pymodule]` or module name mismatch

**Solution**:
```rust
// Ensure module name matches Cargo.toml
#[pymodule]
fn my_rust_extension(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(my_function, m)?)?;
    Ok(())
}
```

#### 2. "TypeError: function takes exactly 1 argument"

**Cause**: Python arguments don't match Rust signature

**Solution**: Check function signature and use `#[pyo3(signature = ...)]`:
```rust
#[pyfunction]
#[pyo3(signature = (a, b, c=None))]  // c is optional
fn my_func(a: i64, b: i64, c: Option<i64>) -> i64 {
    a + b + c.unwrap_or(0)
}
```

#### 3. "RuntimeError: Python GIL is not held"

**Cause**: Trying to call Python API without GIL

**Solution**:
```rust
#[pyfunction]
fn needs_gil(py: Python) {  // Add py: Python parameter
    // Now have GIL access
    let _ = py.None();
}
```

#### 4. "Segmentation fault"

**Possible causes**:
- Null pointer dereference
- Use-after-free
- Invalid type cast
- Calling Python API without GIL

**Debug**:
```bash
RUST_BACKTRACE=1 python test.py
lldb -- python test.py
```

#### 5. "ValueError: embedded null byte"

**Cause**: Rust string contains null byte (`\0`), invalid in Python strings

**Solution**:
```rust
// Check for null bytes
#[pyfunction]
fn safe_string(s: String) -> PyResult<String> {
    if s.contains('\0') {
        return Err(PyValueError::new_err("String contains null byte"));
    }
    Ok(s)
}
```

### Performance Issues

#### Slow FFI Transitions

**Problem**: Calling Rust functions in tight Python loops

```python
# SLOW: FFI overhead per call
for x in data:
    result.append(my_module.process(x))
```

**Solution**: Batch processing
```python
# FAST: Single FFI call
result = my_module.process_batch(data)
```

#### GIL Contention

**Problem**: Holding GIL during CPU-bound work

```rust
// SLOW: Holds GIL
#[pyfunction]
fn slow_computation(data: Vec<i64>) -> i64 {
    data.iter().map(|x| expensive(x)).sum()
}
```

**Solution**: Release GIL
```rust
// FAST: Releases GIL
#[pyfunction]
fn fast_computation(py: Python, data: Vec<i64>) -> i64 {
    py.allow_threads(|| {
        data.iter().map(|x| expensive(x)).sum()
    })
}
```

### Build Issues

#### "linker `cc` not found"

**Solution**:
```bash
# Ubuntu/Debian
sudo apt install build-essential

# Fedora
sudo dnf install gcc

# macOS
xcode-select --install
```

#### "Python.h: No such file or directory"

**Solution**:
```bash
# Ubuntu/Debian
sudo apt install python3-dev

# Fedora
sudo dnf install python3-devel

# macOS (via Homebrew)
brew install python
```

#### "Cannot find -lpython3.X"

**Solution**: Ensure Python library is findable
```bash
# Set PKG_CONFIG_PATH
export PKG_CONFIG_PATH=/usr/lib/pkgconfig:$PKG_CONFIG_PATH

# Or use specific Python
export PYTHON_SYS_EXECUTABLE=/usr/bin/python3.11
```

### Debugging Checklist

- [ ] Check Rust version (`rustc --version`, need 1.70+)
- [ ] Check Python version (`python --version`, need 3.8+)
- [ ] Verify maturin installation (`maturin --version`)
- [ ] Rebuild after changes (`maturin develop`)
- [ ] Check module name matches Cargo.toml
- [ ] Ensure `#[pymodule]` function name matches module
- [ ] Verify GIL is acquired when needed (add `py: Python`)
- [ ] Look for panics (`RUST_BACKTRACE=1`)
- [ ] Check for null pointer dereference (use lldb/gdb)
- [ ] Profile memory usage (valgrind, heaptrack)
- [ ] Compare debug vs release builds
- [ ] Test with different Python versions
- [ ] Verify wheel compatibility (manylinux, macOS universal)

---

## Conclusion

This reference covered:
- **Environment setup**: Rust, Python, maturin, IDE configuration
- **Project structure**: Cargo.toml, pyproject.toml, directory layout
- **Type conversion**: Primitives, collections, custom types, Result<T, E>
- **Error handling**: Python exceptions, anyhow, thiserror integration
- **FFI safety**: GIL management, memory safety, thread safety, panic handling
- **Cross-language debugging**: lldb, gdb, VS Code integration
- **Memory profiling**: valgrind, heaptrack, Instruments, allocation tracking
- **Production deployment**: Building wheels, cross-compilation, PyPI publishing
- **Best practices**: API design, performance, testing, security
- **Troubleshooting**: Common errors, performance issues, build problems

### Next Steps

1. **Build something**: Start with simple functions, gradually add complexity
2. **Profile early**: Measure to ensure PyO3 provides actual benefits
3. **Test thoroughly**: Both Python and Rust test suites
4. **Read PyO3 docs**: https://pyo3.rs/ (official guide)
5. **Study examples**: https://github.com/PyO3/pyo3/tree/main/examples
6. **Join community**: Discord, GitHub Discussions for help

### Additional Resources

- **PyO3 Guide**: https://pyo3.rs/
- **API Docs**: https://docs.rs/pyo3/
- **maturin**: https://www.maturin.rs/
- **Rust Book**: https://doc.rust-lang.org/book/
- **Python C API**: https://docs.python.org/3/c-api/

---

**Document Version**: 1.0.0
**Lines**: 3,897
**Last Updated**: 2025-10-30
