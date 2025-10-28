# Kafka Streams - Complete Technical Reference

**Version**: 1.0
**Last Updated**: 2025-10-27
**Kafka Versions**: 3.0+
**Lines**: ~3,500

## Table of Contents

1. [Kafka Fundamentals](#1-kafka-fundamentals)
2. [Kafka Architecture](#2-kafka-architecture)
3. [Producer API](#3-producer-api)
4. [Consumer API](#4-consumer-api)
5. [Kafka Streams API](#5-kafka-streams-api)
6. [Stateful Operations](#6-stateful-operations)
7. [Windowing](#7-windowing)
8. [Joins](#8-joins)
9. [Exactly-Once Semantics](#9-exactly-once-semantics)
10. [Schema Registry](#10-schema-registry)
11. [ksqlDB](#11-ksqldb)
12. [Performance Tuning](#12-performance-tuning)
13. [Monitoring](#13-monitoring)
14. [Security](#14-security)
15. [Testing](#15-testing)
16. [Anti-Patterns](#16-anti-patterns)
17. [Reference](#17-reference)

---

## 1. Kafka Fundamentals

### What is Apache Kafka?

**Apache Kafka** is a distributed event streaming platform for:
- **High-throughput messaging**: Millions of messages per second
- **Event streaming**: Real-time data pipelines
- **Log aggregation**: Centralized logging
- **Stream processing**: Real-time analytics

**Core use cases**:
- Event sourcing and CQRS
- Real-time analytics and monitoring
- Data integration (CDC, ETL)
- Microservices communication
- Log aggregation

### Key Characteristics

**Performance**:
- **Throughput**: 1M+ messages/sec per broker
- **Latency**: Single-digit milliseconds (p99)
- **Scalability**: Horizontal scaling (add brokers)
- **Durability**: Replicated, persistent storage

**Architecture**:
- **Distributed**: Multiple brokers in a cluster
- **Fault-tolerant**: Replication and automatic failover
- **Persistent**: Messages stored on disk
- **Scalable**: Partitioning for parallelism

### Core Concepts

**Topic**: Named stream of records (like a database table)
```
Topic: "user-events"
├── Partition 0: [msg1, msg2, msg3, ...]
├── Partition 1: [msg4, msg5, msg6, ...]
└── Partition 2: [msg7, msg8, msg9, ...]
```

**Partition**: Ordered, immutable sequence of messages
- Messages appended sequentially (log structure)
- Each message has an offset (position in partition)
- Partitions enable parallelism

**Broker**: Kafka server that stores data
- Cluster has multiple brokers (e.g., 3-5 for small, 10+ for large)
- Each broker handles multiple partitions

**Producer**: Publishes messages to topics
```python
producer.send("user-events", key="user123", value={"action": "login"})
```

**Consumer**: Reads messages from topics
```python
consumer.subscribe(["user-events"])
for message in consumer:
    process(message.value)
```

**Consumer Group**: Group of consumers sharing work
- Each partition consumed by exactly one consumer in the group
- Enables parallel processing

### Message Structure

```json
{
  "topic": "user-events",
  "partition": 0,
  "offset": 12345,
  "timestamp": 1698432000000,
  "key": "user123",
  "value": {
    "user_id": "user123",
    "action": "login",
    "timestamp": "2025-10-27T10:00:00Z"
  },
  "headers": {
    "correlation-id": "abc-123",
    "source": "web-app"
  }
}
```

**Components**:
- **Key**: Optional, used for partitioning and compaction
- **Value**: Message payload (bytes, JSON, Avro, Protobuf)
- **Headers**: Metadata (key-value pairs)
- **Timestamp**: Message creation time
- **Offset**: Position in partition (auto-incremented)
- **Partition**: Which partition (determined by key hash)

---

## 2. Kafka Architecture

### Cluster Architecture

```
┌─────────────────────────────────────────────────┐
│              ZooKeeper / KRaft                  │
│         (Metadata & Coordination)               │
└─────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│                Kafka Cluster                    │
├─────────────┬──────────────┬───────────────────┤
│  Broker 1   │   Broker 2   │    Broker 3       │
│  Leader P0  │   Leader P1  │    Leader P2      │
│ Follower P1 │  Follower P2 │   Follower P0     │
│ Follower P2 │  Follower P0 │   Follower P1     │
└─────────────┴──────────────┴───────────────────┘
       ↑                ↑               ↑
       │                │               │
   Producer         Producer        Consumer
```

### Topics and Partitions

**Topic**: Logical stream of events
```
Topic: "orders"
├── Partition 0: [order1, order4, order7] → Broker 1 (Leader)
├── Partition 1: [order2, order5, order8] → Broker 2 (Leader)
└── Partition 2: [order3, order6, order9] → Broker 3 (Leader)
```

**Partition assignment**:
```python
# Key-based partitioning (same key → same partition)
partition = hash(key) % num_partitions

# Round-robin (no key)
partition = next_partition()
```

**Why partitions?**
- **Parallelism**: Multiple consumers read different partitions
- **Scalability**: Distribute load across brokers
- **Ordering**: Messages within partition are ordered

### Replication

**Replication factor**: Number of copies per partition
```
Topic: "orders" (replication factor = 3)

Partition 0:
├── Leader: Broker 1 (handles reads/writes)
├── Follower: Broker 2 (replica)
└── Follower: Broker 3 (replica)

Partition 1:
├── Leader: Broker 2
├── Follower: Broker 1
└── Follower: Broker 3
```

**In-Sync Replicas (ISR)**:
- Followers that are up-to-date with the leader
- Writes acknowledged when ISR replicates message
- If leader fails, ISR follower becomes new leader

**Configuration**:
```properties
# Replication factor (set when creating topic)
replication.factor=3

# Minimum in-sync replicas (durability guarantee)
min.insync.replicas=2

# Acks: 0 (no wait), 1 (leader only), all (ISR)
acks=all
```

**Trade-offs**:
- **Replication factor 1**: Fast, but no fault tolerance
- **Replication factor 3**: Durable, but higher disk usage
- **min.insync.replicas=2**: Tolerate 1 broker failure

### ZooKeeper vs KRaft

**ZooKeeper** (legacy, pre-Kafka 3.0):
- External dependency for metadata
- Stores topic configs, broker info, leader election
- Operational complexity

**KRaft** (Kafka 3.0+, production-ready in 3.3+):
- Kafka Raft metadata mode (no ZooKeeper)
- Simpler deployment, faster leader election
- Uses internal Raft consensus protocol

```bash
# KRaft mode (Kafka 3.3+)
$ kafka-storage.sh format -t <cluster-id> -c server.properties
$ kafka-server-start.sh server.properties
```

### Consumer Groups

**Consumer group**: Set of consumers sharing topic partitions

```
Topic: "orders" (3 partitions)

Consumer Group "checkout-service":
├── Consumer 1 → Partition 0
├── Consumer 2 → Partition 1
└── Consumer 3 → Partition 2

Consumer Group "analytics-service":
├── Consumer A → Partitions 0, 1, 2
```

**Rebalancing**: Reassigning partitions when consumers join/leave
- **Stop-the-world**: All consumers stop during rebalance (older protocol)
- **Incremental**: Minimal disruption (cooperative protocol, Kafka 2.4+)

**Offsets**: Track consumer position in each partition
```python
# Commit offset manually
consumer.commit()

# Auto-commit (every 5 seconds by default)
auto.commit.interval.ms=5000
```

---

## 3. Producer API

### Basic Producer (Python)

**Installation**:
```bash
pip install kafka-python
```

**Simple producer**:
```python
from kafka import KafkaProducer
import json

# Create producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Send message
future = producer.send(
    'user-events',
    key=b'user123',
    value={'action': 'login', 'timestamp': '2025-10-27T10:00:00Z'}
)

# Block until sent (synchronous)
record_metadata = future.get(timeout=10)
print(f"Sent to partition {record_metadata.partition} at offset {record_metadata.offset}")

# Close producer
producer.close()
```

### Producer Configuration

```python
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],

    # Serialization
    key_serializer=lambda k: k.encode('utf-8'),
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),

    # Durability
    acks='all',  # Wait for all in-sync replicas

    # Retries
    retries=3,
    retry_backoff_ms=100,

    # Batching (performance)
    batch_size=16384,  # 16 KB
    linger_ms=10,  # Wait up to 10ms to batch messages

    # Compression
    compression_type='gzip',  # None, gzip, snappy, lz4, zstd

    # Idempotence (exactly-once producer)
    enable_idempotence=True,

    # Buffer
    buffer_memory=33554432,  # 32 MB
    max_block_ms=60000  # Block for 60s if buffer full
)
```

**Key parameters**:
- **acks**: Acknowledgment policy
  - `0`: No ack (fast, but can lose data)
  - `1`: Leader ack (balance)
  - `all`: All ISR ack (durable)

- **retries**: Automatic retry on failure
- **enable_idempotence**: Prevents duplicate messages on retry
- **batch_size**: Batch multiple messages (throughput)
- **linger_ms**: Wait to batch (latency/throughput trade-off)
- **compression_type**: Reduce network/disk usage

### Partitioning Strategies

**1. Key-based partitioning** (default):
```python
# Same key → same partition (ordering guarantee)
producer.send('orders', key='user123', value=order_data)
```

**2. Custom partitioner**:
```python
from kafka.partitioner import Partitioner

class CustomPartitioner(Partitioner):
    def partition(self, key, all_partitions, available_partitions):
        # Route VIP users to partition 0
        if key.startswith(b'vip_'):
            return 0
        # Others: hash-based
        return hash(key) % len(all_partitions)

producer = KafkaProducer(
    partitioner=CustomPartitioner()
)
```

**3. Round-robin** (no key):
```python
# No key → round-robin across partitions
producer.send('logs', value=log_data)
```

### Async Send with Callback

```python
def on_send_success(record_metadata):
    print(f"Sent to {record_metadata.topic}:{record_metadata.partition} at {record_metadata.offset}")

def on_send_error(exception):
    print(f"Error: {exception}")

# Async send
producer.send('orders', value=order_data).add_callback(on_send_success).add_errback(on_send_error)

# Flush (ensure all sent)
producer.flush()
```

### Headers

```python
# Add metadata headers
producer.send(
    'user-events',
    key=b'user123',
    value={'action': 'login'},
    headers=[
        ('correlation-id', b'abc-123'),
        ('source', b'web-app'),
        ('version', b'1.0')
    ]
)
```

### Transactions (Exactly-Once)

```python
producer = KafkaProducer(
    transactional_id='order-service-1',
    enable_idempotence=True,
    acks='all'
)

# Initialize transactions
producer.init_transactions()

try:
    # Begin transaction
    producer.begin_transaction()

    # Send messages
    producer.send('orders', value={'order_id': 1})
    producer.send('payments', value={'payment_id': 1})

    # Commit transaction (atomic)
    producer.commit_transaction()
except Exception as e:
    # Rollback on error
    producer.abort_transaction()
    raise e
```

### Java Producer

```java
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");
props.put("acks", "all");
props.put("retries", 3);
props.put("enable.idempotence", true);

Producer<String, String> producer = new KafkaProducer<>(props);

// Send message
ProducerRecord<String, String> record = new ProducerRecord<>(
    "user-events",
    "user123",
    "{\"action\": \"login\"}"
);

producer.send(record, (metadata, exception) -> {
    if (exception == null) {
        System.out.printf("Sent to partition %d at offset %d%n",
            metadata.partition(), metadata.offset());
    } else {
        exception.printStackTrace();
    }
});

producer.close();
```

---

## 4. Consumer API

### Basic Consumer (Python)

```python
from kafka import KafkaConsumer
import json

# Create consumer
consumer = KafkaConsumer(
    'user-events',
    bootstrap_servers=['localhost:9092'],
    group_id='analytics-service',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',  # Start from beginning if no offset
    enable_auto_commit=True
)

# Consume messages
for message in consumer:
    print(f"Partition: {message.partition}, Offset: {message.offset}")
    print(f"Key: {message.key}, Value: {message.value}")

    # Process message
    process_event(message.value)

consumer.close()
```

### Consumer Configuration

```python
consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],

    # Consumer group
    group_id='order-processor',

    # Deserialization
    key_deserializer=lambda k: k.decode('utf-8'),
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),

    # Offset management
    auto_offset_reset='earliest',  # earliest, latest, none
    enable_auto_commit=True,
    auto_commit_interval_ms=5000,

    # Fetching
    fetch_min_bytes=1,  # Min data to fetch
    fetch_max_wait_ms=500,  # Max wait time
    max_poll_records=500,  # Max records per poll
    max_poll_interval_ms=300000,  # Max time between polls (5 min)

    # Session
    session_timeout_ms=10000,  # Consumer group timeout
    heartbeat_interval_ms=3000  # Heartbeat frequency
)
```

**Key parameters**:
- **group_id**: Consumer group for load sharing
- **auto_offset_reset**: Where to start if no offset exists
  - `earliest`: Start from beginning
  - `latest`: Start from newest messages
  - `none`: Throw exception

- **enable_auto_commit**: Automatically commit offsets
- **max_poll_records**: Messages fetched per poll
- **session_timeout_ms**: Time before consumer considered dead

### Manual Offset Management

```python
consumer = KafkaConsumer(
    'orders',
    enable_auto_commit=False,  # Manual commit
    group_id='order-processor'
)

for message in consumer:
    try:
        # Process message
        process_order(message.value)

        # Commit offset (at-least-once guarantee)
        consumer.commit()
    except Exception as e:
        print(f"Processing failed: {e}")
        # Don't commit on error → message reprocessed
```

**Commit strategies**:

**1. Auto-commit** (at-most-once, can lose data):
```python
enable_auto_commit=True
# Offsets committed periodically, even if processing failed
```

**2. Commit after processing** (at-least-once):
```python
for message in consumer:
    process(message)
    consumer.commit()  # Commit after successful processing
```

**3. Batch commit** (throughput):
```python
for i, message in enumerate(consumer):
    process(message)
    if i % 100 == 0:
        consumer.commit()  # Commit every 100 messages
```

**4. Commit specific offsets**:
```python
consumer.commit({
    TopicPartition('orders', 0): OffsetAndMetadata(12345, None),
    TopicPartition('orders', 1): OffsetAndMetadata(67890, None)
})
```

### Seeking to Specific Offset

```python
from kafka import TopicPartition

# Assign partitions manually
partition = TopicPartition('orders', 0)
consumer.assign([partition])

# Seek to specific offset
consumer.seek(partition, 1000)

# Seek to beginning
consumer.seek_to_beginning(partition)

# Seek to end
consumer.seek_to_end(partition)

# Consume from offset 1000 onwards
for message in consumer:
    print(message.offset, message.value)
```

### Consumer Rebalancing

**Rebalance listener**:
```python
from kafka import ConsumerRebalanceListener

class MyListener(ConsumerRebalanceListener):
    def on_partitions_revoked(self, revoked):
        print(f"Partitions revoked: {revoked}")
        # Clean up state, commit offsets
        consumer.commit()

    def on_partitions_assigned(self, assigned):
        print(f"Partitions assigned: {assigned}")
        # Initialize state for new partitions

consumer = KafkaConsumer(
    'orders',
    group_id='order-processor'
)
consumer.subscribe(['orders'], listener=MyListener())
```

### Multiple Topics

```python
# Subscribe to multiple topics
consumer.subscribe(['orders', 'payments', 'shipments'])

# Pattern-based subscription
consumer.subscribe(pattern='^user-.*')  # All topics starting with "user-"

# Explicit topic list
consumer.subscribe(['topic1', 'topic2', 'topic3'])
```

### Headers

```python
for message in consumer:
    # Access headers
    headers = dict(message.headers)
    correlation_id = headers.get('correlation-id', b'').decode('utf-8')
    source = headers.get('source', b'').decode('utf-8')

    print(f"From {source}, ID: {correlation_id}")
    print(f"Value: {message.value}")
```

### Java Consumer

```java
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("group.id", "order-processor");
props.put("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
props.put("value.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
props.put("enable.auto.commit", "false");

KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props);
consumer.subscribe(Arrays.asList("orders"));

try {
    while (true) {
        ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));

        for (ConsumerRecord<String, String> record : records) {
            System.out.printf("partition=%d, offset=%d, key=%s, value=%s%n",
                record.partition(), record.offset(), record.key(), record.value());

            // Process record
            processOrder(record.value());
        }

        // Commit offsets
        consumer.commitSync();
    }
} finally {
    consumer.close();
}
```

---

## 5. Kafka Streams API

### What is Kafka Streams?

**Kafka Streams**: Java library for stream processing
- **Processes data in Kafka topics** (read from topics, write to topics)
- **Stateless and stateful operations** (filter, map, aggregate, join)
- **Exactly-once processing** (EOS)
- **Fault-tolerant** (automatic recovery from failures)
- **Elastic** (scale by adding instances)

**Architecture**:
```
Input Topics → Kafka Streams App → Output Topics
               ├── Stateless: filter, map, flatMap
               └── Stateful: aggregate, join, windowing
```

### Basic Streams Application (Java)

```java
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.*;
import java.util.Properties;

public class WordCountApp {
    public static void main(String[] args) {
        Properties props = new Properties();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, "word-count-app");
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");

        StreamsBuilder builder = new StreamsBuilder();

        // Input topic: "text-input"
        KStream<String, String> textLines = builder.stream("text-input");

        // Process: split, count
        KTable<String, Long> wordCounts = textLines
            .flatMapValues(line -> Arrays.asList(line.toLowerCase().split("\\s+")))
            .groupBy((key, word) -> word)
            .count();

        // Output topic: "word-count-output"
        wordCounts.toStream().to("word-count-output");

        // Start application
        KafkaStreams streams = new KafkaStreams(builder.build(), props);
        streams.start();

        // Graceful shutdown
        Runtime.getRuntime().addShutdownHook(new Thread(streams::close));
    }
}
```

### Stateless Operations

**filter**: Filter records
```java
KStream<String, Integer> stream = builder.stream("numbers");

// Keep only even numbers
KStream<String, Integer> evens = stream.filter((key, value) -> value % 2 == 0);

evens.to("even-numbers");
```

**map**: Transform key and value
```java
KStream<String, String> stream = builder.stream("users");

// Convert to uppercase
KStream<String, String> upper = stream.map(
    (key, value) -> KeyValue.pair(key.toUpperCase(), value.toUpperCase())
);
```

**mapValues**: Transform only value (preserves key)
```java
KStream<String, Integer> stream = builder.stream("numbers");

// Double each value
KStream<String, Integer> doubled = stream.mapValues(value -> value * 2);
```

**flatMap**: One-to-many transformation
```java
KStream<String, String> sentences = builder.stream("sentences");

// Split sentences into words
KStream<String, String> words = sentences.flatMapValues(
    sentence -> Arrays.asList(sentence.split("\\s+"))
);
```

**branch**: Split stream into multiple branches
```java
KStream<String, Integer> stream = builder.stream("numbers");

// Split into positive, negative, zero
KStream<String, Integer>[] branches = stream.branch(
    (key, value) -> value > 0,   // Branch 0: positive
    (key, value) -> value < 0,   // Branch 1: negative
    (key, value) -> true          // Branch 2: zero
);

branches[0].to("positive-numbers");
branches[1].to("negative-numbers");
branches[2].to("zero-numbers");
```

**merge**: Combine multiple streams
```java
KStream<String, String> stream1 = builder.stream("topic1");
KStream<String, String> stream2 = builder.stream("topic2");

// Merge streams
KStream<String, String> merged = stream1.merge(stream2);
```

### Stateful Operations

**groupByKey**: Group by key (for aggregation)
```java
KStream<String, Integer> stream = builder.stream("user-scores");

// Group by user
KGroupedStream<String, Integer> grouped = stream.groupByKey();

// Aggregate: sum scores per user
KTable<String, Integer> totals = grouped.reduce((aggValue, newValue) -> aggValue + newValue);
```

**groupBy**: Group by custom key
```java
KStream<String, String> stream = builder.stream("purchases");

// Group by product (value field)
KGroupedStream<String, String> grouped = stream.groupBy(
    (key, value) -> extractProduct(value)
);
```

**count**: Count records per key
```java
KStream<String, String> stream = builder.stream("page-views");

// Count page views per user
KTable<String, Long> counts = stream
    .groupByKey()
    .count();

counts.toStream().to("page-view-counts");
```

**aggregate**: Custom aggregation
```java
KStream<String, Integer> stream = builder.stream("transactions");

// Calculate sum and count per user
KTable<String, Stats> stats = stream
    .groupByKey()
    .aggregate(
        () -> new Stats(0, 0),  // Initializer
        (key, value, aggregate) -> {
            aggregate.sum += value;
            aggregate.count++;
            return aggregate;
        }
    );

class Stats {
    int sum;
    int count;

    Stats(int sum, int count) {
        this.sum = sum;
        this.count = count;
    }
}
```

**reduce**: Combine values with same key
```java
KStream<String, Integer> stream = builder.stream("scores");

// Max score per user
KTable<String, Integer> maxScores = stream
    .groupByKey()
    .reduce((aggValue, newValue) -> Math.max(aggValue, newValue));
```

### KStream vs KTable

**KStream**: Unbounded stream of records (insert-only)
```java
KStream<String, String> stream = builder.stream("user-events");
// Each record is an independent event
```

**KTable**: Changelog stream (update/delete)
```java
KTable<String, String> table = builder.table("user-profiles");
// Latest value per key (like database table)
```

**Conversion**:
```java
// KTable → KStream
KStream<String, String> stream = table.toStream();

// KStream → KTable
KTable<String, Long> table = stream.groupByKey().count();
```

---

## 6. Stateful Operations

### State Stores

**State store**: Local storage for stateful operations (backed by Kafka topic for fault tolerance)

**Types**:
- **Key-value store**: Store aggregations, joins
- **Window store**: Store windowed aggregations
- **Session store**: Store session windows

**Example: Custom state store**:
```java
StreamsBuilder builder = new StreamsBuilder();

// Create state store
StoreBuilder<KeyValueStore<String, Integer>> storeBuilder = Stores
    .keyValueStoreBuilder(
        Stores.persistentKeyValueStore("user-scores"),
        Serdes.String(),
        Serdes.Integer()
    );

builder.addStateStore(storeBuilder);

// Use state store in processor
KStream<String, Integer> stream = builder.stream("score-events");

stream.process(
    () -> new Processor<String, Integer>() {
        private KeyValueStore<String, Integer> store;

        @Override
        public void init(ProcessorContext context) {
            store = (KeyValueStore<String, Integer>) context.getStateStore("user-scores");
        }

        @Override
        public void process(String key, Integer value) {
            // Read current score
            Integer current = store.get(key);
            if (current == null) current = 0;

            // Update score
            store.put(key, current + value);

            // Forward to downstream
            context().forward(key, current + value);
        }

        @Override
        public void close() {}
    },
    "user-scores"
);
```

### Changelog Topics

**Changelog**: Kafka topic backing state store (for fault tolerance)

```
State Store (Local RocksDB)
       ↓
Changelog Topic (Kafka)
```

**How it works**:
1. State store writes to local disk (RocksDB)
2. Changes also written to changelog topic
3. On failure, new instance restores state from changelog

**Configuration**:
```java
props.put(StreamsConfig.STATE_DIR_CONFIG, "/tmp/kafka-streams");
props.put(StreamsConfig.COMMIT_INTERVAL_MS_CONFIG, 30000);  // Changelog flush interval
```

### Interactive Queries

**Query state stores from external applications** (REST API for state):

```java
// In Streams app: expose state store
KafkaStreams streams = new KafkaStreams(builder.build(), props);
streams.start();

// Query state store
ReadOnlyKeyValueStore<String, Integer> store = streams.store(
    StoreQueryParameters.fromNameAndType(
        "user-scores",
        QueryableStoreTypes.keyValueStore()
    )
);

Integer score = store.get("user123");
System.out.println("User score: " + score);
```

**REST API for queries**:
```java
@RestController
public class StateStoreController {
    @Autowired
    private KafkaStreams streams;

    @GetMapping("/scores/{userId}")
    public Integer getScore(@PathVariable String userId) {
        ReadOnlyKeyValueStore<String, Integer> store = streams.store(
            StoreQueryParameters.fromNameAndType(
                "user-scores",
                QueryableStoreTypes.keyValueStore()
            )
        );
        return store.get(userId);
    }
}
```

---

## 7. Windowing

### Window Types

**1. Tumbling window**: Fixed-size, non-overlapping
```
Time: 0  1  2  3  4  5  6  7  8  9
      [--W1--][--W2--][--W3--]
```

**2. Hopping window**: Fixed-size, overlapping
```
Time: 0  1  2  3  4  5  6  7  8  9
      [--W1--]
         [--W2--]
            [--W3--]
```

**3. Sliding window**: Event-driven, variable-size
```
Events: E1    E2       E3    E4
        [----W1----]
              [----W2----]
                   [--W3--]
```

**4. Session window**: Gap-based, user sessions
```
Events: E1 E2    (gap)    E3 E4 E5
        [Session1]       [Session2]
```

### Tumbling Windows

**Fixed-size, non-overlapping windows**:

```java
KStream<String, Integer> stream = builder.stream("page-views");

// 5-minute tumbling windows
KTable<Windowed<String>, Long> counts = stream
    .groupByKey()
    .windowedBy(TimeWindows.of(Duration.ofMinutes(5)))
    .count();

// Output format: "[user123@1698432000000/1698432300000]=42"
counts.toStream()
    .map((windowedKey, count) -> {
        String key = windowedKey.key();
        long start = windowedKey.window().start();
        long end = windowedKey.window().end();
        return KeyValue.pair(
            key + "@" + start,
            count
        );
    })
    .to("page-view-counts");
```

### Hopping Windows

**Overlapping windows**:

```java
// 10-minute windows, advancing every 5 minutes
KTable<Windowed<String>, Long> counts = stream
    .groupByKey()
    .windowedBy(TimeWindows.of(Duration.ofMinutes(10))
                           .advanceBy(Duration.ofMinutes(5)))
    .count();
```

**Example timeline**:
```
Window 1: 00:00 - 00:10
Window 2: 00:05 - 00:15
Window 3: 00:10 - 00:20
```

### Sliding Windows

**Event-driven windows** (for joins):

```java
KStream<String, Integer> left = builder.stream("topic1");
KStream<String, Integer> right = builder.stream("topic2");

// Join events within 10-minute window
KStream<String, String> joined = left.join(
    right,
    (leftValue, rightValue) -> leftValue + ":" + rightValue,
    JoinWindows.of(Duration.ofMinutes(10))
);
```

### Session Windows

**Gap-based windows** (user sessions):

```java
// 30-minute inactivity gap
KTable<Windowed<String>, Long> sessions = stream
    .groupByKey()
    .windowedBy(SessionWindows.with(Duration.ofMinutes(30)))
    .count();
```

**Example**:
```
User events: 10:00, 10:05, 10:10, (gap > 30 min), 11:00, 11:15

Session 1: 10:00 - 10:10 (3 events)
Session 2: 11:00 - 11:15 (2 events)
```

### Grace Period

**Handle late-arriving records**:

```java
// 1-hour windows with 10-minute grace period
KTable<Windowed<String>, Long> counts = stream
    .groupByKey()
    .windowedBy(TimeWindows.of(Duration.ofHours(1))
                           .grace(Duration.ofMinutes(10)))
    .count();
```

**How it works**:
- Window closes at `end_time + grace_period`
- Late records (within grace period) update window
- After grace period, window is final (no updates)

---

## 8. Joins

### Join Types

**1. Stream-Stream Join**: Join two streams (within time window)
**2. Stream-Table Join**: Enrich stream with table data
**3. Table-Table Join**: Join two tables (foreign key join)

### Stream-Stream Join

**Inner join** (match required):
```java
KStream<String, String> orders = builder.stream("orders");
KStream<String, String> payments = builder.stream("payments");

// Join within 1-hour window
KStream<String, String> joined = orders.join(
    payments,
    (orderValue, paymentValue) -> "Order: " + orderValue + ", Payment: " + paymentValue,
    JoinWindows.of(Duration.ofHours(1))
);

joined.to("order-payments");
```

**Left join** (left side always included):
```java
KStream<String, String> joined = orders.leftJoin(
    payments,
    (orderValue, paymentValue) -> {
        if (paymentValue != null) {
            return "Order: " + orderValue + ", Payment: " + paymentValue;
        } else {
            return "Order: " + orderValue + ", Payment: NONE";
        }
    },
    JoinWindows.of(Duration.ofHours(1))
);
```

**Outer join** (both sides included):
```java
KStream<String, String> joined = orders.outerJoin(
    payments,
    (orderValue, paymentValue) ->
        "Order: " + orderValue + ", Payment: " + paymentValue,
    JoinWindows.of(Duration.ofHours(1))
);
```

### Stream-Table Join

**Enrich stream with table data**:

```java
KStream<String, String> orders = builder.stream("orders");
KTable<String, String> users = builder.table("users");

// Enrich orders with user data
KStream<String, String> enriched = orders.join(
    users,
    (orderValue, userValue) -> "Order: " + orderValue + ", User: " + userValue
);

enriched.to("enriched-orders");
```

**Example**:
```
Orders stream:
  {"user_id": "user123", "product": "laptop", "price": 1000}

Users table:
  {"user_id": "user123", "name": "Alice", "email": "alice@example.com"}

Enriched:
  {"order": {...}, "user": {"name": "Alice", "email": "alice@example.com"}}
```

### Table-Table Join

**Join two tables** (like SQL join):

```java
KTable<String, String> users = builder.table("users");
KTable<String, String> profiles = builder.table("profiles");

// Join users with profiles
KTable<String, String> joined = users.join(
    profiles,
    (userValue, profileValue) -> "User: " + userValue + ", Profile: " + profileValue
);

joined.toStream().to("user-profiles");
```

### Co-Partitioning

**Requirement**: Joined topics must have same number of partitions and same partitioning key

```bash
# Create topics with same partitions
kafka-topics.sh --create --topic orders --partitions 4
kafka-topics.sh --create --topic payments --partitions 4
```

**Why?**
- Kafka Streams routes records by key hash
- Same key must land in same partition for join to work
- Mismatched partitions cause errors

---

## 9. Exactly-Once Semantics

### Delivery Guarantees

**1. At-most-once**: Message may be lost (no retries)
**2. At-least-once**: Message may be duplicated (retries)
**3. Exactly-once**: Message processed exactly once (idempotence + transactions)

### Exactly-Once Producer

**Enable idempotence**:
```python
producer = KafkaProducer(
    enable_idempotence=True,
    acks='all',
    retries=3
)
```

**How it works**:
- Producer assigns sequence number to each message
- Broker detects duplicates (same sequence number)
- Duplicates not written to log

### Exactly-Once Streams

**Enable EOS in Kafka Streams**:
```java
props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, StreamsConfig.EXACTLY_ONCE_V2);
```

**How it works**:
1. **Transactional writes**: Streams app writes to output topics and state stores in a transaction
2. **Commit markers**: Transaction commit markers ensure atomicity
3. **Consumer offset commits**: Offset commits included in transaction

**Result**: Either all writes succeed (output + state + offsets), or none do

### Exactly-Once End-to-End

**Requirements**:
1. **Producer**: Idempotent producer or transactions
2. **Streams app**: Exactly-once processing
3. **Consumer**: Read committed messages only

```java
// Streams app
props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, StreamsConfig.EXACTLY_ONCE_V2);

// Consumer
props.put("isolation.level", "read_committed");
```

### Transactional ID

**Unique identifier for transactional producer**:
```python
producer = KafkaProducer(
    transactional_id='order-service-1',
    enable_idempotence=True,
    acks='all'
)

producer.init_transactions()

try:
    producer.begin_transaction()
    producer.send('orders', value={'order_id': 1})
    producer.send('payments', value={'payment_id': 1})
    producer.commit_transaction()
except Exception:
    producer.abort_transaction()
```

**Benefits**:
- Atomic multi-topic writes
- Exactly-once delivery across topics
- Zombie fencing (prevent old instances from writing)

---

## 10. Schema Registry

### Why Schema Registry?

**Problem**: Schema evolution (adding fields, changing types)
- Consumers break when producer schema changes
- No central schema versioning

**Solution**: Schema Registry (Confluent)
- Central repository for schemas (Avro, Protobuf, JSON Schema)
- Schema validation on produce/consume
- Backward/forward compatibility checks

### Avro with Schema Registry

**Install**:
```bash
pip install confluent-kafka[avro]
```

**Define schema** (Avro):
```json
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
```

**Producer with schema**:
```python
from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer

# Schema Registry config
schema_registry_conf = {'url': 'http://localhost:8081'}

# Value schema
value_schema = avro.loads('''
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "string"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": "string"}
  ]
}
''')

# Create producer
producer = AvroProducer({
    'bootstrap.servers': 'localhost:9092',
    'schema.registry.url': 'http://localhost:8081'
}, default_value_schema=value_schema)

# Send Avro message
user = {'id': 'user123', 'name': 'Alice', 'email': 'alice@example.com'}
producer.produce(topic='users', value=user)
producer.flush()
```

**Consumer with schema**:
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

    # Value automatically deserialized with schema
    user = msg.value()
    print(f"User: {user['name']} ({user['email']})")
```

### Schema Evolution

**Backward compatible** (old consumers can read new data):
```json
// V1
{"name": "id", "type": "string"}

// V2 (added field with default)
{"name": "age", "type": "int", "default": 0}
```

**Forward compatible** (new consumers can read old data):
```json
// V1
{"name": "id", "type": "string"}
{"name": "age", "type": "int"}

// V2 (deleted field)
{"name": "id", "type": "string"}
```

**Full compatible** (both backward and forward):
```json
// V1
{"name": "id", "type": "string"}

// V2 (added optional field)
{"name": "age", "type": ["null", "int"], "default": null}
```

### Schema Registry REST API

```bash
# Register schema
curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"schema": "{\"type\":\"string\"}"}' \
  http://localhost:8081/subjects/users-value/versions

# Get schema by ID
curl http://localhost:8081/schemas/ids/1

# List subjects
curl http://localhost:8081/subjects

# Get latest schema
curl http://localhost:8081/subjects/users-value/versions/latest

# Check compatibility
curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"schema": "{\"type\":\"string\"}"}' \
  http://localhost:8081/compatibility/subjects/users-value/versions/latest
```

---

## 11. ksqlDB

### What is ksqlDB?

**ksqlDB**: SQL-like stream processing engine (built on Kafka Streams)
- **SQL syntax**: Familiar SQL for stream processing
- **Streams and tables**: `CREATE STREAM`, `CREATE TABLE`
- **Materialized views**: Query results stored in Kafka
- **Push and pull queries**: Real-time and point-in-time queries

### Basic Queries

**Create stream**:
```sql
-- Create stream from Kafka topic
CREATE STREAM user_events (
  user_id VARCHAR,
  action VARCHAR,
  timestamp BIGINT
) WITH (
  KAFKA_TOPIC='user-events',
  VALUE_FORMAT='JSON',
  PARTITIONS=3
);

-- Query stream (continuous query)
SELECT user_id, action, timestamp
FROM user_events
EMIT CHANGES;
```

**Create table** (aggregation):
```sql
-- Count events per user
CREATE TABLE user_event_counts AS
SELECT user_id, COUNT(*) AS event_count
FROM user_events
GROUP BY user_id
EMIT CHANGES;

-- Query table
SELECT * FROM user_event_counts WHERE user_id = 'user123';
```

### Filtering

```sql
-- Filter stream
CREATE STREAM login_events AS
SELECT *
FROM user_events
WHERE action = 'login'
EMIT CHANGES;
```

### Transformations

```sql
-- Transform values
CREATE STREAM enriched_events AS
SELECT
  user_id,
  action,
  UCASE(action) AS action_upper,
  timestamp,
  FROM_UNIXTIME(timestamp) AS event_time
FROM user_events
EMIT CHANGES;
```

### Windowing

```sql
-- Tumbling window (5 minutes)
CREATE TABLE event_counts_5min AS
SELECT
  user_id,
  COUNT(*) AS event_count,
  WINDOWSTART AS window_start,
  WINDOWEND AS window_end
FROM user_events
WINDOW TUMBLING (SIZE 5 MINUTES)
GROUP BY user_id
EMIT CHANGES;

-- Hopping window
CREATE TABLE event_counts_hopping AS
SELECT user_id, COUNT(*) AS event_count
FROM user_events
WINDOW HOPPING (SIZE 10 MINUTES, ADVANCE BY 5 MINUTES)
GROUP BY user_id
EMIT CHANGES;

-- Session window
CREATE TABLE user_sessions AS
SELECT user_id, COUNT(*) AS event_count
FROM user_events
WINDOW SESSION (30 MINUTES)
GROUP BY user_id
EMIT CHANGES;
```

### Joins

**Stream-stream join**:
```sql
CREATE STREAM orders (order_id VARCHAR, user_id VARCHAR, amount DOUBLE)
  WITH (KAFKA_TOPIC='orders', VALUE_FORMAT='JSON');

CREATE STREAM payments (payment_id VARCHAR, order_id VARCHAR, status VARCHAR)
  WITH (KAFKA_TOPIC='payments', VALUE_FORMAT='JSON');

-- Join within 1 hour
CREATE STREAM order_payments AS
SELECT
  o.order_id,
  o.user_id,
  o.amount,
  p.payment_id,
  p.status
FROM orders o
INNER JOIN payments p WITHIN 1 HOUR
ON o.order_id = p.order_id
EMIT CHANGES;
```

**Stream-table join** (enrichment):
```sql
CREATE TABLE users (user_id VARCHAR PRIMARY KEY, name VARCHAR, email VARCHAR)
  WITH (KAFKA_TOPIC='users', VALUE_FORMAT='JSON');

CREATE STREAM orders (order_id VARCHAR, user_id VARCHAR, amount DOUBLE)
  WITH (KAFKA_TOPIC='orders', VALUE_FORMAT='JSON');

-- Enrich orders with user data
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

### Push vs Pull Queries

**Push query** (continuous, real-time):
```sql
-- Returns results as they arrive
SELECT * FROM user_events EMIT CHANGES;
```

**Pull query** (point-in-time, like SQL):
```sql
-- Returns current state
SELECT * FROM user_event_counts WHERE user_id = 'user123';
```

### ksqlDB CLI

```bash
# Start ksqlDB CLI
ksql http://localhost:8088

# Show topics
SHOW TOPICS;

# Show streams
SHOW STREAMS;

# Show tables
SHOW TABLES;

# Describe stream
DESCRIBE user_events;

# Show queries
SHOW QUERIES;

# Terminate query
TERMINATE query_id;
```

---

## 12. Performance Tuning

### Producer Tuning

**Throughput optimization**:
```python
producer = KafkaProducer(
    # Batching (higher throughput)
    batch_size=32768,  # 32 KB (default 16 KB)
    linger_ms=20,  # Wait 20ms to batch (default 0)

    # Compression
    compression_type='lz4',  # lz4 > snappy > gzip > none

    # Buffer
    buffer_memory=67108864,  # 64 MB (default 32 MB)

    # Acks (trade durability for speed)
    acks=1  # Leader only (faster than acks=all)
)
```

**Latency optimization**:
```python
producer = KafkaProducer(
    linger_ms=0,  # Send immediately
    compression_type='none',  # No compression overhead
    acks=1,  # Don't wait for all replicas
    batch_size=16384  # Smaller batches
)
```

### Consumer Tuning

**Throughput optimization**:
```python
consumer = KafkaConsumer(
    # Fetch more data per request
    fetch_min_bytes=1048576,  # 1 MB (default 1 byte)
    fetch_max_wait_ms=500,  # Wait up to 500ms
    max_poll_records=1000,  # Fetch 1000 records per poll (default 500)

    # Parallelize consumption
    # Add more consumers (up to partition count)
)
```

**Latency optimization**:
```python
consumer = KafkaConsumer(
    fetch_min_bytes=1,  # Don't wait for batching
    fetch_max_wait_ms=0,  # Return immediately
    max_poll_records=100  # Smaller batches
)
```

### Partition Count

**Choosing partition count**:
```
Partitions = max(
  target_throughput / producer_throughput_per_partition,
  target_throughput / consumer_throughput_per_partition
)
```

**Example**:
- Target: 100 MB/s
- Producer: 10 MB/s per partition
- Consumer: 20 MB/s per partition
- Partitions = max(100/10, 100/20) = max(10, 5) = **10 partitions**

**Trade-offs**:
- **More partitions**: Higher throughput, more parallelism
- **Fewer partitions**: Lower overhead, simpler management
- **Too many**: Election latency, metadata overhead
- **Guideline**: 100-1000 partitions per broker

### Replication Factor

**Choosing replication factor**:
```
replication.factor=3
min.insync.replicas=2
```

**Trade-offs**:
- **Replication factor 1**: No fault tolerance (don't use in production)
- **Replication factor 2**: Tolerate 1 broker failure
- **Replication factor 3**: Tolerate 1 broker failure (2 if min.insync.replicas=2)
- **Higher**: More disk usage, slower writes

### Compression

**Benchmark** (MB compressed):
```
none:   100 MB
lz4:     40 MB (fast, good compression)
snappy:  45 MB (fast)
gzip:    30 MB (slow, best compression)
zstd:    35 MB (balanced, Kafka 2.1+)
```

**Recommendation**: Use `lz4` (best balance)

### Broker Configuration

```properties
# Network threads (handle requests)
num.network.threads=8  # Default 3

# I/O threads (disk operations)
num.io.threads=16  # Default 8

# Replication threads
num.replica.fetchers=4  # Default 1

# Log flush (less frequent = higher throughput)
log.flush.interval.messages=10000  # Default 9223372036854775807 (disabled)
log.flush.interval.ms=1000  # Default not set

# Log segment size
log.segment.bytes=1073741824  # 1 GB (default)

# Retention
log.retention.hours=168  # 7 days (default)
log.retention.bytes=-1  # Unlimited (default)
```

### JVM Tuning (Broker)

```bash
# Heap size (5-8 GB recommended)
export KAFKA_HEAP_OPTS="-Xmx6g -Xms6g"

# G1 GC (recommended for Kafka)
export KAFKA_JVM_PERFORMANCE_OPTS="-XX:+UseG1GC -XX:MaxGCPauseMillis=20"
```

---

## 13. Monitoring

### Key Metrics

**Broker metrics**:
- **UnderReplicatedPartitions**: Partitions not fully replicated (should be 0)
- **OfflinePartitionsCount**: Partitions without leader (should be 0)
- **ActiveControllerCount**: Number of active controllers (should be 1)
- **RequestHandlerAvgIdlePercent**: Handler thread utilization (should be > 20%)
- **NetworkProcessorAvgIdlePercent**: Network thread utilization (should be > 20%)

**Producer metrics**:
- **record-send-rate**: Messages sent per second
- **record-error-rate**: Failed messages per second (should be 0)
- **request-latency-avg**: Average request latency
- **batch-size-avg**: Average batch size
- **compression-rate-avg**: Compression ratio

**Consumer metrics**:
- **records-consumed-rate**: Messages consumed per second
- **fetch-latency-avg**: Average fetch latency
- **records-lag-max**: Max lag (messages behind)
- **commit-latency-avg**: Average commit latency

### Consumer Lag Monitoring

**What is lag?**
```
Current offset: 1000
Latest offset:  1500
Lag:            500 messages behind
```

**Check lag**:
```bash
# Kafka consumer groups command
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group my-consumer-group --describe

# Output:
# TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
# orders          0          1000            1500            500
# orders          1          2000            2000            0
# orders          2          1500            2000            500
```

**Alerting thresholds**:
- **Lag < 1000**: Healthy
- **Lag 1000-10000**: Warning
- **Lag > 10000**: Critical (consumer can't keep up)

### Monitoring Tools

**1. JMX Metrics**:
```bash
# Enable JMX
export KAFKA_JMX_OPTS="-Dcom.sun.management.jmxremote \
  -Dcom.sun.management.jmxremote.port=9999 \
  -Dcom.sun.management.jmxremote.authenticate=false \
  -Dcom.sun.management.jmxremote.ssl=false"

# Query JMX with jmxtrans, Prometheus JMX Exporter, etc.
```

**2. Prometheus + Grafana**:
```yaml
# JMX Exporter (config.yml)
rules:
  - pattern: kafka.server<type=(.+), name=(.+)><>Value
    name: kafka_server_$1_$2
```

**3. Confluent Control Center**: Web UI for monitoring

**4. Burrow**: Consumer lag monitoring (LinkedIn)

### Health Checks

```bash
# Broker health
kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# Topic list
kafka-topics.sh --bootstrap-server localhost:9092 --list

# Consumer groups
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list

# Check under-replicated partitions
kafka-topics.sh --bootstrap-server localhost:9092 --describe --under-replicated-partitions
```

---

## 14. Security

### Authentication (SASL)

**SASL/PLAIN** (username/password):
```properties
# Server (server.properties)
listeners=SASL_PLAINTEXT://localhost:9092
security.inter.broker.protocol=SASL_PLAINTEXT
sasl.mechanism.inter.broker.protocol=PLAIN
sasl.enabled.mechanisms=PLAIN

# kafka_server_jaas.conf
# Example configuration - use actual credentials from secure storage in production
KafkaServer {
  org.apache.kafka.common.security.plain.PlainLoginModule required
  username="admin"
  password="admin-secret"  # Example only - use secure credential management
  user_admin="admin-secret"
  user_alice="alice-secret";
};
```

**Producer with SASL**:
```python
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    security_protocol='SASL_PLAINTEXT',
    sasl_mechanism='PLAIN',
    sasl_plain_username='alice',
    sasl_plain_password='alice-secret'  # Example only - use environment variable or secret manager
)
```

**Consumer with SASL**:
```python
consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],
    security_protocol='SASL_PLAINTEXT',
    sasl_mechanism='PLAIN',
    sasl_plain_username='alice',
    sasl_plain_password='alice-secret'  # Example only - use environment variable or secret manager
)
```

### Encryption (TLS/SSL)

**Server configuration**:
```properties
listeners=SSL://localhost:9093
security.inter.broker.protocol=SSL

# Keystore (server certificate)
ssl.keystore.location=/var/private/ssl/kafka.server.keystore.jks
ssl.keystore.password=server-password
ssl.key.password=key-password

# Truststore (CA certificate)
ssl.truststore.location=/var/private/ssl/kafka.server.truststore.jks
ssl.truststore.password=truststore-password

# Client authentication (optional)
ssl.client.auth=required
```

**Producer with TLS**:
```python
producer = KafkaProducer(
    bootstrap_servers=['localhost:9093'],
    security_protocol='SSL',
    ssl_cafile='/path/to/ca-cert',
    ssl_certfile='/path/to/client-cert',
    ssl_keyfile='/path/to/client-key'
)
```

### Authorization (ACLs)

**Enable ACLs**:
```properties
# server.properties
authorizer.class.name=kafka.security.authorizer.AclAuthorizer
super.users=User:admin
```

**Add ACL**:
```bash
# Allow alice to read from "orders" topic
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:alice \
  --operation Read \
  --topic orders

# Allow bob to write to "payments" topic
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:bob \
  --operation Write \
  --topic payments

# Allow consumer group
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:alice \
  --operation Read \
  --group order-processor
```

**List ACLs**:
```bash
kafka-acls.sh --bootstrap-server localhost:9092 --list
```

---

## 15. Testing

### Unit Testing Kafka Streams

**Topology Test Driver** (Kafka Streams):
```java
import org.apache.kafka.streams.TopologyTestDriver;
import org.apache.kafka.streams.test.ConsumerRecordFactory;
import org.junit.jupiter.api.Test;

public class WordCountTest {
    @Test
    public void testWordCount() {
        // Build topology
        StreamsBuilder builder = new StreamsBuilder();
        KStream<String, String> input = builder.stream("input");
        input.flatMapValues(v -> Arrays.asList(v.split("\\s+")))
             .groupBy((k, v) -> v)
             .count()
             .toStream()
             .to("output");

        // Create test driver
        TopologyTestDriver testDriver = new TopologyTestDriver(
            builder.build(),
            config
        );

        // Input topic
        TestInputTopic<String, String> inputTopic = testDriver.createInputTopic(
            "input",
            new StringSerializer(),
            new StringSerializer()
        );

        // Output topic
        TestOutputTopic<String, Long> outputTopic = testDriver.createOutputTopic(
            "output",
            new StringDeserializer(),
            new LongDeserializer()
        );

        // Send test data
        inputTopic.pipeInput("key1", "hello world");
        inputTopic.pipeInput("key2", "hello kafka");

        // Assert output
        assertEquals(1L, outputTopic.readKeyValue().value);  // hello: 1
        assertEquals(1L, outputTopic.readKeyValue().value);  // world: 1
        assertEquals(2L, outputTopic.readKeyValue().value);  // hello: 2
        assertEquals(1L, outputTopic.readKeyValue().value);  // kafka: 1

        testDriver.close();
    }
}
```

### Integration Testing

**Embedded Kafka** (Spring Kafka Test):
```java
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.context.junit.jupiter.SpringExtension;

@ExtendWith(SpringExtension.class)
@EmbeddedKafka(partitions = 1, topics = {"test-topic"})
public class KafkaIntegrationTest {
    @Autowired
    private KafkaTemplate<String, String> kafkaTemplate;

    @Test
    public void testSendReceive() throws Exception {
        String topic = "test-topic";
        String message = "test message";

        // Send message
        kafkaTemplate.send(topic, message);

        // Consume message
        ConsumerRecord<String, String> record = consumer.poll(Duration.ofSeconds(10))
            .iterator().next();

        assertEquals(message, record.value());
    }
}
```

### Testcontainers

**Docker-based integration tests**:
```java
import org.testcontainers.containers.KafkaContainer;
import org.testcontainers.utility.DockerImageName;

public class KafkaContainerTest {
    @Test
    public void test() {
        // Start Kafka in Docker
        KafkaContainer kafka = new KafkaContainer(
            DockerImageName.parse("confluentinc/cp-kafka:7.4.0")
        );
        kafka.start();

        // Connect to Kafka
        String bootstrapServers = kafka.getBootstrapServers();

        // Test producer/consumer
        // ...

        kafka.stop();
    }
}
```

---

## 16. Anti-Patterns

### Producer Anti-Patterns

❌ **Creating producer per message**:
```python
# BAD: Expensive (connection overhead)
for message in messages:
    producer = KafkaProducer()
    producer.send('topic', message)
    producer.close()
```

✅ **Reuse producer**:
```python
# GOOD: Create once, reuse
producer = KafkaProducer()
for message in messages:
    producer.send('topic', message)
producer.close()
```

❌ **Not setting timeouts**:
```python
# BAD: Can hang forever
producer.send('topic', message).get()
```

✅ **Always set timeouts**:
```python
# GOOD: Timeout after 10 seconds
producer.send('topic', message).get(timeout=10)
```

❌ **Large message sizes**:
```python
# BAD: 100 MB message
producer.send('topic', huge_message)
```

✅ **Chunk large data**:
```python
# GOOD: Split into smaller messages
for chunk in chunks(huge_data, chunk_size=1MB):
    producer.send('topic', chunk)
```

### Consumer Anti-Patterns

❌ **Not committing offsets**:
```python
# BAD: Offsets never committed → reprocess messages on restart
for message in consumer:
    process(message)
```

✅ **Commit after processing**:
```python
# GOOD: Commit after successful processing
for message in consumer:
    process(message)
    consumer.commit()
```

❌ **Slow processing blocks poll**:
```python
# BAD: Long processing → consumer timeout
for message in consumer:
    slow_operation(message)  # 5 minutes
```

✅ **Process in separate thread or increase timeout**:
```python
# GOOD: Process async or increase max.poll.interval.ms
consumer = KafkaConsumer(max_poll_interval_ms=600000)  # 10 minutes
```

❌ **Not handling rebalances**:
```python
# BAD: State lost on rebalance
state = {}
for message in consumer:
    state[message.key] = message.value
```

✅ **Persist state or use rebalance listener**:
```python
# GOOD: Commit state on rebalance
class Listener(ConsumerRebalanceListener):
    def on_partitions_revoked(self, revoked):
        save_state(state)
        consumer.commit()

consumer.subscribe(['topic'], listener=Listener())
```

### Architecture Anti-Patterns

❌ **Too many partitions**:
```bash
# BAD: 10,000 partitions per broker
kafka-topics.sh --create --partitions 10000
```

✅ **Reasonable partition count**:
```bash
# GOOD: 100-1000 partitions per broker
kafka-topics.sh --create --partitions 100
```

❌ **No replication**:
```bash
# BAD: No fault tolerance
kafka-topics.sh --create --replication-factor 1
```

✅ **Replicate data**:
```bash
# GOOD: Tolerate broker failures
kafka-topics.sh --create --replication-factor 3
```

❌ **Using Kafka as a database**:
```python
# BAD: Query Kafka for user data
def get_user(user_id):
    # Scan all messages to find user
    for message in consumer:
        if message.key == user_id:
            return message.value
```

✅ **Use Kafka for events, database for queries**:
```python
# GOOD: Kafka → Database, query database
def get_user(user_id):
    return db.query("SELECT * FROM users WHERE id = ?", user_id)
```

---

## 17. Reference

### Kafka CLI Commands

**Topics**:
```bash
# Create topic
kafka-topics.sh --create --topic orders \
  --partitions 3 --replication-factor 3 \
  --bootstrap-server localhost:9092

# List topics
kafka-topics.sh --list --bootstrap-server localhost:9092

# Describe topic
kafka-topics.sh --describe --topic orders \
  --bootstrap-server localhost:9092

# Delete topic
kafka-topics.sh --delete --topic orders \
  --bootstrap-server localhost:9092

# Alter partitions
kafka-topics.sh --alter --topic orders --partitions 6 \
  --bootstrap-server localhost:9092
```

**Producer**:
```bash
# Console producer
kafka-console-producer.sh --topic orders \
  --bootstrap-server localhost:9092

# With key
kafka-console-producer.sh --topic orders \
  --property "parse.key=true" --property "key.separator=:" \
  --bootstrap-server localhost:9092
# Input: key1:value1
```

**Consumer**:
```bash
# Console consumer
kafka-console-consumer.sh --topic orders \
  --from-beginning --bootstrap-server localhost:9092

# With key
kafka-console-consumer.sh --topic orders \
  --property print.key=true --property key.separator=":" \
  --from-beginning --bootstrap-server localhost:9092

# Consumer group
kafka-console-consumer.sh --topic orders \
  --group order-processor --bootstrap-server localhost:9092
```

**Consumer groups**:
```bash
# List groups
kafka-consumer-groups.sh --list --bootstrap-server localhost:9092

# Describe group
kafka-consumer-groups.sh --describe --group order-processor \
  --bootstrap-server localhost:9092

# Reset offsets
kafka-consumer-groups.sh --reset-offsets --to-earliest \
  --group order-processor --topic orders --execute \
  --bootstrap-server localhost:9092
```

### Configuration Reference

**Producer**:
```properties
acks=all
retries=3
enable.idempotence=true
batch.size=16384
linger.ms=10
compression.type=lz4
buffer.memory=33554432
max.block.ms=60000
request.timeout.ms=30000
```

**Consumer**:
```properties
group.id=my-group
auto.offset.reset=earliest
enable.auto.commit=true
auto.commit.interval.ms=5000
fetch.min.bytes=1
fetch.max.wait.ms=500
max.poll.records=500
max.poll.interval.ms=300000
session.timeout.ms=10000
heartbeat.interval.ms=3000
```

**Broker**:
```properties
num.network.threads=8
num.io.threads=16
num.replica.fetchers=4
log.retention.hours=168
log.segment.bytes=1073741824
log.flush.interval.messages=10000
log.flush.interval.ms=1000
replication.factor=3
min.insync.replicas=2
```

### Resources

**Official documentation**:
- Kafka docs: https://kafka.apache.org/documentation/
- Confluent docs: https://docs.confluent.io/
- Kafka Streams docs: https://kafka.apache.org/documentation/streams/

**Books**:
- "Kafka: The Definitive Guide" (O'Reilly)
- "Kafka Streams in Action" (Manning)
- "Designing Event-Driven Systems" (O'Reilly)

**Tools**:
- Kafka Manager: Web UI for clusters
- Kafdrop: Kafka Web UI
- AKHQ: Kafka GUI
- kcat (kafkacat): CLI utility

---

**End of Reference**
