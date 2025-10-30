use anyhow::{Context, Result};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};

/// Input structure for question answering
///
/// Contains the question and relevant context information that the model
/// should use to formulate an answer.
#[derive(Debug, Serialize)]
struct QAInput {
    question: String,
    context: String,
}

/// Output structure containing answer and reasoning
///
/// ChainOfThought produces both a final answer and the intermediate reasoning
/// steps that led to that answer, providing transparency and explainability.
#[derive(Debug, Deserialize)]
struct QAOutput {
    answer: String,
    reasoning: String,
}

/// Example query combining question and context
struct ExampleQuery {
    question: &'static str,
    context: &'static str,
}

/// Initialize DSPy with default configuration
///
/// This sets up the language model (defaults to GPT-3.5-turbo) and configures
/// DSPy settings. Requires OPENAI_API_KEY environment variable.
fn initialize_dspy(py: Python) -> Result<()> {
    let dspy = py.import_bound("dspy")
        .context("Failed to import dspy. Install with: pip install dspy-ai")?;

    // Configure with default OpenAI model
    // In production, you might want to specify model, temperature, max_tokens, etc.
    let lm = dspy
        .call_method1("OpenAI", ("gpt-3.5-turbo",))
        .context("Failed to create OpenAI LM")?;

    dspy.getattr("settings")?
        .call_method1("configure", (lm,))
        .context("Failed to configure DSPy settings")?;

    println!("DSPy initialized with GPT-3.5-turbo");
    Ok(())
}

/// Create a ChainOfThought module with the specified signature
///
/// ChainOfThought vs Predict:
/// - Predict: question, context -> answer (direct)
/// - ChainOfThought: question, context -> reasoning -> answer (explicit steps)
///
/// The signature defines input fields (question, context) and output fields
/// (answer, reasoning). ChainOfThought will prompt the LM to show its work.
fn create_cot_module(py: Python, signature: &str) -> Result<Py<PyAny>> {
    let dspy = py.import_bound("dspy")
        .context("Failed to import dspy")?;

    let cot = dspy
        .getattr("ChainOfThought")
        .context("Failed to get ChainOfThought class")?
        .call1((signature,))
        .context("Failed to create ChainOfThought module")?;

    println!("Created ChainOfThought with signature: {}", signature);
    Ok(cot.unbind())
}

/// Execute a question-answering query using ChainOfThought
///
/// This function:
/// 1. Serializes the Rust input to a Python dict
/// 2. Calls the ChainOfThought module
/// 3. Extracts the prediction object
/// 4. Deserializes answer and reasoning back to Rust
fn query_with_cot(
    py: Python,
    cot_module: &Py<PyAny>,
    input: &QAInput,
) -> Result<QAOutput> {
    // Convert Rust struct to Python dict
    let kwargs = PyDict::new_bound(py);
    kwargs.set_item("question", &input.question)?;
    kwargs.set_item("context", &input.context)?;

    // Call ChainOfThought module
    // This triggers the LM to:
    // 1. Generate reasoning steps
    // 2. Generate final answer based on reasoning
    let prediction = cot_module
        .bind(py)
        .call((), Some(&kwargs))
        .context("ChainOfThought prediction failed")?;

    // Extract answer and reasoning from prediction object
    let answer: String = prediction
        .getattr("answer")
        .and_then(|a| a.extract())
        .context("Failed to extract answer")?;

    let reasoning: String = prediction
        .getattr("reasoning")
        .and_then(|r| r.extract())
        .context("Failed to extract reasoning")?;

    Ok(QAOutput { answer, reasoning })
}

/// Display a query result in a formatted way
fn display_result(query_num: usize, input: &QAInput, output: &QAOutput) {
    println!("\nQuery #{}:", query_num);
    println!("  Question: {}", input.question);
    println!("  Context: {}", input.context);
    println!("\n  Answer: {}", output.answer);
    println!("  Reasoning: {}", output.reasoning);
    println!("  {}", "-".repeat(80));
}

fn main() -> Result<()> {
    println!("Question Answering with DSPy ChainOfThought");
    println!("{}", "=".repeat(80));

    // Example queries demonstrating different question types
    let examples = vec![
        ExampleQuery {
            question: "What is the capital of France?",
            context: "France is a country in Western Europe. Paris is its capital and largest city, known for the Eiffel Tower and the Louvre Museum.",
        },
        ExampleQuery {
            question: "What is photosynthesis?",
            context: "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce oxygen and glucose. It occurs primarily in the chloroplasts.",
        },
        ExampleQuery {
            question: "Who wrote Romeo and Juliet?",
            context: "Romeo and Juliet is a tragedy written by William Shakespeare early in his career about two young star-crossed lovers. It was first performed around 1594-1596.",
        },
        ExampleQuery {
            question: "What causes seasons on Earth?",
            context: "Seasons are caused by Earth's tilted axis as it orbits the Sun. The tilt causes different parts of Earth to receive varying amounts of sunlight throughout the year.",
        },
    ];

    Python::with_gil(|py| {
        // Initialize DSPy configuration
        initialize_dspy(py)?;

        // Create ChainOfThought module
        // Signature format: "input_field1, input_field2 -> output_field1, output_field2"
        //
        // Key point: Including "reasoning" in the output tells ChainOfThought to
        // explicitly generate and expose the reasoning process.
        let signature = "question, context -> answer, reasoning";
        let cot_module = create_cot_module(py, signature)?;

        println!("\nProcessing {} queries...\n", examples.len());

        // Process each example query
        for (i, example) in examples.iter().enumerate() {
            let input = QAInput {
                question: example.question.to_string(),
                context: example.context.to_string(),
            };

            // Execute query with error handling
            match query_with_cot(py, &cot_module, &input) {
                Ok(output) => {
                    display_result(i + 1, &input, &output);
                }
                Err(e) => {
                    eprintln!("Error processing query #{}: {}", i + 1, e);
                    continue;
                }
            }
        }

        println!("\nAll queries completed successfully!");
        Ok(())
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_qa_input_serialization() {
        let input = QAInput {
            question: "What is Rust?".to_string(),
            context: "Rust is a systems programming language.".to_string(),
        };

        let json = serde_json::to_string(&input).unwrap();
        assert!(json.contains("What is Rust?"));
        assert!(json.contains("systems programming"));
    }

    #[test]
    fn test_qa_output_deserialization() {
        let json = r#"{
            "answer": "A programming language",
            "reasoning": "Based on the context provided"
        }"#;

        let output: QAOutput = serde_json::from_str(json).unwrap();
        assert_eq!(output.answer, "A programming language");
        assert_eq!(output.reasoning, "Based on the context provided");
    }
}
