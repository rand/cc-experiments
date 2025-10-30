# Example 08: Callback Functions

Demonstrates calling Python functions from Rust code.

## Key Concepts

1. **Calling Python functions**: Using `PyObject.call1()`
2. **Error handling**: Catching Python exceptions in Rust
3. **Functional patterns**: map, filter, reduce with callbacks
4. **Callback chaining**: Composing multiple transformations

## Usage

```python
import callback_functions as cf

# Map
result = cf.map_with_callback([1, 2, 3], lambda x: x * 2)

# Filter  
evens = cf.filter_with_callback([1, 2, 3, 4], lambda x: x % 2 == 0)

# Reduce
total = cf.reduce_with_callback([1, 2, 3], lambda acc, x: acc + x, 0)

# Chain
result = cf.chain_callbacks(10, [lambda x: x * 2, lambda x: x + 5])
```

Build: `maturin develop && pytest test_example.py -v`

## Performance Note

Callback overhead: Each callback invocation crosses the Python/Rust boundary. For performance-critical code, minimize callback calls or use pure Rust implementations.
