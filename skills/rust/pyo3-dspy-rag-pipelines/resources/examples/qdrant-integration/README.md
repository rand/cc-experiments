# Qdrant Vector Database Integration

Complete production-ready example of Qdrant vector database integration with Rust client, Python bindings via PyO3, and DSPy Retrieve integration.

## Overview

This example demonstrates:
- Qdrant client initialization (local and cloud)
- Collection creation with vector configuration
- Vector upsert with rich metadata payloads
- Filtered similarity search with scoring
- Payload extraction and processing
- DSPy Retrieve module integration
- Production error handling and connection pooling

## Features

### Rust Implementation
- Type-safe Qdrant client wrapper
- Async operations with proper error handling
- Collection management (create, delete, check existence)
- Batch vector upsert with metadata
- Filtered search with scoring thresholds
- Payload serialization/deserialization
- Connection pooling and retry logic

### Python Integration
- PyO3 bindings for Rust Qdrant client
- DSPy Retrieve module with Qdrant backend
- Seamless integration with DSPy pipelines
- Python-native API with Rust performance

### Production Patterns
- Health checks and connection validation
- Graceful error handling with typed errors
- Resource cleanup and connection management
- Configurable batch sizes and timeouts
- Structured logging for operations
- Docker Compose for local development

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DSPy Pipeline                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Question   │───>│   Retrieve   │───>│   Generate   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ PyO3 bindings
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                 Rust Qdrant Client                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Connect    │───>│    Search    │───>│   Results    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ HTTP/gRPC
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Qdrant Server                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Collection  │───>│   Vectors    │───>│   Payload    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Start Qdrant Server

```bash
# Using Docker Compose
docker-compose up -d

# Verify Qdrant is running
curl http://localhost:6333/health
```

### 2. Build and Run Rust Example

```bash
cargo build --release
cargo run --release
```

### 3. Run Python Integration

```bash
# Install Python dependencies
pip install dspy-ai qdrant-client

# Run Python example
python examples/dspy_integration.py
```

## Configuration

### Environment Variables

```bash
# Qdrant connection
export QDRANT_URL="http://localhost:6333"
export QDRANT_API_KEY=""  # For Qdrant Cloud

# Collection settings
export COLLECTION_NAME="documents"
export VECTOR_SIZE=384
export DISTANCE_METRIC="Cosine"

# Search settings
export SEARCH_LIMIT=10
export SCORE_THRESHOLD=0.7
```

### Qdrant Cloud

```bash
# For Qdrant Cloud
export QDRANT_URL="https://your-cluster.cloud.qdrant.io"
export QDRANT_API_KEY="your-api-key"
```

## Usage Examples

### Rust Client

```rust
use qdrant_integration::{QdrantClient, SearchFilter, VectorPoint};
use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize client
    let client = QdrantClient::new("http://localhost:6333", None).await?;

    // Create collection
    client.create_collection("documents", 384, "Cosine").await?;

    // Upsert vectors
    let points = vec![
        VectorPoint {
            id: "doc1".to_string(),
            vector: vec![0.1; 384],
            payload: serde_json::json!({
                "text": "Qdrant is a vector database",
                "category": "documentation",
                "timestamp": 1234567890
            }),
        }
    ];
    client.upsert_vectors("documents", points).await?;

    // Search with filters
    let results = client.search(
        "documents",
        vec![0.1; 384],
        10,
        Some(SearchFilter {
            must: vec![("category", "documentation")],
            score_threshold: Some(0.7),
        })
    ).await?;

    for result in results {
        println!("ID: {}, Score: {:.4}", result.id, result.score);
        println!("Payload: {}", serde_json::to_string_pretty(&result.payload)?);
    }

    Ok(())
}
```

### Python + DSPy Integration

```python
import dspy
from qdrant_integration import QdrantRM

# Configure DSPy
lm = dspy.OpenAI(model="gpt-4")
rm = QdrantRM(
    url="http://localhost:6333",
    collection_name="documents",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2"
)
dspy.settings.configure(lm=lm, rm=rm)

# Define RAG pipeline
class RAG(dspy.Module):
    def __init__(self, num_passages=3):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=num_passages)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = self.retrieve(question).passages
        return self.generate(context=context, question=question)

# Use pipeline
rag = RAG()
response = rag("What is Qdrant?")
print(response.answer)
```

