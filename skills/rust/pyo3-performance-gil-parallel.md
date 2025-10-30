---
name: pyo3-performance-gil-parallel
description: "Master PyO3 performance optimization through GIL management, parallel execution, sub-interpreters, and lock-free data structures. Learn to build high-performance Python extensions that leverage multi-core systems while maintaining safety and correctness."
globs: ["**/*.rs", "**/*.py", "**/Cargo.toml"]
---

# PyO3 Performance: GIL Management & Parallel Execution

Master building high-performance Python extensions with PyO3 by understanding and optimizing Global Interpreter Lock (GIL) behavior, implementing parallel execution patterns, leveraging sub-interpreters, and preparing for nogil Python 3.13+.

## Prerequisites

**Required Knowledge**:
- PyO3 fundamentals (skill: pyo3-fundamentals)
- Rust concurrency primitives (Arc, Mutex, RwLock, channels)
- Python threading and multiprocessing models
- Basic understanding of memory ordering and atomics

**Environment**:
```bash
# Rust nightly for some advanced features
rustup install nightly
rustup default nightly

# Python 3.8+ (3.13+ for nogil support)
python --version

# Performance profiling tools
cargo install cargo-flamegraph
cargo install cargo-bench
pip install py-spy

# Development dependencies
cargo add pyo3 --features extension-module
cargo add rayon tokio parking_lot crossbeam
```

## Learning Path

### 1. GIL Fundamentals

**Understand the GIL**:
- What the GIL is and why it exists
- When Python holds/releases the GIL
- Impact on multi-threaded performance
- PyO3's GIL token (`Python<'py>`) and lifetime management

**GIL Release Strategies**:
```rust
use pyo3::prelude::*;

#[pyfunction]
fn cpu_intensive_work(data: Vec<i64>) -> i64 {
    // Release GIL for CPU-bound work
    Python::with_gil(|py| {
        py.allow_threads(|| {
            // Rust code runs without GIL
            data.iter().sum()
        })
    })
}
```

**Best Practices**:
- Release GIL for CPU-intensive operations
- Hold GIL for Python object access
- Minimize GIL acquisition/release overhead
- Understand when automatic release happens

### 2. Parallel Execution Patterns

**Rayon Integration**:
```rust
use rayon::prelude::*;

#[pyfunction]
fn parallel_process(py: Python, data: Vec<f64>) -> Vec<f64> {
    py.allow_threads(|| {
        data.par_iter()
            .map(|x| x.powi(2))
            .collect()
    })
}
```

**Thread Pools**:
- Custom thread pools for PyO3 workloads
- Worker threads without GIL
- Result aggregation with GIL
- Error propagation across threads

**Data Parallelism**:
- Chunk-based parallel processing
- Load balancing strategies
- Minimizing synchronization overhead

### 3. Sub-Interpreters (PEP 554)

**Multiple Python Interpreters**:
```rust
// Per-interpreter state isolation
// Each interpreter has its own GIL
// True parallelism for Python code
```

**Use Cases**:
- Isolated plugin execution
- Parallel Python code execution
- Sandboxed evaluation
- Multi-tenant applications

**Challenges**:
- Interpreter lifecycle management
- Data sharing between interpreters
- Compatibility with C extensions
- Performance characteristics

### 4. Lock-Free Data Structures

**Atomic Operations**:
```rust
use std::sync::atomic::{AtomicU64, Ordering};

#[pyclass]
struct AtomicCounter {
    count: AtomicU64,
}

