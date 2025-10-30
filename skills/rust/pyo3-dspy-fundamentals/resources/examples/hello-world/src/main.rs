//! Hello World - DSPy from Rust
//!
//! This example demonstrates the minimal setup required to call DSPy from Rust.
//! It initializes Python, imports DSPy, configures an OpenAI language model,
//! and makes a simple prediction using the `Predict` module.
//!
//! Prerequisites:
//! - Python 3.8+ with dspy-ai installed: pip install dspy-ai
//! - OPENAI_API_KEY environment variable set
//!
//! Run with: cargo run

use anyhow::Result;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};

/// Creates a Python dictionary with keyword arguments
macro_rules! kwargs {
    ($py:expr, $($key:expr => $val:expr),* $(,)?) => {{
        let dict = PyDict::new($py);
        $(
            dict.set_item($key, $val)?;
        )*
        dict
    }};
}

/// Creates a Python string
macro_rules! py_str {
    ($py:expr, $s:expr) => {
        PyString::new($py, $s)
    };
}

/// Main entry point - demonstrates minimal DSPy integration
fn main() -> Result<()> {
    // Initialize Python interpreter
    // This must be called before any Python operations
    println!("Initializing Python interpreter...");
    pyo3::prepare_freethreaded_python();

    // Acquire the Global Interpreter Lock (GIL)
    // All Python operations must happen within this closure
    Python::with_gil(|py| {
        // Import DSPy module
        println!("Importing DSPy...");
        let dspy = py.import("dspy")?;

        // Configure OpenAI as the language model
        // This reads OPENAI_API_KEY from environment variables
        println!("Configuring OpenAI language model...");
        let lm = dspy.call_method1(
            "OpenAI",
            (kwargs![py, "model" => "gpt-3.5-turbo"],),
        )?;

        // Set the language model as DSPy's default
        dspy.call_method1("configure", (kwargs![py, "lm" => lm],))?;

        // Create a simple signature: question -> answer
        // Signatures define the input and output fields for DSPy modules
        println!("Creating DSPy signature and predictor...");
        let signature = py_str!(py, "question -> answer");

        // Create a Predict module with our signature
        // Predict is the most basic DSPy module - it makes a single LM call
        let predict = dspy.call_method1("Predict", (signature,))?;

        // Make a prediction by calling the Predict module
        println!("Making prediction...\n");
        let question = "What is the capital of France?";
        let result = predict.call1((kwargs![py, "question" => question],))?;

        // Extract the answer field from the result
        // DSPy returns an object with named attributes for each output field
        let answer: String = result.getattr("answer")?.extract()?;

        // Display the result
        println!("Question: {}", question);
        println!("\nAnswer: {}", answer);

        Ok(())
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_python_initialization() {
        // Test that we can initialize Python without crashing
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let sys = py.import("sys").unwrap();
            let version: String = sys.getattr("version").unwrap().extract().unwrap();
            assert!(version.starts_with("3."));
        });
    }

    #[test]
    fn test_dspy_import() {
        // Test that DSPy can be imported (requires dspy-ai installed)
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let result = py.import("dspy");
            assert!(result.is_ok(), "DSPy not installed. Run: pip install dspy-ai");
        });
    }
}
