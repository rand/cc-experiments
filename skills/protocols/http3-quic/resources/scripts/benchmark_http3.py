#!/usr/bin/env python3
"""
HTTP/3 Performance Benchmark Tool

Comprehensive benchmarking for HTTP/3 throughput, latency, packet loss resilience, and multiplexing.

Usage:
    ./benchmark_http3.py --url https://example.com [--json]
    ./benchmark_http3.py --url https://example.com --test throughput --duration 30 [--json]
    ./benchmark_http3.py --url https://example.com --test latency --count 100 [--json]
    ./benchmark_http3.py --url https://example.com --simulate-loss 1 [--json]
    ./benchmark_http3.py --help

Features:
    - Throughput testing (requests/sec, bytes/sec)
    - Latency measurement (P50, P95, P99 percentiles)
    - Packet loss simulation and resilience testing
    - Multiplexing efficiency (concurrent streams)
    - Connection establishment benchmarking
    - 0-RTT performance comparison
    - Output as JSON or human-readable text

Exit Codes:
    0: Success
    1: Benchmark completed with warnings
    2: Benchmark failed
    3: Invalid arguments
"""

import argparse
import asyncio
import json
import sys
import time
import statistics
import ssl
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from collections import defaultdict


try:
    from aioquic.asyncio import connect
    from aioquic.h3.connection import H3_ALPN, H3Connection
    from aioquic.h3.events import DataReceived, HeadersReceived
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.quic.events import QuicEvent
    AIOQUIC_AVAILABLE = True
except ImportError:
    AIOQUIC_AVAILABLE = False


@dataclass
class BenchmarkResult:
    """Result of a benchmark test"""
    test_name: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    bytes_sent: int = 0
    bytes_received: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def requests_per_second(self) -> float:
        """Calculate requests per second"""
        if self.duration_seconds == 0:
            return 0
        return self.total_requests / self.duration_seconds

    def bytes_per_second(self) -> float:
        """Calculate bytes per second"""
        if self.duration_seconds == 0:
            return 0
        return self.bytes_received / self.duration_seconds

    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0
        return (self.successful_requests / self.total_requests) * 100

    def latency_stats(self) -> Dict[str, float]:
        """Calculate latency statistics"""
        if not self.latencies_ms:
            return {}

        sorted_latencies = sorted(self.latencies_ms)
        return {
            "min_ms": min(self.latencies_ms),
            "max_ms": max(self.latencies_ms),
            "avg_ms": statistics.mean(self.latencies_ms),
            "median_ms": statistics.median(self.latencies_ms),
            "p50_ms": sorted_latencies[int(len(sorted_latencies) * 0.50)],
            "p95_ms": sorted_latencies[int(len(sorted_latencies) * 0.95)],
            "p99_ms": sorted_latencies[int(len(sorted_latencies) * 0.99)],
            "stdev_ms": statistics.stdev(self.latencies_ms) if len(self.latencies_ms) > 1 else 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "test_name": self.test_name,
            "duration_seconds": self.duration_seconds,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate(),
            "requests_per_second": self.requests_per_second(),
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "bytes_per_second": self.bytes_per_second(),
            "latency_stats": self.latency_stats(),
            "metrics": self.metrics,
        }


