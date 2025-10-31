#!/usr/bin/env python3
"""
DSPy + PyO3 Setup Validator

Validates that the environment is correctly configured for using DSPy from Rust via PyO3.
Checks Rust toolchain, Python version, DSPy installation, and cross-language compatibility.

Usage:
    python dspy_setup_validator.py            # Check environment
    python dspy_setup_validator.py --fix      # Auto-fix issues where possible
    python dspy_setup_validator.py --report   # Generate detailed report
"""

import sys
import subprocess
import importlib
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict


@dataclass
class CheckResult:
    """Result of a validation check."""
    name: str
    passed: bool
    message: str
    fix_command: Optional[str] = None
    details: Optional[Dict] = None


class SetupValidator:
    """Validates DSPy + PyO3 environment setup."""

    def __init__(self, auto_fix: bool = False):
        self.auto_fix = auto_fix
        self.results: List[CheckResult] = []

    def check_rust_toolchain(self) -> CheckResult:
        """Check Rust toolchain installation."""
        try:
            result = subprocess.run(
                ["rustc", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()

            # Extract version number
            version_parts = version.split()[1].split('.')
            major, minor = int(version_parts[0]), int(version_parts[1])

            if major > 1 or (major == 1 and minor >= 70):
                return CheckResult(
                    name="Rust Toolchain",
                    passed=True,
                    message=f"✓ {version}",
                    details={"version": version}
                )
            else:
                return CheckResult(
                    name="Rust Toolchain",
                    passed=False,
                    message=f"✗ Version too old: {version} (need 1.70+)",
                    fix_command="rustup update"
                )

        except FileNotFoundError:
            return CheckResult(
                name="Rust Toolchain",
                passed=False,
                message="✗ Rust not installed",
                fix_command="curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
            )
        except Exception as e:
            return CheckResult(
                name="Rust Toolchain",
                passed=False,
                message=f"✗ Error checking Rust: {e}"
            )

    def check_cargo(self) -> CheckResult:
        """Check Cargo (Rust package manager)."""
        try:
            result = subprocess.run(
                ["cargo", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()

            return CheckResult(
                name="Cargo",
                passed=True,
                message=f"✓ {version}"
            )
        except FileNotFoundError:
            return CheckResult(
                name="Cargo",
                passed=False,
                message="✗ Cargo not found",
                fix_command="curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
            )

    def check_python_version(self) -> CheckResult:
        """Check Python version."""
        major, minor = sys.version_info.major, sys.version_info.minor

        if major >= 3 and minor >= 9:
            return CheckResult(
                name="Python Version",
                passed=True,
                message=f"✓ Python {major}.{minor}",
                details={"version": f"{major}.{minor}.{sys.version_info.micro}"}
            )
        else:
            return CheckResult(
                name="Python Version",
                passed=False,
                message=f"✗ Python {major}.{minor} (need 3.9+)",
                fix_command="Use pyenv or download Python 3.9+ from python.org"
            )

    def check_dspy_installation(self) -> CheckResult:
        """Check DSPy installation."""
        try:
            import dspy
            version = getattr(dspy, '__version__', 'unknown')

            return CheckResult(
                name="DSPy Installation",
                passed=True,
                message=f"✓ DSPy {version}",
                details={"version": version, "path": dspy.__file__}
            )
        except ImportError:
            return CheckResult(
                name="DSPy Installation",
                passed=False,
                message="✗ DSPy not installed",
                fix_command="pip install dspy-ai"
            )

    def check_pyo3_compatibility(self) -> CheckResult:
        """Check PyO3 compatibility."""
        try:
            # Check if we can import pyo3-compatible modules
            import sys
            import sysconfig

            python_lib = sysconfig.get_config_var('LIBDIR')
            python_include = sysconfig.get_config_var('INCLUDEPY')

            if python_lib and python_include:
                return CheckResult(
                    name="PyO3 Compatibility",
                    passed=True,
                    message="✓ Python development files found",
                    details={
                        "lib_dir": python_lib,
                        "include_dir": python_include
                    }
                )
            else:
                return CheckResult(
                    name="PyO3 Compatibility",
                    passed=False,
                    message="✗ Python development files not found",
                    fix_command="Install python3-dev (Ubuntu) or python-devel (Fedora)"
                )
        except Exception as e:
            return CheckResult(
                name="PyO3 Compatibility",
                passed=False,
                message=f"✗ Error: {e}"
            )

    def check_optional_dependencies(self) -> CheckResult:
        """Check optional but recommended dependencies."""
        optional = {
            "openai": "OpenAI API",
            "anthropic": "Anthropic API",
            "cohere": "Cohere API",
            "chromadb": "ChromaDB (for RAG)",
        }

        installed = []
        missing = []

        for package, description in optional.items():
            try:
                importlib.import_module(package)
                installed.append(f"{package} ({description})")
            except ImportError:
                missing.append(f"{package} ({description})")

        if missing:
            message = f"⚠ Optional packages missing: {', '.join(missing)}"
            fix_cmd = f"pip install {' '.join([p.split()[0] for p in missing])}"
        else:
            message = f"✓ All optional packages installed"
            fix_cmd = None

        return CheckResult(
            name="Optional Dependencies",
            passed=len(installed) > 0,  # At least some installed
            message=message,
            fix_command=fix_cmd,
            details={"installed": installed, "missing": missing}
        )

    def check_environment_variables(self) -> CheckResult:
        """Check required environment variables."""
        import os

        env_vars = {
            "OPENAI_API_KEY": False,
            "ANTHROPIC_API_KEY": False,
            "COHERE_API_KEY": False,
        }

        found = []
        for var in env_vars:
            if os.environ.get(var):
                found.append(var)
                env_vars[var] = True

        if found:
            return CheckResult(
                name="API Keys",
                passed=True,
                message=f"✓ Found: {', '.join(found)}",
                details=env_vars
            )
        else:
            return CheckResult(
                name="API Keys",
                passed=False,
                message="✗ No API keys found in environment",
                fix_command="export OPENAI_API_KEY=your-key"
            )

    def run_all_checks(self) -> List[CheckResult]:
        """Run all validation checks."""
        checks = [
            self.check_rust_toolchain,
            self.check_cargo,
            self.check_python_version,
            self.check_dspy_installation,
            self.check_pyo3_compatibility,
            self.check_optional_dependencies,
            self.check_environment_variables,
        ]

        self.results = []
        for check in checks:
            result = check()
            self.results.append(result)

            # Auto-fix if enabled
            if not result.passed and result.fix_command and self.auto_fix:
                print(f"\n🔧 Attempting to fix: {result.name}")
                print(f"   Command: {result.fix_command}")
                try:
                    subprocess.run(result.fix_command, shell=True, check=True)
                    print("   ✓ Fix applied successfully")
                except Exception as e:
                    print(f"   ✗ Fix failed: {e}")

        return self.results

    def print_report(self):
        """Print validation report."""
        print("\n" + "=" * 60)
        print("DSPy + PyO3 Environment Validation Report")
        print("=" * 60 + "\n")

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        for result in self.results:
            print(f"{result.message}")

            if not result.passed and result.fix_command:
                print(f"  💡 Fix: {result.fix_command}\n")

        print("\n" + "=" * 60)
        print(f"Summary: {passed}/{total} checks passed")

        if passed == total:
            print("✅ All checks passed! Ready to use DSPy from Rust.")
        elif passed >= total * 0.7:
            print("⚠️  Most checks passed. Fix remaining issues for full functionality.")
        else:
            print("❌ Several issues found. Please fix them before proceeding.")

        print("=" * 60 + "\n")

    def export_json(self, path: str):
        """Export results as JSON."""
        data = {
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
            },
            "checks": [asdict(r) for r in self.results]
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Report exported to: {path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate DSPy + PyO3 environment setup"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to auto-fix issues"
    )
    parser.add_argument(
        "--report",
        metavar="PATH",
        help="Export detailed JSON report to file"
    )

    args = parser.parse_args()

    validator = SetupValidator(auto_fix=args.fix)
    validator.run_all_checks()
    validator.print_report()

    if args.report:
        validator.export_json(args.report)

    # Exit with appropriate code
    passed = sum(1 for r in validator.results if r.passed)
    total = len(validator.results)

    if passed == total:
        sys.exit(0)
    elif passed >= total * 0.7:
        sys.exit(1)  # Warnings
    else:
        sys.exit(2)  # Errors


if __name__ == "__main__":
    main()
