#!/usr/bin/env python3
"""
File Encryption with Envelope Encryption

Demonstrates secure file encryption using envelope encryption pattern:
1. Generate Data Encryption Key (DEK) using KMS
2. Encrypt file with DEK (AES-256-GCM)
3. Store encrypted DEK alongside encrypted file
4. For decryption: decrypt DEK with KMS, then decrypt file

This pattern allows key rotation without re-encrypting all data.
"""

import base64
import json
import os
from pathlib import Path
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class FileEncryption:
    """File encryption using AES-256-GCM with envelope encryption"""

    def __init__(self, kms_master_key: bytes):
        """
        Initialize file encryption.

        Args:
            kms_master_key: Master key from KMS (32 bytes for AES-256)
        """
        if len(kms_master_key) != 32:
            raise ValueError("Master key must be 32 bytes (256 bits)")
        self.master_key = kms_master_key

    def generate_data_key(self) -> Tuple[bytes, bytes]:
        """
        Generate Data Encryption Key (DEK).

        Returns:
            (plaintext_dek, encrypted_dek) tuple
        """
        # Generate random DEK (256 bits)
        plaintext_dek = os.urandom(32)

        # Encrypt DEK with master key (Key Encryption Key)
        encrypted_dek = self._encrypt_key(plaintext_dek)

        return plaintext_dek, encrypted_dek

    def _encrypt_key(self, key: bytes) -> bytes:
        """Encrypt a key with master key using AES-256-GCM"""
        aesgcm = AESGCM(self.master_key)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, key, None)
        # Return nonce + ciphertext
        return nonce + ciphertext

    def _decrypt_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt a key with master key"""
        nonce = encrypted_key[:12]
        ciphertext = encrypted_key[12:]
        aesgcm = AESGCM(self.master_key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_file(self, input_path: Path, output_path: Path) -> dict:
        """
        Encrypt a file using envelope encryption.

        Args:
            input_path: Path to plaintext file
            output_path: Path to write encrypted file

        Returns:
            Metadata dict with encrypted DEK and nonce
        """
        # Generate Data Encryption Key
        plaintext_dek, encrypted_dek = self.generate_data_key()

        # Read plaintext file
        plaintext = input_path.read_bytes()

        # Encrypt file with DEK
        aesgcm = AESGCM(plaintext_dek)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Write encrypted file
        output_path.write_bytes(ciphertext)

        # Return metadata (store separately or as file header)
        metadata = {
            "encrypted_dek": base64.b64encode(encrypted_dek).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "algorithm": "AES-256-GCM",
            "original_size": len(plaintext),
            "encrypted_size": len(ciphertext)
        }

        # Write metadata file
        metadata_path = output_path.with_suffix(output_path.suffix + ".meta")
        metadata_path.write_text(json.dumps(metadata, indent=2))

        return metadata

    def decrypt_file(self, input_path: Path, output_path: Path,
                     metadata: dict = None) -> None:
        """
        Decrypt a file using envelope encryption.

        Args:
            input_path: Path to encrypted file
            output_path: Path to write decrypted file
            metadata: Encryption metadata (or load from .meta file)
        """
        # Load metadata if not provided
        if metadata is None:
            metadata_path = input_path.with_suffix(input_path.suffix + ".meta")
            metadata = json.loads(metadata_path.read_text())

        # Decrypt DEK using master key
        encrypted_dek = base64.b64decode(metadata["encrypted_dek"])
        plaintext_dek = self._decrypt_key(encrypted_dek)

        # Read encrypted file
        ciphertext = input_path.read_bytes()

        # Decrypt file with DEK
        nonce = base64.b64decode(metadata["nonce"])
        aesgcm = AESGCM(plaintext_dek)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        # Write decrypted file
        output_path.write_bytes(plaintext)


def example_basic_encryption():
    """Basic file encryption example"""
    print("=== Basic File Encryption ===")

    # Simulate master key from KMS (in production, get from AWS KMS)
    master_key = os.urandom(32)

    # Initialize encryptor
    encryptor = FileEncryption(master_key)

    # Create test file
    test_file = Path("test_document.txt")
    test_file.write_text("This is sensitive data that needs encryption.")

    # Encrypt file
    encrypted_file = Path("test_document.txt.enc")
    metadata = encryptor.encrypt_file(test_file, encrypted_file)

    print(f"✓ Encrypted {test_file} -> {encrypted_file}")
    print(f"  Original size: {metadata['original_size']} bytes")
    print(f"  Encrypted size: {metadata['encrypted_size']} bytes")
    print(f"  Algorithm: {metadata['algorithm']}")

    # Decrypt file
    decrypted_file = Path("test_document_decrypted.txt")
    encryptor.decrypt_file(encrypted_file, decrypted_file, metadata)

    print(f"✓ Decrypted {encrypted_file} -> {decrypted_file}")

    # Verify
    original = test_file.read_text()
    decrypted = decrypted_file.read_text()
    assert original == decrypted, "Decryption failed"
    print("✓ Verification passed")

    # Cleanup
    test_file.unlink()
    encrypted_file.unlink()
    Path(str(encrypted_file) + ".meta").unlink()
    decrypted_file.unlink()


def example_key_rotation():
    """Demonstrate key rotation without re-encrypting files"""
    print("\n=== Key Rotation Example ===")

    # Old master key
    old_master_key = os.urandom(32)
    old_encryptor = FileEncryption(old_master_key)

    # Encrypt with old key
    test_file = Path("sensitive_data.txt")
    test_file.write_text("Financial data: Account 123456")

    encrypted_file = Path("sensitive_data.txt.enc")
    metadata = old_encryptor.encrypt_file(test_file, encrypted_file)
    print("✓ Encrypted with old key")

    # === Key Rotation ===
    # New master key from KMS
    new_master_key = os.urandom(32)
    new_encryptor = FileEncryption(new_master_key)

    # Re-encrypt only the DEK (not the entire file!)
    old_encrypted_dek = base64.b64decode(metadata["encrypted_dek"])
    plaintext_dek = old_encryptor._decrypt_key(old_encrypted_dek)

    # Encrypt DEK with new master key
    new_encrypted_dek = new_encryptor._encrypt_key(plaintext_dek)

    # Update metadata
    metadata["encrypted_dek"] = base64.b64encode(new_encrypted_dek).decode()

    # Save updated metadata
    metadata_path = Path(str(encrypted_file) + ".meta")
    metadata_path.write_text(json.dumps(metadata, indent=2))

    print("✓ Rotated to new key (only DEK re-encrypted)")

    # Decrypt with new key
    decrypted_file = Path("sensitive_data_decrypted.txt")
    new_encryptor.decrypt_file(encrypted_file, decrypted_file, metadata)

    print("✓ Decrypted with new key")

    # Verify
    assert test_file.read_text() == decrypted_file.read_text()
    print("✓ Key rotation successful")

    # Cleanup
    test_file.unlink()
    encrypted_file.unlink()
    metadata_path.unlink()
    decrypted_file.unlink()


def example_batch_encryption():
    """Encrypt multiple files with same DEK (efficient for directories)"""
    print("\n=== Batch File Encryption ===")

    master_key = os.urandom(32)
    encryptor = FileEncryption(master_key)

    # Generate single DEK for all files
    plaintext_dek, encrypted_dek = encryptor.generate_data_key()

    files = []
    for i in range(5):
        file_path = Path(f"file_{i}.txt")
        file_path.write_text(f"Content of file {i}")
        files.append(file_path)

    # Encrypt all files with same DEK
    aesgcm = AESGCM(plaintext_dek)
    encrypted_files = []

    for file_path in files:
        plaintext = file_path.read_bytes()
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        encrypted_path = file_path.with_suffix(".enc")
        encrypted_path.write_bytes(ciphertext)
        encrypted_files.append((encrypted_path, nonce))

    print(f"✓ Encrypted {len(files)} files with single DEK")

    # Store single metadata for all files
    batch_metadata = {
        "encrypted_dek": base64.b64encode(encrypted_dek).decode(),
        "files": [
            {
                "path": str(path),
                "nonce": base64.b64encode(nonce).decode()
            }
            for path, nonce in encrypted_files
        ]
    }

    metadata_path = Path("batch_metadata.json")
    metadata_path.write_text(json.dumps(batch_metadata, indent=2))

    print("✓ Stored batch metadata")

    # Cleanup
    for f in files:
        f.unlink()
    for enc_f, _ in encrypted_files:
        enc_f.unlink()
    metadata_path.unlink()


if __name__ == "__main__":
    # Note: Requires cryptography package
    # Install with: pip install cryptography

    example_basic_encryption()
    example_key_rotation()
    example_batch_encryption()

    print("\n=== All Examples Completed ===")
