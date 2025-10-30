#!/usr/bin/env python3
"""
PyO3 Development Environment Setup Validator

Validates that all required tools and dependencies are correctly installed
for PyO3 development.

Usage:
    python setup_validator.py [--verbose] [--json] [--fix] [--report PATH]

Examples:
    # Basic validation
    python setup_validator.py

    # Verbose output with all checks
    python setup_validator.py --verbose

    # JSON output for CI integration
    python setup_validator.py --json

    # Attempt automatic fixes
    python setup_validator.py --fix

    # Generate detailed report
    python setup_validator.py --report setup_report.md
"""

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class Status(Enum):
    """Check status enumeration."""
    PASSED = "✓ PASSED"
    FAILED = "✗ FAILED"
    WARNING = "⚠ WARNING"
    SKIPPED = "○ SKIPPED"


@dataclass
class CheckResult:
    """Result of a validation check."""
    name: str
    status: Status
    message: str
    details: Optional[str] = None
    fix_command: Optional[str] = None
    severity: str = "info"  # info, warning, error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.name,
            "message": self.message,
            "details": self.details,
            "fix_command": self.fix_command,
            "severity": self.severity,
        }


@dataclass
class ValidationReport:
    """Complete validation report."""
    platform_info: Dict[str, str] = field(default_factory=dict)
    checks: List[CheckResult] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "platform_info": self.platform_info,
            "checks": [check.to_dict() for check in self.checks],
            "summary": self.summary,
            "recommendations": self.recommendations,
        }


