#!/usr/bin/env python3
"""
Model Manager for DSPy Compiled Models

Manages version control and registry for compiled DSPy models with metadata
and promotion workflows. Provides CLI for model registration, listing,
promotion, rollback, comparison, and deletion.

Usage:
    python model_manager.py register model.json --version 1.0.0 --description "Initial model"
    python model_manager.py list --status production
    python model_manager.py promote 1.0.0 --to production
    python model_manager.py rollback --from production --to 0.9.0
    python model_manager.py compare 1.0.0 0.9.0
    python model_manager.py delete 0.8.0
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class ModelStatus(str, Enum):
    """Model lifecycle status."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class ModelMetadata:
    """Metadata for a compiled model."""
    model_id: str
    version: str
    status: ModelStatus
    optimizer: str
    base_model: str
    num_training_examples: int
    validation_score: float
    hyperparameters: Dict[str, Any]
    created_at: str
    promoted_at: Optional[str] = None
    deprecated_at: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetadata':
        """Create from dictionary."""
        data['status'] = ModelStatus(data['status'])
        return cls(**data)


class VersionValidator:
    """Validate semantic versions."""

    @staticmethod
    def validate(version: str) -> bool:
        """
        Validate semantic version format (major.minor.patch).

        Args:
            version: Version string to validate

        Returns:
            True if valid, False otherwise
        """
        parts = version.split('.')
        if len(parts) != 3:
            return False

        try:
            major, minor, patch = map(int, parts)
            return all(v >= 0 for v in (major, minor, patch))
        except ValueError:
            return False

    @staticmethod
    def compare(v1: str, v2: str) -> int:
        """
        Compare two semantic versions.

        Args:
            v1: First version
            v2: Second version

        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2
        """
        parts1 = tuple(map(int, v1.split('.')))
        parts2 = tuple(map(int, v2.split('.')))

        if parts1 < parts2:
            return -1
        elif parts1 > parts2:
            return 1
        else:
            return 0


