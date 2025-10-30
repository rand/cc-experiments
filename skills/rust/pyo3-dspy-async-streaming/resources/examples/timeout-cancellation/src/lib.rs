//! Timeout and cancellation patterns for async PyO3/DSPy operations
//!
//! This library provides robust timeout and cancellation mechanisms for managing
//! async Python operations from Rust, with special focus on DSPy workflows that
//! may exhibit unpredictable latency.
//!
//! # Key Components
//!
//! - `TimeoutConfig`: Configure timeout behavior with retry policies
//! - `CancellablePrediction`: Wrapper for predictions with cancellation support
//! - `DeadlineExecutor`: Execute operations within absolute time deadlines
//! - `GracefulCancellationHandler`: Coordinate graceful shutdown of operations
//!
//! # Examples
//!
//! ```rust,no_run
//! use timeout_cancellation::*;
//! use std::time::Duration;
//!
//! # async fn example() -> anyhow::Result<()> {
//! let config = TimeoutConfig::new()
//!     .with_request_timeout(Duration::from_secs(5));
//!
//! let result = config.execute_with_timeout(async {
//!     // Your async operation
//!     Ok::<_, anyhow::Error>(42)
//! }).await?;
//! # Ok(())
//! # }
//! ```

use anyhow::Result;
use futures::Future;
use std::pin::Pin;
use std::sync::Arc;
use std::time::{Duration, Instant};
use thiserror::Error;
use tokio::sync::{Mutex, RwLock};
use tokio::time::timeout;
use tokio_util::sync::CancellationToken;
use tracing::{debug, error, info, warn};

/// Errors that can occur during timeout and cancellation operations
#[derive(Error, Debug)]
pub enum TimeoutError {
    /// Operation exceeded its timeout duration
    #[error("operation timed out after {0:?}")]
    Elapsed(Duration),

    /// Operation exceeded absolute deadline
    #[error("deadline exceeded (deadline: {deadline:?}, now: {now:?})")]
    DeadlineExceeded {
        deadline: Instant,
        now: Instant,
    },

    /// Operation was cancelled
    #[error("operation was cancelled")]
    Cancelled,

    /// Operation failed with an error
    #[error("operation failed: {0}")]
    OperationFailed(#[from] anyhow::Error),
}

/// Configuration for timeout behavior
#[derive(Debug, Clone)]
pub struct TimeoutConfig {
    /// Timeout for individual requests
    pub request_timeout: Option<Duration>,

    /// Global timeout for entire session
    pub session_timeout: Option<Duration>,

    /// Maximum number of retry attempts
    pub max_retries: usize,

    /// Backoff strategy for retries
    pub backoff: BackoffStrategy,

    /// Whether to log timeout events
    pub log_timeouts: bool,
}

impl Default for TimeoutConfig {
    fn default() -> Self {
        Self {
            request_timeout: Some(Duration::from_secs(30)),
            session_timeout: Some(Duration::from_secs(300)),
            max_retries: 3,
            backoff: BackoffStrategy::Exponential {
                initial: Duration::from_millis(100),
                max: Duration::from_secs(10),
            },
            log_timeouts: true,
        }
    }
}

impl TimeoutConfig {
    /// Create a new timeout configuration with defaults
    pub fn new() -> Self {
        Self::default()
    }

    /// Set the per-request timeout
    pub fn with_request_timeout(mut self, timeout: Duration) -> Self {
        self.request_timeout = Some(timeout);
        self
    }

    /// Set the session-wide timeout
    pub fn with_session_timeout(mut self, timeout: Duration) -> Self {
        self.session_timeout = Some(timeout);
        self
    }

    /// Set the maximum retry attempts
    pub fn with_max_retries(mut self, retries: usize) -> Self {
        self.max_retries = retries;
        self
    }

    /// Set the backoff strategy
    pub fn with_backoff(mut self, backoff: BackoffStrategy) -> Self {
        self.backoff = backoff;
        self
    }

    /// Enable or disable timeout logging
    pub fn with_logging(mut self, enabled: bool) -> Self {
        self.log_timeouts = enabled;
        self
    }

