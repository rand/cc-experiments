---
name: distributed-systems-interval-tree-clocks
description: Interval tree clocks for dynamic systems, scalable causality tracking, fork/join operations, avoiding process ID exhaustion
---

# Interval Tree Clocks

**Scope**: Interval tree clocks (ITC), dynamic causality, fork/join, scalable distributed time
**Lines**: ~390
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building systems with dynamic process creation
- Avoiding vector clock ID exhaustion
- Implementing fork/join parallelism tracking
- Tracking causality without pre-assigned IDs
- Building actor systems with spawn/terminate
- Implementing causality in serverless functions
- Managing ephemeral worker processes
- Scaling beyond fixed process counts

## Core Concepts

### The Problem with Vector Clocks

**Fixed process ID requirement**:
```
Vector Clock: {A:5, B:3, C:7}
               ↑   ↑   ↑
          Pre-assigned IDs

Problems:
1. Must know all process IDs upfront
2. Adding new process → resize all vectors
3. Short-lived processes waste space
4. Can't handle dynamic fork/join
```

**ID exhaustion**:
```
Serverless functions: 1000s of ephemeral workers
Actor systems: Actors spawn/terminate dynamically
Microservices: Containers scale up/down

Vector clock grows to 1000s of entries!
```

### Interval Tree Clocks Solution

**Key insight**: Represent causality as intervals in ID space, not fixed IDs

```
ITC = (id_interval, event_tree)

id_interval: Portion of ID space owned by this process
event_tree: Binary tree tracking causal events

Properties:
1. Fork: Split ID interval between processes
2. Join: Merge ID intervals when processes sync
3. Event: Increment counter in owned interval
4. O(log N) size for N events (not N processes!)
```

**Visual**:
```
Process A owns [0, 1):
  ITC_A = ([0, 1), tree)

A forks to create B:
  ITC_A = ([0, 0.5), tree_a)
  ITC_B = ([0.5, 1), tree_b)

A and B can fork further:
  ITC_A1 = ([0, 0.25), ...)
  ITC_A2 = ([0.25, 0.5), ...)
```

---

## Algorithm

### Data Structures

```python
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class IDInterval:
    """Interval in ID space [start, end)"""
    start: float
    end: float

    def __repr__(self):
        return f"[{self.start:.3f}, {self.end:.3f})"

    def is_empty(self) -> bool:
        return self.start >= self.end

    def split(self) -> Tuple['IDInterval', 'IDInterval']:
        """Split interval in half"""
        mid = (self.start + self.end) / 2
        return IDInterval(self.start, mid), IDInterval(mid, self.end)

    def merge(self, other: 'IDInterval') -> Optional['IDInterval']:
        """Merge adjacent intervals"""
        if self.end == other.start:
            return IDInterval(self.start, other.end)
        elif other.end == self.start:
            return IDInterval(other.start, self.end)
        return None

class EventTree:
    """Binary tree tracking causal events"""

    def __init__(self, value: int = 0, left: Optional['EventTree'] = None,
                 right: Optional['EventTree'] = None):
        self.value = value
        self.left = left
        self.right = right

    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

    def __repr__(self):
        if self.is_leaf():
            return f"{self.value}"
        return f"({self.value}, {self.left}, {self.right})"

    def copy(self) -> 'EventTree':
        """Deep copy of tree"""
        if self.is_leaf():
            return EventTree(self.value)
        return EventTree(
            self.value,
            self.left.copy() if self.left else None,
            self.right.copy() if self.right else None
        )

class ITC:
    """Interval Tree Clock"""

    def __init__(self, interval: IDInterval, event: EventTree):
        self.interval = interval
        self.event = event

    def __repr__(self):
        return f"ITC({self.interval}, {self.event})"

    @staticmethod
    def seed() -> 'ITC':
        """Create initial ITC with full ID space"""
        return ITC(IDInterval(0.0, 1.0), EventTree(0))

    def copy(self) -> 'ITC':
        """Deep copy"""
        return ITC(self.interval, self.event.copy())
```

---

## Core Operations

### Event (Increment)

