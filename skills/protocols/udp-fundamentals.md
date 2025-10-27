---
name: protocols-udp-fundamentals
description: UDP protocol fundamentals including connectionless communication, use cases, and trade-offs vs TCP
---

# UDP Fundamentals

**Scope**: UDP protocol, connectionless communication, packet structure, use cases
**Lines**: ~280
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building real-time applications (gaming, VoIP, video streaming)
- Implementing DNS, DHCP, or other UDP-based protocols
- Designing QUIC or WebRTC applications
- Optimizing for low latency over reliability
- Broadcasting or multicasting data
- Understanding protocol trade-offs
- Debugging UDP communication
- Implementing custom reliability on top of UDP

## Core Concepts

### UDP vs TCP

**TCP**: Connection-oriented, reliable, ordered
```
Features:
✓ Connection establishment (3-way handshake)
✓ Guaranteed delivery (retransmission)
✓ In-order delivery
✓ Flow control
✓ Congestion control
✗ Higher latency
✗ More overhead
```

**UDP**: Connectionless, unreliable, unordered
```
Features:
✓ No connection setup
✓ Low latency
✓ Simple header (8 bytes)
✓ Broadcast/multicast support
✗ No delivery guarantee
✗ No ordering
✗ No flow control
✗ No congestion control
```

**Packet Comparison**:
```
TCP Header: 20-60 bytes
UDP Header: 8 bytes

TCP Overhead: Handshake + retransmissions + ACKs
UDP Overhead: None
```

### UDP Packet Structure

```
 0      7 8     15 16    23 24    31
+--------+--------+--------+--------+
|     Source      |   Destination   |
|      Port       |       Port      |
+--------+--------+--------+--------+
|     Length      |    Checksum     |
+--------+--------+--------+--------+
|          Data (Payload)           |
+-----------------------------------+
```

**Fields**:
- **Source Port** (16 bits): Sender's port (optional, can be 0)
- **Destination Port** (16 bits): Receiver's port
- **Length** (16 bits): Header + data length
- **Checksum** (16 bits): Optional error checking
- **Data**: Application payload

**Maximum Size**: 65,507 bytes (65,535 - 8 byte header - 20 byte IP header)

### Connectionless Communication

```
Client                        Server
  |                              |
  |-- UDP Packet 1 ------------->|  No handshake!
  |-- UDP Packet 2 ------------->|
  |-- UDP Packet 3 ----X         |  Packet lost (no retry)
  |                              |
```

**No State**:
- Server doesn't track clients
- No connection resources consumed
- Clients can appear/disappear
- Ideal for stateless protocols (DNS)

---

## Use Cases

### 1. DNS Queries

**Why UDP**:
- Simple request/response
- Small payload (usually < 512 bytes)
- Fast is more important than perfect
- Falls back to TCP if needed

```python
import socket

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2.0)

# DNS query for example.com
dns_query = b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00' \
            b'\x07example\x03com\x00\x00\x01\x00\x01'

# Send to DNS server (no connection)
sock.sendto(dns_query, ('8.8.8.8', 53))

# Receive response (or timeout)
try:
    response, server = sock.recvfrom(512)
    print(f"Got DNS response: {len(response)} bytes")
except socket.timeout:
    print("DNS query timed out")
```

### 2. Real-Time Gaming

**Why UDP**:
- Low latency critical
- Old position data is useless (drop it)
- Can tolerate some packet loss
- High packet rate

```rust
use std::net::UdpSocket;

fn game_loop() -> std::io::Result<()> {
    let socket = UdpSocket::bind("0.0.0.0:0")?;
    socket.connect("game-server.com:9000")?;

    loop {
        // Send player position (lossy OK)
        let pos = format!("POS:x={},y={},z={}", x, y, z);
        socket.send(pos.as_bytes())?;

        // Receive game state (non-blocking)
        socket.set_nonblocking(true)?;
        let mut buf = [0u8; 1024];
        match socket.recv(&mut buf) {
            Ok(n) => process_game_state(&buf[..n]),
            Err(_) => {} // No data yet, keep going
        }

        // 60 FPS tick rate
        thread::sleep(Duration::from_millis(16));
    }
}
```

### 3. Video Streaming (RTP)

**Why UDP**:
- Real-time delivery critical
- Old frames are useless
- Slight quality degradation OK
- Bandwidth optimization

```go
package main

import "net"

func streamVideo() {
    // UDP socket for RTP
    conn, _ := net.Dial("udp", "viewer:5004")
    defer conn.Close()

    for frame := range videoFrames {
        // Send frame (if it's lost, skip it)
        rtpPacket := encodeRTP(frame)
        conn.Write(rtpPacket)

        // Don't wait for ACK - keep streaming!
    }
}
```

### 4. Broadcast/Multicast

**Why UDP**: TCP doesn't support broadcast

