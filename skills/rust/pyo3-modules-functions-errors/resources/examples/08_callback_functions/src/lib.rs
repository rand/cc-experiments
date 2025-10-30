//! Example 08: Callback Functions
//!
//! This example demonstrates:
//! - Calling Python functions from Rust
//! - Passing callbacks as arguments
//! - Error handling with callbacks
//! - Performance considerations

use pyo3::prelude::*;
use pyo3::types::PyTuple;

/// Applies a Python callback to each element.
///
/// Args:
///     items: List of items to process
///     callback: Function to apply to each item
///
/// Returns:
///     List of transformed items
#[pyfunction]
fn map_with_callback(py: Python, items: Vec<i64>, callback: PyObject) -> PyResult<Vec<i64>> {
    let mut results = Vec::new();
    
    for item in items {
        // Call Python function with item
        let args = PyTuple::new(py, &[item]);
        let result = callback.call1(py, args)?;
        let value: i64 = result.extract(py)?;
        results.push(value);
    }
    
    Ok(results)
}

/// Filters items using a Python predicate.
///
/// Args:
///     items: List of items to filter
///     predicate: Function that returns True/False
///
/// Returns:
///     Filtered list
#[pyfunction]
fn filter_with_callback(py: Python, items: Vec<i64>, predicate: PyObject) -> PyResult<Vec<i64>> {
    let mut results = Vec::new();
    
    for item in items {
        let args = PyTuple::new(py, &[item]);
        let keep: bool = predicate.call1(py, args)?.extract(py)?;
        if keep {
            results.push(item);
        }
    }
    
    Ok(results)
}

/// Reduces items using a Python reducer function.
///
/// Args:
///     items: List to reduce
///     reducer: Function(accumulator, item) -> new_accumulator
///     initial: Initial accumulator value
///
/// Returns:
///     Final reduced value
#[pyfunction]
fn reduce_with_callback(
    py: Python,
    items: Vec<i64>,
    reducer: PyObject,
    initial: i64,
) -> PyResult<i64> {
    let mut accumulator = initial;
    
    for item in items {
        let args = PyTuple::new(py, &[accumulator, item]);
        accumulator = reducer.call1(py, args)?.extract(py)?;
    }
    
    Ok(accumulator)
}

/// Processes data with error handling callback.
///
/// Args:
///     items: Items to process
///     processor: Function that may raise exceptions
///     error_handler: Callback for handling errors
///
/// Returns:
///     List of successfully processed items
#[pyfunction]
fn process_with_error_callback(
    py: Python,
    items: Vec<i64>,
    processor: PyObject,
    error_handler: PyObject,
) -> PyResult<Vec<i64>> {
    let mut results = Vec::new();
    
    for item in items {
        let args = PyTuple::new(py, &[item]);
        match processor.call1(py, args) {
            Ok(result) => {
                let value: i64 = result.extract(py)?;
                results.push(value);
            }
            Err(err) => {
                // Call error handler with item and error
                let err_args = PyTuple::new(py, &[item]);
                error_handler.call1(py, err_args)?;
                // Continue processing
            }
        }
    }
    
    Ok(results)
}

/// Sorts using a custom comparison callback.
///
/// Args:
///     items: List to sort
///     key_func: Function to extract sort key from item
///
/// Returns:
///     Sorted list
#[pyfunction]
fn sort_with_callback(py: Python, mut items: Vec<i64>, key_func: PyObject) -> PyResult<Vec<i64>> {
    // Extract sort keys
    let mut items_with_keys: Vec<(i64, i64)> = Vec::new();
    
    for item in &items {
        let args = PyTuple::new(py, &[*item]);
        let key: i64 = key_func.call1(py, args)?.extract(py)?;
        items_with_keys.push((*item, key));
    }
    
    // Sort by keys
    items_with_keys.sort_by_key(|(_, key)| *key);
    
    // Extract sorted items
    Ok(items_with_keys.into_iter().map(|(item, _)| item).collect())
}

/// Chains multiple transformation callbacks.
///
/// Args:
///     value: Initial value
///     callbacks: List of transformation functions
///
/// Returns:
///     Final transformed value
#[pyfunction]
fn chain_callbacks(py: Python, mut value: i64, callbacks: Vec<PyObject>) -> PyResult<i64> {
    for callback in callbacks {
        let args = PyTuple::new(py, &[value]);
        value = callback.call1(py, args)?.extract(py)?;
    }
    
    Ok(value)
}

#[pymodule]
fn callback_functions(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(map_with_callback, m)?)?;
    m.add_function(wrap_pyfunction!(filter_with_callback, m)?)?;
    m.add_function(wrap_pyfunction!(reduce_with_callback, m)?)?;
    m.add_function(wrap_pyfunction!(process_with_error_callback, m)?)?;
    m.add_function(wrap_pyfunction!(sort_with_callback, m)?)?;
    m.add_function(wrap_pyfunction!(chain_callbacks, m)?)?;
    
    Ok(())
}
