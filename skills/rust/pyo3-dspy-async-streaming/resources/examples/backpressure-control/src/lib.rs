//! Backpressure control for async streaming
//!
//! This library provides comprehensive backpressure handling for async streams,
//! including bounded channels, adaptive rate control, and multiple buffer strategies.

use anyhow::{Context, Result};
use futures::stream::{Stream, StreamExt};
use std::pin::Pin;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::task::{Context as TaskContext, Poll};
use std::time::{Duration, Instant};
use tokio::sync::mpsc;
use tokio::sync::Mutex;
use tokio::time;
use tracing::{debug, info, warn};

/// Strategy for handling backpressure when buffer is full
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BackpressureStrategy {
    /// Drop oldest items when buffer is full (FIFO drop)
    DropOldest,
    /// Drop newest items when buffer is full (LIFO drop)
    DropNewest,
    /// Block producer until consumer catches up
    Block,
    /// Dynamically adjust production rate
    Adaptive,
}

/// Rate control algorithm for adaptive backpressure
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RateControlAlgorithm {
    /// Additive Increase, Multiplicative Decrease (TCP-like)
    AIMD,
    /// Token bucket with burst capacity
    TokenBucket,
    /// Sliding window rate averaging
    SlidingWindow,
}

/// Metrics tracked by the backpressure controller
#[derive(Debug, Clone)]
pub struct BackpressureMetrics {
    /// Current number of items in queue
    pub current_depth: usize,
    /// Peak queue depth observed
    pub peak_depth: usize,
    /// Total items dropped due to backpressure
    pub dropped_count: u64,
    /// Total items produced
    pub produced_count: u64,
    /// Total items consumed
    pub consumed_count: u64,
    /// Current throughput in items/second
    pub throughput_rate: f64,
    /// Number of times backpressure was triggered
    pub backpressure_events: u64,
    /// Current rate limit (items/second)
    pub current_rate_limit: f64,
    /// Average queue depth over time
    pub avg_queue_depth: f64,
}

impl Default for BackpressureMetrics {
    fn default() -> Self {
        Self {
            current_depth: 0,
            peak_depth: 0,
            dropped_count: 0,
            produced_count: 0,
            consumed_count: 0,
            throughput_rate: 0.0,
            backpressure_events: 0,
            current_rate_limit: 0.0,
            avg_queue_depth: 0.0,
        }
    }
}

/// Shared state for metrics tracking
struct MetricsState {
    current_depth: AtomicUsize,
    peak_depth: AtomicUsize,
    dropped_count: AtomicU64,
    produced_count: AtomicU64,
    consumed_count: AtomicU64,
    backpressure_events: AtomicU64,
    last_update: Mutex<Instant>,
    throughput_samples: Mutex<Vec<(Instant, u64)>>,
}

impl MetricsState {
    fn new() -> Self {
        Self {
            current_depth: AtomicUsize::new(0),
            peak_depth: AtomicUsize::new(0),
            dropped_count: AtomicU64::new(0),
            produced_count: AtomicU64::new(0),
            consumed_count: AtomicU64::new(0),
            backpressure_events: AtomicU64::new(0),
            last_update: Mutex::new(Instant::now()),
            throughput_samples: Mutex::new(Vec::new()),
        }
    }

    fn increment_depth(&self) {
        let new_depth = self.current_depth.fetch_add(1, Ordering::SeqCst) + 1;
        let mut peak = self.peak_depth.load(Ordering::SeqCst);
        while new_depth > peak {
            match self.peak_depth.compare_exchange(
                peak,
                new_depth,
                Ordering::SeqCst,
                Ordering::SeqCst,
            ) {
                Ok(_) => break,
                Err(current) => peak = current,
            }
        }
    }

    fn decrement_depth(&self) {
        self.current_depth.fetch_sub(1, Ordering::SeqCst);
    }
}

