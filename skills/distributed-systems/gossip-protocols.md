---
name: distributed-systems-gossip-protocols
description: Gossip protocols for disseminating information, failure detection, and eventual consistency in large-scale distributed systems
---

# Gossip Protocols

**Scope**: Epidemic protocols, rumor spreading, failure detection, membership, eventual consistency
**Lines**: ~210
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building large-scale distributed systems
- Implementing failure detection
- Disseminating cluster state
- Understanding Cassandra, Redis Cluster
- Implementing membership protocols
- Broadcasting updates efficiently
- Building peer-to-peer systems
- Handling network partitions

## Core Concepts

### Gossip Overview

**Idea**: Nodes periodically exchange information with random peers (like spreading rumors)

```
Node A knows update → Tells random peers (B, C)
B and C → Each tell random peers
Eventually all nodes know update
```

**Properties**:
- Scalable (O(log N) rounds)
- Fault-tolerant (no single point of failure)
- Eventually consistent
- Simple implementation

---

## Gossip Algorithms

### 1. Rumor Spreading (Push)

```python
import random
import time

class GossipNode:
    """Node implementing push-based gossip"""

    def __init__(self, node_id, all_nodes):
        self.node_id = node_id
        self.all_nodes = all_nodes
        self.data = {}  # key → (value, version)
        self.peers = [n for n in all_nodes if n != self]

    def update_local(self, key, value):
        """Update local data"""
        version = time.time()
        self.data[key] = (value, version)

        # Gossip to random peers
        self.gossip_update(key, value, version)

    def gossip_update(self, key, value, version):
        """Push update to random peers"""
        # Select random subset of peers (fanout=3)
        fanout = min(3, len(self.peers))
        peers_to_notify = random.sample(self.peers, fanout)

        for peer in peers_to_notify:
            peer.receive_gossip(key, value, version, self.node_id)

    def receive_gossip(self, key, value, version, sender_id):
        """Receive gossip from peer"""
        if key not in self.data or version > self.data[key][1]:
            # New or newer version - update and re-gossip
            self.data[key] = (value, version)
            self.gossip_update(key, value, version)

# Usage
nodes = [GossipNode(i, range(10)) for i in range(10)]

# Update on one node - gossips to others
nodes[0].update_local('config', 'value')

# After a few rounds, all nodes have update
```

### 2. Anti-Entropy (Pull/Push-Pull)

```python
class AntiEntropyNode:
    """Node with periodic full state synchronization"""

    def __init__(self, node_id, all_nodes):
        self.node_id = node_id
        self.all_nodes = all_nodes
        self.data = {}  # key → (value, version)

    def periodic_sync(self):
        """Periodically sync with random peer"""
        while True:
            time.sleep(5)  # Every 5 seconds

            peer = random.choice([n for n in self.all_nodes if n != self])
            self.sync_with_peer(peer)

    def sync_with_peer(self, peer):
        """Full state synchronization with peer"""
        # Get peer's data
        peer_data = peer.get_all_data()

        # Merge data (element-wise max by version)
        for key, (value, version) in peer_data.items():
            if key not in self.data or version > self.data[key][1]:
                self.data[key] = (value, version)

        # Send our data to peer
        for key, (value, version) in self.data.items():
            if key not in peer_data or version > peer_data[key][1]:
                peer.update_from_sync(key, value, version)

    def get_all_data(self):
        return self.data.copy()

    def update_from_sync(self, key, value, version):
        if key not in self.data or version > self.data[key][1]:
            self.data[key] = (value, version)
```

---

## Failure Detection

### SWIM Protocol

```python
import threading

class SWIMNode:
    """Scalable Weakly-consistent Infection-style Process Group Membership"""

    def __init__(self, node_id, all_nodes):
        self.node_id = node_id
        self.all_nodes = all_nodes
        self.alive_nodes = set(all_nodes)
        self.suspected_nodes = set()

    def periodic_ping(self):
        """Periodically ping random node"""
        while True:
            time.sleep(1)

            # Select random node
            target = random.choice(list(self.alive_nodes - {self.node_id}))

            # Direct ping
            if not self.ping(target, timeout=1):
                # Indirect ping through others
                if not self.indirect_ping(target):
                    # Mark as suspected
                    self.suspect_node(target)

    def ping(self, target, timeout=1):
        """Ping target node directly"""
        try:
            response = target.receive_ping(self.node_id)
            return response == "ACK"
        except:
            return False

    def indirect_ping(self, target):
        """Ping target through k random nodes"""
        k = min(3, len(self.alive_nodes) - 2)
        proxies = random.sample(list(self.alive_nodes - {self.node_id, target}), k)

        for proxy in proxies:
            if proxy.ping_on_behalf(target):
                return True

        return False

    def suspect_node(self, node):
        """Mark node as suspected (gossip suspicion)"""
        self.suspected_nodes.add(node)
        self.gossip_suspicion(node)

    def receive_ping(self, sender_id):
        """Respond to ping"""
        return "ACK"

# Nodes detect failures within a few protocol periods
```

