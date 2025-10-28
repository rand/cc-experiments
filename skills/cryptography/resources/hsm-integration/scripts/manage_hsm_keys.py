#!/usr/bin/env python3
"""
HSM Key Management Tool

Generate, list, manage, backup, restore, and rotate keys in HSM.
Supports multiple PKCS#11 vendors and handles sessions securely.

Supports: SoftHSM, Thales Luna, AWS CloudHSM, YubiHSM
"""

import argparse
import base64
import getpass
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import PyKCS11
    from PyKCS11 import PyKCS11Error
    PKCS11_AVAILABLE = True
except ImportError:
    PKCS11_AVAILABLE = False
    print("Error: PyKCS11 not available. Install with: pip install PyKCS11", file=sys.stderr)
    sys.exit(1)


class KeyType(Enum):
    """Supported key types."""
    RSA = "rsa"
    EC = "ec"
    AES = "aes"
    GENERIC = "generic"


class KeyUsage(Enum):
    """Key usage flags."""
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    SIGN = "sign"
    VERIFY = "verify"
    WRAP = "wrap"
    UNWRAP = "unwrap"
    DERIVE = "derive"


@dataclass
class KeyInfo:
    """Key information."""
    handle: int
    label: str
    key_type: str
    key_id: Optional[bytes] = None
    modulus_bits: Optional[int] = None
    curve: Optional[str] = None
    sensitive: bool = False
    extractable: bool = False
    private: bool = False
    token: bool = False
    encrypt: bool = False
    decrypt: bool = False
    sign: bool = False
    verify: bool = False
    wrap: bool = False
    unwrap: bool = False
    derive: bool = False
    created: Optional[str] = None
    modified: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if data['key_id']:
            data['key_id'] = base64.b64encode(data['key_id']).decode()
        return data


@dataclass
class KeyGenerationParams:
    """Key generation parameters."""
    key_type: KeyType
    label: str
    key_id: Optional[bytes] = None
    token: bool = True
    sensitive: bool = True
    extractable: bool = False
    modulus_bits: int = 2048
    curve: str = "secp256r1"
    key_size: int = 32
    usages: List[KeyUsage] = None

    def __post_init__(self):
        """Initialize default usages."""
        if self.usages is None:
            if self.key_type in [KeyType.RSA, KeyType.EC]:
                self.usages = [KeyUsage.SIGN, KeyUsage.VERIFY]
            else:
                self.usages = [KeyUsage.ENCRYPT, KeyUsage.DECRYPT]


