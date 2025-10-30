---
name: pyo3-dspy-async-streaming
description: Async LM calls and streaming with DSPy from Rust - Tokio/asyncio integration, streaming predictions, concurrent LM calls
skill_id: rust-pyo3-dspy-async-streaming
title: PyO3 DSPy Async and Streaming
category: rust
subcategory: pyo3-dspy
complexity: advanced
prerequisites:
  - rust-pyo3-dspy-fundamentals
  - rust-pyo3-async-embedded-wasm
  - rust-async-tokio
tags:
  - rust
  - python
  - pyo3
  - dspy
  - async
  - streaming
  - tokio
  - asyncio
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Bridge Tokio and asyncio for async DSPy calls
  - Stream LLM responses from DSPy to Rust
  - Execute concurrent DSPy predictions efficiently
  - Implement backpressure handling for streaming
  - Apply timeout and cancellation patterns
  - Build real-time DSPy services with WebSockets
related_skills:
  - rust-pyo3-dspy-fundamentals
  - rust-async-tokio
  - rust-pyo3-async-embedded-wasm
  - ml-dspy-production
resources:
  - REFERENCE.md (900+ lines): Comprehensive async guide
  - 3 Python scripts (900+ lines): Async testing, streaming, monitoring
  - 7 Rust+Python examples (1,400+ lines): Working async code
---

# PyO3 DSPy Async and Streaming

## Overview

Master asynchronous DSPy calls and streaming LLM responses from Rust. Learn to bridge Tokio and asyncio runtimes, handle streaming predictions, execute concurrent LM calls, manage backpressure, and build production-ready real-time AI services.

This skill is critical for production systems that need high throughput, low latency, and efficient resource utilization when calling DSPy from Rust. You'll learn the patterns that power real-world AI services serving thousands of concurrent requests.

## Prerequisites

**Required**:
- PyO3 DSPy fundamentals (module calls, error handling)
- Tokio fundamentals (async/await, tasks, channels)
- Understanding of async Rust patterns
- Python asyncio basics
- DSPy installed and configured

**Recommended**:
- Experience with streaming APIs
- Knowledge of backpressure handling
- WebSocket fundamentals
- Production async service design

## When to Use

**Ideal for**:
- **High-throughput AI services** serving many concurrent requests
- **Real-time streaming** LLM responses to users
- **Low-latency applications** where blocking is unacceptable
- **WebSocket-based AI services** with live updates
- **Concurrent batch processing** of multiple LM calls
- **Long-running LLM operations** that need cancellation
- **Production APIs** requiring timeout handling

**Not ideal for**:
- Simple synchronous scripts (adds complexity)
- Single-request CLI tools
- Prototypes where performance isn't critical
- Applications without concurrent workloads

## Learning Path

### 1. Tokio ↔ Asyncio Integration

The fundamental challenge: bridging two different async runtimes (Rust's Tokio and Python's asyncio).

**Setup Dependencies**:

```toml
[dependencies]
pyo3 = { version = "0.20", features = ["auto-initialize"] }
pyo3-asyncio = { version = "0.20", features = ["tokio-runtime"] }
tokio = { version = "1.35", features = ["full"] }
futures = "0.3"
anyhow = "1.0"
```

**Basic Async DSPy Call**:

```rust
use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize Python with asyncio support
    pyo3::prepare_freethreaded_python();

    let result = async_dspy_call("What is Rust?").await?;
    println!("Answer: {}", result);

    Ok(())
}

async fn async_dspy_call(question: &str) -> Result<String> {
    Python::with_gil(|py| {
        // Import DSPy
        let dspy = py.import("dspy")?;

        // Create predictor
        let predictor = dspy
            .getattr("Predict")?
            .call1(("question -> answer",))?;

        // Convert Python coroutine to Rust future
        let fut = pyo3_asyncio::tokio::into_future(
            predictor.call_method1("__call__", (question,))?
        )?;

        Ok(fut)
    })?
    .await?;

    // Extract answer
    Python::with_gil(|py| {
        let answer: String = result.getattr(py, "answer")?.extract(py)?;
        Ok(answer)
    })
}
```

**Key Pattern**: Use `pyo3_asyncio::tokio::into_future()` to convert Python coroutines to Rust futures.

