---
name: distributed-systems-partitioning-sharding
description: Data partitioning and sharding strategies including hash-based, range-based, consistent hashing, and rebalancing
---

# Partitioning and Sharding

**Scope**: Partitioning strategies, consistent hashing, rebalancing, hotspots, practical implementations
**Lines**: ~280
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Scaling beyond single node
- Distributing data across nodes
- Load balancing requests
- Understanding NoSQL databases
- Implementing caching layers
- Handling large datasets
- Optimizing query performance
- Planning database architecture

## Core Concepts

### Why Partition?

```
Problem: Single node can't handle all data/load

Solution: Split data across multiple nodes

Benefits:
✅ Scalability (more nodes = more capacity)
✅ Performance (parallel queries)
✅ Fault isolation (failure affects subset)
```

### Partitioning vs Sharding

**Partitioning**: General term for splitting data
**Sharding**: Partitioning in distributed databases

*Often used interchangeably*

---

## Partitioning Strategies

### 1. Hash Partitioning

**Approach**: Hash key to determine partition

```python
import hashlib

class HashPartitioner:
    """Hash-based partitioning"""

    def __init__(self, num_partitions):
        self.num_partitions = num_partitions
        self.partitions = [[] for _ in range(num_partitions)]

    def get_partition(self, key):
        """Determine partition for key"""
        hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return hash_val % self.num_partitions

    def write(self, key, value):
        """Write to appropriate partition"""
        partition_id = self.get_partition(key)
        self.partitions[partition_id].append((key, value))

    def read(self, key):
        """Read from appropriate partition"""
        partition_id = self.get_partition(key)
        for k, v in self.partitions[partition_id]:
            if k == key:
                return v
        return None

# Usage
partitioner = HashPartitioner(num_partitions=4)
partitioner.write('user:123', {'name': 'Alice'})
partitioner.write('user:456', {'name': 'Bob'})

print(partitioner.read('user:123'))  # {'name': 'Alice'}
```

**Pros**:
- Even distribution
- Simple implementation

**Cons**:
- Range queries difficult
- Adding nodes requires rehashing

### 2. Range Partitioning

**Approach**: Assign key ranges to partitions

```python
class RangePartitioner:
    """Range-based partitioning"""

    def __init__(self, ranges):
        # ranges = [(min, max, partition_id), ...]
        self.ranges = sorted(ranges, key=lambda x: x[0])
        self.partitions = {}

    def get_partition(self, key):
        """Find partition for key"""
        for min_key, max_key, partition_id in self.ranges:
            if min_key <= key < max_key:
                return partition_id
        raise KeyError(f"No partition for key {key}")

    def range_query(self, start_key, end_key):
        """Query range of keys"""
        results = []

        # Find all relevant partitions
        for min_key, max_key, partition_id in self.ranges:
            if max_key >= start_key and min_key < end_key:
                # This partition contains relevant data
                results.extend(self._query_partition(partition_id, start_key, end_key))

        return results

# Usage
partitioner = RangePartitioner([
    ('A', 'G', 0),  # Partition 0: A-F
    ('G', 'M', 1),  # Partition 1: G-L
    ('M', 'S', 2),  # Partition 2: M-R
    ('S', 'Z', 3),  # Partition 3: S-Z
])
```

**Pros**:
- Efficient range queries
- Predictable data location

**Cons**:
- Risk of hotspots (uneven distribution)
- Manual range management

### 3. Consistent Hashing

**Approach**: Hash keys and nodes onto ring, walk clockwise

```python
import hashlib
import bisect

class ConsistentHashing:
    """Consistent hashing with virtual nodes"""

    def __init__(self, num_virtual_nodes=150):
        self.num_virtual_nodes = num_virtual_nodes
        self.ring = []  # Sorted list of (hash, node_id)
        self.nodes = set()

    def _hash(self, key):
        """Hash key to position on ring"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node_id):
        """Add node to ring"""
        self.nodes.add(node_id)

        # Add virtual nodes
        for i in range(self.num_virtual_nodes):
            virtual_key = f"{node_id}:{i}"
            hash_val = self._hash(virtual_key)
            bisect.insort(self.ring, (hash_val, node_id))

    def remove_node(self, node_id):
        """Remove node from ring"""
        self.nodes.discard(node_id)

        # Remove virtual nodes
        self.ring = [(h, n) for h, n in self.ring if n != node_id]

    def get_node(self, key):
        """Find node responsible for key"""
        if not self.ring:
            return None

        hash_val = self._hash(key)

        # Find first node clockwise
        idx = bisect.bisect_right(self.ring, (hash_val, ''))
        if idx == len(self.ring):
            idx = 0

        return self.ring[idx][1]

# Usage
ch = ConsistentHashing()
ch.add_node('node1')
ch.add_node('node2')
ch.add_node('node3')

print(ch.get_node('user:123'))  # node2
print(ch.get_node('user:456'))  # node1

# Add node - minimal keys moved
ch.add_node('node4')
```

**Pros**:
- Minimal key movement when adding/removing nodes
- Even distribution (with virtual nodes)

**Cons**:
- More complex
- Range queries difficult

---

## Handling Hotspots

### Problem: Uneven Load

```
Celebrity effect:
User "celebrity" has 10M followers
All queries for "celebrity" → Same partition → Overload
```

