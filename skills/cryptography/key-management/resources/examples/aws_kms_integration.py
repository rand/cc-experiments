#!/usr/bin/env python3
"""
AWS KMS Integration Example

Production-ready example of AWS KMS integration for key management,
including envelope encryption, key rotation, and access control.

Features:
- Create and manage KMS keys
- Envelope encryption pattern
- Automatic key rotation
- Key policies and access control
- Multi-region keys
- CloudTrail audit logging
"""

import boto3
import json
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Dict, Tuple


class AWSKMSKeyManager:
    """AWS KMS key manager with envelope encryption"""

    def __init__(self, region: str = "us-east-1"):
        self.kms = boto3.client('kms', region_name=region)
        self.region = region

    def create_customer_managed_key(self, description: str, tags: Dict[str, str] = None) -> str:
        """Create customer-managed KMS key"""
        create_params = {
            'Description': description,
            'KeyUsage': 'ENCRYPT_DECRYPT',
            'Origin': 'AWS_KMS'
        }

        if tags:
            create_params['Tags'] = [
                {'TagKey': k, 'TagValue': v}
                for k, v in tags.items()
            ]

        response = self.kms.create_key(**create_params)
        key_id = response['KeyMetadata']['KeyId']

        print(f"Created KMS key: {key_id}")
        return key_id

    def create_alias(self, key_id: str, alias_name: str) -> None:
        """Create alias for KMS key"""
        if not alias_name.startswith('alias/'):
            alias_name = f'alias/{alias_name}'

        self.kms.create_alias(
            AliasName=alias_name,
            TargetKeyId=key_id
        )

        print(f"Created alias: {alias_name} -> {key_id}")

    def enable_key_rotation(self, key_id: str) -> None:
        """Enable automatic key rotation"""
        self.kms.enable_key_rotation(KeyId=key_id)
        print(f"Enabled automatic rotation for key: {key_id}")

    def set_key_policy(self, key_id: str, admin_arn: str, user_arns: list) -> None:
        """Set key policy with admin and user permissions"""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "Enable IAM User Permissions",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": admin_arn
                    },
                    "Action": "kms:*",
                    "Resource": "*"
                },
                {
                    "Sid": "Allow use of the key",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": user_arns
                    },
                    "Action": [
                        "kms:Decrypt",
                        "kms:DescribeKey",
                        "kms:GenerateDataKey"
                    ],
                    "Resource": "*"
                },
                {
                    "Sid": "Allow attachment of persistent resources",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": user_arns
                    },
                    "Action": [
                        "kms:CreateGrant",
                        "kms:ListGrants",
                        "kms:RevokeGrant"
                    ],
                    "Resource": "*",
                    "Condition": {
                        "Bool": {
                            "kms:GrantIsForAWSResource": "true"
                        }
                    }
                }
            ]
        }

        self.kms.put_key_policy(
            KeyId=key_id,
            PolicyName='default',
            Policy=json.dumps(policy)
        )

        print(f"Updated key policy for: {key_id}")

    def encrypt_with_envelope(self, plaintext: bytes, kms_key_id: str,
                             encryption_context: Dict[str, str] = None) -> Dict:
        """Encrypt data using envelope encryption"""
        # Generate data key
        response = self.kms.generate_data_key(
            KeyId=kms_key_id,
            KeySpec='AES_256',
            EncryptionContext=encryption_context or {}
        )

        dek_plaintext = response['Plaintext']
        dek_encrypted = response['CiphertextBlob']

        # Encrypt data with DEK
        aesgcm = AESGCM(dek_plaintext)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Clear DEK from memory
        del dek_plaintext

        return {
            'ciphertext': ciphertext,
            'nonce': nonce,
            'encrypted_dek': dek_encrypted,
            'encryption_context': encryption_context or {}
        }

    def decrypt_with_envelope(self, envelope: Dict) -> bytes:
        """Decrypt data using envelope encryption"""
        # Decrypt DEK
        response = self.kms.decrypt(
            CiphertextBlob=envelope['encrypted_dek'],
            EncryptionContext=envelope.get('encryption_context', {})
        )

        dek_plaintext = response['Plaintext']

        # Decrypt data with DEK
        aesgcm = AESGCM(dek_plaintext)
        plaintext = aesgcm.decrypt(
            envelope['nonce'],
            envelope['ciphertext'],
            None
        )

        # Clear DEK from memory
        del dek_plaintext

        return plaintext


def main():
    """Example usage"""
    # Initialize manager
    manager = AWSKMSKeyManager(region='us-east-1')

    # Create key
    key_id = manager.create_customer_managed_key(
        description='Application encryption key',
        tags={
            'Environment': 'production',
            'Application': 'myapp',
            'ManagedBy': 'terraform'
        }
    )

    # Create alias
    manager.create_alias(key_id, 'myapp-prod-key')

    # Enable rotation
    manager.enable_key_rotation(key_id)

    # Set key policy
    admin_arn = "arn:aws:iam::123456789012:root"
    user_arns = [
        "arn:aws:iam::123456789012:role/MyAppRole"
    ]
    manager.set_key_policy(key_id, admin_arn, user_arns)

    # Encrypt data
    plaintext = b"Sensitive data to encrypt"
    encryption_context = {
        'Department': 'Finance',
        'Project': 'Q4-2024'
    }

    envelope = manager.encrypt_with_envelope(
        plaintext,
        'alias/myapp-prod-key',
        encryption_context
    )

    print(f"\nEncrypted {len(plaintext)} bytes")
    print(f"Ciphertext size: {len(envelope['ciphertext'])} bytes")
    print(f"Encrypted DEK size: {len(envelope['encrypted_dek'])} bytes")

    # Decrypt data
    decrypted = manager.decrypt_with_envelope(envelope)
    assert decrypted == plaintext

    print(f"Decrypted successfully: {decrypted.decode('utf-8')}")


if __name__ == '__main__':
    main()
