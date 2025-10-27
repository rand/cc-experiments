---
name: proxies-reverse-proxy
description: Reverse proxy patterns including load balancing, SSL termination, request routing, health checks, and high availability configurations
---

# Reverse Proxy

**Scope**: Reverse proxy concepts, load balancing, SSL termination, routing patterns
**Lines**: ~380
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Implementing load balancing across backend servers
- Setting up SSL/TLS termination
- Building API gateways
- Configuring request routing and rewriting
- Implementing caching layers
- Setting up health checks and failover
- Protecting backend services
- Adding rate limiting and security headers

## Core Concepts

### Reverse Proxy Architecture

```
Internet → Reverse Proxy → Backend Pool
                         → [ Server 1 ]
                         → [ Server 2 ]
                         → [ Server 3 ]
```

**Benefits**:
- **Load Balancing**: Distribute traffic across servers
- **SSL Termination**: Handle TLS at proxy, plain HTTP to backends
- **Caching**: Cache responses, reduce backend load
- **Security**: Hide backend topology, add security headers
- **Compression**: Compress responses before sending to clients
- **URL Rewriting**: Transform requests before forwarding

### Load Balancing Algorithms

**Round Robin**:
```
Request 1 → Server 1
Request 2 → Server 2
Request 3 → Server 3
Request 4 → Server 1 (cycle repeats)
```

**Least Connections**:
```
Server 1: 5 connections  ← Request goes here
Server 2: 10 connections
Server 3: 8 connections
```

**IP Hash**:
```
Client IP → Hash → Consistent server assignment
Same client → Always same server (session affinity)
```

**Weighted Round Robin**:
```
Server 1 (weight: 3) → 3x more traffic
Server 2 (weight: 1) → 1x traffic
Server 3 (weight: 2) → 2x traffic
```

---

## Patterns

### Pattern 1: SSL Termination

**Use Case**: Handle TLS at proxy, plain HTTP to backends

```nginx
# ✅ Good: SSL termination at proxy
upstream backend {
    server backend1.internal:8080;
    server backend2.internal:8080;
    server backend3.internal:8080;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/ssl/certs/api.example.com.crt;
    ssl_certificate_key /etc/ssl/private/api.example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Benefits**:
- Centralized certificate management
- Reduced CPU load on backends
- Easier certificate rotation
- Backend servers can be simpler

### Pattern 2: Health Checks and Failover

**Use Case**: Automatic detection of unhealthy backends

```nginx
upstream backend {
    server backend1.internal:8080 max_fails=3 fail_timeout=30s;
    server backend2.internal:8080 max_fails=3 fail_timeout=30s;
    server backend3.internal:8080 backup;  # Only used if others fail

    keepalive 32;
}

server {
    listen 80;

    location / {
        proxy_pass http://backend;
        proxy_next_upstream error timeout http_500 http_502 http_503;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }
}
```

**Benefits**:
- Automatic failover
- No manual intervention
- Improved availability
- Graceful degradation

### Pattern 3: Path-Based Routing

**Use Case**: Route requests to different backends by path

```nginx
upstream api_backend {
    server api1.internal:8080;
    server api2.internal:8080;
}

upstream web_backend {
    server web1.internal:3000;
    server web2.internal:3000;
}

upstream admin_backend {
    server admin.internal:4000;
}

server {
    listen 80;
    server_name example.com;

    location /api/ {
        proxy_pass http://api_backend/;
        proxy_set_header Host $host;
    }

    location /admin/ {
        proxy_pass http://admin_backend/;
        # Add authentication
        auth_basic "Admin Area";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }

    location / {
        proxy_pass http://web_backend;
        proxy_set_header Host $host;
    }
}
```

---

## Implementation Examples

### Python Reverse Proxy (with aiohttp)

```python
import asyncio
from aiohttp import web, ClientSession
from typing import List
import itertools

