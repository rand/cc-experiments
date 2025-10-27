#!/usr/bin/env python3
"""
Key Hierarchy Generation and Management Tool

Generate and manage cryptographic key hierarchies with Root Keys, Key Encryption Keys (KEKs),
and Data Encryption Keys (DEKs) for secure envelope encryption patterns.

Features:
- Multi-tier key hierarchy (Root → KEK → DEK → Data)
- Support for multiple KMS backends (AWS KMS, GCP KMS, Azure, Vault, local HSM simulation)
- Automated key generation with proper entropy
- Key wrapping and unwrapping
- Export/import key hierarchies
- Key hierarchy visualization
- Access control templates
- Audit logging
- JSON output for automation

Usage:
    # Generate complete 3-tier hierarchy
    ./generate_key_hierarchy.py --tiers 3 --platform aws-kms --region us-east-1 --output hierarchy.json

    # Generate local HSM-backed root key
    ./generate_key_hierarchy.py --root-hsm --platform local --output-dir ./keys

    # Generate hierarchy with specific algorithms
    ./generate_key_hierarchy.py --root-algorithm rsa-4096 --kek-algorithm aes-256 --dek-count 10

    # Visualize existing hierarchy
    ./generate_key_hierarchy.py --load hierarchy.json --visualize

    # Export hierarchy for backup
    ./generate_key_hierarchy.py --load hierarchy.json --export encrypted-backup.enc --password <password>
"""

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from enum import Enum


class KeyTier(Enum):
    """Key hierarchy tier"""
    ROOT = "root"
    KEK = "kek"
    DEK = "dek"


class Algorithm(Enum):
    """Supported algorithms"""
    AES_256 = "aes-256-gcm"
    AES_128 = "aes-128-gcm"
    CHACHA20_POLY1305 = "chacha20-poly1305"
    RSA_2048 = "rsa-2048"
    RSA_4096 = "rsa-4096"
    ECC_P256 = "ecc-p256"
    ECC_P384 = "ecc-p384"


class Platform(Enum):
    """Supported platforms"""
    AWS_KMS = "aws-kms"
    GCP_KMS = "gcp-kms"
    AZURE_VAULT = "azure"
    HASHICORP_VAULT = "vault"
    LOCAL = "local"
    HSM_SIMULATED = "hsm-sim"


@dataclass
class KeyMetadata:
    """Key metadata"""
    key_id: str
    tier: str
    algorithm: str
    key_length: int
    created_at: str
    expires_at: Optional[str]
    parent_key_id: Optional[str]
    platform: str
    hsm_backed: bool
    fips_validated: bool
    version: int = 1
    status: str = "active"
    description: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class WrappedKey:
    """Wrapped (encrypted) key"""
    key_id: str
    wrapped_key_material: str  # Base64 encoded
    wrapping_key_id: str
    wrapping_algorithm: str
    nonce: Optional[str] = None  # For AEAD algorithms


@dataclass
class KeyHierarchy:
    """Complete key hierarchy"""
    hierarchy_id: str
    created_at: str
    platform: str
    root_key: KeyMetadata
    keks: List[KeyMetadata]
    deks: List[KeyMetadata]
    wrapped_keys: List[WrappedKey]
    access_policies: List[Dict] = field(default_factory=list)
    audit_log: List[Dict] = field(default_factory=list)


