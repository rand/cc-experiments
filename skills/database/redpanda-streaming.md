---
name: redpanda-streaming
description: **Redpanda deployments**: Setting up Kafka-compatible streaming infrastructure
---


# Redpanda Streaming Platform

## When to Use This Skill

Activate `redpanda-streaming.md` when working with:

- **Redpanda deployments**: Setting up Kafka-compatible streaming infrastructure
- **Event streaming**: Building real-time data pipelines and event-driven architectures
- **Kafka migration**: Migrating from Apache Kafka to Redpanda
- **Stream processing**: Producing/consuming events at high throughput
- **Schema management**: Using Schema Registry for data contracts
- **HTTP streaming**: REST APIs for Kafka topics via Pandaproxy
- **rpk CLI operations**: Managing topics, ACLs, clusters via command line
- **Performance optimization**: Tuning for low latency and high throughput

**Technology focus**: Redpanda 23.x+, Kafka API compatibility, rpk CLI, Schema Registry, Pandaproxy

## Core Concepts

### What is Redpanda?

**Redpanda** is a Kafka-compatible streaming data platform written in C++ that eliminates complexity:
- **No ZooKeeper**: Uses Raft consensus for coordination
- **No JVM**: C++ implementation with lower latency and memory usage
- **Kafka API compatible**: Drop-in replacement for Kafka clients
- **Built-in features**: Schema Registry, HTTP Proxy, tiered storage included

### Architecture Components

```
┌─────────────────────────────────────────────────────────┐
│                     Redpanda Cluster                    │
├─────────────────────────────────────────────────────────┤
│  Broker 1      Broker 2      Broker 3                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │
│  │ Topics  │  │ Topics  │  │ Topics  │                 │
│  │ Raft    │  │ Raft    │  │ Raft    │                 │
│  └─────────┘  └─────────┘  └─────────┘                 │
└─────────────────────────────────────────────────────────┘
         ↑              ↑              ↑
         │              │              │
    ┌────┴──────┬───────┴────┬─────────┴───┐
    │           │            │             │
Kafka API   Pandaproxy   Schema Reg    rpk CLI
(port 9092) (port 8082)  (port 8081)  (local)
```

### Topics and Partitions

**Topics** are named streams of records (events):
```bash
# Create topic with 3 partitions, replication factor 3
rpk topic create orders -p 3 -r 3

# List topics
rpk topic list

# Describe topic
rpk topic describe orders

# Delete topic
rpk topic delete orders
```

**Partitions** enable parallelism:
- Events with same key → same partition (ordering guarantee)
- Multiple partitions → parallel consumption
- Replication factor → data durability (survive broker failures)

### Producers and Consumers

**Producer** pattern (Python with kafka-python):
```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',  # Wait for all replicas
    retries=3
)

# Produce event
producer.send('orders', value={'order_id': 123, 'amount': 99.99})
producer.flush()
```

**Consumer** pattern (Python):
```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],
    group_id='order-processor',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',  # Start from beginning if no offset
    enable_auto_commit=True
)

for message in consumer:
    order = message.value
    print(f"Processing order {order['order_id']}")
```

### Consumer Groups

**Consumer groups** enable parallel processing:
```bash
# Each consumer in group processes subset of partitions
# Group: order-processor
#   Consumer 1 → Partition 0
#   Consumer 2 → Partition 1
#   Consumer 3 → Partition 2

# View consumer groups
rpk group list

# Describe group (offsets, lag)
rpk group describe order-processor

# Seek to offset
rpk group seek order-processor --to start
rpk group seek order-processor --to end
rpk group seek order-processor --to 1000
```

## Deployment Patterns

### Docker Compose (Development)

```yaml
# docker-compose.yml
version: '3.8'
services:
  redpanda:
    image: redpandadata/redpanda:latest
    command:
      - redpanda start
      - --smp 1
      - --memory 1G
      - --overprovisioned
      - --node-id 0
      - --kafka-addr PLAINTEXT://0.0.0.0:29092,OUTSIDE://0.0.0.0:9092
      - --advertise-kafka-addr PLAINTEXT://redpanda:29092,OUTSIDE://localhost:9092
    ports:
      - "9092:9092"     # Kafka API
      - "8081:8081"     # Schema Registry
      - "8082:8082"     # Pandaproxy (HTTP)
      - "9644:9644"     # Admin API
```

Start with:
```bash
docker-compose up -d
rpk cluster info --brokers localhost:9092
```

### Kubernetes (Production)

```bash
# Install Redpanda operator
helm repo add redpanda https://charts.redpanda.com
helm install redpanda-operator redpanda/redpanda-operator \
  --namespace redpanda-system --create-namespace

# Deploy 3-broker cluster
kubectl apply -f - <<EOF
apiVersion: cluster.redpanda.com/v1alpha1
kind: Redpanda
metadata:
  name: redpanda
spec:
  replicas: 3
  resources:
    requests:
      cpu: "2"
      memory: "8Gi"
  storage:
    capacity: 100Gi
EOF

# Verify cluster
kubectl get redpanda
rpk cluster info --brokers redpanda-0.redpanda.default.svc.cluster.local:9092
```

