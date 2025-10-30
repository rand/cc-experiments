# PyO3 Packaging and Distribution Examples

Progressive examples demonstrating packaging and distribution patterns for PyO3 projects, from basic setup to production releases.

## Overview

These examples build on each other, progressing from simple package setup to complete production workflows. Each example is a complete, runnable project with detailed documentation.

## Examples

### Beginner (01-03)

#### [01_basic_package](./01_basic_package/)
**Minimal maturin package setup**

- Minimal Cargo.toml and pyproject.toml configuration
- Basic #[pyfunction] and #[pymodule] usage
- Simple function exports to Python
- Foundation for all other examples

**Key Concepts**: cdylib crate type, extension-module feature, basic PyO3 bindings

#### [02_metadata_config](./02_metadata_config/)
**Complete package metadata**

- Comprehensive Cargo.toml metadata (authors, license, description)
- Complete pyproject.toml with classifiers and URLs
- PyPI trove classifiers for discoverability
- Runtime metadata access

**Key Concepts**: Package metadata, PyPI classifiers, dual licensing, documentation URLs

#### [03_versioning](./03_versioning/)
**Version management and runtime access**

- Semantic versioning (SemVer)
- Version synchronization between Cargo.toml and pyproject.toml
- Runtime version information
- Version comparison and compatibility checks

**Key Concepts**: SemVer, dynamic versioning, version detection, __version__ attribute

### Intermediate (04-07)

#### [04_mixed_layout](./04_mixed_layout/)
**Mixed Rust/Python project structure**

- Combining Rust extensions with pure Python code
- Python wrapper around Rust core
- python-source directory configuration
- Module naming conventions (_core for internal)

**Key Concepts**: Mixed layout, Python wrappers, python-source, public vs internal APIs

#### [05_dependencies](./05_dependencies/)
**Rust and Python dependency management**

- Rust dependencies in Cargo.toml
- Python dependencies in pyproject.toml
- Optional dependencies and extras
- Version constraints

**Key Concepts**: Dependency management, optional dependencies, version constraints, dev vs runtime deps

#### [06_feature_flags](./06_feature_flags/)
**Optional features and conditional compilation**

- Cargo feature flags
- Conditional compilation with cfg!
- Optional dependencies
- Building minimal vs full-featured packages

**Key Concepts**: Feature flags, conditional compilation, optional deps, binary size optimization

#### [07_cross_compile](./07_cross_compile/)
**Cross-compilation for multiple platforms**

- Platform detection at compile-time and runtime
- Cross-compilation with maturin
- Platform-specific code and dependencies
- Universal wheels for macOS

**Key Concepts**: Cross-compilation, target triples, platform detection, universal binaries

### Advanced (08-10)

#### [08_ci_cd_pipeline](./08_ci_cd_pipeline/)
**Complete GitHub Actions workflow**

- Automated CI with linting and testing
- Multi-platform wheel building
- Automated PyPI publishing on release
- Artifact management and verification

**Key Concepts**: GitHub Actions, CI/CD, automated publishing, release workflow

#### [09_multi_platform](./09_multi_platform/)
**Multi-platform wheel building**

- Building for Linux (manylinux, musllinux)
- macOS wheels (Intel, Apple Silicon, universal2)
- Windows wheels (x64, x86)
- Comprehensive platform testing

**Key Concepts**: manylinux, musllinux, universal2, platform compatibility, wheel tags

#### [10_production_release](./10_production_release/)
**Complete production release workflow**

- Semantic versioning strategy
- Changelog management (Keep a Changelog)
- Automated version validation
- PyPI publishing with documentation
- GitHub releases with release notes

**Key Concepts**: SemVer, changelog, release automation, production workflow, documentation

## Learning Path

### Path 1: Quick Start (Minimal Setup)
```
01 → 02 → 03 → 08
```
Get a basic package published quickly.

### Path 2: Hybrid Packages (Rust + Python)
```
01 → 04 → 05 → 06
```
Build packages with both Rust and Python code.

