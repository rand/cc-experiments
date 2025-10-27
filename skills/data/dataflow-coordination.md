---
name: data-dataflow-coordination
description: Coordination patterns for distributed dataflow systems including barriers, epochs, and distributed snapshots
---

# Dataflow Coordination

**Scope**: Coordination primitives, barrier synchronization, epoch markers, distributed snapshots, consistency
**Lines**: 370
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

## When to Use This Skill

Use this skill when:
- Coordinating multiple parallel dataflow streams
- Implementing barrier synchronization across workers
- Managing epochs and checkpointing in distributed systems
- Building consistent snapshots of distributed state
- Coordinating multi-stage pipeline computations
- Implementing exactly-once semantics with coordination
- Synchronizing external systems with dataflow progress
- Handling backpressure across distributed workers

## Core Concepts

### Coordination Mechanisms
```
Barriers
  → Synchronization points across parallel streams
  → All workers must reach barrier before proceeding
  → Use for: Global aggregations, checkpointing
  → Cost: Latency spike at barrier

Epochs
  → Logical time units for batching
  → Watermarks: "No data before T will arrive"
  → Use for: Windowing, progress tracking
  → Cost: Buffering until epoch closes

Snapshots
  → Consistent global state capture
  → Chandy-Lamport algorithm
  → Use for: Fault recovery, migration
  → Cost: Storage and I/O overhead
```

### Progress Tracking Models
```
Global Frontier
  → Minimum timestamp across all workers
  → Conservative: Waits for slowest worker
  → Guarantees: Completeness at timestamp

Per-Worker Frontiers
  → Independent progress per worker
  → Optimistic: Faster workers proceed
  → Requires: Careful synchronization

Hierarchical Frontiers
  → Per-operator, per-worker tracking
  → Fine-grained progress visibility
  → Complex but enables optimization
```

### Consistency Models
```
Strong Consistency
  → All workers see same state
  → Requires: Global coordination
  → Use for: Financial transactions

Eventual Consistency
  → Workers converge over time
  → Minimal coordination
  → Use for: Analytics, monitoring

Causal Consistency
  → Respects causal relationships
  → Vector clocks, happens-before
  → Use for: Distributed collaboration
```

## Patterns

### Pattern 1: Barrier Synchronization (Rust/Timely)

```rust
use timely::dataflow::{Scope, Stream};
use timely::dataflow::channels::pact::Pipeline;
use timely::dataflow::operators::generic::operator::Operator;
use std::collections::HashMap;

// Barrier that emits when all inputs reach same timestamp
fn barrier<G: Scope>(
    streams: Vec<&Stream<G, i32>>,
) -> Stream<G, Vec<i32>> {
    assert!(!streams.is_empty());

    let mut builder = timely::dataflow::operators::generic::builder_rc::OperatorBuilder::new(
        "Barrier".to_string(),
        streams[0].scope(),
    );

    // Create inputs for all streams
    let mut inputs: Vec<_> = streams.iter()
        .map(|stream| builder.new_input(stream, Pipeline))
        .collect();

    let (mut output, stream) = builder.new_output();

    builder.build(move |_capability| {
        let num_inputs = inputs.len();
        let mut buffers: HashMap<G::Timestamp, Vec<Vec<i32>>> = HashMap::new();

        move |_frontiers| {
            // Collect data from all inputs
            for (idx, input) in inputs.iter_mut().enumerate() {
                input.for_each(|time, data| {
                    let entry = buffers.entry(time.time().clone())
                        .or_insert_with(|| vec![Vec::new(); num_inputs]);
                    entry[idx].extend(data.iter().cloned());
                });
            }

            // Emit when all inputs have data at timestamp
            let ready: Vec<G::Timestamp> = buffers.iter()
                .filter(|(_, vecs)| vecs.iter().all(|v| !v.is_empty()))
                .map(|(t, _)| t.clone())
                .collect();

            for time in ready {
                if let Some(mut data_vecs) = buffers.remove(&time) {
                    let mut session = output.session(&time);

                    // Combine data from all inputs
                    let combined: Vec<i32> = data_vecs.into_iter()
                        .flat_map(|v| v)
                        .collect();

                    session.give(combined);
                }
            }
        }
    });

    stream
}

// Usage
fn main() {
    use timely::dataflow::operators::{ToStream, Inspect};

    timely::execute_from_args(std::env::args(), |worker| {
        worker.dataflow::<u64, _, _>(|scope| {
            let stream1 = (0..5).to_stream(scope);
            let stream2 = (10..15).to_stream(scope);

            barrier(vec![&stream1, &stream2])
                .inspect(|data| println!("Barrier output: {:?}", data));
        });
    }).expect("Execution failed");
}
```

