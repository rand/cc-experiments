---
name: protocols-websocket-protocols
description: WebSocket protocol implementation, scaling, and production deployment
---

# WebSocket Protocols

**Scope**: WebSocket protocol (RFC 6455), connection management, load balancing, scaling strategies, security
**Lines**: ~650 (Main skill) | ~8,000+ (Total with Level 3 resources)
**Last Updated**: 2025-10-29
**Level 3 Resources**: Complete ✓ (REFERENCE.md, 3 scripts, 9 examples)

## When to Use This Skill

Activate this skill when:
- Implementing WebSocket servers from scratch
- Designing real-time bidirectional communication systems
- Scaling WebSocket applications horizontally
- Configuring load balancers for WebSocket traffic (nginx, HAProxy)
- Implementing authentication and authorization for WebSocket connections
- Setting up heartbeat and connection health monitoring
- Deploying production WebSocket infrastructure
- Troubleshooting WebSocket connection issues
- Optimizing WebSocket performance and throughput

## Core Concepts

### WebSocket Protocol

**WebSocket** (RFC 6455): Full-duplex communication protocol over a single TCP connection.

**Key characteristics**:
- **Upgrade from HTTP**: Starts as HTTP/1.1 request, upgrades to WebSocket protocol
- **Persistent connection**: Long-lived connection (not request-response)
- **Bidirectional**: Both client and server can send messages independently
- **Low overhead**: 2-byte frame header (vs HTTP headers)
- **Frame-based**: Messages sent as frames (text, binary, control)
- **Built-in ping/pong**: Connection health checking

**Architecture**:
```
Client → HTTP Upgrade Request → Server
       ← 101 Switching Protocols ←
       ↔ WebSocket Frames (bidirectional) ↔
```

---

## WebSocket Handshake

### Client Request

```http
GET /chat HTTP/1.1
Host: server.example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
Origin: http://example.com
```

**Required headers**:
- `Upgrade: websocket` - Request protocol upgrade
- `Connection: Upgrade` - Signals upgrade intent
- `Sec-WebSocket-Key` - Base64-encoded random 16-byte value
- `Sec-WebSocket-Version: 13` - WebSocket protocol version

**Optional headers**:
- `Origin` - For CORS validation
- `Sec-WebSocket-Protocol` - Subprotocol negotiation
- `Sec-WebSocket-Extensions` - Extension negotiation (compression)

### Server Response

```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

**Sec-WebSocket-Accept calculation**:
```python
import base64
import hashlib

def compute_accept(key: str) -> str:
    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    sha1 = hashlib.sha1((key + GUID).encode()).digest()
    return base64.b64encode(sha1).decode()
```

---

## Frame Structure

### Frame Format

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len == 127  |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                               |Masking-key, if MASK set to 1  |
+-------------------------------+-------------------------------+
| Masking-key (continued)       |          Payload Data         |
+-------------------------------- - - - - - - - - - - - - - - - +
:                     Payload Data continued ...                :
+ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
|                     Payload Data continued ...                |
+---------------------------------------------------------------+
```

**Opcodes**:
- `0x0` - Continuation frame
- `0x1` - Text frame (UTF-8)
- `0x2` - Binary frame
- `0x8` - Close frame
- `0x9` - Ping frame
- `0xA` - Pong frame

---

## Python Server Implementation

### Basic Server (websockets library)

```python
import asyncio
import websockets
import json
from typing import Set

class WebSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()

    async def register(self, websocket: websockets.WebSocketServerProtocol):
        """Register new client connection"""
        self.clients.add(websocket)
        print(f"Client connected. Total clients: {len(self.clients)}")

    async def unregister(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister client connection"""
        self.clients.discard(websocket)
        print(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast(self, message: str, exclude=None):
        """Broadcast message to all clients except sender"""
        if self.clients:
            tasks = [
                client.send(message)
                for client in self.clients
                if client != exclude
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def handler(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle individual client connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                # Parse message
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                    elif msg_type == "broadcast":
                        await self.broadcast(message, exclude=websocket)
                    else:
                        await websocket.send(json.dumps({
                            "type": "echo",
                            "data": data
                        }))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    def run(self):
        """Start WebSocket server"""
        start_server = websockets.serve(
            self.handler,
            self.host,
            self.port,
            ping_interval=30,  # Send ping every 30 seconds
            ping_timeout=10,   # Wait 10 seconds for pong
            max_size=10 * 1024 * 1024  # 10 MB max message size
        )

        print(f"WebSocket server starting on ws://{self.host}:{self.port}")
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    server = WebSocketServer()
    server.run()
```

### Python Client

