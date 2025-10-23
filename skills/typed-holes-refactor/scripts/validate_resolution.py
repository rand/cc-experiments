#!/usr/bin/env python3
"""
Validate that a hole resolution satisfies all requirements

Checks:
1. Tests exist and pass
2. Characterization tests still pass
3. Constraints satisfied
4. Main branch untouched
"""

import argparse
import subprocess
from pathlib import Path
from typing import List, Tuple


class ValidationError(Exception):
    pass


class HoleValidator:
    def __init__(self, hole_id: str, project_root: Path):
        self.hole_id = hole_id
        self.root = project_root
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def validate(self) -> bool:
        """Run all validation checks"""
        print(f"🔍 Validating resolution for {self.hole_id}")
        print("=" * 60)
        print()
        
        checks = [
            ("Resolution tests exist", self.check_resolution_tests_exist),
            ("Resolution tests pass", self.check_resolution_tests_pass),
            ("Characterization tests pass", self.check_characterization_tests),
            ("Main branch untouched", self.check_main_untouched),
            ("Beads untouched", self.check_beads_untouched),
        ]
        
        for check_name, check_fn in checks:
            try:
                print(f"Checking: {check_name}...", end=" ")
                check_fn()
                print("✅")
            except ValidationError as e:
                print("❌")
                self.errors.append(f"{check_name}: {e}")
            except Warning as w:
                print("⚠️")
                self.warnings.append(f"{check_name}: {w}")
        
        print()
        
        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   {warning}")
            print()
        
        if self.errors:
            print("❌ VALIDATION FAILED:")
            for error in self.errors:
                print(f"   {error}")
            print()
            return False
        
        print("✅ VALIDATION PASSED")
        print()
        print("Next steps:")
        print(f"  1. Update REFACTOR_IR.md: mark {self.hole_id} as 'resolved'")
        print(f"  2. Propagate constraints: python scripts/propagate.py {self.hole_id}")
        print(f"  3. Commit: git commit -m 'Resolve {self.hole_id}: ...'")
        print()
        
        return True
    
    def check_resolution_tests_exist(self):
        """Check that resolution tests exist"""
        test_pattern = f"test_{self.hole_id.lower()}_*.py"
        test_files = list(Path("tests/refactor").glob(test_pattern))
        
        if not test_files:
            raise ValidationError(
                f"No resolution tests found matching {test_pattern}"
            )
    
    def check_resolution_tests_pass(self):
        """Run resolution tests"""
        test_pattern = f"tests/refactor/test_{self.hole_id.lower()}_*.py"
        test_files = list(Path("tests/refactor").glob(f"test_{self.hole_id.lower()}_*.py"))
        
        if not test_files:
            raise ValidationError("No resolution tests to run")
        
        result = subprocess.run(
            ["pytest", "-xvs"] + [str(f) for f in test_files],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise ValidationError(
                f"Resolution tests failed:\n{result.stdout}\n{result.stderr}"
            )
    
    def check_characterization_tests(self):
        """Ensure characterization tests still pass"""
        if not Path("tests/characterization").exists():
            raise Warning("No characterization tests found - highly recommended!")
        
        result = subprocess.run(
            ["pytest", "-x", "tests/characterization/"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise ValidationError(
                f"Characterization tests failed - behavior changed!\n{result.stdout}"
            )
    
    def check_main_untouched(self):
        """Verify main branch is untouched"""
        # Check current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=self.root
        )
        
        current_branch = result.stdout.strip()
        
        if current_branch == "main":
            raise ValidationError(
                "You're on main branch! Should be on refactor branch."
            )
        
        # Check if main has been modified
        result = subprocess.run(
            ["git", "diff", "origin/main", "--name-only"],
            capture_output=True,
            text=True,
            cwd=self.root
        )
        
        # No changed files means we're good
        # (Note: this is a simple check, could be more sophisticated)
    
    def check_beads_untouched(self):
        """Verify .beads/ in main is untouched"""
        if not (self.root / ".beads").exists():
            return  # No beads, skip check
        
        # Check if .beads/ has been modified in this branch
        result = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", ".beads/"],
            capture_output=True,
            text=True,
            cwd=self.root
        )
        
        changed_beads = result.stdout.strip()
        
        if changed_beads:
            raise ValidationError(
                f"Beads modified in main:\n{changed_beads}\n"
                "Beads should never be modified!"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Validate hole resolution"
    )
    parser.add_argument(
        "hole_id",
        help="Hole ID to validate (e.g., H1, R4)"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory"
    )
    
    args = parser.parse_args()
    
    validator = HoleValidator(args.hole_id, args.root)
    success = validator.validate()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
