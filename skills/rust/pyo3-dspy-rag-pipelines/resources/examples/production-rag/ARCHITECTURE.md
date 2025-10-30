# Production RAG System Architecture

## System Overview

This production RAG system combines Rust's performance and safety with Python's rich ML ecosystem through PyO3 integration.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Applications                          │
│  (HTTP API, Python SDK, CLI tools, Web interfaces)                  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Axum HTTP Server (Rust)                         │
│  ┌────────────┬────────────┬────────────┬─────────────────────┐    │
│  │  /query    │  /index    │  /health   │    /metrics         │    │
│  │  endpoint  │  endpoint  │  endpoint  │    endpoint         │    │
│  └────────────┴────────────┴────────────┴─────────────────────┘    │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Embedder   │      │   Reranker   │      │  Generator   │
│   (Python)   │      │   (Python)   │      │   (Python)   │
│              │      │              │      │              │
│ Sentence     │      │ Cross-       │      │ OpenAI       │
│ Transformers │      │ Encoder      │      │ API          │
└──────────────┘      └──────────────┘      └──────────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                               ▼
                    ┌─────────────────┐
                    │  Cache Manager  │
                    │     (Rust)      │
                    └─────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
        ┌──────────────┐            ┌──────────────┐
        │  L1 Cache    │            │  L2 Cache    │
        │  (Memory)    │            │  (Redis)     │
        │              │            │              │
        │  Moka LRU    │            │  Persistent  │
        │  10k items   │            │  1h TTL      │
        └──────────────┘            └──────────────┘
                │
                ▼
        ┌──────────────┐
        │  Vector DB   │
        │  (Qdrant)    │
        │              │
        │  HNSW Index  │
        │  384-dim     │
        └──────────────┘
```

## Component Details

### 1. HTTP API Layer (Axum)

**Technology**: Axum web framework on Tokio async runtime

**Responsibilities**:
- HTTP request/response handling
- Request validation and deserialization
- Response serialization
- CORS and timeout middleware
- Structured logging
- Metrics collection

**Key Features**:
- Async/await for high concurrency
- Type-safe routing with extractors
- Tower middleware stack
- Graceful shutdown

### 2. Application State (Rust)

**Responsibilities**:
- Configuration management
- Connection pooling (Qdrant, Redis)
- Cache coordination
- PyO3 Python interpreter management

**Key Features**:
- Arc-wrapped shared state for multi-threading
- Connection manager for Redis
- HTTP client for Qdrant
- LRU cache with time-based eviction

### 3. Embedding Layer (Python via PyO3)

**Technology**: sentence-transformers (SBERT)

**Responsibilities**:
- Text embedding generation
- Model loading and inference
- Batch processing

**Flow**:
```rust
// Rust calls Python
let embedding: Vec<f32> = Python::with_gil(|py| {
    let embedder = PyModule::import(py, "embedder")?;
    embedder.call_method1("embed", (text,))?.extract()
})?;
```

**Optimization**:
- Model cached in Python process
- Batch embedding for efficiency
- Results cached in Rust layer

### 4. Two-Tier Cache System

#### L1 Cache (Memory - Moka)
- **Size**: 10,000 entries (configurable)
- **TTL**: 1 hour
- **Strategy**: LRU eviction
- **Latency**: <1ms
- **Scope**: Per-process

#### L2 Cache (Redis)
- **Size**: Limited by Redis memory
- **TTL**: 1 hour (configurable)
- **Strategy**: LRU eviction (Redis maxmemory-policy)
- **Latency**: ~1-3ms
- **Scope**: Shared across all instances

#### Cache Key Strategy
```rust
fn cache_key(text: &str) -> String {
    let normalized = text.trim().to_lowercase();
    let hash = sha256(normalized);
    format!("emb:{}", hash)
}
```

#### Cache Hit Flow
```
Query → Check L1 → Hit? Return
                 ↓ Miss
            Check L2 → Hit? Store in L1, Return
                     ↓ Miss
                Compute → Store in L1+L2, Return
