"""
User View Projection - Event Sourcing Example

Demonstrates how to build a read model (projection) from events.
This projection maintains a denormalized view optimized for queries.

Features:
- Event handling
- Idempotent operations
- Checkpoint management
- Continuous processing
- Error handling
"""

import json
import time
from typing import Any, Dict, Optional
from datetime import datetime
import psycopg2
from dataclasses import dataclass


@dataclass
class Event:
    """Event data structure"""
    position: int
    event_id: str
    event_type: str
    aggregate_id: str
    data: Dict[str, Any]
    timestamp: datetime


class UserProjection:
    """
    User view projection - builds denormalized read model from events

    Read model schema:
        user_view (
            user_id VARCHAR PRIMARY KEY,
            email VARCHAR,
            name VARCHAR,
            status VARCHAR,
            registered_at TIMESTAMP,
            last_login_at TIMESTAMP,
            last_updated TIMESTAMP
        )
    """

    def __init__(self, database_connection_string: str):
        self.db_conn = psycopg2.connect(database_connection_string)
        self.projection_name = 'user_view'

    def handle(self, event: Event):
        """
        Handle event and update projection

        This is idempotent - applying the same event multiple times
        produces the same result.
        """
        if event.event_type == 'UserRegistered':
            self._handle_user_registered(event)
        elif event.event_type == 'UserEmailChanged':
            self._handle_user_email_changed(event)
        elif event.event_type == 'UserNameChanged':
            self._handle_user_name_changed(event)
        elif event.event_type == 'UserActivated':
            self._handle_user_activated(event)
        elif event.event_type == 'UserDeactivated':
            self._handle_user_deactivated(event)
        elif event.event_type == 'UserLoggedIn':
            self._handle_user_logged_in(event)
        elif event.event_type == 'UserDeleted':
            self._handle_user_deleted(event)

    def _handle_user_registered(self, event: Event):
        """Create user in read model"""
        cursor = self.db_conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_view (
                user_id, email, name, status, registered_at, last_updated
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (
                event.data['userId'],
                event.data['email'],
                event.data.get('name', ''),
                'pending',
                event.timestamp,
                event.timestamp
            )
        )

        self.db_conn.commit()
        cursor.close()

    def _handle_user_email_changed(self, event: Event):
        """Update user email"""
        cursor = self.db_conn.cursor()

        cursor.execute(
            """
            UPDATE user_view
            SET email = %s, last_updated = %s
            WHERE user_id = %s
            """,
            (event.data['newEmail'], event.timestamp, event.data['userId'])
        )

        self.db_conn.commit()
        cursor.close()

    def _handle_user_name_changed(self, event: Event):
        """Update user name"""
        cursor = self.db_conn.cursor()

        cursor.execute(
            """
            UPDATE user_view
            SET name = %s, last_updated = %s
            WHERE user_id = %s
            """,
            (event.data['newName'], event.timestamp, event.data['userId'])
        )

        self.db_conn.commit()
        cursor.close()

    def _handle_user_activated(self, event: Event):
        """Activate user"""
        cursor = self.db_conn.cursor()

        cursor.execute(
            """
            UPDATE user_view
            SET status = 'active', last_updated = %s
            WHERE user_id = %s
            """,
            (event.timestamp, event.data['userId'])
        )

        self.db_conn.commit()
        cursor.close()

    def _handle_user_deactivated(self, event: Event):
        """Deactivate user"""
        cursor = self.db_conn.cursor()

        cursor.execute(
            """
            UPDATE user_view
            SET status = 'inactive', last_updated = %s
            WHERE user_id = %s
            """,
            (event.timestamp, event.data['userId'])
        )

        self.db_conn.commit()
        cursor.close()

    def _handle_user_logged_in(self, event: Event):
        """Update last login timestamp"""
        cursor = self.db_conn.cursor()

        cursor.execute(
            """
            UPDATE user_view
            SET last_login_at = %s, last_updated = %s
            WHERE user_id = %s
            """,
            (event.timestamp, event.timestamp, event.data['userId'])
        )

        self.db_conn.commit()
        cursor.close()

    def _handle_user_deleted(self, event: Event):
        """Soft delete user (mark as deleted)"""
        cursor = self.db_conn.cursor()

        cursor.execute(
            """
            UPDATE user_view
            SET status = 'deleted', last_updated = %s
            WHERE user_id = %s
            """,
            (event.timestamp, event.data['userId'])
        )

        self.db_conn.commit()
        cursor.close()

    def clear(self):
        """Clear projection data (for rebuild)"""
        cursor = self.db_conn.cursor()
        # SECURITY: projection_name is set in __init__ from config, not user input
        # Clear projection table for rebuild - safe operation with validated table name
        cursor.execute(f"TRUNCATE TABLE {self.projection_name}")
        self.db_conn.commit()
        cursor.close()


