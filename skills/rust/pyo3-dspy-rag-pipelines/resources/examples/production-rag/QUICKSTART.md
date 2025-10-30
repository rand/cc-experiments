# Production RAG - Quick Start Guide

Get up and running with the Production RAG system in 5 minutes.

## Prerequisites

- **Docker & Docker Compose**: For Qdrant and Redis
- **Rust 1.75+**: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **Python 3.10+**: With pip installed
- **OpenAI API Key**: Get from [platform.openai.com](https://platform.openai.com)

## Quick Start

### 1. Clone and Navigate

```bash
cd production-rag
```

### 2. Environment Setup

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 3. Automated Setup

Run the setup script (recommended):

```bash
./scripts/setup.sh
```

This will:
- Start Qdrant and Redis with Docker
- Create the Qdrant collection
- Install Python dependencies
- Build the Rust application

**OR** Manual Setup:

```bash
# Start infrastructure
docker-compose up -d qdrant redis

# Wait for services
sleep 5

# Create Qdrant collection
curl -X PUT http://localhost:6333/collections/documents \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 384, "distance": "Cosine"}}'

# Install Python dependencies
pip3 install -r python/requirements.txt

# Build Rust application
cargo build --release
```

### 4. Run the Service

```bash
cargo run --release
```

You should see:

```
INFO Starting production RAG system
INFO Server: 0.0.0.0:8080
INFO Qdrant: http://localhost:6333
INFO Redis: redis://localhost:6379
INFO Listening on 0.0.0.0:8080
```

### 5. Test the API

In a new terminal:

```bash
# Health check
curl http://localhost:8080/health | jq

# Index sample document
curl -X POST http://localhost:8080/index \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [{
      "id": "rust-intro",
      "text": "Rust is a systems programming language that runs blazingly fast, prevents segfaults, and guarantees thread safety.",
      "metadata": {"category": "intro"}
    }]
  }' | jq

# Wait a moment for indexing
sleep 2

# Query
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Rust?",
    "top_k": 3
  }' | jq
```

## Usage Examples

### Python Client

```bash
python3 scripts/client.py
```

This will:
1. Check system health
2. Index sample documents about Rust
3. Run several queries
4. Display results with sources and latency

### Bash Test Suite

```bash
./scripts/test_api.sh
```

Runs comprehensive API tests including:
- Health checks
- Document indexing
- Queries with/without reranking
- Cache hit testing
- Metrics collection

### Using Make

```bash
# Show all available commands
make help

# Setup everything
make setup

# Build
make build

# Run
make run

# Test
make test-api

# Start infrastructure only
make infra-up

# View logs
make docker-logs

# Check health
make health

# Show metrics
make metrics
```

## Common Operations

### Index Your Own Documents

```bash
curl -X POST http://localhost:8080/index \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "id": "doc1",
        "text": "Your document content here...",
        "metadata": {"source": "manual", "date": "2025-10-30"}
      }
    ],
    "chunk_size": 512,
    "overlap": 50
  }'
```

### Query with Custom Settings

```bash
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Your question here?",
    "top_k": 5,
    "rerank": true,
    "temperature": 0.7
  }'
```

### Check Metrics

```bash
curl http://localhost:8080/metrics | grep rag_
```

### View Qdrant Dashboard

Open in browser: http://localhost:6333/dashboard

### Access Redis

```bash
docker exec -it production-rag-redis redis-cli
> KEYS emb:*
> GET emb:some-key
```

## Configuration

Key environment variables (see `.env.example` for all options):

```bash
# Server
SERVER_PORT=8080

# Models
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LM_MODEL=gpt-3.5-turbo

# Performance
MAX_CONNECTIONS=100
CACHE_SIZE=10000

# Caching
CACHE_TTL_SECONDS=3600
```

## Troubleshooting

### "Connection refused" errors

**Qdrant**:
```bash
docker ps | grep qdrant
curl http://localhost:6333/healthz
```

**Redis**:
```bash
docker ps | grep redis
redis-cli ping
```

**Solution**: Restart services
```bash
docker-compose restart qdrant redis
```

### "OpenAI API key not set"

Edit `.env` and add:
```bash
OPENAI_API_KEY=sk-your-key-here
```

Then restart the application.

### Slow queries

1. Check cache hit rate:
```bash
curl http://localhost:8080/metrics | grep cache
```

2. Reduce reranking overhead:
```json
{"query": "...", "rerank": false}
```

3. Lower top_k:
```json
{"query": "...", "top_k": 3}
```

### Out of memory

Reduce cache size in `.env`:
```bash
CACHE_SIZE=5000
MAX_CONNECTIONS=50
```

## Next Steps

1. **Read the Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
2. **Deploy to Production**: See [README.md](README.md) for Docker and Kubernetes deployment
3. **Customize Models**: Change `EMBEDDING_MODEL` and `LM_MODEL` in `.env`
4. **Add Authentication**: Implement API key validation in `main.rs`
5. **Monitor**: Set up Prometheus and Grafana dashboards

## Development Workflow

### Watch mode (auto-rebuild on changes)

```bash
cargo install cargo-watch
cargo watch -x 'run --release'
```

### Run tests

```bash
cargo test
./scripts/test_api.sh
```

### Lint and format

```bash
cargo clippy
cargo fmt
```

### Docker build

```bash
docker build -t production-rag:latest .
docker run -p 8080:8080 --env-file .env production-rag:latest
```

## Performance Tips

1. **Use smaller embedding models** for lower latency:
   - `all-MiniLM-L6-v2` (384 dim) - Fast, good quality
   - `all-MiniLM-L12-v2` (384 dim) - Slower, better quality

2. **Enable caching** (default) - 80-90% hit rate typical

3. **Tune batch sizes** in `.env`:
   ```bash
   EMBEDDING_BATCH_SIZE=64  # Larger = more throughput
   ```

4. **Use GPU** if available (requires CUDA setup)

5. **Scale horizontally** with multiple instances + load balancer

## Resources

- **API Documentation**: See [README.md](README.md#api-endpoints)
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Python Integration**: See `python/` directory
- **Scripts**: See `scripts/` directory

## Getting Help

- Check logs: `cargo run --release` output
- View metrics: `curl http://localhost:8080/metrics`
- Test health: `curl http://localhost:8080/health`
- Docker logs: `docker-compose logs -f`

## Clean Up

Stop and remove everything:

```bash
# Stop application (Ctrl+C)

# Stop infrastructure
docker-compose down

# Remove volumes (careful: deletes all data)
docker-compose down -v

# Clean Rust build
cargo clean
```

---

**Ready to go?** Run `./scripts/setup.sh` and start building!
