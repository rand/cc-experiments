---
name: protocols-kafka-streams
description: Apache Kafka stream processing and event streaming platform
---

# Kafka Streams

**Scope**: Kafka architecture, producers, consumers, Kafka Streams API, exactly-once semantics, schema registry, ksqlDB
**Lines**: ~300
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Building real-time data pipelines with Kafka
- Implementing event-driven architectures
- Processing streams with Kafka Streams or ksqlDB
- Ensuring exactly-once message delivery
- Using Avro/Protobuf with Schema Registry
- Monitoring consumer lag and cluster health
- Optimizing Kafka performance and throughput

## Core Concepts

### What is Apache Kafka?

**Apache Kafka**: Distributed event streaming platform
- **High-throughput messaging**: Millions of messages/sec
- **Durable storage**: Messages persisted to disk with replication
- **Stream processing**: Real-time data transformation (Kafka Streams, ksqlDB)
- **Scalable**: Horizontal scaling with partitions and brokers

**Use cases**:
- Event sourcing and CQRS
- Real-time analytics and monitoring
- Log aggregation and metrics collection
- Microservices communication
- Data integration (CDC, ETL)

### Architecture Components

**Topic**: Logical stream of records (like a table)
- Messages organized into ordered log
- Immutable append-only structure

**Partition**: Ordered sequence of messages within topic
- Enable parallelism (multiple consumers)
- Messages in partition are ordered
- Key-based routing ensures same key → same partition

**Broker**: Kafka server instance
- Stores data for partitions
- Handles reads/writes
- Cluster has multiple brokers (3-5+ for production)

**Producer**: Publishes messages to topics
**Consumer**: Reads messages from topics
**Consumer Group**: Set of consumers sharing topic partitions

```
Producer → Topic (Partitions) → Consumer Group → Consumers
                   ↓
            Replication (ISR)
```

---

## Basic Producer/Consumer

### Producer (Python)

```python
from kafka import KafkaProducer
import json

# Create producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',  # Wait for all in-sync replicas
    retries=3,
    compression_type='lz4'
)

# Send message
producer.send(
    'orders',
    key='order-123',
    value={'order_id': 'order-123', 'amount': 99.99}
)

# Flush and close
producer.flush()
producer.close()
```

### Consumer (Python)

```python
from kafka import KafkaConsumer
import json

# Create consumer
consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],
    group_id='order-processor',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=False  # Manual commit for reliability
)

# Consume messages
for message in consumer:
    print(f"Partition: {message.partition}, Offset: {message.offset}")
    print(f"Value: {message.value}")

    # Process message
    process_order(message.value)

    # Commit after processing (at-least-once)
    consumer.commit()

consumer.close()
```

---

## Kafka Streams API

### Stream Processing (Java)

```java
import org.apache.kafka.streams.*;
import org.apache.kafka.streams.kstream.*;

Properties props = new Properties();
props.put(StreamsConfig.APPLICATION_ID_CONFIG, "word-count-app");
props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");

StreamsBuilder builder = new StreamsBuilder();

// Input topic
KStream<String, String> textLines = builder.stream("text-input");

// Process: split words → count
KTable<String, Long> wordCounts = textLines
    .flatMapValues(line -> Arrays.asList(line.split("\\s+")))
    .groupBy((key, word) -> word)
    .count();

// Output topic
wordCounts.toStream().to("word-count-output");

// Start streams app
KafkaStreams streams = new KafkaStreams(builder.build(), props);
streams.start();
```

### Stateless Operations

```java
// Filter
KStream<String, Integer> evens = stream.filter((k, v) -> v % 2 == 0);

// Map
KStream<String, String> upper = stream.mapValues(v -> v.toUpperCase());

// FlatMap
KStream<String, String> words = stream.flatMapValues(
    line -> Arrays.asList(line.split("\\s+"))
);

// Branch (split stream)
KStream<String, Integer>[] branches = stream.branch(
    (k, v) -> v > 0,   // Positive
    (k, v) -> v < 0,   // Negative
    (k, v) -> true     // Zero
);
```