class ProjectionRunner:
    """
    Continuously runs projections, processing new events

    Features:
    - Checkpoint management
    - Error handling with retry
    - Batch processing
    - Multiple projection support
    """

    def __init__(self, event_store_connection: str, projections: Dict[str, UserProjection]):
        self.event_store_conn = psycopg2.connect(event_store_connection)
        self.projections = projections

    def run(self, poll_interval: float = 1.0, batch_size: int = 100):
        """
        Run projections continuously

        Args:
            poll_interval: Seconds to wait between polls
            batch_size: Number of events to process per batch
        """
        print(f"Starting projection runner for: {list(self.projections.keys())}")

        try:
            while True:
                for projection_name, projection in self.projections.items():
                    try:
                        # Get checkpoint
                        checkpoint = self._get_checkpoint(projection_name)

                        # Stream events from checkpoint
                        events = self._fetch_events_batch(checkpoint, batch_size)

                        if events:
                            print(f"Processing {len(events)} events for {projection_name}")

                            for event in events:
                                try:
                                    # Handle event
                                    projection.handle(event)

                                    # Update checkpoint
                                    self._update_checkpoint(projection_name, event.position)

                                except Exception as e:
                                    print(f"Error processing event {event.event_id}: {e}")
                                    # Implement retry logic or dead letter queue here
                                    raise

                        # Poll interval
                        time.sleep(poll_interval)

                    except Exception as e:
                        print(f"Error in projection {projection_name}: {e}")
                        time.sleep(poll_interval * 2)  # Back off on error

        except KeyboardInterrupt:
            print("\nProjection runner stopped")

    def _get_checkpoint(self, projection_name: str) -> int:
        """Get last processed position for projection"""
        cursor = self.event_store_conn.cursor()

        cursor.execute(
            """
            SELECT last_event_id FROM projection_checkpoints
            WHERE projection_name = %s
            """,
            (projection_name,)
        )

        result = cursor.fetchone()
        cursor.close()

        return result[0] if result else 0

    def _update_checkpoint(self, projection_name: str, position: int):
        """Update checkpoint for projection"""
        cursor = self.event_store_conn.cursor()

        cursor.execute(
            """
            INSERT INTO projection_checkpoints (projection_name, last_event_id, last_processed_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (projection_name)
            DO UPDATE SET last_event_id = EXCLUDED.last_event_id,
                         last_processed_at = EXCLUDED.last_processed_at
            """,
            (projection_name, position)
        )

        self.event_store_conn.commit()
        cursor.close()

    def _fetch_events_batch(self, from_position: int, limit: int) -> list[Event]:
        """Fetch batch of events from event store"""
        cursor = self.event_store_conn.cursor()

        cursor.execute(
            """
            SELECT id, event_id, event_type, aggregate_id, data, timestamp
            FROM events
            WHERE id > %s
            ORDER BY id ASC
            LIMIT %s
            """,
            (from_position, limit)
        )

        events = []
        for row in cursor.fetchall():
            events.append(Event(
                position=row[0],
                event_id=str(row[1]),
                event_type=row[2],
                aggregate_id=row[3],
                data=row[4],
                timestamp=row[5]
            ))

        cursor.close()
        return events


# Usage example
if __name__ == '__main__':
    # Database connections
    event_store_conn = 'postgresql://user:password@localhost/eventstore'
    read_model_conn = 'postgresql://user:password@localhost/readmodel'

    # Create projection
    user_projection = UserProjection(read_model_conn)

    # Create projection runner
    runner = ProjectionRunner(
        event_store_connection=event_store_conn,
        projections={
            'user_view': user_projection
        }
    )

    # Run continuously
    runner.run(poll_interval=1.0, batch_size=100)
