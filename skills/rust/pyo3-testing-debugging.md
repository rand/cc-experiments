---
name: pyo3-testing-debugging
description: PyO3 testing and debugging including unit tests, integration tests, property-based testing, native debugging, memory leak detection, and profiling
skill_id: rust-pyo3-testing-debugging
title: PyO3 Testing and Debugging
category: rust
subcategory: pyo3
complexity: advanced
prerequisites:
  - rust-pyo3-basics-types-conversions
  - rust-pyo3-modules-functions-errors
  - rust-pyo3-packaging-distribution
tags:
  - rust
  - python
  - pyo3
  - testing
  - debugging
  - pytest
  - proptest
  - valgrind
  - gdb
  - profiling
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Master unit testing for Rust and Python layers
  - Implement integration tests for PyO3 extensions
  - Use property-based testing with proptest
  - Debug native crashes with GDB/LLDB
  - Detect and fix memory leaks
  - Profile performance bottlenecks
  - Set up test automation and CI
  - Handle platform-specific test scenarios
related_skills:
  - rust-pyo3-packaging-distribution
  - rust-pyo3-performance-gil-parallel
  - testing-pytest-advanced
---

# PyO3 Testing and Debugging

## Overview

Master comprehensive testing and debugging strategies for PyO3 extensions. Learn to test both Rust and Python layers, debug native crashes, detect memory issues, profile performance, and set up robust test automation.

## Prerequisites

- **Required**: PyO3 basics, Rust testing fundamentals, pytest experience
- **Recommended**: GDB/LLDB experience, valgrind familiarity, profiling tools
- **Tools**: cargo test, pytest, gdb/lldb, valgrind, py-spy, flamegraph

## Learning Path

### 1. Rust-Level Unit Testing

#### Testing Pure Rust Functions

```rust
// src/lib.rs
pub fn calculate_sum(data: &[f64]) -> f64 {
    data.iter().sum()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculate_sum() {
        let data = vec![1.0, 2.0, 3.0];
        assert_eq!(calculate_sum(&data), 6.0);
    }

    #[test]
    fn test_empty_sum() {
        assert_eq!(calculate_sum(&[]), 0.0);
    }
}
```

```bash
# Run Rust tests
cargo test

# Run with output
cargo test -- --nocapture

# Run specific test
cargo test test_calculate_sum
```

#### Testing PyO3 Functions

```rust
use pyo3::prelude::*;
use pyo3::types::PyList;

#[pyfunction]
fn process_list(py: Python, items: &PyList) -> PyResult<Vec<i32>> {
    items.iter()
        .map(|item| item.extract::<i32>())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::Python;

    #[test]
    fn test_process_list() {
        Python::with_gil(|py| {
            let list = PyList::new(py, &[1, 2, 3]);
            let result = process_list(py, list).unwrap();
            assert_eq!(result, vec![1, 2, 3]);
        });
    }

    #[test]
    fn test_process_list_invalid() {
        Python::with_gil(|py| {
            let list = PyList::new(py, &["a", "b"]);
            assert!(process_list(py, list).is_err());
        });
    }
}
```

#### Testing with Fixtures

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::Python;

    fn setup_python() -> (Python<'static>, &'static GILPool) {
        // Initialize Python once for tests
        pyo3::prepare_freethreaded_python();
        let gil = GILPool::new();
        let py = gil.python();
        (py, Box::leak(Box::new(gil)))
    }

    #[test]
    fn test_with_fixture() {
        let (py, _pool) = setup_python();
        // Use py for tests
    }
}
```

### 2. Python-Level Integration Testing

#### pytest Setup

```python
# tests/conftest.py
import pytest
import my_extension

@pytest.fixture
def sample_data():
    """Provide test data."""
    return [1.0, 2.0, 3.0, 4.0, 5.0]

@pytest.fixture
def large_data():
    """Provide large dataset for performance tests."""
    return list(range(1000000))
```

```python
# tests/test_basic.py
import pytest
from my_extension import fast_sum, process_data

def test_fast_sum(sample_data):
    """Test basic sum operation."""
    result = fast_sum(sample_data)
    assert result == 15.0

def test_empty_input():
    """Test empty input handling."""
    result = fast_sum([])
    assert result == 0.0

def test_type_error():
    """Test type error handling."""
    with pytest.raises(TypeError):
        fast_sum("not a list")

