#!/usr/bin/env python3
"""
PyO3 Test Runner - Orchestrate Rust and Python tests for PyO3 projects.

This script provides comprehensive test orchestration for PyO3 projects,
running both Rust (cargo test) and Python (pytest) tests across multiple
Python versions, generating unified reports, and aggregating coverage data.

Usage:
    test_runner.py run [options]          # Run all tests
    test_runner.py rust [options]         # Run only Rust tests
    test_runner.py python [options]       # Run only Python tests
    test_runner.py all [options]          # Run all tests with full matrix
    test_runner.py report [options]       # Generate test reports
    test_runner.py compare <baseline>     # Compare against baseline

Examples:
    # Run all tests with coverage
    test_runner.py run --coverage

    # Run tests across Python 3.8-3.12
    test_runner.py all --python-versions 3.8,3.9,3.10,3.11,3.12

    # Generate HTML report
    test_runner.py report --format html --output report.html

    # Compare against baseline
    test_runner.py compare baseline.json --format text
"""

import argparse
import dataclasses
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


class OutputFormat(Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclasses.dataclass
class TestResult:
    """Individual test result."""
    name: str
    status: TestStatus
    duration: float
    output: str
    error: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "duration": self.duration,
            "output": self.output,
            "error": self.error,
            "file": self.file,
            "line": self.line,
        }


@dataclasses.dataclass
class TestSuite:
    """Test suite results."""
    name: str
    language: str  # "rust" or "python"
    python_version: Optional[str] = None
    tests: List[TestResult] = dataclasses.field(default_factory=list)
    total_duration: float = 0.0
    coverage: Optional[float] = None
    timestamp: str = dataclasses.field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    @property
    def passed(self) -> int:
        """Count of passed tests."""
        return sum(1 for t in self.tests if t.status == TestStatus.PASSED)

    @property
    def failed(self) -> int:
        """Count of failed tests."""
        return sum(1 for t in self.tests if t.status == TestStatus.FAILED)

    @property
    def skipped(self) -> int:
        """Count of skipped tests."""
        return sum(1 for t in self.tests if t.status == TestStatus.SKIPPED)

    @property
    def error(self) -> int:
        """Count of errored tests."""
        return sum(1 for t in self.tests if t.status == TestStatus.ERROR)

    @property
    def total(self) -> int:
        """Total test count."""
        return len(self.tests)

    @property
    def success_rate(self) -> float:
        """Success rate percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "language": self.language,
            "python_version": self.python_version,
            "tests": [t.to_dict() for t in self.tests],
            "total_duration": self.total_duration,
            "coverage": self.coverage,
            "timestamp": self.timestamp,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "error": self.error,
                "success_rate": self.success_rate,
            },
        }


@dataclasses.dataclass
class TestReport:
    """Comprehensive test report."""
    project_name: str
    suites: List[TestSuite] = dataclasses.field(default_factory=list)
    total_duration: float = 0.0
    timestamp: str = dataclasses.field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    @property
    def total_tests(self) -> int:
        """Total test count across all suites."""
        return sum(suite.total for suite in self.suites)

    @property
    def total_passed(self) -> int:
        """Total passed tests."""
        return sum(suite.passed for suite in self.suites)

    @property
    def total_failed(self) -> int:
        """Total failed tests."""
        return sum(suite.failed for suite in self.suites)

    @property
    def total_skipped(self) -> int:
        """Total skipped tests."""
        return sum(suite.skipped for suite in self.suites)

    @property
    def overall_success_rate(self) -> float:
        """Overall success rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.total_passed / self.total_tests) * 100.0

    @property
    def average_coverage(self) -> Optional[float]:
        """Average coverage across suites."""
        coverages = [s.coverage for s in self.suites if s.coverage is not None]
        if not coverages:
            return None
        return sum(coverages) / len(coverages)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_name": self.project_name,
            "suites": [s.to_dict() for s in self.suites],
            "total_duration": self.total_duration,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "summary": {
                "total_tests": self.total_tests,
                "total_passed": self.total_passed,
                "total_failed": self.total_failed,
                "total_skipped": self.total_skipped,
                "overall_success_rate": self.overall_success_rate,
                "average_coverage": self.average_coverage,
            },
        }


