# Example 09: Parquet File Reading/Writing

Demonstrates reading and writing Parquet files with PyO3.

## Functions

- `write_parquet(df, path)`: Write DataFrame to Parquet
- `read_parquet(path, engine)`: Read Parquet file
- `parquet_exists(path)`: Check file existence
- `get_parquet_metadata(path)`: Extract metadata

## Usage

```python
import pandas as pd
import parquet_io

df = pd.DataFrame({'id': [1, 2, 3], 'value': [10, 20, 30]})

parquet_io.write_parquet(df, "data.parquet")
df_read = parquet_io.read_parquet("data.parquet")
metadata = parquet_io.get_parquet_metadata("data.parquet")
```

## Requirements

```bash
pip install pandas pyarrow
```
