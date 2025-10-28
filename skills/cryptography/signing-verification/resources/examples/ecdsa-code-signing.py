#!/usr/bin/env python3
"""
ECDSA Code Signing Example

Demonstrates ECDSA (Elliptic Curve Digital Signature Algorithm) for code signing
using NIST P-256 and P-384 curves. ECDSA provides equivalent security to RSA with
smaller key sizes and faster operations.

Features:
- ECDSA signature generation with P-256 and P-384 curves
- Code artifact signing with metadata
- Signature verification
- Multi-file signing
- JSON signature manifest

Production Considerations:
- Use P-384 for high-security applications
- Implement nonce generation carefully (use system CSPRNG)
- Combine with timestamping for long-term validity
- Store signatures separately from signed code
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def generate_ecdsa_key(curve_name: str = 'P-256'):
    """Generate ECDSA key pair"""
    curves = {
        'P-256': ec.SECP256R1(),
        'P-384': ec.SECP384R1(),
        'P-521': ec.SECP521R1()
    }

    if curve_name not in curves:
        raise ValueError(f"Unsupported curve: {curve_name}")

    private_key = ec.generate_private_key(curves[curve_name])
    return private_key


def save_key_pair(private_key, base_name: str):
    """Save ECDSA key pair"""
    # Save private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    Path(f"{base_name}-private.pem").write_bytes(private_pem)

    # Save public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    Path(f"{base_name}-public.pem").write_bytes(public_pem)


def sign_code(private_key, code: bytes, metadata: Dict = None) -> Dict:
    """
    Sign code artifact with metadata

    Returns signature bundle with:
    - Signature bytes
    - Hash algorithm
    - Curve name
    - Timestamp
    - Optional metadata
    """
    # Generate signature
    signature = private_key.sign(
        code,
        ec.ECDSA(hashes.SHA256())
    )

    # Compute code hash for verification
    code_hash = hashlib.sha256(code).hexdigest()

    # Get curve name
    curve = private_key.curve
    curve_name = curve.name

    # Build signature bundle
    bundle = {
        'signature': signature.hex(),
        'code_hash': code_hash,
        'hash_algorithm': 'SHA-256',
        'curve': curve_name,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'metadata': metadata or {}
    }

    return bundle


def verify_code(public_key, code: bytes, signature_bundle: Dict) -> bool:
    """Verify code signature"""
    try:
        # Extract signature
        signature = bytes.fromhex(signature_bundle['signature'])

        # Verify signature
        public_key.verify(
            signature,
            code,
            ec.ECDSA(hashes.SHA256())
        )

        # Verify code hash
        expected_hash = signature_bundle['code_hash']
        actual_hash = hashlib.sha256(code).hexdigest()

        if expected_hash != actual_hash:
            print("Hash mismatch!")
            return False

        return True

    except Exception as e:
        print(f"Verification failed: {e}")
        return False


def sign_multiple_files(private_key, files: List[Path]) -> Dict:
    """Sign multiple code files and create manifest"""
    manifest = {
        'version': '1.0',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'files': {}
    }

    for file_path in files:
        if not file_path.exists():
            print(f"Warning: {file_path} does not exist")
            continue

        # Read file
        code = file_path.read_bytes()

        # Sign file
        bundle = sign_code(
            private_key,
            code,
            metadata={'filename': str(file_path), 'size': len(code)}
        )

        # Add to manifest
        manifest['files'][str(file_path)] = bundle

    return manifest


def verify_manifest(public_key, manifest: Dict) -> Dict[str, bool]:
    """Verify all files in manifest"""
    results = {}

    for file_path, bundle in manifest['files'].items():
        path = Path(file_path)

        if not path.exists():
            print(f"Warning: {file_path} not found")
            results[file_path] = False
            continue

        # Read file
        code = path.read_bytes()

        # Verify
        is_valid = verify_code(public_key, code, bundle)
        results[file_path] = is_valid

    return results


def main():
    """Demonstration workflow"""
    print("ECDSA Code Signing Example\n" + "="*60)

    # 1. Generate P-256 key
    print("\n1. Generating ECDSA P-256 key pair...")
    private_key = generate_ecdsa_key('P-256')
    public_key = private_key.public_key()
    save_key_pair(private_key, "ecdsa-p256")
    print("   Keys saved to ecdsa-p256-private.pem and ecdsa-p256-public.pem")

    # 2. Sign single file
    print("\n2. Signing code artifact...")
    code = b"""#!/usr/bin/env python3
def hello():
    print("Hello, World!")

if __name__ == "__main__":
    hello()
"""
    Path("demo-code.py").write_bytes(code)

    metadata = {
        'version': '1.0.0',
        'author': 'Developer',
        'purpose': 'demonstration'
    }

    bundle = sign_code(private_key, code, metadata)
    print(f"   Signature: {bundle['signature'][:32]}...")
    print(f"   Code hash: {bundle['code_hash']}")
    print(f"   Timestamp: {bundle['timestamp']}")

    # Save signature
    Path("demo-code.py.sig").write_text(json.dumps(bundle, indent=2))
    print("   Signature saved to demo-code.py.sig")

    # 3. Verify signature
    print("\n3. Verifying signature...")
    is_valid = verify_code(public_key, code, bundle)
    print(f"   Signature valid: {is_valid}")

    # 4. Test with modified code
    print("\n4. Testing with modified code...")
    modified_code = code.replace(b"Hello, World!", b"Hello, Universe!")
    is_valid = verify_code(public_key, modified_code, bundle)
    print(f"   Signature valid: {is_valid} (expected: False)")

    # 5. Sign multiple files
    print("\n5. Signing multiple files...")

    # Create test files
    files = []
    for i in range(3):
        filename = f"module_{i}.py"
        content = f"# Module {i}\n\ndef function_{i}():\n    return {i}\n".encode()
        Path(filename).write_bytes(content)
        files.append(Path(filename))

    manifest = sign_multiple_files(private_key, files)
    Path("code-manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"   Signed {len(manifest['files'])} files")
    print("   Manifest saved to code-manifest.json")

    # 6. Verify manifest
    print("\n6. Verifying manifest...")
    results = verify_manifest(public_key, manifest)
    for file_path, is_valid in results.items():
        status = "✓" if is_valid else "✗"
        print(f"   {status} {file_path}")

    # 7. Demonstrate P-384 for high security
    print("\n7. Demonstrating P-384 for high-security applications...")
    private_384 = generate_ecdsa_key('P-384')
    public_384 = private_384.public_key()

    bundle_384 = sign_code(private_384, code, {'security_level': 'high'})
    is_valid = verify_code(public_384, code, bundle_384)
    print(f"   P-384 signature valid: {is_valid}")
    print(f"   P-384 signature length: {len(bundle_384['signature'])} chars")

    # 8. Compare signature sizes
    print("\n8. Signature size comparison:")
    print(f"   P-256 signature: {len(bundle['signature'])} hex chars")
    print(f"   P-384 signature: {len(bundle_384['signature'])} hex chars")
    print(f"   (RSA-2048 would be: ~512 hex chars)")

    print("\n" + "="*60)
    print("Production recommendations:")
    print("- Use P-384 for high-security or long-term applications")
    print("- Include version metadata for signature format evolution")
    print("- Combine with timestamp authority for long-term validity")
    print("- Store signatures in separate .sig files")
    print("- Verify signatures before executing code")
    print("- Rotate keys annually")


if __name__ == "__main__":
    main()
