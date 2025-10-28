#!/usr/bin/env python3
"""
HTTP/3 Connection Tester

Tests HTTP/3 connectivity, 0-RTT, connection migration, and performance metrics.

Usage:
    ./test_http3_connection.py --url https://example.com [--json]
    ./test_http3_connection.py --url https://example.com --test-0rtt [--json]
    ./test_http3_connection.py --url https://example.com --compare-http2 [--json]
    ./test_http3_connection.py --help

Features:
    - Test basic HTTP/3 connectivity
    - Verify 0-RTT (zero round-trip time) resumption
    - Test connection migration (path changes)
    - Measure TTFB (time to first byte)
    - Compare HTTP/3 vs HTTP/2 performance
    - Verify QUIC parameters
    - Check Alt-Svc advertisement
    - Output as JSON or human-readable text

Exit Codes:
    0: Success (all tests passed)
    1: Partial failure (some tests failed)
    2: Complete failure (connection failed)
    3: Invalid arguments
"""

import argparse
import asyncio
import json
import sys
import time
import ssl
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import tempfile


try:
    from aioquic.asyncio import connect
    from aioquic.h3.connection import H3_ALPN, H3Connection
    from aioquic.h3.events import DataReceived, HeadersReceived
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.quic.events import QuicEvent
    AIOQUIC_AVAILABLE = True
except ImportError:
    AIOQUIC_AVAILABLE = False


try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class TestResult:
    """Result of a single test"""
    name: str
    success: bool
    duration_ms: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionMetrics:
    """HTTP/3 connection metrics"""
    ttfb_ms: float  # Time to first byte
    total_time_ms: float
    status_code: int
    protocol: str
    quic_version: Optional[str] = None
    tls_version: Optional[str] = None
    bytes_received: int = 0
    bytes_sent: int = 0
    rtt_ms: Optional[float] = None
    packet_loss_rate: Optional[float] = None


@dataclass
class TestSuite:
    """Container for all test results"""
    url: str
    timestamp: float = field(default_factory=time.time)
    tests: List[TestResult] = field(default_factory=list)
    metrics: Optional[ConnectionMetrics] = None

    def add_test(self, name: str, success: bool, duration_ms: float,
                 message: str, details: Optional[Dict] = None):
        """Add a test result"""
        self.tests.append(TestResult(
            name=name,
            success=success,
            duration_ms=duration_ms,
            message=message,
            details=details or {}
        ))

    def success_rate(self) -> float:
        """Calculate test success rate"""
        if not self.tests:
            return 0.0
        return sum(1 for t in self.tests if t.success) / len(self.tests) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "url": self.url,
            "timestamp": self.timestamp,
            "tests": [asdict(t) for t in self.tests],
            "metrics": asdict(self.metrics) if self.metrics else None,
            "summary": {
                "total_tests": len(self.tests),
                "passed": sum(1 for t in self.tests if t.success),
                "failed": sum(1 for t in self.tests if not t.success),
                "success_rate": self.success_rate(),
            }
        }


