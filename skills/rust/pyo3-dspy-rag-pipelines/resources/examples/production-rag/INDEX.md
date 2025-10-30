# Production RAG - File Index

Quick reference guide to all files in the project.

## Start Here

| File | Purpose | Read This If... |
|------|---------|-----------------|
| **[QUICKSTART.md](QUICKSTART.md)** | 5-minute setup guide | You want to get started quickly |
| **[README.md](README.md)** | Complete documentation | You want comprehensive details |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System architecture | You want to understand design decisions |
| **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** | Project overview | You want a high-level summary |

## Core Application

### Rust Source Code

| File | Lines | Description |
|------|-------|-------------|
| [src/main.rs](src/main.rs) | 680 | Main application with API handlers, caching, vector search, PyO3 integration |
| [src/config.rs](src/config.rs) | 243 | Configuration management with environment variables and validation |

**Key Components in main.rs**:
- HTTP API endpoints (query, index, health, metrics)
- Two-tier cache (Memory + Redis)
- Vector search (Qdrant integration)
- PyO3 embedding and reranking
- Prometheus metrics
- Error handling

### Python Modules

| File | Lines | Description |
|------|-------|-------------|
| [python/embedder.py](python/embedder.py) | 178 | Text embedding with sentence-transformers, called from Rust via PyO3 |
| [python/reranker.py](python/reranker.py) | 198 | Document reranking with CrossEncoder, called from Rust via PyO3 |
| [python/requirements.txt](python/requirements.txt) | 20 | Python dependencies |

**Key Features**:
- Model caching for efficiency
- Batch processing support
- Error handling across Rust-Python boundary

## Configuration & Setup

| File | Lines | Purpose |
|------|-------|---------|
| [Cargo.toml](Cargo.toml) | 68 | Rust dependencies and build configuration |
| [.env.example](.env.example) | 32 | Configuration template (copy to `.env`) |
| [docker-compose.yml](docker-compose.yml) | 116 | Full stack: Qdrant, Redis, Prometheus, Grafana |
| [Dockerfile](Dockerfile) | 60 | Multi-stage production image |
| [prometheus.yml](prometheus.yml) | 27 | Metrics scraping configuration |
| [Makefile](Makefile) | 140 | Development commands and shortcuts |
| [.gitignore](.gitignore) | 40 | Git ignore patterns |

## Scripts & Tools

| File | Lines | Purpose |
|------|-------|---------|
| [scripts/setup.sh](scripts/setup.sh) | 101 | Automated setup: infrastructure + dependencies |
| [scripts/test_api.sh](scripts/test_api.sh) | 100 | Comprehensive API test suite |
| [scripts/client.py](scripts/client.py) | 193 | Python client library and examples |

**Usage**:
```bash
./scripts/setup.sh        # Initial setup
./scripts/test_api.sh     # Test the API
python3 scripts/client.py # Run Python examples
```

## Examples & Tests

| File | Lines | Purpose |
|------|-------|---------|
| [examples/pyo3_integration.rs](examples/pyo3_integration.rs) | 374 | 10 advanced PyO3 integration patterns |
| [tests/integration_test.rs](tests/integration_test.rs) | 423 | 10 integration tests covering all endpoints |

**Run Examples**:
```bash
cargo run --example pyo3_integration  # PyO3 patterns
cargo test --test integration        # Integration tests
```

## Documentation

| File | Lines | Focus |
|------|-------|-------|
| [README.md](README.md) | 466 | Complete system documentation, API reference, deployment |
| [QUICKSTART.md](QUICKSTART.md) | 388 | Getting started in 5 minutes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 495 | Architecture diagrams, design decisions, performance |
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | 392 | High-level overview, statistics, technologies |
| [INDEX.md](INDEX.md) | This file | File navigation guide |

## File Organization

```
production-rag/
├── Documentation (5 files, ~2,200 lines)
│   ├── INDEX.md               ← You are here
│   ├── README.md              ← Start here for details
│   ├── QUICKSTART.md          ← Start here for quick setup
│   ├── ARCHITECTURE.md        ← Architecture deep dive
│   └── PROJECT_SUMMARY.md     ← Project overview
│
├── Source Code (~1,100 lines)
│   ├── src/
│   │   ├── main.rs            ← Main application logic
│   │   └── config.rs          ← Configuration management
│   └── python/
│       ├── embedder.py        ← Embedding module (PyO3)
│       ├── reranker.py        ← Reranking module (PyO3)
│       └── requirements.txt   ← Python dependencies
│
├── Configuration (~300 lines)
│   ├── Cargo.toml             ← Rust dependencies
│   ├── .env.example           ← Config template
│   ├── docker-compose.yml     ← Container orchestration
│   ├── Dockerfile             ← Production image
│   ├── prometheus.yml         ← Metrics config
│   ├── Makefile               ← Dev commands
│   └── .gitignore             ← Git ignore
│
├── Scripts (~400 lines)
│   ├── scripts/setup.sh       ← Automated setup
│   ├── scripts/test_api.sh    ← API tests
│   └── scripts/client.py      ← Python client
│
└── Examples & Tests (~800 lines)
    ├── examples/pyo3_integration.rs  ← PyO3 patterns
    └── tests/integration_test.rs     ← Integration tests
```

## Code Statistics