def test_large_input(large_data):
    """Test with large dataset."""
    result = fast_sum(large_data)
    assert result == sum(large_data)
```

#### Parameterized Tests

```python
# tests/test_parametrized.py
import pytest
from my_extension import process_data

@pytest.mark.parametrize("input_data,expected", [
    ([1, 2, 3], {"sum": 6, "count": 3}),
    ([0], {"sum": 0, "count": 1}),
    ([], {"sum": 0, "count": 0}),
    ([1.5, 2.5], {"sum": 4.0, "count": 2}),
])
def test_process_data_cases(input_data, expected):
    """Test multiple input cases."""
    result = process_data(input_data)
    assert result["sum"] == expected["sum"]
    assert result["count"] == expected["count"]
```

### 3. Property-Based Testing

#### Using proptest in Rust

```rust
// Cargo.toml
[dev-dependencies]
proptest = "1.4"
```

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn test_sum_commutative(a in 0.0..1000.0, b in 0.0..1000.0) {
            let result1 = calculate_sum(&[a, b]);
            let result2 = calculate_sum(&[b, a]);
            assert!((result1 - result2).abs() < 1e-10);
        }

        #[test]
        fn test_sum_associative(data in prop::collection::vec(0.0..1000.0, 1..100)) {
            let sum1 = calculate_sum(&data);
            let sum2: f64 = data.iter().sum();
            assert!((sum1 - sum2).abs() < 1e-6);
        }
    }
}
```

#### Using Hypothesis in Python

```python
# tests/test_hypothesis.py
from hypothesis import given, strategies as st
from my_extension import fast_sum

@given(st.lists(st.floats(allow_nan=False, allow_infinity=False)))
def test_sum_matches_python(data):
    """Property: Rust sum should match Python sum."""
    result = fast_sum(data)
    expected = sum(data)
    assert abs(result - expected) < 1e-6

@given(st.lists(st.floats(min_value=-1e6, max_value=1e6), min_size=1))
def test_sum_positive_for_positive_data(data):
    """Property: Sum of positive numbers is positive."""
    positive_data = [abs(x) for x in data]
    result = fast_sum(positive_data)
    assert result >= 0
```

### 4. Debugging Native Crashes

#### Debug Build Configuration

```toml
# Cargo.toml
[profile.dev]
opt-level = 0
debug = true
split-debuginfo = "unpacked"  # Better debugger experience

[profile.release-with-debug]
inherits = "release"
debug = true
strip = false
```

```bash
# Build with debug symbols
cargo build

# Or use custom profile
cargo build --profile release-with-debug
```

#### Using GDB/LLDB

```bash
# Install extension with debug symbols
maturin develop

# Run Python under debugger
gdb python
(gdb) run -c "import my_extension; my_extension.crash_function()"

# Set breakpoint
(gdb) break src/lib.rs:42
(gdb) continue

# Inspect variables
(gdb) print data
(gdb) backtrace
```

**LLDB (macOS)**:
```bash
lldb python
(lldb) run -c "import my_extension; my_extension.crash_function()"

# Breakpoint
(lldb) breakpoint set --file lib.rs --line 42
(lldb) continue

# Inspect
(lldb) frame variable
(lldb) bt
```

#### Core Dump Analysis

```bash
# Enable core dumps
ulimit -c unlimited

# Run program
python crash_test.py
# Segmentation fault (core dumped)

# Analyze core dump
gdb python core
(gdb) backtrace
(gdb) frame 3
(gdb) list
```

### 5. Memory Leak Detection

#### Using Valgrind

```bash
# Run under valgrind
valgrind --leak-check=full --show-leak-kinds=all \
    python -c "import my_extension; my_extension.test_function()"

# Suppress Python's internal leaks
valgrind --suppressions=python.supp --leak-check=full \
    python test_script.py
```

**Python suppressions file** (`python.supp`):
```
{
   Python_Allocations
   Memcheck:Leak
   ...
   fun:Py_Initialize*
}
```

#### Using AddressSanitizer

```toml
# Cargo.toml
[profile.asan]
inherits = "dev"
```

```bash
# Build with ASAN
RUSTFLAGS="-Z sanitizer=address" cargo +nightly build --profile asan

# Run tests
LD_PRELOAD=$(rustc --print target-libdir)/libasan.so \
    python -c "import my_extension; my_extension.test()"
```

