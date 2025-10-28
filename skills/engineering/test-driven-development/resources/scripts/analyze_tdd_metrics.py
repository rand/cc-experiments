#!/usr/bin/env python3
"""
TDD Metrics Analyzer

Analyze test-to-code ratios, coverage progression, and TDD health metrics
from your codebase. Helps ensure you're following TDD practices and maintaining
good test quality.

Features:
- Calculate test-to-code ratio
- Analyze coverage trends over time
- Detect test smells and anti-patterns
- Generate TDD health report
- Track metrics across commits

Usage:
    analyze_tdd_metrics.py ratio --source-dir src/ --test-dir tests/
    analyze_tdd_metrics.py coverage --coverage-file .coverage
    analyze_tdd_metrics.py health --source-dir src/ --test-dir tests/
    analyze_tdd_metrics.py history --repo-dir . --commits 10
    analyze_tdd_metrics.py --help
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Tuple


@dataclass
class CodeMetrics:
    """Code metrics for a file or directory"""
    lines_of_code: int
    num_files: int
    num_functions: int
    num_classes: int
    blank_lines: int
    comment_lines: int


@dataclass
class TestMetrics:
    """Test metrics for a test suite"""
    num_tests: int
    num_test_files: int
    lines_of_test_code: int
    num_assertions: int
    num_mocks: int
    num_fixtures: int


@dataclass
class TDDHealth:
    """Overall TDD health metrics"""
    test_to_code_ratio: float
    coverage_percentage: float
    tests_per_file: float
    assertions_per_test: float
    has_test_smells: List[str]
    health_score: float  # 0-100


def count_lines(filepath: Path) -> Tuple[int, int, int]:
    """
    Count lines of code, blank lines, and comments in a file.

    Returns:
        (lines_of_code, blank_lines, comment_lines)
    """
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return (0, 0, 0)

    lines = content.split('\n')
    loc = 0
    blank = 0
    comments = 0

    in_multiline_comment = False
    comment_patterns = {
        '.py': (r'^\s*#', r'^\s*"""', r'^\s*"""'),
        '.ts': (r'^\s*//', r'^\s*/\*', r'\*/\s*$'),
        '.tsx': (r'^\s*//', r'^\s*/\*', r'\*/\s*$'),
        '.js': (r'^\s*//', r'^\s*/\*', r'\*/\s*$'),
        '.jsx': (r'^\s*//', r'^\s*/\*', r'\*/\s*$'),
        '.rs': (r'^\s*//', r'^\s*/\*', r'\*/\s*$'),
        '.go': (r'^\s*//', r'^\s*/\*', r'\*/\s*$'),
    }

    ext = filepath.suffix
    if ext not in comment_patterns:
        # Just count non-blank lines
        return (len([l for l in lines if l.strip()]), len([l for l in lines if not l.strip()]), 0)

    single_comment, multi_start, multi_end = comment_patterns[ext]

    for line in lines:
        stripped = line.strip()

        if not stripped:
            blank += 1
            continue

        # Check for multiline comments
        if re.match(multi_start, stripped):
            in_multiline_comment = True
            comments += 1
            continue

        if in_multiline_comment:
            comments += 1
            if re.search(multi_end, stripped):
                in_multiline_comment = False
            continue

        # Check for single-line comments
        if re.match(single_comment, stripped):
            comments += 1
            continue

        loc += 1

    return (loc, blank, comments)


def analyze_code_metrics(directory: Path, extensions: List[str] = None) -> CodeMetrics:
    """Analyze code metrics for a directory"""
    if extensions is None:
        extensions = ['.py', '.ts', '.tsx', '.js', '.jsx', '.rs', '.go']

    total_loc = 0
    total_blank = 0
    total_comments = 0
    num_files = 0
    num_functions = 0
    num_classes = 0

    for ext in extensions:
        for filepath in directory.rglob(f'*{ext}'):
            if any(part.startswith('.') for part in filepath.parts):
                continue  # Skip hidden directories

            num_files += 1
            loc, blank, comments = count_lines(filepath)
            total_loc += loc
            total_blank += blank
            total_comments += comments

            # Count functions and classes (simple heuristic)
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                if ext == '.py':
                    num_functions += len(re.findall(r'^\s*def\s+\w+', content, re.MULTILINE))
                    num_classes += len(re.findall(r'^\s*class\s+\w+', content, re.MULTILINE))
                elif ext in ['.ts', '.tsx', '.js', '.jsx']:
                    num_functions += len(re.findall(r'^\s*function\s+\w+', content, re.MULTILINE))
                    num_functions += len(re.findall(r'^\s*const\s+\w+\s*=\s*\(.*\)\s*=>', content, re.MULTILINE))
                    num_classes += len(re.findall(r'^\s*class\s+\w+', content, re.MULTILINE))
                elif ext == '.rs':
                    num_functions += len(re.findall(r'^\s*fn\s+\w+', content, re.MULTILINE))
                    num_classes += len(re.findall(r'^\s*struct\s+\w+', content, re.MULTILINE))
                elif ext == '.go':
                    num_functions += len(re.findall(r'^\s*func\s+\w+', content, re.MULTILINE))
                    num_classes += len(re.findall(r'^\s*type\s+\w+\s+struct', content, re.MULTILINE))
            except Exception:
                continue

    return CodeMetrics(
        lines_of_code=total_loc,
        num_files=num_files,
        num_functions=num_functions,
        num_classes=num_classes,
        blank_lines=total_blank,
        comment_lines=total_comments,
    )


def analyze_test_metrics(directory: Path, extensions: List[str] = None) -> TestMetrics:
    """Analyze test metrics for a test directory"""
    if extensions is None:
        extensions = ['.py', '.ts', '.tsx', '.js', '.jsx', '.rs', '.go']

    total_loc = 0
    num_test_files = 0
    num_tests = 0
    num_assertions = 0
    num_mocks = 0
    num_fixtures = 0

    test_patterns = {
        '.py': (r'^\s*def\s+test_\w+', r'\bassert\b', r'\bMock\b|\bmock\b|\bpatch\b', r'@pytest\.fixture'),
        '.ts': (r'^\s*test\(|^\s*it\(', r'\bexpect\(|\bassert', r'\bjest\.mock\b|\bmock', r'beforeEach\('),
        '.tsx': (r'^\s*test\(|^\s*it\(', r'\bexpect\(|\bassert', r'\bjest\.mock\b|\bmock', r'beforeEach\('),
        '.js': (r'^\s*test\(|^\s*it\(', r'\bexpect\(|\bassert', r'\bjest\.mock\b|\bmock', r'beforeEach\('),
        '.jsx': (r'^\s*test\(|^\s*it\(', r'\bexpect\(|\bassert', r'\bjest\.mock\b|\bmock', r'beforeEach\('),
        '.rs': (r'#\[test\]|^\s*fn\s+test_\w+', r'\bassert!|\bassert_eq!', r'\bmock', r''),
        '.go': (r'^\s*func\s+Test\w+', r'\bassert\b|\.Equal\(', r'\bmock', r''),
    }

    for ext in extensions:
        if ext not in test_patterns:
            continue

        test_pat, assert_pat, mock_pat, fixture_pat = test_patterns[ext]

        for filepath in directory.rglob(f'*{ext}'):
            if any(part.startswith('.') for part in filepath.parts):
                continue

            # Check if it's a test file
            name = filepath.name.lower()
            if not any(x in name for x in ['test', 'spec', '_test']):
                continue

            num_test_files += 1
            loc, _, _ = count_lines(filepath)
            total_loc += loc

            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                num_tests += len(re.findall(test_pat, content, re.MULTILINE))
                num_assertions += len(re.findall(assert_pat, content))
                num_mocks += len(re.findall(mock_pat, content))
                if fixture_pat:
                    num_fixtures += len(re.findall(fixture_pat, content))
            except Exception:
                continue

    return TestMetrics(
        num_tests=num_tests,
        num_test_files=num_test_files,
        lines_of_test_code=total_loc,
        num_assertions=num_assertions,
        num_mocks=num_mocks,
        num_fixtures=num_fixtures,
    )


def calculate_tdd_health(
    code_metrics: CodeMetrics,
    test_metrics: TestMetrics,
    coverage: float = None
) -> TDDHealth:
    """Calculate overall TDD health score"""

    # Test-to-code ratio (ideal: 1.0-2.0)
    if code_metrics.lines_of_code > 0:
        ratio = test_metrics.lines_of_test_code / code_metrics.lines_of_code
    else:
        ratio = 0.0

    # Tests per file (ideal: 5-20)
    if code_metrics.num_files > 0:
        tests_per_file = test_metrics.num_tests / code_metrics.num_files
    else:
        tests_per_file = 0.0

    # Assertions per test (ideal: 1-3)
    if test_metrics.num_tests > 0:
        assertions_per_test = test_metrics.num_assertions / test_metrics.num_tests
    else:
        assertions_per_test = 0.0

    # Detect test smells
    smells = []

    if ratio < 0.5:
        smells.append("Low test-to-code ratio (< 0.5)")
    elif ratio > 3.0:
        smells.append("Very high test-to-code ratio (> 3.0) - tests may be verbose")

    if assertions_per_test < 0.5:
        smells.append("Too few assertions per test - tests may not be verifying behavior")
    elif assertions_per_test > 5:
        smells.append("Too many assertions per test - tests may be too broad")

    if test_metrics.num_mocks > test_metrics.num_tests * 0.7:
        smells.append("Heavy mocking (>70% of tests) - may indicate over-mocking")

    if coverage and coverage < 70:
        smells.append(f"Low code coverage ({coverage:.1f}%)")

    # Calculate health score (0-100)
    score = 100.0

    # Ratio score (0-30 points)
    if ratio < 0.5:
        score -= 30
    elif ratio < 0.8:
        score -= 20
    elif ratio < 1.0:
        score -= 10
    elif ratio > 3.0:
        score -= 15

    # Coverage score (0-30 points)
    if coverage:
        if coverage < 50:
            score -= 30
        elif coverage < 70:
            score -= 20
        elif coverage < 80:
            score -= 10

    # Assertions score (0-20 points)
    if assertions_per_test < 0.5:
        score -= 20
    elif assertions_per_test < 1.0:
        score -= 10
    elif assertions_per_test > 5:
        score -= 10

    # Mocking score (0-20 points)
    if test_metrics.num_tests > 0:
        mock_ratio = test_metrics.num_mocks / test_metrics.num_tests
        if mock_ratio > 0.9:
            score -= 20
        elif mock_ratio > 0.7:
            score -= 10

    score = max(0, min(100, score))

    return TDDHealth(
        test_to_code_ratio=ratio,
        coverage_percentage=coverage or 0.0,
        tests_per_file=tests_per_file,
        assertions_per_test=assertions_per_test,
        has_test_smells=smells,
        health_score=score,
    )


def analyze_coverage_file(coverage_file: Path) -> float:
    """Extract coverage percentage from coverage file"""
    # Try to parse Python .coverage file
    if coverage_file.name == '.coverage':
        try:
            result = subprocess.run(
                ['coverage', 'report', '--format=total'],
                capture_output=True,
                text=True,
                check=True
            )
            return float(result.stdout.strip())
        except Exception:
            pass

    # Try to parse coverage.json (Jest, Istanbul)
    if coverage_file.suffix == '.json':
        try:
            data = json.loads(coverage_file.read_text())
            if 'total' in data and 'lines' in data['total']:
                return data['total']['lines']['pct']
        except Exception:
            pass

    # Try to parse lcov.info
    if coverage_file.name == 'lcov.info':
        try:
            content = coverage_file.read_text()
            lines_found = sum(int(m.group(1)) for m in re.finditer(r'LF:(\d+)', content))
            lines_hit = sum(int(m.group(1)) for m in re.finditer(r'LH:(\d+)', content))
            if lines_found > 0:
                return (lines_hit / lines_found) * 100
        except Exception:
            pass

    return 0.0


def analyze_history(repo_dir: Path, num_commits: int = 10) -> List[Dict]:
    """Analyze TDD metrics across git history"""
    try:
        # Get commit history
        result = subprocess.run(
            ['git', 'log', f'-{num_commits}', '--format=%H|%at|%s'],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )

        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            commit_hash, timestamp, message = line.split('|', 2)
            commits.append({
                'hash': commit_hash,
                'timestamp': int(timestamp),
                'message': message,
            })

        return commits
    except Exception as e:
        print(f"Error analyzing git history: {e}", file=sys.stderr)
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Analyze TDD metrics and health for your codebase"
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Ratio command
    ratio_parser = subparsers.add_parser('ratio', help='Calculate test-to-code ratio')
    ratio_parser.add_argument('--source-dir', type=Path, required=True, help='Source code directory')
    ratio_parser.add_argument('--test-dir', type=Path, required=True, help='Test directory')
    ratio_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # Coverage command
    coverage_parser = subparsers.add_parser('coverage', help='Analyze code coverage')
    coverage_parser.add_argument('--coverage-file', type=Path, required=True, help='Coverage file')
    coverage_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # Health command
    health_parser = subparsers.add_parser('health', help='Calculate TDD health score')
    health_parser.add_argument('--source-dir', type=Path, required=True, help='Source code directory')
    health_parser.add_argument('--test-dir', type=Path, required=True, help='Test directory')
    health_parser.add_argument('--coverage-file', type=Path, help='Coverage file (optional)')
    health_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # History command
    history_parser = subparsers.add_parser('history', help='Analyze metrics across commits')
    history_parser.add_argument('--repo-dir', type=Path, default=Path('.'), help='Repository directory')
    history_parser.add_argument('--commits', type=int, default=10, help='Number of commits to analyze')
    history_parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'ratio':
        code_metrics = analyze_code_metrics(args.source_dir)
        test_metrics = analyze_test_metrics(args.test_dir)

        ratio = test_metrics.lines_of_test_code / code_metrics.lines_of_code if code_metrics.lines_of_code > 0 else 0

        if args.json:
            print(json.dumps({
                'test_lines': test_metrics.lines_of_test_code,
                'code_lines': code_metrics.lines_of_code,
                'ratio': ratio,
            }, indent=2))
        else:
            print(f"Test-to-Code Ratio Analysis")
            print(f"===========================")
            print(f"Lines of test code: {test_metrics.lines_of_test_code}")
            print(f"Lines of source code: {code_metrics.lines_of_code}")
            print(f"Test-to-code ratio: {ratio:.2f}")
            print()
            if ratio < 0.5:
                print("⚠ Low test coverage - consider writing more tests")
            elif ratio >= 1.0:
                print("✓ Good test coverage!")

    elif args.command == 'coverage':
        coverage = analyze_coverage_file(args.coverage_file)

        if args.json:
            print(json.dumps({'coverage': coverage}, indent=2))
        else:
            print(f"Code Coverage: {coverage:.1f}%")
            if coverage < 70:
                print("⚠ Coverage below 70% - consider increasing test coverage")
            elif coverage >= 80:
                print("✓ Good coverage!")

    elif args.command == 'health':
        code_metrics = analyze_code_metrics(args.source_dir)
        test_metrics = analyze_test_metrics(args.test_dir)

        coverage = None
        if args.coverage_file and args.coverage_file.exists():
            coverage = analyze_coverage_file(args.coverage_file)

        health = calculate_tdd_health(code_metrics, test_metrics, coverage)

        if args.json:
            print(json.dumps({
                'code_metrics': asdict(code_metrics),
                'test_metrics': asdict(test_metrics),
                'health': asdict(health),
            }, indent=2))
        else:
            print("TDD Health Report")
            print("=================")
            print(f"\nCode Metrics:")
            print(f"  Files: {code_metrics.num_files}")
            print(f"  Lines of code: {code_metrics.lines_of_code}")
            print(f"  Functions: {code_metrics.num_functions}")
            print(f"  Classes: {code_metrics.num_classes}")

            print(f"\nTest Metrics:")
            print(f"  Test files: {test_metrics.num_test_files}")
            print(f"  Tests: {test_metrics.num_tests}")
            print(f"  Lines of test code: {test_metrics.lines_of_test_code}")
            print(f"  Assertions: {test_metrics.num_assertions}")

            print(f"\nTDD Health:")
            print(f"  Test-to-code ratio: {health.test_to_code_ratio:.2f}")
            if coverage:
                print(f"  Code coverage: {health.coverage_percentage:.1f}%")
            print(f"  Tests per file: {health.tests_per_file:.1f}")
            print(f"  Assertions per test: {health.assertions_per_test:.1f}")
            print(f"  Health score: {health.health_score:.0f}/100")

            if health.has_test_smells:
                print(f"\nTest Smells Detected:")
                for smell in health.has_test_smells:
                    print(f"  ⚠ {smell}")

            print("\nHealth Grade:")
            if health.health_score >= 90:
                print("  A - Excellent TDD practices!")
            elif health.health_score >= 80:
                print("  B - Good TDD practices")
            elif health.health_score >= 70:
                print("  C - Acceptable, room for improvement")
            elif health.health_score >= 60:
                print("  D - Needs improvement")
            else:
                print("  F - Poor TDD practices, needs significant work")

    elif args.command == 'history':
        commits = analyze_history(args.repo_dir, args.commits)

        if args.json:
            print(json.dumps(commits, indent=2))
        else:
            print(f"Analyzed {len(commits)} commits")
            for commit in commits[:5]:
                print(f"  {commit['hash'][:8]} - {commit['message'][:50]}")


if __name__ == '__main__':
    main()
