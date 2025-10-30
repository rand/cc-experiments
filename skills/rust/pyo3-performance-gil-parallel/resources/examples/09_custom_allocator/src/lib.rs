use pyo3::prelude::*;
use rayon::prelude::*;
use std::alloc::{alloc, dealloc, Layout};

/// Pre-allocated buffer for reuse
#[pyclass]
pub struct BufferPool {
    size: usize,
    capacity: usize,
}

#[pymethods]
impl BufferPool {
    #[new]
    fn new(size: usize, capacity: usize) -> Self {
        BufferPool { size, capacity }
    }

    fn process_batch(&self, py: Python, data: Vec<Vec<f64>>) -> PyResult<Vec<Vec<f64>>> {
        py.allow_threads(|| {
            data.into_par_iter()
                .map(|mut vec| {
                    vec.iter_mut().for_each(|x| *x = *x * *x);
                    vec
                })
                .collect()
        })
    }
}

/// Memory-efficient sliding window
#[pyfunction]
fn sliding_window_sum(py: Python, data: Vec<f64>, window: usize) -> PyResult<Vec<f64>> {
    if window == 0 || window > data.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid window size",
        ));
    }

    let result = py.allow_threads(|| {
        let mut results = Vec::with_capacity(data.len() - window + 1);

        // First window
        let mut sum: f64 = data[0..window].iter().sum();
        results.push(sum);

        // Sliding window - O(n) instead of O(n*w)
        for i in window..data.len() {
            sum = sum - data[i - window] + data[i];
            results.push(sum);
        }

        results
    });

    Ok(result)
}

/// Parallel processing with pre-allocated output
#[pyfunction]
fn parallel_transform_preallocated(
    py: Python,
    data: Vec<f64>,
) -> PyResult<Vec<f64>> {
    py.allow_threads(|| {
        let mut output = vec![0.0; data.len()];

        data.par_iter()
            .zip(output.par_iter_mut())
            .for_each(|(input, output)| {
                *output = input.sqrt();
            });

        output
    })
}

/// Batch processing with arena allocation
#[pyfunction]
fn batch_process_arena(
    py: Python,
    batches: Vec<Vec<f64>>,
) -> PyResult<Vec<f64>> {
    py.allow_threads(|| {
        batches
            .into_par_iter()
            .flat_map(|batch| {
                batch.into_iter().map(|x| x * x).collect::<Vec<_>>()
            })
            .collect()
    })
}

/// Object pool pattern for expensive allocations
#[pyclass]
pub struct ObjectPool {
    object_size: usize,
}

#[pymethods]
impl ObjectPool {
    #[new]
    fn new(object_size: usize) -> Self {
        ObjectPool { object_size }
    }

    fn process_with_pooling(&self, py: Python, items: Vec<f64>) -> PyResult<Vec<f64>> {
        py.allow_threads(|| {
            items
                .par_iter()
                .map(|&x| {
                    // Simulate expensive computation
                    let mut temp = vec![0.0; self.object_size];
                    temp[0] = x;
                    temp.iter().sum::<f64>() + x * x
                })
                .collect()
        })
    }
}

#[pymodule]
fn custom_allocator(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<BufferPool>()?;
    m.add_class::<ObjectPool>()?;
    m.add_function(wrap_pyfunction!(sliding_window_sum, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_transform_preallocated, m)?)?;
    m.add_function(wrap_pyfunction!(batch_process_arena, m)?)?;
    Ok(())
}
