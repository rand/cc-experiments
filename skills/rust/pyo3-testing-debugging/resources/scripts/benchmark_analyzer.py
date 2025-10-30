#!/usr/bin/env python3
"""
PyO3 Benchmark Analyzer - Analyze and compare PyO3 benchmark results.

This script parses benchmark output from both criterion (Rust) and
pytest-benchmark (Python), performs statistical analysis, detects performance
regressions, and generates comprehensive comparison reports with visualizations.

Usage:
    benchmark_analyzer.py analyze <file>     # Analyze benchmark results
    benchmark_analyzer.py compare <a> <b>    # Compare two benchmark runs
    benchmark_analyzer.py regression <file>  # Detect regressions vs baseline
    benchmark_analyzer.py report <file>      # Generate detailed report
    benchmark_analyzer.py visualize <file>   # Create visualizations

Examples:
    # Analyze criterion output
    benchmark_analyzer.py analyze criterion-results.json

    # Compare two benchmark runs
    benchmark_analyzer.py compare baseline.json current.json --format html

    # Detect regressions with 10% threshold
    benchmark_analyzer.py regression current.json --baseline baseline.json --threshold 10

    # Generate HTML report with charts
    benchmark_analyzer.py report results.json --format html --charts

    # Visualize specific benchmarks
    benchmark_analyzer.py visualize results.json --benchmarks "test_*" --output charts/
"""

import argparse
import dataclasses
import json
import math
import pathlib
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class BenchmarkTool(Enum):
    """Benchmark tool type."""
    CRITERION = "criterion"
    PYTEST_BENCHMARK = "pytest-benchmark"
    UNKNOWN = "unknown"


class OutputFormat(Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


class RegressionSeverity(Enum):
    """Performance regression severity."""
    CRITICAL = "critical"  # >50% slower
    HIGH = "high"          # 25-50% slower
    MEDIUM = "medium"      # 10-25% slower
    LOW = "low"            # 5-10% slower
    NONE = "none"          # <5% slower
    IMPROVEMENT = "improvement"  # Faster


@dataclasses.dataclass
class BenchmarkStats:
    """Statistical analysis of benchmark results."""
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    iterations: int
    p50: float  # 50th percentile
    p75: float  # 75th percentile
    p90: float  # 90th percentile
    p95: float  # 95th percentile
    p99: float  # 99th percentile

    @property
    def coefficient_of_variation(self) -> float:
        """Calculate coefficient of variation (CV)."""
        if self.mean == 0:
            return 0.0
        return (self.std_dev / self.mean) * 100.0

    @property
    def is_stable(self) -> bool:
        """Check if benchmark is stable (CV < 5%)."""
        return self.coefficient_of_variation < 5.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mean": self.mean,
            "median": self.median,
            "std_dev": self.std_dev,
            "min": self.min,
            "max": self.max,
            "iterations": self.iterations,
            "percentiles": {
                "p50": self.p50,
                "p75": self.p75,
                "p90": self.p90,
                "p95": self.p95,
                "p99": self.p99,
            },
            "coefficient_of_variation": self.coefficient_of_variation,
            "is_stable": self.is_stable,
        }


@dataclasses.dataclass
class BenchmarkResult:
    """Individual benchmark result."""
    name: str
    tool: BenchmarkTool
    stats: BenchmarkStats
    unit: str = "ns"  # ns, us, ms, s
    group: Optional[str] = None
    timestamp: str = dataclasses.field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "tool": self.tool.value,
            "stats": self.stats.to_dict(),
            "unit": self.unit,
            "group": self.group,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    def format_time(self, value: float) -> str:
        """Format time value with appropriate unit."""
        if self.unit == "s":
            if value < 1e-6:
                return f"{value * 1e9:.2f} ns"
            elif value < 1e-3:
                return f"{value * 1e6:.2f} µs"
            elif value < 1:
                return f"{value * 1e3:.2f} ms"
            else:
                return f"{value:.2f} s"
        elif self.unit == "ms":
            if value < 1:
                return f"{value * 1000:.2f} µs"
            elif value < 1000:
                return f"{value:.2f} ms"
            else:
                return f"{value / 1000:.2f} s"
        elif self.unit == "us" or self.unit == "µs":
            if value < 1:
                return f"{value * 1000:.2f} ns"
            elif value < 1000:
                return f"{value:.2f} µs"
            else:
                return f"{value / 1000:.2f} ms"
        else:  # ns
            if value < 1000:
                return f"{value:.2f} ns"
            elif value < 1e6:
                return f"{value / 1000:.2f} µs"
            elif value < 1e9:
                return f"{value / 1e6:.2f} ms"
            else:
                return f"{value / 1e9:.2f} s"


