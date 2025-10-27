#!/usr/bin/env python3
"""
PromQL Query Validator

Validates PromQL queries for syntax errors, best practices, and performance issues.
Can test queries against a live Prometheus server and detect common anti-patterns.

Usage:
    validate_promql.py --query 'rate(http_requests_total[5m])'
    validate_promql.py --file queries.txt
    validate_promql.py --query 'sum(rate(http_requests_total[5m]))' --url http://localhost:9090
    validate_promql.py --file queries.txt --json
"""

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin
import urllib.request
import urllib.error


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: str  # error, warning, info
    category: str  # syntax, performance, best_practice
    message: str
    suggestion: Optional[str] = None
    line: Optional[int] = None


@dataclass
class QueryMetrics:
    """Metrics about query execution."""
    execution_time_seconds: float
    result_series_count: int
    result_samples_count: int


@dataclass
class ValidationResult:
    """Result of query validation."""
    query: str
    valid: bool
    issues: List[ValidationIssue]
    metrics: Optional[QueryMetrics] = None


class PrometheusClient:
    """Client for Prometheus API."""

    def __init__(self, url: str, timeout: int = 30):
        self.url = url.rstrip('/')
        self.timeout = timeout

    def query(self, query: str) -> Tuple[dict, float]:
        """Execute PromQL query and return result with execution time."""
        url = urljoin(self.url, '/api/v1/query')
        params = urllib.parse.urlencode({'query': query})
        full_url = f"{url}?{params}"

        start_time = time.time()
        try:
            with urllib.request.urlopen(full_url, timeout=self.timeout) as response:
                execution_time = time.time() - start_time
                data = json.loads(response.read().decode())

                if data['status'] != 'success':
                    error_msg = data.get('error', 'Unknown error')
                    raise Exception(f"Query failed: {error_msg}")

                return data['data'], execution_time

        except urllib.error.URLError as e:
            raise Exception(f"Failed to connect to Prometheus: {e}")

    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate query syntax without executing it."""
        # Prometheus doesn't have a dedicated validation endpoint,
        # so we use the query API with a short timeout
        try:
            self.query(query)
            return True, None
        except Exception as e:
            return False, str(e)


class PromQLValidator:
    """Validates PromQL queries for syntax and best practices."""

    # Common aggregation operators
    AGGREGATION_OPS = {
        'sum', 'avg', 'min', 'max', 'count', 'stddev', 'stdvar',
        'topk', 'bottomk', 'quantile', 'count_values'
    }

    # Range functions that require range vector
    RANGE_FUNCTIONS = {
        'rate', 'irate', 'increase', 'delta', 'idelta', 'deriv',
        'avg_over_time', 'min_over_time', 'max_over_time',
        'sum_over_time', 'count_over_time', 'quantile_over_time',
        'stddev_over_time', 'stdvar_over_time', 'changes', 'resets',
        'predict_linear', 'holt_winters'
    }

    # Instant functions
    INSTANT_FUNCTIONS = {
        'abs', 'ceil', 'floor', 'round', 'exp', 'ln', 'log2', 'log10',
        'sqrt', 'clamp', 'clamp_min', 'clamp_max', 'histogram_quantile',
        'label_replace', 'label_join', 'sort', 'sort_desc', 'time',
        'timestamp', 'vector', 'scalar', 'absent', 'absent_over_time'
    }

    def __init__(self, prometheus_url: Optional[str] = None):
        self.client = PrometheusClient(prometheus_url) if prometheus_url else None

    def validate_query(self, query: str, line_number: Optional[int] = None) -> ValidationResult:
        """Validate a single PromQL query."""
        issues = []

        # Basic syntax checks
        issues.extend(self._check_syntax(query, line_number))

        # Best practice checks
        issues.extend(self._check_best_practices(query, line_number))

        # Performance checks
        issues.extend(self._check_performance(query, line_number))

        # Server-side validation if client available
        metrics = None
        if self.client:
            valid, error = self.client.validate_query(query)
            if not valid:
                issues.append(ValidationIssue(
                    severity='error',
                    category='syntax',
                    message=f"Prometheus rejected query: {error}",
                    line=line_number
                ))
            else:
                # Execute and get metrics
                try:
                    data, execution_time = self.client.query(query)
                    result = data.get('result', [])

                    series_count = len(result)
                    samples_count = sum(len(r.get('values', [r.get('value', [])])) for r in result)

                    metrics = QueryMetrics(
                        execution_time_seconds=execution_time,
                        result_series_count=series_count,
                        result_samples_count=samples_count
                    )

                    # Check if query is slow
                    if execution_time > 5.0:
                        issues.append(ValidationIssue(
                            severity='warning',
                            category='performance',
                            message=f"Query took {execution_time:.2f}s to execute (> 5s)",
                            suggestion="Consider using recording rules or reducing time range",
                            line=line_number
                        ))

                except Exception:
                    pass  # Already added error above

        # Determine if query is valid (no errors)
        has_errors = any(issue.severity == 'error' for issue in issues)

        return ValidationResult(
            query=query,
            valid=not has_errors,
            issues=issues,
            metrics=metrics
        )

    def _check_syntax(self, query: str, line_number: Optional[int]) -> List[ValidationIssue]:
        """Check for syntax errors."""
        issues = []

        # Check for empty query
        if not query.strip():
            issues.append(ValidationIssue(
                severity='error',
                category='syntax',
                message="Query is empty",
                line=line_number
            ))
            return issues

        # Check for unmatched parentheses
        if query.count('(') != query.count(')'):
            issues.append(ValidationIssue(
                severity='error',
                category='syntax',
                message="Unmatched parentheses",
                line=line_number
            ))

        # Check for unmatched brackets
        if query.count('[') != query.count(']'):
            issues.append(ValidationIssue(
                severity='error',
                category='syntax',
                message="Unmatched brackets",
                line=line_number
            ))

        # Check for unmatched braces
        if query.count('{') != query.count('}'):
            issues.append(ValidationIssue(
                severity='error',
                category='syntax',
                message="Unmatched braces",
                line=line_number
            ))

        # Check for range vector without duration
        if '[' in query:
            # Find all range vectors
            range_vectors = re.findall(r'\[([^\]]+)\]', query)
            for rv in range_vectors:
                if not re.match(r'^\d+[smhdwy](:?\d+[smhdwy])?$', rv.strip()):
                    issues.append(ValidationIssue(
                        severity='error',
                        category='syntax',
                        message=f"Invalid range duration: [{rv}]",
                        suggestion="Use format like [5m], [1h], [30s]",
                        line=line_number
                    ))

        return issues

    def _check_best_practices(self, query: str, line_number: Optional[int]) -> List[ValidationIssue]:
        """Check for best practice violations."""
        issues = []

        # Check for missing rate() on counter
        counter_pattern = r'(\w+_total)(?!\[)'
        if re.search(counter_pattern, query):
            if 'rate(' not in query and 'increase(' not in query:
                issues.append(ValidationIssue(
                    severity='warning',
                    category='best_practice',
                    message="Counter metric without rate() or increase()",
                    suggestion="Use rate() or increase() with counter metrics",
                    line=line_number
                ))

        # Check for rate() without range vector
        if 'rate(' in query or 'irate(' in query:
            # Simple check: rate should be followed by something with [...]
            if not re.search(r'i?rate\([^)]*\[[^\]]+\]', query):
                issues.append(ValidationIssue(
                    severity='error',
                    category='syntax',
                    message="rate() requires a range vector (e.g., metric[5m])",
                    line=line_number
                ))

        # Check for irate() with large time range
        irate_pattern = r'irate\([^)]*\[(\d+)([smhdwy])\]'
        match = re.search(irate_pattern, query)
        if match:
            value, unit = match.groups()
            # Convert to seconds
            multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'y': 31536000}
            seconds = int(value) * multipliers[unit]

            if seconds > 300:  # > 5 minutes
                issues.append(ValidationIssue(
                    severity='warning',
                    category='best_practice',
                    message=f"irate() with long time range [{value}{unit}]",
                    suggestion="irate() should use short ranges (e.g., [1m]). Use rate() for longer ranges.",
                    line=line_number
                ))

        # Check for histogram_quantile without rate
        if 'histogram_quantile(' in query:
            if 'rate(' not in query and 'sum(' not in query:
                issues.append(ValidationIssue(
                    severity='warning',
                    category='best_practice',
                    message="histogram_quantile() should typically use rate() and aggregation",
                    suggestion="Use: histogram_quantile(0.95, sum(rate(metric_bucket[5m])) by (le))",
                    line=line_number
                ))

            # Check for missing 'by (le)'
            if 'by (le)' not in query and 'by(le)' not in query:
                issues.append(ValidationIssue(
                    severity='warning',
                    category='best_practice',
                    message="histogram_quantile() typically requires 'by (le)' grouping",
                    suggestion="Add 'by (le)' to histogram aggregation",
                    line=line_number
                ))

        # Check for overly broad regex
        if '=~".*"' in query or '=~".+"' in query:
            issues.append(ValidationIssue(
                severity='warning',
                category='performance',
                message="Overly broad regex match (.*  or .+)",
                suggestion="Use more specific regex or exact match when possible",
                line=line_number
            ))

        # Check for missing aggregation on multi-instance metrics
        if any(op in query for op in ['rate(', 'increase(', 'delta(']):
            if not any(agg in query for agg in self.AGGREGATION_OPS):
                issues.append(ValidationIssue(
                    severity='info',
                    category='best_practice',
                    message="No aggregation operator found",
                    suggestion="Consider using sum(), avg(), etc. to aggregate across instances",
                    line=line_number
                ))

        return issues

    def _check_performance(self, query: str, line_number: Optional[int]) -> List[ValidationIssue]:
        """Check for potential performance issues."""
        issues = []

        # Check for very long time ranges
        long_range_pattern = r'\[(\d+)([smhdwy])\]'
        for match in re.finditer(long_range_pattern, query):
            value, unit = match.groups()
            multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'y': 31536000}
            seconds = int(value) * multipliers[unit]

            if seconds > 86400 * 30:  # > 30 days
                issues.append(ValidationIssue(
                    severity='warning',
                    category='performance',
                    message=f"Very long time range [{value}{unit}]",
                    suggestion="Long time ranges can be slow. Consider using recording rules.",
                    line=line_number
                ))

        # Check for nested aggregations (can be slow)
        if query.count('sum(') > 1 or query.count('avg(') > 1:
            issues.append(ValidationIssue(
                severity='info',
                category='performance',
                message="Nested aggregations detected",
                suggestion="Nested aggregations can be slow. Consider using recording rules.",
                line=line_number
            ))

        # Check for complex regex in labels
        complex_regex_pattern = r'=~"[^"]{50,}"'
        if re.search(complex_regex_pattern, query):
            issues.append(ValidationIssue(
                severity='warning',
                category='performance',
                message="Complex regex pattern detected",
                suggestion="Simplify regex or use exact match for better performance",
                line=line_number
            ))

        # Check for multiple label filters (can create high cardinality)
        label_filter_count = len(re.findall(r'\w+\s*=~?\s*"[^"]+"', query))
        if label_filter_count > 5:
            issues.append(ValidationIssue(
                severity='info',
                category='performance',
                message=f"Many label filters ({label_filter_count})",
                suggestion="Too many filters can reduce query performance",
                line=line_number
            ))

        return issues


def format_human_readable(results: List[ValidationResult]) -> str:
    """Format validation results for human reading."""
    output = []

    output.append("=" * 80)
    output.append("PROMQL QUERY VALIDATION RESULTS")
    output.append("=" * 80)
    output.append("")

    total_queries = len(results)
    valid_queries = sum(1 for r in results if r.valid)
    total_issues = sum(len(r.issues) for r in results)

    output.append(f"Total Queries: {total_queries}")
    output.append(f"Valid: {valid_queries}")
    output.append(f"Invalid: {total_queries - valid_queries}")
    output.append(f"Total Issues: {total_issues}")
    output.append("")

    # Process each query
    for i, result in enumerate(results, 1):
        status = "✓ VALID" if result.valid else "✗ INVALID"
        output.append("=" * 80)
        output.append(f"Query {i}: {status}")
        output.append("=" * 80)
        output.append("")
        output.append(f"Query: {result.query}")
        output.append("")

        # Execution metrics
        if result.metrics:
            output.append("Execution Metrics:")
            output.append(f"  - Execution Time: {result.metrics.execution_time_seconds:.3f}s")
            output.append(f"  - Result Series: {result.metrics.result_series_count:,}")
            output.append(f"  - Result Samples: {result.metrics.result_samples_count:,}")
            output.append("")

        # Issues
        if result.issues:
            # Group by severity
            errors = [i for i in result.issues if i.severity == 'error']
            warnings = [i for i in result.issues if i.severity == 'warning']
            infos = [i for i in result.issues if i.severity == 'info']

            if errors:
                output.append("ERRORS:")
                for issue in errors:
                    output.append(f"  ✗ [{issue.category}] {issue.message}")
                    if issue.suggestion:
                        output.append(f"    → {issue.suggestion}")
                output.append("")

            if warnings:
                output.append("WARNINGS:")
                for issue in warnings:
                    output.append(f"  ⚠ [{issue.category}] {issue.message}")
                    if issue.suggestion:
                        output.append(f"    → {issue.suggestion}")
                output.append("")

            if infos:
                output.append("INFO:")
                for issue in infos:
                    output.append(f"  ℹ [{issue.category}] {issue.message}")
                    if issue.suggestion:
                        output.append(f"    → {issue.suggestion}")
                output.append("")
        else:
            output.append("No issues found.")
            output.append("")

    output.append("=" * 80)

    return '\n'.join(output)


def format_json(results: List[ValidationResult]) -> str:
    """Format validation results as JSON."""
    data = {
        'summary': {
            'total_queries': len(results),
            'valid_queries': sum(1 for r in results if r.valid),
            'total_issues': sum(len(r.issues) for r in results)
        },
        'results': [
            {
                'query': r.query,
                'valid': r.valid,
                'issues': [
                    {
                        'severity': i.severity,
                        'category': i.category,
                        'message': i.message,
                        'suggestion': i.suggestion,
                        'line': i.line
                    }
                    for i in r.issues
                ],
                'metrics': {
                    'execution_time_seconds': r.metrics.execution_time_seconds,
                    'result_series_count': r.metrics.result_series_count,
                    'result_samples_count': r.metrics.result_samples_count
                } if r.metrics else None
            }
            for r in results
        ]
    }

    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Validate PromQL queries for syntax and best practices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate single query
  %(prog)s --query 'rate(http_requests_total[5m])'

  # Validate queries from file (one per line)
  %(prog)s --file queries.txt

  # Validate against Prometheus server
  %(prog)s --query 'sum(rate(http_requests_total[5m]))' --url http://localhost:9090

  # Output as JSON
  %(prog)s --file queries.txt --json
        """
    )

    parser.add_argument(
        '--query',
        help='PromQL query to validate'
    )

    parser.add_argument(
        '--file',
        help='File containing queries (one per line)'
    )

    parser.add_argument(
        '--url',
        help='Prometheus server URL for execution validation (e.g., http://localhost:9090)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Validate input
    if not args.query and not args.file:
        parser.error('Either --query or --file must be provided')

    try:
        # Initialize validator
        validator = PromQLValidator(prometheus_url=args.url)

        # Get queries
        queries = []
        if args.query:
            queries = [(args.query, None)]
        elif args.file:
            with open(args.file, 'r') as f:
                queries = [
                    (line.strip(), i + 1)
                    for i, line in enumerate(f)
                    if line.strip() and not line.strip().startswith('#')
                ]

        if not queries:
            print("No queries to validate", file=sys.stderr)
            sys.exit(1)

        # Validate queries
        results = []
        for query, line_number in queries:
            if args.url:
                print(f"Validating and executing query...", file=sys.stderr)
            else:
                print(f"Validating query...", file=sys.stderr)

            result = validator.validate_query(query, line_number)
            results.append(result)

        # Output
        if args.json:
            print(format_json(results))
        else:
            print(format_human_readable(results))

        # Exit with error if any query invalid
        if any(not r.valid for r in results):
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
