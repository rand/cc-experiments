use pyo3::prelude::*;
use pyo3::types::PyDict;
use numpy::{PyArray1, PyReadonlyArray1};

/// Complete data pipeline: CSV → Process → Parquet
///
/// Args:
///     csv_path: Input CSV file path
///     output_path: Output Parquet file path
///     multiplier: Value to multiply by
///
/// Returns:
///     Number of rows processed
#[pyfunction]
fn process_pipeline(
    py: Python,
    csv_path: &str,
    output_path: &str,
    multiplier: f64
) -> PyResult<usize> {
    let pd = py.import("pandas")?;

    // Read CSV
    let df = pd.call_method1("read_csv", (csv_path,))?;

    // Process: multiply numeric column by factor
    if df.call_method1("__contains__", ("value",))?.extract::<bool>()? {
        let values = df.call_method1("__getitem__", ("value",))?;
        let transformed = values.call_method1("__mul__", (multiplier,))?;
        df.call_method1("__setitem__", ("value_transformed", transformed))?;
    }

    // Write Parquet
    df.call_method1("to_parquet", (output_path,))?;

    // Return row count
    let shape = df.getattr("shape")?;
    let rows: usize = shape.get_item(0)?.extract()?;
    Ok(rows)
}

/// Validate data pipeline inputs
///
/// Args:
///     csv_path: CSV file path
///
/// Returns:
///     True if valid, raises error otherwise
#[pyfunction]
fn validate_pipeline_input(py: Python, csv_path: &str) -> PyResult<bool> {
    use std::path::Path;

    if !Path::new(csv_path).exists() {
        return Err(pyo3::exceptions::PyFileNotFoundError::new_err(
            format!("File not found: {}", csv_path)
        ));
    }

    // Try to read CSV
    let pd = py.import("pandas")?;
    let df = pd.call_method1("read_csv", (csv_path,))?;

    // Check if 'value' column exists
    if !df.call_method1("__contains__", ("value",))?.extract::<bool>()? {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "CSV must contain 'value' column"
        ));
    }

    Ok(true)
}

/// Batch process multiple CSV files
///
/// Args:
///     input_files: List of input CSV paths
///     output_dir: Output directory for Parquet files
///     multiplier: Processing multiplier
///
/// Returns:
///     Total rows processed
#[pyfunction]
fn batch_process(
    py: Python,
    input_files: Vec<&str>,
    output_dir: &str,
    multiplier: f64
) -> PyResult<usize> {
    use std::path::Path;

    let mut total_rows = 0;

    for (i, input_file) in input_files.iter().enumerate() {
        let output_file = format!("{}/processed_{}.parquet", output_dir, i);
        let rows = process_pipeline(py, input_file, &output_file, multiplier)?;
        total_rows += rows;
    }

    Ok(total_rows)
}

/// Data quality check
///
/// Args:
///     values: Array of values to check
///     min_val: Minimum allowed value
///     max_val: Maximum allowed value
///
/// Returns:
///     Tuple of (num_valid, num_invalid)
#[pyfunction]
fn quality_check(
    values: PyReadonlyArray1<f64>,
    min_val: f64,
    max_val: f64
) -> PyResult<(usize, usize)> {
    let slice = values.as_slice()?;

    let valid = slice.iter().filter(|&&x| x >= min_val && x <= max_val).count();
    let invalid = slice.len() - valid;

    Ok((valid, invalid))
}

#[pymodule]
fn production_pipeline(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_pipeline, m)?)?;
    m.add_function(wrap_pyfunction!(validate_pipeline_input, m)?)?;
    m.add_function(wrap_pyfunction!(batch_process, m)?)?;
    m.add_function(wrap_pyfunction!(quality_check, m)?)?;
    Ok(())
}
