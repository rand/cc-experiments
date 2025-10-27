---
name: distributed-systems-crdt-fundamentals
description: Conflict-free Replicated Data Types (CRDTs) fundamentals including convergence, commutativity, and basic CRDT operations
---

# CRDT Fundamentals

**Scope**: CRDTs, eventual consistency, conflict-free merging, convergence properties
**Lines**: ~320
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building collaborative applications
- Implementing offline-first apps
- Designing distributed databases
- Understanding Redis, Riak internals
- Building real-time sync systems
- Handling network partitions gracefully
- Avoiding distributed locks
- Implementing eventual consistency

## Core Concepts

### What are CRDTs?

**CRDT**: Conflict-free Replicated Data Type

**Key property**: Replicas can be updated independently and concurrently, and are guaranteed to converge to same state

```
Replica A:  value = 1  →  value += 5  →  value = 6  ─┐
                                                       ├→ Merge → value = 9
Replica B:  value = 1  →  value += 3  →  value = 4  ─┘

Without coordination, replicas converge!
```

**Benefits**:
- No coordination needed
- Always available (AP in CAP)
- Eventually consistent
- Partition tolerant

### Strong Eventual Consistency (SEC)

**Guarantee**: Replicas that have received same updates are in same state

**Requirements**:
1. **Convergence**: f(f(s, u1), u2) = f(f(s, u2), u1)  (commutative)
2. **Monotonic**: Once applied, updates never rolled back

---

## CRDT Categories

### Operation-based CRDTs (CmRDTs)

**Approach**: Broadcast operations, apply in order

**Requirements**:
- Reliable broadcast (exactly-once delivery)
- Commutative operations

**Example**: G-Counter (grow-only counter)
```python
class GCounter:
    """Operation-based grow-only counter"""

    def __init__(self, replica_id, n_replicas):
        self.replica_id = replica_id
        self.counts = [0] * n_replicas  # One count per replica

    def increment(self):
        """Increment local counter"""
        self.counts[self.replica_id] += 1
        return ('increment', self.replica_id)  # Operation to broadcast

    def apply_operation(self, operation):
        """Apply received operation"""
        op_type, replica_id = operation
        if op_type == 'increment':
            self.counts[replica_id] += 1

    def value(self):
        """Get total count"""
        return sum(self.counts)
```

### State-based CRDTs (CvRDTs)

**Approach**: Periodically merge entire state

**Requirements**:
- Idempotent merge function
- Commutative merge
- Associative merge

**Example**: G-Counter (state-based)
```python
class GCounterState:
    """State-based grow-only counter"""

    def __init__(self, replica_id, n_replicas):
        self.replica_id = replica_id
        self.counts = [0] * n_replicas

    def increment(self):
        """Increment local counter"""
        self.counts[self.replica_id] += 1

    def merge(self, other):
        """Merge with another replica (element-wise max)"""
        new_counts = [
            max(self.counts[i], other.counts[i])
            for i in range(len(self.counts))
        ]
        result = GCounterState(self.replica_id, len(self.counts))
        result.counts = new_counts
        return result

    def value(self):
        """Get total count"""
        return sum(self.counts)

# Usage
replica_a = GCounterState(0, 3)
replica_b = GCounterState(1, 3)

replica_a.increment()
replica_a.increment()
replica_b.increment()

# Merge (commutative, idempotent)
merged = replica_a.merge(replica_b)
print(merged.value())  # 3
```

---

## Common CRDT Types

### G-Counter (Grow-Only Counter)

**Operations**: Increment only

**Properties**:
- Monotonically increasing
- Simple merge (element-wise max)

**Use cases**: Page views, likes, metrics

### PN-Counter (Positive-Negative Counter)

**Idea**: Two G-Counters (positive and negative)

```python
class PNCounter:
    """Counter that can increment and decrement"""

    def __init__(self, replica_id, n_replicas):
        self.replica_id = replica_id
        self.positive = GCounterState(replica_id, n_replicas)
        self.negative = GCounterState(replica_id, n_replicas)

    def increment(self):
        self.positive.increment()

    def decrement(self):
        self.negative.increment()

    def value(self):
        return self.positive.value() - self.negative.value()

    def merge(self, other):
        result = PNCounter(self.replica_id, len(self.positive.counts))
        result.positive = self.positive.merge(other.positive)
        result.negative = self.negative.merge(other.negative)
        return result
```

### G-Set (Grow-Only Set)

```python
class GSet:
    """Grow-only set (add-only)"""

    def __init__(self):
        self.elements = set()

    def add(self, element):
        self.elements.add(element)

    def lookup(self, element):
        return element in self.elements

    def merge(self, other):
        """Union of sets"""
        result = GSet()
        result.elements = self.elements | other.elements
        return result
```

### 2P-Set (Two-Phase Set)

**Idea**: Two G-Sets (added and removed)

