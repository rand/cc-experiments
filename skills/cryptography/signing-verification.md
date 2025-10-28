---
name: cryptography-signing-verification
description: Digital signature creation, verification, and chain of trust for documents, code, and artifacts
---

# Digital Signing and Verification

**Scope**: Digital signatures, code signing, artifact verification, chain of trust, timestamping, HSM integration
**Lines**: ~450
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Signing code, documents, containers, or artifacts
- Verifying digital signatures and authenticity
- Implementing code signing workflows (Apple, Microsoft, Android)
- Using Sigstore/cosign for container signing
- Managing signing keys and certificates
- Implementing timestamping for long-term verification
- Integrating HSM for signing operations
- Meeting compliance requirements (FIPS 186-4, eIDAS, Common Criteria)
- Building trust chains and certificate verification
- Detecting tampering or unauthorized modifications

## Core Concepts

### What are Digital Signatures?

**Digital signatures** provide:
- **Authentication**: Proof of signer identity
- **Integrity**: Proof data hasn't been modified
- **Non-repudiation**: Signer cannot deny signing

**How it works**:
```
1. Hash the data → SHA-256 hash
2. Encrypt hash with private key → Digital signature
3. Distribute data + signature + public key

Verification:
1. Hash the received data
2. Decrypt signature with public key → Original hash
3. Compare hashes → Match = authentic, Mismatch = tampered
```

### Signature Algorithms

| Algorithm | Key Type | Security | Use Case |
|-----------|----------|----------|----------|
| **RSA-PSS** | RSA (2048-4096 bit) | High | General purpose, FIPS compliance |
| **ECDSA** | ECC (P-256, P-384) | High | Mobile, embedded, space-constrained |
| **EdDSA (Ed25519)** | Curve25519 | Highest | Modern applications, performance |
| **RSA-PKCS#1 v1.5** | RSA | Moderate | Legacy (vulnerable to attacks) |
| **DSA** | Discrete Log | Low | Deprecated (use ECDSA instead) |

**Recommendations**:
- ✅ **EdDSA (Ed25519)**: Modern, fast, secure (recommended)
- ✅ **ECDSA P-256**: FIPS-approved, widely supported
- ✅ **RSA-PSS 3072+**: FIPS-approved, future-proof
- ❌ **RSA-PKCS#1 v1.5**: Vulnerable to attacks
- ❌ **DSA**: Deprecated

---

## Signature Formats

### PKCS#7 / CMS (Cryptographic Message Syntax)

**Standard**: RFC 5652
**Use case**: Document signing, S/MIME email

```bash
# Sign file with PKCS#7
openssl smime -sign -in document.txt \
    -out document.p7s \
    -signer cert.pem \
    -inkey private.key

# Verify PKCS#7 signature
openssl smime -verify -in document.p7s \
    -CAfile ca-cert.pem \
    -out document.txt
```

### JWS (JSON Web Signature)

**Standard**: RFC 7515
**Use case**: API tokens, JSON data signing

```python
import jwt

# Sign JSON data
payload = {"user": "alice", "role": "admin"}
token = jwt.encode(payload, private_key, algorithm='RS256')

# Verify signature
decoded = jwt.decode(token, public_key, algorithms=['RS256'])
```

### XML-DSig (XML Digital Signature)

**Standard**: W3C Recommendation
**Use case**: SAML, SOAP, XML documents

```xml
<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
  <SignedInfo>
    <CanonicalizationMethod Algorithm="..."/>
    <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
    <Reference URI="">
      <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
      <DigestValue>...</DigestValue>
    </Reference>
  </SignedInfo>
  <SignatureValue>...</SignatureValue>
  <KeyInfo>...</KeyInfo>
</Signature>
```

### Detached vs Embedded Signatures

**Detached** (separate file):
```bash
# Create detached signature
gpg --detach-sign --armor file.tar.gz
# Produces: file.tar.gz.asc

# Verify
gpg --verify file.tar.gz.asc file.tar.gz
```

