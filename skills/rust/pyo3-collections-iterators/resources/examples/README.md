# PyO3 Collections and Iterators - Examples

This directory contains 10 progressive examples demonstrating PyO3 collections and iterators, from beginner to advanced production use.

## Example Overview

### Beginner (01-03)

**01_basic_iterator/** - Simple iterator implementation
- Basic `__iter__` and `__next__` protocol
- State management in iterators
- Converting between Python and Rust iterators
- ~200 lines

**02_collection_conversion/** - List, dict, set conversions
- Automatic type conversion (Vec ↔ List, HashMap ↔ Dict, HashSet ↔ Set)
- Processing collections in Rust
- Nested collections
- Tuples and mixed types
- ~250 lines

**03_sequence_protocol/** - Sequence protocol implementation
- `__len__`, `__getitem__`, `__setitem__`, `__delitem__`
- Slice support
- Negative indices
- Iteration and reversal
- ~280 lines

### Intermediate (04-07)

**04_lazy_iterator/** - Lazy evaluation with yield
- On-demand computation
- Infinite sequences (Fibonacci)
- Lazy filtering and transformation
- Iterator chaining
- Memory efficiency
- ~250 lines

**05_bidirectional_iter/** - Forward and reverse iteration
- VecDeque for bidirectional operations
- Peekable iterators (lookahead)
- Window iterators (sliding windows)
- Push/pop from both ends
- ~200 lines

**06_custom_collection/** - Custom collection types
- HybridCollection (list + dict + set features)
- PriorityQueue (priority-based ordering)
- CircularBuffer (ring buffer with wraparound)
- Domain-specific collections
- ~240 lines

**07_iterator_combinators/** - Map, filter, chain patterns
- MapIterator (transformations)
- FilterIterator (predicates)
- ChainIterator (sequential combination)
- ZipIterator (parallel combination)
- TakeIterator, SkipIterator
- Functional programming patterns
- ~260 lines

### Advanced (08-10)

**08_streaming_data/** - Streaming large datasets
- Batch processing for large files
- ChunkedProcessor (fixed-size chunks)
- StreamingCSVReader (parse CSV incrementally)
- BufferedStream (accumulate until threshold)
- Memory-efficient processing
- ~220 lines

**09_parallel_iterator/** - Parallel iteration with Rayon
- ParallelMapper (map in parallel)
- ParallelFilter (filter using multiple threads)
- ParallelReducer (sum, min, max in parallel)
- ParallelSorter (parallel sorting)
- ParallelBatchProcessor (batch-level parallelism)
- When to use parallelism
- ~240 lines

**10_production_pipeline/** - Complete data processing pipeline
- DataPipeline (filters + transforms + aggregations)
- TimeSeriesProcessor (moving average, anomaly detection, resampling)
- Statistical analysis
- Grouping operations
- Parallel vs sequential execution
- Production-ready architecture
- ~280 lines

## Building Examples

Each example is a standalone Rust project that can be built with maturin:

```bash
# Navigate to an example
cd 01_basic_iterator

# Install maturin (one-time setup)
pip install maturin

# Build and install in development mode
maturin develop

# Run tests
python test_example.py

# Or use pytest
pytest test_example.py -v
```

## Testing All Examples

To build and test all examples:

```bash
#!/bin/bash
for dir in */; do
    echo "Testing $dir"
    cd "$dir"
    maturin develop --quiet && python test_example.py
    cd ..
done
```

## File Structure

Each example contains:
- `src/lib.rs` - Rust implementation
- `Cargo.toml` - Rust dependencies
- `pyproject.toml` - Python packaging configuration
- `test_example.py` - Python tests
- `README.md` - Documentation and usage examples

## Total Line Counts

- Total Rust code: ~2,400 lines
- Total Python tests: ~1,100 lines
- Total documentation: ~2,800 lines
- **Grand total: ~6,300 lines** across 50 files

## Learning Path

**Complete beginner?** Start with 01, 02, 03 in order.

**Familiar with basics?** Jump to 04 (lazy evaluation) or 06 (custom collections).

**Need performance?** Focus on 08 (streaming) and 09 (parallel).

**Building production systems?** Study 10 (complete pipeline).

## Key Concepts by Example

| Concept | Examples |
|---------|----------|
| Iterator protocol | 01, 04, 05 |
| Type conversion | 02, 03 |
| Lazy evaluation | 04, 08 |
| Sequence protocol | 03, 06 |
| Functional patterns | 07 |
| Memory efficiency | 04, 08 |
| Parallelism | 09, 10 |
| Production patterns | 10 |

## Common Patterns

### Iterator State Management
```rust
#[pyclass]
struct MyIterator {
    data: Vec<T>,
    index: usize,  // State
}
```

### Lazy Evaluation
```rust
fn __next__(mut slf: PyRefMut<Self>) -> Option<T> {
    // Compute only when called
}
```

### Parallel Processing
```rust
use rayon::prelude::*;
data.par_iter().map(|x| expensive_operation(x)).collect()
```

### Streaming
```rust
// Process in chunks
while let Some(chunk) = get_next_chunk() {
    process(chunk);
}
```

## Dependencies

All examples require:
- Rust 1.70+
- Python 3.8+
- PyO3 0.20+
- maturin 1.0+

Examples 09 and 10 additionally require:
- rayon 1.8+ (for parallelism)

## Troubleshooting

**Build errors?**
- Ensure Rust is installed: `rustc --version`
- Update maturin: `pip install -U maturin`

**Import errors?**
- Run `maturin develop` in the example directory
- Check you're in a Python environment with maturin installed

**Test failures?**
- Ensure you built with `maturin develop` first
- Check Python version: `python --version` (need 3.8+)

## Next Steps

After completing these examples:
1. Modify examples for your use case
2. Combine patterns (e.g., lazy + parallel)
3. Explore PyO3 advanced topics (async, numpy integration)
4. Build your own production data processing tools

## Resources

- [PyO3 Documentation](https://pyo3.rs/)
- [Rayon Documentation](https://docs.rs/rayon/)
- [Python Iterator Protocol](https://docs.python.org/3/library/stdtypes.html#iterator-types)
- [Rust Iterator Trait](https://doc.rust-lang.org/std/iter/trait.Iterator.html)

---

**Total Examples**: 10
**Total Files**: 50 (10 lib.rs, 10 Cargo.toml, 10 pyproject.toml, 10 tests, 10 READMEs)
**Difficulty Progression**: Beginner → Intermediate → Advanced
**Estimated Learning Time**: 8-12 hours (complete all examples)
