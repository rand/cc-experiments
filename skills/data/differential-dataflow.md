---
name: data-differential-dataflow
description: Differential computation for incremental updates, maintaining indexed collections and efficient joins
---

# Differential Dataflow

**Scope**: Incremental computation, arrangements, differential updates, efficient joins
**Lines**: 390
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

## When to Use This Skill

Use this skill when:
- Building systems that need incremental computation (avoid full recomputation)
- Maintaining materialized views that update efficiently
- Implementing real-time dashboards over changing data
- Performing joins on large, slowly-changing datasets
- Creating reactive systems that respond to data changes
- Building graph algorithms that update incrementally
- Optimizing computations that repeat with small data changes

## Core Concepts

### Differential vs Standard Dataflow
```
Standard Dataflow (Timely)
  → Process complete data at each timestamp
  → Full recomputation for each change
  → Good for: Stateless transformations

Differential Dataflow
  → Process only changes (deltas)
  → Maintains indexed state (arrangements)
  → Incrementally updates results
  → Good for: Joins, aggregations, iterative algorithms
```

### Collections and Updates
```
Collection<G, D>
  → Multiset of data D at times G::Timestamp
  → Represented as (data, time, diff) triples
  → diff: +1 (insert), -1 (delete), +N (multiplicity)

Example:
  ("alice", 0, +1)  → Insert "alice" at time 0
  ("alice", 5, -1)  → Delete "alice" at time 5
  ("bob", 0, +2)    → Insert "bob" twice at time 0
```

### Arrangements (Indexed State)
```
Arrangement
  → Indexed collection for efficient lookup
  → Key-value pairs: (key, value, time, diff)
  → Enables fast joins without full scans
  → Shared across operators (zero-copy)

TraceHandle
  → Reference to arranged data
  → Multiple operators can share same arrangement
  → Compaction merges historical updates
```

### Differential Operators
```
Map/Filter
  → Transform collections
  → diff propagates through transformations

Join
  → Efficient incremental join on arrangements
  → Updates only affected outputs
  → O(delta) complexity, not O(data)

Reduce
  → Group-by aggregation
  → Incremental update on changes
  → Maintains grouped state

Iterate
  → Fixed-point computation
  → Converges when no more changes
  → Efficient for graph algorithms
```

## Patterns

### Pattern 1: Basic Collections and Transformations

```rust
// Cargo.toml
// [dependencies]
// timely = "0.12"
// differential-dataflow = "0.12"

use differential_dataflow::input::Input;
use differential_dataflow::operators::{Join, Reduce};

fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        let mut input = worker.dataflow::<u64, _, _>(|scope| {
            let (input, data) = scope.new_collection();

            // Transform collection
            data.map(|x| x * 2)
                .filter(|x| *x > 10)
                .inspect(|x| println!("Filtered: {:?}", x));

            input
        });

        // Insert data
        input.insert(5);   // (5, +1)
        input.insert(10);  // (10, +1)
        input.advance_to(1);
        worker.step_while(|| input.time().less_than(&1));

        // Remove data
        input.remove(5);   // (5, -1)
        input.advance_to(2);
        worker.step_while(|| input.time().less_than(&2));

        // Output shows only changes
    }).expect("Execution failed");
}
```

### Pattern 2: Incremental Join

