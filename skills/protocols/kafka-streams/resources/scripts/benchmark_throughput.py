#!/usr/bin/env python3
"""
Kafka Producer/Consumer Throughput Benchmark

Benchmarks Kafka producer and consumer throughput, measuring messages/sec,
MB/sec, latency percentiles, and end-to-end latency.

Usage:
    ./benchmark_throughput.py --bootstrap-servers localhost:9092 --mode producer --messages 100000
    ./benchmark_throughput.py --bootstrap-servers localhost:9092 --mode consumer --topic benchmark
    ./benchmark_throughput.py --bootstrap-servers localhost:9092 --mode both --messages 50000
    ./benchmark_throughput.py --bootstrap-servers localhost:9092 --mode producer --json
    ./benchmark_throughput.py --help

Requirements:
    pip install kafka-python
"""

import argparse
import json
import sys
import time
import threading
import statistics
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError


@dataclass
class LatencyStats:
    """Latency statistics"""
    min_ms: float
    max_ms: float
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


@dataclass
class BenchmarkResult:
    """Benchmark results for producer or consumer"""
    mode: str  # producer, consumer, both
    duration_sec: float
    messages_sent: int
    messages_received: int
    bytes_sent: int
    bytes_received: int
    throughput_msg_sec: float
    throughput_mb_sec: float
    producer_latency: Optional[LatencyStats]
    consumer_latency: Optional[LatencyStats]
    end_to_end_latency: Optional[LatencyStats]
    errors: int