#[pymethods]
impl AtomicCounter {
    fn increment(&self) -> u64 {
        self.count.fetch_add(1, Ordering::SeqCst)
    }
}
```

**Concurrent Data Structures**:
- Lock-free queues (crossbeam)
- Concurrent hash maps (dashmap)
- Arc for shared ownership
- RwLock for read-heavy workloads

**Memory Ordering**:
- Understanding Acquire/Release/SeqCst
- When to use which ordering
- Performance vs correctness trade-offs

### 5. Custom Allocators

**Memory Pool Allocators**:
- Reduce allocation overhead
- Thread-local allocation
- Custom allocators for specific workloads

**Zero-Copy Patterns**:
- Minimize memory copies between Rust/Python
- Buffer protocol for large data
- Memory-mapped files

### 6. nogil Python 3.13+

**Preparing for nogil**:
- Understanding free-threaded Python
- API changes and compatibility
- Performance implications
- Migration strategies

**Conditional Compilation**:
```rust
#[cfg(Py_GIL_DISABLED)]
fn nogil_optimized_path() {
    // Optimized for nogil Python
}

#[cfg(not(Py_GIL_DISABLED))]
fn gil_aware_path() {
    // Traditional GIL management
}
```

### 7. Performance Profiling

**Tools**:
- `py-spy`: Profile Python/Rust together
- `cargo-flamegraph`: Visualize hot paths
- `perf`: Linux performance counters
- Custom instrumentation with `tracing`

**Metrics**:
- GIL hold time
- Thread utilization
- Lock contention
- Memory allocation patterns

**Optimization Process**:
1. Profile to find bottlenecks
2. Release GIL where safe
3. Parallelize CPU-bound work
4. Minimize synchronization
5. Validate correctness
6. Measure improvements

### 8. Advanced Patterns

**Work Stealing**:
- Dynamic load balancing
- Efficient thread utilization
- Minimizing idle time

**Pipeline Parallelism**:
- Stage-based processing
- Overlapping I/O and compute
- Backpressure handling

**SIMD Optimization**:
- Vectorized operations
- Platform-specific optimizations
- Fallback implementations

## Common Patterns

### CPU-Bound Parallel Processing
```rust
#[pyfunction]
fn parallel_compute(py: Python, data: Vec<f64>) -> PyResult<Vec<f64>> {
    py.allow_threads(|| {
        Ok(data.par_iter()
            .map(|x| expensive_computation(*x))
            .collect())
    })
}
```

### Shared State with Interior Mutability
```rust
#[pyclass]
struct SharedState {
    data: Arc<RwLock<HashMap<String, i64>>>,
}

#[pymethods]
impl SharedState {
    fn get(&self, key: String) -> Option<i64> {
        self.data.read().unwrap().get(&key).copied()
    }

    fn set(&self, key: String, value: i64) {
        self.data.write().unwrap().insert(key, value);
    }
}
```

### Thread Pool Worker
```rust
use std::sync::mpsc;

#[pyclass]
struct WorkerPool {
    sender: mpsc::Sender<Task>,
}

