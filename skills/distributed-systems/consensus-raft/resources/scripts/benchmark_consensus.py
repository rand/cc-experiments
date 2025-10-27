#!/usr/bin/env python3
"""benchmark_consensus.py - Measure RAFT consensus latency and throughput

Usage:
    ./benchmark_consensus.py [options]

Options:
    --endpoints HOST:PORT,...  Comma-separated etcd endpoints (default: localhost:2379)
    --operations N             Number of operations (default: 1000)
    --concurrency N            Number of concurrent clients (default: 10)
    --key-size N               Size of keys in bytes (default: 32)
    --value-size N             Size of values in bytes (default: 256)
    --json                     Output JSON format
    --help                     Show this help message

Examples:
    # Basic benchmark
    ./benchmark_consensus.py --operations 1000

    # Benchmark with custom endpoints
    ./benchmark_consensus.py --endpoints localhost:2379,localhost:2380,localhost:2381

    # High concurrency test
    ./benchmark_consensus.py --operations 10000 --concurrency 100 --json
"""

import argparse
import json
import random
import string
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Tuple

try:
    import etcd3
except ImportError:
    print("Error: etcd3 library not installed", file=sys.stderr)
    print("Install with: pip install etcd3-py", file=sys.stderr)
    sys.exit(1)


@dataclass
class BenchmarkResult:
    """Results from a single operation"""
    operation: str
    latency_ms: float
    success: bool
    error: str = ""


@dataclass
class BenchmarkStats:
    """Aggregated benchmark statistics"""
    operation: str
    total_ops: int
    successful_ops: int
    failed_ops: int
    min_latency_ms: float
    max_latency_ms: float
    mean_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_ops_per_sec: float
    duration_sec: float


class ConsensusEtcdBenchmark:
    """Benchmark RAFT consensus using etcd"""

    def __init__(self, endpoints: List[str], key_size: int, value_size: int):
        """Initialize benchmark

        Args:
            endpoints: List of etcd endpoints (host:port)
            key_size: Size of keys in bytes
            value_size: Size of values in bytes
        """
        self.endpoints = endpoints
        self.key_size = key_size
        self.value_size = value_size

        # Parse first endpoint
        host, port = endpoints[0].split(":")
        self.client = etcd3.client(host=host, port=int(port))

    def generate_random_string(self, size: int) -> str:
        """Generate random string of given size"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=size))

    def benchmark_put(self, key: str, value: str) -> BenchmarkResult:
        """Benchmark a single PUT operation"""
        start = time.time()
        try:
            self.client.put(key, value)
            latency_ms = (time.time() - start) * 1000
            return BenchmarkResult("put", latency_ms, True)
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return BenchmarkResult("put", latency_ms, False, str(e))

    def benchmark_get(self, key: str) -> BenchmarkResult:
        """Benchmark a single GET operation"""
        start = time.time()
        try:
            self.client.get(key)
            latency_ms = (time.time() - start) * 1000
            return BenchmarkResult("get", latency_ms, True)
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return BenchmarkResult("get", latency_ms, False, str(e))

    def benchmark_transaction(self, key: str, value: str) -> BenchmarkResult:
        """Benchmark a transaction operation"""
        start = time.time()
        try:
            # Compare-and-swap transaction
            self.client.transaction(
                compare=[self.client.transactions.version(key) > -1],
                success=[self.client.transactions.put(key, value)],
                failure=[]
            )
            latency_ms = (time.time() - start) * 1000
            return BenchmarkResult("transaction", latency_ms, True)
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return BenchmarkResult("transaction", latency_ms, False, str(e))

    def run_workload(self, operations: int, concurrency: int) -> Tuple[List[BenchmarkResult], List[BenchmarkResult], List[BenchmarkResult]]:
        """Run mixed workload benchmark

        Args:
            operations: Total number of operations
            concurrency: Number of concurrent workers

        Returns:
            Tuple of (put_results, get_results, txn_results)
        """
        put_results = []
        get_results = []
        txn_results = []

        # Pre-generate keys and values
        keys = [f"bench-key-{self.generate_random_string(self.key_size)}"
                for _ in range(operations)]
        values = [self.generate_random_string(self.value_size)
                  for _ in range(operations)]

        # Phase 1: PUT operations
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = []
            for i in range(operations):
                future = executor.submit(self.benchmark_put, keys[i], values[i])
                futures.append(future)

            for future in as_completed(futures):
                put_results.append(future.result())

        # Phase 2: GET operations
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = []
            for i in range(operations):
                future = executor.submit(self.benchmark_get, keys[i])
                futures.append(future)

            for future in as_completed(futures):
                get_results.append(future.result())

        # Phase 3: Transaction operations (smaller sample)
        txn_ops = min(operations // 10, 100)
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = []
            for i in range(txn_ops):
                future = executor.submit(self.benchmark_transaction, keys[i], values[i])
                futures.append(future)

            for future in as_completed(futures):
                txn_results.append(future.result())

        return put_results, get_results, txn_results

    @staticmethod
    def calculate_stats(results: List[BenchmarkResult]) -> BenchmarkStats:
        """Calculate statistics from benchmark results"""
        if not results:
            return BenchmarkStats("unknown", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        operation = results[0].operation
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        latencies = sorted([r.latency_ms for r in successful])
        if not latencies:
            return BenchmarkStats(
                operation, len(results), 0, len(failed),
                0, 0, 0, 0, 0, 0, 0, 0
            )

        total_time = sum(latencies) / 1000  # Convert to seconds
        throughput = len(successful) / total_time if total_time > 0 else 0

        # Calculate percentiles
        def percentile(data, p):
            k = (len(data) - 1) * p
            f = int(k)
            c = int(k) + 1 if k < len(data) - 1 else int(k)
            d0 = data[f]
            d1 = data[c]
            return d0 + (d1 - d0) * (k - f)

        return BenchmarkStats(
            operation=operation,
            total_ops=len(results),
            successful_ops=len(successful),
            failed_ops=len(failed),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            mean_latency_ms=sum(latencies) / len(latencies),
            median_latency_ms=percentile(latencies, 0.5),
            p95_latency_ms=percentile(latencies, 0.95),
            p99_latency_ms=percentile(latencies, 0.99),
            throughput_ops_per_sec=throughput,
            duration_sec=total_time
        )


def format_stats(stats: BenchmarkStats, json_output: bool = False) -> str:
    """Format statistics for output"""
    if json_output:
        return json.dumps({
            "operation": stats.operation,
            "total_ops": stats.total_ops,
            "successful_ops": stats.successful_ops,
            "failed_ops": stats.failed_ops,
            "latency": {
                "min_ms": round(stats.min_latency_ms, 2),
                "max_ms": round(stats.max_latency_ms, 2),
                "mean_ms": round(stats.mean_latency_ms, 2),
                "median_ms": round(stats.median_latency_ms, 2),
                "p95_ms": round(stats.p95_latency_ms, 2),
                "p99_ms": round(stats.p99_latency_ms, 2),
            },
            "throughput_ops_per_sec": round(stats.throughput_ops_per_sec, 2),
            "duration_sec": round(stats.duration_sec, 2)
        }, indent=2)
    else:
        return f"""