```python
import asyncio
import websockets
import json

async def client():
    uri = "ws://localhost:8765"

    async with websockets.connect(uri) as websocket:
        # Send message
        await websocket.send(json.dumps({
            "type": "message",
            "data": "Hello, server!"
        }))

        # Receive response
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Received: {data}")

        # Ping/pong
        await websocket.send(json.dumps({"type": "ping"}))
        pong = await websocket.recv()
        print(f"Ping response: {pong}")

asyncio.run(client())
```

---

## Load Balancing and Scaling

### Sticky Sessions (Required)

WebSocket connections are stateful and must stay with the same backend server.

**Why needed**:
- Connection state stored on specific server
- Can't switch servers mid-connection
- Load balancer must route all frames from same client to same backend

**Implementation strategies**:
1. **IP-based**: Route based on client IP
2. **Cookie-based**: Set cookie during HTTP upgrade
3. **Connection ID**: Use WebSocket key for routing

### nginx Configuration

```nginx
upstream websocket_backend {
    # IP hash for sticky sessions
    ip_hash;

    server backend1.example.com:8080;
    server backend2.example.com:8080;
    server backend3.example.com:8080;
}

server {
    listen 80;
    server_name ws.example.com;

    location /ws {
        # WebSocket proxying
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Timeouts (increase for long-lived connections)
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;

        # Disable buffering
        proxy_buffering off;
    }
}
```

### HAProxy Configuration

```haproxy
frontend websocket_front
    bind *:80
    default_backend websocket_back

backend websocket_back
    # Sticky session using source IP
    balance source

    # Health check
    option httpchk GET /health
    http-check expect status 200

    # Timeouts for long-lived connections
    timeout tunnel 3600s

    server ws1 backend1.example.com:8080 check
    server ws2 backend2.example.com:8080 check
    server ws3 backend3.example.com:8080 check
```

---

## Horizontal Scaling with Redis Pub/Sub

### Problem

Load-balanced WebSocket servers need to communicate to broadcast messages.

**Example**: User A connects to Server 1, User B connects to Server 2. When A sends a message, Server 1 needs to notify Server 2 to send to B.

### Solution: Redis Pub/Sub

```python
import asyncio
import websockets
import redis
import json
from typing import Set

class ScalableWebSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()

        # Redis for pub/sub
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe('websocket_broadcast')

    async def register(self, websocket: websockets.WebSocketServerProtocol):
        self.clients.add(websocket)

    async def unregister(self, websocket: websockets.WebSocketServerProtocol):
        self.clients.discard(websocket)

    async def local_broadcast(self, message: str):
        """Broadcast to local clients only"""
        if self.clients:
            tasks = [client.send(message) for client in self.clients]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def global_broadcast(self, message: str):
        """Broadcast to all servers via Redis"""
        self.redis_client.publish('websocket_broadcast', message)

    async def redis_listener(self):
        """Listen for Redis pub/sub messages"""
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                data = message['data']
                await self.local_broadcast(data)

    async def handler(self, websocket: websockets.WebSocketServerProtocol, path: str):
        await self.register(websocket)
        try:
            async for message in websocket:
                # Broadcast to all servers
                await self.global_broadcast(message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    def run(self):
        # Start Redis listener in background
        asyncio.create_task(self.redis_listener())

        start_server = websockets.serve(self.handler, self.host, self.port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
```

---

## Security

### Authentication

**Option 1: Token in URL**

```javascript
// Client
const token = "user-auth-token";
const ws = new WebSocket(`wss://api.example.com/ws?token=${token}`);
```

```python
# Server: Extract token from query params
async def handler(websocket, path):
    from urllib.parse import urlparse, parse_qs

    query = parse_qs(urlparse(path).query)
    token = query.get('token', [None])[0]

    if not verify_token(token):
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Continue with authenticated connection
```

**Option 2: Auth message after connection**

```javascript
// Client
const ws = new WebSocket("wss://api.example.com/ws");
ws.onopen = () => {
    ws.send(JSON.stringify({ type: "auth", token: "user-token" }));
};
```

```python
# Server: Validate auth message within timeout
async def handler(websocket, path):
    try:
        # Wait for auth message (5 second timeout)
        auth_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        data = json.loads(auth_msg)

        if data.get('type') != 'auth' or not verify_token(data.get('token')):
            await websocket.close(code=4002, reason="Authentication failed")
            return

        # Authenticated, continue
    except asyncio.TimeoutError:
        await websocket.close(code=4003, reason="Auth timeout")
        return
```

### TLS/SSL (wss://)

```python
import ssl

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('/path/to/cert.pem', '/path/to/key.pem')

