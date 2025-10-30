use pyo3::prelude::*;
use std::fs;
use std::path::Path;

/// Search for a pattern in a file with line numbers
///
/// # Arguments
/// * `pattern` - The search pattern (case-sensitive)
/// * `filepath` - Path to the file to search
/// * `case_sensitive` - Whether to perform case-sensitive search
///
/// # Returns
/// Vector of (line_number, line_content) tuples for matching lines
#[pyfunction]
fn search_file(
    pattern: String,
    filepath: String,
    case_sensitive: bool,
) -> PyResult<Vec<(usize, String)>> {
    let path = Path::new(&filepath);

    if !path.exists() {
        return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
            format!("File not found: {}", filepath)
        ));
    }

    let content = fs::read_to_string(path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(
            format!("Failed to read {}: {}", filepath, e)
        )
    })?;

    let mut results = Vec::new();
    let search_pattern = if case_sensitive {
        pattern.clone()
    } else {
        pattern.to_lowercase()
    };

    for (line_num, line) in content.lines().enumerate() {
        let search_line = if case_sensitive {
            line.to_string()
        } else {
            line.to_lowercase()
        };

        if search_line.contains(&search_pattern) {
            results.push((line_num + 1, line.to_string()));
        }
    }

    Ok(results)
}

/// Search for a pattern in multiple files
///
/// # Arguments
/// * `pattern` - The search pattern
/// * `filepaths` - List of file paths to search
/// * `case_sensitive` - Whether to perform case-sensitive search
///
/// # Returns
/// Dictionary mapping filepath to list of (line_number, line_content) tuples
#[pyfunction]
fn search_files(
    pattern: String,
    filepaths: Vec<String>,
    case_sensitive: bool,
) -> PyResult<Vec<(String, Vec<(usize, String)>)>> {
    let mut all_results = Vec::new();

    for filepath in filepaths {
        match search_file(pattern.clone(), filepath.clone(), case_sensitive) {
            Ok(results) => {
                if !results.is_empty() {
                    all_results.push((filepath, results));
                }
            }
            Err(_) => {
                // Skip files that can't be read
                continue;
            }
        }
    }

    Ok(all_results)
}

/// Count lines in a file
#[pyfunction]
fn count_lines(filepath: String) -> PyResult<usize> {
    let content = fs::read_to_string(&filepath).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(
            format!("Failed to read {}: {}", filepath, e)
        )
    })?;

    Ok(content.lines().count())
}

/// Get file statistics (lines, words, bytes)
#[pyfunction]
fn file_stats(filepath: String) -> PyResult<(usize, usize, usize)> {
    let content = fs::read_to_string(&filepath).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(
            format!("Failed to read {}: {}", filepath, e)
        )
    })?;

    let lines = content.lines().count();
    let words = content.split_whitespace().count();
    let bytes = content.len();

    Ok((lines, words, bytes))
}

#[pymodule]
fn argparse_basic(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(search_file, m)?)?;
    m.add_function(wrap_pyfunction!(search_files, m)?)?;
    m.add_function(wrap_pyfunction!(count_lines, m)?)?;
    m.add_function(wrap_pyfunction!(file_stats, m)?)?;
    Ok(())
}
