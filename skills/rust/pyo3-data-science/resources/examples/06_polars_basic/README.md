# Example 06: Basic Polars DataFrame Operations

Demonstrates working with Polars DataFrames through PyO3.

## What You'll Learn

- Creating Polars DataFrames from Rust
- Filtering and selecting data
- Sorting DataFrames
- Working with Polars Python API

## Functions

- `create_polars_df()`: Create DataFrame
- `filter_dataframe(df, column, threshold)`: Filter rows
- `select_columns(df, columns)`: Select columns
- `sort_dataframe(df, column, descending)`: Sort data
- `get_shape(df)`: Get dimensions

## Usage

```python
import polars_basic

df = polars_basic.create_polars_df()
filtered = polars_basic.filter_dataframe(df, "value", 20.0)
selected = polars_basic.select_columns(df, ["id", "value"])
```

## Requirements

```bash
pip install polars
```