start_server = websockets.serve(
    handler,
    "0.0.0.0",
    8765,
    ssl=ssl_context
)
```

### Origin Validation

```python
async def handler(websocket, path):
    # Check Origin header
    origin = websocket.request_headers.get('Origin')
    allowed_origins = ['https://example.com', 'https://app.example.com']

    if origin not in allowed_origins:
        await websocket.close(code=4004, reason="Invalid origin")
        return
```

---

## Connection Management

### Heartbeat (Ping/Pong)

**Purpose**: Detect dead connections and keep connections alive through proxies.

```python
# Server: websockets library handles ping/pong automatically
start_server = websockets.serve(
    handler,
    "0.0.0.0",
    8765,
    ping_interval=30,  # Send ping every 30 seconds
    ping_timeout=10    # Close if no pong within 10 seconds
)

# Client: Browser WebSocket API handles pong automatically
# Manual ping/pong for application-level heartbeat:
async def heartbeat(websocket):
    while True:
        await asyncio.sleep(30)
        try:
            await websocket.send(json.dumps({"type": "ping"}))
        except:
            break
```

### Graceful Shutdown

```python
import signal

class WebSocketServer:
    def __init__(self):
        self.server = None
        self.clients = set()

    async def shutdown(self):
        """Gracefully close all connections"""
        print("Shutting down...")

        # Close all client connections
        close_tasks = [
            client.close(code=1001, reason="Server shutting down")
            for client in self.clients
        ]
        await asyncio.gather(*close_tasks, return_exceptions=True)

        # Stop server
        self.server.close()
        await self.server.wait_closed()

    def run(self):
        loop = asyncio.get_event_loop()

        # Handle SIGTERM/SIGINT
        def signal_handler():
            loop.create_task(self.shutdown())

        loop.add_signal_handler(signal.SIGTERM, signal_handler)
        loop.add_signal_handler(signal.SIGINT, signal_handler)

        self.server = loop.run_until_complete(
            websockets.serve(self.handler, "0.0.0.0", 8765)
        )
        loop.run_forever()
```

---

## Anti-Patterns

❌ **Not using sticky sessions**: Clients randomly routed to different backends
✅ Use `ip_hash` (nginx) or `balance source` (HAProxy)

❌ **No heartbeat/ping**: Dead connections stay open, waste resources
✅ Enable `ping_interval` and `ping_timeout`

❌ **No authentication**: Anyone can connect
✅ Verify tokens during handshake or within timeout

❌ **Ignoring Origin header**: CSRF vulnerability
✅ Validate Origin against allowed list

❌ **Synchronous blocking code**: Blocks event loop, kills performance
✅ Use `async`/`await` for all I/O operations

❌ **No message size limit**: Memory exhaustion attack
✅ Set `max_size` parameter

❌ **No rate limiting**: Message flooding
✅ Implement token bucket or connection limits

---

## Level 3: Resources

### Overview

This skill includes comprehensive Level 3 resources for deep WebSocket protocol implementation and production deployment.

**Resources Structure**:
```
websocket-protocols/resources/
├── REFERENCE.md (3,816 lines)       # Complete technical reference
├── scripts/                          # Production tools
│   ├── validate_websocket_config.py # Config validator (842 lines)
│   ├── test_websocket_server.py     # Server tester (949 lines)
│   └── benchmark_websocket.py       # Benchmark tool (734 lines)
└── examples/                         # Production examples
    ├── python/                       # Python WebSocket server
    ├── nodejs/                       # Node.js WebSocket server
    ├── react/                        # React WebSocket client hook
    ├── nginx/                        # nginx configuration
    ├── haproxy/                      # HAProxy configuration
    ├── redis-scaling/                # Redis pub/sub scaling
    ├── docker/                       # Docker Compose cluster
    ├── monitoring/                   # Prometheus monitoring
    └── README.md                     # Examples documentation
```

**Total Lines**: 8,000+ lines of production-ready code, configurations, and documentation

### Quick Start

**1. Validate WebSocket configuration**:
```bash
cd skills/protocols/websocket-protocols/resources/scripts

# Validate nginx config
./validate_websocket_config.py --config /etc/nginx/nginx.conf --type nginx

# Validate HAProxy config
./validate_websocket_config.py --config /etc/haproxy/haproxy.cfg --type haproxy --json
```

**2. Test WebSocket server**:
```bash
# Run all tests
./test_websocket_server.py --url ws://localhost:8080 --test-all

# Test specific functionality
./test_websocket_server.py --url ws://localhost:8080 --test latency --duration 60

# Test with JSON output
./test_websocket_server.py --url wss://example.com/ws --test-all --json
```

**3. Benchmark performance**:
```bash
# Run all benchmarks
./benchmark_websocket.py --url ws://localhost:8080 --benchmark all --connections 1000

