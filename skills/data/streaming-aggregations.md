---
name: data-streaming-aggregations
description: Windowing, sessionization, time-series aggregation, and late data handling for streaming systems
---

# Streaming Aggregations

**Scope**: Windowing strategies, sessionization, time-series aggregation, watermarks, late data handling
**Lines**: 385
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

## When to Use This Skill

Use this skill when:
- Aggregating unbounded streams (counts, sums, averages)
- Implementing time-based windows (tumbling, sliding, session)
- Building real-time dashboards and metrics
- Detecting patterns in time-series data
- Handling out-of-order and late-arriving data
- Computing sessionized analytics (user sessions, click streams)
- Building real-time anomaly detection
- Creating streaming leaderboards and rankings

## Core Concepts

### Window Types
```
Tumbling Windows
  → Fixed size, non-overlapping
  → Example: Count events per 5 minutes
  → Use: Periodic reports, batched processing
  → Memory: O(window_size)

Sliding Windows
  → Fixed size, overlapping
  → Example: Moving average over last 10 minutes
  → Use: Continuous metrics, smoothed trends
  → Memory: O(window_size * slide_factor)

Session Windows
  → Dynamic size, gap-based
  → Example: User sessions with 30-min inactivity
  → Use: User behavior, conversation threads
  → Memory: O(active_sessions)

Global Windows
  → Unbounded, single window
  → Example: All-time counts
  → Use: Stateful processing without time bounds
  → Memory: O(cardinality)
```

### Time Semantics
```
Event Time
  → Time when event occurred
  → Requires: Timestamps in data
  → Accurate but complex (late data)
  → Use: Financial, billing, analytics

Processing Time
  → Time when event processed
  → Simple, low latency
  → Inaccurate for time-based logic
  → Use: Monitoring, system metrics

Ingestion Time
  → Time when event entered system
  → Middle ground
  → Use: Approximation when no event time
```

### Watermarks
```
Watermark(T)
  → "All events before T have arrived"
  → Heuristic, not guarantee
  → Triggers window computation

Strategies:
  → Perfect: Wait forever (impractical)
  → Bounded delay: T = max_timestamp - delay
  → Percentile: Allow X% late data
  → Punctuation: Explicit markers in stream
```

### Late Data Handling
```
Strategies:
  → Drop: Ignore late data (simplest)
  → Update: Recompute window (expensive)
  → Side output: Route to separate stream
  → Allowed lateness: Accept within window

Trade-offs:
  → Accuracy vs Latency
  → Completeness vs Timeliness
```

## Patterns

### Pattern 1: Tumbling Window Aggregation (Rust/Timely)

```rust
use timely::dataflow::operators::{ToStream, Map, Inspect};
use differential_dataflow::input::Input;
use differential_dataflow::operators::{Reduce, Consolidate};
use differential_dataflow::operators::arrange::ArrangeByKey;

#[derive(Clone, Debug, Hash, PartialEq, Eq, PartialOrd, Ord)]
struct Event {
    user_id: u32,
    value: i32,
    timestamp: u64,  // Event time in milliseconds
}

fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        let mut input = worker.dataflow::<u64, _, _>(|scope| {
            let (input, events) = scope.new_collection();

            // Tumbling window: 5-minute (300000ms) windows
            let window_size = 300_000u64;

            events
                .map(move |event| {
                    // Assign to window based on event time
                    let window_id = event.timestamp / window_size;
                    ((event.user_id, window_id), event.value)
                })
                .reduce(|_key, values, output| {
                    let sum: i32 = values.iter()
                        .map(|(value, diff)| value * diff)
                        .sum();
                    let count: i32 = values.iter()
                        .map(|(_, diff)| diff)
                        .sum();
                    output.push(((sum, count), 1));
                })
                .inspect(|((user_id, window_id), (sum, count))| {
                    println!("User {}, Window {}: sum={}, count={}",
                             user_id, window_id, sum, count);
                });

            input
        });

        // Simulate events
        input.insert(Event { user_id: 1, value: 10, timestamp: 100_000 });
        input.insert(Event { user_id: 1, value: 20, timestamp: 150_000 });
        input.insert(Event { user_id: 1, value: 30, timestamp: 350_000 }); // Next window
        input.advance_to(1);
        worker.step_while(|| input.time().less_than(&1));
    }).expect("Execution failed");
}
```