### 2. Streaming Predictions

Stream token-by-token responses from LLMs through DSPy to Rust.

**Streaming Architecture**:

```rust
use pyo3::prelude::*;
use tokio::sync::mpsc;
use futures::stream::{Stream, StreamExt};
use anyhow::Result;

/// Stream tokens from a DSPy prediction
pub struct DSpyStream {
    receiver: mpsc::UnboundedReceiver<String>,
}

impl DSpyStream {
    /// Create a new streaming prediction
    pub fn new(question: String) -> Result<Self> {
        let (tx, rx) = mpsc::unbounded_channel();

        // Spawn task to handle Python streaming
        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                let result = stream_prediction(py, &question, tx);
                if let Err(e) = result {
                    eprintln!("Streaming error: {}", e);
                }
            })
        });

        Ok(Self { receiver: rx })
    }

    /// Convert to stream
    pub fn into_stream(self) -> impl Stream<Item = String> {
        tokio_stream::wrappers::UnboundedReceiverStream::new(self.receiver)
    }
}

fn stream_prediction(
    py: Python,
    question: &str,
    tx: mpsc::UnboundedSender<String>,
) -> PyResult<()> {
    // Import streaming-capable LM
    let dspy = py.import("dspy")?;
    let openai = py.import("dspy.utils.openai")?;

    // Configure for streaming
    let kwargs = pyo3::types::PyDict::new(py);
    kwargs.set_item("stream", true)?;

    let lm = openai
        .getattr("OpenAI")?
        .call((), Some(kwargs))?;

    dspy.getattr("settings")?
        .call_method1("configure", (lm,))?;

    // Create predictor
    let predictor = dspy
        .getattr("Predict")?
        .call1(("question -> answer",))?;

    // Get streaming iterator
    let result = predictor.call_method1("__call__", (question,))?;
    let stream = result.getattr("stream")?;

    // Iterate tokens
    for token_result in stream.iter()? {
        let token: String = token_result?.extract()?;
        if tx.send(token).is_err() {
            break; // Receiver dropped
        }
    }

    Ok(())
}

// Usage
#[tokio::main]
async fn main() -> Result<()> {
    let stream = DSpyStream::new("Explain async Rust".to_string())?;
    let mut stream = stream.into_stream();

    print!("Answer: ");
    while let Some(token) = stream.next().await {
        print!("{}", token);
        tokio::io::stdout().flush().await?;
    }
    println!();

    Ok(())
}
```

**Streaming with Error Handling**:

```rust
use tokio::sync::mpsc;
use anyhow::{Result, Context};

#[derive(Debug)]
pub enum StreamEvent {
    Token(String),
    Done(String), // Full response
    Error(String),
}

pub struct SafeDSpyStream {
    receiver: mpsc::UnboundedReceiver<StreamEvent>,
}

impl SafeDSpyStream {
    pub fn new(question: String) -> Self {
        let (tx, rx) = mpsc::unbounded_channel();

        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                match stream_with_errors(py, &question, tx.clone()) {
                    Ok(full_text) => {
                        let _ = tx.send(StreamEvent::Done(full_text));
                    }
                    Err(e) => {
                        let _ = tx.send(StreamEvent::Error(e.to_string()));
                    }
                }
            })
        });

        Self { receiver: rx }
    }

    pub async fn collect_all(&mut self) -> Result<String> {
        let mut full_text = String::new();

        while let Some(event) = self.receiver.recv().await {
            match event {
                StreamEvent::Token(token) => {
                    print!("{}", token);
                    full_text.push_str(&token);
                }
                StreamEvent::Done(text) => {
                    return Ok(text);
                }
                StreamEvent::Error(e) => {
                    return Err(anyhow::anyhow!("Stream error: {}", e));
                }
            }
        }

        Ok(full_text)
    }
}

fn stream_with_errors(
    py: Python,
    question: &str,
    tx: mpsc::UnboundedSender<StreamEvent>,
) -> Result<String> {
    let mut full_text = String::new();

    // Setup streaming DSPy call
    // ... (similar to above)

    for token_result in stream.iter()? {
        let token: String = token_result
            .context("Failed to extract token")?
            .extract()?;

        full_text.push_str(&token);

        if tx.send(StreamEvent::Token(token)).is_err() {
            break;
        }
    }

    Ok(full_text)
}
```

