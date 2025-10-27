---
name: distributed-systems-cap-theorem
description: CAP theorem fundamentals, consistency vs availability trade-offs, and practical implications for distributed system design
---

# CAP Theorem

**Scope**: CAP theorem, consistency-availability trade-offs, partition tolerance, system design implications
**Lines**: ~290
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Designing distributed systems
- Choosing databases (SQL vs NoSQL)
- Understanding system trade-offs
- Planning for network partitions
- Evaluating consistency models
- Selecting replication strategies
- Making architecture decisions
- Troubleshooting distributed system issues

## Core Concepts

### The CAP Theorem

**Statement**: In a distributed system, you can only guarantee **two** of three properties:

```
C = Consistency
    All nodes see the same data at the same time

A = Availability
    Every request receives a response (success or failure)

P = Partition Tolerance
    System continues despite network partitions
```

**Reality**: Network partitions **will** happen, so you must choose between:
- **CP**: Consistency + Partition Tolerance (sacrifice availability)
- **AP**: Availability + Partition Tolerance (sacrifice consistency)

### Why CAP?

**Proof sketch**:
```
Given:
- Network partition splits nodes into two groups
- Client writes to one side
- Client reads from other side

If Consistent (C):
  → Must wait for partition to heal
  → System unavailable (violates A)

If Available (A):
  → Return potentially stale data
  → Not consistent (violates C)

Cannot have both C and A during partition (P)
```

---

## Consistency vs Availability

### CP Systems (Consistency + Partition Tolerance)

**Behavior during partition**: Reject requests to maintain consistency

**Examples**:
- Etcd (used by Kubernetes)
- Consul
- ZooKeeper
- HBase
- MongoDB (with majority writes)
- Traditional SQL databases

**When to choose**:
- Financial transactions
- Inventory management
- Configuration management
- Leader election
- Distributed locks

**Example**:
```python
# CP system: Returns error if can't guarantee consistency
try:
    balance = bank_db.get_balance(account_id)
    if balance >= amount:
        bank_db.withdraw(account_id, amount)  # Blocks during partition
except ConsistencyError:
    return "Service temporarily unavailable"  # Better than wrong data
```

### AP Systems (Availability + Partition Tolerance)

**Behavior during partition**: Always respond, may return stale data

**Examples**:
- Cassandra
- DynamoDB
- Riak
- CouchDB
- DNS
- Caching systems

**When to choose**:
- Social media feeds
- Product catalogs
- Analytics data
- Logging systems
- Caching layers
- Content delivery

**Example**:
```python
# AP system: Always returns data, may be stale
user_profile = cache.get(user_id)  # Returns even if stale
if user_profile is None:
    user_profile = eventual_consistency_db.get(user_id)  # Best effort
```

---

## Real-World Considerations

### PACELC Extension

**CAP is incomplete**: Only describes behavior **during** partitions

**PACELC** adds:
```
If Partition (P):
    Choose between Availability (A) and Consistency (C)
Else (E):
    Choose between Latency (L) and Consistency (C)

Full framework:
- PA/EL: Prioritize availability and low latency (Cassandra)
- PA/EC: Prioritize availability, then consistency (DynamoDB)
- PC/EL: Prioritize consistency, then low latency (MongoDB)
- PC/EC: Prioritize consistency (traditional RDBMS)
```

### Consistency Spectrum

**Not binary**:
```
Strong Consistency (CP)
├─ Linearizability
├─ Sequential Consistency
└─ Causal Consistency

Eventual Consistency (AP)
├─ Read Your Writes
├─ Monotonic Reads
└─ Eventual
```

---

## System Examples

### Example 1: Social Media Feed (AP)

```python
class SocialMediaFeed:
    """AP system: Always available, eventually consistent"""

    def post_update(self, user_id, content):
        # Write to multiple regions asynchronously
        for region in self.regions:
            region.write_async(user_id, content)  # Don't wait
        return {"status": "posted"}  # Immediate response

    def get_feed(self, user_id):
        # Read from nearest region
        region = self.get_nearest_region()
        posts = region.read(user_id)  # May be slightly stale
        return posts  # Always returns something
```

**Trade-off**: User might not see their post immediately on different device (eventual consistency), but system is always available.

### Example 2: Bank Account (CP)

