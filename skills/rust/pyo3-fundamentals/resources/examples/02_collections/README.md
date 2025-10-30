# Example 02: Collections

This example demonstrates working with Python collections in Rust using PyO3.

## What You'll Learn

- Converting Python lists to Rust Vec<T>
- Working with dictionaries (HashMap<K, V>)
- Handling tuples for multiple return values
- Using sets (HashSet<T>)
- Nested collection operations
- Direct PyList and PyDict manipulation

## Building

```bash
maturin develop
```

## Running Tests

```bash
pytest test_example.py -v
```

## Usage Examples

```python
import collections as col

# List operations
col.sum_list([1, 2, 3, 4, 5])  # 15
col.double_list([1, 2, 3])  # [2, 4, 6]
col.filter_positive([1, -2, 3, -4])  # [1, 3]

# Dictionary operations
col.sum_dict_values({"a": 10, "b": 20})  # 30
col.invert_dict({"a": "x", "b": "y"})  # {"x": "a", "y": "b"}
col.get_with_default({"a": 10}, "b", 99)  # 99

# Tuple operations
col.min_max([3, 1, 4, 1, 5])  # (1, 5)
col.tuple_sum((10, 20))  # 30

# Set operations
col.unique_elements([1, 2, 2, 3, 3])  # {1, 2, 3}
col.set_intersection({1, 2, 3}, {2, 3, 4})  # {2, 3}
col.set_union({"a", "b"}, {"b", "c"})  # {"a", "b", "c"}

# Nested collections
col.sum_tuples([(1, 2), (3, 4)])  # [3, 7]
col.flatten_dict_lists({"a": [1, 2], "b": [3, 4]})  # [1, 2, 3, 4]

# Complex transformations
records = [
    {"name": 1, "age": 25},
    {"name": 2, "age": 30},
]
col.transpose_data(records)  # {"name": [1, 2], "age": [25, 30]}

words = ["apple", "apricot", "banana"]
col.group_by_first_letter(words)  # {"a": ["apple", "apricot"], "b": ["banana"]}
```

## Key Concepts

### Automatic Collection Conversion

PyO3 automatically converts:
- Python `list` ↔ Rust `Vec<T>`
- Python `dict` ↔ Rust `HashMap<K, V>`
- Python `tuple` ↔ Rust `(T1, T2, ...)`
- Python `set` ↔ Rust `HashSet<T>`

### Ownership and Performance

When converting collections:
- Python → Rust: Data is copied into Rust-owned collections
- Rust → Python: Data is moved/copied into Python objects
- For large collections, consider zero-copy approaches (see advanced examples)

### Working with PyList/PyDict Directly

For advanced operations, you can work with Python objects directly:

```rust
fn reverse_in_place(py: Python, list: Vec<i64>) -> PyResult<Bound<PyList>> {
    let mut reversed = list;
    reversed.reverse();
    Ok(PyList::new_bound(py, reversed))
}
```

This gives you more control but requires `Python` token.

### Nested Collections

You can work with arbitrarily nested collections:

```rust
// List of tuples
fn sum_tuples(pairs: Vec<(i64, i64)>) -> PyResult<Vec<i64>>

// Dict of lists
fn flatten_dict_lists(data: HashMap<String, Vec<i64>>) -> PyResult<Vec<i64>>

// List of dicts
fn transpose_data(records: Vec<HashMap<String, i64>>) -> PyResult<HashMap<String, Vec<i64>>>
```

## Performance Considerations

- Small collections: Conversion overhead is negligible
- Large collections: Copying can be expensive
- For GB-scale data, use zero-copy techniques (numpy arrays, Arrow)
- HashMap operations are O(1) average case in both languages

## Common Patterns

### Filtering
```rust
numbers.into_iter().filter(|&x| x > 0).collect()
```

### Mapping
```rust
numbers.into_iter().map(|x| x * 2).collect()
```

### Grouping
```rust
for item in items {
    result.entry(key).or_insert_with(Vec::new).push(item);
}
```

## Next Steps

- **03_simple_class**: Creating Python classes in Rust
- **04_type_validation**: Custom type validators
- **05_complex_types**: Nested structures, Option, Result
