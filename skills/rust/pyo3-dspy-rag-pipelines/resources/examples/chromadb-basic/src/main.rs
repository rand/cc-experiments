use anyhow::{Context, Result};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde_json::Value;
use std::iter;

/// Sample documents for the vector database
fn sample_documents() -> Vec<(&'static str, &'static str, serde_json::Value)> {
    vec![
        (
            "doc1",
            "Rust provides the Result<T, E> type for recoverable errors. This allows functions to return either a success value or an error value.",
            serde_json::json!({"topic": "error_handling", "difficulty": "intermediate"})
        ),
        (
            "doc2",
            "The ? operator provides a concise way to propagate errors up the call stack. It works with Result and Option types.",
            serde_json::json!({"topic": "error_handling", "difficulty": "intermediate"})
        ),
        (
            "doc3",
            "For unrecoverable errors, use the panic! macro. This will immediately terminate the program with an error message.",
            serde_json::json!({"topic": "error_handling", "difficulty": "beginner"})
        ),
        (
            "doc4",
            "Rust's ownership system prevents data races at compile time. Each value has a single owner, and when the owner goes out of scope, the value is dropped.",
            serde_json::json!({"topic": "ownership", "difficulty": "intermediate"})
        ),
        (
            "doc5",
            "Borrowing allows you to reference data without taking ownership. References are immutable by default, but you can create mutable references with &mut.",
            serde_json::json!({"topic": "ownership", "difficulty": "intermediate"})
        ),
    ]
}

/// Initialize ChromaDB client and create a collection with sample documents
fn setup_chromadb(py: Python<'_>) -> Result<&PyAny> {
    // Import ChromaDB
    let chromadb = py
        .import("chromadb")
        .context("Failed to import chromadb. Make sure it's installed: pip install chromadb")?;

    // Create client (uses local storage by default)
    let client = chromadb
        .call_method0("Client")
        .context("Failed to create ChromaDB client")?;

    // Set up OpenAI embedding function
    let embedding_functions = py
        .import("chromadb.utils.embedding_functions")
        .context("Failed to import chromadb embedding functions")?;

    let openai_ef = embedding_functions
        .call_method1("OpenAIEmbeddingFunction", ("text-embedding-ada-002",))
        .context("Failed to create OpenAI embedding function. Make sure OPENAI_API_KEY is set")?;

    // Create or get collection
    let collection_name = "rust_docs";
    let kwargs = PyDict::new(py);
    kwargs.set_item("name", collection_name)?;
    kwargs.set_item("embedding_function", openai_ef)?;

    let collection = client
        .call_method("get_or_create_collection", (), Some(kwargs))
        .context("Failed to create collection")?;

    // Prepare documents
    let docs = sample_documents();
    let ids: Vec<&str> = docs.iter().map(|(id, _, _)| *id).collect();
    let documents: Vec<&str> = docs.iter().map(|(_, doc, _)| *doc).collect();
    let metadatas: Vec<Value> = docs.iter().map(|(_, _, meta)| meta.clone()).collect();

    // Convert metadata to Python objects
    let py_metadatas: Vec<_> = metadatas.iter().map(|m| {
        let dict = PyDict::new(py);
        if let Value::Object(obj) = m {
            for (key, value) in obj {
                if let Value::String(s) = value {
                    dict.set_item(key, s).unwrap();
                }
            }
        }
        dict
    }).collect();

    // Add documents to collection
    let add_kwargs = PyDict::new(py);
    add_kwargs.set_item("ids", ids)?;
    add_kwargs.set_item("documents", documents)?;
    add_kwargs.set_item("metadatas", py_metadatas)?;

    collection
        .call_method("add", (), Some(add_kwargs))
        .context("Failed to add documents to collection")?;

    println!("Collection '{}' created with {} documents", collection_name, docs.len());

    Ok(collection)
}