class KafkaBenchmark:
    """Kafka producer/consumer throughput benchmark"""

    DEFAULT_MESSAGE_SIZE = 1024  # 1 KB
    DEFAULT_TOPIC = 'benchmark-topic'

    def __init__(self, bootstrap_servers: str):
        """Initialize benchmark with Kafka connection"""
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.consumer = None

        # Metrics
        self.messages_sent = 0
        self.messages_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.producer_latencies = []
        self.consumer_latencies = []
        self.end_to_end_latencies = []
        self.errors = 0

        # Control
        self.stop_flag = False

    def create_producer(self, **config) -> KafkaProducer:
        """Create Kafka producer with optimized settings"""
        default_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'acks': 1,  # Leader ack only (faster)
            'compression_type': 'lz4',
            'batch_size': 16384,
            'linger_ms': 10,
            'buffer_memory': 33554432,
        }
        default_config.update(config)

        return KafkaProducer(**default_config)

    def create_consumer(self, topic: str, **config) -> KafkaConsumer:
        """Create Kafka consumer with optimized settings"""
        default_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'group_id': f'benchmark-group-{int(time.time())}',
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': True,
            'fetch_min_bytes': 1024,
            'fetch_max_wait_ms': 500,
        }
        default_config.update(config)

        consumer = KafkaConsumer(topic, **default_config)
        return consumer

    def generate_message(self, size: int, message_id: int) -> bytes:
        """Generate test message of specific size"""
        # Include timestamp for latency measurement
        timestamp = time.time()
        header = f"{message_id}:{timestamp}:".encode('utf-8')

        # Pad to desired size
        padding_size = size - len(header)
        if padding_size < 0:
            padding_size = 0

        padding = b'x' * padding_size
        return header + padding

    def parse_message(self, message: bytes) -> Optional[Dict]:
        """Parse message to extract metadata"""
        try:
            parts = message.split(b':', 2)
            if len(parts) >= 2:
                message_id = int(parts[0])
                timestamp = float(parts[1])
                return {'message_id': message_id, 'timestamp': timestamp}
        except Exception:
            pass
        return None

    def benchmark_producer(
        self,
        topic: str,
        num_messages: int,
        message_size: int
    ) -> None:
        """Benchmark producer throughput"""
        print(f"Starting producer benchmark: {num_messages} messages, {message_size} bytes each")

        self.producer = self.create_producer()

        start_time = time.time()

        for i in range(num_messages):
            if self.stop_flag:
                break

            message = self.generate_message(message_size, i)

            try:
                send_start = time.time()

                # Send message (async)
                future = self.producer.send(topic, value=message)

                # Wait for ack (synchronous for latency measurement)
                record_metadata = future.get(timeout=10)

                send_end = time.time()
                latency_ms = (send_end - send_start) * 1000

                self.producer_latencies.append(latency_ms)
                self.messages_sent += 1
                self.bytes_sent += len(message)

                # Progress
                if (i + 1) % 10000 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    print(f"  Sent {i + 1}/{num_messages} messages ({rate:.0f} msg/sec)")

            except Exception as e:
                self.errors += 1
                if self.errors <= 10:  # Print first 10 errors
                    print(f"  Error sending message {i}: {e}", file=sys.stderr)

        # Flush remaining messages
        self.producer.flush()

        end_time = time.time()
        duration = end_time - start_time

        print(f"Producer benchmark complete: {duration:.2f} seconds")

    def benchmark_consumer(
        self,
        topic: str,
        num_messages: Optional[int] = None,
        timeout_sec: int = 60
    ) -> None:
        """Benchmark consumer throughput"""
        print(f"Starting consumer benchmark: consuming from '{topic}'")

        self.consumer = self.create_consumer(topic)

        start_time = time.time()
        last_message_time = start_time

        while True:
            if self.stop_flag:
                break

            # Check timeout
            if time.time() - last_message_time > timeout_sec:
                print("Consumer timeout reached, stopping")
                break

            # Check message count
            if num_messages and self.messages_received >= num_messages:
                print(f"Consumed target {num_messages} messages")
                break

            try:
                # Poll messages
                messages = self.consumer.poll(timeout_ms=1000)

                if not messages:
                    continue

                receive_time = time.time()

                for topic_partition, records in messages.items():
                    for record in records:
                        # Parse message
                        metadata = self.parse_message(record.value)

                        if metadata:
                            # Calculate end-to-end latency
                            send_timestamp = metadata['timestamp']
                            e2e_latency_ms = (receive_time - send_timestamp) * 1000
                            self.end_to_end_latencies.append(e2e_latency_ms)

                        self.messages_received += 1
                        self.bytes_received += len(record.value)
                        last_message_time = receive_time

                        # Progress
                        if self.messages_received % 10000 == 0:
                            elapsed = time.time() - start_time
                            rate = self.messages_received / elapsed
                            print(f"  Received {self.messages_received} messages ({rate:.0f} msg/sec)")

            except Exception as e:
                self.errors += 1
                if self.errors <= 10:
                    print(f"  Error consuming message: {e}", file=sys.stderr)

        end_time = time.time()
        duration = end_time - start_time

        print(f"Consumer benchmark complete: {duration:.2f} seconds")

    def run_producer_benchmark(
        self,
        topic: str,
        num_messages: int,
        message_size: int
    ) -> BenchmarkResult:
        """Run producer-only benchmark"""
        start_time = time.time()

        self.benchmark_producer(topic, num_messages, message_size)

        end_time = time.time()
        duration = end_time - start_time

        # Calculate stats
        producer_latency = self._calculate_latency_stats(self.producer_latencies)

        throughput_msg_sec = self.messages_sent / duration if duration > 0 else 0
        throughput_mb_sec = (self.bytes_sent / duration) / (1024 * 1024) if duration > 0 else 0

        return BenchmarkResult(
            mode='producer',
            duration_sec=duration,
            messages_sent=self.messages_sent,
            messages_received=0,
            bytes_sent=self.bytes_sent,
            bytes_received=0,
            throughput_msg_sec=throughput_msg_sec,
            throughput_mb_sec=throughput_mb_sec,
            producer_latency=producer_latency,
            consumer_latency=None,
            end_to_end_latency=None,
            errors=self.errors
        )

    def run_consumer_benchmark(
        self,
        topic: str,
        num_messages: Optional[int] = None,
        timeout_sec: int = 60
    ) -> BenchmarkResult:
        """Run consumer-only benchmark"""
        start_time = time.time()

        self.benchmark_consumer(topic, num_messages, timeout_sec)

        end_time = time.time()
        duration = end_time - start_time

        # Calculate stats
        e2e_latency = self._calculate_latency_stats(self.end_to_end_latencies)

        throughput_msg_sec = self.messages_received / duration if duration > 0 else 0
        throughput_mb_sec = (self.bytes_received / duration) / (1024 * 1024) if duration > 0 else 0

        return BenchmarkResult(
            mode='consumer',
            duration_sec=duration,
            messages_sent=0,
            messages_received=self.messages_received,
            bytes_sent=0,
            bytes_received=self.bytes_received,
            throughput_msg_sec=throughput_msg_sec,
            throughput_mb_sec=throughput_mb_sec,
            producer_latency=None,
            consumer_latency=None,
            end_to_end_latency=e2e_latency,
            errors=self.errors
        )

    def run_end_to_end_benchmark(
        self,
        topic: str,
        num_messages: int,
        message_size: int
    ) -> BenchmarkResult:
        """Run end-to-end benchmark (producer + consumer)"""
        print("Starting end-to-end benchmark (producer + consumer)")

        # Start consumer in background thread
        consumer_thread = threading.Thread(
            target=self.benchmark_consumer,
            args=(topic, num_messages, 120)
        )
        consumer_thread.start()

        # Wait for consumer to be ready
        time.sleep(2)

        # Run producer
        start_time = time.time()
        self.benchmark_producer(topic, num_messages, message_size)

        # Wait for consumer to finish
        consumer_thread.join(timeout=60)

        end_time = time.time()
        duration = end_time - start_time

        # Calculate stats
        producer_latency = self._calculate_latency_stats(self.producer_latencies)
        e2e_latency = self._calculate_latency_stats(self.end_to_end_latencies)

        # Throughput (based on producer rate)
        throughput_msg_sec = self.messages_sent / duration if duration > 0 else 0
        throughput_mb_sec = (self.bytes_sent / duration) / (1024 * 1024) if duration > 0 else 0

        return BenchmarkResult(
            mode='both',
            duration_sec=duration,
            messages_sent=self.messages_sent,
            messages_received=self.messages_received,
            bytes_sent=self.bytes_sent,
            bytes_received=self.bytes_received,
            throughput_msg_sec=throughput_msg_sec,
            throughput_mb_sec=throughput_mb_sec,
            producer_latency=producer_latency,
            consumer_latency=None,
            end_to_end_latency=e2e_latency,
            errors=self.errors
        )

    def _calculate_latency_stats(self, latencies: List[float]) -> Optional[LatencyStats]:
        """Calculate latency statistics"""
        if not latencies:
            return None

        sorted_latencies = sorted(latencies)
        count = len(sorted_latencies)

        return LatencyStats(
            min_ms=sorted_latencies[0],
            max_ms=sorted_latencies[-1],
            avg_ms=statistics.mean(sorted_latencies),
            p50_ms=sorted_latencies[int(count * 0.5)],
            p95_ms=sorted_latencies[int(count * 0.95)],
            p99_ms=sorted_latencies[int(count * 0.99)]
        )

    def close(self):
        """Close connections"""
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()


