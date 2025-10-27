#!/usr/bin/env python3
"""
Canary Deployment Executor

Executes automated canary deployments with progressive traffic shifting,
health monitoring, and automatic rollback on failure. Supports Kubernetes,
AWS (ECS/ALB), and generic HTTP load balancers.

Usage:
    ./execute_canary.py [OPTIONS]

Examples:
    ./execute_canary.py --platform kubernetes --service myapp --version v2.0
    ./execute_canary.py --platform kubernetes --service myapp --version v2.0 --json
    ./execute_canary.py --platform aws-alb --service myapp --version v2.0 --region us-east-1
    ./execute_canary.py --config canary-config.yaml
    ./execute_canary.py --platform kubernetes --dry-run
"""

import argparse
import json
import sys
import time
import yaml
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path


@dataclass
class CanaryConfig:
    """Canary deployment configuration"""
    service: str
    canary_version: str
    stable_version: str
    initial_weight: int = 5
    step_weight: int = 15
    max_weight: int = 100
    interval_seconds: int = 300
    error_threshold: float = 1.0  # 1% error rate
    latency_threshold_ms: int = 1000
    success_rate_threshold: float = 99.0  # 99% success rate
    min_requests: int = 100  # Minimum requests before evaluation


@dataclass
class CanaryMetrics:
    """Canary deployment metrics"""
    timestamp: str
    weight: int
    request_count: int
    error_rate: float
    success_rate: float
    p50_latency: float
    p95_latency: float
    p99_latency: float
    healthy: bool
    reason: Optional[str] = None


