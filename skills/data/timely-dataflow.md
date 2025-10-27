---
name: data-timely-dataflow
description: Timely dataflow framework for low-latency, high-throughput streaming computation with progress tracking
---

# Timely Dataflow

**Scope**: Timely dataflow graphs, progress tracking, dataflow operators, low-latency streaming
**Lines**: 380
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

## When to Use This Skill

Use this skill when:
- Building low-latency streaming computations with Rust
- Implementing dataflow graphs with explicit progress tracking
- Creating custom streaming operators with timely semantics
- Processing unbounded data streams with strong consistency
- Building foundation for differential dataflow applications
- Designing systems requiring fine-grained progress tracking
- Implementing cyclic dataflow computations (iterative algorithms)

## Core Concepts

### Timely Dataflow Architecture
```
Dataflow Graph
  → Directed graph of operators and channels
  → Data flows through edges, computation at nodes
  → Explicit timestamps on all data
  → Progress tracking across entire graph

Workers
  → Single-threaded execution units
  → Shared-nothing architecture
  → Communication via message passing
  → Each worker processes partition of data

Timestamps
  → Logical time, not wall-clock time
  → Partial order (can have multiple dimensions)
  → Enables reasoning about data completeness
  → Foundation for coordination-free execution
```

### Progress Tracking Protocol
```
Capabilities
  → Token representing ability to send data at timestamp
  → Downgrade: Move to later timestamp
  → Drop: Relinquish ability to send at timestamp

Frontier
  → Set of timestamps that may still be produced
  → Minimal set of active timestamps
  → Advances when capabilities downgraded/dropped

Notifications
  → Triggered when frontier advances past timestamp
  → Enables stateful operators to emit results
  → Guarantees: All data at timestamp T received
```

### Dataflow Operators
```
Unary Operators
  → Transform single input stream
  → Examples: map, filter, inspect

Binary Operators
  → Combine two input streams
  → Examples: concat, join (via state)

Feedback/Iteration
  → Connect output back to input
  → Creates cycles in dataflow graph
  → Requires careful timestamp management

Stateful Operators
  → Maintain state indexed by time
  → Emit results when frontier advances
  → Examples: aggregations, joins, windows
```

## Patterns

### Pattern 1: Basic Dataflow Pipeline

```rust
// Cargo.toml
// [dependencies]
// timely = "0.12"

use timely::dataflow::operators::{Inspect, ToStream};

fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        worker.dataflow::<(), _, _>(|scope| {
            // Create input stream
            (0..10)
                .to_stream(scope)
                .inspect(|x| println!("Observed: {}", x));
        });
    }).expect("Execution failed");
}

// Multi-worker execution:
// cargo run -- -w 2  # 2 workers
// cargo run -- -w 4 -p 2  # 4 workers, 2 processes
```

### Pattern 2: Custom Unary Operator

```rust
use timely::dataflow::{Scope, Stream};
use timely::dataflow::channels::pact::Pipeline;
use timely::dataflow::operators::generic::operator::Operator;

// Extension trait for custom operator
trait Multiply<G: Scope> {
    fn multiply(&self, factor: i32) -> Stream<G, i32>;
}

impl<G: Scope> Multiply<G> for Stream<G, i32> {
    fn multiply(&self, factor: i32) -> Stream<G, i32> {
        self.unary(
            Pipeline,  // Exchange strategy
            "Multiply",  // Operator name
            move |_capability, _info| {
                move |input, output| {
                    input.for_each(|time, data| {
                        let mut session = output.session(&time);
                        for datum in data.iter() {
                            session.give(datum * factor);
                        }
                    });
                }
            },
        )
    }
}

// Usage
fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        worker.dataflow::<(), _, _>(|scope| {
            (0..10)
                .to_stream(scope)
                .multiply(5)
                .inspect(|x| println!("Result: {}", x));
        });
    }).expect("Execution failed");
}
```

### Pattern 3: Stateful Aggregation with Progress Tracking

