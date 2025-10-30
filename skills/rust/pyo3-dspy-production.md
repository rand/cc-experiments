---
name: pyo3-dspy-production
description: Production DSPy deployment from Rust - multi-level caching, circuit breakers, Prometheus metrics, structured logging
skill_id: rust-pyo3-dspy-production
title: PyO3 DSPy Production Deployment
category: rust
subcategory: pyo3-dspy
complexity: advanced
prerequisites:
  - rust-pyo3-dspy-fundamentals
  - rust-pyo3-dspy-async-streaming
  - ml-dspy-production
  - rust-observability
tags:
  - rust
  - python
  - pyo3
  - dspy
  - production
  - caching
  - monitoring
  - metrics
  - observability
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Deploy DSPy services in production with multi-level caching
  - Implement circuit breakers for resilient LM API calls
  - Collect and export Prometheus metrics from Rust DSPy services
  - Apply structured logging patterns for DSPy pipelines
  - Track and monitor LM API costs from Rust
  - Build A/B testing infrastructure for DSPy models
  - Design fault-tolerant production architectures
related_skills:
  - rust-pyo3-dspy-fundamentals
  - rust-pyo3-dspy-async-streaming
  - ml-dspy-production
  - rust-observability
  - caching-redis
resources:
  - Production deployment patterns
  - Monitoring and observability examples
  - Cost tracking implementations
  - A/B testing frameworks
---

# PyO3 DSPy Production Deployment

## Overview

Deploy production-grade DSPy applications from Rust with enterprise features: multi-level caching, circuit breakers, comprehensive monitoring, cost tracking, and A/B testing infrastructure. Learn to build resilient, observable, and cost-effective LLM services that scale.

This skill covers the critical production concerns beyond basic DSPy integration: caching expensive LM calls, handling failures gracefully, monitoring system health, controlling costs, and safely testing model improvements.

## Prerequisites

**Required**:
- PyO3 DSPy fundamentals (module calling, error handling)
- Async/streaming DSPy patterns (Tokio integration)
- Production Rust experience (error handling, logging, metrics)
- Redis or similar cache backend knowledge
- Prometheus metrics exposure

**Recommended**:
- Load testing and performance tuning
- Distributed tracing (OpenTelemetry)
- Cost optimization strategies
- A/B testing methodologies

## When to Use

**Ideal for**:
- **Production LLM services** serving real users
- **Cost-sensitive applications** needing strict budget control
- **High-availability systems** requiring resilience
- **Observable services** needing deep instrumentation
- **Model experimentation** with safe rollout strategies

**Not ideal for**:
- Development and prototyping (adds complexity)
- Single-user applications (overhead not justified)
- Stateless one-off scripts
- Systems with unlimited LM API budgets

## Learning Path

### 1. Multi-Level Caching

**Why**: LM API calls are expensive (latency + cost). Cache aggressively.

**Architecture**: Memory (L1) → Redis (L2) → LM API

**Cargo.toml**:
```toml
[dependencies]
pyo3 = { version = "0.20", features = ["auto-initialize"] }
tokio = { version = "1", features = ["full"] }
redis = { version = "0.24", features = ["tokio-comp", "connection-manager"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
lru = "0.12"
blake3 = "1"  # Fast hashing for cache keys
anyhow = "1"
```

**Implementation**:

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
    pub metadata: PredictionMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictionMetadata {
    pub cached: bool,
    pub cache_level: Option<String>,  // "memory" or "redis"
    pub timestamp: u64,
    pub model: String,
}

pub struct DSpyCacheService {
    // L1: In-memory LRU cache
    memory_cache: Arc<RwLock<LruCache<String, CachedPrediction>>>,

    // L2: Redis cache
    redis: redis::aio::ConnectionManager,

    // DSPy predictor
    predictor: Py<PyAny>,

    // Configuration
    memory_cache_size: usize,
    redis_ttl_secs: usize,
}

