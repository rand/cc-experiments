# WebSocket Service Example

Real-time AI service with WebSocket API for streaming DSPy responses to browser clients.

## Features

- **WebSocket Streaming**: Real-time token streaming to connected clients
- **Connection Management**: Handle multiple concurrent WebSocket connections
- **Message Protocol**: Structured JSON message format for queries and responses
- **Broadcast Support**: Send updates to all connected clients or specific sessions
- **Production Ready**: Error handling, graceful shutdown, health checks
- **Static Client**: Included HTML/JS WebSocket client for testing

## Architecture

```
┌─────────────┐      WebSocket      ┌──────────────┐      PyO3       ┌─────────┐
│   Browser   │ ←─────────────────→ │     Axum     │ ←──────────────→ │  DSPy   │
│   Client    │    JSON Messages    │   Server     │   Async Calls   │ Python  │
└─────────────┘                     └──────────────┘                  └─────────┘
                                            │
                                            ↓
                                    ┌──────────────┐
                                    │  Connection  │
                                    │   Manager    │
                                    └──────────────┘
```

## Message Protocol

### Client → Server

**Query Message**:
```json
{
  "type": "query",
  "session_id": "uuid-v4",
  "query": "What is the capital of France?",
  "stream": true
}
```

**Ping Message**:
```json
{
  "type": "ping"
}
```

### Server → Client

**Stream Token**:
```json
{
  "type": "token",
  "session_id": "uuid-v4",
  "token": "Paris",
  "index": 5
}
```

**Stream End**:
```json
{
  "type": "end",
  "session_id": "uuid-v4",
  "total_tokens": 10,
  "duration_ms": 1523
}
```

**Error**:
```json
{
  "type": "error",
  "session_id": "uuid-v4",
  "error": "Python error: module not found",
  "code": "python_error"
}
```

**Pong**:
```json
{
  "type": "pong",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Quick Start

### Prerequisites

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Python 3.11+
# Install DSPy
pip install dspy-ai
```

### Build and Run

```bash
# Build the project
cargo build --release

# Run the server
cargo run --release

# Or run directly
./target/release/websocket-service
```

The server will start on `http://localhost:8080`.

### Environment Variables

```bash
# Server configuration
export HOST=0.0.0.0
export PORT=8080

# Python configuration
export PYTHONPATH=/path/to/dspy
export DSPY_MODEL=openai/gpt-4

# Logging
export RUST_LOG=info,websocket_service=debug
```

## Testing

### Using the Web Client

1. Start the server:
   ```bash
   cargo run --release
   ```

2. Open browser to: `http://localhost:8080`

3. The static HTML client will connect automatically

4. Type a query and see real-time streaming responses

### Using `websocat`

```bash
# Install websocat
cargo install websocat

# Connect to WebSocket endpoint
websocat ws://localhost:8080/ws

# Send a query (paste JSON and press Enter)
{"type":"query","session_id":"test-123","query":"Hello DSPy","stream":true}

# Watch streaming tokens arrive in real-time
```

### Using JavaScript

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = () => {
  const query = {
    type: 'query',
    session_id: crypto.randomUUID(),
    query: 'Explain quantum computing',
    stream: true
  };
  ws.send(JSON.stringify(query));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log('Received:', msg);

  if (msg.type === 'token') {
    process.stdout.write(msg.token);
  } else if (msg.type === 'end') {
    console.log('\nComplete:', msg);
  } else if (msg.type === 'error') {
    console.error('Error:', msg.error);
  }
};
```

## API Endpoints

### `GET /`
Static HTML client page.

### `GET /health`
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "connections": 5,
  "uptime_seconds": 3600
}
```

### `GET /ws`
WebSocket upgrade endpoint for real-time communication.

**Protocol**: WebSocket (RFC 6455)
**Subprotocol**: None
**Extensions**: permessage-deflate (optional)

## Production Deployment

### Docker

```dockerfile
FROM rust:1.75 as builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install dspy-ai
COPY --from=builder /app/target/release/websocket-service /usr/local/bin/
EXPOSE 8080
CMD ["websocket-service"]
```

Build and run:
```bash
docker build -t websocket-service .
docker run -p 8080:8080 -e RUST_LOG=info websocket-service
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: websocket-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: websocket-service
  template:
    metadata:
      labels:
        app: websocket-service
    spec:
      containers:
      - name: websocket-service
        image: websocket-service:latest
        ports:
        - containerPort: 8080
        env:
        - name: RUST_LOG
          value: "info"
        - name: HOST
          value: "0.0.0.0"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: websocket-service
spec:
  selector:
    app: websocket-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

### systemd Service

```ini
[Unit]
Description=WebSocket AI Service
After=network.target

