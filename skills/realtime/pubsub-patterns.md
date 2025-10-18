---
name: realtime-pubsub-patterns
description: Use pub/sub patterns when you need:
---


# Pub/Sub Patterns

**Scope**: Publish/subscribe architecture, Redis Pub/Sub, message queues, and fan-out patterns
**Lines**: 372
**Last Updated**: 2025-10-18

## When to Use This Skill

Use pub/sub patterns when you need:
- **Decoupled communication**: Publishers don't know about subscribers
- **Broadcasting**: Send messages to multiple consumers simultaneously
- **Event-driven architecture**: React to events across distributed systems
- **Real-time notifications**: Push updates to multiple clients (chat, notifications)
- **Scalability**: Add/remove subscribers without affecting publishers

**Don't use** when:
- Point-to-point communication sufficient (use direct messaging)
- Message ordering critical across topics (use message queue with ordering)
- Request-response pattern needed (use RPC or REST)
- Single consumer per message (use work queue)

## Core Concepts

### Pub/Sub Architecture

```
Publisher                    Pub/Sub Broker                Subscribers
   |                              |                              |
   |-- Publish(topic, msg) ------>|                              |
   |                              |-- topic:A ------------------->| Sub-1
   |                              |-- topic:A ------------------->| Sub-2
   |                              |-- topic:B ------------------->| Sub-3
   |                              |                              |
```

**Key Properties**:
- Publishers and subscribers are decoupled
- Many-to-many communication
- Topics/channels for message routing
- No message persistence (fire-and-forget)
- Real-time delivery (push-based)

### Pub/Sub vs Message Queue

```
Pub/Sub:
- One message → Many consumers
- No persistence (usually)
- Real-time delivery
- Example: Redis Pub/Sub, MQTT

Message Queue:
- One message → One consumer
- Persistent messages
- At-least-once delivery
- Example: RabbitMQ, SQS, Kafka
```

### Common Patterns

```
1. Fan-Out: One publisher → Multiple subscribers
2. Topic-Based: Route by topic/channel name
3. Pattern-Based: Subscribe to pattern (e.g., "user.*")
4. Request-Reply: Pub/sub with response channel
5. Priority: Different topics for different priorities
```

## Patterns

### 1. Basic Redis Pub/Sub (Node.js)

```typescript
import Redis from 'ioredis';

// Publisher
class Publisher {
  private redis: Redis;

  constructor() {
    this.redis = new Redis({
      host: 'localhost',
      port: 6379,
    });
  }

  async publish(channel: string, message: any): Promise<number> {
    const payload = JSON.stringify(message);
    const subscribers = await this.redis.publish(channel, payload);
    console.log(`Published to ${channel}: ${subscribers} subscribers received`);
    return subscribers;
  }

  disconnect() {
    this.redis.disconnect();
  }
}

// Subscriber
class Subscriber {
  private redis: Redis;
  private handlers: Map<string, Set<(message: any) => void>> = new Map();

  constructor() {
    this.redis = new Redis({
      host: 'localhost',
      port: 6379,
    });

    this.redis.on('message', (channel, message) => {
      this.handleMessage(channel, message);
    });
  }

  subscribe(channel: string, handler: (message: any) => void) {
    if (!this.handlers.has(channel)) {
      this.handlers.set(channel, new Set());
      this.redis.subscribe(channel);
      console.log(`Subscribed to ${channel}`);
    }
    this.handlers.get(channel)!.add(handler);
  }

  unsubscribe(channel: string, handler?: (message: any) => void) {
    if (!this.handlers.has(channel)) return;

    if (handler) {
      this.handlers.get(channel)!.delete(handler);
    }

    if (!handler || this.handlers.get(channel)!.size === 0) {
      this.handlers.delete(channel);
      this.redis.unsubscribe(channel);
      console.log(`Unsubscribed from ${channel}`);
    }
  }

  private handleMessage(channel: string, message: string) {
    const handlers = this.handlers.get(channel);
    if (!handlers) return;

    let parsedMessage: any;
    try {
      parsedMessage = JSON.parse(message);
    } catch {
      parsedMessage = message;
    }

    handlers.forEach((handler) => {
      try {
        handler(parsedMessage);
      } catch (error) {
        console.error(`Error in handler for ${channel}:`, error);
      }
    });
  }

  disconnect() {
    this.redis.disconnect();
  }
}

// Usage
const publisher = new Publisher();
const subscriber = new Subscriber();

subscriber.subscribe('notifications', (message) => {
  console.log('Notification received:', message);
});

subscriber.subscribe('chat:room1', (message) => {
  console.log('Chat message:', message);
});

await publisher.publish('notifications', {
  type: 'alert',
  text: 'System maintenance in 5 minutes',
});

await publisher.publish('chat:room1', {
  user: 'alice',
  text: 'Hello, world!',
});
```