impl DSpyCacheService {
    pub async fn new(
        redis_url: &str,
        signature: &str,
        memory_cache_size: usize,
        redis_ttl_secs: usize,
    ) -> Result<Self> {
        // Initialize Redis
        let client = redis::Client::open(redis_url)
            .context("Failed to connect to Redis")?;
        let redis = client.get_connection_manager().await
            .context("Failed to get Redis connection manager")?;

        // Initialize DSPy predictor
        let predictor = Python::with_gil(|py| -> PyResult<Py<PyAny>> {
            let dspy = PyModule::import(py, "dspy")?;
            let predict = dspy.getattr("Predict")?;
            let pred = predict.call1(((signature,),))?;
            Ok(pred.into())
        })?;

        Ok(Self {
            memory_cache: Arc::new(RwLock::new(
                LruCache::new(NonZeroUsize::new(memory_cache_size).unwrap())
            )),
            redis,
            predictor,
            memory_cache_size,
            redis_ttl_secs,
        })
    }

    /// Generate cache key from input
    fn cache_key(&self, input: &str) -> String {
        let hash = blake3::hash(input.as_bytes());
        format!("dspy:prediction:{}", hash.to_hex())
    }

    /// Predict with multi-level caching
    pub async fn predict(&mut self, input: String) -> Result<CachedPrediction> {
        let key = self.cache_key(&input);

        // L1: Check memory cache
        {
            let cache = self.memory_cache.read().await;
            if let Some(cached) = cache.peek(&key) {
                let mut result = cached.clone();
                result.metadata.cache_level = Some("memory".to_string());
                return Ok(result);
            }
        }

        // L2: Check Redis
        if let Some(cached) = self.check_redis(&key).await? {
            // Promote to memory cache
            self.memory_cache.write().await.put(key.clone(), cached.clone());

            let mut result = cached;
            result.metadata.cache_level = Some("redis".to_string());
            return Ok(result);
        }

        // L3: Call LM API
        let prediction = self.call_lm(&input).await?;

        // Store in both caches
        self.store_in_redis(&key, &prediction).await?;
        self.memory_cache.write().await.put(key, prediction.clone());

        Ok(prediction)
    }

    /// Check Redis for cached prediction
    async fn check_redis(&mut self, key: &str) -> Result<Option<CachedPrediction>> {
        let value: Option<String> = self.redis.get(key).await?;

        match value {
            Some(json) => {
                let cached: CachedPrediction = serde_json::from_str(&json)?;
                Ok(Some(cached))
            }
            None => Ok(None),
        }
    }

    /// Store prediction in Redis
    async fn store_in_redis(&mut self, key: &str, prediction: &CachedPrediction) -> Result<()> {
        let json = serde_json::to_string(prediction)?;
        self.redis.set_ex(key, json, self.redis_ttl_secs).await?;
        Ok(())
    }

    /// Call DSPy LM (no cache)
    async fn call_lm(&self, input: &str) -> Result<CachedPrediction> {
        let answer = Python::with_gil(|py| -> PyResult<String> {
            let result = self.predictor.as_ref(py).call1(((input,),))?;
            result.getattr("answer")?.extract()
        })?;

        Ok(CachedPrediction {
            answer,
            metadata: PredictionMetadata {
                cached: false,
                cache_level: None,
                timestamp: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)?
                    .as_secs(),
                model: "default".to_string(),
            },
        })
    }

    /// Clear all caches (useful for model updates)
    pub async fn clear_caches(&mut self) -> Result<()> {
        // Clear memory
        self.memory_cache.write().await.clear();

        // Clear Redis keys (pattern-based)
        let pattern = "dspy:prediction:*";
        let keys: Vec<String> = self.redis.keys(pattern).await?;

        if !keys.is_empty() {
            self.redis.del(&keys).await?;
        }

        Ok(())
    }

    /// Get cache statistics
    pub async fn cache_stats(&self) -> CacheStats {
        let memory_size = self.memory_cache.read().await.len();

        CacheStats {
            memory_cache_size: memory_size,
            memory_cache_capacity: self.memory_cache_size,
            redis_ttl_secs: self.redis_ttl_secs,
        }
    }
}

