---
name: distributed-systems-vector-clocks
description: Vector clocks for tracking causality in distributed systems, detecting concurrent events, and resolving conflicts
---

# Vector Clocks

**Scope**: Vector clocks, causality tracking, happens-before relationships, conflict detection
**Lines**: ~310
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Tracking causality in distributed systems
- Detecting concurrent events
- Implementing conflict resolution
- Understanding Dynamo, Riak internals
- Building distributed databases
- Implementing version control
- Detecting data races
- Ordering distributed events

## Core Concepts

### The Problem: Physical Time Unreliable

```
Server A (clock slow):  t=100 → Write X=1
Server B (clock fast):  t=105 → Write X=2

Which happened first? Can't tell from timestamps!
```

### Lamport Clocks (Logical Time)

**Single counter per system**:
```python
class LamportClock:
    def __init__(self):
        self.time = 0

    def increment(self):
        """Increment on local event"""
        self.time += 1
        return self.time

    def update(self, received_time):
        """Update on receiving message"""
        self.time = max(self.time, received_time) + 1
        return self.time
```

**Problem**: Can't detect concurrency
```
A: t=1 → t=2 → t=3
B:        t=1 → t=2

A:t=2 and B:t=2 concurrent? Can't tell!
```

### Vector Clocks (Track All Processes)

**One counter per process**:
```python
class VectorClock:
    def __init__(self, process_id, num_processes):
        self.process_id = process_id
        self.clock = [0] * num_processes

    def increment(self):
        """Increment local counter"""
        self.clock[self.process_id] += 1
        return self.clock.copy()

    def update(self, received_clock):
        """Merge with received clock"""
        for i in range(len(self.clock)):
            self.clock[i] = max(self.clock[i], received_clock[i])
        self.clock[self.process_id] += 1
        return self.clock.copy()

    def compare(self, other_clock):
        """Compare vector clocks"""
        less_than = any(self.clock[i] < other_clock[i] for i in range(len(self.clock)))
        greater_than = any(self.clock[i] > other_clock[i] for i in range(len(self.clock)))

        if less_than and not greater_than:
            return "BEFORE"  # self happened before other
        elif greater_than and not less_than:
            return "AFTER"   # self happened after other
        elif not less_than and not greater_than:
            return "EQUAL"   # same event
        else:
            return "CONCURRENT"  # concurrent events
```

---

## Happens-Before Relationship

### Definition

**Event A happens-before event B** if:
1. A and B on same process, A before B
2. A is send, B is receive of same message
3. Transitive: A → B and B → C implies A → C

**Vector clock property**: A happens-before B ⟺ VC(A) < VC(B)

### Example

```
Process A:  [1,0,0] → send msg → [2,0,0]
Process B:  [0,1,0] → receive → [2,2,0] → [2,3,0]
Process C:  [0,0,1] → [0,0,2]

Relationships:
[1,0,0] happens-before [2,3,0]  (A:send before B:receive)
[1,0,0] concurrent with [0,0,1] (different processes, no communication)
```

---

## Implementation

### Full Implementation

