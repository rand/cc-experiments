---
name: pyo3-async-embedded-wasm
description: "Master async Python integration with Tokio, embedded Python interpreters, and WASM compilation with PyO3. Build async extensions, embed Python in Rust applications, and compile for browser/WASI environments."
globs: ["**/*.rs", "**/*.py", "**/Cargo.toml", "**/*.wasm"]
---

# PyO3 Async, Embedded Python & WASM

Master building async Python extensions with Tokio integration, embedding Python interpreters in Rust applications, and compiling PyO3 code to WebAssembly for browser and WASI environments.

## Prerequisites

**Required Knowledge**:
- PyO3 fundamentals (skill: pyo3-fundamentals)
- Rust async/await and Tokio basics
- Python asyncio and async/await
- Basic understanding of WASM and browser execution

**Environment**:
```bash
# Rust with wasm32 targets
rustup target add wasm32-unknown-unknown
rustup target add wasm32-wasi

# Python 3.8+ with asyncio
python --version

# WASM tools
cargo install wasm-pack
cargo install wasm-bindgen-cli
npm install -g pyodide

# Development dependencies
cargo add pyo3 --features extension-module
cargo add tokio --features full
cargo add pyo3-asyncio --features tokio-runtime
cargo add wasm-bindgen
```

## Learning Path

### 1. Async Fundamentals

**Python asyncio Integration**:
```rust
use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;

#[pyfunction]
fn async_operation(py: Python) -> PyResult<&PyAny> {
    future_into_py(py, async {
        // Async Rust code
        tokio::time::sleep(Duration::from_secs(1)).await;
        Ok(Python::with_gil(|py| "Done".into_py(py)))
    })
}
```

**Key Concepts**:
- Bridging Rust async and Python asyncio
- Runtime integration (Tokio ↔ asyncio)
- GIL management in async contexts
- Async lifetimes and PyO3

**Patterns**:
- Convert Rust futures to Python coroutines
- Call Python async functions from Rust
- Concurrent async operations
- Proper error propagation

### 2. Tokio Integration

**Tokio Runtime Setup**:
```rust
use pyo3_asyncio::tokio::run;

#[pymodule]
fn my_module(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(async_fn, m)?)?;
    Ok(())
}

#[pyfunction]
fn async_fn(py: Python) -> PyResult<&PyAny> {
    future_into_py(py, async {
        // Tokio async code here
        Ok(())
    })
}
```

**Runtime Management**:
- Single vs multi-threaded runtime
- Runtime configuration for PyO3
- Spawning tasks from Python
- Cleanup and shutdown

**Async Patterns**:
- Concurrent I/O operations
- Timeout handling
- Cancellation support
- Backpressure management

### 3. Embedded Python

**Embedding Python in Rust**:
```rust
use pyo3::prelude::*;
use pyo3::types::IntoPyDict;

fn main() -> PyResult<()> {
    Python::with_gil(|py| {
        let sys = py.import("sys")?;
        let version: String = sys.getattr("version")?.extract()?;
        println!("Python version: {}", version);

        // Execute Python code
        let locals = [("x", 10)].into_py_dict(py);
        py.run("print(x * 2)", None, Some(locals))?;

        Ok(())
    })
}
```

**Use Cases**:
- Plugin systems with Python
- Configuration with Python scripts
- Data processing pipelines
- Testing Rust code with Python

**Interpreter Management**:
- Initialization and finalization
- Multiple interpreters
- Module path configuration
- Extension module loading

### 4. WASM Compilation

**Building for WASM**:
```toml
[lib]
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
wasm-bindgen = "0.2"

[profile.release]
opt-level = "z"
lto = true
```

**Compilation**:
```bash
# For browser (wasm32-unknown-unknown)
wasm-pack build --target web

# For WASI (wasm32-wasi)
cargo build --target wasm32-wasi --release
```

**Limitations**:
- No threading in browser WASM
- Limited file system access
- Memory constraints
- Import restrictions

### 5. Pyodide Integration

**Running in Browser**:
```javascript
import { loadPyodide } from 'pyodide';

async function main() {
    let pyodide = await loadPyodide();

    // Load custom WASM module
    await pyodide.loadPackage('my-module.wasm');

    // Use from Python
    pyodide.runPython(`
        import my_module
        result = my_module.process_data([1, 2, 3, 4, 5])
        print(result)
    `);
}
```

**Features**:
- Browser-based Python execution
- NumPy and scientific stack
- Rust extensions compiled to WASM
- JavaScript interop

