---
name: cryptography-crypto-best-practices
description: Cryptography best practices, common mistakes, security patterns, and anti-patterns to avoid
---

# Cryptography Best Practices

**Scope**: Security patterns, common mistakes, anti-patterns, implementation guidelines
**Lines**: ~340
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Implementing cryptographic systems
- Reviewing security code
- Choosing crypto algorithms
- Handling keys and secrets
- Building authentication systems
- Conducting security audits
- Preventing crypto vulnerabilities
- Following compliance requirements

## Golden Rules

```
1. Don't roll your own crypto
2. Use high-level APIs and established libraries
3. Keep crypto libraries updated
4. Use authenticated encryption
5. Generate truly random keys
6. Never reuse nonces with same key
7. Use constant-time comparisons
8. Protect keys at rest and in transit
```

---

## Common Mistakes

### Mistake 1: ECB Mode

**Problem**: Identical plaintext blocks → identical ciphertext

```python
# ❌ WRONG: ECB mode leaks patterns
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

cipher = Cipher(algorithms.AES(key), modes.ECB())
# Images encrypted with ECB show original patterns!
```

**Solution**: Use GCM or CTR mode
```python
# ✅ CORRECT: GCM mode (authenticated encryption)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

aesgcm = AESGCM(key)
ciphertext = aesgcm.encrypt(nonce, plaintext, None)
```

### Mistake 2: Weak Random Number Generation

```python
# ❌ WRONG: Predictable randomness
import random
key = random.randbytes(32)  # NOT cryptographically secure
token = str(random.randint(1000, 9999))  # Predictable

# ✅ CORRECT: Cryptographically secure
import secrets
key = secrets.token_bytes(32)
token = secrets.token_urlsafe(32)
```

### Mistake 3: Nonce Reuse

```python
# ❌ WRONG: Reusing nonce with same key
nonce = b'\x00' * 12  # Fixed nonce!
for message in messages:
    ciphertext = aesgcm.encrypt(nonce, message, None)  # VULNERABLE!

# ✅ CORRECT: Random nonce for each message
import os
for message in messages:
    nonce = os.urandom(12)  # New nonce each time
    ciphertext = aesgcm.encrypt(nonce, message, None)
```

### Mistake 4: Unauthenticated Encryption

```python
# ❌ WRONG: Encryption without authentication
cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
ciphertext = cipher.encryptor().update(plaintext)
# Attacker can modify ciphertext!

# ✅ CORRECT: Authenticated encryption
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
aesgcm = AESGCM(key)
ciphertext = aesgcm.encrypt(nonce, plaintext, None)
# Any tampering detected
```

### Mistake 5: Timing Attacks

```python
# ❌ WRONG: Variable-time comparison
def verify_token(submitted, expected):
    return submitted == expected  # Leaks timing info

# ✅ CORRECT: Constant-time comparison
import hmac
def verify_token(submitted, expected):
    return hmac.compare_digest(submitted, expected)
```

### Mistake 6: Hardcoded Keys

```python
# ❌ WRONG: Key in source code
SECRET_KEY = b'my_secret_key_123'

# ✅ CORRECT: Key from environment/vault
import os
SECRET_KEY = os.environ['SECRET_KEY'].encode()
```

### Mistake 7: Weak Password Hashing

```python
# ❌ WRONG: Fast hash (MD5, SHA-1, SHA-256)
import hashlib
password_hash = hashlib.sha256(password).hexdigest()  # Too fast!

# ✅ CORRECT: Slow, salted hash
import bcrypt
password_hash = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))

# ✅ EVEN BETTER: Argon2
from argon2 import PasswordHasher
ph = PasswordHasher()
password_hash = ph.hash(password)
```

---

## Best Practices

### Practice 1: Use High-Level APIs

```python
# ✅ BEST: Fernet (symmetric encryption made easy)
from cryptography.fernet import Fernet

key = Fernet.generate_key()
f = Fernet(key)

ciphertext = f.encrypt(b"Secret message")
plaintext = f.decrypt(ciphertext)

# Fernet handles:
# - Key derivation
# - IV generation
# - Authentication (HMAC)
# - Timestamp verification
```

### Practice 2: Key Derivation

```python
# ✅ CORRECT: Derive encryption keys from passwords
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os

def derive_key(password: bytes, salt: bytes = None) -> bytes:
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,  # OWASP recommendation 2023
    )
    key = kdf.derive(password)
    return key, salt

# Derive key from password
key, salt = derive_key(b"user_password")
# Store salt with ciphertext
```

### Practice 3: Secure Key Storage

