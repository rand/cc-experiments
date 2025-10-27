---
name: protocols-protocol-selection
description: Guide for selecting appropriate network protocols (HTTP/1.1, HTTP/2, HTTP/3, TCP, UDP, QUIC) based on use case
---

# Protocol Selection Guide

**Scope**: Decision framework for choosing network protocols based on requirements
**Lines**: ~250
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Designing new networked applications
- Choosing protocols for specific use cases
- Optimizing existing protocol choices
- Understanding protocol trade-offs
- Evaluating HTTP/1.1 vs HTTP/2 vs HTTP/3
- Deciding between TCP and UDP
- Building real-time applications
- Selecting protocols for mobile apps

## Decision Framework

### TCP vs UDP

**Use TCP When**:
- ✓ Reliability is critical (file transfer, database, messages)
- ✓ Ordering matters
- ✓ You need built-in flow control
- ✓ Connection-oriented design fits your use case
- ✓ Firewall traversal is a concern (TCP more widely supported)

**Use UDP When**:
- ✓ Low latency is critical (gaming, VoIP, video streaming)
- ✓ Some packet loss is acceptable
- ✓ Old data is useless (real-time position updates)
- ✓ You want to implement custom reliability
- ✓ Broadcasting or multicasting needed

**Examples**:
```
TCP: HTTP, HTTPS, SSH, FTP, SMTP, databases
UDP: DNS, DHCP, VoIP, gaming, video streaming (RTP), QUIC
```

### HTTP Version Selection

**HTTP/1.1**: Legacy, simple
```
Use When:
✓ Simple request/response model
✓ Few concurrent requests
✓ Client compatibility critical
✓ Debugging ease important

Avoid When:
✗ Many resources per page
✗ High latency networks
✗ Mobile applications
```

**HTTP/2**: Modern, multiplexed
```
Use When:
✓ Modern web applications
✓ Many resources per page
✓ Want server push
✓ Need header compression

Avoid When:
✗ Very high packet loss (TCP HOL blocking)
✗ Legacy client compatibility needed
```

**HTTP/3**: Latest, QUIC-based
```
Use When:
✓ Mobile applications (connection migration)
✓ High-latency or lossy networks
✓ Want lowest latency
✓ Modern clients only

Avoid When:
✗ Broad client compatibility needed
✗ UDP blocked by firewalls
✗ Server infrastructure doesn't support it
```

---

## Use Case Matrix

### Web APIs

| Requirement | HTTP/1.1 | HTTP/2 | HTTP/3 |
|------------|----------|---------|---------|
| Simple REST API | ✅ Good | ✅ Good | ⚠️ Overkill |
| High-traffic API | ⚠️ OK | ✅ Better | ✅ Best |
| Mobile clients | ⚠️ OK | ✅ Good | ✅ Best |
| Legacy clients | ✅ Required | ⚠️ Fallback | ❌ No |
| WebSocket | ✅ Yes | ✅ Yes | ❌ Use WebTransport |

### Real-Time Applications

| Application | TCP | UDP | QUIC |
|------------|-----|-----|------|
| Chat (text) | ✅ Perfect | ❌ No | ✅ Good |
| Voice call | ❌ Too slow | ✅ Perfect | ✅ Perfect |
| Video stream | ❌ Buffering | ✅ Good | ✅ Better |
| Gaming | ❌ Lag | ✅ Perfect | ✅ Good |
| File sharing | ✅ Perfect | ❌ No | ✅ Good |

### Infrastructure Protocols

| Protocol | Transport | Why |
|----------|-----------|-----|
| DNS | UDP (TCP fallback) | Fast lookups, small payload |
| DHCP | UDP | Broadcast discovery |
| SSH | TCP | Reliable shell sessions |
| RDP/VNC | TCP | Pixel-perfect screen updates |
| NTP | UDP | Time sync, best-effort |

---

## Decision Trees

### Application Type Decision

```
Is data loss acceptable?
├─ NO → Use TCP
│   ├─ Many concurrent requests? → HTTP/2 or HTTP/3
│   ├─ Simple request/response? → HTTP/1.1
│   └─ Custom protocol? → Plain TCP
│
└─ YES → Consider UDP
    ├─ Need reliability layer? → QUIC
    ├─ Real-time streaming? → UDP (RTP)
    └─ Simple datagrams? → Plain UDP
```

