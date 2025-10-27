#!/usr/bin/env python3
"""
Elasticsearch Search Benchmark Tool

Benchmarks Elasticsearch query performance with statistical analysis.
Tests different query types and measures latency, throughput, and resource usage.

Usage:
    ./benchmark_search.py --query-file queries.json
    ./benchmark_search.py --query '{"query": {"match_all": {}}}' --iterations 100
    ./benchmark_search.py --query-file queries.json --concurrent-requests 5
    ./benchmark_search.py --query-file queries.json --json
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics


@dataclass
class QueryResult:
    """Single query execution result"""
    latency_ms: float
    took_ms: int
    hits: int
    success: bool
    error: Optional[str] = None


@dataclass
class BenchmarkStats:
    """Statistical analysis of benchmark results"""
    total_queries: int
    successful: int
    failed: int
    success_rate: float
    total_time_s: float
    queries_per_second: float
    latency_min_ms: float
    latency_max_ms: float
    latency_mean_ms: float
    latency_median_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_stddev_ms: float


@dataclass
class BenchmarkResult:
    """Complete benchmark results"""
    query_name: str
    query: Dict[str, Any]
    iterations: int
    concurrent_requests: int
    stats: BenchmarkStats
    results: List[QueryResult] = field(default_factory=list)


class ElasticsearchBenchmark:
    """Benchmark Elasticsearch queries"""

    def __init__(self, endpoint: str, index: str):
        self.endpoint = endpoint.rstrip("/")
        self.index = index

    def execute_query(self, query: Dict[str, Any]) -> QueryResult:
        """Execute a single query and measure performance"""
        url = f"{self.endpoint}/{self.index}/_search"

        start_time = time.time()
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(query).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000

                result = json.loads(response.read().decode())
                took_ms = result.get("took", 0)
                hits = result["hits"]["total"]["value"] if isinstance(result["hits"]["total"], dict) else result["hits"]["total"]

                return QueryResult(
                    latency_ms=latency_ms,
                    took_ms=took_ms,
                    hits=hits,
                    success=True
                )

        except Exception as e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            return QueryResult(
                latency_ms=latency_ms,
                took_ms=0,
                hits=0,
                success=False,
                error=str(e)
            )

    def benchmark_query(
        self,
        query: Dict[str, Any],
        iterations: int = 100,
        concurrent_requests: int = 1
    ) -> BenchmarkResult:
        """Benchmark a query with multiple iterations"""
        results = []
        start_time = time.time()

        if concurrent_requests == 1:
            # Sequential execution
            for _ in range(iterations):
                result = self.execute_query(query)
                results.append(result)
        else:
            # Concurrent execution
            with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
                futures = [
                    executor.submit(self.execute_query, query)
                    for _ in range(iterations)
                ]
                for future in as_completed(futures):
                    results.append(future.result())

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate statistics
        stats = self._calculate_stats(results, total_time)

        return BenchmarkResult(
            query_name="",
            query=query,
            iterations=iterations,
            concurrent_requests=concurrent_requests,
            stats=stats,
            results=results
        )

    def _calculate_stats(self, results: List[QueryResult], total_time: float) -> BenchmarkStats:
        """Calculate statistical metrics"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        if not successful:
            return BenchmarkStats(
                total_queries=len(results),
                successful=0,
                failed=len(failed),
                success_rate=0.0,
                total_time_s=total_time,
                queries_per_second=0.0,
                latency_min_ms=0.0,
                latency_max_ms=0.0,
                latency_mean_ms=0.0,
                latency_median_ms=0.0,
                latency_p95_ms=0.0,
                latency_p99_ms=0.0,
                latency_stddev_ms=0.0
            )

        latencies = [r.latency_ms for r in successful]
        latencies_sorted = sorted(latencies)

        return BenchmarkStats(
            total_queries=len(results),
            successful=len(successful),
            failed=len(failed),
            success_rate=len(successful) / len(results) * 100,
            total_time_s=total_time,
            queries_per_second=len(successful) / total_time if total_time > 0 else 0,
            latency_min_ms=min(latencies),
            latency_max_ms=max(latencies),
            latency_mean_ms=statistics.mean(latencies),
            latency_median_ms=statistics.median(latencies),
            latency_p95_ms=self._percentile(latencies_sorted, 95),
            latency_p99_ms=self._percentile(latencies_sorted, 99),
            latency_stddev_ms=statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        )

    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0.0
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


