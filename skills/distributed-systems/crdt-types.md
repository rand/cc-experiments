---
name: distributed-systems-crdt-types
description: Specific CRDT implementations including LWW-Register, OR-Set, RGA, and collaborative text editing CRDTs
---

# CRDT Types

**Scope**: Specific CRDT implementations, LWW, OR-Set, sequences, collaborative editing
**Lines**: ~370
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Implementing specific CRDT data structures
- Building collaborative editing features
- Choosing appropriate CRDT for use case
- Understanding Yjs, Automerge internals
- Implementing distributed sets
- Building real-time synchronization
- Handling complex conflict resolution
- Optimizing CRDT performance

## Register CRDTs

### LWW-Register (Last-Write-Wins)

**Approach**: Use timestamps to resolve conflicts (latest wins)

```python
import time

class LWWRegister:
    """Last-Write-Wins Register"""

    def __init__(self, replica_id):
        self.replica_id = replica_id
        self.value = None
        self.timestamp = 0

    def set(self, value):
        """Set value with current timestamp"""
        self.value = value
        self.timestamp = time.time()

    def merge(self, other):
        """Merge with another replica (latest timestamp wins)"""
        result = LWWRegister(self.replica_id)

        if other.timestamp > self.timestamp:
            result.value = other.value
            result.timestamp = other.timestamp
        else:
            result.value = self.value
            result.timestamp = self.timestamp

        return result

# Usage
r1 = LWWRegister('A')
r2 = LWWRegister('B')

r1.set('value1')  # timestamp: t1
time.sleep(0.001)
r2.set('value2')  # timestamp: t2 (t2 > t1)

merged = r1.merge(r2)
print(merged.value)  # 'value2' (latest)
```

**Problem**: Concurrent writes may be lost
```
Replica A: set('A') at t=100.001
Replica B: set('B') at t=100.002

Result: 'B' wins (but 'A' is lost!)
```

### MV-Register (Multi-Value Register)

**Approach**: Keep all concurrent values, resolve externally

```python
from typing import Set, Tuple

class MVRegister:
    """Multi-Value Register (keeps concurrent values)"""

    def __init__(self, replica_id):
        self.replica_id = replica_id
        self.values = set()  # Set of (value, vector_clock) tuples

    def set(self, value, vector_clock):
        """Set value with vector clock"""
        # Remove dominated values
        self.values = {
            (v, vc) for (v, vc) in self.values
            if not self._dominates(vector_clock, vc)
        }
        self.values.add((value, vector_clock.copy()))

    def get(self):
        """Get all concurrent values"""
        return {v for (v, vc) in self.values}

    def merge(self, other):
        """Merge preserving concurrent values"""
        result = MVRegister(self.replica_id)
        result.values = self.values | other.values

        # Remove dominated values
        result.values = {
            (v1, vc1) for (v1, vc1) in result.values
            if not any(
                self._dominates(vc2, vc1) and (v1, vc1) != (v2, vc2)
                for (v2, vc2) in result.values
            )
        }

        return result

    def _dominates(self, vc1, vc2):
        """Check if vc1 dominates vc2"""
        return all(vc1.get(k, 0) >= vc2.get(k, 0) for k in vc2) and vc1 != vc2
```

---

## Set CRDTs

### OR-Set (Observed-Remove Set)

**Approach**: Each element tagged with unique ID, can be re-added after remove

```python
import uuid
from typing import Set, Tuple

class ORSet:
    """Observed-Remove Set"""

    def __init__(self):
        self.elements = {}  # element → set of unique IDs

    def add(self, element):
        """Add element with unique tag"""
        tag = str(uuid.uuid4())
        if element not in self.elements:
            self.elements[element] = set()
        self.elements[element].add(tag)
        return tag  # Return for tracking

    def remove(self, element):
        """Remove element (all current tags)"""
        if element in self.elements:
            removed_tags = self.elements[element].copy()
            del self.elements[element]
            return removed_tags
        return set()

    def lookup(self, element):
        """Check if element exists"""
        return element in self.elements and len(self.elements[element]) > 0

    def merge(self, other):
        """Merge two OR-Sets"""
        result = ORSet()

        # Union of all elements and their tags
        all_elements = set(self.elements.keys()) | set(other.elements.keys())

        for elem in all_elements:
            my_tags = self.elements.get(elem, set())
            other_tags = other.elements.get(elem, set())
            combined_tags = my_tags | other_tags

            if combined_tags:
                result.elements[elem] = combined_tags

        return result

# Usage
set1 = ORSet()
set2 = ORSet()

set1.add('apple')
set2.add('banana')
set1.remove('apple')
set1.add('apple')  # Can re-add after remove!

merged = set1.merge(set2)
print(merged.lookup('apple'))   # True (re-added)
print(merged.lookup('banana'))  # True
```

