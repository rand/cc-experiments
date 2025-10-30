#!/usr/bin/env python3
"""
PyO3 Web Frameworks WebSocket Tester

Comprehensive WebSocket testing tool for FastAPI, Flask, and Django applications
with PyO3 extensions. Tests connection stability, message throughput, stress testing,
and performance metrics.

Features:
- WebSocket connection testing
- Message sending/receiving with various payloads
- Stress testing with concurrent connections
- Connection pooling and reuse
- Performance metrics (latency, throughput, error rates)
- Binary and text message support
- Ping/pong monitoring
- JSON and text output formats

Usage:
    ./websocket_tester.py connect ws://localhost:8000/ws
    ./websocket_tester.py send ws://localhost:8000/ws --message '{"type": "hello"}'
    ./websocket_tester.py stress-test ws://localhost:8000/ws --connections 100 --duration 60
    ./websocket_tester.py monitor ws://localhost:8000/ws --duration 300
"""

import argparse
import json
import sys
import time
import asyncio
import websockets
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import statistics
from concurrent.futures import ThreadPoolExecutor
import threading


@dataclass
class MessageResult:
    """Single message result"""
    message_id: int
    sent_at: float
    received_at: Optional[float]
    latency_ms: Optional[float]
    message_type: str
    size_bytes: int
    success: bool
    error: Optional[str] = None


@dataclass
class ConnectionStats:
    """Connection statistics"""
    total_messages: int
    successful_messages: int
    failed_messages: int
    success_rate: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    messages_per_second: float
    bytes_sent: int
    bytes_received: int


@dataclass
class StressTestResult:
    """Stress test results"""
    endpoint: str
    total_connections: int
    successful_connections: int
    failed_connections: int
    duration_s: float
    total_messages: int
    messages_per_second: float
    connection_stats: ConnectionStats
    connection_errors: List[str] = field(default_factory=list)


class WebSocketConnection:
    """Manage WebSocket connection"""

    def __init__(
        self,
        url: str,
        timeout: int = 30,
        ping_interval: Optional[int] = 20,
        ping_timeout: Optional[int] = 10
    ):
        self.url = url
        self.timeout = timeout
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.websocket = None
        self.connected = False
        self.message_id = 0
        self.results: List[MessageResult] = []

    async def connect(self) -> bool:
        """Establish WebSocket connection"""
        try:
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout
                ),
                timeout=self.timeout
            )
            self.connected = True
            return True
        except Exception as e:
            self.connected = False
            return False

    async def send_message(
        self,
        message: str,
        message_type: str = "text"
    ) -> MessageResult:
        """Send message and wait for response"""
        if not self.connected or not self.websocket:
            return MessageResult(
                message_id=self.message_id,
                sent_at=time.time(),
                received_at=None,
                latency_ms=None,
                message_type=message_type,
                size_bytes=len(message.encode()),
                success=False,
                error="Not connected"
            )

        self.message_id += 1
        sent_at = time.time()

        try:
            # Send message
            if message_type == "binary":
                await self.websocket.send(message.encode())
            else:
                await self.websocket.send(message)

            # Wait for response
            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=self.timeout
            )

            received_at = time.time()
            latency_ms = (received_at - sent_at) * 1000

            result = MessageResult(
                message_id=self.message_id,
                sent_at=sent_at,
                received_at=received_at,
                latency_ms=latency_ms,
                message_type=message_type,
                size_bytes=len(message.encode()),
                success=True
            )

            self.results.append(result)
            return result

        except asyncio.TimeoutError:
            return MessageResult(
                message_id=self.message_id,
                sent_at=sent_at,
                received_at=None,
                latency_ms=None,
                message_type=message_type,
                size_bytes=len(message.encode()),
                success=False,
                error="Timeout waiting for response"
            )
        except Exception as e:
            return MessageResult(
                message_id=self.message_id,
                sent_at=sent_at,
                received_at=None,
                latency_ms=None,
                message_type=message_type,
                size_bytes=len(message.encode()),
                success=False,
                error=str(e)
            )

    async def send_messages_batch(
        self,
        messages: List[str],
        message_type: str = "text"
    ) -> List[MessageResult]:
        """Send multiple messages"""
        results = []
        for message in messages:
            result = await self.send_message(message, message_type)
            results.append(result)
        return results

    async def close(self) -> None:
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False

    def get_stats(self) -> ConnectionStats:
        """Calculate connection statistics"""
        if not self.results:
            return ConnectionStats(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0)

        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful
        success_rate = successful / total if total > 0 else 0.0

        # Latency stats
        latencies = [r.latency_ms for r in self.results if r.latency_ms is not None]

        if latencies:
            latencies_sorted = sorted(latencies)
            n = len(latencies_sorted)
            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)

            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            p95_latency = latencies_sorted[p95_idx]
            p99_latency = latencies_sorted[p99_idx]
        else:
            avg_latency = min_latency = max_latency = p95_latency = p99_latency = 0.0

        # Throughput stats
        if self.results:
            duration = self.results[-1].sent_at - self.results[0].sent_at
            mps = total / duration if duration > 0 else 0.0
        else:
            mps = 0.0

        # Size stats
        bytes_sent = sum(r.size_bytes for r in self.results)
        bytes_received = sum(r.size_bytes for r in self.results if r.success)

        return ConnectionStats(
            total_messages=total,
            successful_messages=successful,
            failed_messages=failed,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            messages_per_second=mps,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received
        )


