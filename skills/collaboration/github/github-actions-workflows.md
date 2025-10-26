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

**Last Updated**: 2025-10-18

**Format Version**: 1.0 (Atomic)
