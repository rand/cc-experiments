---
name: cryptography-sni-routing
description: Server Name Indication (SNI) for multi-domain TLS hosting, routing, and configuration patterns
---

# SNI (Server Name Indication)

**Scope**: SNI protocol extension, multi-domain TLS hosting, routing, security implications
**Lines**: ~290
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Hosting multiple HTTPS domains on one IP
- Configuring reverse proxies with TLS
- Implementing TLS-based routing
- Troubleshooting certificate mismatch errors
- Setting up multi-tenant systems
- Working with load balancers
- Debugging old client compatibility
- Implementing TLS termination

## Core Concepts

### What is SNI?

**Problem SNI Solves**:
```
Before SNI (circa 2003):
Client → [TLS Handshake]
       ← [Certificate for ???]
Problem: Server doesn't know which certificate to send!

With SNI (2003+):
Client → [TLS Handshake + hostname: "example.com"]
       ← [Certificate for example.com]
Solution: Server sends correct certificate
```

**How SNI Works**:
```
1. Client initiates TLS handshake
2. Client includes hostname in ClientHello (SNI extension)
3. Server selects appropriate certificate based on SNI
4. Server continues handshake with correct certificate
5. Encrypted connection established
```

### SNI in ClientHello

**TLS Handshake with SNI**:
```
ClientHello
├─ Version: TLS 1.2
├─ Random: [32 bytes]
├─ Cipher Suites: [...]
└─ Extensions:
    └─ server_name (SNI):
        ├─ name_type: host_name (0)
        └─ host_name: "example.com"
```

**Viewing SNI with tcpdump**:
```bash
sudo tcpdump -i any -A 'tcp port 443' | grep -i "server_name"
```

---

## Server Configuration

### Nginx

**Multi-domain setup**:
```nginx
# Domain 1
server {
    listen 443 ssl;
    server_name example.com www.example.com;

    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    location / {
        proxy_pass http://backend1;
    }
}

# Domain 2
server {
    listen 443 ssl;
    server_name api.example.com;

    ssl_certificate /etc/ssl/certs/api.example.com.crt;
    ssl_certificate_key /etc/ssl/private/api.example.com.key;

    location / {
        proxy_pass http://backend2;
    }
}

# Domain 3
server {
    listen 443 ssl;
    server_name another-domain.com;

    ssl_certificate /etc/ssl/certs/another-domain.com.crt;
    ssl_certificate_key /etc/ssl/private/another-domain.com.key;

    location / {
        proxy_pass http://backend3;
    }
}
```

**SNI-based routing**:
```nginx
# Route based on SNI to different backends
map $ssl_server_name $backend {
    example.com          backend1:8080;
    api.example.com      backend2:8080;
    admin.example.com    backend3:8080;
    default              backend1:8080;
}

server {
    listen 443 ssl;
    server_name _;

    ssl_certificate /etc/ssl/certs/default.crt;
    ssl_certificate_key /etc/ssl/private/default.key;

    location / {
        proxy_pass http://$backend;
        proxy_set_header Host $ssl_server_name;
    }
}
```

### Apache

**Multi-domain setup**:
```apache
# Domain 1
<VirtualHost *:443>
    ServerName example.com
    ServerAlias www.example.com

    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/example.com.crt
    SSLCertificateKeyFile /etc/ssl/private/example.com.key
</VirtualHost>

# Domain 2
<VirtualHost *:443>
    ServerName api.example.com

    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/api.example.com.crt
    SSLCertificateKeyFile /etc/ssl/private/api.example.com.key
</VirtualHost>

# Enable SNI
SSLStrictSNIVHostCheck on
```

### Go HTTP Server

**Multi-domain TLS**:
```go
package main

import (
    "crypto/tls"
    "fmt"
    "net/http"
)

func main() {
    // Load certificates for different domains
    cert1, _ := tls.LoadX509KeyPair("example.com.crt", "example.com.key")
    cert2, _ := tls.LoadX509KeyPair("api.example.com.crt", "api.example.com.key")

    tlsConfig := &tls.Config{
        Certificates: []tls.Certificate{cert1, cert2},
        MinVersion:   tls.VersionTLS12,
    }

    // Go automatically handles SNI with multiple certificates
    server := &http.Server{
        Addr:      ":443",
        TLSConfig: tlsConfig,
        Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            fmt.Fprintf(w, "Connected to: %s\n", r.Host)
        }),
    }

    server.ListenAndServeTLS("", "")
}
```

**Custom SNI logic**:
```go
tlsConfig := &tls.Config{
    GetCertificate: func(hello *tls.ClientHelloInfo) (*tls.Certificate, error) {
        // Custom logic based on SNI
        switch hello.ServerName {
        case "example.com", "www.example.com":
            return &cert1, nil
        case "api.example.com":
            return &cert2, nil
        default:
            return &defaultCert, nil
        }
    },
}
```

---

## Client Configuration

### Python

**Set SNI explicitly**:
```python
import ssl
import socket

hostname = 'example.com'
context = ssl.create_default_context()

with socket.create_connection((hostname, 443)) as sock:
    # SNI automatically set from server_hostname parameter
    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
        print(f"SNI sent for: {hostname}")
        print(f"Certificate subject: {ssock.getpeercert()['subject']}")
```

**Requests library** (SNI automatic):
```python
import requests

# SNI automatically extracted from URL
response = requests.get('https://example.com')
```

### cURL

