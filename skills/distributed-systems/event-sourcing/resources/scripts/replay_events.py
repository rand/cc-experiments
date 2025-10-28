#!/usr/bin/env python3
"""
Event Replay Tool

Replay events from event store to rebuild projections, debug aggregates,
perform temporal queries, or test new projection logic.

Usage:
    ./replay_events.py --source postgres://...@localhost/events --projection users
    ./replay_events.py --aggregate account-123 --debug
    ./replay_events.py --until 2025-10-01 --projection analytics
    ./replay_events.py --help

Examples:
    # Rebuild projection from all events
    ./replay_events.py --source postgres://localhost/events --projection user_view

    # Debug aggregate by replaying events step-by-step
    ./replay_events.py --source postgres://localhost/events --aggregate account-123 --debug

    # Temporal query: rebuild projection to specific point in time
    ./replay_events.py --source postgres://localhost/events --until "2025-10-01" --projection analytics

    # Replay from file for testing
    ./replay_events.py --file events.json --projection test_projection --dry-run
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from dataclasses import dataclass


@dataclass
class Event:
    """Event data structure"""
    position: Optional[int]
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    version: int
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime


class EventStore:
    """Interface for reading events from various sources"""

    @staticmethod
    def from_postgres(connection_string: str) -> 'PostgresEventStore':
        """Create PostgreSQL event store"""
        return PostgresEventStore(connection_string)

    @staticmethod
    def from_file(filepath: Path) -> 'FileEventStore':
        """Create file-based event store"""
        return FileEventStore(filepath)


class PostgresEventStore:
    """PostgreSQL event store implementation"""

    def __init__(self, connection_string: str):
        try:
            import psycopg2
            self.conn = psycopg2.connect(connection_string)
        except ImportError:
            raise ImportError("psycopg2 required. Install: pip install psycopg2-binary")

    def get_events(
        self,
        aggregate_id: Optional[str] = None,
        from_position: int = 0,
        until: Optional[datetime] = None
    ) -> List[Event]:
        """Get events from store"""
        cursor = self.conn.cursor()

        query_parts = [
            """
            SELECT id, event_id, event_type, aggregate_id, aggregate_type,
                   version, data, metadata, timestamp
            FROM events
            WHERE id > %s
            """
        ]
        params = [from_position]

        if aggregate_id:
            query_parts.append("AND aggregate_id = %s")
            params.append(aggregate_id)

        if until:
            query_parts.append("AND timestamp <= %s")
            params.append(until)

        query_parts.append("ORDER BY id ASC")
        query = " ".join(query_parts)

        cursor.execute(query, params)

        events = []
        for row in cursor.fetchall():
            events.append(Event(
                position=row[0],
                event_id=str(row[1]),
                event_type=row[2],
                aggregate_id=row[3],
                aggregate_type=row[4],
                version=row[5],
                data=row[6],
                metadata=row[7] if row[7] else {},
                timestamp=row[8]
            ))

        cursor.close()
        return events

    def stream_events(
        self,
        aggregate_id: Optional[str] = None,
        from_position: int = 0,
        until: Optional[datetime] = None
    ) -> Iterator[Event]:
        """Stream events one at a time (memory efficient)"""
        cursor = self.conn.cursor(name='event_stream')

        query_parts = [
            """
            SELECT id, event_id, event_type, aggregate_id, aggregate_type,
                   version, data, metadata, timestamp
            FROM events
            WHERE id > %s
            """
        ]
        params = [from_position]

        if aggregate_id:
            query_parts.append("AND aggregate_id = %s")
            params.append(aggregate_id)

        if until:
            query_parts.append("AND timestamp <= %s")
            params.append(until)

        query_parts.append("ORDER BY id ASC")
        query = " ".join(query_parts)

        cursor.execute(query, params)

        for row in cursor:
            yield Event(
                position=row[0],
                event_id=str(row[1]),
                event_type=row[2],
                aggregate_id=row[3],
                aggregate_type=row[4],
                version=row[5],
                data=row[6],
                metadata=row[7] if row[7] else {},
                timestamp=row[8]
            )

        cursor.close()


class FileEventStore:
    """File-based event store for testing"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        with open(filepath, 'r') as f:
            self.events_data = json.load(f)

        if not isinstance(self.events_data, list):
            self.events_data = [self.events_data]

    def get_events(
        self,
        aggregate_id: Optional[str] = None,
        from_position: int = 0,
        until: Optional[datetime] = None
    ) -> List[Event]:
        """Get events from file"""
        events = []
        for i, event_data in enumerate(self.events_data):
            if i < from_position:
                continue

            if aggregate_id and event_data.get('aggregateId') != aggregate_id:
                continue

            timestamp = datetime.fromisoformat(event_data['timestamp'].replace('Z', '+00:00'))

            if until and timestamp > until:
                continue

            events.append(Event(
                position=i,
                event_id=event_data.get('eventId', f'event-{i}'),
                event_type=event_data['eventType'],
                aggregate_id=event_data['aggregateId'],
                aggregate_type=event_data.get('aggregateType', 'Unknown'),
                version=event_data.get('version', 1),
                data=event_data.get('data', {}),
                metadata=event_data.get('metadata', {}),
                timestamp=timestamp
            ))

        return events

    def stream_events(self, **kwargs) -> Iterator[Event]:
        """Stream events from file"""
        for event in self.get_events(**kwargs):
            yield event


