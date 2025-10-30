# Example 03: Parallel NumPy Processing with Rayon

Demonstrates high-performance parallel processing of NumPy arrays using Rust's Rayon library.

## What You'll Learn

- Parallel array transformations with Rayon
- GIL management for parallel operations
- Chunk-based parallel processing
- Parallel reductions and aggregations
- Performance optimization techniques
- When to use parallelization

## Key Concepts

### GIL Release for Parallelism

Always release the GIL before parallel operations:

```rust
let result: Vec<f64> = py.allow_threads(|| {
    slice.par_iter()
        .map(|&x| x * x)
        .collect()
});
```

### Parallel Iterators

Rayon provides parallel versions of iterator methods:

```rust
use rayon::prelude::*;

// Parallel map
slice.par_iter().map(|&x| x * x).collect()

// Parallel filter
slice.par_iter().filter(|&&x| x > threshold).copied().collect()

// Parallel fold
slice.par_iter().fold(|| 0.0, |sum, &x| sum + x)
```

### Parallel Reductions

Use `fold` and `reduce` for parallel aggregations:

```rust
let (sum, min, max) = slice.par_iter()
    .fold(
        || (0.0, f64::INFINITY, f64::NEG_INFINITY),
        |(sum, min, max), &x| (sum + x, min.min(x), max.max(x))
    )
    .reduce(
        || (0.0, f64::INFINITY, f64::NEG_INFINITY),
        |(s1, min1, max1), (s2, min2, max2)| {
            (s1 + s2, min1.min(min2), max1.max(max2))
        }
    );
```

## Functions Provided

### Transformations
- `parallel_square(array)`: Square elements in parallel
- `parallel_transform(array)`: Apply complex function in parallel
- `parallel_normalize(array)`: Normalize to zero mean, unit variance

### Aggregations
- `parallel_sum(array, chunk_size)`: Parallel sum with chunks
- `parallel_stats(array)`: Compute sum, mean, min, max in parallel
- `parallel_cumsum(array)`: Cumulative sum

### Operations
- `parallel_filter(array, threshold)`: Filter values in parallel
- `parallel_multiply(a, b)`: Element-wise multiplication
- `parallel_window_sum(array, window_size)`: Sliding window sums

## Building and Testing

```bash
# Install dependencies
pip install maturin numpy pytest

# Build and install
maturin develop --release  # Use release mode for performance testing

# Run tests
python test_example.py

# Or use pytest
pytest test_example.py -v
```

## Usage Examples

```python
import numpy as np
import parallel_numpy

# Large array for parallel processing
arr = np.random.rand(1000000)

# Parallel transformations
squared = parallel_numpy.parallel_square(arr)
transformed = parallel_numpy.parallel_transform(arr)

# Parallel statistics
sum_val, mean_val, min_val, max_val = parallel_numpy.parallel_stats(arr)
print(f"Mean: {mean_val}, Min: {min_val}, Max: {max_val}")

# Parallel normalization
normalized = parallel_numpy.parallel_normalize(arr)
print(f"Normalized mean: {np.mean(normalized):.10f}")  # ~0.0
print(f"Normalized std: {np.std(normalized):.10f}")    # ~1.0

# Parallel filtering
large_values = parallel_numpy.parallel_filter(arr, threshold=0.8)
print(f"Values > 0.8: {len(large_values)}")

# Element-wise operations
a = np.random.rand(1000000)
b = np.random.rand(1000000)
product = parallel_numpy.parallel_multiply(a, b)

# Window operations
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
window_sums = parallel_numpy.parallel_window_sum(data, window_size=3)
print(window_sums)  # [6.0, 9.0, 12.0]

# Cumulative sum
cumsum = parallel_numpy.parallel_cumsum(data)
print(cumsum)  # [1.0, 3.0, 6.0, 10.0, 15.0]
```

## Real-World Applications

- Large-scale data preprocessing
- Feature engineering for ML
- Statistical analysis of large datasets
- Time series processing
- Image and signal processing
- Scientific computing workflows

## Performance Notes

### When to Use Parallelization

Parallelization helps when:
- Arrays are large (typically > 10,000 elements)
- Operations are computationally expensive
- GIL can be released (pure Rust operations)

Parallelization may hurt when:
- Arrays are small (overhead > benefit)
- Operations are simple (memory bandwidth bound)
- Can't release GIL

### Benchmarking Results

On a 4-core machine with 100,000 element array:
- Simple operations (square): 2-3x speedup
- Complex operations (transform): 3-4x speedup
- Reductions (sum, stats): 2-3x speedup

### Optimization Tips

1. Always release GIL: `py.allow_threads(|| ...)`
2. Use appropriate chunk size for chunked operations
3. Profile before optimizing
4. Consider memory bandwidth limitations
5. Use release builds for benchmarking

## Next Steps

- Example 04: Creating Pandas DataFrames from Rust
- Example 05: GroupBy and aggregation operations
- Example 06: Basic Polars DataFrame operations

## Common Patterns

### Parallel Map
```rust
let result: Vec<f64> = py.allow_threads(|| {
    slice.par_iter().map(|&x| compute(x)).collect()
});
```

### Parallel Fold-Reduce
```rust
let sum = py.allow_threads(|| {
    slice.par_iter()
        .fold(|| 0.0, |acc, &x| acc + x)
        .sum()
});
```

### Parallel Filter
```rust
let filtered: Vec<f64> = py.allow_threads(|| {
    slice.par_iter()
        .filter(|&&x| predicate(x))
        .copied()
        .collect()
});
```
