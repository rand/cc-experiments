#!/usr/bin/env python3
"""
YubiHSM Setup and Usage Example

Demonstrates YubiHSM 2 setup, key generation, and cryptographic operations.
"""

import os
import sys

try:
    import PyKCS11
    from PyKCS11 import PyKCS11Error
except ImportError:
    print("Error: PyKCS11 not available. Install with: pip install PyKCS11", file=sys.stderr)
    sys.exit(1)


def check_yubihsm_connector():
    """Check if YubiHSM connector is running."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:12345", timeout=2) as response:
            return response.status == 200
    except:
        return False


def main():
    """Main function."""
    print("YubiHSM Setup and Usage Example")
    print("=" * 50)

    # Configuration
    LIBRARY_PATH = "/usr/lib/x86_64-linux-gnu/pkcs11/yubihsm_pkcs11.so"
    SLOT = 0
    DEFAULT_PIN = "0001password"  # Default YubiHSM authentication key

    # Check connector
    print("\nChecking YubiHSM connector...")
    if not check_yubihsm_connector():
        print("  ✗ YubiHSM connector not running", file=sys.stderr)
        print("\nStart connector with: sudo systemctl start yubihsm-connector", file=sys.stderr)
        sys.exit(1)
    print("  ✓ Connector running")

    try:
        # Load PKCS#11 library
        print(f"\nLoading YubiHSM PKCS#11 library...")
        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(LIBRARY_PATH)

        info = pkcs11.getInfo()
        print(f"  Library: {info.manufacturerID}")

        # Open session
        print(f"\nOpening session...")
        session = pkcs11.openSession(SLOT, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)

        # Login
        print("\nLogging in...")
        session.login(DEFAULT_PIN)
        print("  ✓ Logged in")

        # Generate RSA key pair
        print("\nGenerating RSA-2048 key pair...")

        public_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
            (PyKCS11.CKA_TOKEN, True),
            (PyKCS11.CKA_VERIFY, True),
            (PyKCS11.CKA_MODULUS_BITS, 2048),
            (PyKCS11.CKA_PUBLIC_EXPONENT, (0x01, 0x00, 0x01)),
            (PyKCS11.CKA_LABEL, "YubiHSM Demo Key (Public)"),
        ]

        private_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
            (PyKCS11.CKA_TOKEN, True),
            (PyKCS11.CKA_PRIVATE, True),
            (PyKCS11.CKA_SENSITIVE, True),
            (PyKCS11.CKA_SIGN, True),
            (PyKCS11.CKA_LABEL, "YubiHSM Demo Key (Private)"),
        ]

        (public_key, private_key) = session.generateKeyPair(
            public_template,
            private_template,
            mecha=PyKCS11.MechanismRSAPKCSKeyPairGen
        )

        print(f"  ✓ Generated key pair")
        print(f"    Public:  {public_key}")
        print(f"    Private: {private_key}")

        # Sign test data
        print("\nSigning test data...")
        test_data = b"YubiHSM test message"
        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)
        signature = session.sign(private_key, test_data, mechanism)
        print(f"  ✓ Signature generated ({len(signature)} bytes)")

        # Verify signature
        print("\nVerifying signature...")
        session.verify(public_key, test_data, signature, mechanism)
        print("  ✓ Signature valid")

        # Cleanup
        print("\nCleaning up...")
        session.destroyObject(public_key)
        session.destroyObject(private_key)
        print("  ✓ Keys deleted")

        session.logout()
        session.closeSession()

        print("\n" + "=" * 50)
        print("Example completed successfully")
        print("=" * 50)

    except FileNotFoundError:
        print(f"\nError: YubiHSM library not found: {LIBRARY_PATH}", file=sys.stderr)
        print("\nInstall YubiHSM SDK from: https://developers.yubico.com/YubiHSM2/", file=sys.stderr)
        sys.exit(1)
    except PyKCS11Error as e:
        print(f"\nPKCS#11 Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
