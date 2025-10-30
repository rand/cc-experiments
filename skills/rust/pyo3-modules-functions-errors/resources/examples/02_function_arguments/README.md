# Example 02: Function Arguments and Signatures

This example demonstrates how to handle different types of function arguments in PyO3, matching Python's flexible argument syntax.

## What You'll Learn

- Optional arguments using `Option<T>`
- Default values with `#[pyo3(signature = (...))]`
- Keyword-only arguments (after `*`)
- Variable positional arguments (`*args` via `&PyTuple`)
- Variable keyword arguments (`**kwargs` via `&PyDict`)
- Complex signatures combining multiple patterns

## Building and Running

```bash
maturin develop
pytest test_example.py -v
```

## Key Concepts

### 1. Optional Arguments

```rust
#[pyfunction]
fn greet_person(name: &str, age: Option<u32>) -> String {
    match age {
        Some(a) => format!("{} is {} years old", name, a),
        None => format!("Hello, {}", name),
    }
}
```

```python
greet_person("Alice")           # age is None
greet_person("Bob", 25)         # age is Some(25)
greet_person("Charlie", age=30) # keyword argument
```

### 2. Default Values

Use the `signature` attribute to specify default values:

```rust
#[pyfunction]
#[pyo3(signature = (base, exponent=2, modulo=None))]
fn power(base: i64, exponent: u32, modulo: Option<i64>) -> i64 {
    // Implementation
}
```

```python
power(3)           # exponent defaults to 2
power(5, 3)        # override exponent
power(10, 2, 7)    # all arguments
```

### 3. Keyword-Only Arguments

Arguments after `*` in the signature must be passed as keywords:

```rust
#[pyfunction]
#[pyo3(signature = (text, *, uppercase=false, trim=true, repeat=1))]
fn process_text(text: &str, uppercase: bool, trim: bool, repeat: usize) -> String {
    // Implementation
}
```

```python
process_text("hello")                      # Valid
process_text("hello", uppercase=True)      # Valid
process_text("hello", True)                # TypeError! Must use keyword
```

### 4. Variable Positional Arguments (*args)

Use `&PyTuple` to accept variable positional arguments:

```rust
#[pyfunction]
fn sum_numbers(numbers: &PyTuple) -> PyResult<i64> {
    let mut total: i64 = 0;
    for num in numbers.iter() {
        total += num.extract::<i64>()?;
    }
    Ok(total)
}
```

```python
sum_numbers()              # 0
sum_numbers(1, 2, 3)       # 6
sum_numbers(10, 20, 30)    # 60
```

### 5. Variable Keyword Arguments (**kwargs)

Use `Option<&PyDict>` to accept variable keyword arguments:

```rust
#[pyfunction]
fn uppercase_keys(kwargs: Option<&PyDict>) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let result = PyDict::new(py);
        if let Some(kw) = kwargs {
            for (key, value) in kw.iter() {
                let key_str: String = key.extract()?;
                result.set_item(key_str.to_uppercase(), value)?;
            }
        }
        Ok(result.into())
    })
}
```

```python
uppercase_keys(name="Alice", age=30)  # {"NAME": "Alice", "AGE": 30}
```

### 6. Combining All Patterns

```rust
#[pyfunction]
#[pyo3(signature = (prefix, *items, separator=", ", **options))]
fn combine_args(
    prefix: &str,
    items: &PyTuple,
    separator: &str,
    options: Option<&PyDict>,
) -> PyResult<PyObject> {
    // Implementation
}
```

```python
combine_args("Items", "a", "b", "c", separator=" | ", flag=True)
```

## Signature Syntax

The `#[pyo3(signature = (...))]` attribute follows Python's syntax:

```rust
#[pyo3(signature = (
    required,              // Required positional
    optional=None,         // Optional with default
    *args,                 // Variable positional (use &PyTuple)
    keyword_only="default", // Keyword-only after *
    **kwargs               // Variable keywords (use Option<&PyDict>)
))]
```

## Common Patterns

### Pattern 1: Optional with Default

```rust
#[pyfunction]
#[pyo3(signature = (name, count=1))]
fn repeat(name: &str, count: usize) -> String {
    name.repeat(count)
}
```

### Pattern 2: Keyword-Only Configuration

```rust
#[pyfunction]
#[pyo3(signature = (data, *, verbose=false, format="json"))]
fn process(data: &str, verbose: bool, format: &str) -> String {
    // Configuration options must be keywords
}
```

### Pattern 3: Flexible Arguments

```rust
#[pyfunction]
fn flex_sum(args: &PyTuple, kwargs: Option<&PyDict>) -> PyResult<i64> {
    // Accept any combination of positional and keyword arguments
}
```

## Type Conversion

PyO3 automatically handles conversion for common types:

- `i32`, `i64`, `u32`, `u64` ↔ Python `int`
- `f32`, `f64` ↔ Python `float`
- `bool` ↔ Python `bool`
- `&str`, `String` ↔ Python `str`
- `Option<T>` ↔ Python `Optional[T]` (None/Some)
- `Vec<T>` ↔ Python `list`
- `HashMap<K,V>` ↔ Python `dict`

## Error Handling

When extracting from `PyTuple` or `PyDict`, use `?` operator to propagate errors:

```rust
for item in tuple.iter() {
    let value: i64 = item.extract()?;  // Returns PyErr on failure
}
```

## Performance Considerations

1. **Signature complexity**: Complex signatures have minimal overhead
2. **Type extraction**: Extracting types from `PyTuple`/`PyDict` has some cost
3. **Default values**: Handled at Rust level, no Python overhead
4. **Optional arguments**: `Option<T>` is zero-cost in Rust

## Next Steps

- **Example 03**: Error handling and custom exceptions
- **Example 04**: Submodules and module organization
- **Example 06**: Function overloading with multiple signatures

## References

- [PyO3 Function Signatures](https://pyo3.rs/latest/function.html#function-signatures)
- [Python Function Arguments](https://docs.python.org/3/tutorial/controlflow.html#more-on-defining-functions)
