#!/usr/bin/env python3
"""
WebSocket Testing Tool

Test WebSocket servers for connectivity, latency, message handling, and correctness.
Supports text/binary messages, ping/pong, and connection lifecycle testing.

Usage:
    test_websocket.py <url> [options]
    test_websocket.py wss://api.example.com/ws --count 10 --interval 1
    test_websocket.py ws://localhost:8080 --message "Hello" --binary
    test_websocket.py wss://api.example.com/ws --latency --json
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional, List
import websockets
from websockets.exceptions import WebSocketException


@dataclass
class TestResult:
    """Test result for a single operation"""
    success: bool
    operation: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    message_sent: Optional[str] = None
    message_received: Optional[str] = None
    close_code: Optional[int] = None
    close_reason: Optional[str] = None


@dataclass
class TestSummary:
    """Summary of all test results"""
    url: str
    total_tests: int
    successful: int
    failed: int
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    results: List[TestResult]


class WebSocketTester:
    """WebSocket testing utility"""

    def __init__(self, url: str, timeout: float = 10.0, verbose: bool = False):
        self.url = url
        self.timeout = timeout
        self.verbose = verbose
        self.results: List[TestResult] = []

    def log(self, message: str):
        """Log message if verbose mode enabled"""
        if self.verbose:
            print(f"[TEST] {message}", file=sys.stderr)

    async def test_connect(self) -> TestResult:
        """Test basic connection"""
        start = time.time()
        try:
            async with websockets.connect(self.url, timeout=self.timeout) as ws:
                latency = (time.time() - start) * 1000
                self.log(f"Connected successfully in {latency:.2f}ms")
                return TestResult(
                    success=True,
                    operation="connect",
                    latency_ms=latency
                )
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.log(f"Connection failed: {e}")
            return TestResult(
                success=False,
                operation="connect",
                latency_ms=latency,
                error=str(e)
            )

    async def test_echo(self, message: str, binary: bool = False) -> TestResult:
        """Test sending and receiving messages (echo test)"""
        start = time.time()
        try:
            async with websockets.connect(self.url, timeout=self.timeout) as ws:
                # Send message
                if binary:
                    await ws.send(message.encode())
                else:
                    await ws.send(message)

                # Receive response
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                if binary:
                    response = response.decode() if isinstance(response, bytes) else response

                latency = (time.time() - start) * 1000
                success = response == message if not binary else True

                self.log(f"Echo test: sent={message}, received={response}, latency={latency:.2f}ms")

                return TestResult(
                    success=success,
                    operation="echo",
                    latency_ms=latency,
                    message_sent=message,
                    message_received=str(response),
                    error=None if success else "Echo mismatch"
                )
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.log(f"Echo test failed: {e}")
            return TestResult(
                success=False,
                operation="echo",
                latency_ms=latency,
                message_sent=message,
                error=str(e)
            )

    async def test_latency(self, count: int = 10, interval: float = 0.5) -> List[TestResult]:
        """Test message latency with multiple messages"""
        results = []

        try:
            async with websockets.connect(self.url, timeout=self.timeout) as ws:
                for i in range(count):
                    start = time.time()

                    # Send ping-like message
                    message = json.dumps({"type": "ping", "id": i, "timestamp": start})
                    await ws.send(message)

                    # Wait for response
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        latency = (time.time() - start) * 1000

                        results.append(TestResult(
                            success=True,
                            operation="latency",
                            latency_ms=latency,
                            message_sent=message,
                            message_received=response
                        ))

                        self.log(f"Latency test {i+1}/{count}: {latency:.2f}ms")

                    except asyncio.TimeoutError:
                        results.append(TestResult(
                            success=False,
                            operation="latency",
                            error="Response timeout"
                        ))

                    # Wait between messages
                    if i < count - 1:
                        await asyncio.sleep(interval)

        except Exception as e:
            self.log(f"Latency test failed: {e}")
            results.append(TestResult(
                success=False,
                operation="latency",
                error=str(e)
            ))

        return results

    async def test_ping_pong(self) -> TestResult:
        """Test WebSocket ping/pong frames"""
        start = time.time()
        try:
            async with websockets.connect(self.url, timeout=self.timeout) as ws:
                # Send ping
                pong_waiter = await ws.ping()

                # Wait for pong
                await asyncio.wait_for(pong_waiter, timeout=5.0)

                latency = (time.time() - start) * 1000
                self.log(f"Ping/pong successful: {latency:.2f}ms")

                return TestResult(
                    success=True,
                    operation="ping_pong",
                    latency_ms=latency
                )
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.log(f"Ping/pong failed: {e}")
            return TestResult(
                success=False,
                operation="ping_pong",
                latency_ms=latency,
                error=str(e)
            )

    async def test_close(self, code: int = 1000, reason: str = "Normal closure") -> TestResult:
        """Test connection close with status code"""
        start = time.time()
        try:
            async with websockets.connect(self.url, timeout=self.timeout) as ws:
                # Initiate close
                await ws.close(code=code, reason=reason)

                latency = (time.time() - start) * 1000
                self.log(f"Close successful: code={code}, reason={reason}")

                return TestResult(
                    success=True,
                    operation="close",
                    latency_ms=latency,
                    close_code=code,
                    close_reason=reason
                )
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.log(f"Close failed: {e}")
            return TestResult(
                success=False,
                operation="close",
                latency_ms=latency,
                error=str(e)
            )

    async def test_large_message(self, size_kb: int = 100) -> TestResult:
        """Test sending large messages"""
        start = time.time()
        message = "x" * (size_kb * 1024)

        try:
            async with websockets.connect(self.url, timeout=self.timeout) as ws:
                await ws.send(message)

                # Try to receive response
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    latency = (time.time() - start) * 1000

                    self.log(f"Large message test: sent {size_kb}KB, received {len(response)} bytes")

                    return TestResult(
                        success=True,
                        operation="large_message",
                        latency_ms=latency,
                        message_sent=f"{size_kb}KB message"
                    )
                except asyncio.TimeoutError:
                    # Server might not echo, but sending succeeded
                    latency = (time.time() - start) * 1000
                    return TestResult(
                        success=True,
                        operation="large_message",
                        latency_ms=latency,
                        message_sent=f"{size_kb}KB message",
                        error="No echo (expected)"
                    )

        except Exception as e:
            latency = (time.time() - start) * 1000
            self.log(f"Large message test failed: {e}")
            return TestResult(
                success=False,
                operation="large_message",
                latency_ms=latency,
                error=str(e)
            )

    async def test_reconnect(self, attempts: int = 3) -> List[TestResult]:
        """Test reconnection behavior"""
        results = []

        for i in range(attempts):
            result = await self.test_connect()
            results.append(result)

            if result.success:
                self.log(f"Reconnect {i+1}/{attempts} successful")
            else:
                self.log(f"Reconnect {i+1}/{attempts} failed")

            # Wait before next attempt
            if i < attempts - 1:
                await asyncio.sleep(1.0)

        return results

    async def run_all_tests(self, custom_message: Optional[str] = None) -> TestSummary:
        """Run comprehensive test suite"""
        self.results = []

        # Basic connectivity
        self.log("Running connectivity test...")
        self.results.append(await self.test_connect())

        # Echo test
        self.log("Running echo test...")
        message = custom_message or "Hello WebSocket"
        self.results.append(await self.test_echo(message))

        # Latency test
        self.log("Running latency test...")
        latency_results = await self.test_latency(count=5)
        self.results.extend(latency_results)

        # Ping/pong
        self.log("Running ping/pong test...")
        self.results.append(await self.test_ping_pong())

        # Close
        self.log("Running close test...")
        self.results.append(await self.test_close())

        # Large message
        self.log("Running large message test...")
        self.results.append(await self.test_large_message(size_kb=10))

        # Reconnection
        self.log("Running reconnection test...")
        reconnect_results = await self.test_reconnect(attempts=2)
        self.results.extend(reconnect_results)

        # Generate summary
        return self._generate_summary()

    def _generate_summary(self) -> TestSummary:
        """Generate test summary from results"""
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful

        latencies = [r.latency_ms for r in self.results if r.latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0

        return TestSummary(
            url=self.url,
            total_tests=len(self.results),
            successful=successful,
            failed=failed,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            results=self.results
        )


def print_summary(summary: TestSummary, output_json: bool = False):
    """Print test summary"""
    if output_json:
        # JSON output
        print(json.dumps(asdict(summary), indent=2))
    else:
        # Human-readable output
        print(f"\n{'='*60}")
        print(f"WebSocket Test Summary: {summary.url}")
        print(f"{'='*60}")
        print(f"Total Tests:    {summary.total_tests}")
        print(f"Successful:     {summary.successful} ({summary.successful/summary.total_tests*100:.1f}%)")
        print(f"Failed:         {summary.failed}")
        print(f"\nLatency:")
        print(f"  Average:      {summary.avg_latency_ms:.2f}ms")
        print(f"  Min:          {summary.min_latency_ms:.2f}ms")
        print(f"  Max:          {summary.max_latency_ms:.2f}ms")
        print(f"\nDetailed Results:")
        for i, result in enumerate(summary.results, 1):
            status = "✓" if result.success else "✗"
            latency = f"{result.latency_ms:.2f}ms" if result.latency_ms else "N/A"
            print(f"  {status} {result.operation:15s} {latency:10s}", end="")
            if result.error:
                print(f" Error: {result.error}")
            else:
                print()
        print(f"{'='*60}\n")


async def main():
    parser = argparse.ArgumentParser(
        description="WebSocket Testing Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic connectivity test
  %(prog)s wss://api.example.com/ws

  # Custom message echo test
  %(prog)s ws://localhost:8080 --message "Hello World"

  # Latency test with 20 messages
  %(prog)s wss://api.example.com/ws --latency --count 20

  # JSON output for parsing
  %(prog)s wss://api.example.com/ws --json

  # Verbose output
  %(prog)s ws://localhost:8080 --verbose
        """
    )

    parser.add_argument("url", help="WebSocket URL (ws:// or wss://)")
    parser.add_argument("-m", "--message", help="Custom message to send")
    parser.add_argument("-c", "--count", type=int, default=10, help="Number of messages for latency test (default: 10)")
    parser.add_argument("-i", "--interval", type=float, default=0.5, help="Interval between messages in seconds (default: 0.5)")
    parser.add_argument("-t", "--timeout", type=float, default=10.0, help="Connection timeout in seconds (default: 10)")
    parser.add_argument("--binary", action="store_true", help="Send message as binary")
    parser.add_argument("--latency", action="store_true", help="Run latency test only")
    parser.add_argument("--ping", action="store_true", help="Run ping/pong test only")
    parser.add_argument("--large", type=int, metavar="SIZE_KB", help="Test large message of SIZE_KB")
    parser.add_argument("--reconnect", type=int, metavar="ATTEMPTS", help="Test reconnection ATTEMPTS times")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Validate URL
    if not args.url.startswith(("ws://", "wss://")):
        print("Error: URL must start with ws:// or wss://", file=sys.stderr)
        sys.exit(1)

    # Create tester
    tester = WebSocketTester(args.url, timeout=args.timeout, verbose=args.verbose)

    try:
        # Run specific test or full suite
        if args.latency:
            results = await tester.test_latency(count=args.count, interval=args.interval)
            tester.results = results
            summary = tester._generate_summary()
        elif args.ping:
            result = await tester.test_ping_pong()
            tester.results = [result]
            summary = tester._generate_summary()
        elif args.large:
            result = await tester.test_large_message(size_kb=args.large)
            tester.results = [result]
            summary = tester._generate_summary()
        elif args.reconnect:
            results = await tester.test_reconnect(attempts=args.reconnect)
            tester.results = results
            summary = tester._generate_summary()
        else:
            # Full test suite
            summary = await tester.run_all_tests(custom_message=args.message)

        # Print results
        print_summary(summary, output_json=args.json)

        # Exit code based on success
        sys.exit(0 if summary.failed == 0 else 1)

    except KeyboardInterrupt:
        print("\nTest interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
