---
name: distributed-systems-leader-election
description: Leader election algorithms including bully algorithm, ring algorithm, and consensus-based election with RAFT/Paxos
---

# Leader Election

**Scope**: Leader election algorithms, bully, ring, consensus-based, practical implementations
**Lines**: ~220
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Coordinating distributed services
- Implementing active-passive failover
- Building distributed databases
- Managing cluster coordination
- Implementing job schedulers
- Understanding etcd, ZooKeeper patterns
- Handling failover scenarios
- Building high-availability systems

## Core Concepts

### Why Leader Election?

```
Problem: Who coordinates distributed operations?

Solutions requiring leader:
- Single point for writes (primary-backup)
- Job scheduling (avoid duplicate work)
- Configuration management
- Distributed transactions coordination
```

### Properties

```
Safety: At most one leader at a time
Liveness: Eventually elects leader
Termination: Election completes in finite time
```

---

## Election Algorithms

### 1. Bully Algorithm

**Approach**: Highest ID becomes leader

```python
import time
import threading

class BullyElection:
    """Bully algorithm for leader election"""

    def __init__(self, node_id, all_nodes):
        self.node_id = node_id
        self.all_nodes = sorted(all_nodes)
        self.leader = None
        self.is_leader = False

    def start_election(self):
        """Initiate election"""
        print(f"Node {self.node_id} starting election")

        # Send ELECTION message to higher IDs
        higher_nodes = [n for n in self.all_nodes if n > self.node_id]

        if not higher_nodes:
            # No higher nodes - I'm the leader
            self.become_leader()
            return

        # Wait for responses from higher nodes
        responses = []
        for node in higher_nodes:
            response = self.send_election_message(node)
            if response:
                responses.append(node)

        if responses:
            # Higher node responded - they'll handle election
            pass
        else:
            # No higher nodes responded - I'm the leader
            self.become_leader()

    def become_leader(self):
        """Declare self as leader"""
        self.is_leader = True
        self.leader = self.node_id
        print(f"Node {self.node_id} is now LEADER")

        # Broadcast COORDINATOR message to all lower nodes
        for node in self.all_nodes:
            if node < self.node_id:
                self.send_coordinator_message(node)

    def on_election_message(self, sender_id):
        """Handle ELECTION message from lower node"""
        if sender_id < self.node_id:
            # Respond OK and start own election
            self.start_election()
            return "OK"

        return None

    def on_coordinator_message(self, leader_id):
        """Handle COORDINATOR message"""
        self.leader = leader_id
        self.is_leader = False
        print(f"Node {self.node_id} acknowledges {leader_id} as leader")

# Simulation
nodes = [BullyElection(i, [1, 2, 3, 4, 5]) for i in range(1, 6)]

# Node 3 starts election
nodes[2].start_election()  # Node 5 becomes leader

# Node 5 crashes, Node 4 detects and starts election
nodes[3].start_election()  # Node 4 becomes leader
```

**Pros**: Simple, eventually elects highest ID
**Cons**: Many messages, not fault-tolerant during election

### 2. Ring Algorithm

**Approach**: Pass election message around ring

```python
class RingElection:
    """Ring-based leader election"""

    def __init__(self, node_id, next_node):
        self.node_id = node_id
        self.next_node = next_node  # Next node in ring
        self.leader = None
        self.participating = False

    def start_election(self):
        """Start election by sending message with own ID"""
        self.participating = True
        self.send_election_message([self.node_id])

    def on_election_message(self, id_list):
        """Handle election message"""
        if self.node_id in id_list:
            # Message completed circle - elect leader
            leader_id = max(id_list)
            self.announce_leader(leader_id)
        else:
            # Add self and forward
            id_list.append(self.node_id)
            self.send_election_message(id_list)

    def announce_leader(self, leader_id):
        """Announce elected leader"""
        self.leader = leader_id
        self.send_coordinator_message(leader_id)

    def on_coordinator_message(self, leader_id):
        """Acknowledge leader"""
        self.leader = leader_id

        # Forward if not completed circle
        if not self.participating:
            self.send_coordinator_message(leader_id)
        else:
            self.participating = False
```

**Pros**: Fewer messages than bully
**Cons**: Slow if ring is large, depends on ring structure

### 3. Consensus-Based (RAFT, ZooKeeper)

