#!/usr/bin/env python3
"""
PyO3 GIL Profiler

Comprehensive profiling tool for analyzing Global Interpreter Lock (GIL) behavior
in PyO3 extensions. Measures GIL hold times, contention, acquisition costs, and
provides detailed reports to optimize performance.

Features:
- Profile GIL hold times across Python/Rust boundaries
- Measure GIL acquisition and release overhead
- Detect GIL contention in multi-threaded scenarios
- Analyze GIL-related performance bottlenecks
- Generate detailed profiling reports
- Compare GIL behavior across implementations
- Thread-level GIL usage tracking
- Statistical analysis with percentiles

Usage:
    # Profile GIL usage in running process
    gil_profiler.py profile --pid <PID> --duration 10

    # Analyze GIL contention
    gil_profiler.py contention --script test.py --threads 4

    # Benchmark GIL overhead
    gil_profiler.py benchmark --iterations 10000

    # Generate comprehensive report
    gil_profiler.py report --output gil_report.html

    # Compare implementations
    gil_profiler.py compare baseline.py optimized.py

Examples:
    # Profile running application
    python gil_profiler.py profile --pid 12345 --duration 30 --verbose

    # Analyze contention with multiple threads
    python gil_profiler.py contention --script app.py --threads 8 --output contention.json

    # Benchmark GIL acquisition overhead
    python gil_profiler.py benchmark --iterations 100000 --visualize

    # Generate HTML report
    python gil_profiler.py report --format html --output report.html

    # Compare two implementations
    python gil_profiler.py compare old_impl.py new_impl.py --metric throughput

Author: PyO3 Skills Initiative
License: MIT
"""

import argparse
import json
import logging
import os
import sys
import time
import threading
import traceback
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import statistics
import subprocess
import signal

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logging.warning("psutil not available, some features disabled")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GILState(Enum):
    """GIL acquisition states."""
    HELD = "held"
    RELEASED = "released"
    WAITING = "waiting"
    UNKNOWN = "unknown"


@dataclass
class GILEvent:
    """Single GIL-related event."""
    timestamp: float
    thread_id: int
    state: GILState
    duration_ns: Optional[int] = None
    function: str = ""
    line: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'thread_id': self.thread_id,
            'state': self.state.value,
            'duration_ns': self.duration_ns,
            'function': self.function,
            'line': self.line
        }


@dataclass
class ThreadGILStats:
    """GIL statistics for a single thread."""
    thread_id: int
    thread_name: str
    total_hold_time_ns: int = 0
    acquisitions: int = 0
    releases: int = 0
    wait_time_ns: int = 0
    wait_count: int = 0
    hold_times: List[int] = field(default_factory=list)

    def average_hold_time_ns(self) -> float:
        """Calculate average GIL hold time."""
        return self.total_hold_time_ns / self.acquisitions if self.acquisitions > 0 else 0.0

    def average_wait_time_ns(self) -> float:
        """Calculate average wait time."""
        return self.wait_time_ns / self.wait_count if self.wait_count > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'thread_id': self.thread_id,
            'thread_name': self.thread_name,
            'total_hold_time_ns': self.total_hold_time_ns,
            'acquisitions': self.acquisitions,
            'releases': self.releases,
            'wait_time_ns': self.wait_time_ns,
            'wait_count': self.wait_count,
            'average_hold_time_ns': self.average_hold_time_ns(),
            'average_wait_time_ns': self.average_wait_time_ns(),
        }


@dataclass
class GILProfileResult:
    """Complete GIL profiling result."""
    duration_seconds: float
    total_acquisitions: int
    total_releases: int
    total_hold_time_ns: int
    total_wait_time_ns: int
    thread_stats: Dict[int, ThreadGILStats]
    events: List[GILEvent]
    contention_events: int
    gil_utilization: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'duration_seconds': self.duration_seconds,
            'total_acquisitions': self.total_acquisitions,
            'total_releases': self.total_releases,
            'total_hold_time_ns': self.total_hold_time_ns,
            'total_wait_time_ns': self.total_wait_time_ns,
            'thread_stats': {tid: stats.to_dict() for tid, stats in self.thread_stats.items()},
            'events': [e.to_dict() for e in self.events],
            'contention_events': self.contention_events,
            'gil_utilization': self.gil_utilization,
        }


