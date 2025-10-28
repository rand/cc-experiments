#!/usr/bin/env python3
"""
Kafka Exactly-Once Producer Example

Demonstrates exactly-once semantics using transactions.
Ensures atomic writes across multiple topics.

Requirements:
    pip install kafka-python

Usage:
    python exactly_once_producer.py
"""

from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_transactional_producer(transactional_id):
    """Create producer with exactly-once semantics"""
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],

        # Serialization
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),

        # Exactly-once configuration
        transactional_id=transactional_id,  # Unique ID per producer instance
        enable_idempotence=True,  # Prevent duplicates
        acks='all',  # Wait for all ISR
        max_in_flight_requests_per_connection=5,

        # Retries
        retries=3,
        request_timeout_ms=30000
    )

    return producer


def send_transactional_messages(producer, order_id, order_data, payment_data):
    """
    Send messages to multiple topics atomically.
    Either all messages are written, or none.
    """
    try:
        # Begin transaction
        producer.begin_transaction()
        logger.info(f"Transaction started for order {order_id}")

        # Send order event
        producer.send('orders', key=order_id.encode('utf-8'), value=order_data)
        logger.info(f"Sent order: {order_data}")

        # Send payment event
        producer.send('payments', key=order_id.encode('utf-8'), value=payment_data)
        logger.info(f"Sent payment: {payment_data}")

        # Commit transaction (atomic)
        producer.commit_transaction()
        logger.info(f"Transaction committed for order {order_id}")

        return True

    except Exception as e:
        logger.error(f"Transaction failed: {e}")

        # Rollback transaction
        try:
            producer.abort_transaction()
            logger.info("Transaction aborted")
        except Exception as abort_error:
            logger.error(f"Failed to abort transaction: {abort_error}")

        return False


def process_order_with_exactly_once(transactional_id, order_id):
    """
    Process order with exactly-once guarantees.
    Prevents duplicate orders even on retries.
    """
    producer = create_transactional_producer(transactional_id)

    try:
        # Initialize transactions
        producer.init_transactions()
        logger.info("Transactions initialized")

        # Order data
        order_data = {
            'order_id': order_id,
            'user_id': 'user-123',
            'items': ['item-1', 'item-2'],
            'total': 99.99,
            'status': 'pending'
        }

        # Payment data
        payment_data = {
            'payment_id': f'payment-{order_id}',
            'order_id': order_id,
            'amount': 99.99,
            'status': 'processing'
        }

        # Send transactionally
        success = send_transactional_messages(
            producer,
            order_id,
            order_data,
            payment_data
        )

        if success:
            logger.info(f"Order {order_id} processed successfully with exactly-once guarantee")
        else:
            logger.error(f"Order {order_id} failed")

        return success

    finally:
        producer.close()


def send_multiple_transactions():
    """Send multiple transactions in sequence"""
    transactional_id = 'order-processor-1'
    producer = create_transactional_producer(transactional_id)

    try:
        producer.init_transactions()

        # Process multiple orders
        for i in range(5):
            order_id = f'order-{i+1}'

            try:
                producer.begin_transaction()

                # Order event
                order_data = {
                    'order_id': order_id,
                    'amount': 10.0 * (i + 1),
                    'status': 'pending'
                }
                producer.send('orders', key=order_id.encode('utf-8'), value=order_data)

                # Inventory event
                inventory_data = {
                    'order_id': order_id,
                    'action': 'reserve',
                    'items': ['item-1']
                }
                producer.send('inventory', key=order_id.encode('utf-8'), value=inventory_data)

                # Commit
                producer.commit_transaction()
                logger.info(f"Transaction {i+1} committed: {order_id}")

            except Exception as e:
                logger.error(f"Transaction {i+1} failed: {e}")
                producer.abort_transaction()

    finally:
        producer.close()


def main():
    """Main example"""
    logger.info("Starting exactly-once producer example")

    # Example 1: Single transaction
    logger.info("\n=== Example 1: Single Transaction ===")
    process_order_with_exactly_once('order-processor-1', 'order-abc123')

    # Example 2: Multiple transactions
    logger.info("\n=== Example 2: Multiple Transactions ===")
    send_multiple_transactions()

    logger.info("\nExactly-once examples completed")


if __name__ == '__main__':
    main()