### 2. Pattern-Based Subscription

```typescript
// Pattern subscriber using Redis PSUBSCRIBE
class PatternSubscriber {
  private redis: Redis;
  private handlers: Map<string, Set<(channel: string, message: any) => void>> = new Map();

  constructor() {
    this.redis = new Redis();

    this.redis.on('pmessage', (pattern, channel, message) => {
      this.handlePatternMessage(pattern, channel, message);
    });
  }

  psubscribe(pattern: string, handler: (channel: string, message: any) => void) {
    if (!this.handlers.has(pattern)) {
      this.handlers.set(pattern, new Set());
      this.redis.psubscribe(pattern);
      console.log(`Pattern subscribed: ${pattern}`);
    }
    this.handlers.get(pattern)!.add(handler);
  }

  punsubscribe(pattern: string, handler?: (channel: string, message: any) => void) {
    if (!this.handlers.has(pattern)) return;

    if (handler) {
      this.handlers.get(pattern)!.delete(handler);
    }

    if (!handler || this.handlers.get(pattern)!.size === 0) {
      this.handlers.delete(pattern);
      this.redis.punsubscribe(pattern);
      console.log(`Pattern unsubscribed: ${pattern}`);
    }
  }

  private handlePatternMessage(pattern: string, channel: string, message: string) {
    const handlers = this.handlers.get(pattern);
    if (!handlers) return;

    let parsedMessage: any;
    try {
      parsedMessage = JSON.parse(message);
    } catch {
      parsedMessage = message;
    }

    handlers.forEach((handler) => {
      try {
        handler(channel, parsedMessage);
      } catch (error) {
        console.error(`Error in pattern handler for ${pattern}:`, error);
      }
    });
  }
}

// Usage
const patternSub = new PatternSubscriber();

// Subscribe to all chat rooms
patternSub.psubscribe('chat:*', (channel, message) => {
  console.log(`Message in ${channel}:`, message);
});

// Subscribe to all user events
patternSub.psubscribe('user:*:*', (channel, message) => {
  console.log(`User event in ${channel}:`, message);
});
```

### 3. Pub/Sub with WebSocket Bridge

