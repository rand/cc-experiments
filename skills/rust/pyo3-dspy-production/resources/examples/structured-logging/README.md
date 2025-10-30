# Structured Logging for DSPy Production Integration

Production-grade structured logging and tracing infrastructure demonstrating best practices for observability in Rust-based DSPy integrations.

## Features

- **Request ID Propagation**: Automatic correlation across async operations
- **Multi-Format Output**: JSON, pretty console, or compact formats
- **DSPy-Specific Events**: Custom event types for predictions, optimizations, pipelines
- **Performance Metrics**: Aggregation and statistical analysis
- **Error Context Preservation**: Full error chain tracking
- **Concurrent Operation Tracking**: Correlation across parallel workstreams

## Architecture

### Core Components

1. **RequestContext**: Correlation ID management and metadata propagation
2. **DSpyEvent**: Typed events for DSPy-specific operations
3. **PerformanceMetric**: Timing and success tracking
4. **MetricsAggregator**: Statistical aggregation (mean, p50, p95, p99, max)
5. **InstrumentedDSpyService**: Fully instrumented service wrapper

### Logging Layers

```
┌─────────────────────────────────────────┐
│         Application Code                │
│  (with #[instrument] macros)            │
└────────────────┬────────────────────────┘
                 │
        ┌────────▼──────────┐
        │  tracing spans    │
        │  and events       │
        └────────┬──────────┘
                 │
   ┌─────────────┴──────────────┐
   │                            │
┌──▼───────────┐      ┌─────────▼──────┐
│ Console      │      │ JSON File      │
│ (Pretty)     │      │ (Machine)      │
└──────────────┘      └────────────────┘
```

## Usage

### Basic Setup

```rust
use structured_logging::{LoggingConfig, LogFormat, init_logging};

let config = LoggingConfig {
    level: "info".to_string(),
    format: LogFormat::Pretty,
    console_enabled: true,
    file_enabled: true,
    file_path: Some("/var/log/app.jsonl".to_string()),
    request_id_enabled: true,
    performance_metrics_enabled: true,
    dspy_instrumentation_enabled: true,
};

init_logging(&config)?;
```

### Request Correlation

```rust
use structured_logging::RequestContext;

// Create root context
let root = RequestContext::new()
    .with_user_id("user_123".to_string())
    .with_metadata("source".to_string(), "api".to_string());

// Create child contexts (maintains correlation)
let child1 = root.child();
let child2 = root.child();

// All logs from child contexts include parent_id
process_request(&child1).await?;
```

### Instrumenting Functions

```rust
use tracing::{instrument, info};

#[instrument(skip(context), fields(request_id = %context.request_id))]
async fn my_function(context: &RequestContext, data: String) -> Result<()> {
    info!(data_len = data.len(), "Processing data");
    // Function logic here
    Ok(())
}
```

### DSPy Event Logging

```rust
use structured_logging::DSpyEvent;

let event = DSpyEvent::Prediction {
    model: "gpt-4".to_string(),
    prompt_tokens: 150,
    completion_tokens: 75,
    latency_ms: 1250,
};
event.log(&context);
```

### Performance Metrics

```rust
use structured_logging::{MetricsAggregator, PerformanceMetric};

let metrics = MetricsAggregator::new();

metrics.record(PerformanceMetric {
    operation: "predict".to_string(),
    duration_ms: 125,
    success: true,
    timestamp: Utc::now(),
    context: context.clone(),
}).await;

// Get summary statistics
let summary = metrics.summarize().await;
println!("{}", summary);
```

### Using InstrumentedDSpyService

```rust
use structured_logging::InstrumentedDSpyService;

let service = InstrumentedDSpyService::new(config);
let context = RequestContext::new();

// All operations automatically instrumented
let response = service.predict(
    context.clone(),
    "gpt-4".to_string(),
    "What is the capital of France?".to_string(),
).await?;

// Get metrics for all operations
let metrics = service.metrics_summary().await;
```

## Running the Examples

### Build

```bash
cargo build --release
```

### Run with Different Log Levels

```bash
# Default (info level)
cargo run

# Debug level
RUST_LOG=debug cargo run

# Trace level (very verbose)
RUST_LOG=trace cargo run

# Filter specific modules
RUST_LOG=structured_logging=debug cargo run
```

### Run Tests

```bash
cargo test
```

## Log Output Examples

### Pretty Console Format

