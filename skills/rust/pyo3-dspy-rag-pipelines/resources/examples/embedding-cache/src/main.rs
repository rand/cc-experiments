use anyhow::{Context, Result};
use lru::LruCache;
use redis::AsyncCommands;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::num::NonZeroUsize;
use std::sync::Arc;
use tokio::sync::Mutex;

/// Embedding vector type
type Embedding = Vec<f32>;

/// Cache statistics for monitoring and cost calculation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub total_requests: u64,
    pub estimated_cost_saved: f64,
    pub estimated_total_cost: f64,
}

impl CacheStats {
    pub fn new() -> Self {
        Self {
            hits: 0,
            misses: 0,
            total_requests: 0,
            estimated_cost_saved: 0.0,
            estimated_total_cost: 0.0,
        }
    }

    pub fn hit_rate(&self) -> f64 {
        if self.total_requests == 0 {
            0.0
        } else {
            self.hits as f64 / self.total_requests as f64
        }
    }

    pub fn cost_reduction_percent(&self) -> f64 {
        if self.estimated_total_cost == 0.0 {
            0.0
        } else {
            (self.estimated_cost_saved / self.estimated_total_cost) * 100.0
        }
    }
}

/// Two-tier embedding cache with LRU memory and Redis persistence
pub struct EmbeddingCache {
    /// In-memory LRU cache for fast access
    memory_cache: Arc<Mutex<LruCache<String, Embedding>>>,
    /// Redis connection for persistent storage
    redis_client: redis::Client,
    /// Statistics tracking
    stats: Arc<Mutex<CacheStats>>,
    /// Cost per embedding (e.g., OpenAI ada-002: $0.0001 per 1K tokens)
    cost_per_embedding: f64,
}

impl EmbeddingCache {
    /// Create a new embedding cache
    pub async fn new(redis_url: &str, memory_capacity: usize, cost_per_embedding: f64) -> Result<Self> {
        let redis_client = redis::Client::open(redis_url)
            .context("Failed to create Redis client")?;

        // Test Redis connection
        let mut conn = redis_client
            .get_multiplexed_async_connection()
            .await
            .context("Failed to connect to Redis")?;

        let _: String = redis::cmd("PING")
            .query_async(&mut conn)
            .await
            .context("Redis ping failed")?;

        let capacity = NonZeroUsize::new(memory_capacity)
            .context("Memory capacity must be non-zero")?;

        Ok(Self {
            memory_cache: Arc::new(Mutex::new(LruCache::new(capacity))),
            redis_client,
            stats: Arc::new(Mutex::new(CacheStats::new())),
            cost_per_embedding,
        })
    }

    /// Generate cache key from text using SHA-256
    fn generate_key(text: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(text.as_bytes());
        format!("emb:{}", hex::encode(hasher.finalize()))
    }

    /// Get embedding from cache (memory first, then Redis)
    pub async fn get(&self, text: &str) -> Result<Option<Embedding>> {
        let key = Self::generate_key(text);

        // Check memory cache first
        {
            let mut cache = self.memory_cache.lock().await;
            if let Some(embedding) = cache.get(&key) {
                let mut stats = self.stats.lock().await;
                stats.hits += 1;
                stats.total_requests += 1;
                stats.estimated_cost_saved += self.cost_per_embedding;
                return Ok(Some(embedding.clone()));
            }
        }

        // Check Redis
        let mut conn = self.redis_client.get_multiplexed_async_connection().await?;
        let redis_result: Option<String> = conn.get(&key).await?;

        if let Some(json_data) = redis_result {
            // Deserialize from Redis
            let embedding: Embedding = serde_json::from_str(&json_data)
                .context("Failed to deserialize embedding from Redis")?;

            // Promote to memory cache
            {
                let mut cache = self.memory_cache.lock().await;
                cache.put(key.clone(), embedding.clone());
            }

            let mut stats = self.stats.lock().await;
            stats.hits += 1;
            stats.total_requests += 1;
            stats.estimated_cost_saved += self.cost_per_embedding;

            Ok(Some(embedding))
        } else {
            let mut stats = self.stats.lock().await;
            stats.misses += 1;
            stats.total_requests += 1;
            stats.estimated_total_cost += self.cost_per_embedding;

            Ok(None)
        }
    }

    /// Store embedding in both memory and Redis
    pub async fn put(&self, text: &str, embedding: Embedding) -> Result<()> {
        let key = Self::generate_key(text);
        let json_data = serde_json::to_string(&embedding)
            .context("Failed to serialize embedding")?;

        // Store in memory cache
        {
            let mut cache = self.memory_cache.lock().await;
            cache.put(key.clone(), embedding);
        }

        // Store in Redis with 30-day TTL
        let mut conn = self.redis_client.get_multiplexed_async_connection().await?;
        let ttl_seconds = 60 * 60 * 24 * 30; // 30 days
        let _: () = conn.set_ex(&key, json_data, ttl_seconds).await?;

        Ok(())
    }

