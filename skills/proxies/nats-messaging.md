---
name: proxies-nats-messaging
description: NATS messaging patterns including pub/sub, request-reply, queue groups, JetStream persistence, clustering, and high-performance messaging
---

# NATS Messaging

**Scope**: NATS pub/sub, request-reply, JetStream, clustering, streaming
**Lines**: ~400
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building microservices communication
- Implementing pub/sub messaging
- Setting up request-reply patterns
- Working with distributed systems
- Implementing event streaming
- Building real-time applications
- Setting up message persistence with JetStream
- Implementing load balancing with queue groups

## Core Concepts

### NATS Architecture

```
Publisher → NATS Server → Subscriber(s)
            [Subject-based routing]
            [At-most-once delivery by default]
            [Optional JetStream for persistence]
```

**Core Features**:
- **Subjects**: Hierarchical message routing (e.g., `orders.created.us-west`)
- **Pub/Sub**: One-to-many messaging
- **Request/Reply**: Synchronous RPC pattern
- **Queue Groups**: Load balancing across subscribers
- **JetStream**: Persistent streaming, exactly-once delivery

### Subject Hierarchies

```
orders.*              # Match orders.created, orders.updated
orders.>              # Match orders.created, orders.created.v2, etc.
orders.created.*      # Match orders.created.us, orders.created.eu
```

---

## Patterns

### Pattern 1: Basic Pub/Sub

**Use Case**: Event broadcasting to multiple services

```python
# ❌ Bad: Direct service-to-service HTTP
# Service A calls Service B, C, D directly
requests.post('http://service-b/webhook', json=event)
requests.post('http://service-c/webhook', json=event)
requests.post('http://service-d/webhook', json=event)
```

```python
# ✅ Good: Publish event, services subscribe
import asyncio
from nats.aio.client import Client as NATS

async def publish_order_created():
    nc = NATS()
    await nc.connect("nats://localhost:4222")

    # Publish order created event
    order = {"id": 123, "total": 99.99, "status": "created"}
    await nc.publish("orders.created", json.dumps(order).encode())

    await nc.close()

async def subscribe_order_created():
    nc = NATS()
    await nc.connect("nats://localhost:4222")

    async def message_handler(msg):
        order = json.loads(msg.data.decode())
        print(f"Received order: {order['id']}")
        # Process order...

    # Subscribe to orders.created
    await nc.subscribe("orders.created", cb=message_handler)

    # Keep connection alive
    await asyncio.sleep(3600)

# Publisher
asyncio.run(publish_order_created())

# Subscriber (multiple services can subscribe)
asyncio.run(subscribe_order_created())
```

**Benefits**:
- Decoupled services
- Easy to add new subscribers
- No direct service dependencies
- Built-in load balancing

### Pattern 2: Request/Reply (RPC)

**Use Case**: Synchronous request-response pattern

```python
import asyncio
from nats.aio.client import Client as NATS

# Server: Handles requests
async def handle_requests():
    nc = NATS()
    await nc.connect("nats://localhost:4222")

    async def request_handler(msg):
        # Parse request
        request = json.loads(msg.data.decode())
        user_id = request.get('user_id')

        # Process request
        user = get_user_from_db(user_id)

        # Send reply
        response = json.dumps(user).encode()
        await nc.publish(msg.reply, response)

    # Subscribe to requests
    await nc.subscribe("user.get", cb=request_handler)
    await asyncio.sleep(3600)

# Client: Makes request
async def make_request():
    nc = NATS()
    await nc.connect("nats://localhost:4222")

    # Send request and wait for reply
    request = json.dumps({"user_id": 123}).encode()
    response = await nc.request("user.get", request, timeout=2.0)

    user = json.loads(response.data.decode())
    print(f"User: {user}")

    await nc.close()

# Run server
asyncio.run(handle_requests())

# Run client
asyncio.run(make_request())
```

### Pattern 3: Queue Groups (Load Balancing)

**Use Case**: Distribute work across multiple workers

