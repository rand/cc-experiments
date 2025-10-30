# PyO3 Testing and Debugging - Complete Reference

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Skill**: rust-pyo3-testing-debugging

This is a comprehensive reference for testing and debugging PyO3 extensions. It covers unit testing (Rust and Python), integration testing, property-based testing, native debugging, memory leak detection, performance profiling, and CI/CD automation.

---

## Table of Contents

1. [Rust Unit Testing](#1-rust-unit-testing)
2. [Python Integration Testing](#2-python-integration-testing)
3. [Property-Based Testing](#3-property-based-testing)
4. [Native Debugging](#4-native-debugging)
5. [Memory Leak Detection](#5-memory-leak-detection)
6. [Performance Profiling](#6-performance-profiling)
7. [Error Handling Tests](#7-error-handling-tests)
8. [GIL Testing](#8-gil-testing)
9. [CI/CD Test Automation](#9-cicd-test-automation)
10. [Debugging Techniques](#10-debugging-techniques)

---

## 1. Rust Unit Testing

### 1.1 Basic Test Structure

```rust
// src/lib.rs
use pyo3::prelude::*;

// Pure Rust function (easier to test)
pub fn calculate_sum(data: &[f64]) -> f64 {
    data.iter().sum()
}

// PyO3 wrapper
#[pyfunction]
fn sum_py(data: Vec<f64>) -> f64 {
    calculate_sum(&data)
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

    #[test]
    fn test_negative_numbers() {
        let data = vec![-1.0, -2.0, -3.0];
        assert_eq!(calculate_sum(&data), -6.0);
    }
}
```

### 1.2 Testing PyO3 Functions

```rust
use pyo3::prelude::*;
use pyo3::types::{PyList, PyDict};

#[pyfunction]
fn process_list(py: Python, items: &PyList) -> PyResult<Vec<i32>> {
    items.iter()
        .map(|item| item.extract::<i32>())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

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
            let result = process_list(py, list);
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_process_empty_list() {
        Python::with_gil(|py| {
            let list = PyList::empty(py);
            let result = process_list(py, list).unwrap();
            assert_eq!(result, Vec::<i32>::new());
        });
    }
}
```

### 1.3 Testing PyClasses

```rust
use pyo3::prelude::*;

#[pyclass]
struct Counter {
    value: i32,
}

#[pymethods]
impl Counter {
    #[new]
    fn new() -> Self {
        Counter { value: 0 }
    }

    fn increment(&mut self) {
        self.value += 1;
    }

    fn get(&self) -> i32 {
        self.value
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_counter() {
        Python::with_gil(|py| {
            let mut counter = Counter::new();
            assert_eq!(counter.get(), 0);

            counter.increment();
            assert_eq!(counter.get(), 1);

            counter.increment();
            assert_eq!(counter.get(), 2);
        });
    }

    #[test]
    fn test_counter_from_python() {
        Python::with_gil(|py| {
            // Create Python instance
            let counter = Py::new(py, Counter::new()).unwrap();

            // Call methods
            counter.borrow_mut(py).increment();
            let value = counter.borrow(py).get();

            assert_eq!(value, 1);
        });
    }
}
```

### 1.4 Testing with Fixtures

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::Python;

    // Fixture: sample data
    fn sample_data() -> Vec<f64> {
        vec![1.0, 2.0, 3.0, 4.0, 5.0]
    }

    // Fixture: Python environment
    fn setup_python() -> Python<'static> {
        pyo3::prepare_freethreaded_python();
        unsafe { Python::assume_gil_acquired() }
    }

    #[test]
    fn test_with_fixture() {
        let data = sample_data();
        assert_eq!(calculate_sum(&data), 15.0);
    }

    #[test]
    fn test_with_python_fixture() {
        let py = setup_python();
        let list = PyList::new(py, &[1, 2, 3]);
        assert_eq!(list.len(), 3);
    }
}
```

### 1.5 Testing Type Conversions

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[pyfunction]
fn dict_to_struct(py: Python, dict: &PyDict) -> PyResult<MyStruct> {
    let name: String = dict.get_item("name")?.unwrap().extract()?;
    let age: i32 = dict.get_item("age")?.unwrap().extract()?;
    Ok(MyStruct { name, age })
}

#[derive(Debug, PartialEq)]
struct MyStruct {
    name: String,
    age: i32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dict_conversion() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("name", "Alice").unwrap();
            dict.set_item("age", 30).unwrap();

            let result = dict_to_struct(py, dict).unwrap();

            assert_eq!(result, MyStruct {
                name: "Alice".to_string(),
                age: 30,
            });
        });
    }

    #[test]
    fn test_dict_missing_key() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("name", "Bob").unwrap();

            let result = dict_to_struct(py, dict);
            assert!(result.is_err());
        });
    }
}
```

### 1.6 Test Organization

```rust
// src/lib.rs
pub mod calculations;
pub mod conversions;

#[cfg(test)]
mod tests {
    // Unit tests for this module
}

// tests/integration_test.rs
use my_extension::*;

#[test]
fn test_integration() {
    // Integration tests
}

// tests/common/mod.rs - Shared test utilities
use pyo3::Python;

pub fn setup() -> Python<'static> {
    pyo3::prepare_freethreaded_python();
    unsafe { Python::assume_gil_acquired() }
}

pub fn assert_approx_eq(a: f64, b: f64, epsilon: f64) {
    assert!((a - b).abs() < epsilon);
}
```

### 1.7 Running Rust Tests

```bash
# Run all tests
cargo test

# Run tests with output
cargo test -- --nocapture

# Run specific test
cargo test test_calculate_sum

# Run tests matching pattern
cargo test sum

# Run tests in parallel (default)
cargo test

# Run tests sequentially
cargo test -- --test-threads=1

# Show test execution time
cargo test -- --show-output

# Run ignored tests
cargo test -- --ignored

# Run doc tests
cargo test --doc
```

---

## 2. Python Integration Testing

### 2.1 pytest Setup

```python
# tests/conftest.py
import pytest
import my_extension

@pytest.fixture
def sample_data():
    """Provide sample test data."""
    return [1.0, 2.0, 3.0, 4.0, 5.0]

@pytest.fixture
def large_data():
    """Provide large dataset for performance tests."""
    return list(range(1_000_000))

@pytest.fixture(scope="module")
def module_data():
    """Module-scoped fixture (runs once per module)."""
    return {"key": "value"}

@pytest.fixture(scope="session")
def session_setup():
    """Session-scoped fixture (runs once)."""
    print("Session setup")
    yield
    print("Session teardown")
```

### 2.2 Basic Tests

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

def test_single_element():
    """Test single element."""
    result = fast_sum([42.0])
    assert result == 42.0

def test_negative_numbers():
    """Test with negative numbers."""
    result = fast_sum([-1.0, -2.0, -3.0])
    assert result == -6.0

def test_mixed_numbers():
    """Test with mixed positive and negative."""
    result = fast_sum([1.0, -2.0, 3.0, -4.0])
    assert result == -2.0
```

### 2.3 Parametrized Tests

```python
# tests/test_parametrized.py
import pytest
from my_extension import process_data

@pytest.mark.parametrize("input_data,expected_sum,expected_count", [
    ([1, 2, 3], 6, 3),
    ([0], 0, 1),
    ([], 0, 0),
    ([1.5, 2.5], 4.0, 2),
    ([-1, -2, -3], -6, 3),
])
def test_process_data_cases(input_data, expected_sum, expected_count):
    """Test multiple input cases."""
    result = process_data(input_data)
    assert result["sum"] == expected_sum
    assert result["count"] == expected_count

@pytest.mark.parametrize("size", [10, 100, 1000, 10000])
def test_different_sizes(size):
    """Test with different data sizes."""
    data = list(range(size))
    result = process_data(data)
    assert result["count"] == size
```

### 2.4 Error Testing

```python
# tests/test_errors.py
import pytest
from my_extension import divide, process_data

def test_divide_by_zero():
    """Test division by zero raises ValueError."""
    with pytest.raises(ValueError, match="Division by zero"):
        divide(10.0, 0.0)

def test_invalid_type():
    """Test invalid type raises TypeError."""
    with pytest.raises(TypeError):
        divide("10", 5)

def test_overflow():
    """Test overflow handling."""
    with pytest.raises(OverflowError):
        divide(1e308, 1e-308)

def test_error_message_content():
    """Test error message contains helpful info."""
    with pytest.raises(ValueError) as exc_info:
        divide(10.0, 0.0)

    assert "Division by zero" in str(exc_info.value)
    assert "denominator must be non-zero" in str(exc_info.value).lower()
```

### 2.5 Fixture Composition

```python
# tests/conftest.py
import pytest

@pytest.fixture
def database():
    """Provide database connection."""
    db = {"data": {}}
    return db

@pytest.fixture
def populated_database(database):
    """Database with sample data."""
    database["data"]["users"] = [{"id": 1, "name": "Alice"}]
    return database

# tests/test_database.py
def test_empty_database(database):
    assert database["data"] == {}

def test_populated_database(populated_database):
    assert len(populated_database["data"]["users"]) == 1
```

### 2.6 Testing with NumPy

```python
# tests/test_numpy.py
import pytest
import numpy as np
from my_extension import numpy_sum

def test_numpy_array():
    """Test with NumPy array."""
    arr = np.array([1.0, 2.0, 3.0])
    result = numpy_sum(arr)
    assert result == 6.0

def test_numpy_2d():
    """Test with 2D array."""
    arr = np.array([[1.0, 2.0], [3.0, 4.0]])
    result = numpy_sum(arr)
    assert result == 10.0

def test_numpy_types():
    """Test different NumPy dtypes."""
    for dtype in [np.float32, np.float64, np.int32, np.int64]:
        arr = np.array([1, 2, 3], dtype=dtype)
        result = numpy_sum(arr)
        assert result == 6
```

### 2.7 Mocking and Patching

```python
# tests/test_mocking.py
import pytest
from unittest.mock import patch, MagicMock
from my_extension import fetch_data_and_process

@patch('my_extension.fetch_data')
def test_with_mocked_fetch(mock_fetch):
    """Test with mocked external dependency."""
    mock_fetch.return_value = [1, 2, 3]

    result = fetch_data_and_process()

    assert result["sum"] == 6
    mock_fetch.assert_called_once()

@patch('my_extension.logger')
def test_logging(mock_logger):
    """Test that logging occurs."""
    process_data([1, 2, 3])

    mock_logger.info.assert_called()
```

### 2.8 pytest Configuration

```ini
# pytest.ini
[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=my_extension
    --cov-report=html
    --cov-report=term-missing
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks integration tests
    unit: marks unit tests
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
]
```

---

## 3. Property-Based Testing

### 3.1 proptest (Rust)

```toml
# Cargo.toml
[dev-dependencies]
proptest = "1.4"
```

```rust
use proptest::prelude::*;

#[cfg(test)]
mod tests {
    use super::*;

    proptest! {
        #[test]
        fn test_sum_commutative(a in 0.0..1000.0, b in 0.0..1000.0) {
            let sum1 = calculate_sum(&[a, b]);
            let sum2 = calculate_sum(&[b, a]);
            assert!((sum1 - sum2).abs() < 1e-10);
        }

        #[test]
        fn test_sum_associative(
            a in 0.0..1000.0,
            b in 0.0..1000.0,
            c in 0.0..1000.0
        ) {
            let sum1 = calculate_sum(&[a + b, c]);
            let sum2 = calculate_sum(&[a, b + c]);
            assert!((sum1 - sum2).abs() < 1e-6);
        }

        #[test]
        fn test_sum_identity(data in prop::collection::vec(0.0..1000.0, 0..100)) {
            let sum = calculate_sum(&data);
            let sum_with_zero = calculate_sum(&[data, vec![0.0]].concat());
            assert!((sum - sum_with_zero).abs() < 1e-10);
        }
    }
}
```

### 3.2 Custom Strategies

```rust
use proptest::prelude::*;

// Custom strategy for valid email addresses
prop_compose! {
    fn email_strategy()(
        name in "[a-z]{3,10}",
        domain in "[a-z]{3,8}",
        tld in "(com|org|net)"
    ) -> String {
        format!("{}@{}.{}", name, domain, tld)
    }
}

proptest! {
    #[test]
    fn test_email_validation(email in email_strategy()) {
        assert!(validate_email(&email));
    }
}
```

### 3.3 Hypothesis (Python)

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
def test_sum_non_negative_for_positive_data(data):
    """Property: Sum of positive numbers is non-negative."""
    positive_data = [abs(x) for x in data]
    result = fast_sum(positive_data)
    assert result >= 0

@given(st.lists(st.integers(), min_size=0, max_size=100))
def test_process_preserves_length(data):
    """Property: Processing preserves list length."""
    result = process_data(data)
    assert result["count"] == len(data)
```

### 3.4 Stateful Testing

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize

class CounterStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.counter = Counter()
        self.model = 0

    @rule()
    def increment(self):
        self.counter.increment()
        self.model += 1
        assert self.counter.get() == self.model

    @rule()
    def reset(self):
        self.counter.reset()
        self.model = 0
        assert self.counter.get() == self.model

TestCounter = CounterStateMachine.TestCase
```

---

## 4. Native Debugging

### 4.1 Debug Configuration

```toml
# Cargo.toml
[profile.dev]
opt-level = 0
debug = true
split-debuginfo = "unpacked"  # macOS/Linux

[profile.release-with-debug]
inherits = "release"
debug = true
strip = false
lto = false  # Faster builds, easier debugging
```

```bash
# Build with debug symbols
cargo build

# Build release with debug info
cargo build --profile release-with-debug

# Install with debug
maturin develop
```

### 4.2 GDB Setup

```bash
# Install GDB
# Ubuntu: apt-get install gdb
# macOS: brew install gdb (requires codesigning)

# Run Python under GDB
gdb python
(gdb) run -c "import my_extension; my_extension.test_function()"

# Set breakpoint
(gdb) break src/lib.rs:42
(gdb) break my_extension::process_data

# Run to breakpoint
(gdb) continue

# Inspect variables
(gdb) print data
(gdb) print *data
(gdb) print data[0]

# Show backtrace
(gdb) backtrace
(gdb) bt

# Navigate frames
(gdb) frame 3
(gdb) up
(gdb) down

# Step through code
(gdb) next      # Next line
(gdb) step      # Step into function
(gdb) finish    # Finish current function

# Watch variable
(gdb) watch my_var

# Conditional breakpoint
(gdb) break lib.rs:42 if size > 1000
```

### 4.3 LLDB Setup (macOS)

```bash
# Run Python under LLDB
lldb python
(lldb) run -c "import my_extension; my_extension.test_function()"

# Set breakpoint
(lldb) breakpoint set --file lib.rs --line 42
(lldb) br s -f lib.rs -l 42
(lldb) br s -n process_data

# List breakpoints
(lldb) breakpoint list

# Run to breakpoint
(lldb) continue
(lldb) c

# Inspect variables
(lldb) frame variable
(lldb) fr v
(lldb) print data
(lldb) p data[0]

# Backtrace
(lldb) thread backtrace
(lldb) bt

# Navigate frames
(lldb) frame select 3
(lldb) up
(lldb) down

# Step through
(lldb) next
(lldb) n
(lldb) step
(lldb) s
(lldb) finish
```

### 4.4 Core Dump Analysis

```bash
# Enable core dumps
ulimit -c unlimited

# Set core pattern (Linux)
echo "core.%e.%p" | sudo tee /proc/sys/kernel/core_pattern

# Run program (crashes)
python crash_test.py
# Segmentation fault (core dumped)

# Analyze core dump
gdb python core.python.12345
(gdb) backtrace
(gdb) frame 3
(gdb) list
(gdb) print variable_name

# Or with LLDB
lldb python -c core.python.12345
(lldb) bt
(lldb) frame select 3
```

### 4.5 Debugging Mixed Stacks

```bash
# GDB pretty-printing for Rust
cat > ~/.gdbinit <<EOF
set auto-load safe-path /
set print pretty on
set print object on
set print static-members on
EOF

# Debug Python and Rust together
gdb python
(gdb) run -c "import my_extension; my_extension.crash_function()"
(gdb) bt

# Example output:
# #0  my_extension::calculate_sum (data=0x7f...)
# #1  my_extension::_core::sum_py (...)
# #2  PyObject_Call (...)
# #3  PyEval_EvalFrameDefault (...)
```

---

## 5. Memory Leak Detection

### 5.1 Valgrind Usage

```bash
# Install valgrind
# Ubuntu: apt-get install valgrind
# macOS: brew install valgrind

# Run with leak check
valgrind --leak-check=full \
         --show-leak-kinds=all \
         --track-origins=yes \
         python -c "import my_extension; my_extension.test_function()"

# Detailed output
valgrind --leak-check=full \
         --show-leak-kinds=all \
         --track-origins=yes \
         --log-file=valgrind.log \
         python test_script.py

# Suppress Python's internal allocations
valgrind --suppressions=python.supp \
         --leak-check=full \
         python test_script.py
```

**Python suppressions** (`python.supp`):
```
{
   Python_Internal_Allocations
   Memcheck:Leak
   match-leak-kinds: definite
   ...
   fun:Py_Initialize*
}

{
   Python_Dict_Allocations
   Memcheck:Leak
   ...
   fun:PyDict_*
}
```

### 5.2 AddressSanitizer (ASAN)

```bash
# Build with ASAN (nightly Rust required)
RUSTFLAGS="-Z sanitizer=address" cargo +nightly build --target x86_64-unknown-linux-gnu

# Run with ASAN
LD_PRELOAD=$(rustc --print target-libdir)/libasan.so \
    python -c "import my_extension; my_extension.test()"

# Or set environment
export ASAN_OPTIONS=detect_leaks=1:abort_on_error=1
python test_script.py
```

### 5.3 LeakSanitizer (LSAN)

```bash
# Enable LSAN (part of ASAN)
export LSAN_OPTIONS=verbosity=1:log_threads=1

# Run tests
cargo test

# Suppress known leaks
export LSAN_OPTIONS=suppressions=lsan.supp

# lsan.supp
leak:python_internal_function
leak:libpython*
```

### 5.4 Reference Counting Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_no_refcount_leak() {
        Python::with_gil(|py| {
            let list = PyList::new(py, &[1, 2, 3]);
            let initial_refcount = list.get_refcnt();

            // Perform operations
            let _ = process_list(py, list).unwrap();

            // Verify refcount unchanged
            assert_eq!(list.get_refcnt(), initial_refcount);
        });
    }

    #[test]
    fn test_object_lifecycle() {
        Python::with_gil(|py| {
            let obj = create_python_object(py).unwrap();
            let initial_refcount = obj.get_refcnt();

            {
                let _borrowed = obj.borrow(py);
                // Refcount should increase
                assert!(obj.get_refcnt() > initial_refcount);
            }

            // Refcount should return to initial
            assert_eq!(obj.get_refcnt(), initial_refcount);
        });
    }
}
```

### 5.5 Manual Leak Detection

```rust
use std::sync::atomic::{AtomicUsize, Ordering};

static ALLOCATION_COUNT: AtomicUsize = AtomicUsize::new(0);
static DEALLOCATION_COUNT: AtomicUsize = AtomicUsize::new(0);

#[pyclass]
struct TrackedObject {
    data: Vec<u8>,
}

impl TrackedObject {
    fn new(size: usize) -> Self {
        ALLOCATION_COUNT.fetch_add(1, Ordering::SeqCst);
        TrackedObject {
            data: vec![0; size],
        }
    }
}

impl Drop for TrackedObject {
    fn drop(&mut self) {
        DEALLOCATION_COUNT.fetch_add(1, Ordering::SeqCst);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_no_leaks() {
        let before_alloc = ALLOCATION_COUNT.load(Ordering::SeqCst);
        let before_dealloc = DEALLOCATION_COUNT.load(Ordering::SeqCst);

        {
            let _obj = TrackedObject::new(1024);
        }

        let after_alloc = ALLOCATION_COUNT.load(Ordering::SeqCst);
        let after_dealloc = DEALLOCATION_COUNT.load(Ordering::SeqCst);

        assert_eq!(after_alloc - before_alloc, after_dealloc - before_dealloc);
    }
}
```

---

## 6. Performance Profiling

### 6.1 py-spy Usage

```bash
# Install py-spy
pip install py-spy

# Record profile
py-spy record -o profile.svg -- python benchmark.py

# Top-like interface (live profiling)
py-spy top -- python benchmark.py

# Profile running process
py-spy top --pid 12345

# Record to speedscope format
py-spy record --format speedscope -o profile.json -- python benchmark.py

# Profile specific function
py-spy record -o profile.svg --function my_extension.slow_function -- python benchmark.py

# Native symbols (Rust functions)
py-spy record --native -o profile.svg -- python benchmark.py

# Sample at higher rate
py-spy record --rate 1000 -o profile.svg -- python benchmark.py
```

### 6.2 flamegraph Generation

```bash
# Install cargo-flamegraph
cargo install flamegraph

# Generate flamegraph for Rust code
cargo flamegraph --bin my-bench

# For Python extension
py-spy record --format speedscope -o profile.json -- python benchmark.py

# Open in speedscope.app
open profile.json

# Or convert to SVG
inferno-flamegraph < profile.txt > flame.svg
```

### 6.3 perf (Linux)

```bash
# Record performance data
perf record -g python benchmark.py

# Analyze
perf report

# Generate flamegraph
perf script | stackcollapse-perf.pl | flamegraph.pl > perf.svg

# Record specific events
perf record -e cpu-clock -g python benchmark.py

# Record with call graph
perf record --call-graph dwarf python benchmark.py
```

### 6.4 criterion Benchmarking

```toml
# Cargo.toml
[dev-dependencies]
criterion = { version = "0.5", features = ["html_reports"] }

[[bench]]
name = "benchmarks"
harness = false
```

```rust
// benches/benchmarks.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use my_extension::calculate_sum;

fn bench_sum(c: &mut Criterion) {
    let data: Vec<f64> = (0..1000).map(|x| x as f64).collect();

    c.bench_function("sum_1000", |b| {
        b.iter(|| calculate_sum(black_box(&data)))
    });
}

fn bench_sum_sizes(c: &mut Criterion) {
    let mut group = c.benchmark_group("sum_sizes");

    for size in [100, 1000, 10000].iter() {
        let data: Vec<f64> = (0..*size).map(|x| x as f64).collect();

        group.bench_with_input(BenchmarkId::from_parameter(size), size, |b, _| {
            b.iter(|| calculate_sum(black_box(&data)))
        });
    }

    group.finish();
}

criterion_group!(benches, bench_sum, bench_sum_sizes);
criterion_main!(benches);
```

```bash
# Run benchmarks
cargo bench

# Open HTML report
open target/criterion/report/index.html

# Compare with baseline
cargo bench --save-baseline baseline
# ... make changes ...
cargo bench --baseline baseline
```

### 6.5 pytest-benchmark

```python
# Install
pip install pytest-benchmark

# tests/test_benchmark.py
import pytest
from my_extension import fast_sum

def test_benchmark_sum(benchmark):
    """Benchmark sum operation."""
    data = list(range(1000))
    result = benchmark(fast_sum, data)
    assert result == sum(data)

@pytest.mark.parametrize("size", [100, 1000, 10000])
def test_benchmark_sizes(benchmark, size):
    """Benchmark different sizes."""
    data = list(range(size))
    benchmark(fast_sum, data)

# Run benchmarks
pytest tests/test_benchmark.py --benchmark-only

# Compare benchmarks
pytest --benchmark-compare=0001

# Save benchmark
pytest --benchmark-save=baseline
```

---

## 7. Error Handling Tests

### 7.1 Rust Error Tests

```rust
use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyTypeError};

#[pyfunction]
fn divide(a: f64, b: f64) -> PyResult<f64> {
    if b == 0.0 {
        Err(PyValueError::new_err("Division by zero"))
    } else if b.is_nan() || a.is_nan() {
        Err(PyValueError::new_err("NaN not allowed"))
    } else {
        Ok(a / b)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_divide_success() {
        Python::with_gil(|py| {
            let result = divide(10.0, 2.0).unwrap();
            assert_eq!(result, 5.0);
        });
    }

    #[test]
    fn test_divide_by_zero() {
        Python::with_gil(|py| {
            let result = divide(10.0, 0.0);
            assert!(result.is_err());

            let err = result.unwrap_err();
            assert!(err.is_instance::<PyValueError>(py));
        });
    }

    #[test]
    fn test_error_message() {
        Python::with_gil(|py| {
            let result = divide(10.0, 0.0);
            let err = result.unwrap_err();
            let msg = err.to_string();
            assert!(msg.contains("Division by zero"));
        });
    }
}
```

### 7.2 Python Exception Tests

```python
# tests/test_exceptions.py
import pytest
from my_extension import divide

def test_divide_success():
    assert divide(10.0, 2.0) == 5.0

def test_divide_by_zero():
    with pytest.raises(ValueError, match="Division by zero"):
        divide(10.0, 0.0)

def test_nan_error():
    with pytest.raises(ValueError, match="NaN not allowed"):
        divide(float('nan'), 1.0)

def test_exception_type():
    with pytest.raises(ValueError):
        divide(10.0, 0.0)

def test_exception_attributes():
    with pytest.raises(ValueError) as exc_info:
        divide(10.0, 0.0)

    assert "zero" in str(exc_info.value).lower()
    assert exc_info.type is ValueError
```

### 7.3 Custom Exception Types

```rust
use pyo3::prelude::*;
use pyo3::create_exception;

create_exception!(my_extension, MyCustomError, pyo3::exceptions::PyException);

#[pyfunction]
fn risky_operation() -> PyResult<()> {
    Err(MyCustomError::new_err("Something went wrong"))
}

#[pymodule]
fn _core(py: Python, m: &PyModule) -> PyResult<()> {
    m.add("MyCustomError", py.get_type::<MyCustomError>())?;
    m.add_function(wrap_pyfunction!(risky_operation, m)?)?;
    Ok(())
}
```

```python
# tests/test_custom_exceptions.py
import pytest
from my_extension import risky_operation, MyCustomError

def test_custom_exception():
    with pytest.raises(MyCustomError):
        risky_operation()

def test_exception_hierarchy():
    assert issubclass(MyCustomError, Exception)
```

---

## 8. GIL Testing

### 8.1 GIL Release Tests

```rust
use pyo3::prelude::*;
use std::thread;
use std::time::Duration;

#[pyfunction]
fn long_computation(py: Python, duration_ms: u64) -> u64 {
    py.allow_threads(|| {
        thread::sleep(Duration::from_millis(duration_ms));
        42
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gil_released() {
        use std::sync::Arc;
        use std::sync::atomic::{AtomicBool, Ordering};

        Python::with_gil(|py| {
            let flag = Arc::new(AtomicBool::new(false));
            let flag_clone = flag.clone();

            // Spawn thread that needs GIL
            let handle = thread::spawn(move || {
                Python::with_gil(|_py| {
                    flag_clone.store(true, Ordering::SeqCst);
                });
            });

            // Release GIL in main thread
            py.allow_threads(|| {
                thread::sleep(Duration::from_millis(100));
            });

            handle.join().unwrap();

            // Verify thread acquired GIL
            assert!(flag.load(Ordering::SeqCst));
        });
    }
}
```

### 8.2 GIL Contention Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::sync::atomic::{AtomicUsize, Ordering};

    #[test]
    fn test_gil_contention() {
        let counter = Arc::new(AtomicUsize::new(0));
        let mut handles = vec![];

        for _ in 0..4 {
            let counter_clone = counter.clone();
            let handle = thread::spawn(move || {
                Python::with_gil(|py| {
                    // Simulate work
                    py.allow_threads(|| {
                        thread::sleep(Duration::from_millis(10));
                    });

                    counter_clone.fetch_add(1, Ordering::SeqCst);
                });
            });
            handles.push(handle);
        }

        for handle in handles {
            handle.join().unwrap();
        }

        assert_eq!(counter.load(Ordering::SeqCst), 4);
    }
}
```

### 8.3 Deadlock Detection

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    #[should_panic(expected = "timeout")]
    fn test_no_deadlock() {
        Python::with_gil(|py| {
            let handle = thread::spawn(|| {
                // This will deadlock if GIL not released
                Python::with_gil(|_py| {
                    // ...
                });
            });

            // Release GIL
            py.allow_threads(|| {
                if handle.join_timeout(Duration::from_secs(1)).is_err() {
                    panic!("timeout - possible deadlock");
                }
            });
        });
    }
}
```

---

## 9. CI/CD Test Automation

### 9.1 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
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
        with:
          key: ${{ matrix.os }}-${{ matrix.python-version }}

      - name: Install maturin
        run: pip install maturin[patchelf]

      - name: Build extension
        run: maturin develop --release

      - name: Install test dependencies
        run: |
          pip install pytest pytest-cov pytest-benchmark hypothesis

      - name: Run Rust tests
        run: cargo test --release

      - name: Run Python tests
        run: |
          pytest tests/ \
            --cov=my_extension \
            --cov-report=xml \
            --cov-report=term-missing \
            --benchmark-skip

      - name: Upload coverage
        if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.11'
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
        run: cargo clippy --all-targets --all-features -- -D warnings

      - name: Python lint
        run: |
          pip install mypy pytest ruff
          ruff check python/
          mypy python/
          pytest --collect-only tests/

  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - uses: dtolnay/rust-toolchain@stable

      - name: Install dependencies
        run: |
          pip install maturin pytest-benchmark
          maturin develop --release

      - name: Run benchmarks
        run: pytest tests/ --benchmark-only --benchmark-json=output.json

      - name: Store benchmark result
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: output.json
          github-token: ${{ secrets.GITHUB_TOKEN }}
          auto-push: true
```

### 9.2 Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
branch = true
parallel = true
source = ["python/my_extension"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

### 9.3 Test Matrix Strategy

```yaml
# .github/workflows/test-matrix.yml
strategy:
  matrix:
    include:
      # Linux
      - os: ubuntu-latest
        python: '3.11'
        rust: stable

      # macOS Intel
      - os: macos-13
        python: '3.11'
        rust: stable

      # macOS ARM
      - os: macos-14
        python: '3.11'
        rust: stable

      # Windows
      - os: windows-latest
        python: '3.11'
        rust: stable

      # Minimum supported versions
      - os: ubuntu-latest
        python: '3.8'
        rust: '1.70'
```

---

## 10. Debugging Techniques

### 10.1 Print Debugging

```rust
// Development only
#[cfg(debug_assertions)]
macro_rules! debug_print {
    ($($arg:tt)*) => {
        eprintln!("[DEBUG] {}", format!($($arg)*));
    }
}

#[cfg(not(debug_assertions))]
macro_rules! debug_print {
    ($($arg:tt)*) => {};
}

#[pyfunction]
fn process_data(data: Vec<f64>) -> f64 {
    debug_print!("Processing {} elements", data.len());

    let result = data.iter().sum();

    debug_print!("Result: {}", result);

    result
}
```

### 10.2 Logging

```toml
# Cargo.toml
[dependencies]
log = "0.4"
env_logger = "0.11"
```

```rust
use log::{debug, info, warn, error};

#[pyfunction]
fn process_with_logging(data: Vec<f64>) -> f64 {
    info!("Starting processing of {} elements", data.len());

    if data.is_empty() {
        warn!("Empty data provided");
        return 0.0;
    }

    debug!("First element: {}", data[0]);

    let result: f64 = data.iter().sum();

    info!("Processing complete, result: {}", result);

    result
}

// Initialize in module
#[pymodule]
fn _core(_py: Python, m: &PyModule) -> PyResult<()> {
    env_logger::init();
    m.add_function(wrap_pyfunction!(process_with_logging, m)?)?;
    Ok(())
}
```

```bash
# Run with logging
RUST_LOG=debug python -c "import my_extension; my_extension.process([1,2,3])"
```

### 10.3 Assertions and Debug Checks

```rust
#[pyfunction]
fn process_checked(data: Vec<f64>) -> PyResult<f64> {
    debug_assert!(!data.is_empty(), "Data should not be empty");

    if cfg!(debug_assertions) {
        // Extra checks in debug builds
        for (i, &value) in data.iter().enumerate() {
            assert!(value.is_finite(), "Non-finite value at index {}", i);
        }
    }

    Ok(data.iter().sum())
}
```

### 10.4 Runtime Validation

```rust
#[pyfunction]
fn safe_process(py: Python, data: Vec<f64>) -> PyResult<f64> {
    // Validate input
    if data.is_empty() {
        return Err(PyValueError::new_err("Data cannot be empty"));
    }

    if data.len() > 1_000_000 {
        return Err(PyValueError::new_err("Data too large"));
    }

    // Check for invalid values
    for (i, &value) in data.iter().enumerate() {
        if !value.is_finite() {
            return Err(PyValueError::new_err(format!(
                "Invalid value at index {}: {}",
                i, value
            )));
        }
    }

    py.allow_threads(|| {
        Ok(data.iter().sum())
    })
}
```

### 10.5 Conditional Compilation

```rust
#[cfg(debug_assertions)]
fn expensive_validation(data: &[f64]) {
    // Only in debug builds
    for window in data.windows(2) {
        assert!(window[0] <= window[1], "Data not sorted");
    }
}

#[cfg(not(debug_assertions))]
fn expensive_validation(_data: &[f64]) {
    // No-op in release
}

#[pyfunction]
fn process_sorted(data: Vec<f64>) -> f64 {
    expensive_validation(&data);
    data.iter().sum()
}
```

---

## Appendix: Quick Reference

### Cargo Test Commands

```bash
# Run all tests
cargo test

# Run specific test
cargo test test_name

# Run tests with output
cargo test -- --nocapture

# Run tests in parallel (default)
cargo test -- --test-threads=4

# Run doc tests
cargo test --doc

# Run benchmarks
cargo bench
```

### pytest Commands

```bash
# Run all tests
pytest

# Run specific file
pytest tests/test_basic.py

# Run specific test
pytest tests/test_basic.py::test_function

# Run with coverage
pytest --cov=my_extension --cov-report=html

# Run benchmarks
pytest --benchmark-only

# Run with output
pytest -v -s

# Run marked tests
pytest -m slow
pytest -m "not slow"
```

### GDB/LLDB Commands

```bash
# GDB
gdb python
(gdb) run -c "import my_extension; my_extension.test()"
(gdb) break src/lib.rs:42
(gdb) continue
(gdb) backtrace
(gdb) print variable
(gdb) next
(gdb) step

# LLDB
lldb python
(lldb) run -c "import my_extension; my_extension.test()"
(lldb) br s -f lib.rs -l 42
(lldb) c
(lldb) bt
(lldb) fr v
(lldb) n
(lldb) s
```

---

## Summary

This reference covers:

1. **Rust Unit Testing**: Testing Rust functions and PyO3 bindings
2. **Python Integration Testing**: pytest setup, fixtures, parametrization
3. **Property-Based Testing**: proptest and Hypothesis
4. **Native Debugging**: GDB, LLDB, core dumps
5. **Memory Leak Detection**: Valgrind, ASAN, LSAN, reference counting
6. **Performance Profiling**: py-spy, flamegraph, perf, criterion
7. **Error Handling**: Testing Rust errors and Python exceptions
8. **GIL Testing**: Verifying GIL release and contention
9. **CI/CD Automation**: GitHub Actions workflows
10. **Debugging Techniques**: Logging, assertions, validation

For more information, see:
- [PyO3 Testing Guide](https://pyo3.rs/latest/testing)
- [Rust Testing Book](https://rust-lang.github.io/book/ch11-00-testing.html)
- [pytest Documentation](https://docs.pytest.org/)
