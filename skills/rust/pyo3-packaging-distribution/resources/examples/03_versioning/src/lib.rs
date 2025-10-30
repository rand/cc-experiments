//! Version management and runtime access
//!
//! Demonstrates semantic versioning, version synchronization between
//! Cargo.toml and pyproject.toml, and runtime version information access.

use pyo3::prelude::*;

/// Get the package version.
///
/// Returns:
///     Version string in semver format (e.g., "1.2.3")
///
/// Example:
///     >>> import versioning_example
///     >>> versioning_example.version()
///     '0.1.0'
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// Get detailed version information.
///
/// Returns:
///     Dictionary with version components
///
/// Example:
///     >>> import versioning_example
///     >>> info = versioning_example.version_info()
///     >>> info['major']
///     0
#[pyfunction]
fn version_info(py: Python) -> PyResult<PyObject> {
    let version = env!("CARGO_PKG_VERSION");
    let parts: Vec<&str> = version.split('.').collect();

    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("version", version)?;
    dict.set_item("major", parts.first().and_then(|s| s.parse::<u32>().ok()).unwrap_or(0))?;
    dict.set_item("minor", parts.get(1).and_then(|s| s.parse::<u32>().ok()).unwrap_or(0))?;
    dict.set_item("patch", parts.get(2).and_then(|s| s.parse::<u32>().ok()).unwrap_or(0))?;

    Ok(dict.into())
}

/// Check if the package version meets minimum requirements.
///
/// Args:
///     min_version: Minimum required version (e.g., "0.1.0")
///
/// Returns:
///     True if current version >= min_version
///
/// Example:
///     >>> import versioning_example
///     >>> versioning_example.check_version("0.1.0")
///     True
///     >>> versioning_example.check_version("1.0.0")
///     False
#[pyfunction]
fn check_version(min_version: &str) -> PyResult<bool> {
    let current = env!("CARGO_PKG_VERSION");
    Ok(compare_versions(current, min_version))
}

/// Compare two semantic versions.
///
/// Returns true if version_a >= version_b
fn compare_versions(version_a: &str, version_b: &str) -> bool {
    let parse_version = |v: &str| -> Vec<u32> {
        v.split('.')
            .filter_map(|s| s.parse::<u32>().ok())
            .collect()
    };

    let a = parse_version(version_a);
    let b = parse_version(version_b);

    for i in 0..a.len().max(b.len()) {
        let a_val = a.get(i).copied().unwrap_or(0);
        let b_val = b.get(i).copied().unwrap_or(0);

        if a_val > b_val {
            return true;
        } else if a_val < b_val {
            return false;
        }
    }

    true
}

/// Get build information including version and compile time.
///
/// Returns:
///     Dictionary with build metadata
///
/// Example:
///     >>> import versioning_example
///     >>> build = versioning_example.build_info()
///     >>> build['version']
///     '0.1.0'
#[pyfunction]
fn build_info(py: Python) -> PyResult<PyObject> {
    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("version", env!("CARGO_PKG_VERSION"))?;
    dict.set_item("pkg_name", env!("CARGO_PKG_NAME"))?;
    dict.set_item("rust_version", env!("CARGO_PKG_RUST_VERSION").to_string())?;

    // Add Git info if available (requires build.rs)
    dict.set_item("profile", if cfg!(debug_assertions) { "debug" } else { "release" })?;

    Ok(dict.into())
}

/// A package demonstrating version management and runtime access.
#[pymodule]
fn versioning_example(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(version_info, m)?)?;
    m.add_function(wrap_pyfunction!(check_version, m)?)?;
    m.add_function(wrap_pyfunction!(build_info, m)?)?;

    // Add version as module attribute
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        let v = version();
        assert!(!v.is_empty());
        assert!(v.contains('.'));
    }

    #[test]
    fn test_compare_versions() {
        assert!(compare_versions("1.0.0", "0.9.0"));
        assert!(compare_versions("1.0.0", "1.0.0"));
        assert!(!compare_versions("0.9.0", "1.0.0"));
        assert!(compare_versions("1.2.3", "1.2.2"));
    }

    #[test]
    fn test_check_version() {
        assert!(check_version("0.0.0").unwrap());
    }
}
