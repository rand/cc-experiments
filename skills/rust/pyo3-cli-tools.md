---
name: pyo3-cli-tools
description: PyO3 for CLI tools and embedding including pyo3-ffi, dynamic plugin loading, multi-interpreter applications
skill_id: rust-pyo3-cli-tools
title: PyO3 CLI Tools Development
category: rust
subcategory: pyo3
complexity: advanced
prerequisites:
  - rust-pyo3-basics-types-conversions
  - rust-pyo3-modules-functions-errors
tags:
  - rust
  - python
  - pyo3
  - cli
  - terminal
  - tui
  - argparse
  - click
  - typer
  - console
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Build high-performance CLI tools with PyO3
  - Integrate with Python argument parsers (argparse, click, typer)
  - Create terminal UI components
  - Implement progress indicators and spinners
  - Handle configuration management efficiently
  - Build distributable executables
  - Optimize CLI performance
  - Create production CLI applications
related_skills:
  - rust-pyo3-performance-gil-parallel
  - rust-pyo3-packaging-distribution
---

# PyO3 CLI Tools Development

## Overview

Master the development of high-performance command-line interface tools using PyO3. Learn to integrate with Python CLI frameworks, build terminal UIs, handle user input efficiently, and create production-ready CLI applications that leverage Rust's speed.

## Prerequisites

- **Required**: PyO3 basics, CLI fundamentals, terminal concepts
- **Recommended**: Experience with argparse/click/typer, terminal UI libraries
- **Tools**: pyo3, clap (Rust), click/typer (Python), indicatif, crossterm

## Learning Path

### 1. Argument Parsing Integration

#### With Python's argparse

```rust
use pyo3::prelude::*;

#[pyfunction]
fn fast_grep(pattern: String, files: Vec<String>, case_sensitive: bool) -> Vec<String> {
    let mut results = Vec::new();

    for file in files {
        if let Ok(content) = std::fs::read_to_string(&file) {
            for (line_num, line) in content.lines().enumerate() {
                let matches = if case_sensitive {
                    line.contains(&pattern)
                } else {
                    line.to_lowercase().contains(&pattern.to_lowercase())
                };

                if matches {
                    results.push(format!("{}:{}: {}", file, line_num + 1, line));
                }
            }
        }
    }

    results
}
```

```python
# cli.py
import argparse
from my_extension import fast_grep

def main():
    parser = argparse.ArgumentParser(description='Fast grep tool')
    parser.add_argument('pattern', help='Search pattern')
    parser.add_argument('files', nargs='+', help='Files to search')
    parser.add_argument('-i', '--ignore-case', action='store_true',
                        help='Case insensitive search')

    args = parser.parse_args()

    results = fast_grep(args.pattern, args.files, not args.ignore_case)

    for result in results:
        print(result)

if __name__ == '__main__':
    main()
```

#### With click

```rust
#[pyfunction]
fn process_files(
    input_dir: String,
    output_dir: String,
    recursive: bool,
    verbose: bool
) -> PyResult<usize> {
    use walkdir::WalkDir;

    let mut count = 0;

    let walker = if recursive {
        WalkDir::new(&input_dir)
    } else {
        WalkDir::new(&input_dir).max_depth(1)
    };

    for entry in walker {
        let entry = entry?;

        if entry.file_type().is_file() {
            if verbose {
                println!("Processing: {}", entry.path().display());
            }

            // Process file
            count += 1;
        }
    }

    Ok(count)
}
```

```python
import click
from my_extension import process_files

@click.command()
@click.argument('input_dir')
@click.argument('output_dir')
@click.option('-r', '--recursive', is_flag=True, help='Recursive processing')
@click.option('-v', '--verbose', is_flag=True, help='Verbose output')
def main(input_dir, output_dir, recursive, verbose):
    """Process files from INPUT_DIR to OUTPUT_DIR."""
    count = process_files(input_dir, output_dir, recursive, verbose)
    click.echo(f"Processed {count} files")

if __name__ == '__main__':
    main()
```

#### With typer

