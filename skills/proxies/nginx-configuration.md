---
name: proxies-nginx-configuration
description: Nginx configuration including server blocks, locations, upstreams, caching, SSL/TLS, security headers, and performance optimization
---

# Nginx Configuration

**Scope**: Nginx setup, configuration syntax, locations, upstreams, caching, SSL
**Lines**: ~400
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Setting up nginx as reverse proxy or web server
- Configuring load balancing
- Implementing caching strategies
- Setting up SSL/TLS termination
- Optimizing nginx performance
- Debugging nginx configuration issues
- Implementing security headers
- Configuring rate limiting

## Core Concepts

### Nginx Architecture

```
nginx.conf
├── events { }           # Connection processing
├── http {               # HTTP server settings
│   ├── upstream { }     # Backend server pools
│   ├── server {         # Virtual host
│   │   ├── listen       # Port and protocol
│   │   ├── server_name  # Domain name
│   │   └── location { } # Request matching
│   └── server { }
└── stream { }           # TCP/UDP load balancing
```

### Configuration Context Hierarchy

```nginx
# Main context
user nginx;
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    # HTTP context
    include mime.types;
    default_type application/octet-stream;

    upstream backend {
        # Upstream context
        server 127.0.0.1:8080;
    }

    server {
        # Server context
        listen 80;
        server_name example.com;

        location / {
            # Location context
            proxy_pass http://backend;
        }
    }
}
```

---

## Patterns

### Pattern 1: Basic Reverse Proxy

**Use Case**: Proxy requests to backend application

```nginx
# ❌ Bad: Minimal configuration
server {
    listen 80;
    location / {
        proxy_pass http://localhost:8080;
    }
}
```

```nginx
# ✅ Good: Complete proxy configuration
upstream backend {
    server 127.0.0.1:8080;
    keepalive 32;
}

server {
    listen 80;
    server_name example.com;

    # Logging
    access_log /var/log/nginx/example.access.log;
    error_log /var/log/nginx/example.error.log;

    location / {
        proxy_pass http://backend;

        # Proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
}
```

### Pattern 2: SSL/TLS Configuration

**Use Case**: HTTPS with modern security settings

```nginx
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    # SSL certificates
    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # SSL protocols and ciphers
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;

    # SSL session cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### Pattern 3: Advanced Caching

**Use Case**: Cache backend responses efficiently

```nginx
# Define cache zone
proxy_cache_path /var/cache/nginx/api
    levels=1:2
    keys_zone=api_cache:10m
    max_size=1g
    inactive=60m
    use_temp_path=off;

upstream backend {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name api.example.com;

    location /api/ {
        proxy_pass http://backend;

        # Caching
        proxy_cache api_cache;
        proxy_cache_key "$scheme$request_method$host$request_uri";
        proxy_cache_valid 200 10m;
        proxy_cache_valid 404 1m;
        proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
        proxy_cache_background_update on;
        proxy_cache_lock on;

        # Add cache status header
        add_header X-Cache-Status $upstream_cache_status;

        # Cache bypass conditions
        proxy_cache_bypass $http_cache_control;
        proxy_no_cache $http_pragma $http_authorization;
    }
}
```

---

## Location Matching

### Location Priority

```nginx
# 1. Exact match (highest priority)
location = /exact {
    return 200 "Exact match";
}

# 2. Preferential prefix match
location ^~ /images/ {
    root /var/www;
}

# 3. Regex match (case-sensitive)
location ~ \.php$ {
    fastcgi_pass unix:/var/run/php-fpm.sock;
}

# 4. Regex match (case-insensitive)
location ~* \.(jpg|jpeg|png|gif)$ {
    expires 30d;
}