def format_text_output(result: BenchmarkResult) -> str:
    """Format benchmark results as human-readable text"""
    lines = []
    lines.append("=" * 80)
    lines.append("Kafka Throughput Benchmark Results")
    lines.append("=" * 80)
    lines.append("")

    lines.append(f"Mode: {result.mode.upper()}")
    lines.append(f"Duration: {result.duration_sec:.2f} seconds")
    lines.append("")

    # Throughput
    lines.append("Throughput:")
    lines.append(f"  Messages/sec: {result.throughput_msg_sec:,.0f}")
    lines.append(f"  MB/sec:       {result.throughput_mb_sec:.2f}")
    lines.append("")

    # Messages
    if result.messages_sent > 0:
        lines.append(f"Messages Sent:     {result.messages_sent:,}")
        lines.append(f"Bytes Sent:        {result.bytes_sent:,} ({result.bytes_sent / (1024 * 1024):.2f} MB)")
        lines.append("")

    if result.messages_received > 0:
        lines.append(f"Messages Received: {result.messages_received:,}")
        lines.append(f"Bytes Received:    {result.bytes_received:,} ({result.bytes_received / (1024 * 1024):.2f} MB)")
        lines.append("")

    # Producer latency
    if result.producer_latency:
        lines.append("Producer Latency (per message):")
        lines.append(f"  Min:  {result.producer_latency.min_ms:.2f} ms")
        lines.append(f"  Avg:  {result.producer_latency.avg_ms:.2f} ms")
        lines.append(f"  P50:  {result.producer_latency.p50_ms:.2f} ms")
        lines.append(f"  P95:  {result.producer_latency.p95_ms:.2f} ms")
        lines.append(f"  P99:  {result.producer_latency.p99_ms:.2f} ms")
        lines.append(f"  Max:  {result.producer_latency.max_ms:.2f} ms")
        lines.append("")

    # End-to-end latency
    if result.end_to_end_latency:
        lines.append("End-to-End Latency (producer → consumer):")
        lines.append(f"  Min:  {result.end_to_end_latency.min_ms:.2f} ms")
        lines.append(f"  Avg:  {result.end_to_end_latency.avg_ms:.2f} ms")
        lines.append(f"  P50:  {result.end_to_end_latency.p50_ms:.2f} ms")
        lines.append(f"  P95:  {result.end_to_end_latency.p95_ms:.2f} ms")
        lines.append(f"  P99:  {result.end_to_end_latency.p99_ms:.2f} ms")
        lines.append(f"  Max:  {result.end_to_end_latency.max_ms:.2f} ms")
        lines.append("")

    # Errors
    if result.errors > 0:
        lines.append(f"Errors: {result.errors}")
        lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