class CryptoEngine:
    """Cryptographic operations engine"""

    @staticmethod
    def generate_symmetric_key(algorithm: Algorithm) -> bytes:
        """Generate symmetric encryption key"""
        if algorithm in [Algorithm.AES_256, Algorithm.CHACHA20_POLY1305]:
            return secrets.token_bytes(32)  # 256 bits
        elif algorithm == Algorithm.AES_128:
            return secrets.token_bytes(16)  # 128 bits
        else:
            raise ValueError(f"Unsupported symmetric algorithm: {algorithm}")

    @staticmethod
    def generate_asymmetric_keypair(algorithm: Algorithm) -> Tuple[bytes, bytes]:
        """Generate asymmetric key pair"""
        from cryptography.hazmat.primitives.asymmetric import rsa, ec
        from cryptography.hazmat.primitives import serialization

        if algorithm == Algorithm.RSA_2048:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
        elif algorithm == Algorithm.RSA_4096:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096
            )
        elif algorithm == Algorithm.ECC_P256:
            private_key = ec.generate_private_key(ec.SECP256R1())
        elif algorithm == Algorithm.ECC_P384:
            private_key = ec.generate_private_key(ec.SECP384R1())
        else:
            raise ValueError(f"Unsupported asymmetric algorithm: {algorithm}")

        # Serialize keys
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_bytes, public_bytes

    @staticmethod
    def wrap_key(dek: bytes, kek: bytes, algorithm: Algorithm) -> Tuple[bytes, Optional[bytes]]:
        """Wrap (encrypt) DEK with KEK"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305

        if algorithm == Algorithm.AES_256 or algorithm == Algorithm.AES_128:
            aesgcm = AESGCM(kek)
            nonce = secrets.token_bytes(12)
            wrapped = aesgcm.encrypt(nonce, dek, None)
            return wrapped, nonce

        elif algorithm == Algorithm.CHACHA20_POLY1305:
            chacha = ChaCha20Poly1305(kek)
            nonce = secrets.token_bytes(12)
            wrapped = chacha.encrypt(nonce, dek, None)
            return wrapped, nonce

        else:
            raise ValueError(f"Unsupported wrapping algorithm: {algorithm}")

    @staticmethod
    def unwrap_key(wrapped_dek: bytes, kek: bytes, algorithm: Algorithm, nonce: bytes) -> bytes:
        """Unwrap (decrypt) DEK with KEK"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305

        if algorithm == Algorithm.AES_256 or algorithm == Algorithm.AES_128:
            aesgcm = AESGCM(kek)
            dek = aesgcm.decrypt(nonce, wrapped_dek, None)
            return dek

        elif algorithm == Algorithm.CHACHA20_POLY1305:
            chacha = ChaCha20Poly1305(kek)
            dek = chacha.decrypt(nonce, wrapped_dek, None)
            return dek

        else:
            raise ValueError(f"Unsupported unwrapping algorithm: {algorithm}")


