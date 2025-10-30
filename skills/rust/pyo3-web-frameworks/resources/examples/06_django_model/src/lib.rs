//! Django model operations optimization

use pyo3::prelude::*;
use serde_json::Value;

#[pyfunction]
fn serialize_queryset(py: Python, queryset: &PyAny) -> PyResult<Vec<PyObject>> {
    let items: Vec<PyObject> = queryset.call_method0("all")?
        .iter()?
        .map(|item| item.unwrap().into())
        .collect();
    Ok(items)
}

#[pyfunction]
fn bulk_validate(data: Vec<String>) -> PyResult<Vec<bool>> {
    Ok(data.iter().map(|s| !s.is_empty() && s.len() < 100).collect())
}

#[pyfunction]
fn filter_fields(json_data: String, fields: Vec<String>) -> PyResult<String> {
    let value: Value = serde_json::from_str(&json_data)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

    if let Value::Object(map) = value {
        let filtered: serde_json::Map<String, Value> = map.into_iter()
            .filter(|(k, _)| fields.contains(k))
            .collect();
        serde_json::to_string(&filtered)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    } else {
        Ok(json_data)
    }
}

#[pymodule]
fn django_model(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(serialize_queryset, m)?)?;
    m.add_function(wrap_pyfunction!(bulk_validate, m)?)?;
    m.add_function(wrap_pyfunction!(filter_fields, m)?)?;
    Ok(())
}
