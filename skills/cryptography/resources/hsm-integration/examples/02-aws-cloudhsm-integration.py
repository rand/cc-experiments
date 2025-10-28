#!/usr/bin/env python3
"""
AWS CloudHSM Integration Example

Demonstrates integration with AWS CloudHSM using PKCS#11 interface.
Includes key generation, signing, and encryption operations.
"""

import os
import sys
from typing import Optional

try:
    import PyKCS11
    from PyKCS11 import PyKCS11Error
except ImportError:
    print("Error: PyKCS11 not available. Install with: pip install PyKCS11", file=sys.stderr)
    sys.exit(1)


class CloudHSMClient:
    """AWS CloudHSM client wrapper."""

    # CloudHSM PKCS#11 library path
    LIBRARY_PATH = "/opt/cloudhsm/lib/libcloudhsm_pkcs11.so"

    def __init__(self, pin: str, slot: int = 0):
        """Initialize CloudHSM client."""
        self.pin = pin
        self.slot = slot
        self.pkcs11 = None
        self.session = None

    def connect(self):
        """Connect to CloudHSM."""
        print("Connecting to AWS CloudHSM...")

        # Check if library exists
        if not os.path.exists(self.LIBRARY_PATH):
            raise FileNotFoundError(
                f"CloudHSM library not found: {self.LIBRARY_PATH}\n"
                "Install CloudHSM client: https://docs.aws.amazon.com/cloudhsm/latest/userguide/install-and-configure-client-linux.html"
            )

        # Load PKCS#11 library
        self.pkcs11 = PyKCS11.PyKCS11Lib()
        self.pkcs11.load(self.LIBRARY_PATH)

        # Get library info
        info = self.pkcs11.getInfo()
        print(f"  Library: {info.manufacturerID} v{info.libraryVersion}")

        # Get slot info
        slots = self.pkcs11.getSlotList(tokenPresent=True)
        if not slots:
            raise Exception("No slots with tokens found")

        print(f"  Available slots: {len(slots)}")

        # Open session
        self.session = self.pkcs11.openSession(
            self.slot,
            PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION
        )

        # Login
        self.session.login(self.pin)
        print("  ✓ Connected and logged in")

    def disconnect(self):
        """Disconnect from CloudHSM."""
        if self.session:
            try:
                self.session.logout()
                self.session.closeSession()
                print("  ✓ Disconnected")
            except:
                pass

    def generate_rsa_keypair(self, label: str, modulus_bits: int = 2048):
        """Generate RSA key pair."""
        print(f"\nGenerating RSA-{modulus_bits} key pair: {label}...")

        public_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
            (PyKCS11.CKA_TOKEN, True),
            (PyKCS11.CKA_ENCRYPT, True),
            (PyKCS11.CKA_VERIFY, True),
            (PyKCS11.CKA_WRAP, True),
            (PyKCS11.CKA_MODULUS_BITS, modulus_bits),
            (PyKCS11.CKA_PUBLIC_EXPONENT, (0x01, 0x00, 0x01)),
            (PyKCS11.CKA_LABEL, f"{label} (Public)"),
        ]

        private_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
            (PyKCS11.CKA_TOKEN, True),
            (PyKCS11.CKA_PRIVATE, True),
            (PyKCS11.CKA_SENSITIVE, True),
            (PyKCS11.CKA_EXTRACTABLE, False),
            (PyKCS11.CKA_DECRYPT, True),
            (PyKCS11.CKA_SIGN, True),
            (PyKCS11.CKA_UNWRAP, True),
            (PyKCS11.CKA_LABEL, f"{label} (Private)"),
        ]

        (public_key, private_key) = self.session.generateKeyPair(
            public_template,
            private_template,
            mecha=PyKCS11.MechanismRSAPKCSKeyPairGen
        )

        print(f"  ✓ Generated key pair")
        print(f"    Public key:  {public_key}")
        print(f"    Private key: {private_key}")

        return (public_key, private_key)

    def sign_data(self, private_key: int, data: bytes) -> bytes:
        """Sign data with private key."""
        print(f"\nSigning {len(data)} bytes...")

        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)
        signature = self.session.sign(private_key, data, mechanism)

        print(f"  ✓ Generated signature ({len(signature)} bytes)")
        return bytes(signature)

    def verify_signature(self, public_key: int, data: bytes, signature: bytes) -> bool:
        """Verify signature with public key."""
        print(f"\nVerifying signature...")

        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)

        try:
            self.session.verify(public_key, data, signature, mechanism)
            print("  ✓ Signature valid")
            return True
        except PyKCS11Error:
            print("  ✗ Signature invalid")
            return False

    def encrypt_data(self, public_key: int, data: bytes) -> bytes:
        """Encrypt data with public key."""
        print(f"\nEncrypting {len(data)} bytes...")

        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_RSA_PKCS, None)
        ciphertext = self.session.encrypt(public_key, data, mechanism)

        print(f"  ✓ Encrypted ({len(ciphertext)} bytes)")
        return bytes(ciphertext)

    def decrypt_data(self, private_key: int, ciphertext: bytes) -> bytes:
        """Decrypt data with private key."""
        print(f"\nDecrypting {len(ciphertext)} bytes...")

        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_RSA_PKCS, None)
        plaintext = self.session.decrypt(private_key, ciphertext, mechanism)

        print(f"  ✓ Decrypted ({len(plaintext)} bytes)")
        return bytes(plaintext)

    def list_keys(self):
        """List keys in CloudHSM."""
        print("\nListing keys in CloudHSM...")

        # Find private keys
        private_keys = self.session.findObjects([
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY)
        ])

        print(f"\nPrivate keys ({len(private_keys)}):")
        for key_handle in private_keys:
            try:
                attrs = self.session.getAttributeValue(key_handle, [PyKCS11.CKA_LABEL])
                label = ''.join(chr(c) for c in attrs[0] if c != 0)
                print(f"  - {label} (handle: {key_handle})")
            except:
                print(f"  - Unknown (handle: {key_handle})")

        # Find public keys
        public_keys = self.session.findObjects([
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY)
        ])

        print(f"\nPublic keys ({len(public_keys)}):")
        for key_handle in public_keys:
            try:
                attrs = self.session.getAttributeValue(key_handle, [PyKCS11.CKA_LABEL])
                label = ''.join(chr(c) for c in attrs[0] if c != 0)
                print(f"  - {label} (handle: {key_handle})")
            except:
                print(f"  - Unknown (handle: {key_handle})")

    def delete_key(self, key_handle: int):
        """Delete key from CloudHSM."""
        print(f"\nDeleting key {key_handle}...")
        self.session.destroyObject(key_handle)
        print("  ✓ Key deleted")


