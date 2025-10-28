---
name: protocols-amqp-rabbitmq
description: RabbitMQ and AMQP 0-9-1 message broker implementation
---

# AMQP and RabbitMQ Implementation

**Scope**: AMQP 0-9-1 protocol, RabbitMQ broker, exchanges, queues, routing patterns, clustering, high availability
**Lines**: ~350
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Implementing message queuing with RabbitMQ
- Designing exchange and queue topologies
- Building work queue, pub-sub, routing, or RPC patterns
- Implementing message durability and acknowledgments
- Setting up RabbitMQ clustering and high availability
- Optimizing RabbitMQ performance
- Debugging message routing issues
- Implementing dead letter exchanges and retry logic
- Monitoring RabbitMQ metrics

## Core Concepts

### AMQP 0-9-1 Architecture

**AMQP** (Advanced Message Queuing Protocol): Open standard application layer protocol for message-oriented middleware.

**Key characteristics**:
- **Message broker**: Central hub for routing messages
- **Exchanges**: Route messages to queues based on bindings
- **Queues**: Buffer that stores messages for consumers
- **Bindings**: Rules that link exchanges to queues
- **Routing keys**: Used to match messages to queues
- **Virtual hosts**: Isolated namespaces within a broker
- **Channels**: Lightweight connections sharing a TCP connection

**Message flow**:
```
Publisher → Exchange → Binding → Queue → Consumer
            ↓                      ↓
        Routing Key           Delivery Ack
```

---

## Exchange Types

### 1. Direct Exchange

Routes messages with a specific routing key to queues bound with that exact key.

**Use cases**:
- Task distribution with specific worker types
- Targeted notifications
- Command routing

**Example binding**:
```
Exchange: tasks
Queue: email_tasks   Binding: email
Queue: sms_tasks     Binding: sms
Queue: push_tasks    Binding: push

Message with routing_key="email" → email_tasks queue
```

### 2. Fanout Exchange

Routes messages to all bound queues (ignores routing key).

**Use cases**:
- Broadcasting events to multiple systems
- Cache invalidation across services
- Real-time updates to all subscribers

**Example**:
```
Exchange: notifications
Queue: slack_notifier
Queue: email_notifier
Queue: sms_notifier

All queues receive every message
```

### 3. Topic Exchange

Routes based on wildcard pattern matching of routing keys.

**Use cases**:
- Multi-criteria subscriptions
- Log aggregation with filtering
- Event routing by category

**Patterns**:
- `*` matches exactly one word
- `#` matches zero or more words

**Example**:
```
Routing key: "order.created.us"
Binding: "order.*.*"       → Matches
Binding: "order.created.#" → Matches
Binding: "order.#"         → Matches
Binding: "*.created.*"     → Matches
Binding: "invoice.#"       → No match
```

### 4. Headers Exchange

Routes based on message header attributes instead of routing key.

**Use cases**:
- Complex routing logic
- Multiple attribute matching
- Non-string routing criteria

**Example**:
```
Headers: {type: "order", region: "us", priority: "high"}
Binding: {type: "order", region: "us"}  → Matches if x-match=all
```

---

## Common Patterns

### Pattern 1: Work Queue

**Goal**: Distribute tasks among multiple workers.

**Setup**:
- One queue
- Multiple consumers
- Round-robin distribution (default)

**Python example**:
```python
import pika

# Publisher
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='tasks', durable=True)

channel.basic_publish(
    exchange='',
    routing_key='tasks',
    body='Task data',
    properties=pika.BasicProperties(delivery_mode=2)  # Persistent
)

# Consumer
def callback(ch, method, properties, body):
    print(f"Processing: {body}")
    # Do work...
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)  # Fair dispatch
channel.basic_consume(queue='tasks', on_message_callback=callback)
channel.start_consuming()
```

### Pattern 2: Pub-Sub

**Goal**: Broadcast messages to multiple subscribers.

**Setup**:
- Fanout exchange
- One temporary queue per subscriber
- Auto-delete queues

**Python example**:
```python
# Publisher
channel.exchange_declare(exchange='logs', exchange_type='fanout')
channel.basic_publish(exchange='logs', routing_key='', body='Log message')

# Subscriber
result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue
channel.queue_bind(exchange='logs', queue=queue_name)
channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
```

### Pattern 3: Routing

**Goal**: Subscribe to subset of messages.

**Setup**:
- Direct or topic exchange
- Selective queue bindings

**Python example**:
```python
# Publisher
channel.exchange_declare(exchange='logs', exchange_type='direct')
channel.basic_publish(exchange='logs', routing_key='error', body='Error log')

# Consumer (only error logs)
channel.queue_bind(exchange='logs', queue=queue_name, routing_key='error')
```

### Pattern 4: RPC

**Goal**: Remote procedure calls with response.

**Setup**:
- Request queue
- Temporary reply queue
- Correlation ID to match requests/responses

**Python example**:
```python
# Client
import uuid

class RpcClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue
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
        while self.response is None:
            self.connection.process_data_events()
        return int(self.response)
```

---

## Message Durability

### Making Messages Persistent

**Requirements**:
1. Queue must be durable
2. Message must be marked persistent
3. Exchange durability (recommended)

**Python example**:
```python
# Durable queue
channel.queue_declare(queue='tasks', durable=True)

# Persistent message
channel.basic_publish(
    exchange='',
    routing_key='tasks',
    body='Important task',
    properties=pika.BasicProperties(
        delivery_mode=2,  # Persistent
    )
)
```

**Note**: Persistence doesn't guarantee 100% durability. For stronger guarantees, use publisher confirms.

### Publisher Confirms

Ensure message was written to disk before considering it sent.

