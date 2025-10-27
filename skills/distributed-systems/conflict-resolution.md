---
name: distributed-systems-conflict-resolution
description: Conflict resolution strategies including Last-Write-Wins, multi-value, semantic resolution, and application-specific merge functions
---

# Conflict Resolution

**Scope**: Conflict detection, resolution strategies, merge functions, application-specific resolution
**Lines**: ~280
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building eventually consistent systems
- Handling concurrent writes
- Implementing distributed databases
- Designing conflict resolution logic
- Working with CRDTs
- Building collaborative applications
- Understanding Dynamo, Riak
- Implementing offline-first apps

## Core Concepts

### Types of Conflicts

**Write-Write Conflict**: Two replicas update same key concurrently

```
Time →
Replica A: Write X=1
Replica B: Write X=2  (concurrent with A)

Conflict: Which value should win?
```

**Read-Modify-Write Conflict**: Concurrent modifications based on same read

```
Both clients read balance=100
Client A: balance += 50  → 150
Client B: balance += 30  → 130

Which is correct? Should be 180!
```

---

## Resolution Strategies

### 1. Last-Write-Wins (LWW)

**Approach**: Use timestamp, latest wins

```python
import time

class LWWRegister:
    """Last-Write-Wins with timestamps"""

    def __init__(self):
        self.value = None
        self.timestamp = 0

    def write(self, value, timestamp=None):
        """Write with timestamp"""
        if timestamp is None:
            timestamp = time.time()

        if timestamp > self.timestamp:
            self.value = value
            self.timestamp = timestamp

    def merge(self, other):
        """Merge with another replica"""
        if other.timestamp > self.timestamp:
            self.value = other.value
            self.timestamp = other.timestamp

# Problem: Can lose data!
r1 = LWWRegister()
r2 = LWWRegister()

r1.write('A', timestamp=100.001)
r2.write('B', timestamp=100.002)  # B wins, A lost!

r1.merge(r2)
print(r1.value)  # 'B' (A's write lost)
```

**Pros**: Simple, no user intervention
**Cons**: Data loss possible, relies on clock synchronization

### 2. Multi-Value (Siblings)

**Approach**: Keep all concurrent values, resolve later

```python
class MultiValueRegister:
    """Keep concurrent values as siblings"""

    def __init__(self):
        self.values = {}  # vector_clock → value

    def write(self, value, vector_clock):
        """Write with causality tracking"""
        # Remove values this one supersedes
        self.values = {
            vc: v for vc, v in self.values.items()
            if not self._causally_before(vc, vector_clock)
        }
        self.values[vector_clock] = value

    def read(self):
        """Return all concurrent values"""
        return list(self.values.values())

    def _causally_before(self, vc1, vc2):
        """Check if vc1 causally before vc2"""
        return all(vc1.get(k, 0) <= vc2.get(k, 0) for k in vc2) and vc1 != vc2

    def merge(self, other):
        """Merge siblings from other replica"""
        for vc, v in other.values.items():
            if vc not in self.values:
                # Check if dominated by existing values
                dominated = any(
                    self._causally_before(vc, existing_vc)
                    for existing_vc in self.values.keys()
                )
                if not dominated:
                    self.values[vc] = v
```

**Pros**: No data loss
**Cons**: Application must handle siblings

### 3. Semantic Resolution

**Approach**: Use domain knowledge to merge

```python
class ShoppingCart:
    """Shopping cart with semantic merge"""

    def __init__(self):
        self.items = {}  # item_id → (quantity, add_timestamp, remove_timestamp)

    def add_item(self, item_id, quantity, timestamp):
        """Add item to cart"""
        if item_id in self.items:
            qty, add_ts, rem_ts = self.items[item_id]
            # Only if not removed after
            if rem_ts is None or timestamp > rem_ts:
                self.items[item_id] = (qty + quantity, max(add_ts, timestamp), rem_ts)
        else:
            self.items[item_id] = (quantity, timestamp, None)

    def remove_item(self, item_id, timestamp):
        """Remove item from cart"""
        if item_id in self.items:
            qty, add_ts, _ = self.items[item_id]
            # Only if added before removal
            if timestamp > add_ts:
                self.items[item_id] = (qty, add_ts, timestamp)

    def merge(self, other):
        """Semantic merge of shopping carts"""
        # Merge item by item
        all_items = set(self.items.keys()) | set(other.items.keys())

        for item_id in all_items:
            my_item = self.items.get(item_id)
            other_item = other.items.get(item_id)

            if my_item and other_item:
                # Both have item - merge
                qty1, add1, rem1 = my_item
                qty2, add2, rem2 = other_item

                # Use latest add timestamp
                final_add = max(add1, add2)

                # Use latest remove timestamp (if any)
                final_rem = max(rem1 or 0, rem2 or 0) if (rem1 or rem2) else None

                # If removed after added, mark removed; otherwise sum quantities
                if final_rem and final_rem > final_add:
                    self.items[item_id] = (0, final_add, final_rem)
                else:
                    self.items[item_id] = (qty1 + qty2, final_add, None)

            elif my_item:
                pass  # Keep my item
            else:
                self.items[item_id] = other_item  # Use other item

    def get_items(self):
        """Get current cart contents (excluding removed)"""
        return {
            item_id: qty
            for item_id, (qty, add_ts, rem_ts) in self.items.items()
            if rem_ts is None or add_ts > rem_ts
        }
```

### 4. Application-Specific Merge Functions