def format_text_output(results: List[BenchmarkResult]) -> str:
    """Format results as human-readable text"""
    output = []

    for result in results:
        output.append(f"\n{'='*80}")
        output.append(f"Query: {result.query_name}")
        output.append(f"Iterations: {result.iterations}")
        output.append(f"Concurrent Requests: {result.concurrent_requests}")
        output.append(f"{'='*80}\n")

        stats = result.stats

        output.append("EXECUTION SUMMARY:")
        output.append(f"  Total Queries: {stats.total_queries}")
        output.append(f"  Successful: {stats.successful}")
        output.append(f"  Failed: {stats.failed}")
        output.append(f"  Success Rate: {stats.success_rate:.2f}%")
        output.append(f"  Total Time: {stats.total_time_s:.2f}s")
        output.append(f"  Throughput: {stats.queries_per_second:.2f} queries/sec")
        output.append("")

        if stats.successful > 0:
            output.append("LATENCY STATISTICS (ms):")
            output.append(f"  Min: {stats.latency_min_ms:.2f}")
            output.append(f"  Max: {stats.latency_max_ms:.2f}")
            output.append(f"  Mean: {stats.latency_mean_ms:.2f}")
            output.append(f"  Median (p50): {stats.latency_median_ms:.2f}")
            output.append(f"  p95: {stats.latency_p95_ms:.2f}")
            output.append(f"  p99: {stats.latency_p99_ms:.2f}")
            output.append(f"  Std Dev: {stats.latency_stddev_ms:.2f}")
            output.append("")

            # Performance assessment
            if stats.latency_p95_ms < 100:
                performance = "Excellent"
            elif stats.latency_p95_ms < 500:
                performance = "Good"
            elif stats.latency_p95_ms < 1000:
                performance = "Acceptable"
            else:
                performance = "Poor"

            output.append(f"PERFORMANCE ASSESSMENT: {performance}")
            output.append("")

        if stats.failed > 0:
            output.append("ERRORS:")
            error_samples = [r for r in result.results if not r.success][:5]
            for i, error_result in enumerate(error_samples, 1):
                output.append(f"  {i}. {error_result.error}")
            if len(error_samples) < stats.failed:
                output.append(f"  ... and {stats.failed - len(error_samples)} more errors")
            output.append("")

    return "\n".join(output)


def format_json_output(results: List[BenchmarkResult]) -> str:
    """Format results as JSON"""
    output = []
    for result in results:
        stats = result.stats
        output.append({
            "query_name": result.query_name,
            "query": result.query,
            "iterations": result.iterations,
            "concurrent_requests": result.concurrent_requests,
            "summary": {
                "total_queries": stats.total_queries,
                "successful": stats.successful,
                "failed": stats.failed,
                "success_rate": stats.success_rate,
                "total_time_seconds": stats.total_time_s,
                "queries_per_second": stats.queries_per_second
            },
            "latency_ms": {
                "min": stats.latency_min_ms,
                "max": stats.latency_max_ms,
                "mean": stats.latency_mean_ms,
                "median": stats.latency_median_ms,
                "p95": stats.latency_p95_ms,
                "p99": stats.latency_p99_ms,
                "stddev": stats.latency_stddev_ms
            },
            "errors": [
                {"latency_ms": r.latency_ms, "error": r.error}
                for r in result.results if not r.success
            ]
        })
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Elasticsearch query performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Benchmark query from file
  ./benchmark_search.py --query-file queries.json --index products

  # Benchmark single query
  ./benchmark_search.py --query '{"query": {"match_all": {}}}' --index products

  # Custom iterations and concurrency
  ./benchmark_search.py --query-file queries.json --iterations 500 --concurrent-requests 10

  # JSON output
  ./benchmark_search.py --query-file queries.json --json

  # Specify endpoint
  ./benchmark_search.py --query-file queries.json --endpoint http://localhost:9200 --index products
        """
    )

    parser.add_argument(
        "--query",
        help="Query JSON string to benchmark"
    )
    parser.add_argument(
        "--query-file",
        help="Path to file containing query or queries (JSON)"
    )
    parser.add_argument(
        "--index",
        default="_all",
        help="Index to search (default: _all)"
    )
    parser.add_argument(
        "--endpoint",
        default="http://localhost:9200",
        help="Elasticsearch endpoint (default: http://localhost:9200)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of iterations per query (default: 100)"
    )
    parser.add_argument(
        "--concurrent-requests",
        type=int,
        default=1,
        help="Number of concurrent requests (default: 1)"
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=10,
        help="Number of warmup iterations (default: 10)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    if not args.query and not args.query_file:
        parser.error("Either --query or --query-file must be specified")

    # Load queries
    queries = []
    try:
        if args.query:
            query_data = json.loads(args.query)
            queries.append(("command_line_query", query_data))
        elif args.query_file:
            with open(args.query_file, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for i, q in enumerate(data):
                        queries.append((f"query_{i+1}", q))
                elif isinstance(data, dict):
                    if "query" in data or "aggs" in data or "aggregations" in data:
                        queries.append(("query", data))
                    else:
                        for name, query in data.items():
                            queries.append((name, query))
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File not found: {args.query_file}", file=sys.stderr)
        sys.exit(1)

    # Initialize benchmark
    benchmark = ElasticsearchBenchmark(args.endpoint, args.index)

    # Warmup
    if args.warmup > 0 and queries:
        if not args.json:
            print(f"Warming up with {args.warmup} requests...", file=sys.stderr)
        for _ in range(args.warmup):
            benchmark.execute_query(queries[0][1])

    # Benchmark queries
    results = []
    for name, query in queries:
        if not args.json:
            print(f"Benchmarking {name}...", file=sys.stderr)

        result = benchmark.benchmark_query(
            query,
            iterations=args.iterations,
            concurrent_requests=args.concurrent_requests
        )
        result.query_name = name
        results.append(result)

    # Output results
    if args.json:
        print(format_json_output(results))
    else:
        print(format_text_output(results))


if __name__ == "__main__":
    main()