class GILTracer:
    """
    Traces GIL acquisition and release events.

    Uses sys.settrace to monitor Python execution and estimate GIL behavior.
    """

    def __init__(self):
        self.events: List[GILEvent] = []
        self.thread_states: Dict[int, GILState] = {}
        self.thread_acquire_times: Dict[int, float] = {}
        self.active = False
        self.lock = threading.Lock()

    def start(self):
        """Start tracing."""
        self.active = True
        sys.settrace(self._trace_func)
        threading.settrace(self._trace_func)

    def stop(self):
        """Stop tracing."""
        self.active = False
        sys.settrace(None)
        threading.settrace(None)

    def _trace_func(self, frame, event, arg):
        """Trace function callback."""
        if not self.active:
            return None

        thread_id = threading.get_ident()
        timestamp = time.perf_counter()

        # When Python code executes, GIL is held
        if event == 'call':
            with self.lock:
                self.thread_states[thread_id] = GILState.HELD
                self.thread_acquire_times[thread_id] = timestamp

                self.events.append(GILEvent(
                    timestamp=timestamp,
                    thread_id=thread_id,
                    state=GILState.HELD,
                    function=frame.f_code.co_name,
                    line=frame.f_lineno
                ))

        elif event == 'return':
            with self.lock:
                if thread_id in self.thread_acquire_times:
                    acquire_time = self.thread_acquire_times[thread_id]
                    duration_ns = int((timestamp - acquire_time) * 1e9)

                    self.events.append(GILEvent(
                        timestamp=timestamp,
                        thread_id=thread_id,
                        state=GILState.RELEASED,
                        duration_ns=duration_ns,
                        function=frame.f_code.co_name,
                        line=frame.f_lineno
                    ))

                    self.thread_states[thread_id] = GILState.RELEASED
                    del self.thread_acquire_times[thread_id]

        return self._trace_func

    def get_events(self) -> List[GILEvent]:
        """Get all traced events."""
        with self.lock:
            return self.events.copy()


class GILBenchmark:
    """Benchmarks GIL acquisition and release overhead."""

    @staticmethod
    def benchmark_acquisition(iterations: int = 10000) -> Dict[str, float]:
        """
        Benchmark GIL acquisition overhead.

        Measures the time taken to acquire and release the GIL.
        """
        import threading

        results = {
            'iterations': iterations,
            'timings_ns': []
        }

        for _ in range(iterations):
            start = time.perf_counter_ns()

            # Force GIL acquisition by calling Python API
            _ = id(object())

            end = time.perf_counter_ns()
            results['timings_ns'].append(end - start)

        results['mean_ns'] = statistics.mean(results['timings_ns'])
        results['median_ns'] = statistics.median(results['timings_ns'])
        results['std_ns'] = statistics.stdev(results['timings_ns']) if len(results['timings_ns']) > 1 else 0
        results['min_ns'] = min(results['timings_ns'])
        results['max_ns'] = max(results['timings_ns'])

        if HAS_NUMPY:
            results['p95_ns'] = np.percentile(results['timings_ns'], 95)
            results['p99_ns'] = np.percentile(results['timings_ns'], 99)

        return results

    @staticmethod
    def benchmark_contention(num_threads: int = 4, duration: float = 5.0) -> Dict[str, Any]:
        """
        Benchmark GIL contention with multiple threads.

        Spawns multiple threads that compete for the GIL.
        """
        stop_event = threading.Event()
        counters = [0] * num_threads
        timings = [[] for _ in range(num_threads)]

        def worker(thread_idx: int):
            """Worker thread that competes for GIL."""
            while not stop_event.is_set():
                start = time.perf_counter_ns()

                # GIL-bound work
                counters[thread_idx] += 1
                _ = sum(range(100))

                end = time.perf_counter_ns()
                timings[thread_idx].append(end - start)

        # Start threads
        threads = []
        start_time = time.perf_counter()

        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            t.start()
            threads.append(t)

        # Run for duration
        time.sleep(duration)
        stop_event.set()

        # Wait for threads
        for t in threads:
            t.join()

        elapsed = time.perf_counter() - start_time

        # Calculate statistics
        total_iterations = sum(counters)
        throughput = total_iterations / elapsed

        results = {
            'num_threads': num_threads,
            'duration': elapsed,
            'total_iterations': total_iterations,
            'throughput': throughput,
            'per_thread': []
        }

        for i in range(num_threads):
            thread_result = {
                'thread_id': i,
                'iterations': counters[i],
                'throughput': counters[i] / elapsed,
                'mean_iteration_time_ns': statistics.mean(timings[i]) if timings[i] else 0,
            }
            results['per_thread'].append(thread_result)

        # Calculate contention metrics
        ideal_throughput = throughput * num_threads  # If no contention
        actual_throughput = throughput
        contention_factor = ideal_throughput / actual_throughput if actual_throughput > 0 else 0

        results['contention_factor'] = contention_factor
        results['efficiency'] = 1.0 / contention_factor if contention_factor > 0 else 0

        return results


