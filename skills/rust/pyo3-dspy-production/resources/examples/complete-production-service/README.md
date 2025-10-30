# Complete Production DSpy Service

A production-ready service demonstrating best practices for deploying DSpy with Rust/PyO3, featuring:

- Multi-level caching (memory + Redis)
- Circuit breakers for fault tolerance
- Prometheus metrics and monitoring
- Structured JSON logging
- Cost tracking and token usage monitoring
- Health and readiness probes
- Graceful shutdown
- Docker and Kubernetes deployment
- Horizontal pod autoscaling

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Production Service                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────┐ │
│  │ HTTP Server  │────▶│    Router    │────▶│  Handler   │ │
│  │   (Axum)     │     │              │     │            │ │
│  └──────────────┘     └──────────────┘     └─────┬──────┘ │
│                                                   │        │
│                                           ┌───────▼──────┐ │
│                                           │   Service    │ │
│                                           │              │ │
│  ┌──────────────────────────────────────┐│              │ │
│  │        Multi-Level Cache             ││              │ │
│  │  ┌────────────┐    ┌──────────────┐  ││              │ │
│  │  │   Memory   │───▶│    Redis     │  ││              │ │
│  │  │   (Moka)   │    │              │  ││              │ │
│  │  └────────────┘    └──────────────┘  │└──────┬───────┘ │
│  └──────────────────────────────────────┘       │         │
│                                                  │         │
│  ┌───────────────────────────────────────┐      │         │
│  │       Circuit Breakers                │      │         │
│  │   ┌─────────┐  ┌─────────┐           │      │         │
│  │   │ Model A │  │ Model B │  ...      │◀─────┘         │
│  │   └─────────┘  └─────────┘           │                │
│  └───────────────────────────────────────┘                │
│                                                            │
│  ┌───────────────────────────────────────┐                │
│  │      Observability Stack              │                │
│  │  ┌──────────┐  ┌──────────┐          │                │
│  │  │ Metrics  │  │ Logging  │          │                │
│  │  │ (Prom)   │  │ (JSON)   │          │                │
│  │  └──────────┘  └──────────┘          │                │
│  └───────────────────────────────────────┘                │
│                                                            │
│  ┌───────────────────────────────────────┐                │
│  │         Cost Tracking                 │                │
│  │  Tokens • Cost • Request Metrics      │                │
│  └───────────────────────────────────────┘                │
│                                                            │
└─────────────────────────────────────────────────────────────┘
```

## Features

### 1. Multi-Level Caching
- **Memory Cache**: Fast in-process caching using Moka (LRU eviction)
- **Redis Cache**: Distributed caching for multi-instance deployments
- **Cache Hierarchy**: Memory → Redis → DSpy prediction
- **Configurable TTLs**: Separate TTL for each cache level

### 2. Circuit Breakers
- Per-model circuit breakers using failsafe
- Configurable failure/success thresholds
- Automatic recovery with half-open state
- Prevents cascading failures

### 3. Observability

#### Metrics (Prometheus)
- `dspy_predictions_total` - Total predictions by model/variant/status
- `dspy_prediction_duration_seconds` - Prediction latency histogram
- `dspy_cache_operations_total` - Cache hit/miss counters
- `dspy_circuit_breaker_state` - Circuit breaker states
- `dspy_prediction_cost_total` - Total cost in USD
- `dspy_token_usage_total` - Token usage by type
- `dspy_active_predictions` - In-flight prediction count
- `dspy_errors_total` - Error counters by type

#### Logging
- Structured JSON logging
- Request tracing with request IDs
- Performance metrics logged per request
- Error tracking with context

### 4. Cost Tracking
- Token-level tracking (input/output)
- Per-model cost calculation
- Cost aggregation by model and variant
- Real-time cost metrics via `/costs` endpoint

### 5. Health Checks
- `/health` - Liveness probe (uptime, component status)
- `/ready` - Readiness probe (dependency checks)
- `/metrics` - Prometheus metrics
- `/costs` - Cost metrics

### 6. Production Features
- Graceful shutdown
- Request timeouts
- CORS support
- Response compression
- Request tracing
- Configuration from environment

## Quick Start

### Local Development

1. **Install dependencies**:
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Redis
brew install redis  # macOS
apt-get install redis  # Linux

# Start Redis
redis-server
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

3. **Build and run**:
```bash
make build
make run
```

4. **Test the service**:
```bash
# Health check
make test-health

