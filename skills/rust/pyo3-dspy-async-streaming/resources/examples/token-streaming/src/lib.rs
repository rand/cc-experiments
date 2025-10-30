//! Token-by-token streaming for DSPy LLM responses
//!
//! This library provides async streaming support for DSPy language models using PyO3 and Tokio.
//! It enables real-time token-by-token streaming with comprehensive error handling, backpressure
//! management, and concurrent stream support.
//!
//! # Features
//!
//! - **DSpyStream**: Simple unbounded streaming for quick prototyping
//! - **SafeDSpyStream**: Production-ready bounded streaming with backpressure
//! - **StreamEvent**: Lifecycle events (Token, Done, Error)
//! - **Error Recovery**: Automatic retry with exponential backoff
//! - **Concurrent Streams**: Safe parallel streaming with rate limiting
//!
//! # Example
//!
//! ```no_run
//! use token_streaming::{SafeDSpyStream, StreamEvent};
//! use futures::StreamExt;
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     pyo3::prepare_freethreaded_python();
//!
//!     let stream = SafeDSpyStream::new("What is Rust?".to_string(), 100)?;
//!     let mut stream = stream.into_stream();
//!
//!     while let Some(event) = stream.next().await {
//!         match event {
//!             StreamEvent::Token(token) => print!("{}", token),
//!             StreamEvent::Done => println!("\n[Complete]"),
//!             StreamEvent::Error(e) => eprintln!("\n[Error: {}]", e),
//!         }
//!     }
//!
//!     Ok(())
//! }
//! ```

use anyhow::{Context, Result};
use futures::stream::Stream;
use pyo3::prelude::*;
use std::pin::Pin;
use std::task::{Context as TaskContext, Poll};
use std::time::Duration;
use tokio::sync::mpsc;
use tokio_stream::wrappers::{ReceiverStream, UnboundedReceiverStream};

/// Events emitted by streaming operations
#[derive(Debug, Clone)]
pub enum StreamEvent {
    /// A token was received from the LLM
    Token(String),
    /// The stream has completed successfully
    Done,
    /// An error occurred during streaming
    Error(String),
}

/// Simple unbounded token stream for quick prototyping
///
/// This stream uses an unbounded channel, which means it can consume unbounded memory
/// if the consumer is slower than the producer. Use `SafeDSpyStream` for production.
///
/// # Example
///
/// ```no_run
/// use token_streaming::DSpyStream;
/// use futures::StreamExt;
///
/// # #[tokio::main]
/// # async fn main() -> anyhow::Result<()> {
/// pyo3::prepare_freethreaded_python();
///
/// let stream = DSpyStream::new("Explain async Rust".to_string())?;
/// let mut stream = stream.into_stream();
///
/// while let Some(token) = stream.next().await {
///     print!("{}", token);
/// }
/// # Ok(())
/// # }
/// ```
pub struct DSpyStream {
    receiver: mpsc::UnboundedReceiver<String>,
}

impl DSpyStream {
    /// Create a new unbounded token stream
    ///
    /// Spawns a blocking task that calls DSPy and streams tokens through an unbounded channel.
    ///
    /// # Arguments
    ///
    /// * `question` - The question to ask the LLM
    ///
    /// # Errors
    ///
    /// Returns an error if the stream cannot be initialized
    pub fn new(question: String) -> Result<Self> {
        let (tx, rx) = mpsc::unbounded_channel();

        // Spawn blocking task for Python streaming
        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                if let Err(e) = stream_tokens_unbounded(py, &question, tx) {
                    eprintln!("Streaming error: {}", e);
                }
            })
        });

        Ok(Self { receiver: rx })
    }

    /// Convert into a Stream of tokens
    pub fn into_stream(self) -> impl Stream<Item = String> {
        UnboundedReceiverStream::new(self.receiver)
    }
}

