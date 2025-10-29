#!/usr/bin/env python3
"""
Resource Usage Analysis Tool

This script analyzes historical resource usage patterns to identify trends,
anomalies, peak usage, cost optimization opportunities, and right-sizing recommendations.

Usage:
    analyze_resource_usage.py --prometheus http://localhost:9090 --days 30
    analyze_resource_usage.py --input metrics.csv --resources cpu,memory,disk
    analyze_resource_usage.py --prometheus http://localhost:9090 --detect-anomalies
    analyze_resource_usage.py --input metrics.csv --cost-analysis --json
    analyze_resource_usage.py --prometheus http://localhost:9090 --recommend-rightsizing
"""

import argparse
import sys
import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')


@dataclass
class ResourceMetrics:
    """Container for resource metrics."""
    resource_name: str
    avg_utilization: float
    min_utilization: float
    max_utilization: float
    p50_utilization: float
    p95_utilization: float
    p99_utilization: float
    trend_slope: float
    trend_direction: str
    data_points: int
    time_period_days: int


@dataclass
class AnomalyDetection:
    """Container for anomaly detection results."""
    resource_name: str
    anomaly_count: int
    anomaly_timestamps: List[str]
    anomaly_values: List[float]
    anomaly_percent: float
    max_z_score: float


@dataclass
class PeakUsagePattern:
    """Container for peak usage patterns."""
    resource_name: str
    peak_value: float
    peak_timestamp: str
    peak_hour_of_day: Optional[int]
    peak_day_of_week: Optional[int]
    avg_peak_value: float
    peak_frequency: str


@dataclass
class CostAnalysis:
    """Container for cost analysis."""
    resource_type: str
    current_utilization: float
    recommended_utilization: float
    current_monthly_cost: float
    optimized_monthly_cost: float
    potential_savings: float
    savings_percent: float
    recommendation: str


@dataclass
class RightsizingRecommendation:
    """Container for rightsizing recommendations."""
    resource_id: str
    resource_type: str
    current_size: str
    current_utilization: float
    recommended_size: str
    action: str
    estimated_monthly_savings: float
    confidence: str
    reason: str


