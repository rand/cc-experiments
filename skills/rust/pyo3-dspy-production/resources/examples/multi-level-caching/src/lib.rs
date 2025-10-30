//! Multi-Level Caching for DSPy Services
//!
//! Production-grade caching implementation with Memory (L1) → Redis (L2) → LM API cascade.
//!
//! # Architecture
//!
//! ```text
//! Request → Memory Cache (LRU) → Redis Cache → LM API
//!           <1ms latency        1-5ms         500ms-3s
//!           1K-10K entries      100K+         Unlimited
//! ```
//!
//! # Features
//!
//! - **Multi-level caching**: Memory → Redis → API cascade
//! - **Cache promotion**: Redis hits promoted to memory
//! - **Fast hashing**: blake3 for cache key generation
//! - **Metadata tracking**: Cache level, timestamps, model info
//! - **Statistics**: Hit rates, cost savings calculation
//! - **TTL management**: Configurable expiration for both layers
//! - **Cache invalidation**: Clear on model updates
//!
//! # Example
//!
//! ```rust,no_run
//! use multi_level_caching::DSpyCacheService;
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     let mut service = DSpyCacheService::new(
//!         "redis://localhost:6379",
//!         "question -> answer",
//!         1000,  // Memory cache: 1000 entries
//!         3600,  // Redis TTL: 1 hour
//!     ).await?;
//!
//!     // First call: Cache miss → LM API
//!     let result = service.predict("What is Rust?".to_string()).await?;
//!     println!("Answer: {} (cached: {})", result.answer, result.metadata.cached);
//!
//!     // Second call: Cache hit → <1ms
//!     let result = service.predict("What is Rust?".to_string()).await?;
//!     println!("Cache level: {:?}", result.metadata.cache_level);
//!
//!     Ok(())
//! }
//! ```

use anyhow::{Context, Result};
use lru::LruCache;
use pyo3::prelude::*;
use redis::AsyncCommands;
use serde::{Deserialize, Serialize};
use std::num::NonZeroUsize;
use std::sync::Arc;
use tokio::sync::RwLock;

/// A cached DSPy prediction with metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CachedPrediction {
    /// The prediction answer
    pub answer: String,

    /// Metadata about caching and timing
    pub metadata: PredictionMetadata,
}

/// Metadata for a cached prediction
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictionMetadata {
    /// Whether this prediction was served from cache
    pub cached: bool,

    /// Cache level that served this prediction ("memory" or "redis")
    pub cache_level: Option<String>,

    /// Unix timestamp when prediction was created
    pub timestamp: u64,

    /// Model name used for prediction
    pub model: String,
}

/// Statistics about cache performance
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheStats {
    /// Current number of entries in memory cache
    pub memory_cache_size: usize,

    /// Maximum capacity of memory cache
    pub memory_cache_capacity: usize,

    /// TTL for Redis cache entries (seconds)
    pub redis_ttl_secs: usize,

    /// Total predictions made
    pub total_predictions: u64,

    /// Number of memory cache hits
    pub memory_hits: u64,

    /// Number of Redis cache hits
    pub redis_hits: u64,

    /// Number of cache misses (LM API calls)
    pub cache_misses: u64,
}

impl CacheStats {
    /// Calculate overall cache hit rate (0.0 - 1.0)
    pub fn hit_rate(&self) -> f64 {
        let total_hits = self.memory_hits + self.redis_hits;
        if self.total_predictions == 0 {
            0.0
        } else {
            total_hits as f64 / self.total_predictions as f64
        }
    }

    /// Calculate cost savings assuming $0.01 per API call
    pub fn cost_savings(&self, cost_per_call: f64) -> f64 {
        let total_hits = self.memory_hits + self.redis_hits;
        total_hits as f64 * cost_per_call
    }

    /// Get percentage of hits per cache level
    pub fn level_breakdown(&self) -> (f64, f64, f64) {
        if self.total_predictions == 0 {
            return (0.0, 0.0, 0.0);
        }

        let total = self.total_predictions as f64;
        (
            (self.memory_hits as f64 / total) * 100.0,
            (self.redis_hits as f64 / total) * 100.0,
            (self.cache_misses as f64 / total) * 100.0,
        )
    }
}

/// Multi-level caching service for DSPy predictions
///
/// Implements a three-tier caching hierarchy:
/// 1. L1 (Memory): LRU cache for fast access to recent predictions
/// 2. L2 (Redis): Distributed cache for persistence and larger capacity
/// 3. L3 (LM API): Direct DSPy predictor calls for cache misses
///
/// # Cache Flow
///
/// ```text
/// predict(input)
///   ↓
/// Check L1 (Memory) → Hit? → Return (promote to top of LRU)
///   ↓ Miss
/// Check L2 (Redis) → Hit? → Store in L1 → Return
///   ↓ Miss
/// Call L3 (LM API) → Store in L2 → Store in L1 → Return
/// ```
pub struct DSpyCacheService {
    /// L1: In-memory LRU cache for fastest access
    memory_cache: Arc<RwLock<LruCache<String, CachedPrediction>>>,

