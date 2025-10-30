# Example 10: Production Release

Complete production release workflow demonstrating version management, changelog, documentation, automated testing, and PyPI publishing.

## What This Demonstrates

- Production-ready package structure
- Semantic versioning
- Changelog management (Keep a Changelog format)
- Automated release workflow
- Version validation
- Multi-platform testing
- PyPI publishing
- Documentation generation
- GitHub releases

## Project Structure

```
10_production_release/
├── .github/
│   └── workflows/
│       └── release.yml     # Production release workflow
├── docs/
│   ├── conf.py            # Sphinx configuration
│   └── index.rst          # Documentation
├── src/
│   └── lib.rs             # Production code
├── CHANGELOG.md           # Version history
├── Cargo.toml             # Production config
├── pyproject.toml         # Production metadata
└── README.md              # This file
```

## Release Workflow

### 1. Prepare Release

#### Update Version

```bash
# Update version in both files
VERSION="1.0.0"

# Cargo.toml
sed -i '' "s/^version = .*/version = \"$VERSION\"/" Cargo.toml

# pyproject.toml
sed -i '' "s/^version = .*/version = \"$VERSION\"/" pyproject.toml
```

#### Update CHANGELOG.md

```markdown
## [1.0.0] - 2024-10-30

### Added
- New feature X
- New feature Y

### Changed
- Improved performance of Z

### Fixed
- Fixed bug in W
```

#### Commit Changes

```bash
git add Cargo.toml pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to $VERSION"
git push origin main
```

### 2. Create Release Tag

```bash
# Create annotated tag
git tag -a v1.0.0 -m "Release version 1.0.0"

# Push tag - triggers release workflow
git push origin v1.0.0
```

### 3. Automated Release Process

The release workflow automatically:

1. **Validates** version consistency
2. **Checks** CHANGELOG.md has entry for version
3. **Builds** wheels for all platforms
4. **Builds** source distribution
5. **Tests** all wheels
6. **Creates** GitHub release with changelog excerpt
7. **Publishes** to PyPI
8. **Generates** and deploys documentation

## Semantic Versioning

Format: `MAJOR.MINOR.PATCH`

### Version Numbers

- **MAJOR** (1.x.x) - Breaking changes
  - Remove function
  - Change function signature
  - Incompatible API changes

- **MINOR** (x.1.x) - New features (backward compatible)
  - Add new function
  - Add optional parameter
  - New functionality

- **PATCH** (x.x.1) - Bug fixes (backward compatible)
  - Fix bug
  - Performance improvement
  - Documentation update

### Examples

```
0.1.0 → 0.1.1  # Bug fix
0.1.1 → 0.2.0  # New feature
0.2.0 → 1.0.0  # First stable release
1.0.0 → 1.1.0  # New feature (compatible)
1.1.0 → 2.0.0  # Breaking change
```

### Pre-release Versions

```
1.0.0-alpha.1  # Alpha release
1.0.0-beta.1   # Beta release
1.0.0-rc.1     # Release candidate
1.0.0          # Stable release
```

## Changelog Management

