---
name: protocols-quic-protocol
description: QUIC protocol deep dive including transport layer, streams, connection ID, loss recovery, and congestion control
---

# QUIC Protocol

**Scope**: QUIC transport protocol, streams, connection management, loss recovery, congestion control
**Lines**: ~300
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Implementing QUIC-based applications
- Understanding HTTP/3 internals
- Building custom QUIC applications
- Optimizing network performance
- Working with UDP-based protocols
- Implementing connection migration
- Debugging QUIC connections
- Understanding modern transport protocols

## Core Concepts

### QUIC Architecture

**Layer Positioning**:
```
Application (HTTP/3, custom protocols)
         ↓
    QUIC Transport
         ↓
        UDP
         ↓
        IP
```

**QUIC vs TCP+TLS**:
```
TCP+TLS:           QUIC:
┌──────────┐      ┌──────────┐
│  HTTP    │      │  HTTP/3  │
├──────────┤      ├──────────┤
│   TLS    │      │   QUIC   │ ← Integrated crypto
├──────────┤      │  (UDP)   │ ← User-space control
│   TCP    │      └──────────┘
└──────────┘
```

### Connection ID

**Purpose**: Identify connections independent of IP/port

```
Traditional TCP:
Connection = (SrcIP, SrcPort, DstIP, DstPort)
└─> Changes when IP/port changes

QUIC:
Connection = Connection ID (64-bit)
└─> Remains same across network changes
```

**Connection Migration Example**:
```
Client          Server
  |               |
  | WiFi IP: 10.0.1.5, Conn ID: abc123
  |───────────────|
  |               |
  | (Switch to 4G, new IP: 192.168.1.100)
  |               |
  | 4G IP: 192.168.1.100, Conn ID: abc123
  |───────────────|  ← Same connection!
  |               |
```

### Streams

**Multiplexed, Independent Streams**:
```
QUIC Connection
├── Stream 0 (HTTP request /api/users)
├── Stream 4 (HTTP request /api/posts)
├── Stream 8 (HTTP request /api/comments)
└── Stream 12 (HTTP request /api/likes)

If Stream 4 loses packets → only Stream 4 blocks
All other streams continue unaffected
```

**Stream Types**:
- **Bidirectional**: Client-initiated (0, 4, 8...)
- **Bidirectional**: Server-initiated (1, 5, 9...)
- **Unidirectional**: Client-initiated (2, 6, 10...)
- **Unidirectional**: Server-initiated (3, 7, 11...)

**Go Implementation**:
```go
import "github.com/lucas-clemente/quic-go"

// Open bidirectional stream
stream, err := session.OpenStreamSync(ctx)
if err != nil {
    return err
}

// Send data
_, err = stream.Write([]byte("Hello QUIC"))

// Receive response
buf := make([]byte, 1024)
n, err := stream.Read(buf)

// Close stream
stream.Close()
```

### Packet Types

**Long Header Packets** (connection establishment):
- **Initial**: First packet, contains crypto handshake
- **0-RTT**: Early data (if resuming)
- **Handshake**: Complete handshake
- **Retry**: Server asks client to retry (DDoS protection)

**Short Header Packets** (normal data):
- Encrypted application data
- Smaller header (1 byte + Conn ID)
- Most packets during connection

**Packet Structure**:
```
Long Header:
+---+---+---+---+---+---+---+---+
|1|1| Type  |  Reserved | Ver   |
+---+---+---+---+---+---+---+---+
|   Destination Conn ID (0-160) |
+-------------------------------+
|      Source Conn ID (0-160)   |
+-------------------------------+
|          Packet Number         |
+-------------------------------+
|          Payload ...           |

Short Header:
+---+---+---+---+---+---+---+---+
|0|1|Spin|  Reserved | Key Phase |
+---+---+---+---+---+---+---+---+
|   Destination Conn ID (0-160) |
+-------------------------------+
|          Packet Number         |
+-------------------------------+
|          Payload ...           |
```

### Loss Recovery

**Fast Retransmit**:
```
Sent: P1, P2, P3, P4, P5
Received: ACK(P1), ACK(P3), ACK(P4), ACK(P5)
└─> P2 missing after 3 ACKs → retransmit P2
```

