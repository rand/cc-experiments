#!/usr/bin/env python3
"""
Event Store Benchmark Tool

Benchmark event store performance for writes, reads, projections, and snapshots.
Tests throughput, latency, and concurrent operations.

Usage:
    ./benchmark_eventstore.py --store postgres://...@localhost/events --write
    ./benchmark_eventstore.py --store postgres://...@localhost/events --read
    ./benchmark_eventstore.py --store postgres://...@localhost/events --full
    ./benchmark_eventstore.py --help

Examples:
    # Benchmark write performance
    ./benchmark_eventstore.py --store postgres://localhost/events --write --events 10000

    # Benchmark read performance
    ./benchmark_eventstore.py --store postgres://localhost/events --read --aggregates 100

    # Full benchmark suite
    ./benchmark_eventstore.py --store postgres://localhost/events --full --json

    # Concurrent write benchmark
    ./benchmark_eventstore.py --store postgres://localhost/events --write --concurrent 10
"""

import argparse
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from statistics import mean, median, stdev
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkResult:
    """Result of a benchmark run"""
    name: str
    total_operations: int
    duration_seconds: float
    throughput_ops_per_sec: float
    latencies_ms: List[float]
    avg_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    errors: int


class EventStoreClient:
    """Client for interacting with event store"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connect()

    def _connect(self):
        """Connect to event store"""
        try:
            import psycopg2
            self.conn = psycopg2.connect(self.connection_string)
            self.conn.autocommit = False
        except ImportError:
            raise ImportError("psycopg2 required. Install: pip install psycopg2-binary")

    def append_event(self, aggregate_id: str, event_type: str, data: Dict[str, Any], expected_version: int) -> float:
        """
        Append single event and return operation time in milliseconds

        Returns:
            float: Operation time in milliseconds
        """
        start = time.perf_counter()

        cursor = self.conn.cursor()

        try:
            # Check current version
            cursor.execute(
                "SELECT current_version FROM streams WHERE aggregate_id = %s FOR UPDATE",
                (aggregate_id,)
            )
            result = cursor.fetchone()
            current_version = result[0] if result else 0

            # Optimistic concurrency check
            if current_version != expected_version:
                raise Exception(f"Concurrency conflict: expected {expected_version}, got {current_version}")

            # Insert event
            version = expected_version + 1
            cursor.execute(
                """
                INSERT INTO events (
                    event_id, event_type, aggregate_id, aggregate_type,
                    version, data, metadata, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    event_type,
                    aggregate_id,
                    'BenchmarkAggregate',
                    version,
                    json.dumps(data),
                    json.dumps({}),
                    datetime.now()
                )
            )

            # Update stream version
            if result is None:
                cursor.execute(
                    """
                    INSERT INTO streams (aggregate_id, aggregate_type, current_version, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    """,
                    (aggregate_id, 'BenchmarkAggregate', version)
                )
            else:
                cursor.execute(
                    """
                    UPDATE streams SET current_version = %s, updated_at = NOW()
                    WHERE aggregate_id = %s
                    """,
                    (version, aggregate_id)
                )

            self.conn.commit()

            duration = (time.perf_counter() - start) * 1000
            return duration

        except Exception as e:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def append_events_batch(self, aggregate_id: str, events: List[Dict[str, Any]], expected_version: int) -> float:
        """
        Append batch of events and return operation time in milliseconds
        """
        start = time.perf_counter()

        cursor = self.conn.cursor()

        try:
            # Check current version
            cursor.execute(
                "SELECT current_version FROM streams WHERE aggregate_id = %s FOR UPDATE",
                (aggregate_id,)
            )
            result = cursor.fetchone()
            current_version = result[0] if result else 0

            if current_version != expected_version:
                raise Exception(f"Concurrency conflict: expected {expected_version}, got {current_version}")

            # Insert events
            for i, event in enumerate(events):
                version = expected_version + i + 1
                cursor.execute(
                    """
                    INSERT INTO events (
                        event_id, event_type, aggregate_id, aggregate_type,
                        version, data, metadata, timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        event['eventType'],
                        aggregate_id,
                        'BenchmarkAggregate',
                        version,
                        json.dumps(event['data']),
                        json.dumps({}),
                        datetime.now()
                    )
                )

            # Update stream version
            new_version = expected_version + len(events)
            if result is None:
                cursor.execute(
                    """
                    INSERT INTO streams (aggregate_id, aggregate_type, current_version, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    """,
                    (aggregate_id, 'BenchmarkAggregate', new_version)
                )
            else:
                cursor.execute(
                    """
                    UPDATE streams SET current_version = %s, updated_at = NOW()
                    WHERE aggregate_id = %s
                    """,
                    (new_version, aggregate_id)
                )

            self.conn.commit()

            duration = (time.perf_counter() - start) * 1000
            return duration

        except Exception as e:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def read_events(self, aggregate_id: str) -> tuple[List[Dict], float]:
        """
        Read all events for aggregate and return (events, duration_ms)
        """
        start = time.perf_counter()

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT event_id, event_type, version, data, timestamp
            FROM events
            WHERE aggregate_id = %s
            ORDER BY version ASC
            """,
            (aggregate_id,)
        )

        events = []
        for row in cursor.fetchall():
            events.append({
                'eventId': str(row[0]),
                'eventType': row[1],
                'version': row[2],
                'data': row[3],
                'timestamp': row[4]
            })

        cursor.close()

        duration = (time.perf_counter() - start) * 1000
        return events, duration

    def stream_all_events(self, limit: Optional[int] = None) -> tuple[int, float]:
        """
        Stream all events and return (count, duration_ms)
        """
        start = time.perf_counter()

        cursor = self.conn.cursor('stream_cursor')

        if limit:
            cursor.execute(
                "SELECT event_id, event_type, data FROM events ORDER BY id ASC LIMIT %s",
                (limit,)
            )
        else:
            cursor.execute("SELECT event_id, event_type, data FROM events ORDER BY id ASC")

        count = 0
        for _ in cursor:
            count += 1

        cursor.close()

        duration = (time.perf_counter() - start) * 1000
        return count, duration

    def cleanup_benchmark_data(self):
        """Clean up benchmark data"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM events WHERE aggregate_type = 'BenchmarkAggregate'")
        cursor.execute("DELETE FROM streams WHERE aggregate_type = 'BenchmarkAggregate'")
        self.conn.commit()
        cursor.close()


class Benchmarks:
    """Collection of benchmark tests"""

    def __init__(self, client: EventStoreClient):
        self.client = client

    def write_single_events(self, num_events: int = 1000) -> BenchmarkResult:
        """Benchmark writing individual events"""
        print(f"\nRunning write benchmark: {num_events} single events...")

        aggregate_id = f"bench-{uuid.uuid4()}"
        latencies = []
        errors = 0
        version = 0

        start_time = time.perf_counter()

        for i in range(num_events):
            try:
                latency = self.client.append_event(
                    aggregate_id=aggregate_id,
                    event_type="BenchmarkEvent",
                    data={"sequence": i, "payload": "x" * 100},
                    expected_version=version
                )
                latencies.append(latency)
                version += 1

                if (i + 1) % 100 == 0:
                    print(f"  Progress: {i+1}/{num_events} events written")

            except Exception as e:
                errors += 1
                print(f"  Error writing event {i}: {e}")

        duration = time.perf_counter() - start_time

        return self._create_result("Write Single Events", num_events, duration, latencies, errors)

    def write_batch_events(self, num_batches: int = 100, batch_size: int = 10) -> BenchmarkResult:
        """Benchmark writing batched events"""
        print(f"\nRunning batch write benchmark: {num_batches} batches of {batch_size} events...")

        latencies = []
        errors = 0
        version = 0

        start_time = time.perf_counter()

        for i in range(num_batches):
            aggregate_id = f"bench-batch-{uuid.uuid4()}"

            try:
                events = [
                    {
                        "eventType": "BenchmarkEvent",
                        "data": {"sequence": j, "payload": "x" * 100}
                    }
                    for j in range(batch_size)
                ]

                latency = self.client.append_events_batch(
                    aggregate_id=aggregate_id,
                    events=events,
                    expected_version=0
                )
                latencies.append(latency)

                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i+1}/{num_batches} batches written")

            except Exception as e:
                errors += 1
                print(f"  Error writing batch {i}: {e}")

        duration = time.perf_counter() - start_time
        total_events = num_batches * batch_size

        return self._create_result("Write Batch Events", total_events, duration, latencies, errors)

    def read_aggregates(self, num_aggregates: int = 100, events_per_aggregate: int = 10) -> BenchmarkResult:
        """Benchmark reading aggregates"""
        print(f"\nRunning read benchmark: {num_aggregates} aggregates with {events_per_aggregate} events each...")

        # First, create test data
        print("  Creating test data...")
        aggregate_ids = []
        for i in range(num_aggregates):
            aggregate_id = f"bench-read-{uuid.uuid4()}"
            aggregate_ids.append(aggregate_id)

            events = [
                {
                    "eventType": "BenchmarkEvent",
                    "data": {"sequence": j}
                }
                for j in range(events_per_aggregate)
            ]

            self.client.append_events_batch(aggregate_id, events, 0)

            if (i + 1) % 10 == 0:
                print(f"    Created {i+1}/{num_aggregates} aggregates")

        # Now benchmark reads
        print("  Reading aggregates...")
        latencies = []
        errors = 0

        start_time = time.perf_counter()

        for i, aggregate_id in enumerate(aggregate_ids):
            try:
                events, latency = self.client.read_events(aggregate_id)
                latencies.append(latency)

                if len(events) != events_per_aggregate:
                    print(f"  Warning: Expected {events_per_aggregate} events, got {len(events)}")

                if (i + 1) % 10 == 0:
                    print(f"    Read {i+1}/{num_aggregates} aggregates")

            except Exception as e:
                errors += 1
                print(f"  Error reading aggregate {i}: {e}")

        duration = time.perf_counter() - start_time

        return self._create_result("Read Aggregates", num_aggregates, duration, latencies, errors)

    def concurrent_writes(self, num_workers: int = 10, events_per_worker: int = 100) -> BenchmarkResult:
        """Benchmark concurrent writes"""
        print(f"\nRunning concurrent write benchmark: {num_workers} workers, {events_per_worker} events each...")

        def worker(worker_id: int) -> List[float]:
            """Worker function for concurrent writes"""
            aggregate_id = f"bench-concurrent-{uuid.uuid4()}"
            latencies = []
            version = 0

            for i in range(events_per_worker):
                try:
                    latency = self.client.append_event(
                        aggregate_id=aggregate_id,
                        event_type="BenchmarkEvent",
                        data={"worker": worker_id, "sequence": i},
                        expected_version=version
                    )
                    latencies.append(latency)
                    version += 1
                except Exception as e:
                    print(f"  Worker {worker_id} error: {e}")

            return latencies

        all_latencies = []
        errors = 0

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker, i) for i in range(num_workers)]

            for i, future in enumerate(as_completed(futures)):
                try:
                    latencies = future.result()
                    all_latencies.extend(latencies)
                    print(f"  Worker {i} completed")
                except Exception as e:
                    errors += 1
                    print(f"  Worker {i} failed: {e}")

        duration = time.perf_counter() - start_time
        total_events = num_workers * events_per_worker

        return self._create_result("Concurrent Writes", total_events, duration, all_latencies, errors)

    def stream_events(self, limit: int = 10000) -> BenchmarkResult:
        """Benchmark streaming events"""
        print(f"\nRunning stream benchmark: streaming {limit} events...")

        start_time = time.perf_counter()
        count, _ = self.client.stream_all_events(limit=limit)
        duration = time.perf_counter() - start_time

        return BenchmarkResult(
            name="Stream Events",
            total_operations=count,
            duration_seconds=duration,
            throughput_ops_per_sec=count / duration if duration > 0 else 0,
            latencies_ms=[],
            avg_latency_ms=0,
            median_latency_ms=0,
            p95_latency_ms=0,
            p99_latency_ms=0,
            min_latency_ms=0,
            max_latency_ms=0,
            errors=0
        )

    def _create_result(
        self,
        name: str,
        total_ops: int,
        duration: float,
        latencies: List[float],
        errors: int
    ) -> BenchmarkResult:
        """Create benchmark result from raw data"""
        if not latencies:
            return BenchmarkResult(
                name=name,
                total_operations=total_ops,
                duration_seconds=duration,
                throughput_ops_per_sec=0,
                latencies_ms=[],
                avg_latency_ms=0,
                median_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                errors=errors
            )

        sorted_latencies = sorted(latencies)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)

        return BenchmarkResult(
            name=name,
            total_operations=total_ops,
            duration_seconds=duration,
            throughput_ops_per_sec=total_ops / duration if duration > 0 else 0,
            latencies_ms=latencies,
            avg_latency_ms=mean(latencies),
            median_latency_ms=median(latencies),
            p95_latency_ms=sorted_latencies[p95_idx],
            p99_latency_ms=sorted_latencies[p99_idx],
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            errors=errors
        )


def print_results(results: List[BenchmarkResult], json_output: bool = False):
    """Print benchmark results"""
    if json_output:
        output = {
            'timestamp': datetime.now().isoformat(),
            'results': [
                {
                    'name': r.name,
                    'totalOperations': r.total_operations,
                    'durationSeconds': r.duration_seconds,
                    'throughputOpsPerSec': r.throughput_ops_per_sec,
                    'avgLatencyMs': r.avg_latency_ms,
                    'medianLatencyMs': r.median_latency_ms,
                    'p95LatencyMs': r.p95_latency_ms,
                    'p99LatencyMs': r.p99_latency_ms,
                    'minLatencyMs': r.min_latency_ms,
                    'maxLatencyMs': r.max_latency_ms,
                    'errors': r.errors
                }
                for r in results
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'='*80}")
        print("Benchmark Results")
        print(f"{'='*80}\n")

        for result in results:
            print(f"{result.name}")
            print(f"  Total operations: {result.total_operations}")
            print(f"  Duration: {result.duration_seconds:.2f}s")
            print(f"  Throughput: {result.throughput_ops_per_sec:.2f} ops/sec")
            if result.latencies_ms:
                print(f"  Avg latency: {result.avg_latency_ms:.2f}ms")
                print(f"  Median latency: {result.median_latency_ms:.2f}ms")
                print(f"  P95 latency: {result.p95_latency_ms:.2f}ms")
                print(f"  P99 latency: {result.p99_latency_ms:.2f}ms")
                print(f"  Min/Max: {result.min_latency_ms:.2f}ms / {result.max_latency_ms:.2f}ms")
            if result.errors > 0:
                print(f"  Errors: {result.errors}")
            print()

        print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark event store performance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--store', type=str, required=True, help='Event store connection string')

    # Benchmark modes
    parser.add_argument('--write', action='store_true', help='Benchmark write performance')
    parser.add_argument('--read', action='store_true', help='Benchmark read performance')
    parser.add_argument('--concurrent', type=int, metavar='N', help='Benchmark concurrent writes (N workers)')
    parser.add_argument('--stream', action='store_true', help='Benchmark event streaming')
    parser.add_argument('--full', action='store_true', help='Run full benchmark suite')

    # Parameters
    parser.add_argument('--events', type=int, default=1000, help='Number of events for write benchmark')
    parser.add_argument('--aggregates', type=int, default=100, help='Number of aggregates for read benchmark')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for batch writes')

    # Options
    parser.add_argument('--cleanup', action='store_true', help='Cleanup benchmark data before starting')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    args = parser.parse_args()

    # Connect to event store
    try:
        client = EventStoreClient(args.store)
        print(f"Connected to event store")
    except Exception as e:
        print(f"Error connecting to event store: {e}", file=sys.stderr)
        sys.exit(1)

    # Cleanup if requested
    if args.cleanup:
        print("Cleaning up previous benchmark data...")
        client.cleanup_benchmark_data()

    # Run benchmarks
    benchmarks = Benchmarks(client)
    results = []

    try:
        if args.full or args.write:
            results.append(benchmarks.write_single_events(num_events=args.events))
            results.append(benchmarks.write_batch_events(
                num_batches=args.events // args.batch_size,
                batch_size=args.batch_size
            ))

        if args.full or args.read:
            results.append(benchmarks.read_aggregates(num_aggregates=args.aggregates))

        if args.full or args.concurrent:
            workers = args.concurrent if args.concurrent else 10
            results.append(benchmarks.concurrent_writes(
                num_workers=workers,
                events_per_worker=args.events // workers
            ))

        if args.full or args.stream:
            results.append(benchmarks.stream_events(limit=args.events))

        if not results:
            parser.error("No benchmark mode specified. Use --write, --read, --concurrent, --stream, or --full")

        # Print results
        print_results(results, json_output=args.json)

    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Benchmark error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
