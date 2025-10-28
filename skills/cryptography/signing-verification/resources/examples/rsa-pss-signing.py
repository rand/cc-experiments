#!/usr/bin/env python3
"""
RSA-PSS Document Signing Example

Demonstrates RSA-PSS signature generation and verification using the cryptography library.
RSA-PSS (Probabilistic Signature Scheme) is recommended over PKCS#1 v1.5 for new applications
due to its provable security properties.

Features:
- RSA-PSS signature generation with SHA-256
- Signature verification
- Support for both 2048 and 4096-bit keys
- PEM/DER format handling
- Detached signatures

Production Considerations:
- Use 3072 or 4096-bit keys for long-term security
- Store private keys in HSMs for production
- Implement key rotation policies
- Use SHA-384 or SHA-512 for 4096-bit keys
"""

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pathlib import Path


def generate_key_pair(key_size: int = 2048) -> tuple:
    """Generate RSA key pair"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size
    )
    public_key = private_key.public_key()
    return private_key, public_key


def save_keys(private_key, public_key, base_path: str = "rsa-key"):
    """Save keys to PEM files"""
    # Save private key (encrypted with password in production)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()  # Use BestAvailableEncryption in production
    )
    Path(f"{base_path}-private.pem").write_bytes(private_pem)

    # Save public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    Path(f"{base_path}-public.pem").write_bytes(public_pem)


def load_private_key(path: str):
    """Load private key from file"""
    key_data = Path(path).read_bytes()
    return serialization.load_pem_private_key(
        key_data,
        password=None  # Provide password for encrypted keys
    )


def load_public_key(path: str):
    """Load public key from file"""
    key_data = Path(path).read_bytes()
    return serialization.load_pem_public_key(key_data)


def sign_document(private_key, document: bytes) -> bytes:
    """
    Sign document using RSA-PSS

    RSA-PSS parameters:
    - MGF: MGF1 with SHA-256
    - Salt length: Maximum (recommended for security)
    - Hash: SHA-256 (use SHA-384 or SHA-512 for 4096-bit keys)
    """
    signature = private_key.sign(
        document,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature


def verify_signature(public_key, document: bytes, signature: bytes) -> bool:
    """Verify RSA-PSS signature"""
    try:
        public_key.verify(
            signature,
            document,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        print(f"Verification failed: {e}")
        return False


def main():
    """Demonstration workflow"""
    print("RSA-PSS Signature Example\n" + "="*50)

    # 1. Generate key pair
    print("\n1. Generating 2048-bit RSA key pair...")
    private_key, public_key = generate_key_pair(2048)
    save_keys(private_key, public_key, "demo-rsa")
    print("   Keys saved to demo-rsa-private.pem and demo-rsa-public.pem")

    # 2. Sign document
    document = b"This is an important document that requires signing."
    print(f"\n2. Signing document: '{document.decode()}'")
    signature = sign_document(private_key, document)
    print(f"   Signature length: {len(signature)} bytes")

    # Save signature
    Path("demo-signature.bin").write_bytes(signature)
    print("   Signature saved to demo-signature.bin")

    # 3. Verify signature
    print("\n3. Verifying signature...")
    is_valid = verify_signature(public_key, document, signature)
    print(f"   Signature valid: {is_valid}")

    # 4. Test with modified document
    print("\n4. Testing with modified document...")
    modified_document = b"This is a MODIFIED document."
    is_valid = verify_signature(public_key, modified_document, signature)
    print(f"   Signature valid: {is_valid} (expected: False)")

    # 5. Demonstrate loading keys
    print("\n5. Demonstrating key loading...")
    loaded_private = load_private_key("demo-rsa-private.pem")
    loaded_public = load_public_key("demo-rsa-public.pem")

    # Verify with loaded public key
    is_valid = verify_signature(loaded_public, document, signature)
    print(f"   Verification with loaded key: {is_valid}")

    # 6. Demonstrate 4096-bit key
    print("\n6. Demonstrating 4096-bit key for long-term security...")
    private_4096, public_4096 = generate_key_pair(4096)
    signature_4096 = sign_document(private_4096, document)
    print(f"   4096-bit signature length: {len(signature_4096)} bytes")
    is_valid = verify_signature(public_4096, document, signature_4096)
    print(f"   Signature valid: {is_valid}")

    print("\n" + "="*50)
    print("Production recommendations:")
    print("- Use 3072 or 4096-bit keys for long-term security")
    print("- Encrypt private keys with strong passwords")
    print("- Store private keys in HSMs")
    print("- Use SHA-384 or SHA-512 for 4096-bit keys")
    print("- Implement key rotation every 1-2 years")


if __name__ == "__main__":
    main()
