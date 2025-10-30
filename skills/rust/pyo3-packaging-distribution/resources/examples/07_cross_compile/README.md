# Example 07: Cross Compilation

Cross-compilation for multiple platforms demonstrating platform detection, architecture-specific code, and building wheels for different targets.

## What This Demonstrates

- Cross-compilation with maturin
- Platform detection at compile-time and runtime
- Architecture-specific optimizations
- Platform-specific dependencies
- Building universal wheels

## Project Structure

```
07_cross_compile/
├── src/
│   └── lib.rs              # Platform-aware code
├── Cargo.toml              # Platform-specific dependencies
├── pyproject.toml          # Multi-platform classifiers
└── README.md               # This file
```

## Key Concepts

### Target Triples

Format: `{arch}-{vendor}-{os}-{abi}`

Common targets:
- `x86_64-unknown-linux-gnu` - Linux (64-bit)
- `aarch64-unknown-linux-gnu` - Linux ARM64
- `x86_64-apple-darwin` - macOS Intel
- `aarch64-apple-darwin` - macOS Apple Silicon
- `x86_64-pc-windows-msvc` - Windows (64-bit)
- `i686-pc-windows-msvc` - Windows (32-bit)

### Platform Detection

#### Compile-Time (Rust)
```rust
#[cfg(target_os = "linux")]
fn linux_specific() { ... }

#[cfg(target_arch = "x86_64")]
fn x86_64_optimized() { ... }

#[cfg(unix)]
fn unix_platforms() { ... }
```

#### Runtime (Rust)
```rust
use std::env;
let os = env::consts::OS;  // "linux", "macos", "windows"
let arch = env::consts::ARCH;  // "x86_64", "aarch64"
```

## Building for Multiple Platforms

### Local Build (Native)
```bash
# Build for your current platform
maturin build --release
```

### Cross-Compilation

#### Install Cross-Compilation Tools
```bash
# Install rustup targets
rustup target add x86_64-unknown-linux-gnu
rustup target add aarch64-unknown-linux-gnu
rustup target add x86_64-apple-darwin
rustup target add aarch64-apple-darwin
rustup target add x86_64-pc-windows-msvc
```

#### Build for Specific Target
```bash
# Linux x86_64
maturin build --release --target x86_64-unknown-linux-gnu

# Linux ARM64
maturin build --release --target aarch64-unknown-linux-gnu

# macOS Intel
maturin build --release --target x86_64-apple-darwin

# macOS Apple Silicon
maturin build --release --target aarch64-apple-darwin

# Windows
maturin build --release --target x86_64-pc-windows-msvc
```

### Universal Wheels (macOS)

Build single wheel for both Intel and Apple Silicon:
```bash
maturin build --release --target universal2-apple-darwin
```

This creates a "fat binary" containing both architectures.

## Using Docker for Cross-Compilation

### Build Linux Wheels on Any Platform
```bash
# Use manylinux Docker image
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin \
  build --release --manylinux 2014

# This produces wheels compatible with most Linux distributions
```

### Supported manylinux Tags
- `manylinux_2_17` - CentOS 7 compatible
- `manylinux_2_28` - Debian 11+ compatible
- `musllinux_1_2` - Alpine Linux

## Platform-Specific Code

### Conditional Compilation
```rust
// Include only on Linux
#[cfg(target_os = "linux")]
use libc;

// Include only on Windows
#[cfg(windows)]
use winapi;

// Architecture-specific
#[cfg(target_arch = "x86_64")]
fn optimized_x86_64() { ... }

#[cfg(target_arch = "aarch64")]
fn optimized_arm64() { ... }
```

### Platform-Specific Dependencies
```toml
# Cargo.toml
[target.'cfg(unix)'.dependencies]
libc = "0.2"

[target.'cfg(windows)'.dependencies]
winapi = "0.3"

[target.'cfg(target_os = "macos")'.dependencies]
core-foundation = "0.9"
```

## Testing

### Rust Tests
```bash
# Native tests
cargo test

# Test for specific target (requires target installed)
cargo test --target x86_64-unknown-linux-gnu
```

