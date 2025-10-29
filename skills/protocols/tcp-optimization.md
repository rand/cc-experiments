---
name: protocols-tcp-optimization
description: TCP performance optimization and tuning
---

# TCP Optimization

**Scope**: TCP tuning, congestion control, kernel parameters, performance monitoring, throughput optimization
**Lines**: ~370
**Last Updated**: 2025-10-29

## When to Use This Skill

Activate this skill when:
- Optimizing network throughput and latency
- Tuning TCP for high-bandwidth or high-latency networks
- Diagnosing TCP performance issues
- Configuring congestion control algorithms
- Optimizing cloud networking (AWS, GCP, Azure)
- Tuning container networking (Docker, Kubernetes)
- Configuring load balancers for TCP performance
- Optimizing TCP for mobile/wireless networks
- Implementing high-performance data transfer
- Troubleshooting retransmissions and packet loss

## Core Concepts

### TCP Fundamentals

**TCP** (Transmission Control Protocol): Reliable, ordered, connection-oriented transport protocol.

**Key mechanisms**:
- **3-way handshake**: SYN → SYN-ACK → ACK connection establishment
- **Flow control**: Sliding window to prevent receiver overflow
- **Congestion control**: Prevents network congestion via AIMD (Additive Increase Multiplicative Decrease)
- **Retransmission**: Automatic retransmit of lost packets based on timeouts or duplicate ACKs
- **Selective ACK (SACK)**: Acknowledges non-contiguous data blocks

**Performance factors**:
```
Throughput = Window Size / RTT
```

**Key metrics**:
- **RTT** (Round Trip Time): Time for packet round-trip
- **Bandwidth-Delay Product (BDP)**: Optimal window size = Bandwidth × RTT
- **Congestion Window (cwnd)**: Maximum unacknowledged data
- **Receive Window (rwnd)**: Receiver's buffer capacity
- **Retransmission rate**: Percentage of packets retransmitted

---

## When to Optimize TCP

### Optimization Scenarios

**High-bandwidth networks** (10Gbps+):
- Default buffers too small for BDP
- Need large TCP windows (scaling enabled)
- Consider BBR congestion control
- Enable TCP offloading (TSO, GRO)

**High-latency networks** (100ms+ RTT):
- Increase initial congestion window
- Tune retransmission timeouts
- Enable SACK and timestamps
- Consider BBR for better throughput

**Data center networks** (low latency, high bandwidth):
- Use DCTCP or BBR
- Aggressive timeout settings
- Large buffers
- Enable TCP offloading

**Mobile/wireless networks**:
- Conservative timeout settings
- Enable SACK for out-of-order delivery
- Optimize keep-alive intervals
- Consider TCP Fast Open

**Cloud environments** (AWS, GCP, Azure):
- Platform-specific tuning (Enhanced Networking, Accelerated Networking)
- Placement groups for low latency
- Jumbo frames where supported
- Monitor network performance metrics

---

## Congestion Control Algorithms

### Algorithm Selection

**Reno** (classic):
- Default on older systems
- AIMD: slow start, congestion avoidance, fast retransmit, fast recovery
- Poor performance on high BDP networks
- Use: Legacy compatibility only

**Cubic** (default on Linux):
- Default since Linux 2.6.19
- Better than Reno on high BDP networks
- Cubic growth function for window scaling
- Use: General purpose, good default

**BBR** (Bottleneck Bandwidth and RTT):
- Developed by Google (2016)
- Model-based congestion control
- Optimizes for throughput and latency
- Excellent for high BDP networks
- Use: High-performance scenarios, modern networks

**BBRv2** (2020+):
- Improved fairness vs BBRv1
- Better loss tolerance
- Production-ready on Linux 5.18+
- Use: Latest high-performance deployments

**Changing algorithm**:
```bash
# Check available algorithms
sysctl net.ipv4.tcp_available_congestion_control

# Set to BBR (requires kernel module)
sudo modprobe tcp_bbr
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr
sudo sysctl -w net.core.default_qdisc=fq  # Fair Queueing for BBR

# Make persistent
echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.conf
echo "net.core.default_qdisc=fq" | sudo tee -a /etc/sysctl.conf
```

---

## Critical TCP Parameters

### Kernel Parameters (Linux sysctl)