**Challenges**:
- Bundle size optimization
- Loading time
- Memory management
- Browser compatibility

### 6. WASI (WebAssembly System Interface)

**Server-side WASM**:
```rust
// WASI-compatible code
use std::fs;

#[pyfunction]
fn read_file(path: String) -> PyResult<String> {
    fs::read_to_string(path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
}
```

**Benefits**:
- Sandboxed execution
- Portable across platforms
- Security isolation
- Fast startup

**Use Cases**:
- Serverless functions
- Plugin sandboxing
- Portable CLI tools
- Edge computing

### 7. Async Streams

**Stream Processing**:
```rust
use tokio_stream::StreamExt;

#[pyfunction]
fn async_stream(py: Python) -> PyResult<&PyAny> {
    let stream = futures::stream::iter(0..10);

    pyo3_asyncio::tokio::future_into_py(py, async move {
        let results: Vec<_> = stream
            .map(|x| x * 2)
            .collect()
            .await;
        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}
```

**Patterns**:
- Async iterators for Python
- Backpressure handling
- Stream transformation
- Error handling in streams

### 8. Advanced Async Patterns

**Concurrent Operations**:
```rust
use futures::future::join_all;

#[pyfunction]
fn parallel_async_ops(py: Python, urls: Vec<String>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let futures = urls.into_iter().map(|url| fetch_url(url));
        let results = join_all(futures).await;
        Ok(Python::with_gil(|py| results.into_py(py)))
    })
}
```

**Timeouts and Cancellation**:
```rust
use tokio::time::{timeout, Duration};

#[pyfunction]
fn with_timeout(py: Python, seconds: u64) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        match timeout(Duration::from_secs(seconds), long_operation()).await {
            Ok(result) => Ok(result),
            Err(_) => Err(PyErr::new::<pyo3::exceptions::PyTimeoutError, _>(
                "Operation timed out"
            ))
        }
    })
}
```

## Common Patterns

### Async HTTP Client
```rust
use reqwest;

#[pyfunction]
fn fetch_url(py: Python, url: String) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        let response = reqwest::get(&url).await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                e.to_string()
            ))?;

        let body = response.text().await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                e.to_string()
            ))?;

        Ok(Python::with_gil(|py| body.into_py(py)))
    })
}
```

### Embedded Python Plugin System
```rust
struct PluginEngine {
    py: Python<'static>,
}

impl PluginEngine {
    fn new() -> PyResult<Self> {
        pyo3::prepare_freethreaded_python();
        let py = unsafe { Python::assume_gil_acquired() };
        Ok(Self { py })
    }

    fn load_plugin(&self, path: &str) -> PyResult<()> {
        let code = std::fs::read_to_string(path)?;
        self.py.run(&code, None, None)?;
        Ok(())
    }
}
```

### WASM-Compatible Module
```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn process_data(data: Vec<f64>) -> Vec<f64> {
    data.iter().map(|x| x * 2.0).collect()
}

// Also expose via PyO3 when not compiling to WASM
#[cfg(not(target_arch = "wasm32"))]
#[pyfunction]
fn process_data_py(data: Vec<f64>) -> Vec<f64> {
    process_data(data)
}
```

## WASM Best Practices

**Size Optimization**:
```toml
[profile.release]
opt-level = "z"         # Optimize for size
lto = true              # Link-time optimization
codegen-units = 1       # Better optimization
strip = true            # Strip symbols
```

**Conditional Compilation**:
```rust
#[cfg(target_arch = "wasm32")]
mod wasm_specific {
    // WASM-only code
}

#[cfg(not(target_arch = "wasm32"))]
mod native_specific {
    // Native-only code (e.g., threading)
}
```

**Memory Management**:
```rust
// Explicit memory management for WASM
#[wasm_bindgen]
pub struct WasmBuffer {
    data: Vec<u8>,
}

#[wasm_bindgen]
impl WasmBuffer {
    pub fn new(size: usize) -> Self {
        Self { data: vec![0; size] }
    }

    pub fn free(self) {
        // Explicit drop
    }
}
```

## Async Testing

**Test Framework**:
```rust
#[cfg(test)]
mod tests {
    use super::*;
    use tokio::test;

    #[tokio::test]
    async fn test_async_function() {
        let result = async_operation().await;
        assert!(result.is_ok());
    }
}
```

**Python Async Tests**:
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_extension():
    result = await my_module.async_operation()
    assert result == expected
