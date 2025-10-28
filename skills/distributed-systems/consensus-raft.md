---
name: distributed-systems-consensus-raft
description: RAFT consensus algorithm including leader election, log replication, safety guarantees, and implementation patterns
---

# RAFT Consensus

**Scope**: RAFT algorithm, leader election, log replication, safety, implementation patterns
**Lines**: ~380
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building distributed consensus systems
- Implementing replicated state machines
- Designing highly available services
- Understanding etcd, Consul internals
- Implementing leader election
- Building distributed databases
- Ensuring strong consistency
- Working with Kubernetes (uses etcd/RAFT)

## Core Concepts

### RAFT Overview

**Goal**: Maintain replicated log across cluster with strong consistency

**Key properties**:
- Leader-based (one leader at a time)
- Strong consistency (linearizable)
- Majority quorum (tolerates f failures with 2f+1 nodes)
- Understandable (designed to be easier than Paxos)

**Node states**:
```
Follower → Candidate → Leader
   ↑                      ↓
   └──────────────────────┘
```

### Terms (Logical Clock)

**Term**: Monotonically increasing number representing election cycle

```
Term 1:        Term 2:        Term 3:
Leader A ──X   Election  →    Leader B ────→

Each term has at most one leader
Terms prevent conflicts from split-brain
```

---

## Leader Election

### Election Process

```
1. Follower times out waiting for leader heartbeat
2. Increment term, become Candidate
3. Vote for self, request votes from all nodes
4. If majority votes received → become Leader
5. If another leader discovered → become Follower
6. If election timeout → start new election
```

### Election Rules

```python
class RaftNode:
    def __init__(self):
        self.state = "follower"
        self.current_term = 0
        self.voted_for = None
        self.election_timeout = random.randint(150, 300)  # ms

    def on_election_timeout(self):
        """Start election"""
        self.current_term += 1
        self.state = "candidate"
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}

        # Request votes from all nodes
        for node in self.cluster_nodes:
            self.send_request_vote(node, self.current_term, self.node_id,
                                  self.last_log_index, self.last_log_term)

    def handle_request_vote(self, term, candidate_id, last_log_index, last_log_term):
        """Handle vote request"""
        # Reject if term is old
        if term < self.current_term:
            return False

        # Update term if newer
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None
            self.state = "follower"

        # Grant vote if:
        # 1. Haven't voted this term
        # 2. Candidate's log is at least as up-to-date
        if self.voted_for is None or self.voted_for == candidate_id:
            if self.is_log_up_to_date(last_log_index, last_log_term):
                self.voted_for = candidate_id
                return True

        return False

    def is_log_up_to_date(self, candidate_last_log_index, candidate_last_log_term):
        """Check if candidate's log is at least as up-to-date"""
        my_last_log_term = self.log[-1].term if self.log else 0
        my_last_log_index = len(self.log) - 1

        # Candidate's last log term is more recent
        if candidate_last_log_term > my_last_log_term:
            return True

        # Same term, candidate's log is at least as long
        if candidate_last_log_term == my_last_log_term:
            return candidate_last_log_index >= my_last_log_index

        return False
```

---

## Log Replication

### Replication Process

```
Client → Leader: Command
Leader:
  1. Append to local log
  2. Send AppendEntries to all followers
  3. Wait for majority acknowledgment
  4. Apply to state machine
  5. Respond to client
  6. Eventually notify followers to apply
```

### AppendEntries RPC