@dataclasses.dataclass
class BenchmarkReport:
    """Comprehensive benchmark report."""
    project_name: str
    tool: BenchmarkTool
    benchmarks: List[BenchmarkResult] = dataclasses.field(default_factory=list)
    timestamp: str = dataclasses.field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    @property
    def total_benchmarks(self) -> int:
        """Total benchmark count."""
        return len(self.benchmarks)

    @property
    def stable_benchmarks(self) -> int:
        """Count of stable benchmarks."""
        return sum(1 for b in self.benchmarks if b.stats.is_stable)

    @property
    def average_mean(self) -> float:
        """Average mean time across benchmarks."""
        if not self.benchmarks:
            return 0.0
        return statistics.mean(b.stats.mean for b in self.benchmarks)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_name": self.project_name,
            "tool": self.tool.value,
            "benchmarks": [b.to_dict() for b in self.benchmarks],
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "summary": {
                "total_benchmarks": self.total_benchmarks,
                "stable_benchmarks": self.stable_benchmarks,
                "average_mean": self.average_mean,
            },
        }


@dataclasses.dataclass
class BenchmarkComparison:
    """Comparison between two benchmark results."""
    name: str
    baseline: BenchmarkResult
    current: BenchmarkResult
    mean_delta: float  # Percentage change
    median_delta: float
    severity: RegressionSeverity

    @property
    def is_regression(self) -> bool:
        """Check if this is a regression."""
        return self.severity not in [RegressionSeverity.NONE, RegressionSeverity.IMPROVEMENT]

    @property
    def is_improvement(self) -> bool:
        """Check if this is an improvement."""
        return self.severity == RegressionSeverity.IMPROVEMENT

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "baseline": self.baseline.to_dict(),
            "current": self.current.to_dict(),
            "mean_delta": self.mean_delta,
            "median_delta": self.median_delta,
            "severity": self.severity.value,
            "is_regression": self.is_regression,
            "is_improvement": self.is_improvement,
        }


class CriterionParser:
    """Parse criterion benchmark output."""

    @staticmethod
    def parse(file_path: pathlib.Path) -> BenchmarkReport:
        """Parse criterion JSON output."""
        with open(file_path) as f:
            data = json.load(f)

        benchmarks: List[BenchmarkResult] = []

        # Criterion can have different output formats
        if isinstance(data, dict):
            benchmarks.extend(CriterionParser._parse_criterion_dict(data))
        elif isinstance(data, list):
            for item in data:
                benchmarks.extend(CriterionParser._parse_criterion_dict(item))

        return BenchmarkReport(
            project_name=file_path.stem,
            tool=BenchmarkTool.CRITERION,
            benchmarks=benchmarks,
        )

    @staticmethod
    def _parse_criterion_dict(data: Dict[str, Any]) -> List[BenchmarkResult]:
        """Parse criterion dictionary format."""
        benchmarks: List[BenchmarkResult] = []

        # Handle different criterion output structures
        if "benchmarks" in data:
            for bench_data in data["benchmarks"]:
                result = CriterionParser._parse_benchmark_entry(bench_data)
                if result:
                    benchmarks.append(result)
        elif "typical" in data or "mean" in data:
            result = CriterionParser._parse_benchmark_entry(data)
            if result:
                benchmarks.append(result)

        return benchmarks

    @staticmethod
    def _parse_benchmark_entry(data: Dict[str, Any]) -> Optional[BenchmarkResult]:
        """Parse a single benchmark entry."""
        try:
            name = data.get("name", data.get("id", "unknown"))
            group = data.get("group")

            # Extract statistics
            if "typical" in data:
                # Older criterion format
                mean = data["typical"]["estimate"]
                std_dev = data["typical"].get("std_dev", 0.0)
            elif "mean" in data:
                # Newer criterion format
                mean = data["mean"]["estimate"]
                std_dev = data["mean"].get("std_dev", 0.0)
            else:
                return None

            # Extract percentiles if available
            median = data.get("median", {}).get("estimate", mean)
            p75 = data.get("p75", {}).get("estimate", median)
            p90 = data.get("p90", {}).get("estimate", p75)
            p95 = data.get("p95", {}).get("estimate", p90)
            p99 = data.get("p99", {}).get("estimate", p95)

            # Extract min/max
            min_val = data.get("min", mean - std_dev)
            max_val = data.get("max", mean + std_dev)

            # Extract iterations
            iterations = data.get("iterations", data.get("sample_size", 100))

            stats = BenchmarkStats(
                mean=mean,
                median=median,
                std_dev=std_dev,
                min=min_val,
                max=max_val,
                iterations=iterations,
                p50=median,
                p75=p75,
                p90=p90,
                p95=p95,
                p99=p99,
            )

            # Criterion uses nanoseconds by default
            unit = "ns"

            return BenchmarkResult(
                name=name,
                tool=BenchmarkTool.CRITERION,
                stats=stats,
                unit=unit,
                group=group,
                metadata=data,
            )

        except (KeyError, TypeError):
            return None