### Stateful Operations

```java
// Group and count
KTable<String, Long> counts = stream
    .groupByKey()
    .count();

// Aggregate
KTable<String, Integer> sums = stream
    .groupByKey()
    .reduce((aggValue, newValue) -> aggValue + newValue);

// Custom aggregation
KTable<String, Stats> stats = stream
    .groupByKey()
    .aggregate(
        Stats::new,  // Initializer
        (key, value, aggregate) -> {
            aggregate.sum += value;
            aggregate.count++;
            return aggregate;
        }
    );
```

### Windowing

```java
// Tumbling window (5 minutes)
KTable<Windowed<String>, Long> counts = stream
    .groupByKey()
    .windowedBy(TimeWindows.of(Duration.ofMinutes(5)))
    .count();

// Hopping window
KTable<Windowed<String>, Long> counts = stream
    .groupByKey()
    .windowedBy(TimeWindows.of(Duration.ofMinutes(10))
                           .advanceBy(Duration.ofMinutes(5)))
    .count();

// Session window (30-minute inactivity gap)
KTable<Windowed<String>, Long> sessions = stream
    .groupByKey()
    .windowedBy(SessionWindows.with(Duration.ofMinutes(30)))
    .count();
```

---

## Exactly-Once Semantics

### Transactional Producer (Python)

```python
from kafka import KafkaProducer

# Create transactional producer
producer = KafkaProducer(
    transactional_id='order-service-1',  # Unique ID
    enable_idempotence=True,
    acks='all'
)

# Initialize transactions
producer.init_transactions()

try:
    # Begin transaction
    producer.begin_transaction()

    # Send messages (atomic across topics)
    producer.send('orders', order_data)
    producer.send('payments', payment_data)

    # Commit transaction
    producer.commit_transaction()

except Exception as e:
    # Rollback on error
    producer.abort_transaction()
```

### Exactly-Once Streams

```java
// Enable exactly-once in Kafka Streams
props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG,
          StreamsConfig.EXACTLY_ONCE_V2);

// Streams app now has exactly-once guarantees:
// - Output writes are transactional
// - State stores are consistent
// - Offset commits are atomic
```

---

## Schema Registry (Avro)

### Producer with Avro

```python
from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer

# Define schema
user_schema = avro.loads('''
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "string"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": "string"},
    {"name": "age", "type": ["null", "int"], "default": null}
  ]
}
''')

# Create producer
producer = AvroProducer({
    'bootstrap.servers': 'localhost:9092',
    'schema.registry.url': 'http://localhost:8081'
}, default_value_schema=user_schema)

# Send message (Avro serialization automatic)
user = {
    'id': 'user-1',
    'name': 'Alice',
    'email': 'alice@example.com',
    'age': 30
}
producer.produce(topic='users', value=user)
producer.flush()
```

### Consumer with Avro

```python
from confluent_kafka.avro import AvroConsumer

consumer = AvroConsumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'user-consumer',
    'schema.registry.url': 'http://localhost:8081'
})

consumer.subscribe(['users'])

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue

    # Value automatically deserialized
    user = msg.value()
    print(f"User: {user['name']} ({user['email']})")
```

---

## ksqlDB

### Basic Queries

```sql
-- Create stream from topic
CREATE STREAM user_events (
  user_id VARCHAR,
  action VARCHAR,
  timestamp BIGINT
) WITH (
  KAFKA_TOPIC='user-events',
  VALUE_FORMAT='JSON'
);

-- Query stream (continuous)
SELECT * FROM user_events EMIT CHANGES;

-- Create table (aggregation)
CREATE TABLE event_counts AS
SELECT user_id, COUNT(*) AS count
FROM user_events
GROUP BY user_id
EMIT CHANGES;

-- Query table (point-in-time)
SELECT * FROM event_counts WHERE user_id='user123';
```

### Windowing

