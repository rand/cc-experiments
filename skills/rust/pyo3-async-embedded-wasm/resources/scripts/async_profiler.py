#!/usr/bin/env python3
"""
PyO3 Async Profiler

Comprehensive profiling tool for async operations in PyO3 extensions.
Profiles event loop performance, async/await overhead, Tokio integration,
and identifies async bottlenecks.

Features:
- Profile async function execution times
- Measure event loop overhead and efficiency
- Analyze task scheduling and concurrency
- Detect slow coroutines and blocking operations
- Track async/await transition overhead
- Monitor Tokio runtime performance
- Generate detailed async performance reports
- Compare async vs sync implementations

Usage:
    # Profile async application
    async_profiler.py profile --script app.py --duration 30

    # Analyze event loop
    async_profiler.py event-loop --monitor --duration 10

    # Benchmark async overhead
    async_profiler.py benchmark --iterations 10000

    # Profile specific async function
    async_profiler.py function my_module.async_func --iterations 1000

    # Generate comprehensive report
    async_profiler.py report --output async_report.html

Examples:
    # Profile async application
    python async_profiler.py profile --script async_app.py --verbose

    # Monitor event loop
    python async_profiler.py event-loop --monitor --interval 1

    # Benchmark async overhead
    python async_profiler.py benchmark --iterations 100000 --json

    # Profile specific function
    python async_profiler.py function my_ext.fetch_data --iterations 1000

    # Generate HTML report
    python async_profiler.py report --format html --output report.html

Author: PyO3 Skills Initiative
License: MIT
"""

import argparse
import asyncio
import json
import logging
import sys
import time
import traceback
import importlib
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Coroutine
from enum import Enum
import statistics
import functools

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


class TaskState(Enum):
    """Async task states."""
    PENDING = "pending"
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class AsyncEvent:
    """Single async-related event."""
    timestamp: float
    task_id: int
    state: TaskState
    duration_ns: Optional[int] = None
    function: str = ""
    await_point: bool = False
    blocking: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'task_id': self.task_id,
            'state': self.state.value,
            'duration_ns': self.duration_ns,
            'function': self.function,
            'await_point': self.await_point,
            'blocking': self.blocking
        }


@dataclass
class TaskStats:
    """Statistics for a single async task."""
    task_id: int
    function: str
    start_time: float
    end_time: Optional[float] = None
    total_time_ns: int = 0
    await_count: int = 0
    await_time_ns: int = 0
    execution_time_ns: int = 0
    state: TaskState = TaskState.PENDING
    error: Optional[str] = None

    def completion_time_ns(self) -> int:
        """Calculate total completion time."""
        if self.end_time:
            return int((self.end_time - self.start_time) * 1e9)
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'task_id': self.task_id,
            'function': self.function,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'total_time_ns': self.total_time_ns,
            'await_count': self.await_count,
            'await_time_ns': self.await_time_ns,
            'execution_time_ns': self.execution_time_ns,
            'state': self.state.value,
            'error': self.error,
            'completion_time_ns': self.completion_time_ns()
        }


@dataclass
class EventLoopStats:
    """Event loop performance statistics."""
    duration_seconds: float
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    total_await_time_ns: int
    total_execution_time_ns: int
    blocking_operations: int
    average_task_time_ns: float
    loop_overhead_ns: int

    def efficiency(self) -> float:
        """Calculate event loop efficiency."""
        total_time_ns = self.total_await_time_ns + self.total_execution_time_ns + self.loop_overhead_ns
        if total_time_ns == 0:
            return 0.0
        return self.total_execution_time_ns / total_time_ns

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['efficiency'] = self.efficiency()
        return data


@dataclass
class AsyncProfileResult:
    """Complete async profiling result."""
    duration_seconds: float
    task_stats: Dict[int, TaskStats]
    event_loop_stats: EventLoopStats
    events: List[AsyncEvent]
    slow_coroutines: List[Tuple[str, int]]  # (function, duration_ns)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'duration_seconds': self.duration_seconds,
            'task_stats': {tid: stats.to_dict() for tid, stats in self.task_stats.items()},
            'event_loop_stats': self.event_loop_stats.to_dict(),
            'events': [e.to_dict() for e in self.events],
            'slow_coroutines': [{'function': f, 'duration_ns': d} for f, d in self.slow_coroutines]
        }


