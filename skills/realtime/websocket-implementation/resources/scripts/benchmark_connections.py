#!/usr/bin/env python3
"""
WebSocket Connection Benchmark Tool

Benchmark WebSocket servers by testing concurrent connections, throughput,
and server resource utilization under load.

Usage:
    benchmark_connections.py <url> [options]
    benchmark_connections.py wss://api.example.com/ws --connections 1000
    benchmark_connections.py ws://localhost:8080 --connections 500 --duration 60
    benchmark_connections.py wss://api.example.com/ws --ramp-up 10 --json
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, asdict
from typing import List, Optional
import websockets
from websockets.exceptions import WebSocketException


@dataclass
class ConnectionStats:
    """Statistics for a single connection"""
    id: int
    connected: bool
    connect_time_ms: float
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    error: Optional[str] = None


@dataclass
class BenchmarkResult:
    """Benchmark results"""
    url: str
    target_connections: int
    successful_connections: int
    failed_connections: int
    total_duration_s: float
    ramp_up_time_s: float

    # Connection metrics
    avg_connect_time_ms: float
    min_connect_time_ms: float
    max_connect_time_ms: float

    # Throughput metrics
    total_messages_sent: int
    total_messages_received: int
    total_bytes_sent: int
    total_bytes_received: int
    messages_per_second: float
    bytes_per_second: float

    # Per-connection stats (optional, for detailed output)
    connection_stats: Optional[List[ConnectionStats]] = None


class WebSocketBenchmark:
    """WebSocket connection benchmark utility"""

    def __init__(
        self,
        url: str,
        max_connections: int,
        duration: float = 30.0,
        ramp_up: float = 0.0,
        message_interval: float = 1.0,
        message_size: int = 100,
        verbose: bool = False
    ):
        self.url = url
        self.max_connections = max_connections
        self.duration = duration
        self.ramp_up = ramp_up
        self.message_interval = message_interval
        self.message_size = message_size
        self.verbose = verbose

        self.connections: List[ConnectionStats] = []
        self.active_connections = 0
        self.start_time = 0
        self.end_time = 0

    def log(self, message: str):
        """Log message if verbose mode enabled"""
        if self.verbose:
            elapsed = time.time() - self.start_time if self.start_time else 0
            print(f"[{elapsed:6.2f}s] {message}", file=sys.stderr)

    async def create_connection(self, conn_id: int, delay: float = 0.0) -> ConnectionStats:
        """Create and maintain a single WebSocket connection"""

        # Delay for ramp-up
        if delay > 0:
            await asyncio.sleep(delay)

        stat = ConnectionStats(
            id=conn_id,
            connected=False,
            connect_time_ms=0
        )

        connect_start = time.time()

        try:
            async with websockets.connect(self.url, timeout=10.0) as ws:
                # Record successful connection
                stat.connected = True
                stat.connect_time_ms = (time.time() - connect_start) * 1000
                self.active_connections += 1

                self.log(f"Connection {conn_id}: Connected ({stat.connect_time_ms:.2f}ms)")

                # Keep connection alive and send periodic messages
                message = "x" * self.message_size
                end_time = time.time() + self.duration

                while time.time() < end_time:
                    # Send message
                    await ws.send(message)
                    stat.messages_sent += 1
                    stat.bytes_sent += len(message)

                    # Try to receive (with timeout)
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        stat.messages_received += 1
                        stat.bytes_received += len(response)
                    except asyncio.TimeoutError:
                        pass

                    # Wait before next message
                    await asyncio.sleep(self.message_interval)

                # Clean close
                await ws.close()

        except Exception as e:
            stat.connected = False
            stat.connect_time_ms = (time.time() - connect_start) * 1000
            stat.error = str(e)
            self.log(f"Connection {conn_id}: Failed - {e}")

        finally:
            if stat.connected:
                self.active_connections -= 1

        return stat

    async def run_benchmark(self) -> BenchmarkResult:
        """Run the benchmark with specified parameters"""
        self.start_time = time.time()
        self.log(f"Starting benchmark: {self.max_connections} connections, {self.duration}s duration")

        # Calculate ramp-up delay per connection
        delay_per_connection = self.ramp_up / self.max_connections if self.ramp_up > 0 else 0

        # Create all connection tasks
        tasks = []
        for i in range(self.max_connections):
            delay = i * delay_per_connection
            task = asyncio.create_task(self.create_connection(i, delay))
            tasks.append(task)

        # Progress reporting
        if self.verbose:
            asyncio.create_task(self._progress_reporter(tasks))

        # Wait for all connections to complete
        self.connections = await asyncio.gather(*tasks)

        self.end_time = time.time()
        total_duration = self.end_time - self.start_time

        self.log(f"Benchmark complete: {total_duration:.2f}s total")

        # Generate results
        return self._generate_results(total_duration)

    async def _progress_reporter(self, tasks):
        """Report progress during benchmark"""
        total = len(tasks)

        while True:
            completed = sum(1 for t in tasks if t.done())
            active = self.active_connections

            print(
                f"\r[PROGRESS] Completed: {completed}/{total} | Active: {active} | "
                f"Elapsed: {time.time() - self.start_time:.1f}s",
                end="",
                file=sys.stderr
            )

            if completed == total:
                print(file=sys.stderr)  # New line
                break

            await asyncio.sleep(0.5)

    def _generate_results(self, total_duration: float) -> BenchmarkResult:
        """Generate benchmark results from connection stats"""

        # Count successes and failures
        successful = sum(1 for c in self.connections if c.connected)
        failed = len(self.connections) - successful

        # Connection time metrics
        connect_times = [c.connect_time_ms for c in self.connections if c.connected]
        avg_connect = sum(connect_times) / len(connect_times) if connect_times else 0
        min_connect = min(connect_times) if connect_times else 0
        max_connect = max(connect_times) if connect_times else 0

        # Throughput metrics
        total_sent = sum(c.messages_sent for c in self.connections)
        total_received = sum(c.messages_received for c in self.connections)
        total_bytes_sent = sum(c.bytes_sent for c in self.connections)
        total_bytes_received = sum(c.bytes_received for c in self.connections)

        messages_per_sec = total_sent / total_duration if total_duration > 0 else 0
        bytes_per_sec = total_bytes_sent / total_duration if total_duration > 0 else 0

        return BenchmarkResult(
            url=self.url,
            target_connections=self.max_connections,
            successful_connections=successful,
            failed_connections=failed,
            total_duration_s=total_duration,
            ramp_up_time_s=self.ramp_up,
            avg_connect_time_ms=avg_connect,
            min_connect_time_ms=min_connect,
            max_connect_time_ms=max_connect,
            total_messages_sent=total_sent,
            total_messages_received=total_received,
            total_bytes_sent=total_bytes_sent,
            total_bytes_received=total_bytes_received,
            messages_per_second=messages_per_sec,
            bytes_per_second=bytes_per_sec,
            connection_stats=None  # Don't include by default (too large)
        )


def print_results(result: BenchmarkResult, output_json: bool = False, detailed: bool = False):
    """Print benchmark results"""

    if output_json:
        # JSON output (optionally include detailed stats)
        data = asdict(result)
        if not detailed:
            data.pop('connection_stats', None)
        print(json.dumps(data, indent=2))
    else:
        # Human-readable output
        print(f"\n{'='*70}")
        print(f"WebSocket Connection Benchmark Results")
        print(f"{'='*70}")
        print(f"URL:                {result.url}")
        print(f"Target Connections: {result.target_connections}")
        print(f"Duration:           {result.total_duration_s:.2f}s")
        if result.ramp_up_time_s > 0:
            print(f"Ramp-up Time:       {result.ramp_up_time_s:.2f}s")
        print()

        # Connection success
        success_rate = (result.successful_connections / result.target_connections * 100) if result.target_connections > 0 else 0
        print(f"Connections:")
        print(f"  Successful:       {result.successful_connections} ({success_rate:.1f}%)")
        print(f"  Failed:           {result.failed_connections}")
        print()

        # Connection time
        print(f"Connection Time:")
        print(f"  Average:          {result.avg_connect_time_ms:.2f}ms")
        print(f"  Min:              {result.min_connect_time_ms:.2f}ms")
        print(f"  Max:              {result.max_connect_time_ms:.2f}ms")
        print()

        # Throughput
        print(f"Throughput:")
        print(f"  Messages Sent:    {result.total_messages_sent:,}")
        print(f"  Messages Recv:    {result.total_messages_received:,}")
        print(f"  Messages/sec:     {result.messages_per_second:.2f}")
        print(f"  Bytes Sent:       {result.total_bytes_sent:,} ({result.total_bytes_sent/1024/1024:.2f} MB)")
        print(f"  Bytes Received:   {result.total_bytes_received:,} ({result.total_bytes_received/1024/1024:.2f} MB)")
        print(f"  Bandwidth:        {result.bytes_per_second/1024/1024:.2f} MB/s")
        print(f"{'='*70}\n")


async def main():
    parser = argparse.ArgumentParser(
        description="WebSocket Connection Benchmark Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Benchmark 1000 concurrent connections
  %(prog)s wss://api.example.com/ws --connections 1000

  # Gradual ramp-up over 30 seconds
  %(prog)s ws://localhost:8080 --connections 500 --ramp-up 30

  # Long-duration stress test
  %(prog)s wss://api.example.com/ws --connections 2000 --duration 300

  # High message rate
  %(prog)s ws://localhost:8080 --connections 100 --interval 0.1

  # JSON output for analysis
  %(prog)s wss://api.example.com/ws --connections 1000 --json
        """
    )

    parser.add_argument("url", help="WebSocket URL (ws:// or wss://)")
    parser.add_argument("-c", "--connections", type=int, default=100, help="Number of concurrent connections (default: 100)")
    parser.add_argument("-d", "--duration", type=float, default=30.0, help="Test duration in seconds (default: 30)")
    parser.add_argument("-r", "--ramp-up", type=float, default=0.0, help="Ramp-up time in seconds (default: 0)")
    parser.add_argument("-i", "--interval", type=float, default=1.0, help="Message interval in seconds (default: 1)")
    parser.add_argument("-s", "--message-size", type=int, default=100, help="Message size in bytes (default: 100)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--detailed", action="store_true", help="Include per-connection details in JSON output")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Validate URL
    if not args.url.startswith(("ws://", "wss://")):
        print("Error: URL must start with ws:// or wss://", file=sys.stderr)
        sys.exit(1)

    # Validate parameters
    if args.connections < 1:
        print("Error: --connections must be at least 1", file=sys.stderr)
        sys.exit(1)

    if args.duration < 1:
        print("Error: --duration must be at least 1 second", file=sys.stderr)
        sys.exit(1)

    # Create benchmark
    benchmark = WebSocketBenchmark(
        url=args.url,
        max_connections=args.connections,
        duration=args.duration,
        ramp_up=args.ramp_up,
        message_interval=args.interval,
        message_size=args.message_size,
        verbose=args.verbose
    )

    try:
        # Run benchmark
        result = await benchmark.run_benchmark()

        # Add detailed stats if requested
        if args.detailed:
            result.connection_stats = benchmark.connections

        # Print results
        print_results(result, output_json=args.json, detailed=args.detailed)

        # Exit code based on success rate
        success_rate = result.successful_connections / result.target_connections
        sys.exit(0 if success_rate >= 0.95 else 1)

    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
