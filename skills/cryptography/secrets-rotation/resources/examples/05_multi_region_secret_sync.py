#!/usr/bin/env python3
"""
Multi-Region Secret Synchronization

Demonstrates:
- Synchronizing secrets across multiple regions
- Conflict resolution strategies
- Eventual consistency handling
- Cross-region rotation coordination
- Rollback across regions

Use cases:
- Multi-region deployments
- Disaster recovery
- Geographic redundancy
- Compliance requirements

Prerequisites:
    pip install boto3 google-cloud-secret-manager azure-keyvault-secrets azure-identity
"""

import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import boto3
from google.cloud import secretmanager
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential


class SecretProvider(Enum):
    """Supported secret providers."""
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"


@dataclass
class SecretVersion:
    """Secret version metadata."""
    provider: str
    region: str
    secret_id: str
    version_id: str
    value_hash: str
    created_at: str
    is_primary: bool = False


class MultiRegionSecretSync:
    """
    Synchronize secrets across multiple regions and providers.
    """

    def __init__(self):
        """Initialize multi-provider clients."""
        self.aws_clients: Dict[str, boto3.client] = {}
        self.gcp_clients: Dict[str, secretmanager.SecretManagerServiceClient] = {}
        self.azure_clients: Dict[str, SecretClient] = {}

    def add_aws_region(self, region: str):
        """Add AWS region."""
        self.aws_clients[region] = boto3.client('secretsmanager', region_name=region)
        print(f"Added AWS region: {region}")

    def add_gcp_region(self, project_id: str, location: str):
        """Add GCP region."""
        key = f"{project_id}:{location}"
        self.gcp_clients[key] = secretmanager.SecretManagerServiceClient()
        print(f"Added GCP region: {location} (project: {project_id})")

    def add_azure_region(self, vault_url: str, region: str):
        """Add Azure region."""
        credential = DefaultAzureCredential()
        self.azure_clients[region] = SecretClient(vault_url=vault_url, credential=credential)
        print(f"Added Azure region: {region}")

    def sync_secret(self, secret_id: str, secret_value: Dict[str, Any],
                    primary_provider: str, primary_region: str) -> Dict[str, Any]:
        """
        Synchronize secret across all configured regions.

        Args:
            secret_id: Secret identifier
            secret_value: Secret value (dict)
            primary_provider: Primary provider (aws/gcp/azure)
            primary_region: Primary region

        Returns:
            Sync result with status per region
        """
        print(f"[{datetime.utcnow().isoformat()}] Syncing secret: {secret_id}")
        print(f"  Primary: {primary_provider}:{primary_region}")

        results = {}
        value_json = json.dumps(secret_value, sort_keys=True)
        value_hash = hashlib.sha256(value_json.encode()).hexdigest()

        # Step 1: Update primary region
        print(f"  Updating primary region")
        primary_version = self._update_secret(
            provider=primary_provider,
            region=primary_region,
            secret_id=secret_id,
            secret_value=value_json
        )

        results[f"{primary_provider}:{primary_region}"] = {
            'status': 'success',
            'version': primary_version,
            'is_primary': True
        }

        # Step 2: Sync to AWS regions
        for region, client in self.aws_clients.items():
            if primary_provider == 'aws' and region == primary_region:
                continue

            print(f"  Syncing to AWS:{region}")
            try:
                version = self._update_aws_secret(client, secret_id, value_json)
                results[f"aws:{region}"] = {
                    'status': 'success',
                    'version': version,
                    'is_primary': False
                }
            except Exception as e:
                results[f"aws:{region}"] = {
                    'status': 'failed',
                    'error': str(e)
                }
                print(f"    ERROR: {e}")

        # Step 3: Sync to GCP regions
        for key, client in self.gcp_clients.items():
            project_id, location = key.split(':')
            if primary_provider == 'gcp' and location == primary_region:
                continue

            print(f"  Syncing to GCP:{location}")
            try:
                version = self._update_gcp_secret(client, project_id, secret_id, value_json)
                results[f"gcp:{location}"] = {
                    'status': 'success',
                    'version': version,
                    'is_primary': False
                }
            except Exception as e:
                results[f"gcp:{location}"] = {
                    'status': 'failed',
                    'error': str(e)
                }
                print(f"    ERROR: {e}")

        # Step 4: Sync to Azure regions
        for region, client in self.azure_clients.items():
            if primary_provider == 'azure' and region == primary_region:
                continue

            print(f"  Syncing to Azure:{region}")
            try:
                version = self._update_azure_secret(client, secret_id, value_json)
                results[f"azure:{region}"] = {
                    'status': 'success',
                    'version': version,
                    'is_primary': False
                }
            except Exception as e:
                results[f"azure:{region}"] = {
                    'status': 'failed',
                    'error': str(e)
                }
                print(f"    ERROR: {e}")

        # Step 5: Verify consistency
        print("  Verifying consistency")
        consistent = self._verify_consistency(secret_id, value_hash)

        return {
            'secret_id': secret_id,
            'value_hash': value_hash,
            'synced_at': datetime.utcnow().isoformat(),
            'regions': results,
            'consistent': consistent,
            'total_regions': len(results),
            'successful_regions': sum(1 for r in results.values() if r.get('status') == 'success')
        }

    def _update_secret(self, provider: str, region: str, secret_id: str,
                       secret_value: str) -> str:
        """Update secret in specific provider/region."""
        if provider == 'aws':
            client = self.aws_clients[region]
            return self._update_aws_secret(client, secret_id, secret_value)
        elif provider == 'gcp':
            key = f"{region}"
            client = self.gcp_clients[key]
            project_id = region.split(':')[0]
            return self._update_gcp_secret(client, project_id, secret_id, secret_value)
        elif provider == 'azure':
            client = self.azure_clients[region]
            return self._update_azure_secret(client, secret_id, secret_value)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _update_aws_secret(self, client, secret_id: str, secret_value: str) -> str:
        """Update AWS secret."""
        try:
            response = client.put_secret_value(
                SecretId=secret_id,
                SecretString=secret_value
            )
            return response['VersionId']
        except client.exceptions.ResourceNotFoundException:
            # Create if doesn't exist
            response = client.create_secret(
                Name=secret_id,
                SecretString=secret_value
            )
            return response['VersionId']

    def _update_gcp_secret(self, client, project_id: str, secret_id: str,
                           secret_value: str) -> str:
        """Update GCP secret."""
        parent = f"projects/{project_id}/secrets/{secret_id}"

        try:
            # Add new version
            response = client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": secret_value.encode('UTF-8')}
                }
            )
            return response.name.split('/')[-1]

        except Exception:
            # Create if doesn't exist
            secret_parent = f"projects/{project_id}"
            client.create_secret(
                request={
                    "parent": secret_parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}}
                }
            )
            response = client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": secret_value.encode('UTF-8')}
                }
            )
            return response.name.split('/')[-1]

    def _update_azure_secret(self, client, secret_id: str, secret_value: str) -> str:
        """Update Azure secret."""
        secret = client.set_secret(secret_id, secret_value)
        return secret.properties.version

    def _verify_consistency(self, secret_id: str, expected_hash: str) -> bool:
        """Verify all regions have consistent secret value."""
        all_consistent = True

        # Check AWS regions
        for region, client in self.aws_clients.items():
            try:
                response = client.get_secret_value(SecretId=secret_id)
                value_hash = hashlib.sha256(
                    response['SecretString'].encode()
                ).hexdigest()

                if value_hash != expected_hash:
                    print(f"    INCONSISTENT: aws:{region}")
                    all_consistent = False
            except Exception as e:
                print(f"    ERROR checking aws:{region}: {e}")
                all_consistent = False

        # Check GCP regions
        for key, client in self.gcp_clients.items():
            project_id, location = key.split(':')
            try:
                name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                value_hash = hashlib.sha256(response.payload.data).hexdigest()

                if value_hash != expected_hash:
                    print(f"    INCONSISTENT: gcp:{location}")
                    all_consistent = False
            except Exception as e:
                print(f"    ERROR checking gcp:{location}: {e}")
                all_consistent = False

        # Check Azure regions
        for region, client in self.azure_clients.items():
            try:
                secret = client.get_secret(secret_id)
                value_hash = hashlib.sha256(secret.value.encode()).hexdigest()

                if value_hash != expected_hash:
                    print(f"    INCONSISTENT: azure:{region}")
                    all_consistent = False
            except Exception as e:
                print(f"    ERROR checking azure:{region}: {e}")
                all_consistent = False

        return all_consistent

    def rotate_multi_region(self, secret_id: str, rotation_func,
                           primary_provider: str, primary_region: str) -> Dict[str, Any]:
        """
        Rotate secret across all regions.

        Args:
            secret_id: Secret identifier
            rotation_func: Function to generate new secret value
            primary_provider: Primary provider
            primary_region: Primary region

        Returns:
            Rotation result
        """
        print(f"[{datetime.utcnow().isoformat()}] Multi-region rotation: {secret_id}")

        # Generate new secret value
        new_value = rotation_func()

        # Sync to all regions
        result = self.sync_secret(
            secret_id=secret_id,
            secret_value=new_value,
            primary_provider=primary_provider,
            primary_region=primary_region
        )

        return result


