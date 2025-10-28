# CRDT Fundamentals Reference

## Table of Contents
1. [Introduction](#introduction)
2. [Theoretical Foundation](#theoretical-foundation)
3. [Operation-Based CRDTs (CmRDT)](#operation-based-crdts-cmrdt)
4. [State-Based CRDTs (CvRDT)](#state-based-crdts-cvrdt)
5. [Sequence CRDTs](#sequence-crdts)
6. [Map and Composite CRDTs](#map-and-composite-crdts)
7. [Conflict Resolution Semantics](#conflict-resolution-semantics)
8. [CRDT Implementations](#crdt-implementations)
9. [CAP Theorem and CRDT Positioning](#cap-theorem-and-crdt-positioning)
10. [Performance Characteristics](#performance-characteristics)
11. [Design Patterns](#design-patterns)
12. [Testing and Verification](#testing-and-verification)

---

## Introduction

### What are CRDTs?

Conflict-free Replicated Data Types (CRDTs) are data structures that enable distributed systems to achieve **strong eventual consistency** without requiring coordination between replicas. They guarantee that replicas that have received the same set of updates will converge to the same state, regardless of the order in which updates were applied.

### Key Properties

1. **Strong Eventual Consistency**: All replicas that have delivered the same updates eventually reach the same state
2. **Commutativity**: Operations can be applied in any order
3. **Associativity**: Grouping of operations doesn't affect the final result
4. **Idempotency**: Applying the same operation multiple times has the same effect as applying it once

### CRDT Categories

**State-based CRDTs (CvRDT)**:
- Replicas send complete state
- Merge function combines states
- Requires idempotent, commutative, associative merge
- Higher bandwidth, simpler implementation

**Operation-based CRDTs (CmRDT)**:
- Replicas send operations
- Operations must commute
- Requires reliable delivery exactly once
- Lower bandwidth, more complex delivery guarantees

---

## Theoretical Foundation

### Strong Eventual Consistency (SEC)

**Definition**: A system provides strong eventual consistency if:
1. **Eventual delivery**: Every update delivered to one replica is eventually delivered to all replicas
2. **Convergence**: Replicas that have delivered the same updates have equivalent state
3. **Termination**: All methods terminate

**Formal Definition**:
```
∀ replicas r1, r2:
  delivered(r1) = delivered(r2) ⟹ state(r1) = state(r2)
```

### Commutativity

Operations must commute for CRDTs to work correctly.

**Commutativity Requirement**:
```
op1 ∘ op2 = op2 ∘ op1
```

**Example**: Addition is commutative
```
counter + 5 + 3 = counter + 3 + 5 = counter + 8
```

**Counter-example**: Subtraction is not commutative
```
counter - 5 - 3 ≠ counter - 3 - 5
```

### Associativity

Grouping of operations doesn't matter.

```
(op1 ∘ op2) ∘ op3 = op1 ∘ (op2 ∘ op3)
```

### Idempotency

Applying the same operation multiple times yields the same result.

```
op ∘ op = op
```

### Semilattice Structure

State-based CRDTs form a **join-semilattice**:
- Partial order ≤ on states
- Join operation ⊔ (merge)
- Properties:
  - **Commutativity**: s1 ⊔ s2 = s2 ⊔ s1
  - **Associativity**: (s1 ⊔ s2) ⊔ s3 = s1 ⊔ (s2 ⊔ s3)
  - **Idempotency**: s ⊔ s = s

**Monotonicity**: State only grows (or stays the same) under merge
```
s1 ≤ s1 ⊔ s2
```

---

## Operation-Based CRDTs (CmRDT)

### G-Counter (Grow-only Counter)

**Purpose**: Monotonically increasing counter

**State**: Array of integers, one per replica
```
payload = integer[n]  // n = number of replicas
```

**Operations**:
```python
def increment(replica_id):
    payload[replica_id] += 1
    broadcast_op("increment", replica_id)

def value():
    return sum(payload)

def merge_op(op, replica_id):
    if op == "increment":
        payload[replica_id] += 1
```

**Properties**:
- Operations commute: increment operations can be applied in any order
- Memory: O(n) where n = number of replicas
- Query: O(n) to compute sum

**Example**:
```
Replica A: [5, 0, 0]  (A incremented 5 times)
Replica B: [0, 3, 0]  (B incremented 3 times)
Replica C: [0, 0, 2]  (C incremented 2 times)

After merge: [5, 3, 2]
Value: 5 + 3 + 2 = 10
```

### PN-Counter (Positive-Negative Counter)

**Purpose**: Counter that can increment and decrement

**State**: Two G-Counters (positive and negative)
```python
payload = {
    "P": GCounter(),  # increments
    "N": GCounter()   # decrements
}
```

**Operations**:
```python
def increment(replica_id):
    payload["P"].increment(replica_id)
    broadcast_op("increment", replica_id)

def decrement(replica_id):
    payload["N"].increment(replica_id)
    broadcast_op("decrement", replica_id)

def value():
    return payload["P"].value() - payload["N"].value()

def merge(other):
    payload["P"].merge(other.payload["P"])
    payload["N"].merge(other.payload["N"])
```

**Properties**:
- Memory: O(2n)
- Value can be negative
- All operations commute

**Example**:
```
Replica A: P=[3,0], N=[1,0]  → value = 3-1 = 2
Replica B: P=[0,2], N=[0,3]  → value = 2-3 = -1

After merge: P=[3,2], N=[1,3] → value = 5-4 = 1
```

### G-Set (Grow-only Set)

**Purpose**: Set that only supports adding elements

**State**: Set of elements
```python
payload = set()
```

**Operations**:
```python
def add(element):
    payload.add(element)
    broadcast_op("add", element)

def contains(element):
    return element in payload

def merge(other):
    payload.update(other.payload)
```

**Properties**:
- Operations commute: add(a) ∘ add(b) = add(b) ∘ add(a)
- No remove operation
- Memory: O(m) where m = number of added elements

### 2P-Set (Two-Phase Set)

**Purpose**: Set with add and remove, but elements can only be added once and removed once

**State**: Two G-Sets (added and removed)
```python
payload = {
    "A": set(),  # added elements
    "R": set()   # removed elements
}
```

**Operations**:
```python
def add(element):
    payload["A"].add(element)
    broadcast_op("add", element)

def remove(element):
    if element in payload["A"]:
        payload["R"].add(element)
        broadcast_op("remove", element)

def contains(element):
    return element in payload["A"] and element not in payload["R"]

def merge(other):
    payload["A"].update(other.payload["A"])
    payload["R"].update(other.payload["R"])
```

**Properties**:
- Once removed, element cannot be re-added
- Bias: removes win (if in both A and R, considered removed)
- Memory: O(2m)

### OR-Set (Observed-Remove Set)

**Purpose**: Set with add and remove, where elements can be added multiple times

**State**: Set of (element, unique_tag) pairs
```python
payload = set()  # set of (element, unique_id) tuples
```

**Operations**:
```python
def add(element, replica_id, timestamp):
    unique_tag = (replica_id, timestamp)
    payload.add((element, unique_tag))
    broadcast_op("add", element, unique_tag)

def remove(element):
    tags_to_remove = {tag for (e, tag) in payload if e == element}
    payload = {(e, tag) for (e, tag) in payload if e != element}
    broadcast_op("remove", element, tags_to_remove)

def contains(element):
    return any(e == element for (e, _) in payload)

def merge(other):
    payload.update(other.payload)
```

**Properties**:
- Can add same element multiple times
- Remove only affects observed adds
- Concurrent add and remove: add wins
- Memory: O(m × k) where k = average adds per element

**Example**:
```
Replica A adds "x": {("x", "A1")}
Replica B adds "x": {("x", "B1")}

After merge: {("x", "A1"), ("x", "B1")}

Replica A removes "x" (observes only A1): {}
Replica B still has: {("x", "B1")}

After merge: {("x", "B1")}  ← B's add wasn't observed by A's remove
```

---

## State-Based CRDTs (CvRDT)

### LWW-Element-Set (Last-Write-Wins Element Set)

**Purpose**: Set where concurrent operations are resolved by timestamp

**State**: Two sets with timestamps
```python
payload = {
    "A": {},  # {element: timestamp}
    "R": {}   # {element: timestamp}
}
```

**Operations**:
```python
def add(element, timestamp):
    payload["A"][element] = max(
        payload["A"].get(element, 0),
        timestamp
    )

def remove(element, timestamp):
    payload["R"][element] = max(
        payload["R"].get(element, 0),
        timestamp
    )

def contains(element):
    add_ts = payload["A"].get(element, 0)
    rem_ts = payload["R"].get(element, 0)
    return add_ts > rem_ts  # bias towards additions

def merge(other):
    for e, ts in other.payload["A"].items():
        payload["A"][e] = max(payload["A"].get(e, 0), ts)
    for e, ts in other.payload["R"].items():
        payload["R"][e] = max(payload["R"].get(e, 0), ts)
```

**Properties**:
- Requires synchronized clocks or logical timestamps
- Bias: additions win on equal timestamps
- Memory: O(m) where m = number of unique elements
- Can lose updates if timestamps collide

**Timestamp Strategies**:
1. **Physical timestamps**: `time.time()` (requires clock sync)
2. **Lamport timestamps**: Logical clock incremented on each operation
3. **Hybrid logical clocks**: Combine physical and logical time

### LWW-Register (Last-Write-Wins Register)

**Purpose**: Single value register where concurrent writes are resolved by timestamp

**State**: Value and timestamp
```python
payload = {
    "value": None,
    "timestamp": 0
}
```

**Operations**:
```python
def set(value, timestamp):
    if timestamp > payload["timestamp"]:
        payload["value"] = value
        payload["timestamp"] = timestamp

def get():
    return payload["value"]

def merge(other):
    if other.payload["timestamp"] > payload["timestamp"]:
        payload["value"] = other.payload["value"]
        payload["timestamp"] = other.payload["timestamp"]
```

**Properties**:
- Simple but can lose concurrent updates
- Last write wins (arbitrary if timestamps equal)
- Memory: O(1)

### MV-Register (Multi-Value Register)

**Purpose**: Register that preserves all concurrent values

**State**: Set of (value, vector_clock) pairs
```python
payload = set()  # {(value, vector_clock)}
```

**Operations**:
```python
def set(value, vector_clock):
    # Remove dominated versions
    payload = {(v, vc) for (v, vc) in payload
               if not vc < vector_clock}
    payload.add((value, vector_clock))

def get():
    return {value for (value, _) in payload}

def merge(other):
    combined = payload | other.payload
    # Remove dominated versions
    result = set()
    for (v1, vc1) in combined:
        dominated = False
        for (v2, vc2) in combined:
            if vc1 < vc2:
                dominated = True
                break
        if not dominated:
            result.add((v1, vc1))
    payload = result
```

**Properties**:
- No data loss on concurrent writes
- Application must resolve conflicts
- Memory: O(c) where c = number of concurrent writes

---

## Sequence CRDTs

### Overview

Sequence CRDTs enable collaborative editing of ordered sequences (text, lists). Key challenge: maintaining order without coordination.

**Requirements**:
1. Insert at position p
2. Delete at position p
3. Concurrent operations converge to same sequence

### RGA (Replicated Growable Array)

**Purpose**: Ordered sequence with insert and delete

**State**: Linked list with unique identifiers
```python
class Node:
    def __init__(self, id, value, timestamp):
        self.id = id              # (replica_id, seq_num)
        self.value = value
        self.timestamp = timestamp
        self.tombstone = False    # deleted but kept for ordering
        self.next = None
```

**Operations**:
```python
def insert(value, after_id, my_id, timestamp):
    new_node = Node(my_id, value, timestamp)
    # Find node with after_id
    prev = find_node(after_id)
    # Insert after prev, maintaining timestamp order for concurrent inserts
    new_node.next = prev.next
    prev.next = new_node

def delete(id):
    node = find_node(id)
    node.tombstone = True  # mark as deleted

def to_string():
    result = []
    node = head.next
    while node:
        if not node.tombstone:
            result.append(node.value)
        node = node.next
    return ''.join(result)
```

**Ordering Rule**:
For concurrent inserts at same position, use timestamp then replica_id:
```python
def compare(id1, ts1, id2, ts2):
    if ts1 != ts2:
        return ts1 > ts2
    return id1 > id2
```

**Properties**:
- Memory: O(n) including tombstones
- Insert/delete: O(n) to find position
- Preserves intention: inserts stay near reference character

**Example**:
```
Initial: ""
A inserts 'a' at 0, ts=1: "a"
B inserts 'b' at 0, ts=2: "ba"  (higher timestamp comes first)
C inserts 'c' at 0, ts=1: "bca" (same ts as 'a', ordered by ID)
```

### WOOT (WithOut Operational Transformation)

**Purpose**: Ordered sequence optimized for string operations

**State**: Sequence of characters with previous/next identifiers
```python
class Char:
    def __init__(self, id, value, prev_id, next_id, visible):
        self.id = id          # (replica_id, clock)
        self.value = value
        self.prev_id = prev_id  # ID of character before
        self.next_id = next_id  # ID of character after
        self.visible = visible  # not deleted
```

**Operations**:
```python
def insert(char, prev_id, next_id):
    # Find subsquence between prev_id and next_id
    subseq = subsequence(prev_id, next_id)
    # Insert in order by ID
    pos = find_insert_position(subseq, char.id)
    sequence.insert(pos, char)

def delete(id):
    char = find_char(id)
    char.visible = False

def integrate(char):
    # Find correct position between prev and next
    prev_pos = position(char.prev_id)
    next_pos = position(char.next_id)
    # Insert maintaining ID order
    insert_between(char, prev_pos, next_pos)
```

**Properties**:
- Maintains causal relationships via prev/next
- No tombstone accumulation if GC implemented
- Insert complexity: O(n) worst case

### LSEQ

**Purpose**: Variable-size identifiers for efficient sequence

**State**: Sequence with hierarchical identifiers
```python
class Element:
    def __init__(self, id_path, value):
        self.id_path = id_path  # List of integers [2, 5, 13, ...]
        self.value = value
        self.deleted = False
```

**Identifier Allocation**:
```python
def allocate_id(prev_id, next_id):
    # Find first position where prev < next
    depth = 0
    while depth < min(len(prev_id), len(next_id)):
        if prev_id[depth] < next_id[depth]:
            break
        depth += 1

    # Allocate new ID between prev and next
    if next_id[depth] - prev_id[depth] > 1:
        # Space available at this depth
        new_val = random.randint(prev_id[depth] + 1, next_id[depth] - 1)
        return prev_id[:depth] + [new_val]
    else:
        # Need to go deeper
        boundary = random.randint(prev_id[depth] + 1, MAX_INT)
        return prev_id[:depth] + [prev_id[depth], boundary]
```

**Properties**:
- Variable-length identifiers
- Adapts to insertion patterns
- Space complexity: O(n log n) expected
- Better than fixed-size identifiers

### Logoot

**Purpose**: Dense space identifiers for sequence

**State**: Ordered list with position identifiers
```python
class Element:
    def __init__(self, position, value):
        self.position = position  # List of (int, replica_id) tuples
        self.value = value
```

**Position Allocation**:
```python
def allocate_position(prev_pos, next_pos, replica_id):
    # Allocate position between prev and next
    # Each position is list of (int, replica_id)

    # Find boundary
    depth = 0
    while depth < len(prev_pos) and depth < len(next_pos):
        if prev_pos[depth] < next_pos[depth]:
            break
        depth += 1

    # Allocate new position
    if depth < len(next_pos) and next_pos[depth][0] - prev_pos[depth][0] > 1:
        new_int = random.randint(prev_pos[depth][0] + 1, next_pos[depth][0] - 1)
        return prev_pos[:depth] + [(new_int, replica_id)]
    else:
        # Extend
        boundary = random.randint(MIN_INT, MAX_INT)
        return prev_pos[:depth+1] + [(boundary, replica_id)]
```

**Properties**:
- Total order on positions
- No interleaving issues
- Position size grows with dense insertions

---

## Map and Composite CRDTs

### OR-Map (Observed-Remove Map)

**Purpose**: Map where keys can be added, updated, and removed

**State**: Map of keys to OR-Sets of (value, unique_tag)
```python
payload = {}  # {key: ORSet()}
```

**Operations**:
```python
def set(key, value, replica_id, timestamp):
    if key not in payload:
        payload[key] = ORSet()
    payload[key].add(value, replica_id, timestamp)

def remove(key):
    if key in payload:
        del payload[key]

def get(key):
    if key in payload:
        return payload[key].value()
    return None

def merge(other):
    all_keys = set(payload.keys()) | set(other.payload.keys())
    for key in all_keys:
        if key in payload and key in other.payload:
            payload[key].merge(other.payload[key])
        elif key in other.payload:
            payload[key] = other.payload[key].copy()
```

**Properties**:
- Per-key CRDT semantics
- Can compose with any CRDT as value
- Memory: O(k × v) where k = keys, v = values per key

### LWW-Map

**Purpose**: Map with last-write-wins semantics

**State**: Map of keys to (value, timestamp)
```python
payload = {}  # {key: (value, timestamp)}
```

**Operations**:
```python
def set(key, value, timestamp):
    current_ts = payload.get(key, (None, 0))[1]
    if timestamp > current_ts:
        payload[key] = (value, timestamp)

def remove(key, timestamp):
    # Use sentinel value or separate tombstone map
    set(key, TOMBSTONE, timestamp)

def get(key):
    if key in payload and payload[key][0] != TOMBSTONE:
        return payload[key][0]
    return None

def merge(other):
    for key, (value, ts) in other.payload.items():
        current_ts = payload.get(key, (None, 0))[1]
        if ts > current_ts:
            payload[key] = (value, ts)
```

### Composite CRDTs

**JSON-like Structure**:
```python
class CompositeRDT:
    def __init__(self):
        self.root = ORMap()

    # JSON structure: {"users": [{"name": "Alice", "age": 30}]}
    # Represented as nested CRDTs:
    # - Root: OR-Map
    # - "users" key: RGA (sequence)
    # - Each element: OR-Map
    # - "name", "age" keys: LWW-Register
```

**Example Implementation**:
```python
def create_user_list():
    root = ORMap()
    users = RGA()

    user1 = ORMap()
    user1.set("name", LWWRegister("Alice"))
    user1.set("age", LWWRegister(30))

    users.insert(user1, 0)
    root.set("users", users)

    return root
```

---

## Conflict Resolution Semantics

### Resolution Strategies

1. **Last-Write-Wins (LWW)**
   - Use timestamp to determine winner
   - Simple but can lose data
   - Suitable for: registers, maps with low contention

2. **Multi-Value (MV)**
   - Keep all concurrent values
   - Application resolves
   - Suitable for: critical data, user-facing conflicts

3. **Add-Wins**
   - On concurrent add/remove, add wins
   - Used in: OR-Set
   - Bias towards growth

4. **Remove-Wins**
   - On concurrent add/remove, remove wins
   - Used in: 2P-Set
   - Bias towards deletion

5. **Semantic Resolution**
   - Application-specific logic
   - Example: Merge text diffs, combine calendars

### Causal Consistency

**Definition**: If operation A causally precedes operation B, all replicas deliver A before B.

**Implementation**: Vector clocks or version vectors
```python
class VectorClock:
    def __init__(self, n_replicas):
        self.clock = [0] * n_replicas

    def increment(self, replica_id):
        self.clock[replica_id] += 1

    def update(self, other):
        for i in range(len(self.clock)):
            self.clock[i] = max(self.clock[i], other.clock[i])

    def __lt__(self, other):
        # self < other if all components ≤ and at least one <
        less = False
        for i in range(len(self.clock)):
            if self.clock[i] > other.clock[i]:
                return False
            if self.clock[i] < other.clock[i]:
                less = True
        return less

    def concurrent(self, other):
        return not (self < other or other < self)
```

### Delta-State CRDTs

**Optimization**: Send only changes (deltas) instead of full state

**Delta-State G-Counter**:
```python
class DeltaGCounter:
    def __init__(self, n_replicas):
        self.state = [0] * n_replicas
        self.delta = [0] * n_replicas

    def increment(self, replica_id):
        self.state[replica_id] += 1
        self.delta[replica_id] += 1

    def get_delta(self):
        d = self.delta[:]
        self.delta = [0] * len(self.delta)
        return d

    def merge_delta(self, delta):
        for i in range(len(self.state)):
            self.state[i] += delta[i]
```

**Benefits**:
- Reduced bandwidth
- Same convergence guarantees
- More complex implementation

---

## CRDT Implementations

### Automerge

**Description**: JavaScript CRDT library for JSON-like data

**Features**:
- Rich data types: maps, lists, text, counters
- Time-travel (history)
- Efficient encoding
- TypeScript support

**Usage**:
```javascript
import * as Automerge from '@automerge/automerge'

// Create document
let doc1 = Automerge.from({
  tasks: [],
  title: "My Tasks"
})

// Make changes
doc1 = Automerge.change(doc1, doc => {
  doc.tasks.push({ text: "Buy milk", done: false })
})

// Clone for replica
let doc2 = Automerge.clone(doc1)

// Concurrent changes
doc1 = Automerge.change(doc1, doc => {
  doc.tasks[0].done = true
})

doc2 = Automerge.change(doc2, doc => {
  doc.tasks.push({ text: "Buy eggs", done: false })
})

// Merge
doc1 = Automerge.merge(doc1, doc2)
// Result: both changes preserved
```

**Performance**:
- O(1) field updates
- O(n) list operations
- Compact encoding: ~2x JSON size

### Yjs

**Description**: High-performance CRDT library optimized for collaborative editing

**Features**:
- Optimized for text editing
- WebRTC, WebSocket support
- Bindings: React, Vue, Prosemirror, Monaco
- Excellent performance

**Usage**:
```javascript
import * as Y from 'yjs'

const doc1 = new Y.Doc()
const text1 = doc1.getText('mytext')

// Create replica
const doc2 = new Y.Doc()
const text2 = doc2.getText('mytext')

// Setup sync
doc1.on('update', update => {
  Y.applyUpdate(doc2, update)
})
doc2.on('update', update => {
  Y.applyUpdate(doc1, update)
})

// Insert text concurrently
text1.insert(0, "Hello")
text2.insert(0, "World")

// Both docs converge to "WorldHello" or "HelloWorld" (deterministic)
```

**Performance**:
- Highly optimized
- O(1) character insert/delete
- Structural sharing
- Small update sizes

### Conflict-free Replicated JSON (CRJSON)

**Description**: Specification for JSON CRDTs

**Data Types**:
- Objects: LWW-Map or OR-Map
- Arrays: RGA or similar sequence CRDT
- Primitives: LWW-Register or MV-Register
- Nulls: Special handling

**Example Schema**:
```json
{
  "type": "object",
  "properties": {
    "title": { "type": "lww-register" },
    "items": {
      "type": "rga",
      "element": {
        "type": "object",
        "properties": {
          "name": { "type": "lww-register" },
          "done": { "type": "lww-register" }
        }
      }
    }
  }
}
```

### Other Implementations

**Riak KV (Erlang)**:
- Distributed key-value store
- Built-in CRDTs: counters, sets, maps, flags, registers
- Production-grade

**Redis CRDT (Redis Enterprise)**:
- CRDB (Conflict-free Replicated Database)
- Active-active geo-distribution
- CRDTs for core data types

**Akka Distributed Data (Scala)**:
- CRDTs in Akka clusters
- Types: counters, sets, maps, flags
- Gossip-based replication

---

## CAP Theorem and CRDT Positioning

### CAP Theorem Refresher

**CAP**: In a distributed system, you can have at most 2 of 3:
1. **Consistency**: All nodes see same data
2. **Availability**: System responds to requests
3. **Partition tolerance**: System works despite network partitions

**Reality**: Partition tolerance is mandatory (networks fail), so choose between:
- **CP**: Consistent but unavailable during partitions
- **AP**: Available but potentially inconsistent during partitions

### CRDTs and CAP

**CRDT Positioning**: **AP** (Available and Partition-tolerant)

**Consistency Model**: **Strong Eventual Consistency**
- Not strict consistency (linearizability)
- Not eventual consistency (might not converge)
- Stronger than eventual: guarantees convergence

**Tradeoffs**:

**Pros**:
- Always available for reads/writes
- No coordination required
- Partition-tolerant by design
- Guaranteed convergence

**Cons**:
- No read-your-writes guarantee across replicas (without sync)
- Larger memory footprint (metadata)
- Some operations not supported (decrement on G-Counter)
- Application may need conflict resolution

### CRDT vs Other Approaches

**CRDTs vs Operational Transformation (OT)**:

| Aspect | CRDTs | OT |
|--------|-------|-----|
| Commutativity | Required | Not required |
| Central server | Optional | Often required |
| Complexity | Data structure design | Transform functions |
| Correctness | Provable | Subtle edge cases |
| Use case | Any replicated data | Real-time collab editing |

**CRDTs vs Consensus (Paxos/Raft)**:

| Aspect | CRDTs | Consensus |
|--------|-------|-----------|
| Coordination | None | Leader election |
| Availability | High (AP) | Lower (CP) |
| Latency | Low (local writes) | Higher (round trips) |
| Consistency | Eventual | Strong/Linearizable |
| Use case | High availability | Strong consistency |

**CRDTs vs Transactions**:

| Aspect | CRDTs | Transactions |
|--------|-------|--------------|
| Isolation | None | ACID |
| Conflicts | Automatic merge | Abort/retry |
| Performance | High throughput | Lower (locking/2PC) |
| Use case | Replicated data | Multi-object updates |

---

## Performance Characteristics

### Space Complexity

**State-based CRDTs**:
- **G-Counter**: O(n) where n = replicas
- **PN-Counter**: O(2n)
- **OR-Set**: O(m × k) where m = elements, k = adds per element
- **LWW-Set**: O(m)
- **RGA**: O(m) including tombstones
- **OR-Map**: O(k × v) where k = keys, v = values per key

**Metadata Overhead**:
- Vector clocks: O(n) per object
- Unique IDs: O(log m) per element
- Timestamps: O(1) per element

**Optimization Strategies**:
1. **Garbage collection**: Remove tombstones
2. **Compaction**: Merge redundant metadata
3. **Delta-state**: Send only changes
4. **Pruning**: Remove old vector clock entries

### Time Complexity

**G-Counter**:
- Increment: O(1)
- Value: O(n)
- Merge: O(n)

**OR-Set**:
- Add: O(1)
- Remove: O(k) where k = adds for element
- Contains: O(k)
- Merge: O(m)

**RGA**:
- Insert: O(n) to find position
- Delete: O(n) to find element
- To-string: O(n)
- Merge: O(n)

**LWW-Map**:
- Set: O(1)
- Get: O(1)
- Merge: O(k) where k = keys

### Network Overhead

**State-based (Full State)**:
- Message size: O(size of state)
- Good for: Small states, infrequent sync
- Bad for: Large states, frequent sync

**Op-based (Operations)**:
- Message size: O(size of operation)
- Good for: Frequent updates, large state
- Bad for: Requires reliable delivery

**Delta-state (Deltas)**:
- Message size: O(size of changes)
- Best of both worlds
- Complexity: Implementation overhead

**Compression**:
- Binary encoding (vs JSON)
- Delta compression
- Reference compression (string deduplication)

### Benchmarks

**Yjs Performance** (collaborative text editing):
- Inserts: ~500,000 ops/sec
- Memory: ~2x original text size
- Sync: ~1ms for 1000 character document

**Automerge Performance**:
- Inserts: ~10,000 ops/sec
- Memory: ~3-4x original data size
- Sync: ~10ms for medium document

**CRDT vs Central Server** (text editing):
- Latency: CRDT ~10ms, Central ~50-200ms (network)
- Throughput: CRDT higher (no coordination)
- Offline: CRDT works, Central fails

---

## Design Patterns

### Pattern 1: Layered CRDTs

**Problem**: Complex data model needs different consistency semantics

**Solution**: Use different CRDTs at different layers

**Example**: Collaborative document editor
```python
class Document:
    def __init__(self):
        self.metadata = LWWMap()      # Title, author (LWW)
        self.content = RGA()          # Text content (sequence)
        self.comments = ORMap()       # Comments by ID (OR-Map)
        self.users = GSet()           # Active users (grow-only)
```

**Benefits**:
- Right semantics for each data type
- Optimized for use case
- Clear consistency model

### Pattern 2: CRDT with Intent Preservation

**Problem**: Pure CRDT semantics don't match user intent

**Solution**: Add application logic to interpret CRDT operations

**Example**: Whiteboard with move operations
```python
class Shape:
    def __init__(self):
        self.position = LWWRegister()  # x, y coordinates
        self.deleted = LWWRegister()   # is_deleted flag

    def move(self, x, y, timestamp):
        if not self.deleted.get():
            self.position.set((x, y), timestamp)

    # Intent: moving deleted shape should undelete it
    def move_with_intent(self, x, y, timestamp):
        self.deleted.set(False, timestamp)
        self.position.set((x, y), timestamp)
```

### Pattern 3: CRDT with Constraints

**Problem**: CRDT allows invalid states (e.g., negative inventory)

**Solution**: Add validation layer above CRDT

**Example**: Inventory system
```python
class Inventory:
    def __init__(self):
        self.counter = PNCounter()
        self.reservations = ORSet()

    def remove(self, quantity, replica_id):
        # Check constraint before decrement
        current = self.counter.value()
        if current - quantity >= 0:
            self.counter.decrement(replica_id, quantity)
            return True
        return False  # Reject if would go negative

    # Alternative: Use G-Counter only (prevent negatives structurally)
```

**Tradeoffs**:
- Validation may reject valid concurrent operations
- Consider: compensating actions, reservations, eventual validation

### Pattern 4: Hybrid Consistency

**Problem**: Different operations need different consistency

**Solution**: Use CRDTs for availability, consensus for critical ops

**Example**: Bank account
```python
class Account:
    def __init__(self):
        self.balance = PNCounter()     # Optimistic updates
        self.holds = ORSet()           # Holds/reservations

    def deposit(self, amount, replica_id):
        # Fast: CRDT increment
        self.balance.increment(replica_id, amount)

    def withdraw(self, amount, replica_id):
        # Slow: Consensus to prevent overdraft
        if self.available_balance() >= amount:
            consensus_service.acquire_lock(self.id)
            if self.available_balance() >= amount:
                self.balance.decrement(replica_id, amount)
                success = True
            else:
                success = False
            consensus_service.release_lock(self.id)
            return success
        return False
```

### Pattern 5: Undo with CRDTs

**Problem**: CRDTs don't naturally support undo

**Solution**: Track operation history and use inverse operations

**Example**:
```python
class UndoableCounter:
    def __init__(self):
        self.counter = PNCounter()
        self.history = []  # List of (op, params)

    def increment(self, replica_id, amount=1):
        self.counter.increment(replica_id, amount)
        self.history.append(("increment", replica_id, amount))

    def undo(self, replica_id):
        if not self.history:
            return
        op, rid, amount = self.history.pop()
        if op == "increment":
            self.counter.decrement(replica_id, amount)
        elif op == "decrement":
            self.counter.increment(replica_id, amount)
```

**Challenges**:
- Undo of concurrent operations is ambiguous
- Consider: per-user undo vs global undo

---

## Testing and Verification

### Testing Strategies

**1. Convergence Testing**
```python
def test_convergence():
    # Create replicas
    r1 = GCounter(3)
    r2 = GCounter(3)
    r3 = GCounter(3)

    # Apply operations in different orders
    r1.increment(0)
    r1.increment(1)

    r2.increment(1)
    r2.increment(0)

    # Merge
    r3.merge(r1)
    r3.merge(r2)

    # Assert convergence
    assert r1.value() == r2.value() == r3.value()
```

**2. Commutativity Testing**
```python
def test_commutativity():
    s1 = ORSet()
    s2 = ORSet()

    # Apply ops in order: op1, op2
    op1 = s1.add("a", "replica1", 1)
    op2 = s1.add("b", "replica1", 2)

    # Apply ops in reverse: op2, op1
    s2.apply(op2)
    s2.apply(op1)

    # Assert same result
    assert s1.elements() == s2.elements()
```

**3. Idempotency Testing**
```python
def test_idempotency():
    s = ORSet()
    op = s.add("x", "replica1", 1)

    state1 = s.copy()
    s.apply(op)  # Apply once
    state2 = s.copy()
    s.apply(op)  # Apply again
    state3 = s.copy()

    assert state2 == state3  # Same after duplicate apply
```

**4. Concurrent Operations Testing**
```python
def test_concurrent_ops():
    # Simulate network partition
    r1 = LWWSet()
    r2 = LWWSet()

    # Concurrent operations
    r1.add("x", timestamp=100)
    r2.remove("x", timestamp=100)  # Same timestamp

    # Merge and check bias
    r1.merge(r2)
    # Verify add-wins or remove-wins based on spec
```

**5. Property-Based Testing**
```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_counter_monotonic(operations):
    counter = GCounter(1)
    prev_value = counter.value()

    for op in operations:
        if op > 0:
            counter.increment(0, op)
            assert counter.value() >= prev_value
            prev_value = counter.value()
```

### Verification Techniques

**Formal Verification**:
- Prove commutativity, associativity, idempotency
- Use proof assistants: Coq, Isabelle/HOL
- Verify merge function forms semilattice

**Model Checking**:
- Enumerate all possible execution orders
- Check convergence for all orderings
- Tools: TLA+, Alloy

**Simulation Testing**:
```python
def simulate_network(n_replicas, n_operations):
    replicas = [ORSet() for _ in range(n_replicas)]
    operations = generate_random_ops(n_operations)

    # Apply operations with random network delays
    for op in operations:
        replica = random.choice(replicas)
        replica.apply(op)

        # Randomly sync
        if random.random() < 0.3:
            r1, r2 = random.sample(replicas, 2)
            r1.merge(r2)

    # Final sync
    for i in range(len(replicas) - 1):
        replicas[i+1].merge(replicas[i])

    # Verify convergence
    for replica in replicas[1:]:
        assert replica.state() == replicas[0].state()
```

### Common Bugs

**1. Missing Commutativity**
```python
# Bug: operations don't commute
def bad_counter():
    self.value += amount
    self.max = max(self.max, self.value)  # Depends on order!
```

**2. Incorrect Merge**
```python
# Bug: merge not idempotent
def bad_merge(other):
    self.count += other.count  # Doubles on repeated merge!

# Fix: merge should be idempotent
def good_merge(other):
    for i in range(len(self.count)):
        self.count[i] = max(self.count[i], other.count[i])
```

**3. Lost Updates**
```python
# Bug: LWW loses concurrent updates
def lww_register_issue():
    r1.set("Alice", timestamp=100)
    r2.set("Bob", timestamp=100)   # Same timestamp
    # One update lost!

# Fix: Use MV-Register for concurrent values
```

**4. Causality Violations**
```python
# Bug: operation applied before its dependency
def causal_violation():
    r1.insert("b", after="a")  # Depends on "a" existing
    # If this arrives before insert("a"), fails

# Fix: Use vector clocks, buffer out-of-order ops
```

---

## Summary

CRDTs provide **strong eventual consistency** without coordination by:
1. Ensuring operations commute (operation-based)
2. Using merge functions that form semilattices (state-based)
3. Guaranteeing convergence when all replicas receive same updates

**Key Insights**:
- Not all data types have CRDT representations
- Different CRDTs have different tradeoffs (memory, semantics)
- CRDTs sacrifice strong consistency for availability
- Composition enables complex data structures
- Delta-state CRDTs optimize bandwidth

**When to Use CRDTs**:
- High availability required
- Network partitions expected
- Collaborative editing
- Distributed caching
- Edge computing
- Offline-first applications

**When Not to Use CRDTs**:
- Strong consistency required (use consensus)
- Complex constraints (use transactions)
- Low tolerance for conflicts (use coordination)

**Further Reading**:
- Shapiro et al., "A comprehensive study of CRDTs" (2011)
- Kleppmann & Beresford, "A Conflict-Free Replicated JSON Datatype" (2017)
- Attiya et al., "Specification and Complexity of Collaborative Text Editing" (2016)