#[derive(Debug, Serialize)]
pub struct CacheStats {
    pub memory_cache_size: usize,
    pub memory_cache_capacity: usize,
    pub redis_ttl_secs: usize,
}
```

**Usage**:

```rust
#[tokio::main]
async fn main() -> Result<()> {
    let mut service = DSpyCacheService::new(
        "redis://localhost:6379",
        "question -> answer",
        1000,  // Memory cache: 1000 entries
        3600,  // Redis TTL: 1 hour
    ).await?;

    // First call: hits LM
    let result1 = service.predict("What is Rust?".to_string()).await?;
    println!("Answer: {} (cached: {})",
        result1.answer,
        result1.metadata.cached
    );

    // Second call: hits memory cache
    let result2 = service.predict("What is Rust?".to_string()).await?;
    println!("Cache level: {:?}", result2.metadata.cache_level);

    Ok(())
}
```

### 2. Circuit Breakers

**Why**: LM APIs can fail. Circuit breakers prevent cascading failures.

**Pattern**: Closed → Open → Half-Open

**Dependencies**:
```toml
[dependencies]
failsafe = "1"  # Circuit breaker implementation
```

**Implementation**:

```rust
use failsafe::{CircuitBreaker, Config as CBConfig, Error as CBError};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;

pub struct ResilientDSpyService {
    predictor: Py<PyAny>,
    circuit_breaker: Arc<Mutex<CircuitBreaker>>,
}

impl ResilientDSpyService {
    pub fn new(signature: &str) -> Result<Self> {
        let predictor = Python::with_gil(|py| -> PyResult<Py<PyAny>> {
            let dspy = PyModule::import(py, "dspy")?;
            let predict = dspy.getattr("Predict")?;
            let pred = predict.call1(((signature,),))?;
            Ok(pred.into())
        })?;

        // Configure circuit breaker
        let cb_config = CBConfig::new()
            .failure_threshold(5)        // Open after 5 failures
            .success_threshold(2)        // Close after 2 successes
            .timeout(Duration::from_secs(30));

        let circuit_breaker = Arc::new(Mutex::new(
            CircuitBreaker::new(cb_config)
        ));

        Ok(Self {
            predictor,
            circuit_breaker,
        })
    }

