#!/usr/bin/env python3
"""
AMQP/RabbitMQ Benchmark Tool

Benchmarks publisher/consumer throughput, tests different exchange types,
measures latency, tests durability impact, and concurrent connections.

Usage:
    ./benchmark_amqp.py --url amqp://localhost --mode publish --messages 10000
    ./benchmark_amqp.py --url amqp://localhost --mode consume --duration 60
    ./benchmark_amqp.py --url amqp://localhost --mode roundtrip --messages 1000
    ./benchmark_amqp.py --url amqp://localhost --mode throughput --publishers 5 --consumers 10
    ./benchmark_amqp.py --url amqp://localhost --mode exchange-types --json
    ./benchmark_amqp.py --help
"""

import argparse
import json
import sys
import logging
import time
import threading
import statistics
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pika
from urllib.parse import urlparse


@dataclass
class BenchmarkResult:
    """Benchmark result for a single run."""
    mode: str
    duration: float
    messages_sent: int
    messages_received: int
    bytes_sent: int
    bytes_received: int
    throughput_sent: float  # messages/second
    throughput_received: float  # messages/second
    bandwidth_sent: float  # MB/s
    bandwidth_received: float  # MB/s
    latency_min: Optional[float] = None  # milliseconds
    latency_max: Optional[float] = None
    latency_mean: Optional[float] = None
    latency_median: Optional[float] = None
    latency_p95: Optional[float] = None
    latency_p99: Optional[float] = None
    errors: int = 0
    configuration: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""
    broker_url: str
    timestamp: float
    results: List[BenchmarkResult]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'broker_url': self.broker_url,
            'timestamp': self.timestamp,
            'results': [r.to_dict() for r in self.results],
            'summary': self.summary
        }


