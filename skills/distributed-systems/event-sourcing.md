---
name: distributed-systems-event-sourcing
description: Event sourcing architecture, event design, CQRS, aggregates, projections, snapshots, and production implementations
---

# Event Sourcing

**Scope**: Event sourcing fundamentals, event design, CQRS patterns, aggregates, projections, snapshots, saga patterns, temporal queries
**Lines**: ~450
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building event-driven systems
- Implementing audit trails
- Designing CQRS architectures
- Creating temporal query capabilities
- Working with distributed transactions
- Building saga patterns
- Implementing domain-driven design
- Creating analytics from historical data
- Debugging complex state transitions
- Building collaborative systems

## Core Concepts

### Event Sourcing Overview

**Principle**: Store all changes as immutable events instead of current state

```
Traditional:
  users = {id: 1, name: "Alice", status: "active"}

Event Sourced:
  events = [
    UserCreated(id=1, name="Alice"),
    UserActivated(id=1)
  ]
  Current state = reduce(events, initial_state)
```

**Key benefits**:
- Complete audit trail
- Temporal queries (state at any point in time)
- Event replay for debugging
- Multiple projections from same events
- Natural fit for event-driven architectures

**Trade-offs**:
- Higher complexity
- Storage growth (mitigated by snapshots)
- Eventual consistency
- Learning curve
- Event versioning challenges

### Event Design

**Event naming**: Past tense, specific facts

```python
# Good: Past tense
UserRegistered
OrderPlaced
PaymentProcessed
EmailSent

# Bad: Commands or present tense
RegisterUser  # Command, not event
PlaceOrder    # Command
UpdateUser    # Too vague
```

**Event structure**:

```json
{
  "eventId": "uuid",
  "eventType": "OrderPlaced",
  "aggregateId": "order-123",
  "aggregateType": "Order",
  "version": 1,
  "timestamp": "2025-10-27T10:30:00Z",
  "data": {
    "orderId": "order-123",
    "customerId": "customer-456",
    "items": [...],
    "totalAmount": 99.99
  },
  "metadata": {
    "causationId": "command-789",
    "correlationId": "request-012",
    "userId": "admin-1"
  }
}
```

**Required fields**: eventId, eventType, aggregateId, version, timestamp, data

**Recommended fields**: aggregateType, metadata (causationId, correlationId, userId)

---

## Aggregates

### Aggregate Pattern

**Aggregate**: Consistency boundary that enforces invariants and produces events

```python
class BankAccount:
    """Aggregate enforcing account invariants"""

    def __init__(self, account_id):
        self.account_id = account_id
        self.balance = 0
        self.status = "pending"
        self.version = 0
        self._uncommitted_events = []

    def deposit(self, amount):
        """Command: Deposit money"""
        if self.status != "active":
            raise AccountNotActiveError()
        if amount <= 0:
            raise InvalidAmountError()

        # Create and apply event
        event = MoneyDeposited(
            accountId=self.account_id,
            amount=amount,
            balanceAfter=self.balance + amount
        )
        self._apply_event(event)
        self._uncommitted_events.append(event)

    def _apply_event(self, event):
        """Event handler: Update state (NO business logic)"""
        if isinstance(event, AccountOpened):
            self.balance = event.initial_deposit
            self.status = "active"
        elif isinstance(event, MoneyDeposited):
            self.balance = event.balance_after

        self.version += 1
```

**Aggregate boundaries**:
- Small, focused aggregates (< 100 events typical)
- One aggregate per consistency boundary
- Reference other aggregates by ID only
- Use eventual consistency between aggregates

---

## Event Store

### Event Store Responsibilities

**Core operations**:
- Append events (with optimistic concurrency)
- Read stream (all events for aggregate)
- Stream events (for projections)
- Save/load snapshots

**Schema (PostgreSQL)**:

```sql
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(255) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    version INTEGER NOT NULL,
    data JSONB NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMPTZ NOT NULL,
    UNIQUE (aggregate_id, version)
);

CREATE TABLE snapshots (
    aggregate_id VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL,
    data JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (aggregate_id, version)
);
```

**Optimistic concurrency**:

```python
def append_events(aggregate_id, expected_version, events):
    """Append with concurrency control"""
    # Lock and check version
    current_version = get_stream_version(aggregate_id)

    if current_version != expected_version:
        raise ConcurrencyException(
            f"Expected {expected_version}, got {current_version}"
        )

    # Append events
    for i, event in enumerate(events):
        version = expected_version + i + 1
        insert_event(aggregate_id, version, event)

    update_stream_version(aggregate_id, expected_version + len(events))
```