class PytestBenchmarkParser:
    """Parse pytest-benchmark output."""

    @staticmethod
    def parse(file_path: pathlib.Path) -> BenchmarkReport:
        """Parse pytest-benchmark JSON output."""
        with open(file_path) as f:
            data = json.load(f)

        benchmarks: List[BenchmarkResult] = []

        # pytest-benchmark format
        for bench_data in data.get("benchmarks", []):
            result = PytestBenchmarkParser._parse_benchmark_entry(bench_data)
            if result:
                benchmarks.append(result)

        return BenchmarkReport(
            project_name=file_path.stem,
            tool=BenchmarkTool.PYTEST_BENCHMARK,
            benchmarks=benchmarks,
            metadata={
                "machine_info": data.get("machine_info", {}),
                "commit_info": data.get("commit_info", {}),
            },
        )

    @staticmethod
    def _parse_benchmark_entry(data: Dict[str, Any]) -> Optional[BenchmarkResult]:
        """Parse a single benchmark entry."""
        try:
            name = data.get("name", data.get("fullname", "unknown"))
            group = data.get("group")

            stats_data = data.get("stats", {})

            # Extract statistics (pytest-benchmark uses seconds)
            mean = stats_data.get("mean", 0.0)
            median = stats_data.get("median", mean)
            std_dev = stats_data.get("stddev", 0.0)
            min_val = stats_data.get("min", 0.0)
            max_val = stats_data.get("max", 0.0)
            iterations = stats_data.get("iterations", stats_data.get("rounds", 1))

            # Extract percentiles
            iqr = stats_data.get("iqr", std_dev)
            q1 = stats_data.get("q1", median - iqr / 2)
            q3 = stats_data.get("q3", median + iqr / 2)

            # Estimate percentiles if not provided
            p50 = median
            p75 = q3
            p90 = q3 + (q3 - q1)
            p95 = q3 + 1.5 * (q3 - q1)
            p99 = max_val

            stats = BenchmarkStats(
                mean=mean,
                median=median,
                std_dev=std_dev,
                min=min_val,
                max=max_val,
                iterations=iterations,
                p50=p50,
                p75=p75,
                p90=p90,
                p95=p95,
                p99=p99,
            )

            return BenchmarkResult(
                name=name,
                tool=BenchmarkTool.PYTEST_BENCHMARK,
                stats=stats,
                unit="s",  # pytest-benchmark uses seconds
                group=group,
                metadata=data,
            )

        except (KeyError, TypeError):
            return None