[Service]
Type=simple
User=websocket
WorkingDirectory=/opt/websocket-service
Environment="RUST_LOG=info"
ExecStart=/opt/websocket-service/websocket-service
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable websocket-service
sudo systemctl start websocket-service
sudo systemctl status websocket-service
```

## Scaling Considerations

### Horizontal Scaling with Redis

For multi-instance deployments, use Redis pub/sub for cross-instance messaging:

```bash
# Start with docker-compose
docker-compose up -d

# This enables:
# - Session affinity via Redis
# - Broadcast to all instances
# - Shared connection state
```

See `docker-compose.yml` for configuration.

### Connection Limits

Default limits:
- Max connections per instance: 10,000
- Max message size: 1 MB
- Idle timeout: 5 minutes
- Ping interval: 30 seconds

Configure in `src/main.rs`:
```rust
const MAX_CONNECTIONS: usize = 10_000;
const MAX_MESSAGE_SIZE: usize = 1024 * 1024;
const IDLE_TIMEOUT: Duration = Duration::from_secs(300);
```

### Load Balancing

Use sticky sessions for WebSocket connections:

**Nginx**:
```nginx
upstream websocket_backend {
    ip_hash;  # Sticky sessions
    server 10.0.0.1:8080;
    server 10.0.0.2:8080;
    server 10.0.0.3:8080;
}

server {
    listen 80;

    location /ws {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }
}
```

## Monitoring

### Metrics

The service exposes Prometheus-compatible metrics at `/metrics` (if enabled):

- `websocket_connections_total`: Total active WebSocket connections
- `websocket_messages_sent_total`: Total messages sent
- `websocket_messages_received_total`: Total messages received
- `websocket_query_duration_seconds`: Query processing duration histogram
- `websocket_errors_total`: Total errors by type

### Logging

Structured JSON logs with tracing:

```bash
# Enable debug logging
RUST_LOG=debug cargo run

# Log to file
cargo run 2>&1 | tee websocket-service.log
```

## Security

### TLS/SSL

For production, use TLS:

```rust
// In main.rs, replace:
let listener = tokio::net::TcpListener::bind(&addr).await?;

// With:
use tokio_rustls::TlsAcceptor;
let tls_config = load_tls_config()?;
let acceptor = TlsAcceptor::from(tls_config);
```

### Authentication

Add authentication middleware:

```rust
use axum::middleware;

let app = Router::new()
    .route("/ws", get(websocket_handler))
    .layer(middleware::from_fn(auth_middleware));
```

### Rate Limiting

Implement per-connection rate limiting:

```rust
use governor::{Quota, RateLimiter};

let limiter = RateLimiter::direct(
    Quota::per_second(nonzero!(10u32))
);
```

## Troubleshooting

### Connection Refused

```bash
# Check if server is running
curl http://localhost:8080/health

# Check firewall
sudo ufw status
sudo ufw allow 8080/tcp
```

### Python Import Errors

```bash
# Verify Python environment
python3 -c "import dspy; print(dspy.__version__)"

# Set PYTHONPATH
export PYTHONPATH=/path/to/dspy:$PYTHONPATH
```

### WebSocket Handshake Failed

- Ensure proper `Upgrade` and `Connection` headers
- Check for proxy/load balancer WebSocket support
- Verify no conflicting HTTP interceptors

### High Memory Usage

- Limit max connections
- Implement connection pooling
- Enable message compression
- Monitor with `htop` or `ps`

## Performance Tuning

### Tokio Runtime

```rust
#[tokio::main]
async fn main() {
    tokio::runtime::Builder::new_multi_thread()
        .worker_threads(num_cpus::get())
        .thread_name("websocket-worker")
        .enable_all()
        .build()
        .unwrap()
        .block_on(async_main())
}
```

### Message Compression

Enable per-message deflate:
```rust
use axum::extract::ws::WebSocketUpgrade;

ws.on_upgrade(|socket| {
    socket.with_compression(true)
})
```

## Examples

See `static/index.html` for a complete browser-based client implementation.

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.

## Support

For questions or issues:
- GitHub Issues: [your-repo]/issues
- Documentation: [your-docs-url]
