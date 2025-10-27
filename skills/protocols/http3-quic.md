---
name: protocols-http3-quic
description: HTTP/3 and QUIC protocol with UDP transport, 0-RTT, connection migration, and improved performance
---

# HTTP/3 and QUIC Protocol

**Scope**: HTTP/3 over QUIC, UDP-based transport, 0-RTT connection establishment, connection migration
**Lines**: ~370
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Implementing modern high-performance web services
- Working with mobile applications (connection migration)
- Reducing latency for global users
- Building real-time applications
- Optimizing for unreliable networks
- Understanding QUIC protocol
- Migrating from HTTP/2 to HTTP/3
- Debugging QUIC connections

## Core Concepts

### HTTP/3 vs HTTP/2

**HTTP/2 Limitations (TCP-based)**:
- Head-of-line blocking at TCP level
- TCP handshake + TLS handshake (2 RTT)
- No connection migration (breaks on network change)
- TCP ossification (middle boxes)

**HTTP/3 Advantages (QUIC-based)**:
- No TCP head-of-line blocking
- 0-RTT or 1-RTT connection establishment
- Built-in encryption (always secure)
- Connection migration (seamless network switches)
- Improved congestion control

**Protocol Stack Comparison**:
```
HTTP/1.1          HTTP/2             HTTP/3
┌─────────┐      ┌─────────┐        ┌─────────┐
│ HTTP/1.1│      │ HTTP/2  │        │ HTTP/3  │
├─────────┤      ├─────────┤        ├─────────┤
│   TLS   │      │   TLS   │        │  QUIC   │
├─────────┤      ├─────────┤        ├─────────┤
│   TCP   │      │   TCP   │        │   UDP   │
├─────────┤      ├─────────┤        ├─────────┤
│   IP    │      │   IP    │        │   IP    │
└─────────┘      └─────────┘        └─────────┘
```

### QUIC Protocol

**Key Features**:
- UDP-based (bypasses TCP ossification)
- Built-in TLS 1.3 encryption
- Multiplexed streams (like HTTP/2)
- Per-stream flow control
- 0-RTT resumption
- Connection migration
- Improved loss recovery

**Connection Establishment**:
```
Client                              Server
  |                                    |
  |-- Initial Packet (ClientHello) -->|  (0-RTT or 1-RTT)
  |    + QUIC transport params         |
  |    + Application data (0-RTT)      |
  |                                    |
  |<-- Initial + Handshake Packets ----|
  |    (ServerHello, Certificate)      |
  |                                    |
  |-- Handshake Packet --------------->|
  |    (Certificate, Finished)         |
  |                                    |
  |<-- Short Header Packets ---------->|
  |    (Encrypted application data)    |
```

**1-RTT Connection** (first time):
```
Time    Client                  Server
0ms     ├─ ClientHello ────────>│
        │  (QUIC params)         │
        │                        │
50ms    │<──── ServerHello ──────┤
        │     (QUIC params)      │
        │     Certificate        │
        │     Finished           │
        │                        │
        ├─ Finished ────────────>│
        │  HTTP/3 request        │
        │                        │
100ms   │<──── HTTP/3 response ──┤
```

**0-RTT Connection** (resumption):
```
Time    Client                  Server
0ms     ├─ ClientHello ────────>│
        │  0-RTT data            │
        │  HTTP/3 request        │
        │                        │
50ms    │<──── ServerHello ──────┤
        │     1-RTT data         │
        │     HTTP/3 response    │
```

### Stream Multiplexing (No HOL Blocking)

**HTTP/2 over TCP Problem**:
```
┌────────────┐
│ Stream 1   │ ──> Packet lost! All streams blocked ✗
│ Stream 2   │
│ Stream 3   │
└────────────┘
    TCP Layer (head-of-line blocking)
```

**HTTP/3 over QUIC Solution**:
```
┌────────────┐
│ Stream 1   │ ──> Packet lost! Only Stream 1 blocked ✓
│ Stream 2   │ ──> Continues ✓
│ Stream 3   │ ──> Continues ✓
└────────────┘
    QUIC Layer (no head-of-line blocking)
```

### Connection Migration

**Use Case**: Mobile device switches networks

