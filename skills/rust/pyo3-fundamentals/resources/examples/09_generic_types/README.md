# Example 09: Generic Types

Generic-like behavior using PyAny and type-specific implementations.

## What You'll Learn

- Type-erased containers using PyAny
- Type-specific optimizations
- Generic Stack and Queue
- Polymorphic operations

## Building

```bash
maturin develop
```

## Usage

```python
import generic_types as gt

# Generic stack (holds any type)
stack = gt.Stack()
stack.push(10)
stack.push("hello")
stack.push([1, 2, 3])

# Type-specific stack (optimized)
int_stack = gt.IntStack()
int_stack.push(10)
int_stack.push(20)
print(int_stack.sum())  # 30

# Generic queue
queue = gt.Queue()
queue.enqueue("first")
queue.enqueue("second")

# Typed container
container = gt.TypedContainer()
container.add_int(42)
container.add_string("hello")
container.add_float(3.14)
```

## Key Concepts

### Type-Erased Container
```rust
#[pyclass]
struct Stack {
    items: Vec<Py<PyAny>>,  // Holds any Python object
}
```

### Type-Specific Optimization
```rust
#[pyclass]
struct IntStack {
    items: Vec<i64>,  // Optimized for integers
}
```

### Trade-offs
- Generic: Flexible but less optimized
- Type-specific: Fast but less flexible

## Next Steps
- **10_production_library**: Complete production example
