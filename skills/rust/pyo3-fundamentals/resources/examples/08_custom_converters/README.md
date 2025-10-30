# Example 08: Custom Converters

Advanced type conversion using custom FromPyObject implementations.

## What You'll Learn

- Implementing FromPyObject trait
- Multiple input formats
- Type-safe conversions
- Flexible APIs

## Building

```bash
maturin develop
```

## Usage

```python
import custom_converters as cc

# Color accepts dict, tuple, or hex string
cc.make_color_darker({"r": 100, "g": 150, "b": 200}, 50)
cc.make_color_darker((100, 150, 200), 50)
cc.make_color_darker("#FF0000", 50)

# Coordinate from dict or tuple
cc.distance_between({"x": 0, "y": 0}, (3, 4))

# Duration from seconds or components
cc.sleep_for(3600)
cc.sleep_for({"hours": 1, "minutes": 30})
```

## Key Concepts

### Custom FromPyObject

```rust
impl<'py> FromPyObject<'py> for Color {
    fn extract_bound(obj: &Bound<'py, PyAny>) -> PyResult<Self> {
        // Try dict
        if let Ok(dict) = obj.downcast::<PyDict>() { ... }
        // Try tuple
        if let Ok((r, g, b)) = obj.extract::<(u8, u8, u8)>() { ... }
        // Try hex string
        if let Ok(s) = obj.downcast::<PyString>() { ... }
    }
}
```

### Benefits
- Flexible Python API
- Type safety in Rust
- Clear error messages
- Multiple input formats

## Next Steps
- **09_generic_types**: Generic containers
- **10_production_library**: Complete example
