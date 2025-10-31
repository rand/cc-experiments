#!/usr/bin/env python3
"""
PyO3 Web Frameworks API Benchmark Tool

Comprehensive API endpoint performance benchmarking for FastAPI, Flask, and Django
applications with PyO3 extensions. Measures request/response timing, concurrency,
throughput, and latency distributions.

Features:
- Multi-framework support (FastAPI, Flask, Django)
- Concurrent request testing
- Statistical latency analysis (p50, p95, p99)
- Request body templating
- Custom headers and authentication
- JSON and text output formats
- Comparative benchmarking
- Connection pooling metrics

Usage:
    ./api_benchmark.py benchmark http://localhost:8000/api/users --requests 1000
    ./api_benchmark.py load-test http://localhost:8000/api/users --concurrent 50 --duration 60
    ./api_benchmark.py analyze results.json
    ./api_benchmark.py compare baseline.json current.json
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import statistics
import ssl


@dataclass
class RequestResult:
    """Single request execution result"""
    latency_ms: float
    status_code: int
    response_size_bytes: int
    success: bool
    timestamp: float
    error: Optional[str] = None


@dataclass
class LatencyStats:
    """Latency distribution statistics"""
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    stddev_ms: float


@dataclass
class ThroughputStats:
    """Throughput measurements"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    total_time_s: float
    requests_per_second: float
    avg_response_size_bytes: float


@dataclass
class BenchmarkResult:
    """Complete benchmark results"""
    endpoint: str
    method: str
    total_requests: int
    concurrent_workers: int
    start_time: str
    end_time: str
    duration_s: float
    latency: LatencyStats
    throughput: ThroughputStats
    results: List[RequestResult] = field(default_factory=list)


class RequestBuilder:
    """Build HTTP requests with templating support"""

    def __init__(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body_template: Optional[str] = None,
        auth_token: Optional[str] = None
    ):
        self.url = url
        self.method = method.upper()
        self.headers = headers or {}
        self.body_template = body_template

        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"

    def build_request(self, iteration: int) -> urllib.request.Request:
        """Build a request with templated body"""
        body = None
        if self.body_template:
            # Simple template substitution
            body_str = self.body_template.replace("{iteration}", str(iteration))
            body_str = body_str.replace("{timestamp}", str(int(time.time())))
            body = body_str.encode()

        headers = self.headers.copy()
        if body and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        return urllib.request.Request(
            self.url,
            data=body,
            headers=headers,
            method=self.method
        )


