# Token Streaming Example

Complete demonstration of token-by-token LLM response streaming from DSPy using PyO3, Tokio, and async Rust.

## Overview

This example shows how to:
- Stream token-by-token responses from DSPy language models
- Handle real-time terminal output with proper flushing
- Manage multiple concurrent streams efficiently
- Aggregate streams from multiple sources
- Implement comprehensive error handling and recovery
- Display progress indicators during streaming

## Architecture

### Core Components

1. **DSpyStream**: Basic unbounded streaming with mpsc channels
2. **SafeDSpyStream**: Production-ready streaming with bounded channels and error handling
3. **StreamEvent**: Enum for stream lifecycle (Token, Done, Error)
4. **Buffering**: Automatic buffering and backpressure management

### Streaming Flow

```
Python DSPy Module
       ↓
spawn_blocking (offload to blocking thread pool)
       ↓
Python GIL acquisition + token iteration
       ↓
mpsc channel (bounded or unbounded)
       ↓
Tokio async stream
       ↓
Real-time terminal output
```

## Features

### 1. Simple Token Streaming

Basic streaming with unbounded channels for quick prototyping:

```rust
let stream = DSpyStream::new("Explain async programming".to_string())?;
let mut stream = stream.into_stream();

while let Some(token) = stream.next().await {
    print!("{}", token);
}
```

### 2. Safe Streaming with Events

Production-ready streaming with explicit lifecycle events:

```rust
let stream = SafeDSpyStream::new("What is Rust?".to_string(), 100)?;
let mut stream = stream.into_stream();

while let Some(event) = stream.next().await {
    match event {
        StreamEvent::Token(token) => print!("{}", token),
        StreamEvent::Done => println!("\n[Complete]"),
        StreamEvent::Error(e) => eprintln!("\n[Error: {}]", e),
    }
}
```

### 3. Concurrent Streaming

Multiple streams running in parallel:

```rust
let handles: Vec<_> = questions
    .into_iter()
    .map(|q| {
        tokio::spawn(async move {
            let stream = SafeDSpyStream::new(q, 100)?;
            collect_stream(stream).await
        })
    })
    .collect();

let results = join_all(handles).await;
```

### 4. Stream Aggregation

Merge multiple streams into a single output:

```rust
let streams: Vec<_> = questions
    .into_iter()
    .map(|q| SafeDSpyStream::new(q, 100))
    .collect::<Result<_, _>>()?;

let merged = aggregate_streams(streams);
```

### 5. Error Recovery

Automatic retry with exponential backoff:

```rust
let stream = SafeDSpyStream::with_retry(
    question,
    100,      // buffer size
    3,        // max retries
    Duration::from_secs(2), // base delay
)?;
```

### 6. Progress Indicators

Real-time progress display with indicatif:

```rust
let pb = ProgressBar::new_spinner();
pb.set_style(/* ... */);

while let Some(event) = stream.next().await {
    match event {
        StreamEvent::Token(token) => {
            pb.set_message(format!("Streaming: {}", token));
        }
        StreamEvent::Done => pb.finish_with_message("Complete!"),
        // ...
    }
}
```

## Usage

### Prerequisites

1. **Python Environment**: Python 3.9+ with DSPy installed
2. **API Keys**: Set environment variables for your LLM provider

```bash
# OpenAI
export OPENAI_API_KEY="your-key-here"

# Anthropic
export ANTHROPIC_API_KEY="your-key-here"
```

3. **Install DSPy**:
```bash
pip install dspy-ai
```

### Running the Examples

```bash
# Build the project
cargo build --release

# Run all examples
cargo run --release

# Run specific example modes
cargo run --release -- --mode simple
cargo run --release -- --mode concurrent
cargo run --release -- --mode aggregate
cargo run --release -- --mode recovery
```

### Example Output

**Simple Streaming**:
```
Question: Explain async programming in Rust

Answer: Async programming in Rust allows you to write concurrent code
that doesn't block threads. It uses Futures and the async/await syntax
to enable efficient I/O operations...

Duration: 2.456s
```

**Concurrent Streaming**:
```
Processing 3 questions concurrently...

Q1: What is Rust? [=====>              ] 35%
Q2: What is Python? [===========>      ] 67%
Q3: What is DSPy? [==================> ] 98%

All streams completed in 3.421s
Total tokens: 487
Average: 142 tokens/s
```

**Stream Aggregation**:
```
Merging 3 streams...

[Stream 1] Rust is a systems programming language...
[Stream 2] Python is a high-level interpreted language...
[Stream 3] DSPy is a framework for programming language models...

Aggregation complete: 3 responses, 2.891s
```

## Implementation Details

### Backpressure Management

The `SafeDSpyStream` uses bounded channels to prevent memory exhaustion:

- **Buffer Size**: Configurable (default: 100 tokens)
- **Blocking Behavior**: Python side blocks when buffer is full
- **Consumer Control**: Slow consumers naturally throttle producers