**Embedded** (within file):
```bash
# Create embedded signature
gpg --sign file.tar.gz
# Produces: file.tar.gz.gpg (contains both data and signature)

# Verify and extract
gpg file.tar.gz.gpg
```

---

## Code Signing

### macOS / iOS (Apple Developer)

**Requirements**:
- Apple Developer account
- Code signing certificate from Apple
- Xcode or `codesign` tool

**Sign application**:
```bash
# Sign app bundle
codesign --sign "Developer ID Application: Your Name" \
    --deep \
    --force \
    --options runtime \
    --timestamp \
    YourApp.app

# Verify signature
codesign --verify --verbose=4 YourApp.app

# Display signature details
codesign --display --verbose=4 YourApp.app

# Notarize (required for macOS 10.15+)
xcrun notarytool submit YourApp.zip \
    --apple-id "your@email.com" \
    --password "app-specific-password" \
    --team-id "TEAM_ID"
```

### Windows (Authenticode)

**Requirements**:
- Code signing certificate (from CA like DigiCert)
- `signtool.exe` (Windows SDK)

**Sign executable**:
```cmd
# Sign with timestamp
signtool sign /f certificate.pfx /p password /fd SHA256 \
    /tr http://timestamp.digicert.com /td SHA256 \
    application.exe

# Verify signature
signtool verify /pa application.exe

# Display signature details
signtool verify /v /pa application.exe
```

### Android (APK Signing)

**V1 (JAR signing)** - Legacy:
```bash
jarsigner -keystore my-release-key.jks \
    -signedjar app-signed.apk \
    app-unsigned.apk \
    my-key-alias
```

**V2/V3/V4 (APK Signature Scheme)** - Modern:
```bash
# Sign with apksigner (recommended)
apksigner sign --ks my-release-key.jks \
    --ks-key-alias my-key-alias \
    --out app-signed.apk \
    app-unsigned.apk

# Verify
apksigner verify --verbose app-signed.apk
```

---

## Container Signing (Sigstore / Cosign)

### Sigstore

**Sigstore** provides:
- Keyless signing (OIDC-based, no key management)
- Transparency log (Rekor) for audit
- Certificate authority (Fulcio) for ephemeral certificates

**Install cosign**:
```bash
# macOS
brew install cosign

# Linux
wget https://github.com/sigstore/cosign/releases/download/v2.2.0/cosign-linux-amd64
chmod +x cosign-linux-amd64
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
```

### Keyless Signing (OIDC)

**Sign container image**:
```bash
# Sign with OIDC (Google, GitHub, Microsoft)
cosign sign ghcr.io/myorg/myapp:v1.0.0

# Interactive OIDC flow opens browser
# Ephemeral keys generated and certificate issued by Fulcio
# Signature recorded in Rekor transparency log
```

**Verify**:
```bash
# Verify with certificate identity
cosign verify ghcr.io/myorg/myapp:v1.0.0 \
    --certificate-identity=user@example.com \
    --certificate-oidc-issuer=https://accounts.google.com
```

### Key-Based Signing

**Generate signing key**:
```bash
# Generate key pair
cosign generate-key-pair

# Produces:
# - cosign.key (private key, encrypted)
# - cosign.pub (public key)
```

**Sign and verify**:
```bash
# Sign with key
cosign sign --key cosign.key ghcr.io/myorg/myapp:v1.0.0

# Verify with public key
cosign verify --key cosign.pub ghcr.io/myorg/myapp:v1.0.0
```

### Sign Artifacts (Not Containers)

**Sign files**:
```bash
# Sign arbitrary file
cosign sign-blob --key cosign.key file.tar.gz > file.tar.gz.sig

# Verify
cosign verify-blob --key cosign.pub \
    --signature file.tar.gz.sig \
    file.tar.gz
```

---

## Timestamping

### Why Timestamp Signatures?

