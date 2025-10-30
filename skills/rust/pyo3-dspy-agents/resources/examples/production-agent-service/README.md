# Production Agent Service

Enterprise-grade HTTP API for DSPy agent orchestration with comprehensive monitoring, circuit breakers, and memory persistence.

## Overview

This example demonstrates a production-ready agent service featuring:

- **HTTP API**: RESTful endpoints using Axum
- **Agent Pool Management**: Pre-warmed agent instances with RwLock concurrency
- **Circuit Breakers**: Automatic failure detection and recovery
- **Metrics & Monitoring**: Prometheus integration with custom metrics
- **Memory Persistence**: Redis-backed conversation history
- **Health Checks**: Kubernetes-ready liveness and readiness probes
- **Graceful Shutdown**: Clean resource cleanup on termination
- **Structured Logging**: JSON logs with tracing integration
- **Error Handling**: Comprehensive error types with proper HTTP status codes

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────────────┐
│         Axum HTTP Server            │
│  ┌─────────┬──────────┬──────────┐  │
│  │ /query  │ /metrics │ /health  │  │
│  └────┬────┴────┬─────┴────┬─────┘  │
└───────┼─────────┼──────────┼────────┘
        │         │          │
        ▼         ▼          ▼
┌──────────────────────────────────────┐
│   ProductionAgentSystem              │
│  ┌────────────┬─────────────────┐    │
│  │ Agent Pool │ Circuit Breaker │    │
│  │ (RwLock)   │                 │    │
│  └──────┬─────┴─────────────────┘    │
│         │                             │
│  ┌──────▼───────┬──────────────┐     │
│  │ Tool Registry│ Memory Store │     │
│  └──────────────┴──────────────┘     │
└──────────────────────────────────────┘
         │              │
         ▼              ▼
    ┌────────┐    ┌──────────┐
    │  DSPy  │    │  Redis   │
    │ Agents │    │ (Memory) │
    └────────┘    └──────────┘
```

## Prerequisites

- Rust 1.75+
- Python 3.8+ with DSPy installed
- Docker and Docker Compose (for infrastructure)
- Redis (for memory persistence)
- Prometheus (for metrics)

## Setup

### 1. Install Python Dependencies

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install dspy-ai openai
```

### 2. Configure DSPy

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Start Infrastructure

```bash
docker-compose up -d
```

This starts:
- Redis on port 6379 (memory persistence)
- Prometheus on port 9090 (metrics collection)

### 4. Build the Service

```bash
# Development build
cargo build

# Production build (optimized)
cargo build --release
```

## Running

### Development Mode

```bash
# Using cargo
cargo run --bin server

# Using make
make run
```

The server starts on `http://localhost:3000`.

### Production Mode

```bash
# Run optimized binary
./target/release/server

# Or with make
make run-release
```

### Environment Variables

Configure the service using environment variables:

```bash
# Server configuration
export SERVER_HOST="0.0.0.0"
export SERVER_PORT="3000"

# Agent pool configuration
export AGENT_POOL_SIZE="4"
export AGENT_MAX_RETRIES="3"

# Circuit breaker settings
export CIRCUIT_BREAKER_THRESHOLD="5"
export CIRCUIT_BREAKER_TIMEOUT_SECS="30"

# Memory persistence
export REDIS_URL="redis://localhost:6379"
export MEMORY_TTL_HOURS="24"

# Logging
export RUST_LOG="info,production_agent_service=debug"
export LOG_FORMAT="json"  # or "pretty"

# Run the server
cargo run --bin server
```

## API Endpoints

### POST /api/v1/query

Execute an agent query with conversation memory.

**Request:**
```json
{
  "user_id": "user_123",
  "question": "What's the weather in San Francisco?"
}
```

**Response:**
```json
{
  "answer": "The current weather in San Francisco is...",
  "user_id": "user_123",
  "question": "What's the weather in San Francisco?",
  "reasoning_steps": 3,
  "latency_ms": 542,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:3000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_123", "question": "What is 2+2?"}'
```

### GET /api/v1/metrics

Prometheus-compatible metrics endpoint.

**Response:**
```
# HELP agent_requests_total Total number of agent requests
# TYPE agent_requests_total counter
agent_requests_total{status="success"} 142
agent_requests_total{status="failure"} 3

# HELP agent_latency_seconds Agent request latency
# TYPE agent_latency_seconds histogram
agent_latency_seconds_bucket{le="0.1"} 45
agent_latency_seconds_bucket{le="0.5"} 120
agent_latency_seconds_bucket{le="1.0"} 140
agent_latency_seconds_bucket{le="+Inf"} 145

# HELP agent_pool_size Current agent pool size
# TYPE agent_pool_size gauge
agent_pool_size 4

# HELP circuit_breaker_state Circuit breaker state (0=closed, 1=open, 2=half_open)
# TYPE circuit_breaker_state gauge
circuit_breaker_state 0
```

**cURL Example:**
```bash
curl http://localhost:3000/api/v1/metrics
```

### GET /api/v1/health

Health check endpoint for load balancers and orchestrators.