```sql
-- Tumbling window (5 minutes)
CREATE TABLE event_counts_5min AS
SELECT
  user_id,
  COUNT(*) AS count,
  WINDOWSTART AS window_start
FROM user_events
WINDOW TUMBLING (SIZE 5 MINUTES)
GROUP BY user_id
EMIT CHANGES;

-- Session window (30-minute gap)
CREATE TABLE user_sessions AS
SELECT user_id, COUNT(*) AS event_count
FROM user_events
WINDOW SESSION (30 MINUTES)
GROUP BY user_id
EMIT CHANGES;
```

### Joins

```sql
-- Stream-stream join
CREATE STREAM order_payments AS
SELECT
  o.order_id,
  o.amount,
  p.payment_id,
  p.status
FROM orders o
INNER JOIN payments p WITHIN 1 HOUR
ON o.order_id = p.order_id
EMIT CHANGES;

-- Stream-table join (enrichment)
CREATE STREAM enriched_orders AS
SELECT
  o.order_id,
  o.amount,
  u.name AS user_name,
  u.email AS user_email
FROM orders o
LEFT JOIN users u ON o.user_id = u.user_id
EMIT CHANGES;
```

---

## Performance Tuning

### Producer Tuning

**High throughput**:
```python
producer = KafkaProducer(
    acks=1,  # Leader only
    compression_type='lz4',
    batch_size=32768,  # 32 KB
    linger_ms=20,  # Wait to batch
    buffer_memory=67108864  # 64 MB
)
```

**High reliability**:
```python
producer = KafkaProducer(
    acks='all',  # All ISR
    enable_idempotence=True,
    retries=3,
    max_in_flight_requests_per_connection=5
)
```

### Consumer Tuning

**High throughput**:
```python
consumer = KafkaConsumer(
    fetch_min_bytes=1048576,  # 1 MB
    max_poll_records=1000
)
```

**Low latency**:
```python
consumer = KafkaConsumer(
    fetch_min_bytes=1,
    fetch_max_wait_ms=0
)
```

---

## Monitoring

### Key Metrics

**Broker health**:
- `UnderReplicatedPartitions`: Should be 0
- `OfflinePartitionsCount`: Should be 0
- `ActiveControllerCount`: Should be 1

**Producer**:
- `record-send-rate`: Messages/sec
- `record-error-rate`: Errors/sec
- `request-latency-avg`: Latency in ms

**Consumer**:
- `records-lag-max`: Max lag across partitions
- `records-consumed-rate`: Messages/sec
- `fetch-latency-avg`: Fetch latency

### Consumer Lag

```bash
# Check consumer lag
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group my-group --describe

# Output:
# TOPIC    PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
# orders   0          1000            1500            500
# orders   1          2000            2000            0
```

**Thresholds**:
- Lag < 1000: Healthy
- Lag 1000-10000: Warning
- Lag > 10000: Critical

---

## Common Patterns

### Partitioning Strategies

**Key-based** (ordering guarantee):
```python
producer.send('orders', key='user123', value=data)
# Same key → same partition → ordering preserved
```

**Custom partitioner**:
```python
from kafka.partitioner import Partitioner

class VIPPartitioner(Partitioner):
    def partition(self, key, all_partitions, available):
        if key.startswith('vip_'):
            return 0  # VIP users to partition 0
        return hash(key) % len(all_partitions)
```

### Offset Management

**Auto-commit** (at-most-once):
```python
consumer = KafkaConsumer(enable_auto_commit=True)
# Simple, but can lose data on crash
```

**Manual commit** (at-least-once):
```python
consumer = KafkaConsumer(enable_auto_commit=False)
for msg in consumer:
    process(msg)
    consumer.commit()  # Commit after processing
```

**Batch commit** (throughput):
```python
for i, msg in enumerate(consumer):
    process(msg)
    if i % 100 == 0:
        consumer.commit()
```

---

## Anti-Patterns

❌ **Creating producer per message**: Expensive connection overhead
✅ Create once, reuse for all messages