**Problem**: Signatures become invalid when signing certificate expires.

**Solution**: Timestamp Authority (TSA) provides proof that signature existed at specific time.

**Timestamping flow**:
```
1. Sign document with private key
2. Send signature to TSA
3. TSA signs signature with timestamp
4. Signature valid even after certificate expires (as long as it was valid at signing time)
```

### RFC 3161 Timestamp Protocol

**Request timestamp**:
```bash
# Sign with timestamp (OpenSSL)
openssl ts -query -data document.txt -sha256 -cert -out request.tsq

# Send to TSA
curl -H "Content-Type: application/timestamp-query" \
    --data-binary @request.tsq \
    http://timestamp.digicert.com > response.tsr

# Verify timestamp
openssl ts -verify -data document.txt -in response.tsr \
    -CAfile tsa-cert.pem
```

**Popular TSAs**:
- DigiCert: `http://timestamp.digicert.com`
- Sectigo: `http://timestamp.sectigo.com`
- FreeTSA: `https://freetsa.org/tsr`

---

## GPG / PGP Signing

### Generate Key Pair

```bash
# Generate GPG key
gpg --full-generate-key
# Choose: RSA and RSA (default), 4096 bits, expires in 1 year

# List keys
gpg --list-keys
gpg --list-secret-keys
```

### Sign Files

```bash
# Detached ASCII signature
gpg --detach-sign --armor file.tar.gz
# Creates: file.tar.gz.asc

# Verify
gpg --verify file.tar.gz.asc file.tar.gz

# Embedded signature
gpg --sign file.tar.gz
# Creates: file.tar.gz.gpg

# Clear-sign (text with inline signature)
gpg --clearsign message.txt
```

### Git Commit Signing

**Configure Git**:
```bash
# Set signing key
git config --global user.signingkey YOUR_KEY_ID

# Enable signing by default
git config --global commit.gpgsign true
git config --global tag.gpgsign true
```

**Sign commits**:
```bash
# Sign commit
git commit -S -m "Signed commit"

# Sign tag
git tag -s v1.0.0 -m "Signed release"

# Verify
git verify-commit HEAD
git verify-tag v1.0.0
```

---

## Certificate Chains and Trust

### Chain of Trust

```
┌─────────────────────┐
│ Root CA             │ ← Self-signed, offline, highly trusted
└──────────┬──────────┘
           │ signs
┌──────────▼──────────┐
│ Intermediate CA     │ ← Operational CA
└──────────┬──────────┘
           │ signs
┌──────────▼──────────┐
│ Code Signing Cert   │ ← End-entity certificate
└─────────────────────┘
           │
           ▼
      Signed Code
```

### Verify Certificate Chain

**OpenSSL**:
```bash
# Verify certificate chain
openssl verify -CAfile root.pem -untrusted intermediate.pem cert.pem

# Extract certificate from signed binary
openssl pkcs7 -inform DER -in signature.p7s -print_certs -out cert.pem

# Check certificate validity
openssl x509 -in cert.pem -noout -dates
openssl x509 -in cert.pem -noout -subject -issuer
```

### Certificate Revocation

**Check revocation status**:

**CRL (Certificate Revocation List)**:
```bash
# Download CRL
wget http://crl.example.com/revoked.crl

# Check if certificate is revoked
openssl crl -inform DER -in revoked.crl -noout -text | grep -A1 "Serial Number"
```

**OCSP (Online Certificate Status Protocol)**:
```bash
# Query OCSP responder
openssl ocsp -issuer intermediate.pem \
    -cert cert.pem \
    -url http://ocsp.example.com \
    -CAfile root.pem
```

---

## HSM Integration

### Why Use HSM for Signing?

**Benefits**:
- Private keys never leave HSM (tamper-proof)
- FIPS 140-2 Level 3+ compliance
- Audit logging of all signing operations
- Prevents key extraction

### PKCS#11 Interface