class ResourceAnalyzer:
    """Main resource usage analyzer."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def log(self, message: str) -> None:
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[INFO] {message}", file=sys.stderr)

    def load_data_from_csv(self, filepath: Path) -> pd.DataFrame:
        """Load resource usage data from CSV."""
        self.log(f"Loading data from {filepath}")

        try:
            df = pd.read_csv(filepath)

            # Expected columns: timestamp, resource, value
            if 'timestamp' not in df.columns:
                df['timestamp'] = pd.to_datetime(df.iloc[:, 0])

            df['timestamp'] = pd.to_datetime(df['timestamp'])

            self.log(f"Loaded {len(df)} data points")
            return df

        except Exception as e:
            raise ValueError(f"Failed to load CSV: {e}")

    def load_data_from_prometheus(
        self,
        prometheus_url: str,
        queries: Dict[str, str],
        lookback_days: int = 30
    ) -> pd.DataFrame:
        """Load resource usage data from Prometheus."""
        import requests

        self.log(f"Querying Prometheus for {len(queries)} metrics")

        end_time = datetime.now()
        start_time = end_time - timedelta(days=lookback_days)

        all_data = []

        for resource_name, query in queries.items():
            try:
                response = requests.get(
                    f"{prometheus_url}/api/v1/query_range",
                    params={
                        'query': query,
                        'start': start_time.timestamp(),
                        'end': end_time.timestamp(),
                        'step': '5m'
                    },
                    timeout=30
                )

                response.raise_for_status()
                data = response.json()

                if data['status'] != 'success':
                    self.log(f"Query failed for {resource_name}: {data}")
                    continue

                results = data['data']['result']
                if not results:
                    self.log(f"No data for {resource_name}")
                    continue

                # Process first result series
                values = results[0]['values']

                for timestamp, value in values:
                    all_data.append({
                        'timestamp': pd.to_datetime(timestamp, unit='s'),
                        'resource': resource_name,
                        'value': float(value)
                    })

                self.log(f"Retrieved {len(values)} points for {resource_name}")

            except Exception as e:
                self.log(f"Failed to query {resource_name}: {e}")

        if not all_data:
            raise ValueError("No data retrieved from Prometheus")

        df = pd.DataFrame(all_data)
        self.log(f"Total data points: {len(df)}")
        return df

    def analyze_resource_metrics(
        self,
        data: pd.DataFrame,
        resource: str
    ) -> ResourceMetrics:
        """Analyze metrics for a single resource."""
        self.log(f"Analyzing metrics for {resource}")

        resource_data = data[data['resource'] == resource]

        if resource_data.empty:
            raise ValueError(f"No data for resource: {resource}")

        values = resource_data['value'].values

        # Calculate percentiles
        p50 = np.percentile(values, 50)
        p95 = np.percentile(values, 95)
        p99 = np.percentile(values, 99)

        # Calculate trend
        X = np.arange(len(values))
        trend_slope = np.polyfit(X, values, 1)[0]

        if abs(trend_slope) < 0.01:
            trend_direction = 'stable'
        elif trend_slope > 0:
            trend_direction = 'increasing'
        else:
            trend_direction = 'decreasing'

        # Time period
        time_period = (resource_data['timestamp'].max() - resource_data['timestamp'].min()).days

        return ResourceMetrics(
            resource_name=resource,
            avg_utilization=float(np.mean(values)),
            min_utilization=float(np.min(values)),
            max_utilization=float(np.max(values)),
            p50_utilization=float(p50),
            p95_utilization=float(p95),
            p99_utilization=float(p99),
            trend_slope=float(trend_slope),
            trend_direction=trend_direction,
            data_points=len(values),
            time_period_days=time_period
        )

    def detect_anomalies(
        self,
        data: pd.DataFrame,
        resource: str,
        method: str = 'zscore',
        threshold: float = 3.0
    ) -> AnomalyDetection:
        """Detect anomalies in resource usage."""
        self.log(f"Detecting anomalies in {resource} using {method}")

        resource_data = data[data['resource'] == resource].copy()

        if resource_data.empty:
            raise ValueError(f"No data for resource: {resource}")

        values = resource_data['value'].values

        if method == 'zscore':
            # Z-score method
            mean = np.mean(values)
            std = np.std(values)
            z_scores = np.abs((values - mean) / std)

            anomaly_mask = z_scores > threshold
            max_z_score = float(np.max(z_scores))

        elif method == 'iqr':
            # Interquartile range method
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1

            lower_bound = q1 - (1.5 * iqr)
            upper_bound = q3 + (1.5 * iqr)

            anomaly_mask = (values < lower_bound) | (values > upper_bound)
            max_z_score = 0.0

        elif method == 'isolation_forest':
            # Isolation Forest
            try:
                from sklearn.ensemble import IsolationForest

                clf = IsolationForest(contamination=0.05, random_state=42)
                predictions = clf.fit_predict(values.reshape(-1, 1))

                anomaly_mask = predictions == -1
                max_z_score = 0.0

            except ImportError:
                self.log("sklearn not available, falling back to zscore")
                return self.detect_anomalies(data, resource, method='zscore', threshold=threshold)

        else:
            raise ValueError(f"Unknown method: {method}")

        # Extract anomalies
        anomaly_indices = np.where(anomaly_mask)[0]
        anomaly_timestamps = resource_data.iloc[anomaly_indices]['timestamp']
        anomaly_values = values[anomaly_indices]

        anomaly_count = len(anomaly_indices)
        anomaly_percent = (anomaly_count / len(values)) * 100

        return AnomalyDetection(
            resource_name=resource,
            anomaly_count=anomaly_count,
            anomaly_timestamps=[ts.isoformat() for ts in anomaly_timestamps],
            anomaly_values=anomaly_values.tolist(),
            anomaly_percent=float(anomaly_percent),
            max_z_score=max_z_score
        )

    def identify_peak_patterns(
        self,
        data: pd.DataFrame,
        resource: str
    ) -> PeakUsagePattern:
        """Identify peak usage patterns."""
        self.log(f"Identifying peak patterns for {resource}")

        resource_data = data[data['resource'] == resource].copy()

        if resource_data.empty:
            raise ValueError(f"No data for resource: {resource}")

        # Find absolute peak
        peak_idx = resource_data['value'].idxmax()
        peak_row = resource_data.loc[peak_idx]
        peak_value = float(peak_row['value'])
        peak_timestamp = peak_row['timestamp']

        # Extract time features
        resource_data['hour'] = resource_data['timestamp'].dt.hour
        resource_data['dayofweek'] = resource_data['timestamp'].dt.dayofweek

        # Find typical peak hour
        hourly_avg = resource_data.groupby('hour')['value'].mean()
        peak_hour = int(hourly_avg.idxmax())

        # Find typical peak day
        daily_avg = resource_data.groupby('dayofweek')['value'].mean()
        peak_day = int(daily_avg.idxmax())

        # Calculate average of top 5% values (typical peak)
        threshold = np.percentile(resource_data['value'], 95)
        peak_values = resource_data[resource_data['value'] >= threshold]['value']
        avg_peak_value = float(np.mean(peak_values))

        # Determine peak frequency
        peaks = resource_data[resource_data['value'] >= threshold]
        time_between_peaks = peaks['timestamp'].diff().dt.total_seconds() / 3600  # Hours
        avg_time_between_peaks = time_between_peaks.mean()

        if avg_time_between_peaks < 24:
            peak_frequency = 'multiple_daily'
        elif avg_time_between_peaks < 168:  # 7 days
            peak_frequency = 'daily'
        else:
            peak_frequency = 'weekly_or_less'

        return PeakUsagePattern(
            resource_name=resource,
            peak_value=peak_value,
            peak_timestamp=peak_timestamp.isoformat(),
            peak_hour_of_day=peak_hour,
            peak_day_of_week=peak_day,
            avg_peak_value=avg_peak_value,
            peak_frequency=peak_frequency
        )

    def analyze_cost_optimization(
        self,
        metrics: ResourceMetrics,
        resource_type: str,
        current_monthly_cost: float,
        target_utilization: float = 0.70
    ) -> CostAnalysis:
        """Analyze cost optimization opportunities."""
        self.log(f"Analyzing cost optimization for {metrics.resource_name}")

        current_util = metrics.avg_utilization / 100.0  # Convert to decimal

        if current_util < 0.30:
            # Significantly under-utilized
            savings_ratio = 0.50  # Potential 50% savings
            recommendation = "Downsize resource by 50%"
            optimized_util = target_utilization
        elif current_util < target_utilization:
            # Moderately under-utilized
            savings_ratio = (target_utilization - current_util) / target_utilization
            recommendation = f"Downsize to match {target_utilization*100:.0f}% utilization target"
            optimized_util = target_utilization
        elif current_util > 0.85:
            # Over-utilized
            savings_ratio = -0.30  # Need to add capacity (negative savings)
            recommendation = "Add capacity to reduce utilization below 85%"
            optimized_util = target_utilization
        else:
            # Well-utilized
            savings_ratio = 0.0
            recommendation = "Resource is well-sized"
            optimized_util = current_util

        optimized_monthly_cost = current_monthly_cost * (1 - savings_ratio)
        potential_savings = current_monthly_cost - optimized_monthly_cost
        savings_percent = (potential_savings / current_monthly_cost) * 100 if current_monthly_cost > 0 else 0

        return CostAnalysis(
            resource_type=resource_type,
            current_utilization=metrics.avg_utilization,
            recommended_utilization=optimized_util * 100,
            current_monthly_cost=current_monthly_cost,
            optimized_monthly_cost=optimized_monthly_cost,
            potential_savings=potential_savings,
            savings_percent=float(savings_percent),
            recommendation=recommendation
        )

    def recommend_rightsizing(
        self,
        metrics: ResourceMetrics,
        resource_id: str,
        current_size: str,
        instance_sizes: Optional[List[str]] = None
    ) -> RightsizingRecommendation:
        """Generate rightsizing recommendations."""
        self.log(f"Generating rightsizing recommendation for {resource_id}")

        if instance_sizes is None:
            instance_sizes = [
                't3.micro', 't3.small', 't3.medium', 't3.large', 't3.xlarge', 't3.2xlarge',
                'm5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge'
            ]

        current_util = metrics.avg_utilization
        p95_util = metrics.p95_utilization

        # Determine action
        if current_util < 30 and p95_util < 50:
            action = 'downsize'
            confidence = 'high'
            reason = f'Low average utilization ({current_util:.1f}%) and P95 ({p95_util:.1f}%)'

            # Recommend smaller size
            try:
                current_idx = instance_sizes.index(current_size)
                recommended_size = instance_sizes[max(0, current_idx - 1)]
                estimated_savings = 100.0  # Placeholder
            except ValueError:
                recommended_size = current_size
                estimated_savings = 0.0

        elif current_util > 80 or p95_util > 90:
            action = 'upsize'
            confidence = 'high'
            reason = f'High utilization (avg: {current_util:.1f}%, P95: {p95_util:.1f}%)'

            # Recommend larger size
            try:
                current_idx = instance_sizes.index(current_size)
                recommended_size = instance_sizes[min(len(instance_sizes) - 1, current_idx + 1)]
                estimated_savings = -150.0  # Negative = additional cost
            except ValueError:
                recommended_size = current_size
                estimated_savings = 0.0

        else:
            action = 'keep'
            confidence = 'high'
            reason = f'Well-sized (avg: {current_util:.1f}%, P95: {p95_util:.1f}%)'
            recommended_size = current_size
            estimated_savings = 0.0

        return RightsizingRecommendation(
            resource_id=resource_id,
            resource_type=metrics.resource_name,
            current_size=current_size,
            current_utilization=current_util,
            recommended_size=recommended_size,
            action=action,
            estimated_monthly_savings=estimated_savings,
            confidence=confidence,
            reason=reason
        )

    def generate_utilization_report(
        self,
        metrics: List[ResourceMetrics]
    ) -> Dict[str, Any]:
        """Generate comprehensive utilization report."""
        self.log("Generating utilization report")

        report = {
            'summary': {
                'total_resources': len(metrics),
                'avg_utilization': np.mean([m.avg_utilization for m in metrics]),
                'resources_over_80_percent': sum(1 for m in metrics if m.avg_utilization > 80),
                'resources_under_30_percent': sum(1 for m in metrics if m.avg_utilization < 30),
            },
            'resources': []
        }

        for metric in metrics:
            report['resources'].append({
                'name': metric.resource_name,
                'avg_utilization': metric.avg_utilization,
                'p95_utilization': metric.p95_utilization,
                'trend': metric.trend_direction,
                'status': self._get_utilization_status(metric.avg_utilization)
            })

        return report

    def _get_utilization_status(self, utilization: float) -> str:
        """Get status label for utilization level."""
        if utilization > 85:
            return 'over_utilized'
        elif utilization > 70:
            return 'well_utilized'
        elif utilization > 30:
            return 'under_utilized'
        else:
            return 'severely_under_utilized'

    def visualize_usage_trends(
        self,
        data: pd.DataFrame,
        resources: List[str],
        output_file: Path
    ) -> None:
        """Visualize resource usage trends."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
        except ImportError:
            self.log("Matplotlib not installed, skipping visualization")
            return

        self.log(f"Generating visualization: {output_file}")

        fig, axes = plt.subplots(len(resources), 1, figsize=(14, 4 * len(resources)))

        if len(resources) == 1:
            axes = [axes]

        for ax, resource in zip(axes, resources):
            resource_data = data[data['resource'] == resource]

            ax.plot(
                resource_data['timestamp'],
                resource_data['value'],
                linewidth=1
            )

            # Add utilization zones
            ax.axhline(y=30, color='orange', linestyle='--', alpha=0.5, label='Under-utilized')
            ax.axhline(y=70, color='green', linestyle='--', alpha=0.5, label='Target')
            ax.axhline(y=85, color='red', linestyle='--', alpha=0.5, label='Over-utilized')

            ax.set_title(f'{resource} Usage Over Time', fontsize=12, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Utilization (%)')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)

            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300)
        self.log(f"Visualization saved to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Resource usage analysis tool for capacity planning',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze from Prometheus
    %(prog)s --prometheus http://localhost:9090 --days 30

    # Analyze from CSV
    %(prog)s --input metrics.csv --resources cpu,memory,disk

    # Detect anomalies
    %(prog)s --prometheus http://localhost:9090 --detect-anomalies

    # Cost analysis
    %(prog)s --input metrics.csv --cost-analysis --costs '{"cpu": 100, "memory": 50}'

    # Rightsizing recommendations
    %(prog)s --prometheus http://localhost:9090 --recommend-rightsizing

    # Generate report with visualization
    %(prog)s --input metrics.csv --visualize --output report.png
        """
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--input',
        type=Path,
        help='Input CSV file with timestamp,resource,value columns'
    )
    input_group.add_argument(
        '--prometheus',
        help='Prometheus URL (e.g., http://localhost:9090)'
    )

    # Analysis options
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Days of historical data to analyze (default: 30)'
    )
    parser.add_argument(
        '--resources',
        help='Comma-separated list of resources to analyze'
    )
    parser.add_argument(
        '--detect-anomalies',
        action='store_true',
        help='Detect anomalies in resource usage'
    )
    parser.add_argument(
        '--anomaly-method',
        choices=['zscore', 'iqr', 'isolation_forest'],
        default='zscore',
        help='Anomaly detection method (default: zscore)'
    )
    parser.add_argument(
        '--anomaly-threshold',
        type=float,
        default=3.0,
        help='Threshold for anomaly detection (default: 3.0)'
    )
    parser.add_argument(
        '--cost-analysis',
        action='store_true',
        help='Analyze cost optimization opportunities'
    )
    parser.add_argument(
        '--costs',
        type=str,
        help='JSON string with resource costs, e.g., \'{"cpu": 100, "memory": 50}\''
    )
    parser.add_argument(
        '--recommend-rightsizing',
        action='store_true',
        help='Generate rightsizing recommendations'
    )

    # Output options
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file path'
    )
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Generate visualization'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    # Misc options
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    analyzer = ResourceAnalyzer(verbose=args.verbose)

    try:
        # Load data
        if args.input:
            data = analyzer.load_data_from_csv(args.input)
        else:
            # Default Prometheus queries
            queries = {
                'cpu': 'avg(rate(node_cpu_seconds_total{mode!="idle"}[5m])) * 100',
                'memory': '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
                'disk': '(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100'
            }

            if args.resources:
                custom_resources = args.resources.split(',')
                queries = {r: queries.get(r, r) for r in custom_resources}

            data = analyzer.load_data_from_prometheus(
                args.prometheus,
                queries,
                args.days
            )

        # Get resource list
        resources = data['resource'].unique().tolist()

        results = {}

        # Analyze metrics
        metrics_list = []
        for resource in resources:
            metrics = analyzer.analyze_resource_metrics(data, resource)
            metrics_list.append(metrics)
            results[resource] = {'metrics': asdict(metrics)}

        # Detect anomalies
        if args.detect_anomalies:
            for resource in resources:
                anomalies = analyzer.detect_anomalies(
                    data,
                    resource,
                    method=args.anomaly_method,
                    threshold=args.anomaly_threshold
                )
                results[resource]['anomalies'] = asdict(anomalies)

        # Identify peak patterns
        for resource in resources:
            peaks = analyzer.identify_peak_patterns(data, resource)
            results[resource]['peak_patterns'] = asdict(peaks)

        # Cost analysis
        if args.cost_analysis:
            costs = {}
            if args.costs:
                costs = json.loads(args.costs)

            for resource in resources:
                cost = costs.get(resource, 100.0)  # Default cost
                metrics = metrics_list[resources.index(resource)]
                cost_analysis = analyzer.analyze_cost_optimization(
                    metrics,
                    resource,
                    cost
                )
                results[resource]['cost_analysis'] = asdict(cost_analysis)

        # Rightsizing recommendations
        if args.recommend_rightsizing:
            for resource in resources:
                metrics = metrics_list[resources.index(resource)]
                recommendation = analyzer.recommend_rightsizing(
                    metrics,
                    resource_id=f"{resource}-001",
                    current_size='m5.large'
                )
                results[resource]['rightsizing'] = asdict(recommendation)

        # Generate report
        report = analyzer.generate_utilization_report(metrics_list)
        results['summary'] = report

        # Output results
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n=== Resource Usage Analysis ===\n")
            print(f"Resources analyzed: {len(resources)}")
            print(f"Time period: {args.days} days")
            print(f"\nSummary:")
            print(f"  Average utilization: {report['summary']['avg_utilization']:.1f}%")
            print(f"  Over-utilized (>80%): {report['summary']['resources_over_80_percent']}")
            print(f"  Under-utilized (<30%): {report['summary']['resources_under_30_percent']}")

            for resource in resources:
                print(f"\n--- {resource} ---")
                metrics = results[resource]['metrics']
                print(f"  Average: {metrics['avg_utilization']:.1f}%")
                print(f"  P95: {metrics['p95_utilization']:.1f}%")
                print(f"  P99: {metrics['p99_utilization']:.1f}%")
                print(f"  Trend: {metrics['trend_direction']}")

                if 'anomalies' in results[resource]:
                    anomalies = results[resource]['anomalies']
                    print(f"  Anomalies: {anomalies['anomaly_count']} ({anomalies['anomaly_percent']:.2f}%)")

                if 'cost_analysis' in results[resource]:
                    cost = results[resource]['cost_analysis']
                    print(f"  Cost savings: ${cost['potential_savings']:.2f}/month ({cost['savings_percent']:.1f}%)")
                    print(f"  Recommendation: {cost['recommendation']}")

        # Export to file
        if args.output and not args.visualize:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults exported to {args.output}")

        # Visualize
        if args.visualize:
            vis_output = args.output if args.output else Path('usage_analysis.png')
            analyzer.visualize_usage_trends(data, resources, vis_output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
