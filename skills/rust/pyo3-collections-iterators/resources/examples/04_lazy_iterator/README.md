# Example 04: Lazy Iterator

Learn to build lazy iterators that compute values on-demand, enabling efficient processing of large or infinite sequences.

## What You'll Learn

- Lazy evaluation principles
- State management for complex iterators
- Iterator chaining and composition
- Transforming iterators without materializing data
- Memory-efficient data processing

## Key Concepts

### Lazy Evaluation

Lazy evaluation defers computation until values are actually needed:

```rust
// Generates values on-demand, not all at once
fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<T> {
    // Compute next value only when requested
    Some(computed_value)
}
```

Benefits:
- Process infinite sequences
- Low memory footprint
- Early termination possible
- Pipeline optimizations

### State Management

Complex iterators maintain internal state:

```rust
#[pyclass]
struct Fibonacci {
    current: u64,
    next: u64,
    max_value: Option<u64>,
}
```

State is updated only when `__next__` is called.

## Components

### Fibonacci

Generates Fibonacci numbers lazily:
```python
fib = Fibonacci(max_value=100)
for num in fib:
    print(num)  # 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89
```

### LazyFileReader

Reads lines on-demand:
```python
reader = LazyFileReader(content)
for line in reader:
    if line.startswith("ERROR"):
        print(line)
        break  # No need to read remaining lines
```

### FilteredIterator

Filters iterator lazily (no intermediate lists):
```python
filtered = reader.filter_prefix("a")
# Computation happens during iteration
```

### LazyRange

Range with transformations applied lazily:
```python
# Squares computed on-demand
squares = LazyRange(0, 10, 1, "square")
```

### ChainedIterator

Chains multiple iterators:
```python
chain = range1.chain(range2)
# Iterates first, then second, no concatenation
```

## Building and Testing

```bash
pip install maturin
maturin develop
python test_example.py
```

## Usage Examples

```python
import lazy_iterator

# Infinite Fibonacci (stopped manually)
fib = lazy_iterator.Fibonacci(max_value=None)
for i, num in enumerate(fib):
    if i >= 10:
        break
    print(num)

# Lazy file processing
content = open("large_file.txt").read()
reader = lazy_iterator.LazyFileReader(content)
errors = reader.filter_prefix("ERROR")

# Process only errors, skip rest of file
for error_line in errors:
    log_error(error_line)

# Transform on-the-fly
squares = lazy_iterator.LazyRange(1, 1000000, 1, "square")
# Only compute squares as needed
first_ten_squares = [x for i, x in enumerate(squares) if i < 10]

# Chain operations
range1 = lazy_iterator.LazyRange(0, 5, 1, None)
range2 = lazy_iterator.LazyRange(10, 15, 1, "double")
combined = range1.chain(range2)
```

## Performance Benefits

### Memory Efficiency

Lazy vs Eager:
```python
# Eager (bad for large data)
all_values = [compute(x) for x in range(1000000)]
filtered = [x for x in all_values if x > 100]

# Lazy (good)
iterator = LazyRange(0, 1000000, 1, "square")
filtered = (x for x in iterator if x > 100)
```

### Early Termination

Stop as soon as condition met:
```python
# Find first Fibonacci number > 1000
fib = lazy_iterator.Fibonacci(max_value=None)
for num in fib:
    if num > 1000:
        print(f"Found: {num}")
        break  # Stops iteration immediately
```

### Composition

Chain operations without intermediate storage:
```python
# All transformations lazy until final consumption
result = lazy_range.chain(another_range)
filtered = (x for x in result if x % 2 == 0)
final = list(filtered)  # Compute only now
```

## Real-World Applications

- Log file processing (GB+ files)
- Database result streaming
- Infinite sequence generation
- Pipeline processing
- Event stream handling

## Common Patterns

### Infinite Sequences
```rust
fn __next__(mut slf: PyRefMut<Self>) -> Option<T> {
    // No termination condition
    Some(slf.generate())
}
```

### Conditional Termination
```rust
fn __next__(mut slf: PyRefMut<Self>) -> Option<T> {
    if slf.should_stop() {
        None
    } else {
        Some(slf.compute())
    }
}
```

### Filtering
```rust
fn __next__(mut slf: PyRefMut<Self>) -> Option<T> {
    loop {
        let val = slf.source.next()?;
        if slf.predicate(&val) {
            return Some(val);
        }
    }
}
```

## Comparison: Lazy vs Eager

| Aspect | Lazy | Eager |
|--------|------|-------|
| Memory | O(1) | O(n) |
| Startup | Instant | Delayed |
| Termination | Early | Must complete |
| Composable | Yes | Limited |
| Debugging | Harder | Easier |

## Next Steps

- Example 05: Bidirectional iterators
- Example 06: Custom collections
- Example 08: Streaming large datasets

## Troubleshooting

### Unexpected Re-computation

Iterators are single-use:
```python
it = lazy_iterator.Fibonacci(100)
list1 = list(it)  # Consumes iterator
list2 = list(it)  # Empty! Iterator exhausted
```

Solution: Create new iterator or cache results.

### State Corruption

Ensure state updates are correct:
```rust
// Bad: state not updated
fn __next__(slf: PyRefMut<Self>) -> Option<T> {
    Some(slf.value)  // Returns same value forever!
}

// Good: state advances
fn __next__(mut slf: PyRefMut<Self>) -> Option<T> {
    let val = slf.value;
    slf.value += 1;
    Some(val)
}
```