❌ **Not setting timeouts**: Can hang forever
✅ Always set `request_timeout_ms`, `timeout` parameters

❌ **Large messages (> 1 MB)**: Performance issues
✅ Split into smaller messages or use compression

❌ **No replication**: Data loss on broker failure
✅ Use `replication.factor=3`, `min.insync.replicas=2`

❌ **Too many partitions**: Overhead, slow rebalancing
✅ Start with 10-100 partitions per topic

❌ **Ignoring consumer lag**: Consumers falling behind
✅ Monitor lag, alert on thresholds, scale consumers

---

## Level 3: Resources

### Overview

This skill includes comprehensive Level 3 resources for deep Kafka knowledge and practical automation tools.

**Resources include**:
- **REFERENCE.md** (2,438 lines): Complete technical reference covering all Kafka concepts
- **3 executable scripts**: Config validation, consumer lag analysis, throughput benchmarking
- **9 production examples**: Complete implementations in Python, Java, with Docker stack

### REFERENCE.md

**Location**: `skills/protocols/kafka-streams/resources/REFERENCE.md`

**Comprehensive technical reference** (2,438 lines) covering:

**Core Topics**:
- Kafka fundamentals and architecture
- Producer API (Python, Java) - sync, async, batching, transactions
- Consumer API - offset management, rebalancing, partition control
- Kafka Streams API - stateless/stateful operations, windowing, joins
- Exactly-once semantics (EOS) - transactions, idempotence
- Schema Registry - Avro, Protobuf, JSON Schema evolution
- ksqlDB - streams, tables, windowing, joins, aggregations
- Performance tuning - producer/consumer/broker optimization
- Monitoring - JMX metrics, Prometheus, consumer lag
- Security - SASL, TLS, ACLs
- Testing - unit testing, integration testing, Testcontainers

**Key Sections**:
1. **Fundamentals**: Topics, partitions, brokers, replication, ISR
2. **Producer API**: Configuration, partitioning, batching, compression
3. **Consumer API**: Groups, offset management, rebalancing
4. **Kafka Streams**: Topology, stateless/stateful ops, state stores
5. **Windowing**: Tumbling, hopping, sliding, session windows
6. **Joins**: Stream-stream, stream-table, table-table joins
7. **Exactly-Once**: Transactional producer, idempotent writes, EOS v2
8. **Schema Registry**: Avro schemas, backward/forward compatibility
9. **ksqlDB**: SQL queries, push/pull queries, materialized views
10. **Performance**: Throughput vs latency tuning, partition sizing
11. **Monitoring**: Key metrics, alerting thresholds, lag monitoring
12. **Security**: Authentication (SASL), encryption (TLS), authorization (ACLs)

**Format**: Markdown with extensive code examples in Python, Java

### Scripts

Three production-ready executable scripts in `resources/scripts/`:

#### 1. validate_kafka_config.py (588 lines)

**Purpose**: Validate Kafka broker and topic configurations against best practices

**Features**:
- Parse and validate broker configs (threads, buffers, replication)
- Check topic settings (partitions, replication factor, ISR)
- Detect misconfigurations (low replication, missing ISR)
- Validate cluster health (active controller, broker count)
- Output as JSON or human-readable text

**Usage**:
```bash
# Validate entire cluster
./validate_kafka_config.py --bootstrap-servers localhost:9092

# Validate specific topics
./validate_kafka_config.py --bootstrap-servers localhost:9092 --topics orders,payments

# JSON output for CI/CD
./validate_kafka_config.py --bootstrap-servers localhost:9092 --json > report.json
```

**Categories checked**:
- Cluster health (broker count, active controller)
- Broker configs (network threads, I/O threads, buffers)
- Topic configs (partitions, replication factor, min.insync.replicas)
- Retention policies (log retention, cleanup policy)

#### 2. analyze_consumer_lag.py (537 lines)

**Purpose**: Monitor and analyze consumer lag across consumer groups

