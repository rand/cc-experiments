---
name: cryptography-cryptography-basics
description: Cryptography fundamentals including symmetric/asymmetric encryption, hashing, signing, key exchange, and common algorithms
---

# Cryptography Basics

**Scope**: Symmetric/asymmetric encryption, hashing, digital signatures, key exchange, common algorithms
**Lines**: ~380
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Understanding encryption fundamentals
- Implementing data encryption
- Selecting cryptographic algorithms
- Working with keys and signatures
- Building secure authentication
- Hashing passwords or data
- Understanding TLS/PKI foundations
- Making security architecture decisions

## Core Concepts

### Cryptographic Primitives

```
1. Encryption/Decryption → Confidentiality
2. Hashing → Integrity
3. Digital Signatures → Authentication + Integrity
4. Key Exchange → Secure channel establishment
```

---

## Symmetric Encryption

### Overview

**Same key for encryption and decryption**:
```
Plaintext → [Encrypt with Key] → Ciphertext
Ciphertext → [Decrypt with Key] → Plaintext
```

**Characteristics**:
- Fast (hardware-accelerated)
- Key must be shared securely
- Used for bulk data encryption

### Common Algorithms

**AES (Advanced Encryption Standard)**:
```
Key sizes: 128, 192, 256 bits
Block size: 128 bits
Modes: GCM (recommended), CBC, CTR
Status: Industry standard, secure
```

**ChaCha20**:
```
Key size: 256 bits
Stream cipher
Often paired with Poly1305 (MAC)
Status: Modern, secure, fast on mobile
```

### Python Example (AES-GCM)

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

# Generate key
key = AESGCM.generate_key(bit_length=256)
aesgcm = AESGCM(key)

# Encrypt
nonce = os.urandom(12)  # 96 bits for GCM
plaintext = b"Secret message"
ciphertext = aesgcm.encrypt(nonce, plaintext, None)

# Decrypt
recovered = aesgcm.decrypt(nonce, ciphertext, None)
assert recovered == plaintext
```

### Go Example (AES-GCM)

```go
package main

import (
    "crypto/aes"
    "crypto/cipher"
    "crypto/rand"
    "io"
)

func encrypt(key, plaintext []byte) ([]byte, error) {
    block, err := aes.NewCipher(key)
    if err != nil {
        return nil, err
    }

    gcm, err := cipher.NewGCM(block)
    if err != nil {
        return nil, err
    }

    nonce := make([]byte, gcm.NonceSize())
    if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
        return nil, err
    }

    // Prepend nonce to ciphertext
    ciphertext := gcm.Seal(nonce, nonce, plaintext, nil)
    return ciphertext, nil
}

func decrypt(key, ciphertext []byte) ([]byte, error) {
    block, err := aes.NewCipher(key)
    if err != nil {
        return nil, err
    }

    gcm, err := cipher.NewGCM(block)
    if err != nil {
        return nil, err
    }

    nonceSize := gcm.NonceSize()
    nonce, ciphertext := ciphertext[:nonceSize], ciphertext[nonceSize:]

    plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
    return plaintext, err
}
```

---

## Asymmetric Encryption

### Overview

**Different keys for encryption and decryption**:
```
Public Key (share freely) → Encrypt
Private Key (keep secret) → Decrypt

Anyone can encrypt with public key
Only holder of private key can decrypt
```

**Characteristics**:
- Slow (1000x slower than symmetric)
- No need to share secret
- Used for key exchange, digital signatures

### Common Algorithms

**RSA**:
```
Key sizes: 2048, 3072, 4096 bits
Use cases: Key exchange, signatures
Status: Widely supported, slower
```

**ECDSA (Elliptic Curve)**:
```
Key sizes: 256, 384, 521 bits
Use cases: Signatures (TLS, Bitcoin)
Status: Modern, faster, smaller keys
```

**Ed25519**:
```
Key size: 256 bits
Use cases: Signatures (SSH, crypto)
Status: Modern, fast, secure
```

### Python Example (RSA)

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

# Generate key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
public_key = private_key.public_key()

# Encrypt with public key
plaintext = b"Secret message"
ciphertext = public_key.encrypt(
    plaintext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)

# Decrypt with private key
recovered = private_key.decrypt(
    ciphertext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)
assert recovered == plaintext
```

### Rust Example (Ed25519 signatures)

```rust
use ed25519_dalek::{Keypair, Signature, Signer, Verifier};
use rand::rngs::OsRng;

fn main() {
    let mut csprng = OsRng{};
    let keypair: Keypair = Keypair::generate(&mut csprng);

    // Sign
    let message = b"Important message";
    let signature: Signature = keypair.sign(message);

    // Verify
    assert!(keypair.public.verify(message, &signature).is_ok());
}
```

---

## Hashing

### Overview

**One-way function**:
```
Input (any size) → [Hash Function] → Fixed-size output

Properties:
- Deterministic (same input → same output)
- Fast to compute
- Infeasible to reverse
- Collision-resistant
```

### Common Algorithms

**SHA-256** (Secure Hash Algorithm):
```
Output: 256 bits (32 bytes)
Use cases: Integrity, signatures, Bitcoin
Status: Industry standard
```

**SHA-3**:
```
Output: 224, 256, 384, 512 bits
Use cases: Same as SHA-256
Status: Modern alternative
```

**BLAKE2**:
```
Output: Configurable
Use cases: General hashing
Status: Faster than SHA-2, secure
```

### Python Examples

