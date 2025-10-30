# Example 01: Basic GIL Release

This example demonstrates the fundamental concept of releasing Python's Global Interpreter Lock (GIL) in PyO3 to enable true parallel execution of Rust code.

## Concepts Covered

- **GIL Release with `py.allow_threads()`**: The basic mechanism for releasing the GIL
- **Performance Impact**: Measuring the overhead of GIL release
- **Concurrent Execution**: Demonstrating true parallelism vs serialization
- **I/O Operations**: Releasing GIL during sleep/blocking operations

## Key Functions

### `compute_primes_blocking(n: u64) -> usize`
Computes primes without releasing the GIL. Other Python threads cannot run during this operation.

### `compute_primes_releasing(py: Python, n: u64) -> usize`
Computes primes while releasing the GIL. Other Python threads can execute concurrently.

### `benchmark_gil_release(py: Python, n: u64, iterations: usize) -> (f64, f64)`
Measures the performance overhead of GIL release operations.

### `parallel_compute(py: Python, n: u64, thread_count: usize) -> Vec<usize>`
Demonstrates multi-threaded computation with GIL release.

## Building and Testing

```bash
# Install maturin if not already installed
pip install maturin

# Build and install the extension
maturin develop --release

# Run tests
python test_example.py
```

## Expected Output

The tests demonstrate:

1. **Same Results**: Both blocking and releasing versions compute the same results
2. **Minimal Overhead**: GIL release has minimal performance impact (<5% typically)
3. **True Parallelism**: Releasing version shows significant speedup with multiple threads
4. **Concurrent I/O**: Sleep operations run concurrently when GIL is released

## Performance Notes

- **Single-threaded**: GIL release has minimal overhead (typically <5%)
- **Multi-threaded**: GIL release enables near-linear speedup with CPU cores
- **When to Release**: Release GIL for CPU-intensive work or blocking I/O
- **When Not to Release**: Don't release for trivial operations (<1ms) due to overhead

## Learning Points

1. **`py.allow_threads(|| { ... })`**: The basic pattern for GIL release
2. **Thread Safety**: Code inside `allow_threads` cannot access Python objects
3. **Performance Trade-offs**: Small overhead in single-threaded, huge gains in multi-threaded
4. **Rust Safety**: Rust's ownership system ensures thread safety without runtime overhead

## Next Steps

- Example 02: Basic parallel processing with Rayon
- Example 03: Performance timing and benchmarking utilities
