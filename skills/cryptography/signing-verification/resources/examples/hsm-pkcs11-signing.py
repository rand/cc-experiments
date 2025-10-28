#!/usr/bin/env python3
"""
HSM-Backed Signing with PKCS#11

Demonstrates using Hardware Security Modules (HSMs) for signing operations
via the PKCS#11 interface. HSMs provide secure key storage and cryptographic
operations in tamper-resistant hardware.

Features:
- PKCS#11 HSM integration
- RSA and ECDSA signing with HSM-stored keys
- Key generation in HSM
- Secure key storage (keys never leave HSM)
- Multi-slot and multi-token support

Production Considerations:
- Use HSMs for high-value signing keys
- Implement key backup and disaster recovery
- Set up redundant HSMs for availability
- Use role-based access control
- Audit all HSM operations
- Comply with FIPS 140-2 Level 3+ requirements

Requirements:
    pip install python-pkcs11 cryptography

HSM Setup (SoftHSM for testing):
    # Install SoftHSM
    brew install softhsm  # macOS
    apt-get install softhsm2  # Ubuntu

    # Initialize token
    softhsm2-util --init-token --slot 0 --label "signing-token" --pin 1234 --so-pin 5678
"""

import sys
from pathlib import Path

try:
    import pkcs11
    from pkcs11 import Attribute, KeyType, Mechanism, ObjectClass
except ImportError:
    print("Error: python-pkcs11 required. Install: pip install python-pkcs11", file=sys.stderr)
    sys.exit(1)

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.x509.oid import NameOID
except ImportError:
    print("Error: cryptography required. Install: pip install cryptography", file=sys.stderr)
    sys.exit(1)