```rust
#[pyfunction]
fn analyze_data(
    file_path: String,
    format: String,
    output: Option<String>
) -> PyResult<String> {
    // Fast data analysis
    let data = std::fs::read_to_string(&file_path)?;

    let result = format!("Analyzed {} bytes", data.len());

    if let Some(output_path) = output {
        std::fs::write(output_path, &result)?;
    }

    Ok(result)
}
```

```python
import typer
from my_extension import analyze_data
from pathlib import Path

app = typer.Typer()

@app.command()
def analyze(
    file_path: Path = typer.Argument(..., help="Input file path"),
    format: str = typer.Option("json", help="Output format"),
    output: Path = typer.Option(None, help="Output file")
):
    """Analyze data file with Rust backend."""
    result = analyze_data(str(file_path), format, str(output) if output else None)
    typer.echo(result)

if __name__ == '__main__':
    app()
```

### 2. Terminal Output & Formatting

```rust
use pyo3::prelude::*;
use colored::Colorize;

#[pyfunction]
fn print_colored(text: String, color: String) -> String {
    match color.as_str() {
        "red" => text.red().to_string(),
        "green" => text.green().to_string(),
        "blue" => text.blue().to_string(),
        "yellow" => text.yellow().to_string(),
        _ => text,
    }
}

#[pyfunction]
fn format_table(headers: Vec<String>, rows: Vec<Vec<String>>) -> Vec<String> {
    use prettytable::{Table, Row, Cell};

    let mut table = Table::new();

    // Add header
    table.add_row(Row::new(
        headers.iter().map(|h| Cell::new(h)).collect()
    ));

    // Add rows
    for row in rows {
        table.add_row(Row::new(
            row.iter().map(|c| Cell::new(c)).collect()
        ));
    }

    table.to_string().lines().map(|s| s.to_string()).collect()
}
```

```python
from my_extension import print_colored, format_table

# Colored output
print(print_colored("Success!", "green"))
print(print_colored("Error!", "red"))

# Table formatting
headers = ["Name", "Age", "City"]
rows = [
    ["Alice", "30", "NYC"],
    ["Bob", "25", "SF"],
]
table = format_table(headers, rows)
for line in table:
    print(line)
```

### 3. Progress Indicators

```rust
use pyo3::prelude::*;
use std::sync::{Arc, Mutex};

#[pyclass]
struct ProgressBar {
    total: Arc<Mutex<usize>>,
    current: Arc<Mutex<usize>>,
}

#[pymethods]
impl ProgressBar {
    #[new]
    fn new(total: usize) -> Self {
        ProgressBar {
            total: Arc::new(Mutex::new(total)),
            current: Arc::new(Mutex::new(0)),
        }
    }

    fn update(&self, n: usize) {
        let mut current = self.current.lock().unwrap();
        *current += n;

        let total = *self.total.lock().unwrap();
        let percent = (*current as f64 / total as f64) * 100.0;

        print!("\r[{:>3.0}%] {}/{}", percent, *current, total);
        use std::io::Write;
        std::io::stdout().flush().unwrap();
    }

    fn finish(&self) {
        println!("\n✓ Complete!");
    }
}
```

```python
from my_extension import ProgressBar
import time

# Progress bar
pb = ProgressBar(total=100)
for i in range(100):
    time.sleep(0.01)
    pb.update(1)
pb.finish()
```

### 4. File Processing

```rust
use pyo3::prelude::*;
use rayon::prelude::*;

#[pyfunction]
fn process_files_parallel(py: Python, paths: Vec<String>) -> Vec<String> {
    py.allow_threads(|| {
        paths.par_iter()
            .map(|path| {
                std::fs::read_to_string(path)
                    .map(|content| format!("{}: {} bytes", path, content.len()))
                    .unwrap_or_else(|e| format!("{}: error: {}", path, e))
            })
            .collect()
    })
}

#[pyfunction]
fn search_in_files(pattern: String, paths: Vec<String>) -> Vec<(String, usize)> {
    use regex::Regex;

    let re = Regex::new(&pattern).unwrap();
    let mut results = Vec::new();

    for path in paths {
        if let Ok(content) = std::fs::read_to_string(&path) {
            let count = re.find_iter(&content).count();
            if count > 0 {
                results.push((path, count));
            }
        }
    }

    results
}
```

