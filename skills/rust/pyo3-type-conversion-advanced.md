---
skill: pyo3-type-conversion-advanced
description: Advanced PyO3 type conversion including zero-copy, numpy, and custom protocols
category: rust
tags: [pyo3, rust, python, numpy, arrow, zero-copy, performance]
prerequisites:
  - pyo3-fundamentals
  - Basic understanding of numpy arrays
  - Memory management concepts
level: advanced
resources:
  - REFERENCE.md (3,500-4,000 lines)
  - 3 scripts (800+ lines each)
  - 9-10 production examples
---

# PyO3 Advanced Type Conversion

## Overview

Master advanced type conversion patterns in PyO3, focusing on zero-copy operations, numpy array integration, Apache Arrow/Parquet support, custom conversion protocols, buffer protocol implementation, and high-performance data interchange. This skill enables building high-throughput data processing pipelines with minimal memory overhead.

## What You'll Learn

### Core Concepts
- **Zero-Copy Operations**: Sharing memory between Rust and Python without copying
- **Numpy Integration**: Working with numpy arrays efficiently (PyArray, PyReadonlyArray)
- **Buffer Protocol**: Implementing Python's buffer protocol for custom types
- **Arrow/Parquet**: Integrating with Apache Arrow and Parquet formats
- **Custom Protocols**: Sequence, mapping, and iterator protocols for custom types
- **Streaming Conversion**: Processing large datasets without loading into memory

### Advanced Topics [ADVANCED]
- **Custom Allocators**: Using custom allocators for numpy arrays
- **Memory Views**: Advanced memoryview protocol implementations
- **Cross-Language Buffers**: Sharing buffers between multiple languages
- **Lock-Free Structures**: Implementing lock-free data structures for concurrent access
- **SIMD Optimization**: Leveraging SIMD for bulk conversions
- **GPU Memory**: Handling GPU-allocated arrays (CUDA, OpenCL)

## When to Use

**Ideal for**:
- High-performance numerical computing
- Large dataset processing (GB+ data)
- Machine learning pipelines
- Scientific computing applications
- Data engineering workflows
- Real-time data streaming

**Not ideal for**:
- Small data (< 1MB) where copy overhead is negligible
- Infrequent operations (one-time conversions)
- When data format mismatches require transformation anyway

## Key Resources

### REFERENCE.md
Comprehensive guide covering:
- Zero-copy fundamentals and safety guarantees
- Numpy array integration (rust-numpy, ndarray)
- Buffer protocol implementation details
- Arrow/Parquet integration strategies
- Custom conversion protocols
- Memory layout considerations
- Performance profiling and optimization
- Safety patterns and pitfalls
- Cross-language memory management
- Streaming and incremental processing

### Scripts

**1. conversion_profiler.py** (800+ lines)
- Profiles conversion overhead (copy vs zero-copy)
- Benchmarks different conversion strategies
- Analyzes memory usage patterns
- Compares numpy, Arrow, raw buffers
- Generates performance reports
- CLI: --benchmark, --profile, --compare, --report

**2. numpy_validator.py** (800+ lines)
- Validates numpy array conversions
- Tests array layout compatibility
- Checks memory alignment
- Verifies stride patterns
- Tests dtype conversions
- CLI: --validate, --layout, --dtype, --stride

**3. buffer_inspector.py** (800+ lines)
- Inspects buffer protocol implementations
- Validates memory views
- Checks for memory leaks
- Tests lifetime management
- Analyzes sharing patterns
- CLI: --inspect, --validate, --leak-check

### Examples

**1. zero_copy_basics/** - Zero-copy fundamentals
- Sharing Rust Vec with Python
- Borrowing vs owning conversions
- Lifetime management
- Safety considerations

**2. numpy_integration/** - Numpy array operations
- Creating numpy arrays from Rust
- Zero-copy array access
- In-place modifications
- Multi-dimensional arrays
- Custom dtypes

**3. buffer_protocol/** - Buffer protocol implementation
- Implementing buffer protocol for custom types
- Memory layout specification
- Readonly vs mutable buffers
- Format strings

**4. arrow_parquet/** - Arrow/Parquet integration
- Reading/writing Parquet files
- Arrow IPC format
- Zero-copy Arrow arrays
- Schema conversion
- Streaming operations

**5. custom_protocols/** - Custom conversion protocols
- Sequence protocol for Rust collections
- Mapping protocol for custom data structures
- Iterator protocol for streaming data
- Context manager for resource management

**6. streaming_conversion/** - Large dataset processing
- Chunked processing
- Incremental conversion
- Memory-efficient pipelines
- Backpressure handling

**7. performance_optimization/** - Optimization techniques
- SIMD vectorization
- Cache-friendly layouts
- Prefetching strategies
- Parallel conversion

**8. cross_format/** - Multiple format support [ADVANCED]
- Converting between numpy, Arrow, Parquet
- Format negotiation
- Optimal conversion paths
- Zero-copy where possible

**9. gpu_arrays/** - GPU memory handling [ADVANCED]
- CUDA array integration
- GPU-CPU zero-copy
- Pinned memory
- Stream synchronization

**10. custom_allocators/** - Advanced memory management [ADVANCED]
- Custom numpy allocators
- Memory pooling
- NUMA-aware allocation
- Alignment control

## Quality Standards

All resources meet Wave 10-11 quality standards:
- ✅ 0 CRITICAL/HIGH security findings
- ✅ 100% type hints (Python)
- ✅ Comprehensive error handling
- ✅ Production-ready code
- ✅ Full CLI support (--help, --json, --verbose, --dry-run)
- ✅ Extensive benchmarks
- ✅ Memory safety validation

## Loading Resources

```bash
# Load comprehensive reference
cat skills/rust/pyo3-type-conversion-advanced/resources/REFERENCE.md

# Profile conversions
python skills/rust/pyo3-type-conversion-advanced/resources/scripts/conversion_profiler.py \
  --benchmark --compare copy,zerocopy,arrow

# Validate numpy integration
python skills/rust/pyo3-type-conversion-advanced/resources/scripts/numpy_validator.py \
  --validate my_array --layout --dtype

# Inspect buffer protocol
python skills/rust/pyo3-type-conversion-advanced/resources/scripts/buffer_inspector.py \
  --inspect MyBuffer --leak-check
```

## Related Skills

- **pyo3-fundamentals**: Prerequisites (basic type conversion)
- **pyo3-performance-gil-parallel**: Performance optimization context
- **pyo3-data-science-ml**: Practical applications of advanced conversions
- **pyo3-classes-modules**: Implementing protocols on custom classes

## References

- [rust-numpy Documentation](https://docs.rs/numpy/)
- [ndarray Crate](https://docs.rs/ndarray/)
- [Apache Arrow Rust](https://docs.rs/arrow/)
- [Python Buffer Protocol](https://docs.python.org/3/c-api/buffer.html)
- [Numpy C API](https://numpy.org/doc/stable/reference/c-api/)

---

**Status**: Ready for implementation
**Estimated Size**: 7,200-8,400 lines total
**Time to Complete**: 6-7 days