```typescript
import { WebSocketServer, WebSocket } from 'ws';
import Redis from 'ioredis';

interface Client {
  ws: WebSocket;
  id: string;
  subscriptions: Set<string>;
}

class PubSubWebSocketBridge {
  private wss: WebSocketServer;
  private publisher: Redis;
  private subscriber: Redis;
  private clients: Map<string, Client> = new Map();

  constructor(wsPort: number) {
    this.wss = new WebSocketServer({ port: wsPort });
    this.publisher = new Redis();
    this.subscriber = new Redis();

    this.subscriber.on('message', (channel, message) => {
      this.broadcastToChannel(channel, message);
    });

    this.setupWebSocket();
  }

  private setupWebSocket() {
    this.wss.on('connection', (ws) => {
      const client: Client = {
        ws,
        id: this.generateClientId(),
        subscriptions: new Set(),
      };

      this.clients.set(client.id, client);
      console.log(`Client ${client.id} connected`);

      ws.on('message', (data) => {
        this.handleClientMessage(client, data.toString());
      });

      ws.on('close', () => {
        this.handleClientDisconnect(client);
      });
    });
  }

  private handleClientMessage(client: Client, data: string) {
    try {
      const message = JSON.parse(data);

      switch (message.type) {
        case 'subscribe':
          this.handleSubscribe(client, message.channel);
          break;
        case 'unsubscribe':
          this.handleUnsubscribe(client, message.channel);
          break;
        case 'publish':
          this.handlePublish(message.channel, message.data);
          break;
      }
    } catch (error) {
      console.error('Invalid message from client:', error);
    }
  }

  private async handleSubscribe(client: Client, channel: string) {
    if (client.subscriptions.has(channel)) return;

    client.subscriptions.add(channel);

    // Subscribe to Redis channel if first subscriber
    const channelClients = this.getChannelClients(channel);
    if (channelClients.length === 1) {
      await this.subscriber.subscribe(channel);
      console.log(`Subscribed to Redis channel: ${channel}`);
    }

    console.log(`Client ${client.id} subscribed to ${channel}`);
  }

  private async handleUnsubscribe(client: Client, channel: string) {
    if (!client.subscriptions.has(channel)) return;

    client.subscriptions.delete(channel);

    // Unsubscribe from Redis if no more subscribers
    const channelClients = this.getChannelClients(channel);
    if (channelClients.length === 0) {
      await this.subscriber.unsubscribe(channel);
      console.log(`Unsubscribed from Redis channel: ${channel}`);
    }

    console.log(`Client ${client.id} unsubscribed from ${channel}`);
  }

  private async handlePublish(channel: string, data: any) {
    const message = JSON.stringify(data);
    await this.publisher.publish(channel, message);
  }

  private broadcastToChannel(channel: string, message: string) {
    const clients = this.getChannelClients(channel);
    const payload = JSON.stringify({
      type: 'message',
      channel,
      data: JSON.parse(message),
    });

    clients.forEach((client) => {
      if (client.ws.readyState === WebSocket.OPEN) {
        client.ws.send(payload);
      }
    });
  }

  private getChannelClients(channel: string): Client[] {
    return Array.from(this.clients.values()).filter((client) =>
      client.subscriptions.has(channel)
    );
  }

  private async handleClientDisconnect(client: Client) {
    // Unsubscribe from all channels
    for (const channel of client.subscriptions) {
      client.subscriptions.delete(channel);
      const channelClients = this.getChannelClients(channel);
      if (channelClients.length === 0) {
        await this.subscriber.unsubscribe(channel);
      }
    }

    this.clients.delete(client.id);
    console.log(`Client ${client.id} disconnected`);
  }

  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Usage
const bridge = new PubSubWebSocketBridge(8080);

// Clients connect via WebSocket and send:
// {"type": "subscribe", "channel": "notifications"}
// {"type": "publish", "channel": "notifications", "data": {"text": "Hello"}}
```

### 4. Request-Reply Pattern

```typescript
// Request-Reply using pub/sub with correlation IDs
class RequestReplyClient {
  private redis: Redis;
  private subscriber: Redis;
  private clientId: string;
  private replyChannel: string;
  private pendingRequests: Map<string, {
    resolve: (response: any) => void;
    reject: (error: Error) => void;
    timeout: NodeJS.Timeout;
  }> = new Map();

  constructor() {
    this.redis = new Redis();
    this.subscriber = new Redis();
    this.clientId = this.generateClientId();
    this.replyChannel = `reply:${this.clientId}`;

    this.subscriber.subscribe(this.replyChannel);
    this.subscriber.on('message', (channel, message) => {
      if (channel === this.replyChannel) {
        this.handleReply(message);
      }
    });
  }

  async request(channel: string, data: any, timeoutMs: number = 5000): Promise<any> {
    const correlationId = this.generateCorrelationId();

    const promise = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(correlationId);
        reject(new Error('Request timeout'));
      }, timeoutMs);

      this.pendingRequests.set(correlationId, { resolve, reject, timeout });
    });

    const request = {
      correlationId,
      replyTo: this.replyChannel,
      data,
    };

    await this.redis.publish(channel, JSON.stringify(request));
    return promise;
  }

  private handleReply(message: string) {
    try {
      const reply = JSON.parse(message);
      const pending = this.pendingRequests.get(reply.correlationId);

      if (pending) {
        clearTimeout(pending.timeout);
        this.pendingRequests.delete(reply.correlationId);

        if (reply.error) {
          pending.reject(new Error(reply.error));
        } else {
          pending.resolve(reply.data);
        }
      }
    } catch (error) {
      console.error('Error handling reply:', error);
    }
  }

  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateCorrelationId(): string {
    return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Request-Reply Server
class RequestReplyServer {
  private redis: Redis;
  private subscriber: Redis;
  private handlers: Map<string, (data: any) => Promise<any>> = new Map();

  constructor() {
    this.redis = new Redis();
    this.subscriber = new Redis();

    this.subscriber.on('message', (channel, message) => {
      this.handleRequest(channel, message);
    });
  }

  handle(channel: string, handler: (data: any) => Promise<any>) {
    this.handlers.set(channel, handler);
    this.subscriber.subscribe(channel);
    console.log(`Handling requests on ${channel}`);
  }

  private async handleRequest(channel: string, message: string) {
    const handler = this.handlers.get(channel);
    if (!handler) return;

    try {
      const request = JSON.parse(message);
      const result = await handler(request.data);

      const reply = {
        correlationId: request.correlationId,
        data: result,
      };

      await this.redis.publish(request.replyTo, JSON.stringify(reply));
    } catch (error) {
      const request = JSON.parse(message);
      const reply = {
        correlationId: request.correlationId,
        error: error instanceof Error ? error.message : 'Unknown error',
      };

      await this.redis.publish(request.replyTo, JSON.stringify(reply));
    }
  }
}

// Usage
const server = new RequestReplyServer();
server.handle('calculate', async (data) => {
  return { result: data.a + data.b };
});

const client = new RequestReplyClient();
const response = await client.request('calculate', { a: 5, b: 3 });
console.log(response); // { result: 8 }
```