# Benchmark throughput
./benchmark_websocket.py --url ws://localhost:8080 --benchmark throughput --duration 60

# Benchmark latency distribution
./benchmark_websocket.py --url ws://localhost:8080 --benchmark latency --connections 50
```

**4. Deploy production cluster**:
```bash
cd ../examples/docker
docker-compose up -d

# Access services
# - WebSocket: ws://localhost/ws
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

**5. Use production examples**:
```bash
cd ../examples/

# Python server with authentication
cd python && python websocket_server.py --host 0.0.0.0 --port 8765

# Node.js server
cd nodejs && npm install ws && node server.js

# Redis-scaled server
cd redis-scaling && python redis_pubsub_server.py --port 8765
```

### REFERENCE.md Contents

The comprehensive reference (3,816 lines) covers:

1. **WebSocket Protocol Fundamentals** - RFC 6455, architecture, when to use
2. **Protocol Handshake** - Upgrade process, headers, subprotocols
3. **Frame Structure** - Binary format, masking, fragmentation
4. **Message Types and Opcodes** - Text, binary, control frames
5. **Connection Lifecycle** - State machine, establishment, shutdown
6. **Python Implementation** - Complete server/client with examples
7. **Node.js Implementation** - Production server patterns
8. **Go Implementation** - Concurrent server architecture
9. **Java Implementation** - Spring WebSocket integration
10. **Client Implementation** - Browser, React hooks, reconnection
11. **Load Balancing** - nginx, HAProxy, AWS ALB configurations
12. **Horizontal Scaling** - Redis pub/sub, message queues
13. **Authentication** - JWT, OAuth, session-based patterns
14. **Security Best Practices** - TLS, origin validation, rate limiting
15. **Heartbeat Monitoring** - Ping/pong, health checks
16. **Error Handling** - Connection errors, retry logic, circuit breakers
17. **Performance Optimization** - Connection pooling, compression, batching
18. **Testing and Debugging** - Tools, unit tests, load testing
19. **Production Deployment** - Docker, Kubernetes, systemd
20. **Monitoring and Observability** - Prometheus metrics, logging
21. **Anti-Patterns** - Common mistakes and solutions
22. **References** - Specifications, libraries, tools

### Scripts Features

**validate_websocket_config.py** (842 lines):
- Validates nginx and HAProxy configurations
- Checks WebSocket upgrade headers
- Verifies sticky session configuration
- Validates TLS/SSL settings
- Checks timeouts and buffering
- Reports security issues
- JSON and text output formats

**test_websocket_server.py** (949 lines):
- Connection establishment testing
- Echo and message handling tests
- JSON and binary message support
- Protocol-level ping/pong testing
- Close handshake verification
- Large message handling
- Rapid message testing
- Latency measurement over time
- Reconnection testing
- Concurrent connection testing
- TLS connection verification
- Comprehensive reporting (JSON/text)

**benchmark_websocket.py** (734 lines):
- Connection scaling benchmarks
- Throughput measurement
- Latency distribution analysis
- Memory usage profiling
- Burst message handling
- Multiple concurrent clients
- Detailed statistics (mean, median, percentiles)
- Resource monitoring
- JSON and text output

### Production Examples

**Python Server** - Complete server with authentication, rate limiting, broadcasting
**Node.js Server** - Production server with heartbeat and error handling
**React Client** - Hook with auto-reconnection, message queue, state management
**nginx Config** - Complete proxy config with TLS, sticky sessions, limits
**HAProxy Config** - Load balancer with WebSocket ACLs, health checks
**Redis Scaling** - Multi-instance server with pub/sub broadcasting
**Docker Cluster** - 3 servers + Redis + nginx + monitoring stack
**Prometheus Monitoring** - Complete metrics collection and visualization

See `examples/README.md` for detailed usage instructions for all examples.

### Use Cases

**Development**:
- Validate configs before deployment
- Test server functionality comprehensively
- Benchmark performance under load
- Learn from production examples

**Operations**:
- Validate production configurations
- Monitor live server health
- Benchmark capacity planning
- Deploy proven architectures

**Troubleshooting**:
- Test connection issues
- Measure latency problems
- Validate configuration changes
- Identify bottlenecks

### Requirements

**Python scripts**:
```bash
pip install websockets aiohttp pyyaml psutil pyjwt redis
```

**Node.js examples**:
```bash
npm install ws
```

**Docker examples**:
```bash
docker-compose version 1.29+
```

**For complete documentation, see REFERENCE.md**

---

**Last Updated**: 2025-10-29
**Format Version**: 1.0 (Atomic)
