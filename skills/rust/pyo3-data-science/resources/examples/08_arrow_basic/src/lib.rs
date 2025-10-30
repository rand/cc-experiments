use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

/// Create PyArrow Table using Python API
#[pyfunction]
fn create_arrow_table(py: Python) -> PyResult<PyObject> {
    let pa = py.import("pyarrow")?;

    let data = PyDict::new(py);
    data.set_item("id", vec![1, 2, 3, 4, 5])?;
    data.set_item("value", vec![10.5, 20.3, 15.7, 30.2, 25.1])?;

    let table = pa.call_method1("table", (data,))?;
    Ok(table.into())
}

/// Get Arrow table schema
#[pyfunction]
fn get_schema(table: &PyAny) -> PyResult<String> {
    let schema = table.getattr("schema")?;
    let schema_str = schema.call_method0("__str__")?;
    schema_str.extract()
}

/// Get number of rows
#[pyfunction]
fn num_rows(table: &PyAny) -> PyResult<usize> {
    table.call_method0("num_rows")?.extract()
}

#[pymodule]
fn arrow_basic(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(create_arrow_table, m)?)?;
    m.add_function(wrap_pyfunction!(get_schema, m)?)?;
    m.add_function(wrap_pyfunction!(num_rows, m)?)?;
    Ok(())
}
