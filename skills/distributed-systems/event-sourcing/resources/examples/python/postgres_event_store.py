"""
PostgreSQL Event Store Implementation

Production-ready event store implementation using PostgreSQL with:
- Optimistic concurrency control
- Event streaming
- Snapshots
- Transaction support
- Connection pooling

Schema:
    events (id, event_id, event_type, aggregate_id, aggregate_type, version, data, metadata, timestamp)
    streams (aggregate_id, aggregate_type, current_version, created_at, updated_at)
    snapshots (aggregate_id, version, data, timestamp)
"""

import json
import psycopg2
from psycopg2 import pool
from typing import Any, Dict, Iterator, List, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid


class ConcurrencyException(Exception):
    """Raised when optimistic concurrency check fails"""
    pass


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


@dataclass
class Snapshot:
    """Snapshot data structure"""
    aggregate_id: str
    version: int
    data: Dict[str, Any]
    timestamp: datetime


class PostgresEventStore:
    """
    PostgreSQL-based event store with full event sourcing capabilities
    """

    def __init__(self, connection_string: str, min_connections: int = 1, max_connections: int = 10):
        """
        Initialize event store with connection pool

        Args:
            connection_string: PostgreSQL connection string
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
        """
        self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
            min_connections,
            max_connections,
            connection_string
        )

    def __del__(self):
        """Close all connections"""
        if hasattr(self, 'connection_pool'):
            self.connection_pool.closeall()

    def append_events(
        self,
        aggregate_id: str,
        aggregate_type: str,
        expected_version: int,
        events: List[Dict[str, Any]]
    ) -> int:
        """
        Append events to stream with optimistic concurrency control

        Args:
            aggregate_id: Aggregate identifier
            aggregate_type: Type of aggregate
            expected_version: Expected current version (for optimistic locking)
            events: List of event data dictionaries

        Returns:
            int: New version after appending events

        Raises:
            ConcurrencyException: If expected_version doesn't match current version
        """
        conn = self.connection_pool.getconn()
        cursor = conn.cursor()

        try:
            # Lock stream and check version
            cursor.execute(
                "SELECT current_version FROM streams WHERE aggregate_id = %s FOR UPDATE",
                (aggregate_id,)
            )
            result = cursor.fetchone()

            if result is None:
                current_version = 0
            else:
                current_version = result[0]

            # Optimistic concurrency check
            if current_version != expected_version:
                raise ConcurrencyException(
                    f"Concurrency conflict: expected version {expected_version}, "
                    f"but stream is at version {current_version}"
                )

            # Append events
            for i, event in enumerate(events):
                version = expected_version + i + 1

                cursor.execute(
                    """
                    INSERT INTO events (
                        event_id, event_type, aggregate_id, aggregate_type,
                        version, data, metadata, timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event.get('eventId', str(uuid.uuid4())),
                        event['eventType'],
                        aggregate_id,
                        aggregate_type,
                        version,
                        json.dumps(event['data']),
                        json.dumps(event.get('metadata', {})),
                        event.get('timestamp', datetime.now())
                    )
                )

            # Update stream version
            new_version = expected_version + len(events)

            if result is None:
                cursor.execute(
                    """
                    INSERT INTO streams (
                        aggregate_id, aggregate_type, current_version,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, NOW(), NOW())
                    """,
                    (aggregate_id, aggregate_type, new_version)
                )
            else:
                cursor.execute(
                    """
                    UPDATE streams
                    SET current_version = %s, updated_at = NOW()
                    WHERE aggregate_id = %s
                    """,
                    (new_version, aggregate_id)
                )

            conn.commit()
            return new_version

        except Exception as e:
            conn.rollback()
            raise
        finally:
            cursor.close()
            self.connection_pool.putconn(conn)

    def get_events(
        self,
        aggregate_id: str,
        from_version: int = 1,
        to_version: Optional[int] = None
    ) -> List[Event]:
        """
        Get events for an aggregate

        Args:
            aggregate_id: Aggregate identifier
            from_version: Starting version (inclusive)
            to_version: Ending version (inclusive), None for all

        Returns:
            List[Event]: List of events in order
        """
        conn = self.connection_pool.getconn()
        cursor = conn.cursor()

        try:
            if to_version:
                cursor.execute(
                    """
                    SELECT id, event_id, event_type, aggregate_id, aggregate_type,
                           version, data, metadata, timestamp
                    FROM events
                    WHERE aggregate_id = %s AND version >= %s AND version <= %s
                    ORDER BY version ASC
                    """,
                    (aggregate_id, from_version, to_version)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, event_id, event_type, aggregate_id, aggregate_type,
                           version, data, metadata, timestamp
                    FROM events
                    WHERE aggregate_id = %s AND version >= %s
                    ORDER BY version ASC
                    """,
                    (aggregate_id, from_version)
                )

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

            return events

        finally:
            cursor.close()
            self.connection_pool.putconn(conn)

    def stream_events(
        self,
        from_position: int = 0,
        event_types: Optional[List[str]] = None,
        aggregate_types: Optional[List[str]] = None
    ) -> Iterator[Event]:
        """
        Stream all events from a global position (for projections)

        Args:
            from_position: Starting position (event ID)
            event_types: Filter by event types (optional)
            aggregate_types: Filter by aggregate types (optional)

        Yields:
            Event: Events in order
        """
        conn = self.connection_pool.getconn()
        cursor = conn.cursor(name='event_stream_cursor')

        try:
            query_parts = [
                """
                SELECT id, event_id, event_type, aggregate_id, aggregate_type,
                       version, data, metadata, timestamp
                FROM events
                WHERE id > %s
                """
            ]
            params = [from_position]

            if event_types:
                query_parts.append(f"AND event_type = ANY(%s)")
                params.append(event_types)

            if aggregate_types:
                query_parts.append(f"AND aggregate_type = ANY(%s)")
                params.append(aggregate_types)

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

        finally:
            cursor.close()
            self.connection_pool.putconn(conn)

    def save_snapshot(self, aggregate_id: str, version: int, data: Dict[str, Any]):
        """
        Save aggregate snapshot

        Args:
            aggregate_id: Aggregate identifier
            version: Aggregate version at snapshot time
            data: Aggregate state data
        """
        conn = self.connection_pool.getconn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO snapshots (aggregate_id, version, data, timestamp)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (aggregate_id, version) DO UPDATE
                SET data = EXCLUDED.data, timestamp = EXCLUDED.timestamp
                """,
                (aggregate_id, version, json.dumps(data))
            )
            conn.commit()

        finally:
            cursor.close()
            self.connection_pool.putconn(conn)

    def get_latest_snapshot(self, aggregate_id: str) -> Optional[Snapshot]:
        """
        Get latest snapshot for aggregate

        Args:
            aggregate_id: Aggregate identifier

        Returns:
            Optional[Snapshot]: Latest snapshot or None
        """
        conn = self.connection_pool.getconn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT aggregate_id, version, data, timestamp
                FROM snapshots
                WHERE aggregate_id = %s
                ORDER BY version DESC
                LIMIT 1
                """,
                (aggregate_id,)
            )

            row = cursor.fetchone()
            if row:
                return Snapshot(
                    aggregate_id=row[0],
                    version=row[1],
                    data=row[2],
                    timestamp=row[3]
                )

            return None

        finally:
            cursor.close()
            self.connection_pool.putconn(conn)

    def get_stream_version(self, aggregate_id: str) -> Optional[int]:
        """
        Get current version of aggregate stream

        Args:
            aggregate_id: Aggregate identifier

        Returns:
            Optional[int]: Current version or None if stream doesn't exist
        """
        conn = self.connection_pool.getconn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT current_version FROM streams WHERE aggregate_id = %s",
                (aggregate_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

        finally:
            cursor.close()
            self.connection_pool.putconn(conn)


# Usage example
if __name__ == '__main__':
    # Initialize event store
    event_store = PostgresEventStore(
        connection_string='postgresql://user:password@localhost/eventstore'
    )

    # Append events
    events = [
        {
            'eventType': 'AccountOpened',
            'data': {
                'accountId': 'account-123',
                'owner': 'Alice',
                'initialDeposit': '1000.00'
            },
            'metadata': {'userId': 'admin-1'}
        },
        {
            'eventType': 'MoneyDeposited',
            'data': {
                'accountId': 'account-123',
                'amount': '500.00',
                'balanceAfter': '1500.00'
            },
            'metadata': {'userId': 'admin-1'}
        }
    ]

    try:
        new_version = event_store.append_events(
            aggregate_id='account-123',
            aggregate_type='BankAccount',
            expected_version=0,
            events=events
        )
        print(f"Events appended, new version: {new_version}")

    except ConcurrencyException as e:
        print(f"Concurrency conflict: {e}")

    # Read events
    loaded_events = event_store.get_events('account-123')
    print(f"\nLoaded {len(loaded_events)} events:")
    for event in loaded_events:
        print(f"  v{event.version}: {event.event_type}")

    # Save snapshot
    snapshot_data = {
        'owner': 'Alice',
        'balance': '1500.00',
        'status': 'active'
    }
    event_store.save_snapshot('account-123', new_version, snapshot_data)
    print(f"\nSnapshot saved at version {new_version}")

    # Load snapshot
    snapshot = event_store.get_latest_snapshot('account-123')
    if snapshot:
        print(f"Loaded snapshot: version {snapshot.version}, data: {snapshot.data}")
