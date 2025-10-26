---
name: collaboration-github-security-features
description: Dependabot, code scanning, secret scanning, SBOM generation, security advisories, and security best practices
---

# GitHub Security Features

**Scope**: Dependabot configuration and automation, CodeQL code scanning, secret scanning and protection, SBOM generation, security advisories, SECURITY.md policies, and vulnerability remediation

**Lines**: ~340

**Last Updated**: 2025-10-25

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Setting up automated dependency updates with Dependabot
- Configuring code scanning with CodeQL or third-party tools
- Enabling secret scanning and push protection
- Generating and exporting Software Bill of Materials (SBOM)
- Creating private security advisories
- Writing SECURITY.md policy files
- Responding to security vulnerabilities
- Automating security update workflows
- Implementing vulnerability disclosure processes

---

## Core Concepts

### Security Layers

```
Repository Security Layers:
1. Secret Scanning    → Detect leaked credentials
2. Push Protection    → Block secret commits
3. Code Scanning      → Find vulnerabilities in code
4. Dependabot Alerts  → Identify vulnerable dependencies
5. Dependabot Updates → Auto-update dependencies
6. SBOM Export        → Track software components
7. Security Advisories → Coordinate vulnerability disclosure
```

### Dependabot Components

**Dependabot Alerts**:
- Automatic vulnerability detection
- Severity levels: Critical, High, Medium, Low
- CVE tracking and GHSA integration

**Dependabot Security Updates**:
- Automatic PRs for vulnerable dependencies
- Compatibility checks
- Auto-merge capable

**Dependabot Version Updates**:
- Scheduled dependency updates
- Keep dependencies current
- Reduce technical debt

### Code Scanning Workflow

```
Code Push → CodeQL Analysis → Results → Alerts → Review → Fix → Retest
              ↓                  ↓         ↓
         Custom Queries    Security tab   Triage
```

---

## Patterns

### Dependabot Configuration

**Basic setup** (.github/dependabot.yml):
```yaml
version: 2
updates:
  # Enable version updates for npm
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "America/New_York"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "automated"
    reviewers:
      - "backend-team"
    assignees:
      - "security-lead"
    commit-message:
      prefix: "chore"
      include: "scope"

  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    allow:
      - dependency-type: "all"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "monthly"
```

**Advanced configuration**:
```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "daily"

    # Ignore specific dependencies
    ignore:
      - dependency-name: "express"
        # Ignore major version updates
        update-types: ["version-update:semver-major"]
      - dependency-name: "lodash"
        # Ignore all updates
        versions: ["*"]

    # Group updates together
    groups:
      production-dependencies:
        applies-to: "version-updates"
        dependency-type: "production"
      development-dependencies:
        applies-to: "version-updates"
        dependency-type: "development"

    # Custom versioning strategy
    versioning-strategy: "increase"  # or "widen", "increase-if-necessary"

    # Custom branch prefix
    target-branch: "develop"

    # Pull request limits
    open-pull-requests-limit: 10
```

**Multi-directory support**:
```yaml
version: 2
updates:
  # Frontend dependencies
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"

  # Backend dependencies
  - package-ecosystem: "npm"
    directory: "/backend"
    schedule:
      interval: "weekly"

  # Infrastructure
  - package-ecosystem: "terraform"
    directory: "/infrastructure"
    schedule:
      interval: "monthly"
```

### Auto-Merge Dependabot PRs

**GitHub Actions workflow** (.github/workflows/dependabot-auto-merge.yml):
```yaml
name: Dependabot Auto-Merge
on: pull_request

permissions:
  pull-requests: write
  contents: write

jobs:
  auto-merge:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - name: Fetch Dependabot metadata
        id: metadata
        uses: dependabot/fetch-metadata@v1
        with:
          github-token: "${{ secrets.GITHUB_TOKEN }}"

      - name: Auto-merge patch and minor updates
        if: |
          steps.metadata.outputs.update-type == 'version-update:semver-patch' ||
          steps.metadata.outputs.update-type == 'version-update:semver-minor'
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Approve PR
        if: |
          steps.metadata.outputs.update-type == 'version-update:semver-patch' ||
          steps.metadata.outputs.update-type == 'version-update:semver-minor'
        run: gh pr review --approve "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Safer auto-merge** (only security updates):
```yaml
name: Auto-Merge Security Updates
on: pull_request

