# PyO3 DSPy Async and Streaming - Complete Reference

Comprehensive technical guide for async DSPy integration, streaming LLM responses, concurrent predictions, backpressure management, timeout handling, WebSocket patterns, and production async service architecture using PyO3 and Tokio.

## Table of Contents

1. [Async Runtime Integration](#async-runtime-integration)
2. [Streaming Patterns](#streaming-patterns)
3. [Concurrent LM Calls](#concurrent-lm-calls)
4. [Backpressure Management](#backpressure-management)
5. [Timeout and Cancellation](#timeout-and-cancellation)
6. [WebSocket Integration](#websocket-integration)
7. [Production Service Patterns](#production-service-patterns)
8. [Monitoring and Observability](#monitoring-and-observability)
9. [Error Handling](#error-handling)
10. [Best Practices Summary](#best-practices-summary)

---

## Async Runtime Integration

### Dependencies Setup

**Cargo.toml for async PyO3-DSPy projects**:

```toml
[package]
name = "dspy-async-service"
version = "0.1.0"
edition = "2021"

[dependencies]
# PyO3 with async support
pyo3 = { version = "0.20", features = ["auto-initialize", "abi3-py39"] }
pyo3-asyncio = { version = "0.20", features = ["tokio-runtime"] }

# Async runtime
tokio = { version = "1.35", features = ["full"] }
tokio-stream = "0.1"
futures = "0.3"

# Serialization
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# Error handling
anyhow = "1.0"
thiserror = "1.0"

# Logging
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }

# WebSocket support
tokio-tungstenite = "0.21"

# Web framework
axum = { version = "0.7", features = ["ws"] }
tower = "0.4"
tower-http = { version = "0.5", features = ["cors", "trace"] }

# Utilities
once_cell = "1.19"
```

### Basic Tokio-Asyncio Bridge

**Pattern 1: Simple async call**:

```rust
use pyo3::prelude::*;
use pyo3_asyncio::tokio::{future_into_py, into_future};
use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize Python interpreter
    pyo3::prepare_freethreaded_python();

    let answer = simple_async_predict("What is Rust?").await?;
    println!("Answer: {}", answer);

    Ok(())
}

async fn simple_async_predict(question: &str) -> Result<String> {
    Python::with_gil(|py| {
        let dspy = py.import("dspy")?;

        // Create predictor
        let predictor = dspy
            .getattr("Predict")?
            .call1(("question -> answer",))?;

        // Call predictor (synchronous for now)
        let result = predictor.call_method1("__call__", (question,))?;

        let answer: String = result.getattr("answer")?.extract()?;
        Ok(answer)
    })
}
```

**Pattern 2: Non-blocking async with spawn_blocking**:

```rust
use pyo3::prelude::*;
use tokio::task;
use anyhow::Result;

async fn async_predict_nonblocking(question: String) -> Result<String> {
    // Offload to blocking thread pool to avoid blocking Tokio runtime
    task::spawn_blocking(move || {
        Python::with_gil(|py| {
            let dspy = py.import("dspy")?;

            let predictor = dspy
                .getattr("Predict")?
                .call1(("question -> answer",))?;

            let result = predictor.call_method1("__call__", (&question,))?;
            let answer: String = result.getattr("answer")?.extract()?;

            Ok::<_, PyErr>(answer)
        })
    })
    .await?
    .map_err(Into::into)
}

#[tokio::main]
async fn main() -> Result<()> {
    pyo3::prepare_freethreaded_python();

    // Multiple concurrent calls without blocking
    let handles = vec![
        tokio::spawn(async_predict_nonblocking("What is Rust?".to_string())),
        tokio::spawn(async_predict_nonblocking("What is Python?".to_string())),
        tokio::spawn(async_predict_nonblocking("What is DSPy?".to_string())),
    ];

    for handle in handles {
        let answer = handle.await??;
        println!("Answer: {}", answer);
    }

    Ok(())
}
```

**Best Practice**: Always use `spawn_blocking` for Python GIL acquisition in async contexts to prevent blocking the Tokio runtime.

### Async DSPy Module Wrapper

**Complete async-safe wrapper**:

```rust
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::sync::RwLock;
use anyhow::Result;

pub struct AsyncDSpyModule {
    module: Arc<RwLock<Py<PyAny>>>,
}

impl AsyncDSpyModule {
    pub fn new(signature: &str) -> Result<Self> {
        let module = Python::with_gil(|py| {
            let dspy = py.import("dspy")?;
            let predict = dspy.getattr("Predict")?;
            let module = predict.call1((signature,))?;
            Ok::<_, PyErr>(Py::from(module))
        })?;

        Ok(Self {
            module: Arc::new(RwLock::new(module)),
        })
    }

    pub async fn predict(&self, input: String) -> Result<String> {
        let module = self.module.read().await.clone();

        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                let result = module.as_ref(py)
                    .call_method1("__call__", (input,))?;
                let answer: String = result.getattr("answer")?.extract()?;
                Ok::<_, PyErr>(answer)
            })
        })
        .await?
        .map_err(Into::into)
    }

    pub async fn predict_structured<T: serde::de::DeserializeOwned>(
        &self,
        input: String,
    ) -> Result<T> {
        let module = self.module.read().await.clone();

        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                let result = module.as_ref(py)
                    .call_method1("__call__", (input,))?;

                // Extract as JSON and deserialize
                let json_str: String = result.call_method0("json")?.extract()?;
                let data: T = serde_json::from_str(&json_str)?;

                Ok::<_, anyhow::Error>(data)
            })
        })
        .await?
    }
}

// Clone support for sharing across tasks
impl Clone for AsyncDSpyModule {
    fn clone(&self) -> Self {
        Self {
            module: Arc::clone(&self.module),
        }
    }
}
```

**Usage**:

```rust
#[tokio::main]
async fn main() -> Result<()> {
    pyo3::prepare_freethreaded_python();

    let module = AsyncDSpyModule::new("question -> answer")?;

    // Can be cloned and shared across tasks
    let module_clone = module.clone();
    let handle = tokio::spawn(async move {
        module_clone.predict("What is async Rust?".to_string()).await
    });

    let answer = handle.await??;
    println!("Answer: {}", answer);

    Ok(())
}
```

---

## Streaming Patterns

### Token Streaming

**Basic token-by-token streaming**:

```rust
use pyo3::prelude::*;
use tokio::sync::mpsc;
use tokio_stream::wrappers::UnboundedReceiverStream;
use futures::stream::Stream;
use anyhow::Result;

pub struct TokenStream {
    receiver: mpsc::UnboundedReceiver<String>,
}

impl TokenStream {
    pub fn new(question: String) -> Result<Self> {
        let (tx, rx) = mpsc::unbounded_channel();

        // Spawn blocking task for Python streaming
        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                if let Err(e) = stream_tokens(py, &question, tx) {
                    eprintln!("Streaming error: {}", e);
                }
            })
        });

        Ok(Self { receiver: rx })
    }

    pub fn into_stream(self) -> impl Stream<Item = String> {
        UnboundedReceiverStream::new(self.receiver)
    }
}

fn stream_tokens(
    py: Python,
    question: &str,
    tx: mpsc::UnboundedSender<String>,
) -> PyResult<()> {
    // Import DSPy
    let dspy = py.import("dspy")?;

    // Configure streaming LM (OpenAI example)
    let openai_cls = dspy.getattr("OpenAI")?;

    let kwargs = pyo3::types::PyDict::new(py);
    kwargs.set_item("model", "gpt-3.5-turbo")?;
    kwargs.set_item("stream", true)?;

    let lm = openai_cls.call((), Some(kwargs))?;

    dspy.getattr("settings")?
        .call_method1("configure", (lm,))?;

    // Create predictor
    let predictor = dspy
        .getattr("Predict")?
        .call1(("question -> answer",))?;

    // Call and get streaming response
    let result = predictor.call_method1("__call__", (question,))?;

    // Stream tokens if available
    if let Ok(stream_iter) = result.getattr("stream") {
        for token_result in stream_iter.iter()? {
            let token: String = token_result?.extract()?;
            if tx.send(token).is_err() {
                break; // Receiver dropped
            }
        }
    }

    Ok(())
}
```

**Usage**:

```rust
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<()> {
    pyo3::prepare_freethreaded_python();

    let stream = TokenStream::new("Explain async programming".to_string())?;
    let mut stream = stream.into_stream();

    print!("Answer: ");
    while let Some(token) = stream.next().await {
        print!("{}", token);
        tokio::io::AsyncWriteExt::flush(&mut tokio::io::stdout()).await?;
    }
    println!();

    Ok(())
}
```

### Chunk Streaming

**Stream larger chunks instead of tokens**:

```rust
use std::time::Duration;
use tokio::time::sleep;

pub struct ChunkStream {
    receiver: mpsc::Receiver<String>,
}

impl ChunkStream {
    pub fn new(question: String, chunk_size: usize) -> Result<Self> {
        let (tx, rx) = mpsc::channel(10); // Bounded channel

        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                stream_chunks(py, &question, chunk_size, tx)
            })
        });

        Ok(Self { receiver: rx })
    }

    pub async fn next_chunk(&mut self) -> Option<String> {
        self.receiver.recv().await
    }
}

fn stream_chunks(
    py: Python,
    question: &str,
    chunk_size: usize,
    tx: mpsc::Sender<String>,
) -> Result<()> {
    // Setup streaming DSPy
    let dspy = py.import("dspy")?;

    // Configure streaming...
    let predictor = dspy
        .getattr("Predict")?
        .call1(("question -> answer",))?;

    let result = predictor.call_method1("__call__", (question,))?;

    if let Ok(stream_iter) = result.getattr("stream") {
        let mut chunk = String::new();

        for token_result in stream_iter.iter()? {
            let token: String = token_result?.extract()?;
            chunk.push_str(&token);

            // Send chunk when it reaches size
            if chunk.len() >= chunk_size {
                if tx.blocking_send(chunk.clone()).is_err() {
                    break;
                }
                chunk.clear();
            }
        }

        // Send remaining chunk
        if !chunk.is_empty() {
            let _ = tx.blocking_send(chunk);
        }
    }

    Ok(())
}
```

### Server-Sent Events (SSE) Streaming

**SSE pattern for web streaming**:

```rust
use axum::{
    response::sse::{Event, Sse},
    routing::post,
    Json, Router,
};
use futures::stream::{self, Stream};
use serde::Deserialize;
use std::convert::Infallible;
use std::time::Duration;

#[derive(Deserialize)]
struct StreamRequest {
    question: String,
}

async fn sse_stream_handler(
    Json(req): Json<StreamRequest>,
) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let stream = create_sse_stream(req.question);
    Sse::new(stream).keep_alive(
        axum::response::sse::KeepAlive::new()
            .interval(Duration::from_secs(1))
            .text("keep-alive-text"),
    )
}

fn create_sse_stream(
    question: String,
) -> impl Stream<Item = Result<Event, Infallible>> {
    let (tx, mut rx) = mpsc::unbounded_channel::<String>();

    // Spawn streaming task
    tokio::task::spawn_blocking(move || {
        Python::with_gil(|py| {
            let _ = stream_tokens(py, &question, tx);
        })
    });

    // Convert to SSE events
    async_stream::stream! {
        while let Some(token) = rx.recv().await {
            yield Ok(Event::default().data(token));
        }
        yield Ok(Event::default().data("[DONE]"));
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let app = Router::new()
        .route("/stream", post(sse_stream_handler));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
    println!("SSE server on http://0.0.0.0:3000/stream");

    axum::serve(listener, app).await?;

    Ok(())
}
```

**Best Practice**: Use SSE for browser-based streaming, WebSocket for bidirectional communication.

---

## Concurrent LM Calls

### Parallel Predictions

**Pattern 1: JoinSet for dynamic concurrency**:

```rust
use tokio::task::JoinSet;
use std::sync::Arc;

pub struct ConcurrentPredictor {
    module: Arc<AsyncDSpyModule>,
}

impl ConcurrentPredictor {
    pub fn new(signature: &str) -> Result<Self> {
        let module = AsyncDSpyModule::new(signature)?;
        Ok(Self {
            module: Arc::new(module),
        })
    }

    pub async fn batch_predict(&self, questions: Vec<String>) -> Result<Vec<String>> {
        let mut set = JoinSet::new();

        for question in questions {
            let module = Arc::clone(&self.module);
            set.spawn(async move {
                module.predict(question).await
            });
        }

        let mut results = Vec::new();
        while let Some(result) = set.join_next().await {
            results.push(result??);
        }

        Ok(results)
    }
}
```

**Pattern 2: Ordered concurrent execution**:

```rust
use futures::future::join_all;

pub async fn batch_predict_ordered(
    module: &AsyncDSpyModule,
    questions: Vec<String>,
) -> Result<Vec<String>> {
    let futures: Vec<_> = questions
        .into_iter()
        .map(|q| module.predict(q))
        .collect();

    let results = join_all(futures).await;

    // Collect results, propagating first error
    results.into_iter().collect()
}
```

**Pattern 3: Concurrent with error collection**:

```rust
pub async fn batch_predict_with_errors(
    module: &AsyncDSpyModule,
    questions: Vec<String>,
) -> Vec<Result<String>> {
    let futures: Vec<_> = questions
        .into_iter()
        .map(|q| async move { module.predict(q).await })
        .collect();

    join_all(futures).await
}

// Usage: handle errors individually
#[tokio::main]
async fn main() -> Result<()> {
    let module = AsyncDSpyModule::new("question -> answer")?;

    let questions = vec![
        "Valid question 1".to_string(),
        "Valid question 2".to_string(),
        "Invalid question".to_string(),
    ];

    let results = batch_predict_with_errors(&module, questions).await;

    for (i, result) in results.iter().enumerate() {
        match result {
            Ok(answer) => println!("Q{}: {}", i + 1, answer),
            Err(e) => eprintln!("Q{} failed: {}", i + 1, e),
        }
    }

    Ok(())
}
```

### Rate-Limited Concurrency

**Semaphore-based rate limiting**:

```rust
use tokio::sync::Semaphore;
use std::sync::Arc;

pub struct RateLimitedPredictor {
    module: Arc<AsyncDSpyModule>,
    semaphore: Arc<Semaphore>,
}

impl RateLimitedPredictor {
    pub fn new(signature: &str, max_concurrent: usize) -> Result<Self> {
        let module = AsyncDSpyModule::new(signature)?;

        Ok(Self {
            module: Arc::new(module),
            semaphore: Arc::new(Semaphore::new(max_concurrent)),
        })
    }

    pub async fn predict(&self, question: String) -> Result<String> {
        // Acquire permit (blocks if at limit)
        let _permit = self.semaphore.acquire().await?;

        // Predict with permit held
        self.module.predict(question).await
    }

    pub async fn batch_predict(
        &self,
        questions: Vec<String>,
    ) -> Result<Vec<String>> {
        let mut set = JoinSet::new();

        for question in questions {
            let predictor = self.clone();
            set.spawn(async move {
                predictor.predict(question).await
            });
        }

        let mut results = Vec::new();
        while let Some(result) = set.join_next().await {
            results.push(result??);
        }

        Ok(results)
    }
}

impl Clone for RateLimitedPredictor {
    fn clone(&self) -> Self {
        Self {
            module: Arc::clone(&self.module),
            semaphore: Arc::clone(&self.semaphore),
        }
    }
}
```

**Usage with rate limiting**:

```rust
#[tokio::main]
async fn main() -> Result<()> {
    pyo3::prepare_freethreaded_python();

    // Max 5 concurrent LM calls
    let predictor = RateLimitedPredictor::new("question -> answer", 5)?;

    let questions: Vec<String> = (0..20)
        .map(|i| format!("Question number {}", i))
        .collect();

    let start = std::time::Instant::now();
    let answers = predictor.batch_predict(questions).await?;
    let duration = start.elapsed();

    println!("Processed {} questions in {:?}", answers.len(), duration);
    println!("Average: {:?} per question", duration / answers.len() as u32);

    Ok(())
}
```

**Best Practice**: Set rate limits based on API quotas (e.g., OpenAI: 60 RPM → 1 per second).

### Adaptive Concurrency

**Dynamically adjust concurrency based on latency**:

```rust
use std::sync::atomic::{AtomicUsize, Ordering};
use tokio::time::Instant;

pub struct AdaptivePredictor {
    module: Arc<AsyncDSpyModule>,
    semaphore: Arc<Semaphore>,
    max_concurrent: Arc<AtomicUsize>,
}

impl AdaptivePredictor {
    pub fn new(signature: &str, initial_concurrency: usize) -> Result<Self> {
        let module = AsyncDSpyModule::new(signature)?;

        Ok(Self {
            module: Arc::new(module),
            semaphore: Arc::new(Semaphore::new(initial_concurrency)),
            max_concurrent: Arc::new(AtomicUsize::new(initial_concurrency)),
        })
    }

    pub async fn predict_adaptive(&self, question: String) -> Result<(String, Duration)> {
        let _permit = self.semaphore.acquire().await?;

        let start = Instant::now();
        let answer = self.module.predict(question).await?;
        let latency = start.elapsed();

        // Adjust concurrency based on latency
        self.adjust_concurrency(latency);

        Ok((answer, latency))
    }

    fn adjust_concurrency(&self, latency: Duration) {
        let current = self.max_concurrent.load(Ordering::Relaxed);

        // Increase if fast (< 1s)
        if latency.as_secs() < 1 && current < 20 {
            self.max_concurrent.fetch_add(1, Ordering::Relaxed);
            self.semaphore.add_permits(1);
        }
        // Decrease if slow (> 5s)
        else if latency.as_secs() > 5 && current > 1 {
            self.max_concurrent.fetch_sub(1, Ordering::Relaxed);
            // Note: Cannot remove permits, but new acquisitions will be limited
        }
    }

    pub fn current_concurrency(&self) -> usize {
        self.max_concurrent.load(Ordering::Relaxed)
    }
}
```

---

## Backpressure Management

### Bounded Channels

**Pattern 1: Simple bounded backpressure**:

```rust
use tokio::sync::mpsc;

pub async fn stream_with_backpressure(
    question: String,
    buffer_size: usize,
) -> Result<mpsc::Receiver<String>> {
    let (tx, rx) = mpsc::channel(buffer_size);

    tokio::task::spawn_blocking(move || {
        Python::with_gil(|py| {
            stream_tokens_bounded(py, &question, tx)
        })
    });

    Ok(rx)
}

fn stream_tokens_bounded(
    py: Python,
    question: &str,
    tx: mpsc::Sender<String>,
) -> Result<()> {
    // Setup streaming DSPy...

    for token_result in stream_iter.iter()? {
        let token: String = token_result?.extract()?;

        // This blocks if buffer is full (backpressure!)
        if tx.blocking_send(token).is_err() {
            break; // Receiver dropped
        }
    }

    Ok(())
}
```

**Pattern 2: Timeout-based backpressure**:

```rust
use tokio::time::{timeout, Duration};

pub struct TimeoutBackpressure {
    sender: mpsc::Sender<String>,
    send_timeout: Duration,
}

impl TimeoutBackpressure {
    pub fn new(buffer_size: usize, send_timeout_ms: u64) -> (Self, mpsc::Receiver<String>) {
        let (tx, rx) = mpsc::channel(buffer_size);

        let bp = Self {
            sender: tx,
            send_timeout: Duration::from_millis(send_timeout_ms),
        };

        (bp, rx)
    }

    pub async fn send_with_timeout(&self, token: String) -> Result<()> {
        match timeout(self.send_timeout, self.sender.send(token)).await {
            Ok(Ok(_)) => Ok(()),
            Ok(Err(_)) => Err(anyhow::anyhow!("Receiver dropped")),
            Err(_) => Err(anyhow::anyhow!("Send timeout - consumer too slow")),
        }
    }
}
```

**Pattern 3: Drop-on-full strategy**:

```rust
pub struct DropOnFullStream {
    sender: mpsc::UnboundedSender<String>,
    dropped_count: Arc<AtomicUsize>,
}

impl DropOnFullStream {
    pub fn new() -> (Self, mpsc::UnboundedReceiver<String>) {
        let (tx, rx) = mpsc::unbounded_channel();

        let stream = Self {
            sender: tx,
            dropped_count: Arc::new(AtomicUsize::new(0)),
        };

        (stream, rx)
    }

    pub fn send_or_drop(&self, token: String) -> bool {
        match self.sender.send(token) {
            Ok(_) => true,
            Err(_) => {
                self.dropped_count.fetch_add(1, Ordering::Relaxed);
                false
            }
        }
    }

    pub fn dropped_count(&self) -> usize {
        self.dropped_count.load(Ordering::Relaxed)
    }
}
```

**Best Practice**: Use bounded channels for memory safety, unbounded only when drops are acceptable.

---

## Timeout and Cancellation

### Timeout Patterns

**Pattern 1: Simple timeout**:

```rust
use tokio::time::{timeout, Duration};

pub async fn predict_with_timeout(
    module: &AsyncDSpyModule,
    question: String,
    timeout_secs: u64,
) -> Result<String> {
    match timeout(
        Duration::from_secs(timeout_secs),
        module.predict(question),
    )
    .await
    {
        Ok(Ok(answer)) => Ok(answer),
        Ok(Err(e)) => Err(e),
        Err(_) => Err(anyhow::anyhow!("Prediction timeout after {}s", timeout_secs)),
    }
}
```

**Pattern 2: Cascading timeouts**:

```rust
pub struct TimeoutConfig {
    pub total_timeout: Duration,
    pub prediction_timeout: Duration,
    pub processing_timeout: Duration,
}

pub async fn predict_with_cascading_timeouts(
    module: &AsyncDSpyModule,
    question: String,
    config: TimeoutConfig,
) -> Result<String> {
    // Overall timeout
    timeout(config.total_timeout, async {
        // Prediction timeout
        let answer = timeout(
            config.prediction_timeout,
            module.predict(question),
        )
        .await??;

        // Post-processing timeout
        let processed = timeout(
            config.processing_timeout,
            post_process(answer),
        )
        .await??;

        Ok::<_, anyhow::Error>(processed)
    })
    .await?
}

async fn post_process(answer: String) -> Result<String> {
    // Expensive post-processing
    tokio::time::sleep(Duration::from_millis(100)).await;
    Ok(answer.trim().to_string())
}
```

### Cancellation Patterns

**Pattern 1: Token-based cancellation**:

```rust
use tokio::sync::oneshot;
use tokio::select;

pub struct CancellableTask {
    cancel_tx: Option<oneshot::Sender<()>>,
}

impl CancellableTask {
    pub fn spawn_cancellable(
        module: Arc<AsyncDSpyModule>,
        question: String,
    ) -> (Self, tokio::task::JoinHandle<Result<String>>) {
        let (cancel_tx, cancel_rx) = oneshot::channel();

        let handle = tokio::spawn(async move {
            select! {
                result = module.predict(question) => result,
                _ = cancel_rx => Err(anyhow::anyhow!("Task cancelled")),
            }
        });

        (Self { cancel_tx: Some(cancel_tx) }, handle)
    }

    pub fn cancel(mut self) {
        if let Some(tx) = self.cancel_tx.take() {
            let _ = tx.send(());
        }
    }
}

// Usage
#[tokio::main]
async fn main() -> Result<()> {
    let module = Arc::new(AsyncDSpyModule::new("question -> answer")?);

    let (task, handle) = CancellableTask::spawn_cancellable(
        module,
        "Long running question".to_string(),
    );

    // Cancel after 5 seconds
    tokio::spawn(async move {
        tokio::time::sleep(Duration::from_secs(5)).await;
        task.cancel();
    });

    match handle.await? {
        Ok(answer) => println!("Answer: {}", answer),
        Err(e) if e.to_string().contains("cancelled") => {
            println!("Task was cancelled");
        }
        Err(e) => eprintln!("Error: {}", e),
    }

    Ok(())
}
```

**Pattern 2: Abort handle cancellation**:

```rust
pub struct AbortableTask {
    handle: tokio::task::JoinHandle<Result<String>>,
}

impl AbortableTask {
    pub fn spawn(
        module: Arc<AsyncDSpyModule>,
        question: String,
    ) -> Self {
        let handle = tokio::spawn(async move {
            module.predict(question).await
        });

        Self { handle }
    }

    pub fn abort(self) {
        self.handle.abort();
    }

    pub async fn await_result(self) -> Result<String> {
        match self.handle.await {
            Ok(result) => result,
            Err(e) if e.is_cancelled() => Err(anyhow::anyhow!("Task aborted")),
            Err(e) => Err(anyhow::anyhow!("Task panic: {}", e)),
        }
    }
}
```

**Best Practice**: Use cancellation tokens for graceful shutdown, abort handles for immediate termination.

---

## WebSocket Integration

### WebSocket Server

**Complete WebSocket server with DSPy streaming**:

```rust
use axum::{
    extract::{ws::WebSocket, ws::WebSocketUpgrade, State},
    response::Response,
    routing::get,
    Router,
};
use futures::{SinkExt, StreamExt};
use std::sync::Arc;

#[derive(Clone)]
struct WsState {
    module: Arc<AsyncDSpyModule>,
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<WsState>,
) -> Response {
    ws.on_upgrade(|socket| handle_socket(socket, state))
}

async fn handle_socket(socket: WebSocket, state: WsState) {
    let (mut sender, mut receiver) = socket.split();

    while let Some(msg) = receiver.next().await {
        let msg = match msg {
            Ok(msg) => msg,
            Err(e) => {
                eprintln!("WebSocket error: {}", e);
                break;
            }
        };

        if let axum::extract::ws::Message::Text(question) = msg {
            // Stream DSPy response back
            let stream = match TokenStream::new(question) {
                Ok(s) => s,
                Err(e) => {
                    let _ = sender
                        .send(axum::extract::ws::Message::Text(
                            format!("Error: {}", e)
                        ))
                        .await;
                    continue;
                }
            };

            let mut stream = stream.into_stream();

            while let Some(token) = stream.next().await {
                if sender
                    .send(axum::extract::ws::Message::Text(token))
                    .await
                    .is_err()
                {
                    break; // Client disconnected
                }
            }

            // Send completion marker
            let _ = sender
                .send(axum::extract::ws::Message::Text("[DONE]".to_string()))
                .await;
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    pyo3::prepare_freethreaded_python();

    let state = WsState {
        module: Arc::new(AsyncDSpyModule::new("question -> answer")?),
    };

    let app = Router::new()
        .route("/ws", get(ws_handler))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
    println!("WebSocket server on ws://0.0.0.0:3000/ws");

    axum::serve(listener, app).await?;

    Ok(())
}
```

### WebSocket Client

**Async WebSocket client for DSPy**:

```rust
use tokio_tungstenite::{connect_async, tungstenite::Message};
use futures::{SinkExt, StreamExt};

pub struct DSpyWsClient {
    url: String,
}

impl DSpyWsClient {
    pub fn new(url: String) -> Self {
        Self { url }
    }

    pub async fn stream_predict(&self, question: String) -> Result<String> {
        let (ws_stream, _) = connect_async(&self.url).await?;
        let (mut write, mut read) = ws_stream.split();

        // Send question
        write.send(Message::Text(question)).await?;

        // Receive streamed response
        let mut full_response = String::new();

        while let Some(msg) = read.next().await {
            let msg = msg?;

            if let Message::Text(text) = msg {
                if text == "[DONE]" {
                    break;
                }

                print!("{}", text);
                use std::io::Write;
                std::io::stdout().flush()?;
                full_response.push_str(&text);
            }
        }

        println!(); // Newline
        Ok(full_response)
    }
}

// Usage
#[tokio::main]
async fn main() -> Result<()> {
    let client = DSpyWsClient::new("ws://localhost:3000/ws".to_string());

    let response = client
        .stream_predict("Explain WebSocket streaming".to_string())
        .await?;

    println!("\nFull response: {}", response);

    Ok(())
}
```

**Best Practice**: Use WebSocket for bidirectional real-time communication, SSE for unidirectional streaming.

---

## Production Service Patterns

### Complete Async Service Architecture

**Full-featured production service**:

```rust
use axum::{
    Router,
    extract::{State, Json},
    routing::{get, post},
    response::{sse::Event, Sse},
    http::StatusCode,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::{RwLock, Semaphore};
use tower_http::cors::CorsLayer;
use tracing::{info, error};

#[derive(Clone)]
struct AppState {
    predictor: Arc<AsyncDSpyModule>,
    semaphore: Arc<Semaphore>,
    metrics: Arc<Metrics>,
}

#[derive(Deserialize)]
struct PredictRequest {
    question: String,
    timeout_secs: Option<u64>,
}

#[derive(Serialize)]
struct PredictResponse {
    answer: String,
    duration_ms: u128,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt::init();

    // Initialize Python
    pyo3::prepare_freethreaded_python();

    // Configure DSPy
    configure_dspy_from_env()?;

    // Create state
    let state = AppState {
        predictor: Arc::new(AsyncDSpyModule::new("question -> answer")?),
        semaphore: Arc::new(Semaphore::new(10)), // Max 10 concurrent
        metrics: Arc::new(Metrics::new()),
    };

    // Build router
    let app = Router::new()
        .route("/health", get(health_handler))
        .route("/predict", post(predict_handler))
        .route("/predict/stream", post(predict_stream_handler))
        .route("/metrics", get(metrics_handler))
        .layer(CorsLayer::permissive())
        .with_state(state);

    // Start server
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
    info!("Server listening on http://0.0.0.0:3000");

    axum::serve(listener, app).await?;

    Ok(())
}

async fn health_handler() -> &'static str {
    "OK"
}

async fn predict_handler(
    State(state): State<AppState>,
    Json(req): Json<PredictRequest>,
) -> Result<Json<PredictResponse>, (StatusCode, Json<ErrorResponse>)> {
    // Acquire rate limit
    let _permit = state
        .semaphore
        .acquire()
        .await
        .map_err(|e| internal_error(format!("Rate limit error: {}", e)))?;

    // Track metrics
    state.metrics.start_request();
    let start = std::time::Instant::now();

    // Predict with timeout
    let timeout_secs = req.timeout_secs.unwrap_or(30);
    let answer = match predict_with_timeout(
        &state.predictor,
        req.question,
        timeout_secs,
    )
    .await
    {
        Ok(answer) => answer,
        Err(e) => {
            let duration_ms = start.elapsed().as_millis() as u64;
            state.metrics.end_request(duration_ms, true);
            return Err(internal_error(e.to_string()));
        }
    };

    let duration_ms = start.elapsed().as_millis();
    state.metrics.end_request(duration_ms as u64, false);

    Ok(Json(PredictResponse {
        answer,
        duration_ms,
    }))
}

async fn predict_stream_handler(
    State(state): State<AppState>,
    Json(req): Json<PredictRequest>,
) -> Sse<impl futures::stream::Stream<Item = Result<Event, std::convert::Infallible>>> {
    let stream = TokenStream::new(req.question)
        .expect("Failed to create stream");

    let stream = stream.into_stream().map(|token| {
        Ok(Event::default().data(token))
    });

    Sse::new(stream)
}

async fn metrics_handler(
    State(state): State<AppState>,
) -> Json<MetricsSnapshot> {
    Json(state.metrics.snapshot())
}

fn internal_error(message: String) -> (StatusCode, Json<ErrorResponse>) {
    error!("Error: {}", message);
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(ErrorResponse { error: message }),
    )
}

fn configure_dspy_from_env() -> Result<()> {
    Python::with_gil(|py| {
        let dspy = py.import("dspy")?;

        let provider = std::env::var("LM_PROVIDER")
            .unwrap_or_else(|_| "openai".to_string());
        let model = std::env::var("LM_MODEL")
            .unwrap_or_else(|_| "gpt-3.5-turbo".to_string());

        let lm_class = match provider.as_str() {
            "openai" => dspy.getattr("OpenAI")?,
            "anthropic" => dspy.getattr("Anthropic")?,
            _ => return Err(anyhow::anyhow!("Unknown provider: {}", provider)),
        };

        let lm = lm_class.call1((&model,))?;
        dspy.getattr("settings")?.call_method1("configure", (lm,))?;

        Ok(())
    })
}
```

**Best Practice**: Separate concerns (routing, business logic, metrics) for maintainability.

---

## Monitoring and Observability

### Metrics Collection

**Complete metrics system**:

```rust
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use serde::Serialize;

#[derive(Clone)]
pub struct Metrics {
    total_requests: Arc<AtomicU64>,
    active_requests: Arc<AtomicU64>,
    total_errors: Arc<AtomicU64>,
    total_duration_ms: Arc<AtomicU64>,
    total_timeouts: Arc<AtomicU64>,
}

#[derive(Serialize)]
pub struct MetricsSnapshot {
    pub total_requests: u64,
    pub active_requests: u64,
    pub total_errors: u64,
    pub average_duration_ms: u64,
    pub total_timeouts: u64,
    pub error_rate: f64,
}

impl Metrics {
    pub fn new() -> Self {
        Self {
            total_requests: Arc::new(AtomicU64::new(0)),
            active_requests: Arc::new(AtomicU64::new(0)),
            total_errors: Arc::new(AtomicU64::new(0)),
            total_duration_ms: Arc::new(AtomicU64::new(0)),
            total_timeouts: Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn start_request(&self) {
        self.total_requests.fetch_add(1, Ordering::Relaxed);
        self.active_requests.fetch_add(1, Ordering::Relaxed);
    }

    pub fn end_request(&self, duration_ms: u64, is_error: bool) {
        self.active_requests.fetch_sub(1, Ordering::Relaxed);
        self.total_duration_ms.fetch_add(duration_ms, Ordering::Relaxed);

        if is_error {
            self.total_errors.fetch_add(1, Ordering::Relaxed);
        }
    }

    pub fn record_timeout(&self) {
        self.total_timeouts.fetch_add(1, Ordering::Relaxed);
    }

    pub fn snapshot(&self) -> MetricsSnapshot {
        let total = self.total_requests.load(Ordering::Relaxed);
        let active = self.active_requests.load(Ordering::Relaxed);
        let errors = self.total_errors.load(Ordering::Relaxed);
        let duration = self.total_duration_ms.load(Ordering::Relaxed);
        let timeouts = self.total_timeouts.load(Ordering::Relaxed);

        let avg_ms = if total > 0 { duration / total } else { 0 };
        let error_rate = if total > 0 {
            errors as f64 / total as f64
        } else {
            0.0
        };

        MetricsSnapshot {
            total_requests: total,
            active_requests: active,
            total_errors: errors,
            average_duration_ms: avg_ms,
            total_timeouts: timeouts,
            error_rate,
        }
    }

    pub fn report(&self) {
        let snapshot = self.snapshot();

        println!("=== Metrics ===");
        println!("Total requests: {}", snapshot.total_requests);
        println!("Active requests: {}", snapshot.active_requests);
        println!("Total errors: {}", snapshot.total_errors);
        println!("Total timeouts: {}", snapshot.total_timeouts);
        println!("Average duration: {}ms", snapshot.average_duration_ms);
        println!("Error rate: {:.2}%", snapshot.error_rate * 100.0);
    }
}
```

**Usage with monitoring**:

```rust
pub async fn predict_with_monitoring(
    module: &AsyncDSpyModule,
    question: String,
    metrics: Arc<Metrics>,
) -> Result<String> {
    metrics.start_request();
    let start = std::time::Instant::now();

    let result = module.predict(question).await;

    let duration_ms = start.elapsed().as_millis() as u64;
    metrics.end_request(duration_ms, result.is_err());

    result
}
```

---

## Error Handling

### Async Error Types

**Complete error hierarchy**:

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AsyncDSpyError {
    #[error("Python error: {0}")]
    Python(#[from] PyErr),

    #[error("Timeout after {0:?}")]
    Timeout(Duration),

    #[error("Task cancelled")]
    Cancelled,

    #[error("Rate limit exceeded")]
    RateLimit,

    #[error("Stream error: {0}")]
    Stream(String),

    #[error("Channel closed")]
    ChannelClosed,

    #[error("Join error: {0}")]
    Join(#[from] tokio::task::JoinError),

    #[error("Semaphore error: {0}")]
    Semaphore(#[from] tokio::sync::AcquireError),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    Serde(#[from] serde_json::Error),

    #[error("Configuration error: {0}")]
    Config(String),
}

pub type AsyncResult<T> = std::result::Result<T, AsyncDSpyError>;
```

**Error recovery patterns**:

```rust
pub async fn predict_with_retry(
    module: &AsyncDSpyModule,
    question: String,
    max_retries: u32,
) -> AsyncResult<String> {
    let mut attempt = 0;
    let mut last_error = None;

    while attempt <= max_retries {
        match module.predict(question.clone()).await {
            Ok(answer) => return Ok(answer),
            Err(e) => {
                last_error = Some(e);

                if attempt < max_retries {
                    let delay = Duration::from_secs(2_u64.pow(attempt));
                    tracing::warn!(
                        "Attempt {} failed, retrying in {:?}",
                        attempt + 1,
                        delay
                    );
                    tokio::time::sleep(delay).await;
                }

                attempt += 1;
            }
        }
    }

    Err(AsyncDSpyError::Config(format!(
        "Failed after {} retries: {:?}",
        max_retries,
        last_error
    )))
}
```

---

## Best Practices Summary

### Runtime Integration

✅ **DO**:
- Use `pyo3::prepare_freethreaded_python()` for async contexts
- Always use `spawn_blocking` for Python GIL acquisition
- Cache Python objects in `Arc<RwLock<Py<PyAny>>>`
- Release GIL before async operations

❌ **DON'T**:
- Block Tokio runtime with long GIL holds
- Mix sync and async without spawn_blocking
- Forget to initialize Python interpreter
- Create new Python objects on every call

### Streaming

✅ **DO**:
- Use bounded channels for memory safety
- Implement proper error handling in streams
- Send completion markers ([DONE])
- Handle receiver disconnection gracefully

❌ **DON'T**:
- Use unbounded channels without backpressure
- Ignore stream errors
- Block on send without timeout
- Leak stream resources

### Concurrency

✅ **DO**:
- Apply rate limiting with semaphores
- Set maximum concurrency limits
- Monitor active task count
- Use JoinSet for dynamic task management

❌ **DON'T**:
- Allow unlimited concurrent requests
- Ignore API rate limits
- Skip error handling in concurrent tasks
- Create unbounded task spawns

### Timeouts

✅ **DO**:
- Set timeouts on all LM calls (30s default)
- Implement cascading timeouts
- Log timeout events
- Provide timeout configuration

❌ **DON'T**:
- Allow operations to hang indefinitely
- Use same timeout for all operations
- Ignore timeout errors
- Skip timeout testing

### Production

✅ **DO**:
- Implement comprehensive metrics
- Use structured logging
- Provide health check endpoints
- Configure from environment variables
- Test under load

❌ **DON'T**:
- Deploy without monitoring
- Skip error tracking
- Hardcode configuration
- Ignore resource limits
- Skip load testing

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
