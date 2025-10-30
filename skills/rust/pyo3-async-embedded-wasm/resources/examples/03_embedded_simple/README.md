# Example 03: Simple Embedded Python

This example demonstrates how to embed a Python interpreter in a Rust application, executing Python code from within Rust.

## Concepts Covered

- Embedding Python in Rust binaries
- Executing Python code from Rust
- Passing data between Rust and Python
- Calling Python standard library functions
- Working with Python collections from Rust
- Error handling with embedded Python

## Code Structure

- `src/main.rs`: Rust binary that embeds Python interpreter
  - Execute simple Python expressions
  - Pass data between Rust and Python
  - Call standard library functions
  - Execute Python scripts
  - Work with collections
  - Define and call Python functions
  - Handle Python exceptions

## Building

```bash
# Build the binary
cargo build --release

# Run the example
cargo run
```

Note: This is a Rust binary, not a Python extension. It embeds Python within Rust.

## Running

```bash
# Run the embedded Python examples
cargo run

# Build optimized version
cargo build --release
./target/release/embedded_simple
```

## Key Patterns

### Initialize Python

```rust
fn main() -> PyResult<()> {
    // Initialize Python interpreter
    pyo3::prepare_freethreaded_python();

    // All Python operations must use with_gil
    Python::with_gil(|py| {
        // Python code here
    })
}
```

Key points:
- Call `prepare_freethreaded_python()` once at startup
- Use `Python::with_gil()` for all Python operations
- The GIL is acquired automatically within the closure

### Execute Simple Code

```rust
Python::with_gil(|py| {
    // Evaluate expression
    let result = py.eval("2 + 2", None, None)?;
    println!("Result: {}", result);

    // Run statements
    py.run("print('Hello from Python!')", None, None)?;

    Ok(())
})
```

### Pass Data to Python

```rust
Python::with_gil(|py| {
    // Create locals dictionary
    let locals = [
        ("rust_value", 42i32),
        ("multiplier", 3i32),
    ].into_py_dict(py);

    // Execute with locals
    py.run("result = rust_value * multiplier", None, Some(locals))?;

    // Extract result
    let result: i32 = locals.get_item("result")?.extract()?;
    println!("Result: {}", result);

    Ok(())
})
```

### Call Standard Library

```rust
Python::with_gil(|py| {
    // Import module
    let sys = py.import("sys")?;
    let version: String = sys.getattr("version")?.extract()?;

    // Call function
    let math = py.import("math")?;
    let sqrt_func = math.getattr("sqrt")?;
    let result: f64 = sqrt_func.call1((16.0,))?.extract()?;

    Ok(())
})
```

### Execute Scripts

```rust
let script = r#"
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b

result = [fibonacci(i) for i in range(10)]
"#;

Python::with_gil(|py| {
    let locals = PyDict::new(py);
    py.run(script, None, Some(locals))?;

    let result: Vec<i64> = locals.get_item("result")?.extract()?;
    println!("Fibonacci: {:?}", result);

    Ok(())
})
```

### Work with Collections

```rust
Python::with_gil(|py| {
    // Create Python list from Rust
    let rust_vec = vec![1, 2, 3, 4, 5];
    let py_list = PyList::new(py, &rust_vec);

    // Manipulate list
    py_list.append(6)?;

    // Extract back to Rust
    let back_to_rust: Vec<i32> = py_list.extract()?;

    // Create dict from HashMap
    let rust_map = HashMap::new();
    rust_map.insert("key", "value");
    let py_dict = rust_map.into_py_dict(py);

    Ok(())
})
```

### Error Handling

```rust
Python::with_gil(|py| {
    let result = py.eval("1 / 0", None, None);

    match result {
        Ok(_) => println!("Success"),
        Err(e) => {
            println!("Exception type: {}", e.get_type(py).name()?);
            println!("Exception message: {}", e.value(py));
        }
    }

    Ok(())
})
```

## Use Cases

### Configuration with Python

```rust
// Load and execute config.py
let config = std::fs::read_to_string("config.py")?;

Python::with_gil(|py| {
    let globals = PyDict::new(py);
    py.run(&config, Some(globals), None)?;

    let host: String = globals.get_item("HOST")?.extract()?;
    let port: u16 = globals.get_item("PORT")?.extract()?;

    println!("Config: {}:{}", host, port);
    Ok(())
})
```

### Plugin System

```rust
fn load_plugin(path: &str) -> PyResult<()> {
    let code = std::fs::read_to_string(path)?;

    Python::with_gil(|py| {
        let module = PyModule::from_code(py, &code, "plugin.py", "plugin")?;
        let plugin_class = module.getattr("Plugin")?;
        let plugin = plugin_class.call0()?;

        // Call plugin methods
        let result = plugin.call_method0("process")?;

        Ok(())
    })
}
```

## Cargo.toml Configuration

```toml
[dependencies]
pyo3 = { version = "0.20", features = ["auto-initialize"] }
```

Key features:
- `auto-initialize`: Automatically initialize Python interpreter
- For binary applications (not extensions)

## Learning Objectives

After completing this example, you should understand:

1. How to embed Python in Rust applications
2. How to execute Python code from Rust
3. How to pass data between Rust and Python
4. How to call Python standard library
5. How to handle Python exceptions in Rust
6. How to work with Python collections from Rust

## Next Steps

- **Example 04**: Learn about async streams and backpressure
- **Example 05**: Explore advanced plugin systems
- **Example 06**: Build a complete plugin system with hot reloading