/// Production-ready bounded token stream with backpressure and error handling
///
/// This stream uses a bounded channel which provides automatic backpressure when the
/// consumer cannot keep up with the producer. It also emits lifecycle events for
/// better error handling and monitoring.
///
/// # Example
///
/// ```no_run
/// use token_streaming::{SafeDSpyStream, StreamEvent};
/// use futures::StreamExt;
///
/// # #[tokio::main]
/// # async fn main() -> anyhow::Result<()> {
/// pyo3::prepare_freethreaded_python();
///
/// let stream = SafeDSpyStream::new("What is DSPy?".to_string(), 100)?;
/// let mut stream = stream.into_stream();
///
/// while let Some(event) = stream.next().await {
///     match event {
///         StreamEvent::Token(token) => print!("{}", token),
///         StreamEvent::Done => println!("\n[Complete]"),
///         StreamEvent::Error(e) => eprintln!("\n[Error: {}]", e),
///     }
/// }
/// # Ok(())
/// # }
/// ```
pub struct SafeDSpyStream {
    receiver: mpsc::Receiver<StreamEvent>,
}

impl SafeDSpyStream {
    /// Create a new bounded token stream
    ///
    /// # Arguments
    ///
    /// * `question` - The question to ask the LLM
    /// * `buffer_size` - Maximum number of tokens to buffer (typically 100-1000)
    ///
    /// # Errors
    ///
    /// Returns an error if the stream cannot be initialized
    pub fn new(question: String, buffer_size: usize) -> Result<Self> {
        let (tx, rx) = mpsc::channel(buffer_size);

        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                if let Err(e) = stream_tokens_bounded(py, &question, tx.clone()) {
                    let _ = tx.blocking_send(StreamEvent::Error(e.to_string()));
                } else {
                    let _ = tx.blocking_send(StreamEvent::Done);
                }
            })
        });

        Ok(Self { receiver: rx })
    }

    /// Create a stream with automatic retry on failure
    ///
    /// # Arguments
    ///
    /// * `question` - The question to ask the LLM
    /// * `buffer_size` - Maximum number of tokens to buffer
    /// * `max_retries` - Maximum number of retry attempts
    /// * `base_delay` - Base delay between retries (exponentially increased)
    pub fn with_retry(
        question: String,
        buffer_size: usize,
        max_retries: u32,
        base_delay: Duration,
    ) -> Result<Self> {
        let (tx, rx) = mpsc::channel(buffer_size);

        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| {
                let mut attempt = 0;
                let mut last_error = None;

                while attempt <= max_retries {
                    match stream_tokens_bounded(py, &question, tx.clone()) {
                        Ok(_) => {
                            let _ = tx.blocking_send(StreamEvent::Done);
                            return;
                        }
                        Err(e) => {
                            last_error = Some(e.to_string());
                            attempt += 1;

                            if attempt <= max_retries {
                                let delay = base_delay * 2_u32.pow(attempt - 1);
                                std::thread::sleep(delay);
                            }
                        }
                    }
                }

                if let Some(error) = last_error {
                    let _ = tx.blocking_send(StreamEvent::Error(format!(
                        "Failed after {} attempts: {}",
                        max_retries, error
                    )));
                }
            })
        });

        Ok(Self { receiver: rx })
    }

    /// Convert into a Stream of StreamEvents
    pub fn into_stream(self) -> impl Stream<Item = StreamEvent> {
        ReceiverStream::new(self.receiver)
    }
}

/// Stream tokens from DSPy using an unbounded channel
///
/// This function acquires the Python GIL and iterates over streaming tokens from DSPy.
/// It should only be called from a `spawn_blocking` thread.
fn stream_tokens_unbounded(
    py: Python,
    question: &str,
    tx: mpsc::UnboundedSender<String>,
) -> PyResult<()> {
    // Import DSPy
    let dspy = py.import("dspy")?;

    // Create predictor
    let predictor = dspy
        .getattr("Predict")?
        .call1(("question -> answer",))?;

    // Call predictor
    let result = predictor.call_method1("__call__", (question,))?;

    // Try to stream tokens if available
    if let Ok(stream_attr) = result.getattr("stream") {
        // Check if stream is callable or iterable
        if let Ok(stream_iter) = stream_attr.iter() {
            for token_result in stream_iter {
                let token: String = token_result?.extract()?;
                if tx.send(token).is_err() {
                    // Receiver dropped, stop streaming
                    break;
                }
            }
        } else {
            // Fallback: return full answer if streaming not available
            let answer: String = result.getattr("answer")?.extract()?;
            let _ = tx.send(answer);
        }
    } else {
        // No streaming support, return full answer
        let answer: String = result.getattr("answer")?.extract()?;
        let _ = tx.send(answer);
    }

    Ok(())
}