```python
import hashlib

# SHA-256
data = b"Data to hash"
hash_digest = hashlib.sha256(data).hexdigest()
print(f"SHA-256: {hash_digest}")

# BLAKE2b (faster)
hash_digest = hashlib.blake2b(data).hexdigest()
print(f"BLAKE2: {hash_digest}")

# File hashing
def hash_file(filename):
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()
```

---

## Password Hashing

### Overview

**Different from general hashing**:
```
Requirements:
- Slow (prevent brute force)
- Salt (prevent rainbow tables)
- Memory-hard (resist GPU attacks)
```

### Algorithms

**bcrypt**:
```python
import bcrypt

# Hash password
password = b"user_password"
salt = bcrypt.gensalt(rounds=12)  # Cost factor
hashed = bcrypt.hashpw(password, salt)

# Verify password
if bcrypt.checkpw(password, hashed):
    print("Password correct")
```

**Argon2** (modern, recommended):
```python
from argon2 import PasswordHasher

ph = PasswordHasher()

# Hash password
hashed = ph.hash("user_password")

# Verify password
try:
    ph.verify(hashed, "user_password")
    print("Password correct")
except:
    print("Password incorrect")
```

**scrypt**:
```python
import hashlib

password = b"user_password"
salt = os.urandom(16)

# Hash with scrypt (memory-hard)
key = hashlib.scrypt(
    password,
    salt=salt,
    n=2**14,  # CPU/memory cost
    r=8,      # Block size
    p=1,      # Parallelization
    dklen=32  # Key length
)
```

---

## Digital Signatures

### Overview

**Authenticate + Integrity**:
```
1. Hash the message
2. Encrypt hash with private key → Signature
3. Anyone can verify with public key

Proves:
- Message came from private key holder
- Message wasn't modified
```

### Python Example

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

# Generate key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
public_key = private_key.public_key()

# Sign message
message = b"Important document"
signature = private_key.sign(
    message,
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH
    ),
    hashes.SHA256()
)

# Verify signature
try:
    public_key.verify(
        signature,
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    print("Signature valid")
except:
    print("Signature invalid")
```

---

## Key Exchange

### Diffie-Hellman

**Agree on shared secret over insecure channel**:
```
Alice                           Bob
private_a                       private_b
    ↓                              ↓
public_a → -------→ public_b ← public_b
    +                              +
public_b                       public_a
    ↓                              ↓
shared_secret               shared_secret
```

**Python Example**:
```python
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives import serialization

# Generate parameters (can be reused)
parameters = dh.generate_parameters(generator=2, key_size=2048)

# Alice generates keypair
alice_private = parameters.generate_private_key()
alice_public = alice_private.public_key()

# Bob generates keypair
bob_private = parameters.generate_private_key()
bob_public = bob_private.public_key()

# Both derive same shared secret
alice_shared = alice_private.exchange(bob_public)
bob_shared = bob_private.exchange(alice_public)

assert alice_shared == bob_shared
```

---

## Message Authentication Codes (MAC)

### HMAC

**Hash-based MAC**:
```python
import hmac
import hashlib

key = b"shared_secret"
message = b"Message to authenticate"

# Create MAC
mac = hmac.new(key, message, hashlib.sha256).digest()

# Verify MAC
def verify_mac(message, mac, key):
    expected_mac = hmac.new(key, message, hashlib.sha256).digest()
    return hmac.compare_digest(mac, expected_mac)  # Constant-time comparison
```

---

## Patterns

### Pattern 1: Hybrid Encryption

**Use asymmetric for key exchange, symmetric for data**:
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
import os

def hybrid_encrypt(public_key, plaintext):
    # Generate random symmetric key
    symmetric_key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(symmetric_key)

    # Encrypt data with symmetric key
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # Encrypt symmetric key with public key
    encrypted_key = public_key.encrypt(
        symmetric_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return {
        'encrypted_key': encrypted_key,
        'nonce': nonce,
        'ciphertext': ciphertext
    }

def hybrid_decrypt(private_key, encrypted_data):
    # Decrypt symmetric key
    symmetric_key = private_key.decrypt(
        encrypted_data['encrypted_key'],
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Decrypt data
    aesgcm = AESGCM(symmetric_key)
    plaintext = aesgcm.decrypt(
        encrypted_data['nonce'],
        encrypted_data['ciphertext'],
        None
    )

    return plaintext
```

---

## Best Practices

### 1. Use Authenticated Encryption

```python
# ✅ Good: AES-GCM (includes authentication)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ❌ Bad: AES-CBC without MAC (vulnerable)
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
```

### 2. Generate Random Keys Properly

```python
# ✅ Good: Cryptographically secure
import secrets
key = secrets.token_bytes(32)

# ❌ Bad: Predictable
import random
key = random.randbytes(32)  # NOT cryptographically secure
```

### 3. Use High-Level APIs

```python
# ✅ Good: Use established libraries
from cryptography.fernet import Fernet

# ❌ Bad: Roll your own crypto
def my_custom_encryption(data):
    return bytes([b ^ 42 for b in data])  # Insecure!
```

---

## Algorithm Selection Guide

| Use Case | Algorithm |
|----------|-----------|
| Bulk encryption | AES-256-GCM |
| Key exchange | ECDH (X25519) |
| Digital signatures | Ed25519 or ECDSA P-256 |
| Password hashing | Argon2id |
| General hashing | SHA-256 or BLAKE2 |
| Message auth | HMAC-SHA256 |

---

## Related Skills

- `cryptography-pki-fundamentals` - Certificates and PKI
- `cryptography-tls-configuration` - TLS implementation
- `cryptography-crypto-best-practices` - Security guidelines
- `security-authentication` - Auth patterns

---

**Last Updated**: 2025-10-27
