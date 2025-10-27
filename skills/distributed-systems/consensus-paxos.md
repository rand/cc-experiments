---
name: distributed-systems-consensus-paxos
description: Paxos consensus algorithm including Basic Paxos, Multi-Paxos, roles, phases, and practical implementations
---

# Paxos Consensus

**Scope**: Paxos algorithm, Basic Paxos, Multi-Paxos, roles, phases, practical implementations
**Lines**: ~330
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Understanding consensus fundamentals
- Implementing distributed agreement
- Building fault-tolerant systems
- Understanding Google Chubby, Spanner
- Comparing with RAFT
- Studying distributed systems theory
- Building replicated state machines
- Designing coordination services

## Core Concepts

### Paxos Overview

**Goal**: Achieve agreement on single value among distributed nodes despite failures

**Key properties**:
- Safety: Only one value chosen
- Liveness: Eventually chooses value (if majority available)
- Fault tolerance: Tolerates f failures with 2f+1 nodes

**Roles** (nodes can have multiple roles):
```
Proposer  → Proposes values
Acceptor  → Votes on proposals
Learner   → Learns chosen value
```

---

## Basic Paxos

### Two Phases

**Phase 1: Prepare**
```
Proposer → Acceptors: PREPARE(n)
Acceptors → Proposer: PROMISE(n, accepted_value)
```

**Phase 2: Accept**
```
Proposer → Acceptors: ACCEPT(n, value)
Acceptors → Learners: ACCEPTED(n, value)
```

### Algorithm Details

```python
class Proposer:
    def __init__(self, node_id, acceptors):
        self.node_id = node_id
        self.acceptors = acceptors
        self.proposal_number = 0

    def propose(self, value):
        """Propose a value using Basic Paxos"""
        # Generate unique proposal number (node_id + counter)
        self.proposal_number += 1
        n = (self.proposal_number, self.node_id)

        # Phase 1: Prepare
        promises = []
        for acceptor in self.acceptors:
            response = acceptor.prepare(n)
            if response:
                promises.append(response)

        # Need majority
        if len(promises) < len(self.acceptors) // 2 + 1:
            return None  # Failed to get majority

        # Use highest-numbered accepted value, or our value if none
        accepted_values = [p for p in promises if p.accepted_value is not None]
        if accepted_values:
            # Must use previously accepted value
            value = max(accepted_values, key=lambda x: x.accepted_n).accepted_value

        # Phase 2: Accept
        accepts = 0
        for acceptor in self.acceptors:
            if acceptor.accept(n, value):
                accepts += 1

        # Chosen if majority accepted
        if accepts >= len(self.acceptors) // 2 + 1:
            return value

        return None  # Failed


class Acceptor:
    def __init__(self):
        self.promised_n = None      # Highest n seen in prepare
        self.accepted_n = None       # Highest n accepted
        self.accepted_value = None   # Value accepted with accepted_n

    def prepare(self, n):
        """Phase 1: Prepare"""
        # Promise not to accept proposals < n
        if self.promised_n is None or n > self.promised_n:
            self.promised_n = n
            return Promise(n, self.accepted_n, self.accepted_value)
        return None  # Reject (n too low)

    def accept(self, n, value):
        """Phase 2: Accept"""
        # Accept if n >= promised_n
        if self.promised_n is None or n >= self.promised_n:
            self.promised_n = n
            self.accepted_n = n
            self.accepted_value = value
            return True
        return False  # Reject (n < promised_n)


class Promise:
    def __init__(self, n, accepted_n, accepted_value):
        self.n = n
        self.accepted_n = accepted_n
        self.accepted_value = accepted_value
```

---

## Multi-Paxos

### Optimization for Multiple Values

**Basic Paxos**: Requires two round-trips per value (expensive!)

**Multi-Paxos**: Elect stable leader, skip Phase 1 for subsequent proposals

```python
class MultiPaxos:
    def __init__(self, nodes):
        self.nodes = nodes
        self.leader = None
        self.log = []  # Sequence of chosen values

    def elect_leader(self):
        """One-time leader election using Basic Paxos"""
        self.leader = self.run_basic_paxos_for_leader()

    def propose_value(self, value):
        """Leader proposes value (skips Phase 1)"""
        if not self.leader or self.leader != self.node_id:
            raise NotLeaderError()

        # Leader can skip Phase 1 (already has promises)
        # Phase 2 only: Accept
        log_index = len(self.log)
        accepts = 0
        for acceptor in self.acceptors:
            if acceptor.accept_at_index(log_index, self.leader_n, value):
                accepts += 1

        if accepts >= len(self.acceptors) // 2 + 1:
            self.log.append(value)
            return True

        return False
```

