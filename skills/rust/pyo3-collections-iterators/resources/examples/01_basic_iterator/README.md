# Example 01: Basic Iterator

A foundational example demonstrating how to implement Python iterators in Rust using PyO3.

## What You'll Learn

- Implementing the Python iterator protocol (`__iter__` and `__next__`)
- Creating iterators that can be used in Python for loops
- Consuming Python iterators from Rust
- Creating Python iterators from Rust collections
- Understanding iterator state management

## Key Concepts

### Iterator Protocol

Python's iterator protocol requires two methods:
- `__iter__`: Returns the iterator object itself
- `__next__`: Returns the next item or raises StopIteration

In PyO3, we implement these as:
```rust
fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
    slf
}

fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<T> {
    // Return Some(value) or None when exhausted
}
```

### State Management

Iterators maintain internal state (like `current` position). PyO3 handles the conversion between Rust's `Option<T>` and Python's `StopIteration` exception automatically.

## Components

### NumberRange

A simple range iterator similar to Python's `range()`:
```python
for n in NumberRange(0, 5, 1):
    print(n)  # 0, 1, 2, 3, 4
```

### Counter

A stateful counter with a separate iterator:
```python
counter = Counter()
counter.increment()
counter.increment()

for i in counter.iter():
    print(i)  # 0, 1
```

### Helper Functions

- `sum_iterator(iterator)`: Demonstrates consuming Python iterators from Rust
- `create_iterator(list)`: Demonstrates creating Python iterators from Rust

## Building and Testing

```bash
# Install maturin if you haven't already
pip install maturin

# Build and install in development mode
maturin develop

# Run tests
python test_example.py

# Or use pytest
pytest test_example.py -v
```

## Usage Examples

```python
import basic_iterator

# Simple range iteration
for n in basic_iterator.NumberRange(0, 10, 2):
    print(n)  # 0, 2, 4, 6, 8

# Using counter
counter = basic_iterator.Counter()
for _ in range(5):
    counter.increment()

print(list(counter.iter()))  # [0, 1, 2, 3, 4]

# Sum a Python iterator in Rust
result = basic_iterator.sum_iterator(iter([1, 2, 3, 4]))
print(result)  # 10
```

## Real-World Applications

- Custom data source iterators
- Efficient number generation
- Stateful iteration over Rust data structures
- Bridge between Rust and Python iteration models

## Next Steps

- Example 02: Collection conversion (List, Dict, Set)
- Example 03: Sequence protocol (`__len__`, `__getitem__`)
- Example 04: Lazy iteration with complex state

## Performance Notes

Iterators are very efficient for:
- Large datasets that don't fit in memory
- Computational sequences (like ranges)
- Processing items one at a time

Avoid iterators when:
- You need random access
- Dataset is small and fits in memory
- You need to iterate multiple times (unless you can clone/reset)