    /// Execute an operation with the configured timeout
    pub async fn execute_with_timeout<F, T>(&self, fut: F) -> Result<T, TimeoutError>
    where
        F: Future<Output = Result<T>>,
    {
        if let Some(duration) = self.request_timeout {
            match timeout(duration, fut).await {
                Ok(Ok(result)) => Ok(result),
                Ok(Err(e)) => Err(TimeoutError::OperationFailed(e)),
                Err(_) => {
                    if self.log_timeouts {
                        warn!("Operation timed out after {:?}", duration);
                    }
                    Err(TimeoutError::Elapsed(duration))
                }
            }
        } else {
            fut.await.map_err(TimeoutError::OperationFailed)
        }
    }

    /// Execute with retry on timeout
    pub async fn execute_with_retry<F, Fut, T>(&self, mut f: F) -> Result<T, TimeoutError>
    where
        F: FnMut() -> Fut,
        Fut: Future<Output = Result<T>>,
    {
        let mut attempt = 0;

        loop {
            match self.execute_with_timeout(f()).await {
                Ok(result) => return Ok(result),
                Err(TimeoutError::Elapsed(_)) if attempt < self.max_retries => {
                    attempt += 1;
                    let backoff_duration = self.backoff.duration_for_attempt(attempt);

                    if self.log_timeouts {
                        info!(
                            "Retry attempt {} after {:?} backoff",
                            attempt, backoff_duration
                        );
                    }

                    tokio::time::sleep(backoff_duration).await;
                    continue;
                }
                Err(e) => return Err(e),
            }
        }
    }
}

/// Backoff strategies for retry operations
#[derive(Debug, Clone)]
pub enum BackoffStrategy {
    /// Fixed delay between retries
    Fixed(Duration),

    /// Exponential backoff with optional max duration
    Exponential {
        initial: Duration,
        max: Duration,
    },

    /// Linear increase in delay
    Linear {
        initial: Duration,
        increment: Duration,
    },
}

impl BackoffStrategy {
    /// Calculate backoff duration for a given attempt number
    pub fn duration_for_attempt(&self, attempt: usize) -> Duration {
        match self {
            BackoffStrategy::Fixed(duration) => *duration,
            BackoffStrategy::Exponential { initial, max } => {
                let exponential = initial.as_millis() * 2_u128.pow(attempt as u32);
                Duration::from_millis(exponential.min(max.as_millis()) as u64)
            }
            BackoffStrategy::Linear { initial, increment } => {
                *initial + *increment * (attempt as u32)
            }
        }
    }
}

/// Status of a cancellable operation
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OperationStatus {
    /// Operation is pending/not started
    Pending,

    /// Operation is currently running
    Running,

    /// Operation completed successfully
    Completed,

    /// Operation was cancelled
    Cancelled,

    /// Operation failed
    Failed,

    /// Operation timed out
    TimedOut,
}

/// Wrapper for cancellable predictions with status tracking
pub struct CancellablePrediction<T> {
    /// Cancellation token for this prediction
    token: CancellationToken,

    /// Current status of the operation
    status: Arc<RwLock<OperationStatus>>,

    /// Result storage
    result: Arc<Mutex<Option<Result<T>>>>,

    /// Start time
    start_time: Instant,

    /// Operation identifier
    id: String,
}

impl<T> CancellablePrediction<T> {
    /// Create a new cancellable prediction
    pub fn new(id: impl Into<String>) -> Self {
        Self {
            token: CancellationToken::new(),
            status: Arc::new(RwLock::new(OperationStatus::Pending)),
            result: Arc::new(Mutex::new(None)),
            start_time: Instant::now(),
            id: id.into(),
        }
    }

    /// Get the cancellation token
    pub fn token(&self) -> CancellationToken {
        self.token.clone()
    }

    /// Get current status
    pub async fn status(&self) -> OperationStatus {
        *self.status.read().await
    }

    /// Cancel the operation
    pub async fn cancel(&self) {
        self.token.cancel();
        *self.status.write().await = OperationStatus::Cancelled;
        debug!("Cancelled operation: {}", self.id);
    }

    /// Check if cancelled
    pub fn is_cancelled(&self) -> bool {
        self.token.is_cancelled()
    }

    /// Get elapsed time since operation started
    pub fn elapsed(&self) -> Duration {
        self.start_time.elapsed()
    }

