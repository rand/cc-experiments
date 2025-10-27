#!/usr/bin/env python3
"""
Event Schema Validator

Validates event schemas and design patterns for event-sourced systems.
Checks for proper naming, structure, idempotency, and best practices.

Usage:
    ./validate_events.py --file events.json
    ./validate_events.py --directory ./events
    ./validate_events.py --stream postgres://...@localhost/events --aggregate-id order-123
    ./validate_events.py --help

Examples:
    # Validate single event file
    ./validate_events.py --file my-event.json

    # Validate all events in directory
    ./validate_events.py --directory ./events --json

    # Validate events from event store
    ./validate_events.py --stream postgres://user:pass@localhost/eventstore --aggregate-id account-123
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


@dataclass
class ValidationResult:
    """Result of event validation"""
    valid: bool
    event_type: str
    event_id: Optional[str]
    errors: List[str]
    warnings: List[str]
    info: List[str]


class EventValidator:
    """Validates event schemas and design patterns"""

    REQUIRED_FIELDS = {'eventId', 'eventType', 'aggregateId', 'timestamp', 'data'}
    RECOMMENDED_FIELDS = {'aggregateType', 'version', 'metadata'}

    # Event naming patterns
    PAST_TENSE_PATTERN = re.compile(r'^[A-Z][a-zA-Z]+(ed|Created|Opened|Closed|Placed|Processed|Sent|Received|Updated|Deleted|Changed|Added|Removed|Activated|Deactivated|Approved|Rejected|Completed|Cancelled|Failed|Succeeded)$')

    # Common anti-patterns
    COMMAND_SUFFIXES = ['Request', 'Command', 'Action']
    PRESENT_TENSE_VERBS = ['Create', 'Update', 'Delete', 'Place', 'Process', 'Send', 'Receive']

    def __init__(self, strict: bool = False, max_payload_size: int = 10240):
        self.strict = strict
        self.max_payload_size = max_payload_size

    def validate_event(self, event: Dict[str, Any]) -> ValidationResult:
        """Validate single event"""
        errors = []
        warnings = []
        info = []

        event_type = event.get('eventType', 'Unknown')
        event_id = event.get('eventId')

        # Check required fields
        missing = self.REQUIRED_FIELDS - set(event.keys())
        if missing:
            errors.append(f"Missing required fields: {missing}")

        # Check recommended fields
        missing_recommended = self.RECOMMENDED_FIELDS - set(event.keys())
        if missing_recommended:
            warnings.append(f"Missing recommended fields: {missing_recommended}")

        # Validate event type naming
        if 'eventType' in event:
            event_naming_result = self._validate_event_naming(event['eventType'])
            errors.extend(event_naming_result['errors'])
            warnings.extend(event_naming_result['warnings'])
            info.extend(event_naming_result['info'])

        # Validate event ID
        if 'eventId' in event:
            if not self._is_valid_uuid(event['eventId']):
                warnings.append(f"Event ID '{event['eventId']}' is not a UUID")

        # Validate timestamp
        if 'timestamp' in event:
            if not self._is_valid_timestamp(event['timestamp']):
                errors.append(f"Invalid timestamp format: {event['timestamp']}")

        # Validate data payload
        if 'data' in event:
            data_result = self._validate_payload(event['data'])
            errors.extend(data_result['errors'])
            warnings.extend(data_result['warnings'])

        # Validate version
        if 'version' in event:
            if not isinstance(event['version'], int) or event['version'] < 1:
                errors.append(f"Version must be positive integer, got: {event['version']}")

        # Check for metadata
        if 'metadata' in event:
            metadata_result = self._validate_metadata(event['metadata'])
            warnings.extend(metadata_result['warnings'])
            info.extend(metadata_result['info'])

        # Check event size
        event_size = len(json.dumps(event).encode('utf-8'))
        if event_size > self.max_payload_size:
            errors.append(f"Event size ({event_size} bytes) exceeds limit ({self.max_payload_size} bytes)")
        elif event_size > self.max_payload_size * 0.8:
            warnings.append(f"Event size ({event_size} bytes) is close to limit ({self.max_payload_size} bytes)")

        # Additional checks
        self._check_antipatterns(event, errors, warnings)

        valid = len(errors) == 0
        if self.strict and warnings:
            valid = False

        return ValidationResult(
            valid=valid,
            event_type=event_type,
            event_id=event_id,
            errors=errors,
            warnings=warnings,
            info=info
        )

    def _validate_event_naming(self, event_type: str) -> Dict[str, List[str]]:
        """Validate event type naming conventions"""
        errors = []
        warnings = []
        info = []

        # Check for command suffixes
        for suffix in self.COMMAND_SUFFIXES:
            if event_type.endswith(suffix):
                errors.append(f"Event name '{event_type}' looks like a command (ends with {suffix}). Events should be past tense facts.")

        # Check for present tense verbs
        for verb in self.PRESENT_TENSE_VERBS:
            if event_type.startswith(verb):
                errors.append(f"Event name '{event_type}' uses present tense verb '{verb}'. Use past tense (e.g., {verb}d or {verb}ed)")

        # Check past tense pattern
        if not self.PAST_TENSE_PATTERN.match(event_type):
            warnings.append(f"Event name '{event_type}' doesn't follow past tense naming convention")

        # Check PascalCase
        if not event_type[0].isupper():
            errors.append(f"Event type '{event_type}' should be PascalCase")

        if '_' in event_type:
            warnings.append(f"Event type '{event_type}' uses underscores, prefer PascalCase")

        info.append(f"Event type '{event_type}' validated")

        return {'errors': errors, 'warnings': warnings, 'info': info}

    def _validate_payload(self, data: Any) -> Dict[str, List[str]]:
        """Validate event payload"""
        errors = []
        warnings = []

        if not isinstance(data, dict):
            errors.append(f"Event data should be object/dict, got {type(data).__name__}")
            return {'errors': errors, 'warnings': warnings}

        # Check for empty payload
        if not data:
            warnings.append("Event data is empty")

        # Check for derived data (hints only)
        suspicious_fields = ['computed', 'calculated', 'derived', 'total', 'summary']
        for field in data.keys():
            if any(s in field.lower() for s in suspicious_fields):
                warnings.append(f"Field '{field}' might contain derived data (avoid if possible)")

        # Check for mutable references
        reference_patterns = ['current', 'latest', 'active']
        for field in data.keys():
            if any(p in field.lower() for p in reference_patterns):
                warnings.append(f"Field '{field}' might reference mutable state")

        return {'errors': errors, 'warnings': warnings}

    def _validate_metadata(self, metadata: Any) -> Dict[str, List[str]]:
        """Validate event metadata"""
        warnings = []
        info = []

        if not isinstance(metadata, dict):
            warnings.append(f"Metadata should be object/dict, got {type(metadata).__name__}")
            return {'warnings': warnings, 'info': info}

        # Check for recommended metadata fields
        recommended = ['causationId', 'correlationId', 'userId']
        present = [f for f in recommended if f in metadata]
        missing = [f for f in recommended if f not in metadata]

        if present:
            info.append(f"Metadata contains: {', '.join(present)}")
        if missing:
            info.append(f"Consider adding metadata: {', '.join(missing)}")

        return {'warnings': warnings, 'info': info}

    def _check_antipatterns(self, event: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Check for common anti-patterns"""

        # Check for CRUD-like events
        crud_verbs = ['Update', 'Updated', 'Change', 'Changed', 'Modify', 'Modified']
        event_type = event.get('eventType', '')
        if any(verb in event_type for verb in crud_verbs):
            warnings.append(f"Event '{event_type}' uses generic CRUD verb. Consider more specific domain events.")

        # Check for multiple changes in one event
        if 'data' in event and isinstance(event['data'], dict):
            if 'changes' in event['data'] or 'updates' in event['data']:
                warnings.append("Event contains 'changes' or 'updates' field - might be too coarse-grained")

        # Check for system/technical events (not domain events)
        technical_prefixes = ['System', 'Database', 'Cache', 'Queue']
        if any(event_type.startswith(prefix) for prefix in technical_prefixes):
            info = [i for i in warnings if not i.startswith("Event")]  # Remove from warnings
            info.append(f"Event '{event_type}' appears to be a technical/system event")

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        """Check if value is valid UUID"""
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
        return bool(uuid_pattern.match(value))

    @staticmethod
    def _is_valid_timestamp(value: str) -> bool:
        """Check if timestamp is valid ISO 8601 format"""
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
            return True
        except (ValueError, AttributeError):
            return False


