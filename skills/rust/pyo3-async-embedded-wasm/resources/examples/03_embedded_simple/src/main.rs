use pyo3::prelude::*;
use pyo3::types::{IntoPyDict, PyDict, PyList};
use std::collections::HashMap;

/// Example 1: Execute simple Python code
fn execute_simple_code() -> PyResult<()> {
    println!("=== Example 1: Simple Code Execution ===");

    Python::with_gil(|py| {
        // Execute simple expression
        let result = py.eval("2 + 2", None, None)?;
        println!("2 + 2 = {}", result);

        // Execute multiple statements
        py.run(
            r#"
x = 10
y = 20
z = x + y
print(f"x + y = {z}")
"#,
            None,
            None,
        )?;

        Ok(())
    })
}

/// Example 2: Pass data between Rust and Python
fn pass_data_to_python() -> PyResult<()> {
    println!("\n=== Example 2: Data Exchange ===");

    Python::with_gil(|py| {
        // Create Python dict with Rust data
        let locals = [("rust_value", 42i32), ("multiplier", 3i32)].into_py_dict(py);

        // Execute Python code with locals
        py.run("result = rust_value * multiplier", None, Some(locals))?;

        // Extract result back to Rust
        let result: i32 = locals.get_item("result").unwrap().extract()?;
        println!("Result from Python: {}", result);

        Ok(())
    })
}

/// Example 3: Call Python standard library functions
fn call_stdlib_functions() -> PyResult<()> {
    println!("\n=== Example 3: Standard Library ===");

    Python::with_gil(|py| {
        // Import sys module
        let sys = py.import("sys")?;
        let version: String = sys.getattr("version")?.extract()?;
        println!("Python version: {}", version);

        // Import and use math module
        let math = py.import("math")?;
        let pi: f64 = math.getattr("pi")?.extract()?;
        println!("Pi from math module: {}", pi);

        // Call math.sqrt
        let sqrt_func = math.getattr("sqrt")?;
        let result: f64 = sqrt_func.call1((16.0,))?.extract()?;
        println!("sqrt(16) = {}", result);

        // Use builtins
        let builtins = py.import("builtins")?;
        let sum_func = builtins.getattr("sum")?;
        let numbers = vec![1, 2, 3, 4, 5];
        let sum: i64 = sum_func.call1((numbers,))?.extract()?;
        println!("sum([1,2,3,4,5]) = {}", sum);

        Ok(())
    })
}

/// Example 4: Execute Python script from string
fn execute_python_script() -> PyResult<()> {
    println!("\n=== Example 4: Execute Script ===");

    let script = r#"
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b

# Calculate first 10 Fibonacci numbers
fibs = [fibonacci(i) for i in range(10)]
print(f"First 10 Fibonacci numbers: {fibs}")
result = fibs
"#;

    Python::with_gil(|py| {
        let locals = PyDict::new(py);
        py.run(script, None, Some(locals))?;

        let result: Vec<i64> = locals.get_item("result").unwrap().extract()?;
        println!("Fibonacci numbers from Rust: {:?}", result);

        Ok(())
    })
}

/// Example 5: Work with Python collections
fn work_with_collections() -> PyResult<()> {
    println!("\n=== Example 5: Collections ===");

    Python::with_gil(|py| {
        // Create Python list from Rust
        let rust_vec = vec![1, 2, 3, 4, 5];
        let py_list = PyList::new(py, &rust_vec);
        println!("Python list from Rust: {}", py_list);

        // Manipulate Python list
        py_list.append(6)?;
        py_list.append(7)?;

        // Extract back to Rust
        let back_to_rust: Vec<i32> = py_list.extract()?;
        println!("Back to Rust: {:?}", back_to_rust);

        // Create Python dict from Rust HashMap
        let mut rust_map = HashMap::new();
        rust_map.insert("name", "Alice");
        rust_map.insert("role", "Developer");
        rust_map.insert("language", "Rust");

        let py_dict = rust_map.into_py_dict(py);
        println!("Python dict from Rust HashMap: {}", py_dict);

        Ok(())
    })
}

/// Example 6: Define and call Python functions
fn define_and_call_functions() -> PyResult<()> {
    println!("\n=== Example 6: Define Functions ===");

    Python::with_gil(|py| {
        // Define a Python function
        let code = r#"
def process_data(data, operation):
    if operation == "sum":
        return sum(data)
    elif operation == "product":
        result = 1
        for x in data:
            result *= x
        return result
    elif operation == "max":
        return max(data)
    else:
        return None
"#;
        let locals = PyDict::new(py);
        py.run(code, None, Some(locals))?;

        // Get the function
        let process_data = locals.get_item("process_data").unwrap();

        // Call it with different operations
        let data = vec![1, 2, 3, 4, 5];

        let sum: i64 = process_data.call1((data.clone(), "sum"))?.extract()?;
        println!("Sum: {}", sum);

        let product: i64 = process_data.call1((data.clone(), "product"))?.extract()?;
        println!("Product: {}", product);

        let max: i64 = process_data.call1((data.clone(), "max"))?.extract()?;
        println!("Max: {}", max);

        Ok(())
    })
}

/// Example 7: Error handling
fn error_handling() -> PyResult<()> {
    println!("\n=== Example 7: Error Handling ===");

    Python::with_gil(|py| {
        // This will raise a Python exception
        let result = py.eval("1 / 0", None, None);

        match result {
            Ok(_) => println!("No error (unexpected)"),
            Err(e) => {
                println!("Caught Python exception:");
                println!("  Type: {}", e.get_type(py).name()?);
                println!("  Message: {}", e.value(py));
            }
        }

        // Handle missing attributes
        let result = py.eval("nonexistent_variable", None, None);
        if let Err(e) = result {
            println!("\nCaught another exception:");
            println!("  Type: {}", e.get_type(py).name()?);
        }

        Ok(())
    })
}

fn main() -> PyResult<()> {
    println!("Embedded Python Examples\n");

    // Initialize Python interpreter
    pyo3::prepare_freethreaded_python();

    // Run examples
    execute_simple_code()?;
    pass_data_to_python()?;
    call_stdlib_functions()?;
    execute_python_script()?;
    work_with_collections()?;
    define_and_call_functions()?;
    error_handling()?;

    println!("\n=== All examples completed successfully ===");

    Ok(())
}
