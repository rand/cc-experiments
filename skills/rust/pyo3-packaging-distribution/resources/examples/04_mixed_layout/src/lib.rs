//! Mixed Rust/Python project layout
//!
//! Demonstrates how to structure a package with both Rust extensions
//! and pure Python code, allowing for a hybrid approach.

use pyo3::prelude::*;

/// Fast Fibonacci calculation using Rust.
///
/// Args:
///     n: Position in Fibonacci sequence
///
/// Returns:
///     nth Fibonacci number
///
/// Example:
///     >>> from mixed_layout import _core
///     >>> _core.fibonacci(10)
///     55
#[pyfunction]
fn fibonacci(n: u32) -> u64 {
    if n <= 1 {
        return n as u64;
    }

    let mut a = 0u64;
    let mut b = 1u64;

    for _ in 2..=n {
        let tmp = a + b;
        a = b;
        b = tmp;
    }

    b
}

/// Compute greatest common divisor using Euclidean algorithm.
///
/// Args:
///     a: First number
///     b: Second number
///
/// Returns:
///     GCD of a and b
///
/// Example:
///     >>> from mixed_layout import _core
///     >>> _core.gcd(48, 18)
///     6
#[pyfunction]
fn gcd(mut a: i64, mut b: i64) -> i64 {
    while b != 0 {
        let tmp = b;
        b = a % b;
        a = tmp;
    }
    a.abs()
}

/// Fast sum of integers in a range.
///
/// Args:
///     start: Start of range (inclusive)
///     end: End of range (exclusive)
///
/// Returns:
///     Sum of all integers in [start, end)
///
/// Example:
///     >>> from mixed_layout import _core
///     >>> _core.sum_range(1, 101)
///     5050
#[pyfunction]
fn sum_range(start: i64, end: i64) -> i64 {
    if start >= end {
        return 0;
    }
    let n = end - start;
    (n * (start + end - 1)) / 2
}

/// Core Rust extension module for mixed_layout.
///
/// This is typically imported by the Python wrapper layer.
/// Users should use the public API in the `mixed_layout` Python package.
#[pymodule]
fn _core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fibonacci, m)?)?;
    m.add_function(wrap_pyfunction!(gcd, m)?)?;
    m.add_function(wrap_pyfunction!(sum_range, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fibonacci() {
        assert_eq!(fibonacci(0), 0);
        assert_eq!(fibonacci(1), 1);
        assert_eq!(fibonacci(10), 55);
        assert_eq!(fibonacci(20), 6765);
    }

    #[test]
    fn test_gcd() {
        assert_eq!(gcd(48, 18), 6);
        assert_eq!(gcd(100, 50), 50);
        assert_eq!(gcd(17, 19), 1);
    }

    #[test]
    fn test_sum_range() {
        assert_eq!(sum_range(1, 101), 5050);
        assert_eq!(sum_range(0, 10), 45);
        assert_eq!(sum_range(5, 5), 0);
    }
}
