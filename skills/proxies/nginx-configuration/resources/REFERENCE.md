# Nginx Configuration Reference

Comprehensive reference material for Nginx configuration, architecture, directives, optimization, and best practices.

---

## Table of Contents

1. [Nginx Architecture](#nginx-architecture)
2. [Configuration Contexts](#configuration-contexts)
3. [Core Directives Reference](#core-directives-reference)
4. [Server Block Configuration](#server-block-configuration)
5. [Location Matching](#location-matching)
6. [Upstream Configuration](#upstream-configuration)
7. [Proxy Configuration](#proxy-configuration)
8. [SSL/TLS Configuration](#ssltls-configuration)
9. [Caching Strategies](#caching-strategies)
10. [Security Configuration](#security-configuration)
11. [Performance Optimization](#performance-optimization)
12. [Variables Reference](#variables-reference)
13. [Module System](#module-system)
14. [Best Practices](#best-practices)
15. [Anti-Patterns](#anti-patterns)
16. [Troubleshooting](#troubleshooting)
17. [Real-World Configurations](#real-world-configurations)
18. [RFC References](#rfc-references)

---

## Nginx Architecture

### Process Model

Nginx uses a master-worker process architecture:

```
Master Process (nginx)
├── Worker Process 1 (handles connections)
├── Worker Process 2 (handles connections)
├── Worker Process N (handles connections)
└── Cache Manager Process (optional)
```

**Master Process**:
- Read and validate configuration
- Create worker processes
- Handle signals (reload, shutdown)
- Maintain worker processes

**Worker Processes**:
- Handle client connections
- Process requests
- Serve static content
- Proxy to backends
- Non-blocking event-driven architecture

**Event Model**:
```
Worker Process
├── epoll/kqueue (event notification)
├── Event Queue
│   ├── Connection accepted
│   ├── Data received
│   ├── Backend response ready
│   └── Timer expired
└── Request Processing Pipeline
    ├── Parse request
    ├── Find location
    ├── Apply directives
    ├── Generate/proxy response
    └── Send to client
```

### Request Processing Phases

Nginx processes requests through multiple phases:

```
1. NGX_HTTP_POST_READ_PHASE         - Read request body
2. NGX_HTTP_SERVER_REWRITE_PHASE    - Server-level rewrite
3. NGX_HTTP_FIND_CONFIG_PHASE       - Find location configuration
4. NGX_HTTP_REWRITE_PHASE           - Location-level rewrite
5. NGX_HTTP_POST_REWRITE_PHASE      - Post-rewrite processing
6. NGX_HTTP_PREACCESS_PHASE         - Access pre-checks (limit_req, limit_conn)
7. NGX_HTTP_ACCESS_PHASE            - Access control (allow, deny)
8. NGX_HTTP_POST_ACCESS_PHASE       - Post-access processing
9. NGX_HTTP_PRECONTENT_PHASE        - Before content generation
10. NGX_HTTP_CONTENT_PHASE          - Content generation/proxy
11. NGX_HTTP_LOG_PHASE              - Logging
```

### Connection Processing

```
┌──────────────────────────────────────────────────────────────┐
│                       Client Connection                       │
└──────────────────────────────────────────────────────────────┘
                             ↓
                    ┌────────────────┐
                    │ Accept Socket  │
                    └────────────────┘
                             ↓
                    ┌────────────────┐
                    │  Read Request  │
                    └────────────────┘
                             ↓
                    ┌────────────────┐
                    │ Parse Headers  │
                    └────────────────┘
                             ↓
                    ┌────────────────┐
                    │ Find Location  │
                    └────────────────┘
                             ↓
              ┌──────────────┴──────────────┐
              ↓                             ↓
      ┌──────────────┐            ┌──────────────┐
      │ Static File  │            │ Proxy Pass   │
      └──────────────┘            └──────────────┘
              ↓                             ↓
              │                    ┌──────────────┐
              │                    │ Connect Pool │
              │                    └──────────────┘
              │                             ↓
              │                    ┌──────────────┐
              │                    │ Send Request │
              │                    └──────────────┘
              │                             ↓
              │                    ┌──────────────┐
              │                    │ Read Response│
              │                    └──────────────┘
              ↓                             ↓
      ┌──────────────────────────────────────┐
      │       Send Response to Client        │
      └──────────────────────────────────────┘
                             ↓
                    ┌────────────────┐
                    │  Log Request   │
                    └────────────────┘
                             ↓
              ┌──────────────┴──────────────┐
              ↓                             ↓
      ┌──────────────┐            ┌──────────────┐
      │ Keep-Alive   │            │    Close     │
      └──────────────┘            └──────────────┘
```

---

## Configuration Contexts

### Context Hierarchy

```
Main Context (global)
├── events { }                    # Connection processing
├── http { }                      # HTTP server
│   ├── upstream { }              # Backend servers
│   ├── map { }                   # Variables mapping
│   ├── geo { }                   # Geographic mapping
│   ├── limit_req_zone            # Rate limiting zones
│   ├── limit_conn_zone           # Connection limiting zones
│   ├── proxy_cache_path          # Cache configuration
│   └── server { }                # Virtual host
│       ├── location { }          # Request matching
│       │   └── location { }      # Nested locations
│       └── if { }                # Conditional
├── stream { }                    # TCP/UDP load balancing
│   ├── upstream { }
│   └── server { }
└── mail { }                      # Mail proxy
    └── server { }
```

### Directive Inheritance

Directives inherit from parent contexts:

```nginx
http {
    # Applies to all servers
    client_max_body_size 10m;

    server {
        # Inherits 10m, applies to all locations in this server
        listen 80;

        location /api/ {
            # Inherits 10m, can override
            client_max_body_size 50m;  # Override for this location
        }

        location /static/ {
            # Inherits 10m from http context
        }
    }
}
```

---

## Core Directives Reference

### Main Context Directives

#### user

**Syntax**: `user user [group];`
**Default**: `nobody`
**Context**: main

Defines user and group credentials used by worker processes.

```nginx
user nginx nginx;
```

#### worker_processes

**Syntax**: `worker_processes number | auto;`
**Default**: `1`
**Context**: main

Number of worker processes. Use `auto` to match CPU cores.

```nginx
worker_processes auto;
```

#### worker_rlimit_nofile

**Syntax**: `worker_rlimit_nofile number;`
**Default**: —
**Context**: main

Changes the limit on the maximum number of open files for worker processes.

```nginx
worker_rlimit_nofile 65535;
```

#### error_log

**Syntax**: `error_log file [level];`
**Default**: `logs/error.log error`
**Context**: main, http, server, location

Error log configuration. Levels: debug, info, notice, warn, error, crit, alert, emerg.

```nginx
error_log /var/log/nginx/error.log warn;
```

#### pid

**Syntax**: `pid file;`
**Default**: `logs/nginx.pid`
**Context**: main

PID file location.

```nginx
pid /var/run/nginx.pid;
```

---

### Events Context Directives

#### worker_connections

**Syntax**: `worker_connections number;`
**Default**: `512`
**Context**: events

Maximum number of simultaneous connections per worker.

```nginx
events {
    worker_connections 4096;
}
```

**Calculation**:
```
max_clients = worker_processes × worker_connections
# For reverse proxy: max_clients = worker_processes × worker_connections / 2
# (each proxied connection uses 2 connections: client and upstream)
```

#### use

**Syntax**: `use method;`
**Default**: auto-select
**Context**: events

Connection processing method: select, poll, kqueue, epoll, /dev/poll, eventport.

```nginx
events {
    use epoll;  # Linux
    # use kqueue;  # BSD/macOS
}
```

#### multi_accept

**Syntax**: `multi_accept on | off;`
**Default**: `off`
**Context**: events

Accept multiple connections at once.

```nginx
events {
    multi_accept on;
}
```

---

### HTTP Context Directives

#### include

**Syntax**: `include file | mask;`
**Context**: any

Include another file or files matching pattern.

```nginx
http {
    include /etc/nginx/mime.types;
    include /etc/nginx/conf.d/*.conf;
}
```

#### default_type

**Syntax**: `default_type mime-type;`
**Default**: `text/plain`
**Context**: http, server, location

Default MIME type for responses.

```nginx
http {
    default_type application/octet-stream;
}
```

#### log_format

**Syntax**: `log_format name [escape=default|json|none] string ...;`
**Default**: `combined "..."`
**Context**: http

Define custom log format.

```nginx
log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                '$status $body_bytes_sent "$http_referer" '
                '"$http_user_agent" "$http_x_forwarded_for" '
                'rt=$request_time uct="$upstream_connect_time" '
                'uht="$upstream_header_time" urt="$upstream_response_time"';

log_format json escape=json '{'
    '"time":"$time_iso8601",'
    '"remote_addr":"$remote_addr",'
    '"request":"$request",'
    '"status":$status,'
    '"body_bytes_sent":$body_bytes_sent,'
    '"request_time":$request_time,'
    '"upstream_response_time":"$upstream_response_time"'
'}';
```

#### access_log

**Syntax**: `access_log path [format [buffer=size] [gzip[=level]] [flush=time] [if=condition]];`
**Default**: `logs/access.log combined`
**Context**: http, server, location, if in location

Access log configuration.

```nginx
access_log /var/log/nginx/access.log main;
access_log /var/log/nginx/access.log main buffer=32k;
access_log /var/log/nginx/access.log json;
access_log off;  # Disable logging
```

#### sendfile

**Syntax**: `sendfile on | off;`
**Default**: `off`
**Context**: http, server, location

Enable efficient file transfer using sendfile() syscall.

```nginx
http {
    sendfile on;
}
```

#### tcp_nopush

**Syntax**: `tcp_nopush on | off;`
**Default**: `off`
**Context**: http, server, location

Enable TCP_CORK (send headers and file in one packet). Requires sendfile on.

```nginx
http {
    tcp_nopush on;
}
```

#### tcp_nodelay

**Syntax**: `tcp_nodelay on | off;`
**Default**: `on`
**Context**: http, server, location

Enable TCP_NODELAY (disable Nagle algorithm). For keep-alive connections.

```nginx
http {
    tcp_nodelay on;
}
```

#### keepalive_timeout

**Syntax**: `keepalive_timeout timeout [header_timeout];`
**Default**: `75s`
**Context**: http, server, location

Keep-alive connection timeout.

```nginx
http {
    keepalive_timeout 65;
}
```

#### keepalive_requests

**Syntax**: `keepalive_requests number;`
**Default**: `100`
**Context**: http, server, location

Maximum requests per keep-alive connection.

```nginx
http {
    keepalive_requests 100;
}
```

#### client_max_body_size

**Syntax**: `client_max_body_size size;`
**Default**: `1m`
**Context**: http, server, location

Maximum allowed size of client request body.

```nginx
http {
    client_max_body_size 10m;
}
```

#### client_body_buffer_size

**Syntax**: `client_body_buffer_size size;`
**Default**: `8k|16k`
**Context**: http, server, location

Buffer size for reading client request body.

```nginx
http {
    client_body_buffer_size 16k;
}
```

#### client_header_buffer_size

**Syntax**: `client_header_buffer_size size;`
**Default**: `1k`
**Context**: http, server

Buffer size for reading client request header.

```nginx
http {
    client_header_buffer_size 1k;
}
```

#### large_client_header_buffers

**Syntax**: `large_client_header_buffers number size;`
**Default**: `4 8k`
**Context**: http, server

Maximum number and size of buffers for large client headers.

```nginx
http {
    large_client_header_buffers 4 16k;
}
```

#### types_hash_max_size

**Syntax**: `types_hash_max_size size;`
**Default**: `1024`
**Context**: http, server, location

Maximum size of types hash tables.

```nginx
http {
    types_hash_max_size 2048;
}
```

#### server_tokens

**Syntax**: `server_tokens on | off | build | string;`
**Default**: `on`
**Context**: http, server, location

Show Nginx version in error messages and Server header.

```nginx
http {
    server_tokens off;  # Hide version
}
```

#### gzip

**Syntax**: `gzip on | off;`
**Default**: `off`
**Context**: http, server, location

Enable gzip compression.

```nginx
http {
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss;
}
```

---

## Server Block Configuration

### listen Directive

**Syntax**: `listen address[:port] [parameters];`
**Default**: `0.0.0.0:80`
**Context**: server

Listen on specified address and port.

```nginx
# IPv4
listen 80;
listen 443 ssl http2;
listen 127.0.0.1:8080;

# IPv6
listen [::]:80;
listen [::]:443 ssl http2;

# Parameters
listen 443 ssl http2 default_server;
listen 443 ssl http2 reuseport;
listen 443 ssl http2 so_keepalive=on;
listen 443 ssl http2 backlog=4096;

# Unix socket
listen unix:/var/run/nginx.sock;
```

**Parameters**:
- `default_server`: Default server for address:port
- `ssl`: Enable SSL/TLS
- `http2`: Enable HTTP/2
- `reuseport`: Create individual listening socket for each worker (SO_REUSEPORT)
- `backlog=number`: Set listen() backlog queue size
- `so_keepalive=on|off|[keepidle]:[keepintvl]:[keepcnt]`: TCP keepalive

### server_name Directive

**Syntax**: `server_name name ...;`
**Default**: `""`
**Context**: server

Virtual host name matching.

```nginx
# Exact name
server_name example.com;

# Multiple names
server_name example.com www.example.com;

# Wildcard
server_name *.example.com;
server_name example.*;

# Regular expression
server_name ~^www\d+\.example\.com$;
server_name ~^(?<subdomain>.+)\.example\.com$;

# Match all (catch-all)
server_name _;

# Default server (no server_name needed)
server {
    listen 80 default_server;
}
```

**Matching Priority**:
1. Exact name
2. Longest wildcard starting with `*`
3. Longest wildcard ending with `*`
4. First matching regular expression
5. Default server

### root and alias

**Syntax**: `root path;`
**Default**: `html`
**Context**: http, server, location

Document root directory.

```nginx
# root: appends URI to root path
location /static/ {
    root /var/www;
    # /static/file.js → /var/www/static/file.js
}

# alias: replaces location with alias path
location /static/ {
    alias /var/www/assets/;
    # /static/file.js → /var/www/assets/file.js
}

# Common mistake with alias
location /static {  # ❌ Missing trailing slash
    alias /var/www/assets/;
}

location /static/ {  # ✅ Correct
    alias /var/www/assets/;
}
```

### index

**Syntax**: `index file ...;`
**Default**: `index.html`
**Context**: http, server, location

Index files to serve for directory requests.

```nginx
location / {
    index index.html index.htm;
}

location /app/ {
    index index.php index.html;
}
```

### try_files

**Syntax**: `try_files file ... uri | =code;`
**Context**: server, location

Try files in order, fallback to URI or return code.

```nginx
# SPA fallback
location / {
    try_files $uri $uri/ /index.html;
}

# PHP application
location / {
    try_files $uri $uri/ /index.php?$query_string;
}

# Static files, then proxy
location / {
    try_files $uri @proxy;
}

location @proxy {
    proxy_pass http://backend;
}

# Return 404 if not found
location /images/ {
    try_files $uri =404;
}
```

### return

**Syntax**: `return code [text] | code URL | URL;`
**Context**: server, location, if

Return response immediately.

```nginx
# HTTP → HTTPS redirect
server {
    listen 80;
    return 301 https://$host$request_uri;
}

# Redirect
location /old-page {
    return 301 /new-page;
}

# Return text
location /health {
    return 200 "OK\n";
    add_header Content-Type text/plain;
}

# Return JSON
location /status {
    return 200 '{"status":"ok"}';
    add_header Content-Type application/json;
}
```

### rewrite

**Syntax**: `rewrite regex replacement [flag];`
**Context**: server, location, if

Rewrite URI using regular expression.

```nginx
# Basic rewrite
rewrite ^/old/(.*)$ /new/$1 permanent;

# Flags:
# last - stop processing, search for new location
# break - stop processing, use current location
# redirect - 302 temporary redirect
# permanent - 301 permanent redirect

# Example with last
location /download/ {
    rewrite ^/download/(.*)$ /files/$1 last;
}

# Example with break
location /download/ {
    rewrite ^/download/(.*)$ /files/$1 break;
    root /var/www;
}
```

---

## Location Matching

### Location Syntax

**Syntax**: `location [modifier] pattern { ... }`
**Context**: server, location

Match request URI.

**Modifiers**:
- `=` : Exact match
- `^~` : Preferential prefix (no regex check if matched)
- `~` : Case-sensitive regex
- `~*` : Case-insensitive regex
- (none) : Prefix match

### Matching Order

1. Exact match (`=`)
2. Preferential prefix (`^~`)
3. Regular expressions (`~` and `~*`) in order of appearance
4. Prefix match (longest match wins)

```nginx
# 1. Exact match (highest priority)
location = / {
    return 200 "Exact root";
}

location = /exact {
    return 200 "Exact match";
}

# 2. Preferential prefix (stops regex matching)
location ^~ /images/ {
    root /var/www;
}

location ^~ /static/ {
    alias /var/www/static/;
}

# 3. Regex match (case-sensitive)
location ~ \.php$ {
    fastcgi_pass unix:/var/run/php-fpm.sock;
}

location ~ ^/api/v[0-9]+/ {
    proxy_pass http://api_backend;
}

# 4. Regex match (case-insensitive)
location ~* \.(jpg|jpeg|png|gif|ico)$ {
    expires 30d;
}

location ~* \.(css|js)$ {
    expires 1y;
}

# 5. Prefix match (lowest priority, longest wins)
location /api/ {
    proxy_pass http://backend;
}

location / {
    try_files $uri $uri/ /index.html;
}
```

### Location Matching Examples

```nginx
# Request: /exact
# Matches: location = /exact (exact match)

# Request: /images/logo.png
# Matches: location ^~ /images/ (preferential prefix)

# Request: /style.css
# Matches: location ~* \.(css|js)$ (case-insensitive regex)

# Request: /api/v1/users
# Matches: location ~ ^/api/v[0-9]+/ (case-sensitive regex)

# Request: /about
# Matches: location / (prefix match)
```

### Named Locations

```nginx
location / {
    try_files $uri $uri/ @fallback;
}

location @fallback {
    proxy_pass http://backend;
}

# Error page named location
error_page 404 @not_found;

location @not_found {
    return 404 '{"error":"not found"}';
    add_header Content-Type application/json;
}
```

### Nested Locations

```nginx
location /api/ {
    # Applies to all /api/* requests
    limit_req zone=api burst=50;

    location /api/v1/ {
        # Applies to /api/v1/* requests
        proxy_pass http://backend_v1;
    }

    location /api/v2/ {
        # Applies to /api/v2/* requests
        proxy_pass http://backend_v2;
    }

    # Fallback for other /api/* requests
    proxy_pass http://backend_default;
}
```

---

## Upstream Configuration

### Basic Upstream

**Syntax**: `upstream name { ... }`
**Context**: http

Define backend server pool.

```nginx
upstream backend {
    server 127.0.0.1:8080;
    server 127.0.0.1:8081;
    server 127.0.0.1:8082;
}

server {
    location / {
        proxy_pass http://backend;
    }
}
```

### Load Balancing Methods

#### Round-robin (default)

```nginx
upstream backend {
    server backend1.internal:8080;
    server backend2.internal:8080;
    server backend3.internal:8080;
}
```

#### Least Connections

```nginx
upstream backend {
    least_conn;
    server backend1.internal:8080;
    server backend2.internal:8080;
}
```

#### IP Hash (sticky sessions)

```nginx
upstream backend {
    ip_hash;
    server backend1.internal:8080;
    server backend2.internal:8080;
}
```

#### Hash (generic hash)

```nginx
upstream backend {
    hash $request_uri consistent;
    server backend1.internal:8080;
    server backend2.internal:8080;
}

# Hash by cookie
upstream backend {
    hash $cookie_session_id;
    server backend1.internal:8080;
    server backend2.internal:8080;
}
```

#### Random

```nginx
upstream backend {
    random;
    server backend1.internal:8080;
    server backend2.internal:8080;
}

# Random with least_conn weighting
upstream backend {
    random two least_conn;
    server backend1.internal:8080;
    server backend2.internal:8080;
}
```

### Server Parameters

```nginx
upstream backend {
    # Weight (default: 1)
    server backend1.internal:8080 weight=3;
    server backend2.internal:8080 weight=2;
    server backend3.internal:8080 weight=1;

    # Max failures before marking down
    server backend4.internal:8080 max_fails=3 fail_timeout=30s;

    # Backup server (only used when primary servers down)
    server backup.internal:8080 backup;

    # Mark server down temporarily
    server backend5.internal:8080 down;

    # Max concurrent connections (nginx-plus or third-party module)
    # server backend6.internal:8080 max_conns=100;
}
```

### Keepalive Connections

```nginx
upstream backend {
    server backend1.internal:8080;
    server backend2.internal:8080;

    # Keep 32 idle connections to each backend
    keepalive 32;

    # Maximum requests per connection
    keepalive_requests 100;

    # Idle timeout
    keepalive_timeout 60s;
}

server {
    location / {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";  # Required for keepalive
    }
}
```

### Health Checks (passive)

```nginx
upstream backend {
    server backend1.internal:8080 max_fails=3 fail_timeout=30s;
    server backend2.internal:8080 max_fails=3 fail_timeout=30s;
    server backup.internal:8080 backup;
}

# Nginx Plus supports active health checks:
# upstream backend {
#     zone backend 64k;
#     server backend1.internal:8080;
#     server backend2.internal:8080;
# }
#
# server {
#     location / {
#         proxy_pass http://backend;
#         health_check interval=5s fails=3 passes=2 uri=/health;
#     }
# }
```

### Advanced Upstream Configuration

```nginx
upstream api_backend {
    # Load balancing
    least_conn;

    # Servers
    server api1.internal:8080 weight=2 max_fails=3 fail_timeout=30s;
    server api2.internal:8080 weight=2 max_fails=3 fail_timeout=30s;
    server api3.internal:8080 weight=1 max_fails=3 fail_timeout=30s;
    server api-backup.internal:8080 backup;

    # Keepalive
    keepalive 32;
    keepalive_requests 100;
    keepalive_timeout 60s;

    # Shared memory zone (for state sharing between workers)
    # zone api_backend 64k;
}
```

---

## Proxy Configuration

### proxy_pass

**Syntax**: `proxy_pass URL;`
**Context**: location, if in location

Proxy requests to backend server.

```nginx
# Without URI
location /api/ {
    proxy_pass http://backend;
    # /api/users → http://backend/api/users
}

# With URI
location /api/ {
    proxy_pass http://backend/;
    # /api/users → http://backend/users (location path stripped)
}

location /api/ {
    proxy_pass http://backend/v1/;
    # /api/users → http://backend/v1/users
}

# With variable (requires resolver)
location / {
    set $backend "backend.internal";
    resolver 8.8.8.8;
    proxy_pass http://$backend;
}
```

### Proxy Headers

```nginx
location / {
    proxy_pass http://backend;

    # Standard headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;

    # WebSocket support
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;

    # Custom headers
    proxy_set_header X-Request-ID $request_id;
}

# Connection upgrade map for WebSocket
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
```

### Proxy Timeouts

```nginx
location / {
    proxy_pass http://backend;

    # Connection timeout (default: 60s)
    proxy_connect_timeout 5s;

    # Send timeout (default: 60s)
    proxy_send_timeout 10s;

    # Read timeout (default: 60s)
    proxy_read_timeout 30s;

    # Next upstream timeout
    proxy_next_upstream_timeout 10s;
    proxy_next_upstream_tries 3;
}
```

### Proxy Buffering

```nginx
location / {
    proxy_pass http://backend;

    # Enable buffering (default: on)
    proxy_buffering on;

    # Buffer size for response headers (default: 4k|8k)
    proxy_buffer_size 4k;

    # Number and size of buffers for response body (default: 8 4k|8k)
    proxy_buffers 8 4k;

    # Buffer size for busy reading (default: 8k|16k)
    proxy_busy_buffers_size 16k;

    # Temp file size (default: 1024m)
    proxy_max_temp_file_size 1024m;

    # Threshold for temp file (default: 16k|32k)
    proxy_temp_file_write_size 16k;
}

# Disable buffering for streaming
location /stream/ {
    proxy_pass http://streaming_backend;
    proxy_buffering off;
}
```

### Proxy Error Handling

```nginx
location / {
    proxy_pass http://backend;

    # When to try next upstream server
    proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;

    # Timeout for next upstream
    proxy_next_upstream_timeout 10s;

    # Max tries
    proxy_next_upstream_tries 3;

    # Intercept errors
    proxy_intercept_errors on;
}

# Custom error pages
error_page 502 503 504 /50x.html;
location = /50x.html {
    root /usr/share/nginx/html;
}
```

### Proxy Redirect

```nginx
location / {
    proxy_pass http://backend;

    # Rewrite Location and Refresh headers
    proxy_redirect default;
    # or
    proxy_redirect http://backend/ http://$host/;
    # or disable
    proxy_redirect off;
}
```

---

## SSL/TLS Configuration

### Basic SSL Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    # Certificate and key
    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # Protocols
    ssl_protocols TLSv1.2 TLSv1.3;

    # Ciphers
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
}
```

### SSL Session Cache

```nginx
http {
    # Shared session cache (1MB ≈ 4000 sessions)
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Disable session tickets (for better forward secrecy)
    ssl_session_tickets off;
}
```

### OCSP Stapling

```nginx
server {
    listen 443 ssl http2;

    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;

    # Trusted certificate for stapling verification
    ssl_trusted_certificate /etc/ssl/certs/ca-chain.crt;

    # DNS resolver for OCSP
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
}
```

### Security Headers

```nginx
server {
    listen 443 ssl http2;

    # HSTS (HTTP Strict Transport Security)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Prevent clickjacking
    add_header X-Frame-Options "SAMEORIGIN" always;

    # Prevent MIME type sniffing
    add_header X-Content-Type-Options "nosniff" always;

    # XSS protection (legacy)
    add_header X-XSS-Protection "1; mode=block" always;

    # CSP (Content Security Policy)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # Referrer policy
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Permissions policy
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
}
```

### SSL Configuration (Mozilla Modern)

```nginx
# Modern configuration (TLS 1.3 only)
ssl_protocols TLSv1.3;
ssl_prefer_server_ciphers off;

# Modern configuration (TLS 1.2 + 1.3)
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers off;
```

### SSL Configuration (Mozilla Intermediate)

```nginx
# Intermediate configuration (wider compatibility)
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-CHACHA20-POLY1305';
ssl_prefer_server_ciphers off;
```

### HTTP to HTTPS Redirect

```nginx
# Method 1: Separate server blocks
server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;

    # Allow certbot challenges
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect everything else
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com www.example.com;

    # SSL configuration
    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;
}

# Method 2: if statement (less efficient)
server {
    listen 80;
    listen 443 ssl http2;

    if ($scheme != "https") {
        return 301 https://$host$request_uri;
    }
}
```

---

## Caching Strategies

### Proxy Cache Path

**Syntax**: `proxy_cache_path path [levels=levels] [keys_zone=name:size] [max_size=size] [inactive=time] [use_temp_path=on|off];`
**Context**: http

Define cache storage.

```nginx
http {
    # Cache for API responses
    proxy_cache_path /var/cache/nginx/api
        levels=1:2
        keys_zone=api_cache:10m
        max_size=1g
        inactive=60m
        use_temp_path=off;

    # Cache for static proxied content
    proxy_cache_path /var/cache/nginx/static
        levels=1:2
        keys_zone=static_cache:100m
        max_size=10g
        inactive=7d
        use_temp_path=off;
}
```

**Parameters**:
- `levels`: Directory hierarchy (1:2 = 2 levels, 1 char and 2 chars)
- `keys_zone`: Shared memory zone name and size (1MB ≈ 8000 keys)
- `max_size`: Maximum cache size
- `inactive`: Remove cached items not accessed for this time
- `use_temp_path`: Use temp path or write directly to cache

### Proxy Cache Configuration

```nginx
location /api/ {
    proxy_pass http://backend;

    # Enable caching
    proxy_cache api_cache;

    # Cache key (default: $scheme$proxy_host$request_uri)
    proxy_cache_key "$scheme$request_method$host$request_uri";

    # Cache validity by status code
    proxy_cache_valid 200 10m;
    proxy_cache_valid 301 302 1h;
    proxy_cache_valid 404 1m;
    proxy_cache_valid any 1m;

    # Use stale cache on backend errors
    proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;

    # Update stale cache in background
    proxy_cache_background_update on;

    # Lock multiple identical requests
    proxy_cache_lock on;
    proxy_cache_lock_timeout 5s;

    # Minimum uses before caching
    proxy_cache_min_uses 3;

    # Methods to cache
    proxy_cache_methods GET HEAD;

    # Add cache status header
    add_header X-Cache-Status $upstream_cache_status;
}
```

### Cache Bypass and Revalidation

```nginx
location /api/ {
    proxy_pass http://backend;
    proxy_cache api_cache;

    # Bypass cache conditions
    proxy_cache_bypass $http_cache_control $cookie_nocache $arg_nocache;

    # Don't cache conditions
    proxy_no_cache $http_pragma $http_authorization;

    # Revalidate with backend
    proxy_cache_revalidate on;
}

# Skip caching for authenticated users
map $http_cookie $no_cache {
    default 0;
    ~*session_id 1;
}

location / {
    proxy_cache api_cache;
    proxy_cache_bypass $no_cache;
    proxy_no_cache $no_cache;
}
```

### Cache Status Values

```nginx
# $upstream_cache_status values:
# MISS - not in cache, fetched from backend
# HIT - served from cache
# EXPIRED - cache expired, fetched from backend
# STALE - using stale cache (backend error)
# UPDATING - cache updating in background
# REVALIDATED - cache revalidated with backend (304)
# BYPASS - cache bypassed

add_header X-Cache-Status $upstream_cache_status;
```

### FastCGI Cache (for PHP)

```nginx
http {
    fastcgi_cache_path /var/cache/nginx/fastcgi
        levels=1:2
        keys_zone=php_cache:100m
        max_size=2g
        inactive=60m;
}

server {
    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php-fpm.sock;

        fastcgi_cache php_cache;
        fastcgi_cache_key "$scheme$request_method$host$request_uri";
        fastcgi_cache_valid 200 10m;

        # Don't cache POST requests
        fastcgi_cache_methods GET HEAD;

        # Bypass cache for logged-in users
        fastcgi_cache_bypass $cookie_PHPSESSID;
        fastcgi_no_cache $cookie_PHPSESSID;

        add_header X-FastCGI-Cache $upstream_cache_status;
    }
}
```

### Cache Purging

```nginx
# Using proxy_cache_purge directive (nginx-plus or cache_purge module)
location ~ /purge(/.*) {
    allow 127.0.0.1;
    deny all;
    proxy_cache_purge api_cache "$scheme$request_method$host$1";
}

# Manual purge (remove cache files)
# rm -rf /var/cache/nginx/api/*
```

---

## Security Configuration

### Rate Limiting

```nginx
http {
    # Define rate limit zones
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=search:10m rate=10r/s;

    # Connection limit zone
    limit_conn_zone $binary_remote_addr zone=addr:10m;
}

server {
    # General rate limit
    location / {
        limit_req zone=general burst=20 nodelay;
        limit_req_status 429;
    }

    # API rate limit
    location /api/ {
        limit_req zone=api burst=50 nodelay;
        limit_conn addr 10;
    }

    # Login rate limit (strict)
    location /login {
        limit_req zone=login burst=2 nodelay;
        limit_req_status 429;
    }

    # Search rate limit with delay
    location /search {
        limit_req zone=search burst=5 delay=3;
    }
}
```

**Parameters**:
- `zone`: Rate limit zone
- `burst`: Allow burst of requests beyond rate
- `nodelay`: Process burst immediately (no delay)
- `delay`: Start delaying after N requests in burst
- `limit_req_status`: HTTP status code for rejected requests

### IP Access Control

```nginx
# Method 1: allow/deny directives
location /admin/ {
    allow 192.168.1.0/24;
    allow 10.0.0.0/8;
    deny all;
}

# Method 2: geo module
geo $allowed_ip {
    default 0;
    192.168.1.0/24 1;
    10.0.0.0/8 1;
    172.16.0.0/12 1;
}

server {
    location /admin/ {
        if ($allowed_ip = 0) {
            return 403;
        }
        proxy_pass http://admin_backend;
    }
}

# Method 3: map module with real_ip
map $remote_addr $admin_allowed {
    default 0;
    ~^192\.168\. 1;
    ~^10\. 1;
}

location /admin/ {
    if ($admin_allowed = 0) {
        return 403;
    }
}
```

### Basic Authentication

```nginx
location /admin/ {
    auth_basic "Admin Area";
    auth_basic_user_file /etc/nginx/.htpasswd;
}

# Create password file:
# htpasswd -c /etc/nginx/.htpasswd username
```

### Request Filtering

```nginx
# Block by User-Agent
map $http_user_agent $block_ua {
    default 0;
    ~*bot 1;
    ~*crawler 1;
    ~*spider 1;
}

server {
    if ($block_ua) {
        return 403;
    }
}

# Block by Referer
map $http_referer $block_referer {
    default 0;
    ~*spam\.com 1;
    ~*malicious\.com 1;
}

server {
    if ($block_referer) {
        return 403;
    }
}

# Block requests without Host header
if ($host = "") {
    return 444;  # Connection closed without response
}
```

### Request Size Limits

```nginx
server {
    # Request body size
    client_max_body_size 10m;

    # Request header size
    client_header_buffer_size 1k;
    large_client_header_buffers 4 16k;

    # Rate limiting
    limit_rate 1m;  # Limit download speed to 1MB/s
    limit_rate_after 10m;  # Apply limit after 10MB downloaded
}
```

### DDoS Protection

```nginx
http {
    # Connection limits
    limit_conn_zone $binary_remote_addr zone=addr:10m;
    limit_conn_zone $server_name zone=perserver:10m;

    # Request rate limits
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;

    # Timeout configurations
    client_body_timeout 10s;
    client_header_timeout 10s;
    keepalive_timeout 15s;
    send_timeout 10s;
}

server {
    # Connection limits
    limit_conn addr 10;  # Max 10 connections per IP
    limit_conn perserver 1000;  # Max 1000 connections to server

    # Request rate limit
    limit_req zone=general burst=20 nodelay;

    # Slow request protection
    client_body_timeout 10s;
    client_header_timeout 10s;
}
```

---

## Performance Optimization

### Worker Process Tuning

```nginx
# Main context
user nginx;
worker_processes auto;  # Match CPU cores
worker_rlimit_nofile 65535;
pid /var/run/nginx.pid;

events {
    worker_connections 4096;  # Max connections per worker
    use epoll;  # Linux
    multi_accept on;
}
```

**Calculate max clients**:
```
reverse proxy: max_clients = worker_processes × worker_connections / 2
web server: max_clients = worker_processes × worker_connections
```

### Connection Optimization

```nginx
http {
    # Sendfile and TCP optimization
    sendfile on;
    tcp_nopush on;  # Send headers and file in one packet
    tcp_nodelay on;  # Disable Nagle algorithm

    # Keepalive
    keepalive_timeout 65;
    keepalive_requests 100;

    # Client timeouts
    client_body_timeout 12s;
    client_header_timeout 12s;
    send_timeout 10s;

    # Reset lingering connections
    reset_timedout_connection on;
}
```

### Buffer Optimization

```nginx
http {
    # Client buffers
    client_body_buffer_size 16k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 16k;
    client_max_body_size 10m;

    # Output buffers
    output_buffers 2 32k;
    postpone_output 1460;
}

location / {
    proxy_pass http://backend;

    # Proxy buffers
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    proxy_busy_buffers_size 16k;
}
```

### Compression

```nginx
http {
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 1000;
    gzip_disable "msie6";

    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/rss+xml
        font/truetype
        font/opentype
        application/vnd.ms-fontobject
        image/svg+xml;

    # Pre-compressed files
    gzip_static on;
}
```

### Static File Optimization

```nginx
location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
    root /var/www/static;

    # Cache headers
    expires 1y;
    add_header Cache-Control "public, immutable";

    # Disable logging
    access_log off;

    # Pre-compressed files
    gzip_static on;

    # Open file cache
    open_file_cache max=10000 inactive=30s;
    open_file_cache_valid 60s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
}
```

### Open File Cache

```nginx
http {
    open_file_cache max=10000 inactive=30s;
    open_file_cache_valid 60s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
}
```

**Parameters**:
- `max`: Maximum cached entries
- `inactive`: Remove entry if not accessed for this time
- `valid`: Revalidate entry after this time
- `min_uses`: Minimum accesses before caching
- `errors`: Cache file lookup errors

### DNS Resolver

```nginx
# For dynamic proxy_pass
location / {
    set $backend "backend.internal";
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
    proxy_pass http://$backend;
}
```

---

## Variables Reference

### Request Variables

```nginx
$request_method          # GET, POST, etc.
$request_uri             # Full URI with query string
$uri                     # URI without query string
$document_uri            # Same as $uri
$args                    # Query string
$arg_name                # Query parameter "name"
$query_string            # Same as $args
$is_args                 # "?" if has query string, else ""

$request                 # Full request line
$request_length          # Request length (headers + body)
$request_time            # Request processing time
$request_body            # Request body
$request_body_file       # Request body temp file
```

### Connection Variables

```nginx
$remote_addr             # Client IP
$remote_port             # Client port
$remote_user             # HTTP basic auth username
$binary_remote_addr      # Binary form of $remote_addr (for rate limiting)

$server_addr             # Server IP
$server_port             # Server port
$server_name             # Server name from server_name directive
$server_protocol         # HTTP/1.0, HTTP/1.1, HTTP/2.0

$connection              # Connection serial number
$connection_requests     # Number of requests in connection
$pipe                    # "p" if pipelined, else "."
```

### Request Headers

```nginx
$http_host               # Host header
$http_user_agent         # User-Agent header
$http_referer            # Referer header
$http_cookie             # Cookie header
$http_x_forwarded_for    # X-Forwarded-For header
$http_name               # Any header (lowercase, dashes to underscores)

$cookie_name             # Cookie "name"
$sent_http_name          # Response header "name"
```

### Response Variables

```nginx
$status                  # Response status code
$body_bytes_sent         # Response body size
$bytes_sent              # Total bytes sent
$sent_http_content_type  # Content-Type response header
$sent_http_location      # Location response header
```

### Upstream Variables

```nginx
$upstream_addr           # Backend server address
$upstream_status         # Backend response status
$upstream_response_time  # Backend response time
$upstream_connect_time   # Backend connection time
$upstream_header_time    # Backend header time
$upstream_cache_status   # Cache status (MISS, HIT, etc.)
```

### SSL Variables

```nginx
$ssl_protocol            # SSL protocol (TLSv1.2, TLSv1.3)
$ssl_cipher              # SSL cipher
$ssl_server_name         # SNI hostname
$ssl_client_cert         # Client certificate
$ssl_client_verify       # Client cert verification result
$ssl_session_id          # SSL session ID
$ssl_session_reused      # "r" if reused, else "."
```

### Time Variables

```nginx
$time_local              # Local time (Common Log Format)
$time_iso8601            # ISO 8601 format
$msec                    # Unix timestamp with milliseconds
```

### Nginx Variables

```nginx
$nginx_version           # Nginx version
$pid                     # Worker process PID
$hostname                # Hostname
$realpath_root           # Real path to document root
$request_id              # Unique request ID
$scheme                  # http or https
```

### Custom Variables with map

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

map $status $loggable {
    ~^[23] 0;  # Don't log 2xx and 3xx
    default 1;
}

map $request_uri $redirect_uri {
    /old-page /new-page;
    /old-api  /new-api;
    default   "";
}
```

---

## Module System

### Core Modules (always available)

- **ngx_http_core_module**: Core HTTP functionality
- **ngx_http_log_module**: Access logging
- **ngx_http_proxy_module**: Proxy functionality
- **ngx_http_upstream_module**: Load balancing
- **ngx_http_rewrite_module**: URL rewriting
- **ngx_http_access_module**: IP-based access control
- **ngx_http_limit_req_module**: Request rate limiting
- **ngx_http_limit_conn_module**: Connection limiting
- **ngx_http_ssl_module**: SSL/TLS support

### Common Optional Modules

#### ngx_http_realip_module

Get real client IP behind proxy.

```nginx
# Compile: --with-http_realip_module

server {
    # Trust CloudFlare IPs
    set_real_ip_from 103.21.244.0/22;
    set_real_ip_from 103.22.200.0/22;

    # Header containing real IP
    real_ip_header X-Forwarded-For;
    real_ip_recursive on;
}
```

#### ngx_http_geoip_module

Geographic location based on IP.

```nginx
# Compile: --with-http_geoip_module

http {
    geoip_country /usr/share/GeoIP/GeoIP.dat;
    geoip_city /usr/share/GeoIP/GeoLiteCity.dat;
}

server {
    location / {
        if ($geoip_country_code != US) {
            return 403;
        }
    }
}
```

#### ngx_http_stub_status_module

Basic status information.

```nginx
# Compile: --with-http_stub_status_module

location /nginx_status {
    stub_status;
    allow 127.0.0.1;
    deny all;
}

# Output:
# Active connections: 291
# server accepts handled requests
#  16630948 16630948 31070465
# Reading: 6 Writing: 179 Waiting: 106
```

#### ngx_http_auth_request_module

External authentication.

```nginx
# Compile: --with-http_auth_request_module

location /protected/ {
    auth_request /auth;
    proxy_pass http://backend;
}

location = /auth {
    internal;
    proxy_pass http://auth_backend;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
}
```

### Third-Party Modules

#### headers-more-nginx-module

More control over headers.

```nginx
# Set headers
more_set_headers 'Server: Custom';
more_set_headers 'X-Powered-By: ';

# Clear headers
more_clear_headers 'Server';
more_clear_headers 'X-Powered-By';
```

#### ngx_cache_purge

Cache purging functionality.

```nginx
location ~ /purge(/.*) {
    allow 127.0.0.1;
    deny all;
    proxy_cache_purge api_cache "$scheme$request_method$host$1";
}
```

#### lua-nginx-module

Lua scripting in Nginx.

```nginx
location /lua {
    content_by_lua_block {
        ngx.say("Hello from Lua!")
    }
}
```

---

## Best Practices

### Configuration Organization

```
/etc/nginx/
├── nginx.conf                   # Main configuration
├── mime.types                   # MIME types
├── conf.d/                      # Additional HTTP configs
│   ├── upstream.conf
│   ├── cache.conf
│   └── security.conf
├── sites-available/             # Virtual host configs
│   ├── example.com.conf
│   └── api.example.com.conf
├── sites-enabled/               # Enabled virtual hosts (symlinks)
│   ├── example.com.conf -> ../sites-available/example.com.conf
│   └── api.example.com.conf -> ../sites-available/api.example.com.conf
├── snippets/                    # Reusable config snippets
│   ├── ssl-params.conf
│   ├── proxy-params.conf
│   └── security-headers.conf
└── modules-enabled/             # Enabled dynamic modules
```

### Reusable Snippets

**snippets/ssl-params.conf**:
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_session_tickets off;
ssl_stapling on;
ssl_stapling_verify on;
```

**snippets/proxy-params.conf**:
```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_connect_timeout 5s;
proxy_send_timeout 10s;
proxy_read_timeout 30s;
```

**snippets/security-headers.conf**:
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
```

**Usage**:
```nginx
server {
    listen 443 ssl http2;

    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    include snippets/ssl-params.conf;
    include snippets/security-headers.conf;

    location / {
        include snippets/proxy-params.conf;
        proxy_pass http://backend;
    }
}
```

### Testing Configuration

```bash
# Test configuration syntax
nginx -t

# Test and dump configuration
nginx -T

# Reload configuration (graceful)
nginx -s reload

# Restart nginx
systemctl restart nginx
```

### Logging Best Practices

```nginx
# Structured JSON logging
log_format json_combined escape=json '{'
    '"time_local":"$time_local",'
    '"remote_addr":"$remote_addr",'
    '"remote_user":"$remote_user",'
    '"request":"$request",'
    '"status": "$status",'
    '"body_bytes_sent":"$body_bytes_sent",'
    '"request_time":$request_time,'
    '"http_referer":"$http_referer",'
    '"http_user_agent":"$http_user_agent"'
'}';

# Don't log health checks
map $request_uri $loggable {
    /health 0;
    /metrics 0;
    default 1;
}

access_log /var/log/nginx/access.log json_combined if=$loggable;

# Buffered logging (performance)
access_log /var/log/nginx/access.log main buffer=32k flush=1m;
```

---

## Anti-Patterns

### ❌ Using if for String Comparison

```nginx
# ❌ Bad: if is evil
if ($request_uri = /old-page) {
    return 301 /new-page;
}

# ✅ Good: Use location or map
location = /old-page {
    return 301 /new-page;
}
```

### ❌ Using if with Proxy

```nginx
# ❌ Bad: Can cause unexpected behavior
location / {
    if ($host != "example.com") {
        proxy_pass http://backend;
    }
}

# ✅ Good: Use separate server blocks
server {
    server_name example.com;
    location / {
        proxy_pass http://backend;
    }
}
```

### ❌ root in location with proxy_pass

```nginx
# ❌ Bad: root ignored with proxy_pass
location /api/ {
    root /var/www;  # Ignored!
    proxy_pass http://backend;
}

# ✅ Good: Remove unnecessary root
location /api/ {
    proxy_pass http://backend;
}
```

### ❌ Inefficient Regex

```nginx
# ❌ Bad: Regex for simple prefix
location ~ ^/api/ {
    proxy_pass http://backend;
}

# ✅ Good: Use prefix match
location /api/ {
    proxy_pass http://backend;
}
```

### ❌ Missing Trailing Slash with alias

```nginx
# ❌ Bad: Missing slash causes issues
location /static {
    alias /var/www/assets/;
}

# ✅ Good: Match slashes
location /static/ {
    alias /var/www/assets/;
}
```

### ❌ Hardcoded Backend in proxy_pass

```nginx
# ❌ Bad: No load balancing, failover
location / {
    proxy_pass http://127.0.0.1:8080;
}

# ✅ Good: Use upstream
upstream backend {
    server backend1:8080;
    server backend2:8080;
}

location / {
    proxy_pass http://backend;
}
```

### ❌ No SSL Session Cache

```nginx
# ❌ Bad: No session reuse
server {
    listen 443 ssl;
    ssl_certificate cert.crt;
    ssl_certificate_key cert.key;
}

# ✅ Good: Enable session cache
http {
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
}
```

### ❌ Blocking Operations in Worker

```nginx
# ❌ Bad: Synchronous DNS lookup blocks worker
location / {
    set $backend "backend.example.com";
    proxy_pass http://$backend;
}

# ✅ Good: Use resolver for async lookup
location / {
    set $backend "backend.example.com";
    resolver 8.8.8.8;
    proxy_pass http://$backend;
}
```

---

## Troubleshooting

### Common Issues

#### Issue 1: 502 Bad Gateway

**Symptoms**: Nginx cannot connect to backend

**Debug**:
```bash
# Check error log
tail -f /var/log/nginx/error.log

# Test backend connectivity
curl http://backend:8080/

# Check SELinux (if enabled)
getsebool httpd_can_network_connect
```

**Solutions**:
```nginx
# Increase timeouts
proxy_connect_timeout 10s;
proxy_read_timeout 60s;

# Add backup server
upstream backend {
    server backend1:8080;
    server backup:8080 backup;
}

# Enable SELinux permission
# setsebool -P httpd_can_network_connect 1
```

#### Issue 2: 413 Request Entity Too Large

**Symptoms**: Upload fails with 413

**Solution**:
```nginx
http {
    client_max_body_size 50m;
}

# Or per location
location /upload/ {
    client_max_body_size 100m;
}
```

#### Issue 3: Configuration Test Fails

**Debug**:
```bash
# Test configuration
nginx -t

# Detailed test
nginx -T

# Check for common issues:
# - Missing semicolons
# - Wrong directive context
# - Invalid regex
# - Duplicate listen directives
```

#### Issue 4: WebSocket Connection Fails

**Solution**:
```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

location /ws/ {
    proxy_pass http://websocket_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_read_timeout 86400;
}
```

#### Issue 5: Cache Not Working

**Debug**:
```bash
# Check cache directory permissions
ls -la /var/cache/nginx/

# Check cache status header
curl -I http://example.com/api/users
# X-Cache-Status: MISS or HIT

# Monitor cache
tail -f /var/log/nginx/access.log | grep "X-Cache-Status"
```

**Solutions**:
```nginx
# Ensure cache key is correct
proxy_cache_key "$scheme$request_method$host$request_uri";

# Check cache bypass conditions
# Remove: proxy_cache_bypass $http_cache_control;

# Verify cache validity
proxy_cache_valid 200 10m;

# Check cache methods
proxy_cache_methods GET HEAD;
```

### Debugging Tools

**ngxtop** - Real-time request statistics:
```bash
pip install ngxtop

# Top requests
ngxtop

# Top IPs
ngxtop --group-by remote_addr

# Specific log format
ngxtop -l /var/log/nginx/access.log -f combined
```

**nginx-amplify** - Nginx monitoring:
```bash
# Official Nginx monitoring (free)
# https://amplify.nginx.com/
```

**Analyze Logs**:
```bash
# Top 10 IPs
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10

# Top 10 requested URLs
awk '{print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10

# Response status counts
awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# Average response time
awk '{print $NF}' /var/log/nginx/access.log | awk '{sum+=$1; count++} END {print sum/count}'
```

---

## Real-World Configurations

### Configuration 1: High-Performance Web Server

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

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" rt=$request_time';

    access_log /var/log/nginx/access.log main buffer=32k flush=1m;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 100;
    reset_timedout_connection on;

    # Buffers
    client_body_buffer_size 16k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 16k;
    client_max_body_size 10m;

    # Compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss;

    # Security
    server_tokens off;

    # File cache
    open_file_cache max=10000 inactive=30s;
    open_file_cache_valid 60s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
```

### Configuration 2: API Gateway with Caching

```nginx
http {
    # Upstream backends
    upstream api_v1 {
        least_conn;
        server api1.internal:8080 max_fails=3 fail_timeout=30s;
        server api2.internal:8080 max_fails=3 fail_timeout=30s;
        server api3.internal:8080 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    # Cache configuration
    proxy_cache_path /var/cache/nginx/api
        levels=1:2
        keys_zone=api_cache:100m
        max_size=10g
        inactive=60m
        use_temp_path=off;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

    server {
        listen 443 ssl http2;
        server_name api.example.com;

        # SSL
        ssl_certificate /etc/ssl/certs/api.example.com.crt;
        ssl_certificate_key /etc/ssl/private/api.example.com.key;
        include snippets/ssl-params.conf;

        # Security headers
        include snippets/security-headers.conf;

        # Logging
        access_log /var/log/nginx/api.access.log main;
        error_log /var/log/nginx/api.error.log;

        # API endpoints
        location /api/v1/ {
            limit_req zone=api burst=50 nodelay;

            proxy_pass http://api_v1/;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            include snippets/proxy-params.conf;

            # Caching
            proxy_cache api_cache;
            proxy_cache_key "$scheme$request_method$host$request_uri";
            proxy_cache_valid 200 10m;
            proxy_cache_valid 404 1m;
            proxy_cache_use_stale error timeout updating http_500 http_502 http_503;
            proxy_cache_background_update on;
            proxy_cache_lock on;

            add_header X-Cache-Status $upstream_cache_status;
        }

        # Health check
        location /health {
            access_log off;
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }
    }
}
```

### Configuration 3: Microservices Routing

```nginx
http {
    # Service upstreams
    upstream auth_service {
        server auth1.internal:8080;
        server auth2.internal:8080;
        keepalive 16;
    }

    upstream user_service {
        server user1.internal:8080;
        server user2.internal:8080;
        keepalive 16;
    }

    upstream order_service {
        server order1.internal:8080;
        server order2.internal:8080;
        keepalive 16;
    }

    server {
        listen 443 ssl http2;
        server_name gateway.example.com;

        # SSL configuration
        ssl_certificate /etc/ssl/certs/gateway.crt;
        ssl_certificate_key /etc/ssl/private/gateway.key;

        # Auth service
        location /auth/ {
            proxy_pass http://auth_service/;
            include snippets/proxy-params.conf;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }

        # User service
        location /users/ {
            proxy_pass http://user_service/;
            include snippets/proxy-params.conf;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }

        # Order service
        location /orders/ {
            proxy_pass http://order_service/;
            include snippets/proxy-params.conf;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }
    }
}
```

---

## RFC References

### HTTP RFCs

- **RFC 7230**: HTTP/1.1 Message Syntax and Routing
- **RFC 7231**: HTTP/1.1 Semantics and Content
- **RFC 7232**: HTTP/1.1 Conditional Requests
- **RFC 7233**: HTTP/1.1 Range Requests
- **RFC 7234**: HTTP/1.1 Caching
- **RFC 7235**: HTTP/1.1 Authentication
- **RFC 7540**: HTTP/2
- **RFC 9113**: HTTP/2 (obsoletes 7540)

### TLS RFCs

- **RFC 8446**: TLS 1.3
- **RFC 5246**: TLS 1.2
- **RFC 6066**: TLS Extensions (SNI, OCSP Stapling)
- **RFC 7525**: Recommendations for Secure Use of TLS

### Other Relevant RFCs

- **RFC 3986**: URI Generic Syntax
- **RFC 6585**: Additional HTTP Status Codes (429 Too Many Requests)
- **RFC 7239**: Forwarded HTTP Extension
- **RFC 6797**: HTTP Strict Transport Security (HSTS)

### Nginx Documentation

- Official: https://nginx.org/en/docs/
- Nginx Plus: https://docs.nginx.com/
- Nginx Blog: https://www.nginx.com/blog/

---

**Last Updated**: 2025-10-27
**Version**: 1.0
**Lines**: 2900+
