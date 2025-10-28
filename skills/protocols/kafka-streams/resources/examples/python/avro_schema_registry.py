#!/usr/bin/env python3
"""
Kafka Avro Schema Registry Example

Demonstrates using Avro serialization with Schema Registry for schema evolution.

Requirements:
    pip install confluent-kafka[avro] avro-python3

Usage:
    # Start Schema Registry first
    docker-compose up -d schema-registry

    python avro_schema_registry.py
"""

from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer, AvroConsumer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Avro schema definitions
USER_SCHEMA_V1 = """
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {"name": "id", "type": "string"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": "string"}
  ]
}
"""

USER_SCHEMA_V2 = """
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {"name": "id", "type": "string"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": "string"},
    {"name": "age", "type": ["null", "int"], "default": null},
    {"name": "created_at", "type": ["null", "long"], "default": null}
  ]
}
"""

ORDER_SCHEMA = """
{
  "type": "record",
  "name": "Order",
  "namespace": "com.example",
  "fields": [
    {"name": "order_id", "type": "string"},
    {"name": "user_id", "type": "string"},
    {"name": "amount", "type": "double"},
    {"name": "status", "type": {
      "type": "enum",
      "name": "OrderStatus",
      "symbols": ["PENDING", "CONFIRMED", "SHIPPED", "DELIVERED", "CANCELLED"]
    }},
    {"name": "items", "type": {
      "type": "array",
      "items": "string"
    }},
    {"name": "timestamp", "type": "long"}
  ]
}
"""


def create_avro_producer(schema_registry_url='http://localhost:8081'):
    """Create Avro producer with Schema Registry"""
    value_schema = avro.loads(USER_SCHEMA_V2)

    producer_config = {
        'bootstrap.servers': 'localhost:9092',
        'schema.registry.url': schema_registry_url
    }

    producer = AvroProducer(
        producer_config,
        default_value_schema=value_schema
    )

    return producer


def create_avro_consumer(schema_registry_url='http://localhost:8081'):
    """Create Avro consumer with Schema Registry"""
    consumer_config = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'avro-consumer-group',
        'schema.registry.url': schema_registry_url,
        'auto.offset.reset': 'earliest'
    }

    consumer = AvroConsumer(consumer_config)
    return consumer


def produce_avro_messages():
    """Produce messages with Avro serialization"""
    logger.info("Starting Avro producer")

    producer = create_avro_producer()

    try:
        # User data (V2 schema with optional fields)
        users = [
            {
                'id': 'user-1',
                'name': 'Alice Smith',
                'email': 'alice@example.com',
                'age': 30,
                'created_at': 1698432000000
            },
            {
                'id': 'user-2',
                'name': 'Bob Jones',
                'email': 'bob@example.com',
                'age': None,  # Optional field
                'created_at': 1698432100000
            },
            {
                'id': 'user-3',
                'name': 'Charlie Brown',
                'email': 'charlie@example.com',
                # age and created_at use defaults (null)
            }
        ]

        for user in users:
            # Send message (Avro serialization automatic)
            producer.produce(topic='users-avro', value=user)
            logger.info(f"Produced user: {user['name']}")

        # Flush to ensure delivery
        producer.flush()
        logger.info("All messages flushed")

    finally:
        producer.close()


def consume_avro_messages():
    """Consume messages with Avro deserialization"""
    logger.info("Starting Avro consumer")

    consumer = create_avro_consumer()
    consumer.subscribe(['users-avro'])

    try:
        message_count = 0
        while message_count < 10:  # Consume 10 messages for demo
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                logger.error(f"Consumer error: {msg.error()}")
                continue

            # Value is automatically deserialized from Avro
            user = msg.value()
            logger.info(f"Consumed user: {user}")
            logger.info(f"  Name: {user['name']}")
            logger.info(f"  Email: {user['email']}")
            logger.info(f"  Age: {user.get('age', 'Not provided')}")

            message_count += 1

    except KeyboardInterrupt:
        logger.info("Consumer interrupted")
    finally:
        consumer.close()


def produce_orders_with_complex_schema():
    """Produce orders with complex Avro schema (enums, arrays)"""
    logger.info("Starting orders producer with complex schema")

    order_schema = avro.loads(ORDER_SCHEMA)

    producer_config = {
        'bootstrap.servers': 'localhost:9092',
        'schema.registry.url': 'http://localhost:8081'
    }

    producer = AvroProducer(
        producer_config,
        default_value_schema=order_schema
    )

    try:
        orders = [
            {
                'order_id': 'order-1',
                'user_id': 'user-1',
                'amount': 99.99,
                'status': 'PENDING',
                'items': ['item-1', 'item-2', 'item-3'],
                'timestamp': 1698432000000
            },
            {
                'order_id': 'order-2',
                'user_id': 'user-2',
                'amount': 149.50,
                'status': 'CONFIRMED',
                'items': ['item-5'],
                'timestamp': 1698432100000
            }
        ]

        for order in orders:
            producer.produce(topic='orders-avro', value=order)
            logger.info(f"Produced order: {order['order_id']} - ${order['amount']}")

        producer.flush()

    finally:
        producer.close()


def demonstrate_schema_evolution():
    """
    Demonstrate schema evolution:
    1. Producer uses V2 schema (with age, created_at)
    2. Old consumers with V1 schema can still read (backward compatible)
    3. New consumers can read old messages (forward compatible)
    """
    logger.info("\n=== Schema Evolution Demo ===")

    # V1 Schema (old)
    logger.info("Using V1 schema (id, name, email)")

    # V2 Schema (new, with optional fields)
    logger.info("Using V2 schema (id, name, email, age, created_at)")
    logger.info("New fields have defaults, so backward compatible")

    # Produce with V2
    produce_avro_messages()

    # Consume (works with both V1 and V2)
    consume_avro_messages()


def main():
    """Main example"""
    logger.info("Starting Avro Schema Registry examples")
    logger.info("Make sure Schema Registry is running on http://localhost:8081")

    try:
        # Example 1: Basic Avro producer/consumer
        logger.info("\n=== Example 1: Basic Avro Messages ===")
        produce_avro_messages()
        consume_avro_messages()

        # Example 2: Complex schema with enums and arrays
        logger.info("\n=== Example 2: Complex Schema ===")
        produce_orders_with_complex_schema()

        # Example 3: Schema evolution
        logger.info("\n=== Example 3: Schema Evolution ===")
        demonstrate_schema_evolution()

        logger.info("\nAvro examples completed")

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