---

## Paxos vs RAFT

| Feature | Paxos | RAFT |
|---------|-------|------|
| **Understandability** | Complex, hard to grasp | Designed to be understandable |
| **Leader** | Optional (Multi-Paxos adds leader) | Always has leader |
| **Log structure** | Can have gaps | Contiguous log |
| **Membership changes** | Challenging | Built-in mechanism |
| **Implementation** | Many variations | Canonical algorithm |
| **Performance** | Comparable | Comparable |
| **Adoption** | Google (Chubby, Spanner) | etcd, Consul, more common |

---

## Real-World Implementations

### Google Chubby

**Description**: Distributed lock service using Paxos

```python
# Conceptual Chubby API
class Chubby:
    def __init__(self, paxos_cluster):
        self.paxos = paxos_cluster

    def acquire_lock(self, lock_name, timeout=60):
        """Acquire distributed lock"""
        # Use Paxos to agree on lock holder
        value = {
            'holder': self.client_id,
            'timestamp': time.time(),
            'timeout': timeout
        }

        success = self.paxos.propose(f'/locks/{lock_name}', value)
        return success

    def release_lock(self, lock_name):
        """Release distributed lock"""
        self.paxos.propose(f'/locks/{lock_name}', None)
```

### Google Spanner

**Description**: Globally-distributed database using Paxos for replication

**Paxos groups**: Each shard replicated via Paxos
```
Shard 1:  Paxos(Replica A, B, C)
Shard 2:  Paxos(Replica D, E, F)
Shard 3:  Paxos(Replica G, H, I)
```

**Transactions**: Two-phase commit across Paxos groups

---

## Practical Implementation

### Python Example

```python
import time
import random
from typing import Optional, Tuple

class PaxosNode:
    """Complete Paxos node (proposer + acceptor + learner)"""

    def __init__(self, node_id, all_nodes):
        self.node_id = node_id
        self.all_nodes = all_nodes

        # Proposer state
        self.proposal_id = 0

        # Acceptor state
        self.promised_id = None
        self.accepted_id = None
        self.accepted_value = None

        # Learner state
        self.learned_value = None

    def generate_proposal_id(self):
        """Generate unique, monotonically increasing proposal ID"""
        self.proposal_id += 1
        return (self.proposal_id, self.node_id)

    def propose(self, value):
        """Propose a value (Phase 1 + Phase 2)"""
        proposal_id = self.generate_proposal_id()

        # Phase 1: Prepare
        promises = []
        for node in self.all_nodes:
            response = node.receive_prepare(proposal_id)
            if response:
                promises.append(response)

        # Check majority
        if len(promises) < len(self.all_nodes) // 2 + 1:
            return False  # No majority, retry later

        # Determine value to propose
        highest_accepted = max(
            [p for p in promises if p[1] is not None],
            key=lambda x: x[0],
            default=(None, None)
        )

        if highest_accepted[1] is not None:
            value = highest_accepted[1]  # Must use existing value

        # Phase 2: Accept
        accepts = 0
        for node in self.all_nodes:
            if node.receive_accept(proposal_id, value):
                accepts += 1
                # Learner: Learn value when accepted
                node.learned_value = value

        return accepts >= len(self.all_nodes) // 2 + 1

    def receive_prepare(self, proposal_id):
        """Acceptor: Receive prepare request"""
        if self.promised_id is None or proposal_id > self.promised_id:
            self.promised_id = proposal_id
            return (self.accepted_id, self.accepted_value)
        return None

    def receive_accept(self, proposal_id, value):
        """Acceptor: Receive accept request"""
        if self.promised_id is None or proposal_id >= self.promised_id:
            self.promised_id = proposal_id
            self.accepted_id = proposal_id
            self.accepted_value = value
            return True
        return False

# Usage
nodes = [PaxosNode(i, []) for i in range(5)]
for node in nodes:
    node.all_nodes = nodes

# Multiple proposers competing
nodes[0].propose("value_A")
nodes[1].propose("value_B")

# Eventually one value wins
for node in nodes:
    print(f"Node {node.node_id} learned: {node.learned_value}")
```

