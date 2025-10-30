//! Tokio-AsyncIO Bridge Example
//!
//! Demonstrates integration between Rust's Tokio runtime and Python's asyncio event loop
//! using pyo3-asyncio. Shows how to call async DSPy predictions from Rust with proper
//! error handling, timeouts, and concurrent execution.
//!
//! # Architecture
//!
//! ```text
//! Tokio Runtime (Rust)
//!     ↓
//! pyo3_asyncio::tokio::into_future()
//!     ↓
//! Python asyncio event loop
//!     ↓
//! DSPy async predictions
//! ```

use anyhow::{Context, Result};
use futures::future::join_all;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};
use std::time::{Duration, Instant};

/// Initialize Python interpreter and DSPy
///
/// This sets up the Python environment with proper asyncio loop configuration
/// and imports necessary DSPy modules.
fn initialize_python() -> Result<()> {
    Python::with_gil(|py| {
        // Import asyncio and set up event loop policy for compatibility
        let asyncio = py.import("asyncio")?;

        // Set event loop policy to be compatible with pyo3-asyncio
        // This is critical for proper Tokio-asyncio integration
        let policy = asyncio.call_method0("get_event_loop_policy")?;
        asyncio.call_method1("set_event_loop_policy", (policy,))?;

        // Import DSPy
        py.import("dspy")?;

        println!("✓ Python interpreter initialized");
        println!("✓ asyncio event loop configured");
        println!("✓ DSPy imported successfully");

        Ok(())
    })
}

/// Configure DSPy with a language model
///
/// Sets up DSPy to use OpenAI's GPT-3.5-turbo. In production, you would
/// want to make this configurable and handle API keys securely.
fn configure_dspy(py: Python) -> Result<()> {
    let dspy = py.import("dspy")?;

    // Configure OpenAI model
    // Note: Requires OPENAI_API_KEY environment variable
    let lm = dspy
        .getattr("OpenAI")?
        .call1(("gpt-3.5-turbo",))?;

    dspy.call_method1("configure", (lm,))?;

    println!("✓ DSPy configured with OpenAI GPT-3.5-turbo");

    Ok(())
}

/// Create a DSPy ChainOfThought predictor
///
/// Returns a Python object that can be called asynchronously to generate predictions.
fn create_predictor(py: Python) -> Result<PyObject> {
    let dspy = py.import("dspy")?;

    // Create a simple signature: question -> answer
    let signature_code = r#"
class QASignature(dspy.Signature):
    """Answer questions with reasoning."""
    question = dspy.InputField()
    answer = dspy.OutputField()
"#;

    // Execute signature definition
    let locals = PyDict::new(py);
    locals.set_item("dspy", dspy)?;
    py.run(signature_code, None, Some(locals))?;

    let qa_signature = locals.get_item("QASignature").unwrap();

    // Create ChainOfThought predictor
    let chain_of_thought = dspy.getattr("ChainOfThought")?;
    let predictor = chain_of_thought.call1((qa_signature,))?;

    println!("✓ Created DSPy ChainOfThought predictor");

    Ok(predictor.into())
}

/// Make an async DSPy prediction from Rust
///
/// This is the core bridge function that converts a Python coroutine into a Rust Future.
/// It demonstrates proper GIL management and error handling.
///
/// # Arguments
///
/// * `predictor` - DSPy predictor object
/// * `question` - Question to ask
///
/// # Returns
///
/// The answer string from DSPy
///
/// # Errors
///
/// Returns error if Python call fails or prediction fails
async fn async_dspy_call(predictor: PyObject, question: &str) -> Result<String> {
    // Create a Python future from the DSPy prediction call
    let future = Python::with_gil(|py| -> Result<_> {
        // Get the predictor callable
        let predictor = predictor.as_ref(py);

        // Create kwargs dict with question
        let kwargs = PyDict::new(py);
        kwargs.set_item("question", question)?;

        // Call predictor (returns coroutine)
        let coroutine = predictor.call((), Some(kwargs))?;

        // Convert Python coroutine to Rust future
        // This is the key pyo3-asyncio integration point
        let future = pyo3_asyncio::tokio::into_future(coroutine)?;

        Ok(future)
    })?;

    // Await the future on Tokio runtime
    let result = future.await?;

    // Extract answer from result
    let answer = Python::with_gil(|py| -> Result<String> {
        let result = result.as_ref(py);
        let answer = result.getattr("answer")?.extract::<String>()?;
        Ok(answer)
    })?;

    Ok(answer)
}

