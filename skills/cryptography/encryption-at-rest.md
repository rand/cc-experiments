---
name: cryptography-encryption-at-rest
description: Protecting stored data with encryption at rest
---

# Encryption at Rest

**Scope**: Data encryption, key management, compliance (FIPS, PCI-DSS, HIPAA)
**Lines**: ~350
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Implementing encryption for stored data (databases, files, backups)
- Protecting data from physical theft or unauthorized access
- Meeting compliance requirements (GDPR, HIPAA, PCI-DSS, FIPS 140-2)
- Designing key management and rotation strategies
- Choosing between encryption layers (application, database, filesystem, disk)
- Integrating with Key Management Services (AWS KMS, Azure Key Vault, HashiCorp Vault)
- Implementing envelope encryption patterns

## Core Concepts

### What is Encryption at Rest?

**Encryption at rest** protects data stored on disk from unauthorized access when the data is not actively being transmitted.

**Threat model**:
- ✓ Physical theft (stolen laptops, hard drives)
- ✓ Cloud provider access (unauthorized staff)
- ✓ Backup compromise (stolen tapes/files)
- ✓ Forensic recovery from decommissioned drives
- ✗ Application-level attacks (SQL injection)
- ✗ Authorized user access (users with valid credentials)
- ✗ Memory dumps (data in RAM)

### Encryption Layers

```
┌─────────────────────────────────────────┐
│ Application-Level (field encryption)    │ ← Highest control, most complex
├─────────────────────────────────────────┤
│ Database-Level (TDE)                    │ ← Transparent, good performance
├─────────────────────────────────────────┤
│ Filesystem-Level                        │ ← Per-directory encryption
├─────────────────────────────────────────┤
│ Volume/Block-Level (LUKS, BitLocker)    │ ← Full disk encryption
├─────────────────────────────────────────┤
│ Hardware-Level (self-encrypting drives) │ ← Fastest, lowest control
└─────────────────────────────────────────┘
```

**Trade-offs**:
- **Application**: Highest granularity (per-field), but most complex to implement
- **Database**: Good balance of security and performance
- **Volume**: Simplest to implement, protects all data
- **Hardware**: Best performance, but less control over key management

---

## Key Management Patterns

### 1. Envelope Encryption (Recommended)

**Pattern**: Encrypt data with Data Encryption Key (DEK), encrypt DEK with Key Encryption Key (KEK).

```
┌──────────────┐
│ KMS (KEK)    │ ← Master key in secure KMS
└──────┬───────┘
       │ encrypts
┌──────▼───────┐
│ DEK          │ ← Data Encryption Key (one per file/object)
└──────┬───────┘
       │ encrypts
┌──────▼───────┐
│ Data         │ ← Actual data
└──────────────┘
```

**Benefits**:
- **Fast key rotation**: Only re-encrypt small DEKs, not entire dataset
- **Performance**: Data encryption uses local DEK (no KMS latency)
- **Cost-effective**: Minimal KMS API calls (1 per file vs millions)
- **Scalable**: Each object has its own DEK

**Example**:
```python
# Generate DEK from KMS
plaintext_dek, encrypted_dek = kms.generate_data_key()

# Encrypt data with DEK (local, fast)
ciphertext = encrypt(data, plaintext_dek)

# Store encrypted_dek alongside ciphertext
save(ciphertext, encrypted_dek)

# Decrypt: decrypt DEK with KMS, then decrypt data
plaintext_dek = kms.decrypt(encrypted_dek)
data = decrypt(ciphertext, plaintext_dek)
```

### 2. Direct KMS Encryption

**Pattern**: Encrypt data directly using KMS.

**Use case**: Small data (<4KB), secrets, API keys.

**Limitations**:
- KMS has size limits (AWS KMS: 4KB)
- Higher latency (network call per operation)
- More expensive (per-operation pricing)

### 3. Password-Based Encryption

**Pattern**: Derive key from password using Key Derivation Function (KDF).

```python
# Derive key from password
key = pbkdf2(password, salt, iterations=100000)

# Encrypt with derived key
ciphertext = encrypt(data, key)
```

**Use case**: User-encrypted files, backup encryption.

