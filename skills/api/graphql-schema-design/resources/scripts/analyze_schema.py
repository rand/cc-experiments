#!/usr/bin/env python3
"""
GraphQL Schema Analyzer

Analyzes GraphQL schemas for anti-patterns, complexity issues, and best practices.
Provides actionable recommendations for schema improvements.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, List, Dict


class Severity(Enum):
    """Issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    """Schema issue"""
    severity: Severity
    category: str
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class SchemaStats:
    """Schema statistics"""
    total_types: int = 0
    object_types: int = 0
    interface_types: int = 0
    union_types: int = 0
    enum_types: int = 0
    input_types: int = 0
    scalar_types: int = 0
    query_fields: int = 0
    mutation_fields: int = 0
    subscription_fields: int = 0
    deprecated_fields: int = 0
    total_fields: int = 0
    documented_types: int = 0
    documented_fields: int = 0


@dataclass
class AnalysisResult:
    """Complete analysis result"""
    stats: SchemaStats
    issues: List[Issue] = field(default_factory=list)
    score: float = 0.0


class SchemaAnalyzer:
    """Analyze GraphQL schema for issues"""

    def __init__(self, schema_content: str):
        self.schema = schema_content
        self.lines = schema_content.split('\n')
        self.stats = SchemaStats()
        self.issues: List[Issue] = []

    def analyze(self) -> AnalysisResult:
        """Run all analysis checks"""
        self._analyze_types()
        self._check_naming_conventions()
        self._check_documentation()
        self._check_pagination()
        self._check_nullability()
        self._check_list_patterns()
        self._check_mutation_patterns()
        self._check_error_handling()
        self._check_deprecated_usage()
        self._calculate_score()

        return AnalysisResult(
            stats=self.stats,
            issues=self.issues,
            score=self._calculate_score()
        )

    def _analyze_types(self):
        """Analyze type definitions and count them"""
        patterns = {
            'object': (r'^\s*type\s+(\w+)', 'object_types'),
            'interface': (r'^\s*interface\s+(\w+)', 'interface_types'),
            'union': (r'^\s*union\s+(\w+)', 'union_types'),
            'enum': (r'^\s*enum\s+(\w+)', 'enum_types'),
            'input': (r'^\s*input\s+(\w+)', 'input_types'),
            'scalar': (r'^\s*scalar\s+(\w+)', 'scalar_types'),
        }

        for line_num, line in enumerate(self.lines, 1):
            # Count types
            for type_name, (pattern, stat_name) in patterns.items():
                match = re.match(pattern, line)
                if match:
                    setattr(self.stats, stat_name, getattr(self.stats, stat_name) + 1)
                    self.stats.total_types += 1

            # Count fields
            if re.match(r'^\s+\w+.*:', line):
                self.stats.total_fields += 1

                # Check for documentation
                if line_num > 1 and '"""' in self.lines[line_num - 2]:
                    self.stats.documented_fields += 1

            # Count Query/Mutation/Subscription fields
            if re.match(r'^\s*type\s+Query', line):
                self._count_operation_fields('Query', line_num)
            elif re.match(r'^\s*type\s+Mutation', line):
                self._count_operation_fields('Mutation', line_num)
            elif re.match(r'^\s*type\s+Subscription', line):
                self._count_operation_fields('Subscription', line_num)

            # Count deprecated fields
            if '@deprecated' in line:
                self.stats.deprecated_fields += 1

    def _count_operation_fields(self, operation: str, start_line: int):
        """Count fields in Query/Mutation/Subscription types"""
        depth = 0
        for line_num in range(start_line, len(self.lines)):
            line = self.lines[line_num]

            if '{' in line:
                depth += 1
            if '}' in line:
                depth -= 1
                if depth == 0:
                    break

            if depth > 0 and re.match(r'^\s+\w+.*:', line):
                if operation == 'Query':
                    self.stats.query_fields += 1
                elif operation == 'Mutation':
                    self.stats.mutation_fields += 1
                elif operation == 'Subscription':
                    self.stats.subscription_fields += 1

    def _check_naming_conventions(self):
        """Check naming convention compliance"""
        for line_num, line in enumerate(self.lines, 1):
            # Type names should be PascalCase
            match = re.match(r'^\s*(?:type|interface|union|enum|input)\s+(\w+)', line)
            if match:
                type_name = match.group(1)
                if not re.match(r'^[A-Z][a-zA-Z0-9]*$', type_name):
                    self.issues.append(Issue(
                        severity=Severity.WARNING,
                        category='naming',
                        message=f"Type '{type_name}' should be PascalCase",
                        line=line_num,
                        suggestion=f"Rename to {self._to_pascal_case(type_name)}"
                    ))

            # Field names should be camelCase
            match = re.match(r'^\s+(\w+)\s*[\(:]', line)
            if match:
                field_name = match.group(1)
                if '_' in field_name:
                    self.issues.append(Issue(
                        severity=Severity.WARNING,
                        category='naming',
                        message=f"Field '{field_name}' should be camelCase (no underscores)",
                        line=line_num,
                        suggestion=f"Rename to {self._to_camel_case(field_name)}"
                    ))

            # Enum values should be SCREAMING_SNAKE_CASE
            if re.match(r'^\s*enum\s+', line):
                in_enum = True
                enum_start = line_num
            elif 'in_enum' in locals() and in_enum:
                if '}' in line:
                    in_enum = False
                else:
                    match = re.match(r'^\s+([A-Z_]+)', line)
                    if match:
                        enum_value = match.group(1)
                        if not re.match(r'^[A-Z][A-Z0-9_]*$', enum_value):
                            self.issues.append(Issue(
                                severity=Severity.WARNING,
                                category='naming',
                                message=f"Enum value '{enum_value}' should be SCREAMING_SNAKE_CASE",
                                line=line_num,
                                suggestion=f"Rename to {self._to_screaming_snake_case(enum_value)}"
                            ))

    def _check_documentation(self):
        """Check documentation coverage"""
        type_pattern = re.compile(r'^\s*(?:type|interface|union|enum|input)\s+(\w+)')
        field_pattern = re.compile(r'^\s+\w+.*:')

        prev_line_doc = False
        for line_num, line in enumerate(self.lines, 1):
            # Check if previous line was documentation
            if line_num > 1:
                prev_line_doc = '"""' in self.lines[line_num - 2]

            # Type without documentation
            if type_pattern.match(line):
                if not prev_line_doc:
                    self.issues.append(Issue(
                        severity=Severity.INFO,
                        category='documentation',
                        message=f"Type at line {line_num} lacks documentation",
                        line=line_num,
                        suggestion='Add """ description """ above type definition'
                    ))
                else:
                    self.stats.documented_types += 1

    def _check_pagination(self):
        """Check pagination patterns"""
        for line_num, line in enumerate(self.lines, 1):
            # Check for list fields without pagination
            match = re.search(r'(\w+)\s*(?:\([^)]*\))?\s*:\s*\[(\w+)!?\]!?', line)
            if match:
                field_name = match.group(1)
                type_name = match.group(2)

                # Skip if it's in a Connection type or has pagination args
                if 'Connection' in type_name or 'Edge' in type_name:
                    continue

                # Check for pagination arguments
                has_pagination = any(
                    arg in line for arg in ['first', 'after', 'last', 'before', 'limit', 'offset']
                )

                if not has_pagination and field_name not in ['edges', 'nodes']:
                    self.issues.append(Issue(
                        severity=Severity.WARNING,
                        category='pagination',
                        message=f"List field '{field_name}' lacks pagination",
                        line=line_num,
                        suggestion='Use Connection pattern or add first/after arguments'
                    ))

    def _check_nullability(self):
        """Check nullability patterns"""
        for line_num, line in enumerate(self.lines, 1):
            # Non-null list of nullable items: [Item]!
            if re.search(r':\s*\[(\w+)\]!', line):
                self.issues.append(Issue(
                    severity=Severity.INFO,
                    category='nullability',
                    message='Non-null list with nullable items',
                    line=line_num,
                    suggestion='Consider [Item!]! to guarantee non-null items'
                ))

    def _check_list_patterns(self):
        """Check list return patterns"""
        in_query = False
        for line_num, line in enumerate(self.lines, 1):
            if re.match(r'^\s*type\s+Query', line):
                in_query = True
            elif re.match(r'^\s*type\s+\w+', line):
                in_query = False

            if in_query and re.search(r':\s*\[.*\]', line):
                # Check if it's a connection or has pagination
                if 'Connection' not in line and not any(
                    arg in line for arg in ['first', 'after', 'limit']
                ):
                    self.issues.append(Issue(
                        severity=Severity.ERROR,
                        category='performance',
                        message='Query returns unbounded list',
                        line=line_num,
                        suggestion='Use Connection pattern or add pagination arguments'
                    ))

    def _check_mutation_patterns(self):
        """Check mutation design patterns"""
        in_mutation = False
        for line_num, line in enumerate(self.lines, 1):
            if re.match(r'^\s*type\s+Mutation', line):
                in_mutation = True
            elif re.match(r'^\s*type\s+\w+', line):
                in_mutation = False

            if in_mutation:
                match = re.match(r'^\s+(\w+)\s*\(', line)
                if match:
                    mutation_name = match.group(1)

                    # Check for input argument
                    if 'input:' not in line:
                        self.issues.append(Issue(
                            severity=Severity.WARNING,
                            category='mutations',
                            message=f"Mutation '{mutation_name}' should use input type",
                            line=line_num,
                            suggestion='Use input: CreateXInput! pattern'
                        ))

                    # Check for payload return type
                    if 'Payload' not in line and 'Result' not in line:
                        self.issues.append(Issue(
                            severity=Severity.WARNING,
                            category='mutations',
                            message=f"Mutation '{mutation_name}' should return Payload type",
                            line=line_num,
                            suggestion='Return XPayload type with success/errors fields'
                        ))

    def _check_error_handling(self):
        """Check error handling patterns"""
        has_error_type = any('Error' in line for line in self.lines)
        has_payload_errors = any('errors:' in line for line in self.lines)

        if self.stats.mutation_fields > 0 and not has_error_type:
            self.issues.append(Issue(
                severity=Severity.WARNING,
                category='error-handling',
                message='Schema lacks error types',
                suggestion='Define Error interface and concrete error types'
            ))

        if self.stats.mutation_fields > 0 and not has_payload_errors:
            self.issues.append(Issue(
                severity=Severity.WARNING,
                category='error-handling',
                message='Mutation payloads lack errors field',
                suggestion='Add errors: [Error!] field to payload types'
            ))

    def _check_deprecated_usage(self):
        """Check deprecated field usage"""
        for line_num, line in enumerate(self.lines, 1):
            if '@deprecated' in line:
                # Check if reason is provided
                if 'reason:' not in line:
                    self.issues.append(Issue(
                        severity=Severity.WARNING,
                        category='deprecation',
                        message='@deprecated directive lacks reason',
                        line=line_num,
                        suggestion='Add reason: "explanation" to @deprecated'
                    ))

    def _calculate_score(self) -> float:
        """Calculate overall schema quality score (0-100)"""
        score = 100.0

        # Deduct for issues
        for issue in self.issues:
            if issue.severity == Severity.ERROR:
                score -= 5.0
            elif issue.severity == Severity.WARNING:
                score -= 2.0
            elif issue.severity == Severity.INFO:
                score -= 0.5

        # Bonus for documentation
        if self.stats.total_types > 0:
            doc_ratio = self.stats.documented_types / self.stats.total_types
            score += doc_ratio * 10

        # Bonus for proper patterns
        if any('Connection' in line for line in self.lines):
            score += 5
        if any('Payload' in line for line in self.lines):
            score += 5

        return max(0.0, min(100.0, score))

    @staticmethod
    def _to_pascal_case(s: str) -> str:
        """Convert to PascalCase"""
        return ''.join(word.capitalize() for word in re.split(r'[_\s]+', s))

    @staticmethod
    def _to_camel_case(s: str) -> str:
        """Convert to camelCase"""
        words = re.split(r'[_\s]+', s)
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:])

    @staticmethod
    def _to_screaming_snake_case(s: str) -> str:
        """Convert to SCREAMING_SNAKE_CASE"""
        # Insert underscores before capitals
        s = re.sub(r'([a-z])([A-Z])', r'\1_\2', s)
        return s.upper()


