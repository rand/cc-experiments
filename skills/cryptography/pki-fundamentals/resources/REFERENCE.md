# PKI Infrastructure - Comprehensive Technical Reference

**Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: ~3,800

This comprehensive reference covers all aspects of Public Key Infrastructure (PKI) operations, from CA hierarchy setup to certificate management, revocation, compliance, and production deployment patterns.

---

## Table of Contents

1. [PKI Fundamentals](#1-pki-fundamentals)
2. [Certificate Authorities](#2-certificate-authorities)
3. [X.509 Certificate Standards](#3-x509-certificate-standards)
4. [CA Operations](#4-ca-operations)
5. [Certificate Lifecycle](#5-certificate-lifecycle)
6. [Certificate Revocation](#6-certificate-revocation)
7. [Certificate Transparency](#7-certificate-transparency)
8. [Private vs Public CAs](#8-private-vs-public-cas)
9. [HSM Integration](#9-hsm-integration)
10. [Cross-Certification](#10-cross-certification)
11. [Compliance and Standards](#11-compliance-and-standards)
12. [Tools and Software](#12-tools-and-software)
13. [Production Patterns](#13-production-patterns)
14. [Security Best Practices](#14-security-best-practices)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. PKI Fundamentals

### What is PKI?

**Public Key Infrastructure (PKI)** is a framework for managing digital certificates and public-key encryption.

**Core Components**:
```
┌─────────────────────────────────────────────────────────────┐
│                         PKI System                           │
├─────────────────────────────────────────────────────────────┤
│ Certificate Authority (CA)    - Issues certificates          │
│ Registration Authority (RA)   - Verifies identities          │
│ Certificate Repository        - Stores certificates          │
│ Certificate Revocation Lists  - Lists revoked certificates   │
│ OCSP Responder               - Online status checking        │
│ Key Management System        - Protects private keys         │
└─────────────────────────────────────────────────────────────┘
```

### Trust Models

**Hierarchical Trust** (Most Common):
```
                    ┌──────────────┐
                    │   Root CA    │ (Offline, air-gapped)
                    │  Self-signed │
                    └──────┬───────┘
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
    ┌──────────────┐              ┌──────────────┐
    │Intermediate 1│              │Intermediate 2│ (Online)
    └──────┬───────┘              └──────┬───────┘
           │                             │
      ┌────┴────┐                   ┌────┴────┐
      ▼         ▼                   ▼         ▼
  [Server]  [Client]            [Server]  [Client]
```

**Web of Trust** (PGP/GPG):
```
    Alice ←→ Bob ←→ Carol
      ↕              ↕
    Dave          Eve
```

**Bridge CA** (Cross-organization):
```
    Org A CA ←→ Bridge CA ←→ Org B CA
```

### Certificate Chain Validation

**Validation Steps**:
1. **Signature verification**: Each certificate signed by issuer?
2. **Chain construction**: Valid path from end-entity to trusted root?
3. **Expiration check**: All certificates in chain valid?
4. **Revocation check**: No certificates revoked (CRL/OCSP)?
5. **Name constraints**: Certificates issued for valid names?
6. **Policy constraints**: Policies satisfied?

**Chain Example**:
```
End-Entity Certificate (example.com)
├─ Issued by: R3 (Let's Encrypt Intermediate)
│  ├─ Valid: 2025-01-01 to 2025-04-01
│  └─ Signed by: ISRG Root X1
│     ├─ Valid: 2015-06-04 to 2035-06-04
│     └─ Self-signed (in trust store)
```

---

## 2. Certificate Authorities

### CA Hierarchy Design

**Root CA** (Tier 0):
- **Purpose**: Top of trust hierarchy
- **Usage**: Sign intermediate CAs only
- **Lifetime**: 20-30 years
- **Storage**: Offline, air-gapped, HSM
- **Access**: Physical security, dual control
- **Key Ceremony**: Multiple witnesses, video recording

**Intermediate CA** (Tier 1):
- **Purpose**: Operational certificate issuance
- **Usage**: Sign end-entity certificates or sub-intermediates
- **Lifetime**: 5-10 years
- **Storage**: Online, HSM-protected
- **Access**: Automated systems with audit logging

**Issuing CA** (Tier 2):
- **Purpose**: Specific certificate types (TLS, email, code signing)
- **Usage**: Sign end-entity certificates
- **Lifetime**: 3-5 years
- **Storage**: Online, HSM or software-protected

### Root CA Operations

**Key Ceremony**:
```
Prerequisites:
- Secure facility (air-gapped, physically secure)
- Multiple trustees (3-7 people)
- HSM devices (FIPS 140-2 Level 3+)
- Audit procedures (video, witnesses, notary)

Steps:
1. Initialize HSM (factory reset)
2. Generate M-of-N key sharing scheme
3. Generate root key pair in HSM
4. Create self-signed root certificate
5. Export root certificate (not key!)
6. Back up key shares to secure locations
7. Document all operations
8. Store HSM offline

All operations witnessed and recorded
```

**Root CA Certificate Creation**:
```bash
# Generate root CA private key (4096-bit RSA)
openssl genrsa -aes256 -out root-ca-key.pem 4096

# Create root CA certificate (30-year validity)
openssl req -x509 -new -nodes \
    -key root-ca-key.pem \
    -sha384 \
    -days 10950 \
    -out root-ca-cert.pem \
    -config root-ca.conf \
    -extensions v3_ca

# Root CA config (root-ca.conf)
cat > root-ca.conf <<EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_ca

[req_distinguished_name]
countryName = US
organizationName = Example Corp
commonName = Example Root CA

[v3_ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer:always
EOF
```

### Intermediate CA Operations

**Intermediate CA Creation**:
```bash
# Generate intermediate CA key
openssl genrsa -aes256 -out intermediate-ca-key.pem 2048

# Create CSR for intermediate
openssl req -new \
    -key intermediate-ca-key.pem \
    -out intermediate-ca.csr \
    -config intermediate-ca.conf

# Sign with root CA (pathlen:0 means no sub-intermediates)
openssl x509 -req \
    -in intermediate-ca.csr \
    -CA root-ca-cert.pem \
    -CAkey root-ca-key.pem \
    -CAcreateserial \
    -out intermediate-ca-cert.pem \
    -days 3650 \
    -sha384 \
    -extfile intermediate-ca.conf \
    -extensions v3_intermediate_ca

# Intermediate CA config
cat > intermediate-ca.conf <<EOF
[req]
distinguished_name = req_distinguished_name

[req_distinguished_name]
countryName = US
organizationName = Example Corp
commonName = Example Intermediate CA

[v3_intermediate_ca]
basicConstraints = critical,CA:TRUE,pathlen:0
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer:always
crlDistributionPoints = URI:http://crl.example.com/root.crl
authorityInfoAccess = OCSP;URI:http://ocsp.example.com
certificatePolicies = 2.23.140.1.2.1
EOF
```

**Create Certificate Chain**:
```bash
# Combine intermediate and root for full chain
cat intermediate-ca-cert.pem root-ca-cert.pem > ca-chain.pem

# Verify chain
openssl verify -CAfile root-ca-cert.pem intermediate-ca-cert.pem
```

---

## 3. X.509 Certificate Standards

### Certificate Structure

**X.509 v3 Format**:
```
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: 4096 (0x1000)
        Signature Algorithm: sha256WithRSAEncryption

        Issuer: C=US, O=Example Corp, CN=Example Intermediate CA

        Validity:
            Not Before: Jan  1 00:00:00 2025 GMT
            Not After : Apr  1 23:59:59 2025 GMT

        Subject: C=US, ST=California, L=San Francisco,
                 O=Example Inc, CN=www.example.com

        Subject Public Key Info:
            Public Key Algorithm: rsaEncryption
                RSA Public-Key: (2048 bit)
                Modulus: ...
                Exponent: 65537 (0x10001)

        X509v3 Extensions:
            X509v3 Basic Constraints: critical
                CA:FALSE
            X509v3 Key Usage: critical
                Digital Signature, Key Encipherment
            X509v3 Extended Key Usage:
                TLS Web Server Authentication
            X509v3 Subject Alternative Name:
                DNS:www.example.com, DNS:example.com
            X509v3 Subject Key Identifier:
                AB:CD:EF:...
            X509v3 Authority Key Identifier:
                keyid:12:34:56:...
            Authority Information Access:
                OCSP - URI:http://ocsp.example.com
                CA Issuers - URI:http://ca.example.com/intermediate.crt
            X509v3 CRL Distribution Points:
                Full Name:
                  URI:http://crl.example.com/intermediate.crl
            X509v3 Certificate Policies:
                Policy: 2.23.140.1.2.1 (DV)
                  CPS: https://example.com/cps

    Signature Algorithm: sha256WithRSAEncryption
         Signature: ...
```

### Certificate Fields

**Subject and Issuer DN** (Distinguished Name):
```
C   = Country (2-letter ISO code)
ST  = State/Province
L   = Locality/City
O   = Organization
OU  = Organizational Unit (deprecated in DV certs)
CN  = Common Name (domain or user)
```

**Serial Number**:
- Unique identifier within CA
- Minimum 64-bit random
- Used for revocation

**Validity Period**:
```
Not Before: Certificate valid from (inclusive)
Not After:  Certificate valid until (inclusive)

Common lifetimes:
- Root CA: 20-30 years
- Intermediate CA: 5-10 years
- TLS Server: 90 days (Let's Encrypt), 1 year (commercial)
- Code Signing: 1-3 years
- Email (S/MIME): 1-2 years
```

### X.509 Extensions

**Basic Constraints** (critical):
```
CA:TRUE                  - Certificate is a CA
CA:TRUE, pathlen:0       - CA cannot issue sub-CAs
CA:FALSE                 - End-entity certificate
```

**Key Usage** (critical):
```
Digital Signature        - Sign data (TLS, S/MIME)
Key Encipherment         - Encrypt keys (RSA TLS)
Key Agreement            - Derive keys (ECDH TLS)
Certificate Sign         - Issue certificates (CA only)
CRL Sign                 - Sign CRLs (CA only)
Non Repudiation         - Sign documents
```

**Extended Key Usage** (not critical):
```
TLS Web Server Authentication   - id-kp-serverAuth (1.3.6.1.5.5.7.3.1)
TLS Web Client Authentication   - id-kp-clientAuth (1.3.6.1.5.5.7.3.2)
Code Signing                    - id-kp-codeSigning (1.3.6.1.5.5.7.3.3)
Email Protection                - id-kp-emailProtection (1.3.6.1.5.5.7.3.4)
Time Stamping                   - id-kp-timeStamping (1.3.6.1.5.5.7.3.8)
OCSP Signing                    - id-kp-OCSPSigning (1.3.6.1.5.5.7.3.9)
```

**Subject Alternative Names (SAN)**:
```
DNS:example.com
DNS:*.example.com           (wildcard)
DNS:mail.example.com
IP:192.0.2.1
URI:https://example.com
email:admin@example.com
```

**Authority Information Access (AIA)**:
```
OCSP - URI:http://ocsp.example.com
CA Issuers - URI:http://ca.example.com/intermediate.crt
```

**CRL Distribution Points**:
```
URI:http://crl.example.com/intermediate.crl
URI:ldap://ldap.example.com/cn=Intermediate%20CA,ou=PKI,o=Example
```

**Certificate Policies**:
```
2.23.140.1.2.1  - CA/Browser Forum Domain Validated (DV)
2.23.140.1.2.2  - CA/Browser Forum Organization Validated (OV)
2.23.140.1.2.3  - CA/Browser Forum Individual Validated (IV)
2.23.140.1.1    - CA/Browser Forum Extended Validation (EV)
```

**Name Constraints** (CA certificates):
```
Permitted:
  DNS:.example.com
  DNS:.example.org
  IP:192.0.2.0/24

Excluded:
  DNS:.internal.example.com
```

---

## 4. CA Operations

### Certificate Issuance Workflow

**Step 1: CSR Generation**:
```bash
# Generate private key
openssl genrsa -out server-key.pem 2048

# Generate CSR with SANs
openssl req -new \
    -key server-key.pem \
    -out server.csr \
    -config server.conf

# Server config
cat > server.conf <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = req_ext

[req_distinguished_name]
CN = www.example.com
O = Example Inc
C = US

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = www.example.com
DNS.2 = example.com
DNS.3 = api.example.com
EOF
```

**Step 2: CSR Validation**:
```bash
# Verify CSR signature
openssl req -in server.csr -verify -noout

# View CSR contents
openssl req -in server.csr -text -noout

# Extract public key
openssl req -in server.csr -pubkey -noout

# Verify key match
openssl req -in server.csr -noout -modulus | openssl md5
openssl rsa -in server-key.pem -noout -modulus | openssl md5
# (hashes must match)
```

**Step 3: Domain Validation** (DV):
```
HTTP-01 Challenge:
1. Place token at http://example.com/.well-known/acme-challenge/TOKEN
2. CA fetches and validates

DNS-01 Challenge:
1. Add TXT record: _acme-challenge.example.com = TOKEN
2. CA queries DNS and validates

TLS-ALPN-01 Challenge:
1. Serve TLS certificate with acme-validation extension
2. CA connects on port 443 and validates
```

**Step 4: Certificate Signing**:
```bash
# Sign CSR with intermediate CA
openssl x509 -req \
    -in server.csr \
    -CA intermediate-ca-cert.pem \
    -CAkey intermediate-ca-key.pem \
    -CAcreateserial \
    -out server-cert.pem \
    -days 90 \
    -sha256 \
    -extfile server-ext.conf

# Server extensions
cat > server-ext.conf <<EOF
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer:always
subjectAltName = DNS:www.example.com,DNS:example.com
authorityInfoAccess = OCSP;URI:http://ocsp.example.com
crlDistributionPoints = URI:http://crl.example.com/intermediate.crl
certificatePolicies = 2.23.140.1.2.1
EOF
```

**Step 5: Certificate Delivery**:
```bash
# Create certificate bundle
cat server-cert.pem intermediate-ca-cert.pem > server-fullchain.pem

# Verify certificate
openssl x509 -in server-cert.pem -text -noout
openssl verify -CAfile ca-chain.pem server-cert.pem
```

### Certificate Renewal

**Manual Renewal**:
```bash
# Generate new CSR (reuse key or generate new)
openssl req -new -key server-key.pem -out server-renewal.csr -config server.conf

# Sign new certificate
openssl x509 -req -in server-renewal.csr \
    -CA intermediate-ca-cert.pem -CAkey intermediate-ca-key.pem \
    -out server-cert-new.pem -days 90 -sha256 -extfile server-ext.conf

# Deploy new certificate (overlap period)
# Keep old certificate active during transition
```

**Automated Renewal (ACME)**:
```bash
# Certbot automatic renewal
certbot renew --dry-run

# acme.sh automatic renewal
acme.sh --cron

# cert-manager automatic renewal (Kubernetes)
kubectl get certificates -A
```

### Key Ceremony

**Root CA Key Ceremony**:
```
Participants:
- CA Administrator (ceremony leader)
- Key Custodians (3-7 people)
- Auditor (witness)
- Legal Counsel
- Security Officer

Equipment:
- HSM (FIPS 140-2 Level 3+)
- Secure facility (air-gapped)
- Video recording equipment
- Secure key backup media

Procedure:
1. Pre-ceremony verification
   - Verify participants' identities
   - Confirm all equipment present
   - Start video recording
   - Read ceremony script

2. HSM initialization
   - Factory reset HSM
   - Initialize M-of-N key shares (e.g., 3-of-5)
   - Each custodian enters their secret
   - Generate root key pair

3. Root certificate creation
   - Generate self-signed certificate
   - Verify certificate parameters
   - Export root certificate (public key only)
   - Print certificate fingerprint

4. Key backup
   - Backup key shares to secure media
   - Distribute shares to custodians
   - Store in separate secure locations
   - Document serial numbers

5. Post-ceremony
   - Store HSM offline
   - Sign ceremony documentation
   - Archive video recording
   - Publish root certificate

All steps logged and witnessed
```

---

## 5. Certificate Lifecycle

### Lifecycle Stages

```
┌─────────────┐
│  Pending    │ ← CSR created, awaiting validation
└──────┬──────┘
       ▼
┌─────────────┐
│   Issued    │ ← Certificate signed and active
└──────┬──────┘
       │
       ├─→ ┌─────────────┐
       │   │   Renewed   │ ← New certificate issued before expiry
       │   └─────────────┘
       │
       ├─→ ┌─────────────┐
       │   │   Expired   │ ← Certificate past validity period
       │   └─────────────┘
       │
       └─→ ┌─────────────┐
           │   Revoked   │ ← Certificate invalidated before expiry
           └─────────────┘
```

### Certificate Renewal Strategies

**Strategy 1: Renew and Replace**:
```
Timeline:
Day 0:    New certificate issued
Day 0-1:  Overlap period (both certs valid)
Day 1:    Old certificate deactivated
Day 90:   New certificate expires

Pros: Clean cutover, simple
Cons: Downtime risk if not coordinated
```

**Strategy 2: Continuous Renewal**:
```
Timeline:
Day 0:    Cert A issued (90 days)
Day 60:   Cert B issued (overlap with A)
Day 90:   Cert A expires, Cert B active
Day 120:  Cert C issued (overlap with B)
...

Pros: No expiration gaps, always has backup
Cons: More complex, requires automation
```

### Certificate Storage

**Private Key Protection**:
```bash
# Encrypt private key
openssl genrsa -aes256 -out encrypted-key.pem 2048

# Decrypt for use
openssl rsa -in encrypted-key.pem -out decrypted-key.pem

# Store with restricted permissions
chmod 600 decrypted-key.pem
chown root:root decrypted-key.pem
```

**Certificate Repository**:
```
Filesystem:
/etc/pki/
├── CA/
│   ├── certs/         # Issued certificates
│   ├── crl/           # Certificate Revocation Lists
│   ├── newcerts/      # New certificates by serial number
│   └── private/       # Private keys (restricted)
├── issued/
│   ├── server/        # Server certificates
│   ├── client/        # Client certificates
│   └── email/         # Email certificates
└── trust/
    └── ca-bundle.crt  # Trusted CA certificates

Database:
- Certificate serial number (unique)
- Subject DN
- Issuer DN
- Validity period
- Status (valid, expired, revoked)
- Revocation date/reason
- PEM-encoded certificate
```

---

## 6. Certificate Revocation

### Why Revoke Certificates?

**Reasons for Revocation**:
- Private key compromised
- CA key compromised (revoke entire chain)
- Certificate holder identity changed
- Certificate superseded (renewal)
- Cessation of operation
- Certificate hold (temporary suspension)

**Revocation Reasons (RFC 5280)**:
```
0 - unspecified
1 - keyCompromise
2 - cACompromise
3 - affiliationChanged
4 - superseded
5 - cessationOfOperation
6 - certificateHold (reversible)
8 - removeFromCRL (un-hold)
9 - privilegeWithdrawn
10 - aACompromise
```

### Certificate Revocation Lists (CRLs)

**CRL Structure**:
```
Certificate Revocation List (CRL):
    Version: 2 (0x1)
    Signature Algorithm: sha256WithRSAEncryption
    Issuer: CN=Intermediate CA, O=Example Corp
    Last Update: Jan 1 00:00:00 2025 GMT
    Next Update: Jan 8 00:00:00 2025 GMT
    CRL Extensions:
        X509v3 Authority Key Identifier:
            keyid:12:34:56:...
        X509v3 CRL Number:
            42
    Revoked Certificates:
        Serial Number: 1001
            Revocation Date: Dec 25 12:00:00 2024 GMT
            Reason Code: keyCompromise
        Serial Number: 1002
            Revocation Date: Dec 28 15:30:00 2024 GMT
            Reason Code: superseded
    Signature: ...
```

**Generate CRL**:
```bash
# OpenSSL CA database (index.txt)
cat index.txt
V 250401000000Z 1000 unknown /CN=www.example.com/O=Example Inc
R 250401000000Z 241225120000Z,keyCompromise 1001 unknown /CN=api.example.com

# Generate CRL
openssl ca -config ca.conf -gencrl -out intermediate.crl

# View CRL
openssl crl -in intermediate.crl -text -noout

# Verify CRL signature
openssl crl -in intermediate.crl -CAfile intermediate-ca-cert.pem -noout
```

**CRL Distribution**:
```bash
# HTTP distribution
http://crl.example.com/intermediate.crl

# LDAP distribution
ldap://ldap.example.com/cn=Intermediate%20CA,ou=PKI,o=Example

# In certificate (CRL Distribution Points extension)
X509v3 CRL Distribution Points:
    Full Name:
      URI:http://crl.example.com/intermediate.crl
```

**CRL Types**:

**Full CRL**: Complete list of all revoked certificates
**Delta CRL**: Only changes since last full CRL
```bash
# Generate delta CRL
openssl ca -config ca.conf -gencrl -crldays 1 -out delta.crl

# Delta CRL references base CRL number
X509v3 Delta CRL Indicator: critical
    42
```

### OCSP (Online Certificate Status Protocol)

**OCSP Request/Response**:
```
Client → OCSP Responder:
  Request: Is certificate serial 1000 valid?

OCSP Responder → Client:
  Response:
    Status: good | revoked | unknown
    This Update: 2025-01-01 12:00:00
    Next Update: 2025-01-01 18:00:00
    Signature: (signed by OCSP Responder)
```

**OCSP Responder Setup**:
```bash
# Generate OCSP signing certificate
openssl req -new -newkey rsa:2048 -keyout ocsp-key.pem -out ocsp.csr
openssl x509 -req -in ocsp.csr -CA intermediate-ca-cert.pem \
    -CAkey intermediate-ca-key.pem -out ocsp-cert.pem \
    -days 365 -sha256 -extfile ocsp-ext.conf

cat > ocsp-ext.conf <<EOF
basicConstraints = CA:FALSE
keyUsage = critical,digitalSignature
extendedKeyUsage = critical,OCSPSigning
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer:always
EOF

# Start OCSP responder
openssl ocsp -port 8080 \
    -index index.txt \
    -CA intermediate-ca-cert.pem \
    -rkey ocsp-key.pem \
    -rsigner ocsp-cert.pem \
    -text
```

**OCSP Query**:
```bash
# Check certificate status
openssl ocsp \
    -issuer intermediate-ca-cert.pem \
    -cert server-cert.pem \
    -url http://ocsp.example.com \
    -CAfile ca-chain.pem

# Response
Response:
    Response Status: successful (0x0)
    Response Type: Basic OCSP Response
    Version: 1 (0x0)
    Responder Id: ...
    Produced At: Jan  1 12:00:00 2025 GMT
    Responses:
    Certificate ID:
      Hash Algorithm: sha256
      Issuer Name Hash: ...
      Issuer Key Hash: ...
      Serial Number: 1000
    Cert Status: good
    This Update: Jan  1 12:00:00 2025 GMT
    Next Update: Jan  1 18:00:00 2025 GMT
```

### OCSP Stapling

**How OCSP Stapling Works**:
```
Traditional OCSP:
Client ←→ Server (certificate)
Client ←→ OCSP Responder (check status) ← Privacy leak!

OCSP Stapling:
Server ←→ OCSP Responder (get signed response)
Client ←→ Server (certificate + OCSP response)
        ↑
Client verifies OCSP response signature
No contact with OCSP Responder needed!
```

**Nginx OCSP Stapling**:
```nginx
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate /etc/ssl/certs/example.com-fullchain.pem;
    ssl_certificate_key /etc/ssl/private/example.com-key.pem;

    # Enable OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/ssl/certs/ca-chain.pem;

    # OCSP stapling cache
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
}
```

**Verify OCSP Stapling**:
```bash
# Check if OCSP stapling is working
echo | openssl s_client -connect example.com:443 -status
# Look for: OCSP Response Status: successful
```

### OCSP Must-Staple

**Must-Staple Extension**:
```
X509v3 TLS Feature:
    status_request (5)
```

**Enforce OCSP Stapling**:
```bash
# Generate certificate with must-staple
openssl req -new -key server-key.pem -out server.csr -reqexts must_staple

cat >> openssl.cnf <<EOF
[must_staple]
tlsfeature = status_request
EOF
```

**Benefits**:
- Prevents revocation checking bypass
- Forces server to provide OCSP response
- Improves privacy (no client → OCSP connection)

---

## 7. Certificate Transparency

### What is Certificate Transparency?

**Problem**: Rogue CAs issuing unauthorized certificates

**Solution**: Public append-only logs of all issued certificates

**CT Components**:
```
Certificate Authority
     ↓ (submits)
CT Log Server (append-only Merkle tree)
     ↓ (monitors)
CT Monitor (detects unauthorized certificates)
     ↓ (alerts)
Domain Owner
```

### CT Log Structure

**Merkle Tree**:
```
                     Root Hash
                    /         \
                Hash 1         Hash 2
               /      \       /      \
           Hash A   Hash B  Hash C   Hash D
            |        |       |         |
         [Cert 1] [Cert 2] [Cert 3] [Cert 4]
```

**Signed Certificate Timestamp (SCT)**:
```
SCT = Log ID + Timestamp + Certificate Hash + Signature

Embedded in certificate:
X509v3 SCT List (Precertificate):
    Signed Certificate Timestamp:
        Version   : v1 (0x0)
        Log ID    : BB:D9:DF:BC:...
        Timestamp : Jan  1 00:00:00.000 2025 GMT
        Extensions: none
        Signature : ecdsa-with-SHA256
                    30:45:02:20:...
```

### CT Log Submission

**Submit Certificate to Log**:
```bash
# Using ct-submit tool
ct-submit submit \
    --log_url https://ct.googleapis.com/logs/argon2021/ \
    --cert_chain server-fullchain.pem

# Response: SCT
{
  "sct_version": 0,
  "id": "BBD9DFBC1F8A71B593942397AA927B473857950AAB52E81A9090210D8A8C73A5",
  "timestamp": 1704067200000,
  "extensions": "",
  "signature": "BAMASDBGAiEA..."
}
```

**Embed SCT in Certificate**:
```
Option 1: X.509 Extension (Precertificate)
- CA submits precertificate to CT log
- CT log returns SCT
- CA embeds SCT in final certificate
- Most common method

Option 2: TLS Extension
- Server submits certificate to CT log
- Server provides SCT during TLS handshake
- Requires server configuration

Option 3: OCSP Stapling
- CA includes SCT in OCSP response
- Server staples OCSP response
- Client verifies SCT
```

### CT Monitoring

**Monitor for Unauthorized Certificates**:
```python
import requests

def monitor_ct_logs(domain):
    """Monitor CT logs for domain"""
    url = f"https://crt.sh/?q={domain}&output=json"
    response = requests.get(url)

    for cert in response.json():
        print(f"Cert: {cert['name_value']}")
        print(f"Issuer: {cert['issuer_name']}")
        print(f"Serial: {cert['serial_number']}")
        print(f"Not Before: {cert['not_before']}")
        print(f"Not After: {cert['not_after']}")
        print()

monitor_ct_logs("example.com")
```

**CT Log Monitoring Services**:
- **crt.sh**: Public certificate search
- **Facebook CT Monitor**: Real-time alerts
- **SSLMate Cert Spotter**: Commercial monitoring
- **Google CT Search**: CT log search

### CT Policy Requirements

**CA/Browser Forum Requirements**:
```
All publicly-trusted certificates MUST include:
- At least 2 SCTs from qualified CT logs
- SCTs from logs operated by different entities
- SCTs embedded in certificate or provided via OCSP/TLS
```

**Chrome CT Policy**:
```
Required SCTs based on certificate lifetime:
- < 180 days: 2 SCTs
- 180-824 days: 3 SCTs (from 3 different operators)
- > 824 days: Not allowed (max cert lifetime)
```

---

## 8. Private vs Public CAs

### Public CAs

**Characteristics**:
- Trusted by browsers/OS (in trust store)
- Subject to CA/Browser Forum Baseline Requirements
- Annual audits required (WebTrust, ETSI)
- Publicly-trusted for internet-facing services
- Higher cost

**Examples**:
- Let's Encrypt (free, automated)
- DigiCert, Sectigo, GlobalSign (commercial)

**Use Cases**:
- Public websites (HTTPS)
- Public APIs
- Software distribution
- Email (S/MIME)

### Private CAs

**Characteristics**:
- Not in public trust store (manual trust)
- Full control over policies
- No external audits required
- Internal use only
- Lower/no cost

**Examples**:
- OpenSSL CA
- Microsoft Active Directory Certificate Services (AD CS)
- HashiCorp Vault PKI
- AWS Private CA

**Use Cases**:
- Internal services (corporate network)
- mTLS for microservices
- Device certificates (IoT)
- VPN authentication

### Private CA Implementation

**Step-by-Step Setup**:
```bash
# 1. Create directory structure
mkdir -p ca/{root,intermediate}/{certs,crl,newcerts,private}
touch ca/root/index.txt ca/intermediate/index.txt
echo 1000 > ca/root/serial ca/intermediate/serial

# 2. Root CA config
cat > ca/root/openssl.cnf <<'EOF'
[ca]
default_ca = CA_default

[CA_default]
dir              = /path/to/ca/root
certs            = $dir/certs
crl_dir          = $dir/crl
new_certs_dir    = $dir/newcerts
database         = $dir/index.txt
serial           = $dir/serial
private_key      = $dir/private/ca-key.pem
certificate      = $dir/certs/ca-cert.pem
crl              = $dir/crl/ca.crl
crlnumber        = $dir/crlnumber
crl_extensions   = crl_ext
default_crl_days = 30
default_md       = sha384
preserve         = no
policy           = policy_strict

[policy_strict]
countryName             = match
stateOrProvinceName     = optional
organizationName        = match
organizationalUnitName  = optional
commonName              = supplied
emailAddress            = optional

[req]
default_bits        = 4096
distinguished_name  = req_distinguished_name
string_mask         = utf8only
default_md          = sha384
x509_extensions     = v3_ca

[req_distinguished_name]
countryName         = Country Name (2 letter code)
stateOrProvinceName = State or Province Name
localityName        = Locality Name
0.organizationName  = Organization Name
commonName          = Common Name

[v3_ca]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true
keyUsage = critical, keyCertSign, cRLSign

[crl_ext]
authorityKeyIdentifier=keyid:always
EOF

# 3. Generate root CA
cd ca/root
openssl genrsa -aes256 -out private/ca-key.pem 4096
chmod 400 private/ca-key.pem

openssl req -config openssl.cnf -key private/ca-key.pem \
    -new -x509 -days 7300 -sha384 -extensions v3_ca \
    -out certs/ca-cert.pem

# 4. Generate intermediate CA
cd ../intermediate
openssl genrsa -aes256 -out private/intermediate-key.pem 2048
chmod 400 private/intermediate-key.pem

openssl req -config openssl.cnf -new -sha384 \
    -key private/intermediate-key.pem \
    -out csr/intermediate.csr

# 5. Sign intermediate with root
cd ../root
openssl ca -config openssl.cnf -extensions v3_intermediate_ca \
    -days 3650 -notext -md sha384 \
    -in ../intermediate/csr/intermediate.csr \
    -out ../intermediate/certs/intermediate-cert.pem

# 6. Create certificate chain
cat ../intermediate/certs/intermediate-cert.pem \
    certs/ca-cert.pem > ../intermediate/certs/ca-chain.pem

# 7. Issue server certificate
cd ../intermediate
openssl req -config openssl.cnf -new -sha256 \
    -key private/www.example.com-key.pem \
    -out csr/www.example.com.csr

openssl ca -config openssl.cnf -extensions server_cert \
    -days 375 -notext -md sha256 \
    -in csr/www.example.com.csr \
    -out certs/www.example.com-cert.pem
```

---

## 9. HSM Integration

### Why HSM for PKI?

**Benefits**:
- Private keys never leave HSM (tamper-proof)
- FIPS 140-2 Level 3+ compliance
- Dual control and key backup
- Audit logging of all operations
- Physical security

**Use Cases**:
- Root CA key storage (critical)
- Intermediate CA key storage (recommended)
- High-volume certificate signing
- Code signing operations

### HSM Types

**Hardware HSM**:
- **Thales Luna**: Network HSM (FIPS 140-2 Level 3)
- **Entrust nShield**: PCIe or network HSM
- **Utimaco CryptoServer**: Network HSM
- **YubiHSM**: USB HSM (FIPS 140-2 Level 2)

**Cloud HSM**:
- **AWS CloudHSM**: FIPS 140-2 Level 3
- **Azure Dedicated HSM**: Thales Luna
- **Google Cloud HSM**: FIPS 140-2 Level 3

**Software HSM** (testing only):
- **SoftHSM**: PKCS#11 compliant software HSM

### PKCS#11 Integration

**Initialize SoftHSM** (for testing):
```bash
# Install SoftHSM
apt-get install softhsm2

# Initialize token
softhsm2-util --init-token --slot 0 --label "CA-Token" \
    --so-pin 123456 --pin 123456

# List tokens
softhsm2-util --show-slots
```

**Generate Key in HSM**:
```bash
# Generate RSA key pair in HSM
pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so \
    --login --pin 123456 \
    --keypairgen --key-type RSA:2048 \
    --label "CA-Signing-Key"

# List keys
pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so \
    --login --pin 123456 \
    --list-objects
```

**Sign Certificate with HSM**:
```bash
# OpenSSL engine for PKCS#11
openssl engine dynamic \
    -pre SO_PATH:/usr/lib/x86_64-linux-gnu/engines-1.1/libpkcs11.so \
    -pre ID:pkcs11 \
    -pre LIST_ADD:1 \
    -pre LOAD \
    -pre MODULE_PATH:/usr/lib/softhsm/libsofthsm2.so

# Sign certificate using HSM key
openssl ca -config ca.conf \
    -engine pkcs11 \
    -keyform engine \
    -keyfile "pkcs11:object=CA-Signing-Key;type=private;pin-value=123456" \
    -in server.csr \
    -out server-cert.pem
```

**Python HSM Integration**:
```python
from PyKCS11 import *
import subprocess

def sign_with_hsm(csr_path, cert_path):
    """Sign CSR using HSM"""
    pkcs11 = PyKCS11Lib()
    pkcs11.load('/usr/lib/softhsm/libsofthsm2.so')

    slot = pkcs11.getSlotList()[0]
    session = pkcs11.openSession(slot)
    session.login('123456')

    # Find signing key
    objects = session.findObjects([(CKA_CLASS, CKO_PRIVATE_KEY)])
    key = objects[0]

    # Read CSR
    with open(csr_path, 'rb') as f:
        csr_data = f.read()

    # Sign CSR (use OpenSSL ca command with PKCS#11 engine)
    subprocess.run([
        'openssl', 'ca',
        '-engine', 'pkcs11',
        '-keyform', 'engine',
        '-keyfile', 'pkcs11:object=CA-Signing-Key;type=private;pin-value=123456',
        '-in', csr_path,
        '-out', cert_path
    ])

    session.logout()
    session.closeSession()
```

### AWS CloudHSM Integration

**Setup CloudHSM**:
```bash
# Install CloudHSM client
wget https://s3.amazonaws.com/cloudhsmv2-software/CloudHsmClient/EL7/cloudhsm-client-latest.el7.x86_64.rpm
yum install -y cloudhsm-client-latest.el7.x86_64.rpm

# Configure cluster
/opt/cloudhsm/bin/configure -a <cluster-hsm-ip>

# Start client
systemctl start cloudhsm-client
```

**Generate CA Key in CloudHSM**:
```bash
# Activate HSM
/opt/cloudhsm/bin/cloudhsm_mgmt_util
aws-cloudhsm> loginHSM CO admin password
aws-cloudhsm> createUser CU ca-admin password
aws-cloudhsm> quit

# Generate key
/opt/cloudhsm/bin/key_mgmt_util
Command: loginHSM -u CU -s ca-admin -p password
Command: genRSAKeyPair -m 2048 -e 65537 -l ca-key
Command: quit
```

**Sign with CloudHSM**:
```bash
# Configure OpenSSL to use CloudHSM
export PKCS11_MODULE_PATH=/opt/cloudhsm/lib/libcloudhsm_pkcs11.so

# Sign certificate
openssl ca -config ca.conf \
    -engine cloudhsm \
    -keyform engine \
    -keyfile "0:ca-admin:password" \
    -in server.csr \
    -out server-cert.pem
```

---

## 10. Cross-Certification

### What is Cross-Certification?

**Problem**: Trust between different PKI hierarchies

**Solution**: CAs sign each other's certificates

**Cross-Certification Models**:

**Model 1: Peer-to-Peer**:
```
Org A Root CA ←→ Org B Root CA
     ↓                 ↓
Org A Intermediate   Org B Intermediate
```

**Model 2: Bridge CA**:
```
    Org A Root ←→ Bridge CA ←→ Org B Root
         ↓                          ↓
    Org A Intermediate        Org B Intermediate
         ↓                          ↓
    Org A Users              Org B Users
```

### Implementing Cross-Certification

**Step 1: Org A Creates CSR for Cross-Cert**:
```bash
# Org A creates CSR
openssl req -new -key org-a-root-key.pem -out org-a-cross.csr
```

**Step 2: Org B Signs Cross-Certificate**:
```bash
# Org B signs Org A's CSR
openssl x509 -req -in org-a-cross.csr \
    -CA org-b-root-cert.pem \
    -CAkey org-b-root-key.pem \
    -out org-a-cross-cert.pem \
    -days 3650 \
    -extfile cross-cert.conf

cat > cross-cert.conf <<EOF
basicConstraints = critical,CA:TRUE,pathlen:0
keyUsage = critical,keyCertSign,cRLSign
nameConstraints = permitted;DNS:.org-a.com
certificatePolicies = @org_a_policies

[org_a_policies]
policyIdentifier = 1.3.6.1.4.1.99999.1
EOF
```

**Step 3: Configure Certificate Validation**:
```bash
# Trust both roots
cat org-a-root-cert.pem org-b-root-cert.pem > trust-bundle.pem

# Verify certificate from Org B using Org A's trust
openssl verify -CAfile trust-bundle.pem -untrusted org-b-intermediate.pem org-b-cert.pem
```

### Bridge CA Architecture

**FPKI Bridge** (US Federal PKI):
```
Federal Bridge CA (FBCA)
├─→ Cross-certified with commercial CAs (DigiCert, Entrust)
├─→ Cross-certified with government CAs (DOD, State Dept)
└─→ Cross-certified with international CAs

Benefits:
- Central trust point
- Simplified cross-certification (N CAs → 1 bridge, not N² peer-to-peer)
- Policy mapping and constraints
```

**Implementing Bridge CA**:
```bash
# Bridge CA signs cross-certificates for multiple organizations
openssl x509 -req -in org-a.csr -CA bridge-ca.pem -CAkey bridge-ca-key.pem \
    -out org-a-cross.pem -extfile bridge-ext.conf

openssl x509 -req -in org-b.csr -CA bridge-ca.pem -CAkey bridge-ca-key.pem \
    -out org-b-cross.pem -extfile bridge-ext.conf

# Bridge extension (name constraints)
cat > bridge-ext.conf <<EOF
basicConstraints = critical,CA:TRUE,pathlen:0
nameConstraints = permitted;DNS:.org-a.com
certificatePolicies = 2.16.840.1.101.3.2.1.3.13
EOF
```

---

## 11. Compliance and Standards

### CA/Browser Forum Baseline Requirements

**Purpose**: Standards for publicly-trusted CAs

**Key Requirements**:

**Certificate Lifetimes**:
```
- TLS Server: Maximum 398 days (13 months)
- Code Signing: Maximum 39 months
- Email (S/MIME): Maximum 825 days
- EV: Maximum 27 months (being phased out)
```

**Key Sizes**:
```
- RSA: Minimum 2048 bits (4096 for root CAs)
- ECDSA: Minimum P-256
- Hash: SHA-256 or stronger (SHA-1 deprecated)
```

**Domain Validation**:
```
Must use one of 10 approved methods:
1. Email to admin@domain
2. HTTP token validation (.well-known)
3. DNS TXT record
4. TLS ALPN challenge
5. ... (see BR section 3.2.2.4)
```

**Revocation**:
```
- CRL: Update at least every 7 days
- OCSP: Responses valid for maximum 10 days
- Revocation within 24 hours of compromise
```

### WebTrust Audits

**Purpose**: Independent audit of CA operations

**Audit Types**:
- **WebTrust for CAs**: Baseline audit
- **WebTrust BR SSL**: CA/Browser Forum compliance
- **WebTrust EV SSL**: Extended Validation compliance

**Audit Scope**:
```
- Business practices (CP/CPS)
- Key generation and protection
- Certificate issuance procedures
- Revocation processes
- Physical security
- Audit logging
- Incident response
```

**Audit Cycle**:
- Initial audit (point-in-time)
- Annual re-audit
- Continuous monitoring

### NIST Standards

**NIST 800-57**: Key Management
```
Part 1: General Guidance
Part 2: Best Practices for Key Management Organizations
Part 3: Application-Specific Key Management

Key recommendations:
- RSA 2048-bit ≈ 112-bit security (valid until 2030)
- RSA 3072-bit ≈ 128-bit security (valid through 2030+)
- ECC P-256 ≈ 128-bit security
```

**NIST 800-52**: TLS Guidelines
**NIST 800-63**: Digital Identity Guidelines

### FIPS 140-2/3

**Purpose**: Cryptographic module validation

**Levels**:
- **Level 1**: Basic security (software)
- **Level 2**: Tamper-evident (requires role-based authentication)
- **Level 3**: Tamper-resistant (requires physical security)
- **Level 4**: Tamper-responsive (active tamper detection)

**PKI Requirements**:
```
CA key storage:
- Root CA: FIPS 140-2 Level 3+ (offline)
- Intermediate CA: FIPS 140-2 Level 2+ (online)

Algorithms:
- RSA: 2048-bit minimum
- ECDSA: P-256 minimum
- Hash: SHA-256 minimum
```

### Certificate Policies (CP) and Certificate Practice Statement (CPS)

**Certificate Policy** (RFC 3647):
```
High-level policy document defining:
- Certificate usage
- Validation requirements
- Liability and warranties
- Audit requirements

Example: CA/Browser Forum Baseline Requirements
```

**Certificate Practice Statement**:
```
Detailed implementation of CP:
- Physical security controls
- Key ceremony procedures
- Personnel security
- Certificate issuance workflow
- Revocation procedures
- Audit logging

Example: Let's Encrypt CPS
```

**OID Assignment**:
```
Enterprise OID: 1.3.6.1.4.1.{enterprise-number}
Policy OIDs:
- 1.3.6.1.4.1.99999.1.1 - Domain Validated
- 1.3.6.1.4.1.99999.1.2 - Organization Validated
- 1.3.6.1.4.1.99999.1.3 - Extended Validation

Embedded in certificates:
X509v3 Certificate Policies:
    Policy: 1.3.6.1.4.1.99999.1.1
      CPS: https://example.com/cps
```

### PCI-DSS Requirements

**PCI-DSS 4.0**: Certificate requirements for payment card industry

```
Requirement 4.2: Strong cryptography for transmission
- TLS 1.2 minimum (TLS 1.3 recommended)
- Strong cipher suites only
- Valid certificates from trusted CAs

Certificate Management:
- Maintain inventory of certificates
- Monitor expiration (alert 30 days before)
- Renew before expiration
- Revoke compromised certificates immediately
```

---

## 12. Tools and Software

### OpenSSL

**CA Operations**:
```bash
# Generate private key
openssl genrsa -out key.pem 2048
openssl ecparam -genkey -name prime256v1 -out key.pem

# Create CSR
openssl req -new -key key.pem -out request.csr

# Self-signed certificate
openssl req -x509 -new -key key.pem -out cert.pem -days 365

# Sign CSR
openssl ca -config ca.conf -in request.csr -out cert.pem

# View certificate
openssl x509 -in cert.pem -text -noout

# Verify chain
openssl verify -CAfile ca.pem cert.pem

# Convert formats
openssl x509 -in cert.pem -outform DER -out cert.der
openssl pkcs12 -export -in cert.pem -inkey key.pem -out cert.p12

# Generate CRL
openssl ca -config ca.conf -gencrl -out ca.crl

# OCSP responder
openssl ocsp -port 8080 -index index.txt -CA ca.pem -rkey ocsp-key.pem -rsigner ocsp-cert.pem
```

### CFSSL (CloudFlare PKI Toolkit)

**Features**:
- JSON-based configuration
- RESTful API
- Multi-root support
- OCSP responder

**Setup**:
```bash
# Install
go install github.com/cloudflare/cfssl/cmd/cfssl@latest
go install github.com/cloudflare/cfssl/cmd/cfssljson@latest

# CA configuration
cat > ca-config.json <<EOF
{
  "signing": {
    "default": {
      "expiry": "8760h"
    },
    "profiles": {
      "server": {
        "usages": ["signing", "key encipherment", "server auth"],
        "expiry": "8760h"
      },
      "client": {
        "usages": ["signing", "key encipherment", "client auth"],
        "expiry": "8760h"
      }
    }
  }
}
EOF

# Generate CA
cat > ca-csr.json <<EOF
{
  "CN": "Example CA",
  "key": {
    "algo": "ecdsa",
    "size": 256
  },
  "names": [
    {
      "C": "US",
      "ST": "California",
      "L": "San Francisco",
      "O": "Example Corp"
    }
  ]
}
EOF

cfssl gencert -initca ca-csr.json | cfssljson -bare ca

# Issue certificate
cat > server-csr.json <<EOF
{
  "CN": "www.example.com",
  "hosts": [
    "www.example.com",
    "example.com"
  ],
  "key": {
    "algo": "ecdsa",
    "size": 256
  }
}
EOF

cfssl gencert -ca=ca.pem -ca-key=ca-key.pem \
    -config=ca-config.json -profile=server \
    server-csr.json | cfssljson -bare server
```

### Step CA (Smallstep)

**Features**:
- ACME server (Let's Encrypt-compatible)
- SSH certificate authority
- Single-command setup
- OIDC integration

**Setup**:
```bash
# Install
wget https://dl.step.sm/gh-release/cli/docs-ca-install/v0.24.4/step-cli_0.24.4_amd64.deb
dpkg -i step-cli_0.24.4_amd64.deb

# Initialize CA
step ca init --name="Example CA" \
    --dns="ca.example.com" \
    --address=":443" \
    --provisioner="admin@example.com"

# Start CA server
step-ca $(step path)/config/ca.json

# Issue certificate
step ca certificate www.example.com www.example.com.crt www.example.com.key

# ACME support
step ca provisioner add acme --type=ACME
```

### HashiCorp Vault PKI

**Features**:
- Dynamic secrets
- API-driven
- Automated rotation
- Role-based access control

**Setup**:
```bash
# Enable PKI engine
vault secrets enable pki

# Configure max lease
vault secrets tune -max-lease-ttl=87600h pki

# Generate root CA
vault write -field=certificate pki/root/generate/internal \
    common_name="Example Root CA" \
    ttl=87600h > ca.crt

# Configure CRL and OCSP
vault write pki/config/urls \
    issuing_certificates="http://vault.example.com:8200/v1/pki/ca" \
    crl_distribution_points="http://vault.example.com:8200/v1/pki/crl"

# Create role
vault write pki/roles/example-dot-com \
    allowed_domains="example.com" \
    allow_subdomains=true \
    max_ttl="720h"

# Issue certificate
vault write pki/issue/example-dot-com \
    common_name="www.example.com" \
    ttl="24h"
```

### cert-manager (Kubernetes)

**Features**:
- Automated certificate management
- ACME support (Let's Encrypt)
- Internal CA support
- Automatic renewal

**Setup**:
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create CA issuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: ca-issuer
spec:
  ca:
    secretName: ca-key-pair
EOF

# Issue certificate
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-com
spec:
  secretName: example-com-tls
  issuerRef:
    name: ca-issuer
    kind: ClusterIssuer
  dnsNames:
  - example.com
  - www.example.com
EOF
```

---

## 13. Production Patterns

### Pattern 1: Tiered CA Hierarchy

**Architecture**:
```
Tier 0: Root CA (offline, air-gapped)
        └─ Signs Tier 1 CAs only

Tier 1: Policy CAs (offline, quarterly access)
        ├─ TLS CA
        ├─ Email CA
        └─ Code Signing CA

Tier 2: Issuing CAs (online, HSM-protected)
        ├─ Production TLS CA
        ├─ Staging TLS CA
        ├─ Internal TLS CA
        └─ ... (purpose-specific)
```

**Benefits**:
- Root compromise doesn't compromise everything
- Different policies per certificate type
- Easier revocation and re-issuance
- Compliance with separation of duties

### Pattern 2: Hot/Cold CA Design

**Architecture**:
```
Root CA (Cold):
- Stored offline in secure facility
- Access only for:
  * Issuing intermediate certificates (annual)
  * Revoking intermediate certificates (emergency)
  * Root CA renewal (every 20 years)

Intermediate CA (Hot):
- Online HSM-protected
- Issues certificates automatically
- Revokes certificates as needed
- Managed by PKI automation system
```

**Implementation**:
```bash
# Cold CA: Create intermediate certificate (annual operation)
# Performed in secure facility with dual control

# 1. Transport intermediate CSR to secure facility
# 2. Unlock root CA HSM (requires M-of-N key custodians)
# 3. Sign intermediate certificate
openssl ca -config root-ca.conf -in intermediate.csr -out intermediate.pem \
    -days 3650 -extensions v3_intermediate_ca

# 4. Export signed certificate
# 5. Re-lock HSM and return to secure storage
# 6. Transport certificate back to production

# Hot CA: Automated certificate issuance
# Runs continuously, signing thousands of certificates per day
/opt/pki/ca-server --config hot-ca.conf
```

### Pattern 3: Multi-Region CA Deployment

**Architecture**:
```
Primary Region (us-east-1):
├─ Intermediate CA (primary)
├─ OCSP Responder
├─ CRL Distribution Point
└─ Certificate Database (master)

Secondary Region (eu-west-1):
├─ Intermediate CA (replica)
├─ OCSP Responder (replica)
├─ CRL Distribution Point (replica)
└─ Certificate Database (replica)

Disaster Recovery Region (ap-south-1):
├─ Cold standby CA
└─ Database backup
```

**Benefits**:
- High availability
- Low latency globally
- Disaster recovery
- Regulatory compliance (data locality)

### Pattern 4: Automated Certificate Lifecycle

**Components**:
```
┌──────────────────────────────────────────────────┐
│ Certificate Lifecycle Management System          │
├──────────────────────────────────────────────────┤
│ Request → Validation → Issuance → Deployment     │
│    ↓           ↓           ↓           ↓         │
│ Portal     Domain      CA API    Ansible/K8s     │
│            Check                                  │
│                                                   │
│ Monitoring → Renewal → Revocation → Cleanup      │
│     ↓          ↓           ↓           ↓         │
│ Prometheus  Auto-renew  CRL/OCSP  Archive DB     │
└──────────────────────────────────────────────────┘
```

**Workflow**:
```bash
# 1. Certificate Request (API)
curl -X POST https://pki-api.example.com/v1/certificates \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "common_name": "api.example.com",
    "sans": ["api.example.com", "api-v2.example.com"],
    "duration": "90d",
    "profile": "tls-server"
  }'

# 2. Domain Validation (automatic)
# System performs HTTP-01 or DNS-01 validation

# 3. Certificate Issuance (automatic)
# CA signs certificate

# 4. Certificate Deployment (automatic)
# Ansible/Kubernetes deploys certificate

# 5. Monitoring (continuous)
# Prometheus tracks expiration

# 6. Renewal (automatic, 30 days before expiry)
# System generates new certificate and deploys

# 7. Revocation (on-demand)
curl -X DELETE https://pki-api.example.com/v1/certificates/12345 \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"reason": "keyCompromise"}'
```

---

## 14. Security Best Practices

### Root CA Protection

**Physical Security**:
```
- Store in secure facility (datacenter cage, vault)
- Air-gapped (no network connection)
- Access control (biometric, key card, video surveillance)
- Dual control (requires 2+ people for access)
- Tamper-evident seals
- Environmental controls (fire suppression, UPS)
```

**Key Management**:
```
- Generate keys in HSM (never exported)
- M-of-N secret sharing (e.g., 3-of-5)
- Key ceremony with witnesses
- Backup to offline media (encrypted)
- Store backups in separate geographic locations
- Test recovery procedures annually
```

**Operational Security**:
```
- Minimize access frequency (quarterly or less)
- Document all operations (video, log, witness)
- Background checks for key custodians
- Rotate key custodians periodically
- Incident response plan
```

### Intermediate CA Protection

**Network Security**:
```
- Dedicated VLAN
- Firewall rules (least privilege)
- IDS/IPS monitoring
- DDoS protection
- Rate limiting
```

**Application Security**:
```
- Principle of least privilege
- Strong authentication (mTLS, MFA)
- API rate limiting
- Input validation
- Audit logging
```

**Key Protection**:
```
- HSM storage (FIPS 140-2 Level 2+)
- Key rotation (every 5 years)
- Backup and recovery procedures
- Key escrow (if required by policy)
```

### Certificate Validation Best Practices

**Client-Side Validation**:
```python
import ssl
import socket
from datetime import datetime

def validate_certificate(hostname, port=443):
    """Comprehensive certificate validation"""
    context = ssl.create_default_context()

    # 1. Establish connection
    with socket.create_connection((hostname, port), timeout=5) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()

            # 2. Check hostname
            ssl.match_hostname(cert, hostname)

            # 3. Check expiration
            not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
            if not_after < datetime.now():
                raise ValueError("Certificate expired")

            # 4. Check chain (automatically done by create_default_context)
            # context.verify_mode = ssl.CERT_REQUIRED
            # context.check_hostname = True

            # 5. Check revocation (OCSP/CRL)
            # (requires additional libraries like certvalidator)

            return True

try:
    validate_certificate("example.com")
    print("Certificate valid")
except Exception as e:
    print(f"Certificate validation failed: {e}")
```

### Secure Certificate Storage

**Server-Side**:
```bash
# Proper permissions
chown root:ssl-cert /etc/ssl/private/server-key.pem
chmod 640 /etc/ssl/private/server-key.pem

# Encrypted private key
openssl genrsa -aes256 -out encrypted-key.pem 2048

# Hardware Security Module
# Store keys in HSM, never on filesystem
```

**Secret Management**:
```bash
# Kubernetes secrets
kubectl create secret tls example-com-tls \
    --cert=cert.pem \
    --key=key.pem

# HashiCorp Vault
vault kv put secret/certs/example.com \
    cert=@cert.pem \
    key=@key.pem

# AWS Secrets Manager
aws secretsmanager create-secret \
    --name example-com-cert \
    --secret-string file://cert-bundle.json
```

---

## 15. Troubleshooting

### Common Issues

#### Issue 1: Certificate Validation Fails

**Symptoms**:
```
SSL_ERROR_BAD_CERT_DOMAIN
CERT_UNTRUSTED
CERT_HAS_EXPIRED
```

**Diagnosis**:
```bash
# Check certificate details
openssl s_client -connect example.com:443 -showcerts

# Verify certificate chain
openssl verify -CAfile ca-bundle.pem server-cert.pem

# Check hostname matching
openssl x509 -in server-cert.pem -noout -text | grep -A1 "Subject Alternative Name"

# Check expiration
openssl x509 -in server-cert.pem -noout -dates
```

**Solutions**:
- Hostname mismatch: Add SAN or use correct hostname
- Untrusted: Install intermediate certificate
- Expired: Renew certificate

#### Issue 2: CRL/OCSP Unavailable

**Symptoms**:
- Certificate validation failures
- Slow HTTPS connections
- Soft-fail allows invalid certificates

**Diagnosis**:
```bash
# Check CRL accessibility
curl -I http://crl.example.com/intermediate.crl

# Check OCSP responder
openssl ocsp -issuer ca.pem -cert cert.pem -url http://ocsp.example.com -CAfile ca.pem

# Check CRL/OCSP URLs in certificate
openssl x509 -in cert.pem -noout -text | grep -A2 "CRL Distribution\|OCSP"
```

**Solutions**:
- Configure OCSP stapling (server-side)
- Deploy redundant CRL/OCSP servers
- Use CDN for CRL distribution
- Enable soft-fail for non-critical applications

#### Issue 3: Chain Incomplete

**Symptoms**:
```
INCOMPLETE_CHAIN
unable to get local issuer certificate
```

**Diagnosis**:
```bash
# Test with system trust store
openssl s_client -connect example.com:443 -CApath /etc/ssl/certs

# Test with specific CA bundle
openssl s_client -connect example.com:443 -CAfile ca-bundle.pem

# View server's certificate chain
openssl s_client -connect example.com:443 -showcerts
```

**Solutions**:
```bash
# Create full chain (server + intermediate)
cat server-cert.pem intermediate-cert.pem > fullchain.pem

# Configure server with full chain
# Nginx
ssl_certificate /etc/ssl/certs/fullchain.pem;

# Apache
SSLCertificateFile /etc/ssl/certs/fullchain.pem
```

#### Issue 4: Key Mismatch

**Symptoms**:
- Server fails to start
- "key values mismatch" error

**Diagnosis**:
```bash
# Extract modulus from certificate
openssl x509 -noout -modulus -in cert.pem | openssl md5

# Extract modulus from private key
openssl rsa -noout -modulus -in key.pem | openssl md5

# Hashes must match!
```

**Solutions**:
- Ensure correct key used for CSR
- Regenerate certificate with correct key
- Verify key permissions (readable by server)

#### Issue 5: CA Compromise

**Symptoms**:
- Unauthorized certificates discovered
- Private key leaked
- Security breach detected

**Response Plan**:
```
IMMEDIATE (0-24 hours):
1. Revoke compromised CA certificate
2. Notify all relying parties
3. Update CRL/OCSP with revocation
4. Publish incident notification
5. Contact browser vendors (for publicly-trusted CAs)

SHORT-TERM (24-72 hours):
1. Issue new CA certificates
2. Re-issue all certificates from compromised CA
3. Deploy new certificates to all systems
4. Update trust stores

LONG-TERM (72+ hours):
1. Root cause analysis
2. Implement additional controls
3. Security audit
4. Update CP/CPS
5. Re-certification (if required)
```

---

## Appendix A: Certificate Formats

### PEM (Privacy Enhanced Mail)
```
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKHHCgK...
...
-----END CERTIFICATE-----

Base64-encoded DER
File extensions: .pem, .crt, .cer, .key
```

### DER (Distinguished Encoding Rules)
```
Binary format
File extensions: .der, .cer
Convert: openssl x509 -in cert.pem -outform DER -out cert.der
```

### PKCS#12 (.p12, .pfx)
```
Binary format containing certificate + private key
Password-protected
Common in Windows environments

Create:
openssl pkcs12 -export -in cert.pem -inkey key.pem -out cert.p12

Extract:
openssl pkcs12 -in cert.p12 -out cert.pem -nodes
```

### PKCS#7 (.p7b, .p7c)
```
Certificate chain (no private key)
Used for certificate distribution

Create:
openssl crl2pkcs7 -nocrl -certfile fullchain.pem -out cert.p7b

View:
openssl pkcs7 -in cert.p7b -print_certs -text
```

---

## Appendix B: Key Algorithms

### RSA
```
Key Sizes: 2048, 3072, 4096 bits
Security: 2048-bit ≈ 112-bit security
Performance: Slower than ECC
Use Case: General purpose, FIPS compliance
```

### ECDSA
```
Curves: P-256, P-384, P-521
Security: P-256 ≈ 128-bit security
Performance: Faster than RSA
Use Case: Mobile, embedded, modern systems
```

### EdDSA
```
Curves: Ed25519, Ed448
Security: Ed25519 ≈ 128-bit security
Performance: Fastest
Use Case: Modern applications, SSH
```

---

## Appendix C: Useful Commands

```bash
# Generate keys
openssl genrsa -out key.pem 2048                    # RSA
openssl ecparam -genkey -name prime256v1 -out key.pem  # ECDSA

# Create CSR
openssl req -new -key key.pem -out request.csr

# Self-signed certificate
openssl req -x509 -new -key key.pem -out cert.pem -days 365

# View certificate
openssl x509 -in cert.pem -text -noout

# Verify certificate
openssl verify -CAfile ca.pem cert.pem

# Test TLS connection
openssl s_client -connect example.com:443 -showcerts

# Convert formats
openssl x509 -in cert.pem -outform DER -out cert.der
openssl x509 -in cert.der -inform DER -outform PEM -out cert.pem
openssl pkcs12 -export -in cert.pem -inkey key.pem -out cert.p12

# Extract from PKCS#12
openssl pkcs12 -in cert.p12 -out cert.pem -nodes

# Generate CRL
openssl ca -config ca.conf -gencrl -out ca.crl

# Check OCSP
openssl ocsp -issuer ca.pem -cert cert.pem -url http://ocsp.example.com

# Check certificate expiration
openssl x509 -in cert.pem -noout -dates
openssl x509 -in cert.pem -noout -enddate | cut -d= -f2 | xargs -I {} date -d {} +%s
```

---

## References

- **RFC 5280**: X.509 Public Key Infrastructure Certificate and CRL Profile
- **RFC 6960**: Online Certificate Status Protocol (OCSP)
- **RFC 6962**: Certificate Transparency
- **RFC 3647**: Certificate Policy and Certification Practice Framework
- **CA/Browser Forum Baseline Requirements**: https://cabforum.org/baseline-requirements-documents/
- **NIST 800-57**: Recommendation for Key Management
- **NIST 800-52**: Guidelines for TLS Implementation
- **WebTrust Principles and Criteria**: https://www.cpacanada.ca/webtrust

---

**End of PKI Infrastructure Reference**
**Total Lines**: ~3,800
