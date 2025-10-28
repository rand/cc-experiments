---
name: realtime-websocket-implementation
description: Use WebSocket implementation when you need:
---


# WebSocket Implementation

**Scope**: WebSocket protocol, connection management, reconnection strategies, and heartbeat patterns
**Lines**: 387
**Last Updated**: 2025-10-18

## When to Use This Skill

Use WebSocket implementation when you need:
- **Bidirectional communication**: Full-duplex communication between client and server
- **Low latency**: Sub-100ms message delivery for chat, gaming, or trading applications
- **Server push**: Server needs to push updates without client polling
- **Persistent connections**: Long-lived connections for real-time data streams
- **Binary data**: Efficient transmission of binary protocols (protobuf, MessagePack)

**Don't use** when:
- Unidirectional data flow is sufficient (use Server-Sent Events)
- Client is behind restrictive proxies (WebSocket may be blocked)
- Simple HTTP requests would suffice (REST APIs are simpler)
- Broadcasting to many clients without client->server messages (SSE is lighter)

## Core Concepts

### WebSocket Protocol

```
Client                           Server
  |                                |
  |-- HTTP Upgrade Request ------->|
  |                                |
  |<-- 101 Switching Protocols ----|
  |                                |
  |<====== WebSocket Frames ======>|
  |                                |
  |-- Close Frame ---------------->|
  |<-- Close Frame ----------------|
```

**Key Features**:
- Upgrade from HTTP/1.1 to WebSocket protocol
- Frame-based messaging (text or binary)
- Built-in ping/pong for connection health
- Close handshake for graceful shutdown

### Connection States

```
CONNECTING (0) → Handshake in progress
OPEN (1)       → Connection established, can send/receive
CLOSING (2)    → Close handshake started
CLOSED (3)     → Connection closed or failed
```

### Frame Types

```
- Text frames: UTF-8 encoded strings
- Binary frames: Raw binary data
- Ping/Pong frames: Connection health check
- Close frames: Connection termination
- Continuation frames: Fragmented messages
```

## Patterns

### 1. Basic Client Implementation (Browser)

```typescript
// TypeScript/JavaScript client
class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private heartbeatInterval: number | null = null;
  private messageHandlers: Map<string, (data: any) => void> = new Map();

  constructor(url: string) {
    this.url = url;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.startHeartbeat();
        resolve();
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event.data);
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        this.stopHeartbeat();
        this.handleReconnect();
      };
    });
  }

  private handleMessage(data: string) {
    try {
      const message = JSON.parse(data);
      const handler = this.messageHandlers.get(message.type);
      if (handler) {
        handler(message.data);
      }
    } catch (error) {
      console.error('Failed to parse message:', error);
    }
  }

  on(type: string, handler: (data: any) => void) {
    this.messageHandlers.set(type, handler);
  }

  send(type: string, data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    } else {
      console.error('WebSocket not connected');
    }
  }

  private startHeartbeat() {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // 30 seconds
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval !== null) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      setTimeout(() => this.connect(), delay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  close() {
    this.stopHeartbeat();
    this.ws?.close(1000, 'Client closing');
  }
}

// Usage
const client = new WebSocketClient('wss://api.example.com/ws');
await client.connect();

client.on('message', (data) => {
  console.log('Received:', data);
});

client.send('chat', { text: 'Hello, world!' });
```

### 2. Basic Server Implementation (Node.js)

