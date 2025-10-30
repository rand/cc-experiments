use pyo3::prelude::*;

/// Map iterator - transforms values
#[pyclass]
struct MapIterator {
    data: Vec<i32>,
    index: usize,
    operation: MapOperation,
}

#[derive(Clone)]
enum MapOperation {
    Double,
    Square,
    Increment,
}

#[pymethods]
impl MapIterator {
    #[new]
    fn new(data: Vec<i32>, operation: String) -> Self {
        let op = match operation.as_str() {
            "square" => MapOperation::Square,
            "double" => MapOperation::Double,
            _ => MapOperation::Increment,
        };
        MapIterator {
            data,
            index: 0,
            operation: op,
        }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<i32> {
        if slf.index < slf.data.len() {
            let value = slf.data[slf.index];
            slf.index += 1;

            let result = match slf.operation {
                MapOperation::Double => value * 2,
                MapOperation::Square => value * value,
                MapOperation::Increment => value + 1,
            };
            Some(result)
        } else {
            None
        }
    }
}

/// Filter iterator
#[pyclass]
struct FilterIterator {
    data: Vec<i32>,
    index: usize,
    predicate: FilterPredicate,
}

#[derive(Clone)]
enum FilterPredicate {
    Even,
    Odd,
    Positive,
    GreaterThan(i32),
}

#[pymethods]
impl FilterIterator {
    #[new]
    fn new(data: Vec<i32>, predicate: String, threshold: Option<i32>) -> Self {
        let pred = match predicate.as_str() {
            "even" => FilterPredicate::Even,
            "odd" => FilterPredicate::Odd,
            "positive" => FilterPredicate::Positive,
            "gt" => FilterPredicate::GreaterThan(threshold.unwrap_or(0)),
            _ => FilterPredicate::Positive,
        };
        FilterIterator {
            data,
            index: 0,
            predicate: pred,
        }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<i32> {
        while slf.index < slf.data.len() {
            let value = slf.data[slf.index];
            slf.index += 1;

            let matches = match &slf.predicate {
                FilterPredicate::Even => value % 2 == 0,
                FilterPredicate::Odd => value % 2 != 0,
                FilterPredicate::Positive => value > 0,
                FilterPredicate::GreaterThan(t) => value > *t,
            };

            if matches {
                return Some(value);
            }
        }
        None
    }
}

/// Chain iterator - combines multiple iterators
#[pyclass]
struct ChainIterator {
    first: Vec<i32>,
    second: Vec<i32>,
    index: usize,
}

#[pymethods]
impl ChainIterator {
    #[new]
    fn new(first: Vec<i32>, second: Vec<i32>) -> Self {
        ChainIterator {
            first,
            second,
            index: 0,
        }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<i32> {
        if slf.index < slf.first.len() {
            let value = slf.first[slf.index];
            slf.index += 1;
            Some(value)
        } else if slf.index < slf.first.len() + slf.second.len() {
            let idx = slf.index - slf.first.len();
            let value = slf.second[idx];
            slf.index += 1;
            Some(value)
        } else {
            None
        }
    }
}

/// Zip iterator - combines two iterators
#[pyclass]
struct ZipIterator {
    first: Vec<i32>,
    second: Vec<String>,
    index: usize,
}

#[pymethods]
impl ZipIterator {
    #[new]
    fn new(first: Vec<i32>, second: Vec<String>) -> Self {
        ZipIterator {
            first,
            second,
            index: 0,
        }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<(i32, String)> {
        if slf.index < slf.first.len().min(slf.second.len()) {
            let pair = (slf.first[slf.index], slf.second[slf.index].clone());
            slf.index += 1;
            Some(pair)
        } else {
            None
        }
    }
}

/// Take iterator - limits number of items
#[pyclass]
struct TakeIterator {
    data: Vec<i32>,
    index: usize,
    limit: usize,
}

#[pymethods]
impl TakeIterator {
    #[new]
    fn new(data: Vec<i32>, limit: usize) -> Self {
        TakeIterator {
            data,
            index: 0,
            limit,
        }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<i32> {
        if slf.index < slf.limit && slf.index < slf.data.len() {
            let value = slf.data[slf.index];
            slf.index += 1;
            Some(value)
        } else {
            None
        }
    }
}

/// Skip iterator - skips first n items
#[pyclass]
struct SkipIterator {
    data: Vec<i32>,
    index: usize,
    skip_count: usize,
}

#[pymethods]
impl SkipIterator {
    #[new]
    fn new(data: Vec<i32>, skip_count: usize) -> Self {
        SkipIterator {
            data,
            index: skip_count,
            skip_count,
        }
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
}

#[pymodule]
fn iterator_combinators(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<MapIterator>()?;
    m.add_class::<FilterIterator>()?;
    m.add_class::<ChainIterator>()?;
    m.add_class::<ZipIterator>()?;
    m.add_class::<TakeIterator>()?;
    m.add_class::<SkipIterator>()?;
    Ok(())
}