```python
def event(self) -> 'ITC':
    """
    Increment event counter in owned interval

    Returns new ITC with incremented event
    """
    def increment_tree(tree: EventTree, interval: IDInterval,
                      owned: IDInterval) -> EventTree:
        if tree.is_leaf():
            # Leaf covers owned interval - increment
            return EventTree(tree.value + 1)

        # Split interval and recurse
        mid = (interval.start + interval.end) / 2

        if owned.end <= mid:
            # Owned interval in left half
            left = increment_tree(tree.left, IDInterval(interval.start, mid), owned)
            return EventTree(tree.value, left, tree.right.copy())
        elif owned.start >= mid:
            # Owned interval in right half
            right = increment_tree(tree.right, IDInterval(mid, interval.end), owned)
            return EventTree(tree.value, tree.left.copy(), right)
        else:
            # Owned interval spans both halves - should not happen in normal use
            raise ValueError("Owned interval spans tree split")

    new_event = increment_tree(self.event, IDInterval(0.0, 1.0), self.interval)
    return ITC(self.interval, new_event)

# Usage
itc = ITC.seed()
print(f"Initial: {itc}")  # ITC([0.000, 1.000), 0)

itc = itc.event()
print(f"After event: {itc}")  # ITC([0.000, 1.000), 1)

itc = itc.event()
print(f"After event: {itc}")  # ITC([0.000, 1.000), 2)
```

### Fork (Split ID Space)

```python
def fork(self) -> Tuple['ITC', 'ITC']:
    """
    Split ITC into two independent ITCs

    Returns (itc1, itc2) where:
    - itc1 and itc2 can make independent events
    - Together they cover original ID space
    """
    # Split ID interval
    left_interval, right_interval = self.interval.split()

    # Clone event tree for both
    left_itc = ITC(left_interval, self.event.copy())
    right_itc = ITC(right_interval, self.event.copy())

    return left_itc, right_itc

# Usage
itc = ITC.seed()
itc = itc.event()  # ITC([0.000, 1.000), 1)

# Fork into two processes
itc_a, itc_b = itc.fork()
print(f"Process A: {itc_a}")  # ITC([0.000, 0.500), 1)
print(f"Process B: {itc_b}")  # ITC([0.500, 1.000), 1)

# Independent events
itc_a = itc_a.event()  # A increments
itc_b = itc_b.event()  # B increments (concurrent!)
```

### Join (Merge Clocks)

```python
def join(self, other: 'ITC') -> 'ITC':
    """
    Merge two ITCs on synchronization

    Returns new ITC with:
    - Merged ID intervals
    - Combined event trees (max of both)
    """
    def merge_trees(tree1: EventTree, tree2: EventTree,
                   interval: IDInterval, int1: IDInterval,
                   int2: IDInterval) -> EventTree:
        """Merge two event trees"""
        # Base case: both leaves
        if tree1.is_leaf() and tree2.is_leaf():
            return EventTree(max(tree1.value, tree2.value))

        # Expand leaves to match structure
        if tree1.is_leaf() and not tree2.is_leaf():
            tree1 = EventTree(tree1.value, EventTree(0), EventTree(0))
        if tree2.is_leaf() and not tree1.is_leaf():
            tree2 = EventTree(tree2.value, EventTree(0), EventTree(0))

        # Recursive merge
        mid = (interval.start + interval.end) / 2
        left_interval = IDInterval(interval.start, mid)
        right_interval = IDInterval(mid, interval.end)

        left = merge_trees(tree1.left, tree2.left, left_interval, int1, int2)
        right = merge_trees(tree1.right, tree2.right, right_interval, int1, int2)

        # Combine with max base
        base = max(tree1.value, tree2.value)
        return EventTree(base, left, right)

    # Merge intervals
    merged_interval = self._merge_intervals(self.interval, other.interval)

    # Merge event trees
    merged_event = merge_trees(
        self.event, other.event,
        IDInterval(0.0, 1.0),
        self.interval, other.interval
    )

    return ITC(merged_interval, merged_event)

def _merge_intervals(self, int1: IDInterval, int2: IDInterval) -> IDInterval:
    """Merge two intervals (assumes adjacent or overlapping)"""
    return IDInterval(min(int1.start, int2.start), max(int1.end, int2.end))

# Usage
itc_a, itc_b = ITC.seed().fork()
itc_a = itc_a.event()  # A: 1
itc_b = itc_b.event().event()  # B: 2

# Synchronize
itc_merged = itc_a.join(itc_b)
print(f"Merged: {itc_merged}")  # Captures both histories
```

---

## Comparison Operations