```typescript
// Using ws library
import { WebSocketServer, WebSocket } from 'ws';
import http from 'http';

interface Client {
  ws: WebSocket;
  id: string;
  rooms: Set<string>;
  lastPing: number;
}

class WebSocketServerManager {
  private wss: WebSocketServer;
  private clients: Map<string, Client> = new Map();
  private rooms: Map<string, Set<string>> = new Map();

  constructor(server: http.Server) {
    this.wss = new WebSocketServer({ server });
    this.initialize();
  }

  private initialize() {
    this.wss.on('connection', (ws, req) => {
      const id = this.generateClientId();
      const client: Client = {
        ws,
        id,
        rooms: new Set(),
        lastPing: Date.now(),
      };

      this.clients.set(id, client);
      console.log(`Client ${id} connected. Total clients: ${this.clients.size}`);

      ws.on('message', (data) => {
        this.handleMessage(client, data.toString());
      });

      ws.on('close', () => {
        this.handleDisconnect(client);
      });

      ws.on('error', (error) => {
        console.error(`Client ${id} error:`, error);
      });

      ws.on('pong', () => {
        client.lastPing = Date.now();
      });

      // Send welcome message
      this.sendToClient(client, 'connected', { id });
    });

    // Start heartbeat check
    this.startHeartbeat();
  }

  private handleMessage(client: Client, data: string) {
    try {
      const message = JSON.parse(data);

      switch (message.type) {
        case 'ping':
          this.sendToClient(client, 'pong', {});
          break;
        case 'join':
          this.joinRoom(client, message.data.room);
          break;
        case 'leave':
          this.leaveRoom(client, message.data.room);
          break;
        case 'broadcast':
          this.broadcast(message.data.room, message.data);
          break;
        default:
          console.log(`Unknown message type: ${message.type}`);
      }
    } catch (error) {
      console.error('Failed to parse message:', error);
    }
  }

  private sendToClient(client: Client, type: string, data: any) {
    if (client.ws.readyState === WebSocket.OPEN) {
      client.ws.send(JSON.stringify({ type, data }));
    }
  }

  private joinRoom(client: Client, room: string) {
    client.rooms.add(room);
    if (!this.rooms.has(room)) {
      this.rooms.set(room, new Set());
    }
    this.rooms.get(room)!.add(client.id);
    console.log(`Client ${client.id} joined room ${room}`);
  }

  private leaveRoom(client: Client, room: string) {
    client.rooms.delete(room);
    this.rooms.get(room)?.delete(client.id);
    console.log(`Client ${client.id} left room ${room}`);
  }

  private broadcast(room: string, data: any) {
    const clientIds = this.rooms.get(room);
    if (!clientIds) return;

    clientIds.forEach((clientId) => {
      const client = this.clients.get(clientId);
      if (client) {
        this.sendToClient(client, 'broadcast', data);
      }
    });
  }

  private handleDisconnect(client: Client) {
    // Remove from all rooms
    client.rooms.forEach((room) => {
      this.rooms.get(room)?.delete(client.id);
    });
    this.clients.delete(client.id);
    console.log(`Client ${client.id} disconnected. Total clients: ${this.clients.size}`);
  }

  private startHeartbeat() {
    setInterval(() => {
      const now = Date.now();
      this.clients.forEach((client) => {
        if (now - client.lastPing > 60000) {
          // No ping in 60 seconds, close connection
          console.log(`Client ${client.id} timeout`);
          client.ws.terminate();
          return;
        }

        if (client.ws.readyState === WebSocket.OPEN) {
          client.ws.ping();
        }
      });
    }, 30000); // Check every 30 seconds
  }

  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Usage
const server = http.createServer();
const wsManager = new WebSocketServerManager(server);
server.listen(8080);
```

### 3. Exponential Backoff Reconnection