## Quick Reference

### Redis Pub/Sub Commands

```typescript
// Publish
await redis.publish(channel, message); // Returns number of subscribers

// Subscribe
await redis.subscribe(channel1, channel2, ...);
redis.on('message', (channel, message) => { /* Handle */ });

// Pattern subscribe
await redis.psubscribe('pattern:*');
redis.on('pmessage', (pattern, channel, message) => { /* Handle */ });

// Unsubscribe
await redis.unsubscribe(channel);
await redis.punsubscribe(pattern);
```

### Message Format Best Practices

```typescript
// Include metadata
const message = {
  timestamp: Date.now(),
  type: 'notification',
  source: 'user-service',
  data: { /* payload */ },
};

// Use correlation IDs for tracking
const message = {
  correlationId: 'abc-123',
  data: { /* payload */ },
};
```

### Channel Naming Conventions

```
user:123:notifications   // User-specific notifications
chat:room:456            // Chat room messages
events:order:created     // Domain events
system:alerts            // System-wide alerts
```

## Anti-Patterns

### ❌ Using Pub/Sub for Guaranteed Delivery

```typescript
// Wrong: Pub/sub doesn't guarantee delivery
await redis.publish('orders', JSON.stringify(order));
// If no subscribers connected, message is lost
```

**Why it's bad**: Messages are lost if no subscribers are active

**Better approach**:
```typescript
// Use message queue (Redis Streams, RabbitMQ) for guaranteed delivery
await redis.xadd('orders', '*', 'order', JSON.stringify(order));
```

### ❌ Large Message Payloads

```typescript
// Wrong: Publishing large data
await redis.publish('channel', JSON.stringify(largeObject)); // Multiple MB
```

**Why it's bad**: Blocks Redis, consumes bandwidth, slows all subscribers

**Better approach**:
```typescript
// Store data separately, publish reference
const id = await redis.set('data:123', JSON.stringify(largeObject));
await redis.publish('channel', JSON.stringify({ type: 'data_ready', id }));
```

### ❌ No Error Handling in Subscribers

```typescript
// Wrong: Unhandled errors crash subscriber
redis.on('message', (channel, message) => {
  const data = JSON.parse(message); // Can throw
  processData(data); // Can throw
});
```

**Why it's bad**: One bad message crashes the entire subscriber

**Better approach**:
```typescript
redis.on('message', (channel, message) => {
  try {
    const data = JSON.parse(message);
    processData(data);
  } catch (error) {
    console.error('Error processing message:', error);
  }
});
```

### ❌ Synchronous Processing in Subscribers

```typescript
// Wrong: Blocking subscriber
redis.on('message', (channel, message) => {
  expensiveOperation(message); // Blocks event loop
});
```

**Why it's bad**: Slow processing delays other messages

**Better approach**:
```typescript
redis.on('message', async (channel, message) => {
  setImmediate(async () => {
    await expensiveOperation(message);
  });
});
```

## Related Skills

- **websocket-implementation.md**: WebSocket bridge for pub/sub to browsers
- **server-sent-events.md**: SSE for unidirectional pub/sub to clients
- **realtime-sync.md**: Synchronization patterns using pub/sub
- **network-resilience-patterns.md**: Handling failures in pub/sub systems

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
