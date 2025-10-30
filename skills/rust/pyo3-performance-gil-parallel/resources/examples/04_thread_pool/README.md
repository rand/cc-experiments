# Example 04: Custom Thread Pool with Work Stealing

This example demonstrates building a custom thread pool from scratch with work stealing for load balancing, going beyond Rayon for scenarios requiring fine-grained control.

## Concepts Covered

- **Custom Thread Pool**: Building a reusable thread pool
- **Work Stealing**: Load balancing across threads
- **Task Queues**: Distributing work efficiently
- **Adaptive Sizing**: Adjusting thread count based on workload
- **Resource Management**: Proper shutdown and cleanup

## Key Components

### ThreadPool Class
Reusable thread pool with configurable size:
```python
pool = thread_pool.ThreadPool(size=4)
results = pool.execute_batch(tasks)
pool.shutdown()
```

### TaskQueue Class
Queue-based work distribution:
```python
queue = thread_pool.TaskQueue(tasks)
results = queue.process_parallel(thread_count=4)
```

### Work Stealing
```python
results = thread_pool.process_work_stealing(
    tasks,
    thread_count=4
)
```

### Adaptive Parallelism
```python
# Automatically chooses thread count based on task size
results = thread_pool.adaptive_parallel(tasks)
```

## Building and Testing

```bash
pip install maturin
maturin develop --release
python test_example.py
```

## When to Use Custom Thread Pools

### Use Cases
- **Long-lived pools**: Avoid thread creation overhead
- **Custom scheduling**: Need specific task ordering
- **Resource limits**: Control maximum thread count
- **Monitoring**: Track individual thread performance

### When Rayon is Better
- Simple data parallelism
- One-time parallel operations
- Standard map/reduce patterns
- Automatic work distribution

## Work Stealing Explained

Work stealing prevents load imbalance:

1. Each thread has a local queue
2. Threads process their own queue first (fast, no contention)
3. When idle, threads "steal" from other queues
4. Results in better load balancing than static partitioning

## Performance Characteristics

### Thread Pool Creation
- **Cost**: ~1-10ms to create pool
- **Benefit**: Amortized over many task batches
- **Best for**: Long-running applications

### Work Stealing
- **Overhead**: Slight overhead from stealing logic
- **Benefit**: Better load balance for uneven workloads
- **Best for**: Tasks with variable execution time

### Adaptive Sizing
- Small workloads: 2 threads (minimal overhead)
- Medium workloads: 4 threads (balance)
- Large workloads: All available cores (maximum throughput)

## Learning Points

1. **Thread Pool Pattern**: Reusable worker threads reduce overhead
2. **Work Stealing**: Idle threads help busy threads
3. **Lock Contention**: Minimize shared state access
4. **Shutdown Protocol**: Proper cleanup prevents resource leaks
5. **Adaptive Behavior**: One size doesn't fit all workloads

## Next Steps

- Example 05: Lock-free atomic operations for even better performance
- Example 06: Advanced Rayon parallel iterator patterns
