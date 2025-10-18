---
name: realtime-server-sent-events
description: Use Server-Sent Events when you need:
---


# Server-Sent Events (SSE)

**Scope**: SSE protocol, event streams, automatic reconnection, and fallback strategies
**Lines**: 343
**Last Updated**: 2025-10-18

## When to Use This Skill

Use Server-Sent Events when you need:
- **Unidirectional streaming**: Server pushes updates to client only
- **Automatic reconnection**: Built-in browser reconnection with Last-Event-ID
- **Text-based data**: JSON, plain text, or structured event streams
- **HTTP compatibility**: Works through most proxies and firewalls
- **Simple implementation**: Easier than WebSockets for one-way communication

**Don't use** when:
- Bidirectional communication needed (use WebSockets)
- Binary data transmission required (use WebSockets)
- Low latency critical (<100ms, use WebSockets)
- Client needs to send frequent messages to server (use WebSockets)
- IE11 support required without polyfills (use long polling)

## Core Concepts

### SSE Protocol

```
Client                           Server
  |                                |
  |-- GET /events ---------------->|
  |   Accept: text/event-stream    |
  |                                |
  |<-- 200 OK --------------------|
  |   Content-Type: text/event-    |
  |   stream                       |
  |   Cache-Control: no-cache      |
  |                                |
  |<== Event Stream ===============|
  |                                |
  |   data: message 1              |
  |                                |
  |   data: message 2              |
  |                                |
```

**Key Features**:
- Built on HTTP/1.1 (long-lived GET request)
- Text-based protocol (UTF-8 encoded)
- Automatic reconnection with exponential backoff
- Event IDs for resuming from last received event
- Multiple named event types

### Event Format

```
event: message
id: 123
retry: 10000
data: {"text": "Hello"}
data: {"more": "data"}

```

**Fields**:
- `event`: Event type (default: "message")
- `id`: Event identifier for reconnection
- `retry`: Client reconnection time in milliseconds
- `data`: Event payload (can span multiple lines)
- Empty line: Marks end of event

### Connection Lifecycle

```
CONNECTING (0) → Initial connection or reconnecting
OPEN (1)       → Connection established, receiving events
CLOSED (2)     → Connection closed (will not reconnect)
```

## Patterns

### 1. Basic Client Implementation

```typescript
// TypeScript/JavaScript client
class SSEClient {
  private eventSource: EventSource | null = null;
  private url: string;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(url: string) {
    this.url = url;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.eventSource = new EventSource(this.url);

        this.eventSource.onopen = () => {
          console.log('SSE connected');
          this.reconnectAttempts = 0;
          resolve();
        };

        this.eventSource.onerror = (error) => {
          console.error('SSE error:', error);

          if (this.eventSource?.readyState === EventSource.CLOSED) {
            this.handleDisconnect();
          }
        };

        this.eventSource.onmessage = (event) => {
          this.handleEvent('message', event.data);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  on(eventType: string, handler: (data: any) => void) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());

      // Register event listener with EventSource
      if (this.eventSource && eventType !== 'message') {
        this.eventSource.addEventListener(eventType, (event: MessageEvent) => {
          this.handleEvent(eventType, event.data);
        });
      }
    }

    this.listeners.get(eventType)!.add(handler);
  }

  off(eventType: string, handler: (data: any) => void) {
    this.listeners.get(eventType)?.delete(handler);
  }

  private handleEvent(eventType: string, data: string) {
    const handlers = this.listeners.get(eventType);
    if (!handlers) return;

    let parsedData: any;
    try {
      parsedData = JSON.parse(data);
    } catch {
      parsedData = data;
    }

    handlers.forEach((handler) => {
      try {
        handler(parsedData);
      } catch (error) {
        console.error(`Error in ${eventType} handler:`, error);
      }
    });
  }

  private handleDisconnect() {
    this.reconnectAttempts++;

    if (this.reconnectAttempts <= this.maxReconnectAttempts) {
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 30000);
      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

      setTimeout(() => {
        this.connect().catch(console.error);
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  close() {
    this.eventSource?.close();
    this.eventSource = null;
    this.listeners.clear();
  }

  get readyState(): number {
    return this.eventSource?.readyState ?? EventSource.CLOSED;
  }
}

// Usage
const client = new SSEClient('/api/events');
await client.connect();

client.on('message', (data) => {
  console.log('Default message:', data);
});

client.on('notification', (data) => {
  console.log('Notification:', data);
});

client.on('update', (data) => {
  console.log('Update:', data);
});
```

### 2. Server Implementation (Node.js/Express)