class BenchmarkAnalyzer:
    """Analyze benchmark results."""

    @staticmethod
    def detect_tool(file_path: pathlib.Path) -> BenchmarkTool:
        """Detect benchmark tool from file content."""
        try:
            with open(file_path) as f:
                data = json.load(f)

            # Check for pytest-benchmark markers
            if "benchmarks" in data and "machine_info" in data:
                return BenchmarkTool.PYTEST_BENCHMARK

            # Check for criterion markers
            if isinstance(data, dict) and ("typical" in data or "mean" in data):
                return BenchmarkTool.CRITERION

            if isinstance(data, list):
                return BenchmarkTool.CRITERION

        except (json.JSONDecodeError, KeyError):
            pass

        return BenchmarkTool.UNKNOWN

    @staticmethod
    def parse_file(file_path: pathlib.Path) -> Optional[BenchmarkReport]:
        """Parse benchmark file (auto-detect tool)."""
        tool = BenchmarkAnalyzer.detect_tool(file_path)

        if tool == BenchmarkTool.CRITERION:
            return CriterionParser.parse(file_path)
        elif tool == BenchmarkTool.PYTEST_BENCHMARK:
            return PytestBenchmarkParser.parse(file_path)
        else:
            return None

    @staticmethod
    def compare(
        baseline: BenchmarkReport,
        current: BenchmarkReport,
        threshold: float = 5.0,
    ) -> List[BenchmarkComparison]:
        """Compare two benchmark reports."""
        comparisons: List[BenchmarkComparison] = []

        # Build baseline map
        baseline_map = {b.name: b for b in baseline.benchmarks}

        for current_bench in current.benchmarks:
            baseline_bench = baseline_map.get(current_bench.name)
            if not baseline_bench:
                continue

            # Calculate percentage change
            mean_delta = BenchmarkAnalyzer._calculate_delta(
                baseline_bench.stats.mean,
                current_bench.stats.mean,
            )

            median_delta = BenchmarkAnalyzer._calculate_delta(
                baseline_bench.stats.median,
                current_bench.stats.median,
            )

            # Determine severity
            severity = BenchmarkAnalyzer._determine_severity(mean_delta, threshold)

            comparisons.append(
                BenchmarkComparison(
                    name=current_bench.name,
                    baseline=baseline_bench,
                    current=current_bench,
                    mean_delta=mean_delta,
                    median_delta=median_delta,
                    severity=severity,
                )
            )

        return comparisons

    @staticmethod
    def _calculate_delta(baseline: float, current: float) -> float:
        """Calculate percentage change."""
        if baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100.0

    @staticmethod
    def _determine_severity(delta: float, threshold: float) -> RegressionSeverity:
        """Determine regression severity based on delta."""
        if delta < -threshold:
            return RegressionSeverity.IMPROVEMENT
        elif delta < threshold:
            return RegressionSeverity.NONE
        elif delta < threshold * 2:
            return RegressionSeverity.LOW
        elif delta < threshold * 5:
            return RegressionSeverity.MEDIUM
        elif delta < threshold * 10:
            return RegressionSeverity.HIGH
        else:
            return RegressionSeverity.CRITICAL


