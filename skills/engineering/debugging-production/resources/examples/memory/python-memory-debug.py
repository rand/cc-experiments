#!/usr/bin/env python3
"""
Live Python memory debugging with py-spy and tracemalloc.

Demonstrates:
- Production-safe memory profiling
- Heap snapshot comparison
- Memory leak detection
- tracemalloc for allocation tracking
"""

import tracemalloc
import time
import subprocess
import os
from typing import List, Tuple


class MemoryLeaker:
    """Example class that leaks memory."""

    def __init__(self):
        self.cache = {}
        self.events = []

    def process_request(self, request_id: int):
        """Process request that leaks memory."""
        # Leak 1: Unbounded cache
        self.cache[request_id] = f"data_{request_id}" * 1000

        # Leak 2: Event listeners never cleaned
        self.events.append({
            "id": request_id,
            "timestamp": time.time(),
            "data": "x" * 10000
        })

        # Normal processing
        result = self._do_work(request_id)
        return result

    def _do_work(self, request_id: int) -> str:
        """Simulate work."""
        return f"Processed {request_id}"


def demonstrate_tracemalloc():
    """Demonstrate tracemalloc for memory debugging."""

    print("=== Tracemalloc Demonstration ===\n")

    # Start tracking
    tracemalloc.start()

    # Take baseline snapshot
    snapshot1 = tracemalloc.take_snapshot()
    print("Baseline snapshot taken")

    # Create memory leak
    leaker = MemoryLeaker()
    for i in range(1000):
        leaker.process_request(i)

    # Take second snapshot
    snapshot2 = tracemalloc.take_snapshot()
    print("Second snapshot taken after processing 1000 requests\n")

    # Compare snapshots
    print("Top 10 memory increases:")
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')

    for stat in top_stats[:10]:
        print(f"{stat.size_diff / 1024:.1f} KiB: {stat}")
        for line in stat.traceback.format()[:3]:
            print(f"  {line}")
        print()

    # Get current stats
    current = tracemalloc.get_traced_memory()
    peak = tracemalloc.get_traced_memory()[1]
    print(f"Current memory: {current[0] / 1024 / 1024:.1f} MB")
    print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")

    tracemalloc.stop()


def profile_with_pyspy(pid: int, duration: int = 10):
    """Profile running process with py-spy."""

    print(f"\n=== Profiling process {pid} with py-spy ===\n")

    # Check if py-spy is installed
    try:
        subprocess.run(["py-spy", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("py-spy not installed. Install with: pip install py-spy")
        return

    output_file = f"memory_profile_{pid}.svg"

    # Profile the process
    print(f"Profiling for {duration} seconds...")
    result = subprocess.run([
        "py-spy",
        "record",
        "--pid", str(pid),
        "--duration", str(duration),
        "--output", output_file,
        "--rate", "100",  # 100 Hz sampling
    ])

    if result.returncode == 0:
        print(f"Profile saved to: {output_file}")
    else:
        print("Profiling failed")


def demonstrate_leak_detection():
    """Demonstrate leak detection pattern."""

    print("\n=== Memory Leak Detection ===\n")

    tracemalloc.start()

    leaker = MemoryLeaker()

    # Measure memory growth over time
    measurements: List[Tuple[int, int]] = []

    for iteration in range(10):
        # Process batch
        for i in range(100):
            leaker.process_request(iteration * 100 + i)

        # Measure memory
        current, peak = tracemalloc.get_traced_memory()
        measurements.append((iteration, current))

        print(f"Iteration {iteration}: {current / 1024 / 1024:.1f} MB")

        time.sleep(0.1)

    # Analyze growth
    if len(measurements) >= 2:
        first_memory = measurements[0][1]
        last_memory = measurements[-1][1]
        growth = last_memory - first_memory

        print(f"\nMemory growth: {growth / 1024 / 1024:.1f} MB")

        # Calculate growth rate
        growth_per_iteration = growth / len(measurements)
        print(f"Growth per iteration: {growth_per_iteration / 1024:.1f} KB")

        if growth_per_iteration > 1024 * 100:  # 100 KB per iteration
            print("\nWARNING: Potential memory leak detected!")
            print("Recommendations:")
            print("- Check for unbounded caches")
            print("- Look for unclosed resources")
            print("- Review event listener management")

    tracemalloc.stop()


if __name__ == "__main__":
    # Demonstrate tracemalloc
    demonstrate_tracemalloc()

    # Demonstrate leak detection
    demonstrate_leak_detection()

    # Note: For py-spy profiling, run this script and profile it:
    # python python-memory-debug.py &
    # PID=$!
    # py-spy record --pid $PID --duration 10 --output profile.svg
