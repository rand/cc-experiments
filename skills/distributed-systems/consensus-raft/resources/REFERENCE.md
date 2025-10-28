# RAFT Consensus Algorithm Reference

Comprehensive reference material for the RAFT consensus algorithm, including detailed algorithm specifications, safety proofs, implementation guidance, and etcd internals.

## Table of Contents

1. [RAFT Paper Key Sections](#raft-paper-key-sections)
2. [State Machine Specification](#state-machine-specification)
3. [Leader Election Algorithm](#leader-election-algorithm)
4. [Log Replication Details](#log-replication-details)
5. [Safety Properties and Proofs](#safety-properties-and-proofs)
6. [Cluster Membership Changes](#cluster-membership-changes)
7. [etcd Implementation Details](#etcd-implementation-details)
8. [RAFT vs Paxos Comparison](#raft-vs-paxos-comparison)
9. [Performance Characteristics](#performance-characteristics)
10. [Common Implementation Pitfalls](#common-implementation-pitfalls)

---

## RAFT Paper Key Sections

**Original Paper**: "In Search of an Understandable Consensus Algorithm" by Diego Ongaro and John Ousterhout (2014)

**Paper URL**: https://raft.github.io/raft.pdf

### Abstract Summary

RAFT is a consensus algorithm designed for understandability. It separates consensus into three independent subproblems:

1. **Leader Election**: A new leader must be chosen when existing leader fails
2. **Log Replication**: Leader accepts log entries from clients and replicates across cluster
3. **Safety**: If any server has applied a log entry at a given index, no other server will apply a different entry at that index

### Key Design Goals

1. **Strong leader**: Log entries only flow from leader to followers (simplifies replication)
2. **Leader election**: Uses randomized timers to elect leaders quickly with minimal conflicts
3. **Membership changes**: Joint consensus approach for safe cluster reconfiguration

---

## State Machine Specification

### Server States

```
┌─────────────────────────────────────────────────────────┐
│                     ALL SERVERS                          │
├─────────────────────────────────────────────────────────┤
│ Persistent State (updated on stable storage before      │
│ responding to RPCs):                                     │
│   currentTerm: Latest term server has seen              │
│   votedFor: CandidateId that received vote in current   │
│             term (or null)                               │
│   log[]: Log entries; each entry contains command for   │
│          state machine, and term when entry was          │
│          received by leader (first index is 1)           │
│                                                          │
│ Volatile State (on all servers):                         │
│   commitIndex: Index of highest log entry known to be   │
│                committed (initialized to 0)              │
│   lastApplied: Index of highest log entry applied to    │
│                state machine (initialized to 0)          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  LEADERS (VOLATILE STATE)                │
├─────────────────────────────────────────────────────────┤
│ Reinitialized after election:                            │
│   nextIndex[]:  For each server, index of next log      │
│                 entry to send to that server             │
│                 (initialized to leader last log index+1) │
│   matchIndex[]: For each server, index of highest log   │
│                 entry known to be replicated on server   │
│                 (initialized to 0, increases             │
│                 monotonically)                           │
└─────────────────────────────────────────────────────────┘
```

### State Transitions

```python
class ServerState:
    """Complete server state specification"""

    def __init__(self):
        # Persistent state (must survive restarts)
        self.current_term = 0
        self.voted_for = None
        self.log = []  # List of LogEntry(term, command)

        # Volatile state (all servers)
        self.commit_index = 0
        self.last_applied = 0
        self.state = "follower"  # "follower", "candidate", "leader"

        # Volatile state (leaders only)
        self.next_index = {}   # server_id -> index
        self.match_index = {}  # server_id -> index

        # Timers
        self.election_timeout = self.random_timeout(150, 300)  # ms
        self.heartbeat_interval = 50  # ms
        self.election_timer = Timer()
```

---

## Leader Election Algorithm

### Election Timeout and Randomization

**Problem**: Prevent split votes where multiple candidates compete
**Solution**: Randomized election timeouts (150-300ms recommended)

```
Election timeout range: [T, 2T]
Heartbeat interval: T/10 (typically)

Example: T = 150ms
  Election timeout: 150-300ms
  Heartbeat: 15ms
```

### RequestVote RPC

**Arguments**:
```
term:          Candidate's term
candidateId:   Candidate requesting vote
lastLogIndex:  Index of candidate's last log entry
lastLogTerm:   Term of candidate's last log entry
```

**Results**:
```
term:        CurrentTerm, for candidate to update itself
voteGranted: True means candidate received vote
```

**Receiver implementation**:
```python
def request_vote(self, term, candidate_id, last_log_index, last_log_term):
    """Handle RequestVote RPC"""

    # Reply false if term < currentTerm (§5.1)
    if term < self.current_term:
        return {"term": self.current_term, "voteGranted": False}

    # If RPC request contains term T > currentTerm:
    # set currentTerm = T, convert to follower (§5.1)
    if term > self.current_term:
        self.current_term = term
        self.state = "follower"
        self.voted_for = None

    # If votedFor is null or candidateId, and candidate's log is at
    # least as up-to-date as receiver's log, grant vote (§5.2, §5.4)
    vote_granted = False
    if (self.voted_for is None or self.voted_for == candidate_id):
        if self.log_is_up_to_date(last_log_index, last_log_term):
            self.voted_for = candidate_id
            self.reset_election_timeout()
            vote_granted = True

    return {"term": self.current_term, "voteGranted": vote_granted}


def log_is_up_to_date(self, candidate_last_log_index, candidate_last_log_term):
    """Check if candidate's log is at least as up-to-date as receiver's

    "Up-to-date" is determined by comparing the index and term of the
    last entries in the logs. If the logs have last entries with different
    terms, then the log with the later term is more up-to-date. If the
    logs end with the same term, then whichever log is longer is more
    up-to-date. (§5.4.1)
    """
    my_last_log_index = len(self.log) - 1
    my_last_log_term = self.log[-1].term if self.log else 0

    # Candidate's last log entry has later term
    if candidate_last_log_term > my_last_log_term:
        return True

    # Same term, candidate's log is at least as long
    if candidate_last_log_term == my_last_log_term:
        return candidate_last_log_index >= my_last_log_index

    return False
```

### Election Process

```python
def start_election(self):
    """Initiate leader election (§5.2)"""

    # Increment currentTerm
    self.current_term += 1

    # Transition to candidate state
    self.state = "candidate"

    # Vote for self
    self.voted_for = self.node_id
    votes_received = {self.node_id}

    # Reset election timer
    self.reset_election_timeout()

    # Send RequestVote RPCs to all other servers in parallel
    last_log_index = len(self.log) - 1
    last_log_term = self.log[-1].term if self.log else 0

    for server_id in self.cluster_nodes:
        if server_id == self.node_id:
            continue

        response = self.send_request_vote(
            server_id,
            self.current_term,
            self.node_id,
            last_log_index,
            last_log_term
        )

        # If response contains term T > currentTerm: set currentTerm = T,
        # convert to follower (§5.1)
        if response["term"] > self.current_term:
            self.current_term = response["term"]
            self.state = "follower"
            self.voted_for = None
            return

        # Count votes
        if response["voteGranted"]:
            votes_received.add(server_id)

            # If votes received from majority: become leader (§5.2)
            if len(votes_received) > len(self.cluster_nodes) / 2:
                self.become_leader()
                return

    # If election timeout elapses: start new election (§5.2)
    # (Handled by election timer in main loop)
```

---

## Log Replication Details

### AppendEntries RPC

**Arguments**:
```
term:         Leader's term
leaderId:     So follower can redirect clients
prevLogIndex: Index of log entry immediately preceding new ones
prevLogTerm:  Term of prevLogIndex entry
entries[]:    Log entries to store (empty for heartbeat)
leaderCommit: Leader's commitIndex
```

**Results**:
```
term:    CurrentTerm, for leader to update itself
success: True if follower contained entry matching prevLogIndex and prevLogTerm
```

**Receiver implementation**:
```python
def append_entries(self, term, leader_id, prev_log_index, prev_log_term,
                  entries, leader_commit):
    """Handle AppendEntries RPC (§5.3)"""

    # 1. Reply false if term < currentTerm (§5.1)
    if term < self.current_term:
        return {"term": self.current_term, "success": False}

    # If RPC request contains term T > currentTerm:
    # set currentTerm = T, convert to follower (§5.1)
    if term > self.current_term:
        self.current_term = term
        self.state = "follower"
        self.voted_for = None

    # Reset election timeout (we've heard from valid leader)
    self.reset_election_timeout()

    # 2. Reply false if log doesn't contain an entry at prevLogIndex
    # whose term matches prevLogTerm (§5.3)
    if prev_log_index >= 0:
        if prev_log_index >= len(self.log):
            return {"term": self.current_term, "success": False}

        if self.log[prev_log_index].term != prev_log_term:
            return {"term": self.current_term, "success": False}

    # 3. If an existing entry conflicts with a new one (same index
    # but different terms), delete the existing entry and all that
    # follow it (§5.3)
    log_index = prev_log_index + 1
    for i, entry in enumerate(entries):
        if log_index + i < len(self.log):
            if self.log[log_index + i].term != entry.term:
                # Delete conflicting entry and all that follow
                self.log = self.log[:log_index + i]
                self.log.append(entry)
        else:
            # 4. Append any new entries not already in the log
            self.log.append(entry)

    # 5. If leaderCommit > commitIndex, set commitIndex =
    # min(leaderCommit, index of last new entry)
    if leader_commit > self.commit_index:
        self.commit_index = min(leader_commit, len(self.log) - 1)
        self.apply_committed_entries()

    return {"term": self.current_term, "success": True}
```

### Leader Log Replication

```python
def replicate_to_followers(self):
    """Send AppendEntries to all followers (§5.3)"""

    for follower_id in self.cluster_nodes:
        if follower_id == self.node_id:
            continue

        # Determine entries to send
        next_index = self.next_index[follower_id]
        prev_log_index = next_index - 1
        prev_log_term = self.log[prev_log_index].term if prev_log_index >= 0 else 0
        entries = self.log[next_index:]

        response = self.send_append_entries(
            follower_id,
            self.current_term,
            self.node_id,
            prev_log_index,
            prev_log_term,
            entries,
            self.commit_index
        )

        # If response contains term T > currentTerm: set currentTerm = T,
        # convert to follower (§5.1)
        if response["term"] > self.current_term:
            self.current_term = response["term"]
            self.state = "follower"
            self.voted_for = None
            return

        if response["success"]:
            # Update nextIndex and matchIndex for follower (§5.3)
            self.next_index[follower_id] = next_index + len(entries)
            self.match_index[follower_id] = self.next_index[follower_id] - 1

            # If there exists an N such that N > commitIndex, a majority
            # of matchIndex[i] ≥ N, and log[N].term == currentTerm:
            # set commitIndex = N (§5.3, §5.4)
            self.try_commit()
        else:
            # If AppendEntries fails because of log inconsistency:
            # decrement nextIndex and retry (§5.3)
            self.next_index[follower_id] = max(0, self.next_index[follower_id] - 1)


def try_commit(self):
    """Advance commitIndex if majority of servers have replicated entry"""

    # Try each index from commitIndex+1 to end of log
    for n in range(self.commit_index + 1, len(self.log)):
        # Only commit entries from current term (§5.4.2)
        if self.log[n].term != self.current_term:
            continue

        # Count how many servers have replicated this entry
        replicas = 1  # Leader has it
        for follower_id in self.cluster_nodes:
            if follower_id == self.node_id:
                continue
            if self.match_index[follower_id] >= n:
                replicas += 1

        # If majority of servers have replicated: commit
        if replicas > len(self.cluster_nodes) / 2:
            self.commit_index = n
            self.apply_committed_entries()
```

---

## Safety Properties and Proofs

### Five Key Safety Properties

#### 1. Election Safety
**Property**: At most one leader can be elected in a given term.

**Proof**: A candidate must receive votes from a majority of servers to win election. Each server votes for at most one candidate in a given term. Two different candidates cannot both receive majorities in the same term.

#### 2. Leader Append-Only
**Property**: A leader never overwrites or deletes entries in its log; it only appends new entries.

**Proof**: By design - leader code only appends entries, never modifies existing ones.

#### 3. Log Matching
**Property**: If two logs contain an entry with the same index and term, then the logs are identical in all entries up through the given index.

**Proof (by induction)**:
- **Base case**: Empty logs trivially satisfy property
- **Inductive step**: When leader sends AppendEntries:
  - Includes prevLogIndex and prevLogTerm
  - Follower only accepts if its log matches at prevLogIndex
  - This guarantees all entries before new entries match
  - New entries appended with same index and term
  - Therefore, all entries up through new index match

#### 4. Leader Completeness
**Property**: If a log entry is committed in a given term, then that entry will be present in the logs of the leaders for all higher-numbered terms.

**Proof sketch**:
1. Entry is committed means majority of servers have replicated it
2. For any new leader to be elected in later term:
   - Must receive votes from majority of servers
   - At least one server in this majority must have the committed entry
   - RequestVote includes log position check
   - Candidate with incomplete log won't receive vote from servers with more complete logs
3. Therefore, new leader must have all committed entries

**Detailed proof** (by contradiction):
Assume leader L in term T commits entry E at index I, but later leader L' in term T' > T does not have E.

Let L' be the first leader after term T that doesn't have E. Then:
1. L' must have won election in term T'
2. To win, L' received votes from majority M' of servers
3. When L committed E, majority M of servers had E
4. M and M' must overlap (pigeonhole principle)
5. Let S be a server in M ∩ M'
6. S had E when L committed it
7. S voted for L' in term T' > T
8. But RequestVote checks log completeness
9. S would not vote for L' if E is missing (contradiction)

#### 5. State Machine Safety
**Property**: If a server has applied a log entry at a given index to its state machine, no other server will ever apply a different log entry for the same index.

**Proof**: Follows from Leader Completeness and Log Matching properties.

---

## Cluster Membership Changes

### Joint Consensus Approach

**Problem**: Changing cluster membership (adding/removing servers) risks creating split-brain scenario during transition.

**Solution**: Use joint consensus configuration where both old and new configurations must agree.

```
Phase 1: C_old  -->  C_old,new (joint consensus)
Phase 2: C_old,new  -->  C_new
```

**During joint consensus**:
- Log entries replicated to all servers in both configurations
- Any server from either configuration may serve as leader
- Agreement requires separate majorities from both C_old and C_new

**Safety guarantee**: C_old and C_new cannot both make unilateral decisions during transition.

### Algorithm

```python
def add_server(self, new_server_id):
    """Add server to cluster (§6)"""

    # Phase 1: Switch to C_old,new
    config_entry = LogEntry(
        term=self.current_term,
        command={"type": "config", "config": "joint", "new_server": new_server_id}
    )
    self.log.append(config_entry)
    self.replicate_to_followers()

    # Wait for C_old,new to be committed
    while self.commit_index < len(self.log) - 1:
        time.sleep(0.01)

    # Phase 2: Switch to C_new
    config_entry = LogEntry(
        term=self.current_term,
        command={"type": "config", "config": "new"}
    )
    self.log.append(config_entry)
    self.replicate_to_followers()
```

---

## etcd Implementation Details

### Architecture

```
┌────────────────────────────────────────────────┐
│               etcd Architecture                 │
├────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┐      ┌──────────────┐        │
│  │ gRPC Server │──────│  RAFT Module │        │
│  └─────────────┘      └──────────────┘        │
│         │                     │                 │
│         │                     ▼                 │
│         │            ┌──────────────┐          │
│         │            │  Write-Ahead │          │
│         │            │  Log (WAL)   │          │
│         │            └──────────────┘          │
│         │                     │                 │
│         ▼                     ▼                 │
│  ┌──────────────────────────────────┐          │
│  │      BoltDB (Key-Value Store)    │          │
│  └──────────────────────────────────┘          │
│                                                 │
└────────────────────────────────────────────────┘
```

### Key Components

#### 1. RAFT Module (etcd-io/raft)
```go
// Core RAFT state machine implementation
type raft struct {
    id         uint64    // Node ID
    Term       uint64    // Current term
    Vote       uint64    // Voted for in current term
    raftLog    *raftLog  // Log entries
    state      StateType // follower/candidate/leader

    // Election
    electionElapsed  int
    heartbeatElapsed int
    randomizedElectionTimeout int

    // Leader state
    leadTransferee uint64
    prs            map[uint64]*Progress // Follower progress
}
```

#### 2. Write-Ahead Log (WAL)
```go
// Persistent log storage
type WAL struct {
    dir string      // Directory for WAL files
    seq uint64      // Current file sequence number
    encoder *encoder // Protobuf encoder

    // Entries written to WAL before applied to state machine
    // Ensures durability and crash recovery
}
```

#### 3. Storage Backend (BoltDB)
```
BoltDB: Embedded key-value database
- MVCC (Multi-Version Concurrency Control)
- B+ tree structure
- ACID transactions
- Memory-mapped files for performance
```

### etcd Client Operations

#### Linearizable Read (Default)
```go
// Ensures read sees most recent committed value
// Goes through RAFT (reads from leader)
resp, err := cli.Get(ctx, "key")
```

#### Serializable Read (Fast, potentially stale)
```go
// May read from follower (lower latency, but might be stale)
resp, err := cli.Get(ctx, "key",
    clientv3.WithSerializable())
```

#### Watch
```go
// Efficiently watch for changes
watchChan := cli.Watch(ctx, "key", clientv3.WithPrefix())
for watchResp := range watchChan {
    for _, event := range watchResp.Events {
        fmt.Printf("%s %s: %s\n", event.Type, event.Kv.Key, event.Kv.Value)
    }
}
```

### etcd Performance Tuning

```bash
# Heartbeat interval (default: 100ms)
--heartbeat-interval 100

# Election timeout (default: 1000ms = 10x heartbeat)
--election-timeout 1000

# Snapshot frequency (default: 10000 entries)
--snapshot-count 10000

# Backend batch interval (default: 100ms)
--backend-batch-interval 100ms

# Backend batch limit (default: 10000)
--backend-batch-limit 10000
```

---

## RAFT vs Paxos Comparison

| Aspect              | RAFT                          | Paxos                        |
|---------------------|-------------------------------|------------------------------|
| **Design Goal**     | Understandability             | Theoretical elegance         |
| **Leadership**      | Strong leader (simplifies)    | No leader (Multi-Paxos adds) |
| **Log structure**   | Contiguous (no gaps)          | Can have gaps                |
| **Leader election** | Randomized timers             | Multiple possible approaches |
| **Safety proof**    | Decomposed, easier to verify  | Elegant but complex          |
| **Learning curve**  | Moderate (2-3 days)           | Steep (weeks to master)      |
| **Implementations** | etcd, Consul, Kafka           | Chubby, Spanner              |
| **Performance**     | Comparable                    | Comparable                   |

### Why RAFT was Created

1. **Paxos issues**:
   - Difficult to understand and implement correctly
   - Original paper focused on single-decree consensus
   - Multi-Paxos requires many practical decisions left unspecified

2. **RAFT advantages**:
   - Separates concerns (leader election, log replication, safety)
   - Strong leader simplifies reasoning
   - More complete specification
   - Extensive correctness proofs in paper

---

## Performance Characteristics

### Latency Factors

```
Write Latency = Network RTT + Disk Sync Time + Quorum Wait

Typical breakdown:
  Network RTT:      0.5-2ms (same datacenter)
  Disk fsync:       1-10ms (depends on hardware)
  Quorum majority:  RTT/2 (can pipeline)

Total:              2-15ms (same datacenter)
                    50-300ms (cross-region)
```

### Throughput

```
Max Throughput ≈ 1 / (Network RTT + Disk Sync)

With batching:
  Small values:   10,000-50,000 ops/sec
  Large values:   1,000-5,000 ops/sec
```

### Optimization Techniques

#### 1. Pipelining
```python
# Send multiple AppendEntries in parallel
# Don't wait for previous to complete
```

#### 2. Batching
```python
# Batch multiple client requests into single log entry
batch = []
for _ in range(batch_size):
    batch.append(get_client_request())
append_log_entry(batch)
```

#### 3. Read Optimization
```python
# Serializable reads from followers (may be stale)
# Linearizable reads from leader only
```

---

## Common Implementation Pitfalls

### 1. Committing Entries from Previous Terms

**Mistake**: Leader tries to commit old entries directly.

**Correct**: Leader can only commit entries from current term. Old entries are committed indirectly when current-term entry is committed (§5.4.2).

```python
# WRONG
for n in range(self.commit_index + 1, len(self.log)):
    if majority_replicated(n):
        self.commit_index = n  # Dangerous!

# CORRECT
for n in range(self.commit_index + 1, len(self.log)):
    if self.log[n].term == self.current_term:  # Only current term!
        if majority_replicated(n):
            self.commit_index = n
```

### 2. Incorrect Election Timeout Reset

**Mistake**: Reset election timeout on receiving any RPC.

**Correct**: Only reset on receiving valid AppendEntries from current leader or when granting vote.

### 3. Split Vote Infinite Loop

**Mistake**: Fixed election timeout (all nodes timeout simultaneously).

**Correct**: Randomized election timeouts prevent synchronized timeouts.

### 4. Not Persisting State

**Mistake**: Keeping currentTerm, votedFor, log only in memory.

**Correct**: Persist to disk before responding to RPCs (§5.2).

```python
def request_vote(self, term, candidate_id, ...):
    if self.should_grant_vote(...):
        self.voted_for = candidate_id
        self.persist_state()  # MUST persist before responding!
        return True
```

### 5. Incorrect Log Matching

**Mistake**: Only checking prevLogIndex, not prevLogTerm.

**Correct**: Must check both prevLogIndex and prevLogTerm match.

---

**References**:
- Original RAFT paper: https://raft.github.io/raft.pdf
- RAFT website: https://raft.github.io/
- etcd source code: https://github.com/etcd-io/etcd
- etcd-io/raft library: https://github.com/etcd-io/raft
- RAFT consensus visualization: http://thesecretlivesofdata.com/raft/

**Last Updated**: 2025-10-27
