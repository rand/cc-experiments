# Event Sourcing Reference

**Scope**: Comprehensive guide to event sourcing architecture, event design, CQRS patterns, aggregates, projections, snapshots, and production implementations
**Lines**: ~3200
**Last Updated**: 2025-10-27

## Table of Contents

1. [Event Sourcing Fundamentals](#event-sourcing-fundamentals)
2. [Event Design Patterns](#event-design-patterns)
3. [Aggregate Design](#aggregate-design)
4. [Event Store Architecture](#event-store-architecture)
5. [Projections and Read Models](#projections-and-read-models)
6. [Snapshot Strategies](#snapshot-strategies)
7. [CQRS Integration](#cqrs-integration)
8. [Saga Patterns](#saga-patterns)
9. [Event Versioning and Schema Evolution](#event-versioning-and-schema-evolution)
10. [Temporal Queries and Event Replay](#temporal-queries-and-event-replay)
11. [Production Implementations](#production-implementations)
12. [Common Anti-Patterns](#common-anti-patterns)
13. [Performance Optimization](#performance-optimization)
14. [Testing Event-Sourced Systems](#testing-event-sourced-systems)

---

## Event Sourcing Fundamentals

### What is Event Sourcing?

**Event Sourcing** stores application state as a sequence of **immutable events** rather than mutable records.

**Core Principle**: Events are facts about what happened in the past. They are immutable and append-only.

```
Traditional:
  users = {id: 1, name: "Alice", email: "alice@example.com", status: "active"}

Event Sourced:
  events = [
    {type: "UserCreated", id: 1, name: "Alice", email: "alice@example.com"},
    {type: "UserEmailChanged", id: 1, email: "alice@newdomain.com"},
    {type: "UserActivated", id: 1}
  ]

  Current state = reduce(events, initial_state)
```

### Why Event Sourcing?

**Advantages**:
- **Complete audit trail**: Every state change is recorded
- **Temporal queries**: Query state at any point in time
- **Event replay**: Rebuild state from events
- **Debugging**: Reproduce exact sequence that led to a bug
- **Analytics**: Mine events for business insights
- **Flexibility**: New projections without data migration
- **Distributed systems**: Natural fit for event-driven architectures

**Disadvantages**:
- **Complexity**: More moving parts than CRUD
- **Learning curve**: Requires paradigm shift
- **Event versioning**: Schema evolution is challenging
- **Storage growth**: Events accumulate (mitigated by snapshots)
- **Eventual consistency**: Read models lag behind writes

### When to Use Event Sourcing

**Good fit**:
- Audit requirements are critical
- Complex business domains with rich behaviors
- Need to analyze historical data
- Building event-driven systems
- Temporal queries are valuable
- Multiple read models from same events

**Poor fit**:
- Simple CRUD applications
- Strict consistency requirements
- Team lacks event-driven experience
- Low tolerance for complexity

### Event Sourcing Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  Command    │────────▶│  Aggregate   │────────▶│ Event Store │
│  Handler    │         │  (Domain)    │         │  (Append)   │
└─────────────┘         └──────────────┘         └─────────────┘
                                                         │
                                                         │ Events
                                                         ▼
                                         ┌───────────────────────────┐
                                         │   Event Bus/Stream        │
                                         └───────────────────────────┘
                                                         │
                             ┌───────────────────────────┼───────────────────┐
                             ▼                           ▼                   ▼
                    ┌────────────────┐        ┌─────────────────┐  ┌────────────┐
                    │  Projection 1  │        │  Projection 2   │  │  Saga      │
                    │  (Read Model)  │        │  (Analytics)    │  │  (Process) │
                    └────────────────┘        └─────────────────┘  └────────────┘
```

**Key Components**:

1. **Command Handler**: Validates and executes commands
2. **Aggregate**: Business logic, produces events
3. **Event Store**: Append-only event log
4. **Event Bus**: Publishes events to subscribers
5. **Projections**: Build read models from events
6. **Sagas**: Coordinate long-running processes

---

## Event Design Patterns

### Event Naming Conventions

**Rule**: Events are **past tense** facts about what happened.

```python
# Good: Past tense, specific
UserRegistered
OrderPlaced
PaymentProcessed
InventoryReserved
EmailSent

# Bad: Present tense, vague
RegisterUser      # This is a command, not an event
PlaceOrder        # Command
ProcessPayment    # Command
UpdateInventory   # Too vague
SendEmail         # Command
```

### Event Structure

**Minimal event structure**:

```json
{
  "eventId": "uuid",
  "eventType": "UserRegistered",
  "aggregateId": "user-123",
  "aggregateType": "User",
  "version": 1,
  "timestamp": "2025-10-27T10:30:00Z",
  "data": {
    "userId": "user-123",
    "email": "alice@example.com",
    "name": "Alice"
  },
  "metadata": {
    "causationId": "command-456",
    "correlationId": "request-789",
    "userId": "admin-1"
  }
}
```

**Required fields**:
- `eventId`: Unique event identifier (UUID)
- `eventType`: Event type name (UserRegistered)
- `aggregateId`: ID of aggregate this event belongs to
- `version`: Version number within aggregate stream
- `timestamp`: When event occurred
- `data`: Event payload (domain-specific)

**Recommended fields**:
- `aggregateType`: Type of aggregate (User, Order, etc.)
- `metadata.causationId`: ID of command that caused this event
- `metadata.correlationId`: ID for tracing request across services
- `metadata.userId`: Who triggered this event

### Event Granularity

**Too coarse**:
```python
# Bad: Multiple changes in one event
UserUpdated(
    userId="123",
    changes={
        "email": "new@example.com",
        "name": "New Name",
        "address": {...}
    }
)
```

**Too fine**:
```python
# Bad: Overly granular
UserEmailFirstPartChanged(userId="123", firstPart="alice")
UserEmailDomainChanged(userId="123", domain="example.com")
```

**Just right**:
```python
# Good: Single business concept
UserEmailChanged(userId="123", email="alice@example.com")
UserNameChanged(userId="123", name="Alice")
UserAddressChanged(userId="123", address={...})
```

**Rule of thumb**: One event per business fact or invariant.

### Event Payload Design

**Include everything needed to process the event**:

```python
# Bad: Insufficient data
OrderPlaced(orderId="123")

# Good: Complete context
OrderPlaced(
    orderId="123",
    customerId="456",
    items=[
        {"productId": "789", "quantity": 2, "price": 19.99},
        {"productId": "012", "quantity": 1, "price": 29.99}
    ],
    totalAmount=69.97,
    currency="USD",
    shippingAddress={...},
    placedAt="2025-10-27T10:30:00Z"
)
```

**Balance**:
- Include data needed by projections
- Avoid including derived data (can be recomputed)
- Don't include mutable references (e.g., current product name)
- Include immutable snapshots (e.g., price at order time)

### Idempotency

**Every event must be idempotent**: Applying the same event twice should have the same result as applying it once.

```python
# Bad: Non-idempotent
def handle_user_registered(event):
    user_count += 1  # Applying twice doubles count!

# Good: Idempotent
def handle_user_registered(event):
    if event.user_id not in users:
        users[event.user_id] = User(event)
        user_count = len(users)
```

**Techniques**:
- Use event IDs to track processed events
- Design handlers to be idempotent by nature
- Use version numbers to detect duplicates

### Event Enrichment

**When to enrich events**:

```python
# Option 1: Minimal event (better for versioning)
UserRegistered(userId="123", email="alice@example.com")

# Option 2: Enriched event (better for consumers)
UserRegistered(
    userId="123",
    email="alice@example.com",
    registeredFrom="mobile-app",
    ipAddress="192.168.1.1",
    referralSource="google-ads",
    timestamp="2025-10-27T10:30:00Z"
)
```

**Guideline**: Enrich if:
- Data is immutable
- Multiple projections need it
- Recomputation is expensive
- Context is valuable for analytics

**Don't enrich if**:
- Data is mutable
- Only one projection needs it
- Increases coupling unnecessarily

---

## Aggregate Design

### What is an Aggregate?

**Aggregate**: A cluster of domain objects treated as a single unit for data changes.

**Key properties**:
- Has a unique identity (aggregate ID)
- Enforces invariants and business rules
- Produces events
- Rebuilt from event stream
- Consistency boundary

### Aggregate Lifecycle

```python
class BankAccount:
    """
    Aggregate: Bank Account

    Invariants:
    - Balance cannot go negative
    - Account must be active to withdraw
    """

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.balance = 0
        self.status = "pending"
        self.version = 0
        self._uncommitted_events = []

    @classmethod
    def create(cls, account_id: str, owner: str, initial_deposit: float):
        """Create new account (command handler)"""
        account = cls(account_id)
        event = AccountOpened(
            account_id=account_id,
            owner=owner,
            initial_deposit=initial_deposit
        )
        account._apply_event(event)
        account._uncommitted_events.append(event)
        return account

    def deposit(self, amount: float):
        """Deposit money (command handler)"""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        event = MoneyDeposited(
            account_id=self.account_id,
            amount=amount,
            balance=self.balance + amount
        )
        self._apply_event(event)
        self._uncommitted_events.append(event)

    def withdraw(self, amount: float):
        """Withdraw money (command handler)"""
        if self.status != "active":
            raise ValueError("Account is not active")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if self.balance < amount:
            raise ValueError("Insufficient funds")

        event = MoneyWithdrawn(
            account_id=self.account_id,
            amount=amount,
            balance=self.balance - amount
        )
        self._apply_event(event)
        self._uncommitted_events.append(event)

    def _apply_event(self, event):
        """Apply event to update state (event handler)"""
        if isinstance(event, AccountOpened):
            self.balance = event.initial_deposit
            self.status = "active"
            self.owner = event.owner
        elif isinstance(event, MoneyDeposited):
            self.balance = event.balance
        elif isinstance(event, MoneyWithdrawn):
            self.balance = event.balance
        elif isinstance(event, AccountClosed):
            self.status = "closed"

        self.version += 1

    def get_uncommitted_events(self):
        """Get events to be persisted"""
        return self._uncommitted_events

    def mark_events_committed(self):
        """Clear uncommitted events after persistence"""
        self._uncommitted_events = []
```

### Rebuilding Aggregate from Events

```python
def load_aggregate(account_id: str, event_store) -> BankAccount:
    """Rebuild aggregate from event stream"""
    events = event_store.get_events(account_id)

    if not events:
        raise ValueError(f"Account {account_id} not found")

    account = BankAccount(account_id)
    for event in events:
        account._apply_event(event)

    return account
```

### Aggregate Command Flow

```
┌─────────────┐
│   Command   │  deposit(100)
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│    Aggregate    │
│  (Load from     │  1. Load events
│   Event Store)  │  2. Rebuild state
└──────┬──────────┘  3. Validate invariants
       │             4. Create event
       │             5. Apply event
       ▼             6. Return event
┌─────────────────┐
│  Uncommitted    │  MoneyDeposited(...)
│     Events      │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Event Store    │  Persist events
│   (Append)      │
└─────────────────┘
```

### Aggregate Boundaries

**Good aggregate**: Small, focused, enforces clear invariants

```python
# Good: Order is single aggregate
class Order:
    """Order aggregate"""
    def __init__(self, order_id):
        self.order_id = order_id
        self.items = []
        self.status = "pending"

    def add_item(self, product_id, quantity, price):
        """Add item to order"""
        if self.status != "pending":
            raise ValueError("Cannot modify submitted order")
        # Invariant: Order can only be modified while pending
```

**Bad aggregate**: Too large, weak boundaries

```python
# Bad: Customer contains orders (too large)
class Customer:
    """Customer aggregate (too large!)"""
    def __init__(self, customer_id):
        self.customer_id = customer_id
        self.orders = []  # Bad: Orders should be separate aggregates
        self.payments = []  # Bad: Separate aggregate
        self.addresses = []  # Maybe OK if tightly coupled
```

**Guidelines**:
- One aggregate per consistency boundary
- Aggregates should be small (< 100 events typical)
- Reference other aggregates by ID only
- Use eventual consistency between aggregates

---

## Event Store Architecture

### Event Store Responsibilities

An **Event Store** is a specialized database for storing and retrieving events.

**Core operations**:
- **Append events**: Write events to a stream
- **Read stream**: Get all events for an aggregate
- **Read from position**: Get events after a checkpoint
- **Subscribe to events**: Get notified of new events
- **Optimistic concurrency**: Detect conflicts

### Event Store Schema

**Simple PostgreSQL event store**:

```sql
-- Events table: Core event storage
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(255) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    version INTEGER NOT NULL,
    data JSONB NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (aggregate_id, version)
);

-- Indexes for common queries
CREATE INDEX idx_events_aggregate ON events(aggregate_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_id_version ON events(id, version);

-- Streams table: Track aggregate metadata
CREATE TABLE streams (
    aggregate_id VARCHAR(255) PRIMARY KEY,
    aggregate_type VARCHAR(100) NOT NULL,
    current_version INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Snapshots table: Optimize aggregate loading
CREATE TABLE snapshots (
    aggregate_id VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL,
    data JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (aggregate_id, version)
);

-- Projections checkpoint table
CREATE TABLE projection_checkpoints (
    projection_name VARCHAR(255) PRIMARY KEY,
    last_event_id BIGINT NOT NULL,
    last_processed_at TIMESTAMPTZ NOT NULL
);
```

### Append Events (Optimistic Concurrency)

```python
import psycopg2
from typing import List

class PostgresEventStore:
    """PostgreSQL-based event store"""

    def __init__(self, connection_string: str):
        self.conn = psycopg2.connect(connection_string)

    def append_events(
        self,
        aggregate_id: str,
        expected_version: int,
        events: List[Event]
    ):
        """
        Append events to stream with optimistic concurrency control.

        Raises:
            ConcurrencyException: If expected_version doesn't match
        """
        cursor = self.conn.cursor()

        try:
            # Check current version
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
                    f"Expected version {expected_version}, "
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
                        event.event_id,
                        event.event_type,
                        aggregate_id,
                        event.aggregate_type,
                        version,
                        json.dumps(event.data),
                        json.dumps(event.metadata),
                        event.timestamp
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
                    (aggregate_id, events[0].aggregate_type, new_version)
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

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            raise
        finally:
            cursor.close()
```

### Read Events

```python
def get_events(self, aggregate_id: str, from_version: int = 1) -> List[Event]:
    """Get all events for an aggregate"""
    cursor = self.conn.cursor()

    cursor.execute(
        """
        SELECT event_id, event_type, aggregate_id, aggregate_type,
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
            event_id=row[0],
            event_type=row[1],
            aggregate_id=row[2],
            aggregate_type=row[3],
            version=row[4],
            data=json.loads(row[5]),
            metadata=json.loads(row[6]) if row[6] else {},
            timestamp=row[7]
        ))

    cursor.close()
    return events
```

### Event Streams

```python
def stream_events(self, from_position: int = 0) -> Iterator[Event]:
    """Stream all events from a position (for projections)"""
    cursor = self.conn.cursor('event_stream_cursor')

    cursor.execute(
        """
        SELECT id, event_id, event_type, aggregate_id, aggregate_type,
               version, data, metadata, timestamp
        FROM events
        WHERE id > %s
        ORDER BY id ASC
        """,
        (from_position,)
    )

    for row in cursor:
        yield Event(
            position=row[0],
            event_id=row[1],
            event_type=row[2],
            aggregate_id=row[3],
            aggregate_type=row[4],
            version=row[5],
            data=json.loads(row[6]),
            metadata=json.loads(row[7]) if row[7] else {},
            timestamp=row[8]
        )

    cursor.close()
```

---

## Projections and Read Models

### What are Projections?

**Projection**: A read model built by processing events.

```
Event Stream → Projection Handler → Read Model
```

**Example**:

```
Events:
  UserRegistered(userId="123", email="alice@example.com")
  UserEmailChanged(userId="123", email="alice@newdomain.com")
  UserActivated(userId="123")

Projection (User View):
  {
    userId: "123",
    email: "alice@newdomain.com",
    status: "active",
    registeredAt: "2025-01-15",
    lastUpdated: "2025-10-27"
  }
```

### Projection Handler

```python
class UserProjection:
    """Build user read model from events"""

    def __init__(self, database):
        self.db = database

    def handle(self, event):
        """Handle event and update projection"""
        if event.event_type == "UserRegistered":
            self._handle_user_registered(event)
        elif event.event_type == "UserEmailChanged":
            self._handle_user_email_changed(event)
        elif event.event_type == "UserActivated":
            self._handle_user_activated(event)

    def _handle_user_registered(self, event):
        """Create user in read model"""
        self.db.execute(
            """
            INSERT INTO user_view (user_id, email, status, registered_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (
                event.data['userId'],
                event.data['email'],
                'pending',
                event.timestamp
            )
        )

    def _handle_user_email_changed(self, event):
        """Update user email"""
        self.db.execute(
            """
            UPDATE user_view
            SET email = %s, last_updated = %s
            WHERE user_id = %s
            """,
            (event.data['email'], event.timestamp, event.data['userId'])
        )

    def _handle_user_activated(self, event):
        """Activate user"""
        self.db.execute(
            """
            UPDATE user_view
            SET status = 'active', last_updated = %s
            WHERE user_id = %s
            """,
            (event.timestamp, event.data['userId'])
        )
```

### Projection Runner

```python
class ProjectionRunner:
    """Run projections continuously"""

    def __init__(self, event_store, projections: List[Projection]):
        self.event_store = event_store
        self.projections = projections

    def run(self):
        """Process events and update projections"""
        for projection in self.projections:
            # Get last checkpoint
            checkpoint = self._get_checkpoint(projection.name)

            # Stream events from checkpoint
            for event in self.event_store.stream_events(checkpoint):
                try:
                    # Handle event
                    projection.handle(event)

                    # Update checkpoint
                    self._update_checkpoint(projection.name, event.position)

                except Exception as e:
                    logger.error(f"Error processing event {event.event_id}: {e}")
                    # Implement retry logic or dead letter queue

    def _get_checkpoint(self, projection_name: str) -> int:
        """Get last processed position for projection"""
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT last_event_id FROM projection_checkpoints WHERE projection_name = %s",
            (projection_name,)
        )
        result = cursor.fetchone()
        return result[0] if result else 0

    def _update_checkpoint(self, projection_name: str, position: int):
        """Update checkpoint"""
        self.db.execute(
            """
            INSERT INTO projection_checkpoints (projection_name, last_event_id, last_processed_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (projection_name)
            DO UPDATE SET last_event_id = %s, last_processed_at = NOW()
            """,
            (projection_name, position, position)
        )
        self.db.commit()
```

### Multiple Projections from Same Events

```python
# Projection 1: User view (for queries)
class UserViewProjection:
    def handle(self, event):
        # Build normalized user view
        pass

# Projection 2: Analytics (for reporting)
class UserAnalyticsProjection:
    def handle(self, event):
        if event.event_type == "UserRegistered":
            # Track registration metrics
            pass

# Projection 3: Search index (for full-text search)
class UserSearchProjection:
    def handle(self, event):
        # Update Elasticsearch index
        pass

# All projections process same events
projections = [
    UserViewProjection(postgres_db),
    UserAnalyticsProjection(analytics_db),
    UserSearchProjection(elasticsearch)
]

runner = ProjectionRunner(event_store, projections)
runner.run()
```

### Projection Rebuild

```python
def rebuild_projection(projection: Projection, event_store):
    """Rebuild projection from scratch"""

    # 1. Clear existing projection data
    projection.clear()

    # 2. Reset checkpoint
    projection.reset_checkpoint()

    # 3. Replay all events
    for event in event_store.stream_events(from_position=0):
        projection.handle(event)

    print(f"Projection {projection.name} rebuilt successfully")
```

**When to rebuild**:
- Projection logic changed
- Projection data corrupted
- New projection added
- Testing projection behavior

---

## Snapshot Strategies

### Why Snapshots?

**Problem**: Loading aggregates with many events is slow.

```python
# Without snapshots: Load 10,000 events
account = load_aggregate("account-123")  # Slow!
```

**Solution**: Snapshots save aggregate state periodically.

```python
# With snapshots: Load snapshot + recent events
snapshot = load_snapshot("account-123", max_version)  # 1 query
recent_events = load_events_after(snapshot.version)    # 100 events
account = apply_events(snapshot.state, recent_events)  # Fast!
```

### Snapshot Storage

```sql
-- Snapshot table
CREATE TABLE snapshots (
    aggregate_id VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL,
    data JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (aggregate_id, version)
);

-- Index for latest snapshot
CREATE INDEX idx_snapshots_aggregate_version
ON snapshots(aggregate_id, version DESC);
```

### Snapshot Creation

```python
def save_snapshot(aggregate, event_store):
    """Save aggregate snapshot"""
    snapshot = Snapshot(
        aggregate_id=aggregate.account_id,
        version=aggregate.version,
        data={
            'balance': aggregate.balance,
            'status': aggregate.status,
            'owner': aggregate.owner
        },
        timestamp=datetime.now()
    )

    event_store.save_snapshot(snapshot)
```

### Snapshot Loading

```python
def load_aggregate_with_snapshot(aggregate_id: str, event_store):
    """Load aggregate using snapshot + events"""

    # 1. Try to load latest snapshot
    snapshot = event_store.get_latest_snapshot(aggregate_id)

    if snapshot:
        # Rebuild from snapshot
        account = BankAccount(aggregate_id)
        account.balance = snapshot.data['balance']
        account.status = snapshot.data['status']
        account.owner = snapshot.data['owner']
        account.version = snapshot.version

        # Load events after snapshot
        events = event_store.get_events(aggregate_id, from_version=snapshot.version + 1)
    else:
        # No snapshot, load all events
        account = BankAccount(aggregate_id)
        events = event_store.get_events(aggregate_id)

    # Apply remaining events
    for event in events:
        account._apply_event(event)

    return account
```

### Snapshot Frequency Strategies

**Strategy 1: Every N events**

```python
def append_events_with_snapshot(aggregate, events, event_store):
    """Append events and snapshot if needed"""
    event_store.append_events(aggregate.id, aggregate.version, events)

    # Snapshot every 100 events
    if (aggregate.version + len(events)) % 100 == 0:
        save_snapshot(aggregate, event_store)
```

**Strategy 2: Time-based**

```python
def snapshot_old_aggregates(event_store):
    """Snapshot aggregates not snapshotted recently"""
    aggregates = event_store.get_aggregates_without_recent_snapshot(days=7)

    for aggregate_id in aggregates:
        aggregate = load_aggregate(aggregate_id, event_store)
        save_snapshot(aggregate, event_store)
```

**Strategy 3: On-demand**

```python
def load_with_lazy_snapshot(aggregate_id: str, event_store):
    """Load aggregate and create snapshot if loading was slow"""
    start = time.time()

    aggregate = load_aggregate_with_snapshot(aggregate_id, event_store)

    duration = time.time() - start

    # If loading took > 100ms, create snapshot
    if duration > 0.1:
        save_snapshot(aggregate, event_store)

    return aggregate
```

### Snapshot Retention

```sql
-- Keep only last 3 snapshots per aggregate
WITH ranked_snapshots AS (
    SELECT aggregate_id, version,
           ROW_NUMBER() OVER (PARTITION BY aggregate_id ORDER BY version DESC) as rn
    FROM snapshots
)
DELETE FROM snapshots
WHERE (aggregate_id, version) IN (
    SELECT aggregate_id, version
    FROM ranked_snapshots
    WHERE rn > 3
);
```

---

## CQRS Integration

### What is CQRS?

**CQRS** (Command Query Responsibility Segregation): Separate models for writes (commands) and reads (queries).

```
Commands → Write Model → Events → Read Model → Queries
```

**Why combine with Event Sourcing?**
- Event Sourcing naturally produces events for read models
- CQRS allows multiple read models from same events
- Optimization: Write model in event store, read models in any database

### CQRS Architecture

```
┌──────────────┐
│   Command    │  CreateOrder, AddItem, SubmitOrder
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  Command Handler │  Validate, load aggregate, execute
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│   Aggregate      │  Order (event-sourced)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Event Store     │  OrderCreated, ItemAdded, OrderSubmitted
└──────┬───────────┘
       │
       │ Events
       ▼
┌──────────────────────────────────┐
│        Event Bus                 │
└──────┬───────────────────────────┘
       │
       ├──────────────┬──────────────┬──────────────┐
       ▼              ▼              ▼              ▼
   ┌────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐
   │ Order  │   │ Product │   │Analytics │   │ Search  │
   │  View  │   │ Inventory│   │  DB     │   │ Index   │
   └────┬───┘   └────┬────┘   └────┬─────┘   └────┬────┘
        │            │              │              │
        ▼            ▼              ▼              ▼
   ┌──────────────────────────────────────────────────┐
   │                Query Models                      │
   └──────────────────────────────────────────────────┘
        ▲
        │ Queries
   ┌────────┐
   │ Query  │  GetOrder, SearchProducts, GetAnalytics
   │Handler │
   └────────┘
```

### Command Handler

```python
class CreateOrderHandler:
    """Handle CreateOrder command"""

    def __init__(self, event_store):
        self.event_store = event_store

    def handle(self, command: CreateOrder):
        """Execute command"""

        # 1. Validate command
        self._validate(command)

        # 2. Create aggregate
        order = Order.create(
            order_id=command.order_id,
            customer_id=command.customer_id
        )

        # 3. Get uncommitted events
        events = order.get_uncommitted_events()

        # 4. Persist events
        self.event_store.append_events(
            order.order_id,
            expected_version=0,
            events=events
        )

        # 5. Publish events to event bus
        for event in events:
            event_bus.publish(event)

        return order.order_id

    def _validate(self, command):
        """Validate command"""
        if not command.customer_id:
            raise ValueError("Customer ID required")
```

### Query Handler

```python
class GetOrderHandler:
    """Handle GetOrder query"""

    def __init__(self, database):
        self.db = database

    def handle(self, query: GetOrder):
        """Execute query against read model"""

        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT order_id, customer_id, items, total, status, created_at
            FROM order_view
            WHERE order_id = %s
            """,
            (query.order_id,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'orderId': row[0],
            'customerId': row[1],
            'items': json.loads(row[2]),
            'total': row[3],
            'status': row[4],
            'createdAt': row[5]
        }
```

### CQRS Benefits

**Scalability**:
- Scale reads and writes independently
- Read replicas for read-heavy workloads
- Event store optimized for writes

**Flexibility**:
- Multiple read models for different use cases
- Optimize each read model for its queries
- Add new read models without changing write side

**Simplicity**:
- Write model focuses on business logic
- Read models optimized for queries
- No ORM impedance mismatch

---

## Saga Patterns

### What is a Saga?

**Saga**: A long-running process that coordinates multiple aggregates or services.

**Example**: Order fulfillment saga

```
1. Order created
2. Reserve inventory
3. Process payment
4. Ship order
5. Complete order

If any step fails, compensate previous steps.
```

### Saga Implementation

```python
class OrderFulfillmentSaga:
    """Coordinate order fulfillment across services"""

    def __init__(self, event_store, command_bus):
        self.event_store = event_store
        self.command_bus = command_bus
        self.state = {}

    def handle(self, event):
        """Handle events and advance saga"""

        if event.event_type == "OrderSubmitted":
            self._handle_order_submitted(event)

        elif event.event_type == "InventoryReserved":
            self._handle_inventory_reserved(event)

        elif event.event_type == "InventoryReservationFailed":
            self._handle_inventory_reservation_failed(event)

        elif event.event_type == "PaymentProcessed":
            self._handle_payment_processed(event)

        elif event.event_type == "PaymentFailed":
            self._handle_payment_failed(event)

    def _handle_order_submitted(self, event):
        """Step 1: Reserve inventory"""
        order_id = event.data['orderId']
        items = event.data['items']

        # Send command to inventory service
        self.command_bus.send(
            ReserveInventory(order_id=order_id, items=items)
        )

        # Track saga state
        self.state[order_id] = {
            'step': 'inventory_reservation',
            'order_id': order_id,
            'items': items
        }

    def _handle_inventory_reserved(self, event):
        """Step 2: Process payment"""
        order_id = event.data['orderId']
        amount = self.state[order_id]['amount']

        self.command_bus.send(
            ProcessPayment(order_id=order_id, amount=amount)
        )

        self.state[order_id]['step'] = 'payment_processing'

    def _handle_payment_processed(self, event):
        """Step 3: Ship order"""
        order_id = event.data['orderId']

        self.command_bus.send(
            ShipOrder(order_id=order_id)
        )

        self.state[order_id]['step'] = 'shipping'

    def _handle_inventory_reservation_failed(self, event):
        """Compensate: Cancel order"""
        order_id = event.data['orderId']

        self.command_bus.send(
            CancelOrder(order_id=order_id, reason="Insufficient inventory")
        )

        del self.state[order_id]

    def _handle_payment_failed(self, event):
        """Compensate: Release inventory and cancel order"""
        order_id = event.data['orderId']
        items = self.state[order_id]['items']

        # Release reserved inventory
        self.command_bus.send(
            ReleaseInventory(order_id=order_id, items=items)
        )

        # Cancel order
        self.command_bus.send(
            CancelOrder(order_id=order_id, reason="Payment failed")
        )

        del self.state[order_id]
```

### Saga State Persistence

```python
class PersistentSaga:
    """Saga with persistent state"""

    def __init__(self, saga_id, event_store):
        self.saga_id = saga_id
        self.event_store = event_store
        self.state = self._load_state()

    def _load_state(self):
        """Load saga state from database"""
        cursor = db.cursor()
        cursor.execute(
            "SELECT state FROM saga_state WHERE saga_id = %s",
            (self.saga_id,)
        )
        result = cursor.fetchone()
        return json.loads(result[0]) if result else {}

    def _save_state(self):
        """Persist saga state"""
        db.execute(
            """
            INSERT INTO saga_state (saga_id, state, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (saga_id)
            DO UPDATE SET state = %s, updated_at = NOW()
            """,
            (self.saga_id, json.dumps(self.state), json.dumps(self.state))
        )
        db.commit()

    def handle(self, event):
        """Handle event and save state"""
        # Process event
        self._process_event(event)

        # Save state
        self._save_state()
```

---

## Event Versioning and Schema Evolution

### The Versioning Challenge

Events are **immutable**, but requirements change over time.

```python
# V1: Simple user registered event
UserRegistered(userId="123", email="alice@example.com")

# Later: Need to track registration source
# But old events don't have this field!
```

### Strategy 1: Weak Schema (Additive Changes Only)

**Principle**: Only add optional fields, never remove or change existing fields.

```python
# V1
{
    "eventType": "UserRegistered",
    "userId": "123",
    "email": "alice@example.com"
}

# V2: Add optional field
{
    "eventType": "UserRegistered",
    "userId": "123",
    "email": "alice@example.com",
    "source": "mobile-app"  # New optional field
}

# Projection handles both versions
def handle_user_registered(event):
    user_id = event['userId']
    email = event['email']
    source = event.get('source', 'unknown')  # Default for old events
```

**Pros**:
- Simple
- Old events still valid
- No migration needed

**Cons**:
- Can't change existing fields
- Technical debt accumulates
- Handlers must handle all versions

### Strategy 2: Explicit Versioning

**Principle**: Version events explicitly and handle each version.

```python
# Events
{
    "eventType": "UserRegistered",
    "version": 1,
    "data": {"userId": "123", "email": "alice@example.com"}
}

{
    "eventType": "UserRegistered",
    "version": 2,
    "data": {"userId": "123", "email": "alice@example.com", "source": "mobile-app"}
}

# Handler
def handle_user_registered(event):
    if event['version'] == 1:
        return self._handle_v1(event)
    elif event['version'] == 2:
        return self._handle_v2(event)
    else:
        raise ValueError(f"Unknown version {event['version']}")
```

**Pros**:
- Clear version boundaries
- Explicit handling per version
- Can change fields in new versions

**Cons**:
- Handler complexity grows
- Must maintain all version handlers

### Strategy 3: Upcasting

**Principle**: Convert old events to new schema when reading.

```python
class EventUpcaster:
    """Upcast old events to latest schema"""

    def upcast(self, event):
        """Convert event to latest version"""

        if event['eventType'] == 'UserRegistered':
            return self._upcast_user_registered(event)

        return event

    def _upcast_user_registered(self, event):
        """Upcast UserRegistered to latest version"""

        # V1 → V2: Add source field
        if event.get('version', 1) == 1:
            event['data']['source'] = 'unknown'
            event['version'] = 2

        # Future: V2 → V3
        # if event['version'] == 2:
        #     event = self._v2_to_v3(event)

        return event

# Usage
upcaster = EventUpcaster()
events = event_store.get_events(aggregate_id)
upcasted_events = [upcaster.upcast(e) for e in events]
```

**Pros**:
- Single version in application code
- Old events automatically converted
- Can change fields

**Cons**:
- Upcasting logic must be maintained
- Performance overhead (mitigated by caching)

### Strategy 4: Event Replacement

**Principle**: Replace old events with new events (for critical changes).

```python
def replace_events(aggregate_id, event_store):
    """
    Replace old events with new schema.
    WARNING: Dangerous operation!
    """

    # 1. Load old events
    old_events = event_store.get_events(aggregate_id)

    # 2. Convert to new schema
    new_events = []
    for event in old_events:
        if event.event_type == 'UserRegistered' and event.version == 1:
            # Create V2 event
            new_event = Event(
                event_id=event.event_id,  # Keep same ID!
                event_type='UserRegistered',
                version=2,
                data={
                    'userId': event.data['userId'],
                    'email': event.data['email'],
                    'source': 'legacy-migration'
                }
            )
            new_events.append(new_event)
        else:
            new_events.append(event)

    # 3. Replace events (DANGER!)
    event_store.replace_events(aggregate_id, new_events)

    # 4. Rebuild projections
    rebuild_all_projections()
```

**Warning**: Use only when absolutely necessary. Violates immutability.

### Best Practices

1. **Design events carefully**: Hard to change later
2. **Use weak schema** by default: Additive changes only
3. **Version explicitly** when needed: Clear version handling
4. **Upcast for compatibility**: Convert old events on read
5. **Avoid breaking changes**: Design for evolution
6. **Test with old events**: Ensure backward compatibility

---

## Temporal Queries and Event Replay

### Temporal Queries

**Temporal Query**: Query state at a specific point in time.

```python
def get_aggregate_at_time(aggregate_id: str, timestamp: datetime, event_store):
    """Get aggregate state at specific time"""

    # Load events up to timestamp
    events = event_store.get_events_until(aggregate_id, timestamp)

    # Rebuild aggregate from events
    aggregate = BankAccount(aggregate_id)
    for event in events:
        aggregate._apply_event(event)

    return aggregate

# Usage
account_yesterday = get_aggregate_at_time("account-123", yesterday, event_store)
print(f"Balance yesterday: {account_yesterday.balance}")

account_now = load_aggregate("account-123", event_store)
print(f"Balance now: {account_now.balance}")
```

### Temporal Projection

```python
def rebuild_projection_at_time(projection: Projection, timestamp: datetime, event_store):
    """Rebuild projection as it was at a specific time"""

    # Clear projection
    projection.clear()

    # Replay events up to timestamp
    for event in event_store.stream_events_until(timestamp):
        projection.handle(event)

    return projection

# Usage: "What did our analytics look like last month?"
analytics = rebuild_projection_at_time(
    AnalyticsProjection(),
    datetime(2025, 9, 1),
    event_store
)
```

### Event Replay for Testing

```python
def replay_production_events_for_testing():
    """
    Replay production events to test new projection logic
    """

    # 1. Load production events
    prod_events = production_event_store.stream_events()

    # 2. Replay in test environment
    test_projection = NewFeatureProjection(test_db)

    for event in prod_events:
        test_projection.handle(event)

    # 3. Verify projection correctness
    assert test_projection.is_valid()
```

### Event Replay for Debugging

```python
def debug_aggregate(aggregate_id: str, event_store):
    """
    Debug aggregate by replaying events step by step
    """
    events = event_store.get_events(aggregate_id)

    aggregate = BankAccount(aggregate_id)

    print(f"Replaying {len(events)} events for {aggregate_id}\n")

    for i, event in enumerate(events, 1):
        print(f"Event {i}: {event.event_type}")
        print(f"  Data: {event.data}")

        aggregate._apply_event(event)

        print(f"  State after: balance={aggregate.balance}, status={aggregate.status}")
        print()
```

---

## Production Implementations

### EventStoreDB

**EventStoreDB**: Purpose-built database for event sourcing.

**Features**:
- Optimistic concurrency
- Event subscriptions
- Projections
- Clustering
- HTTP and gRPC APIs

**Installation**:

```bash
# Docker
docker run -d -p 2113:2113 -p 1113:1113 \
  -e EVENTSTORE_INSECURE=true \
  eventstore/eventstore:latest

# Access UI: http://localhost:2113
```

**Python client**:

```python
from esdbclient import EventStoreDBClient

# Connect
client = EventStoreDBClient(uri="esdb://localhost:2113?tls=false")

# Append events
client.append_to_stream(
    stream_name="account-123",
    events=[
        NewEvent(
            type="MoneyDeposited",
            data={"amount": 100, "balance": 100}
        )
    ],
    expected_position=None  # Create stream
)

# Read events
events = client.get_stream("account-123")
for event in events:
    print(f"{event.type}: {event.data}")

# Subscribe to events
subscription = client.subscribe_to_all()
for event in subscription:
    print(f"New event: {event.type}")
```

### PostgreSQL Event Store

**Advantages**:
- No new infrastructure
- Familiar tooling
- ACID transactions
- Good performance with proper indexing

**Schema** (shown earlier in Event Store Architecture section)

**Implementation**:

```python
class PostgresEventStore:
    """Full implementation shown earlier"""

    def __init__(self, connection_string):
        self.conn = psycopg2.connect(connection_string)

    def append_events(self, aggregate_id, expected_version, events):
        """Append with optimistic concurrency"""
        # Implementation shown earlier

    def get_events(self, aggregate_id, from_version=1):
        """Get events for aggregate"""
        # Implementation shown earlier

    def stream_events(self, from_position=0):
        """Stream all events"""
        # Implementation shown earlier
```

### Kafka as Event Store

**Use Kafka** for event sourcing in distributed systems.

**Advantages**:
- High throughput
- Distributed by nature
- Long retention
- Multiple consumers

**Topic design**:

```
# One topic per aggregate type
user-events
order-events
payment-events

# Partition by aggregate ID
key = aggregate_id
value = event
```

**Producer**:

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def append_events(aggregate_id, events):
    """Append events to Kafka"""
    for event in events:
        producer.send(
            'user-events',
            key=aggregate_id.encode('utf-8'),
            value={
                'eventId': event.event_id,
                'eventType': event.event_type,
                'aggregateId': aggregate_id,
                'version': event.version,
                'data': event.data,
                'timestamp': event.timestamp.isoformat()
            }
        )
    producer.flush()
```

**Consumer**:

```python
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'user-events',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='earliest',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

# Process events
for message in consumer:
    event = message.value
    projection.handle(event)
```

### Axon Framework (Java)

**Axon**: Event sourcing framework for Java/Spring.

```java
// Aggregate
@Aggregate
public class BankAccount {
    @AggregateIdentifier
    private String accountId;
    private BigDecimal balance;

    @CommandHandler
    public BankAccount(OpenAccountCommand command) {
        // Validate
        AggregateLifecycle.apply(new AccountOpenedEvent(
            command.getAccountId(),
            command.getInitialDeposit()
        ));
    }

    @CommandHandler
    public void handle(DepositMoneyCommand command) {
        // Validate
        AggregateLifecycle.apply(new MoneyDepositedEvent(
            accountId,
            command.getAmount()
        ));
    }

    @EventSourcingHandler
    public void on(AccountOpenedEvent event) {
        this.accountId = event.getAccountId();
        this.balance = event.getInitialDeposit();
    }

    @EventSourcingHandler
    public void on(MoneyDepositedEvent event) {
        this.balance = this.balance.add(event.getAmount());
    }
}

// Projection
@Component
public class AccountViewProjection {
    @EventHandler
    public void on(AccountOpenedEvent event) {
        // Update read model
    }
}
```

### Marten (C#/.NET)

**Marten**: Event store using PostgreSQL.

```csharp
// Configure
var store = DocumentStore.For(options =>
{
    options.Connection("connection_string");
    options.Events.DatabaseSchemaName = "events";
});

// Append events
using var session = store.OpenSession();
var accountId = Guid.NewGuid();
session.Events.StartStream<BankAccount>(
    accountId,
    new AccountOpened(accountId, 1000),
    new MoneyDeposited(accountId, 500)
);
session.SaveChanges();

// Load aggregate
var events = session.Events.FetchStream(accountId);
var account = events.Aggregate<BankAccount>();
```

---

## Common Anti-Patterns

### Anti-Pattern 1: Large Events

**Problem**: Events with too much data.

```python
# Bad: Kitchen sink event
OrderPlaced(
    orderId="123",
    customer={"id": "456", "name": "...", "address": {...}, "orders": [...]},
    products=[...100 products with all details...],
    warehouse={"id": "789", "inventory": {...}},
    pricing={"rules": [...], "discounts": [...]},
    ...  # 50KB of data
)
```

**Solution**: Minimal, focused events.

```python
# Good: Minimal event
OrderPlaced(
    orderId="123",
    customerId="456",
    items=[
        {"productId": "789", "quantity": 2, "price": 19.99}
    ],
    totalAmount=39.98,
    placedAt="2025-10-27T10:30:00Z"
)
```

### Anti-Pattern 2: Missing Idempotency

**Problem**: Processing same event twice causes issues.

```python
# Bad: Non-idempotent handler
def handle_money_deposited(event):
    balance += event.amount  # Applying twice doubles deposit!
```

**Solution**: Idempotent handlers.

```python
# Good: Idempotent handler
def handle_money_deposited(event):
    if event.event_id not in processed_events:
        balance += event.amount
        processed_events.add(event.event_id)
```

### Anti-Pattern 3: No Versioning Strategy

**Problem**: Breaking changes break projections.

```python
# V1
{"eventType": "UserRegistered", "username": "alice"}

# V2: Changed field name!
{"eventType": "UserRegistered", "email": "alice@example.com"}  # Broke everything!
```

**Solution**: Plan for versioning.

```python
# V1
{"eventType": "UserRegistered", "version": 1, "username": "alice"}

# V2: Additive change
{"eventType": "UserRegistered", "version": 2, "username": "alice", "email": "alice@example.com"}
```

### Anti-Pattern 4: Business Logic in Projections

**Problem**: Duplicate business logic.

```python
# Bad: Business logic in projection
def handle_order_placed(event):
    if event.total > 1000:
        # Business rule: Large orders get discount
        discount = event.total * 0.1
    else:
        discount = 0
```

**Solution**: Business logic only in aggregates.

```python
# Good: Business logic in aggregate
class Order:
    def place_order(self):
        total = self.calculate_total()
        discount = self._calculate_discount(total)  # Business logic here

        event = OrderPlaced(
            orderId=self.order_id,
            total=total,
            discount=discount  # Event contains result
        )

# Projection just stores data
def handle_order_placed(event):
    db.insert(order_id=event.orderId, total=event.total, discount=event.discount)
```

### Anti-Pattern 5: Synchronous Projections

**Problem**: Slow projections block writes.

```python
# Bad: Wait for projection
def place_order(order):
    events = order.get_events()
    event_store.append_events(order.id, events)

    # BAD: Block until projection updates
    wait_for_projection_update()  # Slow!

    return {"success": True}
```

**Solution**: Asynchronous projections.

```python
# Good: Don't wait for projections
def place_order(order):
    events = order.get_events()
    event_store.append_events(order.id, events)

    # Return immediately
    return {"success": True}

# Projections update asynchronously
projection_runner.run_async()
```

---

## Performance Optimization

### 1. Snapshots

**Impact**: Massive speedup for aggregates with many events.

```python
# Without snapshot: 10,000 events
aggregate = load_aggregate(aggregate_id)  # 5 seconds

# With snapshot: 1 snapshot + 100 events
aggregate = load_with_snapshot(aggregate_id)  # 50ms
```

### 2. Event Store Indexing

**Critical indexes**:

```sql
-- Aggregate stream lookup (most common query)
CREATE INDEX idx_events_aggregate ON events(aggregate_id, version);

-- Event streaming for projections
CREATE INDEX idx_events_id ON events(id);

-- Event type filtering
CREATE INDEX idx_events_type ON events(event_type);

-- Time-based queries
CREATE INDEX idx_events_timestamp ON events(timestamp);
```

### 3. Projection Batching

**Batch events** for better throughput.

```python
# Bad: Process one at a time
for event in events:
    projection.handle(event)
    db.commit()  # Commit per event!

# Good: Batch commits
batch = []
for event in events:
    projection.handle(event)
    batch.append(event)

    if len(batch) >= 100:
        db.commit()  # Commit batch
        batch = []

if batch:
    db.commit()  # Commit remaining
```

### 4. Read Model Optimization

**Optimize read models** for queries.

```sql
-- Denormalize for fast queries
CREATE TABLE order_view (
    order_id VARCHAR(255) PRIMARY KEY,
    customer_id VARCHAR(255),
    customer_name VARCHAR(255),  -- Denormalized
    total_amount DECIMAL(10,2),
    items JSONB,
    status VARCHAR(50),
    created_at TIMESTAMPTZ
);

-- Index for common queries
CREATE INDEX idx_order_view_customer ON order_view(customer_id);
CREATE INDEX idx_order_view_status ON order_view(status);
CREATE INDEX idx_order_view_created ON order_view(created_at DESC);
```

### 5. Event Store Partitioning

**Partition** event store for scale.

```sql
-- Partition by aggregate type
CREATE TABLE events (
    ...
) PARTITION BY LIST (aggregate_type);

CREATE TABLE events_user PARTITION OF events FOR VALUES IN ('User');
CREATE TABLE events_order PARTITION OF events FOR VALUES IN ('Order');
CREATE TABLE events_payment PARTITION OF events FOR VALUES IN ('Payment');

-- Or partition by time
CREATE TABLE events (
    ...
) PARTITION BY RANGE (timestamp);

CREATE TABLE events_2025_10 PARTITION OF events
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

### 6. Caching

**Cache aggregates** to avoid repeated loading.

```python
class CachedEventStore:
    """Event store with aggregate caching"""

    def __init__(self, event_store, cache):
        self.event_store = event_store
        self.cache = cache  # Redis, Memcached, etc.

    def load_aggregate(self, aggregate_id):
        """Load aggregate with caching"""

        # Try cache
        cached = self.cache.get(f"aggregate:{aggregate_id}")
        if cached:
            return pickle.loads(cached)

        # Load from event store
        aggregate = self.event_store.load_aggregate(aggregate_id)

        # Cache with TTL
        self.cache.setex(
            f"aggregate:{aggregate_id}",
            300,  # 5 minutes
            pickle.dumps(aggregate)
        )

        return aggregate
```

---

## Testing Event-Sourced Systems

### Test Aggregate Behavior

```python
import pytest

def test_deposit_increases_balance():
    """Test depositing money increases balance"""
    # Given: Account with initial balance
    account = BankAccount.create("account-123", "Alice", initial_deposit=100)
    assert account.balance == 100

    # When: Deposit money
    account.deposit(50)

    # Then: Balance increased
    assert account.balance == 150

    # And: Event was produced
    events = account.get_uncommitted_events()
    assert len(events) == 2  # AccountOpened, MoneyDeposited
    assert events[1].event_type == "MoneyDeposited"
    assert events[1].data['amount'] == 50

def test_cannot_withdraw_more_than_balance():
    """Test withdrawing more than balance fails"""
    # Given: Account with balance
    account = BankAccount.create("account-123", "Alice", initial_deposit=100)

    # When/Then: Withdraw too much
    with pytest.raises(ValueError, match="Insufficient funds"):
        account.withdraw(200)

    # And: No event produced
    events = account.get_uncommitted_events()
    assert len(events) == 1  # Only AccountOpened
```

### Test Event Handlers

```python
def test_projection_handles_user_registered():
    """Test projection handles UserRegistered event"""
    # Given: Empty projection
    projection = UserProjection(test_db)

    # When: Handle event
    event = Event(
        event_id="event-123",
        event_type="UserRegistered",
        aggregate_id="user-123",
        data={'userId': 'user-123', 'email': 'alice@example.com'}
    )
    projection.handle(event)

    # Then: User created in read model
    user = test_db.query("SELECT * FROM user_view WHERE user_id = 'user-123'")
    assert user['email'] == 'alice@example.com'
    assert user['status'] == 'pending'
```

### Test Event Replay

```python
def test_aggregate_rebuilds_from_events():
    """Test aggregate rebuilds correctly from events"""
    # Given: Sequence of events
    events = [
        Event(event_type="AccountOpened", data={'accountId': '123', 'initialDeposit': 100}),
        Event(event_type="MoneyDeposited", data={'accountId': '123', 'amount': 50}),
        Event(event_type="MoneyWithdrawn", data={'accountId': '123', 'amount': 30}),
    ]

    # When: Rebuild aggregate
    account = BankAccount('123')
    for event in events:
        account._apply_event(event)

    # Then: State is correct
    assert account.balance == 120  # 100 + 50 - 30
    assert account.version == 3
```

### Test Idempotency

```python
def test_projection_is_idempotent():
    """Test applying same event twice has same effect"""
    # Given: Projection and event
    projection = UserProjection(test_db)
    event = Event(
        event_id="event-123",
        event_type="UserRegistered",
        data={'userId': 'user-123', 'email': 'alice@example.com'}
    )

    # When: Apply event twice
    projection.handle(event)
    projection.handle(event)  # Should be idempotent

    # Then: Only one user created
    users = test_db.query("SELECT * FROM user_view WHERE user_id = 'user-123'")
    assert len(users) == 1
```

### Integration Test

```python
def test_full_flow():
    """Integration test: Command → Events → Projection"""
    # Given: Clean system
    event_store = PostgresEventStore(test_db_connection)
    projection = OrderProjection(test_db)

    # When: Execute command
    command = CreateOrder(order_id="order-123", customer_id="customer-456")
    handler = CreateOrderHandler(event_store)
    handler.handle(command)

    # And: Process events
    events = event_store.get_events("order-123")
    for event in events:
        projection.handle(event)

    # Then: Projection updated
    order = test_db.query("SELECT * FROM order_view WHERE order_id = 'order-123'")
    assert order['customer_id'] == 'customer-456'
    assert order['status'] == 'pending'
```

---

## References

### Key Papers and Books

**Books**:
- **"Domain-Driven Design"** by Eric Evans - Original DDD concepts
- **"Implementing Domain-Driven Design"** by Vaughn Vernon - Practical DDD with event sourcing
- **"Versioning in an Event Sourced System"** by Greg Young - Event versioning strategies
- **"Event Sourcing"** by Martin Fowler - Overview and patterns

**Papers**:
- **"Event Sourcing Pattern"** - Microsoft Azure Architecture Center
- **"CQRS Journey"** by Microsoft patterns & practices - Comprehensive guide

**Online Resources**:
- Greg Young's talks on Event Sourcing and CQRS
- Martin Fowler's blog posts on Event Sourcing
- EventStoreDB documentation
- Axon Framework documentation

### Frameworks and Tools

**Event Stores**:
- **EventStoreDB**: https://www.eventstore.com/
- **Marten** (PostgreSQL): https://martendb.io/
- **Kafka**: https://kafka.apache.org/

**Frameworks**:
- **Axon Framework** (Java): https://axoniq.io/
- **Eventide** (Ruby): https://eventide-project.org/
- **EventFlow** (.NET): https://github.com/eventflow/EventFlow

**Languages**:
- Python: eventstore-client, custom implementations
- Java: Axon Framework, Lagom
- C#: Marten, NEventStore, SqlStreamStore
- Node.js: EventStore.js, custom implementations

---

## Conclusion

**Event Sourcing** is a powerful pattern for building systems with:
- Complete audit trails
- Temporal queries
- Flexible read models
- Event-driven architectures

**Key takeaways**:
1. Events are immutable facts about the past
2. Aggregates enforce invariants and produce events
3. Projections build read models from events
4. CQRS separates writes and reads
5. Snapshots optimize aggregate loading
6. Plan for event versioning from the start
7. Test aggregates, handlers, and projections thoroughly

**When to use**:
- Complex domains with rich business logic
- Audit requirements
- Event-driven architectures
- Need for temporal queries
- Multiple read models from same data

**When to avoid**:
- Simple CRUD applications
- Strict consistency requirements
- Team lacks event sourcing experience
- Low tolerance for complexity

Event sourcing is a significant paradigm shift, but the benefits—audit trails, temporal queries, and flexibility—make it invaluable for the right use cases.
