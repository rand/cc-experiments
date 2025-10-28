---
name: containers-container-security
description: Hardening container images for production
---



# Container Security

**Scope**: USER directive, distroless images, vulnerability scanning, secrets management
**Lines**: ~280
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Hardening container images for production
- Scanning images for vulnerabilities
- Managing secrets securely in containers
- Implementing least privilege access
- Choosing secure base images
- Auditing container security posture
- Complying with security policies
- Preventing container breakout attacks

## Core Concepts

### Container Security Principles

**Defense in depth**: Layer multiple security controls.

**Key principles**:
- **Least privilege**: Run as non-root, minimal permissions
- **Minimal attack surface**: Smallest possible image
- **Immutability**: Containers are read-only
- **Secrets management**: Never hardcode credentials
- **Vulnerability scanning**: Regular image audits
- **Runtime security**: Monitor container behavior

**Threat model**:
```
Attack Vector              → Mitigation
─────────────────────────────────────────────
Vulnerable dependencies   → Scan images (Trivy)
Running as root           → USER directive
Excessive permissions     → Drop capabilities
Hardcoded secrets         → Secrets management
Large attack surface      → Distroless/minimal images
Outdated base images      → Pin + update regularly
```

---

## Running as Non-Root

### Why Non-Root?

**Problem**: Default containers run as `root` (UID 0).

**Risks**:
- Container escape → root on host
- File system modifications
- Network configuration changes
- Process manipulation

**Solution**: Run as unprivileged user.

### Creating Non-Root User

**Method 1: Create user in Dockerfile**:
```dockerfile
FROM python:3.11-slim

# Create user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app and change ownership
COPY . .
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

CMD ["python", "app.py"]
```

**Method 2: Use existing user**:
```dockerfile
FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package.json .
RUN npm install

COPY . .

# Use existing 'node' user (UID 1000)
USER node

CMD ["node", "index.js"]
```

**Method 3: Numeric UID (more portable)**:
```dockerfile
FROM alpine:3.19

RUN adduser -D -u 1000 appuser

USER 1000   # Numeric UID (works even if username changes)

CMD ["./app"]
```

### Fixing Permission Issues

**Problem**: Non-root user can't write to directories.

**Solution**: Change ownership or use mounted volumes correctly.

```dockerfile
FROM python:3.11-slim

RUN useradd -m appuser

WORKDIR /app

COPY --chown=appuser:appuser . .

RUN mkdir /app/logs && chown appuser:appuser /app/logs

USER appuser

CMD ["python", "app.py"]
```

**For volumes**:
```yaml
# docker-compose.yml
services:
  app:
    user: "${UID}:${GID}"   # Match host user
    volumes:
      - ./data:/app/data
```

---

## Minimal Base Images

### Image Security Comparison

| Base Image | Size | Shell | Package Manager | CVEs (Typical) |
|------------|------|-------|-----------------|----------------|
| `ubuntu:22.04` | ~77MB | Yes | apt | High |
| `python:3.11` | ~1GB | Yes | apt | High |
| `python:3.11-slim` | ~180MB | Yes | apt | Medium |
| `alpine:3.19` | ~7MB | Yes | apk | Low |
| `distroless/python3` | ~50MB | No | No | Very Low |
| `scratch` | 0MB | No | No | None |

### Distroless Images

**Purpose**: Runtime-only images (no shell, no package manager).

**Benefits**:
- **Smaller attack surface**: No shell to exploit
- **Fewer CVEs**: Minimal dependencies
- **Smaller size**: Only runtime libraries
- **Immutable**: Can't install malware at runtime

**Available variants**:
```
gcr.io/distroless/static-debian12       # Static binaries (Go, Rust)
gcr.io/distroless/base-debian12         # Requires glibc
gcr.io/distroless/python3-debian12      # Python runtime
gcr.io/distroless/nodejs20-debian12     # Node.js runtime
gcr.io/distroless/java17-debian12       # Java runtime
```

### Using Distroless (Go Example)

```dockerfile
# Build stage
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o app

# Runtime stage with distroless
FROM gcr.io/distroless/static-debian12

COPY --from=builder /app/app /app

USER nonroot:nonroot   # Built-in non-root user (UID 65532)

ENTRYPOINT ["/app"]
```

**Debugging distroless** (no shell):
```dockerfile
# Use debug variant for troubleshooting
FROM gcr.io/distroless/static-debian12:debug

# Includes busybox shell for debugging
```

```bash
# Exec with shell in debug variant
docker exec -it container /busybox/sh
```

### Using Distroless (Python Example)

```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM gcr.io/distroless/python3-debian12

COPY --from=builder /root/.local /root/.local
COPY . /app

WORKDIR /app
ENV PATH=/root/.local/bin:$PATH

USER nonroot:nonroot

CMD ["app.py"]
```

---

## Vulnerability Scanning

### Tool: Trivy (Recommended)

**Install**:
```bash
# Mac
brew install trivy

# Linux
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy
```