    /// L2: Redis cache for persistence and distributed access
    redis: redis::aio::ConnectionManager,

    /// DSPy predictor instance (holds GIL reference)
    predictor: Py<PyAny>,

    /// Configuration: Memory cache capacity
    memory_cache_size: usize,

    /// Configuration: Redis TTL in seconds
    redis_ttl_secs: usize,

    /// Statistics tracking
    stats: Arc<RwLock<CacheStats>>,
}

impl DSpyCacheService {
    /// Create a new multi-level cache service
    ///
    /// # Arguments
    ///
    /// * `redis_url` - Redis connection string (e.g., "redis://localhost:6379")
    /// * `signature` - DSPy signature for the predictor (e.g., "question -> answer")
    /// * `memory_cache_size` - Maximum entries in L1 memory cache
    /// * `redis_ttl_secs` - TTL for L2 Redis cache entries
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// let service = DSpyCacheService::new(
    ///     "redis://localhost:6379",
    ///     "question -> answer",
    ///     1000,  // L1: 1000 entries
    ///     3600,  // L2: 1 hour TTL
    /// ).await?;
    /// ```
    pub async fn new(
        redis_url: &str,
        signature: &str,
        memory_cache_size: usize,
        redis_ttl_secs: usize,
    ) -> Result<Self> {
        // Initialize Redis connection with connection manager for pooling
        let client = redis::Client::open(redis_url)
            .context("Failed to create Redis client")?;
        let redis = client
            .get_connection_manager()
            .await
            .context("Failed to get Redis connection manager")?;

        // Initialize DSPy predictor
        let predictor = Python::with_gil(|py| -> PyResult<Py<PyAny>> {
            let dspy = PyModule::import(py, "dspy")
                .context("Failed to import dspy module. Is dspy-ai installed?")?;

            let predict = dspy.getattr("Predict")?;
            let pred = predict.call1((signature,))?;
            Ok(pred.into())
        })
        .context("Failed to initialize DSPy predictor")?;

        Ok(Self {
            memory_cache: Arc::new(RwLock::new(LruCache::new(
                NonZeroUsize::new(memory_cache_size)
                    .context("Memory cache size must be > 0")?,
            ))),
            redis,
            predictor,
            memory_cache_size,
            redis_ttl_secs,
            stats: Arc::new(RwLock::new(CacheStats {
                memory_cache_size: 0,
                memory_cache_capacity: memory_cache_size,
                redis_ttl_secs,
                total_predictions: 0,
                memory_hits: 0,
                redis_hits: 0,
                cache_misses: 0,
            })),
        })
    }

    /// Generate deterministic cache key from input
    ///
    /// Uses blake3 for fast, cryptographically-strong hashing:
    /// - Speed: 1-2 GB/s hashing throughput
    /// - Collision-resistant: 256-bit output
    /// - Deterministic: Same input → same key
    ///
    /// # Format
    ///
    /// ```text
    /// dspy:prediction:<blake3_hex>
    /// ```
    fn cache_key(&self, input: &str) -> String {
        let hash = blake3::hash(input.as_bytes());
        format!("dspy:prediction:{}", hash.to_hex())
    }

    /// Make a prediction with multi-level caching
    ///
    /// # Cache Flow
    ///
    /// 1. Check L1 (Memory): <1ms
    /// 2. Check L2 (Redis): 1-5ms, promote to L1 on hit
    /// 3. Call L3 (LM API): 500ms-3s, store in L2 + L1
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// let result = service.predict("What is Rust?".to_string()).await?;
    /// println!("Answer: {}", result.answer);
    /// println!("Cached: {}", result.metadata.cached);
    /// println!("Cache level: {:?}", result.metadata.cache_level);
    /// ```
    pub async fn predict(&mut self, input: String) -> Result<CachedPrediction> {
        let key = self.cache_key(&input);

        // Update total predictions count
        {
            let mut stats = self.stats.write().await;
            stats.total_predictions += 1;
        }

        // L1: Check memory cache
        {
            let cache = self.memory_cache.read().await;
            if let Some(cached) = cache.peek(&key) {
                let mut result = cached.clone();
                result.metadata.cache_level = Some("memory".to_string());
                result.metadata.cached = true;

                // Update stats
                {
                    let mut stats = self.stats.write().await;
                    stats.memory_hits += 1;
                }

                return Ok(result);
            }
        }

        // L2: Check Redis
        if let Some(mut cached) = self.check_redis(&key).await? {
            // Promote to memory cache
            {
                let mut cache = self.memory_cache.write().await;
                cache.put(key.clone(), cached.clone());
            }

            cached.metadata.cache_level = Some("redis".to_string());
            cached.metadata.cached = true;

            // Update stats
            {
                let mut stats = self.stats.write().await;
                stats.redis_hits += 1;
            }

            return Ok(cached);
        }

        // L3: Call LM API (cache miss)
        let prediction = self.call_lm(&input).await?;

        // Store in both caches
        self.store_in_redis(&key, &prediction).await?;
        {
            let mut cache = self.memory_cache.write().await;
            cache.put(key, prediction.clone());
        }

        // Update stats
        {
            let mut stats = self.stats.write().await;
            stats.cache_misses += 1;
        }

        Ok(prediction)
    }

