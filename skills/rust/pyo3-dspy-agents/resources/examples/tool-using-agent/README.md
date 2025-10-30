# Tool-Using Agent Example

A production-ready example of a DSPy ReAct agent with multiple custom tools, comprehensive error handling, retry logic, circuit breaker patterns, and monitoring capabilities.

## Features

### Tool System
- **Advanced Tool Registry**: Type-safe tool registration with metadata
- **Tool Validation**: Automatic validation of tool configurations
- **Tool Metrics**: Track performance, success rates, and latency
- **Circuit Breaker**: Prevent cascading failures from unhealthy tools
- **Retry Logic**: Exponential backoff with configurable retry strategies

### Real-World Tools
1. **Web Search**: Mock web search with result ranking
2. **Calculator**: Safe mathematical expression evaluation
3. **File Reader**: Secure file operations with path validation
4. **Weather API**: REST API integration with async support

### Production Features
- Comprehensive error handling with custom error types
- Structured logging and tracing
- Performance metrics collection
- Fault tolerance with circuit breakers
- Async/await integration with Tokio
- Thread-safe shared state management

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DSPy ReAct Agent                        │
│                   (Python Side)                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ PyO3 Bridge
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Tool Executor                             │
│              (Retry + Validation)                           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Tool Registry                             │
│         HashMap<String, ToolEntry>                          │
│                                                             │
│  ToolEntry:                                                 │
│  ├── function: ToolFn                                       │
│  ├── metadata: ToolMetadata                                 │
│  ├── metrics: Arc<ToolMetrics>                              │
│  └── circuit_breaker: Arc<CircuitBreaker>                   │
└─────────────────────────────────────────────────────────────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
              ▼          ▼          ▼
         [Tool 1]   [Tool 2]   [Tool 3]
         (Rust)     (Rust)     (Rust)
```

## Usage

### Prerequisites

1. **Install Rust** (if not already installed):
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

2. **Install Python dependencies**:
```bash
pip install dspy-ai openai
```

3. **Set OpenAI API key** (optional for demo):
```bash
export OPENAI_API_KEY="your-key-here"
```

Note: The example will work without an API key using a dummy LM, but won't produce meaningful agent responses.

### Building

```bash
# Build the project
cargo build --release

# Run tests
cargo test

# Run the example
cargo run --release
```

### Running

```bash
# Run with default configuration
cargo run --release

# Run with logging
RUST_LOG=info cargo run --release

# Run with debug logging
RUST_LOG=debug cargo run --release
```

## Code Structure

### `src/lib.rs` (~400 lines)

Core library implementing the tool system:

- **ToolRegistry**: Central registry for all tools
  - `register()`: Register new tools
  - `execute()`: Execute tools with circuit breaker
  - `get_metrics()`: Retrieve tool performance metrics
  - `validate_all()`: Validate all tool configurations

- **ToolExecutor**: Handles tool execution with retry
  - `execute_with_retry()`: Execute with exponential backoff
  - Configurable retry strategies
  - Timeout handling

- **CircuitBreaker**: Fault tolerance pattern
  - `call()`: Execute with circuit breaker protection
  - States: Closed, Open, HalfOpen
  - Automatic recovery after timeout

- **ToolMetrics**: Performance tracking
  - Total/successful/failed call counts
  - Average duration calculation
  - Success rate computation
  - Last success/failure timestamps

### `src/main.rs` (~300 lines)

Example application demonstrating usage:

1. **Tool Implementations**:
   - `web_search_tool()`: Mock web search
   - `calculator_tool()`: Safe expression evaluation
   - `file_reader_tool()`: Secure file access
   - `weather_api_tool()`: Async REST API calls

2. **DSPy Integration**:
   - `configure_dspy()`: LM configuration
   - `create_react_agent()`: Agent initialization
   - `execute_agent_with_tools()`: Agent execution with tracing

3. **Examples**:
   - Individual tool testing
   - ReAct agent execution
   - Metrics reporting

## Configuration

### Tool Metadata

Each tool can be configured with:

```rust
ToolMetadata {
    name: "tool_name".to_string(),
    description: "Tool description".to_string(),
    version: "1.0.0".to_string(),
    timeout_ms: 5000,           // Tool timeout
    retry_enabled: true,         // Enable retry logic
    max_retries: 3,             // Max retry attempts
    tags: vec!["tag1", "tag2"], // Categorization tags
}
```

### Retry Configuration

Customize retry behavior:

```rust
RetryConfig {
    max_retries: 3,                              // Max attempts
    initial_delay: Duration::from_millis(100),   // Initial backoff
    max_delay: Duration::from_secs(5),           // Max backoff
    backoff_multiplier: 2.0,                     // Exponential factor
    retry_on_timeout: true,                      // Retry on timeout
}
```

### Circuit Breaker Configuration

Configure fault tolerance:

```rust
CircuitBreaker::new(
    5,                          // Failure threshold
    Duration::from_secs(30)     // Recovery timeout
)
```

## Output Example

```
================================================================================
TESTING INDIVIDUAL TOOLS
================================================================================

Web Search Result:
Search results for 'Rust programming':
1. Article about Rust programming: Comprehensive guide and documentation
2. Tutorial on Rust programming: Step-by-step instructions
3. Research paper: Latest developments in Rust programming

Calculator Result:
42 * 2 = 84

Weather Result:
Weather in San Francisco:
Temperature: 72°F (22°C)
Conditions: Partly cloudy
Humidity: 65%
Wind: 10 mph NW

================================================================================
INITIALIZING REACT AGENT
================================================================================

================================================================================
AGENT RESPONSE
================================================================================

Reasoning Steps (3 total):

Step 1:
  Thought: I need to calculate 15 * 8
  Action: calculator("15 * 8")
  Observation: 15 * 8 = 120