# Make a prediction
make test-predict

# View metrics
make test-metrics

# View costs
make test-costs
```

### Docker Deployment

1. **Build Docker image**:
```bash
make docker-build
```

2. **Run with Docker Compose** (includes Redis, Prometheus, Grafana):
```bash
make docker-compose-up
```

3. **Access services**:
- Application: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

4. **View logs**:
```bash
make docker-compose-logs
```

5. **Stop services**:
```bash
make docker-compose-down
```

### Kubernetes Deployment

1. **Build and tag image**:
```bash
docker build -t your-registry/dspy-production-service:v1.0 .
docker push your-registry/dspy-production-service:v1.0
```

2. **Update deployment image**:
Edit `k8s/deployment.yaml` and update the image name.

3. **Create secrets**:
```bash
kubectl create secret generic dspy-secrets \
  --from-literal=openai_api_key=sk-your-key-here
```

4. **Deploy**:
```bash
make k8s-deploy
```

5. **Check status**:
```bash
make k8s-status
```

6. **View logs**:
```bash
make k8s-logs
```

7. **Access the service**:
```bash
# Port forward
make k8s-port-forward

# Or create an Ingress/LoadBalancer
kubectl expose deployment dspy-production-service --type=LoadBalancer --port=80 --target-port=8080
```

## API Reference

### POST /v1/predict

Make a prediction using DSpy.

**Request**:
```json
{
  "request_id": "optional-request-id",
  "model": "gpt-3.5-turbo",
  "variant": "baseline",
  "input": "What is the capital of France?",
  "parameters": {},
  "use_cache": true
}
```

**Response**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "model": "gpt-3.5-turbo",
  "variant": "baseline",
  "output": "The capital of France is Paris.",
  "metadata": {
    "latency_ms": 245,
    "cached": false,
    "cache_level": null,
    "input_tokens": 7,
    "output_tokens": 8,
    "cost_usd": 0.000031,
    "timestamp": "2025-10-30T12:34:56.789Z"
  }
}
```

### GET /health

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_secs": 3600,
  "redis_connected": true,
  "python_initialized": true,
  "cache_size": 42,
  "circuit_breakers": {
    "gpt-3.5-turbo": "closed",
    "gpt-4": "closed"
  }
}
```

### GET /ready

Readiness check (returns 200 OK if ready, 503 if not).

### GET /metrics

Prometheus metrics in text format.

### GET /costs

Cost tracking metrics.

**Response**:
```json
{
  "gpt-3.5-turbo:baseline": {
    "total_requests": 1523,
    "total_input_tokens": 45690,
    "total_output_tokens": 30460,
    "total_cost_usd": 0.1294,
    "last_updated": "2025-10-30T12:34:56.789Z"
  }
}
```

### GET /config

Service configuration (sanitized, no secrets).

## Configuration

All configuration can be provided via environment variables. See `.env.example` for available options.

### Key Configuration Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | `complete-production-service` | Service name |
| `SERVICE_VERSION` | `0.1.0` | Service version |
| `HOST` | `0.0.0.0` | Bind host |
| `PORT` | `8080` | Bind port |
| `LOG_LEVEL` | `info` | Log level (trace, debug, info, warn, error) |
| `LOG_FORMAT` | `json` | Log format (json, text) |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `MEMORY_CACHE_SIZE` | `10000` | Maximum memory cache entries |
| `MEMORY_CACHE_TTL_SECS` | `300` | Memory cache TTL (5 minutes) |
| `REDIS_CACHE_TTL_SECS` | `3600` | Redis cache TTL (1 hour) |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Failures before opening circuit |
| `CIRCUIT_BREAKER_SUCCESS_THRESHOLD` | `2` | Successes to close circuit |
| `CIRCUIT_BREAKER_TIMEOUT_SECS` | `60` | Circuit breaker timeout |
| `OPENAI_API_KEY` | (required) | OpenAI API key |

## Monitoring

### Prometheus

Access Prometheus at http://localhost:9090 (when using Docker Compose).

**Example queries**:
```promql
# Request rate
rate(dspy_predictions_total[5m])

