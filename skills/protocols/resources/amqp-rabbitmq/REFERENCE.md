# AMQP 0-9-1 and RabbitMQ - Comprehensive Reference

## Table of Contents

1. [Protocol Fundamentals](#protocol-fundamentals)
2. [RabbitMQ Architecture](#rabbitmq-architecture)
3. [AMQP Model](#amqp-model)
4. [Exchange Types](#exchange-types)
5. [Queue Patterns](#queue-patterns)
6. [Message Properties](#message-properties)
7. [Durability and Persistence](#durability-and-persistence)
8. [Acknowledgments and Delivery Guarantees](#acknowledgments-and-delivery-guarantees)
9. [Flow Control](#flow-control)
10. [Clustering](#clustering)
11. [High Availability](#high-availability)
12. [Federation and Shovel](#federation-and-shovel)
13. [Dead Letter Exchanges](#dead-letter-exchanges)
14. [TTL and Expiry](#ttl-and-expiry)
15. [Priority Queues](#priority-queues)
16. [Performance Tuning](#performance-tuning)
17. [Monitoring and Observability](#monitoring-and-observability)
18. [Security](#security)
19. [Client Libraries](#client-libraries)
20. [Common Patterns](#common-patterns)
21. [Anti-Patterns](#anti-patterns)
22. [Troubleshooting](#troubleshooting)
23. [Production Best Practices](#production-best-practices)

---

## Protocol Fundamentals

### AMQP 0-9-1 Overview

**AMQP** (Advanced Message Queuing Protocol) is an open standard application layer protocol for message-oriented middleware. AMQP 0-9-1 is the protocol version implemented by RabbitMQ.

**Key Characteristics**:
- **Binary protocol**: Efficient wire format with minimal overhead
- **Message broker model**: Centralized routing and queuing
- **Platform agnostic**: Language and platform independent
- **Reliable**: Built-in acknowledgments and delivery guarantees
- **Flexible routing**: Multiple exchange types for various patterns
- **Interoperable**: Standardized protocol across implementations

**Protocol Layers**:
```
┌─────────────────────────────────┐
│   Application Layer             │
│   (Business logic)              │
├─────────────────────────────────┤
│   AMQP 0-9-1 Protocol           │
│   (Frames, methods, content)    │
├─────────────────────────────────┤
│   TCP                           │
│   (Reliable transport)          │
├─────────────────────────────────┤
│   IP                            │
│   (Network routing)             │
└─────────────────────────────────┘
```

### AMQP vs Other Protocols

**AMQP vs HTTP**:
- AMQP: Persistent connections, bidirectional, push model, message queuing
- HTTP: Request-response, stateless, pull model, no built-in queuing

**AMQP vs MQTT**:
- AMQP: Rich routing, flexible exchanges, enterprise features, heavier
- MQTT: Lightweight, simple pub-sub, IoT focused, resource constrained devices

**AMQP vs Kafka**:
- AMQP: Message broker, flexible routing, low latency, queue-based
- Kafka: Event log, append-only, high throughput, partition-based

### Connection Model

**Hierarchical structure**:
```
Connection (TCP)
  ├── Channel 1 (Virtual connection)
  │   ├── Consumer 1
  │   └── Consumer 2
  ├── Channel 2
  │   └── Publisher 1
  └── Channel 3
      └── Consumer 3
```

**Connection**: TCP connection to broker (heavyweight, resource intensive)
**Channel**: Lightweight virtual connection sharing TCP connection (efficient, low overhead)

**Best practice**: Use one connection per process, multiple channels per connection.

### Frame Types

AMQP communication uses typed frames:

1. **Method frames**: Carry RPC commands (declare queue, publish, consume)
2. **Content header frames**: Carry message properties
3. **Body frames**: Carry message payload
4. **Heartbeat frames**: Keep-alive mechanism

**Message transmission**:
```
Method frame (basic.publish)
  ↓
Content header frame (properties)
  ↓
Body frame (payload chunk 1)
  ↓
Body frame (payload chunk 2)
  ↓
...
```

### Virtual Hosts

**Virtual hosts** (vhosts) provide logical isolation within a single broker.

**Characteristics**:
- Separate namespaces for exchanges, queues, bindings
- Isolated permissions
- Separate resource limits
- Independent monitoring

**Use cases**:
- Multi-tenant systems
- Environment separation (dev, staging, prod)
- Application isolation

**Example**:
```bash
# Create vhost
rabbitmqctl add_vhost myapp_production

# Set permissions
rabbitmqctl set_permissions -p myapp_production myuser ".*" ".*" ".*"

# Connection URL
amqp://myuser:password@localhost:5672/myapp_production
```

---

## RabbitMQ Architecture

### Core Components

**Broker**: RabbitMQ server process managing exchanges, queues, bindings.

**Components**:
```
┌───────────────────────────────────────┐
│           RabbitMQ Broker             │
│  ┌─────────────────────────────────┐  │
│  │      Virtual Host               │  │
│  │  ┌───────────┐  ┌────────────┐ │  │
│  │  │ Exchange  │  │  Exchange  │ │  │
│  │  └─────┬─────┘  └─────┬──────┘ │  │
│  │        │ Bindings     │        │  │
│  │        ▼              ▼        │  │
│  │  ┌─────────┐    ┌─────────┐   │  │
│  │  │  Queue  │    │  Queue  │   │  │
│  │  └────┬────┘    └────┬────┘   │  │
│  └───────┼──────────────┼────────┘  │
│          │              │           │
└──────────┼──────────────┼───────────┘
           │              │
      Consumer         Consumer
```

### Exchanges

**Exchanges** receive messages from publishers and route to queues based on bindings.

**Properties**:
- **Name**: Unique identifier within vhost
- **Type**: Routing algorithm (direct, fanout, topic, headers)
- **Durability**: Survives broker restart if durable
- **Auto-delete**: Deleted when last binding removed
- **Internal**: Can only receive messages from other exchanges

**Default exchange**:
- Empty string name (`""`)
- Direct exchange
- Every queue automatically bound with routing key = queue name
- Used when exchange parameter omitted

**Built-in exchanges**:
```
amq.direct    - Direct exchange
amq.fanout    - Fanout exchange
amq.topic     - Topic exchange
amq.headers   - Headers exchange
amq.match     - Headers exchange (deprecated)
```

### Queues

**Queues** store messages until consumed.

**Properties**:
- **Name**: Unique identifier (empty string for server-generated name)
- **Durability**: Survives broker restart if durable
- **Exclusive**: Used by only one connection, deleted when connection closes
- **Auto-delete**: Deleted when last consumer unsubscribes
- **Arguments**: Queue-specific settings (TTL, max length, DLX, etc.)

**Queue types**:
1. **Classic queue**: Traditional queue implementation
2. **Quorum queue**: Replicated, Raft-based, highly available
3. **Stream**: Append-only log, persistent, replayable

**Queue lifecycle**:
```
Declare → Bind → Publish → Consume → Ack → Empty → Delete
    ↓                                           ↓
  Durable?                                 Auto-delete?
    Yes ↓                                       Yes ↓
  Persisted                                   Deleted
```

### Bindings

**Bindings** connect exchanges to queues with routing rules.

**Components**:
- **Exchange**: Source exchange
- **Queue**: Destination queue
- **Routing key**: Pattern for message matching
- **Arguments**: Type-specific matching criteria

**Example**:
```python
# Bind queue to exchange with routing key
channel.queue_bind(
    exchange='logs',
    queue='error_logs',
    routing_key='error'
)

# Multiple bindings for same queue
channel.queue_bind(exchange='logs', queue='all_logs', routing_key='info')
channel.queue_bind(exchange='logs', queue='all_logs', routing_key='warn')
channel.queue_bind(exchange='logs', queue='all_logs', routing_key='error')
```

### Routing

**Message routing flow**:
```
1. Publisher → Exchange
   - Message has routing key
   - Exchange type determines routing algorithm

2. Exchange → Queue (based on bindings)
   - Direct: Exact routing key match
   - Fanout: All bound queues
   - Topic: Pattern match
   - Headers: Header attribute match

3. Queue → Consumer
   - Round-robin among consumers (default)
   - Fair dispatch with prefetch
```

**Routing scenarios**:

**No matching queue**:
- Message dropped (unless mandatory flag set)
- Publisher can request notification

**Multiple matching queues**:
- Message copied to each queue
- Each queue delivers to its consumers

**No consumers**:
- Messages accumulate in queue
- Queue memory/disk limits apply

---

## AMQP Model

### Publishers

**Publisher** sends messages to exchanges.

**Responsibilities**:
- Open connection and channel
- Declare exchanges (if needed)
- Publish messages with routing keys
- Handle confirmations (if enabled)
- Handle connection failures

**Publishing options**:
```python
channel.basic_publish(
    exchange='logs',              # Exchange name (or '' for default)
    routing_key='info',           # Routing key
    body='Log message',           # Message payload
    properties=pika.BasicProperties(
        delivery_mode=2,          # 1=non-persistent, 2=persistent
        content_type='text/plain',
        content_encoding='utf-8',
        headers={'source': 'app'},
        correlation_id='123',
        reply_to='response_queue',
        expiration='60000',       # TTL in milliseconds
        message_id='msg-001',
        timestamp=1234567890,
        type='log',
        user_id='app',
        app_id='myapp',
        priority=5
    ),
    mandatory=False               # Return message if unroutable
)
```

### Consumers

**Consumer** receives messages from queues.

**Responsibilities**:
- Open connection and channel
- Declare queues (if needed)
- Subscribe to queues
- Process messages
- Acknowledge or reject messages
- Handle redeliveries

**Consuming modes**:

**1. Push (basic.consume)**:
```python
def callback(ch, method, properties, body):
    process(body)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(
    queue='tasks',
    on_message_callback=callback,
    auto_ack=False,
    exclusive=False,
    consumer_tag='consumer-1'
)
channel.start_consuming()
```

**2. Pull (basic.get)**:
```python
method, properties, body = channel.basic_get(queue='tasks', auto_ack=False)
if method:
    process(body)
    channel.basic_ack(method.delivery_tag)
else:
    print("No messages")
```

**Best practice**: Use push (basic.consume) for continuous processing. Use pull (basic.get) for single-message retrieval.

### Message Lifecycle

**Complete message flow**:
```
1. Publisher creates message
2. Publisher sends to exchange
3. Exchange routes to queue(s) based on bindings
4. Queue stores message
5. Queue delivers to consumer
6. Consumer processes message
7. Consumer acknowledges
8. Queue removes message

Alternative paths:
- No route → Message returned or dropped
- Consumer reject + requeue → Back to step 4
- Consumer reject + no requeue → Dead letter or discard
- TTL expires → Dead letter or discard
- Queue full → Message rejected or dropped
```

### Connection Lifecycle

**Connection establishment**:
```
1. TCP connection established
2. Protocol header exchange
3. AMQP connection.start
4. SASL authentication
5. connection.tune (negotiate parameters)
6. connection.open (select vhost)
7. Channel opened
8. Ready for operations
```

**Connection termination**:
```
Graceful:
1. channel.close
2. connection.close
3. TCP connection closed

Ungraceful:
- Network failure
- Timeout
- Server shutdown
- Client crash

Recovery:
- Auto-reconnect (client library)
- Redelivery of unacked messages
- Reestablish topology
```

---

## Exchange Types

### Direct Exchange

Routes messages to queues where routing key exactly matches binding key.

**Routing algorithm**:
```
if message.routing_key == binding.routing_key:
    deliver_to_queue()
```

**Use cases**:
- Task distribution to specific workers
- Command routing to specific handlers
- Targeted notifications

**Example topology**:
```python
# Declare exchange
channel.exchange_declare(exchange='tasks', exchange_type='direct', durable=True)

# Declare queues
channel.queue_declare(queue='email_tasks', durable=True)
channel.queue_declare(queue='sms_tasks', durable=True)
channel.queue_declare(queue='push_tasks', durable=True)

# Bind queues
channel.queue_bind(exchange='tasks', queue='email_tasks', routing_key='email')
channel.queue_bind(exchange='tasks', queue='sms_tasks', routing_key='sms')
channel.queue_bind(exchange='tasks', queue='push_tasks', routing_key='push')

# Publish
channel.basic_publish(exchange='tasks', routing_key='email', body='Send email')
# → Routed to email_tasks queue only
```

**Multiple bindings**:
A queue can bind with multiple routing keys:
```python
channel.queue_bind(exchange='logs', queue='important', routing_key='error')
channel.queue_bind(exchange='logs', queue='important', routing_key='critical')
# Queue receives messages with routing_key='error' OR routing_key='critical'
```

### Fanout Exchange

Routes messages to all bound queues (ignores routing key).

**Routing algorithm**:
```
for queue in bound_queues:
    deliver_to_queue()
```

**Use cases**:
- Broadcasting events
- Cache invalidation
- Real-time updates to all subscribers
- Logging to multiple destinations

**Example topology**:
```python
# Declare exchange
channel.exchange_declare(exchange='broadcast', exchange_type='fanout', durable=True)

# Declare queues
channel.queue_declare(queue='service_a', durable=True)
channel.queue_declare(queue='service_b', durable=True)
channel.queue_declare(queue='service_c', durable=True)

# Bind queues (routing key ignored for fanout)
channel.queue_bind(exchange='broadcast', queue='service_a')
channel.queue_bind(exchange='broadcast', queue='service_b')
channel.queue_bind(exchange='broadcast', queue='service_c')

# Publish
channel.basic_publish(exchange='broadcast', routing_key='', body='Event')
# → Routed to all three queues
```

**Performance note**: Fanout is the fastest exchange type (no routing logic).

### Topic Exchange

Routes messages based on wildcard pattern matching of routing keys.

**Routing algorithm**:
```
routing_key = "order.created.us"
binding_pattern = "order.*.us"

if pattern_matches(binding_pattern, routing_key):
    deliver_to_queue()
```

**Wildcards**:
- `*` matches exactly one word
- `#` matches zero or more words
- Words separated by `.`

**Use cases**:
- Multi-criteria subscriptions
- Log aggregation with filtering
- Event routing by category
- Geographic routing

**Example routing**:
```python
# Declare exchange
channel.exchange_declare(exchange='events', exchange_type='topic', durable=True)

# Bindings
channel.queue_bind(exchange='events', queue='all_orders', routing_key='order.#')
channel.queue_bind(exchange='events', queue='us_orders', routing_key='order.*.us')
channel.queue_bind(exchange='events', queue='created_events', routing_key='*.created.*')
channel.queue_bind(exchange='events', queue='critical', routing_key='*.*.critical')

# Publishing examples:
# routing_key='order.created.us'
#   → Matches: all_orders, us_orders, created_events

# routing_key='order.updated.eu'
#   → Matches: all_orders

# routing_key='user.created.us'
#   → Matches: created_events

# routing_key='order.cancelled.us.critical'
#   → Matches: none (too many words for patterns)
```

**Pattern examples**:
```
Routing key: "quick.orange.rabbit"

Pattern: "*" → No match (needs at least one word)
Pattern: "#" → Match (zero or more words)
Pattern: "quick.#" → Match
Pattern: "*.orange.*" → Match
Pattern: "*.*.rabbit" → Match
Pattern: "quick.orange.#" → Match
Pattern: "lazy.#" → No match
Pattern: "*.*.*.fox" → No match (fox not present)
```

**Special cases**:
- Pattern `#` matches all messages (like fanout)
- Pattern without wildcards matches exact key (like direct)

### Headers Exchange

Routes messages based on header attributes instead of routing key.

**Routing algorithm**:
```
if all_headers_match(binding_headers, message_headers):  # x-match=all
    deliver_to_queue()
elif any_header_matches(binding_headers, message_headers):  # x-match=any
    deliver_to_queue()
```

**Use cases**:
- Complex routing logic
- Multiple attribute matching
- Non-string routing criteria
- Legacy system integration

**Example topology**:
```python
# Declare exchange
channel.exchange_declare(exchange='jobs', exchange_type='headers', durable=True)

# Bindings with header matching
channel.queue_bind(
    exchange='jobs',
    queue='video_jobs',
    arguments={
        'x-match': 'all',        # Match all headers
        'type': 'video',
        'priority': 'high'
    }
)

channel.queue_bind(
    exchange='jobs',
    queue='any_high_priority',
    arguments={
        'x-match': 'any',        # Match any header
        'priority': 'high',
        'urgent': True
    }
)

# Publish with headers
channel.basic_publish(
    exchange='jobs',
    routing_key='',              # Ignored for headers exchange
    body='Process video',
    properties=pika.BasicProperties(
        headers={
            'type': 'video',
            'priority': 'high',
            'format': 'mp4'
        }
    )
)
# → Routed to video_jobs (matches all: type AND priority)
# → Routed to any_high_priority (matches any: priority)
```

**x-match values**:
- `all`: All binding headers must match message headers
- `any`: At least one binding header must match

**Performance note**: Headers exchange is slower than other types (requires header parsing).

### Exchange-to-Exchange Bindings

Exchanges can bind to other exchanges for complex routing.

**Use cases**:
- Multi-stage routing
- Aggregation from multiple sources
- Logical grouping

**Example**:
```python
# Declare exchanges
channel.exchange_declare(exchange='all_logs', exchange_type='topic')
channel.exchange_declare(exchange='error_logs', exchange_type='direct')
channel.exchange_declare(exchange='audit_logs', exchange_type='direct')

# Bind exchanges
channel.exchange_bind(
    destination='error_logs',
    source='all_logs',
    routing_key='*.error'
)

channel.exchange_bind(
    destination='audit_logs',
    source='all_logs',
    routing_key='audit.*'
)

# Now publishing to 'all_logs' routes through to specific exchanges
```

---

## Queue Patterns

### Work Queue (Task Queue)

**Pattern**: Distribute time-consuming tasks among multiple workers.

**Characteristics**:
- One queue
- Multiple competing consumers
- Round-robin distribution by default
- Fair dispatch with prefetch_count

**Implementation**:
```python
# Producer
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Durable queue
channel.queue_declare(queue='tasks', durable=True)

# Publish tasks
for i in range(100):
    message = f'Task {i}'
    channel.basic_publish(
        exchange='',
        routing_key='tasks',
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # Persistent
        )
    )
print("Published 100 tasks")

# Consumer (run multiple instances)
import time

def callback(ch, method, properties, body):
    print(f"Processing: {body}")
    time.sleep(5)  # Simulate work
    print(f"Done: {body}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)  # Fair dispatch
channel.basic_consume(queue='tasks', on_message_callback=callback)
print("Waiting for tasks...")
channel.start_consuming()
```

**Key settings**:
- `durable=True`: Queue survives broker restart
- `delivery_mode=2`: Messages persist to disk
- `auto_ack=False`: Manual acknowledgment after processing
- `prefetch_count=1`: Only one unacked message per worker

### Publish-Subscribe

**Pattern**: Send message to multiple consumers.

**Characteristics**:
- Fanout exchange
- One temporary queue per subscriber
- Each subscriber gets copy of every message

**Implementation**:
```python
# Publisher
channel.exchange_declare(exchange='logs', exchange_type='fanout', durable=True)

message = 'Important event'
channel.basic_publish(exchange='logs', routing_key='', body=message)

# Subscriber (run multiple instances)
# Create exclusive queue (auto-delete on disconnect)
result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue

# Bind to exchange
channel.queue_bind(exchange='logs', queue=queue_name)

def callback(ch, method, properties, body):
    print(f"Received: {body}")

channel.basic_consume(
    queue=queue_name,
    on_message_callback=callback,
    auto_ack=True  # OK for fanout since no retry needed
)
print("Waiting for logs...")
channel.start_consuming()
```

**Queue options**:
- `exclusive=True`: Queue deleted when connection closes
- `auto_delete=True`: Queue deleted when last consumer unsubscribes
- Server-generated name (`queue=''`): Unique queue per subscriber

### Routing

**Pattern**: Subscribe to subset of messages.

**Characteristics**:
- Direct or topic exchange
- Selective bindings based on criteria
- Multiple bindings per queue possible

**Implementation (Direct)**:
```python
# Publisher
channel.exchange_declare(exchange='logs', exchange_type='direct', durable=True)

severity = 'error'  # info, warning, error
message = 'Database connection failed'
channel.basic_publish(exchange='logs', routing_key=severity, body=message)

# Consumer (selective)
import sys

severities = sys.argv[1:]  # e.g., ['error', 'warning']
if not severities:
    print("Usage: consumer.py [info] [warning] [error]")
    sys.exit(1)

result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue

# Bind for each severity
for severity in severities:
    channel.queue_bind(exchange='logs', queue=queue_name, routing_key=severity)

channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
channel.start_consuming()
```

**Implementation (Topic)**:
```python
# Publisher
channel.exchange_declare(exchange='events', exchange_type='topic', durable=True)

routing_key = 'user.signup.us'  # <resource>.<action>.<region>
channel.basic_publish(exchange='events', routing_key=routing_key, body=data)

# Consumer (pattern-based)
import sys

binding_keys = sys.argv[1:]  # e.g., ['user.*.*', '*.signup.*']

result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue

for binding_key in binding_keys:
    channel.queue_bind(exchange='events', queue=queue_name, routing_key=binding_key)

channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
channel.start_consuming()
```

### RPC (Request-Reply)

**Pattern**: Remote procedure call over message broker.

**Characteristics**:
- Request queue (persistent)
- Reply queue (temporary, per client)
- Correlation ID to match requests/responses
- reply_to header specifies response destination

**Implementation**:
```python
# Client
import uuid
import pika

class RpcClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost')
        )
        self.channel = self.connection.channel()

        # Declare callback queue for responses
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        # Consume from callback queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True
        )

        self.response = None
        self.corr_id = None

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())

        self.channel.basic_publish(
            exchange='',
            routing_key='rpc_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=str(n)
        )

        # Wait for response
        while self.response is None:
            self.connection.process_data_events()

        return int(self.response)

# Server
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def on_request(ch, method, props, body):
    n = int(body)
    print(f"Computing fib({n})")

    response = fibonacci(n)

    ch.basic_publish(
        exchange='',
        routing_key=props.reply_to,
        properties=pika.BasicProperties(
            correlation_id=props.correlation_id
        ),
        body=str(response)
    )

    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.queue_declare(queue='rpc_queue', durable=True)
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='rpc_queue', on_message_callback=on_request)
print("RPC server waiting for requests...")
channel.start_consuming()
```

**Key concepts**:
- **Correlation ID**: UUID matching request to response
- **reply_to**: Queue name for response delivery
- **Exclusive queue**: Temporary callback queue per client
- **Timeout handling**: Client should timeout if no response

### Priority Queue

**Pattern**: Process high-priority messages first.

**Implementation**:
```python
# Declare priority queue
channel.queue_declare(
    queue='tasks',
    durable=True,
    arguments={
        'x-max-priority': 10  # Priority range 0-10
    }
)

# Publish with priority
channel.basic_publish(
    exchange='',
    routing_key='tasks',
    body='High priority task',
    properties=pika.BasicProperties(
        delivery_mode=2,
        priority=9  # 0 (lowest) to 10 (highest)
    )
)

channel.basic_publish(
    exchange='',
    routing_key='tasks',
    body='Low priority task',
    properties=pika.BasicProperties(
        delivery_mode=2,
        priority=1
    )
)

# Consumer processes high priority first
```

**Performance note**: Priority queues have overhead. Use only when needed.

---

## Message Properties

### Standard Properties

AMQP defines standard message properties:

```python
properties = pika.BasicProperties(
    # Delivery
    delivery_mode=2,              # 1=non-persistent, 2=persistent
    priority=5,                   # 0-255 (if priority queue)

    # Content
    content_type='application/json',
    content_encoding='utf-8',

    # Application
    headers={'x-custom': 'value'},
    correlation_id='req-123',     # Match request/response
    reply_to='response_queue',    # Reply queue name
    message_id='msg-001',         # Application message ID

    # Metadata
    timestamp=1234567890,         # Unix timestamp
    type='order.created',         # Message type
    user_id='app_user',           # Authenticated user
    app_id='order-service',       # Publishing application

    # Expiration
    expiration='60000'            # TTL in milliseconds (string)
)
```

### Delivery Mode

**Non-persistent (1)**:
- Faster (no disk writes)
- Lost on broker restart
- Use for non-critical data

**Persistent (2)**:
- Slower (disk writes)
- Survives broker restart
- Use for important data

**Example**:
```python
# Non-persistent (fast)
channel.basic_publish(
    exchange='',
    routing_key='logs',
    body='Log entry',
    properties=pika.BasicProperties(delivery_mode=1)
)

# Persistent (durable)
channel.basic_publish(
    exchange='',
    routing_key='orders',
    body='Order data',
    properties=pika.BasicProperties(delivery_mode=2)
)
```

### Content Type

Standard MIME types:

```python
# JSON
properties = pika.BasicProperties(
    content_type='application/json',
    content_encoding='utf-8'
)
channel.basic_publish(exchange='', routing_key='q', body='{"key": "value"}', properties=properties)

# Binary
properties = pika.BasicProperties(content_type='application/octet-stream')
channel.basic_publish(exchange='', routing_key='q', body=binary_data, properties=properties)

# Text
properties = pika.BasicProperties(content_type='text/plain', content_encoding='utf-8')
channel.basic_publish(exchange='', routing_key='q', body='Plain text', properties=properties)
```

### Headers

Custom application headers:

```python
properties = pika.BasicProperties(
    headers={
        'x-source': 'order-service',
        'x-version': '2.0',
        'x-trace-id': 'abc-123',
        'x-retry-count': 0
    }
)

# Consumer accesses headers
def callback(ch, method, properties, body):
    headers = properties.headers or {}
    trace_id = headers.get('x-trace-id')
    print(f"Trace ID: {trace_id}")
```

### Correlation ID and Reply To

For request-response patterns:

```python
# Request
import uuid
corr_id = str(uuid.uuid4())

channel.basic_publish(
    exchange='',
    routing_key='rpc_queue',
    properties=pika.BasicProperties(
        reply_to='response_queue',
        correlation_id=corr_id
    ),
    body='request data'
)

# Response
def on_request(ch, method, props, body):
    # Process request
    response = process(body)

    # Send response
    ch.basic_publish(
        exchange='',
        routing_key=props.reply_to,
        properties=pika.BasicProperties(
            correlation_id=props.correlation_id
        ),
        body=response
    )
```

### Message ID

Unique identifier for deduplication:

```python
import uuid

message_id = str(uuid.uuid4())

channel.basic_publish(
    exchange='',
    routing_key='tasks',
    body='task data',
    properties=pika.BasicProperties(message_id=message_id)
)

# Consumer deduplicates
seen_ids = set()

def callback(ch, method, properties, body):
    msg_id = properties.message_id
    if msg_id in seen_ids:
        print("Duplicate message, skipping")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    seen_ids.add(msg_id)
    process(body)
    ch.basic_ack(delivery_tag=method.delivery_tag)
```

---

## Durability and Persistence

### Queue Durability

**Durable queue**: Survives broker restart (metadata persisted).

```python
# Durable
channel.queue_declare(queue='important', durable=True)

# Non-durable (deleted on restart)
channel.queue_declare(queue='temporary', durable=False)
```

**Important**: Durable queue doesn't make messages persistent. Both queue AND messages must be durable.

### Message Persistence

**Persistent message**: Content written to disk.

```python
channel.basic_publish(
    exchange='',
    routing_key='important',
    body='Critical data',
    properties=pika.BasicProperties(
        delivery_mode=2  # Persistent
    )
)
```

**Persistence guarantees**:
- Message survives broker restart
- NOT 100% guaranteed (timing window before fsync)
- For stronger guarantees, use publisher confirms

### Exchange Durability

**Durable exchange**: Metadata survives broker restart.

```python
# Durable
channel.exchange_declare(exchange='events', exchange_type='topic', durable=True)

# Non-durable
channel.exchange_declare(exchange='temp', exchange_type='fanout', durable=False)
```

### Binding Durability

**Bindings are durable if**:
- Exchange is durable
- Queue is durable
- Binding is to durable exchange and queue

```python
# Durable binding
channel.exchange_declare(exchange='logs', exchange_type='direct', durable=True)
channel.queue_declare(queue='error_logs', durable=True)
channel.queue_bind(exchange='logs', queue='error_logs', routing_key='error')
# Binding persists across restarts
```

### Publisher Confirms

**Ensure messages written to disk before considering them sent.**

**Enable confirms**:
```python
channel.confirm_delivery()
```

**Synchronous confirms**:
```python
try:
    channel.basic_publish(
        exchange='',
        routing_key='important',
        body='data',
        properties=pika.BasicProperties(delivery_mode=2),
        mandatory=True
    )
    print("Message confirmed")
except pika.exceptions.UnroutableError:
    print("Message could not be routed")
except pika.exceptions.NackError:
    print("Message nacked by broker")
```

**Asynchronous confirms** (better performance):
```python
import pika

class PublisherConfirms:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        self.channel.confirm_delivery()
        self.acks = 0
        self.nacks = 0
        self.deliveries = {}

    def on_delivery_confirmation(self, method_frame):
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()
        delivery_tag = method_frame.method.delivery_tag

        if confirmation_type == 'ack':
            self.acks += 1
        elif confirmation_type == 'nack':
            self.nacks += 1

        del self.deliveries[delivery_tag]
        print(f"Confirmed: {delivery_tag} ({confirmation_type})")

    def publish(self, exchange, routing_key, body):
        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        self.deliveries[len(self.deliveries)] = body
```

### Lazy Queues

**Lazy queues** keep messages on disk instead of RAM.

**Use when**:
- Very long queues (millions of messages)
- Large messages
- Limited RAM

```python
channel.queue_declare(
    queue='large_queue',
    durable=True,
    arguments={
        'x-queue-mode': 'lazy'
    }
)
```

**Trade-offs**:
- **Slower delivery** (disk I/O)
- **Lower memory usage**
- **Better for large backlogs**

---

## Acknowledgments and Delivery Guarantees

### Consumer Acknowledgments

**Acknowledgment modes**:

**1. Auto-ack** (not recommended for important data):
```python
channel.basic_consume(
    queue='tasks',
    on_message_callback=callback,
    auto_ack=True  # Message considered delivered immediately
)
```

**2. Manual ack** (recommended):
```python
def callback(ch, method, properties, body):
    try:
        process(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        # Requeue on failure
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

channel.basic_consume(
    queue='tasks',
    on_message_callback=callback,
    auto_ack=False
)
```

### Acknowledgment Methods

**basic.ack**: Positive acknowledgment (message processed successfully).
```python
ch.basic_ack(delivery_tag=method.delivery_tag)
```

**basic.nack**: Negative acknowledgment (message processing failed).
```python
# Requeue for retry
ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

# Don't requeue (dead letter or discard)
ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

# Multiple messages
ch.basic_nack(delivery_tag=method.delivery_tag, multiple=True, requeue=False)
```

**basic.reject**: Reject single message (older method, use nack instead).
```python
ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
```

### Delivery Guarantees

**At-most-once**:
- Auto-ack enabled
- Message lost if consumer crashes before processing
- Fastest, least reliable

**At-least-once**:
- Manual ack
- Message redelivered if consumer crashes
- May receive duplicates
- Most common, good reliability

**Exactly-once**:
- Not natively supported by AMQP
- Requires application-level deduplication
- Use message_id or correlation_id

**Example: At-least-once with deduplication**:
```python
import redis

redis_client = redis.Redis()
seen_key_prefix = 'seen:'

def callback(ch, method, properties, body):
    msg_id = properties.message_id
    if not msg_id:
        print("Missing message_id, skipping")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    seen_key = f"{seen_key_prefix}{msg_id}"

    # Check if already processed
    if redis_client.exists(seen_key):
        print(f"Duplicate message {msg_id}, skipping")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    # Process message
    try:
        process(body)
        # Mark as seen (24 hour expiry)
        redis_client.setex(seen_key, 86400, '1')
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Processing failed: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

channel.basic_consume(queue='tasks', on_message_callback=callback, auto_ack=False)
```

### Redelivery Behavior

**Message redelivered when**:
- Consumer doesn't ack before connection closes
- Consumer sends nack with requeue=True
- Channel or connection closes with unacked messages

**Redelivered flag**: Set on redelivered messages.
```python
def callback(ch, method, properties, body):
    if method.redelivered:
        print("This message was redelivered")
    process(body)
    ch.basic_ack(delivery_tag=method.delivery_tag)
```

**Redelivery order**: FIFO within consumer, but not guaranteed across consumers.

### Prefetch Count (QoS)

**Control how many unacked messages delivered to consumer.**

```python
# Only 1 unacked message at a time (fair dispatch)
channel.basic_qos(prefetch_count=1)

# Up to 10 unacked messages (batch processing)
channel.basic_qos(prefetch_count=10)

# Global QoS (across all consumers on channel)
channel.basic_qos(prefetch_count=5, global_qos=True)
```

**Impact**:
- **prefetch_count=1**: Fair distribution, slower throughput
- **prefetch_count=N**: Batching, faster throughput, uneven distribution
- **No prefetch limit**: All messages delivered immediately, memory risk

**Best practice**:
- Long-running tasks: prefetch_count=1
- Fast processing: prefetch_count=10-100
- Monitor queue depth and consumer utilization

---

## Flow Control

### Consumer Flow Control

**Prefetch count limits** unacked messages per consumer.

```python
channel.basic_qos(prefetch_count=10)
```

### Publisher Flow Control

**Broker blocks publishers** when:
- Memory alarm triggered
- Disk space alarm triggered
- Connection limits reached

**Blocked connection**:
```python
def on_blocked(connection, method):
    print(f"Connection blocked: {method}")

def on_unblocked(connection, method):
    print("Connection unblocked")

connection.add_on_connection_blocked_callback(on_blocked)
connection.add_on_connection_unblocked_callback(on_unblocked)
```

**Handling blocked publishers**:
```python
import pika
import time

def publish_with_retry(channel, exchange, routing_key, body, max_retries=3):
    for attempt in range(max_retries):
        try:
            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body
            )
            return True
        except pika.exceptions.ConnectionBlocked:
            print(f"Connection blocked, retrying in {2**attempt}s...")
            time.sleep(2**attempt)
    return False
```

### Memory Alarms

**RabbitMQ blocks publishers** when memory usage exceeds threshold.

**Default**: 40% of available RAM

**Configure** in rabbitmq.conf:
```
vm_memory_high_watermark.relative = 0.5  # 50% of RAM
vm_memory_high_watermark.absolute = 2GB  # Or absolute value
```

**Monitoring**:
```bash
rabbitmqctl status | grep memory
```

**Resolution**:
- Increase consumer rate
- Reduce publisher rate
- Add more RAM
- Enable lazy queues
- Reduce queue depth

### Disk Alarms

**RabbitMQ blocks publishers** when free disk space below threshold.

**Default**: 50MB free

**Configure**:
```
disk_free_limit.relative = 1.0  # 100% of RAM
disk_free_limit.absolute = 5GB  # Or absolute value
```

---

## Clustering

### Cluster Architecture

**RabbitMQ cluster**: Group of nodes forming a single logical broker.

**What's replicated**:
- Exchanges
- Bindings
- Vhost definitions
- User accounts
- Permissions

**What's NOT replicated by default**:
- Queue contents (except quorum/stream queues)
- Messages

**Cluster topology**:
```
┌──────────────────────────────────┐
│         RabbitMQ Cluster         │
│  ┌───────────┐  ┌───────────┐   │
│  │  Node 1   │  │  Node 2   │   │
│  │  (Master) │  │  (Mirror) │   │
│  └─────┬─────┘  └─────┬─────┘   │
│        │metadata       │         │
│        └───────┬───────┘         │
│                ├───────────┐     │
│          ┌─────┴─────┐     │     │
│          │  Node 3   │     │     │
│          │  (Mirror) │     │     │
│          └───────────┘     │     │
└────────────────────────────┼─────┘
                             │
                        Client Connects
```

### Setting Up a Cluster

**Prerequisites**:
- Same Erlang version
- Same RabbitMQ version
- Shared Erlang cookie
- Network connectivity (ports 4369, 25672)
- DNS or /etc/hosts resolution

**Example 3-node cluster**:

**Node 1** (ubuntu1):
```bash
# Start RabbitMQ
sudo systemctl start rabbitmq-server

# Copy Erlang cookie for other nodes
sudo cat /var/lib/rabbitmq/.erlang.cookie
```

**Node 2** (ubuntu2):
```bash
# Copy Erlang cookie from Node 1
echo "COOKIEVALUE" | sudo tee /var/lib/rabbitmq/.erlang.cookie
sudo chmod 400 /var/lib/rabbitmq/.erlang.cookie
sudo chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie

# Start RabbitMQ
sudo systemctl start rabbitmq-server

# Join cluster
sudo rabbitmqctl stop_app
sudo rabbitmqctl reset
sudo rabbitmqctl join_cluster rabbit@ubuntu1
sudo rabbitmqctl start_app
```

**Node 3** (ubuntu3):
```bash
# Same as Node 2, joining ubuntu1
sudo rabbitmqctl stop_app
sudo rabbitmqctl reset
sudo rabbitmqctl join_cluster rabbit@ubuntu1
sudo rabbitmqctl start_app
```

**Verify cluster**:
```bash
sudo rabbitmqctl cluster_status
```

### Queue Behavior in Cluster

**Classic queue** (non-mirrored):
- Resides on one node (master)
- Other nodes proxy operations
- Lost if master node crashes

**Mirrored queue** (deprecated, use quorum queues):
- Replicated to multiple nodes
- Automatic failover

**Quorum queue** (recommended):
- Raft-based replication
- High availability
- Strongly consistent

### Client Connections

**Clients can connect to any node.**

**Connection strategies**:
```python
import pika

# Single node
params = pika.ConnectionParameters('node1.example.com')

# Multiple nodes (failover)
params = [
    pika.ConnectionParameters('node1.example.com'),
    pika.ConnectionParameters('node2.example.com'),
    pika.ConnectionParameters('node3.example.com')
]
connection = pika.BlockingConnection(params)
```

**Load balancer**:
```
Client → HAProxy → RabbitMQ Node 1
                 → RabbitMQ Node 2
                 → RabbitMQ Node 3
```

**HAProxy config**:
```
listen rabbitmq
    bind *:5672
    mode tcp
    balance roundrobin
    server node1 10.0.0.1:5672 check inter 5s rise 2 fall 3
    server node2 10.0.0.2:5672 check inter 5s rise 2 fall 3
    server node3 10.0.0.3:5672 check inter 5s rise 2 fall 3
```

### Cluster Maintenance

**Add node**:
```bash
# On new node
rabbitmqctl stop_app
rabbitmqctl reset
rabbitmqctl join_cluster rabbit@node1
rabbitmqctl start_app
```

**Remove node**:
```bash
# On node to remove
rabbitmqctl stop_app

# On any cluster node
rabbitmqctl forget_cluster_node rabbit@old_node
```

**Change node type** (disk/ram):
```bash
# Disk node (default, persists metadata)
rabbitmqctl change_cluster_node_type disc

# RAM node (metadata in RAM only, faster but less durable)
rabbitmqctl change_cluster_node_type ram
```

**Best practice**: At least 2 disk nodes for metadata durability.

---

## High Availability

### Quorum Queues

**Quorum queues**: Replicated, durable, highly available queues using Raft consensus.

**Characteristics**:
- Data replicated across nodes
- Leader election on failure
- Strongly consistent
- Higher overhead than classic queues

**Declare quorum queue**:
```python
channel.queue_declare(
    queue='ha_tasks',
    durable=True,
    arguments={
        'x-queue-type': 'quorum',
        'x-quorum-initial-group-size': 3  # Replicas
    }
)
```

**Quorum size**: `(n/2) + 1` nodes must be available (e.g., 3 nodes = tolerate 1 failure).

**Advantages**:
- Automatic failover
- No message loss
- Consistent ordering
- Poison message handling

**Trade-offs**:
- Higher latency (consensus overhead)
- More disk/network usage
- Requires 3+ nodes

### Stream Queues

**Stream queues**: Append-only log, persistent, replayable.

**Use cases**:
- Event sourcing
- Audit logs
- Time-series data
- Large message backlogs

**Declare stream**:
```python
channel.queue_declare(
    queue='events',
    durable=True,
    arguments={
        'x-queue-type': 'stream',
        'x-max-length-bytes': 10_000_000_000,  # 10GB
        'x-stream-max-segment-size-bytes': 500_000_000  # 500MB segments
    }
)
```

**Consuming from offset**:
```python
channel.basic_consume(
    queue='events',
    on_message_callback=callback,
    arguments={
        'x-stream-offset': 'first'  # 'first', 'last', 'next', timestamp, offset
    }
)
```

**Advantages**:
- Non-destructive reads
- Replay messages
- High throughput
- Time-based retention

### Classic Mirrored Queues (Deprecated)

**Mirrored queues** (ha-mode): Deprecated, use quorum queues instead.

**Policy-based mirroring**:
```bash
# Mirror to all nodes
rabbitmqctl set_policy ha-all "^ha\." '{"ha-mode":"all"}' --apply-to queues

# Mirror to 2 nodes
rabbitmqctl set_policy ha-two "^ha\." '{"ha-mode":"exactly","ha-params":2}' --apply-to queues

# Mirror to specific nodes
rabbitmqctl set_policy ha-nodes "^ha\." '{"ha-mode":"nodes","ha-params":["node1@host","node2@host"]}' --apply-to queues
```

**Migration path**: Use quorum queues for new applications.

---

## Federation and Shovel

### Federation

**Federation**: Link exchanges/queues across brokers (different datacenters, regions).

**Use cases**:
- Geographic distribution
- WAN connections
- Multi-datacenter
- Gradual upgrades

**Federation architecture**:
```
Datacenter 1              Datacenter 2
┌─────────────┐           ┌─────────────┐
│  Upstream   │ ────────> │ Downstream  │
│  Exchange   │ Federation│  Exchange   │
└─────────────┘           └─────────────┘
```

**Setup**:
```bash
# Enable plugin
rabbitmq-plugins enable rabbitmq_federation
rabbitmq-plugins enable rabbitmq_federation_management

# Define upstream
rabbitmqctl set_parameter federation-upstream my-upstream \
  '{"uri":"amqp://upstream.example.com","expires":3600000}'

# Define policy
rabbitmqctl set_policy --apply-to exchanges federate-me \
  "^federated\." '{"federation-upstream-set":"all"}'
```

**Python example**:
```python
# Downstream (receives federated messages)
channel.exchange_declare(exchange='federated.logs', exchange_type='topic', durable=True)
channel.queue_bind(exchange='federated.logs', queue='logs', routing_key='#')

# Messages published upstream appear downstream
```

### Shovel

**Shovel**: Move messages from queue/exchange to another queue/exchange.

**Use cases**:
- Migration
- Data integration
- Message forwarding

**Setup**:
```bash
# Enable plugin
rabbitmq-plugins enable rabbitmq_shovel
rabbitmq-plugins enable rabbitmq_shovel_management

# Define shovel
rabbitmqctl set_parameter shovel my-shovel \
  '{"src-uri":"amqp://source.example.com","src-queue":"source_queue",
    "dest-uri":"amqp://dest.example.com","dest-queue":"dest_queue"}'
```

**Dynamic shovel** (via management API):
```json
{
  "src-uri": "amqp://localhost",
  "src-queue": "source",
  "dest-uri": "amqp://remote.example.com",
  "dest-queue": "destination",
  "ack-mode": "on-confirm",
  "src-delete-after": "never"
}
```

**Federation vs Shovel**:
- **Federation**: Automatic, bidirectional, link exchanges
- **Shovel**: Manual, unidirectional, move messages

---

## Dead Letter Exchanges

### Concept

**Dead Letter Exchange (DLX)**: Exchange that receives rejected or expired messages.

**Messages dead-lettered when**:
- Consumer rejects (basic.nack/basic.reject with requeue=False)
- Message TTL expires
- Queue length limit exceeded

**Use cases**:
- Failed message handling
- Retry logic
- Poison message quarantine
- Audit trail

### Setup

**Declare queue with DLX**:
```python
# Main queue
channel.queue_declare(
    queue='tasks',
    durable=True,
    arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'failed.tasks'  # Optional
    }
)

# Dead letter exchange
channel.exchange_declare(exchange='dlx', exchange_type='direct', durable=True)

# Dead letter queue
channel.queue_declare(queue='failed_tasks', durable=True)
channel.queue_bind(exchange='dlx', queue='failed_tasks', routing_key='failed.tasks')
```

**Reject message** (send to DLX):
```python
def callback(ch, method, properties, body):
    try:
        process(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Processing failed: {e}")
        # Send to DLX
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

channel.basic_consume(queue='tasks', on_message_callback=callback, auto_ack=False)
```

### Retry Pattern

**Exponential backoff** using DLX and TTL:

```python
# Main queue
channel.queue_declare(queue='tasks', durable=True, arguments={
    'x-dead-letter-exchange': 'retry'
})

# Retry exchange
channel.exchange_declare(exchange='retry', exchange_type='direct', durable=True)

# Retry queues with increasing TTL
for delay in [1000, 5000, 15000, 60000]:  # 1s, 5s, 15s, 60s
    retry_queue = f'tasks.retry.{delay}'
    channel.queue_declare(
        queue=retry_queue,
        durable=True,
        arguments={
            'x-message-ttl': delay,
            'x-dead-letter-exchange': '',
            'x-dead-letter-routing-key': 'tasks'
        }
    )
    channel.queue_bind(exchange='retry', queue=retry_queue, routing_key=str(delay))

# Consumer with retry logic
def callback(ch, method, properties, body):
    headers = properties.headers or {}
    retry_count = headers.get('x-retry-count', 0)

    try:
        process(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        if retry_count < 3:
            # Retry with exponential backoff
            delay = [1000, 5000, 15000][retry_count]
            headers['x-retry-count'] = retry_count + 1

            ch.basic_publish(
                exchange='retry',
                routing_key=str(delay),
                body=body,
                properties=pika.BasicProperties(headers=headers, delivery_mode=2)
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            # Max retries, send to DLX
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

channel.basic_consume(queue='tasks', on_message_callback=callback, auto_ack=False)
```

### Dead Letter Metadata

**Headers added to dead-lettered messages**:
- `x-first-death-queue`: Original queue name
- `x-first-death-reason`: rejected, expired, maxlen
- `x-first-death-exchange`: Original exchange
- `x-death`: Array of death events (for multiple DLX hops)

**Inspect dead letter reason**:
```python
def callback(ch, method, properties, body):
    headers = properties.headers or {}
    deaths = headers.get('x-death', [])

    if deaths:
        first_death = deaths[0]
        queue = first_death.get('queue')
        reason = first_death.get('reason')
        count = first_death.get('count')
        print(f"Dead lettered from {queue}, reason: {reason}, count: {count}")

    # Handle failed message
    investigate(body)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue='failed_tasks', on_message_callback=callback, auto_ack=False)
```

---

## TTL and Expiry

### Message TTL

**Per-message TTL**:
```python
channel.basic_publish(
    exchange='',
    routing_key='tasks',
    body='Task',
    properties=pika.BasicProperties(
        delivery_mode=2,
        expiration='60000'  # 60 seconds (milliseconds as string)
    )
)
```

**Queue-level TTL** (all messages):
```python
channel.queue_declare(
    queue='temporary',
    durable=True,
    arguments={
        'x-message-ttl': 30000  # 30 seconds (milliseconds as integer)
    }
)
```

**Expired messages**:
- Discarded when reaching head of queue
- Sent to DLX if configured
- Counted in queue statistics

**Use cases**:
- Time-sensitive notifications
- Cache invalidation
- Temporary data

### Queue TTL

**Queue auto-deletion after idle period**:
```python
channel.queue_declare(
    queue='temporary',
    durable=False,
    arguments={
        'x-expires': 60000  # Delete queue after 60s of inactivity
    }
)
```

**Inactivity**: No consumers, no basic.get calls, no new messages.

### TTL Best Practices

1. **Per-message TTL**: When different messages need different expiries
2. **Queue TTL**: When all messages have same expiry
3. **Use DLX**: To capture expired messages for auditing
4. **Monitor expired count**: Indicates consumer backlog

---

## Priority Queues

### Setup

**Declare priority queue**:
```python
channel.queue_declare(
    queue='prioritized_tasks',
    durable=True,
    arguments={
        'x-max-priority': 10  # Priority range: 0 (lowest) to 10 (highest)
    }
)
```

**Publish with priority**:
```python
# High priority
channel.basic_publish(
    exchange='',
    routing_key='prioritized_tasks',
    body='Critical task',
    properties=pika.BasicProperties(
        delivery_mode=2,
        priority=10
    )
)

# Low priority
channel.basic_publish(
    exchange='',
    routing_key='prioritized_tasks',
    body='Background task',
    properties=pika.BasicProperties(
        delivery_mode=2,
        priority=1
    )
)
```

**Consumer** processes high-priority messages first:
```python
channel.basic_consume(queue='prioritized_tasks', on_message_callback=callback, auto_ack=False)
```

### Priority Behavior

**Processing order**:
- Higher priority messages delivered first
- Same priority = FIFO
- Priority only matters when queue has backlog

**Performance impact**:
- CPU overhead (maintaining priority order)
- Memory overhead (priority heap)
- Use only when necessary

**Best practices**:
- Limit priority range (0-5 often sufficient)
- Reserve highest priority for critical messages
- Monitor queue depth by priority

---

## Performance Tuning

### Publisher Performance

**Connection pooling**:
```python
import pika.pool

params = pika.ConnectionParameters('localhost')
pool = pika.pool.ConnectionPool(
    lambda: pika.BlockingConnection(params),
    max_size=10,
    max_overflow=20
)

with pool.acquire() as connection:
    channel = connection.channel()
    channel.basic_publish(...)
```

**Batch publishing**:
```python
# Batch publish (fewer network round trips)
for i in range(1000):
    channel.basic_publish(exchange='', routing_key='tasks', body=f'Task {i}')
# All published together

# vs. Individual publishes with confirms (slower but reliable)
channel.confirm_delivery()
for i in range(1000):
    try:
        channel.basic_publish(...)
    except Exception as e:
        handle_error(e)
```

**Async publishing** (faster):
```python
import asyncio
import aio_pika

async def publish_async():
    connection = await aio_pika.connect_robust("amqp://localhost/")
    channel = await connection.channel()

    tasks = [
        channel.default_exchange.publish(
            aio_pika.Message(body=f'Task {i}'.encode()),
            routing_key='tasks'
        )
        for i in range(1000)
    ]
    await asyncio.gather(*tasks)
    await connection.close()

asyncio.run(publish_async())
```

### Consumer Performance

**Prefetch count**:
```python
# Fast processing: Higher prefetch
channel.basic_qos(prefetch_count=100)

# Slow processing: Lower prefetch
channel.basic_qos(prefetch_count=1)
```

**Multiple consumers**:
```python
# Scale horizontally (run multiple consumer processes)
# Each consumer competes for messages
```

**Async consumers**:
```python
import asyncio
import aio_pika

async def callback(message):
    async with message.process():
        await process_async(message.body)

async def consume_async():
    connection = await aio_pika.connect_robust("amqp://localhost/")
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    queue = await channel.declare_queue('tasks', durable=True)
    await queue.consume(callback)

    await asyncio.Future()  # Run forever

asyncio.run(consume_async())
```

### Queue Performance

**Lazy queues** (large backlogs):
```python
channel.queue_declare(
    queue='large_queue',
    durable=True,
    arguments={'x-queue-mode': 'lazy'}
)
```

**Queue length limits**:
```python
channel.queue_declare(
    queue='bounded',
    durable=True,
    arguments={
        'x-max-length': 100000,          # Max messages
        'x-max-length-bytes': 1000000000, # Max bytes
        'x-overflow': 'reject-publish'    # or 'drop-head'
    }
)
```

**Single active consumer** (prevent concurrent processing):
```python
channel.queue_declare(
    queue='ordered',
    durable=True,
    arguments={'x-single-active-consumer': True}
)
```

### Network Performance

**Heartbeat tuning**:
```python
params = pika.ConnectionParameters(
    'localhost',
    heartbeat=60  # Seconds (0 to disable)
)
```

**Frame size**:
```python
params = pika.ConnectionParameters(
    'localhost',
    frame_max=131072  # Bytes (default 131072 = 128KB)
)
```

**Channel max**:
```python
params = pika.ConnectionParameters(
    'localhost',
    channel_max=2047  # Max channels per connection
)
```

### Broker Performance

**Memory management**:
```
# rabbitmq.conf
vm_memory_high_watermark.relative = 0.5  # 50% of RAM
vm_memory_high_watermark_paging_ratio = 0.75  # Start paging at 37.5% RAM
```

**Disk I/O**:
```
# Use fast disk (SSD)
# Separate disk for mnesia and messages
# Monitor disk I/O wait
```

**Network**:
```
# Increase TCP buffer sizes
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
```

**Erlang VM**:
```
# Increase schedulers (default = CPU cores)
RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS="+S 8:8"

# Increase async threads
+A 128
```

---

## Monitoring and Observability

### Key Metrics

**Queue metrics**:
- `messages`: Total messages in queue
- `messages_ready`: Messages ready for delivery
- `messages_unacknowledged`: Messages delivered but not acked
- `message_stats.publish_details.rate`: Publish rate (msg/s)
- `message_stats.deliver_get_details.rate`: Delivery rate (msg/s)
- `message_stats.ack_details.rate`: Ack rate (msg/s)
- `consumers`: Number of active consumers

**Connection metrics**:
- `connection_created`: Connection count
- `connection_closed`: Closed connections
- `channel_created`: Channel count
- `channel_closed`: Closed channels

**Node metrics**:
- `mem_used`: Memory usage (bytes)
- `mem_limit`: Memory limit
- `fd_used`: File descriptors used
- `fd_total`: File descriptors available
- `disk_free`: Free disk space
- `disk_free_limit`: Minimum free disk
- `proc_used`: Erlang processes
- `proc_total`: Max Erlang processes

### Management API

**Get queue info**:
```python
import requests

response = requests.get(
    'http://localhost:15672/api/queues/%2F/tasks',  # %2F = '/' vhost
    auth=('guest', 'guest')
)
queue_info = response.json()

print(f"Messages: {queue_info['messages']}")
print(f"Publish rate: {queue_info['message_stats']['publish_details']['rate']}")
print(f"Consumers: {queue_info['consumers']}")
```

**List all queues**:
```python
response = requests.get(
    'http://localhost:15672/api/queues',
    auth=('guest', 'guest')
)
queues = response.json()

for queue in queues:
    print(f"{queue['name']}: {queue['messages']} messages, {queue['consumers']} consumers")
```

**Node health**:
```python
response = requests.get(
    'http://localhost:15672/api/nodes',
    auth=('guest', 'guest')
)
nodes = response.json()

for node in nodes:
    print(f"Node: {node['name']}")
    print(f"  Memory: {node['mem_used']/1e9:.2f}GB / {node['mem_limit']/1e9:.2f}GB")
    print(f"  Disk: {node['disk_free']/1e9:.2f}GB free")
    print(f"  FD: {node['fd_used']}/{node['fd_total']}")
```

### Prometheus Metrics

**Enable Prometheus plugin**:
```bash
rabbitmq-plugins enable rabbitmq_prometheus
```

**Scrape endpoint**:
```
http://localhost:15692/metrics
```

**Key Prometheus metrics**:
```
# Queue depth
rabbitmq_queue_messages{queue="tasks"}

# Message rates
rate(rabbitmq_queue_messages_published_total{queue="tasks"}[1m])
rate(rabbitmq_queue_messages_delivered_total{queue="tasks"}[1m])

# Consumer count
rabbitmq_queue_consumers{queue="tasks"}

# Memory
rabbitmq_process_resident_memory_bytes

# Connections
rabbitmq_connections
```

**Grafana dashboard**:
- Import official RabbitMQ dashboard (ID: 10991)
- Visualize queue depths, rates, memory, connections

### Logging

**Log levels** (rabbitmq.conf):
```
log.console.level = info  # debug, info, warning, error
log.file.level = info
```

**Python client logging**:
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('pika')
logger.setLevel(logging.DEBUG)
```

**Important logs**:
- Connection errors
- Channel errors
- Message rejections
- Memory alarms
- Disk alarms
- Cluster events

### Tracing

**Enable message tracing**:
```bash
rabbitmqctl trace_on
rabbitmqctl trace_on -p my_vhost

# Disable
rabbitmqctl trace_off
```

**Firehose tracer** (all messages):
```bash
rabbitmq-plugins enable rabbitmq_tracing
```

**Python tracer**:
```python
# Create trace queue
channel.queue_declare(queue='trace', durable=False, auto_delete=True)
channel.queue_bind(exchange='amq.rabbitmq.trace', queue='trace', routing_key='#')

# Consume trace messages
def trace_callback(ch, method, properties, body):
    print(f"Trace: {method.routing_key} - {body}")

channel.basic_consume(queue='trace', on_message_callback=trace_callback, auto_ack=True)
```

**Warning**: Tracing has significant performance impact. Use only for debugging.

---

## Security

### Authentication

**Default user**:
```bash
# Username: guest
# Password: guest
# Only works from localhost

# Create new user
rabbitmqctl add_user myuser mypassword

# Set tags (administrator, monitoring, management, policymaker)
rabbitmqctl set_user_tags myuser administrator

# Delete user
rabbitmqctl delete_user guest
```

**Connection with auth**:
```python
credentials = pika.PlainCredentials('myuser', 'mypassword')
params = pika.ConnectionParameters('localhost', credentials=credentials)
connection = pika.BlockingConnection(params)
```

### Authorization

**Permissions** (configure, write, read):
```bash
# Grant all permissions on vhost
rabbitmqctl set_permissions -p my_vhost myuser ".*" ".*" ".*"

# Configure: declare/delete exchanges, queues, bindings
# Write: publish messages
# Read: consume messages

# Restrict to specific resources
rabbitmqctl set_permissions -p my_vhost myuser "^myapp-.*" "^myapp-.*" "^myapp-.*"

# List permissions
rabbitmqctl list_permissions -p my_vhost
```

### TLS/SSL

**Generate certificates**:
```bash
# Using tls-gen tool
git clone https://github.com/michaelklishin/tls-gen
cd tls-gen/basic
make
```

**Configure RabbitMQ** (rabbitmq.conf):
```
listeners.ssl.default = 5671

ssl_options.cacertfile = /path/to/ca_certificate.pem
ssl_options.certfile   = /path/to/server_certificate.pem
ssl_options.keyfile    = /path/to/server_key.pem
ssl_options.verify     = verify_peer
ssl_options.fail_if_no_peer_cert = false
```

**Connect with TLS**:
```python
import ssl

ssl_options = {
    'ca_certs': '/path/to/ca_certificate.pem',
    'certfile': '/path/to/client_certificate.pem',
    'keyfile': '/path/to/client_key.pem',
    'cert_reqs': ssl.CERT_REQUIRED
}

params = pika.ConnectionParameters(
    'localhost',
    5671,
    credentials=pika.PlainCredentials('myuser', 'mypassword'),
    ssl_options=pika.SSLOptions(ssl_options)
)
connection = pika.BlockingConnection(params)
```

### Vhost Isolation

**Vhosts provide isolation**:
```bash
# Create vhost
rabbitmqctl add_vhost production
rabbitmqctl add_vhost staging

# Set permissions
rabbitmqctl set_permissions -p production app_user ".*" ".*" ".*"
rabbitmqctl set_permissions -p staging test_user ".*" ".*" ".*"
```

**Connect to vhost**:
```python
params = pika.ConnectionParameters(
    'localhost',
    virtual_host='production'
)
```

**URL format**:
```
amqp://username:password@hostname:port/vhost_name
amqp://app:pass@localhost:5672/production
```

### Network Security

**Bind to specific interface**:
```
# rabbitmq.conf
listeners.tcp.1 = 10.0.0.1:5672  # Internal network only
```

**Firewall rules**:
```bash
# AMQP
iptables -A INPUT -p tcp --dport 5672 -j ACCEPT

# AMQPS
iptables -A INPUT -p tcp --dport 5671 -j ACCEPT

# Management UI
iptables -A INPUT -p tcp --dport 15672 -s 10.0.0.0/8 -j ACCEPT

# Clustering
iptables -A INPUT -p tcp --dport 25672 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 4369 -s 10.0.0.0/8 -j ACCEPT
```

---

## Client Libraries

### Python (pika)

**Install**:
```bash
pip install pika
```

**Basic usage**:
```python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='hello')
channel.basic_publish(exchange='', routing_key='hello', body='Hello World!')

connection.close()
```

**Async** (aio-pika):
```bash
pip install aio-pika
```

```python
import asyncio
import aio_pika

async def main():
    connection = await aio_pika.connect_robust("amqp://localhost/")
    channel = await connection.channel()

    await channel.default_exchange.publish(
        aio_pika.Message(body=b'Hello'),
        routing_key='hello'
    )

    await connection.close()

asyncio.run(main())
```

### Node.js (amqplib)

**Install**:
```bash
npm install amqplib
```

**Basic usage**:
```javascript
const amqp = require('amqplib');

async function main() {
  const connection = await amqp.connect('amqp://localhost');
  const channel = await connection.createChannel();

  await channel.assertQueue('hello');
  channel.sendToQueue('hello', Buffer.from('Hello World!'));

  await channel.close();
  await connection.close();
}

main();
```

### Go (amqp091-go)

**Install**:
```bash
go get github.com/rabbitmq/amqp091-go
```

**Basic usage**:
```go
package main

import (
    "log"
    amqp "github.com/rabbitmq/amqp091-go"
)

func main() {
    conn, err := amqp.Dial("amqp://guest:guest@localhost:5672/")
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()

    ch, err := conn.Channel()
    if err != nil {
        log.Fatal(err)
    }
    defer ch.Close()

    q, err := ch.QueueDeclare("hello", false, false, false, false, nil)
    if err != nil {
        log.Fatal(err)
    }

    err = ch.Publish("", q.Name, false, false, amqp.Publishing{
        ContentType: "text/plain",
        Body:        []byte("Hello World!"),
    })
    if err != nil {
        log.Fatal(err)
    }
}
```

### Java (amqp-client)

**Maven**:
```xml
<dependency>
    <groupId>com.rabbitmq</groupId>
    <artifactId>amqp-client</artifactId>
    <version>5.18.0</version>
</dependency>
```

**Basic usage**:
```java
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.Channel;

public class Publisher {
    public static void main(String[] args) throws Exception {
        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost("localhost");

        try (Connection connection = factory.newConnection();
             Channel channel = connection.createChannel()) {

            channel.queueDeclare("hello", false, false, false, null);
            channel.basicPublish("", "hello", null, "Hello World!".getBytes());
        }
    }
}
```

---

## Common Patterns

### Reliable Publishing

**Publisher confirms + retries**:
```python
import pika
import time

def publish_with_retry(channel, exchange, routing_key, body, max_retries=3):
    for attempt in range(max_retries):
        try:
            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
                mandatory=True
            )
            return True
        except pika.exceptions.UnroutableError:
            print(f"Message unroutable, attempt {attempt+1}/{max_retries}")
            time.sleep(2**attempt)
        except pika.exceptions.NackError:
            print(f"Message nacked, attempt {attempt+1}/{max_retries}")
            time.sleep(2**attempt)
    return False

channel.confirm_delivery()
success = publish_with_retry(channel, 'events', 'user.signup', '{"user_id": 123}')
```

### Idempotent Consumer

**Deduplication with Redis**:
```python
import redis
import pika

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def callback(ch, method, properties, body):
    msg_id = properties.message_id
    if not msg_id:
        print("Missing message_id")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    key = f"processed:{msg_id}"
    if redis_client.exists(key):
        print(f"Duplicate message {msg_id}, skipping")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        process(body)
        redis_client.setex(key, 86400, '1')  # 24 hour expiry
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Processing failed: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

channel.basic_consume(queue='tasks', on_message_callback=callback, auto_ack=False)
channel.start_consuming()
```

### Circuit Breaker

**Prevent cascading failures**:
```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = 1
    OPEN = 2
    HALF_OPEN = 3

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN

            raise e

breaker = CircuitBreaker()

def callback(ch, method, properties, body):
    try:
        breaker.call(process, body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Circuit breaker: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
```

### Message Versioning

**Handle schema evolution**:
```python
import json

def callback(ch, method, properties, body):
    data = json.loads(body)
    version = data.get('version', 1)

    if version == 1:
        process_v1(data)
    elif version == 2:
        process_v2(data)
    else:
        print(f"Unknown version {version}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    ch.basic_ack(delivery_tag=method.delivery_tag)

# Publisher
message = {
    'version': 2,
    'data': {'user_id': 123, 'action': 'signup'}
}
channel.basic_publish(
    exchange='events',
    routing_key='user.signup',
    body=json.dumps(message),
    properties=pika.BasicProperties(
        content_type='application/json',
        type='user.signup.v2'
    )
)
```

---

## Anti-Patterns

### 1. Not Using Durability

**Problem**: Messages lost on broker restart.

**Solution**:
```python
# Durable queue
channel.queue_declare(queue='tasks', durable=True)

# Persistent messages
channel.basic_publish(
    exchange='',
    routing_key='tasks',
    body='task',
    properties=pika.BasicProperties(delivery_mode=2)
)
```

### 2. Auto-Acknowledgment

**Problem**: Messages lost if consumer crashes before processing.

**Solution**:
```python
# Manual ack
def callback(ch, method, properties, body):
    process(body)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue='tasks', on_message_callback=callback, auto_ack=False)
```

### 3. No Prefetch Limit

**Problem**: All messages delivered to single consumer, uneven load.

**Solution**:
```python
channel.basic_qos(prefetch_count=1)  # Fair dispatch
```

### 4. Ignoring Connection Errors

**Problem**: Application crashes on network issues.

**Solution**:
```python
import pika
import time

def get_connection(max_retries=5):
    for attempt in range(max_retries):
        try:
            return pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        except pika.exceptions.AMQPConnectionError:
            print(f"Connection failed, retrying in {2**attempt}s...")
            time.sleep(2**attempt)
    raise Exception("Failed to connect after max retries")

connection = get_connection()
```

### 5. Publishing to Non-Existent Exchange

**Problem**: Messages silently dropped.

**Solution**:
```python
# Declare exchange before publishing
channel.exchange_declare(exchange='logs', exchange_type='direct', durable=True)

# Or use mandatory flag
channel.basic_publish(
    exchange='logs',
    routing_key='info',
    body='message',
    mandatory=True  # Return message if unroutable
)
```

### 6. Not Monitoring Queue Depth

**Problem**: Queue buildup goes unnoticed, memory exhaustion.

**Solution**:
```python
# Monitor via management API
import requests

response = requests.get('http://localhost:15672/api/queues', auth=('guest', 'guest'))
queues = response.json()

for queue in queues:
    if queue['messages'] > 10000:
        print(f"ALERT: {queue['name']} has {queue['messages']} messages")
```

### 7. Too Many Connections

**Problem**: File descriptor exhaustion.

**Solution**:
```python
# Use connection pooling
import pika.pool

params = pika.ConnectionParameters('localhost')
pool = pika.pool.ConnectionPool(lambda: pika.BlockingConnection(params), max_size=10)

with pool.acquire() as connection:
    channel = connection.channel()
    # Use channel
```

### 8. Blocking Operations in Consumer

**Problem**: Consumer stalls, messages accumulate.

**Solution**:
```python
import asyncio
import aio_pika

# Use async consumer
async def callback(message):
    async with message.process():
        await process_async(message.body)

# Or use thread pool for blocking operations
import concurrent.futures

executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

def callback(ch, method, properties, body):
    future = executor.submit(process_blocking, body)
    future.add_done_callback(lambda f: ch.basic_ack(delivery_tag=method.delivery_tag))
```

---

## Troubleshooting

### Connection Refused

**Symptoms**: Can't connect to broker.

**Causes**:
- RabbitMQ not running
- Firewall blocking port
- Wrong hostname/port

**Diagnosis**:
```bash
# Check if RabbitMQ running
sudo systemctl status rabbitmq-server

# Check port listening
sudo netstat -tlnp | grep 5672

# Test connection
telnet localhost 5672
```

**Solution**:
```bash
# Start RabbitMQ
sudo systemctl start rabbitmq-server

# Open firewall
sudo ufw allow 5672/tcp
```

### Authentication Failed

**Symptoms**: Login failed for user.

**Causes**:
- Wrong username/password
- User doesn't exist
- User lacks permissions

**Diagnosis**:
```bash
# List users
rabbitmqctl list_users

# List permissions
rabbitmqctl list_permissions -p /
```

**Solution**:
```bash
# Create user
rabbitmqctl add_user myuser mypassword

# Set permissions
rabbitmqctl set_permissions -p / myuser ".*" ".*" ".*"
```

### Messages Not Routed

**Symptoms**: Messages published but not received.

**Causes**:
- Wrong exchange name
- Wrong routing key
- No binding between exchange and queue
- Exchange type mismatch

**Diagnosis**:
```bash
# List bindings
rabbitmqctl list_bindings

# Check exchange
rabbitmqctl list_exchanges

# Enable tracing
rabbitmqctl trace_on
```

**Solution**:
```python
# Verify binding exists
channel.queue_bind(exchange='logs', queue='my_queue', routing_key='info')

# Use mandatory flag
channel.basic_publish(exchange='logs', routing_key='info', body='msg', mandatory=True)
```

### Memory Alarm

**Symptoms**: Publishers blocked, "memory alarm" in logs.

**Causes**:
- Queue buildup
- Insufficient RAM
- Memory leak

**Diagnosis**:
```bash
# Check memory usage
rabbitmqctl status | grep memory

# List queues by memory
rabbitmqctl list_queues name messages memory | sort -k3 -n
```

**Solution**:
```bash
# Increase consumer rate
# Reduce publisher rate
# Purge queues
rabbitmqctl purge_queue tasks

# Increase memory limit (rabbitmq.conf)
vm_memory_high_watermark.relative = 0.6

# Enable lazy queues
```

### Disk Alarm

**Symptoms**: Publishers blocked, "disk alarm" in logs.

**Causes**:
- Disk full
- Low disk space

**Diagnosis**:
```bash
# Check disk usage
df -h

# Check RabbitMQ data directory
du -sh /var/lib/rabbitmq
```

**Solution**:
```bash
# Free up disk space
# Increase disk_free_limit (rabbitmq.conf)
disk_free_limit.absolute = 1GB

# Move mnesia directory to larger disk
```

### Consumer Not Receiving Messages

**Symptoms**: Queue has messages but consumer doesn't receive them.

**Causes**:
- Consumer not subscribed
- Prefetch limit reached (unacked messages)
- Consumer paused
- Basic.get used instead of basic.consume

**Diagnosis**:
```bash
# Check consumers
rabbitmqctl list_queues name consumers

# Check unacked messages
rabbitmqctl list_queues name messages_unacknowledged
```

**Solution**:
```python
# Ensure consumer is consuming
channel.basic_consume(queue='tasks', on_message_callback=callback, auto_ack=False)
channel.start_consuming()

# Acknowledge messages
ch.basic_ack(delivery_tag=method.delivery_tag)

# Increase prefetch
channel.basic_qos(prefetch_count=10)
```

### Slow Performance

**Symptoms**: High latency, low throughput.

**Causes**:
- Insufficient resources
- Disk I/O bottleneck
- Network latency
- Inefficient consumer
- Publisher confirms enabled

**Diagnosis**:
```bash
# Check queue rates
rabbitmqctl list_queues name messages_ready message_stats

# Check memory/disk
rabbitmqctl status

# Profile consumer
# Profile publisher
```

**Solution**:
- Add more RAM
- Use SSD for storage
- Increase prefetch_count
- Use connection pooling
- Batch publish
- Use lazy queues for large queues
- Scale horizontally (more nodes)

---

## Production Best Practices

### 1. Infrastructure

**Clustering**:
- At least 3 nodes (quorum)
- Odd number of nodes
- Same datacenter (low latency)

**Resources**:
- 4+ CPU cores
- 8+ GB RAM
- SSD storage
- 1+ Gbps network

**Operating system**:
- Linux (Ubuntu, CentOS, Debian)
- Tuned kernel parameters
- Swap disabled or minimal

### 2. Configuration

**Memory**:
```
vm_memory_high_watermark.relative = 0.5
vm_memory_high_watermark_paging_ratio = 0.75
```

**Disk**:
```
disk_free_limit.absolute = 5GB
```

**Network**:
```
heartbeat = 60
frame_max = 131072
```

### 3. Monitoring

**Metrics**:
- Queue depths
- Message rates
- Consumer counts
- Memory usage
- Disk space
- Connection count

**Alerts**:
- Queue depth > threshold
- Memory alarm
- Disk alarm
- No consumers on critical queue
- High unacked message count
- Node down

**Tools**:
- Prometheus + Grafana
- Datadog
- New Relic
- Management API

### 4. Security

**Authentication**:
- Delete default guest user
- Use strong passwords
- Rotate credentials regularly

**Authorization**:
- Least privilege principle
- Separate users per application
- Use vhosts for isolation

**Network**:
- TLS for all connections
- Firewall rules
- VPN or private network

**Secrets**:
- Use secrets manager (Vault, AWS Secrets Manager)
- Don't hardcode credentials

### 5. Reliability

**Durability**:
- Durable queues
- Persistent messages
- Publisher confirms
- Manual acknowledgments

**High availability**:
- Quorum queues
- Multi-node cluster
- Load balancer
- Health checks

**Disaster recovery**:
- Regular backups (definitions, policies)
- Cross-region replication (federation)
- Runbooks for common failures

### 6. Performance

**Publisher**:
- Connection pooling
- Batch publishing
- Async publishing

**Consumer**:
- Appropriate prefetch_count
- Multiple consumers
- Async processing
- Horizontal scaling

**Queue**:
- Lazy queues for large backlogs
- Length limits to prevent unbounded growth
- TTL for time-sensitive messages

### 7. Operations

**Deployment**:
- Blue-green deployments
- Rolling upgrades
- Drain connections before restart

**Maintenance**:
- Regular upgrades
- Capacity planning
- Performance testing

**Troubleshooting**:
- Centralized logging
- Distributed tracing
- Playbooks for common issues

### 8. Development

**Testing**:
- Unit tests (mock broker)
- Integration tests (real broker)
- Load tests (simulate production)

**Code quality**:
- Error handling for all broker operations
- Connection recovery logic
- Idempotent consumers
- Message versioning

**Documentation**:
- Topology diagrams
- Message schemas
- Retry policies
- Runbooks

---

## Conclusion

This reference covered AMQP 0-9-1 protocol fundamentals, RabbitMQ architecture, exchange types, queue patterns, message properties, durability, acknowledgments, clustering, high availability, performance tuning, monitoring, security, client libraries, common patterns, anti-patterns, troubleshooting, and production best practices.

**Key takeaways**:
1. Use durable queues and persistent messages for important data
2. Always use manual acknowledgments
3. Set appropriate prefetch_count for fair dispatch
4. Use quorum queues for high availability
5. Monitor queue depths and set alerts
6. Handle connection failures gracefully
7. Use publisher confirms for critical messages
8. Implement retry logic with dead letter exchanges
9. Secure with TLS and proper authentication
10. Test failure scenarios before production

**Resources**:
- Official docs: https://www.rabbitmq.com/documentation.html
- AMQP 0-9-1 spec: https://www.rabbitmq.com/amqp-0-9-1-reference.html
- Best practices: https://www.rabbitmq.com/production-checklist.html
- Monitoring: https://www.rabbitmq.com/monitoring.html
