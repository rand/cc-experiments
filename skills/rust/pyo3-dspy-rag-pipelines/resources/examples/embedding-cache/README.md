# Embedding Cache Example

Production-ready two-tier embedding cache with LRU memory and Redis persistence for cost reduction in RAG pipelines.

## Overview

This example demonstrates a robust caching strategy for embedding operations that:

- **Reduces API costs** by caching expensive embedding computations
- **Improves latency** with two-tier caching (memory + Redis)
- **Tracks metrics** including hit rates and cost savings
- **Handles batches** efficiently with mixed cache hits/misses
- **Supports warming** for pre-computed embeddings

## Architecture

```
┌─────────────────────────────────────────────┐
│          Embedding Cache                    │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐      ┌─────────────────┐ │
│  │  LRU Cache   │      │     Redis       │ │
│  │  (1000 max)  │◄────►│   (Persistent)  │ │
│  │   ~10ms      │      │     ~50ms       │ │
│  └──────────────┘      └─────────────────┘ │
│         ▲                                   │
│         │ miss                              │
│         ▼                                   │
│  ┌──────────────────────┐                  │
│  │  Embedding API       │                  │
│  │  (OpenAI, etc)       │                  │
│  │  ~200-500ms          │                  │
│  └──────────────────────┘                  │
└─────────────────────────────────────────────┘
```

## Features

### 1. Two-Tier Caching

**Memory Cache (LRU)**:
- Fast access (~10μs)
- Limited capacity (configurable, default 1000)
- Automatic eviction of least-recently-used items

**Redis Cache**:
- Persistent across restarts
- Larger capacity (limited by Redis memory)
- 30-day TTL to prevent unbounded growth
- Shared across multiple instances

### 2. Cost Tracking

Tracks and reports:
- Total API requests (cache hits + misses)
- Cache hit rate percentage
- Estimated cost saved by caching
- Cost reduction percentage

### 3. Batch Operations

Efficiently handles batches with mixed cache hits/misses:
```rust
let texts = vec!["doc1", "doc2", "doc3"];
let embeddings = cache.get_or_compute_batch(&texts, api_fn).await?;
// Only computes embeddings for cache misses
```

### 4. Cache Warming

Pre-populate cache with known embeddings:
```rust
let warmup_data = vec![
    ("common query 1".to_string(), embedding1),
    ("common query 2".to_string(), embedding2),
];
cache.warm(warmup_data).await?;
```

## Usage

### Start Redis

```bash
docker-compose up -d
```

Verify Redis is running:
```bash
docker-compose ps
docker exec -it embedding-cache-redis redis-cli ping
# Expected: PONG
```

### Run the Demo

```bash
cargo run
```

### Expected Output

```
Embedding Cache Demo

✓ Connected to Redis
✓ Initialized LRU cache (capacity: 1000)

=== Demo 1: Cache Warming ===
✓ Warmed cache with 2 embeddings

=== Demo 2: Single Embedding (Cache Hit) ===
Text: 'The quick brown fox'
Cache: HIT
Latency: 150μs
Embedding dims: 384

=== Demo 3: Single Embedding (Cache Miss) ===
Text: 'Machine learning models'
Cache: MISS
Latency: 102ms (API call)
✓ Computed and cached

=== Demo 4: Batch Processing ===
Batch size: 5
Latency: 105ms
Embeddings returned: 5

=== Demo 5: Cache Statistics ===
Total requests: 7
Cache hits: 4
Cache misses: 3
Hit rate: 57.14%
Estimated cost saved: $0.000400
Estimated total cost (without cache): $0.000700
Cost reduction: 57.14%

=== Demo 6: Large Batch Simulation ===
Batch size: 100
First pass latency: 10.2s
Second pass latency: 8ms (all cache hits)

Final Statistics:
Total requests: 207
Hit rate: 97.10%
Cost reduction: 97.10%
Total saved: $0.020100
```

## Implementation Details

### Cache Key Generation

SHA-256 hash of input text ensures:
- Deterministic keys for same input
- Collision resistance
- Compact key representation

```rust
fn generate_key(text: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(text.as_bytes());
    format!("emb:{}", hex::encode(hasher.finalize()))
}
```

### Cache Lookup Flow

```
1. Check memory cache
   ├─ HIT → Return embedding + update stats
   └─ MISS → Continue to step 2

2. Check Redis cache
   ├─ HIT → Promote to memory + return + update stats
   └─ MISS → Continue to step 3

3. Compute via API
   └─ Store in both memory and Redis + return + update stats
```

### Batch Processing Strategy

