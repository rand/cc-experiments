---
name: proxies-forward-proxy
description: Forward proxy fundamentals including HTTP CONNECT, SOCKS protocols, authentication, and use cases for privacy, security, and access control
---

# Forward Proxy

**Scope**: Forward proxy concepts, HTTP CONNECT method, SOCKS protocol, use cases
**Lines**: ~350
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Implementing client-side proxy functionality
- Building corporate network access control
- Adding privacy/anonymity layers
- Debugging proxy connection issues
- Configuring applications to use proxies
- Implementing HTTP CONNECT tunneling
- Working with SOCKS4/SOCKS5 protocols
- Setting up proxy authentication

## Core Concepts

### Forward Proxy vs Reverse Proxy

**Forward Proxy** (this skill):
```
Client → Forward Proxy → Internet → Server
         [client's agent]
```
- Acts on behalf of clients
- Clients explicitly configure proxy
- Used for: access control, caching, anonymity
- Examples: Corporate proxies, Squid, proxy.py

**Reverse Proxy** (see `proxies-reverse-proxy`):
```
Client → Internet → Reverse Proxy → Backend Servers
                    [server's agent]
```
- Acts on behalf of servers
- Clients unaware of proxy
- Used for: load balancing, SSL termination, caching

### HTTP CONNECT Method

**Purpose**: Tunnel TCP connections through HTTP proxy

```http
CONNECT example.com:443 HTTP/1.1
Host: example.com:443
Proxy-Authorization: Basic dXNlcjpwYXNz

HTTP/1.1 200 Connection Established

[TLS handshake begins]
[Encrypted data flows]
```

**Use Cases**:
- HTTPS through HTTP proxy
- WebSocket connections
- SSH tunneling
- Any TCP-based protocol

### SOCKS Protocol

**SOCKS4** (older, IPv4 only):
```
1. Client → SOCKS: Connect request
2. SOCKS → Server: TCP connection
3. SOCKS → Client: Success/Failure
4. Data flows transparently
```

**SOCKS5** (modern, recommended):
- IPv6 support
- UDP support
- Authentication methods
- DNS resolution at proxy

---

## Patterns

### Pattern 1: HTTP Proxy with Authentication

**Use Case**: Corporate proxy requiring credentials

```python
# ❌ Bad: Credentials in URL
import requests

response = requests.get(
    'http://api.example.com/data',
    proxies={
        'http': 'http://user:pass@proxy.corp.com:8080',
        'https': 'http://user:pass@proxy.corp.com:8080'
    }
)
```

```python
# ✅ Good: Secure credential handling
import requests
import os

proxies = {
    'http': f'http://{os.environ["PROXY_HOST"]}:{os.environ["PROXY_PORT"]}',
    'https': f'http://{os.environ["PROXY_HOST"]}:{os.environ["PROXY_PORT"]}'
}

auth = (os.environ['PROXY_USER'], os.environ['PROXY_PASS'])

response = requests.get(
    'http://api.example.com/data',
    proxies=proxies,
    auth=auth
)
```

**Benefits**:
- Credentials not in code/version control
- Centralized credential management
- Easier credential rotation

### Pattern 2: SOCKS5 with DNS Resolution

**Use Case**: Route all traffic through SOCKS proxy

```python
# ❌ Bad: DNS leaks
import requests

proxies = {
    'http': 'socks5://localhost:1080',
    'https': 'socks5://localhost:1080'
}

response = requests.get('http://api.example.com/data', proxies=proxies)
# DNS resolution happens locally, leaking information
```

```python
# ✅ Good: DNS through SOCKS proxy
import requests

proxies = {
    'http': 'socks5h://localhost:1080',  # 'h' = DNS through proxy
    'https': 'socks5h://localhost:1080'
}

response = requests.get('http://api.example.com/data', proxies=proxies)
```

**Benefits**:
- No DNS leaks
- True anonymity
- Bypass DNS-based blocks

---

## Implementation Examples

### Python HTTP Forward Proxy Server