```python
def leq(self, other: 'ITC') -> bool:
    """
    Check if self ≤ other (happens-before or concurrent)

    Returns True if self's events are causally before or equal to other's
    """
    def compare_trees(tree1: EventTree, tree2: EventTree) -> bool:
        """Check if tree1 ≤ tree2"""
        if tree1.is_leaf() and tree2.is_leaf():
            return tree1.value <= tree2.value

        if tree1.is_leaf():
            # Expand tree1 to match structure
            return compare_trees(
                EventTree(tree1.value, EventTree(0), EventTree(0)),
                tree2
            )

        if tree2.is_leaf():
            # Expand tree2 to match structure
            return compare_trees(
                tree1,
                EventTree(tree2.value, EventTree(0), EventTree(0))
            )

        # Both internal nodes
        return (tree1.value <= tree2.value and
                compare_trees(tree1.left, tree2.left) and
                compare_trees(tree1.right, tree2.right))

    return compare_trees(self.event, other.event)

def concurrent(self, other: 'ITC') -> bool:
    """Check if self and other are concurrent"""
    return not self.leq(other) and not other.leq(self)

# Usage
itc_a, itc_b = ITC.seed().fork()
itc_a = itc_a.event()
itc_b = itc_b.event()

print(itc_a.concurrent(itc_b))  # True - concurrent events
print(itc_a.leq(itc_b))  # False
```

---

## Practical Example: Actor System

```python
class Actor:
    """Actor with ITC for causality tracking"""

    def __init__(self, actor_id: str, itc: ITC):
        self.actor_id = actor_id
        self.itc = itc
        self.mailbox = []

    def send_message(self, recipient: 'Actor', msg):
        """Send message with current ITC"""
        # Local event (sending)
        self.itc = self.itc.event()

        # Include ITC snapshot in message
        recipient.receive_message(msg, self.itc.copy())

    def receive_message(self, msg, sender_itc: ITC):
        """Receive message and update ITC"""
        # Merge with sender's causality
        self.itc = self.itc.join(sender_itc)

        # Process message (local event)
        self.itc = self.itc.event()

        print(f"[{self.actor_id}] Received: {msg}, ITC: {self.itc}")

    def spawn_child(self) -> 'Actor':
        """Spawn child actor with forked ITC"""
        parent_itc, child_itc = self.itc.fork()

        self.itc = parent_itc
        child = Actor(f"{self.actor_id}.child", child_itc)

        print(f"[{self.actor_id}] Spawned child with ITC: {child.itc}")
        return child

# Usage Example
# Create initial actor
root = Actor("root", ITC.seed())

# Spawn children
child1 = root.spawn_child()
child2 = root.spawn_child()

# Send messages
root.send_message(child1, "Hello from root")
child1.send_message(child2, "Hello from child1")
child2.send_message(root, "Reply from child2")

# Spawn grandchild
grandchild = child1.spawn_child()
child1.send_message(grandchild, "Message to grandchild")
```

---

## Serverless Function Example

```python
class ServerlessFunction:
    """Serverless function with ITC causality"""

    def __init__(self, function_id: str):
        self.function_id = function_id
        self.itc = None  # Assigned dynamically

    def invoke(self, request, context_itc: Optional[ITC] = None):
        """Invoke function with optional causal context"""
        # Initialize or fork ITC
        if context_itc is None:
            # First invocation
            self.itc = ITC.seed()
        else:
            # Fork from context
            _, self.itc = context_itc.fork()

        # Process request (local event)
        self.itc = self.itc.event()

        print(f"[{self.function_id}] Processing request, ITC: {self.itc}")

        # Return result with ITC
        return {"result": "processed", "itc": self.itc}

    def chain_invoke(self, next_function: 'ServerlessFunction', request):
        """Invoke next function in chain"""
        # Pass ITC context
        return next_function.invoke(request, self.itc)

# Usage: Serverless workflow
fn1 = ServerlessFunction("process-order")
fn2 = ServerlessFunction("send-email")
fn3 = ServerlessFunction("update-inventory")

# Cold start
result1 = fn1.invoke({"order_id": 123})

# Chain invocations (causality preserved)
result2 = fn1.chain_invoke(fn2, {"email": "user@example.com"})
result3 = fn1.chain_invoke(fn3, {"item_id": 456})

# Parallel invocations (concurrent)
fn4 = ServerlessFunction("analytics")
fn5 = ServerlessFunction("logging")
fn1.chain_invoke(fn4, {})  # Concurrent
fn1.chain_invoke(fn5, {})  # Concurrent
```

---

## Comparison: Vector Clocks vs ITC

