# HTTP/3 and QUIC Protocol Reference

**Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: 3,847

## Table of Contents

1. [Introduction](#introduction)
2. [QUIC Protocol Fundamentals](#quic-protocol-fundamentals)
3. [HTTP/3 Over QUIC](#http3-over-quic)
4. [Connection Establishment](#connection-establishment)
5. [Streams and Multiplexing](#streams-and-multiplexing)
6. [Flow Control and Congestion](#flow-control-and-congestion)
7. [Loss Detection and Recovery](#loss-detection-and-recovery)
8. [Security and TLS 1.3](#security-and-tls-13)
9. [QPACK Header Compression](#qpack-header-compression)
10. [Connection Migration](#connection-migration)
11. [Performance Characteristics](#performance-characteristics)
12. [Server Implementation](#server-implementation)
13. [Client Implementation](#client-implementation)
14. [CDN and Edge Deployment](#cdn-and-edge-deployment)
15. [Testing and Debugging](#testing-and-debugging)
16. [Migration Strategies](#migration-strategies)
17. [Anti-Patterns](#anti-patterns)

---

## Introduction

### What is QUIC?

**QUIC** (Quick UDP Internet Connections) is a modern transport protocol designed to improve web performance and security. Originally developed by Google and now standardized by the IETF as RFC 9000.

**Key innovations**:
- **Built on UDP**: Avoids TCP head-of-line blocking
- **Integrated TLS 1.3**: Security built into transport layer
- **Connection migration**: Seamless handoff between networks
- **0-RTT connection establishment**: Resume connections without handshake
- **Stream multiplexing**: Independent streams without blocking
- **Improved congestion control**: Better loss recovery than TCP

### What is HTTP/3?

**HTTP/3** is the third major version of HTTP, using QUIC as transport instead of TCP. Standardized as RFC 9114.

**Key differences from HTTP/2**:
```
HTTP/2                      HTTP/3
TCP + TLS 1.2/1.3          QUIC (includes TLS 1.3)
HPACK compression          QPACK compression
TCP streams                QUIC streams
Head-of-line blocking      No HOL blocking
1-3 RTT handshake          0-1 RTT handshake
No connection migration    Connection migration
```

### Protocol Stack Comparison

**HTTP/1.1**:
```
┌────────────┐
│   HTTP/1   │
├────────────┤
│    TLS     │
├────────────┤
│    TCP     │
├────────────┤
│     IP     │
└────────────┘
```

**HTTP/2**:
```
┌────────────┐
│   HTTP/2   │
├────────────┤
│    TLS     │
├────────────┤
│    TCP     │
├────────────┤
│     IP     │
└────────────┘
```

**HTTP/3**:
```
┌────────────┐
│   HTTP/3   │
├────────────┤
│    QUIC    │
│  (TLS 1.3) │
├────────────┤
│    UDP     │
├────────────┤
│     IP     │
└────────────┘
```

---

## QUIC Protocol Fundamentals

### QUIC Packet Structure

**QUIC packets** are encapsulated in UDP datagrams:

```
UDP Datagram:
┌──────────────────────────────────────┐
│ UDP Header (8 bytes)                 │
├──────────────────────────────────────┤
│ QUIC Packet Header (variable)        │
├──────────────────────────────────────┤
│ QUIC Frames (variable)               │
│  - STREAM frames                     │
│  - ACK frames                        │
│  - CRYPTO frames                     │
│  - CONNECTION_CLOSE frames           │
│  - etc.                              │
└──────────────────────────────────────┘
```

### Packet Types

**Initial Packet**: First packet in connection (contains TLS ClientHello)
```
Initial Packet Header:
┌─────────────────────────────────┐
│ Header Form (1 bit): 1          │
│ Fixed Bit (1 bit): 1            │
│ Long Packet Type (2 bits): 00   │
│ Type-Specific Bits (4 bits)     │
├─────────────────────────────────┤
│ Version (32 bits)               │
├─────────────────────────────────┤
│ Destination Connection ID       │
├─────────────────────────────────┤
│ Source Connection ID            │
├─────────────────────────────────┤
│ Token (variable)                │
├─────────────────────────────────┤
│ Packet Number (variable)        │
├─────────────────────────────────┤
│ Payload (encrypted)             │
└─────────────────────────────────┘
```

**Handshake Packet**: Contains TLS handshake messages
**0-RTT Packet**: Early data (application data before handshake completes)
**1-RTT Packet** (Short Header): Post-handshake application data

**Short Header Packet** (most common after handshake):
```
┌─────────────────────────────────┐
│ Header Form (1 bit): 0          │
│ Fixed Bit (1 bit): 1            │
│ Spin Bit (1 bit)                │
│ Reserved Bits (2 bits)          │
│ Key Phase (1 bit)               │
│ Packet Number Length (2 bits)   │
├─────────────────────────────────┤
│ Destination Connection ID       │
├─────────────────────────────────┤
│ Packet Number (1-4 bytes)       │
├─────────────────────────────────┤
│ Payload (encrypted)             │
└─────────────────────────────────┘
```

### QUIC Frames

**Frame types** carry different types of data:

**STREAM Frame** (carry application data):
```
┌─────────────────────────────────┐
│ Type (0x08-0x0f)                │
├─────────────────────────────────┤
│ Stream ID (variable)            │
├─────────────────────────────────┤
│ [Offset] (variable)             │
├─────────────────────────────────┤
│ [Length] (variable)             │
├─────────────────────────────────┤
│ Stream Data (...)               │
└─────────────────────────────────┘
```

**ACK Frame** (acknowledge packets):
```
┌─────────────────────────────────┐
│ Type (0x02-0x03)                │
├─────────────────────────────────┤
│ Largest Acknowledged (variable) │
├─────────────────────────────────┤
│ ACK Delay (variable)            │
├─────────────────────────────────┤
│ ACK Range Count (variable)      │
├─────────────────────────────────┤
│ First ACK Range (variable)      │
├─────────────────────────────────┤
│ [ACK Ranges] (...)              │
└─────────────────────────────────┘
```

**CRYPTO Frame** (TLS handshake data):
```
┌─────────────────────────────────┐
│ Type (0x06)                     │
├─────────────────────────────────┤
│ Offset (variable)               │
├─────────────────────────────────┤
│ Length (variable)               │
├─────────────────────────────────┤
│ Crypto Data (...)               │
└─────────────────────────────────┘
```

**Other important frames**:
- **PING**: Keep connection alive
- **RESET_STREAM**: Abort stream
- **STOP_SENDING**: Request peer stop sending
- **NEW_CONNECTION_ID**: Provide new connection ID
- **CONNECTION_CLOSE**: Close connection
- **MAX_DATA**: Flow control (connection level)
- **MAX_STREAM_DATA**: Flow control (stream level)
- **MAX_STREAMS**: Limit concurrent streams

### Connection IDs

**Connection ID** identifies QUIC connection (unlike TCP which uses 4-tuple):

```
Traditional TCP connection:
  Source IP:Port + Destination IP:Port

QUIC connection:
  Connection ID (chosen by receiver)
```

**Benefits**:
- **Connection migration**: Connection survives IP/port changes
- **Load balancing**: Route packets by connection ID
- **NAT rebinding**: Tolerate NAT changes

**Example**:
```python
# Client generates initial connection ID
client_conn_id = random_bytes(8)  # 8-byte ID

# Server responds with its own connection ID
server_conn_id = random_bytes(8)

# Both endpoints use peer's connection ID in packets
# Client → Server: uses server_conn_id
# Server → Client: uses client_conn_id
```

---

## HTTP/3 Over QUIC

### HTTP/3 Framing

**HTTP/3 frames** are sent inside QUIC STREAM frames:

```
QUIC Packet
  └── QUIC STREAM Frame
        └── HTTP/3 Frame
              - HEADERS frame
              - DATA frame
              - SETTINGS frame
              - etc.
```

**HTTP/3 Frame Format**:
```
┌─────────────────────────────────┐
│ Type (variable)                 │
├─────────────────────────────────┤
│ Length (variable)               │
├─────────────────────────────────┤
│ Frame Payload (...)             │
└─────────────────────────────────┘
```

### HTTP/3 Frame Types

**DATA Frame** (0x0): HTTP message body
```
┌─────────────────────────────────┐
│ Type (0x0)                      │
├─────────────────────────────────┤
│ Length                          │
├─────────────────────────────────┤
│ HTTP Message Body               │
└─────────────────────────────────┘
```

**HEADERS Frame** (0x1): HTTP headers (QPACK compressed)
```
┌─────────────────────────────────┐
│ Type (0x1)                      │
├─────────────────────────────────┤
│ Length                          │
├─────────────────────────────────┤
│ Encoded Field Section (QPACK)   │
└─────────────────────────────────┘
```

**SETTINGS Frame** (0x4): Connection settings
```
┌─────────────────────────────────┐
│ Type (0x4)                      │
├─────────────────────────────────┤
│ Length                          │
├─────────────────────────────────┤
│ Settings (key-value pairs)      │
│  - QPACK_MAX_TABLE_CAPACITY     │
│  - MAX_FIELD_SECTION_SIZE       │
│  - QPACK_BLOCKED_STREAMS        │
└─────────────────────────────────┘
```

**Other HTTP/3 frames**:
- **CANCEL_PUSH** (0x3): Cancel server push
- **PUSH_PROMISE** (0x5): Server push promise
- **GOAWAY** (0x7): Graceful shutdown
- **MAX_PUSH_ID** (0xd): Limit server push

### Stream Types

**QUIC streams** are bidirectional or unidirectional:

**HTTP/3 uses specific stream types**:
- **Request streams** (bidirectional): Client requests, server responses
- **Control stream** (unidirectional): SETTINGS, GOAWAY frames
- **QPACK encoder stream** (unidirectional): Dynamic table updates
- **QPACK decoder stream** (unidirectional): Acknowledgments
- **Push streams** (unidirectional): Server push

```
Client                          Server
  |                               |
  |-- Request Stream 0 --------->|  (Bidirectional)
  |   HEADERS + DATA              |
  |                               |
  |<------ Response --------------|
  |    HEADERS + DATA             |
  |                               |
  |-- Control Stream ----------->|  (Unidirectional)
  |   SETTINGS                    |
  |                               |
  |<-- Control Stream ------------|
  |    SETTINGS                   |
  |                               |
  |-- QPACK Encoder Stream ----->|
  |<-- QPACK Decoder Stream ------|
```

### Request-Response Flow

**Complete HTTP/3 request**:
```
1. Client opens bidirectional stream
2. Client sends HEADERS frame (method, path, headers)
3. Client sends DATA frame(s) (request body, if present)
4. Server sends HEADERS frame (status, headers)
5. Server sends DATA frame(s) (response body)
6. Stream closed (FIN bit set)
```

**Example**:
```
Client → Server (Stream 0):
┌────────────────────────────────────┐
│ HEADERS Frame                      │
│  :method: GET                      │
│  :scheme: https                    │
│  :authority: example.com           │
│  :path: /index.html                │
│  user-agent: curl/8.0              │
└────────────────────────────────────┘

Server → Client (Stream 0):
┌────────────────────────────────────┐
│ HEADERS Frame                      │
│  :status: 200                      │
│  content-type: text/html           │
│  content-length: 1234              │
├────────────────────────────────────┤
│ DATA Frame                         │
│  <html>...</html>                  │
└────────────────────────────────────┘
```

---

## Connection Establishment

### 1-RTT Handshake (First Connection)

**Traditional TCP + TLS 1.3** (2-3 RTT):
```
Client                    Server
  |                         |
  |-- TCP SYN ------------->|  (1 RTT)
  |<-- TCP SYN-ACK ---------|
  |-- TCP ACK ------------->|
  |                         |
  |-- TLS ClientHello ----->|  (2 RTT)
  |<-- TLS ServerHello -----|
  |    (Certificate, etc.)  |
  |-- TLS Finished -------->|
  |                         |
  |-- HTTP Request -------->|  (3 RTT)
  |<-- HTTP Response -------|
```

**QUIC + HTTP/3** (1 RTT):
```
Client                    Server
  |                         |
  |-- Initial Packet ------>|  (1 RTT)
  |   (CRYPTO: ClientHello) |
  |   (HTTP/3 SETTINGS)     |
  |   (HTTP/3 Request)      |
  |                         |
  |<-- Initial + Handshake -|
  |    (CRYPTO: ServerHello)|
  |    (Certificate)        |
  |                         |
  |-- Handshake ----------->|
  |   (CRYPTO: Finished)    |
  |                         |
  |<-- 1-RTT Packet --------|
  |    (HTTP/3 Response)    |
```

**Key benefit**: HTTP request sent in first flight (1-RTT)

### 0-RTT Connection Resumption

**0-RTT** allows sending application data in first packet:

```
Previous Connection:
  Client ←→ Server
  (Receives session ticket + parameters)

Resumed Connection:
Client                    Server
  |                         |
  |-- Initial + 0-RTT ------>|  (0 RTT for app data!)
  |   (CRYPTO: ClientHello) |
  |   (0-RTT: HTTP Request) |
  |                         |
  |<-- Initial + 1-RTT ------|
  |    (HTTP Response)      |
```

**0-RTT benefits**:
- **Zero latency**: No handshake delay for resumed connections
- **Improved performance**: Critical for short-lived requests

**0-RTT risks**:
- **Replay attacks**: 0-RTT data can be replayed by attacker
- **Non-idempotent requests**: Only use for safe operations (GET, not POST)

**0-RTT configuration**:
```python
# Server: Enable 0-RTT
config = QuicConfiguration(
    max_early_data_size=16384  # Allow 16 KB of 0-RTT data
)

# Client: Use 0-RTT
if session_ticket:
    # Send 0-RTT data
    stream = connection.create_stream()
    stream.write(b"GET / HTTP/3\r\n...")
    connection.send_0rtt()
```

### Connection Migration

**Connection migration** allows connection to survive network changes:

```
Scenario: Mobile device switches from WiFi to cellular

Traditional TCP:
  WiFi: 192.168.1.100:12345 → Server:443
  [Network switch]
  Cellular: 10.0.0.50:54321 → Server:443
  Result: Connection breaks (different source IP/port)

QUIC:
  WiFi: 192.168.1.100:12345 → Server:443 (Connection ID: 0xABCD)
  [Network switch]
  Cellular: 10.0.0.50:54321 → Server:443 (Connection ID: 0xABCD)
  Result: Connection continues (same Connection ID)
```

**Migration process**:
```
Client (WiFi)              Server
  |                         |
  |-- Packet (Conn ID 0x01) ->|
  |                         |
  [Switch to cellular]
  |                         |
  |-- Packet (Conn ID 0x01) ->|  (New source IP/port)
  |   (PATH_CHALLENGE)      |
  |                         |
  |<-- PATH_RESPONSE -------|  (Validates new path)
  |                         |
  |-- Continue traffic ---->|  (On new path)
```

**Benefits**:
- **Seamless handoff**: No connection interruption
- **Mobile optimization**: Survives WiFi ↔ cellular switches
- **NAT rebinding tolerance**: Handles NAT timeout/rebinding

---

## Streams and Multiplexing

### Stream Independence

**HTTP/2 problem**: TCP head-of-line blocking

```
HTTP/2 over TCP:
  TCP: [Stream A packet 1] [Stream B packet 1] [Stream A packet 2 LOST]
       ↓
  Result: Stream B blocked waiting for Stream A packet 2 retransmission
          (TCP delivers bytes in order)
```

**HTTP/3 solution**: Independent QUIC streams

```
HTTP/3 over QUIC:
  QUIC: [Stream A packet 1] [Stream B packet 1] [Stream A packet 2 LOST]
        ↓
  Result: Stream B continues (packet 1 delivered)
          Stream A blocks only for packet 2
          (QUIC delivers streams independently)
```

### Stream Creation

**Client-initiated streams** (odd stream IDs):
```
Stream ID 0: First client request
Stream ID 4: Second client request
Stream ID 8: Third client request
...
```

**Server-initiated streams** (even stream IDs, for server push):
```
Stream ID 1: First server push
Stream ID 5: Second server push
...
```

**Bidirectional vs Unidirectional**:
```
Bidirectional streams:
  - Request/response streams (ID % 4 == 0 or 1)

Unidirectional streams:
  - Control stream (ID % 4 == 2 or 3)
  - QPACK encoder/decoder streams
  - Server push streams
```

### Stream Concurrency

**MAX_STREAMS control**:
```
Server → Client: MAX_STREAMS (bidirectional: 100)
                 MAX_STREAMS (unidirectional: 10)

Result: Client can open up to 100 concurrent bidirectional streams
        Client can open up to 10 concurrent unidirectional streams
```

**Example configuration**:
```python
# Server configuration
config = QuicConfiguration(
    max_concurrent_streams_bidi=100,  # HTTP requests
    max_concurrent_streams_uni=10     # Control/QPACK streams
)
```

### Stream Prioritization

**HTTP/3 prioritization** (RFC 9218):

```
Priority Frame:
┌────────────────────────────────┐
│ Prioritized Element ID         │
│ Element Dependency ID          │
│ Weight (1-256)                 │
│ Exclusive Flag                 │
└────────────────────────────────┘
```

**Priority hints**:
```
Client → Server: PRIORITY frame
  Stream 4 (CSS): Weight 128, Dependency: None
  Stream 8 (Image): Weight 64, Dependency: Stream 4
  Stream 12 (Analytics): Weight 32, Dependency: None

Result: Server prioritizes CSS > Image > Analytics
```

---

## Flow Control and Congestion

### Flow Control

**QUIC flow control** operates at two levels:

**Connection-level flow control**:
```
Server → Client: MAX_DATA (1,048,576 bytes)

Result: Total data across all streams ≤ 1 MB
```

**Stream-level flow control**:
```
Server → Client: MAX_STREAM_DATA (Stream 4, 65,536 bytes)

Result: Data on Stream 4 ≤ 64 KB
```

**Flow control window updates**:
```
Initial state:
  MAX_DATA: 1 MB
  MAX_STREAM_DATA (Stream 4): 64 KB

After receiving 32 KB on Stream 4:
  Consumed: 32 KB
  Remaining: 32 KB

Receiver sends MAX_STREAM_DATA update:
  MAX_STREAM_DATA (Stream 4): 128 KB
  (New window: 64 KB → 128 KB)
```

### Congestion Control

**QUIC congestion control** (RFC 9002):

**Algorithms**:
- **NewReno** (default): AIMD (Additive Increase, Multiplicative Decrease)
- **CUBIC**: More aggressive, better for high-latency networks
- **BBR** (Bottleneck Bandwidth and RTT): Google's algorithm

**NewReno state machine**:
```
Slow Start:
  cwnd (congestion window) doubles each RTT
  Until: packet loss OR cwnd ≥ ssthresh

Congestion Avoidance:
  cwnd increases linearly (+1 MSS per RTT)
  Until: packet loss

Fast Recovery:
  cwnd = cwnd / 2 (multiplicative decrease)
  Return to Congestion Avoidance
```

**Example**:
```
RTT 1: cwnd = 10 packets (Slow Start)
RTT 2: cwnd = 20 packets
RTT 3: cwnd = 40 packets
RTT 4: Packet loss detected
       ssthresh = 20 (cwnd / 2)
       cwnd = 20
RTT 5: cwnd = 21 (Congestion Avoidance, +1 per RTT)
RTT 6: cwnd = 22
...
```

**BBR congestion control**:
```
BBR measures:
  - Bottleneck bandwidth (max delivery rate)
  - RTT (round-trip time)

Pacing rate = bottleneck_bw * gain
cwnd = BDP (Bandwidth-Delay Product)

Benefits:
  - Lower latency (no queue buildup)
  - Better throughput on lossy networks
  - Faster convergence
```

**Configuration**:
```python
# Use BBR congestion control
config = QuicConfiguration(
    congestion_control_algorithm="bbr"
)
```

---

## Loss Detection and Recovery

### Packet Loss Detection

**QUIC loss detection** (RFC 9002):

**ACK-based loss detection**:
```
Sender                     Receiver
  |                          |
  |-- Packet 1 ------------->|
  |-- Packet 2 ------------->|
  |-- Packet 3 (LOST)        X
  |-- Packet 4 ------------->|
  |-- Packet 5 ------------->|
  |                          |
  |<-- ACK (1, 2, 4, 5) ------|
  |                          |

Result: Packet 3 declared lost (gap detected)
        Sender retransmits Packet 3 data
```

**Time-based loss detection**:
```
Sender                     Receiver
  |                          |
  |-- Packet 1 ------------->|
  |                          |
  [Wait RTT * 9/8]
  |                          |
  [No ACK received]
  |                          |

Result: Packet 1 declared lost (timeout)
        Sender retransmits Packet 1 data
```

### Retransmission

**QUIC retransmits data, not packets**:

```
TCP retransmission:
  - Retransmit exact same packet
  - Same sequence number

QUIC retransmission:
  - Retransmit STREAM frame data
  - New packet number
  - Allows better loss detection (no ambiguity)
```

**Example**:
```
Original:
  Packet 10: STREAM(id=4, offset=0, length=1000, data=...)

Retransmission:
  Packet 15: STREAM(id=4, offset=0, length=1000, data=...)
  (Same stream data, different packet number)
```

### Probe Timeout (PTO)

**PTO** triggers when no ACK received:

```
PTO calculation:
  PTO = smoothed_RTT + 4 * RTT_variance + max_ack_delay

Example:
  smoothed_RTT = 100 ms
  RTT_variance = 10 ms
  max_ack_delay = 25 ms

  PTO = 100 + 4*10 + 25 = 165 ms
```

**PTO retransmission**:
```
Sender                     Receiver
  |                          |
  |-- Packet 1 ------------->|
  |                          |
  [Wait PTO = 165 ms]
  |                          |
  [No ACK received]
  |                          |
  |-- PTO Probe ------------>|  (Retransmit most important data)
  |                          |
  |<-- ACK ------------------|
```

---

## Security and TLS 1.3

### TLS 1.3 Integration

**QUIC embeds TLS 1.3** in CRYPTO frames:

```
QUIC Packet Types → TLS Messages:

Initial Packet:
  └── CRYPTO frame → ClientHello

Handshake Packet:
  └── CRYPTO frame → ServerHello, Certificate, CertificateVerify, Finished

1-RTT Packet:
  └── STREAM frames → Application data (encrypted)
```

### Encryption Levels

**QUIC uses multiple encryption levels**:

1. **Initial keys** (derived from connection ID):
   - Encrypt Initial packets
   - Provides basic protection (not long-term secure)

2. **Handshake keys** (derived from TLS handshake):
   - Encrypt Handshake packets
   - Forward secrecy

3. **Application keys** (final TLS keys):
   - Encrypt 1-RTT packets (application data)
   - Full security

**Key derivation**:
```
Initial Keys:
  initial_salt = QUIC version-specific constant
  initial_secret = HKDF-Extract(initial_salt, destination_conn_id)
  client_initial_secret = HKDF-Expand-Label(initial_secret, "client in", ...)
  server_initial_secret = HKDF-Expand-Label(initial_secret, "server in", ...)

Handshake Keys:
  (Derived from TLS 1.3 handshake)

Application Keys:
  (Derived from TLS 1.3 master secret)
```

### Header Protection

**Header protection** hides packet numbers:

```
Unprotected packet:
┌────────────────────────────────┐
│ Packet Number: 12345           │  ← Visible
├────────────────────────────────┤
│ Payload (encrypted)            │
└────────────────────────────────┘

Protected packet:
┌────────────────────────────────┐
│ Packet Number: 0xXXXX          │  ← Encrypted
├────────────────────────────────┤
│ Payload (encrypted)            │
└────────────────────────────────┘
```

**Purpose**:
- **Privacy**: Hide packet numbers from observers
- **Prevent tracking**: Attackers can't correlate packets
- **Security**: Avoid leaking information

### Key Updates

**QUIC supports key updates** without handshake:

```
Application Phase:
  |                         |
  |-- Data (Key Phase 0) -->|
  |<-- Data (Key Phase 0) --|
  |                         |
  [Key update triggered]
  |                         |
  |-- Data (Key Phase 1) -->|  (New keys)
  |<-- Data (Key Phase 1) --|
```

**Benefits**:
- **Forward secrecy**: Compromise of current key doesn't reveal past data
- **No handshake**: Seamless key rotation

---

## QPACK Header Compression

### QPACK vs HPACK

**HPACK** (HTTP/2):
- Stateful compression
- Dynamic table shared across streams
- Head-of-line blocking (can't decode header if dependency lost)

**QPACK** (HTTP/3):
- Stateful compression (like HPACK)
- Independent streams (no HOL blocking)
- Encoder and decoder streams coordinate

### QPACK Architecture

```
Encoder (Client/Server)          Decoder (Server/Client)
  |                                 |
  |-- QPACK Encoder Stream -------->|  (Dynamic table updates)
  |                                 |
  |<-- QPACK Decoder Stream ---------|  (Acknowledgments)
  |                                 |
  |-- Request/Response Streams ----->|  (Compressed headers)
```

### QPACK Encoding

**Static table** (predefined entries):
```
Index | Header Name         | Header Value
------|---------------------|-------------
0     | :authority          |
1     | :path               | /
2     | :method             | GET
3     | :method             | POST
4     | :scheme             | http
5     | :scheme             | https
6     | :status             | 200
...
```

**Dynamic table** (learned during connection):
```
Index | Header Name         | Header Value
------|---------------------|-------------
0     | cache-control       | max-age=3600
1     | content-type        | application/json
2     | x-custom-header     | custom-value
```

**Encoded header block**:
```
Original headers:
  :method: GET
  :scheme: https
  :authority: example.com
  :path: /api/users
  cache-control: max-age=3600

QPACK encoding:
  0x2000  (Static table ref: :method GET)
  0x2005  (Static table ref: :scheme https)
  0x50    (Literal: :authority example.com)
  0x51    (Literal: :path /api/users)
  0x8000  (Dynamic table ref: cache-control max-age=3600)

Result: ~20 bytes (vs 100+ bytes uncompressed)
```

### QPACK Configuration

```python
# HTTP/3 SETTINGS
settings = {
    "QPACK_MAX_TABLE_CAPACITY": 4096,      # Dynamic table size
    "QPACK_BLOCKED_STREAMS": 100,          # Max blocked streams
}
```

---

## Connection Migration

### Migration Scenarios

**1. NAT rebinding**:
```
Client                    NAT                    Server
  |                        |                        |
  |-- Packet (Port 5000) -->|-- Packet (Port 60000) -->|
  |                        |                        |
  [NAT timeout/rebinding]
  |                        |                        |
  |-- Packet (Port 5000) -->|-- Packet (Port 60001) -->|
  |                        |                        |

Result: Connection continues (same Connection ID)
```

**2. Network switch**:
```
Mobile Device:
  WiFi (192.168.1.100) → Cellular (10.0.0.50)

Connection ID: 0xABCD1234

Result: Server sees new source address, validates with PATH_CHALLENGE
```

**3. Load balancer changes**:
```
Client → Load Balancer 1 → Server 1
[Load balancer routes to different server]
Client → Load Balancer 2 → Server 2

Connection ID routing ensures packets reach correct server
```

### Path Validation

**PATH_CHALLENGE / PATH_RESPONSE**:

```
Client                    Server
  |                         |
  |-- Packet (New path) ---->|
  |   PATH_CHALLENGE(data)  |
  |                         |
  |<-- PATH_RESPONSE(data) --|  (Echoes data)
  |                         |

Result: New path validated
        Traffic switches to new path
```

### Connection ID Management

**NEW_CONNECTION_ID frame**:

```
Server → Client: NEW_CONNECTION_ID
  Sequence Number: 5
  Retire Prior To: 3
  Connection ID: 0x9876543210ABCDEF
  Stateless Reset Token: 0x...

Result: Client can use new Connection ID
        Client retires Connection IDs 0-2
```

**Benefits**:
- **Privacy**: Rotate connection IDs to prevent tracking
- **Load balancing**: New connection ID routes to different server
- **Migration**: Use different connection IDs on different paths

---

## Performance Characteristics

### Latency Improvements

**Connection establishment**:
```
HTTP/2:
  TCP handshake: 1 RTT
  TLS handshake: 1-2 RTT
  First request: 2-3 RTT total

HTTP/3:
  QUIC handshake: 1 RTT (first connection)
  QUIC handshake: 0 RTT (resumed connection)
  First request: 0-1 RTT total
```

**Improvement**: 50-66% faster connection establishment

### Throughput and Loss Recovery

**Packet loss impact**:

```
HTTP/2 (1% packet loss):
  TCP retransmits lost packet
  All streams blocked until retransmission
  Throughput: 50-80% of ideal

HTTP/3 (1% packet loss):
  QUIC retransmits lost data
  Only affected stream blocked
  Throughput: 90-95% of ideal
```

**Improvement**: 10-40% better throughput under packet loss

### Real-World Performance

**Cloudflare study** (2020):
```
Desktop (WiFi):
  HTTP/2: 100 ms TTFB
  HTTP/3: 95 ms TTFB (-5%)

Mobile (4G):
  HTTP/2: 250 ms TTFB
  HTTP/3: 200 ms TTFB (-20%)

Mobile (3G, high loss):
  HTTP/2: 800 ms TTFB
  HTTP/3: 500 ms TTFB (-37%)
```

**Google study** (YouTube):
```
HTTP/3 rebuffering reduction:
  - 9% fewer rebuffers on desktop
  - 15% fewer rebuffers on mobile
```

### CPU and Memory

**CPU overhead**:
```
HTTP/2 (TCP + TLS):
  - Kernel TCP processing
  - Userspace TLS encryption

HTTP/3 (QUIC):
  - Userspace QUIC processing (higher CPU)
  - Integrated TLS encryption

Result: HTTP/3 uses 10-30% more CPU (but improving)
```

**Memory overhead**:
```
HTTP/2:
  - TCP buffers (kernel)
  - TLS buffers (userspace)

HTTP/3:
  - QUIC buffers (userspace)
  - Per-stream buffers

Result: HTTP/3 uses similar memory (slightly higher)
```

---

## Server Implementation

### nginx with QUIC

**nginx QUIC module** (mainline branch):

```nginx
# nginx.conf
http {
    server {
        # HTTP/3
        listen 443 quic reuseport;

        # HTTP/2 (fallback)
        listen 443 ssl http2;

        server_name example.com;

        # TLS certificates
        ssl_certificate /path/to/cert.pem;
        ssl_certificate_key /path/to/key.pem;

        # SSL protocols
        ssl_protocols TLSv1.3;

        # QUIC settings
        quic_retry on;
        quic_gso on;

        # Add Alt-Svc header (advertise HTTP/3)
        add_header Alt-Svc 'h3=":443"; ma=86400';

        location / {
            root /var/www/html;
            index index.html;
        }
    }
}
```

**Build nginx with QUIC**:
```bash
# Install dependencies
apt-get install build-essential libssl-dev zlib1g-dev libpcre3-dev

# Clone nginx with QUIC
git clone https://github.com/nginx/nginx.git
cd nginx

# Configure
./auto/configure \
    --with-http_v3_module \
    --with-http_quic_module \
    --with-stream_quic_module \
    --with-http_ssl_module

# Build
make -j$(nproc)
make install
```

### Cloudflare quiche

**quiche** is a Rust QUIC implementation:

```rust
use quiche;

// Create QUIC config
let mut config = quiche::Config::new(quiche::PROTOCOL_VERSION)?;

// Set TLS certificates
config.load_cert_chain_from_pem_file("cert.pem")?;
config.load_priv_key_from_pem_file("key.pem")?;

// Configure HTTP/3
config.set_application_protos(&[b"h3", b"h3-29"])?;

// Set QUIC parameters
config.set_max_idle_timeout(5000);
config.set_max_recv_udp_payload_size(1350);
config.set_max_send_udp_payload_size(1350);
config.set_initial_max_data(10_000_000);
config.set_initial_max_stream_data_bidi_local(1_000_000);
config.set_initial_max_stream_data_bidi_remote(1_000_000);
config.set_initial_max_streams_bidi(100);
config.set_cc_algorithm(quiche::CongestionControlAlgorithm::BBR);

// Create connection
let scid = quiche::ConnectionId::from_ref(&scid);
let mut conn = quiche::accept(&scid, None, local, peer, &mut config)?;

// Process packets
loop {
    let (len, from) = socket.recv_from(&mut buf)?;

    let recv_info = quiche::RecvInfo { from };

    conn.recv(&mut buf[..len], recv_info)?;

    // Process HTTP/3
    if conn.is_established() {
        // Handle HTTP/3 requests
    }

    // Send packets
    loop {
        let (write, send_info) = conn.send(&mut out)?;
        socket.send_to(&out[..write], send_info.to)?;
    }
}
```

### Go with quic-go

**quic-go** HTTP/3 server:

```go
package main

import (
    "crypto/tls"
    "log"
    "net/http"

    "github.com/quic-go/quic-go/http3"
)

func main() {
    // HTTP handler
    mux := http.NewServeMux()
    mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        w.Write([]byte("Hello from HTTP/3!"))
    })

    // TLS config
    tlsConfig := &tls.Config{
        Certificates: loadCertificates(),
        NextProtos:   []string{"h3"},
    }

    // HTTP/3 server
    server := &http3.Server{
        Addr:      ":443",
        Handler:   mux,
        TLSConfig: tlsConfig,
        QuicConfig: &quic.Config{
            MaxIdleTimeout:  5 * time.Minute,
            MaxIncomingStreams: 100,
            EnableDatagrams: false,
        },
    }

    log.Println("Starting HTTP/3 server on :443")
    if err := server.ListenAndServe(); err != nil {
        log.Fatal(err)
    }
}

func loadCertificates() []tls.Certificate {
    cert, err := tls.LoadX509KeyPair("cert.pem", "key.pem")
    if err != nil {
        log.Fatal(err)
    }
    return []tls.Certificate{cert}
}
```

### Python with aioquic

**aioquic** HTTP/3 server:

```python
import asyncio
from aioquic.asyncio import serve
from aioquic.h3.connection import H3Connection
from aioquic.h3.events import HeadersReceived, DataReceived
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent

class HttpRequestHandler:
    def __init__(self, scope):
        self.scope = scope
        self.body = b""

    def http_event_received(self, event):
        if isinstance(event, HeadersReceived):
            # Parse headers
            headers = dict(event.headers)
            path = headers.get(b":path", b"/").decode()

            # Send response
            response_headers = [
                (b":status", b"200"),
                (b"content-type", b"text/html"),
            ]
            response_body = b"<html><body>Hello from HTTP/3!</body></html>"

            return response_headers, response_body

        elif isinstance(event, DataReceived):
            self.body += event.data

async def main():
    # QUIC configuration
    configuration = QuicConfiguration(
        alpn_protocols=["h3", "h3-29"],
        is_client=False,
        max_datagram_frame_size=65536,
    )

    # Load certificates
    configuration.load_cert_chain("cert.pem", "key.pem")

    # Start server
    await serve(
        host="0.0.0.0",
        port=443,
        configuration=configuration,
        create_protocol=HttpRequestHandler,
    )

    await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Client Implementation

### curl with HTTP/3

**curl** with HTTP/3 support (7.66+):

```bash
# Install curl with HTTP/3 (using quiche)
git clone --recursive https://github.com/curl/curl.git
cd curl

# Build with quiche
./buildconf
./configure --with-openssl --with-quiche=/path/to/quiche
make
make install

# Test HTTP/3
curl --http3 https://cloudflare-quic.com
curl --http3 https://www.google.com

# Verbose output
curl --http3 -v https://example.com

# Force HTTP/3 (fail if not available)
curl --http3-only https://example.com

# Check protocol
curl -I --http3 https://example.com | grep -i alt-svc
```

### Python Client

**aioquic HTTP/3 client**:

```python
import asyncio
from aioquic.asyncio import connect
from aioquic.h3.connection import H3Connection
from aioquic.quic.configuration import QuicConfiguration

async def fetch_http3(url):
    # Parse URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 443
    path = parsed.path or "/"

    # QUIC configuration
    configuration = QuicConfiguration(
        alpn_protocols=["h3"],
        is_client=True,
    )

    # Connect
    async with connect(host, port, configuration=configuration) as client:
        # Create HTTP/3 connection
        http = H3Connection(client._quic)

        # Send request
        stream_id = client._quic.get_next_available_stream_id()

        headers = [
            (b":method", b"GET"),
            (b":scheme", b"https"),
            (b":authority", host.encode()),
            (b":path", path.encode()),
        ]

        http.send_headers(stream_id, headers)

        # Receive response
        response_headers = await http.receive_headers(stream_id)
        response_body = await http.receive_data(stream_id)

        print(f"Status: {dict(response_headers)[b':status']}")
        print(f"Body: {response_body.decode()}")

# Usage
asyncio.run(fetch_http3("https://cloudflare-quic.com"))
```

### Go Client

**quic-go HTTP/3 client**:

```go
package main

import (
    "crypto/tls"
    "fmt"
    "io"
    "log"
    "net/http"

    "github.com/quic-go/quic-go/http3"
)

func main() {
    // HTTP/3 client
    client := &http.Client{
        Transport: &http3.RoundTripper{
            TLSClientConfig: &tls.Config{
                InsecureSkipVerify: false,
            },
        },
    }

    // Make request
    resp, err := client.Get("https://cloudflare-quic.com")
    if err != nil {
        log.Fatal(err)
    }
    defer resp.Body.Close()

    // Read response
    body, err := io.ReadAll(resp.Body)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Status: %s\n", resp.Status)
    fmt.Printf("Protocol: %s\n", resp.Proto)
    fmt.Printf("Body: %s\n", body)
}
```

### JavaScript (Browser)

**Browsers with HTTP/3**:

```javascript
// Modern browsers automatically use HTTP/3 if available

// Check if HTTP/3 is supported
fetch('https://cloudflare-quic.com')
  .then(response => {
    // Check protocol (Chrome DevTools → Network → Protocol column)
    console.log('Protocol:', response.headers.get('alt-svc'));
  });

// No special code needed - browser handles protocol negotiation
// Uses Alt-Svc header to discover HTTP/3 support
```

**Check HTTP/3 usage**:
```javascript
// Chrome DevTools → Network → Filter: "All" → Protocol column shows "h3"

// Performance API
performance.getEntriesByType('navigation').forEach(entry => {
  console.log('Next Hop Protocol:', entry.nextHopProtocol);
  // Output: "h3" for HTTP/3
});
```

---

## CDN and Edge Deployment

### Cloudflare

**Cloudflare** enables HTTP/3 by default:

```bash
# No configuration needed - automatic

# Check if enabled
curl -I https://example.com
# Look for: alt-svc: h3=":443"; ma=86400
```

**Enable via dashboard**:
```
Dashboard → Speed → Optimization
  → Enable HTTP/3 (QUIC)
```

**API**:
```bash
curl -X PATCH "https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/http3" \
  -H "Authorization: Bearer {token}" \
  -d '{"value":"on"}'
```

### Fastly

**Fastly HTTP/3**:

```vcl
# Fastly VCL
backend F_origin {
  .dynamic = true;
  .port = "443";
  .host = "origin.example.com";
  .ssl = true;
  .ssl_sni_hostname = "origin.example.com";
  .first_byte_timeout = 60s;
  .between_bytes_timeout = 10s;
}

sub vcl_recv {
  # Enable HTTP/3
  set req.http.Fastly-SSL = "1";
}

sub vcl_deliver {
  # Advertise HTTP/3
  set resp.http.Alt-Svc = "h3=\":443\"; ma=86400";
}
```

### AWS CloudFront

**CloudFront HTTP/3** (enabled in distribution):

```bash
# AWS CLI
aws cloudfront update-distribution \
  --id {distribution-id} \
  --distribution-config '{
    "HttpVersion": "http3",
    ...
  }'
```

**CloudFormation**:
```yaml
Resources:
  Distribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        HttpVersion: http3
        Origins:
          - Id: S3Origin
            DomainName: bucket.s3.amazonaws.com
```

### Google Cloud CDN

**Cloud CDN HTTP/3**:

```bash
# gcloud CLI
gcloud compute backend-services update {backend-service} \
  --enable-http3
```

---

## Testing and Debugging

### Testing Tools

**quic-go interop**:
```bash
# Run interop tests
docker run -it --rm \
  -v /path/to/certs:/certs \
  martenseemann/quic-network-simulator
```

**h3spec** (HTTP/3 conformance):
```bash
# Install
go install github.com/kazu-yamamoto/h3spec@latest

# Test server
h3spec -h localhost -p 443 -k
```

**qlog** (QUIC logging):
```json
{
  "qlog_version": "draft-02",
  "traces": [{
    "vantage_point": {"type": "client"},
    "events": [
      {
        "time": 0,
        "name": "transport:packet_sent",
        "data": {
          "packet_type": "initial",
          "header": {"packet_number": 0},
          "frames": [{"frame_type": "crypto"}]
        }
      }
    ]
  }]
}
```

### Debugging Commands

**tcpdump**:
```bash
# Capture UDP port 443 (QUIC)
tcpdump -i any -n udp port 443 -w quic.pcap

# Wireshark
wireshark quic.pcap
# Analyze → Decode As → UDP → QUIC
```

**Chrome NetLog**:
```
chrome://net-export/
# Start logging
# Visit HTTP/3 site
# Stop logging
# Analyze with https://netlog-viewer.appspot.com
```

**curl verbose**:
```bash
curl -v --http3 https://example.com

# Output shows:
# * QUIC cipher selection: TLS_AES_128_GCM_SHA256
# * SSL connection using QUICv1
# * ALPN: server accepted h3
# > GET / HTTP/3
```

---

## Migration Strategies

### Progressive Rollout

**Phase 1: Enable HTTP/3 (keep HTTP/2 fallback)**:
```nginx
server {
    listen 443 quic reuseport;      # HTTP/3
    listen 443 ssl http2;            # HTTP/2 fallback

    add_header Alt-Svc 'h3=":443"; ma=86400';
}
```

**Phase 2: Monitor metrics**:
```
Metrics to track:
- HTTP/3 adoption rate (% of requests)
- Latency (P50, P95, P99)
- Error rate
- CPU/memory usage
- Connection success rate
```

**Phase 3: Optimize**:
```nginx
# Tune QUIC parameters
quic_gso on;
quic_retry on;
ssl_early_data on;

# Increase UDP buffer sizes
sysctl -w net.core.rmem_max=2500000
sysctl -w net.core.wmem_max=2500000
```

### Compatibility Testing

**Test matrix**:
```
Browsers:
- Chrome 87+ (HTTP/3 GA)
- Firefox 88+ (HTTP/3 enabled)
- Safari 14+ (experimental)
- Edge 87+

Clients:
- curl 7.66+
- wget 1.21+
- Python requests (via aioquic)

Servers:
- nginx (QUIC branch)
- Cloudflare (quiche)
- LiteSpeed
- Caddy 2.0+
```

### Fallback Strategy

**Alt-Svc advertisement**:
```
HTTP/2 response:
  Alt-Svc: h3=":443"; ma=86400

Client behavior:
1. Connect via HTTP/2 (first visit)
2. Receive Alt-Svc header
3. Cache HTTP/3 endpoint for 86400 seconds
4. Next request: Try HTTP/3
5. If HTTP/3 fails: Fall back to HTTP/2
```

**Failure handling**:
```
HTTP/3 connection failure scenarios:
- UDP blocked (firewall/middlebox)
- QUIC not supported (old client)
- TLS 1.3 not available
- Certificate mismatch

Fallback:
- Client retries with HTTP/2
- Server continues serving HTTP/2
- No user-visible error
```

---

## Anti-Patterns

### Common Mistakes

❌ **Not advertising HTTP/3** (missing Alt-Svc header)
```nginx
# BAD: No Alt-Svc header
server {
    listen 443 quic;
}
```
✅ **Advertise HTTP/3**:
```nginx
server {
    listen 443 quic;
    add_header Alt-Svc 'h3=":443"; ma=86400';
}
```

❌ **Blocking UDP port 443**
```bash
# BAD: Firewall blocks UDP
iptables -A INPUT -p udp --dport 443 -j DROP
```
✅ **Allow UDP 443**:
```bash
iptables -A INPUT -p udp --dport 443 -j ACCEPT
```

❌ **Using 0-RTT for non-idempotent requests**
```python
# BAD: POST with 0-RTT (replay attack risk)
connection.send_0rtt()
stream.write(b"POST /api/payment ...")
```
✅ **Use 0-RTT only for safe methods**:
```python
# GOOD: GET with 0-RTT
connection.send_0rtt()
stream.write(b"GET /api/data ...")
```

❌ **Ignoring UDP buffer sizes**
```nginx
# BAD: Default UDP buffers (too small)
# No tuning
```
✅ **Increase UDP buffers**:
```bash
sysctl -w net.core.rmem_max=2500000
sysctl -w net.core.wmem_max=2500000
```

❌ **No HTTP/2 fallback**
```nginx
# BAD: HTTP/3 only (breaks for incompatible clients)
server {
    listen 443 quic;
}
```
✅ **Always provide HTTP/2 fallback**:
```nginx
server {
    listen 443 quic;
    listen 443 ssl http2;
}
```

❌ **Copying TCP congestion control settings**
```
# BAD: Using TCP BBR sysctl for QUIC
sysctl -w net.ipv4.tcp_congestion_control=bbr
```
✅ **Use QUIC-specific congestion control**:
```python
config = QuicConfiguration(
    congestion_control_algorithm="bbr"
)
```

❌ **Not handling connection migration**
```python
# BAD: Binding connection to IP address
if connection.peer_address != original_address:
    raise Exception("Address changed!")
```
✅ **Accept connection migration**:
```python
# Validate new path with PATH_CHALLENGE
if connection.path_changed():
    connection.validate_path()
```

---

## References

### RFCs

- **RFC 9000**: QUIC: A UDP-Based Multiplexed and Secure Transport
- **RFC 9001**: Using TLS to Secure QUIC
- **RFC 9002**: QUIC Loss Detection and Congestion Control
- **RFC 9114**: HTTP/3
- **RFC 9204**: QPACK: Field Compression for HTTP/3
- **RFC 9218**: Extensible Prioritization Scheme for HTTP

### Implementations

**Servers**:
- nginx (https://nginx.org/en/docs/quic.html)
- quiche (https://github.com/cloudflare/quiche)
- aioquic (https://github.com/aiortc/aioquic)
- quic-go (https://github.com/quic-go/quic-go)
- LiteSpeed (https://www.litespeedtech.com/products/litespeed-web-server)

**Clients**:
- curl (https://curl.se/docs/http3.html)
- Chrome (built-in)
- Firefox (built-in)
- Safari (experimental)

### Tools

- **qlog**: QUIC logging format (https://qlog.edm.uhasselt.be/)
- **h3spec**: HTTP/3 conformance testing (https://github.com/kazu-yamamoto/h3spec)
- **Wireshark**: QUIC protocol dissector (https://www.wireshark.org/)
- **Chrome NetLog**: Network logging (chrome://net-export/)

### Performance Studies

- Cloudflare HTTP/3 Performance (https://blog.cloudflare.com/http-3-vs-http-2/)
- Google QUIC Deployment (https://www.chromium.org/quic)
- Meta HTTP/3 at Scale (https://engineering.fb.com/2020/10/21/networking-traffic/how-facebook-is-bringing-quic-to-billions/)

---

**End of Reference** (3,847 lines)
