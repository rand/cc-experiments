---
name: discover-distributed
description: Automatically discover distributed systems and realtime communication skills when working with consensus, CRDTs, replication, WebSocket, SSE, pub/sub, or event-driven architectures
license: MIT
metadata:
  author: rand
  version: "4.0"
compatibility:
  claude-code: ">=1.0.0"
---

# Distributed Systems & Realtime Skills Discovery

## When This Skill Activates
- Consensus algorithms (RAFT, Paxos)
- CAP theorem, consistency models
- CRDTs and eventual consistency
- Vector clocks, logical clocks, causality
- Replication, partitioning, sharding
- Distributed locks and leader election
- Gossip protocols, probabilistic data structures
- WebSockets, Server-Sent Events, streaming
- Pub/sub, push notifications, live updates

## Available Skills (21 total)

### Distributed Systems (17 skills)
1. **cap-theorem** - CAP theorem, consistency vs availability trade-offs
2. **consensus-raft** - RAFT consensus, leader election, log replication
3. **consensus-paxos** - Paxos consensus, Basic/Multi-Paxos
4. **crdt-fundamentals** - Conflict-free Replicated Data Types basics
5. **crdt-types** - Specific CRDT implementations (LWW, OR-Set, RGA)
6. **dotted-version-vectors** - Compact causality, sibling management
7. **interval-tree-clocks** - Dynamic causality, fork/join
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

### Realtime (4 skills)
1. **websocket-implementation** - WebSocket connections, protocols, scaling
2. **server-sent-events** - SSE for server-to-client streaming
3. **pubsub-patterns** - Publish/subscribe architectures
4. **realtime-sync** - Real-time data synchronization

## Load Full Category Details
Read ../distributed-systems/INDEX.md
Read ../realtime/INDEX.md

## Progressive Loading
- **Level 1**: This gateway loads automatically (~60 lines)
- **Level 2**: Load category INDEX.md for full skill listings
- **Level 3**: Load specific skills as needed