class AsyncTracer:
    """
    Traces async execution using asyncio debug mode.
    """

    def __init__(self):
        self.events: List[AsyncEvent] = []
        self.task_stats: Dict[int, TaskStats] = {}
        self.active = False
        self.task_id_counter = 0

    def start(self):
        """Start tracing."""
        self.active = True
        asyncio.get_event_loop().set_debug(True)

    def stop(self):
        """Stop tracing."""
        self.active = False
        asyncio.get_event_loop().set_debug(False)

    def trace_task_start(self, function: str) -> int:
        """Record task start."""
        task_id = self.task_id_counter
        self.task_id_counter += 1

        timestamp = time.perf_counter()

        self.task_stats[task_id] = TaskStats(
            task_id=task_id,
            function=function,
            start_time=timestamp,
            state=TaskState.RUNNING
        )

        self.events.append(AsyncEvent(
            timestamp=timestamp,
            task_id=task_id,
            state=TaskState.RUNNING,
            function=function
        ))

        return task_id

    def trace_task_end(self, task_id: int, success: bool = True, error: Optional[str] = None):
        """Record task completion."""
        timestamp = time.perf_counter()

        if task_id in self.task_stats:
            stats = self.task_stats[task_id]
            stats.end_time = timestamp
            stats.state = TaskState.COMPLETED if success else TaskState.FAILED
            stats.error = error

            self.events.append(AsyncEvent(
                timestamp=timestamp,
                task_id=task_id,
                state=stats.state,
                duration_ns=stats.completion_time_ns(),
                function=stats.function
            ))

    def trace_await(self, task_id: int, await_duration_ns: int):
        """Record await point."""
        if task_id in self.task_stats:
            self.task_stats[task_id].await_count += 1
            self.task_stats[task_id].await_time_ns += await_duration_ns

    def get_stats(self) -> Dict[int, TaskStats]:
        """Get all task statistics."""
        return self.task_stats.copy()

    def get_events(self) -> List[AsyncEvent]:
        """Get all traced events."""
        return self.events.copy()


class AsyncBenchmark:
    """Benchmarks async operation overhead."""

    @staticmethod
    async def benchmark_async_overhead(iterations: int = 10000) -> Dict[str, float]:
        """
        Benchmark async/await overhead.

        Measures the overhead of async function calls and await points.
        """
        timings = []

        async def noop_async():
            """Minimal async function."""
            pass

        for _ in range(iterations):
            start = time.perf_counter_ns()
            await noop_async()
            end = time.perf_counter_ns()
            timings.append(end - start)

        return {
            'iterations': iterations,
            'mean_ns': statistics.mean(timings),
            'median_ns': statistics.median(timings),
            'std_ns': statistics.stdev(timings) if len(timings) > 1 else 0,
            'min_ns': min(timings),
            'max_ns': max(timings),
            'p95_ns': np.percentile(timings, 95) if HAS_NUMPY else 0,
            'p99_ns': np.percentile(timings, 99) if HAS_NUMPY else 0,
        }

    @staticmethod
    async def benchmark_task_creation(iterations: int = 10000) -> Dict[str, float]:
        """
        Benchmark task creation overhead.

        Measures the cost of creating and scheduling async tasks.
        """
        timings = []

        async def dummy_task():
            pass

        for _ in range(iterations):
            start = time.perf_counter_ns()
            task = asyncio.create_task(dummy_task())
            await task
            end = time.perf_counter_ns()
            timings.append(end - start)

        return {
            'iterations': iterations,
            'mean_ns': statistics.mean(timings),
            'median_ns': statistics.median(timings),
            'std_ns': statistics.stdev(timings) if len(timings) > 1 else 0,
            'min_ns': min(timings),
            'max_ns': max(timings),
        }

    @staticmethod
    async def benchmark_concurrent_tasks(num_tasks: int = 100, task_duration_ms: float = 10) -> Dict[str, Any]:
        """
        Benchmark concurrent task execution.

        Measures event loop efficiency with multiple concurrent tasks.
        """
        start_time = time.perf_counter()

        async def worker():
            await asyncio.sleep(task_duration_ms / 1000)

        # Create and run tasks concurrently
        tasks = [asyncio.create_task(worker()) for _ in range(num_tasks)]
        await asyncio.gather(*tasks)

        elapsed = time.perf_counter() - start_time

        # Ideal time is task_duration_ms (if fully concurrent)
        ideal_time = task_duration_ms / 1000
        overhead = elapsed - ideal_time

        return {
            'num_tasks': num_tasks,
            'task_duration_ms': task_duration_ms,
            'total_time': elapsed,
            'ideal_time': ideal_time,
            'overhead': overhead,
            'efficiency': ideal_time / elapsed if elapsed > 0 else 0,
            'tasks_per_second': num_tasks / elapsed if elapsed > 0 else 0
        }