/// Make an async DSPy prediction with timeout
///
/// Wraps async_dspy_call with a timeout to prevent hanging on slow API calls.
///
/// # Arguments
///
/// * `predictor` - DSPy predictor object
/// * `question` - Question to ask
/// * `timeout` - Maximum duration to wait
///
/// # Returns
///
/// The answer string or timeout error
async fn async_dspy_call_with_timeout(
    predictor: PyObject,
    question: &str,
    timeout: Duration,
) -> Result<String> {
    tokio::time::timeout(timeout, async_dspy_call(predictor, question))
        .await
        .context("DSPy call timed out")?
}

/// Example 1: Basic async DSPy call
///
/// Demonstrates the simplest case: single async prediction from Rust.
async fn example_basic_call() -> Result<()> {
    println!("\n=== Example 1: Basic Async Call ===\n");

    let predictor = Python::with_gil(|py| create_predictor(py))?;

    let question = "What is the capital of France?";
    println!("Question: {}", question);

    let start = Instant::now();
    let answer = async_dspy_call(predictor, question).await?;
    let elapsed = start.elapsed();

    println!("Answer: {}", answer);
    println!("Time: {:?}", elapsed);

    Ok(())
}

/// Example 2: Multiple concurrent predictions
///
/// Shows how to execute multiple DSPy predictions concurrently using Tokio,
/// demonstrating the performance benefits of async execution.
async fn example_concurrent_calls() -> Result<()> {
    println!("\n=== Example 2: Concurrent Calls ===\n");

    let predictor = Python::with_gil(|py| create_predictor(py))?;

    let questions = vec![
        "What is the capital of France?",
        "What is the largest planet in our solar system?",
        "Who wrote Romeo and Juliet?",
        "What is the speed of light?",
        "What is the tallest mountain on Earth?",
    ];

    println!("Running {} predictions concurrently...\n", questions.len());

    let start = Instant::now();

    // Create futures for all predictions
    let mut tasks = Vec::new();
    for (i, question) in questions.iter().enumerate() {
        let predictor_clone = predictor.clone();
        let question = question.to_string();

        let task = tokio::spawn(async move {
            let result = async_dspy_call(predictor_clone, &question).await;
            (i, question, result)
        });

        tasks.push(task);
    }

    // Wait for all predictions to complete
    let results = join_all(tasks).await;
    let elapsed = start.elapsed();

    // Display results
    for result in results {
        let (i, question, answer_result) = result?;
        match answer_result {
            Ok(answer) => {
                println!("Q{}: {}", i + 1, question);
                println!("A{}: {}\n", i + 1, answer);
            }
            Err(e) => {
                println!("Q{}: {} - ERROR: {}\n", i + 1, question, e);
            }
        }
    }

    println!("Total time: {:?}", elapsed);
    println!("Average time per question: {:?}", elapsed / questions.len() as u32);

    Ok(())
}

/// Example 3: Timeout handling
///
/// Demonstrates how to handle timeouts gracefully, preventing the application
/// from hanging on slow or stalled API calls.
async fn example_timeout_handling() -> Result<()> {
    println!("\n=== Example 3: Timeout Handling ===\n");

    let predictor = Python::with_gil(|py| create_predictor(py))?;

    let question = "Explain quantum computing in detail.";
    let timeout = Duration::from_secs(10);

    println!("Question: {}", question);
    println!("Timeout: {:?}\n", timeout);

    let start = Instant::now();

    match async_dspy_call_with_timeout(predictor, question, timeout).await {
        Ok(answer) => {
            println!("Answer: {}", answer);
            println!("Time: {:?}", start.elapsed());
        }
        Err(e) => {
            println!("Error: {}", e);
            println!("Time: {:?}", start.elapsed());
        }
    }

    Ok(())
}

