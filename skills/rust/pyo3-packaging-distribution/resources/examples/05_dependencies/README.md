# Example 05: Dependencies

Dependency management demonstrating how to handle both Rust and Python dependencies, including optional dependencies and version constraints.

## What This Demonstrates

- Rust dependencies in `Cargo.toml`
- Python dependencies in `pyproject.toml`
- Optional dependencies for different use cases
- Version constraints and compatibility
- Dev dependencies vs runtime dependencies

## Project Structure

```
05_dependencies/
├── src/
│   └── lib.rs              # Uses Rust dependencies
├── Cargo.toml              # Rust dependency configuration
├── pyproject.toml          # Python dependency configuration
└── README.md               # This file
```

## Key Concepts

### Dependency Types

#### 1. Rust Dependencies (Cargo.toml)
```toml
[dependencies]
pyo3 = "0.20"              # Required for PyO3
serde = "1.0"              # Runtime dependency
statrs = "0.16"            # Another runtime dependency

[dev-dependencies]
criterion = "0.5"          # Only for tests/benchmarks
```

#### 2. Python Dependencies (pyproject.toml)
```toml
[project]
dependencies = [           # Always installed
    "numpy>=1.20.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0.0"]    # pip install package[dev]
viz = ["matplotlib"]       # pip install package[viz]
```

### Version Constraints

#### Rust (Cargo.toml)
```toml
pyo3 = "0.20"              # Compatible with 0.20.x
serde = "1.0"              # Compatible with 1.x
statrs = ">=0.16, <0.20"   # Range
```

#### Python (pyproject.toml)
```toml
"numpy>=1.20.0"            # Minimum version
"numpy>=1.20.0,<2.0"       # Upper bound
"numpy==1.20.0"            # Exact version (avoid)
```

## Building

### Development Build
```bash
# Install with all dependencies
pip install -e ".[dev]"
maturin develop

# Install with specific extras
pip install -e ".[viz]"
```

### Production Build
```bash
maturin build --release
```

## Rust Dependencies in Detail

### Core Dependencies

#### PyO3
```toml
pyo3 = { version = "0.20", features = ["extension-module"] }
```
- `extension-module` - Required for Python extensions
- Must NOT link Python dynamically

#### Serde
```toml
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```
- Serialization framework
- `derive` feature for automatic trait derivation

### Dev Dependencies

Not included in final wheel:
```toml
[dev-dependencies]
criterion = "0.5"     # Benchmarking
proptest = "1.0"      # Property testing
```

## Python Dependencies in Detail

### Required Dependencies

Always installed with the package:
```toml
dependencies = [
    "numpy>=1.20.0",
    "typing-extensions>=4.0.0; python_version<'3.10'",
]
```

### Conditional Dependencies

Environment markers:
```toml
"typing-extensions>=4.0.0; python_version<'3.10'"
"pywin32; platform_system=='Windows'"
"dataclasses; python_version<'3.7'"
```

### Optional Dependencies

Group related dependencies:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "mypy>=1.0.0",
]
docs = [
    "sphinx>=5.0.0",
    "sphinx-rtd-theme>=1.0.0",
]
viz = [
    "matplotlib>=3.5.0",
]
all = ["dependencies_example[dev,docs,viz]"]
```

Install with:
```bash
pip install dependencies_example[dev]
pip install dependencies_example[viz]
pip install dependencies_example[all]
```

## Testing

### Rust Tests
```bash
cargo test
```

### Python Usage
```python
import numpy as np
from dependencies_example import DataPoint, to_json, from_json, statistics

# Test serialization (uses serde)
point = DataPoint(1.0, 2.0, "A")
json_str = to_json(point)
print(json_str)  # {"x":1.0,"y":2.0,"label":"A"}

restored = from_json(json_str)
print(restored)  # DataPoint(1.0, 2.0, 'A')

# Test statistics (uses statrs)
values = [1.0, 2.0, 3.0, 4.0, 5.0]
stats = statistics(values)
print(f"Mean: {stats['mean']}")      # 3.0
print(f"Median: {stats['median']}")  # 3.0
print(f"Std Dev: {stats['std_dev']}")

# Use numpy (Python dependency)
arr = np.array([point.x, point.y])
print(f"Numpy array: {arr}")
```

## Dependency Best Practices

### 1. Pin Build Dependencies
```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]  # Pin major version
```

### 2. Flexible Runtime Dependencies
```toml
dependencies = [
    "numpy>=1.20.0",  # Allow minor/patch updates
]
```

### 3. Group Optional Dependencies
```toml
[project.optional-dependencies]
dev = [...]    # Development tools
test = [...]   # Testing tools
docs = [...]   # Documentation
all = ["package[dev,test,docs]"]  # Everything
```

### 4. Use Environment Markers
```toml
"pywin32; platform_system=='Windows'"
"typing-extensions; python_version<'3.10'"
```

### 5. Avoid Exact Pins
```toml
# Bad - too restrictive
"numpy==1.20.0"

# Good - allows compatible updates
"numpy>=1.20.0,<2.0"
```

## Checking Dependencies

### Rust Dependencies
```bash
# Show dependency tree
cargo tree

# Check for updates
cargo outdated

# Verify compatibility
cargo check
```

### Python Dependencies
```bash
# Show installed packages
pip list

# Show dependency tree
pip install pipdeptree
pipdeptree

# Check for security issues
pip install safety
safety check
```

## Common Patterns

### Pattern 1: Version-Specific Features
```toml
[dependencies]
pyo3 = "0.20"

[dependencies.serde]
version = "1.0"
features = ["derive"]
optional = true

[features]
json = ["serde", "serde_json"]
```

```bash
# Build with feature
maturin build --features json
```

### Pattern 2: Platform-Specific Dependencies
```toml
[target.'cfg(windows)'.dependencies]
winapi = "0.3"

[target.'cfg(unix)'.dependencies]
libc = "0.2"
```

### Pattern 3: Optional Python Dependencies
```python
# In your Python code
try:
    import matplotlib
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

def plot_data(data):
    if not HAS_MATPLOTLIB:
        raise ImportError("Install with: pip install package[viz]")
    # Use matplotlib
```

## Verification

After building, check dependencies:

```bash
# Check Rust compilation
cargo build --release

# Verify wheel doesn't include dev dependencies
unzip -l target/wheels/dependencies_example-*.whl

# Check Python dependencies
pip install dependencies_example
pip show dependencies_example
```

## Next Steps

See `06_feature_flags` for:
- Cargo feature flags
- Conditional compilation
- Optional functionality
- Feature combinations
