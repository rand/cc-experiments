#!/usr/bin/env python3
"""
Check Production Readiness (Gate 4)

Validates that refactor is ready for production deployment.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


class ProductionChecker:
    def __init__(self, refactor_ir: Path, test_dir: Path):
        self.refactor_ir = refactor_ir
        self.test_dir = test_dir
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def check(self) -> bool:
        """Run all production readiness checks. Returns True if passed."""
        print("🚀 Checking Production Readiness (Gate 4)...\n")

        checks = [
            ("Implementation complete", self.check_implementation_done),
            ("Migration plan documented", self.check_migration_plan),
            ("Rollback mechanism tested", self.check_rollback),
            ("Integration tests pass", self.check_integration_tests),
            ("Performance validated", self.check_performance),
            ("Documentation complete", self.check_documentation),
            ("Final report generated", self.check_final_report),
        ]

        results = []
        for name, check_fn in checks:
            passed = check_fn()
            results.append((name, passed))
            status = "✅" if passed else "❌"
            print(f"{status} {name}")

        print()

        if self.warnings:
            print("⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()

        if self.issues:
            print("❌ Issues:")
            for issue in self.issues:
                print(f"  - {issue}")
            print()

        all_passed = all(result[1] for result in results)

        if all_passed:
            print("✅ Production Ready - Refactor can be deployed!")
        else:
            print("❌ Not Production Ready - Address issues before deployment")

        return all_passed

    def check_implementation_done(self) -> bool:
        """Verify implementation phase is complete"""
        if not self.refactor_ir.exists():
            self.issues.append("REFACTOR_IR.md not found")
            return False

        content = self.refactor_ir.read_text()

        # Check all R* holes resolved
        r_holes = re.findall(r'####\s+(R\d+_\w+)', content)
        unresolved = []
        for hole_id in r_holes:
            pattern = rf'{hole_id}.*?\*\*Status\*\*:\s*(\w+)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                status = match.group(1).lower()
                if status not in ['resolved', 'complete', 'done']:
                    unresolved.append(hole_id)

        if unresolved:
            self.issues.append(
                f"Implementation incomplete - unresolved holes: {', '.join(unresolved)}"
            )
            return False

        return True

    def check_migration_plan(self) -> bool:
        """Check that migration plan is documented"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()

        # Look for migration holes
        migration_holes = ['M1_feature_flags', 'M2_backward_compatibility', 'R8_migration_path']

        has_migration_plan = False
        for hole_id in migration_holes:
            if hole_id in content:
                pattern = rf'{hole_id}.*?\*\*Resolution\*\*:\s*(.+?)(?:\*\*|---)'
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    resolution = match.group(1).strip()
                    if resolution not in ['TBD', 'TODO', '', 'N/A']:
                        has_migration_plan = True
                        break

        if not has_migration_plan:
            self.issues.append(
                "No migration plan documented\n"
                "    Define M1_feature_flags, M2_backward_compatibility, or R8_migration_path\n"
                "    How will you safely roll out changes?"
            )
            return False

        return True

    def check_rollback(self) -> bool:
        """Check that rollback mechanism is defined and tested"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()

        # Look for rollback documentation
        if 'R9_rollback' not in content and 'rollback' not in content.lower():
            self.issues.append(
                "No rollback mechanism documented\n"
                "    Define R9_rollback_mechanism with clear revert strategy"
            )
            return False

        # Look for rollback tests
        test_files = list(self.test_dir.rglob("*rollback*.py")) + \
                     list(self.test_dir.rglob("*revert*.py"))

        if not test_files:
            self.warnings.append(
                "No rollback tests found (e.g., test_rollback.py)\n"
                "    Consider testing that rollback works correctly"
            )

        return True

    def check_integration_tests(self) -> bool:
        """Check for integration/e2e tests"""
        integration_dirs = [
            self.test_dir / "integration",
            self.test_dir / "e2e",
            self.test_dir / "end_to_end"
        ]

        test_files = []
        for int_dir in integration_dirs:
            if int_dir.exists():
                test_files.extend(int_dir.glob("test_*.py"))

        if not test_files:
            self.warnings.append(
                "No integration/e2e tests found\n"
                "    Create tests/integration/ or tests/e2e/ with full workflow tests"
            )
            return True

        # Try to run integration tests
        try:
            for int_dir in integration_dirs:
                if int_dir.exists():
                    result = subprocess.run(
                        ["pytest", str(int_dir), "-v"],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )

                    if result.returncode != 0:
                        self.issues.append(
                            f"Integration tests failing in {int_dir.name}/\n"
                            f"    {result.stdout[-300:]}"
                        )
                        return False

            return True

        except FileNotFoundError:
            self.warnings.append("pytest not found - cannot verify integration tests")
            return True
        except subprocess.TimeoutExpired:
            self.warnings.append("Integration test run timed out")
            return True

    def check_performance(self) -> bool:
        """Check that performance hasn't regressed"""
        # Look for performance test results
        perf_files = list(self.test_dir.rglob("*performance*.py")) + \
                     list(self.test_dir.rglob("*benchmark*.py"))

        if not perf_files:
            self.warnings.append(
                "No performance tests found\n"
                "    Consider adding performance/benchmark tests to prevent regressions"
            )
            return True

        # Look for baseline comparisons
        baseline_files = list(Path(".").glob("*baseline*.json")) + \
                        list(Path(".").glob("*performance*.json"))

        if perf_files and not baseline_files:
            self.warnings.append(
                "Performance tests exist but no baseline data found\n"
                "    Save baseline metrics to compare against"
            )

        return True

    def check_documentation(self) -> bool:
        """Verify documentation is complete"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()

        # Check that all resolved holes have documented resolutions
        r_holes = re.findall(r'####\s+(R\d+_\w+)', content)

        missing_docs = []
        for hole_id in r_holes:
            # Check status
            status_pattern = rf'{hole_id}.*?\*\*Status\*\*:\s*(\w+)'
            status_match = re.search(status_pattern, content, re.DOTALL)

            if not status_match:
                continue

            status = status_match.group(1).lower()
            if status not in ['resolved', 'complete', 'done']:
                continue

            # Check resolution documented
            res_pattern = rf'{hole_id}.*?\*\*Resolution\*\*:\s*(.+?)(?:\*\*|---)'
            res_match = re.search(res_pattern, content, re.DOTALL)

            if not res_match or res_match.group(1).strip() in ['TBD', 'TODO', '']:
                missing_docs.append(hole_id)

        if missing_docs:
            self.warnings.append(
                f"Resolved holes missing documentation: {', '.join(missing_docs[:3])}"
            )

        return True

    def check_final_report(self) -> bool:
        """Check that final report has been generated"""
        report_files = [
            Path("REFACTOR_REPORT.md"),
            Path("REPORT.md"),
            Path("docs/REFACTOR_REPORT.md")
        ]

        report_exists = any(f.exists() for f in report_files)

        if not report_exists:
            self.issues.append(
                "Final refactor report not found\n"
                "    Run: python scripts/generate_report.py > REFACTOR_REPORT.md"
            )
            return False

        # Check report is recent and comprehensive
        for report_file in report_files:
            if report_file.exists():
                content = report_file.read_text()

                required_sections = [
                    "Hole Resolution Summary",
                    "Metrics",
                    "Validation"
                ]

                missing = [s for s in required_sections if s.lower() not in content.lower()]

                if missing:
                    self.warnings.append(
                        f"Report missing sections: {', '.join(missing)}"
                    )

                break

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Check Production Readiness (Gate 4)"
    )
    parser.add_argument(
        "--ir",
        type=Path,
        default=Path("REFACTOR_IR.md"),
        help="Path to REFACTOR_IR.md"
    )
    parser.add_argument(
        "--tests",
        type=Path,
        default=Path("tests"),
        help="Path to tests directory"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    checker = ProductionChecker(args.ir, args.tests)
    passed = checker.check()

    if args.json:
        result = {
            "gate": "production",
            "passed": passed,
            "issues": checker.issues,
            "warnings": checker.warnings
        }
        print(json.dumps(result, indent=2))

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