    /// Execute the prediction with cancellation support
    pub async fn execute<F, Fut>(&self, f: F) -> Result<T, TimeoutError>
    where
        F: FnOnce() -> Fut,
        Fut: Future<Output = Result<T>>,
        T: Clone,
    {
        // Update status to running
        *self.status.write().await = OperationStatus::Running;

        let result = tokio::select! {
            result = f() => {
                match result {
                    Ok(value) => {
                        *self.status.write().await = OperationStatus::Completed;
                        *self.result.lock().await = Some(Ok(value.clone()));
                        Ok(value)
                    }
                    Err(e) => {
                        *self.status.write().await = OperationStatus::Failed;
                        *self.result.lock().await = Some(Err(anyhow::anyhow!("{}", e)));
                        Err(TimeoutError::OperationFailed(e))
                    }
                }
            }
            _ = self.token.cancelled() => {
                *self.status.write().await = OperationStatus::Cancelled;
                info!("Operation {} cancelled after {:?}", self.id, self.elapsed());
                Err(TimeoutError::Cancelled)
            }
        };

        result
    }

    /// Execute with timeout
    pub async fn execute_with_timeout<F, Fut>(
        &self,
        duration: Duration,
        f: F,
    ) -> Result<T, TimeoutError>
    where
        F: FnOnce() -> Fut,
        Fut: Future<Output = Result<T>>,
        T: Clone,
    {
        match timeout(duration, self.execute(f)).await {
            Ok(result) => result,
            Err(_) => {
                *self.status.write().await = OperationStatus::TimedOut;
                warn!(
                    "Operation {} timed out after {:?}",
                    self.id, duration
                );
                Err(TimeoutError::Elapsed(duration))
            }
        }
    }
}

/// Executor that enforces absolute deadlines
pub struct DeadlineExecutor {
    /// Absolute deadline for all operations
    deadline: Instant,

    /// Cancellation token for all operations
    token: CancellationToken,

    /// Operations tracking
    operations: Arc<Mutex<Vec<String>>>,
}

impl DeadlineExecutor {
    /// Create a new deadline executor
    pub fn new(deadline: Instant) -> Self {
        Self {
            deadline,
            token: CancellationToken::new(),
            operations: Arc::new(Mutex::new(Vec::new())),
        }
    }

    /// Create with duration from now
    pub fn from_duration(duration: Duration) -> Self {
        Self::new(Instant::now() + duration)
    }

    /// Check if deadline has passed
    pub fn is_past_deadline(&self) -> bool {
        Instant::now() >= self.deadline
    }

    /// Get remaining time until deadline
    pub fn remaining(&self) -> Option<Duration> {
        self.deadline.checked_duration_since(Instant::now())
    }

    /// Execute an operation within the deadline
    pub async fn execute<F, T>(&self, id: impl Into<String>, fut: F) -> Result<T, TimeoutError>
    where
        F: Future<Output = Result<T>>,
    {
        let id = id.into();

        // Check deadline before starting
        if self.is_past_deadline() {
            return Err(TimeoutError::DeadlineExceeded {
                deadline: self.deadline,
                now: Instant::now(),
            });
        }

        // Track operation
        self.operations.lock().await.push(id.clone());

        let remaining = self.remaining().ok_or_else(|| TimeoutError::DeadlineExceeded {
            deadline: self.deadline,
            now: Instant::now(),
        })?;

        debug!("Executing {} with {:?} remaining", id, remaining);

        let result = tokio::select! {
            result = timeout(remaining, fut) => {
                match result {
                    Ok(Ok(value)) => Ok(value),
                    Ok(Err(e)) => Err(TimeoutError::OperationFailed(e)),
                    Err(_) => Err(TimeoutError::DeadlineExceeded {
                        deadline: self.deadline,
                        now: Instant::now(),
                    }),
                }
            }
            _ = self.token.cancelled() => {
                Err(TimeoutError::Cancelled)
            }
        };

        // Remove from tracking
        self.operations.lock().await.retain(|op| op != &id);

        result
    }

    /// Cancel all operations
    pub async fn cancel_all(&self) {
        self.token.cancel();
        let ops = self.operations.lock().await;
        info!("Cancelled {} operations", ops.len());
    }

    /// Get list of running operations
    pub async fn running_operations(&self) -> Vec<String> {
        self.operations.lock().await.clone()
    }
}

/// Handler for graceful cancellation of multiple operations
pub struct GracefulCancellationHandler {
    /// Main cancellation token
    token: CancellationToken,

    /// Child tokens for individual operations
    children: Arc<Mutex<Vec<(String, CancellationToken)>>>,

