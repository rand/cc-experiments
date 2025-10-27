#!/usr/bin/env python3
"""
HashiCorp Vault Transit Secrets Engine Example

Production-ready example of using HashiCorp Vault for encryption as a service
and key management.

Features:
- Transit secrets engine setup
- Key creation and rotation
- Encryption and decryption
- Key versioning
- Re-wrapping (re-encrypt with new key version)
- Dynamic secrets
"""

import hvac
import base64
import json
from typing import Dict, Optional


class VaultKeyManager:
    """HashiCorp Vault key manager"""

    def __init__(self, url: str = 'http://127.0.0.1:8200', token: Optional[str] = None):
        self.client = hvac.Client(url=url, token=token)

        if not self.client.is_authenticated():
            raise RuntimeError("Vault authentication failed")

    def enable_transit(self) -> None:
        """Enable Transit secrets engine"""
        if 'transit/' not in self.client.sys.list_mounted_secrets_engines():
            self.client.sys.enable_secrets_engine(
                backend_type='transit',
                path='transit'
            )
            print("Transit secrets engine enabled")
        else:
            print("Transit secrets engine already enabled")

    def create_encryption_key(self, name: str, key_type: str = 'aes256-gcm96',
                             convergent: bool = False, exportable: bool = False) -> None:
        """Create encryption key"""
        params = {
            'type': key_type,
            'convergent_encryption': convergent,
            'exportable': exportable
        }

        self.client.secrets.transit.create_key(name=name, **params)
        print(f"Created encryption key: {name}")

    def read_key_info(self, name: str) -> Dict:
        """Read key information"""
        response = self.client.secrets.transit.read_key(name=name)
        return response['data']

    def rotate_key(self, name: str) -> None:
        """Rotate encryption key"""
        self.client.secrets.transit.rotate_key(name=name)
        print(f"Rotated key: {name}")

    def encrypt(self, key_name: str, plaintext: bytes,
               context: Optional[str] = None) -> str:
        """Encrypt data"""
        plaintext_b64 = base64.b64encode(plaintext).decode('utf-8')

        params = {'plaintext': plaintext_b64}
        if context:
            params['context'] = base64.b64encode(context.encode()).decode('utf-8')

        response = self.client.secrets.transit.encrypt_data(
            name=key_name,
            **params
        )

        return response['data']['ciphertext']

    def decrypt(self, key_name: str, ciphertext: str,
               context: Optional[str] = None) -> bytes:
        """Decrypt data"""
        params = {'ciphertext': ciphertext}
        if context:
            params['context'] = base64.b64encode(context.encode()).decode('utf-8')

        response = self.client.secrets.transit.decrypt_data(
            name=key_name,
            **params
        )

        plaintext_b64 = response['data']['plaintext']
        return base64.b64decode(plaintext_b64)

    def rewrap(self, key_name: str, ciphertext: str) -> str:
        """Re-encrypt with latest key version"""
        response = self.client.secrets.transit.rewrap_data(
            name=key_name,
            ciphertext=ciphertext
        )

        return response['data']['ciphertext']

    def configure_key_rotation(self, key_name: str, auto_rotate_period: str = '30d') -> None:
        """Configure automatic key rotation"""
        self.client.secrets.transit.update_key_configuration(
            name=key_name,
            auto_rotate_period=auto_rotate_period
        )
        print(f"Configured auto-rotation for {key_name}: {auto_rotate_period}")


def main():
    """Example usage"""
    # Initialize Vault client
    vault = VaultKeyManager(
        url='http://127.0.0.1:8200',
        token='dev-root-token'  # Replace with actual token
    )

    # Enable transit engine
    vault.enable_transit()

    # Create encryption key
    vault.create_encryption_key(
        name='app-encryption-key',
        key_type='aes256-gcm96',
        convergent=False,
        exportable=False
    )

    # Read key info
    key_info = vault.read_key_info('app-encryption-key')
    print(f"\nKey info:")
    print(f"  Type: {key_info['type']}")
    print(f"  Latest version: {key_info['latest_version']}")
    print(f"  Supports encryption: {key_info['supports_encryption']}")
    print(f"  Supports decryption: {key_info['supports_decryption']}")

    # Encrypt data
    plaintext = b"Sensitive data to encrypt"
    context = "user-id:12345"  # Optional additional authenticated data

    ciphertext = vault.encrypt('app-encryption-key', plaintext, context)
    print(f"\nEncrypted: {ciphertext}")

    # Decrypt data
    decrypted = vault.decrypt('app-encryption-key', ciphertext, context)
    assert decrypted == plaintext
    print(f"Decrypted: {decrypted.decode('utf-8')}")

    # Rotate key
    vault.rotate_key('app-encryption-key')

    # Re-wrap ciphertext with new key version
    new_ciphertext = vault.rewrap('app-encryption-key', ciphertext)
    print(f"\nRe-wrapped: {new_ciphertext}")

    # Decrypt with new ciphertext
    decrypted_new = vault.decrypt('app-encryption-key', new_ciphertext, context)
    assert decrypted_new == plaintext
    print(f"Decrypted (after re-wrap): {decrypted_new.decode('utf-8')}")

    # Configure auto-rotation
    vault.configure_key_rotation('app-encryption-key', auto_rotate_period='90d')


if __name__ == '__main__':
    main()
