use pyo3::prelude::*;
use pyo3::exceptions::{PyIndexError, PyTypeError};

/// A simple vector wrapper implementing the sequence protocol
#[pyclass]
struct IntVector {
    data: Vec<i32>,
}

#[pymethods]
impl IntVector {
    #[new]
    fn new(data: Option<Vec<i32>>) -> Self {
        IntVector {
            data: data.unwrap_or_default(),
        }
    }

    /// Required for len(vector)
    fn __len__(&self) -> usize {
        self.data.len()
    }

    /// Required for vector[index]
    fn __getitem__(&self, index: isize) -> PyResult<i32> {
        let idx = self.normalize_index(index)?;
        self.data
            .get(idx)
            .copied()
            .ok_or_else(|| PyIndexError::new_err("Index out of range"))
    }

    /// Required for vector[index] = value
    fn __setitem__(&mut self, index: isize, value: i32) -> PyResult<()> {
        let idx = self.normalize_index(index)?;
        if idx < self.data.len() {
            self.data[idx] = value;
            Ok(())
        } else {
            Err(PyIndexError::new_err("Index out of range"))
        }
    }

    /// Required for del vector[index]
    fn __delitem__(&mut self, index: isize) -> PyResult<()> {
        let idx = self.normalize_index(index)?;
        if idx < self.data.len() {
            self.data.remove(idx);
            Ok(())
        } else {
            Err(PyIndexError::new_err("Index out of range"))
        }
    }

    /// Required for iteration
    fn __iter__(slf: PyRef<'_, Self>) -> PyResult<Py<IntVectorIterator>> {
        let iter = IntVectorIterator {
            data: slf.data.clone(),
            index: 0,
        };
        Py::new(slf.py(), iter)
    }

    /// Required for reversed()
    fn __reversed__(slf: PyRef<'_, Self>) -> PyResult<Py<IntVectorIterator>> {
        let iter = IntVectorIterator {
            data: slf.data.iter().rev().copied().collect(),
            index: 0,
        };
        Py::new(slf.py(), iter)
    }

    /// Required for 'in' operator
    fn __contains__(&self, value: i32) -> bool {
        self.data.contains(&value)
    }

    /// Append a value
    fn append(&mut self, value: i32) {
        self.data.push(value);
    }

    /// Get a string representation
    fn __repr__(&self) -> String {
        format!("IntVector({:?})", self.data)
    }
}

impl IntVector {
    fn normalize_index(&self, index: isize) -> PyResult<usize> {
        let len = self.data.len() as isize;
        let idx = if index < 0 { len + index } else { index };

        if idx < 0 || idx >= len {
            Err(PyIndexError::new_err("Index out of range"))
        } else {
            Ok(idx as usize)
        }
    }
}

/// Iterator for IntVector
#[pyclass]
struct IntVectorIterator {
    data: Vec<i32>,
    index: usize,
}

#[pymethods]
impl IntVectorIterator {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<i32> {
        if slf.index < slf.data.len() {
            let value = slf.data[slf.index];
            slf.index += 1;
            Some(value)
        } else {
            None
        }
    }
}

/// A string collection with slice support
#[pyclass]
struct StringList {
    items: Vec<String>,
}

#[pymethods]
impl StringList {
    #[new]
    fn new(items: Option<Vec<String>>) -> Self {
        StringList {
            items: items.unwrap_or_default(),
        }
    }

    fn __len__(&self) -> usize {
        self.items.len()
    }

    fn __getitem__(&self, py: Python, index: &PyAny) -> PyResult<PyObject> {
        // Handle both integer index and slice
        if let Ok(idx) = index.extract::<isize>() {
            // Single item access
            let pos = self.normalize_index(idx)?;
            Ok(self.items[pos].to_object(py))
        } else if let Ok(slice) = index.extract::<pyo3::types::PySlice>() {
            // Slice access
            let indices = slice.indices(self.items.len() as i64)?;
            let start = indices.start as usize;
            let stop = indices.stop as usize;
            let step = indices.step as isize;

            let result: Vec<String> = if step == 1 {
                self.items[start..stop].to_vec()
            } else {
                let mut sliced = Vec::new();
                let mut i = start as isize;
                while (step > 0 && i < stop as isize) || (step < 0 && i > stop as isize) {
                    sliced.push(self.items[i as usize].clone());
                    i += step;
                }
                sliced
            };

            Ok(result.to_object(py))
        } else {
            Err(PyTypeError::new_err("indices must be integers or slices"))
        }
    }

    fn __contains__(&self, value: String) -> bool {
        self.items.contains(&value)
    }

    fn __repr__(&self) -> String {
        format!("StringList({:?})", self.items)
    }

    fn append(&mut self, value: String) {
        self.items.push(value);
    }

    fn extend(&mut self, values: Vec<String>) {
        self.items.extend(values);
    }
}

impl StringList {
    fn normalize_index(&self, index: isize) -> PyResult<usize> {
        let len = self.items.len() as isize;
        let idx = if index < 0 { len + index } else { index };

        if idx < 0 || idx >= len {
            Err(PyIndexError::new_err("Index out of range"))
        } else {
            Ok(idx as usize)
        }
    }
}

/// Module initialization
#[pymodule]
fn sequence_protocol(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<IntVector>()?;
    m.add_class::<IntVectorIterator>()?;
    m.add_class::<StringList>()?;
    Ok(())
}