jobs:
  auto-merge:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - uses: dependabot/fetch-metadata@v1
        id: metadata

      # Only auto-merge security updates
      - name: Auto-merge security updates
        if: steps.metadata.outputs.alert-state == 'FIXED'
        run: |
          gh pr review --approve "$PR_URL"
          gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Code Scanning with CodeQL

**Basic setup** (.github/workflows/codeql.yml):
```yaml
name: "CodeQL"

on:
  push:
    branches: [ "main", "develop" ]
  pull_request:
    branches: [ "main" ]
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM

jobs:
  analyze:
    name: Analyze
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write

    strategy:
      fail-fast: false
      matrix:
        language: [ 'javascript', 'python' ]

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v2
        with:
          languages: ${{ matrix.language }}
          # Optional: custom queries
          queries: security-and-quality

      - name: Autobuild
        uses: github/codeql-action/autobuild@v2

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v2
        with:
          category: "/language:${{matrix.language}}"
```

**Custom CodeQL queries**:
```yaml
# .github/workflows/codeql.yml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v2
  with:
    languages: javascript
    # Use custom query pack
    packs: owner/custom-queries
    # Or inline queries
    queries: |
      - uses: security-extended
      - uses: ./custom-queries/sql-injection.ql
```

**Custom query example** (custom-queries/sql-injection.ql):
```ql
/**
 * @name SQL injection vulnerability
 * @description Detects SQL injection vulnerabilities
 * @kind path-problem
 * @problem.severity error
 * @id js/sql-injection
 */

import javascript

from DataFlow::Node source, DataFlow::Node sink
where
  source.asExpr() instanceof UserInput and
  sink.asExpr() instanceof SqlQuery and
  DataFlow::flowPath(source, sink)
select sink, "Potential SQL injection from $@.", source, "user input"
```

### Secret Scanning

**Enable secret scanning** (repository settings):
1. Settings → Code security and analysis
2. Enable "Secret scanning"
3. Enable "Push protection" (prevents commits with secrets)

**Configure custom patterns** (.github/secret_scanning.yml):
```yaml
# Custom secret patterns
patterns:
  - name: Internal API Key
    regex: '(?i)api[_-]?key[_-]?([a-z0-9]{32})'

  - name: Database Connection String
    regex: '(?i)(postgres|mysql|mongodb):\/\/[^:]+:[^@]+@[^\/]+'

  - name: Private Key
    regex: '-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----'
```

**Handling secret alerts**:
```bash
# View secret scanning alerts
gh api /repos/owner/repo/secret-scanning/alerts

# Close alert (false positive)
gh api /repos/owner/repo/secret-scanning/alerts/1 \
  --method PATCH \
  --field state=resolved \
  --field resolution=false_positive

# Close alert (revoked)
gh api /repos/owner/repo/secret-scanning/alerts/1 \
  --method PATCH \
  --field state=resolved \
  --field resolution=revoked
```

**Response workflow**:
```
Secret Detected
  ↓
1. Revoke compromised credential
2. Remove from git history (git filter-repo or BFG)
3. Update secret in secure location (GitHub Secrets)
4. Close alert as "revoked"
5. Review access logs for unauthorized use
```

### SBOM (Software Bill of Materials)

**Generate SBOM**:
```bash
# Export SBOM for repository
gh api /repos/owner/repo/dependency-graph/sbom \
  --header "Accept: application/vnd.github+json" \
  > sbom.json

# SBOM includes:
# - Direct dependencies
# - Transitive dependencies
# - License information
# - Vulnerability data
```

**SBOM formats**:
- **SPDX**: ISO/IEC 5962:2021 standard
- **CycloneDX**: OWASP standard for security-focused SBOM

**Use cases**:
- License compliance auditing
- Supply chain security
- Vulnerability tracking
- Regulatory compliance (NIST, EO 14028)

**Automate SBOM generation** (.github/workflows/sbom.yml):
```yaml
name: Generate SBOM
on:
  release:
    types: [published]

jobs:
  sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate SBOM
        run: |
          gh api /repos/${{ github.repository }}/dependency-graph/sbom \
            --header "Accept: application/vnd.github+json" \
            > sbom-${{ github.event.release.tag_name }}.json
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload SBOM to release
        run: |
          gh release upload ${{ github.event.release.tag_name }} \
            sbom-${{ github.event.release.tag_name }}.json
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Security Advisories

**Create private security advisory**:
```bash
# Via web UI:
# Security tab → Advisories → New draft security advisory

