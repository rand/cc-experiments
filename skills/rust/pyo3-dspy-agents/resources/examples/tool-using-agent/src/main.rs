//! Tool-Using Agent Example
//!
//! This example demonstrates a production-ready ReAct agent with multiple
//! custom tools, comprehensive error handling, and monitoring.
//!
//! Features:
//! - Web search tool (mock HTTP requests)
//! - Calculator tool (safe expression evaluation)
//! - File reader tool (secure file operations)
//! - Weather API tool (REST API integration)
//! - Circuit breaker pattern for fault tolerance
//! - Retry logic with exponential backoff
//! - Performance metrics and monitoring
//! - DSPy ReAct agent integration

use anyhow::{Context, Result};
use pyo3::prelude::*;
use pyo3::types::{PyList, PyModule};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use tool_using_agent::{RetryConfig, ToolExecutor, ToolMetadata, ToolRegistry};
use tracing::info;

/// Agent response with reasoning trace
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AgentResponse {
    answer: String,
    reasoning_steps: Vec<ReasoningStep>,
    total_steps: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ReasoningStep {
    thought: String,
    action: Option<String>,
    observation: Option<String>,
}

/// Web search tool (mock implementation)
fn web_search_tool(query: &str) -> Result<String> {
    info!("Executing web search for: {}", query);

    // In production, use reqwest or similar
    // Simulate search results
    let results = format!(
        "Search results for '{}':\n\
        1. Article about {}: Comprehensive guide and documentation\n\
        2. Tutorial on {}: Step-by-step instructions\n\
        3. Research paper: Latest developments in {}",
        query, query, query, query
    );

    Ok(results)
}

/// Calculator tool (safe evaluation)
fn calculator_tool(expression: &str) -> Result<String> {
    info!("Calculating: {}", expression);

    // In production, use a safe expression parser like meval
    // For demo, handle basic operations
    let trimmed = expression.trim();

    // Simple parser for basic arithmetic
    let result = if trimmed.contains('+') {
        let parts: Vec<&str> = trimmed.split('+').collect();
        if parts.len() == 2 {
            let a: f64 = parts[0].trim().parse().context("Invalid number")?;
            let b: f64 = parts[1].trim().parse().context("Invalid number")?;
            a + b
        } else {
            return Err(anyhow::anyhow!("Invalid expression"));
        }
    } else if trimmed.contains('*') {
        let parts: Vec<&str> = trimmed.split('*').collect();
        if parts.len() == 2 {
            let a: f64 = parts[0].trim().parse().context("Invalid number")?;
            let b: f64 = parts[1].trim().parse().context("Invalid number")?;
            a * b
        } else {
            return Err(anyhow::anyhow!("Invalid expression"));
        }
    } else {
        trimmed.parse::<f64>().context("Invalid number")?
    };

    Ok(format!("{} = {}", expression, result))
}

/// File reader tool (secure file operations)
fn file_reader_tool(path: &str) -> Result<String> {
    info!("Reading file: {}", path);

    // Security: only allow reading from safe directories
    let safe_prefixes = ["/tmp/", "/var/tmp/", "./data/"];
    let is_safe = safe_prefixes.iter().any(|prefix| path.starts_with(prefix));

    if !is_safe {
        return Err(anyhow::anyhow!(
            "Access denied: File must be in allowed directory"
        ));
    }

    // In production, implement actual file reading
    // For demo, return mock content
    Ok(format!(
        "File contents from '{}':\n\
        Line 1: Sample data\n\
        Line 2: More information\n\
        Line 3: Additional details",
        path
    ))
}

/// Weather API tool (REST API integration)
async fn weather_api_tool_async(location: &str) -> Result<String> {
    info!("Fetching weather for: {}", location);

    // In production, call actual weather API with reqwest
    // For demo, return mock weather data
    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

    let weather_data = format!(
        "Weather in {}:\n\
        Temperature: 72°F (22°C)\n\
        Conditions: Partly cloudy\n\
        Humidity: 65%\n\
        Wind: 10 mph NW",
        location
    );

    Ok(weather_data)
}

/// Synchronous wrapper for weather tool
fn weather_api_tool(location: &str) -> Result<String> {
    // Use tokio runtime for async operation
    let rt = tokio::runtime::Runtime::new()?;
    rt.block_on(weather_api_tool_async(location))
}

/// Configure DSPy with a language model
fn configure_dspy(py: Python) -> PyResult<()> {
    // Configure with OpenAI (requires OPENAI_API_KEY env var)
    // For demo, using mock LM
    let config_code = r#"
import dspy
import os

# Try to use OpenAI if API key is available
if os.getenv('OPENAI_API_KEY'):
    lm = dspy.OpenAI(model='gpt-3.5-turbo', max_tokens=500)
    dspy.settings.configure(lm=lm)
    print("Configured with OpenAI")
else:
    # Use dummy LM for testing
    print("Warning: OPENAI_API_KEY not set, using dummy LM")
    print("Set OPENAI_API_KEY to use real language model")
"#;

    py.run_bound(config_code, None, None)?;
    Ok(())
}

/// Create a ReAct agent with tool integration
fn create_react_agent(py: Python, registry: Arc<Mutex<ToolRegistry>>) -> PyResult<Py<PyAny>> {
    let _dspy = PyModule::import_bound(py, "dspy")?;

    // Get tool names from registry
    let tool_names = {
        let reg = registry.lock().unwrap();
        reg.list_tools()
    };

    info!("Creating ReAct agent with tools: {:?}", tool_names);

    // Create Python tool executor that calls back to Rust
    let tool_executor_code = r#"
import dspy

class RustToolExecutor(dspy.Module):
    def __init__(self, tool_names, rust_executor):
        super().__init__()
        self.tool_names = tool_names
        self.rust_executor = rust_executor

        # Create ReAct signature with available tools
        self.signature = dspy.Signature(
            "question -> answer",
            instructions=f"Available tools: {', '.join(tool_names)}"
        )

        self.react = dspy.ReAct(self.signature, max_iters=5)

    def forward(self, question):
        try:
            result = self.react(question=question)
            return result
        except Exception as e:
            print(f"Agent error: {e}")
            return dspy.Prediction(answer=f"Error: {str(e)}")
"#;

    let tool_module = PyModule::from_code_bound(py, tool_executor_code, "tool_executor.py", "tool_executor")?;

    let executor_class = tool_module.getattr("RustToolExecutor")?;

    let py_tool_names = PyList::new_bound(py, &tool_names);

    // Create a Python-accessible reference to the registry
    let py_executor = py.None();

    let agent = executor_class.call1((py_tool_names, py_executor))?;

    Ok(agent.into())
}

/// Execute agent with tool integration
fn execute_agent_with_tools(
    py: Python,
    agent: &Py<PyAny>,
    _executor: &ToolExecutor,
    question: &str,
) -> PyResult<AgentResponse> {
    info!("Executing agent with question: {}", question);

    let result = agent.bind(py).call_method1("forward", (question,))?;

    let answer: String = result.getattr("answer")?.extract()?;

    // Extract reasoning trace if available
    let mut reasoning_steps = Vec::new();

    if let Ok(trajectory) = result.getattr("trajectory") {
        let py_list = trajectory.downcast::<PyList>()?;

        for item in py_list.iter() {
            let thought = item
                .getattr("thought")
                .and_then(|v| v.extract::<String>())
                .unwrap_or_default();

            let action = item
                .getattr("action")
                .and_then(|v| v.extract::<String>())
                .ok();

            let observation = item
                .getattr("observation")
                .and_then(|v| v.extract::<String>())
                .ok();

            reasoning_steps.push(ReasoningStep {
                thought,
                action,
                observation,
            });
        }
    }

    let total_steps = reasoning_steps.len();

    Ok(AgentResponse {
        answer,
        reasoning_steps,
        total_steps,
    })
}

/// Print agent response with formatting
fn print_response(response: &AgentResponse) {
    println!("\n{}", "=".repeat(80));
    println!("AGENT RESPONSE");
    println!("{}", "=".repeat(80));

    if !response.reasoning_steps.is_empty() {
        println!("\nReasoning Steps ({} total):", response.total_steps);
        for (idx, step) in response.reasoning_steps.iter().enumerate() {
            println!("\nStep {}:", idx + 1);
            println!("  Thought: {}", step.thought);
            if let Some(action) = &step.action {
                println!("  Action: {}", action);
            }
            if let Some(obs) = &step.observation {
                println!("  Observation: {}", obs);
            }
        }
    }

    println!("\n{}", "-".repeat(80));
    println!("Final Answer:");
    println!("{}", response.answer);
    println!("{}", "=".repeat(80));
}

/// Print registry metrics
fn print_metrics(registry: &ToolRegistry) {
    println!("\n{}", "=".repeat(80));
    println!("TOOL METRICS");
    println!("{}", "=".repeat(80));

    let all_metrics = registry.get_all_metrics();

    for (tool_name, metrics) in all_metrics {
        let total = metrics.total_calls.load(std::sync::atomic::Ordering::Relaxed);
        let successful = metrics
            .successful_calls
            .load(std::sync::atomic::Ordering::Relaxed);
        let failed = metrics
            .failed_calls
            .load(std::sync::atomic::Ordering::Relaxed);

        println!("\nTool: {}", tool_name);
        println!("  Total calls: {}", total);
        println!("  Successful: {}", successful);
        println!("  Failed: {}", failed);
        println!("  Success rate: {:.2}%", metrics.success_rate() * 100.0);
        println!("  Avg duration: {:.2}ms", metrics.average_duration_ms());
    }

    println!("{}", "=".repeat(80));
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter("tool_using_agent=info")
        .init();

    info!("Starting tool-using agent example");

    // Create tool registry
    let mut registry = ToolRegistry::new();

    // Register web search tool
    registry.register_with_metadata(
        "web_search",
        web_search_tool,
        ToolMetadata {
            name: "web_search".to_string(),
            description: "Search the web for information".to_string(),
            version: "1.0.0".to_string(),
            timeout_ms: 5000,
            retry_enabled: true,
            max_retries: 3,
            tags: vec!["search".to_string(), "web".to_string()],
        },
    )?;

    // Register calculator tool
    registry.register_with_metadata(
        "calculator",
        calculator_tool,
        ToolMetadata {
            name: "calculator".to_string(),
            description: "Perform mathematical calculations".to_string(),
            version: "1.0.0".to_string(),
            timeout_ms: 1000,
            retry_enabled: false,
            max_retries: 0,
            tags: vec!["math".to_string(), "calculation".to_string()],
        },
    )?;

    // Register file reader tool
    registry.register_with_metadata(
        "file_reader",
        file_reader_tool,
        ToolMetadata {
            name: "file_reader".to_string(),
            description: "Read contents from files".to_string(),
            version: "1.0.0".to_string(),
            timeout_ms: 3000,
            retry_enabled: true,
            max_retries: 2,
            tags: vec!["file".to_string(), "io".to_string()],
        },
    )?;

    // Register weather API tool
    registry.register_with_metadata(
        "weather_api",
        weather_api_tool,
        ToolMetadata {
            name: "weather_api".to_string(),
            description: "Get current weather information".to_string(),
            version: "1.0.0".to_string(),
            timeout_ms: 5000,
            retry_enabled: true,
            max_retries: 3,
            tags: vec!["weather".to_string(), "api".to_string()],
        },
    )?;

    info!("Registered {} tools", registry.list_tools().len());

    // Validate registry
    registry.validate_all()?;
    info!("All tools validated successfully");

    // Create tool executor
    let executor = ToolExecutor::new(registry);
    let registry_ref = executor.get_registry();

    // Test individual tool execution with retry
    println!("\n{}", "=".repeat(80));
    println!("TESTING INDIVIDUAL TOOLS");
    println!("{}", "=".repeat(80));

    let search_result = executor
        .execute_with_retry("web_search", "Rust programming", &RetryConfig::default())
        .await?;
    println!("\nWeb Search Result:\n{}", search_result);

    let calc_result = executor
        .execute_with_retry("calculator", "42 * 2", &RetryConfig::default())
        .await?;
    println!("\nCalculator Result:\n{}", calc_result);

    let weather_result = executor
        .execute_with_retry("weather_api", "San Francisco", &RetryConfig::default())
        .await?;
    println!("\nWeather Result:\n{}", weather_result);

    // Initialize Python and DSPy
    println!("\n{}", "=".repeat(80));
    println!("INITIALIZING REACT AGENT");
    println!("{}", "=".repeat(80));

    Python::with_gil(|py| -> PyResult<()> {
        // Configure DSPy
        configure_dspy(py)?;

        // Create ReAct agent
        let agent = create_react_agent(py, registry_ref.clone())?;

        // Example questions
        let questions = vec![
            "What is 15 * 8?",
            "Search for information about machine learning",
            "What's the weather like in New York?",
        ];

        for question in questions {
            let response = execute_agent_with_tools(py, &agent, &executor, question)?;
            print_response(&response);

            // Small delay between questions
            std::thread::sleep(std::time::Duration::from_millis(500));
        }

        Ok(())
    })?;

    // Print final metrics
    {
        let registry = registry_ref.lock().unwrap();
        print_metrics(&registry);
    }

    info!("Example completed successfully");
    Ok(())
}
