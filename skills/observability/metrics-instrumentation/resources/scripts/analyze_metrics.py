#!/usr/bin/env python3
"""
Prometheus Metrics Cardinality Analyzer

Analyzes Prometheus metrics to detect cardinality issues, identify high-cardinality
labels, and provide optimization recommendations.

Usage:
    analyze_metrics.py --url http://localhost:9090 [options]
    analyze_metrics.py --metrics-file metrics.txt [options]
    analyze_metrics.py --url http://localhost:9090 --json
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Set, Tuple, Optional
from urllib.parse import urljoin
import urllib.request
import urllib.error


@dataclass
class MetricInfo:
    """Information about a metric."""
    name: str
    type: str
    help: str
    series_count: int
    label_cardinality: Dict[str, int]
    sample_labels: Dict[str, Set[str]]
    severity: str  # low, medium, high, critical


@dataclass
class AnalysisResult:
    """Results of cardinality analysis."""
    total_metrics: int
    total_series: int
    metrics: List[MetricInfo]
    high_cardinality_metrics: List[str]
    problematic_labels: Dict[str, List[str]]
    recommendations: List[str]


class PrometheusClient:
    """Client for querying Prometheus API."""

    def __init__(self, url: str, timeout: int = 30):
        self.url = url.rstrip('/')
        self.timeout = timeout

    def query(self, query: str) -> dict:
        """Execute PromQL query."""
        url = urljoin(self.url, '/api/v1/query')
        params = urllib.parse.urlencode({'query': query})
        full_url = f"{url}?{params}"

        try:
            with urllib.request.urlopen(full_url, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
                if data['status'] != 'success':
                    raise Exception(f"Query failed: {data.get('error', 'Unknown error')}")
                return data['data']
        except urllib.error.URLError as e:
            raise Exception(f"Failed to connect to Prometheus: {e}")

    def get_metric_metadata(self) -> Dict[str, Dict[str, str]]:
        """Get metadata for all metrics."""
        url = urljoin(self.url, '/api/v1/metadata')

        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
                if data['status'] != 'success':
                    return {}

                # Flatten metadata
                metadata = {}
                for metric_name, metric_list in data['data'].items():
                    if metric_list:
                        metadata[metric_name] = metric_list[0]
                return metadata
        except Exception:
            return {}

    def get_all_series(self) -> List[str]:
        """Get all time series from Prometheus."""
        # NOTE: This is a PromQL query, not SQL - no injection risk
        result = self.query('{__name__=~".+"}')
        series = []

        for item in result.get('result', []):
            metric_name = item['metric'].get('__name__', '')
            if metric_name:
                # Reconstruct full series with labels
                labels = ','.join(f'{k}="{v}"' for k, v in item['metric'].items() if k != '__name__')
                series.append(f"{metric_name}{{{labels}}}")

        return series

    def get_series_count_by_metric(self) -> Dict[str, int]:
        """Get series count for each metric."""
        # NOTE: This is a PromQL query, not SQL - no injection risk
        result = self.query('count by (__name__) ({__name__=~".+"})')
        counts = {}

        for item in result.get('result', []):
            metric_name = item['metric'].get('__name__', '')
            count = int(float(item['value'][1]))
            if metric_name:
                counts[metric_name] = count

        return counts


class MetricsAnalyzer:
    """Analyzes Prometheus metrics for cardinality issues."""

    # Cardinality thresholds
    LOW_CARDINALITY = 100
    MEDIUM_CARDINALITY = 1000
    HIGH_CARDINALITY = 10000

    # Known high-cardinality label patterns
    HIGH_CARDINALITY_PATTERNS = [
        r'.*id$',
        r'.*uuid$',
        r'.*guid$',
        r'.*email$',
        r'.*ip$',
        r'.*address$',
        r'.*token$',
        r'.*session$',
        r'.*trace.*id$',
        r'.*span.*id$',
        r'user.*name$',
        r'timestamp',
    ]

    def __init__(self, prometheus_url: Optional[str] = None):
        self.client = PrometheusClient(prometheus_url) if prometheus_url else None

    def parse_metrics_file(self, file_path: str) -> List[str]:
        """Parse metrics from Prometheus text format file."""
        with open(file_path, 'r') as f:
            lines = f.readlines()

        series = []
        for line in lines:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Extract metric name and labels
            if '{' in line:
                series.append(line.split()[0])

        return series

    def extract_metric_info(self, series_list: List[str]) -> Dict[str, MetricInfo]:
        """Extract metric information from series list."""
        metrics = defaultdict(lambda: {
            'series_count': 0,
            'labels': defaultdict(set),
            'type': 'unknown',
            'help': ''
        })

        # Parse each series
        for series in series_list:
            # Extract metric name
            if '{' in series:
                metric_name = series.split('{')[0]
                labels_str = series.split('{')[1].split('}')[0]

                # Parse labels
                labels = {}
                for label in labels_str.split(','):
                    if '=' in label:
                        key, value = label.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"')
                        labels[key] = value
            else:
                metric_name = series.split()[0]
                labels = {}

            metrics[metric_name]['series_count'] += 1

            # Track label values
            for label_key, label_value in labels.items():
                metrics[metric_name]['labels'][label_key].add(label_value)

        # Get metadata if Prometheus client available
        metadata = {}
        if self.client:
            metadata = self.client.get_metric_metadata()

        # Convert to MetricInfo objects
        result = {}
        for metric_name, info in metrics.items():
            label_cardinality = {k: len(v) for k, v in info['labels'].items()}

            # Determine severity
            series_count = info['series_count']
            if series_count < self.LOW_CARDINALITY:
                severity = 'low'
            elif series_count < self.MEDIUM_CARDINALITY:
                severity = 'medium'
            elif series_count < self.HIGH_CARDINALITY:
                severity = 'high'
            else:
                severity = 'critical'

            # Get metadata
            meta = metadata.get(metric_name, {})

            result[metric_name] = MetricInfo(
                name=metric_name,
                type=meta.get('type', 'unknown'),
                help=meta.get('help', ''),
                series_count=series_count,
                label_cardinality=label_cardinality,
                sample_labels={k: list(v)[:5] for k, v in info['labels'].items()},  # Sample only
                severity=severity
            )

        return result

    def detect_problematic_labels(self, metrics: Dict[str, MetricInfo]) -> Dict[str, List[str]]:
        """Detect labels that may cause cardinality issues."""
        problematic = defaultdict(list)

        for metric_name, metric_info in metrics.items():
            for label_name, cardinality in metric_info.label_cardinality.items():
                # Check if label matches high-cardinality pattern
                is_suspicious = any(
                    re.match(pattern, label_name, re.IGNORECASE)
                    for pattern in self.HIGH_CARDINALITY_PATTERNS
                )

                if is_suspicious or cardinality > 100:
                    problematic[label_name].append(
                        f"{metric_name} (cardinality: {cardinality})"
                    )

        return dict(problematic)

    def generate_recommendations(
        self,
        metrics: Dict[str, MetricInfo],
        problematic_labels: Dict[str, List[str]]
    ) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        # High cardinality metrics
        high_card_metrics = [
            m for m in metrics.values()
            if m.severity in ['high', 'critical']
        ]

        if high_card_metrics:
            recommendations.append(
                f"Found {len(high_card_metrics)} metrics with high/critical cardinality. "
                "Consider reducing label cardinality."
            )

        # Problematic labels
        if problematic_labels:
            recommendations.append(
                f"Found {len(problematic_labels)} potentially problematic labels: "
                f"{', '.join(list(problematic_labels.keys())[:5])}. "
                "Consider removing high-cardinality labels like user_id, trace_id, ip_address."
            )

        # Check for missing _total suffix on counters
        for metric in metrics.values():
            if metric.type == 'counter' and not metric.name.endswith('_total'):
                recommendations.append(
                    f"Metric '{metric.name}' is a counter but missing '_total' suffix. "
                    "Add suffix for clarity."
                )

        # Check for missing units
        metrics_without_units = [
            m.name for m in metrics.values()
            if not any(
                m.name.endswith(unit)
                for unit in ['_seconds', '_bytes', '_ratio', '_percent', '_total']
            ) and m.type in ['histogram', 'gauge']
        ]

        if metrics_without_units[:3]:
            recommendations.append(
                f"Metrics without units detected: {', '.join(metrics_without_units[:3])}. "
                "Add unit suffixes (_seconds, _bytes, etc.) for clarity."
            )

        # Overall cardinality
        total_series = sum(m.series_count for m in metrics.values())
        if total_series > 100000:
            recommendations.append(
                f"Total series count is {total_series:,} (> 100K). "
                "This may impact Prometheus performance. Consider reducing cardinality."
            )

        # Label count per metric
        high_label_count = [
            (m.name, len(m.label_cardinality))
            for m in metrics.values()
            if len(m.label_cardinality) > 5
        ]

        if high_label_count:
            recommendations.append(
                f"Metrics with > 5 labels: {', '.join(m[0] for m in high_label_count[:3])}. "
                "Consider reducing number of labels."
            )

        if not recommendations:
            recommendations.append("No major issues detected. Metrics configuration looks good!")

        return recommendations

    def analyze(self, series_list: List[str]) -> AnalysisResult:
        """Perform full analysis on metrics."""
        # Extract metric information
        metrics = self.extract_metric_info(series_list)

        # Detect problematic labels
        problematic_labels = self.detect_problematic_labels(metrics)

        # Generate recommendations
        recommendations = self.generate_recommendations(metrics, problematic_labels)

        # Identify high cardinality metrics
        high_cardinality = [
            m.name for m in metrics.values()
            if m.severity in ['high', 'critical']
        ]

        return AnalysisResult(
            total_metrics=len(metrics),
            total_series=sum(m.series_count for m in metrics.values()),
            metrics=sorted(metrics.values(), key=lambda m: m.series_count, reverse=True),
            high_cardinality_metrics=high_cardinality,
            problematic_labels=problematic_labels,
            recommendations=recommendations
        )


def format_human_readable(result: AnalysisResult) -> str:
    """Format analysis result for human reading."""
    output = []

    output.append("=" * 80)
    output.append("PROMETHEUS METRICS CARDINALITY ANALYSIS")
    output.append("=" * 80)
    output.append("")

    output.append(f"Total Metrics: {result.total_metrics}")
    output.append(f"Total Time Series: {result.total_series:,}")
    output.append("")

    # Top metrics by cardinality
    output.append("=" * 80)
    output.append("TOP METRICS BY CARDINALITY")
    output.append("=" * 80)
    output.append("")

    for i, metric in enumerate(result.metrics[:10], 1):
        output.append(f"{i}. {metric.name}")
        output.append(f"   Type: {metric.type}")
        output.append(f"   Series Count: {metric.series_count:,} ({metric.severity})")

        if metric.label_cardinality:
            output.append(f"   Labels:")
            for label, cardinality in sorted(
                metric.label_cardinality.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                sample_values = metric.sample_labels.get(label, [])
                sample_str = ', '.join(f'"{v}"' for v in sample_values[:3])
                if len(sample_values) > 3:
                    sample_str += ', ...'
                output.append(f"     - {label}: {cardinality} unique values ({sample_str})")

        output.append("")

    # High cardinality metrics
    if result.high_cardinality_metrics:
        output.append("=" * 80)
        output.append("HIGH CARDINALITY METRICS (NEEDS ATTENTION)")
        output.append("=" * 80)
        output.append("")

        for metric_name in result.high_cardinality_metrics[:20]:
            metric = next(m for m in result.metrics if m.name == metric_name)
            output.append(f"  - {metric_name}: {metric.series_count:,} series ({metric.severity})")

        output.append("")

    # Problematic labels
    if result.problematic_labels:
        output.append("=" * 80)
        output.append("PROBLEMATIC LABELS")
        output.append("=" * 80)
        output.append("")

        for label, metrics_list in sorted(
            result.problematic_labels.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:10]:
            output.append(f"Label: {label}")
            for metric in metrics_list[:3]:
                output.append(f"  - {metric}")
            if len(metrics_list) > 3:
                output.append(f"  ... and {len(metrics_list) - 3} more")
            output.append("")

    # Recommendations
    output.append("=" * 80)
    output.append("RECOMMENDATIONS")
    output.append("=" * 80)
    output.append("")

    for i, rec in enumerate(result.recommendations, 1):
        output.append(f"{i}. {rec}")

    output.append("")
    output.append("=" * 80)

    return '\n'.join(output)


def format_json(result: AnalysisResult) -> str:
    """Format analysis result as JSON."""
    data = {
        'total_metrics': result.total_metrics,
        'total_series': result.total_series,
        'metrics': [
            {
                'name': m.name,
                'type': m.type,
                'help': m.help,
                'series_count': m.series_count,
                'severity': m.severity,
                'label_cardinality': m.label_cardinality,
                'sample_labels': m.sample_labels
            }
            for m in result.metrics
        ],
        'high_cardinality_metrics': result.high_cardinality_metrics,
        'problematic_labels': result.problematic_labels,
        'recommendations': result.recommendations
    }

    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Prometheus metrics for cardinality issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze metrics from Prometheus server
  %(prog)s --url http://localhost:9090

  # Analyze metrics from file
  %(prog)s --metrics-file metrics.txt

  # Output as JSON
  %(prog)s --url http://localhost:9090 --json

  # Filter by metric name
  %(prog)s --url http://localhost:9090 --filter "http_.*"

  # Show only high cardinality metrics
  %(prog)s --url http://localhost:9090 --severity high
        """
    )

    parser.add_argument(
        '--url',
        help='Prometheus server URL (e.g., http://localhost:9090)'
    )

    parser.add_argument(
        '--metrics-file',
        help='Path to metrics file (Prometheus text format)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    parser.add_argument(
        '--filter',
        help='Filter metrics by regex pattern'
    )

    parser.add_argument(
        '--severity',
        choices=['low', 'medium', 'high', 'critical'],
        help='Show only metrics with specified severity or higher'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Limit number of metrics shown (default: 10)'
    )

    args = parser.parse_args()

    # Validate input
    if not args.url and not args.metrics_file:
        parser.error('Either --url or --metrics-file must be provided')

    try:
        # Initialize analyzer
        analyzer = MetricsAnalyzer(prometheus_url=args.url)

        # Get series list
        if args.url:
            print("Fetching metrics from Prometheus...", file=sys.stderr)
            series_list = analyzer.client.get_all_series()
        else:
            print(f"Reading metrics from {args.metrics_file}...", file=sys.stderr)
            series_list = analyzer.parse_metrics_file(args.metrics_file)

        print(f"Found {len(series_list)} time series", file=sys.stderr)

        # Analyze
        print("Analyzing cardinality...", file=sys.stderr)
        result = analyzer.analyze(series_list)

        # Filter by pattern
        if args.filter:
            pattern = re.compile(args.filter)
            result.metrics = [m for m in result.metrics if pattern.match(m.name)]

        # Filter by severity
        if args.severity:
            severity_order = ['low', 'medium', 'high', 'critical']
            min_severity_idx = severity_order.index(args.severity)
            result.metrics = [
                m for m in result.metrics
                if severity_order.index(m.severity) >= min_severity_idx
            ]

        # Limit results
        result.metrics = result.metrics[:args.limit]

        # Output
        if args.json:
            print(format_json(result))
        else:
            print(format_human_readable(result))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