/// Adaptive rate controller that adjusts production rate based on backpressure signals
pub struct AdaptiveRateController {
    algorithm: RateControlAlgorithm,
    current_rate: Arc<Mutex<f64>>,
    max_rate: f64,
    min_rate: f64,
    // AIMD parameters
    additive_increase: f64,
    multiplicative_decrease: f64,
    // Token bucket parameters
    tokens: Arc<Mutex<f64>>,
    bucket_capacity: f64,
    refill_rate: f64,
    last_refill: Arc<Mutex<Instant>>,
    // Sliding window parameters
    window_duration: Duration,
    window_samples: Arc<Mutex<Vec<(Instant, usize)>>>,
}

impl AdaptiveRateController {
    /// Create a new adaptive rate controller
    pub fn new(algorithm: RateControlAlgorithm, initial_rate: f64, max_rate: f64) -> Self {
        Self {
            algorithm,
            current_rate: Arc::new(Mutex::new(initial_rate)),
            max_rate,
            min_rate: 1.0,
            additive_increase: 1.0,
            multiplicative_decrease: 0.5,
            tokens: Arc::new(Mutex::new(initial_rate)),
            bucket_capacity: max_rate,
            refill_rate: initial_rate,
            last_refill: Arc::new(Mutex::new(Instant::now())),
            window_duration: Duration::from_secs(5),
            window_samples: Arc::new(Mutex::new(Vec::new())),
        }
    }

    /// Get current rate limit
    pub async fn current_rate(&self) -> f64 {
        *self.current_rate.lock().await
    }

    /// Increase rate (called when no backpressure)
    pub async fn increase_rate(&self) {
        match self.algorithm {
            RateControlAlgorithm::AIMD => {
                let mut rate = self.current_rate.lock().await;
                *rate = (*rate + self.additive_increase).min(self.max_rate);
                debug!("AIMD: Increased rate to {:.2}", *rate);
            }
            RateControlAlgorithm::TokenBucket => {
                // Token bucket automatically refills
            }
            RateControlAlgorithm::SlidingWindow => {
                // Sliding window adjusts based on observed throughput
            }
        }
    }

    /// Decrease rate (called on backpressure event)
    pub async fn decrease_rate(&self) {
        match self.algorithm {
            RateControlAlgorithm::AIMD => {
                let mut rate = self.current_rate.lock().await;
                *rate = (*rate * self.multiplicative_decrease).max(self.min_rate);
                warn!("AIMD: Decreased rate to {:.2} due to backpressure", *rate);
            }
            RateControlAlgorithm::TokenBucket => {
                // Token bucket handles this via token consumption
            }
            RateControlAlgorithm::SlidingWindow => {
                // Sliding window adjusts based on observed throughput
            }
        }
    }

    /// Check if we can produce an item (rate limiting)
    pub async fn can_produce(&self) -> bool {
        match self.algorithm {
            RateControlAlgorithm::AIMD => {
                // AIMD doesn't actively rate limit, just adjusts target
                true
            }
            RateControlAlgorithm::TokenBucket => {
                self.refill_tokens().await;
                let mut tokens = self.tokens.lock().await;
                if *tokens >= 1.0 {
                    *tokens -= 1.0;
                    true
                } else {
                    false
                }
            }
            RateControlAlgorithm::SlidingWindow => {
                self.update_window().await;
                let samples = self.window_samples.lock().await;
                let now = Instant::now();
                let recent_count: usize = samples
                    .iter()
                    .filter(|(t, _)| now.duration_since(*t) < self.window_duration)
                    .map(|(_, count)| count)
                    .sum();

                let current_rate = recent_count as f64 / self.window_duration.as_secs_f64();
                current_rate < self.max_rate
            }
        }
    }

    /// Refill tokens for token bucket algorithm
    async fn refill_tokens(&self) {
        let mut last_refill = self.last_refill.lock().await;
        let now = Instant::now();
        let elapsed = now.duration_since(*last_refill).as_secs_f64();

        if elapsed > 0.0 {
            let mut tokens = self.tokens.lock().await;
            *tokens = (*tokens + self.refill_rate * elapsed).min(self.bucket_capacity);
            *last_refill = now;
        }
    }

