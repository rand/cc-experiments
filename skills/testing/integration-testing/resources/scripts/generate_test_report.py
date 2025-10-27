#!/usr/bin/env python3
"""
Integration Test Report Generator

Generates comprehensive HTML/JSON reports from integration test results,
including test execution details, coverage analysis, and failure diagnostics.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET


VERSION = "1.0.0"


class TestResult:
    """Represents a single test result."""

    def __init__(
        self,
        name: str,
        status: str,
        duration: float,
        message: Optional[str] = None,
        file: Optional[str] = None,
        line: Optional[int] = None,
    ):
        self.name = name
        self.status = status  # passed, failed, skipped, error
        self.duration = duration
        self.message = message
        self.file = file
        self.line = line


class TestSuite:
    """Represents a test suite with multiple tests."""

    def __init__(self, name: str):
        self.name = name
        self.tests: List[TestResult] = []
        self.duration = 0.0

    def add_test(self, test: TestResult):
        self.tests.append(test)
        self.duration += test.duration

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.status == "passed")

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if t.status == "failed")

    @property
    def skipped(self) -> int:
        return sum(1 for t in self.tests if t.status == "skipped")

    @property
    def errors(self) -> int:
        return sum(1 for t in self.tests if t.status == "error")

    @property
    def total(self) -> int:
        return len(self.tests)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100


class ReportGenerator:
    """Generates test reports from various test result formats."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.suites: List[TestSuite] = []

    def log(self, message: str):
        if self.verbose:
            print(f"[INFO] {message}", file=sys.stderr)

    def parse_junit_xml(self, xml_file: Path):
        """Parse JUnit XML format test results."""
        self.log(f"Parsing JUnit XML: {xml_file}")

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Handle both <testsuite> and <testsuites> root elements
            if root.tag == "testsuites":
                suites = root.findall("testsuite")
            else:
                suites = [root]

            for suite_elem in suites:
                suite_name = suite_elem.attrib.get("name", "Unknown Suite")
                suite = TestSuite(suite_name)

                for testcase in suite_elem.findall("testcase"):
                    name = testcase.attrib.get("name", "Unknown Test")
                    classname = testcase.attrib.get("classname", "")
                    duration = float(testcase.attrib.get("time", 0))
                    file_path = testcase.attrib.get("file", None)
                    line = testcase.attrib.get("line", None)

                    # Determine status
                    failure = testcase.find("failure")
                    error = testcase.find("error")
                    skipped = testcase.find("skipped")

                    if failure is not None:
                        status = "failed"
                        message = failure.attrib.get("message", failure.text)
                    elif error is not None:
                        status = "error"
                        message = error.attrib.get("message", error.text)
                    elif skipped is not None:
                        status = "skipped"
                        message = skipped.attrib.get("message", "")
                    else:
                        status = "passed"
                        message = None

                    full_name = f"{classname}.{name}" if classname else name

                    test = TestResult(
                        name=full_name,
                        status=status,
                        duration=duration,
                        message=message,
                        file=file_path,
                        line=int(line) if line else None,
                    )
                    suite.add_test(test)

                self.suites.append(suite)

        except Exception as e:
            self.log(f"Error parsing JUnit XML: {e}")
            raise

    def parse_pytest_json(self, json_file: Path):
        """Parse pytest JSON report format."""
        self.log(f"Parsing pytest JSON: {json_file}")

        try:
            data = json.loads(json_file.read_text())

            suite = TestSuite("pytest")

            for test in data.get("tests", []):
                nodeid = test.get("nodeid", "Unknown")
                outcome = test.get("outcome", "unknown")
                duration = test.get("duration", 0)

                # Map pytest outcomes to standard statuses
                status_map = {
                    "passed": "passed",
                    "failed": "failed",
                    "skipped": "skipped",
                    "error": "error",
                }
                status = status_map.get(outcome, "error")

                message = None
                if status in ("failed", "error"):
                    call = test.get("call", {})
                    message = call.get("longrepr", "")

                # Extract file and line
                file_path = test.get("location", [None])[0]
                line = test.get("location", [None, None])[1]

                test_result = TestResult(
                    name=nodeid,
                    status=status,
                    duration=duration,
                    message=message,
                    file=file_path,
                    line=line,
                )
                suite.add_test(test_result)

            self.suites.append(suite)

        except Exception as e:
            self.log(f"Error parsing pytest JSON: {e}")
            raise

    def parse_coverage_xml(self, xml_file: Path) -> Dict:
        """Parse coverage.xml file."""
        self.log(f"Parsing coverage XML: {xml_file}")

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            line_rate = float(root.attrib.get("line-rate", 0))
            branch_rate = float(root.attrib.get("branch-rate", 0))
            lines_covered = int(root.attrib.get("lines-covered", 0))
            lines_valid = int(root.attrib.get("lines-valid", 0))

            return {
                "line_coverage_rate": line_rate,
                "line_coverage_percent": line_rate * 100,
                "branch_coverage_rate": branch_rate,
                "branch_coverage_percent": branch_rate * 100,
                "lines_covered": lines_covered,
                "lines_valid": lines_valid,
            }

        except Exception as e:
            self.log(f"Error parsing coverage XML: {e}")
            return {}

    def generate_summary(self) -> Dict:
        """Generate summary statistics."""
        total_tests = sum(suite.total for suite in self.suites)
        total_passed = sum(suite.passed for suite in self.suites)
        total_failed = sum(suite.failed for suite in self.suites)
        total_skipped = sum(suite.skipped for suite in self.suites)
        total_errors = sum(suite.errors for suite in self.suites)
        total_duration = sum(suite.duration for suite in self.suites)

        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        return {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "errors": total_errors,
            "success_rate": success_rate,
            "total_duration": total_duration,
        }

    def generate_json_report(self, coverage_data: Optional[Dict] = None) -> Dict:
        """Generate JSON report."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.generate_summary(),
            "suites": [
                {
                    "name": suite.name,
                    "total": suite.total,
                    "passed": suite.passed,
                    "failed": suite.failed,
                    "skipped": suite.skipped,
                    "errors": suite.errors,
                    "duration": suite.duration,
                    "success_rate": suite.success_rate,
                    "tests": [
                        {
                            "name": test.name,
                            "status": test.status,
                            "duration": test.duration,
                            "message": test.message,
                            "file": test.file,
                            "line": test.line,
                        }
                        for test in suite.tests
                    ],
                }
                for suite in self.suites
            ],
        }

        if coverage_data:
            report["coverage"] = coverage_data

        return report

    def generate_html_report(self, coverage_data: Optional[Dict] = None) -> str:
        """Generate HTML report."""
        summary = self.generate_summary()

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Integration Test Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}

        .timestamp {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .metric {{
            padding: 20px;
            border-radius: 6px;
            background: #ecf0f1;
        }}

        .metric.passed {{
            background: #d5f4e6;
            border-left: 4px solid #27ae60;
        }}

        .metric.failed {{
            background: #fadbd8;
            border-left: 4px solid #e74c3c;
        }}

        .metric.skipped {{
            background: #fef5e7;
            border-left: 4px solid #f39c12;
        }}

        .metric-label {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}

        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}

        .success-rate {{
            font-size: 1.2em;
            font-weight: bold;
            margin: 20px 0;
            padding: 15px;
            background: {"#d5f4e6" if summary["success_rate"] >= 90 else "#fef5e7" if summary["success_rate"] >= 70 else "#fadbd8"};
            border-radius: 6px;
            text-align: center;
        }}

        .coverage {{
            margin: 30px 0;
            padding: 20px;
            background: #e8f4f8;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }}

        .coverage h2 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}

        .coverage-bar {{
            background: #bdc3c7;
            height: 30px;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }}

        .coverage-fill {{
            height: 100%;
            background: linear-gradient(90deg, #3498db, #2ecc71);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 1s ease-in-out;
        }}

        .suite {{
            margin: 30px 0;
            border: 1px solid #ddd;
            border-radius: 6px;
            overflow: hidden;
        }}

        .suite-header {{
            padding: 15px 20px;
            background: #34495e;
            color: white;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .suite-header:hover {{
            background: #2c3e50;
        }}

        .suite-stats {{
            display: flex;
            gap: 15px;
            font-size: 0.9em;
        }}

        .suite-body {{
            padding: 20px;
        }}

        .test {{
            padding: 12px 15px;
            margin: 8px 0;
            border-radius: 4px;
            border-left: 4px solid;
        }}

        .test.passed {{
            background: #f0fdf4;
            border-left-color: #27ae60;
        }}

        .test.failed {{
            background: #fef2f2;
            border-left-color: #e74c3c;
        }}

        .test.skipped {{
            background: #fffbeb;
            border-left-color: #f39c12;
        }}

        .test.error {{
            background: #fef2f2;
            border-left-color: #e74c3c;
        }}

        .test-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }}

        .test-name {{
            font-weight: 500;
            color: #2c3e50;
        }}

        .test-duration {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}

        .test-message {{
            margin-top: 10px;
            padding: 10px;
            background: rgba(0,0,0,0.05);
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            white-space: pre-wrap;
            overflow-x: auto;
        }}

        .test-location {{
            color: #7f8c8d;
            font-size: 0.85em;
            margin-top: 5px;
        }}

        .status-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 500;
            text-transform: uppercase;
        }}

        .status-badge.passed {{
            background: #27ae60;
            color: white;
        }}

        .status-badge.failed {{
            background: #e74c3c;
            color: white;
        }}

        .status-badge.skipped {{
            background: #f39c12;
            color: white;
        }}

        .status-badge.error {{
            background: #c0392b;
            color: white;
        }}

        @media print {{
            body {{
                background: white;
                padding: 0;
            }}

            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Integration Test Report</h1>
        <div class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>

        <div class="summary">
            <div class="metric">
                <div class="metric-label">Total Tests</div>
                <div class="metric-value">{summary["total_tests"]}</div>
            </div>
            <div class="metric passed">
                <div class="metric-label">Passed</div>
                <div class="metric-value">{summary["passed"]}</div>
            </div>
            <div class="metric failed">
                <div class="metric-label">Failed</div>
                <div class="metric-value">{summary["failed"]}</div>
            </div>
            <div class="metric skipped">
                <div class="metric-label">Skipped</div>
                <div class="metric-value">{summary["skipped"]}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Duration</div>
                <div class="metric-value">{summary["total_duration"]:.2f}s</div>
            </div>
        </div>

        <div class="success-rate">
            Success Rate: {summary["success_rate"]:.1f}%
        </div>
"""

        # Add coverage if available
        if coverage_data:
            line_coverage = coverage_data.get("line_coverage_percent", 0)
            branch_coverage = coverage_data.get("branch_coverage_percent", 0)

            html += f"""
        <div class="coverage">
            <h2>Code Coverage</h2>
            <div>
                <strong>Line Coverage:</strong>
                <div class="coverage-bar">
                    <div class="coverage-fill" style="width: {line_coverage}%">
                        {line_coverage:.1f}%
                    </div>
                </div>
            </div>
            <div>
                <strong>Branch Coverage:</strong>
                <div class="coverage-bar">
                    <div class="coverage-fill" style="width: {branch_coverage}%">
                        {branch_coverage:.1f}%
                    </div>
                </div>
            </div>
        </div>
"""

        # Add test suites
        for suite in self.suites:
            html += f"""
        <div class="suite">
            <div class="suite-header">
                <h2>{suite.name}</h2>
                <div class="suite-stats">
                    <span>Total: {suite.total}</span>
                    <span>Passed: {suite.passed}</span>
                    <span>Failed: {suite.failed}</span>
                    <span>Duration: {suite.duration:.2f}s</span>
                </div>
            </div>
            <div class="suite-body">
"""

            for test in suite.tests:
                message_html = ""
                if test.message:
                    message_html = f'<div class="test-message">{test.message}</div>'

                location_html = ""
                if test.file:
                    location = f"{test.file}"
                    if test.line:
                        location += f":{test.line}"
                    location_html = f'<div class="test-location">{location}</div>'

                html += f"""
                <div class="test {test.status}">
                    <div class="test-header">
                        <div class="test-name">{test.name}</div>
                        <div>
                            <span class="status-badge {test.status}">{test.status}</span>
                            <span class="test-duration">{test.duration:.3f}s</span>
                        </div>
                    </div>
                    {location_html}
                    {message_html}
                </div>
"""

            html += """
            </div>
        </div>
"""

        html += """
    </div>
</body>
</html>
"""

        return html