class ReverseProxy:
    def __init__(self, backends: List[str]):
        self.backends = backends
        self.backend_cycle = itertools.cycle(backends)
        self.session = None

    async def start(self):
        self.session = ClientSession()

    async def stop(self):
        if self.session:
            await self.session.close()

    async def health_check(self, backend: str) -> bool:
        """Check if backend is healthy"""
        try:
            async with self.session.get(f"{backend}/health", timeout=2) as resp:
                return resp.status == 200
        except:
            return False

    async def get_healthy_backend(self) -> str:
        """Round-robin with health checks"""
        for _ in range(len(self.backends)):
            backend = next(self.backend_cycle)
            if await self.health_check(backend):
                return backend
        raise web.HTTPServiceUnavailable(text="No healthy backends")

    async def proxy_handler(self, request: web.Request) -> web.Response:
        """Proxy request to backend"""
        backend = await self.get_healthy_backend()
        url = f"{backend}{request.path_qs}"

        # Forward headers
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ('host', 'connection')
        }
        headers['X-Forwarded-For'] = request.remote
        headers['X-Real-IP'] = request.remote

        try:
            async with self.session.request(
                method=request.method,
                url=url,
                headers=headers,
                data=await request.read(),
                timeout=10
            ) as backend_resp:
                # Forward response
                body = await backend_resp.read()
                return web.Response(
                    body=body,
                    status=backend_resp.status,
                    headers=backend_resp.headers
                )
        except asyncio.TimeoutError:
            raise web.HTTPGatewayTimeout(text="Backend timeout")
        except Exception as e:
            raise web.HTTPBadGateway(text=f"Backend error: {e}")

async def init_app():
    proxy = ReverseProxy([
        "http://backend1:8080",
        "http://backend2:8080",
        "http://backend3:8080"
    ])

    await proxy.start()

    app = web.Application()
    app.router.add_route('*', '/{tail:.*}', proxy.proxy_handler)
    app.on_cleanup.append(lambda app: proxy.stop())

    return app

if __name__ == '__main__':
    web.run_app(init_app(), port=8000)
```

### Go Reverse Proxy with Load Balancing

```go
package main

import (
    "log"
    "net"
    "net/http"
    "net/http/httputil"
    "net/url"
    "sync"
    "time"
)

type Backend struct {
    URL          *url.URL
    Alive        bool
    mux          sync.RWMutex
    ReverseProxy *httputil.ReverseProxy
}

func (b *Backend) SetAlive(alive bool) {
    b.mux.Lock()
    defer b.mux.Unlock()
    b.Alive = alive
}

func (b *Backend) IsAlive() bool {
    b.mux.RLock()
    defer b.mux.RUnlock()
    return b.Alive
}

type LoadBalancer struct {
    backends []*Backend
    current  int
    mux      sync.Mutex
}

func NewLoadBalancer(backendURLs []string) *LoadBalancer {
    lb := &LoadBalancer{
        backends: make([]*Backend, len(backendURLs)),
    }

    for i, urlStr := range backendURLs {
        backendURL, _ := url.Parse(urlStr)
        lb.backends[i] = &Backend{
            URL:          backendURL,
            Alive:        true,
            ReverseProxy: httputil.NewSingleHostReverseProxy(backendURL),
        }
    }

    // Start health checks
    go lb.healthCheck()

    return lb
}

func (lb *LoadBalancer) nextBackend() *Backend {
    lb.mux.Lock()
    defer lb.mux.Unlock()

    // Round-robin through healthy backends
    start := lb.current
    for {
        backend := lb.backends[lb.current]
        lb.current = (lb.current + 1) % len(lb.backends)

        if backend.IsAlive() {
            return backend
        }

        // Tried all backends
        if lb.current == start {
            return nil
        }
    }
}

func (lb *LoadBalancer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    backend := lb.nextBackend()
    if backend == nil {
        http.Error(w, "Service Unavailable", http.StatusServiceUnavailable)
        return
    }

    // Add forwarding headers
    r.Header.Set("X-Forwarded-For", r.RemoteAddr)
    r.Header.Set("X-Real-IP", r.RemoteAddr)

    backend.ReverseProxy.ServeHTTP(w, r)
}

func (lb *LoadBalancer) healthCheck() {
    ticker := time.NewTicker(10 * time.Second)
    defer ticker.Stop()

    for range ticker.C {
        for _, backend := range lb.backends {
            go func(b *Backend) {
                alive := isBackendAlive(b.URL)
                b.SetAlive(alive)
                status := "up"
                if !alive {
                    status = "down"
                }
                log.Printf("Backend %s is %s", b.URL, status)
            }(backend)
        }
    }
}

func isBackendAlive(u *url.URL) bool {
    timeout := 2 * time.Second
    conn, err := net.DialTimeout("tcp", u.Host, timeout)
    if err != nil {
        return false
    }
    defer conn.Close()
    return true
}

