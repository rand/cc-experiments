use pyo3::prelude::*;
use rayon::prelude::*;
use std::fs;
use std::path::Path;
use walkdir::WalkDir;

/// Process files in parallel with progress callback
#[pyfunction]
fn process_files_parallel(
    py: Python,
    paths: Vec<String>,
    callback: Option<PyObject>,
) -> PyResult<Vec<(String, usize)>> {
    py.allow_threads(|| {
        let results: Vec<(String, usize)> = paths
            .par_iter()
            .filter_map(|path| {
                let result = fs::read_to_string(path)
                    .ok()
                    .map(|content| {
                        let size = content.len();

                        // Call progress callback if provided
                        if let Some(ref cb) = callback {
                            Python::with_gil(|py| {
                                let _ = cb.call1(py, (path, size));
                            });
                        }

                        (path.clone(), size)
                    });
                result
            })
            .collect();

        results
    })
}

/// Find files matching pattern in parallel
#[pyfunction]
fn find_files_parallel(
    py: Python,
    directory: String,
    pattern: String,
    max_depth: Option<usize>,
) -> PyResult<Vec<String>> {
    let path = Path::new(&directory);

    if !path.exists() {
        return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
            format!("Directory not found: {}", directory)
        ));
    }

    py.allow_threads(|| {
        let walker = if let Some(depth) = max_depth {
            WalkDir::new(path).max_depth(depth)
        } else {
            WalkDir::new(path)
        };

        let results: Vec<String> = walker
            .into_iter()
            .par_bridge()
            .filter_map(|e| e.ok())
            .filter(|e| e.file_type().is_file())
            .filter_map(|e| {
                let file_path = e.path();
                let filename = file_path.file_name()?.to_str()?;

                // Simple pattern matching
                if pattern.starts_with('*') {
                    let suffix = pattern.trim_start_matches('*');
                    if filename.ends_with(suffix) {
                        return Some(file_path.to_string_lossy().to_string());
                    }
                } else if filename.contains(&pattern) {
                    return Some(file_path.to_string_lossy().to_string());
                }

                None
            })
            .collect();

        results
    })
}

/// Count lines in files in parallel
#[pyfunction]
fn count_lines_parallel(py: Python, paths: Vec<String>) -> PyResult<Vec<(String, usize)>> {
    py.allow_threads(|| {
        paths
            .par_iter()
            .filter_map(|path| {
                fs::read_to_string(path)
                    .ok()
                    .map(|content| (path.clone(), content.lines().count()))
            })
            .collect()
    })
}

/// Search pattern in files in parallel
#[pyfunction]
fn search_parallel(
    py: Python,
    pattern: String,
    paths: Vec<String>,
    case_sensitive: bool,
) -> PyResult<Vec<(String, usize)>> {
    py.allow_threads(|| {
        let search_pattern = if case_sensitive {
            pattern.clone()
        } else {
            pattern.to_lowercase()
        };

        paths
            .par_iter()
            .filter_map(|path| {
                fs::read_to_string(path).ok().and_then(|content| {
                    let count = if case_sensitive {
                        content.matches(&search_pattern).count()
                    } else {
                        content.to_lowercase().matches(&search_pattern).count()
                    };

                    if count > 0 {
                        Some((path.clone(), count))
                    } else {
                        None
                    }
                })
            })
            .collect()
    })
}

/// Calculate directory size in parallel
#[pyfunction]
fn directory_size_parallel(py: Python, directory: String) -> PyResult<u64> {
    let path = Path::new(&directory);

    if !path.exists() {
        return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
            format!("Directory not found: {}", directory)
        ));
    }

    py.allow_threads(|| {
        let size: u64 = WalkDir::new(path)
            .into_iter()
            .par_bridge()
            .filter_map(|e| e.ok())
            .filter(|e| e.file_type().is_file())
            .filter_map(|e| e.metadata().ok())
            .map(|m| m.len())
            .sum();

        size
    })
}

#[pymodule]
fn file_processing(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_files_parallel, m)?)?;
    m.add_function(wrap_pyfunction!(find_files_parallel, m)?)?;
    m.add_function(wrap_pyfunction!(count_lines_parallel, m)?)?;
    m.add_function(wrap_pyfunction!(search_parallel, m)?)?;
    m.add_function(wrap_pyfunction!(directory_size_parallel, m)?)?;
    Ok(())
}