| Aspect | Vector Clocks | Interval Tree Clocks |
|--------|--------------|---------------------|
| **Process IDs** | Pre-assigned, fixed | Dynamic, allocated on demand |
| **Size** | O(N) processes | O(log E) events |
| **Fork** | Not supported | O(1) |
| **Join** | Element-wise max | Tree merge O(log E) |
| **Event** | O(1) increment | O(log E) tree update |
| **Comparison** | O(N) | O(E) |
| **Dynamic systems** | Poor fit | Excellent fit |
| **Memory** | High for many processes | Low, scales with events |

**Space comparison**:
```
System with 1000 short-lived processes:

Vector Clock:
- 1000 entries × 8 bytes = 8KB per version
- 10 versions = 80KB

ITC:
- Tree depth ≈ log₂(1000) ≈ 10 levels
- ~20 nodes × 8 bytes = 160 bytes per version
- 10 versions = 1.6KB

Savings: ~98% reduction!
```

---

## Optimizations

### Tree Normalization

```python
def normalize_tree(tree: EventTree) -> EventTree:
    """
    Normalize tree by lifting common values

    (5, (5, (5, 0, 0))) → (10, 0, 0)
    """
    if tree.is_leaf():
        return tree

    left = normalize_tree(tree.left) if tree.left else EventTree(0)
    right = normalize_tree(tree.right) if tree.right else EventTree(0)

    # Lift common value
    if not left.is_leaf() or not right.is_leaf():
        min_val = min(left.value, right.value)
        if min_val > 0:
            left = _subtract_tree(left, min_val)
            right = _subtract_tree(right, min_val)
            return EventTree(tree.value + min_val, left, right)

    return EventTree(tree.value, left, right)

def _subtract_tree(tree: EventTree, value: int) -> EventTree:
    """Subtract value from tree"""
    if tree.is_leaf():
        return EventTree(max(0, tree.value - value))
    return EventTree(
        max(0, tree.value - value),
        _subtract_tree(tree.left, value),
        _subtract_tree(tree.right, value)
    )
```

### Interval Coalescing

```python
def coalesce_intervals(itcs: list) -> ITC:
    """
    Merge multiple ITCs with adjacent intervals

    Useful after collecting IDs from terminated processes
    """
    # Sort by interval start
    sorted_itcs = sorted(itcs, key=lambda i: i.interval.start)

    # Merge adjacent intervals
    result = sorted_itcs[0]
    for itc in sorted_itcs[1:]:
        merged_interval = result.interval.merge(itc.interval)
        if merged_interval:
            result = ITC(merged_interval, result.event)
            result = result.join(itc)
        else:
            # Non-adjacent, can't merge
            pass

    return result
```

---

## Testing ITC

```python
import unittest

class TestITC(unittest.TestCase):
    def test_event_increments(self):
        """Test that event increments counter"""
        itc = ITC.seed()
        itc = itc.event()
        itc = itc.event()

        # Should have incremented
        self.assertEqual(itc.event.value, 2)

    def test_fork_splits_interval(self):
        """Test that fork splits ID interval"""
        itc = ITC.seed()
        itc1, itc2 = itc.fork()

        # Check intervals split
        self.assertLess(itc1.interval.end, itc2.interval.start + 0.01)
        self.assertGreater(itc1.interval.end, itc2.interval.start - 0.01)

    def test_concurrent_after_fork(self):
        """Test that independent events after fork are concurrent"""
        itc = ITC.seed()
        itc1, itc2 = itc.fork()

        itc1 = itc1.event()
        itc2 = itc2.event()

        # Should be concurrent
        self.assertTrue(itc1.concurrent(itc2))

    def test_join_merges(self):
        """Test that join merges causality"""
        itc = ITC.seed()
        itc1, itc2 = itc.fork()

        itc1 = itc1.event()
        itc2 = itc2.event()

        # Join
        merged = itc1.join(itc2)

        # Merged should dominate both
        self.assertTrue(itc1.leq(merged))
        self.assertTrue(itc2.leq(merged))

    def test_happens_before(self):
        """Test happens-before relationship"""
        itc = ITC.seed()
        itc1 = itc.event()
        itc2 = itc1.event()

        # itc1 happened before itc2
        self.assertTrue(itc1.leq(itc2))
        self.assertFalse(itc2.leq(itc1))
```

---

## Related Skills

- `distributed-systems-vector-clocks` - Fixed-process causality
- `distributed-systems-dotted-version-vectors` - Optimized vector clocks
- `distributed-systems-logical-clocks` - Lamport clocks
- `distributed-systems-crdt-fundamentals` - Causal CRDTs
- `distributed-systems-eventual-consistency` - Consistency models

---

**Last Updated**: 2025-10-27
