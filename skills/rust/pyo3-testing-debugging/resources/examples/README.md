# PyO3 Testing and Debugging Examples

Complete set of progressive examples demonstrating testing and debugging patterns for PyO3 extensions.

## Overview

This collection contains 10 runnable examples that progressively build testing and debugging expertise:

- **Beginner (01-03)**: Basic testing patterns
- **Intermediate (04-07)**: Advanced testing techniques
- **Advanced (08-10)**: Production-ready patterns

## Examples

### Beginner Level

#### [01. Rust Unit Tests](01_rust_unit_tests/)
**Complexity**: Beginner | **Lines**: ~150

Basic Rust unit testing for PyO3 functions.

**Key Concepts**:
- Testing pure Rust functions
- Testing PyO3 functions with GIL
- Error condition testing
- Running tests with cargo

**Run**:
```bash
cd 01_rust_unit_tests
cargo test
```

---

#### [02. Python Integration Tests](02_python_tests/)
**Complexity**: Beginner | **Lines**: ~200

Python-side testing with pytest, fixtures, and parameterized tests.

**Key Concepts**:
- pytest fixtures
- Parameterized testing
- Coverage reporting
- Testing edge cases

**Run**:
```bash
cd 02_python_tests
maturin develop
pytest tests/ -v
```

---

#### [03. Error Testing](03_error_testing/)
**Complexity**: Beginner | **Lines**: ~250

Comprehensive error handling and exception testing.

**Key Concepts**:
- PyResult error handling
- Custom exception classes
- Error propagation
- Testing exception types and messages

**Run**:
```bash
cd 03_error_testing
maturin develop
pytest tests/ -v
```

---

### Intermediate Level

#### [04. Property Testing](04_property_testing/)
**Complexity**: Intermediate | **Lines**: ~200

Property-based testing with proptest and hypothesis.

**Key Concepts**:
- Proptest in Rust
- Hypothesis in Python
- Automatic edge case discovery
- Invariant verification

**Run**:
```bash
cd 04_property_testing
cargo test  # Rust property tests
maturin develop
pytest tests/ -v  # Python property tests
```

---

#### [05. Benchmarking](05_benchmarking/)
**Complexity**: Intermediate | **Lines**: ~220

Performance benchmarking with criterion and pytest-benchmark.

**Key Concepts**:
- Criterion benchmarks (Rust)
- pytest-benchmark (Python)
- Performance comparison
- Regression detection

**Run**:
```bash
cd 05_benchmarking
cargo bench  # Rust benchmarks
maturin develop --release
pytest tests/ --benchmark-only  # Python benchmarks
```

---

#### [06. Memory Testing](06_memory_testing/)
**Complexity**: Intermediate | **Lines**: ~180

Memory leak detection using reference counting and valgrind.

**Key Concepts**:
- Reference counting tests
- Valgrind integration
- AddressSanitizer
- Memory leak patterns

**Run**:
```bash
cd 06_memory_testing
cargo test
maturin develop
pytest tests/ -v
```

---

#### [07. GIL Testing](07_gil_testing/)
**Complexity**: Intermediate | **Lines**: ~160

Testing GIL release and thread safety.

**Key Concepts**:
- GIL release verification
- Thread safety testing
- Parallel execution
- Deadlock prevention

**Run**:
```bash
cd 07_gil_testing
cargo test
maturin develop
pytest tests/ -v
```

---

### Advanced Level

#### [08. Debugging Setup](08_debugging_setup/)
**Complexity**: Advanced | **Lines**: ~200

Complete debugging configuration with GDB/LLDB.

**Key Concepts**:
- Debug build configuration
- GDB/LLDB setup
- Breakpoint management
- Core dump analysis

**Run**:
```bash
cd 08_debugging_setup
maturin develop
python debug.py

# Debug with GDB/LLDB
gdb python
(gdb) run debug.py
```

---

#### [09. CI Testing](09_ci_testing/)
**Complexity**: Advanced | **Lines**: ~250

Complete CI/CD pipeline with multi-platform testing.

**Key Concepts**:
- GitHub Actions workflows
- Multi-platform testing
- Multi-Python version testing
- Automated coverage reporting

