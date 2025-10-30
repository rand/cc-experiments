use pyo3::prelude::*;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread;
use std::time::Duration;

#[pyfunction]
fn compute_with_gil_release(py: Python<'_>, size: usize) -> usize {
    py.allow_threads(|| {
        // Heavy computation without GIL
        (0..size).map(|x| x * x).sum()
    })
}

#[pyfunction]
fn parallel_sum(py: Python<'_>, data: Vec<Vec<i32>>) -> Vec<i32> {
    py.allow_threads(|| {
        data.iter()
            .map(|chunk| chunk.iter().sum())
            .collect()
    })
}

#[pyfunction]
fn sleep_without_gil(py: Python<'_>, millis: u64) {
    py.allow_threads(|| {
        thread::sleep(Duration::from_millis(millis));
    });
}

#[pymodule]
fn gil_testing(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_with_gil_release, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_sum, m)?)?;
    m.add_function(wrap_pyfunction!(sleep_without_gil, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gil_released_during_computation() {
        Python::with_gil(|py| {
            let counter = Arc::new(AtomicUsize::new(0));
            let counter_clone = counter.clone();

            let handle = thread::spawn(move || {
                Python::with_gil(|_py| {
                    counter_clone.fetch_add(1, Ordering::SeqCst);
                });
            });

            py.allow_threads(|| {
                thread::sleep(Duration::from_millis(100));
            });

            handle.join().unwrap();
            assert_eq!(counter.load(Ordering::SeqCst), 1);
        });
    }

    #[test]
    fn test_parallel_execution() {
        Python::with_gil(|py| {
            let data = vec![vec![1, 2, 3], vec![4, 5, 6]];
            let result = parallel_sum(py, data);
            assert_eq!(result, vec![6, 15]);
        });
    }
}