**TCP Behavior**:
```
Mobile Device                      Server
├─ WiFi connection ────────────────┤
│  Connection: SRC 10.0.1.5:8080   │
│              DST api.com:443     │
│  (Switch from WiFi to 4G)        │
│  Connection LOST ✗               │
├─ Must reconnect (new handshake) ─┤
```

**QUIC Behavior**:
```
Mobile Device                      Server
├─ WiFi connection ────────────────┤
│  Connection ID: abc123           │
│  (Switch from WiFi to 4G)        │
├─ PATH_CHALLENGE (new IP) ───────>│
│<─ PATH_RESPONSE ──────────────────┤
│  Connection MIGRATED ✓           │
│  Same Connection ID: abc123      │
```

---

## Patterns

### Pattern 1: 0-RTT Resumption

**Use Case**: Fast reconnection for returning clients

```go
// Go QUIC server with 0-RTT
package main

import (
    "github.com/lucas-clemente/quic-go"
    "github.com/lucas-clemente/quic-go/http3"
)

func main() {
    server := http3.Server{
        Addr: ":443",
        Handler: myHandler,
        QuicConfig: &quic.Config{
            // Enable 0-RTT
            Allow0RTT: true,
        },
    }

    server.ListenAndServeTLS("cert.pem", "key.pem")
}
```

**Client Side**:
```go
client := &http.Client{
    Transport: &http3.RoundTripper{
        TLSClientConfig: &tls.Config{
            // Store session tickets for 0-RTT
            ClientSessionCache: tls.NewLRUClientSessionCache(100),
        },
    },
}

// First request: 1-RTT
resp1, _ := client.Get("https://api.example.com/data")

// Second request (same domain): 0-RTT
resp2, _ := client.Get("https://api.example.com/more-data")
```

**⚠️ Security Note**: 0-RTT data can be replayed. Only use for idempotent requests (GET, HEAD).

### Pattern 2: Connection Migration

**Use Case**: Maintain connection across network changes

```javascript
// Node.js QUIC client with migration
const { QuicSocket } = require('quic');

const socket = new QuicSocket({ client: { /* ... */ } });

socket.on('sessionReady', (session) => {
    console.log('QUIC session established');

    // Connection will migrate automatically on network change
    session.on('pathUpdated', (remote, local) => {
        console.log('Connection migrated to new path');
        console.log(`Old: ${remote.address}:${remote.port}`);
        console.log(`New: ${local.address}:${local.port}`);
    });
});
```

### Pattern 3: Adaptive Congestion Control

**Use Case**: Optimize for different network conditions

```rust
// Rust QUIC with custom congestion control
use quiche::Config;

let mut config = Config::new(quiche::PROTOCOL_VERSION)?;

// Use BBR for high-bandwidth networks
config.set_cc_algorithm(quiche::CongestionControlAlgorithm::BBR);

// Or use CUBIC for mixed conditions
config.set_cc_algorithm(quiche::CongestionControlAlgorithm::CUBIC);

// Create connection
let conn = quiche::connect(
    Some("example.com"),
    &scid,
    local,
    peer,
    &mut config,
)?;
```

---

## Implementation Examples

### Nginx HTTP/3 Configuration

```nginx
server {
    listen 443 quic reuseport;
    listen 443 ssl http2;

    server_name example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Enable HTTP/3
    add_header Alt-Svc 'h3=":443"; ma=86400';

    # Enable 0-RTT
    ssl_early_data on;

    location / {
        root /var/www/html;
    }
}
```

### Cloudflare Workers (HTTP/3)

```javascript
// Cloudflare automatically uses HTTP/3
export default {
    async fetch(request) {
        // Check if request came via HTTP/3
        const httpVersion = request.cf?.httpProtocol;

        return new Response(`HTTP Version: ${httpVersion}`, {
            headers: {
                'Content-Type': 'text/plain',
                // Advertise HTTP/3 support
                'Alt-Svc': 'h3=":443"; ma=86400'
            }
        });
    }
}
```

### Go HTTP/3 Client

