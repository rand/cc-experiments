#!/usr/bin/env python3
"""
WebSocket Benchmarking Tool

Comprehensive benchmarking tool for WebSocket servers including connection scaling,
throughput, latency distribution, and memory profiling.

Usage:
    ./benchmark_websocket.py --url ws://localhost:8080 --connections 100 --duration 60
    ./benchmark_websocket.py --url ws://localhost:8080 --benchmark throughput --message-size 1024
    ./benchmark_websocket.py --url ws://localhost:8080 --benchmark latency --connections 50
    ./benchmark_websocket.py --url ws://localhost:8080 --benchmark all --json
    ./benchmark_websocket.py --help

Requirements:
    pip install websockets aiohttp psutil
"""

import argparse
import asyncio
import json
import sys
import time
import tracemalloc
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from statistics import mean, median, stdev, quantiles
from urllib.parse import urlparse
import websockets
from websockets.client import WebSocketClientProtocol
import psutil


@dataclass
class BenchmarkResult:
    """Result of a single benchmark"""
    benchmark_name: str
    duration_seconds: float
    connections: int
    messages_sent: int
    messages_received: int
    bytes_sent: int
    bytes_received: int
    errors: int
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results"""
    server_url: str
    timestamp: float
    results: List[BenchmarkResult] = field(default_factory=list)


class WebSocketBenchmark:
    """WebSocket server benchmarking framework"""

    def __init__(
        self,
        url: str,
        verbose: bool = False,
        timeout: int = 10
    ):
        self.url = url
        self.verbose = verbose
        self.timeout = timeout
        self.suite = BenchmarkSuite(server_url=url, timestamp=time.time())

    def log(self, message: str):
        """Log message if verbose"""
        if self.verbose:
            print(f"[{time.strftime('%H:%M:%S')}] {message}")

    async def benchmark_connections(
        self,
        max_connections: int = 1000,
        ramp_up_time: int = 10
    ) -> BenchmarkResult:
        """Benchmark connection scaling"""
        self.log(f"Starting connection benchmark: {max_connections} connections")

        start_time = time.time()
        connections: List[WebSocketClientProtocol] = []
        connection_times: List[float] = []
        errors = 0

        # Calculate delay between connections
        delay = ramp_up_time / max_connections if max_connections > 0 else 0

        try:
            for i in range(max_connections):
                try:
                    conn_start = time.time()
                    ws = await websockets.connect(self.url, open_timeout=self.timeout)
                    conn_time = (time.time() - conn_start) * 1000
                    connection_times.append(conn_time)
                    connections.append(ws)

                    if (i + 1) % 100 == 0:
                        self.log(f"Connected: {i + 1}/{max_connections}")

                    if delay > 0:
                        await asyncio.sleep(delay)

                except Exception as e:
                    errors += 1
                    if self.verbose:
                        self.log(f"Connection {i} failed: {e}")

            # Keep connections alive briefly
            await asyncio.sleep(2)

        finally:
            # Close all connections
            self.log("Closing connections...")
            close_tasks = [ws.close() for ws in connections if ws.open]
            await asyncio.gather(*close_tasks, return_exceptions=True)

        duration = time.time() - start_time
        successful = len(connections)

        result = BenchmarkResult(
            benchmark_name="connection_scaling",
            duration_seconds=duration,
            connections=successful,
            messages_sent=0,
            messages_received=0,
            bytes_sent=0,
            bytes_received=0,
            errors=errors,
            details={
                "target_connections": max_connections,
                "successful_connections": successful,
                "connection_rate": successful / duration,
                "mean_connection_time_ms": mean(connection_times) if connection_times else 0,
                "median_connection_time_ms": median(connection_times) if connection_times else 0,
                "max_connection_time_ms": max(connection_times) if connection_times else 0,
                "min_connection_time_ms": min(connection_times) if connection_times else 0
            }
        )

        self.suite.results.append(result)
        return result

    async def benchmark_throughput(
        self,
        connections: int = 10,
        duration: int = 60,
        message_size: int = 1024
    ) -> BenchmarkResult:
        """Benchmark message throughput"""
        self.log(f"Starting throughput benchmark: {connections} connections, {duration}s")

        test_message = "x" * message_size
        total_sent = 0
        total_received = 0
        total_bytes_sent = 0
        total_bytes_received = 0
        errors = 0

        async def client_worker(client_id: int):
            """Single client worker"""
            nonlocal total_sent, total_received, total_bytes_sent, total_bytes_received, errors

            sent = 0
            received = 0
            bytes_sent = 0
            bytes_received = 0

            try:
                async with websockets.connect(self.url, open_timeout=self.timeout) as ws:
                    test_start = time.time()

                    # Send/receive loop
                    while time.time() - test_start < duration:
                        try:
                            # Send message
                            await ws.send(test_message)
                            sent += 1
                            bytes_sent += len(test_message)

                            # Receive response (non-blocking)
                            try:
                                response = await asyncio.wait_for(ws.recv(), timeout=1.0)
                                received += 1
                                bytes_received += len(response)
                            except asyncio.TimeoutError:
                                pass  # Continue sending

                        except Exception as e:
                            errors += 1
                            if self.verbose:
                                self.log(f"Client {client_id} error: {e}")
                            break

            except Exception as e:
                errors += 1
                if self.verbose:
                    self.log(f"Client {client_id} connection failed: {e}")

            # Update totals
            total_sent += sent
            total_received += received
            total_bytes_sent += bytes_sent
            total_bytes_received += bytes_received

        # Start benchmark
        start_time = time.time()

        # Create client workers
        tasks = [client_worker(i) for i in range(connections)]
        await asyncio.gather(*tasks)

        actual_duration = time.time() - start_time

        result = BenchmarkResult(
            benchmark_name="throughput",
            duration_seconds=actual_duration,
            connections=connections,
            messages_sent=total_sent,
            messages_received=total_received,
            bytes_sent=total_bytes_sent,
            bytes_received=total_bytes_received,
            errors=errors,
            details={
                "message_size_bytes": message_size,
                "messages_per_sec": total_sent / actual_duration,
                "throughput_mbps_sent": (total_bytes_sent * 8 / 1024 / 1024) / actual_duration,
                "throughput_mbps_received": (total_bytes_received * 8 / 1024 / 1024) / actual_duration,
                "avg_messages_per_connection": total_sent / connections if connections > 0 else 0
            }
        )

        self.suite.results.append(result)
        return result

    async def benchmark_latency(
        self,
        connections: int = 10,
        duration: int = 60
    ) -> BenchmarkResult:
        """Benchmark latency distribution"""
        self.log(f"Starting latency benchmark: {connections} connections, {duration}s")

        all_latencies: List[float] = []
        total_sent = 0
        total_received = 0
        errors = 0

        async def client_worker(client_id: int):
            """Single client worker measuring latency"""
            nonlocal total_sent, total_received, errors

            latencies: List[float] = []

            try:
                async with websockets.connect(self.url, open_timeout=self.timeout) as ws:
                    test_start = time.time()

                    while time.time() - test_start < duration:
                        try:
                            # Measure round-trip time
                            ping_start = time.time()
                            await ws.send(json.dumps({"type": "ping", "timestamp": ping_start}))
                            total_sent += 1

                            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                            ping_end = time.time()
                            total_received += 1

                            latency_ms = (ping_end - ping_start) * 1000
                            latencies.append(latency_ms)

                            # Small delay between pings
                            await asyncio.sleep(0.1)

                        except asyncio.TimeoutError:
                            errors += 1
                        except Exception as e:
                            errors += 1
                            if self.verbose:
                                self.log(f"Client {client_id} ping error: {e}")
                            break

            except Exception as e:
                errors += 1
                if self.verbose:
                    self.log(f"Client {client_id} connection failed: {e}")

            all_latencies.extend(latencies)

        # Start benchmark
        start_time = time.time()

        # Create client workers
        tasks = [client_worker(i) for i in range(connections)]
        await asyncio.gather(*tasks)

        actual_duration = time.time() - start_time

        # Calculate statistics
        if all_latencies:
            sorted_latencies = sorted(all_latencies)
            percentiles = quantiles(sorted_latencies, n=100) if len(sorted_latencies) > 100 else []

            details = {
                "samples": len(all_latencies),
                "mean_ms": mean(all_latencies),
                "median_ms": median(all_latencies),
                "min_ms": min(all_latencies),
                "max_ms": max(all_latencies),
                "stddev_ms": stdev(all_latencies) if len(all_latencies) > 1 else 0
            }

            if percentiles:
                details.update({
                    "p50_ms": percentiles[49],  # 50th percentile
                    "p75_ms": percentiles[74],  # 75th percentile
                    "p90_ms": percentiles[89],  # 90th percentile
                    "p95_ms": percentiles[94],  # 95th percentile
                    "p99_ms": percentiles[98],  # 99th percentile
                })

        else:
            details = {"error": "No latency samples collected"}

        result = BenchmarkResult(
            benchmark_name="latency_distribution",
            duration_seconds=actual_duration,
            connections=connections,
            messages_sent=total_sent,
            messages_received=total_received,
            bytes_sent=0,
            bytes_received=0,
            errors=errors,
            details=details
        )

        self.suite.results.append(result)
        return result

    async def benchmark_memory(
        self,
        connections: int = 100,
        hold_time: int = 30
    ) -> BenchmarkResult:
        """Benchmark memory usage with persistent connections"""
        self.log(f"Starting memory benchmark: {connections} connections, {hold_time}s hold time")

        # Start memory tracking
        tracemalloc.start()
        process = psutil.Process()

        # Get baseline memory
        baseline_rss = process.memory_info().rss
        baseline_vms = process.memory_info().vms
        baseline_tracemalloc = tracemalloc.get_traced_memory()[0]

        connections_list: List[WebSocketClientProtocol] = []
        errors = 0

        try:
            # Create connections
            self.log("Establishing connections...")
            for i in range(connections):
                try:
                    ws = await websockets.connect(self.url, open_timeout=self.timeout)
                    connections_list.append(ws)

                    if (i + 1) % 100 == 0:
                        self.log(f"Connected: {i + 1}/{connections}")

                except Exception as e:
                    errors += 1
                    if self.verbose:
                        self.log(f"Connection {i} failed: {e}")

            # Measure memory with connections
            peak_rss = process.memory_info().rss
            peak_vms = process.memory_info().vms
            peak_tracemalloc = tracemalloc.get_traced_memory()[1]  # Peak

            # Hold connections
            self.log(f"Holding {len(connections_list)} connections for {hold_time}s...")
            await asyncio.sleep(hold_time)

            # Measure memory after hold
            hold_rss = process.memory_info().rss
            hold_vms = process.memory_info().vms

        finally:
            # Close connections
            self.log("Closing connections...")
            close_tasks = [ws.close() for ws in connections_list if ws.open]
            await asyncio.gather(*close_tasks, return_exceptions=True)

            # Give time for cleanup
            await asyncio.sleep(2)

            # Measure memory after cleanup
            cleanup_rss = process.memory_info().rss
            cleanup_vms = process.memory_info().vms

            tracemalloc.stop()

        successful = len(connections_list)

        # Calculate memory per connection
        memory_increase_rss = peak_rss - baseline_rss
        memory_increase_vms = peak_vms - baseline_vms
        memory_per_conn_rss = memory_increase_rss / successful if successful > 0 else 0
        memory_per_conn_vms = memory_increase_vms / successful if successful > 0 else 0

        result = BenchmarkResult(
            benchmark_name="memory_usage",
            duration_seconds=hold_time,
            connections=successful,
            messages_sent=0,
            messages_received=0,
            bytes_sent=0,
            bytes_received=0,
            errors=errors,
            details={
                "baseline_memory_mb": baseline_rss / 1024 / 1024,
                "peak_memory_mb": peak_rss / 1024 / 1024,
                "hold_memory_mb": hold_rss / 1024 / 1024,
                "cleanup_memory_mb": cleanup_rss / 1024 / 1024,
                "memory_increase_mb": memory_increase_rss / 1024 / 1024,
                "memory_per_connection_kb": memory_per_conn_rss / 1024,
                "virtual_memory_increase_mb": memory_increase_vms / 1024 / 1024,
                "tracemalloc_peak_mb": peak_tracemalloc / 1024 / 1024,
                "memory_retained_after_cleanup_mb": (cleanup_rss - baseline_rss) / 1024 / 1024
            }
        )

        self.suite.results.append(result)
        return result

    async def benchmark_burst(
        self,
        connections: int = 10,
        messages_per_burst: int = 1000,
        burst_count: int = 10
    ) -> BenchmarkResult:
        """Benchmark burst message handling"""
        self.log(f"Starting burst benchmark: {connections} connections, {messages_per_burst} msgs/burst")

        total_sent = 0
        total_received = 0
        burst_times: List[float] = []
        errors = 0

        async def client_worker(client_id: int):
            """Single client worker"""
            nonlocal total_sent, total_received, errors

            try:
                async with websockets.connect(self.url, open_timeout=self.timeout) as ws:
                    for burst_num in range(burst_count):
                        burst_start = time.time()

                        # Send burst
                        for i in range(messages_per_burst):
                            try:
                                await ws.send(f"burst-{burst_num}-{i}")
                                total_sent += 1
                            except Exception as e:
                                errors += 1
                                break

                        # Try to receive responses
                        received_in_burst = 0
                        try:
                            while received_in_burst < messages_per_burst:
                                response = await asyncio.wait_for(ws.recv(), timeout=0.1)
                                received_in_burst += 1
                                total_received += 1
                        except asyncio.TimeoutError:
                            pass  # No more messages available

                        burst_time = time.time() - burst_start
                        burst_times.append(burst_time)

                        # Small delay between bursts
                        await asyncio.sleep(1)

            except Exception as e:
                errors += 1
                if self.verbose:
                    self.log(f"Client {client_id} failed: {e}")

        # Start benchmark
        start_time = time.time()

        # Create client workers
        tasks = [client_worker(i) for i in range(connections)]
        await asyncio.gather(*tasks)

        actual_duration = time.time() - start_time

        result = BenchmarkResult(
            benchmark_name="burst_handling",
            duration_seconds=actual_duration,
            connections=connections,
            messages_sent=total_sent,
            messages_received=total_received,
            bytes_sent=0,
            bytes_received=0,
            errors=errors,
            details={
                "messages_per_burst": messages_per_burst,
                "burst_count": burst_count,
                "total_bursts": len(burst_times),
                "mean_burst_time_s": mean(burst_times) if burst_times else 0,
                "max_burst_time_s": max(burst_times) if burst_times else 0,
                "min_burst_time_s": min(burst_times) if burst_times else 0,
                "messages_per_sec": total_sent / actual_duration if actual_duration > 0 else 0
            }
        )

        self.suite.results.append(result)
        return result

    async def run_all_benchmarks(
        self,
        connections: int = 100,
        duration: int = 60,
        message_size: int = 1024
    ) -> BenchmarkSuite:
        """Run all benchmarks"""
        benchmarks = [
            ("Connection Scaling", self.benchmark_connections(max_connections=connections)),
            ("Throughput", self.benchmark_throughput(connections=connections // 10, duration=duration, message_size=message_size)),
            ("Latency Distribution", self.benchmark_latency(connections=connections // 10, duration=duration)),
            ("Memory Usage", self.benchmark_memory(connections=connections, hold_time=30)),
            ("Burst Handling", self.benchmark_burst(connections=connections // 10, messages_per_burst=1000))
        ]

        for name, benchmark_coro in benchmarks:
            self.log(f"\n{'='*60}")
            self.log(f"Running: {name}")
            self.log(f"{'='*60}")
            await benchmark_coro
            self.log(f"Completed: {name}")

        return self.suite


def format_output(suite: BenchmarkSuite, output_format: str = "text") -> str:
    """Format benchmark suite results"""
    if output_format == "json":
        return json.dumps(asdict(suite), indent=2)

    # Text output
    lines = []
    lines.append(f"\n{'='*70}")
    lines.append(f"WebSocket Benchmark Results")
    lines.append(f"{'='*70}")
    lines.append(f"Server URL: {suite.server_url}")
    lines.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(suite.timestamp))}")

    for result in suite.results:
        lines.append(f"\n{'='*70}")
        lines.append(f"{result.benchmark_name.upper().replace('_', ' ')}")
        lines.append(f"{'='*70}")
        lines.append(f"Duration: {result.duration_seconds:.2f}s")
        lines.append(f"Connections: {result.connections}")
        lines.append(f"Messages Sent: {result.messages_sent}")
        lines.append(f"Messages Received: {result.messages_received}")

        if result.bytes_sent > 0:
            lines.append(f"Bytes Sent: {result.bytes_sent:,} ({result.bytes_sent / 1024 / 1024:.2f} MB)")
        if result.bytes_received > 0:
            lines.append(f"Bytes Received: {result.bytes_received:,} ({result.bytes_received / 1024 / 1024:.2f} MB)")

        lines.append(f"Errors: {result.errors}")

        if result.details:
            lines.append(f"\nDetails:")
            for key, value in result.details.items():
                if isinstance(value, float):
                    lines.append(f"  {key.replace('_', ' ').title()}: {value:.2f}")
                else:
                    lines.append(f"  {key.replace('_', ' ').title()}: {value}")

    lines.append(f"\n{'='*70}\n")
    return "\n".join(lines)


async def main_async(args):
    """Async main function"""
    benchmark = WebSocketBenchmark(args.url, verbose=args.verbose, timeout=args.timeout)

    if args.benchmark == "all":
        suite = await benchmark.run_all_benchmarks(
            connections=args.connections,
            duration=args.duration,
            message_size=args.message_size
        )
    elif args.benchmark == "connections":
        await benchmark.benchmark_connections(max_connections=args.connections)
    elif args.benchmark == "throughput":
        await benchmark.benchmark_throughput(
            connections=args.connections,
            duration=args.duration,
            message_size=args.message_size
        )
    elif args.benchmark == "latency":
        await benchmark.benchmark_latency(connections=args.connections, duration=args.duration)
    elif args.benchmark == "memory":
        await benchmark.benchmark_memory(connections=args.connections, hold_time=args.duration)
    elif args.benchmark == "burst":
        await benchmark.benchmark_burst(
            connections=args.connections,
            messages_per_burst=args.burst_size
        )

    suite = benchmark.suite

    # Output results
    output_format = "json" if args.json else "text"
    print(format_output(suite, output_format))


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark WebSocket server performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all benchmarks
  %(prog)s --url ws://localhost:8080 --benchmark all --connections 100

  # Benchmark connection scaling
  %(prog)s --url ws://localhost:8080 --benchmark connections --connections 1000

  # Benchmark throughput
  %(prog)s --url ws://localhost:8080 --benchmark throughput --connections 50 --duration 60

  # Benchmark latency
  %(prog)s --url ws://localhost:8080 --benchmark latency --connections 10 --duration 60

  # Benchmark memory usage
  %(prog)s --url ws://localhost:8080 --benchmark memory --connections 500

  # JSON output
  %(prog)s --url ws://localhost:8080 --benchmark all --json

Available benchmarks:
  all          - Run all benchmarks
  connections  - Connection scaling test
  throughput   - Message throughput test
  latency      - Latency distribution test
  memory       - Memory usage test
  burst        - Burst message handling test
        """
    )

    parser.add_argument(
        "--url",
        required=True,
        help="WebSocket server URL (ws:// or wss://)"
    )

    parser.add_argument(
        "--benchmark",
        choices=["all", "connections", "throughput", "latency", "memory", "burst"],
        default="all",
        help="Benchmark to run (default: all)"
    )

    parser.add_argument(
        "--connections",
        type=int,
        default=100,
        help="Number of concurrent connections (default: 100)"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Benchmark duration in seconds (default: 60)"
    )

    parser.add_argument(
        "--message-size",
        type=int,
        default=1024,
        help="Message size in bytes for throughput test (default: 1024)"
    )

    parser.add_argument(
        "--burst-size",
        type=int,
        default=1000,
        help="Messages per burst for burst test (default: 1000)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Connection timeout in seconds (default: 10)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Validate URL
    parsed = urlparse(args.url)
    if parsed.scheme not in ["ws", "wss"]:
        print(f"Error: Invalid WebSocket URL scheme: {parsed.scheme}", file=sys.stderr)
        print("URL must start with ws:// or wss://", file=sys.stderr)
        sys.exit(1)

    # Run async main
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
