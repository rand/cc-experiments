# Rust Skills

## Category Overview

**Total Skills**: 10
**Category**: rust
**Focus**: PyO3 (Rust-Python bindings) for high-performance Python extensions

## Skills in This Category

### pyo3-fundamentals.md
**Description**: PyO3 fundamentals including project setup, type conversion basics, error handling, Python/Rust FFI, memory safety, cross-language debugging, and memory profiling

**Load this skill**:
```bash
cat skills/rust/pyo3-fundamentals.md
```

---

### pyo3-classes-modules.md
**Description**: PyO3 classes and modules including #[pyclass], #[pymethods], class hierarchies, inheritance, Python protocols, module organization, plugin architecture, and hot-reload patterns

**Load this skill**:
```bash
cat skills/rust/pyo3-classes-modules.md
```

---

### pyo3-type-conversion-advanced.md
**Description**: Advanced PyO3 type conversion including zero-copy operations with numpy arrays, Arrow/Parquet integration, custom conversion protocols, buffer protocol, sequence/mapping protocols, and iterator patterns

**Load this skill**:
```bash
cat skills/rust/pyo3-type-conversion-advanced.md
```

---

### pyo3-performance-gil-parallel.md
**Description**: PyO3 performance optimization including GIL management, parallel execution patterns, sub-interpreters (PEP 554), free-threaded Python (PEP 703/nogil), custom allocators, and lock-free data structures

**Load this skill**:
```bash
cat skills/rust/pyo3-performance-gil-parallel.md
```

---

### pyo3-async-embedded-wasm.md
**Description**: PyO3 async integration and embedded Python including pyo3-asyncio, tokio/asyncio bridges, embedded Python in Rust binaries, WASM compilation with Pyodide, WASI support, and browser execution

**Load this skill**:
```bash
cat skills/rust/pyo3-async-embedded-wasm.md
```

---

### pyo3-packaging-distribution.md
**Description**: PyO3 packaging and distribution including maturin workflows, setuptools-rust, wheel building, cross-compilation, static linking, dependency vendoring, and PyPI publishing

**Load this skill**:
```bash
cat skills/rust/pyo3-packaging-distribution.md
```

---

### pyo3-testing-quality-ci.md
**Description**: PyO3 testing and quality assurance including cargo test integration, pytest fixtures, property-based testing, fuzzing (cargo-fuzz), sanitizers (ASAN/MSAN/TSAN), mutation testing, and CI/CD pipelines

**Load this skill**:
```bash
cat skills/rust/pyo3-testing-quality-ci.md
```

---

### pyo3-data-science-ml.md
**Description**: PyO3 for data science and ML including numpy integration, custom ufuncs, Polars DataFrames, Arrow/Parquet streaming, ONNX Runtime, PyTorch (tch-rs), Dask integration, and distributed computing

**Load this skill**:
```bash
cat skills/rust/pyo3-data-science-ml.md
```

---

### pyo3-web-services-systems.md
**Description**: PyO3 for web services and system integration including systemd service integration, IPC (Unix sockets), gRPC with tonic, HTTP clients/servers, middleware patterns, and async web frameworks

**Load this skill**:
```bash
cat skills/rust/pyo3-web-services-systems.md
```

---

### pyo3-cli-embedding-plugins.md
**Description**: PyO3 for CLI tools and embedding including pyo3-ffi for embedding Python interpreters, dynamic plugin loading, multi-interpreter applications, runtime isolation, plugin SDK design, and distribution strategies

**Load this skill**:
```bash
cat skills/rust/pyo3-cli-embedding-plugins.md
```

---

## Loading All Skills

```bash
# List all skills in this category
ls skills/rust/*.md

# Load specific skills
cat skills/rust/pyo3-fundamentals.md
cat skills/rust/pyo3-classes-modules.md
cat skills/rust/pyo3-type-conversion-advanced.md
# ... and 7 more
```

## Related Categories

See `skills/README.md` for the complete catalog of all categories and gateway skills.

---

**Browse**: This index provides a quick reference for PyO3 (Rust-Python bindings) skills covering fundamentals through advanced topics like WASM compilation, embedded Python, ML integration, and system services.

## Progressive Learning Path

**Foundation** (Skills 1-3):
1. pyo3-fundamentals → Basic project setup, type conversion, FFI
2. pyo3-classes-modules → Python classes, modules, plugins
3. pyo3-type-conversion-advanced → Zero-copy, numpy, Arrow

**Performance & Concurrency** (Skills 4-5):
4. pyo3-performance-gil-parallel → GIL, sub-interpreters, nogil
5. pyo3-async-embedded-wasm → Async, embedding, WASM

**Production & Distribution** (Skills 6-7):
6. pyo3-packaging-distribution → maturin, wheels, cross-compilation
7. pyo3-testing-quality-ci → Testing, fuzzing, sanitizers, CI

**Application Domains** (Skills 8-10):
8. pyo3-data-science-ml → numpy, Polars, ONNX, PyTorch, Dask
9. pyo3-web-services-systems → systemd, IPC, gRPC, web frameworks
10. pyo3-cli-embedding-plugins → Embedded interpreters, plugin SDKs
