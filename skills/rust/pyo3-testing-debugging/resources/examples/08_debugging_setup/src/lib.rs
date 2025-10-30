use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

#[pyfunction]
fn divide(a: f64, b: f64) -> PyResult<f64> {
    // Breakpoint location for debugging
    if b == 0.0 {
        return Err(PyValueError::new_err("Division by zero"));
    }

    let result = a / b;
    Ok(result)
}

#[pyfunction]
fn complex_calculation(data: Vec<f64>) -> PyResult<f64> {
    if data.is_empty() {
        return Err(PyValueError::new_err("Empty data"));
    }

    let sum: f64 = data.iter().sum();
    let mean = sum / data.len() as f64;

    let variance: f64 = data.iter()
        .map(|&x| (x - mean).powi(2))
        .sum::<f64>() / data.len() as f64;

    Ok(variance.sqrt())
}

#[pyfunction]
fn process_with_debug(value: i32) -> String {
    let doubled = value * 2;
    let squared = doubled * doubled;

    format!("Processed: {} -> {} -> {}", value, doubled, squared)
}

#[pymodule]
fn debugging_setup(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(divide, m)?)?;
    m.add_function(wrap_pyfunction!(complex_calculation, m)?)?;
    m.add_function(wrap_pyfunction!(process_with_debug, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_divide() {
        assert_eq!(divide(10.0, 2.0).unwrap(), 5.0);
    }

    #[test]
    fn test_complex_calculation() {
        let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let result = complex_calculation(data).unwrap();
        assert!(result > 0.0);
    }
}
