# Example 02: Metadata Configuration

Complete package metadata configuration for PyPI distribution, demonstrating all important metadata fields and best practices.

## What This Demonstrates

- Complete `Cargo.toml` metadata (authors, license, description, etc.)
- Comprehensive `pyproject.toml` configuration
- PyPI classifiers for discoverability
- Project URLs and documentation links
- Accessing package metadata at runtime

## Project Structure

```
02_metadata_config/
├── src/
│   └── lib.rs          # Rust source with metadata access
├── Cargo.toml          # Complete Rust package metadata
├── pyproject.toml      # Complete Python package metadata
└── README.md           # This file
```

## Key Concepts

### Cargo.toml Metadata
- `authors` - Package authors
- `description` - Short package description
- `license` - SPDX license identifier (dual license example)
- `repository` / `homepage` - Project URLs
- `keywords` / `categories` - Discoverability tags

### pyproject.toml Metadata
- `project.version` - Package version
- `project.authors` - Author information
- `project.maintainers` - Current maintainers
- `project.classifiers` - PyPI trove classifiers
- `project.urls` - Links to documentation, issues, etc.

### Runtime Metadata Access
- `env!("CARGO_PKG_NAME")` - Access package name at compile time
- `env!("CARGO_PKG_VERSION")` - Access version
- Package metadata available to Python code

## Building

### Development Build
```bash
pip install maturin
maturin develop
```

### Production Build
```bash
# Build wheel with all metadata
maturin build --release

# Inspect wheel metadata
unzip -p target/wheels/metadata_config-*.whl */METADATA
```

## Testing

### Rust Tests
```bash
cargo test
```

### Python Usage
```python
import metadata_config

# Use the functions
print(metadata_config.factorial(5))  # 120
print(metadata_config.is_prime(17))  # True

# Check package metadata
info = metadata_config.package_info()
print(f"Package: {info['name']} v{info['version']}")
print(f"Authors: {info['authors']}")
print(f"Description: {info['description']}")
```

## PyPI Classifiers

Classifiers help users discover your package on PyPI:

- **Development Status** - Project maturity (1-7)
- **Intended Audience** - Target users
- **License** - SPDX identifiers
- **Programming Language** - Rust, Python versions
- **Operating System** - Supported platforms
- **Topic** - Categorization

Complete list: https://pypi.org/classifiers/

## License Best Practices

### Dual Licensing (Recommended for Rust)
```toml
license = "MIT OR Apache-2.0"
```

This is standard in the Rust ecosystem and maximizes compatibility.

### Single License
```toml
license = "MIT"
```

### Custom License File
```toml
license = { file = "LICENSE.txt" }
```

## Verification

After building, verify metadata:

```bash
# Check wheel contents
unzip -l target/wheels/metadata_config-*.whl

# Read METADATA file
unzip -p target/wheels/metadata_config-*.whl */METADATA | head -30

# Should show:
# Metadata-Version: 2.1
# Name: metadata_config
# Version: 0.1.0
# Classifier: Development Status :: 4 - Beta
# Classifier: Programming Language :: Rust
# ...
```

## Next Steps

See `03_versioning` for:
- Semantic versioning strategies
- Version synchronization between Cargo.toml and pyproject.toml
- Runtime version checks
- Changelog management