```

## Resources

**In resources/ directory**:
- `REFERENCE.md`: Comprehensive async, embedded, and WASM guide
- `scripts/`:
  - `async_profiler.py`: Profile async operations and event loop
  - `embedding_helper.py`: Utilities for embedded Python scenarios
  - `wasm_builder.py`: Build and optimize WASM modules
- `examples/`:
  - `01_basic_async/`: Simple async function integration
  - `02_tokio_integration/`: Full Tokio runtime integration
  - `03_async_http/`: Async HTTP client example
  - `04_embedded_simple/`: Basic embedded Python interpreter
  - `05_embedded_plugins/`: Plugin system with Python
  - `06_wasm_browser/`: Browser WASM module
  - `07_wasm_wasi/`: WASI command-line tool
  - `08_pyodide_integration/`: Pyodide web application
  - `09_async_streams/`: Async stream processing
  - `10_production_async/`: Production-ready async service

**External Resources**:
- [pyo3-asyncio Documentation](https://docs.rs/pyo3-asyncio/)
- [Tokio Documentation](https://tokio.rs/)
- [Pyodide Documentation](https://pyodide.org/)
- [WASI Documentation](https://wasi.dev/)
- [wasm-bindgen Guide](https://rustwasm.github.io/docs/wasm-bindgen/)

## Anti-Patterns

**❌ Blocking in async context**:
```rust
// Bad: Blocks the async runtime
future_into_py(py, async {
    std::thread::sleep(Duration::from_secs(1));  // Blocks!
    Ok(())
})
```

**✅ Use async sleep**:
```rust
// Good: Non-blocking
future_into_py(py, async {
    tokio::time::sleep(Duration::from_secs(1)).await;
    Ok(())
})
```

**❌ Threading in WASM**:
```rust
// Bad: Won't work in WASM
#[pyfunction]
fn spawn_thread() {
    std::thread::spawn(|| {
        // This will panic in WASM!
    });
}
```

**✅ Conditional compilation**:
```rust
// Good: WASM-aware
#[pyfunction]
fn process() {
    #[cfg(not(target_arch = "wasm32"))]
    {
        // Use threading on native platforms
        std::thread::spawn(|| work());
    }

    #[cfg(target_arch = "wasm32")]
    {
        // Sequential processing in WASM
        work();
    }
}
```

**❌ Ignoring GIL in async**:
```rust
// Bad: GIL lifetime issues
async fn process() {
    let py = Python::acquire_gil();  // Don't hold GIL across await!
    some_async_op().await;
}
```

**✅ Acquire GIL when needed**:
```rust
// Good: Acquire GIL only when accessing Python objects
async fn process() {
    let result = some_async_op().await;
    Python::with_gil(|py| {
        // Use py here
    });
}
```

## Performance Considerations

**Async Overhead**:
- Future creation cost
- Context switching overhead
- GIL acquisition in async contexts
- Memory usage of futures

**WASM Constraints**:
- Single-threaded execution
- Limited memory (can grow)
- Slower than native code
- Bundle size impacts load time

**Optimization Strategies**:
- Minimize GIL acquisitions in async code
- Use efficient serialization for WASM
- Batch operations when possible
- Profile async code with `tokio-console`

## Related Skills

- **pyo3-performance-gil-parallel**: Complementary parallelism strategies
- **pyo3-fundamentals**: Core PyO3 concepts
- **pyo3-web-services-systems**: Building async web services
- **pyo3-cli-embedding-plugins**: Advanced embedding patterns

## Expected Outcomes

After mastering this skill, you will be able to:

1. **Build async Python extensions** with Tokio integration
2. **Embed Python interpreters** in Rust applications
3. **Compile PyO3 code to WASM** for browser and WASI
4. **Integrate with Pyodide** for browser-based Python
5. **Handle async streams** and backpressure correctly
6. **Manage GIL lifetime** in async contexts
7. **Build production async services** with proper error handling

## Success Metrics

- Clean integration of Rust async and Python asyncio
- Proper GIL management (no deadlocks or lifetime issues)
- Working WASM builds with optimized bundle sizes
- Zero panics in embedded Python scenarios
- Correct cancellation and timeout handling

---

**Skill Level**: Advanced
**Estimated Learning Time**: 10-12 hours (study) + 25-35 hours (practice)
**Prerequisites**: pyo3-fundamentals, Rust async/await, Python asyncio
**Next Steps**: pyo3-web-services-systems, pyo3-cli-embedding-plugins
