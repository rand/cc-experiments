---
name: cryptography-tls-configuration
description: TLS/SSL configuration including TLS 1.2/1.3 setup, cipher suites, security best practices, and server configuration
---

# TLS Configuration

**Scope**: TLS 1.2/1.3 setup, cipher suites, security configuration, server/client setup
**Lines**: ~380
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Configuring HTTPS servers
- Setting up TLS for APIs
- Implementing secure client connections
- Troubleshooting TLS handshake issues
- Upgrading from TLS 1.2 to TLS 1.3
- Selecting cipher suites
- Configuring mutual TLS (mTLS)
- Meeting security compliance requirements

## Core Concepts

### TLS 1.2 vs TLS 1.3

**Key Differences**:
```
TLS 1.2:
├─ 2-RTT handshake (longer)
├─ Many cipher suites (some weak)
├─ RSA key exchange option
└─ Renegotiation support

TLS 1.3:
├─ 1-RTT handshake (faster)
├─ 0-RTT option (even faster, but replay risk)
├─ Only modern ciphers (AES-GCM, ChaCha20-Poly1305)
├─ Perfect forward secrecy mandatory
└─ No renegotiation
```

**Handshake Comparison**:
```
TLS 1.2 (2-RTT):
Client → ClientHello
       ← ServerHello, Certificate, ServerKeyExchange, ServerHelloDone
Client → ClientKeyExchange, ChangeCipherSpec, Finished
       ← ChangeCipherSpec, Finished
[Application Data]

TLS 1.3 (1-RTT):
Client → ClientHello (with key share)
       ← ServerHello, Certificate, Finished
Client → Finished
[Application Data]
```

### Cipher Suites

**TLS 1.3 Cipher Suites** (simplified):
```
TLS_AES_128_GCM_SHA256
TLS_AES_256_GCM_SHA384
TLS_CHACHA20_POLY1305_SHA256
```

**TLS 1.2 Recommended Cipher Suites**:
```
TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256
```

**Cipher Suite Components**:
```
TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
    │     │         │       │    └─ Hash: SHA256
    │     │         │       └─ Mode: GCM (AEAD)
    │     │         └─ Cipher: AES 128-bit
    │     └─ Authentication: RSA
    └─ Key Exchange: ECDHE (Elliptic Curve Diffie-Hellman Ephemeral)
```

---

## Server Configuration

### Nginx

**Modern Configuration**:
```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    # Certificates
    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # TLS versions
    ssl_protocols TLSv1.2 TLSv1.3;

    # Cipher suites (TLS 1.2)
    ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305';
    ssl_prefer_server_ciphers on;

    # TLS 1.3 ciphers (explicit, though defaults are good)
    ssl_conf_command Ciphersuites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/ssl/certs/ca-chain.crt;

    # Session cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://backend;
    }
}
```

### Apache

**Modern Configuration**:
```apache
<VirtualHost *:443>
    ServerName example.com

    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/example.com.crt
    SSLCertificateKeyFile /etc/ssl/private/example.com.key
    SSLCertificateChainFile /etc/ssl/certs/ca-chain.crt

    # TLS versions
    SSLProtocol -all +TLSv1.2 +TLSv1.3

    # Cipher suites
    SSLCipherSuite ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384
    SSLHonorCipherOrder on

    # OCSP stapling
    SSLUseStapling on
    SSLStaplingCache "shmcb:logs/ssl_stapling(32768)"

    # HSTS
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
</VirtualHost>
```

### Node.js

**HTTPS Server**:
```javascript
const https = require('https');
const fs = require('fs');

const options = {
    key: fs.readFileSync('/etc/ssl/private/example.com.key'),
    cert: fs.readFileSync('/etc/ssl/certs/example.com.crt'),
    ca: fs.readFileSync('/etc/ssl/certs/ca-chain.crt'),

    // TLS version
    minVersion: 'TLSv1.2',
    maxVersion: 'TLSv1.3',

    // Cipher suites (TLS 1.2)
    ciphers: [
        'ECDHE-RSA-AES128-GCM-SHA256',
        'ECDHE-RSA-AES256-GCM-SHA384',
        'ECDHE-RSA-CHACHA20-POLY1305'
    ].join(':'),

    // Prefer server cipher order
    honorCipherOrder: true,

    // Session resumption
    sessionTimeout: 300
};

const server = https.createServer(options, (req, res) => {
    res.writeHead(200);
    res.end('Secure connection\n');
});

server.listen(443, () => {
    console.log('HTTPS server running on port 443');
});
```

---

## Client Configuration

### Python Requests

**Secure Client**:
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_3
        ctx.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20')
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

session = requests.Session()
session.mount('https://', TLSAdapter())

