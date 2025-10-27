#!/usr/bin/env python3
"""
Prometheus Metrics Analyzer

Analyzes Prometheus metrics and configurations for:
- High cardinality issues
- Naming convention violations
- Label anti-patterns
- Recording/alerting rule validation
- Configuration best practices
- Performance optimization opportunities

Usage:
    ./analyze_metrics.py --config prometheus.yml --json
    ./analyze_metrics.py --metrics-endpoint http://localhost:9090 --json
    ./analyze_metrics.py --config prometheus.yml --metrics-endpoint http://localhost:9090
"""

import argparse
import json
import sys
import re
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from urllib.parse import urljoin
import requests
import yaml


class PrometheusAnalyzer:
    """Analyze Prometheus metrics and configuration."""

    def __init__(self, config_path: str = None, metrics_endpoint: str = None):
        self.config_path = config_path
        self.metrics_endpoint = metrics_endpoint
        self.config = None
        self.metrics = []
        self.issues = []
        self.recommendations = []
        self.stats = {}

    def load_config(self) -> bool:
        """Load Prometheus configuration file."""
        if not self.config_path:
            return False

        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            return True
        except Exception as e:
            self.issues.append({
                'severity': 'critical',
                'category': 'config',
                'message': f'Failed to load config: {e}'
            })
            return False

    def fetch_metrics(self) -> bool:
        """Fetch metrics from Prometheus endpoint."""
        if not self.metrics_endpoint:
            return False

        try:
            # Fetch all metric names
            url = urljoin(self.metrics_endpoint, '/api/v1/label/__name__/values')
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data['status'] == 'success':
                self.metrics = data['data']
                return True
            else:
                self.issues.append({
                    'severity': 'error',
                    'category': 'fetch',
                    'message': f"API returned status: {data['status']}"
                })
                return False

        except Exception as e:
            self.issues.append({
                'severity': 'error',
                'category': 'fetch',
                'message': f'Failed to fetch metrics: {e}'
            })
            return False

    def analyze_metric_naming(self):
        """Analyze metric naming conventions."""
        if not self.metrics:
            return

        naming_issues = []
        missing_units = []
        camel_case = []

        unit_suffixes = ['_total', '_seconds', '_bytes', '_ratio', '_percent',
                        '_count', '_sum', '_bucket', '_celsius', '_fahrenheit',
                        '_millis', '_nanos', '_requests', '_errors']

        for metric in self.metrics:
            # Check for CamelCase
            if re.search(r'[A-Z]', metric):
                camel_case.append(metric)

            # Check for missing units (counters should have _total)
            if not any(metric.endswith(suffix) for suffix in unit_suffixes):
                # Check if it looks like a counter or gauge that should have units
                if any(word in metric.lower() for word in ['count', 'total', 'size', 'duration', 'latency', 'time']):
                    missing_units.append(metric)

            # Check for double underscores (invalid)
            if '__' in metric and not metric.startswith('__'):
                naming_issues.append({
                    'metric': metric,
                    'issue': 'Contains double underscore'
                })

        if camel_case:
            self.issues.append({
                'severity': 'warning',
                'category': 'naming',
                'message': f'Found {len(camel_case)} metrics with CamelCase (should be snake_case)',
                'examples': camel_case[:5],
                'count': len(camel_case)
            })

        if missing_units:
            self.issues.append({
                'severity': 'warning',
                'category': 'naming',
                'message': f'Found {len(missing_units)} metrics possibly missing unit suffixes',
                'examples': missing_units[:5],
                'count': len(missing_units)
            })

        if naming_issues:
            self.issues.append({
                'severity': 'error',
                'category': 'naming',
                'message': f'Found {len(naming_issues)} metrics with naming violations',
                'details': naming_issues[:5]
            })

    def analyze_cardinality(self):
        """Analyze metric cardinality from Prometheus."""
        if not self.metrics_endpoint:
            return

        try:
            # Query for cardinality by metric name
            query = 'count by (__name__) ({__name__=~".+"})'
            url = urljoin(self.metrics_endpoint, '/api/v1/query')
            response = requests.get(url, params={'query': query}, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data['status'] != 'success':
                return

            results = data['data']['result']
            cardinality_by_metric = {}

            for result in results:
                metric_name = result['metric']['__name__']
                cardinality = int(result['value'][1])
                cardinality_by_metric[metric_name] = cardinality

            # Find high cardinality metrics
            high_cardinality = {k: v for k, v in cardinality_by_metric.items() if v > 1000}

            if high_cardinality:
                sorted_high = sorted(high_cardinality.items(), key=lambda x: x[1], reverse=True)
                self.issues.append({
                    'severity': 'critical',
                    'category': 'cardinality',
                    'message': f'Found {len(high_cardinality)} metrics with high cardinality (>1000)',
                    'top_offenders': sorted_high[:10]
                })

            # Calculate total cardinality
            total_cardinality = sum(cardinality_by_metric.values())
            self.stats['total_cardinality'] = total_cardinality
            self.stats['total_metrics'] = len(cardinality_by_metric)
            self.stats['avg_cardinality'] = total_cardinality / len(cardinality_by_metric) if cardinality_by_metric else 0

            if total_cardinality > 1000000:
                self.issues.append({
                    'severity': 'critical',
                    'category': 'cardinality',
                    'message': f'Very high total cardinality: {total_cardinality:,} time series',
                    'recommendation': 'Consider reducing cardinality through aggregation or label removal'
                })

        except Exception as e:
            self.issues.append({
                'severity': 'warning',
                'category': 'cardinality',
                'message': f'Failed to analyze cardinality: {e}'
            })

    def analyze_config(self):
        """Analyze Prometheus configuration."""
        if not self.config:
            return

        # Check global settings
        global_config = self.config.get('global', {})
        scrape_interval = global_config.get('scrape_interval', '1m')
        evaluation_interval = global_config.get('evaluation_interval', '1m')

        # Parse intervals (simple parsing for common formats)
        def parse_interval(interval_str):
            match = re.match(r'(\d+)([smhd])', interval_str)
            if match:
                value, unit = match.groups()
                multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
                return int(value) * multipliers.get(unit, 1)
            return 60  # Default 1 minute

        scrape_seconds = parse_interval(scrape_interval)
        if scrape_seconds < 10:
            self.issues.append({
                'severity': 'warning',
                'category': 'config',
                'message': f'Very short scrape_interval: {scrape_interval}',
                'recommendation': 'Consider using at least 15s scrape interval'
            })

        # Check scrape configs
        scrape_configs = self.config.get('scrape_configs', [])
        for scrape_config in scrape_configs:
            job_name = scrape_config.get('job_name', 'unknown')

            # Check for sample limits
            if 'sample_limit' not in scrape_config:
                self.recommendations.append({
                    'category': 'config',
                    'message': f'Job "{job_name}" has no sample_limit',
                    'recommendation': 'Consider adding sample_limit to prevent cardinality explosions'
                })

            # Check for label limits
            if 'label_limit' not in scrape_config:
                self.recommendations.append({
                    'category': 'config',
                    'message': f'Job "{job_name}" has no label_limit',
                    'recommendation': 'Consider adding label_limit (e.g., 50)'
                })

            # Check for static configs with many targets
            static_configs = scrape_config.get('static_configs', [])
            for static_config in static_configs:
                targets = static_config.get('targets', [])
                if len(targets) > 100:
                    self.issues.append({
                        'severity': 'warning',
                        'category': 'config',
                        'message': f'Job "{job_name}" has {len(targets)} static targets',
                        'recommendation': 'Consider using service discovery for large target sets'
                    })

        # Check rule files
        rule_files = self.config.get('rule_files', [])
        if not rule_files:
            self.recommendations.append({
                'category': 'config',
                'message': 'No rule_files configured',
                'recommendation': 'Consider adding recording rules for frequently used queries'
            })

        # Check alerting config
        alerting = self.config.get('alerting', {})
        if not alerting:
            self.recommendations.append({
                'category': 'config',
                'message': 'No alerting configuration',
                'recommendation': 'Configure Alertmanager for production deployments'
            })

        # Check remote write
        remote_write = self.config.get('remote_write', [])
        if not remote_write:
            self.recommendations.append({
                'category': 'config',
                'message': 'No remote_write configured',
                'recommendation': 'Consider remote_write for long-term storage'
            })

        # Check storage retention
        if 'storage' not in self.config:
            self.recommendations.append({
                'category': 'config',
                'message': 'No storage configuration',
                'recommendation': 'Configure retention time and size limits'
            })

    def analyze_rules(self):
        """Analyze recording and alerting rules."""
        if not self.config:
            return

        rule_files = self.config.get('rule_files', [])
        if not rule_files:
            return

        for rule_file in rule_files:
            try:
                with open(rule_file, 'r') as f:
                    rules = yaml.safe_load(f)

                groups = rules.get('groups', [])
                for group in groups:
                    group_name = group.get('name', 'unknown')
                    interval = group.get('interval', 'not set')
                    rules_list = group.get('rules', [])

                    for rule in rules_list:
                        # Recording rule
                        if 'record' in rule:
                            record_name = rule['record']

                            # Check naming convention: level:metric:operations
                            if ':' not in record_name:
                                self.issues.append({
                                    'severity': 'warning',
                                    'category': 'rules',
                                    'message': f'Recording rule "{record_name}" doesn\'t follow level:metric:operations convention'
                                })

                        # Alerting rule
                        elif 'alert' in rule:
                            alert_name = rule['alert']

                            # Check for 'for' clause
                            if 'for' not in rule:
                                self.issues.append({
                                    'severity': 'warning',
                                    'category': 'rules',
                                    'message': f'Alert "{alert_name}" has no "for" clause',
                                    'recommendation': 'Add "for" clause to prevent flapping alerts'
                                })

                            # Check for severity label
                            labels = rule.get('labels', {})
                            if 'severity' not in labels:
                                self.issues.append({
                                    'severity': 'warning',
                                    'category': 'rules',
                                    'message': f'Alert "{alert_name}" has no severity label',
                                    'recommendation': 'Add severity label (critical, warning, info)'
                                })

                            # Check for annotations
                            annotations = rule.get('annotations', {})
                            if not annotations:
                                self.issues.append({
                                    'severity': 'warning',
                                    'category': 'rules',
                                    'message': f'Alert "{alert_name}" has no annotations',
                                    'recommendation': 'Add summary and description annotations'
                                })

            except Exception as e:
                self.issues.append({
                    'severity': 'error',
                    'category': 'rules',
                    'message': f'Failed to load rule file {rule_file}: {e}'
                })

    def generate_report(self, output_json: bool = False) -> str:
        """Generate analysis report."""
        if output_json:
            return json.dumps({
                'stats': self.stats,
                'issues': self.issues,
                'recommendations': self.recommendations
            }, indent=2)

        # Text report
        report = []
        report.append("=" * 80)
        report.append("Prometheus Metrics Analysis Report")
        report.append("=" * 80)

        # Stats
        if self.stats:
            report.append("\nStatistics:")
            report.append("-" * 80)
            for key, value in self.stats.items():
                if isinstance(value, float):
                    report.append(f"  {key}: {value:.2f}")
                else:
                    report.append(f"  {key}: {value:,}" if isinstance(value, int) else f"  {key}: {value}")

        # Issues
        if self.issues:
            report.append("\nIssues Found:")
            report.append("-" * 80)

            # Group by severity
            critical = [i for i in self.issues if i.get('severity') == 'critical']
            errors = [i for i in self.issues if i.get('severity') == 'error']
            warnings = [i for i in self.issues if i.get('severity') == 'warning']

            if critical:
                report.append(f"\nCRITICAL ({len(critical)}):")
                for issue in critical:
                    report.append(f"  - {issue['message']}")
                    if 'examples' in issue:
                        report.append(f"    Examples: {', '.join(issue['examples'][:3])}")
                    if 'top_offenders' in issue:
                        for metric, count in issue['top_offenders'][:5]:
                            report.append(f"    {metric}: {count:,} time series")

            if errors:
                report.append(f"\nERRORS ({len(errors)}):")
                for issue in errors:
                    report.append(f"  - {issue['message']}")

            if warnings:
                report.append(f"\nWARNINGS ({len(warnings)}):")
                for issue in warnings:
                    report.append(f"  - {issue['message']}")
                    if 'recommendation' in issue:
                        report.append(f"    Recommendation: {issue['recommendation']}")

        else:
            report.append("\nNo issues found!")

        # Recommendations
        if self.recommendations:
            report.append("\nRecommendations:")
            report.append("-" * 80)
            for rec in self.recommendations:
                report.append(f"  - {rec['message']}")
                if 'recommendation' in rec:
                    report.append(f"    → {rec['recommendation']}")

        report.append("\n" + "=" * 80)

        return "\n".join(report)

    def run_analysis(self, output_json: bool = False) -> str:
        """Run full analysis."""
        if self.config_path:
            self.load_config()
            self.analyze_config()
            self.analyze_rules()

        if self.metrics_endpoint:
            self.fetch_metrics()
            self.analyze_metric_naming()
            self.analyze_cardinality()

        return self.generate_report(output_json)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Prometheus metrics and configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze configuration file
  ./analyze_metrics.py --config prometheus.yml

  # Analyze metrics from endpoint
  ./analyze_metrics.py --metrics-endpoint http://localhost:9090

  # Analyze both with JSON output
  ./analyze_metrics.py --config prometheus.yml --metrics-endpoint http://localhost:9090 --json

  # Analyze and save to file
  ./analyze_metrics.py --config prometheus.yml --json > analysis.json
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to prometheus.yml configuration file'
    )

    parser.add_argument(
        '--metrics-endpoint',
        type=str,
        help='Prometheus metrics endpoint (e.g., http://localhost:9090)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    args = parser.parse_args()

    if not args.config and not args.metrics_endpoint:
        parser.print_help()
        print("\nError: Must specify either --config or --metrics-endpoint (or both)")
        sys.exit(1)

    analyzer = PrometheusAnalyzer(
        config_path=args.config,
        metrics_endpoint=args.metrics_endpoint
    )

    try:
        report = analyzer.run_analysis(output_json=args.json)
        print(report)

        # Exit with error code if critical issues found
        critical_issues = [i for i in analyzer.issues if i.get('severity') == 'critical']
        sys.exit(1 if critical_issues else 0)

    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