```python
import socket

# Create broadcast socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Broadcast discovery message
message = b"DISCOVER_SERVICE"
sock.sendto(message, ('<broadcast>', 9999))

# All hosts on network receive this
```

---

## Patterns

### Pattern 1: Reliability on Top of UDP

**Use Case**: Want UDP speed with some reliability (QUIC, WebRTC)

```python
import socket
import time

class ReliableUDP:
    def __init__(self, sock):
        self.sock = sock
        self.seq_num = 0
        self.pending_acks = {}

    def send_reliable(self, data, addr):
        packet = {
            'seq': self.seq_num,
            'data': data,
            'timestamp': time.time()
        }

        # Send packet
        self.sock.sendto(json.dumps(packet).encode(), addr)
        self.pending_acks[self.seq_num] = packet
        self.seq_num += 1

        # Retransmit if no ACK after timeout
        self.check_retransmissions()

    def receive_with_ack(self):
        data, addr = self.sock.recvfrom(1024)
        packet = json.loads(data.decode())

        # Send ACK
        ack = {'ack': packet['seq']}
        self.sock.sendto(json.dumps(ack).encode(), addr)

        return packet['data'], addr

    def check_retransmissions(self):
        now = time.time()
        for seq, packet in self.pending_acks.items():
            if now - packet['timestamp'] > 1.0:  # 1s timeout
                # Retransmit
                self.sock.sendto(json.dumps(packet).encode(), last_addr)
                packet['timestamp'] = now
```

### Pattern 2: Rate Limiting

**Use Case**: Prevent network flooding

```go
package main

import (
    "net"
    "time"
    "golang.org/x/time/rate"
)

func sendWithRateLimit() {
    conn, _ := net.Dial("udp", "server:8000")
    limiter := rate.NewLimiter(rate.Limit(100), 10) // 100 packets/sec, burst 10

    for _, packet := range packets {
        // Wait for rate limit
        limiter.Wait(context.Background())

        // Send packet
        conn.Write(packet)
    }
}
```

### Pattern 3: Packet Sequence Numbers

**Use Case**: Detect packet loss and reordering

```rust
use std::collections::HashMap;

struct UDPReceiver {
    expected_seq: u32,
    buffer: HashMap<u32, Vec<u8>>,
}

impl UDPReceiver {
    fn receive_packet(&mut self, packet: &[u8]) {
        let seq = u32::from_be_bytes(packet[0..4].try_into().unwrap());
        let data = packet[4..].to_vec();

        if seq == self.expected_seq {
            // In-order packet
            self.process_data(&data);
            self.expected_seq += 1;

            // Check buffer for next packets
            while let Some(buffered) = self.buffer.remove(&self.expected_seq) {
                self.process_data(&buffered);
                self.expected_seq += 1;
            }
        } else if seq > self.expected_seq {
            // Out-of-order - buffer it
            self.buffer.insert(seq, data);
        }
        // If seq < expected_seq, it's a duplicate - ignore
    }
}
```

---

## Best Practices

### 1. Handle Packet Loss

```python
# ❌ Bad: Assuming delivery
sock.sendto(critical_data, addr)
# What if it's lost?

# ✅ Good: Application-level ACKs
send_with_ack(sock, critical_data, addr, retries=3)
```

### 2. Implement Timeouts

```go
// ✅ Good: Always set read timeout
conn.SetReadDeadline(time.Now().Add(5 * time.Second))
_, err := conn.Read(buffer)
if err != nil {
    // Handle timeout or error
}
```

### 3. Respect MTU

```python
# ❌ Bad: Large UDP packets (fragmentation)
large_packet = b"x" * 10000
sock.sendto(large_packet, addr)  # May fragment or drop

# ✅ Good: Keep packets < 1400 bytes
MAX_UDP_PAYLOAD = 1400
for chunk in chunks(data, MAX_UDP_PAYLOAD):
    sock.sendto(chunk, addr)
```

---

## Troubleshooting

### Issue 1: Packets Not Received

**Check firewall**:
```bash
# Allow UDP port
sudo iptables -A INPUT -p udp --dport 9000 -j ACCEPT

# Test UDP connectivity
nc -u -v server.com 9000
```

### Issue 2: High Packet Loss

**Monitor statistics**:
```bash
# Linux UDP stats
netstat -su | grep -i udp

# Example output:
#   UdpNoPorts: 0
#   UdpInErrors: 157  # Receive errors
#   UdpRcvbufErrors: 0  # Buffer full
```

**Solutions**:
- Increase buffer size
- Reduce send rate
- Implement congestion control

---

## Related Skills

- `protocols-tcp-fundamentals` - TCP comparison
- `protocols-quic-protocol` - QUIC built on UDP
- `protocols-http3-quic` - HTTP/3 using QUIC/UDP
- `realtime-websocket-implementation` - WebSocket over TCP
- `networking-network-protocols` - DNS, DHCP protocols

---

**Last Updated**: 2025-10-27
