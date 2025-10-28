#!/usr/bin/env python3
"""
PKCS#11 Key Generation Example

Demonstrates generating RSA, EC, and AES keys in HSM using PKCS#11.
Production-ready implementation with error handling and secure practices.
"""

import sys
from typing import Tuple

try:
    import PyKCS11
    from PyKCS11 import PyKCS11Error
except ImportError:
    print("Error: PyKCS11 not available. Install with: pip install PyKCS11", file=sys.stderr)
    sys.exit(1)


def generate_rsa_keypair(
    session: PyKCS11.Session,
    label: str,
    modulus_bits: int = 2048,
    extractable: bool = False
) -> Tuple[int, int]:
    """
    Generate RSA key pair in HSM.

    Args:
        session: PKCS#11 session
        label: Key label
        modulus_bits: Key size in bits (2048, 3072, or 4096)
        extractable: Whether private key can be extracted (not recommended)

    Returns:
        Tuple of (public_key_handle, private_key_handle)
    """
    print(f"Generating RSA-{modulus_bits} key pair: {label}...")

    # Public key template
    public_template = [
        (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
        (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
        (PyKCS11.CKA_TOKEN, True),  # Persistent key
        (PyKCS11.CKA_ENCRYPT, True),
        (PyKCS11.CKA_VERIFY, True),
        (PyKCS11.CKA_WRAP, True),
        (PyKCS11.CKA_MODULUS_BITS, modulus_bits),
        (PyKCS11.CKA_PUBLIC_EXPONENT, (0x01, 0x00, 0x01)),  # 65537
        (PyKCS11.CKA_LABEL, f"{label} (Public)"),
    ]

    # Private key template
    private_template = [
        (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
        (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
        (PyKCS11.CKA_TOKEN, True),  # Persistent key
        (PyKCS11.CKA_PRIVATE, True),  # Requires login
        (PyKCS11.CKA_SENSITIVE, True),  # Cannot be read in plaintext
        (PyKCS11.CKA_EXTRACTABLE, extractable),  # Cannot be exported (recommended)
        (PyKCS11.CKA_DECRYPT, True),
        (PyKCS11.CKA_SIGN, True),
        (PyKCS11.CKA_UNWRAP, True),
        (PyKCS11.CKA_LABEL, f"{label} (Private)"),
    ]

    try:
        (public_key, private_key) = session.generateKeyPair(
            public_template,
            private_template,
            mecha=PyKCS11.MechanismRSAPKCSKeyPairGen
        )

        print(f"  ✓ Generated RSA key pair")
        print(f"    Public key handle:  {public_key}")
        print(f"    Private key handle: {private_key}")

        return (public_key, private_key)

    except PyKCS11Error as e:
        print(f"  ✗ Failed to generate RSA key pair: {e}", file=sys.stderr)
        raise


def generate_ec_keypair(
    session: PyKCS11.Session,
    label: str,
    curve: str = "secp256r1",
    extractable: bool = False
) -> Tuple[int, int]:
    """
    Generate EC key pair in HSM.

    Args:
        session: PKCS#11 session
        label: Key label
        curve: Curve name (secp256r1, secp384r1, secp521r1)
        extractable: Whether private key can be extracted (not recommended)

    Returns:
        Tuple of (public_key_handle, private_key_handle)
    """
    print(f"Generating EC key pair ({curve}): {label}...")

    # Curve OIDs (DER encoded)
    curves = {
        "secp256r1": bytes([0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01, 0x07]),  # P-256
        "secp384r1": bytes([0x06, 0x05, 0x2b, 0x81, 0x04, 0x00, 0x22]),  # P-384
        "secp521r1": bytes([0x06, 0x05, 0x2b, 0x81, 0x04, 0x00, 0x23]),  # P-521
    }

    if curve not in curves:
        raise ValueError(f"Unsupported curve: {curve}")

    curve_oid = curves[curve]

    # Public key template
    public_template = [
        (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
        (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_EC),
        (PyKCS11.CKA_TOKEN, True),
        (PyKCS11.CKA_VERIFY, True),
        (PyKCS11.CKA_EC_PARAMS, curve_oid),
        (PyKCS11.CKA_LABEL, f"{label} (Public)"),
    ]

    # Private key template
    private_template = [
        (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
        (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_EC),
        (PyKCS11.CKA_TOKEN, True),
        (PyKCS11.CKA_PRIVATE, True),
        (PyKCS11.CKA_SENSITIVE, True),
        (PyKCS11.CKA_EXTRACTABLE, extractable),
        (PyKCS11.CKA_SIGN, True),
        (PyKCS11.CKA_DERIVE, True),  # For ECDH
        (PyKCS11.CKA_LABEL, f"{label} (Private)"),
    ]

    try:
        (public_key, private_key) = session.generateKeyPair(
            public_template,
            private_template,
            mecha=PyKCS11.MechanismECKeyPairGen
        )

        print(f"  ✓ Generated EC key pair")
        print(f"    Public key handle:  {public_key}")
        print(f"    Private key handle: {private_key}")

        return (public_key, private_key)

    except PyKCS11Error as e:
        print(f"  ✗ Failed to generate EC key pair: {e}", file=sys.stderr)
        raise


def generate_aes_key(
    session: PyKCS11.Session,
    label: str,
    key_size: int = 32,
    extractable: bool = False
) -> int:
    """
    Generate AES key in HSM.

    Args:
        session: PKCS#11 session
        label: Key label
        key_size: Key size in bytes (16=AES-128, 24=AES-192, 32=AES-256)
        extractable: Whether key can be extracted (not recommended)

    Returns:
        Key handle
    """
    print(f"Generating AES-{key_size * 8} key: {label}...")

    # Key template
    template = [
        (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
        (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_AES),
        (PyKCS11.CKA_TOKEN, True),
        (PyKCS11.CKA_PRIVATE, True),
        (PyKCS11.CKA_SENSITIVE, True),
        (PyKCS11.CKA_EXTRACTABLE, extractable),
        (PyKCS11.CKA_ENCRYPT, True),
        (PyKCS11.CKA_DECRYPT, True),
        (PyKCS11.CKA_WRAP, True),
        (PyKCS11.CKA_UNWRAP, True),
        (PyKCS11.CKA_VALUE_LEN, key_size),
        (PyKCS11.CKA_LABEL, label),
    ]

    try:
        key = session.generateKey(template, mecha=PyKCS11.MechanismAESKeyGen)

        print(f"  ✓ Generated AES key")
        print(f"    Key handle: {key}")

        return key

    except PyKCS11Error as e:
        print(f"  ✗ Failed to generate AES key: {e}", file=sys.stderr)
        raise


def main():
    """Main function demonstrating key generation."""
    # Configuration
    LIBRARY_PATH = "/usr/lib/softhsm/libsofthsm2.so"  # Adjust for your HSM
    SLOT = 0
    PIN = "1234"  # Use secure PIN management in production

    print("HSM Key Generation Example")
    print("=" * 50)

    try:
        # Load PKCS#11 library
        print(f"\nLoading PKCS#11 library: {LIBRARY_PATH}")
        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(LIBRARY_PATH)

        # Get library info
        info = pkcs11.getInfo()
        print(f"Library: {info.manufacturerID} v{info.libraryVersion}")

        # Open session
        print(f"\nOpening session on slot {SLOT}...")
        session = pkcs11.openSession(SLOT, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)
        print("  ✓ Session opened")

        # Login
        print("\nLogging in...")
        session.login(PIN)
        print("  ✓ Logged in")

        print("\n" + "=" * 50)
        print("Generating Keys")
        print("=" * 50)

        # Generate RSA key pair
        print("\n1. RSA Key Generation")
        rsa_public, rsa_private = generate_rsa_keypair(
            session,
            label="Demo RSA Key",
            modulus_bits=2048,
            extractable=False
        )

        # Generate EC key pair
        print("\n2. EC Key Generation")
        ec_public, ec_private = generate_ec_keypair(
            session,
            label="Demo EC Key",
            curve="secp256r1",
            extractable=False
        )

        # Generate AES key
        print("\n3. AES Key Generation")
        aes_key = generate_aes_key(
            session,
            label="Demo AES Key",
            key_size=32,  # AES-256
            extractable=False
        )

        print("\n" + "=" * 50)
        print("Listing Generated Keys")
        print("=" * 50)

        # List all keys
        print("\nPrivate keys:")
        private_keys = session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY)])
        for key_handle in private_keys:
            try:
                attrs = session.getAttributeValue(key_handle, [PyKCS11.CKA_LABEL])
                label = ''.join(chr(c) for c in attrs[0] if c != 0)
                print(f"  - {label} (handle: {key_handle})")
            except:
                pass

        print("\nSecret keys:")
        secret_keys = session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY)])
        for key_handle in secret_keys:
            try:
                attrs = session.getAttributeValue(key_handle, [PyKCS11.CKA_LABEL])
                label = ''.join(chr(c) for c in attrs[0] if c != 0)
                print(f"  - {label} (handle: {key_handle})")
            except:
                pass

        print("\n" + "=" * 50)
        print("Cleanup")
        print("=" * 50)

        # Delete generated keys
        print("\nDeleting generated keys...")
        for key_handle in [rsa_public, rsa_private, ec_public, ec_private, aes_key]:
            try:
                session.destroyObject(key_handle)
                print(f"  ✓ Deleted key {key_handle}")
            except Exception as e:
                print(f"  ✗ Failed to delete key {key_handle}: {e}")

        # Logout and close session
        print("\nLogging out...")
        session.logout()
        session.closeSession()
        print("  ✓ Session closed")

        print("\n" + "=" * 50)
        print("Example completed successfully")
        print("=" * 50)

    except PyKCS11Error as e:
        print(f"\nPKCS#11 Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