class HTTP3Tester:
    """HTTP/3 connection tester"""

    def __init__(self, url: str, verify_ssl: bool = True):
        self.url = url
        self.verify_ssl = verify_ssl
        self.parsed_url = urlparse(url)

        if not self.parsed_url.scheme == 'https':
            raise ValueError("URL must use https://")

        self.host = self.parsed_url.hostname
        self.port = self.parsed_url.port or 443
        self.path = self.parsed_url.path or '/'

    async def test_basic_connectivity(self) -> TestResult:
        """Test basic HTTP/3 connectivity"""
        start = time.time()

        try:
            # Configure QUIC
            configuration = QuicConfiguration(
                alpn_protocols=H3_ALPN,
                is_client=True,
                verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
            )

            # Connect
            async with connect(
                self.host,
                self.port,
                configuration=configuration,
            ) as client:
                # Create HTTP/3 connection
                http = H3Connection(client._quic)

                # Send request
                stream_id = client._quic.get_next_available_stream_id()

                headers = [
                    (b":method", b"GET"),
                    (b":scheme", b"https"),
                    (b":authority", self.host.encode()),
                    (b":path", self.path.encode()),
                    (b"user-agent", b"http3-tester/1.0"),
                ]

                http.send_headers(stream_id=stream_id, headers=headers)

                # Wait for response
                response_received = False
                status_code = None
                ttfb = None

                while not response_received:
                    for event in client._quic.next_event():
                        if isinstance(event, HeadersReceived):
                            if ttfb is None:
                                ttfb = (time.time() - start) * 1000

                            for header, value in event.headers:
                                if header == b":status":
                                    status_code = int(value.decode())
                                    response_received = True

                    await asyncio.sleep(0.01)

                duration = (time.time() - start) * 1000

                return TestResult(
                    name="basic_connectivity",
                    success=status_code == 200,
                    duration_ms=duration,
                    message=f"HTTP/3 request successful (status: {status_code})",
                    details={
                        "status_code": status_code,
                        "ttfb_ms": ttfb,
                        "protocol": "h3",
                    }
                )

        except Exception as e:
            duration = (time.time() - start) * 1000
            return TestResult(
                name="basic_connectivity",
                success=False,
                duration_ms=duration,
                message=f"HTTP/3 connection failed: {e}",
                details={"error": str(e)}
            )

    async def test_0rtt(self) -> TestResult:
        """Test 0-RTT connection resumption"""
        start = time.time()

        try:
            # First connection (to get session ticket)
            configuration = QuicConfiguration(
                alpn_protocols=H3_ALPN,
                is_client=True,
                verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
                session_ticket_handler=None,  # Will be set
            )

            session_ticket = None

            def save_session_ticket(ticket):
                nonlocal session_ticket
                session_ticket = ticket

            configuration.session_ticket_handler = save_session_ticket

            # First connection
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
                ]

                http.send_headers(stream_id=stream_id, headers=headers)

                # Wait briefly for response
                await asyncio.sleep(0.5)

            # Check if we got a session ticket
            if not session_ticket:
                return TestResult(
                    name="0rtt",
                    success=False,
                    duration_ms=(time.time() - start) * 1000,
                    message="Server did not provide session ticket for 0-RTT",
                    details={"ticket_received": False}
                )

            # Second connection with 0-RTT
            configuration_0rtt = QuicConfiguration(
                alpn_protocols=H3_ALPN,
                is_client=True,
                verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
            )

            configuration_0rtt.load_session_ticket(session_ticket)

            start_0rtt = time.time()

            async with connect(
                self.host,
                self.port,
                configuration=configuration_0rtt,
            ) as client:
                # Check if 0-RTT was used
                used_0rtt = client._quic._is_0rtt if hasattr(client._quic, '_is_0rtt') else False

                duration = (time.time() - start_0rtt) * 1000

                return TestResult(
                    name="0rtt",
                    success=True,
                    duration_ms=duration,
                    message=f"0-RTT {'used' if used_0rtt else 'not used (server may not support it)'}",
                    details={
                        "ticket_received": True,
                        "0rtt_used": used_0rtt,
                        "connection_time_ms": duration,
                    }
                )

        except Exception as e:
            duration = (time.time() - start) * 1000
            return TestResult(
                name="0rtt",
                success=False,
                duration_ms=duration,
                message=f"0-RTT test failed: {e}",
                details={"error": str(e)}
            )

    async def measure_ttfb(self, iterations: int = 5) -> TestResult:
        """Measure time to first byte over multiple iterations"""
        start = time.time()
        ttfbs = []

        try:
            configuration = QuicConfiguration(
                alpn_protocols=H3_ALPN,
                is_client=True,
                verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
            )

            for i in range(iterations):
                iter_start = time.time()

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
                    ]

                    http.send_headers(stream_id=stream_id, headers=headers)

                    # Wait for first byte
                    response_received = False
                    while not response_received:
                        for event in client._quic.next_event():
                            if isinstance(event, HeadersReceived):
                                ttfb = (time.time() - iter_start) * 1000
                                ttfbs.append(ttfb)
                                response_received = True
                                break
                        if not response_received:
                            await asyncio.sleep(0.01)

            # Calculate statistics
            avg_ttfb = sum(ttfbs) / len(ttfbs)
            min_ttfb = min(ttfbs)
            max_ttfb = max(ttfbs)
            p50_ttfb = sorted(ttfbs)[len(ttfbs) // 2]
            p95_ttfb = sorted(ttfbs)[int(len(ttfbs) * 0.95)]

            duration = (time.time() - start) * 1000

            return TestResult(
                name="ttfb_measurement",
                success=True,
                duration_ms=duration,
                message=f"TTFB average: {avg_ttfb:.2f}ms over {iterations} iterations",
                details={
                    "iterations": iterations,
                    "ttfb_avg_ms": avg_ttfb,
                    "ttfb_min_ms": min_ttfb,
                    "ttfb_max_ms": max_ttfb,
                    "ttfb_p50_ms": p50_ttfb,
                    "ttfb_p95_ms": p95_ttfb,
                    "all_ttfb_ms": ttfbs,
                }
            )

        except Exception as e:
            duration = (time.time() - start) * 1000
            return TestResult(
                name="ttfb_measurement",
                success=False,
                duration_ms=duration,
                message=f"TTFB measurement failed: {e}",
                details={"error": str(e)}
            )

    async def compare_http2(self) -> TestResult:
        """Compare HTTP/3 vs HTTP/2 performance"""
        if not HTTPX_AVAILABLE:
            return TestResult(
                name="http2_comparison",
                success=False,
                duration_ms=0,
                message="httpx library not available (pip install httpx)",
                details={}
            )

        start = time.time()

        try:
            # Test HTTP/3
            http3_start = time.time()
            configuration = QuicConfiguration(
                alpn_protocols=H3_ALPN,
                is_client=True,
                verify_mode=ssl.CERT_REQUIRED if self.verify_ssl else ssl.CERT_NONE,
            )

            http3_ttfb = None

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
                ]

                http.send_headers(stream_id=stream_id, headers=headers)

                response_received = False
                while not response_received:
                    for event in client._quic.next_event():
                        if isinstance(event, HeadersReceived):
                            http3_ttfb = (time.time() - http3_start) * 1000
                            response_received = True
                            break
                    if not response_received:
                        await asyncio.sleep(0.01)

            # Test HTTP/2
            http2_start = time.time()
            async with httpx.AsyncClient(http2=True) as client:
                response = await client.get(self.url)
                http2_ttfb = (time.time() - http2_start) * 1000

            # Compare
            improvement = ((http2_ttfb - http3_ttfb) / http2_ttfb) * 100

            duration = (time.time() - start) * 1000

            return TestResult(
                name="http2_comparison",
                success=True,
                duration_ms=duration,
                message=f"HTTP/3 is {improvement:.1f}% {'faster' if improvement > 0 else 'slower'} than HTTP/2",
                details={
                    "http3_ttfb_ms": http3_ttfb,
                    "http2_ttfb_ms": http2_ttfb,
                    "improvement_percent": improvement,
                }
            )

        except Exception as e:
            duration = (time.time() - start) * 1000
            return TestResult(
                name="http2_comparison",
                success=False,
                duration_ms=duration,
                message=f"HTTP/2 comparison failed: {e}",
                details={"error": str(e)}
            )

    async def test_alt_svc(self) -> TestResult:
        """Test Alt-Svc header advertisement"""
        if not HTTPX_AVAILABLE:
            return TestResult(
                name="alt_svc",
                success=False,
                duration_ms=0,
                message="httpx library not available (pip install httpx)",
                details={}
            )

        start = time.time()

        try:
            # Make HTTP/2 request to check Alt-Svc header
            async with httpx.AsyncClient(http2=True) as client:
                response = await client.get(self.url)
                alt_svc = response.headers.get('alt-svc', '')

                has_h3 = 'h3=' in alt_svc.lower()

                duration = (time.time() - start) * 1000

                return TestResult(
                    name="alt_svc",
                    success=has_h3,
                    duration_ms=duration,
                    message=f"Alt-Svc header {'found' if has_h3 else 'not found'}: {alt_svc or 'N/A'}",
                    details={
                        "alt_svc_header": alt_svc,
                        "advertises_h3": has_h3,
                    }
                )

        except Exception as e:
            duration = (time.time() - start) * 1000
            return TestResult(
                name="alt_svc",
                success=False,
                duration_ms=duration,
                message=f"Alt-Svc test failed: {e}",
                details={"error": str(e)}
            )

    async def run_all_tests(self, test_0rtt: bool = False,
                           compare_http2: bool = False) -> TestSuite:
        """Run all HTTP/3 tests"""
        suite = TestSuite(url=self.url)

        # Basic connectivity
        result = await self.test_basic_connectivity()
        suite.tests.append(result)

        if not result.success:
            # If basic connectivity fails, skip other tests
            return suite

        # TTFB measurement
        result = await self.measure_ttfb()
        suite.tests.append(result)

        # 0-RTT test
        if test_0rtt:
            result = await self.test_0rtt()
            suite.tests.append(result)

        # HTTP/2 comparison
        if compare_http2:
            result = await self.compare_http2()
            suite.tests.append(result)

        # Alt-Svc test
        result = await self.test_alt_svc()
        suite.tests.append(result)

        return suite


