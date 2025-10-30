# Embedding Cache Architecture

## System Overview

A production-ready two-tier caching system for expensive embedding operations in RAG pipelines.

## Components

### 1. Memory Cache (LRU)
- **Implementation**: `lru` crate with fixed capacity
- **Capacity**: 1000 embeddings (configurable)
- **Access Time**: ~10μs
- **Eviction**: Least Recently Used (LRU)
- **Use Case**: Hot data, immediate access

### 2. Redis Cache (Persistent)
- **Implementation**: Redis with async client
- **Capacity**: Limited by Redis memory config
- **Access Time**: ~50μs - 1ms
- **Eviction**: allkeys-lru policy
- **TTL**: 30 days
- **Use Case**: Warm data, persistence across restarts

### 3. Statistics Tracker
- **Metrics**: hits, misses, total requests, costs
- **Thread Safety**: Arc<Mutex<>>
- **Calculations**: Hit rate, cost reduction percentage

## Data Flow

```
Request → Memory Cache?
           ├─ HIT → Return (track stats)
           └─ MISS → Redis Cache?
                      ├─ HIT → Promote to memory → Return (track stats)
                      └─ MISS → Compute API?
                                 └─ Store both caches → Return (track stats)
```

## Key Algorithms

### Cache Key Generation
```rust
SHA256(text) → hex → "emb:{hash}"
```
- Deterministic
- Collision-resistant
- Fixed length

### Batch Processing
```rust
1. Partition texts into [cached, uncached]
2. Compute embeddings only for uncached
3. Store computed embeddings
4. Merge results maintaining order
```

### Cache Promotion
- Redis hits promoted to memory cache
- Implements working set optimization
- Reduces repeated Redis lookups

## Performance Characteristics

| Operation | Memory Hit | Redis Hit | API Call |
|-----------|-----------|-----------|----------|
| Latency | ~10μs | ~50μs-1ms | ~200-500ms |
| Cost | Free | Free | $0.0001 |
| Scalability | Limited | High | Rate limited |

## Cost Model

```
cost_saved = hits × cost_per_embedding
cost_total = (hits + misses) × cost_per_embedding
cost_reduction = (cost_saved / cost_total) × 100%
```

### ROI Calculation

**Break-even point**: N requests where cache setup cost equals savings

```
setup_cost = Redis hosting + dev time
savings_per_month = requests × hit_rate × cost_per_embedding
ROI_months = setup_cost / savings_per_month
```

Example:
- 1M requests/month
- 90% hit rate
- $0.0001 per embedding
- Savings: $90/month
- Redis cost: $15/month
- Net savings: $75/month

## Scalability Strategies

### Vertical Scaling
- Increase memory cache capacity
- Increase Redis memory
- Use Redis Cluster for larger datasets

### Horizontal Scaling
- Shared Redis instance across app instances
- Consistent cache across pods/containers
- No coordination needed

### Partitioning
```rust
// Shard by key hash
let shard = hash(key) % num_shards;
let redis_url = redis_urls[shard];
```

## Failure Modes & Mitigation

### Redis Connection Lost
```rust
match cache.get(text).await {
    Ok(Some(emb)) => emb,
    Ok(None) | Err(_) => compute_direct(text).await?
}
```
**Strategy**: Degrade gracefully to direct API calls

### Memory Cache Full
**Behavior**: LRU eviction automatic
**Mitigation**: Monitor eviction rate, tune capacity

### Redis Memory Full
**Behavior**: allkeys-lru eviction
**Mitigation**: Set maxmemory policy, monitor usage

### Cache Stampede
**Problem**: Multiple threads compute same uncached item
**Mitigation**: Use Redis SETNX for distributed locking

```rust
// Pseudo-code
if redis.setnx(f"lock:{key}", ttl=5s) {
    embedding = compute(text);
    cache.put(key, embedding);
    redis.del(f"lock:{key}");
} else {
    // Wait and retry or compute anyway
}
```

## Monitoring & Observability

### Key Metrics
1. **Hit Rate**: hits / total_requests
   - Target: >80% for stable workloads
   - Alert: <60%

2. **P95 Latency**:
   - Target: <100ms with cache
   - Alert: >500ms