```python
class TwoPhaseSet:
    """Add and remove, but can't re-add after remove"""

    def __init__(self):
        self.added = set()
        self.removed = set()

    def add(self, element):
        self.added.add(element)

    def remove(self, element):
        if element in self.added:
            self.removed.add(element)

    def lookup(self, element):
        return element in self.added and element not in self.removed

    def merge(self, other):
        result = TwoPhaseSet()
        result.added = self.added | other.added
        result.removed = self.removed | other.removed
        return result
```

---

## Practical Example: Collaborative Counter

```python
import time
from typing import Dict

class DistributedCounter:
    """Production-ready distributed counter using PN-Counter CRDT"""

    def __init__(self, replica_id: str, all_replicas: list):
        self.replica_id = replica_id
        self.all_replicas = all_replicas
        self.counter = PNCounter(replica_id, len(all_replicas))

    def increment(self, amount: int = 1):
        """Increment counter locally"""
        for _ in range(amount):
            self.counter.increment()

    def decrement(self, amount: int = 1):
        """Decrement counter locally"""
        for _ in range(amount):
            self.counter.decrement()

    def get_value(self) -> int:
        """Get current counter value"""
        return self.counter.value()

    def sync_with_replica(self, other_replica):
        """Sync state with another replica"""
        self.counter = self.counter.merge(other_replica.counter)

    def periodic_sync(self, interval: int = 5):
        """Periodically sync with all replicas"""
        while True:
            for replica in self.all_replicas:
                if replica != self:
                    self.sync_with_replica(replica)
            time.sleep(interval)

# Usage
replicas = [
    DistributedCounter('A', []),
    DistributedCounter('B', []),
    DistributedCounter('C', [])
]

# Each replica has reference to others
for r in replicas:
    r.all_replicas = replicas

# Concurrent updates
replicas[0].increment(5)
replicas[1].increment(3)
replicas[2].decrement(2)

# Sync
for i in range(len(replicas)):
    for j in range(i + 1, len(replicas)):
        replicas[i].sync_with_replica(replicas[j])

# All replicas converge to same value
assert replicas[0].get_value() == replicas[1].get_value() == replicas[2].get_value()
```

---

## CRDT Properties

### Convergence

**Property**: All replicas eventually reach same state

**How**:
```
Merge must be:
1. Commutative: merge(A, B) = merge(B, A)
2. Idempotent: merge(A, A) = A
3. Associative: merge(merge(A, B), C) = merge(A, merge(B, C))
```

**Test**:
```python
def test_convergence():
    """Test that replicas converge regardless of merge order"""
    r1 = GCounterState(0, 2)
    r2 = GCounterState(1, 2)

    r1.increment()
    r1.increment()
    r2.increment()

    # Merge in different orders
    result1 = r1.merge(r2)
    result2 = r2.merge(r1)

    assert result1.value() == result2.value()  # Convergence
```

### Monotonicity

**Property**: State only grows, never shrinks (in terms of information)

**Implication**: Can't truly "delete" - must use tombstones

---

## Trade-offs

### Advantages

```
✅ No coordination needed
✅ Always available
✅ Partition tolerant
✅ Low latency (local operations)
✅ Offline-first friendly
```

### Disadvantages

```
❌ Limited operations (must be commutative)
❌ Metadata overhead (tracking causality)
❌ Some operations complex (e.g., remove from set)
❌ Conflicts resolved automatically (may not match user intent)
❌ Growing state size (garbage collection needed)
```

---

## When to Use CRDTs

### Good Fit

```
✅ Collaborative editing (Google Docs, Figma)
✅ Distributed databases (Riak, Redis)
✅ Shopping cart
✅ Presence indicators (online/offline)
✅ Like counters
✅ Distributed caching
```

### Poor Fit

```
❌ Financial transactions (need strong consistency)
❌ Inventory management (can't oversell)
❌ Sequential operations (order matters)
❌ Complex business logic
```

---

## Comparison with Other Approaches

| Approach | Consistency | Availability | Coordination | Latency |
|----------|------------|--------------|--------------|---------|
| **CRDTs** | Eventual | High | None | Low |
| **Consensus (RAFT)** | Strong | Medium | High | Medium |
| **2PC** | Strong | Low | High | High |
| **Last-Write-Wins** | Weak | High | None | Low |

---

## Real-World Examples

### Redis

```python
# Redis CRDT support (Redis Enterprise)
import redis

r = redis.Redis()

# CRDT Counter
r.execute_command('CRDT.COUNTER', 'mykey', 'INC', 5)

# CRDT Set
r.execute_command('CRDT.ORADD', 'myset', 'element')
```

### Riak

```python
# Riak KV with CRDTs
from riak import RiakClient

client = RiakClient()
bucket = client.bucket_type('maps').bucket('my_bucket')

# Riak Map CRDT
my_map = bucket.new()
my_map.counters['page_views'].increment(1)
my_map.sets['tags'].add('crdt')
my_map.store()
```

---

## Testing CRDTs