```typescript
class ReconnectingWebSocket {
  private url: string;
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;
  private minReconnectDelay = 1000;
  private reconnectDecay = 1.5;
  private shouldReconnect = true;

  constructor(url: string) {
    this.url = url;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);

      const timeout = setTimeout(() => {
        this.ws?.close();
        reject(new Error('Connection timeout'));
      }, 10000);

      this.ws.onopen = () => {
        clearTimeout(timeout);
        this.reconnectAttempts = 0;
        resolve();
      };

      this.ws.onclose = () => {
        clearTimeout(timeout);
        if (this.shouldReconnect) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        clearTimeout(timeout);
        reject(error);
      };
    });
  }

  private scheduleReconnect() {
    const delay = Math.min(
      this.minReconnectDelay * Math.pow(this.reconnectDecay, this.reconnectAttempts),
      this.maxReconnectDelay
    );

    // Add jitter to prevent thundering herd
    const jitter = delay * 0.1 * Math.random();
    const totalDelay = delay + jitter;

    this.reconnectAttempts++;
    console.log(`Reconnecting in ${totalDelay.toFixed(0)}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      if (this.shouldReconnect) {
        this.connect().catch((error) => {
          console.error('Reconnection failed:', error);
        });
      }
    }, totalDelay);
  }

  disconnect() {
    this.shouldReconnect = false;
    this.ws?.close();
  }
}
```

### 4. Authentication and Authorization

```typescript
// Client-side: Send auth token on connection
class AuthenticatedWebSocket {
  private ws: WebSocket | null = null;

  async connect(url: string, token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      // Option 1: Token in URL query parameter
      this.ws = new WebSocket(`${url}?token=${token}`);

      this.ws.onopen = () => {
        // Option 2: Send auth message after connection
        this.ws!.send(JSON.stringify({ type: 'auth', token }));
        resolve();
      };

      this.ws.onerror = reject;
    });
  }
}

// Server-side: Verify token
interface AuthenticatedClient extends Client {
  userId: string;
  authenticated: boolean;
}

class AuthenticatedWebSocketServer {
  private handleConnection(ws: WebSocket, req: http.IncomingMessage) {
    const client: AuthenticatedClient = {
      ws,
      id: this.generateClientId(),
      rooms: new Set(),
      lastPing: Date.now(),
      userId: '',
      authenticated: false,
    };

    // Option 1: Extract token from URL
    const url = new URL(req.url!, `http://${req.headers.host}`);
    const token = url.searchParams.get('token');

    if (token && this.verifyToken(token)) {
      client.authenticated = true;
      client.userId = this.getUserIdFromToken(token);
    }

    // Set authentication timeout
    const authTimeout = setTimeout(() => {
      if (!client.authenticated) {
        ws.close(4001, 'Authentication timeout');
      }
    }, 5000);

    ws.on('message', (data) => {
      const message = JSON.parse(data.toString());

      // Option 2: Handle auth message
      if (message.type === 'auth') {
        if (this.verifyToken(message.token)) {
          client.authenticated = true;
          client.userId = this.getUserIdFromToken(message.token);
          clearTimeout(authTimeout);
          this.sendToClient(client, 'auth_success', { userId: client.userId });
        } else {
          ws.close(4002, 'Invalid token');
        }
        return;
      }

      // Require authentication for other messages
      if (!client.authenticated) {
        ws.close(4003, 'Not authenticated');
        return;
      }

      this.handleMessage(client, message);
    });
  }

  private verifyToken(token: string): boolean {
    // Implement JWT verification or session validation
    return true; // Placeholder
  }

  private getUserIdFromToken(token: string): string {
    // Extract user ID from token
    return 'user_123'; // Placeholder
  }
}
```

## Quick Reference

### Client Connection

```typescript
// Basic connection
const ws = new WebSocket('wss://api.example.com/ws');

// With protocols
const ws = new WebSocket('wss://api.example.com/ws', ['v1.protocol']);

// Check state
ws.readyState // CONNECTING=0, OPEN=1, CLOSING=2, CLOSED=3

// Send data
ws.send('text message');
ws.send(new Uint8Array([1, 2, 3]));
ws.send(JSON.stringify({ type: 'message', data: {} }));
```

### Event Handlers

```typescript
ws.onopen = (event) => { /* Connection opened */ };
ws.onmessage = (event) => { /* Message received: event.data */ };
ws.onerror = (event) => { /* Error occurred */ };
ws.onclose = (event) => { /* Connection closed: event.code, event.reason */ };
```

### Close Codes

```
1000: Normal closure
1001: Going away (page navigation)
1002: Protocol error
1003: Unsupported data
1006: Abnormal closure (no close frame)
1008: Policy violation
1009: Message too big
1011: Server error
4000-4999: Application-specific codes
```

### Server Libraries

```typescript
// Node.js: ws
import { WebSocketServer } from 'ws';