class ModelRegistry:
    """Registry for managing compiled models."""

    def __init__(self, base_dir: str = "./models"):
        """
        Initialize registry.

        Args:
            base_dir: Base directory for model storage
        """
        self.base_dir = Path(base_dir)
        self.registry_file = self.base_dir / "registry.json"
        self.models: Dict[str, List[ModelMetadata]] = {}

        # Create directory structure
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Load existing registry
        self._load_registry()

    def _load_registry(self):
        """Load registry from disk."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)

                for model_id, versions in data.items():
                    self.models[model_id] = [
                        ModelMetadata.from_dict(v) for v in versions
                    ]
            except Exception as e:
                print(f"Warning: Failed to load registry: {e}", file=sys.stderr)
                self.models = {}

    def _save_registry(self):
        """Save registry to disk."""
        data = {
            model_id: [v.to_dict() for v in versions]
            for model_id, versions in self.models.items()
        }

        with open(self.registry_file, 'w') as f:
            json.dump(data, f, indent=2)

    def register(
        self,
        model_path: str,
        version: str,
        optimizer: str,
        base_model: str,
        num_training_examples: int,
        validation_score: float,
        hyperparameters: Dict[str, Any],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Path:
        """
        Register a new model version.

        Args:
            model_path: Path to model file
            version: Semantic version (major.minor.patch)
            optimizer: Optimizer used
            base_model: Base LM model
            num_training_examples: Number of training examples
            validation_score: Validation score
            hyperparameters: Optimization hyperparameters
            description: Optional description
            tags: Optional tags

        Returns:
            Path to registered model directory
        """
        # Validate version
        if not VersionValidator.validate(version):
            raise ValueError(f"Invalid version format: {version}. Use major.minor.patch")

        # Load model to get ID
        model_file = Path(model_path)
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        # Extract or generate model ID
        if model_file.parent.name == "latest":
            model_id = model_file.parent.parent.name
        else:
            model_id = model_file.parent.name

        # Check for duplicate version
        if model_id in self.models:
            for existing in self.models[model_id]:
                if existing.version == version:
                    raise ValueError(f"Version {version} already exists for {model_id}")

        # Create metadata
        metadata = ModelMetadata(
            model_id=model_id,
            version=version,
            status=ModelStatus.DEVELOPMENT,
            optimizer=optimizer,
            base_model=base_model,
            num_training_examples=num_training_examples,
            validation_score=validation_score,
            hyperparameters=hyperparameters,
            created_at=datetime.utcnow().isoformat(),
            description=description,
            tags=tags or [],
        )

        # Create versioned directory
        model_dir = self.base_dir / model_id / version
        model_dir.mkdir(parents=True, exist_ok=True)

        # Copy model file
        dest_model = model_dir / "model.json"
        shutil.copy2(model_path, dest_model)

        # Save metadata
        metadata_file = model_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Add to registry
        if model_id not in self.models:
            self.models[model_id] = []

        self.models[model_id].append(metadata)
        self._save_registry()

        print(f"✓ Registered {model_id} v{version}")
        print(f"  Status: {metadata.status.value}")
        print(f"  Score: {validation_score:.4f}")
        print(f"  Location: {model_dir}")

        return model_dir

    def list_models(
        self,
        model_id: Optional[str] = None,
        status: Optional[ModelStatus] = None,
    ) -> List[ModelMetadata]:
        """
        List models matching criteria.

        Args:
            model_id: Optional model ID filter
            status: Optional status filter

        Returns:
            List of matching model metadata
        """
        results = []

        # Filter by model_id
        if model_id:
            if model_id not in self.models:
                return []
            models_to_check = {model_id: self.models[model_id]}
        else:
            models_to_check = self.models

        # Collect and filter by status
        for mid, versions in models_to_check.items():
            for metadata in versions:
                if status is None or metadata.status == status:
                    results.append(metadata)

        # Sort by model_id, then version (descending)
        results.sort(
            key=lambda m: (m.model_id, tuple(map(int, m.version.split('.')))),
            reverse=True
        )

        return results

    def get_model(self, model_id: str, version: str) -> Optional[ModelMetadata]:
        """
        Get specific model version.

        Args:
            model_id: Model identifier
            version: Version string

        Returns:
            Model metadata or None if not found
        """
        if model_id not in self.models:
            return None

        for metadata in self.models[model_id]:
            if metadata.version == version:
                return metadata

        return None

    def promote(
        self,
        model_id: str,
        version: str,
        to_status: ModelStatus,
    ) -> bool:
        """
        Promote model to new status.

        Args:
            model_id: Model identifier
            version: Version to promote
            to_status: Target status

        Returns:
            True if successful
        """
        metadata = self.get_model(model_id, version)
        if not metadata:
            raise ValueError(f"Model {model_id} v{version} not found")

        # Validate status transition
        valid_transitions = {
            ModelStatus.DEVELOPMENT: [ModelStatus.STAGING, ModelStatus.ARCHIVED],
            ModelStatus.STAGING: [ModelStatus.PRODUCTION, ModelStatus.DEVELOPMENT, ModelStatus.ARCHIVED],
            ModelStatus.PRODUCTION: [ModelStatus.DEPRECATED],
            ModelStatus.DEPRECATED: [ModelStatus.ARCHIVED],
        }

        if to_status not in valid_transitions.get(metadata.status, []):
            raise ValueError(
                f"Cannot promote from {metadata.status.value} to {to_status.value}"
            )

        # If promoting to production, demote current production
        if to_status == ModelStatus.PRODUCTION:
            for m in self.models[model_id]:
                if m.status == ModelStatus.PRODUCTION:
                    m.status = ModelStatus.DEPRECATED
                    m.deprecated_at = datetime.utcnow().isoformat()
                    print(f"  Demoted {model_id} v{m.version} to deprecated")

        # Update status
        metadata.status = to_status
        metadata.promoted_at = datetime.utcnow().isoformat()

        # Update metadata file
        model_dir = self.base_dir / model_id / version
        metadata_file = model_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)

        self._save_registry()

        print(f"✓ Promoted {model_id} v{version} to {to_status.value}")
        return True

    def rollback(self, model_id: str, from_status: ModelStatus, to_version: str) -> bool:
        """
        Rollback from a status to a specific version.

        Args:
            model_id: Model identifier
            from_status: Current status to rollback from
            to_version: Version to rollback to

        Returns:
            True if successful
        """
        # Find current model at from_status
        current = None
        for m in self.models.get(model_id, []):
            if m.status == from_status:
                current = m
                break

        if not current:
            raise ValueError(f"No {from_status.value} model found for {model_id}")

        # Get target version
        target = self.get_model(model_id, to_version)
        if not target:
            raise ValueError(f"Target version {to_version} not found")

        print(f"Rolling back {model_id} from v{current.version} to v{to_version}")

        # Demote current
        if from_status == ModelStatus.PRODUCTION:
            current.status = ModelStatus.DEPRECATED
            current.deprecated_at = datetime.utcnow().isoformat()

        # Promote target
        target.status = from_status
        target.promoted_at = datetime.utcnow().isoformat()

        # Update metadata files
        for version in [current.version, to_version]:
            model_dir = self.base_dir / model_id / version
            metadata_file = model_dir / "metadata.json"
            meta = self.get_model(model_id, version)
            with open(metadata_file, 'w') as f:
                json.dump(meta.to_dict(), f, indent=2)

        self._save_registry()

        print(f"✓ Rollback complete: {model_id} now at v{to_version} ({from_status.value})")
        return True

    def compare(self, model_id: str, v1: str, v2: str) -> Dict[str, Any]:
        """
        Compare two model versions.

        Args:
            model_id: Model identifier
            v1: First version
            v2: Second version

        Returns:
            Dictionary with comparison details
        """
        meta1 = self.get_model(model_id, v1)
        meta2 = self.get_model(model_id, v2)

        if not meta1:
            raise ValueError(f"Version {v1} not found")
        if not meta2:
            raise ValueError(f"Version {v2} not found")

        return {
            "model_id": model_id,
            "versions": {
                v1: {
                    "status": meta1.status.value,
                    "optimizer": meta1.optimizer,
                    "validation_score": meta1.validation_score,
                    "num_training_examples": meta1.num_training_examples,
                    "created_at": meta1.created_at,
                    "hyperparameters": meta1.hyperparameters,
                },
                v2: {
                    "status": meta2.status.value,
                    "optimizer": meta2.optimizer,
                    "validation_score": meta2.validation_score,
                    "num_training_examples": meta2.num_training_examples,
                    "created_at": meta2.created_at,
                    "hyperparameters": meta2.hyperparameters,
                }
            },
            "differences": {
                "score_delta": meta2.validation_score - meta1.validation_score,
                "score_improvement": (
                    (meta2.validation_score - meta1.validation_score) / meta1.validation_score * 100
                    if meta1.validation_score > 0 else 0
                ),
                "optimizer_changed": meta1.optimizer != meta2.optimizer,
                "hyperparameters_changed": meta1.hyperparameters != meta2.hyperparameters,
            }
        }

    def delete(self, model_id: str, version: str, force: bool = False) -> bool:
        """
        Delete a model version.

        Args:
            model_id: Model identifier
            version: Version to delete
            force: Force deletion even if in production

        Returns:
            True if successful
        """
        metadata = self.get_model(model_id, version)
        if not metadata:
            raise ValueError(f"Model {model_id} v{version} not found")

        # Prevent deletion of production models without force
        if metadata.status == ModelStatus.PRODUCTION and not force:
            raise ValueError(
                f"Cannot delete production model without --force flag"
            )

        # Remove from registry
        self.models[model_id] = [
            m for m in self.models[model_id] if m.version != version
        ]

        # Remove directory
        model_dir = self.base_dir / model_id / version
        if model_dir.exists():
            shutil.rmtree(model_dir)

        # Clean up empty model directory
        parent_dir = self.base_dir / model_id
        if parent_dir.exists() and not list(parent_dir.iterdir()):
            parent_dir.rmdir()
            # Remove from registry entirely
            del self.models[model_id]

        self._save_registry()

        print(f"✓ Deleted {model_id} v{version}")
        return True


def cmd_register(args):
    """Register a new model."""
    registry = ModelRegistry(args.registry_dir)

    # Load hyperparameters if provided
    hyperparameters = {}
    if args.hyperparameters:
        try:
            hyperparameters = json.loads(args.hyperparameters)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON for hyperparameters", file=sys.stderr)
            sys.exit(1)

    # Parse tags
    tags = args.tags.split(',') if args.tags else None

    try:
        registry.register(
            model_path=args.model,
            version=args.version,
            optimizer=args.optimizer,
            base_model=args.base_model,
            num_training_examples=args.num_examples,
            validation_score=args.score,
            hyperparameters=hyperparameters,
            description=args.description,
            tags=tags,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args):
    """List models."""
    registry = ModelRegistry(args.registry_dir)

    # Parse status filter
    status = ModelStatus(args.status) if args.status else None

    models = registry.list_models(model_id=args.model_id, status=status)

    if not models:
        print("No models found")
        return

    print(f"\n{'Model ID':<20} {'Version':<12} {'Status':<15} {'Score':<8} {'Optimizer':<15}")
    print("=" * 80)

    for m in models:
        print(f"{m.model_id:<20} {m.version:<12} {m.status.value:<15} {m.validation_score:<8.4f} {m.optimizer:<15}")
        if m.description:
            print(f"  Description: {m.description}")

    print()


def cmd_promote(args):
    """Promote a model."""
    registry = ModelRegistry(args.registry_dir)

    to_status = ModelStatus(args.to)

    try:
        registry.promote(args.model_id, args.version, to_status)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_rollback(args):
    """Rollback a model."""
    registry = ModelRegistry(args.registry_dir)

    from_status = ModelStatus(args.from_status)

    try:
        registry.rollback(args.model_id, from_status, args.to)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_compare(args):
    """Compare two model versions."""
    registry = ModelRegistry(args.registry_dir)

    try:
        comparison = registry.compare(args.model_id, args.v1, args.v2)

        print(f"\nComparison: {comparison['model_id']}")
        print("=" * 60)

        print(f"\nVersion {args.v1}:")
        for key, value in comparison['versions'][args.v1].items():
            if key != 'hyperparameters':
                print(f"  {key}: {value}")

        print(f"\nVersion {args.v2}:")
        for key, value in comparison['versions'][args.v2].items():
            if key != 'hyperparameters':
                print(f"  {key}: {value}")

        print(f"\nDifferences:")
        diff = comparison['differences']
        print(f"  Score Delta: {diff['score_delta']:+.4f}")
        print(f"  Score Improvement: {diff['score_improvement']:+.2f}%")
        print(f"  Optimizer Changed: {diff['optimizer_changed']}")
        print(f"  Hyperparameters Changed: {diff['hyperparameters_changed']}")

        if diff['hyperparameters_changed']:
            print(f"\n  Hyperparameters Diff:")
            h1 = comparison['versions'][args.v1]['hyperparameters']
            h2 = comparison['versions'][args.v2]['hyperparameters']

            all_keys = set(h1.keys()) | set(h2.keys())
            for key in sorted(all_keys):
                v1_val = h1.get(key, "N/A")
                v2_val = h2.get(key, "N/A")
                if v1_val != v2_val:
                    print(f"    {key}: {v1_val} → {v2_val}")

        print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_delete(args):
    """Delete a model version."""
    registry = ModelRegistry(args.registry_dir)

    try:
        registry.delete(args.model_id, args.version, force=args.force)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Model Manager for DSPy Compiled Models"
    )
    parser.add_argument(
        '--registry-dir',
        default='./models',
        help='Registry directory (default: ./models)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Register command
    parser_reg = subparsers.add_parser('register', help='Register a new model')
    parser_reg.add_argument('model', help='Path to model file')
    parser_reg.add_argument('--version', required=True, help='Semantic version (major.minor.patch)')
    parser_reg.add_argument('--optimizer', required=True, help='Optimizer used')
    parser_reg.add_argument('--base-model', required=True, help='Base LM model')
    parser_reg.add_argument('--num-examples', type=int, required=True, help='Number of training examples')
    parser_reg.add_argument('--score', type=float, required=True, help='Validation score')
    parser_reg.add_argument('--hyperparameters', help='Hyperparameters as JSON')
    parser_reg.add_argument('--description', help='Model description')
    parser_reg.add_argument('--tags', help='Comma-separated tags')

    # List command
    parser_list = subparsers.add_parser('list', help='List models')
    parser_list.add_argument('--model-id', help='Filter by model ID')
    parser_list.add_argument('--status', choices=[s.value for s in ModelStatus], help='Filter by status')

    # Promote command
    parser_promote = subparsers.add_parser('promote', help='Promote a model')
    parser_promote.add_argument('model_id', help='Model ID')
    parser_promote.add_argument('version', help='Version to promote')
    parser_promote.add_argument('--to', required=True, choices=[s.value for s in ModelStatus], help='Target status')

    # Rollback command
    parser_rollback = subparsers.add_parser('rollback', help='Rollback a model')
    parser_rollback.add_argument('model_id', help='Model ID')
    parser_rollback.add_argument('--from', dest='from_status', required=True, choices=[s.value for s in ModelStatus], help='Status to rollback from')
    parser_rollback.add_argument('--to', required=True, help='Version to rollback to')

    # Compare command
    parser_compare = subparsers.add_parser('compare', help='Compare two versions')
    parser_compare.add_argument('model_id', help='Model ID')
    parser_compare.add_argument('v1', help='First version')
    parser_compare.add_argument('v2', help='Second version')

    # Delete command
    parser_delete = subparsers.add_parser('delete', help='Delete a model version')
    parser_delete.add_argument('model_id', help='Model ID')
    parser_delete.add_argument('version', help='Version to delete')
    parser_delete.add_argument('--force', action='store_true', help='Force deletion of production models')

    args = parser.parse_args()

    if args.command == 'register':
        cmd_register(args)
    elif args.command == 'list':
        cmd_list(args)
    elif args.command == 'promote':
        cmd_promote(args)
    elif args.command == 'rollback':
        cmd_rollback(args)
    elif args.command == 'compare':
        cmd_compare(args)
    elif args.command == 'delete':
        cmd_delete(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