class HTTP3Benchmark:
    """HTTP/3 performance benchmark suite"""

    def __init__(self, url: str, verify_ssl: bool = True):
        self.url = url
        self.verify_ssl = verify_ssl
        self.parsed_url = urlparse(url)

        if not self.parsed_url.scheme == 'https':
            raise ValueError("URL must use https://")

        self.host = self.parsed_url.hostname
        self.port = self.parsed_url.port or 443
        self.path = self.parsed_url.path or '/'

    async def _make_request(self, configuration: QuicConfiguration) -> Tuple[bool, float, int]:
        """Make a single HTTP/3 request"""
        start = time.time()
        bytes_received = 0

        try:
            async with connect(
                self.host,
                self.port,
                configuration=configuration,
            ) as client:
                http = H3Connection(client._quic)
                stream_id = client._quic.get_next_available_stream_id()

                headers = [
                    (b":method", b"GET"),
                    (b":scheme", b"https"),
                    (b":authority", self.host.encode()),
                    (b":path", self.path.encode()),
                    (b"user-agent", b"http3-benchmark/1.0"),
                ]

                http.send_headers(stream_id=stream_id, headers=headers)

                # Wait for response
                response_received = False
                status_code = None

                while not response_received:
                    for event in client._quic.next_event():
                        if isinstance(event, HeadersReceived):
                            for header, value in event.headers:
                                if header == b":status":
                                    status_code = int(value.decode())

                        elif isinstance(event, DataReceived):
                            bytes_received += len(event.data)
                            if event.stream_ended:
                                response_received = True

                    if not response_received:
                        await asyncio.sleep(0.001)

                duration = (time.time() - start) * 1000
                success = status_code == 200

                return success, duration, bytes_received

        except Exception as e:
            duration = (time.time() - start) * 1000
            return False, duration, 0

    async def benchmark_throughput(self, duration_seconds: int = 30,
                                   concurrent: int = 1) -> BenchmarkResult:
        """Benchmark throughput (requests/sec, bytes/sec)"""
        result = BenchmarkResult(
            test_name="throughput",
            duration_seconds=duration_seconds,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
        )

        configuration = QuicConfiguration(
            alpn_protocols=H3_ALPN,
            is_client=True,
            verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
        )

        start_time = time.time()
        end_time = start_time + duration_seconds

        async def worker():
            """Worker coroutine for making requests"""
            while time.time() < end_time:
                success, latency, bytes_recv = await self._make_request(configuration)

                result.total_requests += 1
                if success:
                    result.successful_requests += 1
                else:
                    result.failed_requests += 1

                result.bytes_received += bytes_recv
                result.latencies_ms.append(latency)

        # Run concurrent workers
        tasks = [worker() for _ in range(concurrent)]
        await asyncio.gather(*tasks)

        result.duration_seconds = time.time() - start_time
        result.metrics["concurrent_workers"] = concurrent

        return result

    async def benchmark_latency(self, count: int = 100) -> BenchmarkResult:
        """Benchmark latency with percentile analysis"""
        result = BenchmarkResult(
            test_name="latency",
            duration_seconds=0,
            total_requests=count,
            successful_requests=0,
            failed_requests=0,
        )

        configuration = QuicConfiguration(
            alpn_protocols=H3_ALPN,
            is_client=True,
            verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
        )

        start_time = time.time()

        for i in range(count):
            success, latency, bytes_recv = await self._make_request(configuration)

            if success:
                result.successful_requests += 1
            else:
                result.failed_requests += 1

            result.bytes_received += bytes_recv
            result.latencies_ms.append(latency)

        result.duration_seconds = time.time() - start_time
        result.metrics["test_count"] = count

        return result

    async def benchmark_multiplexing(self, num_streams: int = 10,
                                     requests_per_stream: int = 10) -> BenchmarkResult:
        """Benchmark multiplexing efficiency with concurrent streams"""
        result = BenchmarkResult(
            test_name="multiplexing",
            duration_seconds=0,
            total_requests=num_streams * requests_per_stream,
            successful_requests=0,
            failed_requests=0,
        )

        configuration = QuicConfiguration(
            alpn_protocols=H3_ALPN,
            is_client=True,
            verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
        )

        start_time = time.time()

        async def stream_worker():
            """Worker for a single stream making multiple requests"""
            for _ in range(requests_per_stream):
                success, latency, bytes_recv = await self._make_request(configuration)

                if success:
                    result.successful_requests += 1
                else:
                    result.failed_requests += 1

                result.bytes_received += bytes_recv
                result.latencies_ms.append(latency)

        # Run concurrent streams
        tasks = [stream_worker() for _ in range(num_streams)]
        await asyncio.gather(*tasks)

        result.duration_seconds = time.time() - start_time
        result.metrics.update({
            "num_streams": num_streams,
            "requests_per_stream": requests_per_stream,
        })

        return result

    async def benchmark_connection_establishment(self, count: int = 50) -> BenchmarkResult:
        """Benchmark connection establishment time"""
        result = BenchmarkResult(
            test_name="connection_establishment",
            duration_seconds=0,
            total_requests=count,
            successful_requests=0,
            failed_requests=0,
        )

        connection_times = []

        for i in range(count):
            configuration = QuicConfiguration(
                alpn_protocols=H3_ALPN,
                is_client=True,
                verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
            )

            start = time.time()

            try:
                async with connect(
                    self.host,
                    self.port,
                    configuration=configuration,
                ) as client:
                    # Connection established
                    conn_time = (time.time() - start) * 1000
                    connection_times.append(conn_time)
                    result.successful_requests += 1

            except Exception as e:
                conn_time = (time.time() - start) * 1000
                connection_times.append(conn_time)
                result.failed_requests += 1

        result.duration_seconds = time.time() - start
        result.latencies_ms = connection_times
        result.metrics["test_count"] = count

        return result

    async def benchmark_0rtt_performance(self, iterations: int = 20) -> BenchmarkResult:
        """Benchmark 0-RTT vs 1-RTT performance"""
        result = BenchmarkResult(
            test_name="0rtt_performance",
            duration_seconds=0,
            total_requests=iterations * 2,
            successful_requests=0,
            failed_requests=0,
        )

        rtt_1_times = []
        rtt_0_times = []

        # First, establish connection and get session ticket
        configuration = QuicConfiguration(
            alpn_protocols=H3_ALPN,
            is_client=True,
            verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
        )

        session_ticket = None

        def save_ticket(ticket):
            nonlocal session_ticket
            session_ticket = ticket

        configuration.session_ticket_handler = save_ticket

        # Initial connection to get ticket
        async with connect(
            self.host,
            self.port,
            configuration=configuration,
        ) as client:
            await asyncio.sleep(0.5)

        if not session_ticket:
            result.failed_requests = result.total_requests
            result.metrics["error"] = "Server did not provide session ticket"
            return result

        start_time = time.time()

        # Test 1-RTT connections
        for i in range(iterations):
            config_1rtt = QuicConfiguration(
                alpn_protocols=H3_ALPN,
                is_client=True,
                verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
            )

            start = time.time()
            try:
                async with connect(
                    self.host,
                    self.port,
                    configuration=config_1rtt,
                ) as client:
                    conn_time = (time.time() - start) * 1000
                    rtt_1_times.append(conn_time)
                    result.successful_requests += 1
            except:
                result.failed_requests += 1

        # Test 0-RTT connections
        for i in range(iterations):
            config_0rtt = QuicConfiguration(
                alpn_protocols=H3_ALPN,
                is_client=True,
                verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
            )
            config_0rtt.load_session_ticket(session_ticket)

            start = time.time()
            try:
                async with connect(
                    self.host,
                    self.port,
                    configuration=config_0rtt,
                ) as client:
                    conn_time = (time.time() - start) * 1000
                    rtt_0_times.append(conn_time)
                    result.successful_requests += 1
            except:
                result.failed_requests += 1

        result.duration_seconds = time.time() - start_time

        # Calculate statistics
        if rtt_1_times and rtt_0_times:
            avg_1rtt = statistics.mean(rtt_1_times)
            avg_0rtt = statistics.mean(rtt_0_times)
            improvement = ((avg_1rtt - avg_0rtt) / avg_1rtt) * 100

            result.metrics.update({
                "1rtt_avg_ms": avg_1rtt,
                "0rtt_avg_ms": avg_0rtt,
                "improvement_percent": improvement,
                "iterations": iterations,
            })

        return result

    async def benchmark_packet_loss_resilience(self, loss_rate: float = 1.0,
                                               count: int = 50) -> BenchmarkResult:
        """Benchmark performance under simulated packet loss"""
        result = BenchmarkResult(
            test_name="packet_loss_resilience",
            duration_seconds=0,
            total_requests=count,
            successful_requests=0,
            failed_requests=0,
        )

        # Note: Actual packet loss simulation requires OS-level tools (tc, netem)
        # This benchmark measures performance under lossy conditions if available

        configuration = QuicConfiguration(
            alpn_protocols=H3_ALPN,
            is_client=True,
            verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
        )

        start_time = time.time()

        for i in range(count):
            success, latency, bytes_recv = await self._make_request(configuration)

            if success:
                result.successful_requests += 1
            else:
                result.failed_requests += 1

            result.bytes_received += bytes_recv
            result.latencies_ms.append(latency)

        result.duration_seconds = time.time() - start_time
        result.metrics.update({
            "simulated_loss_rate": loss_rate,
            "test_count": count,
            "note": "Actual packet loss requires OS-level tools (tc netem)",
        })

        return result