**Scan image**:
```bash
# Scan for all vulnerabilities
trivy image python:3.11

# Only high/critical
trivy image --severity HIGH,CRITICAL python:3.11

# Scan local Dockerfile
trivy config Dockerfile

# Scan filesystem
trivy fs .

# Output as JSON
trivy image -f json -o results.json myapp:latest
```

**Example output**:
```
myapp:latest (debian 12.0)
===========================
Total: 45 (HIGH: 12, CRITICAL: 3)

┌────────────────┬─────────────┬──────────┬───────────────────┬───────────────┐
│    Library     │ Vulnerability│ Severity │ Installed Version │ Fixed Version │
├────────────────┼─────────────┼──────────┼───────────────────┼───────────────┤
│ openssl        │ CVE-2023-123│ CRITICAL │ 1.1.1n            │ 1.1.1w        │
│ curl           │ CVE-2023-456│ HIGH     │ 7.68.0            │ 7.88.1        │
└────────────────┴─────────────┴──────────┴───────────────────┴───────────────┘
```

### Fixing Vulnerabilities

**Step 1: Update base image**:
```dockerfile
# ❌ Old vulnerable image
FROM python:3.11

# ✅ Latest patched image
FROM python:3.11-slim-bookworm
```

**Step 2: Update dependencies**:
```dockerfile
# Update system packages
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
```

**Step 3: Pin secure versions**:
```dockerfile
# Pin specific package versions
RUN apt-get update && \
    apt-get install -y \
        curl=7.88.1-1 \
        openssl=1.1.1w-1 && \
    rm -rf /var/lib/apt/lists/*  # Safe: cleaning package manager cache
```

**Step 4: Remove unnecessary packages**:
```dockerfile
# Use multi-stage build to exclude build tools
FROM python:3.11 AS builder
RUN pip install -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
```

### CI/CD Integration

**GitHub Actions**:
```yaml
name: Security Scan
on: [push]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build image
        run: docker build -t myapp:latest .

      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:latest
          severity: 'CRITICAL,HIGH'
          exit-code: '1'   # Fail if vulnerabilities found
```

**GitLab CI**:
```yaml
security_scan:
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t myapp:latest .
    - wget -qO - https://github.com/aquasecurity/trivy/releases/download/v0.45.0/trivy_0.45.0_Linux-64bit.tar.gz | tar -xzf -
    - ./trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:latest
```

---

## Secrets Management

### ❌ Anti-Patterns (Never Do This)

**Hardcoded secrets**:
```dockerfile
# ❌ NEVER hardcode secrets
ENV API_KEY=sk-1234567890abcdef
ENV DATABASE_PASSWORD=mysecretpass
```

**Secrets in layers**:
```dockerfile
# ❌ Secret stored in layer history
COPY .env /app/.env
```

**Secrets in build args**:
```dockerfile
# ❌ Build args visible in history
ARG SECRET_KEY=abc123
```

### ✅ Best Practices

**Method 1: Runtime environment variables**:
```bash
# Pass at runtime (not in image)
docker run -e API_KEY=secret123 myapp:latest
```

**docker-compose.yml**:
```yaml
services:
  app:
    environment:
      - API_KEY=${API_KEY}   # From host environment
    env_file:
      - .env                  # From .env file (not committed)
```

**.env** (git-ignored):
```bash
API_KEY=sk-1234567890abcdef
DATABASE_PASSWORD=mysecretpass
```

**Method 2: Docker secrets (Swarm/Compose)**:
```yaml
# docker-compose.yml
services:
  app:
    secrets:
      - db_password
      - api_key

secrets:
  db_password:
    file: ./secrets/db_password.txt
  api_key:
    external: true   # From Docker secret store
```

**Access in container**:
```python
# Read from /run/secrets/db_password
with open('/run/secrets/db_password') as f:
    password = f.read().strip()
```

**Method 3: BuildKit secrets (build-time)**:
```dockerfile
# Use secret during build without storing in layer
RUN --mount=type=secret,id=github_token \
    git clone https://$(cat /run/secrets/github_token)@github.com/private/repo.git
```

**Build command**:
```bash
docker build --secret id=github_token,src=$HOME/.github_token .
```

**Method 4: External secret managers**:
```python
# Fetch from AWS Secrets Manager, Vault, etc.
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

api_key = get_secret('prod/api_key')
```

---

## Dropping Capabilities

### What Are Capabilities?

**Linux capabilities**: Fine-grained permissions (instead of all-or-nothing root).

**Default capabilities** (Docker):
```
CHOWN, DAC_OVERRIDE, FOWNER, FSETID, KILL, SETGID, SETUID,
SETPCAP, NET_BIND_SERVICE, NET_RAW, SYS_CHROOT, MKNOD,
AUDIT_WRITE, SETFCAP
```

### Dropping All Capabilities

```bash
# Run with no capabilities
docker run --cap-drop=ALL myapp:latest

# Add back only needed capabilities
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myapp:latest
```

**docker-compose.yml**:
```yaml
services:
  app:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE   # Only if binding to port <1024
```

