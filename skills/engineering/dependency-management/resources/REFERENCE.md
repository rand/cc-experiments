# Dependency Management Reference Guide

> Comprehensive reference for managing dependencies across all major ecosystems

## Table of Contents

1. [Introduction](#introduction)
2. [Dependency Management Fundamentals](#dependency-management-fundamentals)
3. [Semantic Versioning Deep Dive](#semantic-versioning-deep-dive)
4. [Package Managers](#package-managers)
5. [Lock Files](#lock-files)
6. [Version Resolution](#version-resolution)
7. [Dependency Pinning Strategies](#dependency-pinning-strategies)
8. [Security Scanning](#security-scanning)
9. [Automated Updates](#automated-updates)
10. [License Compliance](#license-compliance)
11. [Dependency Graphs](#dependency-graphs)
12. [Monorepo Dependency Management](#monorepo-dependency-management)
13. [Private Package Registries](#private-package-registries)
14. [Vendoring and Bundling](#vendoring-and-bundling)
15. [Build Reproducibility](#build-reproducibility)
16. [Supply Chain Security](#supply-chain-security)
17. [Deprecation Handling](#deprecation-handling)
18. [Breaking Change Management](#breaking-change-management)
19. [Anti-Patterns](#anti-patterns)
20. [Troubleshooting Guide](#troubleshooting-guide)

---

## Introduction

### What is Dependency Management?

Dependency management is the systematic approach to:
1. **Declaring** what external code your project needs
2. **Resolving** compatible versions of all dependencies
3. **Installing** those dependencies in a reproducible way
4. **Updating** dependencies when needed (security, features, bugs)
5. **Securing** your supply chain against vulnerabilities
6. **Complying** with license requirements

### Why It Matters

**Without proper dependency management**:
- Builds break in different environments
- Security vulnerabilities go unpatched
- Version conflicts cause runtime errors
- License violations create legal risk
- Supply chain attacks compromise systems
- Development velocity decreases

**With proper dependency management**:
- Reproducible builds across all environments
- Fast incident response to security issues
- Predictable upgrade paths
- Legal compliance
- Reduced supply chain risk
- Sustainable development velocity

### Dependency Management Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Dependency Lifecycle                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Selection       → Evaluate need, choose package         │
│  2. Declaration     → Add to manifest (package.json, etc)   │
│  3. Resolution      → Determine compatible version graph    │
│  4. Installation    → Download and cache dependencies       │
│  5. Locking         → Record exact versions in lock file    │
│  6. Verification    → Audit security, licenses, integrity   │
│  7. Monitoring      → Watch for updates, vulnerabilities    │
│  8. Updating        → Apply patches, upgrades               │
│  9. Testing         → Validate compatibility                │
│  10. Deprecation    → Remove unused dependencies            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Dependency Management Fundamentals

### Direct vs Transitive Dependencies

**Direct Dependencies**: Explicitly declared in your manifest file
```json
// package.json
{
  "dependencies": {
    "express": "^4.18.0",     // Direct dependency
    "lodash": "^4.17.21"      // Direct dependency
  }
}
```

**Transitive Dependencies**: Dependencies of your dependencies
```
Your Project
├── express@4.18.0 (direct)
│   ├── body-parser@1.20.0 (transitive)
│   ├── cookie@0.5.0 (transitive)
│   └── debug@2.6.9 (transitive)
│       └── ms@2.0.0 (transitive)
└── lodash@4.17.21 (direct)
```

### Production vs Development Dependencies

**Production Dependencies**: Required at runtime
```json
{
  "dependencies": {
    "express": "^4.18.0",
    "pg": "^8.11.0"
  }
}
```

**Development Dependencies**: Only needed during development
```json
{
  "devDependencies": {
    "typescript": "^5.0.0",
    "jest": "^29.0.0",
    "eslint": "^8.0.0"
  }
}
```

### Peer Dependencies

Dependencies that must be provided by the consuming project:
```json
{
  "peerDependencies": {
    "react": "^18.0.0"
  }
}
```

**Use case**: Plugin/extension systems where the host provides the core library.

### Optional Dependencies

Dependencies that enhance functionality but aren't required:
```json
{
  "optionalDependencies": {
    "fsevents": "^2.3.0"  // macOS-specific file watching
  }
}
```

---

## Semantic Versioning Deep Dive

### SemVer Specification

```
MAJOR.MINOR.PATCH-PRERELEASE+BUILD

Examples:
  1.0.0           - Initial release
  1.2.3           - Standard version
  2.0.0-alpha.1   - Pre-release
  1.4.7+20231015  - Build metadata
```

### Version Component Semantics

**MAJOR (Breaking Changes)**:
- Incompatible API changes
- Removed functionality
- Changed behavior that breaks existing usage
```
1.x.x → 2.0.0: Breaking change
```

**MINOR (New Features)**:
- New functionality, backward compatible
- New API endpoints
- Performance improvements
```
2.3.x → 2.4.0: New feature added
```

**PATCH (Bug Fixes)**:
- Bug fixes, backward compatible
- Security patches
- Documentation updates
```
2.4.7 → 2.4.8: Bug fixed
```

### Pre-release Versions

```
1.0.0-alpha.1    - Alpha (internal testing)
1.0.0-beta.1     - Beta (external testing)
1.0.0-rc.1       - Release candidate (final testing)
1.0.0            - Stable release
```

**Pre-release order**: `alpha < beta < rc < release`

### Version Range Operators

#### Caret (^) - Compatible Releases

```bash
^1.2.3   ≡ >=1.2.3 <2.0.0   # Allow minor and patch updates
^0.2.3   ≡ >=0.2.3 <0.3.0   # For 0.x, only allow patch updates
^0.0.3   ≡ >=0.0.3 <0.0.4   # For 0.0.x, no updates
```

**Philosophy**: "Give me bug fixes and new features, but no breaking changes"

#### Tilde (~) - Patch Releases

```bash
~1.2.3   ≡ >=1.2.3 <1.3.0   # Allow patch updates only
~1.2     ≡ >=1.2.0 <1.3.0   # Same as ~1.2.0
~1       ≡ >=1.0.0 <2.0.0   # Allow minor and patch updates
```

**Philosophy**: "Give me bug fixes only, no new features"

#### Exact Versions

```bash
1.2.3    # Only version 1.2.3 exactly
```

**Use cases**:
- Critical production dependencies
- Known compatibility requirements
- Debugging version-specific issues

#### Comparison Operators

```bash
>1.2.3   # Greater than 1.2.3
>=1.2.3  # Greater than or equal to 1.2.3
<2.0.0   # Less than 2.0.0
<=1.5.0  # Less than or equal to 1.5.0
```

#### Range Combinations

```bash
>=1.2.3 <2.0.0        # Between 1.2.3 and 2.0.0
>=1.2.3 <1.3.0        # Patch updates only
1.2.3 - 1.5.7         # Inclusive range
1.2.x                 # Any 1.2.* version
*                     # Any version (dangerous!)
```

#### Wildcards

```bash
1.2.x    ≡ >=1.2.0 <1.3.0    # Any patch version
1.x      ≡ >=1.0.0 <2.0.0    # Any minor/patch version
*        ≡ >=0.0.0            # Any version (avoid!)
```

### Version Selection Strategy

```
┌──────────────────────────────────────────────────────────┐
│  Dependency Type        │  Recommended Range             │
├─────────────────────────┼────────────────────────────────┤
│  Production app         │  ^1.2.3 (caret)                │
│  Library/package        │  >=1.2.3 <2.0.0 (explicit)     │
│  Build tools            │  ^1.2.3 (caret)                │
│  Testing tools          │  ^1.2.3 (caret)                │
│  Known issues           │  1.2.3 (exact)                 │
│  Internal packages      │  workspace:* (monorepo)        │
└──────────────────────────────────────────────────────────┘
```

---

## Package Managers

### npm (Node Package Manager)

**Commands**:
```bash
# Installation
npm install                    # Install all dependencies
npm install package           # Add to dependencies
npm install -D package        # Add to devDependencies
npm install -g package        # Global install
npm ci                        # Clean install from lock file

# Updates
npm update                    # Update all dependencies
npm update package           # Update specific package
npm outdated                 # List outdated packages

# Information
npm list                     # Dependency tree
npm list --depth=0          # Direct dependencies only
npm info package            # Package information
npm view package versions   # Available versions

# Auditing
npm audit                   # Security audit
npm audit fix              # Fix vulnerabilities
npm audit fix --force      # Apply breaking changes

# Cleanup
npm prune                  # Remove extraneous packages
npm cache clean --force    # Clear cache
```

**Configuration** (`.npmrc`):
```ini
# Private registry
registry=https://registry.example.com/

# Scoped registry
@myorg:registry=https://npm.example.com/

# Authentication
//registry.example.com/:_authToken=${NPM_TOKEN}

# Settings
save-exact=true              # Save exact versions
package-lock=true            # Create lock file
audit-level=moderate         # Audit threshold
```

### Yarn

**Commands**:
```bash
# Installation
yarn install               # Install all dependencies
yarn add package          # Add to dependencies
yarn add -D package       # Add to devDependencies
yarn global add package   # Global install

# Updates
yarn upgrade              # Interactive upgrade
yarn upgrade-interactive  # Choose versions
yarn upgrade package     # Update specific package

# Information
yarn list                # Dependency tree
yarn info package       # Package information
yarn why package        # Why is package installed?

# Auditing
yarn audit              # Security audit
yarn audit --level moderate

# Cleanup
yarn autoclean          # Remove unnecessary files
yarn cache clean        # Clear cache
```

**Yarn 2+ (Berry)** features:
- Plug'n'Play (PnP) - no node_modules
- Zero-installs - commit dependencies
- Constraints engine - enforce policies

### pnpm

**Advantages**:
- Disk space efficient (content-addressable store)
- Fast (parallel operations)
- Strict dependency resolution

**Commands**:
```bash
# Installation
pnpm install              # Install all dependencies
pnpm add package         # Add to dependencies
pnpm add -D package      # Add to devDependencies

# Updates
pnpm update              # Update all dependencies
pnpm update package     # Update specific package
pnpm outdated           # List outdated packages

# Information
pnpm list               # Dependency tree
pnpm why package       # Dependency explanation

# Auditing
pnpm audit             # Security audit
```

### pip (Python)

**Commands**:
```bash
# Installation
pip install package              # Install package
pip install package==1.2.3      # Install specific version
pip install -r requirements.txt # Install from file
pip install -e .                # Editable install

# Information
pip list                        # Installed packages
pip show package               # Package details
pip freeze                     # Generate requirements

# Uninstall
pip uninstall package          # Remove package
```

**Requirements files**:
```txt
# requirements.txt
flask==2.3.0
requests>=2.28.0,<3.0.0
pytest~=7.4.0

# With hashes for security
flask==2.3.0 \
    --hash=sha256:abc123...
```

### uv (Modern Python)

**Advantages**:
- 10-100x faster than pip
- Built in Rust
- Drop-in pip replacement

**Commands**:
```bash
# Installation
uv pip install package         # Install package
uv pip install -r requirements.txt

# Project management
uv init                       # Initialize project
uv add package               # Add dependency
uv sync                      # Install from lock
uv lock                      # Update lock file
uv tree                      # Dependency tree

# Virtual environments
uv venv                      # Create venv
uv run script.py            # Run in venv
```

### pip-tools

**Commands**:
```bash
# Generate locked requirements
pip-compile requirements.in -o requirements.txt

# Upgrade packages
pip-compile --upgrade requirements.in

# Install from compiled file
pip-sync requirements.txt
```

### Poetry (Python)

**Commands**:
```bash
# Project setup
poetry new project          # Create new project
poetry init                 # Initialize existing project

# Dependency management
poetry add package         # Add dependency
poetry add -D package      # Add dev dependency
poetry update              # Update all dependencies
poetry update package     # Update specific package

# Installation
poetry install             # Install all dependencies
poetry install --no-dev   # Production only

# Information
poetry show               # List packages
poetry show --tree       # Dependency tree
poetry show --outdated   # Check for updates
```

### Cargo (Rust)

**Commands**:
```bash
# Installation
cargo build               # Build and install dependencies
cargo add package        # Add dependency
cargo add --dev package  # Add dev dependency

# Updates
cargo update             # Update all dependencies
cargo update package    # Update specific package

# Information
cargo tree              # Dependency tree
cargo tree --duplicates # Find duplicate dependencies

# Auditing
cargo audit            # Security audit
cargo outdated        # Check for updates
```

### Go Modules

**Commands**:
```bash
# Installation
go get package@version     # Get specific version
go get -u package         # Update package

# Maintenance
go mod tidy              # Clean up go.mod
go mod download          # Download modules
go mod verify            # Verify dependencies

# Information
go list -m all          # List all modules
go mod graph            # Dependency graph
go mod why package     # Why is package needed?

# Vendoring
go mod vendor           # Copy dependencies to vendor/
```

### Maven (Java)

**Commands**:
```bash
# Installation
mvn install             # Install dependencies

# Updates
mvn versions:display-dependency-updates
mvn versions:use-latest-versions

# Dependency tree
mvn dependency:tree

# Analysis
mvn dependency:analyze
```

**pom.xml**:
```xml
<dependencies>
  <dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <version>3.1.0</version>
  </dependency>
</dependencies>
```

### Gradle (Java/Kotlin)

**build.gradle.kts**:
```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web:3.1.0")
    testImplementation("org.junit.jupiter:junit-jupiter:5.9.0")
}
```

**Commands**:
```bash
./gradlew dependencies      # Show dependency tree
./gradlew dependencyUpdates # Check for updates
```

---

## Lock Files

### Purpose of Lock Files

Lock files record **exact versions** of all dependencies (direct and transitive) to ensure:
1. **Reproducibility**: Same versions across all environments
2. **Consistency**: Same build on dev, CI, production
3. **Security**: Prevent unexpected version changes
4. **Debugging**: Know exactly what's installed

### Lock File Types

#### package-lock.json (npm)

```json
{
  "name": "my-app",
  "version": "1.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {
      "name": "my-app",
      "version": "1.0.0",
      "dependencies": {
        "express": "^4.18.0"
      }
    },
    "node_modules/express": {
      "version": "4.18.2",
      "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
      "integrity": "sha512-...",
      "dependencies": {
        "body-parser": "1.20.1"
      }
    }
  }
}
```

**Features**:
- Integrity hashes (SHA-512)
- Resolved URLs
- Full dependency graph

#### yarn.lock (Yarn)

```yaml
express@^4.18.0:
  version "4.18.2"
  resolved "https://registry.yarnpkg.com/express/-/express-4.18.2.tgz#..."
  integrity sha512-...
  dependencies:
    body-parser "1.20.1"
    cookie "0.5.0"
```

#### pnpm-lock.yaml (pnpm)

```yaml
lockfileVersion: 5.4
specifiers:
  express: ^4.18.0
dependencies:
  express: 4.18.2
packages:
  /express/4.18.2:
    resolution: {integrity: sha512-...}
    dependencies:
      body-parser: 1.20.1
```

#### Pipfile.lock (Python/pipenv)

```json
{
    "_meta": {
        "hash": {
            "sha256": "..."
        },
        "pipfile-spec": 6
    },
    "default": {
        "flask": {
            "version": "==2.3.0",
            "hashes": [
                "sha256:..."
            ]
        }
    }
}
```

#### Cargo.lock (Rust)

```toml
[[package]]
name = "tokio"
version = "1.28.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "..."
dependencies = [
 "bytes",
 "mio",
]
```

#### go.sum (Go)

```
github.com/gin-gonic/gin v1.9.0 h1:OjyFBKICoexlu99ctXNR2gg+c5pKrKMuyjgARg9qeY8=
github.com/gin-gonic/gin v1.9.0/go.mod h1:W1Me9+hsUSyj3CePGrd1/QrKJMSJ1Tu/0hFEH89961k=
```

### Lock File Best Practices

```bash
# ✅ DO: Commit lock files
git add package-lock.json yarn.lock pnpm-lock.yaml
git add Pipfile.lock Cargo.lock go.sum

# ✅ DO: Use lock files in CI/CD
npm ci                 # Not npm install
yarn install --frozen-lockfile
pnpm install --frozen-lockfile

# ✅ DO: Regenerate lock files after manifest changes
npm install            # Regenerates package-lock.json
poetry lock           # Regenerates poetry.lock

# ❌ DON'T: Delete lock files to fix issues
rm package-lock.json  # This masks underlying problems

# ❌ DON'T: Manually edit lock files
vim package-lock.json # Let tools manage lock files

# ❌ DON'T: Use different package managers
npm install && yarn add package  # Conflicts!
```

---

## Version Resolution

### Resolution Algorithms

#### npm Algorithm

```
1. Read package.json
2. Read package-lock.json (if exists)
3. For each dependency:
   a. Check if version in lock file satisfies manifest
   b. If yes, use locked version
   c. If no, resolve new version
4. Flatten dependency tree (hoisting)
5. Write package-lock.json
```

**Hoisting**: Move transitive dependencies up to reduce duplication
```
Before hoisting:
node_modules/
├── A/
│   └── node_modules/
│       └── lodash@4.17.21
└── B/
    └── node_modules/
        └── lodash@4.17.21

After hoisting:
node_modules/
├── lodash@4.17.21
├── A/
└── B/
```

#### Yarn Algorithm

Similar to npm but with:
- Deterministic resolution order
- Parallel downloads
- Better error messages

#### pnpm Algorithm

**No hoisting** - strict dependency isolation:
```
node_modules/
├── .pnpm/
│   ├── lodash@4.17.21/
│   └── express@4.18.2/
├── express -> .pnpm/express@4.18.2/node_modules/express
└── package.json
```

**Benefits**:
- Disk space efficient (single copy per version)
- Prevents phantom dependencies
- Faster installation

### Dependency Conflicts

#### Scenario: Conflicting Version Requirements

```
Your Project
├── package-a@1.0.0
│   └── requires: util@^1.0.0
└── package-b@2.0.0
    └── requires: util@^2.0.0
```

**Resolution strategies**:

1. **Multiple versions** (npm/yarn):
```
node_modules/
├── util@2.0.0              # Hoisted version
├── package-a/
│   └── node_modules/
│       └── util@1.0.0      # Nested version
└── package-b/
```

2. **Force single version** (overrides):
```json
{
  "overrides": {
    "util": "2.0.0"
  }
}
```

3. **Peer dependency resolution**:
```json
{
  "peerDependencies": {
    "react": "^18.0.0"
  },
  "peerDependenciesMeta": {
    "react": {
      "optional": false
    }
  }
}
```

### Resolution Debugging

```bash
# npm
npm ls package              # Where does package come from?
npm explain package         # Why is package installed?

# yarn
yarn why package           # Dependency explanation

# pnpm
pnpm why package          # Why is package installed?

# cargo
cargo tree -i package     # Reverse dependencies

# go
go mod why package        # Why is package needed?
go mod graph | grep package
```

---

## Dependency Pinning Strategies

### Exact Pinning

**When to use**:
- Critical production systems
- Known compatibility issues
- Reproducing bugs
- Regulatory compliance

```json
{
  "dependencies": {
    "express": "4.18.2",
    "lodash": "4.17.21"
  }
}
```

**Pros**:
- Maximum predictability
- No surprises

**Cons**:
- Manual updates required
- Miss security patches
- Accumulate technical debt

### Patch Pinning (~)

**When to use**:
- Production applications
- Stable APIs
- Conservative updates

```json
{
  "dependencies": {
    "express": "~4.18.2",   // 4.18.x only
    "lodash": "~4.17.21"    // 4.17.x only
  }
}
```

**Pros**:
- Get bug fixes automatically
- Low risk of breakage

**Cons**:
- Miss new features
- Still need minor updates

### Compatible Pinning (^)

**When to use**:
- Most applications
- Active development
- Balanced approach

```json
{
  "dependencies": {
    "express": "^4.18.2",   // 4.x.x
    "lodash": "^4.17.21"    // 4.x.x
  }
}
```

**Pros**:
- Get features and fixes
- Maintains compatibility
- Industry standard

**Cons**:
- Potential breaking changes in minor versions
- Need good tests

### Range Pinning

**When to use**:
- Library development
- Flexible compatibility
- Wide audience

```json
{
  "dependencies": {
    "express": ">=4.0.0 <5.0.0"
  }
}
```

### Hybrid Strategy (Recommended)

```json
{
  "dependencies": {
    "express": "4.18.2",        // Exact: Known critical dependency
    "lodash": "~4.17.21",       // Patch: Stable utility
    "axios": "^1.4.0",          // Compatible: Active library
    "react": ">=18.0.0 <19.0.0" // Range: Peer dependency
  }
}
```

---

## Security Scanning

### Vulnerability Databases

| Database | Coverage | Access |
|----------|----------|--------|
| **NIST NVD** | CVE database | Free, public |
| **GitHub Advisory** | Multi-language | Free, public |
| **Snyk Vuln DB** | Comprehensive | Free tier available |
| **RustSec** | Rust crates | Free, public |
| **npm Advisory** | npm packages | Free, public |
| **PyPI Advisory** | Python packages | Free, public |

### Security Scanning Tools

#### npm audit

```bash
# Basic audit
npm audit

# Output format
npm audit --json > audit.json

# Fix vulnerabilities
npm audit fix              # Safe fixes only
npm audit fix --force      # Including breaking changes

# Audit levels
npm audit --audit-level=moderate  # Moderate and above
npm audit --audit-level=high      # High and critical only
```

**Example output**:
```
┌───────────────┬──────────────────────────────────────────────────┐
│ High          │ Regular Expression Denial of Service             │
├───────────────┼──────────────────────────────────────────────────┤
│ Package       │ lodash                                            │
├───────────────┼──────────────────────────────────────────────────┤
│ Patched in    │ >=4.17.21                                        │
├───────────────┼──────────────────────────────────────────────────┤
│ Dependency of │ express                                           │
├───────────────┼──────────────────────────────────────────────────┤
│ Path          │ express > body-parser > lodash                   │
├───────────────┼──────────────────────────────────────────────────┤
│ More info     │ https://npmjs.com/advisories/1065               │
└───────────────┴──────────────────────────────────────────────────┘
```

#### pip-audit (Python)

```bash
# Audit installed packages
pip-audit

# Audit requirements file
pip-audit -r requirements.txt

# Output formats
pip-audit --format json
pip-audit --format cyclonedx-json  # SBOM format

# Auto-fix
pip-audit --fix

# Ignore specific vulnerabilities
pip-audit --ignore-vuln PYSEC-2023-123
```

#### cargo audit (Rust)

```bash
# Audit dependencies
cargo audit

# Update advisory database
cargo audit fetch

# Output formats
cargo audit --json

# Ignore advisories
cargo audit --ignore RUSTSEC-2023-0001
```

**Configuration** (`.cargo/audit.toml`):
```toml
[advisories]
ignore = [
    "RUSTSEC-2023-0001",  # Known false positive
]

[output]
format = "json"
```

#### Snyk

```bash
# Install
npm install -g snyk

# Authenticate
snyk auth

# Test for vulnerabilities
snyk test

# Test with details
snyk test --severity-threshold=high

# Monitor project
snyk monitor

# Fix vulnerabilities
snyk fix
```

**Features**:
- License scanning
- Container scanning
- IaC scanning
- Automated PRs

#### Trivy (Container scanning)

```bash
# Scan image
trivy image myimage:latest

# Scan filesystem
trivy fs /path/to/project

# Output formats
trivy image --format json myimage:latest
trivy image --format sarif myimage:latest

# Severity filtering
trivy image --severity HIGH,CRITICAL myimage:latest
```

#### OWASP Dependency-Check

```bash
# Scan project
dependency-check --project myapp --scan /path/to/project

# Output formats
dependency-check --format HTML --out report.html
dependency-check --format JSON --out report.json

# Suppression file
dependency-check --suppression suppressions.xml
```

### Security Scanning in CI/CD

#### GitHub Actions

```yaml
name: Security Audit

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 0 * * *'  # Daily

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run npm audit
        run: npm audit --audit-level=moderate

      - name: Run Snyk
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high
```

#### GitLab CI

```yaml
security_scan:
  image: node:18
  stage: test
  script:
    - npm ci
    - npm audit --audit-level=moderate
  allow_failure: false
  only:
    - merge_requests
    - main
```

### Vulnerability Response Process

```
┌──────────────────────────────────────────────────────┐
│         Vulnerability Response Workflow               │
├──────────────────────────────────────────────────────┤
│                                                       │
│  1. Detection                                         │
│     ├─ Automated scan finds vulnerability            │
│     └─ Alert sent to team                            │
│                                                       │
│  2. Triage (< 4 hours)                               │
│     ├─ Assess severity (CVSS score)                  │
│     ├─ Check exploitability                          │
│     ├─ Evaluate impact                               │
│     └─ Prioritize                                    │
│                                                       │
│  3. Investigation (< 24 hours)                       │
│     ├─ Is vulnerability exploitable in our context?  │
│     ├─ Is there a patch available?                   │
│     ├─ Are there workarounds?                        │
│     └─ Document findings                             │
│                                                       │
│  4. Remediation                                      │
│     ├─ Update dependency                             │
│     ├─ Test thoroughly                               │
│     ├─ Deploy patch                                  │
│     └─ Verify fix                                    │
│                                                       │
│  5. Post-Incident                                    │
│     ├─ Update runbooks                               │
│     ├─ Improve detection                             │
│     └─ Share lessons learned                         │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Severity Levels

```
┌─────────┬──────────┬─────────────────────────────────────┐
│ Level   │ CVSS     │ Response Time                        │
├─────────┼──────────┼─────────────────────────────────────┤
│ Critical│ 9.0-10.0 │ Immediate (< 4 hours)               │
│ High    │ 7.0-8.9  │ Urgent (< 24 hours)                 │
│ Medium  │ 4.0-6.9  │ Soon (< 1 week)                     │
│ Low     │ 0.1-3.9  │ Eventually (< 1 month)              │
└─────────┴──────────┴─────────────────────────────────────┘
```

---

## Automated Updates

### Dependabot (GitHub)

**Configuration** (`.github/dependabot.yml`):
```yaml
version: 2
updates:
  # JavaScript dependencies
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "America/New_York"
    open-pull-requests-limit: 10
    reviewers:
      - "team-leads"
    labels:
      - "dependencies"
      - "npm"
    commit-message:
      prefix: "chore"
      include: "scope"

    # Version update strategies
    versioning-strategy: auto

    # Grouping
    groups:
      development-dependencies:
        dependency-type: "development"
        update-types:
          - "minor"
          - "patch"

    # Ignore specific dependencies
    ignore:
      - dependency-name: "lodash"
        versions: ["4.x"]

    # Allow specific update types
    allow:
      - dependency-type: "direct"
      - dependency-type: "production"

  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"

  # Docker
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

**Features**:
- Multi-ecosystem support
- Grouped updates
- Custom schedules
- Auto-merge (with caution)
- Security-only updates
- Version strategies

### Renovate

**Configuration** (`renovate.json`):
```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:base"
  ],
  "schedule": [
    "before 9am on Monday"
  ],
  "labels": [
    "dependencies"
  ],
  "assignees": [
    "@team-lead"
  ],

  "packageRules": [
    {
      "matchUpdateTypes": ["minor", "patch"],
      "matchCurrentVersion": "!/^0/",
      "automerge": true,
      "automergeType": "pr",
      "automergeStrategy": "squash"
    },
    {
      "matchDepTypes": ["devDependencies"],
      "automerge": true
    },
    {
      "matchPackagePatterns": ["^@types/"],
      "automerge": true
    },
    {
      "groupName": "React ecosystem",
      "matchPackagePatterns": ["^react", "^@types/react"],
      "schedule": ["before 9am on Monday"]
    }
  ],

  "vulnerabilityAlerts": {
    "enabled": true,
    "labels": ["security"],
    "assignees": ["@security-team"]
  },

  "prConcurrentLimit": 10,
  "prCreation": "not-pending",
  "prHourlyLimit": 5,

  "timezone": "America/New_York"
}
```

**Advanced features**:
- Regex matching
- Custom scheduling
- Auto-merge rules
- Grouping strategies
- Platform agnostic
- Self-hosted option

### npm-check-updates

```bash
# Check for updates
npx npm-check-updates

# Update package.json
npx npm-check-updates -u

# Interactive mode
npx npm-check-updates -i

# Target specific versions
npx npm-check-updates --target minor
npx npm-check-updates --target latest

# Filter by package
npx npm-check-updates --filter react
npx npm-check-updates --reject lodash
```

### cargo-edit

```bash
# Install
cargo install cargo-edit

# Upgrade dependencies
cargo upgrade

# Upgrade specific package
cargo upgrade tokio

# Upgrade to latest compatible
cargo upgrade --compatible

# Check for outdated
cargo outdated
```

### Update Strategy Decision Tree

```
┌────────────────────────────────────────────────────┐
│  Should I auto-merge this update?                  │
├────────────────────────────────────────────────────┤
│                                                     │
│  Is it a security patch?                           │
│  ├─ Yes: Auto-merge after tests ✅                 │
│  └─ No: Continue evaluation                        │
│                                                     │
│  Is it a dev dependency?                           │
│  ├─ Yes: Auto-merge patch/minor ✅                 │
│  └─ No: Continue evaluation                        │
│                                                     │
│  Is it a type definition (@types/*)?               │
│  ├─ Yes: Auto-merge ✅                             │
│  └─ No: Continue evaluation                        │
│                                                     │
│  Is it a patch version (x.y.PATCH)?                │
│  ├─ Yes: Auto-merge after tests ✅                 │
│  └─ No: Continue evaluation                        │
│                                                     │
│  Is it a minor version (x.MINOR.y)?                │
│  ├─ Yes: Review changelog, auto-merge if safe ⚠️  │
│  └─ No: Continue evaluation                        │
│                                                     │
│  Is it a major version (MAJOR.x.y)?                │
│  └─ Manual review required ❌                      │
│                                                     │
└────────────────────────────────────────────────────┘
```

---

## License Compliance

### License Types

#### Permissive Licenses

**MIT License**:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use
- ⚠️ Attribution required

**Apache 2.0**:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Patent grant
- ⚠️ Attribution required
- ⚠️ Notice of modifications

**BSD 3-Clause**:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ⚠️ Attribution required
- ⚠️ No endorsement clause

#### Copyleft Licenses

**GPL v2/v3**:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ❌ Requires derivative works to be GPL
- ❌ Entire program must be open source

**LGPL**:
- ✅ Commercial use
- ✅ Dynamic linking allowed
- ❌ Modifications to LGPL code must be released

**AGPL v3**:
- ✅ Commercial use
- ❌ Network use triggers distribution
- ❌ Entire program must be open source
- ❌ Most restrictive

#### Proprietary Licenses

- ❌ Custom terms
- ❌ May prohibit commercial use
- ❌ May prohibit redistribution
- ⚠️ Always read the terms

### License Compatibility

```
┌──────────────────────────────────────────────────┐
│  License Compatibility Matrix                    │
├──────────────────────────────────────────────────┤
│                                                   │
│  Your Project  │ Can use dependencies with:      │
│  ─────────────────────────────────────────────── │
│  Proprietary   │ MIT, Apache, BSD ✅             │
│                │ GPL, AGPL ❌                    │
│                │ LGPL ⚠️ (dynamic link only)     │
│                                                   │
│  MIT           │ MIT, Apache, BSD ✅             │
│                │ GPL, AGPL ❌                    │
│                │ LGPL ⚠️                         │
│                                                   │
│  GPL           │ MIT, Apache, BSD, GPL ✅        │
│                │ AGPL ❌                         │
│                │ LGPL ✅                         │
│                                                   │
│  AGPL          │ MIT, Apache, BSD, GPL, AGPL ✅  │
│                                                   │
└──────────────────────────────────────────────────┘
```

### License Checking Tools

#### license-checker (npm)

```bash
# Install
npm install -g license-checker

# List all licenses
license-checker

# Summary
license-checker --summary

# Fail on specific licenses
license-checker --failOn "GPL;AGPL"

# Output formats
license-checker --json > licenses.json
license-checker --csv > licenses.csv

# Check custom packages
license-checker --customPath /path/to/format.json
```

#### pip-licenses (Python)

```bash
# Install
pip install pip-licenses

# List licenses
pip-licenses

# Output formats
pip-licenses --format=json > licenses.json
pip-licenses --format=markdown > licenses.md

# Filter by license
pip-licenses --filter-code-license MIT
```

#### cargo-license (Rust)

```bash
# Install
cargo install cargo-license

# List licenses
cargo license

# Output formats
cargo license --json > licenses.json
```

#### go-licenses (Go)

```bash
# Install
go install github.com/google/go-licenses@latest

# Check licenses
go-licenses check ./...

# Report licenses
go-licenses report ./... --template licenses.tpl

# Save license files
go-licenses save ./... --save_path=./licenses
```

### License Policy

**Example policy**:
```yaml
# .license-policy.yaml
allowed:
  - MIT
  - Apache-2.0
  - BSD-3-Clause
  - ISC

allowed_with_approval:
  - LGPL-3.0

forbidden:
  - GPL-2.0
  - GPL-3.0
  - AGPL-3.0

unknown_licenses:
  action: fail
  exceptions:
    - package-with-custom-license  # Manually reviewed
```

### CI/CD License Checking

```yaml
# GitHub Actions
name: License Check

on: [push, pull_request]

jobs:
  license-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3

      - name: Install dependencies
        run: npm ci

      - name: Check licenses
        run: |
          npx license-checker \
            --failOn "GPL;AGPL" \
            --summary
```

---

## Dependency Graphs

### Visualization Tools

#### npm list

```bash
# View tree
npm list

# Limit depth
npm list --depth=1

# Filter by package
npm list lodash

# Show all versions
npm list --all

# Production only
npm list --prod
```

#### Graphviz visualization

```bash
# Generate graph
npm list --json | \
  jq -r '.dependencies | to_entries[] | "\(.key) -> \(.value.dependencies | keys[])"' | \
  dot -Tpng > deps.png
```

#### cargo tree

```bash
# View tree
cargo tree

# Limit depth
cargo tree --depth 1

# Show duplicates
cargo tree --duplicates

# Invert tree (show dependents)
cargo tree --invert package-name

# Show features
cargo tree --features "feature1,feature2"

# Filter edges
cargo tree --edges normal      # Normal dependencies only
cargo tree --edges dev         # Dev dependencies
cargo tree --edges build       # Build dependencies
```

#### go mod graph

```bash
# Show graph
go mod graph

# Pretty print
go mod graph | sort | uniq

# Find path to package
go mod graph | grep package-name

# Visualize with graphviz
go mod graph | \
  sed 's/@[^ ]*//g' | \
  awk '{print "\""$1"\" -> \""$2"\""}' | \
  sort | uniq | \
  (echo "digraph {"; cat; echo "}") | \
  dot -Tpng > deps.png
```

### Dependency Analysis

#### Finding circular dependencies

```bash
# JavaScript (using madge)
npm install -g madge
madge --circular src/

# Rust (cargo will error on circular dependencies)
cargo build  # Will fail if circular

# Go (detect import cycles)
go list -f '{{.ImportPath}} {{.Imports}}' ./... | \
  grep -E 'pkg/a.*pkg/b|pkg/b.*pkg/a'
```

#### Finding duplicate dependencies

```bash
# npm
npm dedupe                    # Remove duplicates
npm ls package --depth=999   # Find all versions

# pnpm
pnpm list --depth Infinity | grep package

# cargo
cargo tree --duplicates       # Show duplicate dependencies

# Go (Go modules prevent duplicates)
go mod graph | sort | uniq -d
```

#### Finding unused dependencies

```bash
# JavaScript (depcheck)
npx depcheck

# Rust (cargo-udeps)
cargo install cargo-udeps
cargo +nightly udeps

# Go (requires manual checking)
go mod tidy                   # Removes unused
go mod why package           # Why is package needed?
```

---

## Monorepo Dependency Management

### Workspace Features

#### npm Workspaces

**package.json (root)**:
```json
{
  "name": "my-monorepo",
  "private": true,
  "workspaces": [
    "packages/*",
    "apps/*"
  ]
}
```

**Commands**:
```bash
# Install all workspaces
npm install

# Add dependency to specific workspace
npm install lodash -w @myorg/package-a

# Run script in workspace
npm run build -w @myorg/package-a

# Run script in all workspaces
npm run test --workspaces

# List workspaces
npm ls --workspaces --depth=0
```

#### Yarn Workspaces

**package.json**:
```json
{
  "private": true,
  "workspaces": [
    "packages/*"
  ]
}
```

**Commands**:
```bash
# Install all workspaces
yarn install

# Add dependency to workspace
yarn workspace @myorg/package-a add lodash

# Run command in workspace
yarn workspace @myorg/package-a build

# Run in all workspaces
yarn workspaces run build
```

#### pnpm Workspaces

**pnpm-workspace.yaml**:
```yaml
packages:
  - 'packages/*'
  - 'apps/*'
  - '!**/test/**'
```

**Commands**:
```bash
# Install all workspaces
pnpm install

# Add dependency to workspace
pnpm add lodash --filter @myorg/package-a

# Run in workspace
pnpm --filter @myorg/package-a build

# Run in all workspaces
pnpm -r build
```

#### Cargo Workspaces

**Cargo.toml (root)**:
```toml
[workspace]
members = [
    "crates/package-a",
    "crates/package-b",
]

[workspace.dependencies]
tokio = "1.28"
serde = "1.0"
```

**Cargo.toml (member)**:
```toml
[dependencies]
tokio = { workspace = true }
package-b = { path = "../package-b" }
```

**Commands**:
```bash
# Build all workspace members
cargo build --workspace

# Test all members
cargo test --workspace

# Update workspace dependencies
cargo update
```

### Version Synchronization

#### Changesets

```bash
# Install
npm install -g @changesets/cli
npm init @changesets/init

# Add changeset
npx changeset add

# Version packages
npx changeset version

# Publish
npx changeset publish
```

**changeset example**:
```markdown
---
"@myorg/package-a": minor
"@myorg/package-b": patch
---

Add new feature to package-a
```

#### Lerna

```bash
# Install
npm install -g lerna

# Initialize
lerna init

# Version packages
lerna version

# Publish packages
lerna publish

# Run commands
lerna run build
lerna run test --scope @myorg/package-a
```

### Dependency Hoisting

**Benefits**:
- Reduced disk space
- Faster installation
- Consistent versions

**Challenges**:
- Phantom dependencies
- Version conflicts
- Build complexity

**pnpm approach** (recommended):
```yaml
# .npmrc
hoist=false                   # Strict isolation
public-hoist-pattern[]=*eslint*  # Hoist only specific packages
```

---

## Private Package Registries

### npm Private Registry

#### Verdaccio (self-hosted)

**Installation**:
```bash
# Install
npm install -g verdaccio

# Run
verdaccio

# Configure
verdaccio --config /path/to/config.yaml
```

**config.yaml**:
```yaml
storage: /path/to/storage

auth:
  htpasswd:
    file: /path/to/htpasswd

uplinks:
  npmjs:
    url: https://registry.npmjs.org/

packages:
  '@myorg/*':
    access: $authenticated
    publish: $authenticated
    unpublish: $authenticated

  '**':
    access: $all
    publish: $authenticated
    proxy: npmjs

logs:
  - { type: stdout, format: pretty, level: http }
```

**Usage**:
```bash
# Point npm to registry
npm set registry http://localhost:4873/

# Login
npm login --registry http://localhost:4873/

# Publish
npm publish --registry http://localhost:4873/
```

#### GitHub Packages

**.npmrc**:
```ini
@myorg:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

**package.json**:
```json
{
  "name": "@myorg/package",
  "repository": "https://github.com/myorg/repo",
  "publishConfig": {
    "registry": "https://npm.pkg.github.com"
  }
}
```

**Publish**:
```bash
npm publish
```

#### AWS CodeArtifact

**Setup**:
```bash
# Login
aws codeartifact login --tool npm --domain my-domain --repository my-repo

# Get endpoint
aws codeartifact get-repository-endpoint \
  --domain my-domain \
  --repository my-repo \
  --format npm
```

**.npmrc**:
```ini
registry=https://my-domain-111122223333.d.codeartifact.us-east-1.amazonaws.com/npm/my-repo/
//my-domain-111122223333.d.codeartifact.us-east-1.amazonaws.com/npm/my-repo/:always-auth=true
```

### Python Private Registry

#### PyPI Server

```bash
# Install
pip install pypiserver

# Run
pypi-server -p 8080 /path/to/packages

# Upload package
twine upload --repository-url http://localhost:8080 dist/*
```

**pip.conf**:
```ini
[global]
index-url = http://localhost:8080/simple/
trusted-host = localhost
```

### Cargo Private Registry

**config.toml**:
```toml
[source.my-registry]
registry = "https://my-registry.com/git/index"

[source.crates-io]
replace-with = "my-registry"
```

---

## Vendoring and Bundling

### Go Vendoring

```bash
# Create vendor directory
go mod vendor

# Build using vendor
go build -mod=vendor

# Verify vendor
go mod verify
```

**Benefits**:
- Offline builds
- Corporate firewall compliance
- Dependency auditability

**Drawbacks**:
- Increased repository size
- Stale dependencies
- Merge conflicts

### Cargo Vendoring

```bash
# Vendor dependencies
cargo vendor

# Build using vendor
cargo build --offline

# Configuration
mkdir -p .cargo
cat > .cargo/config.toml <<EOF
[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "vendor"
EOF
```

### JavaScript Bundling

**Webpack**:
```javascript
// webpack.config.js
module.exports = {
  entry: './src/index.js',
  output: {
    filename: 'bundle.js',
    path: __dirname + '/dist'
  },
  optimization: {
    minimize: true
  }
};
```

**Rollup**:
```javascript
// rollup.config.js
export default {
  input: 'src/index.js',
  output: {
    file: 'dist/bundle.js',
    format: 'esm'
  }
};
```

**Vite**:
```javascript
// vite.config.js
export default {
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom']
        }
      }
    }
  }
};
```

---

## Build Reproducibility

### Principles

1. **Deterministic inputs**: Same code + dependencies = same output
2. **Pinned dependencies**: Lock files ensure exact versions
3. **Environment isolation**: Containers provide consistent environments
4. **Timestamp handling**: Avoid embedding build timestamps
5. **Parallel build safety**: Avoid race conditions

### Techniques

#### Use Lock Files

```bash
# npm
npm ci                         # Clean install from lock

# yarn
yarn install --frozen-lockfile

# pnpm
pnpm install --frozen-lockfile

# pip
pip install -r requirements.txt --require-hashes

# cargo
cargo build  # Uses Cargo.lock automatically

# go
go build  # Uses go.sum automatically
```

#### Docker Multi-stage Builds

```dockerfile
# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
CMD ["node", "dist/index.js"]
```

#### Nix

```nix
{ pkgs ? import <nixpkgs> {} }:

pkgs.stdenv.mkDerivation {
  name = "my-app";
  src = ./.;

  buildInputs = with pkgs; [
    nodejs-18_x
  ];

  buildPhase = ''
    npm ci
    npm run build
  '';

  installPhase = ''
    mkdir -p $out
    cp -r dist $out/
  '';
}
```

#### Cache Key Generation

```bash
# npm
echo "$(cat package-lock.json | sha256sum)"

# pip
echo "$(cat requirements.txt | sha256sum)"

# cargo
echo "$(cat Cargo.lock | sha256sum)"
```

**GitHub Actions**:
```yaml
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

---

## Supply Chain Security

### Threats

1. **Typosquatting**: Packages with names similar to popular packages
2. **Dependency confusion**: Mixing public and private packages
3. **Compromised maintainers**: Attacker gains access to maintainer account
4. **Malicious code injection**: Backdoors in dependencies
5. **Build system compromise**: Attacking CI/CD pipeline

### Defenses

#### Subresource Integrity (SRI)

```html
<script src="https://cdn.example.com/lib.js"
        integrity="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/uxy9rx7HNQlGYl1kPzQho1wx4JwY8wC"
        crossorigin="anonymous"></script>
```

**Generate SRI hash**:
```bash
cat lib.js | openssl dgst -sha384 -binary | openssl base64 -A
```

#### Package Signing

**npm**:
```bash
# Verify package signature
npm audit signatures
```

**Cargo**:
```bash
# Verify checksums
cargo verify-project
```

**Go**:
```bash
# Verify checksums
go mod verify
```

#### Software Bill of Materials (SBOM)

**Generate SBOM**:
```bash
# CycloneDX (npm)
npx @cyclonedx/bom

# Syft (multi-language)
syft packages dir:. -o cyclonedx-json > sbom.json

# SPDX
syft packages dir:. -o spdx-json > sbom.spdx.json
```

**SBOM formats**:
- **CycloneDX**: Modern, comprehensive
- **SPDX**: Industry standard
- **SWID**: Software identification tags

#### Dependency Pinning

```json
{
  "dependencies": {
    "express": "4.18.2"  // Exact version, not ^4.18.2
  },
  "overrides": {
    "lodash": "4.17.21"  // Force specific version globally
  }
}
```

#### Private Registry

```ini
# .npmrc
registry=https://npm.mycompany.com/
@myorg:registry=https://npm.mycompany.com/
```

**Benefits**:
- Control over allowed packages
- Internal package hosting
- Vulnerability scanning gateway
- License compliance enforcement

#### Automated Scanning

```yaml
# GitHub Actions
name: Supply Chain Security

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

---

## Deprecation Handling

### Identifying Deprecated Dependencies

```bash
# npm
npm outdated

# Check for deprecation warnings
npm ls

# yarn
yarn outdated

# cargo
cargo outdated

# pip
pip list --outdated
```

### Deprecation Strategies

#### Immediate Replacement

```bash
# Remove deprecated package
npm uninstall old-package

# Install replacement
npm install new-package

# Update imports
# Before:
import { fn } from 'old-package';

# After:
import { fn } from 'new-package';
```

#### Gradual Migration

```javascript
// adapter.js - Compatibility layer
import { newFn } from 'new-package';

export function oldFn(...args) {
  console.warn('oldFn is deprecated, use newFn from new-package');
  return newFn(...args);
}
```

#### Fork and Maintain

```bash
# Fork deprecated package
git clone https://github.com/original/deprecated-package
cd deprecated-package

# Apply security patches
# ...

# Publish under new name
npm publish @myorg/maintained-package
```

### Tracking Deprecations

**.deprecations.json**:
```json
{
  "deprecated": [
    {
      "package": "request",
      "version": "2.88.2",
      "reason": "No longer maintained",
      "replacement": "axios",
      "migration_issue": "PROJ-123",
      "target_removal": "2024-Q2"
    }
  ]
}
```

---

## Breaking Change Management

### Pre-upgrade Checklist

```
┌──────────────────────────────────────────────────┐
│  Before Upgrading to Major Version               │
├──────────────────────────────────────────────────┤
│                                                   │
│  [ ] Read CHANGELOG and MIGRATION_GUIDE          │
│  [ ] Check GitHub issues for migration problems  │
│  [ ] Search codebase for affected API usage      │
│  [ ] Create feature branch                       │
│  [ ] Update dependency                           │
│  [ ] Fix type errors                             │
│  [ ] Update tests                                │
│  [ ] Run full test suite                         │
│  [ ] Test in staging environment                 │
│  [ ] Monitor error rates post-deploy             │
│  [ ] Document breaking changes                   │
│                                                   │
└──────────────────────────────────────────────────┘
```

### Codemod Tools

**jscodeshift** (JavaScript):
```javascript
// transform.js
module.exports = function(file, api) {
  const j = api.jscodeshift;
  const root = j(file.source);

  // Replace old API with new API
  root
    .find(j.CallExpression, {
      callee: { name: 'oldApi' }
    })
    .replaceWith(path => {
      return j.callExpression(
        j.identifier('newApi'),
        path.node.arguments
      );
    });

  return root.toSource();
};

// Run transformation
npx jscodeshift -t transform.js src/**/*.js
```

**comby** (multi-language):
```bash
# Replace pattern
comby 'oldApi(:[args])' 'newApi(:[args])' -in-place src/
```

### Gradual Rollout

```javascript
// feature-flag.js
const ENABLE_NEW_API = process.env.ENABLE_NEW_API === 'true';

export function myFunction() {
  if (ENABLE_NEW_API) {
    return newApi();
  } else {
    return oldApi();
  }
}
```

---

## Anti-Patterns

### Never Do This

#### 1. Wildcard Versions

```json
{
  "dependencies": {
    "express": "*",        // ❌ Unpredictable
    "lodash": "latest"     // ❌ Unpredictable
  }
}
```

#### 2. Deleting Lock Files

```bash
# ❌ Never delete lock files to "fix" issues
rm package-lock.json
rm yarn.lock

# ✅ Instead, investigate the root cause
npm ls package
npm explain package
```

#### 3. Committing node_modules

```bash
# ❌ Never commit dependency directories
git add node_modules/
git add vendor/
git add target/

# ✅ Use .gitignore
echo "node_modules/" >> .gitignore
```

#### 4. Installing Without Testing

```bash
# ❌ Update and deploy without testing
npm update && git commit -am "deps" && git push

# ✅ Update, test, then commit
npm update
npm test
npm run build
git commit -am "chore: update dependencies"
```

#### 5. Ignoring Security Warnings

```bash
# ❌ Suppress all warnings
npm audit --audit-level=none

# ✅ Fix vulnerabilities
npm audit fix
npm audit fix --force  # If needed
```

#### 6. Using Deprecated Packages

```bash
# ❌ Continue using deprecated packages
npm install request  # Deprecated!

# ✅ Use maintained alternatives
npm install axios
```

#### 7. No Dependency Review

```bash
# ❌ Add dependency without review
npm install some-random-package

# ✅ Review before adding
npm info some-random-package
npm view some-random-package versions
npm audit signatures
# Check GitHub stars, last commit, maintainers
```

#### 8. Phantom Dependencies

```javascript
// ❌ Using transitive dependency directly
import _ from 'lodash';  // Not in package.json!

// ✅ Declare explicit dependency
// Add to package.json first
import _ from 'lodash';
```

---

## Troubleshooting Guide

### Common Issues

#### Issue: "Cannot find module"

**Cause**: Missing dependency or incorrect import path

**Solution**:
```bash
# Check if installed
npm ls package-name

# Reinstall (⚠️ WARNING: Deletes all installed dependencies)
# Consider backing up node_modules if you have local patches
rm -rf node_modules package-lock.json
npm install

# Check import path
# Before:
import { fn } from 'package';  // Wrong path

# After:
import { fn } from 'package/lib/fn';  // Correct path
```

#### Issue: Version conflict

**Error**: `ERESOLVE unable to resolve dependency tree`

**Solution**:
```bash
# View conflict details
npm install --verbose

# Force resolution (legacy peer deps)
npm install --legacy-peer-deps

# Or use overrides
# package.json
{
  "overrides": {
    "conflicting-package": "1.0.0"
  }
}
```

#### Issue: Slow installation

**Solutions**:
```bash
# Use faster package manager
npm install -g pnpm
pnpm install

# Use CI mode (no integrity checks)
npm ci

# Parallel installation
npm install --prefer-offline --no-audit

# Clean cache
npm cache clean --force
```

#### Issue: Integrity checksum mismatch

**Error**: `sha512-... integrity checksum failed`

**Solution**:
```bash
# Clear cache
npm cache clean --force

# Delete lock file and reinstall
rm package-lock.json
npm install

# Or verify registry
npm config get registry
```

#### Issue: EACCES permission errors

**Error**: `EACCES: permission denied`

**Solution**:
```bash
# Fix npm permissions (preferred)
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.profile
source ~/.profile

# Or use nvm (recommended)
# Safer: Download, inspect, then execute
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh -o nvm-install.sh
# Inspect the script before running
less nvm-install.sh
bash nvm-install.sh
nvm install node
```

#### Issue: Peer dependency warnings

**Warning**: `ERESOLVE could not resolve`

**Solution**:
```bash
# Install peer dependencies
npm install peer-dependency@version

# Or ignore (not recommended)
npm install --legacy-peer-deps

# Or use overrides
{
  "overrides": {
    "peer-dependency": "version"
  }
}
```

#### Issue: Build fails after update

**Solution**:
```bash
# Rollback update
git checkout -- package.json package-lock.json
npm install

# Or pin previous version
npm install package@previous-version

# Identify breaking change
npm view package versions
npm view package@version
# Read changelog
```

### Debugging Tools

```bash
# npm
npm config list                 # Show config
npm ls --depth=0               # Direct dependencies
npm ls package                 # Find package
npm explain package            # Why is package installed?
npm outdated                   # Check for updates
npm audit                      # Security audit

# yarn
yarn why package              # Dependency explanation
yarn check                    # Verify integrity
yarn cache dir               # Cache location

# pnpm
pnpm why package             # Why is package installed?
pnpm store path              # Store location
pnpm store status            # Store statistics

# cargo
cargo tree                   # Dependency tree
cargo tree -i package        # Reverse dependencies
cargo update --dry-run       # Preview updates

# go
go mod why package          # Why is package needed?
go mod graph                # Dependency graph
go list -m all              # List all modules
```

---

## Conclusion

Effective dependency management balances:
- **Security**: Rapid vulnerability patching
- **Stability**: Reproducible builds
- **Velocity**: Fast feature delivery
- **Compliance**: License requirements
- **Sustainability**: Long-term maintainability

**Key Principles**:
1. Always commit lock files
2. Automate security scanning
3. Review dependencies before adding
4. Update regularly, test thoroughly
5. Monitor for deprecations
6. Enforce license policies
7. Use semantic versioning correctly
8. Minimize dependency count

**Golden Rule**: Dependencies are liabilities, not assets. Every dependency adds maintenance burden and security risk. Choose wisely, update proactively, and remove aggressively.
