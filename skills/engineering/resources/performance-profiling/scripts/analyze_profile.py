#!/usr/bin/env python3
"""
Profile data analyzer with hotspot identification and optimization recommendations.

Analyzes CPU, memory, and I/O profiles to identify bottlenecks and suggest optimizations.
Supports multiple profile formats and generates actionable reports.
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class FunctionStats:
    """Statistics for a function in profile."""
    name: str
    self_time: float
    total_time: float
    call_count: int
    self_percent: float
    total_percent: float
    source_file: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class Hotspot:
    """Identified hotspot with optimization suggestions."""
    function: FunctionStats
    severity: str  # "critical", "high", "medium", "low"
    category: str  # "cpu", "memory", "io", "lock"
    recommendations: List[str]


@dataclass
class ProfileAnalysis:
    """Complete profile analysis result."""
    profile_file: str
    profile_type: str
    total_samples: int
    hotspots: List[Hotspot]
    summary: Dict[str, Any]
    top_functions: List[FunctionStats]
    recommendations: List[str]


class AnalysisError(Exception):
    """Base exception for analysis errors."""
    pass


class ProfileAnalyzer:
    """Profile data analyzer."""

    def __init__(self, verbose: bool = False) -> None:
        """
        Initialize analyzer.

        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose

        # Thresholds for hotspot identification
        self.critical_threshold = 0.20  # 20% of time
        self.high_threshold = 0.10      # 10% of time
        self.medium_threshold = 0.05    # 5% of time

    def _log(self, message: str) -> None:
        """Log message if verbose enabled."""
        if self.verbose:
            print(f"[ANALYZE] {message}", file=sys.stderr)

    def analyze_perf_script(self, profile_file: Path) -> ProfileAnalysis:
        """
        Analyze Linux perf script output.

        Args:
            profile_file: Path to perf.data file

        Returns:
            ProfileAnalysis with identified hotspots
        """
        self._log(f"Analyzing perf profile: {profile_file}")

        try:
            # Run perf report to get function statistics
            result = subprocess.run(
                ["perf", "report", "-i", str(profile_file), "--stdio", "--percent-limit", "1"],
                capture_output=True,
                text=True,
                check=True
            )
            report = result.stdout
        except subprocess.CalledProcessError as e:
            raise AnalysisError(f"Failed to run perf report: {e.stderr}") from e
        except FileNotFoundError:
            raise AnalysisError("perf not found. Is it installed?")

        # Parse perf report
        functions = self._parse_perf_report(report)

        # Identify hotspots
        hotspots = self._identify_hotspots(functions, "cpu")

        # Generate recommendations
        recommendations = self._generate_recommendations(hotspots)

        # Summary statistics
        total_samples = sum(f.call_count for f in functions)
        summary = {
            "total_functions": len(functions),
            "total_samples": total_samples,
            "hotspot_count": len(hotspots),
            "critical_hotspots": len([h for h in hotspots if h.severity == "critical"]),
            "high_hotspots": len([h for h in hotspots if h.severity == "high"]),
        }

        return ProfileAnalysis(
            profile_file=str(profile_file),
            profile_type="perf",
            total_samples=total_samples,
            hotspots=hotspots,
            summary=summary,
            top_functions=functions[:20],
            recommendations=recommendations,
        )

    def _parse_perf_report(self, report: str) -> List[FunctionStats]:
        """Parse perf report output into function statistics."""
        functions: List[FunctionStats] = []

        # Find overhead table
        in_table = False
        for line in report.split("\n"):
            line = line.strip()

            if line.startswith("# Overhead"):
                in_table = True
                continue

            if not in_table or not line:
                continue

            if line.startswith("#"):
                continue

            # Parse line: "  12.34%  0.56%  [kernel]  [k] function_name"
            # or: "  12.34%  function_name"
            match = re.match(r'^\s*(\d+\.\d+)%\s+(\d+\.\d+)%.*?\s+(\S+)\s*$', line)
            if not match:
                # Try simpler format
                match = re.match(r'^\s*(\d+\.\d+)%\s+(.+)$', line)
                if match:
                    overhead = float(match.group(1))
                    func_name = match.group(2).strip()

                    functions.append(FunctionStats(
                        name=func_name,
                        self_time=overhead,
                        total_time=overhead,
                        call_count=int(overhead * 100),  # Approximate
                        self_percent=overhead,
                        total_percent=overhead,
                    ))
                continue

            overhead = float(match.group(1))
            self_overhead = float(match.group(2))
            func_name = match.group(3)

            functions.append(FunctionStats(
                name=func_name,
                self_time=self_overhead,
                total_time=overhead,
                call_count=int(overhead * 100),  # Approximate
                self_percent=self_overhead,
                total_percent=overhead,
            ))

        # Sort by total time
        functions.sort(key=lambda f: f.total_time, reverse=True)

        return functions

    def analyze_pprof(self, profile_file: Path) -> ProfileAnalysis:
        """
        Analyze Go pprof profile.

        Args:
            profile_file: Path to .prof file

        Returns:
            ProfileAnalysis with identified hotspots
        """
        self._log(f"Analyzing pprof profile: {profile_file}")

        try:
            # Run go tool pprof to get top functions
            result = subprocess.run(
                ["go", "tool", "pprof", "-top", "-nodecount=50", str(profile_file)],
                capture_output=True,
                text=True,
                check=True
            )
            top_output = result.stdout
        except subprocess.CalledProcessError as e:
            raise AnalysisError(f"Failed to run pprof: {e.stderr}") from e
        except FileNotFoundError:
            raise AnalysisError("go not found. Is it installed?")

        # Parse pprof output
        functions = self._parse_pprof_top(top_output)

        # Identify hotspots
        hotspots = self._identify_hotspots(functions, "cpu")

        # Generate recommendations
        recommendations = self._generate_recommendations(hotspots)

        # Summary
        total_samples = sum(f.call_count for f in functions)
        summary = {
            "total_functions": len(functions),
            "total_samples": total_samples,
            "hotspot_count": len(hotspots),
        }

        return ProfileAnalysis(
            profile_file=str(profile_file),
            profile_type="pprof",
            total_samples=total_samples,
            hotspots=hotspots,
            summary=summary,
            top_functions=functions[:20],
            recommendations=recommendations,
        )

    def _parse_pprof_top(self, output: str) -> List[FunctionStats]:
        """Parse pprof -top output."""
        functions: List[FunctionStats] = []

        for line in output.split("\n"):
            line = line.strip()

            # Example: "  10.23s  12.34% 45.67%  runtime.mallocgc"
            match = re.match(
                r'^\s*(\d+(?:\.\d+)?[smµ]?s?)\s+(\d+\.\d+)%\s+(\d+\.\d+)%\s+(.+)$',
                line
            )
            if not match:
                continue

            time_str = match.group(1)
            flat_pct = float(match.group(2))
            cum_pct = float(match.group(3))
            func_name = match.group(4)

            # Convert time to seconds
            time_val = self._parse_time(time_str)

            functions.append(FunctionStats(
                name=func_name,
                self_time=time_val,
                total_time=time_val,
                call_count=int(flat_pct * 100),  # Approximate
                self_percent=flat_pct,
                total_percent=cum_pct,
            ))

        return functions

    def _parse_time(self, time_str: str) -> float:
        """Parse time string to seconds."""
        # Handle formats: "10.23s", "123ms", "456µs", "789ns"
        time_str = time_str.strip().lower()

        if time_str.endswith("s") and not time_str.endswith("ms") and not time_str.endswith("µs") and not time_str.endswith("ns"):
            return float(time_str[:-1])
        elif time_str.endswith("ms"):
            return float(time_str[:-2]) / 1000
        elif time_str.endswith("µs") or time_str.endswith("us"):
            return float(time_str[:-2]) / 1_000_000
        elif time_str.endswith("ns"):
            return float(time_str[:-2]) / 1_000_000_000
        else:
            return float(time_str)

    def analyze_py_spy(self, profile_file: Path) -> ProfileAnalysis:
        """
        Analyze py-spy speedscope JSON format.

        Args:
            profile_file: Path to .speedscope JSON file

        Returns:
            ProfileAnalysis with identified hotspots
        """
        self._log(f"Analyzing py-spy profile: {profile_file}")

        try:
            with open(profile_file, "r") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise AnalysisError(f"Failed to read profile: {e}") from e

        # Parse speedscope format
        functions = self._parse_speedscope(data)

        # Identify hotspots
        hotspots = self._identify_hotspots(functions, "cpu")

        # Generate recommendations
        recommendations = self._generate_recommendations(hotspots)

        # Summary
        total_samples = sum(f.call_count for f in functions)
        summary = {
            "total_functions": len(functions),
            "total_samples": total_samples,
            "hotspot_count": len(hotspots),
        }

        return ProfileAnalysis(
            profile_file=str(profile_file),
            profile_type="py-spy",
            total_samples=total_samples,
            hotspots=hotspots,
            summary=summary,
            top_functions=functions[:20],
            recommendations=recommendations,
        )

    def _parse_speedscope(self, data: Dict[str, Any]) -> List[FunctionStats]:
        """Parse speedscope JSON format."""
        # Speedscope format is complex, simplified parsing here
        functions: Dict[str, FunctionStats] = {}

        # Extract profiles
        profiles = data.get("profiles", [])
        for profile in profiles:
            samples = profile.get("samples", [])
            weights = profile.get("weights", [1] * len(samples))

            # Count samples per function
            for sample, weight in zip(samples, weights):
                for frame_id in sample:
                    # Get frame name
                    frame = profile["frames"][frame_id]
                    func_name = frame.get("name", "unknown")

                    if func_name not in functions:
                        functions[func_name] = FunctionStats(
                            name=func_name,
                            self_time=0,
                            total_time=0,
                            call_count=0,
                            self_percent=0,
                            total_percent=0,
                            source_file=frame.get("file"),
                            line_number=frame.get("line"),
                        )

                    functions[func_name].call_count += weight
                    functions[func_name].total_time += weight

        # Convert to list and calculate percentages
        total_samples = sum(f.call_count for f in functions.values())
        func_list = list(functions.values())

        for func in func_list:
            func.self_percent = (func.call_count / total_samples * 100) if total_samples > 0 else 0
            func.total_percent = func.self_percent

        # Sort by call count
        func_list.sort(key=lambda f: f.call_count, reverse=True)

        return func_list

    def _identify_hotspots(
        self,
        functions: List[FunctionStats],
        category: str
    ) -> List[Hotspot]:
        """
        Identify hotspots from function statistics.

        Args:
            functions: List of function statistics
            category: Hotspot category (cpu, memory, io, lock)

        Returns:
            List of identified hotspots
        """
        hotspots: List[Hotspot] = []

        for func in functions:
            # Determine severity based on time percentage
            severity = None
            if func.total_percent >= self.critical_threshold * 100:
                severity = "critical"
            elif func.total_percent >= self.high_threshold * 100:
                severity = "high"
            elif func.total_percent >= self.medium_threshold * 100:
                severity = "medium"
            else:
                continue  # Not a hotspot

            # Generate recommendations
            recommendations = self._recommend_for_function(func, category)

            hotspots.append(Hotspot(
                function=func,
                severity=severity,
                category=category,
                recommendations=recommendations,
            ))

        return hotspots

    def _recommend_for_function(
        self,
        func: FunctionStats,
        category: str
    ) -> List[str]:
        """Generate optimization recommendations for a function."""
        recommendations: List[str] = []

        func_name = func.name.lower()

        # Generic recommendations based on function name patterns
        if "sort" in func_name or "sorted" in func_name:
            recommendations.append(
                "Consider using more efficient sorting algorithm (e.g., timsort, radix sort)"
            )
            recommendations.append(
                "If sorting repeatedly, consider maintaining sorted structure (heap, BST)"
            )

        if "parse" in func_name or "json" in func_name or "xml" in func_name:
            recommendations.append(
                "Consider streaming parser for large inputs to reduce memory"
            )
            recommendations.append(
                "Cache parsing results if input doesn't change frequently"
            )

        if "regex" in func_name or "match" in func_name:
            recommendations.append(
                "Compile regex patterns outside loops (e.g., re.compile())"
            )
            recommendations.append(
                "Consider simpler string operations (str.startswith, str.find) if regex not needed"
            )

        if "copy" in func_name or "clone" in func_name:
            recommendations.append(
                "Avoid unnecessary copies; use references or views when possible"
            )
            recommendations.append(
                "Consider shallow copy if deep copy not required"
            )

        if "alloc" in func_name or "malloc" in func_name or "new" in func_name:
            recommendations.append(
                "Reduce allocations by reusing objects (object pooling)"
            )
            recommendations.append(
                "Preallocate collections with known size"
            )

        if "gc" in func_name or "garbage" in func_name:
            recommendations.append(
                "Reduce allocations to decrease GC pressure"
            )
            recommendations.append(
                "Consider manual memory management or arena allocation"
            )

        if "lock" in func_name or "mutex" in func_name or "sync" in func_name:
            recommendations.append(
                "Reduce lock contention by decreasing critical section size"
            )
            recommendations.append(
                "Consider lock-free data structures or finer-grained locking"
            )

        if "read" in func_name or "write" in func_name or "io" in func_name:
            recommendations.append(
                "Batch I/O operations to reduce syscalls"
            )
            recommendations.append(
                "Use buffered I/O or async I/O to overlap computation"
            )

        if "sql" in func_name or "query" in func_name or "database" in func_name:
            recommendations.append(
                "Batch queries to reduce round-trips (avoid N+1 problem)"
            )
            recommendations.append(
                "Add indexes on frequently queried columns"
            )
            recommendations.append(
                "Consider query result caching for read-heavy workloads"
            )

        if "hash" in func_name or "checksum" in func_name:
            recommendations.append(
                "Use faster hash function if cryptographic security not required"
            )
            recommendations.append(
                "Consider caching hash values if computed repeatedly"
            )

        # Category-specific recommendations
        if category == "cpu":
            recommendations.append(
                f"Function accounts for {func.total_percent:.1f}% of CPU time - high optimization priority"
            )

            if func.total_percent > 20:
                recommendations.append(
                    "Consider algorithmic optimization (better time complexity)"
                )
                recommendations.append(
                    "Profile at instruction level to identify specific bottleneck"
                )

        elif category == "memory":
            recommendations.append(
                "Analyze memory allocation patterns with heap profiler"
            )
            recommendations.append(
                "Consider memory pooling or arena allocation"
            )

        # If no specific recommendations, add generic ones
        if not recommendations:
            recommendations.append(
                f"High time consumption ({func.total_percent:.1f}%) - investigate algorithm and data structures"
            )
            recommendations.append(
                "Profile at finer granularity to identify specific bottleneck"
            )

        return recommendations

    def _generate_recommendations(self, hotspots: List[Hotspot]) -> List[str]:
        """Generate overall optimization recommendations."""
        recommendations: List[str] = []

        if not hotspots:
            recommendations.append("No significant hotspots detected (all functions <5% of time)")
            recommendations.append("Consider profiling under heavier load or longer duration")
            return recommendations

        # Count by severity
        critical = [h for h in hotspots if h.severity == "critical"]
        high = [h for h in hotspots if h.severity == "high"]

        if critical:
            recommendations.append(
                f"CRITICAL: {len(critical)} function(s) consuming >20% of time - highest priority"
            )
            for hotspot in critical[:3]:
                recommendations.append(
                    f"  - Optimize {hotspot.function.name} ({hotspot.function.total_percent:.1f}%)"
                )

        if high:
            recommendations.append(
                f"HIGH: {len(high)} function(s) consuming 10-20% of time - high priority"
            )

        # Check for common patterns
        hotspot_names = [h.function.name.lower() for h in hotspots]

        if any("alloc" in name or "malloc" in name for name in hotspot_names):
            recommendations.append(
                "Memory allocations detected in hot path - consider object pooling"
            )

        if any("lock" in name or "mutex" in name for name in hotspot_names):
            recommendations.append(
                "Lock contention detected - consider finer-grained locking or lock-free structures"
            )

        if any("gc" in name or "garbage" in name for name in hotspot_names):
            recommendations.append(
                "GC pressure detected - reduce allocations or tune GC parameters"
            )

        if any("parse" in name or "json" in name for name in hotspot_names):
            recommendations.append(
                "Parsing detected in hot path - consider caching or streaming"
            )

        # General recommendations
        recommendations.append(
            "Apply Amdahl's Law: Optimize the slowest 20% first (80/20 rule)"
        )
        recommendations.append(
            "Measure performance before and after each optimization to verify improvement"
        )

        return recommendations

    def analyze(self, profile_file: Path, profile_type: Optional[str] = None) -> ProfileAnalysis:
        """
        Analyze profile with auto-detection of format.

        Args:
            profile_file: Path to profile file
            profile_type: Profile type (perf, pprof, py-spy) or None for auto-detect

        Returns:
            ProfileAnalysis with identified hotspots

        Raises:
            AnalysisError: If analysis fails
        """
        if not profile_file.exists():
            raise AnalysisError(f"Profile file not found: {profile_file}")

        # Auto-detect profile type
        if profile_type is None:
            suffix = profile_file.suffix.lower()
            if suffix == ".data":
                profile_type = "perf"
            elif suffix == ".prof":
                profile_type = "pprof"
            elif suffix in [".json", ".speedscope"]:
                profile_type = "py-spy"
            else:
                raise AnalysisError(
                    f"Cannot auto-detect profile type from suffix: {suffix}"
                )

            self._log(f"Auto-detected profile type: {profile_type}")

        # Dispatch to type-specific analyzer
        if profile_type == "perf":
            return self.analyze_perf_script(profile_file)
        elif profile_type == "pprof":
            return self.analyze_pprof(profile_file)
        elif profile_type == "py-spy":
            return self.analyze_py_spy(profile_file)
        else:
            raise AnalysisError(f"Unsupported profile type: {profile_type}")