**Probe Timeout**:
```rust
use std::time::{Duration, Instant};

struct QUICLossDetection {
    rtt: Duration,
    rttvar: Duration,
    pto_count: u32,
}

impl QUICLossDetection {
    fn calculate_pto(&self) -> Duration {
        // PTO = SRTT + max(4*RTTVAR, kGranularity) + max_ack_delay
        let pto = self.rtt + 4 * self.rttvar + Duration::from_millis(1);

        // Exponential backoff
        pto * 2_u32.pow(self.pto_count)
    }

    fn on_timeout(&mut self) {
        // Retransmit probe packet
        self.pto_count += 1;
    }

    fn on_ack(&mut self, acked_packet: &Packet) {
        // Update RTT, reset PTO count
        self.update_rtt(acked_packet);
        self.pto_count = 0;
    }
}
```

### Congestion Control

**QUIC Congestion Control**:
- Similar to TCP (Cubic, BBR)
- Per-connection, not per-stream
- Explicit Congestion Notification (ECN) support
- Improved fast recovery

```python
class QUICCongestionControl:
    def __init__(self):
        self.cwnd = 10 * MTU  # Congestion window
        self.ssthresh = float('inf')  # Slow start threshold
        self.in_recovery = False

    def on_ack(self, acked_bytes):
        if self.cwnd < self.ssthresh:
            # Slow start
            self.cwnd += acked_bytes
        else:
            # Congestion avoidance
            self.cwnd += (MTU * acked_bytes) // self.cwnd

    def on_loss(self):
        if not self.in_recovery:
            # Enter recovery
            self.ssthresh = self.cwnd // 2
            self.cwnd = self.ssthresh
            self.in_recovery = True

    def can_send(self, bytes_in_flight):
        return bytes_in_flight < self.cwnd
```

---

## Patterns

### Pattern 1: Custom Application Protocol

**Use Case**: Build application on QUIC (not HTTP)

```rust
use quiche::Config;

// Custom QUIC application
async fn custom_protocol() -> Result<()> {
    let mut config = Config::new(quiche::PROTOCOL_VERSION)?;
    config.set_application_protos(b"\x0cmyapp-proto")?;

    let conn = quiche::connect(
        Some("server.com"),
        &scid,
        local,
        peer,
        &mut config,
    )?;

    // Open stream
    conn.stream_send(4, b"CUSTOM_COMMAND: data", true)?;

    // Receive response
    let mut buf = [0; 1024];
    let (len, fin) = conn.stream_recv(4, &mut buf)?;

    Ok(())
}
```

### Pattern 2: Connection Migration Handling

**Use Case**: Handle network switches gracefully

```go
func handleConnectionMigration(conn quic.Connection) {
    // Monitor path changes
    go func() {
        for {
            select {
            case <-conn.Context().Done():
                return
            default:
                // QUIC handles migration automatically
                // Application continues uninterrupted
                time.Sleep(100 * time.Millisecond)
            }
        }
    }()
}
```

---

## Implementation Example

**Python QUIC Server** (aioquic):
```python
import asyncio
from aioquic.asyncio import serve
from aioquic.quic.configuration import QuicConfiguration

class MyQUICProtocol:
    def __init__(self, scope):
        self.scope = scope

    async def handle_stream(self, stream_id, data):
        # Process data on stream
        response = b"Response data"

        # Send response
        self.scope["connection"].send_stream_data(
            stream_id, response, end_stream=True
        )

async def main():
    config = QuicConfiguration(
        alpn_protocols=["myapp"],
        is_client=False,
    )
    config.load_cert_chain("cert.pem", "key.pem")

    await serve(
        "0.0.0.0",
        4433,
        configuration=config,
        create_protocol=MyQUICProtocol,
    )

asyncio.run(main())
```

---

## Best Practices

### 1. Use Connection IDs

```rust
// ✅ Good: Support connection ID rotation
config.set_max_idle_timeout(30_000);  // 30s
config.set_max_connection_id_lifetime(10_000);  // Rotate every 10s
```

### 2. Handle 0-RTT Carefully

```go
// ❌ Bad: Non-idempotent operation in 0-RTT
if conn.ConnectionState().Used0RTT {
    processPayment()  // Could be replayed!
}

// ✅ Good: Only idempotent operations
if conn.ConnectionState().Used0RTT {
    fetchUserData()  // Safe to replay
}
```

---

## Related Skills

- `protocols-http3-quic` - HTTP/3 over QUIC
- `protocols-udp-fundamentals` - UDP basics
- `protocols-tcp-fundamentals` - TCP comparison
- `networking-network-resilience-patterns` - Resilience patterns

---

**Last Updated**: 2025-10-27