# 5. Prefix match (lowest priority)
location /api/ {
    proxy_pass http://backend;
}
```

### Common Location Patterns

```nginx
# Static files
location /static/ {
    alias /var/www/static/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# SPA fallback
location / {
    try_files $uri $uri/ /index.html;
}

# API proxy
location /api/ {
    proxy_pass http://backend/;
    proxy_redirect off;
}

# WebSocket
location /ws/ {
    proxy_pass http://websocket_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}

# Health check endpoint
location = /health {
    access_log off;
    return 200 "OK\n";
    add_header Content-Type text/plain;
}
```

---

## Upstream Configuration

### Load Balancing Methods

```nginx
# Round-robin (default)
upstream backend {
    server backend1.internal:8080;
    server backend2.internal:8080;
    server backend3.internal:8080;
}

# Least connections
upstream backend {
    least_conn;
    server backend1.internal:8080;
    server backend2.internal:8080;
}

# IP hash (sticky sessions)
upstream backend {
    ip_hash;
    server backend1.internal:8080;
    server backend2.internal:8080;
}

# Weighted round-robin
upstream backend {
    server backend1.internal:8080 weight=3;
    server backend2.internal:8080 weight=2;
    server backend3.internal:8080 weight=1;
}

# Health checks and failover
upstream backend {
    server backend1.internal:8080 max_fails=3 fail_timeout=30s;
    server backend2.internal:8080 max_fails=3 fail_timeout=30s;
    server backup.internal:8080 backup;

    keepalive 32;
}
```

---

## Complete Production Configuration

### Main Configuration (nginx.conf)

```nginx
user nginx;
worker_processes auto;
worker_rlimit_nofile 65535;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 10m;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml font/truetype font/opentype
               application/vnd.ms-fontobject image/svg+xml;

    # Security
    server_tokens off;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

    # Connection limiting
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    # Include virtual hosts
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
```

### Virtual Host Configuration

```nginx
# /etc/nginx/sites-available/example.com

upstream app_backend {
    least_conn;
    server app1.internal:8080 max_fails=3 fail_timeout=30s;
    server app2.internal:8080 max_fails=3 fail_timeout=30s;
    server app3.internal:8080 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# HTTP → HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com www.example.com;

    # SSL configuration
    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/example.com.access.log main;
    error_log /var/log/nginx/example.com.error.log;

    # Static files
    location /static/ {
        alias /var/www/example.com/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Media files
    location /media/ {
        alias /var/www/example.com/media/;
        expires 1d;
    }

    # API with rate limiting
    location /api/ {
        limit_req zone=api burst=50 nodelay;
        limit_conn addr 10;

        proxy_pass http://app_backend/;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;

        # Error handling
        proxy_next_upstream error timeout http_502 http_503 http_504;
    }

    # Main application
    location / {
        limit_req zone=general burst=20 nodelay;

        proxy_pass http://app_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location = /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }
}
```

---

## Security Configuration

### Rate Limiting and DDoS Protection

```nginx
# Define rate limit zones
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=search:10m rate=10r/s;

server {
    listen 443 ssl http2;
    server_name example.com;

    # Login endpoint - strict rate limit
    location /login {
        limit_req zone=login burst=2 nodelay;
        limit_req_status 429;
        proxy_pass http://backend;
    }

    # API endpoints - moderate rate limit
    location /api/ {
        limit_req zone=api burst=50 nodelay;
        proxy_pass http://backend;
    }

    # Search endpoint - custom rate limit
    location /search {
        limit_req zone=search burst=5 delay=3;
        proxy_pass http://backend;
    }
}
```

### IP Whitelisting/Blacklisting

```nginx
# Allow specific IPs
geo $allowed_ip {
    default 0;
    10.0.0.0/8 1;
    172.16.0.0/12 1;
    192.168.0.0/16 1;
}

server {
    listen 443 ssl http2;
    server_name admin.example.com;

    location /admin/ {
        if ($allowed_ip = 0) {
            return 403;
        }
        proxy_pass http://backend;
    }
}

# Or using allow/deny
location /admin/ {
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    deny all;
    proxy_pass http://backend;
}
```

---

## Performance Optimization

### Connection Pooling

```nginx
upstream backend {
    server backend1.internal:8080;
    server backend2.internal:8080;

    # Keep 32 idle connections to each backend
    keepalive 32;
    keepalive_requests 100;
    keepalive_timeout 60s;
}

server {
    location / {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";  # Clear Connection header
    }
}
```

### Static Asset Optimization

```nginx
location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
    root /var/www/static;
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;

    # Gzip for compressible assets
    gzip_static on;
}
```

---

## Troubleshooting

### Issue 1: 502 Bad Gateway

**Symptoms**: Nginx cannot connect to backend
**Debug Steps**:

```bash
# Check nginx error log
tail -f /var/log/nginx/error.log

# Test backend connectivity
curl http://backend1.internal:8080/health

# Check nginx configuration
nginx -t

# Reload configuration
nginx -s reload
```

**Common Solutions**:
```nginx
# Increase timeouts
proxy_connect_timeout 10s;
proxy_read_timeout 60s;

# Add backup server
upstream backend {
    server backend1.internal:8080;
    server backup.internal:8080 backup;
}
```

### Issue 2: Configuration Test Failures

**Debug Command**:
```bash
# Test configuration syntax
nginx -t

# Detailed configuration dump
nginx -T
```

**Common Issues**:
- Missing semicolons
- Wrong context for directive
- Invalid regex in location
- Duplicate listen directives

---

## Related Skills

- `proxies-reverse-proxy` - Reverse proxy patterns
- `proxies-cache-control` - HTTP caching strategies
- `cryptography-tls-ssl` - SSL/TLS configuration
- `observability-logging` - Log analysis and monitoring
- `infrastructure-performance-tuning` - System-level optimization

---

**Last Updated**: 2025-10-27
