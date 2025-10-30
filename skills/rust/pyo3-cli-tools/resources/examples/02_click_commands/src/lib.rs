use pyo3::prelude::*;
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

/// List files in a directory with filtering options
///
/// # Arguments
/// * `directory` - Directory path to scan
/// * `recursive` - Whether to scan recursively
/// * `extensions` - Optional list of file extensions to filter (e.g., ["rs", "py"])
///
/// # Returns
/// Vector of file paths matching the criteria
#[pyfunction]
fn list_files(
    directory: String,
    recursive: bool,
    extensions: Option<Vec<String>>,
) -> PyResult<Vec<String>> {
    let path = Path::new(&directory);

    if !path.exists() {
        return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
            format!("Directory not found: {}", directory)
        ));
    }

    if !path.is_dir() {
        return Err(PyErr::new::<pyo3::exceptions::PyNotADirectoryError, _>(
            format!("Not a directory: {}", directory)
        ));
    }

    let walker = if recursive {
        WalkDir::new(path)
    } else {
        WalkDir::new(path).max_depth(1)
    };

    let mut files = Vec::new();

    for entry in walker.into_iter().filter_map(|e| e.ok()) {
        if entry.file_type().is_file() {
            let path = entry.path();

            // Filter by extension if provided
            if let Some(ref exts) = extensions {
                if let Some(ext) = path.extension() {
                    if let Some(ext_str) = ext.to_str() {
                        if !exts.contains(&ext_str.to_string()) {
                            continue;
                        }
                    }
                } else {
                    continue;
                }
            }

            files.push(path.to_string_lossy().to_string());
        }
    }

    Ok(files)
}

/// Copy files from source to destination directory
///
/// # Arguments
/// * `source_files` - List of source file paths
/// * `dest_dir` - Destination directory
/// * `overwrite` - Whether to overwrite existing files
///
/// # Returns
/// Number of files successfully copied
#[pyfunction]
fn copy_files(
    source_files: Vec<String>,
    dest_dir: String,
    overwrite: bool,
) -> PyResult<usize> {
    let dest_path = Path::new(&dest_dir);

    if !dest_path.exists() {
        fs::create_dir_all(dest_path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(
                format!("Failed to create directory {}: {}", dest_dir, e)
            )
        })?;
    }

    let mut copied = 0;

    for source in source_files {
        let source_path = Path::new(&source);

        if !source_path.exists() {
            continue; // Skip missing files
        }

        let filename = source_path.file_name().ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid filename: {}", source)
            )
        })?;

        let dest_file = dest_path.join(filename);

        if dest_file.exists() && !overwrite {
            continue; // Skip existing files if not overwriting
        }

        fs::copy(source_path, &dest_file).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(
                format!("Failed to copy {}: {}", source, e)
            )
        })?;

        copied += 1;
    }

    Ok(copied)
}

/// Delete files matching a pattern
///
/// # Arguments
/// * `directory` - Directory to search
/// * `pattern` - Glob pattern (e.g., "*.tmp")
/// * `dry_run` - If true, only list files without deleting
///
/// # Returns
/// (files_found, files_deleted) tuple
#[pyfunction]
fn delete_files(
    directory: String,
    pattern: String,
    dry_run: bool,
) -> PyResult<(usize, usize)> {
    let path = Path::new(&directory);

    if !path.exists() {
        return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
            format!("Directory not found: {}", directory)
        ));
    }

    let mut found = 0;
    let mut deleted = 0;

    for entry in WalkDir::new(path).into_iter().filter_map(|e| e.ok()) {
        if entry.file_type().is_file() {
            let file_path = entry.path();

            // Simple pattern matching (ends with)
            if let Some(filename) = file_path.file_name() {
                if let Some(name_str) = filename.to_str() {
                    // Handle wildcard patterns
                    let matches = if pattern.starts_with('*') {
                        let suffix = pattern.trim_start_matches('*');
                        name_str.ends_with(suffix)
                    } else {
                        name_str == pattern
                    };

                    if matches {
                        found += 1;

                        if !dry_run {
                            if fs::remove_file(file_path).is_ok() {
                                deleted += 1;
                            }
                        }
                    }
                }
            }
        }
    }

    Ok((found, deleted))
}

/// Get directory statistics
///
/// # Returns
/// (total_files, total_dirs, total_size) tuple
#[pyfunction]
fn directory_stats(directory: String) -> PyResult<(usize, usize, u64)> {
    let path = Path::new(&directory);

    if !path.exists() {
        return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
            format!("Directory not found: {}", directory)
        ));
    }

    let mut files = 0;
    let mut dirs = 0;
    let mut size = 0u64;

    for entry in WalkDir::new(path).into_iter().filter_map(|e| e.ok()) {
        if entry.file_type().is_file() {
            files += 1;
            if let Ok(metadata) = entry.metadata() {
                size += metadata.len();
            }
        } else if entry.file_type().is_dir() {
            dirs += 1;
        }
    }

    Ok((files, dirs, size))
}

#[pymodule]
fn click_commands(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(list_files, m)?)?;
    m.add_function(wrap_pyfunction!(copy_files, m)?)?;
    m.add_function(wrap_pyfunction!(delete_files, m)?)?;
    m.add_function(wrap_pyfunction!(directory_stats, m)?)?;
    Ok(())
}
