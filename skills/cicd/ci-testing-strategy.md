---
name: cicd-ci-testing-strategy
description: Designing test execution strategies for CI pipelines
---



# CI Testing Strategy

**Scope**: Test stages, parallel execution, test splitting, flaky test handling, and test result reporting in CI pipelines

**Lines**: 365

**Last Updated**: 2025-10-18

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Use this skill when:
- Designing test execution strategies for CI pipelines
- Implementing test stages (unit, integration, e2e)
- Parallelizing tests for faster feedback
- Handling flaky tests and test retries
- Setting up test result reporting and analysis
- Implementing test splitting across multiple runners
- Optimizing test execution order for faster failure detection
- Managing test data and fixtures in CI

Don't use this skill for:
- Workflow syntax and configuration (see `github-actions-workflows.md`)
- Deployment strategies (see `cd-deployment-patterns.md`)
- General pipeline optimization (see `ci-optimization.md`)

---

## Core Concepts

### Test Pyramid in CI

```
        /\
       /E2E\     ← Slow, few, high-value
      /──────\
     / Integ  \   ← Medium speed, moderate count
    /──────────\
   /   Unit     \ ← Fast, many, isolated
  /──────────────\
```

### Test Stages

1. **Unit Tests**: Fast, isolated, no external dependencies
2. **Integration Tests**: Test interactions between components
3. **E2E Tests**: Full application flow, slowest but highest confidence
4. **Security Tests**: SAST, dependency scanning
5. **Performance Tests**: Load testing, benchmarks

### Execution Strategy

```
Fast Feedback Loop:
  Lint → Unit Tests → Build → Integration Tests → E2E Tests
  ↓ Fail fast at each stage
  Stop pipeline on failure (unless configured otherwise)
```

---

## Patterns

### Multi-Stage Testing

```yaml
name: Test Pipeline

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint

  unit-tests:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:unit
      - uses: codecov/codecov-action@v4
        with:
          files: ./coverage/coverage-final.json

  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:integration
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test

  e2e-tests:
    needs: integration-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run test:e2e
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-screenshots
          path: test-results/
```

### Parallel Test Execution

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        # Split tests across 4 runners
        shard: [1, 2, 3, 4]
      fail-fast: false

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci

      # Playwright test sharding
      - run: npx playwright test --shard=${{ matrix.shard }}/4

      # Jest test sharding
      - run: npm test -- --shard=${{ matrix.shard }}/4

      # Upload results
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results-${{ matrix.shard }}
          path: test-results/
```

### Test Splitting by Type

```yaml
jobs:
  test-unit:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, api, ui, utils]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test -- packages/${{ matrix.package }}

  test-browser:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        browser: [chromium, firefox, webkit]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npx playwright install --with-deps ${{ matrix.browser }}
      - run: npx playwright test --project=${{ matrix.browser }}
```

### Flaky Test Handling

```yaml
jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci

      # Retry failed tests automatically
      - name: Run tests with retry
        run: npm test -- --retries=2

      # Playwright retry configuration
      - name: Run E2E tests
        run: npx playwright test
        env:
          PLAYWRIGHT_RETRIES: 2

      # Custom retry script
      - name: Run tests with custom retry
        run: |
          for i in {1..3}; do
            npm test && break || {
              echo "Attempt $i failed"
              sleep 5
            }
          done

      # Quarantine flaky tests
      - name: Run stable tests
        run: npm test -- --testPathIgnorePatterns=flaky

      - name: Run flaky tests (non-blocking)
        run: npm test -- --testPathPattern=flaky
        continue-on-error: true