/// Stream tokens from DSPy using a bounded channel with backpressure
///
/// This function provides automatic backpressure: if the consumer is slow,
/// the blocking_send will block until buffer space is available.
fn stream_tokens_bounded(
    py: Python,
    question: &str,
    tx: mpsc::Sender<StreamEvent>,
) -> PyResult<()> {
    // Import DSPy
    let dspy = py.import("dspy")?;

    // Create predictor
    let predictor = dspy
        .getattr("Predict")?
        .call1(("question -> answer",))?;

    // Call predictor
    let result = predictor.call_method1("__call__", (question,))?;

    // Try to stream tokens
    if let Ok(stream_attr) = result.getattr("stream") {
        if let Ok(stream_iter) = stream_attr.iter() {
            for token_result in stream_iter {
                let token: String = token_result?.extract()?;

                // Blocking send with backpressure
                if tx.blocking_send(StreamEvent::Token(token)).is_err() {
                    // Receiver dropped, stop streaming
                    break;
                }
            }
            return Ok(());
        }
    }

    // Fallback: return full answer if streaming not available
    let answer: String = result.getattr("answer")?.extract()?;
    let _ = tx.blocking_send(StreamEvent::Token(answer));

    Ok(())
}

/// Collect all tokens from a stream into a single String
///
/// # Example
///
/// ```no_run
/// use token_streaming::{SafeDSpyStream, collect_stream};
///
/// # #[tokio::main]
/// # async fn main() -> anyhow::Result<()> {
/// pyo3::prepare_freethreaded_python();
///
/// let stream = SafeDSpyStream::new("What is Rust?".to_string(), 100)?;
/// let full_response = collect_stream(stream).await?;
/// println!("Response: {}", full_response);
/// # Ok(())
/// # }
/// ```
pub async fn collect_stream(stream: SafeDSpyStream) -> Result<String> {
    use futures::StreamExt;

    let mut stream = stream.into_stream();
    let mut full_text = String::new();

    while let Some(event) = stream.next().await {
        match event {
            StreamEvent::Token(token) => full_text.push_str(&token),
            StreamEvent::Done => break,
            StreamEvent::Error(e) => {
                return Err(anyhow::anyhow!("Stream error: {}", e));
            }
        }
    }

    Ok(full_text)
}

/// Aggregate multiple streams into a single stream
///
/// All streams are processed concurrently and their tokens are merged in order.
///
/// # Example
///
/// ```no_run
/// use token_streaming::{SafeDSpyStream, aggregate_streams, StreamEvent};
/// use futures::StreamExt;
///
/// # #[tokio::main]
/// # async fn main() -> anyhow::Result<()> {
/// pyo3::prepare_freethreaded_python();
///
/// let streams = vec![
///     SafeDSpyStream::new("Question 1".to_string(), 100)?,
///     SafeDSpyStream::new("Question 2".to_string(), 100)?,
/// ];
///
/// let mut merged = aggregate_streams(streams);
///
/// while let Some((index, event)) = merged.next().await {
///     match event {
///         StreamEvent::Token(token) => println!("[Stream {}] {}", index, token),
///         StreamEvent::Done => println!("[Stream {}] Complete", index),
///         StreamEvent::Error(e) => eprintln!("[Stream {}] Error: {}", index, e),
///     }
/// }
/// # Ok(())
/// # }
/// ```
pub fn aggregate_streams(
    streams: Vec<SafeDSpyStream>,
) -> impl Stream<Item = (usize, StreamEvent)> {
    use futures::stream::{self, StreamExt};

    let indexed_streams: Vec<_> = streams
        .into_iter()
        .enumerate()
        .map(|(idx, stream)| stream.into_stream().map(move |event| (idx, event)))
        .collect();

    stream::select_all(indexed_streams)
}

/// Configuration for stream processing
#[derive(Debug, Clone)]
pub struct StreamConfig {
    /// Maximum number of tokens to buffer
    pub buffer_size: usize,
    /// Maximum number of retry attempts
    pub max_retries: u32,
    /// Base delay between retries (exponentially increased)
    pub retry_delay: Duration,
    /// Timeout for each streaming operation
    pub timeout: Option<Duration>,
}