class AggregateDebugger:
    """Debug aggregate by replaying events step-by-step"""

    def __init__(self, aggregate_id: str, event_store):
        self.aggregate_id = aggregate_id
        self.event_store = event_store

    def replay(self, pause: bool = False):
        """Replay events with debugging output"""
        events = self.event_store.get_events(aggregate_id=self.aggregate_id)

        if not events:
            print(f"No events found for aggregate {self.aggregate_id}")
            return

        print(f"\n{'='*80}")
        print(f"Replaying {len(events)} events for aggregate: {self.aggregate_id}")
        print(f"{'='*80}\n")

        state = {}

        for i, event in enumerate(events, 1):
            print(f"Event {i}/{len(events)}: {event.event_type}")
            print(f"  ID: {event.event_id}")
            print(f"  Version: {event.version}")
            print(f"  Timestamp: {event.timestamp}")
            print(f"  Data: {json.dumps(event.data, indent=4)}")

            # Simulate state update (simplified)
            state.update(event.data)

            print(f"\n  State after event:")
            print(f"  {json.dumps(state, indent=4)}")
            print(f"\n{'-'*80}\n")

            if pause:
                input("Press Enter to continue to next event...")

        print(f"{'='*80}")
        print(f"Final state:")
        print(json.dumps(state, indent=2))
        print(f"{'='*80}\n")


class ProjectionRebuilder:
    """Rebuild projections from events"""

    def __init__(self, projection_name: str, event_store, target_db=None):
        self.projection_name = projection_name
        self.event_store = event_store
        self.target_db = target_db

    def rebuild(
        self,
        until: Optional[datetime] = None,
        dry_run: bool = False,
        batch_size: int = 100
    ):
        """Rebuild projection from events"""
        print(f"\n{'='*80}")
        print(f"Rebuilding projection: {self.projection_name}")
        if until:
            print(f"Until: {until}")
        if dry_run:
            print("DRY RUN - No changes will be made")
        print(f"{'='*80}\n")

        # Clear projection (if not dry run)
        if not dry_run and self.target_db:
            self._clear_projection()

        # Replay events
        event_count = 0
        batch = []

        for event in self.event_store.stream_events(until=until):
            event_count += 1
            batch.append(event)

            print(f"Processing event {event_count}: {event.event_type} ({event.aggregate_id})")

            if not dry_run:
                self._apply_event(event)

            # Batch commit
            if len(batch) >= batch_size:
                if not dry_run and self.target_db:
                    self._commit_batch()
                print(f"  Batch committed ({len(batch)} events)")
                batch = []

        # Final commit
        if batch and not dry_run and self.target_db:
            self._commit_batch()
            print(f"  Final batch committed ({len(batch)} events)")

        print(f"\n{'='*80}")
        print(f"Projection rebuild complete")
        print(f"Total events processed: {event_count}")
        print(f"{'='*80}\n")

    def _clear_projection(self):
        """Clear projection data (to be implemented per projection)"""
        print(f"Clearing projection {self.projection_name}...")
        # Implementation depends on target database
        # Example for PostgreSQL:
        # cursor = self.target_db.cursor()
        # SECURITY: Validate projection_name is from config, not user input
        # cursor.execute(f"TRUNCATE TABLE {self.projection_name}")
        # self.target_db.commit()

    def _apply_event(self, event: Event):
        """Apply event to projection (to be implemented per projection)"""
        # Implementation depends on projection logic
        # This is a placeholder
        pass

    def _commit_batch(self):
        """Commit batch of changes"""
        if self.target_db:
            self.target_db.commit()