### Python Usage
```python
import cross_compile

# Get runtime platform info
info = cross_compile.platform_info()
print(f"OS: {info['os']}")            # linux, macos, windows
print(f"Arch: {info['arch']}")        # x86_64, aarch64
print(f"Family: {info['family']}")    # unix, windows

# Get build-time platform info
build = cross_compile.build_platform()
print(f"Built for: {build['target']}")
print(f"Is Linux: {build['is_linux']}")
print(f"Is x86_64: {build['is_x86_64']}")

# Platform detection
if cross_compile.is_platform("linux"):
    print("Running on Linux")

# Platform-specific info
print(f"Path separator: {cross_compile.path_separator()}")
print(f"CPU cores: {cross_compile.cpu_count()}")

# Use optimized functions
result = cross_compile.optimized_sum([1, 2, 3, 4, 5])
print(f"Sum: {result}")
```

## Wheel Naming

Wheels follow PEP 425 naming:
```
{distribution}-{version}-{python}-{abi}-{platform}.whl
```

Examples:
```
cross_compile-0.1.0-cp311-cp311-manylinux_2_17_x86_64.whl
cross_compile-0.1.0-cp311-cp311-macosx_11_0_arm64.whl
cross_compile-0.1.0-cp311-cp311-win_amd64.whl
```

## CI/CD Cross-Compilation

### GitHub Actions Example
```yaml
name: Build Wheels

on: [push]

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Build wheels
        uses: PyO3/maturin-action@v1
        with:
          command: build
          args: --release --out dist

      - uses: actions/upload-artifact@v3
        with:
          name: wheels
          path: dist
```

See `08_ci_cd_pipeline` for complete example.

## Platform-Specific Optimizations

### SIMD on x86_64
```rust
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2")]
unsafe fn sum_avx2(data: &[i64]) -> i64 {
    // Use AVX2 instructions
}
```

### NEON on ARM
```rust
#[cfg(target_arch = "aarch64")]
fn sum_neon(data: &[i64]) -> i64 {
    // Use ARM NEON instructions
}
```

## Common Issues

### Issue 1: Missing Target
```
error: target not found: aarch64-unknown-linux-gnu
```

**Solution**: Install target
```bash
rustup target add aarch64-unknown-linux-gnu
```

### Issue 2: Cross-Compilation Linker Error

**Solution**: Install cross-compilation toolchain
```bash
# Ubuntu/Debian
sudo apt install gcc-aarch64-linux-gnu

# Set linker in .cargo/config.toml
[target.aarch64-unknown-linux-gnu]
linker = "aarch64-linux-gnu-gcc"
```

### Issue 3: macOS Universal Binary Fails

**Solution**: Ensure both targets are installed
```bash
rustup target add x86_64-apple-darwin
rustup target add aarch64-apple-darwin
```

## Best Practices

### 1. Test on Target Platforms
Don't assume cross-compilation works without testing on actual hardware.

### 2. Use manylinux for Linux
```bash
docker run --rm -v $(pwd):/io ghcr.io/pyo3/maturin build --manylinux 2014
```

### 3. Build Universal Wheels for macOS
```bash
maturin build --target universal2-apple-darwin
```

### 4. Document Platform Requirements
```markdown
## Platform Support

- Linux: x86_64, aarch64 (glibc 2.17+)
- macOS: Intel and Apple Silicon (10.12+)
- Windows: x86_64 (Windows 7+)
```

### 5. Provide Fallbacks
```rust
#[cfg(target_arch = "x86_64")]
fn fast_function() { /* optimized */ }

#[cfg(not(target_arch = "x86_64"))]
fn fast_function() { /* portable fallback */ }
```

## Verification

After building, verify wheels:

```bash
# List built wheels
ls target/wheels/

# Check wheel contents
unzip -l target/wheels/cross_compile-*.whl

# Verify platform tag
python -c "
import pkginfo
w = pkginfo.Wheel('target/wheels/cross_compile-0.1.0-cp311-cp311-manylinux_2_17_x86_64.whl')
print(f'Platform: {w.supported_platforms}')
"
```

## Next Steps

See `08_ci_cd_pipeline` for:
- Complete GitHub Actions workflow
- Automated multi-platform builds
- Testing across platforms
- Artifact management
