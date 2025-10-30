//! Advanced PyO3 Integration Examples
//!
//! This file demonstrates various PyO3 integration patterns used in the
//! production RAG system, useful for understanding the Rust-Python bridge.

use anyhow::{Context, Result};
use pyo3::{prelude::*, types::PyDict};
use std::collections::HashMap;

/// Example 1: Basic Python function call
///
/// Demonstrates calling a simple Python function with arguments.
fn example_basic_call() -> Result<()> {
    Python::with_gil(|py| {
        let sys = PyModule::import(py, "sys")?;
        let version: String = sys.getattr("version")?.extract()?;
        println!("Python version: {}", version);
        Ok(())
    })
}

/// Example 2: Executing Python code inline
///
/// Shows how to execute Python code as a string from Rust.
fn example_inline_code() -> Result<()> {
    Python::with_gil(|py| {
        let code = r#"
def greet(name):
    return f"Hello, {name}!"

result = greet("Rust")
"#;

        let module = PyModule::from_code(py, code, "inline.py", "inline")?;
        let result: String = module.getattr("result")?.extract()?;
        println!("Inline result: {}", result);
        Ok(())
    })
}

/// Example 3: Creating and using Python classes
///
/// Demonstrates instantiating Python classes and calling methods.
fn example_python_class() -> Result<()> {
    Python::with_gil(|py| {
        let code = r#"
class Calculator:
    def __init__(self, initial_value=0):
        self.value = initial_value

    def add(self, x):
        self.value += x
        return self.value

    def multiply(self, x):
        self.value *= x
        return self.value
"#;

        let module = PyModule::from_code(py, code, "calc.py", "calc")?;
        let calc_class = module.getattr("Calculator")?;

        // Create instance with initial value
        let calc = calc_class.call1((10,))?;

        // Call methods
        let result: i32 = calc.call_method1("add", (5,))?.extract()?;
        println!("After add(5): {}", result);

        let result: i32 = calc.call_method1("multiply", (3,))?.extract()?;
        println!("After multiply(3): {}", result);

        Ok(())
    })
}

/// Example 4: Passing Rust data to Python
///
/// Shows how to convert Rust types to Python objects.
fn example_rust_to_python() -> Result<()> {
    Python::with_gil(|py| {
        // Convert Rust vec to Python list
        let rust_vec = vec![1, 2, 3, 4, 5];
        let py_list = rust_vec.to_object(py);

        // Convert Rust HashMap to Python dict
        let mut rust_map = HashMap::new();
        rust_map.insert("name", "Production RAG");
        rust_map.insert("language", "Rust");
        let py_dict = rust_map.to_object(py);

        // Use in Python
        let code = r#"
def process_data(numbers, metadata):
    total = sum(numbers)
    return f"{metadata['name']} processed {total} items"
"#;

        let module = PyModule::from_code(py, code, "process.py", "process")?;
        let result: String = module
            .getattr("process_data")?
            .call1((py_list, py_dict))?
            .extract()?;

        println!("Result: {}", result);
        Ok(())
    })
}