```

### 5. Vector Database (Qdrant)

**Technology**: Qdrant vector search engine

**Features**:
- HNSW indexing for fast ANN search
- Payload storage (metadata)
- Distance metrics (Cosine, Dot, Euclidean)
- Filtering and hybrid search
- Quantization support

**Collection Schema**:
```json
{
  "name": "documents",
  "vectors": {
    "size": 384,
    "distance": "Cosine"
  },
  "payload": {
    "text": "string",
    "metadata": "object"
  }
}
```

**Search Flow**:
```rust
// 1. Get query embedding
let embedding = get_embedding(query).await?;

// 2. Search Qdrant
let results = qdrant_client
    .post("/collections/documents/points/search")
    .json({
        "vector": embedding,
        "limit": top_k,
        "with_payload": true
    })
    .send()
    .await?;
```

### 6. Reranking Pipeline (Python via PyO3)

**Technology**: CrossEncoder (sentence-transformers)

**Purpose**: Improve precision by reranking initial retrieval results

**Flow**:
```
Query → Retrieve top_k*2 candidates
      ↓
      Rerank with CrossEncoder
      ↓
      Return top_k results
```

**Performance**:
- ~10-50ms per query (depending on candidate count)
- 15-20% improvement in top-3 accuracy
- Only applied to top candidates (not full corpus)

### 7. Generation Layer (Python via PyO3)

**Technology**: OpenAI API (configurable)

**Responsibilities**:
- Answer generation from context
- Prompt engineering
- Temperature and token control

**Prompt Template**:
```
System: Answer based on the provided context.

Context:
{retrieved_documents}

Question: {user_query}
```

## Data Flow

### Query Processing Flow

```
1. Client Request
   ↓
2. Axum Handler
   ↓
3. Get Query Embedding
   ├─→ Check L1 Cache → Hit? Return
   ├─→ Check L2 Cache → Hit? Store L1, Return
   └─→ Compute Embedding → Store L1+L2, Return
   ↓
4. Vector Search (Qdrant)
   ↓
5. Rerank (if enabled)
   ↓
6. Generate Answer (LLM)
   ↓
7. Format Response
   ↓
8. Update Metrics
   ↓
9. Return to Client
```

### Indexing Flow

```
1. Client Request (documents)
   ↓
2. Axum Handler
   ↓
3. Chunk Documents
   ├─→ Split by chunk_size
   └─→ Apply overlap
   ↓
4. Batch Embedding
   ├─→ Check cache for each chunk
   ├─→ Compute missing embeddings
   └─→ Store in cache
   ↓
5. Upload to Qdrant
   ├─→ Create points with vectors
   └─→ Attach payload (text + metadata)
   ↓
6. Return Success
```

## Performance Characteristics

### Latency Breakdown (Typical Query)

| Component           | Latency | Notes                    |
|---------------------|---------|--------------------------|
| HTTP overhead       | ~1ms    | Axum processing          |
| Embedding (cached)  | <1ms    | L1 cache hit             |
| Embedding (L2)      | ~2ms    | Redis cache hit          |
| Embedding (compute) | ~30ms   | Python inference         |
| Vector search       | ~10ms   | Qdrant HNSW search       |
| Reranking           | ~20ms   | CrossEncoder (5 docs)    |
| Generation          | ~200ms  | OpenAI API call          |
| **Total (cached)**  | ~230ms  | With embedding cache hit |
| **Total (uncached)**| ~260ms  | With embedding compute   |

### Throughput

- **Concurrent requests**: 100+ (configurable)
- **Queries per second**: ~50-100 (depending on cache hit rate)
- **Indexing throughput**: ~100 documents/second (with batching)

### Scaling Characteristics

#### Vertical Scaling
- **CPU**: Tokio runtime scales to available cores
- **Memory**: Cache size configurable, Python model memory
- **Storage**: Limited by Qdrant and Redis capacity

#### Horizontal Scaling
- **Stateless**: Application servers are stateless
- **Shared cache**: Redis provides shared L2 cache
- **Shared vector DB**: Qdrant can be clustered
- **Load balancing**: Standard HTTP load balancing

## Configuration

### Environment Variables

```bash
# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
REQUEST_TIMEOUT_SECONDS=30

# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=documents
VECTOR_DIM=384

# Redis
REDIS_URL=redis://redis:6379
CACHE_TTL_SECONDS=3600

# Models
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LM_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=sk-...

# Performance
MAX_CONNECTIONS=100
CACHE_SIZE=10000
WORKER_THREADS=4
```

## Monitoring and Observability

### Metrics (Prometheus)

```
rag_queries_total              # Total queries processed
rag_cache_hits_total           # Cache hits
rag_cache_misses_total         # Cache misses
rag_query_duration_seconds     # Query latency histogram
rag_active_requests            # Current active requests
rag_errors_total               # Errors by type
```

### Health Checks

- **Liveness**: `/health` endpoint
- **Readiness**: Checks Qdrant, Redis, Python components
- **Components**: Individual component health status

### Logging

Structured JSON logging with:
- Request ID for tracing
- Latency measurements
- Error context
- Cache hit/miss tracking

## Security Considerations

### Network Security
- HTTPS recommended for production
- API key authentication (implement as needed)
- CORS configuration for web clients
- Rate limiting (implement as needed)

### Data Security
- Secrets via environment variables
- No sensitive data in logs
- Secure Redis/Qdrant communication (TLS)
- Input validation and sanitization

### Operational Security
- Non-root Docker user
- Minimal Docker image
- Regular dependency updates
- Security scanning (cargo audit)

## Deployment Strategies

### Docker Compose (Development)
```bash
docker-compose up -d
```

### Kubernetes (Production)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-service
spec:
  replicas: 3
  # ... (see README.md for complete example)
```

### Cloud Platforms
- **AWS**: ECS/EKS + ElastiCache + Managed Qdrant
- **GCP**: GKE + Memorystore + Managed Qdrant
- **Azure**: AKS + Azure Cache + Managed Qdrant

## Testing Strategy

### Unit Tests
```bash
cargo test
```

### Integration Tests
```bash
cargo test --test integration
```

### API Tests
```bash
./scripts/test_api.sh
```

### Load Tests
```bash
make load-test
```

## Future Enhancements

### Performance
- [ ] Embedding batch queue for higher throughput
- [ ] Result caching for common queries
- [ ] Streaming responses
- [ ] WebSocket support for real-time updates

### Features
- [ ] Multi-tenancy support
- [ ] Hybrid search (vector + keyword)
- [ ] Query expansion and reformulation
- [ ] Feedback loop for relevance tuning
- [ ] Custom reranking models
- [ ] Document versioning

### Operational
- [ ] Distributed tracing (OpenTelemetry)
- [ ] A/B testing framework
- [ ] Auto-scaling policies
- [ ] Backup and disaster recovery
- [ ] Multi-region deployment

## Troubleshooting

### Common Issues

#### High Latency
1. Check cache hit rate in metrics
2. Verify Qdrant index is built
3. Monitor Python model inference time
4. Check network latency to external APIs

#### Memory Issues
1. Reduce CACHE_SIZE
2. Monitor Python model memory usage
3. Check Redis memory limits
4. Review Qdrant collection size

#### Connection Errors
1. Verify Qdrant is running and reachable
2. Check Redis connection pool settings
3. Review firewall rules
4. Check DNS resolution

## References

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [PyO3 User Guide](https://pyo3.rs/)
- [Axum Framework](https://docs.rs/axum/)
- [Tokio Runtime](https://tokio.rs/)
- [sentence-transformers](https://www.sbert.net/)
