"""
Pub-Sub with Topic Exchange - Python Implementation

Broadcasts messages to multiple subscribers with topic-based filtering.

Usage:
    # Start subscribers (different terminals)
    python pubsub_topic.py subscribe "order.#"
    python pubsub_topic.py subscribe "order.*.us"
    python pubsub_topic.py subscribe "#.critical"

    # Publish messages
    python pubsub_topic.py publish "order.created.us" "New order from US"
    python pubsub_topic.py publish "order.cancelled.eu" "Order cancelled"
    python pubsub_topic.py publish "user.login.critical" "Critical login event"
"""

import argparse
import pika
import sys


def get_connection(url: str = 'amqp://localhost') -> pika.BlockingConnection:
    """Create connection to RabbitMQ."""
    parameters = pika.URLParameters(url)
    return pika.BlockingConnection(parameters)


def setup_exchange(channel: pika.channel.Channel) -> None:
    """Declare topic exchange."""
    channel.exchange_declare(
        exchange='events',
        exchange_type='topic',
        durable=True
    )


def publish_event(routing_key: str, message: str, url: str = 'amqp://localhost') -> None:
    """
    Publish event to topic exchange.

    Args:
        routing_key: Topic routing key (e.g., 'order.created.us')
        message: Event message
        url: AMQP URL
    """
    connection = get_connection(url)
    try:
        channel = connection.channel()
        setup_exchange(channel)

        channel.basic_publish(
            exchange='events',
            routing_key=routing_key,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
                content_type='text/plain'
            )
        )
        print(f"Published to '{routing_key}': {message}")
    finally:
        connection.close()


def subscribe_to_topics(binding_keys: list, url: str = 'amqp://localhost') -> None:
    """
    Subscribe to topic patterns.

    Args:
        binding_keys: List of topic patterns (e.g., ['order.*', '*.critical'])
        url: AMQP URL
    """
    connection = get_connection(url)
    channel = connection.channel()
    setup_exchange(channel)

    # Create exclusive queue for this subscriber
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # Bind to each topic pattern
    for binding_key in binding_keys:
        channel.queue_bind(
            exchange='events',
            queue=queue_name,
            routing_key=binding_key
        )
        print(f"Subscribed to pattern: {binding_key}")

    def callback(ch, method, properties, body):
        """Handle received event."""
        message = body.decode('utf-8')
        print(f"\nReceived [{method.routing_key}]: {message}")

    channel.basic_consume(
        queue=queue_name,
        on_message_callback=callback,
        auto_ack=True
    )

    print("\nWaiting for events. Press CTRL+C to exit.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        channel.stop_consuming()
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description='Topic-based Pub-Sub Example')
    parser.add_argument(
        'action',
        choices=['publish', 'subscribe'],
        help='Action to perform'
    )
    parser.add_argument(
        'key_or_pattern',
        help='Routing key (for publish) or binding pattern (for subscribe)'
    )
    parser.add_argument(
        'message',
        nargs='?',
        default='Event message',
        help='Message (for publish only)'
    )
    parser.add_argument(
        '--url',
        default='amqp://localhost',
        help='AMQP URL (default: amqp://localhost)'
    )

    args = parser.parse_args()

    if args.action == 'publish':
        publish_event(args.key_or_pattern, args.message, args.url)
    else:
        # Support multiple patterns separated by commas
        patterns = [p.strip() for p in args.key_or_pattern.split(',')]
        subscribe_to_topics(patterns, args.url)


if __name__ == '__main__':
    main()
