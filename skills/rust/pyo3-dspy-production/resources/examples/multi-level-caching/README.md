# Multi-Level Caching for DSPy Services

## Overview

Production-grade multi-level caching implementation for DSPy language model services. This example demonstrates a complete caching hierarchy to minimize expensive LM API calls while maintaining low latency.

**Architecture**: Memory (L1 LRU) → Redis (L2) → LM API

## Why Multi-Level Caching?

**Problem**: LM API calls are:
- **Expensive**: $0.50-$1.50 per 1M tokens
- **Slow**: 500ms-3s latency
- **Rate-limited**: 60-3500 RPM depending on tier

**Solution**: Cache aggressively at multiple levels:
1. **L1 Memory (LRU)**: <1ms latency, limited capacity
2. **L2 Redis**: 1-5ms latency, larger capacity, persistence
3. **L3 LM API**: Only for cache misses

## Features

### Implemented Patterns

✅ **Multi-level cache cascade** (Memory → Redis → API)
✅ **Fast cache key hashing** with blake3
✅ **Cache promotion** (Redis hits promoted to memory)
✅ **Metadata tracking** (cache level, timestamps)
✅ **Cache statistics** (hit rates, cost savings)
✅ **TTL management** for both layers
✅ **Cache invalidation** (clear on model updates)

### Performance Characteristics

| Cache Level | Latency | Capacity | Persistence | Cost |
|-------------|---------|----------|-------------|------|
| L1 Memory   | <1ms    | 1,000-10,000 entries | No | Free |
| L2 Redis    | 1-5ms   | 100,000+ entries | Optional | Low |
| L3 LM API   | 500ms-3s | Unlimited | N/A | High |

## Quick Start

### Prerequisites

1. **Python with DSPy**:
```bash
pip install dspy-ai openai
```

2. **Redis**:
```bash
# Using Docker Compose (included)
docker-compose up -d

# Or locally
redis-server
```

3. **OpenAI API Key**:
```bash
export OPENAI_API_KEY="sk-..."
```

### Run the Example

```bash
# Build and run
cargo run

# Expected output:
# - Cache performance demo
# - Sequential vs cached comparison
# - Cache statistics
# - Cost savings calculation
```

## Architecture

### Cache Flow

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  L1: Memory Cache (LRU)             │
│  - Capacity: 1,000 entries          │
│  - Latency: <1ms                    │
│  - Hit: Return immediately          │
│  - Miss: Check L2                   │
└──────┬──────────────────────────────┘
       │ Miss
       ▼
┌─────────────────────────────────────┐
│  L2: Redis Cache                    │
│  - Capacity: 100,000+ entries       │
│  - Latency: 1-5ms                   │
│  - TTL: 1 hour (configurable)       │
│  - Hit: Promote to L1, return       │
│  - Miss: Call L3                    │
└──────┬──────────────────────────────┘
       │ Miss
       ▼
┌─────────────────────────────────────┐
│  L3: LM API Call                    │
│  - Latency: 500ms-3s                │
│  - Cost: $0.50-$1.50 per 1M tokens  │
│  - Result: Store in L2 + L1         │
└─────────────────────────────────────┘
```

### Cache Key Generation

Uses **blake3** for fast, deterministic hashing:

```rust
fn cache_key(input: &str) -> String {
    let hash = blake3::hash(input.as_bytes());
    format!("dspy:prediction:{}", hash.to_hex())
}
```

**Benefits**:
- Fast: 1-2 GB/s hashing speed
- Deterministic: Same input → same key
- Collision-resistant: Cryptographic strength
- Compact: 64-character hex keys

### Cache Promotion Strategy

When L2 (Redis) cache hits:
1. Retrieve prediction from Redis
2. **Promote to L1 (memory)** for faster subsequent access
3. Mark metadata with `cache_level: "redis"`
4. Return to client

This ensures frequently-accessed predictions migrate to the fastest cache layer.

## Code Structure

### `src/lib.rs` (584 lines)

Core caching implementation:

```rust
pub struct DSpyCacheService {
    memory_cache: Arc<RwLock<LruCache<String, CachedPrediction>>>,
    redis: redis::aio::ConnectionManager,
    predictor: Py<PyAny>,
    memory_cache_size: usize,
    redis_ttl_secs: usize,
}

impl DSpyCacheService {
    // Initialize with Redis and DSPy predictor
    pub async fn new(...) -> Result<Self>

    // Generate cache key from input
    fn cache_key(&self, input: &str) -> String

    // Predict with multi-level caching
    pub async fn predict(&mut self, input: String) -> Result<CachedPrediction>

    // Check Redis for cached prediction
    async fn check_redis(&mut self, key: &str) -> Result<Option<CachedPrediction>>

    // Store prediction in Redis
    async fn store_in_redis(&mut self, key: &str, prediction: &CachedPrediction) -> Result<()>

    // Call DSPy LM (no cache)
    async fn call_lm(&self, input: &str) -> Result<CachedPrediction>

    // Clear all caches
    pub async fn clear_caches(&mut self) -> Result<()>

    // Get cache statistics
    pub async fn cache_stats(&self) -> CacheStats
}
```

**Data Structures**:

```rust
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
```

### `src/main.rs` (385 lines)

Demonstration scenarios:

1. **Cache Performance Demo**
   - First call: Cache miss → LM API
   - Second call: Cache hit → <1ms
   - Third call: Same input, memory cache

2. **Sequential vs Cached Comparison**
   - 10 unique questions (sequential)
   - Same 10 questions (cached)
   - Performance comparison

3. **Cache Warming**
   - Pre-populate cache with common queries
   - Demonstrate instant responses

4. **TTL Testing**
   - Verify cache expiration behavior

5. **Cost Savings Report**
   - Track cache hit rate
   - Calculate cost savings vs no cache

## Configuration

### Environment Variables

```bash
# Redis connection
REDIS_URL="redis://localhost:6379"

