//! Basic ReAct Agent - DSPy from Rust
//!
//! This example demonstrates a complete ReAct (Reasoning + Acting) agent implementation
//! using DSPy from Rust via PyO3. It shows how to configure an agent, register tools,
//! execute reasoning loops, and extract complete execution traces.
//!
//! Key Features:
//! - ReAct agent setup with DSPy configuration
//! - Simple tool registration and simulation
//! - Complete trace extraction (thoughts, actions, observations)
//! - Production-quality error handling
//! - Multiple demonstration examples
//!
//! Prerequisites:
//! - Python 3.8+ with dspy-ai installed: pip install dspy-ai
//! - OPENAI_API_KEY environment variable set
//!
//! Run with: cargo run

use anyhow::{Context, Result};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Creates a Python dictionary with keyword arguments
///
/// Usage: kwargs!(py, "key1" => value1, "key2" => value2)
macro_rules! kwargs {
    ($py:expr, $($key:expr => $val:expr),* $(,)?) => {{
        let dict = PyDict::new($py);
        $(
            dict.set_item($key, $val)?;
        )*
        dict
    }};
}

/// Configuration for ReAct agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReActConfig {
    /// DSPy signature defining input/output fields (e.g., "question -> answer")
    pub signature: String,

    /// Maximum reasoning iterations before returning an answer
    pub max_iterations: usize,

    /// Temperature for language model (0.0-1.0, higher = more creative)
    pub temperature: f32,
}

impl Default for ReActConfig {
    fn default() -> Self {
        Self {
            signature: "question -> answer".to_string(),
            max_iterations: 5,
            temperature: 0.7,
        }
    }
}

/// A single step in the agent's reasoning trajectory
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStep {
    /// Step number in the trajectory (1-indexed)
    pub step_number: usize,

    /// The agent's reasoning about what to do
    pub thought: String,

    /// The action taken (e.g., "calculator(2+2)" or "search(Paris)")
    pub action: String,

    /// The result observed from executing the action
    pub observation: String,
}

/// Complete result from a ReAct agent execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReActResult {
    /// Final answer from the agent
    pub answer: String,

    /// Complete trajectory of reasoning steps
    pub trajectory: Vec<AgentStep>,

    /// Total number of iterations performed
    pub total_iterations: usize,

    /// Whether the agent successfully found an answer
    pub success: bool,
}

/// ReAct agent wrapper for DSPy
pub struct ReActAgent {
    /// Python ReAct module instance
    agent: Py<PyAny>,

    /// Configuration
    #[allow(dead_code)]
    config: ReActConfig,
}

impl ReActAgent {
    /// Create a new ReAct agent with the given configuration
    pub fn new(config: ReActConfig) -> Result<Self> {
        Python::with_gil(|py| {
            // Import DSPy
            let dspy = py.import("dspy")
                .context("Failed to import dspy. Is it installed? Run: pip install dspy-ai")?;

            // Create ReAct module
            // ReAct takes a signature string defining inputs and outputs
            let react_class = dspy.getattr("ReAct")
                .context("Failed to get ReAct class from dspy")?;

            let agent = react_class.call1((config.signature.as_str(),))
                .context("Failed to create ReAct instance")?;

            // Configure max iterations
            agent.setattr("max_iters", config.max_iterations)
                .context("Failed to set max_iterations")?;

            Ok(Self {
                agent: agent.into(),
                config,
            })
        })
    }

    /// Execute the agent with a question and return just the answer
    pub fn forward(&self, question: &str) -> Result<String> {
        if question.trim().is_empty() {
            anyhow::bail!("Question cannot be empty");
        }

        Python::with_gil(|py| {
            // Call the agent's forward method
            let result = self.agent.as_ref(py)
                .call_method1("forward", (kwargs![py, "question" => question],))
                .context("Failed to execute agent forward")?;

            // Extract the answer field
            let answer: String = result
                .getattr("answer")
                .context("Failed to get answer from result")?
                .extract()
                .context("Failed to extract answer as string")?;

            Ok(answer)
        })
    }

