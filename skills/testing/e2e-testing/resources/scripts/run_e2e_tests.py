#!/usr/bin/env python3
"""
E2E Test Runner

Orchestrates E2E test execution with Playwright/Cypress/Selenium, manages test
environments, generates reports, and provides detailed execution metrics.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shutil
import signal


VERSION = "1.0.0"


@dataclass
class TestResult:
    """Result of test execution."""
    name: str
    status: str  # passed, failed, skipped, flaky
    duration: float
    error: Optional[str] = None
    retry_count: int = 0
    browser: str = "chromium"
    screenshot: Optional[str] = None
    video: Optional[str] = None
    trace: Optional[str] = None


@dataclass
class TestSuiteResult:
    """Aggregated test suite results."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    flaky: int = 0
    duration: float = 0.0
    start_time: str = ""
    end_time: str = ""
    tests: List[TestResult] = field(default_factory=list)
    framework: str = "playwright"
    browsers: List[str] = field(default_factory=list)
    artifacts_dir: Optional[str] = None


class E2ETestRunner:
    """Execute and manage E2E tests."""

    def __init__(self, config: argparse.Namespace):
        self.config = config
        self.test_dir = Path(config.test_dir)
        self.output_dir = Path(config.output_dir)
        self.framework = config.framework
        self.browsers = config.browsers
        self.parallel = config.parallel
        self.retries = config.retries
        self.timeout = config.timeout
        self.headed = config.headed
        self.debug = config.debug
        self.verbose = config.verbose

        # Initialize results
        self.results = TestSuiteResult(
            framework=self.framework,
            browsers=self.browsers,
            start_time=datetime.now().isoformat()
        )

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir = self.output_dir / "artifacts"
        self.artifacts_dir.mkdir(exist_ok=True)
        self.results.artifacts_dir = str(self.artifacts_dir)

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

    def run(self) -> int:
        """Execute test suite and return exit code."""
        try:
            self.log(f"Starting E2E tests with {self.framework}")
            self.log(f"Test directory: {self.test_dir}")
            self.log(f"Browsers: {', '.join(self.browsers)}")

            # Validate environment
            self._validate_environment()

            # Start test environment if needed
            if self.config.start_env:
                self._start_environment()

            # Run tests
            start = time.time()

            if self.framework == "playwright":
                exit_code = self._run_playwright()
            elif self.framework == "cypress":
                exit_code = self._run_cypress()
            elif self.framework == "selenium":
                exit_code = self._run_selenium()
            else:
                raise ValueError(f"Unsupported framework: {self.framework}")

            self.results.duration = time.time() - start
            self.results.end_time = datetime.now().isoformat()

            # Parse results
            self._parse_results()

            # Generate report
            self._generate_report()

            # Cleanup
            if self.config.start_env and not self.config.keep_env:
                self._stop_environment()

            return exit_code

        except KeyboardInterrupt:
            self.log("Test execution interrupted", "WARNING")
            if self.config.start_env:
                self._stop_environment()
            return 130
        except Exception as e:
            self.log(f"Test execution failed: {e}", "ERROR")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return 1

    def _validate_environment(self):
        """Validate test environment and dependencies."""
        self.log("Validating environment...")

        # Check test directory exists
        if not self.test_dir.exists():
            raise FileNotFoundError(f"Test directory not found: {self.test_dir}")

        # Check framework installed
        if self.framework == "playwright":
            if not shutil.which("npx"):
                raise EnvironmentError("npx not found. Install Node.js and npm.")
            # Check if playwright is installed
            try:
                subprocess.run(
                    ["npx", "playwright", "--version"],
                    capture_output=True,
                    check=True
                )
            except subprocess.CalledProcessError:
                raise EnvironmentError("Playwright not installed. Run: npm install -D @playwright/test")

        elif self.framework == "cypress":
            if not shutil.which("npx"):
                raise EnvironmentError("npx not found. Install Node.js and npm.")
            # Check if cypress is installed
            cypress_bin = Path("node_modules/.bin/cypress")
            if not cypress_bin.exists():
                raise EnvironmentError("Cypress not installed. Run: npm install -D cypress")

        elif self.framework == "selenium":
            try:
                import selenium
            except ImportError:
                raise EnvironmentError("Selenium not installed. Run: pip install selenium")

        self.log("Environment validation passed", "SUCCESS")

    def _start_environment(self):
        """Start test environment (e.g., Docker containers)."""
        self.log("Starting test environment...")

        compose_file = self.config.compose_file
        if not compose_file or not Path(compose_file).exists():
            self.log("No Docker Compose file specified, skipping environment start", "WARNING")
            return

        try:
            subprocess.run(
                ["docker", "compose", "-f", compose_file, "up", "-d"],
                check=True,
                capture_output=not self.verbose
            )
            self.log("Test environment started", "SUCCESS")

            # Wait for services to be ready
            time.sleep(self.config.startup_wait)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to start test environment: {e}")

    def _stop_environment(self):
        """Stop test environment."""
        self.log("Stopping test environment...")

        compose_file = self.config.compose_file
        if not compose_file or not Path(compose_file).exists():
            return

        try:
            subprocess.run(
                ["docker", "compose", "-f", compose_file, "down"],
                check=True,
                capture_output=not self.verbose
            )
            self.log("Test environment stopped", "SUCCESS")
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to stop test environment: {e}", "WARNING")

    def _run_playwright(self) -> int:
        """Run Playwright tests."""
        self.log("Running Playwright tests...")

        cmd = ["npx", "playwright", "test"]

        # Add browsers
        for browser in self.browsers:
            cmd.extend(["--project", browser])

        # Add options
        if self.parallel:
            cmd.append("--workers=auto")
        else:
            cmd.append("--workers=1")

        if self.retries > 0:
            cmd.extend(["--retries", str(self.retries)])

        if self.timeout:
            cmd.extend(["--timeout", str(self.timeout * 1000)])

        if self.headed:
            cmd.append("--headed")

        if self.debug:
            cmd.append("--debug")

        if self.config.pattern:
            cmd.append(self.config.pattern)

        # Output configuration
        cmd.extend(["--reporter", f"json"])

        # Set environment variables
        env = os.environ.copy()
        env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(self.output_dir / "results.json")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.test_dir,
                env=env,
                capture_output=not self.verbose
            )
            return result.returncode
        except subprocess.CalledProcessError as e:
            return e.returncode

    def _run_cypress(self) -> int:
        """Run Cypress tests."""
        self.log("Running Cypress tests...")

        cmd = ["npx", "cypress", "run"]

        # Cypress only supports one browser at a time
        if self.browsers:
            cmd.extend(["--browser", self.browsers[0]])

        if self.headed:
            cmd.append("--headed")

        if self.config.pattern:
            cmd.extend(["--spec", self.config.pattern])

        # Parallel execution
        if self.parallel:
            cmd.append("--parallel")

        # Reporter
        cmd.extend(["--reporter", "json"])
        cmd.extend(["--reporter-options", f"output={self.output_dir}/results.json"])

        try:
            result = subprocess.run(
                cmd,
                cwd=self.test_dir,
                capture_output=not self.verbose
            )
            return result.returncode
        except subprocess.CalledProcessError as e:
            return e.returncode

    def _run_selenium(self) -> int:
        """Run Selenium tests with pytest."""
        self.log("Running Selenium tests...")

        cmd = ["pytest", str(self.test_dir)]

        # Add options
        if self.parallel:
            cmd.extend(["-n", "auto"])

        if self.verbose:
            cmd.append("-v")

        if self.config.pattern:
            cmd.extend(["-k", self.config.pattern])

        # JSON report
        cmd.extend(["--json-report", f"--json-report-file={self.output_dir}/results.json"])

        try:
            result = subprocess.run(cmd, capture_output=not self.verbose)
            return result.returncode
        except subprocess.CalledProcessError as e:
            return e.returncode

    def _parse_results(self):
        """Parse test results from framework output."""
        self.log("Parsing test results...")

        results_file = self.output_dir / "results.json"
        if not results_file.exists():
            self.log("No results file found", "WARNING")
            return

        try:
            with open(results_file) as f:
                data = json.load(f)

            if self.framework == "playwright":
                self._parse_playwright_results(data)
            elif self.framework == "cypress":
                self._parse_cypress_results(data)
            elif self.framework == "selenium":
                self._parse_selenium_results(data)

        except Exception as e:
            self.log(f"Failed to parse results: {e}", "ERROR")

    def _parse_playwright_results(self, data: Dict):
        """Parse Playwright JSON results."""
        for suite in data.get("suites", []):
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    status = test.get("status", "unknown")

                    # Map Playwright status to our format
                    if status == "expected":
                        status = "passed"
                    elif status == "unexpected":
                        status = "failed"
                    elif status == "flaky":
                        status = "flaky"

                    result = TestResult(
                        name=test.get("title", "Unknown"),
                        status=status,
                        duration=test.get("duration", 0) / 1000.0,
                        error=test.get("error", {}).get("message"),
                        browser=test.get("projectName", "chromium")
                    )

                    self.results.tests.append(result)
                    self.results.total += 1

                    if status == "passed":
                        self.results.passed += 1
                    elif status == "failed":
                        self.results.failed += 1
                    elif status == "skipped":
                        self.results.skipped += 1
                    elif status == "flaky":
                        self.results.flaky += 1

    def _parse_cypress_results(self, data: Dict):
        """Parse Cypress JSON results."""
        for run in data.get("runs", []):
            for spec in run.get("specs", []):
                for test in spec.get("tests", []):
                    status = "passed" if test.get("state") == "passed" else "failed"

                    result = TestResult(
                        name=test.get("title", ["Unknown"])[0],
                        status=status,
                        duration=test.get("duration", 0) / 1000.0,
                        error=test.get("displayError")
                    )

                    self.results.tests.append(result)
                    self.results.total += 1

                    if status == "passed":
                        self.results.passed += 1
                    else:
                        self.results.failed += 1

    def _parse_selenium_results(self, data: Dict):
        """Parse pytest JSON results."""
        for test in data.get("tests", []):
            outcome = test.get("outcome", "unknown")

            status_map = {
                "passed": "passed",
                "failed": "failed",
                "skipped": "skipped",
                "xfailed": "skipped",
                "xpassed": "passed"
            }
            status = status_map.get(outcome, "unknown")

            result = TestResult(
                name=test.get("nodeid", "Unknown"),
                status=status,
                duration=test.get("duration", 0),
                error=test.get("call", {}).get("longrepr")
            )

            self.results.tests.append(result)
            self.results.total += 1

            if status == "passed":
                self.results.passed += 1
            elif status == "failed":
                self.results.failed += 1
            elif status == "skipped":
                self.results.skipped += 1

    def _generate_report(self):
        """Generate test report."""
        if self.config.json_output:
            self._generate_json_report()
        else:
            self._generate_human_report()

    def _generate_json_report(self):
        """Generate JSON report."""
        report = {
            "framework": self.results.framework,
            "browsers": self.results.browsers,
            "start_time": self.results.start_time,
            "end_time": self.results.end_time,
            "duration": self.results.duration,
            "summary": {
                "total": self.results.total,
                "passed": self.results.passed,
                "failed": self.results.failed,
                "skipped": self.results.skipped,
                "flaky": self.results.flaky,
                "pass_rate": (self.results.passed / self.results.total * 100) if self.results.total > 0 else 0
            },
            "tests": [
                {
                    "name": t.name,
                    "status": t.status,
                    "duration": t.duration,
                    "error": t.error,
                    "browser": t.browser,
                    "retry_count": t.retry_count
                }
                for t in self.results.tests
            ],
            "artifacts_dir": self.results.artifacts_dir
        }

        print(json.dumps(report, indent=2))

    def _generate_human_report(self):
        """Generate human-readable report."""
        print("\n" + "=" * 70)
        print(f"E2E Test Results - {self.results.framework}")
        print("=" * 70)

        print(f"\nTest Suite Summary:")
        print(f"  Total Tests:  {self.results.total}")
        print(f"  Passed:       {self.results.passed} (\033[0;32m✓\033[0m)")
        print(f"  Failed:       {self.results.failed} (\033[0;31m✗\033[0m)")

        if self.results.skipped > 0:
            print(f"  Skipped:      {self.results.skipped}")
        if self.results.flaky > 0:
            print(f"  Flaky:        {self.results.flaky} (\033[1;33m⚠\033[0m)")

        pass_rate = (self.results.passed / self.results.total * 100) if self.results.total > 0 else 0
        print(f"  Pass Rate:    {pass_rate:.1f}%")
        print(f"  Duration:     {self.results.duration:.2f}s")

        print(f"\nBrowsers: {', '.join(self.results.browsers)}")
        print(f"Artifacts: {self.results.artifacts_dir}")

        # Failed tests
        if self.results.failed > 0:
            print("\n\033[0;31mFailed Tests:\033[0m")
            for test in self.results.tests:
                if test.status == "failed":
                    print(f"  ✗ {test.name}")
                    if test.error and self.verbose:
                        error_lines = test.error.split('\n')[:3]
                        for line in error_lines:
                            print(f"    {line}")

        # Flaky tests
        if self.results.flaky > 0:
            print("\n\033[1;33mFlaky Tests:\033[0m")
            for test in self.results.tests:
                if test.status == "flaky":
                    print(f"  ⚠ {test.name} (passed after {test.retry_count} retries)")

        print("\n" + "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="E2E Test Runner - Execute and manage E2E tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run Playwright tests across all browsers
  %(prog)s --framework playwright --browsers chromium firefox webkit

  # Run Cypress tests in headed mode
  %(prog)s --framework cypress --headed

  # Run specific test pattern
  %(prog)s --pattern "login*" --verbose

  # Run with test environment
  %(prog)s --start-env --compose-file docker-compose.test.yml

  # Run in parallel with retries
  %(prog)s --parallel --retries 2

  # Output as JSON
  %(prog)s --json
        """
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    # Test configuration
    parser.add_argument(
        "-d", "--test-dir",
        default="tests/e2e",
        help="Test directory (default: tests/e2e)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="test-results",
        help="Output directory for results (default: test-results)"
    )
    parser.add_argument(
        "-p", "--pattern",
        help="Test pattern to match (e.g., 'login*')"
    )

    # Framework selection
    parser.add_argument(
        "--framework",
        choices=["playwright", "cypress", "selenium"],
        default="playwright",
        help="E2E testing framework (default: playwright)"
    )

    # Browser configuration
    parser.add_argument(
        "--browsers",
        nargs="+",
        default=["chromium"],
        help="Browsers to test (default: chromium)"
    )

    # Execution options
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=0,
        help="Number of retries for failed tests (default: 0)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Test timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run in headed mode (show browser)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    # Environment management
    parser.add_argument(
        "--start-env",
        action="store_true",
        help="Start test environment before tests"
    )
    parser.add_argument(
        "--compose-file",
        help="Docker Compose file for test environment"
    )
    parser.add_argument(
        "--keep-env",
        action="store_true",
        help="Keep test environment running after tests"
    )
    parser.add_argument(
        "--startup-wait",
        type=int,
        default=5,
        help="Seconds to wait after starting environment (default: 5)"
    )

    # Output options
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    runner = E2ETestRunner(args)
    exit_code = runner.run()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
