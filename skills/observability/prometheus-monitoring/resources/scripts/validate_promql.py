#!/usr/bin/env python3
"""
PromQL Query Validator

Validates PromQL queries for:
- Syntax correctness
- Common anti-patterns
- Performance issues
- Best practices
- Query execution against Prometheus

Usage:
    ./validate_promql.py --query 'rate(http_requests_total[5m])'
    ./validate_promql.py --query 'sum by (job) (rate(http_requests_total[5m]))' --url http://localhost:9090
    ./validate_promql.py --rules-file rules.yml --url http://localhost:9090 --json
"""

import argparse
import json
import sys
import re
from typing import Dict, List, Tuple
from urllib.parse import urljoin
import requests
import yaml
import time


class PromQLValidator:
    """Validate PromQL queries."""

    def __init__(self, prometheus_url: str = None):
        self.prometheus_url = prometheus_url
        self.issues = []
        self.warnings = []
        self.suggestions = []
        self.stats = {}

    def validate_syntax(self, query: str) -> bool:
        """Validate PromQL syntax using Prometheus API."""
        if not self.prometheus_url:
            # Basic syntax validation without Prometheus
            return self.validate_syntax_basic(query)

        try:
            # Use Prometheus query API to validate syntax
            url = urljoin(self.prometheus_url, '/api/v1/query')
            params = {'query': query, 'time': int(time.time())}
            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            if data['status'] == 'success':
                return True
            else:
                error = data.get('error', 'Unknown error')
                self.issues.append({
                    'type': 'syntax',
                    'severity': 'error',
                    'message': f'Syntax error: {error}',
                    'query': query
                })
                return False

        except Exception as e:
            self.issues.append({
                'type': 'validation',
                'severity': 'error',
                'message': f'Failed to validate syntax: {e}',
                'query': query
            })
            return False

    def validate_syntax_basic(self, query: str) -> bool:
        """Basic syntax validation without Prometheus."""
        # Check for balanced parentheses
        if query.count('(') != query.count(')'):
            self.issues.append({
                'type': 'syntax',
                'severity': 'error',
                'message': 'Unbalanced parentheses',
                'query': query
            })
            return False

        # Check for balanced brackets
        if query.count('[') != query.count(']'):
            self.issues.append({
                'type': 'syntax',
                'severity': 'error',
                'message': 'Unbalanced brackets',
                'query': query
            })
            return False

        # Check for balanced braces
        if query.count('{') != query.count('}'):
            self.issues.append({
                'type': 'syntax',
                'severity': 'error',
                'message': 'Unbalanced braces',
                'query': query
            })
            return False

        return True

    def check_anti_patterns(self, query: str):
        """Check for common anti-patterns."""

        # Anti-pattern: rate() without range
        if 'rate(' in query and '[' not in query:
            self.issues.append({
                'type': 'anti-pattern',
                'severity': 'error',
                'message': 'rate() requires a range vector (e.g., rate(metric[5m]))',
                'query': query
            })

        # Anti-pattern: rate() on gauge
        gauge_patterns = ['gauge', 'temperature', 'usage', 'utilization', 'available', 'free']
        if 'rate(' in query:
            for pattern in gauge_patterns:
                if pattern in query.lower():
                    self.warnings.append({
                        'type': 'anti-pattern',
                        'severity': 'warning',
                        'message': f'rate() typically used on counters, not gauges (found "{pattern}")',
                        'query': query,
                        'suggestion': 'Use delta() or deriv() for gauges'
                    })
                    break

        # Anti-pattern: increase() then divide
        if 'increase(' in query and '/' in query:
            self.warnings.append({
                'type': 'anti-pattern',
                'severity': 'warning',
                'message': 'Using increase() then dividing - consider using rate() instead',
                'query': query,
                'suggestion': 'rate() calculates per-second rate directly'
            })

        # Anti-pattern: Unnecessary regex
        if '=~"' in query:
            # Check for simple equality that could be exact match
            regex_patterns = re.findall(r'=~"([^"]+)"', query)
            for pattern in regex_patterns:
                if not any(char in pattern for char in ['.*', '.+', '|', '^', '$', '[', ']', '(', ')']):
                    self.warnings.append({
                        'type': 'performance',
                        'severity': 'warning',
                        'message': f'Regex "{pattern}" can be replaced with exact match',
                        'query': query,
                        'suggestion': f'Use =\"{pattern}\" instead of =~\"{pattern}\"'
                    })

        # Anti-pattern: Very long range vectors
        range_vectors = re.findall(r'\[(\d+)([dhm])\]', query)
        for value, unit in range_vectors:
            value = int(value)
            if (unit == 'd' and value > 7) or (unit == 'h' and value > 168):
                self.warnings.append({
                    'type': 'performance',
                    'severity': 'warning',
                    'message': f'Very long range vector [{value}{unit}] may cause slow queries',
                    'query': query,
                    'suggestion': 'Consider using recording rules for long-term aggregations'
                })

        # Anti-pattern: Aggregation without labels
        aggregations = ['sum', 'avg', 'min', 'max', 'count']
        for agg in aggregations:
            if f'{agg}(' in query and ' by ' not in query and ' without ' not in query:
                # Check if it's not already aggregated (simple heuristic)
                if not query.strip().startswith(f'{agg}(') or query.count(agg) > 1:
                    self.suggestions.append({
                        'type': 'best-practice',
                        'message': f'{agg}() without "by" or "without" clause',
                        'query': query,
                        'suggestion': f'Consider using "by (label)" to preserve useful dimensions'
                    })

        # Anti-pattern: histogram_quantile without rate
        if 'histogram_quantile(' in query and 'rate(' not in query and 'increase(' not in query:
            self.issues.append({
                'type': 'anti-pattern',
                'severity': 'error',
                'message': 'histogram_quantile() should be used with rate() or increase()',
                'query': query,
                'suggestion': 'Use histogram_quantile(φ, rate(metric_bucket[5m]))'
            })

        # Anti-pattern: Missing le label in histogram_quantile
        if 'histogram_quantile(' in query and ' by ' in query:
            by_match = re.search(r'by\s*\(([^)]+)\)', query)
            if by_match:
                labels = [l.strip() for l in by_match.group(1).split(',')]
                if 'le' not in labels:
                    self.issues.append({
                        'type': 'anti-pattern',
                        'severity': 'error',
                        'message': 'histogram_quantile() "by" clause must include "le" label',
                        'query': query,
                        'suggestion': f'Add "le" to by clause: by ({", ".join(labels + ["le"])})'
                    })

    def check_performance(self, query: str):
        """Check for potential performance issues."""

        # Check for high cardinality operations
        if re.search(r'\{[^}]*\}', query):
            # Count label filters
            label_filters = len(re.findall(r'\w+\s*[=!]~?\s*"[^"]+"', query))
            if label_filters == 0:
                self.warnings.append({
                    'type': 'performance',
                    'severity': 'warning',
                    'message': 'Query without label filters may be slow',
                    'query': query,
                    'suggestion': 'Add label filters to reduce time series scanned'
                })

        # Check for OR conditions (can be slow)
        if '|' in query and '=~' in query:
            self.suggestions.append({
                'type': 'performance',
                'message': 'Using OR in regex can be slow for high cardinality',
                'query': query,
                'suggestion': 'Consider splitting into multiple queries if possible'
            })

        # Check for multiple aggregations
        aggregation_count = sum(query.count(agg + '(') for agg in ['sum', 'avg', 'min', 'max', 'count', 'topk', 'bottomk'])
        if aggregation_count > 3:
            self.warnings.append({
                'type': 'performance',
                'severity': 'warning',
                'message': f'Query has {aggregation_count} aggregation functions',
                'query': query,
                'suggestion': 'Complex aggregations may be slow - consider using recording rules'
            })

    def execute_query(self, query: str) -> Dict:
        """Execute query against Prometheus and measure performance."""
        if not self.prometheus_url:
            return {}

        try:
            url = urljoin(self.prometheus_url, '/api/v1/query')
            params = {'query': query, 'time': int(time.time())}

            start_time = time.time()
            response = requests.get(url, params=params, timeout=30)
            duration = time.time() - start_time

            data = response.json()

            if data['status'] != 'success':
                return {'error': data.get('error', 'Unknown error')}

            result = data['data']['result']
            result_count = len(result)

            stats = {
                'duration_seconds': round(duration, 3),
                'result_count': result_count,
                'result_type': data['data']['resultType']
            }

            # Warn on slow queries
            if duration > 5.0:
                self.warnings.append({
                    'type': 'performance',
                    'severity': 'warning',
                    'message': f'Slow query execution: {duration:.2f}s',
                    'query': query,
                    'suggestion': 'Consider optimizing or using recording rules'
                })

            # Warn on large result sets
            if result_count > 1000:
                self.warnings.append({
                    'type': 'performance',
                    'severity': 'warning',
                    'message': f'Large result set: {result_count} time series',
                    'query': query,
                    'suggestion': 'Add more label filters or aggregation'
                })

            return stats

        except Exception as e:
            return {'error': str(e)}

    def validate_query(self, query: str) -> Dict:
        """Validate a single query."""
        self.issues = []
        self.warnings = []
        self.suggestions = []
        self.stats = {}

        # Syntax validation
        if not self.validate_syntax(query):
            return self.get_results(query)

        # Check anti-patterns
        self.check_anti_patterns(query)

        # Check performance
        self.check_performance(query)

        # Execute query if Prometheus URL provided
        if self.prometheus_url:
            execution_stats = self.execute_query(query)
            self.stats = execution_stats

        return self.get_results(query)

    def validate_rules_file(self, rules_file: str) -> List[Dict]:
        """Validate all queries in a rules file."""
        results = []

        try:
            with open(rules_file, 'r') as f:
                rules = yaml.safe_load(f)

            groups = rules.get('groups', [])
            for group in groups:
                group_name = group.get('name', 'unknown')
                rules_list = group.get('rules', [])

                for idx, rule in enumerate(rules_list):
                    expr = rule.get('expr', '')
                    rule_name = rule.get('record') or rule.get('alert') or f'rule_{idx}'

                    result = self.validate_query(expr)
                    result['rule_name'] = rule_name
                    result['group'] = group_name
                    results.append(result)

        except Exception as e:
            results.append({
                'error': f'Failed to load rules file: {e}',
                'file': rules_file
            })

        return results

    def get_results(self, query: str) -> Dict:
        """Get validation results."""
        return {
            'query': query,
            'valid': len(self.issues) == 0,
            'issues': self.issues,
            'warnings': self.warnings,
            'suggestions': self.suggestions,
            'stats': self.stats
        }

    def format_results(self, results: Dict, output_json: bool = False) -> str:
        """Format validation results."""
        if output_json:
            return json.dumps(results, indent=2)

        # Text format
        output = []
        output.append("=" * 80)
        output.append("PromQL Validation Results")
        output.append("=" * 80)

        if isinstance(results, list):
            # Multiple queries (from rules file)
            total = len(results)
            valid = sum(1 for r in results if r.get('valid', False))
            output.append(f"\nValidated {total} queries: {valid} valid, {total - valid} with issues")

            for result in results:
                if not result.get('valid', False):
                    output.append(f"\n{result.get('rule_name', 'unknown')} ({result.get('group', 'unknown')}):")
                    output.append(f"  Query: {result.get('query', 'N/A')}")

                    for issue in result.get('issues', []):
                        output.append(f"  ✗ ERROR: {issue['message']}")

                    for warning in result.get('warnings', []):
                        output.append(f"  ⚠ WARNING: {warning['message']}")

        else:
            # Single query
            output.append(f"\nQuery: {results['query']}")
            output.append(f"Valid: {'✓ Yes' if results['valid'] else '✗ No'}")

            if results['stats']:
                output.append("\nExecution Stats:")
                for key, value in results['stats'].items():
                    output.append(f"  {key}: {value}")

            if results['issues']:
                output.append("\nIssues:")
                for issue in results['issues']:
                    output.append(f"  ✗ {issue['message']}")
                    if 'suggestion' in issue:
                        output.append(f"    → {issue['suggestion']}")

            if results['warnings']:
                output.append("\nWarnings:")
                for warning in results['warnings']:
                    output.append(f"  ⚠ {warning['message']}")
                    if 'suggestion' in warning:
                        output.append(f"    → {warning['suggestion']}")

            if results['suggestions']:
                output.append("\nSuggestions:")
                for suggestion in results['suggestions']:
                    output.append(f"  💡 {suggestion['message']}")
                    if 'suggestion' in suggestion:
                        output.append(f"    → {suggestion['suggestion']}")

        output.append("\n" + "=" * 80)

        return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Validate PromQL queries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single query
  ./validate_promql.py --query 'rate(http_requests_total[5m])'

  # Validate against Prometheus
  ./validate_promql.py --query 'sum by (job) (rate(http_requests_total[5m]))' --url http://localhost:9090

  # Validate rules file
  ./validate_promql.py --rules-file rules.yml --url http://localhost:9090

  # JSON output
  ./validate_promql.py --query 'histogram_quantile(0.95, rate(latency_bucket[5m]))' --json
        """
    )

    parser.add_argument(
        '--query',
        type=str,
        help='PromQL query to validate'
    )

    parser.add_argument(
        '--rules-file',
        type=str,
        help='Path to rules file (recording/alerting rules)'
    )

    parser.add_argument(
        '--url',
        type=str,
        help='Prometheus URL (e.g., http://localhost:9090)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    args = parser.parse_args()

    if not args.query and not args.rules_file:
        parser.print_help()
        print("\nError: Must specify either --query or --rules-file")
        sys.exit(1)

    validator = PromQLValidator(prometheus_url=args.url)

    try:
        if args.query:
            results = validator.validate_query(args.query)
            print(validator.format_results(results, output_json=args.json))
            sys.exit(0 if results['valid'] else 1)

        elif args.rules_file:
            results = validator.validate_rules_file(args.rules_file)
            print(validator.format_results(results, output_json=args.json))

            # Exit with error if any query invalid
            invalid_count = sum(1 for r in results if not r.get('valid', False))
            sys.exit(1 if invalid_count > 0 else 0)

    except KeyboardInterrupt:
        print("\nValidation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
