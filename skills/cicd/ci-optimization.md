---
name: cicd-ci-optimization
description: CI pipelines are taking too long (>10 minutes for feedback)
---



# CI Optimization

**Scope**: Pipeline speed optimization, caching strategies, parallelization, incremental builds, and resource efficiency

**Lines**: 370

**Last Updated**: 2025-10-18

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Use this skill when:
- CI pipelines are taking too long (>10 minutes for feedback)
- Optimizing build times and test execution
- Reducing CI costs and resource usage
- Implementing efficient caching strategies
- Parallelizing independent tasks
- Setting up incremental builds
- Optimizing Docker image builds
- Reducing dependency installation time

Don't use this skill for:
- Basic workflow configuration (see `github-actions-workflows.md`)
- Testing strategies (see `ci-testing-strategy.md`)
- Deployment patterns (see `cd-deployment-patterns.md`)

---

## Core Concepts

### Optimization Hierarchy

```
1. Eliminate unnecessary work    ← Biggest impact
2. Parallelize independent tasks
3. Cache expensive operations
4. Optimize hot paths
5. Tune resource allocation      ← Smallest impact
```

### Pipeline Stages by Cost

```
Stage              | Time  | Cost | Optimization Priority
───────────────────|───────|──────|──────────────────────
Lint               | 10s   | $    | ★
Unit Tests         | 1m    | $    | ★★
Build              | 3m    | $$   | ★★★★
Integration Tests  | 5m    | $$$  | ★★★★★
E2E Tests          | 15m   | $$$$ | ★★★★★
Deployment         | 2m    | $$   | ★★
```

### Feedback Loop Target

```
Critical: < 5 minutes  (lint + unit tests)
Standard: < 10 minutes (+ build + integration)
Extended: < 30 minutes (+ E2E tests)
```

---

## Patterns

### Dependency Caching Strategies

```yaml
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Node.js - automatic caching
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci

      # Python - uv with caching
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Cache uv
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: ${{ runner.os }}-uv-${{ hashFiles('**/pyproject.toml') }}
      - run: uv sync

      # Rust - cargo caching
      - uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/bin/
            ~/.cargo/registry/index/
            ~/.cargo/registry/cache/
            ~/.cargo/git/db/
            target/
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}
          restore-keys: |
            ${{ runner.os }}-cargo-

      # Go - module caching
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true
      - run: go build ./...

      # Gradle - build caching
      - uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'gradle'
      - run: ./gradlew build
```

### Docker Layer Caching

```yaml
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Docker buildx with cache
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and cache
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          cache-from: type=gha
          cache-to: type=gha,mode=max
          tags: myapp:${{ github.sha }}

      # Multi-stage build optimization
      - name: Build with optimized Dockerfile
        run: docker build -t myapp:${{ github.sha }} .
```

**Optimized Dockerfile:**
```dockerfile
# Use specific versions for reproducibility
FROM node:20-alpine AS deps
WORKDIR /app

# Copy only dependency files first (best caching)
COPY package.json package-lock.json ./
RUN npm ci --only=production

# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage (smallest image)
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY package.json ./

CMD ["node", "dist/index.js"]
```

### Parallel Job Execution

```yaml
jobs:
  # Fast feedback jobs run in parallel
  lint:
    runs-on: ubuntu-latest
    steps: [...]

  type-check:
    runs-on: ubuntu-latest
    steps: [...]

  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - run: npm test -- --shard=${{ matrix.shard }}/4

  # Dependent jobs only after fast checks pass
  build:
    needs: [lint, type-check, unit-tests]
    runs-on: ubuntu-latest
    steps: [...]

  integration-tests:
    needs: build
    runs-on: ubuntu-latest
    strategy:
      matrix:
        suite: [api, database, external]
    steps:
      - run: npm run test:${{ matrix.suite }}
```

### Incremental Builds

