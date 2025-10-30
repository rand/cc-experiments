# Production RAG System

A complete, production-ready Retrieval-Augmented Generation (RAG) system built with Rust and Python, demonstrating enterprise patterns for real-world deployments.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      HTTP API (Axum)                        │
│  /query  /health  /metrics  /index  /reindex               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   DSPy LM    │     │   Embedder   │     │  Reranker    │
│   (Python)   │     │   (Python)   │     │   (Python)   │
└──────────────┘     └──────────────┘     └──────────────┘
                              │
                              ▼
                     ┌──────────────┐
                     │ Cache Layer  │
                     │ (Two-Tier)   │
                     │ Memory+Redis │
                     └──────────────┘
                              │
                              ▼
                     ┌──────────────┐
                     │  Vector DB   │
                     │   (Qdrant)   │
                     └──────────────┘
```

## Features

### Core Capabilities
- **Vector Search**: Qdrant integration with HNSW indexing
- **Two-Tier Caching**: In-memory LRU + Redis for embeddings
- **Reranking Pipeline**: Cross-encoder reranking for precision
- **Context Management**: Automatic chunking and overlap handling
- **Async Operations**: Full Tokio async/await throughout

### Production Readiness
- **Health Checks**: Liveness and readiness endpoints
- **Metrics**: Prometheus-compatible metrics
- **Error Handling**: Comprehensive error types and recovery
- **Configuration**: Environment-based config management
- **Logging**: Structured logging with tracing
- **Graceful Shutdown**: Clean resource cleanup

### API Endpoints

#### POST /query
Query the RAG system with automatic retrieval and generation.

```json
{
  "query": "What are the benefits of Rust?",
  "top_k": 5,
  "rerank": true,
  "temperature": 0.7
}
```

Response:
```json
{
  "answer": "Rust offers memory safety without garbage collection...",
  "sources": [
    {"text": "...", "score": 0.92, "metadata": {...}},
    {"text": "...", "score": 0.88, "metadata": {...}}
  ],
  "latency_ms": 245,
  "cache_hit": false
}
```

#### POST /index
Index new documents into the vector database.

```json
{
  "documents": [
    {
      "id": "doc1",
      "text": "Rust is a systems programming language...",
      "metadata": {"source": "docs", "category": "intro"}
    }
  ],
  "chunk_size": 512,
  "overlap": 50
}
```

#### GET /health
Health check endpoint for orchestration.

```json
{
  "status": "healthy",
  "components": {
    "vector_db": "up",
    "cache": "up",
    "embedder": "up"
  },
  "uptime_seconds": 3600
}
```

#### GET /metrics
Prometheus metrics endpoint.

```
# HELP rag_queries_total Total number of queries processed
# TYPE rag_queries_total counter
rag_queries_total 1234

# HELP rag_query_duration_seconds Query latency
# TYPE rag_query_duration_seconds histogram
rag_query_duration_seconds_bucket{le="0.1"} 450
```

## Setup

### Prerequisites
- Rust 1.75+
- Python 3.10+
- Docker and Docker Compose

### Quick Start

1. **Clone and navigate**:
```bash
cd production-rag
```

2. **Start infrastructure**:
```bash
docker-compose up -d
```

This starts:
- Qdrant (vector database) on port 6333
- Redis (cache) on port 6379

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Build and run**:
```bash
cargo build --release
./target/release/production-rag
```

The service will start on `http://localhost:8080`.

### Configuration

All configuration via environment variables:

```bash
# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8080

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=documents
VECTOR_DIM=384

# Redis
REDIS_URL=redis://localhost:6379
CACHE_TTL_SECONDS=3600

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32

# Generation
LM_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=sk-...

# Performance
MAX_CONNECTIONS=100
REQUEST_TIMEOUT_SECONDS=30
CACHE_SIZE=10000
```

## Usage Examples

### Basic Query
```bash
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does Rust ensure memory safety?",
    "top_k": 3
  }'
```

### Index Documents
```bash
curl -X POST http://localhost:8080/index \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "id": "rust-intro",
        "text": "Rust achieves memory safety through its ownership system...",
        "metadata": {"category": "fundamentals"}
      }
    ]
  }'
```

### Health Check
```bash
curl http://localhost:8080/health
```

### Python Client Example
```python
import requests

client = requests.Session()
base_url = "http://localhost:8080"

# Index documents
response = client.post(f"{base_url}/index", json={
    "documents": [
        {
            "id": "doc1",
            "text": "Your document content here...",
            "metadata": {"source": "manual"}
        }
    ]
})
print(f"Indexed: {response.json()}")

# Query
response = client.post(f"{base_url}/query", json={
    "query": "What is ownership in Rust?",
    "top_k": 5,
    "rerank": True
})
result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {len(result['sources'])}")
```

