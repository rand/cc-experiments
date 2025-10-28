#!/usr/bin/env python3
"""
Zero-Downtime Key Rotation Strategy

Demonstrates enterprise-grade key rotation patterns:
1. Dual-key transitional period (read old/new, write new)
2. Phased migration (batch re-encryption)
3. Rollback support
4. Progress tracking
5. Audit logging

Supports multiple KMS backends (AWS KMS, local).
"""

import base64
import json
import os
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class RotationPhase(Enum):
    """Key rotation phases"""
    NOT_STARTED = "not_started"
    DUAL_KEY = "dual_key"           # Both old and new keys active
    MIGRATION = "migration"         # Re-encrypting data
    NEW_KEY_ONLY = "new_key_only"  # Old key retired
    COMPLETED = "completed"


class KeyStatus(Enum):
    """Key lifecycle status"""
    ACTIVE = "active"
    ROTATING = "rotating"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass
class EncryptionKey:
    """Encryption key metadata"""
    key_id: str
    version: int
    algorithm: str
    key_length: int
    status: str
    created_at: str
    activated_at: Optional[str] = None
    deprecated_at: Optional[str] = None
    retired_at: Optional[str] = None
    encrypted_key: Optional[str] = None  # Encrypted by KMS


@dataclass
class RotationPlan:
    """Key rotation plan"""
    rotation_id: str
    old_key: EncryptionKey
    new_key: EncryptionKey
    phase: str
    start_time: str
    estimated_duration: int  # seconds
    items_to_migrate: int
    items_migrated: int
    batch_size: int
    parallel_workers: int


