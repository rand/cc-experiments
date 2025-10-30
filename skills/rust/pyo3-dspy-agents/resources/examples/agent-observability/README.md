# Agent Observability Example

Comprehensive demonstration of tracing, logging, metrics, and distributed observability for DSPy agents executed from Rust using PyO3.

## Overview

This example showcases production-grade observability patterns for AI agents:

- **Structured Logging**: Context-rich logs with spans and fields
- **Distributed Tracing**: OpenTelemetry/Jaeger integration for request tracking
- **Performance Metrics**: Automatic collection of latency, throughput, and error rates
- **Error Categorization**: Intelligent error classification and tracking
- **Reasoning Chain Tracking**: Step-by-step reasoning chain visualization
- **Multi-Layer Tracing**: Console, file, and distributed tracing simultaneously

## Features

### 1. Instrumented Agent Wrapper

The `TracedAgent` wrapper provides automatic instrumentation:

```rust
use agent_observability::{TracedAgent, TracedAgentConfig};

let config = TracedAgentConfig {
    timeout: Duration::from_secs(30),
    verbose: true,
    record_metrics: true,
};

let agent = TracedAgent::new(agent_py, config);
let result = agent.forward(py, "What is machine learning?")?;
```

### 2. Structured Spans

All operations are wrapped in tracing spans:

```rust
#[instrument(skip(py, agent), fields(question_len = question.len()))]
pub fn traced_agent_call(
    py: Python,
    agent: &Py<PyAny>,
    question: &str,
) -> PyResult<String> {
    info!("Executing agent with question");
    // ... execution logic
}
```

### 3. Performance Metrics

Automatic collection of operation metrics:

```rust
pub struct PerformanceMetrics {
    pub operation: String,
    pub start_time: DateTime<Utc>,
    pub end_time: DateTime<Utc>,
    pub duration_ms: u128,
    pub success: bool,
    pub error_category: Option<ErrorCategory>,
    pub metadata: HashMap<String, String>,
}
```

### 4. Error Categorization

Intelligent error classification:

```rust
pub enum ErrorCategory {
    PythonRuntime,
    AgentExecution,
    ToolInvocation,
    Timeout,
    Validation,
    NetworkIO,
    Configuration,
    Unknown,
}
```

### 5. Reasoning Chain Tracking

Track multi-step reasoning:

```rust
let mut chain = ReasoningChain::default();

chain.add_step(
    "Analyzing question",
    Some("search".to_string()),
    Some("Found relevant information".to_string()),
    elapsed,
);
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│  (TracedAgent, TracedTool, ReasoningChain)              │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                  Instrumentation Layer                   │
│  (#[instrument], spans, events, fields)                 │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                   Subscriber Layer                       │
│  (fmt layer, json layer, opentelemetry layer)           │
└───┬──────────────┬──────────────────┬───────────────────┘
    │              │                  │
┌───▼────┐   ┌─────▼─────┐   ┌────────▼────────┐
│Console │   │  File     │   │  Jaeger/OTLP    │
│ Output │   │  Logging  │   │  Export         │
└────────┘   └───────────┘   └─────────────────┘
```

## Prerequisites

- Rust 1.70+
- Python 3.9+
- DSPy (`pip install dspy-ai`)
- OpenAI API key
- Docker (for Jaeger)

## Setup

### 1. Install Dependencies

```bash
cd skills/rust/pyo3-dspy-agents/resources/examples/agent-observability
cargo build
```

### 2. Set Environment Variables

```bash
export OPENAI_API_KEY="your-api-key-here"
export RUST_LOG="info,agent_observability=debug"
```

### 3. Start Jaeger

```bash
docker-compose up -d
```

Verify Jaeger is running:
- UI: http://localhost:16686
- Agent endpoint: localhost:6831

### 4. Run the Example

```bash
cargo run
```

## Usage Examples

### Basic Tracing

```rust
use tracing::{info, instrument};

#[instrument]
fn my_function(input: &str) -> Result<String> {
    info!("Processing input");
    // ... your logic
    Ok(result)
}
```

### Custom Metadata

```rust
let mut metadata = HashMap::new();
metadata.insert("user_id".to_string(), "user_123".to_string());
metadata.insert("session_id".to_string(), "session_456".to_string());

let result = agent.forward_with_metadata(py, question, metadata)?;
```

### Batch Processing with Tracking

```rust
let questions = vec![
    "What is Python?",
    "Explain recursion.",
    "What are neural networks?",
];

let results = run_query_batch(py, &agent, &questions).await?;
```

### Performance Benchmarking

```rust
run_benchmark(py, &agent, 10).await?;
```

### Metrics Export

```rust
use agent_observability::{export_metrics_json, get_metrics};

// Get current metrics
let registry = get_metrics();
let metrics = registry.read();

println!("Total calls: {}", metrics.total_calls);
println!("Success rate: {:.2}%", metrics.success_rate() * 100.0);

// Export as JSON
let json = export_metrics_json()?;
std::fs::write("metrics.json", json)?;
```

## Jaeger Integration

### Viewing Traces

1. Open http://localhost:16686
2. Select service: `dspy-agent-rust`
3. Click "Find Traces"
4. Explore individual traces with full span details

### Trace Details Include

- Operation name and duration
- Input/output sizes
- Error messages and categories
- Custom metadata fields
- Parent-child span relationships
- Service dependencies

### Example Trace Structure

```
dspy-agent-rust
├─ agent_query (150ms)
│  ├─ agent_forward (145ms)
│  │  ├─ execute_with_timeout (140ms)
│  │  └─ metric_recording (5ms)
│  └─ result_processing (5ms)
```

