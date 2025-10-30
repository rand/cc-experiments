# Example 10: Production Library

Complete production-ready text processing library demonstrating all PyO3 best practices.

## What You'll Learn

- Production-ready API design
- Comprehensive error handling
- Input validation
- Performance optimization
- Documentation
- Testing
- Versioning

## Building

```bash
maturin develop --release
```

## Features

### TextProcessor Class
```python
import production_library as pl

# Create processor
proc = pl.TextProcessor("Your text here", case_sensitive=False)

# Get statistics
stats = proc.stats()
print(f"Words: {stats.word_count}")
print(f"Unique: {stats.unique_words}")

# Word frequency analysis
freq = proc.word_frequency()
common = proc.most_common(10)

# Search and replace
positions = proc.find_all("pattern")
new_text = proc.replace_all("old", "new")

# Extract data
sentences = proc.sentences()
```

### Utility Functions
```python
# Word counting
pl.count_words("Hello world")  # 2

# Text manipulation
pl.reverse_text("abc")  # "cba"
pl.truncate("Long text...", max_words=10)

# Analysis
pl.is_palindrome("A man a plan a canal Panama")
pl.reading_time("Your text", wpm=200)
pl.extract_urls("Visit https://example.com")
```

## Production Best Practices

### Input Validation
```rust
#[new]
fn new(text: String) -> PyResult<Self> {
    if text.is_empty() {
        return Err(PyValueError::new_err("Text cannot be empty"));
    }
    Ok(...)
}
```

### Default Parameters
```rust
#[pyo3(signature = (text, case_sensitive=false))]
fn new(text: String, case_sensitive: bool) -> PyResult<Self>
```

### Error Handling
All operations return appropriate Python exceptions with clear messages.

### Performance
- Efficient string operations
- Minimal allocations
- Optimized algorithms

### API Design
- Intuitive method names
- Consistent return types
- Clear documentation
- Type safety

## Testing

```bash
pytest test_example.py -v
```

## Benchmarking

Compare with pure Python implementations:
```python
import timeit
import production_library as pl

text = "your large text" * 1000

# Rust implementation
rust_time = timeit.timeit(
    lambda: pl.TextProcessor(text).stats(),
    number=1000
)

# Python implementation
# ... compare ...
```

## Next Steps

This example combines all concepts from previous examples:
- Type conversions (01)
- Collections (02)
- Classes (03)
- Validation (04)
- Complex types (05)
- Properties (07)
- Custom converters (08)

Use this as a template for your own production PyO3 libraries.

## Version

v0.1.0 - Initial release