**Run**:
```bash
cd 09_ci_testing
cargo test
cargo fmt -- --check
cargo clippy -- -D warnings
maturin develop --release
pytest tests/ --cov=ci_testing
```

---

#### [10. Production Suite](10_production_suite/)
**Complexity**: Advanced | **Lines**: ~300

Production-grade test suite combining all patterns.

**Key Concepts**:
- Complete test coverage strategy
- Integration of all patterns
- Production debugging
- Performance monitoring
- Deployment verification

**Run**:
```bash
cd 10_production_suite
./run_all_tests.sh  # Runs complete test suite
```

---

## Quick Start

### Setup Any Example

```bash
# Navigate to example
cd <example_directory>

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install maturin pytest

# Build and install
maturin develop

# Run tests
cargo test  # Rust tests
pytest tests/ -v  # Python tests
```

### Common Commands

```bash
# Rust tests
cargo test                    # Run all tests
cargo test --nocapture        # Show output
cargo test <name>             # Run specific test

# Python tests
pytest tests/ -v              # Verbose
pytest tests/ -k <pattern>    # Match pattern
pytest tests/ --cov           # With coverage

# Benchmarks
cargo bench                   # Rust benchmarks
pytest tests/ --benchmark-only  # Python benchmarks

# Linting
cargo fmt -- --check          # Format check
cargo clippy -- -D warnings   # Lint check
```

## Learning Path

### For Beginners
1. Start with **01_rust_unit_tests** to learn basic Rust testing
2. Move to **02_python_tests** for pytest integration
3. Study **03_error_testing** for error handling patterns

### For Intermediate Users
4. Explore **04_property_testing** for advanced test generation
5. Learn **05_benchmarking** for performance measurement
6. Study **06_memory_testing** for leak detection
7. Practice **07_gil_testing** for concurrency

### For Advanced Users
8. Configure **08_debugging_setup** for development
9. Implement **09_ci_testing** for automation
10. Study **10_production_suite** as a complete reference

## File Structure

Each example follows a consistent structure:

```
<example_name>/
├── src/
│   └── lib.rs              # Rust implementation
├── tests/                   # Python tests
│   ├── conftest.py         # pytest fixtures (if needed)
│   └── test_*.py           # Test files
├── benches/                 # Benchmarks (if applicable)
│   └── benchmarks.rs
├── Cargo.toml              # Rust dependencies
├── pyproject.toml          # Python package config
└── README.md               # Example-specific docs
```

## Testing Best Practices

### Rust Tests
- Use `#[cfg(test)]` modules
- Acquire GIL with `Python::with_gil`
- Test both success and error paths
- Use proptest for property tests

### Python Tests
- Use pytest fixtures for reusable data
- Parameterize tests with `@pytest.mark.parametrize`
- Test exception types and messages
- Use hypothesis for property tests

### Integration
- Test complete workflows
- Verify error propagation
- Check memory usage patterns
- Validate GIL release

### Performance
- Benchmark critical paths
- Compare Rust vs Python performance
- Track regressions
- Profile bottlenecks

## Debugging Tips

### Rust Debugging
```bash
# Build with debug symbols
maturin develop

# Debug with GDB
gdb python
(gdb) run -c "import module; module.function()"

# Debug with LLDB (macOS)
lldb python
(lldb) run -c "import module; module.function()"
```

### Memory Debugging
```bash
# Valgrind (Linux)
valgrind --leak-check=full python script.py

# AddressSanitizer
RUSTFLAGS="-Z sanitizer=address" cargo +nightly build
```

### Performance Profiling
```bash
# py-spy
py-spy record -o profile.svg -- python script.py

# Rust profiling
cargo flamegraph
```

## Coverage Goals

- **Unit tests**: 90%+ coverage
- **Integration tests**: 80%+ coverage
- **Critical paths**: 100% coverage
- **Error paths**: 100% coverage

## Additional Resources

- [PyO3 Testing Guide](https://pyo3.rs/latest/testing)
- [Rust Testing Book](https://rust-lang.github.io/book/ch11-00-testing.html)
- [pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Criterion Documentation](https://bheisler.github.io/criterion.rs/)

## Support

Each example includes:
- Complete, runnable code
- Detailed README with explanations
- Test execution instructions
- Expected output examples
- Next steps and references

For more information, see the main skill file: `../../pyo3-testing-debugging.md`