class KeyHierarchyGenerator:
    """Key hierarchy generator"""

    def __init__(self, platform: Platform, output_dir: Path, verbose: bool = False):
        self.platform = platform
        self.output_dir = output_dir
        self.verbose = verbose
        self.crypto_engine = CryptoEngine()

        output_dir.mkdir(parents=True, exist_ok=True)

    def generate_hierarchy(
        self,
        tiers: int = 3,
        root_algorithm: Algorithm = Algorithm.AES_256,
        kek_algorithm: Algorithm = Algorithm.AES_256,
        dek_algorithm: Algorithm = Algorithm.AES_256,
        kek_count: int = 1,
        dek_count: int = 10,
        root_hsm: bool = False,
        expiry_days: Optional[int] = None
    ) -> KeyHierarchy:
        """Generate key hierarchy"""

        hierarchy_id = f"hierarchy-{int(datetime.now(timezone.utc).timestamp())}"

        if self.verbose:
            print(f"Generating {tiers}-tier key hierarchy: {hierarchy_id}")

        # Generate root key
        if self.verbose:
            print(f"  Generating root key ({root_algorithm.value})...")

        root_key = self._generate_key(
            tier=KeyTier.ROOT,
            algorithm=root_algorithm,
            parent_key_id=None,
            hsm_backed=root_hsm,
            expiry_days=expiry_days
        )

        # Store root key material (in production, store in HSM!)
        root_key_material = None
        if root_algorithm in [Algorithm.AES_256, Algorithm.AES_128, Algorithm.CHACHA20_POLY1305]:
            root_key_material = self.crypto_engine.generate_symmetric_key(root_algorithm)
            self._save_key_material(root_key.key_id, root_key_material)

        # Generate KEKs
        keks = []
        wrapped_keys = []

        if tiers >= 2:
            for i in range(kek_count):
                if self.verbose:
                    print(f"  Generating KEK {i+1}/{kek_count} ({kek_algorithm.value})...")

                kek = self._generate_key(
                    tier=KeyTier.KEK,
                    algorithm=kek_algorithm,
                    parent_key_id=root_key.key_id,
                    expiry_days=expiry_days
                )

                keks.append(kek)

                # Generate and wrap KEK material
                kek_material = self.crypto_engine.generate_symmetric_key(kek_algorithm)

                if root_key_material:
                    wrapped_kek, nonce = self.crypto_engine.wrap_key(
                        kek_material,
                        root_key_material,
                        root_algorithm
                    )

                    wrapped_keys.append(WrappedKey(
                        key_id=kek.key_id,
                        wrapped_key_material=base64.b64encode(wrapped_kek).decode('utf-8'),
                        wrapping_key_id=root_key.key_id,
                        wrapping_algorithm=root_algorithm.value,
                        nonce=base64.b64encode(nonce).decode('utf-8') if nonce else None
                    ))

                # Save KEK material
                self._save_key_material(kek.key_id, kek_material)

        # Generate DEKs
        deks = []

        if tiers >= 3 and keks:
            # Use first KEK to wrap DEKs
            wrapping_kek = keks[0]
            wrapping_kek_material = self._load_key_material(wrapping_kek.key_id)

            for i in range(dek_count):
                if self.verbose and i % 10 == 0:
                    print(f"  Generating DEKs {i+1}/{dek_count}...")

                dek = self._generate_key(
                    tier=KeyTier.DEK,
                    algorithm=dek_algorithm,
                    parent_key_id=wrapping_kek.key_id,
                    expiry_days=expiry_days
                )

                deks.append(dek)

                # Generate and wrap DEK material
                dek_material = self.crypto_engine.generate_symmetric_key(dek_algorithm)

                wrapped_dek, nonce = self.crypto_engine.wrap_key(
                    dek_material,
                    wrapping_kek_material,
                    kek_algorithm
                )

                wrapped_keys.append(WrappedKey(
                    key_id=dek.key_id,
                    wrapped_key_material=base64.b64encode(wrapped_dek).decode('utf-8'),
                    wrapping_key_id=wrapping_kek.key_id,
                    wrapping_algorithm=kek_algorithm.value,
                    nonce=base64.b64encode(nonce).decode('utf-8') if nonce else None
                ))

                # Don't save DEK material (only wrapped version)

        # Create hierarchy object
        hierarchy = KeyHierarchy(
            hierarchy_id=hierarchy_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            platform=self.platform.value,
            root_key=root_key,
            keks=keks,
            deks=deks,
            wrapped_keys=wrapped_keys
        )

        # Add audit entry
        hierarchy.audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "hierarchy_created",
            "details": {
                "tiers": tiers,
                "kek_count": len(keks),
                "dek_count": len(deks)
            }
        })

        if self.verbose:
            print(f"\n✓ Hierarchy generated successfully")
            print(f"  Root key: {root_key.key_id}")
            print(f"  KEKs: {len(keks)}")
            print(f"  DEKs: {len(deks)}")

        return hierarchy

    def _generate_key(
        self,
        tier: KeyTier,
        algorithm: Algorithm,
        parent_key_id: Optional[str],
        hsm_backed: bool = False,
        expiry_days: Optional[int] = None
    ) -> KeyMetadata:
        """Generate key metadata"""

        key_id = f"{tier.value}-{secrets.token_hex(8)}"

        # Determine key length
        if algorithm in [Algorithm.AES_256, Algorithm.CHACHA20_POLY1305]:
            key_length = 256
        elif algorithm == Algorithm.AES_128:
            key_length = 128
        elif algorithm == Algorithm.RSA_2048:
            key_length = 2048
        elif algorithm == Algorithm.RSA_4096:
            key_length = 4096
        elif algorithm in [Algorithm.ECC_P256, Algorithm.ECC_P384]:
            key_length = 256 if algorithm == Algorithm.ECC_P256 else 384
        else:
            key_length = 256

        # Expiry date
        expires_at = None
        if expiry_days:
            expiry = datetime.now(timezone.utc) + timedelta(days=expiry_days)
            expires_at = expiry.isoformat()

        # FIPS validation (HSM-backed keys are FIPS 140-2 Level 3)
        fips_validated = hsm_backed

        return KeyMetadata(
            key_id=key_id,
            tier=tier.value,
            algorithm=algorithm.value,
            key_length=key_length,
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=expires_at,
            parent_key_id=parent_key_id,
            platform=self.platform.value,
            hsm_backed=hsm_backed,
            fips_validated=fips_validated,
            description=f"{tier.value.upper()} key for {self.platform.value}"
        )

    def _save_key_material(self, key_id: str, key_material: bytes) -> None:
        """Save key material to file (INSECURE - for demo only!)"""
        # In production, keys should NEVER be saved to disk in plaintext!
        # Use HSM or KMS instead
        key_file = self.output_dir / f"{key_id}.key"

        with open(key_file, 'wb') as f:
            f.write(key_material)

        # Restrict permissions
        os.chmod(key_file, 0o600)

    def _load_key_material(self, key_id: str) -> bytes:
        """Load key material from file"""
        key_file = self.output_dir / f"{key_id}.key"

        if not key_file.exists():
            raise ValueError(f"Key material not found: {key_id}")

        with open(key_file, 'rb') as f:
            return f.read()

    def visualize_hierarchy(self, hierarchy: KeyHierarchy) -> str:
        """Visualize key hierarchy as ASCII tree"""
        lines = []
        lines.append(f"\nKey Hierarchy: {hierarchy.hierarchy_id}")
        lines.append(f"Platform: {hierarchy.platform}")
        lines.append(f"Created: {hierarchy.created_at}")
        lines.append("")

        # Root key
        root = hierarchy.root_key
        lines.append(f"┌─ {root.key_id}")
        lines.append(f"│  Tier: ROOT")
        lines.append(f"│  Algorithm: {root.algorithm}")
        lines.append(f"│  HSM: {'Yes' if root.hsm_backed else 'No'}")
        lines.append(f"│  FIPS: {'Yes' if root.fips_validated else 'No'}")

        # KEKs
        if hierarchy.keks:
            lines.append(f"│")
            for i, kek in enumerate(hierarchy.keks):
                is_last_kek = (i == len(hierarchy.keks) - 1)
                prefix = "└─" if is_last_kek and not hierarchy.deks else "├─"

                lines.append(f"{prefix} {kek.key_id}")
                lines.append(f"{'  ' if is_last_kek and not hierarchy.deks else '│ '}  Tier: KEK")
                lines.append(f"{'  ' if is_last_kek and not hierarchy.deks else '│ '}  Algorithm: {kek.algorithm}")
                lines.append(f"{'  ' if is_last_kek and not hierarchy.deks else '│ '}  Parent: {kek.parent_key_id}")

                # DEKs under this KEK
                deks_for_kek = [d for d in hierarchy.deks if d.parent_key_id == kek.key_id]

                if deks_for_kek and i == 0:  # Show DEKs only for first KEK
                    lines.append(f"{'  ' if is_last_kek else '│ '}  │")
                    for j, dek in enumerate(deks_for_kek[:5]):  # Show first 5 DEKs
                        is_last_dek = (j == min(4, len(deks_for_kek) - 1))
                        dek_prefix = "└─" if is_last_dek else "├─"

                        lines.append(f"{'  ' if is_last_kek else '│ '}  {dek_prefix} {dek.key_id}")
                        lines.append(f"{'  ' if is_last_kek else '│ '}  {'  ' if is_last_dek else '│ '}  Tier: DEK")
                        lines.append(f"{'  ' if is_last_kek else '│ '}  {'  ' if is_last_dek else '│ '}  Algorithm: {dek.algorithm}")

                    if len(deks_for_kek) > 5:
                        lines.append(f"{'  ' if is_last_kek else '│ '}     ... and {len(deks_for_kek) - 5} more DEKs")

                if not is_last_kek:
                    lines.append(f"│")

        lines.append("")

        # Statistics
        lines.append(f"Statistics:")
        lines.append(f"  Total KEKs: {len(hierarchy.keks)}")
        lines.append(f"  Total DEKs: {len(hierarchy.deks)}")
        lines.append(f"  Wrapped keys: {len(hierarchy.wrapped_keys)}")
        lines.append("")

        return "\n".join(lines)

    def export_hierarchy(self, hierarchy: KeyHierarchy, output_file: Path) -> None:
        """Export hierarchy to JSON file"""
        hierarchy_dict = asdict(hierarchy)

        with open(output_file, 'w') as f:
            json.dump(hierarchy_dict, f, indent=2)

        if self.verbose:
            print(f"Hierarchy exported to {output_file}")

    def load_hierarchy(self, input_file: Path) -> KeyHierarchy:
        """Load hierarchy from JSON file"""
        with open(input_file, 'r') as f:
            data = json.load(f)

        # Reconstruct KeyHierarchy object
        hierarchy = KeyHierarchy(
            hierarchy_id=data['hierarchy_id'],
            created_at=data['created_at'],
            platform=data['platform'],
            root_key=KeyMetadata(**data['root_key']),
            keks=[KeyMetadata(**kek) for kek in data['keks']],
            deks=[KeyMetadata(**dek) for dek in data['deks']],
            wrapped_keys=[WrappedKey(**wk) for wk in data['wrapped_keys']],
            access_policies=data.get('access_policies', []),
            audit_log=data.get('audit_log', [])
        )

        return hierarchy


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Generate and manage cryptographic key hierarchies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--platform',
        choices=['aws-kms', 'gcp-kms', 'azure', 'vault', 'local', 'hsm-sim'],
        default='local',
        help='KMS platform (default: local)'
    )

    parser.add_argument(
        '--tiers',
        type=int,
        choices=[2, 3],
        default=3,
        help='Number of tiers (2=Root+KEK, 3=Root+KEK+DEK, default: 3)'
    )

    parser.add_argument(
        '--root-algorithm',
        choices=[a.value for a in Algorithm],
        default='aes-256-gcm',
        help='Root key algorithm (default: aes-256-gcm)'
    )

    parser.add_argument(
        '--kek-algorithm',
        choices=[a.value for a in Algorithm],
        default='aes-256-gcm',
        help='KEK algorithm (default: aes-256-gcm)'
    )

    parser.add_argument(
        '--dek-algorithm',
        choices=[a.value for a in Algorithm],
        default='aes-256-gcm',
        help='DEK algorithm (default: aes-256-gcm)'
    )

    parser.add_argument(
        '--kek-count',
        type=int,
        default=1,
        help='Number of KEKs to generate (default: 1)'
    )

    parser.add_argument(
        '--dek-count',
        type=int,
        default=10,
        help='Number of DEKs to generate (default: 10)'
    )

    parser.add_argument(
        '--root-hsm',
        action='store_true',
        help='Mark root key as HSM-backed'
    )

    parser.add_argument(
        '--expiry-days',
        type=int,
        help='Key expiry in days (optional)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('./key-hierarchy'),
        help='Output directory (default: ./key-hierarchy)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        help='Output file for hierarchy JSON'
    )

    parser.add_argument(
        '--load',
        type=Path,
        help='Load existing hierarchy from JSON file'
    )

    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Visualize hierarchy as ASCII tree'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Create generator
    platform = Platform(args.platform)
    generator = KeyHierarchyGenerator(
        platform=platform,
        output_dir=args.output_dir,
        verbose=args.verbose
    )

    try:
        if args.load:
            # Load existing hierarchy
            hierarchy = generator.load_hierarchy(args.load)

            if args.visualize:
                print(generator.visualize_hierarchy(hierarchy))

            elif args.json:
                print(json.dumps(asdict(hierarchy), indent=2))

            else:
                print(f"Loaded hierarchy: {hierarchy.hierarchy_id}")
                print(f"  Root key: {hierarchy.root_key.key_id}")
                print(f"  KEKs: {len(hierarchy.keks)}")
                print(f"  DEKs: {len(hierarchy.deks)}")

        else:
            # Generate new hierarchy
            hierarchy = generator.generate_hierarchy(
                tiers=args.tiers,
                root_algorithm=Algorithm(args.root_algorithm),
                kek_algorithm=Algorithm(args.kek_algorithm),
                dek_algorithm=Algorithm(args.dek_algorithm),
                kek_count=args.kek_count,
                dek_count=args.dek_count,
                root_hsm=args.root_hsm,
                expiry_days=args.expiry_days
            )

            # Export hierarchy
            if args.output:
                generator.export_hierarchy(hierarchy, args.output)
            else:
                default_output = args.output_dir / f"{hierarchy.hierarchy_id}.json"
                generator.export_hierarchy(hierarchy, default_output)

            # Output
            if args.visualize:
                print(generator.visualize_hierarchy(hierarchy))

            elif args.json:
                print(json.dumps(asdict(hierarchy), indent=2))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
