use pyo3::prelude::*;
use pyo3::types::PyIterator;

/// A simple iterator that generates a range of numbers
#[pyclass]
struct NumberRange {
    current: i64,
    end: i64,
    step: i64,
}

#[pymethods]
impl NumberRange {
    #[new]
    fn new(start: i64, end: i64, step: Option<i64>) -> Self {
        NumberRange {
            current: start,
            end,
            step: step.unwrap_or(1),
        }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<i64> {
        if (slf.step > 0 && slf.current >= slf.end)
            || (slf.step < 0 && slf.current <= slf.end)
        {
            None
        } else {
            let result = slf.current;
            slf.current += slf.step;
            Some(result)
        }
    }
}

/// A simple counter that can be iterated
#[pyclass]
struct Counter {
    count: usize,
}

#[pymethods]
impl Counter {
    #[new]
    fn new() -> Self {
        Counter { count: 0 }
    }

    fn increment(&mut self) {
        self.count += 1;
    }

    fn get_count(&self) -> usize {
        self.count
    }

    /// Returns an iterator over the count values
    fn iter(&self) -> CounterIterator {
        CounterIterator {
            current: 0,
            max: self.count,
        }
    }
}

/// Iterator for Counter
#[pyclass]
struct CounterIterator {
    current: usize,
    max: usize,
}

#[pymethods]
impl CounterIterator {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<usize> {
        if slf.current < slf.max {
            let result = slf.current;
            slf.current += 1;
            Some(result)
        } else {
            None
        }
    }
}

/// Demonstrates consuming a Python iterator from Rust
#[pyfunction]
fn sum_iterator(py: Python, iterator: &PyAny) -> PyResult<i64> {
    let mut sum = 0i64;

    for item in iterator.iter()? {
        let value: i64 = item?.extract()?;
        sum += value;
    }

    Ok(sum)
}

/// Demonstrates creating a Python iterator from a Rust Vec
#[pyfunction]
fn create_iterator(py: Python, items: Vec<i64>) -> PyResult<PyObject> {
    let iter = items.into_iter();
    let py_iter = pyo3::types::PyIterator::from_object(
        py,
        &pyo3::types::PyList::new(py, iter).into()
    )?;
    Ok(py_iter.into())
}

/// Module initialization
#[pymodule]
fn basic_iterator(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<NumberRange>()?;
    m.add_class::<Counter>()?;
    m.add_class::<CounterIterator>()?;
    m.add_function(wrap_pyfunction!(sum_iterator, m)?)?;
    m.add_function(wrap_pyfunction!(create_iterator, m)?)?;
    Ok(())
}