**Features**:
- Calculate lag per partition (current offset vs end offset)
- Identify slow consumers and stuck partitions
- Aggregate lag by consumer group
- Classify groups (healthy, warning, critical)
- Output lag statistics and trends

**Usage**:
```bash
# Analyze all consumer groups
./analyze_consumer_lag.py --bootstrap-servers localhost:9092

# Analyze specific group
./analyze_consumer_lag.py --bootstrap-servers localhost:9092 --group order-processor

# Custom lag threshold
./analyze_consumer_lag.py --bootstrap-servers localhost:9092 --threshold 5000

# JSON output for monitoring systems
./analyze_consumer_lag.py --bootstrap-servers localhost:9092 --json
```

**Metrics**:
- Total lag per group
- Max partition lag
- Stuck partitions (not consuming)
- Slow consumers (high lag per consumer)

**Thresholds**:
- Healthy: lag < 1000
- Warning: lag 1000-10000
- Critical: lag > 10000

#### 3. benchmark_throughput.py (620 lines)

**Purpose**: Benchmark Kafka producer/consumer throughput and latency

**Features**:
- Producer benchmark (messages/sec, MB/sec)
- Consumer benchmark (end-to-end latency)
- Latency percentiles (p50, p95, p99)
- Configurable message size and count
- JSON output for automation

**Usage**:
```bash
# Producer benchmark (100k messages)
./benchmark_throughput.py --bootstrap-servers localhost:9092 --mode producer --messages 100000

# Consumer benchmark
./benchmark_throughput.py --bootstrap-servers localhost:9092 --mode consumer --topic orders

# End-to-end benchmark (producer + consumer)
./benchmark_throughput.py --bootstrap-servers localhost:9092 --mode both --messages 50000

# Custom message size (10 KB)
./benchmark_throughput.py --bootstrap-servers localhost:9092 --mode producer --messages 10000 --size 10240

# JSON output
./benchmark_throughput.py --bootstrap-servers localhost:9092 --mode producer --messages 10000 --json
```

**Metrics**:
- Throughput: messages/sec, MB/sec
- Latency: min, avg, p50, p95, p99, max
- Success rate and error count

### Examples

Nine production-ready examples in `resources/examples/`:

#### 1. python/basic_producer.py (200 lines)

Complete Python producer demonstrating:
- Synchronous send (blocking, low throughput)
- Asynchronous send (non-blocking, high throughput)
- Batch send (highest throughput)
- Send with headers (metadata)
- Error handling and callbacks
- Production-ready configuration

#### 2. python/basic_consumer.py (280 lines)

Complete Python consumer demonstrating:
- Auto-commit (at-most-once)
- Manual commit (at-least-once)
- Batch commit (throughput)
- Manual partition assignment
- Multiple topic subscription
- Header access
- Production-ready configuration

#### 3. python/exactly_once_producer.py (180 lines)

Transactional producer with exactly-once semantics:
- Transactional ID and initialization
- Begin/commit/abort transactions
- Atomic writes across multiple topics
- Error handling and rollback
- Multiple transaction sequence

#### 4. python/avro_schema_registry.py (220 lines)

Avro serialization with Schema Registry:
- Define Avro schemas (V1, V2 with evolution)
- Producer with Avro serialization
- Consumer with Avro deserialization
- Complex schemas (enums, arrays, nested records)
- Schema evolution (backward/forward compatible)

#### 5. java/WordCountStreamsApp.java (200 lines)

Kafka Streams application (Java):
- Complete word count topology
- Stateless operations (filter, map, flatMap)
- Stateful operations (groupBy, count, aggregate)
- Advanced topology with windowing and joins
- Exactly-once processing (EOS v2)
- State stores and changelog topics

#### 6. ksqldb/queries.sql (500 lines)

Comprehensive ksqlDB query examples:
- Create streams and tables
- Filter and transform data
- Aggregations (count, sum, avg)
- Windowing (tumbling, hopping, session)
- Joins (stream-stream, stream-table, table-table)
- Advanced functions (string, date/time, conditional)
- Push and pull queries
- Management commands

