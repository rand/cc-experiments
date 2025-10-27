#!/usr/bin/env python3
"""
Encryption Key Rotation Tool

Automated key rotation with zero-downtime using envelope encryption.
Supports multiple KMS backends (AWS KMS, local file-based).

Features:
- Generate new encryption keys
- Support multiple KMS backends (AWS KMS, local)
- Re-encrypt data with new key (envelope encryption)
- Rollback support
- Progress tracking
- Audit logging
- Zero-downtime rotation

Usage:
    ./rotate_keys.py --kms-backend aws-kms --key-id alias/db-key --json
    ./rotate_keys.py --kms-backend local --key-file keys/master.key --data-dir ./data
    ./rotate_keys.py --kms-backend aws-kms --region us-east-1 --dry-run
    ./rotate_keys.py --rollback --backup-dir ./backups/2025-10-27
"""

import argparse
import base64
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from enum import Enum
import secrets


class KMSBackend(Enum):
    """KMS backend types"""
    AWS_KMS = "aws-kms"
    LOCAL = "local"
    HASHICORP_VAULT = "vault"


class RotationStatus(Enum):
    """Rotation status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class EncryptionKey:
    """Encryption key metadata"""
    key_id: str
    key_type: str  # "DEK" (Data Encryption Key) or "KEK" (Key Encryption Key)
    algorithm: str
    key_length: int
    created_at: str
    version: int
    encrypted_key: Optional[str] = None  # For envelope encryption


@dataclass
class RotationProgress:
    """Rotation progress tracking"""
    total_items: int
    processed_items: int
    failed_items: int
    start_time: str
    status: str
    current_key: Optional[EncryptionKey] = None
    new_key: Optional[EncryptionKey] = None
    error: Optional[str] = None


@dataclass
class RotationResult:
    """Rotation result"""
    success: bool
    old_key_id: str
    new_key_id: str
    items_rotated: int
    duration_seconds: float
    backup_path: Optional[str] = None
    audit_log_path: Optional[str] = None


class AuditLogger:
    """Audit log for key rotation"""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.entries: List[Dict] = []

    def log(self, action: str, details: Dict, status: str = "success") -> None:
        """Log an action"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "status": status,
            "details": details
        }
        self.entries.append(entry)

    def write(self) -> None:
        """Write audit log to file"""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, 'w') as f:
            json.dump({
                "rotation_audit": self.entries,
                "summary": {
                    "total_actions": len(self.entries),
                    "failures": sum(1 for e in self.entries if e["status"] == "failure")
                }
            }, f, indent=2)


class LocalKMS:
    """Local file-based KMS (for testing/development)"""

    def __init__(self, key_file: Path):
        self.key_file = key_file

    def generate_data_key(self, algorithm: str = "AES-256-GCM") -> Tuple[bytes, bytes]:
        """Generate a new data encryption key (DEK)

        Returns:
            (plaintext_key, encrypted_key) - For envelope encryption pattern
        """
        # Generate random DEK
        plaintext_key = secrets.token_bytes(32)  # 256 bits

        # Load master key (KEK)
        if not self.key_file.exists():
            raise FileNotFoundError(f"Master key file not found: {self.key_file}")

        master_key = self.key_file.read_bytes()

        # Encrypt DEK with master key (simplified - in production use proper KDF)
        key_hash = hashlib.sha256(master_key).digest()
        encrypted_key = self._xor_encrypt(plaintext_key, key_hash)

        return plaintext_key, encrypted_key

    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt data encryption key (DEK)"""
        master_key = self.key_file.read_bytes()
        key_hash = hashlib.sha256(master_key).digest()
        plaintext_key = self._xor_encrypt(encrypted_key, key_hash)
        return plaintext_key

    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        """Simple XOR encryption (use AES-GCM in production)"""
        return bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))


class AWSKMSWrapper:
    """AWS KMS wrapper (requires boto3)"""

    def __init__(self, key_id: str, region: str = "us-east-1"):
        self.key_id = key_id
        self.region = region
        self._client = None

    @property
    def client(self):
        """Lazy load boto3 client"""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client('kms', region_name=self.region)
            except ImportError:
                raise ImportError("boto3 not installed. Install with: pip install boto3")
        return self._client

    def generate_data_key(self, algorithm: str = "AES-256") -> Tuple[bytes, bytes]:
        """Generate data encryption key using AWS KMS"""
        key_spec = "AES_256" if "256" in algorithm else "AES_128"

        response = self.client.generate_data_key(
            KeyId=self.key_id,
            KeySpec=key_spec
        )

        return response['Plaintext'], response['CiphertextBlob']

    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt data encryption key"""
        response = self.client.decrypt(
            CiphertextBlob=encrypted_key
        )
        return response['Plaintext']

    def create_key_alias(self, alias: str) -> str:
        """Create new KMS key with alias"""
        # Create new key
        response = self.client.create_key(
            Description=f"Encryption key rotated on {datetime.now().isoformat()}",
            KeyUsage='ENCRYPT_DECRYPT',
            Origin='AWS_KMS'
        )
        key_id = response['KeyMetadata']['KeyId']

        # Create alias
        self.client.create_alias(
            AliasName=alias if alias.startswith('alias/') else f'alias/{alias}',
            TargetKeyId=key_id
        )

        return key_id