class AMQPBenchmark:
    """AMQP benchmark tool."""

    def __init__(
        self,
        url: str,
        queue: str = 'benchmark',
        exchange: str = '',
        routing_key: str = '',
        durable: bool = False,
        persistent: bool = False
    ):
        """
        Initialize benchmark.

        Args:
            url: AMQP URL
            queue: Queue name
            exchange: Exchange name (empty for default)
            routing_key: Routing key (queue name if using default exchange)
            durable: Queue durability
            persistent: Message persistence
        """
        self.url = url
        self.queue = queue
        self.exchange = exchange
        self.routing_key = routing_key or queue
        self.durable = durable
        self.persistent = persistent
        self.logger = logging.getLogger(__name__)

    def get_connection(self) -> pika.BlockingConnection:
        """Create connection."""
        params = pika.URLParameters(self.url)
        return pika.BlockingConnection(params)

    def setup_queue(self) -> None:
        """Setup queue."""
        connection = self.get_connection()
        try:
            channel = connection.channel()
            channel.queue_declare(
                queue=self.queue,
                durable=self.durable,
                auto_delete=not self.durable
            )
            if self.exchange:
                channel.exchange_declare(
                    exchange=self.exchange,
                    exchange_type='direct',
                    durable=self.durable
                )
                channel.queue_bind(
                    queue=self.queue,
                    exchange=self.exchange,
                    routing_key=self.routing_key
                )
        finally:
            connection.close()

    def cleanup_queue(self) -> None:
        """Cleanup queue."""
        try:
            connection = self.get_connection()
            try:
                channel = connection.channel()
                channel.queue_delete(queue=self.queue)
                if self.exchange:
                    channel.exchange_delete(exchange=self.exchange)
            finally:
                connection.close()
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")

    def benchmark_publish(
        self,
        message_count: int,
        message_size: int = 1024,
        batch_size: int = 1
    ) -> BenchmarkResult:
        """
        Benchmark publishing.

        Args:
            message_count: Number of messages to publish
            message_size: Message size in bytes
            batch_size: Messages per batch

        Returns:
            Benchmark result
        """
        self.logger.info(f"Publishing {message_count} messages of {message_size} bytes...")

        connection = self.get_connection()
        try:
            channel = connection.channel()

            message = b'x' * message_size
            properties = pika.BasicProperties(
                delivery_mode=2 if self.persistent else 1
            )

            start_time = time.time()
            errors = 0

            for i in range(message_count):
                try:
                    channel.basic_publish(
                        exchange=self.exchange,
                        routing_key=self.routing_key,
                        body=message,
                        properties=properties
                    )
                except Exception as e:
                    self.logger.error(f"Publish error: {e}")
                    errors += 1

                if (i + 1) % 1000 == 0:
                    self.logger.info(f"Published {i+1}/{message_count} messages")

            end_time = time.time()
            duration = end_time - start_time

            bytes_sent = message_count * message_size
            throughput = message_count / duration if duration > 0 else 0
            bandwidth = (bytes_sent / duration / 1024 / 1024) if duration > 0 else 0

            return BenchmarkResult(
                mode='publish',
                duration=duration,
                messages_sent=message_count,
                messages_received=0,
                bytes_sent=bytes_sent,
                bytes_received=0,
                throughput_sent=throughput,
                throughput_received=0,
                bandwidth_sent=bandwidth,
                bandwidth_received=0,
                errors=errors,
                configuration={
                    'message_size': message_size,
                    'batch_size': batch_size,
                    'durable': self.durable,
                    'persistent': self.persistent
                }
            )
        finally:
            connection.close()

    def benchmark_consume(
        self,
        duration: int = 60,
        prefetch_count: int = 1
    ) -> BenchmarkResult:
        """
        Benchmark consuming.

        Args:
            duration: Duration in seconds
            prefetch_count: Prefetch count

        Returns:
            Benchmark result
        """
        self.logger.info(f"Consuming for {duration} seconds...")

        connection = self.get_connection()
        try:
            channel = connection.channel()
            channel.basic_qos(prefetch_count=prefetch_count)

            messages_received = 0
            bytes_received = 0
            errors = 0
            start_time = time.time()
            end_time = start_time + duration

            def callback(ch, method, properties, body):
                nonlocal messages_received, bytes_received
                messages_received += 1
                bytes_received += len(body)
                ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_consume(
                queue=self.queue,
                on_message_callback=callback,
                auto_ack=False
            )

            # Consume with timeout
            while time.time() < end_time:
                try:
                    connection.process_data_events(time_limit=1)
                except Exception as e:
                    self.logger.error(f"Consume error: {e}")
                    errors += 1

            actual_duration = time.time() - start_time
            throughput = messages_received / actual_duration if actual_duration > 0 else 0
            bandwidth = (bytes_received / actual_duration / 1024 / 1024) if actual_duration > 0 else 0

            return BenchmarkResult(
                mode='consume',
                duration=actual_duration,
                messages_sent=0,
                messages_received=messages_received,
                bytes_sent=0,
                bytes_received=bytes_received,
                throughput_sent=0,
                throughput_received=throughput,
                bandwidth_sent=0,
                bandwidth_received=bandwidth,
                errors=errors,
                configuration={
                    'prefetch_count': prefetch_count,
                    'durable': self.durable
                }
            )
        finally:
            connection.close()

    def benchmark_roundtrip(
        self,
        message_count: int,
        message_size: int = 1024
    ) -> BenchmarkResult:
        """
        Benchmark round-trip latency.

        Args:
            message_count: Number of messages
            message_size: Message size in bytes

        Returns:
            Benchmark result with latency stats
        """
        self.logger.info(f"Measuring round-trip latency for {message_count} messages...")

        connection = self.get_connection()
        try:
            channel = connection.channel()

            # Create temporary callback queue
            result = channel.queue_declare(queue='', exclusive=True)
            callback_queue = result.method.queue

            message = b'x' * message_size
            latencies = []
            errors = 0

            def on_response(ch, method, properties, body):
                pass  # Handled synchronously

            channel.basic_consume(
                queue=callback_queue,
                on_message_callback=on_response,
                auto_ack=True
            )

            start_time = time.time()

            for i in range(message_count):
                try:
                    msg_start = time.time()

                    # Publish
                    channel.basic_publish(
                        exchange=self.exchange,
                        routing_key=self.routing_key,
                        body=message,
                        properties=pika.BasicProperties(
                            reply_to=callback_queue,
                            correlation_id=str(i)
                        )
                    )

                    # Wait for response (simulated by get)
                    method_frame, header_frame, body = channel.basic_get(
                        queue=callback_queue,
                        auto_ack=True
                    )

                    if method_frame:
                        msg_end = time.time()
                        latency_ms = (msg_end - msg_start) * 1000
                        latencies.append(latency_ms)
                    else:
                        errors += 1

                except Exception as e:
                    self.logger.error(f"Roundtrip error: {e}")
                    errors += 1

                if (i + 1) % 100 == 0:
                    self.logger.info(f"Completed {i+1}/{message_count} roundtrips")

            end_time = time.time()
            duration = end_time - start_time

            # Calculate latency stats
            if latencies:
                latencies.sort()
                latency_min = min(latencies)
                latency_max = max(latencies)
                latency_mean = statistics.mean(latencies)
                latency_median = statistics.median(latencies)
                latency_p95 = latencies[int(len(latencies) * 0.95)]
                latency_p99 = latencies[int(len(latencies) * 0.99)]
            else:
                latency_min = latency_max = latency_mean = latency_median = 0
                latency_p95 = latency_p99 = 0

            bytes_sent = message_count * message_size
            throughput = message_count / duration if duration > 0 else 0

            return BenchmarkResult(
                mode='roundtrip',
                duration=duration,
                messages_sent=message_count,
                messages_received=len(latencies),
                bytes_sent=bytes_sent,
                bytes_received=bytes_sent,
                throughput_sent=throughput,
                throughput_received=throughput,
                bandwidth_sent=0,
                bandwidth_received=0,
                latency_min=latency_min,
                latency_max=latency_max,
                latency_mean=latency_mean,
                latency_median=latency_median,
                latency_p95=latency_p95,
                latency_p99=latency_p99,
                errors=errors,
                configuration={
                    'message_size': message_size,
                    'durable': self.durable,
                    'persistent': self.persistent
                }
            )
        finally:
            connection.close()

    def benchmark_throughput(
        self,
        duration: int,
        publishers: int,
        consumers: int,
        message_size: int = 1024
    ) -> BenchmarkResult:
        """
        Benchmark concurrent throughput.

        Args:
            duration: Duration in seconds
            publishers: Number of publisher threads
            consumers: Number of consumer threads
            message_size: Message size in bytes

        Returns:
            Benchmark result
        """
        self.logger.info(
            f"Benchmarking throughput with {publishers} publishers "
            f"and {consumers} consumers for {duration}s..."
        )

        # Shared counters
        stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'errors': 0,
            'lock': threading.Lock()
        }

        def publisher_worker():
            try:
                connection = self.get_connection()
                channel = connection.channel()

                message = b'x' * message_size
                properties = pika.BasicProperties(
                    delivery_mode=2 if self.persistent else 1
                )

                end_time = time.time() + duration

                while time.time() < end_time:
                    try:
                        channel.basic_publish(
                            exchange=self.exchange,
                            routing_key=self.routing_key,
                            body=message,
                            properties=properties
                        )
                        with stats['lock']:
                            stats['messages_sent'] += 1
                            stats['bytes_sent'] += len(message)
                    except Exception as e:
                        with stats['lock']:
                            stats['errors'] += 1

                connection.close()
            except Exception as e:
                self.logger.error(f"Publisher worker error: {e}")

        def consumer_worker():
            try:
                connection = self.get_connection()
                channel = connection.channel()
                channel.basic_qos(prefetch_count=10)

                end_time = time.time() + duration

                def callback(ch, method, properties, body):
                    with stats['lock']:
                        stats['messages_received'] += 1
                        stats['bytes_received'] += len(body)
                    ch.basic_ack(delivery_tag=method.delivery_tag)

                channel.basic_consume(
                    queue=self.queue,
                    on_message_callback=callback,
                    auto_ack=False
                )

                while time.time() < end_time:
                    try:
                        connection.process_data_events(time_limit=1)
                    except Exception as e:
                        with stats['lock']:
                            stats['errors'] += 1

                connection.close()
            except Exception as e:
                self.logger.error(f"Consumer worker error: {e}")

        # Start workers
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=publishers + consumers) as executor:
            futures = []

            # Start publishers
            for _ in range(publishers):
                futures.append(executor.submit(publisher_worker))

            # Start consumers
            for _ in range(consumers):
                futures.append(executor.submit(consumer_worker))

            # Wait for completion
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Worker failed: {e}")

        actual_duration = time.time() - start_time

        # Calculate throughput
        throughput_sent = stats['messages_sent'] / actual_duration if actual_duration > 0 else 0
        throughput_received = stats['messages_received'] / actual_duration if actual_duration > 0 else 0
        bandwidth_sent = (stats['bytes_sent'] / actual_duration / 1024 / 1024) if actual_duration > 0 else 0
        bandwidth_received = (stats['bytes_received'] / actual_duration / 1024 / 1024) if actual_duration > 0 else 0

        return BenchmarkResult(
            mode='throughput',
            duration=actual_duration,
            messages_sent=stats['messages_sent'],
            messages_received=stats['messages_received'],
            bytes_sent=stats['bytes_sent'],
            bytes_received=stats['bytes_received'],
            throughput_sent=throughput_sent,
            throughput_received=throughput_received,
            bandwidth_sent=bandwidth_sent,
            bandwidth_received=bandwidth_received,
            errors=stats['errors'],
            configuration={
                'publishers': publishers,
                'consumers': consumers,
                'message_size': message_size,
                'durable': self.durable,
                'persistent': self.persistent
            }
        )

    def benchmark_exchange_types(
        self,
        message_count: int = 1000,
        message_size: int = 1024
    ) -> List[BenchmarkResult]:
        """
        Benchmark different exchange types.

        Args:
            message_count: Number of messages per exchange type
            message_size: Message size in bytes

        Returns:
            List of benchmark results
        """
        results = []

        for ex_type in ['direct', 'fanout', 'topic']:
            self.logger.info(f"Benchmarking {ex_type} exchange...")

            # Create exchange
            exchange_name = f'bench_{ex_type}'
            queue_name = f'bench_{ex_type}_queue'

            connection = self.get_connection()
            try:
                channel = connection.channel()
                channel.exchange_declare(
                    exchange=exchange_name,
                    exchange_type=ex_type,
                    durable=False,
                    auto_delete=True
                )
                channel.queue_declare(
                    queue=queue_name,
                    durable=False,
                    auto_delete=True
                )

                routing_key = 'test.key' if ex_type == 'topic' else 'test'
                channel.queue_bind(
                    queue=queue_name,
                    exchange=exchange_name,
                    routing_key=routing_key
                )
            finally:
                connection.close()

            # Benchmark
            original_exchange = self.exchange
            original_queue = self.queue
            original_routing_key = self.routing_key

            self.exchange = exchange_name
            self.queue = queue_name
            self.routing_key = routing_key

            result = self.benchmark_publish(message_count, message_size)
            result.configuration['exchange_type'] = ex_type

            self.exchange = original_exchange
            self.queue = original_queue
            self.routing_key = original_routing_key

            results.append(result)

            # Cleanup
            connection = self.get_connection()
            try:
                channel = connection.channel()
                channel.queue_delete(queue=queue_name)
                channel.exchange_delete(exchange=exchange_name)
            finally:
                connection.close()

        return results

    def benchmark_durability_impact(
        self,
        message_count: int = 1000,
        message_size: int = 1024
    ) -> List[BenchmarkResult]:
        """
        Benchmark durability impact.

        Args:
            message_count: Number of messages
            message_size: Message size in bytes

        Returns:
            List of benchmark results
        """
        results = []

        configs = [
            {'durable': False, 'persistent': False, 'name': 'non_durable_non_persistent'},
            {'durable': True, 'persistent': False, 'name': 'durable_non_persistent'},
            {'durable': True, 'persistent': True, 'name': 'durable_persistent'},
        ]

        for config in configs:
            self.logger.info(f"Benchmarking {config['name']}...")

            # Update configuration
            original_durable = self.durable
            original_persistent = self.persistent

            self.durable = config['durable']
            self.persistent = config['persistent']

            # Setup queue
            self.setup_queue()

            # Benchmark
            result = self.benchmark_publish(message_count, message_size)
            result.configuration['durability_mode'] = config['name']

            results.append(result)

            # Cleanup
            self.cleanup_queue()

            # Restore
            self.durable = original_durable
            self.persistent = original_persistent

        return results


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Benchmark AMQP/RabbitMQ',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Benchmark publishing
  %(prog)s --url amqp://localhost --mode publish --messages 10000

  # Benchmark consuming
  %(prog)s --url amqp://localhost --mode consume --duration 60

  # Measure latency
  %(prog)s --url amqp://localhost --mode roundtrip --messages 1000

  # Concurrent throughput
  %(prog)s --url amqp://localhost --mode throughput --publishers 5 --consumers 10 --duration 60

  # Test exchange types
  %(prog)s --url amqp://localhost --mode exchange-types --messages 5000

  # Test durability impact
  %(prog)s --url amqp://localhost --mode durability --messages 5000

  # JSON output
  %(prog)s --url amqp://localhost --mode publish --messages 10000 --json
        """
    )

    parser.add_argument(
        '--url',
        required=True,
        help='AMQP broker URL'
    )
    parser.add_argument(
        '--mode',
        choices=['publish', 'consume', 'roundtrip', 'throughput', 'exchange-types', 'durability'],
        default='publish',
        help='Benchmark mode'
    )
    parser.add_argument(
        '--queue',
        default='benchmark',
        help='Queue name (default: benchmark)'
    )
    parser.add_argument(
        '--exchange',
        default='',
        help='Exchange name (default: default exchange)'
    )
    parser.add_argument(
        '--routing-key',
        default='',
        help='Routing key (default: queue name)'
    )
    parser.add_argument(
        '--messages',
        type=int,
        default=10000,
        help='Number of messages (default: 10000)'
    )
    parser.add_argument(
        '--message-size',
        type=int,
        default=1024,
        help='Message size in bytes (default: 1024)'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Duration in seconds (default: 60)'
    )
    parser.add_argument(
        '--publishers',
        type=int,
        default=1,
        help='Number of publishers (default: 1)'
    )
    parser.add_argument(
        '--consumers',
        type=int,
        default=1,
        help='Number of consumers (default: 1)'
    )
    parser.add_argument(
        '--prefetch-count',
        type=int,
        default=1,
        help='Consumer prefetch count (default: 1)'
    )
    parser.add_argument(
        '--durable',
        action='store_true',
        help='Use durable queues'
    )
    parser.add_argument(
        '--persistent',
        action='store_true',
        help='Use persistent messages'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output JSON format'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Create benchmark
    benchmark = AMQPBenchmark(
        url=args.url,
        queue=args.queue,
        exchange=args.exchange,
        routing_key=args.routing_key,
        durable=args.durable,
        persistent=args.persistent
    )

    # Setup queue
    if args.mode in ['publish', 'consume', 'roundtrip', 'throughput']:
        benchmark.setup_queue()

    # Run benchmark
    results = []

    try:
        if args.mode == 'publish':
            result = benchmark.benchmark_publish(args.messages, args.message_size)
            results.append(result)

        elif args.mode == 'consume':
            result = benchmark.benchmark_consume(args.duration, args.prefetch_count)
            results.append(result)

        elif args.mode == 'roundtrip':
            result = benchmark.benchmark_roundtrip(args.messages, args.message_size)
            results.append(result)

        elif args.mode == 'throughput':
            result = benchmark.benchmark_throughput(
                args.duration,
                args.publishers,
                args.consumers,
                args.message_size
            )
            results.append(result)

        elif args.mode == 'exchange-types':
            results = benchmark.benchmark_exchange_types(args.messages, args.message_size)

        elif args.mode == 'durability':
            results = benchmark.benchmark_durability_impact(args.messages, args.message_size)

    finally:
        # Cleanup
        if args.mode in ['publish', 'consume', 'roundtrip', 'throughput']:
            benchmark.cleanup_queue()

    # Create report
    report = BenchmarkReport(
        broker_url=args.url,
        timestamp=time.time(),
        results=results,
        summary={
            'mode': args.mode,
            'total_duration': sum(r.duration for r in results),
            'total_messages_sent': sum(r.messages_sent for r in results),
            'total_messages_received': sum(r.messages_received for r in results),
            'avg_throughput_sent': statistics.mean(r.throughput_sent for r in results if r.throughput_sent > 0) if results else 0,
            'avg_throughput_received': statistics.mean(r.throughput_received for r in results if r.throughput_received > 0) if results else 0,
        }
    )

    # Output results
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"\n{'='*80}")
        print(f"AMQP Benchmark Results")
        print(f"{'='*80}")
        print(f"Broker: {report.broker_url}")
        print(f"Mode: {args.mode}")

        for i, result in enumerate(results, 1):
            if len(results) > 1:
                print(f"\n{'='*80}")
                print(f"Result {i}")
                print(f"{'='*80}")

            print(f"\nDuration: {result.duration:.2f}s")
            print(f"Messages Sent: {result.messages_sent:,}")
            print(f"Messages Received: {result.messages_received:,}")
            print(f"Throughput (sent): {result.throughput_sent:.2f} msg/s")
            print(f"Throughput (received): {result.throughput_received:.2f} msg/s")
            print(f"Bandwidth (sent): {result.bandwidth_sent:.2f} MB/s")
            print(f"Bandwidth (received): {result.bandwidth_received:.2f} MB/s")

            if result.latency_mean is not None:
                print(f"\nLatency Statistics:")
                print(f"  Min: {result.latency_min:.2f}ms")
                print(f"  Mean: {result.latency_mean:.2f}ms")
                print(f"  Median: {result.latency_median:.2f}ms")
                print(f"  P95: {result.latency_p95:.2f}ms")
                print(f"  P99: {result.latency_p99:.2f}ms")
                print(f"  Max: {result.latency_max:.2f}ms")

            if result.errors > 0:
                print(f"\nErrors: {result.errors}")

            if result.configuration:
                print(f"\nConfiguration:")
                for key, value in result.configuration.items():
                    print(f"  {key}: {value}")

        print(f"\n{'='*80}")
        print(f"Summary")
        print(f"{'='*80}")
        print(f"Total Duration: {report.summary['total_duration']:.2f}s")
        print(f"Total Messages Sent: {report.summary['total_messages_sent']:,}")
        print(f"Total Messages Received: {report.summary['total_messages_received']:,}")
        print(f"Average Throughput (sent): {report.summary['avg_throughput_sent']:.2f} msg/s")
        print(f"Average Throughput (received): {report.summary['avg_throughput_received']:.2f} msg/s")

    return 0


if __name__ == '__main__':
    sys.exit(main())
