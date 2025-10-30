# Example 05: GroupBy and Aggregation Operations

Fast groupby operations implemented in Rust, providing performance improvements over Python for large datasets.

## What You'll Learn

- Implementing groupby operations in Rust
- Multiple aggregation functions
- Using HashMaps for group tracking
- Value counting and filtering

## Functions

- `fast_groupby_sum(groups, values)`: Sum by group
- `fast_groupby_mean(groups, values)`: Mean by group
- `fast_groupby_agg(groups, values)`: Multiple statistics
- `fast_value_counts(groups)`: Count occurrences
- `filter_groups_by_size(groups, min_size)`: Filter by group size

## Usage

```python
import numpy as np
import pandas_groupby

groups = np.array([1, 2, 1, 2, 1])
values = np.array([10.0, 20.0, 15.0, 25.0, 5.0])

sums = pandas_groupby.fast_groupby_sum(groups, values)
means = pandas_groupby.fast_groupby_mean(groups, values)
stats = pandas_groupby.fast_groupby_agg(groups, values)
```

## Performance

Rust groupby operations are typically 2-5x faster than Pandas for large datasets due to:
- Efficient HashMap usage
- No Python interpreter overhead
- Single-pass algorithms
