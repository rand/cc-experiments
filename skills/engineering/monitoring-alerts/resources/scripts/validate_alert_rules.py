#!/usr/bin/env python3
"""
Validate Prometheus Alert Rules

This script validates Prometheus alert rule files for syntax correctness,
best practices, and common anti-patterns.

Usage:
    validate_alert_rules.py --file alerts.yml
    validate_alert_rules.py --dir /etc/prometheus/alerts/
    validate_alert_rules.py --file alerts.yml --json
    validate_alert_rules.py --file alerts.yml --prometheus http://localhost:9090
"""

import argparse
import sys
import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
import requests
from datetime import timedelta


class AlertRuleValidator:
    """Validates Prometheus alert rules."""

    def __init__(self, prometheus_url: str = None):
        self.prometheus_url = prometheus_url
        self.errors = []
        self.warnings = []
        self.info = []

    def validate_file(self, filepath: Path) -> Dict[str, Any]:
        """Validate a single alert rule file."""
        try:
            with open(filepath) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return {
                'file': str(filepath),
                'valid': False,
                'errors': [f'YAML parse error: {e}'],
                'warnings': [],
                'info': []
            }
        except Exception as e:
            return {
                'file': str(filepath),
                'valid': False,
                'errors': [f'Failed to read file: {e}'],
                'warnings': [],
                'info': []
            }

        self.errors = []
        self.warnings = []
        self.info = []

        # Validate structure
        if not isinstance(data, dict):
            self.errors.append('Root element must be a dictionary')
            return self._result(filepath)

        if 'groups' not in data:
            self.errors.append('Missing required field: groups')
            return self._result(filepath)

        # Validate each group
        for idx, group in enumerate(data.get('groups', [])):
            self._validate_group(group, idx)

        # Test with Prometheus if URL provided
        if self.prometheus_url and not self.errors:
            self._test_with_prometheus(filepath)

        return self._result(filepath)

    def validate_directory(self, dirpath: Path) -> List[Dict[str, Any]]:
        """Validate all .yml/.yaml files in a directory."""
        results = []
        for filepath in dirpath.glob('**/*.yml'):
            results.append(self.validate_file(filepath))
        for filepath in dirpath.glob('**/*.yaml'):
            results.append(self.validate_file(filepath))
        return results

    def _validate_group(self, group: Dict, idx: int) -> None:
        """Validate an alert group."""
        prefix = f'Group {idx}'

        # Required fields
        if 'name' not in group:
            self.errors.append(f'{prefix}: Missing required field: name')
        else:
            if not isinstance(group['name'], str) or not group['name']:
                self.errors.append(f'{prefix}: name must be a non-empty string')

        if 'rules' not in group:
            self.errors.append(f'{prefix}: Missing required field: rules')
            return

        if not isinstance(group['rules'], list):
            self.errors.append(f'{prefix}: rules must be a list')
            return

        # Validate interval
        if 'interval' in group:
            self._validate_duration(group['interval'], f'{prefix}: interval')

        # Validate each rule
        for rule_idx, rule in enumerate(group['rules']):
            rule_prefix = f'{prefix}.rules[{rule_idx}]'
            if 'alert' in rule:
                self._validate_alert_rule(rule, rule_prefix)
            elif 'record' in rule:
                self._validate_recording_rule(rule, rule_prefix)
            else:
                self.errors.append(f'{rule_prefix}: Must have either "alert" or "record" field')

    def _validate_alert_rule(self, rule: Dict, prefix: str) -> None:
        """Validate an alerting rule."""
        # Required fields
        if 'expr' not in rule:
            self.errors.append(f'{prefix}: Missing required field: expr')
        else:
            self._validate_expression(rule['expr'], prefix)

        # Alert name validation
        alert_name = rule.get('alert', '')
        if not alert_name:
            self.errors.append(f'{prefix}: Alert name is empty')
        elif not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', alert_name):
            self.errors.append(
                f'{prefix}: Alert name "{alert_name}" must match [a-zA-Z_][a-zA-Z0-9_]*'
            )

        # Naming conventions
        if alert_name and not alert_name[0].isupper():
            self.warnings.append(
                f'{prefix}: Alert name "{alert_name}" should start with uppercase (convention)'
            )

        # Duration validation
        if 'for' in rule:
            duration = self._validate_duration(rule['for'], f'{prefix}: for')
            if duration and duration < timedelta(minutes=1):
                self.warnings.append(
                    f'{prefix}: "for" duration < 1m may cause alert flapping'
                )

        # Labels validation
        if 'labels' in rule:
            self._validate_labels(rule['labels'], f'{prefix}.labels')

            # Severity check
            severity = rule['labels'].get('severity')
            if not severity:
                self.warnings.append(f'{prefix}: Missing "severity" label')
            elif severity not in ['critical', 'warning', 'info']:
                self.warnings.append(
                    f'{prefix}: Severity "{severity}" should be one of: critical, warning, info'
                )
        else:
            self.warnings.append(f'{prefix}: No labels defined')

        # Annotations validation
        if 'annotations' in rule:
            self._validate_annotations(rule['annotations'], prefix)
        else:
            self.warnings.append(f'{prefix}: No annotations defined')

    def _validate_recording_rule(self, rule: Dict, prefix: str) -> None:
        """Validate a recording rule."""
        # Required fields
        if 'expr' not in rule:
            self.errors.append(f'{prefix}: Missing required field: expr')
        else:
            self._validate_expression(rule['expr'], prefix)

        # Record name validation
        record_name = rule.get('record', '')
        if not record_name:
            self.errors.append(f'{prefix}: Record name is empty')
        elif not re.match(r'^[a-zA-Z_:][a-zA-Z0-9_:]*$', record_name):
            self.errors.append(
                f'{prefix}: Record name "{record_name}" must match [a-zA-Z_:][a-zA-Z0-9_:]*'
            )

        # Naming convention (level:metric:operation)
        if record_name and ':' not in record_name:
            self.warnings.append(
                f'{prefix}: Record name "{record_name}" should follow "level:metric:operation" convention'
            )

        # Labels in recording rules
        if 'labels' in rule:
            self._validate_labels(rule['labels'], f'{prefix}.labels')

    def _validate_expression(self, expr: str, prefix: str) -> None:
        """Validate PromQL expression."""
        if not expr or not expr.strip():
            self.errors.append(f'{prefix}.expr: Expression is empty')
            return

        # Check for common anti-patterns
        if 'absent(' in expr and 'for:' not in expr:
            self.warnings.append(
                f'{prefix}.expr: absent() queries should use "for" duration to avoid flapping'
            )

        # Check for rate/irate with histogram
        if '_bucket' in expr and 'rate(' in expr:
            if 'histogram_quantile(' not in expr:
                self.warnings.append(
                    f'{prefix}.expr: Use histogram_quantile() with histogram buckets'
                )

        # Check for increase on counter
        if 'increase(' in expr:
            self.info.append(
                f'{prefix}.expr: Consider rate() instead of increase() for alerting (smoother)'
            )

        # Validate with Prometheus if available
        if self.prometheus_url:
            self._validate_expr_with_prometheus(expr, prefix)

    def _validate_expr_with_prometheus(self, expr: str, prefix: str) -> None:
        """Test expression with Prometheus API."""
        try:
            response = requests.post(
                f'{self.prometheus_url}/api/v1/query',
                data={'query': expr, 'time': ''},
                timeout=5
            )
            result = response.json()

            if result.get('status') != 'success':
                error = result.get('error', 'Unknown error')
                self.errors.append(f'{prefix}.expr: PromQL error: {error}')
            elif not result.get('data', {}).get('result'):
                self.info.append(f'{prefix}.expr: Query returns no results (may be expected)')

        except requests.RequestException as e:
            self.warnings.append(f'{prefix}.expr: Failed to test with Prometheus: {e}')

    def _validate_labels(self, labels: Dict, prefix: str) -> None:
        """Validate labels."""
        if not isinstance(labels, dict):
            self.errors.append(f'{prefix}: Labels must be a dictionary')
            return

        for key, value in labels.items():
            # Label key validation
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                self.errors.append(
                    f'{prefix}.{key}: Invalid label name (must match [a-zA-Z_][a-zA-Z0-9_]*)'
                )

            # Label value validation
            if not isinstance(value, str):
                self.errors.append(f'{prefix}.{key}: Label value must be a string')

            # Reserved labels
            if key.startswith('__'):
                self.errors.append(f'{prefix}.{key}: Label names starting with __ are reserved')

    def _validate_annotations(self, annotations: Dict, prefix: str) -> None:
        """Validate annotations."""
        if not isinstance(annotations, dict):
            self.errors.append(f'{prefix}.annotations: Must be a dictionary')
            return

        # Recommended annotations
        recommended = ['summary', 'description']
        for field in recommended:
            if field not in annotations:
                self.warnings.append(f'{prefix}.annotations: Missing recommended field: {field}')

        # Runbook URL
        if 'runbook_url' not in annotations and 'runbook' not in annotations:
            self.warnings.append(f'{prefix}.annotations: Missing runbook_url')
        else:
            url = annotations.get('runbook_url') or annotations.get('runbook', '')
            if url and not url.startswith(('http://', 'https://')):
                self.warnings.append(f'{prefix}.annotations.runbook_url: Should be a full URL')

        # Template validation
        for key, value in annotations.items():
            if not isinstance(value, str):
                continue

            # Check for template syntax
            if '{{' in value and '}}' in value:
                # Validate template syntax
                if '{{ $labels.' in value or '{{ $value' in value:
                    self.info.append(f'{prefix}.annotations.{key}: Uses templating')
                else:
                    self.warnings.append(
                        f'{prefix}.annotations.{key}: Template syntax found but no valid variables'
                    )

    def _validate_duration(self, duration: str, prefix: str) -> timedelta:
        """Validate duration string."""
        if not duration:
            self.errors.append(f'{prefix}: Duration is empty')
            return None

        # Parse duration (e.g., "5m", "1h", "30s")
        match = re.match(r'^(\d+)([smhd])$', duration)
        if not match:
            self.errors.append(
                f'{prefix}: Invalid duration format "{duration}" (expected: 1s, 5m, 1h, 1d)'
            )
            return None

        amount, unit = match.groups()
        amount = int(amount)

        unit_map = {
            's': timedelta(seconds=amount),
            'm': timedelta(minutes=amount),
            'h': timedelta(hours=amount),
            'd': timedelta(days=amount)
        }

        return unit_map.get(unit)

    def _test_with_prometheus(self, filepath: Path) -> None:
        """Test rules with promtool via Prometheus API."""
        try:
            with open(filepath, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    f'{self.prometheus_url}/api/v1/rules/test',
                    files=files,
                    timeout=10
                )

                if response.status_code != 200:
                    self.warnings.append(f'Prometheus validation failed: {response.text}')

        except Exception as e:
            self.warnings.append(f'Failed to test with Prometheus: {e}')

    def _result(self, filepath: Path) -> Dict[str, Any]:
        """Build result dictionary."""
        return {
            'file': str(filepath),
            'valid': len(self.errors) == 0,
            'errors': self.errors.copy(),
            'warnings': self.warnings.copy(),
            'info': self.info.copy()
        }


