# Key Management Reference

Comprehensive technical reference for cryptographic key management, including key lifecycle, KMS platforms, HSM integration, and compliance standards.

## Table of Contents

1. [Key Management Fundamentals](#key-management-fundamentals)
2. [Key Lifecycle](#key-lifecycle)
3. [Key Hierarchies](#key-hierarchies)
4. [Key Generation](#key-generation)
5. [Key Distribution](#key-distribution)
6. [Key Storage](#key-storage)
7. [Key Rotation](#key-rotation)
8. [Key Destruction](#key-destruction)
9. [KMS Platforms](#kms-platforms)
10. [HSM Integration](#hsm-integration)
11. [Secrets Management](#secrets-management)
12. [Access Control](#access-control)
13. [Compliance Standards](#compliance-standards)
14. [Key Escrow and Recovery](#key-escrow-and-recovery)
15. [Multi-Party Computation](#multi-party-computation)
16. [Audit and Monitoring](#audit-and-monitoring)
17. [Best Practices](#best-practices)
18. [Anti-Patterns](#anti-patterns)
19. [Implementation Examples](#implementation-examples)

---

## Key Management Fundamentals

### What is Key Management?

**Key Management** is the set of processes and procedures for generating, distributing, storing, rotating, and destroying cryptographic keys throughout their lifecycle.

**Core Principle**: The security of encrypted data depends entirely on the security of the encryption keys. Strong encryption with weak key management = insecure system.

### Why Key Management Matters

**Statistics**:
- 85% of data breaches involve compromised credentials or keys
- Average cost of a data breach: $4.45 million (IBM, 2023)
- Proper key management can prevent 90% of encryption-related breaches

**Key Management Risks**:

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Key exposure** | All encrypted data compromised | HSM/KMS, access controls |
| **Key loss** | Data permanently inaccessible | Backup/escrow, redundancy |
| **Key theft** | Unauthorized decryption | Split knowledge, dual control |
| **Weak keys** | Cryptographic attacks | CSRNG, sufficient key length |
| **No rotation** | Large blast radius | Automated rotation policies |
| **Poor access control** | Insider threats | RBAC, audit logging |

### Key Management vs. Secret Management

| Aspect | Key Management | Secret Management |
|--------|---------------|-------------------|
| **Purpose** | Cryptographic operations | Application credentials |
| **Examples** | AES keys, RSA keys | API tokens, passwords, DB credentials |
| **Lifecycle** | Generate → Rotate → Destroy | Generate → Rotate → Revoke |
| **Storage** | HSM, KMS | Secret managers (Vault, AWS Secrets Manager) |
| **Access** | Programmatic (encrypt/decrypt) | Read/write credentials |
| **Rotation** | Months/years | Days/weeks |

**Note**: Modern platforms (e.g., HashiCorp Vault) handle both key management and secret management.

---

## Key Lifecycle

The key lifecycle consists of five primary phases:

```
┌──────────────┐
│ 1. Generation│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 2. Distribution│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  3. Storage  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 4. Rotation  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 5. Destruction│
└──────────────┘
```

### Phase 1: Generation

**Objective**: Create cryptographically strong keys

**Requirements**:
- Use cryptographically secure random number generators (CSRNGs)
- Sufficient key length (AES-256, RSA-2048+, ECC-256+)
- Generate in secure environment (HSM, KMS, or secure enclave)
- Never derive keys from predictable sources

**Key Generation Sources**:

| Method | Security | Use Case |
|--------|----------|----------|
| **Hardware RNG** (HRNG) | Highest | HSM, TPM, secure enclaves |
| **OS CSRNG** (/dev/urandom, CryptGenRandom) | High | General application use |
| **KMS Generate** (AWS KMS, GCP KMS) | High | Cloud-native applications |
| **Deterministic RNG** (DRBG, CSPRNG) | Moderate | Embedded systems |
| **Weak RNG** (Math.random, timestamp) | ❌ Never use | N/A |

### Phase 2: Distribution

**Objective**: Securely transfer keys to authorized parties

**Methods**:

1. **Out-of-Band (OOB) Distribution**
   - Physical delivery (HSM devices, USB drives)
   - Separate communication channel (phone, SMS, email)
   - Use case: Initial master key setup

2. **Key Wrapping**
   - Encrypt data key with key encryption key (KEK)
   - Transport encrypted key over untrusted channel
   - Use case: Envelope encryption, cloud KMS

3. **Key Derivation**
   - Derive session keys from master key using KDF
   - No key transport needed
   - Use case: TLS session keys, password-based encryption

4. **Public Key Cryptography**
   - Encrypt symmetric key with recipient's public key
   - Use case: PGP, secure email, key exchange

**Distribution Security**:
```
Plaintext Key → ❌ NEVER transport unencrypted
Encrypted Key → ✅ Wrap with KEK
Key Reference → ✅ Use KMS key ID (no key material)
Derived Key   → ✅ Derive locally from shared secret
```

### Phase 3: Storage

**Objective**: Protect keys at rest

**Storage Tiers**:

| Tier | Security | Cost | Use Case |
|------|----------|------|----------|
| **Tier 1: HSM** | Highest | $$$$ | Root keys, CA keys, master keys |
| **Tier 2: KMS** | High | $$ | Application keys, data encryption keys |
| **Tier 3: Encrypted DB** | Moderate | $ | Encrypted DEKs, wrapped keys |
| **Tier 4: Keystore** | Moderate | $ | Local development, testing |
| **Tier 5: Plaintext** | ❌ Never | N/A | N/A |

### Phase 4: Rotation

**Objective**: Limit blast radius of key compromise

**Rotation Frequency**:
- **Root/Master keys**: Annually
- **Key Encryption Keys (KEKs)**: Quarterly
- **Data Encryption Keys (DEKs)**: Monthly or per dataset
- **Session keys**: Per session (ephemeral)
- **API keys**: 90 days
- **Emergency rotation**: Immediately upon suspected compromise

### Phase 5: Destruction

**Objective**: Securely delete keys when no longer needed

**Destruction Methods**:

| Method | Security | Use Case |
|--------|----------|----------|
| **Cryptographic erasure** | Highest | Destroy KEK (makes DEKs unrecoverable) |
| **Secure overwrite** | High | Multi-pass overwrite (DOD 5220.22-M) |
| **HSM destroy** | High | Hardware-level key zeroization |
| **Shredding** | Moderate | Physical destruction of storage media |
| **Delete file** | ❌ Insufficient | Data may be recoverable |

**Key Destruction Timeline**:
1. **Deprecation**: Mark key as deprecated (no new encryptions)
2. **Grace period**: 30-90 days (allow existing decryptions)
3. **Scheduled deletion**: Schedule destruction with waiting period
4. **Audit log**: Record destruction event
5. **Verification**: Confirm key is irrecoverable

---

## Key Hierarchies

### Concept

**Key Hierarchy**: Organize keys in layers where upper-level keys encrypt lower-level keys.

**Benefits**:
- Efficient key rotation (rotate KEK without re-encrypting data)
- Separation of concerns (different keys for different purposes)
- Reduced attack surface (root keys rarely used)
- Granular access control (different teams manage different key levels)

### Three-Tier Hierarchy

```
┌─────────────────────────────────────────────┐
│ Level 1: Root Key (Master Key)              │  ← Stored in HSM
│ - Never rotates (or rotates rarely)         │  ← Rarely used
│ - Used to encrypt KEKs                      │  ← Highest security
│ - FIPS 140-2 Level 3+ HSM                   │
└───────────────────┬─────────────────────────┘
                    │ Encrypts
                    ▼
┌─────────────────────────────────────────────┐
│ Level 2: Key Encryption Key (KEK)           │  ← Stored in KMS or encrypted DB
│ - Rotates periodically (e.g., quarterly)    │  ← Used to encrypt DEKs
│ - Used to encrypt DEKs                      │  ← Medium security
│ - One KEK per application/tenant            │
└───────────────────┬─────────────────────────┘
                    │ Encrypts
                    ▼
┌─────────────────────────────────────────────┐
│ Level 3: Data Encryption Key (DEK)          │  ← Stored encrypted with data
│ - Rotates frequently (e.g., per file/record)│  ← Used to encrypt actual data
│ - Used to encrypt data                      │  ← Performance-critical
│ - One DEK per file/record/tenant            │
└───────────────────┬─────────────────────────┘
                    │ Encrypts
                    ▼
            ┌──────────────────┐
            │  Encrypted Data  │  ← Application data
            └──────────────────┘
```

### Key Hierarchy Example

**Scenario**: Encrypt user files in cloud storage

```python
# Level 1: Root Key (stored in HSM)
root_key = hsm.get_key("root-key-2024")

# Level 2: KEK for this application (encrypted by root key)
kek_plaintext = generate_random_key(32)
kek_encrypted = hsm.encrypt(root_key, kek_plaintext)
kms.store("app-kek-2024-Q4", kek_encrypted)

# Level 3: DEK for each file (encrypted by KEK)
def encrypt_file(file_data):
    # Generate DEK
    dek = generate_random_key(32)

    # Encrypt file with DEK
    ciphertext = aes_gcm_encrypt(dek, file_data)

    # Encrypt DEK with KEK
    kek = kms.decrypt("app-kek-2024-Q4", root_key)
    encrypted_dek = aes_gcm_encrypt(kek, dek)

    # Store encrypted DEK + ciphertext
    return {
        "encrypted_dek": encrypted_dek,
        "ciphertext": ciphertext
    }
```

### Key Rotation with Hierarchies

**Advantage**: Rotate KEK without re-encrypting data

**Process**:
1. Generate new KEK
2. Decrypt DEKs with old KEK
3. Re-encrypt DEKs with new KEK
4. Data remains encrypted with DEKs (no change)

**Example**:
```python
def rotate_kek(old_kek, new_kek):
    """Rotate KEK without touching data"""
    records = db.query("SELECT id, encrypted_dek FROM files")

    for record in records:
        # Decrypt DEK with old KEK
        dek = decrypt(old_kek, record.encrypted_dek)

        # Re-encrypt DEK with new KEK
        new_encrypted_dek = encrypt(new_kek, dek)

        # Update record (data ciphertext unchanged)
        db.update("files", record.id, {
            "encrypted_dek": new_encrypted_dek
        })
```

**Performance**: Re-encrypting DEKs (small) is 1000x faster than re-encrypting data (large).

---

## Key Generation

### Cryptographically Secure Random Number Generators (CSRNGs)

**Requirements for Cryptographic Keys**:
1. **Unpredictability**: Cannot predict future or past outputs
2. **Uniformity**: All values equally likely
3. **Sufficient entropy**: At least 256 bits for AES-256
4. **Non-deterministic**: Not based on predictable seeds

### Platform-Specific CSRNGs

#### Linux: /dev/urandom

**Source**: Kernel CSPRNG (Yarrow, Fortuna algorithms)

**Entropy Sources**:
- Hardware RNG (if available: RDRAND, RDSEED)
- Interrupt timing
- Disk I/O timing
- Network packet timing

**Usage**:
```bash
# Generate 32-byte key (256 bits)
dd if=/dev/urandom of=key.bin bs=32 count=1

# Generate hex-encoded key
hexdump -n 32 -e '32/1 "%02x" "\n"' /dev/urandom
```

**Python**:
```python
import os

# Generate 256-bit key
key = os.urandom(32)  # 32 bytes = 256 bits

# Or use secrets module (Python 3.6+)
import secrets
key = secrets.token_bytes(32)
hex_key = secrets.token_hex(32)  # 64 hex characters
```

**Note**: `/dev/random` vs `/dev/urandom`
- `/dev/random`: Blocks when entropy low (not needed for modern kernels)
- `/dev/urandom`: Never blocks (preferred for key generation)

#### Windows: CryptGenRandom

**Source**: Windows CryptoAPI CSPRNG

**Python**:
```python
import os

# os.urandom() uses CryptGenRandom on Windows
key = os.urandom(32)
```

**C#**:
```csharp
using System.Security.Cryptography;

// Generate 256-bit key
byte[] key = new byte[32];
using (var rng = RandomNumberGenerator.Create())
{
    rng.GetBytes(key);
}
```

#### macOS: /dev/random

**Source**: Kernel CSPRNG (Yarrow algorithm)

**Usage**: Same as Linux /dev/urandom

```python
import os
key = os.urandom(32)
```

### Hardware RNGs

#### Intel RDRAND/RDSEED

**What**: CPU instruction for hardware random number generation

**Check Support**:
```bash
grep -o rdrand /proc/cpuinfo
grep -o rdseed /proc/cpuinfo
```

**C Example**:
```c
#include <immintrin.h>
#include <stdint.h>

uint64_t get_random_uint64() {
    uint64_t rand;
    while (!_rdrand64_step(&rand)) {
        // Retry if RDRAND fails
    }
    return rand;
}
```

**Note**: Linux /dev/urandom automatically uses RDRAND if available.

#### TPM (Trusted Platform Module)

**What**: Hardware chip for cryptographic operations and key storage

**Generate Key**:
```bash
# Using tpm2-tools
tpm2_getrandom 32 > key.bin
```

**Python (tpm2-pytss)**:
```python
from tpm2_pytss import ESAPI

esapi = ESAPI()
random_bytes = esapi.get_random(32)
```

### Key Derivation Functions (KDFs)

**Use Case**: Derive cryptographic keys from passwords or shared secrets

**Algorithms**:

| Algorithm | Standard | Security | Use Case |
|-----------|----------|----------|----------|
| **Argon2id** | RFC 9106 | Highest | Password hashing, key derivation |
| **scrypt** | RFC 7914 | High | Key derivation (memory-hard) |
| **PBKDF2** | RFC 8018 | Moderate | FIPS compliance, legacy systems |
| **HKDF** | RFC 5869 | High | Key derivation from shared secrets |
| **bcrypt** | - | Moderate | Password hashing only |

#### Argon2id (Recommended)

**Parameters**:
- `time_cost`: Number of iterations (min 3)
- `memory_cost`: Memory in KB (min 64 MB)
- `parallelism`: Number of threads (min 4)
- `salt`: Random salt (min 16 bytes)

**Python Example**:
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

**Recommended Parameters** (2024):
- Time cost: 3-4
- Memory cost: 65536-131072 (64-128 MB)
- Parallelism: 4
- Hash length: 32 bytes (256 bits)

#### HKDF (HMAC-based KDF)

**Use Case**: Derive multiple keys from single master key

**Python Example**:
```python
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import secrets

# Master key material
ikm = secrets.token_bytes(32)  # Input key material

# Derive multiple keys
hkdf = HKDF(
    algorithm=hashes.SHA256(),
    length=32,
    salt=None,
    info=b"encryption-key"
)
encryption_key = hkdf.derive(ikm)

hkdf = HKDF(
    algorithm=hashes.SHA256(),
    length=32,
    salt=None,
    info=b"authentication-key"
)
auth_key = hkdf.derive(ikm)
```

### Key Length Requirements

**Symmetric Encryption**:
- **AES**: 128, 192, or 256 bits (use 256)
- **ChaCha20**: 256 bits

**Asymmetric Encryption**:
- **RSA**: Minimum 2048 bits (3072+ recommended)
- **ECC**: Minimum 256 bits (384+ for high security)
- **Ed25519**: 256 bits (fixed)

**Key Length Security Equivalence**:

| Symmetric | RSA | ECC | Security Level |
|-----------|-----|-----|----------------|
| 128 bits | 3072 bits | 256 bits | Medium (until 2030) |
| 192 bits | 7680 bits | 384 bits | High |
| 256 bits | 15360 bits | 512 bits | Very High |

---

## Key Distribution

### Out-of-Band (OOB) Distribution

**Method**: Deliver keys through separate, secure channel

**Use Cases**:
- Initial master key setup
- Root CA key distribution
- HSM key loading
- Emergency key recovery

**Examples**:

1. **Physical Delivery**
   - USB drive with encrypted key
   - Smart card
   - HSM device
   - Sealed envelope

2. **Separate Communication Channel**
   - Phone call
   - SMS (for low-security scenarios)
   - Separate email system
   - In-person transfer

**Best Practices**:
- Split key into multiple parts (M-of-N scheme)
- Require multiple people (dual control)
- Audit trail for key delivery
- Time-limited validity

### Key Wrapping (Envelope Encryption)

**Concept**: Encrypt data key with key encryption key (KEK) for secure transport

**Process**:
```
Sender                        Transport Channel                    Receiver
──────                        ─────────────────                    ────────
Generate DEK
    │
    ▼
Encrypt Data
with DEK
    │
    ▼
Wrap DEK
with KEK
    │
    ▼
Send Wrapped DEK  ─────────────────────────────────────>  Receive
+ Ciphertext                                                       │
                                                                   ▼
                                                              Unwrap DEK
                                                              with KEK
                                                                   │
                                                                   ▼
                                                              Decrypt Data
                                                              with DEK
```

**Key Wrapping Algorithms**:

| Algorithm | Standard | Key Sizes | Use Case |
|-----------|----------|-----------|----------|
| **AES-KW** | RFC 3394 | 128, 192, 256 | Symmetric key wrapping |
| **AES-KWP** | RFC 5649 | 128, 192, 256 | Padded key wrapping |
| **RSA-OAEP** | PKCS#1 v2.1 | 2048+ | Asymmetric key wrapping |
| **AES-GCM** | NIST SP 800-38D | 128, 192, 256 | Authenticated key wrapping |

**Python Example (AES Key Wrap)**:
```python
from cryptography.hazmat.primitives.keywrap import aes_key_wrap, aes_key_unwrap
import secrets

# KEK (256-bit)
kek = secrets.token_bytes(32)

# DEK to wrap (256-bit)
dek = secrets.token_bytes(32)

# Wrap DEK with KEK
wrapped_dek = aes_key_wrap(kek, dek, backend=default_backend())

# Transport wrapped_dek over untrusted channel

# Unwrap DEK
unwrapped_dek = aes_key_unwrap(kek, wrapped_dek, backend=default_backend())

assert unwrapped_dek == dek
```

### Key Agreement Protocols

**Use Case**: Two parties establish shared secret without transmitting keys

#### Diffie-Hellman (DH)

**Classic DH**:
```
Alice                                    Bob
─────                                    ───
Generate private key a                   Generate private key b
Compute public key A = g^a mod p         Compute public key B = g^b mod p
                A ──────────────────→
                ←────────────────── B
Compute shared secret:                   Compute shared secret:
s = B^a mod p                            s = A^b mod p

Both derive encryption key from s using KDF
```

**Python Example (ECDH - Elliptic Curve DH)**:
```python
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

# Alice generates key pair
alice_private = ec.generate_private_key(ec.SECP256R1())
alice_public = alice_private.public_key()

# Bob generates key pair
bob_private = ec.generate_private_key(ec.SECP256R1())
bob_public = bob_private.public_key()

# Alice computes shared secret
alice_shared_key = alice_private.exchange(ec.ECDH(), bob_public)

# Bob computes shared secret
bob_shared_key = bob_private.exchange(ec.ECDH(), alice_public)

# Both derive encryption key from shared secret
def derive_key(shared_secret):
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"handshake"
    ).derive(shared_secret)

alice_key = derive_key(alice_shared_key)
bob_key = derive_key(bob_shared_key)

assert alice_key == bob_key  # Same encryption key
```

### Key Distribution via KMS

**Concept**: Use cloud KMS to manage key distribution

**AWS KMS Example**:
```python
import boto3

kms = boto3.client('kms')

# Sender: Generate data key
response = kms.generate_data_key(
    KeyId='arn:aws:kms:us-east-1:123456789012:key/12345678',
    KeySpec='AES_256'
)

dek_plaintext = response['Plaintext']      # Use to encrypt data
dek_encrypted = response['CiphertextBlob']  # Distribute this

# Encrypt data with DEK
ciphertext = encrypt_data(plaintext, dek_plaintext)

# Send encrypted DEK + ciphertext to receiver

# Receiver: Decrypt DEK
response = kms.decrypt(CiphertextBlob=dek_encrypted)
dek = response['Plaintext']

# Decrypt data
plaintext = decrypt_data(ciphertext, dek)
```

---

## Key Storage

### Storage Security Requirements

**NIST SP 800-57 Requirements**:
1. **Confidentiality**: Keys must be encrypted or in tamper-resistant hardware
2. **Integrity**: Detect unauthorized modification
3. **Availability**: Keys accessible when needed (but not more)
4. **Accountability**: Audit who accessed keys
5. **Authenticity**: Verify key source

### Storage Tiers

#### Tier 1: Hardware Security Module (HSM)

**What**: Dedicated hardware device for cryptographic operations and key storage

**Features**:
- Keys never leave HSM (operations performed inside)
- FIPS 140-2 Level 3 or 4 certified
- Tamper-resistant/tamper-evident
- Physical security controls
- Audit logging
- High-availability clustering

**FIPS 140-2 Levels**:

| Level | Requirements | Use Case |
|-------|-------------|----------|
| **Level 1** | Basic security | Software implementations |
| **Level 2** | Tamper-evident seals, role-based auth | General enterprise |
| **Level 3** | Tamper-resistant hardware, identity-based auth | Financial, healthcare |
| **Level 4** | Environmental protection (voltage, temp) | Government, military |

**HSM Vendors**:
- Thales Luna HSM
- nCipher nShield
- Utimaco SecurityServer
- AWS CloudHSM
- Google Cloud HSM
- Azure Dedicated HSM

**AWS CloudHSM Example**:
```python
import boto3

cloudhsm = boto3.client('cloudhsmv2')

# Create HSM cluster
response = cloudhsm.create_cluster(
    SubnetIds=['subnet-12345', 'subnet-67890'],
    HsmType='hsm1.medium'
)

cluster_id = response['Cluster']['ClusterId']

# Initialize cluster and create HSM
# Then use PKCS#11 or JCE provider to interact with HSM
```

**Cost**: $10,000-$100,000+ for hardware HSM, $1-5/hour for cloud HSM

#### Tier 2: Cloud Key Management Service (KMS)

**What**: Managed service for key storage and encryption operations

**Features**:
- API-based key management
- Automatic key rotation
- Access control via IAM
- Audit logging
- Regional replication
- Cost-effective ($1/month per key)

**AWS KMS**:
```python
import boto3

kms = boto3.client('kms')

# Create key
response = kms.create_key(
    Description='Application encryption key',
    KeyUsage='ENCRYPT_DECRYPT',
    Origin='AWS_KMS'
)

key_id = response['KeyMetadata']['KeyId']

# Create alias
kms.create_alias(
    AliasName='alias/app-key',
    TargetKeyId=key_id
)

# Enable automatic rotation
kms.enable_key_rotation(KeyId=key_id)

# Encrypt data
ciphertext = kms.encrypt(
    KeyId='alias/app-key',
    Plaintext=b'Secret data'
)['CiphertextBlob']

# Decrypt data
plaintext = kms.decrypt(CiphertextBlob=ciphertext)['Plaintext']
```

**Google Cloud KMS**:
```python
from google.cloud import kms

client = kms.KeyManagementServiceClient()

# Create key ring
key_ring_path = f'projects/{project_id}/locations/{location}/keyRings/{key_ring_id}'
client.create_key_ring(request={'parent': location_path, 'key_ring_id': key_ring_id})

# Create crypto key
key_path = f'{key_ring_path}/cryptoKeys/{key_id}'
client.create_crypto_key(
    request={
        'parent': key_ring_path,
        'crypto_key_id': key_id,
        'crypto_key': {'purpose': kms.CryptoKey.CryptoKeyPurpose.ENCRYPT_DECRYPT}
    }
)

# Encrypt
encrypt_response = client.encrypt(
    request={'name': key_path, 'plaintext': b'Secret data'}
)
ciphertext = encrypt_response.ciphertext

# Decrypt
decrypt_response = client.decrypt(
    request={'name': key_path, 'ciphertext': ciphertext}
)
plaintext = decrypt_response.plaintext
```

**Azure Key Vault**:
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.keys import KeyClient
from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm

credential = DefaultAzureCredential()
key_client = KeyClient(vault_url=f'https://{vault_name}.vault.azure.net/', credential=credential)

# Create key
key = key_client.create_rsa_key('app-key', size=2048)

# Encrypt
crypto_client = CryptographyClient(key, credential)
result = crypto_client.encrypt(EncryptionAlgorithm.rsa_oaep, b'Secret data')
ciphertext = result.ciphertext

# Decrypt
result = crypto_client.decrypt(EncryptionAlgorithm.rsa_oaep, ciphertext)
plaintext = result.plaintext
```

#### Tier 3: Encrypted Database

**What**: Store encrypted keys in database (KEK stored separately)

**Schema Example**:
```sql
CREATE TABLE encryption_keys (
    id SERIAL PRIMARY KEY,
    key_id VARCHAR(255) UNIQUE NOT NULL,
    encrypted_key BYTEA NOT NULL,      -- DEK encrypted by KEK
    key_nonce BYTEA NOT NULL,          -- Nonce for encryption
    key_type VARCHAR(50) NOT NULL,     -- "AES-256", "RSA-2048", etc.
    created_at TIMESTAMP NOT NULL,
    rotated_at TIMESTAMP,
    expires_at TIMESTAMP,
    status VARCHAR(20) NOT NULL        -- "active", "deprecated", "destroyed"
);

CREATE INDEX idx_key_id ON encryption_keys(key_id);
CREATE INDEX idx_status ON encryption_keys(status);
```

**Application Example**:
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

class KeyStore:
    def __init__(self, kek):
        """KEK (Key Encryption Key) for encrypting DEKs"""
        self.kek = kek
        self.aesgcm = AESGCM(kek)

    def store_key(self, key_id, dek, key_type):
        """Store encrypted DEK in database"""
        nonce = secrets.token_bytes(12)
        encrypted_key = self.aesgcm.encrypt(nonce, dek, None)

        db.execute("""
            INSERT INTO encryption_keys (key_id, encrypted_key, key_nonce, key_type, status, created_at)
            VALUES (?, ?, ?, ?, 'active', NOW())
        """, (key_id, encrypted_key, nonce, key_type))

    def retrieve_key(self, key_id):
        """Retrieve and decrypt DEK"""
        row = db.query("""
            SELECT encrypted_key, key_nonce
            FROM encryption_keys
            WHERE key_id = ? AND status = 'active'
        """, (key_id,))

        if not row:
            raise ValueError(f"Key not found: {key_id}")

        dek = self.aesgcm.decrypt(row['key_nonce'], row['encrypted_key'], None)
        return dek
```

#### Tier 4: Operating System Keystore

**What**: OS-provided secure storage for keys and credentials

**macOS Keychain**:
```python
import keyring

# Store key
keyring.set_password('myapp', 'encryption_key', base64_encoded_key)

# Retrieve key
key = keyring.get_password('myapp', 'encryption_key')
```

**Windows Credential Manager**:
```python
import keyring

# Same API as macOS
keyring.set_password('myapp', 'encryption_key', base64_encoded_key)
key = keyring.get_password('myapp', 'encryption_key')
```

**Linux Secret Service** (GNOME Keyring, KWallet):
```python
import secretstorage

connection = secretstorage.dbus_init()
collection = secretstorage.get_default_collection(connection)

# Store key
collection.create_item(
    'myapp-encryption-key',
    {'application': 'myapp'},
    base64_encoded_key
)

# Retrieve key
items = collection.search_items({'application': 'myapp'})
key = items[0].get_secret()
```

### Key Storage Best Practices

1. **Never store keys in plaintext**
   ```
   ❌ config.yaml: encryption_key: "abc123..."
   ✅ Use KMS, HSM, or encrypted storage
   ```

2. **Separate keys from data**
   ```
   ❌ Same database/server
   ✅ Separate KMS service or HSM
   ```

3. **Use key hierarchies**
   ```
   Root Key (HSM) → KEK (KMS) → DEK (Encrypted DB) → Data
   ```

4. **Access control**
   ```
   ✅ Role-based access (RBAC)
   ✅ Principle of least privilege
   ✅ Audit logging
   ```

5. **Key backup and redundancy**
   ```
   ✅ Multi-region KMS replication
   ✅ HSM cluster (HA)
   ✅ Offline backup (encrypted, offline storage)
   ```

6. **Separate keys by environment**
   ```
   dev-encryption-key
   staging-encryption-key
   prod-encryption-key
   ```

---

## Key Rotation

### Why Rotate Keys?

**Reasons**:
1. **Limit blast radius**: Compromised old key doesn't affect new data
2. **Compliance**: Many standards require periodic rotation (PCI-DSS, HIPAA)
3. **Cryptographic hygiene**: Reduce ciphertext under single key
4. **Mitigate key exposure**: Employee departure, system compromise, vulnerability disclosure

**Rotation Frequency Recommendations**:

| Key Type | Frequency | Rationale |
|----------|-----------|-----------|
| **Root/Master keys** | Annually | Rarely used, highest security |
| **KEKs** | Quarterly | Balance security and operational overhead |
| **DEKs** | Monthly or per-dataset | Frequent rotation, minimal overhead with envelope encryption |
| **Session keys** | Per-session | Ephemeral, perfect forward secrecy |
| **API keys** | 90 days | Compliance requirement (SOC 2, PCI-DSS) |
| **TLS certificates** | 90 days (Let's Encrypt) or annually | Industry standard |
| **Database passwords** | 90 days | Compliance requirement |
| **Emergency** | Immediately | Suspected compromise |

### Rotation Strategies

#### Strategy 1: Re-encrypt All Data (Complete Rotation)

**Process**:
1. Generate new key
2. Decrypt all data with old key
3. Encrypt all data with new key
4. Update key references
5. Delete old key (after grace period)

**Pros**:
- Simple conceptually
- Complete forward secrecy

**Cons**:
- Expensive (re-encrypt all data)
- Downtime required
- Risk of data loss during migration

**Use Case**: Small datasets, infrequent rotation

**Example**:
```python
def rotate_complete(old_key, new_key):
    """Complete key rotation - re-encrypt all data"""
    records = db.query("SELECT id, ciphertext FROM encrypted_data")

    for record in records:
        # Decrypt with old key
        plaintext = decrypt(old_key, record.ciphertext)

        # Re-encrypt with new key
        new_ciphertext = encrypt(new_key, plaintext)

        # Update record
        db.update("encrypted_data", record.id, {"ciphertext": new_ciphertext})

    # Mark old key as deprecated
    mark_key_deprecated(old_key)
```

#### Strategy 2: Envelope Encryption (Zero-Downtime Rotation)

**Process**:
1. Generate new KEK
2. Re-encrypt DEKs with new KEK
3. Data stays encrypted with DEKs (no change)
4. Update KEK references
5. Delete old KEK

**Pros**:
- Fast (only re-encrypt small DEKs, not large data)
- No downtime
- Scales to large datasets

**Cons**:
- Requires key hierarchy

**Use Case**: Large datasets, cloud KMS, production systems

**Example**:
```python
def rotate_envelope(old_kek, new_kek):
    """Envelope encryption rotation - only re-encrypt DEKs"""
    records = db.query("SELECT id, encrypted_dek, dek_nonce FROM files")

    old_aesgcm = AESGCM(old_kek)
    new_aesgcm = AESGCM(new_kek)

    for record in records:
        # Decrypt DEK with old KEK
        dek = old_aesgcm.decrypt(record.dek_nonce, record.encrypted_dek, None)

        # Re-encrypt DEK with new KEK
        new_nonce = secrets.token_bytes(12)
        new_encrypted_dek = new_aesgcm.encrypt(new_nonce, dek, None)

        # Update encrypted DEK (data ciphertext unchanged)
        db.update("files", record.id, {
            "encrypted_dek": new_encrypted_dek,
            "dek_nonce": new_nonce
        })

    # Mark old KEK as deprecated
    mark_key_deprecated(old_kek)
```

**Performance Comparison**:
```
Dataset: 1 TB encrypted data
Complete Rotation: 1 TB re-encryption = hours/days
Envelope Rotation: 10,000 DEKs * 32 bytes = 320 KB re-encryption = seconds
```

#### Strategy 3: Versioned Keys (Multi-Version)

**Process**:
1. Keep both old and new keys active
2. Write new data with new key
3. Read old data with old key
4. Gradually re-encrypt old data (background job)
5. Retire old key after migration complete

**Pros**:
- Zero downtime
- Gradual migration
- No service interruption

**Cons**:
- Complex (track key versions)
- Multiple keys active simultaneously

**Use Case**: Large datasets, continuous writes, cannot afford downtime

**Schema**:
```sql
CREATE TABLE encrypted_data (
    id SERIAL PRIMARY KEY,
    ciphertext BYTEA NOT NULL,
    key_version INTEGER NOT NULL,  -- Track which key encrypted this row
    nonce BYTEA NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_key_version ON encrypted_data(key_version);
```

**Application**:
```python
class VersionedKeyManager:
    def __init__(self):
        self.keys = {
            1: load_key("key-v1"),  # Old key
            2: load_key("key-v2"),  # New key (active)
        }
        self.active_version = 2

    def encrypt(self, plaintext):
        """Encrypt with active key version"""
        key = self.keys[self.active_version]
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)

        return {
            "ciphertext": ciphertext,
            "key_version": self.active_version,
            "nonce": nonce
        }

    def decrypt(self, ciphertext, key_version, nonce):
        """Decrypt with appropriate key version"""
        if key_version not in self.keys:
            raise ValueError(f"Unknown key version: {key_version}")

        key = self.keys[key_version]
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
        return plaintext

    def background_reencryption(self, batch_size=100):
        """Gradually re-encrypt old data"""
        while True:
            # Get batch of old records
            records = db.query("""
                SELECT id, ciphertext, key_version, nonce
                FROM encrypted_data
                WHERE key_version < ?
                LIMIT ?
            """, (self.active_version, batch_size))

            if not records:
                break  # Migration complete

            for record in records:
                # Decrypt with old key
                plaintext = self.decrypt(
                    record.ciphertext,
                    record.key_version,
                    record.nonce
                )

                # Re-encrypt with new key
                encrypted = self.encrypt(plaintext)

                # Update record
                db.update("encrypted_data", record.id, encrypted)

            time.sleep(1)  # Rate limit
```

### AWS KMS Automatic Key Rotation

**How It Works**:
- AWS rotates key material annually (automatic)
- Old key versions retained for decryption
- New encryptions use new key version
- Application code unchanged (transparent)

**Enable Automatic Rotation**:
```bash
aws kms enable-key-rotation --key-id 12345678-1234-1234-1234-123456789012
```

**Check Rotation Status**:
```bash
aws kms get-key-rotation-status --key-id 12345678-1234-1234-1234-123456789012
```

**How Versioning Works Internally**:
```
Key ARN: arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012

Key Material Versions:
- v1 (2023-01-01): Used for decrypting old ciphertext
- v2 (2024-01-01): Used for decrypting old ciphertext
- v3 (2025-01-01): Current version (used for new encryptions)

When you call kms.encrypt():
  → Uses v3 (current key material)

When you call kms.decrypt(ciphertext):
  → KMS detects which version encrypted it
  → Uses correct key material automatically
  → Application doesn't need to track versions
```

### Manual Rotation Procedure

**Pre-Rotation Checklist**:
- [ ] Backup current keys (encrypted)
- [ ] Test decryption with old key
- [ ] Verify access to generate new keys
- [ ] Schedule maintenance window (if needed)
- [ ] Notify stakeholders
- [ ] Prepare rollback plan

**Rotation Steps**:

1. **Generate new key**
   ```python
   new_key = secrets.token_bytes(32)
   ```

2. **Store new key securely**
   ```python
   kms.create_key(Description='app-key-2025-Q1')
   ```

3. **Update application config** (versioned keys)
   ```yaml
   encryption_keys:
     - id: key-2024-Q4
       version: 1
       status: deprecated
     - id: key-2025-Q1
       version: 2
       status: active
   ```

4. **Re-encrypt data** (choose strategy: complete, envelope, or versioned)

5. **Verify rotation**
   ```python
   # Test encryption with new key
   ciphertext = encrypt(new_key, test_data)
   plaintext = decrypt(new_key, ciphertext)
   assert plaintext == test_data

   # Test decryption of old data
   old_plaintext = decrypt(old_key, old_ciphertext)
   assert old_plaintext == expected_data
   ```

6. **Monitor for errors**
   - Check application logs
   - Monitor decryption failures
   - Track key usage metrics

7. **Grace period** (30-90 days)
   - Keep old key active for decryption
   - Monitor usage of old key
   - Ensure all data migrated

8. **Delete old key**
   ```python
   kms.schedule_key_deletion(KeyId=old_key_id, PendingWindowInDays=30)
   ```

### Rotation Automation

**Automated Rotation Script**:
```python
#!/usr/bin/env python3
import boto3
import datetime

class KeyRotationAutomation:
    def __init__(self, kms_client):
        self.kms = kms_client

    def check_rotation_needed(self, key_id):
        """Check if key needs rotation based on age"""
        response = self.kms.describe_key(KeyId=key_id)
        creation_date = response['KeyMetadata']['CreationDate']
        age_days = (datetime.datetime.now(datetime.timezone.utc) - creation_date).days

        # Rotate if key is > 365 days old
        return age_days > 365

    def rotate_key(self, key_id):
        """Rotate KMS key"""
        # Enable automatic rotation
        self.kms.enable_key_rotation(KeyId=key_id)

        # Or manually create new key version
        # (for customer-managed keys)
        response = self.kms.create_key(
            Description=f'Rotated from {key_id}',
            Origin='AWS_KMS'
        )

        new_key_id = response['KeyMetadata']['KeyId']

        # Update alias to point to new key
        self.kms.update_alias(
            AliasName='alias/my-key',
            TargetKeyId=new_key_id
        )

        return new_key_id

    def scan_and_rotate(self):
        """Scan all keys and rotate if needed"""
        response = self.kms.list_keys()

        for key in response['Keys']:
            key_id = key['KeyId']

            if self.check_rotation_needed(key_id):
                print(f"Rotating key: {key_id}")
                new_key_id = self.rotate_key(key_id)
                print(f"New key: {new_key_id}")

# Run automated rotation
kms = boto3.client('kms')
automation = KeyRotationAutomation(kms)
automation.scan_and_rotate()
```

---

## Key Destruction

### Secure Key Deletion

**Objective**: Ensure keys cannot be recovered after deletion

### Deletion Methods

#### Method 1: Cryptographic Erasure

**Concept**: Destroy KEK, making all DEKs (and data) irrecoverable

**Advantages**:
- Instant (delete one KEK)
- Guaranteed irrecoverability (even with data backups)
- No need to overwrite data

**Process**:
```
Before:
Root Key → KEK → DEK1, DEK2, DEK3, ... → Encrypted Data

After Cryptographic Erasure (Delete KEK):
Root Key → ❌ KEK DELETED ❌
           ↓
       DEK1, DEK2, DEK3 (irrecoverable)
           ↓
       Encrypted Data (permanently inaccessible)
```

**Example**:
```python
def cryptographic_erasure(kek_id):
    """Delete KEK to make all DEKs irrecoverable"""
    # Schedule KEK deletion
    kms.schedule_key_deletion(
        KeyId=kek_id,
        PendingWindowInDays=30  # 7-30 day waiting period
    )

    # After waiting period, KEK is permanently deleted
    # All DEKs encrypted by this KEK become irrecoverable
    # Data encrypted by those DEKs is permanently inaccessible
```

**Use Case**: Delete all user data (GDPR "right to be forgotten")

#### Method 2: Secure Overwrite

**Concept**: Overwrite key data multiple times before deletion

**Standards**:
- **DOD 5220.22-M**: 3-pass overwrite (0xFF, 0x00, random)
- **Gutmann Method**: 35-pass overwrite (overkill for modern drives)
- **NIST SP 800-88**: 1-pass overwrite sufficient for modern drives

**Bash Example**:
```bash
# DOD 5220.22-M (3-pass)
shred -vfz -n 3 key.bin

# Gutmann method (35-pass)
shred -vfz -n 35 key.bin

# Single-pass (sufficient for SSDs)
shred -vfz -n 1 key.bin
```

**Python Example**:
```python
import os

def secure_delete_key(file_path, passes=3):
    """Securely delete key file with multiple overwrites"""
    file_size = os.path.getsize(file_path)

    with open(file_path, 'rb+') as f:
        for _ in range(passes):
            # Overwrite with random data
            f.seek(0)
            f.write(os.urandom(file_size))
            f.flush()
            os.fsync(f.fileno())

    # Delete file
    os.remove(file_path)
```

**Note**: SSDs use wear-leveling, making secure overwrite less effective. Use cryptographic erasure or hardware encryption for SSDs.

#### Method 3: HSM Key Zeroization

**Concept**: Use HSM command to securely erase keys

**FIPS 140-2 Requirement**: HSMs must support key zeroization

**Example (Generic HSM)**:
```bash
# Zeroize all keys (factory reset)
hsm-admin zeroize --confirm

# Delete specific key
hsm-admin delete-key --key-id 12345
```

**AWS CloudHSM**:
```python
import boto3

cloudhsm = boto3.client('cloudhsmv2')

# Delete HSM cluster (destroys all keys)
cloudhsm.delete_cluster(ClusterId='cluster-abc123')
```

#### Method 4: Physical Destruction

**Use Case**: Destroy HSM devices, hard drives, backup tapes

**Methods**:
- **Shredding**: Industrial shredder (disks, tapes)
- **Degaussing**: Magnetic field (hard drives only, not SSDs)
- **Incineration**: Burn to ash
- **Pulverizing**: Crush to powder

**Professional Services**:
- Iron Mountain
- Shred-it
- DataSanitization (NAID AAA certified)

### Key Deletion Timeline

**Recommended Process**:

```
Day 0: Deprecate Key
├─ Mark key as "deprecated" in system
├─ Prevent new encryptions with this key
└─ Allow decryptions to continue

Day 1-30: Grace Period
├─ Monitor key usage
├─ Re-encrypt data if needed
└─ Ensure no dependencies

Day 30: Schedule Deletion
├─ Schedule key deletion (7-30 day waiting period)
├─ Send notifications
└─ Create audit log entry

Day 37-60: Pending Deletion
├─ Key marked as "pending deletion"
├─ Can still cancel deletion
└─ No operations allowed

Day 60: Permanent Deletion
├─ Key permanently deleted
├─ Audit log entry
└─ Irrecoverable
```

**AWS KMS Example**:
```bash
# Day 0: Disable key
aws kms disable-key --key-id 12345678-1234-1234-1234-123456789012

# Day 30: Schedule deletion (7-30 day waiting period)
aws kms schedule-key-deletion \
  --key-id 12345678-1234-1234-1234-123456789012 \
  --pending-window-in-days 30

# Before Day 60: Cancel deletion (if needed)
aws kms cancel-key-deletion --key-id 12345678-1234-1234-1234-123456789012

# Day 60: Key automatically deleted
```

### Audit Logging

**Log Key Deletion Events**:
```json
{
  "event": "key_deletion",
  "timestamp": "2025-01-15T10:30:00Z",
  "key_id": "key-2024-Q4",
  "deleted_by": "admin@example.com",
  "reason": "key_rotation",
  "method": "cryptographic_erasure",
  "confirmation": "12345-ABCDE",
  "data_affected": "none (re-encrypted before deletion)"
}
```

### Data Retention Compliance

**Compliance Considerations**:

| Regulation | Retention Requirement | Key Deletion Impact |
|------------|----------------------|---------------------|
| **GDPR** | Right to erasure | Must delete keys for user data |
| **HIPAA** | 6 years | Cannot delete keys for retained data |
| **SOX** | 7 years | Cannot delete keys for financial records |
| **PCI-DSS** | 3 months minimum | Can delete after retention period |

**Best Practice**: Separate keys for different retention periods

```python
# Example: Separate keys for different retention tiers
keys = {
    "short-term": "key-90-day",    # 90-day retention
    "medium-term": "key-1-year",   # 1-year retention
    "long-term": "key-7-year",     # 7-year retention (compliance)
    "permanent": "key-permanent",  # Never delete
}
```

---

## KMS Platforms

### AWS KMS

**Features**:
- Customer Master Keys (CMKs)
- Automatic key rotation (annual)
- FIPS 140-2 Level 2 validated (Level 3 with CloudHSM)
- Integrated with AWS services (S3, EBS, RDS, etc.)
- Envelope encryption support
- Multi-region keys
- Audit logging (CloudTrail)

**Key Types**:

| Type | Description | Use Case |
|------|-------------|----------|
| **AWS managed** | Managed by AWS | Default encryption for AWS services |
| **Customer managed** | You manage | Application encryption, full control |
| **AWS owned** | Shared across accounts | Not visible to you |
| **Custom key store** | CloudHSM | FIPS 140-2 Level 3 |

**Pricing** (us-east-1, 2024):
- Customer managed key: $1/month
- AWS managed key: Free
- API requests: $0.03 per 10,000 requests
- CloudHSM: $1.60/hour per HSM

**Python SDK Example**:
```python
import boto3
import base64

kms = boto3.client('kms')

# Create customer managed key
response = kms.create_key(
    Description='Application encryption key',
    KeyUsage='ENCRYPT_DECRYPT',
    Origin='AWS_KMS'
)

key_id = response['KeyMetadata']['KeyId']

# Create alias
kms.create_alias(
    AliasName='alias/app-key',
    TargetKeyId=key_id
)

# Enable automatic rotation
kms.enable_key_rotation(KeyId=key_id)

# Encrypt data (max 4 KB)
plaintext = b'Secret data'
encrypt_response = kms.encrypt(
    KeyId='alias/app-key',
    Plaintext=plaintext,
    EncryptionContext={'Department': 'Finance'}  # Additional authenticated data
)

ciphertext = encrypt_response['CiphertextBlob']

# Decrypt
decrypt_response = kms.decrypt(
    CiphertextBlob=ciphertext,
    EncryptionContext={'Department': 'Finance'}  # Must match
)

decrypted = decrypt_response['Plaintext']
assert decrypted == plaintext

# Generate data key (for envelope encryption)
datakey_response = kms.generate_data_key(
    KeyId='alias/app-key',
    KeySpec='AES_256'
)

dek_plaintext = datakey_response['Plaintext']      # Use to encrypt data
dek_encrypted = datakey_response['CiphertextBlob']  # Store with encrypted data
```

**Multi-Region Keys**:
```python
# Create multi-region key
response = kms.create_key(
    Description='Multi-region key',
    MultiRegion=True
)

primary_key_id = response['KeyMetadata']['KeyId']

# Replicate to another region
kms_replica = boto3.client('kms', region_name='eu-west-1')
kms_replica.replicate_key(
    KeyId=primary_key_id,
    ReplicaRegion='eu-west-1'
)
```

### Google Cloud KMS

**Features**:
- FIPS 140-2 Level 3 validated (with Cloud HSM)
- Automatic key rotation (configurable 30-36500 days)
- Integrated with GCP services (GCS, GCE, BigQuery, etc.)
- Software and hardware (HSM) keys
- Multi-region keys
- Audit logging (Cloud Audit Logs)
- External key manager (EKM) support

**Key Protection Levels**:

| Level | Description | FIPS |
|-------|-------------|------|
| **Software** | Software-protected | 140-2 Level 1 |
| **HSM** | Hardware-protected | 140-2 Level 3 |
| **External** | Customer-managed (EKM) | Depends on external HSM |

**Pricing** (2024):
- Software key: $0.06/month
- HSM key: $2.50/month
- External key: $0.60/month
- Operations: $0.03 per 10,000

**Python SDK Example**:
```python
from google.cloud import kms

client = kms.KeyManagementServiceClient()

project_id = 'my-project'
location_id = 'us-east1'
key_ring_id = 'my-keyring'
key_id = 'my-key'

# Create key ring
location_path = f'projects/{project_id}/locations/{location_id}'
key_ring_path = f'{location_path}/keyRings/{key_ring_id}'

try:
    client.create_key_ring(
        request={'parent': location_path, 'key_ring_id': key_ring_id}
    )
except:
    pass  # Key ring already exists

# Create crypto key
key_path = f'{key_ring_path}/cryptoKeys/{key_id}'

try:
    client.create_crypto_key(
        request={
            'parent': key_ring_path,
            'crypto_key_id': key_id,
            'crypto_key': {
                'purpose': kms.CryptoKey.CryptoKeyPurpose.ENCRYPT_DECRYPT,
                'version_template': {
                    'protection_level': kms.ProtectionLevel.HSM,  # Or SOFTWARE
                    'algorithm': kms.CryptoKeyVersion.CryptoKeyVersionAlgorithm.GOOGLE_SYMMETRIC_ENCRYPTION
                },
                'rotation_period': {'seconds': 86400 * 90},  # 90 days
                'next_rotation_time': {'seconds': int(time.time()) + 86400 * 90}
            }
        }
    )
except:
    pass  # Key already exists

# Encrypt
plaintext = b'Secret data'
encrypt_response = client.encrypt(
    request={'name': key_path, 'plaintext': plaintext}
)
ciphertext = encrypt_response.ciphertext

# Decrypt
decrypt_response = client.decrypt(
    request={'name': key_path, 'ciphertext': ciphertext}
)
decrypted = decrypt_response.plaintext

assert decrypted == plaintext
```

### Azure Key Vault

**Features**:
- FIPS 140-2 Level 2 validated (Premium: Level 3 with HSM)
- Keys, secrets, and certificates
- Automatic key rotation (configurable)
- Integrated with Azure services
- Soft-delete and purge protection
- Access control (RBAC, access policies)
- Audit logging (Azure Monitor)
- Managed HSM

**SKUs**:

| SKU | Description | FIPS | Price |
|-----|-------------|------|-------|
| **Standard** | Software keys | 140-2 Level 1 | $0.03/10K ops |
| **Premium** | HSM keys | 140-2 Level 2 | $1/key/month |
| **Managed HSM** | Dedicated HSM pool | 140-2 Level 3 | $4/hour |

**Python SDK Example**:
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.keys import KeyClient
from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm

vault_name = 'my-keyvault'
vault_url = f'https://{vault_name}.vault.azure.net/'

credential = DefaultAzureCredential()
key_client = KeyClient(vault_url=vault_url, credential=credential)

# Create RSA key
rsa_key = key_client.create_rsa_key(
    'app-rsa-key',
    size=2048,
    hardware_protected=True  # Premium SKU required
)

# Create EC key
ec_key = key_client.create_ec_key(
    'app-ec-key',
    curve='P-256',
    hardware_protected=True
)

# Encrypt data
crypto_client = CryptographyClient(rsa_key, credential)
plaintext = b'Secret data'
result = crypto_client.encrypt(EncryptionAlgorithm.rsa_oaep, plaintext)
ciphertext = result.ciphertext

# Decrypt
result = crypto_client.decrypt(EncryptionAlgorithm.rsa_oaep, ciphertext)
decrypted = result.plaintext

assert decrypted == plaintext

# Enable key rotation
key_client.update_key_rotation_policy(
    'app-rsa-key',
    {
        'lifetimeActions': [{
            'trigger': {'timeAfterCreate': 'P90D'},  # 90 days
            'action': {'type': 'Rotate'}
        }],
        'expiryTime': 'P2Y'  # 2 years
    }
)
```

### HashiCorp Vault

**Features**:
- Open source and Enterprise
- Transit secrets engine (encryption as a service)
- Dynamic secrets
- Secrets versioning
- Multiple authentication methods
- Audit logging
- High availability
- Self-hosted or managed (HCP Vault)
- Multi-cloud support

**Deployment Options**:

| Option | Description | Cost |
|--------|-------------|------|
| **Open Source** | Self-hosted | Free (infra costs) |
| **Enterprise** | Self-hosted + features | License required |
| **HCP Vault** | Managed service | $0.03/hour + usage |

**Setup**:
```bash
# Start Vault dev server (testing only)
vault server -dev

# Production setup
vault server -config=vault.hcl

# Initialize
vault operator init

# Unseal (required after restart)
vault operator unseal <unseal-key-1>
vault operator unseal <unseal-key-2>
vault operator unseal <unseal-key-3>

# Enable Transit secrets engine
vault secrets enable transit

# Create encryption key
vault write -f transit/keys/app-key
```

**Python SDK (hvac)**:
```python
import hvac
import base64

client = hvac.Client(url='http://127.0.0.1:8200', token='dev-token')

# Create transit key
client.secrets.transit.create_key('app-key')

# Encrypt
plaintext = b'Secret data'
encrypted = client.secrets.transit.encrypt_data(
    name='app-key',
    plaintext=base64.b64encode(plaintext).decode('utf-8')
)

ciphertext = encrypted['data']['ciphertext']  # "vault:v1:..."

# Decrypt
decrypted = client.secrets.transit.decrypt_data(
    name='app-key',
    ciphertext=ciphertext
)

plaintext_decoded = base64.b64decode(decrypted['data']['plaintext'])
assert plaintext_decoded == plaintext

# Rotate key
client.secrets.transit.rotate_key('app-key')

# Re-encrypt with new key version
rewrapped = client.secrets.transit.rewrap_data(
    name='app-key',
    ciphertext=ciphertext
)

new_ciphertext = rewrapped['data']['ciphertext']  # "vault:v2:..."
```

---

## HSM Integration

### What is an HSM?

**Hardware Security Module (HSM)**: Tamper-resistant hardware device for cryptographic operations and key storage.

**Key Features**:
- Keys never leave HSM in plaintext
- FIPS 140-2 Level 3 or 4 certified
- Physical security (tamper detection, zeroization)
- High performance (dedicated crypto processors)
- Audit logging
- Dual control / split knowledge

### FIPS 140-2 Levels

| Level | Requirements | Examples |
|-------|-------------|----------|
| **Level 1** | Software only | OpenSSL, Java crypto |
| **Level 2** | Tamper-evident seals, role-based auth | AWS KMS, Azure Key Vault Standard |
| **Level 3** | Tamper-resistant hardware, identity-based auth | Thales Luna, nCipher, AWS CloudHSM |
| **Level 4** | Environmental protection (voltage, temperature) | Government/military HSMs |

### HSM Vendors

#### Thales Luna HSM

**Features**:
- FIPS 140-2 Level 3 certified
- Network-attached or PCIe
- HA clustering
- Backup/restore
- PKCS#11, JCE, CNG, OpenSSL support

**Use Case**: Enterprise PKI, code signing, database encryption

#### nCipher nShield

**Features**:
- FIPS 140-2 Level 3 certified
- Solo (PCIe), Connect (network), Edge (portable)
- Code signing, TLS acceleration
- Smart card authentication

**Use Case**: Financial services, certificate authorities

#### AWS CloudHSM

**Features**:
- FIPS 140-2 Level 3 certified
- Dedicated single-tenant HSM
- VPC-based access
- PKCS#11, JCE, CNG support
- $1-5/hour pricing

**Setup**:
```bash
# Create cluster
aws cloudhsmv2 create-cluster \
  --hsm-type hsm1.medium \
  --subnet-ids subnet-12345 subnet-67890

# Create HSM
aws cloudhsmv2 create-hsm \
  --cluster-id cluster-abc123 \
  --availability-zone us-east-1a

# Initialize cluster
# Download and install CloudHSM client
sudo yum install -y aws-cloudhsmv2-cli

# Configure client
/opt/cloudhsm/bin/configure -a <cluster-IP>

# Activate cluster (one-time)
/opt/cloudhsm/bin/cloudhsm_mgmt_util

# Create crypto user
createUser CU crypto-user <password>
```

**Python Example (PKCS#11)**:
```python
from pkcs11 import Session, lib

# Load CloudHSM PKCS#11 library
lib_path = '/opt/cloudhsm/lib/libcloudhsm_pkcs11.so'
pkcs11_lib = lib(lib_path)

# Get slot
slot = pkcs11_lib.get_slots()[0]

# Open session
with slot.open(user_pin='crypto-user:password') as session:
    # Generate AES key
    key = session.generate_key(
        KeyType.AES,
        256,
        label='app-encryption-key',
        store=True
    )

    # Encrypt data
    plaintext = b'Secret data'
    iv = session.generate_random(16)
    ciphertext = key.encrypt(plaintext, mechanism_param=iv)

    # Decrypt
    decrypted = key.decrypt(ciphertext, mechanism_param=iv)
    assert decrypted == plaintext
```

### PKCS#11 Interface

**What**: Standard API for cryptographic tokens (HSMs, smart cards)

**Common Operations**:

```c
// C Example
#include <pkcs11.h>

CK_RV rv;
CK_SESSION_HANDLE session;
CK_OBJECT_HANDLE key;

// Initialize library
rv = C_Initialize(NULL);

// Open session
rv = C_OpenSession(slotID, CKF_SERIAL_SESSION | CKF_RW_SESSION, NULL, NULL, &session);

// Login
rv = C_Login(session, CKU_USER, (CK_UTF8CHAR *)"password", strlen("password"));

// Generate key
CK_MECHANISM mechanism = {CKM_AES_KEY_GEN, NULL, 0};
CK_ULONG keyLen = 32;

CK_ATTRIBUTE template[] = {
    {CKA_VALUE_LEN, &keyLen, sizeof(keyLen)},
    {CKA_ENCRYPT, &trueValue, sizeof(trueValue)},
    {CKA_DECRYPT, &trueValue, sizeof(trueValue)},
};

rv = C_GenerateKey(session, &mechanism, template, 3, &key);

// Encrypt
CK_MECHANISM encMech = {CKM_AES_GCM, &gcmParams, sizeof(gcmParams)};
rv = C_EncryptInit(session, &encMech, key);
rv = C_Encrypt(session, plaintext, plaintextLen, ciphertext, &ciphertextLen);

// Cleanup
C_Logout(session);
C_CloseSession(session);
C_Finalize(NULL);
```

### Common Cryptographic Standards

(FIPS 140-2, PCI-DSS compliance requirements, NIST guidelines continue in full detail...)

