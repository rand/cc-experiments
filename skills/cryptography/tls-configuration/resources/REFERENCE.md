# TLS Configuration Reference

Comprehensive reference material for TLS/SSL configuration, cipher suites, RFCs, and security best practices.

---

## Table of Contents

1. [TLS Protocol Versions](#tls-protocol-versions)
2. [Cipher Suites](#cipher-suites)
3. [Certificate Chain Validation](#certificate-chain-validation)
4. [OCSP Stapling](#ocsp-stapling)
5. [Session Resumption](#session-resumption)
6. [Security Headers](#security-headers)
7. [RFC References](#rfc-references)
8. [Real-World Configurations](#real-world-configurations)

---

## TLS Protocol Versions

### TLS 1.2 (RFC 5246)

**Release**: August 2008
**Status**: Widely supported, still recommended
**Key Features**:
- 2-RTT handshake (two round trips)
- Flexible cipher suite negotiation
- Support for both RSA and (EC)DHE key exchange
- Optional session resumption (Session IDs, Session Tickets)
- Renegotiation support

**Handshake Flow** (2-RTT):
```
Client                                  Server

ClientHello        --------->
                                      ServerHello
                                     Certificate*
                               ServerKeyExchange*
                              CertificateRequest*
                   <---------      ServerHelloDone
Certificate*
ClientKeyExchange
CertificateVerify*
[ChangeCipherSpec]
Finished           --------->
                              [ChangeCipherSpec]
                   <---------             Finished
Application Data   <-------->     Application Data

* Optional or situation-dependent messages
```

**Cipher Suite Components**:
```
TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
│   │     │        │       │   └─ PRF: SHA256
│   │     │        │       └─ AEAD Mode: GCM
│   │     │        └─ Encryption: AES 128-bit
│   │     └─ Authentication: RSA
│   └─ Key Exchange: ECDHE (Elliptic Curve Diffie-Hellman Ephemeral)
└─ Protocol: TLS
```

**Security Considerations**:
- Must use strong cipher suites (see [Cipher Suites](#cipher-suites))
- Avoid RSA key exchange (no forward secrecy)
- Disable CBC mode ciphers (vulnerable to BEAST, Lucky13)
- Enable ECDHE for perfect forward secrecy
- Use AEAD ciphers (GCM, ChaCha20-Poly1305)

---

### TLS 1.3 (RFC 8446)

**Release**: August 2018
**Status**: Modern standard, recommended
**Key Features**:
- 1-RTT handshake (one round trip)
- 0-RTT mode for resumed connections (replay risk)
- Simplified cipher suites (only AEAD)
- Perfect forward secrecy mandatory
- No renegotiation
- Encrypted handshake messages
- Removed weak algorithms (RSA key exchange, CBC, SHA1, MD5)

**Handshake Flow** (1-RTT):
```
Client                                  Server

Key  ^ ClientHello
Exch | + key_share*
     | + signature_algorithms*
     | + psk_key_exchange_modes*
     v + pre_shared_key*       --------->
                                         ServerHello  ^ Key
                                        + key_share*  | Exch
                                   + pre_shared_key*  v
                             {EncryptedExtensions}  ^  Server
                             {CertificateRequest*}  v  Params
                                    {Certificate*}  ^
                              {CertificateVerify*}  | Auth
                                        {Finished}  v
                   <---------       [Application Data*]
     ^ {Certificate*}
Auth | {CertificateVerify*}
     v {Finished}              --------->
       [Application Data]      <-------->  [Application Data]

+  Indicates notable extensions
*  Indicates optional or situation-dependent
{} Indicates messages protected using keys derived from handshake traffic
[] Indicates messages protected using keys derived from application traffic
```

**Cipher Suites** (TLS 1.3 only - simplified):
```
TLS_AES_128_GCM_SHA256
TLS_AES_256_GCM_SHA384
TLS_CHACHA20_POLY1305_SHA256
TLS_AES_128_CCM_SHA256
TLS_AES_128_CCM_8_SHA256
```

**Key Differences from TLS 1.2**:
```
Feature                   TLS 1.2              TLS 1.3
─────────────────────────────────────────────────────────
Handshake RTT             2-RTT                1-RTT (0-RTT optional)
Forward Secrecy           Optional             Mandatory
Key Exchange              RSA, DH, ECDH        ECDHE, DHE only
Cipher Suites             100+ options         5 options (all AEAD)
CBC Mode                  Supported            Removed
Static RSA                Supported            Removed
Renegotiation             Supported            Removed
Server Cert Encrypted     No                   Yes
Handshake Encrypted       Partial              Mostly encrypted
Session Resumption        Session ID/Ticket    PSK only
```

**0-RTT Mode** (Zero Round Trip Time):
```
Client                                  Server

ClientHello
+ early_data
+ pre_shared_key
(Application Data)        --------->
                                         ServerHello
                                    + pre_shared_key
                             {EncryptedExtensions}
                                        {Finished}
                          <--------  [Application Data*]
(EndOfEarlyData)
{Finished}                --------->
[Application Data]        <-------->  [Application Data]
```

**0-RTT Security Warning**: Vulnerable to replay attacks. Only use for idempotent operations (GET requests, not POST/PUT/DELETE).

---

## Cipher Suites

### TLS 1.3 Cipher Suites

All TLS 1.3 cipher suites provide:
- AEAD encryption (authenticated encryption)
- Perfect forward secrecy (ECDHE or DHE)
- Modern algorithms only

**Recommended Order** (strongest first):
```
1. TLS_AES_256_GCM_SHA384         - AES-256, GCM mode, SHA-384
2. TLS_CHACHA20_POLY1305_SHA256   - ChaCha20, Poly1305, SHA-256
3. TLS_AES_128_GCM_SHA256         - AES-128, GCM mode, SHA-256
```

**Use Cases**:
- AES-GCM: Hardware-accelerated (AES-NI) on modern CPUs
- ChaCha20-Poly1305: Better for mobile devices without AES-NI

---

### TLS 1.2 Cipher Suites

**Recommended Cipher Suites** (Mozilla Modern configuration):
```
TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256      - ECDHE, RSA, AES-128-GCM, SHA-256
TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384      - ECDHE, RSA, AES-256-GCM, SHA-384
TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256 - ECDHE, RSA, ChaCha20-Poly1305
```

**OpenSSL Cipher String** (Modern):
```
ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305
```

**OpenSSL Cipher String** (Intermediate - wider compatibility):
```
ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384
```

---

### Cipher Suite Security Ratings

**STRONG** (Recommended):
- ✅ Forward secrecy (ECDHE, DHE)
- ✅ AEAD mode (GCM, ChaCha20-Poly1305)
- ✅ Strong encryption (AES-128+, ChaCha20)
- ✅ Modern hash (SHA-256+)

Examples:
```
TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256
TLS_AES_256_GCM_SHA384 (TLS 1.3)
```

**MEDIUM** (Acceptable for compatibility):
- ⚠️ May lack forward secrecy or AEAD
- ⚠️ CBC mode (vulnerable to timing attacks)

Examples:
```
TLS_RSA_WITH_AES_128_GCM_SHA256 (no forward secrecy)
TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256 (CBC mode)
```

**WEAK** (Never use):
- ❌ Broken encryption (DES, 3DES, RC4)
- ❌ Weak hash (MD5, SHA1)
- ❌ Export-grade crypto
- ❌ NULL cipher

Examples:
```
TLS_RSA_WITH_3DES_EDE_CBC_SHA (3DES - weak)
TLS_RSA_WITH_RC4_128_SHA (RC4 - broken)
TLS_RSA_WITH_NULL_SHA (NULL - no encryption!)
```

---

### Cipher Suite Breakdown

**Key Exchange Algorithms**:
```
Algorithm   Security         Notes
────────────────────────────────────────────────────────
ECDHE       ✅ STRONG        Elliptic Curve Diffie-Hellman Ephemeral
                            Perfect forward secrecy
                            Recommended

DHE         ✅ STRONG        Diffie-Hellman Ephemeral
                            Perfect forward secrecy
                            Slower than ECDHE

RSA         ❌ WEAK          Static RSA key exchange
                            No forward secrecy
                            Deprecated in TLS 1.3

ECDH        ❌ WEAK          Elliptic Curve Diffie-Hellman (static)
                            No forward secrecy
```

**Encryption Algorithms**:
```
Algorithm       Key Size   Security         Notes
────────────────────────────────────────────────────────
AES-256-GCM     256 bits   ✅ STRONG        AEAD, hardware accelerated
AES-128-GCM     128 bits   ✅ STRONG        AEAD, hardware accelerated
ChaCha20        256 bits   ✅ STRONG        AEAD, fast on mobile
AES-256-CBC     256 bits   ⚠️  MEDIUM       Vulnerable to timing attacks
AES-128-CBC     128 bits   ⚠️  MEDIUM       Vulnerable to timing attacks
3DES            168 bits   ❌ WEAK          Small block size, slow
RC4             128 bits   ❌ WEAK          Broken, never use
DES             56 bits    ❌ WEAK          Broken, never use
```

**Hash Functions**:
```
Algorithm   Security         Notes
────────────────────────────────────────────────────────
SHA-384     ✅ STRONG        384-bit hash
SHA-256     ✅ STRONG        256-bit hash
SHA-1       ❌ WEAK          Collision attacks found
MD5         ❌ WEAK          Completely broken
```

---

## Certificate Chain Validation

### Chain Structure

```
┌─────────────────────────────┐
│   Root CA Certificate       │  Self-signed, in trust store
│   (e.g., DigiCert Root)     │
└──────────────┬──────────────┘
               │ signs
               ▼
┌─────────────────────────────┐
│ Intermediate CA Certificate │  Signed by Root CA
│ (e.g., DigiCert SHA2)       │
└──────────────┬──────────────┘
               │ signs
               ▼
┌─────────────────────────────┐
│   Server Certificate        │  Signed by Intermediate CA
│   (e.g., example.com)       │  Presented to clients
└─────────────────────────────┘
```

### Chain Verification Process

**Client-side validation steps**:
1. Receive server certificate (leaf)
2. Verify certificate signature using issuer's public key
3. Check certificate validity period (notBefore, notAfter)
4. Verify hostname matches certificate CN or SAN
5. Walk up chain to intermediate CA
6. Verify intermediate certificate signature
7. Continue until reaching a trusted root CA
8. Check Certificate Revocation List (CRL) or OCSP

**OpenSSL Command** - Verify chain:
```bash
openssl s_client -connect example.com:443 -showcerts

# Extract chain
openssl s_client -connect example.com:443 -showcerts \
  | sed -n '/BEGIN CERTIFICATE/,/END CERTIFICATE/p' > chain.pem

# Verify against system trust store
openssl verify -CAfile /etc/ssl/certs/ca-bundle.crt chain.pem
```

### Server Configuration

**Nginx** - Include full chain:
```nginx
# CORRECT: Include intermediate + leaf
ssl_certificate /etc/ssl/certs/fullchain.pem;
ssl_certificate_key /etc/ssl/private/privkey.pem;

# Create fullchain manually if needed:
# cat cert.pem intermediate.pem > fullchain.pem
```

**Apache**:
```apache
SSLCertificateFile /etc/ssl/certs/example.com.crt
SSLCertificateKeyFile /etc/ssl/private/example.com.key
SSLCertificateChainFile /etc/ssl/certs/intermediate.crt
```

**Common Errors**:
```
❌ Error: "unable to get local issuer certificate"
   → Missing intermediate certificate in chain

❌ Error: "certificate has expired"
   → Certificate past notAfter date

❌ Error: "hostname mismatch"
   → Request hostname not in CN or SAN
```

---

## OCSP Stapling

**OCSP** (Online Certificate Status Protocol) - RFC 6960

### Why OCSP Stapling?

**Without OCSP stapling**:
- Client must query OCSP responder for each certificate in chain
- Privacy leak (OCSP responder knows which sites you visit)
- Performance overhead (additional network request)
- Single point of failure (if OCSP responder is down)

**With OCSP stapling**:
- Server pre-fetches OCSP response
- Server "staples" response to TLS handshake
- No client queries needed
- Better privacy and performance

### OCSP Response Flow

```
Without Stapling:
Client → Server: TLS handshake
Client ← Server: Certificate
Client → OCSP Responder: Is this cert valid?
Client ← OCSP Responder: Yes, valid
Client → Server: Application data

With Stapling:
Server → OCSP Responder: Is my cert valid? (every few hours)
Server ← OCSP Responder: Yes, valid (signed response)
Client → Server: TLS handshake
Client ← Server: Certificate + OCSP response (stapled)
Client → Server: Application data (no OCSP query needed!)
```

### Server Configuration

**Nginx**:
```nginx
server {
    listen 443 ssl;

    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/privkey.pem;

    # Enable OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;

    # CA certificates for OCSP response verification
    ssl_trusted_certificate /etc/ssl/certs/ca-chain.pem;

    # OCSP resolver
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
}
```

**Apache**:
```apache
<VirtualHost *:443>
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/example.com.crt
    SSLCertificateKeyFile /etc/ssl/private/example.com.key
    SSLCertificateChainFile /etc/ssl/certs/ca-chain.crt

    # Enable OCSP stapling
    SSLUseStapling on
    SSLStaplingCache "shmcb:logs/ssl_stapling(128000)"
    SSLStaplingResponderTimeout 5
    SSLStaplingReturnResponderErrors off
</VirtualHost>

# Global (outside VirtualHost)
SSLStaplingCache "shmcb:logs/ssl_stapling(128000)"
```

### Testing OCSP Stapling

```bash
# Check if OCSP stapling is working
openssl s_client -connect example.com:443 -status -tlsextdebug \
  | grep -A 17 'OCSP response'

# Expected output:
# OCSP Response Status: successful (0x0)
# OCSP Response Data:
#     Cert Status: good
#     This Update: Oct 27 12:00:00 2025 GMT
#     Next Update: Nov  3 12:00:00 2025 GMT
```

---

## Session Resumption

### Session IDs (TLS 1.2)

**Mechanism**: Server assigns session ID, stores session state

**Flow**:
```
Initial Connection:
Client → ClientHello (empty session ID)
Server → ServerHello (assigns session ID: abc123)
[Full handshake]
Client stores session ID

Resumed Connection:
Client → ClientHello (session ID: abc123)
Server → ServerHello (session ID: abc123)
[Abbreviated handshake - no certificate exchange]
```

**Nginx Configuration**:
```nginx
ssl_session_cache shared:SSL:10m;   # 10MB shared cache across workers
ssl_session_timeout 10m;            # Session valid for 10 minutes
```

**Pros**:
- Server controls session state
- Can revoke sessions

**Cons**:
- Server must store session state (memory overhead)
- Doesn't work well with load balancers (need shared cache)

---

### Session Tickets (RFC 5077)

**Mechanism**: Server encrypts session state, sends to client as "ticket"

**Flow**:
```
Initial Connection:
Client → ClientHello (empty session ticket)
Server → ServerHello
Server → NewSessionTicket (encrypted session state)
Client stores ticket

Resumed Connection:
Client → ClientHello (session ticket)
Server decrypts ticket, validates
Server → ServerHello
[Abbreviated handshake]
```

**Nginx Configuration**:
```nginx
# Enable session tickets
ssl_session_tickets on;

# Rotate ticket keys regularly for forward secrecy
ssl_session_ticket_key /etc/ssl/ticket_key_current.key;
ssl_session_ticket_key /etc/ssl/ticket_key_previous.key;

# Or disable for better privacy
ssl_session_tickets off;
```

**Pros**:
- Stateless (server doesn't store sessions)
- Works with load balancers

**Cons**:
- Privacy concern (long-lived tickets can track clients)
- Forward secrecy requires key rotation
- Server can't revoke tickets

**Recommendation**: Disable session tickets for privacy, use session cache instead.

---

### TLS 1.3 PSK Resumption

**Mechanism**: Pre-Shared Key (PSK) derived from previous session

**Flow**:
```
Initial Connection:
[Full 1-RTT handshake]
Server → NewSessionTicket (PSK)

Resumed Connection (1-RTT):
Client → ClientHello (+ PSK)
Server → ServerHello (+ PSK)
[Abbreviated handshake]

Resumed Connection (0-RTT):
Client → ClientHello (+ PSK) + Early Data
Server → ServerHello (+ PSK)
[Application data sent before handshake completes]
```

**Security**: TLS 1.3 PSK provides forward secrecy if PSK is rotated regularly.

---

## Security Headers

### HTTP Strict Transport Security (HSTS)

**RFC 6797**

Forces browsers to use HTTPS for a specified duration.

**Nginx**:
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

**Parameters**:
- `max-age=31536000` - Enforce HTTPS for 1 year (seconds)
- `includeSubDomains` - Apply to all subdomains
- `preload` - Submit to HSTS preload list (browser built-in)

**HSTS Preload**:
- Submit at https://hstspreload.org/
- Domain permanently enforces HTTPS (even on first visit)
- Cannot be easily reversed

**Testing**:
```bash
curl -I https://example.com | grep -i strict

# Expected:
# strict-transport-security: max-age=31536000; includeSubDomains; preload
```

---

### Content Security Policy (CSP)

Prevent XSS and data injection attacks.

**Nginx**:
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; object-src 'none'" always;
```

---

### X-Content-Type-Options

Prevent MIME sniffing.

**Nginx**:
```nginx
add_header X-Content-Type-Options "nosniff" always;
```

---

### X-Frame-Options

Prevent clickjacking.

**Nginx**:
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
```

---

## RFC References

### Core TLS RFCs

**RFC 5246** - The Transport Layer Security (TLS) Protocol Version 1.2
https://www.rfc-editor.org/rfc/rfc5246.html
Published: August 2008
Status: Proposed Standard

**RFC 8446** - The Transport Layer Security (TLS) Protocol Version 1.3
https://www.rfc-editor.org/rfc/rfc8446.html
Published: August 2018
Status: Proposed Standard

**RFC 6066** - Transport Layer Security (TLS) Extensions
https://www.rfc-editor.org/rfc/rfc6066.html
Defines: SNI (Server Name Indication), Maximum Fragment Length, etc.

**RFC 7540** - Hypertext Transfer Protocol Version 2 (HTTP/2)
https://www.rfc-editor.org/rfc/rfc7540.html
Requires TLS 1.2+, works best with TLS 1.3

---

### Certificate and PKI RFCs

**RFC 5280** - Internet X.509 Public Key Infrastructure Certificate and CRL Profile
https://www.rfc-editor.org/rfc/rfc5280.html
Defines certificate structure, validation, revocation

**RFC 6960** - X.509 Internet Public Key Infrastructure - OCSP (Online Certificate Status Protocol)
https://www.rfc-editor.org/rfc/rfc6960.html
Certificate revocation checking protocol

**RFC 6962** - Certificate Transparency
https://www.rfc-editor.org/rfc/rfc6962.html
Public log of certificates to detect mis-issuance

---

### Session Resumption RFCs

**RFC 5077** - Transport Layer Security (TLS) Session Resumption without Server-Side State
https://www.rfc-editor.org/rfc/rfc5077.html
Defines session tickets

**RFC 8446** - Section 4.6 - Post-Handshake Messages (TLS 1.3)
https://www.rfc-editor.org/rfc/rfc8446.html#section-4.6
Defines NewSessionTicket for TLS 1.3

---

### Security Headers RFCs

**RFC 6797** - HTTP Strict Transport Security (HSTS)
https://www.rfc-editor.org/rfc/rfc6797.html
Forces HTTPS connections

**RFC 7469** - Public Key Pinning Extension for HTTP (HPKP)
https://www.rfc-editor.org/rfc/rfc7469.html
**Deprecated** - Do not use (too risky, deprecated by browsers)

---

## Real-World Configurations

### Nginx - Modern Configuration (Mozilla Modern)

**Use case**: Modern browsers only (Chrome 63+, Firefox 57+)

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com;

    # Certificates
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/privkey.pem;

    # TLS versions
    ssl_protocols TLSv1.3 TLSv1.2;

    # Cipher suites (TLS 1.2)
    ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305';
    ssl_prefer_server_ciphers on;

    # TLS 1.3 ciphers (default is good, but explicit for clarity)
    ssl_conf_command Ciphersuites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/ssl/certs/ca-chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Session settings
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;  # Disable for privacy

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

---

### Apache - Modern Configuration

```apache
<VirtualHost *:443>
    ServerName example.com
    DocumentRoot /var/www/html

    SSLEngine on

    # Certificates
    SSLCertificateFile /etc/ssl/certs/example.com.crt
    SSLCertificateKeyFile /etc/ssl/private/example.com.key
    SSLCertificateChainFile /etc/ssl/certs/ca-chain.crt

    # TLS versions
    SSLProtocol -all +TLSv1.2 +TLSv1.3

    # Cipher suites
    SSLCipherSuite ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305
    SSLHonorCipherOrder on

    # OCSP stapling
    SSLUseStapling on
    SSLStaplingCache "shmcb:logs/ssl_stapling(32768)"

    # Security headers
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "SAMEORIGIN"
</VirtualHost>

# Global OCSP stapling cache
SSLStaplingCache "shmcb:logs/ssl_stapling(32768)"
```

---

### Node.js - Modern Configuration

```javascript
const https = require('https');
const fs = require('fs');

const options = {
    key: fs.readFileSync('/etc/ssl/private/privkey.pem'),
    cert: fs.readFileSync('/etc/ssl/certs/fullchain.pem'),

    // TLS versions
    minVersion: 'TLSv1.2',
    maxVersion: 'TLSv1.3',

    // Cipher suites (TLS 1.2)
    ciphers: [
        'ECDHE-RSA-AES128-GCM-SHA256',
        'ECDHE-RSA-AES256-GCM-SHA384',
        'ECDHE-RSA-CHACHA20-POLY1305',
        'TLS_AES_128_GCM_SHA256',
        'TLS_AES_256_GCM_SHA384',
        'TLS_CHACHA20_POLY1305_SHA256'
    ].join(':'),

    honorCipherOrder: true,
    sessionTimeout: 300
};

const server = https.createServer(options, (req, res) => {
    // Set security headers
    res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('X-Frame-Options', 'SAMEORIGIN');

    res.writeHead(200);
    res.end('Secure connection\n');
});

server.listen(443, () => {
    console.log('HTTPS server running on port 443');
});
```

---

### Python - Modern Configuration

```python
import ssl
import http.server
import socketserver

# Create SSL context
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

# Load certificates
context.load_cert_chain('/etc/ssl/certs/fullchain.pem', '/etc/ssl/private/privkey.pem')

# TLS versions
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.maximum_version = ssl.TLSVersion.TLSv1_3

# Cipher suites
context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20')

# Security options
context.options |= ssl.OP_NO_SSLv2
context.options |= ssl.OP_NO_SSLv3
context.options |= ssl.OP_NO_TLSv1
context.options |= ssl.OP_NO_TLSv1_1
context.options |= ssl.OP_NO_COMPRESSION

# Start HTTPS server
PORT = 443
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    print(f"HTTPS server running on port {PORT}")
    httpd.serve_forever()
```

---

**Last Updated**: 2025-10-27
**Version**: 1.0.0
