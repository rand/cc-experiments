use pyo3::prelude::*;

pub fn internal_sum(data: &[f64]) -> f64 {
    data.iter().sum()
}

pub fn internal_factorial(n: u64) -> u64 {
    (1..=n).product()
}

pub fn internal_fibonacci(n: u32) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => {
            let mut a = 0u64;
            let mut b = 1u64;
            for _ in 2..=n {
                let tmp = a + b;
                a = b;
                b = tmp;
            }
            b
        }
    }
}

#[pyfunction]
fn fast_sum(data: Vec<f64>) -> f64 {
    internal_sum(&data)
}

#[pyfunction]
fn fast_factorial(n: u64) -> u64 {
    internal_factorial(n)
}

#[pyfunction]
fn fast_fibonacci(n: u32) -> u64 {
    internal_fibonacci(n)
}

#[pyfunction]
fn process_batch(data: Vec<Vec<f64>>) -> Vec<f64> {
    data.iter().map(|v| internal_sum(v)).collect()
}

#[pymodule]
fn benchmarking(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fast_sum, m)?)?;
    m.add_function(wrap_pyfunction!(fast_factorial, m)?)?;
    m.add_function(wrap_pyfunction!(fast_fibonacci, m)?)?;
    m.add_function(wrap_pyfunction!(process_batch, m)?)?;
    Ok(())
}
