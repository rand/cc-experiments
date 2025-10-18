---
name: data-stream-processing
description: Processing real-time event streams (clicks, IoT, logs)
---



# Stream Processing

**Scope**: Kafka, event streaming, windowing, stateful processing
**Lines**: 368
**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)

## When to Use This Skill

Use this skill when:
- Processing real-time event streams (clicks, IoT, logs)
- Building event-driven architectures with Kafka
- Implementing windowing aggregations (tumbling, sliding, session)
- Managing stateful stream processing
- Handling exactly-once semantics
- Designing stream joins and enrichment patterns
- Working with Kafka Streams, Flink, or custom consumers

## Core Concepts

### Stream vs Batch
```
Batch Processing
  → Bounded datasets, scheduled runs
  → Use when: Historical analysis, daily reports
  → Tools: Airflow, Spark batch jobs

Stream Processing
  → Unbounded datasets, continuous processing
  → Use when: Real-time alerts, live dashboards
  → Tools: Kafka Streams, Flink, ksqlDB
```

### Event Time vs Processing Time
```
Event Time
  → When event actually occurred
  → Use when: Order matters, late data possible
  → Requires: Timestamps in events, watermarks

Processing Time
  → When event processed by system
  → Use when: Latency critical, order irrelevant
  → Simpler but less accurate for time-based logic
```

### Windowing Types
```
Tumbling Window
  → Fixed, non-overlapping intervals
  → Example: Count events per 5-minute window
  → Use when: Periodic aggregations

Sliding Window
  → Fixed size, overlapping intervals
  → Example: Moving average over last 10 minutes
  → Use when: Continuous metrics

Session Window
  → Dynamic size based on inactivity gap
  → Example: User sessions with 30-min timeout
  → Use when: User behavior analysis

Global Window
  → All events in single window
  → Use when: No time-based grouping needed
```

### Delivery Guarantees
```
At-Most-Once
  → May lose messages
  → Fastest, use for metrics/logs

At-Least-Once
  → May duplicate messages
  → Common default, requires idempotent processing

Exactly-Once
  → No loss, no duplication
  → Kafka transactions, complex but correct
```

## Patterns

### Pattern 1: Kafka Producer (Python)

```python
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
from typing import Dict, Any
from datetime import datetime

class EventProducer:
    def __init__(self, bootstrap_servers: list[str], topic: str):
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',  # Wait for all replicas (strongest guarantee)
            retries=3,
            max_in_flight_requests_per_connection=1,  # Maintain order
            compression_type='gzip'
        )

    def send_event(self, event: Dict[str, Any], key: str = None) -> bool:
        """Send event with error handling"""
        # Add metadata
        event['_timestamp'] = datetime.utcnow().isoformat()

        try:
            future = self.producer.send(
                self.topic,
                key=key,
                value=event
            )

            # Block for 'synchronous' sends
            record_metadata = future.get(timeout=10)

            print(f"Sent to {record_metadata.topic} "
                  f"partition {record_metadata.partition} "
                  f"offset {record_metadata.offset}")
            return True

        except KafkaError as e:
            print(f"Failed to send event: {e}")
            return False

    def send_batch(self, events: list[Dict[str, Any]]):
        """Send batch asynchronously"""
        for event in events:
            self.producer.send(self.topic, value=event)

        self.producer.flush()  # Wait for all to complete

    def close(self):
        self.producer.close()

# Usage
producer = EventProducer(['localhost:9092'], 'user-events')

event = {
    'user_id': 'user123',
    'action': 'page_view',
    'page': '/product/456',
    'session_id': 'session789'
}

producer.send_event(event, key='user123')  # Partition by user_id
producer.close()
```

### Pattern 2: Kafka Consumer with Offset Management

```python
from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata
from typing import Callable
import json

class EventConsumer:
    def __init__(
        self,
        bootstrap_servers: list[str],
        topic: str,
        group_id: str,
        auto_commit: bool = False
    ):
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset='earliest',  # Start from beginning if no offset
            enable_auto_commit=auto_commit,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            max_poll_records=500,
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000
        )
        self.processed_count = 0

    def consume(
        self,
        process_fn: Callable[[dict], bool],
        commit_interval: int = 100
    ):
        """Consume with manual offset management"""
        buffer = []

        try:
            for message in self.consumer:
                event = message.value

                # Process event
                success = process_fn(event)

                if success:
                    buffer.append(message)
                    self.processed_count += 1

                    # Commit offsets periodically
                    if len(buffer) >= commit_interval:
                        self._commit_offsets(buffer)
                        buffer = []
                else:
                    # Handle failure (DLQ, retry, log)
                    self._handle_failure(message)

        except KeyboardInterrupt:
            print("Shutting down...")

        finally:
            if buffer:
                self._commit_offsets(buffer)
            self.consumer.close()

    def _commit_offsets(self, messages: list):
        """Commit offsets for processed messages"""
        offsets = {}

        for msg in messages:
            tp = TopicPartition(msg.topic, msg.partition)
            offsets[tp] = OffsetAndMetadata(msg.offset + 1, None)

        self.consumer.commit(offsets)
        print(f"Committed {len(messages)} offsets")

    def _handle_failure(self, message):
        """Send to dead letter queue"""
        print(f"Failed to process: {message.value}")
        # Could send to DLQ topic here

# Usage
def process_event(event: dict) -> bool:
    try:
        user_id = event['user_id']
        action = event['action']

        # Business logic
        print(f"User {user_id} performed {action}")

        # Could write to database, call API, etc.
        return True

    except Exception as e:
        print(f"Error processing event: {e}")
        return False

consumer = EventConsumer(
    ['localhost:9092'],
    'user-events',
    group_id='analytics-pipeline'
)

consumer.consume(process_event, commit_interval=100)
```