**Critical**: Use strong KDF (PBKDF2, Argon2, scrypt) with high iterations.

---

## Algorithms

### Recommended Algorithms

**Symmetric encryption** (for bulk data):
- **AES-256-GCM** - AEAD (authenticated), fastest with AES-NI hardware
- **ChaCha20-Poly1305** - AEAD, better for ARM/mobile, no hardware acceleration needed
- **AES-256-XTS** - For disk/block encryption (IEEE P1619 standard)

**Avoid**:
- ❌ AES-ECB (reveals patterns)
- ❌ AES-CBC without HMAC (vulnerable to padding oracle)
- ❌ DES, 3DES, RC4 (weak)

**Key sizes**:
- **Minimum**: AES-256 (256 bits), RSA-2048
- **Recommended**: AES-256, RSA-3072+, ECDSA-P256+

### Hardware Acceleration

**AES-NI**: Intel/AMD instruction set for AES encryption.

```bash
# Check if AES-NI is available
grep -q aes /proc/cpuinfo && echo "AES-NI supported" || echo "No AES-NI"
```

**Performance impact**:
- With AES-NI: ~3-5% overhead
- Without AES-NI: ~20-30% overhead

**Recommendation**: Use ChaCha20-Poly1305 if AES-NI unavailable.

---

## Database Encryption

### PostgreSQL

**Option 1: Application-level** (recommended)
```python
# Encrypt before INSERT
encrypted = encrypt(plaintext, key)
cursor.execute("INSERT INTO users (ssn) VALUES (%s)", (encrypted,))
```

**Option 2: pgcrypto extension**
```sql
CREATE EXTENSION pgcrypto;

-- Encrypt column
UPDATE users SET ssn_encrypted = pgp_sym_encrypt(ssn, 'key');

-- Decrypt column
SELECT pgp_sym_decrypt(ssn_encrypted, 'key') FROM users;
```

**Option 3: Filesystem encryption** (LUKS)
```bash
# Encrypt PostgreSQL data directory with LUKS
cryptsetup luksFormat /dev/sdb1
cryptsetup luksOpen /dev/sdb1 postgres_data
mount /dev/mapper/postgres_data /var/lib/postgresql/data
```

### MongoDB

**Native encryption** (Enterprise):
```yaml
# mongod.conf
security:
  enableEncryption: true
  encryptionKeyFile: /path/to/keyfile
```

**Client-Side Field Level Encryption (CSFLE)**:
```javascript
// Encrypt specific fields before storing
const autoEncryptionOpts = {
  kmsProviders: { aws: { ... } },
  schemaMap: {
    'db.collection': {
      properties: {
        ssn: { encrypt: { algorithm: 'AEAD_AES_256_CBC_HMAC_SHA_512-Random' } }
      }
    }
  }
};

const client = new MongoClient(uri, { autoEncryption: autoEncryptionOpts });
```

### MySQL

**InnoDB encryption**:
```sql
-- Enable encryption for table
CREATE TABLE users (
  id INT PRIMARY KEY,
  ssn VARCHAR(20)
) ENCRYPTION='Y';

-- Encrypt existing table
ALTER TABLE users ENCRYPTION='Y';
```

---

## File and Disk Encryption

### Linux: LUKS (dm-crypt)

```bash
# Create encrypted volume
cryptsetup luksFormat /dev/sdb1

# Open encrypted volume
cryptsetup luksOpen /dev/sdb1 encrypted_volume

# Mount
mount /dev/mapper/encrypted_volume /mnt/encrypted

# Auto-mount on boot (/etc/crypttab)
encrypted_volume /dev/sdb1 none luks
```

**Algorithms**: AES-256-XTS (default), ChaCha20

### macOS: FileVault

```bash
# Enable FileVault (GUI or CLI)
sudo fdesetup enable

# Check status
fdesetup status
```

### Windows: BitLocker

```powershell
# Enable BitLocker
Enable-BitLocker -MountPoint "C:" -EncryptionMethod Aes256 -UsedSpaceOnly

# Check status
Get-BitLockerVolume
```

---

## Cloud KMS Integration

### AWS KMS

