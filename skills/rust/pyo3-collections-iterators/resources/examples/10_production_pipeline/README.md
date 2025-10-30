# Example 10: Production Pipeline

A comprehensive data processing pipeline combining all previous concepts for production use.

## What You'll Learn

- Building complete data pipelines
- Combining filtering, transformation, and aggregation
- Statistical analysis
- Time series processing
- Anomaly detection
- Parallel vs sequential execution
- Production-ready error handling

## Components

### DataPipeline

Complete data processing pipeline with:
- Record management
- Configurable filters
- Configurable transformations
- Statistical analysis
- Grouping operations
- Parallel execution support

### TimeSeriesProcessor

Time series analysis:
- Moving averages
- Anomaly detection (statistical outliers)
- Resampling to fixed intervals
- Trend analysis

## Usage

```python
import production_pipeline

# Create pipeline
pipeline = production_pipeline.DataPipeline()

# Add data
pipeline.add_record(id=1, value=100.0, category="sales", timestamp=1000)
pipeline.add_record(id=2, value=200.0, category="marketing", timestamp=2000)

# Configure filters
pipeline.add_filter("value", threshold=50.0)

# Configure transforms
pipeline.add_transform("multiply", factor=1.1)
pipeline.add_transform("log", factor=0.0)

# Execute (parallel or sequential)
results = pipeline.execute(parallel=True)

# Get statistics
stats = pipeline.statistics()
print(f"Mean: {stats['mean']}, Sum: {stats['sum']}")

# Group by category
groups = pipeline.group_by_category()

# Time series analysis
ts_data = [(timestamp, value) for timestamp, value in time_series_data]
ts = production_pipeline.TimeSeriesProcessor(ts_data)

# Moving average
smoothed = ts.moving_average(window_size=10)

# Detect anomalies
anomalies = ts.detect_anomalies(threshold=2.0)  # 2 std devs

# Resample to hourly
hourly = ts.resample(interval=3600)
```

## Real-World Applications

- ETL pipelines
- Real-time analytics
- Financial data processing
- IoT sensor data analysis
- Log aggregation and analysis
- Business intelligence systems

## Performance

The pipeline supports both sequential and parallel execution:

```python
# Sequential (better for small datasets)
results = pipeline.execute(parallel=False)

# Parallel (better for large datasets with CPU-bound operations)
results = pipeline.execute(parallel=True)
```

## Architecture

```
Data Input → Filters → Transforms → Aggregations → Output
              ↓           ↓            ↓
           Parallel    Parallel    Statistics
           Support     Support     Analysis
```

## Error Handling

The pipeline handles:
- Empty datasets
- Missing values
- Invalid operations
- Division by zero in statistics

## Extensibility

Easily extend with:
- Custom filters
- Custom transformations
- Additional aggregations
- New time series algorithms

Build: `maturin develop && python test_example.py`

## Next Steps

Apply these patterns to:
- Your specific domain data
- Custom business logic
- Integration with databases
- Real-time streaming systems
