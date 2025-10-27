---
name: distributed-systems-eventual-consistency
description: Eventual consistency models, consistency levels, read/write quorums, and practical trade-offs in distributed systems
---

# Eventual Consistency

**Scope**: Eventual consistency, consistency levels, quorums, BASE, practical considerations
**Lines**: ~300
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building highly available systems
- Designing AP systems (CAP theorem)
- Working with Cassandra, DynamoDB
- Understanding NoSQL databases
- Implementing distributed caching
- Handling network partitions
- Optimizing for low latency
- Building global systems

## Core Concepts

### ACID vs BASE

**ACID** (traditional databases):
```
Atomicity: All or nothing
Consistency: Valid state always
Isolation: Concurrent transactions don't interfere
Durability: Committed data persists
```

**BASE** (eventually consistent systems):
```
Basically Available: System appears to work most of the time
Soft state: State may change without input (due to eventual consistency)
Eventual consistency: System becomes consistent over time
```

### Eventual Consistency

**Definition**: If no new updates made, all replicas eventually converge to same value

**Key property**: Temporary inconsistency tolerated for availability

```
Time →
Replica A: v1 ─→ v2 ────────────→ v3
Replica B: v1 ────→ v2 ─→ v2' ──→ v3
Replica C: v1 ───────→ v2 ───────→ v3

Eventually all reach v3 (after replication settles)
```

---

## Consistency Levels

### Spectrum of Consistency

```
Strongest ←──────────────────────────────────────→ Weakest

Linearizable (Strong Consistency)
├─ All operations appear instantaneous
├─ Total global order
└─ Example: Single-node database

Sequential Consistency
├─ Operations appear in same order to all
├─ Order respects program order per process
└─ Example: Some distributed databases

Causal Consistency
├─ Causally-related operations seen in order
├─ Concurrent operations may differ
└─ Example: Systems with vector clocks

Eventual Consistency
├─ Replicas converge eventually
├─ No ordering guarantees
└─ Example: DNS, Cassandra (default)
```

### Tunable Consistency

**Common in NoSQL databases** (Cassandra, Riak):

```python
# Cassandra example
from cassandra.cluster import Cluster
from cassandra import ConsistencyLevel

cluster = Cluster(['node1', 'node2', 'node3'])
session = cluster.connect('my_keyspace')

# Write to ONE node (fastest, least consistent)
session.execute(query, consistency_level=ConsistencyLevel.ONE)

# Write to QUORUM (balance)
session.execute(query, consistency_level=ConsistencyLevel.QUORUM)

# Write to ALL nodes (slowest, most consistent)
session.execute(query, consistency_level=ConsistencyLevel.ALL)
```

---

## Read/Write Quorums

### Quorum Formula

**N**: Number of replicas
**W**: Write quorum (nodes that must acknowledge write)
**R**: Read quorum (nodes that must respond to read)

**Strong consistency**: `W + R > N`
**Eventual consistency**: `W + R ≤ N`

### Examples

```
N=3 replicas:

W=2, R=2: W+R=4 > N=3 ✅ Strong consistency
W=1, R=1: W+R=2 < N=3 ❌ Eventual consistency

W=3, R=1: Consistent reads (all nodes have latest)
W=1, R=3: Fast writes, slow reads

W=2, R=1: Common balance (allows 1 node failure)
```

### Implementation

```python
class QuorumStore:
    """Key-value store with quorum reads/writes"""

    def __init__(self, nodes, n, w, r):
        self.nodes = nodes
        self.n = n  # Total replicas
        self.w = w  # Write quorum
        self.r = r  # Read quorum

    def write(self, key, value):
        """Write to W replicas"""
        acks = 0
        for node in self.nodes[:self.n]:
            try:
                if node.write(key, value):
                    acks += 1
                if acks >= self.w:
                    return True  # Quorum reached
            except:
                continue

        raise QuorumNotMetError(f"Only {acks}/{self.w} acks")

    def read(self, key):
        """Read from R replicas, return latest version"""
        responses = []

        for node in self.nodes[:self.n]:
            try:
                value, version = node.read(key)
                responses.append((value, version))
                if len(responses) >= self.r:
                    break  # Quorum reached
            except:
                continue

        if len(responses) < self.r:
            raise QuorumNotMetError(f"Only {len(responses)}/{self.r} responses")

        # Return value with highest version
        return max(responses, key=lambda x: x[1])[0]
```

---

## Consistency Models in Practice

### Read Your Writes

**Guarantee**: After write, your reads see that write (or later)

```python
class ReadYourWritesStore:
    """Ensures client sees own writes"""

    def __init__(self, store):
        self.store = store
        self.client_versions = {}  # client_id → last written version

    def write(self, client_id, key, value):
        """Write and track version"""
        version = self.store.write(key, value)
        self.client_versions[client_id] = version
        return version

    def read(self, client_id, key):
        """Read with minimum version guarantee"""
        min_version = self.client_versions.get(client_id, 0)

        value, version = self.store.read(key)

        # Wait if necessary to see own write
        while version < min_version:
            time.sleep(0.01)
            value, version = self.store.read(key)

        return value
```