## Python Integration

The system uses PyO3 for seamless Rust-Python integration:

```python
# embeddings.py - Called from Rust
from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts).tolist()

# reranker.py - Called from Rust
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self, model_name: str):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        pairs = [[query, doc] for doc in documents]
        return self.model.predict(pairs).tolist()
```

Rust calls these via PyO3:

```rust
use pyo3::prelude::*;

let embeddings: Vec<Vec<f32>> = Python::with_gil(|py| {
    let embedder = PyModule::import(py, "embeddings")?
        .getattr("Embedder")?
        .call1(("all-MiniLM-L6-v2",))?;

    embedder
        .call_method1("embed", (texts,))?
        .extract()
})?;
```

## Performance Optimization

### Caching Strategy
1. **L1 Cache (Memory)**: LRU cache for hot embeddings (10k entries)
2. **L2 Cache (Redis)**: Persistent cache with TTL (1 hour)
3. **Cache Key**: SHA-256 hash of normalized text

### Batch Processing
- Embedding batching: 32 documents per batch
- Parallel vector search: Up to 10 concurrent searches
- Async I/O throughout

### Resource Limits
- Connection pooling: 100 max connections
- Request timeout: 30 seconds
- Memory limit: Configurable LRU size

## Monitoring

### Metrics Available
- `rag_queries_total`: Total queries processed
- `rag_query_duration_seconds`: Query latency histogram
- `rag_cache_hits_total`: Cache hit counter
- `rag_cache_misses_total`: Cache miss counter
- `rag_errors_total`: Error counter by type
- `rag_active_requests`: Current active requests

### Logging
Structured JSON logging:
```json
{
  "timestamp": "2025-10-30T12:00:00Z",
  "level": "INFO",
  "target": "production_rag::api",
  "message": "Query processed",
  "query": "What is Rust?",
  "latency_ms": 245,
  "cache_hit": false,
  "sources": 5
}
```

## Testing

```bash
# Unit tests
cargo test

# Integration tests
cargo test --test integration

# Load testing
ab -n 1000 -c 10 -p query.json -T application/json \
  http://localhost:8080/query
```

## Deployment

### Docker
```bash
docker build -t production-rag .
docker run -p 8080:8080 --env-file .env production-rag
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag
  template:
    metadata:
      labels:
        app: rag
    spec:
      containers:
      - name: rag
        image: production-rag:latest
        ports:
        - containerPort: 8080
        env:
        - name: QDRANT_URL
          value: "http://qdrant:6333"
        - name: REDIS_URL
          value: "redis://redis:6379"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
```

## Architecture Decisions

### Why Rust for RAG?
- **Performance**: Sub-millisecond overhead for coordination
- **Safety**: Memory safety prevents production crashes
- **Concurrency**: Fearless async/await for high throughput
- **Integration**: PyO3 enables Python ML ecosystem access

### Why Two-Tier Cache?
- **Latency**: Memory cache provides <1ms lookups
- **Scale**: Redis cache shares state across instances
- **Cost**: Reduces embedding API calls by 80-90%

### Why Qdrant?
- **Performance**: HNSW indexing for fast approximate search
- **Features**: Filtering, payload storage, quantization
- **API**: Clean REST/gRPC API from Rust

### Why Reranking?
- **Precision**: Cross-encoder reranking improves top-3 accuracy by 15-20%
- **Cost**: Only rerank top-K candidates, not full corpus
- **Quality**: Better than pure vector similarity alone

## Troubleshooting

### Qdrant Connection Fails
```bash
# Check Qdrant is running
docker ps | grep qdrant

# Check collection exists
curl http://localhost:6333/collections/documents
```

### Redis Connection Fails
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli ping
```

### Slow Queries
1. Check cache hit rate in metrics
2. Verify Qdrant index is built (HNSW)
3. Reduce `top_k` parameter
4. Enable batch processing

### Memory Issues
1. Reduce `CACHE_SIZE` in config
2. Lower `MAX_CONNECTIONS`
3. Enable streaming responses

## Contributing

1. Follow Rust conventions (rustfmt, clippy)
2. Add tests for new features
3. Update documentation
4. Run `cargo test` before submitting

## License

MIT License - see LICENSE file for details.

## Resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [PyO3 User Guide](https://pyo3.rs/)
- [Axum Framework](https://docs.rs/axum/)
- [DSPy Framework](https://github.com/stanfordnlp/dspy)