**Key insight**: Remove only affects observed adds (hence "Observed-Remove")

---

## Sequence CRDTs

### RGA (Replicated Growable Array)

**Approach**: Each element has unique ID and knows its predecessor

```python
import uuid
from typing import Optional

class RGANode:
    def __init__(self, value, timestamp, replica_id):
        self.id = (timestamp, replica_id, str(uuid.uuid4()))
        self.value = value
        self.prev_id = None
        self.tombstone = False  # For deletion

class RGA:
    """Replicated Growable Array"""

    def __init__(self, replica_id):
        self.replica_id = replica_id
        self.nodes = {}  # id → RGANode
        self.root_id = None
        self.timestamp = 0

    def insert_after(self, prev_id, value):
        """Insert value after given position"""
        self.timestamp += 1
        node = RGANode(value, self.timestamp, self.replica_id)
        node.prev_id = prev_id
        self.nodes[node.id] = node
        return node.id

    def insert_at_start(self, value):
        """Insert at beginning"""
        self.timestamp += 1
        node = RGANode(value, self.timestamp, self.replica_id)
        node.prev_id = None
        self.root_id = node.id
        self.nodes[node.id] = node
        return node.id

    def delete(self, node_id):
        """Delete by marking as tombstone"""
        if node_id in self.nodes:
            self.nodes[node_id].tombstone = True

    def to_list(self):
        """Convert to list (excluding tombstones)"""
        if not self.nodes:
            return []

        # Build list by following prev_id links
        result = []
        current_id = self.root_id

        while current_id:
            node = self.nodes[current_id]
            if not node.tombstone:
                result.append(node.value)

            # Find next node (node where prev_id == current_id)
            next_nodes = [
                (nid, n) for nid, n in self.nodes.items()
                if n.prev_id == current_id and not n.tombstone
            ]

            if next_nodes:
                # Resolve conflicts by ID ordering
                next_nodes.sort(key=lambda x: x[1].id)
                current_id = next_nodes[0][0]
            else:
                break

        return result

    def merge(self, other):
        """Merge with another RGA"""
        result = RGA(self.replica_id)
        result.nodes = {**self.nodes, **other.nodes}  # Union of nodes
        result.timestamp = max(self.timestamp, other.timestamp)
        return result
```

---

## Collaborative Text Editing

### Logoot CRDT

**Approach**: Assign each character a unique position identifier

```python
import random

class LogootPosition:
    """Position identifier between existing positions"""

    def __init__(self, identifiers):
        self.identifiers = identifiers  # List of (int, replica_id)

    def __lt__(self, other):
        return self.identifiers < other.identifiers

    def __eq__(self, other):
        return self.identifiers == other.identifiers

    @staticmethod
    def between(pos1, pos2, replica_id):
        """Generate position between pos1 and pos2"""
        # Simplified: add random component
        new_id = pos1.identifiers + [(random.randint(1, 100), replica_id)]
        return LogootPosition(new_id)

class LogootChar:
    def __init__(self, position, char):
        self.position = position
        self.char = char

class LogootDocument:
    """Collaborative text editor using Logoot"""

    def __init__(self, replica_id):
        self.replica_id = replica_id
        self.chars = []  # Sorted list of LogootChar

        # Sentinels
        self.begin = LogootPosition([(0, 'BEGIN')])
        self.end = LogootPosition([(float('inf'), 'END')])

    def insert(self, index, char):
        """Insert character at index"""
        # Get positions before and after insertion point
        pos_before = self.chars[index - 1].position if index > 0 else self.begin
        pos_after = self.chars[index].position if index < len(self.chars) else self.end

        # Generate position between them
        new_pos = LogootPosition.between(pos_before, pos_after, self.replica_id)

        # Insert character
        logoot_char = LogootChar(new_pos, char)
        self.chars.insert(index, logoot_char)
        self.chars.sort(key=lambda c: c.position)  # Maintain sorted order

        return logoot_char

    def delete(self, index):
        """Delete character at index"""
        if 0 <= index < len(self.chars):
            deleted = self.chars.pop(index)
            return deleted

    def to_string(self):
        """Get document as string"""
        return ''.join(c.char for c in self.chars)

    def merge(self, other):
        """Merge with another document"""
        result = LogootDocument(self.replica_id)
        result.chars = sorted(
            self.chars + other.chars,
            key=lambda c: c.position
        )
        return result
```

### Yjs-like CRDT