class SetupValidator:
    """Validates PyO3 development environment setup."""

    def __init__(self, verbose: bool = False, fix: bool = False):
        """
        Initialize validator.

        Args:
            verbose: Enable verbose output
            fix: Attempt automatic fixes for issues
        """
        self.verbose = verbose
        self.fix = fix
        self.results: List[CheckResult] = []

    def _run_command(
        self,
        cmd: List[str],
        capture_output: bool = True,
        check: bool = False,
        timeout: int = 30
    ) -> Tuple[int, str, str]:
        """
        Run shell command and return result.

        Args:
            cmd: Command and arguments
            capture_output: Capture stdout/stderr
            check: Raise exception on non-zero exit
            timeout: Command timeout in seconds

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=check,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s"
        except FileNotFoundError:
            return -1, "", f"Command not found: {cmd[0]}"
        except Exception as e:
            return -1, "", str(e)

    def _log(self, message: str, level: str = "info") -> None:
        """
        Log message if verbose mode enabled.

        Args:
            message: Message to log
            level: Log level (info, warning, error)
        """
        if self.verbose:
            prefix = {
                "info": "ℹ",
                "warning": "⚠",
                "error": "✗",
            }.get(level, "•")
            print(f"{prefix} {message}", file=sys.stderr)

    def add_result(self, result: CheckResult) -> None:
        """Add check result."""
        self.results.append(result)
        if result.status == Status.FAILED:
            self._log(f"{result.name}: {result.message}", "error")
        elif result.status == Status.WARNING:
            self._log(f"{result.name}: {result.message}", "warning")
        else:
            self._log(f"{result.name}: {result.message}", "info")

    def check_rust_installation(self) -> CheckResult:
        """Check if Rust is installed and meets minimum version."""
        self._log("Checking Rust installation...")

        returncode, stdout, stderr = self._run_command(["rustc", "--version"])

        if returncode != 0:
            return CheckResult(
                name="Rust Installation",
                status=Status.FAILED,
                message="Rust not found",
                details=stderr,
                fix_command="curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
                severity="error",
            )

        # Parse version
        version_match = re.search(r"rustc\s+(\d+)\.(\d+)\.(\d+)", stdout)
        if not version_match:
            return CheckResult(
                name="Rust Installation",
                status=Status.WARNING,
                message="Could not parse Rust version",
                details=stdout,
                severity="warning",
            )

        major, minor, patch = map(int, version_match.groups())
        version_str = f"{major}.{minor}.{patch}"

        # Check minimum version (1.70.0)
        if (major, minor) < (1, 70):
            return CheckResult(
                name="Rust Installation",
                status=Status.FAILED,
                message=f"Rust {version_str} is too old (minimum: 1.70.0)",
                fix_command="rustup update stable",
                severity="error",
            )

        return CheckResult(
            name="Rust Installation",
            status=Status.PASSED,
            message=f"Rust {version_str} installed",
        )

    def check_cargo(self) -> CheckResult:
        """Check if cargo is available."""
        self._log("Checking cargo...")

        returncode, stdout, stderr = self._run_command(["cargo", "--version"])

        if returncode != 0:
            return CheckResult(
                name="Cargo",
                status=Status.FAILED,
                message="cargo not found",
                details=stderr,
                fix_command="curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
                severity="error",
            )

        version_match = re.search(r"cargo\s+([\d.]+)", stdout)
        version_str = version_match.group(1) if version_match else "unknown"

        return CheckResult(
            name="Cargo",
            status=Status.PASSED,
            message=f"cargo {version_str} installed",
        )

    def check_python_installation(self) -> CheckResult:
        """Check if Python is installed and meets minimum version."""
        self._log("Checking Python installation...")

        version_info = sys.version_info
        version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

        # Check minimum version (3.8.0)
        if (version_info.major, version_info.minor) < (3, 8):
            return CheckResult(
                name="Python Installation",
                status=Status.FAILED,
                message=f"Python {version_str} is too old (minimum: 3.8.0)",
                severity="error",
            )

        return CheckResult(
            name="Python Installation",
            status=Status.PASSED,
            message=f"Python {version_str} installed",
        )

    def check_python_dev_headers(self) -> CheckResult:
        """Check if Python development headers are available."""
        self._log("Checking Python development headers...")

        try:
            import sysconfig
            include_dir = sysconfig.get_path("include")
            python_h = Path(include_dir) / "Python.h"

            if python_h.exists():
                return CheckResult(
                    name="Python Development Headers",
                    status=Status.PASSED,
                    message=f"Python.h found at {include_dir}",
                )
            else:
                system = platform.system()
                fix_commands = {
                    "Linux": "sudo apt install python3-dev  # Ubuntu/Debian\n"
                             "sudo dnf install python3-devel  # Fedora",
                    "Darwin": "brew install python  # Homebrew",
                    "Windows": "Reinstall Python with development headers",
                }

                return CheckResult(
                    name="Python Development Headers",
                    status=Status.FAILED,
                    message="Python.h not found",
                    details=f"Expected at: {python_h}",
                    fix_command=fix_commands.get(system, "Install Python development headers"),
                    severity="error",
                )
        except Exception as e:
            return CheckResult(
                name="Python Development Headers",
                status=Status.FAILED,
                message="Could not check for Python.h",
                details=str(e),
                severity="error",
            )

    def check_maturin(self) -> CheckResult:
        """Check if maturin is installed."""
        self._log("Checking maturin...")

        returncode, stdout, stderr = self._run_command(["maturin", "--version"])

        if returncode != 0:
            return CheckResult(
                name="maturin",
                status=Status.FAILED,
                message="maturin not found",
                details=stderr,
                fix_command="pip install maturin",
                severity="error",
            )

        version_match = re.search(r"maturin\s+([\d.]+)", stdout)
        version_str = version_match.group(1) if version_match else "unknown"

        # Check minimum version (1.0.0)
        if version_match:
            major = int(version_match.group(1).split('.')[0])
            if major < 1:
                return CheckResult(
                    name="maturin",
                    status=Status.WARNING,
                    message=f"maturin {version_str} is old (recommended: 1.0+)",
                    fix_command="pip install --upgrade maturin",
                    severity="warning",
                )

        return CheckResult(
            name="maturin",
            status=Status.PASSED,
            message=f"maturin {version_str} installed",
        )

    def check_compilation_target(self) -> CheckResult:
        """Check if compilation target is supported."""
        self._log("Checking compilation target...")

        returncode, stdout, stderr = self._run_command(["rustc", "--print", "target-list"])

        if returncode != 0:
            return CheckResult(
                name="Compilation Target",
                status=Status.WARNING,
                message="Could not list compilation targets",
                details=stderr,
                severity="warning",
            )

        # Get current target
        returncode, current_target, _ = self._run_command(
            ["rustc", "-vV"]
        )

        if returncode == 0:
            target_match = re.search(r"host:\s+(\S+)", current_target)
            if target_match:
                target = target_match.group(1)
                return CheckResult(
                    name="Compilation Target",
                    status=Status.PASSED,
                    message=f"Current target: {target}",
                )

        return CheckResult(
            name="Compilation Target",
            status=Status.PASSED,
            message="Compilation target available",
        )

    def check_c_compiler(self) -> CheckResult:
        """Check if C compiler is available (required for linking)."""
        self._log("Checking C compiler...")

        # Try cc first, then gcc, then clang
        compilers = ["cc", "gcc", "clang"]

        for compiler in compilers:
            returncode, stdout, stderr = self._run_command([compiler, "--version"])
            if returncode == 0:
                version_line = stdout.split('\n')[0] if stdout else "unknown version"
                return CheckResult(
                    name="C Compiler",
                    status=Status.PASSED,
                    message=f"{compiler} available: {version_line}",
                )

        system = platform.system()
        fix_commands = {
            "Linux": "sudo apt install build-essential  # Ubuntu/Debian\n"
                     "sudo dnf install gcc  # Fedora",
            "Darwin": "xcode-select --install",
            "Windows": "Install Visual Studio Build Tools or MinGW",
        }

        return CheckResult(
            name="C Compiler",
            status=Status.FAILED,
            message="No C compiler found (cc, gcc, or clang)",
            fix_command=fix_commands.get(system, "Install a C compiler"),
            severity="error",
        )

    def check_debugging_tools(self) -> CheckResult:
        """Check if debugging tools are available."""
        self._log("Checking debugging tools...")

        tools_found = []
        tools_missing = []

        # Check for lldb
        returncode, stdout, _ = self._run_command(["lldb", "--version"])
        if returncode == 0:
            version_line = stdout.split('\n')[0] if stdout else "lldb"
            tools_found.append(version_line)
        else:
            tools_missing.append("lldb")

        # Check for gdb
        returncode, stdout, _ = self._run_command(["gdb", "--version"])
        if returncode == 0:
            version_line = stdout.split('\n')[0] if stdout else "gdb"
            tools_found.append(version_line)
        else:
            tools_missing.append("gdb")

        if tools_found:
            status = Status.PASSED if not tools_missing else Status.WARNING
            message = f"Found: {', '.join(tools_found)}"
            if tools_missing:
                message += f" (missing: {', '.join(tools_missing)})"

            return CheckResult(
                name="Debugging Tools",
                status=status,
                message=message,
                severity="info" if status == Status.PASSED else "warning",
            )
        else:
            system = platform.system()
            fix_commands = {
                "Linux": "sudo apt install lldb  # Ubuntu/Debian",
                "Darwin": "xcode-select --install  # includes lldb",
                "Windows": "Install LLVM or Visual Studio",
            }

            return CheckResult(
                name="Debugging Tools",
                status=Status.WARNING,
                message="No debugging tools found (lldb or gdb recommended)",
                fix_command=fix_commands.get(system),
                severity="warning",
            )

    def check_pyo3_compilation(self) -> CheckResult:
        """Test PyO3 compilation with a minimal example."""
        self._log("Testing PyO3 compilation...")

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_pyo3"

            try:
                # Initialize maturin project
                returncode, stdout, stderr = self._run_command(
                    ["maturin", "init", "--bindings", "pyo3", "--name", "test_module"],
                    timeout=60,
                )

                if returncode != 0:
                    return CheckResult(
                        name="PyO3 Compilation Test",
                        status=Status.FAILED,
                        message="Failed to initialize maturin project",
                        details=stderr,
                        severity="error",
                    )

                # Change to project directory
                os.chdir(project_dir)

                # Build project
                self._log("Building test project (this may take a minute)...")
                returncode, stdout, stderr = self._run_command(
                    ["maturin", "build", "--release"],
                    timeout=300,  # 5 minutes
                )

                if returncode != 0:
                    return CheckResult(
                        name="PyO3 Compilation Test",
                        status=Status.FAILED,
                        message="Failed to compile PyO3 project",
                        details=stderr,
                        severity="error",
                    )

                return CheckResult(
                    name="PyO3 Compilation Test",
                    status=Status.PASSED,
                    message="Successfully compiled PyO3 test project",
                )

            except Exception as e:
                return CheckResult(
                    name="PyO3 Compilation Test",
                    status=Status.FAILED,
                    message="PyO3 compilation test failed",
                    details=str(e),
                    severity="error",
                )
            finally:
                # Return to original directory
                os.chdir(tmpdir)

    def check_optional_tools(self) -> List[CheckResult]:
        """Check for optional but recommended tools."""
        self._log("Checking optional tools...")

        results = []

        # cargo-watch for auto-rebuild
        returncode, stdout, _ = self._run_command(["cargo", "watch", "--version"])
        if returncode == 0:
            version = stdout.split()[1] if len(stdout.split()) > 1 else "unknown"
            results.append(CheckResult(
                name="cargo-watch",
                status=Status.PASSED,
                message=f"cargo-watch {version} installed",
            ))
        else:
            results.append(CheckResult(
                name="cargo-watch",
                status=Status.SKIPPED,
                message="cargo-watch not installed (optional)",
                fix_command="cargo install cargo-watch",
                severity="info",
            ))

        # flamegraph for profiling
        returncode, stdout, _ = self._run_command(["cargo", "flamegraph", "--version"])
        if returncode == 0:
            version = stdout.split()[1] if len(stdout.split()) > 1 else "unknown"
            results.append(CheckResult(
                name="flamegraph",
                status=Status.PASSED,
                message=f"flamegraph {version} installed",
            ))
        else:
            results.append(CheckResult(
                name="flamegraph",
                status=Status.SKIPPED,
                message="flamegraph not installed (optional)",
                fix_command="cargo install flamegraph",
                severity="info",
            ))

        # pytest for Python testing
        try:
            import pytest
            results.append(CheckResult(
                name="pytest",
                status=Status.PASSED,
                message=f"pytest {pytest.__version__} installed",
            ))
        except ImportError:
            results.append(CheckResult(
                name="pytest",
                status=Status.SKIPPED,
                message="pytest not installed (optional)",
                fix_command="pip install pytest",
                severity="info",
            ))

        # pytest-benchmark
        try:
            import pytest_benchmark
            results.append(CheckResult(
                name="pytest-benchmark",
                status=Status.PASSED,
                message="pytest-benchmark installed",
            ))
        except ImportError:
            results.append(CheckResult(
                name="pytest-benchmark",
                status=Status.SKIPPED,
                message="pytest-benchmark not installed (optional)",
                fix_command="pip install pytest-benchmark",
                severity="info",
            ))

        # mypy for type checking
        returncode, stdout, _ = self._run_command(["mypy", "--version"])
        if returncode == 0:
            version = stdout.strip().split()[-1] if stdout else "unknown"
            results.append(CheckResult(
                name="mypy",
                status=Status.PASSED,
                message=f"mypy {version} installed",
            ))
        else:
            results.append(CheckResult(
                name="mypy",
                status=Status.SKIPPED,
                message="mypy not installed (optional)",
                fix_command="pip install mypy",
                severity="info",
            ))

        return results

    def check_environment_variables(self) -> List[CheckResult]:
        """Check relevant environment variables."""
        self._log("Checking environment variables...")

        results = []

        # RUST_BACKTRACE
        rust_backtrace = os.environ.get("RUST_BACKTRACE")
        if rust_backtrace:
            results.append(CheckResult(
                name="RUST_BACKTRACE",
                status=Status.PASSED,
                message=f"RUST_BACKTRACE={rust_backtrace}",
            ))
        else:
            results.append(CheckResult(
                name="RUST_BACKTRACE",
                status=Status.SKIPPED,
                message="RUST_BACKTRACE not set (recommended for debugging)",
                fix_command="export RUST_BACKTRACE=1",
                severity="info",
            ))

        # PATH includes cargo bin
        cargo_home = os.environ.get("CARGO_HOME", os.path.expanduser("~/.cargo"))
        cargo_bin = Path(cargo_home) / "bin"
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)

        if str(cargo_bin) in path_dirs or cargo_bin.exists():
            results.append(CheckResult(
                name="Cargo in PATH",
                status=Status.PASSED,
                message=f"Cargo bin directory in PATH: {cargo_bin}",
            ))
        else:
            results.append(CheckResult(
                name="Cargo in PATH",
                status=Status.WARNING,
                message="Cargo bin directory not in PATH",
                fix_command=f"export PATH=\"{cargo_bin}:$PATH\"",
                severity="warning",
            ))

        return results

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on check results."""
        recommendations = []

        # Count failures by severity
        errors = [r for r in self.results if r.severity == "error"]
        warnings = [r for r in self.results if r.severity == "warning"]

        if errors:
            recommendations.append(
                f"Fix {len(errors)} critical issue(s) before proceeding with PyO3 development"
            )

        if warnings:
            recommendations.append(
                f"Address {len(warnings)} warning(s) for optimal development experience"
            )

        # Specific recommendations
        failed_checks = {r.name for r in self.results if r.status == Status.FAILED}

        if "Rust Installation" in failed_checks or "Cargo" in failed_checks:
            recommendations.append(
                "Install Rust toolchain: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
            )

        if "maturin" in failed_checks:
            recommendations.append("Install maturin: pip install maturin")

        if "C Compiler" in failed_checks:
            system = platform.system()
            if system == "Linux":
                recommendations.append("Install build tools: sudo apt install build-essential")
            elif system == "Darwin":
                recommendations.append("Install Xcode Command Line Tools: xcode-select --install")

        if "Debugging Tools" in {r.name for r in self.results if r.status == Status.WARNING}:
            recommendations.append("Install lldb for better debugging experience")

        if not errors and not warnings:
            recommendations.append("✓ Your environment is ready for PyO3 development!")

        return recommendations

    def run_all_checks(self) -> ValidationReport:
        """Run all validation checks."""
        print("=" * 60)
        print("PyO3 Development Environment Validator")
        print("=" * 60)
        print()

        # Collect platform info
        platform_info = {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": sys.version,
        }

        # Run core checks
        self.add_result(self.check_rust_installation())
        self.add_result(self.check_cargo())
        self.add_result(self.check_python_installation())
        self.add_result(self.check_python_dev_headers())
        self.add_result(self.check_maturin())
        self.add_result(self.check_compilation_target())
        self.add_result(self.check_c_compiler())
        self.add_result(self.check_debugging_tools())

        # Run environment checks
        for result in self.check_environment_variables():
            self.add_result(result)

        # Run optional tool checks
        for result in self.check_optional_tools():
            self.add_result(result)

        # Run compilation test (optional, can be slow)
        # self.add_result(self.check_pyo3_compilation())

        # Generate summary
        summary = {
            "passed": len([r for r in self.results if r.status == Status.PASSED]),
            "failed": len([r for r in self.results if r.status == Status.FAILED]),
            "warning": len([r for r in self.results if r.status == Status.WARNING]),
            "skipped": len([r for r in self.results if r.status == Status.SKIPPED]),
            "total": len(self.results),
        }

        recommendations = self.generate_recommendations()

        return ValidationReport(
            platform_info=platform_info,
            checks=self.results,
            summary=summary,
            recommendations=recommendations,
        )