### Error Handling

Three-tier error strategy:

1. **Python Errors**: Wrapped in `StreamEvent::Error`
2. **Channel Errors**: Automatic recovery or graceful shutdown
3. **Task Errors**: Propagated with context preservation

### Thread Safety

- **Python GIL**: Acquired only in `spawn_blocking` threads
- **No Tokio Blocking**: All Python calls offloaded to thread pool
- **Send + Sync**: All types can be safely shared across threads

### Performance Characteristics

- **Latency**: ~50-100ms for first token (network dependent)
- **Throughput**: ~200-500 tokens/s (model dependent)
- **Memory**: O(buffer_size) per stream
- **CPU**: Minimal overhead (~1-2% per stream)

## Configuration

### Stream Configuration

```rust
pub struct StreamConfig {
    pub buffer_size: usize,           // Token buffer (default: 100)
    pub max_retries: u32,             // Retry attempts (default: 3)
    pub retry_delay: Duration,        // Base delay (default: 2s)
    pub timeout: Option<Duration>,    // Per-stream timeout
}
```

### DSPy Configuration

```rust
// In your application initialization
Python::with_gil(|py| {
    let dspy = py.import("dspy")?;

    // Configure LM with streaming support
    let kwargs = PyDict::new(py);
    kwargs.set_item("model", "gpt-3.5-turbo")?;
    kwargs.set_item("stream", true)?;

    let lm = dspy.getattr("OpenAI")?.call((), Some(kwargs))?;
    dspy.getattr("settings")?.call_method1("configure", (lm,))?;
});
```

## Testing

Run the test suite:

```bash
cargo test

# With output
cargo test -- --nocapture

# Specific test
cargo test test_safe_stream_basic
```

## Troubleshooting

### Stream Hangs

**Problem**: Stream starts but never completes
**Solutions**:
- Check if DSPy model supports streaming
- Verify `stream=true` in LM configuration
- Check for Python errors in stderr

### High Memory Usage

**Problem**: Memory grows unbounded
**Solutions**:
- Use `SafeDSpyStream` instead of `DSpyStream`
- Reduce buffer size
- Ensure consumers keep up with producers

### Missing Tokens

**Problem**: Tokens appear to be skipped
**Solutions**:
- Flush stdout after each token
- Check terminal buffering settings
- Verify channel is not dropping messages

### Python GIL Deadlock

**Problem**: Application hangs with multiple streams
**Solutions**:
- Always use `spawn_blocking` for Python calls
- Never acquire GIL from Tokio runtime threads
- Limit concurrent stream count

## Advanced Patterns

### Custom Token Processing

```rust
let stream = SafeDSpyStream::new(question, 100)?;
let mut stream = stream.into_stream();

let processed = stream
    .filter_map(|event| match event {
        StreamEvent::Token(token) => {
            // Custom processing
            Some(token.to_uppercase())
        }
        _ => None,
    })
    .collect::<Vec<_>>()
    .await;
```

### Rate-Limited Streaming

```rust
use tokio::time::{sleep, Duration};

let stream = SafeDSpyStream::new(question, 100)?;
let mut stream = stream.into_stream();

while let Some(event) = stream.next().await {
    match event {
        StreamEvent::Token(token) => {
            print!("{}", token);
            sleep(Duration::from_millis(50)).await; // Throttle
        }
        _ => {}
    }
}
```

### Stream to File

```rust
use tokio::fs::File;
use tokio::io::AsyncWriteExt;

let mut file = File::create("output.txt").await?;
let stream = SafeDSpyStream::new(question, 100)?;
let mut stream = stream.into_stream();

while let Some(event) = stream.next().await {
    if let StreamEvent::Token(token) = event {
        file.write_all(token.as_bytes()).await?;
    }
}
```

## Best Practices

1. **Always use bounded channels** in production (`SafeDSpyStream`)
2. **Set appropriate timeouts** to prevent hung streams
3. **Handle all StreamEvent variants** explicitly
4. **Flush stdout** after printing tokens for real-time display
5. **Limit concurrent streams** to avoid overwhelming the API
6. **Monitor memory usage** with many concurrent streams
7. **Implement retry logic** for transient errors
8. **Log stream lifecycle** events for debugging

## Performance Tips

1. **Buffer Sizing**: Larger buffers (100-1000) reduce blocking
2. **Concurrency**: Limit to 5-10 concurrent streams per API key
3. **Thread Pool**: Default Tokio blocking pool is sufficient
4. **Memory**: Each stream uses ~O(buffer_size * avg_token_length) bytes
5. **Network**: Enable HTTP/2 connection pooling in DSPy

## References

- [PyO3 Documentation](https://pyo3.rs/)
- [Tokio Documentation](https://tokio.rs/)
- [DSPy Framework](https://github.com/stanfordnlp/dspy)
- [Async Rust Book](https://rust-lang.github.io/async-book/)

## License

MIT