```python
import socket
import threading
from typing import Tuple

class ForwardProxy:
    def __init__(self, host: str = '0.0.0.0', port: int = 8888):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen(100)
        print(f"[*] Proxy listening on {self.host}:{self.port}")

        while True:
            client_socket, addr = self.server.accept()
            print(f"[*] Connection from {addr}")
            thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            thread.daemon = True
            thread.start()

    def handle_client(self, client_socket: socket.socket):
        try:
            request = client_socket.recv(4096)

            # Parse request line
            first_line = request.split(b'\r\n')[0]
            method, url, version = first_line.split(b' ')

            if method == b'CONNECT':
                self.handle_connect(client_socket, url)
            else:
                self.handle_http(client_socket, request, url)
        except Exception as e:
            print(f"[!] Error: {e}")
        finally:
            client_socket.close()

    def handle_connect(self, client_socket: socket.socket, url: bytes):
        """Handle HTTPS CONNECT tunnel"""
        host, port = url.decode().split(':')

        try:
            # Connect to target
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.connect((host, int(port)))

            # Send success response
            client_socket.send(b'HTTP/1.1 200 Connection Established\r\n\r\n')

            # Bidirectional forwarding
            client_socket.setblocking(False)
            remote.setblocking(False)

            while True:
                # Client → Server
                try:
                    data = client_socket.recv(4096)
                    if data:
                        remote.sendall(data)
                except BlockingIOError:
                    pass

                # Server → Client
                try:
                    data = remote.recv(4096)
                    if data:
                        client_socket.sendall(data)
                except BlockingIOError:
                    pass
        except Exception as e:
            print(f"[!] CONNECT error: {e}")
            client_socket.send(b'HTTP/1.1 502 Bad Gateway\r\n\r\n')

    def handle_http(self, client_socket: socket.socket, request: bytes, url: bytes):
        """Handle plain HTTP requests"""
        try:
            # Extract host and path
            host_line = [l for l in request.split(b'\r\n') if l.startswith(b'Host:')][0]
            host = host_line.split(b': ')[1].decode()

            # Connect to target
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.connect((host, 80))

            # Forward request
            remote.sendall(request)

            # Forward response
            while True:
                data = remote.recv(4096)
                if not data:
                    break
                client_socket.sendall(data)

            remote.close()
        except Exception as e:
            print(f"[!] HTTP error: {e}")

if __name__ == '__main__':
    proxy = ForwardProxy(port=8888)
    proxy.start()
```

### Go SOCKS5 Proxy Client

```go
package main

import (
    "fmt"
    "golang.org/x/net/proxy"
    "io"
    "net"
    "net/http"
    "time"
)

func main() {
    // Create SOCKS5 dialer
    dialer, err := proxy.SOCKS5("tcp", "localhost:1080",
        &proxy.Auth{
            User:     "username",
            Password: "password",
        },
        proxy.Direct,
    )
    if err != nil {
        panic(err)
    }

    // Use SOCKS5 for HTTP client
    httpTransport := &http.Transport{
        Dial: dialer.Dial,
    }

    httpClient := &http.Client{
        Transport: httpTransport,
        Timeout:   10 * time.Second,
    }

    // Make request through SOCKS5
    resp, err := httpClient.Get("https://api.example.com/data")
    if err != nil {
        panic(err)
    }
    defer resp.Body.Close()

    body, _ := io.ReadAll(resp.Body)
    fmt.Printf("Response: %s\n", body)
}

// Direct TCP connection through SOCKS5
func tcpThroughSocks5() {
    dialer, _ := proxy.SOCKS5("tcp", "localhost:1080", nil, proxy.Direct)

    conn, err := dialer.Dial("tcp", "example.com:80")
    if err != nil {
        panic(err)
    }
    defer conn.Close()

    // Use connection
    conn.Write([]byte("GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"))

    buffer := make([]byte, 4096)
    n, _ := conn.Read(buffer)
    fmt.Printf("Response: %s\n", buffer[:n])
}
```

### JavaScript/TypeScript Proxy Configuration

```typescript
// Node.js HTTP request through proxy
import https from 'https';
import { HttpsProxyAgent } from 'https-proxy-agent';

const proxyAgent = new HttpsProxyAgent({
  host: 'proxy.example.com',
  port: 8080,
  auth: 'user:password'
});

const options = {
  hostname: 'api.example.com',
  path: '/data',
  method: 'GET',
  agent: proxyAgent
};

const req = https.request(options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log('Response:', data);
  });
});

req.on('error', (error) => {
  console.error('Error:', error);
});

req.end();
```

```typescript
// Axios with proxy
import axios from 'axios';

const response = await axios.get('https://api.example.com/data', {
  proxy: {
    protocol: 'http',
    host: 'proxy.example.com',
    port: 8080,
    auth: {
      username: process.env.PROXY_USER!,
      password: process.env.PROXY_PASS!
    }
  }
});

console.log(response.data);
```

---

## Configuration Examples

### System-Wide Proxy (Linux/macOS)

