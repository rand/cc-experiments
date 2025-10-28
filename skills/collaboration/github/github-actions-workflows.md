---
name: collaboration-github-actions-workflows
description: Setting up CI/CD pipelines with GitHub Actions
---



# GitHub Actions Workflows

**Scope**: Workflow syntax, triggers, jobs, steps, matrix builds, caching, and artifacts for GitHub Actions CI/CD pipelines

**Lines**: 380

**Last Updated**: 2025-10-18

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Use this skill when:
- Setting up CI/CD pipelines with GitHub Actions
- Configuring workflow triggers (push, pull_request, schedule, workflow_dispatch)
- Implementing matrix builds for multi-platform or multi-version testing
- Optimizing workflows with caching strategies
- Managing artifacts between jobs
- Setting up reusable workflows and composite actions
- Configuring job dependencies and conditions

Don't use this skill for:
- Platform-specific deployment configurations (see `cd-deployment-patterns.md`)
- Testing strategies and optimization (see `ci-testing-strategy.md` and `ci-optimization.md`)
- Security and secret management (see `ci-security.md`)

---

## Core Concepts

### Workflow Structure

```yaml
name: Workflow Name
on: [triggers]
env:
  GLOBAL_VAR: value
jobs:
  job-name:
    runs-on: ubuntu-latest
    steps:
      - name: Step name
        uses: actions/checkout@v4
```

### Key Components

1. **Triggers (on)**: Events that start workflows
2. **Jobs**: Independent execution units that can run in parallel
3. **Steps**: Sequential commands or actions within a job
4. **Runners**: Virtual machines that execute jobs
5. **Actions**: Reusable units of code (marketplace or custom)
6. **Contexts**: Variables available in expressions (${{ github.event.name }})

### Execution Model

```
Trigger Event
  ↓
Workflow Starts
  ↓
Jobs Run (Parallel by default)
  ↓
Each Job: Steps Execute Sequentially
  ↓
Workflow Completes
```

---

## Patterns

### Basic Workflow Structure

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  NODE_VERSION: '20'

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build
```

### Advanced Triggers

```yaml
on:
  # Multiple events
  push:
    branches:
      - main
      - 'releases/**'
    paths:
      - 'src/**'
      - '!src/docs/**'

  pull_request:
    types: [opened, synchronize, reopened]

  # Scheduled runs (cron)
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

  # Manual trigger with inputs
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        type: choice
        options:
          - staging
          - production
      dry_run:
        description: 'Run in dry-run mode'
        required: false
        type: boolean
        default: false

  # Trigger from other workflows
  workflow_call:
    inputs:
      config-path:
        required: true
        type: string
```

### Matrix Builds

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node: [18, 20, 22]
        exclude:
          # Don't test Node 18 on Windows
          - os: windows-latest
            node: 18
        include:
          # Add experimental combinations
          - os: ubuntu-latest
            node: 23
            experimental: true

      # Continue other jobs even if one fails
      fail-fast: false

      # Limit concurrent jobs
      max-parallel: 4

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js ${{ matrix.node }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}

      - name: Run tests
        run: npm test
        continue-on-error: ${{ matrix.experimental || false }}
```

### Job Dependencies

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: npm run build

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: npm test

  deploy-staging:
    needs: [build, test]
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh staging

  deploy-prod:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh production
```

### Caching Dependencies

```yaml
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Node.js with automatic caching
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      # Manual cache for custom paths
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.npm
            node_modules
          key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
          restore-keys: |
            ${{ runner.os }}-node-

      # Python with pip cache
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      # Rust with cargo cache
      - uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/bin/
            ~/.cargo/registry/index/
            ~/.cargo/registry/cache/
            ~/.cargo/git/db/
            target/
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}
```

### Artifacts

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build artifacts
        run: npm run build

      # Upload artifacts
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist-files
          path: dist/
          retention-days: 7
          if-no-files-found: error

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      # Download artifacts
      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist-files
          path: dist/

      - name: Run integration tests
        run: npm run test:integration
```

### Conditional Execution

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Step-level condition
      - name: Deploy to staging
        if: github.ref == 'refs/heads/develop'
        run: ./deploy.sh staging

      # Multiple conditions
      - name: Deploy to production
        if: |
          github.ref == 'refs/heads/main' &&
          github.event_name == 'push' &&
          !contains(github.event.head_commit.message, '[skip deploy]')
        run: ./deploy.sh production

      # Check previous step status
      - name: Notify on failure
        if: failure()
        run: ./notify-slack.sh "Deployment failed"

      # Always run (cleanup)
      - name: Cleanup
        if: always()
        run: ./cleanup.sh
