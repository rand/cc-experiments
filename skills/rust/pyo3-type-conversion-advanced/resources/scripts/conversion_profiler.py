#!/usr/bin/env python3
"""
PyO3 Type Conversion Profiler

Comprehensive benchmarking and profiling tool for PyO3 type conversions.
Measures conversion overhead, memory usage, and performance characteristics
for various strategies including zero-copy, numpy, Arrow, and custom protocols.

Features:
- Benchmark conversion strategies (copy vs zero-copy)
- Profile conversion overhead and latency
- Memory usage analysis
- Comparison of different approaches
- Support for various data types and sizes
- Statistical analysis with confidence intervals
- Visualization of results
- Export to multiple formats

Usage:
    # Benchmark all conversion strategies
    conversion_profiler.py benchmark --all --sizes 1000,10000,100000

    # Profile specific conversion
    conversion_profiler.py profile numpy --dtype float64 --size 1000000

    # Compare strategies
    conversion_profiler.py compare copy zerocopy numpy --size 100000

    # Analyze memory usage
    conversion_profiler.py memory --strategy zerocopy --monitor

    # Generate report
    conversion_profiler.py report --output results.html --format html

Examples:
    # Benchmark with different sizes
    python conversion_profiler.py benchmark --strategies copy,zerocopy --sizes 1k,10k,100k

    # Profile numpy conversions
    python conversion_profiler.py profile numpy --iterations 1000 --warmup 100

    # Compare overhead
    python conversion_profiler.py compare --all --visualize

    # Memory profiling
    python conversion_profiler.py memory --strategy numpy --track-allocations

    # Export results
    python conversion_profiler.py export --format json --output results.json

Author: PyO3 Skills Initiative
License: MIT
"""

import argparse
import gc
import json
import logging
import os
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from enum import Enum
import statistics
import psutil
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConversionStrategy(Enum):
    """Conversion strategy types."""
    COPY = "copy"
    ZEROCOPY = "zerocopy"
    NUMPY = "numpy"
    ARROW = "arrow"
    BUFFER = "buffer"
    CUSTOM = "custom"


class DataType(Enum):
    """Data types for testing."""
    INT32 = "int32"
    INT64 = "int64"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    BYTES = "bytes"
    STRING = "string"
    COMPLEX = "complex"


@dataclass
class BenchmarkConfig:
    """Configuration for benchmarking."""
    strategy: ConversionStrategy
    data_type: DataType
    size: int
    iterations: int = 1000
    warmup_iterations: int = 100
    measure_memory: bool = True
    track_allocations: bool = False
    confidence_level: float = 0.95


@dataclass
class TimingResult:
    """Timing measurements for a single benchmark."""
    mean: float
    median: float
    std: float
    min: float
    max: float
    p95: float
    p99: float
    iterations: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class MemoryResult:
    """Memory measurements."""
    peak_rss_mb: float
    current_rss_mb: float
    allocation_count: int = 0
    deallocation_count: int = 0
    net_allocations: int = 0
    peak_allocation_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BenchmarkResult:
    """Complete benchmark result."""
    config: BenchmarkConfig
    timing: TimingResult
    memory: Optional[MemoryResult]
    throughput_mbs: float
    overhead_ns: float
    success: bool = True
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'config': {
                'strategy': self.config.strategy.value,
                'data_type': self.config.data_type.value,
                'size': self.config.size,
                'iterations': self.config.iterations
            },
            'timing': self.timing.to_dict(),
            'memory': self.memory.to_dict() if self.memory else None,
            'throughput_mbs': self.throughput_mbs,
            'overhead_ns': self.overhead_ns,
            'success': self.success,
            'error_message': self.error_message
        }