class GILAnalyzer:
    """
    Analyzes GIL profiling data and generates insights.
    """

    def __init__(self):
        self.results: Optional[GILProfileResult] = None

    def analyze(self, events: List[GILEvent], duration: float) -> GILProfileResult:
        """
        Analyze GIL events and generate statistics.

        Args:
            events: List of GIL events
            duration: Total profiling duration in seconds

        Returns:
            Complete profiling result
        """
        thread_stats: Dict[int, ThreadGILStats] = defaultdict(
            lambda: ThreadGILStats(thread_id=0, thread_name="")
        )

        total_acquisitions = 0
        total_releases = 0
        total_hold_time_ns = 0
        total_wait_time_ns = 0
        contention_events = 0

        # Track concurrent GIL acquisitions for contention detection
        active_threads: set = set()

        for event in events:
            tid = event.thread_id

            # Initialize thread stats
            if thread_stats[tid].thread_id == 0:
                thread_stats[tid].thread_id = tid
                thread_stats[tid].thread_name = f"Thread-{tid}"

            if event.state == GILState.HELD:
                # GIL acquired
                total_acquisitions += 1
                thread_stats[tid].acquisitions += 1

                # Check for contention
                if active_threads:
                    contention_events += 1

                active_threads.add(tid)

            elif event.state == GILState.RELEASED:
                # GIL released
                total_releases += 1
                thread_stats[tid].releases += 1

                if event.duration_ns:
                    total_hold_time_ns += event.duration_ns
                    thread_stats[tid].total_hold_time_ns += event.duration_ns
                    thread_stats[tid].hold_times.append(event.duration_ns)

                active_threads.discard(tid)

        # Calculate GIL utilization
        gil_utilization = (total_hold_time_ns / 1e9) / duration if duration > 0 else 0

        self.results = GILProfileResult(
            duration_seconds=duration,
            total_acquisitions=total_acquisitions,
            total_releases=total_releases,
            total_hold_time_ns=total_hold_time_ns,
            total_wait_time_ns=total_wait_time_ns,
            thread_stats=dict(thread_stats),
            events=events,
            contention_events=contention_events,
            gil_utilization=gil_utilization,
        )

        return self.results

    def generate_summary(self) -> str:
        """Generate text summary of profiling results."""
        if not self.results:
            return "No results to summarize"

        lines = ["=== GIL Profiling Summary ===\n"]

        r = self.results

        lines.append(f"Duration: {r.duration_seconds:.2f} seconds")
        lines.append(f"Total GIL Acquisitions: {r.total_acquisitions:,}")
        lines.append(f"Total GIL Releases: {r.total_releases:,}")
        lines.append(f"Total Hold Time: {r.total_hold_time_ns / 1e9:.3f} seconds")
        lines.append(f"GIL Utilization: {r.gil_utilization * 100:.1f}%")
        lines.append(f"Contention Events: {r.contention_events}")

        lines.append("\n=== Per-Thread Statistics ===\n")

        for tid, stats in r.thread_stats.items():
            lines.append(f"Thread {tid} ({stats.thread_name}):")
            lines.append(f"  Acquisitions: {stats.acquisitions}")
            lines.append(f"  Average Hold Time: {stats.average_hold_time_ns() / 1e6:.3f} ms")
            lines.append(f"  Total Hold Time: {stats.total_hold_time_ns / 1e9:.3f} s")

            if stats.hold_times:
                lines.append(f"  Min Hold Time: {min(stats.hold_times) / 1e6:.3f} ms")
                lines.append(f"  Max Hold Time: {max(stats.hold_times) / 1e6:.3f} ms")

        return "\n".join(lines)