```rust
use differential_dataflow::input::Input;
use differential_dataflow::operators::Join;

#[derive(Clone, Debug, Hash, PartialEq, Eq, PartialOrd, Ord)]
struct User {
    id: u32,
    name: String,
}

#[derive(Clone, Debug, Hash, PartialEq, Eq, PartialOrd, Ord)]
struct Order {
    user_id: u32,
    product: String,
    amount: f64,
}

fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        let (mut users_in, mut orders_in) = worker.dataflow::<u64, _, _>(|scope| {
            let (users_in, users) = scope.new_collection();
            let (orders_in, orders) = scope.new_collection();

            // Join users with orders
            // Convert to (key, value) format
            let users_keyed = users.map(|u| (u.id, u.name.clone()));
            let orders_keyed = orders.map(|o| (o.user_id, (o.product.clone(), o.amount)));

            // Incremental join
            users_keyed
                .join(&orders_keyed)
                .inspect(|(user_id, (name, (product, amount)))| {
                    println!("User {} ({}) ordered {} for ${}",
                             user_id, name, product, amount);
                });

            (users_in, orders_in)
        });

        // Initial data at time 0
        users_in.insert(User { id: 1, name: "Alice".to_string() });
        users_in.insert(User { id: 2, name: "Bob".to_string() });
        orders_in.insert(Order { user_id: 1, product: "Laptop".to_string(), amount: 999.0 });

        users_in.advance_to(1);
        orders_in.advance_to(1);
        worker.step_while(|| users_in.time().less_than(&1));

        // Add order at time 1 - only processes this change
        orders_in.insert(Order { user_id: 2, product: "Mouse".to_string(), amount: 25.0 });

        users_in.advance_to(2);
        orders_in.advance_to(2);
        worker.step_while(|| orders_in.time().less_than(&2));

        // Update user name at time 2 - join recomputes only affected records
        users_in.remove(User { id: 1, name: "Alice".to_string() });
        users_in.insert(User { id: 1, name: "Alice Smith".to_string() });

        users_in.advance_to(3);
        orders_in.advance_to(3);
        worker.step_while(|| users_in.time().less_than(&3));
    }).expect("Execution failed");
}
```

### Pattern 3: Arrangements for Shared State

```rust
use differential_dataflow::input::Input;
use differential_dataflow::operators::{Join, Reduce, Threshold, arrange::ArrangeBySelf};
use differential_dataflow::operators::arrange::ArrangeByKey;

fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        let mut input = worker.dataflow::<u64, _, _>(|scope| {
            let (input, edges) = scope.new_collection::<(u32, u32)>();

            // Arrange edges by source node (shared arrangement)
            let edges_arranged = edges.arrange_by_key();

            // Query 1: Count outgoing edges per node
            edges_arranged
                .reduce(|_src, input, output| {
                    let count: i32 = input.iter().map(|(_, diff)| diff).sum();
                    output.push((count, 1));
                })
                .inspect(|(node, count)| {
                    println!("Node {} has {} outgoing edges", node, count);
                });

            // Query 2: Find nodes with edges (using same arrangement)
            edges_arranged
                .as_collection(|&src, &_dst| src)
                .distinct()
                .inspect(|node| println!("Active node: {}", node));

            // Query 3: Two-hop paths (self-join on arrangement)
            edges_arranged
                .join_core(&edges_arranged, |&src, &mid, &dst| {
                    Some((src, mid, dst))
                })
                .inspect(|(src, mid, dst)| {
                    println!("Path: {} -> {} -> {}", src, mid, dst);
                });

            input
        });

        // Insert graph edges
        input.insert((1, 2));
        input.insert((2, 3));
        input.insert((1, 3));
        input.advance_to(1);
        worker.step_while(|| input.time().less_than(&1));

        // Add new edge - only affected queries recompute
        input.insert((3, 4));
        input.advance_to(2);
        worker.step_while(|| input.time().less_than(&2));
    }).expect("Execution failed");
}
```

### Pattern 4: Incremental Aggregation (Group-By Reduce)

```rust
use differential_dataflow::input::Input;
use differential_dataflow::operators::Reduce;

#[derive(Clone, Debug, Hash, PartialEq, Eq, PartialOrd, Ord)]
struct Sale {
    category: String,
    amount: i32,
}

fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        let mut input = worker.dataflow::<u64, _, _>(|scope| {
            let (input, sales) = scope.new_collection();

            // Group by category and sum amounts
            sales
                .map(|sale| (sale.category.clone(), sale.amount))
                .reduce(|_category, amounts, output| {
                    let total: i32 = amounts.iter()
                        .map(|(amount, diff)| amount * diff)
                        .sum();
                    output.push((total, 1));
                })
                .inspect(|(category, total)| {
                    println!("Category {}: total = {}", category, total);
                });

            input
        });

        // Initial sales
        input.insert(Sale { category: "Electronics".to_string(), amount: 100 });
        input.insert(Sale { category: "Electronics".to_string(), amount: 200 });
        input.insert(Sale { category: "Books".to_string(), amount: 50 });
        input.advance_to(1);
        worker.step_while(|| input.time().less_than(&1));

        // Add sale - only Electronics group recomputes
        input.insert(Sale { category: "Electronics".to_string(), amount: 150 });
        input.advance_to(2);
        worker.step_while(|| input.time().less_than(&2));

        // Remove sale - incremental update
        input.remove(Sale { category: "Books".to_string(), amount: 50 });
        input.advance_to(3);
        worker.step_while(|| input.time().less_than(&3));
    }).expect("Execution failed");
}
```

