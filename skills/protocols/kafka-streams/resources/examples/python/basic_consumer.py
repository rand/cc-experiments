#!/usr/bin/env python3
"""
Kafka Consumer Example

Demonstrates basic consumer patterns with manual offset management and error handling.

Requirements:
    pip install kafka-python

Usage:
    python basic_consumer.py
"""

from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata
from kafka.errors import KafkaError
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_consumer():
    """Create Kafka consumer with production-ready configuration"""
    consumer = KafkaConsumer(
        bootstrap_servers=['localhost:9092'],

        # Consumer group
        group_id='order-processor',

        # Deserialization
        key_deserializer=lambda k: k.decode('utf-8') if k else None,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),

        # Offset management
        auto_offset_reset='earliest',  # Start from beginning if no offset
        enable_auto_commit=False,  # Manual commit for reliability

        # Performance tuning
        fetch_min_bytes=1024,  # Min 1 KB per fetch
        fetch_max_wait_ms=500,  # Wait up to 500ms
        max_poll_records=500,  # Max records per poll
        max_poll_interval_ms=300000,  # 5 minutes max between polls

        # Session management
        session_timeout_ms=10000,  # 10 seconds
        heartbeat_interval_ms=3000  # 3 seconds
    )

    return consumer


def consume_with_auto_commit():
    """Example 1: Consume with automatic offset commits"""
    logger.info("\n=== Example 1: Auto-commit Consumer ===")

    consumer = KafkaConsumer(
        'orders',
        bootstrap_servers=['localhost:9092'],
        group_id='auto-commit-group',
        auto_offset_reset='earliest',
        enable_auto_commit=True,  # Auto-commit enabled
        auto_commit_interval_ms=5000,  # Commit every 5 seconds
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    try:
        count = 0
        for message in consumer:
            logger.info(
                f"Consumed: topic={message.topic}, "
                f"partition={message.partition}, "
                f"offset={message.offset}, "
                f"key={message.key}, "
                f"value={message.value}"
            )

            # Process message
            process_order(message.value)

            count += 1
            if count >= 10:  # Process 10 messages for demo
                break

    finally:
        consumer.close()


def consume_with_manual_commit():
    """Example 2: Consume with manual offset commits (at-least-once)"""
    logger.info("\n=== Example 2: Manual Commit Consumer ===")

    consumer = KafkaConsumer(
        'orders',
        bootstrap_servers=['localhost:9092'],
        group_id='manual-commit-group',
        auto_offset_reset='earliest',
        enable_auto_commit=False,  # Manual commit
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    try:
        count = 0
        for message in consumer:
            try:
                logger.info(f"Processing message at offset {message.offset}")

                # Process message
                process_order(message.value)

                # Commit offset after successful processing
                consumer.commit()
                logger.info(f"Committed offset {message.offset}")

                count += 1
                if count >= 10:
                    break

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Don't commit on error - message will be reprocessed

    finally:
        consumer.close()


def consume_with_batch_commit():
    """Example 3: Consume with batch commits (higher throughput)"""
    logger.info("\n=== Example 3: Batch Commit Consumer ===")

    consumer = KafkaConsumer(
        'orders',
        bootstrap_servers=['localhost:9092'],
        group_id='batch-commit-group',
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    try:
        batch_size = 10
        count = 0

        for message in consumer:
            logger.info(f"Processing message at offset {message.offset}")
            process_order(message.value)

            count += 1

            # Commit every N messages
            if count % batch_size == 0:
                consumer.commit()
                logger.info(f"Committed batch at offset {message.offset}")

            if count >= 30:
                break

    finally:
        # Commit remaining messages
        consumer.commit()
        consumer.close()


def consume_with_partition_control():
    """Example 4: Manual partition assignment and seeking"""
    logger.info("\n=== Example 4: Manual Partition Control ===")

    consumer = KafkaConsumer(
        bootstrap_servers=['localhost:9092'],
        group_id='partition-control-group',
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    try:
        # Manually assign partitions
        partition = TopicPartition('orders', 0)
        consumer.assign([partition])

        # Seek to specific offset
        consumer.seek(partition, 0)  # Start from offset 0

        logger.info(f"Assigned partition: {partition}")
        logger.info(f"Starting from offset 0")

        count = 0
        for message in consumer:
            logger.info(
                f"Consumed from partition {message.partition} "
                f"at offset {message.offset}"
            )

            count += 1
            if count >= 10:
                break

    finally:
        consumer.close()


def consume_multiple_topics():
    """Example 5: Consume from multiple topics"""
    logger.info("\n=== Example 5: Multiple Topics Consumer ===")

    consumer = KafkaConsumer(
        bootstrap_servers=['localhost:9092'],
        group_id='multi-topic-group',
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    # Subscribe to multiple topics
    consumer.subscribe(['orders', 'payments'])

    try:
        count = 0
        for message in consumer:
            logger.info(
                f"Consumed from {message.topic}: "
                f"partition={message.partition}, "
                f"offset={message.offset}, "
                f"value={message.value}"
            )

            # Route by topic
            if message.topic == 'orders':
                process_order(message.value)
            elif message.topic == 'payments':
                process_payment(message.value)

            count += 1
            if count >= 10:
                break

    finally:
        consumer.close()


def consume_with_headers():
    """Example 6: Access message headers"""
    logger.info("\n=== Example 6: Headers Consumer ===")

    consumer = KafkaConsumer(
        'orders',
        bootstrap_servers=['localhost:9092'],
        group_id='headers-group',
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    try:
        count = 0
        for message in consumer:
            # Extract headers
            headers = dict(message.headers or [])
            correlation_id = headers.get('correlation-id', b'').decode('utf-8')
            source = headers.get('source', b'').decode('utf-8')

            logger.info(
                f"Message headers: correlation_id={correlation_id}, "
                f"source={source}"
            )
            logger.info(f"Message value: {message.value}")

            count += 1
            if count >= 10:
                break

    finally:
        consumer.close()


def process_order(order_data):
    """Process order message"""
    order_id = order_data.get('order_id')
    amount = order_data.get('amount')
    logger.debug(f"Processing order {order_id}: ${amount}")


def process_payment(payment_data):
    """Process payment message"""
    payment_id = payment_data.get('payment_id')
    logger.debug(f"Processing payment {payment_id}")


def main():
    """Main consumer example"""
    logger.info("Starting Kafka consumer examples")

    try:
        # Run examples
        consume_with_auto_commit()
        consume_with_manual_commit()
        consume_with_batch_commit()
        consume_with_partition_control()
        consume_multiple_topics()
        consume_with_headers()

        logger.info("\nAll examples completed successfully")

    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    except Exception as e:
        logger.error(f"Error in consumer: {e}")


if __name__ == '__main__':
    main()