class EventStoreReader:
    """Read events from various sources"""

    @staticmethod
    def read_from_file(filepath: Path) -> List[Dict[str, Any]]:
        """Read events from JSON file"""
        with open(filepath, 'r') as f:
            content = json.load(f)

        # Handle both single event and array of events
        if isinstance(content, list):
            return content
        else:
            return [content]

    @staticmethod
    def read_from_directory(dirpath: Path, pattern: str = "*.json") -> List[Dict[str, Any]]:
        """Read all JSON files from directory"""
        events = []
        for filepath in dirpath.glob(pattern):
            try:
                events.extend(EventStoreReader.read_from_file(filepath))
            except Exception as e:
                print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return events

    @staticmethod
    def read_from_postgres(connection_string: str, aggregate_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read events from PostgreSQL event store"""
        try:
            import psycopg2
        except ImportError:
            raise ImportError("psycopg2 required for PostgreSQL. Install: pip install psycopg2-binary")

        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()

        if aggregate_id:
            query = """
                SELECT event_id, event_type, aggregate_id, aggregate_type,
                       version, data, metadata, timestamp
                FROM events
                WHERE aggregate_id = %s
                ORDER BY version ASC
            """
            cursor.execute(query, (aggregate_id,))
        else:
            query = """
                SELECT event_id, event_type, aggregate_id, aggregate_type,
                       version, data, metadata, timestamp
                FROM events
                ORDER BY id ASC
                LIMIT 1000
            """
            cursor.execute(query)

        events = []
        for row in cursor.fetchall():
            events.append({
                'eventId': str(row[0]),
                'eventType': row[1],
                'aggregateId': row[2],
                'aggregateType': row[3],
                'version': row[4],
                'data': row[5],
                'metadata': row[6] if row[6] else {},
                'timestamp': row[7].isoformat()
            })

        cursor.close()
        conn.close()

        return events


def print_validation_results(results: List[ValidationResult], json_output: bool = False, verbose: bool = False):
    """Print validation results"""
    if json_output:
        output = {
            'total': len(results),
            'valid': sum(1 for r in results if r.valid),
            'invalid': sum(1 for r in results if not r.valid),
            'results': [
                {
                    'valid': r.valid,
                    'eventType': r.event_type,
                    'eventId': r.event_id,
                    'errors': r.errors,
                    'warnings': r.warnings,
                    'info': r.info if verbose else []
                }
                for r in results
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        valid_count = sum(1 for r in results if r.valid)
        invalid_count = len(results) - valid_count

        print(f"\n{'='*80}")
        print(f"Event Validation Report")
        print(f"{'='*80}")
        print(f"Total events: {len(results)}")
        print(f"Valid: {valid_count}")
        print(f"Invalid: {invalid_count}")
        print(f"{'='*80}\n")

        for i, result in enumerate(results, 1):
            status = "✓ VALID" if result.valid else "✗ INVALID"
            print(f"{i}. {result.event_type} ({result.event_id or 'no-id'}) - {status}")

            if result.errors:
                print("   ERRORS:")
                for error in result.errors:
                    print(f"     - {error}")

            if result.warnings:
                print("   WARNINGS:")
                for warning in result.warnings:
                    print(f"     - {warning}")

            if verbose and result.info:
                print("   INFO:")
                for info_msg in result.info:
                    print(f"     - {info_msg}")

            print()

        # Summary
        if invalid_count > 0:
            print(f"❌ Validation failed: {invalid_count} invalid event(s)")
            sys.exit(1)
        else:
            print(f"✅ All events valid!")


def main():
    parser = argparse.ArgumentParser(
        description='Validate event schemas and design patterns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Input sources
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--file', type=Path, help='JSON file containing event(s)')
    input_group.add_argument('--directory', type=Path, help='Directory containing event JSON files')
    input_group.add_argument('--stream', type=str, help='Event store connection string (postgres://...)')

    # Options
    parser.add_argument('--aggregate-id', type=str, help='Aggregate ID to filter events (for --stream)')
    parser.add_argument('--strict', action='store_true', help='Fail on warnings')
    parser.add_argument('--max-size', type=int, default=10240, help='Max event size in bytes (default: 10240)')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Read events
    try:
        if args.file:
            events = EventStoreReader.read_from_file(args.file)
        elif args.directory:
            events = EventStoreReader.read_from_directory(args.directory)
        elif args.stream:
            events = EventStoreReader.read_from_postgres(args.stream, args.aggregate_id)
        else:
            parser.error("No input source specified")
    except Exception as e:
        print(f"Error reading events: {e}", file=sys.stderr)
        sys.exit(1)

    if not events:
        print("No events found", file=sys.stderr)
        sys.exit(1)

    # Validate events
    validator = EventValidator(strict=args.strict, max_payload_size=args.max_size)
    results = [validator.validate_event(event) for event in events]

    # Print results
    print_validation_results(results, json_output=args.json, verbose=args.verbose)


if __name__ == '__main__':
    main()
