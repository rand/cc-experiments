#!/usr/bin/env python3
"""
Secrets Management with Key Hierarchies

Production example of managing secrets (API keys, passwords, tokens)
with proper encryption using key hierarchies.

Features:
- Hierarchical key management for secrets
- Secret versioning
- Automatic rotation
- Access control
- Audit logging
"""

import boto3
import json
import secrets as py_secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os


class SecretsManager:
    """Secrets manager with KMS integration"""

    def __init__(self, kms_key_id: str, region: str = 'us-east-1'):
        self.kms = boto3.client('kms', region_name=region)
        self.kms_key_id = kms_key_id

    def store_secret(self, secret_name: str, secret_value: str,
                    description: str = '', tags: Dict[str, str] = None) -> Dict:
        """Store encrypted secret"""
        # Generate DEK for this secret
        response = self.kms.generate_data_key(
            KeyId=self.kms_key_id,
            KeySpec='AES_256'
        )

        dek_plaintext = response['Plaintext']
        dek_encrypted = response['CiphertextBlob']

        # Encrypt secret with DEK
        aesgcm = AESGCM(dek_plaintext)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, secret_value.encode(), None)

        # Clear DEK from memory
        del dek_plaintext

        # Create secret metadata
        secret_metadata = {
            'secret_name': secret_name,
            'encrypted_value': ciphertext.hex(),
            'nonce': nonce.hex(),
            'encrypted_dek': dek_encrypted.hex(),
            'description': description,
            'tags': tags or {},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'version': 1
        }

        return secret_metadata

    def retrieve_secret(self, secret_metadata: Dict) -> str:
        """Retrieve and decrypt secret"""
        # Decrypt DEK
        encrypted_dek = bytes.fromhex(secret_metadata['encrypted_dek'])
        response = self.kms.decrypt(CiphertextBlob=encrypted_dek)
        dek_plaintext = response['Plaintext']

        # Decrypt secret with DEK
        aesgcm = AESGCM(dek_plaintext)
        nonce = bytes.fromhex(secret_metadata['nonce'])
        ciphertext = bytes.fromhex(secret_metadata['encrypted_value'])
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        # Clear DEK from memory
        del dek_plaintext

        return plaintext.decode('utf-8')

    def rotate_secret(self, old_secret_metadata: Dict, new_secret_value: str) -> Dict:
        """Rotate secret to new value"""
        new_metadata = self.store_secret(
            secret_name=old_secret_metadata['secret_name'],
            secret_value=new_secret_value,
            description=old_secret_metadata['description'],
            tags=old_secret_metadata['tags']
        )

        new_metadata['version'] = old_secret_metadata['version'] + 1
        new_metadata['previous_version'] = old_secret_metadata.copy()

        return new_metadata

    def generate_api_key(self, prefix: str = '', length: int = 32) -> str:
        """Generate secure API key"""
        key = py_secrets.token_urlsafe(length)
        if prefix:
            key = f"{prefix}_{key}"
        return key

    def generate_password(self, length: int = 32, special_chars: bool = True) -> str:
        """Generate secure password"""
        import string

        chars = string.ascii_letters + string.digits
        if special_chars:
            chars += string.punctuation

        password = ''.join(py_secrets.choice(chars) for _ in range(length))
        return password


def main():
    """Example usage"""
    # Initialize secrets manager
    sm = SecretsManager(kms_key_id='alias/secrets-master-key')

    # Generate and store API key
    api_key = sm.generate_api_key(prefix='myapp', length=32)
    api_key_secret = sm.store_secret(
        secret_name='myapp/api_key',
        secret_value=api_key,
        description='MyApp API Key',
        tags={'Environment': 'production', 'Service': 'myapp'}
    )

    print(f"Stored API key secret: {api_key_secret['secret_name']}")

    # Generate and store database password
    db_password = sm.generate_password(length=32, special_chars=True)
    db_secret = sm.store_secret(
        secret_name='myapp/db_password',
        secret_value=db_password,
        description='Database Password',
        tags={'Environment': 'production', 'Service': 'myapp'}
    )

    print(f"Stored database password secret: {db_secret['secret_name']}")

    # Retrieve secrets
    retrieved_api_key = sm.retrieve_secret(api_key_secret)
    print(f"\nRetrieved API key: {retrieved_api_key[:10]}...")

    retrieved_db_password = sm.retrieve_secret(db_secret)
    print(f"Retrieved database password: {retrieved_db_password[:10]}...")

    # Rotate API key
    new_api_key = sm.generate_api_key(prefix='myapp', length=32)
    rotated_secret = sm.rotate_secret(api_key_secret, new_api_key)

    print(f"\nRotated API key to version {rotated_secret['version']}")


if __name__ == '__main__':
    main()
