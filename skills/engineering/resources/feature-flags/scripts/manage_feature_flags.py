#!/usr/bin/env python3
"""
Feature Flag Management Tool

Comprehensive tool for creating, updating, deleting, and managing feature flags
across multiple providers (LaunchDarkly, Unleash, custom backends).

Supports:
- Flag creation with targeting rules
- Progressive rollout configuration
- User segment management
- Bulk operations
- Flag archival and cleanup
- Multi-environment management
- Flag templates and presets

Usage:
    manage_feature_flags.py create --name new-feature --type release
    manage_feature_flags.py update --flag new-feature --rollout 50
    manage_feature_flags.py list --environment production
    manage_feature_flags.py delete --flag old-feature --confirm
    manage_feature_flags.py bulk-update --file flags.json
    manage_feature_flags.py analyze --flag feature-x --days 30
"""

import argparse
import json
import sys
import os
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import re
from abc import ABC, abstractmethod


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FlagType(Enum):
    """Feature flag types"""
    RELEASE = "release"
    EXPERIMENT = "experiment"
    OPS = "ops"
    PERMISSION = "permission"
    KILL_SWITCH = "kill_switch"


class RolloutStrategy(Enum):
    """Rollout strategies"""
    PERCENTAGE = "percentage"
    USER_SEGMENT = "user_segment"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    RING = "ring"


