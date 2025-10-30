use pyo3::prelude::*;
use std::collections::VecDeque;

/// A bidirectional iterator over a deque
#[pyclass]
struct BiDirectionalDeque {
    data: VecDeque<i32>,
}

#[pymethods]
impl BiDirectionalDeque {
    #[new]
    fn new(items: Vec<i32>) -> Self {
        BiDirectionalDeque {
            data: VecDeque::from(items),
        }
    }

    /// Pop from front
    fn pop_front(&mut self) -> Option<i32> {
        self.data.pop_front()
    }

    /// Pop from back
    fn pop_back(&mut self) -> Option<i32> {
        self.data.pop_back()
    }

    /// Push to front
    fn push_front(&mut self, value: i32) {
        self.data.push_front(value);
    }

    /// Push to back
    fn push_back(&mut self, value: i32) {
        self.data.push_back(value);
    }

    fn __len__(&self) -> usize {
        self.data.len()
    }

    /// Forward iterator
    fn __iter__(slf: PyRef<'_, Self>) -> DequeForwardIterator {
        DequeForwardIterator {
            data: slf.data.clone(),
            index: 0,
        }
    }

    /// Reverse iterator
    fn __reversed__(slf: PyRef<'_, Self>) -> DequeReverseIterator {
        DequeReverseIterator {
            data: slf.data.clone(),
        }
    }

    fn __repr__(&self) -> String {
        format!("BiDirectionalDeque({:?})", self.data)
    }
}

#[pyclass]
struct DequeForwardIterator {
    data: VecDeque<i32>,
    index: usize,
}

#[pymethods]
impl DequeForwardIterator {
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

#[pyclass]
struct DequeReverseIterator {
    data: VecDeque<i32>,
}

#[pymethods]
impl DequeReverseIterator {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<i32> {
        slf.data.pop_back()
    }
}

/// Peekable iterator that can look ahead
#[pyclass]
struct PeekableIterator {
    data: Vec<i32>,
    index: usize,
}

#[pymethods]
impl PeekableIterator {
    #[new]
    fn new(data: Vec<i32>) -> Self {
        PeekableIterator { data, index: 0 }
    }

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

    /// Peek at next value without consuming
    fn peek(&self) -> Option<i32> {
        if self.index < self.data.len() {
            Some(self.data[self.index])
        } else {
            None
        }
    }

    /// Peek ahead n positions
    fn peek_n(&self, n: usize) -> Option<i32> {
        let target = self.index + n;
        if target < self.data.len() {
            Some(self.data[target])
        } else {
            None
        }
    }
}

/// Window iterator that yields sliding windows
#[pyclass]
struct WindowIterator {
    data: Vec<i32>,
    window_size: usize,
    index: usize,
}

#[pymethods]
impl WindowIterator {
    #[new]
    fn new(data: Vec<i32>, window_size: usize) -> Self {
        WindowIterator {
            data,
            window_size,
            index: 0,
        }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<Vec<i32>> {
        if slf.index + slf.window_size <= slf.data.len() {
            let window = slf.data[slf.index..slf.index + slf.window_size].to_vec();
            slf.index += 1;
            Some(window)
        } else {
            None
        }
    }
}

#[pymodule]
fn bidirectional_iter(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<BiDirectionalDeque>()?;
    m.add_class::<DequeForwardIterator>()?;
    m.add_class::<DequeReverseIterator>()?;
    m.add_class::<PeekableIterator>()?;
    m.add_class::<WindowIterator>()?;
    Ok(())
}
