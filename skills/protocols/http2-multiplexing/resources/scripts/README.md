# HTTP/2 Multiplexing Scripts

This directory contains executable scripts for testing, benchmarking, and analyzing HTTP/2 protocol features.

## Scripts Overview

### benchmark_http2.py
Compares HTTP/1.1 and HTTP/2 performance characteristics including multiplexing benefits, header compression, and connection efficiency.

**Usage**:
```bash
# Basic benchmark
python benchmark_http2.py --url https://example.com --requests 50

# JSON output
python benchmark_http2.py --url https://example.com --requests 100 --json results.json

# Verbose output
python benchmark_http2.py --url https://example.com --verbose
```

**Features**:
- Simulates HTTP/1.1 with 6 concurrent connections
- Simulates HTTP/2 with single multiplexed connection
- HPACK compression simulation
- Latency percentiles (P95, P99)
- Throughput comparison
- Bandwidth efficiency analysis

**Output**:
```
======================================================================
HTTP/2 vs HTTP/1.1 Performance Benchmark
======================================================================

Metric                         HTTP/1.1        HTTP/2          Improvement
----------------------------------------------------------------------
Requests/sec                   45.2            120.5           +166.6%
Avg latency (ms)               110.5           41.2            62.7% faster
Median latency (ms)            105.0           38.5            -66.5ms
P95 latency (ms)               180.0           68.0            -112.0ms
Bytes sent                     21000           1200            94.3% less
Connections used               6               1               -5

Summary:
  - HTTP/2 is 62.7% faster on average
  - HTTP/2 uses 94.3% less bandwidth (HPACK)
  - HTTP/2 uses 5 fewer connections
```

---

### analyze_hpack.py
Analyzes HPACK header compression efficiency across multiple requests on the same connection.

**Usage**:
```bash
# Demo mode with sample requests
python analyze_hpack.py --demo

# Analyze custom headers from file
python analyze_hpack.py --requests headers.txt

# Verbose output with per-header details
python analyze_hpack.py --demo --verbose

# JSON output
python analyze_hpack.py --demo --json compression.json

# Custom dynamic table size
python analyze_hpack.py --demo --table-size 8192
```

**Headers File Format**:
```
:method: GET
:path: /api/users/1
:scheme: https
host: api.example.com
authorization: Bearer token123

:method: GET
:path: /api/users/2
:scheme: https
host: api.example.com
authorization: Bearer token123
```

**Features**:
- RFC 7541 static table (61 entries)
- Dynamic table simulation with FIFO eviction
- Indexed vs literal encoding
- Compression ratio calculation
- Visual compression breakdown

**Output**:
```
================================================================================
HPACK Header Compression Analysis
================================================================================

Request #1:
  Uncompressed: 420 bytes
  Compressed:   122 bytes
  Compression:  70.9%
  Dynamic table size: 180 bytes

Request #2:
  Uncompressed: 418 bytes
  Compressed:   22 bytes
  Compression:  94.7%
  Dynamic table size: 180 bytes

Summary:
  Total requests:     5
  Total uncompressed: 2095 bytes
  Total compressed:   212 bytes
  Average compression: 89.9%
  Bytes saved:        1883 bytes

  Compression by request:
    Request 1: █████████████████████████████████████ 70.9%
    Request 2: █████████████████████████████████████████████ 94.7%
    Request 3: █████████████████████████████████████████████ 94.7%
    Request 4: █████████████████████████████████████████████ 94.7%
    Request 5: █████████████████████████████████████████████ 94.7%
```

---

### test_server_push.sh
Tests HTTP/2 server push functionality, measuring performance impact and validating cache behavior.

**Usage**:
```bash
# Basic test
./test_server_push.sh --url https://example.com

# JSON output
./test_server_push.sh --url https://example.com --json results.json

# Verbose output
./test_server_push.sh --url https://example.com --verbose

# Custom timeout
./test_server_push.sh --url https://example.com --timeout 30
```

**Features**:
- Detect HTTP/2 support
- Identify server push via Link headers
- Analyze PUSH_PROMISE frames (requires nghttp)
- Measure performance impact
- Validate cache headers on pushed resources
- Compare HTTP/2 vs HTTP/1.1 load times

**Output**:
```
======================================================================
HTTP/2 Server Push Tester
======================================================================

URL: https://example.com

[SUCCESS] Server supports HTTP/2
[SUCCESS] Server push detected via Link headers
  < link: </style.css>; rel=preload; as=style
  < link: </script.js>; rel=preload; as=script

PUSH_PROMISE frames detected:
  recv PUSH_PROMISE frame <stream_id=1, promised_stream_id=2>
  recv PUSH_PROMISE frame <stream_id=1, promised_stream_id=4>

Pushed resources:
  - /style.css
  - /script.js

Performance comparison:
  HTTP/2 (with potential push): 0m0.245s
  HTTP/1.1 (no push):          0m0.412s

Cache headers for pushed resource (/style.css):
  cache-control: public, max-age=31536000
[SUCCESS] Resource has max-age directive (good for caching)

======================================================================
Test completed
======================================================================
```

