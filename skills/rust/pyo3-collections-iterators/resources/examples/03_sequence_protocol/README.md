# Example 03: Sequence Protocol

Master Python's sequence protocol to create custom collection types that feel native to Python.

## What You'll Learn

- Implementing `__len__`, `__getitem__`, `__setitem__`, `__delitem__`
- Supporting slice operations
- Implementing `__contains__` for the `in` operator
- Supporting iteration with `__iter__` and `__reversed__`
- Handling negative indices Python-style
- Creating list-like and vector-like types

## Key Concepts

### Sequence Protocol Methods

Python sequences support these special methods:

```rust
fn __len__(&self) -> usize                        // len(obj)
fn __getitem__(&self, index: isize) -> T          // obj[index]
fn __setitem__(&mut self, index: isize, value: T) // obj[index] = value
fn __delitem__(&mut self, index: isize)           // del obj[index]
fn __contains__(&self, value: T) -> bool          // value in obj
fn __iter__(slf: PyRef<Self>) -> Iterator         // for x in obj
fn __reversed__(slf: PyRef<Self>) -> Iterator     // reversed(obj)
```

### Negative Index Handling

Python allows negative indices to access from the end:
```python
lst = [1, 2, 3, 4, 5]
lst[-1]  # 5 (last element)
lst[-2]  # 4 (second to last)
```

Implement this in Rust:
```rust
fn normalize_index(&self, index: isize) -> PyResult<usize> {
    let len = self.data.len() as isize;
    let idx = if index < 0 { len + index } else { index };

    if idx < 0 || idx >= len {
        Err(PyIndexError::new_err("Index out of range"))
    } else {
        Ok(idx as usize)
    }
}
```

### Slice Support

Advanced sequences support slicing:
```python
lst[1:3]    # Elements 1 and 2
lst[::2]    # Every other element
lst[::-1]   # Reversed
```

Handle slices in `__getitem__`:
```rust
fn __getitem__(&self, py: Python, index: &PyAny) -> PyResult<PyObject> {
    if let Ok(idx) = index.extract::<isize>() {
        // Single item
    } else if let Ok(slice) = index.extract::<PySlice>() {
        // Slice
        let indices = slice.indices(self.len() as i64)?;
        // Process slice...
    }
}
```

## Components

### IntVector

A mutable integer vector with full sequence protocol:
- Index access with `[]`
- Assignment with `[]=`
- Deletion with `del`
- Iteration and reversal
- Membership testing with `in`

### StringList

A string collection with slice support:
- Single item and slice access
- Negative indices
- Step-based slicing
- Extension and appending

## Building and Testing

```bash
# Install maturin
pip install maturin

# Build and install
maturin develop

# Run tests
python test_example.py

# Or use pytest
pytest test_example.py -v
```

## Usage Examples

```python
import sequence_protocol

# IntVector - full mutability
vec = sequence_protocol.IntVector([1, 2, 3, 4, 5])

# Access
print(vec[0])     # 1
print(vec[-1])    # 5

# Modify
vec[0] = 10
print(vec[0])     # 10

# Delete
del vec[2]
print(len(vec))   # 4

# Iterate
for x in vec:
    print(x)

# Reversed
for x in reversed(vec):
    print(x)

# Membership
if 3 in vec:
    print("Found 3")

# Append
vec.append(100)

# StringList - with slicing
lst = sequence_protocol.StringList(["a", "b", "c", "d", "e"])

# Slice access
print(lst[1:3])   # ["b", "c"]
print(lst[::2])   # ["a", "c", "e"]

# List comprehensions
doubled = [x * 2 for x in vec if x > 5]
```

## Comparison with Python Lists

| Feature | Python list | IntVector | StringList |
|---------|-------------|-----------|------------|
| `len()` | ✓ | ✓ | ✓ |
| `[i]` | ✓ | ✓ | ✓ |
| `[i] = v` | ✓ | ✓ | ✗ |
| `del [i]` | ✓ | ✓ | ✗ |
| `[i:j]` | ✓ | ✗ | ✓ |
| `in` | ✓ | ✓ | ✓ |
| `iter()` | ✓ | ✓ | ✗ |
| `reversed()` | ✓ | ✓ | ✗ |

## Performance Considerations

### Efficient Operations
- Index access: O(1)
- Append: O(1) amortized
- Iteration: O(n)
- Membership test: O(n)

### Expensive Operations
- Deletion: O(n) - shifts elements
- Insertion (not shown): O(n)

For better performance:
- Use sets for membership testing
- Use deques for frequent insertions/deletions at both ends
- Consider sorted structures for search-heavy workloads

## Real-World Applications

- Custom data structures (rings, circular buffers)
- Wrapped native Rust collections
- Domain-specific collections (time series, matrices)
- Constrained collections (bounded lists, validated data)

## Common Patterns

### Index Normalization
```rust
fn normalize_index(&self, index: isize) -> PyResult<usize> {
    let len = self.data.len() as isize;
    let idx = if index < 0 { len + index } else { index };
    if idx < 0 || idx >= len {
        Err(PyIndexError::new_err("Index out of range"))
    } else {
        Ok(idx as usize)
    }
}
```

### Iterator Creation
```rust
fn __iter__(slf: PyRef<'_, Self>) -> PyResult<Py<MyIterator>> {
    let iter = MyIterator {
        data: slf.data.clone(),
        index: 0,
    };
    Py::new(slf.py(), iter)
}
```

### Slice Processing
```rust
if let Ok(slice) = index.extract::<PySlice>() {
    let indices = slice.indices(self.len() as i64)?;
    // Extract start, stop, step
    // Generate sliced data
}
```

## Next Steps

- Example 04: Lazy iterators with complex state
- Example 05: Bidirectional iteration
- Example 06: Custom collection with mapping protocol

## Troubleshooting

### Index Errors
Always validate indices:
```rust
if idx >= self.data.len() {
    return Err(PyIndexError::new_err("Index out of range"));
}
```

### Slice Edge Cases
Handle empty slices and step values:
```rust
let step = indices.step;
if step == 0 {
    return Err(PyValueError::new_err("Step cannot be zero"));
}
```

### Iterator Lifetime
Return owned iterators, not references:
```rust
// Good: owned data
fn __iter__(slf: PyRef<Self>) -> MyIterator {
    MyIterator { data: slf.data.clone(), index: 0 }
}

// Bad: borrowing (lifetime issues)
// fn __iter__(&self) -> impl Iterator<Item = &T>
```