Following [Keep a Changelog](https://keepachangelog.com/) format:

### Structure

```markdown
# Changelog

## [Unreleased]
### Added
- Features in development

## [1.0.0] - 2024-10-30
### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes

[Unreleased]: https://github.com/user/repo/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/user/repo/releases/tag/v1.0.0
```

### Best Practices

1. **Update with each change** - Add to Unreleased section
2. **Move to version on release** - Create dated version section
3. **Group changes** - Use categories (Added, Changed, Fixed, etc.)
4. **Link to diffs** - Include comparison links at bottom
5. **Use present tense** - "Add feature" not "Added feature"

## Release Validation

The workflow validates:

### Version Consistency
```bash
# Checks that tag matches Cargo.toml version
TAG_VERSION=${GITHUB_REF#refs/tags/v}
CARGO_VERSION=$(grep '^version' Cargo.toml | head -1 | cut -d '"' -f2)

if [ "$TAG_VERSION" != "$CARGO_VERSION" ]; then
  echo "Version mismatch!"
  exit 1
fi
```

### Changelog Entry
```bash
# Checks that CHANGELOG.md has entry for version
if ! grep -q "v1.0.0" CHANGELOG.md; then
  echo "Missing CHANGELOG entry!"
  exit 1
fi
```

## Testing

### Local Testing Before Release

```bash
# Run tests
cargo test

# Build release wheel
maturin build --release

# Test wheel installation
pip install target/wheels/*.whl

# Verify version
python -c "import production_release; print(production_release.__version__)"

# Run smoke tests
python -c "import production_release; assert production_release.factorial(5) == 120"
```

### CI Testing

The workflow tests on:
- Linux, macOS, Windows
- Python 3.8, 3.12
- All built wheels

## PyPI Publishing

### Setup

1. **Get API Token**
   - Go to https://pypi.org/manage/account/token/
   - Create token for project

2. **Add to GitHub Secrets**
   ```bash
   gh secret set PYPI_API_TOKEN
   ```

3. **Configure Environment** (recommended)
   - Create `pypi` environment in GitHub
   - Add protection rules
   - Require approval for releases

### Publishing

Automatic on tag push:
```bash
git tag v1.0.0
git push origin v1.0.0
```

Manual publishing:
```bash
# Build wheels
maturin build --release

# Upload to PyPI
maturin upload dist/*
```

## Documentation

### Structure

```
docs/
├── conf.py          # Sphinx configuration
├── index.rst        # Main page
├── api.rst          # API reference
├── quickstart.rst   # Quick start guide
└── changelog.rst    # Changelog (linked)
```

### Building Docs

```bash
# Install dependencies
pip install sphinx sphinx-rtd-theme

# Build HTML
cd docs
make html

# View locally
open _build/html/index.html
```

### Deployment

Automated via GitHub Actions:
- Builds on each release
- Deploys to GitHub Pages
- Available at: https://username.github.io/production_release/

## GitHub Releases

### Automated Release Notes

The workflow automatically:
1. Extracts relevant section from CHANGELOG.md
2. Creates GitHub release
3. Attaches wheel files
4. Marks as latest release

### Manual Release Notes

Add custom notes:
```yaml
- name: Create Release
  uses: softprops/action-gh-release@v1
  with:
    body_path: RELEASE_NOTES.md
    files: dist/*
```

## Monitoring

### Check Release Status

```bash
# View workflow runs
gh run list --workflow=release.yml

# Watch current release
gh run watch

# View release
gh release view v1.0.0
```

### Verify PyPI Upload

```bash
# Check on PyPI
pip search production_release

# Install from PyPI
pip install production_release==1.0.0

# Verify
python -c "import production_release; print(production_release.__version__)"
```

## Rollback

If release has issues:

### Delete Release
```bash
# Delete GitHub release
gh release delete v1.0.0

# Delete tag
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
```

### Yank from PyPI
```bash
# Cannot delete from PyPI, but can yank
# Use PyPI web interface to mark as "yanked"
# Users can still install with ==version, but not by default
```

### Create Patch Release
```bash
# Fix issue
# Bump to v1.0.1
# Follow release process
```

## Best Practices

### 1. Test Before Release
```bash
# Complete test suite
cargo test
maturin develop
pytest tests/

# Manual testing
python examples/test_all.py
```

### 2. Automate Everything
- Version validation
- Changelog checks
- Wheel building
- Testing
- Publishing

### 3. Use Environments
```yaml
environment:
  name: pypi
  url: https://pypi.org/p/production-release
```

### 4. Require Approval
- Enable branch protection
- Require PR reviews
- Use GitHub environments for production

### 5. Keep CHANGELOG Current
- Update with each PR
- Use Unreleased section
- Move to version on release

### 6. Document Breaking Changes
```markdown
## [2.0.0] - 2024-11-01

### Changed
- **BREAKING**: `factorial()` now returns `u64` instead of `i64`
- **BREAKING**: Removed deprecated `old_function()`

### Migration Guide
...
```

## Troubleshooting

### Issue 1: Version Mismatch
```
Error: Version mismatch: tag=1.0.0, Cargo.toml=0.9.0
```

**Solution**: Update both Cargo.toml and pyproject.toml

### Issue 2: Missing CHANGELOG Entry
```
Error: CHANGELOG.md missing entry for v1.0.0
```

**Solution**: Add version section to CHANGELOG.md

### Issue 3: PyPI Upload Fails
```
Error: File already exists
```

**Solution**: Cannot re-upload same version. Bump to next patch version.

### Issue 4: Wheel Test Fails
```
Error: ModuleNotFoundError: No module named 'production_release'
```

**Solution**: Check wheel was built correctly, verify platform compatibility

## Complete Release Checklist

Before creating release tag:

- [ ] All tests passing
- [ ] Version updated in Cargo.toml
- [ ] Version updated in pyproject.toml
- [ ] CHANGELOG.md updated with version and date
- [ ] Documentation updated
- [ ] README.md reflects current state
- [ ] No uncommitted changes
- [ ] PR merged to main
- [ ] Local testing complete

After pushing tag:

- [ ] CI workflow completes successfully
- [ ] GitHub release created
- [ ] PyPI package available
- [ ] Documentation deployed
- [ ] Smoke test from PyPI
- [ ] Announce release

## Resources

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [PyPI Packaging Guide](https://packaging.python.org/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Maturin Documentation](https://www.maturin.rs/)
