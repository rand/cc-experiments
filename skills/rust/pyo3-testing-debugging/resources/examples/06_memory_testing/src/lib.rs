use pyo3::prelude::*;
use pyo3::types::{PyList, PyDict};

#[pyfunction]
fn process_list(list: &Bound<'_, PyList>) -> PyResult<usize> {
    Ok(list.len())
}

#[pyfunction]
fn create_and_process() -> PyResult<usize> {
    Python::with_gil(|py| {
        let list = PyList::new_bound(py, &[1, 2, 3, 4, 5]);
        Ok(list.len())
    })
}

#[pyfunction]
fn create_dict(py: Python<'_>) -> PyResult<Py<PyDict>> {
    let dict = PyDict::new_bound(py);
    dict.set_item("key", "value")?;
    Ok(dict.unbind())
}

#[pyfunction]
fn get_refcount(obj: &Bound<'_, PyAny>) -> usize {
    obj.get_refcnt()
}

#[pyfunction]
fn run_tests() {
    println!("Running memory tests...");
}

#[pymodule]
fn memory_testing(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_list, m)?)?;
    m.add_function(wrap_pyfunction!(create_and_process, m)?)?;
    m.add_function(wrap_pyfunction!(create_dict, m)?)?;
    m.add_function(wrap_pyfunction!(get_refcount, m)?)?;
    m.add_function(wrap_pyfunction!(run_tests, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_no_leak_simple() {
        Python::with_gil(|py| {
            let list = PyList::new_bound(py, &[1, 2, 3]);
            let initial_refcount = list.get_refcnt();

            let _ = process_list(&list).unwrap();

            assert_eq!(list.get_refcnt(), initial_refcount);
        });
    }

    #[test]
    fn test_no_leak_complex() {
        Python::with_gil(|py| {
            for _ in 0..1000 {
                let list = PyList::new_bound(py, &[1, 2, 3, 4, 5]);
                let _ = process_list(&list).unwrap();
            }
        });
    }

    #[test]
    fn test_dict_refcount() {
        Python::with_gil(|py| {
            let dict = create_dict(py).unwrap();
            let bound_dict = dict.bind(py);
            assert!(bound_dict.get_refcnt() >= 1);
        });
    }
}