// Node.js: uWebSockets.js (high performance)
import uWS from 'uWebSockets.js';

// Python: websockets
import websockets

// Go: gorilla/websocket
import "github.com/gorilla/websocket"
```

## Anti-Patterns

### ❌ No Reconnection Logic

```typescript
// Wrong: No reconnection handling
const ws = new WebSocket(url);
ws.onclose = () => {
  console.log('Disconnected'); // Connection lost forever
};
```

**Why it's bad**: Network issues, server restarts, or idle timeouts will permanently lose connection

**Better approach**:
```typescript
class WebSocketClient {
  private reconnect() {
    setTimeout(() => this.connect(), this.getBackoffDelay());
  }
}
```

### ❌ No Heartbeat/Keepalive

```typescript
// Wrong: No connection health check
const ws = new WebSocket(url);
// Connection might be dead but readyState still shows OPEN
```

**Why it's bad**: Idle connections can be closed by proxies/load balancers without notification

**Better approach**:
```typescript
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  }
}, 30000);
```

### ❌ Sending Before Connection Open

```typescript
// Wrong: Send immediately
const ws = new WebSocket(url);
ws.send('hello'); // Error: WebSocket is not open
```

**Why it's bad**: Messages sent before connection is established will throw errors

**Better approach**:
```typescript
const ws = new WebSocket(url);
ws.onopen = () => {
  ws.send('hello'); // Safe
};
```

### ❌ No Message Queuing During Reconnection

```typescript
// Wrong: Drop messages during reconnection
send(data: any) {
  if (this.ws?.readyState === WebSocket.OPEN) {
    this.ws.send(data);
  }
  // Message is lost if not connected
}
```

**Why it's bad**: Messages sent during reconnection are silently lost

**Better approach**:
```typescript
private queue: any[] = [];

send(data: any) {
  if (this.ws?.readyState === WebSocket.OPEN) {
    this.ws.send(data);
  } else {
    this.queue.push(data);
  }
}

private flushQueue() {
  while (this.queue.length > 0) {
    this.ws!.send(this.queue.shift()!);
  }
}
```

### ❌ No Error Handling for Invalid Messages

```typescript
// Wrong: Assume all messages are valid JSON
ws.onmessage = (event) => {
  const data = JSON.parse(event.data); // Can throw
  handleMessage(data);
};
```

**Why it's bad**: Malformed messages crash the application

**Better approach**:
```typescript
ws.onmessage = (event) => {
  try {
    const data = JSON.parse(event.data);
    handleMessage(data);
  } catch (error) {
    console.error('Invalid message:', error);
  }
};
```

## Level 3: Resources

### Comprehensive Reference

**Location**: `/Users/rand/src/cc-polymath/skills/realtime/websocket-implementation/resources/REFERENCE.md`

The comprehensive reference (1,900+ lines) covers:
- WebSocket protocol fundamentals (RFC 6455)
- Connection lifecycle (handshake, frames, close)
- Frame structure and opcodes
- Message types (text, binary, ping/pong, close)
- Security considerations (origin validation, authentication, TLS)
- Scaling patterns (sticky sessions, Redis pub/sub, message queues)
- Reconnection strategies with exponential backoff
- Server implementations (Node.js ws, Python websockets, Go gorilla)
- Client implementations (browser, Node.js, Python)
- Testing strategies (unit, integration, load)
- Common patterns (chat, real-time dashboards, multiplayer games)
- Comparison with alternatives (SSE, long polling, HTTP/2)
- Production best practices (monitoring, logging, resource limits)
- Troubleshooting guide
- Performance optimization techniques

### Testing & Analysis Scripts

**Location**: `/Users/rand/src/cc-polymath/skills/realtime/websocket-implementation/resources/scripts/`

**test_websocket.py** - WebSocket testing tool
- Test connectivity, echo, latency, ping/pong
- Support for text and binary messages
- Connection lifecycle testing
- Large message handling
- Reconnection testing
- JSON output for CI/CD integration
- Usage: `./test_websocket.py wss://api.example.com/ws --latency --count 20 --json`