### 3. Concurrent LM Calls

Execute multiple DSPy predictions in parallel for maximum throughput.

**Concurrent Batch Processing**:

```rust
use pyo3::prelude::*;
use tokio::task::JoinSet;
use std::sync::Arc;
use anyhow::Result;

/// Execute multiple DSPy predictions concurrently
pub async fn batch_predict(questions: Vec<String>) -> Result<Vec<String>> {
    let mut set = JoinSet::new();

    for question in questions {
        set.spawn(async move {
            predict_async(question).await
        });
    }

    let mut results = Vec::new();
    while let Some(result) = set.join_next().await {
        results.push(result??);
    }

    Ok(results)
}

async fn predict_async(question: String) -> Result<String> {
    // Each task gets its own GIL acquisition
    tokio::task::spawn_blocking(move || {
        Python::with_gil(|py| {
            let dspy = py.import("dspy")?;
            let predictor = dspy
                .getattr("Predict")?
                .call1(("question -> answer",))?;

            let result = predictor.call_method1("__call__", (&question,))?;
            let answer: String = result.getattr("answer")?.extract()?;
            Ok(answer)
        })
    })
    .await?
}

// Usage
#[tokio::main]
async fn main() -> Result<()> {
    let questions = vec![
        "What is Rust?".to_string(),
        "What is Python?".to_string(),
        "What is DSPy?".to_string(),
        "What is async programming?".to_string(),
    ];

    let start = std::time::Instant::now();
    let answers = batch_predict(questions).await?;
    let duration = start.elapsed();

    println!("Processed {} questions in {:?}", answers.len(), duration);
    for (i, answer) in answers.iter().enumerate() {
        println!("Answer {}: {}", i + 1, answer);
    }

    Ok(())
}
```

**Rate-Limited Concurrent Calls**:

```rust
use tokio::sync::Semaphore;
use std::sync::Arc;

pub struct RateLimitedPredictor {
    semaphore: Arc<Semaphore>,
    predictor: Arc<Py<PyAny>>,
}

impl RateLimitedPredictor {
    pub fn new(max_concurrent: usize, signature: &str) -> Result<Self> {
        let predictor = Python::with_gil(|py| {
            let dspy = py.import("dspy")?;
            let pred = dspy
                .getattr("Predict")?
                .call1((signature,))?;
            Ok::<_, PyErr>(Py::from(pred))
        })?;

        Ok(Self {
            semaphore: Arc::new(Semaphore::new(max_concurrent)),
            predictor: Arc::new(predictor),
        })
    }

    pub async fn predict(&self, question: String) -> Result<String> {
        // Acquire permit (blocks if at limit)
        let _permit = self.semaphore.acquire().await?;

        let predictor = Arc::clone(&self.predictor);

        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                let result = predictor
                    .as_ref(py)
                    .call_method1("__call__", (question,))?;
                let answer: String = result.getattr("answer")?.extract()?;
                Ok(answer)
            })
        })
        .await?
    }
}

// Usage: max 5 concurrent LM calls
#[tokio::main]
async fn main() -> Result<()> {
    let predictor = RateLimitedPredictor::new(5, "question -> answer")?;

    let mut set = JoinSet::new();
    for i in 0..20 {
        let pred = predictor.clone();
        let question = format!("Question number {}?", i);

        set.spawn(async move {
            pred.predict(question).await
        });
    }

    // Only 5 run at a time due to semaphore
    while let Some(result) = set.join_next().await {
        println!("Got answer: {}", result??);
    }

    Ok(())
}
```

### 4. Backpressure Handling

Manage flow control when streaming data faster than consumers can process.

**Bounded Channel Pattern**:

