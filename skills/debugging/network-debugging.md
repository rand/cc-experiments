---
name: debugging-network-debugging
description: Network debugging with tcpdump, Wireshark, curl, DNS tools, SSL/TLS inspection, and network tracing utilities
---

# Network Debugging

**Scope**: tcpdump, Wireshark, curl debugging, HTTP headers, SSL/TLS, DNS (dig, nslookup), strace, lsof, mtr, ping, traceroute

**Lines**: 420

**Last Updated**: 2025-10-26

---

## When to Use This Skill

Use this skill when:
- Debugging API connectivity issues
- Analyzing HTTP request/response problems
- Investigating SSL/TLS certificate errors
- Troubleshooting DNS resolution failures
- Diagnosing network latency or packet loss
- Inspecting network traffic between services
- Debugging websocket connections
- Analyzing load balancer or proxy behavior

**Don't use** for:
- Application logic debugging (use debuggers)
- Simple HTTP client errors (check status codes first)
- Known firewall blocks (check security groups first)

---

## Core Concepts

### Network Debugging Layers

```
Layer 7: Application (HTTP, gRPC, WebSocket)
├─ curl, httpie, wget
├─ Browser DevTools
└─ API clients (Postman, Insomnia)

Layer 4-6: Transport/Session (TCP, TLS)
├─ openssl s_client
├─ nmap
└─ netcat (nc)

Layer 3: Network (IP, routing)
├─ ping, traceroute, mtr
├─ ip route
└─ tcpdump, Wireshark

Layer 2: Data Link (DNS, ARP)
├─ dig, nslookup, host
├─ arp -a
└─ Network packet inspection
```

### Common Network Issues

| Symptom | Likely Cause | Debug Tool |
|---------|--------------|------------|
| Connection refused | Service not listening, firewall | `netcat`, `telnet` |
| Timeout | Network unreachable, slow route | `ping`, `mtr`, `traceroute` |
| DNS error | Misconfigured DNS, missing record | `dig`, `nslookup` |
| SSL error | Certificate invalid, expired | `openssl s_client` |
| Slow requests | High latency, packet loss | `tcpdump`, `Wireshark` |
| 404/503 errors | Wrong endpoint, service down | `curl -v` |

---

## Patterns

### Pattern 1: curl Debugging Flags

```bash
# 1. Basic verbose output
curl -v https://api.example.com/users
# Shows:
# - Request headers
# - Response headers
# - SSL handshake
# - HTTP version

# 2. Show only headers (no body)
curl -I https://api.example.com/users
# HEAD request, shows response headers

# 3. Include response headers in output
curl -i https://api.example.com/users

# 4. Trace ASCII (detailed protocol trace)
curl --trace-ascii /tmp/trace.txt https://api.example.com/users
cat /tmp/trace.txt
# Shows hex dump of request/response

# 5. Trace binary (full packet capture)
curl --trace /tmp/trace.bin https://api.example.com/users

# 6. Follow redirects
curl -L https://example.com  # Follows 301/302 redirects

# 7. Show timing information
curl -w "@curl-format.txt" -o /dev/null -s https://api.example.com/users

# curl-format.txt:
#     time_namelookup:  %{time_namelookup}s\n
#        time_connect:  %{time_connect}s\n
#     time_appconnect:  %{time_appconnect}s\n
#    time_pretransfer:  %{time_pretransfer}s\n
#       time_redirect:  %{time_redirect}s\n
#  time_starttransfer:  %{time_starttransfer}s\n
#                     ----------\n
#          time_total:  %{time_total}s\n

# 8. Test with custom headers
curl -H "Authorization: Bearer token123" \
     -H "Content-Type: application/json" \
     https://api.example.com/users

# 9. Test POST request
curl -X POST https://api.example.com/users \
     -H "Content-Type: application/json" \
     -d '{"name":"Alice","email":"alice@example.com"}' \
     -v

# 10. Test with specific TLS version
curl --tlsv1.2 https://api.example.com/users
curl --tls-max 1.2 https://api.example.com/users

# 11. Ignore SSL certificate errors (testing only!)
curl -k https://self-signed.example.com

# 12. Use specific DNS server
curl --dns-servers 8.8.8.8 https://api.example.com/users

# 13. Resolve hostname to specific IP
curl --resolve api.example.com:443:192.0.2.1 https://api.example.com/users

# 14. Show only HTTP status code
curl -o /dev/null -s -w "%{http_code}\n" https://api.example.com/users

# 15. Test connection reuse
curl -v https://api.example.com/users https://api.example.com/posts
# Look for "Re-using existing connection"
```