```typescript
import express from 'express';
import { Request, Response } from 'express';

interface SSEConnection {
  id: string;
  res: Response;
  lastEventId: number;
}

class SSEServer {
  private connections: Map<string, SSEConnection> = new Map();
  private eventCounter = 0;

  setupRoutes(app: express.Application) {
    app.get('/api/events', (req, res) => {
      this.handleConnection(req, res);
    });
  }

  private handleConnection(req: Request, res: Response) {
    // Set SSE headers
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no'); // Disable nginx buffering

    // Handle CORS if needed
    res.setHeader('Access-Control-Allow-Origin', '*');

    // Get last event ID for reconnection
    const lastEventId = parseInt(req.headers['last-event-id'] as string || '0');

    const connectionId = this.generateConnectionId();
    const connection: SSEConnection = {
      id: connectionId,
      res,
      lastEventId,
    };

    this.connections.set(connectionId, connection);
    console.log(`Client ${connectionId} connected. Total: ${this.connections.size}`);

    // Send initial connection event
    this.sendEvent(connection, {
      event: 'connected',
      data: { connectionId, timestamp: Date.now() },
    });

    // Send missed events if reconnecting
    if (lastEventId > 0) {
      this.sendMissedEvents(connection, lastEventId);
    }

    // Handle client disconnect
    req.on('close', () => {
      this.connections.delete(connectionId);
      console.log(`Client ${connectionId} disconnected. Total: ${this.connections.size}`);
    });

    // Keep connection alive with comments
    const keepAliveInterval = setInterval(() => {
      res.write(': keepalive\n\n');
    }, 30000);

    req.on('close', () => {
      clearInterval(keepAliveInterval);
    });
  }

  private sendEvent(connection: SSEConnection, event: {
    event?: string;
    id?: number;
    data: any;
    retry?: number;
  }) {
    const { res } = connection;
    const { event: eventType = 'message', id, data, retry } = event;

    try {
      if (eventType) {
        res.write(`event: ${eventType}\n`);
      }

      if (id !== undefined) {
        res.write(`id: ${id}\n`);
      }

      if (retry !== undefined) {
        res.write(`retry: ${retry}\n`);
      }

      const jsonData = typeof data === 'string' ? data : JSON.stringify(data);
      const lines = jsonData.split('\n');
      lines.forEach((line) => {
        res.write(`data: ${line}\n`);
      });

      res.write('\n');
    } catch (error) {
      console.error('Error sending event:', error);
      this.connections.delete(connection.id);
    }
  }

  broadcast(event: { event?: string; data: any }) {
    const eventId = ++this.eventCounter;

    this.connections.forEach((connection) => {
      this.sendEvent(connection, {
        ...event,
        id: eventId,
      });
    });
  }

  sendToConnection(connectionId: string, event: { event?: string; data: any }) {
    const connection = this.connections.get(connectionId);
    if (connection) {
      const eventId = ++this.eventCounter;
      this.sendEvent(connection, {
        ...event,
        id: eventId,
      });
    }
  }

  private sendMissedEvents(connection: SSEConnection, lastEventId: number) {
    // In production, retrieve missed events from database or cache
    // For demonstration, we'll send a synthetic event
    this.sendEvent(connection, {
      event: 'catchup',
      data: { message: 'Caught up from event ' + lastEventId },
    });
  }

  private generateConnectionId(): string {
    return `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Usage
const app = express();
const sseServer = new SSEServer();
sseServer.setupRoutes(app);

// Broadcast to all clients
setInterval(() => {
  sseServer.broadcast({
    event: 'time',
    data: { timestamp: Date.now() },
  });
}, 5000);

app.listen(3000);
```

### 3. Authentication with SSE

```typescript
// Client: Send auth token via query parameter or custom header
class AuthenticatedSSEClient extends SSEClient {
  constructor(url: string, token: string) {
    // Option 1: Token in query parameter
    const authenticatedUrl = `${url}?token=${encodeURIComponent(token)}`;
    super(authenticatedUrl);
  }
}

// Server: Validate token before establishing connection
class AuthenticatedSSEServer extends SSEServer {
  setupRoutes(app: express.Application) {
    app.get('/api/events', this.authenticate, (req, res) => {
      this.handleConnection(req, res);
    });
  }

