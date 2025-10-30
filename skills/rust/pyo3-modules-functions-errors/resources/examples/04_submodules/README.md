# Example 04: Submodules and Module Organization

This example demonstrates how to organize PyO3 modules into a hierarchical structure with submodules, similar to Python's package organization.

## What You'll Learn

- Creating submodules within a PyO3 module
- Organizing functions logically across submodules
- Module registration patterns
- Accessing submodules from Python
- Best practices for large project structure

## Building and Running

```bash
maturin develop
pytest test_example.py -v
```

## Interactive Usage

```python
import submodules

# Access submodules
submodules.math.add(5, 3)              # 8
submodules.strings.reverse("hello")     # "olleh"
submodules.collections.unique([1, 2, 2, 3])  # [1, 2, 3]

# Import specific submodules
from submodules import math
math.multiply(4, 5)                     # 20

# Import specific functions
from submodules.math import divide
divide(10.0, 2.0)                       # 5.0

# Module metadata
print(submodules.__version__)
print(submodules.list_submodules())     # ['math', 'strings', 'collections']
```

## Key Concepts

### 1. Submodule Structure

Organize related functionality into Rust modules:

```rust
pub mod math {
    use pyo3::prelude::*;

    #[pyfunction]
    pub fn add(a: i64, b: i64) -> i64 {
        a + b
    }

    // More functions...

    pub fn register_module(py: Python, parent_module: &PyModule) -> PyResult<()> {
        let math_module = PyModule::new(py, "math")?;
        math_module.add_function(wrap_pyfunction!(add, math_module)?)?;
        parent_module.add_submodule(math_module)?;
        Ok(())
    }
}
```

### 2. Module Registration

Each submodule needs a registration function that:
1. Creates a new `PyModule`
2. Adds functions to it
3. Adds the submodule to the parent

```rust
pub fn register_module(py: Python, parent_module: &PyModule) -> PyResult<()> {
    let submod = PyModule::new(py, "submod")?;

    // Add functions
    submod.add_function(wrap_pyfunction!(my_func, submod)?)?;

    // Add to parent
    parent_module.add_submodule(submod)?;

    Ok(())
}
```

### 3. Main Module Setup

The main module registers all submodules:

```rust
#[pymodule]
fn my_module(py: Python, m: &PyModule) -> PyResult<()> {
    // Register submodules
    math::register_module(py, m)?;
    strings::register_module(py, m)?;
    collections::register_module(py, m)?;

    // Add root-level functions
    m.add_function(wrap_pyfunction!(get_version, m)?)?;

    Ok(())
}
```

### 4. Python Import Patterns

Submodules can be imported in multiple ways:

```python
# Pattern 1: Import parent module
import submodules
submodules.math.add(1, 2)

# Pattern 2: Import submodule
from submodules import math
math.add(1, 2)

# Pattern 3: Import function
from submodules.math import add
add(1, 2)
```

## Module Organization Patterns

### Pattern 1: Feature-Based Modules

Organize by functionality:
```
mymodule/
├── math/        # Mathematical operations
├── strings/     # String operations
├── io/          # I/O operations
└── utils/       # Utilities
```

### Pattern 2: Layer-Based Modules

Organize by abstraction layer:
```
mymodule/
├── core/        # Core functionality
├── api/         # Public API
├── utils/       # Internal utilities
└── types/       # Type definitions
```

### Pattern 3: Domain-Based Modules

Organize by problem domain:
```
mymodule/
├── database/    # Database operations
├── network/     # Network operations
├── parsing/     # Parsing utilities
└── crypto/      # Cryptographic functions
```

## Best Practices

### 1. Keep Submodules Focused

Each submodule should have a single, clear purpose:

```rust
// Good: Focused submodule
pub mod strings {
    // All string-related functions
}

// Bad: Mixed concerns
pub mod utils {
    // Strings, math, I/O all mixed together
}
```

### 2. Use Clear Naming

Submodule names should be:
- Descriptive
- Plural for collections of related functions
- Lowercase with underscores

```rust
pub mod math_ops { }      // Good
pub mod string_utils { }  // Good
pub mod stuff { }         // Bad: too vague
```

### 3. Document Submodules

Add docstrings to help users discover functionality:

```python
# In Python
help(submodules.math)  # Shows math submodule documentation
dir(submodules.math)   # Lists all functions in math
```

### 4. Consider Re-exports

For frequently-used functions, consider re-exporting at the root:

```rust
#[pymodule]
fn my_module(py: Python, m: &PyModule) -> PyResult<()> {
    math::register_module(py, m)?;

    // Re-export commonly used functions at root level
    m.add_function(wrap_pyfunction!(math::add, m)?)?;

    Ok(())
}
```

```python
# Now users can use both:
import my_module
my_module.add(1, 2)        # Re-exported at root
my_module.math.add(1, 2)   # Also available in submodule
```

## Scalability Considerations

### For Small Projects (< 10 functions)
- Keep everything in the root module
- No need for submodules

### For Medium Projects (10-50 functions)
- 2-4 logical submodules
- Clear separation of concerns
- This example shows good patterns

### For Large Projects (50+ functions)
- Multiple levels of submodules
- Consider separate Cargo crates
- Use re-exports for public API

## Common Issues

### Issue 1: Import Errors

```python
# This doesn't work:
import submodules.math
# Error: No module named 'submodules.math'

# This works:
import submodules
from submodules import math
```

### Issue 2: Circular Dependencies

Avoid circular dependencies between submodules:

```rust
// Bad: Circular dependency
pub mod a {
    use super::b;  // a depends on b
}

pub mod b {
    use super::a;  // b depends on a - CIRCULAR!
}
```

### Issue 3: Name Conflicts

Be careful with function names across submodules:

```rust
// Both submodules have 'parse' function - that's OK!
pub mod json {
    #[pyfunction]
    pub fn parse(s: &str) { }
}

pub mod xml {
    #[pyfunction]
    pub fn parse(s: &str) { }
}
```

```python
# Python: No conflict
submodules.json.parse("{}")
submodules.xml.parse("<root/>")
```

## Performance Notes

- Submodule organization has no runtime cost
- Function calls through submodules are just as fast
- Module creation happens once at import time

## Next Steps

- **Example 05**: Custom exception types
- **Example 06**: Function overloading patterns
- **Example 07**: Module constants and enums
- **Example 09**: Large-scale module organization

## References

- [PyO3 Modules Guide](https://pyo3.rs/latest/module.html)
- [Python Modules Documentation](https://docs.python.org/3/tutorial/modules.html)