def print_report(report: ValidationReport, verbose: bool = False) -> None:
    """Print validation report to console."""
    print("\n" + "=" * 60)
    print("Validation Results")
    print("=" * 60)
    print()

    # Print summary
    print(f"Total checks: {report.summary['total']}")
    print(f"  ✓ Passed:  {report.summary['passed']}")
    print(f"  ✗ Failed:  {report.summary['failed']}")
    print(f"  ⚠ Warning: {report.summary['warning']}")
    print(f"  ○ Skipped: {report.summary['skipped']}")
    print()

    # Print failed checks
    failed = [c for c in report.checks if c.status == Status.FAILED]
    if failed:
        print("Failed Checks:")
        print("-" * 60)
        for check in failed:
            print(f"{check.status.value} {check.name}")
            print(f"  {check.message}")
            if check.details and verbose:
                print(f"  Details: {check.details}")
            if check.fix_command:
                print(f"  Fix: {check.fix_command}")
            print()

    # Print warnings
    warnings = [c for c in report.checks if c.status == Status.WARNING]
    if warnings:
        print("Warnings:")
        print("-" * 60)
        for check in warnings:
            print(f"{check.status.value} {check.name}")
            print(f"  {check.message}")
            if check.fix_command:
                print(f"  Fix: {check.fix_command}")
            print()

    # Print recommendations
    if report.recommendations:
        print("Recommendations:")
        print("-" * 60)
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")
        print()

    # Print all checks if verbose
    if verbose:
        print("All Checks:")
        print("-" * 60)
        for check in report.checks:
            print(f"{check.status.value} {check.name}: {check.message}")
        print()


