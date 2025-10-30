# Example 09: Multi-Platform Wheels

Multi-platform wheel building demonstrating how to build and distribute wheels for all major platforms and architectures.

## What This Demonstrates

- Building for Linux (x86_64, aarch64, i686) using manylinux
- Building for Linux using musllinux (Alpine)
- Building for macOS (Intel and Apple Silicon)
- Building macOS universal2 wheels (fat binaries)
- Building for Windows (x64, x86)
- Automated multi-platform CI/CD
- Platform compatibility testing

## Project Structure

```
09_multi_platform/
├── .github/
│   └── workflows/
│       └── wheels.yml      # Multi-platform build workflow
├── src/
│   └── lib.rs              # Platform-aware code
├── Cargo.toml
├── pyproject.toml
└── README.md               # This file
```

## Supported Platforms

### Linux
- **x86_64** (64-bit Intel/AMD) - manylinux_2_17
- **aarch64** (64-bit ARM) - manylinux_2_17
- **i686** (32-bit Intel/AMD) - manylinux_2_17
- **x86_64 musllinux** (Alpine Linux)
- **aarch64 musllinux** (Alpine ARM)

### macOS
- **x86_64** (Intel Macs) - macOS 10.12+
- **aarch64** (Apple Silicon) - macOS 11.0+
- **universal2** (Both architectures in one wheel)

### Windows
- **x64** (64-bit) - Windows 7+
- **x86** (32-bit) - Windows 7+

## Building Locally

### Build for Current Platform
```bash
maturin build --release
```

### Build for Specific Platform

#### Linux (using Docker)
```bash
# x86_64 manylinux
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin \
  build --release --manylinux 2014

# aarch64 manylinux (cross-compile)
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin \
  build --release --target aarch64-unknown-linux-gnu --manylinux 2014

# musllinux
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin \
  build --release --manylinux musllinux_1_2
```

#### macOS
```bash
# Intel
maturin build --release --target x86_64-apple-darwin

# Apple Silicon
maturin build --release --target aarch64-apple-darwin

# Universal2 (both in one wheel)
maturin build --release --target universal2-apple-darwin
```

#### Windows
```bash
# 64-bit
maturin build --release --target x86_64-pc-windows-msvc

# 32-bit
maturin build --release --target i686-pc-windows-msvc
```

## CI/CD Workflow

The GitHub Actions workflow builds wheels for all platforms:

```yaml
# .github/workflows/wheels.yml
jobs:
  linux:        # Linux x86_64, aarch64, i686
  linux-musl:   # musllinux x86_64, aarch64
  macos:        # macOS x86_64, aarch64
  macos-universal:  # macOS universal2
  windows:      # Windows x64, x86
  sdist:        # Source distribution
  test:         # Test all wheels
```

### Trigger Build

```bash
# Push to main branch
git push origin main

# Create release tag
git tag v0.1.0
git push origin v0.1.0

# Manual trigger
gh workflow run wheels.yml
```

### View Build Results

```bash
# List workflow runs
gh run list --workflow=wheels.yml

# Watch current run
gh run watch

# Download artifacts
gh run download
```

## Wheel Compatibility

### manylinux Tags

Format: `manylinux_{glibc_major}_{glibc_minor}_{arch}`

Common tags:
- `manylinux_2_17` - CentOS 7 / RHEL 7 compatible (glibc 2.17)
- `manylinux_2_28` - Debian 10+ / Ubuntu 20.04+ (glibc 2.28)
- `manylinux_2_31` - Debian 11+ / Ubuntu 22.04+ (glibc 2.31)

### musllinux Tags

For Alpine Linux and other musl-based distributions:
- `musllinux_1_1` - musl 1.1+
- `musllinux_1_2` - musl 1.2+

### macOS Version Tags

Format: `macosx_{major}_{minor}_{arch}`

- `macosx_10_12_x86_64` - macOS 10.12+ Intel
- `macosx_11_0_arm64` - macOS 11.0+ Apple Silicon
- `macosx_11_0_universal2` - macOS 11.0+ Universal

### Windows Tags

- `win_amd64` - Windows 64-bit
- `win32` - Windows 32-bit

## Testing

### Test Specific Platform Wheel

```bash
# Download artifact
gh run download <run-id> -n wheels

# Install specific wheel
pip install multi_platform-0.1.0-cp311-cp311-manylinux_2_17_x86_64.whl

# Test
python -c "import multi_platform; print(multi_platform.get_platform_info())"
```

### Python Usage