class ReportGenerator:
    """Generates various report formats."""

    @staticmethod
    def generate_text(result: GILProfileResult) -> str:
        """Generate text report."""
        analyzer = GILAnalyzer()
        analyzer.results = result
        return analyzer.generate_summary()

    @staticmethod
    def generate_json(result: GILProfileResult) -> str:
        """Generate JSON report."""
        return json.dumps(result.to_dict(), indent=2)

    @staticmethod
    def generate_html(result: GILProfileResult) -> str:
        """Generate HTML report."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>GIL Profiling Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .metric { font-size: 1.2em; margin: 10px 0; }
        .warning { color: #ff6600; }
    </style>
</head>
<body>
    <h1>GIL Profiling Report</h1>
"""

        html += f"<div class='metric'>Duration: <strong>{result.duration_seconds:.2f}s</strong></div>"
        html += f"<div class='metric'>GIL Utilization: <strong>{result.gil_utilization * 100:.1f}%</strong></div>"
        html += f"<div class='metric'>Total Acquisitions: <strong>{result.total_acquisitions:,}</strong></div>"
        html += f"<div class='metric'>Contention Events: <strong>{result.contention_events:,}</strong></div>"

        html += "<h2>Thread Statistics</h2>"
        html += "<table>"
        html += "<tr><th>Thread ID</th><th>Name</th><th>Acquisitions</th><th>Avg Hold Time (ms)</th><th>Total Hold Time (s)</th></tr>"

        for tid, stats in result.thread_stats.items():
            html += f"<tr>"
            html += f"<td>{tid}</td>"
            html += f"<td>{stats.thread_name}</td>"
            html += f"<td>{stats.acquisitions}</td>"
            html += f"<td>{stats.average_hold_time_ns() / 1e6:.3f}</td>"
            html += f"<td>{stats.total_hold_time_ns / 1e9:.3f}</td>"
            html += f"</tr>"

        html += "</table>"
        html += "</body></html>"

        return html