class HSMSigner:
    """HSM-backed signing operations"""

    def __init__(self, module_path: str, token_label: str, pin: str):
        """
        Initialize HSM connection

        Args:
            module_path: Path to PKCS#11 module (e.g., /usr/lib/softhsm/libsofthsm2.so)
            token_label: Token label
            pin: User PIN
        """
        self.lib = pkcs11.lib(module_path)
        self.token = self.lib.get_token(token_label=token_label)
        self.session = self.token.open(user_pin=pin)

    def generate_rsa_keypair(self, label: str = "signing-key", key_size: int = 2048):
        """Generate RSA key pair in HSM"""
        print(f"Generating {key_size}-bit RSA key pair in HSM...")

        # Generate key pair (keys never leave HSM)
        public_key, private_key = self.session.generate_keypair(
            KeyType.RSA,
            key_size,
            label=label,
            store=True,  # Store persistently in HSM
            capabilities=(
                # Public key capabilities
                pkcs11.MechanismFlag.VERIFY,
                # Private key capabilities
                pkcs11.MechanismFlag.SIGN,
            )
        )

        print(f"   ✓ Key pair generated with label: {label}")
        return public_key, private_key

    def generate_ecdsa_keypair(self, label: str = "signing-key-ec", curve: str = "secp256r1"):
        """Generate ECDSA key pair in HSM"""
        print(f"Generating ECDSA {curve} key pair in HSM...")

        # Map curve names to PKCS#11 parameters
        curves = {
            "secp256r1": pkcs11.util.ec.SECP256R1,
            "secp384r1": pkcs11.util.ec.SECP384R1,
            "secp521r1": pkcs11.util.ec.SECP521R1,
        }

        if curve not in curves:
            raise ValueError(f"Unsupported curve: {curve}")

        # Generate key pair
        public_key, private_key = self.session.generate_keypair(
            KeyType.EC,
            ecparams=curves[curve],
            label=label,
            store=True,
            capabilities=(
                pkcs11.MechanismFlag.VERIFY,
                pkcs11.MechanismFlag.SIGN,
            )
        )

        print(f"   ✓ EC key pair generated with label: {label}")
        return public_key, private_key

    def list_keys(self):
        """List all keys in HSM"""
        print("\nKeys in HSM:")

        # List private keys
        private_keys = list(self.session.get_objects({Attribute.CLASS: ObjectClass.PRIVATE_KEY}))
        print(f"  Private keys: {len(private_keys)}")
        for key in private_keys:
            label = key[Attribute.LABEL]
            key_type = key[Attribute.KEY_TYPE]
            print(f"    - {label} ({key_type})")

        # List public keys
        public_keys = list(self.session.get_objects({Attribute.CLASS: ObjectClass.PUBLIC_KEY}))
        print(f"  Public keys: {len(public_keys)}")
        for key in public_keys:
            label = key[Attribute.LABEL]
            key_type = key[Attribute.KEY_TYPE]
            print(f"    - {label} ({key_type})")

    def sign_data_rsa(self, data: bytes, key_label: str = "signing-key") -> bytes:
        """Sign data using RSA key in HSM"""
        # Find private key
        private_key = self.session.get_key(
            object_class=ObjectClass.PRIVATE_KEY,
            label=key_label
        )

        # Sign data (operation happens in HSM)
        signature = private_key.sign(
            data,
            mechanism=Mechanism.SHA256_RSA_PKCS
        )

        return signature

    def sign_data_ecdsa(self, data: bytes, key_label: str = "signing-key-ec") -> bytes:
        """Sign data using ECDSA key in HSM"""
        # Find private key
        private_key = self.session.get_key(
            object_class=ObjectClass.PRIVATE_KEY,
            label=key_label
        )

        # Sign data
        signature = private_key.sign(
            data,
            mechanism=Mechanism.ECDSA_SHA256
        )

        return signature

    def export_public_key(self, key_label: str, output_path: str):
        """Export public key from HSM (public key can be exported)"""
        # Find public key
        public_key = self.session.get_key(
            object_class=ObjectClass.PUBLIC_KEY,
            label=key_label
        )

        # Get key type
        key_type = public_key[Attribute.KEY_TYPE]

        if key_type == KeyType.RSA:
            # Extract RSA public key components
            modulus = public_key[Attribute.MODULUS]
            exponent = public_key[Attribute.PUBLIC_EXPONENT]

            # For production, convert to proper format
            print(f"   RSA public key exported (modulus length: {len(modulus)} bytes)")

        elif key_type == KeyType.EC:
            # Extract EC public key
            ec_point = public_key[Attribute.EC_POINT]
            ec_params = public_key[Attribute.EC_PARAMS]

            print(f"   EC public key exported (point length: {len(ec_point)} bytes)")

        # Note: Full export to PEM requires additional encoding
        # This is simplified for demonstration

    def verify_signature_rsa(self, data: bytes, signature: bytes, key_label: str = "signing-key") -> bool:
        """Verify RSA signature using public key in HSM"""
        try:
            # Find public key
            public_key = self.session.get_key(
                object_class=ObjectClass.PUBLIC_KEY,
                label=key_label
            )

            # Verify signature
            public_key.verify(
                data,
                signature,
                mechanism=Mechanism.SHA256_RSA_PKCS
            )

            return True
        except Exception as e:
            print(f"Verification failed: {e}")
            return False

    def verify_signature_ecdsa(self, data: bytes, signature: bytes, key_label: str = "signing-key-ec") -> bool:
        """Verify ECDSA signature using public key in HSM"""
        try:
            # Find public key
            public_key = self.session.get_key(
                object_class=ObjectClass.PUBLIC_KEY,
                label=key_label
            )

            # Verify signature
            public_key.verify(
                data,
                signature,
                mechanism=Mechanism.ECDSA_SHA256
            )

            return True
        except Exception as e:
            print(f"Verification failed: {e}")
            return False

    def close(self):
        """Close HSM session"""
        self.session.close()