# Make request
response = session.get('https://api.example.com')
print(f"TLS version: {response.raw.version}")  # 771 = TLS 1.2, 772 = TLS 1.3
```

### Go

**Secure Client**:
```go
package main

import (
    "crypto/tls"
    "fmt"
    "net/http"
)

func main() {
    tlsConfig := &tls.Config{
        MinVersion: tls.VersionTLS12,
        MaxVersion: tls.VersionTLS13,
        CipherSuites: []uint16{
            tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
            tls.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
            tls.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305,
        },
        PreferServerCipherSuites: false,
    }

    client := &http.Client{
        Transport: &http.Transport{
            TLSClientConfig: tlsConfig,
        },
    }

    resp, err := client.Get("https://api.example.com")
    if err != nil {
        panic(err)
    }
    defer resp.Body.Close()

    fmt.Printf("TLS version: %d\n", resp.TLS.Version)
    fmt.Printf("Cipher suite: %x\n", resp.TLS.CipherSuite)
}
```

### Rust

**Secure Client**:
```rust
use reqwest::ClientBuilder;
use std::time::Duration;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = ClientBuilder::new()
        .min_tls_version(reqwest::tls::Version::TLS_1_2)
        .max_tls_version(reqwest::tls::Version::TLS_1_3)
        .timeout(Duration::from_secs(10))
        .build()?;

    let response = client
        .get("https://api.example.com")
        .send()
        .await?;

    println!("Status: {}", response.status());
    Ok(())
}
```

---

## Patterns

### Pattern 1: Mutual TLS (mTLS)

**Server Configuration** (Nginx):
```nginx
server {
    listen 443 ssl;

    ssl_certificate /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/private/server.key;

    # Client certificate verification
    ssl_client_certificate /etc/ssl/certs/ca.crt;
    ssl_verify_client on;
    ssl_verify_depth 2;

    location / {
        # Client cert subject available
        proxy_set_header X-Client-Cert-DN $ssl_client_s_dn;
        proxy_pass http://backend;
    }
}
```

**Go Client with mTLS**:
```go
package main

import (
    "crypto/tls"
    "crypto/x509"
    "io/ioutil"
    "net/http"
)

func main() {
    // Load client cert
    cert, err := tls.LoadX509KeyPair("client.crt", "client.key")
    if err != nil {
        panic(err)
    }

    // Load CA cert
    caCert, err := ioutil.ReadFile("ca.crt")
    if err != nil {
        panic(err)
    }
    caCertPool := x509.NewCertPool()
    caCertPool.AppendCertsFromPEM(caCert)

    tlsConfig := &tls.Config{
        Certificates: []tls.Certificate{cert},
        RootCAs:      caCertPool,
        MinVersion:   tls.VersionTLS12,
    }

    client := &http.Client{
        Transport: &http.Transport{
            TLSClientConfig: tlsConfig,
        },
    }

    resp, err := client.Get("https://api.example.com")
    if err != nil {
        panic(err)
    }
    defer resp.Body.Close()
}
```

### Pattern 2: TLS Session Resumption

**Session Tickets** (Nginx):
```nginx
# Disable session tickets (privacy)
ssl_session_tickets off;

# Or enable with rotation
ssl_session_tickets on;
ssl_session_ticket_key /etc/ssl/ticket_key1.key;
ssl_session_ticket_key /etc/ssl/ticket_key2.key;
```

**Session Cache** (better option):
```nginx
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

---

## Best Practices

### 1. Protocol Selection

```bash
# ✅ Good: TLS 1.2 and 1.3 only
ssl_protocols TLSv1.2 TLSv1.3;

# ❌ Bad: Old protocols
ssl_protocols SSLv3 TLSv1 TLSv1.1 TLSv1.2;
```

### 2. Cipher Suite Selection

```bash
# ✅ Good: Modern ciphers only
ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305';

# ❌ Bad: Weak ciphers included
ssl_ciphers 'ALL:!aNULL:!eNULL';
```

### 3. Perfect Forward Secrecy

```nginx
# ✅ Good: ECDHE for forward secrecy
ssl_ciphers 'ECDHE-RSA-...';
ssl_prefer_server_ciphers on;

# ❌ Bad: Static RSA key exchange
ssl_ciphers 'RSA-AES128-SHA';
```

### 4. Certificate Chain

```python
# ✅ Good: Include full chain
with open('fullchain.pem') as f:  # cert + intermediate
    cert = f.read()

# ❌ Bad: Only leaf certificate
with open('cert.pem') as f:  # missing intermediate
    cert = f.read()
```

### 5. OCSP Stapling

```nginx
# ✅ Good: Enable OCSP stapling
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/ssl/certs/ca-chain.crt;

# ❌ Bad: No OCSP stapling (client must check)
```

---

## Security Headers

### HTTP Strict Transport Security (HSTS)