### Pattern 2: Sliding Window (Python)

```python
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict
import threading

@dataclass
class Event:
    timestamp: float
    user_id: str
    value: float

class SlidingWindowAggregator:
    """Sliding window with event-time semantics"""

    def __init__(self, window_size: float, slide_interval: float):
        self.window_size = window_size  # Window size in seconds
        self.slide_interval = slide_interval  # How often to emit
        self.buffers: Dict[str, Deque[Event]] = {}  # Per-key buffers
        self.lock = threading.Lock()

    def process(self, event: Event):
        """Process event and return windows that are ready"""
        with self.lock:
            # Initialize buffer for key
            if event.user_id not in self.buffers:
                self.buffers[event.user_id] = deque()

            buffer = self.buffers[event.user_id]

            # Add event
            buffer.append(event)

            # Remove events outside window
            cutoff = event.timestamp - self.window_size
            while buffer and buffer[0].timestamp < cutoff:
                buffer.popleft()

            # Compute aggregate
            total = sum(e.value for e in buffer)
            count = len(buffer)
            avg = total / count if count > 0 else 0.0

            return {
                'user_id': event.user_id,
                'window_start': cutoff,
                'window_end': event.timestamp,
                'sum': total,
                'count': count,
                'avg': avg
            }

# Usage
def main():
    aggregator = SlidingWindowAggregator(
        window_size=10.0,     # 10-second window
        slide_interval=2.0    # Emit every 2 seconds
    )

    # Simulate event stream
    events = [
        Event(timestamp=1.0, user_id='alice', value=10),
        Event(timestamp=2.0, user_id='alice', value=20),
        Event(timestamp=5.0, user_id='alice', value=30),
        Event(timestamp=12.0, user_id='alice', value=40),  # Outside first window
    ]

    for event in events:
        result = aggregator.process(event)
        print(f"Window result: {result}")

if __name__ == '__main__':
    main()
```

### Pattern 3: Session Windows (Go)

```go
package main

import (
    "fmt"
    "sort"
    "time"
)

type Event struct {
    UserID    string
    Timestamp time.Time
    Value     int
}

type Session struct {
    UserID string
    Start  time.Time
    End    time.Time
    Events []Event
    Sum    int
}

type SessionWindowAggregator struct {
    inactivityGap time.Duration
    sessions      map[string]*Session
}

func NewSessionWindowAggregator(gap time.Duration) *SessionWindowAggregator {
    return &SessionWindowAggregator{
        inactivityGap: gap,
        sessions:      make(map[string]*Session),
    }
}

func (swa *SessionWindowAggregator) Process(event Event) *Session {
    session, exists := swa.sessions[event.UserID]

    if !exists || event.Timestamp.Sub(session.End) > swa.inactivityGap {
        // Start new session
        if exists {
            // Emit completed session
            completed := session
            fmt.Printf("Session complete: %+v\n", completed)
        }

        session = &Session{
            UserID: event.UserID,
            Start:  event.Timestamp,
            End:    event.Timestamp,
            Events: []Event{event},
            Sum:    event.Value,
        }
        swa.sessions[event.UserID] = session
    } else {
        // Extend existing session
        session.End = event.Timestamp
        session.Events = append(session.Events, event)
        session.Sum += event.Value
    }

    return nil
}

func (swa *SessionWindowAggregator) FlushExpired(currentTime time.Time) []*Session {
    var expired []*Session

    for userID, session := range swa.sessions {
        if currentTime.Sub(session.End) > swa.inactivityGap {
            expired = append(expired, session)
            delete(swa.sessions, userID)
        }
    }

    return expired
}

func main() {
    aggregator := NewSessionWindowAggregator(5 * time.Minute)

    // Simulate event stream
    events := []Event{
        {UserID: "alice", Timestamp: time.Now(), Value: 10},
        {UserID: "alice", Timestamp: time.Now().Add(1 * time.Minute), Value: 20},
        {UserID: "alice", Timestamp: time.Now().Add(10 * time.Minute), Value: 30}, // New session
        {UserID: "bob", Timestamp: time.Now().Add(2 * time.Minute), Value: 15},
    }

    for _, event := range events {
        aggregator.Process(event)
    }

    // Flush expired sessions
    expired := aggregator.FlushExpired(time.Now().Add(20 * time.Minute))
    for _, session := range expired {
        fmt.Printf("Expired session: %+v\n", session)
    }
}
```