def save_json_report(report: ValidationReport, output_path: Path) -> None:
    """Save validation report as JSON."""
    with open(output_path, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)
    print(f"JSON report saved to: {output_path}")


def save_markdown_report(report: ValidationReport, output_path: Path) -> None:
    """Save validation report as Markdown."""
    with open(output_path, 'w') as f:
        f.write("# PyO3 Environment Validation Report\n\n")

        # Platform info
        f.write("## Platform Information\n\n")
        for key, value in report.platform_info.items():
            f.write(f"- **{key}**: {value}\n")
        f.write("\n")

        # Summary
        f.write("## Summary\n\n")
        f.write(f"- **Total checks**: {report.summary['total']}\n")
        f.write(f"- **Passed**: {report.summary['passed']}\n")
        f.write(f"- **Failed**: {report.summary['failed']}\n")
        f.write(f"- **Warning**: {report.summary['warning']}\n")
        f.write(f"- **Skipped**: {report.summary['skipped']}\n")
        f.write("\n")

        # Failed checks
        failed = [c for c in report.checks if c.status == Status.FAILED]
        if failed:
            f.write("## Failed Checks\n\n")
            for check in failed:
                f.write(f"### {check.name}\n\n")
                f.write(f"**Status**: {check.status.value}\n\n")
                f.write(f"**Message**: {check.message}\n\n")
                if check.details:
                    f.write(f"**Details**:\n```\n{check.details}\n```\n\n")
                if check.fix_command:
                    f.write(f"**Fix**:\n```bash\n{check.fix_command}\n```\n\n")

        # Warnings
        warnings = [c for c in report.checks if c.status == Status.WARNING]
        if warnings:
            f.write("## Warnings\n\n")
            for check in warnings:
                f.write(f"### {check.name}\n\n")
                f.write(f"**Message**: {check.message}\n\n")
                if check.fix_command:
                    f.write(f"**Fix**:\n```bash\n{check.fix_command}\n```\n\n")

        # Recommendations
        if report.recommendations:
            f.write("## Recommendations\n\n")
            for i, rec in enumerate(report.recommendations, 1):
                f.write(f"{i}. {rec}\n")
            f.write("\n")

        # All checks
        f.write("## All Checks\n\n")
        f.write("| Check | Status | Message |\n")
        f.write("|-------|--------|----------|\n")
        for check in report.checks:
            status_icon = {
                Status.PASSED: "✓",
                Status.FAILED: "✗",
                Status.WARNING: "⚠",
                Status.SKIPPED: "○",
            }[check.status]
            f.write(f"| {check.name} | {status_icon} | {check.message} |\n")

    print(f"Markdown report saved to: {output_path}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate PyO3 development environment setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt automatic fixes (not implemented yet)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        metavar="PATH",
        help="Save detailed report to file (markdown format)",
    )

    args = parser.parse_args()

    # Run validation
    validator = SetupValidator(verbose=args.verbose, fix=args.fix)
    report = validator.run_all_checks()

    # Output results
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report, verbose=args.verbose)

    # Save report if requested
    if args.report:
        save_markdown_report(report, args.report)

    # Exit code based on failures
    if report.summary['failed'] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