```python
from typing import Dict, List, Tuple

class VectorClock:
    """Vector clock for distributed system"""

    def __init__(self, node_id: str, nodes: List[str]):
        self.node_id = node_id
        self.nodes = nodes
        self.clock = {node: 0 for node in nodes}

    def tick(self) -> Dict[str, int]:
        """Increment local clock on local event"""
        self.clock[self.node_id] += 1
        return self.get_clock()

    def send_event(self) -> Dict[str, int]:
        """Prepare vector clock for sending"""
        return self.tick()

    def receive_event(self, received_clock: Dict[str, int]) -> Dict[str, int]:
        """Update clock on receiving message"""
        # Merge clocks (element-wise max)
        for node in self.nodes:
            self.clock[node] = max(
                self.clock.get(node, 0),
                received_clock.get(node, 0)
            )
        # Increment local clock
        self.clock[self.node_id] += 1
        return self.get_clock()

    def get_clock(self) -> Dict[str, int]:
        """Get current clock value"""
        return self.clock.copy()

    def happens_before(self, vc1: Dict[str, int], vc2: Dict[str, int]) -> bool:
        """Check if vc1 happens before vc2"""
        # vc1 ≤ vc2 for all components, and vc1 < vc2 for at least one
        less_or_equal = all(vc1.get(n, 0) <= vc2.get(n, 0) for n in self.nodes)
        strictly_less = any(vc1.get(n, 0) < vc2.get(n, 0) for n in self.nodes)
        return less_or_equal and strictly_less

    def concurrent(self, vc1: Dict[str, int], vc2: Dict[str, int]) -> bool:
        """Check if vc1 and vc2 are concurrent"""
        return not self.happens_before(vc1, vc2) and not self.happens_before(vc2, vc1)

# Usage Example
nodes = ['A', 'B', 'C']
vc_a = VectorClock('A', nodes)
vc_b = VectorClock('B', nodes)
vc_c = VectorClock('C', nodes)

# Process A: local event
clock_a1 = vc_a.tick()  # A: {A:1, B:0, C:0}

# Process A: send to B
msg_clock = vc_a.send_event()  # A: {A:2, B:0, C:0}

# Process B: receive from A
vc_b.receive_event(msg_clock)  # B: {A:2, B:1, C:0}

# Process B: local event
clock_b1 = vc_b.tick()  # B: {A:2, B:2, C:0}

# Process C: independent event
clock_c1 = vc_c.tick()  # C: {A:0, B:0, C:1}

# Check relationships
print(vc_a.happens_before(clock_a1, clock_b1))  # True (A's event before B's)
print(vc_a.concurrent(clock_a1, clock_c1))      # True (independent)
```

---

## Practical Applications

### Application 1: Distributed Key-Value Store

```python
class VersionedValue:
    """Value with vector clock version"""

    def __init__(self, value, vector_clock):
        self.value = value
        self.vector_clock = vector_clock

class DistributedKVStore:
    """Key-value store with vector clock versioning"""

    def __init__(self, node_id, nodes):
        self.node_id = node_id
        self.vc = VectorClock(node_id, nodes)
        self.store = {}  # key → list of VersionedValue

    def put(self, key, value):
        """Write value with current vector clock"""
        clock = self.vc.tick()
        versioned = VersionedValue(value, clock)

        if key not in self.store:
            self.store[key] = [versioned]
        else:
            # Remove versions that this one supersedes
            self.store[key] = [
                v for v in self.store[key]
                if not self.vc.happens_before(v.vector_clock, clock)
            ]
            self.store[key].append(versioned)

        return clock

    def get(self, key):
        """Get value(s) for key"""
        if key not in self.store:
            return None

        # Return all concurrent versions (siblings)
        versions = self.store[key]
        if len(versions) == 1:
            return versions[0].value
        else:
            # Multiple concurrent versions - conflict!
            return [v.value for v in versions]

    def merge_from_replica(self, key, versioned_values):
        """Merge values from another replica"""
        if key not in self.store:
            self.store[key] = versioned_values
            return

        # Merge versions
        all_versions = self.store[key] + versioned_values

        # Remove dominated versions
        result = []
        for v1 in all_versions:
            dominated = False
            for v2 in all_versions:
                if v1 != v2 and self.vc.happens_before(v1.vector_clock, v2.vector_clock):
                    dominated = True
                    break
            if not dominated:
                result.append(v1)

        self.store[key] = result

# Usage
store_a = DistributedKVStore('A', ['A', 'B'])
store_b = DistributedKVStore('B', ['A', 'B'])

# A writes
store_a.put('user:1', {'name': 'Alice', 'age': 30})

# B writes concurrently (before seeing A's write)
store_b.put('user:1', {'name': 'Alice', 'age': 31})

# Now A and B sync - conflict detected!
# Both versions present with concurrent vector clocks
```

### Application 2: Causal Delivery