```

### Reusable Workflows

**Caller workflow:**
```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-prod:
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
      region: us-east-1
    secrets:
      api-key: ${{ secrets.PROD_API_KEY }}
```

**Reusable workflow:**
```yaml
# .github/workflows/reusable-deploy.yml
name: Reusable Deploy

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
      region:
        required: true
        type: string
    secrets:
      api-key:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to ${{ inputs.environment }}
        env:
          API_KEY: ${{ secrets.api-key }}
          REGION: ${{ inputs.region }}
        run: ./deploy.sh
```

### Composite Actions

```yaml
# .github/actions/setup-node-app/action.yml
name: 'Setup Node.js Application'
description: 'Checkout, setup Node.js, install dependencies'

inputs:
  node-version:
    description: 'Node.js version'
    required: false
    default: '20'

runs:
  using: 'composite'
  steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'npm'

    - name: Install dependencies
      shell: bash
      run: npm ci
```

**Usage:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: ./.github/actions/setup-node-app
        with:
          node-version: '20'

      - run: npm run build
```

### Environment Variables and Contexts

```yaml
jobs:
  build:
    runs-on: ubuntu-latest

    env:
      # Job-level environment variable
      BUILD_ENV: production

    steps:
      - name: Print contexts
        env:
          # Step-level environment variable
          STEP_VAR: value
        run: |
          echo "Event: ${{ github.event_name }}"
          echo "Ref: ${{ github.ref }}"
          echo "SHA: ${{ github.sha }}"
          echo "Actor: ${{ github.actor }}"
          echo "Repository: ${{ github.repository }}"
          echo "Run ID: ${{ github.run_id }}"
          echo "Runner OS: ${{ runner.os }}"
          echo "Job status: ${{ job.status }}"
          echo "Build env: $BUILD_ENV"
          echo "Step var: $STEP_VAR"
```

---

## Quick Reference

### Common Triggers

```yaml
on:
  push:                    # Code pushed
  pull_request:           # PR opened/updated
  schedule:               # Cron schedule
  workflow_dispatch:      # Manual trigger
  release:                # Release created
  issue_comment:          # Comment on issue/PR
  workflow_call:          # Called from another workflow
```

### Runner Options

```yaml
runs-on: ubuntu-latest          # Linux (fastest, cheapest)
runs-on: macos-latest           # macOS
runs-on: windows-latest         # Windows
runs-on: [self-hosted, linux]   # Self-hosted runner
```

### Useful Actions

```yaml
actions/checkout@v4              # Clone repository
actions/setup-node@v4            # Setup Node.js
actions/setup-python@v5          # Setup Python
actions/cache@v4                 # Cache dependencies
actions/upload-artifact@v4       # Upload artifacts
actions/download-artifact@v4     # Download artifacts
github/codeql-action@v3          # Code scanning
```

### Context Variables

```yaml
${{ github.event_name }}         # Event that triggered workflow
${{ github.ref }}                # Branch or tag ref
${{ github.sha }}                # Commit SHA
${{ github.actor }}              # User who triggered
${{ runner.os }}                 # Runner OS (Linux, macOS, Windows)
${{ secrets.SECRET_NAME }}       # Access secrets
${{ env.VAR_NAME }}              # Environment variable
```

### Status Check Functions

```yaml
if: success()       # Previous steps succeeded (default)
if: failure()       # Previous step failed
if: always()        # Run regardless of status
if: cancelled()     # Workflow was cancelled
```

---

## Anti-Patterns

### ❌ Hardcoded Secrets

```yaml
# WRONG: Secrets in plain text
env:
  API_KEY: abc123xyz
  DATABASE_URL: postgresql://user:pass@host/db
```

```yaml
# CORRECT: Use GitHub Secrets
env:
  API_KEY: ${{ secrets.API_KEY }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### ❌ No Caching

```yaml
# WRONG: Install dependencies every time
- run: npm install
```

```yaml
# CORRECT: Cache dependencies
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
- run: npm ci
```

### ❌ Sequential Jobs (When Parallel is Possible)

```yaml
# WRONG: Sequential tests
jobs:
  test-unit:
    runs-on: ubuntu-latest
    steps: [...]

  test-integration:
    needs: test-unit
    runs-on: ubuntu-latest
    steps: [...]
