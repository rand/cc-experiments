//! Collection type conversions between Python and Rust
//!
//! This example demonstrates working with Python collections:
//! - Lists (Vec<T>)
//! - Dictionaries (HashMap<K, V>)
//! - Tuples ((T1, T2, ...))
//! - Sets (HashSet<T>)

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PySet, PyTuple};
use std::collections::{HashMap, HashSet};

/// Sum all elements in a list
#[pyfunction]
fn sum_list(numbers: Vec<i64>) -> PyResult<i64> {
    Ok(numbers.iter().sum())
}

/// Return a new list with each element doubled
#[pyfunction]
fn double_list(numbers: Vec<i64>) -> PyResult<Vec<i64>> {
    Ok(numbers.into_iter().map(|x| x * 2).collect())
}

/// Work with string lists
#[pyfunction]
fn join_strings(strings: Vec<String>, separator: &str) -> PyResult<String> {
    Ok(strings.join(separator))
}

/// Filter list based on predicate
#[pyfunction]
fn filter_positive(numbers: Vec<i64>) -> PyResult<Vec<i64>> {
    Ok(numbers.into_iter().filter(|&x| x > 0).collect())
}

/// Work with dictionaries
#[pyfunction]
fn sum_dict_values(data: HashMap<String, i64>) -> PyResult<i64> {
    Ok(data.values().sum())
}

/// Invert a dictionary (swap keys and values)
#[pyfunction]
fn invert_dict(data: HashMap<String, String>) -> PyResult<HashMap<String, String>> {
    Ok(data.into_iter().map(|(k, v)| (v, k)).collect())
}

/// Get value from dict with default
#[pyfunction]
fn get_with_default(data: HashMap<String, i64>, key: String, default: i64) -> PyResult<i64> {
    Ok(*data.get(&key).unwrap_or(&default))
}

/// Work with tuples - return multiple values
#[pyfunction]
fn min_max(numbers: Vec<i64>) -> PyResult<(i64, i64)> {
    if numbers.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "List cannot be empty",
        ));
    }
    let min = *numbers.iter().min().unwrap();
    let max = *numbers.iter().max().unwrap();
    Ok((min, max))
}

/// Accept tuple as input
#[pyfunction]
fn tuple_sum(pair: (i64, i64)) -> PyResult<i64> {
    Ok(pair.0 + pair.1)
}

/// Work with 3-tuples
#[pyfunction]
fn create_person(name: String, age: u32, score: f64) -> PyResult<(String, u32, f64)> {
    Ok((name, age, score))
}

/// Work with sets - find unique elements
#[pyfunction]
fn unique_elements(items: Vec<i64>) -> PyResult<HashSet<i64>> {
    Ok(items.into_iter().collect())
}

/// Set intersection
#[pyfunction]
fn set_intersection(set1: HashSet<i64>, set2: HashSet<i64>) -> PyResult<HashSet<i64>> {
    Ok(set1.intersection(&set2).copied().collect())
}

/// Set union
#[pyfunction]
fn set_union(set1: HashSet<String>, set2: HashSet<String>) -> PyResult<HashSet<String>> {
    Ok(set1.union(&set2).cloned().collect())
}

/// Set difference
#[pyfunction]
fn set_difference(set1: HashSet<i64>, set2: HashSet<i64>) -> PyResult<HashSet<i64>> {
    Ok(set1.difference(&set2).copied().collect())
}

/// Nested collections - list of tuples
#[pyfunction]
fn sum_tuples(pairs: Vec<(i64, i64)>) -> PyResult<Vec<i64>> {
    Ok(pairs.into_iter().map(|(a, b)| a + b).collect())
}

/// Nested collections - dict of lists
#[pyfunction]
fn flatten_dict_lists(data: HashMap<String, Vec<i64>>) -> PyResult<Vec<i64>> {
    Ok(data.into_values().flatten().collect())
}

/// Working with PyList directly for advanced operations
#[pyfunction]
fn reverse_in_place(py: Python, list: Vec<i64>) -> PyResult<Bound<PyList>> {
    let mut reversed = list;
    reversed.reverse();
    Ok(PyList::new_bound(py, reversed))
}

/// Working with PyDict directly
#[pyfunction]
fn merge_dicts(
    py: Python,
    dict1: HashMap<String, i64>,
    dict2: HashMap<String, i64>,
) -> PyResult<Bound<PyDict>> {
    let result = PyDict::new_bound(py);
    for (k, v) in dict1.iter().chain(dict2.iter()) {
        result.set_item(k, v)?;
    }
    Ok(result)
}

/// Convert list of dicts to dict of lists
#[pyfunction]
fn transpose_data(
    records: Vec<HashMap<String, i64>>,
) -> PyResult<HashMap<String, Vec<i64>>> {
    let mut result: HashMap<String, Vec<i64>> = HashMap::new();

    for record in records {
        for (key, value) in record {
            result.entry(key).or_insert_with(Vec::new).push(value);
        }
    }

    Ok(result)
}

/// Group items by key
#[pyfunction]
fn group_by_first_letter(words: Vec<String>) -> PyResult<HashMap<char, Vec<String>>> {
    let mut result: HashMap<char, Vec<String>> = HashMap::new();

    for word in words {
        if let Some(first_char) = word.chars().next() {
            result
                .entry(first_char.to_ascii_lowercase())
                .or_insert_with(Vec::new)
                .push(word);
        }
    }

    Ok(result)
}

/// Python module initialization
#[pymodule]
fn collections(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_list, m)?)?;
    m.add_function(wrap_pyfunction!(double_list, m)?)?;
    m.add_function(wrap_pyfunction!(join_strings, m)?)?;
    m.add_function(wrap_pyfunction!(filter_positive, m)?)?;
    m.add_function(wrap_pyfunction!(sum_dict_values, m)?)?;
    m.add_function(wrap_pyfunction!(invert_dict, m)?)?;
    m.add_function(wrap_pyfunction!(get_with_default, m)?)?;
    m.add_function(wrap_pyfunction!(min_max, m)?)?;
    m.add_function(wrap_pyfunction!(tuple_sum, m)?)?;
    m.add_function(wrap_pyfunction!(create_person, m)?)?;
    m.add_function(wrap_pyfunction!(unique_elements, m)?)?;
    m.add_function(wrap_pyfunction!(set_intersection, m)?)?;
    m.add_function(wrap_pyfunction!(set_union, m)?)?;
    m.add_function(wrap_pyfunction!(set_difference, m)?)?;
    m.add_function(wrap_pyfunction!(sum_tuples, m)?)?;
    m.add_function(wrap_pyfunction!(flatten_dict_lists, m)?)?;
    m.add_function(wrap_pyfunction!(reverse_in_place, m)?)?;
    m.add_function(wrap_pyfunction!(merge_dicts, m)?)?;
    m.add_function(wrap_pyfunction!(transpose_data, m)?)?;
    m.add_function(wrap_pyfunction!(group_by_first_letter, m)?)?;
    Ok(())
}
