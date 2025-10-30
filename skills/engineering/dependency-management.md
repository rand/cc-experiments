---
name: engineering-dependency-management
description: Strategic approach to managing external libraries, frameworks, and packages throughout the software development lifecycle
skill_id: engineering.dependency-management
version: 1.0.0
category: engineering
requires: []
tags: [dependencies, security, versioning, packages, supply-chain]
platforms: [all]
model: claude-sonnet-4.5
last_validated: 2025-10-29
---

# Dependency Management

> Strategic approach to managing external libraries, frameworks, and packages throughout the software development lifecycle

## Overview

Dependency management is the practice of tracking, updating, and securing external code that your project relies on. It encompasses version selection, conflict resolution, security patching, license compliance, and supply chain risk management.

**When to Apply This Skill**:
- Starting new projects (establish dependency strategy)
- Regular maintenance (weekly/monthly dependency updates)
- Security incidents (emergency patching)
- Production incidents related to dependencies
- Build reproducibility issues
- License compliance audits
- Monorepo management
- Private package management

## Core Principles

### 1. Explicit Over Implicit

Always declare dependencies explicitly with version constraints:

```json
// Good - Explicit version constraints
{
  "dependencies": {
    "express": "^4.18.0",
    "lodash": "~4.17.21",
    "axios": "1.6.0"
  }
}

// Bad - Implicit or missing constraints
{
  "dependencies": {
    "express": "*",
    "lodash": "latest"
  }
}
```

### 2. Lock Files Are Mandatory

Lock files ensure reproducible builds:
- `package-lock.json` (npm)
- `yarn.lock` (Yarn)
- `Pipfile.lock` (Python/pipenv)
- `Cargo.lock` (Rust)
- `go.sum` (Go)

**Always commit lock files to version control.**

### 3. Security First

Security vulnerabilities in dependencies are attack vectors:
- Run automated security audits
- Monitor vulnerability databases
- Apply security patches promptly
- Use Software Bill of Materials (SBOM)

### 4. Minimize Dependency Count

Every dependency adds:
- Maintenance burden
- Security surface area
- Build time
- Binary size
- Supply chain risk

**Ask**: Do we really need this dependency?

## Semantic Versioning (SemVer)

Understanding SemVer is critical for dependency management:

```
MAJOR.MINOR.PATCH (e.g., 2.4.7)

MAJOR: Breaking changes (2.0.0 → 3.0.0)
MINOR: New features, backward compatible (2.4.0 → 2.5.0)
PATCH: Bug fixes, backward compatible (2.4.7 → 2.4.8)
```

### Version Range Specifiers

```bash
# Exact version
"1.2.3"           # Only 1.2.3

# Caret (^) - Compatible changes
"^1.2.3"          # ≥1.2.3 <2.0.0 (minor/patch updates)
"^0.2.3"          # ≥0.2.3 <0.3.0 (patch updates only for 0.x)

# Tilde (~) - Patch-level changes
"~1.2.3"          # ≥1.2.3 <1.3.0 (patch updates only)

# Wildcards
"1.2.x"           # 1.2.0, 1.2.1, 1.2.2, etc.
"1.x"             # 1.0.0, 1.1.0, 1.2.0, etc.

# Ranges
">=1.2.3 <2.0.0"  # Greater than or equal to 1.2.3, less than 2.0.0
```

## Update Strategies

### Conservative Strategy

**When**: Production systems, regulated environments, risk-averse teams

```yaml
# Dependabot example - security only
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 3
    # Only security updates
    allow:
      - dependency-type: "all"
        update-types: ["security"]
```

### Balanced Strategy

**When**: Most production applications

```yaml
# Dependabot example - security + patch
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    allow:
      - dependency-type: "all"
        update-types: ["security", "patch"]
```

### Aggressive Strategy

**When**: Early-stage projects, prototypes, staying on cutting edge

```yaml
# Dependabot example - all updates
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 20
```

## Security Scanning

### Tool Options

| Tool | Languages | Features | Cost |
|------|-----------|----------|------|
| **Dependabot** | Multiple | Auto-PRs, GitHub native | Free |
| **Snyk** | Multiple | Fix PRs, license scanning | Free tier |
| **npm audit** | JavaScript | Built-in, fast | Free |
| **pip-audit** | Python | PyPI vulnerabilities | Free |
| **cargo audit** | Rust | RustSec database | Free |
| **Trivy** | Multiple | Container scanning | Free |
| **OWASP Dependency-Check** | Multiple | NIST NVD database | Free |

### Audit Workflow

```bash
# JavaScript/Node.js
npm audit                    # Check vulnerabilities
npm audit fix               # Auto-fix vulnerabilities
npm audit fix --force       # Apply breaking changes

# Python
pip-audit                   # Check vulnerabilities
pip-audit --fix            # Generate fixed requirements

# Rust
cargo audit                 # Check RustSec database
cargo audit fix            # Update Cargo.toml

# Go
go list -json -m all | nancy sleuth  # Check vulnerabilities
```

## Common Dependency Issues

### 1. Dependency Hell

**Problem**: Conflicting version requirements

```
Project requires:
  - package-a@2.0 (which requires util@^1.0)
  - package-b@3.0 (which requires util@^2.0)

ERROR: Cannot resolve util version
```

**Solutions**:
- Use peer dependencies carefully
- Prefer flat dependency trees
- Consider dependency override/resolutions
- Use tools like npm overrides or yarn resolutions