def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive integration test reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate HTML report from JUnit XML
  %(prog)s --input results.xml --format html --output report.html

  # Generate JSON report from pytest JSON
  %(prog)s --input pytest_report.json --format json --output report.json

  # Include coverage data
  %(prog)s --input results.xml --coverage coverage.xml --output report.html

  # Verbose output
  %(prog)s --input results.xml --output report.html -v
        """
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument(
        "--input",
        required=True,
        help="Input test results file (JUnit XML or pytest JSON)"
    )
    parser.add_argument(
        "--format",
        choices=["html", "json"],
        default="html",
        help="Output format (default: html)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file path"
    )
    parser.add_argument(
        "--coverage",
        help="Coverage XML file (optional)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Shortcut for --format json"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Handle --json shortcut
    if args.json:
        args.format = "json"

    try:
        generator = ReportGenerator(verbose=args.verbose)

        # Parse input file
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input file not found: {input_path}", file=sys.stderr)
            sys.exit(1)

        # Detect format and parse
        if input_path.suffix == ".xml":
            generator.parse_junit_xml(input_path)
        elif input_path.suffix == ".json":
            generator.parse_pytest_json(input_path)
        else:
            print(f"Error: Unknown input format: {input_path.suffix}", file=sys.stderr)
            sys.exit(1)

        # Parse coverage if provided
        coverage_data = None
        if args.coverage:
            coverage_path = Path(args.coverage)
            if coverage_path.exists():
                coverage_data = generator.parse_coverage_xml(coverage_path)
            else:
                print(f"Warning: Coverage file not found: {coverage_path}", file=sys.stderr)

        # Generate report
        output_path = Path(args.output)

        if args.format == "json":
            report = generator.generate_json_report(coverage_data)
            output_path.write_text(json.dumps(report, indent=2))
        else:  # html
            report = generator.generate_html_report(coverage_data)
            output_path.write_text(report)

        print(f"Report generated: {output_path}")

        # Exit with error code if tests failed
        summary = generator.generate_summary()
        sys.exit(0 if summary["failed"] == 0 and summary["errors"] == 0 else 1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
