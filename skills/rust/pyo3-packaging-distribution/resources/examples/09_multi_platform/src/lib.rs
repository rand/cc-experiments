//! Multi-platform wheel building
//!
//! Demonstrates building wheels for all major platforms and architectures
//! using manylinux, macOS universal binaries, and Windows builds.

use pyo3::prelude::*;

/// Calculate sum using platform-optimized code path.
///
/// Args:
///     values: List of numbers to sum
///
/// Returns:
///     Sum of all values
#[pyfunction]
fn platform_sum(values: Vec<i64>) -> i64 {
    #[cfg(all(target_arch = "x86_64", target_feature = "sse2"))]
    {
        // Could use SSE2 optimizations on x86_64
        values.iter().sum()
    }

    #[cfg(all(target_arch = "aarch64", target_feature = "neon"))]
    {
        // Could use NEON optimizations on ARM
        values.iter().sum()
    }

    #[cfg(not(any(
        all(target_arch = "x86_64", target_feature = "sse2"),
        all(target_arch = "aarch64", target_feature = "neon")
    )))]
    {
        // Fallback implementation
        values.iter().sum()
    }
}

/// Get detailed platform information.
///
/// Returns:
///     Dictionary with platform, architecture, and ABI info
#[pyfunction]
fn get_platform_info(py: Python) -> PyResult<PyObject> {
    let dict = pyo3::types::PyDict::new(py);

    // Operating system
    dict.set_item("os", std::env::consts::OS)?;
    dict.set_item("os_family", std::env::consts::FAMILY)?;

    // Architecture
    dict.set_item("arch", std::env::consts::ARCH)?;
    dict.set_item("target", env!("TARGET"))?;

    // Build configuration
    dict.set_item("endian", if cfg!(target_endian = "little") { "little" } else { "big" })?;
    dict.set_item("pointer_width", std::mem::size_of::<usize>() * 8)?;

    // Platform-specific features
    #[cfg(target_os = "linux")]
    dict.set_item("platform", "linux")?;

    #[cfg(target_os = "macos")]
    dict.set_item("platform", "macos")?;

    #[cfg(target_os = "windows")]
    dict.set_item("platform", "windows")?;

    // ABI information
    #[cfg(all(target_os = "linux", target_env = "gnu"))]
    dict.set_item("abi", "gnu")?;

    #[cfg(all(target_os = "linux", target_env = "musl"))]
    dict.set_item("abi", "musl")?;

    #[cfg(target_os = "windows")]
    dict.set_item("abi", "msvc")?;

    Ok(dict.into())
}

/// Check if specific SIMD features are available.
///
/// Returns:
///     Dictionary of available SIMD features
#[pyfunction]
fn simd_features(py: Python) -> PyResult<PyObject> {
    let dict = pyo3::types::PyDict::new(py);

    #[cfg(target_arch = "x86_64")]
    {
        dict.set_item("sse2", cfg!(target_feature = "sse2"))?;
        dict.set_item("avx", cfg!(target_feature = "avx"))?;
        dict.set_item("avx2", cfg!(target_feature = "avx2"))?;
    }

    #[cfg(target_arch = "aarch64")]
    {
        dict.set_item("neon", cfg!(target_feature = "neon"))?;
    }

    Ok(dict.into())
}

/// Get wheel compatibility tag.
///
/// Returns:
///     Expected wheel platform tag
#[pyfunction]
fn wheel_tag() -> String {
    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    return "manylinux_2_17_x86_64".to_string();

    #[cfg(all(target_os = "linux", target_arch = "aarch64"))]
    return "manylinux_2_17_aarch64".to_string();

    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    return "macosx_10_12_x86_64".to_string();

    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    return "macosx_11_0_arm64".to_string();

    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    return "win_amd64".to_string();

    #[cfg(not(any(
        all(target_os = "linux", target_arch = "x86_64"),
        all(target_os = "linux", target_arch = "aarch64"),
        all(target_os = "macos", target_arch = "x86_64"),
        all(target_os = "macos", target_arch = "aarch64"),
        all(target_os = "windows", target_arch = "x86_64")
    )))]
    return "unknown".to_string();
}

/// Multi-platform wheel building example.
#[pymodule]
fn multi_platform(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(platform_sum, m)?)?;
    m.add_function(wrap_pyfunction!(get_platform_info, m)?)?;
    m.add_function(wrap_pyfunction!(simd_features, m)?)?;
    m.add_function(wrap_pyfunction!(wheel_tag, m)?)?;

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_platform_sum() {
        assert_eq!(platform_sum(vec![1, 2, 3, 4, 5]), 15);
    }

    #[test]
    fn test_wheel_tag() {
        let tag = wheel_tag();
        assert!(!tag.is_empty());
        assert_ne!(tag, "unknown");
    }
}
