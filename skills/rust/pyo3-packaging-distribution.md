---
name: pyo3-packaging-distribution
description: PyO3 packaging and distribution using maturin, setuptools-rust, wheel building, cross-compilation
skill_id: rust-pyo3-packaging-distribution
title: PyO3 Packaging and Distribution
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
  - packaging
  - maturin
  - pypi
  - wheels
  - distribution
  - cross-compilation
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Master maturin build system for PyO3 projects
  - Understand Python packaging standards (PEP 517, 621, 660)
  - Build and distribute wheels for multiple platforms
  - Configure cross-compilation for target platforms
  - Publish packages to PyPI and private repositories
  - Implement versioning and dependency management
  - Set up CI/CD pipelines for automated releases
  - Handle native dependencies and platform-specific code
related_skills:
  - rust-pyo3-testing-debugging
  - devops-ci-cd
  - containers-docker
---

# PyO3 Packaging and Distribution

## Overview

Master the complete lifecycle of packaging and distributing PyO3 extensions, from local development builds to production releases on PyPI. Learn maturin's build system, cross-compilation strategies, wheel generation, and CI/CD automation for reliable multi-platform distribution.

## Prerequisites

- **Required**: PyO3 basics, Rust toolchain, Python packaging fundamentals
- **Recommended**: CI/CD experience, Docker familiarity, understanding of platform ABIs
- **Tools**: maturin, cargo, pip, twine, cibuildwheel

## Learning Path

### 1. Maturin Build System Fundamentals

**maturin** is the standard build tool for PyO3 projects, implementing PEP 517 (build backend interface).

#### Setup and Configuration

```toml
# pyproject.toml - Modern Python packaging
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[project]
name = "my-extension"
version = "0.1.0"
description = "Fast data processing extension"
requires-python = ">=3.8"
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Rust",
    "License :: OSI Approved :: MIT License",
]
dependencies = [
    "numpy>=1.20",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "mypy>=1.0"]

[tool.maturin]
python-source = "python"
module-name = "my_extension._core"
features = ["pyo3/extension-module"]
```

```toml
# Cargo.toml - Rust project configuration
[package]
name = "my-extension"
version = "0.1.0"
edition = "2021"

[lib]
name = "my_extension"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }

[profile.release]
opt-level = 3
lto = "fat"
codegen-units = 1
strip = true
```

#### Build Commands

```bash
# Development build (debug, unoptimized)
maturin develop

# Development with editable install
maturin develop --uv

# Release build (optimized)
maturin build --release

# Build wheel for distribution
maturin build --release --out dist/

# Build and install in current environment
maturin develop --release
```

### 2. Project Structure and Layout

#### Mixed Python/Rust Layout

```
my-extension/
├── Cargo.toml              # Rust configuration
├── pyproject.toml          # Python packaging config
├── README.md
├── LICENSE
├── src/
│   └── lib.rs             # Rust implementation
├── python/
│   └── my_extension/
│       ├── __init__.py    # Python wrapper/API
│       └── utils.py       # Pure Python utilities
├── tests/
│   ├── test_basic.py
│   └── test_integration.py
└── examples/
    └── demo.py
```

**`src/lib.rs`**:
```rust
use pyo3::prelude::*;

#[pyfunction]
fn fast_sum(numbers: Vec<f64>) -> f64 {
    numbers.iter().sum()
}

#[pymodule]
fn _core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fast_sum, m)?)?;
    Ok(())
}
```

**`python/my_extension/__init__.py`**:
```python
"""My Extension - Fast data processing."""
from my_extension._core import fast_sum

__version__ = "0.1.0"
__all__ = ["fast_sum", "process_data"]

def process_data(data: list[float]) -> dict:
    """High-level API wrapping Rust implementation."""
    return {
        "sum": fast_sum(data),
        "count": len(data),
        "average": fast_sum(data) / len(data) if data else 0
    }
```

### 3. Platform-Specific Builds

#### Targeting Multiple Platforms

```bash
# Build for current platform
maturin build --release

# Target specific platform (requires cross-compilation setup)
maturin build --release --target x86_64-unknown-linux-gnu
maturin build --release --target aarch64-unknown-linux-gnu
maturin build --release --target x86_64-apple-darwin
maturin build --release --target aarch64-apple-darwin
maturin build --release --target x86_64-pc-windows-msvc
```

#### Cross-Compilation with Docker

```bash
# Use manylinux for Linux wheels
maturin build --release --manylinux 2_28

# Use zig for cross-compilation
maturin build --release --zig
```