```yaml
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for change detection

      # Detect changed files
      - name: Get changed files
        id: changed
        run: |
          if git rev-parse HEAD^ >/dev/null 2>&1; then
            echo "files=$(git diff --name-only HEAD^ HEAD | tr '\n' ' ')" >> $GITHUB_OUTPUT
          else
            echo "files=all" >> $GITHUB_OUTPUT
          fi

      # Skip build if only docs changed
      - name: Skip build check
        id: skip
        run: |
          if [[ "${{ steps.changed.outputs.files }}" =~ ^(README|docs/).* ]]; then
            echo "skip=true" >> $GITHUB_OUTPUT
          else
            echo "skip=false" >> $GITHUB_OUTPUT
          fi

      # Build only changed packages (monorepo)
      - name: Build changed packages
        if: steps.skip.outputs.skip == 'false'
        run: |
          npx lerna run build --since HEAD^ --include-dependencies

      # Turborepo incremental builds
      - name: Turborepo cache
        uses: actions/cache@v4
        with:
          path: .turbo
          key: ${{ runner.os }}-turbo-${{ github.sha }}
          restore-keys: |
            ${{ runner.os }}-turbo-

      - name: Build with Turborepo
        run: npx turbo run build --cache-dir=.turbo
```

### Conditional Job Execution

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
      docs: ${{ steps.filter.outputs.docs }}

    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            backend:
              - 'src/backend/**'
              - 'package.json'
            frontend:
              - 'src/frontend/**'
              - 'package.json'
            docs:
              - 'docs/**'
              - '*.md'

  test-backend:
    needs: changes
    if: needs.changes.outputs.backend == 'true'
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:backend

  test-frontend:
    needs: changes
    if: needs.changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:frontend

  deploy-docs:
    needs: changes
    if: needs.changes.outputs.docs == 'true'
    runs-on: ubuntu-latest
    steps:
      - run: npm run deploy:docs
```

### Optimized Test Execution

```yaml
jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Cache test fixtures
      - name: Cache test fixtures
        uses: actions/cache@v4
        with:
          path: test/fixtures
          key: fixtures-${{ hashFiles('scripts/generate-fixtures.sh') }}

      # Run only affected tests
      - name: Run affected tests
        run: |
          npm test -- --onlyChanged --changedSince=origin/main

      # Fail fast - run fast tests first
      - name: Run fast unit tests
        run: npm test -- --testPathPattern=unit --maxWorkers=4

      - name: Run slow integration tests
        if: success()
        run: npm test -- --testPathPattern=integration --maxWorkers=2

      # Test sharding for parallelization
      - name: Run tests with sharding
        run: npm test -- --shard=${{ matrix.shard }}/4 --maxWorkers=50%
```

### Resource Optimization

```yaml
jobs:
  build:
    runs-on: ubuntu-latest-8-cores  # Use larger runner for compute-heavy tasks

    steps:
      - uses: actions/checkout@v4

      # Optimize compilation with ccache
      - name: Setup ccache
        uses: hendrikmuhs/ccache-action@v1.2
        with:
          key: ${{ runner.os }}-ccache-${{ github.sha }}

      # Parallel compilation
      - name: Build with parallel jobs
        run: |
          export MAKEFLAGS="-j$(nproc)"
          make all

      # Optimize Node.js memory
      - name: Build with increased memory
        run: NODE_OPTIONS="--max-old-space-size=4096" npm run build

      # Rust release build optimization
      - name: Cargo build
        run: |
          # Use all CPU cores
          cargo build --release -j $(nproc)
        env:
          CARGO_INCREMENTAL: 1
```

### Matrix Strategy Optimization

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        # Test critical combinations first
        include:
          # Tier 1: Most common (fail fast)
          - os: ubuntu-latest
            node: 20
            priority: 1
          - os: ubuntu-latest
            node: 22
            priority: 1

          # Tier 2: Important but less common
          - os: macos-latest
            node: 20
            priority: 2
          - os: windows-latest
            node: 20
            priority: 2

      # Run tier 1 first
      fail-fast: true
      max-parallel: 4

    steps:
      - uses: actions/checkout@v4

      # Skip expensive setup for quick tests
      - name: Quick validation
        if: github.event_name == 'pull_request'
        run: npm run lint && npm run test:unit

      # Full test suite for main branch
      - name: Full test suite
        if: github.ref == 'refs/heads/main'
        run: npm test
```

### Artifact Optimization

```yaml
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - run: npm run build

      # Upload only necessary artifacts
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 1  # Short retention for CI artifacts
          compression-level: 9  # Maximum compression

      # Exclude unnecessary files
      - uses: actions/upload-artifact@v4
        with:
          name: build-logs
          path: |
            logs/
            !logs/*.debug
            !logs/temp/

  test:
    needs: build
    runs-on: ubuntu-latest

    steps:
      # Download only needed artifacts
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - run: npm test
```

### Remote Caching (Turborepo)