```python
import multi_platform

# Get platform information
info = multi_platform.get_platform_info()
print(f"OS: {info['os']}")
print(f"Architecture: {info['arch']}")
print(f"Target: {info['target']}")
print(f"Platform: {info['platform']}")

# Check SIMD features
features = multi_platform.simd_features()
print(f"SIMD features: {features}")

# Get wheel tag
tag = multi_platform.wheel_tag()
print(f"Wheel tag: {tag}")

# Use platform-optimized function
result = multi_platform.platform_sum([1, 2, 3, 4, 5])
print(f"Sum: {result}")
```

## Platform-Specific Considerations

### Linux

#### manylinux Compatibility
- Use oldest supported glibc version
- `manylinux_2_17` works on most distributions (2014+)
- Test on CentOS/RHEL, Ubuntu, Debian

#### musllinux for Alpine
- Required for Alpine Linux containers
- Separate build from glibc-based systems

### macOS

#### Universal2 Benefits
- Single wheel for Intel and Apple Silicon
- Reduces download size vs separate wheels
- Recommended for most users

#### Deployment Target
- Minimum macOS version supported
- Set via `MACOSX_DEPLOYMENT_TARGET` env var
- Default: 10.12 for x86_64, 11.0 for arm64

### Windows

#### MSVC vs GNU
- MSVC recommended (better compatibility)
- GNU possible but requires MinGW runtime

#### 32-bit Support
- Still used in some environments
- Consider dropping for modern packages

## Verification

### Check Built Wheels

```bash
# List all wheels
ls dist/*.whl

# Expected output:
# multi_platform-0.1.0-cp38-cp38-manylinux_2_17_x86_64.whl
# multi_platform-0.1.0-cp38-cp38-manylinux_2_17_aarch64.whl
# multi_platform-0.1.0-cp38-cp38-musllinux_1_2_x86_64.whl
# multi_platform-0.1.0-cp38-cp38-macosx_10_12_x86_64.whl
# multi_platform-0.1.0-cp38-cp38-macosx_11_0_arm64.whl
# multi_platform-0.1.0-cp38-cp38-win_amd64.whl
# ... (for each Python version)
```

### Verify Wheel Contents

```bash
# Check wheel metadata
unzip -p dist/multi_platform-*.whl */WHEEL

# Check shared library
unzip -l dist/multi_platform-*.whl | grep '\.so\|\.dylib\|\.pyd'
```

### Test Installation

```bash
# Create clean environment
python -m venv test_env
source test_env/bin/activate

# Install from wheel
pip install dist/multi_platform-*-cp311-*-$(python -c "import sysconfig; print(sysconfig.get_platform().replace('-', '_').replace('.', '_'))").whl

# Test
python -c "import multi_platform; print(multi_platform.__version__)"
```

## Distribution

### Upload to PyPI

All platform wheels in one release:

```bash
# Upload all wheels
twine upload dist/*

# Users install appropriate wheel automatically
pip install multi_platform
```

PyPI automatically selects correct wheel based on:
- Python version
- Operating system
- Architecture
- ABI compatibility

## Best Practices

### 1. Build for Common Platforms First
```
Priority:
1. Linux x86_64 (most users)
2. macOS universal2 (Intel + ARM)
3. Windows x64
4. Linux aarch64 (growing)
5. Others as needed
```

### 2. Use manylinux_2_17 for Broad Compatibility
```bash
maturin build --manylinux 2014  # CentOS 7 compatible
```

### 3. Provide musllinux for Alpine
```bash
maturin build --manylinux musllinux_1_2
```

### 4. Test on Target Platforms
Don't just build - test on actual systems!

### 5. Document Platform Support
```markdown
## Platform Support

| Platform | Architectures | Notes |
|----------|--------------|-------|
| Linux | x86_64, aarch64 | glibc 2.17+ |
| Alpine | x86_64, aarch64 | musl 1.2+ |
| macOS | Intel, Apple Silicon | 10.12+ / 11.0+ |
| Windows | x64, x86 | Windows 7+ |
```

## Troubleshooting

### Issue 1: Wheel Too Large

**Solution**: Reduce binary size
```bash
# Strip symbols
maturin build --release --strip

# Enable LTO in Cargo.toml
[profile.release]
lto = true
codegen-units = 1
```

### Issue 2: Import Error on Specific Platform

Check platform compatibility:
```python
import multi_platform
print(multi_platform.get_platform_info())
```

### Issue 3: Missing Architecture

Add to CI matrix:
```yaml
matrix:
  target: [x86_64, aarch64, i686, armv7]
```

## Next Steps

See `10_production_release` for:
- Complete production release workflow
- Documentation generation
- Changelog automation
- PyPI publishing best practices