def main():
    """Demonstration workflow"""
    print("HSM-Backed Signing with PKCS#11")
    print("="*60)

    # Configuration (adjust for your HSM)
    MODULE_PATH = "/usr/lib/softhsm/libsofthsm2.so"  # SoftHSM path
    TOKEN_LABEL = "signing-token"
    PIN = "1234"

    # Check if module exists
    if not Path(MODULE_PATH).exists():
        print(f"\nError: PKCS#11 module not found at {MODULE_PATH}")
        print("\nFor testing with SoftHSM:")
        print("  1. Install SoftHSM: brew install softhsm (macOS) or apt-get install softhsm2 (Ubuntu)")
        print("  2. Initialize token: softhsm2-util --init-token --slot 0 --label 'signing-token' --pin 1234 --so-pin 5678")
        print("  3. Find module path: softhsm2-util --show-slots")
        return

    try:
        # Initialize HSM connection
        print(f"\n1. Connecting to HSM...")
        print(f"   Module: {MODULE_PATH}")
        print(f"   Token: {TOKEN_LABEL}")

        hsm = HSMSigner(MODULE_PATH, TOKEN_LABEL, PIN)
        print("   ✓ Connected to HSM")

        # Generate RSA key pair
        print("\n2. Generating RSA key pair in HSM...")
        pub_rsa, priv_rsa = hsm.generate_rsa_keypair("demo-rsa-key", 2048)

        # Generate ECDSA key pair
        print("\n3. Generating ECDSA key pair in HSM...")
        pub_ec, priv_ec = hsm.generate_ecdsa_keypair("demo-ec-key", "secp256r1")

        # List all keys
        print("\n4. Listing keys in HSM...")
        hsm.list_keys()

        # Sign with RSA
        print("\n5. Signing with RSA key (in HSM)...")
        data = b"Important document requiring HSM-backed signature"
        signature_rsa = hsm.sign_data_rsa(data, "demo-rsa-key")
        print(f"   ✓ RSA signature generated ({len(signature_rsa)} bytes)")
        print(f"   Note: Private key NEVER left the HSM")

        # Verify RSA signature
        print("\n6. Verifying RSA signature...")
        is_valid = hsm.verify_signature_rsa(data, signature_rsa, "demo-rsa-key")
        print(f"   ✓ Signature valid: {is_valid}")

        # Sign with ECDSA
        print("\n7. Signing with ECDSA key (in HSM)...")
        signature_ec = hsm.sign_data_ecdsa(data, "demo-ec-key")
        print(f"   ✓ ECDSA signature generated ({len(signature_ec)} bytes)")

        # Verify ECDSA signature
        print("\n8. Verifying ECDSA signature...")
        is_valid = hsm.verify_signature_ecdsa(data, signature_ec, "demo-ec-key")
        print(f"   ✓ Signature valid: {is_valid}")

        # Export public key
        print("\n9. Exporting public key...")
        hsm.export_public_key("demo-rsa-key", "hsm-public.pem")

        # Test with modified data
        print("\n10. Testing with modified data...")
        modified_data = b"Modified document"
        is_valid = hsm.verify_signature_rsa(modified_data, signature_rsa, "demo-rsa-key")
        print(f"    Signature valid: {is_valid} (expected: False)")

        # Close connection
        hsm.close()

        print("\n" + "="*60)
        print("Production Recommendations:")
        print("")
        print("HSM Selection:")
        print("  • Use FIPS 140-2 Level 3+ certified HSMs")
        print("  • Consider cloud HSM services (AWS CloudHSM, Azure Dedicated HSM)")
        print("  • Common HSMs: Thales Luna, Utimaco, YubiHSM")
        print("")
        print("Key Management:")
        print("  • Generate keys in HSM (never import if possible)")
        print("  • Use key backup/recovery procedures")
        print("  • Implement M-of-N key custody")
        print("  • Set up redundant HSMs")
        print("")
        print("Access Control:")
        print("  • Use role-based access (Crypto Officer, User)")
        print("  • Implement PIN policies (complexity, rotation)")
        print("  • Enable audit logging")
        print("  • Monitor all HSM operations")
        print("")
        print("Operations:")
        print("  • Never allow private key export")
        print("  • Use session-based authentication")
        print("  • Implement rate limiting")
        print("  • Test disaster recovery procedures")
        print("")
        print("Compliance:")
        print("  • FIPS 140-2 Level 3+ for government/finance")
        print("  • Common Criteria EAL4+ for high security")
        print("  • PCI-DSS for payment processing")
        print("  • eIDAS for qualified signatures (EU)")

    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("  • Verify PKCS#11 module path is correct")
        print("  • Check token is initialized: softhsm2-util --show-slots")
        print("  • Verify PIN is correct")
        print("  • Ensure sufficient permissions to access HSM")


if __name__ == "__main__":
    main()