---

## Projections (Read Models)

### Projection Pattern

**Projection**: Read model built by processing events

```
Event Stream → Projection Handler → Read Model
```

**Example**:

```python
class UserProjection:
    """Build user view from events"""

    def handle(self, event):
        if event.event_type == "UserRegistered":
            db.execute(
                "INSERT INTO user_view (user_id, email, status) "
                "VALUES (%s, %s, %s)",
                (event.data['userId'], event.data['email'], 'pending')
            )

        elif event.event_type == "UserActivated":
            db.execute(
                "UPDATE user_view SET status = 'active' WHERE user_id = %s",
                (event.data['userId'],)
            )
```

**Key properties**:
- Idempotent (processing same event twice = same result)
- Eventually consistent with event store
- Can be rebuilt from events
- Optimized for queries

**Checkpoint management**:

```python
# Track last processed event
checkpoint = get_checkpoint("user_view")

# Process new events
for event in stream_events(from_position=checkpoint):
    projection.handle(event)
    update_checkpoint("user_view", event.position)
```

---

## CQRS Integration

### Command Query Responsibility Segregation

**Principle**: Separate write model (commands) from read model (queries)

```
Commands → Aggregate → Events → Event Store
                         ↓
                    Event Bus
                         ↓
            ┌────────────┼────────────┐
            ▼            ▼            ▼
      Projection 1  Projection 2  Projection 3
            ↓            ↓            ↓
      Read Model 1  Read Model 2  Read Model 3
            ↑            ↑            ↑
         Queries      Queries      Queries
```

**Benefits**:
- Scale reads and writes independently
- Multiple read models from same events
- Optimize each read model for its queries
- Flexible schema evolution

---

## Snapshots

### Snapshot Strategy

**Purpose**: Optimize aggregate loading by saving state periodically

```python
# Without snapshot: Load 10,000 events
aggregate = load_aggregate("account-123")  # Slow!

# With snapshot: Load snapshot + recent events
snapshot = load_snapshot("account-123")
recent_events = load_events_after(snapshot.version)
aggregate = apply_events(snapshot.state, recent_events)  # Fast!
```

**Snapshot frequency**:

1. **Every N events**: Snapshot every 100 events
2. **Time-based**: Snapshot aggregates not snapshotted in 7 days
3. **On-demand**: Create snapshot if loading takes > 100ms

**Snapshot storage**:

```python
def save_snapshot(aggregate, event_store):
    snapshot = {
        'aggregateId': aggregate.id,
        'version': aggregate.version,
        'data': {
            'balance': aggregate.balance,
            'status': aggregate.status
        }
    }
    event_store.save_snapshot(snapshot)
```

---

## Saga Pattern

### Long-Running Processes

**Saga**: Coordinate process across multiple aggregates/services

**Example**: Order fulfillment

```
1. Order submitted
2. Reserve inventory → If fails: Cancel order
3. Process payment   → If fails: Release inventory, cancel order
4. Ship order        → If fails: Refund payment, release inventory, cancel
5. Complete order
```

**Implementation**:

```python
class OrderFulfillmentSaga:
    """Coordinate order fulfillment"""

    def handle_event(self, event):
        if event.type == "OrderSubmitted":
            # Step 1: Reserve inventory
            send_command(ReserveInventory(order_id, items))

        elif event.type == "InventoryReserved":
            # Step 2: Process payment
            send_command(ProcessPayment(order_id, amount))

        elif event.type == "PaymentFailed":
            # Compensate: Release inventory
            send_command(ReleaseInventory(order_id, items))
            send_command(CancelOrder(order_id))
```

**Saga state persistence** required for reliability

---

## Event Versioning

### Schema Evolution

**Strategy 1: Weak schema (additive only)**

```python
# V1
{"eventType": "UserRegistered", "userId": "123", "email": "..."}

# V2: Add optional field
{"eventType": "UserRegistered", "userId": "123", "email": "...", "source": "mobile"}

# Handler handles both
def handle(event):
    source = event.get('source', 'unknown')  # Default for old events
```

**Strategy 2: Explicit versioning**

```python
# Event includes version
{"eventType": "UserRegistered", "version": 2, ...}

# Handler routes by version
if event['version'] == 1:
    handle_v1(event)
elif event['version'] == 2:
    handle_v2(event)
```

**Strategy 3: Upcasting**

```python
def upcast(event):
    """Convert old events to latest schema"""
    if event['version'] == 1:
        event['data']['source'] = 'unknown'
        event['version'] = 2
    return event
```

---

## Temporal Queries

### Query Historical State

**Temporal query**: State at specific point in time

