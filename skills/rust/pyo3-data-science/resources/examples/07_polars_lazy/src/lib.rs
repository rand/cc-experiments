use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Create lazy Polars DataFrame
#[pyfunction]
fn create_lazy_df(py: Python) -> PyResult<PyObject> {
    let pl = py.import("polars")?;

    let data = PyDict::new(py);
    data.set_item("x", vec![1, 2, 3, 4, 5])?;
    data.set_item("y", vec![10, 20, 30, 40, 50])?;

    let df = pl.call_method1("DataFrame", (data,))?;
    let lazy = df.call_method0("lazy")?;
    Ok(lazy.into())
}

/// Execute lazy query
#[pyfunction]
fn execute_lazy(lazy_df: &PyAny) -> PyResult<PyObject> {
    let result = lazy_df.call_method0("collect")?;
    Ok(result.into())
}

#[pymodule]
fn polars_lazy(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(create_lazy_df, m)?)?;
    m.add_function(wrap_pyfunction!(execute_lazy, m)?)?;
    Ok(())
}