def print_results(results: List[Dict[str, Any]], json_output: bool = False) -> bool:
    """Print validation results."""
    if json_output:
        print(json.dumps(results, indent=2))
        return all(r['valid'] for r in results)

    # Human-readable output
    total_errors = 0
    total_warnings = 0
    total_info = 0

    for result in results:
        filepath = result['file']
        print(f"\n{'='*80}")
        print(f"File: {filepath}")
        print(f"{'='*80}")

        if result['valid']:
            print("✓ VALID")
        else:
            print("✗ INVALID")

        if result['errors']:
            print(f"\nErrors ({len(result['errors'])}):")
            for error in result['errors']:
                print(f"  ✗ {error}")
            total_errors += len(result['errors'])

        if result['warnings']:
            print(f"\nWarnings ({len(result['warnings'])}):")
            for warning in result['warnings']:
                print(f"  ⚠ {warning}")
            total_warnings += len(result['warnings'])

        if result['info']:
            print(f"\nInfo ({len(result['info'])}):")
            for info in result['info']:
                print(f"  ℹ {info}")
            total_info += len(result['info'])

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Files checked: {len(results)}")
    print(f"Valid: {sum(1 for r in results if r['valid'])}")
    print(f"Invalid: {sum(1 for r in results if not r['valid'])}")
    print(f"Total errors: {total_errors}")
    print(f"Total warnings: {total_warnings}")
    print(f"Total info: {total_info}")

    return all(r['valid'] for r in results)


