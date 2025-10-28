---
name: protocols-http2-multiplexing
description: HTTP/2 protocol with multiplexing, server push, header compression, and stream prioritization
---

# HTTP/2 Multiplexing

**Scope**: HTTP/2 binary protocol, multiplexing, server push, header compression (HPACK)
**Lines**: ~360
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Optimizing website performance with HTTP/2
- Implementing HTTP/2 servers or clients
- Debugging HTTP/2 connection issues
- Understanding multiplexing and streams
- Configuring server push
- Reducing header overhead with HPACK
- Migrating from HTTP/1.1 to HTTP/2
- Troubleshooting stream prioritization

## Core Concepts

### HTTP/2 vs HTTP/1.1

**HTTP/1.1 Issues**:
- Head-of-line blocking (one request at a time per connection)
- Multiple connections needed for parallel requests
- Redundant header data in every request
- No request prioritization

**HTTP/2 Solutions**:
- Binary framing layer
- Multiplexed streams (many requests over one connection)
- Header compression (HPACK)
- Server push
- Stream prioritization

**Connection Model**:
```
HTTP/1.1:          HTTP/2:
┌─────┐            ┌─────────────┐
│Req 1│───────────>│Stream 1 ────┤
└─────┘            │Stream 2 ────┤
┌─────┐            │Stream 3 ────┼──> Single TCP Connection
│Req 2│───────────>│Stream 4 ────┤
└─────┘            │Stream 5 ────┤
 (sequential)      └─────────────┘
                    (multiplexed)
```

### Binary Framing Layer

**Frame Types**:
- **DATA**: Carries request/response body
- **HEADERS**: Carries HTTP headers
- **PRIORITY**: Stream priority information
- **RST_STREAM**: Stream termination
- **SETTINGS**: Connection configuration
- **PUSH_PROMISE**: Server push notification
- **PING**: Connection liveness check
- **GOAWAY**: Graceful connection shutdown
- **WINDOW_UPDATE**: Flow control
- **CONTINUATION**: Continue header block

**Frame Structure**:
```
+-----------------------------------------------+
|                 Length (24)                   |
+---------------+---------------+---------------+
|   Type (8)    |   Flags (8)   |
+-+-------------+---------------+-------------------------------+
|R|                 Stream Identifier (31)                      |
+=+=============================================================+
|                   Frame Payload (0...)                      ...
+---------------------------------------------------------------+
```

### Multiplexing

**Single Connection, Multiple Streams**:
```python
# HTTP/1.1 - requires 6 connections
conn1.request('GET', '/style.css')
conn2.request('GET', '/script.js')
conn3.request('GET', '/image1.png')
conn4.request('GET', '/image2.png')
conn5.request('GET', '/image3.png')
conn6.request('GET', '/data.json')

# HTTP/2 - single connection
h2_conn = h2.connection.H2Connection()
h2_conn.send_headers(stream_id=1, headers=[(':path', '/style.css')])
h2_conn.send_headers(stream_id=3, headers=[(':path', '/script.js')])
h2_conn.send_headers(stream_id=5, headers=[(':path', '/image1.png')])
h2_conn.send_headers(stream_id=7, headers=[(':path', '/image2.png')])
h2_conn.send_headers(stream_id=9, headers=[(':path', '/image3.png')])
h2_conn.send_headers(stream_id=11, headers=[(':path', '/data.json')])
```

**Benefits**:
- No connection overhead
- Better connection utilization
- Reduced latency
- No TCP slow start penalty

### Server Push

**Concept**: Server proactively sends resources client will need

```
Client                              Server
  |                                    |
  |-- GET /index.html --------------->|
  |                                    |
  |<-- PUSH_PROMISE /style.css -------|
  |<-- PUSH_PROMISE /script.js -------|
  |                                    |
  |<-- HEADERS (index.html) -----------|
  |<-- DATA (index.html content) ------|
  |                                    |
  |<-- HEADERS (style.css) ------------|
  |<-- DATA (style.css content) -------|
  |                                    |
  |<-- HEADERS (script.js) ------------|
  |<-- DATA (script.js content) -------|
```

**Nginx Configuration**:
```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    location = /index.html {
        http2_push /css/style.css;
        http2_push /js/script.js;
        http2_push /images/logo.png;
    }
}
```

**Node.js Implementation**:
```javascript
const http2 = require('http2');
const fs = require('fs');

const server = http2.createSecureServer({
    key: fs.readFileSync('server-key.pem'),
    cert: fs.readFileSync('server-cert.pem')
});

server.on('stream', (stream, headers) => {
    if (headers[':path'] === '/') {
        // Push CSS before sending HTML
        stream.pushStream({ ':path': '/style.css' }, (err, pushStream) => {
            pushStream.respond({ ':status': 200, 'content-type': 'text/css' });
            pushStream.end(fs.readFileSync('style.css'));
        });

        // Send HTML
        stream.respond({ ':status': 200, 'content-type': 'text/html' });
        stream.end('<html><link rel="stylesheet" href="/style.css"></html>');
    }
});

server.listen(8443);
```

