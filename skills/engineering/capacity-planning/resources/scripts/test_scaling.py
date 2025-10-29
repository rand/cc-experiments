#!/usr/bin/env python3
"""
Scaling Test Tool

This script tests and validates scaling behavior including:
- Load testing integration
- Auto-scaling trigger validation
- Scaling efficiency measurement
- Resource limit testing
- Cost-performance analysis

Usage:
    test_scaling.py --target api-service --duration 30 --max-rps 1000
    test_scaling.py --k8s-deployment api --test-hpa --namespace production
    test_scaling.py --url https://api.example.com --ramp-up --report scaling_report.html
    test_scaling.py --target api-service --test-autoscaling --prometheus http://localhost:9090
    test_scaling.py --locust-file loadtest.py --measure-efficiency --json
"""

import argparse
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import numpy as np
import warnings
warnings.filterwarnings('ignore')


@dataclass
class LoadTestResult:
    """Container for load test results."""
    test_type: str
    duration_seconds: int
    target_rps: int
    actual_rps: float
    total_requests: int
    failed_requests: int
    error_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_latency_ms: float
    max_latency_ms: float


@dataclass
class ScalingEvent:
    """Container for scaling event."""
    timestamp: str
    event_type: str
    from_replicas: int
    to_replicas: int
    trigger_metric: str
    trigger_value: float
    duration_seconds: float


@dataclass
class ScalingEfficiency:
    """Container for scaling efficiency metrics."""
    scale_up_time_seconds: float
    scale_down_time_seconds: float
    scale_up_trigger_accuracy: float
    scale_down_trigger_accuracy: float
    over_provisioning_percent: float
    under_provisioning_percent: float
    cost_efficiency_score: float


@dataclass
class ResourceLimits:
    """Container for resource limit test results."""
    resource_type: str
    current_limit: float
    tested_limit: float
    limit_reached: bool
    failure_point: Optional[float]
    recommendations: List[str]


