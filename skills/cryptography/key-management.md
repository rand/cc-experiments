---
name: cryptography-key-management
description: Comprehensive cryptographic key lifecycle management, KMS integration, and compliance
---

# Cryptographic Key Management

**Scope**: Key lifecycle (generation, distribution, storage, rotation, destruction), KMS platforms (AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault), HSM integration, compliance (FIPS 140-2, PCI-DSS, HIPAA, GDPR)
**Lines**: ~500
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Implementing key generation, distribution, storage, rotation, or destruction
- Integrating with Key Management Services (AWS KMS, GCP KMS, Azure Key Vault, Vault)
- Designing key hierarchies (Root → KEK → DEK)
- Implementing envelope encryption patterns
- Meeting compliance requirements (PCI-DSS, HIPAA, FIPS 140-2, GDPR, SOC 2)
- Managing HSM integration for high-security applications
- Automating key rotation with zero-downtime
- Auditing key usage and access control
- Managing secrets (API keys, passwords, tokens)
- Implementing multi-party computation or key escrow

## Core Concepts

### Key Management Lifecycle

**Five Phases**:

```
1. Generation → 2. Distribution → 3. Storage → 4. Rotation → 5. Destruction
     ↑                                                              │
     └──────────────────────────────────────────────────────────────┘
                        (Cycle repeats)
```

**Critical Principle**: The security of encrypted data depends entirely on the security of the encryption keys.

### Key Hierarchies

**Three-Tier Model** (Recommended):

```
┌─────────────────────────────────────────────┐
│ Level 1: Root Key (Master Key)              │  ← Stored in HSM
│ - Rarely rotated (annually or never)        │  ← Rarely used
│ - Encrypts KEKs only                        │  ← FIPS 140-2 Level 3+
└───────────────────┬─────────────────────────┘
                    │ Encrypts
                    ▼
┌─────────────────────────────────────────────┐
│ Level 2: Key Encryption Key (KEK)           │  ← Stored in KMS
│ - Rotated periodically (quarterly/annually) │  ← Encrypts DEKs
│ - One KEK per application/tenant            │
└───────────────────┬─────────────────────────┘
                    │ Encrypts
                    ▼
┌─────────────────────────────────────────────┐
│ Level 3: Data Encryption Key (DEK)          │  ← Stored encrypted with data
│ - Rotated frequently (per file/record)      │  ← Encrypts actual data
│ - One DEK per file/record/tenant            │
└───────────────────┬─────────────────────────┘
                    │ Encrypts
                    ▼
            ┌──────────────────┐
            │  Encrypted Data  │
            └──────────────────┘
```

**Benefits**:
- **Efficient rotation**: Rotate KEK by re-encrypting DEKs (not data)
- **Separation of concerns**: Different keys for different purposes
- **Reduced blast radius**: Compromise of one level doesn't expose others

---

## Key Generation

### Cryptographically Secure Random Number Generators (CSRNGs)

**Platform Sources**:

| Platform | CSRNG | Entropy Source |
|----------|-------|----------------|
| Linux | `/dev/urandom` | Kernel CSPRNG (hardware RNG, interrupts, disk I/O) |
| macOS | `/dev/random` | Yarrow algorithm |
| Windows | `CryptGenRandom` | Windows CryptoAPI |
| AWS KMS | `GenerateDataKey` | FIPS 140-2 validated |
| GCP KMS | `GenerateRandomBytes` | Cloud HSM |

**Python Example**:
```python
import os
import secrets

# Generate 256-bit AES key
key = os.urandom(32)  # 32 bytes = 256 bits

# Or use secrets module (Python 3.6+)
key = secrets.token_bytes(32)
hex_key = secrets.token_hex(32)  # 64 hex characters
```

**❌ Never use**:
- `random.random()` (Python) - Predictable
- `Math.random()` (JavaScript) - Predictable
- Timestamp-based seeds
- Hardcoded keys

### Key Derivation Functions (KDFs)

**For deriving keys from passwords**:

| KDF | Standard | Security | Use Case |
|-----|----------|----------|----------|
| **Argon2id** | RFC 9106 | Highest (memory-hard) | Password hashing, key derivation (recommended) |
| **scrypt** | RFC 7914 | High (memory-hard) | Key derivation from passwords |
| **PBKDF2** | RFC 8018 | Moderate | FIPS compliance, legacy systems |
| **HKDF** | RFC 5869 | High | Key derivation from shared secrets (not passwords) |

