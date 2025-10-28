# Docker Optimization Reference

Comprehensive guide to building efficient, secure, and performant Docker images.

## Table of Contents

1. [Multi-Stage Builds](#multi-stage-builds)
2. [Layer Caching Strategies](#layer-caching-strategies)
3. [Base Image Selection](#base-image-selection)
4. [.dockerignore Best Practices](#dockerignore-best-practices)
5. [Security Hardening](#security-hardening)
6. [Image Size Optimization](#image-size-optimization)
7. [Build Time Optimization](#build-time-optimization)
8. [Runtime Optimization](#runtime-optimization)
9. [Dockerfile Best Practices](#dockerfile-best-practices)
10. [BuildKit Features](#buildkit-features)
11. [Health Checks and Signals](#health-checks-and-signals)
12. [Resource Limits](#resource-limits)

---

## Multi-Stage Builds

Multi-stage builds separate the build environment from the runtime environment, dramatically reducing final image size.

### Basic Pattern

```dockerfile
# Build stage
FROM golang:1.21 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o app

# Runtime stage
FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/app .
CMD ["./app"]
```

### Advanced Multi-Stage Patterns

**Parallel Build Stages**:

```dockerfile
# Dependencies stage
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Runtime stage
FROM node:20-alpine
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY package.json ./
USER node
CMD ["node", "dist/index.js"]
```

**Testing in Build Pipeline**:

```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Test stage
FROM base AS test
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN pytest tests/ && pylint src/

# Production stage
FROM base AS prod
COPY --from=test /app/src ./src
CMD ["python", "-m", "src.main"]
```

**Multi-Platform Builds**:

```dockerfile
FROM --platform=$BUILDPLATFORM golang:1.21 AS builder
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG TARGETOS
ARG TARGETARCH

WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH \
    go build -o app

FROM alpine:3.19
COPY --from=builder /app/app .
CMD ["./app"]
```

### Multi-Stage Build Benefits

1. **Size Reduction**: 90%+ smaller images (e.g., 1GB build → 50MB runtime)
2. **Security**: No build tools, source code, or secrets in final image
3. **Separation**: Clear boundary between build and runtime dependencies
4. **Flexibility**: Multiple outputs from single Dockerfile
5. **Caching**: Independent caching for build and runtime stages

### Common Patterns

**Language-Specific Optimizations**:

```dockerfile
# Python with compiled dependencies
FROM python:3.11 AS builder
RUN pip install --user --no-cache-dir numpy pandas

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
```

```dockerfile
# Rust with minimal runtime
FROM rust:1.75 AS builder
WORKDIR /app
COPY Cargo.* ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
COPY src ./src
RUN touch src/main.rs && cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/app /usr/local/bin/
CMD ["app"]
```

---

## Layer Caching Strategies

Docker caches each layer. Understanding cache invalidation is critical for fast builds.

### Cache Invalidation Rules

1. **Sequential Processing**: Layers processed top to bottom
2. **Invalidation Cascade**: Changed layer invalidates all subsequent layers
3. **Context Checksum**: COPY/ADD instructions checksum source files
4. **Command String**: RUN instructions cached by exact command string

### Optimal Layer Ordering

**Wrong Order** (cache-inefficient):

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY . .                    # Invalidates on any file change
RUN npm install             # Reinstalls on every code change
CMD ["npm", "start"]
```

**Correct Order** (cache-efficient):

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./       # Only invalidates on dependency changes
RUN npm ci                  # Cached unless dependencies change
COPY . .                    # Code changes don't invalidate npm install
CMD ["npm", "start"]
```

### Advanced Caching Techniques

**Cache Mounts** (BuildKit):

```dockerfile
# Python with pip cache
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

```dockerfile
# Go with module cache
FROM golang:1.21
WORKDIR /app
COPY go.* ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    go build -o app
```

**Apt/Apk Cache**:

```dockerfile
# Debian/Ubuntu
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y build-essential
```

```dockerfile
# Alpine
RUN --mount=type=cache,target=/var/cache/apk \
    apk --update add build-base
```

**Dependency Layer Splitting**:

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# System dependencies (rarely change)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache

# Base dependencies (change occasionally)
COPY requirements-base.txt .
RUN pip install --no-cache-dir -r requirements-base.txt

# Application dependencies (change more frequently)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (changes frequently)
COPY . .
```

### Build Cache Inspection

```bash
# View layer cache
docker history <image>

# Build without cache
docker build --no-cache .

# Build with specific cache source
docker build --cache-from=myapp:latest .

# Prune build cache
docker builder prune
```

---

## Base Image Selection

Choosing the right base image impacts size, security, and performance.

### Base Image Options

| Base Image | Size | Use Case | Pros | Cons |
|------------|------|----------|------|------|
| `alpine:3.19` | ~7MB | General, minimal | Smallest, fast | musl libc compatibility |
| `debian:bookworm-slim` | ~74MB | General, compatible | Wide compatibility | Larger |
| `ubuntu:22.04` | ~77MB | Development | Familiar, popular | Larger |
| `distroless` | ~2-20MB | Production | Minimal attack surface | No shell |
| `scratch` | 0MB | Static binaries | Smallest possible | No OS utilities |
| `gcr.io/distroless/static` | ~2MB | Static Go/Rust | Security focused | No debug tools |
| `gcr.io/distroless/base` | ~20MB | Dynamic binaries | Minimal runtime | Limited debugging |

### Alpine Linux

**Advantages**:
- Smallest general-purpose base (~7MB)
- Fast package manager (apk)
- Security-focused

**Disadvantages**:
- musl libc (not glibc) - compatibility issues with some binaries
- Slower Python C extensions compilation
- DNS resolution quirks

**Best Practices**:

```dockerfile
FROM alpine:3.19

# Install with cache mount
RUN --mount=type=cache,target=/var/cache/apk \
    apk --update add python3 py3-pip

# Virtual packages for build dependencies
RUN apk add --no-cache --virtual .build-deps \
    gcc musl-dev python3-dev && \
    pip install numpy && \
    apk del .build-deps
```

### Debian Slim

**Advantages**:
- glibc compatibility
- Stable, well-tested
- Good package availability

**Best Practices**:

```dockerfile
FROM debian:bookworm-slim

# Combine update + install + cleanup
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
```

### Distroless

**Advantages**:
- No shell, package manager, or unnecessary tools
- Minimal attack surface
- Smaller than full distros

**Best Practices**:

```dockerfile
FROM gcr.io/distroless/static-debian12

# Copy only runtime artifacts
COPY --from=builder /app/binary /app/binary

USER nonroot:nonroot
ENTRYPOINT ["/app/binary"]
```

**Debugging Distroless**:

```dockerfile
# Use debug variant for troubleshooting
FROM gcr.io/distroless/base-debian12:debug
# Includes busybox shell at /busybox/sh
```

### Scratch

**Advantages**:
- Absolute minimum size
- Perfect for static binaries

**Best Practices**:

```dockerfile
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o app

FROM scratch
COPY --from=builder /app/app /app
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
ENTRYPOINT ["/app"]
```

### Language-Specific Recommendations

**Python**:
- Development: `python:3.11`
- Production: `python:3.11-slim` or `python:3.11-alpine`
- Minimal: Custom distroless with Python runtime

**Node.js**:
- Development: `node:20`
- Production: `node:20-alpine`
- Minimal: `node:20-alpine` with multi-stage build

**Go**:
- Build: `golang:1.21`
- Runtime: `alpine:3.19`, `distroless/static`, or `scratch`

**Rust**:
- Build: `rust:1.75`
- Runtime: `debian:bookworm-slim` or `distroless/cc`

**Java**:
- Development: `eclipse-temurin:21`
- Production: `eclipse-temurin:21-jre-alpine`
- Minimal: `gcr.io/distroless/java21`

---

## .dockerignore Best Practices

The `.dockerignore` file prevents unnecessary files from being sent to the build context, speeding up builds and reducing image size.

### Essential .dockerignore Template

```gitignore
# Version control
.git
.gitignore
.gitattributes

# CI/CD
.github
.gitlab-ci.yml
.travis.yml
Jenkinsfile

# Documentation
README.md
CHANGELOG.md
LICENSE
docs/
*.md

# Development
.vscode
.idea
*.swp
*.swo
*~

# Build artifacts
target/
dist/
build/
*.o
*.a
*.so
*.dylib
*.dll
*.exe

# Dependencies (rebuild in container)
node_modules/
vendor/
__pycache__/
*.pyc
.pytest_cache/

# Logs
*.log
logs/

# Environment
.env
.env.*
!.env.example

# Testing
coverage/
.coverage
htmlcov/
test-results/

# OS files
.DS_Store
Thumbs.db

# Temporary files
tmp/
temp/
*.tmp

# Large files
*.zip
*.tar.gz
*.iso
*.pdf
```

### Language-Specific Patterns

**Python**:

```gitignore
__pycache__/
*.py[cod]
*$py.class
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
dist/
build/
```

**Node.js**:

```gitignore
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.yarn/cache
.yarn/unplugged
.pnp.*
coverage/
.next/
.nuxt/
dist/
```

**Go**:

```gitignore
vendor/
*.test
*.out
coverage.txt
.go-build-cache/
```

**Rust**:

```gitignore
target/
Cargo.lock
**/*.rs.bk
```

### Performance Impact

**Without .dockerignore**:

```bash
# Build context: 500MB (includes node_modules, .git, etc.)
$ docker build .
Sending build context to Docker daemon  500MB
```

**With .dockerignore**:

```bash
# Build context: 5MB (only source files)
$ docker build .
Sending build context to Docker daemon  5MB
```

### Testing .dockerignore

```bash
# Show what's in build context
docker build --no-cache --progress=plain . 2>&1 | grep "COPY"

# Verify context size
du -sh .
docker build --no-cache . 2>&1 | grep "Sending build context"
```

---

## Security Hardening

Docker security involves minimizing attack surface, running as non-root, and following security best practices.

### Non-Root User

**Why**: Processes in containers shouldn't run as root. If container is compromised, root access amplifies damage.

**Basic Pattern**:

```dockerfile
FROM alpine:3.19

# Create user
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Create app directory with correct ownership
WORKDIR /app
RUN chown appuser:appuser /app

# Switch to non-root user
USER appuser

# Now runs as appuser
COPY --chown=appuser:appuser . .
CMD ["./app"]
```

**Debian/Ubuntu**:

```dockerfile
FROM debian:bookworm-slim

RUN useradd -r -u 1000 -m -s /bin/bash appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

WORKDIR /app
USER appuser
```

**Using numeric UID** (more secure):

```dockerfile
FROM alpine:3.19
RUN adduser -D -u 10001 appuser
USER 10001
```

### Minimal Attack Surface

**Reduce installed packages**:

```dockerfile
FROM debian:bookworm-slim

# Install only what's needed
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl && \
    # Clean up
    rm -rf /var/lib/apt/lists/* \  # Safe: cleaning package manager cache
    /tmp/* \
    /var/tmp/*
```

**Remove unnecessary files**:

```dockerfile
FROM node:20-alpine

# Remove npm after install (if not needed)
RUN npm install -g pm2 && \
    npm cache clean --force && \
    rm -rf /root/.npm
```

**Use distroless**:

```dockerfile
FROM gcr.io/distroless/static-debian12
# No shell, no package manager, minimal attack surface
```

### Secret Management

**NEVER**:

```dockerfile
# WRONG - secret in layer history
FROM alpine
RUN echo "API_KEY=secret123" > /app/.env
```

**Correct Approaches**:

```dockerfile
# Build-time secrets (BuildKit)
FROM alpine
RUN --mount=type=secret,id=api_key \
    API_KEY=$(cat /run/secrets/api_key) && \
    configure-app --key=$API_KEY

# Build with:
# docker build --secret id=api_key,src=./secret.txt .
```

```dockerfile
# Runtime secrets via environment
FROM alpine
CMD ["sh", "-c", "app --key=$API_KEY"]

# Run with:
# docker run -e API_KEY=$API_KEY myapp
```

### Read-Only Filesystem

```dockerfile
FROM alpine:3.19

# App runs with read-only root filesystem
# Must specify writable volumes
USER 10001
CMD ["./app"]

# Run with:
# docker run --read-only -v /app/tmp:/app/tmp myapp
```

### Scan for Vulnerabilities

```bash
# Docker Scout
docker scout cves myapp:latest

# Trivy
trivy image myapp:latest

# Snyk
snyk container test myapp:latest

# Grype
grype myapp:latest
```

### Security Best Practices Checklist

- [ ] Run as non-root user
- [ ] Use minimal base image (alpine, distroless, scratch)
- [ ] No secrets in image layers
- [ ] Scan for CVEs regularly
- [ ] Use specific image tags (not `latest`)
- [ ] Minimize installed packages
- [ ] Remove build tools from final image
- [ ] Use read-only root filesystem where possible
- [ ] Implement health checks
- [ ] Set resource limits
- [ ] Use multi-stage builds
- [ ] Keep base images updated
- [ ] Sign images (Docker Content Trust)
- [ ] Verify image signatures
- [ ] Use private registries for sensitive images

### Security Scanning in CI/CD

```yaml
# GitHub Actions example
- name: Build image
  run: docker build -t myapp:${{ github.sha }} .

- name: Scan with Trivy
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: myapp:${{ github.sha }}
    exit-code: '1'
    severity: 'CRITICAL,HIGH'
```

---

## Image Size Optimization

Smaller images = faster pulls, less storage, quicker starts.

### Size Reduction Techniques

**1. Multi-Stage Builds**:

```dockerfile
# Before: 1.2GB
FROM python:3.11
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]

# After: 150MB
FROM python:3.11-slim AS builder
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY app.py .
CMD ["python", "app.py"]
```

**2. Minimize Layers**:

```dockerfile
# Before: Multiple layers
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y git
RUN apt-get clean

# After: Single layer
RUN apt-get update && \
    apt-get install -y curl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
```

**3. Remove Build Dependencies**:

```dockerfile
FROM python:3.11-slim

# Install, use, remove in one layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    pip install --no-cache-dir numpy && \
    apt-get purge -y --auto-remove gcc && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
```

**4. Use .dockerignore**:

```bash
# Reduces build context from 500MB to 5MB
# See .dockerignore section above
```

**5. Optimize Dependencies**:

```dockerfile
# Python: Use --no-cache-dir
RUN pip install --no-cache-dir -r requirements.txt

# Node: Use npm ci and clean cache
RUN npm ci --only=production && \
    npm cache clean --force

# Go: Use -ldflags to strip debug info
RUN go build -ldflags="-s -w" -o app
```

**6. Choose Smaller Base Images**:

```dockerfile
# 1GB → 150MB → 50MB → 10MB
python:3.11 → python:3.11-slim → python:3.11-alpine → distroless
```

**7. Compress Binaries**:

```dockerfile
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .

# Strip and compress
RUN CGO_ENABLED=0 go build \
    -ldflags="-s -w" \
    -trimpath \
    -o app && \
    upx --best --lzma app

FROM scratch
COPY --from=builder /app/app /app
ENTRYPOINT ["/app"]
```

### Measuring Image Size

```bash
# View image size
docker images myapp

# View layer sizes
docker history myapp

# Detailed layer analysis
docker history --no-trunc --format "{{.Size}}\t{{.CreatedBy}}" myapp

# Use dive for interactive analysis
dive myapp
```

### Size Optimization Targets

| Image Type | Target Size | Acceptable Size |
|------------|-------------|-----------------|
| Static binary (Go, Rust) | < 20MB | < 50MB |
| Node.js app | < 100MB | < 200MB |
| Python app | < 150MB | < 300MB |
| Java app | < 200MB | < 400MB |

### Real-World Example

**Before Optimization** (Node.js):

```dockerfile
FROM node:20
WORKDIR /app
COPY . .
RUN npm install
CMD ["npm", "start"]
# Size: 1.1GB
```

**After Optimization**:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
USER node
CMD ["node", "index.js"]
# Size: 180MB (83% reduction)
```

---

## Build Time Optimization

Faster builds = faster iteration, lower CI costs, happier developers.

### BuildKit Features

Enable BuildKit:

```bash
# Environment variable
export DOCKER_BUILDKIT=1

# Or in daemon.json
{
  "features": {
    "buildkit": true
  }
}
```

**Parallel Stage Execution**:

```dockerfile
# These stages build in parallel
FROM alpine AS stage1
RUN expensive-operation-1

FROM alpine AS stage2
RUN expensive-operation-2

FROM alpine
COPY --from=stage1 /output1 /
COPY --from=stage2 /output2 /
```

**Cache Mounts**:

```dockerfile
# Persist cache across builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

**SSH Mounts** (for private repos):

```dockerfile
RUN --mount=type=ssh \
    git clone git@github.com:org/private-repo.git
```

### Layer Caching Optimization

**Order Dependencies Before Code**:

```dockerfile
# Dependencies cached separately from code
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build
```

**Split Dependency Files**:

```dockerfile
# Base dependencies (rarely change)
COPY requirements-base.txt .
RUN pip install -r requirements-base.txt

# App dependencies (change more often)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Code (changes frequently)
COPY . .
```

### Parallel Builds

```bash
# Build multiple images in parallel
docker build -t app1 ./app1 &
docker build -t app2 ./app2 &
wait
```

### Remote Caching

```bash
# Push cache
docker buildx build \
  --cache-to=type=registry,ref=myregistry/myapp:buildcache \
  .

# Pull cache
docker buildx build \
  --cache-from=type=registry,ref=myregistry/myapp:buildcache \
  .
```

### Incremental Builds

```dockerfile
# Use dependency layers from previous build
COPY --from=myapp:cache /root/.cache /root/.cache
RUN pip install -r requirements.txt
```

### Build Performance Metrics

```bash
# Time the build
time docker build -t myapp .

# Detailed timing with BuildKit
docker buildx build --progress=plain -t myapp . 2>&1 | grep "CACHED"

# Find slow layers
docker build --progress=plain -t myapp . 2>&1 | \
  grep -E "^#[0-9]+ .*" | \
  awk '{print $1, $2, $3, $NF}'
```

### Common Build Time Improvements

| Optimization | Time Saved |
|--------------|------------|
| Enable BuildKit | 10-30% |
| Layer caching | 50-90% (on cache hit) |
| Cache mounts | 30-60% |
| Parallel stages | 20-40% |
| .dockerignore | 5-20% |
| Remote cache | 40-80% (on cache hit) |

---

## Runtime Optimization

Optimize container startup, memory usage, and runtime performance.

### Startup Time

**Use ENTRYPOINT + CMD**:

```dockerfile
# Faster than shell form
ENTRYPOINT ["python"]
CMD ["app.py"]

# vs slower shell form
CMD python app.py
```

**Precompile Assets**:

```dockerfile
# Python
RUN python -m compileall /app

# Node.js
RUN npm run build

# Java
RUN mvn package
```

**Lazy Loading**:

```python
# Load heavy imports only when needed
def process_data():
    import pandas as pd  # Import when function called
    return pd.read_csv('data.csv')
```

### Memory Optimization

**Set Memory Limits**:

```dockerfile
# Document expected memory usage
LABEL memory.recommended="512m"
LABEL memory.minimum="256m"
```

```bash
# Run with limits
docker run -m 512m myapp
```

**Use Memory-Efficient Base Images**:

```dockerfile
# Alpine uses musl (lighter than glibc)
FROM python:3.11-alpine
```

**Optimize Application**:

```python
# Generator instead of list
def process_large_file(filename):
    for line in open(filename):  # Streams
        yield process(line)

# vs
def process_large_file(filename):
    return [process(line) for line in open(filename).readlines()]  # Loads all
```

### CPU Optimization

**Compiled Languages**:

```dockerfile
# Go: Enable all optimizations
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -gcflags="-l" -o app
```

```dockerfile
# Rust: Release mode
RUN cargo build --release
```

**Python**: Use PyPy for CPU-bound tasks:

```dockerfile
FROM pypy:3.10-slim
# 3-5x faster for CPU-bound code
```

**Multi-Threading**:

```dockerfile
# Node.js: Use all CPUs
ENV UV_THREADPOOL_SIZE=4
CMD ["node", "--max-old-space-size=2048", "app.js"]
```

### Disk I/O Optimization

**Use tmpfs for temporary files**:

```bash
docker run --tmpfs /tmp myapp
```

**Optimize logging**:

```dockerfile
# Log to stdout/stderr (not files)
RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log
```

### Network Optimization

**Connection Pooling**:

```python
# Reuse connections
import requests
session = requests.Session()
```

**DNS Caching**:

```dockerfile
# Add to /etc/resolv.conf
RUN echo "options ndots:0" >> /etc/resolv.conf
```

### Runtime Best Practices

- [ ] Use exec form for ENTRYPOINT/CMD
- [ ] Set appropriate resource limits
- [ ] Precompile/prebuild assets
- [ ] Use streaming/generators for large data
- [ ] Enable connection pooling
- [ ] Log to stdout/stderr
- [ ] Use health checks
- [ ] Implement graceful shutdown
- [ ] Use appropriate concurrency settings
- [ ] Monitor resource usage

---

## Dockerfile Best Practices

Comprehensive guide to writing maintainable, secure, and efficient Dockerfiles.

### Instruction Order

```dockerfile
# 1. Base image (least likely to change)
FROM python:3.11-slim

# 2. Metadata
LABEL maintainer="team@example.com"
LABEL version="1.0.0"

# 3. Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 4. System packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache

# 5. Application user
RUN useradd -r -u 1000 appuser

# 6. Working directory
WORKDIR /app

# 7. Dependencies (changes less than code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 8. Application code (changes frequently)
COPY --chown=appuser:appuser . .

# 9. Switch to non-root user
USER appuser

# 10. Port documentation
EXPOSE 8000

# 11. Health check
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1

# 12. Default command
CMD ["python", "app.py"]
```

### Combine RUN Commands

**Wrong**:

```dockerfile
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y git
RUN rm -rf /var/lib/apt/lists/*
# Creates 4 layers, last cleanup doesn't reduce size
```

**Correct**:

```dockerfile
RUN apt-get update && \
    apt-get install -y \
      curl \
      git && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
# Single layer, cleanup works
```

### Use Specific Tags

**Wrong**:

```dockerfile
FROM python:latest  # Unpredictable, breaks reproducibility
```

**Correct**:

```dockerfile
FROM python:3.11.7-slim-bookworm  # Specific, reproducible
```

### Use COPY, Not ADD

```dockerfile
# ADD has implicit behaviors (tar extraction, URL download)
ADD archive.tar.gz /app  # Unexpected extraction

# COPY is explicit and predictable
COPY archive.tar.gz /app  # Just copies
```

Use ADD only when you need:

```dockerfile
ADD https://example.com/file.tar.gz /tmp/  # Remote URL
ADD archive.tar.gz /app/  # Auto-extraction
```

### Exec Form vs Shell Form

**Shell Form** (runs in `/bin/sh -c`):

```dockerfile
CMD python app.py
# PID 1 is shell, app is subprocess
# Doesn't receive signals properly
```

**Exec Form** (runs directly):

```dockerfile
CMD ["python", "app.py"]
# PID 1 is python process
# Receives signals (SIGTERM) for graceful shutdown
```

### Environment Variables

**Group Related Variables**:

```dockerfile
ENV APP_HOME=/app \
    APP_USER=appuser \
    APP_PORT=8000
```

**Use ARG for Build-Time Variables**:

```dockerfile
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

ARG BUILD_DATE
LABEL build_date="${BUILD_DATE}"
```

### WORKDIR Best Practices

```dockerfile
# Use absolute paths
WORKDIR /app

# Creates directory if it doesn't exist
WORKDIR /app/src

# Affects subsequent commands
COPY . .  # Copies to /app/src
```

### Metadata Labels

```dockerfile
LABEL org.opencontainers.image.title="My App"
LABEL org.opencontainers.image.description="Description"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="team@example.com"
LABEL org.opencontainers.image.source="https://github.com/org/repo"
LABEL org.opencontainers.image.licenses="MIT"
```

### Avoid Unnecessary Files

Use `.dockerignore`:

```gitignore
.git
.env
*.md
node_modules
__pycache__
```

### Pin Package Versions

**Wrong**:

```dockerfile
RUN pip install flask  # Unpredictable version
```

**Correct**:

```dockerfile
RUN pip install flask==3.0.0  # Specific version
```

Or better yet:

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
# requirements.txt has pinned versions
```

### Common Anti-Patterns

**Installing Recommended Packages**:

```dockerfile
# Installs 100+ unnecessary packages
RUN apt-get install -y python3

# Installs only python3
RUN apt-get install -y --no-install-recommends python3
```

**Not Cleaning Package Cache**:

```dockerfile
# Cache remains in layer (50MB wasted)
RUN apt-get update && apt-get install -y curl

# Cache cleaned (efficient)
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
```

**Running as Root**:

```dockerfile
# Runs as root (security risk)
CMD ["python", "app.py"]

# Runs as non-root (secure)
USER appuser
CMD ["python", "app.py"]
```

---

## BuildKit Features

BuildKit is Docker's modern build engine with powerful features.

### Enable BuildKit

```bash
# Per-build
DOCKER_BUILDKIT=1 docker build .

# Globally in daemon.json
{
  "features": { "buildkit": true }
}

# Use buildx (BuildKit-based)
docker buildx build .
```

### Cache Mounts

**Package Manager Caches**:

```dockerfile
# pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# npm cache
RUN --mount=type=cache,target=/root/.npm \
    npm install

# go modules
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# apt cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y build-essential
```

**Build Caches**:

```dockerfile
# Go build cache
RUN --mount=type=cache,target=/root/.cache/go-build \
    go build -o app

# Cargo build cache
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    cargo build --release
```

### Secret Mounts

**Build-Time Secrets** (not stored in layers):

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm install

# Build with:
docker build --secret id=npmrc,src=$HOME/.npmrc .
```

**Git Credentials**:

```dockerfile
RUN --mount=type=secret,id=gitconfig,target=/root/.gitconfig \
    --mount=type=secret,id=ssh,target=/root/.ssh/id_rsa \
    git clone git@github.com:org/private-repo.git
```

### SSH Mounts

```dockerfile
RUN --mount=type=ssh \
    git clone git@github.com:org/repo.git

# Build with:
docker build --ssh default .
```

### Bind Mounts

**Mount Host Directory** (read-only):

```dockerfile
RUN --mount=type=bind,source=.,target=/src \
    cp /src/config.json /app/
```

### Heredoc Syntax

**Inline Files**:

```dockerfile
COPY <<EOF /app/config.json
{
  "host": "localhost",
  "port": 8000
}
EOF
```

**Multi-Line Scripts**:

```dockerfile
RUN <<EOF
apt-get update
apt-get install -y curl
rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
EOF
```

**Python Script**:

```dockerfile
RUN python <<EOF
import os
import json
config = {"env": os.getenv("ENV", "prod")}
with open("/app/config.json", "w") as f:
    json.dump(config, f)
EOF
```

### Multi-Platform Builds

```dockerfile
FROM --platform=$BUILDPLATFORM golang:1.21 AS builder
ARG TARGETPLATFORM
ARG BUILDPLATFORM

WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 go build -o app

FROM alpine:3.19
COPY --from=builder /app/app /app
CMD ["/app"]
```

```bash
# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myapp:latest \
  --push \
  .
```

### Parallel Stages

```dockerfile
# These build in parallel
FROM alpine AS fetch-dep1
RUN wget https://example.com/dep1.tar.gz

FROM alpine AS fetch-dep2
RUN wget https://example.com/dep2.tar.gz

# Uses results from both parallel stages
FROM alpine
COPY --from=fetch-dep1 /dep1.tar.gz .
COPY --from=fetch-dep2 /dep2.tar.gz .
```

### Build Arguments with Defaults

```dockerfile
ARG NODE_VERSION=20
ARG ALPINE_VERSION=3.19

FROM node:${NODE_VERSION}-alpine${ALPINE_VERSION}
```

```bash
# Override at build time
docker build --build-arg NODE_VERSION=18 .
```

---

## Health Checks and Signals

Ensure containers are healthy and handle signals gracefully.

### Health Checks

**Basic Health Check**:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

**Without curl**:

```dockerfile
# Python
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Node.js
HEALTHCHECK CMD node -e "require('http').get('http://localhost:8000/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"

# Using application binary
HEALTHCHECK CMD /app/healthcheck || exit 1
```

**Health Check Script**:

```dockerfile
COPY healthcheck.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/healthcheck.sh
HEALTHCHECK CMD healthcheck.sh
```

```bash
#!/bin/sh
# healthcheck.sh
response=$(wget -q -O- http://localhost:8000/health 2>&1)
if [ $? -ne 0 ]; then
  exit 1
fi
echo "$response" | grep -q "healthy" || exit 1
exit 0
```

### Signal Handling

**PID 1 Problem**:

```dockerfile
# WRONG: Shell as PID 1, doesn't forward signals
CMD python app.py

# CORRECT: App as PID 1, receives signals
CMD ["python", "app.py"]
```

**Graceful Shutdown (Python)**:

```python
import signal
import sys

def signal_handler(sig, frame):
    print("Shutting down gracefully...")
    # Clean up resources
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

**Graceful Shutdown (Node.js)**:

```javascript
process.on('SIGTERM', () => {
  console.log('SIGTERM signal received: closing HTTP server')
  server.close(() => {
    console.log('HTTP server closed')
    process.exit(0)
  })
})
```

**Graceful Shutdown (Go)**:

```go
c := make(chan os.Signal, 1)
signal.Notify(c, os.Interrupt, syscall.SIGTERM)

go func() {
    <-c
    fmt.Println("Shutting down...")
    cleanup()
    os.Exit(0)
}()
```

**Using tini (Init System)**:

```dockerfile
FROM alpine:3.19

# Install tini
RUN apk add --no-cache tini

# Use tini as entrypoint
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["python", "app.py"]
```

### Docker Compose Health Checks

```yaml
services:
  app:
    build: .
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 40s
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### Checking Health Status

```bash
# Check health status
docker ps

# Inspect health
docker inspect --format='{{json .State.Health}}' container_name

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' container_name
```

---

## Resource Limits

Set CPU, memory, and other resource constraints.

### Memory Limits

```dockerfile
# Document limits in Dockerfile
LABEL resources.memory.min="256m"
LABEL resources.memory.recommended="512m"
LABEL resources.memory.max="1g"
```

```bash
# Set at runtime
docker run -m 512m --memory-reservation 256m myapp

# Memory swap limit
docker run -m 512m --memory-swap 1g myapp
```

### CPU Limits

```bash
# CPU shares (relative weight)
docker run --cpu-shares 1024 myapp

# CPU quota (hard limit)
docker run --cpus 1.5 myapp

# Specific CPUs
docker run --cpuset-cpus 0,1 myapp
```

### Docker Compose

```yaml
services:
  app:
    image: myapp
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### PID Limit

```bash
# Limit number of processes
docker run --pids-limit 100 myapp
```

### Disk I/O Limits

```bash
# Block I/O weight
docker run --blkio-weight 500 myapp

# Read/write BPS
docker run \
  --device-read-bps /dev/sda:10mb \
  --device-write-bps /dev/sda:10mb \
  myapp
```

### Monitoring Resource Usage

```bash
# Live stats
docker stats

# Container resource usage
docker stats container_name

# Formatted output
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Kubernetes Resource Limits

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: app
    image: myapp:latest
    resources:
      requests:
        memory: "256Mi"
        cpu: "500m"
      limits:
        memory: "1Gi"
        cpu: "2000m"
```

---

## Performance Benchmarking

### Build Time Comparison

```bash
# Measure build time
time docker build -t myapp:v1 .

# Clear cache and rebuild
docker builder prune -af
time docker build -t myapp:v1 .
```

### Image Size Comparison

```bash
# Compare sizes
docker images | grep myapp

# Layer breakdown
docker history myapp:v1
docker history myapp:v2

# Detailed analysis
dive myapp:v1
```

### Startup Time

```bash
# Measure container start time
time docker run --rm myapp:v1 /bin/true

# With application startup
docker run -d --name test myapp:v1
docker logs -f test  # Watch for "Started" message
```

### Runtime Performance

```bash
# CPU/Memory during operation
docker stats test

# Load testing
ab -n 10000 -c 100 http://localhost:8000/
```

---

## Real-World Optimization Examples

### Example 1: Python Flask App

**Before** (540MB):

```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
```

**After** (95MB):

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
RUN useradd -r -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser
ENV PATH=/root/.local/bin:$PATH
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"
CMD ["python", "app.py"]
```

### Example 2: Node.js Express App

**Before** (1.1GB):

```dockerfile
FROM node:20
WORKDIR /app
COPY . .
RUN npm install
CMD ["npm", "start"]
```

**After** (175MB):

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN addgroup -g 1000 node && \
    adduser -D -u 1000 -G node node && \
    chown -R node:node /app
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s CMD node healthcheck.js
CMD ["node", "server.js"]
```

### Example 3: Go Microservice

**Before** (800MB):

```dockerfile
FROM golang:1.21
WORKDIR /app
COPY . .
RUN go build -o app
CMD ["./app"]
```

**After** (8MB):

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-s -w" \
    -trimpath \
    -o app

FROM scratch
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app/app /app
USER 65534:65534
HEALTHCHECK NONE
ENTRYPOINT ["/app"]
```

---

## Conclusion

Docker optimization is multi-faceted:

1. **Size**: Multi-stage builds, minimal base images, cleanup
2. **Speed**: Layer caching, BuildKit, parallel stages
3. **Security**: Non-root users, minimal attack surface, scanning
4. **Performance**: Proper signals, resource limits, health checks

Follow these practices systematically for optimal Docker images.
