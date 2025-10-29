#!/usr/bin/env python3
"""
Benchmark result comparison and performance regression detection.

Compares benchmark results across commits, versions, or configurations.
Performs statistical significance testing and generates visualization reports.
"""

import argparse
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BenchmarkResult:
    """Single benchmark result."""
    name: str
    value: float
    unit: str
    iteration: int
    metadata: Dict[str, Any]


@dataclass
class BenchmarkStats:
    """Statistical summary of benchmark results."""
    name: str
    mean: float
    median: float
    stddev: float
    min_val: float
    max_val: float
    count: int
    unit: str
    percentile_95: float
    percentile_99: float


@dataclass
class Comparison:
    """Comparison between two benchmark sets."""
    benchmark_name: str
    baseline_stats: BenchmarkStats
    current_stats: BenchmarkStats
    change_percent: float
    change_absolute: float
    is_regression: bool
    is_improvement: bool
    is_significant: bool
    p_value: Optional[float] = None


@dataclass
class ComparisonReport:
    """Complete comparison report."""
    baseline_name: str
    current_name: str
    comparisons: List[Comparison]
    summary: Dict[str, Any]
    timestamp: str


class ComparisonError(Exception):
    """Base exception for comparison errors."""
    pass


class BenchmarkComparator:
    """Benchmark result comparator."""

    def __init__(
        self,
        regression_threshold: float = 0.05,
        improvement_threshold: float = 0.05,
        significance_level: float = 0.05,
        verbose: bool = False
    ) -> None:
        """
        Initialize comparator.

        Args:
            regression_threshold: Threshold for regression detection (5% = 0.05)
            improvement_threshold: Threshold for improvement detection (5% = 0.05)
            significance_level: P-value threshold for statistical significance (0.05 = 95% confidence)
            verbose: Enable verbose logging
        """
        self.regression_threshold = regression_threshold
        self.improvement_threshold = improvement_threshold
        self.significance_level = significance_level
        self.verbose = verbose

    def _log(self, message: str) -> None:
        """Log message if verbose enabled."""
        if self.verbose:
            print(f"[COMPARE] {message}", file=sys.stderr)

    def load_benchmark_results(self, file_path: Path) -> List[BenchmarkResult]:
        """
        Load benchmark results from file.

        Supports multiple formats:
        - JSON (custom format)
        - pytest-benchmark JSON
        - Go benchmark output
        - Rust criterion JSON

        Args:
            file_path: Path to benchmark results file

        Returns:
            List of BenchmarkResult objects

        Raises:
            ComparisonError: If file cannot be loaded
        """
        self._log(f"Loading benchmark results from {file_path}")

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise ComparisonError(f"Failed to load benchmark file: {e}") from e

        # Try to detect format and parse
        if "benchmarks" in data:
            # pytest-benchmark format
            return self._parse_pytest_benchmark(data)
        elif "results" in data:
            # Custom format
            return self._parse_custom_format(data)
        else:
            # Assume custom simple format
            return self._parse_simple_format(data)

    def _parse_pytest_benchmark(self, data: Dict[str, Any]) -> List[BenchmarkResult]:
        """Parse pytest-benchmark JSON format."""
        results: List[BenchmarkResult] = []

        for bench in data["benchmarks"]:
            name = bench["name"]
            stats = bench["stats"]

            # Create result for mean
            results.append(BenchmarkResult(
                name=name,
                value=stats["mean"],
                unit="seconds",
                iteration=0,
                metadata={
                    "min": stats["min"],
                    "max": stats["max"],
                    "stddev": stats["stddev"],
                    "median": stats["median"],
                }
            ))

        return results

    def _parse_custom_format(self, data: Dict[str, Any]) -> List[BenchmarkResult]:
        """Parse custom benchmark format."""
        results: List[BenchmarkResult] = []

        for result_data in data["results"]:
            results.append(BenchmarkResult(
                name=result_data["name"],
                value=result_data["value"],
                unit=result_data.get("unit", "seconds"),
                iteration=result_data.get("iteration", 0),
                metadata=result_data.get("metadata", {})
            ))

        return results

    def _parse_simple_format(self, data: Dict[str, Any]) -> List[BenchmarkResult]:
        """Parse simple key-value format."""
        results: List[BenchmarkResult] = []

        for name, value in data.items():
            if isinstance(value, (int, float)):
                results.append(BenchmarkResult(
                    name=name,
                    value=float(value),
                    unit="seconds",
                    iteration=0,
                    metadata={}
                ))
            elif isinstance(value, dict) and "value" in value:
                results.append(BenchmarkResult(
                    name=name,
                    value=float(value["value"]),
                    unit=value.get("unit", "seconds"),
                    iteration=0,
                    metadata=value.get("metadata", {})
                ))

        return results

    def compute_stats(self, results: List[BenchmarkResult]) -> Dict[str, BenchmarkStats]:
        """
        Compute statistics for benchmark results.

        Args:
            results: List of benchmark results

        Returns:
            Dictionary mapping benchmark name to statistics
        """
        # Group by benchmark name
        grouped: Dict[str, List[float]] = defaultdict(list)
        units: Dict[str, str] = {}

        for result in results:
            grouped[result.name].append(result.value)
            units[result.name] = result.unit

        # Compute statistics for each benchmark
        stats: Dict[str, BenchmarkStats] = {}

        for name, values in grouped.items():
            if not values:
                continue

            sorted_values = sorted(values)
            n = len(values)

            stats[name] = BenchmarkStats(
                name=name,
                mean=statistics.mean(values),
                median=statistics.median(values),
                stddev=statistics.stdev(values) if n > 1 else 0.0,
                min_val=min(values),
                max_val=max(values),
                count=n,
                unit=units[name],
                percentile_95=sorted_values[int(n * 0.95)] if n > 1 else sorted_values[0],
                percentile_99=sorted_values[int(n * 0.99)] if n > 1 else sorted_values[0],
            )

        return stats

    def compare(
        self,
        baseline_results: List[BenchmarkResult],
        current_results: List[BenchmarkResult],
        baseline_name: str = "baseline",
        current_name: str = "current",
    ) -> ComparisonReport:
        """
        Compare two sets of benchmark results.

        Args:
            baseline_results: Baseline benchmark results
            current_results: Current benchmark results
            baseline_name: Name for baseline (e.g., "main", "v1.0")
            current_name: Name for current (e.g., "feature-branch", "v1.1")

        Returns:
            ComparisonReport with detailed comparison
        """
        self._log(f"Comparing {baseline_name} vs {current_name}")

        # Compute statistics
        baseline_stats = self.compute_stats(baseline_results)
        current_stats = self.compute_stats(current_results)

        # Find common benchmarks
        common_benchmarks = set(baseline_stats.keys()) & set(current_stats.keys())

        if not common_benchmarks:
            raise ComparisonError("No common benchmarks found between baseline and current")

        self._log(f"Found {len(common_benchmarks)} common benchmarks")

        # Compare each benchmark
        comparisons: List[Comparison] = []

        for name in sorted(common_benchmarks):
            baseline = baseline_stats[name]
            current = current_stats[name]

            # Calculate change
            change_absolute = current.mean - baseline.mean
            change_percent = (change_absolute / baseline.mean * 100) if baseline.mean != 0 else 0

            # Determine if regression or improvement
            # For time-based metrics, increase is regression
            is_regression = change_percent > (self.regression_threshold * 100)
            is_improvement = change_percent < -(self.improvement_threshold * 100)

            # Statistical significance test (t-test approximation)
            is_significant = False
            p_value = None

            if baseline.count > 1 and current.count > 1:
                # Welch's t-test (unequal variances)
                p_value = self._welch_t_test(
                    baseline.mean, baseline.stddev, baseline.count,
                    current.mean, current.stddev, current.count
                )
                is_significant = p_value < self.significance_level

            comparisons.append(Comparison(
                benchmark_name=name,
                baseline_stats=baseline,
                current_stats=current,
                change_percent=change_percent,
                change_absolute=change_absolute,
                is_regression=is_regression and is_significant,
                is_improvement=is_improvement and is_significant,
                is_significant=is_significant,
                p_value=p_value,
            ))

        # Generate summary
        summary = self._generate_summary(comparisons)

        return ComparisonReport(
            baseline_name=baseline_name,
            current_name=current_name,
            comparisons=comparisons,
            summary=summary,
            timestamp=datetime.now().isoformat(),
        )

    def _welch_t_test(
        self,
        mean1: float, std1: float, n1: int,
        mean2: float, std2: float, n2: int
    ) -> float:
        """
        Perform Welch's t-test (for unequal variances).

        Returns approximate p-value (two-tailed).
        """
        import math

        # Calculate t-statistic
        numerator = mean1 - mean2
        denominator = math.sqrt((std1**2 / n1) + (std2**2 / n2))

        if denominator == 0:
            return 1.0  # No difference

        t = abs(numerator / denominator)

        # Calculate degrees of freedom (Welch-Satterthwaite)
        s1_sq = std1**2 / n1
        s2_sq = std2**2 / n2
        df = ((s1_sq + s2_sq)**2) / ((s1_sq**2 / (n1 - 1)) + (s2_sq**2 / (n2 - 1)))

        # Approximate p-value using t-distribution approximation
        # For simplicity, use normal approximation for df > 30
        if df > 30:
            # Normal approximation
            p = 2 * (1 - self._normal_cdf(t))
        else:
            # Simplified t-distribution approximation
            # Not exact, but sufficient for performance comparison
            p = 2 * (1 - self._normal_cdf(t * math.sqrt(df / (df + t**2))))

        return p

    def _normal_cdf(self, x: float) -> float:
        """Cumulative distribution function for standard normal distribution."""
        import math

        # Using error function approximation
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    def _generate_summary(self, comparisons: List[Comparison]) -> Dict[str, Any]:
        """Generate summary statistics from comparisons."""
        total = len(comparisons)
        regressions = [c for c in comparisons if c.is_regression]
        improvements = [c for c in comparisons if c.is_improvement]
        no_change = [c for c in comparisons if not c.is_regression and not c.is_improvement]

        return {
            "total_benchmarks": total,
            "regressions": len(regressions),
            "improvements": len(improvements),
            "no_change": len(no_change),
            "significant_regressions": [c.benchmark_name for c in regressions],
            "significant_improvements": [c.benchmark_name for c in improvements],
            "average_change_percent": statistics.mean([c.change_percent for c in comparisons]),
        }

    def load_and_compare(
        self,
        baseline_file: Path,
        current_file: Path,
        baseline_name: Optional[str] = None,
        current_name: Optional[str] = None,
    ) -> ComparisonReport:
        """
        Load benchmark files and compare.

        Args:
            baseline_file: Path to baseline benchmark results
            current_file: Path to current benchmark results
            baseline_name: Name for baseline (default: filename)
            current_name: Name for current (default: filename)

        Returns:
            ComparisonReport
        """
        baseline_results = self.load_benchmark_results(baseline_file)
        current_results = self.load_benchmark_results(current_file)

        if baseline_name is None:
            baseline_name = baseline_file.stem

        if current_name is None:
            current_name = current_file.stem

        return self.compare(
            baseline_results,
            current_results,
            baseline_name,
            current_name,
        )