class AsyncAnalyzer:
    """Analyzes async profiling data."""

    def __init__(self):
        self.results: Optional[AsyncProfileResult] = None

    def analyze(self, task_stats: Dict[int, TaskStats], events: List[AsyncEvent], duration: float) -> AsyncProfileResult:
        """
        Analyze async execution data.

        Args:
            task_stats: Task statistics
            events: List of async events
            duration: Total profiling duration

        Returns:
            Complete profiling result
        """
        # Calculate aggregate statistics
        total_tasks = len(task_stats)
        completed_tasks = sum(1 for s in task_stats.values() if s.state == TaskState.COMPLETED)
        failed_tasks = sum(1 for s in task_stats.values() if s.state == TaskState.FAILED)
        cancelled_tasks = sum(1 for s in task_stats.values() if s.state == TaskState.CANCELLED)

        total_await_time_ns = sum(s.await_time_ns for s in task_stats.values())
        total_execution_time_ns = sum(s.execution_time_ns for s in task_stats.values())

        blocking_operations = sum(1 for e in events if e.blocking)

        # Calculate average task time
        completion_times = [s.completion_time_ns() for s in task_stats.values() if s.end_time]
        average_task_time_ns = statistics.mean(completion_times) if completion_times else 0

        # Estimate loop overhead
        total_accounted_time_ns = total_await_time_ns + total_execution_time_ns
        loop_overhead_ns = int(duration * 1e9) - total_accounted_time_ns

        event_loop_stats = EventLoopStats(
            duration_seconds=duration,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            cancelled_tasks=cancelled_tasks,
            total_await_time_ns=total_await_time_ns,
            total_execution_time_ns=total_execution_time_ns,
            blocking_operations=blocking_operations,
            average_task_time_ns=average_task_time_ns,
            loop_overhead_ns=loop_overhead_ns
        )

        # Identify slow coroutines (top 10)
        slow_coroutines = sorted(
            [(s.function, s.completion_time_ns()) for s in task_stats.values() if s.end_time],
            key=lambda x: x[1],
            reverse=True
        )[:10]

        self.results = AsyncProfileResult(
            duration_seconds=duration,
            task_stats=task_stats,
            event_loop_stats=event_loop_stats,
            events=events,
            slow_coroutines=slow_coroutines
        )

        return self.results

    def generate_summary(self) -> str:
        """Generate text summary."""
        if not self.results:
            return "No results to summarize"

        lines = ["=== Async Profiling Summary ===\n"]

        r = self.results
        el = r.event_loop_stats

        lines.append(f"Duration: {r.duration_seconds:.2f} seconds")
        lines.append(f"Total Tasks: {el.total_tasks}")
        lines.append(f"Completed: {el.completed_tasks}")
        lines.append(f"Failed: {el.failed_tasks}")
        lines.append(f"Event Loop Efficiency: {el.efficiency() * 100:.1f}%")
        lines.append(f"Average Task Time: {el.average_task_time_ns / 1e6:.3f} ms")
        lines.append(f"Blocking Operations: {el.blocking_operations}")

        if r.slow_coroutines:
            lines.append("\n=== Slowest Coroutines ===\n")
            for func, duration_ns in r.slow_coroutines[:5]:
                lines.append(f"  {func}: {duration_ns / 1e6:.3f} ms")

        return "\n".join(lines)


def profile_async_function(func: Callable) -> Callable:
    """
    Decorator to profile async functions.

    Usage:
        @profile_async_function
        async def my_function():
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tracer = AsyncTracer()
        task_id = tracer.trace_task_start(func.__name__)

        try:
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed_ns = int((time.perf_counter() - start) * 1e9)

            tracer.trace_task_end(task_id, success=True)
            logger.info(f"{func.__name__} completed in {elapsed_ns / 1e6:.3f} ms")

            return result

        except Exception as e:
            tracer.trace_task_end(task_id, success=False, error=str(e))
            raise

    return wrapper


class ReportGenerator:
    """Generates profiling reports."""

    @staticmethod
    def generate_text(result: AsyncProfileResult) -> str:
        """Generate text report."""
        analyzer = AsyncAnalyzer()
        analyzer.results = result
        return analyzer.generate_summary()

    @staticmethod
    def generate_json(result: AsyncProfileResult) -> str:
        """Generate JSON report."""
        return json.dumps(result.to_dict(), indent=2)

    @staticmethod
    def generate_html(result: AsyncProfileResult) -> str:
        """Generate HTML report."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Async Profiling Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .metric { font-size: 1.2em; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Async Profiling Report</h1>