### Pattern 3: Kafka Streams (Windowing & Aggregation)

```java
// Java - Kafka Streams API
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.*;
import java.time.Duration;

public class EventAggregator {
    public static void main(String[] args) {
        StreamsBuilder builder = new StreamsBuilder();

        // Input stream
        KStream<String, UserEvent> events = builder.stream(
            "user-events",
            Consumed.with(Serdes.String(), new UserEventSerde())
        );

        // Tumbling window: Count events per user per 5 minutes
        KTable<Windowed<String>, Long> userEventCounts = events
            .groupByKey()
            .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(5)))
            .count();

        // Sliding window: Moving average of event values
        KTable<Windowed<String>, Double> movingAverage = events
            .groupByKey()
            .windowedBy(
                SlidingWindows.ofTimeDifferenceWithNoGrace(Duration.ofMinutes(10))
            )
            .aggregate(
                () -> new AggregateState(0.0, 0),
                (key, event, aggregate) -> {
                    aggregate.sum += event.getValue();
                    aggregate.count += 1;
                    return aggregate;
                },
                Materialized.with(Serdes.String(), new AggregateStateSerde())
            )
            .mapValues(agg -> agg.sum / agg.count);

        // Session window: User sessions with 30-minute inactivity gap
        KTable<Windowed<String>, Long> sessions = events
            .groupByKey()
            .windowedBy(
                SessionWindows.ofInactivityGapWithNoGrace(Duration.ofMinutes(30))
            )
            .count();

        // Output to topics
        userEventCounts
            .toStream()
            .map((key, value) -> new KeyValue<>(
                key.key() + "@" + key.window().start(),
                value
            ))
            .to("event-counts-per-5min");

        // Build and start
        KafkaStreams streams = new KafkaStreams(builder.build(), getConfig());
        streams.start();

        Runtime.getRuntime().addShutdownHook(new Thread(streams::close));
    }
}
```

### Pattern 4: Stream Joins (Python with Faust)

```python
# Python - Faust framework (Kafka Streams alternative)
import faust
from datetime import timedelta

app = faust.App(
    'stream-joins',
    broker='kafka://localhost:9092',
    store='rocksdb://'
)

# Define models
class ClickEvent(faust.Record):
    user_id: str
    page: str
    timestamp: float

class PurchaseEvent(faust.Record):
    user_id: str
    product_id: str
    amount: float
    timestamp: float

class EnrichedPurchase(faust.Record):
    user_id: str
    product_id: str
    amount: float
    recent_pages: list[str]

# Topics
clicks_topic = app.topic('clicks', value_type=ClickEvent)
purchases_topic = app.topic('purchases', value_type=PurchaseEvent)

# Tables for stateful processing
recent_clicks = app.Table(
    'recent_clicks',
    default=list,
    on_window_close=lambda key, values: print(f"Window closed for {key}")
).tumbling(timedelta(minutes=10), expires=timedelta(hours=1))

# Stream join pattern
@app.agent(purchases_topic)
async def enrich_purchases(purchases):
    async for purchase in purchases:
        # Get recent clicks for user from state table
        clicks = recent_clicks[purchase.user_id].current()

        enriched = EnrichedPurchase(
            user_id=purchase.user_id,
            product_id=purchase.product_id,
            amount=purchase.amount,
            recent_pages=[c.page for c in clicks] if clicks else []
        )

        # Send to enriched topic
        await app.topic('enriched-purchases').send(value=enriched)

# Maintain click state
@app.agent(clicks_topic)
async def track_clicks(clicks):
    async for click in clicks:
        recent_clicks[click.user_id].current().append(click)

# Windowed aggregation
@app.agent(purchases_topic)
async def revenue_per_window(purchases):
    async for purchase in purchases.group_by(lambda p: 'all'):
        # Aggregate in 5-minute tumbling windows
        window = recent_clicks.current()
        # Process aggregation
        yield purchase

if __name__ == '__main__':
    app.main()
```

### Pattern 5: Exactly-Once Semantics (Transactional Producer)