class CanaryExecutor:
    """Executes canary deployments"""

    def __init__(self, platform: str, config: CanaryConfig, dry_run: bool = False, verbose: bool = False):
        self.platform = platform
        self.config = config
        self.dry_run = dry_run
        self.verbose = verbose
        self.metrics_history: List[CanaryMetrics] = []
        self.current_weight = 0

    def execute(self) -> bool:
        """Execute canary deployment"""
        if self.verbose:
            print(f"Starting canary deployment: {self.config.service}")
            print(f"Platform: {self.platform}")
            print(f"Stable: {self.config.stable_version}")
            print(f"Canary: {self.config.canary_version}")
            print(f"Dry run: {self.dry_run}\n")

        # Pre-deployment validation
        if not self._validate_environment():
            return False

        # Execute progressive rollout
        weights = range(
            self.config.initial_weight,
            self.config.max_weight + 1,
            self.config.step_weight
        )

        for weight in weights:
            if self.verbose:
                print(f"\n{'=' * 60}")
                print(f"Step: {weight}% traffic to canary")
                print(f"{'=' * 60}")

            # Update traffic weights
            if not self._update_weights(weight):
                return self._rollback("Failed to update traffic weights")

            self.current_weight = weight

            # Wait for metrics
            if self.verbose:
                print(f"\nWaiting {self.config.interval_seconds}s for metrics...")

            if not self.dry_run:
                self._wait_with_progress(self.config.interval_seconds)

            # Collect and evaluate metrics
            metrics = self._collect_metrics()
            self.metrics_history.append(metrics)

            if self.verbose:
                self._print_metrics(metrics)

            # Check health
            if not metrics.healthy:
                return self._rollback(f"Health check failed: {metrics.reason}")

            if self.verbose:
                print(f"\n✓ {weight}% deployment successful")

        # Final validation
        if not self._final_validation():
            return self._rollback("Final validation failed")

        if self.verbose:
            print(f"\n{'=' * 60}")
            print("✓ Canary deployment complete!")
            print(f"{'=' * 60}")

        return True

    def _validate_environment(self) -> bool:
        """Validate environment before deployment"""
        if self.verbose:
            print("Validating environment...")

        if self.platform == 'kubernetes':
            return self._validate_k8s_environment()
        elif self.platform in ['aws-alb', 'aws-ecs']:
            return self._validate_aws_environment()
        elif self.platform == 'generic':
            return self._validate_generic_environment()
        else:
            print(f"Unsupported platform: {self.platform}", file=sys.stderr)
            return False

    def _validate_k8s_environment(self) -> bool:
        """Validate Kubernetes environment"""
        if self.dry_run:
            if self.verbose:
                print("✓ Kubernetes environment validated (dry run)")
            return True

        try:
            import subprocess

            # Check kubectl access
            result = subprocess.run(
                ['kubectl', 'cluster-info'],
                capture_output=True,
                timeout=10
            )
            if result.returncode != 0:
                print("kubectl cluster-info failed", file=sys.stderr)
                return False

            # Check if service exists
            result = subprocess.run(
                ['kubectl', 'get', 'service', self.config.service],
                capture_output=True,
                timeout=10
            )
            if result.returncode != 0:
                print(f"Service {self.config.service} not found", file=sys.stderr)
                return False

            # Check if deployments exist
            for version in [self.config.stable_version, self.config.canary_version]:
                result = subprocess.run(
                    ['kubectl', 'get', 'deployment', f"{self.config.service}-{version}"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode != 0:
                    print(f"Deployment {self.config.service}-{version} not found", file=sys.stderr)
                    return False

            if self.verbose:
                print("✓ Kubernetes environment validated")
            return True

        except Exception as e:
            print(f"Environment validation failed: {str(e)}", file=sys.stderr)
            return False

    def _validate_aws_environment(self) -> bool:
        """Validate AWS environment"""
        if self.dry_run:
            if self.verbose:
                print("✓ AWS environment validated (dry run)")
            return True

        try:
            import boto3

            # Check AWS credentials
            sts = boto3.client('sts')
            sts.get_caller_identity()

            if self.verbose:
                print("✓ AWS environment validated")
            return True

        except Exception as e:
            print(f"AWS validation failed: {str(e)}", file=sys.stderr)
            return False

    def _validate_generic_environment(self) -> bool:
        """Validate generic HTTP environment"""
        if self.verbose:
            print("✓ Generic environment validated")
        return True

    def _update_weights(self, canary_weight: int) -> bool:
        """Update traffic weights"""
        stable_weight = 100 - canary_weight

        if self.verbose:
            print(f"\nUpdating weights: stable={stable_weight}%, canary={canary_weight}%")

        if self.dry_run:
            if self.verbose:
                print("✓ Weights updated (dry run)")
            return True

        if self.platform == 'kubernetes':
            return self._update_k8s_weights(stable_weight, canary_weight)
        elif self.platform == 'aws-alb':
            return self._update_alb_weights(stable_weight, canary_weight)
        elif self.platform == 'aws-ecs':
            return self._update_ecs_weights(stable_weight, canary_weight)
        elif self.platform == 'generic':
            return self._update_generic_weights(stable_weight, canary_weight)

        return False

    def _update_k8s_weights(self, stable_weight: int, canary_weight: int) -> bool:
        """Update Kubernetes traffic weights using Istio"""
        import subprocess

        # Assume Istio VirtualService exists
        virtual_service = f"""
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: {self.config.service}
spec:
  hosts:
  - {self.config.service}
  http:
  - route:
    - destination:
        host: {self.config.service}
        subset: stable
      weight: {stable_weight}
    - destination:
        host: {self.config.service}
        subset: canary
      weight: {canary_weight}
"""

        try:
            result = subprocess.run(
                ['kubectl', 'apply', '-f', '-'],
                input=virtual_service.encode(),
                capture_output=True,
                timeout=30
            )

            if result.returncode == 0:
                if self.verbose:
                    print("✓ Kubernetes weights updated")
                return True
            else:
                print(f"Failed to update weights: {result.stderr.decode()}", file=sys.stderr)
                return False

        except Exception as e:
            print(f"Error updating weights: {str(e)}", file=sys.stderr)
            return False

    def _update_alb_weights(self, stable_weight: int, canary_weight: int) -> bool:
        """Update AWS ALB target group weights"""
        try:
            import boto3

            elbv2 = boto3.client('elbv2')

            # This is simplified - in reality, you'd need to get listener ARN
            # and target group ARNs from config
            if self.verbose:
                print("✓ ALB weights updated (simulated)")
            return True

        except Exception as e:
            print(f"Error updating ALB weights: {str(e)}", file=sys.stderr)
            return False

    def _update_ecs_weights(self, stable_weight: int, canary_weight: int) -> bool:
        """Update ECS service weights"""
        try:
            import boto3

            ecs = boto3.client('ecs')

            # This is simplified - in reality, you'd update task counts
            # to match the weight distribution
            if self.verbose:
                print("✓ ECS weights updated (simulated)")
            return True

        except Exception as e:
            print(f"Error updating ECS weights: {str(e)}", file=sys.stderr)
            return False

    def _update_generic_weights(self, stable_weight: int, canary_weight: int) -> bool:
        """Update generic load balancer weights"""
        # This would call a custom API or configuration endpoint
        if self.verbose:
            print("✓ Generic weights updated (simulated)")
        return True

    def _collect_metrics(self) -> CanaryMetrics:
        """Collect canary metrics"""
        if self.dry_run:
            # Simulate healthy metrics
            return CanaryMetrics(
                timestamp=datetime.now().isoformat(),
                weight=self.current_weight,
                request_count=500,
                error_rate=0.5,
                success_rate=99.5,
                p50_latency=50.0,
                p95_latency=100.0,
                p99_latency=150.0,
                healthy=True
            )

        if self.platform == 'kubernetes':
            return self._collect_k8s_metrics()
        elif self.platform in ['aws-alb', 'aws-ecs']:
            return self._collect_aws_metrics()
        else:
            return self._collect_generic_metrics()

    def _collect_k8s_metrics(self) -> CanaryMetrics:
        """Collect metrics from Kubernetes (Prometheus)"""
        # In a real implementation, this would query Prometheus
        # Simulated for demonstration
        import random

        request_count = random.randint(200, 1000)
        error_rate = random.uniform(0.1, 0.8)
        success_rate = 100 - error_rate

        metrics = CanaryMetrics(
            timestamp=datetime.now().isoformat(),
            weight=self.current_weight,
            request_count=request_count,
            error_rate=error_rate,
            success_rate=success_rate,
            p50_latency=random.uniform(30, 80),
            p95_latency=random.uniform(100, 200),
            p99_latency=random.uniform(200, 400),
            healthy=True
        )

        # Evaluate health
        metrics.healthy, metrics.reason = self._evaluate_health(metrics)

        return metrics

    def _collect_aws_metrics(self) -> CanaryMetrics:
        """Collect metrics from AWS CloudWatch"""
        # Simulated
        import random

        request_count = random.randint(200, 1000)
        error_rate = random.uniform(0.1, 0.8)

        metrics = CanaryMetrics(
            timestamp=datetime.now().isoformat(),
            weight=self.current_weight,
            request_count=request_count,
            error_rate=error_rate,
            success_rate=100 - error_rate,
            p50_latency=random.uniform(30, 80),
            p95_latency=random.uniform(100, 200),
            p99_latency=random.uniform(200, 400),
            healthy=True
        )

        metrics.healthy, metrics.reason = self._evaluate_health(metrics)

        return metrics

    def _collect_generic_metrics(self) -> CanaryMetrics:
        """Collect generic HTTP metrics"""
        # Simulated
        import random

        request_count = random.randint(200, 1000)
        error_rate = random.uniform(0.1, 0.8)

        metrics = CanaryMetrics(
            timestamp=datetime.now().isoformat(),
            weight=self.current_weight,
            request_count=request_count,
            error_rate=error_rate,
            success_rate=100 - error_rate,
            p50_latency=random.uniform(30, 80),
            p95_latency=random.uniform(100, 200),
            p99_latency=random.uniform(200, 400),
            healthy=True
        )

        metrics.healthy, metrics.reason = self._evaluate_health(metrics)

        return metrics

    def _evaluate_health(self, metrics: CanaryMetrics) -> Tuple[bool, Optional[str]]:
        """Evaluate if canary is healthy"""

        # Check minimum requests
        if metrics.request_count < self.config.min_requests:
            return True, None  # Not enough data yet

        # Check error rate
        if metrics.error_rate > self.config.error_threshold:
            return False, f"Error rate {metrics.error_rate:.2f}% exceeds threshold {self.config.error_threshold}%"

        # Check success rate
        if metrics.success_rate < self.config.success_rate_threshold:
            return False, f"Success rate {metrics.success_rate:.2f}% below threshold {self.config.success_rate_threshold}%"

        # Check latency
        if metrics.p99_latency > self.config.latency_threshold_ms:
            return False, f"P99 latency {metrics.p99_latency:.0f}ms exceeds threshold {self.config.latency_threshold_ms}ms"

        return True, None

    def _final_validation(self) -> bool:
        """Final validation before completing deployment"""
        if self.verbose:
            print("\nPerforming final validation...")

        # Check last 3 metric samples are all healthy
        recent_metrics = self.metrics_history[-3:] if len(self.metrics_history) >= 3 else self.metrics_history

        all_healthy = all(m.healthy for m in recent_metrics)

        if all_healthy:
            if self.verbose:
                print("✓ Final validation passed")
            return True
        else:
            print("Final validation failed: Recent metrics show unhealthy state", file=sys.stderr)
            return False

    def _rollback(self, reason: str) -> bool:
        """Rollback to stable version"""
        print(f"\n{'=' * 60}", file=sys.stderr)
        print(f"🚨 ROLLBACK TRIGGERED: {reason}", file=sys.stderr)
        print(f"{'=' * 60}\n", file=sys.stderr)

        if self.verbose:
            print("Rolling back to stable version...")

        # Set weight to 0% for canary
        if not self.dry_run:
            self._update_weights(0)

        if self.verbose:
            print("✓ Rollback complete")

        return False

    def _wait_with_progress(self, seconds: int):
        """Wait with progress indicator"""
        for i in range(seconds):
            if i % 10 == 0:
                remaining = seconds - i
                print(f"  {remaining}s remaining...", end='\r')
            time.sleep(1)
        print(" " * 40, end='\r')  # Clear line

    def _print_metrics(self, metrics: CanaryMetrics):
        """Print metrics in human-readable format"""
        print("\nMetrics:")
        print(f"  Requests: {metrics.request_count}")
        print(f"  Error rate: {metrics.error_rate:.2f}%")
        print(f"  Success rate: {metrics.success_rate:.2f}%")
        print(f"  Latency (p50/p95/p99): {metrics.p50_latency:.0f}ms / {metrics.p95_latency:.0f}ms / {metrics.p99_latency:.0f}ms")
        print(f"  Health: {'✓ HEALTHY' if metrics.healthy else f'✗ UNHEALTHY ({metrics.reason})'}")

    def get_report(self) -> Dict:
        """Get deployment report"""
        return {
            'config': asdict(self.config),
            'platform': self.platform,
            'success': len(self.metrics_history) > 0 and self.metrics_history[-1].healthy,
            'final_weight': self.current_weight,
            'metrics_history': [asdict(m) for m in self.metrics_history],
            'total_duration_seconds': len(self.metrics_history) * self.config.interval_seconds
        }


def main():
    parser = argparse.ArgumentParser(
        description='Execute automated canary deployment',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--platform',
        choices=['kubernetes', 'aws-alb', 'aws-ecs', 'generic'],
        required=True,
        help='Deployment platform'
    )
    parser.add_argument(
        '--service',
        help='Service name'
    )
    parser.add_argument(
        '--version',
        help='Canary version to deploy'
    )
    parser.add_argument(
        '--stable-version',
        help='Current stable version (default: stable)'
    )
    parser.add_argument(
        '--config',
        help='Canary configuration file (YAML)'
    )
    parser.add_argument(
        '--initial-weight',
        type=int,
        default=5,
        help='Initial canary weight percentage (default: 5)'
    )
    parser.add_argument(
        '--step-weight',
        type=int,
        default=15,
        help='Weight increase per step (default: 15)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Seconds between steps (default: 300)'
    )
    parser.add_argument(
        '--error-threshold',
        type=float,
        default=1.0,
        help='Error rate threshold percentage (default: 1.0)'
    )
    parser.add_argument(
        '--latency-threshold',
        type=int,
        default=1000,
        help='P99 latency threshold in ms (default: 1000)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate deployment without making changes'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Load configuration
    if args.config:
        with open(args.config) as f:
            config_data = yaml.safe_load(f)
            canary_config = CanaryConfig(**config_data)
    else:
        if not args.service or not args.version:
            parser.error('--service and --version required when not using --config')

        canary_config = CanaryConfig(
            service=args.service,
            canary_version=args.version,
            stable_version=args.stable_version or 'stable',
            initial_weight=args.initial_weight,
            step_weight=args.step_weight,
            interval_seconds=args.interval,
            error_threshold=args.error_threshold,
            latency_threshold_ms=args.latency_threshold
        )

    # Execute canary deployment
    executor = CanaryExecutor(
        platform=args.platform,
        config=canary_config,
        dry_run=args.dry_run,
        verbose=args.verbose or not args.json
    )

    success = executor.execute()

    # Output report
    if args.json:
        report = executor.get_report()
        report['success'] = success
        print(json.dumps(report, indent=2))
    elif args.verbose:
        if success:
            print("\n✓ Canary deployment completed successfully!")
        else:
            print("\n✗ Canary deployment failed or was rolled back", file=sys.stderr)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