"""

        el = result.event_loop_stats

        html += f"<div class='metric'>Duration: <strong>{result.duration_seconds:.2f}s</strong></div>"
        html += f"<div class='metric'>Event Loop Efficiency: <strong>{el.efficiency() * 100:.1f}%</strong></div>"
        html += f"<div class='metric'>Total Tasks: <strong>{el.total_tasks}</strong></div>"
        html += f"<div class='metric'>Completed: <strong>{el.completed_tasks}</strong></div>"

        html += "<h2>Slowest Coroutines</h2>"
        html += "<table>"
        html += "<tr><th>Function</th><th>Duration (ms)</th></tr>"

        for func, duration_ns in result.slow_coroutines:
            html += f"<tr><td>{func}</td><td>{duration_ns / 1e6:.3f}</td></tr>"

        html += "</table>"
        html += "</body></html>"

        return html


class AsyncProfiler:
    """Main async profiler."""

    def __init__(self):
        self.tracer = AsyncTracer()
        self.analyzer = AsyncAnalyzer()
        self.benchmark = AsyncBenchmark()

    async def profile_async(self, coro: Coroutine) -> AsyncProfileResult:
        """
        Profile a coroutine.

        Args:
            coro: Coroutine to profile

        Returns:
            Profiling result
        """
        self.tracer.start()
        start = time.perf_counter()

        try:
            await coro
        finally:
            elapsed = time.perf_counter() - start
            self.tracer.stop()

        task_stats = self.tracer.get_stats()
        events = self.tracer.get_events()

        result = self.analyzer.analyze(task_stats, events, elapsed)
        return result

    async def benchmark_overhead(self, iterations: int = 10000) -> Dict[str, float]:
        """Benchmark async overhead."""
        logger.info(f"Benchmarking async overhead ({iterations} iterations)...")
        return await self.benchmark.benchmark_async_overhead(iterations)

    async def benchmark_concurrency(self, num_tasks: int = 100) -> Dict[str, Any]:
        """Benchmark concurrent execution."""
        logger.info(f"Benchmarking concurrency ({num_tasks} tasks)...")
        return await self.benchmark.benchmark_concurrent_tasks(num_tasks)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='PyO3 Async Profiler',
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
    profile_parser = subparsers.add_parser('profile', help='Profile async application')
    profile_parser.add_argument('--script', type=Path, help='Script to profile')
    profile_parser.add_argument('--duration', type=float, default=10.0, help='Profiling duration')
    profile_parser.add_argument('--output', '-o', type=Path, help='Output file')

    # Event loop command
    event_parser = subparsers.add_parser('event-loop', help='Monitor event loop')
    event_parser.add_argument('--monitor', action='store_true', help='Continuous monitoring')
    event_parser.add_argument('--duration', type=float, default=10.0, help='Monitor duration')
    event_parser.add_argument('--interval', type=float, default=1.0, help='Sample interval')

    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Benchmark async overhead')
    benchmark_parser.add_argument('--iterations', type=int, default=10000, help='Number of iterations')
    benchmark_parser.add_argument('--concurrency', type=int, help='Number of concurrent tasks')

    # Function command
    function_parser = subparsers.add_parser('function', help='Profile specific function')
    function_parser.add_argument('function', help='Function to profile (module.function)')
    function_parser.add_argument('--iterations', type=int, default=1000, help='Number of calls')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.add_argument('--format', choices=['text', 'json', 'html'], default='text')
    report_parser.add_argument('--output', '-o', type=Path, help='Output file')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    profiler = AsyncProfiler()
    report_gen = ReportGenerator()

    async def run_command():
        try:
            if args.command == 'profile':
                print("Async profiling not yet fully implemented")
                return

            elif args.command == 'event-loop':
                print("Event loop monitoring not yet implemented")
                return

            elif args.command == 'benchmark':
                if args.concurrency:
                    result = await profiler.benchmark_concurrency(args.concurrency)
                else:
                    result = await profiler.benchmark_overhead(args.iterations)

                if args.json:
                    print(json.dumps(result, indent=2))
                else:
                    print("\nAsync Benchmark Results:")
                    for key, value in result.items():
                        if isinstance(value, float):
                            print(f"  {key}: {value:.2f}")
                        else:
                            print(f"  {key}: {value}")

            elif args.command == 'function':
                print("Function profiling not yet implemented")
                return

            elif args.command == 'report':
                print("Report generation not yet implemented")
                return

            else:
                parser.print_help()

        except KeyboardInterrupt:
            print("\nInterrupted by user")
            sys.exit(130)
        except Exception as e:
            logger.error(f"Error: {e}")
            if args.verbose:
                logger.debug(traceback.format_exc())
            sys.exit(1)

    # Run async command
    if args.command:
        asyncio.run(run_command())
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