### Pattern 5: Iterative Computation (Connected Components)

```rust
use differential_dataflow::input::Input;
use differential_dataflow::operators::{Join, Consolidate, Iterate};

fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        let mut input = worker.dataflow::<u64, _, _>(|scope| {
            let (input, edges) = scope.new_collection::<(u32, u32)>();

            // Compute connected components
            let labels = edges.iterate(|inner| {
                let edges = edges.enter(&inner.scope());

                // Start with self-labels: node -> node
                let nodes = edges.flat_map(|(src, dst)| vec![src, dst])
                    .distinct()
                    .map(|node| (node, node));

                // Propagate minimum label along edges
                inner.join(&edges.map(|(src, dst)| (src, dst)))
                    .map(|(_src, (label, dst))| (dst, label))
                    .concat(&nodes)
                    .reduce(|_node, labels, output| {
                        // Keep minimum label
                        let min_label = labels.iter()
                            .map(|(label, _)| *label)
                            .min()
                            .unwrap();
                        output.push((min_label, 1));
                    })
            });

            labels.inspect(|(node, component)| {
                println!("Node {} in component {}", node, component);
            });

            input
        });

        // Graph with two components: {1,2,3} and {4,5}
        input.insert((1, 2));
        input.insert((2, 3));
        input.insert((4, 5));
        input.advance_to(1);
        worker.step_while(|| input.time().less_than(&1));

        // Bridge components - iterates until convergence
        input.insert((3, 4));
        input.advance_to(2);
        worker.step_while(|| input.time().less_than(&2));
    }).expect("Execution failed");
}
```

### Pattern 6: External State Updates (Probing)

```rust
use differential_dataflow::input::InputSession;
use differential_dataflow::operators::Join;
use timely::dataflow::operators::probe::Handle as ProbeHandle;

fn main() {
    timely::execute_from_args(std::env::args(), |worker| {
        let mut input = InputSession::new();
        let mut probe = ProbeHandle::new();

        worker.dataflow::<u64, _, _>(|scope| {
            input.to_collection(scope)
                .map(|x| x * 2)
                .inspect(|x| println!("Result: {:?}", x))
                .probe_with(&mut probe);
        });

        // External loop with synchronization
        for round in 0..10 {
            input.insert(round);
            input.advance_to(round + 1);
            input.flush();

            // Wait for completion
            while probe.less_than(input.time()) {
                worker.step();
            }

            println!("Round {} complete", round);
        }
    }).expect("Execution failed");
}
```

## Advanced Patterns

### Custom Reduction Logic
```rust
use differential_dataflow::operators::Reduce;

// Top-K items per group
collection
    .map(|(group, value)| (group, value))
    .reduce(move |_group, values, output| {
        let k = 10;
        let mut sorted: Vec<_> = values.iter()
            .map(|(val, diff)| (*val, *diff))
            .collect();
        sorted.sort_by_key(|(val, _)| std::cmp::Reverse(*val));

        for (val, diff) in sorted.into_iter().take(k) {
            output.push((val, diff));
        }
    })
```

### Threshold (Distinct)
```rust
use differential_dataflow::operators::Threshold;

// Remove duplicates (keep diff = 1)
collection.distinct()

// Keep only positive diffs
collection.threshold(|_, count| if *count > 0 { 1 } else { 0 })

// Custom threshold logic
collection.threshold(|value, count| {
    if *value > 100 && *count > 5 { 1 } else { 0 }
})
```

