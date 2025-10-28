#!/usr/bin/env python3
"""
PostgreSQL Migration Analyzer

Analyzes migration files for unsafe operations, locking issues, and best practices.
Detects potential problems before applying migrations to production.

Features:
- Detects unsafe DDL operations (locks, table rewrites)
- Identifies missing idempotency guards (IF EXISTS, IF NOT EXISTS)
- Warns about data loss operations
- Checks for transaction compatibility
- Suggests safer alternatives

Usage:
    ./analyze_migration.py migration.sql
    ./analyze_migration.py --json migration.sql
    ./analyze_migration.py --dir migrations/
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional


class Severity(Enum):
    """Issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Category(Enum):
    """Issue categories"""
    LOCKING = "locking"
    DATA_LOSS = "data_loss"
    IDEMPOTENCY = "idempotency"
    PERFORMANCE = "performance"
    TRANSACTION = "transaction"
    BEST_PRACTICE = "best_practice"


@dataclass
class Issue:
    """Migration analysis issue"""
    severity: Severity
    category: Category
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'severity': self.severity.value,
            'category': self.category.value,
            'message': self.message,
            'line_number': self.line_number,
            'suggestion': self.suggestion
        }


@dataclass
class AnalysisResult:
    """Migration analysis result"""
    file_path: str
    issues: List[Issue]
    safe: bool
    summary: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'file_path': self.file_path,
            'issues': [issue.to_dict() for issue in self.issues],
            'safe': self.safe,
            'summary': self.summary
        }


class MigrationAnalyzer:
    """Analyzes PostgreSQL migration files for safety issues"""

    # Unsafe operations that take AccessExclusiveLock
    UNSAFE_OPERATIONS = [
        (r'\bCREATE\s+INDEX\s+(?!CONCURRENTLY)', 'CREATE INDEX without CONCURRENTLY',
         'Use CREATE INDEX CONCURRENTLY to avoid blocking writes'),
        (r'\bDROP\s+INDEX\s+(?!CONCURRENTLY)', 'DROP INDEX without CONCURRENTLY',
         'Use DROP INDEX CONCURRENTLY to avoid blocking writes'),
        (r'\bALTER\s+TABLE\s+\w+\s+ADD\s+COLUMN\s+\w+.*NOT\s+NULL(?!\s+DEFAULT)',
         'Adding NOT NULL column without DEFAULT',
         'Add column as nullable first, backfill, then add NOT NULL constraint'),
        (r'\bALTER\s+TABLE\s+\w+\s+ALTER\s+COLUMN\s+\w+\s+TYPE',
         'Changing column type (may rewrite table)',
         'Consider adding new column, dual-write, then drop old column'),
        (r'\bALTER\s+TABLE\s+\w+\s+RENAME\s+COLUMN',
         'Renaming column directly',
         'Use expand-contract pattern: add new column, dual-write, drop old'),
    ]

    # Data loss operations
    DATA_LOSS_OPERATIONS = [
        (r'\bDROP\s+TABLE', 'Dropping table (data loss)'),
        (r'\bDROP\s+COLUMN', 'Dropping column (data loss)'),
        (r'\bTRUNCATE', 'Truncating table (data loss)'),
        (r'\bDELETE\s+FROM\s+\w+\s*;', 'Deleting all rows (data loss)'),
    ]

    # Operations requiring idempotency guards
    IDEMPOTENCY_CHECKS = [
        (r'\bCREATE\s+TABLE\s+(?!IF\s+NOT\s+EXISTS)', 'CREATE TABLE without IF NOT EXISTS'),
        (r'\bCREATE\s+INDEX\s+(?!.*IF\s+NOT\s+EXISTS)', 'CREATE INDEX without IF NOT EXISTS'),
        (r'\bALTER\s+TABLE\s+\w+\s+ADD\s+COLUMN\s+(?!.*IF\s+NOT\s+EXISTS)',
         'ADD COLUMN without IF NOT EXISTS (PG 9.6+)'),
        # NOTE: This pattern DETECTS dangerous operations in migrations, doesn't perform them
        (r'\bDROP\s+TABLE\s+(?!IF\s+EXISTS)', 'DROP TABLE without IF EXISTS'),
        (r'\bDROP\s+INDEX\s+(?!.*IF\s+EXISTS)', 'DROP INDEX without IF EXISTS'),
    ]

    # Operations that cannot run in transaction
    NON_TRANSACTIONAL = [
        r'\bCREATE\s+INDEX\s+CONCURRENTLY',
        r'\bDROP\s+INDEX\s+CONCURRENTLY',
        r'\bREINDEX\s+.*CONCURRENTLY',
        r'\bVACUUM',
    ]

    # Best practices
    BEST_PRACTICES = [
        (r'\bALTER\s+TABLE\s+\w+\s+ADD\s+CONSTRAINT.*(?!NOT\s+VALID)',
         'Adding constraint without NOT VALID',
         'Use NOT VALID then VALIDATE CONSTRAINT to avoid blocking writes'),
        (r'\bUPDATE\s+\w+\s+SET.*(?!LIMIT)',
         'Large UPDATE without batching',
         'Consider batching with LIMIT and pg_sleep() to avoid long locks'),
    ]

    def analyze_file(self, file_path: Path) -> AnalysisResult:
        """Analyze a single migration file"""
        issues: List[Issue] = []

        try:
            content = file_path.read_text()
            lines = content.split('\n')

            # Check for unsafe operations
            for pattern, message, suggestion in self.UNSAFE_OPERATIONS:
                issues.extend(self._find_issues(
                    lines, pattern, Severity.ERROR, Category.LOCKING,
                    message, suggestion
                ))

            # Check for data loss operations
            for pattern, message in self.DATA_LOSS_OPERATIONS:
                issues.extend(self._find_issues(
                    lines, pattern, Severity.WARNING, Category.DATA_LOSS, message
                ))

            # Check for idempotency
            for pattern, message in self.IDEMPOTENCY_CHECKS:
                issues.extend(self._find_issues(
                    lines, pattern, Severity.WARNING, Category.IDEMPOTENCY, message
                ))

            # Check for non-transactional operations
            has_begin = any(re.search(r'\bBEGIN\b', line, re.IGNORECASE) for line in lines)
            for pattern in self.NON_TRANSACTIONAL:
                if has_begin:
                    issues.extend(self._find_issues(
                        lines, pattern, Severity.ERROR, Category.TRANSACTION,
                        'Non-transactional operation inside transaction',
                        'Move CONCURRENTLY operations to separate migration file'
                    ))

            # Check best practices
            for pattern, message, suggestion in self.BEST_PRACTICES:
                issues.extend(self._find_issues(
                    lines, pattern, Severity.INFO, Category.BEST_PRACTICE,
                    message, suggestion
                ))

        except Exception as e:
            issues.append(Issue(
                severity=Severity.ERROR,
                category=Category.BEST_PRACTICE,
                message=f"Failed to analyze file: {str(e)}"
            ))

        # Calculate summary
        summary = {
            'errors': sum(1 for i in issues if i.severity == Severity.ERROR),
            'warnings': sum(1 for i in issues if i.severity == Severity.WARNING),
            'info': sum(1 for i in issues if i.severity == Severity.INFO),
        }

        # Consider safe if no errors
        safe = summary['errors'] == 0

        return AnalysisResult(
            file_path=str(file_path),
            issues=issues,
            safe=safe,
            summary=summary
        )

    def _find_issues(
        self,
        lines: List[str],
        pattern: str,
        severity: Severity,
        category: Category,
        message: str,
        suggestion: Optional[str] = None
    ) -> List[Issue]:
        """Find issues matching pattern in lines"""
        issues = []

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('--'):
                continue

            if re.search(pattern, line, re.IGNORECASE):
                issues.append(Issue(
                    severity=severity,
                    category=category,
                    message=message,
                    line_number=line_num,
                    suggestion=suggestion
                ))

        return issues

    def analyze_directory(self, dir_path: Path) -> List[AnalysisResult]:
        """Analyze all SQL files in directory"""
        results = []

        for sql_file in sorted(dir_path.glob('*.sql')):
            if sql_file.is_file():
                results.append(self.analyze_file(sql_file))

        return results


