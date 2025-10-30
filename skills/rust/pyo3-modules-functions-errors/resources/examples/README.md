# PyO3 Modules, Functions, and Errors - Progressive Examples

This directory contains 10 progressive examples demonstrating PyO3 modules, functions, and error handling patterns, from beginner to production-ready code.

## Quick Start

Each example is a complete, runnable Rust project with:
- `src/lib.rs` - Rust implementation
- `Cargo.toml` - Rust dependencies
- `pyproject.toml` - Python packaging
- `test_example.py` - Python tests
- `README.md` - Documentation

### Building an Example

```bash
cd 01_basic_module
maturin develop
pytest test_example.py -v
```

## Example Progression

### Beginner Level (01-03)

#### 01: Basic Module
**Concepts**: Module creation, function export, basic types, docstrings
**Files**: ~150 lines total
**Key Learning**: How to create your first PyO3 module

```python
import basic_module
basic_module.add(2, 3)  # 5
basic_module.greet("Alice")  # "Hello, Alice!"
```

#### 02: Function Arguments
**Concepts**: Optional args, defaults, keyword-only, *args, **kwargs
**Files**: ~200 lines total
**Key Learning**: Python's flexible argument patterns in Rust

```python
import function_arguments as fa
fa.power(2, 10)  # 1024
fa.process_text("hello", uppercase=True, repeat=2)  # "HELLOHELLO"
```

#### 03: Error Handling
**Concepts**: PyResult, standard exceptions, error messages, validation
**Files**: ~180 lines total
**Key Learning**: Proper error handling and exception creation

```python
import error_handling as eh
try:
    eh.divide(10.0, 0.0)
except ZeroDivisionError as e:
    print(f"Error: {e}")
```

### Intermediate Level (04-07)

#### 04: Submodules
**Concepts**: Module organization, nested modules, re-exports
**Files**: ~220 lines total
**Key Learning**: Structuring large projects with submodules

```python
import submodules
submodules.math.add(5, 3)  # 8
submodules.strings.reverse("hello")  # "olleh"
submodules.collections.unique([1, 2, 2, 3])  # [1, 2, 3]
```

#### 05: Custom Exceptions
**Concepts**: Exception hierarchies, custom exception types, attributes
**Files**: ~250 lines total
**Key Learning**: Building professional error hierarchies

```python
import custom_exceptions as ce
try:
    ce.validate_range(100, 0, 10)
except ce.RangeError as e:
    print(f"Out of range: {e}")
```

#### 06: Function Overloading
**Concepts**: Multiple signatures, PyAny, builder patterns
**Files**: ~200 lines total
**Key Learning**: Handling multiple function signatures

```python
import function_overloading as fo
fo.add_any(10, 20)  # 30
fo.add_any("Hello", " World")  # "Hello World"
fo.format_full("text", uppercase=True, prefix=">>> ")
```

#### 07: Module Constants
**Concepts**: Constants, enums, module metadata
**Files**: ~150 lines total
**Key Learning**: Exporting constants and enum types

```python
import module_constants as mc
print(mc.VERSION)  # "1.0.0"
print(mc.MAX_CONNECTIONS)  # 100
level = mc.LogLevel.from_string("error")
```

### Advanced Level (08-10)

#### 08: Callback Functions
**Concepts**: Calling Python from Rust, callbacks, error propagation
**Files**: ~180 lines total
**Key Learning**: Python/Rust interop with callbacks

```python
import callback_functions as cf
cf.map_with_callback([1, 2, 3], lambda x: x * 2)  # [2, 4, 6]
cf.filter_with_callback([1, 2, 3, 4], lambda x: x % 2 == 0)  # [2, 4]
cf.chain_callbacks(10, [lambda x: x * 2, lambda x: x + 5])  # 25
```

#### 09: Error Hierarchy
**Concepts**: Multi-level errors, error context, error codes
**Files**: ~280 lines total
**Key Learning**: Production-grade error handling

```python
import error_hierarchy as eh
try:
    eh.connect_database("localhost", 9999)
except eh.ConnectionError as e:
    print(f"Connection failed: {e}")
except eh.DatabaseError as e:
    print(f"Database error: {e}")
```

#### 10: Production API
**Concepts**: Complete API, all patterns combined, best practices
**Files**: ~300 lines total
**Key Learning**: Building real-world production modules

```python
import production_api as api

# Configuration
config = api.Config(debug=True, max_retries=5)
config.validate()

# Processing
items = ["item1", "item2", "item3"]
result = api.processing.process_batch(items, config)
print(f"Success: {result.success_rate()}")

# Statistics
stats = api.stats.compute_stats([1.0, 2.0, 3.0])
print(f"Mean: {stats['mean']}")
```

## Learning Path

### For Complete Beginners
Start with examples 01-03 in order. These cover the fundamentals you need.

### For Intermediate Users
Skip to examples 04-07. These show how to structure real projects.

### For Advanced Users
Jump to examples 08-10. These demonstrate production patterns.

## Key Patterns Summary

| Pattern | Examples | Key Concept |
|---------|----------|-------------|
| Basic functions | 01, 02 | Exporting Rust functions to Python |
| Error handling | 03, 05, 09 | PyResult and exceptions |
| Module structure | 04, 10 | Submodules and organization |
| Type flexibility | 02, 06 | Multiple signatures and PyAny |
| Configuration | 07, 10 | Constants, enums, config objects |
| Callbacks | 08 | Calling Python from Rust |
| Production ready | 10 | Complete API with all patterns |

## Testing All Examples

Run this script to test all examples:

```bash
#!/bin/bash
for ex in 01_* 02_* 03_* 04_* 05_* 06_* 07_* 08_* 09_* 10_*; do
    echo "Testing $ex..."
    cd "$ex"
    maturin develop -q && pytest test_example.py -q
    cd ..
done
```

## Common Issues and Solutions

### Issue: Module not found after build
**Solution**: Run `maturin develop` in the example directory

### Issue: Import name doesn't match
**Solution**: The Python module name matches the `#[pymodule]` function name, not the Cargo.toml name

### Issue: Type conversion errors
**Solution**: Check the type mappings in the README of each example

### Issue: Tests fail
**Solution**: Make sure you're in the example directory and have run `maturin develop` first

## Performance Notes

- Examples 01-07: Focus on correctness and patterns
- Examples 08-10: Include performance considerations
- Callback overhead: Example 08 discusses FFI boundary costs
- Production patterns: Example 10 shows optimization strategies

## Building for Distribution

To build a wheel for distribution:

```bash
cd 10_production_api
maturin build --release
# Wheel will be in target/wheels/
```

## Further Resources

- [PyO3 User Guide](https://pyo3.rs/)
- [Maturin Documentation](https://www.maturin.rs/)
- [Python/C API](https://docs.python.org/3/c-api/)
- [Rust FFI](https://doc.rust-lang.org/nomicon/ffi.html)

## Contributing

These examples are designed to be:
- Self-contained and runnable
- Progressive in complexity
- Well-documented
- Production-quality code

Feel free to use them as templates for your own projects!

---

**Total Lines of Code**: ~2,150 lines across all examples
**Estimated Learning Time**: 4-6 hours for all examples
**Prerequisites**: Basic Rust and Python knowledge
