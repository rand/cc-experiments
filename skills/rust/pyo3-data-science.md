---
name: pyo3-data-science
description: PyO3 for data science and ML including numpy integration, Polars DataFrames, Arrow/Parquet streaming, ONNX Runtime
skill_id: rust-pyo3-data-science
title: PyO3 Data Science Integration
category: rust
subcategory: pyo3
complexity: advanced
prerequisites:
  - rust-pyo3-basics-types-conversions
  - rust-pyo3-collections-iterators
  - rust-pyo3-performance-gil-parallel
tags:
  - rust
  - python
  - pyo3
  - numpy
  - pandas
  - polars
  - arrow
  - parquet
  - data-science
  - analytics
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Master NumPy array integration with PyO3
  - Build high-performance Pandas extensions
  - Integrate with Polars DataFrames
  - Handle Apache Arrow and Parquet formats
  - Implement parallel data processing pipelines
  - Optimize memory usage for large datasets
  - Create zero-copy data transformations
  - Build production data science libraries
related_skills:
  - rust-pyo3-performance-gil-parallel
  - rust-pyo3-collections-iterators
  - data-processing-parallel
---

# PyO3 Data Science Integration

## Overview

Master the integration of PyO3 with the Python data science ecosystem. Learn to work with NumPy arrays, Pandas DataFrames, Polars, Apache Arrow, and build high-performance data processing pipelines that leverage Rust's speed and safety.

## Prerequisites

- **Required**: PyO3 basics, NumPy fundamentals, understanding of data structures
- **Recommended**: Pandas/Polars experience, Arrow format knowledge, parallel processing
- **Tools**: pyo3, numpy (rust-numpy), polars, arrow-rs, parquet

## Learning Path

### 1. NumPy Array Integration

NumPy is the foundation of Python's scientific computing ecosystem. The `numpy` crate provides PyO3 bindings.

#### Setup

```toml
# Cargo.toml
[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
numpy = "0.20"
ndarray = "0.15"
```

#### Reading NumPy Arrays

```rust
use pyo3::prelude::*;
use numpy::{PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};

#[pyfunction]
fn sum_array(array: PyReadonlyArray1<f64>) -> f64 {
    array.as_slice().unwrap().iter().sum()
}

#[pyfunction]
fn sum_2d(array: PyReadonlyArray2<f64>) -> f64 {
    array.as_slice().unwrap().iter().sum()
}

#[pyfunction]
fn multiply_scalar(array: PyReadonlyArray1<f64>, scalar: f64) -> Py<PyArray1<f64>> {
    Python::with_gil(|py| {
        let result: Vec<f64> = array.as_slice()
            .unwrap()
            .iter()
            .map(|&x| x * scalar)
            .collect();

        PyArray1::from_vec(py, result).to_owned()
    })
}
```

```python
import numpy as np
from my_extension import sum_array, sum_2d, multiply_scalar

# 1D array
arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
total = sum_array(arr)  # 15.0

# 2D array
arr_2d = np.array([[1.0, 2.0], [3.0, 4.0]])
total = sum_2d(arr_2d)  # 10.0

# Transform array
result = multiply_scalar(arr, 2.0)  # [2.0, 4.0, 6.0, 8.0, 10.0]
```

#### Creating NumPy Arrays

```rust
use numpy::PyArray1;

#[pyfunction]
fn create_range(py: Python, n: usize) -> Py<PyArray1<i32>> {
    let data: Vec<i32> = (0..n as i32).collect();
    PyArray1::from_vec(py, data).to_owned()
}

#[pyfunction]
fn create_zeros(py: Python, n: usize) -> Py<PyArray1<f64>> {
    let data = vec![0.0; n];
    PyArray1::from_vec(py, data).to_owned()
}
```

#### Multi-dimensional Arrays

