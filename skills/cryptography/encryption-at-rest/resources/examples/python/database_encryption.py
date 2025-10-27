#!/usr/bin/env python3
"""
Database Field-Level Encryption

Demonstrates application-level encryption for database fields using SQLAlchemy.
Encrypts sensitive columns (SSN, credit cards) before storing in database.

Features:
- Transparent encryption/decryption through SQLAlchemy types
- Field-level encryption for specific columns
- Key versioning for rotation
- Searchable encrypted fields (deterministic encryption)
"""

import base64
import hashlib
import os
from datetime import datetime
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import create_engine, Column, Integer, String, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import TypeDecorator, String as SQLString


Base = declarative_base()


class EncryptionManager:
    """Manages encryption keys and operations"""

    def __init__(self, master_key: bytes, key_version: int = 1):
        """
        Initialize encryption manager.

        Args:
            master_key: 256-bit master key
            key_version: Key version for rotation support
        """
        if len(master_key) != 32:
            raise ValueError("Master key must be 32 bytes")
        self.master_key = master_key
        self.key_version = key_version

    def encrypt(self, plaintext: str, deterministic: bool = False) -> bytes:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt
            deterministic: If True, same plaintext always produces same ciphertext
                          (allows equality searches, but less secure)

        Returns:
            Encrypted bytes (version + nonce + ciphertext)
        """
        plaintext_bytes = plaintext.encode('utf-8')

        if deterministic:
            # Deterministic: derive nonce from plaintext (allows searching)
            # WARNING: Less secure, only use for searchable fields
            nonce = self._derive_nonce(plaintext_bytes)
        else:
            # Random nonce (more secure, but not searchable)
            nonce = os.urandom(12)

        # Encrypt with AES-256-GCM
        aesgcm = AESGCM(self.master_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)

        # Format: version(1) + nonce(12) + ciphertext
        return bytes([self.key_version]) + nonce + ciphertext

    def decrypt(self, encrypted: bytes) -> str:
        """
        Decrypt encrypted bytes.

        Args:
            encrypted: Encrypted bytes from encrypt()

        Returns:
            Decrypted string
        """
        # Parse: version(1) + nonce(12) + ciphertext
        version = encrypted[0]
        nonce = encrypted[1:13]
        ciphertext = encrypted[13:]

        # In production, select key based on version
        if version != self.key_version:
            raise ValueError(f"Unsupported key version: {version}")

        # Decrypt
        aesgcm = AESGCM(self.master_key)
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)

        return plaintext_bytes.decode('utf-8')

    def _derive_nonce(self, plaintext: bytes) -> bytes:
        """Derive deterministic nonce from plaintext (for searchable fields)"""
        # Use PBKDF2 to derive nonce from plaintext + master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=12,  # 96-bit nonce
            salt=self.master_key[:16],
            iterations=100000,
        )
        return kdf.derive(plaintext)


# Global encryption manager (in production, load from secure config)
_encryption_manager = None


def get_encryption_manager() -> EncryptionManager:
    """Get global encryption manager"""
    global _encryption_manager
    if _encryption_manager is None:
        # In production: load from KMS or environment variable
        master_key = os.environ.get('DB_ENCRYPTION_KEY')
        if master_key:
            _encryption_manager = EncryptionManager(base64.b64decode(master_key))
        else:
            # Development: generate random key (NOT for production!)
            print("WARNING: Using random encryption key (development only)")
            _encryption_manager = EncryptionManager(os.urandom(32))
    return _encryption_manager


class EncryptedString(TypeDecorator):
    """SQLAlchemy type for encrypted string columns"""

    impl = LargeBinary
    cache_ok = True

    def __init__(self, deterministic=False, *args, **kwargs):
        """
        Args:
            deterministic: If True, allows equality searches
        """
        self.deterministic = deterministic
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        """Encrypt before storing in database"""
        if value is None:
            return None

        manager = get_encryption_manager()
        return manager.encrypt(value, deterministic=self.deterministic)

    def process_result_value(self, value, dialect):
        """Decrypt when loading from database"""
        if value is None:
            return None

        manager = get_encryption_manager()
        return manager.decrypt(value)


class User(Base):
    """User model with encrypted sensitive fields"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False)  # Not encrypted (searchable)

    # Encrypted fields
    email = Column(EncryptedString(deterministic=True))  # Searchable
    ssn = Column(EncryptedString(deterministic=False))   # Not searchable (more secure)
    credit_card = Column(EncryptedString(deterministic=False))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)


class MedicalRecord(Base):
    """Medical record with encrypted PHI (Protected Health Information)"""
    __tablename__ = 'medical_records'

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, nullable=False)

    # Encrypted PHI
    diagnosis = Column(EncryptedString(deterministic=False))
    medications = Column(EncryptedString(deterministic=False))
    notes = Column(EncryptedString(deterministic=False))

    # Searchable identifiers (deterministic encryption)
    medical_record_number = Column(EncryptedString(deterministic=True))

    created_at = Column(DateTime, default=datetime.utcnow)


