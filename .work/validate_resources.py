#!/usr/bin/env python3
"""
Validate Level 3 Resources for all skills.

Checks:
- REFERENCE.md exists and is within 1,500-4,000 line range
- All scripts are executable and have proper shebang
- Scripts have --help and --json support (basic check)
- No TODO/stub/mock comments in scripts
- Minimum number of examples present

Usage:
    ./validate_resources.py                    # Validate all skills
    ./validate_resources.py --skill grpc       # Validate specific skill
    ./validate_resources.py --json             # JSON output
    ./validate_resources.py --strict           # Fail on warnings
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional

@dataclass
class ValidationResult:
    """Result of validating a single skill's resources."""
    skill_path: str
    skill_name: str
    status: str  # 'pass', 'warn', 'fail'
    issues: List[str]
    warnings: List[str]
    stats: Dict[str, any]

class ResourceValidator:
    """Validator for Level 3 Resources."""

    def __init__(self, skills_dir: Path, strict: bool = False):
        self.skills_dir = skills_dir
        self.strict = strict
        self.results: List[ValidationResult] = []

    def validate_all(self) -> List[ValidationResult]:
        """Validate all skills with resources."""
        skills_with_resources = self._find_skills_with_resources()

        for skill_path in sorted(skills_with_resources):
            result = self.validate_skill(skill_path)
            self.results.append(result)

        return self.results

    def validate_skill(self, skill_path: Path) -> ValidationResult:
        """Validate a single skill's resources."""
        skill_name = self._get_skill_name(skill_path)
        resources_dir = skill_path / "resources"

        issues = []
        warnings = []
        stats = {}

        # Check REFERENCE.md
        ref_check = self._check_reference_md(resources_dir)
        issues.extend(ref_check['errors'])
        warnings.extend(ref_check['warnings'])
        stats['reference_lines'] = ref_check['lines']

        # Check scripts
        scripts_check = self._check_scripts(resources_dir)
        issues.extend(scripts_check['errors'])
        warnings.extend(scripts_check['warnings'])
        stats['scripts_count'] = scripts_check['count']
        stats['scripts_executable'] = scripts_check['executable']

        # Check examples
        examples_check = self._check_examples(resources_dir)
        warnings.extend(examples_check['warnings'])
        stats['examples_count'] = examples_check['count']

        # Determine status
        if issues:
            status = 'fail'
        elif warnings and self.strict:
            status = 'fail'
        elif warnings:
            status = 'warn'
        else:
            status = 'pass'

        return ValidationResult(
            skill_path=str(skill_path.relative_to(self.skills_dir)),
            skill_name=skill_name,
            status=status,
            issues=issues,
            warnings=warnings,
            stats=stats
        )

    def _find_skills_with_resources(self) -> List[Path]:
        """Find all skill directories that have resources/ subdirectory."""
        skills = []

        # Search in main skills directory and category subdirectories
        for category_dir in self.skills_dir.iterdir():
            if not category_dir.is_dir():
                continue

            # Check if category has resources/ directly (e.g., engineering/resources/sre-practices)
            if (category_dir / "resources").exists():
                # Find skill directories under resources/
                resources_dir = category_dir / "resources"
                for skill_dir in resources_dir.iterdir():
                    if skill_dir.is_dir() and (skill_dir / "REFERENCE.md").exists():
                        skills.append(skill_dir.parent.parent / skill_dir.name)

            # Check for individual skill directories with resources/
            for item in category_dir.iterdir():
                if item.is_dir() and (item / "resources").exists():
                    skills.append(item)

        return skills

    def _get_skill_name(self, skill_path: Path) -> str:
        """Extract skill name from path."""
        # Handle both formats:
        # - category/skill-name/resources
        # - category/resources/skill-name
        parts = skill_path.parts
        if 'resources' in parts:
            idx = parts.index('resources')
            if idx > 0 and idx < len(parts) - 1:
                # Format: category/resources/skill-name
                return parts[-1]
            else:
                # Format: category/skill-name/resources
                return parts[-2] if len(parts) > 1 else parts[-1]
        return skill_path.name

    def _check_reference_md(self, resources_dir: Path) -> Dict:
        """Check REFERENCE.md file."""
        result = {'errors': [], 'warnings': [], 'lines': 0}

        ref_path = resources_dir / "REFERENCE.md"

        if not ref_path.exists():
            result['errors'].append("REFERENCE.md not found")
            return result

        # Count lines
        try:
            lines = len(ref_path.read_text().splitlines())
            result['lines'] = lines

            if lines < 1500:
                result['errors'].append(f"REFERENCE.md too short: {lines} lines (minimum 1,500)")
            elif lines > 4000:
                result['warnings'].append(f"REFERENCE.md very long: {lines} lines (target max 4,000)")
        except Exception as e:
            result['errors'].append(f"Error reading REFERENCE.md: {e}")

        return result

    def _check_scripts(self, resources_dir: Path) -> Dict:
        """Check scripts directory."""
        result = {'errors': [], 'warnings': [], 'count': 0, 'executable': 0}

        scripts_dir = resources_dir / "scripts"

        if not scripts_dir.exists():
            result['errors'].append("scripts/ directory not found")
            return result

        # Find all Python scripts
        scripts = list(scripts_dir.glob("*.py"))
        result['count'] = len(scripts)

        if len(scripts) < 3:
            result['warnings'].append(f"Only {len(scripts)} scripts found (expected 3)")

        for script in scripts:
            # Check executable
            if script.stat().st_mode & 0o111:
                result['executable'] += 1
            else:
                result['errors'].append(f"{script.name} is not executable")

            # Check shebang
            try:
                first_line = script.read_text().split('\n')[0]
                if not first_line.startswith('#!'):
                    result['errors'].append(f"{script.name} missing shebang")
                elif 'python' not in first_line.lower():
                    result['warnings'].append(f"{script.name} shebang doesn't reference python")
            except Exception as e:
                result['errors'].append(f"Error reading {script.name}: {e}")

            # Check for TODO/stub/mock comments
            try:
                content = script.read_text()
                if re.search(r'\bTODO\b', content, re.IGNORECASE):
                    result['warnings'].append(f"{script.name} contains TODO comments")
                if re.search(r'\bstub\b', content, re.IGNORECASE):
                    result['warnings'].append(f"{script.name} contains stub comments")
                if re.search(r'\bmock\b.*\bimplementation\b', content, re.IGNORECASE):
                    result['warnings'].append(f"{script.name} may contain mock implementation")

                # Check for --help support (basic heuristic)
                if '--help' not in content and 'argparse' not in content:
                    result['warnings'].append(f"{script.name} may not support --help")

                # Check for --json support (basic heuristic)
                if '--json' not in content:
                    result['warnings'].append(f"{script.name} may not support --json")

            except Exception as e:
                result['errors'].append(f"Error checking {script.name} content: {e}")

        return result

    def _check_examples(self, resources_dir: Path) -> Dict:
        """Check examples directory."""
        result = {'warnings': [], 'count': 0}

        examples_dir = resources_dir / "examples"

        if not examples_dir.exists():
            result['warnings'].append("examples/ directory not found")
            return result

        # Count example files (excluding READMEs and hidden files)
        examples = [f for f in examples_dir.rglob("*")
                   if f.is_file()
                   and not f.name.startswith('.')
                   and f.name.lower() != 'readme.md']
        result['count'] = len(examples)

        if len(examples) < 6:
            result['warnings'].append(f"Only {len(examples)} examples found (expected 6-10)")

        return result

    def print_results(self, verbose: bool = False):
        """Print validation results in human-readable format."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == 'pass')
        warned = sum(1 for r in self.results if r.status == 'warn')
        failed = sum(1 for r in self.results if r.status == 'fail')

        print(f"\n{'='*80}")
        print(f"Resource Validation Results")
        print(f"{'='*80}\n")

        print(f"Total skills validated: {total}")
        print(f"  ✓ Passed: {passed}")
        print(f"  ⚠ Warnings: {warned}")
        print(f"  ✗ Failed: {failed}")
        print()

        # Group by status
        for status, symbol in [('fail', '✗'), ('warn', '⚠'), ('pass', '✓')]:
            results = [r for r in self.results if r.status == status]
            if not results:
                continue

            print(f"\n{symbol} {status.upper()} ({len(results)}):")
            print("-" * 80)

            for result in results:
                print(f"\n{result.skill_name} ({result.skill_path})")
                print(f"  Stats: {result.stats['reference_lines']} lines REFERENCE.md, "
                      f"{result.stats['scripts_count']} scripts, "
                      f"{result.stats['examples_count']} examples")

                if result.issues:
                    print(f"  Issues:")
                    for issue in result.issues:
                        print(f"    ✗ {issue}")

                if result.warnings and (verbose or status != 'pass'):
                    print(f"  Warnings:")
                    for warning in result.warnings:
                        print(f"    ⚠ {warning}")

        print(f"\n{'='*80}\n")

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        return {
            'total': len(self.results),
            'passed': sum(1 for r in self.results if r.status == 'pass'),
            'warned': sum(1 for r in self.results if r.status == 'warn'),
            'failed': sum(1 for r in self.results if r.status == 'fail'),
            'skills': [asdict(r) for r in self.results]
        }

def main():
    parser = argparse.ArgumentParser(description="Validate Level 3 Resources for skills")
    parser.add_argument('--skill', help="Validate specific skill (name or path)")
    parser.add_argument('--json', action='store_true', help="Output as JSON")
    parser.add_argument('--strict', action='store_true', help="Fail on warnings")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose output")
    parser.add_argument('--skills-dir', type=Path, default=Path('skills'),
                       help="Path to skills directory (default: skills)")

    args = parser.parse_args()

    if not args.skills_dir.exists():
        print(f"Error: Skills directory not found: {args.skills_dir}", file=sys.stderr)
        sys.exit(1)

    validator = ResourceValidator(args.skills_dir, strict=args.strict)

    if args.skill:
        # Validate specific skill
        skill_path = args.skills_dir / args.skill
        if not skill_path.exists():
            # Try finding it
            candidates = list(args.skills_dir.rglob(f"*{args.skill}*"))
            if not candidates:
                print(f"Error: Skill not found: {args.skill}", file=sys.stderr)
                sys.exit(1)
            skill_path = candidates[0]

        result = validator.validate_skill(skill_path)
        validator.results = [result]
    else:
        # Validate all skills
        validator.validate_all()

    if args.json:
        print(json.dumps(validator.get_summary(), indent=2))
    else:
        validator.print_results(verbose=args.verbose)

    # Exit code
    summary = validator.get_summary()
    if summary['failed'] > 0:
        sys.exit(1)
    elif summary['warned'] > 0 and args.strict:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
