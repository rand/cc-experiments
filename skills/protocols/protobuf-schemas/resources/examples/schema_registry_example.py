#!/usr/bin/env python3
"""
Schema Registry Integration Example

Demonstrates integrating Protocol Buffers with a schema registry
(Confluent Schema Registry or custom) for centralized schema management,
versioning, and compatibility checking.

Features:
- Schema registration and versioning
- Schema compatibility validation
- Schema retrieval by ID or version
- Subject-based schema organization

Requirements:
    pip install requests protobuf

Usage:
    python schema_registry_example.py --register user_service.proto
    python schema_registry_example.py --get-latest user.User
    python schema_registry_example.py --check-compatibility user.User user_service_v2.proto
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

try:
    import requests
except ImportError:
    print("Error: requests not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

from google.protobuf.descriptor_pb2 import FileDescriptorSet, FileDescriptorProto


@dataclass
class SchemaInfo:
    """Schema information from registry"""
    id: int
    version: int
    schema: str
    subject: str


class SchemaRegistry:
    """Client for Confluent Schema Registry"""

    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def register_schema(self, subject: str, schema_content: str) -> Tuple[int, int]:
        """
        Register a schema under a subject.

        Returns:
            (schema_id, version)
        """
        url = f"{self.base_url}/subjects/{subject}/versions"

        # For Protobuf, the schema is the file descriptor set
        payload = {
            "schemaType": "PROTOBUF",
            "schema": schema_content
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data['id'], data.get('version', 1)

    def get_schema_by_id(self, schema_id: int) -> str:
        """Get schema by ID"""
        url = f"{self.base_url}/schemas/ids/{schema_id}"

        response = self.session.get(url)
        response.raise_for_status()

        data = response.json()
        return data['schema']

    def get_latest_schema(self, subject: str) -> SchemaInfo:
        """Get latest version of schema for subject"""
        url = f"{self.base_url}/subjects/{subject}/versions/latest"

        response = self.session.get(url)
        response.raise_for_status()

        data = response.json()
        return SchemaInfo(
            id=data['id'],
            version=data['version'],
            schema=data['schema'],
            subject=data['subject']
        )

    def get_schema_version(self, subject: str, version: int) -> SchemaInfo:
        """Get specific version of schema"""
        url = f"{self.base_url}/subjects/{subject}/versions/{version}"

        response = self.session.get(url)
        response.raise_for_status()

        data = response.json()
        return SchemaInfo(
            id=data['id'],
            version=data['version'],
            schema=data['schema'],
            subject=data['subject']
        )

    def check_compatibility(self, subject: str, schema_content: str) -> bool:
        """Check if schema is compatible with latest version"""
        url = f"{self.base_url}/compatibility/subjects/{subject}/versions/latest"

        payload = {
            "schemaType": "PROTOBUF",
            "schema": schema_content
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get('is_compatible', False)

    def list_subjects(self) -> List[str]:
        """List all registered subjects"""
        url = f"{self.base_url}/subjects"

        response = self.session.get(url)
        response.raise_for_status()

        return response.json()

    def list_versions(self, subject: str) -> List[int]:
        """List all versions for a subject"""
        url = f"{self.base_url}/subjects/{subject}/versions"

        response = self.session.get(url)
        response.raise_for_status()

        return response.json()

    def delete_subject(self, subject: str, permanent: bool = False) -> List[int]:
        """
        Delete a subject and all its versions.

        Returns list of deleted version numbers.
        """
        url = f"{self.base_url}/subjects/{subject}"
        if permanent:
            url += "?permanent=true"

        response = self.session.delete(url)
        response.raise_for_status()

        return response.json()

    def get_config(self, subject: Optional[str] = None) -> Dict:
        """Get compatibility configuration"""
        if subject:
            url = f"{self.base_url}/config/{subject}"
        else:
            url = f"{self.base_url}/config"

        response = self.session.get(url)
        response.raise_for_status()

        return response.json()

    def update_config(self, compatibility: str, subject: Optional[str] = None) -> Dict:
        """
        Update compatibility level.

        Levels:
        - BACKWARD: New schema can read old data
        - FORWARD: Old schema can read new data
        - FULL: Both backward and forward compatible
        - NONE: No compatibility checking
        """
        if subject:
            url = f"{self.base_url}/config/{subject}"
        else:
            url = f"{self.base_url}/config"

        payload = {"compatibility": compatibility}

        response = self.session.put(url, json=payload)
        response.raise_for_status()

        return response.json()


class CustomSchemaRegistry:
    """
    Custom lightweight schema registry implementation.

    This is a simple file-based registry for demonstration purposes.
    Production systems should use Confluent Schema Registry or similar.
    """

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.subjects_file = self.storage_dir / "subjects.json"
        self.schemas_file = self.storage_dir / "schemas.json"
        self._load_data()

    def _load_data(self) -> None:
        """Load registry data from disk"""
        if self.subjects_file.exists():
            with open(self.subjects_file, 'r') as f:
                self.subjects = json.load(f)
        else:
            self.subjects = {}

        if self.schemas_file.exists():
            with open(self.schemas_file, 'r') as f:
                self.schemas = json.load(f)
        else:
            self.schemas = {}

    def _save_data(self) -> None:
        """Save registry data to disk"""
        with open(self.subjects_file, 'w') as f:
            json.dump(self.subjects, f, indent=2)

        with open(self.schemas_file, 'w') as f:
            json.dump(self.schemas, f, indent=2)

    def register_schema(self, subject: str, schema_content: str) -> Tuple[int, int]:
        """Register schema and return (schema_id, version)"""
        # Generate schema ID from content hash
        schema_id = hash(schema_content) % (2**31)

        # Initialize subject if new
        if subject not in self.subjects:
            self.subjects[subject] = {
                "versions": []
            }

        # Add new version
        version = len(self.subjects[subject]["versions"]) + 1
        self.subjects[subject]["versions"].append({
            "version": version,
            "schema_id": schema_id
        })

        # Store schema content
        self.schemas[str(schema_id)] = {
            "id": schema_id,
            "content": schema_content
        }

        self._save_data()
        return schema_id, version

    def get_schema_by_id(self, schema_id: int) -> str:
        """Get schema content by ID"""
        if str(schema_id) not in self.schemas:
            raise ValueError(f"Schema ID {schema_id} not found")
        return self.schemas[str(schema_id)]["content"]

    def get_latest_schema(self, subject: str) -> SchemaInfo:
        """Get latest version of schema"""
        if subject not in self.subjects:
            raise ValueError(f"Subject {subject} not found")

        versions = self.subjects[subject]["versions"]
        latest = versions[-1]

        schema_content = self.get_schema_by_id(latest["schema_id"])

        return SchemaInfo(
            id=latest["schema_id"],
            version=latest["version"],
            schema=schema_content,
            subject=subject
        )

    def list_subjects(self) -> List[str]:
        """List all subjects"""
        return list(self.subjects.keys())

    def list_versions(self, subject: str) -> List[int]:
        """List all versions for subject"""
        if subject not in self.subjects:
            return []
        return [v["version"] for v in self.subjects[subject]["versions"]]


def load_proto_file(proto_file: Path) -> str:
    """Load proto file content"""
    if not proto_file.exists():
        raise FileNotFoundError(f"Proto file not found: {proto_file}")
    return proto_file.read_text()


def demo_confluent_registry() -> None:
    """Demonstrate Confluent Schema Registry integration"""
    print("Confluent Schema Registry Demo")
    print("=" * 60)

    registry = SchemaRegistry("http://localhost:8081")

    # Check if registry is available
    try:
        subjects = registry.list_subjects()
        print(f"✓ Connected to schema registry")
        print(f"  Existing subjects: {len(subjects)}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to connect: {e}")
        print("\nNote: Start schema registry with:")
        print("  docker run -p 8081:8081 confluentinc/cp-schema-registry")
        return

    # Register schema
    subject = "user.User"
    schema_content = """
    syntax = "proto3";
    package user;
    message User {
        string id = 1;
        string email = 2;
        string name = 3;
    }
    """

    try:
        schema_id, version = registry.register_schema(subject, schema_content)
        print(f"\n✓ Registered schema:")
        print(f"  Subject: {subject}")
        print(f"  Schema ID: {schema_id}")
        print(f"  Version: {version}")
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Failed to register: {e}")

    # Get latest schema
    try:
        info = registry.get_latest_schema(subject)
        print(f"\n✓ Latest schema:")
        print(f"  Subject: {info.subject}")
        print(f"  Version: {info.version}")
        print(f"  Schema ID: {info.id}")
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Failed to get schema: {e}")

    # Check compatibility
    new_schema = """
    syntax = "proto3";
    package user;
    message User {
        string id = 1;
        string email = 2;
        string name = 3;
        string phone = 4;  // New field
    }
    """

    try:
        compatible = registry.check_compatibility(subject, new_schema)
        print(f"\n✓ Compatibility check:")
        print(f"  Compatible: {compatible}")
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Failed to check compatibility: {e}")

    # Get config
    try:
        config = registry.get_config()
        print(f"\n✓ Global config:")
        print(f"  Compatibility: {config.get('compatibilityLevel', 'NONE')}")
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Failed to get config: {e}")


def demo_custom_registry() -> None:
    """Demonstrate custom file-based registry"""
    print("Custom Schema Registry Demo")
    print("=" * 60)

    registry = CustomSchemaRegistry(Path("./registry_data"))

    # Register schemas
    subject = "user.User"

    schema_v1 = """
    syntax = "proto3";
    package user;
    message User {
        string id = 1;
        string email = 2;
    }
    """

    schema_id_v1, version_v1 = registry.register_schema(subject, schema_v1)
    print(f"✓ Registered v1:")
    print(f"  Schema ID: {schema_id_v1}")
    print(f"  Version: {version_v1}")

    schema_v2 = """
    syntax = "proto3";
    package user;
    message User {
        string id = 1;
        string email = 2;
        string name = 3;  // Added field
    }
    """

    schema_id_v2, version_v2 = registry.register_schema(subject, schema_v2)
    print(f"\n✓ Registered v2:")
    print(f"  Schema ID: {schema_id_v2}")
    print(f"  Version: {version_v2}")

    # Get latest
    latest = registry.get_latest_schema(subject)
    print(f"\n✓ Latest schema:")
    print(f"  Version: {latest.version}")
    print(f"  Schema ID: {latest.id}")

    # List versions
    versions = registry.list_versions(subject)
    print(f"\n✓ All versions: {versions}")

    # List subjects
    subjects = registry.list_subjects()
    print(f"✓ All subjects: {subjects}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Schema Registry integration example",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--mode',
        choices=['confluent', 'custom', 'both'],
        default='both',
        help="Registry mode (default: both)"
    )

    parser.add_argument(
        '--registry-url',
        default='http://localhost:8081',
        help="Confluent Schema Registry URL (default: http://localhost:8081)"
    )

    parser.add_argument(
        '--storage-dir',
        type=Path,
        default=Path('./registry_data'),
        help="Storage directory for custom registry (default: ./registry_data)"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point"""
    args = parse_args()

    if args.mode in ['confluent', 'both']:
        demo_confluent_registry()
        print()

    if args.mode in ['custom', 'both']:
        demo_custom_registry()

    return 0


if __name__ == '__main__':
    sys.exit(main())
