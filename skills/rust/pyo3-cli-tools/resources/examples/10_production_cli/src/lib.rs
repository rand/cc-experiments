use pyo3::prelude::*;
use pyo3::types::PyDict;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::sync::{Arc, Mutex};
use walkdir::WalkDir;

/// Production CLI tool configuration
#[pyclass]
#[derive(Clone, Serialize, Deserialize)]
pub struct CliConfig {
    #[pyo3(get, set)]
    pub verbose: bool,
    #[pyo3(get, set)]
    pub threads: usize,
    #[pyo3(get, set)]
    pub output_format: String,
    #[pyo3(get, set)]
    pub color: bool,
}

#[pymethods]
impl CliConfig {
    #[new]
    fn new() -> Self {
        CliConfig {
            verbose: false,
            threads: num_cpus::get(),
            output_format: "text".to_string(),
            color: true,
        }
    }

    fn load(&mut self, filepath: String) -> PyResult<()> {
        let content = fs::read_to_string(&filepath)?;
        let loaded: CliConfig = toml::from_str(&content).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid config: {}", e))
        })?;

        self.verbose = loaded.verbose;
        self.threads = loaded.threads;
        self.output_format = loaded.output_format;
        self.color = loaded.color;

        Ok(())
    }

    fn save(&self, filepath: String) -> PyResult<()> {
        let content = toml::to_string_pretty(self).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{}", e))
        })?;
        fs::write(&filepath, content)?;
        Ok(())
    }
}

/// File analysis result
#[pyclass]
#[derive(Clone)]
pub struct FileAnalysis {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub lines: usize,
    #[pyo3(get)]
    pub words: usize,
    #[pyo3(get)]
    pub bytes: usize,
    #[pyo3(get)]
    pub file_type: String,
}

#[pymethods]
impl FileAnalysis {
    fn __repr__(&self) -> String {
        format!(
            "FileAnalysis(path='{}', lines={}, words={}, bytes={})",
            self.path, self.lines, self.words, self.bytes
        )
    }
}

/// Production file processor
#[pyclass]
pub struct FileProcessor {
    config: Arc<CliConfig>,
    progress: Arc<Mutex<usize>>,
}

#[pymethods]
impl FileProcessor {
    #[new]
    fn new(config: CliConfig) -> Self {
        FileProcessor {
            config: Arc::new(config),
            progress: Arc::new(Mutex::new(0)),
        }
    }

    fn analyze_directory(
        &self,
        py: Python,
        directory: String,
        extensions: Option<Vec<String>>,
        callback: Option<PyObject>,
    ) -> PyResult<Vec<FileAnalysis>> {
        let config = Arc::clone(&self.config);
        let progress = Arc::clone(&self.progress);

        py.allow_threads(|| {
            let walker = WalkDir::new(&directory).into_iter().filter_map(|e| e.ok());

            let files: Vec<_> = walker
                .filter(|e| e.file_type().is_file())
                .filter(|e| {
                    if let Some(ref exts) = extensions {
                        if let Some(ext) = e.path().extension() {
                            if let Some(ext_str) = ext.to_str() {
                                return exts.contains(&ext_str.to_string());
                            }
                        }
                        false
                    } else {
                        true
                    }
                })
                .collect();

            let results: Vec<FileAnalysis> = files
                .par_iter()
                .filter_map(|entry| {
                    let path = entry.path();
                    let path_str = path.to_string_lossy().to_string();

                    let content = fs::read_to_string(path).ok()?;

                    let lines = content.lines().count();
                    let words = content.split_whitespace().count();
                    let bytes = content.len();

                    let file_type = path
                        .extension()
                        .and_then(|e| e.to_str())
                        .unwrap_or("unknown")
                        .to_string();

                    // Update progress
                    {
                        let mut prog = progress.lock().unwrap();
                        *prog += 1;

                        // Call progress callback if provided
                        if let Some(ref cb) = callback {
                            Python::with_gil(|py| {
                                let _ = cb.call1(py, (*prog, files.len()));
                            });
                        }
                    }

                    Some(FileAnalysis {
                        path: path_str,
                        lines,
                        words,
                        bytes,
                        file_type,
                    })
                })
                .collect();

            results
        })
    }

    fn search_content(
        &self,
        py: Python,
        directory: String,
        pattern: String,
        case_sensitive: bool,
    ) -> PyResult<Vec<(String, Vec<(usize, String)>)>> {
        py.allow_threads(|| {
            let walker = WalkDir::new(&directory).into_iter().filter_map(|e| e.ok());

            let files: Vec<_> = walker.filter(|e| e.file_type().is_file()).collect();

            let search_pattern = if case_sensitive {
                pattern.clone()
            } else {
                pattern.to_lowercase()
            };

            let results: Vec<(String, Vec<(usize, String)>)> = files
                .par_iter()
                .filter_map(|entry| {
                    let path = entry.path();
                    let content = fs::read_to_string(path).ok()?;

                    let mut matches = Vec::new();

                    for (line_num, line) in content.lines().enumerate() {
                        let search_line = if case_sensitive {
                            line.to_string()
                        } else {
                            line.to_lowercase()
                        };

                        if search_line.contains(&search_pattern) {
                            matches.push((line_num + 1, line.to_string()));
                        }
                    }

                    if !matches.is_empty() {
                        Some((path.to_string_lossy().to_string(), matches))
                    } else {
                        None
                    }
                })
                .collect();

            results
        })
    }

    fn generate_report(&self, analyses: Vec<FileAnalysis>) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);

            let total_files = analyses.len();
            let total_lines: usize = analyses.iter().map(|a| a.lines).sum();
            let total_words: usize = analyses.iter().map(|a| a.words).sum();
            let total_bytes: usize = analyses.iter().map(|a| a.bytes).sum();

            dict.set_item("total_files", total_files)?;
            dict.set_item("total_lines", total_lines)?;
            dict.set_item("total_words", total_words)?;
            dict.set_item("total_bytes", total_bytes)?;

            // Group by file type
            let mut by_type: std::collections::HashMap<String, usize> =
                std::collections::HashMap::new();

            for analysis in &analyses {
                *by_type.entry(analysis.file_type.clone()).or_insert(0) += 1;
            }

            let type_dict = PyDict::new(py);
            for (ftype, count) in by_type {
                type_dict.set_item(ftype, count)?;
            }

            dict.set_item("by_type", type_dict)?;

            Ok(dict.into())
        })
    }
}

#[pymodule]
fn production_cli(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<CliConfig>()?;
    m.add_class::<FileAnalysis>()?;
    m.add_class::<FileProcessor>()?;
    Ok(())
}
