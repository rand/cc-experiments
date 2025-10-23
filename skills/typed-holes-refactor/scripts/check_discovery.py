#!/usr/bin/env python3
"""
Check Discovery Phase Completeness (Gate 1)

Validates that Phase 0 (Discovery) is complete and ready for hole resolution.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class DiscoveryChecker:
    def __init__(self, refactor_ir: Path, test_dir: Path):
        self.refactor_ir = refactor_ir
        self.test_dir = test_dir
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def check(self) -> bool:
        """Run all discovery checks. Returns True if passed."""
        print("🔍 Checking Discovery Phase (Gate 1)...\n")

        checks = [
            ("REFACTOR_IR.md exists", self.check_ir_exists),
            ("Holes cataloged", self.check_holes_cataloged),
            ("Dependencies mapped", self.check_dependencies_mapped),
            ("Constraints defined", self.check_constraints_defined),
            ("Characterization tests exist", self.check_characterization_tests),
            ("Current state holes resolved", self.check_current_state_holes),
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
            print("✅ Discovery Phase Complete - Ready for hole resolution!")
        else:
            print("❌ Discovery Phase Incomplete - Address issues before proceeding")

        return all_passed

    def check_ir_exists(self) -> bool:
        """Check that REFACTOR_IR.md exists"""
        if not self.refactor_ir.exists():
            self.issues.append(f"REFACTOR_IR.md not found at {self.refactor_ir}")
            return False
        return True

    def check_holes_cataloged(self) -> bool:
        """Check that holes are documented"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()

        # Look for hole definitions
        hole_pattern = r'^####\s+(H\d+|R\d+|M\d+)_\w+'
        holes = re.findall(hole_pattern, content, re.MULTILINE)

        if not holes:
            self.issues.append("No holes found in REFACTOR_IR.md")
            return False

        if len(holes) < 3:
            self.warnings.append(f"Only {len(holes)} holes found - consider more thorough analysis")

        # Check for at least one of each type
        has_current_state = any(h.startswith('H0') for h in holes)
        has_refactor = any(h.startswith('R') for h in holes)

        if not has_current_state:
            self.warnings.append("No current state holes (H0_*) - understanding current system is critical")

        if not has_refactor:
            self.issues.append("No refactor holes (R*) - what are we refactoring?")
            return False

        return True

    def check_dependencies_mapped(self) -> bool:
        """Check that dependencies are documented"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()

        # Look for dependency section
        if "## Dependency Graph" not in content and "Dependencies" not in content:
            self.issues.append("No dependency graph section in REFACTOR_IR.md")
            return False

        # Check for ready holes
        if "Ready to resolve" not in content and "no dependencies" not in content.lower():
            self.warnings.append("No 'ready to resolve' holes identified")

        return True

    def check_constraints_defined(self) -> bool:
        """Check that constraints are defined"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()

        if "## Constraints" not in content:
            self.issues.append("No Constraints section in REFACTOR_IR.md")
            return False

        # Check for the three constraint categories
        categories = ["Must Preserve", "Must Improve", "Must Maintain"]
        missing = [cat for cat in categories if cat not in content]

        if missing:
            self.warnings.append(f"Missing constraint categories: {', '.join(missing)}")

        return True

    def check_characterization_tests(self) -> bool:
        """Check that characterization tests exist"""
        char_test_dir = self.test_dir / "characterization"

        if not char_test_dir.exists():
            self.issues.append(
                f"Characterization test directory not found: {char_test_dir}\n"
                "    Create tests/characterization/ with baseline tests"
            )
            return False

        test_files = list(char_test_dir.glob("test_*.py"))

        if not test_files:
            self.issues.append(
                "No characterization tests found in tests/characterization/\n"
                "    Write tests that capture current behavior as baselines"
            )
            return False

        if len(test_files) < 2:
            self.warnings.append(
                f"Only {len(test_files)} characterization test file(s) - "
                "consider comprehensive coverage"
            )

        return True

    def check_current_state_holes(self) -> bool:
        """Check that current state holes are marked resolved"""
        if not self.refactor_ir.exists():
            return False

        content = self.refactor_ir.read_text()

        # Find all H0_ holes
        h0_holes = re.findall(r'####\s+(H0_\w+)', content)

        if not h0_holes:
            # No current state holes is okay if architecture is clear
            return True

        # Check status of each H0 hole
        unresolved = []
        for hole in h0_holes:
            # Find the hole section
            pattern = rf'####\s+{hole}.*?\*\*Status\*\*:\s*(\w+)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                status = match.group(1).lower()
                if status not in ['resolved', 'complete', 'done']:
                    unresolved.append(hole)
            else:
                unresolved.append(hole)

        if unresolved:
            self.warnings.append(
                f"Current state holes not resolved: {', '.join(unresolved)}\n"
                "    Resolve H0_ holes before refactor holes for better understanding"
            )

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Check Discovery Phase completeness (Gate 1)"
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

    checker = DiscoveryChecker(args.ir, args.tests)
    passed = checker.check()

    if args.json:
        result = {
            "gate": "discovery",
            "passed": passed,
            "issues": checker.issues,
            "warnings": checker.warnings
        }
        print(json.dumps(result, indent=2))

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