### Latency Priority Decision

```
What's your latency requirement?
├─ <50ms critical?
│   ├─ Can lose packets? → UDP
│   ├─ Need reliability? → QUIC
│   └─ Need ordering? → Tricky (custom UDP layer)
│
├─ <200ms acceptable?
│   ├─ HTTP-based? → HTTP/2
│   └─ Custom? → TCP
│
└─ >200ms OK?
    └─ HTTP/1.1 or HTTP/2 fine
```

---

## Examples by Use Case

### 1. Video Conferencing

**Protocol Choice**: WebRTC (UDP + QUIC)

**Why**:
- Real-time video: UDP for low latency
- Audio: UDP (loss tolerance with error concealment)
- Signaling: WebSocket over TCP/HTTP/2
- Data channel: QUIC for reliability when needed

```javascript
// WebRTC uses UDP for media, TCP for signaling
const pc = new RTCPeerConnection();

// Media over UDP
pc.addTrack(videoTrack);
pc.addTrack(audioTrack);

// Data channel (QUIC-like)
const dataChannel = pc.createDataChannel("chat", {
    ordered: false,  // Out-of-order OK for some data
    maxRetransmits: 3  // Limit retries
});
```

### 2. HTTP API

**Protocol Choice**: HTTP/2 with HTTP/3 support

**Why**:
- Multiple requests: HTTP/2 multiplexing
- Server push: Proactively send data
- Mobile: HTTP/3 connection migration
- Fallback: HTTP/1.1 for old clients

```nginx
server {
    listen 443 ssl http2;
    listen 443 quic reuseport;

    add_header Alt-Svc 'h3=":443"; ma=86400';

    location /api {
        proxy_pass http://backend;
    }
}
```

### 3. Online Gaming

**Protocol Choice**: UDP with custom reliability

**Why**:
- Position updates: UDP (loss OK)
- Game state: Custom reliability layer
- Chat: TCP/WebSocket
- Assets: TCP/HTTP

```python
# Player position: UDP (lossy)
udp_socket.sendto(f"POS:{x},{y},{z}".encode(), server)

# Chat messages: TCP (reliable)
tcp_socket.send(f"CHAT:{message}".encode())
```

### 4. File Transfer

**Protocol Choice**: HTTP/2 or HTTP/3

**Why**:
- Reliability required: TCP or QUIC
- Resume support: HTTP Range requests
- Speed: HTTP/2 multiplexing
- Mobile: HTTP/3 migration

```python
import requests

# HTTP/2 with range support
response = requests.get(
    'https://cdn.example.com/large-file.zip',
    headers={'Range': 'bytes=0-1048576'},  # First 1MB
    stream=True
)
```

---

## Anti-Patterns

### ❌ Wrong: TCP for Real-Time Gaming

**Problem**: TCP retransmits block all data

```python
# Player position over TCP
sock.send(b"POS:100,200")  # If lost, blocks everything!
```

**Solution**: Use UDP

```python
# Player position over UDP
sock.sendto(b"POS:100,200", server)  # Loss OK, keep going
```

### ❌ Wrong: UDP for Critical Messages

**Problem**: No delivery guarantee

```python
# Payment transaction over UDP
sock.sendto(b"TRANSFER:$1000", server)  # Might be lost!
```

**Solution**: Use TCP or add reliability

```python
# Payment over TCP
sock.send(b"TRANSFER:$1000")  # Guaranteed delivery
```

---

## Migration Strategies

### HTTP/1.1 → HTTP/2

```
1. Enable HTTP/2 on server
2. Add Alt-Svc header
3. Monitor adoption
4. Optimize with server push
5. Eventually deprecate HTTP/1.1
```

### HTTP/2 → HTTP/3

```
1. Enable HTTP/3 endpoint
2. Add Alt-Svc header
3. Clients auto-upgrade
4. Keep HTTP/2 as fallback
5. Monitor UDP firewall issues
```

---

## Related Skills

- `protocols-http-fundamentals` - HTTP/1.1 basics
- `protocols-http2-multiplexing` - HTTP/2 details
- `protocols-http3-quic` - HTTP/3 details
- `protocols-tcp-fundamentals` - TCP protocol
- `protocols-udp-fundamentals` - UDP protocol
- `protocols-quic-protocol` - QUIC protocol

---

**Last Updated**: 2025-10-27