## Schema Registry

**Schema Registry** enforces data contracts using Avro/Protobuf/JSON Schema:

### Register Schema
```bash
# Register Avro schema for topic 'orders-value'
curl -X POST http://localhost:8081/subjects/orders-value/versions \
  -H 'Content-Type: application/vnd.schemaregistry.v1+json' \
  -d '{
    "schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"order_id\",\"type\":\"int\"},{\"name\":\"amount\",\"type\":\"double\"}]}"
  }'
```

### Python with Schema Registry
```python
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

schema_str = """
{
  "type": "record",
  "name": "Order",
  "fields": [
    {"name": "order_id", "type": "int"},
    {"name": "amount", "type": "double"}
  ]
}
"""

schema_registry_client = SchemaRegistryClient({'url': 'http://localhost:8081'})
avro_serializer = AvroSerializer(schema_registry_client, schema_str)

producer = SerializingProducer({
    'bootstrap.servers': 'localhost:9092',
    'value.serializer': avro_serializer
})

producer.produce('orders', value={'order_id': 123, 'amount': 99.99})
producer.flush()
```

## Pandaproxy (HTTP API)

**Pandaproxy** provides REST API for Kafka operations:

### Produce via HTTP
```bash
curl -X POST http://localhost:8082/topics/orders \
  -H 'Content-Type: application/vnd.kafka.json.v2+json' \
  -d '{
    "records": [
      {"value": {"order_id": 123, "amount": 99.99}}
    ]
  }'
```

### Consume via HTTP
```bash
# Create consumer instance
curl -X POST http://localhost:8082/consumers/order-group \
  -H 'Content-Type: application/vnd.kafka.v2+json' \
  -d '{
    "name": "consumer1",
    "format": "json",
    "auto.offset.reset": "earliest"
  }'

# Subscribe to topic
curl -X POST http://localhost:8082/consumers/order-group/instances/consumer1/subscription \
  -H 'Content-Type: application/vnd.kafka.v2+json' \
  -d '{"topics": ["orders"]}'

# Fetch records
curl http://localhost:8082/consumers/order-group/instances/consumer1/records \
  -H 'Accept: application/vnd.kafka.json.v2+json'
```

## rpk CLI Quick Reference

### Cluster Operations
```bash
# Cluster info
rpk cluster info

# Cluster health
rpk cluster health

# Cluster config
rpk cluster config get
rpk cluster config set log_retention_ms 604800000  # 7 days
```

### Topic Operations
```bash
# Create topic
rpk topic create <topic> -p <partitions> -r <replicas>

# List topics
rpk topic list

# Describe topic (partitions, replicas, config)
rpk topic describe <topic>

# Alter config
rpk topic alter-config <topic> --set retention.ms=3600000

# Delete topic
rpk topic delete <topic>

# Produce to topic
echo '{"key": "value"}' | rpk topic produce <topic>

# Consume from topic
rpk topic consume <topic> --format json
rpk topic consume <topic> --offset start  # From beginning
rpk topic consume <topic> --offset end    # Only new messages
```

### ACL Management
```bash
# Create ACL (allow user 'alice' to read topic 'orders')
rpk acl create --allow-principal User:alice \
  --operation read --topic orders

# List ACLs
rpk acl list

# Delete ACL
rpk acl delete --allow-principal User:alice \
  --operation read --topic orders
```

### Consumer Groups
```bash
# List groups
rpk group list

# Describe group (members, lag)
rpk group describe <group>

# Seek to offset
rpk group seek <group> --to start
rpk group seek <group> --to end
rpk group seek <group> --to 1000

# Delete group
rpk group delete <group>
```

## Performance Tuning

### Producer Optimization
```python
# High throughput configuration
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    acks='1',              # Only leader ack (faster than 'all')
    compression_type='lz4', # Compress batches
    batch_size=32768,      # 32KB batches
    linger_ms=10,          # Wait 10ms to batch more records
    buffer_memory=67108864 # 64MB buffer
)
```

### Consumer Optimization
```python
# High throughput configuration
consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],
    fetch_min_bytes=1024,       # Wait for 1KB before returning
    fetch_max_wait_ms=500,      # Max wait 500ms
    max_partition_fetch_bytes=1048576,  # 1MB per partition
    enable_auto_commit=True,
    auto_commit_interval_ms=5000  # Commit every 5s
)
```

### Broker Tuning
```bash
# Increase retention (7 days)
rpk cluster config set log_retention_ms 604800000

# Increase segment size (1GB)
rpk cluster config set log_segment_size 1073741824

# Enable compression
rpk cluster config set compression.type producer  # Use producer's compression
```

## Monitoring

