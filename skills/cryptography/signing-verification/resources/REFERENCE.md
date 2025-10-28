# Digital Signature and Verification Reference

Comprehensive reference for digital signature algorithms, signing workflows, verification procedures, key management, code signing platforms, timestamping, HSM integration, and compliance standards.

**Version**: 1.0.0
**Last Updated**: 2025-01-27
**Skill**: cryptography/signing-verification

---

## Table of Contents

1. [Digital Signature Fundamentals](#1-digital-signature-fundamentals)
2. [Signature Algorithms](#2-signature-algorithms)
3. [Signing Workflows](#3-signing-workflows)
4. [Verification Procedures](#4-verification-procedures)
5. [Key Management](#5-key-management)
6. [Code Signing Platforms](#6-code-signing-platforms)
7. [Timestamping (RFC 3161)](#7-timestamping-rfc-3161)
8. [HSM Integration](#8-hsm-integration)
9. [File Formats](#9-file-formats)
10. [Standards and Compliance](#10-standards-and-compliance)
11. [Security Best Practices](#11-security-best-practices)
12. [Troubleshooting](#12-troubleshooting)
13. [Tools and Libraries](#13-tools-and-libraries)
14. [References](#14-references)

---

## 1. Digital Signature Fundamentals

### 1.1 What are Digital Signatures?

Digital signatures provide:

- **Authentication**: Verifies the identity of the signer
- **Integrity**: Ensures data hasn't been modified
- **Non-repudiation**: Signer cannot deny having signed

Unlike encryption (which provides confidentiality), signatures focus on authenticity and integrity.

### 1.2 How Digital Signatures Work

**Signing Process**:
```
1. Hash the message: H = Hash(Message)
2. Sign the hash: Signature = Sign(H, PrivateKey)
3. Distribute: (Message, Signature, PublicKey/Certificate)
```

**Verification Process**:
```
1. Hash the received message: H' = Hash(Message)
2. Decrypt signature: H'' = Verify(Signature, PublicKey)
3. Compare: H' == H'' → Valid signature
```

### 1.3 Signature vs. MAC

| Feature | Digital Signature | MAC (Message Authentication Code) |
|---------|------------------|-----------------------------------|
| Keys | Asymmetric (public/private) | Symmetric (shared secret) |
| Authentication | Signer identity | Message authenticity |
| Non-repudiation | Yes | No |
| Use case | Code signing, documents | Network protocols, APIs |

### 1.4 Security Properties

**Unforgeability**: Attacker cannot create valid signatures without private key

**Collision Resistance**: Cannot find two messages with same signature

**Key Security**: Private key must remain confidential

**Algorithm Security**: Must use approved algorithms with adequate key sizes

---

## 2. Signature Algorithms

### 2.1 RSA (Rivest-Shamir-Adleman)

#### RSA-PKCS#1 v1.5

**Description**: Original RSA signature scheme with PKCS#1 v1.5 padding

**Key Sizes**: 2048, 3072, 4096 bits

**Status**: Legacy, avoid for new applications (vulnerable to padding oracle attacks)

**Use Cases**: Legacy system compatibility only

**Example**:
```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
signature = private_key.sign(
    data,
    padding.PKCS1v15(),
    hashes.SHA256()
)
```

#### RSA-PSS (Probabilistic Signature Scheme)

**Description**: Modern RSA signature scheme with PSS padding (PKCS#1 v2.1)

**Key Sizes**:
- 2048 bits: Minimum for current use
- 3072 bits: Recommended for medium-term security (2030+)
- 4096 bits: Long-term security

**Hash Algorithms**: SHA-256, SHA-384, SHA-512

**Advantages**:
- Provable security (tight security reduction)
- Randomized padding (different signatures for same message)
- No known attacks with proper parameters

**Disadvantages**:
- Larger signature size (same as key size)
- Slower than ECDSA/EdDSA
- Larger key size than elliptic curves

**Parameters**:
```python
# Recommended PSS parameters
signature = private_key.sign(
    data,
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),  # Mask generation function
        salt_length=padding.PSS.MAX_LENGTH  # Maximum salt length (recommended)
    ),
    hashes.SHA256()
)
```

**Security Levels**:
| Key Size | Security Level | Valid Until |
|----------|---------------|-------------|
| 2048 bit | 112 bits | 2030 |
| 3072 bit | 128 bits | 2050+ |
| 4096 bit | 128+ bits | Long-term |

**Performance**: ~10-100x slower than ECDSA/EdDSA

### 2.2 ECDSA (Elliptic Curve Digital Signature Algorithm)

**Description**: Signature algorithm based on elliptic curve cryptography

**Approved Curves** (NIST/FIPS 186-4):
- **P-256** (secp256r1): 128-bit security, widely supported
- **P-384** (secp384r1): 192-bit security, high security
- **P-521** (secp521r1): 256-bit security, maximum security

**Hash Algorithm Pairing**:
| Curve | Recommended Hash |
|-------|-----------------|
| P-256 | SHA-256 |
| P-384 | SHA-384 |
| P-521 | SHA-512 |

**Advantages**:
- Smaller key size (256 bits vs 2048 bits RSA)
- Smaller signature size (512 bits vs 2048 bits RSA)
- Faster signing and verification than RSA
- Lower bandwidth and storage requirements

**Disadvantages**:
- Requires careful nonce generation (k must be unique and random)
- Vulnerable to side-channel attacks (timing, power analysis)
- Deterministic ECDSA (RFC 6979) recommended to avoid nonce issues

**Example**:
```python
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

private_key = ec.generate_private_key(ec.SECP256R1())
signature = private_key.sign(
    data,
    ec.ECDSA(hashes.SHA256())
)
```

**Deterministic ECDSA (RFC 6979)**:
- Nonce derived from message and private key
- Eliminates random number generation vulnerabilities
- Recommended for most applications

**Performance**: ~10x faster than RSA-2048

### 2.3 EdDSA (Edwards-curve Digital Signature Algorithm)

#### Ed25519

**Description**: Modern signature algorithm using Curve25519 (twisted Edwards curve)

**Key Size**: 256 bits (fixed)

**Signature Size**: 512 bits (64 bytes)

**Security Level**: ~128 bits

**Advantages**:
- **Fast**: 10-100x faster than RSA, 2-5x faster than ECDSA
- **Simple**: No parameter choices, deterministic
- **Secure**: Designed to avoid side-channel attacks
- **Small**: Compact keys and signatures
- **No random nonce required**: Deterministic by design

**Disadvantages**:
- Less widely supported than RSA/ECDSA (improving rapidly)
- Not FIPS 186-4 approved (but widely used)
- Fixed security level (no higher-security option like Ed448)

**Example**:
```python
from cryptography.hazmat.primitives.asymmetric import ed25519

private_key = ed25519.Ed25519PrivateKey.generate()
signature = private_key.sign(data)  # That's it - no algorithm parameters!
```

**Use Cases**:
- High-throughput signing (APIs, blockchain)
- Embedded systems (small code size)
- Modern applications without legacy constraints

**Performance Comparison**:
```
Ed25519:     ~50,000 signatures/second
ECDSA P-256: ~10,000 signatures/second
RSA-2048:    ~1,000 signatures/second
```

#### Ed448

**Description**: High-security variant using Curve448

**Key Size**: 456 bits

**Signature Size**: 912 bits

**Security Level**: ~224 bits

**Use Cases**: High-security applications requiring >128-bit security

### 2.4 DSA (Digital Signature Algorithm)

**Status**: **DEPRECATED** - Do not use for new applications

**Replacement**: Use ECDSA or EdDSA instead

**Reasons for Deprecation**:
- Similar performance to ECDSA but larger keys
- Nonce generation vulnerabilities (same as ECDSA)
- No advantage over ECDSA
- FIPS 186-5 removes DSA

### 2.5 Algorithm Selection Guide

**Choose RSA-PSS when**:
- Legacy system compatibility required
- FIPS 140-2 compliance mandatory
- Long-term archival (>20 years)
- Maximum compatibility needed

**Choose ECDSA P-256 when**:
- General-purpose signing
- FIPS compliance required
- Moderate performance needed
- Wide compatibility important

**Choose ECDSA P-384 when**:
- High-security applications
- Suite B compliance required
- Government/military use
- Long-term security (>2050)

**Choose Ed25519 when**:
- Modern applications
- High performance critical
- Simplicity valued
- Mobile/embedded systems

**Quick Reference**:
| Algorithm | Key Size | Sig Size | Speed | Security | Compatibility |
|-----------|----------|----------|-------|----------|---------------|
| RSA-2048  | 2048 b   | 2048 b   | ⭐     | ⭐⭐⭐     | ⭐⭐⭐⭐⭐      |
| RSA-3072  | 3072 b   | 3072 b   | ⭐     | ⭐⭐⭐⭐    | ⭐⭐⭐⭐       |
| ECDSA P-256 | 256 b  | 512 b    | ⭐⭐⭐⭐ | ⭐⭐⭐     | ⭐⭐⭐⭐       |
| ECDSA P-384 | 384 b  | 768 b    | ⭐⭐⭐  | ⭐⭐⭐⭐⭐   | ⭐⭐⭐        |
| Ed25519   | 256 b    | 512 b    | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐    | ⭐⭐⭐        |

---

## 3. Signing Workflows

### 3.1 Document Signing

**Purpose**: Sign documents (PDF, Word, text) for authenticity and integrity

**Workflow**:
```
1. Prepare document
2. Compute document hash (SHA-256 or stronger)
3. Sign hash with private key
4. Attach signature (embedded or detached)
5. Optional: Add timestamp
6. Distribute (document + signature)
```

**Formats**:
- **PDF**: PAdES (PDF Advanced Electronic Signatures)
- **Office**: OOXML signatures (Word, Excel, PowerPoint)
- **XML**: XAdES (XML Advanced Electronic Signatures)
- **General**: PKCS#7/CMS detached signatures

**Example - PDF Signing**:
```python
# Using pypdf for basic PDF signing
from pypdf import PdfReader, PdfWriter
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

# Sign PDF (simplified - production should use proper PDF signature format)
pdf_data = Path("document.pdf").read_bytes()
signature = private_key.sign(pdf_data, padding.PSS(...), hashes.SHA256())

# In production, use libraries like:
# - pyHanko for PDF signing
# - Adobe Acrobat SDK
# - iText (Java)
```

**Best Practices**:
- Use PAdES-B for basic signatures
- Use PAdES-T for timestamps
- Use PAdES-LT for long-term validation
- Include visible signature appearance
- Store original unsigned document

### 3.2 Code Signing

**Purpose**: Sign executables, libraries, scripts to verify publisher and integrity

**Workflow**:
```
1. Build code artifact
2. Sign binary/package
3. Optional: Timestamp signature
4. Publish with signature
5. Users verify before execution
```

**Platform-Specific**:

**Windows (Authenticode)**:
```powershell
# Sign with SignTool
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com myapp.exe
```

**macOS (codesign)**:
```bash
# Sign application
codesign --sign "Developer ID Application: Company" --timestamp MyApp.app

# Verify signature
codesign --verify --deep --strict --verbose=2 MyApp.app
spctl --assess --verbose=4 MyApp.app
```

**Linux (GPG/RPM/DEB)**:
```bash
# Sign with GPG
gpg --detach-sign --armor program.tar.gz

# Verify
gpg --verify program.tar.gz.asc program.tar.gz
```

**Java (jarsigner)**:
```bash
# Sign JAR
jarsigner -keystore keystore.jks -signedjar signed.jar unsigned.jar alias

# Verify
jarsigner -verify -verbose signed.jar
```

**Best Practices**:
- Use EV (Extended Validation) certificates when possible
- Always timestamp signatures
- Sign all distributable code
- Verify signatures in CI/CD
- Rotate signing certificates annually

### 3.3 Artifact Signing

**Purpose**: Sign build artifacts, containers, packages for supply chain security

**Workflow**:
```
1. Build artifact (container, package, binary)
2. Generate artifact hash/digest
3. Sign hash with private key
4. Upload signature to registry/repository
5. CI/CD verifies signatures
6. Deployment verifies signatures
```

**Container Signing (Docker/OCI)**:

**Sigstore Cosign**:
```bash
# Generate key
cosign generate-key-pair

# Sign image
cosign sign --key cosign.key registry.io/image:tag

# Verify
cosign verify --key cosign.pub registry.io/image:tag

# Keyless signing (OIDC)
cosign sign registry.io/image:tag  # Opens browser for auth
```

**Docker Content Trust (Notary)**:
```bash
# Enable content trust
export DOCKER_CONTENT_TRUST=1

# Push (automatically signs)
docker push registry.io/image:tag

# Pull (automatically verifies)
docker pull registry.io/image:tag
```

**Package Signing**:

**NPM**:
```bash
# Sign package
npm pack
npm sign package-1.0.0.tgz

# Verify
npm audit signatures
```

**PyPI**:
```bash
# Sign with GPG
gpg --detach-sign --armor dist/package-1.0.0.tar.gz

# Upload with signature
twine upload dist/package-1.0.0.tar.gz dist/package-1.0.0.tar.gz.asc
```

**Best Practices**:
- Sign all artifacts in CI/CD
- Store signatures in registry metadata
- Verify signatures before deployment
- Use transparency logs (Rekor)
- Implement admission controllers

### 3.4 Git Commit Signing

**Purpose**: Sign git commits and tags for authenticity

**Setup**:
```bash
# Generate GPG key
gpg --gen-key

# Configure git
git config --global user.signingkey KEYID
git config --global commit.gpgsign true
git config --global tag.gpgsign true
```

**Signing**:
```bash
# Sign commit
git commit -S -m "Signed commit"

# Sign tag
git tag -s v1.0.0 -m "Signed release"

# Verify commit
git verify-commit HEAD

# Verify tag
git verify-tag v1.0.0
```

**GitHub/GitLab Integration**:
- Upload GPG public key to profile
- Commits show "Verified" badge
- Protect branches requiring signed commits

**Best Practices**:
- Require signed commits for protected branches
- Sign all release tags
- Rotate GPG keys annually
- Backup private keys securely
- Document key rotation process

### 3.5 Batch Signing

**Purpose**: Sign multiple files efficiently

**Strategies**:

**Parallel Signing**:
```python
from concurrent.futures import ThreadPoolExecutor

def sign_file(file_path):
    data = file_path.read_bytes()
    signature = private_key.sign(data, ...)
    return signature

with ThreadPoolExecutor(max_workers=8) as executor:
    signatures = executor.map(sign_file, file_list)
```

**Manifest Signing**:
```python
# Instead of signing each file, sign a manifest
manifest = {
    'files': {
        'file1.bin': 'sha256:abc123...',
        'file2.bin': 'sha256:def456...',
    },
    'timestamp': '2025-01-27T12:00:00Z'
}

manifest_json = json.dumps(manifest, sort_keys=True)
signature = sign(manifest_json.encode())
```

**Best Practices**:
- Use manifest signing for large file sets
- Implement rate limiting for HSM signing
- Cache signatures when possible
- Monitor signing throughput
- Use async I/O for network operations

---

## 4. Verification Procedures

### 4.1 Basic Signature Verification

**Steps**:
```
1. Extract signature from file/message
2. Extract or retrieve public key/certificate
3. Compute hash of signed data
4. Verify signature using public key
5. Check signature algorithm matches expected
6. Validate result
```

**Example**:
```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

try:
    public_key.verify(
        signature,
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    print("✓ Signature valid")
except InvalidSignature:
    print("✗ Signature invalid")
```

### 4.2 Certificate Chain Verification

**Purpose**: Verify certificate chain from signer to trusted root

**Steps**:
```
1. Extract signer certificate
2. Verify certificate signature by issuer
3. Repeat for each certificate in chain
4. Verify root certificate is in trust store
5. Check certificate validity periods
6. Verify certificate is not revoked
```

**Example**:
```python
def verify_certificate_chain(cert, intermediates, trust_anchors):
    """Verify certificate chain"""

    # Build chain
    chain = [cert] + intermediates

    # Verify each certificate signed by next in chain
    for i in range(len(chain) - 1):
        cert = chain[i]
        issuer_cert = chain[i + 1]

        # Verify signature
        try:
            issuer_cert.public_key().verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm
            )
        except InvalidSignature:
            return False, "Certificate signature invalid"

        # Check validity period
        now = datetime.now(timezone.utc)
        if now < cert.not_valid_before_utc:
            return False, "Certificate not yet valid"
        if now > cert.not_valid_after_utc:
            return False, "Certificate expired"

    # Verify root in trust anchors
    root = chain[-1]
    if root not in trust_anchors:
        return False, "Root certificate not trusted"

    return True, "Chain valid"
```

**Best Practices**:
- Always verify complete chain
- Check certificate extensions (Key Usage, Extended Key Usage)
- Verify name constraints
- Check certificate policies
- Validate path length constraints

### 4.3 Revocation Checking

**Purpose**: Verify certificate has not been revoked

**Methods**:

**CRL (Certificate Revocation List)**:
```python
def check_crl(cert):
    """Check if certificate is revoked via CRL"""

    # Extract CRL distribution points
    try:
        cdp_ext = cert.extensions.get_extension_for_oid(
            ExtensionOID.CRL_DISTRIBUTION_POINTS
        )
    except x509.ExtensionNotFound:
        return "unknown"  # No CRL endpoints

    # Download CRL
    for dp in cdp_ext.value:
        if dp.full_name:
            for name in dp.full_name:
                if isinstance(name, x509.UniformResourceIdentifier):
                    crl_url = name.value

                    # Download CRL
                    response = requests.get(crl_url)
                    crl = x509.load_der_x509_crl(response.content)

                    # Check if certificate is revoked
                    for revoked_cert in crl:
                        if revoked_cert.serial_number == cert.serial_number:
                            return "revoked"

    return "valid"
```

**OCSP (Online Certificate Status Protocol)**:
```python
def check_ocsp(cert, issuer_cert):
    """Check certificate status via OCSP"""

    # Extract OCSP responder URL
    try:
        aia = cert.extensions.get_extension_for_oid(
            ExtensionOID.AUTHORITY_INFORMATION_ACCESS
        )
        ocsp_url = None
        for desc in aia.value:
            if desc.access_method == x509.oid.AuthorityInformationAccessOID.OCSP:
                ocsp_url = desc.access_location.value
                break
    except x509.ExtensionNotFound:
        return "unknown"

    if not ocsp_url:
        return "unknown"

    # Build OCSP request
    builder = ocsp.OCSPRequestBuilder()
    builder = builder.add_certificate(cert, issuer_cert, hashes.SHA256())
    req = builder.build()

    # Send OCSP request
    response = requests.post(
        ocsp_url,
        data=req.public_bytes(serialization.Encoding.DER),
        headers={'Content-Type': 'application/ocsp-request'}
    )

    # Parse response
    ocsp_response = ocsp.load_der_ocsp_response(response.content)

    if ocsp_response.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL:
        if ocsp_response.certificate_status == ocsp.OCSPCertStatus.GOOD:
            return "valid"
        elif ocsp_response.certificate_status == ocsp.OCSPCertStatus.REVOKED:
            return "revoked"

    return "unknown"
```

**Comparison**:
| Method | Latency | Privacy | Freshness | Overhead |
|--------|---------|---------|-----------|----------|
| CRL    | Low (cached) | Good | Hours | Large downloads |
| OCSP   | Medium | Poor (leaks cert) | Real-time | Per-cert request |
| OCSP Stapling | Low | Good | Minutes | Minimal |

**Best Practices**:
- Prefer OCSP for real-time verification
- Use CRL as fallback
- Implement caching for CRLs
- Use OCSP stapling when possible
- Set reasonable timeouts (5-10 seconds)
- Handle "unknown" status appropriately

### 4.4 Timestamp Verification

**Purpose**: Verify signature was created at claimed time

**Steps**:
```
1. Extract timestamp token from signature
2. Verify timestamp signature
3. Verify timestamp authority certificate
4. Extract timestamp value
5. Check timestamp is within acceptable range
6. Verify message imprint matches signed data
```

**Example**:
```python
def verify_timestamp(timestamp_token, signed_data):
    """Verify RFC 3161 timestamp"""

    # Parse timestamp token (simplified - use ASN.1 library in production)
    # TimeStampToken ::= ContentInfo (SignedData)

    # 1. Verify timestamp signature
    # timestamp_signature = verify_cms_signature(timestamp_token)

    # 2. Verify TSA certificate
    # tsa_cert = extract_certificate(timestamp_token)
    # verify_certificate_chain(tsa_cert, ...)

    # 3. Extract timestamp value
    # timestamp = extract_timestamp(timestamp_token)

    # 4. Verify message imprint
    # message_imprint = extract_message_imprint(timestamp_token)
    # expected_imprint = hash(signed_data)
    # if message_imprint != expected_imprint:
    #     return False

    # 5. Check timestamp in valid range
    # now = datetime.now(timezone.utc)
    # if timestamp > now + timedelta(minutes=5):  # Clock skew tolerance
    #     return False

    return True
```

**Best Practices**:
- Always verify timestamp signature
- Verify TSA certificate chain
- Check timestamp is reasonable (not future, not too old)
- Verify message imprint matches
- Store timestamp with signature
- Use qualified TSAs for legal validity

### 4.5 Policy-Based Verification

**Purpose**: Enforce organizational signature policies

**Example Policy**:
```yaml
signature_policy:
  allowed_algorithms:
    - RSA-PSS-2048
    - RSA-PSS-3072
    - ECDSA-P256
    - ECDSA-P384
    - Ed25519

  required_properties:
    - certificate_chain_valid
    - not_revoked
    - timestamp_present
    - timestamp_valid

  certificate_requirements:
    key_usage:
      - digitalSignature
    extended_key_usage:
      - codeSigning
    issuer_whitelist:
      - "CN=Corporate CA"

  expiration_warnings:
    certificate_days: 30
    timestamp_years: 5
```

**Implementation**:
```python
class SignaturePolicy:
    """Enforce signature verification policies"""

    def __init__(self, policy_config):
        self.policy = policy_config

    def verify(self, signature_bundle):
        """Verify signature against policy"""
        violations = []

        # Check algorithm
        if signature_bundle.algorithm not in self.policy['allowed_algorithms']:
            violations.append(f"Algorithm {signature_bundle.algorithm} not allowed")

        # Check certificate
        cert = signature_bundle.certificate
        if 'digitalSignature' not in cert.key_usage:
            violations.append("Certificate lacks digitalSignature key usage")

        # Check expiration
        days_until_expiry = (cert.not_after - datetime.now()).days
        if days_until_expiry < self.policy['expiration_warnings']['certificate_days']:
            violations.append(f"Certificate expires in {days_until_expiry} days")

        # Check timestamp
        if 'timestamp_present' in self.policy['required_properties']:
            if not signature_bundle.timestamp:
                violations.append("Timestamp required but not present")

        return len(violations) == 0, violations
```

---

## 5. Key Management

### 5.1 Key Generation

**Requirements**:
- Use cryptographically secure random number generator (CSPRNG)
- Generate keys in secure environment (HSM preferred)
- Document key generation ceremony
- Store offline backup securely

**RSA Key Generation**:
```python
from cryptography.hazmat.primitives.asymmetric import rsa

private_key = rsa.generate_private_key(
    public_exponent=65537,  # Standard exponent
    key_size=3072,          # 3072 recommended, 4096 for long-term
)
```

**ECDSA Key Generation**:
```python
from cryptography.hazmat.primitives.asymmetric import ec

private_key = ec.generate_private_key(
    ec.SECP384R1()  # P-384 for high security
)
```

**Ed25519 Key Generation**:
```python
from cryptography.hazmat.primitives.asymmetric import ed25519

private_key = ed25519.Ed25519PrivateKey.generate()
```

**HSM Key Generation** (recommended for production):
```python
# Using PKCS#11
public_key, private_key = session.generate_keypair(
    KeyType.RSA,
    3072,
    label="code-signing-2025",
    store=True,  # Persist in HSM
    capabilities=(
        MechanismFlag.VERIFY,  # Public key
        MechanismFlag.SIGN,    # Private key
    )
)
```

**Best Practices**:
- Use 3072-bit RSA or P-384 ECDSA for new keys
- Generate keys in HSM when possible
- Never generate keys on untrusted systems
- Use key generation ceremonies for critical keys
- Document key generation parameters
- Test key immediately after generation

### 5.2 Key Storage

**Private Key Storage Options**:

| Storage | Security | Accessibility | Cost | Use Case |
|---------|----------|---------------|------|----------|
| HSM | Highest | Limited | High | Production signing |
| Cloud KMS | High | Good | Medium | Cloud workloads |
| Encrypted file | Medium | Good | Low | Development |
| Smart card | High | Limited | Low | Personal signing |
| Memory only | Low | Immediate | Low | Temporary/testing |

**HSM Storage** (recommended):
```
- FIPS 140-2 Level 2+ certified
- Keys never leave HSM
- Tamper-resistant hardware
- Audit logging
- Role-based access control
```

**Encrypted File Storage**:
```python
# Encrypt private key with password
from cryptography.hazmat.primitives import serialization

encrypted_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.BestAvailableEncryption(
        password.encode()
    )
)

Path("private_key.pem").write_bytes(encrypted_pem)
# Set restrictive permissions
os.chmod("private_key.pem", 0o600)
```

**Cloud KMS**:
```python
# AWS KMS example
import boto3

kms = boto3.client('kms')

# Sign with KMS key
response = kms.sign(
    KeyId='arn:aws:kms:...',
    Message=data,
    SigningAlgorithm='ECDSA_SHA_256'
)
signature = response['Signature']
```

**Best Practices**:
- Never store private keys in version control
- Use HSMs for production signing keys
- Encrypt private keys at rest
- Set restrictive file permissions (0600)
- Use separate keys for different purposes
- Implement key access auditing

### 5.3 Key Rotation

**Purpose**: Limit exposure of compromised keys

**Rotation Schedule**:
| Key Type | Rotation Frequency | Reason |
|----------|-------------------|---------|
| Code signing | 1 year | Limit compromise window |
| Document signing | 2 years | Balance security/convenience |
| Root CA | 10+ years | Stability required |
| Intermediate CA | 5 years | Balance security/stability |

**Rotation Process**:
```
1. Generate new key pair
2. Obtain new certificate
3. Begin signing with new key
4. Continue accepting old key for verification (grace period)
5. After grace period, retire old key
6. Securely destroy old key
```

**Graceful Key Rollover**:
```python
class SigningKeyManager:
    """Manage multiple signing keys with rollover"""

    def __init__(self):
        self.current_key = None
        self.previous_keys = []

    def rotate_key(self, new_key):
        """Rotate to new signing key"""
        if self.current_key:
            self.previous_keys.append({
                'key': self.current_key,
                'retired_at': datetime.now(timezone.utc),
                'valid_for_verification': True
            })
        self.current_key = new_key

    def sign(self, data):
        """Sign with current key"""
        return self.current_key.sign(data)

    def verify(self, data, signature):
        """Verify with current or previous keys"""
        # Try current key
        if self.current_key.verify(data, signature):
            return True

        # Try previous keys (during grace period)
        for key_info in self.previous_keys:
            if key_info['valid_for_verification']:
                if key_info['key'].verify(data, signature):
                    return True

        return False
```

**Best Practices**:
- Rotate annually for code signing keys
- Maintain 30-90 day grace period
- Keep old keys for signature verification
- Document rotation procedures
- Test rotation process regularly
- Automate rotation when possible

### 5.4 Key Backup and Recovery

**Backup Strategy**:
```
1. Offline backup of root keys (HSM backup token)
2. Split knowledge (M-of-N)
3. Geographic distribution
4. Encrypted backup storage
5. Regular recovery testing
```

**Split Knowledge (Shamir's Secret Sharing)**:
```python
# Example: 3-of-5 split
# Key split into 5 shares, any 3 can reconstruct

from cryptography.hazmat.primitives import serialization

# In production, use proper secret sharing library
# This is conceptual only
def split_key(private_key, threshold=3, shares=5):
    """Split private key using secret sharing"""
    # Export key
    key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Split using Shamir's Secret Sharing
    # shares = shamir_split(key_bytes, threshold, shares)

    return shares
```

**Recovery Testing**:
```bash
# Quarterly recovery test procedure
1. Retrieve backup from secure storage
2. Attempt key reconstruction
3. Verify key works for signing
4. Document results
5. Return backup to storage
```

**Best Practices**:
- Use M-of-N split for critical keys
- Store shares in separate locations
- Test recovery quarterly
- Document recovery procedures
- Use tamper-evident storage
- Maintain custody chain

### 5.5 Key Destruction

**Purpose**: Securely destroy keys at end of life

**Destruction Methods**:
```
1. HSM: Zeroize key storage
2. File: Secure delete (overwrite multiple times)
3. Media: Physical destruction (shredding, degaussing)
4. Memory: Zero out key material
```

**Secure Deletion**:
```python
def secure_delete_key(key_path, passes=7):
    """Securely delete key file"""

    # Get file size
    size = key_path.stat().st_size

    # Overwrite with random data
    with open(key_path, 'wb') as f:
        for _ in range(passes):
            f.seek(0)
            f.write(os.urandom(size))
            f.flush()
            os.fsync(f.fileno())

    # Delete file
    key_path.unlink()
```

**Best Practices**:
- Document destruction date and method
- Overwrite key material before deletion
- Physically destroy backup media
- Update key inventory
- Revoke associated certificates
- Maintain destruction audit log

---

## 6. Code Signing Platforms

### 6.1 Sigstore (Cosign, Fulcio, Rekor)

**Description**: Modern, keyless signing infrastructure

**Components**:
- **Cosign**: Container/artifact signing tool
- **Fulcio**: Certificate authority (OIDC-based)
- **Rekor**: Transparency log
- **Gitsign**: Git commit signing

**Keyless Signing Flow**:
```
1. User runs: cosign sign IMAGE
2. Opens browser for OIDC authentication (GitHub/Google/Microsoft)
3. Fulcio issues ephemeral certificate
4. Cosign signs with ephemeral key
5. Signature uploaded to Rekor transparency log
6. Ephemeral key discarded
```

**Advantages**:
- No key management (ephemeral keys)
- Identity from OIDC provider
- Transparency via Rekor
- Free for public use

**Example**:
```bash
# Keyless signing
cosign sign registry.io/image:tag

# Verification (identity-based)
cosign verify \
  --certificate-identity-regexp "^https://github.com/username/*" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  registry.io/image:tag

# Key-based signing (traditional)
cosign generate-key-pair
cosign sign --key cosign.key registry.io/image:tag
cosign verify --key cosign.pub registry.io/image:tag
```

**Best Practices**:
- Use keyless for public projects
- Use key-based for enterprise (with HSM)
- Always verify transparency log entries
- Implement admission controller policies
- Use SBOM attestations

### 6.2 Apple Codesign

**Description**: macOS/iOS code signing

**Requirements**:
- Apple Developer account
- Developer ID certificate
- Notarization for distribution

**Signing**:
```bash
# Sign application
codesign --sign "Developer ID Application: Company Name" \
         --timestamp \
         --options runtime \
         MyApp.app

# Sign with entitlements
codesign --sign "Developer ID Application: Company Name" \
         --entitlements entitlements.plist \
         --timestamp \
         MyApp.app

# Verify
codesign --verify --deep --strict --verbose=2 MyApp.app
spctl --assess --verbose=4 MyApp.app
```

**Notarization** (required for distribution):
```bash
# Create ZIP for notarization
ditto -c -k --keepParent MyApp.app MyApp.zip

# Submit for notarization
xcrun notarytool submit MyApp.zip \
  --apple-id "email@example.com" \
  --password "app-specific-password" \
  --team-id "TEAM_ID" \
  --wait

# Staple notarization ticket
xcrun stapler staple MyApp.app
```

**Hardened Runtime**:
```xml
<!-- entitlements.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <false/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <false/>
</dict>
</plist>
```

**Best Practices**:
- Enable Hardened Runtime
- Notarize all distributed apps
- Use timestamp server
- Sign all executables and libraries
- Test on clean system

### 6.3 Microsoft SignTool (Authenticode)

**Description**: Windows executable signing

**Requirements**:
- Code signing certificate
- SignTool.exe (Windows SDK)

**Signing**:
```powershell
# Sign with PFX file
signtool sign /f certificate.pfx /p password `
  /t http://timestamp.digicert.com `
  /fd SHA256 `
  /d "Application Name" `
  /du "https://example.com" `
  myapp.exe

# Sign with certificate store
signtool sign /n "Certificate Subject Name" `
  /t http://timestamp.digicert.com `
  /fd SHA256 `
  myapp.exe

# Dual-sign (SHA-1 + SHA-256 for compatibility)
signtool sign /f cert.pfx /p password /t http://timestamp.digicert.com /fd SHA1 myapp.exe
signtool sign /f cert.pfx /p password /tr http://timestamp.digicert.com /fd SHA256 /as myapp.exe

# Verify
signtool verify /pa /v myapp.exe
```

**Best Practices**:
- Use SHA-256 (SHA-1 deprecated)
- Always add timestamps
- Use EV certificates when possible
- Dual-sign for Windows 7 compatibility
- Verify signature after signing

### 6.4 GPG (GNU Privacy Guard)

**Description**: OpenPGP implementation for files, commits, packages

**Setup**:
```bash
# Generate key
gpg --full-generate-key
# Choose: (1) RSA and RSA (default)
# Key size: 3072 or 4096
# Expiration: 1 year (recommended)

# List keys
gpg --list-secret-keys --keyid-format LONG

# Export public key
gpg --armor --export KEY_ID > public.asc

# Export private key (for backup)
gpg --armor --export-secret-keys KEY_ID > private.asc
```

**Signing**:
```bash
# Sign file (detached signature)
gpg --detach-sign --armor file.tar.gz
# Creates: file.tar.gz.asc

# Sign file (inline signature)
gpg --sign file.txt
# Creates: file.txt.gpg

# Clear-sign (readable signed text)
gpg --clear-sign message.txt
# Creates: message.txt.asc
```

**Verification**:
```bash
# Verify detached signature
gpg --verify file.tar.gz.asc file.tar.gz

# Verify inline signature
gpg --verify file.txt.gpg
```

**Git Integration**:
```bash
# Configure Git
git config --global user.signingkey KEY_ID
git config --global commit.gpgsign true

# Sign commit
git commit -S -m "Signed commit"

# Verify commit
git verify-commit HEAD
```

**Best Practices**:
- Use 3072 or 4096-bit keys
- Set expiration (1-2 years)
- Upload public key to keyservers
- Sign git commits and tags
- Backup private key securely

### 6.5 In-Toto

**Description**: Framework for securing software supply chain

**Purpose**: End-to-end verification of software supply chain

**Concepts**:
- **Layout**: Defines supply chain steps and required functionaries
- **Link**: Metadata for each step (inputs, outputs, commands)
- **Verification**: Ensures layout compliance

**Example Layout**:
```yaml
# layout.json
{
  "steps": [
    {
      "name": "clone",
      "expected_materials": [],
      "expected_products": [["CREATE", "src/**"]],
      "pubkeys": ["alice-key-id"],
      "expected_command": ["git", "clone", "..."]
    },
    {
      "name": "build",
      "expected_materials": [["MATCH", "src/**", "WITH", "PRODUCTS", "FROM", "clone"]],
      "expected_products": [["CREATE", "target/app"]],
      "pubkeys": ["bob-key-id"],
      "expected_command": ["make", "build"]
    }
  ],
  "inspect": [
    {
      "name": "verify-build",
      "expected_materials": [["MATCH", "target/app", "WITH", "PRODUCTS", "FROM", "build"]],
      "run": ["sha256sum", "target/app"]
    }
  ]
}
```

**Usage**:
```bash
# Create layout
in-toto-run --step-name clone --key alice.key -- git clone repo

# Record step
in-toto-run --step-name build --key bob.key -- make build

# Verify
in-toto-verify --layout layout.json --layout-keys alice.pub bob.pub
```

**Best Practices**:
- Define complete supply chain in layout
- Sign layout with multiple keys
- Record all build steps
- Verify before deployment
- Integrate with CI/CD

---

## 7. Timestamping (RFC 3161)

### 7.1 RFC 3161 Overview

**Purpose**: Prove data existed at a specific time

**Use Cases**:
- Long-term signature validity
- Non-repudiation
- Regulatory compliance
- Timestamping chain

**Protocol**:
```
Client                                  TSA
  |                                      |
  | TimeStampReq (hash of data)         |
  |------------------------------------->|
  |                                      |
  |         TimeStampResp                |
  |         (signed timestamp token)     |
  |<-------------------------------------|
  |                                      |
```

### 7.2 Timestamp Request/Response

**TimeStampReq** structure:
```asn1
TimeStampReq ::= SEQUENCE {
   version          INTEGER  { v1(1) },
   messageImprint   MessageImprint,
   reqPolicy        TSAPolicyId      OPTIONAL,
   nonce            INTEGER           OPTIONAL,
   certReq          BOOLEAN          DEFAULT FALSE,
   extensions       [0] IMPLICIT Extensions OPTIONAL
}

MessageImprint ::= SEQUENCE {
   hashAlgorithm    AlgorithmIdentifier,
   hashedMessage    OCTET STRING
}
```

**TimeStampResp** structure:
```asn1
TimeStampResp ::= SEQUENCE {
   status          PKIStatusInfo,
   timeStampToken  TimeStampToken  OPTIONAL
}

TimeStampToken ::= ContentInfo
   -- contentType is id-signedData
   -- content is SignedData
   -- SignedData contains TSTInfo
```

**TSTInfo** (actual timestamp):
```asn1
TSTInfo ::= SEQUENCE {
   version         INTEGER  { v1(1) },
   policy          TSAPolicyId,
   messageImprint  MessageImprint,
   serialNumber    INTEGER,
   genTime         GeneralizedTime,  -- The timestamp!
   accuracy        Accuracy          OPTIONAL,
   ordering        BOOLEAN           DEFAULT FALSE,
   nonce           INTEGER           OPTIONAL,
   tsa             [0] GeneralName   OPTIONAL,
   extensions      [1] IMPLICIT Extensions OPTIONAL
}
```

### 7.3 Timestamp Authority Selection

**Qualified TSAs**:
- **DigiCert**: https://timestamp.digicert.com
- **Sectigo**: http://timestamp.sectigo.com
- **GlobalSign**: http://timestamp.globalsign.com/tsa/r6advanced1
- **FreeTSA**: https://freetsa.org/tsr (community)

**Evaluation Criteria**:
| Criterion | Importance | Notes |
|-----------|-----------|--------|
| RFC 3161 compliance | Critical | Must be compliant |
| Availability (SLA) | High | 99.9%+ required |
| Response time | Medium | <1 second preferred |
| Certificate validity | High | Long-term trust |
| Geographic distribution | Medium | Redundancy |
| Cost | Low | Free vs paid |
| Audit/certification | High | WebTrust, eIDAS |

**Best Practices**:
- Use qualified TSAs for legal/compliance
- Implement failover (multiple TSAs)
- Monitor TSA response times
- Verify TSA certificate chains
- Cache TSA certificates
- Set reasonable timeouts (10 seconds)

### 7.4 Long-Term Signature Validation

**Problem**: Signatures become invalid when:
- Signer certificate expires
- Hash algorithm becomes weak
- TSA certificate expires

**Solution**: Timestamps prove signature was valid when created

**Validation Timeline**:
```
2024-01-01: Document signed with certificate (valid until 2025-01-01)
2024-01-01: Timestamp obtained from TSA
2025-06-01: Certificate expires
2026-01-01: Signature still valid because:
            - Timestamp proves signature created 2024-01-01
            - Certificate was valid at 2024-01-01
            - Timestamp is still valid
```

**AdES Formats** (Advanced Electronic Signatures):

**AdES-BES**: Basic Electronic Signature
```
- Digital signature
- Signer certificate
- No timestamp
```

**AdES-T**: With Timestamp
```
- AdES-BES
- Timestamp over signature
```

**AdES-C**: Complete validation data
```
- AdES-T
- Complete certificate chain
- Complete revocation data (CRL/OCSP)
```

**AdES-X**: Extended with timestamp
```
- AdES-C
- Archive timestamp over validation data
```

**AdES-A**: Archival (indefinite validity)
```
- AdES-X
- Periodic re-timestamping before TSA cert expires
- Maintains timestamp chain indefinitely
```

**Implementation**:
```python
class ArchivalSignature:
    """AdES-A archival signature with periodic re-timestamping"""

    def __init__(self, initial_signature, initial_timestamp):
        self.signature = initial_signature
        self.timestamps = [initial_timestamp]
        self.validation_data = []

    def add_archive_timestamp(self, tsa_url):
        """Add archive timestamp before TSA cert expires"""

        # Gather all data to be timestamped
        data_to_timestamp = (
            self.signature +
            b''.join(self.timestamps) +
            b''.join(self.validation_data)
        )

        # Get new timestamp
        new_timestamp = get_timestamp(tsa_url, data_to_timestamp)
        self.timestamps.append(new_timestamp)

        # Schedule next re-timestamping
        # (6-12 months before TSA certificate expiration)

    def verify(self, current_date):
        """Verify signature is valid at current date"""

        # Verify timestamp chain
        for i, timestamp in enumerate(self.timestamps):
            if not verify_timestamp(timestamp):
                return False

            # Check timestamp covers previous timestamps
            if i > 0:
                previous_data = b''.join(self.timestamps[:i])
                if not verify_timestamp_covers(timestamp, previous_data):
                    return False

        # Find oldest timestamp proving signature was valid
        oldest_timestamp = self.timestamps[0]
        signature_time = extract_time(oldest_timestamp)

        # Verify certificate was valid at signature time
        if not certificate_valid_at(self.signature.cert, signature_time):
            return False

        return True
```

**Re-timestamping Schedule**:
```
Initial signature:     2024-01-01 (TSA cert valid until 2027-01-01)
First re-timestamp:    2026-07-01 (6 months before TSA cert expiry)
Second re-timestamp:   2029-07-01
Third re-timestamp:    2032-07-01
... continue indefinitely
```

---

## 8. HSM Integration

### 8.1 Hardware Security Modules Overview

**Purpose**: Secure cryptographic key storage and operations

**Security Features**:
- Tamper-resistant/evident hardware
- Keys never leave HSM in plaintext
- FIPS 140-2/3 certified
- Physical access controls
- Audit logging

**Form Factors**:
- **Network HSM**: Rack-mounted, high performance
- **PCIe HSM**: Internal card, low latency
- **USB HSM**: Portable (YubiHSM, Nitrokey)
- **Cloud HSM**: Managed service (AWS CloudHSM, Azure Dedicated HSM)

### 8.2 PKCS#11 Interface

**Description**: Standard API for cryptographic tokens

**Concepts**:
- **Slot**: Physical or logical HSM slot
- **Token**: Cryptographic token in slot
- **Session**: Connection to token
- **Object**: Key, certificate, data in token

**Example**:
```python
import pkcs11
from pkcs11 import Mechanism

# Load PKCS#11 library
lib = pkcs11.lib('/usr/lib/softhsm/libsofthsm2.so')

# Get token
token = lib.get_token(token_label='signing-token')

# Open session
with token.open(user_pin='1234') as session:

    # Generate key pair in HSM
    public_key, private_key = session.generate_keypair(
        pkcs11.KeyType.RSA,
        2048,
        label='code-signing-key',
        store=True  # Persist in HSM
    )

    # Sign data (operation happens in HSM)
    data = b'Important document'
    signature = private_key.sign(
        data,
        mechanism=Mechanism.SHA256_RSA_PKCS
    )

    # Verify
    public_key.verify(data, signature, mechanism=Mechanism.SHA256_RSA_PKCS)
```

### 8.3 HSM Key Management

**Key Generation in HSM**:
```python
def generate_signing_key_in_hsm(session, label, algorithm='rsa', key_size=3072):
    """Generate signing key in HSM (never leaves HSM)"""

    if algorithm == 'rsa':
        public_key, private_key = session.generate_keypair(
            pkcs11.KeyType.RSA,
            key_size,
            label=label,
            store=True,
            capabilities=(
                pkcs11.MechanismFlag.VERIFY,  # Public key
                pkcs11.MechanismFlag.SIGN,    # Private key
            ),
            modifiable=False,  # Prevent modification
            extractable=False  # Prevent export
        )

    elif algorithm == 'ecdsa':
        public_key, private_key = session.generate_keypair(
            pkcs11.KeyType.EC,
            ecparams=pkcs11.util.ec.SECP384R1,
            label=label,
            store=True,
            capabilities=(
                pkcs11.MechanismFlag.VERIFY,
                pkcs11.MechanismFlag.SIGN,
            ),
            modifiable=False,
            extractable=False
        )

    return public_key, private_key
```

**Key Backup**:
```python
def backup_hsm_keys(hsm_config):
    """Backup HSM using HSM-specific backup mechanism"""

    # Most HSMs support backup to encrypted backup token
    # This is HSM-specific (not standardized in PKCS#11)

    # Example for Luna HSM:
    # hsm.backup(backup_token_serial='ABC123')

    # Example for nShield:
    # hsm.backup(ocs_card_set=['card1', 'card2', 'card3'])

    # Key backup requirements:
    # - Use M-of-N scheme
    # - Store backup tokens in separate locations
    # - Test recovery quarterly
    # - Maintain backup custody log
    pass
```

### 8.4 HSM Performance Optimization

**Connection Pooling**:
```python
class HSMConnectionPool:
    """Pool of HSM sessions for high-throughput signing"""

    def __init__(self, hsm_config, pool_size=8):
        self.lib = pkcs11.lib(hsm_config['module'])
        self.token = self.lib.get_token(token_label=hsm_config['token'])
        self.pool_size = pool_size
        self.sessions = []

        # Create session pool
        for _ in range(pool_size):
            session = self.token.open(user_pin=hsm_config['pin'])
            self.sessions.append(session)

    def sign(self, data, key_label):
        """Sign using pooled session"""
        # Round-robin session selection
        session = self.sessions[hash(key_label) % self.pool_size]

        private_key = session.get_key(
            object_class=pkcs11.ObjectClass.PRIVATE_KEY,
            label=key_label
        )

        return private_key.sign(data, mechanism=Mechanism.SHA256_RSA_PKCS)
```

**Batch Signing**:
```python
def batch_sign_with_hsm(hsm_pool, files, key_label):
    """Batch sign files with HSM"""

    from concurrent.futures import ThreadPoolExecutor

    def sign_file(file_path):
        data = file_path.read_bytes()
        signature = hsm_pool.sign(data, key_label)
        return signature

    # Parallel signing (limited by HSM throughput)
    with ThreadPoolExecutor(max_workers=hsm_pool.pool_size) as executor:
        signatures = list(executor.map(sign_file, files))

    return signatures
```

**Performance Considerations**:
- HSM throughput: 100-10,000 signatures/second (varies by model)
- Network latency for network HSMs
- PCIe HSMs have lowest latency
- Use session pooling for concurrency
- Batch operations when possible

### 8.5 HSM Security Best Practices

**Access Control**:
```
- Crypto Officer (CO): Key management, user management
- User (CU): Signing/encryption operations
- Audit: Read-only access to audit logs
- Separate roles and permissions
```

**Operational Security**:
```
1. Physical Security:
   - Locked server room
   - Video surveillance
   - Access logs
   - Tamper-evident seals

2. Logical Security:
   - Strong PINs (12+ characters)
   - M-of-N authentication for critical operations
   - Regular PIN rotation
   - Account lockout after failed attempts

3. Monitoring:
   - Real-time audit log monitoring
   - Alert on suspicious activity
   - Regular security audits
   - Penetration testing

4. Backup/DR:
   - Redundant HSMs
   - Geographic distribution
   - Regular backup testing
   - Documented recovery procedures
```

**Compliance**:
```
- FIPS 140-2 Level 3+: Government, financial
- Common Criteria EAL4+: High security applications
- PCI-DSS: Payment processing
- eIDAS: Qualified signatures (EU)
```

---

## 9. File Formats

### 9.1 PKCS#7 / CMS (Cryptographic Message Syntax)

**Description**: Container format for signed/encrypted data (RFC 5652)

**Structure**:
```asn1
SignedData ::= SEQUENCE {
   version          CMSVersion,
   digestAlgorithms DigestAlgorithmIdentifiers,
   encapContentInfo EncapsulatedContentInfo,
   certificates     [0] IMPLICIT CertificateSet OPTIONAL,
   crls             [1] IMPLICIT RevocationInfoChoices OPTIONAL,
   signerInfos      SignerInfos
}

SignerInfo ::= SEQUENCE {
   version                CMSVersion,
   sid                    SignerIdentifier,
   digestAlgorithm        DigestAlgorithmIdentifier,
   signedAttrs            [0] IMPLICIT SignedAttributes OPTIONAL,
   signatureAlgorithm     SignatureAlgorithmIdentifier,
   signature              SignatureValue,
   unsignedAttrs          [1] IMPLICIT UnsignedAttributes OPTIONAL
}
```

**Formats**:
- **PEM**: Base64-encoded, ASCII
  ```
  -----BEGIN PKCS7-----
  MIIGCAYJKoZIhvcNAQcCoIIF+TCCBfUCAQExDzANBglghkgBZQMEAgEFADAL...
  -----END PKCS7-----
  ```

- **DER**: Binary encoding
  ```
  0x30 0x82 0x05 0xf5 0x06 0x09 0x2a 0x86 ...
  ```

**Use Cases**:
- S/MIME email
- PDF signatures (PAdES)
- Office document signatures
- Windows Authenticode

### 9.2 JWS (JSON Web Signature)

**Description**: JSON-based signature format (RFC 7515)

**Structure**:
```
BASE64URL(Header) . BASE64URL(Payload) . BASE64URL(Signature)
```

**Header**:
```json
{
  "alg": "ES256",  // Algorithm (ES256, RS256, EdDSA, etc.)
  "typ": "JWT",    // Type
  "kid": "key-1"   // Key ID (optional)
}
```

**Payload** (claims):
```json
{
  "iss": "https://example.com",  // Issuer
  "sub": "user@example.com",     // Subject
  "aud": "https://api.example.com", // Audience
  "exp": 1706371200,             // Expiration
  "iat": 1706284800,             // Issued at
  "data": "..."                  // Custom data
}
```

**Algorithms**:
| alg | Algorithm |
|-----|-----------|
| RS256 | RSA-PKCS1v15 with SHA-256 |
| RS384 | RSA-PKCS1v15 with SHA-384 |
| RS512 | RSA-PKCS1v15 with SHA-512 |
| ES256 | ECDSA P-256 with SHA-256 |
| ES384 | ECDSA P-384 with SHA-384 |
| ES512 | ECDSA P-521 with SHA-512 |
| EdDSA | EdDSA (Ed25519 or Ed448) |

**Example**:
```python
import jwt

# Sign
payload = {'data': 'important message', 'iat': time.time()}
token = jwt.encode(payload, private_key, algorithm='ES256')

# Verify
decoded = jwt.decode(token, public_key, algorithms=['ES256'])
```

**Use Cases**:
- API authentication (OAuth 2.0, OpenID Connect)
- Single Sign-On (SSO)
- Microservices communication
- Mobile app backends

### 9.3 XML-DSig (XML Digital Signatures)

**Description**: XML signature format (W3C standard)

**Structure**:
```xml
<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
  <SignedInfo>
    <CanonicalizationMethod Algorithm="..."/>
    <SignatureMethod Algorithm="..."/>
    <Reference URI="...">
      <Transforms>
        <Transform Algorithm="..."/>
      </Transforms>
      <DigestMethod Algorithm="..."/>
      <DigestValue>...</DigestValue>
    </Reference>
  </SignedInfo>
  <SignatureValue>...</SignatureValue>
  <KeyInfo>
    <X509Data>
      <X509Certificate>...</X509Certificate>
    </X509Data>
  </KeyInfo>
</Signature>
```

**Canonicalization**: Transforms XML to canonical form before hashing

**Types**:
- **Enveloped**: Signature inside signed document
- **Enveloping**: Signed data inside Signature element
- **Detached**: Signature separate from document

**Use Cases**:
- SAML assertions
- SOAP web services
- XML documents
- XAdES (XML Advanced Electronic Signatures)

### 9.4 PDF Signatures (PAdES)

**Description**: PDF signature format based on PKCS#7

**Signature Types**:
- **Basic**: Simple PKCS#7 signature
- **PAdES-B**: Baseline profile
- **PAdES-T**: With timestamp
- **PAdES-LT**: Long-term validation data
- **PAdES-LTA**: Archival with re-timestamping

**Structure** (in PDF):
```pdf
/Sig << /Type /Sig
        /Filter /Adobe.PPKLite
        /SubFilter /ETSI.CAdES.detached
        /Contents <hex-encoded PKCS#7>
        /ByteRange [0 1234 5678 9012]  # Signed byte ranges
        /M (D:20250127120000Z)  # Signing time
        /Name (John Doe)
        /Location (New York)
        /Reason (Approval)
     >>
```

**Tools**:
- **pyHanko** (Python): Full PAdES support
- **Adobe Acrobat**: Commercial
- **iText** (Java): Commercial/open source
- **LibreOffice**: Free, basic support

### 9.5 Detached Signatures

**Description**: Signature stored separately from signed data

**Formats**:
```
document.pdf
document.pdf.sig     # Detached signature
document.pdf.p7s     # PKCS#7 detached
document.pdf.asc     # GPG ASCII-armored
```

**Advantages**:
- Original file unchanged
- Can add multiple signatures
- Signature can be verified independently

**Disadvantages**:
- Must distribute two files
- Risk of signature/data separation

**Example Structure**:
```json
// manifest.json with detached signatures
{
  "files": {
    "binary.exe": {
      "hash": "sha256:abc123...",
      "signature": "base64-encoded-signature",
      "signer": "CN=Code Signing Cert"
    },
    "library.dll": {
      "hash": "sha256:def456...",
      "signature": "base64-encoded-signature",
      "signer": "CN=Code Signing Cert"
    }
  },
  "timestamp": "2025-01-27T12:00:00Z"
}
```

---

## 10. Standards and Compliance

### 10.1 FIPS 186-4 (Digital Signature Standard)

**Authority**: NIST (National Institute of Standards and Technology)

**Approved Algorithms**:
- **RSA**: 2048, 3072, 4096 bits (PKCS#1 v1.5 or PSS)
- **ECDSA**: P-256, P-384, P-521 curves
- **DSA**: 2048, 3072 bits (deprecated)

**Approved Hash Functions**: SHA-256, SHA-384, SHA-512, SHA-512/256

**Requirements**:
- Keys must be generated using approved methods
- Random number generation must use approved DRBG
- Private keys must be protected
- Implementation must be validated (CAVP)

**Compliance Check**:
```python
def check_fips_186_4_compliance(algorithm, key_size, hash_algorithm):
    """Check FIPS 186-4 compliance"""

    approved_rsa_sizes = [2048, 3072, 4096]
    approved_ecdsa_curves = ['P-256', 'P-384', 'P-521']
    approved_hashes = ['SHA-256', 'SHA-384', 'SHA-512', 'SHA-512/256']

    if algorithm == 'RSA':
        if key_size not in approved_rsa_sizes:
            return False, f"RSA-{key_size} not FIPS 186-4 approved"
    elif algorithm == 'ECDSA':
        if key_size not in approved_ecdsa_curves:
            return False, f"ECDSA-{key_size} not FIPS 186-4 approved"
    elif algorithm == 'DSA':
        return False, "DSA deprecated in FIPS 186-5"

    if hash_algorithm not in approved_hashes:
        return False, f"{hash_algorithm} not approved"

    return True, "FIPS 186-4 compliant"
```

### 10.2 eIDAS (EU Electronic Identification and Trust Services)

**Authority**: European Union (Regulation 910/2014)

**Signature Levels**:

**Simple Electronic Signature**:
- Basic signature (e.g., scanned handwriting)
- Minimal requirements
- Lowest legal weight

**Advanced Electronic Signature (AdES)**:
- Uniquely linked to signatory
- Capable of identifying signatory
- Created using data under sole control
- Detects subsequent tampering
- Formats: XAdES, PAdES, CAdES, JAdES

**Qualified Electronic Signature (QES)**:
- AdES created by qualified device (QSCD)
- Based on qualified certificate
- Issued by qualified trust service provider
- **Equivalent to handwritten signature** (legal effect)

**Timestamp Requirements**:
- Qualified timestamps for long-term validity
- RFC 3161 compliant
- Issued by qualified TSP

**Compliance Requirements**:
```yaml
qes_requirements:
  signature:
    - Advanced electronic signature properties
    - Created by QSCD (EAL4+ certified)
    - Based on qualified certificate

  certificate:
    - Issued by qualified TSP
    - eIDAS-compliant certificate profile
    - Adequate key length (RSA ≥2048, ECDSA ≥256)
    - Approved signature algorithm (SHA-256+)

  trust_service_provider:
    - Qualified under eIDAS
    - Audited by supervisory body
    - Listed in EU Trusted Lists

  long_term_validation:
    - Qualified timestamp at creation
    - Complete validation data (certificates, CRLs)
    - Archive format (AdES-A) for long-term
```

### 10.3 Common Criteria EAL4+

**Description**: International security evaluation standard

**Evaluation Assurance Levels**:
| EAL | Description | Assurance |
|-----|-------------|-----------|
| EAL1 | Functionally tested | Minimal |
| EAL2 | Structurally tested | Low |
| EAL3 | Methodically tested | Moderate |
| **EAL4** | **Methodically designed and tested** | **High** |
| EAL4+ | EAL4 with additional components | Very high |
| EAL5-7 | Formally verified | Highest |

**Requirements for Signing Systems**:
```
Security Functional Requirements (SFRs):
- Cryptographic key management
- Cryptographic operation (signing)
- User data protection
- Identification and authentication
- Security audit
- Security management

Security Assurance Requirements (SARs):
- Configuration management
- Development security
- Guidance documents
- Life-cycle support
- Tests (coverage, depth, functional)
- Vulnerability assessment
```

**HSM Certification**:
- Most HSMs are Common Criteria EAL4+ certified
- Certification covers hardware and firmware
- Independent security evaluation
- Published Security Target (ST) and Protection Profile (PP)

### 10.4 PCI-DSS (Payment Card Industry)

**Authority**: PCI Security Standards Council

**Code Signing Requirements** (PA-DSS):
```
Requirement 5: Develop secure code
  5.1: Use industry-accepted secure coding guidelines
  5.2: Review custom code for vulnerabilities
  5.3: Secure cryptographic key management
  5.4: Code signing for all payment software

Requirement 6: Protect cryptographic keys
  6.1: Keys stored in FIPS 140-2 Level 2+ HSM
  6.2: Dual control and split knowledge
  6.3: Key generation ceremony documented
  6.4: Keys rotated annually
  6.5: Retired keys securely destroyed

Requirement 9: Control access to signing keys
  9.1: Limit access to authorized personnel
  9.2: Implement M-of-N authentication
  9.3: Log all key access
  9.4: Review logs regularly
```

**Minimum Key Sizes**:
- RSA: 2048 bits
- ECC: 256 bits (P-256 or equivalent)

### 10.5 CA/Browser Forum Baseline Requirements

**Description**: Requirements for publicly-trusted certificates

**Code Signing Certificates**:

**Validity Periods**:
- Maximum: 39 months (3 years + 3 months overlap)
- Recommended: 1-2 years for operational flexibility

**Key Requirements**:
- RSA: Minimum 2048 bits (3072 recommended)
- ECDSA: Minimum P-256 (P-384 for high security)

**Extended Validation (EV) Code Signing**:
```
Requirements:
- Verified legal identity of organization
- Verified operational existence
- Verified exclusive right to use domain
- Private key stored in FIPS 140-2 Level 2+ HSM or USB token
- Multi-factor authentication required
- Enhanced validation procedures
```

**Timestamp Requirements**:
- Must include RFC 3161 timestamp
- Timestamp authority certificate valid >10 years

---

## 11. Security Best Practices

### 11.1 Algorithm Selection

**Current Recommendations (2025)**:

**For New Systems**:
1. **EdDSA Ed25519**: Modern, fast, simple
2. **ECDSA P-384**: High security, FIPS compliant
3. **RSA-PSS 3072**: Long-term security, maximum compatibility

**Avoid**:
- ❌ RSA-PKCS#1 v1.5 (vulnerable to padding oracle)
- ❌ SHA-1 (collision attacks)
- ❌ RSA-1024 (insufficient key length)
- ❌ DSA (deprecated, use ECDSA instead)
- ❌ MD5 (cryptographically broken)

**Migration Path**:
```
Legacy (2020-)        Current (2025)        Future (2030+)
--------------        --------------        --------------
RSA-2048/SHA-256  →   RSA-3072/SHA-384  →  Post-quantum?
ECDSA P-256       →   ECDSA P-384       →  Post-quantum?
SHA-256           →   SHA-384/SHA-512   →  SHA-3?
```

### 11.2 Key Protection

**Security Levels**:

| Protection Level | Method | Use Case |
|------------------|--------|----------|
| **Highest** | FIPS 140-3 Level 4 HSM | Nation-state secrets, CA roots |
| **Very High** | FIPS 140-2 Level 3 HSM | Financial, government, critical infrastructure |
| **High** | FIPS 140-2 Level 2 HSM | Code signing, document signing |
| **Medium** | Cloud KMS (AWS/Azure/GCP) | Cloud-native applications |
| **Low** | Encrypted key file | Development, testing |
| **Minimal** | Plaintext key file | ❌ Never use in production |

**Best Practices**:
```python
# ✓ Good: HSM storage
private_key = hsm.get_key('signing-key')
signature = private_key.sign(data)

# ✓ Acceptable: Encrypted storage
encrypted_key = Path('key.pem').read_bytes()
private_key = serialization.load_pem_private_key(
    encrypted_key,
    password=get_password_from_env()  # Not hardcoded!
)

# ❌ Bad: Plaintext storage
private_key = Path('key.pem').read_bytes()  # Unencrypted!

# ❌ Terrible: Embedded in code (EXAMPLE ONLY - truncated/fake key)
# SECURITY: This is a deliberately bad example for educational purposes
private_key = """-----BEGIN PRIVATE KEY-----
[TRUNCATED - NEVER EMBED REAL KEYS IN CODE]
-----END PRIVATE KEY-----"""  # Never do this!
```

### 11.3 Signature Verification

**Always Verify**:
```python
def secure_signature_verification(data, signature, cert, trust_anchors):
    """Comprehensive signature verification"""

    # 1. Verify signature algorithm is approved
    if not is_approved_algorithm(cert.signature_algorithm):
        raise SecurityError("Signature algorithm not approved")

    # 2. Verify certificate chain
    chain_valid, chain_errors = verify_certificate_chain(
        cert,
        trust_anchors
    )
    if not chain_valid:
        raise SecurityError(f"Certificate chain invalid: {chain_errors}")

    # 3. Check certificate validity period
    now = datetime.now(timezone.utc)
    if not (cert.not_valid_before_utc <= now <= cert.not_valid_after_utc):
        raise SecurityError("Certificate expired or not yet valid")

    # 4. Check certificate revocation
    revocation_status = check_revocation(cert)
    if revocation_status == 'revoked':
        raise SecurityError("Certificate revoked")

    # 5. Verify signature
    try:
        cert.public_key().verify(signature, data, ...)
    except InvalidSignature:
        raise SecurityError("Signature verification failed")

    # 6. Check certificate key usage
    if 'digitalSignature' not in cert.key_usage:
        raise SecurityError("Certificate not valid for signing")

    return True
```

**Never**:
- ❌ Skip certificate chain verification
- ❌ Skip revocation checking
- ❌ Trust self-signed certificates (unless explicitly configured)
- ❌ Accept weak algorithms (MD5, SHA-1, RSA-1024)
- ❌ Ignore certificate expiration

### 11.4 Timestamp Best Practices

**Always Timestamp**:
```python
def sign_with_timestamp(data, private_key, tsa_url):
    """Sign data with timestamp for long-term validity"""

    # 1. Sign data
    signature = private_key.sign(data, ...)

    # 2. Get timestamp
    timestamp = request_timestamp(tsa_url, signature)

    # 3. Bundle signature + timestamp
    signed_bundle = {
        'data_hash': hashlib.sha256(data).hexdigest(),
        'signature': signature.hex(),
        'timestamp': timestamp.hex(),
        'algorithm': 'RSA-PSS-SHA256',
        'timestamp_url': tsa_url
    }

    return signed_bundle
```

**Timestamp Verification**:
```python
def verify_with_timestamp(data, signed_bundle, current_time):
    """Verify signature with timestamp"""

    # 1. Verify timestamp
    timestamp_valid = verify_timestamp(signed_bundle['timestamp'])
    if not timestamp_valid:
        return False, "Timestamp invalid"

    # 2. Extract timestamp time
    timestamp_time = extract_timestamp_time(signed_bundle['timestamp'])

    # 3. Verify certificate was valid at timestamp time
    cert = extract_certificate(signed_bundle)
    if not (cert.not_before <= timestamp_time <= cert.not_after):
        return False, "Certificate was not valid at timestamp time"

    # 4. Verify signature
    signature = bytes.fromhex(signed_bundle['signature'])
    try:
        verify_signature(cert.public_key(), data, signature)
    except:
        return False, "Signature verification failed"

    return True, "Signature and timestamp valid"
```

### 11.5 Operational Security

**Signing Environment**:
```
Production Signing Environment:
- Dedicated hardware (HSM)
- Network-isolated (air-gapped for critical keys)
- Multi-factor authentication
- Audit logging enabled
- Video surveillance
- Access control (physical + logical)
- Regular security audits
```

**Access Control**:
```yaml
access_control:
  roles:
    crypto_officer:
      permissions:
        - key_generation
        - key_backup
        - user_management
        - hsm_configuration
      authentication:
        - smart_card
        - pin
        - biometric

    signing_user:
      permissions:
        - sign_operation
        - verify_operation
      authentication:
        - username
        - password
        - mfa_token

    auditor:
      permissions:
        - read_audit_logs
        - generate_reports
      authentication:
        - username
        - password
```

**Monitoring and Alerting**:
```python
# Alert conditions
alerts = {
    'unauthorized_access': {
        'condition': 'Failed authentication > 3 attempts',
        'severity': 'high',
        'action': 'Lock account, notify security team'
    },
    'weak_algorithm_usage': {
        'condition': 'Signature created with SHA-1 or RSA-1024',
        'severity': 'medium',
        'action': 'Log event, notify compliance team'
    },
    'certificate_expiring': {
        'condition': 'Certificate expires within 30 days',
        'severity': 'medium',
        'action': 'Notify certificate manager'
    },
    'hsm_offline': {
        'condition': 'HSM not responding',
        'severity': 'critical',
        'action': 'Failover to backup HSM, page on-call'
    }
}
```

---

## 12. Troubleshooting

### 12.1 Common Signature Verification Failures

**Problem**: "Signature verification failed"

**Causes**:
1. Data modified after signing
2. Wrong public key used
3. Algorithm mismatch
4. Encoding issues

**Solutions**:
```python
# Debugging signature verification
def debug_signature_verification(data, signature, public_key):
    """Debug why signature verification is failing"""

    print("Debugging signature verification...")

    # 1. Check data integrity
    data_hash = hashlib.sha256(data).hexdigest()
    print(f"Data hash: {data_hash}")

    # 2. Check signature length
    print(f"Signature length: {len(signature)} bytes")

    # 3. Check public key type
    print(f"Public key type: {type(public_key)}")

    # 4. Try different algorithms
    algorithms = [
        (padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256()),
        (padding.PKCS1v15(), hashes.SHA256()),
        (padding.PSS(mgf=padding.MGF1(hashes.SHA384()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA384()),
    ]

    for pad, hash_algo in algorithms:
        try:
            public_key.verify(signature, data, pad, hash_algo)
            print(f"✓ Success with {pad} and {hash_algo}")
            return True
        except Exception as e:
            print(f"✗ Failed with {pad} and {hash_algo}: {e}")

    return False
```

### 12.2 Certificate Chain Issues

**Problem**: "Certificate chain verification failed"

**Causes**:
1. Missing intermediate certificates
2. Root not in trust store
3. Certificate expired
4. Signature algorithm mismatch

**Solutions**:
```bash
# Examine certificate chain
openssl x509 -in cert.pem -text -noout

# Verify chain manually
openssl verify -CAfile root.pem -untrusted intermediate.pem cert.pem

# Check certificate dates
openssl x509 -in cert.pem -noout -dates

# View certificate chain in bundle
openssl crl2pkcs7 -nocrl -certfile bundle.pem | openssl pkcs7 -print_certs -text -noout
```

### 12.3 HSM Connection Problems

**Problem**: "Cannot connect to HSM"

**Causes**:
1. PKCS#11 module path incorrect
2. HSM not initialized
3. Wrong PIN
4. Network issues (for network HSMs)

**Solutions**:
```python
def diagnose_hsm_connection(module_path, token_label, pin):
    """Diagnose HSM connection issues"""

    # 1. Check module exists
    if not Path(module_path).exists():
        print(f"✗ PKCS#11 module not found: {module_path}")
        return

    # 2. Load module
    try:
        lib = pkcs11.lib(module_path)
        print(f"✓ Module loaded: {lib}")
    except Exception as e:
        print(f"✗ Failed to load module: {e}")
        return

    # 3. List slots
    try:
        slots = lib.get_slots()
        print(f"✓ Found {len(list(slots))} slots")
        for slot in lib.get_slots():
            print(f"  Slot {slot.slot_id}: {slot}")
    except Exception as e:
        print(f"✗ Failed to get slots: {e}")
        return

    # 4. Get token
    try:
        token = lib.get_token(token_label=token_label)
        print(f"✓ Token found: {token}")
    except Exception as e:
        print(f"✗ Token not found: {e}")
        return

    # 5. Open session
    try:
        session = token.open(user_pin=pin)
        print(f"✓ Session opened")
        session.close()
    except Exception as e:
        print(f"✗ Failed to open session: {e}")
        print("  Check PIN is correct")
        print("  Check token is initialized")
        return
```

### 12.4 Performance Issues

**Problem**: "Signing is too slow"

**Solutions**:

**Optimization 1: Use faster algorithm**:
```python
# Slow: RSA-4096
private_key = rsa.generate_private_key(65537, 4096)
# ~100 signatures/second

# Fast: Ed25519
private_key = ed25519.Ed25519PrivateKey.generate()
# ~50,000 signatures/second (500x faster!)
```

**Optimization 2: Batch signing**:
```python
# Instead of signing each file individually
for file in files:
    signature = sign_file(file)  # HSM round-trip for each

# Sign manifest of hashes
manifest = {file: hash(file) for file in files}
signature = sign(json.dumps(manifest))  # Single HSM operation
```

**Optimization 3: Connection pooling**:
```python
# Instead of opening new HSM session each time
for file in files:
    session = hsm.open_session()
    signature = session.sign(file)
    session.close()

# Use session pool
pool = HSMSessionPool(size=8)
signatures = pool.batch_sign(files)
```

---

## 13. Tools and Libraries

### 13.1 Python

**cryptography**:
```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519, padding

# Most complete and recommended library
```

**PyJWT**:
```python
import jwt

# For JWS/JWT signatures
token = jwt.encode(payload, private_key, algorithm='ES256')
decoded = jwt.decode(token, public_key, algorithms=['ES256'])
```

**python-pkcs11**:
```python
import pkcs11

# For HSM integration via PKCS#11
lib = pkcs11.lib('/usr/lib/pkcs11/library.so')
```

**pyHanko**:
```python
from pyhanko.sign import signers, fields

# For PDF signing (PAdES)
signer = signers.SimpleSigner.load(...)
```

### 13.2 Go

**crypto/rsa, crypto/ecdsa, crypto/ed25519**:
```go
import (
    "crypto/ed25519"
    "crypto/rand"
)

// Standard library crypto
publicKey, privateKey, _ := ed25519.GenerateKey(rand.Reader)
signature := ed25519.Sign(privateKey, message)
valid := ed25519.Verify(publicKey, message, signature)
```

**jwt-go**:
```go
import "github.com/golang-jwt/jwt/v5"

// JWT signing
token := jwt.NewWithClaims(jwt.SigningMethodES256, claims)
signedToken, _ := token.SignedString(privateKey)
```

### 13.3 Command-Line Tools

**OpenSSL**:
```bash
# Generate key
openssl genrsa -out private.pem 3072

# Sign file
openssl dgst -sha256 -sign private.pem -out signature.bin file.txt

# Verify
openssl dgst -sha256 -verify public.pem -signature signature.bin file.txt

# Work with certificates
openssl x509 -in cert.pem -text -noout
```

**GPG**:
```bash
# Generate key
gpg --full-generate-key

# Sign file
gpg --detach-sign --armor file.txt

# Verify
gpg --verify file.txt.asc file.txt

# Sign git commit
git commit -S -m "Signed commit"
```

**Cosign** (Sigstore):
```bash
# Generate key
cosign generate-key-pair

# Sign container
cosign sign --key cosign.key registry.io/image:tag

# Verify
cosign verify --key cosign.pub registry.io/image:tag

# Keyless signing
cosign sign registry.io/image:tag
```

**SignTool** (Windows):
```powershell
# Sign executable
signtool sign /f cert.pfx /p password /t http://timestamp.digicert.com /fd SHA256 app.exe

# Verify
signtool verify /pa app.exe
```

### 13.4 Online Services

**Certificate Authorities**:
- DigiCert (https://www.digicert.com)
- GlobalSign (https://www.globalsign.com)
- Sectigo (https://sectigo.com)
- Let's Encrypt (https://letsencrypt.org) - Free, but no code signing

**Timestamp Authorities**:
- DigiCert: https://timestamp.digicert.com
- Sectigo: http://timestamp.sectigo.com
- FreeTSA: https://freetsa.org/tsr

**Cloud KMS**:
- AWS KMS (https://aws.amazon.com/kms/)
- Azure Key Vault (https://azure.microsoft.com/services/key-vault/)
- Google Cloud KMS (https://cloud.google.com/kms)

---

## 14. References

### 14.1 Standards

- **FIPS 186-4**: Digital Signature Standard
  https://csrc.nist.gov/publications/detail/fips/186/4/final

- **RFC 3161**: Time-Stamp Protocol (TSP)
  https://datatracker.ietf.org/doc/html/rfc3161

- **RFC 5652**: Cryptographic Message Syntax (CMS)
  https://datatracker.ietf.org/doc/html/rfc5652

- **RFC 7515**: JSON Web Signature (JWS)
  https://datatracker.ietf.org/doc/html/rfc7515

- **RFC 6979**: Deterministic ECDSA
  https://datatracker.ietf.org/doc/html/rfc6979

- **ETSI EN 319 102-1**: AdES Digital Signatures
  https://www.etsi.org/deliver/etsi_en/319100_319199/31910201/

- **eIDAS Regulation**: EU 910/2014
  https://eur-lex.europa.eu/eli/reg/2014/910/oj

### 14.2 Best Practice Guides

- **NIST SP 800-57**: Key Management Recommendations
  https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final

- **NIST SP 800-89**: Recommendation for Obtaining Assurances for Digital Signature Applications
  https://csrc.nist.gov/publications/detail/sp/800-89/final

- **OWASP Cryptographic Storage Cheat Sheet**
  https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html

- **CA/Browser Forum Baseline Requirements**
  https://cabforum.org/baseline-requirements/

### 14.3 Documentation

- **Sigstore Documentation**: https://docs.sigstore.dev/
- **Cryptography.io**: https://cryptography.io/
- **OpenSSL Documentation**: https://www.openssl.org/docs/
- **PKCS#11 Specification**: http://docs.oasis-open.org/pkcs11/

### 14.4 Learning Resources

- **Practical Cryptography for Developers**: https://cryptobook.nakov.com/
- **Applied Cryptography (Bruce Schneier)**: Classic textbook
- **Serious Cryptography (Jean-Philippe Aumasson)**: Modern practical guide

---

## Appendix A: Quick Reference

### Algorithm Comparison

| Algorithm | Key Size | Sig Size | Speed | Security (bits) | FIPS | Use Case |
|-----------|----------|----------|-------|----------------|------|----------|
| RSA-2048  | 2048 b   | 2048 b   | ⭐     | 112            | ✓    | Legacy |
| RSA-3072  | 3072 b   | 3072 b   | ⭐     | 128            | ✓    | Long-term |
| ECDSA P-256 | 256 b  | 512 b    | ⭐⭐⭐⭐  | 128            | ✓    | General |
| ECDSA P-384 | 384 b  | 768 b    | ⭐⭐⭐   | 192            | ✓    | High security |
| Ed25519   | 256 b    | 512 b    | ⭐⭐⭐⭐⭐ | 128            | ✗    | Modern |

### Common Commands

```bash
# Generate RSA key
openssl genrsa -out key.pem 3072

# Generate ECDSA key
openssl ecparam -name prime256v1 -genkey -out key.pem

# Sign with OpenSSL
openssl dgst -sha256 -sign key.pem -out sig.bin file.txt

# Verify with OpenSSL
openssl dgst -sha256 -verify pub.pem -signature sig.bin file.txt

# Sign with GPG
gpg --detach-sign --armor file.txt

# Verify with GPG
gpg --verify file.txt.asc file.txt

# Sign container with Cosign
cosign sign --key cosign.key registry.io/image:tag

# Verify container with Cosign
cosign verify --key cosign.pub registry.io/image:tag
```

### Security Checklist

- [ ] Use approved algorithms (RSA-PSS 3072+, ECDSA P-384+, Ed25519)
- [ ] Avoid deprecated algorithms (DSA, SHA-1, MD5, RSA-1024)
- [ ] Store private keys in HSM (FIPS 140-2 Level 2+)
- [ ] Always include timestamps
- [ ] Verify certificate chains
- [ ] Check certificate revocation (OCSP/CRL)
- [ ] Rotate keys annually
- [ ] Implement audit logging
- [ ] Test disaster recovery procedures
- [ ] Document key management procedures

---

**End of Reference Document**

For questions, updates, or contributions, see the skill documentation.