/// Example 4: Error handling patterns
///
/// Shows different error scenarios and how to handle them:
/// - Invalid Python objects
/// - Python exceptions
/// - Missing attributes
/// - Type conversion errors
async fn example_error_handling() -> Result<()> {
    println!("\n=== Example 4: Error Handling ===\n");

    // Test 1: Handle Python exception gracefully
    println!("Test 1: Handling Python exception");
    let result = Python::with_gil(|py| -> Result<PyObject> {
        let code = r#"
def failing_function():
    raise ValueError("Intentional error for testing")
"#;
        let module = PyModule::from_code(py, code, "test.py", "test")?;
        let func = module.getattr("failing_function")?;

        // This will raise an exception
        func.call0().map(|obj| obj.into()).map_err(|e| e.into())
    });

    match result {
        Ok(_) => println!("  Unexpected success"),
        Err(e) => println!("  ✓ Caught error: {}", e),
    }

    // Test 2: Handle missing predictor gracefully
    println!("\nTest 2: Invalid predictor object");
    let invalid_predictor = Python::with_gil(|py| py.None().into());

    match async_dspy_call(invalid_predictor, "test question").await {
        Ok(_) => println!("  Unexpected success"),
        Err(e) => println!("  ✓ Caught error: {}", e),
    }

    // Test 3: Handle empty question
    println!("\nTest 3: Empty question");
    let predictor = Python::with_gil(|py| create_predictor(py))?;

    match async_dspy_call(predictor, "").await {
        Ok(answer) => println!("  Got answer: {}", answer),
        Err(e) => println!("  ✓ Caught error: {}", e),
    }

    Ok(())
}

/// Example 5: Performance comparison
///
/// Compares sequential vs concurrent execution to demonstrate the
/// performance benefits of async execution with proper runtime integration.
async fn example_performance_comparison() -> Result<()> {
    println!("\n=== Example 5: Performance Comparison ===\n");

    let predictor = Python::with_gil(|py| create_predictor(py))?;

    let questions = vec![
        "What is 2+2?",
        "What is the capital of Japan?",
        "What color is the sky?",
    ];

    // Sequential execution
    println!("Sequential execution:");
    let start = Instant::now();

    for (i, question) in questions.iter().enumerate() {
        let answer = async_dspy_call(predictor.clone(), question).await?;
        println!("  Q{}: {} -> {}", i + 1, question, answer);
    }

    let sequential_time = start.elapsed();
    println!("Sequential time: {:?}\n", sequential_time);

    // Concurrent execution
    println!("Concurrent execution:");
    let start = Instant::now();

    let mut tasks = Vec::new();
    for (i, question) in questions.iter().enumerate() {
        let predictor_clone = predictor.clone();
        let question = question.to_string();

        let task = tokio::spawn(async move {
            let answer = async_dspy_call(predictor_clone, &question).await;
            (i, question, answer)
        });

        tasks.push(task);
    }

    let results = join_all(tasks).await;
    for result in results {
        let (i, question, answer_result) = result?;
        if let Ok(answer) = answer_result {
            println!("  Q{}: {} -> {}", i + 1, question, answer);
        }
    }

    let concurrent_time = start.elapsed();
    println!("Concurrent time: {:?}\n", concurrent_time);

    // Performance analysis
    let speedup = sequential_time.as_secs_f64() / concurrent_time.as_secs_f64();
    println!("Performance:");
    println!("  Sequential: {:?}", sequential_time);
    println!("  Concurrent: {:?}", concurrent_time);
    println!("  Speedup: {:.2}x", speedup);

    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    println!("╔════════════════════════════════════════╗");
    println!("║  Tokio-AsyncIO Bridge Example         ║");
    println!("║  Rust + Python + DSPy Integration     ║");
    println!("╚════════════════════════════════════════╝\n");

    // Initialize Python and DSPy
    initialize_python()?;

    Python::with_gil(|py| configure_dspy(py))?;

    println!("\nRunning examples...\n");
    println!("════════════════════════════════════════");

    // Run all examples
    if let Err(e) = example_basic_call().await {
        eprintln!("Example 1 failed: {}", e);
    }

    if let Err(e) = example_concurrent_calls().await {
        eprintln!("Example 2 failed: {}", e);
    }

    if let Err(e) = example_timeout_handling().await {
        eprintln!("Example 3 failed: {}", e);
    }

    if let Err(e) = example_error_handling().await {
        eprintln!("Example 4 failed: {}", e);
    }

    if let Err(e) = example_performance_comparison().await {
        eprintln!("Example 5 failed: {}", e);
    }

    println!("\n════════════════════════════════════════");
    println!("\nAll examples completed!");
    println!("\nKey Takeaways:");
    println!("  • pyo3_asyncio::tokio::into_future() bridges Python coroutines to Rust futures");
    println!("  • Proper GIL management is critical in async contexts");
    println!("  • Concurrent execution provides significant performance benefits");
    println!("  • Always use timeouts for external API calls");
    println!("  • Error handling should cover Python exceptions and Rust errors");

    Ok(())
}
