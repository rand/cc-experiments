use pyo3::prelude::*;
use rayon::prelude::*;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

/// Statistics for pipeline execution
#[pyclass]
#[derive(Clone)]
pub struct PipelineStats {
    #[pyo3(get)]
    items_processed: usize,
    #[pyo3(get)]
    items_filtered: usize,
    #[pyo3(get)]
    items_failed: usize,
    #[pyo3(get)]
    duration_secs: f64,
}

/// Production-ready data processing pipeline
#[pyclass]
pub struct DataPipeline {
    thread_count: usize,
    batch_size: usize,
    processed: Arc<AtomicUsize>,
    filtered: Arc<AtomicUsize>,
    failed: Arc<AtomicUsize>,
}

#[pymethods]
impl DataPipeline {
    #[new]
    fn new(thread_count: usize, batch_size: usize) -> Self {
        DataPipeline {
            thread_count,
            batch_size,
            processed: Arc::new(AtomicUsize::new(0)),
            filtered: Arc::new(AtomicUsize::new(0)),
            failed: Arc::new(AtomicUsize::new(0)),
        }
    }

    fn process(&self, py: Python, data: Vec<f64>) -> PyResult<(Vec<f64>, PipelineStats)> {
        use std::time::Instant;
        let start = Instant::now();

        // Reset counters
        self.processed.store(0, Ordering::SeqCst);
        self.filtered.store(0, Ordering::SeqCst);
        self.failed.store(0, Ordering::SeqCst);

        let processed = Arc::clone(&self.processed);
        let filtered = Arc::clone(&self.filtered);
        let failed = Arc::clone(&self.failed);

        let results = py.allow_threads(|| {
            data.par_iter()
                .filter_map(|&x| {
                    // Stage 1: Validation
                    if x.is_nan() || x.is_infinite() {
                        failed.fetch_add(1, Ordering::SeqCst);
                        return None;
                    }

                    // Stage 2: Filter
                    if x < 0.0 {
                        filtered.fetch_add(1, Ordering::SeqCst);
                        return None;
                    }

                    // Stage 3: Transform
                    let result = x.sqrt() * 2.0;

                    // Stage 4: Post-validation
                    if result.is_finite() {
                        processed.fetch_add(1, Ordering::SeqCst);
                        Some(result)
                    } else {
                        failed.fetch_add(1, Ordering::SeqCst);
                        None
                    }
                })
                .collect()
        });

        let duration = start.elapsed().as_secs_f64();

        let stats = PipelineStats {
            items_processed: self.processed.load(Ordering::SeqCst),
            items_filtered: self.filtered.load(Ordering::SeqCst),
            items_failed: self.failed.load(Ordering::SeqCst),
            duration_secs: duration,
        };

        Ok((results, stats))
    }

    fn process_batched(&self, py: Python, data: Vec<f64>) -> PyResult<(Vec<f64>, PipelineStats)> {
        use std::time::Instant;
        let start = Instant::now();

        self.processed.store(0, Ordering::SeqCst);
        self.filtered.store(0, Ordering::SeqCst);
        self.failed.store(0, Ordering::SeqCst);

        let processed = Arc::clone(&self.processed);
        let filtered = Arc::clone(&self.filtered);
        let failed = Arc::clone(&self.failed);

        let results = py.allow_threads(|| {
            data.par_chunks(self.batch_size)
                .flat_map(|batch| {
                    let mut batch_results = Vec::new();

                    for &x in batch {
                        if x.is_nan() || x.is_infinite() {
                            failed.fetch_add(1, Ordering::SeqCst);
                            continue;
                        }

                        if x < 0.0 {
                            filtered.fetch_add(1, Ordering::SeqCst);
                            continue;
                        }

                        let result = x.sqrt() * 2.0;

                        if result.is_finite() {
                            processed.fetch_add(1, Ordering::SeqCst);
                            batch_results.push(result);
                        } else {
                            failed.fetch_add(1, Ordering::SeqCst);
                        }
                    }

                    batch_results
                })
                .collect()
        });

        let duration = start.elapsed().as_secs_f64();

        let stats = PipelineStats {
            items_processed: self.processed.load(Ordering::SeqCst),
            items_filtered: self.filtered.load(Ordering::SeqCst),
            items_failed: self.failed.load(Ordering::SeqCst),
            duration_secs: duration,
        };

        Ok((results, stats))
    }

    fn get_stats(&self) -> PipelineStats {
        PipelineStats {
            items_processed: self.processed.load(Ordering::SeqCst),
            items_filtered: self.filtered.load(Ordering::SeqCst),
            items_failed: self.failed.load(Ordering::SeqCst),
            duration_secs: 0.0,
        }
    }
}

/// High-performance aggregation pipeline
#[pyfunction]
fn aggregate_pipeline(
    py: Python,
    data: Vec<f64>,
) -> PyResult<(f64, f64, f64, f64, usize)> {
    let result = py.allow_threads(|| {
        data.par_iter()
            .filter(|x| x.is_finite())
            .fold(
                || (0.0, 0.0, f64::INFINITY, f64::NEG_INFINITY, 0),
                |(sum, sum_sq, min, max, count), &x| {
                    (
                        sum + x,
                        sum_sq + x * x,
                        min.min(x),
                        max.max(x),
                        count + 1,
                    )
                },
            )
            .reduce(
                || (0.0, 0.0, f64::INFINITY, f64::NEG_INFINITY, 0),
                |(sum1, sq1, min1, max1, c1), (sum2, sq2, min2, max2, c2)| {
                    (
                        sum1 + sum2,
                        sq1 + sq2,
                        min1.min(min2),
                        max1.max(max2),
                        c1 + c2,
                    )
                },
            )
    });

    let (sum, sum_sq, min, max, count) = result;
    let mean = if count > 0 { sum / count as f64 } else { 0.0 };
    let variance = if count > 0 {
        (sum_sq / count as f64) - (mean * mean)
    } else {
        0.0
    };

    Ok((mean, variance.sqrt(), min, max, count))
}

#[pymodule]
fn production_pipeline(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<DataPipeline>()?;
    m.add_class::<PipelineStats>()?;
    m.add_function(wrap_pyfunction!(aggregate_pipeline, m)?)?;
    Ok(())
}