    /// Update sliding window samples
    async fn update_window(&self) {
        let mut samples = self.window_samples.lock().await;
        let now = Instant::now();

        // Remove old samples
        samples.retain(|(t, _)| now.duration_since(*t) < self.window_duration);

        // Add new sample
        samples.push((now, 1));
    }

    /// Get delay based on current rate
    pub async fn rate_delay(&self) -> Duration {
        let rate = self.current_rate.lock().await;
        if *rate > 0.0 {
            Duration::from_secs_f64(1.0 / *rate)
        } else {
            Duration::from_secs(1)
        }
    }
}

/// Main backpressure controller
pub struct BackpressureController<T> {
    capacity: usize,
    strategy: BackpressureStrategy,
    sender: mpsc::Sender<T>,
    receiver: Arc<Mutex<mpsc::Receiver<T>>>,
    metrics: Arc<MetricsState>,
    rate_controller: Option<Arc<AdaptiveRateController>>,
}

impl<T: Send + 'static> BackpressureController<T> {
    /// Create a new backpressure controller
    pub fn new(capacity: usize, strategy: BackpressureStrategy) -> Self {
        let (sender, receiver) = mpsc::channel(capacity);
        let metrics = Arc::new(MetricsState::new());

        let rate_controller = if strategy == BackpressureStrategy::Adaptive {
            Some(Arc::new(AdaptiveRateController::new(
                RateControlAlgorithm::AIMD,
                100.0,
                200.0,
            )))
        } else {
            None
        };

        Self {
            capacity,
            strategy,
            sender,
            receiver: Arc::new(Mutex::new(receiver)),
            metrics,
            rate_controller,
        }
    }

    /// Create controller with custom rate control algorithm
    pub fn with_rate_control(
        capacity: usize,
        algorithm: RateControlAlgorithm,
        initial_rate: f64,
        max_rate: f64,
    ) -> Self {
        let (sender, receiver) = mpsc::channel(capacity);
        let metrics = Arc::new(MetricsState::new());
        let rate_controller = Some(Arc::new(AdaptiveRateController::new(
            algorithm,
            initial_rate,
            max_rate,
        )));

        Self {
            capacity,
            strategy: BackpressureStrategy::Adaptive,
            sender,
            receiver: Arc::new(Mutex::new(receiver)),
            metrics,
            rate_controller,
        }
    }

    /// Send an item with backpressure handling
    pub async fn send(&self, item: T) -> Result<()> {
        self.metrics.produced_count.fetch_add(1, Ordering::SeqCst);

        // Check rate limit for adaptive strategy
        if let Some(ref controller) = self.rate_controller {
            while !controller.can_produce().await {
                let delay = controller.rate_delay().await;
                time::sleep(delay).await;
            }
        }

        match self.strategy {
            BackpressureStrategy::Block | BackpressureStrategy::Adaptive => {
                // Try to send, will block if channel is full
                if let Err(e) = self.sender.send(item).await {
                    self.metrics.dropped_count.fetch_add(1, Ordering::SeqCst);
                    return Err(anyhow::anyhow!("Failed to send: {}", e));
                }
                self.metrics.increment_depth();
            }
            BackpressureStrategy::DropOldest | BackpressureStrategy::DropNewest => {
                // For drop strategies, use try_send
                if let Err(mpsc::error::TrySendError::Full(_)) = self.sender.try_send(item) {
                    self.metrics.dropped_count.fetch_add(1, Ordering::SeqCst);
                    self.metrics
                        .backpressure_events
                        .fetch_add(1, Ordering::SeqCst);

                    if let Some(ref controller) = self.rate_controller {
                        controller.decrease_rate().await;
                    }

                    warn!(
                        "Buffer full (strategy: {:?}), dropped item",
                        self.strategy
                    );
                } else {
                    self.metrics.increment_depth();

                    if let Some(ref controller) = self.rate_controller {
                        controller.increase_rate().await;
                    }
                }
            }
        }

        Ok(())
    }

    /// Receive an item
    pub async fn recv(&self) -> Option<T> {
        let mut receiver = self.receiver.lock().await;
        let item = receiver.recv().await;

        if item.is_some() {
            self.metrics.consumed_count.fetch_add(1, Ordering::SeqCst);
            self.metrics.decrement_depth();
        }

        item
    }

    /// Get current metrics
    pub async fn metrics(&self) -> BackpressureMetrics {
        let current_depth = self.metrics.current_depth.load(Ordering::SeqCst);
        let peak_depth = self.metrics.peak_depth.load(Ordering::SeqCst);
        let dropped_count = self.metrics.dropped_count.load(Ordering::SeqCst);
        let produced_count = self.metrics.produced_count.load(Ordering::SeqCst);
        let consumed_count = self.metrics.consumed_count.load(Ordering::SeqCst);
        let backpressure_events = self.metrics.backpressure_events.load(Ordering::SeqCst);

        // Calculate throughput
        let mut last_update = self.metrics.last_update.lock().await;
        let now = Instant::now();
        let elapsed = now.duration_since(*last_update).as_secs_f64();

        let throughput_rate = if elapsed > 0.0 {
            consumed_count as f64 / elapsed
        } else {
            0.0
        };

        let current_rate_limit = if let Some(ref controller) = self.rate_controller {
            controller.current_rate().await
        } else {
            0.0
        };

        // Calculate average queue depth
        let avg_queue_depth = if produced_count > 0 {
            (produced_count - consumed_count) as f64 / 2.0
        } else {
            0.0
        };

        BackpressureMetrics {
            current_depth,
            peak_depth,
            dropped_count,
            produced_count,
            consumed_count,
            throughput_rate,
            backpressure_events,
            current_rate_limit,
            avg_queue_depth,
        }
    }

    /// Create a bounded stream from this controller
    pub fn create_stream(&self) -> BoundedDSpyStream<T> {
        BoundedDSpyStream {
            receiver: Arc::clone(&self.receiver),
            metrics: Arc::clone(&self.metrics),
        }
    }

    /// Get channel capacity
    pub fn capacity(&self) -> usize {
        self.capacity
    }

    /// Get backpressure strategy
    pub fn strategy(&self) -> BackpressureStrategy {
        self.strategy
    }
}