```python
from kafka import KafkaProducer, KafkaConsumer
from kafka.coordinator.assignors.range import RangePartitionAssignor
import json

class ExactlyOnceProcessor:
    def __init__(
        self,
        bootstrap_servers: list[str],
        input_topic: str,
        output_topic: str,
        group_id: str
    ):
        self.input_topic = input_topic
        self.output_topic = output_topic

        # Transactional producer
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            transactional_id=f'{group_id}-producer',
            enable_idempotence=True,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

        # Consumer with read_committed isolation
        self.consumer = KafkaConsumer(
            input_topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=False,
            isolation_level='read_committed',  # Only read committed messages
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )

        self.producer.init_transactions()

    def process(self, transform_fn):
        """Process with exactly-once semantics"""
        try:
            for message in self.consumer:
                self.producer.begin_transaction()

                try:
                    # Transform event
                    input_event = message.value
                    output_event = transform_fn(input_event)

                    # Send to output topic
                    self.producer.send(self.output_topic, value=output_event)

                    # Commit input offset within transaction
                    offsets = {
                        TopicPartition(message.topic, message.partition):
                        OffsetAndMetadata(message.offset + 1, None)
                    }
                    self.producer.send_offsets_to_transaction(
                        offsets,
                        self.consumer.config['group_id']
                    )

                    # Commit transaction (atomic)
                    self.producer.commit_transaction()

                except Exception as e:
                    print(f"Error processing, aborting transaction: {e}")
                    self.producer.abort_transaction()

        finally:
            self.producer.close()
            self.consumer.close()

# Usage
processor = ExactlyOnceProcessor(
    ['localhost:9092'],
    'input-events',
    'output-events',
    'exactly-once-group'
)

def transform(event):
    # Idempotent transformation
    return {
        'user_id': event['user_id'],
        'processed_value': event['value'] * 2,
        'processed_at': datetime.utcnow().isoformat()
    }

processor.process(transform)
```

## Quick Reference

### Kafka CLI Commands
```bash
# Create topic
kafka-topics --create --topic my-topic \
  --partitions 3 --replication-factor 2 \
  --bootstrap-server localhost:9092

# List topics
kafka-topics --list --bootstrap-server localhost:9092

# Describe topic
kafka-topics --describe --topic my-topic \
  --bootstrap-server localhost:9092

# Consume from beginning
kafka-console-consumer --topic my-topic \
  --from-beginning --bootstrap-server localhost:9092

# Produce messages
kafka-console-producer --topic my-topic \
  --bootstrap-server localhost:9092

# Consumer groups
kafka-consumer-groups --list --bootstrap-server localhost:9092
kafka-consumer-groups --describe --group my-group \
  --bootstrap-server localhost:9092

# Reset offsets
kafka-consumer-groups --group my-group \
  --reset-offsets --to-earliest --topic my-topic \
  --execute --bootstrap-server localhost:9092
```

### Windowing Cheat Sheet
```python
# Tumbling (Faust)
table.tumbling(timedelta(minutes=5))

# Hopping/Sliding (Faust)
table.hopping(size=timedelta(minutes=10), step=timedelta(minutes=2))

# Kafka Streams (Java)
TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(5))
SlidingWindows.ofTimeDifferenceWithNoGrace(Duration.ofMinutes(10))
SessionWindows.ofInactivityGapWithNoGrace(Duration.ofMinutes(30))
```

### Partitioning Strategies
```python
# By key (ensures same key -> same partition)
producer.send(topic, key='user123', value=event)

# Round-robin (no key)
producer.send(topic, value=event)

# Custom partitioner
from kafka.partitioner import Murmur2Partitioner
producer = KafkaProducer(partitioner=Murmur2Partitioner())
```

## Anti-Patterns

```
❌ NEVER: Auto-commit without idempotent processing
   → Use manual commits with exactly-once semantics

❌ NEVER: Process events out of order within partition
   → Kafka guarantees order per partition, maintain it

❌ NEVER: Block consumer loop with slow processing
   → Use async processing or separate worker threads

❌ NEVER: Ignore late arriving data
   → Set watermarks and allowed lateness windows

❌ NEVER: Use global state without partitioning
   → State must be partitioned like input data

❌ NEVER: Skip error handling on deserialization
   → Use try-except, send bad records to DLQ

❌ NEVER: Create too many partitions initially
   → Start small, scale up based on throughput needs

❌ NEVER: Use processing time for event-time logic
   → Use event timestamps for accurate windowing

❌ NEVER: Commit offsets before processing completes
   → Commit only after successful processing/write

❌ NEVER: Ignore consumer lag monitoring
   → Monitor lag, alert on growing backlog
```

## Related Skills

- `etl-patterns.md` - Batch alternatives to stream processing
- `batch-processing.md` - Hybrid batch + stream architectures
- `pipeline-orchestration.md` - Managing stream applications
- `data-validation.md` - Schema validation for streams

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