    /// Get or compute embeddings for a batch of texts
    pub async fn get_or_compute_batch<F>(
        &self,
        texts: &[String],
        compute_fn: F,
    ) -> Result<Vec<Embedding>>
    where
        F: Fn(&[String]) -> Result<Vec<Embedding>>,
    {
        let mut results = Vec::with_capacity(texts.len());
        let mut cache_misses = Vec::new();
        let mut miss_indices = Vec::new();

        // Check cache for each text
        for (idx, text) in texts.iter().enumerate() {
            match self.get(text).await? {
                Some(embedding) => {
                    results.push(Some(embedding));
                }
                None => {
                    results.push(None);
                    cache_misses.push(text.clone());
                    miss_indices.push(idx);
                }
            }
        }

        // Compute embeddings for cache misses
        if !cache_misses.is_empty() {
            let computed = compute_fn(&cache_misses)?;

            // Store computed embeddings in cache
            for (text, embedding) in cache_misses.iter().zip(computed.iter()) {
                self.put(text, embedding.clone()).await?;
            }

            // Fill in results
            for (miss_idx, embedding) in miss_indices.iter().zip(computed.into_iter()) {
                results[*miss_idx] = Some(embedding);
            }
        }

        // Unwrap all results (guaranteed to be Some at this point)
        Ok(results.into_iter().map(|e| e.unwrap()).collect())
    }

    /// Warm the cache with pre-computed embeddings
    pub async fn warm(&self, texts_and_embeddings: Vec<(String, Embedding)>) -> Result<()> {
        for (text, embedding) in texts_and_embeddings {
            self.put(&text, embedding).await?;
        }
        Ok(())
    }

    /// Get current cache statistics
    pub async fn stats(&self) -> CacheStats {
        self.stats.lock().await.clone()
    }

    /// Reset cache statistics
    pub async fn reset_stats(&self) {
        let mut stats = self.stats.lock().await;
        *stats = CacheStats::new();
    }

    /// Clear all cached embeddings
    pub async fn clear(&self) -> Result<()> {
        // Clear memory cache
        {
            let mut cache = self.memory_cache.lock().await;
            cache.clear();
        }

        // Clear Redis (delete all keys matching pattern)
        let mut conn = self.redis_client.get_multiplexed_async_connection().await?;
        let keys: Vec<String> = redis::cmd("KEYS")
            .arg("emb:*")
            .query_async(&mut conn)
            .await?;

        if !keys.is_empty() {
            let _: () = redis::cmd("DEL")
                .arg(&keys)
                .query_async(&mut conn)
                .await?;
        }

        Ok(())
    }
}

/// Mock embedding function for demonstration
fn mock_embedding_api(texts: &[String]) -> Result<Vec<Embedding>> {
    // Simulate API latency
    std::thread::sleep(std::time::Duration::from_millis(100));

    // Generate deterministic "embeddings" based on text hash
    let embeddings: Vec<Embedding> = texts
        .iter()
        .map(|text| {
            let mut hasher = Sha256::new();
            hasher.update(text.as_bytes());
            let hash = hasher.finalize();

            // Convert hash to 384-dimensional embedding (like OpenAI ada-002)
            let mut embedding = Vec::with_capacity(384);
            for chunk in hash.chunks(4) {
                let mut bytes = [0u8; 4];
                bytes[..chunk.len()].copy_from_slice(chunk);
                let val = u32::from_le_bytes(bytes) as f32 / u32::MAX as f32;
                embedding.push(val);
            }

            // Pad to 384 dimensions
            while embedding.len() < 384 {
                embedding.push(0.0);
            }
            embedding
        })
        .collect();

    Ok(embeddings)
}

