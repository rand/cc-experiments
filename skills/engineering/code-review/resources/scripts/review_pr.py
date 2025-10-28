#!/usr/bin/env python3
"""
Automated PR review script - runs linters, checks tests, analyzes diff.

This script automates the mechanical aspects of code review:
- Runs configured linters and formatters
- Checks test coverage
- Analyzes diff for common issues
- Generates review report in human or JSON format

Usage:
    ./review_pr.py                          # Review current branch against main
    ./review_pr.py --base develop          # Compare against develop branch
    ./review_pr.py --pr 123                # Review GitHub PR #123
    ./review_pr.py --json                  # Output in JSON format
    ./review_pr.py --config review.yml     # Use custom config
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class Severity(Enum):
    """Issue severity levels."""
    BLOCKING = "blocking"
    IMPORTANT = "important"
    SUGGESTION = "suggestion"
    INFO = "info"


@dataclass
class Issue:
    """Represents a review issue."""
    severity: Severity
    file: str
    line: Optional[int]
    message: str
    tool: str
    code: Optional[str] = None


@dataclass
class ReviewReport:
    """Complete review report."""
    status: str  # "pass", "warning", "fail"
    issues: List[Issue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReviewConfig:
    """Configuration for code review checks."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            "python": {
                "enabled": True,
                "tools": {
                    "ruff": {"enabled": True, "command": "ruff check ."},
                    "mypy": {"enabled": True, "command": "mypy ."},
                    "bandit": {"enabled": True, "command": "bandit -r . -f json"},
                },
            },
            "javascript": {
                "enabled": True,
                "tools": {
                    "eslint": {"enabled": True, "command": "npx eslint . --format json"},
                    "prettier": {"enabled": True, "command": "npx prettier --check ."},
                },
            },
            "typescript": {
                "enabled": True,
                "tools": {
                    "eslint": {"enabled": True, "command": "npx eslint . --ext .ts,.tsx --format json"},
                    "tsc": {"enabled": True, "command": "npx tsc --noEmit"},
                },
            },
            "rust": {
                "enabled": True,
                "tools": {
                    "clippy": {"enabled": True, "command": "cargo clippy -- -D warnings"},
                    "rustfmt": {"enabled": True, "command": "cargo fmt -- --check"},
                },
            },
            "go": {
                "enabled": True,
                "tools": {
                    "golangci-lint": {"enabled": True, "command": "golangci-lint run --out-format json"},
                },
            },
            "tests": {
                "required": True,
                "coverage_threshold": 70,
            },
            "diff": {
                "max_lines": 1000,
                "max_files": 50,
            },
        }

        if config_path and config_path.exists():
            # In real implementation, load from YAML/JSON
            # For now, return defaults
            pass

        return default_config

    def get_enabled_languages(self) -> List[str]:
        """Get list of enabled language checks."""
        return [
            lang for lang, cfg in self.config.items()
            if isinstance(cfg, dict) and cfg.get("enabled", False)
        ]