### Header Compression (HPACK)

**Problem**: HTTP/1.1 headers are redundant
```http
# Request 1
GET /api/users/1 HTTP/1.1
Host: api.example.com
User-Agent: Mozilla/5.0 ...
Accept: application/json
Authorization: Bearer token123

# Request 2 - same headers repeated!
GET /api/users/2 HTTP/1.1
Host: api.example.com
User-Agent: Mozilla/5.0 ...
Accept: application/json
Authorization: Bearer token123
```

**HPACK Solution**:
- Static table (common headers pre-indexed)
- Dynamic table (connection-specific compression)
- Huffman encoding

**Example Encoding**:
```
First request:
:method: GET             -> Index 2 (static table)
:path: /api/users/1      -> Literal, added to dynamic table (index 62)
host: api.example.com    -> Literal, added to dynamic table (index 63)
authorization: Bearer... -> Literal, added to dynamic table (index 64)

Second request:
:method: GET             -> Index 2
:path: /api/users/2      -> Literal (path changed)
host: api.example.com    -> Index 63 (dynamic table)
authorization: Bearer... -> Index 64 (dynamic table)
```

**Compression Ratio**: 85-95% size reduction typical

---

## Patterns

### Pattern 1: Prioritization

**Use Case**: Critical resources load first

```javascript
// Node.js HTTP/2 client
const http2 = require('http2');

const client = http2.connect('https://example.com');

// High priority - CSS (weight 256)
const cssStream = client.request({
    ':path': '/critical.css'
}, { weight: 256 });

// Medium priority - JavaScript (weight 128)
const jsStream = client.request({
    ':path': '/app.js'
}, { weight: 128 });

// Low priority - Images (weight 64)
const imgStream = client.request({
    ':path': '/background.jpg'
}, { weight: 64 });
```

**Benefits**:
- Critical resources load faster
- Better perceived performance
- Optimal resource utilization

### Pattern 2: Conditional Server Push

**Use Case**: Only push if client doesn't have cached resource

```javascript
server.on('stream', (stream, headers) => {
    const cookieHeader = headers['cookie'] || '';
    const hasCache = cookieHeader.includes('has_css=1');

    if (!hasCache) {
        // Push CSS only if client doesn't have it
        stream.pushStream({ ':path': '/style.css' }, (err, pushStream) => {
            pushStream.respond({
                ':status': 200,
                'content-type': 'text/css',
                'cache-control': 'public, max-age=31536000'
            });
            pushStream.end(cssContent);
        });

        // Set cookie to indicate client has CSS
        stream.respond({
            ':status': 200,
            'set-cookie': 'has_css=1; Max-Age=31536000'
        });
    }

    stream.end(htmlContent);
});
```

### Pattern 3: Flow Control

**Use Case**: Prevent overwhelming slow clients

```python
# Python HTTP/2 with flow control
import h2.connection
import h2.events

conn = h2.connection.H2Connection()
conn.initiate_connection()

# Set initial window size
conn.update_settings({
    h2.settings.SettingCodes.INITIAL_WINDOW_SIZE: 65535
})

# Send data respecting flow control
stream_id = 1
data = b"Large payload..."

while data:
    # Check how much we can send
    max_send = min(len(data), conn.local_settings.initial_window_size)

    # Send chunk
    conn.send_data(stream_id, data[:max_send])
    data = data[max_send:]

    # Wait for WINDOW_UPDATE if needed
    if len(data) > 0:
        events = conn.receive_data(socket.recv(4096))
        for event in events:
            if isinstance(event, h2.events.WindowUpdated):
                # Can send more data now
                pass
```

---

## Implementation Examples

### Go HTTP/2 Server

```go
package main

import (
    "fmt"
    "log"
    "net/http"
)

func main() {
    mux := http.NewServeMux()

    mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        // Check if HTTP/2
        if r.ProtoMajor == 2 {
            fmt.Printf("HTTP/2 request: %s\n", r.URL.Path)
        }

        // Server push
        if pusher, ok := w.(http.Pusher); ok {
            // Push CSS before HTML
            if err := pusher.Push("/style.css", nil); err != nil {
                log.Printf("Failed to push: %v", err)
            }
        }

        w.Header().Set("Content-Type", "text/html")
        w.Write([]byte("<html><link rel='stylesheet' href='/style.css'></html>"))
    })

    mux.HandleFunc("/style.css", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "text/css")
        w.Header().Set("Cache-Control", "public, max-age=31536000")
        w.Write([]byte("body { font-family: sans-serif; }"))
    })

    log.Fatal(http.ListenAndServeTLS(":8443", "cert.pem", "key.pem", mux))
}
```

