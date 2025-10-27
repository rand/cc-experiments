#!/usr/bin/env python3
"""
CRDT Merge Performance Benchmark

Benchmarks merge performance for different CRDT types under various scenarios:
- Small vs large state sizes
- High vs low conflict rates
- Different replica counts
- Memory usage analysis
"""

import argparse
import json
import random
import sys
import time
import tracemalloc
from dataclasses import dataclass
from statistics import mean, stdev
from typing import List, Dict, Any


# =============================================================================
# Simplified CRDT Implementations (optimized for benchmarking)
# =============================================================================

class GCounterBench:
    """G-Counter for benchmarking"""

    def __init__(self, n_replicas: int, replica_id: int):
        self.payload = [0] * n_replicas
        self.replica_id = replica_id

    def increment(self, amount: int = 1):
        self.payload[self.replica_id] += amount

    def value(self) -> int:
        return sum(self.payload)

    def merge(self, other: "GCounterBench"):
        for i in range(len(self.payload)):
            self.payload[i] = max(self.payload[i], other.payload[i])

    def size_bytes(self) -> int:
        return len(self.payload) * 8  # 8 bytes per int


class PNCounterBench:
    """PN-Counter for benchmarking"""

    def __init__(self, n_replicas: int, replica_id: int):
        self.positive = [0] * n_replicas
        self.negative = [0] * n_replicas
        self.replica_id = replica_id

    def increment(self, amount: int = 1):
        self.positive[self.replica_id] += amount

    def decrement(self, amount: int = 1):
        self.negative[self.replica_id] += amount

    def value(self) -> int:
        return sum(self.positive) - sum(self.negative)

    def merge(self, other: "PNCounterBench"):
        for i in range(len(self.positive)):
            self.positive[i] = max(self.positive[i], other.positive[i])
            self.negative[i] = max(self.negative[i], other.negative[i])

    def size_bytes(self) -> int:
        return len(self.positive) * 8 * 2


class ORSetBench:
    """OR-Set for benchmarking"""

    def __init__(self, replica_id: int):
        self.payload = set()
        self.replica_id = replica_id
        self.clock = 0

    def add(self, element: Any):
        self.clock += 1
        self.payload.add((element, self.replica_id, self.clock))

    def remove(self, element: Any):
        self.payload = {t for t in self.payload if t[0] != element}

    def elements(self) -> set:
        return {t[0] for t in self.payload}

    def merge(self, other: "ORSetBench"):
        self.payload |= other.payload
        self.clock = max(self.clock, other.clock)

    def size_bytes(self) -> int:
        # Approximate: 8 bytes per int, 50 bytes per string
        return len(self.payload) * (50 + 8 + 8)


class LWWSetBench:
    """LWW-Set for benchmarking"""

    def __init__(self, replica_id: int):
        self.added = {}
        self.removed = {}
        self.replica_id = replica_id
        self.clock = 0

    def add(self, element: Any):
        self.clock += 1
        self.added[element] = max(self.added.get(element, 0), self.clock)

    def remove(self, element: Any):
        self.clock += 1
        self.removed[element] = max(self.removed.get(element, 0), self.clock)

    def elements(self) -> set:
        return {e for e in self.added
                if self.added[e] > self.removed.get(e, 0)}

    def merge(self, other: "LWWSetBench"):
        for e, ts in other.added.items():
            self.added[e] = max(self.added.get(e, 0), ts)
        for e, ts in other.removed.items():
            self.removed[e] = max(self.removed.get(e, 0), ts)
        self.clock = max(self.clock, other.clock)

    def size_bytes(self) -> int:
        return (len(self.added) + len(self.removed)) * (50 + 8)


class RGABench:
    """RGA for benchmarking (simplified)"""

    def __init__(self, replica_id: int):
        self.elements = []
        self.replica_id = replica_id
        self.seq = 0

    def insert(self, char: str, pos: int):
        self.seq += 1
        self.elements.insert(pos, (char, self.replica_id, self.seq, False))

    def delete(self, pos: int):
        if 0 <= pos < len(self.elements):
            char, rid, seq, _ = self.elements[pos]
            self.elements[pos] = (char, rid, seq, True)  # tombstone

    def to_string(self) -> str:
        return ''.join(c for c, _, _, tomb in self.elements if not tomb)

    def merge(self, other: "RGABench"):
        # Simplified merge: combine and sort by (replica_id, seq)
        combined = {}
        for elem in self.elements:
            combined[(elem[1], elem[2])] = elem
        for elem in other.elements:
            key = (elem[1], elem[2])
            if key not in combined:
                combined[key] = elem
            else:
                # Update tombstone status
                if elem[3]:  # other is tombstone
                    c, rid, seq, _ = combined[key]
                    combined[key] = (c, rid, seq, True)

        self.elements = sorted(combined.values(), key=lambda x: (x[1], x[2]))
        self.seq = max(self.seq, other.seq)

    def size_bytes(self) -> int:
        return len(self.elements) * (1 + 8 + 8 + 1)  # char + rid + seq + bool