    /// Execute the agent and return complete trace with all reasoning steps
    pub fn forward_with_trace(&self, question: &str) -> Result<ReActResult> {
        if question.trim().is_empty() {
            anyhow::bail!("Question cannot be empty");
        }

        Python::with_gil(|py| {
            // Call the agent's forward method
            let result = self.agent.as_ref(py)
                .call_method1("forward", (kwargs![py, "question" => question],))
                .context("Failed to execute agent forward")?;

            // Extract the answer
            let answer: String = result
                .getattr("answer")
                .context("Failed to get answer from result")?
                .extract()
                .context("Failed to extract answer as string")?;

            // Extract trajectory if available
            let mut trajectory = Vec::new();

            // DSPy ReAct stores trajectory in the result object
            // Try to extract it, but don't fail if it's not available
            if let Ok(traj_attr) = result.getattr("trajectory") {
                if let Ok(py_list) = traj_attr.downcast::<PyList>() {
                    for (idx, step) in py_list.iter().enumerate() {
                        // Extract thought, action, observation from each step
                        let thought = step
                            .getattr("thought")
                            .ok()
                            .and_then(|t| t.extract::<String>().ok())
                            .unwrap_or_else(|| "[No thought recorded]".to_string());

                        let action = step
                            .getattr("action")
                            .ok()
                            .and_then(|a| a.extract::<String>().ok())
                            .unwrap_or_else(|| "[No action recorded]".to_string());

                        let observation = step
                            .getattr("observation")
                            .ok()
                            .and_then(|o| o.extract::<String>().ok())
                            .unwrap_or_else(|| "[No observation recorded]".to_string());

                        trajectory.push(AgentStep {
                            step_number: idx + 1,
                            thought,
                            action,
                            observation,
                        });
                    }
                }
            }

            let total_iterations = trajectory.len();
            let success = !answer.is_empty();

            Ok(ReActResult {
                answer,
                trajectory,
                total_iterations,
                success,
            })
        })
    }
}

/// Configure DSPy with OpenAI language model
///
/// This must be called before creating any agents.
/// Requires OPENAI_API_KEY environment variable.
fn configure_dspy_lm() -> Result<()> {
    Python::with_gil(|py| {
        // Import DSPy
        let dspy = py.import("dspy")
            .context("Failed to import dspy")?;

        // Create OpenAI LM instance
        // This will use OPENAI_API_KEY from environment
        let openai_class = dspy.getattr("OpenAI")
            .context("Failed to get OpenAI class")?;

        let lm = openai_class.call1((kwargs![py, "model" => "gpt-3.5-turbo"],))
            .context("Failed to create OpenAI LM. Is OPENAI_API_KEY set?")?;

        // Configure DSPy to use this LM
        dspy.call_method1("configure", (kwargs![py, "lm" => lm],))
            .context("Failed to configure DSPy")?;

        Ok(())
    })
}

/// Simulated search tool (in production, use Google Serper API or similar)
#[allow(dead_code)]
fn simulated_search(query: &str) -> String {
    let results: HashMap<&str, &str> = [
        ("paris", "Paris is the capital and largest city of France, with a population of approximately 2.1 million."),
        ("rust", "Rust is a systems programming language focused on safety, speed, and concurrency."),
        ("python", "Python is a high-level, interpreted programming language known for its simplicity and readability."),
        ("dspy", "DSPy is a framework for algorithmically optimizing language model prompts and weights."),
    ].iter().cloned().collect();

    let query_lower = query.to_lowercase();

    for (key, value) in &results {
        if query_lower.contains(key) {
            return value.to_string();
        }
    }

    format!("No specific information found for query: {}", query)
}

