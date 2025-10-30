# PyO3 Performance and Parallelism Examples

Progressive examples demonstrating high-performance parallel programming with PyO3 and Rust.

## Overview

These examples progress from basic concepts to production-ready systems, with each example building on previous concepts.

## Examples

### Beginner (01-03)

#### 01_gil_release - Basic GIL Release
**Concepts**: GIL release with `py.allow_threads()`, performance impact, concurrent execution
- Learn when and how to release the GIL
- Measure GIL release overhead
- Enable true parallelism from Python

#### 02_parallel_basic - Simple Rayon Parallelism
**Concepts**: Rayon parallel iterators, map/filter/reduce, parallel sort
- Convert `.iter()` to `.par_iter()` for parallelism
- Use parallel functional operations
- Process large datasets efficiently

#### 03_performance_timing - Benchmarking and Profiling
**Concepts**: High-resolution timing, statistical benchmarks, memory throughput
- Accurately measure performance
- Compare sequential vs parallel
- Profile multi-stage operations

### Intermediate (04-07)

#### 04_thread_pool - Custom Thread Pool
**Concepts**: Thread pool pattern, work stealing, adaptive sizing
- Build reusable thread pools
- Implement work stealing for load balancing
- Control thread count dynamically

#### 05_atomic_operations - Lock-Free Programming
**Concepts**: Atomic types, compare-and-swap, lock-free algorithms
- Use atomics instead of mutexes
- Implement lock-free statistics
- Achieve better performance in high contention

#### 06_parallel_iterators - Advanced Iterator Patterns
**Concepts**: Flat map, fold/reduce, partition, predicates
- Master Rayon's rich iterator API
- Chain multiple operations
- Handle complex transformations

#### 07_channels - Multi-threaded Communication
**Concepts**: Producer-consumer, pipeline, fan-out/fan-in, broadcast
- Coordinate work between threads
- Build multi-stage pipelines
- Distribute and collect results

### Advanced (08-10)

#### 08_zero_copy - Minimal Data Copying
**Concepts**: In-place processing, reference-based operations, chunked processing
- Avoid unnecessary allocations
- Process data without copying
- Maximize memory bandwidth

#### 09_custom_allocator - Memory Management Patterns
**Concepts**: Buffer pools, object pools, arena allocation, sliding window
- Reuse allocations efficiently
- Reduce memory pressure
- Implement cache-friendly algorithms

#### 10_production_pipeline - Complete System
**Concepts**: Multi-stage pipeline, error handling, monitoring, scalability
- Combine all techniques
- Handle real-world requirements
- Production-ready architecture

## Building All Examples

Each example can be built independently:

```bash
cd 01_gil_release
pip install maturin
maturin develop --release
python test_example.py
```

Or use a script to build all:

```bash
for dir in */; do
  echo "Building ${dir}..."
  cd "$dir"
  maturin develop --release
  cd ..
done
```

## Learning Path

1. **Start with 01-03**: Learn fundamentals of GIL release, parallelism, and benchmarking
2. **Move to 04-07**: Understand thread management, atomics, and communication patterns
3. **Master 08-10**: Apply advanced techniques for production systems

## Performance Expectations

Typical speedups compared to pure Python:

| Example | Speedup | Use Case |
|---------|---------|----------|
| 01 | 1-4x | GIL release enables parallelism |
| 02 | 4-8x | Data parallel operations |
| 03 | N/A | Measurement utilities |
| 04 | 3-6x | Custom thread coordination |
| 05 | 2-10x | High contention scenarios |
| 06 | 6-12x | Complex transformations |
| 07 | 3-8x | Multi-stage pipelines |
| 08 | 2-10x | Large array operations |
| 09 | 1.5-5x | Allocation-heavy workloads |
| 10 | 10-50x | Complete data processing |

## Common Patterns

### GIL Release Pattern
```rust
py.allow_threads(|| {
    // CPU-intensive or blocking work here
    expensive_computation()
})
```

### Rayon Parallel Iterator Pattern
```rust
py.allow_threads(|| {
    data.par_iter()
        .map(|x| transform(x))
        .collect()
})
```

### Atomic Counter Pattern
```rust
let counter = Arc::new(AtomicU64::new(0));
// Share counter across threads
counter.fetch_add(1, Ordering::SeqCst);
```

### Channel Communication Pattern
```rust
let (tx, rx) = channel();
// Producer sends, consumers receive
tx.send(data).unwrap();
let data = rx.recv().unwrap();
```

## Key Takeaways

1. **GIL Release**: Always release GIL for CPU-intensive work
2. **Rayon**: Easiest path to data parallelism
3. **Atomics**: Better than mutexes for simple shared state
4. **Channels**: Clean way to coordinate threads
5. **Zero-Copy**: Minimize allocations for performance
6. **Benchmarking**: Measure before optimizing

## Prerequisites

- Rust 1.70+
- Python 3.8+
- maturin 1.0+

## Resources

- [PyO3 Documentation](https://pyo3.rs)
- [Rayon Documentation](https://docs.rs/rayon)
- [Rust Book - Concurrency](https://doc.rust-lang.org/book/ch16-00-concurrency.html)
- [Rust Atomics and Locks](https://marabos.nl/atomics/)

## License

MIT License - See individual example READMEs for details.