**TCP buffer sizes**:
```bash
# Default: min, default, max (bytes)
net.ipv4.tcp_rmem = 4096 87380 6291456   # Receive buffer
net.ipv4.tcp_wmem = 4096 16384 4194304   # Send buffer

# High-bandwidth tuning (10Gbps+)
net.ipv4.tcp_rmem = 4096 131072 134217728   # 128MB max
net.ipv4.tcp_wmem = 4096 131072 134217728
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
```

**TCP window scaling**:
```bash
net.ipv4.tcp_window_scaling = 1  # Enable (required for >64KB windows)
```

**Initial congestion window**:
```bash
net.ipv4.tcp_slow_start_after_idle = 0  # Don't reset cwnd after idle
ip route change default via <gateway> dev eth0 initcwnd 10  # Set initial cwnd
```

**Selective ACK**:
```bash
net.ipv4.tcp_sack = 1        # Enable SACK (handle out-of-order packets)
net.ipv4.tcp_dsack = 1       # Duplicate SACK
```

**Fast retransmit**:
```bash
net.ipv4.tcp_fastopen = 3    # Enable TCP Fast Open (client and server)
```

**Timestamps**:
```bash
net.ipv4.tcp_timestamps = 1  # Enable (required for high-performance)
```

**Keep-alive**:
```bash
net.ipv4.tcp_keepalive_time = 600      # Start after 10 min idle
net.ipv4.tcp_keepalive_intvl = 60      # Probe every 60 sec
net.ipv4.tcp_keepalive_probes = 3      # 3 failed probes = dead
```

**Reuse and recycle**:
```bash
net.ipv4.tcp_tw_reuse = 1              # Reuse TIME_WAIT sockets
net.ipv4.tcp_fin_timeout = 30          # FIN timeout (default 60)
```

**SYN flood protection**:
```bash
net.ipv4.tcp_syncookies = 1            # Enable SYN cookies
net.ipv4.tcp_max_syn_backlog = 8192    # SYN queue size
```

---

## TCP Offloading

### Hardware Offload Features

**TSO** (TCP Segmentation Offload):
- CPU sends large packets to NIC
- NIC segments into MSS-sized packets
- Reduces CPU overhead

**GSO** (Generic Segmentation Offload):
- Software TSO fallback
- Delays segmentation until last moment

**GRO** (Generic Receive Offload):
- Aggregates received packets
- Reduces interrupts and CPU overhead

**LRO** (Large Receive Offload):
- Hardware packet aggregation
- Can break forwarding (disable on routers)

**Checking offload status**:
```bash
ethtool -k eth0 | grep offload

# Enable offloads
sudo ethtool -K eth0 tso on
sudo ethtool -K eth0 gso on
sudo ethtool -K eth0 gro on
```

**When to disable**:
- Packet capture (tcpdump): TSO/GRO show large packets
- Routing/forwarding: LRO can break it
- Debugging: See actual packets

---

## Monitoring and Diagnosis

### Key Commands

**Current connections**:
```bash
# Modern replacement for netstat
ss -tan                          # All TCP connections
ss -tan state established        # Established only
ss -tni                          # With TCP info (cwnd, rtt)
ss -ti dst <ip>                  # Specific destination

# Connection details
ss -tin | grep -A5 "<ip>"        # cwnd, rtt, retrans
```

**TCP statistics**:
```bash
# System-wide TCP stats
nstat -az | grep Tcp             # All TCP counters
ss -s                            # Summary stats

# Key metrics
nstat TcpRetransSegs             # Retransmissions
nstat TcpExtTCPLoss              # Packet loss
```

**Socket buffer usage**:
```bash
# See send/receive buffers
ss -tm                           # Memory info per socket

# System-wide buffer usage
cat /proc/net/sockstat
```

**Packet capture**:
```bash
# Capture TCP flags
tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn|tcp-fin) != 0'

# Capture retransmissions (same seq number)
tcpdump -i eth0 -nn 'tcp'
```

**Performance testing**:
```bash
# iperf3 throughput test
iperf3 -c <server> -t 60 -P 4    # 4 parallel streams, 60 sec

# With specific congestion control
iperf3 -c <server> -C bbr
```

---

## Quick Tuning Reference

### High-Bandwidth Networks (10Gbps+)

```bash
# Large buffers for high BDP
sysctl -w net.ipv4.tcp_rmem="4096 131072 134217728"
sysctl -w net.ipv4.tcp_wmem="4096 131072 134217728"
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.wmem_max=134217728

# BBR congestion control
modprobe tcp_bbr
sysctl -w net.ipv4.tcp_congestion_control=bbr
sysctl -w net.core.default_qdisc=fq

# TCP offloading
ethtool -K eth0 tso on gso on gro on

# Window scaling and SACK
sysctl -w net.ipv4.tcp_window_scaling=1
sysctl -w net.ipv4.tcp_sack=1
```