```python
class LogEntry:
    def __init__(self, term, command):
        self.term = term
        self.command = command

class RaftNode:
    def __init__(self):
        self.log = []  # List of LogEntry
        self.commit_index = 0  # Index of highest committed entry
        self.last_applied = 0  # Index of highest applied entry

        # Leader state (reinitialized after election)
        self.next_index = {}   # For each server, index of next log entry to send
        self.match_index = {}  # For each server, index of highest log entry known to be replicated

    def append_entries(self, term, leader_id, prev_log_index, prev_log_term,
                      entries, leader_commit):
        """Handle AppendEntries RPC (heartbeat or log replication)"""

        # Reply false if term < current_term
        if term < self.current_term:
            return False

        # Update term and revert to follower if necessary
        if term > self.current_term:
            self.current_term = term
            self.state = "follower"
            self.voted_for = None

        # Reset election timeout (received heartbeat from valid leader)
        self.reset_election_timeout()

        # Reply false if log doesn't contain entry at prev_log_index matching prev_log_term
        if prev_log_index >= 0:
            if prev_log_index >= len(self.log) or \
               self.log[prev_log_index].term != prev_log_term:
                return False

        # Delete conflicting entries and append new ones
        log_index = prev_log_index + 1
        for i, entry in enumerate(entries):
            if log_index + i < len(self.log):
                if self.log[log_index + i].term != entry.term:
                    # Delete this and all following entries
                    self.log = self.log[:log_index + i]
                    self.log.append(entry)
            else:
                self.log.append(entry)

        # Update commit index
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log) - 1)

        # Apply newly committed entries
        self.apply_committed_entries()

        return True

    def apply_committed_entries(self):
        """Apply committed log entries to state machine"""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            self.state_machine.apply(entry.command)
```

### Leader Logic

```python
class RaftLeader(RaftNode):
    def replicate_log(self):
        """Send AppendEntries to all followers"""
        for follower_id in self.cluster_nodes:
            if follower_id == self.node_id:
                continue

            # Get entries to send to this follower
            next_index = self.next_index[follower_id]
            prev_log_index = next_index - 1
            prev_log_term = self.log[prev_log_index].term if prev_log_index >= 0 else 0
            entries = self.log[next_index:]

            success = self.send_append_entries(
                follower_id,
                self.current_term,
                self.node_id,
                prev_log_index,
                prev_log_term,
                entries,
                self.commit_index
            )

            if success:
                # Update next_index and match_index
                self.next_index[follower_id] = next_index + len(entries)
                self.match_index[follower_id] = self.next_index[follower_id] - 1

                # Update commit_index if majority replicated
                self.update_commit_index()
            else:
                # Decrement next_index and retry
                self.next_index[follower_id] = max(0, self.next_index[follower_id] - 1)

    def update_commit_index(self):
        """Advance commit_index if majority of servers have replicated entry"""
        for n in range(self.commit_index + 1, len(self.log)):
            # Only commit entries from current term
            if self.log[n].term != self.current_term:
                continue

            # Count replicas
            replicas = 1  # Leader has it
            for follower_id in self.cluster_nodes:
                if follower_id == self.node_id:
                    continue
                if self.match_index[follower_id] >= n:
                    replicas += 1

            # Commit if majority
            if replicas > len(self.cluster_nodes) / 2:
                self.commit_index = n
                self.apply_committed_entries()
```

---

## Safety Guarantees

### Election Safety

**Guarantee**: At most one leader per term

**How**: Node votes for at most one candidate per term, majority quorum required

### Leader Append-Only

**Guarantee**: Leader never overwrites or deletes entries in its log

**How**: Leader only appends new entries

### Log Matching

**Guarantee**: If two logs contain entry with same index and term, all preceding entries are identical

**How**: AppendEntries consistency check (prev_log_index, prev_log_term)

### Leader Completeness

**Guarantee**: If entry is committed in term T, it will be present in all leader logs for terms > T

**How**: Candidate with incomplete log won't get majority votes

### State Machine Safety

**Guarantee**: If server has applied log entry at index, no other server will apply different entry at same index

**How**: Follows from other properties

---

## Real-World Implementation (etcd)

### Using etcd

```bash
# Start etcd cluster (3 nodes)
etcd --name node1 --initial-cluster node1=http://10.0.1.1:2380,node2=http://10.0.1.2:2380,node3=http://10.0.1.3:2380
```

