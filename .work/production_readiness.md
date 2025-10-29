# Production Readiness Checklist

> **Purpose**: Comprehensive checklist for ensuring applications are production-ready across security, reliability, performance, observability, and operational concerns.
>
> **Usage**: Review all sections before deploying to production. Each unchecked item represents a potential risk or gap.

---

## Table of Contents

1. [Infrastructure & Deployment](#1-infrastructure--deployment)
2. [Application Code](#2-application-code)
3. [Security & Compliance](#3-security--compliance)
4. [Observability](#4-observability)
5. [Documentation](#5-documentation)
6. [Testing](#6-testing)
7. [Operational Readiness](#7-operational-readiness)

---

## 1. Infrastructure & Deployment

### 1.1 Container Security

#### Base Images
- [ ] **Minimal base images**: Use distroless, alpine, or scratch images (not full OS)
- [ ] **Official images only**: Pull from verified publishers (docker.io/library, gcr.io/distroless)
- [ ] **Pinned versions**: Use specific tags (e.g., `python:3.11-alpine`, NOT `python:latest`)
- [ ] **Multi-stage builds**: Separate build and runtime stages to minimize attack surface
- [ ] **Vulnerability scanning**: Scan images with Trivy, Snyk, or Grype in CI/CD

**Example - Good**:
```dockerfile
# Multi-stage build with minimal runtime
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
USER nobody
ENTRYPOINT ["python", "app.py"]
```

**Example - Bad**:
```dockerfile
FROM python:latest  # Unpinned, large image
COPY . .
RUN pip install -r requirements.txt  # Running as root
CMD python app.py  # No entrypoint, runs as root
```

#### Non-Root Execution
- [ ] **Non-root user**: Run processes as non-root user (uid > 1000)
- [ ] **No privilege escalation**: Set `allowPrivilegeEscalation: false` in k8s
- [ ] **Read-only root filesystem**: Mount root filesystem as read-only where possible
- [ ] **Dropped capabilities**: Drop all Linux capabilities except required ones

**Example**:
```dockerfile
# Create non-root user
RUN addgroup -g 1001 appgroup && \
    adduser -D -u 1001 -G appgroup appuser

# Switch to non-root
USER appuser

# Or use numeric UID for better security
USER 1001:1001
```

```yaml
# Kubernetes SecurityContext
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

#### Resource Limits
- [ ] **Memory limits**: Set memory requests and limits (prevent OOM kills)
- [ ] **CPU limits**: Set CPU requests and limits (prevent noisy neighbors)
- [ ] **Storage limits**: Set ephemeral-storage limits
- [ ] **PID limits**: Limit process count (prevent fork bombs)

**Example - Kubernetes**:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
    ephemeral-storage: "1Gi"
  limits:
    memory: "512Mi"
    cpu: "500m"
    ephemeral-storage: "2Gi"
```

**Example - Docker Compose**:
```yaml
services:
  app:
    image: myapp:1.0.0
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    pids_limit: 100
```

#### Network Security
- [ ] **Network policies**: Define ingress/egress rules (least privilege)
- [ ] **Service mesh**: Use Istio, Linkerd for mTLS and traffic control
- [ ] **Private networks**: Deploy in private subnets, use NAT gateways
- [ ] **Firewall rules**: Restrict access to known IPs/ranges

### 1.2 Secrets Management

#### Externalized Secrets
- [ ] **No hardcoded secrets**: Zero credentials in code, config files, or env vars
- [ ] **Secrets manager**: Use Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault
- [ ] **Environment separation**: Different secrets per environment (dev/staging/prod)
- [ ] **Secret rotation**: Automate secret rotation (30-90 day cycles)
- [ ] **Access controls**: IAM/RBAC policies restrict secret access
- [ ] **Audit logging**: Log all secret access attempts

**Anti-Pattern**:
```python
# NEVER DO THIS
DB_PASSWORD = "supersecret123"
API_KEY = "pk_live_abcd1234"
```

**Good Pattern**:
```python
import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Load from secrets manager
credential = DefaultAzureCredential()
client = SecretClient(vault_url=os.environ["VAULT_URL"], credential=credential)

db_password = client.get_secret("db-password").value
api_key = client.get_secret("api-key").value
```

**Kubernetes Secrets**:
```yaml
# External Secrets Operator
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: app-secrets
  data:
    - secretKey: db-password
      remoteRef:
        key: prod/db/password
```

#### Secret Injection
- [ ] **Runtime injection**: Inject secrets at runtime (not build time)
- [ ] **Memory-only storage**: Never write secrets to disk
- [ ] **Masked logging**: Redact secrets from logs, stack traces, errors
- [ ] **Process environment**: Clear sensitive env vars after reading

### 1.3 TLS/SSL Configuration

#### Certificate Management
- [ ] **Valid certificates**: Use trusted CA certificates (Let's Encrypt, DigiCert)
- [ ] **No self-signed certs**: Self-signed only for local dev, never production
- [ ] **Certificate rotation**: Automate renewal (cert-manager, ACME)
- [ ] **Strong ciphers**: TLS 1.2+ only, disable weak ciphers (RC4, 3DES)
- [ ] **Perfect forward secrecy**: Enable ECDHE key exchange
- [ ] **Certificate pinning**: Pin certificates for critical APIs (optional)

**Example - nginx**:
```nginx
server {
    listen 443 ssl http2;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    # TLS 1.2+ only
    ssl_protocols TLSv1.2 TLSv1.3;

    # Strong ciphers
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

**Example - Python (requests)**:
```python
import requests

# Verify certificates (NEVER set verify=False in production)
response = requests.get("https://api.example.com", verify=True)

# Use custom CA bundle if needed
response = requests.get("https://api.example.com", verify="/path/to/ca-bundle.crt")
```

#### mTLS (Mutual TLS)
- [ ] **Client certificates**: Require client certs for service-to-service communication
- [ ] **Certificate validation**: Verify client certificates against CA
- [ ] **Short-lived certificates**: Issue certificates with short TTL (hours/days)

### 1.4 Deployment Strategy

#### Zero-Downtime Deployment
- [ ] **Rolling updates**: Deploy incrementally (blue-green, canary, rolling)
- [ ] **Health checks**: Define readiness/liveness probes
- [ ] **Graceful shutdown**: Handle SIGTERM, drain connections (30-60s grace period)
- [ ] **Pre-stop hooks**: Clean up resources before termination
- [ ] **Connection draining**: Wait for in-flight requests to complete

**Example - Kubernetes**:
```yaml
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1

  template:
    spec:
      containers:
      - name: app
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3

        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]

      terminationGracePeriodSeconds: 60
```

**Example - Graceful Shutdown (Python)**:
```python
import signal
import sys
import time

shutdown_initiated = False

def handle_shutdown(signum, frame):
    global shutdown_initiated
    if shutdown_initiated:
        sys.exit(1)

    shutdown_initiated = True
    print("Received shutdown signal, draining connections...")

    # Stop accepting new requests
    server.stop_accepting()

    # Wait for in-flight requests (max 30s)
    for i in range(30):
        if server.active_connections == 0:
            break
        time.sleep(1)

    # Cleanup resources
    db_pool.close()
    cache.disconnect()

    print("Shutdown complete")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)
```

#### Rollback Strategy
- [ ] **Automated rollback**: Trigger rollback on failed health checks
- [ ] **Version tagging**: Tag images with semantic versions (not `latest`)
- [ ] **Previous version retention**: Keep N previous versions for rollback
- [ ] **Database migrations**: Ensure backward-compatible schema changes

### 1.5 High Availability

#### Redundancy
- [ ] **Multi-zone deployment**: Spread across availability zones
- [ ] **Replica count**: Run 3+ replicas per service (odd number for quorum)
- [ ] **Load balancing**: Distribute traffic across replicas
- [ ] **Pod disruption budgets**: Prevent simultaneous pod terminations

**Example**:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
```

#### Failover
- [ ] **Health-based routing**: Remove unhealthy instances from rotation
- [ ] **Circuit breakers**: Fail fast when downstream services are down
- [ ] **Retry logic**: Retry transient failures with exponential backoff
- [ ] **Fallback mechanisms**: Degrade gracefully when dependencies fail

---

## 2. Application Code

### 2.1 Error Handling

#### Exception Management
- [ ] **Catch specific exceptions**: Avoid bare `except:` clauses
- [ ] **Error context**: Include context in error messages (user ID, request ID)
- [ ] **Error boundaries**: Isolate failures to prevent cascading failures
- [ ] **Panic recovery**: Recover from panics in Go, prevent process crashes
- [ ] **Error propagation**: Propagate errors up the stack with context

**Anti-Pattern**:
```python
try:
    result = risky_operation()
except:  # Catches everything, hides bugs
    pass  # Silently swallows errors
```

**Good Pattern**:
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def process_request(request_id: str, user_id: str) -> Optional[Result]:
    try:
        result = risky_operation(user_id)
        return result
    except ValueError as e:
        logger.error(
            "Invalid input for user",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "error": str(e),
            },
        )
        return None
    except DatabaseError as e:
        logger.exception(
            "Database error during request",
            extra={"request_id": request_id, "user_id": user_id},
        )
        raise  # Re-raise for upstream handling
    except Exception as e:
        logger.exception(
            "Unexpected error",
            extra={"request_id": request_id, "user_id": user_id},
        )
        raise
```

#### Error Responses
- [ ] **Structured errors**: Return consistent error format (Problem Details RFC 7807)
- [ ] **Error codes**: Use meaningful error codes (not just HTTP status)
- [ ] **User-friendly messages**: Don't expose internal details to users
- [ ] **Debug information**: Include request ID for tracing

**Example**:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ErrorResponse:
    """RFC 7807 Problem Details"""
    type: str          # URI reference identifying the problem type
    title: str         # Short human-readable summary
    status: int        # HTTP status code
    detail: str        # Human-readable explanation
    instance: str      # URI reference identifying the occurrence
    request_id: Optional[str] = None

# Usage
error = ErrorResponse(
    type="https://api.example.com/errors/invalid-request",
    title="Invalid Request",
    status=400,
    detail="The 'email' field must be a valid email address",
    instance=f"/users/{user_id}",
    request_id=request_id,
)
```

### 2.2 Input Validation

#### Request Validation
- [ ] **Schema validation**: Validate all inputs against schema (Pydantic, JSON Schema)
- [ ] **Type checking**: Use static types (TypeScript, Python type hints, Rust types)
- [ ] **Bounds checking**: Validate ranges, lengths, sizes
- [ ] **Format validation**: Validate emails, URLs, dates, phone numbers
- [ ] **Whitelist validation**: Accept only known-good values (not blacklist)
- [ ] **Sanitization**: Sanitize inputs to prevent injection attacks

**Example - Pydantic**:
```python
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional

class UserCreateRequest(BaseModel):
    email: EmailStr  # Validates email format
    username: str = Field(..., min_length=3, max_length=32, regex="^[a-zA-Z0-9_]+$")
    age: Optional[int] = Field(None, ge=13, le=120)
    bio: Optional[str] = Field(None, max_length=500)

    @validator("username")
    def username_not_reserved(cls, v):
        reserved = {"admin", "root", "system"}
        if v.lower() in reserved:
            raise ValueError("Username is reserved")
        return v

# Usage
try:
    user = UserCreateRequest(**request_data)
except ValidationError as e:
    return ErrorResponse(
        type="validation-error",
        title="Validation Failed",
        status=400,
        detail=str(e),
        instance=request.path,
        request_id=request.id,
    )
```

#### SQL Injection Prevention
- [ ] **Parameterized queries**: Use prepared statements (NEVER string concatenation)
- [ ] **ORM usage**: Use ORMs with built-in escaping (SQLAlchemy, TypeORM)
- [ ] **Input escaping**: Escape special characters if raw SQL is unavoidable

**Anti-Pattern**:
```python
# NEVER DO THIS - SQL injection vulnerability
query = f"SELECT * FROM users WHERE email = '{email}'"
cursor.execute(query)
```

**Good Pattern**:
```python
# Parameterized query
query = "SELECT * FROM users WHERE email = %s"
cursor.execute(query, (email,))

# Or use ORM
user = session.query(User).filter(User.email == email).first()
```

#### XSS Prevention
- [ ] **Output encoding**: Encode HTML entities in templates
- [ ] **Content-Security-Policy**: Set CSP headers
- [ ] **Framework defaults**: Use framework escaping (React, Vue auto-escape)

### 2.3 Logging

#### Structured Logging
- [ ] **JSON format**: Log in structured format (JSON, not plain text)
- [ ] **Consistent fields**: Include standard fields (timestamp, level, message, context)
- [ ] **Request tracing**: Include request ID, user ID, session ID
- [ ] **Correlation IDs**: Propagate trace IDs across services
- [ ] **Log levels**: Use appropriate levels (DEBUG, INFO, WARN, ERROR, FATAL)
- [ ] **Sampling**: Sample high-volume logs (e.g., 1% of successful requests)

**Example**:
```python
import logging
import json
from datetime import datetime
from typing import Any, Dict

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)

    def log(self, level: str, message: str, **context: Any):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "service": "myapp",
            **context,
        }

        log_func = getattr(self.logger, level.lower())
        log_func(json.dumps(log_entry))

# Usage
logger = StructuredLogger(__name__)

logger.log(
    "INFO",
    "User login successful",
    user_id="user-123",
    request_id="req-456",
    ip_address="203.0.113.42",
    duration_ms=142,
)
```

#### Sensitive Data Redaction
- [ ] **PII masking**: Redact PII (SSN, credit cards, passwords)
- [ ] **Secret redaction**: Never log secrets, tokens, API keys
- [ ] **Request/response filtering**: Redact sensitive fields from HTTP logs

**Example**:
```python
import re
from typing import Any, Dict

SENSITIVE_FIELDS = {"password", "ssn", "credit_card", "api_key", "token"}

def redact_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redact sensitive fields"""
    redacted = {}
    for key, value in data.items():
        if key.lower() in SENSITIVE_FIELDS:
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive(value)
        elif isinstance(value, str):
            # Redact credit card numbers
            redacted[key] = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '****-****-****-****', value)
        else:
            redacted[key] = value
    return redacted

# Usage
logger.info("User registration", extra=redact_sensitive(request_data))
```

#### Log Aggregation
- [ ] **Centralized logging**: Send logs to aggregation service (ELK, Splunk, Datadog)
- [ ] **Log retention**: Define retention policies (30-90 days)
- [ ] **Log shipping**: Use log shippers (Fluentd, Logstash, Vector)

### 2.4 Type Safety

#### Static Typing
- [ ] **Type annotations**: Annotate all function signatures (Python, TypeScript)
- [ ] **Type checking**: Run mypy, pyright, or tsc in CI
- [ ] **Strict mode**: Enable strict type checking
- [ ] **No `any` types**: Avoid `any` in TypeScript, `Any` in Python

**Example - Python**:
```python
from typing import List, Optional, Dict, Union
from dataclasses import dataclass

@dataclass
class User:
    id: str
    email: str
    name: Optional[str] = None

def fetch_users(ids: List[str]) -> Dict[str, User]:
    """Fetch users by IDs. Returns mapping of ID to User."""
    users: Dict[str, User] = {}
    for user_id in ids:
        user = db.get_user(user_id)  # type: Optional[User]
        if user:
            users[user_id] = user
    return users

# Type checking in CI
# mypy --strict --disallow-untyped-defs --disallow-any-generics app.py
```

**Example - TypeScript**:
```typescript
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}

interface User {
  id: string;
  email: string;
  name?: string;
}

function fetchUsers(ids: string[]): Map<string, User> {
  const users = new Map<string, User>();
  for (const id of ids) {
    const user = db.getUser(id);  // User | null
    if (user !== null) {
      users.set(id, user);
    }
  }
  return users;
}
```

### 2.5 Concurrency & Thread Safety

#### Synchronization
- [ ] **Lock management**: Use proper locking (mutexes, semaphores)
- [ ] **Deadlock prevention**: Avoid nested locks, use lock ordering
- [ ] **Lock-free structures**: Use concurrent data structures (Go channels, Rust Arc/Mutex)
- [ ] **Atomic operations**: Use atomic operations for counters

**Example - Python**:
```python
import threading
from typing import Dict

class ThreadSafeCache:
    def __init__(self):
        self._cache: Dict[str, any] = {}
        self._lock = threading.RLock()  # Reentrant lock

    def get(self, key: str) -> any:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: any) -> None:
        with self._lock:
            self._cache[key] = value

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)
```

**Example - Go**:
```go
type SafeCounter struct {
    mu sync.RWMutex
    v  map[string]int
}

func (c *SafeCounter) Inc(key string) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.v[key]++
}

func (c *SafeCounter) Value(key string) int {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return c.v[key]
}
```

#### Async/Await Patterns
- [ ] **Proper await usage**: Await all async operations
- [ ] **Timeout handling**: Set timeouts on async operations
- [ ] **Error propagation**: Handle errors in async context
- [ ] **Task cancellation**: Support cancellation tokens

**Example - Python asyncio**:
```python
import asyncio
from typing import Optional

async def fetch_with_timeout(url: str, timeout: float = 5.0) -> Optional[str]:
    try:
        async with asyncio.timeout(timeout):
            response = await http_client.get(url)
            return await response.text()
    except asyncio.TimeoutError:
        logger.warning(f"Request timeout: {url}")
        return None
    except Exception as e:
        logger.exception(f"Request failed: {url}")
        return None
```

### 2.6 Resource Management

#### Connection Pooling
- [ ] **Database pools**: Use connection pooling (min/max connections)
- [ ] **HTTP client pools**: Reuse HTTP connections
- [ ] **Pool sizing**: Size pools based on load (formula: `connections = ((core_count * 2) + effective_spindle_count)`)
- [ ] **Connection validation**: Validate connections before use (ping/test query)

**Example - PostgreSQL (Python)**:
```python
from psycopg2.pool import ThreadedConnectionPool

# Create connection pool
db_pool = ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    host="db.example.com",
    database="mydb",
    user="appuser",
    password=get_secret("db-password"),
    connect_timeout=5,
)

def execute_query(query: str, params: tuple):
    conn = None
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.commit()
        return result
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            db_pool.putconn(conn)
```

#### File Descriptor Management
- [ ] **Close resources**: Use context managers (with statements)
- [ ] **FD limits**: Monitor open file descriptors
- [ ] **Cleanup on error**: Ensure cleanup in finally blocks

**Example**:
```python
from contextlib import contextmanager

@contextmanager
def open_file_safely(path: str):
    f = None
    try:
        f = open(path, 'r')
        yield f
    finally:
        if f:
            f.close()

# Usage
with open_file_safely('/tmp/data.txt') as f:
    data = f.read()
```

#### Memory Management
- [ ] **Bounded collections**: Limit collection sizes (LRU caches)
- [ ] **Stream processing**: Process large datasets in chunks (generators, streams)
- [ ] **Explicit cleanup**: Call cleanup methods (close, dispose, free)

**Example - Streaming**:
```python
def process_large_file(path: str) -> int:
    """Process file line by line without loading entire file"""
    count = 0
    with open(path, 'r') as f:
        for line in f:  # Generator, doesn't load entire file
            process_line(line)
            count += 1
    return count
```

---

## 3. Security & Compliance

### 3.1 Authentication & Authorization

#### Authentication
- [ ] **Strong authentication**: Use OAuth2, OIDC, SAML (not basic auth)
- [ ] **Multi-factor authentication**: Support MFA (TOTP, WebAuthn)
- [ ] **Password policies**: Enforce strong passwords (length, complexity)
- [ ] **Password hashing**: Use Argon2, bcrypt, or scrypt (not MD5, SHA1)
- [ ] **Session management**: Secure session tokens (HttpOnly, Secure, SameSite)
- [ ] **Token expiration**: Short-lived access tokens (15-60 min), refresh tokens (days)

**Example - Password Hashing**:
```python
import argon2

ph = argon2.PasswordHasher(
    time_cost=2,        # Number of iterations
    memory_cost=65536,  # Memory usage in KiB
    parallelism=1,      # Number of threads
    hash_len=32,        # Hash length
    salt_len=16,        # Salt length
)

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(hash: str, password: str) -> bool:
    try:
        ph.verify(hash, password)

        # Check if rehashing is needed (parameters changed)
        if ph.check_needs_rehash(hash):
            return "REHASH_NEEDED"

        return True
    except argon2.exceptions.VerifyMismatchError:
        return False
```

#### Authorization
- [ ] **Role-based access control (RBAC)**: Define roles and permissions
- [ ] **Attribute-based access control (ABAC)**: Fine-grained access control
- [ ] **Principle of least privilege**: Grant minimum necessary permissions
- [ ] **Authorization checks**: Verify permissions on every request
- [ ] **Resource ownership**: Verify user owns resource before modification

**Example - RBAC**:
```python
from enum import Enum
from typing import Set

class Permission(Enum):
    READ_USER = "read:user"
    WRITE_USER = "write:user"
    DELETE_USER = "delete:user"
    READ_ADMIN = "read:admin"

class Role(Enum):
    USER = "user"
    ADMIN = "admin"

ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.USER: {Permission.READ_USER, Permission.WRITE_USER},
    Role.ADMIN: {Permission.READ_USER, Permission.WRITE_USER,
                 Permission.DELETE_USER, Permission.READ_ADMIN},
}

def check_permission(user_role: Role, required: Permission) -> bool:
    permissions = ROLE_PERMISSIONS.get(user_role, set())
    return required in permissions

# Usage in endpoint
def delete_user(request):
    if not check_permission(request.user.role, Permission.DELETE_USER):
        return ErrorResponse(
            type="forbidden",
            title="Forbidden",
            status=403,
            detail="Insufficient permissions",
            instance=request.path,
        )
    # Proceed with deletion
```

### 3.2 API Security

#### Rate Limiting
- [ ] **Request throttling**: Limit requests per IP/user/API key
- [ ] **Tiered limits**: Different limits per plan/role
- [ ] **Rate limit headers**: Return X-RateLimit-* headers
- [ ] **Burst protection**: Allow short bursts, enforce average rate

**Example - Token Bucket**:
```python
import time
from dataclasses import dataclass
from threading import Lock

@dataclass
class TokenBucket:
    capacity: int      # Maximum tokens
    rate: float        # Tokens per second
    tokens: float      # Current tokens
    last_refill: float # Last refill timestamp
    lock: Lock = Lock()

    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill

            # Refill tokens
            self.tokens = min(
                self.capacity,
                self.tokens + (elapsed * self.rate)
            )
            self.last_refill = now

            # Try to consume
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

# Usage
rate_limiter = TokenBucket(capacity=100, rate=10)  # 100 tokens, 10/sec

def handle_request(request):
    if not rate_limiter.consume():
        return ErrorResponse(
            type="rate-limit-exceeded",
            title="Too Many Requests",
            status=429,
            detail="Rate limit exceeded. Try again later.",
            instance=request.path,
        ), {"Retry-After": "60"}
```

#### CORS Configuration
- [ ] **Restricted origins**: Whitelist allowed origins (not `*`)
- [ ] **Credential support**: Set `Access-Control-Allow-Credentials` appropriately
- [ ] **Method restrictions**: Only allow necessary HTTP methods
- [ ] **Header restrictions**: Only allow necessary headers

**Example - Flask-CORS**:
```python
from flask_cors import CORS

app = Flask(__name__)

CORS(app, resources={
    r"/api/*": {
        "origins": ["https://app.example.com", "https://app.example.io"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["X-Request-ID"],
        "max_age": 3600,
        "supports_credentials": True,
    }
})
```

#### Content Security
- [ ] **Content-Type validation**: Verify Content-Type header
- [ ] **Request size limits**: Limit request body size (prevent DoS)
- [ ] **Upload validation**: Validate file types, scan for malware
- [ ] **CSRF protection**: Use CSRF tokens for state-changing operations

### 3.3 Data Protection

#### Encryption at Rest
- [ ] **Database encryption**: Enable encryption for databases
- [ ] **File encryption**: Encrypt sensitive files (AES-256)
- [ ] **Key management**: Use KMS for encryption keys
- [ ] **Backup encryption**: Encrypt backups

#### Encryption in Transit
- [ ] **TLS everywhere**: Use HTTPS for all endpoints
- [ ] **Service-to-service**: Use mTLS between services
- [ ] **Database connections**: Use TLS for database connections
- [ ] **Message queues**: Use TLS for message queue connections

#### Data Retention
- [ ] **Retention policies**: Define how long data is kept
- [ ] **Data deletion**: Implement hard deletion (not just soft)
- [ ] **Right to erasure**: Support GDPR data deletion requests
- [ ] **Audit logs**: Log data access and modifications

### 3.4 Compliance

#### GDPR Compliance
- [ ] **Data minimization**: Collect only necessary data
- [ ] **Consent management**: Obtain and track user consent
- [ ] **Data portability**: Export user data on request
- [ ] **Right to erasure**: Delete user data on request
- [ ] **Breach notification**: Notify users within 72 hours of breach

#### SOC 2 Compliance
- [ ] **Access controls**: Implement RBAC/ABAC
- [ ] **Audit logging**: Log all access and changes
- [ ] **Encryption**: Encrypt data at rest and in transit
- [ ] **Incident response**: Document incident response procedures

#### PCI DSS (if handling payment data)
- [ ] **Tokenization**: Never store full credit card numbers
- [ ] **PCI-compliant provider**: Use Stripe, Adyen, or Braintree
- [ ] **Secure transmission**: Use TLS 1.2+ for payment data
- [ ] **Access logging**: Log all access to payment data

---

## 4. Observability

### 4.1 Metrics

#### Application Metrics
- [ ] **Request metrics**: Count, latency, error rate (RED metrics)
- [ ] **Resource metrics**: CPU, memory, disk, network (USE metrics)
- [ ] **Business metrics**: Signups, conversions, revenue
- [ ] **Custom metrics**: Domain-specific metrics

**Example - Prometheus (Python)**:
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Request counter
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Request duration histogram
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Active connections gauge
active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

# Usage
@app.route('/api/users')
def get_users():
    active_connections.inc()

    with request_duration.labels(method='GET', endpoint='/api/users').time():
        try:
            users = fetch_users()
            request_count.labels(method='GET', endpoint='/api/users', status=200).inc()
            return jsonify(users), 200
        except Exception:
            request_count.labels(method='GET', endpoint='/api/users', status=500).inc()
            raise
        finally:
            active_connections.dec()

# Start metrics server
start_http_server(9090)
```

#### SLI/SLO Monitoring
- [ ] **Service Level Indicators (SLIs)**: Define measurable metrics
  - Availability: % of successful requests
  - Latency: % of requests below threshold (p95, p99)
  - Error rate: % of failed requests
- [ ] **Service Level Objectives (SLOs)**: Set targets (e.g., 99.9% availability)
- [ ] **Error budgets**: Track remaining error budget
- [ ] **Alerting**: Alert when SLO is at risk

**Example SLO**:
```yaml
slos:
  - name: api-availability
    description: API availability over 28 days
    target: 99.9  # 99.9% availability
    window: 28d
    sli:
      ratio:
        success: http_requests_total{status=~"2.."}
        total: http_requests_total

  - name: api-latency
    description: 95% of requests under 500ms
    target: 95  # 95% of requests
    window: 7d
    sli:
      latency:
        threshold: 0.5  # 500ms
        percentile: 95
```

### 4.2 Distributed Tracing

#### Trace Context Propagation
- [ ] **OpenTelemetry**: Use OpenTelemetry SDK
- [ ] **Trace IDs**: Generate and propagate trace IDs
- [ ] **Span creation**: Create spans for operations
- [ ] **Span attributes**: Add context to spans (user_id, method, status)

**Example - OpenTelemetry (Python)**:
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Setup tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure exporter
otlp_exporter = OTLPSpanExporter(endpoint="http://collector:4317")
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Create spans
def fetch_user(user_id: str):
    with tracer.start_as_current_span("fetch_user") as span:
        span.set_attribute("user.id", user_id)
        span.set_attribute("db.system", "postgresql")

        try:
            user = db.get_user(user_id)
            span.set_attribute("user.found", user is not None)
            return user
        except Exception as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            span.record_exception(e)
            raise
```

#### Trace Sampling
- [ ] **Head-based sampling**: Sample at trace start (1%, 10%, 100%)
- [ ] **Tail-based sampling**: Sample based on trace outcome (errors, slow requests)
- [ ] **Adaptive sampling**: Adjust sample rate based on volume

### 4.3 Alerting

#### Alert Configuration
- [ ] **Error rate alerts**: Alert on elevated error rates
- [ ] **Latency alerts**: Alert on slow requests
- [ ] **Resource alerts**: Alert on high CPU/memory/disk
- [ ] **Availability alerts**: Alert on service downtime
- [ ] **Runbook links**: Include runbook links in alerts

**Example - Prometheus Alerting**:
```yaml
groups:
  - name: api-alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status=~"5.."}[5m]) /
          rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
          runbook: "https://wiki.example.com/runbooks/high-error-rate"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High request latency detected"
          description: "P95 latency is {{ $value }}s (threshold: 1s)"
          runbook: "https://wiki.example.com/runbooks/high-latency"

      - alert: ServiceDown
        expr: up{job="myapp"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.instance }} is unreachable"
          runbook: "https://wiki.example.com/runbooks/service-down"
```

#### Alert Routing
- [ ] **Severity-based routing**: Route by severity (critical, warning, info)
- [ ] **On-call rotation**: Integrate with PagerDuty, Opsgenie
- [ ] **Alert grouping**: Group related alerts
- [ ] **Alert silencing**: Silence alerts during maintenance

### 4.4 Audit Logging

#### Audit Trail
- [ ] **Security events**: Log authentication, authorization, access
- [ ] **Data changes**: Log creates, updates, deletes
- [ ] **Admin actions**: Log all admin operations
- [ ] **API calls**: Log external API calls
- [ ] **Immutable logs**: Store logs in append-only storage

**Example - Audit Log Schema**:
```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class AuditAction(Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACCESS = "access"

@dataclass
class AuditLog:
    timestamp: datetime
    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: str
    ip_address: str
    user_agent: str
    outcome: str  # "success" or "failure"
    details: dict  # Additional context

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "outcome": self.outcome,
            "details": self.details,
        }

# Usage
audit_log = AuditLog(
    timestamp=datetime.utcnow(),
    user_id="user-123",
    action=AuditAction.DELETE,
    resource_type="user",
    resource_id="user-456",
    ip_address=request.remote_addr,
    user_agent=request.headers.get("User-Agent"),
    outcome="success",
    details={"reason": "account_closure"},
)

# Send to audit log service
audit_service.log(audit_log.to_dict())
```

---

## 5. Documentation

### 5.1 API Documentation

#### OpenAPI/Swagger
- [ ] **OpenAPI spec**: Generate OpenAPI 3.0 specification
- [ ] **Interactive docs**: Provide Swagger UI or ReDoc
- [ ] **Examples**: Include request/response examples
- [ ] **Error codes**: Document all error codes and meanings
- [ ] **Authentication**: Document authentication methods

**Example - FastAPI**:
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="User API",
    description="API for managing users",
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
)

class UserResponse(BaseModel):
    id: str = Field(..., example="user-123")
    email: str = Field(..., example="user@example.com")
    name: str = Field(..., example="John Doe")

    class Config:
        schema_extra = {
            "example": {
                "id": "user-123",
                "email": "user@example.com",
                "name": "John Doe",
            }
        }

@app.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Retrieve a user by their unique identifier",
    responses={
        200: {"description": "User found"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
def get_user(user_id: str):
    """
    Get a user by ID.

    - **user_id**: Unique user identifier
    """
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### 5.2 Operational Documentation

#### Runbooks
- [ ] **Deployment procedures**: Step-by-step deployment guide
- [ ] **Incident response**: How to respond to common incidents
- [ ] **Rollback procedures**: How to roll back releases
- [ ] **Troubleshooting guides**: Common issues and solutions
- [ ] **Escalation paths**: Who to contact for what issues

**Example Runbook Structure**:
```markdown
# Runbook: High Error Rate

## Symptoms
- Error rate > 5% for 5+ minutes
- Alert: `HighErrorRate` firing
- Users reporting "500 Internal Server Error"

## Diagnosis

### 1. Check Recent Deployments
```bash
kubectl rollout history deployment/myapp
```

### 2. Check Application Logs
```bash
kubectl logs -l app=myapp --tail=100 | grep ERROR
```

### 3. Check Dependencies
- Database: Check connection pool, query performance
- External APIs: Check status pages, timeouts
- Cache: Check Redis/Memcached health

## Resolution

### If Caused by Recent Deployment
```bash
kubectl rollout undo deployment/myapp
```

### If Database Connection Pool Exhausted
```bash
kubectl scale deployment/myapp --replicas=10
kubectl exec -it deployment/myapp -- python -c "
from app import db_pool
print(f'Active: {db_pool.active}, Idle: {db_pool.idle}')
"
```

## Prevention
- [ ] Add database query timeout (5s)
- [ ] Increase connection pool size
- [ ] Add circuit breaker for external APIs
- [ ] Improve error handling in [specific module]

## Escalation
- Primary: @backend-team
- Secondary: @platform-team
- Incident Channel: #incidents
```

#### Architecture Documentation
- [ ] **System architecture**: Diagram of components and interactions
- [ ] **Data flow diagrams**: How data moves through system
- [ ] **Infrastructure diagram**: Cloud resources, networking
- [ ] **Dependency map**: External dependencies and SLAs

### 5.3 Code Documentation

#### Inline Documentation
- [ ] **Function docstrings**: Document purpose, params, returns, raises
- [ ] **Class docstrings**: Document purpose, attributes, usage
- [ ] **Module docstrings**: Document module purpose and exports
- [ ] **Complex logic**: Comment non-obvious code

**Example - Google Style Docstrings**:
```python
def fetch_users(
    user_ids: List[str],
    include_inactive: bool = False,
    timeout: float = 5.0,
) -> Dict[str, User]:
    """Fetch multiple users by ID.

    Retrieves users from the database in a single query. Users not found
    are omitted from the result. Inactive users are excluded by default.

    Args:
        user_ids: List of user IDs to fetch. Must be non-empty.
        include_inactive: Whether to include inactive users. Defaults to False.
        timeout: Query timeout in seconds. Defaults to 5.0.

    Returns:
        Dictionary mapping user ID to User object. Only found users are included.

    Raises:
        ValueError: If user_ids is empty.
        DatabaseError: If database query fails.
        TimeoutError: If query exceeds timeout.

    Example:
        >>> users = fetch_users(["user-1", "user-2"])
        >>> print(users["user-1"].email)
        user1@example.com
    """
    if not user_ids:
        raise ValueError("user_ids cannot be empty")

    query = "SELECT * FROM users WHERE id IN %s"
    if not include_inactive:
        query += " AND active = TRUE"

    try:
        results = db.execute(query, (tuple(user_ids),), timeout=timeout)
        return {row["id"]: User.from_row(row) for row in results}
    except DBTimeout:
        raise TimeoutError(f"Query exceeded {timeout}s timeout")
```

---

## 6. Testing

### 6.1 Test Coverage

#### Coverage Targets
- [ ] **Critical path**: 90%+ coverage (authentication, payments, data loss scenarios)
- [ ] **Business logic**: 80%+ coverage (core features)
- [ ] **UI layer**: 60%+ coverage (components, pages)
- [ ] **Overall**: 70%+ coverage
- [ ] **Coverage reporting**: Generate coverage reports in CI
- [ ] **Coverage gates**: Block merges if coverage drops

**Example - pytest-cov**:
```bash
# Run tests with coverage
pytest --cov=app --cov-report=html --cov-report=term --cov-fail-under=70

# Coverage config (.coveragerc)
[run]
source = app
omit =
    */tests/*
    */migrations/*
    */venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

### 6.2 Test Types

#### Unit Tests
- [ ] **Function-level tests**: Test individual functions
- [ ] **Mock dependencies**: Mock external dependencies (DB, APIs)
- [ ] **Edge cases**: Test boundary conditions, empty inputs, invalid inputs
- [ ] **Fast execution**: Unit tests should run in milliseconds

**Example**:
```python
import pytest
from unittest.mock import Mock, patch
from app.users import fetch_user

def test_fetch_user_success():
    """Test successful user fetch"""
    mock_db = Mock()
    mock_db.get_user.return_value = {"id": "user-1", "email": "test@example.com"}

    with patch("app.users.db", mock_db):
        user = fetch_user("user-1")

    assert user["id"] == "user-1"
    assert user["email"] == "test@example.com"
    mock_db.get_user.assert_called_once_with("user-1")

def test_fetch_user_not_found():
    """Test user not found"""
    mock_db = Mock()
    mock_db.get_user.return_value = None

    with patch("app.users.db", mock_db):
        user = fetch_user("nonexistent")

    assert user is None

def test_fetch_user_invalid_id():
    """Test invalid user ID"""
    with pytest.raises(ValueError, match="Invalid user ID"):
        fetch_user("")

@pytest.mark.parametrize("user_id,expected", [
    ("user-1", True),
    ("user-2", True),
    ("", False),
    (None, False),
])
def test_fetch_user_parametrized(user_id, expected):
    """Test various user IDs"""
    # ... test implementation
```

#### Integration Tests
- [ ] **Module integration**: Test interactions between modules
- [ ] **Database integration**: Test database queries (use test DB)
- [ ] **API integration**: Test API endpoints (use test server)
- [ ] **External service stubs**: Stub external APIs (WireMock, Mockoon)

**Example - FastAPI Integration Test**:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_user():
    """Test user creation endpoint"""
    response = client.post(
        "/users",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "age": 25,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

    # Verify user was created in DB
    user = db.get_user(data["id"])
    assert user is not None

def test_create_user_invalid_email():
    """Test user creation with invalid email"""
    response = client.post(
        "/users",
        json={"email": "invalid-email", "username": "testuser"},
    )

    assert response.status_code == 400
    assert "email" in response.json()["detail"]
```

#### End-to-End Tests
- [ ] **User workflows**: Test complete user journeys
- [ ] **Real dependencies**: Use staging environment
- [ ] **UI automation**: Use Selenium, Playwright, Cypress
- [ ] **Data cleanup**: Clean up test data after runs

**Example - Playwright**:
```typescript
import { test, expect } from '@playwright/test';

test('user registration flow', async ({ page }) => {
  // Navigate to registration page
  await page.goto('https://staging.example.com/register');

  // Fill registration form
  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'SecurePass123!');
  await page.fill('input[name="username"]', 'testuser');

  // Submit form
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard
  await page.waitForURL('https://staging.example.com/dashboard');

  // Verify welcome message
  await expect(page.locator('h1')).toContainText('Welcome, testuser!');

  // Verify API call was made
  const response = await page.waitForResponse(
    resp => resp.url().includes('/api/users') && resp.status() === 201
  );
  expect(response.ok()).toBeTruthy();
});
```

#### Performance Tests
- [ ] **Load testing**: Test with expected load (JMeter, Locust, k6)
- [ ] **Stress testing**: Test beyond expected load
- [ ] **Spike testing**: Test sudden traffic spikes
- [ ] **Soak testing**: Test sustained load over time

**Example - k6**:
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 50 },   // Ramp-up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '1m', target: 100 },  // Ramp-up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '1m', target: 0 },    // Ramp-down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests under 500ms
    http_req_failed: ['rate<0.01'],    // Error rate < 1%
  },
};

export default function () {
  const response = http.get('https://api.example.com/users');

  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  sleep(1);
}
```

### 6.3 Test Automation

#### CI/CD Integration
- [ ] **Automated test runs**: Run tests on every commit/PR
- [ ] **Parallel execution**: Run tests in parallel
- [ ] **Test result reporting**: Report results in GitHub/GitLab
- [ ] **Flaky test detection**: Track and fix flaky tests

**Example - GitHub Actions**:
```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-xdist

      - name: Run tests
        run: |
          pytest -v -n auto --cov=app --cov-report=xml --cov-fail-under=70

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
```

---

## 7. Operational Readiness

### 7.1 Performance

#### Response Time
- [ ] **Latency targets**: Define targets (p50, p95, p99)
- [ ] **Database query optimization**: Index commonly queried fields
- [ ] **Caching**: Cache frequently accessed data (Redis, Memcached)
- [ ] **CDN**: Use CDN for static assets
- [ ] **Compression**: Enable gzip/brotli compression

#### Timeouts
- [ ] **Request timeouts**: Set timeouts on all external requests
- [ ] **Database timeouts**: Set query timeouts (5-30s)
- [ ] **Circuit breakers**: Fail fast when dependencies are down
- [ ] **Retry with backoff**: Retry transient failures with exponential backoff

**Example - Circuit Breaker**:
```python
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

def call_external_api():
    return circuit_breaker.call(
        requests.get,
        "https://api.example.com/data",
        timeout=5,
    )
```

#### Rate Limiting
- [ ] **Client rate limits**: Limit requests per client
- [ ] **Endpoint rate limits**: Different limits per endpoint
- [ ] **Backpressure**: Apply backpressure when overloaded
- [ ] **Queue management**: Use queues to handle bursts

### 7.2 Scalability

#### Horizontal Scaling
- [ ] **Stateless design**: Design services to be stateless
- [ ] **Auto-scaling**: Configure auto-scaling rules (CPU, memory, request count)
- [ ] **Load balancing**: Distribute traffic across instances
- [ ] **Session affinity**: Use session affinity if needed (sticky sessions)

**Example - Kubernetes HPA**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 30
```

#### Database Scaling
- [ ] **Read replicas**: Use read replicas for read-heavy workloads
- [ ] **Connection pooling**: Pool database connections
- [ ] **Query optimization**: Optimize slow queries
- [ ] **Caching layer**: Cache query results (Redis)
- [ ] **Database sharding**: Shard by tenant, geography, or key range

### 7.3 Disaster Recovery

#### Backup Strategy
- [ ] **Automated backups**: Schedule regular backups (daily, hourly)
- [ ] **Backup retention**: Define retention policy (7 daily, 4 weekly, 12 monthly)
- [ ] **Backup testing**: Regularly test restore procedures
- [ ] **Off-site backups**: Store backups in different region/cloud
- [ ] **Point-in-time recovery**: Enable PITR for databases

**Example - PostgreSQL Backup**:
```bash
#!/bin/bash
# Automated PostgreSQL backup script

BACKUP_DIR="/backups/postgres"
RETENTION_DAYS=7
DB_NAME="mydb"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup
pg_dump -h localhost -U postgres -d $DB_NAME \
  | gzip > "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

# Upload to S3
aws s3 cp "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz" \
  "s3://backups/postgres/${DB_NAME}_${TIMESTAMP}.sql.gz" \
  --storage-class STANDARD_IA

# Delete old backups
find $BACKUP_DIR -type f -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Verify backup
if [ $? -eq 0 ]; then
  echo "Backup successful: ${DB_NAME}_${TIMESTAMP}.sql.gz"
else
  echo "Backup failed!" >&2
  exit 1
fi
```

#### Recovery Plan
- [ ] **RTO/RPO targets**: Define Recovery Time Objective and Recovery Point Objective
- [ ] **Disaster recovery runbook**: Document recovery procedures
- [ ] **Failover testing**: Test failover procedures quarterly
- [ ] **Multi-region deployment**: Deploy to multiple regions for HA

### 7.4 Incident Management

#### Incident Response
- [ ] **On-call rotation**: Establish on-call rotation (PagerDuty, Opsgenie)
- [ ] **Incident severity levels**: Define severity levels (P0-P4)
- [ ] **Escalation policy**: Define escalation paths
- [ ] **Post-mortem process**: Conduct blameless post-mortems
- [ ] **Incident communication**: Use incident channels (#incidents)

**Example - Incident Severity Levels**:
```markdown
## P0 - Critical
- **Impact**: Complete service outage or data loss
- **Response Time**: Immediate
- **Escalation**: Page on-call immediately
- **Examples**: Database down, authentication broken, data breach

## P1 - High
- **Impact**: Major feature unavailable, significant user impact
- **Response Time**: 15 minutes
- **Escalation**: Page on-call if no response in 15 min
- **Examples**: Payment processing down, search broken, high error rate

## P2 - Medium
- **Impact**: Minor feature unavailable, limited user impact
- **Response Time**: 1 hour
- **Escalation**: Notify on-call via Slack
- **Examples**: Email notifications delayed, minor UI bug

## P3 - Low
- **Impact**: Cosmetic issue, no user impact
- **Response Time**: Next business day
- **Escalation**: Create ticket
- **Examples**: Typo in UI, minor style issue

## P4 - Info
- **Impact**: No impact, informational
- **Response Time**: As needed
- **Examples**: Monitoring alert tuning needed
```

---

## Final Checklist

Before deploying to production, verify ALL of the following:

### Infrastructure
- [ ] Container uses minimal base image (distroless, alpine, scratch)
- [ ] Container runs as non-root user (uid > 1000)
- [ ] Resource limits set (CPU, memory, storage)
- [ ] Network policies configured (least privilege)
- [ ] Secrets externalized to secrets manager
- [ ] TLS 1.2+ configured with strong ciphers
- [ ] Valid certificates from trusted CA
- [ ] Zero-downtime deployment configured (rolling/blue-green)
- [ ] Health checks defined (readiness, liveness)
- [ ] Graceful shutdown implemented (SIGTERM handling)
- [ ] Multi-zone deployment (3+ replicas)
- [ ] Auto-scaling configured

### Application
- [ ] No hardcoded secrets or credentials
- [ ] All inputs validated (schema, types, bounds)
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding, CSP)
- [ ] Error handling with proper context
- [ ] Structured logging (JSON format)
- [ ] PII/secrets redacted from logs
- [ ] Type hints on all functions (Python/TypeScript)
- [ ] Thread-safe code (proper locking)
- [ ] Connection pooling configured
- [ ] Timeouts on all external requests
- [ ] Circuit breakers for external dependencies
- [ ] Retry logic with exponential backoff

### Security
- [ ] Authentication implemented (OAuth2/OIDC)
- [ ] Authorization checks on all endpoints (RBAC/ABAC)
- [ ] Rate limiting configured
- [ ] CORS properly configured (no wildcard origins)
- [ ] CSRF protection enabled
- [ ] Encryption at rest (database, files)
- [ ] Encryption in transit (TLS everywhere)
- [ ] Data retention policies defined
- [ ] Audit logging enabled
- [ ] Vulnerability scanning in CI/CD

### Observability
- [ ] Metrics collection configured (Prometheus)
- [ ] SLIs/SLOs defined and tracked
- [ ] Distributed tracing enabled (OpenTelemetry)
- [ ] Alerts configured (error rate, latency, availability)
- [ ] Runbooks linked in alerts
- [ ] Log aggregation configured (ELK, Datadog)
- [ ] Dashboards created for key metrics

### Documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Runbooks for common incidents
- [ ] Architecture diagrams
- [ ] Deployment procedures documented
- [ ] Rollback procedures documented
- [ ] Function docstrings complete

### Testing
- [ ] Unit tests with 80%+ coverage
- [ ] Integration tests for module boundaries
- [ ] E2E tests for critical workflows
- [ ] Performance tests run (load, stress)
- [ ] Tests run in CI on every commit
- [ ] Coverage gates enforced

### Operations
- [ ] Automated backups configured
- [ ] Backup restore tested
- [ ] RTO/RPO targets defined
- [ ] Disaster recovery plan documented
- [ ] On-call rotation established
- [ ] Incident severity levels defined
- [ ] Post-mortem process established

---

## Appendix: Production Readiness Score

Calculate your production readiness score:

| Category | Total Items | Checked | Score |
|----------|-------------|---------|-------|
| Infrastructure | 30 | ___ | ___% |
| Application | 35 | ___ | ___% |
| Security | 25 | ___ | ___% |
| Observability | 20 | ___ | ___% |
| Documentation | 15 | ___ | ___% |
| Testing | 15 | ___ | ___% |
| Operations | 20 | ___ | ___% |
| **Overall** | **160** | **___** | **___%** |

**Score Interpretation**:
- **90-100%**: Production ready
- **80-89%**: Production ready with minor gaps
- **70-79%**: Address gaps before production
- **<70%**: Not production ready

---

**Document Version**: 1.0
**Last Updated**: 2025-10-29
**Maintained By**: Platform Engineering Team