### High-Latency Networks (100ms+ RTT)

```bash
# Large buffers for BDP
sysctl -w net.ipv4.tcp_rmem="4096 262144 67108864"
sysctl -w net.ipv4.tcp_wmem="4096 262144 67108864"

# BBR for latency optimization
sysctl -w net.ipv4.tcp_congestion_control=bbr

# SACK and timestamps
sysctl -w net.ipv4.tcp_sack=1
sysctl -w net.ipv4.tcp_timestamps=1

# Don't reset after idle
sysctl -w net.ipv4.tcp_slow_start_after_idle=0
```

### Data Center Networks

```bash
# Moderate buffers (low latency)
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"

# BBR or Cubic
sysctl -w net.ipv4.tcp_congestion_control=bbr

# Fast recovery
sysctl -w net.ipv4.tcp_fastopen=3

# Aggressive timeouts
sysctl -w net.ipv4.tcp_fin_timeout=10
```

---

## Common Issues and Troubleshooting

### High Retransmission Rate

**Symptoms**:
```bash
nstat TcpRetransSegs             # Growing counter
ss -tin | grep retrans           # Non-zero retrans per connection
```

**Causes**:
- Network congestion or packet loss
- Buffers too small
- Poor congestion control algorithm

**Solutions**:
```bash
# Check for packet loss
mtr <destination>

# Increase buffers
sysctl -w net.ipv4.tcp_rmem="4096 131072 67108864"

# Try BBR
sysctl -w net.ipv4.tcp_congestion_control=bbr
```

### Low Throughput

**Symptoms**:
```bash
iperf3 -c <server>               # Low throughput vs capacity
ss -tin | grep cwnd              # Small cwnd
```

**Causes**:
- Small congestion window
- Buffers too small for BDP
- Poor congestion control

**Solutions**:
```bash
# Calculate BDP: Bandwidth (bits/s) * RTT (s) / 8
# Example: 10Gbps * 0.1s / 8 = 125MB buffer needed

# Increase buffers to match BDP
sysctl -w net.ipv4.tcp_rmem="4096 131072 134217728"

# Enable window scaling
sysctl -w net.ipv4.tcp_window_scaling=1

# Use BBR
sysctl -w net.ipv4.tcp_congestion_control=bbr
```

### Connection Timeouts

**Symptoms**:
```bash
# Many connections in TIME_WAIT
ss -tan | grep TIME_WAIT | wc -l

# Port exhaustion
ss -s                            # Check TCP stats
```

**Solutions**:
```bash
# Reuse TIME_WAIT sockets
sysctl -w net.ipv4.tcp_tw_reuse=1

# Reduce FIN timeout
sysctl -w net.ipv4.tcp_fin_timeout=30

# Increase port range
sysctl -w net.ipv4.ip_local_port_range="10000 65535"
```

---

## Anti-Patterns

**Avoid**:
- **Disabling tcp_timestamps**: Breaks high-performance features
- **tcp_tw_recycle=1**: Breaks NAT (removed in Linux 4.12)
- **Excessive buffers**: Causes bufferbloat (latency spikes)
- **Disabling window scaling**: Limits throughput to 64KB/RTT
- **Random tuning**: Benchmark and measure impact
- **Ignoring application layer**: TCP tuning won't fix application bugs
- **Disabling SACK**: Needed for reliable high-speed transfer
- **Same tuning everywhere**: Optimize for actual network characteristics

**Best practices**:
- Measure before and after tuning
- Use iperf3 or similar for benchmarking
- Monitor production metrics
- Document changes
- Test under real-world conditions
- Consider application-level optimization
- Use BBR for modern high-performance networks
- Enable TCP offloading on high-speed NICs

---

## Resources

For comprehensive TCP tuning guidance, see:
- `resources/REFERENCE.md`: Deep dive into TCP internals, algorithms, and tuning
- `resources/scripts/optimize_tcp.sh`: Automated TCP tuning for various scenarios
- `resources/scripts/analyze_tcp_performance.py`: TCP metrics analysis and recommendations
- `resources/scripts/test_tcp_throughput.sh`: iperf3-based throughput testing
- `resources/examples/`: Production configurations for Linux, Kubernetes, AWS, etc.
