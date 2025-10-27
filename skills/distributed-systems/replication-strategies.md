---
name: distributed-systems-replication-strategies
description: Data replication strategies including primary-backup, multi-primary, chain replication, and quorum-based replication
---

# Replication Strategies

**Scope**: Primary-backup, multi-primary, chain replication, quorum replication, trade-offs
**Lines**: ~270
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Designing distributed databases
- Planning high availability systems
- Understanding replication trade-offs
- Implementing data redundancy
- Building fault-tolerant services
- Optimizing read/write performance
- Understanding database internals
- Choosing replication topology

## Replication Strategies

### 1. Primary-Backup (Master-Slave)

**Approach**: One primary handles writes, backups handle reads

```
Client writes → Primary → Replicate → Backups
Client reads  → Primary or Backups
```

**Implementation**:
```python
class PrimaryBackupStore:
    """Primary-backup replication"""

    def __init__(self, is_primary=False):
        self.is_primary = is_primary
        self.data = {}
        self.backups = []

    def write(self, key, value):
        """Write (primary only)"""
        if not self.is_primary:
            raise NotPrimaryError()

        self.data[key] = value

        # Replicate to all backups
        for backup in self.backups:
            backup.replicate(key, value)

        return True

    def replicate(self, key, value):
        """Receive replication (backup only)"""
        if self.is_primary:
            return

        self.data[key] = value

    def read(self, key):
        """Read (any node)"""
        return self.data.get(key)

# Usage
primary = PrimaryBackupStore(is_primary=True)
backup1 = PrimaryBackupStore(is_primary=False)
backup2 = PrimaryBackupStore(is_primary=False)

primary.backups = [backup1, backup2]

primary.write('key1', 'value1')  # Replicated to backups
print(backup1.read('key1'))      # 'value1'
```

**Pros**:
- Simple
- Strong consistency possible
- Read scalability (read from backups)

**Cons**:
- Single point of failure (primary)
- Write bottleneck
- Replication lag (eventual consistency)

### 2. Multi-Primary (Multi-Master)

**Approach**: Multiple nodes accept writes, sync with each other

```
Client A writes → Primary A ←─┐
                      ↓        │ Sync
                  Primary B ←──┘
                      ↑
Client B writes ──────┘
```

**Implementation**:
```python
class MultiPrimaryStore:
    """Multi-primary with conflict resolution"""

    def __init__(self, node_id):
        self.node_id = node_id
        self.data = {}  # key → (value, vector_clock)
        self.peers = []

    def write(self, key, value):
        """Write to local node"""
        # Update with new vector clock
        vc = self._increment_vector_clock(key)
        self.data[key] = (value, vc)

        # Async replicate to peers
        for peer in self.peers:
            peer.replicate_async(key, value, vc)

    def replicate_async(self, key, value, vector_clock):
        """Receive replication from peer"""
        if key not in self.data:
            self.data[key] = (value, vector_clock)
        else:
            # Merge with conflict resolution
            self._merge(key, value, vector_clock)

    def _merge(self, key, new_value, new_vc):
        """Merge concurrent updates"""
        old_value, old_vc = self.data[key]

        if self._causally_before(old_vc, new_vc):
            # New value supersedes old
            self.data[key] = (new_value, new_vc)
        elif self._causally_before(new_vc, old_vc):
            # Old value supersedes new
            pass
        else:
            # Concurrent - keep both (siblings) or use LWW
            # For simplicity, use LWW based on node ID
            if new_vc > old_vc:  # Simplified comparison
                self.data[key] = (new_value, new_vc)
```

**Pros**:
- No single point of failure
- Write scalability
- Low latency (write locally)

**Cons**:
- Complex conflict resolution
- Potential inconsistency
- More coordination overhead

### 3. Chain Replication

**Approach**: Nodes in a chain, writes flow through chain

```
Client write → Head → Node 2 → ... → Tail → Ack to client
Client read  ← Tail (strongly consistent)
```

**Implementation**:
```python
class ChainNode:
    """Node in chain replication"""

    def __init__(self, node_id):
        self.node_id = node_id
        self.data = {}
        self.next_node = None
        self.is_tail = False

    def write(self, key, value):
        """Write (head only)"""
        self.data[key] = value

        if self.next_node:
            # Forward to next node
            self.next_node.write(key, value)
        elif self.is_tail:
            # Tail: acknowledge to client
            return True

    def read(self, key):
        """Read from tail only (strongly consistent)"""
        if not self.is_tail:
            raise MustReadFromTailError()

        return self.data.get(key)

# Setup chain
head = ChainNode('head')
middle = ChainNode('middle')
tail = ChainNode('tail')

head.next_node = middle
middle.next_node = tail
tail.is_tail = True

# Write flows through chain
head.write('key1', 'value1')

# Read from tail (has all committed writes)
print(tail.read('key1'))  # 'value1'
```