    /// Check Redis for a cached prediction
    ///
    /// # Returns
    ///
    /// - `Ok(Some(prediction))` if key exists in Redis
    /// - `Ok(None)` if key not found
    /// - `Err(_)` on Redis connection or deserialization errors
    async fn check_redis(&mut self, key: &str) -> Result<Option<CachedPrediction>> {
        let value: Option<String> = self
            .redis
            .get(key)
            .await
            .context("Failed to get key from Redis")?;

        match value {
            Some(json) => {
                let cached: CachedPrediction = serde_json::from_str(&json)
                    .context("Failed to deserialize cached prediction from Redis")?;
                Ok(Some(cached))
            }
            None => Ok(None),
        }
    }

    /// Store a prediction in Redis with TTL
    ///
    /// # Arguments
    ///
    /// * `key` - Cache key
    /// * `prediction` - Prediction to store
    ///
    /// # TTL
    ///
    /// Uses `redis_ttl_secs` configured at service creation.
    async fn store_in_redis(&mut self, key: &str, prediction: &CachedPrediction) -> Result<()> {
        let json = serde_json::to_string(prediction)
            .context("Failed to serialize prediction for Redis")?;

        self.redis
            .set_ex(key, json, self.redis_ttl_secs)
            .await
            .context("Failed to store prediction in Redis")?;

        Ok(())
    }

    /// Call DSPy language model directly (no caching)
    ///
    /// # GIL Handling
    ///
    /// Acquires Python GIL for the duration of the DSPy call.
    /// This is a blocking operation from Rust's perspective.
    ///
    /// # Returns
    ///
    /// Fresh prediction with `cached: false` metadata.
    async fn call_lm(&self, input: &str) -> Result<CachedPrediction> {
        // Acquire GIL and call DSPy predictor
        let answer = Python::with_gil(|py| -> PyResult<String> {
            let result = self
                .predictor
                .as_ref(py)
                .call1((input,))
                .context("DSPy predictor call failed")?;

            result
                .getattr("answer")
                .and_then(|a| a.extract::<String>())
                .context("Failed to extract answer from DSPy result")
        })
        .context("Python GIL acquisition failed")?;

        Ok(CachedPrediction {
            answer,
            metadata: PredictionMetadata {
                cached: false,
                cache_level: None,
                timestamp: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .context("System time error")?
                    .as_secs(),
                model: "default".to_string(),
            },
        })
    }

    /// Clear all caches (memory + Redis)
    ///
    /// Useful when:
    /// - Model updated (new version deployed)
    /// - Prompt changed (signature modified)
    /// - Bad predictions detected
    /// - Data changed (underlying knowledge updated)
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// // After deploying new model
    /// service.clear_caches().await?;
    /// println!("All caches cleared");
    /// ```
    pub async fn clear_caches(&mut self) -> Result<()> {
        // Clear L1 (memory)
        {
            let mut cache = self.memory_cache.write().await;
            cache.clear();
        }

        // Clear L2 (Redis) using pattern matching
        let pattern = "dspy:prediction:*";
        let keys: Vec<String> = self
            .redis
            .keys(pattern)
            .await
            .context("Failed to list Redis keys")?;

        if !keys.is_empty() {
            self.redis
                .del(&keys)
                .await
                .context("Failed to delete Redis keys")?;
        }

        Ok(())
    }

    /// Get current cache statistics
    ///
    /// # Returns
    ///
    /// Statistics including:
    /// - Cache sizes and capacities
    /// - Hit/miss counts
    /// - Hit rate calculation
    /// - Cost savings estimation
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// let stats = service.cache_stats().await;
    /// println!("Hit rate: {:.2}%", stats.hit_rate() * 100.0);
    /// println!("Cost savings: ${:.2}", stats.cost_savings(0.01));
    /// ```
    pub async fn cache_stats(&self) -> CacheStats {
        let memory_size = self.memory_cache.read().await.len();

        let mut stats = self.stats.read().await.clone();
        stats.memory_cache_size = memory_size;

        stats
    }