### Pattern 4: Watermark-Based Late Data Handling (Python)

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
import heapq

@dataclass
class Event:
    timestamp: int  # Event time
    key: str
    value: int

@dataclass
class Window:
    start: int
    end: int
    key: str
    sum: int = 0
    count: int = 0

class WatermarkAggregator:
    """Window aggregator with watermark-based triggering"""

    def __init__(
        self,
        window_size: int,
        allowed_lateness: int,
        watermark_delay: int
    ):
        self.window_size = window_size
        self.allowed_lateness = allowed_lateness
        self.watermark_delay = watermark_delay

        self.windows: Dict[tuple, Window] = {}  # (key, window_start) -> Window
        self.max_timestamp = 0
        self.watermark = 0
        self.late_events: List[Event] = []

    def process(self, event: Event) -> List[Window]:
        """Process event and emit completed windows"""
        # Update max timestamp and watermark
        self.max_timestamp = max(self.max_timestamp, event.timestamp)
        self.watermark = self.max_timestamp - self.watermark_delay

        # Assign to window
        window_start = (event.timestamp // self.window_size) * self.window_size
        window_end = window_start + self.window_size
        window_key = (event.key, window_start)

        # Check if too late
        if event.timestamp < self.watermark - self.allowed_lateness:
            self.late_events.append(event)
            print(f"Late event dropped: {event}")
            return []

        # Update window
        if window_key not in self.windows:
            self.windows[window_key] = Window(
                start=window_start,
                end=window_end,
                key=event.key
            )

        window = self.windows[window_key]
        window.sum += event.value
        window.count += 1

        # Emit completed windows (watermark passed end + allowed lateness)
        return self._emit_completed_windows()

    def _emit_completed_windows(self) -> List[Window]:
        """Emit windows that watermark has passed"""
        completed = []
        to_remove = []

        for (key, window_start), window in self.windows.items():
            # Window complete if watermark > window_end + allowed_lateness
            if self.watermark > window.end + self.allowed_lateness:
                completed.append(window)
                to_remove.append((key, window_start))

        # Remove completed windows
        for key in to_remove:
            del self.windows[key]

        return completed

# Usage
def main():
    aggregator = WatermarkAggregator(
        window_size=10,         # 10-second windows
        allowed_lateness=5,     # Accept events up to 5 seconds late
        watermark_delay=3       # Watermark = max_timestamp - 3
    )

    # Events arriving out of order
    events = [
        Event(timestamp=5, key='user1', value=10),
        Event(timestamp=15, key='user1', value=20),
        Event(timestamp=8, key='user1', value=15),   # Late but within allowed
        Event(timestamp=25, key='user1', value=30),
        Event(timestamp=3, key='user1', value=5),    # Too late, dropped
    ]

    for event in events:
        completed = aggregator.process(event)
        for window in completed:
            print(f"Window complete: {window}")

if __name__ == '__main__':
    main()
```

### Pattern 5: Time-Series Aggregation with Downsampling

```python
import numpy as np
from dataclasses import dataclass
from typing import Dict, List
from collections import defaultdict

@dataclass
class TimeSeriesPoint:
    timestamp: int
    metric: str
    value: float

class TimeSeriesAggregator:
    """Multi-resolution time-series aggregation"""

    def __init__(self):
        # Store multiple resolutions
        self.raw: Dict[str, List[TimeSeriesPoint]] = defaultdict(list)
        self.minute: Dict[str, List[tuple]] = defaultdict(list)  # (timestamp, avg, min, max)
        self.hour: Dict[str, List[tuple]] = defaultdict(list)

    def ingest(self, point: TimeSeriesPoint):
        """Ingest raw point and update aggregations"""
        self.raw[point.metric].append(point)

        # Update minute-level aggregation
        minute_bucket = (point.timestamp // 60) * 60
        self._update_aggregation(point.metric, minute_bucket, point.value, self.minute)

        # Update hour-level aggregation
        hour_bucket = (point.timestamp // 3600) * 3600
        self._update_aggregation(point.metric, hour_bucket, point.value, self.hour)

    def _update_aggregation(
        self,
        metric: str,
        bucket: int,
        value: float,
        storage: Dict[str, List[tuple]]
    ):
        """Update aggregation bucket"""
        buckets = storage[metric]

        # Find or create bucket
        if not buckets or buckets[-1][0] != bucket:
            # New bucket
            buckets.append((bucket, value, value, value, 1))  # (time, sum, min, max, count)
        else:
            # Update existing bucket
            old_time, old_sum, old_min, old_max, old_count = buckets[-1]
            buckets[-1] = (
                old_time,
                old_sum + value,
                min(old_min, value),
                max(old_max, value),
                old_count + 1
            )

    def query(
        self,
        metric: str,
        start: int,
        end: int,
        resolution: str = 'minute'
    ) -> List[tuple]:
        """Query aggregated data at specified resolution"""
        storage = {
            'minute': self.minute,
            'hour': self.hour,
            'raw': self.raw
        }[resolution]

        if resolution == 'raw':
            points = storage[metric]
            filtered = [p for p in points if start <= p.timestamp <= end]
            return [(p.timestamp, p.value) for p in filtered]

        buckets = storage[metric]
        filtered = [
            (timestamp, total/count, min_val, max_val)
            for timestamp, total, min_val, max_val, count in buckets
            if start <= timestamp <= end
        ]

        return filtered

# Usage
def main():
    agg = TimeSeriesAggregator()

    # Ingest high-frequency data
    for i in range(7200):  # 2 hours of second-level data
        point = TimeSeriesPoint(
            timestamp=i,
            metric='cpu_usage',
            value=50 + 10 * np.sin(i / 60.0)  # Simulate pattern
        )
        agg.ingest(point)

    # Query at different resolutions
    minute_data = agg.query('cpu_usage', 0, 3600, resolution='minute')
    print(f"Minute-level aggregation: {len(minute_data)} points")

    hour_data = agg.query('cpu_usage', 0, 7200, resolution='hour')
    print(f"Hour-level aggregation: {len(hour_data)} points")

    # Each point: (timestamp, avg, min, max)
    for timestamp, avg, min_val, max_val in hour_data:
        print(f"Hour {timestamp//3600}: avg={avg:.2f}, min={min_val:.2f}, max={max_val:.2f}")

if __name__ == '__main__':
    main()
```

### Pattern 6: Top-K Streaming Aggregation

```rust
use std::collections::BinaryHeap;
use std::cmp::Reverse;

#[derive(Debug, Clone, Eq, PartialEq)]
struct Item {
    key: String,
    count: usize,
}

impl Ord for Item {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.count.cmp(&other.count)
    }
}

impl PartialOrd for Item {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

struct TopKAggregator {
    k: usize,
    counts: std::collections::HashMap<String, usize>,
    heap: BinaryHeap<Reverse<Item>>,
}

impl TopKAggregator {
    fn new(k: usize) -> Self {
        Self {
            k,
            counts: std::collections::HashMap::new(),
            heap: BinaryHeap::new(),
        }
    }

    fn update(&mut self, key: String) {
        // Update count
        let count = self.counts.entry(key.clone()).or_insert(0);
        *count += 1;

        // Maintain top-K heap
        self.rebuild_heap();
    }

    fn rebuild_heap(&mut self) {
        self.heap.clear();

        for (key, count) in &self.counts {
            let item = Item {
                key: key.clone(),
                count: *count,
            };

            if self.heap.len() < self.k {
                self.heap.push(Reverse(item));
            } else if let Some(Reverse(min)) = self.heap.peek() {
                if item.count > min.count {
                    self.heap.pop();
                    self.heap.push(Reverse(item));
                }
            }
        }
    }

    fn top_k(&self) -> Vec<Item> {
        let mut items: Vec<_> = self.heap.iter()
            .map(|Reverse(item)| item.clone())
            .collect();
        items.sort_by(|a, b| b.count.cmp(&a.count));
        items
    }
}

fn main() {
    let mut aggregator = TopKAggregator::new(3);

    // Simulate event stream
    let events = vec!["apple", "banana", "apple", "cherry", "apple", "banana", "date"];

    for event in events {
        aggregator.update(event.to_string());
    }

    println!("Top 3 items:");
    for item in aggregator.top_k() {
        println!("  {}: {}", item.key, item.count);
    }
}
```

## Quick Reference

### Window Selection Guide
```
Use Tumbling: Periodic reports, non-overlapping batches
Use Sliding: Moving averages, continuous metrics
Use Session: User behavior, conversation analysis
Use Global: Unbounded state, all-time aggregations
```

### Watermark Strategies
```python
# Bounded delay
watermark = max_timestamp - fixed_delay

# Percentile-based
watermark = percentile(timestamps, 99)  # Allow 1% late

# Heuristic
watermark = max_timestamp - 2 * stddev(inter_arrival_time)
```

### Time Extraction
```rust
// Extract event time from data
let event_time = |event: &Event| event.timestamp;

// Assign to window
let window_id = event.timestamp / window_size;

// Session gap check
if current_time - last_event_time > session_gap {
    // Start new session
}
```

## Performance Optimization

```
Reduce State Size
  → Compact old windows
  → Use approximate algorithms (HyperLogLog, Count-Min Sketch)
  → Expire inactive keys

Batch Processing
  → Buffer events before aggregating
  → Periodic window evaluation

Incremental Updates
  → Use differential dataflow for efficient re-aggregation
  → Maintain summary statistics (sum, count) instead of raw data
```

## Anti-Patterns

```
❌ NEVER: Use processing time for event-time logic
   → Results depend on processing speed, not actual event timing

❌ NEVER: Wait indefinitely for late data
   → Set allowed lateness bounds

❌ NEVER: Store unbounded state in global windows
   → Use approximate algorithms or periodic cleanup

❌ NEVER: Ignore watermarks
   → Windows never complete, state grows unbounded

❌ NEVER: Use sliding windows with small slide interval on high-volume streams
   → Creates many overlapping windows, high memory usage

❌ NEVER: Recompute entire window on late data
   → Use incremental updates

❌ NEVER: Assume events arrive in order
   → Always design for out-of-order delivery

❌ NEVER: Use session windows without timeouts
   → Sessions never close, memory leak

❌ NEVER: Emit window before watermark passes
   → Incomplete results

❌ NEVER: Drop late data without logging
   → Monitor late data rates for tuning
```

## Related Skills

- `timely-dataflow.md` - Foundation for windowing with progress tracking
- `differential-dataflow.md` - Incremental window updates
- `dataflow-coordination.md` - Watermarks and coordination
- `stream-processing.md` - High-level stream processing with Kafka

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