```python
class CausalBroadcast:
    """Ensure messages delivered in causal order"""

    def __init__(self, node_id, nodes):
        self.node_id = node_id
        self.vc = VectorClock(node_id, nodes)
        self.pending = []  # Messages waiting for causal delivery
        self.delivered = []

    def broadcast(self, message):
        """Broadcast message with vector clock"""
        clock = self.vc.send_event()
        return (message, clock)

    def receive(self, message, sender_clock):
        """Receive message, deliver when causal order satisfied"""
        self.pending.append((message, sender_clock))
        self._try_deliver()

    def _try_deliver(self):
        """Try to deliver pending messages in causal order"""
        delivered_any = True

        while delivered_any:
            delivered_any = False

            for msg, msg_clock in self.pending[:]:
                if self._can_deliver(msg_clock):
                    self.pending.remove((msg, msg_clock))
                    self._deliver(msg, msg_clock)
                    delivered_any = True

    def _can_deliver(self, msg_clock):
        """Check if message can be delivered"""
        # Can deliver if all causally preceding messages delivered
        for node, count in msg_clock.items():
            if node == self.node_id:
                continue  # Skip own clock
            if count > self.vc.clock.get(node, 0):
                return False  # Missing causal predecessor
        return True

    def _deliver(self, message, sender_clock):
        """Deliver message and update vector clock"""
        self.vc.receive_event(sender_clock)
        self.delivered.append(message)
        print(f"Delivered: {message}")
```

---

## Optimizations

### Problem: Vector Clock Size

**Growth**: O(number of processes)

**Solutions**:

1. **Pruning**: Remove inactive processes
```python
def prune_clock(self, min_activity_time):
    """Remove processes inactive for too long"""
    current_time = time.time()
    self.clock = {
        node: count for node, count in self.clock.items()
        if self.last_activity.get(node, 0) > current_time - min_activity_time
    }
```

2. **Use Dotted Version Vectors** (see related skill)

3. **Dynamic process IDs**: Short-lived IDs instead of permanent process IDs

---

## Comparison with Alternatives

| Mechanism | Size | Detects Concurrency | Complexity |
|-----------|------|-------------------|------------|
| **Timestamps** | O(1) | ❌ No | Simple |
| **Lamport Clocks** | O(1) | ❌ No | Simple |
| **Vector Clocks** | O(N) | ✅ Yes | Medium |
| **Dotted Version Vectors** | O(active writers) | ✅ Yes | Medium |
| **Interval Tree Clocks** | O(log N) | ✅ Yes | Complex |

---

## Testing Vector Clocks

```python
import unittest

class TestVectorClock(unittest.TestCase):
    def test_happens_before(self):
        """Test happens-before relationship"""
        vc = VectorClock('A', ['A', 'B'])

        vc1 = {'A': 1, 'B': 0}
        vc2 = {'A': 2, 'B': 1}

        self.assertTrue(vc.happens_before(vc1, vc2))
        self.assertFalse(vc.happens_before(vc2, vc1))

    def test_concurrent(self):
        """Test concurrent events"""
        vc = VectorClock('A', ['A', 'B'])

        vc1 = {'A': 1, 'B': 0}
        vc2 = {'A': 0, 'B': 1}

        self.assertTrue(vc.concurrent(vc1, vc2))

    def test_message_passing(self):
        """Test vector clock update on message passing"""
        vc_a = VectorClock('A', ['A', 'B'])
        vc_b = VectorClock('B', ['A', 'B'])

        # A sends
        sent_clock = vc_a.send_event()

        # B receives
        vc_b.receive_event(sent_clock)

        # B's clock should reflect A's event
        self.assertEqual(vc_b.clock['A'], 1)
        self.assertEqual(vc_b.clock['B'], 1)
```

---

## Related Skills

- `distributed-systems-dotted-version-vectors` - Optimized vector clocks
- `distributed-systems-interval-tree-clocks` - Scalable causality tracking
- `distributed-systems-logical-clocks` - Lamport clocks
- `distributed-systems-crdt-fundamentals` - Using clocks in CRDTs
- `distributed-systems-eventual-consistency` - Consistency models

---

**Last Updated**: 2025-10-27