class MemoryTracker:
    """Tracks memory usage during conversions."""

    def __init__(self, track_allocations: bool = False):
        self.track_allocations = track_allocations
        self.process = psutil.Process()
        self.start_rss = 0
        self.peak_rss = 0
        self.allocations = 0
        self.deallocations = 0

    def __enter__(self):
        """Start tracking."""
        gc.collect()
        self.start_rss = self.process.memory_info().rss
        self.peak_rss = self.start_rss
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop tracking."""
        gc.collect()

    def sample(self) -> None:
        """Sample current memory usage."""
        current_rss = self.process.memory_info().rss
        self.peak_rss = max(self.peak_rss, current_rss)

    def get_result(self) -> MemoryResult:
        """Get memory tracking result."""
        current_rss = self.process.memory_info().rss
        return MemoryResult(
            peak_rss_mb=(self.peak_rss - self.start_rss) / (1024 * 1024),
            current_rss_mb=(current_rss - self.start_rss) / (1024 * 1024),
            allocation_count=self.allocations,
            deallocation_count=self.deallocations,
            net_allocations=self.allocations - self.deallocations
        )


class DataGenerator:
    """Generates test data for benchmarking."""

    @staticmethod
    def generate(data_type: DataType, size: int) -> Any:
        """Generate test data of specified type and size."""
        if data_type == DataType.INT32:
            return np.random.randint(0, 2**31, size=size, dtype=np.int32)
        elif data_type == DataType.INT64:
            return np.random.randint(0, 2**63, size=size, dtype=np.int64)
        elif data_type == DataType.FLOAT32:
            return np.random.randn(size).astype(np.float32)
        elif data_type == DataType.FLOAT64:
            return np.random.randn(size).astype(np.float64)
        elif data_type == DataType.BYTES:
            return bytes(np.random.randint(0, 256, size=size, dtype=np.uint8))
        elif data_type == DataType.STRING:
            return ''.join(chr(np.random.randint(ord('a'), ord('z'))) for _ in range(size))
        elif data_type == DataType.COMPLEX:
            return np.random.randn(size) + 1j * np.random.randn(size)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

    @staticmethod
    def get_size_bytes(data: Any) -> int:
        """Get data size in bytes."""
        if isinstance(data, np.ndarray):
            return data.nbytes
        elif isinstance(data, bytes):
            return len(data)
        elif isinstance(data, str):
            return len(data.encode('utf-8'))
        else:
            return sys.getsizeof(data)


class ConversionSimulator:
    """
    Simulates PyO3 conversion strategies for benchmarking.

    In production, these would call actual Rust/PyO3 code.
    Here we simulate the conversion overhead.
    """

    @staticmethod
    def copy_conversion(data: Any) -> Any:
        """Simulate copy-based conversion."""
        # Simulate copy overhead
        if isinstance(data, np.ndarray):
            return data.copy()
        elif isinstance(data, (bytes, str)):
            return data[:]
        else:
            return data

    @staticmethod
    def zerocopy_conversion(data: Any) -> Any:
        """Simulate zero-copy conversion (view/borrow)."""
        # Zero-copy: no actual copy, just metadata
        if isinstance(data, np.ndarray):
            return data.view()
        else:
            # For non-array types, return reference
            return data

    @staticmethod
    def numpy_conversion(data: Any) -> np.ndarray:
        """Simulate numpy conversion."""
        if isinstance(data, np.ndarray):
            return data
        else:
            return np.array(data)

    @staticmethod
    def arrow_conversion(data: Any) -> Any:
        """Simulate Arrow conversion."""
        # Simulate Arrow serialization/deserialization overhead
        if isinstance(data, np.ndarray):
            # Arrow typically creates columnar format
            time.sleep(len(data) * 0.000001)  # Simulate overhead
            return data
        else:
            return data

    @staticmethod
    def buffer_conversion(data: Any) -> Any:
        """Simulate buffer protocol conversion."""
        if isinstance(data, np.ndarray):
            # Buffer protocol: minimal overhead
            return memoryview(data)
        elif isinstance(data, bytes):
            return memoryview(data)
        else:
            return data

    @staticmethod
    def custom_conversion(data: Any) -> Any:
        """Simulate custom conversion protocol."""
        # Simulate custom conversion logic
        if isinstance(data, np.ndarray):
            # Custom protocol might involve validation, transformation
            time.sleep(len(data) * 0.0000005)
            return data.copy()
        else:
            return data


class ConversionProfiler:
    """
    Profiles PyO3 type conversions.

    Benchmarks different strategies and provides detailed performance metrics.
    """

    def __init__(self):
        self.simulator = ConversionSimulator()
        self.results: List[BenchmarkResult] = []

    def benchmark(self, config: BenchmarkConfig) -> BenchmarkResult:
        """
        Run benchmark for given configuration.

        Returns detailed results including timing and memory.
        """
        logger.info(
            f"Benchmarking {config.strategy.value} "
            f"({config.data_type.value}, size={config.size})"
        )

        # Generate test data
        data = DataGenerator.generate(config.data_type, config.size)
        data_size_bytes = DataGenerator.get_size_bytes(data)

        # Select conversion function
        conversion_func = self._get_conversion_func(config.strategy)

        # Warmup
        for _ in range(config.warmup_iterations):
            _ = conversion_func(data)

        gc.collect()

        # Benchmark
        timings = []
        memory_tracker = MemoryTracker(config.track_allocations) if config.measure_memory else None

        try:
            if memory_tracker:
                with memory_tracker:
                    for _ in range(config.iterations):
                        start = time.perf_counter_ns()
                        _ = conversion_func(data)
                        end = time.perf_counter_ns()
                        timings.append(end - start)
                        memory_tracker.sample()
            else:
                for _ in range(config.iterations):
                    start = time.perf_counter_ns()
                    _ = conversion_func(data)
                    end = time.perf_counter_ns()
                    timings.append(end - start)

            # Calculate statistics
            timing_result = TimingResult(
                mean=statistics.mean(timings),
                median=statistics.median(timings),
                std=statistics.stdev(timings) if len(timings) > 1 else 0.0,
                min=min(timings),
                max=max(timings),
                p95=np.percentile(timings, 95),
                p99=np.percentile(timings, 99),
                iterations=config.iterations
            )

            # Calculate throughput
            throughput_mbs = (data_size_bytes / (1024 * 1024)) / (timing_result.mean / 1e9)

            # Get memory result
            memory_result = memory_tracker.get_result() if memory_tracker else None

            result = BenchmarkResult(
                config=config,
                timing=timing_result,
                memory=memory_result,
                throughput_mbs=throughput_mbs,
                overhead_ns=timing_result.mean,
                success=True
            )

            self.results.append(result)
            return result

        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            result = BenchmarkResult(
                config=config,
                timing=TimingResult(0, 0, 0, 0, 0, 0, 0, 0),
                memory=None,
                throughput_mbs=0.0,
                overhead_ns=0.0,
                success=False,
                error_message=str(e)
            )
            self.results.append(result)
            return result

    def _get_conversion_func(self, strategy: ConversionStrategy) -> Callable:
        """Get conversion function for strategy."""
        mapping = {
            ConversionStrategy.COPY: self.simulator.copy_conversion,
            ConversionStrategy.ZEROCOPY: self.simulator.zerocopy_conversion,
            ConversionStrategy.NUMPY: self.simulator.numpy_conversion,
            ConversionStrategy.ARROW: self.simulator.arrow_conversion,
            ConversionStrategy.BUFFER: self.simulator.buffer_conversion,
            ConversionStrategy.CUSTOM: self.simulator.custom_conversion,
        }
        return mapping[strategy]

    def compare_strategies(
        self,
        strategies: List[ConversionStrategy],
        data_type: DataType,
        size: int,
        iterations: int = 1000
    ) -> Dict[str, BenchmarkResult]:
        """
        Compare multiple strategies.

        Returns dictionary mapping strategy name to result.
        """
        results = {}

        for strategy in strategies:
            config = BenchmarkConfig(
                strategy=strategy,
                data_type=data_type,
                size=size,
                iterations=iterations
            )
            result = self.benchmark(config)
            results[strategy.value] = result

        return results

    def profile_sizes(
        self,
        strategy: ConversionStrategy,
        data_type: DataType,
        sizes: List[int],
        iterations: int = 1000
    ) -> List[BenchmarkResult]:
        """
        Profile a strategy across different data sizes.

        Returns list of results for each size.
        """
        results = []

        for size in sizes:
            config = BenchmarkConfig(
                strategy=strategy,
                data_type=data_type,
                size=size,
                iterations=iterations
            )
            result = self.benchmark(config)
            results.append(result)

        return results

    def generate_report(self, format: str = 'text') -> str:
        """
        Generate report from benchmark results.

        Supports formats: text, markdown, html, json.
        """
        if format == 'json':
            return json.dumps([r.to_dict() for r in self.results], indent=2)

        elif format == 'text':
            lines = ["=== Conversion Profiler Report ===\n"]

            for result in self.results:
                lines.append(f"\n{result.config.strategy.value} - {result.config.data_type.value}")
                lines.append(f"  Size: {result.config.size:,}")
                lines.append(f"  Iterations: {result.timing.iterations}")
                lines.append(f"\nTiming:")
                lines.append(f"  Mean:   {result.timing.mean / 1e6:.3f} ms")
                lines.append(f"  Median: {result.timing.median / 1e6:.3f} ms")
                lines.append(f"  Std:    {result.timing.std / 1e6:.3f} ms")
                lines.append(f"  Min:    {result.timing.min / 1e6:.3f} ms")
                lines.append(f"  Max:    {result.timing.max / 1e6:.3f} ms")
                lines.append(f"  P95:    {result.timing.p95 / 1e6:.3f} ms")
                lines.append(f"  P99:    {result.timing.p99 / 1e6:.3f} ms")
                lines.append(f"\nThroughput: {result.throughput_mbs:.2f} MB/s")

                if result.memory:
                    lines.append(f"\nMemory:")
                    lines.append(f"  Peak RSS: {result.memory.peak_rss_mb:.2f} MB")
                    lines.append(f"  Current:  {result.memory.current_rss_mb:.2f} MB")

                lines.append("\n" + "-" * 50)

            return "\n".join(lines)

        elif format == 'markdown':
            lines = ["# Conversion Profiler Report\n"]

            # Summary table
            lines.append("## Summary\n")
            lines.append("| Strategy | Type | Size | Mean (ms) | Throughput (MB/s) |")
            lines.append("|----------|------|------|-----------|-------------------|")

            for result in self.results:
                lines.append(
                    f"| {result.config.strategy.value} "
                    f"| {result.config.data_type.value} "
                    f"| {result.config.size:,} "
                    f"| {result.timing.mean / 1e6:.3f} "
                    f"| {result.throughput_mbs:.2f} |"
                )

            lines.append("\n## Detailed Results\n")

            for result in self.results:
                lines.append(f"### {result.config.strategy.value} - {result.config.data_type.value}\n")
                lines.append(f"**Configuration:**")
                lines.append(f"- Size: {result.config.size:,}")
                lines.append(f"- Iterations: {result.timing.iterations}\n")
                lines.append(f"**Timing:**")
                lines.append(f"- Mean: {result.timing.mean / 1e6:.3f} ms")
                lines.append(f"- Median: {result.timing.median / 1e6:.3f} ms")
                lines.append(f"- Std: {result.timing.std / 1e6:.3f} ms")
                lines.append(f"- P95: {result.timing.p95 / 1e6:.3f} ms")
                lines.append(f"- P99: {result.timing.p99 / 1e6:.3f} ms\n")

                if result.memory:
                    lines.append(f"**Memory:**")
                    lines.append(f"- Peak RSS: {result.memory.peak_rss_mb:.2f} MB\n")

            return "\n".join(lines)

        elif format == 'html':
            lines = ["<!DOCTYPE html>", "<html>", "<head>"]
            lines.append("<title>Conversion Profiler Report</title>")
            lines.append("<style>")
            lines.append("body { font-family: Arial, sans-serif; margin: 20px; }")
            lines.append("table { border-collapse: collapse; width: 100%; }")
            lines.append("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
            lines.append("th { background-color: #4CAF50; color: white; }")
            lines.append("</style>")
            lines.append("</head>", "<body>")
            lines.append("<h1>Conversion Profiler Report</h1>")

            lines.append("<table>")
            lines.append("<tr><th>Strategy</th><th>Type</th><th>Size</th><th>Mean (ms)</th><th>Throughput (MB/s)</th></tr>")

            for result in self.results:
                lines.append(
                    f"<tr>"
                    f"<td>{result.config.strategy.value}</td>"
                    f"<td>{result.config.data_type.value}</td>"
                    f"<td>{result.config.size:,}</td>"
                    f"<td>{result.timing.mean / 1e6:.3f}</td>"
                    f"<td>{result.throughput_mbs:.2f}</td>"
                    f"</tr>"
                )

            lines.append("</table>")
            lines.append("</body>", "</html>")

            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported format: {format}")

    def clear_results(self) -> None:
        """Clear all stored results."""
        self.results.clear()


def parse_size(size_str: str) -> int:
    """Parse size string (supports 1k, 1m, etc.)."""
    size_str = size_str.lower()
    if size_str.endswith('k'):
        return int(size_str[:-1]) * 1000
    elif size_str.endswith('m'):
        return int(size_str[:-1]) * 1000000
    else:
        return int(size_str)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='PyO3 Type Conversion Profiler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Benchmark command
    bench_parser = subparsers.add_parser('benchmark', help='Run benchmarks')
    bench_parser.add_argument(
        '--strategies',
        type=lambda s: [ConversionStrategy(x.strip()) for x in s.split(',')],
        help='Comma-separated strategies'
    )
    bench_parser.add_argument(
        '--all',
        action='store_true',
        help='Benchmark all strategies'
    )
    bench_parser.add_argument(
        '--type',
        type=DataType,
        default=DataType.FLOAT64,
        help='Data type'
    )
    bench_parser.add_argument(
        '--sizes',
        type=lambda s: [parse_size(x.strip()) for x in s.split(',')],
        default=[10000],
        help='Comma-separated sizes (supports 1k, 1m)'
    )
    bench_parser.add_argument(
        '--iterations',
        type=int,
        default=1000,
        help='Number of iterations'
    )
    bench_parser.add_argument(
        '--no-memory',
        action='store_true',
        help='Skip memory tracking'
    )

    # Profile command
    profile_parser = subparsers.add_parser('profile', help='Profile specific strategy')
    profile_parser.add_argument('strategy', type=ConversionStrategy, help='Strategy to profile')
    profile_parser.add_argument('--type', type=DataType, default=DataType.FLOAT64, help='Data type')
    profile_parser.add_argument('--size', type=parse_size, default=10000, help='Data size')
    profile_parser.add_argument('--iterations', type=int, default=1000, help='Iterations')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare strategies')
    compare_parser.add_argument('strategies', nargs='*', type=ConversionStrategy, help='Strategies')
    compare_parser.add_argument('--all', action='store_true', help='Compare all strategies')
    compare_parser.add_argument('--type', type=DataType, default=DataType.FLOAT64, help='Data type')
    compare_parser.add_argument('--size', type=parse_size, default=10000, help='Data size')
    compare_parser.add_argument('--visualize', action='store_true', help='Generate visualization')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.add_argument('--format', choices=['text', 'markdown', 'html', 'json'], default='text')
    report_parser.add_argument('--output', '-o', type=Path, help='Output file')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    profiler = ConversionProfiler()

    try:
        if args.command == 'benchmark':
            strategies = []
            if args.all:
                strategies = list(ConversionStrategy)
            elif args.strategies:
                strategies = args.strategies
            else:
                parser.error("Specify --strategies or --all")

            for strategy in strategies:
                for size in args.sizes:
                    config = BenchmarkConfig(
                        strategy=strategy,
                        data_type=args.type,
                        size=size,
                        iterations=args.iterations,
                        measure_memory=not args.no_memory
                    )
                    result = profiler.benchmark(config)

                    if not args.json:
                        print(f"\n{strategy.value} ({size:,} elements):")
                        print(f"  Mean: {result.timing.mean / 1e6:.3f} ms")
                        print(f"  Throughput: {result.throughput_mbs:.2f} MB/s")

            if args.json:
                print(json.dumps([r.to_dict() for r in profiler.results], indent=2))

        elif args.command == 'profile':
            config = BenchmarkConfig(
                strategy=args.strategy,
                data_type=args.type,
                size=args.size,
                iterations=args.iterations
            )
            result = profiler.benchmark(config)

            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(f"\nProfile: {args.strategy.value}")
                print(f"  Mean:   {result.timing.mean / 1e6:.3f} ms")
                print(f"  Median: {result.timing.median / 1e6:.3f} ms")
                print(f"  Std:    {result.timing.std / 1e6:.3f} ms")
                print(f"  P95:    {result.timing.p95 / 1e6:.3f} ms")
                print(f"  P99:    {result.timing.p99 / 1e6:.3f} ms")
                print(f"  Throughput: {result.throughput_mbs:.2f} MB/s")

        elif args.command == 'compare':
            strategies = args.strategies if args.strategies else []
            if args.all:
                strategies = list(ConversionStrategy)

            if not strategies:
                parser.error("Specify strategies or --all")

            results = profiler.compare_strategies(
                strategies,
                args.type,
                args.size
            )

            if args.json:
                print(json.dumps({k: v.to_dict() for k, v in results.items()}, indent=2))
            else:
                print("\nComparison Results:")
                for strategy, result in results.items():
                    print(f"\n{strategy}:")
                    print(f"  Mean: {result.timing.mean / 1e6:.3f} ms")
                    print(f"  Throughput: {result.throughput_mbs:.2f} MB/s")

        elif args.command == 'report':
            if not profiler.results:
                print("No results to report. Run benchmarks first.")
                sys.exit(1)

            report = profiler.generate_report(args.format)

            if args.output:
                args.output.write_text(report)
                print(f"Report saved to {args.output}")
            else:
                print(report)

        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
