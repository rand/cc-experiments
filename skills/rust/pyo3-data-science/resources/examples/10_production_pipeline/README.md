# Example 10: Production Data Pipeline

Complete production-ready data pipeline combining CSV reading, processing, and Parquet writing.

## What You'll Learn

- Building end-to-end data pipelines
- Input validation
- Batch processing
- Data quality checks
- Error handling

## Functions

- `process_pipeline(csv_path, output_path, multiplier)`: Complete pipeline
- `validate_pipeline_input(csv_path)`: Validate inputs
- `batch_process(input_files, output_dir, multiplier)`: Batch processing
- `quality_check(values, min_val, max_val)`: Data quality validation

## Usage

```python
import production_pipeline

# Single file processing
rows = production_pipeline.process_pipeline(
    "input.csv",
    "output.parquet",
    multiplier=2.0
)

# Batch processing
total_rows = production_pipeline.batch_process(
    ["file1.csv", "file2.csv"],
    "output_dir/",
    multiplier=1.5
)

# Quality check
import numpy as np
values = np.array([1.0, 5.0, 10.0])
valid, invalid = production_pipeline.quality_check(values, 0.0, 8.0)
```

## Real-World Applications

- ETL pipelines
- Data preprocessing
- Batch data transformation
- Data validation and cleaning
- Production data workflows

## Requirements

```bash
pip install pandas pyarrow numpy
```