class BenchmarkReportGenerator:
    """Generate benchmark reports."""

    def __init__(self, report: BenchmarkReport):
        """Initialize report generator."""
        self.report = report

    def generate(self, format: OutputFormat, output_file: Optional[pathlib.Path] = None) -> str:
        """Generate report in specified format."""
        if format == OutputFormat.TEXT:
            content = self._generate_text()
        elif format == OutputFormat.JSON:
            content = self._generate_json()
        elif format == OutputFormat.HTML:
            content = self._generate_html()
        elif format == OutputFormat.MARKDOWN:
            content = self._generate_markdown()
        else:
            raise ValueError(f"Unknown format: {format}")

        if output_file:
            output_file.write_text(content)

        return content

    def _generate_text(self) -> str:
        """Generate plain text report."""
        lines = [
            f"Benchmark Report: {self.report.project_name}",
            "=" * 80,
            f"Tool: {self.report.tool.value}",
            f"Timestamp: {self.report.timestamp}",
            f"Total Benchmarks: {self.report.total_benchmarks}",
            f"Stable Benchmarks: {self.report.stable_benchmarks} ({self.report.stable_benchmarks / self.report.total_benchmarks * 100:.1f}%)",
            "",
            "Benchmarks:",
            "-" * 80,
        ]

        for bench in sorted(self.report.benchmarks, key=lambda b: b.stats.mean):
            lines.extend([
                f"\n{bench.name}",
                f"  Mean:   {bench.format_time(bench.stats.mean)}",
                f"  Median: {bench.format_time(bench.stats.median)}",
                f"  StdDev: {bench.format_time(bench.stats.std_dev)}",
                f"  Min:    {bench.format_time(bench.stats.min)}",
                f"  Max:    {bench.format_time(bench.stats.max)}",
                f"  CV:     {bench.stats.coefficient_of_variation:.2f}%",
                f"  Stable: {'Yes' if bench.stats.is_stable else 'No'}",
            ])

            if bench.group:
                lines.append(f"  Group:  {bench.group}")

        return "\n".join(lines)

    def _generate_json(self) -> str:
        """Generate JSON report."""
        return json.dumps(self.report.to_dict(), indent=2)

    def _generate_html(self) -> str:
        """Generate HTML report."""
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>Benchmark Report: {self.report.project_name}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; }",
            "table { border-collapse: collapse; width: 100%; margin: 20px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #4CAF50; color: white; }",
            "tr:nth-child(even) { background-color: #f2f2f2; }",
            ".stable { color: green; }",
            ".unstable { color: orange; }",
            ".summary { background-color: #f2f2f2; padding: 15px; margin: 20px 0; border-radius: 5px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>Benchmark Report: {self.report.project_name}</h1>",
            f"<p><strong>Tool:</strong> {self.report.tool.value}</p>",
            f"<p><strong>Timestamp:</strong> {self.report.timestamp}</p>",
            '<div class="summary">',
            "<h2>Summary</h2>",
            f"<p><strong>Total Benchmarks:</strong> {self.report.total_benchmarks}</p>",
            f"<p><strong>Stable Benchmarks:</strong> {self.report.stable_benchmarks} ({self.report.stable_benchmarks / self.report.total_benchmarks * 100:.1f}%)</p>",
            "</div>",
            "<h2>Benchmarks</h2>",
            "<table>",
            "<tr>",
            "<th>Name</th>",
            "<th>Mean</th>",
            "<th>Median</th>",
            "<th>StdDev</th>",
            "<th>Min</th>",
            "<th>Max</th>",
            "<th>CV (%)</th>",
            "<th>Stable</th>",
            "</tr>",
        ]

        for bench in sorted(self.report.benchmarks, key=lambda b: b.stats.mean):
            stable_class = "stable" if bench.stats.is_stable else "unstable"
            stable_text = "Yes" if bench.stats.is_stable else "No"

            html.extend([
                "<tr>",
                f"<td>{bench.name}</td>",
                f"<td>{bench.format_time(bench.stats.mean)}</td>",
                f"<td>{bench.format_time(bench.stats.median)}</td>",
                f"<td>{bench.format_time(bench.stats.std_dev)}</td>",
                f"<td>{bench.format_time(bench.stats.min)}</td>",
                f"<td>{bench.format_time(bench.stats.max)}</td>",
                f"<td>{bench.stats.coefficient_of_variation:.2f}</td>",
                f'<td class="{stable_class}">{stable_text}</td>',
                "</tr>",
            ])

        html.extend(["</table>", "</body>", "</html>"])

        return "\n".join(html)

    def _generate_markdown(self) -> str:
        """Generate Markdown report."""
        lines = [
            f"# Benchmark Report: {self.report.project_name}",
            "",
            f"**Tool:** {self.report.tool.value}",
            f"**Timestamp:** {self.report.timestamp}",
            "",
            "## Summary",
            "",
            f"- **Total Benchmarks:** {self.report.total_benchmarks}",
            f"- **Stable Benchmarks:** {self.report.stable_benchmarks} ({self.report.stable_benchmarks / self.report.total_benchmarks * 100:.1f}%)",
            "",
            "## Benchmarks",
            "",
            "| Name | Mean | Median | StdDev | CV (%) | Stable |",
            "|------|------|--------|--------|--------|--------|",
        ]

        for bench in sorted(self.report.benchmarks, key=lambda b: b.stats.mean):
            stable = "✅" if bench.stats.is_stable else "⚠️"
            lines.append(
                f"| {bench.name} | {bench.format_time(bench.stats.mean)} | "
                f"{bench.format_time(bench.stats.median)} | "
                f"{bench.format_time(bench.stats.std_dev)} | "
                f"{bench.stats.coefficient_of_variation:.2f} | {stable} |"
            )

        return "\n".join(lines)