```rust
use tokio::sync::mpsc;
use tokio::time::{timeout, Duration};

pub struct BackpressureStream {
    sender: mpsc::Sender<String>,
    receiver: mpsc::Receiver<String>,
}

impl BackpressureStream {
    pub fn new(capacity: usize) -> Self {
        let (tx, rx) = mpsc::channel(capacity);
        Self {
            sender: tx,
            receiver: rx,
        }
    }

    pub async fn send_with_backpressure(&self, token: String) -> Result<()> {
        // This will block if channel is full (backpressure)
        self.sender.send(token).await
            .map_err(|_| anyhow::anyhow!("Receiver dropped"))?;
        Ok(())
    }

    pub async fn recv_with_timeout(&mut self, dur: Duration) -> Result<Option<String>> {
        match timeout(dur, self.receiver.recv()).await {
            Ok(Some(token)) => Ok(Some(token)),
            Ok(None) => Ok(None), // Stream ended
            Err(_) => Err(anyhow::anyhow!("Receive timeout")),
        }
    }
}

// Producer: DSPy streaming with backpressure
async fn stream_producer(
    question: String,
    tx: mpsc::Sender<String>,
) -> Result<()> {
    tokio::task::spawn_blocking(move || {
        Python::with_gil(|py| {
            // Setup streaming...

            for token_result in stream.iter()? {
                let token: String = token_result?.extract()?;

                // This blocks if consumer is slow (backpressure!)
                if tx.blocking_send(token).is_err() {
                    break; // Consumer dropped
                }
            }

            Ok::<_, PyErr>(())
        })
    })
    .await??;

    Ok(())
}

// Consumer: Process with simulated slow work
async fn slow_consumer(mut rx: mpsc::Receiver<String>) {
    while let Some(token) = rx.recv().await {
        // Simulate slow processing
        tokio::time::sleep(Duration::from_millis(100)).await;
        println!("Processed: {}", token);
    }
}

// Usage
#[tokio::main]
async fn main() -> Result<()> {
    let (tx, rx) = mpsc::channel(10); // Buffer 10 tokens

    let producer = tokio::spawn(stream_producer("Explain Rust".to_string(), tx));
    let consumer = tokio::spawn(slow_consumer(rx));

    // Wait for both
    tokio::try_join!(producer, consumer)?;

    Ok(())
}
```

**Adaptive Backpressure**:

```rust
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

pub struct AdaptiveStream {
    buffer_size: Arc<AtomicUsize>,
    sender: mpsc::Sender<String>,
}

impl AdaptiveStream {
    pub fn new(initial_capacity: usize) -> (Self, mpsc::Receiver<String>) {
        let (tx, rx) = mpsc::channel(initial_capacity);

        let stream = Self {
            buffer_size: Arc::new(AtomicUsize::new(initial_capacity)),
            sender: tx,
        };

        (stream, rx)
    }

    pub async fn send_adaptive(&self, token: String) -> Result<()> {
        match self.sender.try_send(token.clone()) {
            Ok(_) => {
                // Sent successfully, maybe increase buffer
                let current = self.buffer_size.load(Ordering::Relaxed);
                if current < 100 {
                    self.buffer_size.store(current + 1, Ordering::Relaxed);
                }
                Ok(())
            }
            Err(mpsc::error::TrySendError::Full(_)) => {
                // Buffer full, apply backpressure
                self.buffer_size.fetch_sub(1, Ordering::Relaxed);

                // Wait and retry
                self.sender.send(token).await
                    .map_err(|_| anyhow::anyhow!("Send failed"))?;
                Ok(())
            }
            Err(mpsc::error::TrySendError::Closed(_)) => {
                Err(anyhow::anyhow!("Receiver closed"))
            }
        }
    }

    pub fn current_buffer_size(&self) -> usize {
        self.buffer_size.load(Ordering::Relaxed)
    }
}
```

### 5. Cancellation and Timeouts

Handle timeouts and cancellation for long-running LLM operations.

**Basic Timeout Pattern**:

```rust
use tokio::time::{timeout, Duration};

pub async fn predict_with_timeout(
    question: String,
    timeout_secs: u64,
) -> Result<String> {
    let fut = predict_async(question);

    match timeout(Duration::from_secs(timeout_secs), fut).await {
        Ok(Ok(answer)) => Ok(answer),
        Ok(Err(e)) => Err(e),
        Err(_) => Err(anyhow::anyhow!("Prediction timeout after {}s", timeout_secs)),
    }
}

// Usage
#[tokio::main]
async fn main() -> Result<()> {
    match predict_with_timeout("Complex question".to_string(), 30).await {
        Ok(answer) => println!("Answer: {}", answer),
        Err(e) if e.to_string().contains("timeout") => {
            eprintln!("Request timed out, try a simpler question");
        }
        Err(e) => eprintln!("Error: {}", e),
    }

    Ok(())
}
```