#### Manual Reference Counting Checks

```rust
use pyo3::prelude::*;

#[pyfunction]
fn check_refcount(py: Python, obj: &PyAny) -> usize {
    obj.get_refcnt()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_no_refcount_leak() {
        Python::with_gil(|py| {
            let list = PyList::new(py, &[1, 2, 3]);
            let initial_refcount = list.get_refcnt();

            // Do operations
            let _ = process_list(py, list).unwrap();

            // Check refcount unchanged
            assert_eq!(list.get_refcnt(), initial_refcount);
        });
    }
}
```

### 6. Performance Profiling

#### Using py-spy

```bash
# Install py-spy
pip install py-spy

# Profile running program
py-spy record -o profile.svg -- python benchmark.py

# Top-like interface
py-spy top -- python benchmark.py

# Profile specific function
py-spy record -o profile.svg --function my_extension.slow_function \
    -- python benchmark.py
```

#### Using flamegraph

```bash
# Install cargo-flamegraph
cargo install flamegraph

# Generate flamegraph
cargo flamegraph --bin my-bench

# For Python extension
py-spy record --format speedscope -o profile.json -- python benchmark.py
```

#### Using perf (Linux)

```bash
# Record performance data
perf record -g python benchmark.py

# Analyze
perf report

# Generate flamegraph
perf script | stackcollapse-perf.pl | flamegraph.pl > perf.svg
```

#### Benchmarking with criterion

```toml
# Cargo.toml
[dev-dependencies]
criterion = "0.5"

[[bench]]
name = "benchmarks"
harness = false
```

```rust
// benches/benchmarks.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use my_extension::calculate_sum;

fn bench_sum(c: &mut Criterion) {
    let data: Vec<f64> = (0..1000).map(|x| x as f64).collect();

    c.bench_function("sum_1000", |b| {
        b.iter(|| calculate_sum(black_box(&data)))
    });
}

criterion_group!(benches, bench_sum);
criterion_main!(benches);
```

```bash
# Run benchmarks
cargo bench
```

### 7. Testing Error Handling

#### Rust Error Tests

```rust
use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

#[pyfunction]
fn divide(a: f64, b: f64) -> PyResult<f64> {
    if b == 0.0 {
        Err(PyValueError::new_err("Division by zero"))
    } else {
        Ok(a / b)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_divide_by_zero() {
        Python::with_gil(|py| {
            let result = divide(10.0, 0.0);
            assert!(result.is_err());

            let err = result.unwrap_err();
            assert_eq!(
                err.to_string(),
                "ValueError: Division by zero"
            );
        });
    }
}
```

#### Python Error Tests

```python
# tests/test_errors.py
import pytest
from my_extension import divide

def test_divide_by_zero():
    """Test division by zero raises ValueError."""
    with pytest.raises(ValueError, match="Division by zero"):
        divide(10.0, 0.0)

def test_invalid_type():
    """Test invalid type raises TypeError."""
    with pytest.raises(TypeError):
        divide("10", 5)
```

### 8. Testing GIL Behavior

```rust
use pyo3::prelude::*;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gil_released() {
        use std::thread;

        Python::with_gil(|py| {
            let counter = Arc::new(AtomicUsize::new(0));
            let counter_clone = counter.clone();

            // Spawn thread that tries to acquire GIL
            let handle = thread::spawn(move || {
                Python::with_gil(|_py| {
                    counter_clone.fetch_add(1, Ordering::SeqCst);
                });
            });

            // Release GIL in current thread
            py.allow_threads(|| {
                std::thread::sleep(std::time::Duration::from_millis(100));
            });

            handle.join().unwrap();

            // Verify thread could acquire GIL
            assert_eq!(counter.load(Ordering::SeqCst), 1);
        });
    }
}
```

### 9. CI/CD Test Automation

#### GitHub Actions Workflow

**`.github/workflows/test.yml`**:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Set up Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Cache Rust
        uses: Swatinem/rust-cache@v2

      - name: Install maturin
        run: pip install maturin[patchelf]

      - name: Build
        run: maturin develop --release

      - name: Install test dependencies
        run: pip install pytest pytest-cov hypothesis

      - name: Run Rust tests
        run: cargo test

      - name: Run Python tests
        run: pytest tests/ --cov=my_extension --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt, clippy

      - name: Check formatting
        run: cargo fmt -- --check

      - name: Clippy
        run: cargo clippy -- -D warnings

      - name: Python lint
        run: |
          pip install mypy pytest
          mypy python/
          pytest --collect-only  # Validate test collection