**`Dockerfile.build`**:
```dockerfile
FROM quay.io/pypa/manylinux_2_28_x86_64

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

RUN pip install maturin

WORKDIR /io

CMD ["maturin", "build", "--release", "--out", "dist/"]
```

```bash
# Build wheels in container
docker run --rm -v $(pwd):/io my-extension-builder
```

### 4. Dependency Management

#### Rust Dependencies

```toml
# Cargo.toml
[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
numpy = "0.20"
ndarray = "0.15"
rayon = "1.7"

# Optional features
[features]
default = []
parallel = ["rayon"]
```

#### Python Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "numpy>=1.20,<2.0",
]

[project.optional-dependencies]
parallel = ["scipy>=1.9"]
dev = [
    "pytest>=7.0",
    "pytest-benchmark>=4.0",
    "mypy>=1.0",
]
```

#### Native System Dependencies

```toml
# pyproject.toml - Document system requirements
[tool.maturin]
# Link against system libraries
rustc-args = ["-C", "link-arg=-lblas"]

[project.readme]
text = """
# Installation

## System Requirements
- BLAS/LAPACK libraries
- On Ubuntu: `apt-get install libblas-dev liblapack-dev`
- On macOS: Provided by Accelerate framework
- On Windows: Install Intel MKL or OpenBLAS
"""
```

### 5. Versioning and Metadata

#### Single Source of Truth

**Option 1: Cargo.toml as source**:
```toml
# pyproject.toml
[project]
name = "my-extension"
dynamic = ["version"]

[tool.maturin]
python-source = "python"
```

```toml
# Cargo.toml
[package]
version = "0.1.0"  # Single source of truth
```

**Option 2: Git tags as source**:
```toml
# pyproject.toml
[project]
dynamic = ["version"]

[tool.maturin]
version-from-git = true
```

```bash
# Tag and build
git tag v0.1.0
maturin build --release
```

#### Runtime Version Access

```rust
// src/lib.rs
const VERSION: &str = env!("CARGO_PKG_VERSION");

#[pymodule]
fn _core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add("__version__", VERSION)?;
    Ok(())
}
```

```python
# python/my_extension/__init__.py
from my_extension._core import __version__

print(f"my-extension v{__version__}")
```

### 6. Publishing to PyPI

#### Preparation

```bash
# Install tools
pip install twine

# Build wheels for all platforms (using CI)
# See CI/CD section below

# Check wheel contents
unzip -l dist/my_extension-0.1.0-cp38-cp38-linux_x86_64.whl
```

#### Publishing

```bash
# Test on TestPyPI first
twine upload --repository testpypi dist/*

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ my-extension

# Publish to PyPI
twine upload dist/*
```

#### PyPI Configuration

```ini
# ~/.pypirc
[pypi]
username = __token__
password = pypi-AgEIcH...  # API token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEIcH...
```

### 7. CI/CD for Automated Releases

#### GitHub Actions Workflow

**`.github/workflows/release.yml`**:
```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  linux:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target: [x86_64, aarch64]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - name: Build wheels
        uses: PyO3/maturin-action@v1
        with:
          target: ${{ matrix.target }}
          args: --release --out dist --find-interpreter
          manylinux: auto
      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-linux-${{ matrix.target }}
          path: dist

  macos:
    runs-on: macos-latest
    strategy:
      matrix:
        target: [x86_64, aarch64]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - name: Build wheels
        uses: PyO3/maturin-action@v1
        with:
          target: ${{ matrix.target }}
          args: --release --out dist --find-interpreter
      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-macos-${{ matrix.target }}
          path: dist

  windows:
    runs-on: windows-latest
    strategy:
      matrix:
        target: [x64, x86]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
          architecture: ${{ matrix.target }}
      - name: Build wheels
        uses: PyO3/maturin-action@v1
        with:
          target: ${{ matrix.target }}
          args: --release --out dist --find-interpreter
      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-windows-${{ matrix.target }}
          path: dist

  release:
    name: Publish to PyPI
    runs-on: ubuntu-latest
    needs: [linux, macos, windows]
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: wheels-*
          path: dist
          merge-multiple: true
      - name: Publish to PyPI
        uses: PyO3/maturin-action@v1
        env:
          MATURIN_PYPI_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
        with:
          command: upload
          args: --skip-existing dist/*
```

### 8. Advanced: Custom Build Scripts

#### Build.rs Integration

```rust
// build.rs - Custom build logic
use std::env;

fn main() {
    // Conditional compilation
    if env::var("CARGO_FEATURE_PARALLEL").is_ok() {
        println!("cargo:rustc-cfg=feature=\"parallel\"");
    }

    // Link system libraries
    if cfg!(target_os = "linux") {
        println!("cargo:rustc-link-lib=blas");
        println!("cargo:rustc-link-lib=lapack");
    }

    // Platform-specific config
    let target = env::var("TARGET").unwrap();
    if target.contains("darwin") {
        println!("cargo:rustc-link-lib=framework=Accelerate");
    }
}
```

### 9. Private Package Distribution

#### Private PyPI Repository

```toml
# pyproject.toml
[project.urls]
repository = "https://github.com/org/my-extension"

[tool.maturin]
# Include only necessary files
include = ["LICENSE", "README.md", "src/**/*.rs"]
exclude = ["tests/**", "benchmarks/**"]
```

```bash
# Publish to private index
twine upload --repository-url https://pypi.company.com dist/*