impl Default for StreamConfig {
    fn default() -> Self {
        Self {
            buffer_size: 100,
            max_retries: 3,
            retry_delay: Duration::from_secs(2),
            timeout: Some(Duration::from_secs(30)),
        }
    }
}

/// Initialize DSPy with streaming configuration
///
/// This should be called once at application startup.
///
/// # Arguments
///
/// * `model` - The model to use (e.g., "gpt-3.5-turbo")
/// * `provider` - The provider ("openai", "anthropic", etc.)
///
/// # Example
///
/// ```no_run
/// use token_streaming::init_dspy_streaming;
///
/// # fn main() -> anyhow::Result<()> {
/// pyo3::prepare_freethreaded_python();
/// init_dspy_streaming("gpt-3.5-turbo", "openai")?;
/// # Ok(())
/// # }
/// ```
pub fn init_dspy_streaming(model: &str, provider: &str) -> Result<()> {
    Python::with_gil(|py| {
        let dspy = py.import("dspy").context("Failed to import dspy")?;

        // Get the appropriate LM class
        let lm_class = match provider {
            "openai" => dspy.getattr("OpenAI")?,
            "anthropic" => dspy.getattr("Anthropic")?,
            "cohere" => dspy.getattr("Cohere")?,
            _ => return Err(anyhow::anyhow!("Unknown provider: {}", provider)),
        };

        // Create kwargs for streaming
        let kwargs = pyo3::types::PyDict::new(py);
        kwargs.set_item("model", model)?;
        kwargs.set_item("stream", true)?;

        // Initialize LM with streaming enabled
        let lm = lm_class.call((), Some(kwargs))?;

        // Configure DSPy settings
        dspy.getattr("settings")?
            .call_method1("configure", (lm,))?;

        Ok(())
    })
}

/// Concurrent stream processor with rate limiting
///
/// Processes multiple questions concurrently while respecting rate limits.
pub struct ConcurrentStreamProcessor {
    semaphore: std::sync::Arc<tokio::sync::Semaphore>,
    config: StreamConfig,
}

impl ConcurrentStreamProcessor {
    /// Create a new concurrent processor
    ///
    /// # Arguments
    ///
    /// * `max_concurrent` - Maximum number of concurrent streams
    /// * `config` - Stream configuration
    pub fn new(max_concurrent: usize, config: StreamConfig) -> Self {
        Self {
            semaphore: std::sync::Arc::new(tokio::sync::Semaphore::new(max_concurrent)),
            config,
        }
    }

    /// Process multiple questions concurrently
    ///
    /// Returns a vector of results in the same order as the input questions.
    pub async fn process_batch(&self, questions: Vec<String>) -> Vec<Result<String>> {
        use futures::future::join_all;

        let futures: Vec<_> = questions
            .into_iter()
            .map(|question| self.process_one(question))
            .collect();

        join_all(futures).await
    }

    /// Process a single question with rate limiting
    async fn process_one(&self, question: String) -> Result<String> {
        // Acquire semaphore permit (blocks if at limit)
        let _permit = self.semaphore.acquire().await?;

        // Create and collect stream
        let stream = if self.config.max_retries > 0 {
            SafeDSpyStream::with_retry(
                question,
                self.config.buffer_size,
                self.config.max_retries,
                self.config.retry_delay,
            )?
        } else {
            SafeDSpyStream::new(question, self.config.buffer_size)?
        };

        // Apply timeout if configured
        if let Some(timeout) = self.config.timeout {
            tokio::time::timeout(timeout, collect_stream(stream))
                .await
                .context("Stream timeout")?
        } else {
            collect_stream(stream).await
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_stream_config_default() {
        let config = StreamConfig::default();
        assert_eq!(config.buffer_size, 100);
        assert_eq!(config.max_retries, 3);
        assert_eq!(config.retry_delay, Duration::from_secs(2));
        assert!(config.timeout.is_some());
    }

    #[tokio::test]
    async fn test_stream_event_clone() {
        let event = StreamEvent::Token("test".to_string());
        let cloned = event.clone();

        match (event, cloned) {
            (StreamEvent::Token(a), StreamEvent::Token(b)) => assert_eq!(a, b),
            _ => panic!("Clone failed"),
        }
    }
}