### Pattern 2: Epoch Markers (Go)

```go
package main

import (
    "fmt"
    "sync"
    "time"
)

// EpochCoordinator manages epoch transitions across workers
type EpochCoordinator struct {
    currentEpoch int64
    numWorkers   int
    barriers     map[int64]*sync.WaitGroup
    mu           sync.Mutex
}

func NewEpochCoordinator(numWorkers int) *EpochCoordinator {
    return &EpochCoordinator{
        currentEpoch: 0,
        numWorkers:   numWorkers,
        barriers:     make(map[int64]*sync.WaitGroup),
    }
}

// ArriveAtEpoch signals that worker has reached epoch
func (ec *EpochCoordinator) ArriveAtEpoch(workerID int, epoch int64) {
    ec.mu.Lock()
    defer ec.mu.Unlock()

    // Create barrier for this epoch if needed
    if _, exists := ec.barriers[epoch]; !exists {
        ec.barriers[epoch] = &sync.WaitGroup{}
        ec.barriers[epoch].Add(ec.numWorkers)
    }

    fmt.Printf("Worker %d arrived at epoch %d\n", workerID, epoch)
    ec.barriers[epoch].Done()
}

// WaitForEpoch blocks until all workers reach epoch
func (ec *EpochCoordinator) WaitForEpoch(epoch int64) {
    ec.mu.Lock()
    barrier := ec.barriers[epoch]
    ec.mu.Unlock()

    if barrier != nil {
        barrier.Wait()
        fmt.Printf("Epoch %d complete\n", epoch)

        // Clean up old barriers
        ec.mu.Lock()
        delete(ec.barriers, epoch)
        ec.mu.Unlock()
    }
}

// AdvanceEpoch moves to next epoch
func (ec *EpochCoordinator) AdvanceEpoch() int64 {
    ec.mu.Lock()
    defer ec.mu.Unlock()

    ec.currentEpoch++
    return ec.currentEpoch
}

// Worker simulates dataflow worker with epoch coordination
func worker(id int, coordinator *EpochCoordinator, wg *sync.WaitGroup) {
    defer wg.Done()

    for epoch := int64(0); epoch < 5; epoch++ {
        // Simulate work
        time.Sleep(time.Duration(id*100) * time.Millisecond)
        fmt.Printf("Worker %d processing epoch %d\n", id, epoch)

        // Signal arrival at epoch barrier
        coordinator.ArriveAtEpoch(id, epoch)

        // Wait for all workers to reach epoch
        coordinator.WaitForEpoch(epoch)
    }
}

func main() {
    numWorkers := 3
    coordinator := NewEpochCoordinator(numWorkers)

    var wg sync.WaitGroup
    wg.Add(numWorkers)

    for i := 0; i < numWorkers; i++ {
        go worker(i, coordinator, &wg)
    }

    wg.Wait()
    fmt.Println("All workers complete")
}
```

### Pattern 3: Distributed Snapshot (Chandy-Lamport)

