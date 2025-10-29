#!/usr/bin/env python3
"""
WebSocket Server Tester

Comprehensive testing tool for WebSocket servers including connection tests,
round-trip latency, protocol compliance, and failover testing.

Usage:
    ./test_websocket_server.py --url ws://localhost:8080 --test-all
    ./test_websocket_server.py --url wss://example.com/ws --test connection
    ./test_websocket_server.py --url ws://localhost:8080 --test latency --duration 30
    ./test_websocket_server.py --url ws://localhost:8080 --test-all --json
    ./test_websocket_server.py --help

Requirements:
    pip install websockets aiohttp
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from statistics import mean, median, stdev
from urllib.parse import urlparse
import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedOK,
    ConnectionClosedError,
    InvalidHandshake,
    InvalidStatusCode
)


@dataclass
class TestResult:
    """Result of a single test"""
    test_name: str
    status: str  # pass, fail, skip
    duration_ms: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TestSuite:
    """Collection of test results"""
    server_url: str
    timestamp: float
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total_duration_ms: float = 0.0
    results: List[TestResult] = field(default_factory=list)


class WebSocketTester:
    """WebSocket server testing framework"""

    def __init__(self, url: str, verbose: bool = False, timeout: int = 10):
        self.url = url
        self.verbose = verbose
        self.timeout = timeout
        self.suite = TestSuite(server_url=url, timestamp=time.time())

    def add_result(self, result: TestResult):
        """Add test result to suite"""
        self.suite.results.append(result)
        self.suite.total_tests += 1
        self.suite.total_duration_ms += result.duration_ms

        if result.status == "pass":
            self.suite.passed += 1
        elif result.status == "fail":
            self.suite.failed += 1
        else:
            self.suite.skipped += 1

        if self.verbose:
            status_symbol = "✓" if result.status == "pass" else "✗" if result.status == "fail" else "○"
            print(f"{status_symbol} {result.test_name}: {result.message} ({result.duration_ms:.2f}ms)")

    async def test_connection(self) -> TestResult:
        """Test basic connection establishment"""
        start = time.time()

        try:
            async with websockets.connect(self.url, open_timeout=self.timeout) as websocket:
                duration_ms = (time.time() - start) * 1000

                return TestResult(
                    test_name="connection",
                    status="pass",
                    duration_ms=duration_ms,
                    message="Successfully connected to WebSocket server",
                    details={
                        "remote_address": websocket.remote_address,
                        "local_address": websocket.local_address,
                        "subprotocol": websocket.subprotocol
                    }
                )

        except InvalidHandshake as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="connection",
                status="fail",
                duration_ms=duration_ms,
                message="Handshake failed",
                error=str(e)
            )

        except InvalidStatusCode as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="connection",
                status="fail",
                duration_ms=duration_ms,
                message=f"Invalid status code: {e.status_code}",
                error=str(e)
            )

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="connection",
                status="fail",
                duration_ms=duration_ms,
                message="Connection timeout",
                error=f"Failed to connect within {self.timeout} seconds"
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="connection",
                status="fail",
                duration_ms=duration_ms,
                message="Connection failed",
                error=str(e)
            )

    async def test_echo(self) -> TestResult:
        """Test echo functionality"""
        start = time.time()
        test_message = "Hello, WebSocket!"

        try:
            async with websockets.connect(self.url, open_timeout=self.timeout) as websocket:
                # Send message
                await websocket.send(test_message)

                # Receive response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)

                duration_ms = (time.time() - start) * 1000

                # Check if echo matches
                if response == test_message or test_message in response:
                    return TestResult(
                        test_name="echo",
                        status="pass",
                        duration_ms=duration_ms,
                        message="Echo test successful",
                        details={
                            "sent": test_message,
                            "received": response
                        }
                    )
                else:
                    return TestResult(
                        test_name="echo",
                        status="fail",
                        duration_ms=duration_ms,
                        message="Echo mismatch",
                        details={
                            "sent": test_message,
                            "received": response
                        }
                    )

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="echo",
                status="fail",
                duration_ms=duration_ms,
                message="No response received",
                error="Timeout waiting for echo response"
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="echo",
                status="fail",
                duration_ms=duration_ms,
                message="Echo test failed",
                error=str(e)
            )

    async def test_json_message(self) -> TestResult:
        """Test JSON message handling"""
        start = time.time()
        test_data = {"type": "ping", "timestamp": time.time()}

        try:
            async with websockets.connect(self.url, open_timeout=self.timeout) as websocket:
                # Send JSON message
                await websocket.send(json.dumps(test_data))

                # Receive response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)

                duration_ms = (time.time() - start) * 1000

                # Try to parse response as JSON
                try:
                    response_data = json.loads(response)
                    return TestResult(
                        test_name="json_message",
                        status="pass",
                        duration_ms=duration_ms,
                        message="JSON message handling successful",
                        details={
                            "sent": test_data,
                            "received": response_data
                        }
                    )
                except json.JSONDecodeError:
                    return TestResult(
                        test_name="json_message",
                        status="fail",
                        duration_ms=duration_ms,
                        message="Response is not valid JSON",
                        details={
                            "sent": test_data,
                            "received": response
                        }
                    )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="json_message",
                status="fail",
                duration_ms=duration_ms,
                message="JSON message test failed",
                error=str(e)
            )

    async def test_binary_message(self) -> TestResult:
        """Test binary message handling"""
        start = time.time()
        test_data = b"\x00\x01\x02\x03\x04\x05"

        try:
            async with websockets.connect(self.url, open_timeout=self.timeout) as websocket:
                # Send binary message
                await websocket.send(test_data)

                # Receive response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)

                duration_ms = (time.time() - start) * 1000

                if isinstance(response, bytes):
                    return TestResult(
                        test_name="binary_message",
                        status="pass",
                        duration_ms=duration_ms,
                        message="Binary message handling successful",
                        details={
                            "sent_bytes": len(test_data),
                            "received_bytes": len(response)
                        }
                    )
                else:
                    return TestResult(
                        test_name="binary_message",
                        status="fail",
                        duration_ms=duration_ms,
                        message="Expected binary response, got text",
                        details={
                            "response_type": type(response).__name__
                        }
                    )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="binary_message",
                status="fail",
                duration_ms=duration_ms,
                message="Binary message test failed",
                error=str(e)
            )

    async def test_ping_pong(self) -> TestResult:
        """Test protocol-level ping/pong"""
        start = time.time()

        try:
            async with websockets.connect(self.url, open_timeout=self.timeout) as websocket:
                # Send ping
                pong_waiter = await websocket.ping()

                # Wait for pong
                await asyncio.wait_for(pong_waiter, timeout=5.0)

                duration_ms = (time.time() - start) * 1000

                return TestResult(
                    test_name="ping_pong",
                    status="pass",
                    duration_ms=duration_ms,
                    message="Ping/pong successful",
                    details={
                        "latency_ms": duration_ms
                    }
                )

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="ping_pong",
                status="fail",
                duration_ms=duration_ms,
                message="No pong response",
                error="Timeout waiting for pong"
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="ping_pong",
                status="fail",
                duration_ms=duration_ms,
                message="Ping/pong failed",
                error=str(e)
            )

    async def test_close_handshake(self) -> TestResult:
        """Test graceful close handshake"""
        start = time.time()

        try:
            websocket = await websockets.connect(self.url, open_timeout=self.timeout)

            # Send close frame
            await websocket.close(code=1000, reason="Normal closure")

            # Wait for close
            await asyncio.wait_for(websocket.wait_closed(), timeout=5.0)

            duration_ms = (time.time() - start) * 1000

            return TestResult(
                test_name="close_handshake",
                status="pass",
                duration_ms=duration_ms,
                message="Graceful close successful",
                details={
                    "close_code": 1000,
                    "close_reason": "Normal closure"
                }
            )

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="close_handshake",
                status="fail",
                duration_ms=duration_ms,
                message="Close handshake timeout",
                error="Server did not complete close handshake"
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="close_handshake",
                status="fail",
                duration_ms=duration_ms,
                message="Close handshake failed",
                error=str(e)
            )

    async def test_large_message(self) -> TestResult:
        """Test handling of large messages"""
        start = time.time()
        # 1 MB message
        test_data = "x" * (1024 * 1024)

        try:
            async with websockets.connect(
                self.url,
                open_timeout=self.timeout,
                max_size=10 * 1024 * 1024  # 10 MB max
            ) as websocket:
                # Send large message
                await websocket.send(test_data)

                # Receive response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)

                duration_ms = (time.time() - start) * 1000

                return TestResult(
                    test_name="large_message",
                    status="pass",
                    duration_ms=duration_ms,
                    message="Large message handling successful",
                    details={
                        "message_size_bytes": len(test_data),
                        "throughput_mbps": (len(test_data) * 8 / 1024 / 1024) / (duration_ms / 1000)
                    }
                )

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="large_message",
                status="fail",
                duration_ms=duration_ms,
                message="Large message timeout",
                error="Server did not respond to large message"
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="large_message",
                status="fail",
                duration_ms=duration_ms,
                message="Large message test failed",
                error=str(e)
            )

    async def test_rapid_messages(self) -> TestResult:
        """Test rapid message sending"""
        start = time.time()
        num_messages = 100
        sent = 0
        received = 0

        try:
            async with websockets.connect(self.url, open_timeout=self.timeout) as websocket:
                # Send rapid messages
                for i in range(num_messages):
                    await websocket.send(f"Message {i}")
                    sent += 1

                # Receive responses (with timeout)
                try:
                    for i in range(num_messages):
                        response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        received += 1
                except asyncio.TimeoutError:
                    pass  # Stop receiving after timeout

                duration_ms = (time.time() - start) * 1000
                messages_per_sec = num_messages / (duration_ms / 1000)

                if received >= num_messages * 0.9:  # 90% success rate
                    return TestResult(
                        test_name="rapid_messages",
                        status="pass",
                        duration_ms=duration_ms,
                        message="Rapid message handling successful",
                        details={
                            "sent": sent,
                            "received": received,
                            "messages_per_sec": messages_per_sec
                        }
                    )
                else:
                    return TestResult(
                        test_name="rapid_messages",
                        status="fail",
                        duration_ms=duration_ms,
                        message="Message loss detected",
                        details={
                            "sent": sent,
                            "received": received,
                            "loss_rate": (sent - received) / sent * 100
                        }
                    )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="rapid_messages",
                status="fail",
                duration_ms=duration_ms,
                message="Rapid message test failed",
                error=str(e)
            )

    async def test_latency(self, duration: int = 30) -> TestResult:
        """Measure round-trip latency over time"""
        start = time.time()
        latencies: List[float] = []

        try:
            async with websockets.connect(self.url, open_timeout=self.timeout) as websocket:
                test_start = time.time()

                while time.time() - test_start < duration:
                    # Send ping
                    ping_start = time.time()
                    await websocket.send(json.dumps({"type": "ping"}))

                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        ping_end = time.time()

                        latency_ms = (ping_end - ping_start) * 1000
                        latencies.append(latency_ms)

                        await asyncio.sleep(0.1)  # Small delay between pings

                    except asyncio.TimeoutError:
                        break

                duration_ms = (time.time() - start) * 1000

                if latencies:
                    return TestResult(
                        test_name="latency",
                        status="pass",
                        duration_ms=duration_ms,
                        message="Latency measurement complete",
                        details={
                            "samples": len(latencies),
                            "mean_ms": mean(latencies),
                            "median_ms": median(latencies),
                            "min_ms": min(latencies),
                            "max_ms": max(latencies),
                            "stddev_ms": stdev(latencies) if len(latencies) > 1 else 0,
                            "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else None,
                            "p99_ms": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 100 else None
                        }
                    )
                else:
                    return TestResult(
                        test_name="latency",
                        status="fail",
                        duration_ms=duration_ms,
                        message="No latency samples collected",
                        error="Server did not respond to ping messages"
                    )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="latency",
                status="fail",
                duration_ms=duration_ms,
                message="Latency test failed",
                error=str(e)
            )

    async def test_reconnection(self) -> TestResult:
        """Test reconnection after disconnect"""
        start = time.time()

        try:
            # First connection
            websocket1 = await websockets.connect(self.url, open_timeout=self.timeout)
            await websocket1.send("Connection 1")
            await websocket1.close()

            # Wait briefly
            await asyncio.sleep(0.5)

            # Second connection
            websocket2 = await websockets.connect(self.url, open_timeout=self.timeout)
            await websocket2.send("Connection 2")
            response = await asyncio.wait_for(websocket2.recv(), timeout=5.0)
            await websocket2.close()

            duration_ms = (time.time() - start) * 1000

            return TestResult(
                test_name="reconnection",
                status="pass",
                duration_ms=duration_ms,
                message="Reconnection successful",
                details={
                    "received_after_reconnect": response
                }
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="reconnection",
                status="fail",
                duration_ms=duration_ms,
                message="Reconnection failed",
                error=str(e)
            )

    async def test_concurrent_connections(self, num_connections: int = 10) -> TestResult:
        """Test multiple concurrent connections"""
        start = time.time()

        async def single_connection(conn_id: int) -> bool:
            try:
                async with websockets.connect(self.url, open_timeout=self.timeout) as ws:
                    await ws.send(f"Connection {conn_id}")
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    return True
            except Exception:
                return False

        try:
            # Create concurrent connections
            tasks = [single_connection(i) for i in range(num_connections)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = sum(1 for r in results if r is True)
            duration_ms = (time.time() - start) * 1000

            if successful >= num_connections * 0.9:  # 90% success
                return TestResult(
                    test_name="concurrent_connections",
                    status="pass",
                    duration_ms=duration_ms,
                    message="Concurrent connections handled successfully",
                    details={
                        "total_connections": num_connections,
                        "successful": successful,
                        "failed": num_connections - successful
                    }
                )
            else:
                return TestResult(
                    test_name="concurrent_connections",
                    status="fail",
                    duration_ms=duration_ms,
                    message="Too many concurrent connection failures",
                    details={
                        "total_connections": num_connections,
                        "successful": successful,
                        "failed": num_connections - successful,
                        "success_rate": successful / num_connections * 100
                    }
                )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="concurrent_connections",
                status="fail",
                duration_ms=duration_ms,
                message="Concurrent connection test failed",
                error=str(e)
            )

    async def test_tls_connection(self) -> TestResult:
        """Test TLS/SSL connection (wss://)"""
        start = time.time()

        parsed = urlparse(self.url)
        if parsed.scheme != "wss":
            return TestResult(
                test_name="tls_connection",
                status="skip",
                duration_ms=0,
                message="Skipped (not using wss://)",
                details={
                    "url_scheme": parsed.scheme
                }
            )

        try:
            async with websockets.connect(self.url, open_timeout=self.timeout) as websocket:
                duration_ms = (time.time() - start) * 1000

                return TestResult(
                    test_name="tls_connection",
                    status="pass",
                    duration_ms=duration_ms,
                    message="TLS connection successful",
                    details={
                        "url": self.url
                    }
                )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                test_name="tls_connection",
                status="fail",
                duration_ms=duration_ms,
                message="TLS connection failed",
                error=str(e)
            )

    async def run_all_tests(self, latency_duration: int = 30) -> TestSuite:
        """Run all tests"""
        tests = [
            ("connection", self.test_connection()),
            ("echo", self.test_echo()),
            ("json_message", self.test_json_message()),
            ("binary_message", self.test_binary_message()),
            ("ping_pong", self.test_ping_pong()),
            ("close_handshake", self.test_close_handshake()),
            ("large_message", self.test_large_message()),
            ("rapid_messages", self.test_rapid_messages()),
            ("latency", self.test_latency(duration=latency_duration)),
            ("reconnection", self.test_reconnection()),
            ("concurrent_connections", self.test_concurrent_connections()),
            ("tls_connection", self.test_tls_connection())
        ]

        for test_name, test_coro in tests:
            if self.verbose:
                print(f"\nRunning test: {test_name}")

            result = await test_coro
            self.add_result(result)

        return self.suite

    async def run_specific_test(self, test_name: str, **kwargs) -> TestSuite:
        """Run specific test"""
        test_map = {
            "connection": self.test_connection,
            "echo": self.test_echo,
            "json": self.test_json_message,
            "binary": self.test_binary_message,
            "ping": self.test_ping_pong,
            "close": self.test_close_handshake,
            "large": self.test_large_message,
            "rapid": self.test_rapid_messages,
            "latency": self.test_latency,
            "reconnection": self.test_reconnection,
            "concurrent": self.test_concurrent_connections,
            "tls": self.test_tls_connection
        }

        if test_name not in test_map:
            print(f"Error: Unknown test '{test_name}'", file=sys.stderr)
            print(f"Available tests: {', '.join(test_map.keys())}", file=sys.stderr)
            sys.exit(1)

        test_func = test_map[test_name]

        # Call with kwargs if applicable
        if test_name == "latency" and "duration" in kwargs:
            result = await test_func(duration=kwargs["duration"])
        elif test_name == "concurrent" and "connections" in kwargs:
            result = await test_func(num_connections=kwargs["connections"])
        else:
            result = await test_func()

        self.add_result(result)
        return self.suite