```rust
use timely::dataflow::{Scope, Stream};
use timely::dataflow::channels::pact::Exchange;
use timely::dataflow::operators::generic::operator::Operator;
use std::collections::HashMap;

trait Aggregate<G: Scope<Timestamp = u64>> {
    fn count_by_key(&self) -> Stream<G, (String, usize)>;
}

impl<G: Scope<Timestamp = u64>> Aggregate<G> for Stream<G, (String, i32)> {
    fn count_by_key(&self) -> Stream<G, (String, usize)> {
        self.unary_notify(
            Exchange::new(|x: &(String, i32)| x.0.len() as u64),
            "CountByKey",
            vec![],  // Initial frontier
            move |input, output, notificator| {
                // State: key -> (count, timestamp)
                let mut state: HashMap<String, (usize, u64)> = HashMap::new();

                // Process input
                input.for_each(|time, data| {
                    // Request notification when this time completes
                    notificator.notify_at(time.retain());

                    for (key, _value) in data.iter() {
                        let entry = state.entry(key.clone())
                            .or_insert((0, time.time().clone()));
                        entry.0 += 1;
                        entry.1 = time.time().clone();
                    }
                });

                // Emit results when frontier advances
                notificator.for_each(|time, _count, _notify| {
                    let mut session = output.session(&time);

                    // Find keys at this timestamp
                    let keys: Vec<String> = state.iter()
                        .filter(|(_, (_, t))| t == time.time())
                        .map(|(k, _)| k.clone())
                        .collect();

                    for key in keys {
                        if let Some((count, _)) = state.remove(&key) {
                            session.give((key, count));
                        }
                    }
                });
            },
        )
    }
}

// Usage
fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        use timely::dataflow::operators::ToStream;

        worker.dataflow::<u64, _, _>(|scope| {
            vec![
                ("apple".to_string(), 1),
                ("banana".to_string(), 1),
                ("apple".to_string(), 2),
            ]
            .to_stream(scope)
            .count_by_key()
            .inspect(|(key, count)| {
                println!("Key: {}, Count: {}", key, count);
            });
        });
    }).expect("Execution failed");
}
```

### Pattern 4: Iterative Computation (Feedback Loop)

```rust
use timely::dataflow::{Scope, Stream};
use timely::dataflow::operators::{Inspect, ToStream, Map, Filter, Feedback, ConnectLoop};

fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        worker.dataflow::<u64, _, _>(|scope| {
            // Create feedback loop for iterative computation
            let (handle, cycle) = scope.feedback(1);  // Summary: Product<u64, u32>

            // Initial values
            vec![1, 2, 3, 4, 5]
                .to_stream(scope)
                .map(|x| (x, 0))  // (value, iteration)
                .concat(&cycle)
                .inspect(|(val, iter)| {
                    println!("Iteration {}: value = {}", iter, val);
                })
                .filter(|(val, iter)| *val < 100 && *iter < 10)  // Termination
                .map(|(val, iter)| (val * 2, iter + 1))  // Computation
                .connect_loop(handle);
        });
    }).expect("Execution failed");
}

// Output:
// Iteration 0: value = 1
// Iteration 0: value = 2
// ...
// Iteration 1: value = 2
// Iteration 1: value = 4
// ... (continues until termination)
```

### Pattern 5: Multi-Input Operator (Barrier Pattern)

```rust
use timely::dataflow::{Scope, Stream};
use timely::dataflow::channels::pact::Pipeline;
use timely::dataflow::operators::generic::builder_rc::OperatorBuilder;
use std::collections::HashMap;

fn barrier_join<G: Scope>(
    stream1: &Stream<G, (String, i32)>,
    stream2: &Stream<G, (String, i32)>,
) -> Stream<G, (String, i32, i32)> {
    let mut builder = OperatorBuilder::new("BarrierJoin".to_string(), stream1.scope());

    let mut input1 = builder.new_input(stream1, Pipeline);
    let mut input2 = builder.new_input(stream2, Pipeline);
    let (mut output, stream) = builder.new_output();

    builder.build(move |_capability| {
        // State indexed by time
        let mut buffer1: HashMap<G::Timestamp, Vec<(String, i32)>> = HashMap::new();
        let mut buffer2: HashMap<G::Timestamp, Vec<(String, i32)>> = HashMap::new();

        move |_frontiers| {
            // Read input1
            input1.for_each(|time, data| {
                buffer1.entry(time.time().clone())
                    .or_insert_with(Vec::new)
                    .extend(data.iter().cloned());
            });

            // Read input2
            input2.for_each(|time, data| {
                buffer2.entry(time.time().clone())
                    .or_insert_with(Vec::new)
                    .extend(data.iter().cloned());
            });

            // Process completed times
            let completed: Vec<G::Timestamp> = buffer1.keys()
                .filter(|t| buffer2.contains_key(t))
                .cloned()
                .collect();

            for time in completed {
                if let (Some(data1), Some(data2)) = (buffer1.remove(&time), buffer2.remove(&time)) {
                    let mut session = output.session(&time);

                    // Perform join
                    for (key1, val1) in data1 {
                        for (key2, val2) in &data2 {
                            if key1 == *key2 {
                                session.give((key1.clone(), val1, *val2));
                            }
                        }
                    }
                }
            }
        }
    });

    stream
}
```

### Pattern 6: External Input Source (Probing)

```rust
use timely::dataflow::operators::{Inspect, Probe};
use timely::dataflow::operators::input::Handle;

fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        let mut input = Handle::new();
        let probe = worker.dataflow(|scope| {
            input.to_stream(scope)
                .inspect(|x| println!("Saw: {}", x))
                .probe()
        });

        // External loop feeding data
        for round in 0..10 {
            input.send(round);
            input.advance_to(round + 1);

            // Wait for computation to complete
            while probe.less_than(input.time()) {
                worker.step();
            }
        }
    }).expect("Execution failed");
}
```

