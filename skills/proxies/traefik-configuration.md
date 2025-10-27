---
name: proxies-traefik-configuration
description: Traefik configuration including dynamic service discovery, middleware chains, automatic Let's Encrypt, Docker/Kubernetes integration, and cloud-native routing
---

# Traefik Configuration

**Scope**: Traefik setup, dynamic configuration, middleware, Let's Encrypt, service discovery
**Lines**: ~380
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Setting up cloud-native reverse proxy
- Implementing automatic service discovery
- Configuring automatic SSL/TLS with Let's Encrypt
- Working with Docker or Kubernetes
- Building microservices architectures
- Implementing middleware chains
- Setting up canary deployments
- Configuring dynamic routing rules

## Core Concepts

### Traefik Architecture

```
Internet → EntryPoint → Router → Middleware → Service → Backend
           (Port)       (Rules)  (Transform)  (Load Balance)
```

**Key Components**:
- **EntryPoints**: Listen ports (HTTP/HTTPS/TCP/UDP)
- **Routers**: Match requests and route to services
- **Middleware**: Transform requests/responses
- **Services**: Define backend pools and load balancing
- **Providers**: Dynamic configuration sources (Docker, Kubernetes, File)

### Static vs Dynamic Configuration

**Static Configuration** (traefik.yml):
```yaml
# Core Traefik settings
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
```

**Dynamic Configuration**:
- Docker labels
- Kubernetes ingress
- File configuration
- Consul/etcd

---

## Patterns

### Pattern 1: Docker Provider with Labels

**Use Case**: Automatic service discovery with Docker

```yaml
# docker-compose.yml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./letsencrypt:/letsencrypt

  app:
    image: myapp:latest
    labels:
      # Enable Traefik
      - "traefik.enable=true"

      # HTTP router
      - "traefik.http.routers.app.rule=Host(`example.com`)"
      - "traefik.http.routers.app.entrypoints=web"
      - "traefik.http.routers.app.middlewares=redirect-to-https"

      # HTTPS router
      - "traefik.http.routers.app-secure.rule=Host(`example.com`)"
      - "traefik.http.routers.app-secure.entrypoints=websecure"
      - "traefik.http.routers.app-secure.tls=true"
      - "traefik.http.routers.app-secure.tls.certresolver=letsencrypt"

      # Middleware: HTTP to HTTPS redirect
      - "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https"

      # Service configuration
      - "traefik.http.services.app.loadbalancer.server.port=8080"
```

**Benefits**:
- Automatic service discovery
- No manual configuration updates
- Automatic Let's Encrypt SSL
- Zero-downtime deployments

### Pattern 2: Middleware Chains

**Use Case**: Apply multiple transformations to requests

```yaml
services:
  api:
    image: api:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.example.com`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls=true"

      # Middleware chain
      - "traefik.http.routers.api.middlewares=api-chain"
      - "traefik.http.middlewares.api-chain.chain.middlewares=rate-limit,auth,security-headers,compression"

      # Rate limiting
      - "traefik.http.middlewares.rate-limit.ratelimit.average=100"
      - "traefik.http.middlewares.rate-limit.ratelimit.burst=50"

      # Basic auth
      - "traefik.http.middlewares.auth.basicauth.users=user:$$apr1$$..."

      # Security headers
      - "traefik.http.middlewares.security-headers.headers.customresponseheaders.X-Content-Type-Options=nosniff"
      - "traefik.http.middlewares.security-headers.headers.customresponseheaders.X-Frame-Options=SAMEORIGIN"
      - "traefik.http.middlewares.security-headers.headers.stsSeconds=31536000"

      # Compression
      - "traefik.http.middlewares.compression.compress=true"

      - "traefik.http.services.api.loadbalancer.server.port=8080"