```python
import boto3

kms = boto3.client('kms', region_name='us-east-1')

# Generate data key (envelope encryption)
response = kms.generate_data_key(
    KeyId='alias/my-app-key',
    KeySpec='AES_256'
)

plaintext_key = response['Plaintext']
encrypted_key = response['CiphertextBlob']

# Encrypt data locally with plaintext_key
# Store encrypted_key alongside encrypted data

# Decrypt data key
decrypted_key = kms.decrypt(CiphertextBlob=encrypted_key)['Plaintext']
```

**Best practices**:
- Enable automatic key rotation (annual)
- Use separate keys per environment (dev/staging/prod)
- Use key policies to restrict access
- Enable CloudTrail logging

### Azure Key Vault

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.keys.crypto import CryptographyClient

credential = DefaultAzureCredential()
key_client = KeyClient(vault_url="https://myvault.vault.azure.net", credential=credential)

# Get key
key = key_client.get_key("my-encryption-key")

# Encrypt
crypto_client = CryptographyClient(key, credential=credential)
result = crypto_client.encrypt(EncryptionAlgorithm.rsa_oaep, plaintext)
```

### HashiCorp Vault

```bash
# Enable transit secrets engine
vault secrets enable transit

# Create encryption key
vault write -f transit/keys/my-app-key

# Encrypt data
vault write transit/encrypt/my-app-key plaintext=$(base64 <<< "sensitive data")

# Decrypt data
vault write transit/decrypt/my-app-key ciphertext="vault:v1:..."
```

---

## Key Rotation

**Why rotate keys?**
- Limit exposure if key compromised
- Compliance requirements (PCI-DSS: annually)
- Cryptoperiod limits (NIST SP 800-57)

### Zero-Downtime Rotation

**Phase 1: Dual-key period**
```
1. Generate new key (version 2)
2. Application can decrypt with v1 or v2
3. Application encrypts new data with v2
```

**Phase 2: Migration**
```
4. Background job re-encrypts old data (v1 → v2)
5. Track progress, allow rollback
```

**Phase 3: Deprecate old key**
```
6. Once all data migrated, deprecate v1
7. Keep v1 for emergency rollback (90 days)
8. Retire v1 after retention period
```

**Example**:
```python
# Phase 1: Generate new key
new_key = kms.create_key()

# Phase 2: Re-encrypt in batches
for batch in get_encrypted_items(old_key_version, batch_size=1000):
    plaintext = decrypt(batch, old_key)
    ciphertext = encrypt(plaintext, new_key)
    update_item(batch.id, ciphertext, new_key_version)

