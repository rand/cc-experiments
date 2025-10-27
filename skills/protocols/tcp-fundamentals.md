---
name: protocols-tcp-fundamentals
description: TCP protocol fundamentals including three-way handshake, flow control, congestion control, and reliability
---

# TCP Fundamentals

**Scope**: TCP protocol, connection management, flow control, congestion control, reliability mechanisms
**Lines**: ~340
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Understanding TCP/IP networking
- Debugging connection issues
- Optimizing TCP performance
- Implementing TCP servers/clients
- Troubleshooting latency or throughput problems
- Configuring TCP parameters
- Understanding HTTP, HTTP/2, or other TCP-based protocols
- Analyzing network traces with Wireshark

## Core Concepts

### Three-Way Handshake

**Connection Establishment**:
```
Client                        Server
  |                              |
  |-- SYN (seq=x) ------------->|  1. Client initiates
  |                              |
  |<-- SYN-ACK (seq=y, ack=x+1)-|  2. Server acknowledges
  |                              |
  |-- ACK (seq=x+1, ack=y+1)--->|  3. Client confirms
  |                              |
  |<====== DATA TRANSFER =======>|
```

**Flags**:
- **SYN**: Synchronize sequence numbers (connection start)
- **ACK**: Acknowledge received data
- **FIN**: Finish connection (graceful close)
- **RST**: Reset connection (abrupt close)
- **PSH**: Push data to application immediately
- **URG**: Urgent data pointer

**Python Socket Example**:
```python
import socket

# Create TCP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect triggers three-way handshake
sock.connect(('example.com', 80))

# Send HTTP request
sock.sendall(b'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n')

# Receive response
response = sock.recv(4096)
print(response.decode())

# Close connection (FIN handshake)
sock.close()
```

### Flow Control

**Window Size**: Controls how much data sender can send

```
Sender                          Receiver
  |                                |
  |-- Data (seq=1000, len=1000)-->| Window: 4000 bytes
  |-- Data (seq=2000, len=1000)-->| Window: 3000 bytes
  |-- Data (seq=3000, len=1000)-->| Window: 2000 bytes
  |-- Data (seq=4000, len=1000)-->| Window: 1000 bytes
  |                                |
  |   (Must stop - window full)   | Buffer full!
  |                                |
  |<-- ACK (ack=5000, window=2000)| App read 2000 bytes
  |                                |
  |-- Data (seq=5000, len=1000)-->| Can send again
```

**TCP Window**:
- Receiver advertises available buffer space
- Sender cannot exceed receiver's window
- Prevents buffer overflow
- Dynamic adjustment

**Go Example with Buffer Control**:
```go
package main

import (
    "net"
    "syscall"
)

func setTCPBuffers(conn net.Conn) error {
    tcpConn := conn.(*net.TCPConn)
    rawConn, _ := tcpConn.SyscallConn()

    return rawConn.Control(func(fd uintptr) {
        // Set send buffer
        syscall.SetsockoptInt(int(fd), syscall.SOL_SOCKET,
            syscall.SO_SNDBUF, 262144) // 256KB

        // Set receive buffer
        syscall.SetsockoptInt(int(fd), syscall.SOL_SOCKET,
            syscall.SO_RCVBUF, 262144)
    })
}
```

### Congestion Control

**Algorithms**:
- **Slow Start**: Exponential growth until loss detected
- **Congestion Avoidance**: Linear growth
- **Fast Retransmit**: Resend after 3 duplicate ACKs
- **Fast Recovery**: Resume without slow start

**Congestion Window Evolution**:
```
CWND (congestion window size)
  ^
  |     Slow Start    Congestion Avoidance
  |      ____________________/\
  |     /                      \
  |    /                        \  Packet Loss
  |   /                          \
  |  /                            \______
  |_/
  +--------------------------------> Time

1. Start small (1-10 MSS)
2. Double each RTT (slow start)
3. Hit threshold → linear growth
4. Loss → cut window in half
5. Resume from Fast Recovery
```

**Modern Algorithms**:
- **Cubic** (Linux default): Optimized for high-bandwidth networks
- **BBR** (Google): Measures bottleneck bandwidth
- **Reno**: Classic algorithm
- **Vegas**: Proactive congestion avoidance

**Check Current Algorithm** (Linux):
```bash
# View current congestion control
sysctl net.ipv4.tcp_congestion_control
# cubic

# Change to BBR
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr
```

### Reliability Mechanisms

**Retransmission**:
```
Sender                          Receiver
  |                                |
  |-- Packet 1 ------------------>|
  |-- Packet 2 --------X  LOST    |
  |-- Packet 3 ------------------>|
  |                                |
  |<-- ACK 1 ----------------------|
  |<-- ACK 1 (duplicate) ----------| Packet 2 missing
  |<-- ACK 1 (duplicate) ----------|
  |<-- ACK 1 (duplicate) ----------|
  |                                |
  |-- Packet 2 (retransmit) ----->| Fast Retransmit
  |                                |
  |<-- ACK 4 ----------------------| All received!
```

