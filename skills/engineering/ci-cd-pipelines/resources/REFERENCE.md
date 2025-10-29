# CI/CD Pipelines - Comprehensive Reference

**Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: 3,847

This comprehensive reference covers complete CI/CD pipeline design, implementation, and optimization across all major platforms.

---

## Table of Contents

1. [Introduction](#introduction)
2. [CI/CD Fundamentals](#cicd-fundamentals)
3. [Pipeline Architecture Patterns](#pipeline-architecture-patterns)
4. [GitHub Actions Deep Dive](#github-actions-deep-dive)
5. [GitLab CI Deep Dive](#gitlab-ci-deep-dive)
6. [Jenkins Deep Dive](#jenkins-deep-dive)
7. [CircleCI Deep Dive](#circleci-deep-dive)
8. [Buildkite Deep Dive](#buildkite-deep-dive)
9. [Azure Pipelines Deep Dive](#azure-pipelines-deep-dive)
10. [Testing Strategies in Pipelines](#testing-strategies-in-pipelines)
11. [Security Scanning Integration](#security-scanning-integration)
12. [Artifact Management](#artifact-management)
13. [Secret Management](#secret-management)
14. [Deployment Automation](#deployment-automation)
15. [Pipeline as Code](#pipeline-as-code)
16. [Monitoring and Observability](#monitoring-and-observability)
17. [Performance Optimization](#performance-optimization)
18. [Multi-Environment Promotion](#multi-environment-promotion)
19. [DORA Metrics](#dora-metrics)
20. [Troubleshooting Guide](#troubleshooting-guide)

---

## Introduction

### What is CI/CD?

**Continuous Integration (CI)**: The practice of automatically building and testing code changes as they are committed to version control.

**Continuous Delivery (CD)**: Extending CI to automatically deploy every change to a staging environment after passing all tests.

**Continuous Deployment (CD)**: Taking CD further by automatically deploying every change that passes testing to production.

### Why CI/CD Matters

**Benefits**:
- **Faster time to market**: Automated pipelines reduce deployment time from days to minutes
- **Higher quality**: Automated testing catches bugs before production
- **Reduced risk**: Small, frequent deployments are easier to troubleshoot and rollback
- **Developer productivity**: Automation frees developers from manual tasks
- **Consistency**: Reproducible builds and deployments eliminate "works on my machine" issues
- **Feedback loops**: Fast failure detection enables rapid iteration

**Impact on Business**:
- Reduced mean time to recovery (MTTR)
- Increased deployment frequency
- Lower change failure rate
- Improved customer satisfaction through faster feature delivery

### Evolution of CI/CD

**Traditional (2000s)**:
- Manual builds and deployments
- Weekly or monthly releases
- Dedicated operations teams
- High failure rates
- Long feedback cycles

**Modern (2010s+)**:
- Automated pipelines
- Multiple deployments per day
- DevOps culture
- Infrastructure as code
- GitOps workflows
- Progressive delivery

**Current Trends (2020s)**:
- Platform engineering
- Internal developer platforms (IDPs)
- AI-assisted pipeline optimization
- Security-first pipelines (DevSecOps)
- Multi-cloud and hybrid deployments
- GitOps and declarative infrastructure

---

## CI/CD Fundamentals

### Core Pipeline Stages

#### 1. Source Stage
**Purpose**: Trigger pipeline on code changes

**Key Activities**:
- Monitor version control for changes
- Clone repository
- Checkout specific branch/commit
- Validate repository state

**Triggers**:
```yaml
# Push to branches
on:
  push:
    branches: [main, develop, 'feature/*']

# Pull requests
on:
  pull_request:
    types: [opened, synchronize, reopened]

# Manual dispatch
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options: [dev, staging, prod]

# Scheduled
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

# Tag creation
on:
  push:
    tags:
      - 'v*.*.*'
```

#### 2. Build Stage
**Purpose**: Compile code and generate artifacts

**Key Activities**:
- Install dependencies
- Compile source code
- Bundle assets
- Generate version metadata
- Create distributable artifacts

**Best Practices**:
```yaml
# Cache dependencies
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}

# Reproducible builds
- name: Build
  run: |
    export SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)
    npm run build

# Version tagging
- name: Generate version
  run: |
    VERSION="$(jq -r .version package.json)"
    GIT_SHA="${GITHUB_SHA::8}"
    BUILD_DATE="$(date -u +%Y%m%d)"
    echo "VERSION=v${VERSION}-${BUILD_DATE}-${GIT_SHA}" >> $GITHUB_ENV
```

**Artifact Generation**:
- Binaries (compiled executables)
- Container images
- Package archives (tar.gz, zip)
- Static assets
- Build metadata (version, commit, timestamp)
- Bill of Materials (SBOM)

#### 3. Test Stage
**Purpose**: Validate code quality and functionality

**Test Pyramid**:
```
       /\
      /E2E\       <- Few, slow, high-value (10%)
     /------\
    /Integr.\    <- Some, medium speed (20%)
   /----------\
  /   Unit     \ <- Many, fast, isolated (70%)
 /--------------\
```

**Unit Tests**:
```yaml
test-unit:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'
    - run: npm ci
    - run: npm run test:unit -- --coverage --maxWorkers=4

    # Upload coverage
    - uses: codecov/codecov-action@v3
      with:
        files: ./coverage/coverage-final.json
        flags: unit
        fail_ci_if_error: true
```

**Integration Tests**:
```yaml
test-integration:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:16
      env:
        POSTGRES_PASSWORD: test
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
    redis:
      image: redis:7
      options: >-
        --health-cmd "redis-cli ping"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  steps:
    - uses: actions/checkout@v4
    - run: npm ci
    - run: npm run test:integration
      env:
        DATABASE_URL: postgresql://postgres:test@postgres:5432/test
        REDIS_URL: redis://redis:6379
```

**E2E Tests**:
```yaml
test-e2e:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
    - run: npm ci
    - run: npx playwright install --with-deps

    # Start application
    - run: npm run start &
    - run: npx wait-on http://localhost:3000

    # Run tests
    - run: npm run test:e2e

    # Upload artifacts on failure
    - uses: actions/upload-artifact@v4
      if: failure()
      with:
        name: playwright-report
        path: playwright-report/
```

#### 4. Security Stage
**Purpose**: Identify vulnerabilities and security issues

**Security Scanning Types**:

**SAST (Static Application Security Testing)**:
```yaml
security-sast:
  runs-on: ubuntu-latest
  permissions:
    security-events: write
  steps:
    - uses: actions/checkout@v4

    # CodeQL
    - uses: github/codeql-action/init@v3
      with:
        languages: javascript, python
        queries: security-extended
    - uses: github/codeql-action/autobuild@v3
    - uses: github/codeql-action/analyze@v3

    # Semgrep
    - uses: returntocorp/semgrep-action@v1
      with:
        config: >-
          p/security-audit
          p/owasp-top-ten
```

**Dependency Scanning**:
```yaml
security-dependencies:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    # npm audit
    - run: npm audit --audit-level=high

    # Snyk
    - uses: snyk/actions/node@master
      env:
        SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
      with:
        args: --severity-threshold=high --fail-on=upgradable

    # Trivy for dependencies
    - uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
```

**Secret Scanning**:
```yaml
security-secrets:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full history for secret scanning

    # Gitleaks
    - uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

    # TruffleHog
    - name: TruffleHog scan
      uses: trufflesecurity/trufflehog@main
      with:
        path: ./
        base: main
        head: HEAD
```

**Container Scanning**:
```yaml
security-container:
  runs-on: ubuntu-latest
  needs: [build-image]
  steps:
    - name: Scan with Trivy
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: ${{ needs.build-image.outputs.image }}
        format: 'sarif'
        output: 'trivy-results.sarif'
        severity: 'CRITICAL,HIGH'
        exit-code: '1'

    - name: Scan with Grype
      uses: anchore/scan-action@v3
      with:
        image: ${{ needs.build-image.outputs.image }}
        fail-build: true
        severity-cutoff: high
```

#### 5. Package Stage
**Purpose**: Create deployable artifacts

**Container Images**:
```yaml
package-docker:
  runs-on: ubuntu-latest
  needs: [test-unit, test-integration, security-sast]
  outputs:
    image-tag: ${{ steps.meta.outputs.tags }}
    image-digest: ${{ steps.build.outputs.digest }}
  steps:
    - uses: actions/checkout@v4

    # Set up buildx for multi-platform builds
    - uses: docker/setup-buildx-action@v3

    # Login to registry
    - uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    # Generate metadata
    - id: meta
      uses: docker/metadata-action@v5
      with:
        images: ghcr.io/${{ github.repository }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}

    # Build and push
    - id: build
      uses: docker/build-push-action@v5
      with:
        context: .
        platforms: linux/amd64,linux/arm64
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        build-args: |
          VERSION=${{ env.VERSION }}
          COMMIT=${{ github.sha }}
          BUILD_DATE=${{ env.BUILD_DATE }}

    # Generate SBOM
    - uses: anchore/sbom-action@v0
      with:
        image: ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
        format: spdx-json
        output-file: sbom.spdx.json

    # Attest provenance
    - uses: actions/attest-build-provenance@v1
      with:
        subject-name: ghcr.io/${{ github.repository }}
        subject-digest: ${{ steps.build.outputs.digest }}
        push-to-registry: true
```

**Language-Specific Packaging**:

**Node.js/npm**:
```yaml
package-npm:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
        registry-url: 'https://registry.npmjs.org'

    - run: npm ci
    - run: npm run build
    - run: npm pack

    # Publish to npm
    - run: npm publish --access public
      env:
        NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

**Python/PyPI**:
```yaml
package-python:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'

    - run: pip install build twine
    - run: python -m build
    - run: twine check dist/*

    # Publish to PyPI
    - run: twine upload dist/*
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

**Go modules**:
```yaml
package-go:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-go@v5
      with:
        go-version: '1.21'

    - run: go build -v -o myapp
    - run: go test -v ./...

    # Create release with goreleaser
    - uses: goreleaser/goreleaser-action@v5
      with:
        version: latest
        args: release --clean
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### 6. Deploy Stage
**Purpose**: Release to target environments

**Environment Promotion**:
```yaml
deploy-dev:
  runs-on: ubuntu-latest
  needs: [package]
  if: github.ref == 'refs/heads/develop'
  environment:
    name: development
    url: https://dev.example.com
  steps:
    - name: Deploy to dev
      run: ./scripts/deploy.sh dev ${{ needs.package.outputs.image-tag }}

deploy-staging:
  runs-on: ubuntu-latest
  needs: [package, deploy-dev]
  if: github.ref == 'refs/heads/main'
  environment:
    name: staging
    url: https://staging.example.com
  steps:
    - name: Deploy to staging
      run: ./scripts/deploy.sh staging ${{ needs.package.outputs.image-tag }}

    # Smoke tests
    - name: Run smoke tests
      run: |
        curl -f https://staging.example.com/health
        npm run test:smoke -- --baseUrl=https://staging.example.com

deploy-production:
  runs-on: ubuntu-latest
  needs: [package, deploy-staging]
  if: github.ref == 'refs/heads/main'
  environment:
    name: production
    url: https://example.com
  steps:
    - name: Deploy to production
      run: ./scripts/deploy.sh production ${{ needs.package.outputs.image-tag }}

    # Verify deployment
    - name: Verify production
      run: |
        curl -f https://example.com/health
        ./scripts/verify-deployment.sh production
```

#### 7. Monitor Stage
**Purpose**: Track deployment success and system health

**Post-Deployment Verification**:
```yaml
monitor-deployment:
  runs-on: ubuntu-latest
  needs: [deploy-production]
  steps:
    # Check error rates
    - name: Check error rates
      run: |
        ERROR_RATE=$(curl -s "http://prometheus:9090/api/v1/query?query=rate(http_requests_total{status=~\"5..\"}[5m])" | jq -r '.data.result[0].value[1]')
        if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
          echo "Error rate too high: $ERROR_RATE"
          exit 1
        fi

    # Check latency
    - name: Check latency
      run: |
        P95_LATENCY=$(curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))" | jq -r '.data.result[0].value[1]')
        if (( $(echo "$P95_LATENCY > 1.0" | bc -l) )); then
          echo "p95 latency too high: $P95_LATENCY"
          exit 1
        fi

    # Trigger incident if issues detected
    - name: Create incident
      if: failure()
      run: |
        curl -X POST https://api.pagerduty.com/incidents \
          -H "Authorization: Token token=${{ secrets.PAGERDUTY_TOKEN }}" \
          -H "Content-Type: application/json" \
          -d '{
            "incident": {
              "type": "incident",
              "title": "Deployment verification failed",
              "service": {"id": "${{ secrets.PAGERDUTY_SERVICE_ID }}"},
              "urgency": "high"
            }
          }'
```

### Pipeline Design Principles

#### 1. Fail Fast
**Principle**: Run fastest, most likely to fail checks first

**Implementation**:
```yaml
stages:
  - lint        # Fast, catches syntax errors (30s)
  - typecheck   # Fast, catches type errors (1m)
  - unit        # Fast, catches logic errors (2m)
  - integration # Slower, catches integration issues (5m)
  - e2e         # Slowest, catches UI/workflow issues (10m)
  - security    # Parallel with tests (5m)
  - deploy      # Only if all pass
```

**Benefits**:
- Faster feedback loops
- Reduced compute waste
- Better developer experience

#### 2. Build Once, Deploy Many
**Principle**: Create artifact once, promote through environments

**Anti-Pattern**:
```yaml
# Bad: Rebuilding for each environment
deploy-dev:
  steps:
    - run: npm run build  # Rebuilds
    - run: deploy to dev

deploy-staging:
  steps:
    - run: npm run build  # Rebuilds differently!
    - run: deploy to staging
```

**Best Practice**:
```yaml
# Good: Build once, deploy everywhere
build:
  steps:
    - run: npm run build
    - run: docker build -t myapp:$VERSION .
  artifacts:
    - myapp:$VERSION

deploy-dev:
  needs: [build]
  steps:
    - run: deploy myapp:$VERSION to dev

deploy-staging:
  needs: [build]
  steps:
    - run: deploy myapp:$VERSION to staging
```

#### 3. Idempotency
**Principle**: Running pipeline multiple times produces same result

**Implementation**:
```bash
# Idempotent deployment
deploy() {
  local env=$1
  local version=$2

  # Check if version already deployed
  current_version=$(kubectl get deployment myapp -n $env -o jsonpath='{.spec.template.spec.containers[0].image}')
  if [ "$current_version" = "myapp:$version" ]; then
    echo "Version $version already deployed"
    return 0
  fi

  # Deploy new version
  kubectl set image deployment/myapp myapp=myapp:$version -n $env
  kubectl rollout status deployment/myapp -n $env
}
```

#### 4. Isolation
**Principle**: Pipeline stages should not interfere with each other

**Implementation**:
```yaml
# Each job runs in clean environment
test-unit:
  runs-on: ubuntu-latest
  container: node:20
  steps:
    - uses: actions/checkout@v4
    - run: npm ci  # Fresh install
    - run: npm test

test-integration:
  runs-on: ubuntu-latest
  container: node:20
  steps:
    - uses: actions/checkout@v4
    - run: npm ci  # Separate install
    - run: npm run test:integration
```

#### 5. Observability
**Principle**: Pipeline execution should be transparent and traceable

**Implementation**:
```yaml
steps:
  - name: Build
    run: |
      echo "::group::Installing dependencies"
      npm ci
      echo "::endgroup::"

      echo "::group::Building application"
      npm run build
      echo "::endgroup::"

      echo "::notice::Build completed successfully"

  # Upload logs
  - uses: actions/upload-artifact@v4
    if: always()
    with:
      name: build-logs
      path: |
        *.log
        npm-debug.log*
```

---

## Pipeline Architecture Patterns

### Pattern 1: Monolithic Pipeline

**Description**: Single pipeline handles all stages sequentially

**Structure**:
```
Source → Build → Test → Security → Package → Deploy → Monitor
```

**Pros**:
- Simple to understand
- Easy to maintain
- Clear dependency chain

**Cons**:
- Slow execution (sequential)
- No parallelization
- All-or-nothing failure

**Use Case**: Small projects, simple workflows, learning CI/CD

### Pattern 2: Parallel Pipeline

**Description**: Independent stages run concurrently

**Structure**:
```
Source → Build →┬→ Unit Tests ────┬→ Package → Deploy
                ├→ Integration ───┤
                ├→ E2E Tests ─────┤
                └→ Security Scan ─┘
```

**Implementation**:
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: npm run build
    outputs:
      artifact-id: ${{ steps.upload.outputs.artifact-id }}

  test-unit:
    needs: [build]
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:unit

  test-integration:
    needs: [build]
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:integration

  test-e2e:
    needs: [build]
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:e2e

  security:
    needs: [build]
    runs-on: ubuntu-latest
    steps:
      - run: npm audit

  package:
    needs: [test-unit, test-integration, test-e2e, security]
    runs-on: ubuntu-latest
    steps:
      - run: docker build -t myapp .
```

**Pros**:
- Faster execution
- Efficient resource usage
- Early feedback on multiple fronts

**Cons**:
- More complex orchestration
- Potential resource contention
- More difficult to debug

**Use Case**: Medium to large projects, multiple test suites

### Pattern 3: Matrix Pipeline

**Description**: Test against multiple configurations simultaneously

**Structure**:
```
Source → Build → Test Matrix:
                 ├→ Node 18 / Ubuntu
                 ├→ Node 18 / macOS
                 ├→ Node 20 / Ubuntu
                 ├→ Node 20 / macOS
                 ├→ Node 22 / Ubuntu
                 └→ Node 22 / macOS
```

**Implementation**:
```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node: [18, 20, 22]
        exclude:
          # Skip expensive combinations
          - os: macos-latest
            node: 18
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
      - run: npm ci
      - run: npm test
```

**Pros**:
- Comprehensive compatibility testing
- Parallel execution
- Early detection of platform-specific issues

**Cons**:
- High resource consumption
- Complex failure diagnosis
- Long execution with large matrices

**Use Case**: Libraries, cross-platform applications, open-source projects

### Pattern 4: Fan-Out/Fan-In Pipeline

**Description**: Split work across multiple jobs, then aggregate results

**Structure**:
```
Source → Build → Fan-Out:
                 ├→ Test Suite 1 ─┐
                 ├→ Test Suite 2 ─┤
                 ├→ Test Suite 3 ─┼→ Fan-In: Aggregate → Package
                 ├→ Test Suite 4 ─┤
                 └→ Test Suite 5 ─┘
```

**Implementation**:
```yaml
jobs:
  test-split:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4, 5]
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run test -- --shard=${{ matrix.shard }}/5
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-${{ matrix.shard }}
          path: coverage/

  aggregate-coverage:
    needs: [test-split]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: coverage-*
          merge-multiple: true
      - run: npx nyc merge coverage/ .nyc_output/coverage.json
      - run: npx nyc report --reporter=text --reporter=html
```

**Pros**:
- Scales to large test suites
- Balanced workload distribution
- Aggregate reporting

**Cons**:
- Complex setup
- Requires test sharding support
- Coordination overhead

**Use Case**: Large test suites, long-running tests, monorepos

### Pattern 5: Trunk-Based Development Pipeline

**Description**: All work happens on main branch with feature flags

**Structure**:
```
main ─┬→ PR opened → CI checks → Merge
      ├→ Commit → CI → Deploy to staging → Auto-deploy to prod (if green)
      └→ Hotfix → CI → Deploy directly to prod
```

**Implementation**:
```yaml
on:
  push:
    branches: [main]

jobs:
  ci-cd:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test
      - run: npm run build

      # Always deploy to staging
      - name: Deploy to staging
        run: ./deploy.sh staging

      # Auto-deploy to prod if staging healthy
      - name: Verify staging
        run: ./verify.sh staging

      - name: Deploy to production
        if: success()
        run: ./deploy.sh production
```

**Pros**:
- Simple branching model
- Fast integration
- Continuous deployment

**Cons**:
- Requires feature flags
- All code must be production-ready
- High discipline required

**Use Case**: Mature teams, feature flag infrastructure, high deployment frequency

### Pattern 6: Multi-Stage Environment Pipeline

**Description**: Progressive promotion through environments with gates

**Structure**:
```
main → CI → Package → Dev (auto) → Staging (auto) → Prod (manual approval)
                       ↓             ↓                ↓
                    Smoke tests   Integration     Full validation
                                     tests         + monitoring
```

**Implementation**:
```yaml
jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - run: npm ci && npm test && npm run build

  deploy-dev:
    needs: [build-and-test]
    environment: development
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh dev
      - run: curl -f https://dev.example.com/health

  deploy-staging:
    needs: [deploy-dev]
    environment: staging
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh staging
      - run: npm run test:smoke -- --baseUrl=https://staging.example.com

  deploy-production:
    needs: [deploy-staging]
    environment:
      name: production
      url: https://example.com
    runs-on: ubuntu-latest
    steps:
      # Manual approval required (configured in GitHub)
      - run: ./deploy.sh production
      - run: ./verify.sh production
```

**Pros**:
- Controlled release process
- Risk mitigation through staged rollout
- Testing in production-like environments

**Cons**:
- Slower time to production
- Resource intensive (multiple environments)
- Potential configuration drift

**Use Case**: Regulated industries, high-stakes applications, enterprise software

---

## GitHub Actions Deep Dive

### Architecture

**Components**:
- **Workflows**: YAML files defining automation (`.github/workflows/*.yml`)
- **Jobs**: Group of steps that execute on same runner
- **Steps**: Individual tasks (actions or shell commands)
- **Actions**: Reusable units of code (marketplace or custom)
- **Runners**: Servers that execute workflows (GitHub-hosted or self-hosted)

**Execution Model**:
```
Workflow Trigger → Queue Jobs → Assign Runners → Execute Steps → Report Results
```

### Workflow Syntax

**Basic Structure**:
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:

env:
  NODE_VERSION: '20'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - run: npm ci
      - run: npm run build
```

### Advanced Features

#### Reusable Workflows

**Define reusable workflow** (`.github/workflows/reusable-deploy.yml`):
```yaml
name: Reusable Deploy

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
      version:
        required: true
        type: string
    secrets:
      deploy-key:
        required: true
    outputs:
      deployment-url:
        description: "URL of deployed application"
        value: ${{ jobs.deploy.outputs.url }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    outputs:
      url: ${{ steps.deploy.outputs.url }}
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        id: deploy
        run: |
          ./deploy.sh ${{ inputs.environment }} ${{ inputs.version }}
          echo "url=https://${{ inputs.environment }}.example.com" >> $GITHUB_OUTPUT
        env:
          DEPLOY_KEY: ${{ secrets.deploy-key }}
```

**Call reusable workflow**:
```yaml
name: Main Pipeline

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
    steps:
      - id: version
        run: echo "version=v1.2.3" >> $GITHUB_OUTPUT

  deploy-staging:
    needs: [build]
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: staging
      version: ${{ needs.build.outputs.version }}
    secrets:
      deploy-key: ${{ secrets.STAGING_DEPLOY_KEY }}

  deploy-production:
    needs: [deploy-staging]
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
      version: ${{ needs.build.outputs.version }}
    secrets:
      deploy-key: ${{ secrets.PROD_DEPLOY_KEY }}
```

#### Matrix Strategies with Dynamic Values

```yaml
jobs:
  prepare-matrix:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - id: set-matrix
        run: |
          # Dynamically generate matrix based on changed files
          MATRIX=$(cat <<EOF
          {
            "include": [
              {"service": "api", "port": 3000},
              {"service": "web", "port": 3001},
              {"service": "worker", "port": 3002}
            ]
          }
          EOF
          )
          echo "matrix=$(echo $MATRIX | jq -c)" >> $GITHUB_OUTPUT

  test:
    needs: [prepare-matrix]
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.prepare-matrix.outputs.matrix) }}
    steps:
      - run: echo "Testing ${{ matrix.service }} on port ${{ matrix.port }}"
```

#### Composite Actions

**Create composite action** (`.github/actions/setup-env/action.yml`):
```yaml
name: 'Setup Environment'
description: 'Sets up Node.js and caches dependencies'

inputs:
  node-version:
    description: 'Node.js version'
    required: false
    default: '20'

runs:
  using: 'composite'
  steps:
    - uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'npm'

    - run: npm ci
      shell: bash

    - run: echo "Environment setup complete"
      shell: bash
```

**Use composite action**:
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-env
        with:
          node-version: '20'
      - run: npm run build
```

#### Concurrency Control

```yaml
# Cancel in-progress runs for same PR
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    # Only one deployment at a time
    concurrency:
      group: deploy-${{ github.ref }}
      cancel-in-progress: false
    steps:
      - run: ./deploy.sh
```

#### Secrets and Environments

**Organization/Repository Secrets**:
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying with key"
        env:
          API_KEY: ${{ secrets.API_KEY }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
```

**Environment Secrets and Protection Rules**:
```yaml
jobs:
  deploy-prod:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      # Requires approval if configured in GitHub
      # Uses environment-specific secrets
      - run: ./deploy.sh
        env:
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}  # From production environment
```

#### OIDC Authentication

**AWS**:
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: us-east-1

      - run: aws s3 ls  # Authenticated via OIDC, no long-lived credentials
```

**Azure**:
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: azure/login@v1
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - run: az account show
```

**GCP**:
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: 'projects/123/locations/global/workloadIdentityPools/github/providers/github'
          service_account: 'github-actions@project.iam.gserviceaccount.com'

      - run: gcloud projects list
```

### Performance Optimization

#### Caching Strategies

**npm**:
```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'  # Automatic caching
```

**Custom cache**:
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      ~/.cache/Cypress
      node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

**Docker layers**:
```yaml
- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: myapp:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

#### Artifacts Management

**Upload artifacts**:
```yaml
- uses: actions/upload-artifact@v4
  with:
    name: dist-${{ github.sha }}
    path: dist/
    retention-days: 7
    compression-level: 6
```

**Download artifacts**:
```yaml
- uses: actions/download-artifact@v4
  with:
    name: dist-${{ github.sha }}
    path: dist/
```

#### Self-Hosted Runners

**Setup**:
```bash
# On your server
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz
./config.sh --url https://github.com/myorg/myrepo --token TOKEN
./run.sh
```

**Use in workflow**:
```yaml
jobs:
  build:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - run: ./build.sh
```

**Labels for specific runners**:
```yaml
jobs:
  build:
    runs-on: [self-hosted, linux, x64, gpu]
    steps:
      - run: nvidia-smi  # Runs on GPU-enabled runner
```

---

## GitLab CI Deep Dive

### Architecture

**Components**:
- **Pipeline**: Top-level workflow (triggered by events)
- **Stages**: Sequential groups of jobs
- **Jobs**: Individual tasks that run in stages
- **Runners**: Agents that execute jobs (shared or project-specific)

**Execution Model**:
```
Pipeline Trigger → Queue Jobs by Stage → Assign Runners → Execute Jobs → Report Results
```

### Pipeline Syntax

**Basic Structure**:
```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

variables:
  NODE_VERSION: "20"

build-job:
  stage: build
  image: node:${NODE_VERSION}
  script:
    - npm ci
    - npm run build
  artifacts:
    paths:
      - dist/
    expire_in: 1 week
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/
```

### Advanced Features

#### Includes and Templates

**External templates**:
```yaml
include:
  # GitLab templates
  - template: Security/SAST.gitlab-ci.yml
  - template: Security/Dependency-Scanning.gitlab-ci.yml

  # Remote files
  - remote: 'https://gitlab.com/myorg/templates/-/raw/main/deploy.yml'

  # Local files
  - local: '.gitlab/templates/build.yml'

  # Project files
  - project: 'myorg/shared-ci'
    ref: main
    file: '/templates/deploy.yml'
```

**Template inheritance**:
```yaml
# .gitlab/templates/build.yml
.build-template:
  image: node:20
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/
  before_script:
    - npm ci

# .gitlab-ci.yml
include:
  - local: '.gitlab/templates/build.yml'

build:
  extends: .build-template
  script:
    - npm run build
```

#### DAG (Directed Acyclic Graph) Pipelines

```yaml
stages:
  - build
  - test
  - deploy

build-api:
  stage: build
  script:
    - ./build-api.sh
  artifacts:
    paths: [api/dist/]

build-web:
  stage: build
  script:
    - ./build-web.sh
  artifacts:
    paths: [web/dist/]

test-api:
  stage: test
  needs: [build-api]  # Only depends on build-api
  script:
    - ./test-api.sh

test-web:
  stage: test
  needs: [build-web]  # Only depends on build-web
  script:
    - ./test-web.sh

deploy:
  stage: deploy
  needs: [test-api, test-web]  # Wait for both
  script:
    - ./deploy.sh
```

**Visualization**:
```
build-api → test-api ↘
                      deploy
build-web → test-web ↗
```

#### Dynamic Child Pipelines

**Parent pipeline**:
```yaml
generate-config:
  stage: build
  script:
    - ./generate-child-pipeline.sh > child-pipeline.yml
  artifacts:
    paths:
      - child-pipeline.yml

trigger-child:
  stage: test
  trigger:
    include:
      - artifact: child-pipeline.yml
        job: generate-config
    strategy: depend
```

**Generated child pipeline** (child-pipeline.yml):
```yaml
test-service-1:
  script:
    - ./test-service-1.sh

test-service-2:
  script:
    - ./test-service-2.sh
```

#### Environments and Deployments

```yaml
deploy-staging:
  stage: deploy
  script:
    - ./deploy.sh staging
  environment:
    name: staging
    url: https://staging.example.com
    on_stop: stop-staging
    auto_stop_in: 1 week
  only:
    - develop

stop-staging:
  stage: deploy
  script:
    - ./stop.sh staging
  environment:
    name: staging
    action: stop
  when: manual

deploy-production:
  stage: deploy
  script:
    - ./deploy.sh production
  environment:
    name: production
    url: https://example.com
    deployment_tier: production
  when: manual
  only:
    - main
```

#### Rules and Conditions

```yaml
build:
  script:
    - npm run build
  rules:
    # Run on MRs
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

    # Run on main branch
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

    # Run if specific files changed
    - changes:
        - src/**/*
        - package.json
      when: always

    # Skip if commit message contains [skip ci]
    - if: $CI_COMMIT_MESSAGE =~ /\[skip ci\]/
      when: never

    # Allow manual trigger
    - when: manual
      allow_failure: true
```

#### Services (Sidecar Containers)

```yaml
test:integration:
  image: node:20
  services:
    - name: postgres:16
      alias: postgres
    - name: redis:7
      alias: redis
    - name: elasticsearch:8.11.0
      alias: elasticsearch
      command: ['bin/elasticsearch', '-Expack.security.enabled=false']
  variables:
    POSTGRES_DB: test
    POSTGRES_USER: test
    POSTGRES_PASSWORD: test
    DATABASE_URL: postgresql://test:test@postgres:5432/test
    REDIS_URL: redis://redis:6379
    ELASTICSEARCH_URL: http://elasticsearch:9200
  script:
    - npm run test:integration
```

#### Caching Strategies

**Per-branch caching**:
```yaml
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - node_modules/
    - .npm/
  policy: pull-push
```

**Global cache with fallback**:
```yaml
cache:
  key:
    files:
      - package-lock.json
  paths:
    - node_modules/
  fallback_keys:
    - ${CI_COMMIT_REF_SLUG}
    - default
```

**Job-specific cache**:
```yaml
build:
  cache:
    key: build-cache
    paths:
      - dist/
    policy: push

test:
  cache:
    key: build-cache
    paths:
      - dist/
    policy: pull
```

### GitLab Runner Configuration

**Register runner**:
```bash
gitlab-runner register \
  --url https://gitlab.com/ \
  --registration-token TOKEN \
  --executor docker \
  --docker-image alpine:latest \
  --docker-volumes /var/run/docker.sock:/var/run/docker.sock
```

**Configure runner** (`config.toml`):
```toml
[[runners]]
  name = "production-runner"
  url = "https://gitlab.com/"
  token = "TOKEN"
  executor = "docker"

  [runners.docker]
    image = "alpine:latest"
    privileged = true
    volumes = ["/cache", "/var/run/docker.sock:/var/run/docker.sock"]
    pull_policy = "if-not-present"

  [runners.cache]
    Type = "s3"
    Shared = true
    [runners.cache.s3]
      ServerAddress = "s3.amazonaws.com"
      BucketName = "gitlab-runner-cache"
      BucketLocation = "us-east-1"
```

---

## Jenkins Deep Dive

### Architecture

**Components**:
- **Master**: Orchestrates builds, manages configuration
- **Agents**: Execute builds (can be static or dynamic)
- **Executors**: Concurrent build slots on agents
- **Plugins**: Extend functionality (1800+ available)

**Execution Model**:
```
Job Trigger → Master Schedules → Assign to Agent → Execute on Executor → Report to Master
```

### Pipeline Syntax

#### Declarative Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any

    parameters {
        string(name: 'ENVIRONMENT', defaultValue: 'staging', description: 'Deployment environment')
        booleanParam(name: 'RUN_TESTS', defaultValue: true, description: 'Run tests')
    }

    environment {
        NODE_VERSION = '20'
        DOCKER_REGISTRY = 'registry.example.com'
        IMAGE_NAME = "${DOCKER_REGISTRY}/myapp"
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 1, unit: 'HOURS')
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                script {
                    sh 'npm ci'
                    sh 'npm run build'
                }
            }
        }

        stage('Test') {
            when {
                expression { params.RUN_TESTS }
            }
            parallel {
                stage('Unit Tests') {
                    steps {
                        sh 'npm run test:unit'
                    }
                }
                stage('Integration Tests') {
                    steps {
                        sh 'npm run test:integration'
                    }
                }
            }
        }

        stage('Package') {
            steps {
                script {
                    def version = sh(script: "jq -r .version package.json", returnStdout: true).trim()
                    def imageTag = "${IMAGE_NAME}:${version}-${BUILD_NUMBER}"

                    sh "docker build -t ${imageTag} ."
                    sh "docker push ${imageTag}"

                    env.IMAGE_TAG = imageTag
                }
            }
        }

        stage('Deploy') {
            steps {
                script {
                    deploy(params.ENVIRONMENT, env.IMAGE_TAG)
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            slackSend(color: 'good', message: "Build succeeded: ${env.BUILD_URL}")
        }
        failure {
            slackSend(color: 'danger', message: "Build failed: ${env.BUILD_URL}")
        }
    }
}

def deploy(environment, imageTag) {
    sh """
        kubectl config use-context ${environment}-cluster
        kubectl set image deployment/myapp myapp=${imageTag} -n ${environment}
        kubectl rollout status deployment/myapp -n ${environment}
    """
}
```

#### Scripted Pipeline

```groovy
// More flexible but requires more code
node {
    try {
        stage('Checkout') {
            checkout scm
        }

        stage('Build') {
            sh 'npm ci'
            sh 'npm run build'
        }

        stage('Test') {
            parallel(
                'unit': {
                    sh 'npm run test:unit'
                },
                'integration': {
                    sh 'npm run test:integration'
                }
            )
        }

        stage('Deploy') {
            input message: 'Deploy to production?', ok: 'Deploy'
            sh './deploy.sh production'
        }

        currentBuild.result = 'SUCCESS'
    } catch (Exception e) {
        currentBuild.result = 'FAILURE'
        throw e
    } finally {
        // Cleanup
        cleanWs()
    }
}
```

### Shared Libraries

**Define library** (`vars/deployToK8s.groovy`):
```groovy
def call(Map config) {
    def environment = config.environment
    def imageTag = config.imageTag
    def namespace = config.get('namespace', environment)

    sh """
        kubectl config use-context ${environment}-cluster
        kubectl set image deployment/${config.deployment} \
            ${config.container}=${imageTag} \
            -n ${namespace}
        kubectl rollout status deployment/${config.deployment} -n ${namespace}
    """

    // Run smoke tests
    sh "curl -f https://${environment}.example.com/health"
}
```

**Use library** (Jenkinsfile):
```groovy
@Library('shared-pipeline-library') _

pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                sh 'npm run build'
                sh "docker build -t myapp:${BUILD_NUMBER} ."
            }
        }

        stage('Deploy') {
            steps {
                deployToK8s(
                    environment: 'production',
                    deployment: 'myapp',
                    container: 'myapp',
                    imageTag: "myapp:${BUILD_NUMBER}"
                )
            }
        }
    }
}
```

### Kubernetes Plugin

**Dynamic pod agents**:
```groovy
pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    jenkins: agent
spec:
  containers:
  - name: node
    image: node:20
    command:
    - cat
    tty: true
  - name: docker
    image: docker:24
    command:
    - cat
    tty: true
    volumeMounts:
    - name: docker-sock
      mountPath: /var/run/docker.sock
  volumes:
  - name: docker-sock
    hostPath:
      path: /var/run/docker.sock
"""
        }
    }

    stages {
        stage('Build') {
            steps {
                container('node') {
                    sh 'npm ci'
                    sh 'npm run build'
                }
            }
        }

        stage('Package') {
            steps {
                container('docker') {
                    sh 'docker build -t myapp .'
                }
            }
        }
    }
}
```

### Pipeline Optimization

**Stash/Unstash for artifacts**:
```groovy
stage('Build') {
    steps {
        sh 'npm run build'
        stash includes: 'dist/**', name: 'build-artifacts'
    }
}

stage('Deploy') {
    agent { label 'deploy-agent' }
    steps {
        unstash 'build-artifacts'
        sh './deploy.sh'
    }
}
```

**Parallel stages**:
```groovy
stage('Test') {
    parallel {
        stage('Unit') {
            steps {
                sh 'npm run test:unit'
            }
        }
        stage('Integration') {
            steps {
                sh 'npm run test:integration'
            }
        }
        stage('E2E') {
            steps {
                sh 'npm run test:e2e'
            }
        }
    }
}
```

---

## CircleCI Deep Dive

### Architecture

**Components**:
- **Projects**: Repository connections
- **Workflows**: Orchestrate jobs
- **Jobs**: Groups of steps
- **Executors**: Environment for jobs (docker, machine, macos, windows)
- **Orbs**: Reusable configuration packages

### Configuration Syntax

**Basic structure**:
```yaml
# .circleci/config.yml
version: 2.1

orbs:
  node: circleci/node@5.1.0
  docker: circleci/docker@2.2.0

executors:
  node-executor:
    docker:
      - image: cimg/node:20.10
    resource_class: medium

jobs:
  build:
    executor: node-executor
    steps:
      - checkout
      - node/install-packages:
          pkg-manager: npm
      - run:
          name: Build
          command: npm run build
      - persist_to_workspace:
          root: .
          paths:
            - dist/

  test:
    executor: node-executor
    parallelism: 4
    steps:
      - checkout
      - node/install-packages
      - run:
          name: Run tests
          command: |
            TESTFILES=$(circleci tests glob "src/**/*.test.js" | circleci tests split --split-by=timings)
            npm test $TESTFILES

  deploy:
    executor: node-executor
    steps:
      - checkout
      - attach_workspace:
          at: .
      - run:
          name: Deploy
          command: ./deploy.sh production

workflows:
  version: 2
  build-test-deploy:
    jobs:
      - build
      - test:
          requires:
            - build
      - deploy:
          requires:
            - test
          filters:
            branches:
              only: main
```

### Advanced Features

#### Orbs

**Using orbs**:
```yaml
version: 2.1

orbs:
  aws-cli: circleci/aws-cli@4.0
  slack: circleci/slack@4.12

jobs:
  deploy:
    executor: aws-cli/default
    steps:
      - checkout
      - aws-cli/setup:
          aws-access-key-id: AWS_ACCESS_KEY_ID
          aws-secret-access-key: AWS_SECRET_ACCESS_KEY
      - run: aws s3 sync dist/ s3://my-bucket/
      - slack/notify:
          event: fail
          template: basic_fail_1
```

**Creating orbs** (advanced):
```yaml
version: 2.1

description: Custom deployment orb

commands:
  deploy:
    parameters:
      environment:
        type: string
      version:
        type: string
    steps:
      - run:
          name: Deploy to << parameters.environment >>
          command: |
            ./deploy.sh << parameters.environment >> << parameters.version >>

jobs:
  deploy-job:
    parameters:
      environment:
        type: string
    docker:
      - image: cimg/base:stable
    steps:
      - checkout
      - deploy:
          environment: << parameters.environment >>
          version: $CIRCLE_TAG
```

#### Matrix Jobs

```yaml
version: 2.1

jobs:
  test:
    parameters:
      node-version:
        type: string
      os:
        type: string
    docker:
      - image: cimg/node:<< parameters.node-version >>
    steps:
      - checkout
      - run: npm ci
      - run: npm test

workflows:
  test-matrix:
    jobs:
      - test:
          matrix:
            parameters:
              node-version: ["18.19", "20.10", "21.5"]
              os: ["linux", "macos"]
```

#### Dynamic Configuration

```yaml
version: 2.1

setup: true

orbs:
  continuation: circleci/continuation@0.3.1

jobs:
  setup:
    executor: continuation/default
    steps:
      - checkout
      - run:
          name: Generate config
          command: |
            ./generate-config.sh > generated-config.yml
      - continuation/continue:
          configuration_path: generated-config.yml

workflows:
  setup-workflow:
    jobs:
      - setup
```

---

## Buildkite Deep Dive

### Architecture

**Components**:
- **Pipeline**: YAML configuration defining steps
- **Agents**: Self-hosted workers that execute steps
- **Steps**: Individual commands or script executions
- **Plugins**: Extend functionality (Docker, S3, etc.)

### Pipeline Syntax

```yaml
# .buildkite/pipeline.yml
steps:
  - label: ":hammer: Build"
    command: |
      npm ci
      npm run build
    artifact_paths:
      - "dist/**/*"
    agents:
      queue: "default"
      os: "linux"

  - wait

  - label: ":test_tube: Test"
    command: "npm test"
    parallelism: 3
    agents:
      queue: "default"

  - wait

  - block: ":rocket: Deploy to production?"
    blocked_state: "passed"

  - label: ":rocket: Deploy"
    command: "./deploy.sh production"
    agents:
      queue: "deploy"
    concurrency: 1
    concurrency_group: "production-deploy"
```

### Dynamic Pipelines

```yaml
steps:
  - label: ":pipeline: Upload dynamic pipeline"
    command: |
      ./generate-pipeline.sh | buildkite-agent pipeline upload
```

**Generated pipeline**:
```bash
#!/bin/bash
# generate-pipeline.sh

cat << EOF
steps:
  - label: "Test service 1"
    command: "./test-service-1.sh"
  - label: "Test service 2"
    command: "./test-service-2.sh"
EOF
```

### Plugins

**Docker plugin**:
```yaml
steps:
  - label: ":docker: Build in Docker"
    plugins:
      - docker#v5.7.0:
          image: "node:20"
          workdir: /app
          volumes:
            - ".:/app"
          command: ["npm", "ci", "&&", "npm", "test"]
```

**Docker Compose plugin**:
```yaml
steps:
  - label: ":docker: Integration tests"
    plugins:
      - docker-compose#v4.14.0:
          run: app
          config: docker-compose.test.yml
          command: npm run test:integration
```

---

## Azure Pipelines Deep Dive

### Architecture

**Components**:
- **Pipelines**: YAML or visual definitions
- **Stages**: Major divisions in pipeline (build, test, deploy)
- **Jobs**: Units of work within stages
- **Steps**: Individual tasks
- **Agents**: Microsoft-hosted or self-hosted

### Pipeline Syntax

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main
      - develop
  paths:
    exclude:
      - docs/*

pr:
  branches:
    include:
      - main

variables:
  buildConfiguration: 'Release'
  vmImageName: 'ubuntu-latest'

stages:
  - stage: Build
    displayName: 'Build stage'
    jobs:
      - job: Build
        displayName: 'Build job'
        pool:
          vmImage: $(vmImageName)
        steps:
          - task: NodeTool@0
            inputs:
              versionSpec: '20.x'
            displayName: 'Install Node.js'

          - script: |
              npm ci
              npm run build
            displayName: 'npm install and build'

          - task: PublishBuildArtifacts@1
            inputs:
              PathtoPublish: 'dist'
              ArtifactName: 'drop'
            displayName: 'Publish artifacts'

  - stage: Test
    displayName: 'Test stage'
    dependsOn: Build
    jobs:
      - job: Test
        displayName: 'Test job'
        pool:
          vmImage: $(vmImageName)
        strategy:
          matrix:
            Node18:
              node_version: '18.x'
            Node20:
              node_version: '20.x'
        steps:
          - task: NodeTool@0
            inputs:
              versionSpec: $(node_version)

          - script: npm ci && npm test
            displayName: 'Run tests'

          - task: PublishTestResults@2
            condition: succeededOrFailed()
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: '**/test-results.xml'

  - stage: Deploy
    displayName: 'Deploy stage'
    dependsOn: Test
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: Deploy
        displayName: 'Deploy job'
        environment: 'production'
        pool:
          vmImage: $(vmImageName)
        strategy:
          runOnce:
            deploy:
              steps:
                - task: DownloadBuildArtifacts@1
                  inputs:
                    buildType: 'current'
                    downloadType: 'single'
                    artifactName: 'drop'

                - script: ./deploy.sh production
                  displayName: 'Deploy to production'
```

### Multi-Stage Deployments

```yaml
stages:
  - stage: DeployDev
    displayName: 'Deploy to Dev'
    jobs:
      - deployment: DeployDev
        environment: 'dev'
        strategy:
          runOnce:
            deploy:
              steps:
                - script: ./deploy.sh dev

  - stage: DeployStaging
    displayName: 'Deploy to Staging'
    dependsOn: DeployDev
    jobs:
      - deployment: DeployStaging
        environment: 'staging'
        strategy:
          runOnce:
            deploy:
              steps:
                - script: ./deploy.sh staging

  - stage: DeployProd
    displayName: 'Deploy to Production'
    dependsOn: DeployStaging
    jobs:
      - deployment: DeployProd
        environment: 'production'
        strategy:
          canary:
            increments: [10, 20, 50, 100]
            deploy:
              steps:
                - script: ./deploy.sh production --canary $(strategy.canaryPercentage)
```

---

## Testing Strategies in Pipelines

### Test Pyramid Implementation

**Unit Tests** (70% of tests):
```yaml
test-unit:
  runs-on: ubuntu-latest
  steps:
    - run: npm run test:unit -- --coverage
    - uses: codecov/codecov-action@v3
      with:
        flags: unit
        fail_ci_if_error: true
```

**Characteristics**:
- Fast (< 10 seconds total)
- No external dependencies
- Test individual functions/methods
- High code coverage (80%+)

**Integration Tests** (20% of tests):
```yaml
test-integration:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:16
    redis:
      image: redis:7
  steps:
    - run: npm run test:integration
```

**Characteristics**:
- Medium speed (1-5 minutes)
- Test module boundaries
- Use real databases/services (in containers)
- Test API contracts

**E2E Tests** (10% of tests):
```yaml
test-e2e:
  runs-on: ubuntu-latest
  steps:
    - run: npx playwright install --with-deps
    - run: npm run start &
    - run: npx wait-on http://localhost:3000
    - run: npm run test:e2e
```

**Characteristics**:
- Slow (5-15 minutes)
- Test complete user workflows
- Browser automation
- Critical paths only

### Test Sharding

**Playwright sharding**:
```yaml
test-e2e:
  runs-on: ubuntu-latest
  strategy:
    matrix:
      shard: [1, 2, 3, 4]
  steps:
    - run: npx playwright test --shard=${{ matrix.shard }}/4
```

**Jest sharding**:
```yaml
test-unit:
  runs-on: ubuntu-latest
  strategy:
    matrix:
      shard: [1, 2, 3, 4]
  steps:
    - run: |
        npm test -- --shard=${{ matrix.shard }}/4 --maxWorkers=4
```

### Flaky Test Detection

```yaml
test-e2e:
  runs-on: ubuntu-latest
  steps:
    - run: npx playwright test --retries=2 --reporter=html

    # Detect flaky tests
    - name: Analyze flaky tests
      if: always()
      run: |
        FLAKY=$(cat test-results/flaky-tests.json | jq -r '.[] | .name')
        if [ -n "$FLAKY" ]; then
          echo "::warning::Flaky tests detected: $FLAKY"
          # Create issue for flaky tests
          gh issue create --title "Flaky tests detected" --body "$FLAKY"
        fi
```

### Contract Testing

**Provider side** (API):
```yaml
test-contract:
  runs-on: ubuntu-latest
  steps:
    - run: npm run start &
    - run: npx wait-on http://localhost:3000

    # Verify provider satisfies contracts
    - run: npm run test:pact:verify

    # Publish contracts
    - run: |
        npx pact-broker publish pacts/ \
          --consumer-app-version ${{ github.sha }} \
          --broker-base-url https://pact-broker.example.com \
          --broker-token ${{ secrets.PACT_BROKER_TOKEN }}
```

**Consumer side** (Client):
```yaml
test-contract:
  runs-on: ubuntu-latest
  steps:
    # Generate contracts
    - run: npm run test:pact

    # Publish contracts
    - run: |
        npx pact-broker publish pacts/ \
          --consumer-app-version ${{ github.sha }} \
          --broker-base-url https://pact-broker.example.com

    # Can we deploy?
    - run: |
        npx pact-broker can-i-deploy \
          --pacticipant my-consumer \
          --version ${{ github.sha }} \
          --to production
```

---

## Security Scanning Integration

### SAST (Static Application Security Testing)

#### CodeQL

```yaml
security-codeql:
  runs-on: ubuntu-latest
  permissions:
    security-events: write
  steps:
    - uses: actions/checkout@v4

    - uses: github/codeql-action/init@v3
      with:
        languages: javascript, python, go
        queries: security-extended, security-and-quality

    - uses: github/codeql-action/autobuild@v3

    - uses: github/codeql-action/analyze@v3
      with:
        category: "/language:javascript"
```

#### Semgrep

```yaml
security-semgrep:
  runs-on: ubuntu-latest
  container: returntocorp/semgrep
  steps:
    - uses: actions/checkout@v4

    - run: |
        semgrep scan \
          --config="p/security-audit" \
          --config="p/owasp-top-ten" \
          --config="p/cwe-top-25" \
          --sarif \
          --output=semgrep-results.sarif

    - uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: semgrep-results.sarif
```

#### SonarQube

```yaml
security-sonar:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full history for better analysis

    - uses: sonarsource/sonarqube-scan-action@master
      env:
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}

    # Check quality gate
    - uses: sonarsource/sonarqube-quality-gate-action@master
      timeout-minutes: 5
      env:
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### Dependency Scanning

#### npm audit

```yaml
security-npm:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4

    - run: npm audit --audit-level=moderate

    # Generate audit report
    - run: npm audit --json > npm-audit.json

    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: npm-audit-report
        path: npm-audit.json
```

#### Snyk

```yaml
security-snyk:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - uses: snyk/actions/setup@master

    # Test dependencies
    - run: snyk test --severity-threshold=high --json-file-output=snyk-test.json
      env:
        SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
      continue-on-error: true

    # Monitor for ongoing tracking
    - run: snyk monitor
      env:
        SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

#### Trivy

```yaml
security-trivy-fs:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
        severity: 'CRITICAL,HIGH'

    - uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: 'trivy-results.sarif'
```

### Container Scanning

```yaml
security-container:
  runs-on: ubuntu-latest
  needs: [build-image]
  steps:
    # Trivy scan
    - uses: aquasecurity/trivy-action@master
      with:
        image-ref: ${{ needs.build-image.outputs.image }}
        format: 'sarif'
        output: 'trivy-container.sarif'
        severity: 'CRITICAL,HIGH'
        exit-code: '1'

    # Grype scan
    - uses: anchore/scan-action@v3
      with:
        image: ${{ needs.build-image.outputs.image }}
        fail-build: true
        severity-cutoff: high
        output-format: sarif

    # Upload results
    - uses: github/codeql-action/upload-sarif@v3
      if: always()
      with:
        sarif_file: trivy-container.sarif
```

### DAST (Dynamic Application Security Testing)

```yaml
security-dast:
  runs-on: ubuntu-latest
  needs: [deploy-staging]
  steps:
    # OWASP ZAP scan
    - name: ZAP Scan
      uses: zaproxy/action-full-scan@v0.7.0
      with:
        target: 'https://staging.example.com'
        rules_file_name: '.zap/rules.tsv'
        cmd_options: '-a'
```

### Secret Scanning

#### Gitleaks

```yaml
security-secrets:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}
```

#### TruffleHog

```yaml
security-trufflehog:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - uses: trufflesecurity/trufflehog@main
      with:
        path: ./
        base: ${{ github.event.repository.default_branch }}
        head: HEAD
```

### License Compliance

```yaml
security-licenses:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    # Check licenses
    - run: npx license-checker --production --json --out licenses.json

    # Fail on prohibited licenses
    - run: |
        npx license-checker --production --failOn 'GPL;AGPL;LGPL'

    # Generate SBOM
    - uses: anchore/sbom-action@v0
      with:
        format: spdx-json
        output-file: sbom.spdx.json

    - uses: actions/upload-artifact@v4
      with:
        name: sbom
        path: sbom.spdx.json
```

---

## Artifact Management

### Versioning Strategies

#### Semantic Versioning

```yaml
- name: Generate version
  id: version
  run: |
    # Extract version from package.json
    BASE_VERSION=$(jq -r .version package.json)

    # Append metadata
    GIT_SHA=${GITHUB_SHA::8}
    BUILD_NUM=${GITHUB_RUN_NUMBER}

    # Full version: v1.2.3-build.123+abc1234
    VERSION="v${BASE_VERSION}-build.${BUILD_NUM}+${GIT_SHA}"

    echo "version=$VERSION" >> $GITHUB_OUTPUT
```

#### CalVer (Calendar Versioning)

```yaml
- name: Generate CalVer
  id: version
  run: |
    # Format: YYYY.MM.MINOR
    YEAR=$(date +%Y)
    MONTH=$(date +%m)
    MINOR=$(git rev-list --count HEAD)

    VERSION="${YEAR}.${MONTH}.${MINOR}"
    echo "version=$VERSION" >> $GITHUB_OUTPUT
```

#### Git-Based Versioning

```yaml
- name: Generate version from git
  id: version
  run: |
    # Use git describe
    VERSION=$(git describe --tags --always --dirty)

    # Or use commits since last tag
    LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
    COMMITS=$(git rev-list ${LAST_TAG}..HEAD --count)
    SHA=${GITHUB_SHA::8}

    VERSION="${LAST_TAG}-${COMMITS}-g${SHA}"
    echo "version=$VERSION" >> $GITHUB_OUTPUT
```

### Registry Management

#### Docker Registries

**GitHub Container Registry (GHCR)**:
```yaml
- uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- uses: docker/build-push-action@v5
  with:
    push: true
    tags: |
      ghcr.io/${{ github.repository }}:${{ steps.version.outputs.version }}
      ghcr.io/${{ github.repository }}:latest
```

**Amazon ECR**:
```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE }}
    aws-region: us-east-1

- name: Login to ECR
  id: ecr-login
  uses: aws-actions/amazon-ecr-login@v2

- uses: docker/build-push-action@v5
  with:
    push: true
    tags: |
      ${{ steps.ecr-login.outputs.registry }}/myapp:${{ steps.version.outputs.version }}
```

**Google Artifact Registry**:
```yaml
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
    service_account: ${{ secrets.SERVICE_ACCOUNT }}

- name: Login to GAR
  run: gcloud auth configure-docker us-central1-docker.pkg.dev

- uses: docker/build-push-action@v5
  with:
    push: true
    tags: us-central1-docker.pkg.dev/project/repo/myapp:${{ steps.version.outputs.version }}
```

#### Package Registries

**npm**:
```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    registry-url: 'https://registry.npmjs.org'

- run: npm publish
  env:
    NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

**PyPI**:
```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'

- run: |
    pip install build twine
    python -m build
    twine upload dist/*
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

**Maven Central**:
```yaml
- uses: actions/setup-java@v4
  with:
    java-version: '21'
    distribution: 'temurin'
    server-id: ossrh
    server-username: MAVEN_USERNAME
    server-password: MAVEN_PASSWORD
    gpg-private-key: ${{ secrets.GPG_PRIVATE_KEY }}
    gpg-passphrase: GPG_PASSPHRASE

- run: mvn deploy
  env:
    MAVEN_USERNAME: ${{ secrets.OSSRH_USERNAME }}
    MAVEN_PASSWORD: ${{ secrets.OSSRH_TOKEN }}
    GPG_PASSPHRASE: ${{ secrets.GPG_PASSPHRASE }}
```

### Artifact Retention

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: build-artifacts
    path: dist/
    retention-days: 30  # Keep for 30 days
    compression-level: 6  # Balance speed and size
    if-no-files-found: error  # Fail if artifacts missing
```

### SBOM (Software Bill of Materials)

**Generate SBOM**:
```yaml
- name: Generate SBOM with Syft
  uses: anchore/sbom-action@v0
  with:
    image: myapp:${{ steps.version.outputs.version }}
    format: spdx-json
    output-file: sbom.spdx.json

- name: Generate SBOM with CycloneDX
  run: |
    npx @cyclonedx/cyclonedx-npm --output-file sbom.cyclonedx.json

- uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: |
      sbom.spdx.json
      sbom.cyclonedx.json
```

**Attest SBOM** (GitHub):
```yaml
- uses: actions/attest-sbom@v1
  with:
    subject-name: ghcr.io/${{ github.repository }}
    subject-digest: ${{ steps.build.outputs.digest }}
    sbom-path: sbom.spdx.json
    push-to-registry: true
```

---

## Secret Management

### Platform-Native Secrets

**GitHub Actions**:
```yaml
steps:
  - run: ./deploy.sh
    env:
      API_KEY: ${{ secrets.API_KEY }}
      DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
```

**GitLab CI**:
```yaml
deploy:
  script:
    - ./deploy.sh
  variables:
    API_KEY: ${{ secrets.API_KEY }}
```

**Azure Pipelines**:
```yaml
- script: ./deploy.sh
  env:
    API_KEY: $(API_KEY)
```

### External Secret Management

#### HashiCorp Vault

```yaml
- name: Import Secrets from Vault
  uses: hashicorp/vault-action@v2
  with:
    url: https://vault.example.com
    token: ${{ secrets.VAULT_TOKEN }}
    secrets: |
      secret/data/production/db password | DB_PASSWORD ;
      secret/data/production/api key | API_KEY

- run: ./deploy.sh
  env:
    DB_PASSWORD: ${{ env.DB_PASSWORD }}
    API_KEY: ${{ env.API_KEY }}
```

#### AWS Secrets Manager

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE }}
    aws-region: us-east-1

- name: Retrieve secrets
  uses: aws-actions/aws-secretsmanager-get-secrets@v1
  with:
    secret-ids: |
      DB_PASSWORD, production/db/password
      API_KEY, production/api/key

- run: ./deploy.sh
  env:
    DB_PASSWORD: ${{ env.DB_PASSWORD }}
    API_KEY: ${{ env.API_KEY }}
```

#### Azure Key Vault

```yaml
- uses: azure/login@v1
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}

- uses: azure/get-keyvault-secrets@v1
  with:
    keyvault: 'my-keyvault'
    secrets: 'db-password, api-key'
  id: secrets

- run: ./deploy.sh
  env:
    DB_PASSWORD: ${{ steps.secrets.outputs.db-password }}
    API_KEY: ${{ steps.secrets.outputs.api-key }}
```

#### Google Secret Manager

```yaml
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
    service_account: ${{ secrets.SERVICE_ACCOUNT }}

- id: secrets
  uses: google-github-actions/get-secretmanager-secrets@v1
  with:
    secrets: |-
      db-password:projects/PROJECT_ID/secrets/db-password
      api-key:projects/PROJECT_ID/secrets/api-key

- run: ./deploy.sh
  env:
    DB_PASSWORD: '${{ steps.secrets.outputs.db-password }}'
    API_KEY: '${{ steps.secrets.outputs.api-key }}'
```

### OIDC Authentication

**Benefits**:
- No long-lived credentials
- Automatic rotation
- Fine-grained permissions
- Audit trail

**Setup for AWS**:

1. **Create OIDC provider in AWS**:
```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

2. **Create IAM role**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:*"
        }
      }
    }
  ]
}
```

3. **Use in workflow**:
```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
    aws-region: us-east-1
```

---

## Deployment Automation

### Deployment Strategies

#### Rolling Deployment

```yaml
deploy-rolling:
  runs-on: ubuntu-latest
  steps:
    - name: Rolling update
      run: |
        kubectl set image deployment/myapp \
          myapp=${{ env.IMAGE }} \
          -n production

        kubectl rollout status deployment/myapp -n production

        # Check health
        kubectl get pods -n production -l app=myapp
```

#### Blue-Green Deployment

```yaml
deploy-blue-green:
  runs-on: ubuntu-latest
  steps:
    - name: Determine colors
      id: colors
      run: |
        CURRENT=$(kubectl get service myapp -n prod -o jsonpath='{.spec.selector.color}')
        NEW=$([ "$CURRENT" = "blue" ] && echo "green" || echo "blue")
        echo "current=$CURRENT" >> $GITHUB_OUTPUT
        echo "new=$NEW" >> $GITHUB_OUTPUT

    - name: Deploy new version
      run: |
        kubectl set image deployment/myapp-${{ steps.colors.outputs.new }} \
          myapp=${{ env.IMAGE }} -n prod
        kubectl rollout status deployment/myapp-${{ steps.colors.outputs.new }} -n prod

    - name: Verify new version
      run: |
        POD=$(kubectl get pod -n prod -l app=myapp,color=${{ steps.colors.outputs.new }} -o jsonpath='{.items[0].metadata.name}')
        kubectl exec -n prod $POD -- curl -f http://localhost/health

    - name: Switch traffic
      run: |
        kubectl patch service myapp -n prod -p '{"spec":{"selector":{"color":"${{ steps.colors.outputs.new }}"}}}'

    - name: Monitor for 5 minutes
      run: |
        sleep 300
        # Check error rates from monitoring system

    - name: Cleanup old version
      run: |
        kubectl scale deployment/myapp-${{ steps.colors.outputs.current }} -n prod --replicas=0
```

#### Canary Deployment

```yaml
deploy-canary:
  runs-on: ubuntu-latest
  steps:
    - name: Deploy canary (10%)
      run: |
        kubectl apply -f k8s/canary.yml
        kubectl set image deployment/myapp-canary myapp=${{ env.IMAGE }} -n prod
        kubectl rollout status deployment/myapp-canary -n prod

    - name: Monitor canary
      run: |
        for i in {1..10}; do
          ERROR_RATE=$(curl -s "http://prometheus/api/v1/query?query=rate(http_requests_total{deployment=\"canary\",status=~\"5..\"}[5m])" | jq -r '.data.result[0].value[1]')
          if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
            echo "Canary error rate too high: $ERROR_RATE"
            kubectl rollout undo deployment/myapp-canary -n prod
            exit 1
          fi
          sleep 60
        done

    - name: Promote canary (50%)
      run: |
        kubectl scale deployment/myapp-canary -n prod --replicas=5
        kubectl scale deployment/myapp -n prod --replicas=5
        sleep 300

    - name: Promote canary (100%)
      run: |
        kubectl set image deployment/myapp myapp=${{ env.IMAGE }} -n prod
        kubectl rollout status deployment/myapp -n prod
        kubectl delete deployment myapp-canary -n prod
```

### Platform-Specific Deployments

#### Kubernetes

```yaml
deploy-k8s:
  runs-on: ubuntu-latest
  steps:
    - uses: azure/setup-kubectl@v3
      with:
        version: 'v1.28.0'

    - uses: azure/k8s-set-context@v3
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBE_CONFIG }}

    - name: Deploy with Kustomize
      run: |
        cd k8s/overlays/production
        kustomize edit set image myapp=${{ env.IMAGE }}
        kustomize build . | kubectl apply -f -

    - name: Verify deployment
      run: |
        kubectl rollout status deployment/myapp -n production
        kubectl get pods -n production -l app=myapp
```

#### AWS ECS

```yaml
deploy-ecs:
  runs-on: ubuntu-latest
  steps:
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: ${{ secrets.AWS_ROLE }}
        aws-region: us-east-1

    - name: Deploy to ECS
      run: |
        # Update task definition
        TASK_DEFINITION=$(aws ecs describe-task-definition --task-definition myapp --query taskDefinition)
        NEW_TASK_DEF=$(echo $TASK_DEFINITION | jq --arg IMAGE "${{ env.IMAGE }}" '.containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)')

        # Register new task definition
        NEW_TASK_ARN=$(aws ecs register-task-definition --cli-input-json "$NEW_TASK_DEF" --query 'taskDefinition.taskDefinitionArn' --output text)

        # Update service
        aws ecs update-service \
          --cluster production \
          --service myapp \
          --task-definition $NEW_TASK_ARN \
          --force-new-deployment

        # Wait for service stability
        aws ecs wait services-stable \
          --cluster production \
          --services myapp
```

#### Google Cloud Run

```yaml
deploy-cloud-run:
  runs-on: ubuntu-latest
  steps:
    - uses: google-github-actions/auth@v2
      with:
        workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
        service_account: ${{ secrets.SERVICE_ACCOUNT }}

    - name: Deploy to Cloud Run
      uses: google-github-actions/deploy-cloudrun@v2
      with:
        service: myapp
        image: ${{ env.IMAGE }}
        region: us-central1
        flags: |
          --port=8080
          --memory=512Mi
          --cpu=1
          --max-instances=10
          --allow-unauthenticated
```

#### Azure App Service

```yaml
deploy-azure:
  runs-on: ubuntu-latest
  steps:
    - uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}

    - uses: azure/webapps-deploy@v2
      with:
        app-name: 'myapp'
        images: ${{ env.IMAGE }}
```

### Rollback Procedures

```yaml
rollback:
  runs-on: ubuntu-latest
  if: failure()
  steps:
    - name: Rollback Kubernetes
      run: |
        kubectl rollout undo deployment/myapp -n production
        kubectl rollout status deployment/myapp -n production

    - name: Notify team
      uses: slackapi/slack-github-action@v1
      with:
        payload: |
          {
            "text": "Deployment rolled back",
            "blocks": [
              {
                "type": "section",
                "text": {
                  "type": "mrkdwn",
                  "text": "Deployment to production was rolled back due to failures.\n*Repository*: ${{ github.repository }}\n*Commit*: ${{ github.sha }}"
                }
              }
            ]
          }
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Pipeline as Code

### Modularity and Reuse

#### Template Actions (GitHub)

**Define template**:
```yaml
# .github/workflows/template-test.yml
name: Reusable Test Workflow

on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string
      test-command:
        required: false
        type: string
        default: 'npm test'
    outputs:
      coverage:
        description: "Test coverage percentage"
        value: ${{ jobs.test.outputs.coverage }}

jobs:
  test:
    runs-on: ubuntu-latest
    outputs:
      coverage: ${{ steps.coverage.outputs.percentage }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      - run: npm ci
      - run: ${{ inputs.test-command }}

      - id: coverage
        run: |
          COVERAGE=$(cat coverage/coverage-summary.json | jq -r '.total.lines.pct')
          echo "percentage=$COVERAGE" >> $GITHUB_OUTPUT
```

**Use template**:
```yaml
# .github/workflows/ci.yml
jobs:
  test-node-18:
    uses: ./.github/workflows/template-test.yml
    with:
      node-version: '18'

  test-node-20:
    uses: ./.github/workflows/template-test.yml
    with:
      node-version: '20'
      test-command: 'npm run test:ci'
```

#### Includes (GitLab)

**Define template** (`.gitlab/templates/deploy.yml`):
```yaml
.deploy-template:
  image: alpine:latest
  before_script:
    - apk add --no-cache kubectl
  script:
    - kubectl config use-context ${ENVIRONMENT}-cluster
    - kubectl set image deployment/myapp myapp=${IMAGE} -n ${ENVIRONMENT}
    - kubectl rollout status deployment/myapp -n ${ENVIRONMENT}

deploy:dev:
  extends: .deploy-template
  variables:
    ENVIRONMENT: dev
  environment:
    name: development

deploy:staging:
  extends: .deploy-template
  variables:
    ENVIRONMENT: staging
  environment:
    name: staging
  when: manual

deploy:production:
  extends: .deploy-template
  variables:
    ENVIRONMENT: production
  environment:
    name: production
  when: manual
  only:
    - main
```

**Use template** (`.gitlab-ci.yml`):
```yaml
include:
  - local: '.gitlab/templates/deploy.yml'

stages:
  - build
  - deploy

build:
  stage: build
  script:
    - docker build -t myapp:$CI_COMMIT_SHA .
```

#### Shared Libraries (Jenkins)

**Define library** (`vars/standardPipeline.groovy`):
```groovy
def call(Map config) {
    pipeline {
        agent any

        stages {
            stage('Build') {
                steps {
                    script {
                        sh config.buildCommand ?: 'npm run build'
                    }
                }
            }

            stage('Test') {
                steps {
                    script {
                        sh config.testCommand ?: 'npm test'
                    }
                }
            }

            stage('Deploy') {
                when {
                    branch config.deployBranch ?: 'main'
                }
                steps {
                    script {
                        sh "${config.deployScript} ${config.environment}"
                    }
                }
            }
        }
    }
}
```

**Use library** (Jenkinsfile):
```groovy
@Library('shared-pipeline-library') _

standardPipeline(
    buildCommand: 'npm run build',
    testCommand: 'npm run test:ci',
    deployScript: './deploy.sh',
    environment: 'production',
    deployBranch: 'main'
)
```

### Configuration Validation

**JSON Schema validation**:
```yaml
validate-config:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Validate pipeline config
      run: |
        npx ajv-cli validate \
          -s .github/schemas/pipeline.schema.json \
          -d .github/workflows/*.yml
```

**Linting**:
```yaml
lint-workflows:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Lint GitHub Actions workflows
      uses: docker://rhysd/actionlint:latest
      with:
        args: -color
```

---

## Monitoring and Observability

### Pipeline Metrics

**Build duration**:
```yaml
- name: Track build time
  run: |
    START_TIME=$(date +%s)
    npm run build
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Send to monitoring system
    curl -X POST https://metrics.example.com/pipeline \
      -H "Content-Type: application/json" \
      -d '{
        "metric": "build_duration_seconds",
        "value": '${DURATION}',
        "tags": {
          "repo": "'${GITHUB_REPOSITORY}'",
          "branch": "'${GITHUB_REF_NAME}'"
        }
      }'
```

**Test results**:
```yaml
- name: Publish test results
  uses: dorny/test-reporter@v1
  if: always()
  with:
    name: Test Results
    path: 'test-results/**/*.xml'
    reporter: java-junit
```

**Coverage tracking**:
```yaml
- uses: codecov/codecov-action@v3
  with:
    files: ./coverage/coverage-final.json
    flags: unit
    fail_ci_if_error: true
```

### Deployment Tracking

**Datadog**:
```yaml
- name: Track deployment
  run: |
    curl -X POST "https://api.datadoghq.com/api/v1/events" \
      -H "Content-Type: application/json" \
      -H "DD-API-KEY: ${{ secrets.DATADOG_API_KEY }}" \
      -d '{
        "title": "Deployed to production",
        "text": "Deployed version ${{ env.VERSION }}",
        "tags": [
          "env:production",
          "service:myapp",
          "version:${{ env.VERSION }}"
        ],
        "alert_type": "info"
      }'
```

**New Relic**:
```yaml
- name: Track deployment
  run: |
    curl -X POST "https://api.newrelic.com/v2/applications/${{ secrets.NEW_RELIC_APP_ID }}/deployments.json" \
      -H "Api-Key: ${{ secrets.NEW_RELIC_API_KEY }}" \
      -H "Content-Type: application/json" \
      -d '{
        "deployment": {
          "revision": "${{ github.sha }}",
          "changelog": "${{ github.event.head_commit.message }}",
          "description": "Deployed from GitHub Actions",
          "user": "${{ github.actor }}"
        }
      }'
```

**Sentry**:
```yaml
- name: Create Sentry release
  uses: getsentry/action-release@v1
  env:
    SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
    SENTRY_ORG: ${{ secrets.SENTRY_ORG }}
    SENTRY_PROJECT: ${{ secrets.SENTRY_PROJECT }}
  with:
    environment: production
    version: ${{ env.VERSION }}
```

### Build Notifications

**Slack**:
```yaml
- name: Notify Slack
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "Deployment ${{ job.status }}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Deployment Status*: ${{ job.status }}\n*Repository*: ${{ github.repository }}\n*Branch*: ${{ github.ref_name }}\n*Commit*: <${{ github.event.head_commit.url }}|${{ github.sha }}>\n*Actor*: ${{ github.actor }}"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

**Microsoft Teams**:
```yaml
- name: Notify Teams
  run: |
    curl -H 'Content-Type: application/json' \
      -d '{
        "@type": "MessageCard",
        "title": "Deployment Status",
        "text": "Deployment to production ${{ job.status }}",
        "themeColor": "${{ job.status == 'success' && '0078D4' || 'D13438' }}",
        "sections": [{
          "facts": [
            {"name": "Repository", "value": "${{ github.repository }}"},
            {"name": "Branch", "value": "${{ github.ref_name }}"},
            {"name": "Commit", "value": "${{ github.sha }}"},
            {"name": "Actor", "value": "${{ github.actor }}"}
          ]
        }]
      }' \
      ${{ secrets.TEAMS_WEBHOOK }}
```

---

## Performance Optimization

### Caching Strategies

**Dependency caching**:
```yaml
# Automatic
- uses: actions/setup-node@v4
  with:
    cache: 'npm'

# Manual
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

**Docker layer caching**:
```yaml
- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: myapp:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

**Build output caching**:
```yaml
- uses: actions/cache@v4
  with:
    path: |
      dist/
      .next/cache
    key: ${{ runner.os }}-build-${{ github.sha }}
    restore-keys: |
      ${{ runner.os }}-build-
```

### Parallelization

**Job-level parallelization**:
```yaml
jobs:
  test-unit:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:unit

  test-integration:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:integration

  test-e2e:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:e2e
```

**Test sharding**:
```yaml
test:
  runs-on: ubuntu-latest
  strategy:
    matrix:
      shard: [1, 2, 3, 4, 5, 6, 7, 8]
  steps:
    - run: npm test -- --shard=${{ matrix.shard }}/8
```

**Matrix builds**:
```yaml
test:
  runs-on: ${{ matrix.os }}
  strategy:
    matrix:
      os: [ubuntu-latest, macos-latest, windows-latest]
      node: [18, 20, 22]
  steps:
    - uses: actions/setup-node@v4
      with:
        node-version: ${{ matrix.node }}
    - run: npm test
```

### Resource Optimization

**Self-hosted runners**:
```yaml
jobs:
  build:
    runs-on: [self-hosted, linux, x64, high-memory]
    steps:
      - run: npm run build
```

**Conditional execution**:
```yaml
jobs:
  test:
    if: ${{ !contains(github.event.head_commit.message, '[skip ci]') }}
    steps:
      - run: npm test

  deploy:
    if: github.ref == 'refs/heads/main'
    steps:
      - run: ./deploy.sh
```

**Path filtering**:
```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'package.json'
      - 'package-lock.json'
    paths-ignore:
      - 'docs/**'
      - '**.md'
```

---

## Multi-Environment Promotion

### Environment Configuration

**GitHub Environments**:
```yaml
deploy-staging:
  runs-on: ubuntu-latest
  environment:
    name: staging
    url: https://staging.example.com
  steps:
    - run: ./deploy.sh staging

deploy-production:
  runs-on: ubuntu-latest
  environment:
    name: production
    url: https://example.com
  needs: [deploy-staging]
  steps:
    - run: ./deploy.sh production
```

**Environment Protection Rules**:
- Required reviewers
- Wait timer
- Deployment branches
- Environment secrets

### Approval Gates

**Manual approval** (GitHub):
```yaml
deploy-production:
  runs-on: ubuntu-latest
  environment:
    name: production  # Configure protection rules in GitHub
  steps:
    - run: ./deploy.sh production
```

**Manual approval** (GitLab):
```yaml
deploy:production:
  stage: deploy
  script:
    - ./deploy.sh production
  when: manual
  only:
    - main
```

**Manual approval** (Jenkins):
```groovy
stage('Deploy to Production') {
    steps {
        input message: 'Deploy to production?', ok: 'Deploy'
        sh './deploy.sh production'
    }
}
```

### Smoke Tests

```yaml
deploy-staging:
  runs-on: ubuntu-latest
  steps:
    - name: Deploy
      run: ./deploy.sh staging

    - name: Wait for deployment
      run: sleep 30

    - name: Smoke tests
      run: |
        # Health check
        curl -f https://staging.example.com/health

        # Critical endpoints
        curl -f https://staging.example.com/api/version
        curl -f https://staging.example.com/

        # Database connectivity
        curl -f https://staging.example.com/api/db/health

        # Run automated smoke tests
        npm run test:smoke -- --baseUrl=https://staging.example.com
```

---

## DORA Metrics

### Deployment Frequency

**Track deployments**:
```yaml
- name: Record deployment
  run: |
    curl -X POST https://metrics.example.com/deployments \
      -H "Content-Type: application/json" \
      -d '{
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "service": "myapp",
        "environment": "production",
        "version": "${{ env.VERSION }}",
        "commit": "${{ github.sha }}"
      }'
```

### Lead Time for Changes

**Calculate lead time**:
```yaml
- name: Calculate lead time
  run: |
    # Time from commit to deployment
    COMMIT_TIME=$(git show -s --format=%ct ${{ github.sha }})
    DEPLOY_TIME=$(date +%s)
    LEAD_TIME=$((DEPLOY_TIME - COMMIT_TIME))

    curl -X POST https://metrics.example.com/lead-time \
      -d "lead_time_seconds=${LEAD_TIME}&service=myapp"
```

### Change Failure Rate

**Track failures**:
```yaml
post-deploy-verify:
  needs: [deploy]
  runs-on: ubuntu-latest
  steps:
    - name: Verify deployment
      id: verify
      run: |
        # Check error rates
        ERROR_RATE=$(curl -s "http://prometheus/api/v1/query?query=rate(http_requests_total{status=~\"5..\"}[5m])")

        if [ "$ERROR_RATE" -gt "0.01" ]; then
          echo "Deployment failed verification"
          exit 1
        fi

    - name: Record outcome
      if: always()
      run: |
        STATUS=${{ steps.verify.outcome }}
        curl -X POST https://metrics.example.com/deployment-outcome \
          -d "status=${STATUS}&service=myapp&version=${{ env.VERSION }}"
```

### Time to Restore Service

**Track incidents**:
```yaml
- name: Rollback and track MTTR
  if: failure()
  run: |
    INCIDENT_START=$(date +%s)

    # Rollback
    kubectl rollout undo deployment/myapp -n production
    kubectl rollout status deployment/myapp -n production

    INCIDENT_END=$(date +%s)
    MTTR=$((INCIDENT_END - INCIDENT_START))

    curl -X POST https://metrics.example.com/mttr \
      -d "mttr_seconds=${MTTR}&service=myapp"
```

---

## Troubleshooting Guide

### Common Issues

#### Issue: Slow Pipeline Execution

**Symptoms**:
- Pipeline takes > 30 minutes
- Developers waiting for feedback

**Diagnosis**:
```bash
# Analyze job durations
gh run list --limit 10 --json databaseId,startedAt,updatedAt | \
  jq -r '.[] | "\(.databaseId) \((.updatedAt | fromdateiso8601) - (.startedAt | fromdateiso8601))s"'
```

**Solutions**:
1. Enable caching
2. Parallelize independent jobs
3. Use faster runners (self-hosted)
4. Shard tests
5. Skip unnecessary steps

#### Issue: Flaky Tests

**Symptoms**:
- Tests pass/fail intermittently
- Requires multiple re-runs

**Diagnosis**:
```bash
# Run tests multiple times
for i in {1..10}; do npm test || echo "Failed run $i"; done
```

**Solutions**:
1. Add retries for E2E tests
2. Increase timeouts
3. Fix race conditions
4. Isolate tests
5. Use deterministic data

#### Issue: Out of Disk Space

**Symptoms**:
- Build fails with "No space left on device"

**Diagnosis**:
```bash
df -h
docker system df
```

**Solutions**:
```yaml
- name: Clean up
  run: |
    docker system prune -af --volumes
    rm -rf node_modules
```

#### Issue: Secret Not Available

**Symptoms**:
- "secret not found" errors

**Diagnosis**:
- Check secret is defined in correct scope (org/repo/environment)
- Verify permissions

**Solutions**:
1. Add secret to correct scope
2. Check environment protection rules
3. Verify permissions

#### Issue: Rate Limiting

**Symptoms**:
- "API rate limit exceeded"

**Diagnosis**:
```bash
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit
```

**Solutions**:
1. Use authentication token
2. Cache API responses
3. Implement retry with exponential backoff

---

## Conclusion

This comprehensive reference covers all aspects of CI/CD pipeline design, implementation, and optimization. Key takeaways:

1. **Start simple, iterate**: Begin with basic pipelines and add complexity as needed
2. **Fail fast**: Run quick checks first to provide rapid feedback
3. **Security first**: Integrate security scanning throughout the pipeline
4. **Measure everything**: Track DORA metrics and pipeline performance
5. **Automate ruthlessly**: Eliminate manual steps wherever possible
6. **Monitor continuously**: Track deployments and verify success
7. **Document thoroughly**: Maintain runbooks and troubleshooting guides

For specific implementations, refer to the examples in the resources directory.