```bash
# SNI automatically sent
curl https://example.com

# Test different SNI vs Host header
curl --resolve example.com:443:192.168.1.1 https://example.com

# Test SNI with different hostname
curl --connect-to example.com:443:api.example.com:443 https://example.com
```

---

## Patterns

### Pattern 1: Wildcard Certificates with SNI

**Setup**:
```nginx
server {
    listen 443 ssl;
    server_name *.example.com;

    # Single wildcard cert for all subdomains
    ssl_certificate /etc/ssl/certs/wildcard.example.com.crt;
    ssl_certificate_key /etc/ssl/private/wildcard.example.com.key;

    # Route based on subdomain
    location / {
        set $subdomain "";
        if ($host ~* "^(.+)\.example\.com$") {
            set $subdomain $1;
        }

        proxy_pass http://$subdomain-backend:8080;
    }
}
```

### Pattern 2: Multi-Tenant Systems

**Tenant-specific certificates**:
```go
package main

import (
    "crypto/tls"
    "database/sql"
    "net/http"
)

type CertStore struct {
    db *sql.DB
}

func (cs *CertStore) GetCertificate(hello *tls.ClientHelloInfo) (*tls.Certificate, error) {
    // Fetch tenant cert from database based on SNI
    var certPEM, keyPEM string
    err := cs.db.QueryRow(
        "SELECT cert, key FROM tenant_certs WHERE domain = ?",
        hello.ServerName,
    ).Scan(&certPEM, &keyPEM)

    if err != nil {
        // Return default cert
        return getDefaultCert()
    }

    cert, err := tls.X509KeyPair([]byte(certPEM), []byte(keyPEM))
    return &cert, err
}

func main() {
    store := &CertStore{db: initDB()}

    tlsConfig := &tls.Config{
        GetCertificate: store.GetCertificate,
        MinVersion:     tls.VersionTLS12,
    }

    server := &http.Server{
        Addr:      ":443",
        TLSConfig: tlsConfig,
        Handler:   myHandler(),
    }

    server.ListenAndServeTLS("", "")
}
```

### Pattern 3: Default Certificate Fallback

```nginx
# Catch-all for invalid SNI
server {
    listen 443 ssl default_server;
    server_name _;

    ssl_certificate /etc/ssl/certs/default.crt;
    ssl_certificate_key /etc/ssl/private/default.key;

    return 404;
}

# Specific domains
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # ... normal config
}
```

---

## Security Considerations

### SNI Leaks Hostname

**Problem**: SNI is sent in plaintext during handshake

```
Eavesdropper can see:
✓ Destination hostname (from SNI)
✓ Client IP
✓ Connection timing
✗ Actual data (encrypted)
```

**Solution**: Encrypted Client Hello (ECH) / ESNI

```nginx
# Enable ECH (nginx 1.25+)
ssl_ech on;
ssl_ech_key /etc/ssl/ech-key.pem;
```

### SNI Spoofing

**Attack**: Client sends wrong SNI to bypass routing

**Mitigation**:
```nginx
# Verify SNI matches Host header
server {
    if ($ssl_server_name != $host) {
        return 421 "Mismatch Error";
    }
}
```

---

## Troubleshooting

### Issue 1: Certificate Mismatch

**Symptom**: Certificate doesn't match hostname

**Check SNI sent**:
```bash
openssl s_client -connect example.com:443 -servername example.com -tlsextdebug
```

**Common causes**:
- Client not sending SNI (very old clients)
- SNI mismatch with Host header
- Server not configured for SNI

### Issue 2: Old Clients Without SNI

**Affected clients**:
```
- IE 6 on Windows XP
- Java 6
- Python < 2.7.9
- Android < 2.3
```

**Workaround**: Dedicated IP per domain

```nginx
# Different IPs for each domain
server {
    listen 192.168.1.10:443 ssl;
    server_name example.com;
    ssl_certificate /etc/ssl/certs/example.com.crt;
}

server {
    listen 192.168.1.11:443 ssl;
    server_name api.example.com;
    ssl_certificate /etc/ssl/certs/api.example.com.crt;
}
```

### Issue 3: Load Balancer SNI

**Problem**: Load balancer needs to route based on SNI

**Solution** (HAProxy):
```haproxy
frontend https_front
    bind *:443
    mode tcp
    tcp-request inspect-delay 5s
    tcp-request content accept if { req_ssl_hello_type 1 }

    use_backend example_com if { req_ssl_sni -i example.com }
    use_backend api_example_com if { req_ssl_sni -i api.example.com }
    default_backend default_backend

backend example_com
    mode tcp
    server server1 192.168.1.10:443

backend api_example_com
    mode tcp
    server server2 192.168.1.11:443
```

---

## Testing SNI

### Check SNI Support

```bash
# Test with specific SNI
openssl s_client -connect 192.168.1.1:443 -servername example.com

# Test without SNI (should get default cert)
openssl s_client -connect 192.168.1.1:443 -noservername

# Test different SNI values
for domain in example.com api.example.com unknown.com; do
    echo "Testing SNI: $domain"
    openssl s_client -connect 192.168.1.1:443 -servername $domain 2>/dev/null | \
        openssl x509 -noout -subject
done
```

---

## Related Skills

- `cryptography-pki-fundamentals` - Certificate basics
- `cryptography-tls-configuration` - TLS setup
- `networking-load-balancing` - Load balancer configuration
- `proxies-reverse-proxy` - Reverse proxy patterns

---

**Last Updated**: 2025-10-27