def format_human_output(result: AnalysisResult) -> str:
    """Format analysis result for human reading"""
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("GraphQL Schema Analysis Report")
    lines.append("=" * 60)
    lines.append("")

    # Score
    lines.append(f"Overall Score: {result.score:.1f}/100")
    lines.append("")

    # Statistics
    lines.append("Schema Statistics:")
    lines.append(f"  Total Types: {result.stats.total_types}")
    lines.append(f"    - Object Types: {result.stats.object_types}")
    lines.append(f"    - Interface Types: {result.stats.interface_types}")
    lines.append(f"    - Union Types: {result.stats.union_types}")
    lines.append(f"    - Enum Types: {result.stats.enum_types}")
    lines.append(f"    - Input Types: {result.stats.input_types}")
    lines.append(f"    - Scalar Types: {result.stats.scalar_types}")
    lines.append("")
    lines.append(f"  Total Fields: {result.stats.total_fields}")
    lines.append(f"    - Query Fields: {result.stats.query_fields}")
    lines.append(f"    - Mutation Fields: {result.stats.mutation_fields}")
    lines.append(f"    - Subscription Fields: {result.stats.subscription_fields}")
    lines.append(f"    - Deprecated Fields: {result.stats.deprecated_fields}")
    lines.append("")

    # Documentation coverage
    if result.stats.total_types > 0:
        doc_pct = (result.stats.documented_types / result.stats.total_types) * 100
        lines.append(f"  Documentation Coverage: {doc_pct:.1f}%")
        lines.append("")

    # Issues
    if result.issues:
        lines.append("Issues Found:")
        lines.append("")

        # Group by severity
        errors = [i for i in result.issues if i.severity == Severity.ERROR]
        warnings = [i for i in result.issues if i.severity == Severity.WARNING]
        infos = [i for i in result.issues if i.severity == Severity.INFO]

        for severity_name, issues in [
            ("ERRORS", errors),
            ("WARNINGS", warnings),
            ("INFO", infos)
        ]:
            if issues:
                lines.append(f"{severity_name} ({len(issues)}):")
                for issue in issues:
                    location = f"Line {issue.line}" if issue.line else "Schema"
                    lines.append(f"  [{issue.category}] {location}: {issue.message}")
                    if issue.suggestion:
                        lines.append(f"    → {issue.suggestion}")
                lines.append("")
    else:
        lines.append("No issues found!")
        lines.append("")

    return '\n'.join(lines)


