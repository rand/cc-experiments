# Basic Type Mapping Example

This example demonstrates fundamental Python ↔ Rust type conversions for DSPy integration using PyO3.

## Overview

Shows how to map basic Python types to Rust equivalents when extracting data from DSPy predictions:

| Python Type | Rust Type | Example |
|-------------|-----------|---------|
| `str` | `String` | `"hello"` → `String::from("hello")` |
| `int` | `i64` | `42` → `42i64` |
| `float` | `f64` | `3.14` → `3.14f64` |
| `bool` | `bool` | `True` → `true` |
| `List[str]` | `Vec<String>` | `["a", "b"]` → `vec!["a".to_string(), "b".to_string()]` |
| `Dict[str, int]` | `HashMap<String, i64>` | `{"x": 1}` → `HashMap::from([("x".to_string(), 1)])` |
| `Optional[T]` | `Option<T>` | `None` → `None`, `"value"` → `Some("value".to_string())` |

## What This Example Demonstrates

1. **String Extraction**: Converting Python strings to Rust `String`
2. **Numeric Types**: Handling integers and floats with proper type conversions
3. **Boolean Values**: Extracting boolean flags from predictions
4. **Collections**: Working with lists and dictionaries
5. **Optional Values**: Safely handling `None` cases with `Option<T>`
6. **Error Handling**: Robust extraction with `anyhow::Result`
7. **Round-Trip Testing**: Verifying conversions work in both directions

## Files

- `src/main.rs` - Complete type mapping examples with extraction patterns
- `Cargo.toml` - Dependencies (pyo3, anyhow, serde, serde_json)

## Building and Running

```bash
# Build the example
cargo build

# Run the demonstration
cargo run

# Run tests
cargo test
```

## Example Output

```
=== Basic Type Mapping Examples ===

String Extraction:
  Python: "Hello, World!"
  Rust: Hello, World!

Integer Extraction:
  Python: 42
  Rust: 42

Float Extraction:
  Python: 3.14159
  Rust: 3.14159

Boolean Extraction:
  Python: True
  Rust: true

List[str] Extraction:
  Python: ["apple", "banana", "cherry"]
  Rust: ["apple", "banana", "cherry"]

Dict[str, int] Extraction:
  Python: {"x": 10, "y": 20, "z": 30}
  Rust: {"x": 10, "y": 20, "z": 30}

Optional[str] Extraction:
  Python: "some_value"
  Rust: Some("some_value")

  Python: None
  Rust: None
```

## Key Patterns

### Safe String Extraction

```rust
fn extract_string(obj: &PyAny) -> Result<String> {
    obj.extract::<String>()
        .context("Failed to extract string")
}
```

### List Iteration

```rust
fn extract_string_list(obj: &PyAny) -> Result<Vec<String>> {
    let list = obj.downcast::<PyList>()?;
    list.iter()
        .map(|item| item.extract::<String>())
        .collect::<PyResult<Vec<String>>>()
        .context("Failed to extract string list")
}
```

### Dictionary Conversion

```rust
fn extract_dict(obj: &PyAny) -> Result<HashMap<String, i64>> {
    let dict = obj.downcast::<PyDict>()?;
    let mut map = HashMap::new();

    for (key, value) in dict.iter() {
        let k = key.extract::<String>()?;
        let v = value.extract::<i64>()?;
        map.insert(k, v);
    }

    Ok(map)
}
```

### Optional Handling

```rust
fn extract_optional_string(obj: &PyAny) -> Result<Option<String>> {
    if obj.is_none() {
        Ok(None)
    } else {
        Ok(Some(obj.extract::<String>()?))
    }
}
```

## Common Patterns from DSPy

When working with DSPy predictions, you'll typically see:

```python
# DSPy prediction structure
prediction = Prediction(
    summary="A text summary",      # str
    confidence=0.95,                # float
    word_count=150,                 # int
    is_valid=True,                  # bool
    tags=["tag1", "tag2"],          # List[str]
    metadata={"key": "value"},      # Dict[str, str]
    optional_field=None,            # Optional[str]
)
```

Rust extraction:

```rust
let summary: String = pred.getattr("summary")?.extract()?;
let confidence: f64 = pred.getattr("confidence")?.extract()?;
let word_count: i64 = pred.getattr("word_count")?.extract()?;
let is_valid: bool = pred.getattr("is_valid")?.extract()?;
let tags: Vec<String> = extract_string_list(pred.getattr("tags")?)?;
let metadata: HashMap<String, String> = extract_dict(pred.getattr("metadata")?)?;
let optional: Option<String> = extract_optional(pred.getattr("optional_field")?)?;
```

## Error Handling

All extraction functions use `anyhow::Result` for consistent error handling:

```rust
use anyhow::{Context, Result};

fn safe_extraction() -> Result<()> {
    Python::with_gil(|py| {
        let value = get_python_object(py);

        // Extraction with context
        let s = value.extract::<String>()
            .context("Failed to extract string from prediction")?;

        Ok(())
    })
}
```

## Type Safety

Rust's type system provides compile-time guarantees:

```rust
// Compiler prevents type mismatches
let count: i64 = prediction.getattr("count")?.extract()?; // ✓
let count: String = prediction.getattr("count")?.extract()?; // ✗ Runtime error

// Option<T> forces explicit None handling
match extract_optional(obj)? {
    Some(value) => println!("Got: {}", value),
    None => println!("No value provided"),
}
```

## Next Steps

After mastering basic types, see:

- **Complex Structs**: `resources/examples/complex-structs/` for nested structures
- **Custom Types**: `resources/examples/custom-types/` for domain-specific conversions
- **Error Handling**: `resources/examples/error-handling/` for robust extraction patterns

## References

- [PyO3 Type Conversions](https://pyo3.rs/latest/conversions.html)
- [PyO3 Python Types](https://pyo3.rs/latest/types.html)
- [Rust Type System](https://doc.rust-lang.org/book/ch03-02-data-types.html)
