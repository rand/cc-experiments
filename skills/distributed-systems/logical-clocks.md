---
name: distributed-systems-logical-clocks
description: Lamport logical clocks for establishing happened-before ordering in distributed systems without synchronized physical clocks
---

# Logical Clocks

**Scope**: Lamport clocks, happened-before, logical time, total ordering
**Lines**: ~260
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Ordering events in distributed systems
- Understanding Lamport's seminal work
- Implementing simple causality tracking
- Building distributed snapshots
- Debugging distributed systems
- Understanding logical time foundations
- Implementing total order broadcast
- Learning distributed systems basics

## Core Concepts

### The Problem: Physical Clocks Unreliable

```
Server A (clock: 10:00:00): Event X
Server B (clock: 09:59:59): Event Y

Physical time says X after Y, but maybe:
- B's clock is slow
- Network delay
- Events actually concurrent
```

**Solution**: Logical time based on causality, not physical time

### Happened-Before Relation (→)

**Definition** (Lamport, 1978):

Event `a` happened-before event `b` (written `a → b`) if:
1. `a` and `b` on same process, `a` occurs before `b`
2. `a` is send event, `b` is receive of same message
3. Transitive: if `a → b` and `b → c`, then `a → c`

If neither `a → b` nor `b → a`, then `a` and `b` are **concurrent**.

---

## Lamport Clocks

### Algorithm

```python
class LamportClock:
    """Lamport logical clock"""

    def __init__(self):
        self.time = 0

    def tick(self):
        """Increment clock on local event"""
        self.time += 1
        return self.time

    def send_event(self):
        """Prepare timestamp for sending in message"""
        self.time += 1
        return self.time

    def receive_event(self, received_time):
        """Update clock upon receiving message"""
        self.time = max(self.time, received_time) + 1
        return self.time

# Usage
clock_a = LamportClock()
clock_b = LamportClock()

# Process A: local events
t1 = clock_a.tick()  # t1 = 1

# Process A: send message
msg_time = clock_a.send_event()  # msg_time = 2

# Process B: receive message
clock_b.receive_event(msg_time)  # B's time = max(0, 2) + 1 = 3

# Process B: local event
t2 = clock_b.tick()  # t2 = 4
```

### Clock Condition

**Property**: If `a → b`, then `C(a) < C(b)`

**Note**: Converse not true! `C(a) < C(b)` does NOT imply `a → b`

**Limitation**: Can't detect concurrency
```
Process A: C=1, C=2, C=3
Process B:      C=1, C=2

A:C=2 and B:C=2 concurrent? Unknown from clocks alone!
```

---

## Total Ordering

### Problem: Partial Order Not Enough

**Scenario**: Distributed mutual exclusion needs total order

**Solution**: Break ties with process ID

```python
class TotalOrderClock:
    """Lamport clock with total ordering"""

    def __init__(self, process_id):
        self.process_id = process_id
        self.time = 0

    def tick(self):
        self.time += 1
        return (self.time, self.process_id)

    def send_event(self):
        self.time += 1
        return (self.time, self.process_id)

    def receive_event(self, received_time, sender_id):
        self.time = max(self.time, received_time) + 1
        return (self.time, self.process_id)

    @staticmethod
    def compare(timestamp1, timestamp2):
        """Total order comparison"""
        time1, pid1 = timestamp1
        time2, pid2 = timestamp2

        if time1 < time2:
            return -1
        elif time1 > time2:
            return 1
        else:
            # Same logical time - break tie with process ID
            return -1 if pid1 < pid2 else (1 if pid1 > pid2 else 0)
```

---

## Practical Applications

### Application 1: Distributed Mutual Exclusion

```python
import heapq
from typing import Set

class DistributedMutex:
    """Lamport's distributed mutual exclusion"""

    def __init__(self, process_id, all_processes):
        self.process_id = process_id
        self.all_processes = all_processes
        self.clock = TotalOrderClock(process_id)
        self.request_queue = []  # Priority queue of (timestamp, process_id)
        self.replies_received = set()

    def request_lock(self):
        """Request access to critical section"""
        timestamp = self.clock.send_event()

        # Add own request to queue
        heapq.heappush(self.request_queue, (timestamp, self.process_id))

        # Broadcast request to all processes
        for proc in self.all_processes:
            if proc != self.process_id:
                self.send_request(proc, timestamp)

        # Wait for replies from all other processes
        while len(self.replies_received) < len(self.all_processes) - 1:
            pass  # In real system, would wait on condition variable

    def receive_request(self, sender_id, request_timestamp):
        """Handle lock request from another process"""
        self.clock.receive_event(request_timestamp[0], sender_id)

        # Add to queue
        heapq.heappush(self.request_queue, (request_timestamp, sender_id))

        # Send reply
        reply_timestamp = self.clock.send_event()
        self.send_reply(sender_id, reply_timestamp)

    def receive_reply(self, sender_id):
        """Handle reply from another process"""
        self.replies_received.add(sender_id)

    def can_enter_cs(self):
        """Check if can enter critical section"""
        if not self.request_queue:
            return False

        # Own request must be at head of queue
        earliest = self.request_queue[0]
        return earliest[1] == self.process_id

    def release_lock(self):
        """Release lock after critical section"""
        # Remove own request
        heapq.heappop(self.request_queue)

        # Broadcast release to all
        timestamp = self.clock.send_event()
        for proc in self.all_processes:
            if proc != self.process_id:
                self.send_release(proc, timestamp)

    def receive_release(self, sender_id):
        """Handle release from another process"""
        # Remove sender's request from queue
        self.request_queue = [
            (ts, pid) for (ts, pid) in self.request_queue
            if pid != sender_id
        ]
        heapq.heapify(self.request_queue)
```