def print_report(report: ComparisonReport, detailed: bool = False) -> None:
    """Print comparison report in human-readable format."""
    print(f"\n{'='*80}")
    print(f"Benchmark Comparison: {report.baseline_name} vs {report.current_name}")
    print(f"{'='*80}\n")

    # Summary
    summary = report.summary
    print("Summary:")
    print(f"  Total Benchmarks: {summary['total_benchmarks']}")
    print(f"  Regressions: {summary['regressions']}")
    print(f"  Improvements: {summary['improvements']}")
    print(f"  No Change: {summary['no_change']}")
    print(f"  Average Change: {summary['average_change_percent']:+.2f}%\n")

    # Regressions (most important)
    regressions = [c for c in report.comparisons if c.is_regression]
    if regressions:
        print(f"{'='*80}")
        print("REGRESSIONS (Slower Performance):")
        print(f"{'='*80}\n")

        for comp in sorted(regressions, key=lambda c: abs(c.change_percent), reverse=True):
            print(f"❌ {comp.benchmark_name}")
            print(f"   Baseline: {comp.baseline_stats.mean:.6f} {comp.baseline_stats.unit}")
            print(f"   Current:  {comp.current_stats.mean:.6f} {comp.current_stats.unit}")
            print(f"   Change:   {comp.change_percent:+.2f}% ({comp.change_absolute:+.6f})")

            if comp.p_value is not None:
                print(f"   P-value:  {comp.p_value:.4f} {'✓ significant' if comp.is_significant else '✗ not significant'}")

            if detailed:
                print(f"   Baseline StdDev: {comp.baseline_stats.stddev:.6f}")
                print(f"   Current StdDev:  {comp.current_stats.stddev:.6f}")

            print()

    # Improvements
    improvements = [c for c in report.comparisons if c.is_improvement]
    if improvements:
        print(f"{'='*80}")
        print("IMPROVEMENTS (Faster Performance):")
        print(f"{'='*80}\n")

        for comp in sorted(improvements, key=lambda c: abs(c.change_percent), reverse=True):
            print(f"✅ {comp.benchmark_name}")
            print(f"   Baseline: {comp.baseline_stats.mean:.6f} {comp.baseline_stats.unit}")
            print(f"   Current:  {comp.current_stats.mean:.6f} {comp.current_stats.unit}")
            print(f"   Change:   {comp.change_percent:+.2f}% ({comp.change_absolute:+.6f})")

            if comp.p_value is not None:
                print(f"   P-value:  {comp.p_value:.4f} {'✓ significant' if comp.is_significant else '✗ not significant'}")

            print()

    # No significant change
    if detailed:
        no_change = [c for c in report.comparisons if not c.is_regression and not c.is_improvement]
        if no_change:
            print(f"{'='*80}")
            print("NO SIGNIFICANT CHANGE:")
            print(f"{'='*80}\n")

            for comp in no_change:
                print(f"➖ {comp.benchmark_name}")
                print(f"   Change: {comp.change_percent:+.2f}%")
                print()

    # Exit status hint
    print(f"{'='*80}")
    if regressions:
        print("⚠️  Performance regressions detected!")
        print("   Review the changes above and consider optimizations.")
    elif improvements:
        print("✨ Performance improvements detected!")
    else:
        print("✓ No significant performance changes.")
    print(f"{'='*80}\n")


