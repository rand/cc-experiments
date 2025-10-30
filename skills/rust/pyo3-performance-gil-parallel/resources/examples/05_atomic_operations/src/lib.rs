use pyo3::prelude::*;
use std::sync::atomic::{AtomicBool, AtomicI64, AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;

/// Thread-safe atomic counter
#[pyclass]
pub struct AtomicCounter {
    value: Arc<AtomicU64>,
}

#[pymethods]
impl AtomicCounter {
    #[new]
    fn new(initial: u64) -> Self {
        AtomicCounter {
            value: Arc::new(AtomicU64::new(initial)),
        }
    }

    fn increment(&self) -> u64 {
        self.value.fetch_add(1, Ordering::SeqCst)
    }

    fn add(&self, delta: u64) -> u64 {
        self.value.fetch_add(delta, Ordering::SeqCst)
    }

    fn get(&self) -> u64 {
        self.value.load(Ordering::SeqCst)
    }

    fn set(&self, value: u64) {
        self.value.store(value, Ordering::SeqCst);
    }

    fn compare_and_swap(&self, current: u64, new: u64) -> Result<u64, u64> {
        self.value
            .compare_exchange(current, new, Ordering::SeqCst, Ordering::SeqCst)
    }

    fn parallel_increment(&self, py: Python, threads: usize, increments: usize) -> PyResult<u64> {
        py.allow_threads(|| {
            let handles: Vec<_> = (0..threads)
                .map(|_| {
                    let counter = Arc::clone(&self.value);
                    thread::spawn(move || {
                        for _ in 0..increments {
                            counter.fetch_add(1, Ordering::SeqCst);
                        }
                    })
                })
                .collect();

            for handle in handles {
                handle.join().unwrap();
            }
        });

        Ok(self.get())
    }
}

/// Atomic flag for signaling
#[pyclass]
pub struct AtomicFlag {
    flag: Arc<AtomicBool>,
}

#[pymethods]
impl AtomicFlag {
    #[new]
    fn new(initial: bool) -> Self {
        AtomicFlag {
            flag: Arc::new(AtomicBool::new(initial)),
        }
    }

    fn set(&self, value: bool) {
        self.flag.store(value, Ordering::SeqCst);
    }

    fn get(&self) -> bool {
        self.flag.load(Ordering::SeqCst)
    }

    fn swap(&self, value: bool) -> bool {
        self.flag.swap(value, Ordering::SeqCst)
    }

    fn compare_and_swap(&self, current: bool, new: bool) -> Result<bool, bool> {
        self.flag
            .compare_exchange(current, new, Ordering::SeqCst, Ordering::SeqCst)
    }
}

/// Lock-free statistics collector
#[pyclass]
pub struct AtomicStats {
    count: Arc<AtomicUsize>,
    sum: Arc<AtomicI64>,
    min: Arc<AtomicI64>,
    max: Arc<AtomicI64>,
}

#[pymethods]
impl AtomicStats {
    #[new]
    fn new() -> Self {
        AtomicStats {
            count: Arc::new(AtomicUsize::new(0)),
            sum: Arc::new(AtomicI64::new(0)),
            min: Arc::new(AtomicI64::new(i64::MAX)),
            max: Arc::new(AtomicI64::new(i64::MIN)),
        }
    }

    fn record(&self, value: i64) {
        self.count.fetch_add(1, Ordering::SeqCst);
        self.sum.fetch_add(value, Ordering::SeqCst);

        // Update min
        let mut current_min = self.min.load(Ordering::SeqCst);
        while value < current_min {
            match self.min.compare_exchange_weak(
                current_min,
                value,
                Ordering::SeqCst,
                Ordering::SeqCst,
            ) {
                Ok(_) => break,
                Err(x) => current_min = x,
            }
        }

        // Update max
        let mut current_max = self.max.load(Ordering::SeqCst);
        while value > current_max {
            match self.max.compare_exchange_weak(
                current_max,
                value,
                Ordering::SeqCst,
                Ordering::SeqCst,
            ) {
                Ok(_) => break,
                Err(x) => current_max = x,
            }
        }
    }

    fn count(&self) -> usize {
        self.count.load(Ordering::SeqCst)
    }

    fn sum(&self) -> i64 {
        self.sum.load(Ordering::SeqCst)
    }

    fn mean(&self) -> Option<f64> {
        let count = self.count();
        if count == 0 {
            None
        } else {
            Some(self.sum.load(Ordering::SeqCst) as f64 / count as f64)
        }
    }

    fn min(&self) -> Option<i64> {
        let count = self.count();
        if count == 0 {
            None
        } else {
            Some(self.min.load(Ordering::SeqCst))
        }
    }

    fn max(&self) -> Option<i64> {
        let count = self.count();
        if count == 0 {
            None
        } else {
            Some(self.max.load(Ordering::SeqCst))
        }
    }

    fn parallel_record(&self, py: Python, values: Vec<i64>) -> PyResult<()> {
        let chunk_size = (values.len() + 3) / 4;

        py.allow_threads(|| {
            let handles: Vec<_> = values
                .chunks(chunk_size)
                .map(|chunk| {
                    let stats = AtomicStats {
                        count: Arc::clone(&self.count),
                        sum: Arc::clone(&self.sum),
                        min: Arc::clone(&self.min),
                        max: Arc::clone(&self.max),
                    };
                    let chunk = chunk.to_vec();

                    thread::spawn(move || {
                        for value in chunk {
                            stats.record(value);
                        }
                    })
                })
                .collect();

            for handle in handles {
                handle.join().unwrap();
            }
        });

        Ok(())
    }

    fn summary(&self) -> String {
        format!(
            "AtomicStats(count={}, sum={}, mean={:.2}, min={}, max={})",
            self.count(),
            self.sum(),
            self.mean().unwrap_or(0.0),
            self.min().unwrap_or(0),
            self.max().unwrap_or(0)
        )
    }
}

/// Lock-free progress tracker
#[pyfunction]
fn parallel_with_progress(
    py: Python,
    total: usize,
    thread_count: usize,
) -> PyResult<AtomicCounter> {
    let counter = AtomicCounter::new(0);
    let counter_ref = Arc::clone(&counter.value);

    py.allow_threads(|| {
        let chunk_size = (total + thread_count - 1) / thread_count;

        let handles: Vec<_> = (0..thread_count)
            .map(|i| {
                let start = i * chunk_size;
                let end = ((i + 1) * chunk_size).min(total);
                let counter = Arc::clone(&counter_ref);

                thread::spawn(move || {
                    for _ in start..end {
                        // Simulate work
                        let mut sum = 0;
                        for j in 0..1000 {
                            sum += j;
                        }
                        let _ = sum;

                        counter.fetch_add(1, Ordering::SeqCst);
                    }
                })
            })
            .collect();

        for handle in handles {
            handle.join().unwrap();
        }
    });

    Ok(counter)
}

/// Compare atomic vs mutex performance
#[pyfunction]
fn benchmark_atomic_vs_mutex(
    py: Python,
    increments: usize,
    thread_count: usize,
) -> PyResult<(f64, f64)> {
    use std::sync::Mutex;
    use std::time::Instant;

    // Atomic benchmark
    let atomic_counter = Arc::new(AtomicU64::new(0));
    let atomic_start = Instant::now();

    py.allow_threads(|| {
        let handles: Vec<_> = (0..thread_count)
            .map(|_| {
                let counter = Arc::clone(&atomic_counter);
                thread::spawn(move || {
                    for _ in 0..increments {
                        counter.fetch_add(1, Ordering::SeqCst);
                    }
                })
            })
            .collect();

        for handle in handles {
            handle.join().unwrap();
        }
    });

    let atomic_time = atomic_start.elapsed().as_secs_f64();

    // Mutex benchmark
    let mutex_counter = Arc::new(Mutex::new(0u64));
    let mutex_start = Instant::now();

    py.allow_threads(|| {
        let handles: Vec<_> = (0..thread_count)
            .map(|_| {
                let counter = Arc::clone(&mutex_counter);
                thread::spawn(move || {
                    for _ in 0..increments {
                        *counter.lock().unwrap() += 1;
                    }
                })
            })
            .collect();

        for handle in handles {
            handle.join().unwrap();
        }
    });

    let mutex_time = mutex_start.elapsed().as_secs_f64();

    Ok((atomic_time, mutex_time))
}

#[pymodule]
fn atomic_operations(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<AtomicCounter>()?;
    m.add_class::<AtomicFlag>()?;
    m.add_class::<AtomicStats>()?;
    m.add_function(wrap_pyfunction!(parallel_with_progress, m)?)?;
    m.add_function(wrap_pyfunction!(benchmark_atomic_vs_mutex, m)?)?;
    Ok(())
}
