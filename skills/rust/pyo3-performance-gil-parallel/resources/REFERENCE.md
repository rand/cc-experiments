# PyO3 Performance: GIL & Parallel Execution - Comprehensive Reference

Complete guide to building high-performance PyO3 extensions through GIL optimization, parallel execution, sub-interpreters, and lock-free programming.

**Version**: 1.0.0
**PyO3**: 0.20+
**Python**: 3.8+ (3.13+ for nogil)
**Last Updated**: 2025-10-30

---

## Table of Contents

1. [GIL Fundamentals](#gil-fundamentals)
2. [GIL Release Strategies](#gil-release-strategies)
3. [Parallel Execution with Rayon](#parallel-execution-with-rayon)
4. [Thread Pools and Workers](#thread-pools-and-workers)
5. [Lock-Free Data Structures](#lock-free-data-structures)
6. [Sub-Interpreters](#sub-interpreters)
7. [Custom Allocators](#custom-allocators)
8. [nogil Python 3.13+](#nogil-python-313)
9. [Performance Profiling](#performance-profiling)
10. [Best Practices](#best-practices)

---

## 1. GIL Fundamentals

### What is the GIL?

The **Global Interpreter Lock (GIL)** is a mutex that protects access to Python objects, preventing multiple native threads from executing Python bytecodes simultaneously.

**Key Properties**:
- Only one thread can execute Python code at a time
- Protects Python's memory management (reference counting)
- Released during I/O operations automatically
- Must be explicitly released for CPU-bound Rust code

**Impact on Performance**:
```python
# Python threads don't provide true parallelism for CPU-bound work
import threading

def cpu_work():
    sum(range(10000000))

# These run sequentially due to GIL
t1 = threading.Thread(target=cpu_work)
t2 = threading.Thread(target=cpu_work)
t1.start(); t2.start()
t1.join(); t2.join()
```

### PyO3 GIL Token

PyO3 represents GIL ownership with the `Python<'py>` token:

```rust
use pyo3::prelude::*;

#[pyfunction]
fn needs_gil(py: Python) -> PyResult<()> {
    // py token proves we hold the GIL
    // Can safely access Python objects
    let sys = py.import("sys")?;
    let version: String = sys.getattr("version")?.extract()?;
    println!("Python {}", version);
    Ok(())
}
```

**Lifetime Management**:
```rust
// GIL token is lifetime-bound
fn example<'py>(py: Python<'py>) -> &'py PyAny {
    // Return value tied to GIL lifetime
    py.None()
}

// Common error: trying to store GIL-dependent data
// struct Bad {
//     obj: Py<PyAny>,  // ✅ Correct: Py<T> doesn't require GIL
//     any: &PyAny,      // ❌ Error: Can't store GIL-bound reference
// }
```

### When Python Holds the GIL

**Automatically Released**:
- I/O operations (`read`, `write`, `socket` operations)
- `time.sleep()`
- Blocking system calls
- Some C extension functions

**Always Held**:
- Python bytecode execution
- Object allocation/deallocation
- Reference counting operations
- CPython C API calls (unless explicitly released)

### GIL Acquisition Cost

```rust
use std::time::Instant;

fn measure_gil_acquisition() {
    let iterations = 10000;
    let start = Instant::now();

    for _ in 0..iterations {
        Python::with_gil(|_py| {
            // Minimal work
        });
    }

    let elapsed = start.elapsed();
    println!("Average GIL acquisition: {:?}", elapsed / iterations);
    // Typically 100-500ns on modern hardware
}
```

**Key Insight**: GIL acquisition is cheap (~100-500ns), but becomes significant when done millions of times per second.

---

## 2. GIL Release Strategies

### Basic GIL Release

```rust
use pyo3::prelude::*;

#[pyfunction]
fn compute_intensive(py: Python, data: Vec<f64>) -> f64 {
    // Release GIL for CPU-bound work
    py.allow_threads(|| {
        // Rust code runs without GIL
        // Other Python threads can execute
        data.iter().sum()
    })
}
```

**How `allow_threads` Works**:
1. Saves current GIL state
2. Releases the GIL
3. Executes closure
4. Re-acquires GIL
5. Restores state

### When to Release the GIL

**✅ Release for**:
- CPU-intensive computations
- Long-running algorithms
- Parallel data processing
- Blocking operations (if not already released)

**❌ Don't release for**:
- Quick operations (< 1μs)
- Code that accesses Python objects
- Operations requiring Python API calls

### Example: Image Processing

```rust
use pyo3::prelude::*;
use image::{DynamicImage, GenericImageView};

#[pyfunction]
fn process_image(py: Python, path: String) -> PyResult<Vec<u8>> {
    // Load image with GIL (file I/O)
    let img = image::open(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    // Release GIL for CPU-intensive processing
    let processed = py.allow_threads(|| {
        let (width, height) = img.dimensions();
        let mut output = Vec::with_capacity((width * height * 3) as usize);

        // Process pixels (CPU-intensive)
        for pixel in img.pixels() {
            let (_x, _y, rgba) = pixel;
            output.push(rgba[0]);
            output.push(rgba[1]);
            output.push(rgba[2]);
        }

        output
    });

    Ok(processed)
}
```

### Nested GIL Operations

```rust
#[pyfunction]
fn nested_example(py: Python, data: Vec<Vec<f64>>) -> PyResult<Vec<f64>> {
    let results = py.allow_threads(|| {
        // Outer GIL release
        data.into_iter()
            .map(|chunk| {
                // Process chunk in Rust
                let sum: f64 = chunk.iter().sum();

                // Need to call Python? Re-acquire GIL
                Python::with_gil(|py| {
                    let math = py.import("math")?;
                    let sqrt = math.getattr("sqrt")?;
                    sqrt.call1((sum,))?.extract()
                })
            })
            .collect::<PyResult<Vec<f64>>>()
    })?;

    Ok(results)
}
```

**Warning**: Re-acquiring GIL inside `allow_threads` defeats the purpose. Redesign to minimize GIL acquisitions.

### GIL State Management

```rust
use pyo3::PyGILState;

fn check_gil_state() {
    match PyGILState::check_gil() {
        PyGILState::Held => println!("GIL is held"),
        PyGILState::NotHeld => println!("GIL is NOT held"),
    }
}
```

---

## 3. Parallel Execution with Rayon

### Rayon Basics

[Rayon](https://docs.rs/rayon/) provides data parallelism via work stealing:

```rust
use rayon::prelude::*;

#[pyfunction]
fn parallel_sum(py: Python, data: Vec<i64>) -> i64 {
    py.allow_threads(|| {
        data.par_iter()  // Parallel iterator
            .sum()
    })
}
```

**Key Methods**:
- `par_iter()`: Parallel iterator
- `par_chunks()`: Process in chunks
- `par_bridge()`: Convert iterator to parallel
- `par_extend()`: Parallel collection

### Parallel Map

```rust
#[pyfunction]
fn parallel_map(py: Python, data: Vec<f64>) -> Vec<f64> {
    py.allow_threads(|| {
        data.par_iter()
            .map(|x| x.powi(2) + 2.0 * x + 1.0)
            .collect()
    })
}
```

### Parallel Filter

```rust
#[pyfunction]
fn parallel_filter(py: Python, data: Vec<i64>, threshold: i64) -> Vec<i64> {
    py.allow_threads(|| {
        data.par_iter()
            .filter(|&&x| x > threshold)
            .copied()
            .collect()
    })
}
```

### Parallel Reduce

```rust
#[pyfunction]
fn parallel_max(py: Python, data: Vec<f64>) -> Option<f64> {
    py.allow_threads(|| {
        data.par_iter()
            .copied()
            .reduce(|| f64::NEG_INFINITY, f64::max)
            .into()
    })
}
```

### Chunked Parallel Processing

```rust
#[pyfunction]
fn parallel_chunked(py: Python, data: Vec<f64>, chunk_size: usize) -> Vec<f64> {
    py.allow_threads(|| {
        data.par_chunks(chunk_size)
            .map(|chunk| {
                // Process chunk
                chunk.iter().sum()
            })
            .collect()
    })
}
```

### Custom Thread Pool

```rust
use rayon::ThreadPoolBuilder;
use once_cell::sync::OnceCell;

static THREAD_POOL: OnceCell<rayon::ThreadPool> = OnceCell::new();

fn get_pool() -> &'static rayon::ThreadPool {
    THREAD_POOL.get_or_init(|| {
        ThreadPoolBuilder::new()
            .num_threads(8)
            .thread_name(|i| format!("pyo3-worker-{}", i))
            .build()
            .unwrap()
    })
}

#[pyfunction]
fn parallel_with_pool(py: Python, data: Vec<f64>) -> Vec<f64> {
    py.allow_threads(|| {
        get_pool().install(|| {
            data.par_iter()
                .map(|x| x * 2.0)
                .collect()
        })
    })
}
```

### Error Handling in Parallel Code

```rust
#[pyfunction]
fn parallel_with_errors(py: Python, data: Vec<f64>) -> PyResult<Vec<f64>> {
    py.allow_threads(|| {
        data.par_iter()
            .map(|&x| {
                if x < 0.0 {
                    Err(format!("Negative value: {}", x))
                } else {
                    Ok(x.sqrt())
                }
            })
            .collect::<Result<Vec<_>, _>>()
    })
    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e))
}
```

### Performance Tuning

**Chunk Size**:
```rust
// Too small: overhead dominates
data.par_chunks(10).for_each(|chunk| process(chunk));

// Too large: poor load balancing
data.par_chunks(1000000).for_each(|chunk| process(chunk));

// Good: balance overhead and work distribution
let chunk_size = (data.len() / rayon::current_num_threads()).max(1000);
data.par_chunks(chunk_size).for_each(|chunk| process(chunk));
```

---

## 4. Thread Pools and Workers

### Custom Worker Pool

```rust
use std::sync::mpsc::{channel, Sender, Receiver};
use std::sync::{Arc, Mutex};
use std::thread;

type Job = Box<dyn FnOnce() + Send + 'static>;

struct WorkerPool {
    workers: Vec<Worker>,
    sender: Option<Sender<Job>>,
}

struct Worker {
    id: usize,
    thread: Option<thread::JoinHandle<()>>,
}

impl WorkerPool {
    fn new(size: usize) -> WorkerPool {
        let (sender, receiver) = channel();
        let receiver = Arc::new(Mutex::new(receiver));

        let mut workers = Vec::with_capacity(size);

        for id in 0..size {
            workers.push(Worker::new(id, Arc::clone(&receiver)));
        }

        WorkerPool {
            workers,
            sender: Some(sender),
        }
    }

    fn execute<F>(&self, f: F)
    where
        F: FnOnce() + Send + 'static,
    {
        let job = Box::new(f);
        self.sender.as_ref().unwrap().send(job).unwrap();
    }
}

impl Worker {
    fn new(id: usize, receiver: Arc<Mutex<Receiver<Job>>>) -> Worker {
        let thread = thread::spawn(move || loop {
            let message = receiver.lock().unwrap().recv();

            match message {
                Ok(job) => {
                    println!("Worker {id} got a job; executing.");
                    job();
                }
                Err(_) => {
                    println!("Worker {id} disconnected; shutting down.");
                    break;
                }
            }
        });

        Worker {
            id,
            thread: Some(thread),
        }
    }
}

impl Drop for WorkerPool {
    fn drop(&mut self) {
        drop(self.sender.take());

        for worker in &mut self.workers {
            if let Some(thread) = worker.thread.take() {
                thread.join().unwrap();
            }
        }
    }
}
```

### PyO3 Integration

```rust
use pyo3::prelude::*;
use once_cell::sync::Lazy;

static POOL: Lazy<WorkerPool> = Lazy::new(|| WorkerPool::new(4));

#[pyfunction]
fn async_process(py: Python, data: Vec<f64>) -> PyResult<()> {
    POOL.execute(move || {
        // Process data without GIL
        let result: f64 = data.iter().sum();

        // Store result somewhere accessible to Python
        println!("Result: {}", result);
    });

    Ok(())
}
```

### Result Collection

```rust
use std::sync::mpsc::sync_channel;

#[pyfunction]
fn worker_with_result(py: Python, data: Vec<Vec<f64>>) -> PyResult<Vec<f64>> {
    let (tx, rx) = sync_channel(data.len());

    // Spawn workers
    for chunk in data {
        let tx = tx.clone();
        thread::spawn(move || {
            let result: f64 = chunk.iter().sum();
            tx.send(result).unwrap();
        });
    }
    drop(tx);  // Drop original sender

    // Collect results
    let results: Vec<f64> = rx.iter().collect();
    Ok(results)
}
```

---

## 5. Lock-Free Data Structures

### Atomic Operations

```rust
use std::sync::atomic::{AtomicU64, AtomicBool, Ordering};

#[pyclass]
struct AtomicCounter {
    count: AtomicU64,
    active: AtomicBool,
}

#[pymethods]
impl AtomicCounter {
    #[new]
    fn new() -> Self {
        Self {
            count: AtomicU64::new(0),
            active: AtomicBool::new(true),
        }
    }

    fn increment(&self) -> u64 {
        self.count.fetch_add(1, Ordering::SeqCst)
    }

    fn get(&self) -> u64 {
        self.count.load(Ordering::SeqCst)
    }

    fn set_active(&self, active: bool) {
        self.active.store(active, Ordering::Release);
    }

    fn is_active(&self) -> bool {
        self.active.load(Ordering::Acquire)
    }
}
```

### Memory Ordering

**Ordering Types**:
- `Relaxed`: No synchronization guarantees
- `Acquire`: Synchronizes with `Release` stores
- `Release`: Synchronizes with `Acquire` loads
- `AcqRel`: Both Acquire and Release
- `SeqCst`: Sequentially consistent (strongest, slowest)

**When to Use**:
```rust
// Relaxed: Counters where exact ordering doesn't matter
counter.fetch_add(1, Ordering::Relaxed);

// Acquire/Release: Flag synchronization
if flag.load(Ordering::Acquire) {
    // Safe to access data protected by flag
}
flag.store(true, Ordering::Release);

// SeqCst: When unsure or correctness is critical
counter.fetch_add(1, Ordering::SeqCst);
```

### Lock-Free Queue (crossbeam)

```rust
use crossbeam::queue::SegQueue;
use std::sync::Arc;

#[pyclass]
struct LockFreeQueue {
    queue: Arc<SegQueue<i64>>,
}

#[pymethods]
impl LockFreeQueue {
    #[new]
    fn new() -> Self {
        Self {
            queue: Arc::new(SegQueue::new()),
        }
    }

    fn push(&self, item: i64) {
        self.queue.push(item);
    }

    fn pop(&self) -> Option<i64> {
        self.queue.pop()
    }

    fn len(&self) -> usize {
        self.queue.len()
    }
}
```

### Concurrent HashMap (dashmap)

```rust
use dashmap::DashMap;
use std::sync::Arc;

#[pyclass]
struct ConcurrentDict {
    map: Arc<DashMap<String, i64>>,
}

#[pymethods]
impl ConcurrentDict {
    #[new]
    fn new() -> Self {
        Self {
            map: Arc::new(DashMap::new()),
        }
    }

    fn insert(&self, key: String, value: i64) {
        self.map.insert(key, value);
    }

    fn get(&self, key: String) -> Option<i64> {
        self.map.get(&key).map(|v| *v)
    }

    fn remove(&self, key: String) -> Option<i64> {
        self.map.remove(&key).map(|(_, v)| v)
    }

    fn len(&self) -> usize {
        self.map.len()
    }
}
```

### Arc and RwLock

```rust
use std::sync::{Arc, RwLock};
use std::collections::HashMap;

#[pyclass]
struct SharedState {
    data: Arc<RwLock<HashMap<String, Vec<f64>>>>,
}

#[pymethods]
impl SharedState {
    #[new]
    fn new() -> Self {
        Self {
            data: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn get(&self, key: String) -> Option<Vec<f64>> {
        self.data.read().unwrap()
            .get(&key)
            .cloned()
    }

    fn set(&self, key: String, value: Vec<f64>) {
        self.data.write().unwrap()
            .insert(key, value);
    }

    fn parallel_read(&self, py: Python, keys: Vec<String>) -> Vec<Option<Vec<f64>>> {
        py.allow_threads(|| {
            keys.par_iter()
                .map(|key| {
                    self.data.read().unwrap()
                        .get(key)
                        .cloned()
                })
                .collect()
        })
    }
}
```

---

## 6. Sub-Interpreters

### PEP 554 Overview

**Sub-interpreters** allow multiple Python interpreters in a single process:
- Each has its own GIL
- Isolated module state
- True parallelism for Python code

**Status**: PEP 554 approved, implementation ongoing in CPython 3.12+

### Current API (Limited)

```rust
// As of CPython 3.12, sub-interpreter support is limited
// Full PEP 554 API expected in later versions

use pyo3::prelude::*;

fn create_subinterpreter() -> PyResult<()> {
    // This is conceptual - actual API depends on CPython version
    Python::with_gil(|py| {
        // Would create isolated interpreter
        // Each interpreter has separate GIL
        // Can run Python code in parallel
        Ok(())
    })
}
```

### Use Cases

**Plugin Isolation**:
```rust
// Each plugin runs in separate interpreter
// Crashes/errors don't affect other plugins
// True isolation of global state
```

**Parallel Python Execution**:
```rust
// Execute Python code in parallel
// Each sub-interpreter has own GIL
// No GIL contention between interpreters
```

**Sandboxing**:
```rust
// Limited access to main interpreter
// Controlled import mechanisms
// Resource limits per interpreter
```

### Challenges

**Module Import**:
- Some C extensions don't support multiple interpreters
- Module state must be per-interpreter
- Import machinery complexity

**Data Sharing**:
- No direct object sharing between interpreters
- Must serialize/deserialize data
- Channels or shared memory needed

**Performance**:
- Interpreter creation overhead
- Memory usage per interpreter
- Coordination costs

---

## 7. Custom Allocators

### Why Custom Allocators?

**Benefits**:
- Reduce allocation overhead
- Improve cache locality
- Thread-local allocation (no contention)
- Specialized allocation patterns

### Using `jemalloc`

```toml
[dependencies]
jemallocator = "0.5"
```

```rust
#[global_allocator]
static GLOBAL: jemallocator::Jemalloc = jemallocator::Jemalloc;

#[pyfunction]
fn allocate_heavy_workload(data: Vec<Vec<f64>>) -> Vec<f64> {
    // Uses jemalloc instead of system allocator
    // Better performance for many allocations
    data.into_iter()
        .flat_map(|v| v.into_iter())
        .collect()
}
```

### Arena Allocation

```rust
use bumpalo::Bump;

#[pyfunction]
fn arena_example(py: Python, data: Vec<f64>) -> Vec<f64> {
    py.allow_threads(|| {
        let arena = Bump::new();

        // Allocate in arena
        let allocated: Vec<_> = data.iter()
            .map(|&x| {
                let ptr = arena.alloc(x * 2.0);
                *ptr
            })
            .collect();

        // Arena memory freed when dropped
        allocated
    })
}
```

### Object Pooling

```rust
use std::sync::Mutex;

struct Pool<T> {
    objects: Mutex<Vec<T>>,
    factory: Box<dyn Fn() -> T + Send + Sync>,
}

impl<T> Pool<T> {
    fn new<F>(factory: F) -> Self
    where
        F: Fn() -> T + Send + Sync + 'static,
    {
        Self {
            objects: Mutex::new(Vec::new()),
            factory: Box::new(factory),
        }
    }

    fn acquire(&self) -> T {
        self.objects.lock().unwrap()
            .pop()
            .unwrap_or_else(|| (self.factory)())
    }

    fn release(&self, object: T) {
        self.objects.lock().unwrap().push(object);
    }
}
```

---

## 8. nogil Python 3.13+

### PEP 703: Making the GIL Optional

**Overview**: Python 3.13+ introduces optional GIL-free mode.

**Build Flag**:
```bash
# Build Python without GIL
./configure --disable-gil
make
```

**Detection in Rust**:
```rust
#[cfg(Py_GIL_DISABLED)]
fn nogil_optimized() {
    // Optimized for free-threaded Python
    // No GIL overhead
}

#[cfg(not(Py_GIL_DISABLED))]
fn gil_aware() {
    // Traditional GIL management
}
```

### API Changes

**Reference Counting**:
```rust
// With GIL: Simple reference counting
// Without GIL: Atomic reference counting

#[cfg(Py_GIL_DISABLED)]
use std::sync::atomic::AtomicUsize;

// Reference count becomes atomic
```

**Object Access**:
```rust
// With GIL: Direct access OK
// Without GIL: Need per-object locks

#[cfg(Py_GIL_DISABLED)]
fn access_object(obj: &PyAny) -> PyResult<()> {
    // May need to acquire object-specific lock
    // Details depend on CPython implementation
    Ok(())
}
```

### Migration Strategy

**1. Write GIL-agnostic code**:
```rust
#[pyfunction]
fn portable(data: Vec<f64>) -> Vec<f64> {
    // This works with or without GIL
    data.iter().map(|x| x * 2.0).collect()
}
```

**2. Conditional optimization**:
```rust
#[pyfunction]
fn optimized(py: Python, data: Vec<f64>) -> Vec<f64> {
    #[cfg(not(Py_GIL_DISABLED))]
    {
        // Release GIL in traditional Python
        py.allow_threads(|| process(data))
    }

    #[cfg(Py_GIL_DISABLED)]
    {
        // No GIL to release, just process
        process(data)
    }
}
```

**3. Test both modes**:
```bash
# Test with GIL
python3.12 -m pytest tests/

# Test without GIL
python3.13-nogil -m pytest tests/
```

### Performance Implications

**With nogil**:
- ✅ True Python parallelism
- ✅ No GIL contention
- ❌ Atomic reference counting overhead
- ❌ Per-object locking overhead

**Trade-offs**:
- Single-threaded: May be slower (atomic ops)
- Multi-threaded: Much faster (no GIL bottleneck)

---

## 9. Performance Profiling

### py-spy

Profile Python and Rust together:

```bash
# Profile running process
py-spy record -o profile.svg --pid <PID>

# Profile command
py-spy record -o profile.svg -- python script.py

# Top-like view
py-spy top --pid <PID>
```

### cargo-flamegraph

Visualize Rust hot paths:

```bash
# Generate flamegraph
cargo flamegraph --bin my_app

# With release optimizations
cargo flamegraph --release --bin my_app
```

### Custom Instrumentation

```rust
use std::time::Instant;

#[pyfunction]
fn instrumented(py: Python, data: Vec<f64>) -> PyResult<(Vec<f64>, f64)> {
    let start = Instant::now();

    let result = py.allow_threads(|| {
        data.iter().map(|x| x * 2.0).collect()
    });

    let elapsed = start.elapsed().as_secs_f64();
    Ok((result, elapsed))
}
```

### GIL Profiler

```rust
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

static GIL_HOLD_TIME: AtomicU64 = AtomicU64::new(0);
static GIL_ACQUISITIONS: AtomicU64 = AtomicU64::new(0);

#[pyfunction]
fn profile_gil_usage(py: Python, data: Vec<f64>) -> PyResult<Vec<f64>> {
    let start = Instant::now();

    let result = py.allow_threads(|| {
        data.iter().map(|x| x * 2.0).collect()
    });

    let hold_time = start.elapsed().as_nanos() as u64;
    GIL_HOLD_TIME.fetch_add(hold_time, Ordering::Relaxed);
    GIL_ACQUISITIONS.fetch_add(1, Ordering::Relaxed);

    Ok(result)
}

#[pyfunction]
fn get_gil_stats() -> (f64, u64) {
    let total_time = GIL_HOLD_TIME.load(Ordering::Relaxed) as f64 / 1e9;
    let acquisitions = GIL_ACQUISITIONS.load(Ordering::Relaxed);
    (total_time, acquisitions)
}
```

---

## 10. Best Practices

### GIL Management

**✅ Do**:
- Release GIL for CPU-bound work > 1μs
- Hold GIL only when accessing Python objects
- Measure GIL hold time
- Minimize GIL acquisition frequency

**❌ Don't**:
- Release GIL for trivial operations
- Re-acquire GIL inside parallel loops
- Hold GIL across blocking operations
- Assume GIL release is always beneficial

### Parallelization

**✅ Do**:
- Use Rayon for data parallelism
- Choose appropriate chunk sizes
- Balance work across threads
- Handle errors properly in parallel code

**❌ Don't**:
- Parallelize small datasets (overhead > benefit)
- Ignore load balancing
- Share mutable state without synchronization
- Panic in parallel code (propagate errors)

### Lock-Free Programming

**✅ Do**:
- Use appropriate memory ordering
- Test thoroughly (especially on different CPUs)
- Document ordering choices
- Profile performance impact

**❌ Don't**:
- Use `Relaxed` ordering by default
- Assume sequential consistency
- Ignore platform differences
- Over-optimize prematurely

### Performance Optimization

**Process**:
1. **Measure**: Profile to find actual bottlenecks
2. **Analyze**: Identify GIL contention, lock contention, etc.
3. **Optimize**: Release GIL, parallelize, use lock-free structures
4. **Verify**: Ensure correctness (tests, sanitizers)
5. **Measure Again**: Validate improvements

**Common Pitfalls**:
- Optimizing wrong code (measure first!)
- Breaking correctness for performance
- Micro-optimizations (focus on hot paths)
- Ignoring memory allocation overhead

---

## Troubleshooting

### Deadlocks

**Symptom**: Program hangs

**Causes**:
- Circular wait for locks
- GIL + Mutex lock ordering issues
- Forgetting to release GIL

**Solutions**:
```rust
// Use timeout with locks
use std::time::Duration;

let data = match lock.try_lock_for(Duration::from_secs(5)) {
    Some(guard) => guard,
    None => return Err(PyErr::new::<pyo3::exceptions::PyTimeoutError, _>(
        "Lock timeout"
    )),
};
```

### Performance Issues

**Not Seeing Speedup**:
- Profile to verify parallelism
- Check GIL release effectiveness
- Verify thread utilization
- Measure actual work vs overhead

**Slower Than Expected**:
- Too many GIL acquisitions
- Poor work distribution
- Lock contention
- Excessive allocations

### Data Races

**Rust prevents data races at compile time**, but logical races are still possible:

```rust
// Logical race (not caught by compiler)
if counter.load(Ordering::Relaxed) < 100 {
    counter.fetch_add(1, Ordering::Relaxed);  // May exceed 100!
}

// Fix: Use atomic operation
counter.fetch_update(Ordering::SeqCst, Ordering::SeqCst, |val| {
    if val < 100 {
        Some(val + 1)
    } else {
        None
    }
});
```

---

## Summary

**Key Takeaways**:
1. **Release GIL** for CPU-bound Rust code with `py.allow_threads()`
2. **Use Rayon** for data parallelism (easiest approach)
3. **Minimize GIL acquisitions** (each costs ~100-500ns)
4. **Use lock-free structures** where appropriate (atomics, dashmap, crossbeam)
5. **Profile always** before and after optimizations
6. **Test correctness** thoroughly (thread sanitizer, stress tests)
7. **Prepare for nogil** Python 3.13+ with conditional compilation

**Performance Hierarchy**:
1. Algorithm choice (biggest impact)
2. GIL release for CPU-bound work
3. Parallel execution (Rayon)
4. Lock-free data structures
5. Custom allocators
6. Micro-optimizations (SIMD, etc.)

**Remember**: Correctness first, then performance. Rust ensures memory safety, but you must ensure logical correctness in concurrent code.

---

**End of Reference** | For examples, see `examples/` directory | For tools, see `scripts/`
