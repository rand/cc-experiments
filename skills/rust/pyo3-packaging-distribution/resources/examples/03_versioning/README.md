# Example 03: Versioning

Version management and runtime access, demonstrating semantic versioning, version synchronization, and runtime version checks.

## What This Demonstrates

- Semantic versioning (SemVer) in Rust packages
- Version synchronization between Cargo.toml and pyproject.toml
- Runtime version information access
- Version comparison and compatibility checks
- `__version__` attribute for Python packages

## Project Structure

```
03_versioning/
├── src/
│   └── lib.rs          # Version access and comparison functions
├── Cargo.toml          # Single source of truth for version
├── pyproject.toml      # Dynamic version from Cargo.toml
└── README.md           # This file
```

## Key Concepts

### Semantic Versioning (SemVer)

Format: `MAJOR.MINOR.PATCH`

- **MAJOR** - Incompatible API changes
- **MINOR** - Backward-compatible functionality additions
- **PATCH** - Backward-compatible bug fixes

Examples:
- `0.1.0` - Initial development
- `1.0.0` - First stable release
- `1.1.0` - Added features (compatible with 1.0.0)
- `1.1.1` - Bug fix (compatible with 1.1.0)
- `2.0.0` - Breaking changes (NOT compatible with 1.x)

### Version Synchronization

#### Option 1: Single Source (Recommended)
```toml
# pyproject.toml
[project]
dynamic = ["version"]

[tool.maturin]
# Reads from Cargo.toml automatically
```

#### Option 2: Explicit Version
```toml
# pyproject.toml
[project]
version = "0.1.0"  # Must match Cargo.toml
```

### Runtime Version Access

```rust
// In Rust code
env!("CARGO_PKG_VERSION")  // "0.1.0"
```

```python
# In Python code
import versioning_example
print(versioning_example.__version__)  # "0.1.0"
```

## Building

### Development Build
```bash
maturin develop
```

### Check Version Sync
```bash
# Extract version from Cargo.toml
cargo metadata --no-deps --format-version 1 | jq -r '.packages[0].version'

# Check built wheel version
unzip -p target/wheels/versioning_example-*.whl */METADATA | grep "^Version:"
```

## Testing

### Rust Tests
```bash
cargo test
```

### Python Usage
```python
import versioning_example

# Get version string
print(versioning_example.version())  # "0.1.0"
print(versioning_example.__version__)  # "0.1.0"

# Get detailed version info
info = versioning_example.version_info()
print(f"Major: {info['major']}")  # 0
print(f"Minor: {info['minor']}")  # 1
print(f"Patch: {info['patch']}")  # 0

# Check version compatibility
is_compatible = versioning_example.check_version("0.1.0")
print(f"Compatible: {is_compatible}")  # True

# Get build information
build = versioning_example.build_info()
print(f"Version: {build['version']}")
print(f"Profile: {build['profile']}")  # debug or release
```

## Version Management Workflow

### 1. Update Version
```bash
# Edit Cargo.toml
version = "0.2.0"

# Maturin automatically uses this version
```

### 2. Build with New Version
```bash
maturin build --release
```

### 3. Verify Version
```bash
# Check wheel filename
ls target/wheels/
# versioning_example-0.2.0-...whl

# Check metadata
unzip -p target/wheels/versioning_example-0.2.0-*.whl */METADATA | grep Version
# Version: 0.2.0
```

## Pre-release and Build Metadata

### Pre-release Versions
```toml
# Cargo.toml
version = "1.0.0-alpha.1"
version = "1.0.0-beta.2"
version = "1.0.0-rc.1"
```

### Build Metadata (Optional)
```toml
version = "1.0.0+20241030"
```

## Best Practices

### 1. Use Single Source of Truth
Let maturin read version from `Cargo.toml`:
```toml
# pyproject.toml
[project]
dynamic = ["version"]
```

### 2. Expose Version to Python
```rust
#[pymodule]
fn mymodule(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
```

### 3. Validate Version Format
```bash
# Ensure version is valid SemVer
cargo publish --dry-run
```

### 4. Tag Releases
```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

## Common Patterns

### Version-Specific Behavior
```rust
#[pyfunction]
fn feature_available() -> bool {
    let version = env!("CARGO_PKG_VERSION");
    compare_versions(version, "1.0.0")
}
```

### Deprecation Warnings
```python
import versioning_example
import warnings

if versioning_example.check_version("2.0.0"):
    warnings.warn(
        "This API is deprecated in 2.0.0",
        DeprecationWarning
    )
```

## Next Steps

See `04_mixed_layout` for:
- Mixed Rust/Python project structure
- Pure Python code alongside Rust extensions
- Organizing hybrid packages
- Importing Python modules from Rust extensions
