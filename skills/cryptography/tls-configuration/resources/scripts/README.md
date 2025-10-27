# TLS Configuration Scripts

This directory contains executable scripts for TLS configuration validation, cipher suite analysis, and connection testing.

## Scripts Overview

### validate_tls_config.sh
Validate TLS configuration in nginx, apache, or other server configurations. Checks for security best practices, deprecated protocols, weak ciphers, and missing security headers.

**Usage**:
```bash
./validate_tls_config.sh --file /etc/nginx/sites-available/default
./validate_tls_config.sh --file /etc/apache2/sites-available/default-ssl.conf --type apache
./validate_tls_config.sh --file nginx.conf --strict --json > report.json
```

**Options**:
- `-f, --file FILE` - Configuration file to validate (required)
- `-t, --type TYPE` - Server type: nginx, apache, auto (default: auto)
- `-s, --strict` - Strict mode (warnings become errors)
- `-j, --json` - JSON output
- `-v, --verbose` - Verbose output

**Checks performed**:
- TLS protocol versions (1.2, 1.3 recommended)
- Cipher suite configuration
- Forward secrecy (ECDHE)
- AEAD ciphers (GCM, ChaCha20)
- OCSP stapling
- HSTS headers
- Session cache settings
- HTTP/2 support

**Exit codes**:
- 0 - All checks passed
- 1 - Errors found
- 2 - Invalid arguments

---

### check_cipher_suites.py
List and verify TLS cipher suites for a given host or list available cipher suites on the local system.

**Usage**:
```bash
# Scan remote host
python check_cipher_suites.py --host example.com
python check_cipher_suites.py --host api.github.com --port 443 --json

# List local ciphers
python check_cipher_suites.py --list-ciphers
python check_cipher_suites.py --list-ciphers --tls-version 1.3
```

**Options**:
- `--host HOST` - Target host to scan
- `--port PORT` - Target port (default: 443)
- `--list-ciphers` - List available cipher suites on this system
- `--tls-version VERSION` - Filter ciphers by TLS version (1.0, 1.1, 1.2, 1.3)
- `-j, --json` - JSON output
- `-v, --verbose` - Verbose output

**Output includes**:
- Security score (A+, A, B, C)
- Supported TLS protocols
- Cipher suite details:
  - Name and protocol version
  - Key size (bits)
  - Forward secrecy support
  - AEAD support
  - Security rating (STRONG, MEDIUM, WEAK)
  - Warnings
- Certificate information

**Exit codes**:
- 0 - No weak ciphers found
- 1 - Weak ciphers detected or scan failed

---

### test_tls_connection.py
Test TLS connections with detailed handshake analysis, timing information, and certificate validation.

**Usage**:
```bash
# Basic test
python test_tls_connection.py example.com

# Test specific TLS versions
python test_tls_connection.py example.com --min-tls 1.2 --max-tls 1.3

# Test all versions
python test_tls_connection.py example.com --test-all-versions

# Test specific cipher
python test_tls_connection.py example.com --cipher ECDHE-RSA-AES128-GCM-SHA256

# Skip certificate verification
python test_tls_connection.py example.com --no-verify --verbose
```

**Options**:
- `host` - Target host (required)
- `--port PORT` - Target port (default: 443)
- `--min-tls VERSION` - Minimum TLS version (default: 1.2)
- `--max-tls VERSION` - Maximum TLS version (default: 1.3)
- `--cipher CIPHER` - Specific cipher suite to test
- `--test-all-versions` - Test all TLS versions separately
- `--no-verify` - Disable certificate verification
- `--timeout SECONDS` - Connection timeout (default: 10)
- `-j, --json` - JSON output
- `-v, --verbose` - Verbose output

**Output includes**:
- Connection success/failure
- TLS version negotiated
- Cipher suite negotiated
- Cipher strength (bits)
- Timing breakdown:
  - DNS lookup time
  - TCP connection time
  - TLS handshake time
  - Total time
- Certificate details:
  - Subject and issuer
  - Serial number
  - Validity period
  - Subject Alternative Names (SANs)
- Warnings (deprecated protocols, expiring certs)

**Exit codes**:
- 0 - Connection successful
- 1 - Connection failed