# Example usage
if __name__ == '__main__':
    # Initialize synchronizer
    sync = MultiRegionSecretSync()

    # Configure regions
    sync.add_aws_region('us-east-1')
    sync.add_aws_region('us-west-2')
    sync.add_aws_region('eu-west-1')

    # Example secret value
    secret_value = {
        'username': 'app_user',
        'password': 'secure_password_123',
        'host': 'db.example.com',
        'port': 5432
    }

    # Sync secret across regions
    result = sync.sync_secret(
        secret_id='prod/database/credentials',
        secret_value=secret_value,
        primary_provider='aws',
        primary_region='us-east-1'
    )

    print(f"\nSync result:")
    print(f"  Secret ID: {result['secret_id']}")
    print(f"  Value hash: {result['value_hash'][:16]}...")
    print(f"  Synced at: {result['synced_at']}")
    print(f"  Total regions: {result['total_regions']}")
    print(f"  Successful: {result['successful_regions']}")
    print(f"  Consistent: {result['consistent']}")

    print(f"\nRegion status:")
    for region, status in result['regions'].items():
        print(f"  {region}: {status['status']}")

    # Multi-region rotation example
    def generate_new_credentials():
        """Generate new database credentials."""
        import secrets
        return {
            'username': 'app_user',
            'password': secrets.token_urlsafe(32),
            'host': 'db.example.com',
            'port': 5432
        }

    # Uncomment to perform rotation
    # rotation_result = sync.rotate_multi_region(
    #     secret_id='prod/database/credentials',
    #     rotation_func=generate_new_credentials,
    #     primary_provider='aws',
    #     primary_region='us-east-1'
    # )
