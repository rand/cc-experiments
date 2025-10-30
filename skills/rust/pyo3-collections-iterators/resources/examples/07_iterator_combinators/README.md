# Example 07: Iterator Combinators

Learn functional programming patterns with iterator combinators: map, filter, chain, zip, take, and skip.

## Components

- **MapIterator**: Transform each element
- **FilterIterator**: Keep only matching elements
- **ChainIterator**: Combine multiple iterators sequentially
- **ZipIterator**: Pair elements from two iterators
- **TakeIterator**: Limit to first N elements
- **SkipIterator**: Skip first N elements

## Usage

```python
import iterator_combinators

# Map
squares = iterator_combinators.MapIterator([1, 2, 3], "square")
list(squares)  # [1, 4, 9]

# Filter
evens = iterator_combinators.FilterIterator([1, 2, 3, 4], "even", None)
list(evens)  # [2, 4]

# Chain
combined = iterator_combinators.ChainIterator([1, 2], [3, 4])
list(combined)  # [1, 2, 3, 4]

# Zip
paired = iterator_combinators.ZipIterator([1, 2], ["a", "b"])
list(paired)  # [(1, "a"), (2, "b")]
```

## Real-World Applications

- Data transformation pipelines
- ETL operations
- Stream processing
- Functional data processing

Build: `maturin develop && python test_example.py`
