# GitHub Actions - Comprehensive Reference

## Table of Contents
1. [GitHub Actions Fundamentals](#github-actions-fundamentals)
2. [Workflow Architecture](#workflow-architecture)
3. [Workflow Syntax](#workflow-syntax)
4. [Triggers and Events](#triggers-and-events)
5. [Jobs and Steps](#jobs-and-steps)
6. [Runners and Environments](#runners-and-environments)
7. [Contexts and Expressions](#contexts-and-expressions)
8. [Actions and Marketplace](#actions-and-marketplace)
9. [Caching Strategies](#caching-strategies)
10. [Artifacts and Storage](#artifacts-and-storage)
11. [Matrix Builds](#matrix-builds)
12. [Reusable Workflows](#reusable-workflows)
13. [Composite Actions](#composite-actions)
14. [Security Best Practices](#security-best-practices)
15. [Performance Optimization](#performance-optimization)
16. [Monorepo Strategies](#monorepo-strategies)
17. [Common Patterns](#common-patterns)
18. [Anti-Patterns](#anti-patterns)
19. [Debugging and Troubleshooting](#debugging-and-troubleshooting)
20. [References](#references)

---

## GitHub Actions Fundamentals

### What is GitHub Actions?

GitHub Actions is a CI/CD platform integrated directly into GitHub repositories. It enables automation of build, test, and deployment workflows through event-driven execution.

**Core Benefits:**
- Native GitHub integration (no external CI/CD service needed)
- Event-driven automation (push, PR, issues, releases, schedules)
- Extensive marketplace with 10,000+ pre-built actions
- Matrix builds for multi-platform/multi-version testing
- Free tier: 2,000 minutes/month for private repos, unlimited for public repos
- Self-hosted runners for custom environments

### Key Components

```
Repository
  ↓
.github/workflows/*.yml (Workflow files)
  ↓
Triggers (Events that start workflows)
  ↓
Jobs (Independent execution units)
  ↓
Steps (Sequential commands/actions)
  ↓
Actions (Reusable code units)
  ↓
Runners (VMs that execute jobs)
```

### Execution Model

**Workflow Lifecycle:**
1. **Trigger**: Event occurs (push, PR, schedule, manual)
2. **Queue**: Workflow queued for available runner
3. **Execute**: Runner pulls code, sets up environment, runs jobs
4. **Jobs**: Execute in parallel by default (unless dependencies specified)
5. **Steps**: Execute sequentially within each job
6. **Complete**: Results, logs, and artifacts stored

**Parallelization:**
- Jobs run in parallel by default
- Steps within a job run sequentially
- Matrix builds create multiple job instances
- Concurrency controls prevent duplicate runs

### Pricing and Limits

**Free Tier (Public Repos):**
- Unlimited minutes
- 20 concurrent jobs
- Matrix jobs count toward concurrency

**Free Tier (Private Repos):**
- 2,000 minutes/month
- 20 concurrent jobs
- Additional minutes: $0.008/minute (Linux)

**Usage Limits:**
- Workflow run time: 35 days max
- Job execution time: 6 hours max
- API requests: 1,000/hour per repository
- Workflow run queue: 500 pending runs
- Artifact storage: 500 MB per artifact, 2 GB total (free tier)
- Artifact retention: 90 days default (configurable)

**Runner Minutes Multipliers:**
- Linux: 1x
- Windows: 2x
- macOS: 10x

**Best Practices for Free Tier:**
- Use Linux runners when possible (cheapest)
- Implement aggressive caching
- Use path filters to avoid unnecessary runs
- Cancel redundant workflow runs
- Optimize matrix builds

---

## Workflow Architecture

### Basic Structure

Every workflow is a YAML file in `.github/workflows/`:

```yaml
name: Workflow Name
on: [triggers]
env:
  GLOBAL_VAR: value
jobs:
  job-id:
    runs-on: ubuntu-latest
    env:
      JOB_VAR: value
    steps:
      - name: Step name
        env:
          STEP_VAR: value
        run: command
```

### Workflow Organization

**Single Repository Patterns:**

1. **Monolithic Workflow** (Simple projects):
```
.github/
  workflows/
    main.yml        # All CI/CD in one file
```

2. **Separated Workflows** (Standard projects):
```
.github/
  workflows/
    ci.yml          # Build and test
    cd-staging.yml  # Deploy to staging
    cd-prod.yml     # Deploy to production
    security.yml    # Security scans
    release.yml     # Release automation
```

3. **Modular with Reusable Workflows** (Large projects):
```
.github/
  workflows/
    _reusable-test.yml      # Reusable test workflow
    _reusable-deploy.yml    # Reusable deploy workflow
    pr.yml                  # PR validation (calls _reusable-test.yml)
    main.yml                # Main branch CI/CD
    release.yml             # Release workflow
  actions/
    setup-app/              # Custom composite action
      action.yml
```

**Monorepo Patterns:**

```
.github/
  workflows/
    backend-ci.yml          # Backend testing
    frontend-ci.yml         # Frontend testing
    services-deploy.yml     # Service deployments
    _reusable-deploy.yml    # Shared deployment logic
  actions/
    detect-changes/         # Path-based change detection
    setup-monorepo/         # Monorepo setup
```

### Naming Conventions

**Workflow Files:**
- Use descriptive, hyphenated names: `ci-backend.yml`, `deploy-staging.yml`
- Prefix reusable workflows with `_`: `_reusable-test.yml`
- Group by purpose: `ci-*.yml`, `cd-*.yml`, `security-*.yml`

**Job IDs:**
- Use hyphenated lowercase: `build-backend`, `test-unit`, `deploy-prod`
- Be descriptive and specific
- Group related jobs: `test-unit`, `test-integration`, `test-e2e`

**Step Names:**
- Use sentence case: "Install dependencies", "Run tests"
- Be specific about what the step does
- Include version/platform when relevant: "Setup Node.js 20"

### Workflow Dependencies

**Job Dependencies:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps: [...]

  test:
    needs: build  # Wait for build
    steps: [...]

  deploy:
    needs: [build, test]  # Wait for both
    steps: [...]
```

**Workflow Chaining:**
```yaml
# workflow-1.yml
name: Build
on: [push]
jobs:
  build:
    steps:
      - run: npm run build
      - name: Trigger deployment
        run: |
          gh workflow run deploy.yml \
            --ref ${{ github.ref }}

# workflow-2.yml (deploy.yml)
name: Deploy
on:
  workflow_dispatch:  # Manual or API trigger
jobs:
  deploy:
    steps: [...]
```

---

## Workflow Syntax

### Complete Syntax Example

```yaml
name: Complete Workflow Example

# Workflow-level configuration
run-name: CI for ${{ github.ref_name }}

# Trigger configuration
on:
  push:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'tests/**'
  pull_request:
    types: [opened, synchronize]
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options: [staging, production]

# Workflow-level permissions
permissions:
  contents: read
  pull-requests: write

# Global environment variables
env:
  NODE_VERSION: '20'
  CACHE_VERSION: v1

# Concurrency control
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

# Default settings for all jobs
defaults:
  run:
    shell: bash
    working-directory: ./app

jobs:
  build:
    name: Build Application
    runs-on: ubuntu-latest
    timeout-minutes: 30

    # Job-level permissions
    permissions:
      contents: read
      packages: write

    # Job-level environment variables
    env:
      BUILD_ENV: production

    # Job outputs
    outputs:
      version: ${{ steps.version.outputs.version }}
      cache-key: ${{ steps.cache.outputs.cache-key }}

    # Service containers
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Get version
        id: version
        run: echo "version=$(node -p "require('./package.json').version")" >> $GITHUB_OUTPUT

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
          retention-days: 7

  test:
    needs: build
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        node: [18, 20]
        exclude:
          - os: macos-latest
            node: 18
      fail-fast: false
      max-parallel: 4

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}

      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/

      - name: Run tests
        run: npm test
        continue-on-error: ${{ matrix.node == '18' }}

      - name: Upload coverage
        if: success() && matrix.os == 'ubuntu-latest' && matrix.node == '20'
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
```

### Workflow Name and Run Name

```yaml
# Static name (shown in Actions tab)
name: CI Pipeline

# Dynamic run name (shown in runs list)
run-name: Deploy to ${{ inputs.environment }} by @${{ github.actor }}
```

### Permissions

**Available Permissions:**
```yaml
permissions:
  actions: read|write|none        # GitHub Actions
  checks: read|write|none         # Checks API
  contents: read|write|none       # Repository contents
  deployments: read|write|none    # Deployments
  discussions: read|write|none    # Discussions
  id-token: write                 # OIDC tokens
  issues: read|write|none         # Issues
  packages: read|write|none       # GitHub Packages
  pages: read|write|none          # GitHub Pages
  pull-requests: read|write|none  # Pull requests
  repository-projects: read|write|none  # Projects
  security-events: read|write|none      # Security events
  statuses: read|write|none       # Commit statuses
```

**Best Practice - Principle of Least Privilege:**
```yaml
# Workflow-level: Minimal permissions
permissions:
  contents: read

jobs:
  deploy:
    # Job-level: Only what's needed
    permissions:
      contents: read
      packages: write
      id-token: write  # For OIDC
    steps: [...]
```

### Concurrency

**Prevent Concurrent Runs:**
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

**Common Patterns:**

1. **Per Branch:**
```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

2. **Per PR:**
```yaml
concurrency:
  group: pr-${{ github.event.pull_request.number }}
  cancel-in-progress: true
```

3. **Per Environment:**
```yaml
concurrency:
  group: deploy-${{ inputs.environment }}
  cancel-in-progress: false  # Don't cancel deployments
```

4. **Global Lock:**
```yaml
concurrency:
  group: production-deploy
  cancel-in-progress: false
```

### Defaults

**Run Defaults:**
```yaml
defaults:
  run:
    shell: bash
    working-directory: ./app
```

**Available Shells:**
- `bash` (Linux/macOS default)
- `pwsh` (PowerShell Core)
- `python`
- `sh` (Linux/macOS)
- `cmd` (Windows)
- `powershell` (Windows)

---

## Triggers and Events

### Push Events

**Basic:**
```yaml
on: push
```

**Branch Filters:**
```yaml
on:
  push:
    branches:
      - main
      - develop
      - 'releases/**'      # Wildcard
      - '!experimental/**' # Exclude
```

**Tag Filters:**
```yaml
on:
  push:
    tags:
      - 'v*'              # v1.0.0, v2.1.3
      - 'v[0-9]+.[0-9]+'  # Regex pattern
```

**Path Filters:**
```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
      - '!docs/**'        # Exclude docs
```

**Combined Filters:**
```yaml
on:
  push:
    branches:
      - main
    paths:
      - 'backend/**'
      - '!backend/docs/**'
```

### Pull Request Events

**Basic:**
```yaml
on: pull_request
```

**Activity Types:**
```yaml
on:
  pull_request:
    types:
      - opened          # PR opened
      - synchronize     # New commits pushed
      - reopened        # PR reopened
      - ready_for_review # Draft → Ready
      - converted_to_draft
      - labeled
      - unlabeled
```

**Common Pattern (CI on PRs):**
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main, develop]
```

**Pull Request Target (Fork PRs):**
```yaml
on:
  pull_request_target:  # Runs in base repo context (has secrets access)
    types: [opened, synchronize]
```

**SECURITY WARNING:** `pull_request_target` runs with write permissions and access to secrets. Never checkout PR code directly. Use with extreme caution.

### Scheduled Events

**Cron Syntax:**
```yaml
on:
  schedule:
    - cron: '0 2 * * *'        # Daily at 2 AM UTC
    - cron: '0 */4 * * *'      # Every 4 hours
    - cron: '0 0 * * 0'        # Weekly on Sunday
    - cron: '0 0 1 * *'        # Monthly on 1st
```

**Cron Format:**
```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

**Common Schedules:**
```yaml
# Weekdays at 9 AM UTC
- cron: '0 9 * * 1-5'

# Every 30 minutes
- cron: '*/30 * * * *'

# First day of quarter at midnight
- cron: '0 0 1 1,4,7,10 *'
```

**Important:** Scheduled workflows run on the default branch only.

### Manual Triggers (workflow_dispatch)

**Basic:**
```yaml
on:
  workflow_dispatch:
```

**With Inputs:**
```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - staging
          - production

      version:
        description: 'Version to deploy'
        required: true
        type: string

      dry_run:
        description: 'Run in dry-run mode'
        required: false
        type: boolean
        default: false

      log_level:
        description: 'Log level'
        required: false
        type: choice
        options: [debug, info, warning, error]
        default: 'info'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy
        env:
          ENVIRONMENT: ${{ inputs.environment }}
          VERSION: ${{ inputs.version }}
          DRY_RUN: ${{ inputs.dry_run }}
          LOG_LEVEL: ${{ inputs.log_level }}
        run: |
          echo "Deploying $VERSION to $ENVIRONMENT"
          if [[ "$DRY_RUN" == "true" ]]; then
            echo "DRY RUN MODE"
          fi
```

**Input Types:**
- `string`: Text input
- `boolean`: Checkbox
- `choice`: Dropdown menu
- `environment`: GitHub environment selector

### Reusable Workflow Triggers (workflow_call)

```yaml
on:
  workflow_call:
    inputs:
      config-path:
        required: true
        type: string
      environment:
        required: false
        type: string
        default: 'production'

    secrets:
      api-key:
        required: true
      database-url:
        required: false

    outputs:
      deployment-id:
        description: "Deployment ID"
        value: ${{ jobs.deploy.outputs.deployment-id }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    outputs:
      deployment-id: ${{ steps.deploy.outputs.id }}
    steps:
      - name: Deploy
        id: deploy
        env:
          API_KEY: ${{ secrets.api-key }}
          CONFIG: ${{ inputs.config-path }}
        run: ./deploy.sh
```

### Other Events

**Release Events:**
```yaml
on:
  release:
    types: [published, created, edited, deleted]
```

**Issue Events:**
```yaml
on:
  issues:
    types: [opened, labeled, assigned]
```

**Issue Comment Events:**
```yaml
on:
  issue_comment:
    types: [created, edited]
```

**Repository Dispatch (API-triggered):**
```yaml
on:
  repository_dispatch:
    types: [deploy-production, backup-database]
```

**Multiple Events:**
```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:
```

### Event Filters

**Path Filters:**
```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
      - 'package.json'
      - '!**/*.md'          # Exclude markdown
      - '!docs/**'          # Exclude docs directory
```

**Branch Filters:**
```yaml
on:
  pull_request:
    branches:
      - main
      - develop
      - 'release/**'        # Wildcard
      - '!experimental/**'  # Exclude
```

---

## Jobs and Steps

### Job Configuration

**Basic Job:**
```yaml
jobs:
  job-id:
    name: Human-Readable Name
    runs-on: ubuntu-latest
    steps:
      - run: echo "Hello"
```

**Complete Job Configuration:**
```yaml
jobs:
  build:
    name: Build Application
    runs-on: ubuntu-latest
    timeout-minutes: 30
    continue-on-error: false

    # Job conditions
    if: github.event_name == 'push'

    # Job dependencies
    needs: [setup, lint]

    # Job strategy
    strategy:
      matrix:
        node: [18, 20]
      fail-fast: false

    # Job permissions
    permissions:
      contents: read
      packages: write

    # Job environment
    environment:
      name: production
      url: https://example.com

    # Job outputs
    outputs:
      version: ${{ steps.version.outputs.version }}

    # Job environment variables
    env:
      NODE_ENV: production

    # Job defaults
    defaults:
      run:
        shell: bash
        working-directory: ./app

    steps: [...]
```

### Step Configuration

**Run Command:**
```yaml
steps:
  - name: Run command
    run: echo "Hello World"
```

**Multi-line Command:**
```yaml
steps:
  - name: Multi-line script
    run: |
      echo "Line 1"
      echo "Line 2"
      npm install
      npm test
```

**Using Actions:**
```yaml
steps:
  - name: Checkout code
    uses: actions/checkout@v4
    with:
      fetch-depth: 0
      ref: main
```

**Complete Step Configuration:**
```yaml
steps:
  - name: Step Name
    id: step-id
    if: success()
    uses: actions/checkout@v4
    with:
      fetch-depth: 0
    env:
      VAR: value
    continue-on-error: false
    timeout-minutes: 10
    working-directory: ./app
    shell: bash
```

### Step Conditions

**Status Functions:**
```yaml
steps:
  - name: Always run
    if: always()
    run: echo "Cleanup"

  - name: On success
    if: success()
    run: echo "Tests passed"

  - name: On failure
    if: failure()
    run: echo "Tests failed"

  - name: On cancellation
    if: cancelled()
    run: echo "Workflow cancelled"
```

**Complex Conditions:**
```yaml
steps:
  - name: Deploy to production
    if: |
      github.ref == 'refs/heads/main' &&
      github.event_name == 'push' &&
      !contains(github.event.head_commit.message, '[skip ci]')
    run: ./deploy.sh

  - name: Deploy to staging
    if: github.ref == 'refs/heads/develop' && success()
    run: ./deploy.sh staging
```

**Check Previous Step:**
```yaml
steps:
  - name: Build
    id: build
    run: npm run build

  - name: Deploy
    if: steps.build.outcome == 'success'
    run: ./deploy.sh
```

### Job Dependencies

**Sequential:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps: [...]

  test:
    needs: build
    runs-on: ubuntu-latest
    steps: [...]

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps: [...]
```

**Parallel with Convergence:**
```yaml
jobs:
  test-unit:
    runs-on: ubuntu-latest
    steps: [...]

  test-integration:
    runs-on: ubuntu-latest
    steps: [...]

  test-e2e:
    runs-on: ubuntu-latest
    steps: [...]

  deploy:
    needs: [test-unit, test-integration, test-e2e]
    runs-on: ubuntu-latest
    steps: [...]
```

**Conditional Dependencies:**
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps: [...]

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps: [...]
```

### Job Outputs

**Define Outputs:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
      artifact-id: ${{ steps.upload.outputs.artifact-id }}

    steps:
      - name: Get version
        id: version
        run: echo "version=$(cat VERSION)" >> $GITHUB_OUTPUT

      - name: Upload artifact
        id: upload
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ github.sha }}
          path: dist/
```

**Use Outputs:**
```yaml
jobs:
  build:
    outputs:
      version: ${{ steps.version.outputs.version }}
    steps: [...]

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy version
        run: |
          echo "Deploying version ${{ needs.build.outputs.version }}"
          ./deploy.sh ${{ needs.build.outputs.version }}
```

### Service Containers

**PostgreSQL:**
```yaml
jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Run tests
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/testdb
        run: npm test
```

**Redis:**
```yaml
services:
  redis:
    image: redis:7
    ports:
      - 6379:6379
    options: >-
      --health-cmd "redis-cli ping"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

**Multiple Services:**
```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_PASSWORD: postgres
    ports:
      - 5432:5432

  redis:
    image: redis:7
    ports:
      - 6379:6379

  elasticsearch:
    image: elasticsearch:8.10.0
    env:
      discovery.type: single-node
      xpack.security.enabled: false
    ports:
      - 9200:9200
```

---

## Runners and Environments

### GitHub-Hosted Runners

**Available Runners:**
```yaml
runs-on: ubuntu-latest          # Ubuntu 22.04 (most common)
runs-on: ubuntu-20.04           # Ubuntu 20.04
runs-on: macos-latest           # macOS 12 (Monterey)
runs-on: macos-13               # macOS 13 (Ventura)
runs-on: macos-14               # macOS 14 (Sonoma, M1)
runs-on: windows-latest         # Windows Server 2022
runs-on: windows-2019           # Windows Server 2019
```

**Larger Runners (Team/Enterprise):**
```yaml
runs-on: ubuntu-latest-4-cores  # 4 vCPU, 16 GB RAM
runs-on: ubuntu-latest-8-cores  # 8 vCPU, 32 GB RAM
runs-on: ubuntu-latest-16-cores # 16 vCPU, 64 GB RAM
```

**Runner Specifications:**

| OS | vCPU | RAM | Storage | Cost Multiplier |
|----|------|-----|---------|-----------------|
| Ubuntu | 2 | 7 GB | 14 GB SSD | 1x |
| Windows | 2 | 7 GB | 14 GB SSD | 2x |
| macOS | 3 | 14 GB | 14 GB SSD | 10x |

**Pre-installed Software:**
- Language runtimes (Node.js, Python, Ruby, Go, Java, PHP, Rust)
- Package managers (npm, pip, gem, cargo, maven, gradle)
- Version control (git, gh CLI)
- Databases (PostgreSQL, MySQL, MongoDB, Redis)
- Tools (Docker, kubectl, helm, terraform, az, aws, gcloud)

Full list: https://github.com/actions/runner-images

### Self-Hosted Runners

**Setup:**
```bash
# On your server
./config.sh --url https://github.com/owner/repo --token TOKEN
./run.sh
```

**Use in Workflow:**
```yaml
jobs:
  build:
    runs-on: [self-hosted, linux, x64]
    steps: [...]
```

**Labels:**
```yaml
# Multiple labels (AND logic)
runs-on: [self-hosted, linux, gpu, high-memory]
```

**Best Practices:**
- Use ephemeral runners (one job, then destroy)
- Never use self-hosted runners for public repos
- Isolate runner environment (containers/VMs)
- Regular security updates
- Monitor runner health and capacity

### Environments

**Define Environment:**
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com

    steps:
      - name: Deploy
        run: ./deploy.sh
```

**Environment with Conditions:**
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
      url: ${{ steps.deploy.outputs.url }}

    steps:
      - name: Deploy
        id: deploy
        run: ./deploy.sh
```

**Environment Features:**
- Required reviewers (manual approval gates)
- Wait timer (delay before deployment)
- Environment secrets (scoped to environment)
- Deployment branches (restrict which branches can deploy)
- Protection rules

**Access Environment Secrets:**
```yaml
jobs:
  deploy:
    environment: production
    steps:
      - name: Deploy
        env:
          API_KEY: ${{ secrets.API_KEY }}  # Environment secret
        run: ./deploy.sh
```

---

## Contexts and Expressions

### Context Objects

**`github` Context:**
```yaml
${{ github.event_name }}         # Event that triggered workflow
${{ github.ref }}                # Branch/tag ref (refs/heads/main)
${{ github.ref_name }}           # Branch/tag name (main)
${{ github.sha }}                # Commit SHA
${{ github.actor }}              # User who triggered
${{ github.repository }}         # owner/repo
${{ github.repository_owner }}   # owner
${{ github.run_id }}             # Workflow run ID
${{ github.run_number }}         # Workflow run number (incremental)
${{ github.job }}                # Current job ID
${{ github.action }}             # Current action
${{ github.workflow }}           # Workflow name
${{ github.event.pull_request.number }}  # PR number
${{ github.event.pull_request.head.ref }} # PR branch
${{ github.event.head_commit.message }}  # Commit message
```

**`env` Context:**
```yaml
${{ env.NODE_VERSION }}          # Environment variable
${{ env.PATH }}                  # System PATH
```

**`secrets` Context:**
```yaml
${{ secrets.API_KEY }}           # Repository secret
${{ secrets.GITHUB_TOKEN }}      # Automatic token
```

**`runner` Context:**
```yaml
${{ runner.os }}                 # Linux, Windows, macOS
${{ runner.arch }}               # X64, ARM, ARM64
${{ runner.name }}               # Runner name
${{ runner.temp }}               # Temp directory path
${{ runner.tool_cache }}         # Tool cache directory
```

**`job` Context:**
```yaml
${{ job.status }}                # Job status
${{ job.container }}             # Container info
${{ job.services }}              # Service containers
```

**`steps` Context:**
```yaml
${{ steps.step-id.outputs.version }}     # Step output
${{ steps.step-id.outcome }}             # success, failure, cancelled
${{ steps.step-id.conclusion }}          # success, failure, cancelled, skipped
```

**`needs` Context:**
```yaml
${{ needs.build.result }}        # Job result
${{ needs.build.outputs.version }} # Job output
```

**`inputs` Context (workflow_dispatch/workflow_call):**
```yaml
${{ inputs.environment }}        # Input value
${{ inputs.dry_run }}            # Boolean input
```

**`matrix` Context:**
```yaml
${{ matrix.os }}                 # Matrix value
${{ matrix.node }}               # Matrix value
```

### Expression Syntax

**Operators:**
```yaml
# Comparison
${{ 1 == 1 }}                    # Equality
${{ 1 != 2 }}                    # Inequality
${{ 5 > 3 }}                     # Greater than
${{ 5 < 10 }}                    # Less than
${{ 5 >= 5 }}                    # Greater or equal
${{ 5 <= 5 }}                    # Less or equal

# Logical
${{ true && false }}             # AND
${{ true || false }}             # OR
${{ !false }}                    # NOT

# String
${{ 'hello' == 'hello' }}        # String equality
${{ contains('hello world', 'hello') }}  # Substring
${{ startsWith('hello', 'hel') }} # Starts with
${{ endsWith('hello', 'lo') }}    # Ends with
${{ format('Hello {0}', 'World') }} # Format string
```

**Functions:**
```yaml
# Status functions
if: success()                    # Previous steps succeeded
if: failure()                    # Previous step failed
if: always()                     # Always run
if: cancelled()                  # Workflow cancelled

# String functions
${{ contains('hello world', 'hello') }}  # true
${{ startsWith('hello', 'hel') }}        # true
${{ endsWith('hello', 'lo') }}           # true
${{ format('v{0}.{1}', 1, 0) }}          # v1.0

# JSON functions
${{ toJSON(github.event) }}      # Convert to JSON string
${{ fromJSON('{"a":1}') }}       # Parse JSON string

# Hash function
${{ hashFiles('**/package-lock.json') }}  # Hash files
${{ hashFiles('Cargo.lock') }}            # Single file hash
```

**Complex Expressions:**
```yaml
steps:
  - name: Deploy
    if: |
      github.ref == 'refs/heads/main' &&
      github.event_name == 'push' &&
      !contains(github.event.head_commit.message, '[skip ci]') &&
      (success() || failure())
    run: ./deploy.sh
```

### Setting Outputs

**GITHUB_OUTPUT (Current Method):**
```yaml
steps:
  - name: Set output
    id: vars
    run: |
      echo "version=1.0.0" >> $GITHUB_OUTPUT
      echo "date=$(date +'%Y-%m-%d')" >> $GITHUB_OUTPUT

  - name: Use output
    run: |
      echo "Version: ${{ steps.vars.outputs.version }}"
      echo "Date: ${{ steps.vars.outputs.date }}"
```

**Multiline Outputs:**
```yaml
steps:
  - name: Set multiline output
    id: multiline
    run: |
      echo "content<<EOF" >> $GITHUB_OUTPUT
      cat CHANGELOG.md >> $GITHUB_OUTPUT
      echo "EOF" >> $GITHUB_OUTPUT

  - name: Use multiline output
    run: echo "${{ steps.multiline.outputs.content }}"
```

### Environment Variables

**Set Environment Variable:**
```yaml
steps:
  - name: Set env var
    run: |
      echo "MY_VAR=hello" >> $GITHUB_ENV
      echo "PATH=$HOME/bin:$PATH" >> $GITHUB_ENV

  - name: Use env var
    run: echo $MY_VAR
```

**Add to PATH:**
```yaml
steps:
  - name: Add to PATH
    run: echo "$HOME/bin" >> $GITHUB_PATH

  - name: Use new PATH
    run: which my-tool
```

---

## Actions and Marketplace

### Using Actions

**Basic Syntax:**
```yaml
steps:
  - name: Action name
    uses: owner/repo@version
    with:
      input1: value1
      input2: value2
```

**Version Specifications:**
```yaml
uses: actions/checkout@v4              # Major version (recommended)
uses: actions/checkout@v4.1.0          # Exact version
uses: actions/checkout@main            # Branch (not recommended)
uses: actions/checkout@{sha}           # Commit SHA (most secure)
```

**From Marketplace:**
```yaml
uses: actions/checkout@v4
uses: actions/setup-node@v4
uses: docker/build-push-action@v5
```

**From Same Repository:**
```yaml
uses: ./.github/actions/my-action
```

**From Private Repository:**
```yaml
uses: owner/private-repo/.github/actions/my-action@v1
```

### Essential Actions

**Checkout:**
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0           # Full history
    ref: main                # Specific branch
    token: ${{ secrets.PAT }} # Custom token
    submodules: recursive    # Clone submodules
```

**Setup Languages:**
```yaml
# Node.js
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'

# Python
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'

# Java
- uses: actions/setup-java@v4
  with:
    distribution: 'temurin'
    java-version: '21'
    cache: 'maven'

# Go
- uses: actions/setup-go@v5
  with:
    go-version: '1.21'
    cache: true
```

**Cache:**
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

**Artifacts:**
```yaml
# Upload
- uses: actions/upload-artifact@v4
  with:
    name: dist
    path: dist/
    retention-days: 7
    if-no-files-found: error

# Download
- uses: actions/download-artifact@v4
  with:
    name: dist
    path: dist/
```

**GitHub CLI:**
```yaml
- name: Create issue
  run: |
    gh issue create \
      --title "Issue title" \
      --body "Issue body"
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Popular Third-Party Actions

**Docker:**
```yaml
- uses: docker/setup-buildx-action@v3
- uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKER_USERNAME }}
    password: ${{ secrets.DOCKER_PASSWORD }}

- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: user/repo:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

**AWS:**
```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
    aws-region: us-east-1

- uses: aws-actions/amazon-ecr-login@v2
```

**Code Quality:**
```yaml
# CodeQL (Security scanning)
- uses: github/codeql-action/init@v3
  with:
    languages: javascript, python

- uses: github/codeql-action/analyze@v3

# Codecov
- uses: codecov/codecov-action@v3
  with:
    files: ./coverage/lcov.info
    flags: unittests
```

**Deployment:**
```yaml
# Vercel
- uses: amondnet/vercel-action@v25
  with:
    vercel-token: ${{ secrets.VERCEL_TOKEN }}
    vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
    vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}

# Netlify
- uses: nwtgck/actions-netlify@v2
  with:
    publish-dir: ./dist
    production-deploy: true
  env:
    NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
    NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
```

### Creating Composite Actions

**action.yml:**
```yaml
name: 'Setup Node.js App'
description: 'Checkout, setup Node.js, install dependencies'
author: 'Your Name'

inputs:
  node-version:
    description: 'Node.js version'
    required: false
    default: '20'

  cache:
    description: 'Enable caching'
    required: false
    default: 'true'

outputs:
  cache-hit:
    description: 'Whether cache was hit'
    value: ${{ steps.cache.outputs.cache-hit }}

runs:
  using: 'composite'
  steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: ${{ inputs.cache == 'true' && 'npm' || '' }}

    - name: Install dependencies
      shell: bash
      run: npm ci

    - name: Cache check
      id: cache
      shell: bash
      run: echo "cache-hit=true" >> $GITHUB_OUTPUT
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

---

## Caching Strategies

### Cache Action

**Basic Cache:**
```yaml
- uses: actions/cache@v4
  with:
    path: node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

**Cache Hit Check:**
```yaml
- name: Cache dependencies
  id: cache
  uses: actions/cache@v4
  with:
    path: node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}

- name: Install dependencies
  if: steps.cache.outputs.cache-hit != 'true'
  run: npm ci
```

### Language-Specific Caching

**Node.js/npm:**
```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'  # Automatic caching

# Manual cache
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

**Python/pip:**
```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'  # Automatic caching

# Manual cache
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

**Rust/Cargo:**
```yaml
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
```

**Go:**
```yaml
- uses: actions/setup-go@v5
  with:
    go-version: '1.21'
    cache: true  # Automatic caching

# Manual cache
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/go-build
      ~/go/pkg/mod
    key: ${{ runner.os }}-go-${{ hashFiles('**/go.sum') }}
    restore-keys: |
      ${{ runner.os }}-go-
```

**Java/Maven:**
```yaml
- uses: actions/setup-java@v4
  with:
    distribution: 'temurin'
    java-version: '21'
    cache: 'maven'  # Automatic caching

# Manual cache
- uses: actions/cache@v4
  with:
    path: ~/.m2/repository
    key: ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}
    restore-keys: |
      ${{ runner.os }}-maven-
```

### Docker Layer Caching

**BuildKit Cache:**
```yaml
- uses: docker/setup-buildx-action@v3

- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: user/repo:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

**Registry Cache:**
```yaml
- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: user/repo:latest
    cache-from: type=registry,ref=user/repo:cache
    cache-to: type=registry,ref=user/repo:cache,mode=max
```

### Cache Management

**Cache Limits:**
- 10 GB per repository
- Caches not accessed in 7 days are evicted
- Caches on inactive branches deleted after 7 days

**Cache Keys Best Practices:**
```yaml
# Good: Specific, includes hash
key: ${{ runner.os }}-node-v1-${{ hashFiles('**/package-lock.json') }}

# Good: Multiple restore keys (fallback)
restore-keys: |
  ${{ runner.os }}-node-v1-
  ${{ runner.os }}-node-

# Bad: Too generic
key: node-modules

# Bad: No hash (won't update)
key: ${{ runner.os }}-node
```

**Version Cache Keys:**
```yaml
# Include cache version for manual invalidation
key: v2-${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
```

---

## Artifacts and Storage

### Upload Artifacts

**Basic Upload:**
```yaml
- uses: actions/upload-artifact@v4
  with:
    name: build-artifacts
    path: dist/
```

**Multiple Paths:**
```yaml
- uses: actions/upload-artifact@v4
  with:
    name: artifacts
    path: |
      dist/
      build/
      *.log
```

**Complete Configuration:**
```yaml
- uses: actions/upload-artifact@v4
  with:
    name: build-${{ github.sha }}
    path: |
      dist/
      !dist/**/*.map  # Exclude source maps
    retention-days: 7
    if-no-files-found: error  # error, warn, ignore
    compression-level: 6      # 0-9 (default: 6)
```

### Download Artifacts

**Download in Same Workflow:**
```yaml
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
          path: dist/

      - run: npm test
```

**Download All Artifacts:**
```yaml
- uses: actions/download-artifact@v4
  # No name specified = download all
```

**Download from Different Workflow:**
```yaml
- uses: dawidd6/action-download-artifact@v2
  with:
    workflow: build.yml
    workflow_conclusion: success
    name: dist
```

### Artifact Management

**Artifact Limits:**
- 500 MB per artifact (free tier)
- 2 GB total per workflow run (free tier)
- 90 days default retention
- Artifact storage counts toward storage quota

**Best Practices:**
```yaml
# Compress before upload
- run: tar -czf dist.tar.gz dist/

- uses: actions/upload-artifact@v4
  with:
    name: dist
    path: dist.tar.gz
    retention-days: 7  # Reduce retention

# Clean up large files to save storage
- run: |
    rm -rf node_modules  # Safe: cleaning CI cache
    rm -f *.log
```

### Release Assets

**Create Release with Assets:**
```yaml
- name: Create Release
  uses: softprops/action-gh-release@v1
  with:
    files: |
      dist/*.zip
      dist/*.tar.gz
      checksums.txt
    tag_name: v${{ steps.version.outputs.version }}
    name: Release v${{ steps.version.outputs.version }}
    body_path: CHANGELOG.md
    draft: false
    prerelease: false
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Matrix Builds

### Basic Matrix

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node: [18, 20, 22]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}

      - run: npm test
```

**This creates 9 jobs (3 OS × 3 Node versions)**

### Matrix with Exclusions

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    node: [18, 20, 22]
    exclude:
      # Don't test Node 18 on Windows
      - os: windows-latest
        node: 18

      # Don't test Node 22 on macOS
      - os: macos-latest
        node: 22
```

### Matrix with Inclusions

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest]
    node: [18, 20]
    include:
      # Add experimental Node 22 on Ubuntu
      - os: ubuntu-latest
        node: 22
        experimental: true

      # Add custom configuration
      - os: ubuntu-latest
        node: 20
        arch: arm64
```

**Using Experimental Flag:**
```yaml
steps:
  - run: npm test
    continue-on-error: ${{ matrix.experimental || false }}
```

### Matrix Configuration

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest]
    node: [18, 20]

  # Don't fail all jobs if one fails
  fail-fast: false

  # Limit concurrent jobs
  max-parallel: 4
```

### Complex Matrix

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    node: [18, 20]
    database: [postgres, mysql]

    exclude:
      # No MySQL on macOS
      - os: macos-latest
        database: mysql

    include:
      # Add Redis for Linux only
      - os: ubuntu-latest
        node: 20
        database: postgres
        cache: redis

steps:
  - name: Setup database
    run: |
      case "${{ matrix.database }}" in
        postgres) setup-postgres.sh ;;
        mysql) setup-mysql.sh ;;
      esac
```

### Matrix with Multiple Axes

```yaml
strategy:
  matrix:
    python: ['3.10', '3.11', '3.12']
    os: [ubuntu-latest, macos-latest]
    architecture: [x64, arm64]

    exclude:
      # ARM64 only on macOS 14
      - os: ubuntu-latest
        architecture: arm64

      - os: macos-latest
        architecture: arm64

    include:
      # Add macOS 14 for ARM64
      - os: macos-14
        python: '3.12'
        architecture: arm64
```

### Using Matrix Variables

```yaml
steps:
  - name: Display matrix info
    run: |
      echo "OS: ${{ matrix.os }}"
      echo "Node: ${{ matrix.node }}"
      echo "Runner OS: ${{ runner.os }}"

  - name: Platform-specific command
    run: |
      if [[ "${{ matrix.os }}" == "windows-latest" ]]; then
        dir
      else
        ls -la
      fi
```

---

## Reusable Workflows

### Creating Reusable Workflow

```yaml
# .github/workflows/_reusable-deploy.yml
name: Reusable Deploy

on:
  workflow_call:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        type: string

      region:
        description: 'AWS region'
        required: false
        type: string
        default: 'us-east-1'

      dry-run:
        description: 'Dry run mode'
        required: false
        type: boolean
        default: false

    secrets:
      aws-access-key-id:
        required: true
      aws-secret-access-key:
        required: true
      api-key:
        required: false

    outputs:
      deployment-id:
        description: 'Deployment ID'
        value: ${{ jobs.deploy.outputs.deployment-id }}

      deployment-url:
        description: 'Deployment URL'
        value: ${{ jobs.deploy.outputs.deployment-url }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}

    outputs:
      deployment-id: ${{ steps.deploy.outputs.id }}
      deployment-url: ${{ steps.deploy.outputs.url }}

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.aws-access-key-id }}
          aws-secret-access-key: ${{ secrets.aws-secret-access-key }}
          aws-region: ${{ inputs.region }}

      - name: Deploy
        id: deploy
        run: |
          if [[ "${{ inputs.dry-run }}" == "true" ]]; then
            echo "DRY RUN MODE"
          fi

          ./deploy.sh ${{ inputs.environment }}

          echo "id=deploy-$(date +%s)" >> $GITHUB_OUTPUT
          echo "url=https://${{ inputs.environment }}.example.com" >> $GITHUB_OUTPUT
```

### Calling Reusable Workflow

**From Same Repository:**
```yaml
# .github/workflows/deploy-staging.yml
name: Deploy to Staging

on:
  push:
    branches: [develop]

jobs:
  deploy:
    uses: ./.github/workflows/_reusable-deploy.yml
    with:
      environment: staging
      region: us-west-2
      dry-run: false
    secrets:
      aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
      aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

**From Different Repository:**
```yaml
jobs:
  deploy:
    uses: owner/repo/.github/workflows/deploy.yml@v1
    with:
      environment: production
    secrets: inherit  # Pass all secrets
```

**Using Outputs:**
```yaml
jobs:
  deploy:
    uses: ./.github/workflows/_reusable-deploy.yml
    with:
      environment: staging
    secrets: inherit

  notify:
    needs: deploy
    runs-on: ubuntu-latest
    steps:
      - name: Notify deployment
        run: |
          echo "Deployment ID: ${{ needs.deploy.outputs.deployment-id }}"
          echo "URL: ${{ needs.deploy.outputs.deployment-url }}"
          ./notify-slack.sh "${{ needs.deploy.outputs.deployment-url }}"
```

### Reusable Workflow Best Practices

**1. Naming Convention:**
- Prefix with `_` to indicate internal/reusable: `_reusable-test.yml`
- Use descriptive names: `_reusable-deploy.yml`, `_reusable-build-docker.yml`

**2. Input Validation:**
```yaml
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validate inputs
        run: |
          if [[ ! "${{ inputs.environment }}" =~ ^(staging|production)$ ]]; then
            echo "Invalid environment: ${{ inputs.environment }}"
            exit 1
          fi
```

**3. Secret Handling:**
```yaml
# Caller passes specific secrets
secrets:
  api-key: ${{ secrets.API_KEY }}

# OR inherit all secrets
secrets: inherit
```

**4. Documentation:**
```yaml
# Add comprehensive descriptions
on:
  workflow_call:
    inputs:
      environment:
        description: |
          Target environment for deployment.
          Valid values: staging, production
          Default: staging
        required: false
        type: choice
        options: [staging, production]
        default: 'staging'
```

---

## Composite Actions

### Creating Composite Action

```yaml
# .github/actions/setup-node-app/action.yml
name: 'Setup Node.js Application'
description: 'Checkout code, setup Node.js, install dependencies, and cache'
author: 'Your Name'

# Branding (shows in Marketplace)
branding:
  icon: 'package'
  color: 'green'

inputs:
  node-version:
    description: 'Node.js version to use'
    required: false
    default: '20'

  cache:
    description: 'Enable dependency caching'
    required: false
    default: 'true'

  install-command:
    description: 'Command to install dependencies'
    required: false
    default: 'npm ci'

outputs:
  cache-hit:
    description: 'Whether cache was restored'
    value: ${{ steps.cache.outputs.cache-hit }}

  node-version:
    description: 'Installed Node.js version'
    value: ${{ steps.setup-node.outputs.node-version }}

runs:
  using: 'composite'
  steps:
    - name: Checkout code
      uses: actions/checkout@v4
      shell: bash

    - name: Setup Node.js
      id: setup-node
      uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: ${{ inputs.cache == 'true' && 'npm' || '' }}
      shell: bash

    - name: Cache dependencies
      id: cache
      if: inputs.cache == 'true'
      uses: actions/cache@v4
      with:
        path: node_modules
        key: ${{ runner.os }}-node-${{ inputs.node-version }}-${{ hashFiles('**/package-lock.json') }}
      shell: bash

    - name: Install dependencies
      if: steps.cache.outputs.cache-hit != 'true'
      run: ${{ inputs.install-command }}
      shell: bash

    - name: Print versions
      run: |
        echo "Node: $(node --version)"
        echo "npm: $(npm --version)"
      shell: bash
```

### Using Composite Action

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Setup application
        id: setup
        uses: ./.github/actions/setup-node-app
        with:
          node-version: '20'
          cache: 'true'

      - name: Check setup
        run: |
          echo "Cache hit: ${{ steps.setup.outputs.cache-hit }}"
          echo "Node version: ${{ steps.setup.outputs.node-version }}"

      - name: Build
        run: npm run build
```

### Composite Action with Scripts

```yaml
# action.yml
runs:
  using: 'composite'
  steps:
    - name: Run validation script
      run: ${{ github.action_path }}/scripts/validate.sh
      shell: bash

    - name: Run with inputs
      run: |
        ${{ github.action_path }}/scripts/deploy.sh \
          --environment "${{ inputs.environment }}" \
          --region "${{ inputs.region }}"
      shell: bash
```

**Directory Structure:**
```
.github/actions/my-action/
├── action.yml
└── scripts/
    ├── validate.sh
    └── deploy.sh
```

### Composite Action Best Practices

**1. Always Specify Shell:**
```yaml
# REQUIRED for composite actions
- run: echo "Hello"
  shell: bash
```

**2. Use action_path for Scripts:**
```yaml
- run: ${{ github.action_path }}/scripts/setup.sh
  shell: bash
```

**3. Validate Inputs:**
```yaml
steps:
  - name: Validate inputs
    run: |
      if [[ -z "${{ inputs.required-input }}" ]]; then
        echo "Error: required-input is missing"
        exit 1
      fi
    shell: bash
```

**4. Provide Defaults:**
```yaml
inputs:
  timeout:
    description: 'Timeout in seconds'
    required: false
    default: '300'
```

**5. Document Thoroughly:**
```yaml
# Add README.md alongside action.yml
.github/actions/my-action/
├── action.yml
└── README.md
```

---

## Security Best Practices

### Secrets Management

**Using Secrets:**
```yaml
steps:
  - name: Deploy
    env:
      API_KEY: ${{ secrets.API_KEY }}
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
    run: ./deploy.sh
```

**NEVER:**
```yaml
# ❌ DON'T: Print secrets
- run: echo ${{ secrets.API_KEY }}

# ❌ DON'T: Pass secrets as arguments
- run: ./script.sh ${{ secrets.API_KEY }}

# ❌ DON'T: Hardcode secrets
env:
  API_KEY: abc123xyz
```

**Environment Secrets:**
```yaml
jobs:
  deploy:
    environment: production  # Uses production secrets
    steps:
      - env:
          API_KEY: ${{ secrets.API_KEY }}  # Environment-scoped secret
        run: ./deploy.sh
```

### OIDC Authentication (OpenID Connect)

**AWS with OIDC:**
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # Required for OIDC
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: us-east-1

      - name: Deploy to AWS
        run: aws s3 sync ./dist s3://my-bucket/
```

**Benefits:**
- No long-lived credentials stored as secrets
- Automatic credential rotation
- Fine-grained access control
- Audit trail in cloud provider

### Permissions

**Principle of Least Privilege:**
```yaml
# Workflow-level: Minimal default permissions
permissions:
  contents: read

jobs:
  deploy:
    # Job-level: Only what's needed
    permissions:
      contents: read
      packages: write
      deployments: write
    steps: [...]
```

**Common Permission Sets:**

1. **Read-only (Default for PRs):**
```yaml
permissions:
  contents: read
```

2. **Build and Test:**
```yaml
permissions:
  contents: read
  checks: write        # Write check results
  pull-requests: write # Comment on PRs
```

3. **Deploy:**
```yaml
permissions:
  contents: read
  packages: write      # Push to registry
  deployments: write   # Create deployments
  id-token: write      # OIDC auth
```

4. **Release:**
```yaml
permissions:
  contents: write      # Create releases
  packages: write      # Publish packages
```

### Pull Request Security

**NEVER use pull_request_target with Untrusted Code:**
```yaml
# ❌ DANGEROUS: Checks out PR code with write permissions
on: pull_request_target
jobs:
  test:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - run: npm install && npm test  # Malicious code could access secrets!
```

**SAFE Patterns:**

1. **Use pull_request for CI:**
```yaml
# ✅ SAFE: Limited permissions, no secrets
on: pull_request
jobs:
  test:
    steps:
      - uses: actions/checkout@v4
      - run: npm install && npm test
```

2. **Use pull_request_target for Comments Only:**
```yaml
# ✅ SAFE: No checkout of PR code
on: pull_request_target
jobs:
  comment:
    permissions:
      pull-requests: write
    steps:
      - name: Comment on PR
        run: |
          gh pr comment ${{ github.event.pull_request.number }} \
            --body "Thank you for your contribution!"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Action Pinning

**Pin to Commit SHA (Most Secure):**
```yaml
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
```

**Pin to Major Version (Recommended):**
```yaml
- uses: actions/checkout@v4  # Receives patches and features
```

**NEVER Pin to Branch:**
```yaml
# ❌ DON'T: Branch can be rewritten
- uses: actions/checkout@main
```

**Audit Third-Party Actions:**
```yaml
# ✅ Review action source code before using
- uses: third-party/action@v1
  # Check: https://github.com/third-party/action

# ✅ Use trusted actions
- uses: actions/checkout@v4      # Official GitHub action
- uses: docker/build-push-action@v5  # Docker official
```

### Secure Workflows

**1. Limit Workflow Triggers:**
```yaml
# Limit to specific branches
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
```

**2. Validate Inputs:**
```yaml
jobs:
  deploy:
    steps:
      - name: Validate environment
        run: |
          if [[ ! "${{ inputs.environment }}" =~ ^(staging|production)$ ]]; then
            echo "Invalid environment"
            exit 1
          fi
```

**3. Use Branch Protection:**
- Require PR reviews
- Require status checks
- Require signed commits
- Restrict push access

**4. Enable Workflow Approval:**
- Environment protection rules
- Required reviewers for deployments
- Deployment branches restrictions

### Dependency Security

**Dependabot:**
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

**CodeQL Scanning:**
```yaml
name: CodeQL

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      actions: read
      contents: read

    strategy:
      matrix:
        language: [javascript, python]

    steps:
      - uses: actions/checkout@v4

      - uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}

      - uses: github/codeql-action/autobuild@v3

      - uses: github/codeql-action/analyze@v3
```

---

## Performance Optimization

### Workflow Optimization

**1. Use Concurrency Control:**
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

**2. Path Filters:**
```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
      - '!docs/**'
```

**3. Conditional Jobs:**
```yaml
jobs:
  deploy:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps: [...]
```

**4. Parallel Jobs:**
```yaml
jobs:
  test-unit:
    runs-on: ubuntu-latest
    steps: [...]

  test-integration:
    runs-on: ubuntu-latest
    steps: [...]

  lint:
    runs-on: ubuntu-latest
    steps: [...]
```

### Caching Optimization

**1. Aggressive Caching:**
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      ~/.cache
      node_modules
      .next/cache
    key: ${{ runner.os }}-deps-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-deps-
```

**2. Incremental Builds:**
```yaml
- uses: actions/cache@v4
  with:
    path: |
      dist/
      .build-cache/
    key: build-${{ github.sha }}
    restore-keys: |
      build-${{ github.base_ref }}-
      build-
```

**3. Docker Layer Caching:**
```yaml
- uses: docker/build-push-action@v5
  with:
    context: .
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### Runner Optimization

**1. Use Ubuntu Runners:**
```yaml
# Linux is 1x cost, Windows is 2x, macOS is 10x
runs-on: ubuntu-latest
```

**2. Matrix Optimization:**
```yaml
strategy:
  matrix:
    os: [ubuntu-latest]  # Test only on Linux
    node: [20]            # Test only LTS

  # Test other platforms only on main branch
  include:
    - os: macos-latest
      node: 20
      if: github.ref == 'refs/heads/main'
```

**3. Self-Hosted Runners for Heavy Workloads:**
```yaml
runs-on: [self-hosted, linux, high-cpu]
```

### Build Optimization

**1. Parallel Steps (Where Possible):**
```yaml
jobs:
  build:
    steps:
      - run: npm ci

      # These don't depend on each other
      - name: Lint
        run: npm run lint &

      - name: Type Check
        run: npm run typecheck &

      - name: Wait for checks
        run: wait

      - run: npm run build
```

**2. Selective Testing:**
```yaml
- name: Detect changes
  id: changes
  uses: dorny/paths-filter@v2
  with:
    filters: |
      backend:
        - 'backend/**'
      frontend:
        - 'frontend/**'

- name: Test backend
  if: steps.changes.outputs.backend == 'true'
  run: npm run test:backend

- name: Test frontend
  if: steps.changes.outputs.frontend == 'true'
  run: npm run test:frontend
```

**3. Artifact Optimization:**
```yaml
# Compress before upload
- run: tar -czf dist.tar.gz dist/

- uses: actions/upload-artifact@v4
  with:
    name: dist
    path: dist.tar.gz
    compression-level: 9  # Max compression
    retention-days: 1     # Short retention
```

### Network Optimization

**1. Use Mirrors:**
```yaml
- name: Use npm mirror
  run: npm config set registry https://registry.npmmirror.com

- run: npm ci
```

**2. Shallow Checkouts:**
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 1  # Only latest commit
```

**3. Sparse Checkouts:**
```yaml
- uses: actions/checkout@v4
  with:
    sparse-checkout: |
      src/
      tests/
      package.json
```

---

## Monorepo Strategies

### Path-Based Triggering

**Detect Changes:**
```yaml
name: Monorepo CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
      shared: ${{ steps.filter.outputs.shared }}

    steps:
      - uses: actions/checkout@v4

      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            backend:
              - 'packages/backend/**'
              - 'shared/**'
            frontend:
              - 'packages/frontend/**'
              - 'shared/**'
            shared:
              - 'shared/**'

  test-backend:
    needs: detect-changes
    if: needs.detect-changes.outputs.backend == 'true'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: packages/backend
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test

  test-frontend:
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: packages/frontend
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test
```

### Matrix for Packages

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package:
          - backend
          - frontend
          - api
          - workers

    defaults:
      run:
        working-directory: packages/${{ matrix.package }}

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: packages/${{ matrix.package }}/package-lock.json

      - run: npm ci
      - run: npm test
```

### Dependency Graph

```yaml
jobs:
  # Build shared libraries first
  build-shared:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - working-directory: packages/shared
        run: |
          npm ci
          npm run build

      - uses: actions/upload-artifact@v4
        with:
          name: shared
          path: packages/shared/dist

  # Build packages that depend on shared
  build-backend:
    needs: build-shared
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/download-artifact@v4
        with:
          name: shared
          path: packages/shared/dist

      - working-directory: packages/backend
        run: |
          npm ci
          npm run build

  build-frontend:
    needs: build-shared
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/download-artifact@v4
        with:
          name: shared
          path: packages/shared/dist

      - working-directory: packages/frontend
        run: |
          npm ci
          npm run build
```

### Turborepo Integration

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      # Turborepo with remote caching
      - name: Build with Turborepo
        run: npx turbo run build --cache-dir=.turbo
        env:
          TURBO_TOKEN: ${{ secrets.TURBO_TOKEN }}
          TURBO_TEAM: ${{ vars.TURBO_TEAM }}

      - uses: actions/cache@v4
        with:
          path: .turbo
          key: turbo-${{ github.sha }}
          restore-keys: turbo-
```

### Nx Integration

```yaml
jobs:
  affected:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Nx needs full history

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      # Test only affected projects
      - name: Run affected tests
        run: npx nx affected --target=test --base=origin/main --head=HEAD

      # Build only affected projects
      - name: Build affected
        run: npx nx affected --target=build --base=origin/main --head=HEAD
```

---

## Common Patterns

### CI/CD Pipeline

**Complete CI/CD Example:**
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

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

  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci
      - run: npm test

      - uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci
      - run: npm run build

      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 7

  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - uses: actions/checkout@v4

      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Deploy to staging
        run: ./deploy.sh staging
        env:
          API_KEY: ${{ secrets.STAGING_API_KEY }}

  deploy-production:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4

      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Deploy to production
        run: ./deploy.sh production
        env:
          API_KEY: ${{ secrets.PROD_API_KEY }}
```

### Docker Build and Push

```yaml
name: Docker Build

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64
```

### Release Automation

```yaml
name: Release

on:
  push:
    tags: ['v*']

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            target: x86_64-unknown-linux-gnu
            artifact: app-linux-x64

          - os: macos-latest
            target: x86_64-apple-darwin
            artifact: app-macos-x64

          - os: windows-latest
            target: x86_64-pc-windows-msvc
            artifact: app-windows-x64.exe

    steps:
      - uses: actions/checkout@v4

      - name: Build
        run: cargo build --release --target ${{ matrix.target }}

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact }}
          path: target/${{ matrix.target }}/release/app*

  release:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/download-artifact@v4

      - name: Create checksums
        run: |
          sha256sum app-*/* > checksums.txt

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            app-*/*
            checksums.txt
          generate_release_notes: true
```

### Security Scanning

```yaml
name: Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'  # Weekly

jobs:
  codeql:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      actions: read
      contents: read

    steps:
      - uses: actions/checkout@v4

      - uses: github/codeql-action/init@v3
        with:
          languages: javascript, python

      - uses: github/codeql-action/autobuild@v3

      - uses: github/codeql-action/analyze@v3

  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Snyk
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

  secrets-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Anti-Patterns

### Security Anti-Patterns

**❌ Hardcoded Secrets:**
```yaml
# WRONG
env:
  API_KEY: abc123xyz
```

```yaml
# CORRECT
env:
  API_KEY: ${{ secrets.API_KEY }}
```

**❌ Printing Secrets:**
```yaml
# WRONG
- run: echo "API Key: ${{ secrets.API_KEY }}"
```

```yaml
# CORRECT
- run: ./deploy.sh
  env:
    API_KEY: ${{ secrets.API_KEY }}
```

**❌ Using pull_request_target Unsafely:**
```yaml
# WRONG - Dangerous!
on: pull_request_target
jobs:
  test:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - run: npm install && npm test
```

```yaml
# CORRECT
on: pull_request
jobs:
  test:
    steps:
      - uses: actions/checkout@v4
      - run: npm install && npm test
```

### Performance Anti-Patterns

**❌ No Caching:**
```yaml
# WRONG
- run: npm install
```

```yaml
# CORRECT
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
- run: npm ci
```

**❌ Sequential Jobs (When Parallel is Possible):**
```yaml
# WRONG
jobs:
  lint:
    steps: [...]

  test:
    needs: lint
    steps: [...]
```

```yaml
# CORRECT
jobs:
  lint:
    steps: [...]

  test:
    steps: [...]

  deploy:
    needs: [lint, test]
    steps: [...]
```

**❌ No Concurrency Control:**
```yaml
# WRONG - Wastes runner minutes
on:
  pull_request:

jobs:
  test:
    steps: [...]
```

```yaml
# CORRECT
on:
  pull_request:

concurrency:
  group: pr-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  test:
    steps: [...]
```

**❌ Rebuilding Artifacts:**
```yaml
# WRONG
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
# CORRECT
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
      - run: npm test

  deploy:
    needs: build
    steps:
      - uses: actions/download-artifact@v4
      - run: ./deploy.sh
```

### Workflow Anti-Patterns

**❌ Using npm install Instead of npm ci:**
```yaml
# WRONG
- run: npm install
```

```yaml
# CORRECT
- run: npm ci
```

**❌ No Path Filters (Unnecessary Runs):**
```yaml
# WRONG
on:
  push:
    branches: [main]
```

```yaml
# CORRECT
on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - '!docs/**'
```

**❌ No Matrix for Multi-Platform:**
```yaml
# WRONG
jobs:
  test-linux:
    runs-on: ubuntu-latest
    steps: [...]

  test-mac:
    runs-on: macos-latest
    steps: [...]
```

```yaml
# CORRECT
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
    steps: [...]
```

**❌ Pinning to Branch:**
```yaml
# WRONG
- uses: actions/checkout@main
```

```yaml
# CORRECT
- uses: actions/checkout@v4  # Major version
# OR
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # SHA
```

---

## Debugging and Troubleshooting

### Enable Debug Logging

**Repository Secrets:**
- `ACTIONS_RUNNER_DEBUG` = `true`
- `ACTIONS_STEP_DEBUG` = `true`

**In Workflow:**
```yaml
steps:
  - name: Enable debug
    run: |
      echo "ACTIONS_RUNNER_DEBUG=true" >> $GITHUB_ENV
      echo "ACTIONS_STEP_DEBUG=true" >> $GITHUB_ENV
```

### Inspect Contexts

```yaml
steps:
  - name: Dump GitHub context
    run: echo '${{ toJSON(github) }}'

  - name: Dump runner context
    run: echo '${{ toJSON(runner) }}'

  - name: Dump job context
    run: echo '${{ toJSON(job) }}'

  - name: Dump steps context
    run: echo '${{ toJSON(steps) }}'

  - name: Dump env context
    run: echo '${{ toJSON(env) }}'
```

### Conditional Debugging

```yaml
steps:
  - name: Debug on failure
    if: failure()
    run: |
      echo "Workflow failed"
      echo "Event: ${{ github.event_name }}"
      echo "Ref: ${{ github.ref }}"
      echo "SHA: ${{ github.sha }}"
      cat /tmp/*.log || true
```

### SSH Debugging (action-tmate)

```yaml
steps:
  - name: Setup tmate session
    if: ${{ failure() }}
    uses: mxschmitt/action-tmate@v3
    timeout-minutes: 30
```

### Common Issues

**1. Permission Denied:**
```yaml
# Issue: No write permission
permissions:
  contents: read

# Fix: Add required permission
permissions:
  contents: write
```

**2. Cache Not Restored:**
```yaml
# Issue: Cache key doesn't match
key: ${{ runner.os }}-node-${{ hashFiles('package-lock.json') }}

# Fix: Use correct path pattern
key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
```

**3. Artifact Not Found:**
```yaml
# Issue: Artifact name mismatch
- uses: actions/upload-artifact@v4
  with:
    name: build

- uses: actions/download-artifact@v4
  with:
    name: dist  # WRONG

# Fix: Match names exactly
- uses: actions/download-artifact@v4
  with:
    name: build
```

**4. Environment Variable Not Set:**
```yaml
# Issue: Env var not available in next step
- run: echo "VAR=value"

# Fix: Use GITHUB_ENV
- run: echo "VAR=value" >> $GITHUB_ENV
```

**5. Service Container Connection:**
```yaml
# Issue: Can't connect to service
services:
  postgres:
    image: postgres:15

# Fix: Wait for health check
services:
  postgres:
    image: postgres:15
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

---

## References

### Official Documentation
- GitHub Actions Docs: https://docs.github.com/en/actions
- Workflow Syntax: https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions
- Events: https://docs.github.com/en/actions/reference/events-that-trigger-workflows
- Contexts: https://docs.github.com/en/actions/reference/context-and-expression-syntax-for-github-actions
- Marketplace: https://github.com/marketplace?type=actions

### Community Resources
- Awesome Actions: https://github.com/sdras/awesome-actions
- Actions Toolkit: https://github.com/actions/toolkit
- Runner Images: https://github.com/actions/runner-images

### Security
- Security Hardening: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
- OIDC in Actions: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect

### Best Practices
- GitHub Actions Best Practices: https://docs.github.com/en/actions/learn-github-actions/best-practices-for-github-actions
- Performance Optimization: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstrategyjob-strategy

---

**Document Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: 3500+