---

## Membership Management

### Gossip-Based Membership

```python
class MembershipGossip:
    """Distributed membership using gossip"""

    def __init__(self, node_id):
        self.node_id = node_id
        self.members = {}  # node_id → (heartbeat, timestamp)

    def update_heartbeat(self):
        """Increment own heartbeat"""
        if self.node_id not in self.members:
            self.members[self.node_id] = (0, time.time())

        heartbeat, _ = self.members[self.node_id]
        self.members[self.node_id] = (heartbeat + 1, time.time())

        # Gossip to peers
        self.gossip_membership()

    def gossip_membership(self):
        """Send membership list to random peers"""
        # Send to random subset
        pass

    def receive_membership(self, peer_members):
        """Merge membership from peer"""
        for node_id, (heartbeat, timestamp) in peer_members.items():
            if node_id not in self.members:
                # New member
                self.members[node_id] = (heartbeat, timestamp)
            else:
                my_heartbeat, my_timestamp = self.members[node_id]

                if heartbeat > my_heartbeat:
                    # More recent heartbeat
                    self.members[node_id] = (heartbeat, timestamp)

    def detect_failures(self, timeout=30):
        """Detect failed nodes (no heartbeat updates)"""
        now = time.time()
        failed = []

        for node_id, (heartbeat, timestamp) in self.members.items():
            if now - timestamp > timeout:
                failed.append(node_id)

        return failed
```

---

## Convergence Properties

### Epidemic Spreading

```
Round 1: 1 node knows
Round 2: 3 nodes know (1 + 2 new)
Round 3: 9 nodes know (3 + 6 new)
...
Round log(N): All N nodes know

Convergence: O(log N) rounds
```

### Guarantees

```
Eventual delivery: All non-faulty nodes eventually receive update
Reliability: High probability of delivery (adjustable with fanout)
Scalability: Communication overhead O(N log N) total
```

---

## Real-World Examples

### Cassandra Gossip

```
Every second:
1. Node picks random peer
2. Exchanges state (nodes, tokens, schema)
3. Updates local view

State includes:
- Live nodes
- Dead/suspected nodes
- Token ownership
- Schema versions
```

### Redis Cluster

```
Every second:
1. Node sends PING to random nodes
2. Receives PONG with cluster state
3. Detects node failures
4. Gossips slot ownership

Failure detection: No PONG → node marked as FAIL
```

---

## Optimizations

### 1. Bounded Fanout

```python
# Limit gossip fanout to control overhead
FANOUT = 3  # Each node gossips to 3 peers

# Achieves O(log N) convergence with O(N) messages per round
```

### 2. Damping

```python
class DampedGossip:
    """Stop gossiping old news"""

    def __init__(self):
        self.gossip_count = {}  # update_id → count

    def should_gossip(self, update_id):
        count = self.gossip_count.get(update_id, 0)
        # Stop after k rounds
        return count < 5

    def gossip(self, update_id):
        if self.should_gossip(update_id):
            # Gossip
            self.gossip_count[update_id] = self.gossip_count.get(update_id, 0) + 1
```

### 3. Prioritization

```python
# Gossip recent/important updates more frequently
# Gossip old updates less frequently
```

---

## When to Use Gossip

```
✅ Good for:
- Large-scale systems (>100 nodes)
- Eventually consistent data
- Failure detection
- Cluster membership
- Configuration distribution

❌ Not good for:
- Strong consistency required
- Low latency critical
- Small clusters (<10 nodes)
- Ordered delivery required
```

---

## Related Skills

- `distributed-systems-eventual-consistency` - Consistency models
- `distributed-systems-crdt-fundamentals` - Conflict-free updates
- `distributed-systems-replication-strategies` - Data replication

---

**Last Updated**: 2025-10-27