```python
class Counter:
    """Counter with commutative merge"""

    def __init__(self, replica_id):
        self.replica_id = replica_id
        self.increments = {}  # replica_id → count

    def increment(self, amount=1):
        """Increment counter"""
        if self.replica_id not in self.increments:
            self.increments[self.replica_id] = 0
        self.increments[self.replica_id] += amount

    def value(self):
        """Get total count"""
        return sum(self.increments.values())

    def merge(self, other):
        """Merge with another counter (element-wise max)"""
        for replica_id, count in other.increments.items():
            self.increments[replica_id] = max(
                self.increments.get(replica_id, 0),
                count
            )

# No conflicts! Merges commute
c1 = Counter('A')
c2 = Counter('B')

c1.increment(5)
c2.increment(3)

c1.merge(c2)
print(c1.value())  # 8 (correct!)
```

---

## Conflict Resolution in Practice

### Riak

```python
# Riak allows custom merge functions
import riak

client = riak.RiakClient()
bucket = client.bucket('users')

# Allow siblings
bucket.allow_mult = True

# Write
obj = bucket.new('user_123', data={'name': 'Alice', 'age': 30})
obj.store()

# Concurrent write creates sibling
obj2 = bucket.get('user_123')
obj2.data['age'] = 31
obj2.store()

# Read returns siblings
obj3 = bucket.get('user_123')
if obj3.siblings:
    # Application resolves conflict
    merged = resolve_user_siblings(obj3.siblings)
    obj3.data = merged
    obj3.store()  # Store resolved value
```

### DynamoDB

```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Orders')

# Conditional write to avoid conflicts
try:
    table.put_item(
        Item={'order_id': '123', 'status': 'shipped', 'version': 2},
        ConditionExpression='version = :v',
        ExpressionAttributeValues={':v': 1}
    )
except ClientError as e:
    if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
        # Conflict detected - handle retry logic
        current = table.get_item(Key={'order_id': '123'})
        # Merge or retry...
```

---

## Automatic Conflict Resolution

### Convergent Replicated Data Types (CRDTs)

```python
# CRDTs guarantee conflict-free merges

class GSet:
    """Grow-only set - automatically conflict-free"""

    def __init__(self):
        self.elements = set()

    def add(self, element):
        self.elements.add(element)

    def merge(self, other):
        """Union - always conflict-free"""
        self.elements |= other.elements

# No conflicts possible!
s1 = GSet()
s2 = GSet()

s1.add('A')
s2.add('B')

s1.merge(s2)  # {A, B}
s2.merge(s1)  # {B, A} = {A, B} (same result)
```

---

## User-Driven Resolution

### Interactive Resolution

```python
class DocumentEditor:
    """Collaborative editor with manual conflict resolution"""

    def __init__(self):
        self.content = ""
        self.versions = []  # List of (content, vector_clock)

    def edit(self, new_content, vector_clock):
        """Edit document"""
        self.versions.append((new_content, vector_clock))

    def get_conflicts(self):
        """Detect concurrent edits"""
        conflicts = []
        for i, (content1, vc1) in enumerate(self.versions):
            for j, (content2, vc2) in enumerate(self.versions[i+1:]):
                if self._concurrent(vc1, vc2):
                    conflicts.append((content1, content2))
        return conflicts

    def resolve_conflict_manually(self, conflicts, chosen_version):
        """User chooses resolution"""
        self.content = chosen_version
        self.versions = [(chosen_version, self._new_vector_clock())]
```

---

## Strategies Comparison

| Strategy | Data Loss | Complexity | User Action |
|----------|-----------|------------|-------------|
| **Last-Write-Wins** | ❌ Possible | ✅ Simple | None |
| **Multi-Value** | ✅ None | ⚠️ Medium | Required |
| **Semantic Merge** | ✅ None | ⚠️ Medium-High | None |
| **CRDTs** | ✅ None | ⚠️ Medium | None |
| **Manual** | ✅ None | ❌ Complex | Required |

---

## Best Practices

### 1. Choose Strategy Based on Use Case

```
✅ LWW: When latest value is correct (user status, config)
✅ Multi-value: When user must decide (editing documents)
✅ Semantic: When domain knowledge helps (shopping cart, calendar)
✅ CRDTs: When automatic merge possible (counters, sets)
```

### 2. Minimize Conflicts

```python
# Partition data to reduce conflicts
class PartitionedStore:
    """Partition by user to reduce conflicts"""

    def __init__(self):
        self.partitions = {}  # user_id → user's data

    def write(self, user_id, key, value):
        """Write to user's partition"""
        if user_id not in self.partitions:
            self.partitions[user_id] = {}
        self.partitions[user_id][key] = value

# Users rarely conflict with themselves
```

### 3. Detect Conflicts Early

```python
def detect_conflict(write_vector_clock, stored_vector_clock):
    """Detect if write conflicts with stored value"""
    # Concurrent if neither dominates
    neither_dominates = (
        not causally_before(write_vector_clock, stored_vector_clock) and
        not causally_before(stored_vector_clock, write_vector_clock)
    )
    return neither_dominates
```

---

## Related Skills

- `distributed-systems-crdt-fundamentals` - Conflict-free data types
- `distributed-systems-vector-clocks` - Causality tracking
- `distributed-systems-eventual-consistency` - Consistency models
- `distributed-systems-crdt-types` - Specific CRDT implementations

---

**Last Updated**: 2025-10-27
