#!/usr/bin/env python3
"""
MQTT Broker Benchmark Tool

Benchmarks MQTT broker performance including connections, throughput, and latency.

Usage:
    ./benchmark_mqtt_broker.py --broker mqtt.example.com --connections 1000 --duration 60
    ./benchmark_mqtt_broker.py --broker localhost --test throughput --messages 10000
    ./benchmark_mqtt_broker.py --broker mqtt.example.com --test latency --count 100
    ./benchmark_mqtt_broker.py --broker localhost --connections 1000 --ramp-up 30 --json
"""

import argparse
import json
import sys
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import paho.mqtt.client as mqtt

@dataclass
class BenchmarkResult:
    """Benchmark results"""
    test_type: str
    broker: str
    port: int
    duration: float = 0.0
    connections: int = 0
    connections_succeeded: int = 0
    connections_failed: int = 0
    connection_rate: float = 0.0
    messages_sent: int = 0
    messages_received: int = 0
    throughput: float = 0.0
    latencies: List[float] = field(default_factory=list)
    min_latency: float = 0.0
    avg_latency: float = 0.0
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    max_latency: float = 0.0
    errors: List[str] = field(default_factory=list)

class MQTTBenchmark:
    """MQTT broker benchmarking"""

    def __init__(self, broker: str, port: int = 1883, username: Optional[str] = None,
                 password: Optional[str] = None):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.verbose = False

    def benchmark_connections(self, num_connections: int, ramp_up: int = 0,
                             duration: int = 60) -> BenchmarkResult:
        """Benchmark connection establishment"""
        result = BenchmarkResult(
            test_type="connections",
            broker=self.broker,
            port=self.port,
            connections=num_connections
        )

        clients = []
        lock = threading.Lock()
        start_time = time.time()

        def connect_client(client_id: int):
            try:
                client = mqtt.Client(client_id=f"bench_conn_{client_id}")
                if self.username and self.password:
                    client.username_pw_set(self.username, self.password)

                connected = threading.Event()

                def on_connect(client, userdata, flags, rc):
                    if rc == 0:
                        with lock:
                            result.connections_succeeded += 1
                        connected.set()
                    else:
                        with lock:
                            result.connections_failed += 1
                            result.errors.append(f"Client {client_id} connection failed: {rc}")

                client.on_connect = on_connect
                client.connect(self.broker, self.port, keepalive=60)
                client.loop_start()

                # Wait for connection
                if connected.wait(timeout=10):
                    with lock:
                        clients.append(client)
                else:
                    with lock:
                        result.connections_failed += 1
                        result.errors.append(f"Client {client_id} connection timeout")
                    client.loop_stop()

            except Exception as e:
                with lock:
                    result.connections_failed += 1
                    result.errors.append(f"Client {client_id} exception: {e}")

        # Ramp-up phase
        if ramp_up > 0:
            delay = ramp_up / num_connections
            if self.verbose:
                print(f"Ramping up {num_connections} connections over {ramp_up}s...")

            threads = []
            for i in range(num_connections):
                t = threading.Thread(target=connect_client, args=(i,))
                threads.append(t)
                t.start()

                if ramp_up > 0:
                    time.sleep(delay)

            # Wait for all threads
            for t in threads:
                t.join()
        else:
            # Connect all at once
            if self.verbose:
                print(f"Connecting {num_connections} clients...")

            threads = []
            for i in range(num_connections):
                t = threading.Thread(target=connect_client, args=(i,))
                threads.append(t)
                t.start()

            # Wait for all threads
            for t in threads:
                t.join()

        connection_time = time.time() - start_time

        # Hold connections for duration
        if self.verbose:
            print(f"Holding {result.connections_succeeded} connections for {duration}s...")

        time.sleep(duration)

        # Disconnect
        if self.verbose:
            print("Disconnecting clients...")

        for client in clients:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass

        total_time = time.time() - start_time

        # Calculate stats
        result.duration = total_time
        if connection_time > 0:
            result.connection_rate = result.connections_succeeded / connection_time

        return result

    def benchmark_throughput(self, num_messages: int, qos: int = 0) -> BenchmarkResult:
        """Benchmark message throughput"""
        result = BenchmarkResult(
            test_type="throughput",
            broker=self.broker,
            port=self.port,
            messages_sent=num_messages
        )

        received_count = [0]
        lock = threading.Lock()

        # Subscriber
        sub_client = mqtt.Client(client_id="bench_throughput_sub")
        if self.username and self.password:
            sub_client.username_pw_set(self.username, self.password)

        def on_message(client, userdata, msg):
            with lock:
                received_count[0] += 1

        sub_client.on_message = on_message

        try:
            sub_client.connect(self.broker, self.port, keepalive=60)
            sub_client.subscribe("benchmark/throughput", qos=qos)
            sub_client.loop_start()
            time.sleep(1)

            # Publisher
            pub_client = mqtt.Client(client_id="bench_throughput_pub")
            if self.username and self.password:
                pub_client.username_pw_set(self.username, self.password)

            pub_client.connect(self.broker, self.port, keepalive=60)
            pub_client.loop_start()
            time.sleep(1)

            # Publish messages
            if self.verbose:
                print(f"Publishing {num_messages} messages (QoS {qos})...")

            start_time = time.time()

            for i in range(num_messages):
                pub_client.publish("benchmark/throughput", f"msg_{i}", qos=qos)

            # Wait for QoS 1/2
            if qos > 0:
                time.sleep(2)

            # Wait for all messages to be received
            timeout = 30
            wait_time = 0
            while wait_time < timeout:
                with lock:
                    if received_count[0] >= num_messages:
                        break
                time.sleep(0.1)
                wait_time += 0.1

            end_time = time.time()
            duration = end_time - start_time

            with lock:
                result.messages_received = received_count[0]

            result.duration = duration
            if duration > 0:
                result.throughput = result.messages_received / duration

            # Cleanup
            pub_client.loop_stop()
            pub_client.disconnect()
            sub_client.loop_stop()
            sub_client.disconnect()

        except Exception as e:
            result.errors.append(f"Throughput test exception: {e}")

        return result

    def benchmark_latency(self, num_messages: int, qos: int = 1) -> BenchmarkResult:
        """Benchmark pub-sub latency"""
        result = BenchmarkResult(
            test_type="latency",
            broker=self.broker,
            port=self.port,
            messages_sent=num_messages
        )

        latencies = []
        message_times = {}
        lock = threading.Lock()

        # Subscriber
        sub_client = mqtt.Client(client_id="bench_latency_sub")
        if self.username and self.password:
            sub_client.username_pw_set(self.username, self.password)

        def on_message(client, userdata, msg):
            recv_time = time.time()
            try:
                msg_id = int(msg.payload.decode())
                if msg_id in message_times:
                    latency = recv_time - message_times[msg_id]
                    with lock:
                        latencies.append(latency)
                        result.messages_received += 1
            except:
                pass

        sub_client.on_message = on_message

        try:
            sub_client.connect(self.broker, self.port, keepalive=60)
            sub_client.subscribe("benchmark/latency", qos=qos)
            sub_client.loop_start()
            time.sleep(1)

            # Publisher
            pub_client = mqtt.Client(client_id="bench_latency_pub")
            if self.username and self.password:
                pub_client.username_pw_set(self.username, self.password)

            pub_client.connect(self.broker, self.port, keepalive=60)
            pub_client.loop_start()
            time.sleep(1)

            # Publish messages
            if self.verbose:
                print(f"Measuring latency for {num_messages} messages (QoS {qos})...")

            start_time = time.time()

            for i in range(num_messages):
                send_time = time.time()
                message_times[i] = send_time
                pub_client.publish("benchmark/latency", str(i), qos=qos)
                time.sleep(0.01)  # Small delay between messages

            # Wait for all messages
            timeout = 30
            wait_time = 0
            while wait_time < timeout:
                with lock:
                    if len(latencies) >= num_messages:
                        break
                time.sleep(0.1)
                wait_time += 0.1

            end_time = time.time()
            result.duration = end_time - start_time

            # Calculate statistics
            with lock:
                result.latencies = sorted(latencies)

                if result.latencies:
                    result.min_latency = result.latencies[0]
                    result.max_latency = result.latencies[-1]
                    result.avg_latency = sum(result.latencies) / len(result.latencies)

                    p50_idx = int(len(result.latencies) * 0.50)
                    p95_idx = int(len(result.latencies) * 0.95)
                    p99_idx = int(len(result.latencies) * 0.99)

                    result.p50_latency = result.latencies[p50_idx] if p50_idx < len(result.latencies) else 0
                    result.p95_latency = result.latencies[p95_idx] if p95_idx < len(result.latencies) else 0
                    result.p99_latency = result.latencies[p99_idx] if p99_idx < len(result.latencies) else 0

            # Cleanup
            pub_client.loop_stop()
            pub_client.disconnect()
            sub_client.loop_stop()
            sub_client.disconnect()

        except Exception as e:
            result.errors.append(f"Latency test exception: {e}")

        return result