```

### Test Result Reporting

```yaml
jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci

      # Generate test reports
      - name: Run tests
        run: npm test -- --coverage --reporters=default --reporters=jest-junit
        env:
          JEST_JUNIT_OUTPUT_DIR: ./test-results

      # Publish test results
      - name: Publish test results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: test-results/*.xml

      # Code coverage
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage/coverage-final.json
          fail_ci_if_error: true

      # Comment PR with coverage
      - name: Coverage comment
        uses: romeovs/lcov-reporter-action@v0.3.1
        if: github.event_name == 'pull_request'
        with:
          lcov-file: ./coverage/lcov.info
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

### Test Data Management

```yaml
jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Cache test fixtures
      - name: Cache test data
        uses: actions/cache@v4
        with:
          path: test/fixtures/
          key: test-fixtures-${{ hashFiles('scripts/generate-fixtures.sh') }}

      # Generate test data if not cached
      - name: Generate test fixtures
        run: |
          if [ ! -d "test/fixtures" ]; then
            ./scripts/generate-fixtures.sh
          fi

      # Database seeding
      - name: Setup test database
        run: |
          npm run db:migrate
          npm run db:seed:test

      - run: npm test

      # Cleanup
      - name: Cleanup test data
        if: always()
        run: npm run db:reset
```

### Performance Testing

```yaml
jobs:
  benchmark:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci

      # Run benchmarks
      - name: Run benchmarks
        run: npm run bench

      # Compare with baseline
      - name: Store benchmark result
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'benchmarkjs'
          output-file-path: bench-results.json
          github-token: ${{ secrets.GITHUB_TOKEN }}
          auto-push: true
          alert-threshold: '150%'
          comment-on-alert: true
          fail-on-alert: true
```

### Contract Testing

```yaml
jobs:
  contract-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci

      # Provider verification (API)
      - name: Run Pact provider tests
        run: npm run test:pact:provider
        env:
          PACT_BROKER_URL: ${{ secrets.PACT_BROKER_URL }}
          PACT_BROKER_TOKEN: ${{ secrets.PACT_BROKER_TOKEN }}

      # Consumer verification (Client)
      - name: Run Pact consumer tests
        run: npm run test:pact:consumer

      # Publish contracts
      - name: Publish Pact contracts
        if: github.ref == 'refs/heads/main'
        run: npm run pact:publish
```

### Visual Regression Testing

```yaml
jobs:
  visual-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci

      # Chromatic visual testing
      - name: Run visual tests
        uses: chromaui/action@v1
        with:
          projectToken: ${{ secrets.CHROMATIC_PROJECT_TOKEN }}
          exitZeroOnChanges: false
          exitOnceUploaded: true

      # Percy visual testing
      - name: Percy visual tests
        run: npx percy exec -- npm run test:visual
        env:
          PERCY_TOKEN: ${{ secrets.PERCY_TOKEN }}
```

### Conditional Test Execution

```yaml
jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      # Detect changed files
      - name: Get changed files
        id: changed-files
        uses: tj-actions/changed-files@v40
        with:
          files: |
            src/**
            tests/**

      # Run tests only if relevant files changed
      - name: Run tests
        if: steps.changed-files.outputs.any_changed == 'true'
        run: npm test

      # Run specific tests based on changes
      - name: Run API tests
        if: contains(steps.changed-files.outputs.modified_files, 'src/api/')
        run: npm run test:api

      # Always run critical tests
      - name: Run smoke tests
        run: npm run test:smoke
```

---

## Quick Reference

### Test Execution Order

```yaml
1. Lint/Format       # Fastest, catches syntax errors
2. Unit Tests        # Fast, isolated
3. Integration Tests # Medium, external deps
4. E2E Tests         # Slow, full stack
5. Performance Tests # Slowest, resource-intensive
```

### Test Parallelization Strategies

```yaml
By Shard:        --shard=1/4
By Package:      packages/${{ matrix.package }}
By Browser:      --project=${{ matrix.browser }}
By Test Suite:   --testPathPattern=${{ matrix.suite }}
```

### Common Test Runners

```bash
# Jest
npm test -- --coverage --shard=1/4

# Playwright
npx playwright test --shard=1/4 --project=chromium

# Pytest
pytest --numprocesses=4 --dist=loadscope

# Go
go test -parallel=4 ./...

# Rust
cargo test --jobs=4
```

### Coverage Thresholds

```json
{
  "coverageThreshold": {
    "global": {
      "branches": 80,
      "functions": 80,
      "lines": 80,
      "statements": 80
    }
  }
}
```

---

## Anti-Patterns

### ❌ Running All Tests Sequentially

```yaml
# WRONG: Sequential execution
- run: npm run test:unit
- run: npm run test:integration
- run: npm run test:e2e
```

```yaml
# CORRECT: Parallel jobs
jobs:
  test-unit:
    steps: [...]
  test-integration:
    steps: [...]
  test-e2e:
    needs: [test-unit, test-integration]
    steps: [...]
```

### ❌ No Test Isolation

```yaml
# WRONG: Tests share state
- run: npm test
  env:
    DB_NAME: shared_test_db
```

```yaml
# CORRECT: Isolated databases per runner
- run: npm test
  env:
    DB_NAME: test_db_${{ github.run_id }}_${{ matrix.shard }}
```

### ❌ Ignoring Flaky Tests

```yaml
# WRONG: Hide failures
- run: npm test || true
```

```yaml
# CORRECT: Track and fix flaky tests
- run: npm test -- --retries=2
- run: npm run test:flaky
  continue-on-error: true
  # File issue for flaky tests
```

### ❌ No Coverage Enforcement

```yaml
# WRONG: No coverage check
- run: npm test
```

```yaml
# CORRECT: Enforce coverage thresholds
- run: npm test -- --coverage
- run: |
    if [ $(cat coverage/coverage-summary.json | jq '.total.lines.pct') -lt 80 ]; then
      echo "Coverage below 80%"
      exit 1
    fi
```

### ❌ Slow E2E Tests on Every Commit

```yaml
# WRONG: Full E2E suite on every push
on: [push]
jobs:
  e2e:
    steps: [run all 500 E2E tests]
```

```yaml
# CORRECT: Smoke tests on push, full suite on main
jobs:
  e2e-smoke:
    if: github.ref != 'refs/heads/main'
    steps: [run critical E2E tests]

  e2e-full:
    if: github.ref == 'refs/heads/main'
    steps: [run all E2E tests]
```

### ❌ Not Retaining Test Artifacts

```yaml
# WRONG: No artifacts on failure
- run: npx playwright test
```

```yaml
# CORRECT: Upload screenshots/videos on failure
- run: npx playwright test
- uses: actions/upload-artifact@v4
  if: failure()
  with:
    name: test-artifacts
    path: |
      test-results/
      screenshots/
      videos/
```

---

## Related Skills

- `github-actions-workflows.md` - Workflow configuration and syntax
- `ci-optimization.md` - Pipeline speed and efficiency
- `cd-deployment-patterns.md` - Post-test deployment strategies
- `ci-security.md` - Security testing and scanning

---

**Last Updated**: 2025-10-18

**Format Version**: 1.0 (Atomic)