**Response (Healthy):**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "agent_pool_size": 4,
  "circuit_breaker_state": "closed",
  "checks": {
    "python_runtime": "ok",
    "agent_pool": "ok",
    "circuit_breaker": "ok"
  }
}
```

**Response (Unhealthy):**
```json
{
  "status": "unhealthy",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "agent_pool_size": 0,
  "circuit_breaker_state": "open",
  "checks": {
    "python_runtime": "ok",
    "agent_pool": "failed: no agents available",
    "circuit_breaker": "open"
  }
}
```

**cURL Example:**
```bash
curl http://localhost:3000/api/v1/health
```

## Monitoring

### Prometheus Queries

```promql
# Request rate (requests per second)
rate(agent_requests_total[5m])

# Average latency
rate(agent_latency_seconds_sum[5m]) / rate(agent_latency_seconds_count[5m])

# Error rate
rate(agent_requests_total{status="failure"}[5m]) / rate(agent_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(agent_latency_seconds_bucket[5m]))

# Circuit breaker openings
changes(circuit_breaker_state[1h])
```

### Grafana Dashboard

Import the included Grafana dashboard:

1. Open Grafana at `http://localhost:3001`
2. Go to Dashboards → Import
3. Upload `grafana-dashboard.json`
4. Select Prometheus as the data source

## Production Deployment

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: production-agent-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-service
  template:
    metadata:
      labels:
        app: agent-service
    spec:
      containers:
      - name: agent-service
        image: agent-service:latest
        ports:
        - containerPort: 3000
        env:
        - name: AGENT_POOL_SIZE
          value: "4"
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### Docker

Build and run using Docker:

```bash
# Build image
docker build -t agent-service:latest .

# Run container
docker run -d \
  -p 3000:3000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  agent-service:latest
```

## Testing

### Unit Tests

```bash
cargo test --lib
```

### Integration Tests

```bash
# Start infrastructure
docker-compose up -d

# Run integration tests
cargo test --test integration

# Cleanup
docker-compose down
```

### Load Testing

Using Apache Bench:

```bash
ab -n 1000 -c 10 -p query.json -T application/json \
  http://localhost:3000/api/v1/query
```

Using `hey`:

```bash
hey -n 1000 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"What is 2+2?"}' \
  http://localhost:3000/api/v1/query
```

## Troubleshooting

### Agent Pool Exhaustion

**Symptom:** All requests return 503 Service Unavailable

**Solution:**
1. Check agent pool health: `curl http://localhost:3000/api/v1/health`
2. Increase pool size: `export AGENT_POOL_SIZE=8`
3. Restart service

### Circuit Breaker Open

**Symptom:** Metrics show `circuit_breaker_state=1`

**Solution:**
1. Check error logs for root cause
2. Wait for timeout period (default 30s)
3. Circuit breaker will automatically half-open and retry

### Memory Leaks

**Symptom:** Memory usage grows unbounded

**Solution:**
1. Enable memory limits in Docker/Kubernetes
2. Configure Redis TTL: `export MEMORY_TTL_HOURS=24`
3. Monitor with `docker stats` or Prometheus

### Python Runtime Errors

**Symptom:** Errors about missing Python modules

**Solution:**
```bash
# Verify Python environment
python -c "import dspy; print(dspy.__version__)"

# Reinstall dependencies
pip install --force-reinstall dspy-ai

# Set Python path explicitly
export PYTHONPATH=/path/to/venv/lib/python3.x/site-packages
```

## Performance Tuning

### Agent Pool Size

- **Low traffic (<10 req/s):** 2-4 agents
- **Medium traffic (10-50 req/s):** 4-8 agents
- **High traffic (>50 req/s):** 8-16 agents

### Circuit Breaker Tuning

```bash
# Conservative (fail fast)
export CIRCUIT_BREAKER_THRESHOLD="3"
export CIRCUIT_BREAKER_TIMEOUT_SECS="60"

# Aggressive (more tolerant)
export CIRCUIT_BREAKER_THRESHOLD="10"
export CIRCUIT_BREAKER_TIMEOUT_SECS="15"
```

### Connection Pooling

Edit `Cargo.toml` to adjust Tokio worker threads:

```toml
[dependencies]
tokio = { version = "1.35", features = ["full", "rt-multi-thread"] }
```

Set worker threads:
```bash
export TOKIO_WORKER_THREADS=8
```

## Security

### API Authentication

Add authentication middleware:

```rust
use axum::middleware;

let app = Router::new()
    .route("/api/v1/query", post(query_handler))
    .layer(middleware::from_fn(auth_middleware));
```

### Rate Limiting

Add tower rate limiting:

```bash
cargo add tower-governor
```

### TLS/HTTPS

Use a reverse proxy (nginx, Traefik) for TLS termination:

```nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

## Makefile Commands

```bash
make build          # Build debug binary
make build-release  # Build optimized binary
make run            # Run development server
make run-release    # Run production server
make test           # Run all tests
make docker-build   # Build Docker image
make docker-run     # Run Docker container
make docker-push    # Push to registry
make clean          # Clean build artifacts
make infra-up       # Start Docker Compose services
make infra-down     # Stop Docker Compose services
make logs           # View service logs
make metrics        # Query Prometheus metrics
```

## Contributing

1. Follow Rust API guidelines
2. Add tests for new features
3. Update documentation
4. Run `cargo clippy` and `cargo fmt`

## License

MIT License - see LICENSE file for details

## Resources

- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [Axum Documentation](https://docs.rs/axum/)
- [PyO3 Guide](https://pyo3.rs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