```yaml
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Turborepo remote caching
      - name: Setup Turborepo cache
        run: |
          echo "TURBO_TOKEN=${{ secrets.TURBO_TOKEN }}" >> $GITHUB_ENV
          echo "TURBO_TEAM=${{ secrets.TURBO_TEAM }}" >> $GITHUB_ENV

      - name: Build with remote cache
        run: |
          npx turbo run build test --cache-dir=.turbo

      # Results cached across runs and branches
```

### Workflow Reuse for Common Tasks

```yaml
# .github/workflows/reusable-test.yml
name: Reusable Test

on:
  workflow_call:
    inputs:
      node-version:
        type: string
        default: '20'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: npm test
```

**Usage:**
```yaml
# .github/workflows/ci.yml
jobs:
  test-node-20:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'

  test-node-22:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '22'
```

---

## Quick Reference

### Cache Key Patterns

```yaml
# Dependencies
key: ${{ runner.os }}-deps-${{ hashFiles('**/package-lock.json') }}

# Build artifacts
key: ${{ runner.os }}-build-${{ github.sha }}

# Test fixtures
key: fixtures-${{ hashFiles('scripts/generate-fixtures.sh') }}

# With restore keys
key: ${{ runner.os }}-cache-${{ github.sha }}
restore-keys: |
  ${{ runner.os }}-cache-
  ${{ runner.os }}-
```

### Runner Selection

```yaml
# Standard (2-core)
runs-on: ubuntu-latest

# Larger runners (8-core, 16-core)
runs-on: ubuntu-latest-8-cores

# GPU runners
runs-on: [self-hosted, gpu]

# ARM runners
runs-on: [self-hosted, ARM64]
```

### Time-to-Feedback Targets

```yaml
Lint:            < 30s
Unit Tests:      < 2m
Build:           < 3m
Integration:     < 5m
Total Feedback:  < 10m
```

### Optimization Checklist

```yaml
[ ] Dependencies cached
[ ] Docker layers optimized
[ ] Tests parallelized
[ ] Artifacts minimized
[ ] Conditional execution enabled
[ ] Incremental builds configured
[ ] Fast tests run first
[ ] Appropriate runner size
```

---

## Anti-Patterns

### ❌ No Caching

```yaml
# WRONG: Install every time
- run: npm install
```

```yaml
# CORRECT: Cache dependencies
- uses: actions/setup-node@v4
  with:
    cache: 'npm'
- run: npm ci
```

### ❌ Sequential When Parallel is Possible

```yaml
# WRONG: Sequential jobs
jobs:
  test-unit:
    steps: [...]
  test-integration:
    needs: test-unit
    steps: [...]
```

```yaml
# CORRECT: Parallel independent jobs
jobs:
  test-unit:
    steps: [...]
  test-integration:
    steps: [...]
```

### ❌ Full Rebuild Every Time

```yaml
# WRONG: Clean build (inefficient - defeats caching)
- run: rm -rf dist node_modules
- run: npm install
- run: npm run build
```

```yaml
# CORRECT: Incremental build
- uses: actions/cache@v4
  with:
    path: |
      node_modules
      .turbo
    key: ${{ runner.os }}-build-${{ hashFiles('**/package-lock.json') }}
- run: npm ci
- run: npx turbo build
```

### ❌ Inefficient Docker Layers

```dockerfile
# WRONG: Copy everything, then install
COPY . .
RUN npm install
```

```dockerfile
# CORRECT: Copy deps first, then code
COPY package*.json ./
RUN npm ci
COPY . .
```

### ❌ Running All Tests on Doc Changes

```yaml
# WRONG: Test everything
on: [push]
jobs:
  test:
    steps: [run all tests]
```

```yaml
# CORRECT: Conditional execution
jobs:
  changes:
    outputs:
      code: ${{ steps.filter.outputs.code }}
  test:
    needs: changes
    if: needs.changes.outputs.code == 'true'
    steps: [run tests]
```

### ❌ Not Using Fail-Fast

```yaml
# WRONG: Run all matrix jobs even if one fails
strategy:
  matrix:
    version: [18, 20, 22]
```

```yaml
# CORRECT: Fail fast for quick feedback
strategy:
  fail-fast: true
  matrix:
    version: [18, 20, 22]
```

---

## Related Skills

- `github-actions-workflows.md` - Workflow configuration basics
- `ci-testing-strategy.md` - Test execution optimization
- `cd-deployment-patterns.md` - Deployment optimization
- `ci-security.md` - Security scanning performance

---

**Last Updated**: 2025-10-18

**Format Version**: 1.0 (Atomic)