def format_json_output(result: BenchmarkResult) -> str:
    """Format benchmark results as JSON"""
    output = {
        'mode': result.mode,
        'duration_sec': result.duration_sec,
        'throughput': {
            'messages_per_sec': result.throughput_msg_sec,
            'mb_per_sec': result.throughput_mb_sec
        },
        'messages': {
            'sent': result.messages_sent,
            'received': result.messages_received
        },
        'bytes': {
            'sent': result.bytes_sent,
            'received': result.bytes_received
        },
        'errors': result.errors
    }

    if result.producer_latency:
        output['producer_latency_ms'] = asdict(result.producer_latency)

    if result.end_to_end_latency:
        output['end_to_end_latency_ms'] = asdict(result.end_to_end_latency)

    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark Kafka producer/consumer throughput and latency',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Producer benchmark (100k messages)
  %(prog)s --bootstrap-servers localhost:9092 --mode producer --messages 100000

  # Consumer benchmark (consume from existing topic)
  %(prog)s --bootstrap-servers localhost:9092 --mode consumer --topic orders

  # End-to-end benchmark (50k messages)
  %(prog)s --bootstrap-servers localhost:9092 --mode both --messages 50000

  # Custom message size (10 KB)
  %(prog)s --bootstrap-servers localhost:9092 --mode producer --messages 10000 --size 10240

  # JSON output for automation
  %(prog)s --bootstrap-servers localhost:9092 --mode producer --messages 10000 --json
        """
    )

    parser.add_argument(
        '--bootstrap-servers',
        required=True,
        help='Kafka bootstrap servers (e.g., localhost:9092)'
    )

    parser.add_argument(
        '--mode',
        required=True,
        choices=['producer', 'consumer', 'both'],
        help='Benchmark mode: producer, consumer, or both (end-to-end)'
    )

    parser.add_argument(
        '--topic',
        default='benchmark-topic',
        help='Kafka topic for benchmark (default: benchmark-topic)'
    )

    parser.add_argument(
        '--messages',
        type=int,
        default=10000,
        help='Number of messages for benchmark (default: 10000)'
    )

    parser.add_argument(
        '--size',
        type=int,
        default=1024,
        help='Message size in bytes (default: 1024)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='Consumer timeout in seconds (default: 60)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Create benchmark
    benchmark = KafkaBenchmark(args.bootstrap_servers)

    try:
        # Run benchmark based on mode
        if args.mode == 'producer':
            result = benchmark.run_producer_benchmark(
                args.topic,
                args.messages,
                args.size
            )
        elif args.mode == 'consumer':
            result = benchmark.run_consumer_benchmark(
                args.topic,
                args.messages,
                args.timeout
            )
        else:  # both
            result = benchmark.run_end_to_end_benchmark(
                args.topic,
                args.messages,
                args.size
            )

        # Format output
        if args.json:
            output = format_json_output(result)
        else:
            output = format_text_output(result)

        print(output)

        # Exit code
        if result.errors > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\nBenchmark cancelled by user", file=sys.stderr)
        benchmark.stop_flag = True
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        benchmark.close()


if __name__ == '__main__':
    main()