### Pattern 2: tcpdump Packet Capture

```bash
# 1. Capture all traffic on interface
sudo tcpdump -i eth0

# 2. Capture traffic on any interface
sudo tcpdump -i any

# 3. Capture traffic to/from specific host
sudo tcpdump host api.example.com

# 4. Capture traffic on specific port
sudo tcpdump port 443
sudo tcpdump port 80 or port 443

# 5. Capture HTTP traffic (port 80)
sudo tcpdump -i any -A 'tcp port 80'
# -A: Print packets in ASCII

# 6. Capture DNS queries
sudo tcpdump -i any port 53

# 7. Save capture to file (for Wireshark)
sudo tcpdump -i any -w /tmp/capture.pcap

# 8. Read from capture file
tcpdump -r /tmp/capture.pcap

# 9. Capture with timestamps
sudo tcpdump -tttt -i any port 443

# 10. Capture specific number of packets
sudo tcpdump -c 100 -i any

# 11. Verbose output (show TTL, IP options)
sudo tcpdump -v -i any host api.example.com

# 12. Filter by source/destination
sudo tcpdump src 192.168.1.10
sudo tcpdump dst 10.0.0.5

# 13. Capture TCP SYN packets (connection attempts)
sudo tcpdump 'tcp[tcpflags] & tcp-syn != 0'

# 14. Capture TCP RST packets (connection resets)
sudo tcpdump 'tcp[tcpflags] & tcp-rst != 0'

# 15. Capture traffic between two hosts
sudo tcpdump host 192.168.1.10 and host 10.0.0.5

# 16. Exclude traffic from SSH (avoid clutter when SSH'd)
sudo tcpdump -i any port not 22

# 17. Capture with snaplen (full packet capture)
sudo tcpdump -s 65535 -i any -w /tmp/full-capture.pcap

# Example: Debug API call
sudo tcpdump -i any -A 'host api.example.com and port 443' -w /tmp/api-debug.pcap
# In another terminal:
curl https://api.example.com/users
# Stop tcpdump (Ctrl+C), analyze in Wireshark:
wireshark /tmp/api-debug.pcap
```

### Pattern 3: DNS Debugging

```bash
# 1. dig (recommended for debugging)
dig api.example.com

# Show only answer section
dig api.example.com +short

# Query specific record type
dig api.example.com A      # IPv4 address
dig api.example.com AAAA   # IPv6 address
dig api.example.com CNAME  # Canonical name
dig api.example.com MX     # Mail exchange
dig api.example.com TXT    # Text records

# Query specific DNS server
dig @8.8.8.8 api.example.com
dig @1.1.1.1 api.example.com

# Trace DNS resolution path
dig api.example.com +trace

# Show TTL (time to live)
dig api.example.com +noall +answer +ttlid

# Reverse DNS lookup
dig -x 93.184.216.34

# 2. nslookup (simpler, cross-platform)
nslookup api.example.com
nslookup api.example.com 8.8.8.8

# 3. host (concise output)
host api.example.com
host -t MX example.com

# 4. Check /etc/hosts override
cat /etc/hosts | grep api.example.com

# 5. Check DNS resolver configuration
cat /etc/resolv.conf

# 6. Test DNS propagation
# Query multiple DNS servers
for ns in 8.8.8.8 1.1.1.1 208.67.222.222; do
  echo "DNS Server: $ns"
  dig @$ns api.example.com +short
done

# Example: Debug DNS issue
# Step 1: Check system resolver
dig api.example.com +short
# Step 2: Check Google DNS
dig @8.8.8.8 api.example.com +short
# Step 3: Trace resolution
dig api.example.com +trace
# Step 4: Check if /etc/hosts override
grep api.example.com /etc/hosts
```

### Pattern 4: SSL/TLS Debugging