# Fill in:
# - Title: Brief description of vulnerability
# - CVE ID: Request CVE if needed
# - Ecosystem: npm, pip, rubygems, etc.
# - Package name: Affected package
# - Affected versions: Version range
# - Patched versions: Fixed versions
# - Severity: Low, Medium, High, Critical
# - CWE: Common Weakness Enumeration
# - Description: Detailed description
# - References: Links to related information
```

**Coordinated disclosure workflow**:
```
1. Create draft advisory (private)
   ↓
2. Add collaborators (security researchers, maintainers)
   ↓
3. Develop fix in temporary private fork
   ↓
4. Test and verify fix
   ↓
5. Publish advisory and release fix simultaneously
   ↓
6. Request CVE assignment
   ↓
7. Notify users via GitHub, email, social media
```

**Example advisory template**:
```markdown
# SQL Injection in User Authentication

## Impact
Authenticated users can execute arbitrary SQL queries through the login endpoint.

## Patches
Fixed in version 2.1.5. Users should upgrade immediately.

## Workarounds
Disable user login functionality until upgrade is possible.

## References
- Fix: https://github.com/owner/repo/pull/123
- Advisory: GHSA-xxxx-xxxx-xxxx
- CVE: CVE-2025-12345

## Credits
Thanks to @security-researcher for responsible disclosure.
```

### SECURITY.md Policy

**Security policy file** (SECURITY.md):
```markdown
# Security Policy

## Supported Versions

We currently support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 2.1.x   | :white_check_mark: |
| 2.0.x   | :white_check_mark: |
| 1.9.x   | :x:                |
| < 1.9   | :x:                |

## Reporting a Vulnerability

**DO NOT** open a public issue for security vulnerabilities.

Instead, please report security vulnerabilities by:

1. Using GitHub's private vulnerability reporting:
   - Go to the Security tab
   - Click "Report a vulnerability"
   - Fill out the advisory form

2. Or email security@example.com with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Response time**: Within 48 hours
- **Update frequency**: Weekly until resolved
- **Disclosure timeline**: 90 days or when patched (whichever comes first)

### Security Update Process

1. We acknowledge receipt within 48 hours
2. We investigate and verify the vulnerability
3. We develop and test a fix
4. We release a patch version
5. We publish a security advisory
6. We notify affected users

## Security Best Practices

When using this project:

- Keep dependencies up to date
- Enable Dependabot security updates
- Use environment variables for secrets
- Enable two-factor authentication
- Review security advisories regularly
- Follow least privilege principle

## Bug Bounty Program

We currently do not have a bug bounty program, but we acknowledge and credit all security researchers who responsibly disclose vulnerabilities.

## Hall of Fame

Thanks to these security researchers:
- @researcher1 - SQL injection (2024-03)
- @researcher2 - XSS vulnerability (2024-05)
```

---

## Quick Reference

### Dependabot Commands

```bash
# Trigger Dependabot update
@dependabot rebase                # Rebase PR
@dependabot recreate              # Recreate PR
@dependabot merge                 # Merge PR
@dependabot squash and merge      # Squash and merge
@dependabot cancel merge          # Cancel auto-merge
@dependabot close                 # Close PR
@dependabot reopen                # Reopen PR
@dependabot ignore this dependency  # Ignore this dependency
@dependabot ignore this major version  # Ignore major version
```

### Security Severity Levels

```
Critical: Immediate action required
  - Remote code execution
  - SQL injection
  - Authentication bypass

High: Address within days
  - XSS vulnerabilities
  - Privilege escalation
  - Data exposure

Medium: Address within weeks
  - CSRF vulnerabilities
  - Information disclosure
  - DoS vulnerabilities

Low: Address when convenient
  - Minor information leaks
  - Best practice violations
```

### Security Checklist

```
✅ DO: Enable Dependabot alerts and updates
✅ DO: Configure code scanning with CodeQL
✅ DO: Enable secret scanning and push protection
✅ DO: Create SECURITY.md policy
✅ DO: Generate SBOM for releases
✅ DO: Respond to security advisories within 48 hours
✅ DO: Auto-merge security updates (patch/minor)
✅ DO: Require signed commits for production