```rust
pub async fn get_or_compute_batch<F>(
    &self,
    texts: &[String],
    compute_fn: F,
) -> Result<Vec<Embedding>>
where
    F: Fn(&[String]) -> Result<Vec<Embedding>>
{
    // 1. Check cache for all texts
    // 2. Identify cache misses
    // 3. Batch compute only misses
    // 4. Store computed embeddings
    // 5. Return complete results
}
```

### Cost Calculation

```rust
// Per-request cost tracking
stats.hits += 1;  // Saved API call
stats.estimated_cost_saved += cost_per_embedding;

stats.misses += 1;  // Required API call
stats.estimated_total_cost += cost_per_embedding;

// Hit rate = hits / (hits + misses)
// Cost reduction = (saved / total) * 100%
```

## Production Considerations

### 1. Memory Cache Size

Choose based on:
- Available RAM
- Embedding dimension size
- Expected working set size

Example sizing:
```
384-dim float32 = 384 * 4 bytes = 1.5KB per embedding
1000 embeddings ≈ 1.5MB memory
10000 embeddings ≈ 15MB memory
```

### 2. Redis Configuration

**Memory Policy**: `allkeys-lru`
- Automatically evicts least-recently-used keys when memory limit reached
- Prevents Redis from running out of memory

**Persistence**: `appendonly yes`
- Durability for cache across restarts
- Slower than RDB but safer for cache data

**Max Memory**: Configure based on available RAM and cache size needs

### 3. TTL Strategy

Current: 30 days
- Balances freshness with cost savings
- Prevents unbounded growth
- Adjust based on:
  - Data update frequency
  - Available storage
  - Compliance requirements

### 4. Error Handling

Cache failures should not break the application:

```rust
match cache.get(text).await {
    Ok(Some(embedding)) => embedding,
    Ok(None) | Err(_) => {
        // Fallback to direct API call
        compute_embedding_via_api(text).await?
    }
}
```

### 5. Monitoring

Track in production:
- Hit rate (target: >80% for stable workloads)
- Cache size (memory + Redis)
- Eviction rate
- Cost savings vs. baseline
- P50/P95/P99 latency

### 6. Cache Warming Strategies

**Static Warming**: Pre-compute common queries
```rust
// On startup
cache.warm(load_common_embeddings()).await?;
```

**Progressive Warming**: Background cache population
```rust
// Periodic job
for doc in get_all_documents() {
    if cache.get(&doc.text).await?.is_none() {
        let emb = compute_embedding(&doc.text).await?;
        cache.put(&doc.text, emb).await?;
    }
}
```

**Adaptive Warming**: Based on query logs
```rust
// Analyze query patterns
let top_queries = analyze_query_logs().await?;
for query in top_queries {
    warm_cache_for_query(&query).await?;
}
```

## Cost Savings Examples

### Scenario 1: RAG System with 1M queries/month

**Without Cache**:
- 1M API calls × $0.0001 = $100/month

**With 90% Hit Rate**:
- 100K API calls × $0.0001 = $10/month
- Savings: $90/month (90%)

**With 95% Hit Rate**:
- 50K API calls × $0.0001 = $5/month
- Savings: $95/month (95%)

### Scenario 2: Document Processing Pipeline

Processing 10,000 documents with 100 chunks each:

**Without Cache**:
- 1M embeddings × $0.0001 = $100

**With Cache** (re-processing common patterns):
- First run: $100 (build cache)
- Subsequent runs: $10-20 (80-90% cache hits)
- ROI: Break-even after 2nd run

## Testing

Run tests:
```bash
cargo test
```

Run with Redis integration test:
```bash
docker-compose up -d
cargo test -- --test-threads=1
docker-compose down
```

## Cleanup

Stop Redis:
```bash
docker-compose down
```

Remove Redis data:
```bash
docker-compose down -v
```

## Integration Example

```rust
use embedding_cache::EmbeddingCache;

// Initialize cache
let cache = EmbeddingCache::new(
    "redis://127.0.0.1:6379",
    1000,  // memory capacity
    0.0001 // cost per embedding
).await?;

// Use in RAG pipeline
async fn embed_documents(docs: &[String], cache: &EmbeddingCache) -> Result<Vec<Embedding>> {
    cache.get_or_compute_batch(docs, |texts| {
        // Your actual embedding API call
        openai_embed(texts)
    }).await
}

// Monitor performance
let stats = cache.stats().await;
println!("Hit rate: {:.2}%", stats.hit_rate() * 100.0);
println!("Saved: ${:.2}", stats.estimated_cost_saved);
```

## References

- **OpenAI Embeddings Pricing**: https://openai.com/pricing
- **Redis LRU Eviction**: https://redis.io/docs/reference/eviction/
- **LRU Cache in Rust**: https://docs.rs/lru/
- **Redis Rust Client**: https://docs.rs/redis/

## License

MIT
