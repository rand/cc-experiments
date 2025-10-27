#!/usr/bin/env python3
"""
Test Rate Limits - API Rate Limiting Testing Tool

Tests API rate limiting behavior and configuration by sending requests
and analyzing responses.

Usage:
    ./test_rate_limits.py --endpoint https://api.example.com/resource
    ./test_rate_limits.py --endpoint https://api.example.com --json
    ./test_rate_limits.py --endpoint https://api.example.com --rps 10 --duration 60
    ./test_rate_limits.py --help

Features:
- Send requests to test rate limit enforcement
- Measure limit thresholds and reset times
- Validate rate limit headers
- Test different algorithms (token bucket, sliding window)
- Generate compliance report
"""

import argparse
import asyncio
import aiohttp
import time
import json
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from statistics import mean, median, stdev


@dataclass
class RequestResult:
    """Result of a single request"""
    timestamp: float
    status_code: int
    latency: float
    headers: Dict[str, str]
    error: Optional[str] = None


@dataclass
class RateLimitInfo:
    """Parsed rate limit information from headers"""
    limit: Optional[int] = None
    remaining: Optional[int] = None
    reset: Optional[int] = None
    retry_after: Optional[int] = None


@dataclass
class TestSummary:
    """Summary of rate limit test"""
    endpoint: str
    total_requests: int
    successful: int
    rate_limited: int
    errors: int
    success_rate: float
    rate_limit_rate: float
    avg_latency: float
    median_latency: float
    min_latency: float
    max_latency: float
    detected_limit: Optional[int]
    detected_window: Optional[int]
    algorithm_estimate: str
    rate_limit_info: RateLimitInfo
    boundary_burst_detected: bool
    compliant_headers: bool


