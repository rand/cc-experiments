#!/usr/bin/env python3
"""
Benchmark Throughput - Rate Limiter Performance Testing Tool

Benchmarks rate limiting implementation performance by testing
throughput, latency, and scalability.

Usage:
    ./benchmark_throughput.py --algorithm token_bucket
    ./benchmark_throughput.py --algorithm sliding_window --json
    ./benchmark_throughput.py --concurrent-users 100 --duration 30
    ./benchmark_throughput.py --help

Features:
- Test rate limiter throughput and latency
- Compare different algorithms (token bucket vs sliding window)
- Measure Redis overhead for distributed limiting
- Test under various load patterns
- Generate performance report
"""

import argparse
import asyncio
import time
import json
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from statistics import mean, median, stdev, quantiles
import redis
import redis.asyncio as aioredis


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run"""
    algorithm: str
    total_requests: int
    duration: float
    throughput: float
    latencies: List[float]
    avg_latency: float
    median_latency: float
    p95_latency: float
    p99_latency: float
    min_latency: float
    max_latency: float
    allowed_requests: int
    denied_requests: int
    errors: int


@dataclass
class ComparisonSummary:
    """Summary of algorithm comparison"""
    results: List[BenchmarkResult]
    winner: str
    winner_reason: str


class TokenBucketBenchmark:
    """Token bucket implementation for benchmarking"""

    def __init__(self, redis_client, capacity: int, refill_rate: float):
        """Initialize token bucket

        Args:
            redis_client: Redis client
            capacity: Maximum tokens
            refill_rate: Tokens per second
        """
        self.redis = redis_client
        self.capacity = capacity
        self.refill_rate = refill_rate

        # Lua script
        self.script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_needed = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])

        local state = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(state[1])
        local last_refill = tonumber(state[2])

        if not tokens then
            tokens = capacity
            last_refill = now
        end

        local elapsed = now - last_refill
        tokens = math.min(capacity, tokens + (elapsed * refill_rate))

        if tokens >= tokens_needed then
            tokens = tokens - tokens_needed
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)
            return 1
        else
            return 0
        end
        """

        self.script_sha = None

    async def init_script(self):
        """Load Lua script"""
        self.script_sha = await self.redis.script_load(self.script)

    async def check_limit(self, key: str) -> bool:
        """Check rate limit

        Args:
            key: Rate limit key

        Returns:
            True if allowed, False if denied
        """
        now = time.time()

        try:
            if not self.script_sha:
                await self.init_script()

            result = await self.redis.evalsha(
                self.script_sha,
                1,
                f"benchmark:token:{key}",
                self.capacity,
                self.refill_rate,
                1,
                now
            )

            return bool(result)

        except redis.exceptions.NoScriptError:
            await self.init_script()
            return await self.check_limit(key)

    async def cleanup(self):
        """Cleanup Redis keys"""
        keys = await self.redis.keys("benchmark:token:*")
        if keys:
            await self.redis.delete(*keys)