**Python client**:
```python
import etcd3

etcd = etcd3.client(host='localhost', port=2379)

# Write (goes through RAFT consensus)
etcd.put('/config/setting', 'value')

# Read (consistent read from leader)
value, metadata = etcd.get('/config/setting')

# Watch for changes
watch_id = etcd.add_watch_callback('/config/', lambda event: print(event))

# Lease (TTL)
lease = etcd.lease(ttl=60)
etcd.put('/ephemeral/key', 'value', lease=lease)

# Transactions (atomic operations)
etcd.transaction(
    compare=[etcd.transactions.value('/counter') == b'5'],
    success=[etcd.transactions.put('/counter', '6')],
    failure=[etcd.transactions.get('/counter')]
)
```

### Go client (native etcd client):

```go
package main

import (
    "context"
    "time"
    clientv3 "go.etcd.io/etcd/client/v3"
)

func main() {
    cli, _ := clientv3.New(clientv3.Config{
        Endpoints:   []string{"localhost:2379"},
        DialTimeout: 5 * time.Second,
    })
    defer cli.Close()

    ctx, cancel := context.WithTimeout(context.Background(), time.Second)
    defer cancel()

    // Put
    cli.Put(ctx, "/config/setting", "value")

    // Get
    resp, _ := cli.Get(ctx, "/config/setting")
    for _, kv := range resp.Kvs {
        fmt.Printf("%s: %s\n", kv.Key, kv.Value)
    }

    // Watch
    watchChan := cli.Watch(context.Background(), "/config/", clientv3.WithPrefix())
    for watchResp := range watchChan {
        for _, event := range watchResp.Events {
            fmt.Printf("Event: %s %s\n", event.Type, event.Kv.Key)
        }
    }
}
```

---

## Performance Considerations

### Cluster Size

```
3 nodes:  Tolerates 1 failure (quorum = 2)
5 nodes:  Tolerates 2 failures (quorum = 3)
7 nodes:  Tolerates 3 failures (quorum = 4)

More nodes:
✅ Higher availability
❌ Slower writes (more nodes to replicate to)
❌ More network traffic

Recommendation: 3 or 5 nodes for most use cases
```

### Latency

```
Write latency = Network RTT + Disk sync time

Typically:
- Same datacenter: 1-10ms
- Cross-region: 50-300ms

Optimization:
- Batch writes
- Use faster disks (SSD)
- Tune election timeout
```

---

## Common Patterns

### Pattern 1: Configuration Management

```python
class ConfigManager:
    """Use RAFT for distributed configuration"""

    def __init__(self, etcd_client):
        self.etcd = etcd_client

    def set_config(self, key, value):
        """Set configuration value (strongly consistent)"""
        self.etcd.put(f'/config/{key}', value)

    def get_config(self, key):
        """Get configuration value"""
        value, _ = self.etcd.get(f'/config/{key}')
        return value

    def watch_config(self, key, callback):
        """Watch for configuration changes"""
        self.etcd.add_watch_callback(f'/config/{key}', callback)
```

### Pattern 2: Leader Election

```python
import etcd3
import time

class LeaderElection:
    """Distributed leader election using etcd"""

    def __init__(self, etcd_client, name):
        self.etcd = etcd_client
        self.name = name
        self.lease = None

    def campaign(self):
        """Attempt to become leader"""
        self.lease = self.etcd.lease(ttl=60)

        # Try to create election key with our name
        success, _ = self.etcd.transaction(
            compare=[
                self.etcd.transactions.version('/election/leader') == 0
            ],
            success=[
                self.etcd.transactions.put('/election/leader', self.name, lease=self.lease)
            ],
            failure=[]
        )

        if success:
            print(f"{self.name} became leader")
            return True
        return False

    def resign(self):
        """Resign from leadership"""
        if self.lease:
            self.lease.revoke()

    def keep_alive(self):
        """Keep leadership alive"""
        if self.lease:
            self.lease.refresh()
```

---

## Testing RAFT

### Partition Testing