```python
import threading
import queue
from dataclasses import dataclass
from typing import Dict, List, Set
from enum import Enum

class MessageType(Enum):
    DATA = 1
    MARKER = 2

@dataclass
class Message:
    msg_type: MessageType
    data: any
    snapshot_id: int = 0

class SnapshotWorker:
    """Implements Chandy-Lamport snapshot algorithm"""

    def __init__(self, worker_id: int, neighbors: List[int]):
        self.worker_id = worker_id
        self.neighbors = neighbors
        self.state = {}  # Local state
        self.channels: Dict[int, queue.Queue] = {}  # Input channels

        # Snapshot state
        self.recording: Dict[int, bool] = {}  # Per snapshot
        self.recorded_state: Dict[int, dict] = {}  # Snapshot ID -> state
        self.recorded_messages: Dict[int, Dict[int, List]] = {}  # Snapshot -> channel -> messages
        self.markers_received: Dict[int, Set[int]] = {}  # Snapshot -> set of channels

        # Initialize channels
        for neighbor in neighbors:
            self.channels[neighbor] = queue.Queue()

    def start_snapshot(self, snapshot_id: int):
        """Initiate snapshot (only by coordinator)"""
        print(f"Worker {self.worker_id}: Starting snapshot {snapshot_id}")

        # Record local state
        self.recorded_state[snapshot_id] = self.state.copy()
        self.recording[snapshot_id] = True
        self.recorded_messages[snapshot_id] = {n: [] for n in self.neighbors}
        self.markers_received[snapshot_id] = set()

        # Send markers to all neighbors
        for neighbor in self.neighbors:
            self.send_message(neighbor, Message(MessageType.MARKER, None, snapshot_id))

    def receive_marker(self, snapshot_id: int, from_channel: int):
        """Handle marker message"""
        if snapshot_id not in self.recording:
            # First marker for this snapshot
            print(f"Worker {self.worker_id}: Received first marker for snapshot {snapshot_id}")

            # Record state
            self.recorded_state[snapshot_id] = self.state.copy()
            self.recording[snapshot_id] = True
            self.recorded_messages[snapshot_id] = {n: [] for n in self.neighbors}
            self.markers_received[snapshot_id] = {from_channel}

            # Channel from which marker arrived is empty
            self.recorded_messages[snapshot_id][from_channel] = []

            # Send markers to all neighbors
            for neighbor in self.neighbors:
                self.send_message(neighbor, Message(MessageType.MARKER, None, snapshot_id))
        else:
            # Subsequent marker
            print(f"Worker {self.worker_id}: Received marker from channel {from_channel}")
            self.markers_received[snapshot_id].add(from_channel)

        # Check if snapshot complete
        if len(self.markers_received[snapshot_id]) == len(self.neighbors):
            self.finalize_snapshot(snapshot_id)

    def receive_data(self, data: any, from_channel: int):
        """Handle data message"""
        # Process data (update state)
        self.state[f'key_{len(self.state)}'] = data

        # Record message if snapshot in progress
        for snapshot_id, recording in self.recording.items():
            if recording and from_channel not in self.markers_received.get(snapshot_id, set()):
                # Recording messages on this channel
                self.recorded_messages[snapshot_id][from_channel].append(data)

    def finalize_snapshot(self, snapshot_id: int):
        """Snapshot complete for this worker"""
        print(f"Worker {self.worker_id}: Snapshot {snapshot_id} complete")
        print(f"  State: {self.recorded_state[snapshot_id]}")
        print(f"  Messages: {self.recorded_messages[snapshot_id]}")

        self.recording[snapshot_id] = False

    def send_message(self, to_worker: int, message: Message):
        """Send message to another worker (simulated)"""
        # In real system, this would send over network
        pass

# Example usage
def main():
    # Create 3 workers in ring topology: 0 -> 1 -> 2 -> 0
    workers = [
        SnapshotWorker(0, [1, 2]),
        SnapshotWorker(1, [0, 2]),
        SnapshotWorker(2, [0, 1]),
    ]

    # Simulate some processing
    workers[0].state = {'count': 10}
    workers[1].state = {'count': 20}
    workers[2].state = {'count': 30}

    # Initiate snapshot from worker 0
    workers[0].start_snapshot(snapshot_id=1)

    # Simulate marker propagation
    workers[1].receive_marker(snapshot_id=1, from_channel=0)
    workers[2].receive_marker(snapshot_id=1, from_channel=1)
    workers[0].receive_marker(snapshot_id=1, from_channel=2)
    workers[1].receive_marker(snapshot_id=1, from_channel=2)
    workers[2].receive_marker(snapshot_id=1, from_channel=0)

if __name__ == '__main__':
    main()
```

### Pattern 4: Backpressure Coordination (Python)

