# Example 02: Basic Parallel Processing with Rayon

This example demonstrates parallel operations using Rayon, a data-parallelism library for Rust that makes it easy to convert sequential computations into parallel ones.

## Concepts Covered

- **Parallel Iterators**: `.par_iter()` for automatic parallelization
- **Map/Filter/Reduce**: Parallel functional operations
- **Parallel Sorting**: Efficient parallel sort with `.par_sort_by()`
- **Chunked Processing**: Custom chunk sizes for load balancing
- **Nested Parallelism**: Matrix operations with nested parallel loops

## Key Functions

### Basic Operations
- `parallel_sum(numbers)`: Parallel sum using `.par_iter().sum()`
- `parallel_square(numbers)`: Parallel map operation
- `parallel_filter_even(numbers)`: Parallel filter operation
- `parallel_max(numbers)`: Parallel reduce to find maximum
- `parallel_sort(numbers)`: Parallel sort

### Advanced Operations
- `parallel_mandelbrot(...)`: Complex computation demonstrating parallelism benefits
- `parallel_sum_chunked(numbers, chunk_size)`: Control work distribution with chunks
- `parallel_word_count(documents)`: Parallel string processing
- `parallel_matrix_multiply(a, b)`: Nested parallelism example

## Building and Testing

```bash
# Install dependencies
pip install maturin

# Build and install
maturin develop --release

# Run tests
python test_example.py
```

## Expected Output

The tests demonstrate:

1. **Correctness**: Parallel results match sequential/Python results
2. **Performance**: Speedup on large datasets (5-10M+ elements)
3. **Scalability**: Performance scales with available CPU cores
4. **Versatility**: Works with numbers, strings, matrices

## Performance Characteristics

### When Rayon Helps
- Large datasets (1M+ elements)
- CPU-intensive operations per element
- Independent operations (no dependencies between elements)

### When Rayon Doesn't Help
- Small datasets (<10K elements) - overhead dominates
- Memory-bound operations - already at bandwidth limit
- Operations with dependencies - can't parallelize

### Typical Speedups
- **Sum/aggregate**: 4-8x on 8-core machine
- **Map operations**: 6-12x (very parallel)
- **Complex compute**: 10-15x (Mandelbrot example)
- **Sort**: 3-6x (more complex coordination)

## Rayon Patterns

### Basic Pattern
```rust
py.allow_threads(|| {
    data.par_iter()
        .map(|x| expensive_operation(x))
        .collect()
})
```

### With Chunk Size
```rust
py.allow_threads(|| {
    data.par_chunks(chunk_size)
        .map(|chunk| process_chunk(chunk))
        .collect()
})
```

### Nested Parallelism
```rust
py.allow_threads(|| {
    (0..rows).into_par_iter()
        .map(|i| {
            (0..cols).map(|j| compute(i, j)).collect()
        })
        .collect()
})
```

## Learning Points

1. **Easy Parallelism**: Change `.iter()` to `.par_iter()` for automatic parallelization
2. **GIL Release Required**: Always wrap Rayon calls in `py.allow_threads()`
3. **Thread Pool**: Rayon manages a thread pool automatically
4. **Work Stealing**: Rayon uses work stealing for load balancing
5. **No Data Races**: Rust's type system prevents data races at compile time

## Tuning Tips

- **Chunk Size**: Adjust for load balancing vs overhead trade-off
- **Data Size**: Consider sequential for small datasets
- **CPU vs Memory**: Parallelism helps CPU-bound, not memory-bound
- **Core Count**: Speedup typically 0.7-0.9x per core due to overhead

## Next Steps

- Example 03: Performance timing and detailed benchmarking
- Example 04: Custom thread pools for more control
