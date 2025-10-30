//! Agent Observability Demo
//!
//! Demonstrates comprehensive tracing, metrics, and Jaeger integration
//! for DSPy agents from Rust.

use agent_observability::{
    export_metrics_json, get_metrics, reset_metrics, ReasoningChain, TracedAgent,
    TracedAgentConfig,
};
use anyhow::{Context, Result};
use opentelemetry::global;
use opentelemetry::sdk::trace as sdktrace;
use opentelemetry::sdk::Resource;
use opentelemetry::KeyValue;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::time::Duration;
use tracing::{debug, error, info, info_span, instrument, warn, Level};
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;
use tracing_subscriber::{fmt, EnvFilter};

/// Initialize tracing with multiple layers
fn init_tracing() -> Result<()> {
    info!("Initializing tracing infrastructure");

    // Console layer for human-readable output
    let fmt_layer = fmt::layer()
        .with_target(true)
        .with_thread_ids(true)
        .with_line_number(true)
        .with_level(true)
        .pretty();

    // JSON layer for structured logging
    let json_layer = fmt::layer()
        .json()
        .with_current_span(true)
        .with_span_list(true);

    // Environment filter
    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info,agent_observability=debug"));

    // OpenTelemetry/Jaeger layer
    let tracer = opentelemetry_jaeger::new_agent_pipeline()
        .with_service_name("dspy-agent-rust")
        .with_endpoint("localhost:6831")
        .with_trace_config(
            sdktrace::config().with_resource(Resource::new(vec![
                KeyValue::new("service.name", "dspy-agent-rust"),
                KeyValue::new("service.version", "0.1.0"),
                KeyValue::new("deployment.environment", "development"),
            ])),
        )
        .install_batch(opentelemetry::runtime::Tokio)
        .context("Failed to initialize Jaeger tracer")?;

    let telemetry_layer = tracing_opentelemetry::layer().with_tracer(tracer);

    // Combine all layers
    tracing_subscriber::registry()
        .with(env_filter)
        .with(fmt_layer)
        .with(telemetry_layer)
        .try_init()
        .context("Failed to initialize tracing subscriber")?;

    info!("Tracing initialized successfully");
    Ok(())
}

/// Shutdown tracing and flush all data
fn shutdown_tracing() {
    info!("Shutting down tracing");
    global::shutdown_tracer_provider();
}

/// Setup DSPy environment
#[instrument]
fn setup_dspy(py: Python) -> Result<()> {
    info!("Setting up DSPy environment");

    let sys = py.import("sys")?;
    let path = sys.getattr("path")?;
    path.call_method1("append", (".",))?;

    debug!("Importing DSPy");
    let dspy = py.import("dspy")?;

    debug!("Configuring OpenAI LM");
    let openai_class = dspy.getattr("OpenAI")?;
    let lm = openai_class.call1(("gpt-3.5-turbo",))?;

    dspy.call_method1("configure", (lm,))?;

    info!("DSPy configured successfully");
    Ok(())
}

/// Create a simple Chain of Thought agent
#[instrument(skip(py))]
fn create_cot_agent(py: Python) -> Result<Py<PyAny>> {
    info!("Creating Chain of Thought agent");

    let dspy = py.import("dspy")?;

    // Define signature
    let code = r#"
class QASignature(dspy.Signature):
    """Answer questions with step-by-step reasoning."""
    question = dspy.InputField()
    answer = dspy.OutputField(desc="A clear, concise answer")
"#;

    py.run(code, None, None)?;

    let locals = PyDict::new(py);
    locals.set_item("dspy", dspy)?;

    // Create ChainOfThought module
    let code = r#"
agent = dspy.ChainOfThought(QASignature)
"#;

    py.run(code, None, Some(locals))?;

    let agent = locals.get_item("agent")?.unwrap();

    info!("Chain of Thought agent created");
    Ok(agent.into())
}

/// Run single agent query with full instrumentation
#[instrument(skip(agent, py))]
async fn run_instrumented_query(
    py: Python<'_>,
    agent: &TracedAgent,
    question: &str,
) -> Result<String> {
    let span = info_span!("agent_query", question_preview = question.chars().take(50).collect::<String>());
    let _enter = span.enter();

    info!("Starting instrumented agent query");

    let result = agent.forward(py, question)?;

    info!(
        answer_preview = result.chars().take(100).collect::<String>(),
        "Query completed"
    );

    Ok(result)
}