class HSMKeyManager:
    """HSM key management operations."""

    # EC curve OIDs
    CURVES = {
        "secp256r1": bytes([0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01, 0x07]),  # P-256
        "secp384r1": bytes([0x06, 0x05, 0x2b, 0x81, 0x04, 0x00, 0x22]),  # P-384
        "secp521r1": bytes([0x06, 0x05, 0x2b, 0x81, 0x04, 0x00, 0x23]),  # P-521
    }

    def __init__(self, library_path: str, slot: int, pin: Optional[str] = None):
        """Initialize key manager."""
        self.library_path = library_path
        self.slot = slot
        self.pin = pin
        self.pkcs11 = None
        self.session = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def connect(self):
        """Connect to HSM."""
        try:
            self.pkcs11 = PyKCS11.PyKCS11Lib()
            self.pkcs11.load(self.library_path)

            # Open session
            self.session = self.pkcs11.openSession(
                self.slot,
                PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION
            )

            # Login if PIN provided
            if self.pin:
                self.session.login(self.pin)

        except PyKCS11Error as e:
            raise Exception(f"Failed to connect to HSM: {e}")

    def disconnect(self):
        """Disconnect from HSM."""
        if self.session:
            try:
                if self.pin:
                    self.session.logout()
                self.session.closeSession()
            except:
                pass

    def generate_key(self, params: KeyGenerationParams) -> KeyInfo:
        """Generate key in HSM."""
        if not self.session:
            raise Exception("Not connected to HSM")

        if params.key_type == KeyType.RSA:
            return self._generate_rsa_key(params)
        elif params.key_type == KeyType.EC:
            return self._generate_ec_key(params)
        elif params.key_type == KeyType.AES:
            return self._generate_aes_key(params)
        elif params.key_type == KeyType.GENERIC:
            return self._generate_generic_key(params)
        else:
            raise ValueError(f"Unsupported key type: {params.key_type}")

    def _generate_rsa_key(self, params: KeyGenerationParams) -> KeyInfo:
        """Generate RSA key pair."""
        # Convert usages to PKCS#11 attributes
        public_encrypt = KeyUsage.ENCRYPT in params.usages
        public_verify = KeyUsage.VERIFY in params.usages
        public_wrap = KeyUsage.WRAP in params.usages
        private_decrypt = KeyUsage.DECRYPT in params.usages
        private_sign = KeyUsage.SIGN in params.usages
        private_unwrap = KeyUsage.UNWRAP in params.usages

        # Public key template
        public_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
            (PyKCS11.CKA_TOKEN, params.token),
            (PyKCS11.CKA_ENCRYPT, public_encrypt),
            (PyKCS11.CKA_VERIFY, public_verify),
            (PyKCS11.CKA_WRAP, public_wrap),
            (PyKCS11.CKA_MODULUS_BITS, params.modulus_bits),
            (PyKCS11.CKA_PUBLIC_EXPONENT, (0x01, 0x00, 0x01)),  # 65537
            (PyKCS11.CKA_LABEL, params.label + " (Public)"),
        ]

        if params.key_id:
            public_template.append((PyKCS11.CKA_ID, params.key_id))

        # Private key template
        private_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
            (PyKCS11.CKA_TOKEN, params.token),
            (PyKCS11.CKA_PRIVATE, True),
            (PyKCS11.CKA_SENSITIVE, params.sensitive),
            (PyKCS11.CKA_EXTRACTABLE, params.extractable),
            (PyKCS11.CKA_DECRYPT, private_decrypt),
            (PyKCS11.CKA_SIGN, private_sign),
            (PyKCS11.CKA_UNWRAP, private_unwrap),
            (PyKCS11.CKA_LABEL, params.label + " (Private)"),
        ]

        if params.key_id:
            private_template.append((PyKCS11.CKA_ID, params.key_id))

        # Generate key pair
        try:
            (public_key, private_key) = self.session.generateKeyPair(
                public_template,
                private_template,
                mecha=PyKCS11.MechanismRSAPKCSKeyPairGen
            )

            # Get key info
            return self._get_key_info(private_key)

        except PyKCS11Error as e:
            raise Exception(f"Failed to generate RSA key: {e}")

    def _generate_ec_key(self, params: KeyGenerationParams) -> KeyInfo:
        """Generate EC key pair."""
        # Get curve OID
        if params.curve not in self.CURVES:
            raise ValueError(f"Unsupported curve: {params.curve}")

        curve_oid = self.CURVES[params.curve]

        # Convert usages
        public_verify = KeyUsage.VERIFY in params.usages
        private_sign = KeyUsage.SIGN in params.usages
        private_derive = KeyUsage.DERIVE in params.usages

        # Public key template
        public_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_EC),
            (PyKCS11.CKA_TOKEN, params.token),
            (PyKCS11.CKA_VERIFY, public_verify),
            (PyKCS11.CKA_EC_PARAMS, curve_oid),
            (PyKCS11.CKA_LABEL, params.label + " (Public)"),
        ]

        if params.key_id:
            public_template.append((PyKCS11.CKA_ID, params.key_id))

        # Private key template
        private_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_EC),
            (PyKCS11.CKA_TOKEN, params.token),
            (PyKCS11.CKA_PRIVATE, True),
            (PyKCS11.CKA_SENSITIVE, params.sensitive),
            (PyKCS11.CKA_EXTRACTABLE, params.extractable),
            (PyKCS11.CKA_SIGN, private_sign),
            (PyKCS11.CKA_DERIVE, private_derive),
            (PyKCS11.CKA_LABEL, params.label + " (Private)"),
        ]

        if params.key_id:
            private_template.append((PyKCS11.CKA_ID, params.key_id))

        # Generate key pair
        try:
            (public_key, private_key) = self.session.generateKeyPair(
                public_template,
                private_template,
                mecha=PyKCS11.MechanismECKeyPairGen
            )

            return self._get_key_info(private_key)

        except PyKCS11Error as e:
            raise Exception(f"Failed to generate EC key: {e}")

    def _generate_aes_key(self, params: KeyGenerationParams) -> KeyInfo:
        """Generate AES key."""
        # Convert usages
        encrypt = KeyUsage.ENCRYPT in params.usages
        decrypt = KeyUsage.DECRYPT in params.usages
        wrap = KeyUsage.WRAP in params.usages
        unwrap = KeyUsage.UNWRAP in params.usages

        # Key template
        template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_AES),
            (PyKCS11.CKA_TOKEN, params.token),
            (PyKCS11.CKA_PRIVATE, True),
            (PyKCS11.CKA_SENSITIVE, params.sensitive),
            (PyKCS11.CKA_EXTRACTABLE, params.extractable),
            (PyKCS11.CKA_ENCRYPT, encrypt),
            (PyKCS11.CKA_DECRYPT, decrypt),
            (PyKCS11.CKA_WRAP, wrap),
            (PyKCS11.CKA_UNWRAP, unwrap),
            (PyKCS11.CKA_VALUE_LEN, params.key_size),
            (PyKCS11.CKA_LABEL, params.label),
        ]

        if params.key_id:
            template.append((PyKCS11.CKA_ID, params.key_id))

        # Generate key
        try:
            key = self.session.generateKey(template, mecha=PyKCS11.MechanismAESKeyGen)
            return self._get_key_info(key)

        except PyKCS11Error as e:
            raise Exception(f"Failed to generate AES key: {e}")

    def _generate_generic_key(self, params: KeyGenerationParams) -> KeyInfo:
        """Generate generic secret key."""
        # Convert usages
        encrypt = KeyUsage.ENCRYPT in params.usages
        decrypt = KeyUsage.DECRYPT in params.usages
        sign = KeyUsage.SIGN in params.usages
        verify = KeyUsage.VERIFY in params.usages

        # Key template
        template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_GENERIC_SECRET),
            (PyKCS11.CKA_TOKEN, params.token),
            (PyKCS11.CKA_PRIVATE, True),
            (PyKCS11.CKA_SENSITIVE, params.sensitive),
            (PyKCS11.CKA_EXTRACTABLE, params.extractable),
            (PyKCS11.CKA_ENCRYPT, encrypt),
            (PyKCS11.CKA_DECRYPT, decrypt),
            (PyKCS11.CKA_SIGN, sign),
            (PyKCS11.CKA_VERIFY, verify),
            (PyKCS11.CKA_VALUE_LEN, params.key_size),
            (PyKCS11.CKA_LABEL, params.label),
        ]

        if params.key_id:
            template.append((PyKCS11.CKA_ID, params.key_id))

        # Generate key
        try:
            key = self.session.generateKey(template, mecha=PyKCS11.MechanismGenericSecretKeyGen)
            return self._get_key_info(key)

        except PyKCS11Error as e:
            raise Exception(f"Failed to generate generic key: {e}")

    def list_keys(
        self,
        key_class: Optional[int] = None,
        label_pattern: Optional[str] = None
    ) -> List[KeyInfo]:
        """List keys in HSM."""
        if not self.session:
            raise Exception("Not connected to HSM")

        # Build search template
        template = []
        if key_class:
            template.append((PyKCS11.CKA_CLASS, key_class))

        # Find objects
        try:
            objects = self.session.findObjects(template if template else [])

            # Get info for each key
            keys = []
            for obj in objects:
                try:
                    key_info = self._get_key_info(obj)

                    # Filter by label pattern
                    if label_pattern:
                        if label_pattern.lower() not in key_info.label.lower():
                            continue

                    keys.append(key_info)

                except Exception as e:
                    print(f"Warning: Could not get info for object {obj}: {e}", file=sys.stderr)

            return keys

        except PyKCS11Error as e:
            raise Exception(f"Failed to list keys: {e}")

    def _get_key_info(self, handle: int) -> KeyInfo:
        """Get key information."""
        # Try to get all possible attributes
        attr_list = [
            PyKCS11.CKA_CLASS,
            PyKCS11.CKA_KEY_TYPE,
            PyKCS11.CKA_LABEL,
            PyKCS11.CKA_ID,
            PyKCS11.CKA_TOKEN,
            PyKCS11.CKA_PRIVATE,
            PyKCS11.CKA_SENSITIVE,
            PyKCS11.CKA_EXTRACTABLE,
            PyKCS11.CKA_ENCRYPT,
            PyKCS11.CKA_DECRYPT,
            PyKCS11.CKA_SIGN,
            PyKCS11.CKA_VERIFY,
            PyKCS11.CKA_WRAP,
            PyKCS11.CKA_UNWRAP,
            PyKCS11.CKA_DERIVE,
        ]

        try:
            attrs = self.session.getAttributeValue(handle, attr_list, allAsBinary=True)
        except PyKCS11Error:
            # Try with minimal attributes
            attr_list = [PyKCS11.CKA_CLASS, PyKCS11.CKA_LABEL]
            attrs = self.session.getAttributeValue(handle, attr_list, allAsBinary=True)

        # Parse attributes
        key_class = attrs[0] if len(attrs) > 0 else None
        key_type_raw = attrs[1] if len(attrs) > 1 else None
        label_raw = attrs[2] if len(attrs) > 2 else b""
        key_id = attrs[3] if len(attrs) > 3 else None

        # Convert label
        label = label_raw.decode('utf-8', errors='ignore').rstrip('\x00') if label_raw else "Unknown"

        # Determine key type
        key_type_map = {
            PyKCS11.CKK_RSA: "RSA",
            PyKCS11.CKK_EC: "EC",
            PyKCS11.CKK_AES: "AES",
            PyKCS11.CKK_GENERIC_SECRET: "Generic",
        }
        key_type = key_type_map.get(key_type_raw, f"Unknown({key_type_raw})")

        # Create KeyInfo
        info = KeyInfo(
            handle=handle,
            label=label,
            key_type=key_type,
            key_id=key_id if isinstance(key_id, bytes) else None,
        )

        # Set boolean attributes
        if len(attrs) > 4:
            info.token = bool(attrs[4])
        if len(attrs) > 5:
            info.private = bool(attrs[5])
        if len(attrs) > 6:
            info.sensitive = bool(attrs[6])
        if len(attrs) > 7:
            info.extractable = bool(attrs[7])
        if len(attrs) > 8:
            info.encrypt = bool(attrs[8])
        if len(attrs) > 9:
            info.decrypt = bool(attrs[9])
        if len(attrs) > 10:
            info.sign = bool(attrs[10])
        if len(attrs) > 11:
            info.verify = bool(attrs[11])
        if len(attrs) > 12:
            info.wrap = bool(attrs[12])
        if len(attrs) > 13:
            info.unwrap = bool(attrs[13])
        if len(attrs) > 14:
            info.derive = bool(attrs[14])

        # Get RSA modulus size if applicable
        if key_type_raw == PyKCS11.CKK_RSA:
            try:
                modulus_attrs = self.session.getAttributeValue(handle, [PyKCS11.CKA_MODULUS])
                if modulus_attrs and modulus_attrs[0]:
                    info.modulus_bits = len(modulus_attrs[0]) * 8
            except:
                pass

        return info

    def delete_key(self, handle: int) -> bool:
        """Delete key from HSM."""
        if not self.session:
            raise Exception("Not connected to HSM")

        try:
            self.session.destroyObject(handle)
            return True
        except PyKCS11Error as e:
            raise Exception(f"Failed to delete key: {e}")

    def set_attributes(self, handle: int, attributes: Dict[str, Any]) -> bool:
        """Set key attributes."""
        if not self.session:
            raise Exception("Not connected to HSM")

        # Build attribute template
        template = []

        attr_map = {
            "label": PyKCS11.CKA_LABEL,
            "encrypt": PyKCS11.CKA_ENCRYPT,
            "decrypt": PyKCS11.CKA_DECRYPT,
            "sign": PyKCS11.CKA_SIGN,
            "verify": PyKCS11.CKA_VERIFY,
            "wrap": PyKCS11.CKA_WRAP,
            "unwrap": PyKCS11.CKA_UNWRAP,
        }

        for name, value in attributes.items():
            if name in attr_map:
                template.append((attr_map[name], value))

        if not template:
            raise ValueError("No valid attributes to set")

        try:
            self.session.setAttributeValue(handle, template)
            return True
        except PyKCS11Error as e:
            raise Exception(f"Failed to set attributes: {e}")

    def backup_key(self, handle: int, wrap_key_handle: int, output_file: str) -> bool:
        """Backup key by wrapping with another key."""
        if not self.session:
            raise Exception("Not connected to HSM")

        try:
            # Wrap key
            wrapped = self.session.wrapKey(
                wrap_key_handle,
                handle,
                PyKCS11.Mechanism(PyKCS11.CKM_AES_KEY_WRAP, None)
            )

            # Get key info for metadata
            key_info = self._get_key_info(handle)

            # Create backup data
            backup_data = {
                "version": 1,
                "timestamp": datetime.utcnow().isoformat(),
                "key_info": key_info.to_dict(),
                "wrapped_key": base64.b64encode(bytes(wrapped)).decode(),
            }

            # Write to file
            with open(output_file, 'w') as f:
                json.dump(backup_data, f, indent=2)

            return True

        except PyKCS11Error as e:
            raise Exception(f"Failed to backup key: {e}")

    def restore_key(self, input_file: str, unwrap_key_handle: int) -> KeyInfo:
        """Restore key from backup."""
        if not self.session:
            raise Exception("Not connected to HSM")

        try:
            # Read backup file
            with open(input_file) as f:
                backup_data = json.load(f)

            # Extract wrapped key
            wrapped_key = base64.b64decode(backup_data["wrapped_key"])

            # Get original key info
            key_info = backup_data["key_info"]

            # Build unwrap template
            template = [
                (PyKCS11.CKA_CLASS, self._get_key_class_from_type(key_info["key_type"])),
                (PyKCS11.CKA_TOKEN, key_info["token"]),
                (PyKCS11.CKA_PRIVATE, key_info["private"]),
                (PyKCS11.CKA_SENSITIVE, key_info["sensitive"]),
                (PyKCS11.CKA_EXTRACTABLE, key_info["extractable"]),
                (PyKCS11.CKA_LABEL, key_info["label"] + " (Restored)"),
            ]

            # Add usage attributes
            if key_info["encrypt"]:
                template.append((PyKCS11.CKA_ENCRYPT, True))
            if key_info["decrypt"]:
                template.append((PyKCS11.CKA_DECRYPT, True))
            if key_info["sign"]:
                template.append((PyKCS11.CKA_SIGN, True))
            if key_info["verify"]:
                template.append((PyKCS11.CKA_VERIFY, True))
            if key_info["wrap"]:
                template.append((PyKCS11.CKA_WRAP, True))
            if key_info["unwrap"]:
                template.append((PyKCS11.CKA_UNWRAP, True))

            # Unwrap key
            restored_handle = self.session.unwrapKey(
                unwrap_key_handle,
                wrapped_key,
                template,
                PyKCS11.Mechanism(PyKCS11.CKM_AES_KEY_WRAP, None)
            )

            return self._get_key_info(restored_handle)

        except Exception as e:
            raise Exception(f"Failed to restore key: {e}")

    def _get_key_class_from_type(self, key_type: str) -> int:
        """Get PKCS#11 key class from type string."""
        if key_type in ["RSA", "EC"]:
            return PyKCS11.CKO_PRIVATE_KEY
        else:
            return PyKCS11.CKO_SECRET_KEY

    def rotate_key(self, old_label: str, new_label: str, params: KeyGenerationParams) -> Tuple[KeyInfo, List[int]]:
        """Rotate key: generate new key and mark old key for retirement."""
        if not self.session:
            raise Exception("Not connected to HSM")

        # Find old key(s)
        old_keys = self.list_keys(label_pattern=old_label)
        if not old_keys:
            raise Exception(f"Old key not found: {old_label}")

        # Generate new key
        params.label = new_label
        new_key = self.generate_key(params)

        # Mark old keys as decrypt/verify only (disable encryption/signing)
        old_handles = []
        for old_key in old_keys:
            if old_key.label == old_label:
                try:
                    # Update label to mark as retired
                    retired_label = f"{old_label}-retired-{datetime.utcnow().strftime('%Y%m%d')}"

                    self.set_attributes(old_key.handle, {
                        "label": retired_label,
                        "encrypt": False,
                        "sign": False,
                    })

                    old_handles.append(old_key.handle)

                except Exception as e:
                    print(f"Warning: Could not retire key {old_key.handle}: {e}", file=sys.stderr)

        return new_key, old_handles