def main():
    parser = argparse.ArgumentParser(
        description='Validate Prometheus alert rules',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate single file
  validate_alert_rules.py --file alerts.yml

  # Validate directory
  validate_alert_rules.py --dir /etc/prometheus/alerts/

  # JSON output
  validate_alert_rules.py --file alerts.yml --json

  # Test with Prometheus
  validate_alert_rules.py --file alerts.yml --prometheus http://localhost:9090

  # Strict mode (warnings are errors)
  validate_alert_rules.py --file alerts.yml --strict
        """
    )

    parser.add_argument(
        '--file', '-f',
        type=Path,
        help='Alert rule file to validate'
    )

    parser.add_argument(
        '--dir', '-d',
        type=Path,
        help='Directory containing alert rule files'
    )

    parser.add_argument(
        '--prometheus', '-p',
        help='Prometheus URL for testing queries (e.g., http://localhost:9090)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors'
    )

    parser.add_argument(
        '--help-examples',
        action='store_true',
        help='Show usage examples and exit'
    )

    args = parser.parse_args()

    if args.help_examples:
        parser.print_help()
        sys.exit(0)

    if not args.file and not args.dir:
        parser.error('Either --file or --dir must be specified')

    # Validate
    validator = AlertRuleValidator(prometheus_url=args.prometheus)

    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        results = [validator.validate_file(args.file)]
    else:
        if not args.dir.exists():
            print(f"Error: Directory not found: {args.dir}", file=sys.stderr)
            sys.exit(1)
        results = validator.validate_directory(args.dir)

    if not results:
        print("No alert rule files found", file=sys.stderr)
        sys.exit(1)

    # Print results
    all_valid = print_results(results, json_output=args.json)

    # Check strict mode
    if args.strict:
        has_warnings = any(r['warnings'] for r in results)
        if has_warnings:
            if not args.json:
                print("\n✗ FAILED (strict mode: warnings present)", file=sys.stderr)
            sys.exit(1)

    # Exit code
    if all_valid:
        if not args.json:
            print("\n✓ All checks passed")
        sys.exit(0)
    else:
        if not args.json:
            print("\n✗ Validation failed", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
