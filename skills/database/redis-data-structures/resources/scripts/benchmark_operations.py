#!/usr/bin/env python3
"""
Redis Operations Benchmark

Benchmarks different Redis data structures and operations to measure performance.
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Callable

try:
    import redis
except ImportError:
    print("Error: redis package required. Install with: pip install redis", file=sys.stderr)
    sys.exit(1)


@dataclass
class BenchmarkResult:
    """Result from a benchmark run."""
    operation: str
    iterations: int
    total_time: float
    ops_per_sec: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


class RedisBenchmark:
    """Benchmarks Redis operations."""

    def __init__(self, host: str = 'localhost', port: int = 6379,
                 password: Optional[str] = None, db: int = 0):
        """Initialize Redis connection."""
        self.client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True
        )
        self.binary_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=False
        )

    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile from sorted data."""
        if not data:
            return 0.0
        size = len(data)
        index = int(size * percentile / 100)
        return data[min(index, size - 1)]

    def _run_benchmark(self, name: str, operation: Callable, iterations: int,
                      setup: Optional[Callable] = None,
                      cleanup: Optional[Callable] = None) -> BenchmarkResult:
        """
        Run a benchmark operation.

        Args:
            name: Benchmark name
            operation: Function to benchmark
            iterations: Number of iterations
            setup: Optional setup function
            cleanup: Optional cleanup function

        Returns:
            BenchmarkResult with statistics
        """
        if setup:
            setup()

        latencies = []
        start_time = time.time()

        for i in range(iterations):
            op_start = time.time()
            operation(i)
            op_end = time.time()
            latencies.append((op_end - op_start) * 1000)  # Convert to ms

        end_time = time.time()
        total_time = end_time - start_time

        if cleanup:
            cleanup()

        # Sort for percentile calculation
        latencies.sort()

        return BenchmarkResult(
            operation=name,
            iterations=iterations,
            total_time=total_time,
            ops_per_sec=iterations / total_time if total_time > 0 else 0,
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p50_latency_ms=self._percentile(latencies, 50),
            p95_latency_ms=self._percentile(latencies, 95),
            p99_latency_ms=self._percentile(latencies, 99)
        )

    def benchmark_strings(self, iterations: int) -> List[BenchmarkResult]:
        """Benchmark string operations."""
        results = []

        # SET
        results.append(self._run_benchmark(
            "String SET",
            lambda i: self.client.set(f"bench:str:{i}", f"value{i}"),
            iterations,
            cleanup=lambda: self.client.delete(*[f"bench:str:{i}" for i in range(iterations)])
        ))

        # GET
        def setup_get():
            for i in range(iterations):
                self.client.set(f"bench:str:{i}", f"value{i}")

        results.append(self._run_benchmark(
            "String GET",
            lambda i: self.client.get(f"bench:str:{i}"),
            iterations,
            setup=setup_get,
            cleanup=lambda: self.client.delete(*[f"bench:str:{i}" for i in range(iterations)])
        ))

        # INCR
        results.append(self._run_benchmark(
            "String INCR",
            lambda i: self.client.incr("bench:counter"),
            iterations,
            cleanup=lambda: self.client.delete("bench:counter")
        ))

        return results

    def benchmark_lists(self, iterations: int) -> List[BenchmarkResult]:
        """Benchmark list operations."""
        results = []

        # LPUSH
        results.append(self._run_benchmark(
            "List LPUSH",
            lambda i: self.client.lpush("bench:list", f"value{i}"),
            iterations,
            cleanup=lambda: self.client.delete("bench:list")
        ))

        # RPUSH
        results.append(self._run_benchmark(
            "List RPUSH",
            lambda i: self.client.rpush("bench:list2", f"value{i}"),
            iterations,
            cleanup=lambda: self.client.delete("bench:list2")
        ))

        # LPOP
        def setup_lpop():
            for i in range(iterations):
                self.client.lpush("bench:list3", f"value{i}")

        results.append(self._run_benchmark(
            "List LPOP",
            lambda i: self.client.lpop("bench:list3"),
            iterations,
            setup=setup_lpop,
            cleanup=lambda: self.client.delete("bench:list3")
        ))

        # LRANGE (small)
        def setup_lrange():
            for i in range(1000):
                self.client.lpush("bench:list4", f"value{i}")

        results.append(self._run_benchmark(
            "List LRANGE (0-99)",
            lambda i: self.client.lrange("bench:list4", 0, 99),
            min(iterations, 1000),
            setup=setup_lrange,
            cleanup=lambda: self.client.delete("bench:list4")
        ))

        return results

    def benchmark_sets(self, iterations: int) -> List[BenchmarkResult]:
        """Benchmark set operations."""
        results = []

        # SADD
        results.append(self._run_benchmark(
            "Set SADD",
            lambda i: self.client.sadd("bench:set", f"member{i}"),
            iterations,
            cleanup=lambda: self.client.delete("bench:set")
        ))

        # SISMEMBER
        def setup_sismember():
            for i in range(iterations):
                self.client.sadd("bench:set2", f"member{i}")

        results.append(self._run_benchmark(
            "Set SISMEMBER",
            lambda i: self.client.sismember("bench:set2", f"member{i}"),
            iterations,
            setup=setup_sismember,
            cleanup=lambda: self.client.delete("bench:set2")
        ))

        # SINTER
        def setup_sinter():
            for i in range(1000):
                self.client.sadd("bench:set3", f"member{i}")
                self.client.sadd("bench:set4", f"member{i + 500}")

        results.append(self._run_benchmark(
            "Set SINTER (2 sets, 1000 members)",
            lambda i: self.client.sinter("bench:set3", "bench:set4"),
            min(iterations, 100),
            setup=setup_sinter,
            cleanup=lambda: self.client.delete("bench:set3", "bench:set4")
        ))

        return results

    def benchmark_sorted_sets(self, iterations: int) -> List[BenchmarkResult]:
        """Benchmark sorted set operations."""
        results = []

        # ZADD
        results.append(self._run_benchmark(
            "Sorted Set ZADD",
            lambda i: self.client.zadd("bench:zset", {f"member{i}": i}),
            iterations,
            cleanup=lambda: self.client.delete("bench:zset")
        ))

        # ZSCORE
        def setup_zscore():
            for i in range(iterations):
                self.client.zadd("bench:zset2", {f"member{i}": i})

        results.append(self._run_benchmark(
            "Sorted Set ZSCORE",
            lambda i: self.client.zscore("bench:zset2", f"member{i}"),
            iterations,
            setup=setup_zscore,
            cleanup=lambda: self.client.delete("bench:zset2")
        ))

        # ZRANGE
        def setup_zrange():
            for i in range(10000):
                self.client.zadd("bench:zset3", {f"member{i}": i})

        results.append(self._run_benchmark(
            "Sorted Set ZRANGE (0-99)",
            lambda i: self.client.zrange("bench:zset3", 0, 99),
            min(iterations, 1000),
            setup=setup_zrange,
            cleanup=lambda: self.client.delete("bench:zset3")
        ))

        # ZRANK
        results.append(self._run_benchmark(
            "Sorted Set ZRANK",
            lambda i: self.client.zrank("bench:zset3", f"member{i % 10000}"),
            min(iterations, 1000),
            setup=setup_zrange,
            cleanup=lambda: self.client.delete("bench:zset3")
        ))

        return results

    def benchmark_hashes(self, iterations: int) -> List[BenchmarkResult]:
        """Benchmark hash operations."""
        results = []

        # HSET
        results.append(self._run_benchmark(
            "Hash HSET",
            lambda i: self.client.hset("bench:hash", f"field{i}", f"value{i}"),
            iterations,
            cleanup=lambda: self.client.delete("bench:hash")
        ))

        # HGET
        def setup_hget():
            for i in range(iterations):
                self.client.hset("bench:hash2", f"field{i}", f"value{i}")

        results.append(self._run_benchmark(
            "Hash HGET",
            lambda i: self.client.hget("bench:hash2", f"field{i}"),
            iterations,
            setup=setup_hget,
            cleanup=lambda: self.client.delete("bench:hash2")
        ))

        # HINCRBY
        results.append(self._run_benchmark(
            "Hash HINCRBY",
            lambda i: self.client.hincrby("bench:hash3", "counter", 1),
            iterations,
            cleanup=lambda: self.client.delete("bench:hash3")
        ))

        # HGETALL
        def setup_hgetall():
            for i in range(100):
                self.client.hset("bench:hash4", f"field{i}", f"value{i}")

        results.append(self._run_benchmark(
            "Hash HGETALL (100 fields)",
            lambda i: self.client.hgetall("bench:hash4"),
            min(iterations, 1000),
            setup=setup_hgetall,
            cleanup=lambda: self.client.delete("bench:hash4")
        ))

        return results

    def benchmark_pipelining(self, iterations: int) -> List[BenchmarkResult]:
        """Benchmark pipelining vs individual commands."""
        results = []

        # Individual SETs
        results.append(self._run_benchmark(
            "Individual SETs (no pipeline)",
            lambda i: self.client.set(f"bench:pipe:{i}", f"value{i}"),
            min(iterations, 1000),
            cleanup=lambda: self.client.delete(*[f"bench:pipe:{i}" for i in range(min(iterations, 1000))])
        ))

        # Pipelined SETs
        def pipelined_sets(i):
            pipe = self.client.pipeline(transaction=False)
            for j in range(100):
                pipe.set(f"bench:pipe2:{i * 100 + j}", f"value{j}")
            pipe.execute()

        results.append(self._run_benchmark(
            "Pipelined SETs (100 per pipeline)",
            pipelined_sets,
            min(iterations // 100, 100),
            cleanup=lambda: [self.client.delete(*[f"bench:pipe2:{i}" for i in range(10000)])]
        ))

        return results

    def benchmark_data_sizes(self, iterations: int) -> List[BenchmarkResult]:
        """Benchmark operations with different data sizes."""
        results = []
        sizes = [64, 256, 1024, 4096, 16384]  # bytes

        for size in sizes:
            value = "x" * size

            results.append(self._run_benchmark(
                f"String SET ({size} bytes)",
                lambda i, v=value: self.client.set(f"bench:size:{i}", v),
                min(iterations, 1000),
                cleanup=lambda: self.client.delete(*[f"bench:size:{i}" for i in range(min(iterations, 1000))])
            ))

            # Setup for GET benchmark
            def setup_get_size(v=value):
                for i in range(min(iterations, 1000)):
                    self.client.set(f"bench:size2:{i}", v)

            results.append(self._run_benchmark(
                f"String GET ({size} bytes)",
                lambda i: self.client.get(f"bench:size2:{i}"),
                min(iterations, 1000),
                setup=setup_get_size,
                cleanup=lambda: self.client.delete(*[f"bench:size2:{i}" for i in range(min(iterations, 1000))])
            ))

        return results

    def run_all_benchmarks(self, iterations: int) -> Dict[str, List[BenchmarkResult]]:
        """Run all benchmark suites."""
        return {
            "strings": self.benchmark_strings(iterations),
            "lists": self.benchmark_lists(iterations),
            "sets": self.benchmark_sets(iterations),
            "sorted_sets": self.benchmark_sorted_sets(iterations),
            "hashes": self.benchmark_hashes(iterations),
            "pipelining": self.benchmark_pipelining(iterations),
            "data_sizes": self.benchmark_data_sizes(iterations)
        }


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark Redis data structures and operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all benchmarks
  %(prog)s

  # Benchmark specific data structure
  %(prog)s --benchmark strings

  # More iterations for better accuracy
  %(prog)s --iterations 10000

  # JSON output
  %(prog)s --json

  # Connect to remote Redis
  %(prog)s --host redis.example.com --port 6380
        """
    )

    # Connection options
    parser.add_argument('--host', default='localhost', help='Redis host (default: localhost)')
    parser.add_argument('--port', type=int, default=6379, help='Redis port (default: 6379)')
    parser.add_argument('--password', help='Redis password')
    parser.add_argument('--db', type=int, default=0, help='Redis database (default: 0)')

    # Benchmark options
    parser.add_argument('--benchmark', choices=['all', 'strings', 'lists', 'sets',
                                                'sorted_sets', 'hashes', 'pipelining',
                                                'data_sizes'],
                       default='all', help='Benchmark to run (default: all)')
    parser.add_argument('--iterations', type=int, default=1000,
                       help='Number of iterations per benchmark (default: 1000)')

    # Output options
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    try:
        benchmark = RedisBenchmark(
            host=args.host,
            port=args.port,
            password=args.password,
            db=args.db
        )

        # Test connection
        benchmark.client.ping()

        if args.verbose:
            print(f"Connected to Redis at {args.host}:{args.port}", file=sys.stderr)
            print(f"Running benchmarks with {args.iterations} iterations...\n", file=sys.stderr)

        # Run benchmarks
        if args.benchmark == 'all':
            results = benchmark.run_all_benchmarks(args.iterations)
        else:
            bench_method = {
                'strings': benchmark.benchmark_strings,
                'lists': benchmark.benchmark_lists,
                'sets': benchmark.benchmark_sets,
                'sorted_sets': benchmark.benchmark_sorted_sets,
                'hashes': benchmark.benchmark_hashes,
                'pipelining': benchmark.benchmark_pipelining,
                'data_sizes': benchmark.benchmark_data_sizes
            }[args.benchmark]
            results = {args.benchmark: bench_method(args.iterations)}

        if args.json:
            # Convert to JSON-serializable format
            json_results = {}
            for category, benchmarks in results.items():
                json_results[category] = [asdict(b) for b in benchmarks]
            print(json.dumps(json_results, indent=2))
        else:
            # Human-readable output
            print("\n" + "=" * 100)
            print(f"Redis Benchmark Results ({args.iterations} iterations)")
            print("=" * 100)

            for category, benchmarks in results.items():
                print(f"\n{category.upper().replace('_', ' ')}")
                print("-" * 100)
                print(f"{'Operation':<35} {'Ops/sec':>12} {'Avg(ms)':>10} "
                      f"{'P50(ms)':>10} {'P95(ms)':>10} {'P99(ms)':>10}")
                print("-" * 100)

                for result in benchmarks:
                    print(f"{result.operation:<35} "
                          f"{result.ops_per_sec:>12,.1f} "
                          f"{result.avg_latency_ms:>10.3f} "
                          f"{result.p50_latency_ms:>10.3f} "
                          f"{result.p95_latency_ms:>10.3f} "
                          f"{result.p99_latency_ms:>10.3f}")

                    if args.verbose:
                        print(f"{'':35} Min: {result.min_latency_ms:.3f}ms | "
                              f"Max: {result.max_latency_ms:.3f}ms | "
                              f"Total: {result.total_time:.2f}s")

            print("\n" + "=" * 100)
            print("Notes:")
            print("  - Ops/sec: Operations per second (higher is better)")
            print("  - Avg/P50/P95/P99: Latency in milliseconds (lower is better)")
            print("  - P50: 50th percentile (median)")
            print("  - P95: 95th percentile")
            print("  - P99: 99th percentile")
            print("=" * 100 + "\n")

    except redis.exceptions.ConnectionError as e:
        print(f"Error: Cannot connect to Redis at {args.host}:{args.port}", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)
    except redis.exceptions.AuthenticationError:
        print("Error: Authentication failed. Check password.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
