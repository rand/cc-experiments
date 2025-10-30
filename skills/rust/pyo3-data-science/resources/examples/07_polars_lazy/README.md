# Example 07: Lazy Polars Query Optimization

Demonstrates Polars lazy evaluation for query optimization.

## Functions

- `create_lazy_df()`: Create lazy DataFrame
- `execute_lazy(lazy_df)`: Execute lazy query

## Usage

```python
import polars_lazy

lazy_df = polars_lazy.create_lazy_df()
result = polars_lazy.execute_lazy(lazy_df)
```
