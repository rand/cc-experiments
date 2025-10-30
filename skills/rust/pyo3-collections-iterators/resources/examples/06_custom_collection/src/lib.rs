use pyo3::prelude::*;
use pyo3::exceptions::PyKeyError;
use std::collections::HashMap;

/// A custom collection combining list and dict features
#[pyclass]
struct HybridCollection {
    items: Vec<String>,
    index_map: HashMap<String, usize>,
}

#[pymethods]
impl HybridCollection {
    #[new]
    fn new() -> Self {
        HybridCollection {
            items: Vec::new(),
            index_map: HashMap::new(),
        }
    }

    /// Add item (list-like)
    fn add(&mut self, item: String) {
        if !self.index_map.contains_key(&item) {
            let index = self.items.len();
            self.items.push(item.clone());
            self.index_map.insert(item, index);
        }
    }

    /// Get by index (list-like)
    fn get_by_index(&self, index: usize) -> Option<String> {
        self.items.get(index).cloned()
    }

    /// Get index by value (dict-like)
    fn get_index(&self, item: &str) -> Option<usize> {
        self.index_map.get(item).copied()
    }

    /// Check contains (set-like)
    fn __contains__(&self, item: String) -> bool {
        self.index_map.contains_key(&item)
    }

    fn __len__(&self) -> usize {
        self.items.len()
    }

    fn __iter__(slf: PyRef<'_, Self>) -> HybridIterator {
        HybridIterator {
            items: slf.items.clone(),
            index: 0,
        }
    }

    fn __repr__(&self) -> String {
        format!("HybridCollection({:?})", self.items)
    }
}

#[pyclass]
struct HybridIterator {
    items: Vec<String>,
    index: usize,
}

#[pymethods]
impl HybridIterator {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<String> {
        if slf.index < slf.items.len() {
            let item = slf.items[slf.index].clone();
            slf.index += 1;
            Some(item)
        } else {
            None
        }
    }
}

/// A priority queue collection
#[pyclass]
struct PriorityQueue {
    items: Vec<(i32, String)>,  // (priority, value)
}

#[pymethods]
impl PriorityQueue {
    #[new]
    fn new() -> Self {
        PriorityQueue { items: Vec::new() }
    }

    /// Insert with priority
    fn push(&mut self, priority: i32, value: String) {
        self.items.push((priority, value));
        self.items.sort_by(|a, b| b.0.cmp(&a.0));  // Higher priority first
    }

    /// Pop highest priority
    fn pop(&mut self) -> Option<(i32, String)> {
        if !self.items.is_empty() {
            Some(self.items.remove(0))
        } else {
            None
        }
    }

    /// Peek at highest priority
    fn peek(&self) -> Option<(i32, String)> {
        self.items.first().cloned()
    }

    fn __len__(&self) -> usize {
        self.items.len()
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PriorityQueueIterator {
        PriorityQueueIterator {
            items: slf.items.clone(),
            index: 0,
        }
    }
}

#[pyclass]
struct PriorityQueueIterator {
    items: Vec<(i32, String)>,
    index: usize,
}

#[pymethods]
impl PriorityQueueIterator {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<(i32, String)> {
        if slf.index < slf.items.len() {
            let item = slf.items[slf.index].clone();
            slf.index += 1;
            Some(item)
        } else {
            None
        }
    }
}

/// A circular buffer
#[pyclass]
struct CircularBuffer {
    buffer: Vec<i32>,
    capacity: usize,
    head: usize,
    size: usize,
}

#[pymethods]
impl CircularBuffer {
    #[new]
    fn new(capacity: usize) -> Self {
        CircularBuffer {
            buffer: vec![0; capacity],
            capacity,
            head: 0,
            size: 0,
        }
    }

    fn push(&mut self, value: i32) {
        let index = (self.head + self.size) % self.capacity;
        if self.size < self.capacity {
            self.buffer[index] = value;
            self.size += 1;
        } else {
            self.buffer[self.head] = value;
            self.head = (self.head + 1) % self.capacity;
        }
    }

    fn __len__(&self) -> usize {
        self.size
    }

    fn __iter__(slf: PyRef<'_, Self>) -> CircularBufferIterator {
        let mut items = Vec::new();
        for i in 0..slf.size {
            let index = (slf.head + i) % slf.capacity;
            items.push(slf.buffer[index]);
        }
        CircularBufferIterator { items, index: 0 }
    }
}

#[pyclass]
struct CircularBufferIterator {
    items: Vec<i32>,
    index: usize,
}

#[pymethods]
impl CircularBufferIterator {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<i32> {
        if slf.index < slf.items.len() {
            let item = slf.items[slf.index];
            slf.index += 1;
            Some(item)
        } else {
            None
        }
    }
}

#[pymodule]
fn custom_collection(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<HybridCollection>()?;
    m.add_class::<HybridIterator>()?;
    m.add_class::<PriorityQueue>()?;
    m.add_class::<PriorityQueueIterator>()?;
    m.add_class::<CircularBuffer>()?;
    m.add_class::<CircularBufferIterator>()?;
    Ok(())
}