```rust
use numpy::{PyArray2, PyReadonlyArray2};

#[pyfunction]
fn transpose_2d<'py>(
    py: Python<'py>,
    array: PyReadonlyArray2<f64>
) -> &'py PyArray2<f64> {
    let shape = array.shape();
    let (rows, cols) = (shape[0], shape[1]);

    let mut result = vec![0.0; rows * cols];
    let slice = array.as_slice().unwrap();

    for i in 0..rows {
        for j in 0..cols {
            result[j * rows + i] = slice[i * cols + j];
        }
    }

    PyArray2::from_vec2(py, &vec![vec![0.0; rows]; cols]).unwrap()
}

#[pyfunction]
fn matrix_multiply<'py>(
    py: Python<'py>,
    a: PyReadonlyArray2<f64>,
    b: PyReadonlyArray2<f64>
) -> PyResult<&'py PyArray2<f64>> {
    let a_shape = a.shape();
    let b_shape = b.shape();

    if a_shape[1] != b_shape[0] {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Incompatible matrix dimensions"
        ));
    }

    let (m, n, p) = (a_shape[0], a_shape[1], b_shape[1]);
    let mut result = vec![0.0; m * p];

    let a_slice = a.as_slice().unwrap();
    let b_slice = b.as_slice().unwrap();

    for i in 0..m {
        for j in 0..p {
            let mut sum = 0.0;
            for k in 0..n {
                sum += a_slice[i * n + k] * b_slice[k * p + j];
            }
            result[i * p + j] = sum;
        }
    }

    // Convert to 2D array (simplified)
    Ok(PyArray2::from_vec2(py, &vec![vec![0.0; p]; m]).unwrap())
}
```

### 2. Integration with ndarray

The `ndarray` crate provides n-dimensional arrays in Rust, similar to NumPy.

```rust
use ndarray::{Array1, Array2, ArrayView1, s};
use numpy::{PyArray1, PyReadonlyArray1, ToPyArray};

#[pyfunction]
fn process_with_ndarray<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>
) -> &'py PyArray1<f64> {
    // Convert to ndarray for processing
    let arr = array.as_array();

    // Use ndarray operations
    let result = &arr * 2.0 + 1.0;

    // Convert back to NumPy
    result.to_pyarray(py)
}

#[pyfunction]
fn parallel_process<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>
) -> &'py PyArray1<f64> {
    use rayon::prelude::*;

    let arr = array.as_array();

    // Release GIL for parallel processing
    py.allow_threads(|| {
        let result: Vec<f64> = arr.par_iter()
            .map(|&x| x.powi(2))
            .collect();

        Python::with_gil(|py| {
            PyArray1::from_vec(py, result)
        })
    })
}
```

### 3. Pandas DataFrame Integration

Pandas DataFrames are collections of Series (1D arrays).

```rust
use pyo3::types::{PyDict, PyList};
use numpy::PyArray1;

#[pyfunction]
fn create_dataframe(py: Python) -> PyResult<PyObject> {
    let pd = py.import("pandas")?;

    // Create data dict
    let data = PyDict::new(py);
    data.set_item("a", PyArray1::from_vec(py, vec![1, 2, 3]))?;
    data.set_item("b", PyArray1::from_vec(py, vec![4.0, 5.0, 6.0]))?;
    data.set_item("c", vec!["x", "y", "z"])?;

    // Create DataFrame
    let df = pd.call_method1("DataFrame", (data,))?;
    Ok(df.into())
}

#[pyfunction]
fn process_dataframe(py: Python, df: &PyAny) -> PyResult<PyObject> {
    // Extract column as NumPy array
    let column_a = df.get_item("a")?;
    let values: PyReadonlyArray1<i32> = column_a.getattr("values")?.extract()?;

    // Process data
    let processed: Vec<i32> = values.as_slice()
        .unwrap()
        .iter()
        .map(|&x| x * 2)
        .collect();

    // Create new Series
    let pd = py.import("pandas")?;
    let new_series = pd.call_method1(
        "Series",
        (PyArray1::from_vec(py, processed),)
    )?;

    Ok(new_series.into())
}

#[pyfunction]
fn fast_groupby(py: Python, df: &PyAny) -> PyResult<PyObject> {
    // Extract data from DataFrame
    let group_col: PyReadonlyArray1<i32> = df
        .get_item("group")?
        .getattr("values")?
        .extract()?;

    let value_col: PyReadonlyArray1<f64> = df
        .get_item("value")?
        .getattr("values")?
        .extract()?;

    // Fast groupby in Rust
    use std::collections::HashMap;
    let mut groups: HashMap<i32, Vec<f64>> = HashMap::new();

    for (g, v) in group_col.as_slice().unwrap().iter()
        .zip(value_col.as_slice().unwrap().iter()) {
        groups.entry(*g).or_insert_with(Vec::new).push(*v);
    }

    // Calculate group means
    let means: HashMap<i32, f64> = groups.into_iter()
        .map(|(k, v)| {
            let sum: f64 = v.iter().sum();
            (k, sum / v.len() as f64)
        })
        .collect();

    // Convert back to Python dict
    let result = PyDict::new(py);
    for (k, v) in means {
        result.set_item(k, v)?;
    }

    Ok(result.into())
}
```