class APIBenchmark:
    """Benchmark API endpoints"""

    def __init__(
        self,
        verify_ssl: bool = True,
        timeout: int = 30,
        user_agent: str = "PyO3-API-Benchmark/1.0"
    ):
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.user_agent = user_agent
        self._setup_ssl_context()

    def _setup_ssl_context(self) -> None:
        """Setup SSL context"""
        if not self.verify_ssl:
            # WARNING: Disabling SSL verification for benchmarking only - NOT FOR PRODUCTION
            self.ssl_context = ssl._create_unverified_context()
        else:
            self.ssl_context = ssl.create_default_context()

    def execute_request(self, request: urllib.request.Request) -> RequestResult:
        """Execute a single request and measure performance"""
        start_time = time.time()

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
                context=self.ssl_context
            ) as response:
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000

                body = response.read()

                return RequestResult(
                    latency_ms=latency_ms,
                    status_code=response.status,
                    response_size_bytes=len(body),
                    success=True,
                    timestamp=start_time
                )

        except urllib.error.HTTPError as e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            return RequestResult(
                latency_ms=latency_ms,
                status_code=e.code,
                response_size_bytes=0,
                success=False,
                timestamp=start_time,
                error=f"HTTP {e.code}: {e.reason}"
            )

        except Exception as e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            return RequestResult(
                latency_ms=latency_ms,
                status_code=0,
                response_size_bytes=0,
                success=False,
                timestamp=start_time,
                error=str(e)
            )

    def benchmark(
        self,
        request_builder: RequestBuilder,
        total_requests: int,
        concurrent_workers: int = 1
    ) -> BenchmarkResult:
        """Run benchmark with specified concurrency"""
        results: List[RequestResult] = []
        start_time = datetime.now()

        if concurrent_workers == 1:
            # Sequential execution
            for i in range(total_requests):
                request = request_builder.build_request(i)
                result = self.execute_request(request)
                results.append(result)
        else:
            # Concurrent execution
            with ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
                futures = []

                for i in range(total_requests):
                    request = request_builder.build_request(i)
                    future = executor.submit(self.execute_request, request)
                    futures.append(future)

                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)

        end_time = datetime.now()
        duration_s = (end_time - start_time).total_seconds()

        # Calculate statistics
        latency_stats = self._calculate_latency_stats(results)
        throughput_stats = self._calculate_throughput_stats(results, duration_s)

        return BenchmarkResult(
            endpoint=request_builder.url,
            method=request_builder.method,
            total_requests=total_requests,
            concurrent_workers=concurrent_workers,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_s=duration_s,
            latency=latency_stats,
            throughput=throughput_stats,
            results=results
        )

    def load_test(
        self,
        request_builder: RequestBuilder,
        duration_s: int,
        concurrent_workers: int
    ) -> BenchmarkResult:
        """Run load test for specified duration"""
        results: List[RequestResult] = []
        start_time = datetime.now()
        end_time_target = start_time + timedelta(seconds=duration_s)

        iteration = 0

        with ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            futures = []

            while datetime.now() < end_time_target:
                request = request_builder.build_request(iteration)
                future = executor.submit(self.execute_request, request)
                futures.append(future)
                iteration += 1

            # Wait for all requests to complete
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        end_time = datetime.now()
        actual_duration_s = (end_time - start_time).total_seconds()

        # Calculate statistics
        latency_stats = self._calculate_latency_stats(results)
        throughput_stats = self._calculate_throughput_stats(results, actual_duration_s)

        return BenchmarkResult(
            endpoint=request_builder.url,
            method=request_builder.method,
            total_requests=len(results),
            concurrent_workers=concurrent_workers,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_s=actual_duration_s,
            latency=latency_stats,
            throughput=throughput_stats,
            results=results
        )

    def _calculate_latency_stats(self, results: List[RequestResult]) -> LatencyStats:
        """Calculate latency statistics"""
        if not results:
            return LatencyStats(0, 0, 0, 0, 0, 0, 0, 0)

        latencies = [r.latency_ms for r in results]
        latencies_sorted = sorted(latencies)

        n = len(latencies_sorted)
        p50_idx = int(n * 0.50)
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)

        return LatencyStats(
            min_ms=min(latencies),
            max_ms=max(latencies),
            mean_ms=statistics.mean(latencies),
            median_ms=statistics.median(latencies),
            p50_ms=latencies_sorted[p50_idx],
            p95_ms=latencies_sorted[p95_idx],
            p99_ms=latencies_sorted[p99_idx],
            stddev_ms=statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        )

    def _calculate_throughput_stats(
        self,
        results: List[RequestResult],
        duration_s: float
    ) -> ThroughputStats:
        """Calculate throughput statistics"""
        if not results:
            return ThroughputStats(0, 0, 0, 0.0, 0.0, 0.0, 0.0)

        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful
        success_rate = successful / total if total > 0 else 0.0

        rps = total / duration_s if duration_s > 0 else 0.0
        avg_size = statistics.mean(r.response_size_bytes for r in results)

        return ThroughputStats(
            total_requests=total,
            successful_requests=successful,
            failed_requests=failed,
            success_rate=success_rate,
            total_time_s=duration_s,
            requests_per_second=rps,
            avg_response_size_bytes=avg_size
        )


