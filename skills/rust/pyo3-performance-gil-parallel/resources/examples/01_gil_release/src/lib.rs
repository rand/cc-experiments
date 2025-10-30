use pyo3::prelude::*;
use std::thread;
use std::time::{Duration, Instant};

/// Simulates CPU-intensive work (computing prime numbers)
fn compute_primes(n: u64) -> Vec<u64> {
    let mut primes = Vec::new();

    for num in 2..=n {
        let mut is_prime = true;
        for p in &primes {
            if p * p > num {
                break;
            }
            if num % p == 0 {
                is_prime = false;
                break;
            }
        }
        if is_prime {
            primes.push(num);
        }
    }

    primes
}

/// CPU-intensive function WITHOUT GIL release
/// This blocks Python threads while computing
#[pyfunction]
fn compute_primes_blocking(n: u64) -> PyResult<usize> {
    let primes = compute_primes(n);
    Ok(primes.len())
}

/// CPU-intensive function WITH GIL release
/// This allows other Python threads to run during computation
#[pyfunction]
fn compute_primes_releasing(py: Python, n: u64) -> PyResult<usize> {
    let result = py.allow_threads(|| {
        compute_primes(n)
    });
    Ok(result.len())
}

/// Demonstrates the performance difference with timing
#[pyfunction]
fn benchmark_gil_release(py: Python, n: u64, iterations: usize) -> PyResult<(f64, f64)> {
    // Benchmark without GIL release
    let start = Instant::now();
    for _ in 0..iterations {
        let _ = compute_primes(n);
    }
    let blocking_time = start.elapsed().as_secs_f64();

    // Benchmark with GIL release
    let start = Instant::now();
    for _ in 0..iterations {
        py.allow_threads(|| {
            let _ = compute_primes(n);
        });
    }
    let releasing_time = start.elapsed().as_secs_f64();

    Ok((blocking_time, releasing_time))
}

/// Demonstrates multi-threaded work with GIL release
#[pyfunction]
fn parallel_compute(py: Python, n: u64, thread_count: usize) -> PyResult<Vec<usize>> {
    py.allow_threads(|| {
        let handles: Vec<_> = (0..thread_count)
            .map(|i| {
                let start = (n / thread_count as u64) * i as u64;
                let end = if i == thread_count - 1 {
                    n
                } else {
                    (n / thread_count as u64) * (i + 1) as u64
                };

                thread::spawn(move || {
                    compute_primes(end).len() - compute_primes(start).len()
                })
            })
            .collect();

        handles
            .into_iter()
            .map(|h| h.join().unwrap())
            .collect()
    })
}

/// Sleep function that demonstrates GIL release for I/O-like operations
#[pyfunction]
fn sleep_releasing(py: Python, seconds: f64) -> PyResult<()> {
    py.allow_threads(|| {
        thread::sleep(Duration::from_secs_f64(seconds));
    });
    Ok(())
}

#[pymodule]
fn gil_release(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_primes_blocking, m)?)?;
    m.add_function(wrap_pyfunction!(compute_primes_releasing, m)?)?;
    m.add_function(wrap_pyfunction!(benchmark_gil_release, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_compute, m)?)?;
    m.add_function(wrap_pyfunction!(sleep_releasing, m)?)?;
    Ok(())
}
