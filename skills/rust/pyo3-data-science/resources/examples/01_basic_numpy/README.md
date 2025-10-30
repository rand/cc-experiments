# Example 01: Basic NumPy Array Operations

A foundational example demonstrating basic NumPy array operations using PyO3 and the `numpy` crate.

## What You'll Learn

- Reading NumPy arrays from Python into Rust
- Performing basic mathematical operations (sum, mean, min, max)
- Element-wise array operations
- Creating NumPy arrays from Rust
- Type validation and error handling
- Working with 1D and 2D arrays

## Key Concepts

### PyReadonlyArray

`PyReadonlyArray1<T>` provides read-only access to NumPy arrays:

```rust
fn sum_array(array: PyReadonlyArray1<f64>) -> PyResult<f64> {
    Ok(array.as_slice()?.iter().sum())
}
```

### Creating NumPy Arrays

Use `PyArray1::from_vec` to create arrays from Rust vectors:

```rust
fn create_zeros<'py>(py: Python<'py>, size: usize) -> PyResult<&'py PyArray1<f64>> {
    let data = vec![0.0; size];
    Ok(PyArray1::from_vec(py, data))
}
```

### Error Handling

Proper error handling for edge cases:

```rust
if slice.is_empty() {
    return Err(pyo3::exceptions::PyValueError::new_err("Cannot compute mean of empty array"));
}
```

## Functions Provided

### Statistical Operations
- `sum_array(array)`: Sum all elements
- `mean_array(array)`: Calculate mean value
- `min_array(array)`: Find minimum value
- `max_array(array)`: Find maximum value

### Array Operations
- `multiply_scalar(array, scalar)`: Element-wise multiplication
- `add_arrays(a, b)`: Element-wise addition
- `dot_product(a, b)`: Compute dot product

### Array Creation
- `create_range(start, end, step)`: Create range array
- `create_zeros(size)`: Create array of zeros
- `create_ones(size)`: Create array of ones

### Validation
- `validate_range(array, min, max)`: Check if values are in range
- `sum_2d(array)`: Sum 2D array elements

## Building and Testing

```bash
# Install dependencies
pip install maturin numpy pytest

# Build and install in development mode
maturin develop

# Run tests
python test_example.py

# Or use pytest
pytest test_example.py -v
```

## Usage Examples

```python
import numpy as np
import basic_numpy

# Basic statistics
arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print(basic_numpy.sum_array(arr))   # 15.0
print(basic_numpy.mean_array(arr))  # 3.0
print(basic_numpy.min_array(arr))   # 1.0
print(basic_numpy.max_array(arr))   # 5.0

# Array operations
doubled = basic_numpy.multiply_scalar(arr, 2.0)
print(doubled)  # [2.0, 4.0, 6.0, 8.0, 10.0]

a = np.array([1.0, 2.0, 3.0])
b = np.array([4.0, 5.0, 6.0])
sum_ab = basic_numpy.add_arrays(a, b)
print(sum_ab)  # [5.0, 7.0, 9.0]

dot = basic_numpy.dot_product(a, b)
print(dot)  # 32.0

# Array creation
zeros = basic_numpy.create_zeros(5)
ones = basic_numpy.create_ones(3)
range_arr = basic_numpy.create_range(0, 10, 2)
print(range_arr)  # [0, 2, 4, 6, 8]

# Validation
arr = np.array([1.0, 2.0, 3.0])
is_valid = basic_numpy.validate_range(arr, 0.0, 5.0)
print(is_valid)  # True
```

## Real-World Applications

- Data preprocessing and cleaning
- Statistical analysis of datasets
- Numerical computations
- Array transformations and filtering
- Input validation for ML pipelines

## Performance Notes

- Uses `as_slice()` for zero-copy access to NumPy arrays
- Efficient iterators for element-wise operations
- Minimal overhead for simple operations
- Error handling adds safety without significant cost

## Next Steps

- Example 02: Multi-dimensional array operations with ndarray
- Example 03: Parallel NumPy processing with Rayon
- Example 04: Creating Pandas DataFrames from Rust

## Common Patterns

### Reading Arrays
```rust
let slice = array.as_slice()?;  // Get slice of NumPy array
```

### Creating Arrays
```rust
let data: Vec<f64> = vec![1.0, 2.0, 3.0];
let numpy_array = PyArray1::from_vec(py, data);
```

### Shape Validation
```rust
if slice_a.len() != slice_b.len() {
    return Err(pyo3::exceptions::PyValueError::new_err("Shape mismatch"));
}
```
