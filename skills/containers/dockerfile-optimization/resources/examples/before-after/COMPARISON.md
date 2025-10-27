# Before/After Optimization Comparison

This directory contains examples showing the impact of Docker optimization techniques.

## Python Example

### Before (`python-before.Dockerfile`)
- Base: `python:3.11` (full image)
- Size: ~1.2GB
- Build time: ~120s (no cache optimization)
- Security: Runs as root
- Issues:
  - Full Python image includes unnecessary tools
  - Poor layer caching (COPY . . before pip install)
  - No health check
  - Shell form CMD (poor signal handling)

### After (`python-after.Dockerfile`)
- Base: `python:3.11-slim` (minimal)
- Size: ~150MB
- Build time: ~60s (first), ~10s (cached)
- Security: Non-root user (UID 1000)
- Improvements:
  - Multi-stage build separates build and runtime
  - Slim base image (87% size reduction)
  - Cache mounts for pip
  - Proper layer ordering for cache efficiency
  - Health check included
  - Exec form CMD for proper signal handling

**Size Reduction: 87% (1.2GB → 150MB)**
**Build Time: 50% faster (cache optimization)**

## Node.js Example

### Before (`node-before.Dockerfile`)
- Base: `node:20` (full image)
- Size: ~1.1GB
- Build time: ~90s
- Security: Runs as root
- Issues:
  - Full Node image with build tools
  - Includes dev dependencies in production
  - Poor caching (code before npm install)
  - No health check

### After (`node-after.Dockerfile`)
- Base: `node:20-alpine` (minimal)
- Size: ~180MB
- Build time: ~45s (first), ~8s (cached)
- Security: Non-root user (nodejs:nodejs)
- Improvements:
  - Alpine base (83% size reduction)
  - Multi-stage build
  - Production dependencies only
  - Cache mounts for npm
  - Proper layer ordering
  - Health check
  - Exec form CMD

**Size Reduction: 83% (1.1GB → 180MB)**
**Build Time: 50% faster (cache optimization)**

## Key Optimization Techniques Applied

### 1. Multi-Stage Builds
Separate build environment from runtime:
- Build stage: Has compilers, build tools, dev dependencies
- Runtime stage: Only production dependencies and application

### 2. Base Image Selection
Choose minimal base images:
- Python: `python:3.11-slim` instead of `python:3.11`
- Node: `node:20-alpine` instead of `node:20`
- Go/Rust: Use `scratch` or `distroless` for static binaries

### 3. Layer Caching Optimization
Order instructions for maximum cache reuse:
```dockerfile
# Good: Dependencies cached separately
COPY package.json .
RUN npm install
COPY . .

# Bad: Any code change invalidates npm install
COPY . .
RUN npm install
```

### 4. Cache Mounts (BuildKit)
Persist cache across builds:
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

### 5. Security Hardening
- Non-root user (useradd/adduser)
- Minimal attack surface (slim/alpine/distroless)
- No secrets in layers
- Regular vulnerability scanning

### 6. Runtime Optimization
- Health checks for monitoring
- Exec form for signal handling
- Resource limits documentation
- Proper environment variables

## Build Time Comparison

| Strategy | Before | After | Improvement |
|----------|--------|-------|-------------|
| Python (cold) | 120s | 60s | 50% faster |
| Python (cached) | 120s | 10s | 92% faster |
| Node (cold) | 90s | 45s | 50% faster |
| Node (cached) | 90s | 8s | 91% faster |

## Size Comparison

| Language | Before | After | Reduction |
|----------|--------|-------|-----------|
| Python | 1.2GB | 150MB | 87% |
| Node.js | 1.1GB | 180MB | 83% |
| Go (example) | 800MB | 8MB | 99% |

## Best Practices Checklist

Use the "after" examples as templates. They demonstrate:

- [x] Multi-stage builds
- [x] Minimal base images (slim/alpine)
- [x] Cache mount usage
- [x] Proper layer ordering
- [x] Non-root user
- [x] Health checks
- [x] Exec form CMD/ENTRYPOINT
- [x] Environment variables
- [x] Package manager cache cleanup
- [x] Dependency-first copying

## Testing the Examples

Build and compare:

```bash
# Build before version
docker build -f python-before.Dockerfile -t python-before .

# Build after version
docker build -f python-after.Dockerfile -t python-after .

# Compare sizes
docker images | grep python-

# Compare with dive
dive python-before
dive python-after
```

## Further Optimization

For even more optimization:
1. Use `distroless` or `scratch` for Go/Rust
2. Compress binaries with `upx`
3. Use `.dockerignore` aggressively
4. Consider `docker-slim` for automated optimization
5. Implement layer squashing for final images
6. Use BuildKit's `--cache-from` for CI/CD