**Argon2id Example**:
```python
from argon2 import PasswordHasher
from argon2.low_level import hash_secret_raw, Type
import secrets

password = b"user-password"
salt = secrets.token_bytes(16)

# Derive 256-bit key
key = hash_secret_raw(
    secret=password,
    salt=salt,
    time_cost=3,          # Iterations
    memory_cost=65536,    # 64 MB
    parallelism=4,        # 4 threads
    hash_len=32,          # 256-bit key
    type=Type.ID          # Argon2id
)
```

---

## Key Storage

### Storage Tiers

| Tier | Security | Cost | Use Case |
|------|----------|------|----------|
| **Tier 1: HSM** | Highest (FIPS 140-2 Level 3/4) | $$$$ | Root keys, CA keys |
| **Tier 2: Cloud KMS** | High (FIPS 140-2 Level 2/3) | $$ | Application keys, KEKs |
| **Tier 3: Encrypted DB** | Moderate | $ | Encrypted DEKs |
| **Tier 4: OS Keystore** | Moderate | $ | Local development |
| **Tier 5: Plaintext** | ❌ Never | N/A | N/A |

### Hardware Security Module (HSM)

**FIPS 140-2 Levels**:

| Level | Requirements | Use Case |
|-------|-------------|----------|
| **Level 1** | Software only | Basic applications |
| **Level 2** | Tamper-evident seals, role-based auth | Enterprise |
| **Level 3** | Tamper-resistant hardware, identity-based auth | Financial, healthcare (recommended) |
| **Level 4** | Environmental protection (voltage, temp) | Government, military |

**HSM Vendors**:
- **Cloud**: AWS CloudHSM, Google Cloud HSM, Azure Dedicated HSM
- **On-premise**: Thales Luna, nCipher nShield, Utimaco SecurityServer

### Cloud KMS Platforms

**AWS KMS**:
```python
import boto3

kms = boto3.client('kms')

# Create key
response = kms.create_key(Description='App encryption key')
key_id = response['KeyMetadata']['KeyId']

# Enable automatic rotation
kms.enable_key_rotation(KeyId=key_id)

# Encrypt data
ciphertext = kms.encrypt(KeyId=key_id, Plaintext=b'Secret data')

# Decrypt
plaintext = kms.decrypt(CiphertextBlob=ciphertext['CiphertextBlob'])
```

**HashiCorp Vault**:
```bash
# Enable transit engine
vault secrets enable transit

# Create encryption key
vault write -f transit/keys/my-key

# Encrypt
vault write transit/encrypt/my-key plaintext=$(echo "Secret data" | base64)

# Decrypt
vault write transit/decrypt/my-key ciphertext="vault:v1:..."
```

---

## Key Rotation

### Why Rotate Keys?

**Reasons**:
1. Limit blast radius of compromise
2. Compliance requirements (PCI-DSS, HIPAA)
3. Cryptographic hygiene (reduce ciphertext under single key)
4. Mitigate key exposure (employee departure, system compromise)

**Rotation Frequency**:
- **Root/Master keys**: Annually
- **KEKs**: Quarterly
- **DEKs**: Monthly or per-dataset
- **Session keys**: Per-session (ephemeral)
- **API keys/passwords**: 90 days
- **Emergency**: Immediately upon suspected compromise

### Rotation Strategies

**Strategy 1: Envelope Encryption (Zero-Downtime)**

Re-encrypt KEKs with new root key, DEKs with new KEK. Data stays encrypted with DEKs (no change).

**Strategy 2: Versioned Keys (Multi-Version)**

Keep old and new keys active. Write new data with new key, read old data with old key. Background job gradually re-encrypts.

**AWS KMS Automatic Rotation**:
```bash
# Enable automatic rotation (annual)
aws kms enable-key-rotation --key-id <key-id>

# Check rotation status
aws kms get-key-rotation-status --key-id <key-id>
```

---

## Access Control

### Principle of Least Privilege

**Best Practices**:
- Separate keys by environment (dev, staging, prod)
- Separate keys by application/tenant
- Use IAM roles (not user credentials) for applications
- Require MFA for key administrative operations
- Use encryption context for additional security
- Audit all key access (CloudTrail, Cloud Audit Logs)