# Error rate
rate(dspy_predictions_total{status="error"}[5m])

# P95 latency
histogram_quantile(0.95, rate(dspy_prediction_duration_seconds_bucket[5m]))

# Cache hit rate
rate(dspy_cache_operations_total{operation="hit"}[5m]) / rate(dspy_cache_operations_total[5m])

# Total cost
sum(dspy_prediction_cost_total)
```

### Grafana

Access Grafana at http://localhost:3000 (admin/admin).

1. Add Prometheus datasource (already configured in docker-compose)
2. Import or create dashboards
3. Monitor key metrics:
   - Request rate and latency
   - Error rates
   - Cache hit ratio
   - Circuit breaker states
   - Cost tracking

## Performance Tuning

### Cache Tuning
- Increase `MEMORY_CACHE_SIZE` for more in-memory caching
- Adjust TTLs based on data freshness requirements
- Monitor cache hit rates and adjust accordingly

### Circuit Breaker Tuning
- Lower `FAILURE_THRESHOLD` for faster failure detection
- Increase `TIMEOUT_SECS` for slow-recovering services
- Monitor circuit breaker state changes

### Resource Limits
Kubernetes resource requests/limits:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "200m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

Adjust based on actual usage patterns.

### Horizontal Scaling
The HPA configuration automatically scales based on:
- CPU utilization (70%)
- Memory utilization (80%)
- Request rate (100 requests/pod/sec)

Adjust in `k8s/hpa.yaml`.

## Troubleshooting

### Service won't start
- Check Redis connectivity
- Verify Python installation
- Check environment variables
- Review logs: `make docker-compose-logs` or `make k8s-logs`

### High latency
- Check cache hit rate
- Monitor circuit breaker states
- Review Prometheus metrics
- Check Redis performance

### Circuit breaker open
- Check underlying service health
- Review error logs
- Adjust failure threshold if needed
- Monitor recovery attempts

### Memory issues
- Reduce `MEMORY_CACHE_SIZE`
- Check for memory leaks
- Review pod memory limits
- Monitor memory metrics

## Development

### Running tests
```bash
make test
```

### Code quality
```bash
make check  # Run clippy and format checks
make fmt    # Format code
```

### Local development workflow
```bash
# Start dependencies
docker-compose up -d redis prometheus grafana

# Run service locally
cargo run

# Make changes, test, iterate
make test

# Stop dependencies
docker-compose down
```

## Production Checklist

Before deploying to production:

- [ ] Update `OPENAI_API_KEY` in secrets
- [ ] Configure appropriate resource limits
- [ ] Set up monitoring alerts in Prometheus/Grafana
- [ ] Configure log aggregation (ELK, Loki, CloudWatch)
- [ ] Set up distributed tracing (Jaeger, Tempo)
- [ ] Configure ingress/load balancer
- [ ] Set up TLS certificates
- [ ] Configure network policies
- [ ] Set up backup for Redis (if using persistence)
- [ ] Configure autoscaling parameters
- [ ] Set up cost alerts
- [ ] Document runbooks for common issues
- [ ] Test disaster recovery procedures

## Security Considerations

- Never commit API keys to version control
- Use Kubernetes secrets for sensitive data
- Run containers as non-root user (already configured)
- Keep dependencies updated
- Use private container registries
- Configure network policies to restrict traffic
- Enable pod security policies
- Regular security scanning of container images

## License

MIT

## Support

For issues and questions:
- Check logs for error messages
- Review Prometheus metrics
- Consult troubleshooting section
- Check circuit breaker states
- Review cost metrics for unexpected usage
