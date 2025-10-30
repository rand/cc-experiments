# PyO3 Async, Embedded Python & WASM Examples

Progressive examples demonstrating async Python integration, embedded interpreters, and WebAssembly compilation with PyO3.

## Overview

These 10 examples progress from beginner to advanced concepts, demonstrating real-world patterns for building async Python extensions, embedding Python in Rust applications, and compiling to WASM.

## Examples Structure

### Beginner (01-03)

**01_async_basic/** - Basic Async Functions
- Simple async/await patterns with `future_into_py`
- GIL management in async contexts
- Error handling in async functions
- **Build**: `maturin develop`
- **Run**: `pytest test_example.py`

**02_tokio_runtime/** - Tokio Runtime Integration
- Multi-threaded runtime configuration
- Background task spawning
- Shared state with `Arc<Mutex>`
- Timeouts and channels
- **Build**: `maturin develop`
- **Run**: `pytest test_example.py`

**03_embedded_simple/** - Simple Embedded Python
- Embedding Python interpreter in Rust binaries
- Executing Python code from Rust
- Data exchange between Rust and Python
- Calling Python standard library
- **Build**: `cargo run`

### Intermediate (04-07)

**04_async_streams/** - Async Streams and Backpressure
- Stream transformations (map, filter, fold)
- Backpressure with bounded channels
- Stream chunking and merging
- Rate limiting
- **Build**: `maturin develop`
- **Run**: `pytest test_example.py`

**05_concurrent_tasks/** - Concurrent Task Management
- Parallel task execution with `join_all`
- Task racing with `select_all`
- Work-stealing pattern
- Semaphore-based concurrency limiting
- **Build**: `maturin develop`
- **Run**: `pytest test_example.py`

**06_plugin_system/** - Dynamic Plugin System
- Loading Python plugins from Rust
- Plugin management and isolation
- Dynamic code execution
- Plugin lifecycle management
- **Build**: `cargo run`

**07_event_loop/** - Custom Event Loop
- Pub/sub messaging pattern
- Task scheduling
- Event-driven architecture
- Broadcast channels
- **Build**: `maturin develop`
- **Run**: `pytest test_example.py`

### Advanced (08-10)

**08_wasm_basic/** - WASM Compilation
- Dual-target compilation (WASM + Python)
- Conditional compilation with `cfg`
- wasm-bindgen integration
- Size optimization
- **Build WASM**: `wasm-pack build --target web`
- **Build Python**: `maturin develop`

**09_async_io/** - Async File and Network I/O
- Async file operations with tokio::fs
- Async HTTP requests with reqwest
- Batch operations
- Directory operations
- **Build**: `maturin develop`
- **Run**: `pytest test_example.py`

**10_production_service/** - Production-Ready Service
- Connection pooling and rate limiting
- Request statistics and monitoring
- Health checks
- Error handling and recovery
- Thread-safe state management
- **Build**: `maturin develop`
- **Run**: `pytest test_example.py`

## Prerequisites

### System Requirements

```bash
# Rust with WASM targets
rustup target add wasm32-unknown-unknown
rustup target add wasm32-wasi

# Python 3.8+
python --version

# Build tools
pip install maturin
cargo install wasm-pack  # For WASM examples
```

### Dependencies

Each example has its own `Cargo.toml` with specific dependencies. Common dependencies:
- `pyo3`: PyO3 bindings
- `pyo3-asyncio`: Async integration
- `tokio`: Async runtime
- `wasm-bindgen`: WASM bindings (WASM examples)

## Building Examples

### Python Extensions (01, 02, 04, 05, 07, 09, 10)

```bash
cd <example_directory>
maturin develop           # Development build
maturin build --release   # Production build
```

### Rust Binaries (03, 06)

```bash
cd <example_directory>
cargo run                 # Run directly
cargo build --release     # Build binary
```

### WASM (08)

```bash
cd 08_wasm_basic

# For browser
wasm-pack build --target web

# For Python
maturin develop
```

## Testing

Each example includes tests:

```bash
# Python tests
pytest test_example.py

# Run example standalone
python test_example.py

# Rust tests (where applicable)
cargo test
```

## Learning Path

**Recommended order**:

1. Start with **01_async_basic** to understand async fundamentals
2. Progress to **02_tokio_runtime** for runtime management
3. Explore **03_embedded_simple** to learn embedding
4. Study **04_async_streams** for stream processing
5. Master **05_concurrent_tasks** for parallelism
6. Build **06_plugin_system** for dynamic loading
7. Implement **07_event_loop** for event-driven patterns
8. Compile **08_wasm_basic** for WASM targets
9. Handle **09_async_io** for I/O operations
10. Deploy **10_production_service** for production use

## Key Patterns

### Async Pattern
```rust
#[pyfunction]
fn async_function(py: Python) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        // Async Rust code
        let result = some_async_operation().await;
        Ok(Python::with_gil(|py| result.into_py(py)))
    })
}
```

### Embedding Pattern
```rust
fn main() -> PyResult<()> {
    pyo3::prepare_freethreaded_python();
    Python::with_gil(|py| {
        py.run("print('Hello from Python!')", None, None)?;
        Ok(())
    })
}
```

### WASM Pattern
```rust
#[wasm_bindgen]
pub fn process_data(data: Vec<f64>) -> Vec<f64> {
    data.iter().map(|x| x * 2.0).collect()
}

#[cfg(not(target_arch = "wasm32"))]
#[pyfunction]
fn py_process_data(data: Vec<f64>) -> Vec<f64> {
    process_data(data)
}
```

## Common Issues

### GIL Deadlocks
- Never hold GIL across `.await` points
- Use `Python::with_gil()` to acquire GIL temporarily

### WASM Limitations
- No threading in browser WASM
- Limited file system access
- Use conditional compilation for platform-specific code

### Performance
- Use multi-threaded runtime for CPU-bound work
- Implement backpressure for stream processing
- Profile with `tokio-console`

## File Structure

Each example contains:
```
<example_name>/
├── src/
│   └── lib.rs (or main.rs)
├── Cargo.toml
├── pyproject.toml
├── test_example.py
└── README.md
```

## Contributing

When adding examples:
1. Follow the existing structure
2. Include comprehensive README
3. Add tests with pytest
4. Document key patterns
5. Keep examples focused (150-300 lines)

## Resources

- [PyO3 Documentation](https://pyo3.rs/)
- [pyo3-asyncio Documentation](https://docs.rs/pyo3-asyncio/)
- [Tokio Guide](https://tokio.rs/tokio/tutorial)
- [wasm-bindgen Book](https://rustwasm.github.io/docs/wasm-bindgen/)
- [Parent Skill: pyo3-async-embedded-wasm](../../pyo3-async-embedded-wasm.md)

---

**Total Examples**: 10
**Difficulty Levels**: Beginner (3), Intermediate (4), Advanced (3)
**Build Systems**: maturin (7), cargo (3)
**Estimated Learning Time**: 15-20 hours