```python
def get_aggregate_at_time(aggregate_id, timestamp, event_store):
    """Rebuild aggregate as it was at timestamp"""
    events = event_store.get_events_until(aggregate_id, timestamp)

    aggregate = BankAccount(aggregate_id)
    for event in events:
        aggregate._apply_event(event)

    return aggregate

# Query yesterday's balance
account_yesterday = get_aggregate_at_time("account-123", yesterday, event_store)
print(f"Balance yesterday: {account_yesterday.balance}")
```

**Use cases**:
- Audit investigations
- Regulatory reporting
- "What if" analysis
- Debugging production issues

---

## Production Implementations

### EventStoreDB

**Purpose-built event store**:

```bash
docker run -d -p 2113:2113 eventstore/eventstore:latest
```

```python
from esdbclient import EventStoreDBClient

client = EventStoreDBClient(uri="esdb://localhost:2113?tls=false")

# Append events
client.append_to_stream(
    stream_name="account-123",
    events=[NewEvent(type="MoneyDeposited", data={...})]
)

# Read stream
events = client.get_stream("account-123")
```

### PostgreSQL Event Store

**Advantages**: No new infrastructure, familiar tooling, ACID

```python
class PostgresEventStore:
    def append_events(self, aggregate_id, expected_version, events):
        # Optimistic concurrency control
        # See REFERENCE.md for full implementation
        pass
```

### Kafka as Event Store

**For distributed systems**:

```python
producer.send(
    'user-events',
    key=aggregate_id,
    value=event_data
)
```

---

## Anti-Patterns

### Common Mistakes

**1. Large events**: Keep events focused

```python
# Bad: Kitchen sink
OrderUpdated(changes={...100 fields...})

# Good: Specific events
ItemAdded(productId, quantity, price)
```

**2. Missing idempotency**:

```python
# Bad
def handle(event):
    balance += event.amount  # Applying twice doubles amount!

# Good
def handle(event):
    if event.id not in processed:
        balance += event.amount
        processed.add(event.id)
```

**3. Business logic in projections**:

```python
# Bad: Logic in projection
def handle(event):
    if event.total > 1000:
        discount = calculate_discount(event.total)  # Business logic!

# Good: Logic in aggregate, event contains result
# Event: OrderPlaced(total=1000, discount=100)
```

**4. No versioning strategy**: Plan for schema evolution from day one

**5. Synchronous projections**: Projections should be asynchronous

---

## Performance Optimization

### Key Optimizations

**1. Snapshots**: Massive speedup for large aggregates

**2. Indexing**:

```sql
CREATE INDEX idx_events_aggregate ON events(aggregate_id, version);
CREATE INDEX idx_events_id ON events(id);
CREATE INDEX idx_events_type ON events(event_type);
```

**3. Projection batching**:

```python
# Batch commit every 100 events
batch = []
for event in events:
    projection.handle(event)
    batch.append(event)
    if len(batch) >= 100:
        db.commit()
        batch = []
```

**4. Read model denormalization**: Optimize for queries

**5. Caching**: Cache frequently-accessed aggregates

---

## Testing Event-Sourced Systems

### Test Strategies

**1. Aggregate behavior**:

```python
def test_withdraw_reduces_balance():
    account = BankAccount.open("account-123", "Alice", 1000)
    account.withdraw(200)
    assert account.balance == 800
```

**2. Event production**:

```python
def test_withdraw_produces_event():
    account.withdraw(200)
    events = account.get_uncommitted_events()
    assert events[-1].event_type == "MoneyWithdrawn"
```

**3. Event replay**:

```python
def test_rebuild_from_events():
    events = [
        AccountOpened(accountId="123", initialDeposit=1000),
        MoneyDeposited(accountId="123", amount=500)
    ]
    account = BankAccount.from_events("123", events)
    assert account.balance == 1500
```

**4. Projection correctness**:

```python
def test_projection_handles_event():
    projection.handle(UserRegistered(userId="123", email="alice@example.com"))
    user = db.query("SELECT * FROM user_view WHERE user_id = '123'")
    assert user['email'] == "alice@example.com"
```

---

## Level 3: Resources

### Reference Documentation

**REFERENCE.md** (2,378 lines): Comprehensive guide covering:
- Event sourcing fundamentals
- Event design patterns (naming, structure, granularity)
- Aggregate design and lifecycle
- Event store architecture (PostgreSQL schema, operations)
- Projections and read models
- Snapshot strategies (frequency, storage, loading)
- CQRS integration patterns
- Saga patterns for distributed transactions
- Event versioning and schema evolution
- Temporal queries and event replay
- Production implementations (EventStoreDB, PostgreSQL, Kafka, Axon, Marten)
- Common anti-patterns and solutions
- Performance optimization techniques
- Testing strategies (aggregates, projections, idempotency)