def main():
    """Main function demonstrating CloudHSM integration."""
    print("AWS CloudHSM Integration Example")
    print("=" * 50)

    # Configuration
    # In production, use AWS Secrets Manager or environment variables
    CU_USER = os.environ.get("CLOUDHSM_USER", "user1")
    CU_PASSWORD = os.environ.get("CLOUDHSM_PASSWORD")

    if not CU_PASSWORD:
        print("\nError: CLOUDHSM_PASSWORD environment variable not set", file=sys.stderr)
        print("Set it with: export CLOUDHSM_PASSWORD='your-password'", file=sys.stderr)
        sys.exit(1)

    # PIN format: <username>:<password>
    pin = f"{CU_USER}:{CU_PASSWORD}"

    try:
        # Create client
        client = CloudHSMClient(pin=pin)

        # Connect
        client.connect()

        # List existing keys
        client.list_keys()

        # Generate key pair
        print("\n" + "=" * 50)
        print("Key Generation")
        print("=" * 50)

        public_key, private_key = client.generate_rsa_keypair(
            label="Demo CloudHSM Key",
            modulus_bits=2048
        )

        # Test signing
        print("\n" + "=" * 50)
        print("Digital Signature")
        print("=" * 50)

        test_data = b"Hello, AWS CloudHSM! This is a test message."
        signature = client.sign_data(private_key, test_data)

        # Verify signature
        is_valid = client.verify_signature(public_key, test_data, signature)

        # Test encryption (note: RSA can only encrypt small amounts of data)
        print("\n" + "=" * 50)
        print("Encryption/Decryption")
        print("=" * 50)

        small_data = b"Secret message"
        ciphertext = client.encrypt_data(public_key, small_data)
        decrypted = client.decrypt_data(private_key, ciphertext)

        if decrypted == small_data:
            print("  ✓ Decryption successful")
        else:
            print("  ✗ Decryption failed")

        # Cleanup
        print("\n" + "=" * 50)
        print("Cleanup")
        print("=" * 50)

        response = input("\nDelete generated keys? (y/N): ")
        if response.lower() == 'y':
            client.delete_key(public_key)
            client.delete_key(private_key)

        # Disconnect
        print("\nDisconnecting...")
        client.disconnect()

        print("\n" + "=" * 50)
        print("Example completed successfully")
        print("=" * 50)

    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        print("\nTo install CloudHSM client:", file=sys.stderr)
        print("1. Download from AWS: https://docs.aws.amazon.com/cloudhsm/latest/userguide/install-and-configure-client-linux.html", file=sys.stderr)
        print("2. Install: sudo yum install -y ./cloudhsm-client-*.rpm", file=sys.stderr)
        print("3. Configure: sudo /opt/cloudhsm/bin/configure -a <cluster-ip>", file=sys.stderr)
        sys.exit(1)
    except PyKCS11Error as e:
        print(f"\nPKCS#11 Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