### Solution 1: Split Hot Partition

```python
class AdaptivePartitioner:
    """Split partitions that become hot"""

    def __init__(self):
        self.partitions = {}
        self.access_counts = {}

    def access(self, key):
        self.access_counts[key] = self.access_counts.get(key, 0) + 1

        # Split if too hot
        if self.access_counts[key] > 10000:
            self._split_hot_key(key)

    def _split_hot_key(self, key):
        """Replicate hot key to multiple partitions"""
        # Create replicas
        for i in range(3):
            replica_key = f"{key}:replica:{i}"
            self.partitions[replica_key] = self.partitions[key]
```

### Solution 2: Add Randomization

```python
def read_with_randomization(key):
    """Read from random replica of hot key"""
    replicas = get_replicas(key)
    replica = random.choice(replicas)
    return replica.read(key)
```

---

## Rebalancing

### When to Rebalance

```
Triggers:
- Node added (scale out)
- Node removed (failure or scale down)
- Load imbalance detected
```

### Strategies

**1. Stop-the-World** (simple but downtime):
```python
def rebalance_stop_the_world(old_partitions, new_num_partitions):
    """Rebalance with downtime"""
    # 1. Stop writes
    stop_writes()

    # 2. Redistribute data
    new_partitions = redistribute(old_partitions, new_num_partitions)

    # 3. Resume writes
    resume_writes()

    return new_partitions
```

**2. Online Rebalancing** (no downtime):
```python
class OnlineRebalancer:
    """Rebalance without downtime"""

    def rebalance(self, target_partitions):
        # 1. Create new partitions (in parallel with old)
        new_partitions = self._create_partitions(target_partitions)

        # 2. Start dual-writing (to both old and new)
        self._enable_dual_write()

        # 3. Copy existing data to new partitions
        self._copy_data(new_partitions)

        # 4. Switch reads to new partitions
        self._switch_reads(new_partitions)

        # 5. Stop dual-writing, remove old partitions
        self._disable_dual_write()
        self._remove_old_partitions()
```

---

## Secondary Indexes

### Problem: Queries by Non-Partition Key

```
Partition by user_id, but want to query by email
```

### Solution 1: Local Index (Scatter-Gather)

```python
class LocalIndexPartitioner:
    """Local secondary index per partition"""

    def __init__(self, num_partitions):
        self.partitions = [
            {'data': {}, 'email_index': {}}
            for _ in range(num_partitions)
        ]

    def write(self, user_id, email, data):
        """Write with local index"""
        partition_id = hash(user_id) % len(self.partitions)
        partition = self.partitions[partition_id]

        partition['data'][user_id] = data
        partition['email_index'][email] = user_id

    def query_by_email(self, email):
        """Scatter-gather across all partitions"""
        for partition in self.partitions:
            if email in partition['email_index']:
                user_id = partition['email_index'][email]
                return partition['data'][user_id]

        return None
```

### Solution 2: Global Index

```python
class GlobalIndexPartitioner:
    """Separate global secondary index"""

    def __init__(self, num_partitions):
        self.data_partitions = [{} for _ in range(num_partitions)]
        self.global_email_index = {}  # email → (partition_id, user_id)

    def write(self, user_id, email, data):
        """Write to data partition and global index"""
        partition_id = hash(user_id) % len(self.data_partitions)
        self.data_partitions[partition_id][user_id] = data
        self.global_email_index[email] = (partition_id, user_id)

    def query_by_email(self, email):
        """Direct lookup via global index"""
        if email in self.global_email_index:
            partition_id, user_id = self.global_email_index[email]
            return self.data_partitions[partition_id][user_id]

        return None
```

---

## Real-World Examples

### MongoDB Sharding
```javascript
// Enable sharding
sh.enableSharding("mydb")

// Shard collection by user_id (hash)
sh.shardCollection("mydb.users", {user_id: "hashed"})

// Or by range
sh.shardCollection("mydb.orders", {order_date: 1})
```

### Cassandra Partitioning
```sql
-- Partition key determines data distribution
CREATE TABLE users (
    user_id UUID,
    name TEXT,
    PRIMARY KEY (user_id)  -- Partition key
);

-- Composite partition key
CREATE TABLE user_posts (
    user_id UUID,
    post_date DATE,
    post_id UUID,
    content TEXT,
    PRIMARY KEY ((user_id, post_date), post_id)  -- Partition key: (user_id, post_date)
);
```

---

## Strategy Comparison

| Strategy | Distribution | Range Queries | Rebalancing | Hotspots |
|----------|--------------|---------------|-------------|----------|
| **Hash** | ✅ Even | ❌ Hard | ⚠️ Rehash all | ✅ Rare |
| **Range** | ⚠️ Uneven | ✅ Easy | ✅ Easy | ❌ Common |
| **Consistent Hash** | ✅ Even | ❌ Hard | ✅ Minimal | ✅ Rare |

---

## Related Skills

- `distributed-systems-replication-strategies` - Data replication
- `distributed-systems-consensus-raft` - Consensus for configuration
- `distributed-systems-eventual-consistency` - Consistency models
- `distributed-systems-distributed-locks` - Coordination primitives

---

**Last Updated**: 2025-10-27