class KeyRotator:
    """Handles key rotation with envelope encryption"""

    def __init__(self, kms_backend: str, audit_logger: AuditLogger, dry_run: bool = False):
        self.kms_backend = kms_backend
        self.audit_logger = audit_logger
        self.dry_run = dry_run
        self.kms = None

    def initialize_kms(self, **kms_config) -> None:
        """Initialize KMS backend"""
        if self.kms_backend == KMSBackend.LOCAL.value:
            key_file = Path(kms_config.get('key_file', 'master.key'))
            self.kms = LocalKMS(key_file)
        elif self.kms_backend == KMSBackend.AWS_KMS.value:
            key_id = kms_config.get('key_id')
            region = kms_config.get('region', 'us-east-1')
            if not key_id:
                raise ValueError("AWS KMS requires --key-id")
            self.kms = AWSKMSWrapper(key_id, region)
        else:
            raise ValueError(f"Unsupported KMS backend: {self.kms_backend}")

    def generate_new_key(self, version: int) -> EncryptionKey:
        """Generate new encryption key"""
        plaintext_key, encrypted_key = self.kms.generate_data_key()

        key = EncryptionKey(
            key_id=f"key-v{version}-{secrets.token_hex(8)}",
            key_type="DEK",
            algorithm="AES-256-GCM",
            key_length=256,
            created_at=datetime.now().isoformat(),
            version=version,
            encrypted_key=base64.b64encode(encrypted_key).decode()
        )

        self.audit_logger.log(
            "generate_key",
            {
                "key_id": key.key_id,
                "version": version,
                "algorithm": key.algorithm
            }
        )

        return key

    def encrypt_data(self, plaintext: bytes, key: bytes) -> bytes:
        """Encrypt data with AES-256-GCM (simplified)"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Return nonce + ciphertext
        return nonce + ciphertext

    def decrypt_data(self, ciphertext: bytes, key: bytes) -> bytes:
        """Decrypt data with AES-256-GCM"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # Extract nonce and ciphertext
        nonce = ciphertext[:12]
        actual_ciphertext = ciphertext[12:]

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, actual_ciphertext, None)
        return plaintext

    def rotate_file(self, file_path: Path, old_key: bytes, new_key: bytes) -> None:
        """Rotate encryption key for a single file"""
        try:
            # Read encrypted data
            encrypted_data = file_path.read_bytes()

            if self.dry_run:
                self.audit_logger.log(
                    "rotate_file",
                    {"file": str(file_path), "action": "dry_run"},
                    "success"
                )
                return

            # Decrypt with old key
            plaintext = self.decrypt_data(encrypted_data, old_key)

            # Re-encrypt with new key
            new_encrypted = self.encrypt_data(plaintext, new_key)

            # Backup original
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            shutil.copy2(file_path, backup_path)

            # Write new encrypted data
            file_path.write_bytes(new_encrypted)

            self.audit_logger.log(
                "rotate_file",
                {
                    "file": str(file_path),
                    "backup": str(backup_path),
                    "old_size": len(encrypted_data),
                    "new_size": len(new_encrypted)
                },
                "success"
            )

        except Exception as e:
            self.audit_logger.log(
                "rotate_file",
                {"file": str(file_path), "error": str(e)},
                "failure"
            )
            raise

    def rotate_directory(self, data_dir: Path, old_key: EncryptionKey,
                        new_key: EncryptionKey, pattern: str = "*.enc") -> RotationProgress:
        """Rotate all encrypted files in directory"""
        files = list(data_dir.rglob(pattern))

        progress = RotationProgress(
            total_items=len(files),
            processed_items=0,
            failed_items=0,
            start_time=datetime.now().isoformat(),
            status=RotationStatus.IN_PROGRESS.value,
            current_key=old_key,
            new_key=new_key
        )

        # Decrypt the keys
        old_dek = self.kms.decrypt_data_key(base64.b64decode(old_key.encrypted_key))
        new_dek = self.kms.decrypt_data_key(base64.b64decode(new_key.encrypted_key))

        for file_path in files:
            try:
                self.rotate_file(file_path, old_dek, new_dek)
                progress.processed_items += 1
            except Exception as e:
                progress.failed_items += 1
                progress.error = str(e)

        progress.status = (RotationStatus.COMPLETED.value
                          if progress.failed_items == 0
                          else RotationStatus.FAILED.value)

        return progress