**Sign with HSM (PKCS#11)**:
```python
from PyKCS11 import *

pkcs11 = PyKCS11Lib()
pkcs11.load('/usr/lib/softhsm/libsofthsm2.so')  # HSM library

# Open session
session = pkcs11.openSession(slot)
session.login('user_pin')

# Find signing key
key = session.findObjects([(CKA_CLASS, CKO_PRIVATE_KEY)])[0]

# Sign data
mechanism = Mechanism(CKM_RSA_PKCS, None)
signature = session.sign(key, data, mechanism)

session.logout()
```

**AWS CloudHSM**:
```bash
# Configure CloudHSM
/opt/cloudhsm/bin/configure -a <cluster-ip>

# Sign with pkcs11-tool
pkcs11-tool --module /opt/cloudhsm/lib/libcloudhsm_pkcs11.so \
    --login --pin <user-pin> \
    --sign --mechanism RSA-PKCS \
    --input-file data.bin \
    --output-file signature.bin
```

---

## Compliance

### FIPS 186-4 (Digital Signature Standard)

**Approved algorithms**:
- RSA-PSS (2048, 3072 bits)
- ECDSA (P-256, P-384, P-521)
- DSA (deprecated)

**Requirements**:
- Use FIPS-approved RNG for key generation
- Use SHA-256 or stronger for hashing
- Validate all signatures
- Protect private keys (HSM recommended)

### eIDAS (EU Electronic Identification and Trust Services)

**Signature levels**:
- **Simple**: Basic digital signature
- **Advanced**: Linked to signer, detects tampering
- **Qualified**: Equivalent to handwritten signature

**Requirements**:
- Qualified Trust Service Provider (QTSP)
- Qualified certificate
- Secure Signature Creation Device (SSCD)

### Common Criteria

**Evaluation Assurance Levels (EAL)**:
- EAL4+: Commercial applications
- EAL5+: High-security environments
- EAL7: Formal verification

---

## Best Practices

### 1. Signature Algorithm Selection

```bash
# ✅ Good: Modern, secure algorithms
EdDSA (Ed25519)
ECDSA P-256
RSA-PSS 3072+

# ❌ Bad: Deprecated or weak
RSA-PKCS#1 v1.5
DSA
MD5 hashing
```

### 2. Always Timestamp Signatures

```bash
# ✅ Good: Include timestamp
codesign --timestamp --sign "Developer ID" app.app
signtool sign /tr http://timestamp.digicert.com /td SHA256 app.exe

# ❌ Bad: No timestamp (signature expires with certificate)
codesign --sign "Developer ID" app.app
```

### 3. Verify Signatures Before Use

```bash
# ✅ Good: Always verify before execution
cosign verify --key cosign.pub image:tag
gpg --verify file.tar.gz.asc file.tar.gz

# ❌ Bad: Trust without verification
docker run unverified-image
tar -xzf unsigned-archive.tar.gz
```

### 4. Protect Private Keys

```bash
# ✅ Good: Use HSM, encrypted keys, access control
- Store signing keys in HSM
- Encrypt private keys (gpg, openssl)
- Require authentication for signing
- Audit all signing operations

# ❌ Bad: Unprotected keys
- Private key in Git repository
- Unencrypted key on disk
- Shared signing credentials
```

---

## Troubleshooting

### Issue 1: Signature Verification Fails

**Check**:
```bash
# Certificate expired?
openssl x509 -in cert.pem -noout -dates

# Wrong public key?
openssl x509 -in cert.pem -pubkey -noout > pubkey.pem

# Certificate revoked?
openssl ocsp -issuer ca.pem -cert cert.pem -url http://ocsp.example.com

# Data modified after signing?
sha256sum file.tar.gz  # Compare with original hash
```

### Issue 2: Code Signing Rejected by OS

**macOS Gatekeeper**:
```bash
# Check notarization status
spctl --assess --verbose=4 YourApp.app

# Check signature
codesign --verify --deep --strict --verbose=2 YourApp.app
```

**Windows SmartScreen**:
```bash
# Verify certificate chain
signtool verify /pa /v application.exe

# Check timestamp
signtool verify /pa /tw application.exe
```

---

## Related Skills

- `cryptography-key-management` - Managing signing keys
- `cryptography-certificate-management` - Certificate lifecycle
- `cryptography-pki-fundamentals` - PKI and trust chains
- `cryptography-crypto-best-practices` - Cryptographic guidelines

---

## Level 3: Resources

**Location**: `/Users/rand/src/cc-polymath/skills/cryptography/signing-verification/resources/`

This skill includes comprehensive Level 3 resources for production signing and verification implementations.

### REFERENCE.md (~3,500 lines)

Comprehensive technical reference covering:
- **Digital Signature Fundamentals**: Cryptographic primitives, hash-then-sign, signature schemes
- **Signature Algorithms**: RSA-PSS, ECDSA, EdDSA, algorithm comparison, security analysis
- **Signature Formats**: PKCS#7/CMS, JWS, XML-DSig, detached vs embedded, format conversion
- **Code Signing Platforms**: Apple (macOS/iOS), Microsoft (Authenticode), Android (APK), Java (JAR)
- **Container Signing**: Sigstore architecture, cosign usage, keyless signing, Rekor transparency
- **GPG/PGP**: Key management, signing workflows, web of trust, Git integration
- **Timestamping**: RFC 3161 protocol, timestamp authorities, long-term verification
- **Certificate Chains**: Trust models, chain validation, revocation (CRL/OCSP)
- **HSM Integration**: PKCS#11, CloudHSM, YubiHSM, key protection
- **Compliance**: FIPS 186-4, eIDAS, Common Criteria, industry requirements
- **Security Best Practices**: Key protection, algorithm selection, signature verification
- **Attack Vectors**: Signature forgery, key compromise, replay attacks, timing attacks
- **Real-world implementations**: Production examples, integration patterns

### Scripts (3 production-ready tools)

**validate_signatures.py** (650+ lines) - Multi-format signature validator
- Validates PKCS#7, CMS, JWS, XML-DSig signatures
- Certificate chain verification and revocation checking (OCSP/CRL)
- Supports RSA-PSS, ECDSA, EdDSA algorithms
- Timestamp validation (RFC 3161)
- Batch validation from file lists
- Compliance checking (FIPS 186-4, eIDAS)
- JSON output for automation
- Detailed reporting with severity levels
- Usage: `./validate_signatures.py --file document.p7s --check-revocation --json`

**sign_artifacts.py** (750+ lines) - Universal artifact signing tool
- Signs files, code, containers with RSA/ECDSA/EdDSA
- Supports multiple backends: local keys, AWS KMS, CloudHSM, PKCS#11
- Generates detached and embedded signatures
- Timestamp integration with configurable TSAs
- Batch signing with progress tracking
- HSM integration for key protection
- Multiple output formats (PKCS#7, JWS, raw signatures)
- Pre/post signing hooks
- Usage: `./sign_artifacts.py --file app.tar.gz --key signing.key --format pkcs7 --timestamp --json`

**audit_signing_keys.py** (600+ lines) - Signing key lifecycle auditor
- Audits signing key usage and access patterns
- Detects weak algorithms (RSA-1024, SHA-1, DSA)
- Tracks key lifecycle (creation, expiration, rotation)
- Identifies expiring keys with configurable thresholds
- Certificate validation and chain verification
- Compliance checking (FIPS 186-4, algorithm requirements)
- Usage metrics and anomaly detection
- JSON reporting for monitoring integration
- Usage: `./audit_signing_keys.py --keystore ./keys --compliance FIPS --threshold-warning 90 --json`

### Examples (8 production-ready implementations)

**python/rsa_pss_signing.py** - RSA-PSS document signing
- RSA-PSS signature generation and verification
- PKCS#1 PSS padding scheme
- Multiple hash algorithms (SHA-256, SHA-384, SHA-512)
- Key generation and management
- PEM/DER format handling
- Compliance with FIPS 186-4

**python/ecdsa_signing.py** - ECDSA code signing with verification
- ECDSA signing with P-256, P-384, P-521 curves
- Signature generation and verification
- Key serialization (PEM, DER, JWK)
- Multiple signature formats
- Nonce generation best practices

**go/ed25519_artifacts.go** - EdDSA artifact signing
- Ed25519 signing and verification
- High-performance implementation
- Batch signing support
- Detached signature generation
- JSON metadata integration

**python/sigstore_cosign.py** - Sigstore cosign integration
- Keyless signing with OIDC
- Key-based signing with cosign
- Container image verification
- Rekor transparency log integration
- Policy enforcement

**python/hsm_signing.py** - HSM-backed signing (PKCS#11)
- PKCS#11 interface for HSM integration
- SoftHSM, CloudHSM, YubiHSM support
- RSA and ECDSA signing via HSM
- Key generation in HSM
- Session management and error handling

**python/timestamp_authority.py** - Timestamp authority integration
- RFC 3161 timestamp requests
- TSA client implementation
- Timestamp verification
- Multiple TSA support (DigiCert, Sectigo, FreeTSA)
- Long-term signature validation

**docker-compose/signing-infrastructure.yml** - Container signing infrastructure
- Sigstore stack (Fulcio, Rekor, Cosign)
- Private timestamp authority
- Certificate authority setup
- HSM simulator (SoftHSM)
- Complete signing pipeline

**config/compliance-validation.yaml** - Compliance policy configuration
- FIPS 186-4 algorithm policies
- eIDAS signature level requirements
- Key strength requirements
- Certificate validation rules
- Audit logging configuration

### Quick Start

```bash
# Validate signature
cd /Users/rand/src/cc-polymath/skills/cryptography/signing-verification/resources/scripts
./validate_signatures.py --file document.p7s --check-chain --check-revocation

# Sign artifact with timestamp
./sign_artifacts.py --file release.tar.gz --key signing.key --timestamp --format pkcs7

# Audit signing keys
./audit_signing_keys.py --keystore /etc/pki/signing --compliance FIPS --json

# Run Python examples
cd ../examples/python
pip install cryptography PyKCS11 jwt sigstore
python rsa_pss_signing.py sign document.txt
python ecdsa_signing.py verify signature.bin
python sigstore_cosign.py keyless-sign myimage:v1.0.0

# View comprehensive reference
cd ../
less REFERENCE.md
```

### Integration Notes

**CI/CD Integration**:
```yaml
# .github/workflows/sign-release.yml
- name: Sign Release Artifacts
  run: |
    ./scripts/sign_artifacts.py \
      --batch-file artifacts.txt \
      --key ${{ secrets.SIGNING_KEY }} \
      --timestamp \
      --json
```

**Verification in Deployment**:
```bash
# Verify signatures before deployment
./scripts/validate_signatures.py \
  --batch-file production-artifacts.txt \
  --check-revocation \
  --compliance FIPS \
  --fail-on-error
```

---

## Quick Reference

```bash
# OpenSSL signing
openssl dgst -sha256 -sign private.key -out signature.bin file.txt
openssl dgst -sha256 -verify public.key -signature signature.bin file.txt

# GPG signing
gpg --detach-sign --armor file.tar.gz
gpg --verify file.tar.gz.asc file.tar.gz

# Cosign (container)
cosign sign --key cosign.key image:tag
cosign verify --key cosign.pub image:tag

# Code signing (macOS)
codesign --sign "Developer ID" --timestamp app.app
codesign --verify --verbose=4 app.app

# Code signing (Windows)
signtool sign /f cert.pfx /p password /tr http://timestamp.digicert.com /td SHA256 app.exe
signtool verify /pa app.exe
```

---

**Last Updated**: 2025-10-27