=== {stats.operation.upper()} Operations ===
Total operations:    {stats.total_ops}
Successful:          {stats.successful_ops}
Failed:              {stats.failed_ops}

Latency (ms):
  Min:      {stats.min_latency_ms:.2f}
  Max:      {stats.max_latency_ms:.2f}
  Mean:     {stats.mean_latency_ms:.2f}
  Median:   {stats.median_latency_ms:.2f}
  P95:      {stats.p95_latency_ms:.2f}
  P99:      {stats.p99_latency_ms:.2f}

Throughput:          {stats.throughput_ops_per_sec:.2f} ops/sec
Duration:            {stats.duration_sec:.2f} sec
"""


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark RAFT consensus latency and throughput",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--endpoints",
        default="localhost:2379",
        help="Comma-separated etcd endpoints (default: localhost:2379)"
    )
    parser.add_argument(
        "--operations",
        type=int,
        default=1000,
        help="Number of operations (default: 1000)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Number of concurrent clients (default: 10)"
    )
    parser.add_argument(
        "--key-size",
        type=int,
        default=32,
        help="Size of keys in bytes (default: 32)"
    )
    parser.add_argument(
        "--value-size",
        type=int,
        default=256,
        help="Size of values in bytes (default: 256)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format"
    )

    args = parser.parse_args()

    # Parse endpoints
    endpoints = [e.strip() for e in args.endpoints.split(",")]

    # Initialize benchmark
    try:
        bench = ConsensusEtcdBenchmark(endpoints, args.key_size, args.value_size)
    except Exception as e:
        print(f"Error connecting to etcd: {e}", file=sys.stderr)
        print(f"Make sure etcd is running at {endpoints}", file=sys.stderr)
        sys.exit(1)

    # Run benchmark
    if not args.json:
        print(f"Starting benchmark with {args.operations} operations and {args.concurrency} concurrent clients...")
        print(f"Endpoints: {endpoints}")
        print(f"Key size: {args.key_size} bytes, Value size: {args.value_size} bytes")
        print()

    start_time = time.time()
    put_results, get_results, txn_results = bench.run_workload(args.operations, args.concurrency)
    total_time = time.time() - start_time

    # Calculate statistics
    put_stats = bench.calculate_stats(put_results)
    get_stats = bench.calculate_stats(get_results)
    txn_stats = bench.calculate_stats(txn_results)

    # Output results
    if args.json:
        output = {
            "config": {
                "endpoints": endpoints,
                "operations": args.operations,
                "concurrency": args.concurrency,
                "key_size": args.key_size,
                "value_size": args.value_size
            },
            "results": {
                "put": json.loads(format_stats(put_stats, json_output=True)),
                "get": json.loads(format_stats(get_stats, json_output=True)),
                "transaction": json.loads(format_stats(txn_stats, json_output=True))
            },
            "total_duration_sec": round(total_time, 2)
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_stats(put_stats))
        print(format_stats(get_stats))
        print(format_stats(txn_stats))
        print(f"\nTotal benchmark duration: {total_time:.2f} sec")


if __name__ == "__main__":
    main()
