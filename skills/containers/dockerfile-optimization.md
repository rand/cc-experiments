---
name: containers-dockerfile-optimization
description: Writing Dockerfiles for production applications
---



# Dockerfile Optimization

**Scope**: Layer caching, multi-stage builds, .dockerignore, image size reduction
**Lines**: ~280
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Writing Dockerfiles for production applications
- Optimizing build times and image sizes
- Implementing multi-stage builds
- Configuring layer caching strategies
- Reducing container attack surface
- Troubleshooting slow Docker builds
- Minimizing image transfer times

## Core Concepts

### Docker Image Layers

**Images are built in layers**: Each instruction creates a new layer.

**Key properties**:
- **Immutable**: Once created, layers never change
- **Cacheable**: Unchanged layers are reused from cache
- **Ordered**: Layers stack sequentially (base → final)
- **Shared**: Multiple images can share base layers
- **Additive**: Each layer adds to previous (can't truly delete)

**Example**:
```dockerfile
FROM python:3.11-slim    # Layer 1: Base image
RUN apt-get update       # Layer 2: Package manager update
COPY requirements.txt    # Layer 3: Copy requirements
RUN pip install -r req   # Layer 4: Install dependencies
COPY . .                 # Layer 5: Copy application code
```

---

## Layer Caching Strategies

### Rule 1: Order Instructions by Change Frequency

**❌ Wrong** (bust cache on every code change):
```dockerfile
FROM python:3.11-slim
COPY . .                        # Changes frequently
RUN pip install -r requirements.txt  # Reinstalls every time
CMD ["python", "app.py"]
```

**✅ Correct** (cache dependencies):
```dockerfile
FROM python:3.11-slim
COPY requirements.txt .         # Changes rarely
RUN pip install -r requirements.txt  # Cached unless requirements change
COPY . .                        # Changes frequently
CMD ["python", "app.py"]
```

**Principle**: Place stable layers first, volatile layers last.

### Rule 2: Combine Commands to Reduce Layers

**❌ Wrong** (many layers):
```dockerfile
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y git
RUN apt-get install -y vim
RUN rm -rf /var/lib/apt/lists/*
```

**✅ Correct** (single layer):
```dockerfile
RUN apt-get update && \
    apt-get install -y \
        curl \
        git \
        vim && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
```

**Benefits**: Smaller image, fewer layers, better caching.

### Rule 3: Use .dockerignore to Exclude Files

**Create `.dockerignore`**:
```
# Version control
.git
.gitignore

# Dependencies
node_modules/
vendor/
__pycache__/
*.pyc

# Build artifacts
dist/
build/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp

# Logs and temp files
*.log
tmp/
.env.local

# Documentation
README.md
docs/

# CI/CD
.github/
.gitlab-ci.yml
Jenkinsfile
```

**Impact**: Faster builds, smaller context, no accidental secret leakage.

### Rule 4: Cache Package Manager Dependencies

**Python (pip)**:
```dockerfile
# ✅ Cache pip dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

**Node.js (npm/pnpm)**:
```dockerfile
# ✅ Cache npm dependencies
COPY package.json pnpm-lock.yaml .
RUN pnpm install --frozen-lockfile
COPY . .
```

**Go**:
```dockerfile
# ✅ Cache Go modules
COPY go.mod go.sum .
RUN go mod download
COPY . .
RUN go build -o app
```

**Rust (Cargo)**:
```dockerfile
# ✅ Cache Cargo dependencies
COPY Cargo.toml Cargo.lock .
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
COPY . .
RUN cargo build --release
```

---

## Multi-Stage Builds

### Purpose: Separate Build and Runtime Environments

**Problem**: Including build tools bloats final image.

**Solution**: Multi-stage builds.

### Basic Multi-Stage Pattern

```dockerfile
# Stage 1: Build
FROM golang:1.21 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o app

# Stage 2: Runtime
FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/app .
CMD ["./app"]
```

**Result**: Final image contains only binary, not Go compiler.

### Multi-Stage for Python

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app.py"]
```

### Multi-Stage for Node.js

```dockerfile
# Stage 1: Build
FROM node:20 AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# Stage 2: Runtime
FROM node:20-slim
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
CMD ["node", "dist/index.js"]
```

### Multi-Stage for Static Sites

```dockerfile
# Stage 1: Build
FROM node:20 AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install
COPY . .
RUN pnpm build

# Stage 2: Serve with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Result**: Final image is nginx + static files (no Node.js).

---

## Image Size Optimization

### Strategy 1: Use Minimal Base Images

**Base image comparison**:
| Image | Size | Use Case |
|-------|------|----------|
| `ubuntu:22.04` | ~77MB | Full Ubuntu (avoid) |
| `python:3.11` | ~1GB | Full Python + build tools |
| `python:3.11-slim` | ~180MB | Python without extras |
| `alpine:3.19` | ~7MB | Minimal Linux (musl libc) |
| `scratch` | ~0MB | Empty (static binaries only) |
| `distroless` | ~20MB | Runtime only (no shell) |

**Recommendations**:
- **General**: Use `-slim` variants (`python:3.11-slim`, `node:20-slim`)
- **Static binaries**: Use `scratch` or `distroless`
- **Alpine**: Good for size, but musl libc can cause issues

### Strategy 2: Use Distroless for Security

```dockerfile
# Build stage
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 go build -o app

# Runtime stage with distroless
FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/app /app
ENTRYPOINT ["/app"]
```

**Benefits**:
- No shell (smaller attack surface)
- No package manager (can't install malware)
- Minimal CVEs
- Small size (~20MB)

**Distroless variants**:
- `gcr.io/distroless/static-debian12` - Static binaries
- `gcr.io/distroless/base-debian12` - Requires libc
- `gcr.io/distroless/python3-debian12` - Python runtime
- `gcr.io/distroless/nodejs20-debian12` - Node.js runtime

### Strategy 3: Remove Build Artifacts

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl && \
    # Build app \
    make build && \
    # Clean up in same layer \
    apt-get purge -y build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
```

**Key**: Cleanup in same `RUN` instruction (same layer).

### Strategy 4: Use --no-cache-dir for Package Managers

```dockerfile
# Python
RUN pip install --no-cache-dir -r requirements.txt

# Alpine apk
RUN apk add --no-cache curl git

# Debian/Ubuntu apt
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
```

### Strategy 5: Optimize COPY Instructions

**❌ Wrong** (copies everything):
```dockerfile
COPY . .
```

**✅ Correct** (copy only needed files):
```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ ./src/
COPY config/ ./config/
```

**Use .dockerignore** to exclude unnecessary files automatically.

---

## Build Performance Optimization

### Technique 1: BuildKit (Modern Docker)

**Enable BuildKit** (faster builds, better caching):
```bash
# Linux/Mac
export DOCKER_BUILDKIT=1
docker build .

# Or per-command
DOCKER_BUILDKIT=1 docker build .
```

**BuildKit features**:
- Parallel builds
- Better cache management
- Improved layer reuse
- Secrets mounting (no secrets in history)

### Technique 2: Cache Mounts (BuildKit)

```dockerfile
# Python with cache mount
FROM python:3.11-slim
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

**Benefits**: Reuses pip cache across builds (faster).

### Technique 3: SSH Mounts for Private Dependencies

```dockerfile
# Clone private repo without embedding SSH key
FROM golang:1.21
RUN --mount=type=ssh \
    git clone git@github.com:private/repo.git
```

**Build command**:
```bash
docker build --ssh default .
```

### Technique 4: Secrets Mounting

```dockerfile
# Use secret without embedding in layer
FROM alpine
RUN --mount=type=secret,id=github_token \
    wget --header="Authorization: token $(cat /run/secrets/github_token)" \
    https://api.github.com/repos/private/repo/tarball
```

**Build command**:
```bash
docker build --secret id=github_token,src=$HOME/.github_token .
```

**Benefit**: Secret never stored in image layers.

---

## Common Dockerfile Patterns

### Pattern 1: Python Web App (FastAPI/Flask)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Pattern 2: Node.js App

```dockerfile
FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile --prod

# Copy application
COPY . .

# Non-root user
RUN chown -R node:node /app
USER node

EXPOSE 3000
CMD ["node", "index.js"]
```

### Pattern 3: Go Static Binary

```dockerfile
# Build stage
FROM golang:1.21 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o app

# Runtime stage
FROM scratch
COPY --from=builder /app/app /app
ENTRYPOINT ["/app"]
```

**Flags**: `-ldflags="-w -s"` removes debug info (smaller binary).

### Pattern 4: Rust Binary

```dockerfile
# Build stage
FROM rust:1.75 AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
COPY . .
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim
COPY --from=builder /app/target/release/app /usr/local/bin/app
CMD ["app"]
```

---

## Dockerfile Linting and Analysis

### Tool 1: hadolint (Dockerfile Linter)

```bash
# Install
brew install hadolint

# Lint Dockerfile
hadolint Dockerfile
```

**Common warnings**:
- `DL3008`: Pin apt package versions
- `DL3013`: Pin pip versions
- `DL3059`: Multiple RUN commands (combine)
- `DL4006`: Use SHELL or arrays for pipefail

### Tool 2: dive (Image Layer Explorer)

```bash
# Install
brew install dive

# Analyze image
dive myimage:latest
```

**Features**:
- Layer-by-layer breakdown
- File changes per layer
- Wasted space detection
- Efficiency score

### Tool 3: docker history (Built-in)

```bash
# Show layer sizes
docker history myimage:latest

# Show layer commands
docker history --no-trunc myimage:latest
```

---

## Dockerfile Best Practices Checklist

```
Base Image:
[ ] Use official images (python:3.11-slim, node:20-slim)
[ ] Pin specific versions (not :latest)
[ ] Use minimal variants (-slim, -alpine, distroless)

Layer Optimization:
[ ] Order instructions by change frequency (stable → volatile)
[ ] Combine RUN commands with &&
[ ] Clean up in same RUN layer
[ ] Use .dockerignore to exclude files

Caching:
[ ] Copy dependency files before application code
[ ] Use cache mounts for package managers (BuildKit)
[ ] Leverage multi-stage builds
[ ] Order COPY instructions carefully

Security:
[ ] Use non-root USER
[ ] Don't store secrets in layers
[ ] Use --mount=type=secret for sensitive data
[ ] Scan images for vulnerabilities (Trivy)

Size:
[ ] Use multi-stage builds
[ ] Remove build dependencies
[ ] Use --no-cache-dir for package managers
[ ] Remove unnecessary files

Performance:
[ ] Enable BuildKit (DOCKER_BUILDKIT=1)
[ ] Use cache mounts for dependencies
[ ] Parallelize independent stages
[ ] Use SSH mounts for private repos
```

---

## Common Dockerfile Anti-Patterns

❌ **Using :latest tag**: `FROM python:latest`
✅ Pin versions: `FROM python:3.11-slim`

❌ **Running as root**: No `USER` directive
✅ Create non-root user: `USER appuser`

❌ **Busting cache**: `COPY . .` before dependencies
✅ Copy dependencies first: `COPY requirements.txt .`

❌ **Storing secrets**: `ENV API_KEY=secret123`
✅ Use runtime secrets or mount: `--mount=type=secret`

❌ **Many small layers**: Multiple `RUN` commands
✅ Combine commands: `RUN cmd1 && cmd2 && cmd3`

❌ **Not using .dockerignore**: Copying `.git`, `node_modules`
✅ Exclude with .dockerignore

❌ **Installing unnecessary packages**: `apt-get install -y vim curl wget`
✅ Install only required: `--no-install-recommends`

---

## Quick Reference

### Build Commands

```bash
# Basic build
docker build -t myapp:latest .

# BuildKit build
DOCKER_BUILDKIT=1 docker build -t myapp:latest .

# Build with secrets
docker build --secret id=token,src=./token.txt -t myapp .

# Build with SSH
docker build --ssh default -t myapp .

# Build specific stage
docker build --target builder -t myapp:builder .

# No cache
docker build --no-cache -t myapp .
```

### Image Analysis

```bash
# Show layers
docker history myapp:latest

# Inspect image
docker inspect myapp:latest

# Analyze with dive
dive myapp:latest

# Lint Dockerfile
hadolint Dockerfile
```

---

## Related Skills

- `container-security.md` - USER directive, vulnerability scanning
- `docker-compose-development.md` - Multi-container builds
- `container-registry-management.md` - Tagging and pushing images
- `kubernetes-deployments.md` - Deploying optimized images

---

## Level 3: Resources

This skill has comprehensive Level 3 resources in `skills/containers/dockerfile-optimization/resources/`.

### REFERENCE.md

Comprehensive 900+ line reference covering:
- Multi-stage builds (basic patterns, advanced patterns, parallel builds)
- Layer caching strategies (cache invalidation, optimization techniques, BuildKit cache mounts)
- Base image selection (alpine, slim, distroless, scratch comparisons)
- .dockerignore best practices (templates, language-specific patterns)
- Security hardening (non-root users, minimal attack surface, secret management)
- Image size optimization (reduction techniques, real-world examples)
- Build time optimization (BuildKit features, parallel stages, remote caching)
- Runtime optimization (startup time, memory, CPU, disk I/O)
- Dockerfile best practices (instruction order, anti-patterns, exec vs shell form)
- BuildKit features (cache mounts, secret mounts, SSH mounts, heredoc syntax)
- Health checks and signal handling (graceful shutdown patterns)
- Resource limits (CPU, memory, disk I/O constraints)
- Performance benchmarking techniques
- Real-world optimization examples with before/after comparisons

### Scripts

Production-ready executable scripts with `--help` and `--json` support:

1. **analyze_dockerfile.py** (500+ lines)
   - Analyzes Dockerfiles for anti-patterns and security issues
   - Detects: root user, latest tags, inefficient layers, missing .dockerignore
   - Calculates optimization score (0-100)
   - Provides specific recommendations
   - Usage: `./analyze_dockerfile.py Dockerfile [--json] [--min-score 80]`

2. **optimize_image.sh** (400+ lines)
   - Analyzes Docker images with size and layer breakdown
   - Identifies optimization opportunities
   - Optional: Builds optimized version with comparison
   - Shows before/after size reduction percentage
   - Usage: `./optimize_image.sh [--build] [--json] myapp:latest`

3. **benchmark_builds.py** (500+ lines)
   - Benchmarks build times with different strategies
   - Compares: cached, no-cache, BuildKit, legacy builder, parallel stages
   - Measures image sizes and build durations
   - Provides speedup analysis and recommendations
   - Usage: `./benchmark_builds.py [--all] [--json] myapp`

### Examples

#### Optimized Dockerfiles by Language

- **python-optimized.Dockerfile**: Multi-stage, slim base, cache mounts, non-root user
- **node-optimized.Dockerfile**: Alpine base, production deps only, dumb-init
- **go-optimized.Dockerfile**: Scratch base, static binary, minimal size (<10MB)
- **rust-optimized.Dockerfile**: Cargo cache mounts, debian-slim runtime
- **multi-stage-example.Dockerfile**: Parallel stages, test stage, multiple targets

#### Before/After Optimization Examples

- **python-before.Dockerfile** → **python-after.Dockerfile**: 1.2GB → 150MB (87% reduction)
- **node-before.Dockerfile** → **node-after.Dockerfile**: 1.1GB → 180MB (83% reduction)
- **COMPARISON.md**: Detailed analysis of optimization techniques and impact

### Usage

```bash
# Analyze Dockerfile for issues
cd skills/containers/dockerfile-optimization/resources/scripts
./analyze_dockerfile.py /path/to/Dockerfile

# Get JSON output for CI/CD integration
./analyze_dockerfile.py Dockerfile --json --min-score 80

# Analyze existing image
./optimize_image.sh myapp:latest

# Build optimized version and compare
./optimize_image.sh --build myapp:latest

# Benchmark different build strategies
./benchmark_builds.py --all myapp

# Compare specific strategies
./benchmark_builds.py -s cached -s buildkit -s parallel myapp --json
```

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