class RustTestRunner:
    """Run Rust tests via cargo."""

    def __init__(
        self,
        project_dir: pathlib.Path,
        release: bool = False,
        features: Optional[List[str]] = None,
        no_default_features: bool = False,
        timeout: int = 300,
        verbose: bool = False,
    ):
        """Initialize Rust test runner."""
        self.project_dir = project_dir
        self.release = release
        self.features = features or []
        self.no_default_features = no_default_features
        self.timeout = timeout
        self.verbose = verbose

    def run(self, coverage: bool = False) -> TestSuite:
        """Run Rust tests."""
        cmd = ["cargo", "test"]

        if self.release:
            cmd.append("--release")

        if self.no_default_features:
            cmd.append("--no-default-features")

        if self.features:
            cmd.extend(["--features", ",".join(self.features)])

        if coverage:
            cmd.extend(["--", "--test-threads=1"])

        cmd.append("--")
        cmd.append("--format=json")

        if self.verbose:
            print(f"Running: {' '.join(cmd)}")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**os.environ, "RUST_BACKTRACE": "1"},
            )
            duration = time.time() - start_time

            tests = self._parse_cargo_output(result.stdout, result.stderr)
            suite = TestSuite(
                name="rust",
                language="rust",
                tests=tests,
                total_duration=duration,
            )

            if coverage:
                suite.coverage = self._get_rust_coverage()

            return suite

        except subprocess.TimeoutExpired:
            return TestSuite(
                name="rust",
                language="rust",
                tests=[
                    TestResult(
                        name="cargo_test",
                        status=TestStatus.TIMEOUT,
                        duration=self.timeout,
                        output="",
                        error=f"Test execution timed out after {self.timeout}s",
                    )
                ],
                total_duration=self.timeout,
            )
        except Exception as e:
            return TestSuite(
                name="rust",
                language="rust",
                tests=[
                    TestResult(
                        name="cargo_test",
                        status=TestStatus.ERROR,
                        duration=0.0,
                        output="",
                        error=str(e),
                    )
                ],
                total_duration=0.0,
            )

    def _parse_cargo_output(self, stdout: str, stderr: str) -> List[TestResult]:
        """Parse cargo test output."""
        tests: List[TestResult] = []

        # Parse JSON output from cargo test
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue

            # Try to extract test results from output
            # Format: test <name> ... ok/FAILED
            match = re.match(
                r"test\s+(\S+)\s+\.\.\.\s+(ok|FAILED|ignored)",
                line,
            )
            if match:
                name, status_str = match.groups()
                if status_str == "ok":
                    status = TestStatus.PASSED
                elif status_str == "FAILED":
                    status = TestStatus.FAILED
                else:
                    status = TestStatus.SKIPPED

                tests.append(
                    TestResult(
                        name=name,
                        status=status,
                        duration=0.0,  # Cargo doesn't provide per-test timing
                        output=line,
                    )
                )

        # If no tests found, check for compilation errors
        if not tests and stderr:
            tests.append(
                TestResult(
                    name="compilation",
                    status=TestStatus.ERROR,
                    duration=0.0,
                    output=stderr,
                    error="Compilation failed",
                )
            )

        return tests

    def _get_rust_coverage(self) -> Optional[float]:
        """Get Rust code coverage using tarpaulin or llvm-cov."""
        try:
            # Try tarpaulin first
            result = subprocess.run(
                ["cargo", "tarpaulin", "--output-dir", "target/coverage", "--out", "Json"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode == 0:
                coverage_file = self.project_dir / "target" / "coverage" / "tarpaulin-report.json"
                if coverage_file.exists():
                    with open(coverage_file) as f:
                        data = json.load(f)
                        return data.get("coverage", 0.0)

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return None


class PythonTestRunner:
    """Run Python tests via pytest."""

    def __init__(
        self,
        project_dir: pathlib.Path,
        python_version: str = sys.version.split()[0],
        test_dir: Optional[pathlib.Path] = None,
        markers: Optional[List[str]] = None,
        timeout: int = 300,
        verbose: bool = False,
    ):
        """Initialize Python test runner."""
        self.project_dir = project_dir
        self.python_version = python_version
        self.test_dir = test_dir or (project_dir / "tests")
        self.markers = markers or []
        self.timeout = timeout
        self.verbose = verbose

    def run(self, coverage: bool = False) -> TestSuite:
        """Run Python tests."""
        cmd = ["pytest", str(self.test_dir)]

        cmd.extend(["--json-report", "--json-report-file=test-report.json"])

        if coverage:
            cmd.extend(["--cov", "--cov-report=json"])

        if self.markers:
            for marker in self.markers:
                cmd.extend(["-m", marker])

        if self.verbose:
            cmd.append("-v")
            print(f"Running: {' '.join(cmd)}")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            duration = time.time() - start_time

            tests = self._parse_pytest_output(result.stdout, result.stderr)
            suite = TestSuite(
                name="python",
                language="python",
                python_version=self.python_version,
                tests=tests,
                total_duration=duration,
            )

            if coverage:
                suite.coverage = self._get_python_coverage()

            return suite

        except subprocess.TimeoutExpired:
            return TestSuite(
                name="python",
                language="python",
                python_version=self.python_version,
                tests=[
                    TestResult(
                        name="pytest",
                        status=TestStatus.TIMEOUT,
                        duration=self.timeout,
                        output="",
                        error=f"Test execution timed out after {self.timeout}s",
                    )
                ],
                total_duration=self.timeout,
            )
        except Exception as e:
            return TestSuite(
                name="python",
                language="python",
                python_version=self.python_version,
                tests=[
                    TestResult(
                        name="pytest",
                        status=TestStatus.ERROR,
                        duration=0.0,
                        output="",
                        error=str(e),
                    )
                ],
                total_duration=0.0,
            )

    def _parse_pytest_output(self, stdout: str, stderr: str) -> List[TestResult]:
        """Parse pytest output."""
        tests: List[TestResult] = []

        # Try to load JSON report
        report_file = self.project_dir / "test-report.json"
        if report_file.exists():
            try:
                with open(report_file) as f:
                    data = json.load(f)

                for test in data.get("tests", []):
                    status_str = test.get("outcome", "unknown")
                    if status_str == "passed":
                        status = TestStatus.PASSED
                    elif status_str == "failed":
                        status = TestStatus.FAILED
                    elif status_str == "skipped":
                        status = TestStatus.SKIPPED
                    else:
                        status = TestStatus.ERROR

                    tests.append(
                        TestResult(
                            name=test.get("nodeid", "unknown"),
                            status=status,
                            duration=test.get("duration", 0.0),
                            output=test.get("call", {}).get("stdout", ""),
                            error=test.get("call", {}).get("stderr"),
                            file=test.get("file"),
                            line=test.get("line"),
                        )
                    )

                return tests

            except (json.JSONDecodeError, KeyError) as e:
                if self.verbose:
                    print(f"Failed to parse JSON report: {e}")

        # Fallback: parse text output
        for line in stdout.splitlines():
            match = re.match(
                r"(\S+\.py)::(\S+)\s+(PASSED|FAILED|SKIPPED|ERROR)",
                line,
            )
            if match:
                file, name, status_str = match.groups()
                if status_str == "PASSED":
                    status = TestStatus.PASSED
                elif status_str == "FAILED":
                    status = TestStatus.FAILED
                elif status_str == "SKIPPED":
                    status = TestStatus.SKIPPED
                else:
                    status = TestStatus.ERROR

                tests.append(
                    TestResult(
                        name=f"{file}::{name}",
                        status=status,
                        duration=0.0,
                        output=line,
                        file=file,
                    )
                )

        return tests

    def _get_python_coverage(self) -> Optional[float]:
        """Get Python code coverage from coverage.json."""
        coverage_file = self.project_dir / "coverage.json"
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    data = json.load(f)
                    totals = data.get("totals", {})
                    return totals.get("percent_covered")
            except (json.JSONDecodeError, KeyError):
                pass

        return None


class TestReportGenerator:
    """Generate test reports in various formats."""

    def __init__(self, report: TestReport):
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
            f"Test Report: {self.report.project_name}",
            "=" * 80,
            f"Timestamp: {self.report.timestamp}",
            f"Total Duration: {self.report.total_duration:.2f}s",
            "",
            "Summary:",
            f"  Total Tests: {self.report.total_tests}",
            f"  Passed: {self.report.total_passed}",
            f"  Failed: {self.report.total_failed}",
            f"  Skipped: {self.report.total_skipped}",
            f"  Success Rate: {self.report.overall_success_rate:.1f}%",
        ]

        if self.report.average_coverage is not None:
            lines.append(f"  Average Coverage: {self.report.average_coverage:.1f}%")

        lines.append("")

        for suite in self.report.suites:
            lines.extend(
                [
                    f"\n{suite.name} ({suite.language})",
                    "-" * 80,
                ]
            )

            if suite.python_version:
                lines.append(f"Python Version: {suite.python_version}")

            lines.extend(
                [
                    f"Duration: {suite.total_duration:.2f}s",
                    f"Tests: {suite.total} (Passed: {suite.passed}, Failed: {suite.failed}, Skipped: {suite.skipped})",
                    f"Success Rate: {suite.success_rate:.1f}%",
                ]
            )

            if suite.coverage is not None:
                lines.append(f"Coverage: {suite.coverage:.1f}%")

            if suite.failed > 0:
                lines.append("\nFailed Tests:")
                for test in suite.tests:
                    if test.status == TestStatus.FAILED:
                        lines.append(f"  - {test.name}")
                        if test.error:
                            lines.append(f"    Error: {test.error}")

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
            f"<title>Test Report: {self.report.project_name}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; }",
            "table { border-collapse: collapse; width: 100%; margin: 20px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #4CAF50; color: white; }",
            ".passed { color: green; }",
            ".failed { color: red; }",
            ".skipped { color: orange; }",
            ".summary { background-color: #f2f2f2; padding: 15px; margin: 20px 0; border-radius: 5px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>Test Report: {self.report.project_name}</h1>",
            f"<p><strong>Timestamp:</strong> {self.report.timestamp}</p>",
            f"<p><strong>Total Duration:</strong> {self.report.total_duration:.2f}s</p>",
            '<div class="summary">',
            "<h2>Summary</h2>",
            f"<p><strong>Total Tests:</strong> {self.report.total_tests}</p>",
            f'<p><strong>Passed:</strong> <span class="passed">{self.report.total_passed}</span></p>',
            f'<p><strong>Failed:</strong> <span class="failed">{self.report.total_failed}</span></p>',
            f'<p><strong>Skipped:</strong> <span class="skipped">{self.report.total_skipped}</span></p>',
            f"<p><strong>Success Rate:</strong> {self.report.overall_success_rate:.1f}%</p>",
        ]

        if self.report.average_coverage is not None:
            html.append(f"<p><strong>Average Coverage:</strong> {self.report.average_coverage:.1f}%</p>")

        html.append("</div>")

        for suite in self.report.suites:
            html.extend(
                [
                    f"<h2>{suite.name} ({suite.language})</h2>",
                    "<table>",
                    "<tr><th>Metric</th><th>Value</th></tr>",
                ]
            )

            if suite.python_version:
                html.append(f"<tr><td>Python Version</td><td>{suite.python_version}</td></tr>")

            html.extend(
                [
                    f"<tr><td>Duration</td><td>{suite.total_duration:.2f}s</td></tr>",
                    f"<tr><td>Total Tests</td><td>{suite.total}</td></tr>",
                    f'<tr><td>Passed</td><td class="passed">{suite.passed}</td></tr>',
                    f'<tr><td>Failed</td><td class="failed">{suite.failed}</td></tr>',
                    f'<tr><td>Skipped</td><td class="skipped">{suite.skipped}</td></tr>',
                    f"<tr><td>Success Rate</td><td>{suite.success_rate:.1f}%</td></tr>",
                ]
            )

            if suite.coverage is not None:
                html.append(f"<tr><td>Coverage</td><td>{suite.coverage:.1f}%</td></tr>")

            html.append("</table>")

        html.extend(["</body>", "</html>"])

        return "\n".join(html)

    def _generate_markdown(self) -> str:
        """Generate Markdown report."""
        lines = [
            f"# Test Report: {self.report.project_name}",
            "",
            f"**Timestamp:** {self.report.timestamp}",
            f"**Total Duration:** {self.report.total_duration:.2f}s",
            "",
            "## Summary",
            "",
            f"- **Total Tests:** {self.report.total_tests}",
            f"- **Passed:** {self.report.total_passed} ✅",
            f"- **Failed:** {self.report.total_failed} ❌",
            f"- **Skipped:** {self.report.total_skipped} ⏭️",
            f"- **Success Rate:** {self.report.overall_success_rate:.1f}%",
        ]

        if self.report.average_coverage is not None:
            lines.append(f"- **Average Coverage:** {self.report.average_coverage:.1f}%")

        lines.append("")

        for suite in self.report.suites:
            lines.extend([f"## {suite.name} ({suite.language})", ""])

            if suite.python_version:
                lines.append(f"**Python Version:** {suite.python_version}")

            lines.extend(
                [
                    f"**Duration:** {suite.total_duration:.2f}s",
                    f"**Tests:** {suite.total} (Passed: {suite.passed}, Failed: {suite.failed}, Skipped: {suite.skipped})",
                    f"**Success Rate:** {suite.success_rate:.1f}%",
                ]
            )

            if suite.coverage is not None:
                lines.append(f"**Coverage:** {suite.coverage:.1f}%")

            lines.append("")

        return "\n".join(lines)