```python
# Using etcd (RAFT-based)
import etcd3
import time

class ConsensusLeaderElection:
    """Leader election using etcd"""

    def __init__(self, node_id):
        self.node_id = node_id
        self.etcd = etcd3.client()
        self.lease = None
        self.is_leader = False

    def campaign(self):
        """Attempt to become leader"""
        # Create lease
        self.lease = self.etcd.lease(ttl=60)

        # Try to create leader key with our ID
        success, _ = self.etcd.transaction(
            compare=[
                self.etcd.transactions.version('/leader') == 0
            ],
            success=[
                self.etcd.transactions.put('/leader', self.node_id, lease=self.lease)
            ],
            failure=[]
        )

        if success:
            self.is_leader = True
            self._start_keepalive()
            return True

        return False

    def _start_keepalive(self):
        """Keep lease alive"""
        def keepalive_loop():
            while self.is_leader:
                self.lease.refresh()
                time.sleep(20)

        threading.Thread(target=keepalive_loop, daemon=True).start()

    def resign(self):
        """Resign from leadership"""
        if self.is_leader and self.lease:
            self.lease.revoke()
            self.is_leader = False

    def watch_leader(self, callback):
        """Watch for leader changes"""
        watch_id = self.etcd.add_watch_callback('/leader', callback)
        return watch_id

# Usage
election = ConsensusLeaderElection('node1')

if election.campaign():
    print("I am the leader!")
    try:
        # Do leader work
        while True:
            lead()
            time.sleep(1)
    except KeyboardInterrupt:
        election.resign()
else:
    # Watch for leader changes
    election.watch_leader(lambda event: print(f"New leader: {event.value}"))
```

---

## Split-Brain Prevention

### Problem

```
Network partition:
[Node A] | [Node B, C]

Both sides elect leader → Two leaders!
```

### Solution: Quorum

```python
class QuorumElection:
    """Elect leader only with majority quorum"""

    def __init__(self, node_id, all_nodes):
        self.node_id = node_id
        self.all_nodes = all_nodes
        self.quorum_size = len(all_nodes) // 2 + 1

    def campaign(self):
        """Campaign with quorum requirement"""
        votes = {self.node_id}  # Vote for self

        # Request votes from others
        for node in self.all_nodes:
            if node != self.node_id:
                if self.request_vote(node):
                    votes.add(node)

        # Become leader only if quorum
        if len(votes) >= self.quorum_size:
            self.become_leader()
            return True

        return False

# Guarantees at most one leader per term
```

---

## Practical Patterns

### Pattern 1: Active-Passive Failover

```python
class ActivePassiveService:
    """Service with leader election"""

    def __init__(self, node_id):
        self.node_id = node_id
        self.election = ConsensusLeaderElection(node_id)

    def run(self):
        """Run service with leadership"""
        while True:
            if self.election.campaign():
                # I'm the leader - do active work
                self.do_leader_work()
            else:
                # I'm a follower - standby
                self.do_follower_work()

    def do_leader_work(self):
        """Active work (only leader)"""
        while self.election.is_leader:
            process_jobs()
            time.sleep(1)

    def do_follower_work(self):
        """Passive work (followers)"""
        time.sleep(5)  # Wait for potential leadership
```

### Pattern 2: Distributed Cron

```python
class DistributedCron:
    """Only leader executes scheduled jobs"""

    def __init__(self, node_id, schedule):
        self.election = ConsensusLeaderElection(node_id)
        self.schedule = schedule

    def run(self):
        while True:
            if self.election.is_leader:
                for job in self.schedule.due_jobs():
                    self.execute(job)

            time.sleep(1)

    def execute(self, job):
        """Execute job (leader only)"""
        print(f"Leader executing: {job}")
        job.run()
```

---

## Best Practices

### 1. Use Fencing Tokens

```python
# Leader includes generation/term number
class FencedLeader:
    def __init__(self):
        self.generation = 0

    def become_leader(self):
        self.generation += 1
        return self.generation

    def perform_action(self, action, generation):
        """Resource validates generation"""
        if generation < self.last_generation:
            raise StaleLeaderError()
```

### 2. Handle Leadership Loss

```python
class GracefulLeader:
    def do_leader_work(self):
        while self.is_leader:
            try:
                work()
            except LeadershipLostError:
                self.cleanup()
                break
```

### 3. Lease-Based Leadership

```python
# Lease expires if leader crashes
# Prevents indefinite wait for crashed leader
```

---

## Related Skills

- `distributed-systems-consensus-raft` - RAFT consensus
- `distributed-systems-distributed-locks` - Distributed locking
- `distributed-systems-eventual-consistency` - Consistency models

---

**Last Updated**: 2025-10-27