❌ DON'T: Commit secrets to repository
❌ DON'T: Ignore security alerts
❌ DON'T: Disable security features
❌ DON'T: Public disclosure before patch available
❌ DON'T: Use outdated dependencies
```

---

## Anti-Patterns

### ❌ Ignoring Dependabot Alerts

```bash
# WRONG: 50 open Dependabot alerts, all ignored
# Some critical vulnerabilities months old
```

**Problems**:
- Exposed to known vulnerabilities
- Attackers target known CVEs
- Accumulating technical debt
- Regulatory compliance issues

```bash
# CORRECT: Triage and address alerts
# 1. Review new alerts weekly
# 2. Prioritize by severity (Critical > High > Medium > Low)
# 3. Test and merge security updates
# 4. Dismiss false positives with explanation
# 5. Create issues for complex updates

# Enable auto-merge for patch updates
# Use Dependabot auto-merge workflow
```

### ❌ Committing Secrets

```bash
# WRONG: Hardcoded credentials in code
API_KEY = "sk-abc123xyz"
DATABASE_URL = "postgresql://user:password@host/db"

# Or in config files
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Problems**:
- Credentials exposed in git history
- Cannot easily rotate secrets
- Security breach if repository is public
- Compliance violations

```bash
# CORRECT: Use environment variables and secrets
# 1. Store secrets in GitHub Secrets
# Settings → Secrets and variables → Actions → New repository secret

# 2. Reference in workflows
env:
  API_KEY: ${{ secrets.API_KEY }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}

# 3. Use environment variables in code
import os
API_KEY = os.environ.get("API_KEY")

# 4. Enable push protection
# Settings → Code security → Push protection
```

### ❌ No Code Scanning

```bash
# WRONG: No automated security analysis
# Vulnerabilities only found in production
# No visibility into code quality issues
```

**Problems**:
- Security vulnerabilities reach production
- No early warning system
- Higher remediation costs
- Potential data breaches

```yaml
# CORRECT: Enable CodeQL scanning
# .github/workflows/codeql.yml
name: "CodeQL"
on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]
  schedule:
    - cron: '0 2 * * 1'  # Weekly

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v2
        with:
          languages: javascript, python
          queries: security-and-quality
      - uses: github/codeql-action/autobuild@v2
      - uses: github/codeql-action/analyze@v2
```

### ❌ No Security Policy

```bash
# WRONG: No SECURITY.md file
# Users don't know how to report vulnerabilities
# Public issues created for security bugs
```

**Problems**:
- Security issues disclosed publicly
- No coordinated disclosure process
- Vulnerabilities exploited before fix
- Damages reputation

```markdown
# CORRECT: Create SECURITY.md
# Located at repository root or .github/SECURITY.md

# Security Policy

## Reporting a Vulnerability
Please report security vulnerabilities privately:
- GitHub Security Advisories (preferred)
- Email: security@example.com

**DO NOT** open public issues for security vulnerabilities.

## Response Timeline
- Acknowledgment: Within 48 hours
- Status updates: Weekly
- Disclosure: 90 days or when patched

## Supported Versions
| Version | Supported |
|---------|-----------|
| 2.x     | ✓         |
| 1.x     | ✗         |
```

### ❌ Manual Dependency Updates

```bash
# WRONG: Manually updating dependencies
# Updates happen sporadically
# Security patches delayed
# High maintenance burden
```

**Problems**:
- Slow response to vulnerabilities
- Inconsistent update cadence
- Human error (missed updates)
- Wastes developer time

```yaml
# CORRECT: Automate with Dependabot
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    groups:
      security-updates:
        applies-to: "security-updates"
```

---

## Related Skills

- `collaboration/github/github-actions-workflows.md` - Automating security workflows
- `collaboration/github/github-repository-management.md` - Repository security settings
- `cicd/ci-security.md` - Secret management in CI/CD
- `security/vulnerability-management.md` - Vulnerability response processes
- `security/secure-coding-practices.md` - Preventing security issues in code

---

**Last Updated**: 2025-10-25

**Format Version**: 1.0 (Atomic)