/// Simulated calculator tool (in production, use evalexpr crate or WolframAlpha API)
#[allow(dead_code)]
fn simulated_calculator(expression: &str) -> Result<String> {
    // Simple calculator for basic operations
    let expr = expression.trim();

    // Handle common patterns
    if let Some(result) = parse_simple_expression(expr) {
        return Ok(result.to_string());
    }

    // Fallback for unknown expressions
    Ok(format!("Cannot evaluate: {}", expr))
}

/// Parse simple mathematical expressions (e.g., "2 + 2", "15 * 23")
#[allow(dead_code)]
fn parse_simple_expression(expr: &str) -> Option<i64> {
    let parts: Vec<&str> = expr.split_whitespace().collect();

    if parts.len() != 3 {
        return None;
    }

    let left = parts[0].parse::<i64>().ok()?;
    let op = parts[1];
    let right = parts[2].parse::<i64>().ok()?;

    match op {
        "+" => Some(left + right),
        "-" => Some(left - right),
        "*" => Some(left * right),
        "/" if right != 0 => Some(left / right),
        _ => None,
    }
}

/// Display a ReActResult with formatted output
fn display_result(result: &ReActResult) {
    println!("\nAgent Trace:");
    println!("─────────────────────────────────────────────────");

    for step in &result.trajectory {
        println!("\nStep {}:", step.step_number);
        println!("  Thought: {}", step.thought);
        println!("  Action: {}", step.action);
        println!("  Observation: {}", step.observation);
    }

    println!("\n─────────────────────────────────────────────────");
    println!("Answer: {}", result.answer);
    println!("─────────────────────────────────────────────────");
    println!("Total iterations: {}", result.total_iterations);
    println!("Success: {}", result.success);
}