/// Query ChromaDB collection with similarity search
fn query_chromadb(py: Python, collection: &PyAny, query: &str, n_results: usize) -> Result<()> {
    println!("\nQuerying: \"{}\"", query);

    // Execute query
    let kwargs = PyDict::new(py);
    kwargs.set_item("query_texts", vec![query])?;
    kwargs.set_item("n_results", n_results)?;

    let results = collection
        .call_method("query", (), Some(kwargs))
        .context("Failed to query collection")?;

    // Extract results
    let documents = results
        .get_item("documents")
        .context("Failed to get documents from results")?
        .downcast::<PyList>()
        .map_err(|e| anyhow::anyhow!("Documents is not a list: {}", e))?
        .get_item(0)?
        .downcast::<PyList>()
        .map_err(|e| anyhow::anyhow!("Documents[0] is not a list: {}", e))?;

    let metadatas = results
        .get_item("metadatas")
        .context("Failed to get metadatas from results")?
        .downcast::<PyList>()
        .map_err(|e| anyhow::anyhow!("Metadatas is not a list: {}", e))?
        .get_item(0)?
        .downcast::<PyList>()
        .map_err(|e| anyhow::anyhow!("Metadatas[0] is not a list: {}", e))?;

    let distances = results
        .get_item("distances")
        .context("Failed to get distances from results")?
        .downcast::<PyList>()
        .map_err(|e| anyhow::anyhow!("Distances is not a list: {}", e))?
        .get_item(0)?
        .downcast::<PyList>()
        .map_err(|e| anyhow::anyhow!("Distances[0] is not a list: {}", e))?;

    // Display results
    println!("\nTop {} Results:", n_results);
    println!("{}", iter::repeat('-').take(50).collect::<String>());

    for i in 0..documents.len() {
        let doc = documents.get_item(i)?;
        let metadata = metadatas.get_item(i)?;
        let distance = distances.get_item(i)?;

        // Convert distance to similarity score (1 - normalized_distance)
        let dist_value: f64 = distance.extract()?;
        let similarity = 1.0 - (dist_value / 2.0); // Normalize L2 distance to 0-1 range

        println!("\nResult {} (Score: {:.2}):", i + 1, similarity);
        println!("Document: {}", doc.extract::<String>()?);

        // Extract metadata as dict
        let meta_dict = metadata.downcast::<PyDict>()
            .map_err(|e| anyhow::anyhow!("Metadata is not a dict: {}", e))?;
        let mut meta_json = serde_json::Map::new();
        for (key, value) in meta_dict.iter() {
            let k = key.extract::<String>()?;
            let v = value.extract::<String>()?;
            meta_json.insert(k, Value::String(v));
        }
        println!("Metadata: {}", serde_json::to_string_pretty(&meta_json)?);
    }

    Ok(())
}

/// Create a DSPy Retrieve module that wraps ChromaDB
fn create_dspy_retriever<'py>(py: Python<'py>, collection: &'py PyAny, k: usize) -> Result<&'py PyAny> {
    // Import DSPy
    let _dspy = py
        .import("dspy")
        .context("Failed to import dspy. Make sure it's installed: pip install dspy-ai")?;

    // Create a custom retriever function that uses ChromaDB
    let retriever_code = format!(
        r#"
def chromadb_retriever(query, k={}):
    results = collection.query(query_texts=[query], n_results=k)

    # Format results for DSPy
    formatted = []
    for i, doc in enumerate(results['documents'][0]):
        formatted.append({{
            'text': doc,
            'score': 1.0 - (results['distances'][0][i] / 2.0),  # Normalize to 0-1
            'metadata': results['metadatas'][0][i]
        }})

    return formatted
"#,
        k
    );

    // Execute the retriever function definition
    let locals = PyDict::new(py);
    locals.set_item("collection", collection)?;
    py.run(&retriever_code, None, Some(locals))
        .context("Failed to create retriever function")?;

    let retriever_fn = locals
        .get_item("chromadb_retriever")
        .context("Failed to get retriever function")?
        .expect("chromadb_retriever not found");

    // Create DSPy Retrieve module with custom retriever
    let kwargs = PyDict::new(py);
    kwargs.set_item("k", k)?;

    // Note: DSPy's Retrieve module expects a retriever function
    // For this basic example, we'll demonstrate the pattern
    // In practice, you'd subclass dspy.Retrieve or use dspy.retrieve

    Ok(retriever_fn)
}

/// Demonstrate DSPy integration with ChromaDB
fn test_dspy_integration(_py: Python, retriever: &PyAny, query: &str) -> Result<()> {
    println!("\nTesting DSPy Integration");
    println!("{}", iter::repeat('-').take(50).collect::<String>());

    // Call the retriever function
    let results = retriever
        .call1((query,))
        .context("Failed to call retriever")?;

    let results_list = results
        .downcast::<PyList>()
        .map_err(|e| anyhow::anyhow!("Results is not a list: {}", e))?;

    println!("\nDSPy Retrieve Results:");
    for (i, result) in results_list.iter().enumerate() {
        let result_dict = result.downcast::<PyDict>()
            .map_err(|e| anyhow::anyhow!("Result is not a dict: {}", e))?;
        let text = result_dict.get_item("text")?.unwrap().extract::<String>()?;
        let score = result_dict.get_item("score")?.unwrap().extract::<f64>()?;

        println!("{}. [Score: {:.2}] {}", i + 1, score,
                 if text.len() > 80 {
                     format!("{}...", &text[..77])
                 } else {
                     text
                 });
    }

    Ok(())
}

fn main() -> Result<()> {
    println!("ChromaDB Basic Example");
    println!("{}", iter::repeat('=').take(50).collect::<String>());
    println!();

    Python::with_gil(|py| -> Result<()> {
        // Step 1: Setup ChromaDB with sample documents
        println!("Setting up ChromaDB with sample documents...");
        let collection = setup_chromadb(py)?;

        // Step 2: Query ChromaDB with similarity search
        println!();
        let query = "How do I handle errors in Rust?";
        query_chromadb(py, &collection, query, 3)?;

        // Step 3: Create DSPy retriever
        println!();
        println!("Creating DSPy retriever...");
        let retriever = create_dspy_retriever(py, &collection, 3)?;

        // Step 4: Test DSPy integration
        test_dspy_integration(py, &retriever, query)?;

        println!();
        println!("Example completed successfully!");

        Ok(())
    })?;

    Ok(())
}
