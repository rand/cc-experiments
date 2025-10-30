# Example 08: CI/CD Pipeline

Complete GitHub Actions workflow demonstrating automated building, testing, and publishing of PyO3 packages.

## What This Demonstrates

- Automated CI with GitHub Actions
- Multi-platform wheel building
- Rust and Python testing
- Automated PyPI publishing
- Release automation
- Artifact management

## Project Structure

```
08_ci_cd_pipeline/
├── .github/
│   └── workflows/
│       ├── ci.yml          # Continuous integration
│       └── release.yml     # Release automation
├── src/
│   └── lib.rs              # Rust source
├── Cargo.toml
├── pyproject.toml
└── README.md               # This file
```

## CI/CD Workflows

### 1. CI Workflow (ci.yml)

Triggered on: Push to main, Pull requests

Jobs:
1. **Lint** - Format and clippy checks
2. **Test Rust** - Run Rust tests on all platforms
3. **Test Python** - Test Python package on all platforms/versions
4. **Build Wheels** - Build wheels for Linux, macOS, Windows
5. **Build sdist** - Build source distribution
6. **Verify Wheels** - Install and test built wheels

### 2. Release Workflow (release.yml)

Triggered on: Git tags (v*)

Jobs:
1. **Build Wheels** - Build release wheels with metadata
2. **Build sdist** - Build source distribution
3. **Create Release** - Create GitHub release with artifacts
4. **Publish PyPI** - Upload to PyPI
5. **Publish TestPyPI** - Upload to TestPyPI (optional)

## Setup Instructions

### 1. GitHub Repository Setup

```bash
# Create repository
gh repo create mypackage --public

# Add repository
git remote add origin https://github.com/username/mypackage.git
git push -u origin main
```

### 2. PyPI Setup

#### Get API Token
1. Go to https://pypi.org/manage/account/token/
2. Create new API token
3. Scope: "Entire account" or specific project

#### Add to GitHub Secrets
```bash
# Add PyPI token to repository secrets
gh secret set PYPI_API_TOKEN

# Optional: Add TestPyPI token
gh secret set TEST_PYPI_API_TOKEN
```

### 3. Configure GitHub Environments (Optional)

For better security, create a `pypi` environment:

1. Go to repository Settings → Environments
2. Create `pypi` environment
3. Add `PYPI_API_TOKEN` as environment secret
4. Enable "Required reviewers" for production releases

## Using the CI/CD Pipeline

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "Add new feature"

# Push - triggers CI
git push origin feature/new-feature

# Create PR - runs full CI suite
gh pr create --title "Add new feature"
```

CI will:
- Run linters (rustfmt, clippy)
- Run Rust tests on Linux, macOS, Windows
- Run Python tests on all versions
- Build wheels
- Verify wheels install correctly

### Release Workflow

```bash
# Update version in Cargo.toml and pyproject.toml
sed -i 's/version = "0.1.0"/version = "0.2.0"/' Cargo.toml pyproject.toml

# Commit version bump
git add Cargo.toml pyproject.toml
git commit -m "Bump version to 0.2.0"

# Create and push tag
git tag v0.2.0
git push origin v0.2.0
```

Release workflow will:
1. Build wheels for all platforms
2. Build source distribution
3. Create GitHub release with artifacts
4. Publish to PyPI
5. Publish to TestPyPI (if configured)

## Workflow Configuration

### Matrix Strategy

Test across multiple platforms and Python versions:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']
```

### Caching

Speed up builds with cargo caching:

```yaml
- name: Cache cargo
  uses: actions/cache@v3
  with:
    path: |
      ~/.cargo/registry
      ~/.cargo/git
      target
    key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}
```

### Maturin Action

Build wheels using PyO3/maturin-action:

```yaml
- name: Build wheels
  uses: PyO3/maturin-action@v1
  with:
    command: build
    args: --release --out dist
    manylinux: auto
```

## Local Testing

### Test CI Steps Locally

```bash
# Lint
cargo fmt --check
cargo clippy -- -D warnings

# Test Rust
cargo test --all-features

# Test Python
pip install maturin pytest
maturin develop
pytest tests/

# Build wheels
maturin build --release

# Verify wheel
pip install target/wheels/*.whl
python -c "import ci_cd_example; print(ci_cd_example.__version__)"
```

### Using act (Local GitHub Actions)

```bash
# Install act
brew install act  # macOS
# or download from https://github.com/nektos/act

# Run CI workflow
act push

# Run specific job
act -j lint

# Run release workflow
act -s PYPI_API_TOKEN=your-token release
```

## Best Practices

### 1. Version Management

Synchronize versions:
```bash
# Use single source of truth (Cargo.toml)
# Let maturin read it automatically
[project]
dynamic = ["version"]
```

### 2. Test Matrix

Test combinations that users will use:
```yaml
matrix:
  os: [ubuntu-latest, macos-latest, windows-latest]
  python-version: ['3.8', '3.12']  # Min and max
include:
  - os: ubuntu-latest
    python-version: '3.11'  # Add specific combinations
```

### 3. Secrets Management

Never commit secrets:
```yaml
env:
  MATURIN_PYPI_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
```

### 4. Release Notes

Auto-generate release notes:
```yaml
- uses: softprops/action-gh-release@v1
  with:
    generate_release_notes: true
```

### 5. Conditional Jobs

Skip TestPyPI for non-release builds:
```yaml
if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
```

## Monitoring

### Check Workflow Status

```bash
# View runs
gh run list

# Watch specific run
gh run watch

# View logs
gh run view --log
```

### Badges

Add status badges to README.md:

```markdown
![CI](https://github.com/username/repo/workflows/CI/badge.svg)
![Release](https://github.com/username/repo/workflows/Release/badge.svg)
```

## Troubleshooting

### Issue 1: Build Fails on Specific Platform

Check platform-specific logs:
```bash
gh run view --log | grep -A 50 "windows-latest"
```

### Issue 2: PyPI Upload Fails

Verify token:
```bash
gh secret list
```

Check PyPI project name availability:
```bash
pip search ci-cd-example
```

### Issue 3: Wheel Verification Fails

Test wheel locally:
```bash
maturin build --release
pip install target/wheels/*.whl
python -c "import ci_cd_example"
```

## Advanced Configuration

### Pre-release Versions

```yaml
# In release.yml
- name: Check if pre-release
  id: prerelease
  run: |
    if [[ "${{ github.ref }}" =~ ^refs/tags/v.*-(alpha|beta|rc) ]]; then
      echo "prerelease=true" >> $GITHUB_OUTPUT
    fi

- uses: softprops/action-gh-release@v1
  with:
    prerelease: ${{ steps.prerelease.outputs.prerelease }}
```

### Build Artifacts

```yaml
- uses: actions/upload-artifact@v3
  with:
    name: wheels-${{ matrix.os }}-${{ github.sha }}
    path: dist
    retention-days: 7
```

### Notification

Send notifications on failure:
```yaml
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## Next Steps

See `09_multi_platform` for:
- Advanced platform-specific builds
- Universal wheels
- Platform-specific optimizations
- Testing across architectures