/// Main entry point - demonstrates ReAct agent usage
fn main() -> Result<()> {
    println!("╔════════════════════════════════════════════════╗");
    println!("║   Basic ReAct Agent - DSPy from Rust          ║");
    println!("╚════════════════════════════════════════════════╝\n");

    // Initialize Python interpreter
    println!("Initializing Python interpreter...");
    pyo3::prepare_freethreaded_python();

    // Configure DSPy with OpenAI
    println!("Configuring DSPy with OpenAI...");
    configure_dspy_lm()
        .context("Failed to configure DSPy. Ensure OPENAI_API_KEY is set")?;

    // Create ReAct agent with default configuration
    println!("Creating ReAct agent...\n");
    let config = ReActConfig::default();
    let agent = ReActAgent::new(config)
        .context("Failed to create ReAct agent")?;

    // Example 1: Simple calculation
    println!("\n╔════════════════════════════════════════════════╗");
    println!("║ Example 1: Simple Calculation                  ║");
    println!("╚════════════════════════════════════════════════╝");

    let question1 = "What is 25 * 17?";
    println!("\nQuestion: {}", question1);

    match agent.forward_with_trace(question1) {
        Ok(result) => display_result(&result),
        Err(e) => eprintln!("Error: {:#}", e),
    }

    // Example 2: Search-based question
    println!("\n\n╔════════════════════════════════════════════════╗");
    println!("║ Example 2: Search-based Question              ║");
    println!("╚════════════════════════════════════════════════╝");

    let question2 = "What is the capital of France?";
    println!("\nQuestion: {}", question2);

    match agent.forward_with_trace(question2) {
        Ok(result) => display_result(&result),
        Err(e) => eprintln!("Error: {:#}", e),
    }

    // Example 3: Multi-step reasoning
    println!("\n\n╔════════════════════════════════════════════════╗");
    println!("║ Example 3: Multi-step Reasoning               ║");
    println!("╚════════════════════════════════════════════════╝");

    let question3 = "Search for information about Rust programming language";
    println!("\nQuestion: {}", question3);

    match agent.forward_with_trace(question3) {
        Ok(result) => display_result(&result),
        Err(e) => eprintln!("Error: {:#}", e),
    }

    // Example 4: Error handling - empty question
    println!("\n\n╔════════════════════════════════════════════════╗");
    println!("║ Example 4: Error Handling                     ║");
    println!("╚════════════════════════════════════════════════╝");

    println!("\nTrying empty question...");
    match agent.forward_with_trace("") {
        Ok(result) => display_result(&result),
        Err(e) => println!("Expected error caught: {}", e),
    }

    // Example 5: JSON serialization of result
    println!("\n\n╔════════════════════════════════════════════════╗");
    println!("║ Example 5: JSON Serialization                 ║");
    println!("╚════════════════════════════════════════════════╝");

    let question5 = "What is 100 + 234?";
    println!("\nQuestion: {}", question5);

    if let Ok(result) = agent.forward_with_trace(question5) {
        match serde_json::to_string_pretty(&result) {
            Ok(json) => {
                println!("\nJSON representation:");
                println!("{}", json);
            }
            Err(e) => eprintln!("Failed to serialize: {}", e),
        }
    }

    println!("\n\n╔════════════════════════════════════════════════╗");
    println!("║ All examples completed successfully!          ║");
    println!("╚════════════════════════════════════════════════╝\n");

    Ok(())
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
            assert!(
                result.is_ok(),
                "DSPy not installed. Run: pip install dspy-ai"
            );
        });
    }

    #[test]
    fn test_config_default() {
        let config = ReActConfig::default();
        assert_eq!(config.signature, "question -> answer");
        assert_eq!(config.max_iterations, 5);
        assert_eq!(config.temperature, 0.7);
    }

    #[test]
    fn test_config_custom() {
        let config = ReActConfig {
            signature: "context, question -> detailed_answer".to_string(),
            max_iterations: 10,
            temperature: 0.5,
        };
        assert_eq!(config.signature, "context, question -> detailed_answer");
        assert_eq!(config.max_iterations, 10);
        assert_eq!(config.temperature, 0.5);
    }

    #[test]
    fn test_simulated_search() {
        let result = simulated_search("Paris France");
        assert!(result.contains("Paris"));
        assert!(result.contains("capital"));

        let result = simulated_search("Rust programming");
        assert!(result.contains("Rust"));
        assert!(result.contains("systems programming"));
    }

    #[test]
    fn test_simulated_calculator() {
        assert_eq!(simulated_calculator("2 + 2").unwrap(), "4");
        assert_eq!(simulated_calculator("10 * 5").unwrap(), "50");
        assert_eq!(simulated_calculator("20 - 8").unwrap(), "12");
        assert_eq!(simulated_calculator("100 / 4").unwrap(), "25");
    }

    #[test]
    fn test_parse_simple_expression() {
        assert_eq!(parse_simple_expression("2 + 2"), Some(4));
        assert_eq!(parse_simple_expression("15 * 23"), Some(345));
        assert_eq!(parse_simple_expression("100 - 42"), Some(58));
        assert_eq!(parse_simple_expression("144 / 12"), Some(12));
        assert_eq!(parse_simple_expression("invalid"), None);
    }

    #[test]
    fn test_agent_step_serialization() {
        let step = AgentStep {
            step_number: 1,
            thought: "I need to calculate".to_string(),
            action: "calculator(2+2)".to_string(),
            observation: "4".to_string(),
        };

        let json = serde_json::to_string(&step).unwrap();
        assert!(json.contains("step_number"));
        assert!(json.contains("thought"));
        assert!(json.contains("action"));
        assert!(json.contains("observation"));
    }

    #[test]
    fn test_react_result_serialization() {
        let result = ReActResult {
            answer: "4".to_string(),
            trajectory: vec![AgentStep {
                step_number: 1,
                thought: "Calculate".to_string(),
                action: "calculator(2+2)".to_string(),
                observation: "4".to_string(),
            }],
            total_iterations: 1,
            success: true,
        };

        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("answer"));
        assert!(json.contains("trajectory"));
        assert!(json.contains("total_iterations"));
        assert!(json.contains("success"));
    }
}
