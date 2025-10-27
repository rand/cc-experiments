---
name: protocols-protocol-debugging
description: Debug network protocols using Wireshark, tcpdump, curl, and other tools for HTTP, TCP, UDP, and QUIC
---

# Protocol Debugging

**Scope**: Tools and techniques for debugging network protocols (HTTP, TCP, UDP, QUIC)
**Lines**: ~320
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Debugging connection failures
- Analyzing network performance issues
- Troubleshooting HTTP errors
- Understanding packet loss or retransmissions
- Verifying TLS/SSL handshakes
- Debugging API communication
- Investigating slow requests
- Capturing and analyzing network traffic

## Core Tools

### tcpdump

**Basic Capture**:
```bash
# Capture all traffic on interface
sudo tcpdump -i eth0

# Capture HTTP traffic (port 80)
sudo tcpdump -i eth0 'tcp port 80'

# Capture to file
sudo tcpdump -i eth0 -w capture.pcap

# Read from file
tcpdump -r capture.pcap
```

**Advanced Filters**:
```bash
# Specific host
sudo tcpdump host example.com

# Source or destination
sudo tcpdump src 192.168.1.100
sudo tcpdump dst 192.168.1.100

# TCP SYN packets only
sudo tcpdump 'tcp[tcpflags] & (tcp-syn) != 0'

# HTTP GET requests
sudo tcpdump -s 0 -A 'tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)'

# UDP DNS queries
sudo tcpdump -i eth0 udp port 53
```

### Wireshark

**Capture Filters** (applied before capture):
```
# HTTP traffic
tcp port 80 or tcp port 443

# Specific host
host 192.168.1.100

# Not local traffic
not broadcast and not multicast
```

**Display Filters** (after capture):
```
# HTTP GET requests
http.request.method == "GET"

# HTTP errors
http.response.code >= 400

# TCP retransmissions
tcp.analysis.retransmission

# Slow responses (>1s)
http.time > 1

# TLS handshake
ssl.handshake.type == 1

# QUIC traffic
quic
```

**Follow TCP Stream**:
```
1. Right-click packet
2. Follow → TCP Stream
3. See full conversation
```

### curl

**Verbose HTTP Debugging**:
```bash
# Verbose output
curl -v https://api.example.com

# Include response headers
curl -i https://api.example.com

# Timing breakdown
curl -w "@curl-format.txt" -o /dev/null -s https://api.example.com

# curl-format.txt:
#   time_namelookup:  %{time_namelookup}s\n
#   time_connect:  %{time_connect}s\n
#   time_appconnect:  %{time_appconnect}s\n
#   time_pretransfer:  %{time_pretransfer}s\n
#   time_starttransfer:  %{time_starttransfer}s\n
#   time_total:  %{time_total}s\n
```

**HTTP/2 and HTTP/3**:
```bash
# Force HTTP/2
curl --http2 https://example.com

# Try HTTP/3
curl --http3 https://cloudflare-quic.com

# Show protocol used
curl -I --http2 -s -o /dev/null -w '%{http_version}\n' https://example.com
```

---

## Debugging Patterns

### Pattern 1: Connection Establishment Issues

**Symptoms**: Cannot connect to server

**Debug Steps**:
```bash
# 1. Check DNS resolution
nslookup example.com
dig example.com

# 2. Test basic connectivity
ping example.com

# 3. Check port is open
nc -zv example.com 80
telnet example.com 80

# 4. Capture handshake
sudo tcpdump -i eth0 'host example.com' -w handshake.pcap

# 5. Analyze in Wireshark
# Look for: SYN, SYN-ACK, ACK packets
```

**Common Issues**:
- No SYN-ACK → Server not listening or firewall blocking
- SYN-ACK without final ACK → Client firewall issue
- RST packet → Connection refused

### Pattern 2: Slow HTTP Requests

**Diagnosis**:
```bash
# Measure timing
curl -w "@curl-format.txt" -o /dev/null -s https://api.example.com

# Example output:
#   time_namelookup:  0.005s   ← DNS lookup
#   time_connect:  0.045s      ← TCP handshake
#   time_appconnect:  0.180s   ← TLS handshake
#   time_pretransfer:  0.180s  ← Ready to transfer
#   time_starttransfer:  1.234s ← First byte (TTFB)
#   time_total:  2.456s        ← Complete
```

**Identify Bottleneck**:
```
If time_namelookup is high → DNS issue
If time_connect is high → Network latency
If time_appconnect is high → TLS handshake slow
If time_starttransfer is high → Server processing slow
If time_total is high → Large response or slow transfer
```

**Wireshark Analysis**:
```
1. Filter: http.host == "api.example.com"
2. Right-click request → Follow HTTP Stream
3. Check "Time since previous frame"
4. Look for gaps
```

### Pattern 3: TCP Retransmissions