    /// Cleanup handlers
    cleanup_handlers: Arc<Mutex<Vec<Pin<Box<dyn Future<Output = ()> + Send>>>>>,
}

impl GracefulCancellationHandler {
    /// Create a new graceful cancellation handler
    pub fn new() -> Self {
        Self {
            token: CancellationToken::new(),
            children: Arc::new(Mutex::new(Vec::new())),
            cleanup_handlers: Arc::new(Mutex::new(Vec::new())),
        }
    }

    /// Create a child token for an operation
    pub async fn create_child(&self, id: impl Into<String>) -> CancellationToken {
        let child = self.token.child_token();
        self.children.lock().await.push((id.into(), child.clone()));
        child
    }

    /// Register a cleanup handler
    pub async fn register_cleanup<F>(&self, cleanup: F)
    where
        F: Future<Output = ()> + Send + 'static,
    {
        self.cleanup_handlers.lock().await.push(Box::pin(cleanup));
    }

    /// Cancel all operations gracefully
    pub async fn cancel_gracefully(&self) {
        info!("Initiating graceful cancellation");

        // Cancel main token (propagates to all children)
        self.token.cancel();

        // Wait a moment for operations to notice cancellation
        tokio::time::sleep(Duration::from_millis(100)).await;

        // Run cleanup handlers
        let handlers = std::mem::take(&mut *self.cleanup_handlers.lock().await);
        let cleanup_count = handlers.len();

        if cleanup_count > 0 {
            info!("Running {} cleanup handlers", cleanup_count);
            futures::future::join_all(handlers).await;
        }

        info!("Graceful cancellation complete");
    }

    /// Check if cancelled
    pub fn is_cancelled(&self) -> bool {
        self.token.is_cancelled()
    }

    /// Wait for cancellation signal
    pub async fn cancelled(&self) {
        self.token.cancelled().await
    }

    /// Get number of active children
    pub async fn active_count(&self) -> usize {
        self.children.lock().await.len()
    }
}

impl Default for GracefulCancellationHandler {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_timeout_config() {
        let config = TimeoutConfig::new()
            .with_request_timeout(Duration::from_millis(100));

        // Should succeed
        let result = config.execute_with_timeout(async {
            Ok::<_, anyhow::Error>(42)
        }).await;
        assert!(result.is_ok());

        // Should timeout
        let result = config.execute_with_timeout(async {
            tokio::time::sleep(Duration::from_secs(1)).await;
            Ok::<_, anyhow::Error>(42)
        }).await;
        assert!(matches!(result, Err(TimeoutError::Elapsed(_))));
    }

    #[tokio::test]
    async fn test_cancellable_prediction() {
        let pred = CancellablePrediction::<i32>::new("test");

        // Should be cancellable
        let handle = tokio::spawn({
            let pred = CancellablePrediction::new("test");
            async move {
                pred.execute(|| async {
                    tokio::time::sleep(Duration::from_secs(10)).await;
                    Ok::<_, anyhow::Error>(42)
                }).await
            }
        });

        tokio::time::sleep(Duration::from_millis(50)).await;
        pred.cancel().await;

        let result = handle.await.unwrap();
        assert!(matches!(result, Err(TimeoutError::Cancelled)));
    }

    #[tokio::test]
    async fn test_deadline_executor() {
        let executor = DeadlineExecutor::from_duration(Duration::from_millis(200));

        // Should succeed
        let result = executor.execute("fast", async {
            Ok::<_, anyhow::Error>(42)
        }).await;
        assert!(result.is_ok());

        // Should fail deadline
        let result = executor.execute("slow", async {
            tokio::time::sleep(Duration::from_secs(1)).await;
            Ok::<_, anyhow::Error>(42)
        }).await;
        assert!(matches!(result, Err(TimeoutError::DeadlineExceeded { .. })));
    }

    #[tokio::test]
    async fn test_graceful_cancellation() {
        let handler = GracefulCancellationHandler::new();
        let token = handler.create_child("test").await;

        let cleanup_done = Arc::new(Mutex::new(false));
        let cleanup_done_clone = cleanup_done.clone();

        handler.register_cleanup(async move {
            *cleanup_done_clone.lock().await = true;
        }).await;

        tokio::spawn({
            let token = token.clone();
            async move {
                token.cancelled().await;
            }
        });

        handler.cancel_gracefully().await;

        assert!(handler.is_cancelled());
        assert!(*cleanup_done.lock().await);
    }
}