class RateLimitTester:
    """Test API rate limiting behavior"""

    def __init__(self, endpoint: str, headers: Optional[Dict] = None):
        """Initialize rate limit tester

        Args:
            endpoint: API endpoint to test
            headers: Request headers (authentication, etc.)
        """
        self.endpoint = endpoint
        self.headers = headers or {}
        self.results: List[RequestResult] = []

    async def send_request(self, session: aiohttp.ClientSession) -> RequestResult:
        """Send single request and record result

        Args:
            session: aiohttp session

        Returns:
            Request result
        """
        start = time.time()

        try:
            async with session.get(self.endpoint, headers=self.headers) as response:
                latency = time.time() - start

                return RequestResult(
                    timestamp=time.time(),
                    status_code=response.status,
                    latency=latency,
                    headers=dict(response.headers),
                    error=None
                )

        except Exception as e:
            return RequestResult(
                timestamp=time.time(),
                status_code=0,
                latency=0.0,
                headers={},
                error=str(e)
            )

    async def burst_test(self, burst_size: int) -> List[RequestResult]:
        """Send burst of requests to test burst handling

        Args:
            burst_size: Number of requests in burst

        Returns:
            List of request results
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self.send_request(session) for _ in range(burst_size)]
            results = await asyncio.gather(*tasks)

        self.results.extend(results)
        return results

    async def sustained_test(self, rps: int, duration: int) -> List[RequestResult]:
        """Send sustained requests at target RPS

        Args:
            rps: Target requests per second
            duration: Test duration in seconds

        Returns:
            List of request results
        """
        interval = 1.0 / rps
        results = []

        async with aiohttp.ClientSession() as session:
            start_time = time.time()

            while time.time() - start_time < duration:
                request_start = time.time()

                result = await self.send_request(session)
                results.append(result)

                elapsed = time.time() - request_start
                if elapsed < interval:
                    await asyncio.sleep(interval - elapsed)

        self.results.extend(results)
        return results

    async def boundary_test(self, expected_limit: int, window_seconds: int) -> List[RequestResult]:
        """Test for boundary burst vulnerability (fixed window)

        Sends requests at window boundaries to detect fixed window algorithm.

        Args:
            expected_limit: Expected rate limit
            window_seconds: Expected window duration

        Returns:
            List of request results
        """
        results = []

        # Wait for window boundary
        now = time.time()
        next_boundary = (int(now // window_seconds) + 1) * window_seconds
        wait_time = next_boundary - now - 0.5  # Start 0.5s before boundary

        if wait_time > 0:
            await asyncio.sleep(wait_time)

        # Send requests across boundary
        async with aiohttp.ClientSession() as session:
            # Send expected_limit requests before boundary
            for _ in range(expected_limit):
                result = await self.send_request(session)
                results.append(result)

            # Wait for boundary
            await asyncio.sleep(1.0)

            # Send expected_limit requests after boundary
            for _ in range(expected_limit):
                result = await self.send_request(session)
                results.append(result)

        self.results.extend(results)
        return results

    def parse_rate_limit_headers(self, headers: Dict[str, str]) -> RateLimitInfo:
        """Parse rate limit headers from response

        Args:
            headers: Response headers

        Returns:
            Parsed rate limit information
        """
        # Try different header formats
        limit = None
        remaining = None
        reset = None
        retry_after = None

        # X-RateLimit-* format (most common)
        if 'x-ratelimit-limit' in headers:
            limit = int(headers['x-ratelimit-limit'])
        if 'x-ratelimit-remaining' in headers:
            remaining = int(headers['x-ratelimit-remaining'])
        if 'x-ratelimit-reset' in headers:
            reset = int(headers['x-ratelimit-reset'])

        # RateLimit-* format (newer standard)
        if 'ratelimit-limit' in headers:
            limit = int(headers['ratelimit-limit'])
        if 'ratelimit-remaining' in headers:
            remaining = int(headers['ratelimit-remaining'])
        if 'ratelimit-reset' in headers:
            reset = int(headers['ratelimit-reset'])

        # Retry-After header (429 response)
        if 'retry-after' in headers:
            try:
                retry_after = int(headers['retry-after'])
            except ValueError:
                pass

        return RateLimitInfo(
            limit=limit,
            remaining=remaining,
            reset=reset,
            retry_after=retry_after
        )

    def detect_algorithm(self) -> str:
        """Detect rate limiting algorithm based on behavior

        Returns:
            Algorithm name estimate
        """
        if not self.results:
            return "unknown"

        # Check for boundary burst (fixed window indicator)
        rate_limited = [r for r in self.results if r.status_code == 429]
        success = [r for r in self.results if r.status_code == 200]

        if not rate_limited:
            return "no_limit_detected"

        # Check timing of 429s
        if rate_limited:
            # Get time distribution
            timestamps = [r.timestamp for r in rate_limited]
            if len(timestamps) > 1:
                gaps = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]

                # Regular gaps suggest fixed window
                if len(gaps) > 2:
                    avg_gap = mean(gaps)
                    if stdev(gaps) / avg_gap < 0.2:  # Low variance
                        return "fixed_window"

        # Check for burst tolerance
        first_n = self.results[:20] if len(self.results) > 20 else self.results
        success_burst = sum(1 for r in first_n if r.status_code == 200)

        if success_burst > 10:
            return "token_bucket"

        return "sliding_window_or_leaky_bucket"

    def detect_boundary_burst(self) -> bool:
        """Detect if boundary burst occurred (fixed window vulnerability)

        Returns:
            True if boundary burst detected
        """
        if len(self.results) < 10:
            return False

        # Look for pattern: many 200s, then 429s, then 200s again
        status_codes = [r.status_code for r in self.results]

        # Find transitions
        transitions = []
        prev = status_codes[0]
        for code in status_codes[1:]:
            if code != prev:
                transitions.append((prev, code))
            prev = code

        # Look for 200 -> 429 -> 200 pattern
        for i in range(len(transitions) - 1):
            if (transitions[i] == (200, 429) and
                transitions[i+1] == (429, 200)):
                return True

        return False

    def analyze_results(self) -> TestSummary:
        """Analyze test results and generate summary

        Returns:
            Test summary
        """
        if not self.results:
            return TestSummary(
                endpoint=self.endpoint,
                total_requests=0,
                successful=0,
                rate_limited=0,
                errors=0,
                success_rate=0.0,
                rate_limit_rate=0.0,
                avg_latency=0.0,
                median_latency=0.0,
                min_latency=0.0,
                max_latency=0.0,
                detected_limit=None,
                detected_window=None,
                algorithm_estimate="unknown",
                rate_limit_info=RateLimitInfo(),
                boundary_burst_detected=False,
                compliant_headers=False
            )

        total = len(self.results)
        successful = sum(1 for r in self.results if r.status_code == 200)
        rate_limited = sum(1 for r in self.results if r.status_code == 429)
        errors = sum(1 for r in self.results if r.status_code not in [200, 429] and r.status_code != 0)

        latencies = [r.latency for r in self.results if r.latency > 0]
        avg_latency = mean(latencies) if latencies else 0.0
        median_latency = median(latencies) if latencies else 0.0
        min_latency = min(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0

        # Parse rate limit info from first response with headers
        rate_limit_info = RateLimitInfo()
        for result in self.results:
            if result.headers:
                rate_limit_info = self.parse_rate_limit_headers(result.headers)
                if rate_limit_info.limit is not None:
                    break

        # Detect limit and window
        detected_limit = rate_limit_info.limit
        detected_window = None

        if rate_limited > 0:
            # Try to detect window from reset times
            reset_times = []
            for result in self.results:
                if result.status_code == 429 and result.headers:
                    info = self.parse_rate_limit_headers(result.headers)
                    if info.reset:
                        reset_times.append(info.reset)

            if len(reset_times) > 1:
                gaps = [reset_times[i+1] - reset_times[i] for i in range(len(reset_times)-1)]
                if gaps:
                    detected_window = int(median(gaps))

        # Check header compliance
        compliant = False
        for result in self.results:
            if result.status_code == 429 and result.headers:
                info = self.parse_rate_limit_headers(result.headers)
                if info.limit and info.reset and info.retry_after:
                    compliant = True
                    break

        return TestSummary(
            endpoint=self.endpoint,
            total_requests=total,
            successful=successful,
            rate_limited=rate_limited,
            errors=errors,
            success_rate=successful / total if total > 0 else 0.0,
            rate_limit_rate=rate_limited / total if total > 0 else 0.0,
            avg_latency=avg_latency,
            median_latency=median_latency,
            min_latency=min_latency,
            max_latency=max_latency,
            detected_limit=detected_limit,
            detected_window=detected_window,
            algorithm_estimate=self.detect_algorithm(),
            rate_limit_info=rate_limit_info,
            boundary_burst_detected=self.detect_boundary_burst(),
            compliant_headers=compliant
        )


def format_human_readable(summary: TestSummary) -> str:
    """Format summary for human-readable output

    Args:
        summary: Test summary

    Returns:
        Formatted string
    """
    lines = [
        "=" * 70,
        "API Rate Limit Test Results",
        "=" * 70,
        f"Endpoint: {summary.endpoint}",
        "",
        "Request Statistics:",
        f"  Total Requests:  {summary.total_requests}",
        f"  Successful:      {summary.successful} ({summary.success_rate:.1%})",
        f"  Rate Limited:    {summary.rate_limited} ({summary.rate_limit_rate:.1%})",
        f"  Errors:          {summary.errors}",
        "",
        "Latency Statistics:",
        f"  Average:         {summary.avg_latency*1000:.2f} ms",
        f"  Median:          {summary.median_latency*1000:.2f} ms",
        f"  Min:             {summary.min_latency*1000:.2f} ms",
        f"  Max:             {summary.max_latency*1000:.2f} ms",
        "",
        "Rate Limit Configuration:",
        f"  Detected Limit:  {summary.detected_limit or 'Unknown'}",
        f"  Detected Window: {summary.detected_window or 'Unknown'} seconds" if summary.detected_window else "  Detected Window: Unknown",
        f"  Algorithm:       {summary.algorithm_estimate.replace('_', ' ').title()}",
        "",
        "Rate Limit Headers:",
        f"  Limit:           {summary.rate_limit_info.limit or 'Not present'}",
        f"  Remaining:       {summary.rate_limit_info.remaining or 'Not present'}",
        f"  Reset:           {summary.rate_limit_info.reset or 'Not present'}",
        f"  Retry-After:     {summary.rate_limit_info.retry_after or 'Not present'}",
        "",
        "Compliance Check:",
        f"  RFC 6585 Headers: {'✓ Compliant' if summary.compliant_headers else '✗ Non-compliant'}",
        f"  Boundary Burst:   {'✗ Detected (Fixed Window)' if summary.boundary_burst_detected else '✓ Not Detected'}",
        "=" * 70
    ]

    return "\n".join(lines)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test API rate limiting behavior and configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test endpoint with burst
  %(prog)s --endpoint https://api.example.com/resource

  # Test with sustained load
  %(prog)s --endpoint https://api.example.com --rps 10 --duration 60

  # Test with authentication
  %(prog)s --endpoint https://api.example.com --header "Authorization: Bearer token"

  # JSON output for automation
  %(prog)s --endpoint https://api.example.com --json

  # Test for boundary burst vulnerability
  %(prog)s --endpoint https://api.example.com --boundary-test --limit 100 --window 60
        """
    )

    parser.add_argument('--endpoint', required=True,
                       help='API endpoint to test')
    parser.add_argument('--rps', type=int, default=10,
                       help='Requests per second for sustained test (default: 10)')
    parser.add_argument('--duration', type=int, default=10,
                       help='Test duration in seconds (default: 10)')
    parser.add_argument('--burst', type=int,
                       help='Burst size for burst test')
    parser.add_argument('--boundary-test', action='store_true',
                       help='Test for boundary burst vulnerability')
    parser.add_argument('--limit', type=int,
                       help='Expected rate limit (for boundary test)')
    parser.add_argument('--window', type=int, default=60,
                       help='Expected window duration in seconds (default: 60)')
    parser.add_argument('--header', action='append', dest='headers',
                       help='Request header (format: "Name: Value")')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')

    args = parser.parse_args()

    # Parse headers
    headers = {}
    if args.headers:
        for header in args.headers:
            if ':' in header:
                name, value = header.split(':', 1)
                headers[name.strip()] = value.strip()

    # Create tester
    tester = RateLimitTester(args.endpoint, headers)

    # Run test
    try:
        if args.boundary_test:
            if not args.limit:
                print("Error: --limit required for boundary test", file=sys.stderr)
                sys.exit(1)

            if not args.json:
                print(f"Running boundary test (limit={args.limit}, window={args.window}s)...")

            await tester.boundary_test(args.limit, args.window)

        elif args.burst:
            if not args.json:
                print(f"Running burst test ({args.burst} requests)...")

            await tester.burst_test(args.burst)

        else:
            if not args.json:
                print(f"Running sustained test ({args.rps} RPS for {args.duration}s)...")

            await tester.sustained_test(args.rps, args.duration)

        # Analyze results
        summary = tester.analyze_results()

        # Output results
        if args.json:
            print(json.dumps(asdict(summary), indent=2))
        else:
            print()
            print(format_human_readable(summary))

    except KeyboardInterrupt:
        print("\nTest interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
