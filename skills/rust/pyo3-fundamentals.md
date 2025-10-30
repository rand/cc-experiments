---
skill: pyo3-fundamentals
description: PyO3 fundamentals for building Python extensions in Rust
category: rust
tags: [pyo3, rust, python, ffi, performance, extensions]
prerequisites:
  - Basic Rust knowledge (ownership, lifetimes, traits)
  - Python 3.8+ familiarity
  - Understanding of compiled vs interpreted languages
level: intermediate
resources:
  - REFERENCE.md (3,500-4,000 lines)
  - 3 scripts (800+ lines each)
  - 9-10 production examples
---

# PyO3 Fundamentals

## Overview

PyO3 enables writing high-performance Python extensions in Rust, combining Python's ease of use with Rust's performance and safety. This skill covers project setup, type conversion, error handling, FFI boundaries, memory safety, cross-language debugging, and performance profiling.

## What You'll Learn

### Core Concepts
- **Project Setup**: maturin, Cargo.toml configuration, Python metadata
- **Type Conversion**: Rust ↔ Python type mapping, FromPyObject, IntoPy traits
- **Error Handling**: anyhow/thiserror integration, Python exception mapping
- **FFI Safety**: Memory ownership across language boundaries, GIL awareness
- **Cross-Language Debugging**: lldb, rust-gdb, VS Code integration, stack traces
- **Memory Profiling**: valgrind, heaptrack, Rust profilers, Python tracemalloc

### Advanced Topics [ADVANCED]
- **Custom Type Protocols**: Implementing Python protocols in Rust
- **Performance Profiling**: Identifying bottlenecks across language boundaries
- **Memory Safety Patterns**: Avoiding use-after-free, double-free, data races
- **FFI Best Practices**: API design, version compatibility, stability

## When to Use

**Ideal for**:
- Performance-critical Python code (10-100x speedups possible)
- CPU-bound operations (numerical computation, parsing, encoding/decoding)
- Integrating existing Rust libraries into Python
- Memory-safe alternatives to C extensions

**Not ideal for**:
- I/O-bound operations (network, disk) - Python async is often sufficient
- Code with frequent Python ↔ Rust transitions (FFI overhead)
- Prototyping (slower development than pure Python)

## Key Resources

### REFERENCE.md
Comprehensive guide covering:
- Environment setup (Rust, Python, maturin)
- Project structure and configuration
- Type conversion patterns (primitives, collections, custom types)
- Error handling strategies
- FFI safety rules and patterns
- Cross-language debugging workflows
- Memory profiling techniques
- Production deployment considerations

### Scripts

**1. setup_validator.py** (800+ lines)
- Validates PyO3 development environment
- Checks Rust toolchain, Python version, maturin
- Verifies compilation targets
- Tests cross-language debugging tools
- Generates setup report with recommendations

**2. type_converter.py** (800+ lines)
- Demonstrates all type conversion patterns
- Benchmarks conversion overhead
- Tests edge cases (None, overflow, invalid UTF-8)
- Validates memory safety
- Generates type mapping reference

**3. debugger.py** (800+ lines)
- Cross-language debugging utilities
- Stack trace aggregation (Rust + Python)
- Breakpoint coordination
- Memory leak detection
- Performance profiler integration

### Examples

**1. hello_world/** - Basic PyO3 module
- Minimal project setup
- Simple function export
- Building and importing

**2. type_conversion/** - Comprehensive type examples
- Primitives, collections, custom types
- Option<T>, Result<T, E> mapping
- Ownership and borrowing patterns

**3. error_handling/** - Error patterns
- anyhow integration
- Custom Python exceptions
- Error context preservation

**4. calculator/** - Production-ready library
- Multiple operations (add, multiply, factorial)
- Input validation
- Error handling
- Documentation
- Tests (Rust + Python)

**5. json_parser/** - Real-world use case
- High-performance JSON parsing
- Zero-copy where possible
- Error propagation
- Benchmarks vs Python json module

**6. ffi_safety/** - Memory safety patterns
- Safe reference passing
- GIL acquisition/release
- Preventing use-after-free
- Data race prevention

**7. debugging_example/** - Cross-language debugging
- lldb configuration
- Breakpoint setting (Rust + Python)
- Stack trace inspection
- Variable inspection across languages

**8. profiling_example/** - Performance profiling
- CPU profiling (perf, flamegraph)
- Memory profiling (valgrind, heaptrack)
- Identifying bottlenecks
- Optimization iteration

**9. versioning/** - Version compatibility
- Python version detection
- PyO3 version compatibility
- ABI stability patterns
- Feature flags

**10. production_deployment/** - Deployment strategies
- Wheel building (manylinux, macOS, Windows)
- Cross-compilation
- Dependency management
- CI/CD integration

## Quality Standards

All resources meet Wave 10-11 quality standards:
- ✅ 0 CRITICAL/HIGH security findings
- ✅ 100% type hints (Python)
- ✅ Comprehensive error handling
- ✅ Production-ready code
- ✅ Full CLI support (--help, --json, --verbose, --dry-run)
- ✅ Extensive documentation
- ✅ Real-world examples

## Loading Resources

```bash
# Load comprehensive reference
cat skills/rust/pyo3-fundamentals/resources/REFERENCE.md

# Run environment validator
python skills/rust/pyo3-fundamentals/resources/scripts/setup_validator.py --verbose

# Explore examples
ls skills/rust/pyo3-fundamentals/resources/examples/

# Test type conversion patterns
python skills/rust/pyo3-fundamentals/resources/scripts/type_converter.py --all-types
```

## Related Skills

- **pyo3-classes-modules**: Next step - classes, modules, plugins
- **pyo3-type-conversion-advanced**: Deep dive on zero-copy, numpy
- **pyo3-performance-gil-parallel**: Performance optimization
- **pyo3-testing-quality-ci**: Testing strategies

## References

- [PyO3 Official Guide](https://pyo3.rs/)
- [PyO3 API Documentation](https://docs.rs/pyo3/)
- [maturin User Guide](https://www.maturin.rs/)
- [Rust FFI Omnibus](http://jakegoulding.com/rust-ffi-omnibus/)

---

**Status**: Ready for implementation
**Estimated Size**: 7,200-8,400 lines total
**Time to Complete**: 6-7 days