def create_backup(data_dir: Path, backup_dir: Path) -> Path:
    """Create backup of data directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"backup_{timestamp}"

    shutil.copytree(data_dir, backup_path)
    return backup_path


def rollback_rotation(backup_path: Path, data_dir: Path) -> None:
    """Rollback to previous backup"""
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    # Remove current data
    shutil.rmtree(data_dir)

    # Restore from backup
    shutil.copytree(backup_path, data_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Rotate encryption keys with zero downtime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rotate keys using AWS KMS
  ./rotate_keys.py --kms-backend aws-kms --key-id alias/db-key --data-dir ./data

  # Rotate keys using local master key
  ./rotate_keys.py --kms-backend local --key-file master.key --data-dir ./data

  # Dry run (no actual changes)
  ./rotate_keys.py --kms-backend local --key-file master.key --dry-run

  # Rollback to previous backup
  ./rotate_keys.py --rollback --backup-dir ./backups/backup_20251027_120000

  # JSON output
  ./rotate_keys.py --kms-backend aws-kms --key-id alias/app-key --json

Key Rotation Process:
  1. Generate new data encryption key (DEK) using KMS
  2. Create backup of all encrypted data
  3. For each encrypted file:
     a. Decrypt with old DEK
     b. Re-encrypt with new DEK
     c. Write back to file
  4. Update key metadata
  5. Log audit trail

Exit codes:
  0 - Rotation successful
  1 - Rotation failed
  2 - Configuration error
        """
    )

    parser.add_argument("--kms-backend", choices=[b.value for b in KMSBackend],
                        help="KMS backend to use")
    parser.add_argument("--key-id", type=str,
                        help="KMS key ID or alias (AWS KMS)")
    parser.add_argument("--key-file", type=Path,
                        help="Master key file path (local KMS)")
    parser.add_argument("--region", type=str, default="us-east-1",
                        help="AWS region (default: us-east-1)")
    parser.add_argument("--data-dir", type=Path, default=Path("./data"),
                        help="Directory containing encrypted files")
    parser.add_argument("--pattern", type=str, default="*.enc",
                        help="File pattern to rotate (default: *.enc)")
    parser.add_argument("--backup-dir", type=Path, default=Path("./backups"),
                        help="Backup directory (default: ./backups)")
    parser.add_argument("--rollback", action="store_true",
                        help="Rollback to backup (use with --backup-dir)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate rotation without making changes")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--audit-log", type=Path,
                        help="Audit log path (default: auto-generated)")

    args = parser.parse_args()

    # Rollback mode
    if args.rollback:
        if not args.backup_dir or not args.data_dir:
            parser.error("--rollback requires --backup-dir and --data-dir")

        try:
            rollback_rotation(args.backup_dir, args.data_dir)
            print(f"Successfully rolled back to {args.backup_dir}")
            sys.exit(0)
        except Exception as e:
            print(f"Rollback failed: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate arguments for rotation
    if not args.kms_backend:
        parser.error("--kms-backend required (unless using --rollback)")

    if args.kms_backend == KMSBackend.LOCAL.value and not args.key_file:
        parser.error("--key-file required for local KMS backend")

    if args.kms_backend == KMSBackend.AWS_KMS.value and not args.key_id:
        parser.error("--key-id required for AWS KMS backend")

    # Setup audit logging
    audit_log_path = args.audit_log or Path(f"rotation_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    audit_logger = AuditLogger(audit_log_path)

    # Create rotator
    rotator = KeyRotator(args.kms_backend, audit_logger, dry_run=args.dry_run)

    try:
        # Initialize KMS
        kms_config = {
            'key_file': args.key_file,
            'key_id': args.key_id,
            'region': args.region
        }
        rotator.initialize_kms(**kms_config)

        audit_logger.log("initialize", {"kms_backend": args.kms_backend})

        # Create backup (unless dry-run)
        backup_path = None
        if not args.dry_run:
            backup_path = create_backup(args.data_dir, args.backup_dir)
            audit_logger.log("backup", {"backup_path": str(backup_path)})

        # Load current key (simplified - in production load from metadata)
        old_key = EncryptionKey(
            key_id="key-v1-current",
            key_type="DEK",
            algorithm="AES-256-GCM",
            key_length=256,
            created_at=(datetime.now()).isoformat(),
            version=1,
            encrypted_key=None  # Would load from metadata
        )

        # Generate new key
        new_key = rotator.generate_new_key(version=old_key.version + 1)

        # For demo purposes, generate dummy encrypted keys
        if old_key.encrypted_key is None:
            _, old_enc = rotator.kms.generate_data_key()
            old_key.encrypted_key = base64.b64encode(old_enc).decode()

        # Perform rotation
        start_time = datetime.now()
        progress = rotator.rotate_directory(args.data_dir, old_key, new_key, args.pattern)
        duration = (datetime.now() - start_time).total_seconds()

        # Create result
        result = RotationResult(
            success=progress.status == RotationStatus.COMPLETED.value,
            old_key_id=old_key.key_id,
            new_key_id=new_key.key_id,
            items_rotated=progress.processed_items,
            duration_seconds=duration,
            backup_path=str(backup_path) if backup_path else None,
            audit_log_path=str(audit_log_path)
        )

        # Write audit log
        audit_logger.log("rotation_complete", asdict(result))
        audit_logger.write()

        # Output results
        if args.json:
            print(json.dumps({
                "result": asdict(result),
                "progress": asdict(progress)
            }, indent=2))
        else:
            print("=" * 80)
            print("KEY ROTATION REPORT")
            print("=" * 80)
            print(f"Status: {'SUCCESS' if result.success else 'FAILED'}")
            print(f"Old Key: {result.old_key_id}")
            print(f"New Key: {result.new_key_id}")
            print(f"Items Rotated: {result.items_rotated}")
            print(f"Duration: {result.duration_seconds:.2f} seconds")
            if result.backup_path:
                print(f"Backup: {result.backup_path}")
            print(f"Audit Log: {result.audit_log_path}")
            if progress.failed_items > 0:
                print(f"\nWARNING: {progress.failed_items} items failed")

        sys.exit(0 if result.success else 1)

    except Exception as e:
        audit_logger.log("rotation_error", {"error": str(e)}, "failure")
        audit_logger.write()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
