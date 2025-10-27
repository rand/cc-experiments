---
name: distributed-systems-dotted-version-vectors
description: Dotted version vectors for efficient sibling management, compact causality tracking, reducing metadata overhead compared to pure vector clocks
---

# Dotted Version Vectors

**Scope**: Dotted version vectors (DVV), sibling management, compact causality, optimized vector clocks
**Lines**: ~380
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building Riak-like key-value stores
- Managing concurrent siblings efficiently
- Reducing vector clock metadata overhead
- Implementing optimized causality tracking
- Avoiding false conflicts in distributed databases
- Understanding Riak's sibling resolution
- Tracking only active writers
- Optimizing storage for versioned data

## Core Concepts

### The Problem with Vector Clocks

**Vector clocks grow unbounded**:
```
3 replicas write to same key:
Version 1: {A:1, B:0, C:0}
Version 2: {A:1, B:1, C:0}
Version 3: {A:1, B:1, C:1}

After 1000 writes across replicas:
{A:342, B:401, C:257}  ← Metadata grows forever!
```

**False siblings problem**:
```
Client writes via replica A:
Value 1: {A:1, B:0}  "Alice"

Client writes again via A:
Value 2: {A:2, B:0}  "Alice Smith"

Vector clocks say: NOT concurrent (A:1 < A:2)
But system treats as siblings because client ID changed!
```

### Dotted Version Vectors Solution

**Key insight**: Separate **event** (dot) from **context** (causal history)

```
DVV = (dot, context)

dot = (node_id, counter)        ← The write event
context = {node → counter}       ← Causal history seen
```

**Properties**:
1. **Compact**: Only track active writes, not full history
2. **Precise**: Distinguish updates from concurrent writes
3. **Efficient**: Prune dominated versions automatically

---

## Algorithm

### Data Structure

```python
from typing import Dict, Tuple, Set

class Dot:
    """Single event identifier"""
    def __init__(self, node_id: str, counter: int):
        self.node_id = node_id
        self.counter = counter

    def __eq__(self, other):
        return self.node_id == other.node_id and self.counter == other.counter

    def __hash__(self):
        return hash((self.node_id, self.counter))

    def __repr__(self):
        return f"({self.node_id}:{self.counter})"

class DottedVersionVector:
    """Dotted version vector for causality tracking"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.context = {}  # node_id → max_counter seen

    def new_dot(self) -> Dot:
        """Create new dot for a write event"""
        current = self.context.get(self.node_id, 0)
        new_counter = current + 1
        self.context[self.node_id] = new_counter
        return Dot(self.node_id, new_counter)

    def update_context(self, other_context: Dict[str, int]):
        """Merge contexts (element-wise max)"""
        for node, counter in other_context.items():
            self.context[node] = max(self.context.get(node, 0), counter)

    def dot_in_context(self, dot: Dot) -> bool:
        """Check if dot is in causal history"""
        return self.context.get(dot.node_id, 0) >= dot.counter

    def is_concurrent(self, dot1: Dot, dot2: Dot, context1: Dict[str, int],
                     context2: Dict[str, int]) -> bool:
        """Check if two dotted values are concurrent"""
        # dot1 concurrent with dot2 if:
        # - dot1 not in context2, AND
        # - dot2 not in context1
        dot1_seen = context2.get(dot1.node_id, 0) >= dot1.counter
        dot2_seen = context1.get(dot2.node_id, 0) >= dot2.counter
        return not dot1_seen and not dot2_seen
```

### Versioned Value

```python
class DottedValue:
    """Value with its causal dot"""
    def __init__(self, value, dot: Dot, context: Dict[str, int]):
        self.value = value
        self.dot = dot
        self.context = context.copy()

    def __repr__(self):
        return f"DottedValue({self.value}, {self.dot}, ctx={self.context})"

class DottedVersionStore:
    """Key-value store using dotted version vectors"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.dvv = DottedVersionVector(node_id)
        self.store = {}  # key → set of DottedValue

    def write(self, key: str, value, context: Dict[str, int] = None):
        """Write value with new dot"""
        # Update context with client's causal knowledge
        if context:
            self.dvv.update_context(context)

        # Create new dot for this write
        dot = self.dvv.new_dot()

        # Create dotted value
        dotted = DottedValue(value, dot, self.dvv.context)

        if key not in self.store:
            self.store[key] = {dotted}
        else:
            # Remove values dominated by this write
            self.store[key] = {
                v for v in self.store[key]
                if not self._is_dominated(v.dot, v.context, dot, dotted.context)
            }
            self.store[key].add(dotted)

        return dotted

    def read(self, key: str):
        """Read value(s) and context"""
        if key not in self.store:
            return [], {}

        values = list(self.store[key])

        # Compute merged context from all siblings
        merged_context = {}
        for v in values:
            for node, counter in v.context.items():
                merged_context[node] = max(merged_context.get(node, 0), counter)

        return values, merged_context

    def _is_dominated(self, dot1: Dot, ctx1: Dict[str, int],
                     dot2: Dot, ctx2: Dict[str, int]) -> bool:
        """Check if (dot1, ctx1) is dominated by (dot2, ctx2)"""
        # dot1 dominated if dot1 is in ctx2's causal past
        return ctx2.get(dot1.node_id, 0) >= dot1.counter

    def merge(self, key: str, remote_values: Set[DottedValue]):
        """Merge values from replica"""
        if key not in self.store:
            self.store[key] = remote_values
            # Update context
            for v in remote_values:
                self.dvv.update_context(v.context)
            return

        # Merge local and remote
        all_values = self.store[key] | remote_values

        # Remove dominated versions
        result = set()
        for v1 in all_values:
            dominated = False
            for v2 in all_values:
                if v1 != v2 and self._is_dominated(v1.dot, v1.context, v2.dot, v2.context):
                    dominated = True
                    break
            if not dominated:
                result.add(v1)

        self.store[key] = result

        # Update context from all values
        for v in result:
            self.dvv.update_context(v.context)
```

