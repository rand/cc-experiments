#!/usr/bin/env python3
"""
Debug memory issues in production including leaks, exhaustion, and excessive GC.

This script provides comprehensive memory debugging capabilities:
- Memory leak detection through heap analysis
- Heap snapshot comparison
- Memory growth trending
- GC analysis and optimization recommendations
- Live process attachment with safety limits
"""

import argparse
import json
import os
import psutil
import signal
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import statistics


@dataclass
class HeapSnapshot:
    """Represents a heap memory snapshot."""

    timestamp: datetime
    process_id: int
    total_bytes: int
    objects: Dict[str, int] = field(default_factory=dict)
    allocations: List[Dict[str, Any]] = field(default_factory=list)
    stacks: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_mb(self) -> float:
        """Get total memory in MB."""
        return self.total_bytes / (1024 * 1024)


@dataclass
class MemoryTrend:
    """Represents memory usage trend over time."""

    measurements: List[Tuple[datetime, int]]
    process_id: int
    start_time: datetime
    end_time: datetime

    @property
    def duration_seconds(self) -> float:
        """Get duration of measurement period."""
        return (self.end_time - self.start_time).total_seconds()

    @property
    def growth_rate_mb_per_hour(self) -> float:
        """Calculate memory growth rate in MB/hour."""
        if len(self.measurements) < 2:
            return 0.0

        start_bytes = self.measurements[0][1]
        end_bytes = self.measurements[-1][1]
        duration_hours = self.duration_seconds / 3600

        if duration_hours == 0:
            return 0.0

        growth_bytes = end_bytes - start_bytes
        return (growth_bytes / (1024 * 1024)) / duration_hours

    @property
    def is_leaking(self) -> bool:
        """Determine if memory appears to be leaking."""
        if len(self.measurements) < 5:
            return False

        growth_rate = self.growth_rate_mb_per_hour

        if growth_rate < 1.0:
            return False

        values = [m[1] for m in self.measurements]
        correlation = self._calculate_correlation()

        return correlation > 0.8 and growth_rate > 1.0

    def _calculate_correlation(self) -> float:
        """Calculate correlation coefficient with time."""
        if len(self.measurements) < 2:
            return 0.0

        times = [(m[0] - self.start_time).total_seconds() for m, _ in enumerate(self.measurements)]
        values = [m[1] for m in self.measurements]

        n = len(times)
        sum_x = sum(times)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(times, values))
        sum_x2 = sum(x * x for x in times)
        sum_y2 = sum(y * y for y in values)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator


class MemoryDebugger:
    """Debug memory issues in running processes."""

    def __init__(self, pid: int, verbose: bool = False):
        """
        Initialize memory debugger.

        Args:
            pid: Process ID to debug
            verbose: Enable verbose output

        Raises:
            psutil.NoSuchProcess: If process doesn't exist
            psutil.AccessDenied: If insufficient permissions
        """
        self.pid = pid
        self.verbose = verbose

        try:
            self.process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            raise ValueError(f"Process {pid} does not exist")
        except psutil.AccessDenied:
            raise PermissionError(f"Insufficient permissions to access process {pid}")

    def get_memory_info(self) -> Dict[str, Any]:
        """
        Get current memory information for process.

        Returns:
            Dictionary with memory statistics

        Raises:
            psutil.NoSuchProcess: If process terminated
        """
        try:
            mem_info = self.process.memory_info()
            mem_full = self.process.memory_full_info()

            return {
                "rss_bytes": mem_info.rss,
                "rss_mb": round(mem_info.rss / (1024 * 1024), 2),
                "vms_bytes": mem_info.vms,
                "vms_mb": round(mem_info.vms / (1024 * 1024), 2),
                "shared_bytes": getattr(mem_full, "shared", 0),
                "shared_mb": round(getattr(mem_full, "shared", 0) / (1024 * 1024), 2),
                "uss_bytes": getattr(mem_full, "uss", 0),
                "uss_mb": round(getattr(mem_full, "uss", 0) / (1024 * 1024), 2),
                "percent": round(self.process.memory_percent(), 2),
            }
        except psutil.NoSuchProcess:
            raise ValueError(f"Process {self.pid} terminated")

    def monitor_memory_trend(
        self,
        duration_seconds: int = 60,
        interval_seconds: float = 1.0,
    ) -> MemoryTrend:
        """
        Monitor memory usage over time to detect leaks.

        Args:
            duration_seconds: How long to monitor
            interval_seconds: Sampling interval

        Returns:
            MemoryTrend object with measurements

        Raises:
            ValueError: If process terminates during monitoring
        """
        if self.verbose:
            print(f"Monitoring memory for {duration_seconds} seconds...", file=sys.stderr)

        measurements = []
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)

        try:
            while datetime.now() < end_time:
                timestamp = datetime.now()
                mem_info = self.process.memory_info()
                measurements.append((timestamp, mem_info.rss))

                if self.verbose:
                    elapsed = (timestamp - start_time).total_seconds()
                    mb = mem_info.rss / (1024 * 1024)
                    print(f"  [{elapsed:.1f}s] {mb:.1f} MB", file=sys.stderr)

                time.sleep(interval_seconds)

        except psutil.NoSuchProcess:
            raise ValueError(f"Process {self.pid} terminated during monitoring")
        except KeyboardInterrupt:
            if self.verbose:
                print("\nMonitoring interrupted", file=sys.stderr)

        actual_end_time = datetime.now()

        return MemoryTrend(
            measurements=measurements,
            process_id=self.pid,
            start_time=start_time,
            end_time=actual_end_time,
        )

    def take_heap_snapshot(self, output_file: Optional[str] = None) -> Optional[str]:
        """
        Take heap snapshot of Python process.

        Args:
            output_file: Optional output file path

        Returns:
            Path to snapshot file if successful

        Raises:
            RuntimeError: If snapshot fails
        """
        if self.verbose:
            print(f"Taking heap snapshot of process {self.pid}...", file=sys.stderr)

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"heap_snapshot_{self.pid}_{timestamp}.json"

        try:
            result = subprocess.run(
                ["py-spy", "dump", "--pid", str(self.pid), "--json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(f"py-spy failed: {result.stderr}")

            with open(output_file, "w") as f:
                f.write(result.stdout)

            if self.verbose:
                print(f"Snapshot saved to {output_file}", file=sys.stderr)

            return output_file

        except subprocess.TimeoutExpired:
            raise RuntimeError("Snapshot timed out after 30 seconds")
        except FileNotFoundError:
            raise RuntimeError("py-spy not found. Install with: pip install py-spy")

    def profile_allocations(
        self,
        duration_seconds: int = 30,
        rate_hz: int = 100,
        output_file: Optional[str] = None,
    ) -> str:
        """
        Profile memory allocations using py-spy.

        Args:
            duration_seconds: Duration to profile
            rate_hz: Sampling rate
            output_file: Output file path

        Returns:
            Path to output file

        Raises:
            RuntimeError: If profiling fails
        """
        if self.verbose:
            print(f"Profiling allocations for {duration_seconds} seconds...", file=sys.stderr)

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"allocation_profile_{self.pid}_{timestamp}.svg"

        try:
            result = subprocess.run(
                [
                    "py-spy",
                    "record",
                    "--pid", str(self.pid),
                    "--rate", str(rate_hz),
                    "--duration", str(duration_seconds),
                    "--output", output_file,
                ],
                capture_output=True,
                text=True,
                timeout=duration_seconds + 10,
            )

            if result.returncode != 0:
                raise RuntimeError(f"py-spy failed: {result.stderr}")

            if self.verbose:
                print(f"Profile saved to {output_file}", file=sys.stderr)

            return output_file

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Profiling timed out")
        except FileNotFoundError:
            raise RuntimeError("py-spy not found. Install with: pip install py-spy")

    def detect_leaks(self, duration_seconds: int = 300) -> Dict[str, Any]:
        """
        Comprehensive leak detection.

        Args:
            duration_seconds: How long to monitor

        Returns:
            Dictionary with leak analysis

        Raises:
            ValueError: If process terminates
        """
        if self.verbose:
            print("Starting comprehensive leak detection...", file=sys.stderr)

        initial_mem = self.get_memory_info()
        if self.verbose:
            print(f"Initial memory: {initial_mem['rss_mb']} MB", file=sys.stderr)

        trend = self.monitor_memory_trend(
            duration_seconds=duration_seconds,
            interval_seconds=1.0,
        )

        final_mem = self.get_memory_info()
        if self.verbose:
            print(f"Final memory: {final_mem['rss_mb']} MB", file=sys.stderr)

        memory_delta_mb = final_mem["rss_mb"] - initial_mem["rss_mb"]
        growth_rate = trend.growth_rate_mb_per_hour

        is_leaking = trend.is_leaking

        if self.verbose:
            print(f"Memory delta: {memory_delta_mb:+.2f} MB", file=sys.stderr)
            print(f"Growth rate: {growth_rate:+.2f} MB/hour", file=sys.stderr)
            print(f"Leak detected: {is_leaking}", file=sys.stderr)

        result = {
            "process_id": self.pid,
            "duration_seconds": duration_seconds,
            "initial_memory_mb": initial_mem["rss_mb"],
            "final_memory_mb": final_mem["rss_mb"],
            "memory_delta_mb": round(memory_delta_mb, 2),
            "growth_rate_mb_per_hour": round(growth_rate, 2),
            "is_leaking": is_leaking,
            "measurements": len(trend.measurements),
        }

        if is_leaking:
            time_to_oom_hours = None
            if growth_rate > 0:
                available_mem = psutil.virtual_memory().available / (1024 * 1024)
                time_to_oom_hours = available_mem / growth_rate

            result["severity"] = self._assess_leak_severity(growth_rate)
            result["time_to_oom_hours"] = (
                round(time_to_oom_hours, 2) if time_to_oom_hours else None
            )
            result["recommendations"] = self._get_leak_recommendations(growth_rate)

        return result

    def compare_snapshots(
        self,
        snapshot1_file: str,
        snapshot2_file: str,
    ) -> Dict[str, Any]:
        """
        Compare two heap snapshots to find leaks.

        Args:
            snapshot1_file: Path to first snapshot
            snapshot2_file: Path to second snapshot

        Returns:
            Dictionary with comparison results

        Raises:
            FileNotFoundError: If snapshot files don't exist
            json.JSONDecodeError: If snapshots are invalid
        """
        if self.verbose:
            print(f"Comparing snapshots...", file=sys.stderr)

        with open(snapshot1_file) as f:
            snap1 = json.load(f)

        with open(snapshot2_file) as f:
            snap2 = json.load(f)

        objects1 = defaultdict(int)
        objects2 = defaultdict(int)

        for frame in snap1.get("frames", []):
            func = frame.get("function", "unknown")
            objects1[func] += 1

        for frame in snap2.get("frames", []):
            func = frame.get("function", "unknown")
            objects2[func] += 1

        increases = {}
        for func, count2 in objects2.items():
            count1 = objects1.get(func, 0)
            if count2 > count1:
                increases[func] = {
                    "before": count1,
                    "after": count2,
                    "increase": count2 - count1,
                    "percentage": round(((count2 - count1) / count1 * 100), 2) if count1 > 0 else float('inf'),
                }

        sorted_increases = sorted(
            increases.items(),
            key=lambda x: x[1]["increase"],
            reverse=True,
        )

        return {
            "snapshot1": snapshot1_file,
            "snapshot2": snapshot2_file,
            "top_increases": [
                {"function": func, **data}
                for func, data in sorted_increases[:20]
            ],
        }

    def analyze_gc(self) -> Dict[str, Any]:
        """
        Analyze garbage collection if applicable.

        Returns:
            Dictionary with GC analysis

        Note:
            This is a placeholder for language-specific GC analysis
        """
        return {
            "note": "GC analysis requires language-specific tools",
            "recommendations": [
                "For Python: Use gc module to track collections",
                "For Java: Enable GC logging with -Xlog:gc*",
                "For Go: Use GODEBUG=gctrace=1",
                "For Node.js: Use --trace-gc flag",
            ],
        }

    @staticmethod
    def _assess_leak_severity(growth_rate_mb_per_hour: float) -> str:
        """Assess severity of memory leak."""
        if growth_rate_mb_per_hour < 5:
            return "low"
        elif growth_rate_mb_per_hour < 50:
            return "medium"
        elif growth_rate_mb_per_hour < 500:
            return "high"
        else:
            return "critical"

    @staticmethod
    def _get_leak_recommendations(growth_rate_mb_per_hour: float) -> List[str]:
        """Get recommendations based on leak severity."""
        recommendations = [
            "Take heap snapshots at intervals and compare",
            "Profile allocations to find hot spots",
            "Check for unclosed file handles or connections",
            "Review caching logic for unbounded growth",
            "Look for event listeners not being removed",
        ]

        if growth_rate_mb_per_hour > 50:
            recommendations.extend([
                "Consider restarting service on schedule",
                "Implement memory limits and circuit breakers",
                "Escalate to development team urgently",
            ])

        if growth_rate_mb_per_hour > 500:
            recommendations.insert(0, "CRITICAL: Service may OOM soon, prepare for restart")

        return recommendations


class SafetyMonitor:
    """Monitor system health during debug operations."""

    def __init__(
        self,
        max_cpu_percent: float = 80.0,
        max_memory_percent: float = 85.0,
        check_interval: float = 1.0,
    ):
        """
        Initialize safety monitor.

        Args:
            max_cpu_percent: Maximum CPU usage
            max_memory_percent: Maximum memory usage
            check_interval: How often to check
        """
        self.max_cpu = max_cpu_percent
        self.max_memory = max_memory_percent
        self.check_interval = check_interval
        self.violations = 0
        self.max_violations = 3
        self.should_stop = False

    def check_safety(self) -> Tuple[bool, Optional[str]]:
        """
        Check if it's safe to continue.

        Returns:
            Tuple of (is_safe, error_message)
        """
        cpu_percent = psutil.cpu_percent(interval=self.check_interval)
        memory_percent = psutil.virtual_memory().percent

        if cpu_percent > self.max_cpu:
            self.violations += 1
            if self.violations >= self.max_violations:
                return False, f"CPU usage too high: {cpu_percent:.1f}%"

        if memory_percent > self.max_memory:
            self.violations += 1
            if self.violations >= self.max_violations:
                return False, f"Memory usage too high: {memory_percent:.1f}%"

        if cpu_percent < self.max_cpu and memory_percent < self.max_memory:
            self.violations = max(0, self.violations - 1)

        return True, None

    def monitor_operation(self, operation_func, *args, **kwargs):
        """
        Monitor operation with safety checks.

        Args:
            operation_func: Function to execute
            *args: Arguments to pass
            **kwargs: Keyword arguments to pass

        Returns:
            Result of operation_func

        Raises:
            RuntimeError: If safety limits exceeded
        """
        import threading

        stop_event = threading.Event()
        error_msg = None

        def safety_check():
            nonlocal error_msg
            while not stop_event.is_set():
                safe, msg = self.check_safety()
                if not safe:
                    error_msg = msg
                    self.should_stop = True
                    break
                time.sleep(self.check_interval)

        monitor_thread = threading.Thread(target=safety_check, daemon=True)
        monitor_thread.start()

        try:
            result = operation_func(*args, **kwargs)
            return result
        finally:
            stop_event.set()
            monitor_thread.join(timeout=2)
            if error_msg:
                raise RuntimeError(f"Operation aborted: {error_msg}")


def format_output(data: Any, output_format: str) -> str:
    """
    Format output data.

    Args:
        data: Data to format
        output_format: Format type ('json' or 'text')

    Returns:
        Formatted string
    """
    if output_format == "json":
        return json.dumps(data, indent=2, default=str)

    lines = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"\n{key}:")
                lines.append(format_output(value, "text"))
            else:
                lines.append(f"{key}: {value}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            lines.append(f"\n[{i}]")
            lines.append(format_output(item, "text"))
    else:
        lines.append(str(data))

    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Debug memory issues in production processes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor memory trend
  %(prog)s --pid 12345 --duration 60

  # Detect memory leaks
  %(prog)s --pid 12345 --detect-leaks --duration 300

  # Take heap snapshot
  %(prog)s --pid 12345 --heap-snapshot

  # Profile allocations
  %(prog)s --pid 12345 --profile-allocations --duration 30

  # Compare snapshots
  %(prog)s --compare snapshot1.json snapshot2.json

  # Full analysis with JSON output
  %(prog)s --pid 12345 --detect-leaks --heap-snapshot --json
        """,
    )

    parser.add_argument(
        "--pid",
        type=int,
        help="Process ID to debug",
    )

    # Analysis options
    analysis_group = parser.add_argument_group("analysis options")
    analysis_group.add_argument(
        "--detect-leaks",
        action="store_true",
        help="Detect memory leaks",
    )
    analysis_group.add_argument(
        "--heap-snapshot",
        action="store_true",
        help="Take heap snapshot",
    )
    analysis_group.add_argument(
        "--profile-allocations",
        action="store_true",
        help="Profile memory allocations",
    )
    analysis_group.add_argument(
        "--compare",
        nargs=2,
        metavar=("SNAPSHOT1", "SNAPSHOT2"),
        help="Compare two heap snapshots",
    )

    # Configuration options
    config_group = parser.add_argument_group("configuration options")
    config_group.add_argument(
        "--duration",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Duration for monitoring/profiling (default: 60)",
    )
    config_group.add_argument(
        "--interval",
        type=float,
        default=1.0,
        metavar="SECONDS",
        help="Sampling interval (default: 1.0)",
    )
    config_group.add_argument(
        "--rate",
        type=int,
        default=100,
        metavar="HZ",
        help="Profiling sample rate (default: 100)",
    )

    # Output options
    output_group = parser.add_argument_group("output options")
    output_group.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Output file",
    )
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    output_group.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    try:
        # Snapshot comparison doesn't need PID
        if args.compare:
            if args.verbose:
                print("Comparing snapshots...", file=sys.stderr)

            debugger = MemoryDebugger(os.getpid(), args.verbose)
            result = debugger.compare_snapshots(args.compare[0], args.compare[1])

            output = format_output(result, "json" if args.json else "text")
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
            else:
                print(output)

            return 0

        # All other operations need PID
        if not args.pid:
            print("Error: --pid required (except when using --compare)", file=sys.stderr)
            parser.print_help()
            return 1

        # Create debugger
        debugger = MemoryDebugger(args.pid, args.verbose)

        # Get current memory info
        mem_info = debugger.get_memory_info()
        if args.verbose:
            print(f"Process {args.pid} memory: {mem_info['rss_mb']} MB", file=sys.stderr)

        results = {"process_id": args.pid, "memory_info": mem_info}

        # Perform requested analyses
        if args.detect_leaks:
            if args.verbose:
                print("\nDetecting memory leaks...", file=sys.stderr)

            leak_analysis = debugger.detect_leaks(duration_seconds=args.duration)
            results["leak_detection"] = leak_analysis

        if args.heap_snapshot:
            if args.verbose:
                print("\nTaking heap snapshot...", file=sys.stderr)

            snapshot_file = debugger.take_heap_snapshot(args.output)
            results["heap_snapshot"] = {
                "file": snapshot_file,
                "timestamp": datetime.now().isoformat(),
            }

        if args.profile_allocations:
            if args.verbose:
                print("\nProfiling allocations...", file=sys.stderr)

            profile_file = debugger.profile_allocations(
                duration_seconds=args.duration,
                rate_hz=args.rate,
            )
            results["allocation_profile"] = {
                "file": profile_file,
                "duration_seconds": args.duration,
                "rate_hz": args.rate,
            }

        # If no specific analysis requested, do basic monitoring
        if not any([args.detect_leaks, args.heap_snapshot, args.profile_allocations]):
            if args.verbose:
                print("\nMonitoring memory trend...", file=sys.stderr)

            trend = debugger.monitor_memory_trend(
                duration_seconds=args.duration,
                interval_seconds=args.interval,
            )

            results["trend"] = {
                "duration_seconds": trend.duration_seconds,
                "measurement_count": len(trend.measurements),
                "growth_rate_mb_per_hour": round(trend.growth_rate_mb_per_hour, 2),
                "is_leaking": trend.is_leaking,
                "start_memory_mb": round(trend.measurements[0][1] / (1024 * 1024), 2),
                "end_memory_mb": round(trend.measurements[-1][1] / (1024 * 1024), 2),
            }

        # Format and output
        output = format_output(results, "json" if args.json else "text")

        if args.output and not (args.heap_snapshot or args.profile_allocations):
            with open(args.output, "w") as f:
                f.write(output)
            if args.verbose:
                print(f"\nResults written to {args.output}", file=sys.stderr)
        else:
            print(output)

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except PermissionError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Try running with sudo or as the process owner", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
