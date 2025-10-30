# Example 06: Feature Flags

Feature flags and conditional compilation using Cargo features to create minimal or full-featured builds.

## What This Demonstrates

- Cargo feature flags
- Conditional compilation with `cfg!(feature = "...")`
- Optional dependencies
- Building minimal vs full-featured packages
- Feature detection at runtime

## Project Structure

```
06_feature_flags/
├── src/
│   └── lib.rs              # Conditional code based on features
├── Cargo.toml              # Feature definitions
├── pyproject.toml          # Maturin feature configuration
└── README.md               # This file
```

## Key Concepts

### Feature Flags

Features allow conditional inclusion of code and dependencies:

```rust
// Only compiled if "json" feature is enabled
#[cfg(feature = "json")]
fn json_function() { ... }

// Only compiled if "parallel" feature is enabled
#[cfg(feature = "parallel")]
fn parallel_function() { ... }
```

### Benefits

1. **Smaller Binary Size** - Exclude unused features
2. **Fewer Dependencies** - Only include what's needed
3. **Faster Compilation** - Less code to compile
4. **User Choice** - Users decide which features they need

## Feature Definitions

### Cargo.toml

```toml
[dependencies]
# Optional dependencies
serde = { version = "1.0", optional = true }
rayon = { version = "1.8", optional = true }

[features]
# Default features
default = []

# Named features
json = ["dep:serde", "dep:serde_json"]
parallel = ["dep:rayon"]

# Meta-feature that enables multiple features
full = ["json", "parallel"]
```

## Building with Features

### Minimal Build (No Features)
```bash
maturin build --release
```

This creates the smallest binary with only core functionality.

### Build with Specific Features
```bash
# Single feature
maturin build --release --features json

# Multiple features
maturin build --release --features json,parallel

# All features
maturin build --release --features full
```

### Development Build with Features
```bash
# Minimal
maturin develop

# With features
maturin develop --features json,parallel
```

## Testing

### Test Specific Features
```bash
# Test with no features
cargo test

# Test with json feature
cargo test --features json

# Test all features
cargo test --all-features
```

### Python Usage

```python
import feature_flags

# Check which features are available
info = feature_flags.feature_info()
print(f"JSON support: {info['json']}")
print(f"Advanced math: {info['advanced_math']}")
print(f"Parallel: {info['parallel']}")

# Check individual feature
if feature_flags.has_feature("json"):
    from feature_flags import JsonData, to_json_string
    data = JsonData("test", 42)
    json = to_json_string(data)
    print(json)

# Try to use feature-gated function
try:
    # This will fail if 'parallel' feature not enabled
    result = feature_flags.parallel_sum([1, 2, 3])
    print(f"Parallel sum: {result}")
except AttributeError:
    print("Parallel feature not enabled")
```

## Feature Patterns

### Pattern 1: Optional Functionality
```rust
#[cfg(feature = "json")]
#[pyfunction]
fn json_export(data: &Data) -> PyResult<String> {
    serde_json::to_string(data).map_err(...)
}
```

### Pattern 2: Feature-Specific Types
```rust
#[cfg(feature = "advanced")]
#[pyclass]
pub struct AdvancedProcessor {
    // Complex implementation
}
```

### Pattern 3: Feature Detection
```rust
#[pyfunction]
fn supports_json() -> bool {
    cfg!(feature = "json")
}
```

### Pattern 4: Graceful Degradation
```rust
#[pyfunction]
fn process(data: Vec<i64>) -> i64 {
    #[cfg(feature = "parallel")]
    {
        use rayon::prelude::*;
        return data.par_iter().sum();
    }

    #[cfg(not(feature = "parallel"))]
    {
        return data.iter().sum();
    }
}
```

## Feature Dependencies

### Feature Enabling Other Features
```toml
[features]
# "full" enables both json and parallel
full = ["json", "parallel"]

# "json" requires serde and serde_json
json = ["dep:serde", "dep:serde_json"]
```

### Optional Dependencies
```toml
[dependencies]
# Only included if "json" feature is enabled
serde = { version = "1.0", optional = true }

[features]
json = ["dep:serde"]
```

## Binary Size Comparison

```bash
# Build minimal
maturin build --release
ls -lh target/wheels/feature_flags-*-minimal.whl

# Build full
maturin build --release --features full
ls -lh target/wheels/feature_flags-*-full.whl

# Compare sizes
# Minimal: ~500KB
# Full: ~2MB (example sizes)
```

## Distribution Strategies

### Strategy 1: Multiple Wheels
Build different wheels for different use cases:

```bash
# Minimal distribution
maturin build --release -o dist/minimal/

# Full distribution
maturin build --release --features full -o dist/full/
```

### Strategy 2: Single Full-Featured Wheel
Build once with all features:

```toml
# pyproject.toml
[tool.maturin]
features = ["full"]
```

### Strategy 3: User-Configurable Build
Let users build with desired features:

```bash
# In documentation
pip install maturin
maturin build --features json,parallel
pip install target/wheels/feature_flags-*.whl
```

## Feature Configuration in pyproject.toml

### Default Features
```toml
[tool.maturin]
features = ["json"]  # Always build with json
```

### No Features
```toml
[tool.maturin]
# Build minimal by default (commented out)
# features = []
```

## Best Practices

### 1. Sensible Defaults
```toml
[features]
default = ["json"]  # Most users need JSON
```

### 2. Feature Documentation
```rust
/// JSON serialization support.
///
/// Available when compiled with `--features json`
#[cfg(feature = "json")]
#[pyfunction]
fn to_json(...) -> ... { ... }
```

### 3. Feature Detection
```python
# In Python wrapper
if not has_feature("json"):
    raise ImportError(
        "JSON support not available. "
        "Reinstall with: maturin build --features json"
    )
```

### 4. Test All Combinations
```bash
# In CI
cargo test --no-default-features
cargo test --features json
cargo test --features parallel
cargo test --all-features
```

### 5. Document Feature Requirements
```markdown
## Features

- `json` - JSON serialization (requires serde)
- `parallel` - Parallel processing (requires rayon)
- `advanced_math` - Advanced math functions (requires statrs)
- `full` - All features enabled
```

## Common Issues

### Issue 1: Missing Feature
```
AttributeError: module 'feature_flags' has no attribute 'parallel_sum'
```

**Solution**: Rebuild with feature enabled
```bash
maturin develop --features parallel
```

### Issue 2: Feature Not Available
Check at runtime:
```python
if not feature_flags.has_feature("json"):
    print("JSON feature not available")
```

### Issue 3: Dependency Conflicts
Some features may have conflicting dependencies. Use feature groups:
```toml
[features]
# Mutually exclusive features
mode_a = [...]
mode_b = [...]
# Don't enable both!
```

## Next Steps

See `07_cross_compile` for:
- Cross-compilation for multiple platforms
- Platform-specific builds
- Target architecture configuration
- Universal wheels
