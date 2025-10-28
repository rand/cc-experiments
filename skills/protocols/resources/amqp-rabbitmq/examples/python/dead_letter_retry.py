"""
Dead Letter Exchange with Retry Logic - Python Implementation

Implements exponential backoff retry using dead letter exchanges and TTL.

Usage:
    # Start consumer with retry logic
    python dead_letter_retry.py

    # The consumer will automatically retry failed messages with exponential backoff
"""

import argparse
import pika
import json
import random
import time


def get_connection(url: str = 'amqp://localhost') -> pika.BlockingConnection:
    """Create connection to RabbitMQ."""
    parameters = pika.URLParameters(url)
    return pika.BlockingConnection(parameters)


def setup_queues_with_retry(channel: pika.channel.Channel):
    """
    Setup queue topology with DLX and retry queues.

    Topology:
    - Main queue (tasks)
    - Dead letter exchange (retry)
    - Retry queues with increasing TTL (1s, 5s, 15s, 60s)
    - Failed queue (max retries exceeded)
    """
    # Main task queue with DLX
    channel.queue_declare(
        queue='tasks',
        durable=True,
        arguments={
            'x-dead-letter-exchange': 'retry',
            'x-dead-letter-routing-key': 'tasks.retry'
        }
    )

    # Retry exchange
    channel.exchange_declare(
        exchange='retry',
        exchange_type='direct',
        durable=True
    )

    # Retry queues with increasing TTL
    retry_delays = [1000, 5000, 15000, 60000]  # milliseconds

    for delay in retry_delays:
        queue_name = f'tasks.retry.{delay}'
        channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments={
                'x-message-ttl': delay,  # TTL before requeue
                'x-dead-letter-exchange': '',  # Default exchange
                'x-dead-letter-routing-key': 'tasks'  # Back to main queue
            }
        )
        channel.queue_bind(
            exchange='retry',
            queue=queue_name,
            routing_key=str(delay)
        )

    # Failed messages queue (max retries)
    channel.queue_declare(queue='tasks.failed', durable=True)
    channel.queue_bind(
        exchange='retry',
        queue='tasks.failed',
        routing_key='failed'
    )


def publish_task(task_data: str, url: str = 'amqp://localhost'):
    """
    Publish task to main queue.

    Args:
        task_data: Task data
        url: AMQP URL
    """
    connection = get_connection(url)
    try:
        channel = connection.channel()
        setup_queues_with_retry(channel)

        channel.basic_publish(
            exchange='',
            routing_key='tasks',
            body=json.dumps({'data': task_data, 'retry_count': 0}),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json'
            )
        )
        print(f"Published task: {task_data}")
    finally:
        connection.close()


def process_task(task: dict) -> bool:
    """
    Process task (simulates random failures).

    Args:
        task: Task data

    Returns:
        True if successful, False if failed
    """
    print(f"Processing: {task['data']}")

    # Simulate processing with 30% failure rate
    time.sleep(random.uniform(0.5, 2))

    if random.random() < 0.3:
        print(f"  FAILED: {task['data']}")
        return False

    print(f"  SUCCESS: {task['data']}")
    return True


def consume_with_retry(url: str = 'amqp://localhost'):
    """
    Consume tasks with automatic retry logic.

    Args:
        url: AMQP URL
    """
    connection = get_connection(url)
    channel = connection.channel()
    setup_queues_with_retry(channel)

    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        """Process message with retry logic."""
        task = json.loads(body)
        retry_count = task.get('retry_count', 0)
        max_retries = 3

        print(f"\n[Attempt {retry_count + 1}/{max_retries + 1}] Processing task")

        # Try to process
        success = process_task(task)

        if success:
            # Success: acknowledge
            print("  Acknowledging successful processing")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            # Failed: retry with backoff or move to failed queue
            if retry_count < max_retries:
                # Increment retry count
                task['retry_count'] = retry_count + 1

                # Calculate delay
                retry_delays = [1000, 5000, 15000, 60000]
                delay = retry_delays[min(retry_count, len(retry_delays) - 1)]

                print(f"  Retrying after {delay}ms (attempt {retry_count + 1}/{max_retries})")

                # Publish to retry queue
                ch.basic_publish(
                    exchange='retry',
                    routing_key=str(delay),
                    body=json.dumps(task),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )

                # Acknowledge original message
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                # Max retries exceeded: move to failed queue
                print(f"  MAX RETRIES EXCEEDED: Moving to failed queue")

                ch.basic_publish(
                    exchange='retry',
                    routing_key='failed',
                    body=json.dumps(task),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )

                # Acknowledge original message
                ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue='tasks',
        on_message_callback=callback,
        auto_ack=False
    )

    print("Consumer with retry logic started. Press CTRL+C to exit.")
    print("\nRetry Configuration:")
    print("  Attempt 1: Immediate")
    print("  Attempt 2: After 1s")
    print("  Attempt 3: After 5s")
    print("  Attempt 4: After 15s")
    print("  Failed: After 60s (moved to failed queue)\n")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nStopping consumer...")
        channel.stop_consuming()
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(
        description='Dead Letter Exchange with Retry Logic'
    )
    parser.add_argument(
        '--url',
        default='amqp://localhost',
        help='AMQP URL (default: amqp://localhost)'
    )
    parser.add_argument(
        '--publish',
        metavar='TASK',
        help='Publish a task instead of consuming'
    )

    args = parser.parse_args()

    if args.publish:
        publish_task(args.publish, args.url)
    else:
        consume_with_retry(args.url)


if __name__ == '__main__':
    main()