---

## Practical Example: Riak-Style KV Store

### Complete Implementation

```python
class RiakStyleKVStore:
    """Riak-inspired key-value store with DVV"""

    def __init__(self, node_id: str, replicas: list):
        self.node_id = node_id
        self.replicas = replicas
        self.store = DottedVersionStore(node_id)

    def put(self, key: str, value, context: Dict[str, int] = None):
        """
        Put value with optional causal context

        Args:
            key: The key to write
            value: The value to write
            context: Causal context from previous read (for updates)

        Returns:
            DottedValue with dot and updated context
        """
        dotted = self.store.write(key, value, context)

        # In real system: replicate to other nodes
        # self._replicate_to_nodes(key, dotted)

        return dotted

    def get(self, key: str):
        """
        Get value(s) for key

        Returns:
            (values, context) tuple
            - If no conflict: single value
            - If conflict: list of siblings
            - context: causal context for next write
        """
        values, context = self.store.read(key)

        if not values:
            return None, context
        elif len(values) == 1:
            return values[0].value, context
        else:
            # Multiple siblings - client must resolve
            return [v.value for v in values], context

    def resolve_siblings(self, key: str, resolved_value, context: Dict[str, int]):
        """
        Resolve sibling conflict by writing resolution

        Args:
            key: The key with siblings
            resolved_value: The resolved value
            context: Context from get() that returned siblings
        """
        return self.put(key, resolved_value, context)

# Usage Example
store_a = RiakStyleKVStore('A', ['A', 'B', 'C'])
store_b = RiakStyleKVStore('B', ['A', 'B', 'C'])

# Write on replica A
dotted1 = store_a.put('user:1', {'name': 'Alice', 'age': 30})
print(f"Write 1: {dotted1}")
# Output: DottedValue({'name': 'Alice', 'age': 30}, (A:1), ctx={'A': 1})

# Read and update on replica A
value, context = store_a.get('user:1')
dotted2 = store_a.put('user:1', {'name': 'Alice', 'age': 31}, context)
print(f"Update: {dotted2}")
# Output: DottedValue({'name': 'Alice', 'age': 31}, (A:2), ctx={'A': 2})

# Concurrent write on replica B (without seeing A's updates)
dotted3 = store_b.put('user:1', {'name': 'Alice', 'email': 'alice@example.com'})
print(f"Concurrent write: {dotted3}")
# Output: DottedValue({...}, (B:1), ctx={'B': 1})

# Merge at replica A
store_a.store.merge('user:1', {dotted3})

# Now reading shows siblings
siblings, ctx = store_a.get('user:1')
print(f"Siblings detected: {siblings}")
# Output: [{'name': 'Alice', 'age': 31}, {'name': 'Alice', 'email': 'alice@example.com'}]

# Resolve conflict
merged = {'name': 'Alice', 'age': 31, 'email': 'alice@example.com'}
resolved = store_a.resolve_siblings('user:1', merged, ctx)
print(f"Resolved: {resolved}")
# Output: DottedValue({...}, (A:3), ctx={'A': 3, 'B': 1})
```

---

## Comparison: Vector Clocks vs DVV

### Memory Overhead

```python
# Vector Clock approach
class VectorClockedValue:
    def __init__(self, value, vc):
        self.value = value
        self.vector_clock = vc  # Full vector: {A:342, B:401, C:257, ...}

# Dotted Version Vector approach
class DottedValue:
    def __init__(self, value, dot, context):
        self.value = value
        self.dot = dot           # Single dot: (A:343)
        self.context = context   # Pruned context: {A:342, B:401, C:257}

# Example after 1000 writes:
# VC: Every value carries full vector (3 nodes × 8 bytes × 1000 values = 24KB)
# DVV: Each value carries 1 dot + shared context (8 bytes + 24 bytes = 32 bytes)
# Savings: ~99% metadata reduction!
```

### False Siblings