def format_output(suite: TestSuite, output_format: str = "text") -> str:
    """Format test suite results"""
    if output_format == "json":
        return json.dumps(asdict(suite), indent=2)

    # Text output
    lines = []
    lines.append(f"\n{'='*70}")
    lines.append(f"WebSocket Server Test Results")
    lines.append(f"{'='*70}")
    lines.append(f"Server URL: {suite.server_url}")
    lines.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(suite.timestamp))}")
    lines.append(f"")
    lines.append(f"Summary:")
    lines.append(f"  Total Tests: {suite.total_tests}")
    lines.append(f"  Passed: {suite.passed}")
    lines.append(f"  Failed: {suite.failed}")
    lines.append(f"  Skipped: {suite.skipped}")
    lines.append(f"  Total Duration: {suite.total_duration_ms:.2f}ms")

    if suite.results:
        lines.append(f"\n{'='*70}")
        lines.append(f"Detailed Results")
        lines.append(f"{'='*70}\n")

        for result in suite.results:
            status_symbol = "✓" if result.status == "pass" else "✗" if result.status == "fail" else "○"
            lines.append(f"\n{status_symbol} {result.test_name.upper()} ({result.duration_ms:.2f}ms)")
            lines.append(f"  Status: {result.status.upper()}")
            lines.append(f"  {result.message}")

            if result.error:
                lines.append(f"  Error: {result.error}")

            if result.details:
                lines.append(f"  Details:")
                for key, value in result.details.items():
                    if isinstance(value, float):
                        lines.append(f"    {key}: {value:.2f}")
                    else:
                        lines.append(f"    {key}: {value}")

    lines.append(f"\n{'='*70}\n")
    return "\n".join(lines)