| Category | Files | Lines | Description |
|----------|-------|-------|-------------|
| **Documentation** | 5 | ~2,200 | README, guides, architecture |
| **Source Code** | 4 | ~1,100 | Rust + Python implementation |
| **Configuration** | 7 | ~300 | Dependencies, Docker, Make |
| **Scripts** | 3 | ~400 | Setup, testing, client |
| **Examples/Tests** | 2 | ~800 | Integration patterns and tests |
| **Total** | **21** | **~4,800** | **Complete production system** |

## Quick Navigation

### I want to...

**...get started quickly**
→ [QUICKSTART.md](QUICKSTART.md) + `./scripts/setup.sh`

**...understand the architecture**
→ [ARCHITECTURE.md](ARCHITECTURE.md)

**...see the API documentation**
→ [README.md](README.md#api-endpoints)

**...learn PyO3 patterns**
→ [examples/pyo3_integration.rs](examples/pyo3_integration.rs)

**...modify the configuration**
→ [.env.example](.env.example) + [src/config.rs](src/config.rs)

**...add a new endpoint**
→ [src/main.rs](src/main.rs) (search for "handle_query")

**...change the embedding model**
→ [python/embedder.py](python/embedder.py) + `.env` (EMBEDDING_MODEL)

**...deploy to production**
→ [README.md](README.md#deployment) + [Dockerfile](Dockerfile)

**...run tests**
→ `cargo test` or `./scripts/test_api.sh`

**...see usage examples**
→ [scripts/client.py](scripts/client.py)

**...understand caching**
→ [ARCHITECTURE.md](ARCHITECTURE.md#two-tier-cache-system)

**...monitor the system**
→ [README.md](README.md#monitoring) + `/metrics` endpoint

**...troubleshoot issues**
→ [QUICKSTART.md](QUICKSTART.md#troubleshooting)

## Development Workflow

### First Time Setup
1. Read [QUICKSTART.md](QUICKSTART.md)
2. Run `./scripts/setup.sh`
3. Edit `.env` (copy from `.env.example`)
4. Run `cargo run --release`

### Making Changes
1. Edit code in `src/` or `python/`
2. Run `cargo build`
3. Test with `./scripts/test_api.sh`
4. Check formatting: `cargo fmt`
5. Check linting: `cargo clippy`

### Testing
```bash
cargo test                        # Unit tests
cargo test --test integration     # Integration tests
./scripts/test_api.sh            # API tests
cargo run --example pyo3_integration  # PyO3 examples
```

### Deployment
```bash
make docker-build                 # Build image
make docker-up                    # Start services
make health                       # Check health
make metrics                      # View metrics
```

## Key Files by Use Case

### Learning PyO3
- [examples/pyo3_integration.rs](examples/pyo3_integration.rs) - 10 PyO3 patterns
- [src/main.rs](src/main.rs) - Production PyO3 usage
- [python/embedder.py](python/embedder.py) - Python side of PyO3

### Learning RAG
- [ARCHITECTURE.md](ARCHITECTURE.md) - RAG architecture
- [src/main.rs](src/main.rs) - RAG implementation
- [README.md](README.md) - RAG concepts and API

### Learning Async Rust
- [src/main.rs](src/main.rs) - Async handlers
- [src/config.rs](src/config.rs) - Async initialization
- [tests/integration_test.rs](tests/integration_test.rs) - Async tests

### Learning Caching
- [src/main.rs](src/main.rs) - Two-tier cache implementation
- [ARCHITECTURE.md](ARCHITECTURE.md#two-tier-cache-system) - Cache design

### Learning Vector Search
- [src/main.rs](src/main.rs) - Qdrant integration
- [docker-compose.yml](docker-compose.yml) - Qdrant setup
- [ARCHITECTURE.md](ARCHITECTURE.md#vector-database-qdrant) - Vector DB usage

## External Resources

### Technologies Used
- **Rust**: [rust-lang.org](https://www.rust-lang.org/)
- **PyO3**: [pyo3.rs](https://pyo3.rs/)
- **Tokio**: [tokio.rs](https://tokio.rs/)
- **Axum**: [docs.rs/axum](https://docs.rs/axum/)
- **Qdrant**: [qdrant.tech](https://qdrant.tech/)
- **sentence-transformers**: [sbert.net](https://www.sbert.net/)

### Learning Resources
- **PyO3 Guide**: [pyo3.rs/latest](https://pyo3.rs/v0.20.0/)
- **Async Rust**: [rust-lang.org/async-book](https://rust-lang.github.io/async-book/)
- **RAG Patterns**: [pinecone.io/learn/rag](https://www.pinecone.io/learn/retrieval-augmented-generation/)

## Support

### Documentation
- All documentation is in this directory
- Start with [QUICKSTART.md](QUICKSTART.md) or [README.md](README.md)
- Architecture questions → [ARCHITECTURE.md](ARCHITECTURE.md)

### Code Examples
- PyO3 patterns → [examples/pyo3_integration.rs](examples/pyo3_integration.rs)
- API usage → [scripts/client.py](scripts/client.py)
- Testing → [tests/integration_test.rs](tests/integration_test.rs)

### Troubleshooting
- Common issues → [QUICKSTART.md](QUICKSTART.md#troubleshooting)
- Configuration → [.env.example](.env.example)
- Health check → `curl http://localhost:8080/health`

---

**Navigation tip**: Use your editor's "Go to file" (Ctrl+P / Cmd+P) to quickly jump to any file listed here!