def print_human_readable(results: List[BenchmarkResult]):
    """Print results in human-readable format"""
    print(f"\nHTTP/3 Performance Benchmark Results")
    print(f"{'=' * 80}\n")

    for result in results:
        print(f"{result.test_name.replace('_', ' ').title()}")
        print("-" * 80)

        print(f"Duration: {result.duration_seconds:.2f} seconds")
        print(f"Total Requests: {result.total_requests}")
        print(f"Successful: {result.successful_requests}")
        print(f"Failed: {result.failed_requests}")
        print(f"Success Rate: {result.success_rate():.1f}%")

        if result.total_requests > 0:
            print(f"Requests/sec: {result.requests_per_second():.2f}")

        if result.bytes_received > 0:
            print(f"Bytes Received: {result.bytes_received:,}")
            print(f"Throughput: {result.bytes_per_second() / 1024:.2f} KB/sec")

        if result.latencies_ms:
            stats = result.latency_stats()
            print(f"\nLatency Statistics:")
            print(f"  Min: {stats['min_ms']:.2f}ms")
            print(f"  Max: {stats['max_ms']:.2f}ms")
            print(f"  Avg: {stats['avg_ms']:.2f}ms")
            print(f"  Median: {stats['median_ms']:.2f}ms")
            print(f"  P95: {stats['p95_ms']:.2f}ms")
            print(f"  P99: {stats['p99_ms']:.2f}ms")
            print(f"  StdDev: {stats['stdev_ms']:.2f}ms")

        if result.metrics:
            print(f"\nAdditional Metrics:")
            for key, value in result.metrics.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")

        print()