### 5. Configuration Management

```rust
use pyo3::prelude::*;
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize)]
struct Config {
    host: String,
    port: u16,
    debug: bool,
    workers: usize,
}

#[pyfunction]
fn load_config(path: String) -> PyResult<(String, u16, bool, usize)> {
    let content = std::fs::read_to_string(&path)?;
    let config: Config = toml::from_str(&content)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    Ok((config.host, config.port, config.debug, config.workers))
}

#[pyfunction]
fn save_config(
    path: String,
    host: String,
    port: u16,
    debug: bool,
    workers: usize
) -> PyResult<()> {
    let config = Config { host, port, debug, workers };

    let content = toml::to_string(&config)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    std::fs::write(&path, content)?;
    Ok(())
}
```

```python
from my_extension import load_config, save_config

# Load config
host, port, debug, workers = load_config("config.toml")

# Modify and save
save_config("config.toml", host, port + 1, debug, workers)
```

### 6. Interactive Input

```rust
use pyo3::prelude::*;

#[pyfunction]
fn read_password() -> PyResult<String> {
    use rpassword::read_password;

    print!("Password: ");
    use std::io::Write;
    std::io::stdout().flush()?;

    Ok(read_password()?)
}

#[pyfunction]
fn confirm(message: String) -> PyResult<bool> {
    use std::io::{self, Write};

    print!("{} [y/N]: ", message);
    io::stdout().flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;

    Ok(input.trim().to_lowercase() == "y")
}
```

```python
from my_extension import read_password, confirm

# Password input (hidden)
password = read_password()

# Confirmation
if confirm("Delete all files?"):
    print("Deleting...")
else:
    print("Cancelled")
```

### 7. Terminal UI Components

```rust
use pyo3::prelude::*;

#[pyclass]
struct Spinner {
    message: String,
    running: std::sync::Arc<std::sync::atomic::AtomicBool>,
}

#[pymethods]
impl Spinner {
    #[new]
    fn new(message: String) -> Self {
        Spinner {
            message,
            running: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),
        }
    }

    fn start(&self) {
        use std::sync::atomic::Ordering;
        self.running.store(true, Ordering::SeqCst);

        let message = self.message.clone();
        let running = self.running.clone();

        std::thread::spawn(move || {
            let frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
            let mut i = 0;

            while running.load(Ordering::SeqCst) {
                print!("\r{} {}", frames[i % frames.len()], message);
                use std::io::Write;
                std::io::stdout().flush().unwrap();

                std::thread::sleep(std::time::Duration::from_millis(80));
                i += 1;
            }

            print!("\r\x1B[K");  // Clear line
        });
    }

    fn stop(&self) {
        use std::sync::atomic::Ordering;
        self.running.store(false, Ordering::SeqCst);
        std::thread::sleep(std::time::Duration::from_millis(100));
    }
}
```

```python
from my_extension import Spinner
import time

spinner = Spinner("Loading...")
spinner.start()

# Do work
time.sleep(3)

spinner.stop()
print("✓ Done!")
```

### 8. Command Execution

```rust
use pyo3::prelude::*;
use std::process::Command;

#[pyfunction]
fn run_command(cmd: String, args: Vec<String>) -> PyResult<(i32, String, String)> {
    let output = Command::new(&cmd)
        .args(&args)
        .output()?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    Ok((output.status.code().unwrap_or(-1), stdout, stderr))
}

#[pyfunction]
fn run_command_async(py: Python, cmd: String, args: Vec<String>) -> PyResult<&PyAny> {
    use pyo3_asyncio::tokio::future_into_py;

    future_into_py(py, async move {
        let output = tokio::process::Command::new(&cmd)
            .args(&args)
            .output()
            .await
            .unwrap();

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();

        Python::with_gil(|py| {
            Ok((output.status.code().unwrap_or(-1), stdout, stderr).into_py(py))
        })
    })
}
```