### Key Metrics (via Admin API)
```bash
# Cluster metrics
curl http://localhost:9644/metrics | grep redpanda

# Important metrics:
# - redpanda_kafka_request_latency_seconds
# - redpanda_kafka_request_bytes_total
# - redpanda_storage_disk_free_bytes
# - redpanda_cluster_partition_count
```

### rpk Monitoring
```bash
# Cluster health
rpk cluster health

# Topic lag
rpk group describe <group>

# Disk usage
rpk cluster info
```

## Kafka Compatibility

Redpanda is **100% Kafka API compatible**:

```python
# Works with any Kafka client library
from kafka import KafkaProducer, KafkaConsumer  # kafka-python
from confluent_kafka import Producer, Consumer  # confluent-kafka-python
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer  # aiokafka

# Just point to Redpanda broker
bootstrap_servers = 'localhost:9092'  # Redpanda instead of Kafka
```

**Migration from Kafka**:
1. Update `bootstrap.servers` to Redpanda brokers
2. No code changes needed
3. Remove ZooKeeper configuration (Redpanda doesn't use it)

## Anti-Patterns

### ❌ Don't: Produce without error handling
```python
# Bad: Silent failures
producer.send('orders', value=order)
```

**✅ Do: Handle errors**
```python
future = producer.send('orders', value=order)
try:
    record_metadata = future.get(timeout=10)
    print(f"Produced to {record_metadata.topic}:{record_metadata.partition}")
except Exception as e:
    print(f"Failed to produce: {e}")
```

### ❌ Don't: Ignore consumer lag
```python
# Bad: No lag monitoring
for message in consumer:
    process(message.value)
```

**✅ Do: Monitor lag and scale**
```bash
# Monitor lag regularly
rpk group describe order-processor

# High lag? Add consumers to group (up to partition count)
```

### ❌ Don't: Use auto-commit without understanding
```python
# Bad: Auto-commit can lose messages on crashes
consumer = KafkaConsumer(enable_auto_commit=True)
```

**✅ Do: Manual commit for critical data**
```python
consumer = KafkaConsumer(enable_auto_commit=False)
for message in consumer:
    process(message.value)
    consumer.commit()  # Commit only after processing
```

### ❌ Don't: Create topics with 1 partition for scalability
```bash
# Bad: Limits to 1 consumer
rpk topic create orders -p 1
```

**✅ Do: Plan partitions based on throughput**
```bash
# Good: 3 partitions → up to 3 parallel consumers
rpk topic create orders -p 3 -r 3
```

### ❌ Don't: Hardcode broker addresses
```python
# Bad: Breaks when brokers change
producer = KafkaProducer(bootstrap_servers=['redpanda-1:9092'])
```

**✅ Do: Use service discovery or env vars**
```python
import os
brokers = os.getenv('REDPANDA_BROKERS', 'localhost:9092')
producer = KafkaProducer(bootstrap_servers=brokers.split(','))
```

## Related Skills

**Core Dependencies**:
- `docker-basics.md` - Container deployment patterns
- `kubernetes-deployment.md` - K8s operator deployment

**Complementary Skills**:
- `kafka-streams.md` - Stream processing with Kafka Streams API
- `flink-streaming.md` - Apache Flink for complex event processing
- `postgres-partitioning.md` - Database patterns for event sourcing
- `observability-patterns.md` - Monitoring and alerting

**Integration Patterns**:
- `fastapi-async.md` - Building async HTTP APIs over Redpanda
- `python-async-patterns.md` - Async producers/consumers with aiokafka
- `go-concurrency.md` - High-performance Go consumers

## Quick Reference

### Common Commands
```bash
# Cluster
rpk cluster info
rpk cluster health
rpk cluster config get

# Topics
rpk topic create <topic> -p 3 -r 3
rpk topic list
rpk topic describe <topic>
rpk topic delete <topic>

# Produce/Consume
echo 'message' | rpk topic produce <topic>
rpk topic consume <topic> --format json

# Consumer Groups
rpk group list
rpk group describe <group>
rpk group seek <group> --to start

# ACLs
rpk acl create --allow-principal User:alice --operation read --topic orders
rpk acl list
```

### Client Configuration (Python)
```python
# Producer (high throughput)
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    acks='all',
    compression_type='lz4',
    batch_size=32768,
    linger_ms=10
)

# Consumer (reliable processing)
consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],
    group_id='order-processor',
    enable_auto_commit=False,
    auto_offset_reset='earliest'
)
```

### Docker Compose Snippet
```yaml
services:
  redpanda:
    image: redpandadata/redpanda:latest
    command:
      - redpanda start
      - --kafka-addr PLAINTEXT://0.0.0.0:29092,OUTSIDE://0.0.0.0:9092
      - --advertise-kafka-addr PLAINTEXT://redpanda:29092,OUTSIDE://localhost:9092
    ports:
      - "9092:9092"
      - "8081:8081"
      - "8082:8082"
```