/// Example 5: Extracting Python data to Rust
///
/// Demonstrates converting Python objects back to Rust types.
fn example_python_to_rust() -> Result<()> {
    Python::with_gil(|py| {
        let code = r#"
def get_embeddings():
    return [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

def get_metadata():
    return {
        "model": "all-MiniLM-L6-v2",
        "dimension": 384,
        "normalized": True
    }
"#;

        let module = PyModule::from_code(py, code, "data.py", "data")?;

        // Extract 2D vector
        let embeddings: Vec<Vec<f32>> =
            module.getattr("get_embeddings")?.call0()?.extract()?;
        println!("Embeddings: {:?}", embeddings);

        // Extract dictionary
        let metadata: HashMap<String, serde_json::Value> =
            module.getattr("get_metadata")?.call0()?.extract()?;
        println!("Metadata: {:?}", metadata);

        Ok(())
    })
}

/// Example 6: Error handling across the boundary
///
/// Shows how to handle Python exceptions in Rust.
fn example_error_handling() -> Result<()> {
    Python::with_gil(|py| {
        let code = r#"
def divide(a, b):
    if b == 0:
        raise ValueError("Division by zero!")
    return a / b
"#;

        let module = PyModule::from_code(py, code, "divide.py", "divide")?;
        let divide_fn = module.getattr("divide")?;

        // This succeeds
        match divide_fn.call1((10, 2))?.extract::<f64>() {
            Ok(result) => println!("10 / 2 = {}", result),
            Err(e) => println!("Error: {}", e),
        }

        // This raises an exception
        match divide_fn.call1((10, 0)) {
            Ok(_) => println!("Unexpectedly succeeded"),
            Err(e) => println!("Caught Python error: {}", e),
        }

        Ok(())
    })
}

/// Example 7: Using kwargs (keyword arguments)
///
/// Demonstrates passing keyword arguments to Python functions.
fn example_kwargs() -> Result<()> {
    Python::with_gil(|py| {
        let code = r#"
def configure(model_name="default", batch_size=32, normalize=True):
    return {
        "model": model_name,
        "batch_size": batch_size,
        "normalize": normalize
    }
"#;

        let module = PyModule::from_code(py, code, "config.py", "config")?;
        let configure_fn = module.getattr("configure")?;

        // Create kwargs
        let kwargs = PyDict::new(py);
        kwargs.set_item("model_name", "all-MiniLM-L6-v2")?;
        kwargs.set_item("batch_size", 64)?;
        kwargs.set_item("normalize", false)?;

        // Call with kwargs
        let result: HashMap<String, serde_json::Value> =
            configure_fn.call((), Some(kwargs))?.extract()?;

        println!("Configuration: {:?}", result);
        Ok(())
    })
}

/// Example 8: Caching Python objects in Rust
///
/// Shows how to store and reuse Python objects across calls.
struct CachedPythonModel {
    model: Py<PyAny>,
}

impl CachedPythonModel {
    fn new(model_name: &str) -> Result<Self> {
        Python::with_gil(|py| {
            let code = r#"
class Model:
    def __init__(self, name):
        self.name = name
        print(f"Model {name} loaded!")

    def predict(self, text):
        return f"Processed '{text}' with {self.name}"
"#;

            let module = PyModule::from_code(py, code, "model.py", "model")?;
            let model_class = module.getattr("Model")?;
            let model = model_class.call1((model_name,))?;

            Ok(Self {
                model: model.into(),
            })
        })
    }

    fn predict(&self, text: &str) -> Result<String> {
        Python::with_gil(|py| {
            let model = self.model.as_ref(py);
            let result: String = model.call_method1("predict", (text,))?.extract()?;
            Ok(result)
        })
    }
}

fn example_cached_model() -> Result<()> {
    // Model is loaded once
    let model = CachedPythonModel::new("my-model")?;

    // Multiple predictions reuse the same model
    for text in &["hello", "world", "rust"] {
        let result = model.predict(text)?;
        println!("{}", result);
    }

    Ok(())
}

/// Example 9: Batch processing with Python
///
/// Demonstrates efficient batch processing across the Rust-Python boundary.
fn example_batch_processing() -> Result<()> {
    Python::with_gil(|py| {
        let code = r#"
def embed_batch(texts, batch_size=32):
    # Simulate batch embedding
    return [[float(i) * 0.1 for i in range(3)] for _ in texts]
"#;

        let module = PyModule::from_code(py, code, "batch.py", "batch")?;
        let embed_fn = module.getattr("embed_batch")?;

        // Prepare batch of texts
        let texts = vec![
            "Document 1",
            "Document 2",
            "Document 3",
            "Document 4",
            "Document 5",
        ];

        // Process as batch
        let embeddings: Vec<Vec<f32>> = embed_fn.call1((texts,))?.extract()?;
        println!("Generated {} embeddings", embeddings.len());

        Ok(())
    })
}

/// Example 10: Real embedding integration (like in main.rs)
///
/// This mirrors the actual production code pattern.
fn example_production_embedding() -> Result<Vec<f32>> {
    let text = "Rust is a systems programming language";

    Python::with_gil(|py| {
        let embedder_code = r#"
from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self, model_name):
        self.model = SentenceTransformer(model_name)

    def embed(self, text):
        return self.model.encode([text])[0].tolist()

embedder = None

def get_embedder(model_name):
    global embedder
    if embedder is None:
        embedder = Embedder(model_name)
    return embedder
"#;

        let embedder_module =
            PyModule::from_code(py, embedder_code, "embedder.py", "embedder")?;

        let get_embedder = embedder_module.getattr("get_embedder")?;
        let embedder = get_embedder.call1(("sentence-transformers/all-MiniLM-L6-v2",))?;
        let embedding: Vec<f32> = embedder.call_method1("embed", (text,))?.extract()?;

        println!("Generated embedding with {} dimensions", embedding.len());
        Ok(embedding)
    })
    .context("Failed to generate embedding")
}

fn main() -> Result<()> {
    println!("=== PyO3 Integration Examples ===\n");

    println!("1. Basic Python call");
    example_basic_call()?;
    println!();

    println!("2. Inline Python code");
    example_inline_code()?;
    println!();

    println!("3. Python classes");
    example_python_class()?;
    println!();

    println!("4. Rust to Python conversion");
    example_rust_to_python()?;
    println!();

    println!("5. Python to Rust extraction");
    example_python_to_rust()?;
    println!();

    println!("6. Error handling");
    example_error_handling()?;
    println!();

    println!("7. Keyword arguments");
    example_kwargs()?;
    println!();

    println!("8. Cached Python model");
    example_cached_model()?;
    println!();

    println!("9. Batch processing");
    example_batch_processing()?;
    println!();

    println!("10. Production embedding (requires sentence-transformers)");
    match example_production_embedding() {
        Ok(embedding) => println!("Successfully generated embedding: {:?}...", &embedding[..5]),
        Err(e) => println!("Skipped (likely missing dependencies): {}", e),
    }

    Ok(())
}
