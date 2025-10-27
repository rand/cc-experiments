# Distributed Systems Skills

## Category Overview

**Total Skills**: 17
**Category**: distributed-systems

## Skills in This Category

### cap-theorem.md
**Description**: CAP theorem fundamentals, consistency vs availability trade-offs, and practical implications for distributed system design

**Load this skill**:
```bash
cat skills/distributed-systems/cap-theorem.md
```

---

### consensus-raft.md
**Description**: RAFT consensus algorithm including leader election, log replication, safety guarantees, and implementation patterns

**Load this skill**:
```bash
cat skills/distributed-systems/consensus-raft.md
```

---

### consensus-paxos.md
**Description**: Paxos consensus algorithm including Basic Paxos, Multi-Paxos, roles, phases, and practical implementations

**Load this skill**:
```bash
cat skills/distributed-systems/consensus-paxos.md
```

---

### crdt-fundamentals.md
**Description**: Conflict-free Replicated Data Types (CRDTs) fundamentals including convergence, commutativity, and basic CRDT operations

**Load this skill**:
```bash
cat skills/distributed-systems/crdt-fundamentals.md
```

---

### crdt-types.md
**Description**: Specific CRDT implementations including LWW-Register, OR-Set, RGA, and collaborative text editing CRDTs

**Load this skill**:
```bash
cat skills/distributed-systems/crdt-types.md
```

---

### dotted-version-vectors.md
**Description**: Dotted version vectors for efficient sibling management, compact causality tracking, reducing metadata overhead compared to pure vector clocks

**Load this skill**:
```bash
cat skills/distributed-systems/dotted-version-vectors.md
```

---

### interval-tree-clocks.md
**Description**: Interval tree clocks for dynamic systems, scalable causality tracking, fork/join operations, avoiding process ID exhaustion

**Load this skill**:
```bash
cat skills/distributed-systems/interval-tree-clocks.md
```

---

### vector-clocks.md
**Description**: Vector clocks for tracking causality in distributed systems, detecting concurrent events, and resolving conflicts

**Load this skill**:
```bash
cat skills/distributed-systems/vector-clocks.md
```

---

### logical-clocks.md
**Description**: Lamport logical clocks for establishing happened-before ordering in distributed systems without synchronized physical clocks

**Load this skill**:
```bash
cat skills/distributed-systems/logical-clocks.md
```

---

### eventual-consistency.md
**Description**: Eventual consistency models, consistency levels, read/write quorums, and practical trade-offs in distributed systems

**Load this skill**:
```bash
cat skills/distributed-systems/eventual-consistency.md
```

---

### conflict-resolution.md
**Description**: Conflict resolution strategies including Last-Write-Wins, multi-value, semantic resolution, and application-specific merge functions

**Load this skill**:
```bash
cat skills/distributed-systems/conflict-resolution.md
```

---

### replication-strategies.md
**Description**: Data replication strategies including primary-backup, multi-primary, chain replication, and quorum-based replication

**Load this skill**:
```bash
cat skills/distributed-systems/replication-strategies.md
```

---

### partitioning-sharding.md
**Description**: Data partitioning and sharding strategies including hash-based, range-based, consistent hashing, and rebalancing

**Load this skill**:
```bash
cat skills/distributed-systems/partitioning-sharding.md
```

---

### distributed-locks.md
**Description**: Distributed locking patterns including Redis Redlock, ZooKeeper locks, lease-based locking, and fencing tokens

**Load this skill**:
```bash
cat skills/distributed-systems/distributed-locks.md
```

---

### leader-election.md
**Description**: Leader election algorithms including bully algorithm, ring algorithm, and consensus-based election with RAFT/Paxos

**Load this skill**:
```bash
cat skills/distributed-systems/leader-election.md
```

---

### gossip-protocols.md
**Description**: Gossip protocols for disseminating information, failure detection, and eventual consistency in large-scale distributed systems

**Load this skill**:
```bash
cat skills/distributed-systems/gossip-protocols.md
```

---

### probabilistic-data-structures.md
**Description**: Probabilistic data structures including Bloom filters, HyperLogLog, Count-Min Sketch for space-efficient approximations

**Load this skill**:
```bash
cat skills/distributed-systems/probabilistic-data-structures.md
```

---

## Loading All Skills

```bash
# List all skills in this category
ls skills/distributed-systems/*.md

# Load specific skills
cat skills/distributed-systems/cap-theorem.md
cat skills/distributed-systems/consensus-raft.md
cat skills/distributed-systems/crdt-fundamentals.md
# ... and 14 more
```

## Related Categories

See `skills/README.md` for the complete catalog of all categories and gateway skills.

---

**Browse**: This index provides a quick reference. Load the `discover-distributed-systems` gateway skill for common workflows and integration patterns.

```bash
cat skills/discover-distributed-systems/SKILL.md
```