### 4. Polars Integration

Polars is a fast DataFrame library with Arrow backend.

```toml
# Cargo.toml
[dependencies]
polars = { version = "0.36", features = ["lazy"] }
```

```rust
use polars::prelude::*;

#[pyfunction]
fn process_polars_df(py: Python, df: &PyAny) -> PyResult<PyObject> {
    // Get Arrow representation
    let arrow = df.call_method0("to_arrow")?;

    // Convert to Polars DataFrame (via Arrow)
    // Process with Polars...

    // Return result
    Ok(py.None())
}

#[pyfunction]
fn fast_filter(df: &PyAny, column: &str, threshold: f64) -> PyResult<PyObject> {
    // Efficient filtering using Polars
    Python::with_gil(|py| {
        let result = df.call_method1("filter", (
            df.call_method1("__getitem__", (column,))?
                .call_method1("__gt__", (threshold,))?,
        ))?;
        Ok(result.into())
    })
}
```

### 5. Apache Arrow Integration

Arrow provides a columnar memory format for efficient data interchange.

```toml
# Cargo.toml
[dependencies]
arrow = "50.0"
parquet = "50.0"
```

```rust
use arrow::array::{Float64Array, Int32Array};
use arrow::datatypes::{Schema, Field, DataType};
use arrow::record_batch::RecordBatch;

#[pyfunction]
fn create_arrow_batch(py: Python) -> PyResult<PyObject> {
    // Create Arrow arrays
    let ids = Int32Array::from(vec![1, 2, 3, 4, 5]);
    let values = Float64Array::from(vec![1.0, 2.0, 3.0, 4.0, 5.0]);

    // Create schema
    let schema = Schema::new(vec![
        Field::new("id", DataType::Int32, false),
        Field::new("value", DataType::Float64, false),
    ]);

    // Create record batch
    let batch = RecordBatch::try_new(
        std::sync::Arc::new(schema),
        vec![
            std::sync::Arc::new(ids),
            std::sync::Arc::new(values),
        ]
    ).unwrap();

    // Convert to PyArrow
    // (requires pyarrow integration)
    Ok(py.None())
}
```

### 6. Parquet File Handling

```rust
use parquet::file::reader::SerializedFileReader;
use parquet::file::writer::SerializedFileWriter;

#[pyfunction]
fn read_parquet(path: String) -> PyResult<()> {
    let file = std::fs::File::open(path)?;
    let reader = SerializedFileReader::new(file)?;

    let metadata = reader.metadata();
    println!("Rows: {}", metadata.file_metadata().num_rows());

    Ok(())
}

#[pyfunction]
fn write_parquet(path: String, data: Vec<f64>) -> PyResult<()> {
    // Write data to Parquet file
    // (requires full Arrow integration)
    Ok(())
}
```

### 7. Parallel Data Processing

```rust
use rayon::prelude::*;
use numpy::PyReadonlyArray1;

#[pyfunction]
fn parallel_transform(
    py: Python,
    array: PyReadonlyArray1<f64>,
    chunk_size: usize
) -> Py<PyArray1<f64>> {
    py.allow_threads(|| {
        let slice = array.as_slice().unwrap();

        let result: Vec<f64> = slice
            .par_chunks(chunk_size)
            .flat_map(|chunk| {
                chunk.iter().map(|&x| {
                    // Expensive computation
                    (x * x + x).sqrt()
                }).collect::<Vec<_>>()
            })
            .collect();

        Python::with_gil(|py| {
            PyArray1::from_vec(py, result).to_owned()
        })
    })
}

#[pyfunction]
fn parallel_reduce(py: Python, array: PyReadonlyArray1<f64>) -> f64 {
    py.allow_threads(|| {
        array.as_slice()
            .unwrap()
            .par_iter()
            .map(|&x| x * x)
            .sum()
    })
}
```

### 8. Zero-Copy Operations

```rust
#[pyfunction]
fn zero_copy_view<'py>(
    py: Python<'py>,
    array: &'py PyArray1<f64>
) -> &'py PyArray1<f64> {
    // Return view without copying
    array
}

#[pyfunction]
fn in_place_modify(array: &PyArray1<f64>, scalar: f64) {
    unsafe {
        let slice = array.as_slice_mut().unwrap();
        for x in slice {
            *x *= scalar;
        }
    }
}
```

### 9. Memory-Efficient Pipelines