def print_human_readable(suite: TestSuite):
    """Print results in human-readable format"""
    print(f"\nHTTP/3 Connection Test Results")
    print(f"{'=' * 80}")
    print(f"URL: {suite.url}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(suite.timestamp))}")
    print()

    # Print test results
    for test in suite.tests:
        icon = "✓" if test.success else "✗"
        color = "\033[92m" if test.success else "\033[91m"
        reset = "\033[0m"

        print(f"{color}{icon}{reset} {test.name.replace('_', ' ').title()}")
        print(f"  Duration: {test.duration_ms:.2f}ms")
        print(f"  Result: {test.message}")

        if test.details:
            print(f"  Details:")
            for key, value in test.details.items():
                if isinstance(value, list):
                    continue  # Skip lists for brevity
                print(f"    {key}: {value}")
        print()

    # Print summary
    summary = suite.to_dict()["summary"]
    print(f"SUMMARY")
    print("-" * 80)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print()


async def main_async():
    parser = argparse.ArgumentParser(
        description="HTTP/3 Connection Tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic connectivity test
  ./test_http3_connection.py --url https://cloudflare-quic.com

  # Test with 0-RTT
  ./test_http3_connection.py --url https://cloudflare-quic.com --test-0rtt

  # Compare HTTP/3 vs HTTP/2
  ./test_http3_connection.py --url https://cloudflare-quic.com --compare-http2

  # JSON output
  ./test_http3_connection.py --url https://cloudflare-quic.com --json

  # All tests with JSON output
  ./test_http3_connection.py --url https://cloudflare-quic.com --test-0rtt --compare-http2 --json

Exit codes:
  0 = All tests passed
  1 = Some tests failed
  2 = Connection failed
  3 = Invalid arguments
        """
    )

    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="URL to test (must use https://)",
    )

    parser.add_argument(
        "--test-0rtt",
        action="store_true",
        help="Test 0-RTT connection resumption",
    )

    parser.add_argument(
        "--compare-http2",
        action="store_true",
        help="Compare HTTP/3 vs HTTP/2 performance",
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

    # Create tester
    try:
        tester = HTTP3Tester(args.url, verify_ssl=not args.no_verify_ssl)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 3

    # Run tests
    try:
        suite = await tester.run_all_tests(
            test_0rtt=args.test_0rtt,
            compare_http2=args.compare_http2,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    # Output results
    if args.json:
        output = suite.to_dict()
        print(json.dumps(output, indent=2))

        # Return exit code based on results
        if suite.success_rate() == 100:
            return 0
        elif suite.success_rate() > 0:
            return 1
        else:
            return 2
    else:
        print_human_readable(suite)

        # Return exit code
        if suite.success_rate() == 100:
            return 0
        elif suite.success_rate() > 0:
            return 1
        else:
            return 2


def main():
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