3. **Cache Size**:
   - Memory: Current entries / capacity
   - Redis: Memory usage / max_memory
   - Alert: >90% capacity

4. **Eviction Rate**:
   - Items evicted per minute
   - Alert: >100/min indicates undersized cache

5. **Cost Savings**:
   - Dollars saved per day/month
   - Track ROI

### Logging Strategy
```rust
// Log cache misses for analysis
if cache_miss {
    log::info!(
        "Cache miss for key={}, will compute",
        sanitize(key)
    );
}

// Periodic stats dump
every(1.hour, || {
    let stats = cache.stats();
    log::info!("Cache stats: {:?}", stats);
});
```

## Security Considerations

### 1. Cache Key Generation
- SHA-256 prevents text extraction from keys
- No PII in Redis keys

### 2. Data Sensitivity
- Embeddings may encode semantic information
- Consider encryption at rest for sensitive data
- Redis AUTH for access control

### 3. TTL Management
- 30-day TTL prevents indefinite data retention
- Compliant with data retention policies

## Testing Strategy

### Unit Tests
```rust
#[test]
fn test_cache_key_deterministic() { }

#[test]
fn test_stats_calculation() { }
```

### Integration Tests
```rust
#[tokio::test]
async fn test_cache_hit_flow() { }

#[tokio::test]
async fn test_batch_processing() { }
```

### Performance Tests
```rust
#[tokio::test]
async fn bench_cache_latency() {
    // Measure P50, P95, P99
}
```

### Chaos Tests
```rust
#[tokio::test]
async fn test_redis_failure_handling() {
    // Kill Redis mid-operation
}
```

## Configuration Tuning

### Memory Cache Size
```rust
// Formula: (avg_embedding_size × capacity) < available_ram × 0.1
// Example: (1.5KB × 10000) = 15MB

let capacity = match available_ram {
    ram if ram < 1_GB => 1000,
    ram if ram < 4_GB => 5000,
    _ => 10000,
};
```

### Redis Max Memory
```
# redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru
```

### TTL Strategy
```rust
let ttl = match data_volatility {
    High => 24 * 60 * 60,      // 1 day
    Medium => 7 * 24 * 60 * 60, // 7 days
    Low => 30 * 24 * 60 * 60,  // 30 days
};
```

## Future Enhancements

### 1. Distributed Locking
Prevent cache stampede:
```rust
let lock = RedisLock::acquire(&key, Duration::from_secs(5))?;
```

### 2. Cache Warming Scheduler
```rust
#[tokio::main]
async fn warm_cache_job() {
    let queries = load_common_queries().await?;
    for query in queries {
        cache.get_or_compute(&query, api_fn).await?;
    }
}
```

### 3. Adaptive TTL
```rust
// Shorter TTL for frequently-changing data
let ttl = match access_frequency {
    freq if freq > 100/day => 7 * 86400,
    freq if freq > 10/day => 14 * 86400,
    _ => 30 * 86400,
};
```

### 4. Multi-Model Support
```rust
enum EmbeddingModel {
    OpenAI_Ada002,
    OpenAI_TextEmbedding3Small,
    Cohere_Embed,
}

// Cache key includes model
let key = format!("emb:{}:{}", model, hash(text));
```

### 5. Compression
```rust
// Compress embeddings in Redis
let compressed = zstd::encode(&embedding)?;
redis.set(key, compressed)?;
```

## Deployment Checklist

- [ ] Redis deployed with persistence
- [ ] Redis AUTH configured
- [ ] maxmemory and maxmemory-policy set
- [ ] Memory cache size tuned for workload
- [ ] Cost per embedding configured accurately
- [ ] Monitoring/alerting configured
- [ ] Graceful degradation tested
- [ ] Cache warming strategy implemented
- [ ] TTL appropriate for data freshness needs
- [ ] Load testing completed
- [ ] Runbook created for common issues

## References

- LRU Cache: https://docs.rs/lru/
- Redis Rust: https://docs.rs/redis/
- Redis Eviction: https://redis.io/docs/reference/eviction/
- Cache Stampede: https://en.wikipedia.org/wiki/Cache_stampede