```rust
use std::sync::Arc;

#[pyclass]
struct DataPipeline {
    data: Arc<Vec<f64>>,
}

#[pymethods]
impl DataPipeline {
    #[new]
    fn new(data: Vec<f64>) -> Self {
        DataPipeline {
            data: Arc::new(data),
        }
    }

    fn filter(&self, threshold: f64) -> Self {
        let filtered: Vec<f64> = self.data.iter()
            .filter(|&&x| x > threshold)
            .copied()
            .collect();

        DataPipeline {
            data: Arc::new(filtered),
        }
    }

    fn map(&self, py: Python, func: PyObject) -> PyResult<Self> {
        let mapped: Vec<f64> = self.data.iter()
            .map(|&x| {
                func.call1(py, (x,))
                    .and_then(|obj| obj.extract::<f64>(py))
                    .unwrap_or(x)
            })
            .collect();

        Ok(DataPipeline {
            data: Arc::new(mapped),
        })
    }

    fn to_numpy<'py>(&self, py: Python<'py>) -> &'py PyArray1<f64> {
        PyArray1::from_vec(py, (*self.data).clone())
    }
}
```

## Common Patterns

### Type Conversion

```rust
// NumPy to Rust
let rust_vec: Vec<f64> = numpy_array.as_slice().unwrap().to_vec();

// Rust to NumPy
let numpy_array = PyArray1::from_vec(py, rust_vec);

// Zero-copy (when possible)
let view = numpy_array.as_array();
```

### Error Handling

```rust
#[pyfunction]
fn safe_divide(a: PyReadonlyArray1<f64>, b: PyReadonlyArray1<f64>) -> PyResult<Py<PyArray1<f64>>> {
    if a.len() != b.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Arrays must have same length"
        ));
    }

    Python::with_gil(|py| {
        let result: Vec<f64> = a.as_slice().unwrap().iter()
            .zip(b.as_slice().unwrap().iter())
            .map(|(&x, &y)| {
                if y == 0.0 { f64::NAN } else { x / y }
            })
            .collect();

        Ok(PyArray1::from_vec(py, result).to_owned())
    })
}
```

## Anti-Patterns

### ❌ Incorrect: Copying Large Arrays

```rust
fn bad_process(array: PyReadonlyArray1<f64>) -> Vec<f64> {
    array.as_slice().unwrap().to_vec()  // Unnecessary copy
}
```

### ✅ Correct: Use Views

```rust
fn good_process(array: PyReadonlyArray1<f64>) -> f64 {
    array.as_slice().unwrap().iter().sum()  // No copy
}
```

### ❌ Incorrect: GIL-Held Computation

```rust
#[pyfunction]
fn slow(py: Python, array: PyReadonlyArray1<f64>) -> f64 {
    // Holds GIL during computation
    array.as_slice().unwrap().iter().sum()
}
```

### ✅ Correct: Release GIL

```rust
#[pyfunction]
fn fast(py: Python, array: PyReadonlyArray1<f64>) -> f64 {
    py.allow_threads(|| {
        array.as_slice().unwrap().iter().sum()
    })
}
```

## Resources

### Crates
- **numpy**: NumPy bindings for PyO3
- **ndarray**: N-dimensional arrays in Rust
- **polars**: Fast DataFrame library
- **arrow**: Apache Arrow implementation
- **parquet**: Parquet file format

### Documentation
- [rust-numpy Documentation](https://docs.rs/numpy/)
- [ndarray Documentation](https://docs.rs/ndarray/)
- [Polars Documentation](https://pola-rs.github.io/polars/)
- [Arrow Rust Documentation](https://docs.rs/arrow/)

### Related Skills
- [pyo3-performance-gil-parallel.md](pyo3-performance-gil-parallel.md)
- [pyo3-collections-iterators.md](pyo3-collections-iterators.md)

## Examples

See `resources/examples/` for:
1. NumPy array basics
2. Multi-dimensional operations
3. Pandas DataFrame integration
4. Polars DataFrame processing
5. Arrow format handling
6. Parquet file I/O
7. Parallel data pipelines
8. Zero-copy transformations
9. Memory-efficient processing
10. Production data science library

## Additional Resources

- **REFERENCE.md**: Comprehensive patterns and examples
- **Scripts**:
  - `numpy_bridge.py`: NumPy integration utilities
  - `dataframe_processor.py`: DataFrame processing toolkit
  - `arrow_converter.py`: Arrow format conversion tools