### Rust HTTP/2 Client (hyper)

```rust
use hyper::{Body, Client, Request};
use hyper::client::HttpConnector;
use hyper_tls::HttpsConnector;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Create HTTP/2 client
    let https = HttpsConnector::new();
    let client = Client::builder()
        .http2_only(true)
        .build::<_, Body>(https);

    // Make multiple concurrent requests (multiplexed)
    let urls = vec![
        "https://example.com/api/users/1",
        "https://example.com/api/users/2",
        "https://example.com/api/users/3",
    ];

    let futures: Vec<_> = urls.into_iter()
        .map(|url| {
            let req = Request::get(url).body(Body::empty()).unwrap();
            client.request(req)
        })
        .collect();

    // All requests use same connection
    let responses = futures::future::join_all(futures).await;

    for response in responses {
        println!("Status: {}", response?.status());
    }

    Ok(())
}
```

---

## Best Practices

### 1. Enable HTTP/2 Everywhere

```nginx
# ✅ Good: Enable HTTP/2
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
}
```

### 2. Don't Over-Push

```javascript
// ❌ Bad: Pushing everything
stream.pushStream({ ':path': '/rarely-used-library.js' }, ...);

// ✅ Good: Only push critical resources
stream.pushStream({ ':path': '/critical.css' }, ...);
```

### 3. Use Connection Coalescing

```
# Same IP, same certificate -> reuse connection
https://example.com (IP: 1.2.3.4)
https://www.example.com (IP: 1.2.3.4)
https://api.example.com (IP: 1.2.3.4)
└─> All use same HTTP/2 connection
```

---

## Troubleshooting

### Issue 1: HTTP/2 Not Working

**Check Protocol**:
```bash
curl -I --http2 https://example.com
# Look for: HTTP/2 200

# Or
openssl s_client -connect example.com:443 -alpn h2
# Look for: ALPN protocol: h2
```

### Issue 2: Server Push Ignored

**Symptom**: Pushed resources not cached
**Solution**: Check browser support and cache headers

```javascript
// Ensure proper cache headers on pushed resources
pushStream.respond({
    ':status': 200,
    'cache-control': 'public, max-age=31536000',
    'content-type': 'text/css'
});
```

---

## Level 3 Resources

This skill includes executable scripts, reference documentation, and configuration examples in the `resources/` directory.

### Scripts (`resources/scripts/`)

**benchmark_http2.py**: Compare HTTP/1.1 and HTTP/2 performance
```bash
# Benchmark 50 requests
python resources/scripts/benchmark_http2.py --url https://example.com --requests 50

# JSON output
python resources/scripts/benchmark_http2.py --url https://example.com --json results.json
```

**analyze_hpack.py**: Analyze HPACK header compression efficiency
```bash
# Demo with sample requests
python resources/scripts/analyze_hpack.py --demo

# Analyze custom headers
python resources/scripts/analyze_hpack.py --requests headers.txt --verbose
```

**test_server_push.sh**: Test HTTP/2 server push functionality
```bash
# Test server push support
./resources/scripts/test_server_push.sh --url https://example.com

# Detailed analysis with nghttp
./resources/scripts/test_server_push.sh --url https://example.com --verbose
```

### Reference Documentation (`resources/REFERENCE.md`)

- RFC 7540: HTTP/2 protocol specification
- Binary framing layer details
- HPACK compression algorithm (RFC 7541)
- Flow control mechanisms
- Stream prioritization
- Performance benchmarks

### Configuration Examples (`resources/examples/`)

**Nginx** (`resources/examples/nginx/http2.conf`):
- Basic HTTP/2 setup
- Server push configuration
- Performance tuning
- Multiple domain coalescing

**Node.js** (`resources/examples/node/http2-server.js`):
- Server push implementation
- Stream prioritization
- Flow control
- API server example

**Python** (`resources/examples/python/http2_client.py`):
- HTTP/2 client with httpx
- Multiplexed concurrent requests
- Low-level h2 library usage
- API client with authentication

See `resources/scripts/README.md` for complete documentation.

---

## Related Skills

- `protocols-http-fundamentals` - HTTP/1.1 basics
- `protocols-http3-quic` - HTTP/3 and QUIC
- `proxies-nginx-configuration` - Nginx HTTP/2 setup
- `proxies-envoy-proxy` - Envoy HTTP/2 configuration
- `frontend-performance` - Front-end performance optimization

---

**Last Updated**: 2025-10-27