```python
import asyncio
from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class Watermark:
    """Progress indicator for backpressure"""
    timestamp: int
    worker_id: int

class BackpressureCoordinator:
    """Coordinates flow control across pipeline stages"""

    def __init__(self, num_workers: int, buffer_size: int = 100):
        self.num_workers = num_workers
        self.buffer_size = buffer_size
        self.worker_watermarks = [0] * num_workers
        self.global_watermark = 0
        self.lock = asyncio.Lock()

    async def update_watermark(self, worker_id: int, timestamp: int):
        """Update watermark for worker"""
        async with self.lock:
            self.worker_watermarks[worker_id] = timestamp
            old_global = self.global_watermark
            self.global_watermark = min(self.worker_watermarks)

            if self.global_watermark > old_global:
                print(f"Global watermark advanced to {self.global_watermark}")

    async def can_proceed(self, worker_id: int, timestamp: int) -> bool:
        """Check if worker can proceed without overwhelming downstream"""
        async with self.lock:
            # Allow if within buffer_size of slowest worker
            return timestamp <= self.global_watermark + self.buffer_size

    async def get_global_watermark(self) -> int:
        async with self.lock:
            return self.global_watermark

class PipelineStage:
    """Dataflow pipeline stage with backpressure"""

    def __init__(
        self,
        stage_id: int,
        coordinator: BackpressureCoordinator,
        input_queue: asyncio.Queue,
        output_queue: Optional[asyncio.Queue] = None
    ):
        self.stage_id = stage_id
        self.coordinator = coordinator
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.current_timestamp = 0

    async def process(self):
        """Process data with backpressure"""
        while True:
            try:
                data = await asyncio.wait_for(
                    self.input_queue.get(),
                    timeout=1.0
                )

                if data is None:  # Shutdown signal
                    if self.output_queue:
                        await self.output_queue.put(None)
                    break

                timestamp, value = data

                # Check backpressure before proceeding
                while not await self.coordinator.can_proceed(self.stage_id, timestamp):
                    print(f"Stage {self.stage_id}: Backpressure at timestamp {timestamp}")
                    await asyncio.sleep(0.1)

                # Process data (simulate work)
                await asyncio.sleep(0.01)
                processed = value * 2

                # Update watermark
                self.current_timestamp = timestamp
                await self.coordinator.update_watermark(self.stage_id, timestamp)

                # Send to next stage
                if self.output_queue:
                    await self.output_queue.put((timestamp, processed))

            except asyncio.TimeoutError:
                continue

async def main():
    num_stages = 3
    coordinator = BackpressureCoordinator(num_stages, buffer_size=50)

    # Create pipeline: source -> stage1 -> stage2 -> sink
    queues = [asyncio.Queue() for _ in range(num_stages)]

    stages = [
        PipelineStage(0, coordinator, queues[0], queues[1]),
        PipelineStage(1, coordinator, queues[1], queues[2]),
        PipelineStage(2, coordinator, queues[2], None),
    ]

    # Start processing
    tasks = [asyncio.create_task(stage.process()) for stage in stages]

    # Feed data
    for i in range(200):
        await queues[0].put((i, i))
        await asyncio.sleep(0.005)  # Fast producer

    # Shutdown
    await queues[0].put(None)

    # Wait for completion
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
```

### Pattern 5: Causal Consistency with Vector Clocks (Go)

