# Example 05: Lock-Free Atomic Operations

This example demonstrates lock-free programming using Rust's atomic types, providing better performance than mutexes in high-contention scenarios.

## Concepts Covered

- **Atomic Types**: Lock-free shared state (AtomicU64, AtomicBool, etc.)
- **Memory Ordering**: SeqCst, Acquire, Release for correctness
- **Compare-and-Swap (CAS)**: Atomic conditional updates
- **Lock-Free Algorithms**: Stats collection without locks
- **Progress Tracking**: Concurrent progress monitoring

## Key Components

### AtomicCounter
```python
counter = atomic_operations.AtomicCounter(0)
counter.increment()
counter.add(10)
value = counter.get()
counter.compare_and_swap(current, new)
```

### AtomicFlag
```python
flag = atomic_operations.AtomicFlag(False)
flag.set(True)
old_value = flag.swap(False)
```

### AtomicStats
```python
stats = atomic_operations.AtomicStats()
stats.record(value)
print(stats.summary())  # count, sum, mean, min, max
```

## Building and Testing

```bash
pip install maturin
maturin develop --release
python test_example.py
```

## When to Use Atomics vs Mutexes

### Use Atomics When
- Simple operations (increment, swap, CAS)
- High contention (many threads)
- Need lock-free guarantees
- Minimal critical section

### Use Mutexes When
- Complex operations
- Multiple related updates
- Need to hold lock across function calls
- Clearer code is priority

## Performance Comparison

Typical results from benchmark:
```
Atomic: 0.023s
Mutex:  0.089s
Speedup: 3.87x
```

Atomics shine in high-contention scenarios where many threads compete for the same resource.

## Memory Ordering

This example uses `SeqCst` (Sequentially Consistent) ordering:
- Strongest guarantee
- Easiest to reason about
- Slight performance cost

For experts, weaker orderings (Acquire/Release) can provide better performance.

## Lock-Free Algorithms

The AtomicStats implementation demonstrates a lock-free algorithm:
- Multiple threads can update stats concurrently
- No thread can block another thread
- Always makes forward progress
- Compare-and-swap loop for min/max updates

## Learning Points

1. **No Data Races**: Atomics prevent data races at the type level
2. **Lock-Free**: No thread can block another thread
3. **Performance**: 2-10x faster than mutexes in high contention
4. **Simplicity**: Limited to simple operations
5. **Progress Guarantees**: Always makes forward progress

## Next Steps

- Example 06: Advanced parallel iterator patterns with Rayon
- Example 07: Multi-threaded communication with channels
