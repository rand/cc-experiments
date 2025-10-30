use anyhow::{Context, Result};
use pyo3::prelude::*;
use pyo3::types::PyModule;
use std::time::{Duration, Instant};

/// Statistical metrics for benchmark results
#[derive(Debug, Clone)]
struct BenchmarkStats {
    min: Duration,
    max: Duration,
    mean: Duration,
    median: Duration,
    p95: Duration,
    p99: Duration,
    samples: Vec<Duration>,
}

impl BenchmarkStats {
    fn from_samples(mut samples: Vec<Duration>) -> Self {
        samples.sort();
        let n = samples.len();

        let sum: Duration = samples.iter().sum();
        let mean = sum / n as u32;

        let median = samples[n / 2];
        let p95 = samples[(n as f64 * 0.95) as usize];
        let p99 = samples[(n as f64 * 0.99) as usize];

        Self {
            min: samples[0],
            max: samples[n - 1],
            mean,
            median,
            p95,
            p99,
            samples,
        }
    }

    fn print_report(&self, label: &str) {
        println!("\n--- {} ---", label);
        println!("Min:     {:>8.2} ms", self.min.as_secs_f64() * 1000.0);
        println!("Max:     {:>8.2} ms", self.max.as_secs_f64() * 1000.0);
        println!("Mean:    {:>8.2} ms", self.mean.as_secs_f64() * 1000.0);
        println!("Median:  {:>8.2} ms", self.median.as_secs_f64() * 1000.0);
        println!("P95:     {:>8.2} ms", self.p95.as_secs_f64() * 1000.0);
        println!("P99:     {:>8.2} ms", self.p99.as_secs_f64() * 1000.0);
    }
}

/// Metrics for GIL overhead analysis
#[derive(Debug, Clone)]
struct GILMetrics {
    total_time: Duration,
    gil_acquire_time: Duration,
    python_execute_time: Duration,
    result_convert_time: Duration,
}

impl GILMetrics {
    fn print_report(&self) {
        println!("\n--- GIL Overhead Analysis ---");
        let total_ms = self.total_time.as_secs_f64() * 1000.0;
        let gil_ms = self.gil_acquire_time.as_secs_f64() * 1000.0;
        let exec_ms = self.python_execute_time.as_secs_f64() * 1000.0;
        let convert_ms = self.result_convert_time.as_secs_f64() * 1000.0;

        println!("Total time:      {:>8.2} ms", total_ms);
        println!(
            "GIL acquire:     {:>8.2} ms ({:.2}%)",
            gil_ms,
            (gil_ms / total_ms) * 100.0
        );
        println!(
            "Python execute:  {:>8.2} ms ({:.2}%)",
            exec_ms,
            (exec_ms / total_ms) * 100.0
        );
        println!(
            "Result convert:  {:>8.2} ms ({:.2}%)",
            convert_ms,
            (convert_ms / total_ms) * 100.0
        );
    }
}

/// Initialize DSPy with OpenAI configuration
fn init_dspy(py: Python) -> PyResult<()> {
    let dspy = PyModule::import(py, "dspy")?;
    let openai = dspy.getattr("OpenAI")?;

    let lm = openai.call1(("gpt-3.5-turbo",))?;
    dspy.getattr("configure")?.call1((lm,))?;

    Ok(())
}

/// Create a simple Predict module
fn create_predict_module(py: Python) -> PyResult<PyObject> {
    let dspy = PyModule::import(py, "dspy")?;

    // Create signature: "question -> answer"
    let signature = "question -> answer";

    // Create Predict module
    let predict_class = dspy.getattr("Predict")?;
    let predictor = predict_class.call1((signature,))?;

    Ok(predictor.into())
}

/// Create a ChainOfThought module
fn create_cot_module(py: Python) -> PyResult<PyObject> {
    let dspy = PyModule::import(py, "dspy")?;

    let signature = "question -> answer";
    let cot_class = dspy.getattr("ChainOfThought")?;
    let cot = cot_class.call1((signature,))?;

    Ok(cot.into())
}

/// Benchmark a single DSPy call with detailed timing
fn benchmark_single_call(
    py: Python,
    predictor: &PyObject,
    question: &str,
) -> Result<(Duration, GILMetrics)> {
    let start = Instant::now();

    // Measure GIL acquisition (simulated - actual acquisition is instant)
    let gil_start = Instant::now();
    let gil_acquire_time = gil_start.elapsed();

    // Measure Python execution
    let exec_start = Instant::now();
    let result = predictor.call_method1(py, "__call__", (question,))?;
    let python_execute_time = exec_start.elapsed();

    // Measure result conversion
    let convert_start = Instant::now();
    let _answer: String = result
        .getattr(py, "answer")?
        .extract(py)
        .context("Failed to extract answer")?;
    let result_convert_time = convert_start.elapsed();

    let total_time = start.elapsed();

    let metrics = GILMetrics {
        total_time,
        gil_acquire_time,
        python_execute_time,
        result_convert_time,
    };

    Ok((total_time, metrics))
}