# Install from private index
pip install --index-url https://pypi.company.com my-extension
```

#### Direct Installation from Git

```bash
# Install from git (requires Rust toolchain)
pip install git+https://github.com/org/my-extension.git

# Install specific version
pip install git+https://github.com/org/my-extension.git@v0.1.0
```

## Common Patterns

### Binary Stubs for Fast Imports

```python
# python/my_extension/__init__.pyi - Type stubs
def fast_sum(numbers: list[float]) -> float: ...
def process_data(data: list[float]) -> dict[str, float]: ...
```

### Feature Flags

```toml
# Cargo.toml
[features]
default = []
numpy = ["dep:numpy", "pyo3/numpy"]
parallel = ["rayon"]
all = ["numpy", "parallel"]
```

```rust
#[cfg(feature = "parallel")]
use rayon::prelude::*;

#[pyfunction]
fn process(data: Vec<f64>) -> Vec<f64> {
    #[cfg(feature = "parallel")]
    return data.par_iter().map(|x| x * 2.0).collect();

    #[cfg(not(feature = "parallel"))]
    return data.iter().map(|x| x * 2.0).collect();
}
```

### Platform Detection

```rust
use pyo3::prelude::*;

#[pyfunction]
fn platform_info() -> HashMap<&'static str, &'static str> {
    let mut info = HashMap::new();
    info.insert("os", env::consts::OS);
    info.insert("arch", env::consts::ARCH);
    info.insert("family", env::consts::FAMILY);
    info
}
```

## Anti-Patterns

### ❌ Incorrect: Hardcoded Paths

```toml
# pyproject.toml
[tool.maturin]
python-source = "/home/user/project/python"  # Absolute path
```

### ✅ Correct: Relative Paths

```toml
[tool.maturin]
python-source = "python"  # Relative to project root
```

### ❌ Incorrect: Missing manylinux

```bash
# Wheel only works on your specific Linux
maturin build --release
```

### ✅ Correct: Portable Linux Wheels

```bash
# Compatible with many Linux distributions
maturin build --release --manylinux 2_28
```

### ❌ Incorrect: Version Mismatch

```toml
# Cargo.toml
[package]
version = "0.1.0"
```

```python
# __init__.py
__version__ = "0.2.0"  # Out of sync!
```

### ✅ Correct: Single Source of Truth

```python
from my_extension._core import __version__  # From Rust
```

## Testing

See [pyo3-testing-debugging.md](pyo3-testing-debugging.md) for comprehensive testing strategies.

## Resources

### Tools
- **maturin**: Build tool for PyO3 projects
- **twine**: PyPI publishing tool
- **cibuildwheel**: Multi-platform wheel builder
- **auditwheel**: Linux wheel repair tool

### Documentation
- [Maturin Guide](https://www.maturin.rs/)
- [PyO3 User Guide - Building](https://pyo3.rs/latest/building-and-distribution)
- [Python Packaging User Guide](https://packaging.python.org/)
- [PEP 517 - Build Backend Interface](https://peps.python.org/pep-0517/)

### Related Skills
- [pyo3-testing-debugging.md](pyo3-testing-debugging.md)
- [../cicd/github-actions.md](../cicd/github-actions.md)

## Examples

See `resources/examples/` for:
1. Basic package setup
2. Mixed Python/Rust layout
3. Cross-compilation configuration
4. CI/CD pipelines
5. Private package distribution
6. Feature flag usage
7. Version management
8. manylinux builds
9. Platform-specific code
10. Advanced build customization

## Additional Resources

- **REFERENCE.md**: Comprehensive patterns and configurations
- **Scripts**:
  - `package_builder.py`: Build wheels for multiple platforms
  - `dependency_checker.py`: Validate dependencies and system requirements
  - `release_manager.py`: Automate version bumps and releases
