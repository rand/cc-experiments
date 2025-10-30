use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PySet, PyTuple};
use std::collections::{HashMap, HashSet};

/// Converts between Rust Vec and Python list
#[pyclass]
struct ListConverter;

#[pymethods]
impl ListConverter {
    #[new]
    fn new() -> Self {
        ListConverter
    }

    /// Convert Python list to Rust Vec and back
    fn roundtrip(&self, py_list: Vec<i32>) -> Vec<i32> {
        py_list
    }

    /// Process a list: filter evens, double them
    fn process_list(&self, items: Vec<i32>) -> Vec<i32> {
        items
            .into_iter()
            .filter(|x| x % 2 == 0)
            .map(|x| x * 2)
            .collect()
    }

    /// Create nested lists
    fn create_nested(&self) -> Vec<Vec<String>> {
        vec![
            vec!["a".to_string(), "b".to_string()],
            vec!["c".to_string(), "d".to_string()],
            vec!["e".to_string()],
        ]
    }
}

/// Converts between Rust HashMap and Python dict
#[pyclass]
struct DictConverter;

#[pymethods]
impl DictConverter {
    #[new]
    fn new() -> Self {
        DictConverter
    }

    /// Convert Python dict to Rust HashMap and back
    fn roundtrip(&self, py_dict: HashMap<String, i32>) -> HashMap<String, i32> {
        py_dict
    }

    /// Invert a dictionary (values become keys, keys become values)
    fn invert(&self, dict: HashMap<String, i32>) -> HashMap<i32, String> {
        dict.into_iter().map(|(k, v)| (v, k)).collect()
    }

    /// Merge two dictionaries, summing values for duplicate keys
    fn merge_sum(&self, dict1: HashMap<String, i32>, dict2: HashMap<String, i32>) -> HashMap<String, i32> {
        let mut result = dict1;
        for (key, value) in dict2 {
            *result.entry(key).or_insert(0) += value;
        }
        result
    }

    /// Filter dictionary by predicate
    fn filter_values(&self, dict: HashMap<String, i32>, threshold: i32) -> HashMap<String, i32> {
        dict.into_iter()
            .filter(|(_, v)| *v > threshold)
            .collect()
    }
}

/// Converts between Rust HashSet and Python set
#[pyclass]
struct SetConverter;

#[pymethods]
impl SetConverter {
    #[new]
    fn new() -> Self {
        SetConverter
    }

    /// Convert Python set to Rust HashSet and back
    fn roundtrip(&self, py_set: HashSet<String>) -> HashSet<String> {
        py_set
    }

    /// Union of two sets
    fn union(&self, set1: HashSet<i32>, set2: HashSet<i32>) -> HashSet<i32> {
        set1.union(&set2).copied().collect()
    }

    /// Intersection of two sets
    fn intersection(&self, set1: HashSet<i32>, set2: HashSet<i32>) -> HashSet<i32> {
        set1.intersection(&set2).copied().collect()
    }

    /// Difference of two sets (set1 - set2)
    fn difference(&self, set1: HashSet<i32>, set2: HashSet<i32>) -> HashSet<i32> {
        set1.difference(&set2).copied().collect()
    }

    /// Remove duplicates from list and return as sorted list
    fn deduplicate(&self, items: Vec<i32>) -> Vec<i32> {
        let set: HashSet<_> = items.into_iter().collect();
        let mut result: Vec<_> = set.into_iter().collect();
        result.sort();
        result
    }
}

/// Demonstrates tuple conversions
#[pyfunction]
fn tuple_operations(py: Python, data: Vec<(String, i32, f64)>) -> PyResult<PyObject> {
    // Process tuples: filter by threshold, transform
    let processed: Vec<_> = data
        .into_iter()
        .filter(|(_, count, _)| *count > 5)
        .map(|(name, count, value)| (name.to_uppercase(), count * 2, value * 1.5))
        .collect();

    // Convert to Python tuple of tuples
    let py_list = PyList::empty(py);
    for (name, count, value) in processed {
        let py_tuple = PyTuple::new(py, &[
            name.to_object(py),
            count.to_object(py),
            value.to_object(py),
        ]);
        py_list.append(py_tuple)?;
    }

    Ok(py_list.into())
}

/// Mixed collection operations
#[pyfunction]
fn mixed_collections(py: Python) -> PyResult<PyObject> {
    // Create a complex nested structure
    let result = PyDict::new(py);

    // Add a list
    let numbers = PyList::new(py, &[1, 2, 3, 4, 5]);
    result.set_item("numbers", numbers)?;

    // Add a set
    let tags = PySet::new(py, &["rust", "python", "pyo3"])?;
    result.set_item("tags", tags)?;

    // Add a nested dict
    let metadata = PyDict::new(py);
    metadata.set_item("version", "1.0")?;
    metadata.set_item("author", "PyO3")?;
    result.set_item("metadata", metadata)?;

    Ok(result.into())
}

/// Module initialization
#[pymodule]
fn collection_conversion(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<ListConverter>()?;
    m.add_class::<DictConverter>()?;
    m.add_class::<SetConverter>()?;
    m.add_function(wrap_pyfunction!(tuple_operations, m)?)?;
    m.add_function(wrap_pyfunction!(mixed_collections, m)?)?;
    Ok(())
}