```
2024-01-15T10:30:45.123Z  INFO structured_logging: Starting prediction
    at src/lib.rs:234
    in structured_logging::predict with request_id: 550e8400-e29b-41d4-a716-446655440000, model: "gpt-4"

2024-01-15T10:30:46.373Z  INFO structured_logging: DSPy prediction completed
    at src/lib.rs:245
    in structured_logging::predict with request_id: 550e8400-e29b-41d4-a716-446655440000
    model: "gpt-4"
    prompt_tokens: 150
    completion_tokens: 75
    latency_ms: 1250
    total_tokens: 225
```

### JSON Format

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "fields": {
    "message": "Starting prediction",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "model": "gpt-4",
    "prompt_len": 42
  },
  "target": "structured_logging",
  "span": {
    "name": "predict",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "file": "src/lib.rs",
  "line": 234
}
```

### Compact Format

```
2024-01-15T10:30:45.123Z INFO predict{request_id=550e8400-e29b-41d4-a716-446655440000 model="gpt-4"}: structured_logging: Starting prediction prompt_len=42
```

## Best Practices

### 1. Always Use Request Context

```rust
// Good
async fn my_handler(context: RequestContext) -> Result<Response> {
    info!(request_id = %context.request_id, "Handling request");
    // ...
}

// Bad
async fn my_handler() -> Result<Response> {
    info!("Handling request"); // No correlation!
    // ...
}
```

### 2. Instrument All Async Functions

```rust
#[instrument(skip(context), fields(request_id = %context.request_id))]
async fn process_data(context: &RequestContext, data: Vec<u8>) -> Result<()> {
    // Automatically creates span for this function
    // ...
}
```

### 3. Use Structured Fields

```rust
// Good
info!(
    user_id = %user.id,
    action = "login",
    duration_ms = elapsed,
    success = true,
    "User action completed"
);

// Bad
info!("User {} performed login in {}ms", user.id, elapsed);
```

### 4. Preserve Error Context

```rust
// Good
operation()
    .await
    .context("Failed to complete operation")?;

// Bad
operation().await?; // No context preserved
```

### 5. Log at Appropriate Levels

- **TRACE**: Very detailed, function entry/exit
- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages
- **WARN**: Warning conditions that should be addressed
- **ERROR**: Error conditions that need attention

### 6. Use Skip for Large Data

```rust
#[instrument(skip(large_data), fields(data_len = large_data.len()))]
async fn process(large_data: Vec<u8>) -> Result<()> {
    // Don't log large_data itself, just its length
}
```

### 7. Aggregate Metrics, Don't Just Log

```rust
// Good: Collect metrics for analysis
metrics.record(metric).await;
let summary = metrics.summarize().await;

// Bad: Just logging individual measurements
info!("Operation took {}ms", duration);
```

## Performance Considerations

### Overhead

- **Pretty format**: ~5-10% overhead (dev/testing)
- **JSON format**: ~2-5% overhead (production)
- **Compact format**: ~1-3% overhead (high-throughput)

### Recommendations

1. Use JSON format in production
2. Set appropriate log levels (INFO or WARN in prod)
3. Use file output for production logs
4. Implement log rotation (not shown in this example)
5. Consider sampling for high-frequency events

### Async Overhead

The `#[instrument]` macro adds minimal overhead:
- Span creation: ~100ns
- Event emission: ~200-500ns
- Context propagation: ~50ns

## Integration with Monitoring Systems

### Exporting to External Systems

The JSON format is compatible with:
- **Elasticsearch**: Direct ingestion via Filebeat
- **Splunk**: HEC input or file monitoring
- **DataDog**: Log agent ingestion
- **CloudWatch**: CloudWatch Logs agent

### OpenTelemetry Integration

For OpenTelemetry, replace `tracing-subscriber` layers with:

```rust
use tracing_opentelemetry::OpenTelemetryLayer;

let tracer = opentelemetry_jaeger::new_pipeline()
    .with_service_name("my-service")
    .install_simple()?;

let telemetry = OpenTelemetryLayer::new(tracer);
```

## Troubleshooting

### No Logs Appearing

1. Check `RUST_LOG` environment variable
2. Verify logging is initialized before any log calls
3. Ensure log level allows messages through

### Missing Request IDs

1. Ensure `RequestContext` is created and passed
2. Check `#[instrument]` includes `request_id` field
3. Verify context is propagated to child tasks

### Poor Performance

1. Lower log level in production
2. Use compact or JSON format
3. Consider async file writing
4. Implement log sampling for high-frequency events

## License

MIT