**Environment variables**:
```bash
# ✅ Good for development
export SECRET_KEY="base64_encoded_key"
```

**Secrets management**:
```python
# ✅ BETTER: Use secrets manager
import boto3

def get_key():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='my-app/secret-key')
    return response['SecretString'].encode()
```

**Hardware security modules**:
```python
# ✅ BEST: Use HSM for production
# Keys never leave HSM
# Examples: AWS KMS, Google Cloud KMS, Azure Key Vault
```

### Practice 4: Key Rotation

```python
# ✅ Support multiple active keys
class KeyManager:
    def __init__(self):
        self.keys = {
            'v1': load_key('key_v1'),
            'v2': load_key('key_v2'),  # New key
        }
        self.current_version = 'v2'

    def encrypt(self, data):
        key = self.keys[self.current_version]
        ciphertext = encrypt_with_key(key, data)
        return {
            'version': self.current_version,
            'ciphertext': ciphertext
        }

    def decrypt(self, encrypted_data):
        version = encrypted_data['version']
        key = self.keys[version]  # Use old key if needed
        return decrypt_with_key(key, encrypted_data['ciphertext'])
```

### Practice 5: Salt Everything

```python
# ✅ CORRECT: Unique salt per password
import os
import hashlib

def hash_password(password: str) -> tuple:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt, key

def verify_password(password: str, salt: bytes, expected_key: bytes) -> bool:
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return hmac.compare_digest(key, expected_key)
```

---

## Secure Patterns

### Pattern 1: Envelope Encryption

**Encrypt data with DEK, encrypt DEK with KEK**:
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

class EnvelopeEncryption:
    def __init__(self, kek):
        """KEK = Key Encryption Key (from KMS)"""
        self.kek = AESGCM(kek)

    def encrypt(self, plaintext):
        # Generate Data Encryption Key
        dek = AESGCM.generate_key(bit_length=256)

        # Encrypt data with DEK
        aesgcm_dek = AESGCM(dek)
        data_nonce = os.urandom(12)
        ciphertext = aesgcm_dek.encrypt(data_nonce, plaintext, None)

        # Encrypt DEK with KEK
        kek_nonce = os.urandom(12)
        encrypted_dek = self.kek.encrypt(kek_nonce, dek, None)

        return {
            'encrypted_dek': encrypted_dek,
            'kek_nonce': kek_nonce,
            'data_nonce': data_nonce,
            'ciphertext': ciphertext
        }

    def decrypt(self, encrypted_data):
        # Decrypt DEK with KEK
        dek = self.kek.decrypt(
            encrypted_data['kek_nonce'],
            encrypted_data['encrypted_dek'],
            None
        )

        # Decrypt data with DEK
        aesgcm_dek = AESGCM(dek)
        plaintext = aesgcm_dek.decrypt(
            encrypted_data['data_nonce'],
            encrypted_data['ciphertext'],
            None
        )

        return plaintext
```

### Pattern 2: Authenticated Encryption with Associated Data (AEAD)

```python
# Include metadata that must be authentic but not encrypted
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import json

def encrypt_with_metadata(key, plaintext, metadata):
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)

    # Metadata is authenticated but not encrypted
    associated_data = json.dumps(metadata).encode()

    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)

    return {
        'nonce': nonce,
        'ciphertext': ciphertext,
        'metadata': metadata  # Sent in clear
    }

def decrypt_with_metadata(key, encrypted):
    aesgcm = AESGCM(key)
    associated_data = json.dumps(encrypted['metadata']).encode()

    # Decryption fails if metadata was tampered
    plaintext = aesgcm.decrypt(
        encrypted['nonce'],
        encrypted['ciphertext'],
        associated_data
    )

    return plaintext
```

### Pattern 3: Rate Limiting Authentication

```python
# Prevent brute force attacks
from datetime import datetime, timedelta
import time

class RateLimitedAuth:
    def __init__(self):
        self.attempts = {}  # user_id → (count, lockout_until)

    def check_password(self, user_id, password, expected_hash):
        # Check if locked out
        if user_id in self.attempts:
            count, lockout_until = self.attempts[user_id]
            if datetime.now() < lockout_until:
                remaining = (lockout_until - datetime.now()).seconds
                raise Exception(f"Locked out for {remaining}s")

        # Verify password
        if bcrypt.checkpw(password, expected_hash):
            # Success - clear attempts
            self.attempts.pop(user_id, None)
            return True

        # Failed - increment attempts
        count, _ = self.attempts.get(user_id, (0, datetime.now()))
        count += 1

        if count >= 5:
            # Lock out after 5 failed attempts
            lockout_until = datetime.now() + timedelta(minutes=15)
            self.attempts[user_id] = (count, lockout_until)
        else:
            self.attempts[user_id] = (count, datetime.now())

        # Add delay to slow brute force
        time.sleep(min(count, 5))  # Max 5s delay

        return False
