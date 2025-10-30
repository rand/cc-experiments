//! Cross-compilation example
//!
//! Demonstrates platform detection, architecture-specific optimizations,
//! and building wheels for multiple platforms.

use pyo3::prelude::*;
use std::env;

/// Get platform information.
///
/// Returns:
///     Dictionary with OS, architecture, and target information
///
/// Example:
///     >>> import cross_compile
///     >>> info = cross_compile.platform_info()
///     >>> info['os']
///     'linux'
#[pyfunction]
fn platform_info(py: Python) -> PyResult<PyObject> {
    let dict = pyo3::types::PyDict::new(py);

    // Operating system
    dict.set_item("os", env::consts::OS)?;
    dict.set_item("family", env::consts::FAMILY)?;
    dict.set_item("arch", env::consts::ARCH)?;

    // Target information (compile-time)
    dict.set_item("target", env!("TARGET"))?;
    dict.set_item("target_os", std::env::consts::OS)?;
    dict.set_item("target_arch", std::env::consts::ARCH)?;

    // Endianness
    dict.set_item("is_little_endian", cfg!(target_endian = "little"))?;

    // Pointer width
    dict.set_item("pointer_width", std::mem::size_of::<usize>() * 8)?;

    Ok(dict.into())
}

/// Platform-specific calculation using SIMD when available.
///
/// Args:
///     values: List of integers to sum
///
/// Returns:
///     Sum of all values
///
/// Example:
///     >>> import cross_compile
///     >>> cross_compile.optimized_sum([1, 2, 3, 4, 5])
///     15
#[pyfunction]
fn optimized_sum(values: Vec<i64>) -> i64 {
    // In a real implementation, you might use:
    // - SIMD on x86_64 with AVX2
    // - NEON on ARM
    // - Fallback for other architectures

    #[cfg(target_arch = "x86_64")]
    {
        // Could use x86_64-specific optimizations here
        values.iter().sum()
    }

    #[cfg(target_arch = "aarch64")]
    {
        // Could use ARM NEON optimizations here
        values.iter().sum()
    }

    #[cfg(not(any(target_arch = "x86_64", target_arch = "aarch64")))]
    {
        // Fallback for other architectures
        values.iter().sum()
    }
}

/// Check if running on a specific platform.
///
/// Args:
///     platform: Platform name ("linux", "macos", "windows")
///
/// Returns:
///     True if running on specified platform
#[pyfunction]
fn is_platform(platform: &str) -> bool {
    match platform.to_lowercase().as_str() {
        "linux" => cfg!(target_os = "linux"),
        "macos" | "darwin" => cfg!(target_os = "macos"),
        "windows" | "win" => cfg!(target_os = "windows"),
        _ => false,
    }
}

/// Get build-time platform information.
///
/// Returns:
///     Dictionary with compile-time platform details
#[pyfunction]
fn build_platform(py: Python) -> PyResult<PyObject> {
    let dict = pyo3::types::PyDict::new(py);

    dict.set_item("target", env!("TARGET"))?;

    // Platform checks
    dict.set_item("is_linux", cfg!(target_os = "linux"))?;
    dict.set_item("is_macos", cfg!(target_os = "macos"))?;
    dict.set_item("is_windows", cfg!(target_os = "windows"))?;

    // Architecture checks
    dict.set_item("is_x86_64", cfg!(target_arch = "x86_64"))?;
    dict.set_item("is_aarch64", cfg!(target_arch = "aarch64"))?;
    dict.set_item("is_x86", cfg!(target_arch = "x86"))?;

    // Unix vs Windows
    dict.set_item("is_unix", cfg!(unix))?;
    dict.set_item("is_windows_family", cfg!(windows))?;

    Ok(dict.into())
}

/// Platform-specific path separator.
///
/// Returns:
///     Path separator character for this platform
#[pyfunction]
fn path_separator() -> &'static str {
    std::path::MAIN_SEPARATOR_STR
}

/// Get number of CPU cores.
///
/// Returns:
///     Number of logical CPU cores
#[pyfunction]
fn cpu_count() -> usize {
    num_cpus::get()
}

/// Package demonstrating cross-compilation and platform detection.
#[pymodule]
fn cross_compile(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(platform_info, m)?)?;
    m.add_function(wrap_pyfunction!(optimized_sum, m)?)?;
    m.add_function(wrap_pyfunction!(is_platform, m)?)?;
    m.add_function(wrap_pyfunction!(build_platform, m)?)?;
    m.add_function(wrap_pyfunction!(path_separator, m)?)?;
    m.add_function(wrap_pyfunction!(cpu_count, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_optimized_sum() {
        assert_eq!(optimized_sum(vec![1, 2, 3, 4, 5]), 15);
    }

    #[test]
    fn test_is_platform() {
        // At least one should be true
        assert!(
            is_platform("linux")
                || is_platform("macos")
                || is_platform("windows")
        );
    }

    #[test]
    fn test_path_separator() {
        let sep = path_separator();
        #[cfg(unix)]
        assert_eq!(sep, "/");
        #[cfg(windows)]
        assert_eq!(sep, "\\");
    }
}