def format_key_table(keys: List[KeyInfo]) -> str:
    """Format keys as text table."""
    if not keys:
        return "No keys found."

    lines = []
    lines.append(f"{'Handle':<10} {'Label':<30} {'Type':<10} {'Size':<10} {'Usage':<30}")
    lines.append("-" * 100)

    for key in keys:
        # Format usage
        usage_parts = []
        if key.encrypt:
            usage_parts.append("E")
        if key.decrypt:
            usage_parts.append("D")
        if key.sign:
            usage_parts.append("S")
        if key.verify:
            usage_parts.append("V")
        if key.wrap:
            usage_parts.append("W")
        if key.unwrap:
            usage_parts.append("U")
        if key.derive:
            usage_parts.append("Der")

        usage = ",".join(usage_parts)

        # Format size
        if key.modulus_bits:
            size = f"{key.modulus_bits} bits"
        elif key.curve:
            size = key.curve
        else:
            size = "-"

        lines.append(f"{key.handle:<10} {key.label:<30} {key.key_type:<10} {size:<10} {usage:<30}")

    return "\n".join(lines)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="HSM key management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all keys
  %(prog)s --library /usr/lib/softhsm/libsofthsm2.so --slot 0 --pin 1234 list

  # Generate RSA-2048 key
  %(prog)s --library /usr/lib/softhsm/libsofthsm2.so --slot 0 --pin 1234 \\
    generate --type rsa --label "Test Key" --size 2048

  # Generate EC P-256 key
  %(prog)s --library /usr/lib/softhsm/libsofthsm2.so --slot 0 --pin 1234 \\
    generate --type ec --label "EC Key" --curve secp256r1

  # Delete key
  %(prog)s --library /usr/lib/softhsm/libsofthsm2.so --slot 0 --pin 1234 \\
    delete --handle 12345

  # Backup key
  %(prog)s --library /usr/lib/softhsm/libsofthsm2.so --slot 0 --pin 1234 \\
    backup --handle 12345 --wrap-key 67890 --output backup.json

  # Rotate key
  %(prog)s --library /usr/lib/softhsm/libsofthsm2.so --slot 0 --pin 1234 \\
    rotate --old-label "Old Key" --new-label "New Key" --type rsa
        """
    )

    parser.add_argument(
        "--library",
        required=True,
        help="Path to PKCS#11 library"
    )

    parser.add_argument(
        "--slot",
        type=int,
        default=0,
        help="Slot number (default: 0)"
    )

    parser.add_argument(
        "--pin",
        help="User PIN (will prompt if not provided)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List command
    list_parser = subparsers.add_parser("list", help="List keys")
    list_parser.add_argument(
        "--class",
        choices=["public", "private", "secret"],
        help="Filter by key class"
    )
    list_parser.add_argument(
        "--label",
        help="Filter by label pattern"
    )

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate key")
    gen_parser.add_argument(
        "--type",
        required=True,
        choices=["rsa", "ec", "aes", "generic"],
        help="Key type"
    )
    gen_parser.add_argument(
        "--label",
        required=True,
        help="Key label"
    )
    gen_parser.add_argument(
        "--size",
        type=int,
        help="Key size (RSA modulus bits or AES key bytes)"
    )
    gen_parser.add_argument(
        "--curve",
        choices=["secp256r1", "secp384r1", "secp521r1"],
        default="secp256r1",
        help="EC curve (default: secp256r1)"
    )
    gen_parser.add_argument(
        "--usage",
        action="append",
        choices=["encrypt", "decrypt", "sign", "verify", "wrap", "unwrap", "derive"],
        help="Key usage (can specify multiple)"
    )
    gen_parser.add_argument(
        "--extractable",
        action="store_true",
        help="Make key extractable (not recommended)"
    )
    gen_parser.add_argument(
        "--session-only",
        action="store_true",
        help="Create session key (not persistent)"
    )

    # Delete command
    del_parser = subparsers.add_parser("delete", help="Delete key")
    del_parser.add_argument(
        "--handle",
        type=int,
        required=True,
        help="Key handle"
    )

    # Set attributes command
    attr_parser = subparsers.add_parser("set-attributes", help="Set key attributes")
    attr_parser.add_argument(
        "--handle",
        type=int,
        required=True,
        help="Key handle"
    )
    attr_parser.add_argument(
        "--label",
        help="New label"
    )
    attr_parser.add_argument(
        "--encrypt",
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Enable/disable encryption"
    )
    attr_parser.add_argument(
        "--decrypt",
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Enable/disable decryption"
    )

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Backup key")
    backup_parser.add_argument(
        "--handle",
        type=int,
        required=True,
        help="Key handle to backup"
    )
    backup_parser.add_argument(
        "--wrap-key",
        type=int,
        required=True,
        help="Wrapping key handle"
    )
    backup_parser.add_argument(
        "--output",
        required=True,
        help="Output file"
    )

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore key")
    restore_parser.add_argument(
        "--input",
        required=True,
        help="Backup file"
    )
    restore_parser.add_argument(
        "--unwrap-key",
        type=int,
        required=True,
        help="Unwrapping key handle"
    )

    # Rotate command
    rotate_parser = subparsers.add_parser("rotate", help="Rotate key")
    rotate_parser.add_argument(
        "--old-label",
        required=True,
        help="Old key label"
    )
    rotate_parser.add_argument(
        "--new-label",
        required=True,
        help="New key label"
    )
    rotate_parser.add_argument(
        "--type",
        required=True,
        choices=["rsa", "ec", "aes"],
        help="Key type"
    )
    rotate_parser.add_argument(
        "--size",
        type=int,
        help="Key size"
    )
    rotate_parser.add_argument(
        "--curve",
        choices=["secp256r1", "secp384r1", "secp521r1"],
        default="secp256r1",
        help="EC curve"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Get PIN if not provided
    pin = args.pin
    if not pin:
        pin = getpass.getpass("Enter PIN: ")

    # Execute command
    try:
        with HSMKeyManager(args.library, args.slot, pin) as manager:
            if args.command == "list":
                # Map class name to PKCS#11 constant
                key_class = None
                class_filter = getattr(args, 'class', None)
                if class_filter == "public":
                    key_class = PyKCS11.CKO_PUBLIC_KEY
                elif class_filter == "private":
                    key_class = PyKCS11.CKO_PRIVATE_KEY
                elif class_filter == "secret":
                    key_class = PyKCS11.CKO_SECRET_KEY

                keys = manager.list_keys(key_class=key_class, label_pattern=args.label)

                if args.json:
                    print(json.dumps([k.to_dict() for k in keys], indent=2))
                else:
                    print(format_key_table(keys))

            elif args.command == "generate":
                # Build parameters
                key_type = KeyType(args.type)

                # Parse usages
                usages = []
                if args.usage:
                    usages = [KeyUsage(u) for u in args.usage]

                params = KeyGenerationParams(
                    key_type=key_type,
                    label=args.label,
                    token=not args.session_only,
                    extractable=args.extractable,
                    usages=usages if usages else None,
                )

                # Set type-specific parameters
                if key_type == KeyType.RSA:
                    params.modulus_bits = args.size or 2048
                elif key_type == KeyType.EC:
                    params.curve = args.curve
                elif key_type in [KeyType.AES, KeyType.GENERIC]:
                    params.key_size = args.size or 32

                key_info = manager.generate_key(params)

                if args.json:
                    print(json.dumps(key_info.to_dict(), indent=2))
                else:
                    print(f"Generated key: {key_info.label}")
                    print(f"  Handle: {key_info.handle}")
                    print(f"  Type: {key_info.key_type}")
                    if key_info.modulus_bits:
                        print(f"  Size: {key_info.modulus_bits} bits")

            elif args.command == "delete":
                manager.delete_key(args.handle)
                print(f"Deleted key {args.handle}")

            elif args.command == "set-attributes":
                attributes = {}
                if args.label:
                    attributes["label"] = args.label
                if args.encrypt is not None:
                    attributes["encrypt"] = args.encrypt
                if args.decrypt is not None:
                    attributes["decrypt"] = args.decrypt

                manager.set_attributes(args.handle, attributes)
                print(f"Updated key {args.handle}")

            elif args.command == "backup":
                manager.backup_key(args.handle, args.wrap_key, args.output)
                print(f"Backed up key {args.handle} to {args.output}")

            elif args.command == "restore":
                key_info = manager.restore_key(args.input, args.unwrap_key)
                print(f"Restored key: {key_info.label} (handle: {key_info.handle})")

            elif args.command == "rotate":
                # Build parameters
                key_type = KeyType(args.type)
                params = KeyGenerationParams(
                    key_type=key_type,
                    label=args.new_label,
                )

                if key_type == KeyType.RSA:
                    params.modulus_bits = args.size or 2048
                elif key_type == KeyType.EC:
                    params.curve = args.curve
                elif key_type == KeyType.AES:
                    params.key_size = args.size or 32

                new_key, old_handles = manager.rotate_key(args.old_label, args.new_label, params)

                print(f"Rotated key: {args.old_label} → {args.new_label}")
                print(f"  New key handle: {new_key.handle}")
                print(f"  Retired keys: {', '.join(map(str, old_handles))}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