```go
package main

import (
    "crypto/tls"
    "fmt"
    "io"
    "net/http"

    "github.com/lucas-clemente/quic-go/http3"
)

func main() {
    // Create HTTP/3 client
    client := &http.Client{
        Transport: &http3.RoundTripper{
            TLSClientConfig: &tls.Config{
                InsecureSkipVerify: false,
            },
        },
    }

    // Make request over HTTP/3
    resp, err := client.Get("https://cloudflare-quic.com")
    if err != nil {
        panic(err)
    }
    defer resp.Body.Close()

    // Check protocol
    fmt.Printf("Protocol: %s\n", resp.Proto) // HTTP/3.0

    body, _ := io.ReadAll(resp.Body)
    fmt.Printf("Body: %s\n", body)
}
```

### Python HTTP/3 with aioquic

```python
import asyncio
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration

async def fetch_http3(url):
    # Configure QUIC
    configuration = QuicConfiguration(
        is_client=True,
        alpn_protocols=["h3"],
    )

    # Connect
    async with connect(
        "example.com",
        443,
        configuration=configuration,
    ) as client:
        # Send HTTP/3 request
        stream_id = client._quic.get_next_available_stream_id()

        headers = [
            (b":method", b"GET"),
            (b":scheme", b"https"),
            (b":authority", b"example.com"),
            (b":path", b"/"),
        ]

        client._quic.send_headers(stream_id, headers)

        # Receive response
        response = await client.receive_response(stream_id)
        return response.content

# Run
asyncio.run(fetch_http3("https://example.com"))
```

---

## Best Practices

### 1. Fallback to HTTP/2

```nginx
# ✅ Good: Support both HTTP/3 and HTTP/2
server {
    listen 443 quic reuseport;
    listen 443 ssl http2;  # Fallback

    add_header Alt-Svc 'h3=":443"; ma=86400';
}
```

### 2. Careful with 0-RTT

```python
# ❌ Bad: Non-idempotent request in 0-RTT
@app.route('/transfer-money', methods=['POST'])
def transfer():
    # Could be replayed!
    transfer_money(from_user, to_user, amount)

# ✅ Good: Only idempotent requests in 0-RTT
if request.is_0rtt:
    if request.method != 'GET':
        return "405 Method Not Allowed", 405
```

### 3. UDP Firewall Configuration

```bash
# Allow UDP port 443 for QUIC
iptables -A INPUT -p udp --dport 443 -j ACCEPT
iptables -A OUTPUT -p udp --sport 443 -j ACCEPT
```

---

## Performance Comparison

### Latency Improvement

```
Round-trip times for first request:

HTTP/1.1:  TCP handshake (1 RTT) + TLS handshake (2 RTT) = 3 RTT
HTTP/2:    TCP handshake (1 RTT) + TLS handshake (2 RTT) = 3 RTT
HTTP/3:    QUIC handshake (1 RTT, or 0 RTT with resumption)

Example with 50ms RTT:
HTTP/1.1:  150ms before first byte
HTTP/2:    150ms before first byte
HTTP/3:    50ms (or 0ms with 0-RTT!)
```

### Packet Loss Resilience

```
10% packet loss impact:

HTTP/2: All streams blocked when any packet lost
HTTP/3: Only affected stream blocked

Result: HTTP/3 often 2-3x faster on lossy networks
```

---

## Troubleshooting

### Issue 1: QUIC Blocked

**Check UDP connectivity**:
```bash
# Test if UDP port 443 is open
nc -zuv example.com 443

# Check with curl
curl --http3 https://cloudflare-quic.com
```

### Issue 2: Alt-Svc Not Working

**Verify header**:
```bash
curl -I https://example.com
# Look for: Alt-Svc: h3=":443"; ma=86400

# If missing, check server config
```

### Issue 3: Connection Migration Failing

**Symptoms**: Connection drops when switching networks

**Solution**: Ensure both client and server support migration

```go
config := &quic.Config{
    // Enable connection migration
    DisablePathMTUDiscovery: false,
    MaxIdleTimeout: 30 * time.Second,
}
```

---

## Related Skills

- `protocols-http2-multiplexing` - HTTP/2 protocol
- `protocols-udp-fundamentals` - UDP protocol basics
- `protocols-quic-protocol` - QUIC protocol deep dive
- `networking-network-resilience-patterns` - Network resilience
- `proxies-nginx-configuration` - Nginx HTTP/3 setup
- `cryptography-tls-configuration` - TLS 1.3 configuration

---

**Last Updated**: 2025-10-27