```python
class BankAccount:
    """CP system: Strongly consistent, may be unavailable"""

    def transfer(self, from_account, to_account, amount):
        # Distributed transaction with 2PC
        transaction = self.begin_transaction()
        try:
            # Both operations must succeed or both fail
            transaction.debit(from_account, amount)
            transaction.credit(to_account, amount)
            transaction.commit()  # Blocks until confirmed on all nodes
            return {"status": "success"}
        except PartitionError:
            transaction.rollback()
            raise ServiceUnavailableError("Cannot guarantee consistency")

    def get_balance(self, account_id):
        # Read from majority quorum
        return self.read_with_quorum(account_id)  # Blocks if partition
```

**Trade-off**: System may become unavailable during network issues, but data is always correct.

### Example 3: Hybrid Approach

```python
class HybridSystem:
    """Different consistency for different data"""

    def write_user_profile(self, user_id, profile):
        # AP: Profile updates can be eventually consistent
        self.ap_store.write_async(user_id, profile)
        return {"status": "updated"}

    def charge_payment(self, user_id, amount):
        # CP: Payments must be strongly consistent
        try:
            result = self.cp_store.transaction(user_id, amount)
            return {"status": "charged"}
        except PartitionError:
            return {"status": "unavailable", "retry": True}
```

---

## Database Classification

### CP Databases

```
MongoDB (w=majority):
- Consistent reads from primary
- Blocks during partition
- Use for: Transactions, inventory

Etcd/Consul:
- Raft consensus
- Strong consistency
- Use for: Configuration, service discovery

HBase:
- Single master, consistent regions
- May be unavailable during failures
- Use for: Time-series, analytics requiring consistency
```

### AP Databases

```
Cassandra:
- Tunable consistency (default AP)
- Eventually consistent
- Use for: Time-series, logging, IoT

DynamoDB:
- Eventually consistent reads (default)
- Strongly consistent reads (optional, higher latency)
- Use for: User profiles, session data

Riak:
- Eventual consistency
- High availability
- Use for: Content storage, caching
```

---

## Tunable Consistency

### Cassandra Example

```python
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from cassandra import ConsistencyLevel

cluster = Cluster(['node1', 'node2', 'node3'])
session = cluster.connect('my_keyspace')

# AP: Eventually consistent (fast)
statement = SimpleStatement(
    "SELECT * FROM users WHERE user_id = %s",
    consistency_level=ConsistencyLevel.ONE  # Read from any single node
)

# CP: Strongly consistent (slower)
statement = SimpleStatement(
    "SELECT * FROM users WHERE user_id = %s",
    consistency_level=ConsistencyLevel.QUORUM  # Read from majority
)

# Per-query choice based on use case
```

---

## Decision Framework

### Choose CP When:

```
✅ Correctness is critical (financial, inventory)
✅ Can tolerate downtime
✅ Data conflicts must be prevented
✅ Transactions required
✅ Regulated industry (banking, healthcare)
```

### Choose AP When:

```
✅ Availability is critical (user-facing)
✅ Can tolerate stale reads
✅ Conflicts can be resolved later
✅ High write throughput needed
✅ Global distribution required
```

---

## Common Misconceptions

### Misconception 1: "CAP means pick 2 of 3"

**Wrong**: Network partitions happen, so it's really "CP or AP"

**Correct**: Choose consistency or availability **during** partitions

### Misconception 2: "NoSQL = AP, SQL = CP"

**Wrong**: Many NoSQL databases offer tunable consistency

**Examples**:
- Cassandra: Can be CP with QUORUM consistency
- MongoDB: Can be AP with w=1 writes
- PostgreSQL: Can be AP with async replication

### Misconception 3: "AP means no consistency"

**Wrong**: AP means eventual consistency, not no consistency

**Clarification**: Updates propagate to all nodes, just not immediately

---

## Testing CAP Properties

### Partition Simulation

```python
import subprocess
import time

def simulate_partition(node_ips):
    """Block network traffic between nodes"""
    for ip in node_ips:
        subprocess.run([
            'iptables', '-A', 'INPUT', '-s', ip, '-j', 'DROP'
        ])

def test_ap_system():
    """Test that system remains available during partition"""
    simulate_partition(['192.168.1.2'])

    # Should still respond (maybe stale)
    response = api.get('/data')
    assert response.status_code == 200  # Available

def test_cp_system():
    """Test that system maintains consistency during partition"""
    simulate_partition(['192.168.1.2'])

    # Should refuse to serve potentially inconsistent data
    response = api.get('/data')
    assert response.status_code in [503, 500]  # Unavailable but consistent
```

---

## Related Skills

- `distributed-systems-eventual-consistency` - Consistency models
- `distributed-systems-replication-strategies` - Data replication
- `distributed-systems-consensus-raft` - Consensus algorithms
- `distributed-systems-conflict-resolution` - Handling conflicts

---

**Last Updated**: 2025-10-27