class SlidingWindowBenchmark:
    """Sliding window implementation for benchmarking"""

    def __init__(self, redis_client, limit: int, window_seconds: int):
        """Initialize sliding window

        Args:
            redis_client: Redis client
            limit: Maximum requests
            window_seconds: Window duration
        """
        self.redis = redis_client
        self.limit = limit
        self.window_seconds = window_seconds

        # Lua script
        self.script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local request_id = ARGV[4]

        local window_start = now - window

        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

        local count = redis.call('ZCARD', key)

        if count < limit then
            redis.call('ZADD', key, now, request_id)
            redis.call('EXPIRE', key, window * 2)
            return 1
        else
            return 0
        end
        """

        self.script_sha = None
        self.request_counter = 0

    async def init_script(self):
        """Load Lua script"""
        self.script_sha = await self.redis.script_load(self.script)

    async def check_limit(self, key: str) -> bool:
        """Check rate limit

        Args:
            key: Rate limit key

        Returns:
            True if allowed, False if denied
        """
        now = time.time()
        self.request_counter += 1
        request_id = f"{now}:{self.request_counter}"

        try:
            if not self.script_sha:
                await self.init_script()

            result = await self.redis.evalsha(
                self.script_sha,
                1,
                f"benchmark:sliding:{key}",
                self.limit,
                self.window_seconds,
                now,
                request_id
            )

            return bool(result)

        except redis.exceptions.NoScriptError:
            await self.init_script()
            return await self.check_limit(key)

    async def cleanup(self):
        """Cleanup Redis keys"""
        keys = await self.redis.keys("benchmark:sliding:*")
        if keys:
            await self.redis.delete(*keys)


class FixedWindowBenchmark:
    """Fixed window implementation for benchmarking"""

    def __init__(self, redis_client, limit: int, window_seconds: int):
        """Initialize fixed window

        Args:
            redis_client: Redis client
            limit: Maximum requests
            window_seconds: Window duration
        """
        self.redis = redis_client
        self.limit = limit
        self.window_seconds = window_seconds

    async def check_limit(self, key: str) -> bool:
        """Check rate limit

        Args:
            key: Rate limit key

        Returns:
            True if allowed, False if denied
        """
        now = int(time.time())
        window_id = now // self.window_seconds
        redis_key = f"benchmark:fixed:{key}:{window_id}"

        pipe = self.redis.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, self.window_seconds * 2)
        results = await pipe.execute()

        count = results[0]
        return count <= self.limit

    async def cleanup(self):
        """Cleanup Redis keys"""
        keys = await self.redis.keys("benchmark:fixed:*")
        if keys:
            await self.redis.delete(*keys)


class RateLimiterBenchmark:
    """Benchmark rate limiter performance"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize benchmark

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client = None

    async def init_redis(self):
        """Initialize Redis connection"""
        self.redis_client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )

    async def close_redis(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    async def benchmark_algorithm(
        self,
        algorithm: str,
        concurrent_users: int,
        requests_per_user: int,
        limit: int,
        window: int
    ) -> BenchmarkResult:
        """Benchmark specific algorithm

        Args:
            algorithm: Algorithm name (token_bucket, sliding_window, fixed_window)
            concurrent_users: Number of concurrent users
            requests_per_user: Requests per user
            limit: Rate limit
            window: Window duration

        Returns:
            Benchmark result
        """
        # Create limiter
        if algorithm == "token_bucket":
            limiter = TokenBucketBenchmark(
                self.redis_client,
                capacity=limit,
                refill_rate=limit / window
            )
        elif algorithm == "sliding_window":
            limiter = SlidingWindowBenchmark(
                self.redis_client,
                limit=limit,
                window_seconds=window
            )
        elif algorithm == "fixed_window":
            limiter = FixedWindowBenchmark(
                self.redis_client,
                limit=limit,
                window_seconds=window
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        # Cleanup before test
        await limiter.cleanup()

        # Run benchmark
        latencies = []
        allowed = 0
        denied = 0
        errors = 0

        async def user_workload(user_id: int):
            """Simulate user workload"""
            nonlocal allowed, denied, errors

            for _ in range(requests_per_user):
                start = time.time()

                try:
                    result = await limiter.check_limit(f"user:{user_id}")
                    latency = time.time() - start
                    latencies.append(latency)

                    if result:
                        allowed += 1
                    else:
                        denied += 1

                except Exception as e:
                    errors += 1

        # Run concurrent users
        start_time = time.time()
        tasks = [user_workload(i) for i in range(concurrent_users)]
        await asyncio.gather(*tasks)
        duration = time.time() - start_time

        # Cleanup after test
        await limiter.cleanup()

        # Calculate statistics
        total_requests = len(latencies)
        throughput = total_requests / duration if duration > 0 else 0

        percentiles = self._calculate_percentiles(latencies)

        return BenchmarkResult(
            algorithm=algorithm,
            total_requests=total_requests,
            duration=duration,
            throughput=throughput,
            latencies=latencies,
            avg_latency=mean(latencies) if latencies else 0.0,
            median_latency=median(latencies) if latencies else 0.0,
            p95_latency=percentiles.get('p95', 0.0),
            p99_latency=percentiles.get('p99', 0.0),
            min_latency=min(latencies) if latencies else 0.0,
            max_latency=max(latencies) if latencies else 0.0,
            allowed_requests=allowed,
            denied_requests=denied,
            errors=errors
        )

    def _calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate percentiles

        Args:
            values: List of values

        Returns:
            Dict of percentiles
        """
        if not values:
            return {}

        sorted_values = sorted(values)
        result = {}

        for p in [0.5, 0.9, 0.95, 0.99]:
            key = f"p{int(p*100)}"
            idx = int(len(sorted_values) * p)
            result[key] = sorted_values[min(idx, len(sorted_values)-1)]

        return result

    async def compare_algorithms(
        self,
        algorithms: List[str],
        concurrent_users: int,
        requests_per_user: int,
        limit: int,
        window: int
    ) -> ComparisonSummary:
        """Compare multiple algorithms

        Args:
            algorithms: List of algorithm names
            concurrent_users: Number of concurrent users
            requests_per_user: Requests per user
            limit: Rate limit
            window: Window duration

        Returns:
            Comparison summary
        """
        results = []

        for algorithm in algorithms:
            result = await self.benchmark_algorithm(
                algorithm,
                concurrent_users,
                requests_per_user,
                limit,
                window
            )
            results.append(result)

        # Determine winner (highest throughput, lowest latency)
        best_throughput = max(results, key=lambda r: r.throughput)
        best_latency = min(results, key=lambda r: r.avg_latency)

        if best_throughput.algorithm == best_latency.algorithm:
            winner = best_throughput.algorithm
            reason = (
                f"Highest throughput ({best_throughput.throughput:.2f} req/s) "
                f"and lowest latency ({best_latency.avg_latency*1000:.2f} ms)"
            )
        else:
            # Trade-off: prioritize throughput
            winner = best_throughput.algorithm
            reason = (
                f"Highest throughput ({best_throughput.throughput:.2f} req/s), "
                f"slightly higher latency than {best_latency.algorithm}"
            )

        return ComparisonSummary(
            results=results,
            winner=winner,
            winner_reason=reason
        )


def format_human_readable(summary: ComparisonSummary) -> str:
    """Format summary for human-readable output

    Args:
        summary: Comparison summary

    Returns:
        Formatted string
    """
    lines = [
        "=" * 70,
        "Rate Limiter Performance Benchmark",
        "=" * 70,
        ""
    ]

    for result in summary.results:
        lines.extend([
            f"Algorithm: {result.algorithm.replace('_', ' ').title()}",
            f"  Total Requests:   {result.total_requests:,}",
            f"  Duration:         {result.duration:.2f} seconds",
            f"  Throughput:       {result.throughput:.2f} req/s",
            "",
            f"  Latency:",
            f"    Average:        {result.avg_latency*1000:.2f} ms",
            f"    Median:         {result.median_latency*1000:.2f} ms",
            f"    P95:            {result.p95_latency*1000:.2f} ms",
            f"    P99:            {result.p99_latency*1000:.2f} ms",
            f"    Min:            {result.min_latency*1000:.2f} ms",
            f"    Max:            {result.max_latency*1000:.2f} ms",
            "",
            f"  Rate Limiting:",
            f"    Allowed:        {result.allowed_requests:,}",
            f"    Denied:         {result.denied_requests:,}",
            f"    Errors:         {result.errors}",
            ""
        ])

    lines.extend([
        "=" * 70,
        f"Winner: {summary.winner.replace('_', ' ').title()}",
        f"Reason: {summary.winner_reason}",
        "=" * 70
    ])

    return "\n".join(lines)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Benchmark rate limiter implementation performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Benchmark token bucket
  %(prog)s --algorithm token_bucket

  # Compare all algorithms
  %(prog)s --algorithm all

  # Custom load parameters
  %(prog)s --algorithm sliding_window --concurrent-users 100 --requests 50

  # JSON output
  %(prog)s --algorithm all --json

  # Custom Redis connection
  %(prog)s --algorithm token_bucket --redis redis://localhost:6380/0
        """
    )

    parser.add_argument('--algorithm', required=True,
                       choices=['token_bucket', 'sliding_window', 'fixed_window', 'all'],
                       help='Algorithm to benchmark')
    parser.add_argument('--concurrent-users', type=int, default=10,
                       help='Number of concurrent users (default: 10)')
    parser.add_argument('--requests', type=int, default=100,
                       help='Requests per user (default: 100)')
    parser.add_argument('--limit', type=int, default=100,
                       help='Rate limit (default: 100)')
    parser.add_argument('--window', type=int, default=60,
                       help='Window duration in seconds (default: 60)')
    parser.add_argument('--redis', default='redis://localhost:6379/0',
                       help='Redis connection URL (default: redis://localhost:6379/0)')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')

    args = parser.parse_args()

    # Determine algorithms to test
    if args.algorithm == 'all':
        algorithms = ['token_bucket', 'sliding_window', 'fixed_window']
    else:
        algorithms = [args.algorithm]

    # Create benchmark
    benchmark = RateLimiterBenchmark(args.redis)

    try:
        # Initialize Redis
        await benchmark.init_redis()

        if not args.json:
            print(f"Benchmarking rate limiter performance...")
            print(f"Algorithms: {', '.join(algorithms)}")
            print(f"Concurrent users: {args.concurrent_users}")
            print(f"Requests per user: {args.requests}")
            print(f"Rate limit: {args.limit} requests per {args.window} seconds")
            print()

        # Run benchmark
        summary = await benchmark.compare_algorithms(
            algorithms,
            args.concurrent_users,
            args.requests,
            args.limit,
            args.window
        )

        # Output results
        if args.json:
            # Convert to dict, excluding latencies list (too large)
            result = asdict(summary)
            for r in result['results']:
                r['latencies'] = []  # Remove raw latencies
            print(json.dumps(result, indent=2))
        else:
            print(format_human_readable(summary))

    except redis.ConnectionError as e:
        print(f"Error: Redis connection failed: {e}", file=sys.stderr)
        print(f"Make sure Redis is running at {args.redis}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await benchmark.close_redis()


if __name__ == '__main__':
    asyncio.run(main())