/// Run multiple queries and track reasoning chains
#[instrument(skip(agent, py))]
async fn run_query_batch(
    py: Python<'_>,
    agent: &TracedAgent,
    questions: &[&str],
) -> Result<Vec<String>> {
    info!(batch_size = questions.len(), "Starting query batch");

    let mut results = Vec::new();
    let mut chain = ReasoningChain::default();

    for (idx, question) in questions.iter().enumerate() {
        let span = info_span!("batch_query", batch_index = idx, total = questions.len());
        let _enter = span.enter();

        debug!(question = question, "Processing batch item");

        let start = std::time::Instant::now();

        match agent.forward(py, question) {
            Ok(answer) => {
                let elapsed = start.elapsed();
                chain.add_step(
                    format!("Question: {}", question),
                    Some("forward".to_string()),
                    Some(answer.clone()),
                    elapsed,
                );

                results.push(answer);
                info!(batch_index = idx, "Batch item completed");
            }
            Err(e) => {
                error!(batch_index = idx, error = %e, "Batch item failed");
                return Err(e);
            }
        }
    }

    info!(
        batch_size = questions.len(),
        total_steps = chain.step_count(),
        total_duration_ms = chain.total_duration().as_millis(),
        "Batch processing complete"
    );

    // Export reasoning chain
    if let Ok(json) = chain.export_json() {
        debug!("Reasoning chain: {}", json);
    }

    Ok(results)
}

/// Run performance benchmark
#[instrument(skip(agent, py))]
async fn run_benchmark(py: Python<'_>, agent: &TracedAgent, iterations: usize) -> Result<()> {
    info!(iterations, "Starting performance benchmark");

    let test_question = "What is the capital of France?";

    for i in 0..iterations {
        let span = info_span!("benchmark_iteration", iteration = i, total = iterations);
        let _enter = span.enter();

        match agent.forward(py, test_question) {
            Ok(_) => {
                debug!(iteration = i, "Benchmark iteration successful");
            }
            Err(e) => {
                warn!(iteration = i, error = %e, "Benchmark iteration failed");
            }
        }
    }

    info!(iterations, "Benchmark complete");
    Ok(())
}

/// Demonstrate metadata tracking
#[instrument(skip(agent, py))]
async fn run_with_metadata(py: Python<'_>, agent: &TracedAgent) -> Result<String> {
    info!("Running query with custom metadata");

    let mut metadata = HashMap::new();
    metadata.insert("user_id".to_string(), "user_123".to_string());
    metadata.insert("session_id".to_string(), "session_456".to_string());
    metadata.insert("experiment".to_string(), "metadata_tracking".to_string());

    let question = "Explain quantum computing in simple terms.";

    agent.forward_with_metadata(py, question, metadata)
}

/// Display metrics summary
fn display_metrics() -> Result<()> {
    info!("Displaying metrics summary");

    let registry = get_metrics();
    let metrics = registry.read();

    println!("\n{}", "=".repeat(60));
    println!("METRICS SUMMARY");
    println!("{}", "=".repeat(60));

    println!("\nOverall Statistics:");
    println!("  Total Calls: {}", metrics.total_calls);
    println!("  Successful: {}", metrics.successful_calls);
    println!("  Success Rate: {:.2}%", metrics.success_rate() * 100.0);

    println!("\nFailure Breakdown:");
    for (category, count, percentage) in metrics.failure_breakdown() {
        println!("  {}: {} ({:.1}%)", category.as_str(), count, percentage);
    }

    println!("\nRecent Operations:");
    for metric in metrics.all_metrics().iter().rev().take(5) {
        println!(
            "  {} - {} - {}ms - {}",
            metric.operation,
            if metric.success { "SUCCESS" } else { "FAILED" },
            metric.duration_ms,
            metric.start_time.format("%H:%M:%S")
        );
    }

    println!("\n{}", "=".repeat(60));

    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    init_tracing().context("Failed to initialize tracing")?;

    info!("Starting agent observability demo");

    // Reset metrics
    reset_metrics();

    let result = Python::with_gil(|py| {
        let span = info_span!("main_execution");
        let _enter = span.enter();

        // Setup DSPy
        setup_dspy(py).context("Failed to setup DSPy")?;

        // Create agent
        let agent_py = create_cot_agent(py).context("Failed to create agent")?;

        // Configure traced agent
        let config = TracedAgentConfig {
            timeout: Duration::from_secs(30),
            verbose: true,
            record_metrics: true,
        };

        let agent = TracedAgent::new(agent_py, config);

        // Run single query
        let _result = tokio::runtime::Handle::current()
            .block_on(run_instrumented_query(
                py,
                &agent,
                "What is machine learning?",
            ))
            .context("Single query failed")?;

        // Run batch queries
        let questions = vec![
            "What is Python?",
            "Explain recursion.",
            "What are neural networks?",
        ];

        let _batch_results = tokio::runtime::Handle::current()
            .block_on(run_query_batch(py, &agent, &questions))
            .context("Batch queries failed")?;

        // Run benchmark
        tokio::runtime::Handle::current()
            .block_on(run_benchmark(py, &agent, 5))
            .context("Benchmark failed")?;

        // Run with metadata
        let _metadata_result = tokio::runtime::Handle::current()
            .block_on(run_with_metadata(py, &agent))
            .context("Metadata query failed")?;

        Ok::<(), anyhow::Error>(())
    });

    result?;

    // Display metrics
    display_metrics()?;

    // Export metrics to JSON
    if let Ok(json) = export_metrics_json() {
        println!("\nExported metrics JSON (first 500 chars):");
        println!("{}", json.chars().take(500).collect::<String>());
    }

    info!("Demo complete - check Jaeger UI at http://localhost:16686");

    // Shutdown and flush
    shutdown_tracing();

    Ok(())
}
