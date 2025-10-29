# TCP Optimization Reference

**Comprehensive guide to TCP performance tuning, congestion control, and optimization**

---

## Table of Contents

1. [TCP Fundamentals](#tcp-fundamentals)
2. [Congestion Control Algorithms](#congestion-control-algorithms)
3. [TCP Parameters and Tuning](#tcp-parameters-and-tuning)
4. [Kernel Tuning](#kernel-tuning)
5. [TCP Offloading](#tcp-offloading)
6. [Keep-Alive Configuration](#keep-alive-configuration)
7. [Selective Acknowledgment (SACK)](#selective-acknowledgment-sack)
8. [Fast Retransmit and Recovery](#fast-retransmit-and-recovery)
9. [TCP Performance Metrics](#tcp-performance-metrics)
10. [High-Performance TCP](#high-performance-tcp)
11. [TCP Over Wireless](#tcp-over-wireless)
12. [Cloud Optimization](#cloud-optimization)
13. [Container Networking](#container-networking)
14. [Load Balancer TCP Optimization](#load-balancer-tcp-optimization)
15. [TLS/SSL Impact on TCP](#tlsssl-impact-on-tcp)
16. [Testing and Benchmarking](#testing-and-benchmarking)
17. [Monitoring Tools](#monitoring-tools)
18. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)
19. [Anti-Patterns](#anti-patterns)

---

## TCP Fundamentals

### Protocol Overview

**TCP** (Transmission Control Protocol) provides:
- **Reliable delivery**: All data arrives or connection fails
- **Ordered delivery**: Packets received in send order
- **Connection-oriented**: Explicit setup and teardown
- **Flow control**: Prevent receiver overflow
- **Congestion control**: Prevent network congestion
- **Error detection**: Checksums verify data integrity

### Three-Way Handshake

**Connection establishment**:

```
Client                           Server
  |                                |
  |-------- SYN (seq=x) --------->|  (1) Client initiates
  |                                |
  |<--- SYN-ACK (seq=y, ack=x+1)--|  (2) Server responds
  |                                |
  |-------- ACK (ack=y+1) ------->|  (3) Client confirms
  |                                |
  |  CONNECTION ESTABLISHED        |
```

**Sequence numbers**:
- Client chooses random initial sequence number (ISN) x
- Server chooses random ISN y
- Sequence numbers track every byte sent
- Acknowledgments confirm bytes received

**Connection options negotiated**:
- Maximum Segment Size (MSS)
- Window scale factor
- Selective ACK (SACK) support
- Timestamps

### Sliding Window Protocol

**Flow control mechanism**:

```
Sender's perspective:
|----|----|----|----|----|----|----|----|
  1    2    3    4    5    6    7    8
  ↑         ↑              ↑
 Sent    Acked         Window
 +Acked              (can send)

Receiver's perspective:
  Receive Buffer
|-------------------------|
  ← Used →  ← Available →
            (rwnd)
```

**Key concepts**:
- **Send window**: Unacknowledged data sender can have in flight
- **Receive window (rwnd)**: Buffer space advertised by receiver
- **Congestion window (cwnd)**: Network capacity estimate
- **Effective window**: min(rwnd, cwnd)

**Window sliding**:
```
Initial: [1 2 3 4] 5 6 7 8
After ACK 2: 1 2 [3 4 5 6] 7 8
After ACK 4: 1 2 3 4 [5 6 7 8]
```

### TCP Segment Structure

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Sequence Number                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Acknowledgment Number                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Data |       |C|E|U|A|P|R|S|F|                               |
| Offset| Rsvd  |W|C|R|C|S|S|Y|I|            Window             |
|       |       |R|E|G|K|H|T|N|N|                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Checksum            |         Urgent Pointer        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Options                    |    Padding    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                             data                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

**Important fields**:
- **Sequence Number**: Byte position of first data byte
- **Acknowledgment Number**: Next expected sequence number
- **Window**: Receive window size (scaled if option set)
- **Flags**: SYN, ACK, FIN, RST, PSH, URG
- **Options**: MSS, window scale, SACK, timestamps

### Flow Control vs Congestion Control

**Flow control** (receiver protection):
- Prevents sender from overwhelming receiver
- Receiver advertises window size (rwnd)
- Sender respects receiver's capacity
- Per-connection mechanism

**Congestion control** (network protection):
- Prevents sender from overwhelming network
- Sender maintains congestion window (cwnd)
- Adapts to network conditions
- Uses packet loss or delay as signals

**Relationship**:
```
Effective window = min(rwnd, cwnd)
Throughput ≈ Effective Window / RTT
```

### Bandwidth-Delay Product (BDP)

**Definition**: Amount of data "in flight" on network

```
BDP = Bandwidth × RTT
```

**Example calculations**:
```
10 Gbps, 1ms RTT:   10 Gbps × 0.001s = 10 Mb = 1.25 MB
10 Gbps, 10ms RTT:  10 Gbps × 0.01s  = 100 Mb = 12.5 MB
10 Gbps, 100ms RTT: 10 Gbps × 0.1s   = 1 Gb = 125 MB
1 Gbps, 100ms RTT:  1 Gbps × 0.1s    = 100 Mb = 12.5 MB
```

**Implications**:
- **TCP window must be ≥ BDP** for full throughput
- Without window scaling, max window = 64 KB
- 64 KB / 100ms = 640 KB/s = 5.12 Mbps (maximum!)
- High BDP networks need large windows

### Maximum Segment Size (MSS)

**Definition**: Largest TCP payload per segment

```
MSS = MTU - IP header - TCP header
    = 1500 - 20 - 20 = 1460 bytes (typical Ethernet)
```

**MSS negotiation**:
```
Client: SYN, MSS=1460
Server: SYN-ACK, MSS=1460
→ Both sides use min(1460, 1460) = 1460
```

**Jumbo frames**:
```
MTU = 9000 bytes
MSS = 9000 - 20 - 20 = 8960 bytes
→ 6x larger payload per packet
→ Lower CPU overhead
→ Better throughput
```

**Path MTU Discovery (PMTUD)**:
- Discovers smallest MTU along path
- Sends packets with DF (Don't Fragment) bit set
- If too large, receives ICMP Fragmentation Needed
- Adjusts MSS accordingly

**MSS clamping** (for VPN/tunnel):
```bash
# Prevent fragmentation in tunnel
iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
```

---

## Congestion Control Algorithms

### Algorithm Evolution

**Timeline**:
```
1988: Tahoe (slow start, congestion avoidance)
1990: Reno (fast retransmit, fast recovery)
2001: BIC (Binary Increase Congestion control)
2005: Cubic (default Linux since 2.6.19)
2016: BBR (Bottleneck Bandwidth and RTT)
2020: BBRv2 (improved fairness)
```

### Reno (Classic TCP)

**Phases**:

1. **Slow Start**:
   - cwnd starts at 1-10 MSS (initial window)
   - cwnd doubles each RTT (exponential growth)
   - Continues until ssthresh (slow start threshold)
   ```
   RTT 1: cwnd = 1
   RTT 2: cwnd = 2
   RTT 3: cwnd = 4
   RTT 4: cwnd = 8
   ```

2. **Congestion Avoidance**:
   - cwnd increases by 1 MSS per RTT (linear growth)
   - Probes for available bandwidth
   ```
   RTT n:   cwnd = X
   RTT n+1: cwnd = X + 1
   RTT n+2: cwnd = X + 2
   ```

3. **Fast Retransmit**:
   - Triggered by 3 duplicate ACKs
   - Retransmit lost packet immediately
   - Don't wait for timeout

4. **Fast Recovery**:
   - After fast retransmit: ssthresh = cwnd / 2
   - cwnd = ssthresh + 3
   - Inflate cwnd for each duplicate ACK
   - Return to congestion avoidance on new ACK

**Loss recovery**:
```
            ┌─ Congestion! (loss detected)
            │
cwnd   ────╱│╲────────────
          /  │ \
         /   │  \
        /    │   \_____ ssthresh = cwnd/2
       /     │         cwnd resets to ssthresh
  Slow      Fast      Congestion
  Start   Recovery    Avoidance
```

**Problems**:
- Slow on high BDP networks
- Takes many RTTs to reach capacity
- Aggressive response to loss
- Not ideal for modern networks

### Cubic (Linux Default)

**Key innovation**: Cubic function for window growth

**Window growth function**:
```
W(t) = C(t - K)³ + Wmax

Where:
- t: Time since last loss
- K: Time to reach Wmax (inflection point)
- C: Cubic parameter (0.4)
- Wmax: Window size at last loss
```

**Growth phases**:
```
cwnd
  ^
  │        ┌─ Wmax (previous loss)
  │       /│\
  │      / │ \
  │     /  │  \_____ Cubic function
  │    /   │
  │   /    │   Fast ramp-up
  │  /     │   after loss
  │ /      │
  │/       │
  └────────┴────────> time
      K (inflection)
```

**Advantages over Reno**:
- Faster recovery after loss
- Better for high BDP networks
- More stable in high-speed scenarios
- Independent of RTT (more fair)

**Behavior**:
- Rapid increase when far from Wmax
- Slow increase near Wmax (probing carefully)
- Multiplicative decrease on loss
- Good balance of throughput and fairness

**Configuration**:
```bash
# Check if Cubic is active
sysctl net.ipv4.tcp_congestion_control

# Cubic parameters (usually don't need tuning)
sysctl net.ipv4.tcp_cubic
```

### BBR (Bottleneck Bandwidth and RTT)

**Paradigm shift**: Model-based instead of loss-based

**Key insight**: Congestion is detected before loss occurs
- Reno/Cubic: Wait for loss → React
- BBR: Model bandwidth → Operate at optimal point

**BBR measures**:
1. **Bottleneck bandwidth** (BtlBw): Maximum delivery rate
2. **RTT** (round-trip propagation time): Minimum observed RTT

**Operating point**:
```
           Rate
             ^
             │     Packet loss region
             │    /
  BtlBw   ───┼───●────────────
             │  /│\
             │ / │ \  BBR operates here
             │/  │  \
             │   │   Buffer filling region
             │   │
             └───┴──────────> Inflight Data
              BDP = BtlBw × RTTmin
```

**BBR pacing rate**:
```
pacing_rate = pacing_gain × BtlBw
cwnd = cwnd_gain × BDP
```

**State machine**:
```
STARTUP → DRAIN → PROBE_BW ⇄ PROBE_RTT
   │                 ^          │
   └─────────────────┴──────────┘
```

**States**:

1. **STARTUP** (initial):
   - Exponential search for bandwidth
   - pacing_gain = 2.89 (high gain)
   - Exits when bandwidth stops increasing

2. **DRAIN**:
   - Remove excess queue built during STARTUP
   - pacing_gain = 1/2.89
   - Drains until inflight = BDP

3. **PROBE_BW** (steady state):
   - Cycle through gains: [1.25, 0.75, 1, 1, 1, 1, 1, 1]
   - Periodically probe for more bandwidth
   - Drain any queues built

4. **PROBE_RTT**:
   - Every 10 seconds, reduce cwnd to 4 packets
   - Measure true RTTmin
   - Prevents queue buildup

**Advantages**:
- 2-25x throughput improvement on high BDP networks
- Lower latency (smaller queues)
- Faster convergence
- Works well with shallow buffers
- Loss-tolerant (wireless networks)

**Disadvantages**:
- Can be too aggressive (BBRv1)
- Fairness issues with Cubic
- Requires Fair Queueing (fq) qdisc

**Enabling BBR**:
```bash
# Check kernel version (need 4.9+)
uname -r

# Load BBR module
sudo modprobe tcp_bbr

# Set BBR as default
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr
sudo sysctl -w net.core.default_qdisc=fq

# Verify
sysctl net.ipv4.tcp_congestion_control
sysctl net.core.default_qdisc

# Make persistent
cat <<EOF | sudo tee -a /etc/sysctl.conf
net.ipv4.tcp_congestion_control=bbr
net.core.default_qdisc=fq
EOF

sudo sysctl -p
```

### BBRv2 (2020+)

**Improvements over BBRv1**:
- Better fairness with other flows
- Improved loss tolerance
- More responsive to changing conditions
- Production-ready in Linux 5.18+

**Key changes**:
- New PROBE_UP state for bandwidth search
- Better response to loss signals
- Enhanced flow startup behavior
- Improved RTT probe logic

**Enabling BBRv2**:
```bash
# Check kernel version (need 5.18+)
uname -r

# Load BBRv2 (if available)
sudo modprobe tcp_bbr2

# Set BBRv2
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr2
sudo sysctl -w net.core.default_qdisc=fq
```

### DCTCP (Data Center TCP)

**Designed for**: Low-latency data center networks

**Key features**:
- Explicit Congestion Notification (ECN) based
- Switches mark packets instead of dropping
- More precise congestion signaling
- Smaller queues, lower latency

**When to use**:
- Data center networks (low RTT, high bandwidth)
- Networks with ECN-capable switches
- Latency-sensitive applications

**Enabling DCTCP**:
```bash
# Enable ECN
sudo sysctl -w net.ipv4.tcp_ecn=1

# Set DCTCP
sudo sysctl -w net.ipv4.tcp_congestion_control=dctcp
```

### Algorithm Comparison

| Algorithm | Best For | Throughput | Latency | Fairness | Loss Tolerance |
|-----------|----------|------------|---------|----------|----------------|
| Reno      | Legacy   | Poor       | Medium  | Good     | Poor           |
| Cubic     | General  | Good       | Medium  | Good     | Medium         |
| BBR       | High BDP | Excellent  | Good    | Medium   | Excellent      |
| BBRv2     | High BDP | Excellent  | Good    | Good     | Excellent      |
| DCTCP     | Data Ctr | Excellent  | Best    | Good     | Medium         |

**Selection guide**:
```
High BDP (WAN, Cloud)     → BBR/BBRv2
Data Center               → BBR/DCTCP
General Purpose           → Cubic
Legacy Compatibility      → Reno
Wireless/Mobile           → BBR (loss tolerant)
```

---

## TCP Parameters and Tuning

### Buffer Sizes

**Critical parameters**:
```bash
# Receive buffer: min, default, max (bytes)
net.ipv4.tcp_rmem = 4096 131072 6291456

# Send buffer: min, default, max
net.ipv4.tcp_wmem = 4096 16384 4194304

# Maximum socket buffer (must be ≥ tcp_rmem/wmem max)
net.core.rmem_max = 134217728   # 128 MB
net.core.wmem_max = 134217728
```

**Buffer sizing strategy**:

1. **Calculate BDP**:
   ```
   BDP = Bandwidth × RTT

   Examples:
   10 Gbps × 1ms   = 1.25 MB
   10 Gbps × 10ms  = 12.5 MB
   10 Gbps × 100ms = 125 MB
   1 Gbps × 100ms  = 12.5 MB
   ```

2. **Set max buffer ≥ 2 × BDP**:
   ```bash
   # For 10 Gbps, 100ms RTT (BDP = 125 MB)
   net.ipv4.tcp_rmem = 4096 131072 268435456   # 256 MB max
   net.ipv4.tcp_wmem = 4096 131072 268435456
   net.core.rmem_max = 268435456
   net.core.wmem_max = 268435456
   ```

3. **Conservative defaults**:
   ```bash
   # General purpose (1-10 Gbps)
   net.ipv4.tcp_rmem = 4096 131072 67108864    # 64 MB max
   net.ipv4.tcp_wmem = 4096 65536 67108864
   net.core.rmem_max = 67108864
   net.core.wmem_max = 67108864
   ```

**Auto-tuning**:
```bash
# Enable TCP buffer auto-tuning (usually enabled)
net.ipv4.tcp_moderate_rcvbuf = 1

# Monitor buffer usage
ss -tm | grep -E "skmem|cwnd"
```

**Memory limits**:
```bash
# TCP memory: min, pressure, max (pages, 4KB each)
net.ipv4.tcp_mem = 1048576 2097152 4194304

# Example: 16 GB max TCP memory
# 4194304 pages × 4KB = 16 GB
```

### Window Scaling

**Problem**: TCP window field is 16 bits → max 65535 bytes

```
Without scaling:
Max throughput = 65535 bytes / RTT

65535 / 0.001s = 65 MB/s   = 524 Mbps  (okay)
65535 / 0.01s  = 6.5 MB/s  = 52 Mbps   (poor)
65535 / 0.1s   = 655 KB/s  = 5.2 Mbps  (terrible)
```

**Solution**: Window scaling (RFC 1323)
```bash
# Enable window scaling (essential!)
net.ipv4.tcp_window_scaling = 1
```

**How it works**:
- Negotiate scale factor during handshake
- Scale factor: 0-14 (multiply window by 2^scale)
- Max effective window: 65535 × 2^14 = 1 GB

**Checking negotiated scale**:
```bash
# Capture SYN packets
tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-syn != 0' -v
# Look for: wscale 7 (window scale factor)
```

### Initial Congestion Window

**Problem**: Slow start begins with small window (1-10 MSS)
- Multiple RTTs to reach capacity
- High latency for short flows

**Modern default**:
```bash
# Check initial cwnd
ip route show

# Set initial cwnd = 10 (RFC 6928)
ip route change default via <gateway> dev eth0 initcwnd 10 initrwnd 10
```

**Impact**:
```
initcwnd=1:  1, 2, 4, 8, 16, 32... (slow start)
initcwnd=10: 10, 20, 40, 80...     (faster start)

For 14 KB response:
cwnd=1:  4 RTTs needed
cwnd=10: 1 RTT needed
```

**Per-route configuration**:
```bash
# Specific destination
ip route add 10.0.0.0/8 via 192.168.1.1 dev eth0 initcwnd 10

# Default route
ip route change default via 192.168.1.1 dev eth0 initcwnd 10

# Verify
ip route show
```

### Slow Start After Idle

**Behavior**: Reset cwnd to initial value after idle period

```bash
# Default: 1 (reset after idle)
net.ipv4.tcp_slow_start_after_idle = 1

# Disable (recommended for high BDP)
net.ipv4.tcp_slow_start_after_idle = 0
```

**Impact**:
- **Enabled**: Bursty traffic resets to slow start
- **Disabled**: Maintain cwnd across idle periods
- **Recommendation**: Disable for servers with intermittent traffic

### Timestamps

**Purpose**: Accurate RTT measurement, PAWS (Protect Against Wrapped Sequences)

```bash
# Enable timestamps (essential for high performance)
net.ipv4.tcp_timestamps = 1
```

**Benefits**:
- More accurate RTT estimation
- Better timeout calculation
- Required for window scaling > 1 GB
- Prevents sequence number wrap issues

**Overhead**: 10 bytes per packet (minimal)

### Selective ACK (SACK)

**Problem**: Without SACK, only cumulative ACKs
```
Sent: 1 2 3 4 5
Recv: 1 2 X 4 5
ACK:  2 (can only ACK 2, even though 4,5 received)
→ Retransmit 3,4,5 (inefficient!)
```

**With SACK**:
```
Sent: 1 2 3 4 5
Recv: 1 2 X 4 5
ACK:  2, SACK: 4-5 (acknowledge 4,5 separately)
→ Retransmit 3 only (efficient!)
```

**Configuration**:
```bash
# Enable SACK (essential!)
net.ipv4.tcp_sack = 1

# Duplicate SACK (helpful for reordering)
net.ipv4.tcp_dsack = 1
```

### TCP Fast Open (TFO)

**Problem**: 1 RTT wasted on handshake for short flows

**Traditional**:
```
Client → SYN → Server
Client ← SYN-ACK ← Server
Client → ACK + Request → Server     (1 RTT wasted)
Client ← Response ← Server
```

**With TFO**:
```
Client → SYN + Request → Server     (Data in SYN!)
Client ← SYN-ACK + Response ← Server
Client → ACK → Server
```

**Configuration**:
```bash
# TFO modes:
# 0: Disabled
# 1: Client only
# 2: Server only
# 3: Client and server

net.ipv4.tcp_fastopen = 3

# TFO key for server (generated automatically)
net.ipv4.tcp_fastopen_key = <generated>

# Max TFO requests in SYN queue
net.ipv4.tcp_fastopen_blackhole_timeout_sec = 3600
```

**Application support required**:
```c
// Server: MSG_FASTOPEN flag
sendto(sock, data, len, MSG_FASTOPEN, ...);

// Client: TCP_FASTOPEN socket option
setsockopt(sock, IPPROTO_TCP, TCP_FASTOPEN, ...);
```

**Benefits**:
- 0 RTT for repeat connections
- 1 RTT for first connection
- Great for HTTP, RPC

**Caveats**:
- Requires application support
- Security considerations (replay attacks)
- Not all middleboxes support it

---

## Kernel Tuning

### Essential sysctl Parameters

**Complete high-performance configuration**:

```bash
# /etc/sysctl.d/99-tcp-tuning.conf

# === TCP Buffer Sizes ===
# For 10+ Gbps networks with 10-100ms RTT
net.ipv4.tcp_rmem = 4096 131072 134217728      # 128 MB max receive
net.ipv4.tcp_wmem = 4096 131072 134217728      # 128 MB max send
net.core.rmem_max = 134217728                   # Socket receive max
net.core.wmem_max = 134217728                   # Socket send max
net.core.rmem_default = 131072                  # Default receive
net.core.wmem_default = 131072                  # Default send
net.core.optmem_max = 65536                     # Ancillary buffer

# === TCP Memory Limits ===
# Total memory for TCP (pages of 4KB)
# min: below this, no pressure
# pressure: above this, start reclaiming
# max: maximum TCP memory
net.ipv4.tcp_mem = 1048576 2097152 4194304     # 4GB, 8GB, 16GB

# === Window Scaling ===
net.ipv4.tcp_window_scaling = 1                 # Enable (required!)

# === Timestamps ===
net.ipv4.tcp_timestamps = 1                     # Enable (required!)

# === SACK ===
net.ipv4.tcp_sack = 1                           # Enable SACK
net.ipv4.tcp_dsack = 1                          # Duplicate SACK
net.ipv4.tcp_fack = 1                           # Forward ACK

# === Congestion Control ===
net.ipv4.tcp_congestion_control = bbr           # Use BBR
net.core.default_qdisc = fq                     # Fair Queueing for BBR

# === Connection Management ===
net.ipv4.tcp_slow_start_after_idle = 0          # Don't reset cwnd
net.ipv4.tcp_tw_reuse = 1                       # Reuse TIME_WAIT sockets
net.ipv4.tcp_fin_timeout = 30                   # FIN timeout (default 60)
net.ipv4.tcp_max_tw_buckets = 2000000           # Max TIME_WAIT sockets
net.ipv4.tcp_max_syn_backlog = 8192             # SYN queue size

# === Fast Open ===
net.ipv4.tcp_fastopen = 3                       # Enable client + server

# === SYN Cookies (DDoS protection) ===
net.ipv4.tcp_syncookies = 1                     # Enable SYN cookies

# === Retransmission ===
net.ipv4.tcp_retries1 = 3                       # Fast retransmit attempts
net.ipv4.tcp_retries2 = 15                      # Max retransmit attempts
net.ipv4.tcp_syn_retries = 5                    # SYN retries
net.ipv4.tcp_synack_retries = 5                 # SYN-ACK retries

# === Keep-Alive ===
net.ipv4.tcp_keepalive_time = 600               # Start probing after 10 min
net.ipv4.tcp_keepalive_intvl = 60               # Probe every 60 sec
net.ipv4.tcp_keepalive_probes = 3               # 3 failed probes = dead

# === MTU Probing ===
net.ipv4.tcp_mtu_probing = 1                    # Enable MTU probing

# === Misc ===
net.ipv4.tcp_no_metrics_save = 1                # Don't cache metrics
net.ipv4.tcp_moderate_rcvbuf = 1                # Auto-tune receive buffer

# === IP Settings ===
net.ipv4.ip_local_port_range = 10000 65535      # Port range for outbound
net.core.netdev_max_backlog = 5000              # Device queue length
net.core.somaxconn = 4096                       # Socket listen backlog

# === Apply ===
# sysctl -p /etc/sysctl.d/99-tcp-tuning.conf
```

### Tuning by Scenario

**1. High-Bandwidth WAN (10Gbps, 100ms RTT)**:
```bash
# BDP = 10 Gbps × 0.1s = 125 MB
net.ipv4.tcp_rmem = 4096 131072 268435456       # 256 MB
net.ipv4.tcp_wmem = 4096 131072 268435456
net.core.rmem_max = 268435456
net.core.wmem_max = 268435456
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_slow_start_after_idle = 0
```

**2. Data Center (Low latency, high bandwidth)**:
```bash
# Lower buffers (short RTT)
net.ipv4.tcp_rmem = 4096 87380 16777216         # 16 MB
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_congestion_control = dctcp         # or BBR
net.ipv4.tcp_ecn = 1                            # For DCTCP
net.ipv4.tcp_fin_timeout = 10                   # Fast cleanup
```

**3. Wireless/Mobile**:
```bash
# Conservative buffers, loss tolerance
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_congestion_control = bbr           # Loss tolerant
net.ipv4.tcp_sack = 1                           # Handle reordering
net.ipv4.tcp_keepalive_time = 300               # Shorter keep-alive
```

**4. High-Connection-Rate Server (Web server)**:
```bash
# Fast connection handling
net.ipv4.tcp_tw_reuse = 1                       # Reuse connections
net.ipv4.tcp_fin_timeout = 15                   # Fast cleanup
net.ipv4.tcp_max_tw_buckets = 2000000           # Many TIME_WAITs
net.ipv4.tcp_max_syn_backlog = 16384            # Large SYN queue
net.core.somaxconn = 8192                       # Listen backlog
net.ipv4.ip_local_port_range = 1024 65535       # Max port range
net.ipv4.tcp_fastopen = 3                       # Fast Open
```

### Applying Configuration

**Temporary** (immediate, not persistent):
```bash
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr
```

**Persistent** (survives reboot):
```bash
# Create config file
sudo vi /etc/sysctl.d/99-tcp-tuning.conf

# Add parameters
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq

# Apply
sudo sysctl -p /etc/sysctl.d/99-tcp-tuning.conf

# Verify
sysctl net.ipv4.tcp_congestion_control
```

**Verification**:
```bash
# Check all TCP settings
sysctl -a | grep tcp

# Check specific setting
sysctl net.ipv4.tcp_congestion_control

# Check available congestion control algorithms
sysctl net.ipv4.tcp_available_congestion_control

# Check current connections
ss -tin | head -20
```

---

## TCP Offloading

### Offload Types

**Hardware offloads**: NIC performs TCP operations

**Benefits**:
- Reduced CPU usage
- Higher throughput
- Lower latency
- Better scalability

### TCP Segmentation Offload (TSO)

**What it does**: NIC segments large packets into MSS-sized segments

**Without TSO**:
```
CPU:  Segment 64KB → 1460-byte packets (44 packets)
      ↓ (44 packets)
NIC:  Transmit packets
```

**With TSO**:
```
CPU:  Create 64KB packet
      ↓ (1 large packet)
NIC:  Segment into 1460-byte packets (44 packets)
      Transmit packets
```

**Benefits**:
- CPU processes 1 packet instead of 44
- Lower CPU usage (up to 50% reduction)
- Higher throughput

**Commands**:
```bash
# Check TSO status
ethtool -k eth0 | grep tcp-segmentation-offload

# Enable
sudo ethtool -K eth0 tso on

# Disable (for debugging)
sudo ethtool -K eth0 tso off
```

### Generic Segmentation Offload (GSO)

**What it does**: Software TSO (delays segmentation)

**Flow**:
```
Application → TCP → IP → GSO (large packets) → NIC/qdisc
                                              ↓
                                      Segment before TX
```

**Benefits**:
- Works even without hardware TSO
- Reduces network stack overhead
- Improves throughput

**Commands**:
```bash
# Check GSO status
ethtool -k eth0 | grep generic-segmentation-offload

# Enable
sudo ethtool -K eth0 gso on
```

### Generic Receive Offload (GRO)

**What it does**: Aggregates received packets (inverse of GSO)

**Without GRO**:
```
NIC → 44 small packets → IP → TCP → Application
      (many interrupts, context switches)
```

**With GRO**:
```
NIC → 44 packets → GRO aggregates → 1 large packet → TCP → Application
      (fewer interrupts, better performance)
```

**Benefits**:
- Lower CPU usage (fewer interrupts)
- Better throughput
- Improved application performance

**Commands**:
```bash
# Check GRO status
ethtool -k eth0 | grep generic-receive-offload

# Enable
sudo ethtool -K eth0 gro on

# Check statistics
ethtool -S eth0 | grep gro
```

### Large Receive Offload (LRO)

**What it does**: Hardware packet aggregation (similar to GRO)

**Difference from GRO**:
- **LRO**: Hardware-based, less flexible
- **GRO**: Software-based, more flexible

**Warning**: LRO breaks forwarding!
```
Problem: LRO merges packets from different flows
→ Routing decisions based on merged packet
→ Wrong forwarding behavior
```

**When to disable**:
- Routers
- Bridges
- Any forwarding device

**Commands**:
```bash
# Check LRO status
ethtool -k eth0 | grep large-receive-offload

# Disable (if forwarding)
sudo ethtool -K eth0 lro off
```

### Checksum Offload

**What it does**: NIC calculates checksums

**Types**:
- **TX checksum offload**: NIC calculates outgoing checksums
- **RX checksum offload**: NIC verifies incoming checksums

**Benefits**:
- CPU savings (checksums expensive)
- Higher throughput

**Commands**:
```bash
# Check status
ethtool -k eth0 | grep checksum

# Enable
sudo ethtool -K eth0 tx-checksumming on
sudo ethtool -K eth0 rx-checksumming on
```

### Interrupt Coalescing

**What it does**: Batch interrupts together

**Without coalescing**:
```
Packet arrives → Interrupt → Context switch
→ High interrupt rate
→ High CPU usage
```

**With coalescing**:
```
Packets arrive → Wait for timeout or count → Single interrupt
→ Lower interrupt rate
→ Lower CPU, slight latency increase
```

**Configuration**:
```bash
# Check current settings
ethtool -c eth0

# Set coalescing (microseconds or packet count)
sudo ethtool -C eth0 rx-usecs 50
sudo ethtool -C eth0 rx-frames 16

# Adaptive coalescing (auto-tune)
sudo ethtool -C eth0 adaptive-rx on
```

**Tuning**:
- **Low latency**: Low rx-usecs (10-20)
- **High throughput**: Higher rx-usecs (50-100)
- **Adaptive**: Let kernel tune automatically

### RSS (Receive Side Scaling)

**What it does**: Distribute incoming packets across CPUs

**Benefits**:
- Parallel packet processing
- Better multi-core utilization
- Higher throughput

**Check configuration**:
```bash
# Number of RSS queues
ethtool -l eth0

# RSS hash function and indirection table
ethtool -x eth0

# Set number of queues
sudo ethtool -L eth0 combined 8
```

### RPS (Receive Packet Steering)

**What it does**: Software RSS (for NICs without hardware RSS)

**Configuration**:
```bash
# Set RPS CPU mask for eth0, queue 0
echo "f" | sudo tee /sys/class/net/eth0/queues/rx-0/rps_cpus
# "f" = 0xF = 1111 binary = CPUs 0,1,2,3

# For all CPUs (32-core)
echo "ffffffff" | sudo tee /sys/class/net/eth0/queues/rx-0/rps_cpus
```

### XPS (Transmit Packet Steering)

**What it does**: Steer TX packets to specific queues/CPUs

**Configuration**:
```bash
# Set XPS for queue 0 to CPU 0
echo "1" | sudo tee /sys/class/net/eth0/queues/tx-0/xps_cpus
```

### Complete Offload Configuration

**Enable all performance features**:
```bash
#!/bin/bash
IFACE="eth0"

# TSO, GSO, GRO
sudo ethtool -K $IFACE tso on
sudo ethtool -K $IFACE gso on
sudo ethtool -K $IFACE gro on

# Checksums
sudo ethtool -K $IFACE tx-checksumming on
sudo ethtool -K $IFACE rx-checksumming on

# Disable LRO (can break forwarding)
sudo ethtool -K $IFACE lro off

# RSS (use all queues)
NUM_CPUS=$(nproc)
sudo ethtool -L $IFACE combined $NUM_CPUS

# Interrupt coalescing (adaptive)
sudo ethtool -C $IFACE adaptive-rx on adaptive-tx on

# Verify
ethtool -k $IFACE | grep -E "offload|checksum"
ethtool -l $IFACE
ethtool -c $IFACE
```

**When to disable offloads**:
```bash
# Packet capture (see actual packets, not aggregated)
sudo ethtool -K eth0 gro off tso off gso off

# After capture, re-enable
sudo ethtool -K eth0 gro on tso on gso on
```

---

## Keep-Alive Configuration

### Purpose

**Keep-alive probes**:
- Detect dead connections
- Prevent middlebox (firewall, NAT) timeout
- Clean up stale connections

### How Keep-Alive Works

```
Client                               Server
  |                                    |
  |--- Data exchange -----------------|
  |                                    |
  |    (Idle for tcp_keepalive_time)  |
  |                                    |
  |--- PROBE 1 ---------------------->|
  |    (wait tcp_keepalive_intvl)     |
  |--- PROBE 2 ---------------------->|
  |    (wait tcp_keepalive_intvl)     |
  |--- PROBE 3 ---------------------->|
  |    (tcp_keepalive_probes failed)  |
  |                                    |
  X  Connection declared dead         |
```

### Kernel Parameters

```bash
# Start probing after idle time (seconds)
net.ipv4.tcp_keepalive_time = 7200      # Default: 2 hours

# Interval between probes (seconds)
net.ipv4.tcp_keepalive_intvl = 75       # Default: 75 sec

# Number of failed probes before giving up
net.ipv4.tcp_keepalive_probes = 9       # Default: 9

# Example: Time to detect dead connection
# = tcp_keepalive_time + (tcp_keepalive_intvl × tcp_keepalive_probes)
# = 7200 + (75 × 9) = 7875 seconds = 2.2 hours
```

### Tuning by Scenario

**Long-lived connections (databases)**:
```bash
# Aggressive keep-alive
net.ipv4.tcp_keepalive_time = 600       # 10 minutes
net.ipv4.tcp_keepalive_intvl = 60       # 1 minute
net.ipv4.tcp_keepalive_probes = 3       # 3 probes
# Detection time: 10 + (1 × 3) = 13 minutes
```

**Behind NAT/firewall** (prevent timeout):
```bash
# Very aggressive (firewall timeout typically 30-60 min)
net.ipv4.tcp_keepalive_time = 300       # 5 minutes
net.ipv4.tcp_keepalive_intvl = 30       # 30 seconds
net.ipv4.tcp_keepalive_probes = 3       # 3 probes
# Detection time: 5 + (0.5 × 3) = 6.5 minutes
```

**Mobile/wireless**:
```bash
# Frequent keep-alive (connection may drop)
net.ipv4.tcp_keepalive_time = 300       # 5 minutes
net.ipv4.tcp_keepalive_intvl = 60       # 1 minute
net.ipv4.tcp_keepalive_probes = 3       # 3 probes
```

**Low-resource servers**:
```bash
# Fast connection cleanup
net.ipv4.tcp_keepalive_time = 600       # 10 minutes
net.ipv4.tcp_keepalive_intvl = 30       # 30 seconds
net.ipv4.tcp_keepalive_probes = 2       # 2 probes
# Detection time: 10 + (0.5 × 2) = 11 minutes
```

### Application-Level Keep-Alive

**Socket options** (override kernel defaults):

```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Enable keep-alive
sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

# Set parameters (Linux-specific)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)   # Time
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)  # Interval
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)     # Probes
```

```go
// Go example
import (
    "net"
    "time"
)

conn, _ := net.Dial("tcp", "example.com:80")
tcpConn := conn.(*net.TCPConn)

// Enable keep-alive
tcpConn.SetKeepAlive(true)
tcpConn.SetKeepAlivePeriod(60 * time.Second)
```

### Keep-Alive vs Application Heartbeat

**TCP keep-alive**:
- Detects network/OS failure
- Low overhead
- No application awareness

**Application heartbeat**:
- Detects application failure
- Higher overhead
- Application-level awareness
- Can carry metadata

**Best practice**: Use both!
```
TCP keep-alive: Detect network issues (10-30 min interval)
App heartbeat:  Detect app issues (30-60 sec interval)
```

---

## Selective Acknowledgment (SACK)

### Problem Without SACK

**Cumulative ACKs only**:
```
Sent packets: 1 2 3 4 5 6 7 8
Received:     1 2 X 4 5 X 7 8

ACK sent: 2 (can only acknowledge contiguous sequence)
→ Sender retransmits 3,4,5,6,7,8 (even though 4,5,7,8 received!)
→ Inefficient, wastes bandwidth
```

### SACK Mechanism

**Selective acknowledgments**:
```
Sent packets: 1 2 3 4 5 6 7 8
Received:     1 2 X 4 5 X 7 8

ACK sent: 2, SACK: 4-5, 7-8
→ Sender retransmits only 3 and 6
→ Efficient!
```

**SACK block format**:
```
TCP Option:
- Kind: 5 (SACK)
- Length: Variable (8N + 2 bytes)
- Blocks: Up to 3-4 SACK blocks per packet

Example:
SACK: 4-5, 7-8
→ "I have bytes 4-5 and 7-8"
```

### Enabling SACK

```bash
# Enable SACK (usually enabled by default)
net.ipv4.tcp_sack = 1

# Duplicate SACK (D-SACK)
net.ipv4.tcp_dsack = 1

# Forward ACK (uses SACK info)
net.ipv4.tcp_fack = 1

# Verify in handshake
tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-syn != 0' -v
# Look for: sackOK
```

### D-SACK (Duplicate SACK)

**Purpose**: Report duplicate data received

**Use cases**:
1. **Detect spurious retransmissions**:
   ```
   Original packet delayed → Retransmitted → Original arrives
   D-SACK tells sender: "I got it twice"
   → Sender knows network is delaying, not losing packets
   ```

2. **Detect reordering**:
   ```
   Packets arrive out of order
   D-SACK helps distinguish reordering from loss
   ```

**Configuration**:
```bash
net.ipv4.tcp_dsack = 1
```

### FACK (Forward ACK)

**What it does**: Use SACK info for congestion control

**Logic**:
```
SACK received: 4-5, 7-8
→ Packets 3 and 6 are missing
→ Infer they're lost (not just reordered)
→ Reduce cwnd accordingly
```

**Configuration**:
```bash
net.ipv4.tcp_fack = 1
```

### SACK Performance Impact

**Benefits**:
- **Faster recovery** from packet loss
- **Better bandwidth utilization**
- **Essential** for high-speed networks

**Overhead**:
- **10-40 bytes** per TCP packet (SACK option)
- **Minimal CPU overhead**

**Scenarios where SACK crucial**:
- High packet loss (wireless, long-distance)
- Packet reordering
- High BDP networks

### Monitoring SACK

**Check SACK usage**:
```bash
# System-wide SACK stats
nstat -az | grep Sack

# Per-connection SACK info
ss -tin | grep sack

# Example output:
#   sack_out:0 sack_in:5
#   → 0 SACK blocks sent, 5 received
```

**Packet capture**:
```bash
# Capture packets with SACK option
tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-ack != 0' -v | grep -i sack

# Example:
#   ACK 1000, SACK [2000:3000] [4000:5000]
```

---

## Fast Retransmit and Recovery

### Fast Retransmit

**Problem**: Timeout-based retransmission is slow
```
Packet lost → Wait for timeout (RTO) → Retransmit
→ Delay: RTT × 2 to 4 (typical RTO)
```

**Fast Retransmit**:
```
Packet lost → 3 duplicate ACKs → Immediate retransmit
→ Delay: ~1 RTT
```

**How it works**:
```
Sender:  1  2  3  4  5  6  7
         ↓  ↓  X  ↓  ↓  ↓  ↓
Receiver: 1  2     4  5  6  7

ACKs sent: ACK 2, ACK 2, ACK 2, ACK 2  (duplicate ACKs)
                          ↑
                    After 3 duplicates,
                    retransmit packet 3
```

**Trigger**: 3 duplicate ACKs (RFC 2581)

**Configuration**:
```bash
# Duplicate ACK threshold (usually 3)
# Note: This is typically hardcoded, not tunable via sysctl
```

### Fast Recovery

**Goal**: Avoid slow start after fast retransmit

**Without fast recovery**:
```
Loss detected → ssthresh = cwnd / 2
              → cwnd = 1
              → Slow start from 1
              → Slow!
```

**With fast recovery** (Reno algorithm):
```
Loss detected (3 dup ACKs):
  1. ssthresh = cwnd / 2
  2. cwnd = ssthresh + 3     (Inflate for 3 dup ACKs)
  3. For each additional dup ACK: cwnd += 1
  4. On new ACK: cwnd = ssthresh (deflate)
  5. Enter congestion avoidance
```

**Illustration**:
```
cwnd before loss: 20

Fast retransmit triggered:
  ssthresh = 20 / 2 = 10
  cwnd = 10 + 3 = 13

3 more dup ACKs arrive:
  cwnd = 13 + 3 = 16

New ACK arrives (retransmit successful):
  cwnd = 10 (deflate to ssthresh)
  Continue in congestion avoidance
```

**Benefits**:
- Maintain ~half of previous cwnd
- No slow start penalty
- Faster recovery

### NewReno

**Problem with Reno**: Multiple losses in one window

**Reno behavior**:
```
Window: 1 2 3 4 5 6 7 8
Lost:   X       X       (Two losses)

Fast retransmit: Retransmit 1
Partial ACK received (only ACK 1)
→ Exit fast recovery
→ Another timeout needed for 5
→ Inefficient!
```

**NewReno improvement**:
```
Stay in fast recovery until all outstanding data ACKed
→ Partial ACK → Retransmit next lost packet
→ Handles multiple losses in one window
→ No premature exit from fast recovery
```

**Configuration**:
```bash
# NewReno typically enabled by default (kernel implementation)
# No explicit sysctl parameter
```

### SACK-based Recovery

**Even better with SACK**:
```
Window: 1 2 3 4 5 6 7 8
Lost:   X       X

SACK: 2-3, 4, 6-8
→ Sender knows exactly which packets lost (1 and 5)
→ Retransmit only 1 and 5
→ Most efficient recovery
```

**Why SACK is essential**:
- Precise loss detection
- Minimal retransmissions
- Faster recovery

---

## TCP Performance Metrics

### Key Metrics

**Throughput**:
```
Throughput = Data Transferred / Time
Units: Mbps, Gbps, MB/s

Theoretical max:
Throughput ≤ Window Size / RTT

Example:
Window = 128 KB, RTT = 100 ms
Max Throughput = 128 KB / 0.1s = 1.28 MB/s = 10.24 Mbps
```

**Round-Trip Time (RTT)**:
```
RTT = Time for packet round trip
Includes: Propagation + Transmission + Queuing + Processing

Components:
- Propagation: Distance / Speed of light
- Transmission: Packet size / Link bandwidth
- Queuing: Wait time in router queues
- Processing: Router/host processing time

Measuring RTT:
ping example.com
ss -tin | grep rtt
```

**Retransmission Rate**:
```
Retransmission Rate = Retransmitted Packets / Total Packets

Good: < 0.1% (1 in 1000)
Acceptable: < 1% (1 in 100)
Poor: > 1%

Check:
nstat TcpRetransSegs
```

**Packet Loss Rate**:
```
Packet Loss = Lost Packets / Total Packets

Good: < 0.01% (1 in 10,000)
Acceptable: < 0.1% (1 in 1,000)
Poor: > 1%

Measure:
mtr --report --report-cycles 100 example.com
```

**Congestion Window (cwnd)**:
```
cwnd = Sender's estimate of network capacity

Ideal: cwnd ≈ BDP (Bandwidth-Delay Product)

Check:
ss -tin | grep cwnd

Example output:
  cwnd:10 ssthresh:7 bytes_acked:12000
```

**Slow Start Threshold (ssthresh)**:
```
ssthresh = Threshold for switching from slow start to congestion avoidance

After loss: ssthresh = cwnd / 2

Check:
ss -tin | grep ssthresh
```

**Receive Window (rwnd)**:
```
rwnd = Receiver's available buffer space

Advertised to sender in every ACK

Check:
ss -tin | grep rcv_space
```

### Collecting Metrics

**ss (socket statistics)**:
```bash
# Basic connection info
ss -tan

# With TCP info (cwnd, rtt, retrans)
ss -tin

# Specific connection
ss -tin dst <ip> dport = <port>

# Example output:
ESTAB  0  0  192.168.1.100:45678  93.184.216.34:443
         cubic wscale:7,7 rto:204 rtt:1.5/0.5 cwnd:10 ssthresh:7
         bytes_acked:12000 bytes_received:50000 segs_out:20 segs_in:30
         send 80.0Mbps lastsnd:100 lastrcv:100 lastack:100
         retrans:0/0 rcv_space:29200
```

**nstat (network statistics)**:
```bash
# All TCP statistics
nstat -az | grep Tcp

# Key metrics
nstat TcpActiveOpens      # Outbound connections
nstat TcpPassiveOpens     # Inbound connections
nstat TcpRetransSegs      # Retransmissions
nstat TcpInSegs           # Segments received
nstat TcpOutSegs          # Segments sent
nstat TcpExtTCPLoss       # Packet loss events

# Reset and measure delta
nstat -z && sleep 60 && nstat TcpRetransSegs
```

**iperf3 (throughput testing)**:
```bash
# Server
iperf3 -s

# Client
iperf3 -c <server> -t 60 -i 5 -P 4

# Output:
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-60.00  sec  7.00 GBytes   1.00 Gbits/sec    0    sender
[  5]   0.00-60.00  sec  6.99 GBytes   1.00 Gbits/sec         receiver
```

**tcpdump (packet capture)**:
```bash
# Capture TCP packets
tcpdump -i eth0 -nn 'tcp' -w capture.pcap

# Analyze in Wireshark or tcpdump
tcpdump -r capture.pcap -nn

# Extract TCP info
tcpdump -r capture.pcap -nn 'tcp' -v | grep -E "win|length"
```

### Performance Formulas

**Mathis equation** (throughput with packet loss):
```
Throughput = (MSS / RTT) × (C / √Loss)

Where:
- MSS: Maximum Segment Size (typically 1460 bytes)
- RTT: Round-trip time
- C: Constant (typically ~1.22 for Reno, ~1.31 for others)
- Loss: Packet loss rate

Example:
MSS = 1460, RTT = 100ms, Loss = 0.1% (0.001)
Throughput = (1460 / 0.1) × (1.22 / √0.001)
           = 14600 × 38.6
           = 564 KB/s = 4.5 Mbps
```

**Bandwidth-Delay Product** (optimal window):
```
BDP = Bandwidth × RTT

Required window ≥ BDP for full utilization

Example:
10 Gbps × 100ms = 1.25 Gb = 125 MB
→ Need 125 MB window for full throughput
```

**Goodput** (application-level throughput):
```
Goodput = (Data Transferred - Retransmitted) / Time

Overhead from:
- TCP headers (20 bytes)
- IP headers (20 bytes)
- Ethernet headers (14 bytes)
- Retransmissions

Goodput / Throughput ≈ 0.95-0.98 (good network)
```

### Monitoring Dashboards

**Prometheus + Grafana metrics**:
```yaml
# Prometheus node_exporter metrics
- node_netstat_Tcp_RetransSegs
- node_netstat_Tcp_InSegs
- node_netstat_Tcp_OutSegs
- node_netstat_Tcp_CurrEstab

# Derived metrics
retransmit_rate = rate(node_netstat_Tcp_RetransSegs[5m]) / rate(node_netstat_Tcp_OutSegs[5m])
```

**Example Grafana queries**:
```promql
# Retransmission rate
rate(node_netstat_Tcp_RetransSegs[5m]) / rate(node_netstat_Tcp_OutSegs[5m]) * 100

# Active connections
node_netstat_Tcp_CurrEstab

# Connection rate
rate(node_netstat_Tcp_PassiveOpens[5m]) + rate(node_netstat_Tcp_ActiveOpens[5m])
```

---

## High-Performance TCP

### Data Center Tuning

**Characteristics**:
- Low latency (< 1ms RTT)
- High bandwidth (10-100 Gbps)
- Reliable network
- Controlled environment

**Optimal configuration**:
```bash
# Moderate buffers (low RTT × high BW)
net.ipv4.tcp_rmem = 4096 87380 33554432        # 32 MB
net.ipv4.tcp_wmem = 4096 65536 33554432
net.core.rmem_max = 33554432
net.core.wmem_max = 33554432

# BBR or DCTCP
net.ipv4.tcp_congestion_control = bbr          # or dctcp
net.core.default_qdisc = fq

# ECN for DCTCP
net.ipv4.tcp_ecn = 1

# Fast connection handling
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_max_tw_buckets = 2000000

# Large initial cwnd
ip route change default via <gateway> dev eth0 initcwnd 100

# TCP offloading
ethtool -K eth0 tso on gso on gro on

# Jumbo frames (if supported)
ip link set eth0 mtu 9000
```

### WAN Optimization

**Characteristics**:
- High latency (50-200ms RTT)
- High bandwidth (1-10 Gbps)
- Variable conditions
- Potential packet loss

**Optimal configuration**:
```bash
# Large buffers for high BDP
# BDP = 10 Gbps × 0.1s = 125 MB
net.ipv4.tcp_rmem = 4096 131072 268435456      # 256 MB
net.ipv4.tcp_wmem = 4096 131072 268435456
net.core.rmem_max = 268435456
net.core.wmem_max = 268435456

# BBR (handles latency and loss well)
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq

# Window scaling (essential!)
net.ipv4.tcp_window_scaling = 1

# SACK (handle loss efficiently)
net.ipv4.tcp_sack = 1
net.ipv4.tcp_dsack = 1

# Don't reset after idle
net.ipv4.tcp_slow_start_after_idle = 0

# Timestamps
net.ipv4.tcp_timestamps = 1

# TCP offloading
ethtool -K eth0 tso on gso on gro on
```

### 100 Gbps Tuning

**Extreme performance requirements**:

```bash
# Massive buffers
# BDP = 100 Gbps × 0.1s = 1.25 GB
net.ipv4.tcp_rmem = 4096 131072 1073741824     # 1 GB
net.ipv4.tcp_wmem = 4096 131072 1073741824
net.core.rmem_max = 1073741824
net.core.wmem_max = 1073741824

# Large memory allocation
net.ipv4.tcp_mem = 2097152 4194304 8388608     # 32 GB max

# BBR v2 (if available)
net.ipv4.tcp_congestion_control = bbr2
net.core.default_qdisc = fq

# Large backlog
net.core.netdev_max_backlog = 100000
net.core.netdev_budget = 600

# Multiple RSS queues
ethtool -L eth0 combined 64

# CPU isolation
# isolcpus kernel parameter
# Dedicate CPUs for network processing

# Jumbo frames
ip link set eth0 mtu 9000

# Hardware offloading
ethtool -K eth0 tso on gso on gro on

# Interrupt coalescing tuning
ethtool -C eth0 adaptive-rx on adaptive-tx on
```

### RDMA and Kernel Bypass

**RDMA** (Remote Direct Memory Access):
- Bypass kernel networking stack
- Direct memory-to-memory transfer
- Ultra-low latency (< 1 μs)
- Zero CPU overhead

**Technologies**:
- **InfiniBand**: Dedicated RDMA fabric
- **RoCE** (RDMA over Converged Ethernet): RDMA over Ethernet
- **iWARP**: RDMA over TCP/IP

**User-space networking**:
- **DPDK** (Data Plane Development Kit)
- **XDP** (eXpress Data Path)
- Complete kernel bypass

**When to use**:
- HPC (High-Performance Computing)
- Low-latency trading
- Storage networks (NVMe-oF)
- Database clusters

---

## TCP Over Wireless

### Challenges

**Wireless characteristics**:
- **Packet loss** from interference (not congestion!)
- **Variable latency**
- **Bandwidth fluctuation**
- **Handoff** between cells

**TCP assumptions violated**:
- TCP assumes loss = congestion
- Wireless loss triggers congestion control
- Cwnd reduced unnecessarily
- Poor throughput

### Optimization Strategies

**1. BBR congestion control**:
```bash
# BBR doesn't rely on loss signals
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq
```

**2. SACK and D-SACK**:
```bash
# Handle reordering and out-of-order delivery
net.ipv4.tcp_sack = 1
net.ipv4.tcp_dsack = 1
```

**3. Conservative timeouts**:
```bash
# Don't timeout too quickly
net.ipv4.tcp_retries2 = 15
```

**4. Shorter keep-alive**:
```bash
# Detect dead connections faster
net.ipv4.tcp_keepalive_time = 300      # 5 min
net.ipv4.tcp_keepalive_intvl = 30      # 30 sec
net.ipv4.tcp_keepalive_probes = 3
```

**5. Moderate buffers**:
```bash
# Balance throughput and latency
net.ipv4.tcp_rmem = 4096 131072 16777216       # 16 MB
net.ipv4.tcp_wmem = 4096 65536 16777216
```

### Mobile-Specific Tuning

**Android/iOS optimization**:
```bash
# Client-side tuning
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_sack = 1
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_fastopen = 3

# Connection management
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_fin_timeout = 30
```

**Server-side for mobile clients**:
```bash
# Tolerate mobile network characteristics
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_fastopen = 3

# Larger initial cwnd (help mobile clients)
ip route change default via <gateway> initcwnd 10

# Keep connections alive through NAT
net.ipv4.tcp_keepalive_time = 300
```

### Wi-Fi Optimization

**Access Point (AP) tuning**:
- Reduce beacon interval
- Enable frame aggregation (A-MPDU, A-MSDU)
- Optimize channel width
- Enable MCS rate control

**Client tuning**:
```bash
# Power management
# (Balance power saving vs latency)

# For Linux clients
iwconfig wlan0 power off               # Disable power saving

# Or moderate power saving
iw dev wlan0 set power_save on
```

---

## Cloud Optimization

### AWS

**EC2 Enhanced Networking**:
- **Intel 82599 VF** (up to 10 Gbps): Older instances
- **ENA** (Elastic Network Adapter, up to 100 Gbps): Modern instances
- **EFA** (Elastic Fabric Adapter): HPC with RDMA

**Enabling Enhanced Networking**:
```bash
# Check ENA module loaded
lsmod | grep ena

# Check ENA driver version
modinfo ena

# Update ENA driver
sudo apt install linux-aws
```

**Placement Groups**:
```
Cluster: Low latency, high bandwidth (same AZ)
Partition: Fault isolation (different racks)
Spread: Maximize availability (different hosts)
```

**Jumbo Frames**:
```bash
# MTU 9001 within VPC
ip link set dev eth0 mtu 9001

# Test
ping -M do -s 8973 <internal-ip>
# 8973 + 28 (IP+ICMP headers) = 9001
```

**AWS-specific tuning**:
```bash
# Large buffers for 10+ Gbps
net.ipv4.tcp_rmem = 4096 131072 134217728
net.ipv4.tcp_wmem = 4096 131072 134217728
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728

# BBR
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq

# TCP offloading
ethtool -K eth0 tso on gso on gro on

# RSS queues (match vCPUs)
ethtool -L eth0 combined $(nproc)

# Instance-specific
# c5n.18xlarge: 100 Gbps, tune accordingly
```

### GCP

**gVNIC** (Google Virtual NIC):
- Up to 100 Gbps
- Required for N2, C2, M2 VMs

**Enabling gVNIC**:
```bash
# Check gVNIC loaded
lsmod | grep gvnic

# Check gVNIC queues
ethtool -l eth0
```

**Tier_1 Networking**:
- Premium network tier
- Global load balancing
- Lower latency

**GCP-specific tuning**:
```bash
# Similar to AWS
net.ipv4.tcp_rmem = 4096 131072 134217728
net.ipv4.tcp_wmem = 4096 131072 134217728
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728

# BBR (Google developed)
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq

# MTU 8896 (GCP jumbo frames)
ip link set dev eth0 mtu 8896

# TCP offloading
ethtool -K eth0 tso on gso on gro on

# RSS queues
ethtool -L eth0 combined $(nproc)
```

### Azure

**Accelerated Networking**:
- SR-IOV (Single Root I/O Virtualization)
- Up to 30 Gbps
- Supported on most VM sizes

**Enabling Accelerated Networking**:
```bash
# Check Mellanox driver loaded
lsmod | grep mlx

# Check driver version
modinfo mlx5_core
```

**Azure-specific tuning**:
```bash
# Large buffers
net.ipv4.tcp_rmem = 4096 131072 134217728
net.ipv4.tcp_wmem = 4096 131072 134217728
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728

# BBR
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq

# TCP offloading
ethtool -K eth0 tso on gso on gro on

# RSS queues
ethtool -L eth0 combined $(nproc)
```

### Multi-Cloud Best Practices

**Universal tuning**:
```bash
#!/bin/bash
# Works across AWS, GCP, Azure

# Detect cloud provider
if grep -qi amazon /sys/class/dmi/id/bios_version; then
    CLOUD="AWS"
    MTU=9001
elif grep -qi google /sys/class/dmi/id/bios_version; then
    CLOUD="GCP"
    MTU=8896
elif grep -qi microsoft /sys/class/dmi/id/bios_version; then
    CLOUD="Azure"
    MTU=1500  # Accelerated Networking uses 1500
else
    CLOUD="Unknown"
    MTU=1500
fi

echo "Detected cloud: $CLOUD"

# Set MTU
ip link set dev eth0 mtu $MTU

# Universal TCP tuning
sysctl -w net.ipv4.tcp_rmem="4096 131072 134217728"
sysctl -w net.ipv4.tcp_wmem="4096 131072 134217728"
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.wmem_max=134217728
sysctl -w net.ipv4.tcp_congestion_control=bbr
sysctl -w net.core.default_qdisc=fq
sysctl -w net.ipv4.tcp_window_scaling=1
sysctl -w net.ipv4.tcp_sack=1
sysctl -w net.ipv4.tcp_timestamps=1

# TCP offloading
ethtool -K eth0 tso on gso on gro on

echo "TCP tuning complete for $CLOUD"
```

---

## Container Networking

### Docker

**Default networking**:
- **bridge**: NAT, performance overhead
- **host**: Direct host network, best performance
- **overlay**: Multi-host networking

**Performance comparison**:
```
Bridge:  ~50-70% of bare metal (NAT overhead)
Host:    ~95-99% of bare metal (minimal overhead)
Overlay: ~60-80% of bare metal (encapsulation overhead)
```

**Host network mode** (best performance):
```bash
docker run --network host <image>
```

**Docker tuning**:
```bash
# Host sysctl applies to containers in host mode

# Bridge mode optimization
# Increase bridge MTU
ip link set docker0 mtu 9000

# Docker daemon config (/etc/docker/daemon.json)
{
  "mtu": 9000,
  "userland-proxy": false
}

sudo systemctl restart docker
```

### Kubernetes

**CNI plugins** (Container Network Interface):
- **Calico**: Layer 3, no encapsulation, best performance
- **Flannel**: Simple, VXLAN encapsulation
- **Cilium**: eBPF, advanced features
- **Weave**: Easy setup, encryption support

**Performance ranking**:
```
1. Host network (no CNI)
2. Calico (native routing)
3. Cilium (eBPF)
4. Flannel (VXLAN)
5. Weave (encapsulation + encryption)
```

**Host network in Kubernetes**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: high-performance-pod
spec:
  hostNetwork: true           # Use host network
  containers:
  - name: app
    image: myapp:latest
```

**Calico tuning**:
```yaml
# Calico configuration
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Increase MTU (if jumbo frames supported)
  mtu: 9000

  # Enable eBPF dataplane (Linux 5.3+)
  bpfEnabled: true

  # Disable IP-in-IP (use native routing)
  ipipEnabled: false
```

**Node tuning for Kubernetes**:
```bash
# Apply on all worker nodes

# Large buffers
sysctl -w net.ipv4.tcp_rmem="4096 131072 67108864"
sysctl -w net.ipv4.tcp_wmem="4096 131072 67108864"
sysctl -w net.core.rmem_max=67108864
sysctl -w net.core.wmem_max=67108864

# BBR
sysctl -w net.ipv4.tcp_congestion_control=bbr
sysctl -w net.core.default_qdisc=fq

# Connection handling (many pods)
sysctl -w net.ipv4.ip_local_port_range="10000 65535"
sysctl -w net.ipv4.tcp_tw_reuse=1
sysctl -w net.ipv4.tcp_fin_timeout=15
sysctl -w net.core.somaxconn=8192

# Large conntrack table
sysctl -w net.netfilter.nf_conntrack_max=1000000
sysctl -w net.netfilter.nf_conntrack_buckets=250000

# Forwarding
sysctl -w net.ipv4.ip_forward=1

# Make persistent
cat <<EOF | sudo tee /etc/sysctl.d/99-k8s-tuning.conf
net.ipv4.tcp_rmem = 4096 131072 67108864
net.ipv4.tcp_wmem = 4096 131072 67108864
net.core.rmem_max = 67108864
net.core.wmem_max = 67108864
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq
net.ipv4.ip_local_port_range = 10000 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.core.somaxconn = 8192
net.netfilter.nf_conntrack_max = 1000000
net.ipv4.ip_forward = 1
EOF

sysctl -p /etc/sysctl.d/99-k8s-tuning.conf
```

**Cilium with eBPF**:
```bash
# Install Cilium with eBPF dataplane
helm install cilium cilium/cilium \
  --namespace kube-system \
  --set bpf.masquerade=true \
  --set bpf.hostRouting=true \
  --set ipam.mode=kubernetes \
  --set kubeProxyReplacement=strict
```

---

## Load Balancer TCP Optimization

### HAProxy

**TCP mode configuration**:
```
# /etc/haproxy/haproxy.cfg

global
    maxconn 100000
    tune.bufsize 32768
    tune.maxrewrite 8196
    nbproc 4
    nbthread 8

defaults
    mode tcp
    option tcplog
    option dontlognull
    timeout connect 5s
    timeout client 50s
    timeout server 50s

frontend tcp_front
    bind *:80
    default_backend tcp_back

backend tcp_back
    balance roundrobin
    option tcp-check
    server srv1 192.168.1.10:80 check
    server srv2 192.168.1.11:80 check
```

**Performance tuning**:
```
global
    # Connection limits
    maxconn 100000

    # SSL/TLS
    tune.ssl.default-dh-param 2048
    ssl-default-bind-ciphers ECDHE-RSA-AES128-GCM-SHA256
    ssl-default-bind-options no-sslv3 no-tlsv10

    # Buffer tuning
    tune.bufsize 32768             # Buffer size per connection
    tune.maxrewrite 8192           # Header rewrite space

    # Multi-threading
    nbthread 8                     # Match CPU cores

    # Queue sizes
    tune.maxaccept 256             # Accept queue

defaults
    # Keep-alive
    option http-keep-alive
    timeout http-keep-alive 60s

    # Timeouts
    timeout connect 5s
    timeout client 60s
    timeout server 60s
    timeout queue 30s

    # Health checks
    option tcp-check
    default-server inter 10s fall 3 rise 2
```

**Source IP preservation**:
```
# Proxy Protocol v2
frontend tcp_front
    bind *:80
    mode tcp
    tcp-request connection send-proxy-v2

backend tcp_back
    mode tcp
    source 0.0.0.0 usesrc clientip
    server srv1 192.168.1.10:80 send-proxy-v2
```

### Nginx

**TCP stream module**:
```nginx
# /etc/nginx/nginx.conf

stream {
    upstream tcp_backend {
        least_conn;
        server 192.168.1.10:80 max_fails=3 fail_timeout=30s;
        server 192.168.1.11:80 max_fails=3 fail_timeout=30s;
    }

    server {
        listen 80;
        proxy_pass tcp_backend;
        proxy_connect_timeout 5s;
        proxy_timeout 60s;
    }
}
```

**Performance tuning**:
```nginx
user nginx;
worker_processes auto;          # Match CPU cores
worker_rlimit_nofile 100000;

events {
    worker_connections 10000;
    use epoll;
    multi_accept on;
}

stream {
    # TCP optimizations
    tcp_nodelay on;
    tcp_nopush on;

    # Timeouts
    proxy_connect_timeout 10s;
    proxy_timeout 60s;

    # Buffer sizes
    proxy_buffer_size 16k;

    upstream tcp_backend {
        least_conn;
        keepalive 100;              # Connection pool
        server 192.168.1.10:80;
        server 192.168.1.11:80;
    }

    server {
        listen 80 reuseport;        # SO_REUSEPORT for multi-worker
        proxy_pass tcp_backend;
    }
}
```

### Envoy

**TCP proxy configuration**:
```yaml
# envoy.yaml

static_resources:
  listeners:
  - name: tcp_listener
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 80
    filter_chains:
    - filters:
      - name: envoy.filters.network.tcp_proxy
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.tcp_proxy.v3.TcpProxy
          stat_prefix: tcp
          cluster: tcp_cluster
          access_log:
          - name: envoy.access_loggers.stdout
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.access_loggers.stream.v3.StdoutAccessLog

  clusters:
  - name: tcp_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: tcp_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: 192.168.1.10
                port_value: 80
        - endpoint:
            address:
              socket_address:
                address: 192.168.1.11
                port_value: 80

    # TCP tuning
    upstream_connection_options:
      tcp_keepalive:
        keepalive_time: 300
        keepalive_interval: 60
        keepalive_probes: 3
```

### Linux IPVS (LVS)

**High-performance L4 load balancing**:
```bash
# Install ipvsadm
apt install ipvsadm

# Create virtual service
ipvsadm -A -t 192.168.1.100:80 -s rr    # Round robin

# Add real servers
ipvsadm -a -t 192.168.1.100:80 -r 192.168.1.10:80 -m
ipvsadm -a -t 192.168.1.100:80 -r 192.168.1.11:80 -m

# Forwarding modes:
# -m: Masquerading (NAT)
# -g: Direct Routing (DSR) - fastest
# -i: IP tunneling

# Save rules
ipvsadm-save > /etc/ipvsadm.rules
```

**IPVS tuning**:
```bash
# Connection timeouts
ipvsadm --set 900 120 300    # TCP, TCPFIN, UDP timeouts

# Scheduler algorithms
ipvsadm -A -t 192.168.1.100:80 -s rr     # Round robin
ipvsadm -A -t 192.168.1.100:80 -s lc     # Least connection
ipvsadm -A -t 192.168.1.100:80 -s wlc    # Weighted least connection

# Connection tracking
sysctl -w net.ipv4.vs.conn_reuse_mode=1
sysctl -w net.ipv4.vs.conntrack=1
```

---

## TLS/SSL Impact on TCP

### Handshake Overhead

**TLS 1.2 handshake** (2 RTTs):
```
Client → ClientHello → Server
Client ← ServerHello, Certificate, ServerHelloDone ← Server
Client → ClientKeyExchange, ChangeCipherSpec, Finished → Server
Client ← ChangeCipherSpec, Finished ← Server
Client → Application Data → Server
```

**TLS 1.3 handshake** (1 RTT):
```
Client → ClientHello (+ Key Share) → Server
Client ← ServerHello, Certificate, Finished ← Server
Client → Application Data → Server
```

**Performance impact**:
- TLS 1.2: +2 RTTs (additional delay)
- TLS 1.3: +1 RTT (50% improvement)
- 0-RTT resumption: +0 RTT (subsequent connections)

### TCP Effects

**Segment size reduction**:
```
Without TLS: MSS = 1460 bytes (Ethernet MTU 1500 - 40 headers)
With TLS:    Payload = 1460 - TLS overhead (13-29 bytes)
             → ~1431-1447 bytes usable payload
```

**Increased round trips**:
```
HTTP: TCP handshake (1 RTT) + Request/Response (1 RTT) = 2 RTTs
HTTPS: TCP (1 RTT) + TLS 1.3 (1 RTT) + Request/Response (1 RTT) = 3 RTTs
HTTPS: TCP (1 RTT) + TLS 1.2 (2 RTTs) + Request/Response (1 RTT) = 4 RTTs
```

**Throughput impact**:
```
TLS encryption/decryption overhead: 5-20% CPU
Throughput reduction: ~10-30% (depends on CPU, cipher)
```

### Optimization Strategies

**1. TLS 1.3**:
```
# Nginx
ssl_protocols TLSv1.3;

# OpenSSL
SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);
```

**2. Session resumption**:
```nginx
# Session tickets (stateless)
ssl_session_tickets on;
ssl_session_timeout 24h;

# Session cache (stateful)
ssl_session_cache shared:SSL:50m;
ssl_session_timeout 24h;
```

**3. 0-RTT (TLS 1.3)**:
```nginx
ssl_early_data on;

# Warning: Replay attack risk
# Only use for idempotent requests
```

**4. Hardware acceleration**:
```bash
# Check CPU supports AES-NI
grep aes /proc/cpuinfo

# OpenSSL with AES-NI
openssl speed -evp aes-128-gcm    # Test throughput

# Enable AES-NI in application
```

**5. Optimized ciphers**:
```nginx
# Prefer fast, secure ciphers
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
ssl_prefer_server_ciphers on;

# ChaCha20-Poly1305 (fast on mobile without AES-NI)
ssl_ciphers 'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256';
```

**6. OCSP stapling**:
```nginx
# Avoid client OCSP lookup (saves 1 RTT)
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
```

**7. TLS record size**:
```python
# Python example
import ssl

context = ssl.create_default_context()
# Smaller records = lower latency, but more overhead
# Larger records = higher throughput, but more latency
context.maximum_version = ssl.TLSVersion.TLSv1_3
```

### Monitoring TLS Performance

**OpenSSL s_time**:
```bash
openssl s_time -connect example.com:443 -time 60 -www /
# Reports: connections/sec, bytes transferred
```

**ssllabs.com**:
```
Online tool for TLS configuration analysis
- Protocol support
- Cipher strength
- Certificate validation
- Performance metrics
```

**tcpdump analysis**:
```bash
# Capture TLS handshake
tcpdump -i eth0 -nn 'port 443' -w tls.pcap

# Analyze in Wireshark
# Statistics → TCP Stream Graphs → Time-Sequence Graph (Stevens)
```

---

## Testing and Benchmarking

### iperf3

**Basic throughput test**:
```bash
# Server
iperf3 -s

# Client (10 second test)
iperf3 -c <server> -t 10

# Output:
[  5]   0.00-10.00  sec  1.09 GBytes   938 Mbits/sec    0  sender
[  5]   0.00-10.00  sec  1.09 GBytes   937 Mbits/sec       receiver
```

**Advanced options**:
```bash
# Multiple parallel streams
iperf3 -c <server> -P 4          # 4 parallel TCP streams

# Specific bandwidth target
iperf3 -c <server> -b 1G         # Target 1 Gbps

# Reverse mode (server sends)
iperf3 -c <server> -R

# Bidirectional
iperf3 -c <server> --bidir

# Specific congestion control
iperf3 -c <server> -C bbr

# JSON output
iperf3 -c <server> -J > results.json

# UDP test
iperf3 -c <server> -u -b 1G      # UDP at 1 Gbps

# Interval reports
iperf3 -c <server> -t 60 -i 5    # 60 sec, report every 5 sec
```

**Interpreting results**:
```
[  5]   0.00-10.00  sec  1.09 GBytes   938 Mbits/sec    125  sender
                                                         ↑ Retransmits

Retransmits > 0: Network issues or buffer problems
Low throughput: Check cwnd, buffers, RTT
```

### netperf

**TCP throughput**:
```bash
# Server
netserver

# Client
netperf -H <server> -t TCP_STREAM -l 60

# Output:
Recv   Send    Send
Socket Socket  Message  Elapsed
Size   Size    Size     Time     Throughput
bytes  bytes   bytes    secs.    Mbps

87380  16384  16384    60.00    938.42
```

**Request/response latency**:
```bash
# TCP_RR (request-response)
netperf -H <server> -t TCP_RR

# Output: transactions/sec

# With 1-byte request/response
netperf -H <server> -t TCP_RR -- -r 1,1

# With 1KB request, 16KB response
netperf -H <server> -t TCP_RR -- -r 1024,16384
```

**Connection rate**:
```bash
# TCP_CRR (connect-request-response-close)
netperf -H <server> -t TCP_CRR

# Output: connections/sec
```

### qperf

**Comprehensive network testing**:
```bash
# Server
qperf

# Client

# TCP bandwidth
qperf <server> tcp_bw

# TCP latency
qperf <server> tcp_lat

# RDMA (if available)
qperf <server> rc_bw      # Reliable Connection bandwidth
qperf <server> rc_lat     # Reliable Connection latency

# Multiple tests
qperf <server> tcp_bw tcp_lat

# With options
qperf <server> -t 60 tcp_bw   # 60 second test
```

### nuttcp

**Simple throughput test**:
```bash
# Server
nuttcp -S

# Client
nuttcp <server>

# Specific options
nuttcp -t 60 <server>         # 60 second test
nuttcp -r <server>            # Receive mode (server sends)
nuttcp -w4m <server>          # 4MB window
```

### tcpdump Performance Analysis

**Capture for analysis**:
```bash
# Capture TCP packets
tcpdump -i eth0 -nn 'tcp' -w capture.pcap

# Capture specific connection
tcpdump -i eth0 -nn 'host <ip> and port <port>' -w capture.pcap

# With timestamps
tcpdump -i eth0 -nn -ttt 'tcp' -w capture.pcap
```

**Analyze retransmissions**:
```bash
# Extract retransmits
tcpdump -r capture.pcap -nn 'tcp[tcpflags] & tcp-syn != 0 or tcp[tcpflags] & tcp-fin != 0' | wc -l
```

**Wireshark analysis**:
```
Statistics → TCP Stream Graphs → Throughput
Statistics → TCP Stream Graphs → Round Trip Time
Statistics → TCP Stream Graphs → Window Scaling

Analyze → Expert Information
→ Notes/Warnings for retransmissions, zero windows, etc.
```

### Baseline Testing

**Establish baseline**:
```bash
#!/bin/bash
# baseline_test.sh

SERVER="192.168.1.100"
DURATION=60

echo "=== TCP Throughput (iperf3) ==="
iperf3 -c $SERVER -t $DURATION -P 4

echo ""
echo "=== TCP Latency (qperf) ==="
qperf $SERVER tcp_lat

echo ""
echo "=== Connection Rate (netperf TCP_CRR) ==="
netperf -H $SERVER -t TCP_CRR -l 10

echo ""
echo "=== Retransmission Rate ==="
nstat -z >/dev/null && sleep 60 && nstat TcpRetransSegs TcpOutSegs | awk '
/TcpRetransSegs/ { retrans=$2 }
/TcpOutSegs/ { out=$2 }
END { if (out > 0) printf "Retransmission rate: %.2f%%\n", (retrans/out)*100 }
'

echo ""
echo "=== TCP Connection Stats ==="
ss -s
```

**Before/after comparison**:
```bash
# Save baseline
./baseline_test.sh > baseline.txt

# Apply tuning
./optimize_tcp.sh --profile datacenter

# Test again
./baseline_test.sh > optimized.txt

# Compare
diff -y baseline.txt optimized.txt
```

---

## Monitoring Tools

### ss (Socket Statistics)

**Basic usage**:
```bash
# All TCP connections
ss -tan

# State-specific
ss -tan state established
ss -tan state syn-sent
ss -tan state time-wait

# With process info
ss -tanp

# With TCP info
ss -tin

# Specific destination
ss -tan dst <ip>
ss -tan dst <ip> dport = <port>
```

**TCP info fields**:
```bash
ss -tin | head -5

# Example output:
ESTAB  0  0  192.168.1.100:45678  93.184.216.34:443
         cubic wscale:7,7 rto:204 rtt:1.5/0.5 ato:40 mss:1460 pmtu:1500
         rcvmss:1460 advmss:1460 cwnd:10 ssthresh:7 bytes_acked:12000
         bytes_received:50000 segs_out:20 segs_in:30 data_segs_out:10
         data_segs_in:15 send 80.0Mbps lastsnd:100 lastrcv:100 lastack:100
         pacing_rate 160.0Mbps delivery_rate 80.0Mbps busy:1000ms
         retrans:0/0 dsack_dups:0 rcv_rtt:2 rcv_space:29200 rcv_ssthresh:64088
         minrtt:0.5

Field explanation:
- cubic: Congestion control algorithm
- wscale:7,7: Window scale factors (send, receive)
- rto:204: Retransmission timeout (ms)
- rtt:1.5/0.5: RTT smooth/variance (ms)
- cwnd:10: Congestion window (segments)
- ssthresh:7: Slow start threshold
- bytes_acked: Total bytes acknowledged
- segs_out: Segments sent
- retrans:0/0: Retransmits (current/total)
- rcv_space: Receive buffer auto-tuned size
```

**Filtering and analysis**:
```bash
# Connections with retransmits
ss -tin | grep -B1 "retrans:[1-9]"

# Connections with small cwnd
ss -tin | grep -B1 "cwnd:[1-9] "

# High RTT connections
ss -tin | awk '/rtt:/ && $0 ~ /rtt:[0-9]{3}/ {print}'

# Summary by state
ss -tan | awk '{print $1}' | sort | uniq -c
```

### nstat (Network Statistics)

**Usage**:
```bash
# All statistics
nstat -az

# TCP only
nstat -az | grep Tcp

# Key metrics
nstat TcpActiveOpens        # Outbound connections
nstat TcpPassiveOpens       # Inbound connections
nstat TcpInSegs             # Segments received
nstat TcpOutSegs            # Segments sent
nstat TcpRetransSegs        # Retransmissions
nstat TcpExtTCPLoss         # Packet loss events
nstat TcpExtTCPTimeouts     # Timeouts

# Delta measurement
nstat -z                    # Zero counters
sleep 60                    # Wait 1 minute
nstat TcpRetransSegs        # Show new retransmits

# Retransmission rate
nstat TcpRetransSegs TcpOutSegs | awk '
/TcpRetransSegs/ { r=$2 }
/TcpOutSegs/ { o=$2 }
END { printf "Retransmit rate: %.2f%%\n", (r/o)*100 }
'
```

**Important counters**:
```bash
# Connection management
TcpActiveOpens          # Outbound connection attempts
TcpPassiveOpens         # Inbound connections accepted
TcpAttemptFails         # Failed connection attempts
TcpEstabResets          # Connections reset (established)
TcpCurrEstab            # Currently established connections

# Data transfer
TcpInSegs               # Segments received
TcpOutSegs              # Segments sent
TcpRetransSegs          # Segments retransmitted

# Errors
TcpInErrs               # Segments received with errors
TcpInCsumErrors         # Checksum errors
TcpExtTCPLoss           # Packet loss detected
TcpExtTCPTimeouts       # Retransmission timeouts

# Fast path
TcpExtTCPHPHits         # Fast path hits
TcpExtTCPHPHitsToUser   # Fast path to user

# SACK
TcpExtTCPSACKReorder    # SACK reordering events
TcpExtTCPSACKDiscard    # SACK discarded

# Congestion control
TcpExtTCPLossProbes     # Probe for losses
TcpExtTCPLossProbeRecovery  # Recoveries from probes
```

### ethtool

**Check settings**:
```bash
# Link status and speed
ethtool eth0

# Offload features
ethtool -k eth0

# Statistics
ethtool -S eth0

# Driver info
ethtool -i eth0

# Ring buffer sizes
ethtool -g eth0

# Interrupt coalescing
ethtool -c eth0

# RSS/queue information
ethtool -l eth0
ethtool -x eth0
```

**Monitor drops**:
```bash
# Interface statistics
ethtool -S eth0 | grep -E "drop|error|miss"

# Example output:
rx_dropped: 0
tx_dropped: 0
rx_errors: 0
tx_errors: 0
rx_missed_errors: 125     # Packets dropped by NIC (buffer full)
```

### eBPF Tools

**bcc-tools**:
```bash
# Install
apt install bpfcc-tools

# TCP connection tracing
tcpconnect              # Trace new TCP connections
tcpaccept               # Trace TCP passive connections
tcpconnlat              # TCP connection latency
tcptracer               # Trace TCP connections (more detail)

# TCP retransmits
tcpretrans              # Trace TCP retransmits

# TCP throughput
tcptop                  # Top TCP connections by throughput

# TCP state changes
tcpstates               # Trace TCP connection state changes

# TCP window
tcpwin                  # Trace TCP send congestion window

# TCP lifetime
tcplife                 # Trace TCP connection duration and stats
```

**tcpconnlat example**:
```bash
# Trace connection latency
tcpconnlat

# Output:
PID    COMM         IP SADDR           DADDR           DPORT LAT(ms)
1234   curl         4  192.168.1.100   93.184.216.34   443   0.50
```

**tcpretrans example**:
```bash
# Trace retransmits
tcpretrans

# Output:
TIME     PID    IP LADDR:LPORT          T> RADDR:RPORT          STATE
01:23:45 1234   4  192.168.1.100:45678  R> 93.184.216.34:443    ESTABLISHED
```

**tcplife example**:
```bash
# Trace connection lifetime
tcplife

# Output:
PID   COMM       LADDR           LPORT RADDR           RPORT TX_KB RX_KB MS
1234  curl       192.168.1.100   45678 93.184.216.34   443   1     10    523
```

### Performance Monitoring

**collectd/telegraf**:
```toml
# telegraf.conf

[[inputs.netstat]]
  # Collect TCP stats

[[inputs.kernel]]
  # Collect kernel stats

[[inputs.net]]
  interfaces = ["eth0"]
  # Collect interface stats

[[outputs.influxdb]]
  urls = ["http://localhost:8086"]
  database = "telegraf"
```

**Prometheus node_exporter**:
```bash
# Install
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvfz node_exporter-*.tar.gz
cd node_exporter-*/
./node_exporter &

# Metrics available at http://localhost:9100/metrics
curl http://localhost:9100/metrics | grep node_netstat_Tcp
```

**Grafana dashboard**:
```promql
# Retransmission rate
rate(node_netstat_Tcp_RetransSegs[5m]) / rate(node_netstat_Tcp_OutSegs[5m]) * 100

# Established connections
node_netstat_Tcp_CurrEstab

# Connection rate
rate(node_netstat_Tcp_ActiveOpens[5m]) + rate(node_netstat_Tcp_PassiveOpens[5m])

# Throughput (bytes/sec)
rate(node_network_receive_bytes_total{device="eth0"}[5m])
rate(node_network_transmit_bytes_total{device="eth0"}[5m])
```

---

## Common Issues and Troubleshooting

### Issue: High Retransmission Rate

**Symptoms**:
```bash
nstat TcpRetransSegs          # Increasing counter
ss -tin | grep retrans        # Non-zero retrans on connections
```

**Diagnosis**:
```bash
# 1. Check packet loss
mtr --report <destination>    # Path MTU and loss

# 2. Check network errors
ethtool -S eth0 | grep -E "error|drop"

# 3. Check buffer sizes
ss -tim | grep -E "rcv_space|skmem"

# 4. Check congestion algorithm
sysctl net.ipv4.tcp_congestion_control
```

**Solutions**:
```bash
# Increase buffers
sysctl -w net.ipv4.tcp_rmem="4096 131072 67108864"
sysctl -w net.ipv4.tcp_wmem="4096 131072 67108864"

# Try BBR (handles loss better)
modprobe tcp_bbr
sysctl -w net.ipv4.tcp_congestion_control=bbr
sysctl -w net.core.default_qdisc=fq

# Enable SACK
sysctl -w net.ipv4.tcp_sack=1

# Check physical issues (cables, NICs)
ethtool eth0          # Link status
dmesg | grep eth0     # Kernel messages
```

### Issue: Low Throughput

**Symptoms**:
```bash
iperf3 -c <server>            # Low throughput
ss -tin | grep cwnd           # Small cwnd
```

**Diagnosis**:
```bash
# 1. Calculate expected throughput
# BDP = Bandwidth × RTT
# Max throughput ≈ Window / RTT

# 2. Check cwnd
ss -tin dst <ip> | grep cwnd

# 3. Check window scaling
tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-syn != 0' -c 10 -v | grep wscale

# 4. Check receive window
ss -tin | grep rcv_space

# 5. Check application
# Is application reading data fast enough?
ss -tim | grep "skmem"        # Check socket buffer usage
```

**Solutions**:
```bash
# Enable window scaling
sysctl -w net.ipv4.tcp_window_scaling=1

# Increase buffers to match BDP
# Example: 10 Gbps, 100ms RTT → 125 MB BDP
sysctl -w net.ipv4.tcp_rmem="4096 131072 134217728"
sysctl -w net.ipv4.tcp_wmem="4096 131072 134217728"
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.wmem_max=134217728

# Use BBR
modprobe tcp_bbr
sysctl -w net.ipv4.tcp_congestion_control=bbr
sysctl -w net.core.default_qdisc=fq

# Don't reset cwnd after idle
sysctl -w net.ipv4.tcp_slow_start_after_idle=0

# Enable TCP offloading
ethtool -K eth0 tso on gso on gro on

# Increase initial cwnd
ip route change default via <gateway> dev eth0 initcwnd 10
```

### Issue: Connection Timeouts

**Symptoms**:
```bash
ss -tan | grep TIME_WAIT | wc -l    # Many TIME_WAIT sockets
# Connection refused errors
# Port exhaustion
```

**Diagnosis**:
```bash
# 1. Check TIME_WAIT sockets
ss -tan state time-wait | wc -l

# 2. Check available ports
sysctl net.ipv4.ip_local_port_range
ss -tan | awk '{print $4}' | cut -d: -f2 | sort -n | uniq | wc -l

# 3. Check connection rate
nstat TcpActiveOpens

# 4. Check if hitting limits
ulimit -n                # File descriptor limit
sysctl net.core.somaxconn    # Listen backlog
```

**Solutions**:
```bash
# Reuse TIME_WAIT sockets
sysctl -w net.ipv4.tcp_tw_reuse=1

# Reduce FIN timeout
sysctl -w net.ipv4.tcp_fin_timeout=30

# Increase TIME_WAIT bucket limit
sysctl -w net.ipv4.tcp_max_tw_buckets=2000000

# Expand port range
sysctl -w net.ipv4.ip_local_port_range="10000 65535"

# Increase file descriptors
ulimit -n 100000
# Or edit /etc/security/limits.conf:
*  soft  nofile  100000
*  hard  nofile  100000

# Increase listen backlog
sysctl -w net.core.somaxconn=4096
sysctl -w net.ipv4.tcp_max_syn_backlog=8192
```

### Issue: High Latency

**Symptoms**:
```bash
ping <destination>            # High RTT
ss -tin | grep rtt            # High RTT values
```

**Diagnosis**:
```bash
# 1. Measure RTT
ping <destination>
mtr --report <destination>

# 2. Check bufferbloat
# Large buffers + no traffic shaping = bufferbloat
ss -tin | grep -E "cwnd|rtt"

# 3. Check queuing
tc -s qdisc show dev eth0

# 4. Check system load
top
vmstat 1
```

**Solutions**:
```bash
# Use FQ/CoDel qdisc (fights bufferbloat)
tc qdisc replace dev eth0 root fq_codel

# Or use FQ for BBR
tc qdisc replace dev eth0 root fq

# Reduce buffer sizes (if bufferbloat suspected)
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"

# Use BBR (optimizes for latency)
sysctl -w net.ipv4.tcp_congestion_control=bbr

# Enable ECN (congestion signaling without drops)
sysctl -w net.ipv4.tcp_ecn=1

# Check application performance
# Slow application processing can cause latency
```

### Issue: Connection Drops

**Symptoms**:
```bash
# Connections reset
# Application errors "Connection reset by peer"
nstat TcpEstabResets          # Increasing counter
```

**Diagnosis**:
```bash
# 1. Check for RST packets
tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-rst != 0'

# 2. Check firewall/NAT timeout
# Firewalls may drop idle connections

# 3. Check keep-alive settings
sysctl net.ipv4.tcp_keepalive_time
sysctl net.ipv4.tcp_keepalive_intvl
sysctl net.ipv4.tcp_keepalive_probes

# 4. Check for middlebox interference
mtr <destination>             # Check path
```

**Solutions**:
```bash
# Enable/shorten keep-alive
sysctl -w net.ipv4.tcp_keepalive_time=300       # 5 min
sysctl -w net.ipv4.tcp_keepalive_intvl=30       # 30 sec
sysctl -w net.ipv4.tcp_keepalive_probes=3

# Enable at application level
# Python
sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 300)

# Check firewall rules
iptables -L -v -n             # Linux firewall
# Adjust timeout if needed

# Enable TCP Fast Open (reduces handshake time)
sysctl -w net.ipv4.tcp_fastopen=3
```

### Issue: Zero Window

**Symptoms**:
```bash
# Wireshark shows "TCP Zero Window"
# Throughput drops to zero intermittently
ss -tin | grep "rcv_space"
```

**Diagnosis**:
```bash
# 1. Check receive buffer
ss -tim | grep -E "rcv_space|skmem"

# 2. Check if receiver is slow
# Application not reading data fast enough

# 3. Monitor buffer usage over time
watch -n 1 'ss -tim dst <ip> | grep -E "skmem|rcv"'
```

**Solutions**:
```bash
# Increase receive buffer
sysctl -w net.ipv4.tcp_rmem="4096 131072 67108864"
sysctl -w net.core.rmem_max=67108864

# Enable auto-tuning
sysctl -w net.ipv4.tcp_moderate_rcvbuf=1

# Check application
# Ensure application reads data promptly
# Profile application performance
```

---

## Anti-Patterns

**1. Disabling tcp_timestamps**:
```bash
# DON'T DO THIS
sysctl -w net.ipv4.tcp_timestamps=0

# Why: Breaks PAWS (Protect Against Wrapped Sequences)
# Breaks accurate RTT measurement
# Required for high-performance networks
```

**2. Using tcp_tw_recycle**:
```bash
# DON'T DO THIS (removed in Linux 4.12)
sysctl -w net.ipv4.tcp_tw_recycle=1

# Why: Breaks NAT (multiple clients behind same IP)
# Causes connection failures
# Use tcp_tw_reuse instead
```

**3. Excessive buffers**:
```bash
# DON'T DO THIS
sysctl -w net.ipv4.tcp_rmem="4096 1073741824 10737418240"  # 10 GB!

# Why: Causes bufferbloat (high latency)
# Wastes memory
# No benefit beyond 2×BDP
```

**4. Disabling window scaling**:
```bash
# DON'T DO THIS
sysctl -w net.ipv4.tcp_window_scaling=0

# Why: Limits throughput to 64KB/RTT
# Example: 64KB / 100ms = 5.2 Mbps (terrible!)
```

**5. Random tuning without measurement**:
```bash
# DON'T DO THIS
# Copy settings from random blog posts
# Apply tuning without testing
# No before/after comparison

# DO THIS
# Measure baseline
# Apply targeted tuning
# Measure improvement
# Document changes
```

**6. Same tuning everywhere**:
```bash
# DON'T DO THIS
# Use same settings for all scenarios
# Data center, WAN, mobile, etc.

# DO THIS
# Tune for actual network characteristics
# Measure BDP
# Adjust for latency, bandwidth, loss
```

**7. Ignoring application layer**:
```bash
# DON'T EXPECT MAGIC
# TCP tuning won't fix application bugs
# Won't fix database query performance
# Won't fix inefficient algorithms

# DO THIS
# Profile application first
# Fix application bottlenecks
# Then optimize TCP
```

**8. Disabling SACK**:
```bash
# DON'T DO THIS
sysctl -w net.ipv4.tcp_sack=0

# Why: Essential for high-speed networks
# Needed for efficient loss recovery
# No good reason to disable
```

**9. Testing before committing changes**:
```bash
# DON'T DO THIS
# Test code before git commit
# Changes during test invalidate results

# DO THIS
# Git commit first
# Then test committed code
# Fix issues → commit again → re-test
```

**10. Front-loading all skills**:
```bash
# DON'T DO THIS
# Load all TCP skills at session start
# Waste context budget

# DO THIS
# Let Optimizer discover needed skills
# Load on-demand based on task
# Unload low-priority skills when constrained
```

---

## Summary

TCP optimization requires:
1. **Understanding fundamentals**: Flow control, congestion control, BDP
2. **Measuring baseline**: Before tuning, know current performance
3. **Targeted tuning**: Optimize for actual network characteristics
4. **Testing thoroughly**: Verify improvements with benchmarks
5. **Monitoring continuously**: Track metrics in production
6. **Avoiding anti-patterns**: Don't blindly copy settings
7. **Considering application**: TCP tuning complements app optimization

**Key takeaways**:
- **BBR** for high BDP networks
- **Large buffers** (≥2×BDP) for high throughput
- **Window scaling** mandatory for modern networks
- **SACK** essential for reliable high-speed transfer
- **Measure, tune, measure** - always verify improvements
- **Tune for scenario** - WAN, data center, mobile differ

**Resources**:
- `optimize_tcp.sh`: Automated tuning
- `analyze_tcp_performance.py`: Performance analysis
- `test_tcp_throughput.sh`: Benchmarking
- Production examples for various scenarios