```python
def test_network_partition():
    """Test RAFT behavior during network partition"""
    cluster = RaftCluster(nodes=5)

    # Normal operation
    cluster.write('key1', 'value1')
    assert cluster.read('key1') == 'value1'

    # Partition: [1, 2] | [3, 4, 5]
    cluster.partition([1, 2], [3, 4, 5])

    # Majority side (3, 4, 5) should elect new leader and continue
    cluster.write_to_node(3, 'key2', 'value2')  # Should succeed
    assert cluster.read_from_node(3, 'key2') == 'value2'

    # Minority side (1, 2) should refuse writes
    with pytest.raises(NoQuorumError):
        cluster.write_to_node(1, 'key3', 'value3')

    # Heal partition
    cluster.heal_partition()

    # Minority nodes should sync with majority
    time.sleep(1)
    assert cluster.read_from_node(1, 'key2') == 'value2'
```

---

## Level 3 Resources

This skill includes executable scripts, comprehensive references, and examples for hands-on RAFT consensus work.

### Quick Start

```bash
# Navigate to resources
cd skills/distributed-systems/consensus-raft/resources/scripts

# Start test cluster (Docker-based)
./test_etcd_cluster.sh --nodes 3

# Benchmark consensus performance
./benchmark_consensus.py --operations 5000 --concurrency 50

# Visualize RAFT state machine
./visualize_raft_state.py --type state-machine --format mermaid
```

### Resources Structure

```
consensus-raft/resources/
├── REFERENCE.md           # RAFT algorithm deep-dive, etcd internals, proofs
├── scripts/
│   ├── README.md         # Scripts documentation
│   ├── test_etcd_cluster.sh      # Docker-based etcd cluster setup
│   ├── benchmark_consensus.py    # Performance benchmarking
│   └── visualize_raft_state.py   # State machine visualizations
└── examples/
    ├── python/           # Python RAFT client examples
    └── go/               # Go etcd integration examples
```

### Available Scripts

#### test_etcd_cluster.sh
Automated Docker-based etcd RAFT cluster for testing:
```bash
# 5-node cluster
./test_etcd_cluster.sh --nodes 5

# JSON output for CI/CD
./test_etcd_cluster.sh --nodes 3 --json

# Cleanup
./test_etcd_cluster.sh --cleanup
```

#### benchmark_consensus.py
Measure consensus latency and throughput:
```bash
# Basic benchmark
./benchmark_consensus.py --operations 10000

# High concurrency
./benchmark_consensus.py --operations 50000 --concurrency 200 --json
```

**Metrics**: min/max/mean/p95/p99 latency, throughput, success rates

#### visualize_raft_state.py
Generate RAFT diagrams:
```bash
# State machine diagram
./visualize_raft_state.py --type state-machine --format mermaid

# Log replication sequence
./visualize_raft_state.py --type log-replication --format ascii

# Live cluster status
./visualize_raft_state.py --type cluster-status --endpoints localhost:2379
```

### Reference Material

**REFERENCE.md** includes:
- RAFT paper key sections and safety proofs
- Complete state machine specification
- Leader election algorithm details
- Log replication implementation
- etcd architecture and internals
- RAFT vs Paxos comparison
- Performance characteristics
- Common implementation pitfalls

### Example Workflow

```bash
# 1. Setup cluster
./test_etcd_cluster.sh --nodes 3

# 2. Run benchmarks
./benchmark_consensus.py --operations 5000 --json > results.json

# 3. Analyze results
cat results.json | jq '.results.put.latency.p99_ms'

# 4. Generate diagrams
./visualize_raft_state.py --type state-machine --output state.mmd

# 5. Test fault tolerance (in separate terminal)
docker stop etcd-node2  # Observe leader election

# 6. Cleanup
./test_etcd_cluster.sh --cleanup
```

**See**: `resources/scripts/README.md` for complete documentation

---

## Related Skills

- `distributed-systems-consensus-paxos` - Alternative consensus algorithm
- `distributed-systems-leader-election` - Leader election patterns
- `distributed-systems-replication-strategies` - Data replication
- `distributed-systems-cap-theorem` - Consistency trade-offs

---

**Last Updated**: 2025-10-27