```python
async def worker(worker_id: int):
    nc = NATS()
    await nc.connect("nats://localhost:4222")

    async def process_job(msg):
        job = json.loads(msg.data.decode())
        print(f"Worker {worker_id} processing job {job['id']}")
        # Process job...
        await asyncio.sleep(1)  # Simulate work

    # All workers join "workers" queue group
    # NATS distributes messages across the group
    await nc.subscribe("jobs.process", queue="workers", cb=process_job)

    await asyncio.sleep(3600)

# Start multiple workers
async def start_workers():
    await asyncio.gather(
        worker(1),
        worker(2),
        worker(3)
    )

asyncio.run(start_workers())

# Publisher
async def publish_jobs():
    nc = NATS()
    await nc.connect("nats://localhost:4222")

    for job_id in range(10):
        job = json.dumps({"id": job_id, "task": "process"}).encode()
        await nc.publish("jobs.process", job)
        print(f"Published job {job_id}")

    await nc.close()

asyncio.run(publish_jobs())
```

---

## JetStream (Persistent Streaming)

### Creating Streams

```python
import asyncio
from nats.aio.client import Client as NATS

async def create_stream():
    nc = NATS()
    await nc.connect("nats://localhost:4222")

    js = nc.jetstream()

    # Create stream for orders
    await js.add_stream(
        name="ORDERS",
        subjects=["orders.*"],
        retention="limits",  # or "interest", "workqueue"
        max_msgs=1000000,
        max_bytes=1024 * 1024 * 1024,  # 1GB
        max_age=7 * 24 * 60 * 60,  # 7 days in seconds
        storage="file",  # or "memory"
        num_replicas=3  # For clustering
    )

    await nc.close()

asyncio.run(create_stream())
```

### Publishing to JetStream

```python
async def publish_to_stream():
    nc = NATS()
    await nc.connect("nats://localhost:4222")

    js = nc.jetstream()

    # Publish with ack
    order = {"id": 123, "total": 99.99}
    ack = await js.publish("orders.created", json.dumps(order).encode())

    print(f"Published to stream: {ack.stream}, seq: {ack.seq}")

    await nc.close()
```

### Consuming from JetStream

```python
async def consume_from_stream():
    nc = NATS()
    await nc.connect("nats://localhost:4222")

    js = nc.jetstream()

    # Create durable consumer
    await js.add_consumer(
        stream="ORDERS",
        durable_name="orders-processor",
        deliver_policy="all",  # or "new", "last", "by_start_sequence", "by_start_time"
        ack_policy="explicit",  # or "none", "all"
        max_deliver=3,  # Max redelivery attempts
        ack_wait=30,  # Ack timeout in seconds
        max_ack_pending=100
    )

    # Subscribe to consumer
    psub = await js.pull_subscribe("orders.*", "orders-processor")

    while True:
        try:
            msgs = await psub.fetch(batch=10, timeout=5)
            for msg in msgs:
                order = json.loads(msg.data.decode())
                print(f"Processing order: {order['id']}")

                # Process order...

                # Acknowledge message
                await msg.ack()
        except asyncio.TimeoutError:
            pass

asyncio.run(consume_from_stream())
```

---

## Go Implementation

### Basic Pub/Sub

```go
package main

import (
    "encoding/json"
    "fmt"
    "log"
    "time"

    "github.com/nats-io/nats.go"
)

type Order struct {
    ID     int     `json:"id"`
    Total  float64 `json:"total"`
    Status string  `json:"status"`
}

func main() {
    // Connect to NATS
    nc, err := nats.Connect(nats.DefaultURL)
    if err != nil {
        log.Fatal(err)
    }
    defer nc.Close()

    // Subscribe
    nc.Subscribe("orders.created", func(msg *nats.Msg) {
        var order Order
        json.Unmarshal(msg.Data, &order)
        fmt.Printf("Received order: %d\n", order.ID)
    })

    // Publish
    order := Order{ID: 123, Total: 99.99, Status: "created"}
    data, _ := json.Marshal(order)
    nc.Publish("orders.created", data)

    time.Sleep(time.Second)
}
```

### Request/Reply