---

## Prerequisites

### System Tools
```bash
# For validate_tls_config.sh
bash 4.0+
grep, cat, basic Unix tools

# For check_cipher_suites.py and test_tls_connection.py
python 3.7+
```

### Python Dependencies
No external dependencies required - uses Python standard library only:
- `ssl`
- `socket`
- `json`
- `argparse`
- `dataclasses`
- `datetime`

---

## Examples

### Full TLS Security Assessment

```bash
# 1. Validate server configuration
./validate_tls_config.sh --file /etc/nginx/nginx.conf --verbose

# 2. Scan live host for cipher suites
python check_cipher_suites.py --host example.com --json > ciphers.json

# 3. Test connection and timing
python test_tls_connection.py example.com --verbose

# 4. Test all TLS versions
python test_tls_connection.py example.com --test-all-versions
```

### CI/CD Integration

```bash
# Validate config in strict mode (fail on warnings)
./validate_tls_config.sh \
  --file nginx.conf \
  --strict \
  --json > tls-config-report.json

# Check for weak ciphers (exit 1 if found)
python check_cipher_suites.py \
  --host staging.example.com \
  --json > cipher-report.json

# Test TLS 1.3 support
python test_tls_connection.py \
  staging.example.com \
  --min-tls 1.3 \
  --max-tls 1.3 \
  --json > tls13-test.json
```

### Development and Debugging

```bash
# List all available ciphers on system
python check_cipher_suites.py --list-ciphers

# Test specific cipher suite
python test_tls_connection.py example.com \
  --cipher ECDHE-RSA-AES256-GCM-SHA384 \
  --verbose

# Test with self-signed cert (skip verification)
python test_tls_connection.py localhost \
  --port 8443 \
  --no-verify
```

---

## JSON Output Format

All scripts support `--json` output for programmatic parsing and CI/CD integration.

**validate_tls_config.sh**:
```json
{
  "version": "1.0.0",
  "file": "/etc/nginx/nginx.conf",
  "server_type": "nginx",
  "timestamp": "2025-10-27T12:00:00Z",
  "results": {
    "passed": 12,
    "warnings": 2,
    "errors": 0,
    "total": 14
  },
  "status": "pass",
  "grade": "B"
}
```

**check_cipher_suites.py**:
```json
{
  "version": "1.0.0",
  "scan": {
    "host": "example.com",
    "port": 443,
    "security_score": "A"
  },
  "protocols": ["TLS 1.2", "TLS 1.3"],
  "cipher_suites": [
    {
      "name": "TLS_AES_256_GCM_SHA384",
      "protocol_version": "TLS 1.3",
      "bits": 256,
      "has_forward_secrecy": true,
      "is_aead": true,
      "security_rating": "STRONG",
      "warnings": []
    }
  ],
  "summary": {
    "total_ciphers": 2,
    "weak_ciphers": 0,
    "warnings": []
  }
}
```

**test_tls_connection.py**:
```json
{
  "version": "1.0.0",
  "timestamp": "2025-10-27T12:00:00Z",
  "result": {
    "success": true,
    "host": "example.com",
    "port": 443,
    "tls_version": "TLS 1.3",
    "cipher_suite": "TLS_AES_256_GCM_SHA384",
    "cipher_bits": 256,
    "warnings": []
  },
  "timing": {
    "dns_lookup_ms": 15.2,
    "tcp_connect_ms": 42.8,
    "tls_handshake_ms": 67.3,
    "total_ms": 125.3
  },
  "certificate": {
    "subject": {"commonName": "example.com"},
    "issuer": {"commonName": "DigiCert TLS RSA SHA256 2020 CA1"},
    "not_before": "Jan 1 00:00:00 2025 GMT",
    "not_after": "Jan 1 23:59:59 2026 GMT"
  }
}
```

---

## Safety Note

**IMPORTANT**: Only test systems you own or have explicit written authorization to scan. Unauthorized security testing may be illegal and unethical.

---

## Related Resources

- `../REFERENCE.md` - Detailed TLS specifications and RFCs
- `../examples/` - Example configurations
- Main skill: `../../tls-configuration.md`