```go
package main

import (
    "fmt"
    "sync"
)

// VectorClock tracks causal relationships
type VectorClock map[int]int

func (vc VectorClock) Copy() VectorClock {
    copy := make(VectorClock)
    for k, v := range vc {
        copy[k] = v
    }
    return copy
}

func (vc VectorClock) Increment(nodeID int) {
    vc[nodeID]++
}

func (vc VectorClock) Merge(other VectorClock) {
    for nodeID, timestamp := range other {
        if current, exists := vc[nodeID]; !exists || timestamp > current {
            vc[nodeID] = timestamp
        }
    }
}

func (vc VectorClock) HappensBefore(other VectorClock) bool {
    lessOrEqual := true
    strictlyLess := false

    for nodeID := range vc {
        if vc[nodeID] > other[nodeID] {
            return false // Not happens-before
        }
        if vc[nodeID] < other[nodeID] {
            strictlyLess = true
        }
    }

    return lessOrEqual && strictlyLess
}

// Event with causal timestamp
type Event struct {
    NodeID int
    Data   string
    Clock  VectorClock
}

// CausalBroadcast ensures causal ordering
type CausalBroadcast struct {
    nodeID   int
    clock    VectorClock
    pending  []Event
    delivered map[string]bool
    mu       sync.Mutex
}

func NewCausalBroadcast(nodeID int, numNodes int) *CausalBroadcast {
    clock := make(VectorClock)
    for i := 0; i < numNodes; i++ {
        clock[i] = 0
    }

    return &CausalBroadcast{
        nodeID:    nodeID,
        clock:     clock,
        pending:   []Event{},
        delivered: make(map[string]bool),
    }
}

func (cb *CausalBroadcast) Send(data string) Event {
    cb.mu.Lock()
    defer cb.mu.Unlock()

    cb.clock.Increment(cb.nodeID)

    event := Event{
        NodeID: cb.nodeID,
        Data:   data,
        Clock:  cb.clock.Copy(),
    }

    fmt.Printf("Node %d: Sent event %s with clock %v\n",
        cb.nodeID, data, event.Clock)

    return event
}

func (cb *CausalBroadcast) Receive(event Event) {
    cb.mu.Lock()
    defer cb.mu.Unlock()

    // Check if can deliver immediately
    if cb.canDeliver(event) {
        cb.deliver(event)
        cb.checkPending()
    } else {
        // Buffer for later
        cb.pending = append(cb.pending, event)
        fmt.Printf("Node %d: Buffered event %s (waiting for causality)\n",
            cb.nodeID, event.Data)
    }
}

func (cb *CausalBroadcast) canDeliver(event Event) bool {
    // Can deliver if:
    // 1. Event from sender is next expected from that sender
    // 2. All causally preceding events delivered

    expected := cb.clock[event.NodeID] + 1
    if event.Clock[event.NodeID] != expected {
        return false
    }

    for nodeID, timestamp := range event.Clock {
        if nodeID != event.NodeID && timestamp > cb.clock[nodeID] {
            return false // Missing causal dependency
        }
    }

    return true
}

func (cb *CausalBroadcast) deliver(event Event) {
    cb.clock.Merge(event.Clock)
    cb.delivered[event.Data] = true

    fmt.Printf("Node %d: Delivered event %s with clock %v\n",
        cb.nodeID, event.Data, event.Clock)
}

func (cb *CausalBroadcast) checkPending() {
    // Try to deliver pending events
    var stillPending []Event

    for _, event := range cb.pending {
        if cb.canDeliver(event) {
            cb.deliver(event)
        } else {
            stillPending = append(stillPending, event)
        }
    }

    cb.pending = stillPending
}

func main() {
    // Create 3 nodes
    nodes := []*CausalBroadcast{
        NewCausalBroadcast(0, 3),
        NewCausalBroadcast(1, 3),
        NewCausalBroadcast(2, 3),
    }

    // Node 0 sends event A
    eventA := nodes[0].Send("A")

    // Node 0 sends event B (causally after A)
    eventB := nodes[0].Send("B")

    // Node 1 receives events out of order
    nodes[1].Receive(eventB) // Should buffer
    nodes[1].Receive(eventA) // Should deliver both A and B
}
```

## Quick Reference

### Coordination Patterns
```
Barrier: Wait for all workers at sync point
Epoch: Logical time units for batching
Watermark: "No data before T will arrive"
Snapshot: Consistent global state capture
Vector Clock: Track causal dependencies
```

### Trade-offs
```
Strong Coordination
  Pros: Consistency, simplicity
  Cons: Latency, throughput impact

Weak Coordination
  Pros: Low latency, high throughput
  Cons: Complex, eventual consistency
```

## Anti-Patterns

```
❌ NEVER: Use global locks in hot path
   → Use lock-free coordination or partitioning

❌ NEVER: Block all workers for slow worker
   → Use timeout or skip slow worker with compensation

❌ NEVER: Ignore stragglers in barrier
   → Implement timeout and speculative execution

❌ NEVER: Take snapshots synchronously in critical path
   → Use background checkpointing

❌ NEVER: Use barriers for every record
   → Batch into epochs for efficiency

❌ NEVER: Assume synchronized clocks
   → Use logical clocks (Lamport, vector)

❌ NEVER: Coordinate without backpressure
   → Fast producers overwhelm slow consumers

❌ NEVER: Hardcode barrier counts
   → Use dynamic registration for elasticity
```

## Related Skills

- `timely-dataflow.md` - Progress tracking in timely dataflow
- `differential-dataflow.md` - Incremental computation
- `streaming-aggregations.md` - Windowing with watermarks
- `stream-processing.md` - High-level stream processing

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
