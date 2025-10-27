---
name: cryptography-pki-fundamentals
description: PKI fundamentals including certificate authorities, chains of trust, X.509 certificates, and certificate lifecycle
---

# PKI Fundamentals

**Scope**: Public Key Infrastructure, certificate authorities, trust chains, X.509 certificates
**Lines**: ~290
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Understanding certificate authorities and trust
- Implementing TLS/SSL
- Managing certificates
- Building secure authentication systems
- Troubleshooting certificate errors
- Understanding mTLS
- Working with code signing
- Implementing certificate-based authentication

## Core Concepts

### Certificate Authority (CA)

**Trust Hierarchy**:
```
Root CA (self-signed, in trust store)
    ↓
Intermediate CA (signed by Root)
    ↓
End Entity Certificate (signed by Intermediate)
    → Used by servers, clients, code signing
```

**Certificate Chain**:
```
example.com certificate
├─ Issued by: Intermediate CA
│  └─ Issued by: Root CA
│     └─ Self-signed (trusted)
```

### X.509 Certificates

**Structure**:
```
Certificate:
    Version: 3
    Serial Number: 1234567890abcdef
    Signature Algorithm: SHA256-RSA
    Issuer: CN=Intermediate CA, O=Trust Corp
    Validity:
        Not Before: 2025-01-01 00:00:00
        Not After:  2026-01-01 00:00:00
    Subject: CN=example.com, O=Example Inc
    Subject Public Key Info:
        Algorithm: RSA 2048-bit
        Public Key: (2048-bit modulus)
    Extensions:
        Subject Alternative Name: example.com, www.example.com
        Key Usage: Digital Signature, Key Encipherment
        Extended Key Usage: Server Authentication
```

**View Certificate**:
```bash
# View certificate details
openssl x509 -in cert.pem -text -noout

# Check expiration
openssl x509 -in cert.pem -enddate -noout

# Verify chain
openssl verify -CAfile chain.pem cert.pem
```

### Creating Certificates

**Self-Signed Certificate** (for testing):
```bash
# Generate private key
openssl genrsa -out private-key.pem 2048

# Create self-signed certificate
openssl req -new -x509 -key private-key.pem -out cert.pem -days 365 \
  -subj "/CN=test.example.com/O=Test Org"
```

**Certificate Signing Request (CSR)**:
```bash
# Generate private key
openssl genrsa -out private-key.pem 2048

# Create CSR
openssl req -new -key private-key.pem -out request.csr \
  -subj "/CN=example.com/O=Example Inc/C=US"

# Send CSR to CA for signing
# CA returns signed certificate
```

**Certificate Authority Setup**:
```bash
# Create CA private key
openssl genrsa -out ca-key.pem 4096

# Create CA certificate (self-signed)
openssl req -new -x509 -days 3650 -key ca-key.pem -out ca-cert.pem \
  -subj "/CN=My CA/O=Trust Corp"

# Sign a certificate request
openssl x509 -req -in request.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out signed-cert.pem -days 365
```

---

## Patterns

### Pattern 1: Certificate Validation

**Python Example**:
```python
import ssl
import socket
from datetime import datetime

def validate_certificate(hostname, port=443):
    context = ssl.create_default_context()

    with socket.create_connection((hostname, port)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()

            # Check subject
            subject = dict(x[0] for x in cert['subject'])
            print(f"Subject: {subject['commonName']}")

            # Check validity
            not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
            days_remaining = (not_after - datetime.now()).days
            print(f"Valid for: {days_remaining} days")

            # Check SANs
            san = cert.get('subjectAltName', [])
            print(f"SANs: {[name for typ, name in san if typ == 'DNS']}")

validate_certificate('example.com')
```

### Pattern 2: Certificate Pinning

**Go Example**:
```go
package main

import (
    "crypto/sha256"
    "crypto/tls"
    "crypto/x509"
    "encoding/hex"
    "fmt"
    "net/http"
)

func verifyPinnedCert(rawCerts [][]byte, verifiedChains [][]*x509.Certificate) error {
    // Expected certificate fingerprint (SHA256)
    expected := "1234567890abcdef..."

    for _, rawCert := range rawCerts {
        hash := sha256.Sum256(rawCert)
        fingerprint := hex.EncodeToString(hash[:])

        if fingerprint == expected {
            return nil
        }
    }

    return fmt.Errorf("certificate pinning failed")
}

func main() {
    client := &http.Client{
        Transport: &http.Transport{
            TLSClientConfig: &tls.Config{
                VerifyPeerCertificate: verifyPinnedCert,
            },
        },
    }

    resp, err := client.Get("https://example.com")
    if err != nil {
        panic(err)
    }
    defer resp.Body.Close()
}
```

---

## Certificate Lifecycle

### Issuance

```
1. Generate private key
2. Create CSR
3. Submit CSR to CA
4. CA validates domain ownership
5. CA signs certificate
6. Deploy certificate
```

### Renewal

```bash
# Check expiration (90 days before expiry)
if [ $(openssl x509 -enddate -noout -in cert.pem | \
      cut -d= -f2 | date -f- +%s) -lt $(date -d "+90 days" +%s) ]; then
    echo "Certificate needs renewal"
    # Renew via ACME (Let's Encrypt), CA API, or manual process
fi
```

### Revocation

**Certificate Revocation List (CRL)**:
```bash
# Check CRL
openssl crl -in crl.pem -text -noout
```

**OCSP (Online Certificate Status Protocol)**:
```bash
# Check certificate status via OCSP
openssl ocsp -issuer ca-cert.pem -cert cert.pem \
  -url http://ocsp.example.com -CAfile ca-cert.pem
```

---

## Best Practices

### 1. Use Strong Keys

```bash
# ❌ Bad: Weak 1024-bit RSA
openssl genrsa -out key.pem 1024

# ✅ Good: Strong 2048-bit RSA or better
openssl genrsa -out key.pem 2048

# ✅ Better: ECC (faster, smaller, equally secure)
openssl ecparam -genkey -name prime256v1 -out key.pem
```

### 2. Proper Certificate Storage

```python
# ❌ Bad: Certificate in code
cert = """-----BEGIN CERTIFICATE-----
MIIBkTCB+wIJAKHHCgK...
-----END CERTIFICATE-----"""

# ✅ Good: Certificate from secure storage
with open('/etc/ssl/certs/cert.pem') as f:
    cert = f.read()
```

### 3. Validate Certificate Chain

```go
// ✅ Good: Verify full chain
roots := x509.NewCertPool()
roots.AppendCertsFromPEM(rootCA)

opts := x509.VerifyOptions{
    Roots:     roots,
    DNSName:   "example.com",
}

_, err := cert.Verify(opts)
if err != nil {
    log.Fatal("Certificate verification failed:", err)
}
```

---

## Troubleshooting

### Issue 1: Certificate Expired

**Check expiration**:
```bash
openssl x509 -in cert.pem -noout -dates
```

**Solution**: Renew certificate

### Issue 2: Untrusted Certificate

**Check chain**:
```bash
openssl s_client -connect example.com:443 -showcerts
```

**Solution**: Install intermediate certificates

### Issue 3: Hostname Mismatch

**Symptoms**: Certificate CN doesn't match hostname

**Solution**: Check Subject Alternative Names (SANs)

---

## Related Skills

- `cryptography-tls-configuration` - TLS/SSL setup
- `cryptography-certificate-management` - Certificate operations
- `networking-mtls-implementation` - Mutual TLS
- `cryptography-crypto-best-practices` - Security practices

---

**Last Updated**: 2025-10-27