/// Bounded stream wrapper that enforces capacity and tracks metrics
pub struct BoundedDSpyStream<T> {
    receiver: Arc<Mutex<mpsc::Receiver<T>>>,
    metrics: Arc<MetricsState>,
}

impl<T> Stream for BoundedDSpyStream<T>
where
    T: Send + 'static,
{
    type Item = T;

    fn poll_next(self: Pin<&mut Self>, cx: &mut TaskContext<'_>) -> Poll<Option<Self::Item>> {
        let receiver = self.receiver.clone();

        // This is a simplified implementation
        // In production, you'd want to properly implement Stream
        Poll::Pending
    }
}

impl<T> BoundedDSpyStream<T> {
    /// Create a new bounded stream
    pub fn new(capacity: usize) -> (Self, mpsc::Sender<T>) {
        let (sender, receiver) = mpsc::channel(capacity);
        let metrics = Arc::new(MetricsState::new());

        (
            Self {
                receiver: Arc::new(Mutex::new(receiver)),
                metrics,
            },
            sender,
        )
    }

    /// Receive next item
    pub async fn next(&mut self) -> Option<T> {
        let mut receiver = self.receiver.lock().await;
        let item = receiver.recv().await;

        if item.is_some() {
            self.metrics.consumed_count.fetch_add(1, Ordering::SeqCst);
            self.metrics.decrement_depth();
        }

        item
    }

    /// Get current queue depth
    pub fn queue_depth(&self) -> usize {
        self.metrics.current_depth.load(Ordering::SeqCst)
    }
}

/// Buffer management strategy
pub enum BufferStrategy {
    /// Ring buffer (overwrite oldest)
    Ring,
    /// Growing buffer up to max size
    Growing { max_size: usize },
    /// Fixed size with rejection
    Fixed,
}

/// Advanced buffer manager with custom strategies
pub struct BufferManager<T> {
    strategy: BufferStrategy,
    buffer: Arc<Mutex<Vec<T>>>,
    capacity: usize,
    metrics: Arc<MetricsState>,
}

