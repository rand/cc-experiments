use pyo3::prelude::*;
use std::collections::HashMap;

/// Compute statistics for a list of numbers
#[pyfunction]
fn compute_stats(data: Vec<f64>) -> PyResult<HashMap<String, f64>> {
    let count = data.len();
    let sum: f64 = data.iter().sum();
    let mean = if count > 0 { sum / count as f64 } else { 0.0 };

    let mut stats = HashMap::new();
    stats.insert("count".to_string(), count as f64);
    stats.insert("sum".to_string(), sum);
    stats.insert("mean".to_string(), mean);

    if count > 0 {
        let min = data.iter().cloned().fold(f64::INFINITY, f64::min);
        let max = data.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        stats.insert("min".to_string(), min);
        stats.insert("max".to_string(), max);
    }

    Ok(stats)
}

/// Filter data by threshold
#[pyfunction]
fn filter_above(data: Vec<f64>, threshold: f64) -> Vec<f64> {
    data.into_iter().filter(|&x| x > threshold).collect()
}

/// Normalize data to range [0, 1]
#[pyfunction]
fn normalize(data: Vec<f64>) -> PyResult<Vec<f64>> {
    if data.is_empty() {
        return Ok(vec![]);
    }

    let min = data.iter().cloned().fold(f64::INFINITY, f64::min);
    let max = data.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

    if (max - min).abs() < 1e-10 {
        // All values are the same
        return Ok(vec![0.5; data.len()]);
    }

    let normalized: Vec<f64> = data.iter()
        .map(|&x| (x - min) / (max - min))
        .collect();

    Ok(normalized)
}

#[pymodule]
fn python_tests(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_stats, m)?)?;
    m.add_function(wrap_pyfunction!(filter_above, m)?)?;
    m.add_function(wrap_pyfunction!(normalize, m)?)?;
    Ok(())
}