---

## Common Issues

### Issue 1: Dueling Proposers

**Problem**: Two proposers keep interfering with each other

```
Proposer A: PREPARE(1)
Proposer B: PREPARE(2)  ← Invalidates A's prepare
Proposer A: PREPARE(3)  ← Invalidates B's prepare
Proposer B: PREPARE(4)  ← Invalidates A's prepare
... (infinite loop)
```

**Solution**: Randomized backoff or leader election (Multi-Paxos)

```python
def propose_with_backoff(self, value):
    """Propose with exponential backoff"""
    backoff = 0.1
    max_attempts = 10

    for attempt in range(max_attempts):
        if self.propose(value):
            return True

        # Exponential backoff with jitter
        time.sleep(backoff * (1 + random.random()))
        backoff = min(backoff * 2, 10)

    return False
```

### Issue 2: Learning the Chosen Value

**Problem**: Acceptors don't know when value is chosen

**Solutions**:

**Option 1**: Proposer notifies learners after Phase 2
```python
def notify_learners(self, value):
    for learner in self.learners:
        learner.learn(value)
```

**Option 2**: Acceptors notify distinguished learner
```python
def receive_accept(self, proposal_id, value):
    if self.accept_proposal(proposal_id, value):
        self.distinguished_learner.notify_accepted(proposal_id, value)
```

**Option 3**: Learners track acceptances
```python
class Learner:
    def __init__(self, quorum_size):
        self.acceptances = {}  # proposal_id → {acceptor_ids}
        self.quorum_size = quorum_size

    def notify_accepted(self, acceptor_id, proposal_id, value):
        if proposal_id not in self.acceptances:
            self.acceptances[proposal_id] = (value, set())

        self.acceptances[proposal_id][1].add(acceptor_id)

        if len(self.acceptances[proposal_id][1]) >= self.quorum_size:
            self.learned_value = value
```

---

## Testing Paxos

```python
import unittest

class TestPaxos(unittest.TestCase):
    def test_single_proposer(self):
        """Single proposer should succeed"""
        nodes = [PaxosNode(i, []) for i in range(5)]
        for node in nodes:
            node.all_nodes = nodes

        result = nodes[0].propose("value_A")
        self.assertTrue(result)

        # All nodes should learn the value
        for node in nodes:
            self.assertEqual(node.learned_value, "value_A")

    def test_concurrent_proposers(self):
        """Concurrent proposers should reach consensus"""
        nodes = [PaxosNode(i, []) for i in range(5)]
        for node in nodes:
            node.all_nodes = nodes

        # Multiple proposers
        nodes[0].propose("value_A")
        nodes[1].propose("value_B")

        # All nodes should agree (on one of the values)
        learned_values = {node.learned_value for node in nodes if node.learned_value}
        self.assertEqual(len(learned_values), 1)  # All same

    def test_node_failure(self):
        """Should tolerate minority node failures"""
        nodes = [PaxosNode(i, []) for i in range(5)]
        for node in nodes:
            node.all_nodes = nodes

        # Simulate 2 nodes failing (3/5 still available)
        available_nodes = nodes[:3]

        # Proposal should still succeed with majority
        result = available_nodes[0].propose("value_A")
        self.assertTrue(result)
```

---

## Performance Optimizations

### 1. Fast Paxos

**Optimization**: Skip proposer, clients send directly to acceptors

**Benefit**: One fewer network round-trip when no conflicts

### 2. Pipelining

**Optimization**: Proposer sends multiple proposals without waiting

**Benefit**: Higher throughput

### 3. Batching

```python
def propose_batch(self, values):
    """Propose multiple values in single Paxos instance"""
    batch_value = {
        'type': 'batch',
        'values': values
    }
    return self.propose(batch_value)
```

---

## Related Skills

- `distributed-systems-consensus-raft` - Alternative consensus algorithm
- `distributed-systems-leader-election` - Leader election patterns
- `distributed-systems-distributed-transactions` - Transaction protocols
- `distributed-systems-replication-strategies` - Data replication

---

**Last Updated**: 2025-10-27