def format_text_output(results: List[AnalysisResult]) -> str:
    """Format results as human-readable text"""
    output = []

    for result in results:
        output.append(f"\n{'='*80}")
        output.append(f"File: {result.file_path}")
        output.append(f"Status: {'✓ SAFE' if result.safe else '✗ UNSAFE'}")
        output.append(f"Issues: {result.summary['errors']} errors, "
                     f"{result.summary['warnings']} warnings, "
                     f"{result.summary['info']} info")
        output.append('='*80)

        if not result.issues:
            output.append("  No issues found!")
            continue

        # Group issues by severity
        for severity in [Severity.ERROR, Severity.WARNING, Severity.INFO]:
            severity_issues = [i for i in result.issues if i.severity == severity]

            if severity_issues:
                output.append(f"\n{severity.value.upper()}S:")
                for issue in severity_issues:
                    line_info = f" (line {issue.line_number})" if issue.line_number else ""
                    output.append(f"  • {issue.message}{line_info}")

                    if issue.suggestion:
                        output.append(f"    Suggestion: {issue.suggestion}")

    return '\n'.join(output)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Analyze PostgreSQL migration files for safety issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./analyze_migration.py migration.sql
  ./analyze_migration.py --json migration.sql
  ./analyze_migration.py --dir migrations/

Categories:
  - locking: Operations that may lock tables
  - data_loss: Operations that may lose data
  - idempotency: Missing idempotency guards
  - performance: Performance concerns
  - transaction: Transaction compatibility issues
  - best_practice: Best practice recommendations
        """
    )

    parser.add_argument(
        'path',
        type=Path,
        help='Migration file or directory to analyze'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    parser.add_argument(
        '--dir',
        action='store_true',
        help='Analyze all SQL files in directory'
    )

    parser.add_argument(
        '--severity',
        choices=['error', 'warning', 'info'],
        help='Filter by minimum severity level'
    )

    args = parser.parse_args()

    # Validate path
    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    # Analyze
    analyzer = MigrationAnalyzer()

    if args.dir or args.path.is_dir():
        if not args.path.is_dir():
            print(f"Error: --dir specified but path is not a directory", file=sys.stderr)
            sys.exit(1)
        results = analyzer.analyze_directory(args.path)
    else:
        results = [analyzer.analyze_file(args.path)]

    # Filter by severity if requested
    if args.severity:
        severity_levels = {
            'error': [Severity.ERROR],
            'warning': [Severity.ERROR, Severity.WARNING],
            'info': [Severity.ERROR, Severity.WARNING, Severity.INFO]
        }
        allowed_severities = severity_levels[args.severity]

        for result in results:
            result.issues = [i for i in result.issues if i.severity in allowed_severities]

    # Output
    if args.json:
        output = {
            'results': [result.to_dict() for result in results],
            'summary': {
                'total_files': len(results),
                'safe_files': sum(1 for r in results if r.safe),
                'total_errors': sum(r.summary['errors'] for r in results),
                'total_warnings': sum(r.summary['warnings'] for r in results),
                'total_info': sum(r.summary['info'] for r in results),
            }
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_text_output(results))

    # Exit code: 0 if all safe, 1 if any unsafe
    sys.exit(0 if all(r.safe for r in results) else 1)


if __name__ == '__main__':
    main()