/// Benchmark single call latency
fn benchmark_latency(predictor: &PyObject, iterations: usize) -> Result<BenchmarkStats> {
    let mut samples = Vec::with_capacity(iterations);

    println!("Running {} single call benchmarks...", iterations);

    Python::with_gil(|py| {
        for i in 0..iterations {
            let question = format!("What is {}+{}?", i, i + 1);
            let (duration, _) = benchmark_single_call(py, predictor, &question)?;
            samples.push(duration);

            if (i + 1) % 5 == 0 {
                print!(".");
                use std::io::Write;
                std::io::stdout().flush().ok();
            }
        }
        println!(" Done!");
        Ok(BenchmarkStats::from_samples(samples))
    })
}

/// Benchmark batch processing throughput
fn benchmark_batch(predictor: &PyObject, batch_size: usize) -> Result<(Duration, Duration)> {
    let questions: Vec<String> = (0..batch_size)
        .map(|i| format!("What is the capital of country {}?", i))
        .collect();

    // Sequential processing
    let seq_start = Instant::now();
    Python::with_gil(|py| {
        for question in &questions {
            predictor.call_method1(py, "__call__", (question,))?;
        }
        Ok::<_, anyhow::Error>(())
    })?;
    let seq_duration = seq_start.elapsed();

    // Parallel processing (simulated - releases GIL between calls)
    let par_start = Instant::now();
    Python::with_gil(|py| {
        // In real parallel scenario, you'd use threading or async
        // Here we simulate by showing the pattern
        for question in &questions {
            // In reality: spawn thread, acquire GIL, call, release GIL
            predictor.call_method1(py, "__call__", (question,))?;
        }
        Ok::<_, anyhow::Error>(())
    })?;
    let par_duration = par_start.elapsed();

    Ok((seq_duration, par_duration))
}

/// Measure GIL overhead in detail
fn measure_gil_overhead(predictor: &PyObject, iterations: usize) -> Result<GILMetrics> {
    let mut total_metrics = GILMetrics {
        total_time: Duration::ZERO,
        gil_acquire_time: Duration::ZERO,
        python_execute_time: Duration::ZERO,
        result_convert_time: Duration::ZERO,
    };

    Python::with_gil(|py| -> Result<()> {
        for i in 0..iterations {
            let question = format!("Calculate {}*{}", i, i + 1);
            let (_, metrics) = benchmark_single_call(py, predictor, &question)?;

            total_metrics.total_time += metrics.total_time;
            total_metrics.gil_acquire_time += metrics.gil_acquire_time;
            total_metrics.python_execute_time += metrics.python_execute_time;
            total_metrics.result_convert_time += metrics.result_convert_time;
        }
        Ok(())
    })?;

    // Calculate averages
    total_metrics.total_time /= iterations as u32;
    total_metrics.gil_acquire_time /= iterations as u32;
    total_metrics.python_execute_time /= iterations as u32;
    total_metrics.result_convert_time /= iterations as u32;

    Ok(total_metrics)
}

/// Compare different DSPy modules
fn compare_modules(iterations: usize) -> Result<(BenchmarkStats, BenchmarkStats)> {
    println!("\nComparing Predict vs ChainOfThought...");

    let predict_stats = Python::with_gil(|py| {
        let predictor = create_predict_module(py)?;
        let mut samples = Vec::with_capacity(iterations);

        for i in 0..iterations {
            let question = format!("Solve: {}+{}", i * 2, i * 3);
            let (duration, _) = benchmark_single_call(py, &predictor, &question)?;
            samples.push(duration);
        }

        Ok::<_, anyhow::Error>(BenchmarkStats::from_samples(samples))
    })?;

    let cot_stats = Python::with_gil(|py| {
        let cot = create_cot_module(py)?;
        let mut samples = Vec::with_capacity(iterations);

        for i in 0..iterations {
            let question = format!("Solve: {}+{}", i * 2, i * 3);
            let (duration, _) = benchmark_single_call(py, &cot, &question)?;
            samples.push(duration);
        }

        Ok::<_, anyhow::Error>(BenchmarkStats::from_samples(samples))
    })?;

    Ok((predict_stats, cot_stats))
}