def format_json_output(result: AnalysisResult) -> str:
    """Format analysis result as JSON"""
    return json.dumps({
        'score': result.score,
        'stats': {
            'total_types': result.stats.total_types,
            'object_types': result.stats.object_types,
            'interface_types': result.stats.interface_types,
            'union_types': result.stats.union_types,
            'enum_types': result.stats.enum_types,
            'input_types': result.stats.input_types,
            'scalar_types': result.stats.scalar_types,
            'query_fields': result.stats.query_fields,
            'mutation_fields': result.stats.mutation_fields,
            'subscription_fields': result.stats.subscription_fields,
            'deprecated_fields': result.stats.deprecated_fields,
            'total_fields': result.stats.total_fields,
            'documented_types': result.stats.documented_types,
            'documented_fields': result.stats.documented_fields,
        },
        'issues': [
            {
                'severity': issue.severity.value,
                'category': issue.category,
                'message': issue.message,
                'line': issue.line,
                'suggestion': issue.suggestion,
            }
            for issue in result.issues
        ]
    }, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze GraphQL schema for anti-patterns and best practices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s schema.graphql
  %(prog)s schema.graphql --json
  %(prog)s schema.graphql --min-score 80
  cat schema.graphql | %(prog)s -
        """
    )

    parser.add_argument(
        'schema_file',
        help='GraphQL schema file (use - for stdin)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )
    parser.add_argument(
        '--min-score',
        type=float,
        default=0,
        help='Minimum score to pass (exit 1 if below)'
    )

    args = parser.parse_args()

    # Read schema
    try:
        if args.schema_file == '-':
            schema_content = sys.stdin.read()
        else:
            schema_path = Path(args.schema_file)
            if not schema_path.exists():
                print(f"Error: File not found: {args.schema_file}", file=sys.stderr)
                return 1
            schema_content = schema_path.read_text()
    except Exception as e:
        print(f"Error reading schema: {e}", file=sys.stderr)
        return 1

    # Analyze
    analyzer = SchemaAnalyzer(schema_content)
    result = analyzer.analyze()

    # Output
    if args.json:
        print(format_json_output(result))
    else:
        print(format_human_output(result))

    # Check minimum score
    if result.score < args.min_score:
        print(f"\nScore {result.score:.1f} is below minimum {args.min_score}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