Step 2:
  Thought: I have the result
  Action: None
  Observation: None

--------------------------------------------------------------------------------
Final Answer:
The answer is 120. I used the calculator tool to multiply 15 by 8.
================================================================================

================================================================================
TOOL METRICS
================================================================================

Tool: web_search
  Total calls: 2
  Successful: 2
  Failed: 0
  Success rate: 100.00%
  Avg duration: 0.15ms

Tool: calculator
  Total calls: 3
  Successful: 3
  Failed: 0
  Success rate: 100.00%
  Avg duration: 0.08ms

Tool: weather_api
  Total calls: 2
  Successful: 2
  Failed: 0
  Success rate: 100.00%
  Avg duration: 102.50ms

Tool: file_reader
  Total calls: 0
  Successful: 0
  Failed: 0
  Success rate: 100.00%
  Avg duration: 0.00ms
================================================================================
```

## Extending the Example

### Adding a New Tool

1. **Implement the tool function**:
```rust
fn my_custom_tool(input: &str) -> Result<String> {
    // Your tool logic here
    Ok(format!("Processed: {}", input))
}
```

2. **Register the tool**:
```rust
registry.register_with_metadata(
    "my_tool",
    my_custom_tool,
    ToolMetadata {
        name: "my_tool".to_string(),
        description: "My custom tool".to_string(),
        ..Default::default()
    },
)?;
```

3. **Use in agent queries**:
The ReAct agent will automatically discover and use your tool.

### Async Tools

For async operations:

```rust
async fn async_tool(input: &str) -> Result<String> {
    // Async operations
    tokio::time::sleep(Duration::from_millis(100)).await;
    Ok("result".to_string())
}

// Synchronous wrapper
fn sync_wrapper(input: &str) -> Result<String> {
    let rt = tokio::runtime::Runtime::new()?;
    rt.block_on(async_tool(input))
}

// Register wrapper
registry.register("async_tool", sync_wrapper)?;
```

### External API Integration

For real HTTP requests:

```rust
async fn real_weather_tool(location: &str) -> Result<String> {
    let client = reqwest::Client::new();
    let response = client
        .get(&format!("https://api.weather.com/v1/location/{}", location))
        .header("Authorization", "Bearer YOUR_API_KEY")
        .send()
        .await?
        .json::<WeatherResponse>()
        .await?;

    Ok(format!("Temperature: {}", response.temperature))
}
```

## Testing

### Unit Tests

```bash
# Run all tests
cargo test

# Run specific test
cargo test test_registry_basic

# Run with output
cargo test -- --nocapture
```

### Integration Tests

```bash
# Test with real DSPy agent
cargo test --features integration

# Benchmark tool performance
cargo bench
```

## Production Deployment

### Recommended Practices

1. **Error Handling**: Always use proper error types and context
2. **Timeouts**: Set appropriate timeouts for all tools
3. **Circuit Breakers**: Enable circuit breakers for external services
4. **Retry Logic**: Configure exponential backoff for transient failures
5. **Metrics**: Monitor tool performance and health
6. **Logging**: Use structured logging for debugging
7. **Security**: Validate all inputs, especially for file and command tools
8. **Rate Limiting**: Implement rate limiting for API tools
9. **Caching**: Cache expensive tool results when appropriate
10. **Testing**: Write comprehensive tests for all tools

### Monitoring

Track these metrics in production:
- Tool call rates
- Success/failure rates
- Latency percentiles (p50, p95, p99)
- Circuit breaker states
- Error types and frequencies

### Scaling

For high-throughput scenarios:
- Use connection pooling for API tools
- Implement request queuing
- Deploy multiple agent instances
- Use async execution where possible
- Cache frequently-accessed data

## Troubleshooting

### Common Issues

1. **Import Error**: `ModuleNotFoundError: No module named 'dspy'`
   - Solution: `pip install dspy-ai`

2. **API Key Error**: Agent produces empty responses
   - Solution: Set `OPENAI_API_KEY` environment variable

3. **Circuit Breaker Open**: Tool execution blocked
   - Solution: Check tool health, wait for recovery timeout, or reset breaker

4. **Timeout Errors**: Tool execution exceeds timeout
   - Solution: Increase timeout in `ToolMetadata` or optimize tool logic

5. **Build Errors**: Missing dependencies
   - Solution: Run `cargo update` and ensure all dependencies are available

## Performance Characteristics

- **Tool Registration**: O(1)
- **Tool Lookup**: O(1)
- **Tool Execution**: Depends on tool implementation
- **Metrics Collection**: O(1) with atomic operations
- **Circuit Breaker Check**: O(1)

## Dependencies

- **pyo3** (0.22): Python interop
- **anyhow**: Error handling
- **tokio**: Async runtime
- **reqwest**: HTTP client (for API tools)
- **serde**: Serialization
- **tracing**: Structured logging
- **chrono**: Time handling
- **thiserror**: Custom error types

## License

MIT License - See LICENSE file for details

## References

- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [PyO3 Guide](https://pyo3.rs/)
- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Tokio Documentation](https://tokio.rs/)

## Related Examples

- **basic-react**: Simple ReAct agent without custom tools
- **stateful-agent**: Agent with conversation memory
- **production-agent-service**: Full production deployment
- **parallel-agents**: Concurrent agent execution

## Contributing

Contributions welcome! Please ensure:
- All tests pass
- Code is formatted with `cargo fmt`
- No clippy warnings: `cargo clippy`
- Documentation is updated

## Support

For issues or questions:
- Check the troubleshooting section
- Review DSPy documentation
- Open an issue on GitHub
- Consult the main skill file: `skill-rust-pyo3-dspy-agents.md`