```nginx
# Force HTTPS for 1 year, including subdomains
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

### Additional Security Headers

```nginx
# Prevent MIME sniffing
add_header X-Content-Type-Options "nosniff" always;

# XSS protection
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;

# CSP
add_header Content-Security-Policy "default-src 'self'" always;
```

---

## Troubleshooting

### Issue 1: Handshake Failure

**Check with OpenSSL**:
```bash
openssl s_client -connect example.com:443 -tls1_2
openssl s_client -connect example.com:443 -tls1_3
```

**Common causes**:
- Mismatched TLS versions
- No common cipher suites
- Invalid certificate chain
- SNI not sent (old clients)

### Issue 2: Performance Issues

**Symptoms**: Slow HTTPS connections

**Check**:
```bash
# Measure handshake time
curl -w "time_appconnect: %{time_appconnect}s\n" -o /dev/null -s https://example.com

# Should be < 200ms for TLS 1.3, < 400ms for TLS 1.2
```

**Solutions**:
- Enable session resumption
- Use TLS 1.3 (1-RTT)
- Enable OCSP stapling
- Use HTTP/2

### Issue 3: Certificate Chain Issues

**Check chain**:
```bash
openssl s_client -connect example.com:443 -showcerts
```

**Fix**: Ensure full chain in certificate file
```bash
cat cert.pem intermediate.pem > fullchain.pem
```

---

## Testing TLS Configuration

### Online Tools

```bash
# SSL Labs
https://www.ssllabs.com/ssltest/analyze.html?d=example.com

# Mozilla Observatory
https://observatory.mozilla.org/analyze/example.com
```

### Local Testing

```bash
# Test specific TLS version
openssl s_client -connect example.com:443 -tls1_2
openssl s_client -connect example.com:443 -tls1_3

# Test cipher suite
openssl s_client -connect example.com:443 -cipher 'ECDHE-RSA-AES128-GCM-SHA256'

# Test with curl
curl -v --tlsv1.2 --tls-max 1.2 https://example.com
curl -v --tlsv1.3 --tls-max 1.3 https://example.com
```

---

## TLS 1.3 Migration

### Gradual Rollout

```nginx
# Phase 1: Enable TLS 1.3 alongside 1.2
ssl_protocols TLSv1.2 TLSv1.3;

# Phase 2: Monitor adoption (check logs)
# Phase 3: Eventually deprecate TLS 1.2 (if possible)
```

### Compatibility Considerations

```
TLS 1.3 Support (as of 2025):
✅ All modern browsers
✅ Modern programming language libraries
⚠️ Some legacy enterprise systems
❌ Very old clients (pre-2018)
```

---

---

## Level 3 Resources

This skill includes comprehensive resources for advanced TLS configuration, testing, and validation.

### Structure

```
resources/
├── REFERENCE.md              # Detailed TLS specifications, RFCs, cipher suites
├── scripts/                  # Executable validation and testing scripts
│   ├── README.md
│   ├── validate_tls_config.sh    # Validate nginx/apache TLS configs
│   ├── check_cipher_suites.py    # List and verify cipher suites
│   └── test_tls_connection.py    # Test TLS connectivity and timing
└── examples/                 # Real-world configuration examples
    ├── nginx/
    │   ├── modern-tls-config.conf
    │   └── mtls-config.conf
    └── python/
        ├── tls_server.py
        └── tls_client.py
```

### Quick Start

**Validate TLS configuration**:
```bash
cd resources/scripts
./validate_tls_config.sh --file /etc/nginx/nginx.conf --verbose
```

**Check cipher suites on remote host**:
```bash
python check_cipher_suites.py --host example.com --json
```

**Test TLS connection with timing**:
```bash
python test_tls_connection.py example.com --test-all-versions
```

**Reference material**:
```bash
cat resources/REFERENCE.md  # TLS 1.2 vs 1.3, cipher suites, RFCs, OCSP
```

### Use Cases

- **Configuration validation**: Validate nginx/apache TLS settings against best practices
- **Cipher suite analysis**: Identify weak ciphers and security issues
- **Connection testing**: Test TLS handshake, measure timing, verify certificates
- **Learning**: Comprehensive reference for TLS protocols and RFCs
- **CI/CD integration**: JSON output for automated security testing

See `resources/scripts/README.md` for detailed usage examples and CI/CD integration patterns.

---

## Related Skills

- `cryptography-pki-fundamentals` - Certificate basics
- `cryptography-certificate-management` - Certificate lifecycle
- `networking-mtls-implementation` - Mutual TLS patterns
- `protocols-http2-multiplexing` - HTTP/2 over TLS
- `protocols-http3-quic` - QUIC with built-in TLS 1.3

---

**Last Updated**: 2025-10-27