---

## Prerequisites

### Python Dependencies
```bash
# No external dependencies required for basic functionality
# All scripts use Python 3 standard library

# Optional: for advanced features
pip install requests h2
```

### System Tools
```bash
# curl with HTTP/2 support (required for test_server_push.sh)
curl --version | grep HTTP2

# nghttp for detailed frame analysis (optional)
# macOS
brew install nghttp2

# Ubuntu/Debian
apt-get install nghttp2-client

# Fedora/RHEL
dnf install nghttp2
```

---

## Examples

### Complete HTTP/2 Analysis Workflow

```bash
# 1. Test server push support
./test_server_push.sh --url https://example.com --json push-report.json

# 2. Benchmark HTTP/2 vs HTTP/1.1
python benchmark_http2.py --url https://example.com --requests 100 --json bench-results.json

# 3. Analyze HPACK compression
python analyze_hpack.py --demo --verbose

# 4. Review results
cat push-report.json bench-results.json
```

### Testing Different Scenarios

```bash
# High-latency network simulation
python benchmark_http2.py --url https://example.com --requests 200

# Many concurrent requests (test multiplexing)
python benchmark_http2.py --url https://api.example.com --requests 500

# Custom HPACK table size (match server settings)
python analyze_hpack.py --demo --table-size 8192
```

### CI/CD Integration

```bash
#!/bin/bash
# Run in CI pipeline

# Benchmark performance
python benchmark_http2.py \
    --url "$STAGING_URL" \
    --requests 100 \
    --json benchmark-results.json

# Parse results
RPS=$(jq '.http2.requests_per_second' benchmark-results.json)
THRESHOLD=100

if (( $(echo "$RPS < $THRESHOLD" | bc -l) )); then
    echo "Performance regression: $RPS req/s < $THRESHOLD req/s"
    exit 1
fi

echo "Performance test passed: $RPS req/s"
```

---

## Output Formats

All scripts support JSON output for easy integration with monitoring tools, CI/CD pipelines, and dashboards.

### benchmark_http2.py JSON
```json
{
  "http1": {
    "protocol": "HTTP/1.1",
    "total_time": 2.5,
    "requests_per_second": 40.0,
    "avg_latency": 0.125,
    "compression_ratio": 0.0
  },
  "http2": {
    "protocol": "HTTP/2",
    "total_time": 1.2,
    "requests_per_second": 83.3,
    "avg_latency": 0.048,
    "compression_ratio": 0.94
  },
  "comparison": {
    "throughput_improvement": {
      "rps_percent": 108.25
    },
    "latency_improvement": {
      "percent_faster": 61.6
    }
  }
}
```

### analyze_hpack.py JSON
```json
{
  "table_size": 4096,
  "num_requests": 5,
  "analyses": [
    {
      "request_num": 1,
      "total_uncompressed": 420,
      "total_compressed": 122,
      "compression_ratio": 70.95,
      "dynamic_table_size": 180
    }
  ]
}
```

### test_server_push.sh JSON
```json
{
  "url": "https://example.com",
  "timestamp": "2025-10-27T12:00:00Z",
  "http2_support": true,
  "server_push_detected": true,
  "test_completed": true
}
```

---

## Troubleshooting

### Issue: "curl does not support HTTP/2"

**Solution**: Install curl with HTTP/2 support
```bash
# macOS
brew install curl

# Ubuntu/Debian (ensure libcurl4-openssl-dev)
apt-get install curl libcurl4-openssl-dev

# Verify
curl --version | grep HTTP2
```

### Issue: HPACK compression ratio lower than expected

**Possible causes**:
- Different headers between requests (not cached in dynamic table)
- Dynamic table size too small
- Headers not suitable for compression

**Solution**:
```bash
# Increase table size
python analyze_hpack.py --demo --table-size 8192 --verbose

# Review per-header breakdown
python analyze_hpack.py --demo --verbose
```

### Issue: Server push not detected

**Possible causes**:
- Server doesn't support push
- Push disabled via SETTINGS frame
- No suitable resources to push

**Solution**:
```bash
# Test with nghttp for detailed analysis
nghttp -v https://example.com

# Check server configuration (nginx example)
# nginx.conf should have:
# http2_push /style.css;
```

---

## References

- **RFC 7540**: HTTP/2 Protocol
- **RFC 7541**: HPACK Header Compression
- **nghttp2**: https://nghttp2.org/
- **curl HTTP/2**: https://curl.se/docs/http2.html

---

**Last Updated**: 2025-10-27