def format_result(result: BenchmarkResult) -> str:
    """Format benchmark result"""
    lines = [f"{result.test_type.capitalize()} Benchmark Results:"]
    lines.append(f"  Broker: {result.broker}:{result.port}")
    lines.append(f"  Duration: {result.duration:.2f}s")

    if result.test_type == "connections":
        lines.append(f"  Connections attempted: {result.connections}")
        lines.append(f"  Connections succeeded: {result.connections_succeeded}")
        lines.append(f"  Connections failed: {result.connections_failed}")
        lines.append(f"  Connection rate: {result.connection_rate:.2f} conn/sec")

    elif result.test_type == "throughput":
        lines.append(f"  Messages sent: {result.messages_sent}")
        lines.append(f"  Messages received: {result.messages_received}")
        lines.append(f"  Throughput: {result.throughput:.2f} msg/sec")

    elif result.test_type == "latency":
        lines.append(f"  Messages sent: {result.messages_sent}")
        lines.append(f"  Messages received: {result.messages_received}")
        if result.latencies:
            lines.append(f"  Latency (ms):")
            lines.append(f"    Min: {result.min_latency * 1000:.2f}")
            lines.append(f"    Avg: {result.avg_latency * 1000:.2f}")
            lines.append(f"    P50: {result.p50_latency * 1000:.2f}")
            lines.append(f"    P95: {result.p95_latency * 1000:.2f}")
            lines.append(f"    P99: {result.p99_latency * 1000:.2f}")
            lines.append(f"    Max: {result.max_latency * 1000:.2f}")

    if result.errors:
        lines.append(f"  Errors ({len(result.errors)} total):")
        for error in result.errors[:5]:  # Show first 5
            lines.append(f"    - {error}")
        if len(result.errors) > 5:
            lines.append(f"    ... and {len(result.errors) - 5} more")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark MQTT broker performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Benchmark connections
  %(prog)s --broker mqtt.example.com --connections 1000 --duration 60

  # With ramp-up
  %(prog)s --broker localhost --connections 5000 --ramp-up 120 --duration 300

  # Benchmark throughput
  %(prog)s --broker mqtt.example.com --test throughput --messages 10000

  # Benchmark latency
  %(prog)s --broker mqtt.example.com --test latency --count 100

  # JSON output
  %(prog)s --broker mqtt.example.com --connections 1000 --json
        """
    )

    parser.add_argument(
        '--broker',
        required=True,
        help='MQTT broker hostname'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=1883,
        help='MQTT broker port (default: 1883)'
    )
    parser.add_argument(
        '--username',
        help='MQTT username'
    )
    parser.add_argument(
        '--password',
        help='MQTT password'
    )
    parser.add_argument(
        '--test',
        choices=['connections', 'throughput', 'latency'],
        help='Test type (default: connections if --connections specified)'
    )
    parser.add_argument(
        '--connections',
        type=int,
        help='Number of concurrent connections to test'
    )
    parser.add_argument(
        '--ramp-up',
        type=int,
        default=0,
        help='Ramp-up time in seconds for connections (default: 0 = all at once)'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Duration to hold connections in seconds (default: 60)'
    )
    parser.add_argument(
        '--messages',
        type=int,
        default=10000,
        help='Number of messages for throughput test (default: 10000)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=100,
        help='Number of messages for latency test (default: 100)'
    )
    parser.add_argument(
        '--qos',
        type=int,
        choices=[0, 1, 2],
        default=0,
        help='QoS level (default: 0)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Determine test type
    if args.test:
        test_type = args.test
    elif args.connections:
        test_type = 'connections'
    else:
        parser.print_help()
        sys.exit(1)

    benchmark = MQTTBenchmark(
        broker=args.broker,
        port=args.port,
        username=args.username,
        password=args.password
    )
    benchmark.verbose = args.verbose

    # Run benchmark
    if test_type == 'connections':
        if not args.connections:
            print("Error: --connections required for connections test")
            sys.exit(1)

        if args.verbose:
            print(f"Benchmarking {args.connections} connections...")

        result = benchmark.benchmark_connections(
            num_connections=args.connections,
            ramp_up=args.ramp_up,
            duration=args.duration
        )

    elif test_type == 'throughput':
        if args.verbose:
            print(f"Benchmarking throughput ({args.messages} messages, QoS {args.qos})...")

        result = benchmark.benchmark_throughput(
            num_messages=args.messages,
            qos=args.qos
        )

    elif test_type == 'latency':
        if args.verbose:
            print(f"Benchmarking latency ({args.count} messages, QoS {args.qos})...")

        result = benchmark.benchmark_latency(
            num_messages=args.count,
            qos=args.qos
        )

    # Output results
    if args.json:
        # Remove latencies list for JSON (too large)
        output = asdict(result)
        output['latencies'] = len(result.latencies)
        print(json.dumps(output, indent=2))
    else:
        print("\n=== MQTT Broker Benchmark ===\n")
        print(format_result(result))

    sys.exit(0)

if __name__ == "__main__":
    main()