#### 7. docker/docker-compose.yml (280 lines)

Complete Kafka stack with Docker Compose:
- Kafka broker (with JMX monitoring)
- ZooKeeper
- Schema Registry
- Kafka Connect
- ksqlDB server and CLI
- Control Center (Web UI)
- REST Proxy
- Production-ready configuration with health checks

**Services**:
- Kafka: localhost:9092
- Schema Registry: http://localhost:8081
- ksqlDB: http://localhost:8088
- Control Center: http://localhost:9021
- REST Proxy: http://localhost:8082

#### 8. monitoring/prometheus_config.yml (250 lines)

Prometheus configuration for Kafka monitoring:
- Scrape configs for broker, ZooKeeper, Schema Registry
- Alert rules (under-replicated partitions, high lag, offline partitions)
- Consumer lag monitoring
- JMX metrics collection
- Grafana dashboard integration

**Key alerts**:
- Broker down
- Under-replicated partitions
- Offline partitions
- No active controller
- High consumer lag
- Critical consumer lag

#### 9. examples/README.md (420 lines)

Comprehensive guide with:
- Quick start instructions
- Example usage for each pattern
- Configuration tuning guidelines
- Troubleshooting common issues
- Best practices checklist

### Quick Start

**1. Validate Kafka cluster**:
```bash
cd skills/protocols/kafka-streams/resources/scripts
./validate_kafka_config.py --bootstrap-servers localhost:9092 --json
```

**2. Monitor consumer lag**:
```bash
./analyze_consumer_lag.py --bootstrap-servers localhost:9092 --group my-group
```

**3. Benchmark throughput**:
```bash
./benchmark_throughput.py --bootstrap-servers localhost:9092 --mode both --messages 10000
```

**4. Run examples with Docker**:
```bash
cd ../examples/docker
docker-compose up -d

# Wait for services
docker-compose logs -f kafka

# Access Control Center: http://localhost:9021
```

**5. Test producer/consumer**:
```bash
cd ../examples/python
python basic_producer.py
python basic_consumer.py  # In another terminal
```

### File Structure

```
skills/protocols/kafka-streams/
├── kafka-streams.md (this file)
└── resources/
    ├── REFERENCE.md (2,438 lines)
    ├── scripts/
    │   ├── validate_kafka_config.py (588 lines)
    │   ├── analyze_consumer_lag.py (537 lines)
    │   └── benchmark_throughput.py (620 lines)
    └── examples/
        ├── README.md (420 lines)
        ├── python/
        │   ├── basic_producer.py (200 lines)
        │   ├── basic_consumer.py (280 lines)
        │   ├── exactly_once_producer.py (180 lines)
        │   └── avro_schema_registry.py (220 lines)
        ├── java/
        │   └── WordCountStreamsApp.java (200 lines)
        ├── ksqldb/
        │   └── queries.sql (500 lines)
        ├── docker/
        │   └── docker-compose.yml (280 lines)
        └── monitoring/
            └── prometheus_config.yml (250 lines)
```

### Resources Summary

| Category | Item | Lines | Description |
|----------|------|-------|-------------|
| **Reference** | REFERENCE.md | 2,438 | Complete technical reference |
| **Scripts** | validate_kafka_config.py | 588 | Config validator |
| | analyze_consumer_lag.py | 537 | Lag analyzer |
| | benchmark_throughput.py | 620 | Throughput benchmark |
| **Examples** | basic_producer.py | 200 | Producer patterns |
| | basic_consumer.py | 280 | Consumer patterns |
| | exactly_once_producer.py | 180 | Transactions |
| | avro_schema_registry.py | 220 | Schema Registry |
| | WordCountStreamsApp.java | 200 | Kafka Streams |
| | queries.sql | 500 | ksqlDB queries |
| | docker-compose.yml | 280 | Docker stack |
| | prometheus_config.yml | 250 | Monitoring |
| | README.md | 420 | Examples guide |

**Total**: 6,713 lines of production-ready resources

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
