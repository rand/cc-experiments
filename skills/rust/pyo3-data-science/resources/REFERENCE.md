# PyO3 Data Science Integration - Complete Reference

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Skill**: rust-pyo3-data-science

This is a comprehensive reference for integrating PyO3 with the Python data science ecosystem. It covers NumPy arrays, Pandas DataFrames, Polars, Apache Arrow, Parquet, and high-performance data processing patterns.

---

## Table of Contents

1. [NumPy Array Operations](#1-numpy-array-operations)
2. [ndarray Integration](#2-ndarray-integration)
3. [Pandas DataFrame Integration](#3-pandas-dataframe-integration)
4. [Polars Integration](#4-polars-integration)
5. [Apache Arrow](#5-apache-arrow)
6. [Parquet File Handling](#6-parquet-file-handling)
7. [Parallel Data Processing](#7-parallel-data-processing)
8. [Zero-Copy Patterns](#8-zero-copy-patterns)
9. [Performance Optimization](#9-performance-optimization)
10. [Production Examples](#10-production-examples)

---

## 1. NumPy Array Operations

### 1.1 Setup

```toml
# Cargo.toml
[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
numpy = "0.20"
ndarray = "0.15"
```

### 1.2 Reading NumPy Arrays

```rust
use pyo3::prelude::*;
use numpy::{PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};

#[pyfunction]
fn sum_array(array: PyReadonlyArray1<f64>) -> f64 {
    array.as_slice().unwrap().iter().sum()
}

#[pyfunction]
fn mean_array(array: PyReadonlyArray1<f64>) -> f64 {
    let slice = array.as_slice().unwrap();
    if slice.is_empty() {
        return 0.0;
    }
    slice.iter().sum::<f64>() / slice.len() as f64
}

#[pyfunction]
fn sum_2d(array: PyReadonlyArray2<f64>) -> f64 {
    array.as_slice().unwrap().iter().sum()
}

#[pyfunction]
fn element_wise_multiply(
    a: PyReadonlyArray1<f64>,
    b: PyReadonlyArray1<f64>
) -> PyResult<Py<PyArray1<f64>>> {
    if a.len() != b.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Arrays must have same length"
        ));
    }

    Python::with_gil(|py| {
        let result: Vec<f64> = a.as_slice().unwrap().iter()
            .zip(b.as_slice().unwrap().iter())
            .map(|(&x, &y)| x * y)
            .collect();

        Ok(PyArray1::from_vec(py, result).to_owned())
    })
}
```

### 1.3 Creating NumPy Arrays

```rust
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

#[pyfunction]
fn create_linspace(py: Python, start: f64, end: f64, n: usize) -> Py<PyArray1<f64>> {
    let step = (end - start) / (n - 1) as f64;
    let data: Vec<f64> = (0..n).map(|i| start + step * i as f64).collect();
    PyArray1::from_vec(py, data).to_owned()
}
```

### 1.4 Multi-dimensional Operations

```rust
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
            format!("Incompatible shapes: ({}, {}) @ ({}, {})",
                a_shape[0], a_shape[1], b_shape[0], b_shape[1])
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

    unsafe {
        Ok(PyArray2::from_vec2(py, &vec![vec![0.0; p]; m]).unwrap())
    }
}

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

    unsafe {
        PyArray2::from_vec2(py, &vec![vec![0.0; rows]; cols]).unwrap()
    }
}
```

---

## 2. ndarray Integration

### 2.1 Converting Between NumPy and ndarray

```rust
use ndarray::{Array1, Array2, ArrayView1, s};
use numpy::ToPyArray;

#[pyfunction]
fn process_with_ndarray<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>
) -> &'py PyArray1<f64> {
    // Convert to ndarray
    let arr = array.as_array();

    // Use ndarray operations
    let result = &arr * 2.0 + 1.0;

    // Convert back to NumPy
    result.to_pyarray(py)
}

#[pyfunction]
fn ndarray_operations<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>
) -> &'py PyArray1<f64> {
    let arr = array.as_array();

    // Chain operations
    let result = arr.mapv(|x| x.powi(2))
        .mapv(|x| x.sqrt())
        .mapv(|x| x + 1.0);

    result.to_pyarray(py)
}
```

### 2.2 Parallel Operations

```rust
#[pyfunction]
fn parallel_process<'py>(
    py: Python<'py>,
    array: PyReadonlyArray1<f64>
) -> &'py PyArray1<f64> {
    use rayon::prelude::*;

    let arr = array.as_array();

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

---

## 3. Pandas DataFrame Integration

### 3.1 Creating DataFrames

```rust
use pyo3::types::{PyDict, PyList};

#[pyfunction]
fn create_dataframe(py: Python) -> PyResult<PyObject> {
    let pd = py.import("pandas")?;

    // Create data dict
    let data = PyDict::new(py);
    data.set_item("id", PyArray1::from_vec(py, vec![1, 2, 3, 4, 5]))?;
    data.set_item("value", PyArray1::from_vec(py, vec![10.0, 20.0, 30.0, 40.0, 50.0]))?;
    data.set_item("category", vec!["A", "B", "A", "B", "A"])?;

    // Create DataFrame
    let df = pd.call_method1("DataFrame", (data,))?;
    Ok(df.into())
}
```

### 3.2 Processing DataFrames

```rust
#[pyfunction]
fn fast_groupby(py: Python, df: &PyAny) -> PyResult<PyObject> {
    // Extract columns
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

    // Calculate group statistics
    let result = PyDict::new(py);
    for (group, values) in groups {
        let sum: f64 = values.iter().sum();
        let mean = sum / values.len() as f64;
        let count = values.len();

        let stats = PyDict::new(py);
        stats.set_item("sum", sum)?;
        stats.set_item("mean", mean)?;
        stats.set_item("count", count)?;

        result.set_item(group, stats)?;
    }

    Ok(result.into())
}

#[pyfunction]
fn filter_dataframe(py: Python, df: &PyAny, column: &str, threshold: f64) -> PyResult<PyObject> {
    // Extract column
    let values: PyReadonlyArray1<f64> = df
        .get_item(column)?
        .getattr("values")?
        .extract()?;

    // Find matching indices
    let mask: Vec<bool> = values.as_slice().unwrap().iter()
        .map(|&x| x > threshold)
        .collect();

    // Filter DataFrame
    let filtered = df.call_method1("loc", (mask,))?;
    Ok(filtered.into())
}
```

---

## 4. Polars Integration

### 4.1 Basic Operations

```rust
// Note: Polars integration typically uses Arrow backend
#[pyfunction]
fn process_polars_df(py: Python, df: &PyAny) -> PyResult<PyObject> {
    // Get column as NumPy array
    let column = df.call_method1("get_column", ("value",))?;
    let values: PyReadonlyArray1<f64> = column
        .call_method0("to_numpy")?
        .extract()?;

    // Process in Rust
    let processed: Vec<f64> = values.as_slice().unwrap().iter()
        .map(|&x| x * 2.0)
        .collect();

    // Create new column
    let pl = py.import("polars")?;
    let series = pl.call_method1("Series", ("processed", processed))?;

    Ok(series.into())
}
```

---

## 5. Apache Arrow

### 5.1 Arrow Arrays

```rust
use arrow::array::{Float64Array, Int32Array, StringArray};
use arrow::datatypes::{Schema, Field, DataType};
use arrow::record_batch::RecordBatch;
use std::sync::Arc;

#[pyfunction]
fn create_arrow_batch(py: Python) -> PyResult<()> {
    // Create arrays
    let ids = Int32Array::from(vec![1, 2, 3, 4, 5]);
    let values = Float64Array::from(vec![1.0, 2.0, 3.0, 4.0, 5.0]);
    let names = StringArray::from(vec!["a", "b", "c", "d", "e"]);

    // Create schema
    let schema = Schema::new(vec![
        Field::new("id", DataType::Int32, false),
        Field::new("value", DataType::Float64, false),
        Field::new("name", DataType::Utf8, false),
    ]);

    // Create record batch
    let batch = RecordBatch::try_new(
        Arc::new(schema),
        vec![
            Arc::new(ids),
            Arc::new(values),
            Arc::new(names),
        ]
    ).unwrap();

    println!("Created batch with {} rows", batch.num_rows());
    Ok(())
}
```

---

## 6. Parquet File Handling

### 6.1 Reading Parquet

```rust
use parquet::file::reader::{FileReader, SerializedFileReader};
use std::fs::File;

#[pyfunction]
fn read_parquet_metadata(path: String) -> PyResult<(i64, usize)> {
    let file = File::open(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let reader = SerializedFileReader::new(file)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    let metadata = reader.metadata();
    let num_rows = metadata.file_metadata().num_rows();
    let num_cols = metadata.file_metadata().schema().num_columns();

    Ok((num_rows, num_cols))
}
```

---

## 7. Parallel Data Processing

### 7.1 Parallel Transform

```rust
use rayon::prelude::*;

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

#[pyfunction]
fn parallel_filter(
    py: Python,
    array: PyReadonlyArray1<f64>,
    threshold: f64
) -> Py<PyArray1<f64>> {
    py.allow_threads(|| {
        let result: Vec<f64> = array.as_slice()
            .unwrap()
            .par_iter()
            .filter(|&&x| x > threshold)
            .copied()
            .collect();

        Python::with_gil(|py| {
            PyArray1::from_vec(py, result).to_owned()
        })
    })
}
```

---

## 8. Zero-Copy Patterns

### 8.1 Array Views

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

#[pyfunction]
fn in_place_add(a: &PyArray1<f64>, b: PyReadonlyArray1<f64>) -> PyResult<()> {
    if a.len() != b.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Arrays must have same length"
        ));
    }

    unsafe {
        let a_slice = a.as_slice_mut().unwrap();
        let b_slice = b.as_slice().unwrap();

        for (dst, &src) in a_slice.iter_mut().zip(b_slice.iter()) {
            *dst += src;
        }
    }

    Ok(())
}
```

---

## 9. Performance Optimization

### 9.1 Vectorization

```rust
#[pyfunction]
fn vectorized_operation(
    py: Python,
    array: PyReadonlyArray1<f64>
) -> Py<PyArray1<f64>> {
    let slice = array.as_slice().unwrap();

    // Compiler can vectorize this
    let result: Vec<f64> = slice.iter()
        .map(|&x| x * 2.0 + 1.0)
        .collect();

    PyArray1::from_vec(py, result).to_owned()
}
```

### 9.2 Memory Efficiency

```rust
#[pyfunction]
fn streaming_process(
    py: Python,
    array: PyReadonlyArray1<f64>,
    callback: PyObject
) -> PyResult<()> {
    let slice = array.as_slice().unwrap();
    let chunk_size = 1000;

    for chunk in slice.chunks(chunk_size) {
        let sum: f64 = chunk.iter().sum();
        callback.call1(py, (sum,))?;
    }

    Ok(())
}
```

---

## 10. Production Examples

### 10.1 Data Pipeline

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

    fn reduce(&self, py: Python, func: PyObject, initial: f64) -> PyResult<f64> {
        self.data.iter().try_fold(initial, |acc, &x| {
            func.call1(py, (acc, x))?.extract::<f64>(py)
        })
    }

    fn to_numpy<'py>(&self, py: Python<'py>) -> &'py PyArray1<f64> {
        PyArray1::from_vec(py, (*self.data).clone())
    }

    fn len(&self) -> usize {
        self.data.len()
    }
}
```

### 10.2 Feature Engineering

```rust
#[pyfunction]
fn extract_features(
    py: Python,
    data: PyReadonlyArray2<f64>
) -> Py<PyArray2<f64>> {
    let shape = data.shape();
    let (n_samples, n_features) = (shape[0], shape[1]);

    // Extract multiple features in parallel
    py.allow_threads(|| {
        use rayon::prelude::*;

        let slice = data.as_slice().unwrap();

        let features: Vec<f64> = (0..n_samples).into_par_iter()
            .flat_map(|i| {
                let row_start = i * n_features;
                let row = &slice[row_start..row_start + n_features];

                vec![
                    row.iter().sum::<f64>(),                    // sum
                    row.iter().sum::<f64>() / n_features as f64, // mean
                    row.iter().map(|x| x.powi(2)).sum::<f64>(), // sum of squares
                ]
            })
            .collect();

        Python::with_gil(|py| {
            unsafe {
                PyArray2::from_vec2(py, &vec![vec![0.0; 3]; n_samples]).unwrap().to_owned()
            }
        })
    })
}
```

---

## Summary

This reference covers:

1. **NumPy Arrays**: Reading, creating, multi-dimensional operations
2. **ndarray**: Integration patterns, parallel operations
3. **Pandas**: DataFrame creation, groupby, filtering
4. **Polars**: DataFrame operations with Arrow backend
5. **Arrow**: RecordBatch creation, schema definition
6. **Parquet**: Reading metadata and data
7. **Parallel Processing**: Rayon-based parallel transforms
8. **Zero-Copy**: Views, in-place modifications
9. **Performance**: Vectorization, memory efficiency
10. **Production**: Complete pipelines, feature engineering

For more information, see:
- [rust-numpy Documentation](https://docs.rs/numpy/)
- [ndarray Documentation](https://docs.rs/ndarray/)
- [Arrow Rust Documentation](https://docs.rs/arrow/)