**benchmark_connections.py** - Connection benchmark tool
- Test concurrent connections (100s to 1000s)
- Measure connection establishment time
- Throughput metrics (messages/sec, bytes/sec)
- Gradual ramp-up support
- Duration-based load testing
- Detailed per-connection statistics
- Usage: `./benchmark_connections.py ws://localhost:8080 --connections 1000 --duration 60`

**analyze_traffic.sh** - Traffic analysis tool
- Capture WebSocket traffic with tcpdump
- Analyze with tshark for detailed inspection
- WebSocket handshake detection
- Frame type breakdown (text, binary, ping, pong, close)
- Payload size statistics
- Connection duration analysis
- JSON output for tooling integration
- Usage: `./analyze_traffic.sh --interface eth0 --port 8080 --duration 60 --analyze`

### Production Examples

**Location**: `/Users/rand/src/cc-polymath/skills/realtime/websocket-implementation/resources/examples/`

**Node.js Server** (`node/websocket-server.js`)
- Production-ready WebSocket server using 'ws' library
- Room-based messaging with broadcast support
- Rate limiting and connection metrics
- Ping/pong heartbeat with timeout detection
- Graceful shutdown handling
- Health check and metrics endpoints
- Message routing and validation

**Node.js Client** (`node/websocket-client.js`)
- Robust client with exponential backoff reconnection
- Message queueing during disconnection
- Heartbeat detection with automatic reconnect
- State machine management
- Event-driven architecture
- TypeScript-ready implementation

**Python Server** (`python/websocket_server.py`)
- Async/await server using 'websockets' library
- Room management and broadcasting
- Token bucket rate limiting
- Built-in ping/pong support
- Metrics reporting
- Signal handling for graceful shutdown

**Python Client** (`python/websocket_client.py`)
- Async client with reconnection logic
- Message queueing and batching
- Callback-based event handling
- Heartbeat monitoring
- Connection state tracking

**React Hook** (`react/useWebSocket.tsx`)
- Custom hook for React applications
- Automatic reconnection with state management
- Message queueing during reconnection
- TypeScript support
- Example components (chat room, connection status)
- Optimized for React 18+ patterns

**Docker Deployment** (`docker/`)
- Multi-container setup with docker-compose
- Scalable WebSocket servers with Redis pub/sub
- Nginx load balancer with sticky sessions
- Prometheus + Grafana monitoring
- Health checks and auto-restart
- Production-ready configuration

### Usage Examples

```bash
# Test WebSocket server connectivity and latency
./resources/scripts/test_websocket.py wss://api.example.com/ws --latency --count 10

# Benchmark 1000 concurrent connections
./resources/scripts/benchmark_connections.py ws://localhost:8080 \
  --connections 1000 --duration 60 --ramp-up 30

# Analyze WebSocket traffic
./resources/scripts/analyze_traffic.sh \
  --interface eth0 --port 8080 --duration 300 --analyze

# Run Node.js server
cd resources/examples/node && npm install && node websocket-server.js

# Run Python server
cd resources/examples/python && python websocket_server.py --port 8080

# Deploy with Docker
cd resources/examples/docker && docker-compose up -d
docker-compose scale websocket=3  # Scale to 3 instances
```

## Related Skills

- **server-sent-events.md**: Alternative for unidirectional server-to-client streaming
- **realtime-sync.md**: Conflict resolution and data synchronization over WebSockets
- **pubsub-patterns.md**: Message routing and fan-out patterns for WebSocket servers
- **network-resilience-patterns.md**: Advanced retry, circuit breaker, and timeout patterns

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