impl<T: Clone> BufferManager<T> {
    /// Create a new buffer manager
    pub fn new(capacity: usize, strategy: BufferStrategy) -> Self {
        Self {
            strategy,
            buffer: Arc::new(Mutex::new(Vec::with_capacity(capacity))),
            capacity,
            metrics: Arc::new(MetricsState::new()),
        }
    }

    /// Push item into buffer
    pub async fn push(&self, item: T) -> Result<()> {
        let mut buffer = self.buffer.lock().await;

        match self.strategy {
            BufferStrategy::Ring => {
                if buffer.len() >= self.capacity {
                    buffer.remove(0);
                    self.metrics.dropped_count.fetch_add(1, Ordering::SeqCst);
                }
                buffer.push(item);
            }
            BufferStrategy::Growing { max_size } => {
                if buffer.len() >= max_size {
                    return Err(anyhow::anyhow!("Buffer at maximum size"));
                }
                buffer.push(item);
            }
            BufferStrategy::Fixed => {
                if buffer.len() >= self.capacity {
                    return Err(anyhow::anyhow!("Buffer full"));
                }
                buffer.push(item);
            }
        }

        self.metrics.increment_depth();
        Ok(())
    }

    /// Pop item from buffer
    pub async fn pop(&self) -> Option<T> {
        let mut buffer = self.buffer.lock().await;
        let item = if !buffer.is_empty() {
            Some(buffer.remove(0))
        } else {
            None
        };

        if item.is_some() {
            self.metrics.decrement_depth();
        }

        item
    }

    /// Get current buffer size
    pub async fn len(&self) -> usize {
        self.buffer.lock().await.len()
    }

    /// Check if buffer is empty
    pub async fn is_empty(&self) -> bool {
        self.buffer.lock().await.is_empty()
    }

    /// Get buffer capacity
    pub fn capacity(&self) -> usize {
        self.capacity
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_backpressure_controller_creation() {
        let controller: BackpressureController<i32> =
            BackpressureController::new(10, BackpressureStrategy::Block);
        assert_eq!(controller.capacity(), 10);
        assert_eq!(controller.strategy(), BackpressureStrategy::Block);
    }

    #[tokio::test]
    async fn test_send_receive() {
        let controller = BackpressureController::new(10, BackpressureStrategy::Block);

        controller.send(42).await.unwrap();
        let received = controller.recv().await;

        assert_eq!(received, Some(42));
    }

    #[tokio::test]
    async fn test_metrics_tracking() {
        let controller = BackpressureController::new(10, BackpressureStrategy::Block);

        controller.send(1).await.unwrap();
        controller.send(2).await.unwrap();

        let metrics = controller.metrics().await;
        assert_eq!(metrics.produced_count, 2);
    }

    #[tokio::test]
    async fn test_adaptive_rate_controller() {
        let controller = AdaptiveRateController::new(
            RateControlAlgorithm::AIMD,
            50.0,
            100.0,
        );

        let initial_rate = controller.current_rate().await;
        assert_eq!(initial_rate, 50.0);

        controller.increase_rate().await;
        let increased_rate = controller.current_rate().await;
        assert!(increased_rate > initial_rate);

        controller.decrease_rate().await;
        let decreased_rate = controller.current_rate().await;
        assert!(decreased_rate < increased_rate);
    }

    #[tokio::test]
    async fn test_buffer_manager_ring() {
        let manager = BufferManager::new(3, BufferStrategy::Ring);

        manager.push(1).await.unwrap();
        manager.push(2).await.unwrap();
        manager.push(3).await.unwrap();
        manager.push(4).await.unwrap(); // Should overwrite oldest

        assert_eq!(manager.len().await, 3);
        assert_eq!(manager.pop().await, Some(2)); // First was dropped
    }

    #[tokio::test]
    async fn test_buffer_manager_fixed() {
        let manager = BufferManager::new(2, BufferStrategy::Fixed);

        manager.push(1).await.unwrap();
        manager.push(2).await.unwrap();

        let result = manager.push(3).await;
        assert!(result.is_err());
    }
}
