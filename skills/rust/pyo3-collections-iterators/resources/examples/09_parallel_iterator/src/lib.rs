use pyo3::prelude::*;
use rayon::prelude::*;

/// Parallel map operation
#[pyclass]
struct ParallelMapper;

#[pymethods]
impl ParallelMapper {
    #[new]
    fn new() -> Self {
        ParallelMapper
    }

    /// Map with parallel processing
    fn map_square(&self, data: Vec<i32>) -> Vec<i32> {
        data.par_iter().map(|x| x * x).collect()
    }

    fn map_double(&self, data: Vec<i32>) -> Vec<i32> {
        data.par_iter().map(|x| x * 2).collect()
    }

    /// Complex computation in parallel
    fn expensive_computation(&self, data: Vec<i32>) -> Vec<i32> {
        data.par_iter()
            .map(|x| {
                // Simulate expensive computation
                let mut result = *x;
                for _ in 0..1000 {
                    result = (result * 17 + 13) % 1000000;
                }
                result
            })
            .collect()
    }
}

/// Parallel filter operation
#[pyclass]
struct ParallelFilter;

#[pymethods]
impl ParallelFilter {
    #[new]
    fn new() -> Self {
        ParallelFilter
    }

    fn filter_even(&self, data: Vec<i32>) -> Vec<i32> {
        data.par_iter()
            .filter(|x| *x % 2 == 0)
            .copied()
            .collect()
    }

    fn filter_prime(&self, data: Vec<i32>) -> Vec<i32> {
        data.par_iter()
            .filter(|&&n| {
                if n < 2 {
                    return false;
                }
                for i in 2..=((n as f64).sqrt() as i32) {
                    if n % i == 0 {
                        return false;
                    }
                }
                true
            })
            .copied()
            .collect()
    }
}

/// Parallel reduction operations
#[pyclass]
struct ParallelReducer;

#[pymethods]
impl ParallelReducer {
    #[new]
    fn new() -> Self {
        ParallelReducer
    }

    fn sum(&self, data: Vec<i32>) -> i32 {
        data.par_iter().sum()
    }

    fn product(&self, data: Vec<i32>) -> i64 {
        data.par_iter().map(|x| *x as i64).product()
    }

    fn min(&self, data: Vec<i32>) -> Option<i32> {
        data.par_iter().min().copied()
    }

    fn max(&self, data: Vec<i32>) -> Option<i32> {
        data.par_iter().max().copied()
    }

    fn count_if(&self, data: Vec<i32>, threshold: i32) -> usize {
        data.par_iter().filter(|&&x| x > threshold).count()
    }
}

/// Parallel sorting
#[pyclass]
struct ParallelSorter;

#[pymethods]
impl ParallelSorter {
    #[new]
    fn new() -> Self {
        ParallelSorter
    }

    fn sort(&self, mut data: Vec<i32>) -> Vec<i32> {
        data.par_sort_unstable();
        data
    }

    fn sort_descending(&self, mut data: Vec<i32>) -> Vec<i32> {
        data.par_sort_unstable_by(|a, b| b.cmp(a));
        data
    }
}

/// Parallel batch processor
#[pyclass]
struct ParallelBatchProcessor {
    batch_size: usize,
}

#[pymethods]
impl ParallelBatchProcessor {
    #[new]
    fn new(batch_size: usize) -> Self {
        ParallelBatchProcessor { batch_size }
    }

    /// Process in parallel batches
    fn process_batches(&self, data: Vec<i32>) -> Vec<i32> {
        data.par_chunks(self.batch_size)
            .flat_map(|chunk| {
                chunk
                    .iter()
                    .map(|x| x * 2)
                    .collect::<Vec<i32>>()
            })
            .collect()
    }

    /// Sum each batch in parallel
    fn sum_batches(&self, data: Vec<i32>) -> Vec<i32> {
        data.par_chunks(self.batch_size)
            .map(|chunk| chunk.iter().sum())
            .collect()
    }
}

#[pymodule]
fn parallel_iterator(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<ParallelMapper>()?;
    m.add_class::<ParallelFilter>()?;
    m.add_class::<ParallelReducer>()?;
    m.add_class::<ParallelSorter>()?;
    m.add_class::<ParallelBatchProcessor>()?;
    Ok(())
}