class KeyRotationManager:
    """Manages zero-downtime key rotation"""

    def __init__(self, kms_client, data_store):
        """
        Initialize rotation manager.

        Args:
            kms_client: KMS client (AWS KMS, local, etc.)
            data_store: Data storage backend
        """
        self.kms = kms_client
        self.data_store = data_store
        self.current_rotation: Optional[RotationPlan] = None
        self.audit_log: List[Dict] = []

    def generate_new_key(self) -> EncryptionKey:
        """Generate new encryption key via KMS"""
        # Generate Data Encryption Key
        plaintext_key, encrypted_key = self.kms.generate_data_key()

        # Get current max version
        current_keys = self.data_store.list_keys()
        max_version = max([k.version for k in current_keys], default=0)

        new_key = EncryptionKey(
            key_id=f"key-v{max_version + 1}-{os.urandom(4).hex()}",
            version=max_version + 1,
            algorithm="AES-256-GCM",
            key_length=256,
            status=KeyStatus.ROTATING.value,
            created_at=datetime.utcnow().isoformat(),
            encrypted_key=base64.b64encode(encrypted_key).decode()
        )

        self.data_store.save_key(new_key)
        self._log_audit("key_generated", {"key_id": new_key.key_id})

        return new_key

    def initiate_rotation(self, old_key_id: str, batch_size: int = 1000,
                         parallel_workers: int = 4) -> RotationPlan:
        """
        Initiate key rotation with dual-key period.

        Args:
            old_key_id: Current active key ID
            batch_size: Items to process per batch
            parallel_workers: Number of parallel workers

        Returns:
            Rotation plan
        """
        # Load old key
        old_key = self.data_store.get_key(old_key_id)
        if old_key.status != KeyStatus.ACTIVE.value:
            raise ValueError(f"Key {old_key_id} is not active")

        # Generate new key
        new_key = self.generate_new_key()

        # Count items to migrate
        items_count = self.data_store.count_encrypted_items(old_key.version)

        # Estimate duration (based on benchmark)
        items_per_second = 100  # Adjust based on actual performance
        estimated_duration = items_count // items_per_second

        # Create rotation plan
        plan = RotationPlan(
            rotation_id=f"rotation-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            old_key=old_key,
            new_key=new_key,
            phase=RotationPhase.DUAL_KEY.value,
            start_time=datetime.utcnow().isoformat(),
            estimated_duration=estimated_duration,
            items_to_migrate=items_count,
            items_migrated=0,
            batch_size=batch_size,
            parallel_workers=parallel_workers
        )

        self.current_rotation = plan
        self.data_store.save_rotation_plan(plan)

        # Update key statuses
        old_key.status = KeyStatus.ROTATING.value
        new_key.status = KeyStatus.ROTATING.value
        new_key.activated_at = datetime.utcnow().isoformat()

        self.data_store.save_key(old_key)
        self.data_store.save_key(new_key)

        self._log_audit("rotation_initiated", asdict(plan))

        print(f"✓ Rotation initiated: {plan.rotation_id}")
        print(f"  Old key: {old_key.key_id} (v{old_key.version})")
        print(f"  New key: {new_key.key_id} (v{new_key.version})")
        print(f"  Items to migrate: {items_count:,}")
        print(f"  Estimated duration: {estimated_duration // 60} minutes")

        return plan

    def migrate_batch(self, plan: RotationPlan, offset: int) -> int:
        """
        Migrate a batch of encrypted items.

        Args:
            plan: Rotation plan
            offset: Starting offset

        Returns:
            Number of items migrated
        """
        # Fetch batch of encrypted items
        items = self.data_store.fetch_encrypted_items(
            key_version=plan.old_key.version,
            limit=plan.batch_size,
            offset=offset
        )

        if not items:
            return 0

        # Decrypt old keys
        old_dek = self.kms.decrypt_data_key(
            base64.b64decode(plan.old_key.encrypted_key)
        )
        new_dek = self.kms.decrypt_data_key(
            base64.b64decode(plan.new_key.encrypted_key)
        )

        migrated = 0
        for item in items:
            try:
                # Decrypt with old key
                old_aesgcm = AESGCM(old_dek)
                plaintext = old_aesgcm.decrypt(
                    item['nonce'],
                    item['ciphertext'],
                    None
                )

                # Re-encrypt with new key
                new_aesgcm = AESGCM(new_dek)
                new_nonce = os.urandom(12)
                new_ciphertext = new_aesgcm.encrypt(new_nonce, plaintext, None)

                # Update item
                self.data_store.update_encrypted_item(
                    item_id=item['id'],
                    ciphertext=new_ciphertext,
                    nonce=new_nonce,
                    key_version=plan.new_key.version
                )

                migrated += 1

            except Exception as e:
                self._log_audit("migration_error", {
                    "item_id": item['id'],
                    "error": str(e)
                })
                print(f"  Error migrating item {item['id']}: {e}")

        return migrated

    def execute_migration(self, plan: RotationPlan) -> bool:
        """
        Execute full migration with progress tracking.

        Args:
            plan: Rotation plan

        Returns:
            True if successful
        """
        print(f"\n=== Executing Migration: {plan.rotation_id} ===")

        # Update phase
        plan.phase = RotationPhase.MIGRATION.value
        self.data_store.save_rotation_plan(plan)

        # Migrate in batches
        offset = 0
        total_migrated = 0

        while offset < plan.items_to_migrate:
            batch_start = datetime.utcnow()

            migrated = self.migrate_batch(plan, offset)
            if migrated == 0:
                break

            total_migrated += migrated
            offset += plan.batch_size

            batch_duration = (datetime.utcnow() - batch_start).total_seconds()
            rate = migrated / batch_duration if batch_duration > 0 else 0

            # Update progress
            plan.items_migrated = total_migrated
            self.data_store.save_rotation_plan(plan)

            # Progress report
            progress_pct = (total_migrated / plan.items_to_migrate) * 100
            print(f"  Progress: {total_migrated:,}/{plan.items_to_migrate:,} "
                  f"({progress_pct:.1f}%) | Rate: {rate:.1f} items/sec")

        # Verify migration
        remaining = self.data_store.count_encrypted_items(plan.old_key.version)
        if remaining > 0:
            print(f"  Warning: {remaining} items still using old key")
            return False

        print(f"✓ Migration completed: {total_migrated:,} items migrated")
        return True

    def complete_rotation(self, plan: RotationPlan) -> None:
        """
        Complete rotation by activating new key and deprecating old key.

        Args:
            plan: Rotation plan
        """
        # Activate new key
        new_key = plan.new_key
        new_key.status = KeyStatus.ACTIVE.value
        self.data_store.save_key(new_key)

        # Deprecate old key (keep for rollback period)
        old_key = plan.old_key
        old_key.status = KeyStatus.DEPRECATED.value
        old_key.deprecated_at = datetime.utcnow().isoformat()
        self.data_store.save_key(old_key)

        # Update rotation phase
        plan.phase = RotationPhase.NEW_KEY_ONLY.value
        self.data_store.save_rotation_plan(plan)

        self._log_audit("rotation_completed", {
            "rotation_id": plan.rotation_id,
            "new_key": new_key.key_id
        })

        print(f"\n✓ Rotation completed")
        print(f"  New active key: {new_key.key_id} (v{new_key.version})")
        print(f"  Old key deprecated (retain for 90 days)")

    def retire_old_key(self, key_id: str) -> None:
        """
        Retire old key after safe retention period.

        Args:
            key_id: Key to retire
        """
        key = self.data_store.get_key(key_id)

        if key.status != KeyStatus.DEPRECATED.value:
            raise ValueError("Can only retire deprecated keys")

        # Check deprecation period (e.g., 90 days)
        deprecated_at = datetime.fromisoformat(key.deprecated_at)
        days_since = (datetime.utcnow() - deprecated_at).days

        if days_since < 90:
            raise ValueError(f"Key can be retired in {90 - days_since} days")

        # Retire key
        key.status = KeyStatus.RETIRED.value
        key.retired_at = datetime.utcnow().isoformat()
        self.data_store.save_key(key)

        self._log_audit("key_retired", {"key_id": key_id})

        print(f"✓ Key retired: {key_id}")

    def rollback_rotation(self, plan: RotationPlan) -> None:
        """
        Rollback rotation (emergency procedure).

        Args:
            plan: Rotation plan
        """
        print(f"\n⚠️  Rolling back rotation: {plan.rotation_id}")

        # Re-encrypt migrated items with old key
        migrated_items = self.data_store.fetch_encrypted_items(
            key_version=plan.new_key.version,
            limit=plan.items_migrated
        )

        old_dek = self.kms.decrypt_data_key(
            base64.b64decode(plan.old_key.encrypted_key)
        )
        new_dek = self.kms.decrypt_data_key(
            base64.b64decode(plan.new_key.encrypted_key)
        )

        for item in migrated_items:
            # Decrypt with new key
            new_aesgcm = AESGCM(new_dek)
            plaintext = new_aesgcm.decrypt(item['nonce'], item['ciphertext'], None)

            # Re-encrypt with old key
            old_aesgcm = AESGCM(old_dek)
            old_nonce = os.urandom(12)
            old_ciphertext = old_aesgcm.encrypt(old_nonce, plaintext, None)

            self.data_store.update_encrypted_item(
                item_id=item['id'],
                ciphertext=old_ciphertext,
                nonce=old_nonce,
                key_version=plan.old_key.version
            )

        # Restore key statuses
        plan.old_key.status = KeyStatus.ACTIVE.value
        plan.new_key.status = KeyStatus.RETIRED.value
        self.data_store.save_key(plan.old_key)
        self.data_store.save_key(plan.new_key)

        self._log_audit("rotation_rolled_back", {"rotation_id": plan.rotation_id})

        print("✓ Rollback completed")

    def _log_audit(self, action: str, details: Dict) -> None:
        """Log audit event"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": details
        }
        self.audit_log.append(entry)
        self.data_store.save_audit_log(entry)


# =============================================================================
# Example Usage
# =============================================================================

class MockKMS:
    """Mock KMS for demonstration"""

    def generate_data_key(self) -> Tuple[bytes, bytes]:
        plaintext = os.urandom(32)
        encrypted = os.urandom(48)  # Simulated encrypted key
        return plaintext, encrypted

    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        return os.urandom(32)  # Simulated decryption


class MockDataStore:
    """Mock data store for demonstration"""

    def __init__(self):
        self.keys: Dict[str, EncryptionKey] = {}
        self.items: List[Dict] = []
        self.rotation_plans: List[RotationPlan] = []
        self.audit_logs: List[Dict] = []

    def list_keys(self) -> List[EncryptionKey]:
        return list(self.keys.values())

    def get_key(self, key_id: str) -> EncryptionKey:
        return self.keys[key_id]

    def save_key(self, key: EncryptionKey) -> None:
        self.keys[key.key_id] = key

    def count_encrypted_items(self, key_version: int) -> int:
        return sum(1 for item in self.items if item['key_version'] == key_version)

    def fetch_encrypted_items(self, key_version: int, limit: int, offset: int = 0) -> List[Dict]:
        items = [item for item in self.items if item['key_version'] == key_version]
        return items[offset:offset + limit]

    def update_encrypted_item(self, item_id: str, ciphertext: bytes,
                             nonce: bytes, key_version: int) -> None:
        for item in self.items:
            if item['id'] == item_id:
                item['ciphertext'] = ciphertext
                item['nonce'] = nonce
                item['key_version'] = key_version
                break

    def save_rotation_plan(self, plan: RotationPlan) -> None:
        self.rotation_plans.append(plan)

    def save_audit_log(self, entry: Dict) -> None:
        self.audit_logs.append(entry)


def example_complete_rotation():
    """Complete key rotation workflow"""
    print("=== Zero-Downtime Key Rotation Example ===\n")

    # Initialize
    kms = MockKMS()
    data_store = MockDataStore()

    # Create initial key and data
    initial_key = EncryptionKey(
        key_id="key-v1-initial",
        version=1,
        algorithm="AES-256-GCM",
        key_length=256,
        status=KeyStatus.ACTIVE.value,
        created_at=datetime.utcnow().isoformat(),
        encrypted_key=base64.b64encode(os.urandom(48)).decode()
    )
    data_store.save_key(initial_key)

    # Create mock encrypted items
    for i in range(5000):
        data_store.items.append({
            'id': f'item-{i}',
            'ciphertext': os.urandom(100),
            'nonce': os.urandom(12),
            'key_version': 1
        })

    print(f"Initial state: {len(data_store.items):,} items encrypted with v1")

    # Create rotation manager
    manager = KeyRotationManager(kms, data_store)

    # Step 1: Initiate rotation
    plan = manager.initiate_rotation(
        old_key_id=initial_key.key_id,
        batch_size=1000,
        parallel_workers=4
    )

    # Step 2: Execute migration
    success = manager.execute_migration(plan)

    if success:
        # Step 3: Complete rotation
        manager.complete_rotation(plan)

        # Verify
        remaining = data_store.count_encrypted_items(1)
        migrated = data_store.count_encrypted_items(2)
        print(f"\nVerification:")
        print(f"  Items with old key (v1): {remaining}")
        print(f"  Items with new key (v2): {migrated}")

    print(f"\nAudit log entries: {len(manager.audit_log)}")


if __name__ == "__main__":
    # Note: Requires cryptography package
    # pip install cryptography

    example_complete_rotation()

    print("\n=== Best Practices ===")
    print("  • Dual-key period: both old and new keys active during migration")
    print("  • Batch processing: migrate in small batches to avoid blocking")
    print("  • Progress tracking: monitor migration status")
    print("  • Rollback support: keep old key for emergency rollback")
    print("  • Retention period: keep deprecated keys for 90 days")
    print("  • Audit logging: log all rotation operations")
    print("  • Zero downtime: applications continue using old key until migration")