  private authenticate(req: Request, res: Response, next: express.NextFunction) {
    const token = req.query.token as string || req.headers.authorization?.split(' ')[1];

    if (!token) {
      res.status(401).json({ error: 'Missing token' });
      return;
    }

    if (!verifyToken(token)) {
      res.status(403).json({ error: 'Invalid token' });
      return;
    }

    // Attach user info to request
    (req as any).userId = getUserIdFromToken(token);
    next();
  }
}
```

### 4. Fallback Pattern (Polyfill for Older Browsers)

```typescript
// Polyfill using long polling for browsers without EventSource
class EventSourcePolyfill {
  private url: string;
  private listeners: Map<string, (event: MessageEvent) => void> = new Map();
  private abortController: AbortController | null = null;
  public readyState: number = 0;
  public onopen: (() => void) | null = null;
  public onerror: ((error: any) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    this.connect();
  }

  private async connect() {
    this.readyState = 0; // CONNECTING
    this.abortController = new AbortController();

    try {
      const response = await fetch(this.url, {
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      this.readyState = 1; // OPEN
      this.onopen?.();

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        events.forEach((eventStr) => {
          this.parseAndDispatchEvent(eventStr);
        });
      }
    } catch (error) {
      this.readyState = 2; // CLOSED
      this.onerror?.(error);
    }
  }

  private parseAndDispatchEvent(eventStr: string) {
    const lines = eventStr.split('\n');
    let eventType = 'message';
    let data = '';

    lines.forEach((line) => {
      if (line.startsWith('event:')) {
        eventType = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        data += line.substring(5).trim() + '\n';
      }
    });

    const event = new MessageEvent(eventType, { data: data.trim() });

    if (eventType === 'message' && this.onmessage) {
      this.onmessage(event);
    }

    const listener = this.listeners.get(eventType);
    listener?.(event);
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners.set(type, listener);
  }

  close() {
    this.abortController?.abort();
    this.readyState = 2; // CLOSED
  }
}

// Use native or polyfill
const EventSourceImpl = typeof EventSource !== 'undefined' ? EventSource : EventSourcePolyfill;
const eventSource = new EventSourceImpl('/api/events');
```

## Quick Reference

### Client API

```typescript
// Create connection
const eventSource = new EventSource('/api/events');

// Listen to events
eventSource.onmessage = (event) => { /* Default message */ };
eventSource.addEventListener('custom', (event) => { /* Named event */ });

// Connection state
eventSource.onopen = () => { /* Connected */ };
eventSource.onerror = (error) => { /* Error or disconnect */ };

// Check state
eventSource.readyState // CONNECTING=0, OPEN=1, CLOSED=2

// Close connection
eventSource.close();
```

### Server Response Format

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: message
id: 1
data: {"text": "Hello"}

event: notification
id: 2
data: {"title": "New message"}

```

### Event Fields

```
event: <event-name>    // Optional, default: "message"
id: <event-id>         // Optional, for reconnection
retry: <milliseconds>  // Optional, reconnection delay
data: <payload>        // Required, can be multi-line
```

## Anti-Patterns

### ❌ No Cache-Control Headers

```typescript
// Wrong: Missing cache headers
app.get('/events', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  // Missing Cache-Control header
});
```

**Why it's bad**: Proxies and CDNs may cache the event stream

**Better approach**:
```typescript
res.setHeader('Cache-Control', 'no-cache');
res.setHeader('X-Accel-Buffering', 'no'); // Nginx
```

### ❌ Not Handling Reconnection

```typescript
// Wrong: No last-event-id handling
app.get('/events', (req, res) => {
  // Start sending all events from beginning
});
```

**Why it's bad**: Client receives duplicate events after reconnection

**Better approach**:
```typescript
const lastEventId = parseInt(req.headers['last-event-id'] as string || '0');
sendMissedEvents(res, lastEventId);
```

### ❌ Buffering Issues

```typescript
// Wrong: Large data without flushing
res.write(`data: ${largeObject}\n\n`);
// May be buffered by Node.js or proxy
```

**Why it's bad**: Events may be delayed or batched

**Better approach**:
```typescript
res.write(`data: ${data}\n\n`);
res.flush?.(); // Flush immediately if available
```

### ❌ No Keep-Alive Comments

```typescript
// Wrong: No keepalive mechanism
app.get('/events', (req, res) => {
  // Connection may timeout after idle period
});
```

**Why it's bad**: Proxies may close idle connections

**Better approach**:
```typescript
setInterval(() => {
  res.write(': keepalive\n\n');
}, 30000);
```

## Related Skills

- **websocket-implementation.md**: Alternative for bidirectional communication
- **realtime-sync.md**: Data synchronization patterns for SSE streams
- **pubsub-patterns.md**: Server-side message routing for SSE broadcasts
- **network-resilience-patterns.md**: Error handling and retry strategies

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