**AWS KMS IAM Policy Example**:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
    "Resource": "arn:aws:kms:us-east-1:123456789012:key/*",
    "Condition": {
      "StringEquals": {
        "kms:EncryptionContext:Department": "Finance"
      }
    }
  }]
}
```

---

## Compliance Standards

### PCI-DSS Requirements

**Requirement 3.6**: Protect cryptographic keys

- **3.6.1**: Access to keys limited (need-to-know)
- **3.6.2**: Keys stored securely
- **3.6.3**: Keys distributed securely
- **3.6.4**: Keys changed at least annually (or upon suspected compromise)
- **3.6.5**: Retirement/destruction of old keys
- **3.6.6**: Split knowledge/dual control for manual key operations

### HIPAA Requirements

**Security Rule § 164.312(a)(2)(iv)**: Encryption and decryption (addressable)

- Use NIST-approved algorithms
- Encrypt ePHI at rest and in transit
- Secure key management procedures
- Access controls for encryption keys
- Audit logging

### GDPR Requirements

**Article 32**: Security of processing

- Encryption of personal data (recommended, not required)
- Pseudonymization and encryption as appropriate technical measures
- Regular testing and evaluation of security measures

### FIPS 140-2 Requirements

**Approved Algorithms**:
- Encryption: AES, Triple-DES
- Hashing: SHA-256, SHA-384, SHA-512
- Key Exchange: Diffie-Hellman, ECDH
- Signatures: RSA, ECDSA

**❌ Not Approved**:
- ChaCha20-Poly1305 (secure but not FIPS-approved)
- MD5, SHA-1 (deprecated)

---

## Best Practices

### Key Management Checklist

✅ **Generation**:
- Use CSRNG (not predictable random)
- Sufficient key length (AES-256, RSA-2048+)
- Generate in secure environment (HSM, KMS)

✅ **Distribution**:
- Use key wrapping (envelope encryption)
- Never transmit keys in plaintext
- Use separate channels for key distribution (out-of-band)

✅ **Storage**:
- Never store keys with data
- Use HSM or KMS for master keys
- Encrypt keys at rest (key hierarchy)
- Separate keys by environment

✅ **Rotation**:
- Automate rotation schedules
- Use envelope encryption for zero-downtime
- Test rotation procedures regularly
- Maintain key version history

✅ **Destruction**:
- Cryptographic erasure (destroy KEK)
- Secure overwrite (DOD 5220.22-M)
- Grace period before deletion (30-90 days)
- Audit log destruction events

✅ **Access Control**:
- Principle of least privilege
- Role-based access control (RBAC)
- Require MFA for administrative operations
- Audit all key access

✅ **Monitoring**:
- Enable audit logging (CloudTrail, Cloud Audit Logs)
- Monitor for unusual key access patterns
- Alert on failed decryption attempts
- Track key age and rotation status

---

## Anti-Patterns

**❌ Never do**:
- Hardcode keys in source code
- Store keys in version control (Git)
- Store keys in plaintext configuration files
- Use the same key for all environments
- Store keys with encrypted data
- Reuse nonces/IVs
- Use weak algorithms (DES, 3DES, RC4)
- Skip key rotation
- Allow public access to keys
- Test before committing code changes

---

## Level 3: Resources

### Reference Materials

**Comprehensive Documentation**:
- [`resources/REFERENCE.md`](resources/REFERENCE.md) - 2,000+ line technical reference covering:
  - Complete key lifecycle (generation, distribution, storage, rotation, destruction)
  - KMS platforms (AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault)
  - HSM integration (FIPS 140-2 levels, PKCS#11, vendor comparison)
  - Compliance standards (PCI-DSS, HIPAA, GDPR, SOC 2, FIPS 140-2)
  - Secrets management patterns
  - Access control and audit logging
  - Multi-party computation and key escrow
  - Detailed implementation examples

### Production Scripts

**Three executable scripts** (all with `--help` and `--json` support):

1. **`scripts/audit_keys.py`** (848 lines)
   - Comprehensive key audit across multiple KMS platforms
   - Checks key age, rotation status, compliance violations
   - Detects unused keys, overly permissive policies
   - Security score calculation
   - Multi-platform support (AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault)

2. **`scripts/rotate_master_keys.py`** (821 lines)
   - Automated master key rotation with zero-downtime
   - Re-encrypts DEKs without touching data (envelope encryption)
   - Rollback capability with backup
   - Progress tracking and resume
   - Multi-platform support (AWS KMS, GCP KMS, local, Vault)

3. **`scripts/generate_key_hierarchy.py`** (698 lines)
   - Generate complete key hierarchies (Root → KEK → DEK)
   - Configurable tiers (2 or 3 levels)
   - Multiple algorithms (AES-256, RSA-2048, ECC-P256)
   - Key wrapping and export
   - ASCII tree visualization

### Production Examples

**Five production-ready examples**:

1. **`examples/aws_kms_integration.py`**
   - Create and manage AWS KMS keys
   - Envelope encryption with GenerateDataKey
   - Automatic key rotation
   - Key policies and access control
   - Encryption context usage

2. **`examples/hashicorp_vault_setup.py`**
   - Transit secrets engine configuration
   - Key creation, rotation, and versioning
   - Encryption as a service
   - Re-wrapping (re-encrypt with new version)
   - Auto-rotation configuration

3. **`examples/key_rotation_automation.py`**
   - Automated rotation scheduling
   - Zero-downtime rotation workflow
   - CloudWatch metrics integration
   - Rollback procedures
   - Monitoring and alerting

4. **`examples/secrets_management.py`**
   - Secure API key and password storage
   - Secret versioning and rotation
   - KMS-backed encryption
   - Secure password generation
   - Audit logging

5. **`examples/compliance_config.py`**
   - Compliance policy templates (PCI-DSS, HIPAA, GDPR, SOC 2, FIPS 140-2)
   - Automated compliance validation
   - Key lifecycle enforcement
   - Audit trail generation
   - Violation reporting

### Usage

**Run scripts**:
```bash
# Audit all keys in AWS KMS
./scripts/audit_keys.py --platform aws-kms --region us-east-1 --json