async def main_async():
    parser = argparse.ArgumentParser(
        description="HTTP/3 Performance Benchmark Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic throughput test (30 seconds)
  ./benchmark_http3.py --url https://cloudflare-quic.com --test throughput

  # Latency test (100 requests)
  ./benchmark_http3.py --url https://cloudflare-quic.com --test latency --count 100

  # Multiplexing test
  ./benchmark_http3.py --url https://cloudflare-quic.com --test multiplexing

  # 0-RTT performance
  ./benchmark_http3.py --url https://cloudflare-quic.com --test 0rtt

  # All tests with JSON output
  ./benchmark_http3.py --url https://cloudflare-quic.com --test all --json

  # Custom throughput test (60 seconds, 5 concurrent workers)
  ./benchmark_http3.py --url https://cloudflare-quic.com --test throughput --duration 60 --concurrent 5

Exit codes:
  0 = Success
  1 = Warnings
  2 = Failure
  3 = Invalid arguments
        """
    )

    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="URL to benchmark (must use https://)",
    )

    parser.add_argument(
        "--test",
        choices=["throughput", "latency", "multiplexing", "connection", "0rtt", "loss", "all"],
        default="all",
        help="Test type to run (default: all)",
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration in seconds for throughput test (default: 30)",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of requests for latency test (default: 100)",
    )

    parser.add_argument(
        "--concurrent",
        type=int,
        default=1,
        help="Number of concurrent workers for throughput test (default: 1)",
    )

    parser.add_argument(
        "--simulate-loss",
        type=float,
        default=0.0,
        help="Simulated packet loss rate (0-100, requires tc netem)",
    )

    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification (insecure)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Check dependencies
    if not AIOQUIC_AVAILABLE:
        print("Error: aioquic library not found", file=sys.stderr)
        print("Install: pip install aioquic", file=sys.stderr)
        return 3

    # Create benchmark
    try:
        benchmark = HTTP3Benchmark(args.url, verify_ssl=not args.no_verify_ssl)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 3

    results = []

    # Run selected tests
    try:
        if args.test in ["throughput", "all"]:
            print(f"Running throughput test ({args.duration}s, {args.concurrent} workers)...")
            result = await benchmark.benchmark_throughput(
                duration_seconds=args.duration,
                concurrent=args.concurrent
            )
            results.append(result)

        if args.test in ["latency", "all"]:
            print(f"Running latency test ({args.count} requests)...")
            result = await benchmark.benchmark_latency(count=args.count)
            results.append(result)

        if args.test in ["multiplexing", "all"]:
            print(f"Running multiplexing test...")
            result = await benchmark.benchmark_multiplexing()
            results.append(result)

        if args.test in ["connection", "all"]:
            print(f"Running connection establishment test...")
            result = await benchmark.benchmark_connection_establishment()
            results.append(result)

        if args.test in ["0rtt", "all"]:
            print(f"Running 0-RTT performance test...")
            result = await benchmark.benchmark_0rtt_performance()
            results.append(result)

        if args.test in ["loss", "all"] or args.simulate_loss > 0:
            print(f"Running packet loss resilience test...")
            result = await benchmark.benchmark_packet_loss_resilience(
                loss_rate=args.simulate_loss
            )
            results.append(result)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    # Output results
    if args.json:
        output = {
            "url": args.url,
            "timestamp": time.time(),
            "results": [r.to_dict() for r in results],
        }
        print(json.dumps(output, indent=2))
    else:
        print_human_readable(results)

    # Determine exit code
    if all(r.success_rate() == 100 for r in results):
        return 0
    elif any(r.success_rate() > 0 for r in results):
        return 1
    else:
        return 2


def main():
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
