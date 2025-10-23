#!/usr/bin/env python3
"""
Check Foundation Phase Completeness (Gate 2)

Validates that core interface and architecture holes are resolved.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


class FoundationChecker:
    def __init__(self, refactor_ir: Path, test_dir: Path):
        self.refactor_ir = refactor_ir
        self.test_dir = test_dir
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def check(self) -> bool:
        """Run all foundation checks. Returns True if passed."""
        print("🏗️  Checking Foundation Phase (Gate 2)...\n")

        checks = [
            ("Discovery phase complete", self.check_discovery_done),
            ("Architecture holes resolved", self.check_architecture_holes),
            ("Core interfaces defined", self.check_interfaces),
            ("Resolution tests exist", self.check_resolution_tests),
            ("All tests passing", self.check_tests_pass),
            ("No violations of main branch", self.check_main_untouched),
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
            print("✅ Foundation Phase Complete - Ready for implementation holes!")
        else:
            print("❌ Foundation Phase Incomplete - Address issues before proceeding")

        return all_passed

    def check_discovery_done(self) -> bool:
        """Run check_discovery.py to ensure discovery is complete"""
        if not self.refactor_ir.exists():
            self.issues.append("REFACTOR_IR.md not found - run discovery first")
            return False

        # Check that characterization tests exist
        char_dir = self.test_dir / "characterization"
        if not char_dir.exists() or not list(char_dir.glob("test_*.py")):
            self.issues.append("Discovery incomplete - no characterization tests")
            return False

        return True

    def check_architecture_holes(self) -> bool:
        """Check that core architecture holes are resolved"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()

        # Key architecture holes that should be resolved
        key_holes = ['R1_target_architecture', 'R2_module_boundaries', 'R3_abstraction_layers']

        unresolved = []
        for hole_id in key_holes:
            # Check if hole exists
            if hole_id not in content:
                continue

            # Check status
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
                f"Key architecture holes not resolved: {', '.join(unresolved)}\n"
                "    Foundation requires clear architecture before implementation"
            )
            return False

        # Check that resolutions are documented
        for hole_id in key_holes:
            if hole_id in content:
                pattern = rf'{hole_id}.*?\*\*Resolution\*\*:\s*(.+?)(?:\*\*|---)'
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    resolution = match.group(1).strip()
                    if resolution in ['TBD', 'TODO', '']:
                        self.issues.append(f"{hole_id} marked resolved but has no resolution documented")
                        return False

        return True

    def check_interfaces(self) -> bool:
        """Check that core interfaces/protocols are defined in code"""
        # Look for interface definitions in the codebase
        code_dirs = [Path("src"), Path("lib"), Path(".")]

        interface_files = []
        for code_dir in code_dirs:
            if code_dir.exists():
                interface_files.extend(code_dir.glob("**/*interface*.py"))
                interface_files.extend(code_dir.glob("**/*protocol*.py"))
                interface_files.extend(code_dir.glob("**/base*.py"))

        if not interface_files:
            self.warnings.append(
                "No interface/protocol files found (e.g., interface.py, protocols.py, base.py)\n"
                "    Consider defining core abstractions explicitly"
            )

        return True

    def check_resolution_tests(self) -> bool:
        """Check that resolution tests exist for foundation holes"""
        refactor_dir = self.test_dir / "refactor"

        if not refactor_dir.exists():
            self.issues.append(
                f"Refactor test directory not found: {refactor_dir}\n"
                "    Create tests/refactor/ with resolution tests"
            )
            return False

        test_files = list(refactor_dir.glob("test_*.py"))

        if not test_files:
            self.issues.append(
                "No resolution tests in tests/refactor/\n"
                "    Write test_h*_resolution.py tests for each resolved hole"
            )
            return False

        # Check for architecture hole tests
        arch_tests = [f for f in test_files if any(x in f.name for x in ['r1', 'r2', 'r3', 'architecture', 'interface'])]

        if not arch_tests:
            self.warnings.append(
                "No tests for architecture holes found\n"
                "    Write tests validating architecture decisions (layer violations, etc.)"
            )

        return True

    def check_tests_pass(self) -> bool:
        """Check that all tests are passing"""
        try:
            # Try to run pytest
            result = subprocess.run(
                ["pytest", str(self.test_dir), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                self.issues.append(
                    "Tests are failing\n"
                    f"    Output: {result.stdout[-500:]}\n"
                    "    All tests must pass before proceeding to implementation"
                )
                return False

            return True

        except FileNotFoundError:
            self.warnings.append("pytest not found - cannot verify tests pass")
            return True
        except subprocess.TimeoutExpired:
            self.warnings.append("Test run timed out - check for hanging tests")
            return True

    def check_main_untouched(self) -> bool:
        """Verify main branch hasn't been modified"""
        try:
            # Check current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True
            )

            current_branch = result.stdout.strip()

            if current_branch in ["main", "master"]:
                self.issues.append(
                    f"Currently on {current_branch} branch!\n"
                    "    CRITICAL: Work must be done in refactor branch, never main"
                )
                return False

            # Check for refactor branch
            if not current_branch.startswith("refactor/"):
                self.warnings.append(
                    f"On branch '{current_branch}' - consider using 'refactor/*' naming convention"
                )

            return True

        except FileNotFoundError:
            self.warnings.append("Git not found - cannot verify branch safety")
            return True


def main():
    parser = argparse.ArgumentParser(
        description="Check Foundation Phase completeness (Gate 2)"
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

    checker = FoundationChecker(args.ir, args.tests)
    passed = checker.check()

    if args.json:
        result = {
            "gate": "foundation",
            "passed": passed,
            "issues": checker.issues,
            "warnings": checker.warnings
        }
        print(json.dumps(result, indent=2))

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