**Pros**:
- Strong consistency
- Simple recovery
- Efficient replication

**Cons**:
- Head is write bottleneck
- Higher write latency (chain)
- Tail failure delays reads

### 4. Quorum Replication

**Approach**: Write to W nodes, read from R nodes where W+R > N

```
Write: Ack when W replicas confirm
Read: Query R replicas, return latest
```

**Implementation**:
```python
class QuorumStore:
    """Quorum-based replication"""

    def __init__(self, nodes, w, r):
        self.nodes = nodes
        self.w = w  # Write quorum
        self.r = r  # Read quorum

    def write(self, key, value):
        """Write to W nodes"""
        version = self._generate_version()
        acks = 0

        for node in self.nodes:
            try:
                if node.put(key, value, version):
                    acks += 1
                if acks >= self.w:
                    return True
            except:
                continue

        raise QuorumNotMetError(f"Only {acks}/{self.w} acks")

    def read(self, key):
        """Read from R nodes"""
        responses = []

        for node in self.nodes:
            try:
                value, version = node.get(key)
                responses.append((value, version))
                if len(responses) >= self.r:
                    break
            except:
                continue

        if len(responses) < self.r:
            raise QuorumNotMetError(f"Only {len(responses)}/{self.r} responses")

        # Return value with highest version
        return max(responses, key=lambda x: x[1])[0]
```

**Pros**:
- Tunable consistency
- Fault tolerance (tolerates N-W or N-R failures)
- No single point of failure

**Cons**:
- More complex
- Potential conflicts
- Higher latency

---

## Synchronous vs Asynchronous

### Synchronous Replication

```python
def sync_write(primary, backups, key, value):
    """Wait for all backups to acknowledge"""
    primary.write(key, value)

    for backup in backups:
        backup.replicate(key, value)  # Blocks until complete

    return True  # All replicas updated
```

**Pros**: Strong consistency
**Cons**: Higher latency, availability depends on all nodes

### Asynchronous Replication

```python
import threading

def async_write(primary, backups, key, value):
    """Don't wait for backups"""
    primary.write(key, value)

    for backup in backups:
        threading.Thread(target=backup.replicate, args=(key, value)).start()

    return True  # Don't wait for replication
```

**Pros**: Low latency, high availability
**Cons**: Eventual consistency, data loss risk

---

## Replication Topologies

### Star (Primary-Backup)
```
        Primary
       /   |   \
  Backup Backup Backup
```

### Ring (Chain)
```
Node A → Node B → Node C → Node A
```

### Mesh (Multi-Primary)
```
Node A ←→ Node B
  ↕         ↕
Node C ←→ Node D
```

---

## Strategy Comparison

| Strategy | Consistency | Availability | Write Perf | Read Perf | Complexity |
|----------|-------------|--------------|------------|-----------|------------|
| **Primary-Backup** | Strong | Low | Low | Medium | Low |
| **Multi-Primary** | Eventual | High | High | High | High |
| **Chain** | Strong | Medium | Low | Medium | Medium |
| **Quorum** | Tunable | Medium | Medium | Medium | Medium |

---

## Real-World Examples

### MySQL Replication (Primary-Backup)
```sql
-- On primary
CHANGE MASTER TO
  MASTER_HOST='primary_host',
  MASTER_USER='repl_user',
  MASTER_PASSWORD='password';

START SLAVE;
```

### MongoDB Replica Set
```python
from pymongo import MongoClient

client = MongoClient('mongodb://host1,host2,host3/?replicaSet=myReplicaSet')

# Write to primary
db = client.mydb
db.collection.insert_one({'key': 'value'})

# Read from secondary
db.collection.find_one({'key': 'value'}, read_preference=ReadPreference.SECONDARY)
```

### Cassandra (Quorum)
```python
from cassandra.cluster import Cluster
from cassandra import ConsistencyLevel

cluster = Cluster()
session = cluster.connect('keyspace')

# Write to quorum
session.execute(query, consistency_level=ConsistencyLevel.QUORUM)
```

---

## Related Skills

- `distributed-systems-consensus-raft` - Consensus-based replication
- `distributed-systems-eventual-consistency` - Consistency models
- `distributed-systems-conflict-resolution` - Handling conflicts
- `distributed-systems-partitioning-sharding` - Data partitioning

---

**Last Updated**: 2025-10-27