def print_analysis(analysis: ProfileAnalysis, detailed: bool = False) -> None:
    """Print analysis results in human-readable format."""
    print(f"\n{'='*80}")
    print(f"Profile Analysis: {Path(analysis.profile_file).name}")
    print(f"{'='*80}\n")

    # Summary
    print("Summary:")
    print(f"  Profile Type: {analysis.profile_type}")
    print(f"  Total Functions: {analysis.summary.get('total_functions', 0)}")
    print(f"  Total Samples: {analysis.summary.get('total_samples', 0)}")
    print(f"  Hotspots Found: {analysis.summary.get('hotspot_count', 0)}")

    if "critical_hotspots" in analysis.summary:
        print(f"    Critical: {analysis.summary['critical_hotspots']}")
        print(f"    High: {analysis.summary['high_hotspots']}")

    # Hotspots
    if analysis.hotspots:
        print(f"\n{'='*80}")
        print("Hotspots (Optimization Targets):")
        print(f"{'='*80}\n")

        for i, hotspot in enumerate(analysis.hotspots[:10], 1):
            func = hotspot.function
            print(f"{i}. [{hotspot.severity.upper()}] {func.name}")
            print(f"   Time: {func.total_percent:.2f}% (self: {func.self_percent:.2f}%)")

            if func.source_file:
                print(f"   Source: {func.source_file}:{func.line_number or '?'}")

            if detailed:
                print(f"   Recommendations:")
                for rec in hotspot.recommendations[:3]:
                    print(f"     - {rec}")

            print()

    # Top functions
    if not detailed:
        print(f"\n{'='*80}")
        print("Top 10 Functions by Time:")
        print(f"{'='*80}\n")

        for i, func in enumerate(analysis.top_functions[:10], 1):
            print(f"{i:2d}. {func.total_percent:6.2f}%  {func.name}")

    # Recommendations
    print(f"\n{'='*80}")
    print("Optimization Recommendations:")
    print(f"{'='*80}\n")

    for i, rec in enumerate(analysis.recommendations, 1):
        print(f"{i}. {rec}")

    print()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Profile data analyzer with optimization recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze perf profile
  %(prog)s profile.data

  # Analyze Go pprof
  %(prog)s cpu.prof --type pprof

  # Analyze py-spy JSON
  %(prog)s profile.speedscope --type py-spy

  # Detailed analysis with all recommendations
  %(prog)s profile.data --detailed

  # JSON output
  %(prog)s profile.data --json