## API Reference

### QdrantClient

#### Constructor
```rust
pub async fn new(url: &str, api_key: Option<&str>) -> Result<Self>
```
Create a new Qdrant client with optional API key for cloud deployment.

#### Collection Management
```rust
pub async fn create_collection(
    &self,
    name: &str,
    vector_size: u64,
    distance: &str
) -> Result<()>

pub async fn delete_collection(&self, name: &str) -> Result<()>

pub async fn collection_exists(&self, name: &str) -> Result<bool>
```

#### Vector Operations
```rust
pub async fn upsert_vectors(
    &self,
    collection: &str,
    points: Vec<VectorPoint>
) -> Result<()>

pub async fn search(
    &self,
    collection: &str,
    query_vector: Vec<f32>,
    limit: usize,
    filter: Option<SearchFilter>
) -> Result<Vec<SearchResult>>
```

#### Health Check
```rust
pub async fn health_check(&self) -> Result<bool>
```

### Data Structures

#### VectorPoint
```rust
pub struct VectorPoint {
    pub id: String,
    pub vector: Vec<f32>,
    pub payload: serde_json::Value,
}
```

#### SearchFilter
```rust
pub struct SearchFilter {
    pub must: Vec<(String, String)>,
    pub score_threshold: Option<f32>,
}
```

#### SearchResult
```rust
pub struct SearchResult {
    pub id: String,
    pub score: f32,
    pub payload: serde_json::Value,
}
```

## Production Considerations

### Performance
- **Batch Operations**: Use batch upsert for inserting multiple vectors
- **Connection Pooling**: Client maintains connection pool internally
- **Async Operations**: All operations are async for high concurrency
- **Vector Dimensions**: Match embedding model output (384 for MiniLM, 768 for BERT)

### Reliability
- **Health Checks**: Validate connection before operations
- **Retry Logic**: Automatic retry with exponential backoff
- **Error Types**: Typed errors for better handling
- **Timeouts**: Configurable request timeouts

### Scaling
- **Horizontal Scaling**: Qdrant supports clustering
- **Sharding**: Distribute collections across nodes
- **Replication**: High availability with replicas
- **Resource Limits**: Configure memory and disk limits

### Security
- **API Keys**: Use API keys for authentication
- **TLS/SSL**: Enable HTTPS for production
- **Network Isolation**: Run Qdrant in private network
- **Access Control**: Implement application-level ACLs

## Troubleshooting

### Connection Issues
```bash
# Check Qdrant is running
curl http://localhost:6333/health

# Check logs
docker logs qdrant

# Test connection
cargo run -- --health-check
```

### Performance Issues
```bash
# Monitor Qdrant metrics
curl http://localhost:6333/metrics

# Check collection stats
curl http://localhost:6333/collections/documents

# Optimize HNSW index
# Increase ef_construct and m parameters in collection config
```

### Memory Issues
```bash
# Monitor Qdrant memory usage
docker stats qdrant

# Configure memory limits in docker-compose.yml
mem_limit: 4g
memswap_limit: 4g
```

## Testing

```bash
# Run unit tests
cargo test

# Run integration tests (requires running Qdrant)
docker-compose up -d
cargo test --test integration

# Run benchmarks
cargo bench

# Cleanup
docker-compose down -v
```

## Advanced Features

### Named Vectors
```rust
// Store multiple vector representations per point
client.create_collection_multi_vector(
    "documents",
    vec![
        ("dense", 384, "Cosine"),
        ("sparse", 1000, "Dot"),
    ]
).await?;
```

### Quantization
```rust
// Enable scalar quantization for memory efficiency
client.enable_quantization("documents", "scalar").await?;
```

### Snapshots
```rust
// Create snapshot for backup
let snapshot_path = client.create_snapshot("documents").await?;

// Restore from snapshot
client.restore_snapshot("documents", &snapshot_path).await?;
```

## Resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Qdrant Rust Client](https://github.com/qdrant/rust-client)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [Vector Search Best Practices](https://qdrant.tech/articles/vector-search-best-practices/)

## License

MIT License - See LICENSE file for details
