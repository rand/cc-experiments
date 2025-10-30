use pyo3::prelude::*;

/// Sum a list of numbers
#[pyfunction]
fn sum_numbers(data: Vec<f64>) -> f64 {
    data.iter().sum()
}

/// Reverse a list
#[pyfunction]
fn reverse_list(data: Vec<i32>) -> Vec<i32> {
    data.into_iter().rev().collect()
}

/// Sort a list
#[pyfunction]
fn sort_list(mut data: Vec<i32>) -> Vec<i32> {
    data.sort();
    data
}

/// Check if list is sorted
#[pyfunction]
fn is_sorted(data: Vec<i32>) -> bool {
    data.windows(2).all(|w| w[0] <= w[1])
}

/// Multiply all elements by a factor
#[pyfunction]
fn scale(data: Vec<f64>, factor: f64) -> Vec<f64> {
    data.iter().map(|&x| x * factor).collect()
}

#[pymodule]
fn property_testing(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_numbers, m)?)?;
    m.add_function(wrap_pyfunction!(reverse_list, m)?)?;
    m.add_function(wrap_pyfunction!(sort_list, m)?)?;
    m.add_function(wrap_pyfunction!(is_sorted, m)?)?;
    m.add_function(wrap_pyfunction!(scale, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    // Pure Rust functions for testing
    fn rust_sum(data: &[f64]) -> f64 {
        data.iter().sum()
    }

    fn rust_reverse(data: Vec<i32>) -> Vec<i32> {
        data.into_iter().rev().collect()
    }

    fn rust_sort(mut data: Vec<i32>) -> Vec<i32> {
        data.sort();
        data
    }

    // Property tests
    proptest! {
        #[test]
        fn test_sum_commutative(a in 0.0..1000.0, b in 0.0..1000.0) {
            let sum1 = rust_sum(&[a, b]);
            let sum2 = rust_sum(&[b, a]);
            prop_assert!((sum1 - sum2).abs() < 1e-10);
        }

        #[test]
        fn test_reverse_is_involution(data in prop::collection::vec(any::<i32>(), 0..100)) {
            let reversed = rust_reverse(data.clone());
            let double_reversed = rust_reverse(reversed);
            prop_assert_eq!(data, double_reversed);
        }

        #[test]
        fn test_sort_is_idempotent(data in prop::collection::vec(any::<i32>(), 0..100)) {
            let sorted_once = rust_sort(data.clone());
            let sorted_twice = rust_sort(sorted_once.clone());
            prop_assert_eq!(sorted_once, sorted_twice);
        }

        #[test]
        fn test_sort_preserves_length(data in prop::collection::vec(any::<i32>(), 0..100)) {
            let original_len = data.len();
            let sorted = rust_sort(data);
            prop_assert_eq!(original_len, sorted.len());
        }

        #[test]
        fn test_scale_distributive(data in prop::collection::vec(-100.0..100.0, 0..50), factor in -10.0..10.0) {
            let sum_then_scale = rust_sum(&data) * factor;
            let scaled: Vec<f64> = data.iter().map(|&x| x * factor).collect();
            let scale_then_sum = rust_sum(&scaled);
            prop_assert!((sum_then_scale - scale_then_sum).abs() < 1e-6);
        }
    }
}