### Path 3: Production Ready (Complete Workflow)
```
01 → 02 → 03 → 07 → 08 → 09 → 10
```
Full production release pipeline.

### Path 4: Advanced Features (Optimization)
```
01 → 05 → 06 → 07 → 09
```
Feature flags, cross-compilation, multi-platform.

## Quick Reference

### Building Examples

```bash
# Navigate to any example
cd 01_basic_package

# Development build
pip install maturin
maturin develop

# Production build
maturin build --release

# Test
cargo test
python -c "import package_name"
```

### Common Commands

```bash
# Install maturin
pip install maturin

# Create new project
maturin new my-project
cd my-project

# Development mode (editable install)
maturin develop

# Build wheel
maturin build --release

# Build for specific platform
maturin build --target x86_64-unknown-linux-gnu

# Publish to PyPI
maturin publish
```

## Key Concepts Summary

### Package Configuration

| File | Purpose | Key Fields |
|------|---------|------------|
| Cargo.toml | Rust configuration | name, version, dependencies, features |
| pyproject.toml | Python metadata | name, version, dependencies, classifiers |
| src/lib.rs | Rust source | #[pyfunction], #[pymodule], #[pyclass] |

### Build Targets

| Platform | Target Triple | Wheel Tag |
|----------|---------------|-----------|
| Linux x64 | x86_64-unknown-linux-gnu | manylinux_2_17_x86_64 |
| Linux ARM64 | aarch64-unknown-linux-gnu | manylinux_2_17_aarch64 |
| macOS Intel | x86_64-apple-darwin | macosx_10_12_x86_64 |
| macOS ARM | aarch64-apple-darwin | macosx_11_0_arm64 |
| macOS Universal | universal2-apple-darwin | macosx_11_0_universal2 |
| Windows x64 | x86_64-pc-windows-msvc | win_amd64 |

### Version Management

| Version | Type | Example |
|---------|------|---------|
| Major.Minor.Patch | Stable | 1.0.0 |
| Major.Minor.Patch-alpha.N | Alpha | 1.0.0-alpha.1 |
| Major.Minor.Patch-beta.N | Beta | 1.0.0-beta.1 |
| Major.Minor.Patch-rc.N | Release Candidate | 1.0.0-rc.1 |

## Troubleshooting

### Common Issues

**Issue**: `maturin: command not found`
```bash
pip install maturin
```

**Issue**: `error: crate type must be cdylib`
```toml
# Cargo.toml
[lib]
crate-type = ["cdylib"]
```

**Issue**: `ImportError: No module named 'package'`
```bash
# Ensure you ran maturin develop
maturin develop
```

**Issue**: Cross-compilation fails
```bash
# Install target
rustup target add x86_64-unknown-linux-gnu
```

**Issue**: Version mismatch
```bash
# Ensure versions match in both files
grep version Cargo.toml
grep version pyproject.toml
```

## Best Practices

1. **Start Simple** - Begin with 01_basic_package, add complexity as needed
2. **Use Dynamic Versioning** - Let maturin read version from Cargo.toml
3. **Document Everything** - Include docstrings, README, and examples
4. **Test Thoroughly** - Rust tests + Python tests + CI
5. **Automate Releases** - Use GitHub Actions for consistent releases
6. **Follow SemVer** - Clear versioning helps users understand changes
7. **Maintain Changelog** - Keep users informed of changes

## Resources

- [PyO3 Documentation](https://pyo3.rs/)
- [Maturin Guide](https://www.maturin.rs/)
- [Python Packaging Guide](https://packaging.python.org/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)

## Contributing

To add new examples or improve existing ones:

1. Follow the progressive structure (beginner → intermediate → advanced)
2. Include complete project with Cargo.toml, pyproject.toml, src/lib.rs, README.md
3. Keep examples focused on 1-2 key concepts
4. Provide clear documentation and usage examples
5. Ensure all examples are runnable and tested

## License

Examples are provided under MIT OR Apache-2.0 license for maximum compatibility.
