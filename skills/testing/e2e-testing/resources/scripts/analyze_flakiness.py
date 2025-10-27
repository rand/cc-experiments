#!/usr/bin/env python3
"""
E2E Test Flakiness Analyzer

Analyzes E2E test stability by examining test history, identifying flaky tests,
root causes, and providing actionable recommendations for improvement.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


VERSION = "1.0.0"


@dataclass
class TestRun:
    """Single test execution result."""
    test_name: str
    status: str  # passed, failed, skipped
    duration: float
    timestamp: datetime
    browser: str = "chromium"
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class FlakyTest:
    """Flaky test analysis."""
    name: str
    total_runs: int
    pass_count: int
    fail_count: int
    flake_rate: float
    avg_duration: float
    common_errors: List[Tuple[str, int]]
    browsers_affected: Set[str]
    first_seen: datetime
    last_seen: datetime
    severity: str  # high, medium, low


@dataclass
class FlakinesReport:
    """Aggregated flakiness analysis."""
    total_tests: int = 0
    flaky_tests: int = 0
    stable_tests: int = 0
    overall_flake_rate: float = 0.0
    tests: List[FlakyTest] = field(default_factory=list)
    root_causes: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    analysis_period: str = ""


class FlakinessAnalyzer:
    """Analyze E2E test flakiness."""

    # Common flakiness patterns
    TIMEOUT_PATTERNS = [
        r"timeout",
        r"timed out",
        r"wait.*exceeded",
        r"no element found",
    ]

    TIMING_PATTERNS = [
        r"element not visible",
        r"element not interactable",
        r"still animating",
        r"element is hidden",
    ]

    NETWORK_PATTERNS = [
        r"network.*failed",
        r"connection.*refused",
        r"ECONNREFUSED",
        r"fetch.*failed",
        r"request.*timeout",
    ]

    STATE_PATTERNS = [
        r"state.*invalid",
        r"element not found",
        r"stale element",
        r"element is not attached",
    ]

    RACE_PATTERNS = [
        r"race condition",
        r"concurrent",
        r"already.*progress",
    ]

    def __init__(self, config: argparse.Namespace):
        self.config = config
        self.results_dir = Path(config.results_dir)
        self.threshold = config.threshold
        self.min_runs = config.min_runs
        self.days = config.days
        self.verbose = config.verbose

        # Analysis data
        self.test_runs: Dict[str, List[TestRun]] = defaultdict(list)
        self.flaky_tests: List[FlakyTest] = []
        self.root_causes: Counter = Counter()

    def log(self, message: str, level: str = "INFO"):
        """Log message to stderr."""
        if self.config.json_output:
            return

        colors = {
            "INFO": "\033[0;34m",
            "SUCCESS": "\033[0;32m",
            "WARNING": "\033[1;33m",
            "ERROR": "\033[0;31m",
        }
        reset = "\033[0m"
        color = colors.get(level, "")
        print(f"{color}[{level}]{reset} {message}", file=sys.stderr)

    def analyze(self) -> FlakinesReport:
        """Run complete flakiness analysis."""
        self.log("Starting flakiness analysis...")

        # Load test results
        self._load_test_results()

        # Analyze flakiness
        self._analyze_flakiness()

        # Identify root causes
        self._identify_root_causes()

        # Generate recommendations
        recommendations = self._generate_recommendations()

        # Build report
        report = FlakinesReport(
            total_tests=len(self.test_runs),
            flaky_tests=len(self.flaky_tests),
            stable_tests=len(self.test_runs) - len(self.flaky_tests),
            overall_flake_rate=self._calculate_overall_flake_rate(),
            tests=sorted(self.flaky_tests, key=lambda t: t.flake_rate, reverse=True),
            root_causes=dict(self.root_causes),
            recommendations=recommendations,
            analysis_period=f"Last {self.days} days"
        )

        return report

    def _load_test_results(self):
        """Load test results from JSON files."""
        self.log(f"Loading test results from {self.results_dir}")

        if not self.results_dir.exists():
            raise FileNotFoundError(f"Results directory not found: {self.results_dir}")

        # Find all result files
        result_files = list(self.results_dir.glob("**/results*.json"))
        self.log(f"Found {len(result_files)} result files")

        cutoff_date = datetime.now() - timedelta(days=self.days)

        for result_file in result_files:
            try:
                with open(result_file) as f:
                    data = json.load(f)

                timestamp = self._parse_timestamp(data, result_file)

                if timestamp < cutoff_date:
                    continue

                # Parse tests based on framework
                self._parse_test_results(data, timestamp)

            except Exception as e:
                self.log(f"Failed to parse {result_file}: {e}", "WARNING")

        self.log(f"Loaded {sum(len(runs) for runs in self.test_runs.values())} test runs")

    def _parse_timestamp(self, data: Dict, result_file: Path) -> datetime:
        """Extract timestamp from result data or file."""
        # Try to get from data
        if "start_time" in data:
            try:
                return datetime.fromisoformat(data["start_time"])
            except:
                pass

        if "timestamp" in data:
            try:
                return datetime.fromisoformat(data["timestamp"])
            except:
                pass

        # Fall back to file modification time
        return datetime.fromtimestamp(result_file.stat().st_mtime)

    def _parse_test_results(self, data: Dict, timestamp: datetime):
        """Parse test results from JSON data."""
        # Try different result formats
        tests = []

        # Playwright format
        if "tests" in data:
            tests = data["tests"]
        # Cypress format
        elif "runs" in data:
            for run in data["runs"]:
                for spec in run.get("specs", []):
                    tests.extend(spec.get("tests", []))
        # pytest format
        elif "tests" in data:
            tests = data["tests"]

        for test in tests:
            test_run = self._parse_test_run(test, timestamp)
            if test_run:
                self.test_runs[test_run.test_name].append(test_run)

    def _parse_test_run(self, test: Dict, timestamp: datetime) -> Optional[TestRun]:
        """Parse single test run."""
        try:
            # Extract test name
            name = (
                test.get("name") or
                test.get("title") or
                test.get("nodeid") or
                "Unknown"
            )

            # Extract status
            status = test.get("status", "unknown")
            if status == "expected":
                status = "passed"
            elif status == "unexpected":
                status = "failed"

            # Extract duration
            duration = test.get("duration", 0)
            if isinstance(duration, int) and duration > 1000:
                duration = duration / 1000.0  # Convert ms to seconds

            # Extract error
            error = None
            if "error" in test:
                error = test["error"].get("message") if isinstance(test["error"], dict) else str(test["error"])

            # Extract browser
            browser = test.get("browser") or test.get("projectName") or "chromium"

            # Extract retry count
            retry_count = test.get("retry", 0)

            return TestRun(
                test_name=name,
                status=status,
                duration=duration,
                timestamp=timestamp,
                browser=browser,
                error=error,
                retry_count=retry_count
            )

        except Exception as e:
            if self.verbose:
                self.log(f"Failed to parse test run: {e}", "WARNING")
            return None

    def _analyze_flakiness(self):
        """Analyze test runs to identify flaky tests."""
        self.log("Analyzing test flakiness...")

        for test_name, runs in self.test_runs.items():
            if len(runs) < self.min_runs:
                continue

            # Count outcomes
            pass_count = sum(1 for r in runs if r.status == "passed")
            fail_count = sum(1 for r in runs if r.status == "failed")
            total = pass_count + fail_count

            if total == 0:
                continue

            # Calculate flake rate
            flake_rate = fail_count / total

            # Only consider flaky if both passed and failed
            if pass_count > 0 and fail_count > 0 and flake_rate >= self.threshold:
                # Collect errors
                errors = [r.error for r in runs if r.error]
                common_errors = Counter(errors).most_common(3)

                # Calculate average duration
                durations = [r.duration for r in runs if r.duration > 0]
                avg_duration = sum(durations) / len(durations) if durations else 0

                # Collect affected browsers
                browsers = {r.browser for r in runs}

                # Timestamps
                timestamps = [r.timestamp for r in runs]
                first_seen = min(timestamps)
                last_seen = max(timestamps)

                # Determine severity
                severity = self._calculate_severity(flake_rate, fail_count)

                flaky = FlakyTest(
                    name=test_name,
                    total_runs=len(runs),
                    pass_count=pass_count,
                    fail_count=fail_count,
                    flake_rate=flake_rate,
                    avg_duration=avg_duration,
                    common_errors=common_errors,
                    browsers_affected=browsers,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    severity=severity
                )

                self.flaky_tests.append(flaky)

        self.log(f"Identified {len(self.flaky_tests)} flaky tests")

    def _calculate_severity(self, flake_rate: float, fail_count: int) -> str:
        """Calculate test severity based on flake rate and failure count."""
        if flake_rate >= 0.5 or fail_count >= 10:
            return "high"
        elif flake_rate >= 0.25 or fail_count >= 5:
            return "medium"
        else:
            return "low"

    def _identify_root_causes(self):
        """Identify common root causes of flakiness."""
        self.log("Identifying root causes...")

        for flaky in self.flaky_tests:
            for error, count in flaky.common_errors:
                if not error:
                    continue

                # Check for timeout issues
                if any(re.search(pattern, error, re.I) for pattern in self.TIMEOUT_PATTERNS):
                    self.root_causes["Timeout/Wait Issues"] += count

                # Check for timing issues
                elif any(re.search(pattern, error, re.I) for pattern in self.TIMING_PATTERNS):
                    self.root_causes["Element Timing Issues"] += count

                # Check for network issues
                elif any(re.search(pattern, error, re.I) for pattern in self.NETWORK_PATTERNS):
                    self.root_causes["Network Issues"] += count

                # Check for state issues
                elif any(re.search(pattern, error, re.I) for pattern in self.STATE_PATTERNS):
                    self.root_causes["State Management Issues"] += count

                # Check for race conditions
                elif any(re.search(pattern, error, re.I) for pattern in self.RACE_PATTERNS):
                    self.root_causes["Race Conditions"] += count

                else:
                    self.root_causes["Other"] += count

    def _calculate_overall_flake_rate(self) -> float:
        """Calculate overall flake rate across all tests."""
        if not self.flaky_tests:
            return 0.0

        total_runs = sum(t.total_runs for t in self.flaky_tests)
        total_failures = sum(t.fail_count for t in self.flaky_tests)

        return (total_failures / total_runs) if total_runs > 0 else 0.0

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Timeout issues
        if self.root_causes.get("Timeout/Wait Issues", 0) > 0:
            recommendations.append(
                "Increase test timeouts and use explicit waits instead of implicit waits. "
                "Replace sleep() calls with waitForSelector() or waitForCondition()."
            )

        # Timing issues
        if self.root_causes.get("Element Timing Issues", 0) > 0:
            recommendations.append(
                "Use auto-waiting features (Playwright) or implement proper wait strategies. "
                "Ensure elements are visible and stable before interaction."
            )

        # Network issues
        if self.root_causes.get("Network Issues", 0) > 0:
            recommendations.append(
                "Add retry logic for network requests. Consider mocking external APIs. "
                "Use network idle waits for dynamic content loading."
            )

        # State issues
        if self.root_causes.get("State Management Issues", 0) > 0:
            recommendations.append(
                "Ensure proper test isolation. Reset application state between tests. "
                "Use fresh browser contexts for each test."
            )

        # Race conditions
        if self.root_causes.get("Race Conditions", 0) > 0:
            recommendations.append(
                "Avoid parallel state mutations. Use proper synchronization primitives. "
                "Ensure tests don't share mutable state."
            )

        # High flake rate
        if self.flaky_tests and any(t.flake_rate > 0.5 for t in self.flaky_tests):
            recommendations.append(
                "Consider rewriting highly flaky tests (>50% failure rate) or converting "
                "them to integration/unit tests with mocked dependencies."
            )

        # Browser-specific issues
        multi_browser_flaky = [t for t in self.flaky_tests if len(t.browsers_affected) > 1]
        if multi_browser_flaky:
            recommendations.append(
                f"{len(multi_browser_flaky)} tests fail across multiple browsers. "
                "This suggests timing or environment issues rather than browser-specific bugs."
            )

        return recommendations

    def generate_report(self, report: FlakinesReport):
        """Generate and output report."""
        if self.config.json_output:
            self._output_json_report(report)
        else:
            self._output_human_report(report)

    def _output_json_report(self, report: FlakinesReport):
        """Output JSON report."""
        data = {
            "summary": {
                "total_tests": report.total_tests,
                "flaky_tests": report.flaky_tests,
                "stable_tests": report.stable_tests,
                "overall_flake_rate": report.overall_flake_rate,
                "analysis_period": report.analysis_period
            },
            "flaky_tests": [
                {
                    "name": t.name,
                    "total_runs": t.total_runs,
                    "pass_count": t.pass_count,
                    "fail_count": t.fail_count,
                    "flake_rate": t.flake_rate,
                    "avg_duration": t.avg_duration,
                    "severity": t.severity,
                    "browsers_affected": list(t.browsers_affected),
                    "common_errors": [{"error": e, "count": c} for e, c in t.common_errors]
                }
                for t in report.tests
            ],
            "root_causes": report.root_causes,
            "recommendations": report.recommendations
        }

        print(json.dumps(data, indent=2))

    def _output_human_report(self, report: FlakinesReport):
        """Output human-readable report."""
        print("\n" + "=" * 70)
        print("E2E Test Flakiness Analysis")
        print("=" * 70)

        print(f"\nAnalysis Period: {report.analysis_period}")
        print(f"\nSummary:")
        print(f"  Total Tests:      {report.total_tests}")
        print(f"  Flaky Tests:      {report.flaky_tests} (\033[1;33m⚠\033[0m)")
        print(f"  Stable Tests:     {report.stable_tests} (\033[0;32m✓\033[0m)")
        print(f"  Overall Flake Rate: {report.overall_flake_rate:.1%}")

        # Root causes
        if report.root_causes:
            print("\nRoot Causes:")
            for cause, count in sorted(report.root_causes.items(), key=lambda x: x[1], reverse=True):
                print(f"  {cause}: {count} occurrences")

        # Top flaky tests
        if report.tests:
            print("\nTop Flaky Tests:")
            for i, test in enumerate(report.tests[:10], 1):
                severity_icon = {
                    "high": "\033[0;31m●\033[0m",
                    "medium": "\033[1;33m●\033[0m",
                    "low": "\033[0;34m●\033[0m"
                }[test.severity]

                print(f"\n{i}. {severity_icon} {test.name}")
                print(f"   Flake Rate: {test.flake_rate:.1%} ({test.fail_count}/{test.total_runs} runs)")
                print(f"   Severity: {test.severity}")
                print(f"   Browsers: {', '.join(test.browsers_affected)}")

                if test.common_errors and self.verbose:
                    print(f"   Common Errors:")
                    for error, count in test.common_errors:
                        if error:
                            error_preview = error[:80] + "..." if len(error) > 80 else error
                            print(f"     - {error_preview} ({count}x)")

        # Recommendations
        if report.recommendations:
            print("\n" + "=" * 70)
            print("Recommendations:")
            print("=" * 70)
            for i, rec in enumerate(report.recommendations, 1):
                print(f"\n{i}. {rec}")

        print("\n" + "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="E2E Test Flakiness Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze flakiness over last 7 days
  %(prog)s --results-dir test-results --days 7

  # Find tests with >20 percent failure rate
  analyze_flakiness.py --threshold 0.2

  # Require minimum 5 runs to consider test
  %(prog)s --min-runs 5

  # Verbose output with error details
  %(prog)s --verbose

  # Output as JSON
  %(prog)s --json
        """
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    parser.add_argument(
        "-r", "--results-dir",
        default="test-results",
        help="Directory containing test results (default: test-results)"
    )
    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.1,
        help="Flakiness threshold (0.0-1.0, default: 0.1 = 10 percent)"
    )
    parser.add_argument(
        "-m", "--min-runs",
        type=int,
        default=3,
        help="Minimum test runs to consider (default: 3)"
    )
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=30,
        help="Analysis period in days (default: 30)"
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output with error details"
    )

    args = parser.parse_args()

    analyzer = FlakinessAnalyzer(args)
    report = analyzer.analyze()
    analyzer.generate_report(report)


if __name__ == "__main__":
    main()
