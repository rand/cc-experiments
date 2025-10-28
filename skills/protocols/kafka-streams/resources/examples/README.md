# Kafka Streams Examples

Production-ready examples for Apache Kafka covering producers, consumers, Kafka Streams, exactly-once semantics, schema registry, ksqlDB, and more.

## Contents

1. **Python Examples** (`python/`)
   - `basic_producer.py` - Producer patterns (sync, async, batch, headers)
   - `basic_consumer.py` - Consumer patterns (auto-commit, manual, batch, partition control)
   - `exactly_once_producer.py` - Transactional producer with exactly-once semantics
   - `avro_schema_registry.py` - Avro serialization with Schema Registry

2. **Java Examples** (`java/`)
   - `WordCountStreamsApp.java` - Kafka Streams application (stateless/stateful processing)

3. **ksqlDB Examples** (`ksqldb/`)
   - `queries.sql` - Complete ksqlDB query examples (streams, tables, joins, windowing)

4. **Docker** (`docker/`)
   - `docker-compose.yml` - Complete Kafka stack (Kafka, Schema Registry, Connect, ksqlDB, Control Center)

5. **Monitoring** (`monitoring/`)
   - `prometheus_config.yml` - Prometheus configuration for Kafka monitoring

## Quick Start

### 1. Start Kafka Stack with Docker

```bash
cd docker
docker-compose up -d

# Wait for services to be ready
docker-compose logs -f kafka
```

Services:
- Kafka: `localhost:9092`
- Schema Registry: `http://localhost:8081`
- ksqlDB: `http://localhost:8088`
- Control Center: `http://localhost:9021`
- REST Proxy: `http://localhost:8082`

### 2. Create Topics

```bash
# Create test topic
docker-compose exec kafka kafka-topics --create \
  --topic orders \
  --partitions 3 \
  --replication-factor 1 \
  --bootstrap-server localhost:9092

# List topics
docker-compose exec kafka kafka-topics --list \
  --bootstrap-server localhost:9092

# Describe topic
docker-compose exec kafka kafka-topics --describe \
  --topic orders \
  --bootstrap-server localhost:9092
```

### 3. Run Python Examples

**Install dependencies**:
```bash
pip install kafka-python confluent-kafka[avro]
```

**Run producer**:
```bash
cd python
python basic_producer.py
```

**Run consumer** (in another terminal):
```bash
cd python
python basic_consumer.py
```

**Exactly-once producer**:
```bash
python exactly_once_producer.py
```

**Avro with Schema Registry**:
```bash
# Make sure Schema Registry is running
python avro_schema_registry.py
```

### 4. Run Java Streams App

**Build** (with Maven):
```bash
cd java

# Create pom.xml with Kafka Streams dependency
mvn clean package

# Run
java -jar target/word-count-streams-1.0.jar
```

**Test**:
```bash
# Produce text
echo "hello world hello kafka" | \
  docker-compose exec -T kafka kafka-console-producer \
    --topic text-input \
    --bootstrap-server localhost:9092

# Consume word counts
docker-compose exec kafka kafka-console-consumer \
  --topic word-count-output \
  --from-beginning \
  --bootstrap-server localhost:9092 \
  --property print.key=true \
  --property key.separator=":"
```

### 5. Run ksqlDB Queries

**Access ksqlDB CLI**:
```bash
docker-compose exec ksqldb-cli ksql http://ksqldb-server:8088
```

**Run queries**:
```sql
-- Show topics
SHOW TOPICS;

-- Create stream
CREATE STREAM user_events (
  user_id VARCHAR,
  action VARCHAR,
  timestamp BIGINT
) WITH (
  KAFKA_TOPIC='user-events',
  VALUE_FORMAT='JSON'
);

-- Query stream
SELECT * FROM user_events EMIT CHANGES;

-- Aggregate
CREATE TABLE event_counts AS
SELECT user_id, COUNT(*) AS count
FROM user_events
GROUP BY user_id
EMIT CHANGES;
```

See `ksqldb/queries.sql` for complete examples.

### 6. Monitoring

**Access Control Center**:
```
http://localhost:9021
```

Features:
- Cluster health
- Topic management
- Consumer lag monitoring
- ksqlDB queries
- Schema Registry

**Prometheus + Grafana**:
```bash
# Deploy Prometheus
docker run -d -p 9090:9090 \
  -v $(pwd)/monitoring/prometheus_config.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Deploy Grafana
docker run -d -p 3000:3000 grafana/grafana

# Access Grafana: http://localhost:3000 (admin/admin)
# Add Prometheus data source: http://prometheus:9090
# Import Kafka dashboard
```

## Examples Overview

### Producer Patterns

**1. Synchronous send** (blocking, low throughput):
```python
future = producer.send('orders', key='order1', value=data)
record_metadata = future.get(timeout=10)
```