## Architecture Patterns

### Timestamp Structure
```
Single Dimension (u64)
  → Linear time progression
  → Use for: Simple pipelines, no iteration
  → Example: Event time in milliseconds

Product (Outer, Inner)
  → Product<u64, u32> for iterative computation
  → Outer: Input time, Inner: Iteration number
  → Allows feedback loops with progress guarantees

Custom Lattice
  → Implement PartialOrder trait
  → Use for: Complex coordination patterns
  → Example: Vector clocks, causal timestamps
```

### Operator Exchange Patterns
```rust
use timely::dataflow::channels::pact::{Pipeline, Exchange};

// Pipeline: No data movement (data stays on same worker)
stream.unary(Pipeline, "Op", |cap, info| { ... })

// Exchange: Partition data by hash of key
stream.unary(Exchange::new(|x: &T| hash(x)), "Op", |cap, info| { ... })

// Broadcast: Send all data to all workers (expensive)
// Custom Pact: Implement ParallelizationContract trait
```

## Performance Optimization

### Worker Configuration
```bash
# Single machine, multiple threads
cargo run -- -w 4

# Multiple processes (distributed)
cargo run -- -w 8 -p 2  # 8 workers, 2 processes (4 workers each)
cargo run -- -w 8 -p 4  # 8 workers, 4 processes (2 workers each)

# With specific hosts
cargo run -- -w 4 -p 2 -h worker1,worker2
```

### Batch Size Tuning
```rust
// Configure batch sizes for better throughput
use timely::dataflow::operators::Operator;

stream.unary_frontier(
    Pipeline,
    "BatchedOp",
    |_capability, _info| {
        let mut buffer = Vec::new();
        const BATCH_SIZE: usize = 1000;

        move |input, output| {
            input.for_each(|time, data| {
                buffer.extend(data.iter().cloned());

                if buffer.len() >= BATCH_SIZE {
                    let mut session = output.session(&time);
                    for item in buffer.drain(..) {
                        session.give(item);
                    }
                }
            });
        }
    },
)
```

### Memory Management
```rust
// Use capabilities efficiently
use timely::progress::Timestamp;

// Downgrade capabilities when possible
capability.downgrade(&new_time);

// Drop capabilities when done
drop(capability);

// Clean up old state based on frontier
let frontier = &frontiers[0];
state.retain(|time, _| !frontier.less_equal(time));
```

## Quick Reference

### Common Operators
```rust
use timely::dataflow::operators::*;

// Transform
stream.map(|x| x * 2)
stream.flat_map(|x| 0..x)
stream.filter(|x| *x > 5)

// Inspect (side effects)
stream.inspect(|x| println!("{}", x))
stream.inspect_time(|t, x| println!("{:?}: {}", t, x))

// Combine
stream1.concat(&stream2)
stream1.binary(&stream2, ...) // Custom binary operator

// Feedback
let (handle, cycle) = scope.feedback(summary);
stream.connect_loop(handle)

// Control
stream.probe()  // Track progress
input.advance_to(time)  // Advance input frontier
```

### Debugging
```rust
// Log operator names and structure
std::env::set_var("TIMELY_WORKER_LOG_ADDR", "localhost:51317");

// Progress tracking
stream.inspect_time(|time, data| {
    eprintln!("Time {:?}: {:?}", time, data);
})

// Frontier inspection
use timely::dataflow::operators::probe::Handle as ProbeHandle;
let probe = stream.probe();
println!("Frontier: {:?}", probe.with_frontier(|f| f.to_vec()));
```

## Anti-Patterns

```
❌ NEVER: Hold capabilities indefinitely
   → Prevents frontier advancement, blocks progress

❌ NEVER: Ignore timestamp management in feedback loops
   → Can create non-monotonic timestamps, breaks progress tracking

❌ NEVER: Perform blocking I/O in operators
   → Single-threaded workers, blocks entire worker

❌ NEVER: Accumulate unbounded state without cleanup
   → Use frontier to determine safe cleanup points

❌ NEVER: Use exchange for small data volumes
   → Overhead of shuffling > benefit, use Pipeline

❌ NEVER: Create too many operators
   → Overhead in progress tracking, combine logic when possible

❌ NEVER: Forget to advance input frontiers
   → Computation stalls waiting for future data

❌ NEVER: Use global state across workers
   → Shared-nothing architecture, use message passing

❌ NEVER: Assume data ordering beyond timestamp
   → Only timestamp order guaranteed, not arrival order

❌ NEVER: Mix wall-clock time with logical timestamps
   → Logical timestamps for correctness, wall-clock for monitoring only
```

## Related Skills

- `differential-dataflow.md` - Incremental computation on top of timely dataflow
- `dataflow-coordination.md` - Advanced coordination patterns and barriers
- `streaming-aggregations.md` - Window-based aggregations using timely semantics
- `stream-processing.md` - Higher-level stream processing frameworks

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
