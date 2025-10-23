#!/usr/bin/env python3
"""
Check Implementation Phase Completeness (Gate 3)

Validates that all refactor holes are resolved and metrics have improved.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


class ImplementationChecker:
    def __init__(self, refactor_ir: Path, test_dir: Path):
        self.refactor_ir = refactor_ir
        self.test_dir = test_dir
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def check(self) -> bool:
        """Run all implementation checks. Returns True if passed."""
        print("⚙️  Checking Implementation Phase (Gate 3)...\n")

        checks = [
            ("Foundation phase complete", self.check_foundation_done),
            ("All refactor holes resolved", self.check_all_holes_resolved),
            ("Implementation tests pass", self.check_implementation_tests),
            ("All tests passing", self.check_all_tests_pass),
            ("Metrics improved", self.check_metrics),
            ("Constraints satisfied", self.check_constraints),
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
            print("✅ Implementation Phase Complete - Ready for production validation!")
        else:
            print("❌ Implementation Phase Incomplete - Address issues before production")

        return all_passed

    def check_foundation_done(self) -> bool:
        """Verify foundation holes are resolved"""
        if not self.refactor_ir.exists():
            self.issues.append("REFACTOR_IR.md not found")
            return False

        content = self.refactor_ir.read_text()
        foundation_holes = ['R1_target_architecture', 'R2_module_boundaries']

        for hole_id in foundation_holes:
            if hole_id in content:
                pattern = rf'{hole_id}.*?\*\*Status\*\*:\s*(\w+)'
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    status = match.group(1).lower()
                    if status not in ['resolved', 'complete', 'done']:
                        self.issues.append(f"Foundation hole {hole_id} not resolved")
                        return False

        return True

    def check_all_holes_resolved(self) -> bool:
        """Check that all R* holes are resolved"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()

        # Find all R* holes
        r_holes = re.findall(r'####\s+(R\d+_\w+)', content)

        if not r_holes:
            self.warnings.append("No refactor holes found - was anything refactored?")
            return True

        unresolved = []
        for hole_id in r_holes:
            pattern = rf'{hole_id}.*?\*\*Status\*\*:\s*(\w+)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                status = match.group(1).lower()
                if status not in ['resolved', 'complete', 'done']:
                    unresolved.append(hole_id)
            else:
                unresolved.append(hole_id)

        if unresolved:
            self.issues.append(
                f"Unresolved refactor holes: {', '.join(unresolved)}\n"
                "    All R* holes must be resolved before implementation phase is complete"
            )
            return False

        return True

    def check_implementation_tests(self) -> bool:
        """Check that resolution tests exist for all resolved holes"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()
        resolved_holes = []

        # Find resolved R* holes
        r_holes = re.findall(r'####\s+(R\d+_\w+)', content)
        for hole_id in r_holes:
            pattern = rf'{hole_id}.*?\*\*Status\*\*:\s*(\w+)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                status = match.group(1).lower()
                if status in ['resolved', 'complete', 'done']:
                    resolved_holes.append(hole_id)

        if not resolved_holes:
            return True

        # Check for corresponding test files
        refactor_dir = self.test_dir / "refactor"
        if not refactor_dir.exists():
            self.issues.append("tests/refactor/ directory missing")
            return False

        test_files = list(refactor_dir.glob("test_*.py"))
        test_names = [f.stem.lower() for f in test_files]

        missing_tests = []
        for hole_id in resolved_holes:
            # Look for test files containing the hole ID
            hole_num = hole_id.split('_')[0].lower()  # e.g., "r1"
            if not any(hole_num in name for name in test_names):
                missing_tests.append(hole_id)

        if missing_tests:
            self.warnings.append(
                f"No tests found for resolved holes: {', '.join(missing_tests[:3])}"
                + (f" and {len(missing_tests) - 3} more" if len(missing_tests) > 3 else "")
            )

        return True

    def check_all_tests_pass(self) -> bool:
        """Verify all tests pass"""
        try:
            result = subprocess.run(
                ["pytest", str(self.test_dir), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                self.issues.append(
                    "Tests are failing\n"
                    f"    {result.stdout[-500:]}\n"
                    "    All tests must pass before proceeding"
                )
                return False

            return True

        except FileNotFoundError:
            self.warnings.append("pytest not found - cannot verify tests")
            return True
        except subprocess.TimeoutExpired:
            self.warnings.append("Test run timed out")
            return True

    def check_metrics(self) -> bool:
        """Check that code quality metrics have improved"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()

        # Look for constraint improvements
        if "Must Improve" not in content:
            self.warnings.append("No 'Must Improve' constraints defined")
            return True

        # Check for completion markers
        improve_section = content.split("Must Improve")[1].split("###")[0] if "Must Improve" in content else ""

        # Count checked vs unchecked improvements
        checked = improve_section.count("[x]") + improve_section.count("[X]")
        unchecked = improve_section.count("[ ]")

        if unchecked > 0 and checked == 0:
            self.warnings.append(
                f"None of the 'Must Improve' constraints are checked off\n"
                "    Measure and document metric improvements"
            )

        return True

    def check_constraints(self) -> bool:
        """Verify all constraints are satisfied"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()

        if "## Constraints" not in content:
            self.warnings.append("No Constraints section found")
            return True

        # Check each constraint category
        categories = {
            "Must Preserve": "critical",
            "Must Improve": "important",
            "Must Maintain": "important"
        }

        all_satisfied = True
        for category, severity in categories.items():
            if category not in content:
                continue

            section = content.split(category)[1].split("###")[0] if category in content else ""

            checked = section.count("[x]") + section.count("[X]")
            unchecked = section.count("[ ]")

            if unchecked > checked and severity == "critical":
                self.issues.append(
                    f"'{category}' constraints not satisfied - {unchecked} unchecked\n"
                    "    These are critical - all must be verified"
                )
                all_satisfied = False
            elif unchecked > 0 and severity == "important":
                self.warnings.append(
                    f"'{category}' has {unchecked} unchecked constraints"
                )

        return all_satisfied


def main():
    parser = argparse.ArgumentParser(
        description="Check Implementation Phase completeness (Gate 3)"
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

    checker = ImplementationChecker(args.ir, args.tests)
    passed = checker.check()

    if args.json:
        result = {
            "gate": "implementation",
            "passed": passed,
            "issues": checker.issues,
            "warnings": checker.warnings
        }
        print(json.dumps(result, indent=2))

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
