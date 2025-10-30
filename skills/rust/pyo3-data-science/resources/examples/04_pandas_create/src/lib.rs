use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use numpy::PyArray1;

/// Create a simple Pandas DataFrame from Rust data
///
/// Returns:
///     Pandas DataFrame with columns: id, value, name
#[pyfunction]
fn create_simple_dataframe(py: Python) -> PyResult<PyObject> {
    let pd = py.import("pandas")?;

    // Create data dictionary
    let data = PyDict::new(py);
    data.set_item("id", PyArray1::from_vec(py, vec![1, 2, 3, 4, 5]))?;
    data.set_item("value", PyArray1::from_vec(py, vec![10.5, 20.3, 15.7, 30.2, 25.1]))?;
    data.set_item("name", vec!["Alice", "Bob", "Charlie", "David", "Eve"])?;

    let df = pd.call_method1("DataFrame", (data,))?;
    Ok(df.into())
}

/// Create DataFrame from separate vectors
///
/// Args:
///     ids: Vector of integer IDs
///     values: Vector of float values
///     names: Vector of string names
///
/// Returns:
///     Pandas DataFrame
#[pyfunction]
fn create_from_vecs(
    py: Python,
    ids: Vec<i32>,
    values: Vec<f64>,
    names: Vec<String>
) -> PyResult<PyObject> {
    if ids.len() != values.len() || ids.len() != names.len() {
        return Err(pyo3::exceptions::PyValueError::new_err("All vectors must have same length"));
    }

    let pd = py.import("pandas")?;

    let data = PyDict::new(py);
    data.set_item("id", PyArray1::from_vec(py, ids))?;
    data.set_item("value", PyArray1::from_vec(py, values))?;
    data.set_item("name", names)?;

    let df = pd.call_method1("DataFrame", (data,))?;
    Ok(df.into())
}

/// Create DataFrame with date range
///
/// Args:
///     start_date: Starting date (YYYY-MM-DD)
///     periods: Number of periods
///
/// Returns:
///     DataFrame with date and random values
#[pyfunction]
fn create_time_series(py: Python, start_date: &str, periods: usize) -> PyResult<PyObject> {
    let pd = py.import("pandas")?;

    // Create date range
    let dates = pd.call_method(
        "date_range",
        (start_date, periods),
        None
    )?;

    // Create random-ish values (deterministic for testing)
    let values: Vec<f64> = (0..periods)
        .map(|i| 100.0 + (i as f64 * 1.5))
        .collect();

    let data = PyDict::new(py);
    data.set_item("date", dates)?;
    data.set_item("value", PyArray1::from_vec(py, values))?;

    let df = pd.call_method1("DataFrame", (data,))?;
    Ok(df.into())
}

/// Create DataFrame from nested structure
///
/// Args:
///     records: Number of records to create
///
/// Returns:
///     DataFrame with multiple columns
#[pyfunction]
fn create_complex_dataframe(py: Python, records: usize) -> PyResult<PyObject> {
    let pd = py.import("pandas")?;

    let ids: Vec<i32> = (1..=records as i32).collect();
    let categories: Vec<&str> = (0..records).map(|i| {
        match i % 3 {
            0 => "A",
            1 => "B",
            _ => "C",
        }
    }).collect();

    let values: Vec<f64> = (0..records)
        .map(|i| (i as f64 * 10.0) + (i as f64).sin() * 5.0)
        .collect();

    let flags: Vec<bool> = (0..records).map(|i| i % 2 == 0).collect();

    let data = PyDict::new(py);
    data.set_item("id", PyArray1::from_vec(py, ids))?;
    data.set_item("category", categories)?;
    data.set_item("value", PyArray1::from_vec(py, values))?;
    data.set_item("is_even", flags)?;

    let df = pd.call_method1("DataFrame", (data,))?;
    Ok(df.into())
}

/// Create DataFrame and immediately process it
///
/// Args:
///     size: Number of rows
///     multiplier: Value multiplier
///
/// Returns:
///     Processed DataFrame
#[pyfunction]
fn create_and_transform(py: Python, size: usize, multiplier: f64) -> PyResult<PyObject> {
    let pd = py.import("pandas")?;

    let values: Vec<f64> = (0..size).map(|i| i as f64).collect();
    let transformed: Vec<f64> = values.iter().map(|&v| v * multiplier).collect();

    let data = PyDict::new(py);
    data.set_item("original", PyArray1::from_vec(py, values))?;
    data.set_item("transformed", PyArray1::from_vec(py, transformed))?;

    let df = pd.call_method1("DataFrame", (data,))?;
    Ok(df.into())
}

/// Extract column from DataFrame as Vec
///
/// Args:
///     df: Pandas DataFrame
///     column: Column name
///
/// Returns:
///     Python list of values
#[pyfunction]
fn extract_column(py: Python, df: &PyAny, column: &str) -> PyResult<PyObject> {
    let col = df.get_item(column)?;
    let values = col.call_method0("tolist")?;
    Ok(values.into())
}

/// Get DataFrame shape
///
/// Args:
///     df: Pandas DataFrame
///
/// Returns:
///     Tuple of (rows, columns)
#[pyfunction]
fn get_shape(df: &PyAny) -> PyResult<(usize, usize)> {
    let shape = df.getattr("shape")?;
    let tuple: (usize, usize) = shape.extract()?;
    Ok(tuple)
}

/// Create DataFrame from Rust struct-like data
#[pyclass]
#[derive(Clone)]
struct Record {
    #[pyo3(get, set)]
    id: i32,
    #[pyo3(get, set)]
    name: String,
    #[pyo3(get, set)]
    score: f64,
}

#[pymethods]
impl Record {
    #[new]
    fn new(id: i32, name: String, score: f64) -> Self {
        Record { id, name, score }
    }
}

/// Convert list of records to DataFrame
///
/// Args:
///     records: List of Record objects
///
/// Returns:
///     Pandas DataFrame
#[pyfunction]
fn records_to_dataframe(py: Python, records: Vec<Py<Record>>) -> PyResult<PyObject> {
    let pd = py.import("pandas")?;

    let mut ids = Vec::new();
    let mut names = Vec::new();
    let mut scores = Vec::new();

    for record in records {
        let r = record.borrow(py);
        ids.push(r.id);
        names.push(r.name.clone());
        scores.push(r.score);
    }

    let data = PyDict::new(py);
    data.set_item("id", PyArray1::from_vec(py, ids))?;
    data.set_item("name", names)?;
    data.set_item("score", PyArray1::from_vec(py, scores))?;

    let df = pd.call_method1("DataFrame", (data,))?;
    Ok(df.into())
}

/// Module initialization
#[pymodule]
fn pandas_create(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(create_simple_dataframe, m)?)?;
    m.add_function(wrap_pyfunction!(create_from_vecs, m)?)?;
    m.add_function(wrap_pyfunction!(create_time_series, m)?)?;
    m.add_function(wrap_pyfunction!(create_complex_dataframe, m)?)?;
    m.add_function(wrap_pyfunction!(create_and_transform, m)?)?;
    m.add_function(wrap_pyfunction!(extract_column, m)?)?;
    m.add_function(wrap_pyfunction!(get_shape, m)?)?;
    m.add_function(wrap_pyfunction!(records_to_dataframe, m)?)?;
    m.add_class::<Record>()?;
    Ok(())
}
