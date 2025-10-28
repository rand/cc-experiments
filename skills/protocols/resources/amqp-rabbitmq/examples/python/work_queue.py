"""
Work Queue Pattern - Python Implementation

Distributes tasks among multiple workers using a durable queue with manual acknowledgments.

Usage:
    # Start multiple workers
    python work_queue.py consume

    # Publish tasks
    python work_queue.py publish "Task 1"
    python work_queue.py publish "Task 2" --priority 9
"""

import argparse
import pika
import time
import sys
import random


def get_connection(url: str = 'amqp://localhost') -> pika.BlockingConnection:
    """Create connection to RabbitMQ."""
    parameters = pika.URLParameters(url)
    return pika.BlockingConnection(parameters)


def setup_queue(channel: pika.channel.Channel) -> None:
    """Declare durable queue with priority support."""
    channel.queue_declare(
        queue='tasks',
        durable=True,
        arguments={
            'x-max-priority': 10  # Priority range 0-10
        }
    )


def publish_task(task_data: str, priority: int = 5, url: str = 'amqp://localhost') -> None:
    """
    Publish task to work queue.

    Args:
        task_data: Task data
        priority: Task priority (0-10, higher = more important)
        url: AMQP URL
    """
    connection = get_connection(url)
    try:
        channel = connection.channel()
        setup_queue(channel)

        # Publish with persistence and priority
        channel.basic_publish(
            exchange='',
            routing_key='tasks',
            body=task_data,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent message
                priority=priority
            )
        )
        print(f"Published task (priority {priority}): {task_data}")
    finally:
        connection.close()


def consume_tasks(url: str = 'amqp://localhost') -> None:
    """
    Consume and process tasks from work queue.

    Args:
        url: AMQP URL
    """
    connection = get_connection(url)
    channel = connection.channel()
    setup_queue(channel)

    # Fair dispatch: only one unacked message at a time
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        """Process task with simulated work and manual ack."""
        task = body.decode('utf-8')
        priority = properties.priority or 0

        print(f"Processing task (priority {priority}): {task}")

        # Simulate work (random duration 1-5 seconds)
        work_time = random.uniform(1, 5)
        time.sleep(work_time)

        print(f"Completed task: {task} (took {work_time:.2f}s)")

        # Acknowledge after successful processing
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue='tasks',
        on_message_callback=callback,
        auto_ack=False  # Manual acknowledgment
    )

    print("Worker waiting for tasks. Press CTRL+C to exit.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nStopping worker...")
        channel.stop_consuming()
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description='Work Queue Example')
    parser.add_argument(
        'action',
        choices=['publish', 'consume'],
        help='Action to perform'
    )
    parser.add_argument(
        'task',
        nargs='?',
        default='Default task',
        help='Task data (for publish)'
    )
    parser.add_argument(
        '--priority',
        type=int,
        default=5,
        choices=range(0, 11),
        help='Task priority 0-10 (default: 5)'
    )
    parser.add_argument(
        '--url',
        default='amqp://localhost',
        help='AMQP URL (default: amqp://localhost)'
    )

    args = parser.parse_args()

    if args.action == 'publish':
        publish_task(args.task, args.priority, args.url)
    else:
        consume_tasks(args.url)


if __name__ == '__main__':
    main()