### Monotonic Reads

**Guarantee**: Once read value V, won't later read older value

```python
class MonotonicReadsStore:
    """Ensures non-decreasing versions"""

    def __init__(self, store):
        self.store = store
        self.client_max_versions = {}  # client_id → max seen version

    def read(self, client_id, key):
        """Read with monotonic version guarantee"""
        max_seen = self.client_max_versions.get(client_id, 0)

        value, version = self.store.read(key)

        # Wait if version went backwards
        while version < max_seen:
            time.sleep(0.01)
            value, version = self.store.read(key)

        self.client_max_versions[client_id] = max(max_seen, version)
        return value
```

### Monotonic Writes

**Guarantee**: Writes by same client applied in order

```python
class MonotonicWritesStore:
    """Ensures writes from client ordered"""

    def __init__(self, store):
        self.store = store
        self.client_write_queues = {}  # client_id → ordered writes

    def write(self, client_id, key, value):
        """Queue write to ensure ordering"""
        if client_id not in self.client_write_queues:
            self.client_write_queues[client_id] = []

        write_op = (key, value)
        self.client_write_queues[client_id].append(write_op)

        # Process writes in order
        self._process_write_queue(client_id)

    def _process_write_queue(self, client_id):
        """Process queued writes in order"""
        while self.client_write_queues[client_id]:
            key, value = self.client_write_queues[client_id][0]
            try:
                self.store.write(key, value)
                self.client_write_queues[client_id].pop(0)
            except:
                break  # Retry later
```

---

## Conflict Resolution

### Last-Write-Wins (LWW)

```python
class LWWStore:
    """Resolve conflicts with timestamps"""

    def __init__(self):
        self.data = {}  # key → (value, timestamp)

    def write(self, key, value, timestamp):
        """Write if timestamp is latest"""
        if key not in self.data or timestamp > self.data[key][1]:
            self.data[key] = (value, timestamp)

    def merge(self, other):
        """Merge with another replica"""
        for key, (value, timestamp) in other.data.items():
            if key not in self.data or timestamp > self.data[key][1]:
                self.data[key] = (value, timestamp)
```

### Vector Clocks

```python
# See vector-clocks skill for full implementation

class VectorClockStore:
    """Track causality to detect conflicts"""

    def write(self, key, value):
        """Write with vector clock"""
        vc = self.get_next_vector_clock()
        self.data[key] = (value, vc)

    def read(self, key):
        """Return all concurrent versions"""
        return [v for v, vc in self.data[key]]  # Siblings
```

---

## Trade-offs

### When to Use Eventual Consistency

```
✅ High write throughput required
✅ Low latency critical
✅ Global distribution needed
✅ Availability > consistency
✅ Conflicts rare or easily resolved
✅ Data can be stale briefly

Examples:
- Social media feeds
- Product catalogs
- User profiles
- Analytics data
- Caching layers
```

### When to Use Strong Consistency

```
✅ Correctness critical
✅ Complex transactions
✅ Can tolerate higher latency
✅ Single region
✅ Consistency > availability

Examples:
- Financial transactions
- Inventory management
- Booking systems
- Configuration data
- Distributed locks
```

---

## Real-World Examples

### DynamoDB

```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Users')

# Eventually consistent read (default, faster)
response = table.get_item(
    Key={'user_id': '123'}
)

# Strongly consistent read (slower, guaranteed latest)
response = table.get_item(
    Key={'user_id': '123'},
    ConsistentRead=True
)
```

### Cassandra

```python
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from cassandra import ConsistencyLevel

cluster = Cluster()
session = cluster.connect('my_keyspace')

# Eventual consistency (fast)
session.execute(
    "SELECT * FROM users WHERE user_id = %s",
    [user_id],
    consistency_level=ConsistencyLevel.ONE
)

# Strong consistency (slower)
session.execute(
    "SELECT * FROM users WHERE user_id = %s",
    [user_id],
    consistency_level=ConsistencyLevel.QUORUM
)
```

---

## Testing Eventual Consistency

```python
import unittest
import time

class TestEventualConsistency(unittest.TestCase):
    def test_convergence(self):
        """Test replicas eventually converge"""
        store_a = EventuallyConsistentStore()
        store_b = EventuallyConsistentStore()

        # Concurrent writes
        store_a.write('key', 'value_a')
        store_b.write('key', 'value_b')

        # Replicate
        store_a.merge(store_b)
        store_b.merge(store_a)

        # Should converge (same conflict resolution)
        self.assertEqual(store_a.read('key'), store_b.read('key'))

    def test_read_your_writes(self):
        """Test client sees own writes"""
        store = ReadYourWritesStore(backend_store)
        client_id = 'client_1'

        store.write(client_id, 'key', 'value')
        result = store.read(client_id, 'key')

        self.assertEqual(result, 'value')
```

---

## Related Skills

- `distributed-systems-cap-theorem` - Consistency vs availability
- `distributed-systems-conflict-resolution` - Handling conflicts
- `distributed-systems-crdt-fundamentals` - Conflict-free data types
- `distributed-systems-replication-strategies` - Replication patterns

---

**Last Updated**: 2025-10-27