# =============================================================================
# Benchmark Framework
# =============================================================================

@dataclass
class BenchmarkResult:
    """Result of a benchmark run"""
    crdt_type: str
    scenario: str
    n_replicas: int
    state_size: int
    merge_time_ms: float
    memory_bytes: int
    operations_per_sec: float


class CRDTBenchmark:
    """Benchmark framework for CRDTs"""

    def __init__(self, crdt_type: str, n_replicas: int):
        self.crdt_type = crdt_type
        self.n_replicas = n_replicas
        self.replicas = []

        # Create replicas
        for i in range(n_replicas):
            if crdt_type == "g-counter":
                self.replicas.append(GCounterBench(n_replicas, i))
            elif crdt_type == "pn-counter":
                self.replicas.append(PNCounterBench(n_replicas, i))
            elif crdt_type == "or-set":
                self.replicas.append(ORSetBench(i))
            elif crdt_type == "lww-set":
                self.replicas.append(LWWSetBench(i))
            elif crdt_type == "rga":
                self.replicas.append(RGABench(i))
            else:
                raise ValueError(f"Unknown CRDT type: {crdt_type}")

    def populate_counter(self, ops_per_replica: int):
        """Populate counter with increments"""
        for replica in self.replicas:
            for _ in range(ops_per_replica):
                replica.increment(random.randint(1, 10))

    def populate_pn_counter(self, ops_per_replica: int):
        """Populate PN-counter with inc/dec"""
        for replica in self.replicas:
            for _ in range(ops_per_replica):
                if random.random() < 0.6:
                    replica.increment(random.randint(1, 10))
                else:
                    replica.decrement(random.randint(1, 10))

    def populate_set(self, elements_per_replica: int, conflict_rate: float):
        """Populate set with adds/removes"""
        universe = [f"elem_{i}" for i in range(int(elements_per_replica / conflict_rate))]

        for replica in self.replicas:
            # Add elements
            for _ in range(elements_per_replica):
                elem = random.choice(universe)
                replica.add(elem)

            # Remove some elements
            for _ in range(int(elements_per_replica * 0.3)):
                elem = random.choice(universe)
                replica.remove(elem)

    def populate_rga(self, chars_per_replica: int):
        """Populate RGA with characters"""
        for replica in self.replicas:
            for i in range(chars_per_replica):
                char = chr(ord('a') + random.randint(0, 25))
                pos = random.randint(0, len(replica.elements))
                replica.insert(char, pos)

            # Delete some characters
            for _ in range(int(chars_per_replica * 0.2)):
                if replica.elements:
                    pos = random.randint(0, len(replica.elements) - 1)
                    replica.delete(pos)

    def benchmark_merge(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark merge performance"""

        # Get state size before merge
        state_size = sum(len(r.payload) if hasattr(r, 'payload')
                        else len(r.elements) if hasattr(r, 'elements')
                        else len(r.positive)
                        for r in self.replicas)

        # Benchmark merge
        merge_times = []

        for _ in range(iterations):
            # Clone replicas for fresh merge
            import copy
            replicas_copy = [copy.deepcopy(r) for r in self.replicas]

            # Time merge
            start = time.perf_counter()

            # Merge all replicas into first
            for i in range(1, len(replicas_copy)):
                replicas_copy[0].merge(replicas_copy[i])

            end = time.perf_counter()
            merge_times.append((end - start) * 1000)  # Convert to ms

        # Measure memory
        tracemalloc.start()
        test_replica = copy.deepcopy(self.replicas[0])
        for i in range(1, len(self.replicas)):
            test_replica.merge(self.replicas[i])
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Calculate statistics
        avg_merge_time = mean(merge_times)
        ops_per_sec = 1000.0 / avg_merge_time if avg_merge_time > 0 else 0

        return BenchmarkResult(
            crdt_type=self.crdt_type,
            scenario="merge",
            n_replicas=self.n_replicas,
            state_size=state_size,
            merge_time_ms=avg_merge_time,
            memory_bytes=peak,
            operations_per_sec=ops_per_sec
        )

    def benchmark_operations(self, n_operations: int) -> BenchmarkResult:
        """Benchmark operation performance"""

        replica = self.replicas[0]
        op_times = []

        for _ in range(n_operations):
            start = time.perf_counter()

            if self.crdt_type == "g-counter":
                replica.increment(1)
            elif self.crdt_type == "pn-counter":
                if random.random() < 0.5:
                    replica.increment(1)
                else:
                    replica.decrement(1)
            elif self.crdt_type in ["or-set", "lww-set"]:
                if random.random() < 0.7:
                    replica.add(f"elem_{random.randint(0, 1000)}")
                else:
                    replica.remove(f"elem_{random.randint(0, 1000)}")
            elif self.crdt_type == "rga":
                if random.random() < 0.8:
                    char = chr(ord('a') + random.randint(0, 25))
                    pos = random.randint(0, len(replica.elements))
                    replica.insert(char, pos)
                else:
                    if replica.elements:
                        pos = random.randint(0, len(replica.elements) - 1)
                        replica.delete(pos)

            end = time.perf_counter()
            op_times.append((end - start) * 1000)

        avg_op_time = mean(op_times)
        ops_per_sec = 1000.0 / avg_op_time if avg_op_time > 0 else 0

        # Measure memory
        tracemalloc.start()
        test_replica = copy.deepcopy(replica)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        state_size = (len(replica.payload) if hasattr(replica, 'payload')
                     else len(replica.elements) if hasattr(replica, 'elements')
                     else len(replica.positive))

        return BenchmarkResult(
            crdt_type=self.crdt_type,
            scenario="operations",
            n_replicas=1,
            state_size=state_size,
            merge_time_ms=avg_op_time,
            memory_bytes=peak,
            operations_per_sec=ops_per_sec
        )


# =============================================================================
# Benchmark Scenarios
# =============================================================================

def run_merge_scaling_benchmark(crdt_type: str, sizes: List[int]) -> List[BenchmarkResult]:
    """Benchmark merge performance with increasing state sizes"""
    results = []

    for size in sizes:
        bench = CRDTBenchmark(crdt_type, 3)

        # Populate based on type
        if crdt_type == "g-counter":
            bench.populate_counter(size)
        elif crdt_type == "pn-counter":
            bench.populate_pn_counter(size)
        elif crdt_type in ["or-set", "lww-set"]:
            bench.populate_set(size, conflict_rate=0.3)
        elif crdt_type == "rga":
            bench.populate_rga(size)

        result = bench.benchmark_merge(iterations=50)
        results.append(result)

    return results


def run_replica_scaling_benchmark(crdt_type: str, replica_counts: List[int]) -> List[BenchmarkResult]:
    """Benchmark merge performance with increasing replica counts"""
    results = []

    for n_replicas in replica_counts:
        bench = CRDTBenchmark(crdt_type, n_replicas)

        # Fixed state size
        ops = 100

        # Populate
        if crdt_type == "g-counter":
            bench.populate_counter(ops)
        elif crdt_type == "pn-counter":
            bench.populate_pn_counter(ops)
        elif crdt_type in ["or-set", "lww-set"]:
            bench.populate_set(ops, conflict_rate=0.3)
        elif crdt_type == "rga":
            bench.populate_rga(ops)

        result = bench.benchmark_merge(iterations=50)
        results.append(result)

    return results


def run_conflict_rate_benchmark(crdt_type: str, conflict_rates: List[float]) -> List[BenchmarkResult]:
    """Benchmark set merge with different conflict rates"""
    if crdt_type not in ["or-set", "lww-set"]:
        return []

    results = []

    for conflict_rate in conflict_rates:
        bench = CRDTBenchmark(crdt_type, 3)
        bench.populate_set(100, conflict_rate)

        result = bench.benchmark_merge(iterations=50)
        result.scenario = f"conflict_rate_{conflict_rate}"
        results.append(result)

    return results


def run_operation_benchmark(crdt_type: str, n_operations: int) -> BenchmarkResult:
    """Benchmark individual operation performance"""
    bench = CRDTBenchmark(crdt_type, 1)
    return bench.benchmark_operations(n_operations)


# =============================================================================
# Main CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark CRDT merge and operation performance"
    )
    parser.add_argument(
        "crdt_type",
        choices=["g-counter", "pn-counter", "or-set", "lww-set", "rga", "all"],
        help="Type of CRDT to benchmark"
    )
    parser.add_argument(
        "--benchmark", "-b",
        choices=["merge-scaling", "replica-scaling", "conflict-rate", "operations", "all"],
        default="all",
        help="Benchmark scenario to run"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--sizes",
        type=str,
        default="10,50,100,500,1000",
        help="Comma-separated state sizes for scaling benchmark"
    )
    parser.add_argument(
        "--replicas",
        type=str,
        default="2,3,5,10,20",
        help="Comma-separated replica counts for scaling benchmark"
    )

    args = parser.parse_args()

    # Parse sizes and replica counts
    sizes = [int(x) for x in args.sizes.split(",")]
    replica_counts = [int(x) for x in args.replicas.split(",")]

    # Determine CRDTs to benchmark
    crdt_types = ["g-counter", "pn-counter", "or-set", "lww-set", "rga"] if args.crdt_type == "all" else [args.crdt_type]

    all_results = []

    for crdt_type in crdt_types:
        if not args.json:
            print(f"\n{'='*60}")
            print(f"Benchmarking: {crdt_type.upper()}")
            print(f"{'='*60}\n")

        try:
            # Run benchmarks
            if args.benchmark in ["merge-scaling", "all"]:
                if not args.json:
                    print(f"Running merge scaling benchmark (sizes: {sizes})...")
                results = run_merge_scaling_benchmark(crdt_type, sizes)
                all_results.extend(results)

                if not args.json:
                    print(f"\n{'State Size':<12} {'Merge Time (ms)':<18} {'Ops/sec':<12} {'Memory (KB)':<12}")
                    print("-" * 60)
                    for r in results:
                        print(f"{r.state_size:<12} {r.merge_time_ms:<18.4f} {r.operations_per_sec:<12.2f} {r.memory_bytes/1024:<12.2f}")

            if args.benchmark in ["replica-scaling", "all"]:
                if not args.json:
                    print(f"\nRunning replica scaling benchmark (replicas: {replica_counts})...")
                results = run_replica_scaling_benchmark(crdt_type, replica_counts)
                all_results.extend(results)

                if not args.json:
                    print(f"\n{'Replicas':<12} {'Merge Time (ms)':<18} {'Ops/sec':<12} {'Memory (KB)':<12}")
                    print("-" * 60)
                    for r in results:
                        print(f"{r.n_replicas:<12} {r.merge_time_ms:<18.4f} {r.operations_per_sec:<12.2f} {r.memory_bytes/1024:<12.2f}")

            if args.benchmark in ["conflict-rate", "all"] and crdt_type in ["or-set", "lww-set"]:
                if not args.json:
                    print(f"\nRunning conflict rate benchmark...")
                conflict_rates = [0.1, 0.3, 0.5, 0.7, 0.9]
                results = run_conflict_rate_benchmark(crdt_type, conflict_rates)
                all_results.extend(results)

                if not args.json:
                    print(f"\n{'Conflict Rate':<15} {'Merge Time (ms)':<18} {'Ops/sec':<12}")
                    print("-" * 50)
                    for r, rate in zip(results, conflict_rates):
                        print(f"{rate:<15.2f} {r.merge_time_ms:<18.4f} {r.operations_per_sec:<12.2f}")

            if args.benchmark in ["operations", "all"]:
                if not args.json:
                    print(f"\nRunning operation benchmark...")
                result = run_operation_benchmark(crdt_type, 1000)
                all_results.append(result)

                if not args.json:
                    print(f"\nOperation Performance:")
                    print(f"  Operations/sec: {result.operations_per_sec:.2f}")
                    print(f"  Avg time per op: {result.merge_time_ms:.6f} ms")
                    print(f"  Memory: {result.memory_bytes/1024:.2f} KB")

        except Exception as e:
            if args.json:
                print(json.dumps({"error": str(e)}, indent=2))
            else:
                print(f"Error benchmarking {crdt_type}: {e}", file=sys.stderr)

    # Output JSON results
    if args.json:
        output = {
            "benchmark": args.benchmark,
            "results": [
                {
                    "crdt_type": r.crdt_type,
                    "scenario": r.scenario,
                    "n_replicas": r.n_replicas,
                    "state_size": r.state_size,
                    "merge_time_ms": r.merge_time_ms,
                    "memory_bytes": r.memory_bytes,
                    "operations_per_sec": r.operations_per_sec
                }
                for r in all_results
            ]
        }
        print(json.dumps(output, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