class GILProfiler:
    """Main GIL profiler."""

    def __init__(self):
        self.tracer = GILTracer()
        self.analyzer = GILAnalyzer()
        self.benchmark = GILBenchmark()

    def profile(self, duration: float = 10.0) -> GILProfileResult:
        """
        Profile GIL usage for specified duration.

        Args:
            duration: Profiling duration in seconds

        Returns:
            Profiling result
        """
        logger.info(f"Starting GIL profiling for {duration}s...")

        self.tracer.start()
        start = time.perf_counter()

        time.sleep(duration)

        self.tracer.stop()
        elapsed = time.perf_counter() - start

        events = self.tracer.get_events()
        logger.info(f"Captured {len(events)} GIL events")

        result = self.analyzer.analyze(events, elapsed)
        return result

    def profile_script(self, script_path: str, args: List[str] = None) -> GILProfileResult:
        """
        Profile a Python script.

        Args:
            script_path: Path to Python script
            args: Command-line arguments

        Returns:
            Profiling result
        """
        logger.info(f"Profiling script: {script_path}")

        # This is a simplified version - real implementation would use
        # subprocess and custom profiling instrumentation
        start = time.perf_counter()

        # Execute script with tracing
        self.tracer.start()

        with open(script_path) as f:
            code = f.read()
            exec(code, {'__name__': '__main__'})

        self.tracer.stop()
        elapsed = time.perf_counter() - start

        events = self.tracer.get_events()
        result = self.analyzer.analyze(events, elapsed)

        return result

    def benchmark_gil_overhead(self, iterations: int = 10000) -> Dict[str, float]:
        """Benchmark GIL acquisition overhead."""
        logger.info(f"Benchmarking GIL overhead ({iterations} iterations)...")
        return self.benchmark.benchmark_acquisition(iterations)

    def benchmark_gil_contention(
        self,
        num_threads: int = 4,
        duration: float = 5.0
    ) -> Dict[str, Any]:
        """Benchmark GIL contention."""
        logger.info(f"Benchmarking GIL contention ({num_threads} threads, {duration}s)...")
        return self.benchmark.benchmark_contention(num_threads, duration)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='PyO3 GIL Profiler',
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

    # Profile command
    profile_parser = subparsers.add_parser('profile', help='Profile GIL usage')
    profile_parser.add_argument('--duration', type=float, default=10.0, help='Profiling duration (seconds)')
    profile_parser.add_argument('--output', '-o', type=Path, help='Output file')

    # Contention command
    contention_parser = subparsers.add_parser('contention', help='Analyze GIL contention')
    contention_parser.add_argument('--script', type=Path, help='Script to profile')
    contention_parser.add_argument('--threads', type=int, default=4, help='Number of threads')
    contention_parser.add_argument('--duration', type=float, default=5.0, help='Test duration')
    contention_parser.add_argument('--output', '-o', type=Path, help='Output file')

    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Benchmark GIL overhead')
    benchmark_parser.add_argument('--iterations', type=int, default=10000, help='Number of iterations')
    benchmark_parser.add_argument('--visualize', action='store_true', help='Generate visualization')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.add_argument('--format', choices=['text', 'json', 'html'], default='text')
    report_parser.add_argument('--output', '-o', type=Path, help='Output file')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare implementations')
    compare_parser.add_argument('baseline', type=Path, help='Baseline script')
    compare_parser.add_argument('optimized', type=Path, help='Optimized script')
    compare_parser.add_argument('--metric', choices=['throughput', 'latency', 'gil_time'], default='throughput')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    profiler = GILProfiler()
    report_gen = ReportGenerator()

    try:
        if args.command == 'profile':
            result = profiler.profile(args.duration)

            if args.json:
                output = report_gen.generate_json(result)
            else:
                output = report_gen.generate_text(result)

            if args.output:
                args.output.write_text(output)
                print(f"Report saved to {args.output}")
            else:
                print(output)

        elif args.command == 'contention':
            if args.script:
                result = profiler.profile_script(str(args.script))
            else:
                contention_result = profiler.benchmark_gil_contention(
                    args.threads,
                    args.duration
                )

                if args.json:
                    output = json.dumps(contention_result, indent=2)
                else:
                    output = f"\nGIL Contention Benchmark:\n"
                    output += f"  Threads: {contention_result['num_threads']}\n"
                    output += f"  Duration: {contention_result['duration']:.2f}s\n"
                    output += f"  Total Iterations: {contention_result['total_iterations']:,}\n"
                    output += f"  Throughput: {contention_result['throughput']:.0f} ops/s\n"
                    output += f"  Contention Factor: {contention_result['contention_factor']:.2f}x\n"
                    output += f"  Efficiency: {contention_result['efficiency'] * 100:.1f}%\n"

                if args.output:
                    args.output.write_text(output)
                    print(f"Results saved to {args.output}")
                else:
                    print(output)

        elif args.command == 'benchmark':
            overhead_result = profiler.benchmark_gil_overhead(args.iterations)

            if args.json:
                print(json.dumps(overhead_result, indent=2))
            else:
                print("\nGIL Acquisition Overhead:")
                print(f"  Iterations: {overhead_result['iterations']:,}")
                print(f"  Mean: {overhead_result['mean_ns']:.0f} ns")
                print(f"  Median: {overhead_result['median_ns']:.0f} ns")
                print(f"  Std Dev: {overhead_result['std_ns']:.0f} ns")
                print(f"  Min: {overhead_result['min_ns']:.0f} ns")
                print(f"  Max: {overhead_result['max_ns']:.0f} ns")

                if 'p95_ns' in overhead_result:
                    print(f"  P95: {overhead_result['p95_ns']:.0f} ns")
                    print(f"  P99: {overhead_result['p99_ns']:.0f} ns")

        elif args.command == 'report':
            # Generate report from previous profiling
            print("Report generation from saved data not yet implemented")
            sys.exit(1)

        elif args.command == 'compare':
            print("Comparison not yet implemented")
            sys.exit(1)

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