Supported profile types: perf, pprof, py-spy
        """
    )

    parser.add_argument(
        "profile",
        type=Path,
        help="Profile file to analyze"
    )

    parser.add_argument(
        "-t", "--type",
        type=str,
        choices=["perf", "pprof", "py-spy"],
        help="Profile type (default: auto-detect from extension)"
    )

    parser.add_argument(
        "-d", "--detailed",
        action="store_true",
        help="Show detailed recommendations for each hotspot"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        analyzer = ProfileAnalyzer(verbose=args.verbose)

        analysis = analyzer.analyze(args.profile, args.type)

        if args.json:
            # Convert to JSON-serializable format
            output = {
                "profile_file": analysis.profile_file,
                "profile_type": analysis.profile_type,
                "total_samples": analysis.total_samples,
                "summary": analysis.summary,
                "hotspots": [
                    {
                        "function": asdict(h.function),
                        "severity": h.severity,
                        "category": h.category,
                        "recommendations": h.recommendations,
                    }
                    for h in analysis.hotspots
                ],
                "top_functions": [asdict(f) for f in analysis.top_functions],
                "recommendations": analysis.recommendations,
            }
            print(json.dumps(output, indent=2))
        else:
            print_analysis(analysis, detailed=args.detailed)

        return 0

    except AnalysisError as e:
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