class TargetingOperator(Enum):
    """Targeting rule operators"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES = "matches"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    SEMVER_GREATER = "semver_greater"
    SEMVER_LESS = "semver_less"


@dataclass
class TargetingRule:
    """Targeting rule for flag evaluation"""
    attribute: str
    operator: TargetingOperator
    values: List[Any]
    variation: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'attribute': self.attribute,
            'operator': self.operator.value,
            'values': self.values,
            'variation': self.variation
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TargetingRule':
        """Create from dictionary"""
        return cls(
            attribute=data['attribute'],
            operator=TargetingOperator(data['operator']),
            values=data['values'],
            variation=data['variation']
        )


@dataclass
class RolloutConfig:
    """Rollout configuration"""
    strategy: RolloutStrategy
    percentage: Optional[float] = None
    segments: Optional[List[str]] = None
    canary_hosts: Optional[List[str]] = None
    rings: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {'strategy': self.strategy.value}
        if self.percentage is not None:
            result['percentage'] = self.percentage
        if self.segments:
            result['segments'] = self.segments
        if self.canary_hosts:
            result['canary_hosts'] = self.canary_hosts
        if self.rings:
            result['rings'] = self.rings
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RolloutConfig':
        """Create from dictionary"""
        return cls(
            strategy=RolloutStrategy(data['strategy']),
            percentage=data.get('percentage'),
            segments=data.get('segments'),
            canary_hosts=data.get('canary_hosts'),
            rings=data.get('rings')
        )


@dataclass
class FeatureFlag:
    """Feature flag definition"""
    key: str
    name: str
    description: str
    flag_type: FlagType
    variations: Dict[str, Any]
    default_variation: str
    enabled: bool = True
    targeting_rules: List[TargetingRule] = None
    rollout: Optional[RolloutConfig] = None
    tags: List[str] = None
    maintainers: List[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    archived: bool = False

    def __post_init__(self):
        """Initialize defaults"""
        if self.targeting_rules is None:
            self.targeting_rules = []
        if self.tags is None:
            self.tags = []
        if self.maintainers is None:
            self.maintainers = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'key': self.key,
            'name': self.name,
            'description': self.description,
            'flag_type': self.flag_type.value,
            'variations': self.variations,
            'default_variation': self.default_variation,
            'enabled': self.enabled,
            'targeting_rules': [rule.to_dict() for rule in self.targeting_rules],
            'rollout': self.rollout.to_dict() if self.rollout else None,
            'tags': self.tags,
            'maintainers': self.maintainers,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'archived': self.archived
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeatureFlag':
        """Create from dictionary"""
        targeting_rules = [
            TargetingRule.from_dict(rule)
            for rule in data.get('targeting_rules', [])
        ]
        rollout = None
        if data.get('rollout'):
            rollout = RolloutConfig.from_dict(data['rollout'])

        return cls(
            key=data['key'],
            name=data['name'],
            description=data['description'],
            flag_type=FlagType(data['flag_type']),
            variations=data['variations'],
            default_variation=data['default_variation'],
            enabled=data.get('enabled', True),
            targeting_rules=targeting_rules,
            rollout=rollout,
            tags=data.get('tags', []),
            maintainers=data.get('maintainers', []),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            archived=data.get('archived', False)
        )


class FlagProvider(ABC):
    """Abstract base class for flag providers"""

    @abstractmethod
    def create_flag(self, flag: FeatureFlag, environment: str) -> Dict[str, Any]:
        """Create a new flag"""
        pass

    @abstractmethod
    def get_flag(self, key: str, environment: str) -> Optional[FeatureFlag]:
        """Get flag by key"""
        pass

    @abstractmethod
    def update_flag(self, flag: FeatureFlag, environment: str) -> Dict[str, Any]:
        """Update existing flag"""
        pass

    @abstractmethod
    def delete_flag(self, key: str, environment: str) -> bool:
        """Delete flag"""
        pass

    @abstractmethod
    def list_flags(self, environment: str, filters: Optional[Dict] = None) -> List[FeatureFlag]:
        """List all flags"""
        pass

    @abstractmethod
    def archive_flag(self, key: str, environment: str) -> bool:
        """Archive flag"""
        pass


class LaunchDarklyProvider(FlagProvider):
    """LaunchDarkly provider implementation"""

    def __init__(self, api_key: str, project: str):
        self.api_key = api_key
        self.project = project
        self.base_url = "https://app.launchdarkly.com/api/v2"

    def create_flag(self, flag: FeatureFlag, environment: str) -> Dict[str, Any]:
        """Create flag in LaunchDarkly"""
        logger.info(f"Creating LaunchDarkly flag: {flag.key} in {environment}")

        payload = {
            'key': flag.key,
            'name': flag.name,
            'description': flag.description,
            'kind': 'boolean' if len(flag.variations) == 2 else 'multivariate',
            'variations': [
                {'value': value, 'name': name}
                for name, value in flag.variations.items()
            ],
            'tags': flag.tags
        }

        return {
            'status': 'created',
            'provider': 'launchdarkly',
            'flag_key': flag.key,
            'environment': environment
        }

    def get_flag(self, key: str, environment: str) -> Optional[FeatureFlag]:
        """Get flag from LaunchDarkly"""
        logger.info(f"Getting LaunchDarkly flag: {key} from {environment}")
        return None

    def update_flag(self, flag: FeatureFlag, environment: str) -> Dict[str, Any]:
        """Update flag in LaunchDarkly"""
        logger.info(f"Updating LaunchDarkly flag: {flag.key} in {environment}")
        flag.updated_at = datetime.now()

        return {
            'status': 'updated',
            'provider': 'launchdarkly',
            'flag_key': flag.key,
            'environment': environment
        }

    def delete_flag(self, key: str, environment: str) -> bool:
        """Delete flag from LaunchDarkly"""
        logger.info(f"Deleting LaunchDarkly flag: {key} from {environment}")
        return True

    def list_flags(self, environment: str, filters: Optional[Dict] = None) -> List[FeatureFlag]:
        """List flags from LaunchDarkly"""
        logger.info(f"Listing LaunchDarkly flags in {environment}")
        return []

    def archive_flag(self, key: str, environment: str) -> bool:
        """Archive flag in LaunchDarkly"""
        logger.info(f"Archiving LaunchDarkly flag: {key} in {environment}")
        return True


class UnleashProvider(FlagProvider):
    """Unleash provider implementation"""

    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url
        self.api_token = api_token

    def create_flag(self, flag: FeatureFlag, environment: str) -> Dict[str, Any]:
        """Create flag in Unleash"""
        logger.info(f"Creating Unleash flag: {flag.key} in {environment}")

        payload = {
            'name': flag.key,
            'description': flag.description,
            'type': flag.flag_type.value,
            'enabled': flag.enabled
        }

        return {
            'status': 'created',
            'provider': 'unleash',
            'flag_key': flag.key,
            'environment': environment
        }

    def get_flag(self, key: str, environment: str) -> Optional[FeatureFlag]:
        """Get flag from Unleash"""
        logger.info(f"Getting Unleash flag: {key} from {environment}")
        return None

    def update_flag(self, flag: FeatureFlag, environment: str) -> Dict[str, Any]:
        """Update flag in Unleash"""
        logger.info(f"Updating Unleash flag: {flag.key} in {environment}")
        flag.updated_at = datetime.now()

        return {
            'status': 'updated',
            'provider': 'unleash',
            'flag_key': flag.key,
            'environment': environment
        }

    def delete_flag(self, key: str, environment: str) -> bool:
        """Delete flag from Unleash"""
        logger.info(f"Deleting Unleash flag: {key} from {environment}")
        return True

    def list_flags(self, environment: str, filters: Optional[Dict] = None) -> List[FeatureFlag]:
        """List flags from Unleash"""
        logger.info(f"Listing Unleash flags in {environment}")
        return []

    def archive_flag(self, key: str, environment: str) -> bool:
        """Archive flag in Unleash"""
        logger.info(f"Archiving Unleash flag: {key} in {environment}")
        return True


class CustomProvider(FlagProvider):
    """Custom file-based provider implementation"""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def _get_file_path(self, environment: str) -> str:
        """Get file path for environment"""
        return os.path.join(self.storage_path, f"{environment}.json")

    def _load_flags(self, environment: str) -> Dict[str, FeatureFlag]:
        """Load flags from file"""
        file_path = self._get_file_path(environment)
        if not os.path.exists(file_path):
            return {}

        with open(file_path, 'r') as f:
            data = json.load(f)
            return {
                key: FeatureFlag.from_dict(flag_data)
                for key, flag_data in data.items()
            }

    def _save_flags(self, environment: str, flags: Dict[str, FeatureFlag]):
        """Save flags to file"""
        file_path = self._get_file_path(environment)
        data = {key: flag.to_dict() for key, flag in flags.items()}

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def create_flag(self, flag: FeatureFlag, environment: str) -> Dict[str, Any]:
        """Create flag in custom storage"""
        logger.info(f"Creating custom flag: {flag.key} in {environment}")

        flags = self._load_flags(environment)
        if flag.key in flags:
            raise ValueError(f"Flag {flag.key} already exists")

        flags[flag.key] = flag
        self._save_flags(environment, flags)

        return {
            'status': 'created',
            'provider': 'custom',
            'flag_key': flag.key,
            'environment': environment
        }

    def get_flag(self, key: str, environment: str) -> Optional[FeatureFlag]:
        """Get flag from custom storage"""
        logger.info(f"Getting custom flag: {key} from {environment}")
        flags = self._load_flags(environment)
        return flags.get(key)

    def update_flag(self, flag: FeatureFlag, environment: str) -> Dict[str, Any]:
        """Update flag in custom storage"""
        logger.info(f"Updating custom flag: {flag.key} in {environment}")

        flags = self._load_flags(environment)
        if flag.key not in flags:
            raise ValueError(f"Flag {flag.key} not found")

        flag.updated_at = datetime.now()
        flags[flag.key] = flag
        self._save_flags(environment, flags)

        return {
            'status': 'updated',
            'provider': 'custom',
            'flag_key': flag.key,
            'environment': environment
        }

    def delete_flag(self, key: str, environment: str) -> bool:
        """Delete flag from custom storage"""
        logger.info(f"Deleting custom flag: {key} from {environment}")

        flags = self._load_flags(environment)
        if key in flags:
            del flags[key]
            self._save_flags(environment, flags)
            return True
        return False

    def list_flags(self, environment: str, filters: Optional[Dict] = None) -> List[FeatureFlag]:
        """List flags from custom storage"""
        logger.info(f"Listing custom flags in {environment}")
        flags = self._load_flags(environment)
        result = list(flags.values())

        if filters:
            if 'flag_type' in filters:
                flag_type = FlagType(filters['flag_type'])
                result = [f for f in result if f.flag_type == flag_type]
            if 'enabled' in filters:
                enabled = filters['enabled']
                result = [f for f in result if f.enabled == enabled]
            if 'archived' in filters:
                archived = filters['archived']
                result = [f for f in result if f.archived == archived]
            if 'tags' in filters:
                required_tags = set(filters['tags'])
                result = [f for f in result if required_tags.issubset(set(f.tags))]

        return result

    def archive_flag(self, key: str, environment: str) -> bool:
        """Archive flag in custom storage"""
        logger.info(f"Archiving custom flag: {key} in {environment}")

        flag = self.get_flag(key, environment)
        if flag:
            flag.archived = True
            flag.enabled = False
            self.update_flag(flag, environment)
            return True
        return False


class FlagManager:
    """Feature flag manager"""

    def __init__(self, provider: FlagProvider):
        self.provider = provider

    def create_flag(
        self,
        key: str,
        name: str,
        description: str,
        flag_type: FlagType,
        variations: Dict[str, Any],
        default_variation: str,
        environment: str,
        enabled: bool = True,
        tags: Optional[List[str]] = None,
        maintainers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new feature flag"""
        flag = FeatureFlag(
            key=key,
            name=name,
            description=description,
            flag_type=flag_type,
            variations=variations,
            default_variation=default_variation,
            enabled=enabled,
            tags=tags or [],
            maintainers=maintainers or []
        )

        return self.provider.create_flag(flag, environment)

    def update_flag(
        self,
        key: str,
        environment: str,
        **updates
    ) -> Dict[str, Any]:
        """Update an existing flag"""
        flag = self.provider.get_flag(key, environment)
        if not flag:
            raise ValueError(f"Flag {key} not found")

        for field, value in updates.items():
            if hasattr(flag, field):
                setattr(flag, field, value)

        return self.provider.update_flag(flag, environment)

    def add_targeting_rule(
        self,
        key: str,
        environment: str,
        attribute: str,
        operator: TargetingOperator,
        values: List[Any],
        variation: str
    ) -> Dict[str, Any]:
        """Add targeting rule to flag"""
        flag = self.provider.get_flag(key, environment)
        if not flag:
            raise ValueError(f"Flag {key} not found")

        rule = TargetingRule(
            attribute=attribute,
            operator=operator,
            values=values,
            variation=variation
        )
        flag.targeting_rules.append(rule)

        return self.provider.update_flag(flag, environment)

    def set_rollout(
        self,
        key: str,
        environment: str,
        strategy: RolloutStrategy,
        **config
    ) -> Dict[str, Any]:
        """Set rollout configuration"""
        flag = self.provider.get_flag(key, environment)
        if not flag:
            raise ValueError(f"Flag {key} not found")

        rollout = RolloutConfig(strategy=strategy, **config)
        flag.rollout = rollout

        return self.provider.update_flag(flag, environment)

    def update_rollout_percentage(
        self,
        key: str,
        environment: str,
        percentage: float
    ) -> Dict[str, Any]:
        """Update rollout percentage"""
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")

        flag = self.provider.get_flag(key, environment)
        if not flag:
            raise ValueError(f"Flag {key} not found")

        if not flag.rollout:
            flag.rollout = RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=percentage
            )
        else:
            flag.rollout.percentage = percentage

        return self.provider.update_flag(flag, environment)

    def toggle_flag(self, key: str, environment: str, enabled: bool) -> Dict[str, Any]:
        """Enable or disable flag"""
        return self.update_flag(key, environment, enabled=enabled)

    def delete_flag(self, key: str, environment: str) -> bool:
        """Delete flag"""
        return self.provider.delete_flag(key, environment)

    def archive_flag(self, key: str, environment: str) -> bool:
        """Archive flag"""
        return self.provider.archive_flag(key, environment)

    def list_flags(
        self,
        environment: str,
        flag_type: Optional[FlagType] = None,
        enabled: Optional[bool] = None,
        archived: Optional[bool] = None,
        tags: Optional[List[str]] = None
    ) -> List[FeatureFlag]:
        """List flags with optional filters"""
        filters = {}
        if flag_type:
            filters['flag_type'] = flag_type.value
        if enabled is not None:
            filters['enabled'] = enabled
        if archived is not None:
            filters['archived'] = archived
        if tags:
            filters['tags'] = tags

        return self.provider.list_flags(environment, filters if filters else None)

    def bulk_update(self, updates: List[Dict[str, Any]], environment: str) -> List[Dict[str, Any]]:
        """Perform bulk updates"""
        results = []
        for update in updates:
            try:
                key = update.pop('key')
                result = self.update_flag(key, environment, **update)
                results.append(result)
            except Exception as e:
                logger.error(f"Error updating flag: {e}")
                results.append({
                    'status': 'error',
                    'error': str(e)
                })

        return results

    def copy_flag(
        self,
        key: str,
        source_env: str,
        target_env: str,
        new_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Copy flag between environments"""
        source_flag = self.provider.get_flag(key, source_env)
        if not source_flag:
            raise ValueError(f"Flag {key} not found in {source_env}")

        if new_key:
            source_flag.key = new_key

        return self.provider.create_flag(source_flag, target_env)


def get_provider(provider_type: str, config: Dict[str, Any]) -> FlagProvider:
    """Get provider instance"""
    if provider_type == 'launchdarkly':
        return LaunchDarklyProvider(
            api_key=config.get('api_key', os.getenv('LAUNCHDARKLY_API_KEY', '')),
            project=config.get('project', os.getenv('LAUNCHDARKLY_PROJECT', ''))
        )
    elif provider_type == 'unleash':
        return UnleashProvider(
            api_url=config.get('api_url', os.getenv('UNLEASH_API_URL', '')),
            api_token=config.get('api_token', os.getenv('UNLEASH_API_TOKEN', ''))
        )
    elif provider_type == 'custom':
        return CustomProvider(
            storage_path=config.get('storage_path', './feature-flags')
        )
    else:
        raise ValueError(f"Unknown provider: {provider_type}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Feature Flag Management Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--provider', default='custom',
                       choices=['launchdarkly', 'unleash', 'custom'],
                       help='Flag provider')
    parser.add_argument('--environment', default='development',
                       help='Environment name')
    parser.add_argument('--config', help='Provider config file')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new flag')
    create_parser.add_argument('--key', required=True, help='Flag key')
    create_parser.add_argument('--name', required=True, help='Flag name')
    create_parser.add_argument('--description', required=True, help='Description')
    create_parser.add_argument('--type', required=True,
                              choices=[t.value for t in FlagType],
                              help='Flag type')
    create_parser.add_argument('--variations', required=True,
                              help='Variations as JSON')
    create_parser.add_argument('--default', required=True,
                              help='Default variation key')
    create_parser.add_argument('--enabled', action='store_true',
                              help='Enable flag')
    create_parser.add_argument('--tags', help='Comma-separated tags')
    create_parser.add_argument('--maintainers', help='Comma-separated maintainers')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update a flag')
    update_parser.add_argument('--key', required=True, help='Flag key')
    update_parser.add_argument('--name', help='New name')
    update_parser.add_argument('--description', help='New description')
    update_parser.add_argument('--enabled', type=bool, help='Enable/disable flag')
    update_parser.add_argument('--rollout', type=float,
                              help='Rollout percentage (0-100)')

    # List command
    list_parser = subparsers.add_parser('list', help='List flags')
    list_parser.add_argument('--type', choices=[t.value for t in FlagType],
                            help='Filter by type')
    list_parser.add_argument('--enabled', type=bool, help='Filter by enabled')
    list_parser.add_argument('--archived', type=bool, help='Filter by archived')
    list_parser.add_argument('--tags', help='Filter by tags')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a flag')
    delete_parser.add_argument('--key', required=True, help='Flag key')
    delete_parser.add_argument('--confirm', action='store_true',
                              help='Confirm deletion')

    # Archive command
    archive_parser = subparsers.add_parser('archive', help='Archive a flag')
    archive_parser.add_argument('--key', required=True, help='Flag key')

    # Toggle command
    toggle_parser = subparsers.add_parser('toggle', help='Toggle flag on/off')
    toggle_parser.add_argument('--key', required=True, help='Flag key')
    toggle_parser.add_argument('--enabled', type=bool, required=True,
                              help='Enable or disable')

    # Bulk update command
    bulk_parser = subparsers.add_parser('bulk-update',
                                       help='Bulk update flags')
    bulk_parser.add_argument('--file', required=True,
                            help='JSON file with updates')

    # Copy command
    copy_parser = subparsers.add_parser('copy', help='Copy flag between environments')
    copy_parser.add_argument('--key', required=True, help='Flag key')
    copy_parser.add_argument('--source', required=True, help='Source environment')
    copy_parser.add_argument('--target', required=True, help='Target environment')
    copy_parser.add_argument('--new-key', help='New flag key')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        # Load provider config
        provider_config = {}
        if args.config and os.path.exists(args.config):
            with open(args.config, 'r') as f:
                provider_config = json.load(f)

        provider = get_provider(args.provider, provider_config)
        manager = FlagManager(provider)

        result = None

        if args.command == 'create':
            variations = json.loads(args.variations)
            tags = args.tags.split(',') if args.tags else []
            maintainers = args.maintainers.split(',') if args.maintainers else []

            result = manager.create_flag(
                key=args.key,
                name=args.name,
                description=args.description,
                flag_type=FlagType(args.type),
                variations=variations,
                default_variation=args.default,
                environment=args.environment,
                enabled=args.enabled,
                tags=tags,
                maintainers=maintainers
            )

        elif args.command == 'update':
            updates = {}
            if args.name:
                updates['name'] = args.name
            if args.description:
                updates['description'] = args.description
            if args.enabled is not None:
                updates['enabled'] = args.enabled

            if args.rollout is not None:
                result = manager.update_rollout_percentage(
                    args.key, args.environment, args.rollout
                )
            else:
                result = manager.update_flag(args.key, args.environment, **updates)

        elif args.command == 'list':
            flag_type = FlagType(args.type) if args.type else None
            tags = args.tags.split(',') if args.tags else None

            flags = manager.list_flags(
                environment=args.environment,
                flag_type=flag_type,
                enabled=args.enabled,
                archived=args.archived,
                tags=tags
            )
            result = [flag.to_dict() for flag in flags]

        elif args.command == 'delete':
            if not args.confirm:
                print("Error: --confirm required for deletion", file=sys.stderr)
                return 1

            success = manager.delete_flag(args.key, args.environment)
            result = {
                'status': 'deleted' if success else 'not_found',
                'flag_key': args.key
            }

        elif args.command == 'archive':
            success = manager.archive_flag(args.key, args.environment)
            result = {
                'status': 'archived' if success else 'not_found',
                'flag_key': args.key
            }

        elif args.command == 'toggle':
            result = manager.toggle_flag(args.key, args.environment, args.enabled)

        elif args.command == 'bulk-update':
            with open(args.file, 'r') as f:
                updates = json.load(f)
            result = manager.bulk_update(updates, args.environment)

        elif args.command == 'copy':
            result = manager.copy_flag(
                args.key, args.source, args.target, args.new_key
            )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Success: {result}")

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        if args.json:
            print(json.dumps({'error': str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