class ComparisonReportGenerator:
    """Generate comparison reports."""

    def __init__(self, comparisons: List[BenchmarkComparison]):
        """Initialize comparison report generator."""
        self.comparisons = comparisons

    def generate(self, format: OutputFormat, output_file: Optional[pathlib.Path] = None) -> str:
        """Generate comparison report."""
        if format == OutputFormat.TEXT:
            content = self._generate_text()
        elif format == OutputFormat.JSON:
            content = self._generate_json()
        elif format == OutputFormat.MARKDOWN:
            content = self._generate_markdown()
        else:
            raise ValueError(f"Unknown format: {format}")

        if output_file:
            output_file.write_text(content)

        return content

    def _generate_text(self) -> str:
        """Generate plain text comparison."""
        regressions = [c for c in self.comparisons if c.is_regression]
        improvements = [c for c in self.comparisons if c.is_improvement]
        stable = [c for c in self.comparisons if c.severity == RegressionSeverity.NONE]

        lines = [
            "Benchmark Comparison",
            "=" * 80,
            f"Total Comparisons: {len(self.comparisons)}",
            f"Regressions: {len(regressions)}",
            f"Improvements: {len(improvements)}",
            f"Stable: {len(stable)}",
            "",
        ]

        if regressions:
            lines.extend(["Regressions:", "-" * 80])
            for comp in sorted(regressions, key=lambda c: abs(c.mean_delta), reverse=True):
                lines.extend([
                    f"\n{comp.name} [{comp.severity.value}]",
                    f"  Baseline: {comp.baseline.format_time(comp.baseline.stats.mean)}",
                    f"  Current:  {comp.current.format_time(comp.current.stats.mean)}",
                    f"  Delta:    {comp.mean_delta:+.2f}%",
                ])

        if improvements:
            lines.extend(["\n\nImprovements:", "-" * 80])
            for comp in sorted(improvements, key=lambda c: c.mean_delta):
                lines.extend([
                    f"\n{comp.name}",
                    f"  Baseline: {comp.baseline.format_time(comp.baseline.stats.mean)}",
                    f"  Current:  {comp.current.format_time(comp.current.stats.mean)}",
                    f"  Delta:    {comp.mean_delta:+.2f}%",
                ])

        return "\n".join(lines)

    def _generate_json(self) -> str:
        """Generate JSON comparison."""
        data = {
            "comparisons": [c.to_dict() for c in self.comparisons],
            "summary": {
                "total": len(self.comparisons),
                "regressions": sum(1 for c in self.comparisons if c.is_regression),
                "improvements": sum(1 for c in self.comparisons if c.is_improvement),
                "stable": sum(1 for c in self.comparisons if c.severity == RegressionSeverity.NONE),
            },
        }
        return json.dumps(data, indent=2)

    def _generate_markdown(self) -> str:
        """Generate Markdown comparison."""
        regressions = [c for c in self.comparisons if c.is_regression]
        improvements = [c for c in self.comparisons if c.is_improvement]
        stable = [c for c in self.comparisons if c.severity == RegressionSeverity.NONE]

        lines = [
            "# Benchmark Comparison",
            "",
            f"**Total Comparisons:** {len(self.comparisons)}",
            f"**Regressions:** {len(regressions)} ❌",
            f"**Improvements:** {len(improvements)} ✅",
            f"**Stable:** {len(stable)} ➡️",
            "",
        ]

        if regressions:
            lines.extend([
                "## Regressions",
                "",
                "| Benchmark | Baseline | Current | Delta | Severity |",
                "|-----------|----------|---------|-------|----------|",
            ])

            for comp in sorted(regressions, key=lambda c: abs(c.mean_delta), reverse=True):
                lines.append(
                    f"| {comp.name} | {comp.baseline.format_time(comp.baseline.stats.mean)} | "
                    f"{comp.current.format_time(comp.current.stats.mean)} | "
                    f"{comp.mean_delta:+.2f}% | {comp.severity.value} |"
                )

        if improvements:
            lines.extend([
                "",
                "## Improvements",
                "",
                "| Benchmark | Baseline | Current | Delta |",
                "|-----------|----------|---------|-------|",
            ])

            for comp in sorted(improvements, key=lambda c: c.mean_delta):
                lines.append(
                    f"| {comp.name} | {comp.baseline.format_time(comp.baseline.stats.mean)} | "
                    f"{comp.current.format_time(comp.current.stats.mean)} | "
                    f"{comp.mean_delta:+.2f}% |"
                )

        return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PyO3 Benchmark Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze benchmark results")
    analyze_parser.add_argument("file", type=pathlib.Path, help="Benchmark results file")
    analyze_parser.add_argument(
        "--format",
        choices=["text", "json", "html", "markdown"],
        default="text",
        help="Output format",
    )
    analyze_parser.add_argument("--output", type=pathlib.Path, help="Output file")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two benchmark runs")
    compare_parser.add_argument("baseline", type=pathlib.Path, help="Baseline results")
    compare_parser.add_argument("current", type=pathlib.Path, help="Current results")
    compare_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format",
    )
    compare_parser.add_argument("--output", type=pathlib.Path, help="Output file")
    compare_parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
        help="Regression threshold percentage (default: 5%%)",
    )

    # Regression command
    regression_parser = subparsers.add_parser("regression", help="Detect regressions")
    regression_parser.add_argument("file", type=pathlib.Path, help="Current results")
    regression_parser.add_argument("--baseline", type=pathlib.Path, required=True, help="Baseline results")
    regression_parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
        help="Regression threshold percentage (default: 5%%)",
    )
    regression_parser.add_argument("--fail-on-regression", action="store_true", help="Exit with error if regressions found")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate detailed report")
    report_parser.add_argument("file", type=pathlib.Path, help="Benchmark results file")
    report_parser.add_argument(
        "--format",
        choices=["text", "json", "html", "markdown"],
        default="html",
        help="Output format",
    )
    report_parser.add_argument("--output", type=pathlib.Path, help="Output file")

    # Visualize command
    visualize_parser = subparsers.add_parser("visualize", help="Create visualizations")
    visualize_parser.add_argument("file", type=pathlib.Path, help="Benchmark results file")
    visualize_parser.add_argument("--benchmarks", help="Filter benchmarks (glob pattern)")
    visualize_parser.add_argument("--output", type=pathlib.Path, help="Output directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "analyze":
            return cmd_analyze(args)
        elif args.command == "compare":
            return cmd_compare(args)
        elif args.command == "regression":
            return cmd_regression(args)
        elif args.command == "report":
            return cmd_report(args)
        elif args.command == "visualize":
            return cmd_visualize(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze benchmark results."""
    report = BenchmarkAnalyzer.parse_file(args.file)
    if not report:
        print(f"Failed to parse benchmark file: {args.file}", file=sys.stderr)
        return 1

    generator = BenchmarkReportGenerator(report)
    format = OutputFormat(args.format)
    output = generator.generate(format, args.output)

    if not args.output:
        print(output)

    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Compare two benchmark runs."""
    baseline = BenchmarkAnalyzer.parse_file(args.baseline)
    if not baseline:
        print(f"Failed to parse baseline file: {args.baseline}", file=sys.stderr)
        return 1

    current = BenchmarkAnalyzer.parse_file(args.current)
    if not current:
        print(f"Failed to parse current file: {args.current}", file=sys.stderr)
        return 1

    comparisons = BenchmarkAnalyzer.compare(baseline, current, args.threshold)

    generator = ComparisonReportGenerator(comparisons)
    format = OutputFormat(args.format)
    output = generator.generate(format, args.output)

    if not args.output:
        print(output)

    return 0


def cmd_regression(args: argparse.Namespace) -> int:
    """Detect performance regressions."""
    baseline = BenchmarkAnalyzer.parse_file(args.baseline)
    if not baseline:
        print(f"Failed to parse baseline file: {args.baseline}", file=sys.stderr)
        return 1

    current = BenchmarkAnalyzer.parse_file(args.file)
    if not current:
        print(f"Failed to parse current file: {args.file}", file=sys.stderr)
        return 1

    comparisons = BenchmarkAnalyzer.compare(baseline, current, args.threshold)
    regressions = [c for c in comparisons if c.is_regression]

    if regressions:
        print(f"Found {len(regressions)} regression(s):")
        for reg in regressions:
            print(f"  {reg.name}: {reg.mean_delta:+.2f}% ({reg.severity.value})")

        if args.fail_on_regression:
            return 1

    else:
        print("No regressions detected.")

    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generate detailed report."""
    report = BenchmarkAnalyzer.parse_file(args.file)
    if not report:
        print(f"Failed to parse benchmark file: {args.file}", file=sys.stderr)
        return 1

    generator = BenchmarkReportGenerator(report)
    format = OutputFormat(args.format)
    output = generator.generate(format, args.output)

    if not args.output:
        print(output)
    else:
        print(f"Report saved to: {args.output}")

    return 0


def cmd_visualize(args: argparse.Namespace) -> int:
    """Create visualizations."""
    print("Visualization not yet implemented.", file=sys.stderr)
    print("Consider using external tools like matplotlib or plotly.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