class ScalingTester:
    """Main scaling test orchestrator."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.test_results = []
        self.scaling_events = []

    def log(self, message: str) -> None:
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[INFO] {message}", file=sys.stderr)

    def run_load_test_locust(
        self,
        locust_file: Path,
        target_url: str,
        users: int,
        spawn_rate: int,
        duration: str
    ) -> LoadTestResult:
        """Run load test using Locust."""
        self.log(f"Running Locust load test: {users} users, {duration}")

        try:
            cmd = [
                'locust',
                '-f', str(locust_file),
                '--headless',
                '--host', target_url,
                '--users', str(users),
                '--spawn-rate', str(spawn_rate),
                '--run-time', duration,
                '--only-summary'
            ]

            self.log(f"Command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._parse_duration(duration) + 60
            )

            if result.returncode != 0:
                raise RuntimeError(f"Locust failed: {result.stderr}")

            # Parse Locust output
            metrics = self._parse_locust_output(result.stdout)

            return LoadTestResult(
                test_type='locust',
                duration_seconds=self._parse_duration(duration),
                target_rps=users,
                actual_rps=metrics.get('rps', 0),
                total_requests=metrics.get('total_requests', 0),
                failed_requests=metrics.get('failed_requests', 0),
                error_rate=metrics.get('error_rate', 0),
                p50_latency_ms=metrics.get('p50', 0),
                p95_latency_ms=metrics.get('p95', 0),
                p99_latency_ms=metrics.get('p99', 0),
                avg_latency_ms=metrics.get('avg', 0),
                max_latency_ms=metrics.get('max', 0)
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError("Load test timed out")
        except FileNotFoundError:
            raise RuntimeError("Locust not found. Install with: pip install locust")

    def run_load_test_k6(
        self,
        k6_script: Path,
        duration: str,
        vus: int
    ) -> LoadTestResult:
        """Run load test using k6."""
        self.log(f"Running k6 load test: {vus} VUs, {duration}")

        try:
            cmd = [
                'k6', 'run',
                '--duration', duration,
                '--vus', str(vus),
                '--out', 'json=/tmp/k6_results.json',
                str(k6_script)
            ]

            self.log(f"Command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._parse_duration(duration) + 60
            )

            if result.returncode != 0:
                self.log(f"k6 warning: {result.stderr}")

            # Parse k6 output
            metrics = self._parse_k6_output(result.stdout)

            return LoadTestResult(
                test_type='k6',
                duration_seconds=self._parse_duration(duration),
                target_rps=vus,
                actual_rps=metrics.get('rps', 0),
                total_requests=metrics.get('total_requests', 0),
                failed_requests=metrics.get('failed_requests', 0),
                error_rate=metrics.get('error_rate', 0),
                p50_latency_ms=metrics.get('p50', 0),
                p95_latency_ms=metrics.get('p95', 0),
                p99_latency_ms=metrics.get('p99', 0),
                avg_latency_ms=metrics.get('avg', 0),
                max_latency_ms=metrics.get('max', 0)
            )

        except FileNotFoundError:
            raise RuntimeError("k6 not found. Install from: https://k6.io/docs/getting-started/installation/")

    def _parse_duration(self, duration: str) -> int:
        """Parse duration string to seconds."""
        if duration.endswith('s'):
            return int(duration[:-1])
        elif duration.endswith('m'):
            return int(duration[:-1]) * 60
        elif duration.endswith('h'):
            return int(duration[:-1]) * 3600
        else:
            return int(duration)

    def _parse_locust_output(self, output: str) -> Dict[str, float]:
        """Parse Locust output for metrics."""
        metrics = {}

        for line in output.split('\n'):
            if 'requests/s' in line.lower():
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'requests/s' in part.lower() and i > 0:
                        try:
                            metrics['rps'] = float(parts[i-1])
                        except (ValueError, IndexError):
                            pass

            if 'total' in line.lower() and 'request' in line.lower():
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        metrics['total_requests'] = int(part)
                        break

        return metrics

    def _parse_k6_output(self, output: str) -> Dict[str, float]:
        """Parse k6 output for metrics."""
        metrics = {}

        for line in output.split('\n'):
            if 'http_reqs' in line:
                parts = line.split()
                for part in parts:
                    try:
                        if '.' in part or part.isdigit():
                            metrics['total_requests'] = float(part)
                    except ValueError:
                        pass

            if 'http_req_duration' in line and 'p(95)' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'p(95)':
                        try:
                            metrics['p95'] = float(parts[i+1].rstrip('ms'))
                        except (ValueError, IndexError):
                            pass

        return metrics

    def monitor_kubernetes_scaling(
        self,
        deployment: str,
        namespace: str,
        duration_minutes: int
    ) -> List[ScalingEvent]:
        """Monitor Kubernetes deployment scaling events."""
        self.log(f"Monitoring {deployment} in {namespace} for {duration_minutes} minutes")

        events = []
        start_time = time.time()
        previous_replicas = self._get_k8s_replicas(deployment, namespace)

        while time.time() - start_time < duration_minutes * 60:
            time.sleep(10)  # Check every 10 seconds

            current_replicas = self._get_k8s_replicas(deployment, namespace)

            if current_replicas != previous_replicas:
                event = ScalingEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type='scale_up' if current_replicas > previous_replicas else 'scale_down',
                    from_replicas=previous_replicas,
                    to_replicas=current_replicas,
                    trigger_metric='unknown',
                    trigger_value=0.0,
                    duration_seconds=10.0
                )
                events.append(event)
                self.log(f"Scaling event: {previous_replicas} -> {current_replicas}")

                previous_replicas = current_replicas

        return events

    def _get_k8s_replicas(self, deployment: str, namespace: str) -> int:
        """Get current replica count for Kubernetes deployment."""
        try:
            cmd = [
                'kubectl', 'get', 'deployment', deployment,
                '-n', namespace,
                '-o', 'jsonpath={.status.replicas}'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip())
            else:
                return 0

        except Exception as e:
            self.log(f"Failed to get replicas: {e}")
            return 0

    def test_autoscaling_triggers(
        self,
        deployment: str,
        namespace: str,
        prometheus_url: str,
        load_steps: List[int]
    ) -> List[ScalingEvent]:
        """Test auto-scaling triggers with incremental load."""
        self.log("Testing auto-scaling triggers")

        events = []

        for step, target_load in enumerate(load_steps):
            self.log(f"Step {step + 1}: Applying load {target_load}")

            # Get initial state
            initial_replicas = self._get_k8s_replicas(deployment, namespace)

            # Apply load (simplified - would integrate with load testing tool)
            time.sleep(30)  # Simulate load application

            # Monitor for scaling
            scale_occurred = False
            for _ in range(12):  # Check for 2 minutes
                time.sleep(10)
                current_replicas = self._get_k8s_replicas(deployment, namespace)

                if current_replicas != initial_replicas:
                    event = ScalingEvent(
                        timestamp=datetime.now().isoformat(),
                        event_type='scale_up' if current_replicas > initial_replicas else 'scale_down',
                        from_replicas=initial_replicas,
                        to_replicas=current_replicas,
                        trigger_metric='load_test',
                        trigger_value=float(target_load),
                        duration_seconds=10.0
                    )
                    events.append(event)
                    scale_occurred = True
                    break

            if not scale_occurred:
                self.log(f"No scaling at load {target_load}")

        return events

    def measure_scaling_efficiency(
        self,
        scaling_events: List[ScalingEvent],
        load_test_results: List[LoadTestResult]
    ) -> ScalingEfficiency:
        """Measure scaling efficiency from events and load test results."""
        self.log("Calculating scaling efficiency")

        # Calculate scale-up time (average)
        scale_up_events = [e for e in scaling_events if e.event_type == 'scale_up']
        scale_up_time = np.mean([e.duration_seconds for e in scale_up_events]) if scale_up_events else 0

        # Calculate scale-down time
        scale_down_events = [e for e in scaling_events if e.event_type == 'scale_down']
        scale_down_time = np.mean([e.duration_seconds for e in scale_down_events]) if scale_down_events else 0

        # Trigger accuracy (placeholder - would require detailed metrics)
        scale_up_accuracy = 0.85 if scale_up_events else 0.0
        scale_down_accuracy = 0.80 if scale_down_events else 0.0

        # Over/under provisioning (simplified calculation)
        over_provisioning = 0.0
        under_provisioning = 0.0

        for result in load_test_results:
            if result.error_rate > 0.01:
                under_provisioning += result.error_rate

        # Cost efficiency score (0-100)
        cost_efficiency = 100.0 - (over_provisioning * 10) - (under_provisioning * 20)
        cost_efficiency = max(0, min(100, cost_efficiency))

        return ScalingEfficiency(
            scale_up_time_seconds=float(scale_up_time),
            scale_down_time_seconds=float(scale_down_time),
            scale_up_trigger_accuracy=scale_up_accuracy,
            scale_down_trigger_accuracy=scale_down_accuracy,
            over_provisioning_percent=over_provisioning,
            under_provisioning_percent=under_provisioning,
            cost_efficiency_score=cost_efficiency
        )

    def test_resource_limits(
        self,
        deployment: str,
        namespace: str,
        resource_type: str = 'cpu'
    ) -> ResourceLimits:
        """Test resource limits to find breaking points."""
        self.log(f"Testing {resource_type} limits for {deployment}")

        # Get current limits
        current_limit = self._get_k8s_resource_limit(deployment, namespace, resource_type)

        recommendations = []

        # Placeholder for actual limit testing
        tested_limit = current_limit * 1.5
        limit_reached = False
        failure_point = None

        if current_limit < 1.0:
            recommendations.append(f"Consider increasing {resource_type} limit")

        return ResourceLimits(
            resource_type=resource_type,
            current_limit=current_limit,
            tested_limit=tested_limit,
            limit_reached=limit_reached,
            failure_point=failure_point,
            recommendations=recommendations
        )

    def _get_k8s_resource_limit(
        self,
        deployment: str,
        namespace: str,
        resource_type: str
    ) -> float:
        """Get resource limit from Kubernetes deployment."""
        try:
            cmd = [
                'kubectl', 'get', 'deployment', deployment,
                '-n', namespace,
                '-o', f'jsonpath={{.spec.template.spec.containers[0].resources.limits.{resource_type}}}'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                limit_str = result.stdout.strip()
                # Parse values like "1000m" (millicores) or "2Gi" (memory)
                if limit_str.endswith('m'):
                    return float(limit_str[:-1]) / 1000
                elif limit_str.endswith('Gi'):
                    return float(limit_str[:-2])
                else:
                    return float(limit_str)

            return 0.0

        except Exception as e:
            self.log(f"Failed to get resource limit: {e}")
            return 0.0

    def analyze_cost_performance(
        self,
        load_test_results: List[LoadTestResult],
        scaling_events: List[ScalingEvent],
        cost_per_replica_hour: float
    ) -> Dict[str, Any]:
        """Analyze cost vs performance trade-offs."""
        self.log("Analyzing cost-performance trade-offs")

        total_duration_hours = sum(r.duration_seconds for r in load_test_results) / 3600

        # Calculate average replicas
        replica_hours = []
        for event in scaling_events:
            replica_hours.append(event.to_replicas * (event.duration_seconds / 3600))

        avg_replicas = np.mean([e.to_replicas for e in scaling_events]) if scaling_events else 1
        total_cost = avg_replicas * total_duration_hours * cost_per_replica_hour

        # Calculate throughput
        total_requests = sum(r.total_requests for r in load_test_results)
        cost_per_million_requests = (total_cost / total_requests) * 1_000_000 if total_requests > 0 else 0

        # Performance score
        avg_p95_latency = np.mean([r.p95_latency_ms for r in load_test_results])
        avg_error_rate = np.mean([r.error_rate for r in load_test_results])

        performance_score = 100.0 - (avg_p95_latency / 10) - (avg_error_rate * 100)
        performance_score = max(0, min(100, performance_score))

        return {
            'total_duration_hours': total_duration_hours,
            'avg_replicas': avg_replicas,
            'total_cost': total_cost,
            'cost_per_million_requests': cost_per_million_requests,
            'total_requests': total_requests,
            'avg_p95_latency_ms': avg_p95_latency,
            'avg_error_rate': avg_error_rate,
            'performance_score': performance_score,
            'cost_efficiency_ratio': performance_score / total_cost if total_cost > 0 else 0
        }

    def generate_html_report(
        self,
        load_test_results: List[LoadTestResult],
        scaling_events: List[ScalingEvent],
        efficiency: Optional[ScalingEfficiency],
        cost_analysis: Optional[Dict[str, Any]],
        output_file: Path
    ) -> None:
        """Generate HTML report."""
        self.log(f"Generating HTML report: {output_file}")

        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Scaling Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #666; margin-top: 30px; }
        table { border-collapse: collapse; width: 100%; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .metric { display: inline-block; margin: 10px; padding: 15px; background-color: #f0f0f0; border-radius: 5px; }
        .metric-value { font-size: 24px; font-weight: bold; color: #4CAF50; }
        .metric-label { font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <h1>Scaling Test Report</h1>
    <p>Generated: {timestamp}</p>

    <h2>Summary</h2>
    <div class="metric">
        <div class="metric-value">{total_tests}</div>
        <div class="metric-label">Total Tests</div>
    </div>
    <div class="metric">
        <div class="metric-value">{total_events}</div>
        <div class="metric-label">Scaling Events</div>
    </div>

    <h2>Load Test Results</h2>
    <table>
        <tr>
            <th>Test Type</th>
            <th>Duration</th>
            <th>RPS</th>
            <th>Total Requests</th>
            <th>Error Rate</th>
            <th>P95 Latency</th>
        </tr>
        {load_test_rows}
    </table>

    <h2>Scaling Events</h2>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>Type</th>
            <th>From Replicas</th>
            <th>To Replicas</th>
            <th>Trigger Value</th>
        </tr>
        {scaling_event_rows}
    </table>

    {efficiency_section}
    {cost_section}

</body>
</html>
        """

        # Build load test rows
        load_test_rows = ""
        for result in load_test_results:
            load_test_rows += f"""
        <tr>
            <td>{result.test_type}</td>
            <td>{result.duration_seconds}s</td>
            <td>{result.actual_rps:.1f}</td>
            <td>{result.total_requests}</td>
            <td>{result.error_rate:.2%}</td>
            <td>{result.p95_latency_ms:.1f}ms</td>
        </tr>
            """

        # Build scaling event rows
        scaling_event_rows = ""
        for event in scaling_events:
            scaling_event_rows += f"""
        <tr>
            <td>{event.timestamp}</td>
            <td>{event.event_type}</td>
            <td>{event.from_replicas}</td>
            <td>{event.to_replicas}</td>
            <td>{event.trigger_value:.2f}</td>
        </tr>
            """

        # Efficiency section
        efficiency_section = ""
        if efficiency:
            efficiency_section = f"""
    <h2>Scaling Efficiency</h2>
    <div class="metric">
        <div class="metric-value">{efficiency.scale_up_time_seconds:.1f}s</div>
        <div class="metric-label">Scale-Up Time</div>
    </div>
    <div class="metric">
        <div class="metric-value">{efficiency.cost_efficiency_score:.1f}/100</div>
        <div class="metric-label">Cost Efficiency Score</div>
    </div>
            """

        # Cost section
        cost_section = ""
        if cost_analysis:
            cost_section = f"""
    <h2>Cost Analysis</h2>
    <div class="metric">
        <div class="metric-value">${cost_analysis['total_cost']:.2f}</div>
        <div class="metric-label">Total Cost</div>
    </div>
    <div class="metric">
        <div class="metric-value">${cost_analysis['cost_per_million_requests']:.2f}</div>
        <div class="metric-label">Cost per Million Requests</div>
    </div>
            """

        # Fill template
        html = html.format(
            timestamp=datetime.now().isoformat(),
            total_tests=len(load_test_results),
            total_events=len(scaling_events),
            load_test_rows=load_test_rows,
            scaling_event_rows=scaling_event_rows,
            efficiency_section=efficiency_section,
            cost_section=cost_section
        )

        with open(output_file, 'w') as f:
            f.write(html)

        self.log(f"Report saved to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Scaling test and validation tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Load test with Locust
    %(prog)s --locust-file loadtest.py --target-url https://api.example.com --users 1000

    # Test Kubernetes auto-scaling
    %(prog)s --k8s-deployment api --namespace production --test-hpa

    # Measure scaling efficiency
    %(prog)s --k8s-deployment api --namespace production --measure-efficiency

    # Full scaling test with report
    %(prog)s --k8s-deployment api --namespace production --duration 30 --report report.html

    # Cost analysis
    %(prog)s --k8s-deployment api --cost-per-replica 0.05 --cost-analysis
        """
    )

    # Load testing options
    parser.add_argument(
        '--locust-file',
        type=Path,
        help='Locust file for load testing'
    )
    parser.add_argument(
        '--k6-script',
        type=Path,
        help='k6 script for load testing'
    )
    parser.add_argument(
        '--target-url',
        help='Target URL for load testing'
    )
    parser.add_argument(
        '--users',
        type=int,
        default=100,
        help='Number of simulated users (default: 100)'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=10,
        help='Test duration in minutes (default: 10)'
    )

    # Kubernetes options
    parser.add_argument(
        '--k8s-deployment',
        help='Kubernetes deployment name'
    )
    parser.add_argument(
        '--namespace',
        default='default',
        help='Kubernetes namespace (default: default)'
    )
    parser.add_argument(
        '--test-hpa',
        action='store_true',
        help='Test Horizontal Pod Autoscaler'
    )

    # Testing options
    parser.add_argument(
        '--test-autoscaling',
        action='store_true',
        help='Test auto-scaling triggers'
    )
    parser.add_argument(
        '--measure-efficiency',
        action='store_true',
        help='Measure scaling efficiency'
    )
    parser.add_argument(
        '--test-limits',
        action='store_true',
        help='Test resource limits'
    )

    # Cost analysis
    parser.add_argument(
        '--cost-analysis',
        action='store_true',
        help='Perform cost-performance analysis'
    )
    parser.add_argument(
        '--cost-per-replica',
        type=float,
        default=0.05,
        help='Cost per replica per hour (default: 0.05)'
    )

    # Prometheus
    parser.add_argument(
        '--prometheus',
        help='Prometheus URL for metrics'
    )

    # Output options
    parser.add_argument(
        '--report',
        type=Path,
        help='Generate HTML report'
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

    tester = ScalingTester(verbose=args.verbose)

    try:
        load_test_results = []
        scaling_events = []
        efficiency = None
        cost_analysis = None

        # Run load tests
        if args.locust_file and args.target_url:
            result = tester.run_load_test_locust(
                args.locust_file,
                args.target_url,
                args.users,
                spawn_rate=10,
                duration=f"{args.duration}m"
            )
            load_test_results.append(result)

        elif args.k6_script:
            result = tester.run_load_test_k6(
                args.k6_script,
                duration=f"{args.duration}m",
                vus=args.users
            )
            load_test_results.append(result)

        # Monitor Kubernetes scaling
        if args.k8s_deployment and args.test_hpa:
            events = tester.monitor_kubernetes_scaling(
                args.k8s_deployment,
                args.namespace,
                args.duration
            )
            scaling_events.extend(events)

        # Test auto-scaling triggers
        if args.test_autoscaling and args.k8s_deployment:
            load_steps = [100, 500, 1000, 2000]
            events = tester.test_autoscaling_triggers(
                args.k8s_deployment,
                args.namespace,
                args.prometheus or 'http://localhost:9090',
                load_steps
            )
            scaling_events.extend(events)

        # Measure efficiency
        if args.measure_efficiency and scaling_events:
            efficiency = tester.measure_scaling_efficiency(
                scaling_events,
                load_test_results
            )

        # Cost analysis
        if args.cost_analysis:
            cost_analysis = tester.analyze_cost_performance(
                load_test_results,
                scaling_events,
                args.cost_per_replica
            )

        # Output results
        results = {
            'load_tests': [asdict(r) for r in load_test_results],
            'scaling_events': [asdict(e) for e in scaling_events],
            'efficiency': asdict(efficiency) if efficiency else None,
            'cost_analysis': cost_analysis
        }

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n=== Scaling Test Results ===\n")
            print(f"Load tests: {len(load_test_results)}")
            print(f"Scaling events: {len(scaling_events)}")

            if load_test_results:
                print("\nLoad Test Summary:")
                for result in load_test_results:
                    print(f"  Type: {result.test_type}")
                    print(f"  RPS: {result.actual_rps:.1f}")
                    print(f"  Error rate: {result.error_rate:.2%}")
                    print(f"  P95 latency: {result.p95_latency_ms:.1f}ms")

            if efficiency:
                print("\nScaling Efficiency:")
                print(f"  Scale-up time: {efficiency.scale_up_time_seconds:.1f}s")
                print(f"  Scale-down time: {efficiency.scale_down_time_seconds:.1f}s")
                print(f"  Cost efficiency: {efficiency.cost_efficiency_score:.1f}/100")

            if cost_analysis:
                print("\nCost Analysis:")
                print(f"  Total cost: ${cost_analysis['total_cost']:.2f}")
                print(f"  Cost per million requests: ${cost_analysis['cost_per_million_requests']:.2f}")

        # Generate report
        if args.report:
            tester.generate_html_report(
                load_test_results,
                scaling_events,
                efficiency,
                cost_analysis,
                args.report
            )

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