class TemporalQuery:
    """Perform temporal queries on event store"""

    def __init__(self, event_store):
        self.event_store = event_store

    def query_at_time(self, aggregate_id: str, at_time: datetime) -> Dict[str, Any]:
        """Query aggregate state at specific point in time"""
        print(f"\nQuerying aggregate {aggregate_id} at {at_time}\n")

        events = self.event_store.get_events(aggregate_id=aggregate_id, until=at_time)

        if not events:
            print(f"No events found for {aggregate_id} before {at_time}")
            return {}

        # Rebuild state from events
        state = {}
        for event in events:
            state.update(event.data)
            print(f"Applied: {event.event_type} (version {event.version}) at {event.timestamp}")

        print(f"\nState at {at_time}:")
        print(json.dumps(state, indent=2))

        return state

    def compare_times(self, aggregate_id: str, time1: datetime, time2: datetime):
        """Compare aggregate state at two different times"""
        print(f"\nComparing aggregate {aggregate_id}")
        print(f"Time 1: {time1}")
        print(f"Time 2: {time2}\n")

        state1 = self.query_at_time(aggregate_id, time1)
        print("\n" + "="*80 + "\n")
        state2 = self.query_at_time(aggregate_id, time2)

        print(f"\n{'='*80}")
        print("Differences:")
        print(f"{'='*80}\n")

        all_keys = set(state1.keys()) | set(state2.keys())
        for key in sorted(all_keys):
            val1 = state1.get(key, '<missing>')
            val2 = state2.get(key, '<missing>')
            if val1 != val2:
                print(f"{key}:")
                print(f"  Time 1: {val1}")
                print(f"  Time 2: {val2}")


class EventStatistics:
    """Analyze event store statistics"""

    def __init__(self, event_store):
        self.event_store = event_store

    def analyze(self):
        """Analyze events and print statistics"""
        print(f"\n{'='*80}")
        print("Event Store Statistics")
        print(f"{'='*80}\n")

        events = self.event_store.get_events()

        if not events:
            print("No events in store")
            return

        # Count by type
        type_counts = {}
        aggregate_counts = {}
        for event in events:
            type_counts[event.event_type] = type_counts.get(event.event_type, 0) + 1
            aggregate_counts[event.aggregate_id] = aggregate_counts.get(event.aggregate_id, 0) + 1

        print(f"Total events: {len(events)}")
        print(f"Unique aggregates: {len(aggregate_counts)}")
        print(f"Event types: {len(type_counts)}")
        print(f"Date range: {events[0].timestamp} to {events[-1].timestamp}")

        print(f"\nTop event types:")
        for event_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {event_type}: {count}")

        print(f"\nTop aggregates by event count:")
        for aggregate_id, count in sorted(aggregate_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {aggregate_id}: {count} events")

        print(f"\n{'='*80}\n")


def parse_datetime(date_string: str) -> datetime:
    """Parse datetime from various formats"""
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue

    # Try ISO format with timezone
    try:
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError(f"Unable to parse datetime: {date_string}")


def main():
    parser = argparse.ArgumentParser(
        description='Replay events from event store',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Source
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--source', type=str, help='Event store connection string (postgres://...)')
    source_group.add_argument('--file', type=Path, help='JSON file containing events')

    # Mode
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--projection', type=str, help='Rebuild projection')
    mode_group.add_argument('--aggregate', type=str, help='Debug aggregate')
    mode_group.add_argument('--temporal', type=str, help='Temporal query for aggregate')
    mode_group.add_argument('--stats', action='store_true', help='Show event store statistics')

    # Options
    parser.add_argument('--until', type=str, help='Replay until timestamp (YYYY-MM-DD or ISO8601)')
    parser.add_argument('--debug', action='store_true', help='Step-by-step debugging')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no changes)')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for projection rebuild')
    parser.add_argument('--compare', type=str, help='Second timestamp for temporal comparison')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    # Parse until timestamp
    until = None
    if args.until:
        until = parse_datetime(args.until)

    # Create event store
    try:
        if args.source:
            event_store = EventStore.from_postgres(args.source)
        elif args.file:
            event_store = EventStore.from_file(args.file)
        else:
            parser.error("No source specified")
    except Exception as e:
        print(f"Error connecting to event store: {e}", file=sys.stderr)
        sys.exit(1)

    # Execute mode
    try:
        if args.projection:
            rebuilder = ProjectionRebuilder(args.projection, event_store)
            rebuilder.rebuild(until=until, dry_run=args.dry_run, batch_size=args.batch_size)

        elif args.aggregate:
            debugger = AggregateDebugger(args.aggregate, event_store)
            debugger.replay(pause=args.debug)

        elif args.temporal:
            temporal = TemporalQuery(event_store)
            if args.compare:
                time1 = parse_datetime(args.until) if args.until else datetime.now()
                time2 = parse_datetime(args.compare)
                temporal.compare_times(args.temporal, time1, time2)
            else:
                at_time = parse_datetime(args.until) if args.until else datetime.now()
                temporal.query_at_time(args.temporal, at_time)

        elif args.stats:
            stats = EventStatistics(event_store)
            stats.analyze()

    except Exception as e:
        print(f"Error during replay: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