### 9. Shell Completion

```rust
use pyo3::prelude::*;

#[pyfunction]
fn generate_completions(shell: String) -> String {
    // Generate shell completion script
    match shell.as_str() {
        "bash" => r#"
_my_tool_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="--help --version analyze process"

    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
    return 0
}
complete -F _my_tool_completion my-tool
"#.to_string(),
        "zsh" => r#"
#compdef my-tool
_my_tool() {
    local -a commands
    commands=(
        'analyze:Analyze data'
        'process:Process files'
    )
    _describe 'command' commands
}
"#.to_string(),
        _ => String::new(),
    }
}
```

### 10. Pipeline Processing

```rust
use pyo3::prelude::*;

#[pyclass]
struct Pipeline {
    stages: Vec<String>,
}

#[pymethods]
impl Pipeline {
    #[new]
    fn new() -> Self {
        Pipeline { stages: Vec::new() }
    }

    fn add_stage(&mut self, name: String) {
        self.stages.push(name);
    }

    fn execute(&self, py: Python, data: Vec<u8>) -> PyResult<Vec<u8>> {
        let mut current_data = data;

        for stage in &self.stages {
            // Execute each stage
            current_data = self.process_stage(py, stage, current_data)?;
        }

        Ok(current_data)
    }

    fn process_stage(&self, _py: Python, _stage: &str, data: Vec<u8>) -> PyResult<Vec<u8>> {
        // Process data through stage
        Ok(data)
    }
}
```

## Common Patterns

### Error Handling for CLI

```rust
#[pyfunction]
fn cli_operation(path: String) -> PyResult<String> {
    std::fs::read_to_string(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(
            format!("Failed to read '{}': {}", path, e)
        ))
}
```

### Streaming Output

```rust
#[pyfunction]
fn stream_process(files: Vec<String>, callback: PyObject) -> PyResult<()> {
    Python::with_gil(|py| {
        for file in files {
            if let Ok(content) = std::fs::read_to_string(&file) {
                callback.call1(py, (file, content.len()))?;
            }
        }
        Ok(())
    })
}
```

```python
from my_extension import stream_process

def progress_callback(filename, size):
    print(f"Processed {filename}: {size} bytes")

stream_process(files, progress_callback)
```

## Anti-Patterns

### ❌ Incorrect: Blocking Main Thread

```rust
#[pyfunction]
fn slow_cli_operation() {
    std::thread::sleep(std::time::Duration::from_secs(10));
    // Blocks entire CLI
}
```

### ✅ Correct: Show Progress

```rust
#[pyfunction]
fn fast_cli_operation(callback: PyObject) {
    for i in 0..100 {
        Python::with_gil(|py| {
            callback.call1(py, (i,)).unwrap();
        });
        std::thread::sleep(std::time::Duration::from_millis(100));
    }
}
```

## Resources

### Crates
- **clap**: Command-line argument parser (Rust)
- **indicatif**: Progress bars and spinners
- **colored**: Terminal colors
- **rpassword**: Password input
- **walkdir**: Directory traversal

### Documentation
- [click Documentation](https://click.palletsprojects.com/)
- [typer Documentation](https://typer.tiangolo.com/)
- [argparse Documentation](https://docs.python.org/3/library/argparse.html)

### Related Skills
- [pyo3-performance-gil-parallel.md](pyo3-performance-gil-parallel.md)
- [pyo3-packaging-distribution.md](pyo3-packaging-distribution.md)

## Examples

See `resources/examples/` for:
1. argparse integration
2. click CLI tool
3. typer application
4. Progress bars and spinners
5. File search tool
6. Configuration manager
7. Interactive wizard
8. Terminal dashboard
9. Pipeline processor
10. Production CLI application

## Additional Resources

- **REFERENCE.md**: Comprehensive patterns and examples
- **Scripts**:
  - `cli_generator.py`: CLI boilerplate generation
  - `completion_builder.py`: Shell completion generator
  - `tui_components.py`: Terminal UI component library