**Cancellable Operations**:

```rust
use tokio::sync::oneshot;
use tokio::select;

pub struct CancellablePredictor {
    cancel_tx: Option<oneshot::Sender<()>>,
}

impl CancellablePredictor {
    pub async fn predict_cancellable(
        question: String,
    ) -> (Self, tokio::task::JoinHandle<Result<String>>) {
        let (cancel_tx, cancel_rx) = oneshot::channel();

        let handle = tokio::spawn(async move {
            select! {
                result = predict_async(question) => result,
                _ = cancel_rx => {
                    Err(anyhow::anyhow!("Prediction cancelled"))
                }
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
    let (canceller, handle) = CancellablePredictor::predict_cancellable(
        "Long running question".to_string()
    ).await;

    // Cancel after 5 seconds
    tokio::spawn(async move {
        tokio::time::sleep(Duration::from_secs(5)).await;
        canceller.cancel();
    });

    match handle.await? {
        Ok(answer) => println!("Answer: {}", answer),
        Err(e) if e.to_string().contains("cancelled") => {
            println!("User cancelled the request");
        }
        Err(e) => eprintln!("Error: {}", e),
    }

    Ok(())
}
```

**Retry with Exponential Backoff**:

```rust
use tokio::time::{sleep, Duration};

pub async fn predict_with_retry(
    question: String,
    max_retries: u32,
) -> Result<String> {
    let mut attempt = 0;

    loop {
        match predict_async(question.clone()).await {
            Ok(answer) => return Ok(answer),
            Err(e) if attempt >= max_retries => {
                return Err(anyhow::anyhow!(
                    "Failed after {} retries: {}",
                    max_retries,
                    e
                ));
            }
            Err(e) => {
                let delay = Duration::from_secs(2_u64.pow(attempt));
                eprintln!("Attempt {} failed: {}. Retrying in {:?}...", attempt + 1, e, delay);
                sleep(delay).await;
                attempt += 1;
            }
        }
    }
}

// Usage
#[tokio::main]
async fn main() -> Result<()> {
    let answer = predict_with_retry("Question".to_string(), 3).await?;
    println!("Answer: {}", answer);
    Ok(())
}
```

### 6. WebSocket Patterns

Build real-time DSPy services with WebSocket streaming.

**WebSocket Server with Streaming**:

```rust
use tokio::net::TcpListener;
use tokio_tungstenite::{accept_async, tungstenite::Message};
use futures::{StreamExt, SinkExt};

#[tokio::main]
async fn main() -> Result<()> {
    let listener = TcpListener::bind("127.0.0.1:8080").await?;
    println!("WebSocket server listening on ws://127.0.0.1:8080");

    while let Ok((stream, addr)) = listener.accept().await {
        tokio::spawn(handle_connection(stream, addr));
    }

    Ok(())
}

async fn handle_connection(
    stream: tokio::net::TcpStream,
    addr: std::net::SocketAddr,
) -> Result<()> {
    let ws_stream = accept_async(stream).await?;
    println!("WebSocket connection from: {}", addr);

    let (mut write, mut read) = ws_stream.split();

    while let Some(msg) = read.next().await {
        let msg = msg?;

        if let Message::Text(question) = msg {
            // Stream DSPy response back over WebSocket
            let stream = DSpyStream::new(question)?;
            let mut stream = stream.into_stream();

            while let Some(token) = stream.next().await {
                write.send(Message::Text(token)).await?;
            }

            // Send end marker
            write.send(Message::Text("[DONE]".to_string())).await?;
        }
    }

    Ok(())
}
```

**WebSocket Client**:

