use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use numpy::PyArray1;

/// Create a Polars DataFrame using Python API
///
/// Returns:
///     Polars DataFrame
#[pyfunction]
fn create_polars_df(py: Python) -> PyResult<PyObject> {
    let pl = py.import("polars")?;

    let data = PyDict::new(py);
    data.set_item("id", vec![1, 2, 3, 4, 5])?;
    data.set_item("value", vec![10.5, 20.3, 15.7, 30.2, 25.1])?;
    data.set_item("category", vec!["A", "B", "A", "C", "B"])?;

    let df = pl.call_method1("DataFrame", (data,))?;
    Ok(df.into())
}

/// Filter Polars DataFrame
///
/// Args:
///     df: Polars DataFrame
///     column: Column name to filter on
///     threshold: Minimum value
///
/// Returns:
///     Filtered DataFrame
#[pyfunction]
fn filter_dataframe(df: &PyAny, column: &str, threshold: f64) -> PyResult<PyObject> {
    let filtered = df.call_method1(
        "filter",
        (df.call_method1("__getitem__", (column,))?
            .call_method1("__gt__", (threshold,))?,)
    )?;
    Ok(filtered.into())
}

/// Select columns from DataFrame
///
/// Args:
///     df: Polars DataFrame
///     columns: List of column names
///
/// Returns:
///     DataFrame with selected columns
#[pyfunction]
fn select_columns(py: Python, df: &PyAny, columns: Vec<&str>) -> PyResult<PyObject> {
    let col_list = PyList::new(py, &columns);
    let selected = df.call_method1("select", (col_list,))?;
    Ok(selected.into())
}

/// Sort DataFrame by column
///
/// Args:
///     df: Polars DataFrame
///     column: Column to sort by
///     descending: Sort in descending order
///
/// Returns:
///     Sorted DataFrame
#[pyfunction]
fn sort_dataframe(df: &PyAny, column: &str, descending: bool) -> PyResult<PyObject> {
    let sorted = df.call_method(
        "sort",
        (column,),
        Some(&[("descending", descending)].into_py_dict(df.py()))
    )?;
    Ok(sorted.into())
}

/// Get DataFrame shape
///
/// Args:
///     df: Polars DataFrame
///
/// Returns:
///     Tuple of (rows, columns)
#[pyfunction]
fn get_shape(df: &PyAny) -> PyResult<(usize, usize)> {
    let shape = df.getattr("shape")?;
    shape.extract()
}

/// Module initialization
#[pymodule]
fn polars_basic(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(create_polars_df, m)?)?;
    m.add_function(wrap_pyfunction!(filter_dataframe, m)?)?;
    m.add_function(wrap_pyfunction!(select_columns, m)?)?;
    m.add_function(wrap_pyfunction!(sort_dataframe, m)?)?;
    m.add_function(wrap_pyfunction!(get_shape, m)?)?;
    Ok(())
}