func main() {
    backends := []string{
        "http://localhost:8081",
        "http://localhost:8082",
        "http://localhost:8083",
    }

    lb := NewLoadBalancer(backends)

    server := &http.Server{
        Addr:         ":8080",
        Handler:      lb,
        ReadTimeout:  10 * time.Second,
        WriteTimeout: 10 * time.Second,
    }

    log.Printf("Load balancer starting on :8080")
    log.Fatal(server.ListenAndServe())
}
```

### Caddy Configuration

```caddy
# Caddyfile - Simple reverse proxy with auto HTTPS
example.com {
    reverse_proxy backend1:8080 backend2:8080 backend3:8080 {
        lb_policy round_robin
        health_uri /health
        health_interval 10s
        health_timeout 2s
    }

    # Add security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        -Server
    }
}

# Path-based routing
api.example.com {
    reverse_proxy /v1/* backend-v1:8080
    reverse_proxy /v2/* backend-v2:8080
}
```

---

## Advanced Patterns

### Session Affinity (Sticky Sessions)

```nginx
upstream backend {
    ip_hash;  # Same IP → same backend
    server backend1.internal:8080;
    server backend2.internal:8080;
}

# Or using cookies
upstream backend {
    server backend1.internal:8080;
    server backend2.internal:8080;
    sticky cookie srv_id expires=1h domain=.example.com path=/;
}
```

### Rate Limiting

```nginx
# Define rate limit zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

server {
    listen 80;

    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://backend;
    }
}
```

### Request Buffering

```nginx
server {
    listen 80;

    # Buffer large uploads
    client_body_buffer_size 128k;
    client_max_body_size 10m;

    location / {
        proxy_pass http://backend;
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
}
```

### WebSocket Proxying

```nginx
upstream websocket_backend {
    server ws1.internal:8080;
    server ws2.internal:8080;
}

server {
    listen 80;

    location /ws/ {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;  # 24 hours
    }
}
```

---

## Best Practices

### 1. Always Set Forwarding Headers

```nginx
# ✅ Good: Preserve client information
location / {
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
}
```

### 2. Configure Timeouts

```nginx
# ✅ Good: Prevent hanging connections
location / {
    proxy_pass http://backend;
    proxy_connect_timeout 5s;
    proxy_send_timeout 10s;
    proxy_read_timeout 10s;
}
```

### 3. Use Health Checks

```python
# ✅ Good: Active health monitoring
async def health_check_loop(backends: List[str]):
    while True:
        for backend in backends:
            try:
                async with session.get(f"{backend}/health", timeout=2) as resp:
                    healthy = resp.status == 200
                    backend_status[backend] = healthy
            except:
                backend_status[backend] = False
        await asyncio.sleep(10)
```

---

## Troubleshooting

### Issue 1: 502 Bad Gateway

**Symptoms**: Proxy cannot reach backend
**Common Causes**:
- Backend server down
- Network connectivity issues
- Wrong backend address/port
- Backend timeout

**Solution**:
```nginx
# Add retry logic and backup servers
upstream backend {
    server backend1.internal:8080 max_fails=3 fail_timeout=30s;
    server backend2.internal:8080 max_fails=3 fail_timeout=30s;
    server backup.internal:8080 backup;
}

server {
    location / {
        proxy_pass http://backend;
        proxy_next_upstream error timeout http_502;
    }
}
```

### Issue 2: Lost Client IP Address

**Symptoms**: Backend sees proxy IP, not client IP
**Common Causes**:
- Missing X-Forwarded-For header
- Backend not reading forwarded headers

**Solution**:
```nginx
# Nginx configuration
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

```python
# Backend application (Flask)
from flask import Flask, request

app = Flask(__name__)

@app.route('/')
def index():
    # Get real client IP
    client_ip = request.headers.get('X-Real-IP') or \
                request.headers.get('X-Forwarded-For', '').split(',')[0] or \
                request.remote_addr
    return f"Your IP: {client_ip}"
```

### Issue 3: Session Affinity Issues

**Symptoms**: User session lost between requests
**Common Causes**:
- Load balancer distributing to different backends
- No sticky sessions configured

**Solution**:
```nginx
# Cookie-based sticky sessions
upstream backend {
    server backend1.internal:8080;
    server backend2.internal:8080;
    sticky cookie srv_id expires=1h;
}

# Or IP-based
upstream backend {
    ip_hash;
    server backend1.internal:8080;
    server backend2.internal:8080;
}
```

---

## Related Skills

- `proxies-forward-proxy` - Forward proxy concepts
- `proxies-nginx-configuration` - Detailed nginx configuration
- `proxies-traefik-configuration` - Traefik setup and configuration
- `proxies-envoy-proxy` - Envoy proxy architecture
- `proxies-cache-control` - Caching strategies
- `networking-load-balancing` - Load balancing algorithms
- `cryptography-tls-ssl` - TLS/SSL configuration

---

**Last Updated**: 2025-10-27