```

### 10. Platform-Specific Testing

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[cfg(target_os = "linux")]
    fn test_linux_specific() {
        // Linux-only test
    }

    #[test]
    #[cfg(target_os = "macos")]
    fn test_macos_specific() {
        // macOS-only test
    }

    #[test]
    #[cfg(target_os = "windows")]
    fn test_windows_specific() {
        // Windows-only test
    }
}
```

```python
# tests/test_platform.py
import sys
import pytest

@pytest.mark.skipif(sys.platform != "linux", reason="Linux only")
def test_linux_feature():
    """Test Linux-specific functionality."""
    pass

@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
def test_macos_feature():
    """Test macOS-specific functionality."""
    pass
```

## Common Patterns

### Test Utilities Module

```rust
// tests/common/mod.rs
use pyo3::prelude::*;

pub fn setup_test_env() -> Python<'static> {
    pyo3::prepare_freethreaded_python();
    Python::acquire_gil().python()
}

pub fn assert_float_eq(a: f64, b: f64, epsilon: f64) {
    assert!((a - b).abs() < epsilon, "{} != {} (epsilon: {})", a, b, epsilon);
}
```

```python
# tests/utils.py
import numpy as np

def assert_arrays_equal(a, b, rtol=1e-7, atol=1e-9):
    """Assert NumPy arrays are approximately equal."""
    np.testing.assert_allclose(a, b, rtol=rtol, atol=atol)

def generate_test_data(size, seed=42):
    """Generate reproducible test data."""
    rng = np.random.default_rng(seed)
    return rng.random(size)
```

### Snapshot Testing

```python
# tests/test_snapshots.py
import pytest
from syrupy import snapshot

def test_output_format(snapshot):
    """Test output matches saved snapshot."""
    result = my_extension.format_result({"a": 1, "b": 2})
    assert result == snapshot
```

## Anti-Patterns

### ❌ Incorrect: Forgetting GIL in Tests

```rust
#[test]
fn test_without_gil() {
    let list = PyList::new(/* No Python! */);  // Crash!
}
```

### ✅ Correct: Acquire GIL

```rust
#[test]
fn test_with_gil() {
    Python::with_gil(|py| {
        let list = PyList::new(py, &[1, 2, 3]);
        // Safe!
    });
}
```

### ❌ Incorrect: No Memory Leak Tests

```rust
// Never check for leaks
#[test]
fn test_operation() {
    // Do stuff, hope it doesn't leak
}
```

### ✅ Correct: Explicit Leak Detection

```rust
#[test]
fn test_no_leaks() {
    Python::with_gil(|py| {
        let obj = create_object(py);
        let initial_refcount = obj.get_refcnt();

        do_operations(obj);

        assert_eq!(obj.get_refcnt(), initial_refcount);
    });
}
```

## Resources

### Tools
- **cargo test**: Rust testing framework
- **pytest**: Python testing framework
- **proptest**: Property-based testing for Rust
- **hypothesis**: Property-based testing for Python
- **gdb/lldb**: Native debuggers
- **valgrind**: Memory leak detection
- **py-spy**: Python profiler
- **criterion**: Rust benchmarking framework

### Documentation
- [PyO3 Testing Guide](https://pyo3.rs/latest/testing)
- [Rust Testing Book](https://rust-lang.github.io/book/ch11-00-testing.html)
- [pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)

### Related Skills
- [pyo3-packaging-distribution.md](pyo3-packaging-distribution.md)
- [pyo3-performance-gil-parallel.md](pyo3-performance-gil-parallel.md)

## Examples

See `resources/examples/` for:
1. Basic unit tests (Rust and Python)
2. Integration test suite
3. Property-based testing
4. Memory leak detection
5. Performance profiling
6. CI/CD configuration
7. Error handling tests
8. GIL behavior tests
9. Platform-specific tests
10. Advanced debugging scenarios

## Additional Resources

- **REFERENCE.md**: Comprehensive testing patterns and debugging techniques
- **Scripts**:
  - `test_runner.py`: Orchestrate test execution across platforms
  - `leak_detector.py`: Automated memory leak detection
  - `benchmark_analyzer.py`: Analyze and compare benchmark results