def example_basic_encryption():
    """Basic field encryption example"""
    print("=== Basic Field Encryption ===")

    # Create in-memory database
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create user with encrypted fields
    user = User(
        username="john_doe",
        email="john@example.com",
        ssn="123-45-6789",
        credit_card="4532-1234-5678-9010"
    )
    session.add(user)
    session.commit()

    print(f"✓ Created user: {user.username}")
    print(f"  Email (decrypted): {user.email}")
    print(f"  SSN (decrypted): {user.ssn}")

    # Query by encrypted field (only works with deterministic=True)
    found = session.query(User).filter(User.email == "john@example.com").first()
    if found:
        print(f"✓ Found user by encrypted email: {found.username}")

    # Show raw encrypted data in database
    result = session.execute("SELECT email, ssn FROM users").fetchone()
    print(f"\n  Raw email in DB: {base64.b64encode(result[0]).decode()[:50]}...")
    print(f"  Raw SSN in DB: {base64.b64encode(result[1]).decode()[:50]}...")

    session.close()


def example_key_rotation():
    """Demonstrate key rotation for encrypted fields"""
    print("\n=== Key Rotation ===")

    # Create database with old key
    old_key = os.urandom(32)
    global _encryption_manager
    _encryption_manager = EncryptionManager(old_key, key_version=1)

    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Insert data with old key
    user = User(username="alice", email="alice@example.com", ssn="111-22-3333")
    session.add(user)
    session.commit()
    user_id = user.id

    print("✓ Encrypted data with key v1")

    # Rotate to new key
    new_key = os.urandom(32)
    old_manager = _encryption_manager
    new_manager = EncryptionManager(new_key, key_version=2)

    # Re-encrypt all data (in production, do in batches)
    user = session.query(User).get(user_id)

    # Decrypt with old key
    _encryption_manager = old_manager
    email_plaintext = user.email
    ssn_plaintext = user.ssn

    # Re-encrypt with new key
    _encryption_manager = new_manager
    user.email = email_plaintext
    user.ssn = ssn_plaintext
    session.commit()

    print("✓ Re-encrypted data with key v2")

    # Verify decryption works with new key
    user = session.query(User).get(user_id)
    assert user.email == "alice@example.com"
    print("✓ Decryption successful with new key")

    session.close()


def example_hipaa_compliance():
    """HIPAA-compliant medical records encryption"""
    print("\n=== HIPAA-Compliant Medical Records ===")

    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Store encrypted medical record
    record = MedicalRecord(
        patient_id=12345,
        medical_record_number="MR-2025-001",
        diagnosis="Hypertension Stage 2",
        medications="Lisinopril 10mg daily",
        notes="Patient reports headaches. BP: 150/95."
    )
    session.add(record)
    session.commit()

    print("✓ Stored encrypted medical record")

    # Search by medical record number (deterministic encryption)
    found = session.query(MedicalRecord).filter(
        MedicalRecord.medical_record_number == "MR-2025-001"
    ).first()

    if found:
        print(f"✓ Found record by MRN")
        print(f"  Diagnosis: {found.diagnosis}")
        print(f"  Medications: {found.medications}")

    # Show that diagnosis is encrypted in database
    result = session.execute(
        "SELECT diagnosis FROM medical_records"
    ).fetchone()
    print(f"\n  Raw diagnosis in DB (encrypted): {base64.b64encode(result[0]).decode()[:50]}...")

    session.close()


def example_batch_update():
    """Efficient batch encryption/decryption"""
    print("\n=== Batch Operations ===")

    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Bulk insert
    users = [
        User(username=f"user{i}", email=f"user{i}@example.com", ssn=f"SSN-{i:06d}")
        for i in range(100)
    ]
    session.bulk_save_objects(users)
    session.commit()

    print("✓ Bulk inserted 100 encrypted records")

    # Bulk query
    all_users = session.query(User).all()
    print(f"✓ Retrieved and decrypted {len(all_users)} records")

    # Note: Encryption/decryption happens automatically through SQLAlchemy types
    for user in all_users[:3]:
        print(f"  {user.username}: {user.email}")

    session.close()


if __name__ == "__main__":
    # Note: Requires cryptography and sqlalchemy packages
    # Install with: pip install cryptography sqlalchemy

    example_basic_encryption()
    example_key_rotation()
    example_hipaa_compliance()
    example_batch_update()

    print("\n=== All Examples Completed ===")
    print("\nBest Practices:")
    print("  • Use deterministic encryption only for searchable fields")
    print("  • Rotate keys regularly (quarterly recommended)")
    print("  • Store master keys in KMS (AWS KMS, HashiCorp Vault)")
    print("  • Use different keys for different data classification levels")
    print("  • Audit all access to encrypted fields")
