#!/usr/bin/env python3
"""
Code Signing with HSM Example

Demonstrates using HSM for code signing operations.
Protects code signing keys in tamper-resistant hardware.
"""

import hashlib
import sys
from pathlib import Path

try:
    import PyKCS11
    from PyKCS11 import PyKCS11Error
except ImportError:
    print("Error: PyKCS11 not available. Install with: pip install PyKCS11", file=sys.stderr)
    sys.exit(1)


class CodeSigner:
    """HSM-based code signer."""

    def __init__(self, library_path: str, slot: int, pin: str):
        """Initialize code signer."""
        self.library_path = library_path
        self.slot = slot
        self.pin = pin
        self.session = None

    def connect(self):
        """Connect to HSM."""
        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(self.library_path)

        self.session = pkcs11.openSession(
            self.slot,
            PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION
        )
        self.session.login(self.pin)

    def generate_signing_key(self, label: str) -> tuple:
        """Generate code signing key pair."""
        print(f"Generating code signing key: {label}...")

        public_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
            (PyKCS11.CKA_TOKEN, True),
            (PyKCS11.CKA_VERIFY, True),
            (PyKCS11.CKA_MODULUS_BITS, 3072),
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
            (PyKCS11.CKA_SIGN, True),
            (PyKCS11.CKA_LABEL, f"{label} (Private)"),
        ]

        keys = self.session.generateKeyPair(
            public_template,
            private_template,
            mecha=PyKCS11.MechanismRSAPKCSKeyPairGen
        )

        print(f"  ✓ Key generated")
        return keys

    def sign_file(self, file_path: str, private_key: int) -> bytes:
        """Sign file with HSM key."""
        print(f"\nSigning file: {file_path}")

        # Read file
        with open(file_path, 'rb') as f:
            data = f.read()

        print(f"  File size: {len(data)} bytes")

        # Calculate hash
        file_hash = hashlib.sha256(data).digest()
        print(f"  SHA-256: {file_hash.hex()}")

        # Sign with HSM
        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)
        signature = self.session.sign(private_key, data, mechanism)

        print(f"  ✓ Signature generated ({len(signature)} bytes)")
        return bytes(signature)

    def verify_signature(self, file_path: str, signature: bytes, public_key: int) -> bool:
        """Verify file signature."""
        print(f"\nVerifying signature for: {file_path}")

        with open(file_path, 'rb') as f:
            data = f.read()

        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)

        try:
            self.session.verify(public_key, data, signature, mechanism)
            print("  ✓ Signature valid")
            return True
        except PyKCS11Error:
            print("  ✗ Signature invalid")
            return False


def main():
    """Main function."""
    print("Code Signing with HSM Example")
    print("=" * 50)

    # Configuration
    LIBRARY_PATH = "/usr/lib/softhsm/libsofthsm2.so"
    SLOT = 0
    PIN = "1234"

    try:
        # Create test file
        test_file = "/tmp/test-application.bin"
        with open(test_file, 'wb') as f:
            f.write(b"Application binary data..." * 100)
        print(f"\nCreated test file: {test_file}")

        # Initialize signer
        signer = CodeSigner(LIBRARY_PATH, SLOT, PIN)
        signer.connect()

        # Generate signing key
        print("\n" + "=" * 50)
        print("Key Generation")
        print("=" * 50)

        public_key, private_key = signer.generate_signing_key("Code Signing Key")

        # Sign file
        print("\n" + "=" * 50)
        print("Signing")
        print("=" * 50)

        signature = signer.sign_file(test_file, private_key)

        # Save signature
        sig_file = test_file + ".sig"
        with open(sig_file, 'wb') as f:
            f.write(signature)
        print(f"\n  ✓ Signature saved to {sig_file}")

        # Verify signature
        print("\n" + "=" * 50)
        print("Verification")
        print("=" * 50)

        is_valid = signer.verify_signature(test_file, signature, public_key)

        # Test with modified file
        print("\nTesting with modified file...")
        with open(test_file, 'ab') as f:
            f.write(b"MODIFIED")

        is_valid_modified = signer.verify_signature(test_file, signature, public_key)

        # Cleanup
        print("\n" + "=" * 50)
        print("Cleanup")
        print("=" * 50)

        signer.session.destroyObject(public_key)
        signer.session.destroyObject(private_key)
        Path(test_file).unlink()
        Path(sig_file).unlink()
        print("  ✓ Cleaned up")

        print("\n" + "=" * 50)
        print("Example completed successfully")
        print("=" * 50)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