```python
# Vector Clock: False siblings from client ID changes
vc_store = VectorClockStore('A', ['A', 'B'])

# Client 1 writes via A
vc_store.put('key', 'v1')  # VC: {A:1, B:0}

# Same client writes again via A (new client connection)
vc_store.put('key', 'v2')  # VC: {A:2, B:0}

# Result: May create siblings even though v2 supersedes v1!

# DVV: Correct handling
dvv_store = DottedVersionStore('A')

# Client writes
dotted1 = dvv_store.write('key', 'v1')  # Dot: (A:1), ctx: {A:1}

# Client updates with context
dotted2 = dvv_store.write('key', 'v2', context={'A': 1})  # Dot: (A:2), ctx: {A:2}

# Result: v1 correctly pruned, no false siblings
```

---

## Real-World Use Case: Riak

**Riak's DVV implementation**:

```python
class RiakDVV:
    """Simplified Riak DVV logic"""

    @staticmethod
    def reconcile(local_values: Set[DottedValue],
                  remote_values: Set[DottedValue]) -> Set[DottedValue]:
        """Riak's sibling reconciliation"""
        all_values = local_values | remote_values

        # Compute global context
        global_context = {}
        for v in all_values:
            for node, counter in v.context.items():
                global_context[node] = max(global_context.get(node, 0), counter)

        # Keep only values not in global context
        survivors = set()
        for v in all_values:
            # Keep if dot not dominated by global context
            if global_context.get(v.dot.node_id, 0) < v.dot.counter:
                survivors.add(v)
            # Update context to global
            v.context = global_context.copy()

        return survivors if survivors else {max(all_values, key=lambda v: (v.dot.node_id, v.dot.counter))}

# Riak's anti-entropy (read repair)
def read_repair(replicas: list, key: str) -> DottedValue:
    """Fetch from multiple replicas and repair inconsistencies"""
    all_values = set()
    for replica in replicas:
        values, _ = replica.read(key)
        all_values.update(values)

    # Reconcile
    reconciled = RiakDVV.reconcile(all_values, set())

    # Write reconciled values back to out-of-date replicas
    for replica in replicas:
        replica.store.store[key] = reconciled

    return reconciled
```

---

## Performance Characteristics

| Aspect | Vector Clocks | Dotted Version Vectors |
|--------|--------------|----------------------|
| **Write latency** | O(1) | O(1) |
| **Read latency** | O(siblings) | O(siblings) |
| **Metadata size** | O(N × writes) | O(N) + dot |
| **Sibling detection** | Accurate | More accurate |
| **Pruning** | Manual/periodic | Automatic |
| **False siblings** | Common | Rare |
| **Memory** | High (unbounded) | Low (bounded) |

**Space complexity**:
- Vector clock: O(N) per version, grows with writes
- DVV: O(N) shared context + O(1) per version

---

## Advanced: Causal Stability

```python
class CausallyStableDVV:
    """DVV with causal stability detection"""

    def __init__(self, node_id: str):
        self.dvv = DottedVersionVector(node_id)
        self.stable_context = {}  # Causally stable events

    def mark_stable(self, node_id: str, counter: int):
        """Mark events up to counter as stable"""
        self.stable_context[node_id] = counter

    def prune_stable(self, key: str):
        """Prune values dominated by stable context"""
        if key not in self.store:
            return

        self.store[key] = {
            v for v in self.store[key]
            if self.stable_context.get(v.dot.node_id, 0) < v.dot.counter
        }

    def compute_stability(self, replicas: list) -> Dict[str, int]:
        """Compute causally stable frontier across replicas"""
        # Stable = min counter across all replicas
        stability = {}
        for node_id in self.dvv.context.keys():
            min_counter = min(
                r.dvv.context.get(node_id, 0) for r in replicas
            )
            stability[node_id] = min_counter
        return stability
```

---

## Testing DVV

```python
import unittest

class TestDottedVersionVector(unittest.TestCase):
    def test_update_supersedes(self):
        """Test that update with context supersedes previous"""
        store = DottedVersionStore('A')

        # Write
        v1 = store.write('key', 'value1')

        # Update with context
        v2 = store.write('key', 'value2', context=v1.context)

        # Only v2 should remain
        values, _ = store.read('key')
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0].value, 'value2')

    def test_concurrent_creates_siblings(self):
        """Test that concurrent writes create siblings"""
        store_a = DottedVersionStore('A')
        store_b = DottedVersionStore('B')

        # Concurrent writes
        v1 = store_a.write('key', 'value_a')
        v2 = store_b.write('key', 'value_b')

        # Merge at A
        store_a.merge('key', {v2})

        # Should have siblings
        values, _ = store_a.read('key')
        self.assertEqual(len(values), 2)

    def test_no_false_siblings(self):
        """Test that sequential updates don't create false siblings"""
        store = DottedVersionStore('A')

        # First write
        v1 = store.write('key', 'v1')

        # Update with same key (simulating client getting context)
        v2 = store.write('key', 'v2', context=v1.context)

        # Should only have v2
        values, _ = store.read('key')
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0].value, 'v2')
```

---

## Related Skills

- `distributed-systems-vector-clocks` - Foundation causality tracking
- `distributed-systems-interval-tree-clocks` - Dynamic process IDs
- `distributed-systems-conflict-resolution` - Handling siblings
- `distributed-systems-eventual-consistency` - Consistency models
- `distributed-systems-crdt-fundamentals` - Convergent data structures

---

**Last Updated**: 2025-10-27