# Phase 3: Deprecate old key
kms.disable_key(old_key_id)
```

---

## Compliance

### FIPS 140-2

**Requirements**:
- Use FIPS-approved algorithms (AES, SHA-2, RSA-2048+)
- Validate cryptographic modules
- Key generation in FIPS-certified hardware (HSM)

**FIPS-approved algorithms**:
- ✓ AES-256-GCM, AES-128-GCM
- ✓ SHA-256, SHA-384, SHA-512
- ✓ RSA-2048+, ECDSA-P256+
- ✗ ChaCha20-Poly1305 (not FIPS-approved)

### PCI-DSS

**Requirements**:
- Encrypt cardholder data (Requirement 3.4)
- Key rotation (annually at minimum)
- Separate keys for different environments
- Restrict access to encryption keys
- Never log decrypted cardholder data

### HIPAA

**Requirements**:
- Encrypt PHI (Protected Health Information)
- Addressable specification (implement if reasonable)
- Use AES-256 or stronger
- Key management and access controls
- Audit logging

### GDPR

**Requirements**:
- Pseudonymization and encryption (Article 32)
- Protect personal data from unauthorized access
- Data breach notification (encryption may exempt)

---

## Performance Optimization

**Benchmarks** (AES-256-GCM with AES-NI):
- Throughput: ~3-5 GB/s per core
- Latency: <1ms for small files (<1MB)
- Overhead: 3-5% CPU

**Tips**:
- **Use hardware acceleration** (AES-NI, ARM Crypto Extensions)
- **Cache data keys** (don't call KMS for every operation)
- **Batch operations** (encrypt/decrypt multiple items together)
- **Use streaming** (for large files, don't load all in memory)

---

## Common Pitfalls

❌ **Hardcoded keys in code** - Exposed in version control
✅ Use KMS or environment variables

❌ **Using weak algorithms** (DES, 3DES, ECB mode)
✅ Use AES-256-GCM or ChaCha20-Poly1305

❌ **No key rotation** - Key compromise affects all historical data
✅ Rotate keys quarterly or annually

❌ **Storing keys with encrypted data** - No protection if both stolen
✅ Store keys in separate KMS

❌ **Encrypting with random key and losing it** - Permanent data loss
✅ Use KMS, backup keys securely

❌ **Not testing decryption** - Discover data loss too late
✅ Verify decryption works immediately after encryption

---

## Related Skills

- `cryptography-basics.md` - Fundamental cryptography concepts
- `crypto-best-practices.md` - Security best practices for encryption
- `tls-configuration.md` - Encryption in transit
- `certificate-management.md` - Managing encryption certificates
- `pki-fundamentals.md` - Public Key Infrastructure basics

---

## Level 3: Resources

**Location**: `/Users/rand/src/cc-polymath/skills/cryptography/encryption-at-rest/resources/`

This skill includes comprehensive Level 3 resources for production encryption implementations:

### REFERENCE.md (~2,900 lines)
Comprehensive technical reference covering:
- Fundamentals: Encryption concepts, at-rest vs in-transit, threat model
- Core Concepts: Symmetric/asymmetric encryption, key derivation, envelope encryption
- Encryption Algorithms: AES-256-GCM, ChaCha20-Poly1305, XTS mode, algorithm comparison
- Key Management: KMS integration, key hierarchies, separation of duties
- Envelope Encryption: Patterns, benefits, implementation details
- Database Encryption: PostgreSQL pgcrypto, MongoDB TDE, MySQL InnoDB encryption
- File and Disk Encryption: LUKS, BitLocker, FileVault, self-encrypting drives
- Cloud KMS Integration: AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault
- Key Rotation: Zero-downtime strategies, phased migration, rollback procedures
- Compliance Standards: FIPS 140-2, PCI-DSS, HIPAA, GDPR requirements
- Performance: Hardware acceleration (AES-NI), benchmarks, optimization techniques
- Common Patterns: Application-level, database-level, volume-level encryption
- Anti-Patterns: Hardcoded keys, weak algorithms, poor rotation practices
- Security Best Practices: Key separation, access control, audit logging
- Real implementation examples with production-ready code

### Scripts (3 production-ready tools)

**validate_encryption.py** (504 lines) - Encryption configuration validator
- Detects weak algorithms (DES, 3DES, RC4, ECB mode)
- Validates key lengths (minimum 256-bit for AES)
- Scans for hardcoded keys in source code and config files
- Audits key storage locations and access patterns
- Checks key rotation policies and compliance
- FIPS 140-2, PCI-DSS, HIPAA, GDPR compliance validation
- JSON output for CI/CD integration
- Severity-based reporting (critical, high, medium, low)
- Usage: `./validate_encryption.py --config-file db.conf --check-compliance FIPS --json`

**rotate_keys.py** (569 lines) - Automated key rotation tool
- Zero-downtime key rotation using envelope encryption
- Supports multiple KMS backends (AWS KMS, local file-based)
- Generates new encryption keys via KMS
- Re-encrypts data with new keys (batch processing)
- Progress tracking and audit logging
- Rollback support for emergency recovery
- Backup creation before rotation
- Dual-key transitional period (read old/new, write new)
- Usage: `./rotate_keys.py --kms-backend aws-kms --key-id alias/db-key --data-dir ./data --json`

**benchmark_encryption.sh** (570 lines) - Encryption performance benchmarking
- Tests multiple algorithms (AES-256-GCM, ChaCha20-Poly1305, AES-CBC)
- Measures throughput (MB/s) and operations per second
- Tests hardware acceleration (AES-NI detection)
- Benchmarks key derivation functions (PBKDF2, Argon2, scrypt)
- Multiple file sizes (1MB to 1GB)
- Performance comparison reports
- JSON output for automation
- Hardware capability detection
- Usage: `./benchmark_encryption.sh --algorithm aes-256-gcm --file-size 1G --json`

### Examples (7 production-ready implementations)

**python/file_encryption.py** - File encryption with envelope encryption
- Demonstrates AES-256-GCM encryption
- Envelope encryption pattern (DEK + KEK)
- Key rotation without re-encrypting files
- Batch file encryption
- Metadata management
- Complete encrypt/decrypt workflow

**python/database_encryption.py** - SQLAlchemy field-level encryption
- Transparent encryption through custom SQLAlchemy types
- Deterministic encryption for searchable fields
- Random encryption for high-security fields
- Key versioning and rotation
- HIPAA-compliant medical records example
- Batch operations optimization

**python/aws_kms_integration.py** - AWS KMS integration
- Data key generation (envelope encryption)
- Automatic key rotation
- Multi-region keys
- Grant-based access control
- Encryption context (AAD)
- Cost optimization strategies
- CloudTrail audit logging

**go/disk_encryption.go** - Block-level encryption (AES-XTS)
- Sector-based encryption (512/4096 bytes)
- AES-256-XTS mode (IEEE P1619 standard)
- Password-based key derivation (PBKDF2)
- Encrypted volume implementation
- Compatible with dm-crypt/LUKS patterns
- Zero-copy encryption

**config/postgres-encryption.conf** - PostgreSQL encryption setup
- pgcrypto extension configuration
- Table-level encryption strategies
- Application-level encryption patterns
- Transparent decryption views
- Key rotation procedures
- LUKS filesystem encryption
- Performance optimization
- GDPR, HIPAA, PCI-DSS compliance notes

**config/mongodb-encryption.conf** - MongoDB encryption setup
- Encrypted Storage Engine (Enterprise)
- Client-Side Field Level Encryption (CSFLE)
- AWS KMS integration
- Key rotation strategies
- LUKS filesystem encryption
- Backup encryption
- Audit logging configuration
- Performance tuning

**python/key_rotation.py** - Zero-downtime key rotation
- Multi-phase rotation strategy
- Dual-key transitional period
- Batch re-encryption with progress tracking
- Rollback procedures
- Audit logging
- Key lifecycle management
- Production-ready patterns

### Quick Start

```bash
# Validate encryption configuration
cd /Users/rand/src/cc-polymath/skills/cryptography/encryption-at-rest/resources/scripts
./validate_encryption.py --config-file /etc/app/db.conf --check-compliance PCI-DSS