```bash
# 1. Test SSL connection
openssl s_client -connect api.example.com:443

# 2. Show certificate details
openssl s_client -connect api.example.com:443 -showcerts

# 3. Test with SNI (Server Name Indication)
openssl s_client -connect api.example.com:443 -servername api.example.com

# 4. Test specific TLS version
openssl s_client -connect api.example.com:443 -tls1_2
openssl s_client -connect api.example.com:443 -tls1_3

# 5. Check certificate expiration
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -dates

# 6. Verify certificate chain
echo | openssl s_client -connect api.example.com:443 -showcerts 2>/dev/null | \
  openssl x509 -noout -text

# 7. Check certificate subject
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -subject

# 8. Test cipher suites
openssl s_client -connect api.example.com:443 -cipher 'ECDHE-RSA-AES128-GCM-SHA256'

# 9. Dump all supported ciphers
nmap --script ssl-enum-ciphers -p 443 api.example.com

# 10. Check OCSP stapling
openssl s_client -connect api.example.com:443 -status

# 11. Verify certificate against CA bundle
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -out /tmp/cert.pem
openssl verify -CAfile /etc/ssl/certs/ca-bundle.crt /tmp/cert.pem

# Example: Debug SSL error
# Step 1: Test connection
openssl s_client -connect api.example.com:443 -servername api.example.com
# Look for "Verify return code: 0 (ok)" or error message

# Step 2: Check certificate dates
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -dates

# Step 3: Check certificate chain
curl -v https://api.example.com 2>&1 | grep -A 5 "SSL certificate"
```

### Pattern 5: Network Tracing (strace, lsof)

```bash
# 1. strace - Trace system calls (network operations)
# Trace all syscalls for process
strace -p <pid>

# Trace only network syscalls
strace -e trace=network -p <pid>
# Shows: socket, connect, bind, listen, accept, send, recv

# Trace with timestamps
strace -tt -e trace=network -p <pid>

# Save to file
strace -e trace=network -o /tmp/strace.log -p <pid>

# Trace new process from start
strace -e trace=network python app.py

# Example: Debug connection issue
strace -e trace=network,open,stat python -c "import requests; requests.get('https://api.example.com')"
# Look for connect() calls, check errno

# 2. lsof - List open files (including sockets)
# Show all network connections
lsof -i

# Show connections on specific port
lsof -i :8080

# Show connections for specific process
lsof -p <pid>
lsof -c python  # All python processes

# Show listening ports
lsof -i -sTCP:LISTEN

# Show established connections
lsof -i -sTCP:ESTABLISHED

# Show connections to specific host
lsof -i @api.example.com

# Show IPv4 connections
lsof -i 4

# Continuous monitoring
lsof -i -r 2  # Refresh every 2 seconds

# Example: Find what's using port 8080
lsof -i :8080
# Output: Shows PID, command, user
kill <pid>  # If needed

# 3. netstat (alternative to lsof)
# Show all listening ports
netstat -tuln

# Show all connections with process info
netstat -tunap

# Show routing table
netstat -r

# 4. ss (modern alternative to netstat)
# Show all TCP connections
ss -t

# Show listening sockets
ss -tl

# Show process using socket
ss -tp

# Show stats
ss -s
```

### Pattern 6: Connectivity Testing (ping, traceroute, mtr)

```bash
# 1. ping - Basic connectivity test
ping api.example.com
ping -c 4 api.example.com  # Send 4 packets

# Test with custom packet size
ping -s 1000 api.example.com

# Flood ping (requires root, testing only)
sudo ping -f api.example.com

# 2. traceroute - Show network path
traceroute api.example.com

# Use ICMP instead of UDP
traceroute -I api.example.com

# Show AS numbers
traceroute -A api.example.com

# Max hops
traceroute -m 20 api.example.com

# 3. mtr - Combined ping + traceroute
mtr api.example.com

# Run for 100 cycles
mtr -c 100 api.example.com

# Report mode (non-interactive)
mtr -r -c 100 api.example.com

# Show both hostnames and IPs
mtr -b api.example.com

# 4. netcat (nc) - Manual connection testing
# Test TCP connection
nc -zv api.example.com 443

# Test port range
nc -zv api.example.com 80-443

# Send HTTP request manually
echo -e "GET / HTTP/1.1\r\nHost: api.example.com\r\n\r\n" | nc api.example.com 80

# Listen on port (server mode)
nc -l 8080

# Example: Debug intermittent connectivity
# Terminal 1: Run mtr
mtr -r -c 1000 api.example.com > /tmp/mtr-report.txt

# Terminal 2: Monitor connections
watch -n 1 'ss -t | grep api.example.com'

# Analyze results
cat /tmp/mtr-report.txt | grep -E 'Loss%|[0-9]+\.[0-9]+'
```