**Simplified Yjs approach**:
```python
class YjsChar:
    def __init__(self, char, clock, client_id):
        self.char = char
        self.id = (client_id, clock)
        self.left_id = None  # ID of left neighbor
        self.right_id = None  # ID of right neighbor
        self.deleted = False

class YjsText:
    """Simplified Yjs-like text CRDT"""

    def __init__(self, client_id):
        self.client_id = client_id
        self.clock = 0
        self.items = {}  # id → YjsChar

    def insert(self, index, char):
        """Insert character at index"""
        self.clock += 1

        items_list = self._to_list()

        yjs_char = YjsChar(char, self.clock, self.client_id)

        if index > 0:
            yjs_char.left_id = items_list[index - 1].id
        if index < len(items_list):
            yjs_char.right_id = items_list[index].id

        self.items[yjs_char.id] = yjs_char
        return yjs_char.id

    def delete(self, index):
        """Delete character at index"""
        items_list = self._to_list()
        if 0 <= index < len(items_list):
            items_list[index].deleted = True

    def _to_list(self):
        """Reconstruct ordered list"""
        # Build from left/right relationships
        result = []
        for item in self.items.values():
            if not item.deleted:
                result.append(item)
        # Sort by causal relationships and IDs
        result.sort(key=lambda x: x.id)
        return result

    def to_string(self):
        return ''.join(item.char for item in self._to_list())
```

---

## Map CRDTs

### OR-Map (Observed-Remove Map)

```python
class ORMap:
    """Map with OR-Set semantics for keys"""

    def __init__(self):
        self.keys = ORSet()  # Keys as OR-Set
        self.values = {}     # key → CRDT value

    def set(self, key, value_crdt):
        """Set key to CRDT value"""
        self.keys.add(key)
        if key not in self.values:
            self.values[key] = value_crdt
        else:
            # Merge with existing value
            self.values[key] = self.values[key].merge(value_crdt)

    def remove(self, key):
        """Remove key"""
        self.keys.remove(key)
        # Keep value for potential re-add

    def get(self, key):
        """Get value for key"""
        if self.keys.lookup(key):
            return self.values.get(key)
        return None

    def merge(self, other):
        """Merge two OR-Maps"""
        result = ORMap()
        result.keys = self.keys.merge(other.keys)

        # Merge values for all keys
        all_keys = set(self.values.keys()) | set(other.values.keys())
        for key in all_keys:
            if key in self.values and key in other.values:
                result.values[key] = self.values[key].merge(other.values[key])
            elif key in self.values:
                result.values[key] = self.values[key]
            else:
                result.values[key] = other.values[key]

        return result
```

---

## Performance Optimization

### Tombstone Garbage Collection

**Problem**: Deleted items accumulate as tombstones

**Solution**: Periodic GC when safe

```python
class RGAWithGC(RGA):
    def garbage_collect(self, min_vector_clock):
        """Remove tombstones that all replicas have seen"""
        self.nodes = {
            nid: node for nid, node in self.nodes.items()
            if not node.tombstone or not self._all_replicas_seen(node, min_vector_clock)
        }

    def _all_replicas_seen(self, node, min_vc):
        """Check if all replicas have seen this deletion"""
        node_time, node_replica, _ = node.id
        return min_vc.get(node_replica, 0) >= node_time
```

### Compression

**Approach**: Merge consecutive inserts from same replica

```python
class CompressedRGA:
    """RGA with run-length compression"""

    def __init__(self, replica_id):
        self.replica_id = replica_id
        self.runs = []  # List of (values, id, prev_id)

    def insert_run(self, prev_id, values):
        """Insert multiple values as single run"""
        run_id = self._generate_id()
        self.runs.append((values, run_id, prev_id))
        return run_id
```

---

## Choosing the Right CRDT

| Use Case | CRDT Type | Why |
|----------|-----------|-----|
| Configuration value | LWW-Register | Simple, last write wins acceptable |
| Feature flags | OR-Set | Enables/disables need conflict handling |
| Shopping cart | OR-Set or OR-Map | Items can be added/removed by multiple devices |
| Like counter | PN-Counter | Increments/decrements commute |
| Collaborative text | Logoot or Yjs | Preserves user intent in concurrent edits |
| Chat messages | RGA | Insertion order matters |
| User presence | LWW-Register or G-Set | Recent status most relevant |

---

## Related Skills

- `distributed-systems-crdt-fundamentals` - CRDT basics
- `distributed-systems-vector-clocks` - Causality tracking
- `distributed-systems-conflict-resolution` - Conflict handling
- `distributed-systems-eventual-consistency` - Consistency models

---

**Last Updated**: 2025-10-27