class BenchmarkAnalyzer:
    """Analyze benchmark results"""

    def analyze(self, result: BenchmarkResult) -> Dict[str, Any]:
        """Analyze benchmark result"""
        analysis = {
            "summary": {
                "endpoint": result.endpoint,
                "method": result.method,
                "total_requests": result.total_requests,
                "duration_s": result.duration_s,
                "success_rate": result.throughput.success_rate
            },
            "latency": {
                "min_ms": result.latency.min_ms,
                "max_ms": result.latency.max_ms,
                "mean_ms": result.latency.mean_ms,
                "median_ms": result.latency.median_ms,
                "p95_ms": result.latency.p95_ms,
                "p99_ms": result.latency.p99_ms,
                "stddev_ms": result.latency.stddev_ms
            },
            "throughput": {
                "requests_per_second": result.throughput.requests_per_second,
                "successful_requests": result.throughput.successful_requests,
                "failed_requests": result.throughput.failed_requests
            },
            "recommendations": self._generate_recommendations(result)
        }

        return analysis

    def compare(
        self,
        baseline: BenchmarkResult,
        current: BenchmarkResult
    ) -> Dict[str, Any]:
        """Compare two benchmark results"""
        latency_change = (
            (current.latency.mean_ms - baseline.latency.mean_ms) /
            baseline.latency.mean_ms * 100
        )

        throughput_change = (
            (current.throughput.requests_per_second - baseline.throughput.requests_per_second) /
            baseline.throughput.requests_per_second * 100
        )

        p95_change = (
            (current.latency.p95_ms - baseline.latency.p95_ms) /
            baseline.latency.p95_ms * 100
        )

        comparison = {
            "summary": {
                "baseline_endpoint": baseline.endpoint,
                "current_endpoint": current.endpoint,
                "baseline_requests": baseline.total_requests,
                "current_requests": current.total_requests
            },
            "latency_comparison": {
                "baseline_mean_ms": baseline.latency.mean_ms,
                "current_mean_ms": current.latency.mean_ms,
                "change_percent": latency_change,
                "baseline_p95_ms": baseline.latency.p95_ms,
                "current_p95_ms": current.latency.p95_ms,
                "p95_change_percent": p95_change
            },
            "throughput_comparison": {
                "baseline_rps": baseline.throughput.requests_per_second,
                "current_rps": current.throughput.requests_per_second,
                "change_percent": throughput_change
            },
            "verdict": self._generate_verdict(latency_change, throughput_change)
        }

        return comparison

    def _generate_recommendations(self, result: BenchmarkResult) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []

        # Check success rate
        if result.throughput.success_rate < 0.95:
            recommendations.append(
                f"Low success rate ({result.throughput.success_rate:.1%}). "
                "Check error logs and server capacity."
            )

        # Check latency variance
        if result.latency.stddev_ms > result.latency.mean_ms:
            recommendations.append(
                "High latency variance detected. Consider connection pooling "
                "or caching to stabilize response times."
            )

        # Check p99 latency
        if result.latency.p99_ms > result.latency.mean_ms * 3:
            recommendations.append(
                "P99 latency is significantly higher than mean. "
                "Investigate tail latencies and optimize slow queries."
            )

        # Check throughput
        if result.throughput.requests_per_second < 100:
            recommendations.append(
                "Low throughput detected. Consider PyO3 optimizations, "
                "connection pooling, or horizontal scaling."
            )

        if not recommendations:
            recommendations.append("Performance looks good!")

        return recommendations

    def _generate_verdict(
        self,
        latency_change: float,
        throughput_change: float
    ) -> str:
        """Generate performance comparison verdict"""
        if latency_change < -5 and throughput_change > 5:
            return "IMPROVED: Lower latency and higher throughput"
        elif latency_change > 10 or throughput_change < -10:
            return "DEGRADED: Performance regression detected"
        else:
            return "STABLE: No significant performance change"


class ResultFormatter:
    """Format benchmark results for output"""

    def format_text(self, result: BenchmarkResult) -> str:
        """Format results as human-readable text"""
        lines = [
            "=" * 80,
            "API BENCHMARK RESULTS",
            "=" * 80,
            "",
            f"Endpoint:        {result.endpoint}",
            f"Method:          {result.method}",
            f"Total Requests:  {result.total_requests}",
            f"Concurrent:      {result.concurrent_workers}",
            f"Duration:        {result.duration_s:.2f}s",
            "",
            "LATENCY STATISTICS",
            "-" * 80,
            f"Min:             {result.latency.min_ms:.2f}ms",
            f"Max:             {result.latency.max_ms:.2f}ms",
            f"Mean:            {result.latency.mean_ms:.2f}ms",
            f"Median:          {result.latency.median_ms:.2f}ms",
            f"P95:             {result.latency.p95_ms:.2f}ms",
            f"P99:             {result.latency.p99_ms:.2f}ms",
            f"Std Dev:         {result.latency.stddev_ms:.2f}ms",
            "",
            "THROUGHPUT STATISTICS",
            "-" * 80,
            f"Successful:      {result.throughput.successful_requests}",
            f"Failed:          {result.throughput.failed_requests}",
            f"Success Rate:    {result.throughput.success_rate:.1%}",
            f"Requests/sec:    {result.throughput.requests_per_second:.2f}",
            f"Avg Size:        {result.throughput.avg_response_size_bytes:.0f} bytes",
            "=" * 80
        ]

        return "\n".join(lines)

    def format_json(self, result: BenchmarkResult, include_results: bool = False) -> str:
        """Format results as JSON"""
        data = {
            "endpoint": result.endpoint,
            "method": result.method,
            "total_requests": result.total_requests,
            "concurrent_workers": result.concurrent_workers,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "duration_s": result.duration_s,
            "latency": asdict(result.latency),
            "throughput": asdict(result.throughput)
        }

        if include_results:
            data["results"] = [asdict(r) for r in result.results]

        return json.dumps(data, indent=2)

    def format_comparison_text(self, comparison: Dict[str, Any]) -> str:
        """Format comparison results as text"""
        lines = [
            "=" * 80,
            "BENCHMARK COMPARISON",
            "=" * 80,
            "",
            f"Baseline:        {comparison['summary']['baseline_endpoint']}",
            f"Current:         {comparison['summary']['current_endpoint']}",
            "",
            "LATENCY COMPARISON",
            "-" * 80,
            f"Baseline Mean:   {comparison['latency_comparison']['baseline_mean_ms']:.2f}ms",
            f"Current Mean:    {comparison['latency_comparison']['current_mean_ms']:.2f}ms",
            f"Change:          {comparison['latency_comparison']['change_percent']:+.1f}%",
            "",
            f"Baseline P95:    {comparison['latency_comparison']['baseline_p95_ms']:.2f}ms",
            f"Current P95:     {comparison['latency_comparison']['current_p95_ms']:.2f}ms",
            f"Change:          {comparison['latency_comparison']['p95_change_percent']:+.1f}%",
            "",
            "THROUGHPUT COMPARISON",
            "-" * 80,
            f"Baseline RPS:    {comparison['throughput_comparison']['baseline_rps']:.2f}",
            f"Current RPS:     {comparison['throughput_comparison']['current_rps']:.2f}",
            f"Change:          {comparison['throughput_comparison']['change_percent']:+.1f}%",
            "",
            f"VERDICT: {comparison['verdict']}",
            "=" * 80
        ]

        return "\n".join(lines)


