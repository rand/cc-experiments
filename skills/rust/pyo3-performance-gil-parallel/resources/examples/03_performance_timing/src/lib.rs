use pyo3::prelude::*;
use std::time::{Duration, Instant};
use rayon::prelude::*;

/// Timer result containing duration and optional name
#[pyclass]
#[derive(Clone)]
pub struct TimerResult {
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    duration_secs: f64,
    #[pyo3(get)]
    iterations: usize,
}

#[pymethods]
impl TimerResult {
    fn per_iteration(&self) -> f64 {
        self.duration_secs / self.iterations as f64
    }

    fn ops_per_second(&self) -> f64 {
        self.iterations as f64 / self.duration_secs
    }

    fn __repr__(&self) -> String {
        format!(
            "TimerResult(name='{}', duration={:.6}s, iterations={}, per_iter={:.6}s, ops/sec={:.2f})",
            self.name,
            self.duration_secs,
            self.iterations,
            self.per_iteration(),
            self.ops_per_second()
        )
    }
}

/// High-resolution timer for benchmarking
#[pyclass]
pub struct Timer {
    start: Instant,
    name: String,
}

#[pymethods]
impl Timer {
    #[new]
    fn new(name: String) -> Self {
        Timer {
            start: Instant::now(),
            name,
        }
    }

    fn elapsed(&self) -> f64 {
        self.start.elapsed().as_secs_f64()
    }

    fn stop(&self, iterations: usize) -> TimerResult {
        TimerResult {
            name: self.name.clone(),
            duration_secs: self.elapsed(),
            iterations,
        }
    }

    fn __enter__(slf: PyRef<Self>) -> PyRef<Self> {
        slf
    }

    fn __exit__(&self, _exc_type: &PyAny, _exc_value: &PyAny, _traceback: &PyAny) -> bool {
        false
    }
}

/// Benchmark a function with multiple iterations
#[pyfunction]
fn benchmark<'py>(
    py: Python<'py>,
    name: String,
    func: &'py PyAny,
    iterations: usize,
) -> PyResult<TimerResult> {
    let start = Instant::now();

    for _ in 0..iterations {
        func.call0()?;
    }

    let duration = start.elapsed().as_secs_f64();

    Ok(TimerResult {
        name,
        duration_secs: duration,
        iterations,
    })
}

/// Compare sequential vs parallel performance
#[pyfunction]
fn compare_seq_vs_parallel(
    py: Python,
    data: Vec<f64>,
    iterations: usize,
) -> PyResult<(TimerResult, TimerResult)> {
    // Sequential benchmark
    let seq_start = Instant::now();
    for _ in 0..iterations {
        let _: f64 = data.iter().map(|x| x * x).sum();
    }
    let seq_duration = seq_start.elapsed().as_secs_f64();

    // Parallel benchmark
    let par_start = Instant::now();
    for _ in 0..iterations {
        py.allow_threads(|| {
            let _: f64 = data.par_iter().map(|x| x * x).sum();
        });
    }
    let par_duration = par_start.elapsed().as_secs_f64();

    Ok((
        TimerResult {
            name: "Sequential".to_string(),
            duration_secs: seq_duration,
            iterations,
        },
        TimerResult {
            name: "Parallel".to_string(),
            duration_secs: par_duration,
            iterations,
        },
    ))
}

/// Detailed performance profiler with multiple measurements
#[pyclass]
pub struct Profiler {
    measurements: Vec<(String, Duration)>,
}

#[pymethods]
impl Profiler {
    #[new]
    fn new() -> Self {
        Profiler {
            measurements: Vec::new(),
        }
    }

    fn measure(&mut self, name: String, duration_secs: f64) {
        self.measurements.push((name, Duration::from_secs_f64(duration_secs)));
    }

    fn results(&self) -> Vec<(String, f64)> {
        self.measurements
            .iter()
            .map(|(name, dur)| (name.clone(), dur.as_secs_f64()))
            .collect()
    }

    fn summary(&self) -> String {
        let total: Duration = self.measurements.iter().map(|(_, d)| *d).sum();
        let mut summary = format!("Profiler Summary (Total: {:.6}s)\n", total.as_secs_f64());

        for (name, duration) in &self.measurements {
            let percentage = (duration.as_secs_f64() / total.as_secs_f64()) * 100.0;
            summary.push_str(&format!(
                "  {}: {:.6}s ({:.1}%)\n",
                name,
                duration.as_secs_f64(),
                percentage
            ));
        }

        summary
    }
}

/// Benchmark function with warmup iterations
#[pyfunction]
fn benchmark_with_warmup(
    py: Python,
    name: String,
    func: &PyAny,
    warmup: usize,
    iterations: usize,
) -> PyResult<TimerResult> {
    // Warmup
    for _ in 0..warmup {
        func.call0()?;
    }

    // Actual benchmark
    let start = Instant::now();
    for _ in 0..iterations {
        func.call0()?;
    }
    let duration = start.elapsed().as_secs_f64();

    Ok(TimerResult {
        name,
        duration_secs: duration,
        iterations,
    })
}

/// Statistical benchmark with multiple runs
#[pyfunction]
fn benchmark_statistical(
    py: Python,
    name: String,
    func: &PyAny,
    runs: usize,
    iterations_per_run: usize,
) -> PyResult<(f64, f64, f64, f64)> {
    let mut durations = Vec::new();

    for _ in 0..runs {
        let start = Instant::now();
        for _ in 0..iterations_per_run {
            func.call0()?;
        }
        durations.push(start.elapsed().as_secs_f64());
    }

    let mean = durations.iter().sum::<f64>() / runs as f64;
    let mut sorted = durations.clone();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let median = sorted[runs / 2];
    let min = sorted[0];
    let max = sorted[runs - 1];

    Ok((mean, median, min, max))
}

/// Measure memory throughput (GB/s)
#[pyfunction]
fn measure_memory_throughput(py: Python, size: usize, iterations: usize) -> PyResult<f64> {
    let data: Vec<f64> = (0..size).map(|i| i as f64).collect();
    let bytes_per_iteration = size * std::mem::size_of::<f64>();

    let start = Instant::now();
    py.allow_threads(|| {
        for _ in 0..iterations {
            let _: f64 = data.par_iter().sum();
        }
    });
    let duration = start.elapsed().as_secs_f64();

    let total_bytes = bytes_per_iteration * iterations;
    let gb_per_sec = (total_bytes as f64 / 1_000_000_000.0) / duration;

    Ok(gb_per_sec)
}

#[pymodule]
fn performance_timing(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Timer>()?;
    m.add_class::<TimerResult>()?;
    m.add_class::<Profiler>()?;
    m.add_function(wrap_pyfunction!(benchmark, m)?)?;
    m.add_function(wrap_pyfunction!(compare_seq_vs_parallel, m)?)?;
    m.add_function(wrap_pyfunction!(benchmark_with_warmup, m)?)?;
    m.add_function(wrap_pyfunction!(benchmark_statistical, m)?)?;
    m.add_function(wrap_pyfunction!(measure_memory_throughput, m)?)?;
    Ok(())
}
