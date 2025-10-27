#!/usr/bin/env python3
"""
Kafka Producer Example

Demonstrates basic producer patterns with error handling, retries, and callbacks.

Requirements:
    pip install kafka-python

Usage:
    python basic_producer.py
"""

from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_producer():
    """Create Kafka producer with production-ready configuration"""
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],

        # Serialization
        key_serializer=lambda k: k.encode('utf-8') if k else None,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),

        # Durability and reliability
        acks='all',  # Wait for all in-sync replicas
        retries=3,  # Retry on failure
        max_in_flight_requests_per_connection=5,  # Ordering with retries

        # Performance tuning
        compression_type='lz4',  # Fast compression
        batch_size=16384,  # 16 KB batches
        linger_ms=10,  # Wait up to 10ms to batch messages
        buffer_memory=33554432,  # 32 MB buffer

        # Idempotence (exactly-once producer)
        enable_idempotence=True,

        # Timeouts
        request_timeout_ms=30000,  # 30 seconds
        max_block_ms=60000  # Block for 60s if buffer full
    )

    return producer


def on_send_success(record_metadata):
    """Callback for successful send"""
    logger.info(
        f"Message delivered to {record_metadata.topic} "
        f"[partition {record_metadata.partition}] "
        f"at offset {record_metadata.offset}"
    )


def on_send_error(exception):
    """Callback for send failure"""
    logger.error(f"Failed to send message: {exception}")


def send_message_sync(producer, topic, key, value):
    """Send message synchronously (blocking)"""
    try:
        # Send and wait for result
        future = producer.send(topic, key=key, value=value)
        record_metadata = future.get(timeout=10)

        logger.info(
            f"Sent message (sync): key={key}, "
            f"partition={record_metadata.partition}, "
            f"offset={record_metadata.offset}"
        )
        return True
    except KafkaError as e:
        logger.error(f"Error sending message (sync): {e}")
        return False


def send_message_async(producer, topic, key, value):
    """Send message asynchronously (non-blocking)"""
    try:
        # Send with callbacks
        future = producer.send(topic, key=key, value=value)
        future.add_callback(on_send_success)
        future.add_errback(on_send_error)
        return True
    except Exception as e:
        logger.error(f"Error sending message (async): {e}")
        return False


def send_message_with_headers(producer, topic, key, value, headers):
    """Send message with metadata headers"""
    try:
        future = producer.send(
            topic,
            key=key,
            value=value,
            headers=headers
        )
        record_metadata = future.get(timeout=10)

        logger.info(
            f"Sent message with headers: key={key}, headers={headers}"
        )
        return True
    except KafkaError as e:
        logger.error(f"Error sending message with headers: {e}")
        return False


def send_batch_messages(producer, topic, messages):
    """Send batch of messages efficiently"""
    futures = []

    for key, value in messages:
        try:
            future = producer.send(topic, key=key, value=value)
            futures.append(future)
        except Exception as e:
            logger.error(f"Error queuing message: {e}")

    # Wait for all messages to be sent
    for future in futures:
        try:
            future.get(timeout=10)
        except KafkaError as e:
            logger.error(f"Error in batch: {e}")

    logger.info(f"Sent batch of {len(messages)} messages")


def main():
    """Main producer example"""
    logger.info("Starting Kafka producer example")

    # Create producer
    producer = create_producer()

    try:
        # Example 1: Synchronous send
        logger.info("\n=== Example 1: Synchronous Send ===")
        send_message_sync(
            producer,
            'orders',
            key='order-123',
            value={'order_id': 'order-123', 'amount': 99.99, 'status': 'pending'}
        )

        # Example 2: Asynchronous send
        logger.info("\n=== Example 2: Asynchronous Send ===")
        for i in range(5):
            send_message_async(
                producer,
                'orders',
                key=f'order-{i}',
                value={'order_id': f'order-{i}', 'amount': 10.0 * (i + 1)}
            )

        # Flush to ensure async messages are sent
        producer.flush()
        logger.info("Flushed async messages")

        # Example 3: Send with headers
        logger.info("\n=== Example 3: Send with Headers ===")
        headers = [
            ('correlation-id', b'abc-123'),
            ('source', b'order-service'),
            ('timestamp', str(time.time()).encode('utf-8'))
        ]
        send_message_with_headers(
            producer,
            'orders',
            key='order-456',
            value={'order_id': 'order-456', 'amount': 149.99},
            headers=headers
        )

        # Example 4: Batch send
        logger.info("\n=== Example 4: Batch Send ===")
        batch_messages = [
            (f'order-batch-{i}', {'order_id': f'order-batch-{i}', 'amount': 5.0 * i})
            for i in range(100)
        ]
        send_batch_messages(producer, 'orders', batch_messages)

        # Example 5: Send to multiple topics
        logger.info("\n=== Example 5: Multiple Topics ===")
        send_message_sync(
            producer,
            'payments',
            key='payment-123',
            value={'payment_id': 'payment-123', 'order_id': 'order-123', 'status': 'completed'}
        )

        logger.info("\nAll examples completed successfully")

    except KeyboardInterrupt:
        logger.info("Producer interrupted by user")
    except Exception as e:
        logger.error(f"Error in producer: {e}")
    finally:
        # Close producer
        logger.info("Closing producer...")
        producer.close()
        logger.info("Producer closed")


if __name__ == '__main__':
    main()
