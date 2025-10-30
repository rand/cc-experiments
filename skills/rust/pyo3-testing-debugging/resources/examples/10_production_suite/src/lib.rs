use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use std::collections::HashMap;

pub mod compute {
    pub fn sum(data: &[f64]) -> f64 {
        data.iter().sum()
    }

    pub fn mean(data: &[f64]) -> Option<f64> {
        if data.is_empty() {
            None
        } else {
            Some(sum(data) / data.len() as f64)
        }
    }

    pub fn variance(data: &[f64]) -> Option<f64> {
        let m = mean(data)?;
        let var = data.iter()
            .map(|&x| (x - m).powi(2))
            .sum::<f64>() / data.len() as f64;
        Some(var)
    }

    pub fn std_dev(data: &[f64]) -> Option<f64> {
        variance(data).map(|v| v.sqrt())
    }
}

pub mod validation {
    use super::PyValueError;
    use pyo3::PyResult;

    pub fn validate_non_empty(data: &[f64]) -> PyResult<()> {
        if data.is_empty() {
            Err(PyValueError::new_err("Data cannot be empty"))
        } else {
            Ok(())
        }
    }

    pub fn validate_range(data: &[f64], min: f64, max: f64) -> PyResult<()> {
        if min > max {
            return Err(PyValueError::new_err("Min cannot exceed max"));
        }

        for (i, &val) in data.iter().enumerate() {
            if val < min || val > max {
                return Err(PyValueError::new_err(
                    format!("Value at index {} ({}) outside range [{}, {}]", i, val, min, max)
                ));
            }
        }
        Ok(())
    }

    pub fn validate_no_nan(data: &[f64]) -> PyResult<()> {
        if data.iter().any(|x| x.is_nan()) {
            Err(PyValueError::new_err("Data contains NaN values"))
        } else {
            Ok(())
        }
    }
}

#[pyfunction]
fn compute_statistics(data: Vec<f64>) -> PyResult<HashMap<String, f64>> {
    validation::validate_non_empty(&data)?;
    validation::validate_no_nan(&data)?;

    let mut stats = HashMap::new();
    stats.insert("count".to_string(), data.len() as f64);
    stats.insert("sum".to_string(), compute::sum(&data));

    if let Some(mean) = compute::mean(&data) {
        stats.insert("mean".to_string(), mean);
    }

    if let Some(variance) = compute::variance(&data) {
        stats.insert("variance".to_string(), variance);
    }

    if let Some(std_dev) = compute::std_dev(&data) {
        stats.insert("std_dev".to_string(), std_dev);
    }

    Ok(stats)
}

#[pyfunction]
fn process_with_validation(data: Vec<f64>, min: f64, max: f64) -> PyResult<Vec<f64>> {
    validation::validate_non_empty(&data)?;
    validation::validate_range(&data, min, max)?;
    validation::validate_no_nan(&data)?;

    Ok(data.iter().map(|&x| x * x).collect())
}

#[pyfunction]
fn parallel_process(py: Python<'_>, batches: Vec<Vec<f64>>) -> PyResult<Vec<f64>> {
    if batches.is_empty() {
        return Err(PyValueError::new_err("No batches to process"));
    }

    py.allow_threads(|| {
        let results: Vec<f64> = batches.iter()
            .map(|batch| compute::sum(batch))
            .collect();
        Ok(results)
    })
}

#[pymodule]
fn production_suite(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_statistics, m)?)?;
    m.add_function(wrap_pyfunction!(process_with_validation, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_process, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    mod compute_tests {
        use super::compute::*;

        #[test]
        fn test_sum() {
            assert_eq!(sum(&[1.0, 2.0, 3.0]), 6.0);
        }

        #[test]
        fn test_mean() {
            assert_eq!(mean(&[1.0, 2.0, 3.0]), Some(2.0));
            assert_eq!(mean(&[]), None);
        }

        #[test]
        fn test_variance() {
            let data = vec![2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0];
            let var = variance(&data).unwrap();
            assert!((var - 4.0).abs() < 0.01);
        }
    }

    mod validation_tests {
        use super::*;

        #[test]
        fn test_validate_non_empty() {
            assert!(validation::validate_non_empty(&[1.0]).is_ok());
            assert!(validation::validate_non_empty(&[]).is_err());
        }

        #[test]
        fn test_validate_range() {
            assert!(validation::validate_range(&[5.0], 0.0, 10.0).is_ok());
            assert!(validation::validate_range(&[15.0], 0.0, 10.0).is_err());
        }
    }

    #[cfg(test)]
    mod proptests {
        use super::*;
        use proptest::prelude::*;

        proptest! {
            #[test]
            fn test_sum_commutative(a in -1000.0..1000.0, b in -1000.0..1000.0) {
                let sum1 = compute::sum(&[a, b]);
                let sum2 = compute::sum(&[b, a]);
                prop_assert!((sum1 - sum2).abs() < 1e-10);
            }

            #[test]
            fn test_mean_in_range(data in prop::collection::vec(-100.0..100.0, 1..100)) {
                if let Some(m) = compute::mean(&data) {
                    let min = data.iter().cloned().fold(f64::INFINITY, f64::min);
                    let max = data.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
                    prop_assert!(m >= min && m <= max);
                }
            }
        }
    }
}