# Rotate master key
./scripts/rotate_master_keys.py --platform aws-kms --key-id alias/master-key

# Generate 3-tier key hierarchy
./scripts/generate_key_hierarchy.py --tiers 3 --dek-count 100 --visualize
```

**Integrate examples**:
```python
# Use AWS KMS integration
from examples.aws_kms_integration import AWSKMSKeyManager

manager = AWSKMSKeyManager(region='us-east-1')
envelope = manager.encrypt_with_envelope(plaintext, 'alias/my-key')
decrypted = manager.decrypt_with_envelope(envelope)
```

---

## Quick Reference

### Common Commands

**AWS KMS**:
```bash
# Create key
aws kms create-key --description "App key"

# Enable rotation
aws kms enable-key-rotation --key-id <key-id>

# Encrypt
aws kms encrypt --key-id alias/my-key --plaintext fileb://secret.txt

# Decrypt
aws kms decrypt --ciphertext-blob fileb://encrypted.bin
```

**HashiCorp Vault**:
```bash
# Enable transit
vault secrets enable transit

# Create key
vault write -f transit/keys/my-key

# Encrypt
vault write transit/encrypt/my-key plaintext=$(base64 <<< "secret")

# Rotate
vault write -f transit/keys/my-key/rotate
```

**Google Cloud KMS**:
```bash
# Create key ring
gcloud kms keyrings create my-keyring --location global

# Create key
gcloud kms keys create my-key --location global --keyring my-keyring --purpose encryption

# Encrypt
gcloud kms encrypt --location global --keyring my-keyring --key my-key --plaintext-file secret.txt --ciphertext-file encrypted.bin
```

---

## Related Skills

- **cryptography-encryption-at-rest** - Protecting stored data
- **security-tls-configuration** - Certificates and TLS key management
- **cryptography-crypto-best-practices** - Cryptographic implementation guidelines
- **security-secrets-management** - Application secrets and credentials

---

## Resources

### Standards and Specifications

- **NIST SP 800-57**: Recommendation for Key Management
- **NIST SP 800-175B**: Guideline for Using Cryptographic Standards
- **FIPS 140-2**: Security Requirements for Cryptographic Modules
- **RFC 5869**: HKDF (HMAC-based Key Derivation Function)
- **RFC 9106**: Argon2 Memory-Hard Function

### Compliance Resources

- **PCI-DSS Requirement 3**: Protect stored cardholder data
- **HIPAA Security Rule**: Encryption and Decryption
- **GDPR Article 32**: Security of processing
- **SOC 2 Trust Services Criteria**: Confidentiality

### Tools and Libraries

- **AWS KMS**: https://aws.amazon.com/kms/
- **Google Cloud KMS**: https://cloud.google.com/kms
- **Azure Key Vault**: https://azure.microsoft.com/en-us/services/key-vault/
- **HashiCorp Vault**: https://www.vaultproject.io/
- **Python cryptography**: https://cryptography.io/
