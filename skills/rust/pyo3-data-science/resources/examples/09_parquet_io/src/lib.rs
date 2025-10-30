use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::path::Path;

/// Write DataFrame to Parquet file
///
/// Args:
///     df: Pandas or Polars DataFrame
///     path: Output file path
#[pyfunction]
fn write_parquet(df: &PyAny, path: &str) -> PyResult<()> {
    df.call_method1("write_parquet", (path,))?;
    Ok(())
}

/// Read Parquet file into DataFrame
///
/// Args:
///     path: Input file path
///     engine: Engine to use (pandas or polars)
///
/// Returns:
///     DataFrame
#[pyfunction]
fn read_parquet(py: Python, path: &str, engine: Option<&str>) -> PyResult<PyObject> {
    let engine = engine.unwrap_or("pandas");

    if engine == "polars" {
        let pl = py.import("polars")?;
        let df = pl.call_method1("read_parquet", (path,))?;
        Ok(df.into())
    } else {
        let pd = py.import("pandas")?;
        let df = pd.call_method1("read_parquet", (path,))?;
        Ok(df.into())
    }
}

/// Check if Parquet file exists
///
/// Args:
///     path: File path to check
///
/// Returns:
///     True if file exists
#[pyfunction]
fn parquet_exists(path: &str) -> bool {
    Path::new(path).exists()
}

/// Get Parquet file metadata
///
/// Args:
///     path: Parquet file path
///
/// Returns:
///     Dictionary with metadata
#[pyfunction]
fn get_parquet_metadata(py: Python, path: &str) -> PyResult<PyObject> {
    let pq = py.import("pyarrow.parquet")?;
    let parquet_file = pq.call_method1("ParquetFile", (path,))?;
    let metadata = parquet_file.getattr("metadata")?;

    let result = PyDict::new(py);
    result.set_item("num_rows", metadata.getattr("num_rows")?)?;
    result.set_item("num_row_groups", metadata.getattr("num_row_groups")?)?;

    Ok(result.into())
}

#[pymodule]
fn parquet_io(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(write_parquet, m)?)?;
    m.add_function(wrap_pyfunction!(read_parquet, m)?)?;
    m.add_function(wrap_pyfunction!(parquet_exists, m)?)?;
    m.add_function(wrap_pyfunction!(get_parquet_metadata, m)?)?;
    Ok(())
}