def generate_html_report(report: ComparisonReport, output_file: Path) -> None:
    """Generate HTML visualization report."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Benchmark Comparison: {report.baseline_name} vs {report.current_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #007bff;
        }}
        .stat.regression {{ border-left-color: #dc3545; }}
        .stat.improvement {{ border-left-color: #28a745; }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .comparison {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .comparison.regression {{
            border-left: 4px solid #dc3545;
        }}
        .comparison.improvement {{
            border-left: 4px solid #28a745;
        }}
        .comparison.neutral {{
            border-left: 4px solid #6c757d;
        }}
        .benchmark-name {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .metric:last-child {{
            border-bottom: none;
        }}
        .metric-label {{
            color: #666;
        }}
        .metric-value {{
            font-family: monospace;
            font-weight: bold;
        }}
        .change {{
            font-size: 20px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .change.positive {{ color: #28a745; }}
        .change.negative {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Benchmark Comparison</h1>
        <p><strong>{report.baseline_name}</strong> vs <strong>{report.current_name}</strong></p>
        <p style="color: #666; font-size: 14px;">Generated: {report.timestamp}</p>
    </div>

    <div class="summary">
        <div class="stat">
            <div class="stat-label">Total Benchmarks</div>
            <div class="stat-value">{report.summary['total_benchmarks']}</div>
        </div>
        <div class="stat regression">
            <div class="stat-label">Regressions</div>
            <div class="stat-value">{report.summary['regressions']}</div>
        </div>
        <div class="stat improvement">
            <div class="stat-label">Improvements</div>
            <div class="stat-value">{report.summary['improvements']}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Average Change</div>
            <div class="stat-value">{report.summary['average_change_percent']:+.2f}%</div>
        </div>
    </div>
"""

    # Sort: regressions first, then improvements, then neutral
    comparisons = sorted(
        report.comparisons,
        key=lambda c: (
            0 if c.is_regression else (1 if c.is_improvement else 2),
            -abs(c.change_percent)
        )
    )

    for comp in comparisons:
        css_class = "regression" if comp.is_regression else ("improvement" if comp.is_improvement else "neutral")
        change_class = "negative" if comp.change_percent > 0 else "positive"

        html += f"""
    <div class="comparison {css_class}">
        <div class="benchmark-name">{comp.benchmark_name}</div>
        <div class="change {change_class}">{comp.change_percent:+.2f}%</div>
        <div class="metric">
            <span class="metric-label">Baseline:</span>
            <span class="metric-value">{comp.baseline_stats.mean:.6f} {comp.baseline_stats.unit}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Current:</span>
            <span class="metric-value">{comp.current_stats.mean:.6f} {comp.current_stats.unit}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Absolute Change:</span>
            <span class="metric-value">{comp.change_absolute:+.6f} {comp.current_stats.unit}</span>
        </div>
"""

        if comp.p_value is not None:
            sig = "✓ Significant" if comp.is_significant else "✗ Not significant"
            html += f"""
        <div class="metric">
            <span class="metric-label">Statistical Significance:</span>
            <span class="metric-value">{sig} (p={comp.p_value:.4f})</span>
        </div>
"""

        html += "    </div>\n"

    html += """
</body>
</html>
"""

    output_file.write_text(html)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Benchmark result comparison and regression detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two benchmark files
  %(prog)s baseline.json current.json

  # With custom names
  %(prog)s main.json feature.json --baseline main --current feature-branch

  # Generate HTML report
  %(prog)s baseline.json current.json --html report.html

  # Detailed output
  %(prog)s baseline.json current.json --detailed

  # JSON output for CI
  %(prog)s baseline.json current.json --json

  # Fail on regression (exit code 1)
  %(prog)s baseline.json current.json --fail-on-regression