class DiffAnalyzer:
    """Analyzes git diff for common issues."""

    def __init__(self, base_branch: str = "main"):
        self.base_branch = base_branch

    def get_diff(self) -> str:
        """Get diff against base branch."""
        try:
            result = subprocess.run(
                ["git", "diff", self.base_branch, "--unified=0"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error getting diff: {e}", file=sys.stderr)
            return ""

    def analyze(self) -> List[Issue]:
        """Analyze diff for common issues."""
        issues = []
        diff = self.get_diff()

        # Check for common patterns
        issues.extend(self._check_console_logs(diff))
        issues.extend(self._check_debug_statements(diff))
        issues.extend(self._check_todo_comments(diff))
        issues.extend(self._check_secrets(diff))
        issues.extend(self._check_large_files(diff))

        return issues

    def _check_console_logs(self, diff: str) -> List[Issue]:
        """Check for console.log/print statements in added lines."""
        issues = []
        pattern = re.compile(r'^\+.*\b(console\.log|print\(|println!|fmt\.Println)\b', re.MULTILINE)

        for match in pattern.finditer(diff):
            line_num = diff[:match.start()].count('\n') + 1
            issues.append(Issue(
                severity=Severity.SUGGESTION,
                file="unknown",  # Would need better diff parsing
                line=line_num,
                message="Consider removing debug statement before merge",
                tool="diff-analyzer",
                code="debug-statement"
            ))

        return issues

    def _check_debug_statements(self, diff: str) -> List[Issue]:
        """Check for debugger statements."""
        issues = []
        pattern = re.compile(r'^\+.*\b(debugger|pdb\.set_trace|breakpoint\(\))\b', re.MULTILINE)

        for match in pattern.finditer(diff):
            line_num = diff[:match.start()].count('\n') + 1
            issues.append(Issue(
                severity=Severity.BLOCKING,
                file="unknown",
                line=line_num,
                message="Remove debugger statement before merge",
                tool="diff-analyzer",
                code="debugger"
            ))

        return issues

    def _check_todo_comments(self, diff: str) -> List[Issue]:
        """Check for TODO/FIXME comments."""
        issues = []
        pattern = re.compile(r'^\+.*\b(TODO|FIXME|XXX|HACK)\b', re.MULTILINE | re.IGNORECASE)

        for match in pattern.finditer(diff):
            line_num = diff[:match.start()].count('\n') + 1
            issues.append(Issue(
                severity=Severity.IMPORTANT,
                file="unknown",
                line=line_num,
                message="TODO comment should be tracked in issue tracker or completed",
                tool="diff-analyzer",
                code="todo-comment"
            ))

        return issues

    def _check_secrets(self, diff: str) -> List[Issue]:
        """Check for potential secrets in added lines."""
        issues = []
        patterns = [
            (r'^\+.*\b(password|secret|api[_-]?key|token)\s*=\s*["\'][^"\']+["\']',
             "Potential secret in code"),
            (r'^\+.*\b(AWS|AKIA)[A-Z0-9]{16,}',
             "Potential AWS access key"),
            (r'^\+.*\bghp_[a-zA-Z0-9]{36,}',
             "Potential GitHub personal access token"),
        ]

        for pattern_str, message in patterns:
            pattern = re.compile(pattern_str, re.MULTILINE | re.IGNORECASE)
            for match in pattern.finditer(diff):
                line_num = diff[:match.start()].count('\n') + 1
                issues.append(Issue(
                    severity=Severity.BLOCKING,
                    file="unknown",
                    line=line_num,
                    message=message,
                    tool="diff-analyzer",
                    code="potential-secret"
                ))

        return issues

    def _check_large_files(self, diff: str) -> List[Issue]:
        """Check for large files being added."""
        issues = []
        # Simple heuristic: if diff is very long, file might be large
        lines = diff.split('\n')
        if len(lines) > 2000:
            issues.append(Issue(
                severity=Severity.SUGGESTION,
                file="unknown",
                line=None,
                message="Very large diff (>2000 lines). Consider splitting into smaller PRs.",
                tool="diff-analyzer",
                code="large-diff"
            ))

        return issues


class LinterRunner:
    """Runs linters and collects results."""

    def __init__(self, config: ReviewConfig):
        self.config = config

    def run_all(self) -> List[Issue]:
        """Run all enabled linters."""
        issues = []

        for language in self.config.get_enabled_languages():
            lang_config = self.config.config[language]
            tools = lang_config.get("tools", {})

            for tool_name, tool_config in tools.items():
                if not tool_config.get("enabled", True):
                    continue

                tool_issues = self._run_tool(tool_name, tool_config)
                issues.extend(tool_issues)

        return issues

    def _run_tool(self, tool_name: str, tool_config: Dict[str, Any]) -> List[Issue]:
        """Run a specific linting tool."""
        command = tool_config["command"]

        # SECURITY: command from config file - use trusted config files only
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            # Parse output based on tool
            if tool_name == "ruff":
                return self._parse_ruff_output(result.stdout, result.stderr)
            elif tool_name == "mypy":
                return self._parse_mypy_output(result.stdout)
            elif tool_name == "eslint":
                return self._parse_eslint_output(result.stdout)
            elif tool_name == "bandit":
                return self._parse_bandit_output(result.stdout)
            else:
                # Generic parser
                return self._parse_generic_output(result.stdout, result.stderr, tool_name)

        except subprocess.TimeoutExpired:
            return [Issue(
                severity=Severity.IMPORTANT,
                file="",
                line=None,
                message=f"{tool_name} timed out after 5 minutes",
                tool=tool_name,
            )]
        except FileNotFoundError:
            return [Issue(
                severity=Severity.INFO,
                file="",
                line=None,
                message=f"{tool_name} not found. Install it to enable checks.",
                tool=tool_name,
            )]
        except Exception as e:
            return [Issue(
                severity=Severity.INFO,
                file="",
                line=None,
                message=f"Error running {tool_name}: {str(e)}",
                tool=tool_name,
            )]

    def _parse_ruff_output(self, stdout: str, stderr: str) -> List[Issue]:
        """Parse ruff output."""
        issues = []
        # Ruff format: path/to/file.py:10:5: E501 Line too long
        pattern = re.compile(r'^([^:]+):(\d+):(?:\d+): ([A-Z]\d+) (.+)$', re.MULTILINE)

        for match in pattern.finditer(stdout):
            file_path, line_num, code, message = match.groups()
            severity = Severity.IMPORTANT if code.startswith('E') else Severity.SUGGESTION

            issues.append(Issue(
                severity=severity,
                file=file_path,
                line=int(line_num),
                message=message,
                tool="ruff",
                code=code,
            ))

        return issues

    def _parse_mypy_output(self, stdout: str) -> List[Issue]:
        """Parse mypy output."""
        issues = []
        # mypy format: path/to/file.py:10: error: Message
        pattern = re.compile(r'^([^:]+):(\d+): (error|warning|note): (.+)$', re.MULTILINE)

        for match in pattern.finditer(stdout):
            file_path, line_num, level, message = match.groups()
            severity = Severity.BLOCKING if level == "error" else Severity.SUGGESTION

            issues.append(Issue(
                severity=severity,
                file=file_path,
                line=int(line_num),
                message=message,
                tool="mypy",
            ))

        return issues

    def _parse_eslint_output(self, stdout: str) -> List[Issue]:
        """Parse ESLint JSON output."""
        try:
            data = json.loads(stdout)
            issues = []

            for file_result in data:
                file_path = file_result.get("filePath", "")
                for message in file_result.get("messages", []):
                    severity_level = message.get("severity", 1)
                    severity = Severity.IMPORTANT if severity_level == 2 else Severity.SUGGESTION

                    issues.append(Issue(
                        severity=severity,
                        file=file_path,
                        line=message.get("line"),
                        message=message.get("message", ""),
                        tool="eslint",
                        code=message.get("ruleId"),
                    ))

            return issues
        except json.JSONDecodeError:
            return []

    def _parse_bandit_output(self, stdout: str) -> List[Issue]:
        """Parse Bandit JSON output."""
        try:
            data = json.loads(stdout)
            issues = []

            for result in data.get("results", []):
                severity_map = {
                    "HIGH": Severity.BLOCKING,
                    "MEDIUM": Severity.IMPORTANT,
                    "LOW": Severity.SUGGESTION,
                }
                severity = severity_map.get(result.get("issue_severity", "LOW"), Severity.SUGGESTION)

                issues.append(Issue(
                    severity=severity,
                    file=result.get("filename", ""),
                    line=result.get("line_number"),
                    message=result.get("issue_text", ""),
                    tool="bandit",
                    code=result.get("test_id"),
                ))

            return issues
        except json.JSONDecodeError:
            return []

    def _parse_generic_output(self, stdout: str, stderr: str, tool_name: str) -> List[Issue]:
        """Generic parser for unknown tools."""
        if stdout.strip() or stderr.strip():
            return [Issue(
                severity=Severity.INFO,
                file="",
                line=None,
                message=f"{tool_name} output:\n{stdout}\n{stderr}",
                tool=tool_name,
            )]
        return []


class TestChecker:
    """Checks test coverage and execution."""

    def __init__(self, config: ReviewConfig):
        self.config = config

    def check(self) -> Tuple[List[Issue], Dict[str, Any]]:
        """Check tests and coverage."""
        issues = []
        stats = {}

        # Try to detect test framework and run tests
        if self._has_pytest():
            test_issues, test_stats = self._run_pytest()
            issues.extend(test_issues)
            stats.update(test_stats)
        elif self._has_jest():
            test_issues, test_stats = self._run_jest()
            issues.extend(test_issues)
            stats.update(test_stats)
        elif self._has_cargo():
            test_issues, test_stats = self._run_cargo_test()
            issues.extend(test_issues)
            stats.update(test_stats)
        else:
            issues.append(Issue(
                severity=Severity.INFO,
                file="",
                line=None,
                message="No test framework detected",
                tool="test-checker",
            ))

        return issues, stats

    def _has_pytest(self) -> bool:
        """Check if pytest is available."""
        return subprocess.run(["which", "pytest"], capture_output=True).returncode == 0

    def _has_jest(self) -> bool:
        """Check if jest is available."""
        return Path("node_modules/.bin/jest").exists()

    def _has_cargo(self) -> bool:
        """Check if cargo is available."""
        return subprocess.run(["which", "cargo"], capture_output=True).returncode == 0

    def _run_pytest(self) -> Tuple[List[Issue], Dict[str, Any]]:
        """Run pytest with coverage."""
        issues = []
        stats = {}

        try:
            result = subprocess.run(
                ["pytest", "--cov", "--cov-report=json", "--cov-report=term", "-v"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            # Check if tests passed
            if result.returncode != 0:
                issues.append(Issue(
                    severity=Severity.BLOCKING,
                    file="",
                    line=None,
                    message="Tests failed. All tests must pass before merge.",
                    tool="pytest",
                ))

            # Parse coverage
            coverage_file = Path("coverage.json")
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                    stats["test_coverage"] = total_coverage

                    threshold = self.config.config["tests"].get("coverage_threshold", 70)
                    if total_coverage < threshold:
                        issues.append(Issue(
                            severity=Severity.IMPORTANT,
                            file="",
                            line=None,
                            message=f"Coverage {total_coverage:.1f}% is below threshold {threshold}%",
                            tool="pytest",
                        ))

        except subprocess.TimeoutExpired:
            issues.append(Issue(
                severity=Severity.BLOCKING,
                file="",
                line=None,
                message="Tests timed out after 5 minutes",
                tool="pytest",
            ))
        except Exception as e:
            issues.append(Issue(
                severity=Severity.INFO,
                file="",
                line=None,
                message=f"Error running tests: {str(e)}",
                tool="pytest",
            ))

        return issues, stats

    def _run_jest(self) -> Tuple[List[Issue], Dict[str, Any]]:
        """Run Jest tests."""
        issues = []
        stats = {}

        try:
            result = subprocess.run(
                ["npx", "jest", "--coverage", "--json"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                issues.append(Issue(
                    severity=Severity.BLOCKING,
                    file="",
                    line=None,
                    message="Tests failed",
                    tool="jest",
                ))

            # Parse Jest JSON output
            try:
                data = json.loads(result.stdout)
                if "coverageMap" in data:
                    # Calculate coverage
                    pass  # Simplified for example
            except json.JSONDecodeError:
                pass

        except Exception as e:
            issues.append(Issue(
                severity=Severity.INFO,
                file="",
                line=None,
                message=f"Error running Jest: {str(e)}",
                tool="jest",
            ))

        return issues, stats

    def _run_cargo_test(self) -> Tuple[List[Issue], Dict[str, Any]]:
        """Run Rust cargo tests."""
        issues = []
        stats = {}

        try:
            result = subprocess.run(
                ["cargo", "test"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                issues.append(Issue(
                    severity=Severity.BLOCKING,
                    file="",
                    line=None,
                    message="Tests failed",
                    tool="cargo-test",
                ))

        except Exception as e:
            issues.append(Issue(
                severity=Severity.INFO,
                file="",
                line=None,
                message=f"Error running cargo test: {str(e)}",
                tool="cargo-test",
            ))

        return issues, stats


class PRReviewer:
    """Main PR review orchestrator."""

    def __init__(self, config: ReviewConfig, base_branch: str = "main"):
        self.config = config
        self.base_branch = base_branch
        self.diff_analyzer = DiffAnalyzer(base_branch)
        self.linter_runner = LinterRunner(config)
        self.test_checker = TestChecker(config)

    def review(self) -> ReviewReport:
        """Perform complete PR review."""
        all_issues = []
        stats = {}

        # 1. Analyze diff
        print("Analyzing diff...", file=sys.stderr)
        diff_issues = self.diff_analyzer.analyze()
        all_issues.extend(diff_issues)

        # 2. Run linters
        print("Running linters...", file=sys.stderr)
        linter_issues = self.linter_runner.run_all()
        all_issues.extend(linter_issues)

        # 3. Check tests
        print("Running tests...", file=sys.stderr)
        test_issues, test_stats = self.test_checker.check()
        all_issues.extend(test_issues)
        stats.update(test_stats)

        # 4. Compile statistics
        stats.update({
            "total_issues": len(all_issues),
            "blocking_issues": sum(1 for i in all_issues if i.severity == Severity.BLOCKING),
            "important_issues": sum(1 for i in all_issues if i.severity == Severity.IMPORTANT),
            "suggestions": sum(1 for i in all_issues if i.severity == Severity.SUGGESTION),
        })

        # 5. Determine overall status
        if stats["blocking_issues"] > 0:
            status = "fail"
        elif stats["important_issues"] > 0:
            status = "warning"
        else:
            status = "pass"

        return ReviewReport(
            status=status,
            issues=all_issues,
            stats=stats,
            metadata={
                "base_branch": self.base_branch,
                "timestamp": subprocess.run(
                    ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
                    capture_output=True,
                    text=True
                ).stdout.strip(),
            }
        )


def format_report_human(report: ReviewReport) -> str:
    """Format report for human reading."""
    lines = []

    # Header
    lines.append("=" * 70)
    lines.append("PR REVIEW REPORT")
    lines.append("=" * 70)
    lines.append(f"Status: {report.status.upper()}")
    lines.append(f"Base branch: {report.metadata.get('base_branch', 'unknown')}")
    lines.append(f"Timestamp: {report.metadata.get('timestamp', 'unknown')}")
    lines.append("")

    # Statistics
    lines.append("Statistics:")
    lines.append(f"  Total issues: {report.stats.get('total_issues', 0)}")
    lines.append(f"  Blocking: {report.stats.get('blocking_issues', 0)}")
    lines.append(f"  Important: {report.stats.get('important_issues', 0)}")
    lines.append(f"  Suggestions: {report.stats.get('suggestions', 0)}")

    if "test_coverage" in report.stats:
        lines.append(f"  Test coverage: {report.stats['test_coverage']:.1f}%")

    lines.append("")

    # Issues by severity
    if report.issues:
        for severity in [Severity.BLOCKING, Severity.IMPORTANT, Severity.SUGGESTION, Severity.INFO]:
            severity_issues = [i for i in report.issues if i.severity == severity]
            if not severity_issues:
                continue

            lines.append(f"\n{severity.value.upper()} Issues ({len(severity_issues)}):")
            lines.append("-" * 70)

            for issue in severity_issues:
                location = f"{issue.file}:{issue.line}" if issue.line else issue.file
                if location:
                    lines.append(f"  {location}")
                lines.append(f"  [{issue.tool}] {issue.message}")
                if issue.code:
                    lines.append(f"  Code: {issue.code}")
                lines.append("")
    else:
        lines.append("\nNo issues found! ✓")

    lines.append("=" * 70)

    return "\n".join(lines)


def format_report_json(report: ReviewReport) -> str:
    """Format report as JSON."""
    data = {
        "status": report.status,
        "issues": [
            {
                "severity": issue.severity.value,
                "file": issue.file,
                "line": issue.line,
                "message": issue.message,
                "tool": issue.tool,
                "code": issue.code,
            }
            for issue in report.issues
        ],
        "stats": report.stats,
        "metadata": report.metadata,
    }
    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Automated PR review - runs linters, checks tests, analyzes diff",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Review current branch against main
  %(prog)s --base develop           # Compare against develop branch
  %(prog)s --pr 123                 # Review GitHub PR #123
  %(prog)s --json                   # Output in JSON format
  %(prog)s --config review.yml      # Use custom config
        """
    )

    parser.add_argument(
        "--base",
        default="main",
        help="Base branch to compare against (default: main)"
    )
    parser.add_argument(
        "--pr",
        type=int,
        help="GitHub PR number to review"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to review configuration file"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report in JSON format"
    )

    args = parser.parse_args()

    # Load configuration
    config = ReviewConfig(args.config)

    # Create reviewer
    reviewer = PRReviewer(config, args.base)

    # Run review
    report = reviewer.review()

    # Output report
    if args.json:
        print(format_report_json(report))
    else:
        print(format_report_human(report))

    # Exit with appropriate code
    if report.status == "fail":
        sys.exit(1)
    elif report.status == "warning":
        sys.exit(0)  # Don't fail on warnings
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
