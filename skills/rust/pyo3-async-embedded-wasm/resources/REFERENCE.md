# PyO3 Async, Embedded Python & WASM - Comprehensive Reference

Complete guide to async Python integration, embedded interpreters, and WebAssembly compilation with PyO3.

**Version**: 1.0.0
**PyO3**: 0.20+
**Python**: 3.8+
**Tokio**: 1.0+
**Last Updated**: 2025-10-30

---

## Table of Contents

1. [Async Fundamentals](#async-fundamentals)
2. [Tokio Integration](#tokio-integration)
3. [pyo3-asyncio](#pyo3-asyncio)
4. [Embedded Python](#embedded-python)
5. [WASM Compilation](#wasm-compilation)
6. [Pyodide Integration](#pyodide-integration)
7. [WASI Applications](#wasi-applications)
8. [Async Streams](#async-streams)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## 1. Async Fundamentals

### Rust Async vs Python Async

**Rust async**:
- Zero-cost abstraction
- Compile-time state machines
- No runtime by default (need Tokio, async-std, etc.)
- `Future` trait

**Python asyncio**:
- Event loop-based
- Runtime included in standard library
- Coroutines (`async def`)
- `awaitable` objects

**Bridge**: Need to convert between Rust `Future` and Python coroutines.

### Basic Async Function

```rust
use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use std::time::Duration;

#[pyfunction]
fn async_sleep(py: Python, seconds: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        tokio::time::sleep(Duration::from_secs(seconds)).await;
        Ok(Python::with_gil(|py| "Done".into_py(py)))
    })
}
```

**Python usage**:
```python
import asyncio
import my_module

async def main():
    result = await my_module.async_sleep(1)
    print(result)  # "Done"

asyncio.run(main())
```

### GIL Lifetime in Async

**Critical Rule**: Don't hold GIL across `.await` points!

```rust
// ❌ BAD: Holding GIL across await
async fn bad_example() {
    let py = Python::acquire_gil();  // Acquire GIL
    let py = py.python();

    some_async_operation().await;  // Still holding GIL! Deadlock risk!

    // Use Python objects
}

// ✅ GOOD: Acquire GIL only when needed
async fn good_example() {
    let result = some_async_operation().await;  // No GIL

    Python::with_gil(|py| {
        // Use result with Python
    });
}
```

### Async Errors

```rust
#[pyfunction]
fn async_with_error(py: Python) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        // Async operation that might fail
        let result = tokio::fs::read_to_string("file.txt").await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(
                format!("Failed to read file: {}", e)
            ))?;

        Ok(Python::with_gil(|py| result.into_py(py)))
    })
}
```

---

## 2. Tokio Integration

### Runtime Setup

**Single-threaded Runtime**:
```rust
use pyo3::prelude::*;
use pyo3_asyncio::tokio::init_runtime;

#[pymodule]
fn my_module(py: Python, m: &PyModule) -> PyResult<()> {
    // Initialize Tokio runtime
    pyo3_asyncio::tokio::init(py)?;

    m.add_function(wrap_pyfunction!(async_function, m)?)?;
    Ok(())
}
```

**Multi-threaded Runtime**:
```rust
use tokio::runtime::Runtime;
use once_cell::sync::OnceCell;

static RUNTIME: OnceCell<Runtime> = OnceCell::new();

fn get_runtime() -> &'static Runtime {
    RUNTIME.get_or_init(|| {
        tokio::runtime::Builder::new_multi_thread()
            .worker_threads(4)
            .thread_name("pyo3-tokio")
            .build()
            .unwrap()
    })
}

#[pyfunction]
fn async_with_runtime(py: Python) -> PyResult<&PyAny> {
    let runtime = get_runtime();

    future_into_py(py, async move {
        // Run on Tokio runtime
        runtime.spawn(async {
            // Async work
        }).await.unwrap();

        Ok(Python::with_gil(|py| py.None()))
    })
}
```

### Spawning Tasks

```rust
use tokio::task;

#[pyfunction]
fn spawn_background_task(py: Python, count: u64) -> PyResult<()> {
    task::spawn(async move {
        for i in 0..count {
            tokio::time::sleep(Duration::from_secs(1)).await;
            println!("Background task: {}", i);
        }
    });

    Ok(())
}
```

### Async HTTP Client

```rust
use reqwest;

#[pyfunction]
fn fetch_url(py: Python, url: String) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let response = reqwest::get(&url)
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("HTTP error: {}", e)
            ))?;

        let status = response.status().as_u16();
        let body = response.text()
            .await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Body read error: {}", e)
            ))?;

        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("status", status)?;
            dict.set_item("body", body)?;
            Ok(dict.into())
        })
    })
}
```

**Python usage**:
```python
async def main():
    result = await my_module.fetch_url("https://api.github.com")
    print(f"Status: {result['status']}")
    print(f"Body: {result['body'][:100]}")
```

### Concurrent Operations

```rust
use futures::future::join_all;

#[pyfunction]
fn fetch_many(py: Python, urls: Vec<String>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let futures = urls.into_iter().map(|url| async move {
            reqwest::get(&url)
                .await
                .and_then(|r| r.text().await)
                .map_err(|e| e.to_string())
        });

        let results = join_all(futures).await;

        Python::with_gil(|py| {
            let list = pyo3::types::PyList::empty(py);
            for result in results {
                match result {
                    Ok(body) => list.append(body)?,
                    Err(e) => list.append(py.None())?,
                }
            }
            Ok(list.into())
        })
    })
}
```

### Timeouts

```rust
use tokio::time::{timeout, Duration};

#[pyfunction]
fn with_timeout(py: Python, url: String, seconds: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let future = reqwest::get(&url);

        match timeout(Duration::from_secs(seconds), future).await {
            Ok(Ok(response)) => {
                let body = response.text().await.map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())
                })?;
                Ok(Python::with_gil(|py| body.into_py(py)))
            }
            Ok(Err(e)) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Request failed: {}", e)
            )),
            Err(_) => Err(PyErr::new::<pyo3::exceptions::PyTimeoutError, _>(
                format!("Request timed out after {}s", seconds)
            )),
        }
    })
}
```

---

## 3. pyo3-asyncio

### Installation

```toml
[dependencies]
pyo3 = "0.20"
pyo3-asyncio = { version = "0.20", features = ["tokio-runtime"] }
tokio = { version = "1", features = ["full"] }
```

### future_into_py

Converts Rust `Future` to Python coroutine:

```rust
use pyo3_asyncio::tokio::future_into_py;

#[pyfunction]
fn rust_future_to_py(py: Python) -> PyResult<&PyAny> {
    future_into_py(py, async {
        // Async Rust code
        tokio::time::sleep(Duration::from_millis(100)).await;

        Ok(Python::with_gil(|py| 42.into_py(py)))
    })
}
```

### Calling Python Async from Rust

```rust
use pyo3_asyncio::tokio::into_future;

async fn call_python_async(py: Python<'_>, coro: &PyAny) -> PyResult<PyObject> {
    let future = into_future(coro)?;
    future.await
}
```

**Example**:
```rust
#[pyfunction]
fn call_python_coro(py: Python, coro: &PyAny) -> PyResult<&PyAny> {
    let coro = coro.into();
    future_into_py(py, async move {
        let result = pyo3_asyncio::tokio::into_future(coro).await?;
        Ok(result)
    })
}
```

**Python usage**:
```python
async def python_coro():
    await asyncio.sleep(1)
    return "from Python"

async def main():
    result = await my_module.call_python_coro(python_coro())
    print(result)  # "from Python"
```

### Runtime Selection

```toml
# For Tokio
pyo3-asyncio = { version = "0.20", features = ["tokio-runtime"] }

# For async-std
pyo3-asyncio = { version = "0.20", features = ["async-std-runtime"] }
```

### Event Loop Integration

```rust
use pyo3_asyncio::tokio::run_until_complete;

#[pyfunction]
fn run_async_task(py: Python, task: &PyAny) -> PyResult<PyObject> {
    run_until_complete(py, async move {
        // Execute Python coroutine
        pyo3_asyncio::tokio::into_future(task).await
    })
}
```

---

## 4. Embedded Python

### Basic Embedding

```rust
use pyo3::prelude::*;
use pyo3::types::IntoPyDict;

fn main() -> PyResult<()> {
    Python::with_gil(|py| {
        // Execute Python code
        let result = py.eval("2 + 2", None, None)?;
        println!("2 + 2 = {}", result);

        // Import and use modules
        let sys = py.import("sys")?;
        let version: String = sys.getattr("version")?.extract()?;
        println!("Python version: {}", version);

        Ok(())
    })
}
```

### Running Python Scripts

```rust
fn run_script(script_path: &str) -> PyResult<()> {
    Python::with_gil(|py| {
        let code = std::fs::read_to_string(script_path)?;
        py.run(&code, None, None)?;
        Ok(())
    })
}
```

### Passing Data to Python

```rust
fn execute_with_vars() -> PyResult<()> {
    Python::with_gil(|py| {
        let locals = [
            ("x", 10i32.into_py(py)),
            ("y", 20i32.into_py(py)),
        ].into_py_dict(py);

        py.run("result = x + y", None, Some(locals))?;

        let result: i32 = locals.get_item("result")
            .unwrap()
            .extract()?;

        println!("Result: {}", result);
        Ok(())
    })
}
```

### Calling Python Functions

```rust
fn call_python_function() -> PyResult<()> {
    Python::with_gil(|py| {
        let builtins = py.import("builtins")?;
        let sum_func = builtins.getattr("sum")?;

        let result: i64 = sum_func
            .call1((vec![1, 2, 3, 4, 5],))?
            .extract()?;

        println!("Sum: {}", result);
        Ok(())
    })
}
```

### Embedding with Custom Module

```rust
use pyo3::wrap_pymodule;

#[pymodule]
fn embedded_module(_py: Python, m: &PyModule) -> PyResult<()> {
    #[pyfn(m)]
    fn rust_function(x: i64, y: i64) -> i64 {
        x * y
    }

    Ok(())
}

fn main() -> PyResult<()> {
    pyo3::prepare_freethreaded_python();

    Python::with_gil(|py| {
        let module = wrap_pymodule!(embedded_module)(py);
        py.import("sys")?
            .getattr("modules")?
            .set_item("embedded_module", module)?;

        py.run("import embedded_module", None, None)?;
        py.run("print(embedded_module.rust_function(6, 7))", None, None)?;

        Ok(())
    })
}
```

### Plugin System

```rust
use std::path::PathBuf;
use std::collections::HashMap;

struct PluginEngine {
    plugins: HashMap<String, Py<PyAny>>,
}

impl PluginEngine {
    fn new() -> Self {
        pyo3::prepare_freethreaded_python();
        Self {
            plugins: HashMap::new(),
        }
    }

    fn load_plugin(&mut self, name: String, path: PathBuf) -> PyResult<()> {
        Python::with_gil(|py| {
            let code = std::fs::read_to_string(&path)?;

            // Execute plugin code
            let module = PyModule::from_code(
                py,
                &code,
                &path.to_string_lossy(),
                &name,
            )?;

            // Get plugin class
            let plugin_class = module.getattr("Plugin")?;
            let plugin_instance = plugin_class.call0()?;

            self.plugins.insert(name, plugin_instance.into());
            Ok(())
        })
    }

    fn call_plugin(&self, name: &str, method: &str, args: &[i64]) -> PyResult<i64> {
        Python::with_gil(|py| {
            let plugin = self.plugins.get(name)
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>(
                    format!("Plugin not found: {}", name)
                ))?;

            let result = plugin.call_method1(py, method, (args.to_vec(),))?;
            result.extract(py)
        })
    }
}
```

**Plugin file (plugin.py)**:
```python
class Plugin:
    def process(self, data):
        return sum(data)
```

**Usage**:
```rust
fn main() -> PyResult<()> {
    let mut engine = PluginEngine::new();
    engine.load_plugin("math_plugin".to_string(), "plugin.py".into())?;

    let result = engine.call_plugin("math_plugin", "process", &[1, 2, 3, 4, 5])?;
    println!("Result: {}", result);

    Ok(())
}
```

### Module Search Path

```rust
fn configure_python_path() -> PyResult<()> {
    Python::with_gil(|py| {
        let sys = py.import("sys")?;
        let path: Vec<String> = sys.getattr("path")?.extract()?;

        println!("Python path:");
        for p in path {
            println!("  {}", p);
        }

        // Add custom path
        sys.getattr("path")?
            .call_method1("append", ("/custom/path",))?;

        Ok(())
    })
}
```

---

## 5. WASM Compilation

### Setup

```toml
[lib]
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
wasm-bindgen = "0.2"

[profile.release]
opt-level = "z"       # Optimize for size
lto = true            # Link-time optimization
codegen-units = 1     # Better optimization
strip = true          # Strip symbols
```

### Build for Browser

```bash
# Install wasm-pack
cargo install wasm-pack

# Build
wasm-pack build --target web --release

# Output: pkg/ directory with .wasm file
```

### WASM-Compatible Code

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn process_data(data: Vec<f64>) -> Vec<f64> {
    data.iter().map(|x| x * 2.0).collect()
}

// Conditional compilation for PyO3
#[cfg(not(target_arch = "wasm32"))]
#[pyfunction]
fn process_data_py(data: Vec<f64>) -> Vec<f64> {
    process_data(data)
}

#[cfg(not(target_arch = "wasm32"))]
#[pymodule]
fn my_module(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_data_py, m)?)?;
    Ok(())
}
```

### JavaScript Integration

```javascript
import init, { process_data } from './pkg/my_module.js';

async function main() {
    await init();

    const data = [1.0, 2.0, 3.0, 4.0, 5.0];
    const result = process_data(data);
    console.log(result);  // [2.0, 4.0, 6.0, 8.0, 10.0]
}

main();
```

### WASM Limitations

**No Threading**:
```rust
// ❌ Won't work in WASM
#[cfg(not(target_arch = "wasm32"))]
fn use_threads() {
    std::thread::spawn(|| {
        // ...
    });
}

// ✅ Alternative: Sequential processing
#[cfg(target_arch = "wasm32")]
fn process_sequential() {
    // Process without threads
}
```

**Limited File System**:
```rust
// ❌ No file system in browser WASM
#[cfg(not(target_arch = "wasm32"))]
fn read_file() {
    std::fs::read_to_string("file.txt").unwrap();
}

// ✅ Use JavaScript File API or fetch
#[wasm_bindgen]
pub fn process_file_content(content: String) -> String {
    // Process content passed from JavaScript
    content.to_uppercase()
}
```

### Memory Management

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct Buffer {
    data: Vec<u8>,
}

#[wasm_bindgen]
impl Buffer {
    #[wasm_bindgen(constructor)]
    pub fn new(size: usize) -> Self {
        Self {
            data: vec![0; size],
        }
    }

    pub fn len(&self) -> usize {
        self.data.len()
    }

    pub fn ptr(&self) -> *const u8 {
        self.data.as_ptr()
    }

    // Explicit memory cleanup
    pub fn free(self) {
        drop(self);
    }
}
```

---

## 6. Pyodide Integration

### What is Pyodide?

**Pyodide** = CPython compiled to WebAssembly + scientific stack (NumPy, Pandas, etc.)

**Features**:
- Full Python in the browser
- NumPy, SciPy, Matplotlib
- Load custom packages
- JavaScript ↔ Python interop

### Loading Pyodide

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/pyodide/v0.24.0/full/pyodide.js"></script>
</head>
<body>
    <script type="module">
        async function main() {
            let pyodide = await loadPyodide();

            // Run Python code
            pyodide.runPython(`
                import sys
                print(f"Python {sys.version}")
            `);
        }

        main();
    </script>
</body>
</html>
```

### Loading Custom WASM Module

```javascript
async function loadCustomModule() {
    let pyodide = await loadPyodide();

    // Load custom compiled extension
    await pyodide.loadPackage('./my_module.wasm');

    // Use from Python
    pyodide.runPython(`
        import my_module
        result = my_module.process_data([1, 2, 3, 4, 5])
        print(result)
    `);
}
```

### Python ↔ JavaScript Bridge

```javascript
let pyodide = await loadPyodide();

// JavaScript -> Python
pyodide.globals.set("js_data", [1, 2, 3, 4, 5]);

pyodide.runPython(`
    from js import js_data
    result = sum(js_data)
    result  # Return to JavaScript
`);

// Python -> JavaScript
let result = pyodide.globals.get("result");
console.log(result);  // 15
```

### NumPy Example

```javascript
let pyodide = await loadPyodide();
await pyodide.loadPackage('numpy');

pyodide.runPython(`
    import numpy as np

    # Create array
    arr = np.array([1, 2, 3, 4, 5])

    # Operations
    squared = arr ** 2
    mean = arr.mean()

    print(f"Squared: {squared}")
    print(f"Mean: {mean}")
`);
```

### Rust Extension in Pyodide

```rust
// Rust side (compiled to WASM)
#[wasm_bindgen]
pub fn fast_computation(data: Vec<f64>) -> Vec<f64> {
    data.iter().map(|x| {
        // Fast Rust computation
        x.powi(2) + 2.0 * x + 1.0
    }).collect()
}
```

```javascript
// JavaScript side
let pyodide = await loadPyodide();
await pyodide.loadPackage('./my_rust_module.wasm');

pyodide.runPython(`
    import my_rust_module
    import numpy as np

    # Use Rust from Python
    data = np.linspace(0, 10, 1000).tolist()
    result = my_rust_module.fast_computation(data)
    print(f"Computed {len(result)} values")
`);
```

---

## 7. WASI Applications

### What is WASI?

**WASI** (WebAssembly System Interface) = System interface for WASM outside browsers

**Features**:
- File system access
- Environment variables
- Command-line arguments
- Network (in development)

### Building for WASI

```bash
# Add target
rustup target add wasm32-wasi

# Build
cargo build --target wasm32-wasi --release

# Output: target/wasm32-wasi/release/my_app.wasm
```

### Running WASI

```bash
# Using wasmtime
wasmtime target/wasm32-wasi/release/my_app.wasm

# Using wasmer
wasmer run target/wasm32-wasi/release/my_app.wasm
```

### WASI-Compatible Code

```rust
// This works in WASI!
use std::fs;
use std::env;

fn main() -> std::io::Result<()> {
    // Read environment
    let args: Vec<String> = env::args().collect();
    println!("Args: {:?}", args);

    // File I/O (with appropriate permissions)
    let content = fs::read_to_string("input.txt")?;
    println!("Content: {}", content);

    fs::write("output.txt", "Hello from WASI!")?;

    Ok(())
}
```

### PyO3 with WASI

```rust
use pyo3::prelude::*;

#[pyfunction]
fn process_file(path: String) -> PyResult<String> {
    let content = std::fs::read_to_string(path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    Ok(content.to_uppercase())
}

#[pymodule]
fn wasi_module(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_file, m)?)?;
    Ok(())
}
```

### Sandboxing with WASI

```bash
# Run with restricted file system access
wasmtime \
    --dir /tmp::./sandbox \  # Map ./sandbox to /tmp
    --env VAR=value \         # Set environment variable
    my_app.wasm
```

---

## 8. Async Streams

### Basic Stream

```rust
use tokio_stream::{Stream, StreamExt};
use futures::stream;

#[pyfunction]
fn async_range(py: Python, n: usize) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let stream = stream::iter(0..n);

        let results: Vec<_> = stream
            .map(|x| x * 2)
            .collect()
            .await;

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}
```

### Stream from Channel

```rust
use tokio::sync::mpsc;
use tokio_stream::wrappers::ReceiverStream;

#[pyfunction]
fn stream_from_channel(py: Python, count: usize) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let (tx, rx) = mpsc::channel(100);

        // Producer
        tokio::spawn(async move {
            for i in 0..count {
                if tx.send(i).await.is_err() {
                    break;
                }
                tokio::time::sleep(Duration::from_millis(100)).await;
            }
        });

        // Consumer
        let stream = ReceiverStream::new(rx);
        let results: Vec<_> = stream.collect().await;

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}
```

### Async Iterator for Python

```rust
use pyo3::pyclass;

#[pyclass]
struct AsyncRange {
    current: usize,
    end: usize,
}

#[pymethods]
impl AsyncRange {
    #[new]
    fn new(end: usize) -> Self {
        Self { current: 0, end }
    }

    fn __aiter__(slf: PyRef<Self>) -> PyRef<Self> {
        slf
    }

    fn __anext__(mut slf: PyRefMut<Self>, py: Python) -> PyResult<Option<&PyAny>> {
        if slf.current >= slf.end {
            return Ok(None);
        }

        let current = slf.current;
        slf.current += 1;

        let future = future_into_py(py, async move {
            tokio::time::sleep(Duration::from_millis(10)).await;
            Ok(Python::with_gil(|py| current.into_py(py)))
        })?;

        Ok(Some(future))
    }
}
```

**Python usage**:
```python
async def main():
    async for i in my_module.AsyncRange(10):
        print(i)
```

### Backpressure

```rust
use tokio::sync::mpsc;

#[pyfunction]
fn with_backpressure(py: Python, data: Vec<i64>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let (tx, mut rx) = mpsc::channel(10);  // Buffer size = 10

        // Producer (respects backpressure)
        tokio::spawn(async move {
            for item in data {
                // Blocks when buffer full
                if tx.send(item).await.is_err() {
                    break;
                }
            }
        });

        // Consumer
        let mut results = Vec::new();
        while let Some(item) = rx.recv().await {
            // Simulate slow processing
            tokio::time::sleep(Duration::from_millis(50)).await;
            results.push(item * 2);
        }

        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}
```

---

## 9. Best Practices

### Async Guidelines

**✅ Do**:
- Release GIL before `.await` points
- Use `Python::with_gil()` to acquire GIL temporarily
- Handle cancellation gracefully
- Implement timeouts for network operations

**❌ Don't**:
- Hold GIL across `.await`
- Block async runtime with synchronous operations
- Panic in async code (propagate errors)
- Ignore backpressure in streams

### Embedding Guidelines

**✅ Do**:
- Call `pyo3::prepare_freethreaded_python()` once at startup
- Use `Python::with_gil()` for all Python operations
- Handle Python exceptions properly
- Configure Python path for module imports

**❌ Don't**:
- Initialize Python multiple times
- Access Python objects without GIL
- Leak Python exceptions as Rust panics
- Assume Python is available (check initialization)

### WASM Guidelines

**✅ Do**:
- Use conditional compilation (`#[cfg(target_arch = "wasm32")]`)
- Optimize for size (`opt-level = "z"`)
- Test in target environment (browser/WASI)
- Provide JavaScript wrappers for ergonomics

**❌ Don't**:
- Use threading in browser WASM
- Assume file system access
- Ignore memory limits
- Create large WASM bundles

---

## 10. Troubleshooting

### Async Deadlocks

**Symptom**: Program hangs

**Cause**: Holding GIL across `.await`

**Fix**:
```rust
// ❌ Bad
async fn deadlock_example() {
    Python::with_gil(|py| {
        // ... some async operation ...
        some_future.await;  // Deadlock!
    });
}

// ✅ Good
async fn no_deadlock() {
    let data = Python::with_gil(|py| {
        // Prepare data with GIL
        get_data(py)
    });

    // Await without GIL
    let result = some_future(data).await;

    Python::with_gil(|py| {
        // Use result with GIL
        process_result(py, result)
    });
}
```

### WASM Build Issues

**Symptom**: Compile errors for WASM target

**Common Causes**:
- Threading code
- File system operations
- Network operations (without fetch API)

**Fix**: Conditional compilation
```rust
#[cfg(not(target_arch = "wasm32"))]
use std::thread;

#[cfg(target_arch = "wasm32")]
fn alternative_for_wasm() {
    // WASM-compatible version
}
```

### Embedded Python Crashes

**Symptom**: Segmentation fault or crash

**Causes**:
- Accessing Python without GIL
- Python not initialized
- Lifetime issues with Python objects

**Fix**:
```rust
// Ensure initialization
pyo3::prepare_freethreaded_python();

// Always use with_gil
Python::with_gil(|py| {
    // Safe Python access
});
```

---

## Summary

**Key Takeaways**:

1. **Async**: Use `pyo3-asyncio` to bridge Rust futures and Python coroutines
2. **GIL**: Never hold GIL across `.await` points
3. **Embedding**: Initialize Python once, use `with_gil()` for access
4. **WASM**: Use conditional compilation, optimize for size
5. **Pyodide**: Full Python in browser with NumPy support
6. **WASI**: Server-side WASM with file system access
7. **Streams**: Handle backpressure and cancellation properly

**Development Workflow**:
1. Start with async/await patterns
2. Test with Tokio runtime integration
3. Add WASM targets conditionally
4. Profile and optimize bundle size
5. Test in target environments

---

**End of Reference** | For examples, see `examples/` directory | For tools, see `scripts/`
