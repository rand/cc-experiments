# Example 02: Multi-dimensional Array Operations with ndarray

Demonstrates working with multi-dimensional arrays using Rust's `ndarray` crate integrated with NumPy through PyO3.

## What You'll Learn

- Converting between NumPy arrays and ndarray
- Matrix operations (transpose, multiplication)
- Row and column-wise operations
- Array normalization techniques
- Slicing and reshaping arrays
- Advanced array manipulation (outer product, stacking)

## Key Concepts

### ndarray Integration

The `ndarray` crate provides powerful n-dimensional array operations in Rust:

```rust
use numpy::{PyReadonlyArray2, ToPyArray};
use ndarray::Array2;

fn transpose<'py>(
    py: Python<'py>,
    array: PyReadonlyArray2<f64>
) -> PyResult<&'py PyArray2<f64>> {
    let arr = array.as_array();  // Convert to ndarray
    let transposed = arr.t().to_owned();
    Ok(transposed.to_pyarray(py))  // Convert back to NumPy
}
```

### Zero-Copy Views

Use `as_array()` to get zero-copy views of NumPy arrays:

```rust
let arr = array.as_array();  // ArrayView, no copy
let result = &arr * 2.0 + 1.0;  // Efficient operations
```

### Axis Operations

Operations along specific axes:

```rust
let row_sums = arr.sum_axis(ndarray::Axis(1));  // Sum along rows
let col_sums = arr.sum_axis(ndarray::Axis(0));  // Sum along columns
```

## Functions Provided

### Matrix Operations
- `transpose(array)`: Matrix transpose
- `matmul(a, b)`: Matrix multiplication
- `outer_product(a, b)`: Outer product of two vectors
- `identity(size)`: Create identity matrix

### Aggregations
- `sum_rows(array)`: Sum each row
- `sum_cols(array)`: Sum each column
- `get_diagonal(array)`: Extract diagonal elements

### Transformations
- `normalize_rows(array)`: Normalize rows (zero mean, unit variance)
- `element_wise_op(array)`: Element-wise operations
- `reshape(array, rows, cols)`: Reshape 1D to 2D
- `slice_array(array, ...)`: Extract subarray

### Stacking
- `vstack(a, b)`: Stack arrays vertically

## Building and Testing

```bash
# Install dependencies
pip install maturin numpy pytest

# Build and install
maturin develop

# Run tests
python test_example.py

# Or use pytest
pytest test_example.py -v
```

## Usage Examples

```python
import numpy as np
import ndarray_ops

# Matrix operations
a = np.array([[1.0, 2.0],
              [3.0, 4.0]])
b = np.array([[5.0, 6.0],
              [7.0, 8.0]])

transposed = ndarray_ops.transpose(a)
print(transposed)

product = ndarray_ops.matmul(a, b)
print(product)

# Row/column operations
arr = np.array([[1.0, 2.0, 3.0],
                [4.0, 5.0, 6.0]])

row_sums = ndarray_ops.sum_rows(arr)  # [6.0, 15.0]
col_sums = ndarray_ops.sum_cols(arr)  # [5.0, 7.0, 9.0]

# Normalization
normalized = ndarray_ops.normalize_rows(arr)
print("Mean per row:", np.mean(normalized, axis=1))  # ~[0, 0]
print("Std per row:", np.std(normalized, axis=1))    # ~[1, 1]

# Reshaping and slicing
flat = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
reshaped = ndarray_ops.reshape(flat, 2, 3)

sliced = ndarray_ops.slice_array(reshaped, 0, 2, 1, 3)

# Advanced operations
x = np.array([1.0, 2.0, 3.0])
y = np.array([4.0, 5.0])
outer = ndarray_ops.outer_product(x, y)
print(outer)  # 3x2 matrix

identity = ndarray_ops.identity(3)
print(identity)  # 3x3 identity matrix
```

## Real-World Applications

- Linear algebra computations
- Machine learning feature transformations
- Image processing operations
- Statistical analysis
- Scientific computing
- Neural network operations

## Performance Notes

- ndarray provides efficient vectorized operations
- Zero-copy conversion between NumPy and ndarray when possible
- Axis operations are optimized for cache locality
- Matrix multiplication uses efficient algorithms

## Next Steps

- Example 03: Parallel NumPy processing with Rayon
- Example 04: Creating Pandas DataFrames from Rust
- Example 05: GroupBy and aggregation operations

## Common Patterns

### Converting NumPy to ndarray
```rust
let arr = array.as_array();  // ArrayView (zero-copy)
let owned = arr.to_owned();  // Array (copied)
```

### Converting ndarray to NumPy
```rust
let result: Array2<f64> = ...;
Ok(result.to_pyarray(py))
```

### Axis Operations
```rust
let row_op = arr.sum_axis(ndarray::Axis(1));    // Operate on rows
let col_op = arr.sum_axis(ndarray::Axis(0));    // Operate on columns
```

### Shape Validation
```rust
if arr_a.shape()[1] != arr_b.shape()[0] {
    return Err(PyValueError::new_err("Incompatible shapes"));
}
```