### Pattern 7: HTTP Header Inspection

```bash
# 1. Inspect request headers
curl -v https://api.example.com/users 2>&1 | grep '^>'

# 2. Inspect response headers
curl -v https://api.example.com/users 2>&1 | grep '^<'

# 3. Common headers to check
# Content-Type
curl -I https://api.example.com/users | grep -i content-type

# Cache-Control
curl -I https://api.example.com/users | grep -i cache-control

# CORS headers
curl -I https://api.example.com/users | grep -i access-control

# Rate limiting
curl -I https://api.example.com/users | grep -i rate-limit

# 4. Test CORS preflight
curl -X OPTIONS https://api.example.com/users \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v

# 5. Check compression
curl -H "Accept-Encoding: gzip" -I https://api.example.com/users | grep -i content-encoding

# 6. Test authentication headers
curl -H "Authorization: Bearer token123" -I https://api.example.com/users

# 7. Custom User-Agent
curl -A "MyApp/1.0" -I https://api.example.com/users
```

---

## Quick Reference

### Network Debugging Toolbox

```bash
# Install essential tools (Ubuntu/Debian)
sudo apt-get update && sudo apt-get install -y \
  curl wget netcat-openbsd \
  dnsutils net-tools iproute2 \
  tcpdump wireshark-cli \
  mtr traceroute nmap \
  openssl

# Install on macOS
brew install curl wget netcat \
  bind dnsutils \
  tcpdump wireshark \
  mtr nmap openssl
```

### Common curl Options

| Flag | Purpose | Example |
|------|---------|---------|
| `-v` | Verbose output | `curl -v https://api.example.com` |
| `-I` | HEAD request only | `curl -I https://api.example.com` |
| `-i` | Include headers | `curl -i https://api.example.com` |
| `-L` | Follow redirects | `curl -L https://example.com` |
| `-H` | Custom header | `curl -H "Auth: token" https://api.example.com` |
| `-X` | HTTP method | `curl -X POST https://api.example.com` |
| `-d` | Request data | `curl -d '{"key":"val"}' https://api.example.com` |
| `-k` | Ignore SSL errors | `curl -k https://self-signed.example.com` |
| `-w` | Custom output format | `curl -w "%{http_code}" https://api.example.com` |

### tcpdump Filters

```bash
# Protocol
tcpdump tcp
tcpdump udp
tcpdump icmp

# Host
tcpdump host api.example.com
tcpdump src 192.168.1.10
tcpdump dst 10.0.0.5

# Port
tcpdump port 443
tcpdump portrange 8000-9000

# Combinations
tcpdump 'tcp and port 80'
tcpdump 'host api.example.com and (port 80 or port 443)'

# Packet content
tcpdump -A 'tcp port 80'  # ASCII
tcpdump -X 'tcp port 80'  # Hex + ASCII
```

---

## Anti-Patterns

### ❌ Ignoring SSL Errors in Production

```bash
# WRONG: Disabling SSL verification
curl -k https://api.example.com  # Security risk!

# CORRECT: Fix certificate issue
# Check cert: openssl s_client -connect api.example.com:443
# Update CA bundle or fix certificate
```

### ❌ Using ping for Application Health

```bash
# WRONG: ICMP may be blocked
ping api.example.com  # Firewall may block ICMP

# CORRECT: HTTP health check
curl -f https://api.example.com/health
```

### ❌ Capturing Too Much Data

```bash
# WRONG: Unbounded tcpdump
sudo tcpdump -i any -w /tmp/capture.pcap  # Fills disk!

# CORRECT: Limit capture
sudo tcpdump -i any -c 1000 -w /tmp/capture.pcap  # 1000 packets
sudo tcpdump -i any -G 60 -w /tmp/capture.pcap    # 60 seconds
```

### ❌ Not Using SNI with openssl

```bash
# WRONG: Missing SNI
openssl s_client -connect api.example.com:443

# CORRECT: Include SNI
openssl s_client -connect api.example.com:443 -servername api.example.com
```

---

## Related Skills

- **debugging/container-debugging.md** - Network debugging in containers
- **debugging/distributed-systems-debugging.md** - Multi-service network issues
- **observability/distributed-tracing.md** - Trace network calls across services
- **api/rest-api-design.md** - HTTP best practices

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
