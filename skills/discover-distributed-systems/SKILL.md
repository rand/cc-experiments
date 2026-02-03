---
name: discover-distributed-systems
description: Automatically discover distributed systems skills when working with consensus, CRDTs, replication, partitioning, and distributed algorithms
license: MIT
metadata:
  author: rand
  version: "3.1"
compatibility: Designed for Claude Code. Compatible with any agent supporting the Agent Skills format.
---

# Distributed Systems Skills Discovery

Provides automatic access to comprehensive distributed systems skills.

## When This Skill Activates

This skill auto-activates when you're working with:
- Consensus algorithms (RAFT, Paxos)
- CAP theorem, consistency models
- CRDTs and eventual consistency
- Vector clocks, causality
- Replication and partitioning
- Distributed locks and leader election
- Gossip protocols
- Probabilistic data structures

## Available Skills

### Quick Reference

The Distributed Systems category contains 17 skills:

1. **cap-theorem** - CAP theorem, consistency vs availability trade-offs
2. **consensus-raft** - RAFT consensus, leader election, log replication
3. **consensus-paxos** - Paxos consensus, Basic/Multi-Paxos
4. **crdt-fundamentals** - Conflict-free Replicated Data Types basics
5. **crdt-types** - Specific CRDT implementations (LWW, OR-Set, RGA)
6. **dotted-version-vectors** - Compact causality, sibling management, optimized vector clocks
7. **interval-tree-clocks** - Dynamic causality, fork/join, scalable tracking
8. **vector-clocks** - Causality tracking, happens-before
9. **logical-clocks** - Lamport clocks, logical time
10. **eventual-consistency** - Consistency levels, quorums, BASE
11. **conflict-resolution** - LWW, multi-value, semantic resolution
12. **replication-strategies** - Primary-backup, multi-primary, chain, quorum
13. **partitioning-sharding** - Hash/range/consistent hashing, rebalancing
14. **distributed-locks** - Redlock, ZooKeeper locks, fencing tokens
15. **leader-election** - Bully, ring, consensus-based election
16. **gossip-protocols** - Epidemic protocols, failure detection
17. **probabilistic-data-structures** - Bloom filters, HyperLogLog, Count-Min Sketch

### Load Full Category Details

For complete descriptions and workflows:

Read <cc-polymath-root>/skills/distributed-systems/INDEX.md


This loads the full Distributed Systems category index with:
- Detailed skill descriptions
- Usage triggers for each skill
- Common workflow combinations
- Cross-references to related skills

### Load Specific Skills

Load individual skills as needed:

Read <cc-polymath-root>/skills/distributed-systems/cap-theorem.md
Read <cc-polymath-root>/skills/distributed-systems/consensus-raft.md
Read <cc-polymath-root>/skills/distributed-systems/crdt-fundamentals.md
Read <cc-polymath-root>/skills/distributed-systems/replication-strategies.md


## Common Workflows

### Understanding Consistency Trade-offs
# CAP → Eventual consistency → Conflict resolution
Read <cc-polymath-root>/skills/distributed-systems/cap-theorem.md
Read <cc-polymath-root>/skills/distributed-systems/eventual-consistency.md
Read <cc-polymath-root>/skills/distributed-systems/conflict-resolution.md


### Implementing Consensus
# RAFT → Leader election → Replication
Read <cc-polymath-root>/skills/distributed-systems/consensus-raft.md
Read <cc-polymath-root>/skills/distributed-systems/leader-election.md
Read <cc-polymath-root>/skills/distributed-systems/replication-strategies.md


### Building Eventually Consistent Systems
# CRDTs → Vector clocks → Conflict resolution
Read <cc-polymath-root>/skills/distributed-systems/crdt-fundamentals.md
Read <cc-polymath-root>/skills/distributed-systems/vector-clocks.md
Read <cc-polymath-root>/skills/distributed-systems/conflict-resolution.md


### Advanced Causality Tracking
# Vector clocks → Dotted version vectors → Interval tree clocks
Read <cc-polymath-root>/skills/distributed-systems/vector-clocks.md
Read <cc-polymath-root>/skills/distributed-systems/dotted-version-vectors.md
Read <cc-polymath-root>/skills/distributed-systems/interval-tree-clocks.md


### Scaling Data
# Partitioning → Replication → Gossip
Read <cc-polymath-root>/skills/distributed-systems/partitioning-sharding.md
Read <cc-polymath-root>/skills/distributed-systems/replication-strategies.md
Read <cc-polymath-root>/skills/distributed-systems/gossip-protocols.md


## Progressive Loading

This gateway skill enables progressive loading:
- **Level 1**: Gateway loads automatically (you're here now)
- **Level 2**: Load category INDEX.md for full overview
- **Level 3**: Load specific skills as needed

## Usage Instructions

1. **Auto-activation**: This skill loads automatically when Claude Code detects distributed systems work
2. **Browse skills**: Run `Read <cc-polymath-root>/skills/distributed-systems/INDEX.md` for full category overview
3. **Load specific skills**: Use bash commands above to load individual skills


**Next Steps**: Run `Read <cc-polymath-root>/skills/distributed-systems/INDEX.md` to see full category details.