def load_benchmark_result(file_path: str) -> BenchmarkResult:
    """Load benchmark result from JSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Reconstruct dataclass objects
    latency = LatencyStats(**data['latency'])
    throughput = ThroughputStats(**data['throughput'])

    results = []
    if 'results' in data:
        results = [RequestResult(**r) for r in data['results']]

    return BenchmarkResult(
        endpoint=data['endpoint'],
        method=data['method'],
        total_requests=data['total_requests'],
        concurrent_workers=data['concurrent_workers'],
        start_time=data['start_time'],
        end_time=data['end_time'],
        duration_s=data['duration_s'],
        latency=latency,
        throughput=throughput,
        results=results
    )


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Run benchmark command"""
    # Parse headers
    headers = {}
    if args.headers:
        for header in args.headers:
            key, value = header.split(':', 1)
            headers[key.strip()] = value.strip()

    # Create request builder
    request_builder = RequestBuilder(
        url=args.url,
        method=args.method,
        headers=headers,
        body_template=args.body,
        auth_token=args.auth_token
    )

    # Create benchmark
    benchmark = APIBenchmark(
        verify_ssl=not args.no_verify_ssl,
        timeout=args.timeout
    )

    # Run benchmark
    print(f"Running benchmark: {args.requests} requests, {args.concurrent} concurrent workers...")
    result = benchmark.benchmark(
        request_builder,
        total_requests=args.requests,
        concurrent_workers=args.concurrent
    )

    # Format output
    formatter = ResultFormatter()

    if args.json:
        output = formatter.format_json(result, include_results=args.include_results)
    else:
        output = formatter.format_text(result)

    print(output)

    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(formatter.format_json(result, include_results=True))
        print(f"\nResults saved to: {args.output}")

    return 0


