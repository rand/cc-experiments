# Example 02: Collection Conversion

Learn how to seamlessly convert between Rust and Python collection types (List, Dict, Set, Tuple).

## What You'll Learn

- Converting Vec ↔ List
- Converting HashMap ↔ Dict
- Converting HashSet ↔ Set
- Working with tuples
- Handling nested collections
- Processing collections in Rust with Python API

## Key Concepts

### Automatic Conversion

PyO3 provides automatic conversion for common types:

```rust
// Python list → Rust Vec
fn process_list(&self, items: Vec<i32>) -> Vec<i32> {
    items.into_iter().filter(|x| x % 2 == 0).collect()
}

// Python dict → Rust HashMap
fn process_dict(&self, data: HashMap<String, i32>) -> HashMap<String, i32> {
    data.into_iter().filter(|(_, v)| *v > 10).collect()
}

// Python set → Rust HashSet
fn process_set(&self, items: HashSet<String>) -> HashSet<String> {
    items.into_iter().map(|s| s.to_uppercase()).collect()
}
```

### Type Requirements

For automatic conversion:
- Keys and values must implement `FromPyObject` and `ToPyObject`
- Common types work out of the box: integers, floats, strings, bools
- Custom types need trait implementations

## Components

### ListConverter

Operations on lists:
- `roundtrip(list)`: Convert list to Rust and back
- `process_list(list)`: Filter and transform
- `create_nested()`: Build nested list structures

### DictConverter

Operations on dictionaries:
- `roundtrip(dict)`: Convert dict to Rust and back
- `invert(dict)`: Swap keys and values
- `merge_sum(dict1, dict2)`: Merge with value summation
- `filter_values(dict, threshold)`: Filter by value

### SetConverter

Operations on sets:
- `roundtrip(set)`: Convert set to Rust and back
- `union(set1, set2)`: Set union
- `intersection(set1, set2)`: Set intersection
- `difference(set1, set2)`: Set difference
- `deduplicate(list)`: Remove duplicates from list

### Helper Functions

- `tuple_operations(data)`: Process list of tuples
- `mixed_collections()`: Create complex nested structures

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
import collection_conversion

# List operations
list_conv = collection_conversion.ListConverter()
evens_doubled = list_conv.process_list([1, 2, 3, 4, 5, 6])
print(evens_doubled)  # [4, 8, 12]

# Dictionary operations
dict_conv = collection_conversion.DictConverter()
merged = dict_conv.merge_sum(
    {"a": 1, "b": 2},
    {"b": 3, "c": 4}
)
print(merged)  # {"a": 1, "b": 5, "c": 4}

# Set operations
set_conv = collection_conversion.SetConverter()
unique_sorted = set_conv.deduplicate([1, 2, 2, 3, 3, 3])
print(unique_sorted)  # [1, 2, 3]

# Tuple operations
data = [
    ("alice", 10, 100.0),
    ("bob", 3, 200.0),
]
result = collection_conversion.tuple_operations(data)
print(result)  # [("ALICE", 20, 150.0)]
```

## Performance Considerations

### When Conversion is Cheap

- Small collections (< 1000 items)
- Simple types (integers, strings)
- One-time operations

### When Conversion is Expensive

- Large collections (> 1MB)
- Complex nested structures
- Repeated conversions in loops

For large data, consider:
- Zero-copy approaches (see advanced examples)
- Processing in chunks
- Using numpy for numerical data

## Real-World Applications

- Data transformation pipelines
- Configuration processing
- API response formatting
- Database result processing
- JSON/data structure manipulation

## Common Patterns

### Filter-Map Pipeline
```rust
fn process(&self, items: Vec<i32>) -> Vec<i32> {
    items.into_iter()
        .filter(|x| x % 2 == 0)
        .map(|x| x * 2)
        .collect()
}
```

### Dictionary Merging
```rust
fn merge(&self, a: HashMap<K, V>, b: HashMap<K, V>) -> HashMap<K, V> {
    let mut result = a;
    result.extend(b);
    result
}
```

### Set Operations
```rust
fn unique(&self, items: Vec<T>) -> Vec<T> {
    let set: HashSet<_> = items.into_iter().collect();
    set.into_iter().collect()
}
```

## Next Steps

- Example 03: Sequence protocol for custom types
- Example 04: Lazy evaluation with iterators
- Example 08: Streaming large datasets with zero-copy

## Troubleshooting

### Type Mismatch Errors
Ensure Python types match Rust expectations:
```python
# Wrong: passing float where int expected
converter.process_list([1.5, 2.5])  # Error!

# Right: use integers
converter.process_list([1, 2])  # OK
```

### Ownership Issues
PyO3 handles ownership automatically. Rust moves values, Python sees copies:
```rust
fn take_ownership(&self, items: Vec<i32>) -> Vec<i32> {
    // 'items' is moved into Rust
    items  // Moved back to Python
}
```