#[tokio::main]
async fn main() -> Result<()> {
    println!("Embedding Cache Demo\n");

    // Initialize cache (1000 embeddings in memory, $0.0001 per embedding)
    let cache = EmbeddingCache::new("redis://127.0.0.1:6379", 1000, 0.0001)
        .await
        .context("Failed to initialize cache")?;

    println!("✓ Connected to Redis");
    println!("✓ Initialized LRU cache (capacity: 1000)\n");

    // Clear cache for fresh demo
    cache.clear().await?;
    cache.reset_stats().await;

    // Demo 1: Cache warming
    println!("=== Demo 1: Cache Warming ===");
    let warmup_data = vec![
        ("The quick brown fox".to_string(), mock_embedding_api(&["The quick brown fox".to_string()])?[0].clone()),
        ("jumps over the lazy dog".to_string(), mock_embedding_api(&["jumps over the lazy dog".to_string()])?[0].clone()),
    ];
    cache.warm(warmup_data).await?;
    println!("✓ Warmed cache with 2 embeddings\n");

    // Demo 2: Single embedding with cache hit
    println!("=== Demo 2: Single Embedding (Cache Hit) ===");
    let text = "The quick brown fox";
    let start = std::time::Instant::now();
    let embedding = cache.get(text).await?;
    let elapsed = start.elapsed();
    println!("Text: '{}'", text);
    println!("Cache: HIT");
    println!("Latency: {:?}", elapsed);
    println!("Embedding dims: {}\n", embedding.unwrap().len());

    // Demo 3: Single embedding with cache miss
    println!("=== Demo 3: Single Embedding (Cache Miss) ===");
    let text = "Machine learning models";
    let start = std::time::Instant::now();
    let result = cache.get(text).await?;
    println!("Text: '{}'", text);
    println!("Cache: MISS");

    if result.is_none() {
        let embedding = mock_embedding_api(&[text.to_string()])?[0].clone();
        cache.put(text, embedding).await?;
        let elapsed = start.elapsed();
        println!("Latency: {:?} (API call)", elapsed);
        println!("✓ Computed and cached\n");
    }

    // Demo 4: Batch processing with mixed hits/misses
    println!("=== Demo 4: Batch Processing ===");
    let batch_texts = vec![
        "The quick brown fox".to_string(), // HIT (from warmup)
        "Machine learning models".to_string(), // HIT (from demo 3)
        "Deep neural networks".to_string(), // MISS
        "Natural language processing".to_string(), // MISS
        "jumps over the lazy dog".to_string(), // HIT (from warmup)
    ];

    let start = std::time::Instant::now();
    let embeddings = cache.get_or_compute_batch(&batch_texts, mock_embedding_api).await?;
    let elapsed = start.elapsed();

    println!("Batch size: {}", batch_texts.len());
    println!("Latency: {:?}", elapsed);
    println!("Embeddings returned: {}\n", embeddings.len());

    // Demo 5: Cache statistics and cost savings
    println!("=== Demo 5: Cache Statistics ===");
    let stats = cache.stats().await;
    println!("Total requests: {}", stats.total_requests);
    println!("Cache hits: {}", stats.hits);
    println!("Cache misses: {}", stats.misses);
    println!("Hit rate: {:.2}%", stats.hit_rate() * 100.0);
    println!("Estimated cost saved: ${:.6}", stats.estimated_cost_saved);
    println!("Estimated total cost (without cache): ${:.6}", stats.estimated_total_cost);
    println!("Cost reduction: {:.2}%\n", stats.cost_reduction_percent());

    // Demo 6: Large batch simulation
    println!("=== Demo 6: Large Batch Simulation ===");
    let mut large_batch = Vec::new();
    for i in 0..100 {
        large_batch.push(format!("Document chunk {}", i));
    }

    let start = std::time::Instant::now();
    let _ = cache.get_or_compute_batch(&large_batch, mock_embedding_api).await?;
    let elapsed = start.elapsed();
    println!("Batch size: 100");
    println!("First pass latency: {:?}", elapsed);

    // Second pass - all cache hits
    let start = std::time::Instant::now();
    let _ = cache.get_or_compute_batch(&large_batch, mock_embedding_api).await?;
    let elapsed = start.elapsed();
    println!("Second pass latency: {:?} (all cache hits)", elapsed);

    let final_stats = cache.stats().await;
    println!("\nFinal Statistics:");
    println!("Total requests: {}", final_stats.total_requests);
    println!("Hit rate: {:.2}%", final_stats.hit_rate() * 100.0);
    println!("Cost reduction: {:.2}%", final_stats.cost_reduction_percent());
    println!("Total saved: ${:.6}", final_stats.estimated_cost_saved);

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_cache_key_generation() {
        let key1 = EmbeddingCache::generate_key("test");
        let key2 = EmbeddingCache::generate_key("test");
        let key3 = EmbeddingCache::generate_key("different");

        assert_eq!(key1, key2);
        assert_ne!(key1, key3);
        assert!(key1.starts_with("emb:"));
    }

    #[tokio::test]
    async fn test_cache_stats() {
        let mut stats = CacheStats::new();
        assert_eq!(stats.hit_rate(), 0.0);

        stats.hits = 7;
        stats.misses = 3;
        stats.total_requests = 10;
        assert_eq!(stats.hit_rate(), 0.7);
    }
}