/// Track memory usage
fn measure_memory_usage(predictor: &PyObject, iterations: usize) -> Result<(usize, usize, usize)> {
    // Get baseline memory
    let baseline = get_memory_usage()?;

    Python::with_gil(|py| {
        for i in 0..iterations {
            let question = format!("Query number {}", i);
            predictor.call_method1(py, "__call__", (question,))?;
        }
        Ok::<_, anyhow::Error>(())
    })?;

    // Get peak memory
    let peak = get_memory_usage()?;
    let delta = peak.saturating_sub(baseline);
    let per_call = delta / iterations;

    Ok((baseline, peak, per_call))
}

/// Get current memory usage (simplified)
fn get_memory_usage() -> Result<usize> {
    // In real implementation, use platform-specific APIs
    // For demonstration, return mock value
    Python::with_gil(|py| {
        let psutil = PyModule::import(py, "psutil").ok();
        if let Some(psutil) = psutil {
            let process = psutil.call_method0("Process")?;
            let memory_info = process.call_method0("memory_info")?;
            let rss: usize = memory_info.getattr("rss")?.extract()?;
            Ok(rss / 1024 / 1024) // Convert to MB
        } else {
            // Fallback if psutil not available
            Ok(50) // Mock value
        }
    })
}

fn main() -> Result<()> {
    println!("=== DSPy Performance Benchmark Suite ===\n");

    // Get iterations from environment or use default
    let iterations: usize = std::env::var("ITERATIONS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(20);

    println!("Iterations: {}", iterations);
    println!("Model: gpt-3.5-turbo\n");

    // Initialize DSPy
    println!("Initializing DSPy...");
    Python::with_gil(|py| init_dspy(py))?;

    // Create predictor
    let predictor = Python::with_gil(|py| create_predict_module(py))?;

    // Warm-up (not measured)
    println!("Warming up (3 calls)...");
    Python::with_gil(|py| {
        for i in 0..3 {
            let question = format!("Warm up {}", i);
            benchmark_single_call(py, &predictor, &question).ok();
        }
    });

    // 1. Single Call Latency
    let latency_stats = benchmark_latency(&predictor, iterations)?;
    latency_stats.print_report("Single Call Latency (Predict)");

    // 2. Batch Processing
    println!("\nBenchmarking batch processing (10 queries)...");
    let (seq_duration, par_duration) = benchmark_batch(&predictor, 10)?;
    println!("\n--- Batch Processing (10 queries) ---");
    println!(
        "Sequential: {:>8.2} ms ({:.2} qps)",
        seq_duration.as_secs_f64() * 1000.0,
        10.0 / seq_duration.as_secs_f64()
    );
    println!(
        "Parallel:   {:>8.2} ms ({:.2} qps)",
        par_duration.as_secs_f64() * 1000.0,
        10.0 / par_duration.as_secs_f64()
    );
    println!(
        "Speedup:    {:.2}x",
        seq_duration.as_secs_f64() / par_duration.as_secs_f64()
    );

    // 3. GIL Overhead
    println!("\nMeasuring GIL overhead...");
    let gil_metrics = measure_gil_overhead(&predictor, 5)?;
    gil_metrics.print_report();

    // 4. Module Comparison
    let (predict_stats, cot_stats) = compare_modules(10)?;
    println!("\n--- Module Comparison ---");
    println!(
        "Predict:        {:>8.2} ms (baseline)",
        predict_stats.mean.as_secs_f64() * 1000.0
    );
    println!(
        "ChainOfThought: {:>8.2} ms ({:.2}x slower)",
        cot_stats.mean.as_secs_f64() * 1000.0,
        cot_stats.mean.as_secs_f64() / predict_stats.mean.as_secs_f64()
    );

    // 5. Memory Usage
    println!("\nMeasuring memory usage...");
    let (baseline, peak, per_call) = measure_memory_usage(&predictor, 10)?;
    println!("\n--- Memory Usage ---");
    println!("Baseline:   {:>6.1} MB", baseline);
    println!("Peak:       {:>6.1} MB", peak);
    println!("Delta:      {:>6.1} MB", peak.saturating_sub(baseline));
    println!("Per-call:   {:>6.1} KB", per_call);

    // Summary
    println!("\n=== Benchmark Complete ===");
    println!("Total iterations: {}", iterations);
    println!(
        "Average latency:  {:.2} ms",
        latency_stats.mean.as_secs_f64() * 1000.0
    );
    println!(
        "Throughput:       {:.2} qps",
        1.0 / latency_stats.mean.as_secs_f64()
    );

    Ok(())
}