class WebSocketTester:
    """Test WebSocket endpoints"""

    def __init__(self, url: str, timeout: int = 30):
        self.url = url
        self.timeout = timeout

    async def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test basic connection"""
        connection = WebSocketConnection(self.url, self.timeout)

        try:
            connected = await connection.connect()
            if connected:
                await connection.close()
                return True, None
            else:
                return False, "Connection failed"
        except Exception as e:
            return False, str(e)

    async def test_echo(self, message: str) -> Tuple[bool, Optional[str], Optional[float]]:
        """Test echo with single message"""
        connection = WebSocketConnection(self.url, self.timeout)

        try:
            connected = await connection.connect()
            if not connected:
                return False, "Connection failed", None

            result = await connection.send_message(message)
            await connection.close()

            if result.success:
                return True, None, result.latency_ms
            else:
                return False, result.error, None

        except Exception as e:
            return False, str(e), None

    async def stress_test(
        self,
        num_connections: int,
        duration_s: int,
        messages_per_connection: int = 100
    ) -> StressTestResult:
        """Run stress test with multiple connections"""
        start_time = time.time()
        end_time = start_time + duration_s

        # Create connections
        connections: List[WebSocketConnection] = []
        connection_errors: List[str] = []

        print(f"Establishing {num_connections} connections...")

        for i in range(num_connections):
            connection = WebSocketConnection(self.url, self.timeout)
            try:
                connected = await connection.connect()
                if connected:
                    connections.append(connection)
                else:
                    connection_errors.append(f"Connection {i}: failed to connect")
            except Exception as e:
                connection_errors.append(f"Connection {i}: {str(e)}")

        successful_connections = len(connections)
        failed_connections = num_connections - successful_connections

        print(f"Connected: {successful_connections}/{num_connections}")

        # Send messages
        print(f"Sending messages for {duration_s}s...")

        tasks = []
        for connection in connections:
            task = self._send_messages_until_time(
                connection,
                end_time,
                messages_per_connection
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Close connections
        for connection in connections:
            await connection.close()

        # Calculate statistics
        all_results = []
        for connection in connections:
            all_results.extend(connection.results)

        duration = time.time() - start_time
        total_messages = len(all_results)
        mps = total_messages / duration if duration > 0 else 0.0

        # Calculate aggregate stats
        if connections:
            stats_list = [conn.get_stats() for conn in connections]
            aggregate_stats = self._aggregate_stats(stats_list)
        else:
            aggregate_stats = ConnectionStats(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0)

        return StressTestResult(
            endpoint=self.url,
            total_connections=num_connections,
            successful_connections=successful_connections,
            failed_connections=failed_connections,
            duration_s=duration,
            total_messages=total_messages,
            messages_per_second=mps,
            connection_stats=aggregate_stats,
            connection_errors=connection_errors
        )

    async def _send_messages_until_time(
        self,
        connection: WebSocketConnection,
        end_time: float,
        batch_size: int
    ) -> None:
        """Send messages until time limit"""
        message_template = '{"type": "test", "timestamp": %d, "data": "x" * 100}'

        while time.time() < end_time:
            timestamp = int(time.time())
            message = message_template % timestamp
            await connection.send_message(message)
            await asyncio.sleep(0.01)  # Small delay between messages

    def _aggregate_stats(self, stats_list: List[ConnectionStats]) -> ConnectionStats:
        """Aggregate statistics from multiple connections"""
        if not stats_list:
            return ConnectionStats(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0)

        total_messages = sum(s.total_messages for s in stats_list)
        successful_messages = sum(s.successful_messages for s in stats_list)
        failed_messages = sum(s.failed_messages for s in stats_list)
        success_rate = successful_messages / total_messages if total_messages > 0 else 0.0

        # Weighted average for latencies
        latencies = []
        for stats in stats_list:
            if stats.avg_latency_ms > 0:
                latencies.append(stats.avg_latency_ms)

        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(s.min_latency_ms for s in stats_list if s.min_latency_ms > 0)
            max_latency = max(s.max_latency_ms for s in stats_list)
            p95_latency = statistics.mean(s.p95_latency_ms for s in stats_list if s.p95_latency_ms > 0)
            p99_latency = statistics.mean(s.p99_latency_ms for s in stats_list if s.p99_latency_ms > 0)
        else:
            avg_latency = min_latency = max_latency = p95_latency = p99_latency = 0.0

        messages_per_second = sum(s.messages_per_second for s in stats_list)
        bytes_sent = sum(s.bytes_sent for s in stats_list)
        bytes_received = sum(s.bytes_received for s in stats_list)

        return ConnectionStats(
            total_messages=total_messages,
            successful_messages=successful_messages,
            failed_messages=failed_messages,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            messages_per_second=messages_per_second,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received
        )

    async def monitor(self, duration_s: int, interval_s: int = 5) -> List[ConnectionStats]:
        """Monitor WebSocket connection over time"""
        connection = WebSocketConnection(self.url, self.timeout)

        connected = await connection.connect()
        if not connected:
            raise RuntimeError("Failed to connect")

        stats_history = []
        start_time = time.time()
        end_time = start_time + duration_s

        print(f"Monitoring for {duration_s}s (reporting every {interval_s}s)...")

        try:
            while time.time() < end_time:
                # Send test message
                message = f'{{"type": "ping", "timestamp": {int(time.time())}}}'
                await connection.send_message(message)

                # Wait for interval
                await asyncio.sleep(interval_s)

                # Record stats
                stats = connection.get_stats()
                stats_history.append(stats)

                # Print current stats
                print(f"[{len(stats_history) * interval_s}s] "
                      f"Messages: {stats.total_messages}, "
                      f"Avg Latency: {stats.avg_latency_ms:.2f}ms, "
                      f"Success Rate: {stats.success_rate:.1%}")

        finally:
            await connection.close()

        return stats_history


class ResultFormatter:
    """Format test results"""

    def format_connection_test(
        self,
        success: bool,
        error: Optional[str]
    ) -> str:
        """Format connection test result"""
        if success:
            return "✓ Connection successful"
        else:
            return f"✗ Connection failed: {error}"

    def format_echo_test(
        self,
        success: bool,
        error: Optional[str],
        latency_ms: Optional[float]
    ) -> str:
        """Format echo test result"""
        if success:
            return f"✓ Echo successful (latency: {latency_ms:.2f}ms)"
        else:
            return f"✗ Echo failed: {error}"

    def format_stress_test(self, result: StressTestResult) -> str:
        """Format stress test result"""
        lines = [
            "=" * 80,
            "WEBSOCKET STRESS TEST RESULTS",
            "=" * 80,
            "",
            f"Endpoint:             {result.endpoint}",
            f"Total Connections:    {result.total_connections}",
            f"Successful:           {result.successful_connections}",
            f"Failed:               {result.failed_connections}",
            f"Duration:             {result.duration_s:.2f}s",
            f"Total Messages:       {result.total_messages}",
            f"Messages/sec:         {result.messages_per_second:.2f}",
            "",
            "MESSAGE STATISTICS",
            "-" * 80,
            f"Successful:           {result.connection_stats.successful_messages}",
            f"Failed:               {result.connection_stats.failed_messages}",
            f"Success Rate:         {result.connection_stats.success_rate:.1%}",
            "",
            "LATENCY STATISTICS",
            "-" * 80,
            f"Min:                  {result.connection_stats.min_latency_ms:.2f}ms",
            f"Max:                  {result.connection_stats.max_latency_ms:.2f}ms",
            f"Average:              {result.connection_stats.avg_latency_ms:.2f}ms",
            f"P95:                  {result.connection_stats.p95_latency_ms:.2f}ms",
            f"P99:                  {result.connection_stats.p99_latency_ms:.2f}ms",
            "",
            "BANDWIDTH",
            "-" * 80,
            f"Bytes Sent:           {result.connection_stats.bytes_sent:,}",
            f"Bytes Received:       {result.connection_stats.bytes_received:,}",
            "=" * 80
        ]

        if result.connection_errors:
            lines.extend([
                "",
                "CONNECTION ERRORS",
                "-" * 80
            ])
            for error in result.connection_errors[:10]:  # Show first 10 errors
                lines.append(f"  {error}")

            if len(result.connection_errors) > 10:
                lines.append(f"  ... and {len(result.connection_errors) - 10} more")

        return "\n".join(lines)

    def format_json(self, data: Any) -> str:
        """Format result as JSON"""
        if hasattr(data, '__dict__'):
            return json.dumps(asdict(data), indent=2)
        else:
            return json.dumps(data, indent=2)


async def cmd_connect(args: argparse.Namespace) -> int:
    """Test WebSocket connection"""
    tester = WebSocketTester(args.url, args.timeout)
    formatter = ResultFormatter()

    success, error = await tester.test_connection()

    if args.json:
        result = {"success": success, "error": error}
        print(json.dumps(result))
    else:
        print(formatter.format_connection_test(success, error))

    return 0 if success else 1


async def cmd_send(args: argparse.Namespace) -> int:
    """Send message and test echo"""
    tester = WebSocketTester(args.url, args.timeout)
    formatter = ResultFormatter()

    # Load message from file if specified
    if args.message_file:
        with open(args.message_file, 'r') as f:
            message = f.read()
    else:
        message = args.message

    success, error, latency_ms = await tester.test_echo(message)

    if args.json:
        result = {
            "success": success,
            "error": error,
            "latency_ms": latency_ms
        }
        print(json.dumps(result))
    else:
        print(formatter.format_echo_test(success, error, latency_ms))

    return 0 if success else 1


async def cmd_stress_test(args: argparse.Namespace) -> int:
    """Run stress test"""
    tester = WebSocketTester(args.url, args.timeout)
    formatter = ResultFormatter()

    result = await tester.stress_test(
        num_connections=args.connections,
        duration_s=args.duration,
        messages_per_connection=args.messages
    )

    if args.json:
        print(formatter.format_json(result))
    else:
        print(formatter.format_stress_test(result))

    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(formatter.format_json(result))
        print(f"\nResults saved to: {args.output}")

    return 0


async def cmd_monitor(args: argparse.Namespace) -> int:
    """Monitor WebSocket connection"""
    tester = WebSocketTester(args.url, args.timeout)

    try:
        stats_history = await tester.monitor(
            duration_s=args.duration,
            interval_s=args.interval
        )

        print("\nMonitoring Summary:")
        print("=" * 80)

        if stats_history:
            final_stats = stats_history[-1]
            print(f"Total Messages:       {final_stats.total_messages}")
            print(f"Success Rate:         {final_stats.success_rate:.1%}")
            print(f"Average Latency:      {final_stats.avg_latency_ms:.2f}ms")
            print(f"P95 Latency:          {final_stats.p95_latency_ms:.2f}ms")
            print(f"Messages/sec:         {final_stats.messages_per_second:.2f}")

        # Save to file if requested
        if args.output:
            data = [asdict(s) for s in stats_history]
            with open(args.output, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\nResults saved to: {args.output}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test WebSocket endpoints for PyO3 web frameworks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Connect command
    connect_parser = subparsers.add_parser(
        'connect',
        help='Test WebSocket connection'
    )
    connect_parser.add_argument(
        'url',
        help='WebSocket URL (e.g., ws://localhost:8000/ws)'
    )
    connect_parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Connection timeout in seconds (default: 30)'
    )
    connect_parser.add_argument(
        '--json',
        action='store_true',
        help='Output result as JSON'
    )

    # Send command
    send_parser = subparsers.add_parser(
        'send',
        help='Send message and test echo'
    )
    send_parser.add_argument(
        'url',
        help='WebSocket URL'
    )
    send_parser.add_argument(
        '--message', '-m',
        help='Message to send'
    )
    send_parser.add_argument(
        '--message-file', '-f',
        help='Read message from file'
    )
    send_parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Timeout in seconds (default: 30)'
    )
    send_parser.add_argument(
        '--json',
        action='store_true',
        help='Output result as JSON'
    )

    # Stress test command
    stress_parser = subparsers.add_parser(
        'stress-test',
        help='Run stress test with multiple connections'
    )
    stress_parser.add_argument(
        'url',
        help='WebSocket URL'
    )
    stress_parser.add_argument(
        '--connections', '-c',
        type=int,
        default=10,
        help='Number of concurrent connections (default: 10)'
    )
    stress_parser.add_argument(
        '--duration', '-t',
        type=int,
        default=60,
        help='Test duration in seconds (default: 60)'
    )
    stress_parser.add_argument(
        '--messages', '-m',
        type=int,
        default=100,
        help='Messages per connection (default: 100)'
    )
    stress_parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Connection timeout in seconds (default: 30)'
    )
    stress_parser.add_argument(
        '--output', '-o',
        help='Save results to JSON file'
    )
    stress_parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    # Monitor command
    monitor_parser = subparsers.add_parser(
        'monitor',
        help='Monitor WebSocket connection over time'
    )
    monitor_parser.add_argument(
        'url',
        help='WebSocket URL'
    )
    monitor_parser.add_argument(
        '--duration', '-t',
        type=int,
        default=300,
        help='Monitoring duration in seconds (default: 300)'
    )
    monitor_parser.add_argument(
        '--interval', '-i',
        type=int,
        default=5,
        help='Reporting interval in seconds (default: 5)'
    )
    monitor_parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Connection timeout in seconds (default: 30)'
    )
    monitor_parser.add_argument(
        '--output', '-o',
        help='Save results to JSON file'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'connect':
            return asyncio.run(cmd_connect(args))
        elif args.command == 'send':
            if not args.message and not args.message_file:
                print("Error: Either --message or --message-file is required", file=sys.stderr)
                return 1
            return asyncio.run(cmd_send(args))
        elif args.command == 'stress-test':
            return asyncio.run(cmd_stress_test(args))
        elif args.command == 'monitor':
            return asyncio.run(cmd_monitor(args))
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