# DSPy model
OPENAI_API_KEY="sk-..."

# Cache settings
CACHE_MEMORY_SIZE=1000      # L1 capacity
CACHE_REDIS_TTL_SECS=3600   # L2 TTL (1 hour)
```

### Tuning Cache Sizes

**L1 (Memory) Size**:
- Small service: 100-1,000 entries
- Medium service: 1,000-10,000 entries
- Large service: 10,000-100,000 entries

**L2 (Redis) TTL**:
- Real-time data: 60-300 seconds
- Semi-static data: 1-6 hours
- Static data: 24 hours+

**Trade-offs**:
- Larger L1: More memory, faster hits
- Longer TTL: Stale data risk, higher hit rate
- Shorter TTL: Fresh data, more API calls

## Performance Metrics

### Expected Cache Hit Rates

| Scenario | L1 Hit Rate | L2 Hit Rate | Total Hit Rate |
|----------|-------------|-------------|----------------|
| High repetition | 80-95% | 5-15% | 85-99% |
| Medium repetition | 40-60% | 20-40% | 60-90% |
| Low repetition | 10-20% | 10-30% | 20-50% |

### Latency Comparison

```
No Cache:     500-3000ms per request
L2 Hit:       1-5ms (100-3000x faster)
L1 Hit:       <1ms (500-3000x faster)
```

### Cost Savings

**Example**: 10,000 requests/day, 90% cache hit rate

```
Without cache: 10,000 requests × $0.01/request = $100/day
With cache:    1,000 requests × $0.01/request = $10/day
Savings:       $90/day = $2,700/month
```

## Cache Invalidation

### When to Clear Caches

1. **Model updates**: New version deployed
2. **Prompt changes**: Signature modified
3. **Data changes**: Underlying data updated
4. **Quality issues**: Bad predictions cached

### Invalidation Methods

**Clear all caches**:
```rust
service.clear_caches().await?;
```

**Clear specific key**:
```rust
// Memory
memory_cache.write().await.pop(&key);

// Redis
redis.del(key).await?;
```

**Pattern-based clearing** (Redis):
```rust
let keys: Vec<String> = redis.keys("dspy:prediction:*").await?;
if !keys.is_empty() {
    redis.del(&keys).await?;
}
```

## Production Considerations

### DO

✅ **Monitor cache hit rates** - Target 85-95%
✅ **Set appropriate TTLs** - Balance freshness vs cost
✅ **Use connection pooling** - Reuse Redis connections
✅ **Hash cache keys** - Avoid key collisions
✅ **Track cost savings** - Justify infrastructure
✅ **Implement cache warming** - Pre-populate common queries
✅ **Add jitter to TTLs** - Prevent cache stampede

### DON'T

❌ **Cache sensitive data** without encryption
❌ **Use unlimited memory** - LRU prevents OOM
❌ **Ignore cache misses** - Monitor and investigate
❌ **Forget to invalidate** - Stale data hurts quality
❌ **Skip connection pooling** - Performance bottleneck
❌ **Use predictable keys** - Enables cache poisoning

## Troubleshooting

### High Cache Miss Rate

**Symptoms**: Most requests hit LM API, high costs

**Causes**:
- Cache too small (L1)
- TTL too short (L2)
- Input variations (whitespace, case)
- Cache stampede

**Solutions**:
```rust
// Increase L1 size
memory_cache_size: 10000  // from 1000

// Extend L2 TTL
redis_ttl_secs: 7200  // 2 hours from 1 hour

// Normalize inputs
let normalized = input.trim().to_lowercase();
```

### Redis Connection Failures

**Symptoms**: Errors like "Connection refused" or timeouts

**Causes**:
- Redis not running
- Network issues
- Connection pool exhausted

**Solutions**:
```bash
# Check Redis status
redis-cli ping  # Should return PONG

# Verify connectivity
redis-cli -h localhost -p 6379 INFO
```

### Memory Pressure

**Symptoms**: High memory usage, OOM errors

**Causes**:
- L1 cache too large
- Memory leaks
- Large prediction values

**Solutions**:
```rust
// Reduce L1 size
memory_cache_size: 100  // from 1000

// Monitor memory
let stats = service.cache_stats().await;
println!("Memory cache: {}/{}", stats.memory_cache_size, stats.memory_cache_capacity);
```

## Advanced Patterns

### Cache Stampede Prevention

When cache expires, many requests hit LM simultaneously. Add jitter:

```rust
use rand::Rng;

let jitter = rand::thread_rng().gen_range(0..300);  // 0-5 min
let ttl_with_jitter = redis_ttl_secs + jitter;
```

### Cache Warming

Pre-populate cache with common queries:

```rust
async fn warm_cache(service: &mut DSpyCacheService, queries: Vec<String>) -> Result<()> {
    for query in queries {
        service.predict(query).await?;
    }
    Ok(())
}
```

### Tiered TTLs

Different TTLs based on query type:

```rust
fn get_ttl(query: &str) -> usize {
    if query.contains("current") || query.contains("latest") {
        300  // 5 minutes for time-sensitive
    } else if query.contains("historical") {
        86400  // 24 hours for historical
    } else {
        3600  // 1 hour default
    }
}
```

## Related Resources

- **pyo3-dspy-fundamentals**: Basic DSPy integration
- **pyo3-dspy-async-streaming**: Async patterns
- **redis-caching-patterns**: Redis best practices
- **cache-performance-monitoring**: Metrics and observability

## License

MIT