```go
func requestReply() {
    nc, _ := nats.Connect(nats.DefaultURL)
    defer nc.Close()

    // Server side
    nc.Subscribe("user.get", func(msg *nats.Msg) {
        // Parse request
        var req struct {
            UserID int `json:"user_id"`
        }
        json.Unmarshal(msg.Data, &req)

        // Process and reply
        user := getUserFromDB(req.UserID)
        data, _ := json.Marshal(user)
        msg.Respond(data)
    })

    // Client side
    req := `{"user_id": 123}`
    msg, err := nc.Request("user.get", []byte(req), 2*time.Second)
    if err != nil {
        log.Fatal(err)
    }

    var user User
    json.Unmarshal(msg.Data, &user)
    fmt.Printf("User: %v\n", user)
}
```

### JetStream with Go

```go
import (
    "github.com/nats-io/nats.go"
)

func jetStreamExample() {
    nc, _ := nats.Connect(nats.DefaultURL)
    defer nc.Close()

    js, _ := nc.JetStream()

    // Create stream
    js.AddStream(&nats.StreamConfig{
        Name:     "ORDERS",
        Subjects: []string{"orders.*"},
        MaxAge:   7 * 24 * time.Hour,
        Storage:  nats.FileStorage,
        Replicas: 3,
    })

    // Publish
    order := Order{ID: 123, Total: 99.99}
    data, _ := json.Marshal(order)
    ack, err := js.Publish("orders.created", data)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Published to stream %s, seq %d\n", ack.Stream, ack.Sequence)

    // Create consumer
    js.AddConsumer("ORDERS", &nats.ConsumerConfig{
        Durable:   "orders-processor",
        AckPolicy: nats.AckExplicitPolicy,
        MaxDeliver: 3,
        AckWait:   30 * time.Second,
    })

    // Subscribe
    sub, _ := js.PullSubscribe("orders.*", "orders-processor")

    for {
        msgs, err := sub.Fetch(10, nats.MaxWait(5*time.Second))
        if err != nil {
            continue
        }

        for _, msg := range msgs {
            var order Order
            json.Unmarshal(msg.Data, &order)
            fmt.Printf("Processing order: %d\n", order.ID)

            // Acknowledge
            msg.Ack()
        }
    }
}
```

---

## Clustering and High Availability

### Cluster Configuration

```conf
# nats-server.conf
port: 4222
cluster {
  name: nats-cluster
  listen: 0.0.0.0:6222
  routes: [
    nats://nats-1:6222
    nats://nats-2:6222
    nats://nats-3:6222
  ]
}

jetstream {
  store_dir: /data/nats/jetstream
  max_memory_store: 1GB
  max_file_store: 10GB
}
```

### Client Connection Options

```python
async def connect_with_options():
    nc = NATS()

    # Multiple servers for failover
    await nc.connect(
        servers=[
            "nats://nats-1:4222",
            "nats://nats-2:4222",
            "nats://nats-3:4222"
        ],
        # Reconnect options
        reconnect_time_wait=2,
        max_reconnect_attempts=10,
        # TLS
        tls="path/to/cert.pem",
        # Authentication
        user="nats-user",
        password="secret"
    )

    # Connection callbacks
    async def disconnected_cb():
        print("Disconnected from NATS")

    async def reconnected_cb():
        print("Reconnected to NATS")

    async def error_cb(e):
        print(f"Error: {e}")

    nc.disconnected_cb = disconnected_cb
    nc.reconnected_cb = reconnected_cb
    nc.error_cb = error_cb
```

---

## Advanced Patterns

### Message Deduplication

```python
async def publish_with_dedup():
    nc = NATS()
    await nc.connect("nats://localhost:4222")
    js = nc.jetstream()

    # Publish with message ID for deduplication
    order = {"id": 123, "total": 99.99}
    await js.publish(
        "orders.created",
        json.dumps(order).encode(),
        headers={"Nats-Msg-Id": f"order-{order['id']}"}
    )

    # Duplicate publish will be ignored within dedup window
    await js.publish(
        "orders.created",
        json.dumps(order).encode(),
        headers={"Nats-Msg-Id": f"order-{order['id']}"}
    )

    await nc.close()
```