    /// Get detailed cache statistics as formatted string
    ///
    /// # Example Output
    ///
    /// ```text
    /// === Cache Statistics ===
    /// Memory Cache: 42/1000 entries (4.2%)
    /// Redis TTL: 3600 seconds (1.0 hours)
    ///
    /// Performance:
    ///   Total Predictions: 100
    ///   Memory Hits: 42 (42.0%)
    ///   Redis Hits: 38 (38.0%)
    ///   Cache Misses: 20 (20.0%)
    ///   Overall Hit Rate: 80.0%
    ///
    /// Cost Savings (@ $0.01/call):
    ///   Total Savings: $0.80
    ///   Avoided API Calls: 80
    /// ```
    pub async fn detailed_stats_report(&self) -> String {
        let stats = self.cache_stats().await;
        let (memory_pct, redis_pct, miss_pct) = stats.level_breakdown();

        format!(
            r#"=== Cache Statistics ===
Memory Cache: {}/{} entries ({:.1}%)
Redis TTL: {} seconds ({:.1} hours)

Performance:
  Total Predictions: {}
  Memory Hits: {} ({:.1}%)
  Redis Hits: {} ({:.1}%)
  Cache Misses: {} ({:.1}%)
  Overall Hit Rate: {:.1}%

Cost Savings (@ $0.01/call):
  Total Savings: ${:.2}
  Avoided API Calls: {}
"#,
            stats.memory_cache_size,
            stats.memory_cache_capacity,
            (stats.memory_cache_size as f64 / stats.memory_cache_capacity as f64) * 100.0,
            stats.redis_ttl_secs,
            stats.redis_ttl_secs as f64 / 3600.0,
            stats.total_predictions,
            stats.memory_hits,
            memory_pct,
            stats.redis_hits,
            redis_pct,
            stats.cache_misses,
            miss_pct,
            stats.hit_rate() * 100.0,
            stats.cost_savings(0.01),
            stats.memory_hits + stats.redis_hits,
        )
    }

    /// Warm the cache with a list of common queries
    ///
    /// Pre-populates cache with frequently-used queries to ensure
    /// instant responses for common use cases.
    ///
    /// # Arguments
    ///
    /// * `queries` - List of queries to pre-cache
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// let common_queries = vec![
    ///     "What is Rust?".to_string(),
    ///     "How does async work?".to_string(),
    ///     "Explain ownership".to_string(),
    /// ];
    ///
    /// service.warm_cache(common_queries).await?;
    /// println!("Cache warmed with {} queries", 3);
    /// ```
    pub async fn warm_cache(&mut self, queries: Vec<String>) -> Result<usize> {
        let mut count = 0;

        for query in queries {
            match self.predict(query.clone()).await {
                Ok(_) => count += 1,
                Err(e) => {
                    eprintln!("Failed to warm cache for query '{}': {}", query, e);
                }
            }
        }

        Ok(count)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_key_deterministic() {
        let service = DSpyCacheService {
            memory_cache: Arc::new(RwLock::new(LruCache::new(
                NonZeroUsize::new(10).unwrap(),
            ))),
            redis: todo!(),
            predictor: todo!(),
            memory_cache_size: 10,
            redis_ttl_secs: 3600,
            stats: Arc::new(RwLock::new(CacheStats {
                memory_cache_size: 0,
                memory_cache_capacity: 10,
                redis_ttl_secs: 3600,
                total_predictions: 0,
                memory_hits: 0,
                redis_hits: 0,
                cache_misses: 0,
            })),
        };

        let key1 = service.cache_key("test input");
        let key2 = service.cache_key("test input");
        let key3 = service.cache_key("different input");

        assert_eq!(key1, key2, "Same input should produce same key");
        assert_ne!(key1, key3, "Different inputs should produce different keys");
        assert!(key1.starts_with("dspy:prediction:"), "Key should have correct prefix");
    }

    #[test]
    fn test_cache_stats_calculations() {
        let stats = CacheStats {
            memory_cache_size: 10,
            memory_cache_capacity: 100,
            redis_ttl_secs: 3600,
            total_predictions: 100,
            memory_hits: 60,
            redis_hits: 30,
            cache_misses: 10,
        };

        assert_eq!(stats.hit_rate(), 0.9, "Hit rate should be 90%");
        assert_eq!(stats.cost_savings(0.01), 0.90, "Cost savings should be $0.90");

        let (mem_pct, redis_pct, miss_pct) = stats.level_breakdown();
        assert_eq!(mem_pct, 60.0, "Memory hits should be 60%");
        assert_eq!(redis_pct, 30.0, "Redis hits should be 30%");
        assert_eq!(miss_pct, 10.0, "Misses should be 10%");
    }
}
