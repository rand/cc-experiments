# Example 09: Parallel Iterator

Leverage Rayon for parallel data processing with automatic work distribution across CPU cores.

## What You'll Learn

- Parallel map operations
- Parallel filtering
- Parallel reduction (sum, min, max)
- Parallel sorting
- Batch-based parallel processing
- When to use parallelism

## Components

- **ParallelMapper**: Apply transformations in parallel
- **ParallelFilter**: Filter data using multiple threads
- **ParallelReducer**: Aggregate data in parallel
- **ParallelSorter**: Sort large datasets efficiently
- **ParallelBatchProcessor**: Process in parallel batches

## Usage

```python
import parallel_iterator

# Parallel map
mapper = parallel_iterator.ParallelMapper()
squares = mapper.map_square(range(1000000))  # Uses all CPU cores

# Parallel filter
filter_obj = parallel_iterator.ParallelFilter()
primes = filter_obj.filter_prime(range(1000))

# Parallel reduce
reducer = parallel_iterator.ParallelReducer()
total = reducer.sum(large_dataset)
minimum = reducer.min(large_dataset)

# Parallel sort
sorter = parallel_iterator.ParallelSorter()
sorted_data = sorter.sort(unsorted_data)

# Batch processing
processor = parallel_iterator.ParallelBatchProcessor(batch_size=1000)
results = processor.process_batches(data)
```

## Performance Considerations

**Use parallel when:**
- Large datasets (> 10,000 items)
- CPU-bound operations
- Independent computations
- Multiple CPU cores available

**Avoid parallel when:**
- Small datasets (overhead > benefit)
- I/O-bound operations
- Sequential dependencies
- Single-core systems

## Real-World Applications

- Large-scale data transformations
- Batch processing systems
- Scientific computing
- Image/video processing
- Machine learning pipelines

Build: `maturin develop && python test_example.py`
