# Example 04: Create Pandas DataFrames from Rust

Demonstrates creating and manipulating Pandas DataFrames from Rust using PyO3.

## What You'll Learn

- Creating DataFrames from Rust vectors
- Working with Pandas Python API from Rust
- Converting Rust structs to DataFrames
- Extracting data from DataFrames
- Type conversions between Rust and Pandas

## Key Concepts

### Creating DataFrames

Use PyDict to build column data:

```rust
let pd = py.import("pandas")?;
let data = PyDict::new(py);
data.set_item("col1", PyArray1::from_vec(py, vec![1, 2, 3]))?;
let df = pd.call_method1("DataFrame", (data,))?;
```

### Calling Pandas Methods

Call Pandas methods from Rust:

```rust
let df = pd.call_method("date_range", (start_date, periods), None)?;
```

## Functions Provided

- `create_simple_dataframe()`: Basic DataFrame creation
- `create_from_vecs(ids, values, names)`: From separate vectors
- `create_time_series(start_date, periods)`: Time series data
- `create_complex_dataframe(records)`: Multi-column DataFrame
- `create_and_transform(size, multiplier)`: Create and transform
- `extract_column(df, column)`: Extract column values
- `get_shape(df)`: Get DataFrame dimensions
- `records_to_dataframe(records)`: Convert Record objects

## Building and Testing

```bash
pip install maturin pandas numpy pytest
maturin develop
pytest test_example.py -v
```

## Usage Examples

```python
import pandas_create

# Simple DataFrame
df = pandas_create.create_simple_dataframe()
print(df)

# From vectors
df = pandas_create.create_from_vecs([1, 2], [10.0, 20.0], ["A", "B"])

# Time series
ts_df = pandas_create.create_time_series("2024-01-01", 30)

# Complex DataFrame
df = pandas_create.create_complex_dataframe(100)

# Using Record objects
records = [pandas_create.Record(i, f"Name{i}", i * 10.0) for i in range(5)]
df = pandas_create.records_to_dataframe(records)
```

## Real-World Applications

- Data ingestion from Rust services
- Creating report data
- Converting Rust structs to DataFrames
- Building test data
- ETL pipelines

## Next Steps

- Example 05: GroupBy and aggregation operations
- Example 06: Basic Polars DataFrame operations
