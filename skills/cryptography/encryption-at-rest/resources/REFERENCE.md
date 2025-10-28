# Encryption at Rest Reference

Comprehensive technical reference for encryption at rest, key management, and compliance standards.

## Table of Contents

1. [Fundamentals](#fundamentals)
2. [Encryption Algorithms](#encryption-algorithms)
3. [Key Management](#key-management)
4. [Envelope Encryption](#envelope-encryption)
5. [Database Encryption](#database-encryption)
6. [File and Disk Encryption](#file-and-disk-encryption)
7. [Cloud KMS Integration](#cloud-kms-integration)
8. [Key Rotation](#key-rotation)
9. [Compliance Standards](#compliance-standards)
10. [Performance Considerations](#performance-considerations)
11. [Common Patterns](#common-patterns)
12. [Anti-Patterns](#anti-patterns)
13. [Security Best Practices](#security-best-practices)
14. [Implementation Examples](#implementation-examples)

---

## Fundamentals

### What is Encryption at Rest?

**Encryption at rest** protects data stored on disk from unauthorized access. Unlike encryption in transit (TLS/SSL), encryption at rest protects data when it's not actively being transmitted.

**Key Differences**:

| Aspect | Encryption at Rest | Encryption in Transit |
|--------|-------------------|----------------------|
| **Protects** | Stored data on disk | Data moving over network |
| **Threat Model** | Physical access, disk theft, backups | Network eavesdropping, MITM |
| **Typical Use** | Databases, files, backups, volumes | HTTPS, TLS, SSH |
| **Performance** | One-time cost on read/write | Continuous overhead during transmission |
| **Key Lifetime** | Long-lived (months/years) | Short-lived (session keys) |

### Threat Model

**What encryption at rest protects against**:
- **Physical theft**: Stolen laptops, hard drives, backup tapes
- **Cloud provider access**: Unauthorized access by cloud staff
- **Forensic recovery**: Data recovery from decommissioned drives
- **Backup compromise**: Stolen or leaked backup files
- **Snapshot access**: Unauthorized access to volume snapshots
- **Insider threats**: Malicious employees with physical access

**What it does NOT protect against**:
- **Application-level attacks**: SQL injection, XSS, CSRF
- **Authorized user access**: Users with valid credentials
- **Memory dumps**: Data in RAM is not encrypted
- **Side-channel attacks**: Timing attacks, cache attacks
- **Compromised encryption keys**: If attacker has keys, encryption is useless

### Encryption Layers

```
┌─────────────────────────────────────────┐
│ Application-Level Encryption            │  ← Column/field encryption (highest control)
├─────────────────────────────────────────┤
│ Database-Level Encryption               │  ← TDE (Transparent Data Encryption)
├─────────────────────────────────────────┤
│ Filesystem-Level Encryption             │  ← eCryptfs, EncFS
├─────────────────────────────────────────┤
│ Volume/Block-Level Encryption           │  ← LUKS, dm-crypt, BitLocker
├─────────────────────────────────────────┤
│ Hardware-Level Encryption               │  ← Self-encrypting drives (SEDs)
└─────────────────────────────────────────┘
```

**Trade-offs**:

| Layer | Granularity | Performance | Key Management | Flexibility |
|-------|-------------|-------------|----------------|-------------|
| Application | Per-field | Slowest | Most complex | Highest |
| Database | Per-database | Fast | Moderate | Moderate |
| Filesystem | Per-file | Moderate | Moderate | Moderate |
| Volume | Per-volume | Fast | Simple | Low |
| Hardware | Per-drive | Fastest | Simple | Lowest |

### When to Use Each Layer

**Application-Level**:
- Need per-field encryption (e.g., credit card numbers)
- Compliance requires end-to-end encryption
- Different users need different keys
- Zero-trust architecture

**Database-Level**:
- Encrypt entire database with minimal code changes
- Compliance requires encryption at rest
- Centralized key management
- Performance is critical

**Filesystem-Level**:
- Encrypt user directories or shared folders
- Protect files from OS-level access
- Need per-user encryption

**Volume-Level**:
- Encrypt entire disk/partition
- Protect against physical theft
- Simplest to implement
- Minimal performance overhead

**Hardware-Level**:
- Best performance
- No OS support required
- Limited key management control

---

## Encryption Algorithms

### Symmetric Encryption

**Definition**: Same key used for encryption and decryption.

**Use Case**: Encryption at rest (fast, efficient).

#### AES (Advanced Encryption Standard)

**Overview**:
- **Standard**: FIPS 197 (2001)
- **Block Size**: 128 bits
- **Key Sizes**: 128, 192, 256 bits
- **Status**: Industry standard, NIST approved

**Modes of Operation**:

| Mode | Properties | Use Case | Security |
|------|-----------|----------|----------|
| **ECB** (Electronic Codebook) | Deterministic, no IV | ❌ NEVER USE | Insecure |
| **CBC** (Cipher Block Chaining) | Requires IV, sequential | Legacy systems | Secure with IV |
| **CTR** (Counter) | Parallel, requires nonce | Performance-critical | Secure with unique nonce |
| **GCM** (Galois/Counter Mode) | AEAD, parallel, auth tag | Modern apps | Best choice |
| **XTS** (XEX-based tweaked-codebook) | Disk encryption | Full-disk encryption | Optimized for storage |

**Recommended**: **AES-256-GCM** (authenticated encryption with associated data).

**Example (OpenSSL)**:
```bash
# Encrypt file with AES-256-GCM
openssl enc -aes-256-gcm -salt -in plaintext.txt -out encrypted.bin -k password

# Decrypt
openssl enc -aes-256-gcm -d -in encrypted.bin -out plaintext.txt -k password
```

**Python Example (cryptography library)**:
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

# Generate key (256 bits)
key = AESGCM.generate_key(bit_length=256)
aesgcm = AESGCM(key)

# Generate nonce (96 bits recommended for GCM)
nonce = os.urandom(12)

# Encrypt
plaintext = b"Secret data"
ciphertext = aesgcm.encrypt(nonce, plaintext, None)

# Decrypt
decrypted = aesgcm.decrypt(nonce, ciphertext, None)
assert decrypted == plaintext
```

**Go Example**:
```go
package main

import (
    "crypto/aes"
    "crypto/cipher"
    "crypto/rand"
    "io"
)

func encryptAESGCM(plaintext, key []byte) ([]byte, error) {
    block, err := aes.NewCipher(key)
    if err != nil {
        return nil, err
    }

    aesGCM, err := cipher.NewGCM(block)
    if err != nil {
        return nil, err
    }

    nonce := make([]byte, aesGCM.NonceSize())
    if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
        return nil, err
    }

    // Prepend nonce to ciphertext
    ciphertext := aesGCM.Seal(nonce, nonce, plaintext, nil)
    return ciphertext, nil
}
```

**Performance**:
- **Hardware acceleration**: AES-NI (Intel), ARMv8 Crypto Extensions
- **Throughput**: 2-10 GB/s with hardware acceleration
- **Latency**: ~1-5 microseconds per operation

#### ChaCha20-Poly1305

**Overview**:
- **Standard**: RFC 8439 (2018)
- **Algorithm**: Stream cipher (ChaCha20) + MAC (Poly1305)
- **Key Size**: 256 bits
- **Nonce Size**: 96 bits (12 bytes)
- **Use Case**: Mobile devices without AES-NI, software-only systems

**Advantages over AES**:
- Faster on systems without AES-NI
- Constant-time implementation (resistant to timing attacks)
- Simpler to implement correctly

**Python Example**:
```python
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import os

# Generate key
key = ChaCha20Poly1305.generate_key()
chacha = ChaCha20Poly1305(key)

# Generate nonce
nonce = os.urandom(12)

# Encrypt
plaintext = b"Secret data"
ciphertext = chacha.encrypt(nonce, plaintext, None)

# Decrypt
decrypted = chacha.decrypt(nonce, ciphertext, None)
assert decrypted == plaintext
```

**When to use ChaCha20-Poly1305**:
- Mobile devices (ARM without crypto extensions)
- Software-only encryption
- Need constant-time implementation
- Alternative to AES-GCM

**When to use AES-GCM**:
- x86/x64 processors with AES-NI
- Hardware acceleration available
- Compliance requires FIPS-approved algorithms

#### Deprecated/Insecure Algorithms

**❌ Never use**:
- **DES** (Data Encryption Standard) - 56-bit key, broken
- **3DES** (Triple DES) - 112-bit effective key, deprecated
- **RC4** - Stream cipher, broken
- **Blowfish** - 64-bit block size, vulnerable to birthday attacks

**Key Takeaways**:
- Use **AES-256-GCM** or **ChaCha20-Poly1305**
- Always use authenticated encryption (AEAD)
- Never reuse nonces
- Use hardware acceleration when available

---

## Key Management

### Key Hierarchy

**Principle**: Separate encryption keys from data encryption keys (DEKs).

```
┌──────────────────────────────────────────┐
│ Root Key (Master Key)                    │  ← Stored in HSM or KMS
│ - Rarely changed                         │
│ - Used to encrypt KEKs                   │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ Key Encryption Key (KEK)                 │  ← Encrypted by root key
│ - Changed periodically (e.g., yearly)    │
│ - Used to encrypt DEKs                   │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ Data Encryption Key (DEK)                │  ← Encrypted by KEK
│ - Changed frequently (e.g., daily)       │
│ - Used to encrypt actual data            │
└──────────────┬───────────────────────────┘
               │
               ▼
       ┌──────────────────┐
       │ Encrypted Data   │  ← Encrypted by DEK
       └──────────────────┘
```

**Benefits**:
- **Key rotation**: Rotate KEKs without re-encrypting all data
- **Performance**: Encrypt DEKs (small) instead of data (large)
- **Security**: Compromise of DEK doesn't expose root key

### Key Generation

**Cryptographically Secure Random Number Generators (CSRNGs)**:

| Language | CSRNG Function | Entropy Source |
|----------|---------------|----------------|
| Python | `os.urandom()`, `secrets` | `/dev/urandom` (Linux), CryptGenRandom (Windows) |
| Go | `crypto/rand.Reader` | `/dev/urandom` |
| Node.js | `crypto.randomBytes()` | OpenSSL |
| OpenSSL | `RAND_bytes()` | `/dev/urandom` |

**❌ Never use**:
- `random.random()` (Python) - Predictable
- `Math.random()` (JavaScript) - Predictable
- `rand()` (C) - Predictable
- Timestamp-based keys
- Hardcoded keys

**✅ Good key generation**:
```python
import os
import secrets

# Generate 256-bit key (32 bytes)
key = os.urandom(32)

# Or use secrets module (Python 3.6+)
key = secrets.token_bytes(32)

# Generate key from password (DO NOT use directly, see KDF section)
```

### Key Derivation Functions (KDFs)

**Purpose**: Derive encryption keys from passwords or passphrases.

**Problem**: Passwords are low-entropy, weak keys.
**Solution**: Use KDF to derive strong keys from passwords.

#### PBKDF2 (Password-Based Key Derivation Function 2)

**Standard**: RFC 8018 (PKCS #5)
**Algorithm**: HMAC + iteration count
**Parameters**:
- Password/passphrase
- Salt (16+ bytes, random)
- Iteration count (100,000+ for HMAC-SHA256)
- Key length (32 bytes for AES-256)

**Python Example**:
```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os

password = b"user-password"
salt = os.urandom(16)

kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,  # 256 bits
    salt=salt,
    iterations=480000,  # OWASP recommendation (2023)
)

key = kdf.derive(password)
```

**Pros**: FIPS-approved, widely supported
**Cons**: Vulnerable to GPU/ASIC attacks

#### Argon2

**Standard**: RFC 9106 (2021)
**Algorithm**: Memory-hard KDF
**Variants**:
- **Argon2i**: Optimized for resistance to side-channel attacks
- **Argon2d**: Optimized for resistance to GPU attacks
- **Argon2id**: Hybrid (recommended)

**Parameters**:
- Password
- Salt (16+ bytes)
- Time cost (iterations)
- Memory cost (KB)
- Parallelism (threads)

**Python Example**:
```python
from argon2 import PasswordHasher
import os

ph = PasswordHasher(
    time_cost=3,        # Number of iterations
    memory_cost=65536,  # 64 MB
    parallelism=4,      # 4 threads
    hash_len=32,        # 256-bit key
    salt_len=16,
)

password = "user-password"  # Example only - in production, get from secure input
hash_str = ph.hash(password)

# Verify
try:
    ph.verify(hash_str, password)
    print("Password correct")
except:
    print("Password incorrect")
```

**Pros**: Memory-hard (resistant to GPU/ASIC attacks), winner of Password Hashing Competition (2015)
**Cons**: Not FIPS-approved (yet)

#### scrypt

**Standard**: RFC 7914 (2016)
**Algorithm**: Memory-hard KDF
**Parameters**:
- Password
- Salt (16+ bytes)
- N (CPU/memory cost factor, power of 2, e.g., 2^14)
- r (block size, e.g., 8)
- p (parallelization factor, e.g., 1)

**Python Example**:
```python
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import os

password = b"user-password"
salt = os.urandom(16)

kdf = Scrypt(
    salt=salt,
    length=32,
    n=2**14,  # CPU/memory cost factor
    r=8,      # Block size
    p=1,      # Parallelization factor
)

key = kdf.derive(password)
```

**Pros**: Memory-hard, widely supported
**Cons**: Complex parameter tuning

#### Recommendations

**For password hashing (authentication)**:
- **First choice**: Argon2id
- **FIPS compliance**: PBKDF2-HMAC-SHA256 (480,000+ iterations)
- **Legacy systems**: bcrypt

**For key derivation (encryption)**:
- **First choice**: Argon2id or scrypt
- **FIPS compliance**: PBKDF2-HMAC-SHA256

### Key Storage

**❌ Never store keys**:
- Hardcoded in source code
- In configuration files (plaintext)
- In version control (Git)
- In environment variables (for production)
- In application logs
- In databases (unencrypted)

**✅ Secure key storage**:

#### Option 1: Hardware Security Module (HSM)

**What**: Dedicated hardware for key storage and cryptographic operations.

**Features**:
- Keys never leave HSM
- FIPS 140-2 Level 3/4 certified
- Tamper-resistant
- Expensive ($10K-$100K+)

**Use Case**: High-security environments (banks, government).

**Examples**:
- Thales Luna HSM
- AWS CloudHSM
- Google Cloud HSM
- Azure Dedicated HSM

#### Option 2: Cloud Key Management Service (KMS)

**What**: Managed service for key storage and encryption.

**Features**:
- API-based key management
- Automatic key rotation
- Access control (IAM)
- Audit logging
- Lower cost ($1-$10/month per key)

**Use Case**: Cloud-native applications.

**Examples**:
- AWS KMS
- Google Cloud KMS
- Azure Key Vault
- HashiCorp Vault

#### Option 3: Software-Based Key Management

**What**: Store keys encrypted with master key.

**Pattern**:
1. Generate master key (stored securely, e.g., HSM or KMS)
2. Encrypt data encryption keys (DEKs) with master key
3. Store encrypted DEKs alongside encrypted data

**Example (envelope encryption)**:
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import json

# Master key (stored in KMS or HSM)
master_key = os.urandom(32)
master_aesgcm = AESGCM(master_key)

# Generate DEK for this data
dek = AESGCM.generate_key(bit_length=256)
dek_nonce = os.urandom(12)

# Encrypt DEK with master key
encrypted_dek = master_aesgcm.encrypt(dek_nonce, dek, None)

# Encrypt data with DEK
data_aesgcm = AESGCM(dek)
data_nonce = os.urandom(12)
plaintext = b"Sensitive data"
ciphertext = data_aesgcm.encrypt(data_nonce, plaintext, None)

# Store encrypted DEK + ciphertext
envelope = {
    "encrypted_dek": encrypted_dek.hex(),
    "dek_nonce": dek_nonce.hex(),
    "ciphertext": ciphertext.hex(),
    "data_nonce": data_nonce.hex(),
}

print(json.dumps(envelope, indent=2))
```

**Decryption**:
```python
# Load envelope
envelope = json.loads(envelope_json)

# Decrypt DEK with master key
dek = master_aesgcm.decrypt(
    bytes.fromhex(envelope["dek_nonce"]),
    bytes.fromhex(envelope["encrypted_dek"]),
    None
)

# Decrypt data with DEK
data_aesgcm = AESGCM(dek)
plaintext = data_aesgcm.decrypt(
    bytes.fromhex(envelope["data_nonce"]),
    bytes.fromhex(envelope["ciphertext"]),
    None
)
```

#### Option 4: Operating System Keystore

**What**: OS-provided secure storage (e.g., macOS Keychain, Windows Credential Manager).

**Use Case**: Desktop applications, local development.

**Python Example (macOS Keychain)**:
```python
import keyring

# Store key
keyring.set_password("myapp", "encryption_key", "base64-encoded-key")

# Retrieve key
key = keyring.get_password("myapp", "encryption_key")
```

### Key Access Control

**Principle of Least Privilege**: Only authorized users/services should access keys.

**AWS KMS Example (IAM Policy)**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
      "Condition": {
        "StringEquals": {
          "kms:EncryptionContext:AppName": "myapp"
        }
      }
    }
  ]
}
```

**Best Practices**:
- Use separate keys for different environments (dev, staging, prod)
- Use separate keys for different applications
- Rotate keys regularly
- Audit key access (CloudTrail, Stackdriver, Azure Monitor)
- Use encryption context for additional security

---

## Envelope Encryption

### Concept

**Problem**: Encrypting large amounts of data with KMS is slow and expensive (API calls).

**Solution**:
1. Generate Data Encryption Key (DEK) locally
2. Encrypt data with DEK (fast, local)
3. Encrypt DEK with KMS (small, one API call)
4. Store encrypted DEK + encrypted data together

**Flow**:
```
┌─────────────┐
│  Plaintext  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│ Generate DEK (local)        │
│ key = os.urandom(32)        │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│ Encrypt data with DEK       │
│ ciphertext = encrypt(       │
│   plaintext, dek            │
│ )                           │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│ Encrypt DEK with KMS        │  ← One API call
│ encrypted_dek = kms.encrypt(│
│   dek                       │
│ )                           │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│ Store encrypted_dek +       │
│       ciphertext            │
└─────────────────────────────┘
```

**Decryption**:
```
┌─────────────────────────────┐
│ Load encrypted_dek +        │
│      ciphertext             │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│ Decrypt DEK with KMS        │  ← One API call
│ dek = kms.decrypt(          │
│   encrypted_dek             │
│ )                           │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│ Decrypt data with DEK       │
│ plaintext = decrypt(        │
│   ciphertext, dek           │
│ )                           │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────┐
│  Plaintext  │
└─────────────┘
```

### AWS KMS Envelope Encryption

**Python Example**:
```python
import boto3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import json

kms = boto3.client('kms')
KMS_KEY_ID = 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012'

def encrypt_file(plaintext, kms_key_id):
    """Encrypt file using envelope encryption with AWS KMS"""

    # 1. Generate DEK (plaintext key)
    response = kms.generate_data_key(
        KeyId=kms_key_id,
        KeySpec='AES_256'
    )

    dek_plaintext = response['Plaintext']      # DEK (plaintext)
    dek_encrypted = response['CiphertextBlob']  # DEK encrypted by KMS

    # 2. Encrypt data with DEK
    aesgcm = AESGCM(dek_plaintext)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # 3. Return envelope (encrypted DEK + ciphertext)
    return {
        'encrypted_dek': dek_encrypted,
        'ciphertext': ciphertext,
        'nonce': nonce,
    }

def decrypt_file(envelope, kms_key_id):
    """Decrypt file using envelope encryption with AWS KMS"""

    # 1. Decrypt DEK with KMS
    response = kms.decrypt(
        CiphertextBlob=envelope['encrypted_dek']
    )
    dek_plaintext = response['Plaintext']

    # 2. Decrypt data with DEK
    aesgcm = AESGCM(dek_plaintext)
    plaintext = aesgcm.decrypt(
        envelope['nonce'],
        envelope['ciphertext'],
        None
    )

    return plaintext

# Usage
plaintext = b"Sensitive data to encrypt"
envelope = encrypt_file(plaintext, KMS_KEY_ID)
decrypted = decrypt_file(envelope, KMS_KEY_ID)
assert decrypted == plaintext
```

### Google Cloud KMS Envelope Encryption

**Python Example**:
```python
from google.cloud import kms
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt_with_gcp_kms(plaintext, project_id, location_id, key_ring_id, key_id):
    """Encrypt using envelope encryption with GCP KMS"""

    # Initialize KMS client
    client = kms.KeyManagementServiceClient()
    key_name = client.crypto_key_path(project_id, location_id, key_ring_id, key_id)

    # 1. Generate DEK locally
    dek = AESGCM.generate_key(bit_length=256)

    # 2. Encrypt data with DEK
    aesgcm = AESGCM(dek)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # 3. Encrypt DEK with KMS
    encrypt_response = client.encrypt(
        request={'name': key_name, 'plaintext': dek}
    )
    encrypted_dek = encrypt_response.ciphertext

    return {
        'encrypted_dek': encrypted_dek,
        'ciphertext': ciphertext,
        'nonce': nonce,
    }

def decrypt_with_gcp_kms(envelope, project_id, location_id, key_ring_id, key_id):
    """Decrypt using envelope encryption with GCP KMS"""

    client = kms.KeyManagementServiceClient()
    key_name = client.crypto_key_path(project_id, location_id, key_ring_id, key_id)

    # 1. Decrypt DEK with KMS
    decrypt_response = client.decrypt(
        request={'name': key_name, 'ciphertext': envelope['encrypted_dek']}
    )
    dek = decrypt_response.plaintext

    # 2. Decrypt data with DEK
    aesgcm = AESGCM(dek)
    plaintext = aesgcm.decrypt(
        envelope['nonce'],
        envelope['ciphertext'],
        None
    )

    return plaintext
```

### Benefits of Envelope Encryption

1. **Performance**: Local encryption (fast) + one KMS call (small overhead)
2. **Cost**: Fewer KMS API calls
3. **Scalability**: Can encrypt large files without KMS payload limits
4. **Key rotation**: Rotate master key without re-encrypting data (just re-encrypt DEKs)

---

## Database Encryption

### Transparent Data Encryption (TDE)

**What**: Database-level encryption that encrypts entire database files.

**How it works**:
1. Database generates master key
2. Database encrypts data pages before writing to disk
3. Database decrypts data pages after reading from disk
4. Applications see plaintext (transparent)

**Pros**:
- No application changes required
- Encrypts all data (tables, indexes, logs)
- Protects backups
- Minimal performance overhead (~3-10%)

**Cons**:
- Database has full access to keys
- All-or-nothing (can't encrypt specific columns)
- Doesn't protect against application-level attacks

### PostgreSQL TDE

**Status**: Not natively supported (as of PostgreSQL 16).

**Alternatives**:
1. **pgcrypto extension**: Column-level encryption
2. **Filesystem-level encryption**: LUKS, dm-crypt
3. **Cloud provider TDE**: AWS RDS, Google Cloud SQL

**pgcrypto Example (Column-Level Encryption)**:
```sql
-- Enable pgcrypto extension
CREATE EXTENSION pgcrypto;

-- Encrypt data
INSERT INTO users (email, encrypted_ssn)
VALUES (
    'user@example.com',
    pgp_sym_encrypt('123-45-6789', 'encryption-password')
);

-- Decrypt data
SELECT
    email,
    pgp_sym_decrypt(encrypted_ssn::bytea, 'encryption-password') AS ssn
FROM users;
```

**Best Practice**: Use envelope encryption with KMS instead of hardcoded password:
```sql
-- Store encrypted DEK alongside data
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255),
    encrypted_ssn BYTEA,
    encrypted_dek BYTEA,  -- DEK encrypted by KMS
    dek_nonce BYTEA
);

-- Application encrypts SSN with DEK, encrypts DEK with KMS
-- Store both encrypted_ssn and encrypted_dek
```

### MySQL TDE

**Support**: MySQL 5.7+ (Enterprise), MariaDB 10.1+

**Setup**:
```sql
-- Enable TDE plugin
INSTALL PLUGIN keyring_file SONAME 'keyring_file.so';

-- Configure keyring in my.cnf
[mysqld]
early-plugin-load=keyring_file.so
keyring_file_data=/var/lib/mysql-keyring/keyring

-- Create encrypted table
CREATE TABLE users (
    id INT PRIMARY KEY,
    email VARCHAR(255),
    ssn VARCHAR(11)
) ENCRYPTION='Y';

-- Encrypt existing table
ALTER TABLE users ENCRYPTION='Y';
```

**Key Rotation**:
```sql
-- Rotate master key
ALTER INSTANCE ROTATE INNODB MASTER KEY;
```

### MongoDB Encryption at Rest

**Support**: MongoDB 3.2+ (Enterprise, Atlas)

**Configuration** (mongod.conf):
```yaml
security:
  enableEncryption: true
  encryptionKeyFile: /etc/mongodb-keyfile

# Or use KMIP (Key Management Interoperability Protocol)
security:
  enableEncryption: true
  kmip:
    serverName: kmip.example.com
    port: 5696
    clientCertificateFile: /etc/mongodb-client.pem
```

**Encrypted Storage Engine**:
- Uses AES-256-CBC
- Encrypts data files, journals, logs
- Keys stored in keyfile or KMIP server
- Automatic decryption on read

**Encrypted Collections** (Client-Side Field Level Encryption - CSFLE):
```javascript
const { ClientEncryption } = require('mongodb-client-encryption');

// Setup encryption options
const encryptionOptions = {
  keyVaultNamespace: 'encryption.__keyVault',
  kmsProviders: {
    aws: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    }
  }
};

// Create encrypted client
const client = new MongoClient(uri, {
  autoEncryption: encryptionOptions
});

// Create data key
const encryption = new ClientEncryption(client, encryptionOptions);
const dataKeyId = await encryption.createDataKey('aws', {
  masterKey: {
    key: 'arn:aws:kms:us-east-1:123456789012:key/12345678',
    region: 'us-east-1'
  }
});

// Create collection with encrypted fields
await db.createCollection('users', {
  validator: {
    $jsonSchema: {
      properties: {
        ssn: {
          encrypt: {
            keyId: [dataKeyId],
            algorithm: 'AEAD_AES_256_CBC_HMAC_SHA_512-Deterministic'
          }
        }
      }
    }
  }
});

// Insert encrypted data (automatic)
await db.collection('users').insertOne({
  name: 'John Doe',
  ssn: '123-45-6789'  // Automatically encrypted
});
```

### SQLite Encryption

**Native**: SQLite doesn't support encryption natively.

**Extensions**:
1. **SQLCipher**: Open-source SQLite extension
2. **SEE (SQLite Encryption Extension)**: Commercial

**SQLCipher Setup (Python)**:
```python
from pysqlcipher3 import dbapi2 as sqlite3

# Connect to encrypted database
conn = sqlite3.connect('encrypted.db')
conn.execute("PRAGMA key='strong-password'")

# Set encryption algorithm
conn.execute("PRAGMA cipher='aes-256-cbc'")

# Create table and insert data
conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)')
conn.execute("INSERT INTO users (email) VALUES ('user@example.com')")
conn.commit()
```

**Key Derivation**: SQLCipher uses PBKDF2-HMAC-SHA512 by default.

**Rekey** (change password):
```python
conn.execute("PRAGMA rekey='new-strong-password'")
```

---

## File and Disk Encryption

### Linux: LUKS (Linux Unified Key Setup)

**What**: Standard disk encryption on Linux.

**Features**:
- Full-disk or partition encryption
- Multiple key slots (up to 8 passphrases/keys)
- Uses dm-crypt kernel module
- Supports AES, XTS mode

**Setup**:
```bash
# Format partition with LUKS
sudo cryptsetup luksFormat /dev/sdb1

# Open encrypted partition
sudo cryptsetup luksOpen /dev/sdb1 encrypted_disk

# Create filesystem
sudo mkfs.ext4 /dev/mapper/encrypted_disk

# Mount
sudo mount /dev/mapper/encrypted_disk /mnt/encrypted

# Auto-mount on boot (add to /etc/crypttab)
echo "encrypted_disk /dev/sdb1 none luks" | sudo tee -a /etc/crypttab

# Add to /etc/fstab
echo "/dev/mapper/encrypted_disk /mnt/encrypted ext4 defaults 0 2" | sudo tee -a /etc/fstab
```

**Key Management**:
```bash
# Add new key slot
sudo cryptsetup luksAddKey /dev/sdb1

# Remove key slot
sudo cryptsetup luksRemoveKey /dev/sdb1

# Backup LUKS header
sudo cryptsetup luksHeaderBackup /dev/sdb1 --header-backup-file luks-header-backup

# Restore LUKS header
sudo cryptsetup luksHeaderRestore /dev/sdb1 --header-backup-file luks-header-backup
```

**Key File** (instead of passphrase):
```bash
# Generate key file
dd if=/dev/urandom of=/root/keyfile bs=1024 count=4
chmod 600 /root/keyfile

# Add key file to LUKS
sudo cryptsetup luksAddKey /dev/sdb1 /root/keyfile

# Open with key file
sudo cryptsetup luksOpen /dev/sdb1 encrypted_disk --key-file /root/keyfile
```

### eCryptfs (Enterprise Cryptographic Filesystem)

**What**: Stacked filesystem encryption (per-directory).

**Use Case**: Encrypt user home directories.

**Setup**:
```bash
# Install eCryptfs
sudo apt-get install ecryptfs-utils

# Setup encrypted directory
mkdir ~/Private
sudo mount -t ecryptfs ~/Private ~/Private

# Configure encryption options (interactive)
# - Key type: passphrase
# - Cipher: aes
# - Key bytes: 32 (AES-256)
# - Plaintext passthrough: no
# - Filename encryption: yes

# Add to /etc/fstab for auto-mount
/home/user/Private /home/user/Private ecryptfs defaults 0 0
```

**Encrypting Home Directory**:
```bash
# Migrate existing home directory to encrypted
ecryptfs-migrate-home -u username
```

### Windows: BitLocker

**What**: Full-disk encryption on Windows (Pro/Enterprise).

**Setup** (via GUI):
1. Control Panel → BitLocker Drive Encryption
2. Turn on BitLocker for drive
3. Choose authentication method (password, smart card, TPM)
4. Save recovery key
5. Encrypt drive

**Setup** (via PowerShell):
```powershell
# Enable BitLocker with password
Enable-BitLocker -MountPoint "C:" -PasswordProtector -Password (ConvertTo-SecureString "password" -AsPlainText -Force)

# Backup recovery key
Backup-BitLockerKeyProtector -MountPoint "C:" -KeyProtectorId (Get-BitLockerVolume -MountPoint "C:").KeyProtector[0].KeyProtectorId -Path "C:\recovery-key.txt"

# Encrypt drive
Resume-BitLocker -MountPoint "C:"
```

**TPM (Trusted Platform Module)**: Hardware chip that stores encryption keys.

**Recovery Key**: 48-digit recovery password, stored in Active Directory or printed.

### macOS: FileVault 2

**What**: Full-disk encryption on macOS.

**Setup** (via GUI):
1. System Preferences → Security & Privacy → FileVault
2. Turn On FileVault
3. Choose recovery method (iCloud or recovery key)
4. Restart to encrypt

**Setup** (via command line):
```bash
# Enable FileVault
sudo fdesetup enable

# Check status
sudo fdesetup status

# List enabled users
sudo fdesetup list
```

**Recovery Key**: 24-character alphanumeric key, store securely.

### File-Level Encryption (GPG)

**What**: Encrypt individual files with GPG (GNU Privacy Guard).

**Setup**:
```bash
# Generate GPG key pair
gpg --full-generate-key

# Encrypt file
gpg --encrypt --recipient user@example.com file.txt

# Decrypt file
gpg --decrypt file.txt.gpg > file.txt
```

**Symmetric Encryption** (password-based):
```bash
# Encrypt
gpg --symmetric --cipher-algo AES256 file.txt

# Decrypt
gpg --decrypt file.txt.gpg > file.txt
```

---

## Cloud KMS Integration

### AWS KMS

**Features**:
- Managed key storage
- FIPS 140-2 Level 2 validated
- Automatic key rotation (annual)
- Audit logging (CloudTrail)
- Integration with AWS services (S3, EBS, RDS)

**Setup**:
```bash
# Create KMS key
aws kms create-key --description "My encryption key"

# Create alias
aws kms create-alias --alias-name alias/my-key --target-key-id 12345678-1234-1234-1234-123456789012

# Enable automatic key rotation
aws kms enable-key-rotation --key-id 12345678-1234-1234-1234-123456789012
```

**Python SDK**:
```python
import boto3

kms = boto3.client('kms')

# Encrypt data directly (max 4 KB)
response = kms.encrypt(
    KeyId='alias/my-key',
    Plaintext=b'Secret data',
    EncryptionContext={'Department': 'Finance'}
)
ciphertext = response['CiphertextBlob']

# Decrypt
response = kms.decrypt(
    CiphertextBlob=ciphertext,
    EncryptionContext={'Department': 'Finance'}
)
plaintext = response['Plaintext']

# Generate data key (for envelope encryption)
response = kms.generate_data_key(
    KeyId='alias/my-key',
    KeySpec='AES_256'
)
dek_plaintext = response['Plaintext']
dek_encrypted = response['CiphertextBlob']
```

**Encryption Context**: Additional authenticated data (AAD) for additional security.

**Key Policies** (IAM-like permissions for keys):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Enable IAM User Permissions",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:root"
      },
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "Allow use of the key for encryption",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
      },
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey",
        "kms:GenerateDataKey"
      ],
      "Resource": "*"
    }
  ]
}
```

### Google Cloud KMS

**Features**:
- Managed key storage
- FIPS 140-2 Level 3 validated (HSM option)
- Automatic key rotation (configurable)
- Audit logging (Cloud Audit Logs)
- Integration with GCP services (GCS, GCE, BigQuery)

**Setup**:
```bash
# Create key ring
gcloud kms keyrings create my-keyring --location us-east1

# Create key
gcloud kms keys create my-key \
  --location us-east1 \
  --keyring my-keyring \
  --purpose encryption

# Enable automatic rotation (90 days)
gcloud kms keys update my-key \
  --location us-east1 \
  --keyring my-keyring \
  --rotation-period 90d \
  --next-rotation-time 2025-12-01T00:00:00Z
```

**Python SDK**:
```python
from google.cloud import kms

client = kms.KeyManagementServiceClient()

# Key resource name
key_name = 'projects/my-project/locations/us-east1/keyRings/my-keyring/cryptoKeys/my-key'

# Encrypt
plaintext = b'Secret data'
encrypt_response = client.encrypt(
    request={'name': key_name, 'plaintext': plaintext}
)
ciphertext = encrypt_response.ciphertext

# Decrypt
decrypt_response = client.decrypt(
    request={'name': key_name, 'ciphertext': ciphertext}
)
plaintext = decrypt_response.plaintext
```

**IAM Permissions**:
```bash
# Grant encrypt/decrypt permissions
gcloud kms keys add-iam-policy-binding my-key \
  --location us-east1 \
  --keyring my-keyring \
  --member serviceAccount:my-app@my-project.iam.gserviceaccount.com \
  --role roles/cloudkms.cryptoKeyEncrypterDecrypter
```

### Azure Key Vault

**Features**:
- Managed key storage
- FIPS 140-2 Level 2 validated (Premium: HSM)
- Automatic key rotation (configurable)
- Audit logging (Azure Monitor)
- Integration with Azure services (Storage, SQL, VMs)

**Setup**:
```bash
# Create Key Vault
az keyvault create \
  --name my-keyvault \
  --resource-group my-rg \
  --location eastus

# Create key
az keyvault key create \
  --vault-name my-keyvault \
  --name my-key \
  --protection software \
  --kty RSA \
  --size 2048

# Enable automatic rotation
az keyvault key rotation-policy update \
  --vault-name my-keyvault \
  --name my-key \
  --value '{"lifetimeActions":[{"trigger":{"timeAfterCreate":"P90D"},"action":{"type":"Rotate"}}],"attributes":{"expiryTime":"P2Y"}}'
```

**Python SDK**:
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm

credential = DefaultAzureCredential()
key_url = "https://my-keyvault.vault.azure.net/keys/my-key"

crypto_client = CryptographyClient(key_url, credential)

# Encrypt
plaintext = b"Secret data"
result = crypto_client.encrypt(EncryptionAlgorithm.rsa_oaep, plaintext)
ciphertext = result.ciphertext

# Decrypt
result = crypto_client.decrypt(EncryptionAlgorithm.rsa_oaep, ciphertext)
plaintext = result.plaintext
```

**Access Policies**:
```bash
# Grant permissions to application
az keyvault set-policy \
  --name my-keyvault \
  --object-id <app-object-id> \
  --key-permissions encrypt decrypt get list
```

### HashiCorp Vault

**What**: Open-source secrets management and encryption service.

**Features**:
- Encryption as a Service (Transit Secrets Engine)
- Dynamic secrets
- Secrets versioning
- Audit logging
- Self-hosted or managed (HCP Vault)

**Setup**:
```bash
# Start Vault dev server (testing only)
vault server -dev

# Set VAULT_ADDR
export VAULT_ADDR='http://127.0.0.1:8200'

# Enable Transit secrets engine
vault secrets enable transit

# Create encryption key
vault write -f transit/keys/my-key
```

**Encrypt/Decrypt**:
```bash
# Encrypt
vault write transit/encrypt/my-key plaintext=$(echo "Secret data" | base64)

# Output:
# Key           Value
# ciphertext    vault:v1:8SDd3WHDOjf7mq69CyCqYjBXAiQQAVZRkFM96F4qzA==

# Decrypt
vault write transit/decrypt/my-key ciphertext="vault:v1:8SDd3WHDOjf7mq69CyCqYjBXAiQQAVZRkFM96F4qzA=="

# Output (base64 encoded):
# plaintext     U2VjcmV0IGRhdGE=

# Decode
echo "U2VjcmV0IGRhdGE=" | base64 -d
# Output: Secret data
```

**Python SDK (hvac)**:
```python
import hvac
import base64

client = hvac.Client(url='http://127.0.0.1:8200', token='dev-token')

# Encrypt
plaintext = b'Secret data'
response = client.secrets.transit.encrypt_data(
    name='my-key',
    plaintext=base64.b64encode(plaintext).decode('utf-8')
)
ciphertext = response['data']['ciphertext']

# Decrypt
response = client.secrets.transit.decrypt_data(
    name='my-key',
    ciphertext=ciphertext
)
plaintext = base64.b64decode(response['data']['plaintext'])
```

**Key Rotation**:
```bash
# Rotate key (creates new version)
vault write -f transit/keys/my-key/rotate

# Re-encrypt data with new key version
vault write transit/rewrap/my-key ciphertext="vault:v1:8SDd3WHDOjf7mq69CyCqYjBXAiQQAVZRkFM96F4qzA=="
```

---

## Key Rotation

### Why Rotate Keys?

**Reasons**:
1. **Limit blast radius**: Compromise of old key doesn't affect new data
2. **Compliance**: Many standards require periodic rotation (e.g., PCI-DSS)
3. **Cryptographic hygiene**: Reduce ciphertext exposure
4. **Mitigate key exposure**: Employee departure, system compromise

**How Often?**:
- **Master keys**: Annually
- **Data encryption keys (DEKs)**: Monthly or per dataset
- **Secrets (passwords, API keys)**: 90 days
- **Emergency rotation**: Immediately on suspected compromise

### Rotation Strategies

#### Strategy 1: Re-encrypt All Data (Complete Rotation)

**How**:
1. Generate new key
2. Decrypt all data with old key
3. Encrypt all data with new key
4. Update key references
5. Delete old key (after grace period)

**Pros**: Clean, simple
**Cons**: Expensive (re-encrypt all data), downtime, risky

**Use Case**: Small datasets, infrequent rotation.

**Example**:
```python
def rotate_complete(old_key, new_key, data_files):
    for file_path in data_files:
        # Read encrypted data
        with open(file_path, 'rb') as f:
            ciphertext = f.read()

        # Decrypt with old key
        plaintext = decrypt(ciphertext, old_key)

        # Encrypt with new key
        new_ciphertext = encrypt(plaintext, new_key)

        # Write back
        with open(file_path, 'wb') as f:
            f.write(new_ciphertext)
```

#### Strategy 2: Envelope Encryption (Zero-Downtime Rotation)

**How** (using key hierarchy):
1. Generate new KEK (Key Encryption Key)
2. Re-encrypt all DEKs with new KEK
3. Data stays encrypted with DEKs (no change)
4. Update KEK references
5. Delete old KEK

**Pros**: Fast (only re-encrypt DEKs, not data), no downtime
**Cons**: Requires key hierarchy

**Use Case**: Large datasets, cloud KMS.

**Flow**:
```
Before Rotation:
┌────────────────┐
│  Old KEK       │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Encrypted DEKs │ ← Re-encrypt these (small)
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Encrypted Data │ ← Leave unchanged (large)
└────────────────┘

After Rotation:
┌────────────────┐
│  New KEK       │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Encrypted DEKs │ ← Re-encrypted with new KEK
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Encrypted Data │ ← Unchanged
└────────────────┘
```

**Example**:
```python
def rotate_envelope(old_kek, new_kek, encrypted_deks):
    """Rotate KEK without touching data"""
    for record in encrypted_deks:
        # Decrypt DEK with old KEK
        dek = decrypt(record['encrypted_dek'], old_kek)

        # Re-encrypt DEK with new KEK
        new_encrypted_dek = encrypt(dek, new_kek)

        # Update database
        update_dek(record['id'], new_encrypted_dek)

        # Data encrypted with DEK remains unchanged
```

#### Strategy 3: Versioned Keys (Multi-Version)

**How**:
1. Keep both old and new keys active
2. Write new data with new key
3. Read old data with old key
4. Gradually re-encrypt old data (background job)
5. Retire old key after all data migrated

**Pros**: Zero downtime, gradual migration
**Cons**: Complex (need to track key versions)

**Use Case**: Large datasets, continuous writes.

**Schema Example**:
```sql
CREATE TABLE encrypted_data (
    id SERIAL PRIMARY KEY,
    ciphertext BYTEA,
    key_version INTEGER,  -- Track which key encrypted this row
    created_at TIMESTAMP
);
```

**Application Logic**:
```python
def read_data(record_id):
    record = db.query("SELECT * FROM encrypted_data WHERE id = ?", record_id)

    # Use key version to select correct key
    if record['key_version'] == 1:
        key = old_key
    elif record['key_version'] == 2:
        key = new_key
    else:
        raise ValueError(f"Unknown key version: {record['key_version']}")

    plaintext = decrypt(record['ciphertext'], key)
    return plaintext

def write_data(plaintext):
    # Always use latest key for new data
    ciphertext = encrypt(plaintext, new_key)
    db.execute(
        "INSERT INTO encrypted_data (ciphertext, key_version) VALUES (?, ?)",
        ciphertext, 2
    )

def background_reencryption():
    """Gradually re-encrypt old data"""
    while True:
        # Get batch of old records
        old_records = db.query(
            "SELECT * FROM encrypted_data WHERE key_version = 1 LIMIT 100"
        )

        if not old_records:
            break  # All done

        for record in old_records:
            # Decrypt with old key
            plaintext = decrypt(record['ciphertext'], old_key)

            # Re-encrypt with new key
            new_ciphertext = encrypt(plaintext, new_key)

            # Update record
            db.execute(
                "UPDATE encrypted_data SET ciphertext = ?, key_version = ? WHERE id = ?",
                new_ciphertext, 2, record['id']
            )

        time.sleep(1)  # Rate limit
```

### AWS KMS Automatic Key Rotation

**How**:
- KMS automatically rotates key material annually
- Old key versions retained (for decryption)
- New encryptions use new key version
- Application code unchanged (KMS handles versioning)

**Enable**:
```bash
aws kms enable-key-rotation --key-id 12345678-1234-1234-1234-123456789012
```

**How It Works Internally**:
```
Key ARN: arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012

Key Versions:
- v1 (2024-01-01): Used for old ciphertext
- v2 (2025-01-01): Used for new encryptions (current)

Encryption: Uses v2
Decryption: KMS automatically detects version and uses correct key material
```

**No Application Changes Required**.

### Manual Key Rotation (Non-KMS)

**Procedure**:
1. Generate new key
2. Update application config to use new key for encryptions
3. Keep old key for decryptions
4. Re-encrypt data in background (optional)
5. Remove old key after grace period

**Configuration Example**:
```yaml
# keys.yaml
encryption_keys:
  - id: key-v1
    key: <base64-encoded-key>
    created_at: 2024-01-01
    deprecated: true  # Don't use for new encryptions
  - id: key-v2
    key: <base64-encoded-key>
    created_at: 2025-01-01
    deprecated: false  # Active key
```

**Application Logic**:
```python
def get_active_key():
    """Get current key for encryptions"""
    for key in config['encryption_keys']:
        if not key['deprecated']:
            return key
    raise ValueError("No active key found")

def get_key_by_id(key_id):
    """Get key by ID for decryptions"""
    for key in config['encryption_keys']:
        if key['id'] == key_id:
            return key
    raise ValueError(f"Key not found: {key_id}")

def encrypt_with_rotation(plaintext):
    """Encrypt with active key, store key ID"""
    key = get_active_key()
    ciphertext = encrypt(plaintext, key['key'])
    return {
        'key_id': key['id'],
        'ciphertext': ciphertext
    }

def decrypt_with_rotation(envelope):
    """Decrypt using key ID"""
    key = get_key_by_id(envelope['key_id'])
    plaintext = decrypt(envelope['ciphertext'], key['key'])
    return plaintext
```

---

## Compliance Standards

### FIPS 140-2 (Federal Information Processing Standards)

**What**: US government standard for cryptographic modules.

**Levels**:
- **Level 1**: Basic security (software only)
- **Level 2**: Tamper-evident seals, role-based authentication
- **Level 3**: Tamper-resistant hardware (HSM), identity-based authentication
- **Level 4**: Environmental failure protection (temperature, voltage)

**Approved Algorithms**:
- **Encryption**: AES, Triple-DES
- **Hashing**: SHA-256, SHA-384, SHA-512
- **Key Exchange**: Diffie-Hellman, ECDH
- **Signatures**: RSA, ECDSA

**NOT Approved**:
- ChaCha20-Poly1305 (not FIPS-approved, but secure)
- MD5, SHA-1 (deprecated)

**Cloud KMS FIPS Compliance**:
- AWS KMS: FIPS 140-2 Level 2 (standard), Level 3 (CloudHSM)
- Google Cloud KMS: FIPS 140-2 Level 3 (HSM)
- Azure Key Vault: FIPS 140-2 Level 2 (standard), Level 3 (Premium HSM)

### GDPR (General Data Protection Regulation)

**Requirement**: Article 32 - "Appropriate technical and organizational measures" including encryption.

**Key Points**:
- Encrypt personal data at rest and in transit
- Pseudonymization and encryption recommended
- No specific algorithms mandated (risk-based approach)
- Data breach notification required (encryption reduces risk)

**Best Practices**:
- Use AES-256-GCM or stronger
- Encrypt all personal data (names, emails, etc.)
- Key management separate from data storage
- Regular key rotation
- Audit logging

### HIPAA (Health Insurance Portability and Accountability Act)

**Requirement**: "Encryption and decryption" (addressable safeguard under Security Rule).

**Standards**:
- Use NIST-approved algorithms
- Encryption at rest for ePHI (electronic Protected Health Information)
- Encryption in transit (TLS 1.2+)
- Access controls for encryption keys
- Audit logging

**Recommended**:
- AES-256
- Key management via KMS or HSM
- Separate keys for different data types
- Annual key rotation

### PCI-DSS (Payment Card Industry Data Security Standard)

**Requirement**: 3.4 - "Render PAN [Primary Account Number] unreadable anywhere it is stored."

**Methods**:
1. **Encryption**: AES-128 or stronger
2. **Truncation**: Store only last 4 digits
3. **Tokenization**: Replace PAN with token
4. **Hashing**: One-way hash (with salt)

**Key Management Requirements** (3.5-3.6):
- Split knowledge of keys (no single person has full key)
- Dual control (two people required for key operations)
- Key rotation at least annually
- Secure key storage (HSM or KMS)
- Audit logging of key access

**Example (Tokenization)**:
```python
import secrets
import hashlib

# Store token → encrypted PAN mapping in secure vault
token_vault = {}

def tokenize_pan(pan):
    """Replace PAN with random token"""
    token = secrets.token_urlsafe(16)

    # Encrypt PAN before storing
    encrypted_pan = encrypt(pan, kms_key)
    token_vault[token] = encrypted_pan

    return token

def detokenize(token):
    """Retrieve PAN from token"""
    encrypted_pan = token_vault.get(token)
    if not encrypted_pan:
        raise ValueError("Invalid token")

    pan = decrypt(encrypted_pan, kms_key)
    return pan

# Usage
pan = "4111111111111111"
token = tokenize_pan(pan)  # "xYz123..."
print(f"Store token: {token}")

# Retrieve
original_pan = detokenize(token)
assert original_pan == pan
```

### SOC 2 (System and Organization Controls 2)

**Requirement**: Trust Services Criteria (TSC) - Confidentiality.

**Key Points**:
- Encrypt sensitive data at rest
- Encrypt data in transit
- Key management procedures documented
- Access controls for keys
- Audit logging and monitoring

**Compliance Checklist**:
- [ ] Encryption policy documented
- [ ] Encryption algorithms approved (AES-256, etc.)
- [ ] Key management procedures (generation, storage, rotation, destruction)
- [ ] Access controls (who can access keys)
- [ ] Audit logging enabled
- [ ] Incident response plan (key compromise)
- [ ] Annual review of encryption practices

---

## Performance Considerations

### Encryption Overhead

**Typical Performance Impact**:

| Layer | Overhead | Mitigation |
|-------|----------|------------|
| Application-level | 10-30% | Hardware acceleration, caching |
| Database TDE | 3-10% | Hardware acceleration, async encryption |
| Filesystem | 5-15% | Hardware acceleration, kernel optimization |
| Volume/disk | 2-5% | Hardware acceleration (AES-NI), SSD |
| Hardware (SED) | <1% | Built-in encryption |

### Hardware Acceleration

#### AES-NI (Intel/AMD)

**What**: CPU instruction set for AES encryption.

**Check Support** (Linux):
```bash
grep -o aes /proc/cpuinfo
```

**Performance**:
- **Without AES-NI**: ~100-500 MB/s
- **With AES-NI**: 2-10 GB/s (10-20x faster)

**Enable in Code** (automatic with modern libraries):
```python
# cryptography library automatically uses AES-NI if available
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
# No configuration needed - hardware acceleration automatic
```

**OpenSSL** (check):
```bash
openssl speed aes-256-gcm
```

#### ARM Crypto Extensions

**What**: ARMv8 Crypto Extensions (similar to AES-NI).

**Check Support**:
```bash
grep -o aes /proc/cpuinfo
```

**Performance**: Similar to x86 AES-NI (2-5 GB/s).

### Caching Decrypted Data

**Problem**: Decrypting on every read is expensive.

**Solution**: Cache decrypted data in memory (with TTL).

**Example**:
```python
from functools import lru_cache
import time

# Cache decrypted data (max 1000 items)
@lru_cache(maxsize=1000)
def decrypt_cached(ciphertext, key):
    return decrypt(ciphertext, key)

# Time-based cache (TTL = 5 minutes)
cache = {}

def decrypt_with_ttl(ciphertext, key, ttl=300):
    cache_key = hashlib.sha256(ciphertext).hexdigest()

    if cache_key in cache:
        plaintext, timestamp = cache[cache_key]
        if time.time() - timestamp < ttl:
            return plaintext  # Cache hit

    # Cache miss - decrypt
    plaintext = decrypt(ciphertext, key)
    cache[cache_key] = (plaintext, time.time())
    return plaintext
```

**Trade-offs**:
- **Pros**: Faster reads
- **Cons**: Memory usage, cache invalidation complexity, data in RAM (unencrypted)

### Encryption Parallelization

**GCM Mode**: Supports parallel encryption/decryption (unlike CBC).

**Example (Multi-threaded Encryption)**:
```python
from concurrent.futures import ThreadPoolExecutor
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt_chunk(chunk, key):
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, chunk, None)
    return (nonce, ciphertext)

def encrypt_large_file_parallel(file_path, key, chunk_size=1024*1024):
    """Encrypt large file in parallel chunks"""
    with open(file_path, 'rb') as f:
        chunks = []
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            chunks.append(chunk)

    # Encrypt chunks in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        encrypted_chunks = list(executor.map(
            lambda chunk: encrypt_chunk(chunk, key),
            chunks
        ))

    return encrypted_chunks
```

### Benchmarking Encryption Performance

**OpenSSL Benchmark**:
```bash
# Benchmark AES-256-GCM
openssl speed -evp aes-256-gcm

# Benchmark multiple algorithms
openssl speed aes-256-gcm chacha20-poly1305 aes-128-cbc
```

**Python Benchmark**:
```python
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
import os

def benchmark_encryption(algorithm, plaintext, iterations=10000):
    if algorithm == 'aes-gcm':
        key = AESGCM.generate_key(bit_length=256)
        cipher = AESGCM(key)
    elif algorithm == 'chacha20':
        key = ChaCha20Poly1305.generate_key()
        cipher = ChaCha20Poly1305(key)

    nonce = os.urandom(12)

    start = time.time()
    for _ in range(iterations):
        ciphertext = cipher.encrypt(nonce, plaintext, None)
    elapsed = time.time() - start

    throughput = (len(plaintext) * iterations) / elapsed / 1024 / 1024
    print(f"{algorithm}: {throughput:.2f} MB/s")

# Test
plaintext = b"A" * 1024  # 1 KB
benchmark_encryption('aes-gcm', plaintext)
benchmark_encryption('chacha20', plaintext)
```

---

## Common Patterns

### Pattern 1: Column-Level Encryption (Application-Level)

**Use Case**: Encrypt specific sensitive columns (e.g., SSN, credit card).

**Schema**:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255),
    encrypted_ssn BYTEA,  -- Encrypted SSN
    encrypted_dek BYTEA,  -- DEK encrypted by KMS
    dek_nonce BYTEA
);
```

**Application**:
```python
def insert_user(email, ssn, kms_key):
    # Generate DEK
    dek = AESGCM.generate_key(bit_length=256)
    dek_nonce = os.urandom(12)

    # Encrypt DEK with KMS
    encrypted_dek = kms.encrypt(KeyId=kms_key, Plaintext=dek)['CiphertextBlob']

    # Encrypt SSN with DEK
    aesgcm = AESGCM(dek)
    ssn_nonce = os.urandom(12)
    encrypted_ssn = aesgcm.encrypt(ssn_nonce, ssn.encode(), None)

    # Store
    db.execute(
        "INSERT INTO users (email, encrypted_ssn, encrypted_dek, dek_nonce) VALUES (?, ?, ?, ?)",
        email, encrypted_ssn, encrypted_dek, dek_nonce
    )

def get_user_ssn(user_id, kms_key):
    row = db.query("SELECT * FROM users WHERE id = ?", user_id)

    # Decrypt DEK with KMS
    dek = kms.decrypt(CiphertextBlob=row['encrypted_dek'])['Plaintext']

    # Decrypt SSN with DEK
    aesgcm = AESGCM(dek)
    ssn = aesgcm.decrypt(row['dek_nonce'], row['encrypted_ssn'], None)
    return ssn.decode()
```

### Pattern 2: File Encryption with Metadata

**Use Case**: Encrypt files, store metadata alongside.

**File Structure**:
```
encrypted_file.bin:
  - Header (256 bytes):
    - Version (4 bytes)
    - Algorithm (16 bytes, e.g., "aes-256-gcm")
    - Key ID (32 bytes)
    - Nonce (12 bytes)
    - Encrypted DEK (varies)
  - Ciphertext (remaining bytes)
```

**Implementation**:
```python
import struct
import json

def encrypt_file_with_metadata(input_path, output_path, kms_key_id):
    # Read plaintext
    with open(input_path, 'rb') as f:
        plaintext = f.read()

    # Generate DEK
    dek = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)

    # Encrypt DEK with KMS
    kms_response = kms.encrypt(KeyId=kms_key_id, Plaintext=dek)
    encrypted_dek = kms_response['CiphertextBlob']

    # Encrypt file with DEK
    aesgcm = AESGCM(dek)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # Build header
    header = {
        'version': 1,
        'algorithm': 'aes-256-gcm',
        'key_id': kms_key_id,
        'nonce': nonce.hex(),
        'encrypted_dek': encrypted_dek.hex(),
    }
    header_json = json.dumps(header).encode('utf-8')
    header_len = len(header_json)

    # Write encrypted file
    with open(output_path, 'wb') as f:
        f.write(struct.pack('<I', header_len))  # Header length (4 bytes)
        f.write(header_json)
        f.write(ciphertext)

def decrypt_file_with_metadata(input_path, output_path):
    with open(input_path, 'rb') as f:
        # Read header length
        header_len = struct.unpack('<I', f.read(4))[0]

        # Read header
        header_json = f.read(header_len)
        header = json.loads(header_json)

        # Read ciphertext
        ciphertext = f.read()

    # Decrypt DEK with KMS
    dek = kms.decrypt(
        CiphertextBlob=bytes.fromhex(header['encrypted_dek'])
    )['Plaintext']

    # Decrypt file
    aesgcm = AESGCM(dek)
    plaintext = aesgcm.decrypt(
        bytes.fromhex(header['nonce']),
        ciphertext,
        None
    )

    # Write plaintext
    with open(output_path, 'wb') as f:
        f.write(plaintext)
```

### Pattern 3: Searchable Encryption (Deterministic)

**Problem**: Can't search encrypted data (ciphertext is random).

**Solution**: Deterministic encryption (same plaintext → same ciphertext).

**⚠️ Security Trade-off**: Reveals equality (can see if two values are same).

**Use Case**: Encrypt email addresses, but allow searching by email.

**Algorithm**: AES-SIV (Synthetic IV) - deterministic AEAD.

**Python Example**:
```python
from cryptography.hazmat.primitives.ciphers.aead import AESSIV

# Generate key (2x key size for SIV)
key = AESSIV.generate_key(bit_length=512)  # AES-256-SIV needs 512-bit key
aessiv = AESSIV(key)

# Encrypt (deterministic)
email1 = b"user@example.com"
ciphertext1 = aessiv.encrypt(email1, None)

email2 = b"user@example.com"
ciphertext2 = aessiv.encrypt(email2, None)

# Same plaintext → same ciphertext
assert ciphertext1 == ciphertext2  # Allows searching

# Store
db.execute(
    "INSERT INTO users (email_encrypted) VALUES (?)",
    ciphertext1
)

# Search
search_email = b"user@example.com"
search_ciphertext = aessiv.encrypt(search_email, None)
results = db.query(
    "SELECT * FROM users WHERE email_encrypted = ?",
    search_ciphertext
)
```

**⚠️ Warning**: Don't use deterministic encryption for high-entropy data (e.g., SSNs). Use only for low-sensitivity, searchable fields.

### Pattern 4: Key Per Tenant (Multi-Tenancy)

**Use Case**: SaaS application with multiple customers.

**Goal**: Each tenant has separate encryption key (data isolation).

**Schema**:
```sql
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    kms_key_id VARCHAR(255)  -- Separate KMS key per tenant
);

CREATE TABLE tenant_data (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    encrypted_data BYTEA,
    nonce BYTEA
);
```

**Application**:
```python
def insert_tenant_data(tenant_id, plaintext):
    # Get tenant's KMS key
    tenant = db.query("SELECT kms_key_id FROM tenants WHERE id = ?", tenant_id)
    kms_key_id = tenant['kms_key_id']

    # Encrypt with tenant's key
    envelope = encrypt_with_kms(plaintext, kms_key_id)

    db.execute(
        "INSERT INTO tenant_data (tenant_id, encrypted_data, nonce) VALUES (?, ?, ?)",
        tenant_id, envelope['ciphertext'], envelope['nonce']
    )

def get_tenant_data(tenant_id, record_id):
    # Get tenant's KMS key
    tenant = db.query("SELECT kms_key_id FROM tenants WHERE id = ?", tenant_id)
    kms_key_id = tenant['kms_key_id']

    # Get encrypted data
    record = db.query(
        "SELECT * FROM tenant_data WHERE id = ? AND tenant_id = ?",
        record_id, tenant_id
    )

    # Decrypt with tenant's key
    plaintext = decrypt_with_kms(record, kms_key_id)
    return plaintext
```

**Benefits**:
- Data isolation (key per tenant)
- Tenant-specific key rotation
- Compliance (some customers require dedicated keys)
- Key revocation (disable tenant's key)

---

## Anti-Patterns

### ❌ Hardcoded Keys

**Bad**:
```python
# NEVER DO THIS
AES_KEY = b'my-secret-key-12345678901234567890'

def encrypt(plaintext):
    aesgcm = AESGCM(AES_KEY)
    nonce = os.urandom(12)
    return aesgcm.encrypt(nonce, plaintext, None)
```

**Why**: Keys in source code → Git history → compromised.

**Fix**: Use environment variables (dev) or KMS (production).

```python
import os

# Load from environment variable
AES_KEY = os.environ['AES_KEY'].encode()

# Or load from KMS
kms_response = kms.decrypt(CiphertextBlob=encrypted_key)
AES_KEY = kms_response['Plaintext']
```

### ❌ Weak Algorithms

**Bad**:
```python
from Crypto.Cipher import DES  # NEVER USE DES

key = b'12345678'  # 56-bit key (too weak)
cipher = DES.new(key, DES.MODE_ECB)
ciphertext = cipher.encrypt(plaintext)
```

**Why**: DES is broken (can be cracked in hours).

**Fix**: Use AES-256-GCM.

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

key = AESGCM.generate_key(bit_length=256)
aesgcm = AESGCM(key)
nonce = os.urandom(12)
ciphertext = aesgcm.encrypt(nonce, plaintext, None)
```

### ❌ ECB Mode

**Bad**:
```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

cipher = Cipher(algorithms.AES(key), modes.ECB())
encryptor = cipher.encryptor()
ciphertext = encryptor.update(plaintext) + encryptor.finalize()
```

**Why**: ECB reveals patterns (same plaintext → same ciphertext block).

**Famous Example**: [ECB Penguin](https://en.wikipedia.org/wiki/Block_cipher_mode_of_operation#Electronic_Codebook_(ECB))

**Fix**: Use GCM mode.

### ❌ Reusing Nonces

**Bad**:
```python
nonce = b'12345678'  # Fixed nonce
aesgcm = AESGCM(key)

ciphertext1 = aesgcm.encrypt(nonce, plaintext1, None)  # Same nonce
ciphertext2 = aesgcm.encrypt(nonce, plaintext2, None)  # Same nonce (BAD!)
```

**Why**: Nonce reuse breaks GCM security (can recover key).

**Fix**: Generate new nonce for each encryption.

```python
nonce1 = os.urandom(12)
ciphertext1 = aesgcm.encrypt(nonce1, plaintext1, None)

nonce2 = os.urandom(12)
ciphertext2 = aesgcm.encrypt(nonce2, plaintext2, None)
```

### ❌ No Authentication (Encryption Without MAC)

**Bad**:
```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

cipher = Cipher(algorithms.AES(key), modes.CTR(nonce))
encryptor = cipher.encryptor()
ciphertext = encryptor.update(plaintext) + encryptor.finalize()
# No authentication - attacker can modify ciphertext
```

**Why**: Unauthenticated encryption is vulnerable to tampering (e.g., bit flipping).

**Fix**: Use authenticated encryption (AEAD) like GCM.

```python
aesgcm = AESGCM(key)
ciphertext = aesgcm.encrypt(nonce, plaintext, None)  # Includes auth tag
```

### ❌ Storing Keys with Data

**Bad**:
```python
# Store key in same database as encrypted data
db.execute(
    "INSERT INTO users (name, encrypted_ssn, encryption_key) VALUES (?, ?, ?)",
    name, encrypted_ssn, key
)
```

**Why**: If attacker gets database, they get both data and keys.

**Fix**: Store keys separately (KMS, HSM, separate database).

### ❌ No Key Rotation

**Bad**:
```python
# Use same key forever
KEY = load_key_from_config()  # Never changes
```

**Why**: Long-lived keys increase blast radius of compromise.

**Fix**: Implement key rotation strategy (see Key Rotation section).

---

## Security Best Practices

### 1. Use Authenticated Encryption (AEAD)

**Always use**:
- AES-GCM
- ChaCha20-Poly1305
- AES-SIV (deterministic)

**Never use**:
- AES-CBC without HMAC
- AES-CTR without HMAC
- AES-ECB

### 2. Generate Keys Properly

**✅ Use CSRNGs**:
```python
import os
import secrets

key = os.urandom(32)  # Good
key = secrets.token_bytes(32)  # Good
```

**❌ Never use**:
```python
import random

key = random.randbytes(32)  # BAD (predictable)
key = hashlib.sha256(b"password").digest()  # BAD (no KDF)
```

### 3. Never Hardcode Keys

**✅ Environment variables (dev)**:
```python
key = os.environ['ENCRYPTION_KEY']
```

**✅ KMS (production)**:
```python
response = kms.decrypt(CiphertextBlob=encrypted_key)
key = response['Plaintext']
```

### 4. Use Key Hierarchies

**Pattern**:
```
Root Key (KMS/HSM)
  └─> KEK (Key Encryption Key)
       └─> DEK (Data Encryption Key)
            └─> Data
```

### 5. Rotate Keys Regularly

**Schedule**:
- Master keys: Annually
- DEKs: Monthly or per dataset
- Secrets: 90 days

### 6. Audit Key Access

**Enable logging**:
- AWS CloudTrail (KMS key usage)
- Google Cloud Audit Logs
- Azure Monitor

**Monitor for**:
- Unusual key access patterns
- Failed decryption attempts
- Key deletion attempts

### 7. Separate Keys by Environment

**Good**:
```
keys/
├── dev/encryption-key
├── staging/encryption-key
└── prod/encryption-key
```

**Bad**:
```
# Same key for all environments
ENCRYPTION_KEY=abc123...
```

### 8. Encrypt Backups

**Always encrypt**:
- Database backups
- File backups
- Volume snapshots

**Example**:
```bash
# Encrypt backup with GPG
tar czf - /var/lib/postgresql | gpg --encrypt --recipient admin@example.com > backup.tar.gz.gpg

# Decrypt
gpg --decrypt backup.tar.gz.gpg | tar xzf -
```

### 9. Use Encryption Context (AAD)

**What**: Additional Authenticated Data - authenticated but not encrypted.

**Use Case**: Bind ciphertext to specific context (user ID, resource ID).

**AWS KMS Example**:
```python
response = kms.encrypt(
    KeyId='alias/my-key',
    Plaintext=plaintext,
    EncryptionContext={
        'UserId': '12345',
        'ResourceId': 'file-abc'
    }
)

# Decryption requires same context
plaintext = kms.decrypt(
    CiphertextBlob=ciphertext,
    EncryptionContext={
        'UserId': '12345',
        'ResourceId': 'file-abc'
    }
)
```

**Benefit**: Prevents ciphertext from being decrypted in wrong context.

### 10. Secure Key Deletion

**Process**:
1. Disable key (prevent new encryptions)
2. Grace period (30 days)
3. Delete key
4. Audit logging

**AWS KMS**:
```bash
# Schedule key deletion (7-30 day waiting period)
aws kms schedule-key-deletion --key-id 12345678-1234-1234-1234-123456789012 --pending-window-in-days 30

# Cancel deletion (if needed)
aws kms cancel-key-deletion --key-id 12345678-1234-1234-1234-123456789012
```

---

## Implementation Examples

### Example 1: Encrypting Files with AWS KMS

```python
import boto3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import json

kms = boto3.client('kms')
KMS_KEY_ID = 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012'

def encrypt_file(input_path, output_path):
    """Encrypt file using envelope encryption"""
    # Read file
    with open(input_path, 'rb') as f:
        plaintext = f.read()

    # Generate DEK
    response = kms.generate_data_key(KeyId=KMS_KEY_ID, KeySpec='AES_256')
    dek_plaintext = response['Plaintext']
    dek_encrypted = response['CiphertextBlob']

    # Encrypt file with DEK
    aesgcm = AESGCM(dek_plaintext)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # Save encrypted file + metadata
    envelope = {
        'encrypted_dek': dek_encrypted.hex(),
        'nonce': nonce.hex(),
        'ciphertext': ciphertext.hex(),
    }

    with open(output_path, 'w') as f:
        json.dump(envelope, f)

def decrypt_file(input_path, output_path):
    """Decrypt file"""
    # Load envelope
    with open(input_path, 'r') as f:
        envelope = json.load(f)

    # Decrypt DEK
    dek_plaintext = kms.decrypt(
        CiphertextBlob=bytes.fromhex(envelope['encrypted_dek'])
    )['Plaintext']

    # Decrypt file
    aesgcm = AESGCM(dek_plaintext)
    plaintext = aesgcm.decrypt(
        bytes.fromhex(envelope['nonce']),
        bytes.fromhex(envelope['ciphertext']),
        None
    )

    # Save decrypted file
    with open(output_path, 'wb') as f:
        f.write(plaintext)

# Usage
encrypt_file('secret.txt', 'secret.txt.encrypted')
decrypt_file('secret.txt.encrypted', 'secret.txt.decrypted')
```

### Example 2: Database Column Encryption

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64

class EncryptedField:
    """SQLAlchemy custom type for encrypted fields"""

    def __init__(self, key):
        self.key = key
        self.aesgcm = AESGCM(key)

    def encrypt(self, plaintext):
        """Encrypt plaintext"""
        if plaintext is None:
            return None

        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode(), None)

        # Prepend nonce to ciphertext
        encrypted_data = nonce + ciphertext
        return base64.b64encode(encrypted_data).decode('utf-8')

    def decrypt(self, encrypted_data):
        """Decrypt ciphertext"""
        if encrypted_data is None:
            return None

        encrypted_bytes = base64.b64decode(encrypted_data)

        # Extract nonce and ciphertext
        nonce = encrypted_bytes[:12]
        ciphertext = encrypted_bytes[12:]

        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')

# Usage with SQLAlchemy
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# Load encryption key
ENCRYPTION_KEY = os.urandom(32)  # In production, load from KMS
encrypted_field = EncryptedField(ENCRYPTION_KEY)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String)
    _encrypted_ssn = Column('encrypted_ssn', String)

    @property
    def ssn(self):
        return encrypted_field.decrypt(self._encrypted_ssn)

    @ssn.setter
    def ssn(self, value):
        self._encrypted_ssn = encrypted_field.encrypt(value)

# Create database
engine = create_engine('sqlite:///encrypted.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

# Insert encrypted data
user = User(email='user@example.com', ssn='123-45-6789')
session.add(user)
session.commit()

# Retrieve and decrypt
user = session.query(User).first()
print(f"Email: {user.email}")
print(f"SSN: {user.ssn}")  # Automatically decrypted
```

### Example 3: Zero-Downtime Key Rotation

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import time

class KeyRotator:
    def __init__(self, old_key, new_key):
        self.old_key = old_key
        self.new_key = new_key
        self.old_aesgcm = AESGCM(old_key)
        self.new_aesgcm = AESGCM(new_key)

    def re_encrypt_deks(self, db):
        """Re-encrypt all DEKs with new key"""
        records = db.query("SELECT id, encrypted_dek, dek_nonce FROM encrypted_data")

        for record in records:
            # Decrypt DEK with old key
            dek = self.old_aesgcm.decrypt(
                record['dek_nonce'],
                record['encrypted_dek'],
                None
            )

            # Re-encrypt DEK with new key
            new_nonce = os.urandom(12)
            new_encrypted_dek = self.new_aesgcm.encrypt(new_nonce, dek, None)

            # Update database
            db.execute(
                "UPDATE encrypted_data SET encrypted_dek = ?, dek_nonce = ? WHERE id = ?",
                new_encrypted_dek, new_nonce, record['id']
            )

            print(f"Re-encrypted DEK for record {record['id']}")

        print("Key rotation complete!")

# Usage
old_key = os.urandom(32)  # Current key
new_key = os.urandom(32)  # New key

rotator = KeyRotator(old_key, new_key)
rotator.re_encrypt_deks(db)
```

---

## References

### Standards and Specifications

1. **NIST SP 800-175B**: Guideline for Using Cryptographic Standards
   - https://csrc.nist.gov/publications/detail/sp/800-175b/rev-1/final

2. **NIST SP 800-57**: Recommendation for Key Management
   - https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final

3. **FIPS 140-2**: Security Requirements for Cryptographic Modules
   - https://csrc.nist.gov/publications/detail/fips/140/2/final

4. **RFC 5116**: An Interface and Algorithms for Authenticated Encryption
   - https://tools.ietf.org/html/rfc5116

5. **RFC 8439**: ChaCha20 and Poly1305 for IETF Protocols
   - https://tools.ietf.org/html/rfc8439

6. **RFC 8018**: PKCS #5: Password-Based Cryptography Specification (PBKDF2)
   - https://tools.ietf.org/html/rfc8018

7. **RFC 9106**: Argon2 Memory-Hard Function
   - https://tools.ietf.org/html/rfc9106

### Compliance Resources

1. **GDPR Article 32**: Security of processing
   - https://gdpr-info.eu/art-32-gdpr/

2. **HIPAA Security Rule**: Encryption and Decryption (§ 164.312(a)(2)(iv))
   - https://www.hhs.gov/hipaa/for-professionals/security/index.html

3. **PCI-DSS Requirement 3**: Protect stored cardholder data
   - https://www.pcisecuritystandards.org/

4. **SOC 2 Trust Services Criteria**: Confidentiality
   - https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/sorhome.html

### Tools and Libraries

1. **cryptography** (Python): https://cryptography.io/
2. **OpenSSL**: https://www.openssl.org/
3. **AWS KMS**: https://aws.amazon.com/kms/
4. **Google Cloud KMS**: https://cloud.google.com/kms
5. **Azure Key Vault**: https://azure.microsoft.com/en-us/services/key-vault/
6. **HashiCorp Vault**: https://www.vaultproject.io/
7. **SQLCipher**: https://www.zetetic.net/sqlcipher/

### Further Reading

1. **Cryptographic Right Answers**: https://latacora.micro.blog/2018/04/03/cryptographic-right-answers.html
2. **OWASP Cryptographic Storage Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
3. **Encryption in Use**: https://en.wikipedia.org/wiki/Encryption#Encryption_in_use
4. **Key Management Best Practices**: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf

---

**Last Updated**: 2025-10-27
**Version**: 1.0