## Configuration

### Tracing Levels

Set via `RUST_LOG` environment variable:

```bash
# All info, library debug
export RUST_LOG="info,agent_observability=debug"

# Everything debug
export RUST_LOG="debug"

# Specific modules
export RUST_LOG="agent_observability::traced_agent=trace"
```

### Jaeger Configuration

Edit `tracing_config.toml`:

```toml
[jaeger]
enabled = true
endpoint = "localhost:6831"
sampling = "always"  # or "never", or 0.0-1.0 for ratio
max_queue_size = 2048
batch_size = 512
```

### Custom Filters

In `tracing_config.toml`:

```toml
[filters]
default_level = "info"
module_levels = [
    "agent_observability=debug",
    "pyo3=info",
    "tokio=warn",
]
```

## Output Examples

### Console Output (Pretty Format)

```
2024-10-30T10:15:23.456Z INFO agent_observability::traced_agent: Starting agent execution
    at src/lib.rs:245
    in agent_observability::traced_agent::forward with question_len: 27

2024-10-30T10:15:23.789Z INFO agent_observability::traced_agent: Agent execution successful
    at src/lib.rs:268
    in agent_observability::traced_agent::forward
    duration_ms: 333
    answer_len: 156
```

### JSON Output (Structured Logging)

```json
{
  "timestamp": "2024-10-30T10:15:23.456Z",
  "level": "INFO",
  "target": "agent_observability::traced_agent",
  "fields": {
    "message": "Starting agent execution",
    "question_len": 27
  },
  "span": {
    "name": "forward",
    "question_len": 27,
    "timeout_ms": 30000
  }
}
```

### Metrics Summary

```
============================================================
METRICS SUMMARY
============================================================

Overall Statistics:
  Total Calls: 15
  Successful: 14
  Success Rate: 93.33%

Failure Breakdown:
  timeout: 1 (100.0%)

Recent Operations:
  agent_forward - SUCCESS - 145ms - 10:15:23
  agent_forward - SUCCESS - 132ms - 10:15:22
  agent_forward - FAILED - 30001ms - 10:15:20
  agent_forward - SUCCESS - 156ms - 10:14:58
  agent_forward - SUCCESS - 143ms - 10:14:57

============================================================
```

## Advanced Patterns

### Custom Span Attributes

```rust
use tracing::Span;

let span = Span::current();
span.record("user_id", "user_123");
span.record("model_version", "v2.1.0");
```

### Nested Spans

```rust
#[instrument]
fn outer_operation() -> Result<()> {
    let span = info_span!("inner_operation", step = 1);
    let _enter = span.enter();

    // Inner work here

    Ok(())
}
```

### Error Context Propagation

```rust
match agent.forward(py, question) {
    Ok(answer) => Ok(answer),
    Err(e) => {
        let category = ErrorCategory::from_error(&e.to_string());
        error!(
            error = %e,
            category = category.as_str(),
            "Agent execution failed"
        );
        Err(e)
    }
}
```

### Conditional Instrumentation

```rust
if config.verbose {
    debug!("Detailed execution information");
    span.record("detailed", true);
}
```

## Performance Considerations

### Overhead

- Tracing: ~1-5% overhead
- Metrics collection: ~0.5-1% overhead
- Jaeger export: ~1-2% overhead (batched)

### Optimization Tips

1. **Use appropriate log levels**: Debug only when needed
2. **Batch Jaeger exports**: Configure batch size (default: 512)
3. **Sample in production**: Use ratio-based sampling for high-volume
4. **Async I/O**: Enabled by default for minimal blocking

### Production Settings

```toml
[jaeger]
sampling = 0.1  # Sample 10% of traces
batch_size = 1024
max_queue_size = 4096

[filters]
default_level = "warn"
module_levels = [
    "agent_observability=info",
]
```

## Troubleshooting

### Jaeger Not Receiving Traces

1. Check Jaeger is running: `docker ps`
2. Verify endpoint: `telnet localhost 6831`
3. Check firewall settings
4. Enable debug logging: `RUST_LOG=opentelemetry=debug`

### High Memory Usage

1. Reduce batch size in `tracing_config.toml`
2. Decrease max queue size
3. Enable sampling
4. Limit metrics retention period

### Missing Spans

1. Ensure `#[instrument]` macro is applied
2. Check span is entered with `let _enter = span.enter()`
3. Verify tracing subscriber is initialized
4. Check log level filters

## Best Practices

### DO

- Use `#[instrument]` for all public functions
- Add context with span fields
- Record meaningful metadata
- Categorize errors appropriately
- Export metrics periodically
- Monitor dashboard regularly

### DON'T

- Log sensitive data (passwords, tokens)
- Over-instrument hot paths
- Block on trace export
- Ignore error categories
- Skip span context
- Use println! for production logging

## Testing

Run the included tests:

```bash
cargo test
```

Tests cover:
- Error categorization
- Metrics aggregation
- Reasoning chain tracking
- Span creation and recording

## Integration with Other Systems

### Prometheus

Future enhancement - uncomment in `docker-compose.yml`:

```yaml
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9090:9090"
```

### Grafana

Future enhancement - uncomment in `docker-compose.yml`:

```yaml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
```

## Resources

- [Tracing Documentation](https://docs.rs/tracing)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [PyO3 Guide](https://pyo3.rs)

## Related Examples

- `tool-using-agent`: Tool execution patterns
- Future: `state-persistence`: State management patterns
- Future: `multi-agent-system`: Multi-agent coordination

## License

Part of the PyO3 DSPy Agents skill collection.