```bash
# Environment variables
export http_proxy="http://proxy.example.com:8080"
export https_proxy="http://proxy.example.com:8080"
export no_proxy="localhost,127.0.0.1,*.local"

# With authentication
export http_proxy="http://user:pass@proxy.example.com:8080"
export https_proxy="http://user:pass@proxy.example.com:8080"

# SOCKS5
export ALL_PROXY="socks5://localhost:1080"
```

### Git Through Proxy

```bash
# HTTP proxy
git config --global http.proxy http://proxy.example.com:8080
git config --global https.proxy http://proxy.example.com:8080

# SOCKS5
git config --global http.proxy socks5://localhost:1080
git config --global https.proxy socks5://localhost:1080

# Unset proxy
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### Docker Through Proxy

```json
// ~/.docker/config.json
{
  "proxies": {
    "default": {
      "httpProxy": "http://proxy.example.com:8080",
      "httpsProxy": "http://proxy.example.com:8080",
      "noProxy": "localhost,127.0.0.1"
    }
  }
}
```

---

## Best Practices

### 1. Handle Proxy Errors Gracefully

```python
# ✅ Good: Fallback and retry logic
import requests
from requests.exceptions import ProxyError, Timeout

def fetch_with_proxy(url: str, proxies: dict, retries: int = 3):
    for attempt in range(retries):
        try:
            response = requests.get(url, proxies=proxies, timeout=10)
            return response
        except ProxyError:
            print(f"Proxy error, attempt {attempt + 1}/{retries}")
            if attempt == retries - 1:
                # Fallback to direct connection
                return requests.get(url, timeout=10)
        except Timeout:
            print(f"Timeout, attempt {attempt + 1}/{retries}")

    raise Exception("Failed after all retries")
```

### 2. Use Proxy Auto-Config (PAC)

```javascript
// PAC file for smart proxy routing
function FindProxyForURL(url, host) {
  // Direct for local addresses
  if (isPlainHostName(host) ||
      shExpMatch(host, "*.local") ||
      isInNet(host, "10.0.0.0", "255.0.0.0") ||
      isInNet(host, "172.16.0.0", "255.240.0.0") ||
      isInNet(host, "192.168.0.0", "255.255.0.0")) {
    return "DIRECT";
  }

  // Use proxy for everything else
  return "PROXY proxy.example.com:8080; DIRECT";
}
```

### 3. Validate Proxy Health

```python
# ✅ Good: Health check before use
import requests

def is_proxy_healthy(proxy_url: str) -> bool:
    try:
        response = requests.get(
            'http://httpbin.org/ip',
            proxies={'http': proxy_url, 'https': proxy_url},
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

proxy = "http://proxy.example.com:8080"
if is_proxy_healthy(proxy):
    # Use proxy
    pass
else:
    # Use alternative or direct
    pass
```

---

## Troubleshooting

### Issue 1: Proxy Authentication Failures

**Symptoms**: 407 Proxy Authentication Required
**Common Causes**:
- Wrong credentials
- Expired credentials
- Special characters in password not URL-encoded

**Solution**:
```python
from urllib.parse import quote

username = "user@domain"  # Example - use actual credentials from environment
password = "p@ss:word"  # Example - use actual credentials from environment

proxy = f"http://{quote(username)}:{quote(password)}@proxy.example.com:8080"
```

### Issue 2: SSL/TLS Errors Through Proxy

**Symptoms**: Certificate verification failures
**Common Causes**:
- Proxy doing SSL inspection
- Missing intermediate certificates

**Solution**:
```python
# Add proxy's CA certificate
import requests

response = requests.get(
    'https://api.example.com/data',
    proxies={'https': 'http://proxy.example.com:8080'},
    verify='/path/to/proxy-ca-bundle.crt'
)
```

### Issue 3: Slow Proxy Connections

**Symptoms**: High latency through proxy
**Common Causes**:
- Proxy overloaded
- No connection pooling
- DNS resolution delays

**Solution**:
```python
# Use connection pooling
import requests
from requests.adapters import HTTPAdapter

session = requests.Session()
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
session.mount('http://', adapter)
session.mount('https://', adapter)

session.proxies = {
    'http': 'http://proxy.example.com:8080',
    'https': 'http://proxy.example.com:8080'
}

# Reuse session for multiple requests
for url in urls:
    response = session.get(url)
```

---

## Related Skills

- `proxies-reverse-proxy` - Reverse proxy patterns and use cases
- `proxies-nginx-configuration` - Nginx as forward/reverse proxy
- `protocols-http-fundamentals` - HTTP protocol basics
- `networking-tls-troubleshooting` - SSL/TLS debugging
- `containers-docker-networking` - Container proxy configuration

---

**Last Updated**: 2025-10-27
