# Example 08: Apache Arrow RecordBatch Creation

Demonstrates working with Apache Arrow tables through PyO3.

## Functions

- `create_arrow_table()`: Create Arrow table
- `get_schema(table)`: Get table schema
- `num_rows(table)`: Get row count

## Usage

```python
import arrow_basic

table = arrow_basic.create_arrow_table()
schema = arrow_basic.get_schema(table)
rows = arrow_basic.num_rows(table)
```

## Requirements

```bash
pip install pyarrow
```