**2. Asynchronous send** (non-blocking, high throughput):
```python
future = producer.send('orders', key='order1', value=data)
future.add_callback(on_success)
future.add_errback(on_error)
```

**3. Batch send** (highest throughput):
```python
for message in messages:
    producer.send('orders', message)
producer.flush()
```

**4. Transactional send** (exactly-once):
```python
producer.init_transactions()
producer.begin_transaction()
producer.send('orders', order_data)
producer.send('payments', payment_data)
producer.commit_transaction()  # Atomic
```

### Consumer Patterns

**1. Auto-commit** (at-most-once, can lose data):
```python
consumer = KafkaConsumer(enable_auto_commit=True)
for message in consumer:
    process(message)
```

**2. Manual commit** (at-least-once, can duplicate):
```python
consumer = KafkaConsumer(enable_auto_commit=False)
for message in consumer:
    process(message)
    consumer.commit()  # Commit after processing
```

**3. Batch commit** (higher throughput):
```python
for i, message in enumerate(consumer):
    process(message)
    if i % 100 == 0:
        consumer.commit()
```

**4. Partition control** (manual assignment):
```python
partition = TopicPartition('orders', 0)
consumer.assign([partition])
consumer.seek(partition, 100)  # Start from offset 100
```

### Kafka Streams Patterns

**Stateless operations**:
- `filter()` - Filter records
- `map()` - Transform key/value
- `flatMap()` - One-to-many transformation

**Stateful operations**:
- `groupBy()` - Group for aggregation
- `count()` - Count records per key
- `reduce()` - Custom aggregation
- `aggregate()` - Advanced aggregation

**Windowing**:
- Tumbling - Fixed-size, non-overlapping
- Hopping - Overlapping windows
- Sliding - Event-driven
- Session - Gap-based user sessions

**Joins**:
- Stream-stream - Join two streams (within window)
- Stream-table - Enrich stream with table data
- Table-table - Join two tables (foreign key)

## Configuration Tuning

### Producer (High Throughput)

```python
producer = KafkaProducer(
    acks=1,  # Leader only (faster)
    compression_type='lz4',
    batch_size=32768,  # 32 KB
    linger_ms=20,  # Wait 20ms to batch
    buffer_memory=67108864  # 64 MB
)
```

### Producer (High Reliability)

```python
producer = KafkaProducer(
    acks='all',  # All ISR
    retries=3,
    enable_idempotence=True,
    max_in_flight_requests_per_connection=5
)
```

### Consumer (High Throughput)

```python
consumer = KafkaConsumer(
    fetch_min_bytes=1048576,  # 1 MB
    max_poll_records=1000,
    enable_auto_commit=True
)
```

### Consumer (High Reliability)

```python
consumer = KafkaConsumer(
    enable_auto_commit=False,
    isolation_level='read_committed',  # For exactly-once
    max_poll_interval_ms=600000  # 10 minutes
)
```

## Troubleshooting

### Producer Issues

**"Buffer full"**:
```python
buffer_memory=67108864  # Increase buffer
max_block_ms=120000  # Wait longer
```

**"Timeout"**:
```python
request_timeout_ms=60000  # Increase timeout
retries=5  # More retries
```

### Consumer Issues

**"Rebalancing too often"**:
```python
max_poll_interval_ms=600000  # Increase poll interval
session_timeout_ms=30000  # Increase session timeout
```

**"High lag"**:
- Add more consumers (up to partition count)
- Increase `max_poll_records`
- Optimize processing logic

### Broker Issues

**"Under-replicated partitions"**:
```bash
# Check broker health
kafka-topics.sh --describe --under-replicated-partitions

# Increase ISR
min.insync.replicas=2
```

**"Out of disk space"**:
```properties
log.retention.hours=24  # Reduce retention
log.cleanup.policy=delete
```

## Best Practices

1. **Always set timeouts** - Prevent hanging requests
2. **Enable compression** - Reduce network/disk usage (lz4 recommended)
3. **Use consumer groups** - Parallelize consumption
4. **Monitor lag** - Alert on high lag (> 10k messages)
5. **Replication factor 3** - Tolerate broker failures
6. **min.insync.replicas=2** - Durability guarantee
7. **Use Schema Registry** - Manage schema evolution
8. **Exactly-once for critical data** - Prevent duplicates
9. **Partition by key** - Maintain ordering
10. **Test failure scenarios** - Broker failure, network partition, etc.

## Resources

- Kafka docs: https://kafka.apache.org/documentation/
- Confluent docs: https://docs.confluent.io/
- Kafka Streams: https://kafka.apache.org/documentation/streams/
- ksqlDB: https://ksqldb.io/

## Cleanup

```bash
# Stop services
docker-compose down

# Remove volumes (clean slate)
docker-compose down -v

# ⚠️ WARNING: This permanently deletes all Kafka data
# Always backup important data before running
# Remove all Kafka data
rm -rf /tmp/kafka-logs /tmp/zookeeper
```