```

### Pattern 3: Path-Based Routing with Path Stripping

**Use Case**: Route different paths to different services

```yaml
services:
  web:
    image: web:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.web.rule=Host(`example.com`)"
      - "traefik.http.routers.web.entrypoints=websecure"
      - "traefik.http.routers.web.tls=true"
      - "traefik.http.services.web.loadbalancer.server.port=3000"

  api:
    image: api:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`example.com`) && PathPrefix(`/api`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls=true"
      - "traefik.http.routers.api.middlewares=api-strip-prefix"
      - "traefik.http.middlewares.api-strip-prefix.stripprefix.prefixes=/api"
      - "traefik.http.services.api.loadbalancer.server.port=8080"

  admin:
    image: admin:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.admin.rule=Host(`example.com`) && PathPrefix(`/admin`)"
      - "traefik.http.routers.admin.entrypoints=websecure"
      - "traefik.http.routers.admin.tls=true"
      - "traefik.http.routers.admin.middlewares=admin-auth"
      - "traefik.http.middlewares.admin-auth.basicauth.users=admin:$$apr1$$..."
      - "traefik.http.services.admin.loadbalancer.server.port=4000"
```

---

## Complete Static Configuration

### traefik.yml (File-Based Configuration)

```yaml
# Global configuration
global:
  checkNewVersion: true
  sendAnonymousUsage: false

# API and dashboard
api:
  dashboard: true
  insecure: false  # Use middleware for auth in production

# Entry points
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https

  websecure:
    address: ":443"
    http:
      tls:
        certResolver: letsencrypt

  metrics:
    address: ":8082"

# Providers
providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: traefik-public
    watch: true

  file:
    directory: /etc/traefik/dynamic
    watch: true

# Certificate resolvers
certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web

# Logging
log:
  level: INFO
  format: json
  filePath: /var/log/traefik/traefik.log

accessLog:
  filePath: /var/log/traefik/access.log
  format: json
  fields:
    defaultMode: keep
    headers:
      defaultMode: keep

# Metrics
metrics:
  prometheus:
    entryPoint: metrics
    addEntryPointsLabels: true
    addServicesLabels: true
```

---

## Dynamic Configuration Examples

### Load Balancing Strategies

```yaml
# dynamic/services.yml
http:
  services:
    # Round-robin (default)
    app-service:
      loadBalancer:
        servers:
          - url: "http://app1:8080"
          - url: "http://app2:8080"
          - url: "http://app3:8080"
        healthCheck:
          path: /health
          interval: 10s
          timeout: 3s

    # Weighted round-robin
    app-weighted:
      loadBalancer:
        servers:
          - url: "http://app1:8080"
          - url: "http://app2:8080"
          - url: "http://app3:8080"
        weighted:
          services:
            - name: app1
              weight: 3
            - name: app2
              weight: 2
            - name: app3
              weight: 1

    # Sticky sessions
    app-sticky:
      loadBalancer:
        servers:
          - url: "http://app1:8080"
          - url: "http://app2:8080"
        sticky:
          cookie:
            name: server_id
            secure: true
            httpOnly: true
```

### Advanced Middleware

```yaml
# dynamic/middleware.yml
http:
  middlewares:
    # Rate limiting
    api-rate-limit:
      rateLimit:
        average: 100
        period: 1s
        burst: 50

    # IP whitelist
    ip-whitelist:
      ipWhiteList:
        sourceRange:
          - "10.0.0.0/8"
          - "172.16.0.0/12"
          - "192.168.0.0/16"

    # Circuit breaker
    circuit-breaker:
      circuitBreaker:
        expression: "NetworkErrorRatio() > 0.30 || ResponseCodeRatio(500, 600, 0, 600) > 0.25"

    # Retry
    retry-policy:
      retry:
        attempts: 3
        initialInterval: 100ms

    # Request buffering
    buffer-requests:
      buffering:
        maxRequestBodyBytes: 2000000
        memRequestBodyBytes: 2000000
        maxResponseBodyBytes: 2000000
        memResponseBodyBytes: 2000000

    # CORS
    cors-policy:
      headers:
        accessControlAllowMethods:
          - GET
          - POST
          - PUT
          - DELETE
        accessControlAllowOriginList:
          - "https://example.com"
        accessControlAllowHeaders:
          - "Content-Type"
          - "Authorization"
        accessControlMaxAge: 100
        addVaryHeader: true

    # Security headers
    security-headers:
      headers:
        customResponseHeaders:
          X-Content-Type-Options: "nosniff"
          X-Frame-Options: "SAMEORIGIN"
          X-XSS-Protection: "1; mode=block"
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        stsPreload: true
        contentSecurityPolicy: "default-src 'self'"
```

---

## Kubernetes Integration

### Ingress Resource

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
    traefik.ingress.kubernetes.io/router.tls.certresolver: letsencrypt
    traefik.ingress.kubernetes.io/router.middlewares: default-rate-limit@kubernetescrd
spec:
  rules:
    - host: example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-service
                port:
                  number: 80
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 8080
```

### Custom Resource Definitions (CRDs)

```yaml
# IngressRoute
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: app-ingressroute
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`example.com`) && PathPrefix(`/api`)
      kind: Rule
      services:
        - name: api-service
          port: 8080
      middlewares:
        - name: rate-limit
        - name: security-headers
  tls:
    certResolver: letsencrypt

---
# Middleware CRD
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: rate-limit
spec:
  rateLimit:
    average: 100
    burst: 50

---
# TLSOption CRD
apiVersion: traefik.containo.us/v1alpha1
kind: TLSOption
metadata:
  name: modern-tls
spec:
  minVersion: VersionTLS12
  cipherSuites:
    - TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
    - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
```

---

## Advanced Patterns

### Canary Deployments

```yaml
services:
  app-v1:
    image: app:v1
    deploy:
      replicas: 3
    labels:
      - "traefik.enable=true"
      - "traefik.http.services.app-v1.loadbalancer.server.port=8080"
      - "traefik.http.services.app-v1.loadbalancer.weighted.services.app-v1.weight=90"

  app-v2:
    image: app:v2
    deploy:
      replicas: 1
    labels:
      - "traefik.enable=true"
      - "traefik.http.services.app-v2.loadbalancer.server.port=8080"
      - "traefik.http.services.app-v2.loadbalancer.weighted.services.app-v2.weight=10"

  router:
    image: traefik:v2.10
    labels:
      - "traefik.http.routers.app.rule=Host(`example.com`)"
      - "traefik.http.routers.app.service=app-weighted"
      - "traefik.http.services.app-weighted.weighted.services.app-v1.weight=90"
      - "traefik.http.services.app-weighted.weighted.services.app-v2.weight=10"
```

### TCP/UDP Routing

```yaml
# traefik.yml
entryPoints:
  postgres:
    address: ":5432"
  mysql:
    address: ":3306"

# dynamic/tcp.yml
tcp:
  routers:
    postgres-router:
      entryPoints:
        - postgres
      rule: "HostSNI(`*`)"
      service: postgres-service

  services:
    postgres-service:
      loadBalancer:
        servers:
          - address: "postgres1:5432"
          - address: "postgres2:5432"
```

---

## Best Practices

### 1. Use Health Checks

```yaml
labels:
  - "traefik.http.services.app.loadbalancer.healthcheck.path=/health"
  - "traefik.http.services.app.loadbalancer.healthcheck.interval=10s"
  - "traefik.http.services.app.loadbalancer.healthcheck.timeout=3s"
  - "traefik.http.services.app.loadbalancer.healthcheck.scheme=http"
```

### 2. Secure Dashboard Access

```yaml
# Dashboard with middleware auth
labels:
  - "traefik.http.routers.dashboard.rule=Host(`traefik.example.com`)"
  - "traefik.http.routers.dashboard.service=api@internal"
  - "traefik.http.routers.dashboard.middlewares=dashboard-auth"
  - "traefik.http.middlewares.dashboard-auth.basicauth.users=admin:$$apr1$$..."
```

### 3. Use Separate Networks

```yaml
services:
  traefik:
    networks:
      - traefik-public

  app:
    networks:
      - traefik-public
      - internal

networks:
  traefik-public:
    external: true
  internal:
    internal: true
```

---

## Troubleshooting

### Issue 1: Services Not Discovered

**Debug Steps**:
```bash
# Check Traefik logs
docker logs traefik

# Verify provider configuration
docker exec traefik cat /etc/traefik/traefik.yml

# Check service labels
docker inspect app | grep traefik
```

**Common Solutions**:
- Ensure `traefik.enable=true` label
- Check `exposedByDefault` setting
- Verify network connectivity
- Ensure correct provider configuration

### Issue 2: Let's Encrypt Rate Limits

**Solutions**:
```yaml
# Use staging environment for testing
certificatesResolvers:
  letsencrypt:
    acme:
      caServer: https://acme-staging-v02.api.letsencrypt.org/directory
      email: admin@example.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web
```

---

## Related Skills

- `proxies-reverse-proxy` - Reverse proxy patterns
- `proxies-nginx-configuration` - Nginx configuration
- `containers-docker-compose` - Docker Compose orchestration
- `containers-kubernetes` - Kubernetes deployment
- `cryptography-tls-ssl` - SSL/TLS configuration

---

**Last Updated**: 2025-10-27