```rust
use tokio_tungstenite::{connect_async, tungstenite::Message};
use futures::{StreamExt, SinkExt};

pub async fn stream_dspy_over_ws(question: String) -> Result<String> {
    let (ws_stream, _) = connect_async("ws://127.0.0.1:8080").await?;
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
            full_response.push_str(&text);
        }
    }

    println!(); // Newline
    Ok(full_response)
}

// Usage
#[tokio::main]
async fn main() -> Result<()> {
    let response = stream_dspy_over_ws("Explain WebSockets".to_string()).await?;
    println!("Full response: {}", response);
    Ok(())
}
```

### 7. Production Service Pattern

Complete async DSPy service with all patterns combined.

```rust
use axum::{
    Router,
    extract::State,
    routing::post,
    Json,
    response::sse::{Event, Sse},
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use futures::stream::Stream;

#[derive(Clone)]
struct AppState {
    predictor: Arc<RwLock<Py<PyAny>>>,
    semaphore: Arc<Semaphore>,
}

#[derive(Deserialize)]
struct PredictRequest {
    question: String,
    stream: Option<bool>,
}

#[derive(Serialize)]
struct PredictResponse {
    answer: String,
    duration_ms: u128,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize DSPy
    let predictor = Python::with_gil(|py| {
        let dspy = py.import("dspy")?;
        let pred = dspy.getattr("Predict")?.call1(("question -> answer",))?;
        Ok::<_, PyErr>(Py::from(pred))
    })?;

    let state = AppState {
        predictor: Arc::new(RwLock::new(predictor)),
        semaphore: Arc::new(Semaphore::new(10)), // Max 10 concurrent
    };

    let app = Router::new()
        .route("/predict", post(predict_handler))
        .route("/predict/stream", post(predict_stream_handler))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
    println!("Server listening on http://0.0.0.0:3000");

    axum::serve(listener, app).await?;

    Ok(())
}

async fn predict_handler(
    State(state): State<AppState>,
    Json(req): Json<PredictRequest>,
) -> Result<Json<PredictResponse>, String> {
    let _permit = state.semaphore.acquire().await
        .map_err(|e| format!("Rate limit: {}", e))?;

    let start = std::time::Instant::now();

    let predictor = state.predictor.read().await;

    let answer = tokio::task::spawn_blocking(move || {
        Python::with_gil(|py| {
            let result = predictor.as_ref(py)
                .call_method1("__call__", (req.question,))?;
            let answer: String = result.getattr("answer")?.extract()?;
            Ok::<_, PyErr>(answer)
        })
    })
    .await
    .map_err(|e| format!("Task error: {}", e))?
    .map_err(|e| format!("Python error: {}", e))?;

    let duration_ms = start.elapsed().as_millis();

    Ok(Json(PredictResponse { answer, duration_ms }))
}

async fn predict_stream_handler(
    State(state): State<AppState>,
    Json(req): Json<PredictRequest>,
) -> Sse<impl Stream<Item = Result<Event, String>>> {
    let stream = DSpyStream::new(req.question)
        .expect("Failed to create stream");

    let stream = stream.into_stream().map(|token| {
        Ok(Event::default().data(token))
    });

    Sse::new(stream)
}
```

### 8. Monitoring and Observability

Track async DSPy operations for production debugging.

```rust
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tokio::time::Instant;

#[derive(Clone)]
pub struct Metrics {
    total_requests: Arc<AtomicU64>,
    active_requests: Arc<AtomicU64>,
    total_errors: Arc<AtomicU64>,
    total_duration_ms: Arc<AtomicU64>,
}

impl Metrics {
    pub fn new() -> Self {
        Self {
            total_requests: Arc::new(AtomicU64::new(0)),
            active_requests: Arc::new(AtomicU64::new(0)),
            total_errors: Arc::new(AtomicU64::new(0)),
            total_duration_ms: Arc::new(AtomicU64::new(0)),
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

    pub fn report(&self) {
        let total = self.total_requests.load(Ordering::Relaxed);
        let active = self.active_requests.load(Ordering::Relaxed);
        let errors = self.total_errors.load(Ordering::Relaxed);
        let duration = self.total_duration_ms.load(Ordering::Relaxed);

        let avg_ms = if total > 0 { duration / total } else { 0 };

        println!("Metrics:");
        println!("  Total requests: {}", total);
        println!("  Active requests: {}", active);
        println!("  Total errors: {}", errors);
        println!("  Average duration: {}ms", avg_ms);
    }
}

pub async fn predict_with_metrics(
    question: String,
    metrics: Arc<Metrics>,
) -> Result<String> {
    metrics.start_request();
    let start = Instant::now();

    let result = predict_async(question).await;

    let duration_ms = start.elapsed().as_millis() as u64;
    metrics.end_request(duration_ms, result.is_err());

    result
}
```

