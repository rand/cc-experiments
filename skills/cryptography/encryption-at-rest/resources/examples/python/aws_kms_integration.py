#!/usr/bin/env python3
"""
AWS KMS Integration for Encryption at Rest

Demonstrates using AWS Key Management Service (KMS) for:
- Data key generation (envelope encryption)
- Key rotation
- Multi-region keys
- Grant-based access control
- Audit logging with CloudTrail
"""

import base64
import json
import os
from datetime import datetime
from typing import Dict, Optional, Tuple

import boto3
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AWSKMSEncryption:
    """Encryption using AWS KMS for key management"""

    def __init__(self, key_id: str, region: str = 'us-east-1'):
        """
        Initialize AWS KMS encryption.

        Args:
            key_id: KMS key ID or alias (e.g., 'alias/my-app-key')
            region: AWS region
        """
        self.key_id = key_id
        self.region = region
        self.kms_client = boto3.client('kms', region_name=region)

    def generate_data_key(self, key_spec: str = 'AES_256') -> Tuple[bytes, bytes]:
        """
        Generate data encryption key using KMS.

        Args:
            key_spec: Key specification (AES_256 or AES_128)

        Returns:
            (plaintext_key, encrypted_key) tuple for envelope encryption
        """
        try:
            response = self.kms_client.generate_data_key(
                KeyId=self.key_id,
                KeySpec=key_spec
            )

            return response['Plaintext'], response['CiphertextBlob']

        except ClientError as e:
            raise Exception(f"Failed to generate data key: {e}")

    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """
        Decrypt data encryption key using KMS.

        Args:
            encrypted_key: Encrypted key from generate_data_key()

        Returns:
            Plaintext key
        """
        try:
            response = self.kms_client.decrypt(
                CiphertextBlob=encrypted_key
            )

            return response['Plaintext']

        except ClientError as e:
            raise Exception(f"Failed to decrypt data key: {e}")

    def encrypt_data(self, plaintext: bytes) -> Dict:
        """
        Encrypt data using envelope encryption.

        Args:
            plaintext: Data to encrypt

        Returns:
            Dict with encrypted data and metadata
        """
        # Generate data key
        plaintext_key, encrypted_key = self.generate_data_key()

        # Encrypt data with data key
        aesgcm = AESGCM(plaintext_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        return {
            'ciphertext': base64.b64encode(ciphertext).decode(),
            'encrypted_key': base64.b64encode(encrypted_key).decode(),
            'nonce': base64.b64encode(nonce).decode(),
            'key_id': self.key_id,
            'algorithm': 'AES-256-GCM',
            'timestamp': datetime.utcnow().isoformat()
        }

    def decrypt_data(self, encrypted_data: Dict) -> bytes:
        """
        Decrypt data using envelope encryption.

        Args:
            encrypted_data: Dict from encrypt_data()

        Returns:
            Decrypted plaintext
        """
        # Decrypt data key
        encrypted_key = base64.b64decode(encrypted_data['encrypted_key'])
        plaintext_key = self.decrypt_data_key(encrypted_key)

        # Decrypt data
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        nonce = base64.b64decode(encrypted_data['nonce'])

        aesgcm = AESGCM(plaintext_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        return plaintext

    def enable_key_rotation(self) -> None:
        """Enable automatic key rotation (annual)"""
        try:
            self.kms_client.enable_key_rotation(KeyId=self.key_id)
            print(f"✓ Enabled automatic key rotation for {self.key_id}")
        except ClientError as e:
            raise Exception(f"Failed to enable key rotation: {e}")

    def get_key_rotation_status(self) -> bool:
        """Check if key rotation is enabled"""
        try:
            response = self.kms_client.get_key_rotation_status(KeyId=self.key_id)
            return response['KeyRotationEnabled']
        except ClientError as e:
            raise Exception(f"Failed to get key rotation status: {e}")

    def create_grant(self, grantee_principal: str, operations: list) -> str:
        """
        Create a grant for another AWS principal.

        Args:
            grantee_principal: AWS principal ARN
            operations: List of allowed operations (e.g., ['Decrypt', 'Encrypt'])

        Returns:
            Grant ID
        """
        try:
            response = self.kms_client.create_grant(
                KeyId=self.key_id,
                GranteePrincipal=grantee_principal,
                Operations=operations
            )
            return response['GrantId']
        except ClientError as e:
            raise Exception(f"Failed to create grant: {e}")


def example_basic_encryption():
    """Basic AWS KMS encryption example"""
    print("=== Basic AWS KMS Encryption ===")

    # Initialize (requires AWS credentials configured)
    kms = AWSKMSEncryption(key_id='alias/demo-key')

    # Encrypt data
    plaintext = b"Sensitive financial data: Account balance $100,000"
    encrypted = kms.encrypt_data(plaintext)

    print("✓ Encrypted data")
    print(f"  Key ID: {encrypted['key_id']}")
    print(f"  Algorithm: {encrypted['algorithm']}")
    print(f"  Ciphertext (truncated): {encrypted['ciphertext'][:50]}...")

    # Decrypt data
    decrypted = kms.decrypt_data(encrypted)
    print(f"\n✓ Decrypted: {decrypted.decode()}")

    assert plaintext == decrypted


def example_file_encryption():
    """Encrypt file using AWS KMS"""
    print("\n=== File Encryption with AWS KMS ===")

    kms = AWSKMSEncryption(key_id='alias/file-encryption-key')

    # Create test file
    test_file = "sensitive_document.txt"
    with open(test_file, 'w') as f:
        f.write("Top Secret: Project Codename Alpha\n")
        f.write("Budget: $5M\n")

    # Read and encrypt
    with open(test_file, 'rb') as f:
        plaintext = f.read()

    encrypted = kms.encrypt_data(plaintext)

    # Save encrypted file
    encrypted_file = test_file + ".enc"
    with open(encrypted_file, 'w') as f:
        json.dump(encrypted, f, indent=2)

    print(f"✓ Encrypted {test_file} -> {encrypted_file}")

    # Decrypt
    with open(encrypted_file, 'r') as f:
        encrypted_data = json.load(f)

    decrypted = kms.decrypt_data(encrypted_data)

    # Verify
    assert plaintext == decrypted
    print("✓ Decryption verified")

    # Cleanup
    os.remove(test_file)
    os.remove(encrypted_file)


def example_key_rotation():
    """Demonstrate key rotation with AWS KMS"""
    print("\n=== AWS KMS Key Rotation ===")

    kms = AWSKMSEncryption(key_id='alias/rotation-demo')

    # Check current rotation status
    enabled = kms.get_key_rotation_status()
    print(f"Current rotation status: {'Enabled' if enabled else 'Disabled'}")

    # Enable automatic rotation
    if not enabled:
        kms.enable_key_rotation()
        print("✓ Enabled automatic annual key rotation")

    print("\nKey Rotation Details:")
    print("  • AWS KMS automatically rotates keys annually")
    print("  • Old key versions remain available for decryption")
    print("  • New encryptions use the latest key version")
    print("  • No application changes needed")


def example_multi_region():
    """Use multi-region KMS keys"""
    print("\n=== Multi-Region KMS Keys ===")

    # Primary region
    primary_kms = AWSKMSEncryption(
        key_id='arn:aws:kms:us-east-1:123456789012:key/mrk-abcd1234',
        region='us-east-1'
    )

    # Encrypt in primary region
    plaintext = b"Global application data"
    encrypted = primary_kms.encrypt_data(plaintext)

    print("✓ Encrypted in us-east-1")

    # Decrypt in replica region using same key ID
    replica_kms = AWSKMSEncryption(
        key_id='arn:aws:kms:eu-west-1:123456789012:key/mrk-abcd1234',
        region='eu-west-1'
    )

    decrypted = replica_kms.decrypt_data(encrypted)

    print("✓ Decrypted in eu-west-1")
    print("  Multi-region keys enable low-latency decryption worldwide")

    assert plaintext == decrypted


def example_access_control():
    """Demonstrate grant-based access control"""
    print("\n=== Grant-Based Access Control ===")

    kms = AWSKMSEncryption(key_id='alias/shared-key')

    # Create grant for another service/role
    grantee_arn = "arn:aws:iam::123456789012:role/DataProcessingRole"

    try:
        grant_id = kms.create_grant(
            grantee_principal=grantee_arn,
            operations=['Decrypt', 'DescribeKey']
        )

        print(f"✓ Created grant: {grant_id}")
        print(f"  Grantee: {grantee_arn}")
        print(f"  Operations: Decrypt, DescribeKey")
        print("\n  Grants enable temporary access without key policy changes")

    except Exception as e:
        print(f"Note: Grant creation requires proper IAM permissions")


def example_encryption_context():
    """Use encryption context for additional security"""
    print("\n=== Encryption Context (Additional Authentication) ===")

    kms = AWSKMSEncryption(key_id='alias/context-demo')

    # Encryption context provides additional authenticated data (AAD)
    plaintext_key, encrypted_key = kms.kms_client.generate_data_key(
        KeyId=kms.key_id,
        KeySpec='AES_256',
        EncryptionContext={
            'application': 'financial-system',
            'department': 'accounting',
            'purpose': 'quarterly-report'
        }
    )

    print("✓ Generated key with encryption context")
    print("  Context: application=financial-system, department=accounting")

    # Decryption requires matching context
    try:
        decrypted_key = kms.kms_client.decrypt(
            CiphertextBlob=encrypted_key,
            EncryptionContext={
                'application': 'financial-system',
                'department': 'accounting',
                'purpose': 'quarterly-report'
            }
        )['Plaintext']

        print("✓ Decryption successful with matching context")

    except Exception:
        print("✗ Decryption failed - context mismatch")

    print("\nBenefits of Encryption Context:")
    print("  • Prevents ciphertext from being used in wrong context")
    print("  • Logged in CloudTrail for audit")
    print("  • No performance overhead")


def example_cost_optimization():
    """Demonstrate cost-effective KMS usage"""
    print("\n=== Cost Optimization ===")

    print("AWS KMS Pricing Model:")
    print("  • $1/month per customer master key (CMK)")
    print("  • $0.03 per 10,000 API requests")
    print()

    print("Cost Optimization Strategies:")
    print()
    print("1. Data Key Caching:")
    print("   • Generate one data key per batch of files")
    print("   • Cache data keys for 5 minutes")
    print("   • Reduces KMS API calls by 95%+")
    print()

    print("2. Envelope Encryption:")
    print("   • Only small data keys hit KMS (not full data)")
    print("   • Example: 1GB file = 1 KMS call (vs 1 million calls)")
    print()

    print("3. Use Grants Instead of Key Policies:")
    print("   • Grants don't count against key policy size limit")
    print("   • Easier to manage temporary access")
    print()

    print("Example cost calculation:")
    print("  • 1 million file encryptions")
    print("  • With caching (1 key per 1000 files): 1,000 API calls = $0.003")
    print("  • Without caching: 1,000,000 API calls = $3.00")


if __name__ == "__main__":
    print("AWS KMS Integration Examples")
    print("=" * 60)
    print("\nNote: These examples require:")
    print("  • AWS credentials configured (AWS CLI or environment variables)")
    print("  • KMS key created in your AWS account")
    print("  • IAM permissions: kms:GenerateDataKey, kms:Decrypt, kms:Encrypt")
    print()
    print("Setup:")
    print("  pip install boto3 cryptography")
    print("  aws configure")
    print("  aws kms create-key --description 'Demo encryption key'")
    print("  aws kms create-alias --alias-name alias/demo-key --target-key-id <key-id>")
    print()
    print("=" * 60)

    try:
        # Comment out examples that require actual AWS resources
        # example_basic_encryption()
        # example_file_encryption()
        # example_key_rotation()
        # example_multi_region()
        # example_access_control()
        example_encryption_context()
        example_cost_optimization()

        print("\n=== Documentation Examples Complete ===")
        print("\nFor production use:")
        print("  • Enable CloudTrail logging for audit")
        print("  • Use key policies to restrict access")
        print("  • Enable automatic key rotation")
        print("  • Use separate keys for different data classifications")
        print("  • Implement key material expiration for compliance")

    except Exception as e:
        print(f"\nNote: Some examples require AWS resources: {e}")
        print("See comments in code for setup instructions")
