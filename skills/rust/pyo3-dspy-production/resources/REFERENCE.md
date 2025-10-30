# PyO3 DSPy Production - Complete Reference

Comprehensive production deployment guide for DSPy applications from Rust, covering multi-level caching, circuit breakers, metrics collection, structured logging, cost tracking, rate limiting, A/B testing, health checks, deployment, and monitoring.

## Table of Contents

1. [Multi-Level Caching](#multi-level-caching)
2. [Circuit Breakers](#circuit-breakers)
3. [Metrics Collection](#metrics-collection)
4. [Structured Logging](#structured-logging)
5. [Cost Tracking](#cost-tracking)
6. [Rate Limiting](#rate-limiting)
7. [A/B Testing](#ab-testing)
8. [Health Checks](#health-checks)
9. [Deployment](#deployment)
10. [Monitoring Dashboards](#monitoring-dashboards)
11. [Best Practices Summary](#best-practices-summary)

---

## Multi-Level Caching

### Architecture

**Cache hierarchy**: Memory (L1) → Redis (L2) → LM API

**Benefits**:
- Reduce latency: Cached responses are 100-1000x faster
- Lower costs: Avoid repeated expensive LM calls
- Improve reliability: Serve cached results when LM API is down

### Dependencies

```toml
[dependencies]
redis = { version = "0.24", features = ["tokio-comp", "connection-manager"] }
lru = "0.12"
blake3 = "1.5"  # Fast hashing for cache keys
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
```

### Complete Implementation

```rust
use anyhow::{Context, Result};
use lru::LruCache;
use pyo3::prelude::*;
use redis::AsyncCommands;
use serde::{Deserialize, Serialize};
use std::num::NonZeroUsize;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CachedPrediction {
    pub answer: String,
    pub reasoning: Option<String>,
    pub metadata: CacheMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheMetadata {
    pub cached: bool,
    pub cache_level: Option<String>,  // "memory" or "redis"
    pub timestamp: u64,
    pub model: String,
    pub input_hash: String,
}

pub struct MultiLevelCache {
    // L1: In-memory LRU cache
    memory: Arc<RwLock<LruCache<String, CachedPrediction>>>,

    // L2: Redis distributed cache
    redis: redis::aio::ConnectionManager,

    // Configuration
    memory_capacity: usize,
    redis_ttl_secs: usize,
}

impl MultiLevelCache {
    pub async fn new(
        redis_url: &str,
        memory_capacity: usize,
        redis_ttl_secs: usize,
    ) -> Result<Self> {
        let client = redis::Client::open(redis_url)
            .context("Failed to connect to Redis")?;

        let redis = client.get_connection_manager().await
            .context("Failed to get Redis connection manager")?;

        Ok(Self {
            memory: Arc::new(RwLock::new(
                LruCache::new(NonZeroUsize::new(memory_capacity).unwrap())
            )),
            redis,
            memory_capacity,
            redis_ttl_secs,
        })
    }

    /// Generate deterministic cache key from input
    fn cache_key(&self, input: &str, model: &str) -> String {
        let combined = format!("{}:{}", model, input);
        let hash = blake3::hash(combined.as_bytes());
        format!("dspy:v1:prediction:{}", hash.to_hex())
    }

    /// Check L1 memory cache
    pub async fn get_memory(&self, key: &str) -> Option<CachedPrediction> {
        let cache = self.memory.read().await;
        cache.peek(key).cloned()
    }

    /// Check L2 Redis cache
    pub async fn get_redis(&mut self, key: &str) -> Result<Option<CachedPrediction>> {
        let value: Option<String> = self.redis.get(key).await?;

        match value {
            Some(json) => {
                let cached: CachedPrediction = serde_json::from_str(&json)
                    .context("Failed to deserialize cached prediction")?;
                Ok(Some(cached))
            }
            None => Ok(None),
        }
    }

    /// Store in L1 memory cache
    pub async fn put_memory(&self, key: String, value: CachedPrediction) {
        let mut cache = self.memory.write().await;
        cache.put(key, value);
    }

    /// Store in L2 Redis cache
    pub async fn put_redis(&mut self, key: &str, value: &CachedPrediction) -> Result<()> {
        let json = serde_json::to_string(value)
            .context("Failed to serialize prediction")?;

        self.redis.set_ex(key, json, self.redis_ttl_secs).await?;
        Ok(())
    }

    /// Get from cache (L1 then L2)
    pub async fn get(&mut self, key: &str) -> Result<Option<CachedPrediction>> {
        // Check L1
        if let Some(cached) = self.get_memory(key).await {
            let mut result = cached.clone();
            result.metadata.cache_level = Some("memory".to_string());
            return Ok(Some(result));
        }

        // Check L2
        if let Some(cached) = self.get_redis(key).await? {
            // Promote to L1
            self.put_memory(key.to_string(), cached.clone()).await;

            let mut result = cached;
            result.metadata.cache_level = Some("redis".to_string());
            return Ok(Some(result));
        }

        Ok(None)
    }

    /// Store in both caches
    pub async fn put(&mut self, key: String, value: CachedPrediction) -> Result<()> {
        self.put_memory(key.clone(), value.clone()).await;
        self.put_redis(&key, &value).await?;
        Ok(())
    }

    /// Clear all caches
    pub async fn clear(&mut self) -> Result<()> {
        // Clear memory
        self.memory.write().await.clear();

        // Clear Redis (pattern-based deletion)
        let pattern = "dspy:v1:prediction:*";
        let keys: Vec<String> = self.redis.keys(pattern).await?;

        if !keys.is_empty() {
            self.redis.del(&keys).await?;
        }

        Ok(())
    }

    /// Invalidate specific key
    pub async fn invalidate(&mut self, key: &str) -> Result<()> {
        // Remove from memory
        self.memory.write().await.pop(key);

        // Remove from Redis
        self.redis.del(key).await?;

        Ok(())
    }

    /// Get cache statistics
    pub async fn stats(&self) -> CacheStats {
        let memory_size = self.memory.read().await.len();

        CacheStats {
            memory_size,
            memory_capacity: self.memory_capacity,
            redis_ttl_secs: self.redis_ttl_secs,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheStats {
    pub memory_size: usize,
    pub memory_capacity: usize,
    pub redis_ttl_secs: usize,
}

/// Complete cached prediction service
pub struct CachedPredictionService {
    cache: MultiLevelCache,
    predictor: Py<PyAny>,
    model_name: String,
}

impl CachedPredictionService {
    pub async fn new(
        redis_url: &str,
        signature: &str,
        model_name: String,
        memory_capacity: usize,
        redis_ttl_secs: usize,
    ) -> Result<Self> {
        let cache = MultiLevelCache::new(redis_url, memory_capacity, redis_ttl_secs).await?;

        let predictor = Python::with_gil(|py| -> PyResult<Py<PyAny>> {
            let dspy = PyModule::import(py, "dspy")?;
            let predict = dspy.getattr("Predict")?;
            let pred = predict.call1(((signature,),))?;
            Ok(pred.into())
        })?;

        Ok(Self {
            cache,
            predictor,
            model_name,
        })
    }

    pub async fn predict(&mut self, input: String) -> Result<CachedPrediction> {
        let key = self.cache.cache_key(&input, &self.model_name);

        // Try cache first
        if let Some(cached) = self.cache.get(&key).await? {
            return Ok(cached);
        }

        // Cache miss: call LM
        let prediction = self.call_lm(&input).await?;

        // Store in cache
        self.cache.put(key, prediction.clone()).await?;

        Ok(prediction)
    }

    async fn call_lm(&self, input: &str) -> Result<CachedPrediction> {
        let answer = Python::with_gil(|py| -> PyResult<String> {
            let result = self.predictor.as_ref(py).call1(((input,),))?;
            result.getattr("answer")?.extract()
        })?;

        let input_hash = blake3::hash(input.as_bytes()).to_hex().to_string();

        Ok(CachedPrediction {
            answer,
            reasoning: None,
            metadata: CacheMetadata {
                cached: false,
                cache_level: None,
                timestamp: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)?
                    .as_secs(),
                model: self.model_name.clone(),
                input_hash,
            },
        })
    }
}
```

### Cache Warming

**Preload frequently accessed predictions**:

```rust
impl CachedPredictionService {
    /// Warm cache with common queries
    pub async fn warm_cache(&mut self, queries: Vec<String>) -> Result<()> {
        for query in queries {
            let _ = self.predict(query).await;
        }
        Ok(())
    }
}

// Usage
async fn startup_cache_warming() -> Result<()> {
    let mut service = CachedPredictionService::new(
        "redis://localhost:6379",
        "question -> answer",
        "gpt-3.5-turbo".to_string(),
        1000,
        3600,
    ).await?;

    let common_queries = vec![
        "What is Rust?".to_string(),
        "Explain async/await".to_string(),
        "How does PyO3 work?".to_string(),
    ];

    service.warm_cache(common_queries).await?;

    Ok(())
}
```

### Cache Invalidation Strategies

**1. Time-based (TTL)**:
```rust
// Already implemented via redis_ttl_secs
```

**2. Manual invalidation**:
```rust
// Invalidate on model update
service.cache.clear().await?;
```

**3. Selective invalidation**:
```rust
// Invalidate specific prediction
let key = service.cache.cache_key(&query, &model);
service.cache.invalidate(&key).await?;
```

**4. Version-based**:
```rust
// Include model version in cache key
fn cache_key(&self, input: &str, model: &str, version: &str) -> String {
    let combined = format!("{}:{}:{}", model, version, input);
    let hash = blake3::hash(combined.as_bytes());
    format!("dspy:v1:prediction:{}", hash.to_hex())
}
```

### Best Practices

**DO**:
- ✅ Use fast hashing (blake3) for cache keys
- ✅ Include model version in cache key
- ✅ Set appropriate TTLs (1 hour for most cases)
- ✅ Monitor cache hit rates
- ✅ Implement cache warming for hot paths
- ✅ Use connection pooling for Redis

**DON'T**:
- ❌ Cache sensitive or personal data without encryption
- ❌ Use unbounded memory cache (always set capacity)
- ❌ Forget to invalidate cache on model updates
- ❌ Cache errors or failed predictions
- ❌ Use slow hash functions (MD5, SHA256) for keys

---

## Circuit Breakers

### Purpose

**Prevent cascading failures** when LM APIs are down or degraded.

**States**:
- **Closed**: Normal operation, requests flow through
- **Open**: Too many failures, reject immediately
- **Half-Open**: Test if service recovered

### Dependencies

```toml
[dependencies]
failsafe = "1.0"
tokio = { version = "1", features = ["full"] }
```

### Implementation

```rust
use failsafe::{CircuitBreaker, Config as CBConfig, Error as CBError};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;

pub struct CircuitBreakerService {
    predictor: Py<PyAny>,
    circuit_breaker: Arc<Mutex<CircuitBreaker>>,
    fallback_response: Option<String>,
}

impl CircuitBreakerService {
    pub fn new(
        signature: &str,
        failure_threshold: usize,
        success_threshold: usize,
        timeout: Duration,
        fallback_response: Option<String>,
    ) -> Result<Self> {
        let predictor = Python::with_gil(|py| -> PyResult<Py<PyAny>> {
            let dspy = PyModule::import(py, "dspy")?;
            let predict = dspy.getattr("Predict")?;
            let pred = predict.call1(((signature,),))?;
            Ok(pred.into())
        })?;

        let cb_config = CBConfig::new()
            .failure_threshold(failure_threshold)
            .success_threshold(success_threshold)
            .timeout(timeout);

        let circuit_breaker = Arc::new(Mutex::new(
            CircuitBreaker::new(cb_config)
        ));

        Ok(Self {
            predictor,
            circuit_breaker,
            fallback_response,
        })
    }

    pub async fn predict(&self, input: String) -> Result<String> {
        let cb = self.circuit_breaker.lock().await;

        match cb.call(|| self.call_lm(&input)) {
            Ok(answer) => Ok(answer),
            Err(CBError::Rejected) => {
                // Circuit open: use fallback
                tracing::warn!("Circuit breaker open, using fallback");

                match &self.fallback_response {
                    Some(fallback) => Ok(fallback.clone()),
                    None => Err(anyhow::anyhow!("Service unavailable")),
                }
            }
            Err(CBError::Execution(e)) => {
                tracing::error!("LM call failed: {}", e);
                Err(anyhow::anyhow!("Prediction failed: {}", e))
            }
        }
    }

    fn call_lm(&self, input: &str) -> Result<String> {
        Python::with_gil(|py| -> Result<String> {
            let result = self.predictor.as_ref(py)
                .call1(((input,),))
                .context("DSPy prediction failed")?;

            let answer: String = result.getattr("answer")?.extract()?;
            Ok(answer)
        })
    }

    pub async fn state(&self) -> String {
        let cb = self.circuit_breaker.lock().await;
        format!("{:?}", cb.state())
    }

    pub async fn reset(&self) {
        let mut cb = self.circuit_breaker.lock().await;
        cb.reset();
    }
}
```

### Advanced Circuit Breaker

**With exponential backoff and metrics**:

```rust
use std::time::{Duration, Instant};

pub struct AdvancedCircuitBreaker {
    predictor: Py<PyAny>,

    // State
    state: Arc<RwLock<CBState>>,

    // Configuration
    failure_threshold: usize,
    success_threshold: usize,
    timeout: Duration,
    max_backoff: Duration,
}

#[derive(Debug, Clone)]
enum CBState {
    Closed,
    Open { opened_at: Instant },
    HalfOpen { successes: usize },
}

impl AdvancedCircuitBreaker {
    pub fn new(
        signature: &str,
        failure_threshold: usize,
        success_threshold: usize,
        timeout: Duration,
        max_backoff: Duration,
    ) -> Result<Self> {
        let predictor = Python::with_gil(|py| -> PyResult<Py<PyAny>> {
            let dspy = PyModule::import(py, "dspy")?;
            let predict = dspy.getattr("Predict")?;
            let pred = predict.call1(((signature,),))?;
            Ok(pred.into())
        })?;

        Ok(Self {
            predictor,
            state: Arc::new(RwLock::new(CBState::Closed)),
            failure_threshold,
            success_threshold,
            timeout,
            max_backoff,
        })
    }

    pub async fn predict(&self, input: String) -> Result<String> {
        // Check if circuit should transition to half-open
        self.check_timeout().await;

        let state = self.state.read().await.clone();

        match state {
            CBState::Closed => {
                match self.try_call(&input).await {
                    Ok(answer) => Ok(answer),
                    Err(e) => {
                        self.record_failure().await;
                        Err(e)
                    }
                }
            }
            CBState::Open { .. } => {
                // Record metric
                CIRCUIT_BREAKER_REJECTIONS.inc();
                Err(anyhow::anyhow!("Circuit breaker open"))
            }
            CBState::HalfOpen { .. } => {
                match self.try_call(&input).await {
                    Ok(answer) => {
                        self.record_success().await;
                        Ok(answer)
                    }
                    Err(e) => {
                        self.record_failure().await;
                        Err(e)
                    }
                }
            }
        }
    }

    async fn try_call(&self, input: &str) -> Result<String> {
        Python::with_gil(|py| -> Result<String> {
            let result = self.predictor.as_ref(py)
                .call1(((input,),))
                .context("DSPy prediction failed")?;

            let answer: String = result.getattr("answer")?.extract()?;
            Ok(answer)
        })
    }

    async fn record_failure(&self) {
        let mut state = self.state.write().await;

        match *state {
            CBState::Closed => {
                // Transition to open
                *state = CBState::Open { opened_at: Instant::now() };
                CIRCUIT_BREAKER_STATE.set(1.0);  // 1 = open
                tracing::warn!("Circuit breaker opened");
            }
            CBState::HalfOpen { .. } => {
                // Transition back to open
                *state = CBState::Open { opened_at: Instant::now() };
                CIRCUIT_BREAKER_STATE.set(1.0);
                tracing::warn!("Circuit breaker reopened");
            }
            _ => {}
        }
    }

    async fn record_success(&self) {
        let mut state = self.state.write().await;

        if let CBState::HalfOpen { successes } = *state {
            if successes + 1 >= self.success_threshold {
                // Transition to closed
                *state = CBState::Closed;
                CIRCUIT_BREAKER_STATE.set(0.0);  // 0 = closed
                tracing::info!("Circuit breaker closed");
            } else {
                *state = CBState::HalfOpen { successes: successes + 1 };
            }
        }
    }

    async fn check_timeout(&self) {
        let mut state = self.state.write().await;

        if let CBState::Open { opened_at } = *state {
            if opened_at.elapsed() >= self.timeout {
                // Transition to half-open
                *state = CBState::HalfOpen { successes: 0 };
                CIRCUIT_BREAKER_STATE.set(0.5);  // 0.5 = half-open
                tracing::info!("Circuit breaker half-open");
            }
        }
    }
}
```

### Best Practices

**DO**:
- ✅ Set appropriate failure threshold (3-5 failures)
- ✅ Implement exponential backoff
- ✅ Provide meaningful fallback responses
- ✅ Monitor circuit breaker state
- ✅ Test circuit breaker behavior
- ✅ Log state transitions

**DON'T**:
- ❌ Use circuit breakers for validation errors (only transient failures)
- ❌ Set timeout too short (allow time for recovery)
- ❌ Forget to implement half-open state
- ❌ Return cached data as fallback (can be stale)

---

## Metrics Collection

### Prometheus Integration

**Complete metrics implementation**:

```rust
use lazy_static::lazy_static;
use prometheus::{
    register_counter_vec, register_histogram_vec, register_gauge,
    CounterVec, HistogramVec, Gauge, Encoder, TextEncoder,
};

lazy_static! {
    // Request counter
    pub static ref PREDICTIONS_TOTAL: CounterVec = register_counter_vec!(
        "dspy_predictions_total",
        "Total number of DSPy predictions",
        &["model", "status", "variant"]
    ).unwrap();

    // Latency histogram
    pub static ref PREDICTION_DURATION: HistogramVec = register_histogram_vec!(
        "dspy_prediction_duration_seconds",
        "DSPy prediction latency",
        &["model", "cached"],
        vec![0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
    ).unwrap();

    // Cache metrics
    pub static ref CACHE_HITS: CounterVec = register_counter_vec!(
        "dspy_cache_hits_total",
        "Cache hits by level",
        &["level"]  // "memory" or "redis"
    ).unwrap();

    pub static ref CACHE_MISSES: CounterVec = register_counter_vec!(
        "dspy_cache_misses_total",
        "Cache misses",
        &["model"]
    ).unwrap();

    pub static ref CACHE_SIZE: Gauge = register_gauge!(
        "dspy_cache_size_bytes",
        "Current cache size in bytes"
    ).unwrap();

    // Active requests
    pub static ref ACTIVE_REQUESTS: Gauge = register_gauge!(
        "dspy_active_requests",
        "Number of active DSPy requests"
    ).unwrap();

    // Circuit breaker state
    pub static ref CIRCUIT_BREAKER_STATE: Gauge = register_gauge!(
        "dspy_circuit_breaker_open",
        "Circuit breaker state (0=closed, 0.5=half-open, 1=open)"
    ).unwrap();

    pub static ref CIRCUIT_BREAKER_REJECTIONS: CounterVec = register_counter_vec!(
        "dspy_circuit_breaker_rejections_total",
        "Requests rejected by circuit breaker",
        &["model"]
    ).unwrap();

    // Token usage
    pub static ref TOKENS_USED: CounterVec = register_counter_vec!(
        "dspy_tokens_used_total",
        "Total tokens used",
        &["model", "type"]  // type: "prompt" or "completion"
    ).unwrap();

    // Cost metrics
    pub static ref COST_USD: CounterVec = register_counter_vec!(
        "dspy_cost_usd_total",
        "Total cost in USD",
        &["model"]
    ).unwrap();

    // Error metrics
    pub static ref ERRORS: CounterVec = register_counter_vec!(
        "dspy_errors_total",
        "Total errors",
        &["model", "error_type"]
    ).unwrap();
}

/// Instrumented prediction service
pub struct MetricsService {
    cache_service: CachedPredictionService,
    circuit_breaker: AdvancedCircuitBreaker,
    model_name: String,
}

impl MetricsService {
    pub async fn new(
        redis_url: &str,
        signature: &str,
        model_name: String,
    ) -> Result<Self> {
        let cache_service = CachedPredictionService::new(
            redis_url,
            signature,
            model_name.clone(),
            1000,
            3600,
        ).await?;

        let circuit_breaker = AdvancedCircuitBreaker::new(
            signature,
            5,  // failure threshold
            2,  // success threshold
            Duration::from_secs(30),
            Duration::from_secs(300),
        )?;

        Ok(Self {
            cache_service,
            circuit_breaker,
            model_name,
        })
    }

    pub async fn predict(&mut self, input: String) -> Result<String> {
        ACTIVE_REQUESTS.inc();

        let timer = PREDICTION_DURATION
            .with_label_values(&[&self.model_name, "unknown"])
            .start_timer();

        let result = self.cache_service.predict(input).await;

        ACTIVE_REQUESTS.dec();

        match result {
            Ok(prediction) => {
                // Record success
                PREDICTIONS_TOTAL
                    .with_label_values(&[&self.model_name, "success", "default"])
                    .inc();

                // Record cache metrics
                if let Some(cache_level) = &prediction.metadata.cache_level {
                    CACHE_HITS.with_label_values(&[cache_level]).inc();

                    // Update timer with cache status
                    drop(timer);
                    PREDICTION_DURATION
                        .with_label_values(&[&self.model_name, "true"])
                        .observe(0.001);
                } else {
                    CACHE_MISSES.with_label_values(&[&self.model_name]).inc();
                    drop(timer);  // Records actual duration
                }

                Ok(prediction.answer)
            }
            Err(e) => {
                // Record failure
                PREDICTIONS_TOTAL
                    .with_label_values(&[&self.model_name, "error", "default"])
                    .inc();

                // Categorize error
                let error_type = if e.to_string().contains("timeout") {
                    "timeout"
                } else if e.to_string().contains("rate_limit") {
                    "rate_limit"
                } else {
                    "unknown"
                };

                ERRORS.with_label_values(&[&self.model_name, error_type]).inc();

                drop(timer);
                Err(e)
            }
        }
    }

    /// Export metrics in Prometheus format
    pub fn metrics(&self) -> Result<String> {
        let encoder = TextEncoder::new();
        let metric_families = prometheus::gather();
        let mut buffer = Vec::new();
        encoder.encode(&metric_families, &mut buffer)?;
        Ok(String::from_utf8(buffer)?)
    }
}
```

### HTTP Metrics Endpoint

**Using Axum**:

```rust
use axum::{
    routing::get,
    Router,
};
use std::net::SocketAddr;

async fn metrics_handler() -> String {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();
    encoder.encode(&metric_families, &mut buffer).unwrap();
    String::from_utf8(buffer).unwrap()
}

pub async fn start_metrics_server(port: u16) -> Result<()> {
    let app = Router::new().route("/metrics", get(metrics_handler));

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    tracing::info!("Metrics server listening on {}", addr);

    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await?;

    Ok(())
}
```

### Custom Metrics

**Business-specific metrics**:

```rust
lazy_static! {
    // Question complexity
    pub static ref QUESTION_COMPLEXITY: HistogramVec = register_histogram_vec!(
        "dspy_question_complexity",
        "Question complexity score",
        &["category"],
        vec![1.0, 2.0, 3.0, 4.0, 5.0]
    ).unwrap();

    // Answer quality
    pub static ref ANSWER_QUALITY: HistogramVec = register_histogram_vec!(
        "dspy_answer_quality_score",
        "Answer quality score from 0-1",
        &["model"],
        vec![0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
    ).unwrap();
}

impl MetricsService {
    pub async fn predict_with_quality(&mut self, input: String) -> Result<ScoredAnswer> {
        let answer = self.predict(input.clone()).await?;

        // Calculate quality score (simplified)
        let quality_score = self.score_answer(&answer);

        ANSWER_QUALITY
            .with_label_values(&[&self.model_name])
            .observe(quality_score);

        Ok(ScoredAnswer {
            answer,
            quality_score,
        })
    }

    fn score_answer(&self, answer: &str) -> f64 {
        // Implement quality scoring logic
        // Could use length, coherence, factuality, etc.
        0.85  // Placeholder
    }
}

#[derive(Debug, Serialize)]
pub struct ScoredAnswer {
    pub answer: String,
    pub quality_score: f64,
}
```

---

## Structured Logging

### Tracing Setup

```toml
[dependencies]
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["json", "env-filter"] }
tracing-opentelemetry = "0.21"
opentelemetry = "0.21"
opentelemetry-jaeger = "0.20"
```

### Implementation

```rust
use tracing::{info, warn, error, debug, instrument, Span};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

pub fn init_tracing(service_name: &str) -> Result<()> {
    tracing_subscriber::registry()
        .with(EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into())
        ))
        .with(tracing_subscriber::fmt::layer().json())
        .init();

    info!(service = service_name, "Tracing initialized");
    Ok(())
}

pub struct LoggingService {
    predictor: Py<PyAny>,
    service_name: String,
}

impl LoggingService {
    #[instrument(skip(self), fields(service = %self.service_name))]
    pub async fn predict(&self, input: String, request_id: String) -> Result<String> {
        let span = Span::current();
        span.record("request_id", &request_id.as_str());
        span.record("input_length", input.len());

        info!(
            request_id = %request_id,
            input_length = input.len(),
            "Starting prediction"
        );

        let start = std::time::Instant::now();

        let result = Python::with_gil(|py| -> Result<String> {
            debug!(request_id = %request_id, "Acquiring GIL");

            let py_result = self.predictor.as_ref(py)
                .call1(((input.as_str(),),))
                .context("DSPy call failed")?;

            let answer: String = py_result.getattr("answer")?.extract()?;

            debug!(
                request_id = %request_id,
                answer_length = answer.len(),
                "Extracted answer"
            );

            Ok(answer)
        });

        let duration = start.elapsed();

        match &result {
            Ok(answer) => {
                info!(
                    request_id = %request_id,
                    duration_ms = duration.as_millis(),
                    answer_length = answer.len(),
                    "Prediction completed"
                );
            }
            Err(e) => {
                error!(
                    request_id = %request_id,
                    duration_ms = duration.as_millis(),
                    error = %e,
                    "Prediction failed"
                );
            }
        }

        result
    }
}
```

### Structured Log Fields

**Standard fields for DSPy operations**:

```rust
#[derive(Debug, Serialize)]
pub struct PredictionLogEntry {
    pub timestamp: String,
    pub request_id: String,
    pub service: String,
    pub model: String,
    pub input_hash: String,
    pub cache_hit: bool,
    pub cache_level: Option<String>,
    pub duration_ms: u64,
    pub tokens: Option<TokenUsage>,
    pub cost_usd: Option<f64>,
    pub status: String,
    pub error: Option<String>,
}

impl LoggingService {
    pub async fn predict_with_logging(&self, input: String, request_id: String) -> Result<String> {
        let start = std::time::Instant::now();
        let input_hash = blake3::hash(input.as_bytes()).to_hex().to_string();

        let result = self.predict(input, request_id.clone()).await;
        let duration = start.elapsed();

        let log_entry = PredictionLogEntry {
            timestamp: chrono::Utc::now().to_rfc3339(),
            request_id: request_id.clone(),
            service: self.service_name.clone(),
            model: "gpt-3.5-turbo".to_string(),
            input_hash,
            cache_hit: false,  // Would come from cache metadata
            cache_level: None,
            duration_ms: duration.as_millis() as u64,
            tokens: None,  // Would come from token tracking
            cost_usd: None,
            status: if result.is_ok() { "success" } else { "error" }.to_string(),
            error: result.as_ref().err().map(|e| e.to_string()),
        };

        // Log as structured JSON
        info!(
            log = ?log_entry,
            "Prediction log entry"
        );

        result
    }
}
```

### Log Aggregation

**Send logs to external systems**:

```rust
use serde_json::json;

pub async fn send_to_loki(log_entry: &PredictionLogEntry) -> Result<()> {
    let client = reqwest::Client::new();

    let payload = json!({
        "streams": [{
            "stream": {
                "service": log_entry.service,
                "level": "info"
            },
            "values": [[
                log_entry.timestamp.clone(),
                serde_json::to_string(log_entry)?
            ]]
        }]
    });

    client.post("http://loki:3100/loki/api/v1/push")
        .json(&payload)
        .send()
        .await?;

    Ok(())
}
```

---

## Cost Tracking

### Token Usage Tracking

```rust
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenUsage {
    pub prompt_tokens: u64,
    pub completion_tokens: u64,
    pub total_tokens: u64,
}

pub struct CostTracker {
    // Atomic counters
    total_prompt_tokens: Arc<AtomicU64>,
    total_completion_tokens: Arc<AtomicU64>,
    total_cost_cents: Arc<AtomicU64>,  // Store as integer cents

    // Pricing (per 1M tokens)
    prompt_price_per_million: f64,
    completion_price_per_million: f64,

    // Budget limits
    daily_budget_cents: Option<u64>,
    monthly_budget_cents: Option<u64>,
}

impl CostTracker {
    pub fn new(
        prompt_price_per_million: f64,
        completion_price_per_million: f64,
        daily_budget_usd: Option<f64>,
        monthly_budget_usd: Option<f64>,
    ) -> Self {
        Self {
            total_prompt_tokens: Arc::new(AtomicU64::new(0)),
            total_completion_tokens: Arc::new(AtomicU64::new(0)),
            total_cost_cents: Arc::new(AtomicU64::new(0)),
            prompt_price_per_million,
            completion_price_per_million,
            daily_budget_cents: daily_budget_usd.map(|d| (d * 100.0) as u64),
            monthly_budget_cents: monthly_budget_usd.map(|m| (m * 100.0) as u64),
        }
    }

    pub fn record_usage(&self, usage: &TokenUsage) -> Result<f64> {
        // Calculate cost
        let prompt_cost = (usage.prompt_tokens as f64 / 1_000_000.0) * self.prompt_price_per_million;
        let completion_cost = (usage.completion_tokens as f64 / 1_000_000.0) * self.completion_price_per_million;
        let total_cost = prompt_cost + completion_cost;

        // Update counters
        self.total_prompt_tokens.fetch_add(usage.prompt_tokens, Ordering::Relaxed);
        self.total_completion_tokens.fetch_add(usage.completion_tokens, Ordering::Relaxed);
        self.total_cost_cents.fetch_add((total_cost * 100.0) as u64, Ordering::Relaxed);

        // Update Prometheus metrics
        TOKENS_USED
            .with_label_values(&["default", "prompt"])
            .inc_by(usage.prompt_tokens as f64);
        TOKENS_USED
            .with_label_values(&["default", "completion"])
            .inc_by(usage.completion_tokens as f64);
        COST_USD
            .with_label_values(&["default"])
            .inc_by(total_cost);

        // Check budget
        if let Some(daily_budget) = self.daily_budget_cents {
            let current_cost = self.total_cost_cents.load(Ordering::Relaxed);
            if current_cost > daily_budget {
                return Err(anyhow::anyhow!("Daily budget exceeded: ${:.2}", current_cost as f64 / 100.0));
            }
        }

        Ok(total_cost)
    }

    pub fn total_cost_usd(&self) -> f64 {
        self.total_cost_cents.load(Ordering::Relaxed) as f64 / 100.0
    }

    pub fn usage_report(&self) -> CostReport {
        let prompt_tokens = self.total_prompt_tokens.load(Ordering::Relaxed);
        let completion_tokens = self.total_completion_tokens.load(Ordering::Relaxed);
        let total_cost = self.total_cost_usd();

        CostReport {
            total_prompt_tokens: prompt_tokens,
            total_completion_tokens: completion_tokens,
            total_tokens: prompt_tokens + completion_tokens,
            total_cost_usd: total_cost,
            prompt_price_per_million: self.prompt_price_per_million,
            completion_price_per_million: self.completion_price_per_million,
            daily_budget_remaining_usd: self.daily_budget_cents.map(|b| {
                (b as f64 / 100.0) - total_cost
            }),
        }
    }

    pub fn reset_daily(&self) {
        self.total_prompt_tokens.store(0, Ordering::Relaxed);
        self.total_completion_tokens.store(0, Ordering::Relaxed);
        self.total_cost_cents.store(0, Ordering::Relaxed);
    }
}

#[derive(Debug, Serialize)]
pub struct CostReport {
    pub total_prompt_tokens: u64,
    pub total_completion_tokens: u64,
    pub total_tokens: u64,
    pub total_cost_usd: f64,
    pub prompt_price_per_million: f64,
    pub completion_price_per_million: f64,
    pub daily_budget_remaining_usd: Option<f64>,
}
```

### Cost Monitoring Service

```rust
pub struct CostMonitoringService {
    predictor: Py<PyAny>,
    cost_tracker: Arc<CostTracker>,
}

impl CostMonitoringService {
    pub async fn predict_with_cost(&self, input: String) -> Result<(String, f64)> {
        let (answer, usage) = Python::with_gil(|py| -> Result<(String, TokenUsage)> {
            let result = self.predictor.as_ref(py).call1(((input.as_str(),),))?;
            let answer: String = result.getattr("answer")?.extract()?;

            // Extract token usage from DSPy
            let usage = self.extract_usage(py, &result)?;

            Ok((answer, usage))
        })?;

        let cost = self.cost_tracker.record_usage(&usage)?;

        Ok((answer, cost))
    }

    fn extract_usage(&self, py: Python, result: &PyAny) -> Result<TokenUsage> {
        // Implementation depends on DSPy version
        // Simplified extraction
        let lm = py.import("dspy")?.getattr("settings")?.getattr("lm")?;

        let prompt_tokens = lm.getattr("prompt_tokens")
            .and_then(|t| t.extract::<u64>())
            .unwrap_or(0);

        let completion_tokens = lm.getattr("completion_tokens")
            .and_then(|t| t.extract::<u64>())
            .unwrap_or(0);

        Ok(TokenUsage {
            prompt_tokens,
            completion_tokens,
            total_tokens: prompt_tokens + completion_tokens,
        })
    }
}
```

---

## Rate Limiting

### Token Bucket Implementation

```rust
use std::time::{Duration, Instant};

pub struct RateLimiter {
    tokens: Arc<RwLock<f64>>,
    max_tokens: f64,
    refill_rate: f64,  // tokens per second
    last_refill: Arc<RwLock<Instant>>,
}

impl RateLimiter {
    pub fn new(max_requests_per_second: f64) -> Self {
        Self {
            tokens: Arc::new(RwLock::new(max_requests_per_second)),
            max_tokens: max_requests_per_second,
            refill_rate: max_requests_per_second,
            last_refill: Arc::new(RwLock::new(Instant::now())),
        }
    }

    pub async fn acquire(&self) -> Result<()> {
        loop {
            // Refill tokens
            self.refill().await;

            // Try to acquire
            let mut tokens = self.tokens.write().await;
            if *tokens >= 1.0 {
                *tokens -= 1.0;
                return Ok(());
            }

            // Wait and retry
            drop(tokens);
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    }

    async fn refill(&self) {
        let mut last_refill = self.last_refill.write().await;
        let now = Instant::now();
        let elapsed = now.duration_since(*last_refill).as_secs_f64();

        if elapsed > 0.0 {
            let mut tokens = self.tokens.write().await;
            let new_tokens = (*tokens + elapsed * self.refill_rate).min(self.max_tokens);
            *tokens = new_tokens;
            *last_refill = now;
        }
    }
}

pub struct RateLimitedService {
    predictor: Py<PyAny>,
    rate_limiter: Arc<RateLimiter>,
}

impl RateLimitedService {
    pub async fn predict(&self, input: String) -> Result<String> {
        // Wait for rate limit token
        self.rate_limiter.acquire().await?;

        // Make prediction
        Python::with_gil(|py| -> Result<String> {
            let result = self.predictor.as_ref(py).call1(((input.as_str(),),))?;
            let answer: String = result.getattr("answer")?.extract()?;
            Ok(answer)
        })
    }
}
```

---

## A/B Testing

### Complete Implementation

```rust
use rand::Rng;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct Variant {
    pub name: String,
    pub signature: String,
    pub model: String,
    pub weight: f64,  // 0.0 - 1.0
}

pub struct ABTestService {
    variants: Vec<Variant>,
    predictors: HashMap<String, Py<PyAny>>,

    // Statistics
    stats: Arc<RwLock<HashMap<String, VariantStatsInternal>>>,
}

#[derive(Debug, Clone)]
struct VariantStatsInternal {
    calls: u64,
    successes: u64,
    failures: u64,
    total_latency_ms: u64,
}

impl ABTestService {
    pub fn new(variants: Vec<Variant>) -> Result<Self> {
        // Validate weights sum to 1.0
        let total_weight: f64 = variants.iter().map(|v| v.weight).sum();
        if (total_weight - 1.0).abs() > 0.001 {
            return Err(anyhow::anyhow!("Variant weights must sum to 1.0, got {}", total_weight));
        }

        let mut predictors = HashMap::new();
        let mut stats_map = HashMap::new();

        Python::with_gil(|py| -> Result<()> {
            for variant in &variants {
                let dspy = PyModule::import(py, "dspy")?;

                // Configure LM for variant
                let lm = dspy.getattr("OpenAI")?.call1(((variant.model.as_str(),),))?;
                dspy.getattr("settings")?.call_method1("configure", ((lm,),))?;

                // Create predictor
                let predict = dspy.getattr("Predict")?;
                let predictor = predict.call1(((variant.signature.as_str(),),))?;

                predictors.insert(variant.name.clone(), predictor.into());

                stats_map.insert(variant.name.clone(), VariantStatsInternal {
                    calls: 0,
                    successes: 0,
                    failures: 0,
                    total_latency_ms: 0,
                });
            }
            Ok(())
        })?;

        Ok(Self {
            variants,
            predictors,
            stats: Arc::new(RwLock::new(stats_map)),
        })
    }

    fn select_variant(&self) -> &Variant {
        let mut rng = rand::thread_rng();
        let roll: f64 = rng.gen();

        let mut cumulative = 0.0;
        for variant in &self.variants {
            cumulative += variant.weight;
            if roll <= cumulative {
                return variant;
            }
        }

        &self.variants[0]
    }

    pub async fn predict(&self, input: String) -> Result<ABTestResult> {
        let variant = self.select_variant();
        let start = Instant::now();

        // Track call
        {
            let mut stats = self.stats.write().await;
            if let Some(stat) = stats.get_mut(&variant.name) {
                stat.calls += 1;
            }
        }

        let predictor = self.predictors.get(&variant.name)
            .ok_or_else(|| anyhow::anyhow!("Variant predictor not found"))?;

        let result = Python::with_gil(|py| -> Result<String> {
            let prediction = predictor.as_ref(py).call1(((input.as_str(),),))?;
            let answer: String = prediction.getattr("answer")?.extract()?;
            Ok(answer)
        });

        let latency = start.elapsed().as_millis() as u64;

        // Update stats
        {
            let mut stats = self.stats.write().await;
            if let Some(stat) = stats.get_mut(&variant.name) {
                stat.total_latency_ms += latency;

                match &result {
                    Ok(_) => stat.successes += 1,
                    Err(_) => stat.failures += 1,
                }
            }
        }

        match result {
            Ok(answer) => {
                Ok(ABTestResult {
                    answer,
                    variant_name: variant.name.clone(),
                    variant_model: variant.model.clone(),
                    latency_ms: latency,
                })
            }
            Err(e) => Err(e),
        }
    }

    pub async fn variant_stats(&self) -> Vec<VariantStats> {
        let stats = self.stats.read().await;

        self.variants.iter().map(|v| {
            let stat = stats.get(&v.name).unwrap();

            VariantStats {
                name: v.name.clone(),
                model: v.model.clone(),
                weight: v.weight,
                calls: stat.calls,
                successes: stat.successes,
                failures: stat.failures,
                success_rate: if stat.calls > 0 {
                    stat.successes as f64 / stat.calls as f64
                } else {
                    0.0
                },
                avg_latency_ms: if stat.calls > 0 {
                    stat.total_latency_ms / stat.calls
                } else {
                    0
                },
            }
        }).collect()
    }
}

#[derive(Debug, Serialize)]
pub struct ABTestResult {
    pub answer: String,
    pub variant_name: String,
    pub variant_model: String,
    pub latency_ms: u64,
}

#[derive(Debug, Serialize)]
pub struct VariantStats {
    pub name: String,
    pub model: String,
    pub weight: f64,
    pub calls: u64,
    pub successes: u64,
    pub failures: u64,
    pub success_rate: f64,
    pub avg_latency_ms: u64,
}
```

---

## Health Checks

### Implementation

```rust
use axum::{
    extract::State,
    http::StatusCode,
    response::IntoResponse,
    Json,
};

#[derive(Debug, Serialize)]
pub struct HealthStatus {
    pub status: String,  // "healthy", "degraded", "unhealthy"
    pub checks: HashMap<String, CheckResult>,
}

#[derive(Debug, Serialize)]
pub struct CheckResult {
    pub status: String,
    pub message: Option<String>,
    pub latency_ms: Option<u64>,
}

pub struct HealthChecker {
    redis: redis::aio::ConnectionManager,
    predictor: Py<PyAny>,
}

impl HealthChecker {
    pub async fn check(&mut self) -> HealthStatus {
        let mut checks = HashMap::new();

        // Check Redis
        checks.insert("redis".to_string(), self.check_redis().await);

        // Check DSPy/LM
        checks.insert("dspy".to_string(), self.check_dspy().await);

        // Overall status
        let status = if checks.values().all(|c| c.status == "healthy") {
            "healthy"
        } else if checks.values().any(|c| c.status == "unhealthy") {
            "unhealthy"
        } else {
            "degraded"
        };

        HealthStatus {
            status: status.to_string(),
            checks,
        }
    }

    async fn check_redis(&mut self) -> CheckResult {
        let start = Instant::now();

        match self.redis.ping::<String>().await {
            Ok(_) => CheckResult {
                status: "healthy".to_string(),
                message: None,
                latency_ms: Some(start.elapsed().as_millis() as u64),
            },
            Err(e) => CheckResult {
                status: "unhealthy".to_string(),
                message: Some(e.to_string()),
                latency_ms: None,
            },
        }
    }

    async fn check_dspy(&self) -> CheckResult {
        let start = Instant::now();

        let result = Python::with_gil(|py| -> Result<()> {
            let dspy = PyModule::import(py, "dspy")?;
            let _settings = dspy.getattr("settings")?;
            Ok(())
        });

        match result {
            Ok(_) => CheckResult {
                status: "healthy".to_string(),
                message: None,
                latency_ms: Some(start.elapsed().as_millis() as u64),
            },
            Err(e) => CheckResult {
                status: "unhealthy".to_string(),
                message: Some(e.to_string()),
                latency_ms: None,
            },
        }
    }
}

// HTTP handler
async fn health_handler(
    State(checker): State<Arc<RwLock<HealthChecker>>>,
) -> impl IntoResponse {
    let mut checker = checker.write().await;
    let health = checker.check().await;

    let status_code = match health.status.as_str() {
        "healthy" => StatusCode::OK,
        "degraded" => StatusCode::OK,
        "unhealthy" => StatusCode::SERVICE_UNAVAILABLE,
        _ => StatusCode::INTERNAL_SERVER_ERROR,
    };

    (status_code, Json(health))
}
```

---

## Deployment

### Cargo.toml (Production)

```toml
[package]
name = "dspy-production-service"
version = "0.1.0"
edition = "2021"

[dependencies]
# Core
pyo3 = { version = "0.20", features = ["auto-initialize", "abi3-py39"] }
tokio = { version = "1", features = ["full"] }

# Web framework
axum = "0.7"
tower = "0.4"
tower-http = { version = "0.5", features = ["trace", "cors"] }

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"

# Error handling
anyhow = "1"
thiserror = "1"

# Caching
redis = { version = "0.24", features = ["tokio-comp", "connection-manager"] }
lru = "0.12"
blake3 = "1.5"

# Observability
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["json", "env-filter"] }
prometheus = "0.13"

# Resilience
failsafe = "1.0"

# Utilities
lazy_static = "1.4"
rand = "0.8"
chrono = "0.4"

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
```

### Dockerfile

```dockerfile
FROM rust:1.75 as builder

WORKDIR /app

# Install Python
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Build dependencies (cached layer)
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -rf src

# Copy source
COPY src ./src

# Build application
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install Python runtime
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install DSPy and dependencies
RUN pip3 install --no-cache-dir \
    dspy-ai \
    openai \
    anthropic

# Copy binary
COPY --from=builder /app/target/release/dspy-production-service /usr/local/bin/

# Set environment
ENV RUST_LOG=info
ENV PYO3_PYTHON=python3.11

EXPOSE 8080 9090

CMD ["dspy-production-service"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  dspy-service:
    build: .
    ports:
      - "8080:8080"  # API
      - "9090:9090"  # Metrics
    environment:
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - RUST_LOG=info
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    restart: unless-stopped

volumes:
  redis-data:
  prometheus-data:
  grafana-data:
```

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'dspy-service'
    static_configs:
      - targets: ['dspy-service:9090']
    metrics_path: /metrics
```

---

## Monitoring Dashboards

### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "DSPy Production Service",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(dspy_predictions_total[5m])",
            "legendFormat": "{{status}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Latency (p50, p95, p99)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(dspy_prediction_duration_seconds_bucket[5m]))",
            "legendFormat": "p50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(dspy_prediction_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(dspy_prediction_duration_seconds_bucket[5m]))",
            "legendFormat": "p99"
          }
        ]
      },
      {
        "id": 3,
        "title": "Cache Hit Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(dspy_cache_hits_total[5m]) / (rate(dspy_cache_hits_total[5m]) + rate(dspy_cache_misses_total[5m]))",
            "legendFormat": "hit_rate"
          }
        ]
      },
      {
        "id": 4,
        "title": "Cost per Hour",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(dspy_cost_usd_total[1h])",
            "legendFormat": "{{model}}"
          }
        ]
      },
      {
        "id": 5,
        "title": "Circuit Breaker State",
        "type": "stat",
        "targets": [
          {
            "expr": "dspy_circuit_breaker_open",
            "legendFormat": "state"
          }
        ]
      }
    ]
  }
}
```

### Alert Rules

```yaml
# alert.rules.yml
groups:
  - name: dspy_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(dspy_predictions_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      - alert: CircuitBreakerOpen
        expr: dspy_circuit_breaker_open == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker is open"
          description: "DSPy service circuit breaker has opened"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(dspy_prediction_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "p95 latency is {{ $value }}s"

      - alert: BudgetExceeded
        expr: rate(dspy_cost_usd_total[1h]) > 10
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Hourly cost budget exceeded"
          description: "Current rate: ${{ $value }}/hour"
```

---

## Best Practices Summary

### Caching
- ✅ Use multi-level caching (memory + Redis)
- ✅ Hash inputs for deterministic keys
- ✅ Set appropriate TTLs
- ✅ Monitor cache hit rates
- ✅ Implement cache warming
- ❌ Don't cache sensitive data without encryption
- ❌ Don't forget to invalidate on model updates

### Circuit Breakers
- ✅ Set failure thresholds based on testing
- ✅ Implement half-open state
- ✅ Provide meaningful fallbacks
- ✅ Monitor circuit breaker state
- ❌ Don't use for validation errors
- ❌ Don't set timeout too short

### Metrics
- ✅ Expose Prometheus metrics
- ✅ Track request rate, latency, errors
- ✅ Monitor cache performance
- ✅ Track costs and token usage
- ❌ Don't create high-cardinality labels
- ❌ Don't forget to aggregate metrics

### Logging
- ✅ Use structured logging (JSON)
- ✅ Include request IDs
- ✅ Log timing information
- ✅ Send logs to aggregation system
- ❌ Don't log sensitive data
- ❌ Don't use synchronous logging in hot paths

### Cost Control
- ✅ Track token usage per request
- ✅ Set daily/monthly budgets
- ✅ Monitor cost trends
- ✅ Alert on budget overruns
- ❌ Don't allow unbounded spending
- ❌ Don't forget to track failed requests

### Deployment
- ✅ Use Docker for consistency
- ✅ Implement health checks
- ✅ Configure resource limits
- ✅ Use Redis for distributed caching
- ❌ Don't run without monitoring
- ❌ Don't skip load testing

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