**Python example**:
```python
channel.confirm_delivery()

try:
    channel.basic_publish(
        exchange='',
        routing_key='tasks',
        body='Task',
        properties=pika.BasicProperties(delivery_mode=2),
        mandatory=True
    )
    print("Message delivered")
except pika.exceptions.UnroutableError:
    print("Message could not be routed")
```

---

## Acknowledgments

### Manual Acknowledgments

**Consumer should acknowledge** after processing completes.

```python
def callback(ch, method, properties, body):
    try:
        process_message(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        # Requeue on failure
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

channel.basic_consume(
    queue='tasks',
    on_message_callback=callback,
    auto_ack=False  # Manual ack
)
```

### Prefetch Count

Control how many messages delivered to consumer before acknowledgment.

```python
channel.basic_qos(prefetch_count=1)  # One at a time (fair dispatch)
channel.basic_qos(prefetch_count=10) # Batch processing
```

**Best practice**: Use `prefetch_count=1` for long-running tasks to ensure fair distribution.

---

## Dead Letter Exchanges

Route failed messages to another exchange for retry or inspection.

**Setup**:
```python
# Main queue with DLX
channel.queue_declare(
    queue='tasks',
    durable=True,
    arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'failed.tasks',
        'x-message-ttl': 60000  # Optional: TTL before DLX
    }
)

# Dead letter exchange
channel.exchange_declare(exchange='dlx', exchange_type='direct')

# Dead letter queue
channel.queue_declare(queue='failed_tasks', durable=True)
channel.queue_bind(exchange='dlx', queue='failed_tasks', routing_key='failed.tasks')
```

**Messages sent to DLX when**:
- Consumer rejects with `requeue=False`
- Message TTL expires
- Queue length limit reached

---

## High Availability

### Clustering

**Setup** (3-node cluster):
```bash
# Node 1
rabbitmq-server -detached
rabbitmqctl stop_app
rabbitmqctl reset
rabbitmqctl start_app

# Node 2
rabbitmq-server -detached
rabbitmqctl stop_app
rabbitmqctl reset
rabbitmqctl join_cluster rabbit@node1
rabbitmqctl start_app

# Node 3
rabbitmqctl stop_app
rabbitmqctl join_cluster rabbit@node1
rabbitmqctl start_app
```

### Quorum Queues

Replicated queue type with high availability and data safety.

**Python example**:
```python
channel.queue_declare(
    queue='ha_tasks',
    durable=True,
    arguments={
        'x-queue-type': 'quorum'
    }
)
```

**Characteristics**:
- Raft consensus algorithm
- Data replicated across nodes
- Leader election on failure
- Stronger durability guarantees

---

## Performance Optimization

### Connection Pooling

Reuse connections and channels.

```python
import pika.pool

params = pika.ConnectionParameters('localhost')
pool = pika.pool.ConnectionPool(
    lambda: pika.BlockingConnection(params),
    max_size=10,
    max_overflow=20,
    timeout=10,
    recycle=3600
)

with pool.acquire() as connection:
    channel = connection.channel()
    channel.basic_publish(...)
```

### Batch Publishing

Publish multiple messages in one go.

```python
for i in range(1000):
    channel.basic_publish(
        exchange='',
        routing_key='tasks',
        body=f'Task {i}'
    )
# All published in one network round trip
```

### Lazy Queues

Keep messages on disk instead of RAM.

```python
channel.queue_declare(
    queue='large_queue',
    durable=True,
    arguments={'x-queue-mode': 'lazy'}
)
```

**Use when**: Queue has many messages (millions) or messages are large.

---

## Monitoring

### Key Metrics

Monitor these via management API or Prometheus:

**Queue metrics**:
- `messages_ready`: Messages ready for delivery
- `messages_unacknowledged`: Messages delivered but not acked
- `message_stats.publish`: Publish rate
- `message_stats.deliver`: Delivery rate

**Connection metrics**:
- `connection_count`: Active connections
- `channel_count`: Active channels

**Node metrics**:
- `mem_used`: Memory usage
- `fd_used`: File descriptors
- `disk_free`: Available disk space

**Python monitoring example**:
```python
import requests

response = requests.get(
    'http://localhost:15672/api/queues',
    auth=('guest', 'guest')
)
queues = response.json()

for queue in queues:
    print(f"{queue['name']}: {queue['messages']} messages")
```

---

## Best Practices

1. **Use manual acknowledgments** for important messages
2. **Set prefetch_count=1** for long-running tasks
3. **Enable publisher confirms** for critical data
4. **Use quorum queues** for high availability
5. **Monitor queue depths** and set alerts
6. **Use dead letter exchanges** for failed message handling
7. **Set message TTL** to prevent queue buildup
8. **Limit queue length** with `x-max-length`
9. **Use connection pooling** in high-throughput scenarios
10. **Test failure scenarios** (node crashes, network partitions)

---

## Common Pitfalls

1. **Not using durable queues**: Messages lost on broker restart
2. **Auto-acknowledgment**: Messages lost if consumer crashes
3. **No prefetch limit**: All messages delivered to one consumer
4. **Not handling connection errors**: Application crashes on network issues
5. **Publishing to non-existent exchange**: Messages silently dropped
6. **Not monitoring**: Queue buildup goes unnoticed
7. **Ignoring memory alarms**: Broker blocks publishers
8. **Too many connections**: File descriptor exhaustion

---

## Resources

- **Documentation**: https://www.rabbitmq.com/documentation.html
- **AMQP 0-9-1 Reference**: https://www.rabbitmq.com/amqp-0-9-1-reference.html
- **Management API**: https://www.rabbitmq.com/management.html
- **Monitoring**: https://www.rabbitmq.com/monitoring.html
- **Clustering**: https://www.rabbitmq.com/clustering.html