**Common capabilities**:
- `NET_BIND_SERVICE` - Bind to ports <1024
- `NET_RAW` - Use RAW/PACKET sockets
- `SYS_TIME` - Set system time
- `SYS_ADMIN` - Admin operations (avoid!)

---

## Read-Only Root Filesystem

### Why Read-Only?

**Benefits**:
- Prevents runtime modifications
- Stops malware installation
- Enforces immutability

**Enable read-only**:
```bash
docker run --read-only myapp:latest
```

**docker-compose.yml**:
```yaml
services:
  app:
    read_only: true
    tmpfs:
      - /tmp        # Allow writes to /tmp
      - /var/run
```

**Dockerfile** (explicit tmp directories):
```dockerfile
FROM python:3.11-slim

RUN useradd -m appuser

WORKDIR /app
COPY . .

# Create writable directories
RUN mkdir -p /app/tmp /app/logs && \
    chown -R appuser:appuser /app/tmp /app/logs

USER appuser

CMD ["python", "app.py"]
```

**Run with read-only + tmpfs**:
```bash
docker run \
  --read-only \
  --tmpfs /tmp \
  --tmpfs /app/logs \
  myapp:latest
```

---

## Security Scanning Checklist

```
Image Hardening:
[ ] Run as non-root user (USER directive)
[ ] Use minimal base image (distroless/slim)
[ ] Pin base image versions (not :latest)
[ ] Remove unnecessary packages
[ ] Use multi-stage builds

Vulnerability Management:
[ ] Scan images with Trivy
[ ] Update base images regularly
[ ] Patch critical/high vulnerabilities
[ ] Integrate scanning in CI/CD
[ ] Monitor for new CVEs

Secrets:
[ ] Never hardcode secrets in Dockerfiles
[ ] Use runtime environment variables
[ ] Use Docker secrets or external secret managers
[ ] Git-ignore .env files
[ ] Use BuildKit secrets for build-time

Runtime Security:
[ ] Drop unnecessary capabilities (cap_drop)
[ ] Enable read-only root filesystem
[ ] Limit resources (CPU/memory)
[ ] Use security profiles (AppArmor/SELinux)
[ ] Enable Docker Content Trust (image signing)

Network Security:
[ ] Isolate containers with networks
[ ] Expose only necessary ports
[ ] Use TLS for inter-service communication
[ ] Implement network policies
```

---

## Security Best Practices

### Practice 1: Regularly Update Images

```bash
# Pull latest base image
docker pull python:3.11-slim

# Rebuild
docker build --no-cache -t myapp:latest .

# Rescan
trivy image myapp:latest
```

### Practice 2: Use Image Signing

```bash
# Enable Docker Content Trust
export DOCKER_CONTENT_TRUST=1

# Push signed image
docker push myapp:latest

# Pull (verifies signature)
docker pull myapp:latest
```

### Practice 3: Limit Container Resources

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          memory: 256M
    pids_limit: 100   # Prevent fork bombs
```

### Practice 4: Use Security Profiles

**AppArmor**:
```bash
docker run --security-opt apparmor=docker-default myapp:latest
```

**Seccomp** (restrict syscalls):
```bash
docker run --security-opt seccomp=/path/to/profile.json myapp:latest
```

**Custom seccomp profile**:
```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "syscalls": [
    {
      "names": ["read", "write", "open", "close"],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

---

## Common Security Anti-Patterns

❌ **Running as root**: No `USER` directive
✅ Create and use non-root user

❌ **Using :latest tag**: `FROM python:latest`
✅ Pin versions: `FROM python:3.11-slim`

❌ **Hardcoding secrets**: `ENV API_KEY=secret`
✅ Use runtime env vars or secret managers

❌ **Large base images**: `FROM ubuntu:22.04`
✅ Use minimal images: `FROM alpine` or distroless

❌ **No vulnerability scanning**: Deploying without scanning
✅ Integrate Trivy in CI/CD

❌ **Excessive capabilities**: Running with default caps
✅ Drop all, add only needed: `--cap-drop=ALL`

❌ **Writable filesystem**: No read-only restriction
✅ Enable read-only: `--read-only`

---

## Quick Reference

### Trivy Commands

```bash
# Scan image
trivy image myapp:latest

# Only critical/high
trivy image --severity CRITICAL,HIGH myapp:latest

# Ignore unfixed
trivy image --ignore-unfixed myapp:latest

# Scan Dockerfile
trivy config Dockerfile

# Scan IaC
trivy config .
```

### Security Hardening Template

```dockerfile
# Multi-stage build
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Minimal runtime
FROM gcr.io/distroless/python3-debian12

# Copy dependencies
COPY --from=builder /root/.local /root/.local

# Copy app
COPY --chown=nonroot:nonroot . /app

WORKDIR /app
ENV PATH=/root/.local/bin:$PATH

# Non-root user
USER nonroot:nonroot

# Run app
CMD ["app.py"]
```

---

## Related Skills

- `dockerfile-optimization.md` - Multi-stage builds, layer caching
- `docker-compose-development.md` - Compose security configurations
- `container-networking.md` - Network isolation
- `kubernetes-security.md` - Pod security policies

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
