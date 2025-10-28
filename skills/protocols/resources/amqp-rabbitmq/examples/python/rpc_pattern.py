"""
RPC Pattern - Python Implementation

Remote procedure call pattern with correlation IDs and reply queues.

Usage:
    # Start RPC server
    python rpc_pattern.py server

    # Make RPC calls (client)
    python rpc_pattern.py client 10
    python rpc_pattern.py client 20
"""

import argparse
import pika
import uuid
import json
import time


def get_connection(url: str = 'amqp://localhost') -> pika.BlockingConnection:
    """Create connection to RabbitMQ."""
    parameters = pika.URLParameters(url)
    return pika.BlockingConnection(parameters)


class FibonacciRPCClient:
    """RPC client for Fibonacci calculation."""

    def __init__(self, url: str = 'amqp://localhost'):
        """Initialize RPC client."""
        self.connection = get_connection(url)
        self.channel = self.connection.channel()

        # Declare callback queue for responses
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True
        )

        self.response = None
        self.corr_id = None

    def on_response(self, ch, method, props, body):
        """Handle RPC response."""
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n: int) -> int:
        """
        Make RPC call to calculate Fibonacci number.

        Args:
            n: Fibonacci sequence index

        Returns:
            Fibonacci number
        """
        self.response = None
        self.corr_id = str(uuid.uuid4())

        request = json.dumps({'n': n})

        print(f"Calling fibonacci({n})...")
        start_time = time.time()

        self.channel.basic_publish(
            exchange='',
            routing_key='rpc_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
                content_type='application/json'
            ),
            body=request
        )

        # Wait for response
        while self.response is None:
            self.connection.process_data_events()

        elapsed = time.time() - start_time
        result = json.loads(self.response)

        print(f"Result: fibonacci({n}) = {result['result']} (took {elapsed:.3f}s)")

        return result['result']

    def close(self):
        """Close connection."""
        self.connection.close()


def fibonacci(n: int) -> int:
    """Calculate Fibonacci number (recursive for demonstration)."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def run_rpc_server(url: str = 'amqp://localhost'):
    """
    Run RPC server to handle Fibonacci calculations.

    Args:
        url: AMQP URL
    """
    connection = get_connection(url)
    channel = connection.channel()

    # Declare RPC queue
    channel.queue_declare(queue='rpc_queue', durable=True)

    # Fair dispatch
    channel.basic_qos(prefetch_count=1)

    def on_request(ch, method, props, body):
        """Handle RPC request."""
        request = json.loads(body)
        n = request['n']

        print(f"Received request: fibonacci({n})")
        start_time = time.time()

        # Calculate result
        result = fibonacci(n)

        elapsed = time.time() - start_time
        print(f"Computed: fibonacci({n}) = {result} (took {elapsed:.3f}s)")

        # Send response
        response = json.dumps({'result': result})

        ch.basic_publish(
            exchange='',
            routing_key=props.reply_to,
            properties=pika.BasicProperties(
                correlation_id=props.correlation_id,
                content_type='application/json'
            ),
            body=response
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue='rpc_queue',
        on_message_callback=on_request
    )

    print("RPC server waiting for requests. Press CTRL+C to exit.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nStopping server...")
        channel.stop_consuming()
    finally:
        connection.close()


def run_rpc_client(n: int, url: str = 'amqp://localhost'):
    """
    Run RPC client.

    Args:
        n: Fibonacci index
        url: AMQP URL
    """
    client = FibonacciRPCClient(url)
    try:
        client.call(n)
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description='RPC Pattern Example')
    parser.add_argument(
        'mode',
        choices=['server', 'client'],
        help='Run as server or client'
    )
    parser.add_argument(
        'n',
        type=int,
        nargs='?',
        default=10,
        help='Fibonacci index (client only, default: 10)'
    )
    parser.add_argument(
        '--url',
        default='amqp://localhost',
        help='AMQP URL (default: amqp://localhost)'
    )

    args = parser.parse_args()

    if args.mode == 'server':
        run_rpc_server(args.url)
    else:
        run_rpc_client(args.n, args.url)


if __name__ == '__main__':
    main()