### Multi-way Joins
```rust
// Three-way join
let result = collection1
    .join(&collection2)
    .map(|(key, (val1, val2))| ((key, val1), val2))
    .join(&collection3.map(|(key, val)| ((key, ()), val)))
    .map(|((key, val1), ((), val2))| (key, val1, val2));
```

## Performance Optimization

### Arrangement Strategy
```rust
// Arrange when:
// 1. Multiple operators read same data
// 2. Performing joins
// 3. Random access needed

let arranged = collection.arrange_by_key();

// Use arrangement multiple times (zero-copy)
arranged.as_collection(|k, v| (k.clone(), v.clone()));
arranged.join_core(&other_arranged, |k, v1, v2| ...);
```

### Compaction Control
```rust
// Configure trace compaction
use differential_dataflow::trace::implementations::ord::OrdValSpine;

let trace = collection
    .arrange_by_key()
    .trace;

// Compact aggressively (saves memory, costs CPU)
trace.set_physical_compaction(Duration::from_secs(1));

// Compact lazily (saves CPU, uses more memory)
trace.set_logical_compaction(Duration::from_secs(60));
```

### Batch Size Tuning
```rust
use differential_dataflow::input::InputSession;

let mut input = InputSession::new();

// Buffer insertions
for item in large_dataset {
    input.insert(item);

    // Periodic flush
    if input.len() > 10000 {
        input.flush();
    }
}

input.advance_to(1);
input.flush();
```

## Quick Reference

### Collection Operators
```rust
// Transform
collection.map(|x| x * 2)
collection.flat_map(|x| vec![x, x * 2])
collection.filter(|x| *x > 10)

// Combine
collection1.concat(&collection2)
collection.distinct()
collection.negate()  // Flip diff signs

// Join
keyed1.join(&keyed2)
keyed1.semijoin(&keyed2)  // Keep keyed1 where key in keyed2
keyed1.antijoin(&keyed2)  // Keep keyed1 where key NOT in keyed2

// Aggregate
keyed.reduce(|key, vals, output| { ... })
keyed.count()  // Count occurrences

// Arrange
collection.arrange_by_key()
collection.arrange_by_self()
```

### Input Management
```rust
use differential_dataflow::input::{Input, InputSession};

// Simple input
let (mut input, collection) = scope.new_collection();
input.insert(data);
input.remove(data);
input.advance_to(time);

// Session input (buffered)
let mut input = InputSession::new();
input.insert(data);
input.flush();  // Send batched updates
input.advance_to(time);
```

### Debugging
```rust
// Inspect updates
collection.inspect(|(data, time, diff)| {
    println!("Update: {:?} at {:?} with diff {}", data, time, diff);
});

// Consolidate before inspection (merge diffs)
collection.consolidate().inspect(|x| println!("{:?}", x));

// Count updates
collection.count().inspect(|x| println!("Counts: {:?}", x));
```

## Anti-Patterns

```
❌ NEVER: Scan entire collection for point lookups
   → Use arrange_by_key for indexed access

❌ NEVER: Recompute from scratch on updates
   → Use differential operators (join, reduce) for incremental updates

❌ NEVER: Arrange data that's used only once
   → Arrangement overhead not worth it, use direct operators

❌ NEVER: Accumulate unbounded history
   → Configure compaction to bound memory usage

❌ NEVER: Join without arrangement
   → Direct join is O(n²), arranged join is O(delta)

❌ NEVER: Use distinct on high-cardinality data unnecessarily
   → Maintains full set in memory, expensive

❌ NEVER: Forget to consolidate before inspection
   → May see multiple updates for same data (inserts + deletes)

❌ NEVER: Use differential for stateless transformations
   → Use standard timely dataflow (less overhead)

❌ NEVER: Create arrangements inside iterations
   → Build arrangements outside, enter into iteration scope

❌ NEVER: Ignore diff values in custom reduce logic
   → Must handle negative diffs (deletions) correctly
```

## Related Skills

- `timely-dataflow.md` - Foundation for differential dataflow
- `dataflow-coordination.md` - Coordination patterns for complex computations
- `streaming-aggregations.md` - Window-based aggregations
- `stream-processing.md` - Higher-level stream processing abstractions

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
