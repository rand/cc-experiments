# Rust Skills

## Category Overview

**Total Skills**: 19
**Category**: rust
**Focus**: PyO3 (Rust-Python bindings) for high-performance Python extensions, including comprehensive DSPy integration with 36 production-ready examples

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

### pyo3-testing-debugging.md
**Description**: PyO3 testing and quality assurance including cargo test integration, pytest fixtures, property-based testing, fuzzing (cargo-fuzz), sanitizers (ASAN/MSAN/TSAN), mutation testing, and CI/CD pipelines

**Load this skill**:
```bash
cat skills/rust/pyo3-testing-debugging.md
```

---

### pyo3-data-science.md
**Description**: PyO3 for data science and ML including numpy integration, custom ufuncs, Polars DataFrames, Arrow/Parquet streaming, ONNX Runtime, PyTorch (tch-rs), Dask integration, and distributed computing

**Load this skill**:
```bash
cat skills/rust/pyo3-data-science.md
```

---

### pyo3-dspy-agents.md
**Description**: Building ReAct agents with DSPy from Rust - tool use, memory management, state persistence, error recovery, tool execution from Rust, and multi-step reasoning patterns

**Load this skill**:
```bash
cat skills/rust/pyo3-dspy-agents.md
```

---

### pyo3-dspy-async-streaming.md
**Description**: Async LM calls and streaming with DSPy from Rust - Tokio/asyncio integration, streaming predictions, concurrent LM calls, backpressure handling, cancellation, timeouts, and WebSocket patterns

**Load this skill**:
```bash
cat skills/rust/pyo3-dspy-async-streaming.md
```

---

### pyo3-dspy-fundamentals.md
**Description**: DSPy fundamentals from Rust - environment setup, LM configuration (OpenAI/Anthropic/Cohere/Ollama), calling DSPy modules (Predict/ChainOfThought/ReAct), prediction handling, error propagation, GIL management, and production patterns

**Load this skill**:
```bash
cat skills/rust/pyo3-dspy-fundamentals.md
```

---

### pyo3-dspy-optimization.md
**Description**: DSPy optimization workflows from Rust - running teleprompters (BootstrapFewShot/MIPROv2/COPRO), compiled model management, versioning, evaluation, A/B testing, and deployment pipelines

**Load this skill**:
```bash
cat skills/rust/pyo3-dspy-optimization.md
```

---

### pyo3-dspy-production.md
**Description**: Production DSPy deployment from Rust - multi-level caching (memory/Redis), circuit breakers, Prometheus metrics, structured logging, cost tracking, rate limiting, and A/B testing infrastructure

**Load this skill**:
```bash
cat skills/rust/pyo3-dspy-production.md
```

---

### pyo3-dspy-rag-pipelines.md
**Description**: RAG pipelines with DSPy from Rust - ChromaDB/Qdrant/Pinecone integration, retrieval modules, context management, hybrid search, reranking, and production RAG architectures

**Load this skill**:
```bash
cat skills/rust/pyo3-dspy-rag-pipelines.md
```

---

### pyo3-dspy-type-system.md
**Description**: Type-safe DSPy from Rust - signature type mapping (Python ↔ Rust), field extraction/validation, Pydantic integration with serde, custom types, compile-time type safety, and code generation

**Load this skill**:
```bash
cat skills/rust/pyo3-dspy-type-system.md
```

---

### pyo3-collections-iterators (Level 3 Resources only)
**Description**: PyO3 collections and iterators including iterator protocols (__iter__/__next__), collection conversions (Vec/HashMap/HashSet ↔ Python), sequence protocol implementation, lazy iterators, bidirectional iteration, custom collections, iterator combinators, streaming data, parallel iteration, and production pipelines

**Resources**:
```bash
ls skills/rust/pyo3-collections-iterators/resources/examples/
```

---

### pyo3-modules-functions-errors (Level 3 Resources only)
**Description**: PyO3 modules, functions, and error handling including module creation, function export, argument handling, submodules, custom exceptions, function overloading, module constants, callback functions, error hierarchies, and production API design

**Resources**:
```bash
ls skills/rust/pyo3-modules-functions-errors/resources/examples/
```

---

### pyo3-web-frameworks.md
**Description**: PyO3 for web services and system integration including systemd service integration, IPC (Unix sockets), gRPC with tonic, HTTP clients/servers, middleware patterns, and async web frameworks

**Load this skill**:
```bash
cat skills/rust/pyo3-web-frameworks.md
```

---

### pyo3-cli-tools.md
**Description**: PyO3 for CLI tools and embedding including pyo3-ffi for embedding Python interpreters, dynamic plugin loading, multi-interpreter applications, runtime isolation, plugin SDK design, and distribution strategies

**Load this skill**:
```bash
cat skills/rust/pyo3-cli-tools.md
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
# ... and 16 more
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
7. pyo3-testing-debugging → Testing, fuzzing, sanitizers, CI

**Application Domains** (Skills 8-12):
8. pyo3-data-science → numpy, Polars, ONNX, PyTorch, Dask
9. pyo3-collections-iterators → Iterator protocols, collections, streaming (Level 3 only, 10 examples)
10. pyo3-modules-functions-errors → Module structure, error handling (Level 3 only, 10 examples)
11. pyo3-web-frameworks → systemd, IPC, gRPC, web frameworks
12. pyo3-cli-tools → Embedded interpreters, plugin SDKs

**DSPy Integration** (Skills 13-19 - 36 production examples total):
13. pyo3-dspy-fundamentals → Setup, LM config, basic module calls (6 examples)
14. pyo3-dspy-type-system → Type-safe signatures, Pydantic integration (6 examples)
15. pyo3-dspy-rag-pipelines → RAG with vector DBs, retrieval, reranking (8 examples)
16. pyo3-dspy-agents → ReAct agents, tools, memory, multi-step reasoning (7 examples)
17. pyo3-dspy-async-streaming → Async LM calls, streaming, Tokio integration (7 examples)
18. pyo3-dspy-production → Caching, monitoring, circuit breakers, deployment (6 examples)
19. pyo3-dspy-optimization → Teleprompters, model management, A/B testing (6 examples)