```

---

## Security Checklist

### Algorithm Selection

```
✅ Symmetric encryption: AES-256-GCM or ChaCha20-Poly1305
✅ Asymmetric encryption: RSA-OAEP (4096-bit) or ECIES
✅ Digital signatures: Ed25519, ECDSA (P-256), or RSA-PSS
✅ Key exchange: X25519 (ECDH) or DHE
✅ Hashing: SHA-256, SHA-3, or BLAKE2
✅ Password hashing: Argon2id, bcrypt, or scrypt
✅ MAC: HMAC-SHA256 or Poly1305

❌ Avoid: MD5, SHA-1, RC4, DES, 3DES
❌ Avoid: ECB mode, small RSA keys (<2048), weak passwords
```

### Implementation Checklist

```
□ Using cryptographically secure random (secrets/urandom)
□ Generating unique nonce/IV for each encryption
□ Using authenticated encryption (GCM, ChaCha20-Poly1305)
□ Constant-time comparisons for secrets
□ No hardcoded keys or secrets
□ Keys stored securely (HSM, secrets manager)
□ Key rotation supported
□ Passwords hashed with slow algorithm + salt
□ TLS 1.2+ for network communication
□ Certificate validation enabled
□ Inputs validated before crypto operations
□ Crypto library kept updated
□ Security audit performed
```

---

## Anti-Patterns

### Anti-Pattern 1: Crypto as Obfuscation

```python
# ❌ WRONG: XOR "encryption"
def xor_encrypt(data, key):
    return bytes([d ^ key for d in data])  # Trivially broken

# ✅ CORRECT: Real encryption
from cryptography.fernet import Fernet
f = Fernet(key)
ciphertext = f.encrypt(data)
```

### Anti-Pattern 2: Security Through Obscurity

```python
# ❌ WRONG: Custom "secret" algorithm
def my_secure_hash(data):
    # Secret algorithm only I know!
    return some_complex_transformation(data)

# ✅ CORRECT: Standard algorithms
import hashlib
hash_digest = hashlib.sha256(data).hexdigest()
```

### Anti-Pattern 3: Encrypt-Then-MAC Order

```python
# ❌ RISKY: MAC-then-encrypt
mac = hmac.new(mac_key, plaintext).digest()
ciphertext = encrypt(plaintext + mac)

# ✅ CORRECT: Encrypt-then-MAC (or use AEAD)
ciphertext = encrypt(plaintext)
mac = hmac.new(mac_key, ciphertext).digest()

# ✅ BEST: Use AEAD (GCM) - handles authentication
ciphertext = aesgcm.encrypt(nonce, plaintext, None)
```

---

## Testing Cryptographic Code

```python
import unittest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

class TestEncryption(unittest.TestCase):
    def test_encrypt_decrypt(self):
        """Test basic encryption/decryption"""
        key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(key)
        plaintext = b"Test message"
        nonce = os.urandom(12)

        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        recovered = aesgcm.decrypt(nonce, ciphertext, None)

        self.assertEqual(plaintext, recovered)

    def test_tampering_detected(self):
        """Test that tampering is detected"""
        key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(key)
        plaintext = b"Test message"
        nonce = os.urandom(12)

        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Tamper with ciphertext
        tampered = bytearray(ciphertext)
        tampered[0] ^= 1
        tampered = bytes(tampered)

        # Should raise exception
        with self.assertRaises(Exception):
            aesgcm.decrypt(nonce, tampered, None)

    def test_different_nonces(self):
        """Test that same plaintext with different nonces produces different ciphertext"""
        key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(key)
        plaintext = b"Test message"

        nonce1 = os.urandom(12)
        nonce2 = os.urandom(12)

        ciphertext1 = aesgcm.encrypt(nonce1, plaintext, None)
        ciphertext2 = aesgcm.encrypt(nonce2, plaintext, None)

        self.assertNotEqual(ciphertext1, ciphertext2)
```

---

## Related Skills

- `cryptography-cryptography-basics` - Fundamental concepts
- `cryptography-pki-fundamentals` - PKI and certificates
- `cryptography-tls-configuration` - TLS setup
- `security-vulnerability-assessment` - Security auditing

---

**Last Updated**: 2025-10-27