## Best Practices

### DO

✅ **Use pyo3-asyncio** for proper runtime integration
✅ **Spawn blocking tasks** for Python calls (avoid blocking Tokio runtime)
✅ **Apply backpressure** to prevent memory exhaustion
✅ **Set timeouts** on all LM calls
✅ **Rate limit** concurrent requests
✅ **Monitor metrics** for debugging
✅ **Handle cancellation** gracefully
✅ **Test error paths** thoroughly

### DON'T

❌ **Block Tokio runtime** with Python GIL acquisition
❌ **Ignore backpressure** (leads to OOM)
❌ **Skip timeout handling** (hangs forever)
❌ **Assume success** (LLMs can fail)
❌ **Unlimited concurrency** (overwhelm APIs)
❌ **Forget cleanup** (resource leaks)
❌ **Mix sync and async** without care
❌ **Skip error propagation** (silent failures)

## Common Pitfalls

### 1. GIL Blocking Tokio Runtime

**Problem**: Acquiring GIL on Tokio threads blocks async tasks
```rust
// ❌ Bad: Blocks entire Tokio runtime
#[tokio::main]
async fn main() {
    Python::with_gil(|py| {
        // Long Python operation blocks all async tasks!
        expensive_python_call(py);
    })
}
```

**Solution**: Use spawn_blocking
```rust
// ✅ Good: Offload to blocking thread pool
#[tokio::main]
async fn main() {
    tokio::task::spawn_blocking(|| {
        Python::with_gil(|py| {
            expensive_python_call(py);
        })
    }).await;
}
```

### 2. Unbounded Channel Memory Leak

**Problem**: Producer faster than consumer fills memory
```rust
// ❌ Bad: Unbounded channel
let (tx, rx) = mpsc::unbounded_channel();
// Producer floods memory if consumer is slow
```

**Solution**: Use bounded channels
```rust
// ✅ Good: Bounded with backpressure
let (tx, rx) = mpsc::channel(100);
// Blocks producer if full
```

### 3. Missing Timeout Handling

**Problem**: LLM calls hang forever
```rust
// ❌ Bad: No timeout
let answer = predict_async(question).await?;
```

**Solution**: Always set timeouts
```rust
// ✅ Good: Timeout after 30s
let answer = timeout(Duration::from_secs(30), predict_async(question)).await??;
```

## Troubleshooting

### Issue: Runtime Panic

**Symptom**: `Cannot start a runtime from within a runtime`

**Solution**: Use `spawn_blocking` for Python calls:
```rust
tokio::task::spawn_blocking(|| {
    Python::with_gil(|py| {
        // Python calls here
    })
}).await?
```

### Issue: Slow Performance

**Symptom**: Async calls slower than expected

**Diagnosis**:
1. Check GIL contention (too many threads)
2. Verify using spawn_blocking
3. Check rate limiting configuration
4. Profile with tokio-console

**Solution**: Tune concurrency limits

### Issue: Memory Growth

**Symptom**: Memory usage increases over time

**Causes**:
- Unbounded channels
- Python object leaks
- No backpressure

**Solution**: Use bounded channels and monitor buffer sizes

## Next Steps

**After mastering async and streaming**:
1. **pyo3-dspy-production**: Caching, circuit breakers, metrics
2. **pyo3-dspy-optimization**: Model optimization and compilation
3. **rust-observability-tracing**: Distributed tracing for async services

## References

- [pyo3-asyncio Documentation](https://github.com/awestlake87/pyo3-asyncio)
- [Tokio Tutorial](https://tokio.rs/tokio/tutorial)
- [Async Rust Book](https://rust-lang.github.io/async-book/)
- [DSPy Streaming](https://dspy-docs.vercel.app/docs/building-blocks/language_models#streaming)

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Maintainer**: DSPy-PyO3 Integration Team