### Key-Value Store

```python
async def kv_store():
    nc = NATS()
    await nc.connect("nats://localhost:4222")
    js = nc.jetstream()

    # Create KV bucket
    kv = await js.create_key_value(bucket="config", history=5, ttl=3600)

    # Put values
    await kv.put("api.timeout", b"30")
    await kv.put("api.retries", b"3")

    # Get value
    entry = await kv.get("api.timeout")
    print(f"Timeout: {entry.value.decode()}")

    # Watch for changes
    watcher = await kv.watch("api.*")
    async for entry in watcher:
        print(f"Key {entry.key} changed to {entry.value.decode()}")

    await nc.close()
```

### Object Store

```python
async def object_store():
    nc = NATS()
    await nc.connect("nats://localhost:4222")
    js = nc.jetstream()

    # Create object store
    obs = await js.create_object_store(bucket="files")

    # Put object
    with open("large_file.bin", "rb") as f:
        await obs.put("large_file.bin", f)

    # Get object
    result = await obs.get("large_file.bin")
    with open("downloaded_file.bin", "wb") as f:
        f.write(result.data)

    # List objects
    async for info in obs.list():
        print(f"Object: {info.name}, Size: {info.size}")

    await nc.close()
```

---

## Monitoring and Observability

### Server Monitoring

```bash
# HTTP monitoring endpoint
curl http://localhost:8222/varz     # Server info
curl http://localhost:8222/connz    # Connection info
curl http://localhost:8222/routez   # Route info
curl http://localhost:8222/subsz    # Subscription info
```

### Metrics Collection

```python
from prometheus_client import Counter, Histogram

messages_published = Counter('nats_messages_published_total', 'Messages published')
messages_received = Counter('nats_messages_received_total', 'Messages received')
publish_latency = Histogram('nats_publish_latency_seconds', 'Publish latency')

@publish_latency.time()
async def publish_with_metrics(subject: str, data: bytes):
    await nc.publish(subject, data)
    messages_published.inc()

async def subscribe_with_metrics(subject: str):
    async def handler(msg):
        messages_received.inc()
        # Process message...

    await nc.subscribe(subject, cb=handler)
```

---

## Best Practices

### 1. Use Subject Hierarchies

```python
# ✅ Good: Hierarchical subjects
"orders.created.us-west"
"orders.updated.eu-central"
"users.login.mobile"

# ❌ Bad: Flat subjects
"order_created"
"order_updated"
```

### 2. Handle Reconnections

```python
async def robust_subscriber():
    nc = NATS()

    async def reconnected_cb():
        print("Reconnected, resubscribing...")
        await setup_subscriptions(nc)

    await nc.connect(
        servers=["nats://nats-1:4222", "nats://nats-2:4222"],
        reconnected_cb=reconnected_cb,
        max_reconnect_attempts=-1  # Infinite reconnects
    )
```

### 3. Use Queue Groups for Scalability

```python
# Multiple workers automatically load balance
await nc.subscribe("jobs.process", queue="workers", cb=handler)
```

---

## Troubleshooting

### Issue 1: Messages Not Received

**Debug Steps**:
```python
# Check connection
print(f"Connected: {nc.is_connected}")
print(f"Reconnecting: {nc.is_reconnecting}")

# Verify subscription
print(f"Active subscriptions: {len(nc._subs)}")

# Enable debug logging
nc.options['verbose'] = True
```

### Issue 2: JetStream Not Available

**Solution**:
```bash
# Enable JetStream in server config
cat << EOF > nats-server.conf
jetstream {
  store_dir: /data/nats/jetstream
  max_memory_store: 1GB
  max_file_store: 10GB
}
EOF

# Start with JetStream enabled
nats-server -c nats-server.conf
```

---

## Related Skills

- `distributed-systems-messaging-patterns` - Messaging patterns
- `observability-distributed-tracing` - Distributed tracing
- `containers-kubernetes` - K8s deployment
- `protocols-grpc` - gRPC with NATS
- `realtime-websockets` - WebSocket integration

---

**Last Updated**: 2025-10-27
