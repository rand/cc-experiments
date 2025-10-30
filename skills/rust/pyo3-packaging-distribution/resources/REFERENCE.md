# PyO3 Packaging & Distribution - Comprehensive Reference

Complete guide to packaging, building, and distributing PyO3 extensions using maturin, covering all platforms, CI/CD automation, and production deployment strategies.

**Version**: 1.0.0
**PyO3**: 0.20+
**Maturin**: 1.4+
**Python**: 3.8+
**Last Updated**: 2025-10-30

---

## Table of Contents

1. [Maturin Configuration](#1-maturin-configuration)
2. [Build Commands and Workflows](#2-build-commands-and-workflows)
3. [Dependency Management](#3-dependency-management)
4. [Platform-Specific Builds](#4-platform-specific-builds)
5. [Version Management](#5-version-management)
6. [PyPI Publishing](#6-pypi-publishing)
7. [CI/CD Automation](#7-cicd-automation)
8. [Advanced Build Customization](#8-advanced-build-customization)
9. [Distribution Strategies](#9-distribution-strategies)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Maturin Configuration

### What is Maturin?

**Maturin** is the official build tool for PyO3 extensions. It handles:
- Building Rust code into Python wheels
- Platform-specific compilation
- ABI compatibility
- Source distribution creation
- PyPI metadata generation

**Key Features**:
- Zero-configuration for simple projects
- Supports mixed Python/Rust layouts
- Multi-platform cross-compilation
- Integrates with PEP 517 build system
- Automatic manylinux compliance

### Basic pyproject.toml

```toml
# Minimal configuration
[build-system]
requires = ["maturin>=1.4,<2.0"]
build-backend = "maturin"

[project]
name = "my_extension"
version = "0.1.0"
description = "Fast Python extension in Rust"
requires-python = ">=3.8"
```

**Build Command**:
```bash
# Install in development mode
maturin develop

# Build wheel
maturin build --release
```

### Complete pyproject.toml Template

```toml
[build-system]
requires = ["maturin>=1.4,<2.0"]
build-backend = "maturin"

[project]
name = "my_extension"
version = "0.1.0"
description = "High-performance Python extension written in Rust"
readme = "README.md"
requires-python = ">=3.8"
license = { text = "MIT OR Apache-2.0" }
keywords = ["performance", "rust", "extension"]
authors = [
    { name = "Your Name", email = "your.email@example.com" }
]
maintainers = [
    { name = "Your Name", email = "your.email@example.com" }
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Rust",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
    "Operating System :: Microsoft :: Windows",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

dependencies = [
    "numpy>=1.20",
    "typing-extensions>=4.0; python_version < '3.11'",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-benchmark>=4.0",
    "mypy>=1.0",
    "ruff>=0.1",
]
test = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "hypothesis>=6.0",
]
docs = [
    "sphinx>=5.0",
    "sphinx-rtd-theme>=1.0",
]

[project.urls]
Homepage = "https://github.com/username/my_extension"
Documentation = "https://my_extension.readthedocs.io"
Repository = "https://github.com/username/my_extension.git"
Issues = "https://github.com/username/my_extension/issues"
Changelog = "https://github.com/username/my_extension/blob/main/CHANGELOG.md"

[tool.maturin]
# Python source directory (for mixed Rust/Python packages)
python-source = "python"

# Include additional files in wheel
include = ["LICENSE", "README.md", "CHANGELOG.md"]

# Build options
features = ["pyo3/extension-module"]
strip = true  # Strip debug symbols in release builds

# Platform-specific settings
[tool.maturin.target.x86_64-unknown-linux-gnu]
rustflags = ["-C", "link-arg=-s"]

[tool.maturin.target.x86_64-apple-darwin]
rustflags = ["-C", "link-arg=-Wl,-dead_strip"]

[tool.maturin.target.aarch64-apple-darwin]
rustflags = ["-C", "link-arg=-Wl,-dead_strip"]

[tool.maturin.target.x86_64-pc-windows-msvc]
rustflags = ["/LTCG"]  # Link-time code generation
```

### Cargo.toml Configuration

```toml
[package]
name = "my_extension"
version = "0.1.0"
edition = "2021"
rust-version = "1.70"

[lib]
# Library name (Python will import this name)
name = "my_extension"
# Build as dynamic library for Python
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
numpy = "0.20"
ndarray = "0.15"

# Optional features
rayon = { version = "1.8", optional = true }
serde = { version = "1.0", features = ["derive"], optional = true }

[dev-dependencies]
pyo3 = { version = "0.20", features = ["auto-initialize"] }
criterion = "0.5"

[features]
default = []
parallel = ["rayon"]
serialization = ["serde", "pyo3/serde"]

[profile.release]
# Optimize for size and speed
opt-level = 3
lto = "fat"
codegen-units = 1
strip = true

[profile.release-with-debug]
inherits = "release"
strip = false
debug = true
```

### Project Layout: Pure Rust Extension

```
my_extension/
├── Cargo.toml
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── lib.rs          # Rust source
├── tests/
│   ├── test_basic.py
│   └── test_perf.py
└── benches/
    └── benchmark.rs
```

**src/lib.rs**:
```rust
use pyo3::prelude::*;

#[pyfunction]
fn add(a: i64, b: i64) -> i64 {
    a + b
}

#[pymodule]
fn my_extension(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(add, m)?)?;
    Ok(())
}
```

### Project Layout: Mixed Python/Rust

```
my_extension/
├── Cargo.toml
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── lib.rs              # Rust implementation
├── python/
│   └── my_extension/
│       ├── __init__.py     # Python API layer
│       ├── utils.py        # Pure Python utilities
│       └── _core.pyi       # Type stubs for Rust module
└── tests/
    ├── test_python.py
    └── test_rust.py
```

**pyproject.toml** (add):
```toml
[tool.maturin]
python-source = "python"
module-name = "my_extension._core"
```

**python/my_extension/__init__.py**:
```python
"""My Extension - High-performance operations in Rust."""

from my_extension._core import add, multiply  # Import Rust functions

__version__ = "0.1.0"
__all__ = ["add", "multiply", "BatchProcessor"]

class BatchProcessor:
    """Pure Python wrapper around Rust core."""

    def __init__(self, size: int):
        self.size = size

    def process(self, data: list[int]) -> int:
        """Process data in batches using Rust."""
        return sum(add(x, self.size) for x in data)
```

**python/my_extension/_core.pyi**:
```python
"""Type stubs for Rust core module."""

def add(a: int, b: int) -> int:
    """Add two integers."""
    ...

def multiply(a: int, b: int) -> int:
    """Multiply two integers."""
    ...
```

### Configuration for Multiple Binary Modules

For packages with multiple Rust modules:

**Cargo.toml**:
```toml
[workspace]
members = ["core", "utils", "io"]

[workspace.dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
```

**core/Cargo.toml**:
```toml
[package]
name = "my_extension_core"
version = "0.1.0"
edition = "2021"

[lib]
name = "_core"
crate-type = ["cdylib"]

[dependencies]
pyo3.workspace = true
```

**utils/Cargo.toml**:
```toml
[package]
name = "my_extension_utils"
version = "0.1.0"
edition = "2021"

[lib]
name = "_utils"
crate-type = ["cdylib"]

[dependencies]
pyo3.workspace = true
my_extension_core = { path = "../core" }
```

**pyproject.toml**:
```toml
[tool.maturin]
python-source = "python"

[[tool.maturin.module]]
name = "my_extension._core"
path = "core"

[[tool.maturin.module]]
name = "my_extension._utils"
path = "utils"
```

### Source Distribution Configuration

```toml
[tool.maturin]
# Include source distribution (sdist) when building
sdist-include = [
    "src/**/*.rs",
    "Cargo.toml",
    "Cargo.lock",
    "tests/**/*.py",
    "examples/**/*.py",
    "README.md",
    "LICENSE",
]

# Exclude unnecessary files from sdist
sdist-exclude = [
    "target/",
    ".github/",
    "*.pyc",
    "__pycache__/",
    ".pytest_cache/",
]
```

### Feature Flags in pyproject.toml

```toml
[project.optional-dependencies]
# Map to Cargo features
parallel = []  # Empty, triggers Cargo feature
all-features = []  # Build with all features

[tool.maturin]
# Build with specific features
features = ["parallel", "serialization"]

# Or build with all features
# features = ["--all-features"]

# Feature per platform
[tool.maturin.target.x86_64-unknown-linux-gnu]
features = ["parallel", "avx2"]

[tool.maturin.target.x86_64-apple-darwin]
features = ["parallel", "neon"]
```

**Usage**:
```bash
# Install with specific features
pip install my_extension[parallel]

# Build wheel with features
maturin build --release --features parallel,serialization
```

### Integration with build.rs

For advanced build customization:

**Cargo.toml**:
```toml
[package]
build = "build.rs"

[build-dependencies]
pyo3-build-config = "0.20"
```

**build.rs**:
```rust
fn main() {
    // Configure Python version
    pyo3_build_config::use_pyo3_cfgs();

    // Custom build logic
    println!("cargo:rerun-if-changed=src/wrapper.h");

    // Platform-specific compilation
    #[cfg(target_os = "linux")]
    {
        println!("cargo:rustc-link-lib=static=somelib");
    }

    // Feature detection
    if cfg!(feature = "parallel") {
        println!("cargo:rustc-cfg=has_parallel");
    }
}
```

---

## 2. Build Commands and Workflows

### Development Builds

#### Basic Development Build

```bash
# Install in editable mode (similar to pip install -e .)
maturin develop

# With debug symbols (default for develop)
maturin develop --profile dev

# With release optimizations (slower to build, faster runtime)
maturin develop --release
```

**What `maturin develop` Does**:
1. Builds Rust code as debug build (or release if specified)
2. Creates Python wheel
3. Installs wheel in current virtualenv
4. Enables immediate testing without reinstalling

**Output**:
```
   Compiling my_extension v0.1.0
    Finished dev [unoptimized + debuginfo] target(s) in 3.42s
📦 Built wheel for CPython 3.11 to /tmp/.tmpxxx/my_extension-0.1.0-cp311-cp311-linux_x86_64.whl
🛠 Installed my_extension-0.1.0
```

#### Incremental Development Workflow

```bash
# Terminal 1: Auto-rebuild on file changes
cargo watch -x "maturin develop" -w src/

# Terminal 2: Run tests
pytest tests/
```

**cargo-watch Configuration** (.cargo/config.toml):
```toml
[alias]
watch-dev = "watch -x 'maturin develop' -w src/"
watch-test = "watch -x test -w src/"
```

### Release Builds

#### Building Wheels

```bash
# Build wheel for current platform
maturin build --release

# Output location
ls target/wheels/
# my_extension-0.1.0-cp311-cp311-linux_x86_64.whl
```

#### Build for Specific Python Versions

```bash
# Build for all available Python versions
maturin build --release --interpreter python3.8 python3.9 python3.10 python3.11 python3.12

# Or use pyenv/conda environments
maturin build --release --find-interpreter

# Output
ls target/wheels/
# my_extension-0.1.0-cp38-cp38-linux_x86_64.whl
# my_extension-0.1.0-cp39-cp39-linux_x86_64.whl
# my_extension-0.1.0-cp310-cp310-linux_x86_64.whl
# ...
```

#### Build Source Distribution

```bash
# Build sdist only
maturin sdist

# Build both sdist and wheel
maturin build --release --sdist

ls target/wheels/
# my_extension-0.1.0.tar.gz
# my_extension-0.1.0-cp311-cp311-linux_x86_64.whl
```

### manylinux Builds

#### What is manylinux?

**manylinux** is a PEP standard for Linux wheel compatibility:
- `manylinux_2_28`: Modern Linux (glibc 2.28+, 2023)
- `manylinux_2_17`: Broad compatibility (glibc 2.17+, 2013)
- `manylinux2014`: Older systems (CentOS 7 era)

#### Building manylinux Wheels

```bash
# Build for manylinux_2_28 (recommended for new projects)
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4 \
  build --release --manylinux 2_28

# Build for maximum compatibility (manylinux_2_17)
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4 \
  build --release --manylinux 2_17

# Build for all interpreters in container
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4 \
  build --release --manylinux 2_28 --find-interpreter
```

**Output**:
```
target/wheels/
├── my_extension-0.1.0-cp38-cp38-manylinux_2_28_x86_64.whl
├── my_extension-0.1.0-cp39-cp39-manylinux_2_28_x86_64.whl
├── my_extension-0.1.0-cp310-cp310-manylinux_2_28_x86_64.whl
├── my_extension-0.1.0-cp311-cp311-manylinux_2_28_x86_64.whl
└── my_extension-0.1.0-cp312-cp312-manylinux_2_28_x86_64.whl
```

#### Custom manylinux Container

```dockerfile
# Dockerfile.manylinux
FROM ghcr.io/pyo3/maturin:v1.4

# Install additional system dependencies
RUN yum install -y \
    openblas-devel \
    lapack-devel \
    && yum clean all

# Set environment variables
ENV OPENBLAS=/usr/lib64/libopenblas.so
ENV LAPACK=/usr/lib64/liblapack.so
```

**Build**:
```bash
docker build -t my_manylinux -f Dockerfile.manylinux .
docker run --rm -v $(pwd):/io my_manylinux build --release --manylinux 2_28
```

### Cross-Compilation

#### Linux to Linux (Different Architecture)

```bash
# Install cross-compilation toolchain
rustup target add aarch64-unknown-linux-gnu

# Install cross
cargo install cross

# Build using cross
cross build --target aarch64-unknown-linux-gnu --release

# Or with maturin (requires cross-compilation setup)
maturin build --release --target aarch64-unknown-linux-gnu
```

#### macOS Universal Binaries

```bash
# Build for both Intel and Apple Silicon
# (Only works on macOS)
rustup target add x86_64-apple-darwin aarch64-apple-darwin

maturin build --release \
  --target x86_64-apple-darwin \
  --target aarch64-apple-darwin \
  --universal2

# Output: Universal wheel compatible with both architectures
ls target/wheels/
# my_extension-0.1.0-cp311-cp311-macosx_10_12_universal2.whl
```

#### Windows Cross-Compilation (from Linux)

```bash
# Install MinGW cross-compiler
sudo apt-get install mingw-w64

# Add Windows target
rustup target add x86_64-pc-windows-gnu

# Configure cargo
cat >> ~/.cargo/config.toml << 'EOF'
[target.x86_64-pc-windows-gnu]
linker = "x86_64-w64-mingw32-gcc"
EOF

# Build
maturin build --release --target x86_64-pc-windows-gnu
```

### Docker-Based Builds

#### Multi-Platform Build Script

```bash
#!/bin/bash
# build_all.sh - Build wheels for all platforms

set -e

PROJECT_ROOT=$(pwd)
WHEELS_DIR="$PROJECT_ROOT/dist"

mkdir -p "$WHEELS_DIR"

echo "Building Linux wheels..."
docker run --rm \
  -v "$PROJECT_ROOT:/io" \
  -v "$WHEELS_DIR:/output" \
  ghcr.io/pyo3/maturin:v1.4 \
  bash -c "
    cd /io && \
    maturin build --release --manylinux 2_28 --find-interpreter && \
    cp target/wheels/* /output/
  "

echo "Building musllinux wheels..."
docker run --rm \
  -v "$PROJECT_ROOT:/io" \
  -v "$WHEELS_DIR:/output" \
  ghcr.io/pyo3/maturin:v1.4-musllinux_1_2 \
  bash -c "
    cd /io && \
    maturin build --release --find-interpreter && \
    cp target/wheels/* /output/
  "

echo "Wheels built in $WHEELS_DIR"
ls -lh "$WHEELS_DIR"
```

**Make executable**:
```bash
chmod +x build_all.sh
./build_all.sh
```

### Build Profiles

#### Custom Cargo Profiles

```toml
# Cargo.toml

[profile.dev]
# Fast compilation, slow runtime
opt-level = 0
debug = true

[profile.release]
# Slow compilation, fast runtime
opt-level = 3
lto = "fat"
codegen-units = 1
strip = true

[profile.release-size]
inherits = "release"
opt-level = "z"  # Optimize for size
lto = "fat"
strip = true

[profile.bench]
inherits = "release"
debug = true  # Keep symbols for profiling
```

**Usage**:
```bash
# Development
maturin develop --profile dev

# Release
maturin build --profile release

# Size-optimized
maturin build --profile release-size

# Benchmarking
maturin build --profile bench
```

### Parallel Builds

```bash
# Use all CPU cores
maturin build --release -j$(nproc)

# Limit to 4 cores
maturin build --release -j4

# Set in environment
export CARGO_BUILD_JOBS=8
maturin build --release
```

### Caching and Incremental Builds

#### cargo Cache

```bash
# Clean build cache
cargo clean

# Clean release artifacts only
cargo clean --release

# Clean specific target
cargo clean --target x86_64-unknown-linux-gnu
```

#### sccache for Distributed Caching

```bash
# Install sccache
cargo install sccache

# Configure cargo to use sccache
export RUSTC_WRAPPER=sccache

# Build with cached compilation
maturin build --release

# View cache statistics
sccache --show-stats
```

**.cargo/config.toml**:
```toml
[build]
rustc-wrapper = "sccache"
```

### Build Scripts

#### Makefile

```makefile
# Makefile

.PHONY: dev release test clean install

dev:
	maturin develop

release:
	maturin build --release --find-interpreter

test:
	pytest tests/

clean:
	cargo clean
	rm -rf target/wheels/ dist/

install: release
	pip install --force-reinstall target/wheels/*-cp$$(python -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")'-*.whl

bench:
	maturin build --profile bench
	pytest tests/ --benchmark-only

format:
	cargo fmt
	ruff format python/

lint:
	cargo clippy -- -D warnings
	ruff check python/
	mypy python/

all: clean release test
```

**Usage**:
```bash
make dev      # Development build
make release  # Release build
make test     # Run tests
make install  # Build and install
```

#### Just (Modern Alternative to Make)

```just
# justfile

# Default recipe
default: dev

# Development build
dev:
    maturin develop

# Release build for all Python versions
release:
    maturin build --release --find-interpreter

# Run tests
test:
    pytest tests/ -v

# Run benchmarks
bench:
    maturin build --profile bench
    pytest tests/ --benchmark-only

# Clean build artifacts
clean:
    cargo clean
    rm -rf target/wheels/ dist/

# Format code
fmt:
    cargo fmt
    ruff format python/

# Lint code
lint:
    cargo clippy -- -D warnings
    ruff check python/

# Type check
typecheck:
    mypy python/

# Full CI pipeline
ci: fmt lint typecheck test

# Build and install locally
install: release
    #!/usr/bin/env bash
    PYVER=$(python -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')
    pip install --force-reinstall target/wheels/*-cp${PYVER}-*.whl
```

**Usage**:
```bash
just dev      # Development build
just release  # Release build
just ci       # Full CI pipeline
```

---

## 3. Dependency Management

### Rust Dependencies (Cargo.toml)

#### Core PyO3 Dependencies

```toml
[dependencies]
# Core PyO3
pyo3 = { version = "0.20", features = ["extension-module"] }

# NumPy integration
numpy = "0.20"

# Common utility crates
anyhow = "1.0"          # Error handling
thiserror = "1.0"       # Custom error types
```

**Extension Module Feature**:
```toml
# ✅ Correct for Python extensions
pyo3 = { version = "0.20", features = ["extension-module"] }

# ❌ Wrong: Omitting extension-module causes linking errors
pyo3 = "0.20"
```

#### Optional Features

```toml
[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }

# Optional dependencies
rayon = { version = "1.8", optional = true }
serde = { version = "1.0", features = ["derive"], optional = true }
serde_json = { version = "1.0", optional = true }

[features]
default = []
parallel = ["rayon"]
serialization = ["serde", "serde_json"]
all = ["parallel", "serialization"]
```

**Build with Features**:
```bash
# Default features
maturin build --release

# With specific features
maturin build --release --features parallel

# With all features
maturin build --release --all-features
```

#### Version Constraints

```toml
[dependencies]
# Exact version (not recommended)
pyo3 = "=0.20.0"

# Caret requirement (recommended)
pyo3 = "^0.20"  # >=0.20.0, <0.21.0

# Tilde requirement
pyo3 = "~0.20.3"  # >=0.20.3, <0.21.0

# Wildcard
pyo3 = "0.20.*"  # >=0.20.0, <0.21.0

# Range
pyo3 = ">=0.20, <0.22"

# Multiple sources
pyo3 = { version = "0.20", features = ["extension-module"] }
# pyo3 = { git = "https://github.com/PyO3/pyo3", branch = "main" }
# pyo3 = { path = "../pyo3" }
```

#### Workspace Dependencies

For multi-crate projects:

**Cargo.toml** (workspace root):
```toml
[workspace]
members = ["core", "utils", "io"]
resolver = "2"

[workspace.dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
numpy = "0.20"
anyhow = "1.0"
```

**core/Cargo.toml**:
```toml
[dependencies]
pyo3.workspace = true
numpy.workspace = true
anyhow.workspace = true
```

### Python Dependencies (pyproject.toml)

#### Core Dependencies

```toml
[project]
dependencies = [
    "numpy>=1.20,<2.0",
    "typing-extensions>=4.0; python_version < '3.11'",
]
```

#### Optional Dependencies

```toml
[project.optional-dependencies]
# Development tools
dev = [
    "pytest>=7.0",
    "pytest-benchmark>=4.0",
    "mypy>=1.0",
    "ruff>=0.1",
    "ipython>=8.0",
]

# Testing dependencies
test = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-xdist>=3.0",  # Parallel testing
    "hypothesis>=6.0",     # Property-based testing
]

# Documentation
docs = [
    "sphinx>=5.0",
    "sphinx-rtd-theme>=1.0",
    "myst-parser>=1.0",
]

# ML/Scientific computing
ml = [
    "torch>=2.0",
    "scipy>=1.9",
    "scikit-learn>=1.2",
]

# All extras
all = [
    "my_extension[dev,test,docs,ml]",
]
```

**Installation**:
```bash
# Base package only
pip install my_extension

# With dev tools
pip install my_extension[dev]

# With multiple extras
pip install my_extension[dev,test]

# With all extras
pip install my_extension[all]
```

#### Python Version Constraints

```toml
[project]
requires-python = ">=3.8"

# Per-dependency version constraints
dependencies = [
    # Only on older Python
    "typing-extensions>=4.0; python_version < '3.11'",

    # Only on newer Python
    "tomllib; python_version >= '3.11'",

    # Platform-specific
    "pywin32; platform_system == 'Windows'",

    # Combined constraints
    "dataclasses>=0.8; python_version < '3.7'",
]
```

### Native System Dependencies

#### System Libraries

For extensions that link against system libraries:

**Cargo.toml**:
```toml
[dependencies]
# OpenSSL
openssl = { version = "0.10", features = ["vendored"] }

# For dynamic linking (requires system OpenSSL)
# openssl = "0.10"

[build-dependencies]
pkg-config = "0.3"
```

**build.rs**:
```rust
fn main() {
    // Link against system library
    pkg_config::Config::new()
        .atleast_version("1.1.1")
        .probe("openssl")
        .unwrap();

    // Or specify manually
    println!("cargo:rustc-link-lib=ssl");
    println!("cargo:rustc-link-lib=crypto");
}
```

#### Vendored Dependencies

**Pros**: Self-contained, no system dependencies
**Cons**: Larger binary size, longer build times

```toml
[dependencies]
# OpenBLAS (vendored)
openblas-src = { version = "0.10", features = ["static"] }

# SQLite (vendored)
rusqlite = { version = "0.30", features = ["bundled"] }

# OpenSSL (vendored)
openssl = { version = "0.10", features = ["vendored"] }
```

#### Platform-Specific Dependencies

```toml
[target.'cfg(unix)'.dependencies]
libc = "0.2"

[target.'cfg(windows)'.dependencies]
winapi = { version = "0.3", features = ["winsock2", "ws2def"] }

[target.'cfg(target_os = "macos")'.dependencies]
core-foundation = "0.9"

[target.'cfg(target_os = "linux")'.dependencies]
nix = "0.27"
```

### Dependency Locking

#### Cargo.lock

```bash
# Generate Cargo.lock
cargo generate-lockfile

# Update all dependencies
cargo update

# Update specific dependency
cargo update pyo3

# Update within version constraint
cargo update --package pyo3
```

**Include in Version Control**:
```
# ✅ Commit Cargo.lock for:
- Applications
- Binary crates
- Reproducible builds

# ❌ Don't commit for:
- Libraries (unless required for reproducibility)
```

#### requirements.txt for Python

```bash
# Generate from pyproject.toml
pip-compile pyproject.toml

# Or manually create
pip freeze > requirements-dev.txt
```

**requirements-dev.txt**:
```
pytest==7.4.3
pytest-benchmark==4.0.0
mypy==1.7.1
ruff==0.1.6
```

### Dependency Auditing

#### Security Audits

```bash
# Install cargo-audit
cargo install cargo-audit

# Run security audit
cargo audit

# Fix vulnerabilities
cargo audit fix

# Check Python dependencies
pip install pip-audit
pip-audit
```

#### License Compliance

```bash
# Install cargo-license
cargo install cargo-license

# List all dependency licenses
cargo license

# Generate license report
cargo license --json > licenses.json
```

**Check for Incompatible Licenses**:
```bash
#!/bin/bash
# check_licenses.sh

ALLOWED_LICENSES=(
    "MIT"
    "Apache-2.0"
    "BSD-3-Clause"
    "BSD-2-Clause"
    "ISC"
    "Unlicense"
)

cargo license --json | jq -r '.[] | .license' | sort -u | while read -r license; do
    if [[ ! " ${ALLOWED_LICENSES[@]} " =~ " ${license} " ]]; then
        echo "WARNING: Found potentially incompatible license: $license"
    fi
done
```

---

## 4. Platform-Specific Builds

### Linux Builds

#### glibc vs musl

**glibc** (GNU C Library):
- Standard on most Linux distributions
- Better performance
- Larger binaries
- Target: `x86_64-unknown-linux-gnu`

**musl** (Minimal C Library):
- Smaller binaries
- Better portability (static linking)
- Slightly slower
- Target: `x86_64-unknown-linux-musl`

#### Building for glibc (manylinux)

```bash
# manylinux_2_28 (glibc 2.28+, modern distros)
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4 \
  build --release --manylinux 2_28

# manylinux_2_17 (glibc 2.17+, maximum compatibility)
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4 \
  build --release --manylinux 2_17
```

**Compatibility Matrix**:
```
manylinux_2_28: RHEL 8+, Ubuntu 20.04+, Debian 11+
manylinux_2_17: RHEL 7+, Ubuntu 16.04+, Debian 9+
manylinux2014:  CentOS 7 (EOL, not recommended)
```

#### Building for musl (musllinux)

```bash
# musllinux_1_2 (Alpine Linux, static binaries)
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4-musllinux_1_2 \
  build --release

# Or with rustup
rustup target add x86_64-unknown-linux-musl
maturin build --release --target x86_64-unknown-linux-musl
```

**Use Cases**:
- Docker containers (Alpine Linux)
- Embedded systems
- Static binaries for portability

#### Linux ARM64 (aarch64)

```bash
# Using cross
cargo install cross
cross build --target aarch64-unknown-linux-gnu --release

# Using Docker
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4 \
  build --release --target aarch64-unknown-linux-gnu
```

#### Platform Detection at Runtime

```rust
use pyo3::prelude::*;

#[pyfunction]
fn get_platform_info() -> String {
    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    return "Linux x86_64".to_string();

    #[cfg(all(target_os = "linux", target_arch = "aarch64"))]
    return "Linux ARM64".to_string();

    #[cfg(target_os = "linux")]
    return format!("Linux {}", std::env::consts::ARCH);

    "Unknown".to_string()
}
```

### macOS Builds

#### Intel vs Apple Silicon

```bash
# Intel (x86_64)
rustup target add x86_64-apple-darwin
maturin build --release --target x86_64-apple-darwin

# Apple Silicon (ARM64)
rustup target add aarch64-apple-darwin
maturin build --release --target aarch64-apple-darwin

# Universal binary (both architectures)
maturin build --release \
  --target x86_64-apple-darwin \
  --target aarch64-apple-darwin \
  --universal2
```

**Universal Binary Advantages**:
- Single wheel for both architectures
- Simpler distribution
- Larger file size (contains both binaries)

#### macOS Version Targeting

```toml
# Cargo.toml
[target.x86_64-apple-darwin]
rustflags = ["-C", "link-arg=-mmacosx-version-min=10.12"]

[target.aarch64-apple-darwin]
rustflags = ["-C", "link-arg=-mmacosx-version-min=11.0"]
```

**Deployment Targets**:
```
macOS 10.12+: x86_64 (Intel)
macOS 11.0+:  aarch64 (Apple Silicon)
```

#### Accelerate Framework

```rust
// Use Apple's Accelerate framework for BLAS/LAPACK
use pyo3::prelude::*;

#[pyfunction]
fn matrix_multiply(a: Vec<f64>, b: Vec<f64>) -> Vec<f64> {
    #[cfg(target_os = "macos")]
    {
        // Use Accelerate framework
        accelerate_gemm(a, b)
    }

    #[cfg(not(target_os = "macos"))]
    {
        // Fallback implementation
        naive_gemm(a, b)
    }
}
```

**Cargo.toml**:
```toml
[target.'cfg(target_os = "macos")'.dependencies]
accelerate-src = "0.3"
```

### Windows Builds

#### MSVC vs GNU Toolchain

**MSVC** (Microsoft Visual C++):
- Official Windows compiler
- Better compatibility with Windows libraries
- Recommended for most use cases
- Target: `x86_64-pc-windows-msvc`

**GNU** (MinGW):
- Cross-compilation friendly
- Smaller runtime dependencies
- Target: `x86_64-pc-windows-gnu`

#### Building for Windows (MSVC)

```bash
# On Windows
rustup target add x86_64-pc-windows-msvc
maturin build --release --target x86_64-pc-windows-msvc

# On Linux (cross-compilation, requires setup)
rustup target add x86_64-pc-windows-msvc
cargo install xwin
xwin --accept-license 1 splat --output ~/.xwin
maturin build --release --target x86_64-pc-windows-msvc
```

#### Building for Windows (GNU)

```bash
# Install MinGW
# Linux: sudo apt-get install mingw-w64
# macOS: brew install mingw-w64

rustup target add x86_64-pc-windows-gnu
maturin build --release --target x86_64-pc-windows-gnu
```

**.cargo/config.toml**:
```toml
[target.x86_64-pc-windows-gnu]
linker = "x86_64-w64-mingw32-gcc"
ar = "x86_64-w64-mingw32-ar"
```

#### Windows-Specific Features

```rust
use pyo3::prelude::*;

#[pyfunction]
fn get_windows_version() -> PyResult<String> {
    #[cfg(target_os = "windows")]
    {
        use winapi::um::sysinfoapi::GetVersionExW;
        // Windows-specific code
        Ok("Windows 10".to_string())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(PyErr::new::<pyo3::exceptions::PyOSError, _>(
            "Not running on Windows"
        ))
    }
}
```

**Cargo.toml**:
```toml
[target.'cfg(windows)'.dependencies]
winapi = { version = "0.3", features = ["sysinfoapi", "winnt"] }
```

### Cross-Compilation Setup

#### Using cross

```bash
# Install cross
cargo install cross

# Build for different target
cross build --target aarch64-unknown-linux-gnu --release

# With maturin
cross run maturin build --release --target aarch64-unknown-linux-gnu
```

**.cross/Cross.toml**:
```toml
[target.aarch64-unknown-linux-gnu]
image = "ghcr.io/cross-rs/aarch64-unknown-linux-gnu:latest"

[build]
pre-build = [
    "dpkg --add-architecture arm64",
    "apt-get update",
    "apt-get install -y libssl-dev:arm64",
]
```

#### Target Triple Reference

**Linux**:
```
x86_64-unknown-linux-gnu      # glibc x86_64
x86_64-unknown-linux-musl     # musl x86_64
aarch64-unknown-linux-gnu     # glibc ARM64
aarch64-unknown-linux-musl    # musl ARM64
armv7-unknown-linux-gnueabihf # ARMv7 (Raspberry Pi)
```

**macOS**:
```
x86_64-apple-darwin           # Intel Mac
aarch64-apple-darwin          # Apple Silicon
```

**Windows**:
```
x86_64-pc-windows-msvc        # 64-bit MSVC
i686-pc-windows-msvc          # 32-bit MSVC
x86_64-pc-windows-gnu         # 64-bit MinGW
```

#### Conditional Compilation by Platform

```rust
use pyo3::prelude::*;

#[pyfunction]
fn optimized_function(data: Vec<f64>) -> f64 {
    #[cfg(all(target_arch = "x86_64", target_feature = "avx2"))]
    {
        avx2_implementation(data)
    }

    #[cfg(all(target_arch = "aarch64", target_feature = "neon"))]
    {
        neon_implementation(data)
    }

    #[cfg(not(any(
        all(target_arch = "x86_64", target_feature = "avx2"),
        all(target_arch = "aarch64", target_feature = "neon")
    )))]
    {
        portable_implementation(data)
    }
}
```

### Platform Testing

#### Local Testing Script

```bash
#!/bin/bash
# test_all_platforms.sh

set -e

# Array of targets to test
TARGETS=(
    "x86_64-unknown-linux-gnu"
    "x86_64-unknown-linux-musl"
    "aarch64-unknown-linux-gnu"
    "x86_64-apple-darwin"
    "aarch64-apple-darwin"
    "x86_64-pc-windows-msvc"
)

for target in "${TARGETS[@]}"; do
    echo "Building for $target..."

    if command -v cross &> /dev/null; then
        cross build --target "$target" --release
    else
        cargo build --target "$target" --release
    fi

    echo "✓ $target build successful"
done

echo "All platform builds completed successfully!"
```

---

## 5. Version Management

### Single Source of Truth

#### Version in pyproject.toml Only

**pyproject.toml**:
```toml
[project]
name = "my_extension"
version = "0.1.0"
dynamic = []
```

**Cargo.toml**:
```toml
[package]
name = "my_extension"
version = "0.0.0"  # Dummy version, overridden by maturin
edition = "2021"
```

**How It Works**:
- Maturin reads version from `pyproject.toml`
- Overrides Cargo.toml version during build
- Python package uses pyproject.toml version

#### Version in Cargo.toml Only

**Cargo.toml**:
```toml
[package]
name = "my_extension"
version = "0.1.0"
edition = "2021"
```

**pyproject.toml**:
```toml
[project]
name = "my_extension"
dynamic = ["version"]  # Version comes from Cargo.toml
```

**How It Works**:
- Maturin reads version from `Cargo.toml`
- Generates wheel with Cargo version
- Best for Rust-first projects

### Git Tag-Based Versioning

#### Using setuptools-scm

**pyproject.toml**:
```toml
[build-system]
requires = ["maturin>=1.4,<2.0", "setuptools-scm"]
build-backend = "maturin"

[project]
name = "my_extension"
dynamic = ["version"]

[tool.setuptools_scm]
write_to = "python/my_extension/_version.py"
```

**Create Git Tags**:
```bash
# Tag a release
git tag v0.1.0
git push origin v0.1.0

# Build uses tag for version
maturin build --release
# Generates: my_extension-0.1.0-...whl
```

**Version String Format**:
```
v0.1.0          → 0.1.0
v0.1.0-1-gabcd  → 0.1.0.post1+gabcd  (1 commit after tag)
(no tags)       → 0.0.0+d20231101    (date-based)
```

#### Custom Version Script

**scripts/version.py**:
```python
#!/usr/bin/env python3
"""Generate version from git."""

import subprocess
import sys

def get_version():
    try:
        # Get latest tag
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()

        # Remove 'v' prefix if present
        version = tag.lstrip('v')

        # Check if we're on the tag
        current = subprocess.check_output(
            ["git", "describe", "--tags"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()

        if current != tag:
            # Add dev version
            commits = subprocess.check_output(
                ["git", "rev-list", f"{tag}..HEAD", "--count"],
            ).decode().strip()
            version += f".dev{commits}"

        return version
    except subprocess.CalledProcessError:
        return "0.0.0.dev0"

if __name__ == "__main__":
    print(get_version())
```

**pyproject.toml**:
```toml
[project]
name = "my_extension"
dynamic = ["version"]

[tool.maturin]
version-script = "scripts/version.py"
```

### Runtime Version Access

#### From Python

**python/my_extension/__init__.py**:
```python
"""My Extension package."""

# If using setuptools-scm
try:
    from my_extension._version import version as __version__
except ImportError:
    __version__ = "unknown"

# Or hardcoded (updated by build script)
# __version__ = "0.1.0"

__all__ = ["__version__"]
```

**Usage**:
```python
import my_extension
print(my_extension.__version__)  # "0.1.0"
```

#### From Rust

**src/lib.rs**:
```rust
use pyo3::prelude::*;

#[pymodule]
fn my_extension(_py: Python, m: &PyModule) -> PyResult<()> {
    // Version from Cargo.toml
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Build timestamp
    m.add("__build_timestamp__", env!("BUILD_TIMESTAMP"))?;

    // Git commit
    m.add("__git_commit__", env!("GIT_COMMIT"))?;

    Ok(())
}
```

**build.rs**:
```rust
use std::process::Command;

fn main() {
    pyo3_build_config::use_pyo3_cfgs();

    // Get git commit
    let output = Command::new("git")
        .args(&["rev-parse", "--short", "HEAD"])
        .output()
        .unwrap();
    let git_hash = String::from_utf8(output.stdout).unwrap();
    println!("cargo:rustc-env=GIT_COMMIT={}", git_hash.trim());

    // Build timestamp
    let timestamp = chrono::Utc::now().to_rfc3339();
    println!("cargo:rustc-env=BUILD_TIMESTAMP={}", timestamp);
}
```

**Cargo.toml**:
```toml
[build-dependencies]
pyo3-build-config = "0.20"
chrono = "0.4"
```

### Changelog Management

#### Keep a Changelog Format

**CHANGELOG.md**:
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature X

### Changed
- Updated behavior of Y

### Fixed
- Bug in Z function

## [0.1.0] - 2025-10-30

### Added
- Initial release
- Core functionality for data processing
- Python API wrapper

[Unreleased]: https://github.com/user/repo/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/user/repo/releases/tag/v0.1.0
```

#### Automated Changelog Generation

```bash
# Install git-cliff
cargo install git-cliff

# Generate changelog
git cliff --output CHANGELOG.md
```

**cliff.toml**:
```toml
[changelog]
header = """
# Changelog\n
All notable changes to this project will be documented in this file.\n
"""
body = """
{% for group, commits in commits | group_by(attribute="group") %}
    ### {{ group | upper_first }}
    {% for commit in commits %}
        - {{ commit.message | upper_first }}
    {% endfor %}
{% endfor %}
"""
trim = true

[git]
conventional_commits = true
filter_unconventional = true
commit_parsers = [
    { message = "^feat", group = "Added" },
    { message = "^fix", group = "Fixed" },
    { message = "^perf", group = "Performance" },
    { message = "^refactor", group = "Changed" },
]
```

### Version Bumping Workflow

```bash
#!/bin/bash
# bump_version.sh

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <major|minor|patch>"
    exit 1
fi

# Get current version
CURRENT=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "Current version: $CURRENT"

# Bump version
NEW=$(python -c "
import sys
major, minor, patch = map(int, '$CURRENT'.split('.'))
bump = '$1'
if bump == 'major':
    major += 1
    minor = 0
    patch = 0
elif bump == 'minor':
    minor += 1
    patch = 0
else:
    patch += 1
print(f'{major}.{minor}.{patch}')
")

echo "New version: $NEW"

# Update pyproject.toml
sed -i.bak "s/^version = \".*\"/version = \"$NEW\"/" pyproject.toml
rm pyproject.toml.bak

# Update Cargo.toml (if using)
sed -i.bak "s/^version = \".*\"/version = \"$NEW\"/" Cargo.toml
rm Cargo.toml.bak

# Commit and tag
git add pyproject.toml Cargo.toml
git commit -m "Bump version to $NEW"
git tag "v$NEW"

echo "Version bumped to $NEW"
echo "Push with: git push && git push --tags"
```

---

## 6. PyPI Publishing

### Package Preparation

#### Pre-Publishing Checklist

```markdown
- [ ] Version bumped in pyproject.toml
- [ ] CHANGELOG.md updated
- [ ] All tests passing (pytest tests/)
- [ ] Documentation up-to-date
- [ ] Wheels built for all platforms
- [ ] README.md renders correctly on PyPI
- [ ] License file included
- [ ] PyPI classifiers accurate
- [ ] Project URLs set correctly
```

#### Build All Wheels

```bash
#!/bin/bash
# build_wheels.sh - Build wheels for all platforms

set -e

# Clean previous builds
rm -rf target/wheels/ dist/

# Linux (manylinux)
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4 \
  build --release --manylinux 2_28 --find-interpreter

# musllinux (Alpine)
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4-musllinux_1_2 \
  build --release --find-interpreter

# macOS (universal binary)
# Run on macOS machine
if [[ "$OSTYPE" == "darwin"* ]]; then
    maturin build --release \
      --target x86_64-apple-darwin \
      --target aarch64-apple-darwin \
      --universal2
fi

# Windows (MSVC)
# Run on Windows machine or cross-compile
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    maturin build --release --target x86_64-pc-windows-msvc
fi

# Build source distribution
maturin sdist

# Move to dist/
mkdir -p dist/
cp target/wheels/* dist/

echo "Wheels built successfully:"
ls -lh dist/
```

### Wheel Inspection and Validation

#### Inspect Wheel Contents

```bash
# List contents
unzip -l dist/my_extension-0.1.0-cp311-cp311-linux_x86_64.whl

# Extract and inspect
mkdir -p /tmp/wheel_contents
unzip -d /tmp/wheel_contents dist/my_extension-0.1.0-*.whl

# Check shared library
file /tmp/wheel_contents/my_extension/_core.*.so
# my_extension/_core.cpython-311-x86_64-linux-gnu.so: ELF 64-bit LSB shared object

# Check dependencies
ldd /tmp/wheel_contents/my_extension/_core.*.so
# linux-vdso.so.1
# libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6
# /lib64/ld-linux-x86-64.so.2
```

#### Validate Wheel

```bash
# Install wheel-inspect
pip install wheel-inspect

# Inspect wheel
wheel2json dist/my_extension-0.1.0-*.whl | jq .

# Check for issues
python -m wheel unpack dist/my_extension-0.1.0-*.whl
```

#### Test Wheel in Clean Environment

```bash
# Create clean virtualenv
python -m venv /tmp/test_env
source /tmp/test_env/bin/activate

# Install wheel
pip install dist/my_extension-0.1.0-*.whl

# Test import
python -c "import my_extension; print(my_extension.__version__)"

# Run tests
pytest tests/

deactivate
rm -rf /tmp/test_env
```

### TestPyPI Testing

#### Upload to TestPyPI

```bash
# Install twine
pip install twine

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Or with explicit URL
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

**~/.pypirc**:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-...
```

#### Test Installation from TestPyPI

```bash
# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ my_extension

# With extra-index for dependencies
pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  my_extension

# Test
python -c "import my_extension; print(my_extension.__version__)"
```

### PyPI Publishing

#### API Token Configuration

1. **Generate Token**:
   - Go to https://pypi.org/manage/account/token/
   - Click "Add API token"
   - Scope: "Entire account" or specific project
   - Copy token (starts with `pypi-`)

2. **Configure Locally**:
```bash
# Store in ~/.pypirc
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-AgENdGVzdC5weXBpLm9yZwIkZjBhY...
EOF

chmod 600 ~/.pypirc
```

3. **Use in CI** (GitHub Actions):
```yaml
- name: Publish to PyPI
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
  run: twine upload dist/*
```

#### Upload to PyPI

```bash
# Build wheels
./build_wheels.sh

# Verify wheels
twine check dist/*

# Upload to PyPI
twine upload dist/*
```

**Output**:
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading my_extension-0.1.0-cp38-cp38-manylinux_2_28_x86_64.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.1/2.1 MB • 00:02 • ?
Uploading my_extension-0.1.0-cp39-cp39-manylinux_2_28_x86_64.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.1/2.1 MB • 00:02 • ?
...
View at: https://pypi.org/project/my-extension/0.1.0/
```

#### Verify Published Package

```bash
# Check on PyPI
open https://pypi.org/project/my-extension/

# Install from PyPI
pip install my-extension

# Verify
python -c "import my_extension; print(my_extension.__version__)"
```

### Package Metadata

#### README.md for PyPI

**README.md**:
```markdown
# My Extension

[![PyPI version](https://badge.fury.io/py/my-extension.svg)](https://pypi.org/project/my-extension/)
[![Python versions](https://img.shields.io/pypi/pyversions/my-extension.svg)](https://pypi.org/project/my-extension/)
[![License](https://img.shields.io/pypi/l/my-extension.svg)](https://github.com/user/my-extension/blob/main/LICENSE)

High-performance Python extension written in Rust.

## Features

- 🚀 **Fast**: 10-100x faster than pure Python
- 🔒 **Safe**: Memory-safe Rust implementation
- 🐍 **Pythonic**: Familiar Python API
- 📦 **Easy to install**: `pip install my-extension`

## Installation

```bash
pip install my-extension
```

## Quick Start

```python
import my_extension

result = my_extension.process_data([1, 2, 3, 4, 5])
print(result)  # Processed data
```

## Documentation

Full documentation: https://my-extension.readthedocs.io

## Development

```bash
git clone https://github.com/user/my-extension
cd my-extension
pip install maturin
maturin develop
pytest tests/
```

## License

MIT OR Apache-2.0
```

#### Long Description from README

**pyproject.toml**:
```toml
[project]
readme = "README.md"

# Or from a different file
# readme = { file = "docs/pypi_description.md", content-type = "text/markdown" }
```

#### Classifiers Reference

```toml
[project]
classifiers = [
    # Development Status
    "Development Status :: 3 - Alpha",
    "Development Status :: 4 - Beta",
    "Development Status :: 5 - Production/Stable",

    # Intended Audience
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "Intended Audience :: Information Technology",

    # License
    "License :: OSI Approved :: MIT License",
    "License :: OSI Approved :: Apache Software License",
    "License :: OSI Approved :: BSD License",

    # Programming Languages
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
    "Programming Language :: Rust",

    # Operating Systems
    "Operating System :: OS Independent",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
    "Operating System :: Microsoft :: Windows",

    # Topics
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Scientific/Engineering",
    "Topic :: System :: Hardware",

    # Typing
    "Typing :: Typed",
]
```

### Troubleshooting Publishing

#### Common Errors

**Error: File already exists**
```
HTTPError: 400 Bad Request from https://upload.pypi.org/legacy/
File already exists.
```

**Solution**: You cannot re-upload the same version. Bump version and try again.

**Error: Invalid README**
```
HTTPError: 400 Bad Request
The description failed to render in the default format of reStructuredText.
```

**Solution**: Use Markdown instead:
```toml
[project]
readme = { file = "README.md", content-type = "text/markdown" }
```

**Error: Missing dependencies**
```
Could not install packages due to an OSError: my_extension requires libc.so.6(GLIBC_2.29)
```

**Solution**: Build with older manylinux version for better compatibility.

---

## 7. CI/CD Automation

### GitHub Actions Workflows

#### Complete Build and Test Workflow

**.github/workflows/ci.yml**:
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  CARGO_TERM_COLOR: always

jobs:
  # Rust tests and linting
  rust-tests:
    name: Rust Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt, clippy

      - name: Cache cargo
        uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/bin/
            ~/.cargo/registry/index/
            ~/.cargo/registry/cache/
            ~/.cargo/git/db/
            target/
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}

      - name: Check formatting
        run: cargo fmt --all -- --check

      - name: Clippy
        run: cargo clippy --all-features -- -D warnings

      - name: Run tests
        run: cargo test --all-features

  # Python tests
  python-tests:
    name: Python Tests (${{ matrix.python-version }}, ${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Install maturin
        run: pip install maturin pytest pytest-benchmark

      - name: Build and install
        run: maturin develop --release

      - name: Run Python tests
        run: pytest tests/ -v

      - name: Run benchmarks
        run: pytest tests/ --benchmark-only

  # Security audit
  security:
    name: Security Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Audit Rust dependencies
        uses: rustsec/audit-check@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```

#### Release Workflow with Multi-Platform Builds

**.github/workflows/release.yml**:
```yaml
name: Release

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  # Linux builds
  linux:
    name: Build Linux (${{ matrix.target }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target:
          - x86_64-unknown-linux-gnu
          - aarch64-unknown-linux-gnu
    steps:
      - uses: actions/checkout@v4

      - name: Build wheels
        uses: PyO3/maturin-action@v1
        with:
          target: ${{ matrix.target }}
          args: --release --out dist --find-interpreter
          manylinux: 2_28

      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-linux-${{ matrix.target }}
          path: dist

  # musllinux builds
  musllinux:
    name: Build musllinux (${{ matrix.target }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target:
          - x86_64-unknown-linux-musl
          - aarch64-unknown-linux-musl
    steps:
      - uses: actions/checkout@v4

      - name: Build wheels
        uses: PyO3/maturin-action@v1
        with:
          target: ${{ matrix.target }}
          args: --release --out dist --find-interpreter
          manylinux: musllinux_1_2

      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-musllinux-${{ matrix.target }}
          path: dist

  # macOS builds
  macos:
    name: Build macOS
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build wheels (universal2)
        uses: PyO3/maturin-action@v1
        with:
          args: --release --out dist --find-interpreter --target universal2-apple-darwin

      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-macos
          path: dist

  # Windows builds
  windows:
    name: Build Windows (${{ matrix.target }})
    runs-on: windows-latest
    strategy:
      matrix:
        target:
          - x64
          - x86
    steps:
      - uses: actions/checkout@v4

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

  # Source distribution
  sdist:
    name: Build source distribution
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build sdist
        uses: PyO3/maturin-action@v1
        with:
          command: sdist
          args: --out dist

      - name: Upload sdist
        uses: actions/upload-artifact@v4
        with:
          name: sdist
          path: dist

  # PyPI release
  release:
    name: Release to PyPI
    runs-on: ubuntu-latest
    needs: [linux, musllinux, macos, windows, sdist]
    if: startsWith(github.ref, 'refs/tags/v')
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: dist
          pattern: wheels-*
          merge-multiple: true

      - uses: actions/download-artifact@v4
        with:
          name: sdist
          path: dist

      - name: Publish to PyPI
        uses: PyO3/maturin-action@v1
        env:
          MATURIN_PYPI_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
        with:
          command: upload
          args: --non-interactive --skip-existing dist/*

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### Nightly Builds

**.github/workflows/nightly.yml**:
```yaml
name: Nightly

on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight UTC
  workflow_dispatch:

jobs:
  test-nightly:
    name: Test with Rust nightly
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Rust nightly
        uses: dtolnay/rust-toolchain@nightly

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install maturin
        run: pip install maturin pytest

      - name: Build
        run: maturin develop --release

      - name: Test
        run: pytest tests/

      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Nightly build failed',
              body: 'The nightly build has failed. See: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}',
              labels: ['bug', 'nightly']
            })
```

### maturin-action Configuration

#### Basic Usage

```yaml
- name: Build wheels
  uses: PyO3/maturin-action@v1
  with:
    args: --release --out dist --find-interpreter
```

#### Advanced Configuration

```yaml
- name: Build wheels
  uses: PyO3/maturin-action@v1
  with:
    # Build command: build (default), publish, sdist
    command: build

    # Additional arguments
    args: --release --out dist

    # Target triple
    target: x86_64-unknown-linux-gnu

    # manylinux version
    manylinux: 2_28

    # Container image (overrides manylinux)
    # container: ghcr.io/pyo3/maturin:v1.4

    # Working directory
    working-directory: .

    # Rust toolchain
    rust-toolchain: stable

    # Docker options
    docker-options: --privileged
```

#### Feature-Specific Builds

```yaml
- name: Build with all features
  uses: PyO3/maturin-action@v1
  with:
    args: --release --out dist --all-features

- name: Build with specific features
  uses: PyO3/maturin-action@v1
  with:
    args: --release --out dist --features parallel,serialization

- name: Build without default features
  uses: PyO3/maturin-action@v1
  with:
    args: --release --out dist --no-default-features
```

### Test Automation

#### Pytest Integration

```yaml
- name: Run tests
  run: |
    pip install pytest pytest-cov pytest-xdist
    pytest tests/ \
      --cov=my_extension \
      --cov-report=xml \
      --cov-report=term \
      -n auto \
      -v

- name: Upload coverage
  uses: codecov/codecov-action@v4
  with:
    files: ./coverage.xml
```

#### Property-Based Testing

```yaml
- name: Run property tests
  run: |
    pip install pytest hypothesis
    pytest tests/property_tests.py \
      --hypothesis-show-statistics \
      -v
```

#### Benchmarking in CI

```yaml
- name: Run benchmarks
  run: |
    pip install pytest pytest-benchmark
    pytest tests/ --benchmark-only \
      --benchmark-autosave \
      --benchmark-compare

- name: Store benchmark results
  uses: benchmark-action/github-action-benchmark@v1
  with:
    tool: 'pytest'
    output-file-path: .benchmarks/Linux-CPython-3.11-64bit/0001_benchmark.json
    github-token: ${{ secrets.GITHUB_TOKEN }}
    auto-push: true
```

### Artifact Management

#### Uploading Build Artifacts

```yaml
- name: Upload wheels
  uses: actions/upload-artifact@v4
  with:
    name: wheels-${{ matrix.os }}-${{ matrix.python-version }}
    path: dist/*.whl
    retention-days: 7

- name: Upload source distribution
  uses: actions/upload-artifact@v4
  with:
    name: sdist
    path: dist/*.tar.gz
```

#### Downloading Artifacts

```yaml
- name: Download all wheels
  uses: actions/download-artifact@v4
  with:
    path: dist
    pattern: wheels-*
    merge-multiple: true

- name: List artifacts
  run: ls -lh dist/
```

### Caching Strategies

#### Cargo Cache

```yaml
- name: Cache cargo registry
  uses: actions/cache@v4
  with:
    path: ~/.cargo/registry
    key: ${{ runner.os }}-cargo-registry-${{ hashFiles('**/Cargo.lock') }}

- name: Cache cargo index
  uses: actions/cache@v4
  with:
    path: ~/.cargo/git
    key: ${{ runner.os }}-cargo-index-${{ hashFiles('**/Cargo.lock') }}

- name: Cache cargo build
  uses: actions/cache@v4
  with:
    path: target
    key: ${{ runner.os }}-cargo-build-target-${{ hashFiles('**/Cargo.lock') }}
```

#### Python Cache

```yaml
- name: Cache Python dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

#### sccache Integration

```yaml
- name: Run sccache-cache
  uses: mozilla-actions/sccache-action@v0.0.4

- name: Build with sccache
  env:
    RUSTC_WRAPPER: sccache
    SCCACHE_GHA_ENABLED: "true"
  run: maturin build --release
```

### Release Automation

#### Automated Tagging

```yaml
name: Tag Release

on:
  push:
    branches:
      - main
    paths:
      - 'pyproject.toml'

jobs:
  tag:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Get version
        id: version
        run: |
          VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
          echo "version=$VERSION" >> $GITHUB_OUTPUT

      - name: Create tag
        run: |
          git config user.name github-actions
          git config user.email github-actions@github.com
          git tag -a v${{ steps.version.outputs.version }} -m "Release v${{ steps.version.outputs.version }}"
          git push origin v${{ steps.version.outputs.version }}
```

#### Changelog Generation

```yaml
- name: Generate changelog
  uses: mikepenz/release-changelog-builder-action@v4
  with:
    configuration: .github/changelog-config.json
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

- name: Create release
  uses: softprops/action-gh-release@v1
  with:
    body: ${{ steps.changelog.outputs.changelog }}
    files: dist/*
```

---

## 8. Advanced Build Customization

### build.rs Integration

#### Basic build.rs

```rust
// build.rs
fn main() {
    // Configure PyO3
    pyo3_build_config::use_pyo3_cfgs();

    // Rerun if build script changes
    println!("cargo:rerun-if-changed=build.rs");
}
```

**Cargo.toml**:
```toml
[build-dependencies]
pyo3-build-config = "0.20"
```

#### Conditional Compilation

```rust
// build.rs
use std::env;

fn main() {
    pyo3_build_config::use_pyo3_cfgs();

    // Platform-specific flags
    let target_os = env::var("CARGO_CFG_TARGET_OS").unwrap();
    match target_os.as_str() {
        "linux" => {
            println!("cargo:rustc-cfg=os_linux");
            println!("cargo:rustc-link-lib=m");
        }
        "macos" => {
            println!("cargo:rustc-cfg=os_macos");
            println!("cargo:rustc-link-lib=framework=Accelerate");
        }
        "windows" => {
            println!("cargo:rustc-cfg=os_windows");
        }
        _ => {}
    }

    // Feature detection
    if cfg!(feature = "simd") {
        println!("cargo:rustc-cfg=has_simd");
    }
}
```

**Usage in Rust**:
```rust
#[cfg(os_linux)]
fn platform_specific() {
    // Linux-specific code
}

#[cfg(has_simd)]
fn simd_implementation() {
    // SIMD code
}
```

#### Code Generation

```rust
// build.rs
use std::env;
use std::fs::File;
use std::io::Write;
use std::path::Path;

fn main() {
    pyo3_build_config::use_pyo3_cfgs();

    // Generate code
    let out_dir = env::var("OUT_DIR").unwrap();
    let dest_path = Path::new(&out_dir).join("generated.rs");
    let mut f = File::create(&dest_path).unwrap();

    writeln!(f, "// Auto-generated code").unwrap();
    writeln!(f, "pub const BUILD_TIME: &str = \"{}\";",
             chrono::Utc::now().to_rfc3339()).unwrap();
    writeln!(f, "pub const GIT_COMMIT: &str = \"{}\";",
             get_git_commit()).unwrap();

    println!("cargo:rerun-if-changed=.git/HEAD");
}

fn get_git_commit() -> String {
    use std::process::Command;

    let output = Command::new("git")
        .args(&["rev-parse", "--short", "HEAD"])
        .output()
        .unwrap();

    String::from_utf8(output.stdout).unwrap().trim().to_string()
}
```

**Include in lib.rs**:
```rust
include!(concat!(env!("OUT_DIR"), "/generated.rs"));

#[pyfunction]
fn build_info() -> (String, String) {
    (BUILD_TIME.to_string(), GIT_COMMIT.to_string())
}
```

#### Linking External Libraries

```rust
// build.rs
use pkg_config;

fn main() {
    pyo3_build_config::use_pyo3_cfgs();

    // Use pkg-config to find library
    pkg_config::Config::new()
        .atleast_version("1.0")
        .probe("somelib")
        .unwrap();

    // Or link manually
    println!("cargo:rustc-link-lib=static=mylib");
    println!("cargo:rustc-link-search=native=/usr/local/lib");
}
```

### Custom rustc Flags

#### Per-Target Flags

**Cargo.toml**:
```toml
[target.x86_64-unknown-linux-gnu]
rustflags = [
    "-C", "link-arg=-s",              # Strip symbols
    "-C", "target-cpu=native",        # Optimize for host CPU
    "-C", "link-arg=-fuse-ld=lld",   # Use LLD linker
]

[target.x86_64-apple-darwin]
rustflags = [
    "-C", "link-arg=-Wl,-dead_strip",
    "-C", "target-cpu=native",
]

[target.x86_64-pc-windows-msvc]
rustflags = [
    "/LTCG",                          # Link-time code generation
]
```

#### Project-Wide Flags

**.cargo/config.toml**:
```toml
[build]
rustflags = ["-C", "target-cpu=native"]

[target.x86_64-unknown-linux-gnu]
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=lld"]
```

### Feature Flags

#### Feature Configuration

```toml
[features]
default = ["numpy"]

# Basic features
numpy = ["dep:numpy"]
parallel = ["dep:rayon"]

# Platform-specific features
simd = []
avx2 = ["simd"]
neon = ["simd"]

# Conditional features
gpu = ["dep:cudarc"]
opencl = ["dep:opencl3"]

# Feature combinations
all-features = ["numpy", "parallel", "simd"]
minimal = []
```

#### Feature-Dependent Code

```rust
#[cfg(feature = "numpy")]
use numpy::{PyArray1, PyReadonlyArray1};

#[cfg(feature = "parallel")]
use rayon::prelude::*;

#[pyfunction]
fn process_data(
    #[cfg(feature = "numpy")] data: PyReadonlyArray1<f64>,
    #[cfg(not(feature = "numpy"))] data: Vec<f64>,
) -> f64 {
    let slice = {
        #[cfg(feature = "numpy")]
        { data.as_slice().unwrap() }

        #[cfg(not(feature = "numpy"))]
        { &data }
    };

    #[cfg(feature = "parallel")]
    return slice.par_iter().sum();

    #[cfg(not(feature = "parallel"))]
    return slice.iter().sum();
}
```

### Link-Time Optimization (LTO)

#### LTO Configuration

```toml
[profile.release]
lto = "fat"          # Full LTO (slowest build, best performance)
# lto = "thin"       # Thin LTO (balanced)
# lto = false        # No LTO (fastest build)

codegen-units = 1    # Single codegen unit for better optimization
```

**Trade-offs**:
```
Fat LTO:  30-60 min build, 10-30% performance gain
Thin LTO: 10-20 min build, 5-15% performance gain
No LTO:   2-5 min build,   baseline performance
```

#### Cross-Language LTO

```toml
[profile.release]
lto = true

[profile.release.package."*"]
opt-level = 3
lto = true
```

### Size Optimization

#### Minimize Binary Size

```toml
[profile.release-size]
inherits = "release"
opt-level = "z"       # Optimize for size
lto = true
codegen-units = 1
panic = "abort"       # Remove panic unwinding code
strip = true          # Strip symbols
```

**Build**:
```bash
maturin build --profile release-size

# Compare sizes
ls -lh target/wheels/
# Before: 2.5 MB
# After:  800 KB
```

#### Reduce Dependencies

```toml
[dependencies]
# Use minimal features
serde = { version = "1.0", default-features = false, features = ["derive"] }
tokio = { version = "1.0", default-features = false, features = ["rt"] }
```

### Custom Allocators

#### jemalloc

```toml
[dependencies]
tikv-jemallocator = "0.5"

[profile.release]
# jemalloc performs better with LTO
lto = "thin"
```

```rust
#[global_allocator]
static GLOBAL: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;

#[pymodule]
fn my_extension(_py: Python, m: &PyModule) -> PyResult<()> {
    // Module uses jemalloc
    Ok(())
}
```

#### mimalloc

```toml
[dependencies]
mimalloc = { version = "0.1", default-features = false }
```

```rust
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;
```

---

## 9. Distribution Strategies

### Public PyPI

**Advantages**:
- Maximum discoverability
- `pip install` works out of the box
- CDN distribution worldwide
- Version management

**Setup**:
1. Build wheels for all platforms
2. Upload to PyPI
3. Users install with `pip install my-extension`

**Best Practices**:
- Use semantic versioning
- Include comprehensive README
- Maintain changelog
- Provide type stubs

### Private PyPI Repository

#### Using pypiserver

```bash
# Install pypiserver
pip install pypiserver

# Run server
pypiserver run -p 8080 ~/packages

# Upload packages
twine upload --repository-url http://localhost:8080 dist/*

# Install from private server
pip install --index-url http://localhost:8080/simple/ my-extension
```

#### Using Artifactory/Nexus

**~/.pypirc**:
```ini
[distutils]
index-servers =
    private

[private]
repository = https://artifactory.company.com/artifactory/api/pypi/pypi-local
username = user
password = password
```

**Upload**:
```bash
twine upload --repository private dist/*
```

**Install**:
```bash
pip install \
  --index-url https://artifactory.company.com/artifactory/api/pypi/pypi-local/simple \
  my-extension
```

### Git-Based Installation

#### Install from Git Repository

```bash
# Install from main branch
pip install git+https://github.com/user/my-extension.git

# Install from specific branch
pip install git+https://github.com/user/my-extension.git@develop

# Install from tag
pip install git+https://github.com/user/my-extension.git@v0.1.0

# Install from commit
pip install git+https://github.com/user/my-extension.git@abc123
```

**In requirements.txt**:
```
my-extension @ git+https://github.com/user/my-extension.git@v0.1.0
```

**In pyproject.toml**:
```toml
[project]
dependencies = [
    "my-extension @ git+https://github.com/user/my-extension.git@v0.1.0",
]
```

#### Editable Install

```bash
# Clone repository
git clone https://github.com/user/my-extension.git
cd my-extension

# Install in editable mode
pip install -e .

# Or with maturin
maturin develop
```

### Binary Distribution

#### Pre-Built Wheels

```bash
# Build wheels for all platforms
./scripts/build_wheels.sh

# Distribute via file server
cp dist/*.whl /var/www/wheels/

# Install from URL
pip install https://example.com/wheels/my_extension-0.1.0-cp311-cp311-linux_x86_64.whl
```

#### Conda Packages

**meta.yaml**:
```yaml
package:
  name: my-extension
  version: 0.1.0

source:
  path: ..

build:
  number: 0
  script: maturin build --release && pip install target/wheels/*.whl

requirements:
  build:
    - python
    - rust
    - maturin
  host:
    - python
    - pip
  run:
    - python
    - numpy >=1.20

test:
  imports:
    - my_extension
  commands:
    - pytest tests/

about:
  home: https://github.com/user/my-extension
  license: MIT
  summary: High-performance Python extension
```

**Build**:
```bash
conda build conda-recipe/
conda install --use-local my-extension
```

### Source Distribution

#### sdist Structure

```
my_extension-0.1.0.tar.gz
├── Cargo.toml
├── Cargo.lock
├── pyproject.toml
├── README.md
├── LICENSE
├── MANIFEST.in
├── src/
│   └── lib.rs
├── python/
│   └── my_extension/
│       └── __init__.py
└── tests/
    └── test_basic.py
```

#### MANIFEST.in

```
# Include source files
include Cargo.toml
include Cargo.lock
include pyproject.toml
include README.md
include LICENSE
recursive-include src *.rs
recursive-include python *.py *.pyi

# Include tests
recursive-include tests *.py

# Exclude build artifacts
global-exclude *.pyc
global-exclude __pycache__
prune target
```

#### Build sdist

```bash
maturin sdist

# Install from sdist (requires Rust toolchain)
pip install my_extension-0.1.0.tar.gz
```

### Container Distribution

#### Docker Image

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install Rust (for building from source)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install package
COPY dist/*.whl /tmp/
RUN pip install /tmp/*.whl

# Run application
CMD ["python", "-c", "import my_extension; print(my_extension.__version__)"]
```

**Build and distribute**:
```bash
docker build -t my-extension:0.1.0 .
docker push registry.example.com/my-extension:0.1.0
```

#### Pre-Built Wheels in Container

```dockerfile
# Dockerfile.prebuilt
FROM python:3.11-slim

# Copy pre-built wheel
COPY dist/my_extension-0.1.0-cp311-cp311-manylinux_2_28_x86_64.whl /tmp/

# Install wheel
RUN pip install /tmp/my_extension-0.1.0-cp311-cp311-manylinux_2_28_x86_64.whl

# Application
WORKDIR /app
COPY app/ /app/

CMD ["python", "main.py"]
```

---

## 10. Troubleshooting

### Common Build Failures

#### Missing Python Development Headers

**Error**:
```
error: failed to run custom build command for `pyo3-ffi v0.20.0`
fatal error: Python.h: No such file or directory
```

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# RHEL/CentOS
sudo yum install python3-devel

# macOS (usually not needed)
brew install python@3.11

# Windows
# Install Python from python.org (includes headers)
```

#### Linker Errors

**Error**:
```
error: linking with `cc` failed: exit status: 1
undefined reference to `pthread_create'
```

**Solution**:
```toml
# Cargo.toml
[target.'cfg(unix)'.dependencies]
# Add missing system library
libc = "0.2"

# Or in build.rs
fn main() {
    println!("cargo:rustc-link-lib=pthread");
}
```

#### manylinux Incompatibility

**Error**:
```
ERROR: my_extension-0.1.0-cp311-cp311-linux_x86_64.whl is not a supported wheel on this platform.
```

**Solution**:
```bash
# Build with older manylinux version
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4 \
  build --release --manylinux 2_17  # More compatible

# Or use musllinux for maximum portability
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4-musllinux_1_2 \
  build --release
```

#### Cross-Compilation Failures

**Error**:
```
error: failed to run `rustc` to learn about target-specific information
```

**Solution**:
```bash
# Install target
rustup target add aarch64-unknown-linux-gnu

# Install cross-compilation toolchain
sudo apt-get install gcc-aarch64-linux-gnu

# Configure linker
cat >> ~/.cargo/config.toml << 'EOF'
[target.aarch64-unknown-linux-gnu]
linker = "aarch64-linux-gnu-gcc"
EOF
```

### Platform-Specific Issues

#### macOS: Unsupported Architecture

**Error**:
```
ImportError: dlopen(): symbol not found in flat namespace (_PyInit_my_extension)
```

**Solution**:
```bash
# Ensure correct architecture
rustc --version --verbose
# host: aarch64-apple-darwin (Apple Silicon)
# host: x86_64-apple-darwin (Intel)

# Build for correct architecture
rustup target add $(rustc -vV | grep host | cut -d' ' -f2)
maturin build --release
```

#### Windows: Missing Visual Studio

**Error**:
```
error: linker `link.exe` not found
```

**Solution**:
1. Install Visual Studio Build Tools
2. Or install full Visual Studio
3. Or use MinGW:
```bash
rustup target add x86_64-pc-windows-gnu
maturin build --release --target x86_64-pc-windows-gnu
```

#### Linux: GLIBC Version

**Error**:
```
ImportError: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.29' not found
```

**Solution**:
```bash
# Check system GLIBC version
ldd --version

# Build with compatible manylinux
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4 \
  build --release --manylinux 2_17  # GLIBC 2.17

# Or use static linking (musllinux)
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin:v1.4-musllinux_1_2 \
  build --release
```

### Dependency Resolution Problems

#### Conflicting Dependencies

**Error**:
```
error: failed to select a version for `serde`
```

**Solution**:
```toml
# Force specific version
[dependencies]
serde = "=1.0.192"

# Or use workspace dependencies
[workspace.dependencies]
serde = "1.0"

[dependencies]
serde.workspace = true
```

#### Missing Optional Dependencies

**Error**:
```
error[E0433]: failed to resolve: use of undeclared crate or module `rayon`
```

**Solution**:
```toml
[dependencies]
rayon = { version = "1.8", optional = true }

[features]
parallel = ["rayon"]  # Enable feature to use rayon
```

```bash
# Build with feature enabled
maturin build --release --features parallel
```

### ABI Compatibility Issues

#### Python Version Mismatch

**Error**:
```
ImportError: dynamic module does not define module export function (PyInit_my_extension)
```

**Solution**:
```bash
# Check Python version used for build
python --version

# Ensure consistent Python version
maturin build --release --interpreter python3.11

# Or specify in pyproject.toml
```

```toml
[project]
requires-python = ">=3.8,<3.13"
```

#### Limited API

```toml
# Use abi3 for forward compatibility
[dependencies]
pyo3 = { version = "0.20", features = ["abi3-py38"] }
```

**Benefits**:
- Single wheel for Python 3.8+
- No need to rebuild for new Python versions

**Limitations**:
- Slight performance overhead
- Limited to stable ABI functions

### Debug Techniques

#### Verbose Build Output

```bash
# Cargo verbose output
maturin build --release -vv

# Show linker invocation
export RUSTFLAGS="-C link-arg=-Wl,--verbose"
maturin build --release
```

#### Inspect Symbols

```bash
# List symbols in shared library
nm target/release/libmy_extension.so | grep PyInit

# Check dependencies
ldd target/release/libmy_extension.so

# macOS
otool -L target/release/libmy_extension.dylib

# Windows
dumpbin /DEPENDENTS target/release/my_extension.pyd
```

#### Debug Build

```toml
[profile.dev]
debug = true
opt-level = 0

[profile.release-with-debug]
inherits = "release"
debug = true
strip = false
```

```bash
# Build with debug symbols
maturin build --profile release-with-debug

# Debug with gdb/lldb
gdb python
(gdb) run -c "import my_extension; my_extension.function()"
```

### Performance Issues

#### Slow Compilation

**Solutions**:
```toml
# Use parallel compilation
[build]
jobs = 8

# Use incremental compilation (dev only)
[profile.dev]
incremental = true

# Reduce optimization level temporarily
[profile.release]
opt-level = 2  # Instead of 3
lto = "thin"   # Instead of "fat"
```

```bash
# Use sccache
export RUSTC_WRAPPER=sccache
maturin build --release
```

#### Runtime Performance

**Profiling**:
```bash
# Python profiling
python -m cProfile -o profile.stats script.py
python -m pstats profile.stats

# Rust profiling
cargo install flamegraph
maturin build --profile release-with-debug
sudo flamegraph python script.py

# py-spy
pip install py-spy
py-spy record -o profile.svg -- python script.py
```

**Common Issues**:
- Not releasing GIL: Use `py.allow_threads(||{})`
- Excessive Python/Rust boundary crossings
- Inefficient data conversion
- Missing SIMD optimizations

### Import Errors

#### Module Not Found

**Error**:
```
ModuleNotFoundError: No module named 'my_extension'
```

**Checklist**:
```bash
# 1. Check installation
pip list | grep my-extension

# 2. Check Python path
python -c "import sys; print(sys.path)"

# 3. Check wheel contents
unzip -l dist/*.whl

# 4. Verify module name matches
python -c "import my_extension; print(my_extension.__file__)"
```

#### Symbol Not Found

**Error**:
```
ImportError: dlopen(): symbol not found: _PyInit_my_extension
```

**Solutions**:
```toml
# Ensure correct crate type
[lib]
crate-type = ["cdylib"]

# Ensure correct module name
name = "my_extension"  # Must match Python import
```

```rust
// Ensure correct pymodule name
#[pymodule]
fn my_extension(_py: Python, m: &PyModule) -> PyResult<()> {
    // Name must match Cargo.toml
    Ok(())
}
```

---

## Appendix: Quick Reference

### Common Commands

```bash
# Development
maturin develop                    # Build and install for development
maturin develop --release          # Release build for development

# Building
maturin build --release            # Build release wheel
maturin sdist                      # Build source distribution
maturin build --release --sdist    # Build both

# Multi-platform
maturin build --release --find-interpreter  # All Python versions
maturin build --release --target <TARGET>   # Specific target

# Docker builds
docker run --rm -v $(pwd):/io ghcr.io/pyo3/maturin:v1.4 \
  build --release --manylinux 2_28

# Publishing
twine check dist/*                 # Validate packages
twine upload --repository testpypi dist/*   # Test PyPI
twine upload dist/*                # Production PyPI
```

### Configuration Templates

**Minimal pyproject.toml**:
```toml
[build-system]
requires = ["maturin>=1.4,<2.0"]
build-backend = "maturin"

[project]
name = "my_extension"
version = "0.1.0"
requires-python = ">=3.8"
```

**Production pyproject.toml**: See [Complete pyproject.toml Template](#complete-pyprojecttoml-template)

**Minimal Cargo.toml**:
```toml
[package]
name = "my_extension"
version = "0.1.0"
edition = "2021"

[lib]
name = "my_extension"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
```

### Platform Targets

```
Linux:
  x86_64-unknown-linux-gnu
  x86_64-unknown-linux-musl
  aarch64-unknown-linux-gnu
  aarch64-unknown-linux-musl

macOS:
  x86_64-apple-darwin
  aarch64-apple-darwin
  universal2-apple-darwin

Windows:
  x86_64-pc-windows-msvc
  i686-pc-windows-msvc
  x86_64-pc-windows-gnu
```

### Environment Variables

```bash
# Rust
RUSTFLAGS="-C target-cpu=native"
CARGO_BUILD_JOBS=8
RUSTC_WRAPPER=sccache

# Python
PYO3_PYTHON=/usr/bin/python3.11
PYO3_CROSS_LIB_DIR=/usr/lib/python3.11

# maturin
MATURIN_PYPI_TOKEN=pypi-...
```

---

**End of PyO3 Packaging & Distribution Reference**

This comprehensive reference covers all aspects of packaging, building, and distributing PyO3 extensions. For specific use cases, refer to the relevant sections and adapt the examples to your project's needs.