Location: `skills/distributed-systems/event-sourcing/resources/REFERENCE.md`

### Executable Scripts

**1. validate_events.py** (16K, 575 lines)

Validates event schemas and design patterns.

```bash
# Validate event file
./validate_events.py --file events.json

# Validate directory
./validate_events.py --directory ./events --json

# Validate from event store
./validate_events.py --stream postgres://localhost/events --aggregate-id account-123
```

Features:
- Event naming validation (past tense)
- Schema validation (required fields)
- Idempotency checks
- Payload size limits
- Anti-pattern detection
- JSON output support

**2. replay_events.py** (17K, 600 lines)

Replay events for debugging, temporal queries, and projection rebuilds.

```bash
# Debug aggregate
./replay_events.py --source postgres://localhost/events --aggregate account-123 --debug

# Rebuild projection
./replay_events.py --source postgres://localhost/events --projection user_view

# Temporal query
./replay_events.py --source postgres://localhost/events --temporal account-123 --until "2025-10-01"

# Event store statistics
./replay_events.py --source postgres://localhost/events --stats
```

Features:
- Step-by-step aggregate debugging
- Projection rebuilding
- Temporal queries
- Event comparison
- Statistics analysis
- File and database sources

**3. benchmark_eventstore.py** (22K, 820 lines)

Benchmark event store performance.

```bash
# Write benchmark
./benchmark_eventstore.py --store postgres://localhost/events --write --events 10000

# Read benchmark
./benchmark_eventstore.py --store postgres://localhost/events --read --aggregates 100

# Concurrent writes
./benchmark_eventstore.py --store postgres://localhost/events --concurrent 10

# Full benchmark suite
./benchmark_eventstore.py --store postgres://localhost/events --full --json
```

Features:
- Single and batch writes
- Aggregate reads
- Concurrent operations
- Event streaming
- Latency percentiles (p95, p99)
- Throughput measurement
- JSON output

Location: `skills/distributed-systems/event-sourcing/resources/scripts/`

### Production-Ready Examples

**1. Bank Account Aggregate (Python)** - Complete aggregate implementation with command handling, event production, and state reconstruction

**2. PostgreSQL Event Store (Python)** - Full event store with optimistic concurrency, snapshots, and connection pooling

**3. User View Projection (Python)** - Projection with checkpoint management and continuous processing

**4. Order Aggregate (TypeScript)** - Type-safe aggregate with strong typing and invariant enforcement

**5. Event Schemas (JSON Schema)** - Comprehensive event schema definitions with validation

**6. Docker Compose Setup** - Complete event sourcing stack (PostgreSQL, EventStoreDB, Kafka, Redis)

**7. SQL Initialization** - Event store database schema with indexes and triggers

**8. Order Fulfillment Saga (Python)** - Saga pattern with compensating transactions and state management

Location: `skills/distributed-systems/event-sourcing/resources/examples/`

All examples are:
- Production-ready with error handling
- Fully documented with docstrings
- Executable with example usage
- Following best practices
- Demonstrating key patterns

---

## Quick Decision Tree

```
Need to track state changes?
  ├─ Audit trail critical? → Event sourcing
  ├─ Temporal queries needed? → Event sourcing
  ├─ Multiple read models? → Event sourcing + CQRS
  ├─ Simple CRUD? → Traditional persistence
  └─ Team unfamiliar? → Start simple, migrate later

Implementing event sourcing?
  ├─ Design events (past tense, focused)
  ├─ Create aggregates (enforce invariants)
  ├─ Set up event store (PostgreSQL/EventStoreDB)
  ├─ Build projections (asynchronous)
  ├─ Add snapshots (for performance)
  ├─ Plan versioning (additive changes)
  └─ Test thoroughly (aggregates, replay, projections)
```

---

## References

**Books**:
- "Domain-Driven Design" by Eric Evans
- "Implementing Domain-Driven Design" by Vaughn Vernon
- "Versioning in an Event Sourced System" by Greg Young

**Online**:
- Martin Fowler: Event Sourcing pattern
- Greg Young: CQRS and Event Sourcing talks
- EventStoreDB documentation
- Microsoft CQRS Journey

**Tools**:
- EventStoreDB: https://www.eventstore.com/
- Marten (PostgreSQL): https://martendb.io/
- Axon Framework (Java): https://axoniq.io/

**Last Updated**: 2025-10-27