**Timeout Calculation**:
```python
# Adaptive RTO (Retransmission Timeout)
RTT_measured = measure_round_trip_time()
SRTT = 0.875 * SRTT + 0.125 * RTT_measured  # Smoothed RTT
RTTVAR = 0.75 * RTTVAR + 0.25 * abs(SRTT - RTT_measured)
RTO = SRTT + 4 * RTTVAR

# Retransmit if no ACK within RTO
```

---

## Patterns

### Pattern 1: TCP Keep-Alive

**Use Case**: Detect dead connections

```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Enable keep-alive
sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

# Keep-alive settings (Linux)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)   # Start after 60s idle
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)  # Probe every 10s
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)     # 5 probes before timeout

sock.connect(('example.com', 80))
```

### Pattern 2: Nagle's Algorithm Disable

**Use Case**: Low-latency applications (gaming, real-time)

```go
// Disable Nagle's algorithm for low latency
conn, _ := net.Dial("tcp", "game-server.com:9000")
tcpConn := conn.(*net.TCPConn)

// Disable buffering (TCP_NODELAY)
tcpConn.SetNoDelay(true)

// Send immediately without waiting
tcpConn.Write([]byte("PLAYER_MOVE x=10 y=20"))
```

**Trade-offs**:
- ✅ Lower latency
- ❌ More small packets (less efficient)

### Pattern 3: Connection Pool

**Use Case**: Reuse TCP connections

```python
import requests
from requests.adapters import HTTPAdapter

# Create session with connection pooling
session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,    # Connection pools
    pool_maxsize=100,       # Max connections per pool
    max_retries=3
)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Connections reused across requests
for i in range(100):
    response = session.get(f'http://api.example.com/data/{i}')
    # No handshake overhead after first request
```

---

## Performance Optimization

### Tuning TCP Parameters

**Linux Kernel Tuning**:
```bash
# Increase buffer sizes
sudo sysctl -w net.core.rmem_max=26214400      # 25MB
sudo sysctl -w net.core.wmem_max=26214400
sudo sysctl -w net.ipv4.tcp_rmem="4096 87380 26214400"
sudo sysctl -w net.ipv4.tcp_wmem="4096 65536 26214400"

# Enable window scaling
sudo sysctl -w net.ipv4.tcp_window_scaling=1

# Enable TCP Fast Open
sudo sysctl -w net.ipv4.tcp_fastopen=3

# Use BBR congestion control
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr
```

**Application-Level**:
```rust
use tokio::net::TcpStream;
use socket2::{Socket, Domain, Type, Protocol};

// Create socket with custom options
let socket = Socket::new(Domain::IPV4, Type::STREAM, Some(Protocol::TCP))?;

// Set buffer sizes
socket.set_recv_buffer_size(262144)?;  // 256KB
socket.set_send_buffer_size(262144)?;

// Disable Nagle
socket.set_nodelay(true)?;

// Enable keep-alive
socket.set_keepalive(Some(std::time::Duration::from_secs(60)))?;

// Convert to Tokio stream
let std_stream = socket.into();
let stream = TcpStream::from_std(std_stream)?;
```

---

## Troubleshooting

### Issue 1: Connection Refused

**Symptoms**: Cannot establish connection

**Causes**:
- No server listening on port
- Firewall blocking
- Wrong IP/port

**Debug**:
```bash
# Check if port is listening
netstat -tuln | grep :80

# Test connectivity
telnet example.com 80
nc -zv example.com 80

# Check firewall
sudo iptables -L -n | grep 80
```

### Issue 2: Connection Timeout

**Symptoms**: Connection hangs

**Causes**:
- Network issue
- Firewall dropping SYN packets
- Server overloaded

**Debug**:
```bash
# Trace route
traceroute example.com

# TCP dump
sudo tcpdump -i eth0 'tcp port 80'
```

### Issue 3: Slow Performance

**Check Metrics**:
```bash
# View TCP statistics
ss -ti

# Example output:
#  cwnd:10 rtt:45/30 ato:40 mss:1460 retrans:0/5
```

**Optimize**:
```bash
# Enable BBR
echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## Related Skills

- `protocols-udp-fundamentals` - UDP protocol comparison
- `protocols-quic-protocol` - QUIC over UDP
- `protocols-http-fundamentals` - HTTP over TCP
- `networking-load-balancing` - TCP load balancing
- `networking-network-protocols` - DNS, DHCP over TCP/UDP

---

**Last Updated**: 2025-10-27