```

```yaml
# CORRECT: Parallel tests
jobs:
  test-unit:
    runs-on: ubuntu-latest
    steps: [...]

  test-integration:
    runs-on: ubuntu-latest
    steps: [...]

  deploy:
    needs: [test-unit, test-integration]
    steps: [...]
```

### ❌ Using `npm install` Instead of `npm ci`

```yaml
# WRONG: Non-deterministic installs
- run: npm install
```

```yaml
# CORRECT: Reproducible installs
- run: npm ci
```

### ❌ Rebuilding Artifacts

```yaml
# WRONG: Build in multiple jobs
jobs:
  test:
    steps:
      - run: npm run build
      - run: npm test

  deploy:
    steps:
      - run: npm run build
      - run: ./deploy.sh
```

```yaml
# CORRECT: Build once, share artifacts
jobs:
  build:
    steps:
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  test:
    needs: build
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
      - run: npm test
```

### ❌ No Matrix for Multi-Platform

```yaml
# WRONG: Separate jobs for each platform
jobs:
  test-ubuntu:
    runs-on: ubuntu-latest
    steps: [...]

  test-macos:
    runs-on: macos-latest
    steps: [...]
```

```yaml
# CORRECT: Use matrix
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps: [...]
```

---

## Related Skills

- `collaboration/github/github-pull-requests.md` - PR workflow and code review integration with workflows
- `collaboration/github/github-security-features.md` - Security scanning and dependency management in Actions
- `collaboration/github/github-repository-management.md` - Repository settings and configuration
- `cicd/ci-testing-strategy.md` - Test execution patterns in CI
- `cicd/cd-deployment-patterns.md` - Deployment strategies and rollbacks
- `cicd/ci-optimization.md` - Speed and efficiency improvements
- `cicd/ci-security.md` - Secret management and security best practices

---

## Level 3: Resources

### Overview
Comprehensive resources for GitHub Actions CI/CD implementation including complete reference documentation, validation and optimization tools, and production-ready workflow examples.

### Resources Structure

#### REFERENCE.md (3,843 lines)
Complete GitHub Actions reference covering:
- **Fundamentals**: GitHub Actions architecture, workflow lifecycle, pricing/limits
- **Workflow Syntax**: Complete YAML syntax, triggers, permissions, concurrency
- **Triggers and Events**: All event types with examples (push, PR, schedule, workflow_dispatch)
- **Jobs and Steps**: Configuration, dependencies, conditions, service containers
- **Runners**: GitHub-hosted and self-hosted runners, environments
- **Contexts and Expressions**: All context objects, expression syntax, functions
- **Actions**: Using marketplace actions, creating composite actions
- **Caching Strategies**: Language-specific caching, Docker layer caching
- **Artifacts**: Upload/download patterns, release assets
- **Matrix Builds**: Multi-platform/version testing, exclusions, inclusions
- **Reusable Workflows**: Creation and usage patterns with inputs/outputs
- **Security**: OIDC authentication, permissions, secret management, pull_request_target safety
- **Performance Optimization**: Parallelization, path filters, concurrency control
- **Monorepo Strategies**: Path-based change detection, selective testing
- **Common Patterns**: Complete CI/CD pipelines, Docker builds, security scanning
- **Anti-Patterns**: Security, performance, and workflow anti-patterns with fixes
- **Debugging**: Enable debug logging, inspect contexts, troubleshoot common issues

Location: `./resources/REFERENCE.md`

#### Scripts

**validate_workflow.py** (576 lines)
Validates GitHub Actions workflow files for syntax, security, and best practices.

Features:
- Parse and validate YAML syntax
- Detect security issues (hardcoded secrets, dangerous pull_request_target usage)
- Check for outdated action versions
- Identify caching opportunities
- Validate permissions configuration
- Suggest best practices (concurrency control, npm ci vs npm install)
- JSON and human-readable output

Usage:
```bash
# Validate single workflow
./resources/scripts/validate_workflow.py .github/workflows/ci.yml

# Validate directory with JSON output
./resources/scripts/validate_workflow.py .github/workflows/ --json