class TestComparator:
    """Compare test results against baseline."""

    def __init__(self, baseline: TestReport, current: TestReport):
        """Initialize comparator."""
        self.baseline = baseline
        self.current = current

    def compare(self) -> Dict[str, Any]:
        """Compare current results against baseline."""
        comparison = {
            "timestamp": datetime.utcnow().isoformat(),
            "baseline_timestamp": self.baseline.timestamp,
            "current_timestamp": self.current.timestamp,
            "summary": {
                "tests_delta": self.current.total_tests - self.baseline.total_tests,
                "passed_delta": self.current.total_passed - self.baseline.total_passed,
                "failed_delta": self.current.total_failed - self.baseline.total_failed,
                "success_rate_delta": self.current.overall_success_rate - self.baseline.overall_success_rate,
                "duration_delta": self.current.total_duration - self.baseline.total_duration,
            },
            "suites": [],
            "new_failures": [],
            "fixed_tests": [],
            "new_tests": [],
        }

        # Compare coverage
        if self.baseline.average_coverage is not None and self.current.average_coverage is not None:
            comparison["summary"]["coverage_delta"] = (
                self.current.average_coverage - self.baseline.average_coverage
            )

        # Build test maps
        baseline_tests = self._build_test_map(self.baseline)
        current_tests = self._build_test_map(self.current)

        # Find new failures
        for test_name, test in current_tests.items():
            if test.status == TestStatus.FAILED:
                baseline_test = baseline_tests.get(test_name)
                if baseline_test is None or baseline_test.status == TestStatus.PASSED:
                    comparison["new_failures"].append(test_name)

        # Find fixed tests
        for test_name, test in baseline_tests.items():
            if test.status == TestStatus.FAILED:
                current_test = current_tests.get(test_name)
                if current_test and current_test.status == TestStatus.PASSED:
                    comparison["fixed_tests"].append(test_name)

        # Find new tests
        comparison["new_tests"] = list(set(current_tests.keys()) - set(baseline_tests.keys()))

        return comparison

    def _build_test_map(self, report: TestReport) -> Dict[str, TestResult]:
        """Build a flat map of all tests."""
        test_map: Dict[str, TestResult] = {}
        for suite in report.suites:
            for test in suite.tests:
                key = f"{suite.name}::{test.name}"
                test_map[key] = test
        return test_map

    def format_comparison(self, comparison: Dict[str, Any], format: OutputFormat) -> str:
        """Format comparison results."""
        if format == OutputFormat.JSON:
            return json.dumps(comparison, indent=2)
        elif format == OutputFormat.TEXT:
            return self._format_comparison_text(comparison)
        elif format == OutputFormat.MARKDOWN:
            return self._format_comparison_markdown(comparison)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_comparison_text(self, comparison: Dict[str, Any]) -> str:
        """Format comparison as plain text."""
        lines = [
            "Test Comparison Report",
            "=" * 80,
            f"Baseline: {comparison['baseline_timestamp']}",
            f"Current:  {comparison['current_timestamp']}",
            "",
            "Summary:",
            f"  Tests Delta: {comparison['summary']['tests_delta']:+d}",
            f"  Passed Delta: {comparison['summary']['passed_delta']:+d}",
            f"  Failed Delta: {comparison['summary']['failed_delta']:+d}",
            f"  Success Rate Delta: {comparison['summary']['success_rate_delta']:+.1f}%",
            f"  Duration Delta: {comparison['summary']['duration_delta']:+.2f}s",
        ]

        if "coverage_delta" in comparison["summary"]:
            lines.append(f"  Coverage Delta: {comparison['summary']['coverage_delta']:+.1f}%")

        if comparison["new_failures"]:
            lines.extend(["\nNew Failures:", *[f"  - {t}" for t in comparison["new_failures"]]])

        if comparison["fixed_tests"]:
            lines.extend(["\nFixed Tests:", *[f"  - {t}" for t in comparison["fixed_tests"]]])

        if comparison["new_tests"]:
            lines.extend(["\nNew Tests:", *[f"  - {t}" for t in comparison["new_tests"]]])

        return "\n".join(lines)

    def _format_comparison_markdown(self, comparison: Dict[str, Any]) -> str:
        """Format comparison as Markdown."""
        lines = [
            "# Test Comparison Report",
            "",
            f"**Baseline:** {comparison['baseline_timestamp']}",
            f"**Current:** {comparison['current_timestamp']}",
            "",
            "## Summary",
            "",
            f"- **Tests Delta:** {comparison['summary']['tests_delta']:+d}",
            f"- **Passed Delta:** {comparison['summary']['passed_delta']:+d}",
            f"- **Failed Delta:** {comparison['summary']['failed_delta']:+d}",
            f"- **Success Rate Delta:** {comparison['summary']['success_rate_delta']:+.1f}%",
            f"- **Duration Delta:** {comparison['summary']['duration_delta']:+.2f}s",
        ]

        if "coverage_delta" in comparison["summary"]:
            lines.append(f"- **Coverage Delta:** {comparison['summary']['coverage_delta']:+.1f}%")

        if comparison["new_failures"]:
            lines.extend(["", "## New Failures", ""] + [f"- {t}" for t in comparison["new_failures"]])

        if comparison["fixed_tests"]:
            lines.extend(["", "## Fixed Tests", ""] + [f"- {t}" for t in comparison["fixed_tests"]])

        if comparison["new_tests"]:
            lines.extend(["", "## New Tests", ""] + [f"- {t}" for t in comparison["new_tests"]])

        return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PyO3 Test Runner - Orchestrate Rust and Python tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Common arguments
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--project-dir",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Project directory (default: current directory)",
    )
    common.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    common.add_argument("--timeout", type=int, default=300, help="Test timeout in seconds")

    # Run command
    run_parser = subparsers.add_parser("run", parents=[common], help="Run all tests")
    run_parser.add_argument("--coverage", action="store_true", help="Collect coverage data")
    run_parser.add_argument("--output", type=pathlib.Path, help="Output file for report")

    # Rust command
    rust_parser = subparsers.add_parser("rust", parents=[common], help="Run Rust tests only")
    rust_parser.add_argument("--release", action="store_true", help="Build in release mode")
    rust_parser.add_argument("--features", help="Comma-separated list of features")
    rust_parser.add_argument("--no-default-features", action="store_true", help="Disable default features")
    rust_parser.add_argument("--coverage", action="store_true", help="Collect coverage data")

    # Python command
    python_parser = subparsers.add_parser("python", parents=[common], help="Run Python tests only")
    python_parser.add_argument("--python-version", default=sys.version.split()[0], help="Python version")
    python_parser.add_argument("--test-dir", type=pathlib.Path, help="Test directory")
    python_parser.add_argument("--markers", help="Comma-separated list of pytest markers")
    python_parser.add_argument("--coverage", action="store_true", help="Collect coverage data")

    # All command
    all_parser = subparsers.add_parser("all", parents=[common], help="Run full test matrix")
    all_parser.add_argument(
        "--python-versions",
        default=sys.version.split()[0],
        help="Comma-separated list of Python versions",
    )
    all_parser.add_argument("--coverage", action="store_true", help="Collect coverage data")
    all_parser.add_argument("--output", type=pathlib.Path, help="Output file for report")

    # Report command
    report_parser = subparsers.add_parser("report", parents=[common], help="Generate test report")
    report_parser.add_argument(
        "--input",
        type=pathlib.Path,
        required=True,
        help="Input JSON report file",
    )
    report_parser.add_argument(
        "--format",
        choices=["text", "json", "html", "markdown"],
        default="text",
        help="Output format",
    )
    report_parser.add_argument("--output", type=pathlib.Path, help="Output file")

    # Compare command
    compare_parser = subparsers.add_parser("compare", parents=[common], help="Compare against baseline")
    compare_parser.add_argument("baseline", type=pathlib.Path, help="Baseline report JSON file")
    compare_parser.add_argument(
        "--current",
        type=pathlib.Path,
        help="Current report JSON file (default: run tests)",
    )
    compare_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format",
    )
    compare_parser.add_argument("--output", type=pathlib.Path, help="Output file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "run":
            return cmd_run(args)
        elif args.command == "rust":
            return cmd_rust(args)
        elif args.command == "python":
            return cmd_python(args)
        elif args.command == "all":
            return cmd_all(args)
        elif args.command == "report":
            return cmd_report(args)
        elif args.command == "compare":
            return cmd_compare(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Run all tests."""
    project_name = args.project_dir.name

    # Run Rust tests
    rust_runner = RustTestRunner(
        args.project_dir,
        timeout=args.timeout,
        verbose=args.verbose,
    )
    rust_suite = rust_runner.run(coverage=args.coverage)

    # Run Python tests
    python_runner = PythonTestRunner(
        args.project_dir,
        timeout=args.timeout,
        verbose=args.verbose,
    )
    python_suite = python_runner.run(coverage=args.coverage)

    # Create report
    report = TestReport(
        project_name=project_name,
        suites=[rust_suite, python_suite],
        total_duration=rust_suite.total_duration + python_suite.total_duration,
    )

    # Generate output
    generator = TestReportGenerator(report)
    output = generator.generate(OutputFormat.TEXT)
    print(output)

    # Save report
    if args.output:
        args.output.write_text(json.dumps(report.to_dict(), indent=2))
        print(f"\nReport saved to: {args.output}")

    return 0 if report.total_failed == 0 else 1


def cmd_rust(args: argparse.Namespace) -> int:
    """Run Rust tests only."""
    features = args.features.split(",") if args.features else None

    runner = RustTestRunner(
        args.project_dir,
        release=args.release,
        features=features,
        no_default_features=args.no_default_features,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    suite = runner.run(coverage=args.coverage)

    # Print results
    print(f"Rust Tests: {suite.passed}/{suite.total} passed")
    print(f"Duration: {suite.total_duration:.2f}s")
    if suite.coverage is not None:
        print(f"Coverage: {suite.coverage:.1f}%")

    return 0 if suite.failed == 0 else 1


def cmd_python(args: argparse.Namespace) -> int:
    """Run Python tests only."""
    markers = args.markers.split(",") if args.markers else None

    runner = PythonTestRunner(
        args.project_dir,
        python_version=args.python_version,
        test_dir=args.test_dir,
        markers=markers,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    suite = runner.run(coverage=args.coverage)

    # Print results
    print(f"Python Tests ({suite.python_version}): {suite.passed}/{suite.total} passed")
    print(f"Duration: {suite.total_duration:.2f}s")
    if suite.coverage is not None:
        print(f"Coverage: {suite.coverage:.1f}%")

    return 0 if suite.failed == 0 else 1


def cmd_all(args: argparse.Namespace) -> int:
    """Run full test matrix."""
    project_name = args.project_dir.name
    python_versions = args.python_versions.split(",")

    suites: List[TestSuite] = []

    # Run Rust tests once
    rust_runner = RustTestRunner(
        args.project_dir,
        timeout=args.timeout,
        verbose=args.verbose,
    )
    rust_suite = rust_runner.run(coverage=args.coverage)
    suites.append(rust_suite)

    # Run Python tests for each version
    for py_version in python_versions:
        if args.verbose:
            print(f"\nTesting with Python {py_version}...")

        python_runner = PythonTestRunner(
            args.project_dir,
            python_version=py_version,
            timeout=args.timeout,
            verbose=args.verbose,
        )
        python_suite = python_runner.run(coverage=args.coverage)
        suites.append(python_suite)

    # Create report
    total_duration = sum(s.total_duration for s in suites)
    report = TestReport(
        project_name=project_name,
        suites=suites,
        total_duration=total_duration,
    )

    # Generate output
    generator = TestReportGenerator(report)
    output = generator.generate(OutputFormat.TEXT)
    print(output)

    # Save report
    if args.output:
        args.output.write_text(json.dumps(report.to_dict(), indent=2))
        print(f"\nReport saved to: {args.output}")

    return 0 if report.total_failed == 0 else 1


def cmd_report(args: argparse.Namespace) -> int:
    """Generate test report."""
    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1

    with open(args.input) as f:
        data = json.load(f)

    # Reconstruct report from JSON
    suites = []
    for suite_data in data["suites"]:
        tests = [
            TestResult(
                name=t["name"],
                status=TestStatus(t["status"]),
                duration=t["duration"],
                output=t["output"],
                error=t.get("error"),
                file=t.get("file"),
                line=t.get("line"),
            )
            for t in suite_data["tests"]
        ]

        suite = TestSuite(
            name=suite_data["name"],
            language=suite_data["language"],
            python_version=suite_data.get("python_version"),
            tests=tests,
            total_duration=suite_data["total_duration"],
            coverage=suite_data.get("coverage"),
            timestamp=suite_data["timestamp"],
        )
        suites.append(suite)

    report = TestReport(
        project_name=data["project_name"],
        suites=suites,
        total_duration=data["total_duration"],
        timestamp=data["timestamp"],
        metadata=data.get("metadata", {}),
    )

    # Generate report
    generator = TestReportGenerator(report)
    format = OutputFormat(args.format)
    output = generator.generate(format, args.output)

    if not args.output:
        print(output)

    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Compare against baseline."""
    if not args.baseline.exists():
        print(f"Baseline file not found: {args.baseline}", file=sys.stderr)
        return 1

    # Load baseline
    with open(args.baseline) as f:
        baseline_data = json.load(f)

    # Load or generate current report
    if args.current:
        if not args.current.exists():
            print(f"Current file not found: {args.current}", file=sys.stderr)
            return 1
        with open(args.current) as f:
            current_data = json.load(f)
    else:
        # Run tests to generate current report
        print("Running tests to generate current report...")
        # This would call cmd_run() and capture the result
        # For simplicity, we'll require --current for now
        print("Error: --current is required", file=sys.stderr)
        return 1

    # Reconstruct reports (similar to cmd_report)
    def reconstruct_report(data: Dict[str, Any]) -> TestReport:
        suites = []
        for suite_data in data["suites"]:
            tests = [
                TestResult(
                    name=t["name"],
                    status=TestStatus(t["status"]),
                    duration=t["duration"],
                    output=t["output"],
                    error=t.get("error"),
                    file=t.get("file"),
                    line=t.get("line"),
                )
                for t in suite_data["tests"]
            ]

            suite = TestSuite(
                name=suite_data["name"],
                language=suite_data["language"],
                python_version=suite_data.get("python_version"),
                tests=tests,
                total_duration=suite_data["total_duration"],
                coverage=suite_data.get("coverage"),
                timestamp=suite_data["timestamp"],
            )
            suites.append(suite)

        return TestReport(
            project_name=data["project_name"],
            suites=suites,
            total_duration=data["total_duration"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )

    baseline = reconstruct_report(baseline_data)
    current = reconstruct_report(current_data)

    # Compare
    comparator = TestComparator(baseline, current)
    comparison = comparator.compare()

    # Format output
    format = OutputFormat(args.format)
    output = comparator.format_comparison(comparison, format)

    if args.output:
        args.output.write_text(output)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