async def main_async(args):
    """Async main function"""
    tester = WebSocketTester(args.url, verbose=args.verbose, timeout=args.timeout)

    if args.test_all:
        suite = await tester.run_all_tests(latency_duration=args.duration)
    elif args.test:
        kwargs = {}
        if args.test == "latency":
            kwargs["duration"] = args.duration
        elif args.test == "concurrent":
            kwargs["connections"] = args.connections

        suite = await tester.run_specific_test(args.test, **kwargs)
    else:
        # Default: run connection test
        suite = await tester.run_specific_test("connection")

    # Output results
    output_format = "json" if args.json else "text"
    print(format_output(suite, output_format))

    # Exit with appropriate code
    if suite.failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Test WebSocket server functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  %(prog)s --url ws://localhost:8080 --test-all

  # Test connection only
  %(prog)s --url wss://example.com/ws --test connection

  # Test latency for 60 seconds
  %(prog)s --url ws://localhost:8080 --test latency --duration 60

  # Test concurrent connections
  %(prog)s --url ws://localhost:8080 --test concurrent --connections 100

  # JSON output
  %(prog)s --url ws://localhost:8080 --test-all --json

Available tests:
  connection      - Basic connection establishment
  echo            - Echo functionality
  json            - JSON message handling
  binary          - Binary message handling
  ping            - Protocol-level ping/pong
  close           - Graceful close handshake
  large           - Large message handling
  rapid           - Rapid message sending
  latency         - Round-trip latency measurement
  reconnection    - Reconnection capability
  concurrent      - Concurrent connections
  tls             - TLS/SSL connection (wss://)
        """
    )

    parser.add_argument(
        "--url",
        required=True,
        help="WebSocket server URL (ws:// or wss://)"
    )

    parser.add_argument(
        "--test",
        choices=["connection", "echo", "json", "binary", "ping", "close",
                "large", "rapid", "latency", "reconnection", "concurrent", "tls"],
        help="Specific test to run"
    )

    parser.add_argument(
        "--test-all",
        action="store_true",
        help="Run all tests"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration for latency test (seconds, default: 30)"
    )

    parser.add_argument(
        "--connections",
        type=int,
        default=10,
        help="Number of concurrent connections to test (default: 10)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Connection timeout (seconds, default: 10)"
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