### Application 2: Causal Logging

```python
class CausalLogger:
    """Log events with causal ordering"""

    def __init__(self, node_id):
        self.node_id = node_id
        self.clock = LamportClock()
        self.log = []

    def log_event(self, event_type, data):
        """Log local event"""
        timestamp = self.clock.tick()
        log_entry = {
            'timestamp': timestamp,
            'node': self.node_id,
            'type': event_type,
            'data': data
        }
        self.log.append(log_entry)
        return timestamp

    def log_send(self, recipient, message):
        """Log message send"""
        timestamp = self.clock.send_event()
        self.log.append({
            'timestamp': timestamp,
            'node': self.node_id,
            'type': 'send',
            'recipient': recipient,
            'message': message
        })
        return timestamp

    def log_receive(self, sender, message, sender_timestamp):
        """Log message receive"""
        timestamp = self.clock.receive_event(sender_timestamp)
        self.log.append({
            'timestamp': timestamp,
            'node': self.node_id,
            'type': 'receive',
            'sender': sender,
            'message': message,
            'sender_timestamp': sender_timestamp
        })
        return timestamp

    def get_ordered_log(self):
        """Get log entries in happened-before order"""
        return sorted(self.log, key=lambda x: x['timestamp'])
```

---

## Distributed Snapshots

### Chandy-Lamport Snapshot Algorithm

```python
class SnapshotManager:
    """Distributed snapshot using logical clocks"""

    def __init__(self, process_id, channels):
        self.process_id = process_id
        self.channels = channels  # Other processes
        self.clock = LamportClock()
        self.state = {}
        self.snapshot_state = None
        self.snapshot_in_progress = False
        self.channel_states = {}  # Messages in transit

    def initiate_snapshot(self):
        """Start snapshot (by any process)"""
        self.snapshot_in_progress = True
        self.snapshot_state = self.state.copy()

        # Record state of all channels
        for channel in self.channels:
            self.channel_states[channel] = []

        # Send marker on all outgoing channels
        for channel in self.channels:
            self.send_marker(channel)

    def receive_marker(self, sender):
        """Handle marker from another process"""
        if not self.snapshot_in_progress:
            # First marker received - take snapshot
            self.initiate_snapshot()
            self.channel_states[sender] = []  # Empty (no messages before marker)
        else:
            # Already snapshotting - stop recording on this channel
            # Messages received after marker not in snapshot
            pass

    def receive_message(self, sender, message):
        """Handle regular message"""
        if self.snapshot_in_progress and sender in self.channel_states:
            # Record message as part of channel state
            self.channel_states[sender].append(message)

        # Process message normally
        self.clock.receive_event(message['timestamp'])
```

---

## Limitations

```
❌ Can't detect concurrency (unlike vector clocks)
❌ Clock values can grow large
❌ Doesn't capture full causality
✅ Simple and efficient
✅ Establishes partial order
✅ Foundation for other algorithms
```

---

## Comparison

| Clock Type | Space | Detects Concurrency | Use Case |
|------------|-------|-------------------|----------|
| **Physical** | O(1) | ❌ No | When synchronized clocks available |
| **Lamport** | O(1) | ❌ No | Simple ordering, total order needed |
| **Vector** | O(N) | ✅ Yes | Conflict detection, versioning |
| **Hybrid** | O(1) + physical | Partially | Balance simplicity and accuracy |

---

## Testing

```python
import unittest

class TestLamportClock(unittest.TestCase):
    def test_local_events(self):
        """Test local event ordering"""
        clock = LamportClock()
        t1 = clock.tick()
        t2 = clock.tick()
        self.assertLess(t1, t2)

    def test_message_passing(self):
        """Test clock update on message passing"""
        clock_a = LamportClock()
        clock_b = LamportClock()

        # A: several local events
        clock_a.tick()
        clock_a.tick()
        clock_a.tick()

        # A sends to B
        msg_time = clock_a.send_event()  # 4

        # B receives
        clock_b.receive_event(msg_time)

        # B's clock should jump
        self.assertGreater(clock_b.time, msg_time)

    def test_clock_condition(self):
        """Test happened-before implies clock ordering"""
        clock_a = LamportClock()
        clock_b = LamportClock()

        t1 = clock_a.tick()
        send_time = clock_a.send_event()
        recv_time = clock_b.receive_event(send_time)

        # t1 happened-before recv_time
        self.assertLess(t1, recv_time)
```

---

## Related Skills

- `distributed-systems-vector-clocks` - Full causality tracking
- `distributed-systems-interval-tree-clocks` - Scalable clocks
- `distributed-systems-distributed-locks` - Mutual exclusion
- `distributed-systems-eventual-consistency` - Ordering in eventual consistency

---

**Last Updated**: 2025-10-27