### 2. Phantom Dependencies

**Problem**: Using transitive dependencies directly

```javascript
// Bad - lodash is not in package.json but comes transitively
import _ from 'lodash';

// Good - Explicitly declare dependency
// Add lodash to package.json first
import _ from 'lodash';
```

### 3. Version Drift

**Problem**: Different versions in different environments

**Solutions**:
- Commit lock files
- Use exact versions in CI/CD
- Validate lock file integrity
- Use `npm ci` instead of `npm install` in CI

### 4. Outdated Dependencies

**Problem**: Using old versions with known vulnerabilities

**Solutions**:
- Automated update tools (Dependabot, Renovate)
- Regular update schedules
- Monitor deprecation notices
- Track end-of-life dates

## License Compliance

### License Categories

```bash
# Permissive licenses (generally safe)
MIT, Apache-2.0, BSD-3-Clause, ISC

# Copyleft licenses (require attribution/disclosure)
GPL-2.0, GPL-3.0, AGPL-3.0, LGPL

# Proprietary/Commercial licenses
Custom commercial licenses, check restrictions
```

### License Checking

```bash
# JavaScript
npx license-checker --summary

# Python
pip-licenses --format=table

# Go
go-licenses check ./...

# Rust
cargo-license --json
```

## Tools Reference

### Package Managers

```bash
# JavaScript
npm install package@version      # Install specific version
npm update                       # Update dependencies
npm outdated                     # Check for updates
npm dedupe                       # Reduce duplication

# Python (uv - preferred)
uv add package==version         # Add dependency
uv sync                         # Install from lock
uv lock                         # Update lock file
uv tree                         # View dependency tree

# Rust
cargo add package@version       # Add dependency
cargo update                    # Update dependencies
cargo tree                      # View dependency tree

# Go
go get package@version          # Get dependency
go mod tidy                     # Clean up go.mod
go mod graph                    # Dependency graph
go mod why package              # Why is package included?
```

### Dependency Update Tools

```bash
# Dependabot (GitHub)
# Configured via .github/dependabot.yml

# Renovate (cross-platform)
# Configured via renovate.json

# npm-check-updates (JavaScript)
npx npm-check-updates          # Check for updates
npx npm-check-updates -u       # Update package.json

# cargo-edit (Rust)
cargo upgrade                  # Upgrade dependencies
```

## Best Practices Checklist

### Setup Phase
- [ ] Choose appropriate version constraints (^, ~, exact)
- [ ] Configure lock files (and commit them)
- [ ] Set up automated security scanning
- [ ] Configure dependency update automation
- [ ] Document dependency approval process
- [ ] Establish update cadence (weekly/monthly)

### Maintenance Phase
- [ ] Review and merge security updates within 24-48h
- [ ] Review other updates on schedule
- [ ] Run full test suite before merging updates
- [ ] Monitor for breaking changes in changelogs
- [ ] Keep lock files up to date
- [ ] Audit licenses periodically

### Incident Response
- [ ] Have rollback procedure ready
- [ ] Monitor for supply chain attacks
- [ ] Subscribe to security advisories
- [ ] Document emergency update process
- [ ] Test updates in staging first

## Anti-Patterns

### Never Do This

```bash
# ❌ Never commit node_modules or vendor directories
git add node_modules/

# ❌ Never use wildcard versions in production
"dependencies": { "express": "*" }

# ❌ Never ignore security warnings
npm audit --audit-level=none

# ❌ Never update dependencies without testing
npm update && git commit -am "update deps" && git push

# ❌ Never delete lock files to "fix" issues
rm package-lock.json
```

## Quick Reference

### Daily Operations

```bash
# Install dependencies
npm install / pip install / cargo build

# Check for vulnerabilities
npm audit / pip-audit / cargo audit

# Update single dependency
npm update package@latest
uv add --upgrade package

# View dependency tree
npm list --depth=1
cargo tree --depth 1
```

### Weekly Maintenance

```bash
# Check for outdated dependencies
npm outdated
cargo outdated

# Review and merge automated PRs
gh pr list --label dependencies

# Run full security audit
npm audit --audit-level=moderate
```

### Monthly Cleanup

```bash
# Remove unused dependencies
npm prune
cargo clean

# Analyze bundle size (JavaScript)
npx webpack-bundle-analyzer

# Check license compliance
npx license-checker --summary
```

## Resources

### Level 3 Resources

- **`resources/REFERENCE.md`**: Comprehensive 1,500+ line reference covering all aspects of dependency management
- **`resources/scripts/audit_dependencies.py`**: Multi-language dependency security auditing tool
- **`resources/scripts/update_dependencies.py`**: Automated dependency update tool with rollback
- **`resources/scripts/analyze_dep_graph.py`**: Dependency graph analysis and visualization
- **`resources/examples/`**: Production-ready configuration examples

### External Resources

- [Semantic Versioning Spec](https://semver.org/)
- [npm Documentation](https://docs.npmjs.com/)
- [Cargo Book](https://doc.rust-lang.org/cargo/)
- [Go Modules Reference](https://go.dev/ref/mod)
- [OWASP Dependency Check](https://owasp.org/www-project-dependency-check/)
- [NIST National Vulnerability Database](https://nvd.nist.gov/)

## Conclusion

Effective dependency management is about balance: staying secure and up-to-date while maintaining stability. Automate where possible, test thoroughly, and respond quickly to security issues. Good dependency hygiene prevents incidents and enables sustainable development velocity.