**Capture Retransmissions**:
```bash
# tcpdump with verbose
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-push) != 0' -vv

# Wireshark filter
tcp.analysis.retransmission
```

**Analyze**:
```
High retransmissions indicate:
- Packet loss (network congestion)
- High latency (timeout too aggressive)
- Receiver buffer full (window size issues)
```

**Solutions**:
```bash
# Increase TCP buffer sizes
sudo sysctl -w net.core.rmem_max=26214400
sudo sysctl -w net.core.wmem_max=26214400

# Use better congestion control
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr
```

### Pattern 4: HTTP Error Debugging

**Capture HTTP Errors**:
```bash
# tcpdump HTTP traffic
sudo tcpdump -i eth0 -A -s 0 'tcp port 80'

# Filter in Wireshark
http.response.code >= 400
```

**Common HTTP Errors**:
```
400 Bad Request:
- Malformed JSON
- Missing required headers
- Invalid URL encoding

401 Unauthorized:
- Missing Authorization header
- Invalid token
- Expired token

403 Forbidden:
- Valid auth but no permission
- IP whitelist issue

404 Not Found:
- Wrong URL
- Resource deleted
- Routing issue

500 Internal Server Error:
- Server crash
- Unhandled exception
- Database connection failure

502 Bad Gateway:
- Upstream server down
- Proxy misconfiguration

503 Service Unavailable:
- Server overloaded
- Maintenance mode
- Rate limiting

504 Gateway Timeout:
- Upstream server slow
- Timeout too aggressive
```

---

## Advanced Debugging

### TLS/SSL Handshake

**Capture Handshake**:
```bash
# With openssl
openssl s_client -connect example.com:443 -debug

# Key exchange details
openssl s_client -connect example.com:443 -showcerts

# Check protocol and cipher
openssl s_client -connect example.com:443 -tls1_2
openssl s_client -connect example.com:443 -tls1_3
```

**Wireshark TLS**:
```
Filters:
ssl.handshake.type == 1   # ClientHello
ssl.handshake.type == 2   # ServerHello
ssl.handshake.type == 11  # Certificate
ssl.handshake.type == 16  # ClientKeyExchange
```

### HTTP/2 Debugging

**Chrome DevTools**:
```
1. Open DevTools → Network
2. Right-click header row → Protocol
3. See "h2" for HTTP/2 requests
4. Timing tab shows multiplexing
```

**Wireshark HTTP/2**:
```
Filter: http2
- See HEADERS frames
- See DATA frames
- See WINDOW_UPDATE
- See GOAWAY
```

### QUIC/HTTP/3 Debugging

**Check QUIC Support**:
```bash
# Test with curl
curl --http3 https://cloudflare-quic.com -I

# Check Alt-Svc header
curl -I https://example.com | grep Alt-Svc
```

**Wireshark QUIC**:
```
Filter: quic
- Initial packet (handshake)
- 0-RTT data
- 1-RTT data
- Connection migration
```

**Chrome QUIC Logs**:
```
chrome://net-export/
- Start logging
- Navigate to site
- Stop and save log
- Analyze with netlog-viewer
```

---

## Troubleshooting Checklist

### Connection Issues

```
□ DNS resolves correctly (nslookup)
□ Host is reachable (ping)
□ Port is open (nc -zv)
□ No firewall blocking (iptables -L)
□ TLS handshake succeeds (openssl s_client)
□ Certificates are valid (openssl s_client -showcerts)
```

### Performance Issues

```
□ DNS lookup fast (<100ms)
□ TCP handshake fast (<100ms for local, <500ms for distant)
□ TLS handshake efficient (HTTP/2, TLS 1.3)
□ No excessive retransmissions (< 1%)
□ Using keep-alive connections
□ Compression enabled (gzip, brotli)
```

### HTTP Issues

```
□ Correct HTTP method
□ Valid headers (Content-Type, Authorization)
□ Proper status codes returned
□ CORS configured if needed
□ Request/response sizes reasonable
□ No rate limiting applied
```

---

## Tools Comparison

| Tool | Best For | Pros | Cons |
|------|----------|------|------|
| tcpdump | Quick captures, servers | Fast, scriptable | No GUI |
| Wireshark | Detailed analysis | Rich UI, filters | Resource-heavy |
| curl | HTTP debugging | Simple, scriptable | HTTP only |
| nc (netcat) | Port testing | Versatile | Basic |
| nmap | Port scanning | Comprehensive | Slow |
| mtr | Route tracing | Real-time | Limited protocol support |

---

## Related Skills

- `protocols-tcp-fundamentals` - TCP protocol details
- `protocols-udp-fundamentals` - UDP protocol details
- `protocols-http-fundamentals` - HTTP basics
- `networking-network-protocols` - DNS, DHCP debugging
- `cryptography-tls-configuration` - TLS troubleshooting
- `observability-distributed-tracing` - Application-level tracing

---

**Last Updated**: 2025-10-27