def cmd_load_test(args: argparse.Namespace) -> int:
    """Run load test command"""
    # Parse headers
    headers = {}
    if args.headers:
        for header in args.headers:
            key, value = header.split(':', 1)
            headers[key.strip()] = value.strip()

    # Create request builder
    request_builder = RequestBuilder(
        url=args.url,
        method=args.method,
        headers=headers,
        body_template=args.body,
        auth_token=args.auth_token
    )

    # Create benchmark
    benchmark = APIBenchmark(
        verify_ssl=not args.no_verify_ssl,
        timeout=args.timeout
    )

    # Run load test
    print(f"Running load test: {args.duration}s duration, {args.concurrent} concurrent workers...")
    result = benchmark.load_test(
        request_builder,
        duration_s=args.duration,
        concurrent_workers=args.concurrent
    )

    # Format output
    formatter = ResultFormatter()

    if args.json:
        output = formatter.format_json(result, include_results=args.include_results)
    else:
        output = formatter.format_text(result)

    print(output)

    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(formatter.format_json(result, include_results=True))
        print(f"\nResults saved to: {args.output}")

    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Run analyze command"""
    result = load_benchmark_result(args.file)

    analyzer = BenchmarkAnalyzer()
    analysis = analyzer.analyze(result)

    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        print("=" * 80)
        print("BENCHMARK ANALYSIS")
        print("=" * 80)
        print()

        print("SUMMARY")
        print("-" * 80)
        for key, value in analysis['summary'].items():
            print(f"{key:20s} {value}")
        print()

        print("RECOMMENDATIONS")
        print("-" * 80)
        for rec in analysis['recommendations']:
            print(f"- {rec}")
        print("=" * 80)

    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Run compare command"""
    baseline = load_benchmark_result(args.baseline)
    current = load_benchmark_result(args.current)

    analyzer = BenchmarkAnalyzer()
    comparison = analyzer.compare(baseline, current)

    formatter = ResultFormatter()

    if args.json:
        print(json.dumps(comparison, indent=2))
    else:
        print(formatter.format_comparison_text(comparison))

    return 0


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Benchmark API endpoints for PyO3 web frameworks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Benchmark command
    benchmark_parser = subparsers.add_parser(
        'benchmark',
        help='Run performance benchmark'
    )
    benchmark_parser.add_argument(
        'url',
        help='API endpoint URL to benchmark'
    )
    benchmark_parser.add_argument(
        '--requests', '-n',
        type=int,
        default=1000,
        help='Total number of requests (default: 1000)'
    )
    benchmark_parser.add_argument(
        '--concurrent', '-c',
        type=int,
        default=1,
        help='Number of concurrent workers (default: 1)'
    )
    benchmark_parser.add_argument(
        '--method', '-X',
        default='GET',
        help='HTTP method (default: GET)'
    )
    benchmark_parser.add_argument(
        '--headers', '-H',
        action='append',
        help='Custom header (format: "Key: Value")'
    )
    benchmark_parser.add_argument(
        '--body', '-d',
        help='Request body template (use {iteration}, {timestamp})'
    )
    benchmark_parser.add_argument(
        '--auth-token',
        help='Bearer authentication token'
    )
    benchmark_parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    benchmark_parser.add_argument(
        '--no-verify-ssl',
        action='store_true',
        help='Disable SSL certificate verification'
    )
    benchmark_parser.add_argument(
        '--output', '-o',
        help='Save results to JSON file'
    )
    benchmark_parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    benchmark_parser.add_argument(
        '--include-results',
        action='store_true',
        help='Include individual request results in JSON output'
    )

    # Load test command
    load_test_parser = subparsers.add_parser(
        'load-test',
        help='Run load test for specified duration'
    )
    load_test_parser.add_argument(
        'url',
        help='API endpoint URL to test'
    )
    load_test_parser.add_argument(
        '--duration', '-t',
        type=int,
        default=60,
        help='Test duration in seconds (default: 60)'
    )
    load_test_parser.add_argument(
        '--concurrent', '-c',
        type=int,
        default=10,
        help='Number of concurrent workers (default: 10)'
    )
    load_test_parser.add_argument(
        '--method', '-X',
        default='GET',
        help='HTTP method (default: GET)'
    )
    load_test_parser.add_argument(
        '--headers', '-H',
        action='append',
        help='Custom header (format: "Key: Value")'
    )
    load_test_parser.add_argument(
        '--body', '-d',
        help='Request body template (use {iteration}, {timestamp})'
    )
    load_test_parser.add_argument(
        '--auth-token',
        help='Bearer authentication token'
    )
    load_test_parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    load_test_parser.add_argument(
        '--no-verify-ssl',
        action='store_true',
        help='Disable SSL certificate verification'
    )
    load_test_parser.add_argument(
        '--output', '-o',
        help='Save results to JSON file'
    )
    load_test_parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    load_test_parser.add_argument(
        '--include-results',
        action='store_true',
        help='Include individual request results in JSON output'
    )

    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze benchmark results'
    )
    analyze_parser.add_argument(
        'file',
        help='Benchmark results JSON file'
    )
    analyze_parser.add_argument(
        '--json',
        action='store_true',
        help='Output analysis as JSON'
    )

    # Compare command
    compare_parser = subparsers.add_parser(
        'compare',
        help='Compare two benchmark results'
    )
    compare_parser.add_argument(
        'baseline',
        help='Baseline benchmark results JSON file'
    )
    compare_parser.add_argument(
        'current',
        help='Current benchmark results JSON file'
    )
    compare_parser.add_argument(
        '--json',
        action='store_true',
        help='Output comparison as JSON'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'benchmark':
            return cmd_benchmark(args)
        elif args.command == 'load-test':
            return cmd_load_test(args)
        elif args.command == 'analyze':
            return cmd_analyze(args)
        elif args.command == 'compare':
            return cmd_compare(args)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