    pub async fn predict_with_fallback(
        &self,
        input: String,
        fallback: Option<String>,
    ) -> Result<String> {
        let cb = self.circuit_breaker.lock().await;

        match cb.call(|| self.call_lm(&input)) {
            Ok(answer) => Ok(answer),
            Err(CBError::Rejected) => {
                // Circuit open: use fallback
                match fallback {
                    Some(fb) => {
                        log::warn!("Circuit breaker open, using fallback");
                        Ok(fb)
                    }
                    None => Err(anyhow::anyhow!("Circuit breaker open, no fallback")),
                }
            }
            Err(CBError::Execution(e)) => {
                // Execution failed
                Err(anyhow::anyhow!("LM call failed: {}", e))
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

    pub async fn circuit_state(&self) -> String {
        let cb = self.circuit_breaker.lock().await;
        format!("{:?}", cb.state())
    }
}
```

**Usage**:

```rust
#[tokio::main]
async fn main() -> Result<()> {
    let service = ResilientDSpyService::new("question -> answer")?;

    match service.predict_with_fallback(
        "What is machine learning?".to_string(),
        Some("I'm currently unavailable. Please try again later.".to_string()),
    ).await {
        Ok(answer) => println!("Answer: {}", answer),
        Err(e) => eprintln!("Error: {}", e),
    }

    println!("Circuit state: {}", service.circuit_state().await);

    Ok(())
}
```

### 3. Prometheus Metrics

**Why**: Monitor service health, performance, and usage.

**Dependencies**:
```toml
[dependencies]
prometheus = "0.13"
lazy_static = "1.4"
```

**Implementation**:

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
        &["model", "status"]
    ).unwrap();

    // Latency histogram
    pub static ref PREDICTION_DURATION: HistogramVec = register_histogram_vec!(
        "dspy_prediction_duration_seconds",
        "DSPy prediction latency",
        &["model", "cached"],
        vec![0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    ).unwrap();

    // Cache hit rate
    pub static ref CACHE_HITS: CounterVec = register_counter_vec!(
        "dspy_cache_hits_total",
        "Cache hits by level",
        &["level"]
    ).unwrap();

    pub static ref CACHE_MISSES: CounterVec = register_counter_vec!(
        "dspy_cache_misses_total",
        "Cache misses",
        &[]
    ).unwrap();

    // Active requests
    pub static ref ACTIVE_REQUESTS: Gauge = register_gauge!(
        "dspy_active_requests",
        "Number of active DSPy requests"
    ).unwrap();

    // Circuit breaker state
    pub static ref CIRCUIT_BREAKER_STATE: Gauge = register_gauge!(
        "dspy_circuit_breaker_open",
        "Circuit breaker state (1 = open, 0 = closed)"
    ).unwrap();

    // Token usage (for cost tracking)
    pub static ref TOKENS_USED: CounterVec = register_counter_vec!(
        "dspy_tokens_used_total",
        "Total tokens used",
        &["model", "type"]  // type: prompt, completion
    ).unwrap();
}

pub struct InstrumentedDSpyService {
    cache_service: DSpyCacheService,
    model_name: String,
}

impl InstrumentedDSpyService {
    pub async fn new(
        redis_url: &str,
        signature: &str,
        model_name: String,
    ) -> Result<Self> {
        let cache_service = DSpyCacheService::new(
            redis_url,
            signature,
            1000,
            3600,
        ).await?;

        Ok(Self {
            cache_service,
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
                    .with_label_values(&[&self.model_name, "success"])
                    .inc();

                // Record cache metrics
                if let Some(cache_level) = &prediction.metadata.cache_level {
                    CACHE_HITS.with_label_values(&[cache_level]).inc();

                    // Update timer label
                    drop(timer);
                    PREDICTION_DURATION
                        .with_label_values(&[&self.model_name, "true"])
                        .observe(0.001);  // Cached responses are fast
                } else {
                    CACHE_MISSES.with_label_values(&[]).inc();
                    drop(timer);  // Records actual duration
                }

                Ok(prediction.answer)
            }
            Err(e) => {
                // Record failure
                PREDICTIONS_TOTAL
                    .with_label_values(&[&self.model_name, "error"])
                    .inc();

                drop(timer);
                Err(e)
            }
        }
    }

    /// Export metrics for Prometheus scraping
    pub fn metrics(&self) -> Result<String> {
        let encoder = TextEncoder::new();
        let metric_families = prometheus::gather();
        let mut buffer = Vec::new();
        encoder.encode(&metric_families, &mut buffer)?;
        Ok(String::from_utf8(buffer)?)
    }
}
```

**HTTP Metrics Endpoint** (using Axum):

```rust
use axum::{routing::get, Router};
use std::net::SocketAddr;

async fn metrics_handler() -> String {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();
    encoder.encode(&metric_families, &mut buffer).unwrap();
    String::from_utf8(buffer).unwrap()
}

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/metrics", get(metrics_handler));

    let addr = SocketAddr::from(([0, 0, 0, 0], 9090));
    println!("Metrics server listening on {}", addr);

    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}
```

### 4. Structured Logging

**Why**: Debug production issues, trace request flows, audit predictions.

**Dependencies**:
```toml
[dependencies]
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["json", "env-filter"] }
tracing-opentelemetry = "0.21"
```

**Implementation**:

```rust
use tracing::{info, warn, error, debug, instrument};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

pub struct LoggingDSpyService {
    predictor: Py<PyAny>,
    service_name: String,
}

impl LoggingDSpyService {
    pub fn init_logging() {
        tracing_subscriber::registry()
            .with(tracing_subscriber::EnvFilter::new(
                std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into())
            ))
            .with(tracing_subscriber::fmt::layer().json())
            .init();
    }

    #[instrument(skip(self), fields(service = %self.service_name))]
    pub async fn predict(&self, input: String) -> Result<String> {
        info!(
            input_length = input.len(),
            "Starting DSPy prediction"
        );

        let start = std::time::Instant::now();

        let result = Python::with_gil(|py| -> Result<String> {
            debug!("Acquiring GIL for DSPy call");

            let py_result = self.predictor.as_ref(py)
                .call1(((input.as_str(),),))
                .context("DSPy call failed")?;

            let answer: String = py_result.getattr("answer")?.extract()?;

            debug!(answer_length = answer.len(), "Extracted answer");
            Ok(answer)
        });

        let duration = start.elapsed();

        match &result {
            Ok(answer) => {
                info!(
                    duration_ms = duration.as_millis(),
                    answer_length = answer.len(),
                    "Prediction completed successfully"
                );
            }
            Err(e) => {
                error!(
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

### 5. Cost Tracking

**Why**: LM APIs charge per token. Track costs to stay within budget.

**Implementation**:

```rust
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

#[derive(Debug, Clone)]
pub struct TokenUsage {
    pub prompt_tokens: u64,
    pub completion_tokens: u64,
    pub total_tokens: u64,
}

pub struct CostTrackingService {
    predictor: Py<PyAny>,

    // Atomic counters for thread-safe tracking
    total_prompt_tokens: Arc<AtomicU64>,
    total_completion_tokens: Arc<AtomicU64>,

    // Pricing (per 1M tokens)
    prompt_price_per_million: f64,
    completion_price_per_million: f64,
}

impl CostTrackingService {
    pub fn new(
        signature: &str,
        prompt_price_per_million: f64,
        completion_price_per_million: f64,
    ) -> Result<Self> {
        let predictor = Python::with_gil(|py| -> PyResult<Py<PyAny>> {
            let dspy = PyModule::import(py, "dspy")?;
            let predict = dspy.getattr("Predict")?;
            let pred = predict.call1(((signature,),))?;
            Ok(pred.into())
        })?;

        Ok(Self {
            predictor,
            total_prompt_tokens: Arc::new(AtomicU64::new(0)),
            total_completion_tokens: Arc::new(AtomicU64::new(0)),
            prompt_price_per_million,
            completion_price_per_million,
        })
    }

    pub fn predict_with_usage(&self, input: String) -> Result<(String, TokenUsage)> {
        Python::with_gil(|py| {
            // Make prediction
            let result = self.predictor.as_ref(py).call1(((input.as_str(),),))?;

            let answer: String = result.getattr("answer")?.extract()?;

            // Extract token usage from LM response
            // Note: This assumes DSPy exposes usage metadata
            let usage = self.extract_token_usage(py, &result)?;

            // Update counters
            self.total_prompt_tokens.fetch_add(usage.prompt_tokens, Ordering::Relaxed);
            self.total_completion_tokens.fetch_add(usage.completion_tokens, Ordering::Relaxed);

            // Update Prometheus metrics
            TOKENS_USED
                .with_label_values(&["default", "prompt"])
                .inc_by(usage.prompt_tokens as f64);
            TOKENS_USED
                .with_label_values(&["default", "completion"])
                .inc_by(usage.completion_tokens as f64);

            Ok((answer, usage))
        })
    }

    fn extract_token_usage(&self, py: Python, result: &PyAny) -> Result<TokenUsage> {
        // Try to extract usage from DSPy response
        // This depends on DSPy version and LM provider
        let lm = py.import("dspy")?.getattr("settings")?.getattr("lm")?;

        // Simplified: actual implementation depends on DSPy internals
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

    pub fn total_cost(&self) -> f64 {
        let prompt = self.total_prompt_tokens.load(Ordering::Relaxed) as f64;
        let completion = self.total_completion_tokens.load(Ordering::Relaxed) as f64;

        let prompt_cost = (prompt / 1_000_000.0) * self.prompt_price_per_million;
        let completion_cost = (completion / 1_000_000.0) * self.completion_price_per_million;

        prompt_cost + completion_cost
    }

    pub fn usage_report(&self) -> CostReport {
        let prompt_tokens = self.total_prompt_tokens.load(Ordering::Relaxed);
        let completion_tokens = self.total_completion_tokens.load(Ordering::Relaxed);

        CostReport {
            total_prompt_tokens: prompt_tokens,
            total_completion_tokens: completion_tokens,
            total_tokens: prompt_tokens + completion_tokens,
            total_cost_usd: self.total_cost(),
            prompt_price_per_million: self.prompt_price_per_million,
            completion_price_per_million: self.completion_price_per_million,
        }
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
}
```

**Usage**:

```rust
fn main() -> Result<()> {
    // OpenAI GPT-3.5 pricing (example)
    let service = CostTrackingService::new(
        "question -> answer",
        0.50,   // $0.50 per 1M prompt tokens
        1.50,   // $1.50 per 1M completion tokens
    )?;

    let (answer, usage) = service.predict_with_usage(
        "Explain quantum computing".to_string()
    )?;

    println!("Answer: {}", answer);
    println!("Tokens used: {}", usage.total_tokens);

    // Get total cost
    let report = service.usage_report();
    println!("Total cost: ${:.4}", report.total_cost_usd);

    Ok(())
}
```

### 6. A/B Testing Infrastructure

**Why**: Safely test new models or prompts without breaking production.

**Implementation**:

```rust
use rand::Rng;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct Variant {
    pub name: String,
    pub signature: String,
    pub model: String,
    pub weight: f64,  // Traffic percentage (0.0 - 1.0)
}

pub struct ABTestingService {
    variants: Vec<Variant>,
    predictors: HashMap<String, Py<PyAny>>,

    // Metrics per variant
    variant_calls: Arc<RwLock<HashMap<String, u64>>>,
    variant_successes: Arc<RwLock<HashMap<String, u64>>>,
}

impl ABTestingService {
    pub fn new(variants: Vec<Variant>) -> Result<Self> {
        // Validate weights sum to 1.0
        let total_weight: f64 = variants.iter().map(|v| v.weight).sum();
        if (total_weight - 1.0).abs() > 0.001 {
            return Err(anyhow::anyhow!("Variant weights must sum to 1.0"));
        }

        // Initialize predictors
        let mut predictors = HashMap::new();

        Python::with_gil(|py| -> Result<()> {
            for variant in &variants {
                let dspy = PyModule::import(py, "dspy")?;

                // Configure model for this variant
                let lm = dspy.getattr("OpenAI")?.call1(((variant.model.as_str(),),))?;
                dspy.getattr("settings")?.call_method1("configure", ((lm,),))?;

                // Create predictor
                let predict = dspy.getattr("Predict")?;
                let predictor = predict.call1(((variant.signature.as_str(),),))?;

                predictors.insert(variant.name.clone(), predictor.into());
            }
            Ok(())
        })?;

        Ok(Self {
            variants,
            predictors,
            variant_calls: Arc::new(RwLock::new(HashMap::new())),
            variant_successes: Arc::new(RwLock::new(HashMap::new())),
        })
    }

    /// Select variant based on weights
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

        &self.variants[0]  // Fallback
    }

    pub async fn predict(&self, input: String) -> Result<ABTestResult> {
        let variant = self.select_variant();

        // Track call
        {
            let mut calls = self.variant_calls.write().await;
            *calls.entry(variant.name.clone()).or_insert(0) += 1;
        }

        let predictor = self.predictors.get(&variant.name)
            .ok_or_else(|| anyhow::anyhow!("Variant predictor not found"))?;

        let result = Python::with_gil(|py| -> Result<String> {
            let prediction = predictor.as_ref(py).call1(((input.as_str(),),))?;
            let answer: String = prediction.getattr("answer")?.extract()?;
            Ok(answer)
        });

        match result {
            Ok(answer) => {
                // Track success
                {
                    let mut successes = self.variant_successes.write().await;
                    *successes.entry(variant.name.clone()).or_insert(0) += 1;
                }

                Ok(ABTestResult {
                    answer,
                    variant_name: variant.name.clone(),
                    variant_model: variant.model.clone(),
                })
            }
            Err(e) => Err(e),
        }
    }

    pub async fn variant_stats(&self) -> Vec<VariantStats> {
        let calls = self.variant_calls.read().await;
        let successes = self.variant_successes.read().await;

        self.variants.iter().map(|v| {
            let call_count = *calls.get(&v.name).unwrap_or(&0);
            let success_count = *successes.get(&v.name).unwrap_or(&0);

            VariantStats {
                name: v.name.clone(),
                model: v.model.clone(),
                weight: v.weight,
                calls: call_count,
                successes: success_count,
                success_rate: if call_count > 0 {
                    success_count as f64 / call_count as f64
                } else {
                    0.0
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
}

#[derive(Debug, Serialize)]
pub struct VariantStats {
    pub name: String,
    pub model: String,
    pub weight: f64,
    pub calls: u64,
    pub successes: u64,
    pub success_rate: f64,
}
```

**Usage**:

```rust
#[tokio::main]
async fn main() -> Result<()> {
    let variants = vec![
        Variant {
            name: "baseline".to_string(),
            signature: "question -> answer".to_string(),
            model: "gpt-3.5-turbo".to_string(),
            weight: 0.8,  // 80% traffic
        },
        Variant {
            name: "experiment".to_string(),
            signature: "question -> detailed_answer".to_string(),
            model: "gpt-4".to_string(),
            weight: 0.2,  // 20% traffic
        },
    ];

    let service = ABTestingService::new(variants)?;

    // Make predictions
    for i in 0..100 {
        let result = service.predict(format!("Question {}", i)).await?;
        println!("Variant: {} | Answer: {}", result.variant_name, result.answer);
    }

    // Get stats
    let stats = service.variant_stats().await;
    for stat in stats {
        println!("{}: {} calls, {:.2}% success",
            stat.name,
            stat.calls,
            stat.success_rate * 100.0
        );
    }

    Ok(())
}
```

### 7. Complete Production Service Architecture

**Combining all patterns**:

```rust
use axum::{
    extract::State,
    routing::{get, post},
    Json, Router,
};
use std::sync::Arc;
use tokio::sync::RwLock;

pub struct ProductionDSpyService {
    cache: DSpyCacheService,
    circuit_breaker: Arc<Mutex<CircuitBreaker>>,
    cost_tracker: Arc<CostTrackingService>,
    service_name: String,
}

impl ProductionDSpyService {
    pub async fn new(config: ServiceConfig) -> Result<Self> {
        LoggingDSpyService::init_logging();

        let cache = DSpyCacheService::new(
            &config.redis_url,
            &config.signature,
            config.cache_size,
            config.cache_ttl_secs,
        ).await?;

        let cb_config = CBConfig::new()
            .failure_threshold(config.circuit_breaker_threshold)
            .timeout(Duration::from_secs(config.timeout_secs));

        let circuit_breaker = Arc::new(Mutex::new(CircuitBreaker::new(cb_config)));

        let cost_tracker = Arc::new(CostTrackingService::new(
            &config.signature,
            config.prompt_price_per_million,
            config.completion_price_per_million,
        )?);

        Ok(Self {
            cache,
            circuit_breaker,
            cost_tracker,
            service_name: config.service_name,
        })
    }

    #[instrument(skip(self), fields(service = %self.service_name))]
    pub async fn predict(&mut self, input: String) -> Result<PredictionResponse> {
        ACTIVE_REQUESTS.inc();
        let start = std::time::Instant::now();

        let result = self.cache.predict(input).await;

        let duration = start.elapsed();
        ACTIVE_REQUESTS.dec();

        match result {
            Ok(prediction) => {
                PREDICTIONS_TOTAL
                    .with_label_values(&[&self.service_name, "success"])
                    .inc();

                PREDICTION_DURATION
                    .with_label_values(&[
                        &self.service_name,
                        if prediction.metadata.cached { "true" } else { "false" }
                    ])
                    .observe(duration.as_secs_f64());

                Ok(PredictionResponse {
                    answer: prediction.answer,
                    cached: prediction.metadata.cached,
                    cache_level: prediction.metadata.cache_level,
                    duration_ms: duration.as_millis() as u64,
                })
            }
            Err(e) => {
                PREDICTIONS_TOTAL
                    .with_label_values(&[&self.service_name, "error"])
                    .inc();

                error!(error = %e, "Prediction failed");
                Err(e)
            }
        }
    }
}

#[derive(Debug, Serialize)]
pub struct PredictionResponse {
    pub answer: String,
    pub cached: bool,
    pub cache_level: Option<String>,
    pub duration_ms: u64,
}

#[derive(Debug, Deserialize)]
pub struct ServiceConfig {
    pub service_name: String,
    pub redis_url: String,
    pub signature: String,
    pub cache_size: usize,
    pub cache_ttl_secs: usize,
    pub circuit_breaker_threshold: usize,
    pub timeout_secs: u64,
    pub prompt_price_per_million: f64,
    pub completion_price_per_million: f64,
}

// HTTP API
async fn predict_handler(
    State(service): State<Arc<RwLock<ProductionDSpyService>>>,
    Json(request): Json<PredictRequest>,
) -> Json<PredictionResponse> {
    let mut svc = service.write().await;
    match svc.predict(request.input).await {
        Ok(response) => Json(response),
        Err(e) => Json(PredictionResponse {
            answer: format!("Error: {}", e),
            cached: false,
            cache_level: None,
            duration_ms: 0,
        }),
    }
}

#[derive(Debug, Deserialize)]
struct PredictRequest {
    input: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    let config = ServiceConfig {
        service_name: "dspy-production".to_string(),
        redis_url: "redis://localhost:6379".to_string(),
        signature: "question -> answer".to_string(),
        cache_size: 10000,
        cache_ttl_secs: 3600,
        circuit_breaker_threshold: 5,
        timeout_secs: 30,
        prompt_price_per_million: 0.50,
        completion_price_per_million: 1.50,
    };

    let service = Arc::new(RwLock::new(
        ProductionDSpyService::new(config).await?
    ));

    let app = Router::new()
        .route("/predict", post(predict_handler))
        .route("/metrics", get(metrics_handler))
        .route("/health", get(|| async { "OK" }))
        .with_state(service);

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    info!("Production DSPy service listening on {}", addr);

    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await?;

    Ok(())
}
```

### 8. Deployment Checklist

**Pre-deployment**:
- [ ] All caches configured (memory + Redis)
- [ ] Circuit breakers tested and tuned
- [ ] Metrics endpoint exposed
- [ ] Structured logging enabled
- [ ] Cost tracking validated
- [ ] Health check endpoint working
- [ ] Environment variables documented
- [ ] Rate limiting configured
- [ ] Timeouts set appropriately

**Monitoring**:
- [ ] Prometheus scraping configured
- [ ] Grafana dashboards created
- [ ] Alerts for high error rates
- [ ] Alerts for circuit breaker trips
- [ ] Cost alerts configured
- [ ] Latency SLO defined and monitored

**Operations**:
- [ ] Runbook documented
- [ ] Rollback procedure tested
- [ ] Cache invalidation strategy
- [ ] Model version tracking
- [ ] Incident response plan

## Best Practices

### DO

✅ **Cache aggressively** with multi-level strategy
✅ **Monitor everything** - metrics, logs, traces
✅ **Set cost budgets** and alert on overages
✅ **Use circuit breakers** for all external LM calls
✅ **Test in shadow mode** before full rollout
✅ **Version your models** and track lineage
✅ **Log request IDs** for tracing
✅ **Implement graceful degradation**

### DON'T

❌ **Skip caching** - LM calls are expensive
❌ **Ignore cost tracking** - budgets matter
❌ **Deploy without circuit breakers** - APIs fail
❌ **Run A/B tests without stats** - meaningless data
❌ **Cache sensitive data** without encryption
❌ **Forget cache invalidation** on model updates
❌ **Expose raw errors** to users

## Common Pitfalls

### 1. Cache Stampede

**Problem**: Many requests hit LM simultaneously when cache expires.

**Solution**: Use cache warming and jittered TTLs:
```rust
// Add jitter to TTL
let ttl = base_ttl + rand::thread_rng().gen_range(0..300);  // ±5 min
```

### 2. Unbounded Cost Growth

**Problem**: No limits on API spending.

**Solution**: Implement cost gates:
```rust
if cost_tracker.total_cost() > DAILY_BUDGET {
    return Err(anyhow::anyhow!("Daily budget exceeded"));
}
```

### 3. Metric Cardinality Explosion

**Problem**: Too many label combinations in metrics.

**Solution**: Limit label values:
```rust
// ❌ Bad: unlimited user_id labels
PREDICTIONS.with_label_values(&[user_id, model]);

// ✅ Good: limited labels
PREDICTIONS.with_label_values(&["unknown", model]);
```

## Troubleshooting

### Issue: High Cache Miss Rate

**Symptoms**: Most requests hit LM API, costs high

**Debug**:
```rust
let stats = service.cache_stats().await;
println!("Cache hit rate: {:.2}%", stats.hit_rate() * 100.0);
```

**Solutions**:
- Increase cache size
- Extend TTL
- Normalize inputs (lowercase, trim)
- Pre-warm cache

### Issue: Circuit Breaker Stuck Open

**Symptoms**: All requests rejected, service unavailable

**Debug**:
```rust
println!("CB state: {}", service.circuit_state().await);
println!("Failure count: {}", cb.failure_count());
```

**Solutions**:
- Check LM API status
- Increase timeout threshold
- Adjust failure threshold
- Implement manual circuit reset

## Next Steps

**After mastering production deployment**:
1. **Distributed tracing** with OpenTelemetry
2. **Advanced caching** with write-through patterns
3. **Multi-region deployment** for low latency
4. **Model versioning** and blue/green deployments
5. **pyo3-dspy-optimization**: Compile and optimize models

## References

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Structured Logging](https://www.structlog.org/)
- [Redis Caching Patterns](https://redis.io/docs/manual/patterns/)
- [Cost Optimization for LLMs](https://platform.openai.com/docs/guides/production-best-practices)

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Maintainer**: DSPy-PyO3 Integration Team