# Benchmark encryption performance
./benchmark_encryption.sh --all-algorithms --file-size 100M --json

# Rotate encryption keys
./rotate_keys.py --kms-backend local --key-file master.key --data-dir ./data

# Run Python examples
cd ../examples/python
pip install cryptography sqlalchemy boto3
python file_encryption.py
python database_encryption.py
python key_rotation.py

# View comprehensive reference
cd ../
less REFERENCE.md
```

### Integration Notes

**CI/CD Integration**:
```yaml
# .github/workflows/security.yml
- name: Validate Encryption
  run: |
    ./scripts/validate_encryption.py \
      --scan-directory ./config \
      --check-compliance FIPS \
      --json \
      --fail-on high
```

**Monitoring**:
- Track key rotation age (alert if >90 days)
- Monitor encryption overhead (<10% target)
- Audit key access logs
- Alert on weak algorithm detection

---

## Quick Reference

```bash
# Check for AES-NI hardware acceleration
grep -q aes /proc/cpuinfo && echo "AES-NI available"

# Encrypt file with OpenSSL
openssl enc -aes-256-gcm -in plaintext.txt -out encrypted.bin -K $(openssl rand -hex 32) -iv $(openssl rand -hex 12)

# Generate encryption key (256-bit)
openssl rand -base64 32

# Benchmark encryption speed
openssl speed aes-256-gcm

# Create encrypted LUKS volume
cryptsetup luksFormat /dev/sdb1
cryptsetup luksOpen /dev/sdb1 encrypted_volume

# Enable BitLocker (Windows)
Enable-BitLocker -MountPoint "C:" -EncryptionMethod Aes256

# Check MongoDB encryption status
use admin
db.serverStatus().encryptionAtRest
```