#[pymethods]
impl WorkerPool {
    fn submit(&self, task: Task) -> PyResult<()> {
        self.sender.send(task)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to submit task: {}", e)
            ))
    }
}
```

## Performance Optimization Checklist

**GIL Management**:
- [ ] Identify CPU-bound operations
- [ ] Release GIL with `py.allow_threads()`
- [ ] Minimize GIL acquisition/release frequency
- [ ] Profile GIL hold time

**Parallelization**:
- [ ] Use Rayon for data parallelism
- [ ] Balance work across threads
- [ ] Minimize synchronization overhead
- [ ] Consider sub-interpreters for Python parallelism

**Memory Efficiency**:
- [ ] Use zero-copy where possible
- [ ] Consider custom allocators for hot paths
- [ ] Minimize allocations in tight loops
- [ ] Use buffer protocol for large data

**Safety**:
- [ ] No data races (verified by Rust)
- [ ] Proper error propagation
- [ ] Thread-safe shared state
- [ ] Correct memory ordering for atomics

## Resources

**In resources/ directory**:
- `REFERENCE.md`: Comprehensive GIL, parallelism, and optimization guide
- `scripts/`:
  - `gil_profiler.py`: Profile GIL hold times and contention
  - `parallel_benchmark.py`: Benchmark parallel execution strategies
  - `performance_analyzer.py`: Analyze performance characteristics
- `examples/`:
  - `01_gil_release/`: Basic GIL release patterns
  - `02_parallel_rayon/`: Rayon-based parallelism
  - `03_thread_pool/`: Custom thread pool implementation
  - `04_atomic_counters/`: Lock-free atomic operations
  - `05_shared_state/`: Thread-safe shared state patterns
  - `06_subinterpreters/`: Sub-interpreter usage (when available)
  - `07_custom_allocator/`: Custom allocator integration
  - `08_simd_optimization/`: SIMD vectorization
  - `09_nogil_preparation/`: Preparing for nogil Python
  - `10_production_optimization/`: Complete production example

**External Resources**:
- [PEP 554 - Multiple Interpreters](https://peps.python.org/pep-0554/)
- [PEP 703 - Making the GIL Optional](https://peps.python.org/pep-0703/)
- [PyO3 Parallelism Guide](https://pyo3.rs/latest/parallelism.html)
- [Rayon Documentation](https://docs.rs/rayon/)
- [Crossbeam Documentation](https://docs.rs/crossbeam/)

## Anti-Patterns

**❌ Holding GIL unnecessarily**:
```rust
// Bad: GIL held during CPU-bound work
#[pyfunction]
fn slow(py: Python, data: Vec<i64>) -> i64 {
    data.iter().sum()  // GIL held!
}
```

**✅ Release GIL for CPU-bound work**:
```rust
// Good: Release GIL
#[pyfunction]
fn fast(py: Python, data: Vec<i64>) -> i64 {
    py.allow_threads(|| data.iter().sum())
}
```

**❌ Excessive synchronization**:
```rust
// Bad: Lock contention
for item in items {
    state.lock().unwrap().process(item);  // Lock per item!
}
```

**✅ Batch operations**:
```rust
// Good: Batch updates
let batch: Vec<_> = items.iter().map(|i| process(i)).collect();
state.lock().unwrap().update_batch(batch);
```

**❌ Ignoring memory ordering**:
```rust
// Bad: Wrong ordering can cause bugs
counter.fetch_add(1, Ordering::Relaxed);  // May not be visible!
```

**✅ Appropriate ordering**:
```rust
// Good: Correct ordering for use case
counter.fetch_add(1, Ordering::SeqCst);  // or AcqRel if appropriate
```

## Testing Performance Optimizations

**Benchmark Framework**:
```bash
# Criterion benchmarks
cargo bench

# Python benchmarking
python -m pytest benchmarks/ --benchmark-only
```

**Correctness Validation**:
- Thread sanitizer (`-Zsanitizer=thread`)
- Miri for undefined behavior detection
- Extensive property testing
- Stress testing under load

**Performance Validation**:
- Compare with baseline implementation
- Measure speedup vs single-threaded
- Profile GIL usage patterns
- Monitor resource utilization

## Related Skills

- **pyo3-fundamentals**: Core PyO3 concepts and GIL basics
- **pyo3-async-embedded-wasm**: Async patterns (complementary parallelism)
- **pyo3-testing-quality-ci**: Testing parallel code
- **pyo3-data-science-ml**: Applying parallelism to data processing

## Expected Outcomes

After mastering this skill, you will be able to:

1. **Optimize GIL usage** for maximum performance
2. **Implement parallel algorithms** using Rayon and custom thread pools
3. **Use lock-free data structures** for concurrent access
4. **Profile and measure** performance improvements accurately
5. **Prepare code** for nogil Python 3.13+
6. **Build production systems** that leverage multi-core hardware efficiently
7. **Balance** performance, safety, and maintainability

## Success Metrics

- Achieve near-linear speedup for embarrassingly parallel workloads
- Minimize GIL hold time to < 1% for CPU-bound operations
- Zero data races (guaranteed by Rust's type system)
- Throughput improvements of 2-8x on multi-core systems
- Clean profiling results showing efficient parallelism

---

**Skill Level**: Advanced
**Estimated Learning Time**: 8-10 hours (study) + 20-30 hours (practice)
**Prerequisites**: pyo3-fundamentals, Rust concurrency basics
**Next Steps**: pyo3-async-embedded-wasm, pyo3-data-science-ml
