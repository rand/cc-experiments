# Example 10: Production-Ready API

A complete, production-ready PyO3 module demonstrating best practices.

## Features

### 1. Module Organization
- Root-level utilities
- `processing` submodule for data processing
- `stats` submodule for statistics

### 2. Configuration Management
```python
config = api.Config(debug=True, max_retries=5, timeout=60)
config.set_setting("api_key", "secret")
config.validate()
```

### 3. Batch Processing
```python
items = ["item1", "item2", "item3"]
result = api.processing.process_batch(items, config)
print(f"Success rate: {result.success_rate()}")
```

### 4. Data Transformation
```python
items = ["hello", "world"]
upper = api.processing.transform(items, "uppercase")
filtered = api.processing.filter_by_length(items, 3, 10)
```

### 5. Statistics
```python
numbers = [1.0, 2.0, 3.0, 4.0, 5.0]
stats = api.stats.compute_stats(numbers)
print(f"Mean: {stats['mean']}, Median: {stats['median']}")
```

### 6. Error Handling
- Custom exception hierarchy
- Configuration validation
- Input validation with detailed errors

## Build and Test

```bash
maturin develop
pytest test_example.py -v
```

## Production Checklist

- ✅ Version information exposed
- ✅ Constants documented and accessible
- ✅ Configuration with validation
- ✅ Comprehensive error handling
- ✅ Submodule organization
- ✅ Type safety throughout
- ✅ Full test coverage
- ✅ Documentation strings

## API Design Principles

1. **Fail fast**: Validate inputs early
2. **Clear errors**: Descriptive exception messages
3. **Sensible defaults**: Config with defaults
4. **Type safety**: Leverage Rust's type system
5. **Modularity**: Logical submodule structure
6. **Testability**: Easy to test all components

This example serves as a template for real-world PyO3 projects.
