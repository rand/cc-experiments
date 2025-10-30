use pyo3::prelude::*;
use pyo3::types::PyDict;
use numpy::{PyArray1, PyReadonlyArray1};
use std::collections::HashMap;

/// Fast groupby-sum operation in Rust
///
/// Args:
///     groups: Group labels array
///     values: Values to sum by group
///
/// Returns:
///     Python dict mapping group -> sum
#[pyfunction]
fn fast_groupby_sum(
    py: Python,
    groups: PyReadonlyArray1<i32>,
    values: PyReadonlyArray1<f64>
) -> PyResult<PyObject> {
    let group_slice = groups.as_slice()?;
    let value_slice = values.as_slice()?;

    if group_slice.len() != value_slice.len() {
        return Err(pyo3::exceptions::PyValueError::new_err("Length mismatch"));
    }

    let mut group_sums: HashMap<i32, f64> = HashMap::new();

    for (&g, &v) in group_slice.iter().zip(value_slice.iter()) {
        *group_sums.entry(g).or_insert(0.0) += v;
    }

    let result = PyDict::new(py);
    for (k, v) in group_sums {
        result.set_item(k, v)?;
    }

    Ok(result.into())
}

/// Fast groupby-mean operation
#[pyfunction]
fn fast_groupby_mean(
    py: Python,
    groups: PyReadonlyArray1<i32>,
    values: PyReadonlyArray1<f64>
) -> PyResult<PyObject> {
    let group_slice = groups.as_slice()?;
    let value_slice = values.as_slice()?;

    if group_slice.len() != value_slice.len() {
        return Err(pyo3::exceptions::PyValueError::new_err("Length mismatch"));
    }

    let mut group_data: HashMap<i32, (f64, usize)> = HashMap::new();

    for (&g, &v) in group_slice.iter().zip(value_slice.iter()) {
        let entry = group_data.entry(g).or_insert((0.0, 0));
        entry.0 += v;
        entry.1 += 1;
    }

    let result = PyDict::new(py);
    for (k, (sum, count)) in group_data {
        result.set_item(k, sum / count as f64)?;
    }

    Ok(result.into())
}

/// Groupby with multiple aggregations
#[pyfunction]
fn fast_groupby_agg(
    py: Python,
    groups: PyReadonlyArray1<i32>,
    values: PyReadonlyArray1<f64>
) -> PyResult<PyObject> {
    let group_slice = groups.as_slice()?;
    let value_slice = values.as_slice()?;

    struct GroupStats {
        sum: f64,
        count: usize,
        min: f64,
        max: f64,
    }

    let mut stats: HashMap<i32, GroupStats> = HashMap::new();

    for (&g, &v) in group_slice.iter().zip(value_slice.iter()) {
        stats.entry(g).and_modify(|s| {
            s.sum += v;
            s.count += 1;
            s.min = s.min.min(v);
            s.max = s.max.max(v);
        }).or_insert(GroupStats {
            sum: v,
            count: 1,
            min: v,
            max: v,
        });
    }

    let result = PyDict::new(py);
    for (k, s) in stats {
        let group_result = PyDict::new(py);
        group_result.set_item("sum", s.sum)?;
        group_result.set_item("mean", s.sum / s.count as f64)?;
        group_result.set_item("count", s.count)?;
        group_result.set_item("min", s.min)?;
        group_result.set_item("max", s.max)?;
        result.set_item(k, group_result)?;
    }

    Ok(result.into())
}

/// Count occurrences in each group
#[pyfunction]
fn fast_value_counts(py: Python, groups: PyReadonlyArray1<i32>) -> PyResult<PyObject> {
    let slice = groups.as_slice()?;
    let mut counts: HashMap<i32, usize> = HashMap::new();

    for &g in slice {
        *counts.entry(g).or_insert(0) += 1;
    }

    let result = PyDict::new(py);
    for (k, v) in counts {
        result.set_item(k, v)?;
    }

    Ok(result.into())
}

/// Filter groups by size
#[pyfunction]
fn filter_groups_by_size<'py>(
    py: Python<'py>,
    groups: PyReadonlyArray1<i32>,
    min_size: usize
) -> PyResult<&'py PyArray1<bool>> {
    let slice = groups.as_slice()?;
    let mut counts: HashMap<i32, usize> = HashMap::new();

    for &g in slice {
        *counts.entry(g).or_insert(0) += 1;
    }

    let mask: Vec<bool> = slice.iter()
        .map(|&g| counts.get(&g).copied().unwrap_or(0) >= min_size)
        .collect();

    Ok(PyArray1::from_vec(py, mask))
}

/// Module initialization
#[pymodule]
fn pandas_groupby(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fast_groupby_sum, m)?)?;
    m.add_function(wrap_pyfunction!(fast_groupby_mean, m)?)?;
    m.add_function(wrap_pyfunction!(fast_groupby_agg, m)?)?;
    m.add_function(wrap_pyfunction!(fast_value_counts, m)?)?;
    m.add_function(wrap_pyfunction!(filter_groups_by_size, m)?)?;
    Ok(())
}
