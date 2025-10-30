# PyO3 CLI Tools Integration - Complete Reference

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Skill**: rust-pyo3-cli-tools

This is a comprehensive reference for integrating PyO3 with Python CLI tools. It covers argument parsing, terminal output, progress indicators, file processing, configuration management, interactive input, terminal UI, command execution, shell completion, and production patterns.

---

## Table of Contents

1. [Argument Parsing](#1-argument-parsing)
2. [Terminal Output](#2-terminal-output)
3. [Progress Indicators](#3-progress-indicators)
4. [File Processing](#4-file-processing)
5. [Configuration Management](#5-configuration-management)
6. [Interactive Input](#6-interactive-input)
7. [Terminal UI](#7-terminal-ui)
8. [Command Execution](#8-command-execution)
9. [Shell Completion](#9-shell-completion)
10. [Production Patterns](#10-production-patterns)

---

## 1. Argument Parsing

### 1.1 Setup

```toml
# Cargo.toml
[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
clap = { version = "4", features = ["derive"] }
serde = { version = "1.0", features = ["derive"] }
```

### 1.2 Basic Argument Parsing

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;

#[pyclass]
struct ArgumentParser {
    arguments: HashMap<String, ArgDefinition>,
}

#[pyclass]
#[derive(Clone)]
struct ArgDefinition {
    #[pyo3(get, set)]
    name: String,
    #[pyo3(get, set)]
    arg_type: String,
    #[pyo3(get, set)]
    required: bool,
    #[pyo3(get, set)]
    default: Option<String>,
    #[pyo3(get, set)]
    help: String,
}

#[pymethods]
impl ArgDefinition {
    #[new]
    fn new(name: String, arg_type: String, required: bool, default: Option<String>, help: String) -> Self {
        ArgDefinition {
            name,
            arg_type,
            required,
            default,
            help,
        }
    }
}

#[pymethods]
impl ArgumentParser {
    #[new]
    fn new() -> Self {
        ArgumentParser {
            arguments: HashMap::new(),
        }
    }

    fn add_argument(&mut self, arg: ArgDefinition) {
        self.arguments.insert(arg.name.clone(), arg);
    }

    fn parse(&self, args: Vec<String>) -> PyResult<HashMap<String, String>> {
        let mut result = HashMap::new();
        let mut i = 0;

        while i < args.len() {
            let arg = &args[i];

            if arg.starts_with("--") {
                let key = arg.trim_start_matches("--");

                if let Some(def) = self.arguments.get(key) {
                    if def.arg_type == "flag" {
                        result.insert(key.to_string(), "true".to_string());
                    } else if i + 1 < args.len() {
                        result.insert(key.to_string(), args[i + 1].clone());
                        i += 1;
                    }
                }
            }

            i += 1;
        }

        // Apply defaults
        for (name, def) in &self.arguments {
            if !result.contains_key(name) {
                if def.required {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Required argument '{}' not provided", name)
                    ));
                } else if let Some(ref default) = def.default {
                    result.insert(name.clone(), default.clone());
                }
            }
        }

        Ok(result)
    }

    fn generate_help(&self) -> String {
        let mut help = String::from("Usage:\n");

        for (name, def) in &self.arguments {
            let required = if def.required { "(required)" } else { "(optional)" };
            help.push_str(&format!("  --{} {} - {}\n", name, required, def.help));
        }

        help
    }
}
```

### 1.3 Positional Arguments

```rust
#[pyfunction]
fn parse_positional_args(args: Vec<String>, expected_count: usize) -> PyResult<Vec<String>> {
    let positional: Vec<String> = args.iter()
        .filter(|arg| !arg.starts_with('-'))
        .cloned()
        .collect();

    if positional.len() != expected_count {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Expected {} positional arguments, got {}", expected_count, positional.len())
        ));
    }

    Ok(positional)
}
```

### 1.4 argparse Integration

```rust
#[pyfunction]
fn validate_argparse_args(py: Python, parser: &PyAny, args: Vec<String>) -> PyResult<bool> {
    // Convert Rust args to Python list
    let py_args = PyList::new(py, &args);

    // Call parser.parse_args()
    match parser.call_method1("parse_args", (py_args,)) {
        Ok(_) => Ok(true),
        Err(e) => {
            eprintln!("Parse error: {}", e);
            Ok(false)
        }
    }
}

#[pyfunction]
fn extract_parsed_args(py: Python, namespace: &PyAny) -> PyResult<HashMap<String, String>> {
    let dict = namespace.call_method0("__dict__")?;
    let mut result = HashMap::new();

    for item in dict.call_method0("items")?.iter()? {
        let (key, value): (&str, &PyAny) = item?.extract()?;
        result.insert(key.to_string(), value.to_string());
    }

    Ok(result)
}
```

### 1.5 Click Integration

```rust
#[pyclass]
struct ClickCommand {
    #[pyo3(get, set)]
    name: String,
    options: Vec<ClickOption>,
}

#[pyclass]
#[derive(Clone)]
struct ClickOption {
    #[pyo3(get, set)]
    name: String,
    #[pyo3(get, set)]
    option_type: String,
    #[pyo3(get, set)]
    default: Option<String>,
    #[pyo3(get, set)]
    help: String,
}

#[pymethods]
impl ClickOption {
    #[new]
    fn new(name: String, option_type: String, default: Option<String>, help: String) -> Self {
        ClickOption {
            name,
            option_type,
            default,
            help,
        }
    }

    fn to_decorator(&self) -> String {
        let type_str = match self.option_type.as_str() {
            "int" => "type=int",
            "float" => "type=float",
            "bool" => "is_flag=True",
            _ => "type=str",
        };

        let default_str = if let Some(ref d) = self.default {
            format!(", default='{}'", d)
        } else {
            String::new()
        };

        format!(
            "@click.option('--{}', {}, help='{}'{})",
            self.name, type_str, self.help, default_str
        )
    }
}

#[pymethods]
impl ClickCommand {
    #[new]
    fn new(name: String) -> Self {
        ClickCommand {
            name,
            options: Vec::new(),
        }
    }

    fn add_option(&mut self, option: ClickOption) {
        self.options.push(option);
    }

    fn generate_function(&self) -> String {
        let mut code = String::new();

        // Add decorators
        for option in &self.options {
            code.push_str(&option.to_decorator());
            code.push('\n');
        }

        // Add function definition
        code.push_str(&format!("def {}(", self.name));
        code.push_str(&self.options.iter()
            .map(|o| o.name.clone())
            .collect::<Vec<_>>()
            .join(", "));
        code.push_str("):\n");
        code.push_str("    pass\n");

        code
    }
}
```

---

## 2. Terminal Output

### 2.1 Colored Output

```rust
use std::fmt;

#[derive(Clone, Copy)]
enum Color {
    Black,
    Red,
    Green,
    Yellow,
    Blue,
    Magenta,
    Cyan,
    White,
}

impl Color {
    fn code(&self) -> u8 {
        match self {
            Color::Black => 30,
            Color::Red => 31,
            Color::Green => 32,
            Color::Yellow => 33,
            Color::Blue => 34,
            Color::Magenta => 35,
            Color::Cyan => 36,
            Color::White => 37,
        }
    }
}

#[pyfunction]
fn colorize(text: String, color: &str, bold: bool) -> String {
    let color_enum = match color.to_lowercase().as_str() {
        "red" => Color::Red,
        "green" => Color::Green,
        "yellow" => Color::Yellow,
        "blue" => Color::Blue,
        "magenta" => Color::Magenta,
        "cyan" => Color::Cyan,
        "white" => Color::White,
        _ => Color::White,
    };

    let bold_code = if bold { "1;" } else { "" };

    format!("\x1b[{}{}m{}\x1b[0m", bold_code, color_enum.code(), text)
}

#[pyfunction]
fn print_error(message: String) -> String {
    colorize(format!("ERROR: {}", message), "red", true)
}

#[pyfunction]
fn print_success(message: String) -> String {
    colorize(format!("SUCCESS: {}", message), "green", true)
}

#[pyfunction]
fn print_warning(message: String) -> String {
    colorize(format!("WARNING: {}", message), "yellow", true)
}

#[pyfunction]
fn print_info(message: String) -> String {
    colorize(format!("INFO: {}", message), "blue", false)
}
```

### 2.2 Table Formatting

```rust
#[pyclass]
struct TableFormatter {
    headers: Vec<String>,
    rows: Vec<Vec<String>>,
    column_widths: Vec<usize>,
}

#[pymethods]
impl TableFormatter {
    #[new]
    fn new(headers: Vec<String>) -> Self {
        let column_widths = headers.iter().map(|h| h.len()).collect();

        TableFormatter {
            headers,
            rows: Vec::new(),
            column_widths,
        }
    }

    fn add_row(&mut self, row: Vec<String>) -> PyResult<()> {
        if row.len() != self.headers.len() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Row has {} columns, expected {}", row.len(), self.headers.len())
            ));
        }

        // Update column widths
        for (i, cell) in row.iter().enumerate() {
            self.column_widths[i] = self.column_widths[i].max(cell.len());
        }

        self.rows.push(row);
        Ok(())
    }

    fn render(&self) -> String {
        let mut output = String::new();

        // Render separator
        let separator = self.render_separator();

        // Render header
        output.push_str(&separator);
        output.push_str(&self.render_row(&self.headers));
        output.push_str(&separator);

        // Render rows
        for row in &self.rows {
            output.push_str(&self.render_row(row));
        }

        output.push_str(&separator);

        output
    }

    fn render_markdown(&self) -> String {
        let mut output = String::new();

        // Render header
        output.push('|');
        for (i, header) in self.headers.iter().enumerate() {
            output.push_str(&format!(" {} |", self.pad(header, self.column_widths[i])));
        }
        output.push('\n');

        // Render separator
        output.push('|');
        for width in &self.column_widths {
            output.push_str(&format!(" {} |", "-".repeat(*width)));
        }
        output.push('\n');

        // Render rows
        for row in &self.rows {
            output.push('|');
            for (i, cell) in row.iter().enumerate() {
                output.push_str(&format!(" {} |", self.pad(cell, self.column_widths[i])));
            }
            output.push('\n');
        }

        output
    }
}

impl TableFormatter {
    fn render_separator(&self) -> String {
        let mut sep = String::from("+");

        for width in &self.column_widths {
            sep.push_str(&"-".repeat(width + 2));
            sep.push('+');
        }

        sep.push('\n');
        sep
    }

    fn render_row(&self, cells: &[String]) -> String {
        let mut row = String::from("|");

        for (i, cell) in cells.iter().enumerate() {
            row.push_str(&format!(" {} |", self.pad(cell, self.column_widths[i])));
        }

        row.push('\n');
        row
    }

    fn pad(&self, text: &str, width: usize) -> String {
        format!("{:width$}", text, width = width)
    }
}
```

### 2.3 Pretty Printing

```rust
#[pyfunction]
fn pretty_print_dict(data: HashMap<String, String>, indent: usize) -> String {
    let indent_str = " ".repeat(indent);
    let mut output = String::from("{\n");

    let max_key_len = data.keys().map(|k| k.len()).max().unwrap_or(0);

    for (key, value) in &data {
        let padded_key = format!("{:width$}", key, width = max_key_len);
        output.push_str(&format!("{}{}: {}\n", indent_str, padded_key, value));
    }

    output.push('}');
    output
}

#[pyfunction]
fn format_bytes(bytes: u64) -> String {
    const UNITS: &[&str] = &["B", "KB", "MB", "GB", "TB"];
    let mut size = bytes as f64;
    let mut unit_idx = 0;

    while size >= 1024.0 && unit_idx < UNITS.len() - 1 {
        size /= 1024.0;
        unit_idx += 1;
    }

    format!("{:.2} {}", size, UNITS[unit_idx])
}

#[pyfunction]
fn format_duration(seconds: f64) -> String {
    if seconds < 1.0 {
        format!("{:.0}ms", seconds * 1000.0)
    } else if seconds < 60.0 {
        format!("{:.1}s", seconds)
    } else if seconds < 3600.0 {
        let mins = (seconds / 60.0).floor();
        let secs = seconds % 60.0;
        format!("{}m{:.0}s", mins, secs)
    } else {
        let hours = (seconds / 3600.0).floor();
        let mins = ((seconds % 3600.0) / 60.0).floor();
        format!("{}h{}m", hours, mins)
    }
}
```

---

## 3. Progress Indicators

### 3.1 Progress Bar

```rust
use std::time::{Duration, Instant};

#[pyclass]
struct ProgressBar {
    #[pyo3(get)]
    total: usize,
    current: usize,
    start_time: Instant,
    width: usize,
}

#[pymethods]
impl ProgressBar {
    #[new]
    fn new(total: usize, width: Option<usize>) -> Self {
        ProgressBar {
            total,
            current: 0,
            start_time: Instant::now(),
            width: width.unwrap_or(50),
        }
    }

    fn update(&mut self, amount: usize) {
        self.current += amount;
        if self.current > self.total {
            self.current = self.total;
        }
    }

    fn set_progress(&mut self, current: usize) {
        self.current = current.min(self.total);
    }

    fn render(&self) -> String {
        let percent = if self.total > 0 {
            (self.current as f64 / self.total as f64) * 100.0
        } else {
            0.0
        };

        let filled = ((self.current as f64 / self.total as f64) * self.width as f64) as usize;
        let empty = self.width - filled;

        let elapsed = self.start_time.elapsed().as_secs_f64();
        let eta = if self.current > 0 {
            let rate = self.current as f64 / elapsed;
            let remaining = self.total - self.current;
            remaining as f64 / rate
        } else {
            0.0
        };

        format!(
            "[{}{}] {:.1}% ({}/{}) ETA: {}",
            "=".repeat(filled),
            " ".repeat(empty),
            percent,
            self.current,
            self.total,
            format_duration(eta)
        )
    }

    fn is_complete(&self) -> bool {
        self.current >= self.total
    }

    fn percentage(&self) -> f64 {
        if self.total > 0 {
            (self.current as f64 / self.total as f64) * 100.0
        } else {
            0.0
        }
    }

    fn reset(&mut self) {
        self.current = 0;
        self.start_time = Instant::now();
    }
}
```

### 3.2 Spinner

```rust
#[pyclass]
struct Spinner {
    frames: Vec<String>,
    current_frame: usize,
    message: String,
}

#[pymethods]
impl Spinner {
    #[new]
    fn new(message: String) -> Self {
        Spinner {
            frames: vec![
                "⠋".to_string(),
                "⠙".to_string(),
                "⠹".to_string(),
                "⠸".to_string(),
                "⠼".to_string(),
                "⠴".to_string(),
                "⠦".to_string(),
                "⠧".to_string(),
                "⠇".to_string(),
                "⠏".to_string(),
            ],
            current_frame: 0,
            message,
        }
    }

    fn next_frame(&mut self) -> String {
        let frame = format!("{} {}", self.frames[self.current_frame], self.message);
        self.current_frame = (self.current_frame + 1) % self.frames.len();
        frame
    }

    fn set_message(&mut self, message: String) {
        self.message = message;
    }

    fn render(&self) -> String {
        format!("{} {}", self.frames[self.current_frame], self.message)
    }
}
```

### 3.3 Multi-Progress

```rust
use std::collections::HashMap;

#[pyclass]
struct MultiProgress {
    bars: HashMap<String, ProgressBar>,
}

#[pymethods]
impl MultiProgress {
    #[new]
    fn new() -> Self {
        MultiProgress {
            bars: HashMap::new(),
        }
    }

    fn add_bar(&mut self, name: String, total: usize) {
        self.bars.insert(name, ProgressBar::new(total, Some(40)));
    }

    fn update_bar(&mut self, name: String, amount: usize) -> PyResult<()> {
        if let Some(bar) = self.bars.get_mut(&name) {
            bar.update(amount);
            Ok(())
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(
                format!("Progress bar '{}' not found", name)
            ))
        }
    }

    fn render_all(&self) -> String {
        let mut output = String::new();

        for (name, bar) in &self.bars {
            output.push_str(&format!("{}: {}\n", name, bar.render()));
        }

        output
    }

    fn is_all_complete(&self) -> bool {
        self.bars.values().all(|bar| bar.is_complete())
    }

    fn remove_bar(&mut self, name: String) -> bool {
        self.bars.remove(&name).is_some()
    }
}
```

---

## 4. File Processing

### 4.1 File I/O

```rust
use std::fs::{self, File};
use std::io::{BufRead, BufReader, Write};
use std::path::Path;

#[pyfunction]
fn read_lines_fast(path: String) -> PyResult<Vec<String>> {
    let file = File::open(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let reader = BufReader::new(file);
    let lines: Result<Vec<String>, _> = reader.lines().collect();

    lines.map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
}

#[pyfunction]
fn write_lines_fast(path: String, lines: Vec<String>) -> PyResult<()> {
    let mut file = File::create(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    for line in lines {
        writeln!(file, "{}", line)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    }

    Ok(())
}

#[pyfunction]
fn count_lines(path: String) -> PyResult<usize> {
    let file = File::open(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let reader = BufReader::new(file);
    Ok(reader.lines().count())
}

#[pyfunction]
fn grep_file(path: String, pattern: String) -> PyResult<Vec<String>> {
    let file = File::open(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let reader = BufReader::new(file);
    let mut matches = Vec::new();

    for line in reader.lines() {
        let line = line.map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        if line.contains(&pattern) {
            matches.push(line);
        }
    }

    Ok(matches)
}
```

### 4.2 Directory Traversal

```rust
use walkdir::WalkDir;

#[pyfunction]
fn walk_directory(path: String, max_depth: Option<usize>) -> PyResult<Vec<String>> {
    let mut walker = WalkDir::new(&path);

    if let Some(depth) = max_depth {
        walker = walker.max_depth(depth);
    }

    let paths: Vec<String> = walker
        .into_iter()
        .filter_map(|e| e.ok())
        .map(|e| e.path().to_string_lossy().to_string())
        .collect();

    Ok(paths)
}

#[pyfunction]
fn find_files_by_extension(path: String, extension: String) -> PyResult<Vec<String>> {
    let files: Vec<String> = WalkDir::new(&path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().is_file())
        .filter(|e| {
            e.path()
                .extension()
                .and_then(|s| s.to_str())
                .map(|s| s == extension)
                .unwrap_or(false)
        })
        .map(|e| e.path().to_string_lossy().to_string())
        .collect();

    Ok(files)
}

#[pyfunction]
fn get_directory_size(path: String) -> PyResult<u64> {
    let mut total_size = 0u64;

    for entry in WalkDir::new(&path).into_iter().filter_map(|e| e.ok()) {
        if entry.path().is_file() {
            if let Ok(metadata) = entry.metadata() {
                total_size += metadata.len();
            }
        }
    }

    Ok(total_size)
}
```

### 4.3 Parallel File Processing

```rust
use rayon::prelude::*;

#[pyfunction]
fn process_files_parallel(
    py: Python,
    paths: Vec<String>,
    processor: PyObject
) -> PyResult<Vec<PyObject>> {
    py.allow_threads(|| {
        let results: Vec<PyObject> = paths
            .par_iter()
            .map(|path| {
                Python::with_gil(|py| {
                    processor.call1(py, (path,)).unwrap_or_else(|_| py.None())
                })
            })
            .collect();

        Ok(results)
    })
}

#[pyfunction]
fn count_lines_parallel(paths: Vec<String>) -> PyResult<HashMap<String, usize>> {
    use std::sync::{Arc, Mutex};

    let results = Arc::new(Mutex::new(HashMap::new()));

    paths.par_iter().for_each(|path| {
        if let Ok(count) = count_lines(path.clone()) {
            results.lock().unwrap().insert(path.clone(), count);
        }
    });

    let results = Arc::try_unwrap(results).unwrap().into_inner().unwrap();
    Ok(results)
}
```

### 4.4 File Watching

```rust
use std::sync::mpsc::{channel, Receiver};
use std::thread;

#[pyclass]
struct FileWatcher {
    path: String,
}

#[pymethods]
impl FileWatcher {
    #[new]
    fn new(path: String) -> Self {
        FileWatcher { path }
    }

    fn watch(&self, py: Python, callback: PyObject) -> PyResult<()> {
        let path = self.path.clone();

        thread::spawn(move || {
            use std::time::Duration;

            let mut last_modified = None;

            loop {
                if let Ok(metadata) = fs::metadata(&path) {
                    if let Ok(modified) = metadata.modified() {
                        if last_modified.is_none() || last_modified.unwrap() != modified {
                            last_modified = Some(modified);

                            Python::with_gil(|py| {
                                let _ = callback.call1(py, (&path,));
                            });
                        }
                    }
                }

                thread::sleep(Duration::from_secs(1));
            }
        });

        Ok(())
    }
}
```

---

## 5. Configuration Management

### 5.1 TOML Configuration

```rust
use toml;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct Config {
    app_name: String,
    version: String,
    settings: HashMap<String, String>,
}

#[pyfunction]
fn load_toml_config(path: String) -> PyResult<HashMap<String, String>> {
    let content = fs::read_to_string(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let config: Config = toml::from_str(&content)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    let mut result = HashMap::new();
    result.insert("app_name".to_string(), config.app_name);
    result.insert("version".to_string(), config.version);

    for (key, value) in config.settings {
        result.insert(key, value);
    }

    Ok(result)
}

#[pyfunction]
fn save_toml_config(path: String, config: HashMap<String, String>) -> PyResult<()> {
    let app_name = config.get("app_name").cloned().unwrap_or_default();
    let version = config.get("version").cloned().unwrap_or_default();

    let mut settings = HashMap::new();
    for (key, value) in config {
        if key != "app_name" && key != "version" {
            settings.insert(key, value);
        }
    }

    let config_struct = Config {
        app_name,
        version,
        settings,
    };

    let toml_string = toml::to_string_pretty(&config_struct)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    fs::write(&path, toml_string)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    Ok(())
}
```

### 5.2 YAML Configuration

```rust
use serde_yaml;

#[pyfunction]
fn load_yaml_config(path: String) -> PyResult<HashMap<String, serde_json::Value>> {
    let content = fs::read_to_string(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let config: HashMap<String, serde_json::Value> = serde_yaml::from_str(&content)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    Ok(config)
}

#[pyfunction]
fn save_yaml_config(path: String, config: HashMap<String, String>) -> PyResult<()> {
    let yaml_string = serde_yaml::to_string(&config)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    fs::write(&path, yaml_string)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    Ok(())
}
```

### 5.3 Environment Variables

```rust
use std::env;

#[pyfunction]
fn load_env_file(path: String) -> PyResult<HashMap<String, String>> {
    let content = fs::read_to_string(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let mut config = HashMap::new();

    for line in content.lines() {
        let line = line.trim();

        if line.is_empty() || line.starts_with('#') {
            continue;
        }

        if let Some((key, value)) = line.split_once('=') {
            let key = key.trim();
            let value = value.trim().trim_matches('"');
            config.insert(key.to_string(), value.to_string());
        }
    }

    Ok(config)
}

#[pyfunction]
fn get_env_var(key: String, default: Option<String>) -> String {
    env::var(&key).unwrap_or_else(|_| default.unwrap_or_default())
}

#[pyfunction]
fn set_env_vars(vars: HashMap<String, String>) {
    for (key, value) in vars {
        env::set_var(key, value);
    }
}
```

### 5.4 Configuration Validation

```rust
#[pyclass]
struct ConfigValidator {
    required_keys: Vec<String>,
    optional_keys: Vec<String>,
}

#[pymethods]
impl ConfigValidator {
    #[new]
    fn new(required_keys: Vec<String>, optional_keys: Vec<String>) -> Self {
        ConfigValidator {
            required_keys,
            optional_keys,
        }
    }

    fn validate(&self, config: HashMap<String, String>) -> PyResult<Vec<String>> {
        let mut errors = Vec::new();

        // Check required keys
        for key in &self.required_keys {
            if !config.contains_key(key) {
                errors.push(format!("Missing required key: {}", key));
            }
        }

        // Check for unexpected keys
        for key in config.keys() {
            if !self.required_keys.contains(key) && !self.optional_keys.contains(key) {
                errors.push(format!("Unexpected key: {}", key));
            }
        }

        Ok(errors)
    }

    fn is_valid(&self, config: HashMap<String, String>) -> bool {
        self.validate(config).unwrap_or_default().is_empty()
    }
}
```

---

## 6. Interactive Input

### 6.1 Prompts

```rust
use std::io::{self, Write};

#[pyfunction]
fn prompt(message: String) -> PyResult<String> {
    print!("{}: ", message);
    io::stdout().flush()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    Ok(input.trim().to_string())
}

#[pyfunction]
fn prompt_with_default(message: String, default: String) -> PyResult<String> {
    print!("{} [{}]: ", message, default);
    io::stdout().flush()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let input = input.trim();
    Ok(if input.is_empty() {
        default
    } else {
        input.to_string()
    })
}

#[pyfunction]
fn prompt_confirm(message: String) -> PyResult<bool> {
    print!("{} (y/n): ", message);
    io::stdout().flush()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let input = input.trim().to_lowercase();
    Ok(input == "y" || input == "yes")
}
```

### 6.2 Password Input

```rust
#[pyfunction]
fn prompt_password(message: String) -> PyResult<String> {
    use rpassword::read_password;

    print!("{}: ", message);
    io::stdout().flush()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    read_password()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
}

#[pyfunction]
fn validate_password(password: String, min_length: usize) -> Vec<String> {
    let mut errors = Vec::new();

    if password.len() < min_length {
        errors.push(format!("Password must be at least {} characters", min_length));
    }

    if !password.chars().any(|c| c.is_uppercase()) {
        errors.push("Password must contain at least one uppercase letter".to_string());
    }

    if !password.chars().any(|c| c.is_lowercase()) {
        errors.push("Password must contain at least one lowercase letter".to_string());
    }

    if !password.chars().any(|c| c.is_numeric()) {
        errors.push("Password must contain at least one number".to_string());
    }

    errors
}
```

### 6.3 Selection Menus

```rust
#[pyfunction]
fn prompt_select(message: String, options: Vec<String>) -> PyResult<String> {
    println!("{}", message);

    for (i, option) in options.iter().enumerate() {
        println!("  {}. {}", i + 1, option);
    }

    loop {
        print!("Select (1-{}): ", options.len());
        io::stdout().flush()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        let mut input = String::new();
        io::stdin().read_line(&mut input)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        if let Ok(choice) = input.trim().parse::<usize>() {
            if choice > 0 && choice <= options.len() {
                return Ok(options[choice - 1].clone());
            }
        }

        println!("Invalid selection. Please try again.");
    }
}

#[pyfunction]
fn prompt_multiselect(message: String, options: Vec<String>) -> PyResult<Vec<String>> {
    println!("{}", message);

    for (i, option) in options.iter().enumerate() {
        println!("  {}. {}", i + 1, option);
    }

    println!("Enter numbers separated by spaces (e.g., '1 3 4'):");

    print!("Select: ");
    io::stdout().flush()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let selections: Vec<String> = input
        .split_whitespace()
        .filter_map(|s| s.parse::<usize>().ok())
        .filter(|&i| i > 0 && i <= options.len())
        .map(|i| options[i - 1].clone())
        .collect();

    Ok(selections)
}
```

---

## 7. Terminal UI

### 7.1 Screen Management

```rust
#[pyfunction]
fn clear_screen() {
    print!("\x1b[2J\x1b[H");
    io::stdout().flush().unwrap();
}

#[pyfunction]
fn move_cursor(row: u16, col: u16) {
    print!("\x1b[{};{}H", row, col);
    io::stdout().flush().unwrap();
}

#[pyfunction]
fn hide_cursor() {
    print!("\x1b[?25l");
    io::stdout().flush().unwrap();
}

#[pyfunction]
fn show_cursor() {
    print!("\x1b[?25h");
    io::stdout().flush().unwrap();
}

#[pyfunction]
fn get_terminal_size() -> PyResult<(u16, u16)> {
    use terminal_size::{Width, Height, terminal_size};

    if let Some((Width(w), Height(h))) = terminal_size() {
        Ok((w, h))
    } else {
        Ok((80, 24)) // Default fallback
    }
}
```

### 7.2 Box Drawing

```rust
#[pyfunction]
fn draw_box(width: usize, height: usize, title: Option<String>) -> String {
    let mut output = String::new();

    // Top border
    output.push('┌');
    if let Some(ref t) = title {
        let title_len = t.len();
        let padding = (width - 2 - title_len) / 2;
        output.push_str(&"─".repeat(padding));
        output.push_str(&format!(" {} ", t));
        output.push_str(&"─".repeat(width - 2 - padding - title_len - 2));
    } else {
        output.push_str(&"─".repeat(width - 2));
    }
    output.push_str("┐\n");

    // Sides
    for _ in 0..height - 2 {
        output.push('│');
        output.push_str(&" ".repeat(width - 2));
        output.push_str("│\n");
    }

    // Bottom border
    output.push('└');
    output.push_str(&"─".repeat(width - 2));
    output.push('┘');

    output
}

#[pyfunction]
fn draw_border(content: Vec<String>) -> Vec<String> {
    if content.is_empty() {
        return vec![];
    }

    let max_width = content.iter().map(|s| s.len()).max().unwrap_or(0);
    let mut result = Vec::new();

    // Top border
    result.push(format!("┌{}┐", "─".repeat(max_width + 2)));

    // Content with sides
    for line in content {
        result.push(format!("│ {:width$} │", line, width = max_width));
    }

    // Bottom border
    result.push(format!("└{}┘", "─".repeat(max_width + 2)));

    result
}
```

### 7.3 Layout System

```rust
#[pyclass]
struct Panel {
    #[pyo3(get, set)]
    content: Vec<String>,
    #[pyo3(get, set)]
    width: usize,
    #[pyo3(get, set)]
    height: usize,
    #[pyo3(get, set)]
    title: Option<String>,
}

#[pymethods]
impl Panel {
    #[new]
    fn new(width: usize, height: usize, title: Option<String>) -> Self {
        Panel {
            content: Vec::new(),
            width,
            height,
            title,
        }
    }

    fn add_line(&mut self, line: String) {
        if self.content.len() < self.height - 2 {
            self.content.push(line);
        }
    }

    fn render(&self) -> String {
        let mut output = String::new();

        // Top border
        output.push_str("┌");
        if let Some(ref t) = self.title {
            output.push_str(&format!(" {} ", t));
            output.push_str(&"─".repeat(self.width - t.len() - 4));
        } else {
            output.push_str(&"─".repeat(self.width - 2));
        }
        output.push_str("┐\n");

        // Content
        for (i, line) in self.content.iter().enumerate() {
            if i < self.height - 2 {
                output.push_str(&format!("│ {:width$} │\n", line, width = self.width - 4));
            }
        }

        // Fill remaining space
        for _ in self.content.len()..self.height - 2 {
            output.push_str(&format!("│ {:width$} │\n", "", width = self.width - 4));
        }

        // Bottom border
        output.push_str("└");
        output.push_str(&"─".repeat(self.width - 2));
        output.push_str("┘");

        output
    }

    fn clear(&mut self) {
        self.content.clear();
    }
}
```

---

## 8. Command Execution

### 8.1 Process Spawning

```rust
use std::process::{Command, Stdio};

#[pyfunction]
fn run_command(command: String, args: Vec<String>) -> PyResult<(i32, String, String)> {
    let output = Command::new(&command)
        .args(&args)
        .output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyOSError, _>(e.to_string()))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    let exit_code = output.status.code().unwrap_or(-1);

    Ok((exit_code, stdout, stderr))
}

#[pyfunction]
fn run_command_stream(py: Python, command: String, args: Vec<String>, callback: PyObject) -> PyResult<i32> {
    use std::io::BufReader;

    let mut child = Command::new(&command)
        .args(&args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyOSError, _>(e.to_string()))?;

    if let Some(stdout) = child.stdout.take() {
        let reader = BufReader::new(stdout);

        for line in reader.lines() {
            if let Ok(line) = line {
                callback.call1(py, (line,))?;
            }
        }
    }

    let status = child.wait()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyOSError, _>(e.to_string()))?;

    Ok(status.code().unwrap_or(-1))
}
```

### 8.2 Pipeline Support

```rust
#[pyfunction]
fn run_pipeline(commands: Vec<(String, Vec<String>)>) -> PyResult<String> {
    use std::process::{Command, Stdio};

    if commands.is_empty() {
        return Ok(String::new());
    }

    let mut processes = Vec::new();

    for (i, (cmd, args)) in commands.iter().enumerate() {
        let stdin = if i == 0 {
            Stdio::inherit()
        } else {
            Stdio::from(processes[i - 1].stdout.take().unwrap())
        };

        let stdout = if i == commands.len() - 1 {
            Stdio::piped()
        } else {
            Stdio::piped()
        };

        let process = Command::new(cmd)
            .args(args)
            .stdin(stdin)
            .stdout(stdout)
            .spawn()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyOSError, _>(e.to_string()))?;

        processes.push(process);
    }

    let output = processes.last_mut().unwrap()
        .wait_with_output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyOSError, _>(e.to_string()))?;

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}
```

### 8.3 Signal Handling

```rust
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

#[pyclass]
struct SignalHandler {
    interrupted: Arc<AtomicBool>,
}

#[pymethods]
impl SignalHandler {
    #[new]
    fn new() -> Self {
        SignalHandler {
            interrupted: Arc::new(AtomicBool::new(false)),
        }
    }

    fn is_interrupted(&self) -> bool {
        self.interrupted.load(Ordering::Relaxed)
    }

    fn reset(&self) {
        self.interrupted.store(false, Ordering::Relaxed);
    }

    fn setup(&self) -> PyResult<()> {
        let interrupted = self.interrupted.clone();

        ctrlc::set_handler(move || {
            interrupted.store(true, Ordering::Relaxed);
        }).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        Ok(())
    }
}
```

---

## 9. Shell Completion

### 9.1 Bash Completion

```rust
#[pyfunction]
fn generate_bash_completion(command: String, subcommands: Vec<String>) -> String {
    let subcommand_list = subcommands.join(" ");

    format!(
        r#"_{}_completion() {{
    local cur prev opts
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    opts="{}"

    if [[ ${{cur}} == -* ]] ; then
        COMPREPLY=( $(compgen -W "--help --version" -- ${{cur}}) )
        return 0
    fi

    COMPREPLY=( $(compgen -W "${{opts}}" -- ${{cur}}) )
    return 0
}}

complete -F _{}_completion {}
"#,
        command, subcommand_list, command, command
    )
}
```

### 9.2 Zsh Completion

```rust
#[pyfunction]
fn generate_zsh_completion(command: String, subcommands: Vec<String>) -> String {
    let mut completion = format!("#compdef {}\n\n", command);
    completion.push_str("_arguments \\\n");
    completion.push_str("  '--help[Show help information]' \\\n");
    completion.push_str("  '--version[Show version information]' \\\n");

    if !subcommands.is_empty() {
        completion.push_str("  '1: :_values \"subcommand\"");
        for subcmd in subcommands {
            completion.push_str(&format!(" \"{}\"", subcmd));
        }
        completion.push_str("'\n");
    }

    completion
}
```

### 9.3 Fish Completion

```rust
#[pyfunction]
fn generate_fish_completion(command: String, subcommands: Vec<String>) -> String {
    let mut completion = String::new();

    completion.push_str(&format!("complete -c {} -f\n", command));
    completion.push_str(&format!("complete -c {} -l help -d 'Show help information'\n", command));
    completion.push_str(&format!("complete -c {} -l version -d 'Show version information'\n", command));

    for subcmd in subcommands {
        completion.push_str(&format!("complete -c {} -a '{}'\n", command, subcmd));
    }

    completion
}
```

---

## 10. Production Patterns

### 10.1 Error Handling

```rust
use std::fmt;

#[pyclass]
#[derive(Debug, Clone)]
struct CLIError {
    #[pyo3(get)]
    message: String,
    #[pyo3(get)]
    exit_code: i32,
}

#[pymethods]
impl CLIError {
    #[new]
    fn new(message: String, exit_code: Option<i32>) -> Self {
        CLIError {
            message,
            exit_code: exit_code.unwrap_or(1),
        }
    }

    fn __repr__(&self) -> String {
        format!("CLIError(message='{}', exit_code={})", self.message, self.exit_code)
    }

    fn __str__(&self) -> String {
        self.message.clone()
    }

    fn format_error(&self) -> String {
        colorize(format!("Error: {}", self.message), "red", true)
    }
}

#[pyfunction]
fn handle_error(error: CLIError) -> ! {
    eprintln!("{}", error.format_error());
    std::process::exit(error.exit_code);
}
```

### 10.2 Logging

```rust
use std::fs::OpenOptions;
use std::io::Write;

#[pyclass]
struct Logger {
    log_file: Option<String>,
    level: LogLevel,
}

#[derive(Clone, Copy, PartialEq, PartialOrd)]
enum LogLevel {
    Debug = 0,
    Info = 1,
    Warning = 2,
    Error = 3,
}

#[pymethods]
impl Logger {
    #[new]
    fn new(log_file: Option<String>, level: Option<String>) -> Self {
        let log_level = match level.as_deref() {
            Some("debug") => LogLevel::Debug,
            Some("info") => LogLevel::Info,
            Some("warning") => LogLevel::Warning,
            Some("error") => LogLevel::Error,
            _ => LogLevel::Info,
        };

        Logger {
            log_file,
            level: log_level,
        }
    }

    fn debug(&self, message: String) {
        self.log(LogLevel::Debug, message);
    }

    fn info(&self, message: String) {
        self.log(LogLevel::Info, message);
    }

    fn warning(&self, message: String) {
        self.log(LogLevel::Warning, message);
    }

    fn error(&self, message: String) {
        self.log(LogLevel::Error, message);
    }
}

impl Logger {
    fn log(&self, level: LogLevel, message: String) {
        if level < self.level {
            return;
        }

        let level_str = match level {
            LogLevel::Debug => "DEBUG",
            LogLevel::Info => "INFO",
            LogLevel::Warning => "WARN",
            LogLevel::Error => "ERROR",
        };

        let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S");
        let log_message = format!("[{}] {}: {}\n", timestamp, level_str, message);

        if let Some(ref path) = self.log_file {
            if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
                let _ = file.write_all(log_message.as_bytes());
            }
        } else {
            print!("{}", log_message);
        }
    }
}
```

### 10.3 Testing Utilities

```rust
#[pyfunction]
fn capture_stdout(py: Python, func: PyObject) -> PyResult<String> {
    use std::io::Cursor;

    // This is a simplified version - production would use more robust capturing
    let output = func.call0(py)?;
    Ok(output.to_string())
}

#[pyfunction]
fn mock_stdin(input: String) -> PyResult<()> {
    // This would require platform-specific implementation
    // Showing the concept here
    Ok(())
}

#[pyclass]
struct TestRunner {
    tests: Vec<PyObject>,
}

#[pymethods]
impl TestRunner {
    #[new]
    fn new() -> Self {
        TestRunner {
            tests: Vec::new(),
        }
    }

    fn add_test(&mut self, test: PyObject) {
        self.tests.push(test);
    }

    fn run_all(&self, py: Python) -> PyResult<(usize, usize)> {
        let mut passed = 0;
        let mut failed = 0;

        for test in &self.tests {
            match test.call0(py) {
                Ok(_) => {
                    passed += 1;
                    println!("{}", colorize("PASS".to_string(), "green", true));
                }
                Err(e) => {
                    failed += 1;
                    println!("{}: {}", colorize("FAIL".to_string(), "red", true), e);
                }
            }
        }

        Ok((passed, failed))
    }
}
```

### 10.4 Performance Profiling

```rust
use std::time::Instant;
use std::collections::HashMap;

#[pyclass]
struct Profiler {
    timings: HashMap<String, Vec<Duration>>,
}

#[pymethods]
impl Profiler {
    #[new]
    fn new() -> Self {
        Profiler {
            timings: HashMap::new(),
        }
    }

    fn start_timer(&self, name: String) -> Timer {
        Timer::new(name)
    }

    fn record(&mut self, name: String, duration: f64) {
        let dur = Duration::from_secs_f64(duration);
        self.timings.entry(name).or_insert_with(Vec::new).push(dur);
    }

    fn get_stats(&self, name: String) -> Option<(f64, f64, f64, usize)> {
        self.timings.get(&name).map(|timings| {
            let count = timings.len();
            let total: Duration = timings.iter().sum();
            let avg = total.as_secs_f64() / count as f64;
            let min = timings.iter().min().unwrap().as_secs_f64();
            let max = timings.iter().max().unwrap().as_secs_f64();

            (avg, min, max, count)
        })
    }

    fn print_report(&self) {
        println!("\n=== Performance Report ===");

        for (name, timings) in &self.timings {
            if let Some((avg, min, max, count)) = self.get_stats(name.clone()) {
                println!("\n{}:", name);
                println!("  Count: {}", count);
                println!("  Average: {:.3}s", avg);
                println!("  Min: {:.3}s", min);
                println!("  Max: {:.3}s", max);
            }
        }
    }
}

#[pyclass]
struct Timer {
    name: String,
    start: Instant,
}

#[pymethods]
impl Timer {
    #[new]
    fn new(name: String) -> Self {
        Timer {
            name,
            start: Instant::now(),
        }
    }

    fn elapsed(&self) -> f64 {
        self.start.elapsed().as_secs_f64()
    }

    fn stop(&self) -> (String, f64) {
        (self.name.clone(), self.elapsed())
    }
}
```

---

## Summary

This reference covers:

1. **Argument Parsing**: ArgumentParser, positional args, argparse/click integration
2. **Terminal Output**: Colors, tables, pretty printing, formatting
3. **Progress Indicators**: Progress bars, spinners, multi-progress
4. **File Processing**: Fast I/O, directory traversal, parallel processing, watching
5. **Configuration**: TOML, YAML, env files, validation
6. **Interactive Input**: Prompts, passwords, selections, confirmations
7. **Terminal UI**: Screen management, box drawing, layouts, panels
8. **Command Execution**: Process spawning, pipelines, signal handling
9. **Shell Completion**: Bash, Zsh, Fish completion generation
10. **Production Patterns**: Error handling, logging, testing, profiling

For more information, see:
- [PyO3 Documentation](https://pyo3.rs/)
- [Clap Documentation](https://docs.rs/clap/)
- [Crossterm Documentation](https://docs.rs/crossterm/)
- [Ratatui Documentation](https://docs.rs/ratatui/)