```python
import unittest

class TestCRDT(unittest.TestCase):
    def test_commutativity(self):
        """Test merge is commutative"""
        r1 = GCounterState(0, 2)
        r2 = GCounterState(1, 2)

        r1.increment()
        r2.increment()
        r2.increment()

        # merge(A, B) == merge(B, A)
        result1 = r1.merge(r2)
        result2 = r2.merge(r1)

        self.assertEqual(result1.value(), result2.value())

    def test_idempotence(self):
        """Test merge is idempotent"""
        r1 = GCounterState(0, 2)
        r1.increment()

        # merge(A, A) == A
        result = r1.merge(r1)
        self.assertEqual(result.value(), r1.value())

    def test_associativity(self):
        """Test merge is associative"""
        r1 = GCounterState(0, 3)
        r2 = GCounterState(1, 3)
        r3 = GCounterState(2, 3)

        r1.increment()
        r2.increment()
        r3.increment()

        # merge(merge(A, B), C) == merge(A, merge(B, C))
        result1 = r1.merge(r2).merge(r3)
        result2 = r1.merge(r2.merge(r3))

        self.assertEqual(result1.value(), result2.value())
```

---

## Level 3: Resources

**Location**: `skills/distributed-systems/crdt-fundamentals/resources/`

### Reference Documentation

**REFERENCE.md** (~950 lines): Comprehensive CRDT reference covering:
- Theoretical foundation (strong eventual consistency, commutativity, semilattice structure)
- Operation-based CRDTs: G-Counter, PN-Counter, G-Set, 2P-Set, OR-Set
- State-based CRDTs: LWW-Element-Set, LWW-Register, MV-Register
- Sequence CRDTs: RGA, WOOT, LSEQ, Logoot
- Map and composite CRDTs (OR-Map, LWW-Map, JSON structures)
- Conflict resolution semantics (LWW, MV, add-wins, remove-wins)
- CRDT implementations (Automerge, Yjs, CRJSON, Riak, Redis, Akka)
- CAP theorem positioning and tradeoffs
- Performance characteristics (space/time complexity, network overhead)
- Design patterns (layered CRDTs, intent preservation, constraints, hybrid consistency, undo)
- Testing and verification strategies

### Scripts

**simulate_crdt.py**: Simulate CRDT operations with concurrent replicas
- Implementations: G-Counter, PN-Counter, OR-Set, LWW-Set, RGA
- Predefined scenarios demonstrating convergence
- Support for custom operation sequences
- JSON output for integration

```bash
# Simulate G-Counter with 3 replicas
./simulate_crdt.py g-counter --replicas 3

# Simulate OR-Set with concurrent add/remove
./simulate_crdt.py or-set --scenario concurrent-ops --json

# Simulate RGA text editing
./simulate_crdt.py rga --scenario text-edit
```

**benchmark_merge.py**: Benchmark CRDT merge performance
- Merge scaling with increasing state sizes
- Replica scaling (2 to 20+ replicas)
- Conflict rate impact on merge performance
- Individual operation performance
- Memory usage analysis

```bash
# Benchmark all CRDTs
./benchmark_merge.py all --benchmark all

# Benchmark specific CRDT with custom sizes
./benchmark_merge.py or-set --benchmark merge-scaling --sizes 10,100,1000

# JSON output for visualization
./benchmark_merge.py pn-counter --json > results.json
```

**visualize_convergence.py**: Generate convergence diagrams
- ASCII timeline visualization
- Mermaid sequence diagrams
- Graphviz DOT graphs
- JSON data export

```bash
# ASCII visualization of linear convergence
./visualize_convergence.py g-counter --scenario linear

# Mermaid diagram for star topology
./visualize_convergence.py or-set --scenario star --format mermaid

# Export all formats
./visualize_convergence.py g-counter --scenario partition --format all -o convergence.md
```

### Examples

**Python**:
- `g_counter.py`: G-Counter with serialization, distributed system simulation
- `or_set.py`: OR-Set with add-wins semantics, shopping cart example
- `lww_register.py`: LWW-Register with hybrid logical clocks, MV-Register

**TypeScript**:
- `yjs-collaborative-editing.ts`: Real-time collaborative text editing with Yjs
  - Text, map, array synchronization
  - Undo/redo support
  - Observers and persistence
  - Collaborative todo list

**JavaScript**:
- `automerge-example.js`: Automerge for JSON CRDTs
  - Document collaboration
  - Nested objects and lists
  - History and time travel
  - Conflict resolution

All examples are runnable and include multiple scenarios demonstrating:
- Basic CRDT operations
- Concurrent operations and convergence
- Distributed system simulation
- Real-world applications

---

## Related Skills

- `distributed-systems-crdt-types` - Specific CRDT implementations
- `distributed-systems-eventual-consistency` - Consistency models
- `distributed-systems-conflict-resolution` - Conflict handling
- `distributed-systems-vector-clocks` - Causality tracking

---

**Last Updated**: 2025-10-27