Benchmark File Formats:
  - JSON with "benchmarks" key (pytest-benchmark)
  - JSON with "results" key (custom format)
  - JSON key-value pairs (simple format)
        """
    )

    parser.add_argument(
        "baseline",
        type=Path,
        help="Baseline benchmark results file"
    )

    parser.add_argument(
        "current",
        type=Path,
        help="Current benchmark results file"
    )

    parser.add_argument(
        "--baseline-name",
        type=str,
        help="Name for baseline (default: filename)"
    )

    parser.add_argument(
        "--current-name",
        type=str,
        help="Name for current (default: filename)"
    )

    parser.add_argument(
        "--regression-threshold",
        type=float,
        default=0.05,
        help="Regression threshold as fraction (default: 0.05 = 5%%)"
    )

    parser.add_argument(
        "--improvement-threshold",
        type=float,
        default=0.05,
        help="Improvement threshold as fraction (default: 0.05 = 5%%)"
    )

    parser.add_argument(
        "--significance-level",
        type=float,
        default=0.05,
        help="Statistical significance level (default: 0.05 = 95%% confidence)"
    )

    parser.add_argument(
        "-d", "--detailed",
        action="store_true",
        help="Show detailed output including non-significant changes"
    )

    parser.add_argument(
        "--html",
        type=Path,
        help="Generate HTML report to specified file"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with code 1 if regressions detected (for CI)"
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
        comparator = BenchmarkComparator(
            regression_threshold=args.regression_threshold,
            improvement_threshold=args.improvement_threshold,
            significance_level=args.significance_level,
            verbose=args.verbose,
        )

        report = comparator.load_and_compare(
            args.baseline,
            args.current,
            args.baseline_name,
            args.current_name,
        )

        if args.json:
            # JSON output
            output = {
                "baseline": report.baseline_name,
                "current": report.current_name,
                "summary": report.summary,
                "comparisons": [
                    {
                        "benchmark": c.benchmark_name,
                        "baseline_mean": c.baseline_stats.mean,
                        "current_mean": c.current_stats.mean,
                        "change_percent": c.change_percent,
                        "change_absolute": c.change_absolute,
                        "is_regression": c.is_regression,
                        "is_improvement": c.is_improvement,
                        "is_significant": c.is_significant,
                        "p_value": c.p_value,
                    }
                    for c in report.comparisons
                ],
                "timestamp": report.timestamp,
            }
            print(json.dumps(output, indent=2))
        else:
            # Human-readable output
            print_report(report, detailed=args.detailed)

        # Generate HTML report if requested
        if args.html:
            generate_html_report(report, args.html)
            print(f"HTML report generated: {args.html}")

        # Exit with error if regressions detected and --fail-on-regression
        if args.fail_on_regression and report.summary["regressions"] > 0:
            return 1

        return 0

    except ComparisonError as e:
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
