use pyo3::prelude::*;

/// Lazy iterator that generates Fibonacci numbers
#[pyclass]
struct Fibonacci {
    current: u64,
    next: u64,
    max_value: Option<u64>,
}

#[pymethods]
impl Fibonacci {
    #[new]
    fn new(max_value: Option<u64>) -> Self {
        Fibonacci {
            current: 0,
            next: 1,
            max_value,
        }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<u64> {
        if let Some(max) = slf.max_value {
            if slf.current > max {
                return None;
            }
        }

        let result = slf.current;
        let new_next = slf.current + slf.next;
        slf.current = slf.next;
        slf.next = new_next;
        Some(result)
    }
}

/// Lazy iterator that reads lines from a file-like stream
#[pyclass]
struct LazyFileReader {
    lines: Vec<String>,
    index: usize,
}

#[pymethods]
impl LazyFileReader {
    #[new]
    fn new(content: String) -> Self {
        LazyFileReader {
            lines: content.lines().map(String::from).collect(),
            index: 0,
        }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<String> {
        if slf.index < slf.lines.len() {
            let line = slf.lines[slf.index].clone();
            slf.index += 1;
            Some(line)
        } else {
            None
        }
    }

    /// Create a filtered iterator (lazy)
    fn filter_prefix(slf: PyRef<'_, Self>, prefix: String) -> FilteredIterator {
        FilteredIterator {
            lines: slf.lines.clone(),
            index: slf.index,
            prefix,
        }
    }
}

/// Filtered iterator (lazy evaluation)
#[pyclass]
struct FilteredIterator {
    lines: Vec<String>,
    index: usize,
    prefix: String,
}

#[pymethods]
impl FilteredIterator {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<String> {
        while slf.index < slf.lines.len() {
            let line = &slf.lines[slf.index];
            slf.index += 1;

            if line.starts_with(&slf.prefix) {
                return Some(line.clone());
            }
        }
        None
    }
}

/// Lazy range with transformation
#[pyclass]
struct LazyRange {
    start: i64,
    end: i64,
    step: i64,
    current: i64,
    transform: TransformType,
}

#[derive(Clone)]
enum TransformType {
    Identity,
    Square,
    Double,
}

#[pymethods]
impl LazyRange {
    #[new]
    fn new(start: i64, end: i64, step: Option<i64>, transform: Option<String>) -> Self {
        let transform = match transform.as_deref() {
            Some("square") => TransformType::Square,
            Some("double") => TransformType::Double,
            _ => TransformType::Identity,
        };

        LazyRange {
            start,
            end,
            step: step.unwrap_or(1),
            current: start,
            transform,
        }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<i64> {
        if (slf.step > 0 && slf.current >= slf.end)
            || (slf.step < 0 && slf.current <= slf.end)
        {
            return None;
        }

        let value = match slf.transform {
            TransformType::Identity => slf.current,
            TransformType::Square => slf.current * slf.current,
            TransformType::Double => slf.current * 2,
        };

        slf.current += slf.step;
        Some(value)
    }

    /// Chain this range with another (lazy)
    fn chain(slf: PyRef<'_, Self>, other: PyRef<'_, Self>) -> ChainedIterator {
        ChainedIterator {
            first: Some(Box::new(RangeSnapshot {
                current: slf.current,
                end: slf.end,
                step: slf.step,
                transform: slf.transform.clone(),
            })),
            second: Some(Box::new(RangeSnapshot {
                current: other.current,
                end: other.end,
                step: other.step,
                transform: other.transform.clone(),
            })),
        }
    }
}

/// Helper for chaining
struct RangeSnapshot {
    current: i64,
    end: i64,
    step: i64,
    transform: TransformType,
}

impl RangeSnapshot {
    fn next(&mut self) -> Option<i64> {
        if (self.step > 0 && self.current >= self.end)
            || (self.step < 0 && self.current <= self.end)
        {
            return None;
        }

        let value = match self.transform {
            TransformType::Identity => self.current,
            TransformType::Square => self.current * self.current,
            TransformType::Double => self.current * 2,
        };

        self.current += self.step;
        Some(value)
    }
}

/// Chained iterator (lazy)
#[pyclass]
struct ChainedIterator {
    first: Option<Box<RangeSnapshot>>,
    second: Option<Box<RangeSnapshot>>,
}

#[pymethods]
impl ChainedIterator {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<i64> {
        if let Some(ref mut first) = slf.first {
            if let Some(value) = first.next() {
                return Some(value);
            }
            slf.first = None;
        }

        if let Some(ref mut second) = slf.second {
            if let Some(value) = second.next() {
                return Some(value);
            }
            slf.second = None;
        }

        None
    }
}

#[pymodule]
fn lazy_iterator(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Fibonacci>()?;
    m.add_class::<LazyFileReader>()?;
    m.add_class::<FilteredIterator>()?;
    m.add_class::<LazyRange>()?;
    m.add_class::<ChainedIterator>()?;
    Ok(())
}