# Recursive validation with fix suggestions
./resources/scripts/validate_workflow.py . --recursive --fix-suggestions
```

**optimize_pipeline.py** (669 lines)
Analyzes workflows and suggests optimizations for performance and cost.

Features:
- Identify parallelization opportunities
- Detect duplicate builds and artifact rebuilding
- Suggest caching improvements
- Find matrix build opportunities
- Calculate cost optimization potential
- Recommend performance enhancements (path filters, shallow checkouts)
- Estimate time and cost savings

Usage:
```bash
# Analyze single workflow
./resources/scripts/optimize_pipeline.py .github/workflows/ci.yml

# JSON output with implementation details
./resources/scripts/optimize_pipeline.py workflow.yml --json --suggestions
```

**test_actions.sh** (416 lines)
Tests GitHub Actions workflows locally using act (nektos/act).

Features:
- Run workflows locally with Docker
- Test different event triggers
- Measure execution time
- Validate workflow outputs
- List available workflows
- Support for dry-run mode
- JSON output for CI integration

Usage:
```bash
# Test workflow with push event
./resources/scripts/test_actions.sh --workflow ci.yml --event push

# Test specific job
./resources/scripts/test_actions.sh --workflow ci.yml --job build

# List all workflows
./resources/scripts/test_actions.sh --list

# Dry run
./resources/scripts/test_actions.sh --workflow ci.yml --dry-run
```

Dependencies:
- act: `brew install act` or `gh extension install nektos/gh-act`
- Docker (required by act)

#### Examples

**workflows/python-ci.yml**
Complete Python CI pipeline with:
- Lint and format checking (ruff, black, isort, mypy)
- Multi-version testing (Python 3.10, 3.11, 3.12)
- Service containers (PostgreSQL, Redis)
- Security scanning (Safety, Bandit)
- Build and distribution packaging
- Documentation build
- Coverage reporting with Codecov
- Status check job for branch protection

**workflows/nodejs-ci-cd.yml**
Full Node.js CI/CD pipeline with:
- Multi-stage pipeline (install, lint, test, build, docker, e2e)
- Multi-version testing (Node 18, 20, 22)
- Docker image build and push to GHCR
- E2E tests with Playwright
- Deployment to staging and production environments
- Artifact management and cleanup
- GitHub Packages integration

**workflows/monorepo-matrix.yml**
Monorepo CI with efficient change detection:
- Path-based change detection using dorny/paths-filter
- Matrix builds for multiple packages
- Conditional job execution (only run if package changed)
- Integration and E2E tests for affected services
- Parallel deployment of changed services
- Service containers for integration tests

**workflows/reusable-workflow.yml**
Reusable deployment workflow demonstrating:
- Workflow inputs and secrets
- Environment configuration
- Health checks and validation
- Deployment timing and outputs
- Rollback on failure
- Slack notifications
- Smoke tests after deployment

**actions/custom-action/action.yml**
Composite action for multi-language setup:
- Support for Node.js, Python, Go, Rust
- Automatic caching configuration
- Version detection and validation
- Custom install commands
- Timing and performance metrics
- GitHub step summary output

**workflows/security-scan.yml**
Security scanning workflow with:
- CodeQL analysis for multiple languages
- Dependency vulnerability scanning with Trivy
- Secrets detection with Gitleaks
- Docker image scanning
- SARIF upload to GitHub Security
- Scheduled weekly scans

**workflows/caching-strategy.yml**
Advanced caching patterns for:
- Multi-layer Node.js caching (npm + node_modules + build cache)
- Docker layer caching with GitHub Actions cache
- Rust incremental build caching
- Python pip and venv caching
- Monorepo selective caching

### Quick Start

1. **Validate existing workflows:**
```bash
./resources/scripts/validate_workflow.py .github/workflows/ --recursive
```

2. **Optimize pipeline:**
```bash
./resources/scripts/optimize_pipeline.py .github/workflows/ci.yml
```

3. **Test locally:**
```bash
./resources/scripts/test_actions.sh --workflow ci.yml --event push
```

4. **Use as template:**
Copy examples from `./resources/examples/workflows/` to your `.github/workflows/` directory.

5. **Create composite action:**
Copy and customize `./resources/examples/actions/custom-action/` to `.github/actions/`.

### Reference Links

- Complete documentation: [REFERENCE.md](./resources/REFERENCE.md)
- Official GitHub Actions docs: https://docs.github.com/en/actions
- Workflow syntax: https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions
- Actions Marketplace: https://github.com/marketplace?type=actions
- act tool: https://github.com/nektos/act

---

**Last Updated**: 2025-10-27

**Format Version**: 1.0 (Atomic)
